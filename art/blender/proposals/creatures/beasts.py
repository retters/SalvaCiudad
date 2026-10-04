"""Wild and hostile four-legged beasts made with the quad generator: the
giant rat (and a plague rat), the dire wolf with bone spikes along its back
(and a brown warg), and the fox (red and arctic)."""

import math

from mathutils import Vector

import _parts as P
import quad

RAT_TAIL = ([(0, 0.5, 0.62), (0, 0.8, 0.5), (0, 1.1, 0.42), (0, 1.4, 0.4), (0, 1.7, 0.45)],
            [0.04, 0.032, 0.026, 0.02, 0.012])


def rat(name, fur, light, eye):
    colors = {**P.shades("fur", fur), **P.palette(light=light, dark=fur, pink=0xD9A0A0, eye=eye, nose=0xD9868A,
                                                  tooth=0xF2E8C8)}

    def coat(u, n):
        if u.z < quad.PAW_TOP * 1.4:
            return "pink"                         # Bare paws.
        if u.y < -0.9:
            return "pink"                         # The tip of the snout.
        if -0.5 < u.y < 0.5 and u.z < 0.5 and n.z < -0.2:
            return "light"
        return "fur"

    def teeth(spec, mb):
        tip = Vector(spec.snout_b)
        for s in (-1, 1):
            quad.tag(mb.box(spec.V(tip + Vector((s * 0.014, -0.02, -0.05))), (0.022 * spec.k, 0.014 * spec.k,
                                                                           0.05 * spec.k), "tooth"), "head")
        for s in (-1, 1):                         # Whiskers.
            for dz in (-0.01, 0.02):
                a = tip + Vector((s * 0.04, 0.0, dz))
                quad.tag(mb.cylinder(spec.V(a), spec.V(a + Vector((s * 0.16, 0.03, dz * 2))), 0.004 * spec.k,
                                     0.002 * spec.k, "tooth", segments=3), "head")

    return quad.Quad(name, colors, coat, k=0.5, leg=0.62, bulk=1.2, belly=1.25, head=0.95, snout=1.2,
                     snout_r=0.75, ruff=0.8, ears="round", ear_size=1.0, inner_ear="pink", tail=RAT_TAIL,
                     tail_detail="pink", clips=("attack",), eye=0.02, extra=teeth, sit_tail=0.0, lie_tail=0.0)


def dire_wolf(name, fur, light, dark, eye, k=1.3, bulk=1.2, spikes=True):
    colors = {**P.shades("fur", fur), **P.palette(light=light, dark=dark, eye=eye, nose=0x121014, bone=0xD8D0BC)}

    def extra(spec, mb):
        kk = spec.k
        if spikes:
            for i, (y, z) in enumerate(((-0.56, 0.99), (-0.44, 0.97), (-0.3, 0.87), (-0.14, 0.82), (0.04, 0.79),
                                        (0.22, 0.8), (0.4, 0.78))):
                size = 1.0 - 0.09 * i
                bone = "neck" if y < -0.42 else ("chest" if y < -0.02 else "body")
                quad.tag(mb.cylinder(spec.V((0, y, z - 0.05)), spec.V((0, y + 0.07, z + 0.15 * size)),
                                     0.04 * size * kk, 0.0, "bone", segments=4), bone)
        tip = Vector(spec.snout_b)
        for s in (-1, 1):                         # Fangs.
            quad.tag(mb.cylinder(spec.V(tip + Vector((s * 0.035, 0.01, -0.035))),
                                 spec.V(tip + Vector((s * 0.035, 0.0, -0.1))), 0.014 * kk, 0.0, "bone", segments=4),
                     "head")

    return quad.Quad(name, colors, quad.wolf_coat(socks=False, tail_tip="dark", muzzle=False), k=k, bulk=bulk,
                     head=1.15, neck=1.15, ruff=1.25, snout_r=1.15, ears="up", ear_size=0.9, leg_r=1.2,
                     clips=("attack", "howl"), extra=extra, max_tris=2000, budget=900, eye=0.02)


def fox(name, fur, light, dark, tip="light"):
    colors = {**P.shades("fur", fur), **P.palette(light=light, dark=dark, eye=0x1A1412, nose=0x1A1412)}
    return quad.Quad(name, colors, quad.wolf_coat(saddle=False, socks="dark", tail_tip=tip), k=0.52, snout_r=0.8,
                     ruff=0.85, ears="up", ear_size=1.3, tail=quad.TAIL_BRUSH, sit_tail=30.0, lie_tail=14.0,
                     leg_r=0.9)


SQUIRREL_TAIL = ([(0, 0.5, 0.66), (0, 0.74, 0.8), (0, 0.84, 1.08), (0, 0.72, 1.34), (0, 0.54, 1.42)],
                 [0.07, 0.13, 0.15, 0.13, 0.07])


def squirrel(name, fur, light):
    colors = {**P.shades("fur", fur), **P.palette(light=light, dark=P._mix(fur, 0x000000, 0.35), eye=0x151012,
                                                  nose=0x3A2A22, pink=0xE7A7A2)}

    def coat(u, n):
        if u.y < -0.82 and u.z < 0.86:
            return "light"
        if -0.5 < u.y < 0.5 and u.z < 0.56 and n.z < -0.1:
            return "light"
        if u.y < -0.38 and u.z < 0.72 and abs(u.x) < 0.12 and n.y < 0.2 and n.z < 0.4:
            return "light"
        return "fur"

    return quad.Quad(name, colors, coat, k=0.2, leg=0.72, head=1.25, snout=0.45, snout_r=0.9, ruff=0.75, bulk=1.1,
                     ears="up", ear_size=0.8, inner_ear="pink", tail=SQUIRREL_TAIL, clips=("sit",), sit_tail=0.0,
                     lie_tail=0.0, eye=0.024, budget=600, max_tris=1200)


def hedgehog(name):
    colors = {**P.shades("fur", 0x6A5440), **P.palette(light=0xD8C4A4, dark=0x3A2E24, eye=0x151012, nose=0x1E1C1E,
                                                       pink=0xE7A7A2, quill=0xE8DCC0)}

    def coat(u, n):
        if u.y < -0.45 or u.z < 0.5 or n.z < -0.1:
            return "light"                         # Face, legs and belly.
        return "fur"

    def quills(spec, mb):
        import random
        rnd = random.Random(5)
        for i in range(46):
            y = rnd.uniform(-0.42, 0.52)
            a = rnd.uniform(-1.25, 1.25)
            r = 0.2 if abs(y) < 0.35 else 0.15
            base = Vector((math.sin(a) * r * spec.bulk, y, 0.61 + math.cos(a) * 0.2))
            tip = base + Vector((math.sin(a) * 0.1, 0.07, math.cos(a) * 0.1 + 0.02))
            quad.tag(mb.cylinder(spec.V(base), spec.V(tip), 0.022 * spec.k, 0.0, "quill" if i % 3 else "dark",
                                 segments=3), "chest" if y < -0.02 else "body")

    return quad.Quad(name, colors, coat, k=0.16, leg=0.5, bulk=1.35, belly=1.3, head=0.9, snout=0.8, snout_r=0.7,
                     ruff=0.9, ears="round", ear_size=0.5, inner_ear="pink", tail=quad.TAIL_STUB, clips=(), eye=0.02,
                     extra=quills, sit_tail=0.0, lie_tail=0.0, budget=500, max_tris=1200)


def beaver(name):
    colors = {**P.shades("fur", 0x6A4A32), **P.palette(light=0x9A7A5A, dark=0x2E2420, eye=0x151012, nose=0x1E1C1E,
                                                       tooth=0xE8962A, pink=0xE7A7A2)}

    def coat(u, n):
        if u.y < -0.86 and u.z < 0.88:
            return "light"
        return "fur"

    def gear(spec, mb):
        k = spec.k
        pts = [(x, y, z) for x in (-0.14, 0.14) for y, z in ((0.55, 0.62), (0.75, 0.55), (1.05, 0.5), (1.15, 0.5))]
        quad.tag(P.hull(mb, [spec.V((x * (0.6 if y in (0.55, 1.15) else 1.0), y, z + dz)) for x, y, z in pts
                             for dz in (-0.02, 0.02)], "dark"), "tail.2")       # The flat paddle tail.
        tip = Vector(spec.snout_b)
        for s in (-1, 1):
            quad.tag(mb.box(spec.V(tip + Vector((s * 0.016, -0.03, -0.055))), (0.026 * k, 0.014 * k, 0.05 * k), "tooth"),
                     "head")

    return quad.Quad(name, colors, coat, k=0.42, leg=0.55, bulk=1.4, belly=1.35, head=1.05, snout=0.6, snout_r=1.2,
                     ruff=0.9, ears="round", ear_size=0.55, inner_ear="pink", clips=(),
                     tail=([(0, 0.5, 0.62), (0, 0.78, 0.55), (0, 1.08, 0.5)], [0.05, 0.045, 0.035]),
                     extra=gear, sit_tail=0.0, lie_tail=0.0, eye=0.018, snout_end=1.3)


def build(make, *args, **kw):
    return lambda: P.kit.build_zoo_spec(make(*args, **kw), P.FAMILY)


MODELS = {
    "enemy_giant_rat": build(rat, "enemy_giant_rat", 0x6E6259, 0x9A8E84, 0xC8302A),
    "enemy_giant_rat_plague": build(rat, "enemy_giant_rat_plague", 0x4A503C, 0x7A8060, 0xD8E04A),
    "enemy_dire_wolf": build(dire_wolf, "enemy_dire_wolf", 0x3A3C46, 0x6A6E78, 0x1E1E24, 0xE8B830),
    "enemy_winter_wolf": build(dire_wolf, "enemy_winter_wolf", 0xDCE4EC, 0xFFFFFF, 0xA8BCD0, 0x5AC8F0),
    "enemy_warg": build(dire_wolf, "enemy_warg", 0x6A4E36, 0x9A7A56, 0x3A2A20, 0xD8342A, k=1.45, bulk=1.35,
                        spikes=False),
    "animal_fox": build(fox, "animal_fox", 0xD9742A, 0xF4EEE4, 0x2A2422),
    "animal_fox_arctic": build(fox, "animal_fox_arctic", 0xECEEF0, 0xFFFFFF, 0xD8DCE0),
    "animal_hedgehog": build(hedgehog, "animal_hedgehog"),
    "animal_beaver": build(beaver, "animal_beaver"),
    "animal_squirrel": build(squirrel, "animal_squirrel", 0xB8622A, 0xF4EEE4),
    "animal_squirrel_gray": build(squirrel, "animal_squirrel_gray", 0x8A8A8E, 0xF0F0F0),
}
