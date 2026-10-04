"""A half-round mural tower, shutters between the merlons and an abatis."""

import math

import _kit as kit
import towers
import wall_models
from registry import reg
from wallkit import brazier, cone_roof, flame_mech, ladder, rng, scaffold
from walltypes import WALLS

# --- Mural tower -----------------------------------------------------------------------------


def tower_mural(p, W):
    """A half-round tower 4 m wide that stands out 1.9 m from a straight
    stretch of wall (outside toward -Y), level with the back face of the wall."""
    H = W.h + 2.2
    r = 1.9
    back = W.half
    arc = [(math.cos(math.radians(a)), math.sin(math.radians(a))) for a in range(180, 361, 30)]

    def shape(k):
        return [(r * k * x, r * k * y) for x, y in arc] + [(r * k, back), (-r * k, back)]

    p.prism(shape(1.12), 0.0, 0.5, W.dark)
    p.prism(shape(1.0), 0.0, H, W.mat)
    z, row = 0.9, 0
    rr = rng("mural", W.key)
    while z < H - 0.3:
        p.prism(shape(1.012), z, z + 0.05, W.dark)
        zt = min(z + W.course, H - 0.25)
        if zt - z > 0.2 and (W.course > 0.4 or row % 2 == 0):
            for j in range(2):
                a = math.radians(rr.uniform(195, 345))
                p.box(((r - 0.06) * math.cos(a), (r - 0.06) * math.sin(a), (z + zt) / 2 + 0.02),
                      (0.2, rr.uniform(0.4, 0.6), zt - z - 0.1), W.light if (row + j) % 3 else W.dark,
                      rz=math.degrees(a))
        z += W.course
        row += 1
    for zb in W.bands:
        p.prism(shape(1.02), zb - 0.07, zb + 0.07, W.band_mat)
    p.prism(shape(1.14), H - 0.26, H, W.dark)
    p.prism(shape(0.96), H, H + 0.04, W.walkmat)
    rp = r + 0.1
    wseg = 2 * (rp + 0.15) * math.tan(math.pi / 12) + 0.02
    for k in range(6):
        a = 180.0 + (k + 0.5) * 30.0
        q = p.at(rot=a + 90.0)
        q.box((0, -rp, H + 0.3), (wseg, 0.3, 0.6), W.mat)
        if k % 2 == 0 or k == 5:
            q.box((0, -rp, H + 0.85), (wseg * 0.8, 0.3, 0.5), W.mat)
            q.box((0, -rp, H + 1.13), (wseg * 0.8 + 0.06, 0.38, 0.07), W.trim)
    W.parapet(p, -r - 0.1, r + 0.1, 1, H - W.h, phase=0.0)
    for s in (-1, 1):
        p.box((s * rp, back / 2, H + 0.3), (0.3, back + 0.3, 0.6), W.mat)
    for a, zz in ((270, H - 1.6), (225, H - 1.6), (315, H - 1.6), (270, 2.0)):
        q = p.at(rot=a + 90.0)
        q.box((0, -r + 0.02, zz), (0.42, 0.14, 1.3), W.trim)
        q.box((0, -r - 0.02, zz), (0.1, 0.1, 1.05), "dark")
    p.box((0, back + 0.01, 0.96), (1.25, 0.14, 1.92), W.trim)
    p.box((0, back + 0.05, 0.9), (0.95, 0.1, 1.8), "door")
    towers.flag(p, 0.9, -0.3, H, 2.4)
    pt = towers.top_fire(p, H, 0.0, -0.7)
    if p.static:
        return None
    return flame_mech([pt])


for _key, _nombre, _mat in (("stone", "Sillería", "piedra"), ("brick", "Ladrillo", "ladrillo y piedra"),
                            ("iron", "Reforzada con hierro", "piedra y hierro"), ("sandstone", "Arenisca", "piedra"),
                            ("dwarf", "Enana", "piedra y oro"), ("darkelf", "De elfos oscuros", "piedra y hierro"),
                            ("catfolk", "De la gente gato", "arcilla y tejas")):
    reg("tower_mural", "tower_%s_mural" % _key, _nombre, (lambda p, W=WALLS[_key]: tower_mural(p, W)), material=_mat,
        anim={"flicker": "La llama del brasero se mueve"})


# --- Shutters between the merlons ------------------------------------------------------------


def shutters(p, W):
    """A straight whose middle crenel, on both faces, has a wooden shutter
    hung from a bar: `open` swings them out to shoot, `close` drops them."""
    W.run(p, -1.0, 1.0)
    top = W.h
    bones, names = [], []
    for s, name in ((-1, "shutter"), (1, "shutter2")):
        y = s * (W.half + 0.1)
        p.box((0, y, top + 1.12), (1.1, 0.08, 0.08), "timber")
        w = {name: 1.0}
        for i in range(3):
            p.box((-0.16 + i * 0.16, y + s * 0.03, top + 0.84), (0.15, 0.05, 0.5), "wood" if i % 2 else "wood_light", w)
        p.box((0, y + s * 0.06, top + 0.96), (0.5, 0.03, 0.06), "iron", w)
        p.box((0, y + s * 0.06, top + 0.7), (0.5, 0.03, 0.06), "iron", w)
        bones.append((name, (0, y, top + 1.1), (0, y, top + 0.6), None))
        names.append((name, s))
    if p.static:
        return None
    mech = kit.Mech(bones)

    def opened(t_):
        return {name: [(kit.X, s * 62.0 * kit.smooth(t_))] for name, s in names}

    mech.clip("open", 1.0, opened, loops=False)
    mech.clip("close", 1.0, lambda t_: opened(1.0 - t_), loops=False)
    return mech


for _key in ("stone", "brick", "iron", "sandstone", "dwarf", "darkelf", "foxfolk", "catfolk"):
    reg("wall_" + _key, "wall_%s_shutters" % _key, "Con manteletes en las almenas",
        (lambda p, W=WALLS[_key]: shutters(p, W)), material=wall_models.MATERIAL[_key],
        anim={"open": "Los manteletes se levantan hacia fuera", "close": "Los manteletes caen y tapan el hueco"})


# --- Abatis ----------------------------------------------------------------------------------


def abatis(p):
    """Felled trees laid side by side, their sharpened branches toward the
    enemy (-Y): a 2 m stretch, 3 m deep."""
    r = rng("abatis")
    for i in range(3):
        x = -0.7 + i * 0.7
        a = (x + r.uniform(-0.1, 0.1), 1.3, 0.2)
        b = (x + r.uniform(-0.25, 0.25), -0.9, 0.45 + 0.1 * i)
        p.cyl(a, b, 0.17, 0.09, "log", seg=7)
        p.cyl(a, (a[0], a[1] + 0.03, a[2]), 0.15, 0.15, "log_end", seg=7)
        for k in range(6):
            t = 0.25 + 0.13 * k
            o = tuple(a[j] + (b[j] - a[j]) * t for j in range(3))
            side = (-1 if k % 2 else 1) * r.uniform(0.35, 0.7)
            tip = (o[0] + side, o[1] - r.uniform(0.5, 0.9), o[2] + r.uniform(0.25, 0.75))
            mid = tuple(o[j] + (tip[j] - o[j]) * 0.8 for j in range(3))
            p.cyl(o, mid, 0.05, 0.035, "timber", seg=5)
            p.cyl(mid, tip, 0.035, 0.0, "log_end", seg=5)
        tip = (b[0], b[1] - 0.45, b[2] + 0.12)
        p.cyl(b, tip, 0.09, 0.0, "log_end", seg=6)
    for x in (-0.9, 0.9):   # Stakes that pin the trunks down.
        p.cyl((x, 0.9, 0.0), (x, 0.9, 0.7), 0.05, 0.04, "timber", seg=5)
    p.box((0, 0.9, 0.55), (1.9, 0.07, 0.07), "timber")


reg("defense_abatis", "defense_abatis", "Tala de árboles con ramas afiladas", abatis, material="troncos")


# --- A tower under construction ----------------------------------------------------------------


def tower_building(p, W):
    """The square tower half raised: scaffolds on two faces, a gin pole
    lifting a block and stone waiting at the foot."""
    size, hs = 3.6, 1.8
    hb = (W.h + 3.0) * 0.5
    p.taper((0, 0), (size + 0.6, size + 0.6), (size + 0.08, size + 0.08), 0.0, 0.9, W.dark)
    W.block(p, -hs, hs, -hs, hs, 0.0, hb, 0.0, proud_x=True)
    r = rng("tower_building", W.key)
    for i in range(9):   # The course being laid.
        a = i * 2 * math.pi / 9
        p.box((1.5 * math.cos(a), 1.5 * math.sin(a), hb + 0.15), (0.6, 0.4, 0.3), r.choice((W.mat, W.light)),
              rz=math.degrees(a) + 90)
    scaffold(p, -hs, hs, -hs, hb, side=-1)
    scaffold(p.at(rot=90), -hs, hs, -hs, hb, side=-1)
    p.beam((0.9, 0.9, hb), (-0.5, -0.5, hb + 2.8), 0.12, "timber")
    p.beam((0.9, -0.2, hb), (-0.5, -0.5, hb + 2.8), 0.08, "timber")
    p.cyl((-0.5, -0.5, hb + 2.75), (-0.5, -0.5, hb + 1.2), 0.02, 0.02, "rope", seg=4)
    p.box((-0.5, -0.5, hb + 1.0), (0.5, 0.4, 0.35), W.light)
    for i in range(8):
        p.box((r.uniform(-1.2, 1.2), hs + r.uniform(0.5, 1.1), 0.15 + 0.3 * (i % 2)), (0.55, 0.4, 0.3),
              r.choice(W.rubble_mats), rz=r.uniform(-15, 15))
    p.box((-2.6, 2.6, 0.2), (0.9, 0.6, 0.4), "wood")          # A mortar trough.
    p.box((-2.6, 2.6, 0.38), (0.8, 0.5, 0.06), "stone_light")


def tower_reed(p, roof=True):
    """The frogfolk's lookout: a platform of canes on eight stilts at
    4.2 m, with a cane rail, a ladder and a reed roof. 4 x 4 m."""
    H = 4.2
    stilts = [(1.6 * math.cos(a), 1.6 * math.sin(a)) for a in (math.pi * (k + 0.5) / 4 for k in range(8))]
    for x, y in stilts:
        p.cyl((x * 1.12, y * 1.12, 0), (x, y, H + (2.3 if roof else 1.1)), 0.09, 0.07, "bamboo", seg=6)
        p.cyl((x * 1.12, y * 1.12, 0), (x * 1.12, y * 1.12, 0.3), 0.2, 0.14, "mud", seg=6)
    for z, k in ((1.4, 1.08), (2.8, 1.04)):
        for i in range(8):
            a, b = stilts[i], stilts[(i + 1) % 8]
            p.beam((a[0] * k, a[1] * k, z), (b[0] * k, b[1] * k, z), 0.06, "bamboo_dark")
    for i in range(0, 8, 2):   # Cross braces on every other bay.
        a, b = stilts[i], stilts[(i + 1) % 8]
        p.beam((a[0] * 1.08, a[1] * 1.08, 1.4), (b[0] * 1.04, b[1] * 1.04, 2.8), 0.05, "bamboo_dark")
    p.cyl((0, 0, H - 0.12), (0, 0, H), 1.95, 1.95, "bamboo_dark", seg=8)
    for i in range(13):
        x = -1.8 + i * 0.3
        half = math.sqrt(max(0.05, 1.9 * 1.9 - x * x))
        p.cyl((x, -half, H + 0.05), (x, half, H + 0.05), 0.07, 0.07, "bamboo" if i % 2 else "bamboo_dark", seg=5)
    for z in (H + 0.55, H + 1.0):
        for i in range(8):
            if i == 1:   # The gap for the ladder, toward +Y.
                continue
            a, b = stilts[i], stilts[(i + 1) % 8]
            p.beam((a[0], a[1], z), (b[0], b[1], z), 0.05, "bamboo")
    for x, y in stilts:
        for z in (1.4, 2.8, H + 0.02):
            k = 1.12 - 0.12 * z / H
            p.cyl((x * k, y * k, z - 0.05), (x * k, y * k, z + 0.05), 0.11, 0.11, "rope", seg=6)
    ladder(p, (0.0, 3.0, 0.0), (0.0, 1.75, H + 0.3), mat="bamboo_dark")
    if roof:
        cone_roof(p, (0, 0), 2.5, H + 2.2, 1.9, mats=("thatch", "thatch_dark"), seg=8)
        p.cyl((0, 0, H + 2.15), (0, 0, H + 2.3), 1.75, 1.75, "bamboo_dark", seg=8)
        return None
    pt = brazier(p, 0.0, 0.0, H + 0.1, 1.2)
    if p.static:
        return None
    return flame_mech([pt])


reg("tower_wood", "tower_reed", "De cañas sobre pilotes, con techo", lambda p: tower_reed(p),
    material="cañas y paja")
reg("tower_wood", "tower_reed_open", "De cañas sobre pilotes, abierta", lambda p: tower_reed(p, roof=False),
    material="cañas", anim={"flicker": "La llama del brasero se mueve"})


def tower_damaged(p, W):
    """The square tower after a siege: the battlements gone on two sides,
    a hole torn in the front, charred beams and rubble at the foot."""
    size, hs = 3.6, 1.8
    H = W.h + 3.0
    p.taper((0, 0), (size + 0.6, size + 0.6), (size + 0.08, size + 0.08), 0.0, 0.9, W.dark)
    W.block(p, -hs, hs, -hs, hs, 0.0, H - 1.6, 0.0, proud_x=True)
    # What still stands of the top: the back and the left side, in ragged steps.
    for x0, x1, y0, y1, top in ((-hs, hs, 0.9, hs, H), (-hs, -0.7, -hs, 0.9, H - 0.5), (-0.7, 0.4, 0.2, 0.9, H - 0.9),
                                (0.9, hs, -0.2, 0.9, H - 1.1)):
        W.block(p, x0, x1, y0, y1, H - 1.6, top, H - 2.0, proud_x=True)
    W.parapet(p.at(y=hs + 0.05 - W.half), -hs - 0.15, 0.6, 1, H - W.h, phase=0.0)
    p.box((0.2, -hs - 0.02, H - 2.6), (1.5, 0.12, 1.5), "dark")             # The breach in the front.
    p.box((0.75, -hs - 0.03, H - 3.2), (0.7, 0.14, 0.6), "dark")
    for a, b in (((-0.5, -1.2, H - 1.6), (1.4, 0.3, H - 0.6)), ((0.2, -1.5, H - 1.7), (0.9, 1.0, H - 0.2)),
                 ((1.0, -1.7, H - 1.6), (1.9, -2.3, H - 3.0))):
        p.beam(a, b, 0.14, "charcoal")
    r = rng("tower_damaged", W.key)
    for i in range(16):
        s = r.uniform(0.25, 0.5)
        p.box((r.uniform(-1.6, 2.4), -hs - r.uniform(0.3, 1.5), s * 0.35), (s * 1.3, s, s * 0.7),
              r.choice(W.rubble_mats), rz=r.uniform(0, 90))
    towers.slit_on(p, W, "E", 0.9, 2.2, hs)
    towers.slit_on(p, W, "W", 0.9, 2.2, hs)
    towers.door_on(p, W, "N", 0.0, hs)


for _key, _nombre, _mat in (("stone", "Sillería", "piedra"), ("brick", "Ladrillo", "ladrillo y piedra"),
                            ("iron", "Reforzada con hierro", "piedra y hierro")):
    reg("tower_building", "tower_%s_building" % _key, _nombre + ", en construcción",
        (lambda p, W=WALLS[_key]: tower_building(p, W)), material=_mat)
    reg("tower_building", "tower_%s_damaged" % _key, _nombre + ", dañada",
        (lambda p, W=WALLS[_key]: tower_damaged(p, W)), material=_mat)
