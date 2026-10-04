"""Gates: double doors 4 m wide for every wall type, posterns of 2 m and
stone gatehouses with a portcullis. The gate ends show the wall's own
cross-section at x = -2 and x = +2, so they plug into the wall run."""

import math

import _kit as kit
from registry import reg
from wallkit import Pen, add_flicker, brazier, door_leaf, door_mech, flame_bones, flame_mech, rubble
from walltypes import WALLS, Adobe, Fieldstone, Hedge, Palisade, PlankRampart, ReedWall

OPEN = {"open": "Las dos hojas se abren hacia dentro", "close": "Las dos hojas se cierran"}


BROKEN = [False]   # Set while a damaged gate is drawn: see broken_gate().


NO_LEAVES = [False]   # Set while an open archway is drawn: see open_arch().


def leaves(p, half_w, height, style, y=0.0):
    if NO_LEAVES[0]:
        return [("door_l", (-half_w, y), +1), ("door_r", (half_w, y), -1)]
    if BROKEN[0]:   # One leaf hangs ajar from a hinge, the other lies on the ground inside.
        from mathutils import Matrix
        hang = Pen(p.mb, p.m @ Matrix.Translation((-half_w, y, 0.0)) @ Matrix.Rotation(math.radians(38), 4, "Z")
                   @ Matrix.Rotation(math.radians(-7), 4, "Y"), True)
        door_leaf(hang, 0.0, 0.0, half_w - 0.02, height, +1, "door_l", style)
        flat = Pen(p.mb, p.m @ Matrix.Translation((half_w - 0.3, y + 0.9, 0.12))
                   @ Matrix.Rotation(math.radians(-80), 4, "Z") @ Matrix.Rotation(math.radians(-90), 4, "X"), True)
        door_leaf(flat, 0.0, 0.0, half_w - 0.02, height, -1, "door_r", style, z0=0.0)
        return [("door_l", (-half_w, y), +1), ("door_r", (half_w, y), -1)]
    door_leaf(p, -half_w, y, half_w - 0.02, height, +1, "door_l", style)
    door_leaf(p, half_w, y, half_w - 0.02, height, -1, "door_r", style)
    return [("door_l", (-half_w, y), +1), ("door_r", (half_w, y), -1)]


def gate_walkway(p, W, style="plank"):
    """Masonry or plank wall with a walkway: the walkway crosses over the
    doors on a bridge, raised if the wall is low."""
    over = max(W.h, 3.4)
    lift = over - W.h
    door_h = min(over - 0.8, 3.4)
    for s in (-1, 1):
        W.run(p.at(rot=0 if s > 0 else 180), 1.4, 2.0)
    W.run(p, -1.4, 1.4, base=lift, floor=door_h + 0.25)
    t = W.t
    wood = isinstance(W, PlankRampart)
    trim = W.frame_mat
    for s in (-1, 1):
        p.box((s * 1.47, 0, door_h / 2), (0.16, t + 0.14, door_h), trim)
        for f in (-1, 1):   # Buttresses on both faces.
            p.box((s * 1.72, f * (t / 2 + 0.14), over / 2), (0.44, 0.3, over), "timber" if wood else W.mat)
            if not wood:
                p.box((s * 1.72, f * (t / 2 + 0.16), 0.25), (0.52, 0.36, 0.5), W.dark)
                p.taper((s * 1.72, f * (t / 2 + 0.14)), (0.44, 0.3), (0.44, 0.06), over, over + 0.4, W.trim)
            # Corbels that round the top corners of the opening.
            p.box((s * 1.22, f * (t / 2 - 0.1), door_h - 0.15), (0.36, 0.3, 0.36), trim)
            p.box((s * 0.98, f * (t / 2 - 0.1), door_h + 0.02), (0.2, 0.3, 0.2), trim)
        if lift > 0.05:   # Steps from the wall's walkway up to the bridge.
            for i in range(3):
                p.box((s * (1.9 - i * 0.2), 0, W.h + (i + 1) * lift / 6), (0.2, t - 0.34, (i + 1) * lift / 3),
                      "wood_light" if wood else W.walkmat)
    p.box((0, 0, door_h + 0.2), (3.1, t + 0.16, 0.3), trim)
    p.box((0, -(t / 2 + 0.1), door_h + 0.24), (0.4, 0.1, 0.5), W.light if not wood else "iron")
    p.box((0, -(t / 2 + 0.16), over - 0.55), (0.6, 0.06, 0.7), "cloth_red")   # The town's arms.
    p.box((0, -(t / 2 + 0.2), over - 0.5), (0.3, 0.04, 0.3), "gold", rz=0)
    hinges = leaves(p, 1.38, door_h - 0.05, style)
    pts = [brazier(p, s * 1.72, -(t / 2 + 0.42), 0.0, 1.9, bone) for s, bone in ((-1, "flame"), (1, "flame2"))]
    if p.static:
        return None
    names, bones = flame_bones(pts)
    return add_flicker(door_mech(hinges, extra=bones), names)


def gate_palisade(p, W):
    for s in (-1, 1):
        p.cyl((s * 1.7, 0, 0), (s * 1.7, 0, 4.2), 0.3, 0.27, W.log, seg=8)
        p.cyl((s * 1.7, 0, 4.2), (s * 1.7, 0, 4.75), 0.27, 0.0, W.tip, seg=8)
        for z in (1.0, 3.2):
            p.cyl((s * 1.7, 0, z - 0.08), (s * 1.7, 0, z + 0.08), 0.32, 0.32, "iron", seg=8)
        for f in (-1, 1):   # Raking shores.
            p.beam((s * 1.7, f * 1.0, 0.0), (s * 1.7, f * 0.25, 2.4), 0.14, "timber")
        p.beam((s * 1.4, 0, 2.9), (s * 0.7, 0, 3.55), 0.14, "timber")
    for z, r in ((3.62, 0.17), (3.98, 0.15)):
        p.cyl((-2.0, 0, z), (2.0, 0, z), r, r, W.log, seg=7)
        for s in (-1, 1):
            p.cyl((s * 2.0, 0, z), (s * 2.02, 0, z), r * 0.85, r * 0.85, W.tip, seg=7)
    # A lookout plank and a small shingled roof over the doors.
    p.box((0, 0, 4.16), (3.0, 0.9, 0.07), "wood_light")
    for f in (-1, 1):
        p.box((0, f * 0.45, 4.6), (3.0, 0.05, 0.08), "wood")
        for x in (-1.2, 0.0, 1.2):
            p.box((x, f * 0.45, 4.4), (0.07, 0.07, 0.45), "timber")
    hinges = leaves(p, 1.38, 3.25, "plank")
    return None if p.static else door_mech(hinges)


def gate_adobe(p, W):
    for s in (-1, 1):
        p.box((s * 1.7, 0, 0.17), (0.72, 1.12, 0.34), "stone_dark")
        p.taper((s * 1.7, 0), (0.6, 1.0), (0.6, 0.86), 0.0, 3.3, "adobe")
        for f in (-1, 1):
            p.cyl((s * 1.7, f * 0.36, 2.5), (s * 1.7, f * 0.62, 2.5), 0.07, 0.07, "timber", seg=6)
    p.box((0, 0, 3.0), (3.2, 0.42, 0.3), "timber")
    for x in (-1.0, -0.33, 0.33, 1.0):
        p.cyl((x, -0.55, 3.2), (x, 0.55, 3.2), 0.07, 0.07, "timber", seg=6)
    p.box((0, 0, 3.55), (4.0, 0.8, 0.6), "adobe")
    p.box((0, -0.41, 3.55), (0.9, 0.03, 0.36), "adobe_light")
    p.xprism([(-0.54, 3.85), (0.54, 3.85), (0.54, 3.9), (0, 4.14), (-0.54, 3.9)], -2.06, 2.06, "roof")
    p.box((0, 0, 4.13), (4.12, 0.12, 0.08), "roof_dark")
    hinges = leaves(p, 1.38, 2.8, "plank")
    return None if p.static else door_mech(hinges)


def gate_low_masonry(p, W):
    """Walls without a walkway (whitewashed, rubble): pillars, a timber
    lintel and a small tiled roof."""
    t = W.t
    for s in (-1, 1):
        p.box((s * 1.7, 0, 0.22), (0.72, t + 0.42, 0.44), W.dark)
        W.block(p, s * 1.7 - 0.3, s * 1.7 + 0.3, -t / 2 - 0.15, t / 2 + 0.15, 0.0, 3.2, 0.0, proud_x=True)
        p.box((s * 1.7, 0, 3.26), (0.72, t + 0.42, 0.12), W.trim)
    p.box((0, 0, 3.02), (3.0, 0.4, 0.28), "timber")
    p.xprism([(-0.75, 3.3), (0.75, 3.3), (0.75, 3.36), (0, 3.85), (-0.75, 3.36)], -2.1, 2.1, "roof")
    p.box((0, 0, 3.86), (4.2, 0.14, 0.09), "roof_dark")
    hinges = leaves(p, 1.38, 2.82, "plank")
    return None if p.static else door_mech(hinges)


def gate_fieldstone(p, W):
    for s in (-1, 1):
        W.node(p.at(x=s * 1.6), set())
    hinges = leaves(p, 1.2, 1.15, "bars")
    p.box((0, 0.06, 0.6), (0.08, 0.06, 0.5), "iron")   # The latch.
    return None if p.static else door_mech(hinges, angle=95.0, seconds=1.2)


def gate_hedge(p, W):
    W.run(p, -2.0, -1.35)
    W.run(p, 1.35, 2.0)
    for s in (-1, 1):
        for f in (-1, 1):
            p.box((s * 1.28, f * 0.3, 1.35), (0.1, 0.1, 2.7), "wood")
        for z in (0.6, 1.3, 2.0):
            p.box((s * 1.28, 0, z), (0.05, 0.6, 0.05), "wood_light")
    for f in (-1, 1):
        p.box((0, f * 0.3, 2.7), (2.76, 0.1, 0.1), "wood")
    for x in (-0.9, -0.3, 0.3, 0.9):
        p.box((x, 0, 2.78), (0.06, 0.8, 0.06), "wood_light")
    W.run(p, -1.3, 1.3, floor=2.8, h=3.3)   # The hedge trained over the arch.
    hinges = leaves(p, 1.2, 1.2, "picket")
    return None if p.static else door_mech(hinges, angle=95.0, seconds=1.2)


def gate_reed(p, W):
    for s in (-1, 1):
        W.node(p.at(x=s * 1.7), set())
        p.cyl((s * 1.45, 0, 0), (s * 1.45, 0, 3.3), 0.09, 0.08, "bamboo_dark", seg=7)
    for z, r in ((2.75, 0.07), (3.05, 0.08)):
        p.cyl((-2.1, 0, z), (2.1, 0, z), r, r, "bamboo", seg=7)
    for x in (-1.0, -0.33, 0.33, 1.0):
        p.cyl((x, 0, 2.75), (x, 0, 3.05), 0.04, 0.04, "bamboo_dark", seg=5)
    p.box((0, -0.05, 2.45), (0.5, 0.03, 0.5), "cloth_green")
    hinges = leaves(p, 1.36, 2.1, "bars")
    return None if p.static else door_mech(hinges, angle=95.0, seconds=1.2)


def gate_for(key):
    W = WALLS[key]
    if isinstance(W, ReedWall):
        return lambda p: gate_reed(p, W)
    if isinstance(W, Palisade):
        return lambda p: gate_palisade(p, W)
    if isinstance(W, Adobe):
        return lambda p: gate_adobe(p, W)
    if isinstance(W, Fieldstone):
        return lambda p: gate_fieldstone(p, W)
    if isinstance(W, Hedge):
        return lambda p: gate_hedge(p, W)
    if W.walk is None:
        return lambda p: gate_low_masonry(p, W)
    return lambda p: gate_walkway(p, W, "iron" if key in ("iron", "darkelf", "dwarf") else "plank")


def broken_gate(key):
    """The gate of a wall type after raiders broke it: the damage state."""
    def make(p):
        BROKEN[0] = True
        try:
            gate_for(key)(Pen(p.mb, p.m, True))
        finally:
            BROKEN[0] = False
        W = WALLS[key]
        rubble(p, -1.2, 1.2, 0.5, ("wood", "door", "timber") + tuple(W.rubble_mats[:1]), "gate" + key, n=12, size=0.3)
        p.cyl((-0.9, -1.3, 0.2), (0.6, -0.5, 0.2), 0.2, 0.2, "log", seg=7)       # What is left of the ram.
        p.cyl((0.6, -0.5, 0.2), (0.85, -0.37, 0.2), 0.24, 0.16, "iron", seg=7)
        return None
    return make


def open_arch(key):
    """The gate of a wall type without its leaves: an archway 4 m wide for
    a road through an inner wall, with the wall walk passing over it."""
    def make(p):
        NO_LEAVES[0] = True
        try:
            gate_for(key)(Pen(p.mb, p.m, True))
        finally:
            NO_LEAVES[0] = False
        for i in range(5):   # The road's paving under the arch.
            p.box((-1.04 + i * 0.52, 0, 0.02), (0.5, 2.6, 0.04), "stone_dark" if i % 2 else "stone")
        return None
    return make


# --- Postern ---------------------------------------------------------------------------------


def postern(p, W, style=None):
    """A 2 m piece with a small door (0.95 x 1.75 m) through the wall."""
    style = style or W.door_style
    low = W.h < 2.2
    W.run(p, -1.0, -0.5)
    W.run(p, 0.5, 1.0)
    dh = 1.15 if low else 1.75
    if not low:
        W.run(p, -0.5, 0.5, floor=1.9)
        p.box((0, 0, 1.9), (1.2, W.t + 0.14, 0.2), W.frame_mat)
    for s in (-1, 1):
        p.box((s * 0.53, 0, (dh + 0.1) / 2), (0.12, W.t + 0.1 if not low else 0.14, dh + 0.1), W.frame_mat)
    door_leaf(p, -0.47, 0.0, 0.93, dh, +1, "door", style)
    if p.static:
        return None
    return door_mech([("door", (-0.47, 0.0), +1)], angle=95.0, seconds=1.0)


# --- Gatehouse -------------------------------------------------------------------------------


def gatehouse(p, W, bridge=False):
    """A stone gatehouse 6 x 4 m with a passage 2.8 m wide, an iron
    portcullis and, with `bridge`, a drawbridge on chains."""
    H = max(W.h + 2.4, 6.4)
    base = H - W.h
    for s in (-1, 1):
        p.box((s * 2.2, 0, 0.25), (1.76, 4.16, 0.5), W.dark)
        W.block(p, min(s * 1.4, s * 3.0), max(s * 1.4, s * 3.0), -2.0, 2.0, 0.0, H, 0.0, proud_x=True)
        # Slits on the front and doors to the wall walk on the sides.
        for z in (1.8, 4.3):
            p.box((s * 2.2, -2.02, z), (0.4, 0.1, 1.2), W.trim)
            p.box((s * 2.2, -2.05, z), (0.1, 0.08, 0.95), "dark")
        p.box((s * 3.0, 0, W.h + 0.95), (0.1, 1.0, 1.9), W.trim)
        p.box((s * 3.03, 0, W.h + 0.9), (0.08, 0.8, 1.8), "dark")
        for f in (-1, 1):   # Jambs and the corbels that round the arch.
            p.box((s * 1.45, f * 1.95, 1.7), (0.2, 0.22, 3.4), W.trim)
            p.box((s * 1.2, f * 1.95, 3.25), (0.4, 0.22, 0.4), W.trim)
            p.box((s * 0.95, f * 1.95, 3.42), (0.22, 0.22, 0.22), W.trim)
    W.block(p, -1.4, 1.4, -2.0, 2.0, 3.55, H, 0.0)
    for f in (-1, 1):
        p.box((0, f * 1.95, 3.7), (3.1, 0.24, 0.32), W.trim)
    p.box((0, -2.1, 3.75), (0.45, 0.12, 0.55), W.light)
    p.box((0, 0, H - 0.11), (6.2, 4.2, 0.22), W.dark)
    p.box((0, 0, H + 0.01), (5.7, 3.7, 0.05), W.walkmat)
    W.parapet(p.at(y=-(2.0 - W.half)), -3.1, 3.1, -1, base)
    W.parapet(p.at(y=2.0 - W.half), -3.1, 3.1, 1, base)
    W.parapet(p.at(x=3.0 - W.half, rot=90), -2.1, 2.1, -1, base, phase=0.0)
    W.parapet(p.at(x=-(3.0 - W.half), rot=270), -2.1, 2.1, -1, base, phase=0.0)
    # The town's banner over the arch.
    p.box((0, -2.14, H - 0.75), (0.9, 0.05, 1.3), "cloth_red")
    p.box((0, -2.18, H - 0.7), (0.4, 0.04, 0.4), "gold")
    # The portcullis, in its slot behind the front arch.
    w = {"portcullis": 1.0}
    y = -1.55
    for i in range(9):
        x = -1.28 + i * 0.32
        p.box((x, y, 1.8), (0.08, 0.08, 3.3), "iron", w)
        p.cyl((x, y, 0.15), (x, y, 0.0), 0.05, 0.0, "iron_dark", w, seg=4)
    for z in (0.45, 1.0, 1.55, 2.1, 2.65, 3.2):
        p.box((0, y, z), (2.7, 0.1, 0.07), "iron_dark", w)
    # The winch on the roof.
    for s in (-1, 1):
        p.box((s * 0.7, y, H + 0.4), (0.12, 0.3, 0.8), "timber")
    p.cyl((-0.8, y, H + 0.65), (0.8, y, H + 0.65), 0.1, 0.1, "wood", seg=8)
    p.cyl((0.8, y, H + 0.65), (1.05, y, H + 0.65), 0.03, 0.03, "iron", seg=5)
    pts = [brazier(p, s * 2.2, -2.3, 0.0, 2.0, bone) for s, bone in ((-1, "flame"), (1, "flame2"))]
    extra = [("portcullis", (0, y, 0.0), (0, y, 1.0), None)]
    if bridge:
        wb = {"bridge": 1.0}
        for i in range(7):   # The deck lies outward (toward -Y) when down.
            p.box((-1.2 + i * 0.4, -4.1, 0.17), (0.38, 4.0, 0.1), "wood" if i % 2 else "wood_light", wb)
        for yy in (-2.6, -4.2, -5.8):
            p.box((0, yy, 0.06), (2.9, 0.16, 0.12), "timber", wb)
        for s in (-1, 1):
            p.box((s * 1.36, -4.1, 0.28), (0.1, 4.0, 0.16), "timber", wb)
            p.beam((s * 1.3, -5.9, 0.25), (s * 1.3, -2.12, 4.6), 0.045, "iron_dark", wb)
            p.box((s * 1.3, -2.1, 4.6), (0.2, 0.12, 0.2), W.trim)
        extra.append(("bridge", (0, -2.1, 0.1), (0, -3.1, 0.1), None))
    if p.static:
        return None
    mech = flame_mech(pts, extra=extra)
    rise = 3.2

    def opened(t):
        moves = {"portcullis": (0, 0, rise * kit.smooth(t))}
        turns = {"bridge": [(kit.X, -78.0 * (1.0 - kit.smooth(t)))]} if bridge else {}
        return turns, moves

    mech.clip("open", 3.0, opened, loops=False)
    mech.clip("close", 3.0, lambda t: opened(1.0 - t), loops=False)
    return mech


# --- Registration ----------------------------------------------------------------------------

GATE_NAMES = [
    ("palisade", "Empalizada", "troncos"), ("plank", "Tablas con adarve", "troncos"),
    ("stone", "Sillería", "piedra"), ("brick", "Ladrillo", "ladrillo y piedra"), ("adobe", "Adobe", "arcilla"),
    ("iron", "Reforzada con hierro", "piedra y hierro"), ("fieldstone", "Piedra de campo (cancela)", "piedra"),
    ("hedge", "Seto (arco con cancela)", "seto vivo"), ("whitewash", "Tapia encalada", "piedra encalada y tejas"),
    ("cobble", "Mampostería", "piedra"), ("dwarf", "Enana", "piedra y oro"), ("elf", "Élfica", "piedra"),
    ("darkelf", "De elfos oscuros", "piedra y hierro"), ("sandstone", "Arenisca", "piedra"),
    ("orc", "Orca", "troncos y hierro"), ("reed", "De cañas", "cañas y arcilla"),
    ("stockade", "Empalizada doble", "troncos"), ("foxfolk", "De la gente zorro", "piedra, troncos y tejas"),
    ("catfolk", "De la gente gato", "arcilla y tejas"),
]
for key, nombre, material in GATE_NAMES:
    anim = dict(OPEN)
    if WALLS[key].walk is not None:
        anim["flicker"] = "Las llamas de los dos braseros se mueven"
    reg("gate_double", "gate_%s" % key, nombre, gate_for(key), material=material, anim=anim)

for key, nombre, material in GATE_NAMES:
    if key in ("palisade", "plank", "stone", "brick", "adobe", "iron", "stockade", "orc"):
        reg("gate_broken", "gate_%s_broken" % key, nombre, broken_gate(key), material=material)

for key, nombre, material in GATE_NAMES:
    if key not in ("fieldstone", "hedge", "reed"):
        reg("gate_arch", "gate_%s_arch" % key, nombre, open_arch(key), material=material)

POSTERN = {"open": "La puerta se abre hacia dentro", "close": "La puerta se cierra"}
for key, nombre, material in GATE_NAMES:
    if key == "hedge":
        continue
    reg("gate_postern", "gate_%s_postern" % key, nombre, (lambda p, W=WALLS[key]: postern(p, W)), material=material,
        anim=POSTERN)

PORT = {"open": "El rastrillo sube", "close": "El rastrillo baja", "flicker": "Las llamas de los braseros se mueven"}
for key, nombre, material in (("stone", "Sillería", "piedra"), ("brick", "Ladrillo", "ladrillo y piedra"),
                              ("iron", "Reforzada con hierro", "piedra y hierro"), ("dwarf", "Enana", "piedra y oro"),
                              ("elf", "Élfica", "piedra"), ("darkelf", "De elfos oscuros", "piedra y hierro"),
                              ("sandstone", "Arenisca", "piedra"),
                              ("foxfolk", "De la gente zorro", "piedra, troncos y tejas"),
                              ("catfolk", "De la gente gato", "arcilla y tejas")):
    reg("gate_gatehouse", "gate_%s_gatehouse" % key, nombre, (lambda p, W=WALLS[key]: gatehouse(p, W)),
        material=material, anim=PORT)
    reg("gate_drawbridge", "gate_%s_drawbridge" % key, nombre,
        (lambda p, W=WALLS[key]: gatehouse(p, W, bridge=True)), material=material,
        anim={"open": "El puente baja y el rastrillo sube", "close": "El puente se levanta y el rastrillo baja",
              "flicker": "Las llamas de los braseros se mueven"})
