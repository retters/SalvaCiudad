"""A larger assembled demo for the masonry walls with a walkway: a castle
of 30 x 24 m built only from the family's pieces, to show the modular
system at the scale of a late-game town.

Center line of the outer wall: x = -13..13, y = -10..10 (front at -Y).
Round roofed towers on the front corners, a gatehouse with a drawbridge
between them, a bastion with a ballista and a square tower at the back,
and an inner ward (north-west) closed by an inner wall with its own gate,
holding the keep."""

import defenses
import extras
import gates
import towers
import wall_models
from registry import reg
from wallkit import Pen
from walltypes import PIECES, WALLS, stairs_length


def castle(p, key):
    W = WALLS[key]
    q = Pen(p.mb, p.m, True)

    def put(kind, x, y, rot=0.0):
        PIECES[kind](q.at(x=x, y=y, rot=rot), W)

    # Front: towers, gatehouse with drawbridge, hoardings beside it.
    towers.tower_round(q.at(x=-13, y=-10), W, roof=True, walk_sides="EN")
    towers.tower_round(q.at(x=13, y=-10), W, roof=True, walk_sides="WN")
    gates.gatehouse(q.at(x=0, y=-10), W, bridge=True)
    for s in (-1, 1):
        put("straight", s * 10, -10)
        put("torch", s * 8, -10)
        put("slit", s * 6, -10)
        defenses.hoarding(q.at(x=s * 4, y=-10), W)
    # Right side and its square tower at the back.
    for y, kind in ((-7, "straight"), (-5, "buttress"), (-3, "straight"), (-1, "torch"), (1, "straight"),
                    (3, "buttress"), (5, "straight"), (7, "slit")):
        put(kind, 13, y, 90)
    towers.tower_square(q.at(x=13, y=10), W, walk_sides="WS")
    # Left side, with the T of the inner wall, up to the bastion.
    for y, kind in ((-7, "straight"), (-5, "buttress"), (-3, "torch"), (-1, "straight"), (3, "straight"),
                    (5, "slit")):
        put(kind, -13, y, 270)
    put("tee", -13, 1, 270)
    put("half", -13, 6.5, 270)
    towers.tower_bastion(q.at(x=-13, y=10), W)
    towers.ballista(q.at(x=-13, y=10, rot=135), W.h + 0.45)
    # Back wall: roofed walk, a postern, stairs, the T of the inner wall.
    for x in (-9, -7, -5, -3, -1):
        put("roofed", x, 10)
    put("tee", 1, 10, 180)
    gates.postern(q.at(x=3, y=10), W)
    Ls = stairs_length(W)
    put("stairs", 4 + Ls / 2, 10, 180)
    if Ls == 4:
        put("straight", 9, 10)
    put("half", 10.5, 10)
    # Inner wall: from the left T east to a gate, a corner, and north to the back T.
    for x in (-11, -9, -7):
        put("straight", x, 1)
    gates.gate_for(key)(q.at(x=-4, y=1))
    put("straight", -1, 1)
    put("corner", 1, 1, 90)
    for y in (3, 5, 7):
        put("straight", 1, y, 90)
    put("half", 1, 8.5, 90)
    # The keep in the inner ward; machines and stores in the outer ward.
    towers.tower_keep(q.at(x=-8.0, y=5.5, rot=90), W)
    extras.catapult(q.at(x=7, y=-3, rot=200))
    defenses.watch_platform(q.at(x=8, y=4, rot=180))
    for i, (x, y) in enumerate(((4.5, 7.2), (5.2, 7.5), (4.8, 6.6))):
        q.cyl((x, y, 0), (x, y, 0.9), 0.32, 0.32, "wood", seg=8)
        q.cyl((x, y, 0.2), (x, y, 0.26), 0.34, 0.34, "iron", seg=8)
        q.cyl((x, y, 0.64), (x, y, 0.7), 0.34, 0.34, "iron", seg=8)
    for x, y, s in ((10.2, 6.0, 0.7), (10.3, 6.9, 0.6), (10.25, 6.4, 0.5)):
        q.box((x, y, s / 2 if s > 0.55 else 0.7 + s / 2), (s, s, s), "wood_light", rz=10 * s)
    return None


NOTE = ("Montado solo con piezas del catálogo: 2 torres redondas con tejado, torre-puerta con puente levadizo, "
        "2 cadalsos, torre cuadrada, bastión con balista, adarve cubierto, poterna, escalera, contrafuertes, "
        "aspilleras, braseros, medios módulos, 2 uniones en T, un muro interior con su puerta y su esquina, la "
        "torre del homenaje, una catapulta y una atalaya.")

for _key in ("stone", "brick", "iron", "sandstone", "dwarf", "elf", "darkelf", "foxfolk", "catfolk"):
    reg("wall_" + _key, "wall_%s_demo_castle" % _key, "Castillo de demostración (30 × 24 m)",
        (lambda p, key=_key: castle(p, key)), material=wall_models.MATERIAL[_key], nota=NOTE)
