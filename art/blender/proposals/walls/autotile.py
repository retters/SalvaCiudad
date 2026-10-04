"""A reference implementation of the connection rule the catalog describes:
given a map of 2 m cells, pick the piece and its turn for every wall cell
from its four neighbors. The demo models are built with it from a small
text map, so what the owner sees is what the rule produces.

Map characters (one per 2 x 2 m cell, top row = north):

    .  nothing            #  wall
    t  wall, with a brazier where the cell is a straight
    s  wall, with an arrow slit or window where it is a straight
    T  tower (4 x 4 m, centered on the cell; the walls run 1 m into it)
    G  gate: two G side by side (or one above the other) make one 4 m gate
    P  postern (a straight cell with a small door)
"""

import gates
import towers
import wall_models
from registry import reg
from wallkit import Pen
from walltypes import PIECES, WALLS

WALL_LIKE = "#tsTGP"
DIRS = {"E": (1, 0), "N": (0, -1), "W": (-1, 0), "S": (0, 1)}   # (column, row) steps; row 0 is north.

# The piece and its turn (degrees) for every set of neighbors.
RULE = {
    "": ("pillar", 0),
    "W": ("end", 0), "S": ("end", 90), "E": ("end", 180), "N": ("end", 270),
    "EW": ("straight", 0), "NS": ("straight", 90),
    "EN": ("corner", 0), "NW": ("corner", 90), "SW": ("corner", 180), "ES": ("corner", 270),
    "ENW": ("tee", 0), "NSW": ("tee", 90), "ESW": ("tee", 180), "ENS": ("tee", 270),
    "ENSW": ("cross", 0),
}
SPECIAL = {"t": "torch", "s": "slit"}


def pick(arms):
    """(piece, turn) for a set of sides ("E", "N", "W", "S") with a neighbor."""
    return RULE["".join(sorted(arms))]


def neighbors(rows, c, r):
    out = set()
    for d, (dc, dr) in DIRS.items():
        rr, cc = r + dr, c + dc
        if 0 <= rr < len(rows) and 0 <= cc < len(rows[rr]) and rows[rr][cc] in WALL_LIKE:
            out.add(d)
    return out


def outside(rows):
    """The cells that are not enclosed: every cell without wall that can be
    reached from the border of the map (plus the ring around the map)."""
    h, w = len(rows), len(rows[0])
    seen = {(c, r) for c in range(-1, w + 1) for r in (-1, h)} | {(c, r) for r in range(-1, h + 1) for c in (-1, w)}
    todo = list(seen)
    while todo:
        c, r = todo.pop()
        for dc, dr in DIRS.values():
            n = (c + dc, r + dr)
            if n in seen or not (0 <= n[0] < w and 0 <= n[1] < h) or rows[n[1]][n[0]] in WALL_LIKE:
                continue
            seen.add(n)
            todo.append(n)
    return seen


def build(p, key, text, tower=None):
    """Draws the map with the pieces of wall type `key`."""
    W = WALLS[key]
    q = Pen(p.mb, p.m, True)
    rows = [line for line in text.strip("\n").split("\n")]
    width = max(len(line) for line in rows)
    rows = [line.ljust(width, ".") for line in rows]

    def center(c, r):
        return ((c - (width - 1) / 2) * 2.0, ((len(rows) - 1) / 2 - r) * 2.0)

    out = outside(rows)

    def outward(c, r, turn):
        """Adds half a turn if the front of a piece turned `turn` degrees
        (its local -Y) would look inside the enclosure."""
        dc, dr = {0: (0, 1), 90: (1, 0), 180: (0, -1), 270: (-1, 0)}[turn % 360]
        behind = (c - dc, r - dr)
        return turn + 180 if behind in out and (c + dc, r + dr) not in out else turn

    done = set()
    count = {}
    for r, line in enumerate(rows):
        for c, ch in enumerate(line):
            if ch not in WALL_LIKE or (c, r) in done:
                continue
            x, y = center(c, r)
            arms = neighbors(rows, c, r)
            if ch == "G":   # A gate takes this cell and the next one, east or south.
                if c + 1 < width and rows[r][c + 1] == "G":
                    done.add((c + 1, r))
                    gates.gate_for(key)(q.at(x=x + 1.0, y=y, rot=outward(c, r, 0)))
                else:
                    done.add((c, r + 1))
                    gates.gate_for(key)(q.at(x=x, y=y - 1.0, rot=outward(c, r, 90)))
                kind = "gate"
            elif ch == "T" and tower is not None:
                tower(q.at(x=x, y=y), "".join(sorted(arms)))
                kind = "tower"
            elif ch == "P" and len(arms) == 2 and pick(arms)[0] == "straight":
                gates.postern(q.at(x=x, y=y, rot=pick(arms)[1]), W)
                kind = "postern"
            else:
                kind, turn = pick(arms)
                if kind == "straight" and ch in SPECIAL and SPECIAL[ch] in wall_models.SETS[key]:
                    kind = SPECIAL[ch]
                    turn = outward(c, r, turn)   # The brazier looks out.
                PIECES[kind](q.at(x=x, y=y, rot=turn), W)
            count[kind] = count.get(kind, 0) + 1
    return count


# A town wall with an irregular outline: a notch, inner dividing walls
# with T junctions, a cross, spurs that end in caps and a lone pillar.
TOWN = """
T###t##GG##t###T
#..............#
s..............s
#......T####t###
#......#........
t......#...#....
#......P...#....
#######T#######.
#......#...#....
s......#......#.
#......t........
T##t#GG#........
"""


def town(p, key, tower):
    build(p, key, TOWN, tower)
    return None


def masonry_tower(key):
    W = WALLS[key]
    state = {"n": 0}

    def make(pen, arms):
        state["n"] += 1
        if state["n"] % 2:
            towers.tower_round(pen, W, roof=True, walk_sides=arms)
        else:
            towers.tower_square(pen, W, walk_sides=arms)
    return make


def wood_tower(pen, arms):
    towers.tower_wood_round(pen, roof=True)


NOTE = ("Generada con la regla de conexión del catálogo a partir de un mapa de texto de 16 × 12 celdas "
        "(32 × 24 m): el código elige recto, esquina, T, cruce, remate o pilar según los vecinos de cada "
        "celda, coloca torres, puertas y una poterna donde el mapa las marca y orienta puertas y braseros "
        "hacia fuera (lo que no está encerrado se halla rellenando desde el borde). Es la referencia para el "
        "algoritmo del juego (art/blender/proposals/walls/autotile.py).")

for _key, _tower in (("stone", masonry_tower("stone")), ("palisade", wood_tower), ("brick", masonry_tower("brick")),
                     ("hedge", None), ("fieldstone", None), ("adobe", None), ("stockade", wood_tower)):
    reg("wall_" + _key, "wall_%s_demo_autotile" % _key, "Recinto generado por la regla (32 × 24 m)",
        (lambda p, key=_key, tower=_tower: town(p, key, tower)), material=wall_models.MATERIAL[_key], nota=NOTE)
