"""Defenses that go with the walls: obstacles (cheval de frise, stakes,
caltrops, ditch), wall-top works (hoarding, machicolation, oil cauldron)
and lookouts (watch platform with an alarm bell, earth rampart)."""

import math

import _kit as kit
from registry import reg
from wallkit import add_flicker, brazier, flame_bones, ladder, rng
from walltypes import WALLS


def cheval(p, iron=False, length=2.0):
    """A cheval de frise: a log bristling with crossed, sharpened stakes."""
    h = 0.62
    p.cyl((-length / 2 + 0.05, 0, h), (length / 2 - 0.05, 0, h), 0.12, 0.12, "log", seg=8)
    for s in (-1, 1):
        p.cyl((s * (length / 2 - 0.05), 0, h), (s * (length / 2 - 0.03), 0, h), 0.1, 0.1, "log_end", seg=8)
    n = int(length / 0.32)
    for i in range(n):
        x = -length / 2 + 0.2 + i * (length - 0.4) / (n - 1)
        for s in (-1, 1):
            a = (x + s * 0.045, -s * 0.6, 0.02)
            b = (x + s * 0.045, s * 0.52, 1.14)
            tip = (x + s * 0.045, s * 0.62, 1.24)
            p.cyl(a, b, 0.045, 0.04, "wood", seg=6)
            p.cyl(b, tip, 0.04 if not iron else 0.05, 0.0, "iron" if iron else "log_end", seg=6)
        p.cyl((x - 0.1, 0, h), (x + 0.1, 0, h), 0.135, 0.135, "rope" if not iron else "iron_dark", seg=8)


def stakes(p, iron=False):
    """Two staggered rows of sharpened stakes leaning outward (-Y) from a
    low bank of earth, 2 m long."""
    p.xprism([(-0.7, 0.0), (0.7, 0.0), (0.45, 0.3), (-0.3, 0.3)], -1.0, 1.0, "soil")
    p.box((0, 0.075, 0.31), (2.0, 0.75, 0.03), "grass")
    r = rng("stakes", iron)
    for row, (y, n) in enumerate(((-0.25, 6), (0.2, 5))):
        for i in range(n):
            x = -1.0 + (i + 0.5 + 0.0 * row) * 2.0 / n
            lean = r.uniform(0.75, 0.95)
            ln = r.uniform(1.3, 1.6)
            a = (x, y + 0.25, 0.05)
            b = (x + r.uniform(-0.05, 0.05), y + 0.25 - lean * ln * 0.75, 0.05 + ln * 0.62)
            tip = tuple(b[k] + (b[k] - a[k]) * 0.16 for k in range(3))
            p.cyl(a, b, 0.065, 0.055, "log", seg=6)
            p.cyl(b, tip, 0.055, 0.0, "iron" if iron else "log_end", seg=6)


def caltrops(p):
    """A 2 x 2 m patch sown with iron caltrops."""
    p.taper((0, 0), (1.96, 1.96), (1.8, 1.8), 0.0, 0.03, "mud")
    r = rng("caltrops")
    dirs = [(0, 0, 1)] + [(0.94 * math.cos(a), 0.94 * math.sin(a), -0.33) for a in (0.5, 2.6, 4.7)]
    for i in range(34):
        x, y = r.uniform(-0.85, 0.85), r.uniform(-0.85, 0.85)
        q = p.at(x=x, y=y, rot=r.uniform(0, 360), z=0.065)
        for d in dirs:
            q.cyl((0, 0, 0), (d[0] * 0.11, d[1] * 0.11, d[2] * 0.11), 0.016, 0.0, "iron_dark" if i % 3 else "steel",
                  seg=4)
    for i in range(5):
        p.box((r.uniform(-0.8, 0.8), r.uniform(-0.8, 0.8), 0.04), (0.5, 0.05, 0.03), "hay", rz=r.uniform(0, 180))


GROUND = 1.5


def moat(p, water=False):
    """A ditch section 2 m long and 4 m wide (outside toward -Y) with a
    bank on the inner side, as a block of ground with the ditch cut in it."""
    x0, x1 = -1.0, 1.0
    p = p.at(z=GROUND)   # The model stands on its lowest point: the ground level is at Z = GROUND.
    p.xprism([(-2.0, -1.5), (-0.9, -1.5), (-0.9, -1.3), (-1.7, 0.0), (-2.0, 0.0)], x0, x1, "soil")
    p.xprism([(-0.9, -1.5), (0.3, -1.5), (0.3, -1.3), (-0.9, -1.3)], x0, x1, "mud")
    p.xprism([(0.3, -1.5), (2.0, -1.5), (2.0, 0.0), (1.1, 0.0), (0.3, -1.3)], x0, x1, "soil")
    p.xprism([(1.1, 0.0), (2.0, 0.0), (1.85, 0.75), (1.4, 0.75)], x0, x1, "soil")
    p.box((0, 1.625, 0.76), (2.0, 0.45, 0.04), "grass")
    p.box((0, -1.85, 0.0), (2.0, 0.3, 0.04), "grass")
    r = rng("moat", water)
    if water:
        p.box((0, -0.36, -0.45), (2.0, 2.5, 0.04), "water")
        for i in range(3):   # Reeds.
            x, y = r.uniform(-0.8, 0.8), r.uniform(0.5, 0.75)
            for k in range(3):
                p.cyl((x + k * 0.06, y, -0.5), (x + k * 0.07 + 0.03, y + 0.02, 0.25 + k * 0.1), 0.015, 0.008, "leaves",
                      seg=4)
    else:
        for i in range(7):   # Stakes planted in the bottom.
            x, y = -0.9 + i * 0.3, r.uniform(-0.7, 0.1)
            p.cyl((x, y, -1.3), (x + r.uniform(-0.1, 0.1), y - 0.12, -0.55), 0.05, 0.04, "log", seg=5)
            p.cyl((x, y - 0.12, -0.55), (x, y - 0.15, -0.35), 0.04, 0.0, "log_end", seg=5)
    for i in range(5):       # Stakes on the bank, pointing out.
        x = -0.8 + i * 0.4
        p.cyl((x, 1.5, 0.3), (x, 0.75, 0.85), 0.05, 0.045, "log", seg=5)
        p.cyl((x, 0.75, 0.85), (x, 0.6, 0.96), 0.045, 0.0, "log_end", seg=5)


def moat_bridge(p):
    """A plank footbridge over the ditch section."""
    moat(p, water=True)
    p = p.at(z=GROUND)
    for i in range(9):
        p.box((0, -1.9 + i * 0.4, 0.1), (1.5, 0.38, 0.07), "wood" if i % 2 else "wood_light")
    for s in (-1, 1):
        p.box((s * 0.65, -0.3, 0.02), (0.14, 3.7, 0.14), "timber")
        for y in (-1.9, -0.3, 1.3):
            p.box((s * 0.7, y, 0.55), (0.09, 0.09, 1.0), "timber")
        p.box((s * 0.7, -0.3, 1.0), (0.07, 3.3, 0.07), "wood")
    for y in (-0.9, 0.3):
        for s in (-1, 1):
            p.cyl((s * 0.6, y, -1.4), (s * 0.6, y, 0.0), 0.07, 0.07, "log", seg=6)


def hoarding(p, W):
    """A timber hoarding hung outside the battlements of a wall piece:
    defenders shoot and drop stones through its floor."""
    W.run(p, -1.0, 1.0)
    top = W.h
    yo = -(W.t / 2 + 0.1)
    out = 1.0
    for x in (-0.75, -0.25, 0.25, 0.75):
        p.box((x, yo - out / 2 + 0.25, top + 0.07), (0.14, out + 0.5, 0.14), "timber")
        p.beam((x, yo + 0.02, top - 1.0), (x, yo - out + 0.1, top - 0.02), 0.11, "timber")
    for i in range(3):
        p.box((0, yo - 0.32 - i * 0.26, top + 0.17), (2.0, 0.25, 0.06), "wood" if i % 2 else "wood_light")
    yf = yo - out
    for i in range(6):
        p.box((0, yf, top + 0.34 + i * 0.28), (2.0, 0.07, 0.27), "wood" if i % 2 else "wood_light")
    for x in (-0.5, 0.5):
        p.box((x, yf - 0.02, top + 1.2), (0.12, 0.08, 0.6), "dark")
        p.box((x, yf - 0.02, top + 1.2), (0.36, 0.08, 0.1), "dark")
    for x in (-0.94, 0.0, 0.94):
        p.box((x, yf + 0.02, top + 1.05), (0.12, 0.14, 1.9), "timber")
    zb = top + 2.75
    yb = W.t / 2 + 0.25
    for x in (-0.9, 0.9):
        p.box((x, W.t / 2 + 0.1 - 0.15, (top + 1.1 + zb) / 2 - 0.1), (0.12, 0.12, zb - top - 1.1), "timber")
        p.beam((x, yf, top + 1.95), (x, yb, zb - 0.06), 0.1, "timber")
    p.xprism([(yf - 0.2, top + 1.96), (yb, zb), (yb, zb + 0.08), (yf - 0.2, top + 2.04)], -1.0, 1.0, "wood")
    for i in range(4):
        y = yf - 0.1 + (i + 0.5) * (yb - yf) / 4
        z = top + 2.05 + (i + 0.5) * (zb - top - 1.96) / 4
        p.box((0, y, z + 0.03), (2.0, 0.05, 0.05), "timber")


def machicolation(p, W):
    """A wall piece whose outer parapet stands out on stone corbels, with
    murder holes in the floor between them."""
    W.run(p, -1.0, 1.0, sides=(1,))
    top = W.h
    y0 = -W.t / 2
    out = 0.6
    for x in (-0.75, -0.25, 0.25, 0.75):
        p.xprism([(y0 - out, top - 0.22), (y0, top - 1.15), (y0, top), (y0 - out, top)][::-1], x - 0.13, x + 0.13,
                 W.light)
        p.box((x, y0 - out * 0.5, top - 0.45), (0.3, out * 0.5, 0.12), W.dark)
    for x in (-0.5, 0.0, 0.5):   # The holes, dark, between the corbels.
        p.box((x, y0 - out * 0.45, top - 0.02), (0.22, out * 0.5, 0.04), "dark")
    p.box((0, y0 - out - 0.02, top - 0.1), (2.0, 0.3, 0.24), W.dark)
    q = p.at(y=-(out - 0.0))
    W.parapet(q, -1.0, 1.0, -1, 0.0)


def watch_platform(p, roof=True):
    """A lookout 2 x 2 m on four posts with an alarm bell."""
    H = 3.2
    for sx in (-1, 1):
        for sy in (-1, 1):
            p.cyl((sx * 0.85, sy * 0.85, 0), (sx * 0.78, sy * 0.78, H + (2.1 if roof else 1.1)), 0.09, 0.07, "log",
                  seg=6)
    for s in (-1, 1):
        p.beam((-0.84, s * 0.84, 0.3), (0.8, s * 0.8, H - 0.3), 0.07, "timber")
        p.beam((s * 0.84, 0.84, 0.3), (s * 0.8, -0.8, H - 0.3), 0.07, "timber")
        p.box((0, s * 0.8, H - 0.1), (1.9, 0.1, 0.12), "timber")
    for i in range(6):
        p.box((-0.83 + i * 0.33, 0, H), (0.31, 1.9, 0.07), "wood_light" if i % 2 else "wood")
    for d in range(4):
        q = p.at(rot=d * 90)
        if d != 2:
            q.box((0, -0.86, H + 0.55), (1.8, 0.05, 0.07), "wood")
            q.box((0, -0.86, H + 0.95), (1.8, 0.05, 0.07), "wood")
            for x in (-0.45, 0.0, 0.45):
                q.box((x, -0.86, H + 0.5), (0.05, 0.04, 0.9), "wood_light")
    ladder(p, (0.0, 1.75, 0.0), (0.0, 0.95, H + 0.4))
    if roof:
        p.taper((0, 0), (2.5, 2.5), (0.1, 0.1), H + 2.05, H + 2.9, "thatch")
        p.taper((0, 0), (1.5, 1.5), (0.05, 0.05), H + 2.42, H + 3.05, "thatch_dark")
    # The alarm bell on a bracket, toward the front.
    zb = H + 1.75
    p.box((0, -0.55, zb + 0.05), (0.08, 0.9, 0.08), "timber")
    w = {"bell": 1.0}
    p.cyl((0, -0.9, zb), (0, -0.9, zb - 0.1), 0.03, 0.03, "iron", w, seg=5)
    p.cyl((0, -0.9, zb - 0.1), (0, -0.9, zb - 0.38), 0.07, 0.17, "bell", w, seg=8)
    p.cyl((0, -0.9, zb - 0.38), (0, -0.9, zb - 0.42), 0.18, 0.18, "bell", w, seg=8)
    p.cyl((0, -0.9, zb - 0.3), (0, -0.9, zb - 0.5), 0.02, 0.035, "iron_dark", {"clapper": 1.0}, seg=5)
    p.cyl((0, -0.9, zb - 0.5), (0.02, -0.9, zb - 1.3), 0.012, 0.012, "rope", {"clapper": 1.0}, seg=4)
    if p.static:
        return None
    mech = kit.Mech([("bell", (0, -0.9, zb), (0, -0.9, zb - 0.4), None),
                     ("clapper", (0, -0.9, zb - 0.12), (0, -0.9, zb - 0.5), "bell")])
    mech.clip("ring", 1.0, lambda t: {
        "bell": [(kit.Y, 24 * math.sin(2 * math.pi * t))],
        "clapper": [(kit.Y, -34 * math.sin(2 * math.pi * t + 0.6))],
    })
    return mech


def rampart(p, palisade=True):
    """An earth bank 2 m long, 4 m wide and 1.4 m high, turfed, with a
    wattle revetment on the front and a palisade on top."""
    p.xprism([(-2.0, 0.0), (2.0, 0.0), (0.9, 1.4), (-0.6, 1.4)], -1.0, 1.0, "soil")
    p.xprism([(-0.62, 1.4), (0.92, 1.4), (0.9, 1.45), (-0.6, 1.45)], -1.0, 1.0, "grass")
    p.xprism([(0.9, 1.42), (2.02, 0.0), (2.1, 0.0), (0.95, 1.45)], -1.0, 1.0, "grass")
    for i in range(5):   # Wattle revetment on the outer slope.
        t = (i + 0.5) / 5
        p.box((0, -2.0 + 1.4 * t - 0.03, 1.4 * t), (2.0, 0.07, 0.22), "wattle" if i % 2 else "wattle_dark")
    for x in (-0.8, 0.0, 0.8):
        p.beam((x, -2.05, 0.0), (x, -0.62, 1.5), 0.07, "timber")
    if palisade:
        WALLS["palisade"].run(p.at(y=-0.2), -1.0, 1.0, base=1.4, floor=0.9)
        for i in range(5):   # A plank walk behind the palisade.
            p.box((-0.8 + i * 0.4, 0.4, 1.48), (0.38, 0.7, 0.06), "wood_light" if i % 2 else "wood")


def cauldron(p, W):
    """A wall piece with a cauldron of boiling oil on a pivot at an
    embrasure: the `pour` clip tips it outward."""
    W.run(p, -1.0, 1.0)
    top = W.h
    y = -(W.t / 2 - 0.25)
    zc = top + 0.95
    for s in (-1, 1):
        p.box((s * 0.32, y, top + 0.5), (0.08, 0.1, 1.0), "iron_dark")
    p.cyl((-0.4, y, zc), (0.4, y, zc), 0.03, 0.03, "iron", seg=5)
    w = {"pot": 1.0}
    p.cyl((0, y, zc - 0.3), (0, y, zc + 0.1), 0.17, 0.27, "iron_dark", w, seg=10)
    p.cyl((0, y, zc + 0.1), (0, y, zc + 0.14), 0.29, 0.29, "iron", w, seg=10)
    p.cyl((0, y, zc + 0.1), (0, y, zc + 0.15), 0.23, 0.23, "charcoal", w, seg=10)
    pt = brazier(p, 0.0, y, top + 0.05, 0.12)
    p.box((0.7, W.t / 2 - 0.45, top + 0.25), (0.4, 0.4, 0.4), "wood")   # A keg of oil.
    if p.static:
        return None
    names, bones = flame_bones([pt])
    mech = add_flicker(kit.Mech(bones + [("pot", (0, y, zc), (0, y, zc + 0.3), None)]), names)

    def pour(t):
        k = math.sin(math.pi * min(1.0, t / 0.8)) if t < 0.8 else 0.0
        return {"pot": [(kit.X, 95.0 * k)]}

    mech.clip("pour", 3.0, pour)
    return mech


def mantlet(p):
    """A wheeled wooden shield (mantlet) for archers outside the walls."""
    for i in range(6):
        p.yprism([(-0.9 + i * 0.3, 0.12), (-0.6 + i * 0.3 - 0.01, 0.12), (-0.6 + i * 0.3 - 0.01, 1.85),
                  (-0.9 + i * 0.3, 1.85)], -0.04, 0.04, "wood" if i % 2 else "wood_light")
    for z in (0.5, 1.5):
        p.box((0, -0.06, z), (1.84, 0.05, 0.1), "iron")
    p.box((0, -0.06, 1.2), (0.14, 0.06, 0.5), "dark")
    for s in (-1, 1):
        p.beam((s * 0.7, 0.05, 1.3), (s * 0.7, 1.1, 0.05), 0.08, "timber")
        p.cyl((s * 0.98, 0.0, 0.25), (s * 1.06, 0.0, 0.25), 0.25, 0.25, "timber", seg=10)
        p.cyl((s * 1.06, 0.0, 0.25), (s * 1.08, 0.0, 0.25), 0.07, 0.07, "iron", seg=6)
    p.cyl((-1.0, 0, 0.25), (1.0, 0, 0.25), 0.04, 0.04, "iron_dark", seg=5)


# --- Registration ----------------------------------------------------------------------------

reg("defense_cheval", "defense_cheval_wood", "Estacas de madera", lambda p: cheval(p), material="troncos")
reg("defense_cheval", "defense_cheval_iron", "Puntas de hierro", lambda p: cheval(p, iron=True),
    material="troncos y hierro")
reg("defense_cheval", "defense_cheval_long", "Largo (4 m)", lambda p: cheval(p, length=4.0), material="troncos")
reg("defense_stakes", "defense_stakes_wood", "Estacas de madera", lambda p: stakes(p), material="troncos")
reg("defense_stakes", "defense_stakes_iron", "Puntas de hierro", lambda p: stakes(p, iron=True),
    material="troncos y hierro")
reg("defense_caltrops", "defense_caltrops", "Abrojos de hierro", caltrops, material="hierro")
NOTE_MOAT = ("El modelo incluye el bloque de terreno: el nivel del suelo queda a 1,5 m y el fondo del foso en "
             "Z = 0. En el juego habría que hundir el terreno en vez de dibujar el bloque.")
reg("defense_moat", "defense_moat_stakes", "Seco, con estacas", lambda p: moat(p), material="tierra y troncos",
    nota=NOTE_MOAT)
reg("defense_moat", "defense_moat_water", "Con agua", lambda p: moat(p, water=True), material="tierra", nota=NOTE_MOAT)
reg("defense_moat", "defense_moat_bridge", "Con pasarela", moat_bridge, material="tierra y troncos", nota=NOTE_MOAT)
for key, nombre, material in (("stone", "Sillería", "piedra"), ("brick", "Ladrillo", "ladrillo y piedra"),
                              ("iron", "Reforzada con hierro", "piedra y hierro"), ("sandstone", "Arenisca", "piedra"),
                              ("dwarf", "Muralla enana", "piedra y oro"),
                              ("darkelf", "Muralla de elfos oscuros", "piedra y hierro"),
                              ("catfolk", "Muralla de la gente gato", "arcilla y tejas")):
    W_ = WALLS[key]
    reg("defense_hoarding", "defense_hoarding_%s" % key, "Sobre " + nombre.lower(),
        (lambda p, W=W_: hoarding(p, W)), material="troncos sobre " + material)
    reg("defense_machicolation", "defense_machicolation_%s" % key, nombre,
        (lambda p, W=W_: machicolation(p, W)), material=material)
    reg("defense_cauldron", "defense_cauldron_%s" % key, "Sobre " + nombre.lower(),
        (lambda p, W=W_: cauldron(p, W)), material="hierro sobre " + material,
        anim={"pour": "El caldero se vuelca hacia fuera y vuelve", "flicker": "El fuego bajo el caldero se mueve"})
reg("defense_watch", "defense_watch_platform", "Con techo de paja", lambda p: watch_platform(p), material="troncos",
    anim={"ring": "La campana de alarma repica"})
reg("defense_watch", "defense_watch_platform_open", "Abierta", lambda p: watch_platform(p, roof=False),
    material="troncos", anim={"ring": "La campana de alarma repica"})
reg("defense_rampart", "defense_rampart_palisade", "Con empalizada", lambda p: rampart(p), material="tierra y troncos")
reg("defense_rampart", "defense_rampart_bare", "Solo el terraplén", lambda p: rampart(p, palisade=False),
    material="tierra")
reg("defense_mantlet", "defense_mantlet", "Mantelete con ruedas", mantlet, material="troncos y hierro")
