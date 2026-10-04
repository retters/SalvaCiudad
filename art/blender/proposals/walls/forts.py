"""Assembled demo models: a small fort per wall type, made by calling the
family's own piece builders at grid offsets, to show how the pieces join.

The wall's center line is a rectangle of 14 x 10 m (16 x 12 m outside):
two 4 x 4 m towers on the front corners, a 4 m gate between them with a
1 m half module on each side, two plain corners at the back, and a T
junction on the back wall from which an inner wall runs to an end cap."""

import gates
import more2
import towers
import wall_models
from registry import reg
from wallkit import Pen
from walltypes import PIECES, WALLS, Masonry, stairs_length

ADOBE_TOWER = Masonry("adobe_tower", "adobe", "adobe_dark", "roof", "adobe_light", 2.4, 0.8, course=0.8,
                      walkmat="adobe_dark")
WHITE_TOWER = Masonry("white_tower", "plaster", "stone_dark", "roof", "plaster_warm", 2.6, 0.8, course=0.9)


def fort(p, key, tower_l=None, tower_r=None, back_special="slit"):
    W = WALLS[key]
    q = Pen(p.mb, p.m, True)

    def put(kind, x, y, rot=0.0):
        PIECES[kind](q.at(x=x, y=y, rot=rot), W)

    # Front: towers (or corners), wall, half modules and the gate.
    if tower_l:
        tower_l(q.at(x=-7, y=-5))
        tower_r(q.at(x=7, y=-5))
        put("straight", -4, -5)
        put("straight", 4, -5)
        put("half", -2.5, -5)
        put("half", 2.5, -5)
        side = [(-2, "straight"), (0, "torch"), (2, "straight"), (3.5, "half")]
    else:
        put("corner", -7, -5, 0)
        put("corner", 7, -5, 90)
        for x in (-5, -3, 3, 5):
            put("straight", x, -5)
        side = [(-3, "straight"), (-1, "straight"), (1, "torch"), (3, "straight")]
    gates.gate_for(key)(q.at(x=0, y=-5))
    # Sides (the brazier looks outward).
    for y, kind in side:
        put(kind, -7, y, 270)
        put(kind, 7, y, 90)
    # Back: corners, stairs (walls with a walkway), a special piece and the T.
    put("corner", 7, 5, 180)
    put("corner", -7, 5, 270)
    cells = [-5, -3, -1, 3, 5]
    if W.walk is not None:
        Ls = stairs_length(W)
        put("stairs", -6 + Ls / 2, 5, 180)
        cells = [c for c in cells if c > -6 + Ls]
    for c in cells:
        put(back_special if c == 3 and back_special in PIECES else "straight", c, 5)
    put("tee", 1, 5, 180)
    put("straight", 1, 3, 90)
    put("straight", 1, 1, 90)
    put("end", 1, -1, 270)
    return None


def describe(key, towers_text, gate_text, extra=""):
    W = WALLS[key]
    stairs = ", 1 escalera al adarve" if W.walk is not None else ""
    halves = ("" if towers_text.startswith("sin") else
              "2 medios módulos de 1 m junto a la puerta y otros 2 en los lados, 2 esquinas, ")
    return ("Montado solo con piezas del catálogo: %s, %s, rectos, %s1 unión en T con un muro interior de "
            "2 rectos y 1 remate, 2 piezas con brasero%s%s." % (towers_text, gate_text, halves, stairs, extra))


def tw(fn, W, sides, **kw):
    return lambda q: fn(q, W, walk_sides=sides, **kw)


FORTS = [
    ("palisade", lambda q: towers.tower_wood_round(q, roof=True), lambda q: towers.tower_wood_round(q, roof=True),
     "slit", "2 torres redondas de troncos con techo", "la puerta de empalizada", " y 1 tronera"),
    ("plank", lambda q: towers.tower_wood_square(q, roof=True), lambda q: towers.tower_wood_square(q, roof=True),
     "slit", "2 torres cuadradas de madera con techo", "la puerta de tablas", " y 1 aspillera"),
    ("stone", tw(towers.tower_square, WALLS["stone"], "EN"), tw(towers.tower_round, WALLS["stone"], "WN", roof=True),
     "buttress", "1 torre cuadrada abierta y 1 redonda con tejado", "la puerta de sillería", " y 1 contrafuerte"),
    ("brick", tw(towers.tower_round, WALLS["brick"], "EN", roof=True),
     tw(towers.tower_round, WALLS["brick"], "WN", roof=True),
     "banner", "2 torres redondas de ladrillo con tejado", "la puerta de ladrillo", " y 1 estandarte"),
    ("adobe", tw(towers.tower_square, ADOBE_TOWER, "", roof=True), tw(towers.tower_square, ADOBE_TOWER, "", roof=True),
     "slit", "2 torres cuadradas de adobe con tejado (variante de la torre cuadrada)", "la puerta de adobe",
     " y 1 ventana"),
    ("iron", tw(towers.tower_square, WALLS["iron"], "EN", roof=True), tw(towers.tower_ballista, WALLS["iron"], "WN"),
     "drain", "1 torre cuadrada con tejado y 1 torre de balista", "la puerta reforzada", " y 1 desagüe enrejado"),
    ("fieldstone", None, None, "stile", "sin torres (4 esquinas)", "la cancela de piedra de campo",
     " y 1 paso de escalones"),
    ("hedge", None, None, "arch", "sin torres (4 esquinas)", "el arco con cancela", " y 1 arco de paso"),
    ("whitewash", tw(towers.tower_square, WHITE_TOWER, "", roof=True),
     tw(towers.tower_square, WHITE_TOWER, "", roof=True), "slit",
     "2 torres cuadradas encaladas con tejado (variante de la torre cuadrada)", "la puerta de la tapia",
     " y 1 ventana"),
    ("dwarf", tw(towers.tower_square, WALLS["dwarf"], "EN"), tw(towers.tower_square, WALLS["dwarf"], "WN", roof=True),
     "buttress", "2 torres cuadradas enanas, una abierta y una con tejado de pizarra", "la puerta enana",
     " y 1 contrafuerte"),
    ("elf", tw(towers.tower_round, WALLS["elf"], "EN", roof=True),
     tw(towers.tower_round, WALLS["elf"], "WN", roof=True),
     "banner", "2 torres redondas élficas con tejado verde", "la puerta élfica", " y 1 estandarte"),
    ("darkelf", tw(towers.tower_round, WALLS["darkelf"], "EN", roof=True),
     tw(towers.tower_square, WALLS["darkelf"], "WN"), "slit",
     "1 torre redonda con tejado y 1 cuadrada abierta de los elfos oscuros", "la puerta de los elfos oscuros",
     " y 1 aspillera"),
    ("sandstone", tw(towers.tower_square, WALLS["sandstone"], "EN"),
     tw(towers.tower_round, WALLS["sandstone"], "WN"), "drain", "1 torre cuadrada y 1 redonda de arenisca, abiertas",
     "la puerta de arenisca", " y 1 desagüe enrejado"),
    ("foxfolk", tw(towers.tower_square, WALLS["foxfolk"], "EN", roof=True),
     tw(towers.tower_square, WALLS["foxfolk"], "WN", roof=True), "banner",
     "2 torres cuadradas de la gente zorro con tejado de pizarra", "la puerta de la gente zorro", " y 1 estandarte"),
    ("catfolk", tw(towers.tower_round, WALLS["catfolk"], "EN", roof=True),
     tw(towers.tower_square, WALLS["catfolk"], "WN"), "buttress",
     "1 torre redonda con tejado azul y 1 cuadrada abierta de la gente gato", "la puerta de la gente gato",
     " y 1 contrafuerte"),
    ("orc", lambda q: towers.tower_wood_round(q, **towers.ORC),
     lambda q: towers.tower_wood_round(q, roof=True, **towers.ORC), "slit",
     "2 torres redondas orcas, una abierta y una con techo de pieles", "la puerta orca", " y 1 tronera"),
    ("stockade", lambda q: towers.tower_wood_square(q, roof=True), lambda q: towers.tower_wood_round(q, roof=True),
     "slit", "1 torre cuadrada y 1 redonda de madera con techo", "la puerta de empalizada doble", " y 1 ventana"),
    ("reed", lambda q: more2.tower_reed(q), lambda q: more2.tower_reed(q, roof=False), "straight",
     "2 atalayas de cañas sobre pilotes, una con techo y una abierta", "la puerta de cañas", ""),
    ("cobble", tw(towers.tower_square, WALLS["cobble"], "", roof=True),
     tw(towers.tower_round, WALLS["cobble"], "", roof=True), "buttress",
     "1 torre cuadrada y 1 redonda de mampostería", "la puerta de mampostería", " y 1 contrafuerte"),
]

for key, tl, tr, special, towers_text, gate_text, extra in FORTS:
    reg("wall_" + key, "wall_%s_demo_fort" % key, "Fuerte de demostración (16 × 12 m)",
        (lambda p, key=key, tl=tl, tr=tr, special=special: fort(p, key, tl, tr, special)),
        material=wall_models.MATERIAL[key], nota=describe(key, towers_text, gate_text, extra))
