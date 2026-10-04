"""Heraldry proposals: a flag, a war standard, a wall banner and a border
marker for each of the game's nine races. See ../LEEME.md.

    blender --background --factory-startup --python art/blender/proposals/heraldry/build.py -- [ids]
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import _kit as kit  # noqa: E402
import _shapes  # noqa: E402
import common  # noqa: E402
from _shapes import TAU, beam, rope, solid  # noqa: E402

FAMILY = "heraldry"
C = common.rgb
BASE = {
    **_shapes.COLORS,
    "bronze": C(0x9A7A3A), "paint_red": C(0xB8362E), "lime": C(0xB8E060), "bone": C(0xE0D8C0), "cave": C(0x14110F), "leaf": C(0x4E8A3C),
    "feather": C(0xC84A3A), "moss": C(0x5E8A3A),
}
# Cloth, second colour, emblem, the emblem itself, what tops the pole, and the stone or wood of the marker.
RACES = {
    "human": (0x2E5A9A, 0xECE6D6, 0xE0B84A, "tower", "cone", 0x9A938A),
    "catfolk": (0xD8892E, 0xF4E2B0, 0x7A3A1E, "sun", "disc", 0xD8B888),
    "dwarf": (0x8A2E2A, 0x3A3438, 0xC9A441, "hammer", "cube", 0x5E5A5E),
    "elf": (0x3E7A4A, 0xECE6D6, 0xF4F0E0, "leaf", "leaf", 0xE4E0D6),
    "dark_elf": (0x4A2E6A, 0x1E1A24, 0xC8C8D8, "moon", "spike", 0x2A2630),
    "foxfolk": (0xC0392B, 0xF4EDE0, 0xF4EDE0, "flame", "ball", 0xA83A2E),
    "frogfolk": (0x2E8A8A, 0x1E5A5A, 0xB8E060, "lily", "drop", 0x7A8A6A),
    "lizardfolk": (0x2E9A6A, 0xD8B040, 0xE8C850, "pyramid", "feathers", 0xC8A870),
    "orc": (0x3A2E2A, 0x8A2A22, 0xE0D8C0, "tusks", "skull", 0x6B4A2E),
}


def colors(race):
    main, second, emblem, _sign, _top, post = RACES[race]
    return {**BASE, "cloth": C(main), "cloth_second": C(second), "emblem": C(emblem), "post": C(post)}


def plate(mb, pts, cx, y, cz, depth, w, mat="emblem"):
    solid(mb, [(cx + px, y, cz + pz) for px, pz in pts], (0, depth, 0), mat, w)


def rect(x0, x1, z0, z1):
    return [(x0, z0), (x1, z0), (x1, z1), (x0, z1)]


def sign(mb, kind, cx, y, cz, s, depth, w):
    """The emblem of a race, drawn on a plane that faces along Y."""
    def p(pts):
        plate(mb, pts, cx, y, cz, depth, w)
    if kind == "tower":
        p(rect(-0.5 * s, 0.5 * s, -0.7 * s, 0.35 * s))
        p(rect(-0.75 * s, 0.75 * s, -0.95 * s, -0.7 * s))
        for x in (-0.5, -0.125, 0.25):
            p(rect(x * s, (x + 0.25) * s, 0.35 * s, 0.8 * s))
    elif kind == "sun":
        p([(math.cos(TAU * k / 10) * 0.5 * s, math.sin(TAU * k / 10) * 0.5 * s) for k in range(10)])
        for k in range(8):
            a = TAU * k / 8
            p([(math.cos(a - 0.18) * 0.62 * s, math.sin(a - 0.18) * 0.62 * s), (math.cos(a + 0.18) * 0.62 * s, math.sin(a + 0.18) * 0.62 * s), (math.cos(a) * s, math.sin(a) * s)])
    elif kind == "hammer":
        p(rect(-0.09 * s, 0.09 * s, -0.95 * s, 0.4 * s))
        p(rect(-0.65 * s, 0.65 * s, 0.35 * s, 0.9 * s))
    elif kind == "leaf":
        p([(0, -0.7 * s), (0.45 * s, -0.15 * s), (0.4 * s, 0.4 * s), (0, 0.95 * s), (-0.4 * s, 0.4 * s), (-0.45 * s, -0.15 * s)])
        p(rect(-0.05 * s, 0.05 * s, -0.95 * s, -0.7 * s))
    elif kind == "moon":
        n = 8
        for k in range(n):
            def at(u):
                a = math.radians(60 + 240 * u)
                o = (math.cos(a) * 0.9 * s, math.sin(a) * 0.9 * s)
                thin = 1 - 0.5 * math.sin(math.pi * u)
                return o, (o[0] * thin + 0.12 * s * math.sin(math.pi * u), o[1] * thin)
            (o0, i0), (o1, i1) = at(k / n), at((k + 1) / n)
            p([o0, o1, i1, i0])
    elif kind == "flame":
        p([(0, -0.9 * s), (0.5 * s, -0.3 * s), (0.35 * s, 0.25 * s), (-0.35 * s, 0.25 * s), (-0.5 * s, -0.3 * s)])
        p([(-0.35 * s, 0.25 * s), (0.35 * s, 0.25 * s), (0.12 * s, s)])
        p([(-0.5 * s, -0.3 * s), (-0.35 * s, 0.25 * s), (-0.72 * s, 0.55 * s)])
    elif kind == "lily":
        for k in range(8):
            a0, a1 = math.radians(35 + 290 * k / 8), math.radians(35 + 290 * (k + 1) / 8)
            p([(0, 0), (math.cos(a0) * 0.85 * s, math.sin(a0) * 0.85 * s), (math.cos(a1) * 0.85 * s, math.sin(a1) * 0.85 * s)])
    elif kind == "pyramid":
        p(rect(-0.9 * s, 0.9 * s, -0.8 * s, -0.35 * s))
        p(rect(-0.6 * s, 0.6 * s, -0.35 * s, 0.1 * s))
        p(rect(-0.3 * s, 0.3 * s, 0.1 * s, 0.55 * s))
        p([(math.cos(TAU * k / 8) * 0.2 * s, 0.8 * s + math.sin(TAU * k / 8) * 0.2 * s) for k in range(8)])
    else:   # Tusks.
        for sx in (-1, 1):
            p([(sx * 0.7 * s, -0.6 * s), (sx * 0.25 * s, -0.6 * s), (sx * 0.8 * s, 0.9 * s)])
        p(rect(-0.8 * s, 0.8 * s, -0.9 * s, -0.6 * s))


def finial(mb, kind, x, y, z, w=None):
    """What crowns the pole."""
    if kind == "cone":
        mb.cylinder((x, y, z), (x, y, z + 0.08), 0.09, 0.09, "gold", w, segments=6)
        mb.cylinder((x, y, z + 0.08), (x, y, z + 0.45), 0.07, 0.0, "gold", w, segments=6)
    elif kind == "disc":
        mb.sphere((x, y, z + 0.2), 0.2, "gold", w, segments=8, rings=5, scale=(1, 0.3, 1))
    elif kind == "cube":
        mb.box((x, y, z + 0.12), (0.22, 0.22, 0.24), "bronze", w)
        mb.box((x, y, z + 0.27), (0.3, 0.3, 0.06), "bronze", w)
    elif kind == "leaf":
        mb.cylinder((x, y, z), (x, y, z + 0.2), 0.03, 0.12, "leaf", w, segments=5)
        mb.cylinder((x, y, z + 0.2), (x, y, z + 0.55), 0.12, 0.0, "leaf", w, segments=5)
    elif kind == "spike":
        mb.sphere((x, y, z + 0.1), 0.1, "steel", w, segments=6, rings=4)
        mb.cylinder((x, y, z + 0.15), (x, y, z + 0.7), 0.04, 0.0, "steel", w, segments=5)
    elif kind == "ball":
        mb.sphere((x, y, z + 0.12), 0.13, "gold", w, segments=7, rings=5)
        mb.cylinder((x, y, z - 0.3), (x, y, z), 0.05, 0.02, "paint_red", w, segments=5)
    elif kind == "drop":
        mb.sphere((x, y, z + 0.14), 0.15, "lime", w, segments=7, rings=5, scale=(1, 1, 1.2))
    elif kind == "feathers":
        mb.sphere((x, y, z + 0.14), 0.16, "gold", w, segments=8, rings=5, scale=(1, 0.3, 1))
        for sx in (-1, 0, 1):
            solid(mb, [(x + sx * 0.08, y, z + 0.25), (x + sx * 0.3 + 0.07, y, z + 0.75), (x + sx * 0.3 - 0.07, y, z + 0.75)], (0, 0.02, 0), "feather" if sx else "lime", w)
    else:   # A skull.
        mb.sphere((x, y, z + 0.16), 0.17, "bone", w, segments=7, rings=5)
        mb.box((x, y - 0.1, z + 0.04), (0.16, 0.12, 0.1), "bone", w)
        for sx in (-1, 1):
            mb.box((x + sx * 0.07, y - 0.16, z + 0.18), (0.06, 0.03, 0.06), "cave", w)
            mb.cylinder((x + sx * 0.14, y, z + 0.2), (x + sx * 0.38, y, z + 0.5), 0.04, 0.0, "bone", w, segments=5)


def pole_foot(mb, race):
    post = "post"
    if race in ("orc", "foxfolk", "elf"):
        for k in range(5):
            a = TAU * k / 5
            mb.sphere((math.cos(a) * 0.3, math.sin(a) * 0.3, 0.08), 0.16, "stone" if k % 2 else "stone_dark", segments=5, rings=3)
    else:
        mb.cylinder((0, 0, 0), (0, 0, 0.3), 0.5, 0.42, post, segments=8)
        mb.cylinder((0, 0, 0.3), (0, 0, 0.5), 0.3, 0.24, post, segments=8)


def flag(race):
    def build():
        mb = kit.begin()
        _main, _second, _emblem, mark, top_kind, _post = RACES[race]
        pole_foot(mb, race)
        mb.cylinder((0, 0, 0), (0, 0, 6.6), 0.08, 0.05, "pole", segments=7)
        finial(mb, top_kind, 0, 0, 6.6)
        top, high, n = 6.4, 1.7, 3
        seg = 2.7 / n
        bones = []
        for k in range(n):
            x0, x1 = 0.06 + seg * k, 0.06 + seg * (k + 1)
            w = {"f%d" % k: 1.0}
            mb.box(((x0 + x1) / 2, 0, top - high / 2), (seg + 0.012, 0.03, high), "cloth", w)
            for z in (top - 0.14, top - high + 0.14):
                mb.box(((x0 + x1) / 2, 0, z), (seg + 0.014, 0.036, 0.16), "cloth_second", w)
            bones.append(("f%d" % k, (x0, 0, top - high / 2), (x1, 0, top - high / 2), "f%d" % (k - 1) if k else None))
        w = {"f%d" % (n - 1): 1.0}
        end = 0.06 + seg * n
        for z0, z1 in ((top, top - high / 2), (top - high / 2, top - high)):     # A swallowtail.
            solid(mb, [(end, -0.015, z0), (end + 0.5, -0.015, z0), (end, -0.015, z1)] if z0 == top else [(end, -0.015, z0), (end + 0.5, -0.015, z1), (end, -0.015, z1)],
                  (0, 0.03, 0), "cloth_second" if race in ("orc", "foxfolk", "dark_elf") else "cloth", w)
        mid = 0.06 + seg * 1.5
        sign(mb, mark, mid, -0.018, top - high / 2, 0.4, -0.012, {"f1": 1.0})
        sign(mb, mark, mid, 0.018, top - high / 2, 0.4, 0.012, {"f1": 1.0})
        for z in (top - 0.1, top - high + 0.1):
            mb.cylinder((0, -0.02, z), (0.1, -0.02, z), 0.02, 0.02, "rope", segments=4)

        def wave(t):
            return {"f%d" % k: [(kit.Z, (12.0 + 8.0 * k) * math.sin(TAU * t - 1.1 * k))] for k in range(n)}

        kit.save(mb, FAMILY, "banner_%s_flag" % race, colors(race), mech=kit.Mech(bones).clip("wave", 2.0, wave))
    return build


def hanging(mb, race, x, y, top, wide, long, s, front_only=True):
    """A banner hanging from a rod at `top`; returns its two bones."""
    mark = RACES[race][3]
    half = long * 0.55
    w0, w1 = {"b0": 1.0}, {"b1": 1.0}
    mb.box((x, y, top - half / 2), (wide, 0.03, half), "cloth", w0)
    mb.box((x, y, top - 0.1), (wide + 0.004, 0.036, 0.14), "cloth_second", w0)
    mb.box((x, y, top - half - (long - half) * 0.3), (wide, 0.03, (long - half) * 0.6 + 0.01), "cloth", w1)
    z = top - half - (long - half) * 0.6
    for sx in (-1, 1):                                                           # It ends in two points.
        solid(mb, [(x + sx * wide / 2, y - 0.015, z), (x, y - 0.015, z), (x + sx * wide / 2, y - 0.015, top - long)], (0, 0.03, 0), "cloth", w1)
        solid(mb, [(x + sx * wide / 2, y - 0.02, z - 0.02), (x + sx * wide * 0.3, y - 0.02, z - 0.02), (x + sx * wide / 2, y - 0.02, top - long + 0.12)], (0, 0.04, 0), "cloth_second", w1)
    mb.box((x, y, z + 0.12), (wide + 0.004, 0.036, 0.1), "emblem", w1)
    sign(mb, mark, x, y - 0.018, top - half * 0.55, s, -0.012, w0)
    if not front_only:
        sign(mb, mark, x, y + 0.018, top - half * 0.55, s, 0.012, w0)
    return [("b0", (x, y, top), (x, y, top - half), None), ("b1", (x, y, top - half), (x, y, top - long), "b0")]


def sway(t):
    return {"b0": [(kit.X, 5.0 * math.sin(TAU * t))], "b1": [(kit.X, 9.0 * math.sin(TAU * t - 1.0))]}


def standard(race):
    """What goes in front of the troops."""
    def build():
        mb = kit.begin()
        top_kind = RACES[race][4]
        mb.cylinder((0, 0, 0), (0, 0, 4.3), 0.06, 0.045, "pole", segments=7)
        mb.cylinder((0, 0, 0), (0, 0, 0.25), 0.03, 0.07, "iron", segments=6)
        beam(mb, (-0.75, 0, 4.05), (0.75, 0, 4.05), 0.04, "pole_dark")
        finial(mb, top_kind, 0, 0, 4.3)
        for sx in (-1, 1):
            mb.sphere((sx * 0.75, 0, 4.05), 0.07, "gold" if race != "orc" else "bone", segments=6, rings=4)
            rope(mb, (sx * 0.7, 0, 4.05), (0, 0, 4.3), 0.01)
            w = {"b0": 1.0}
            rope(mb, (sx * 0.62, -0.05, 4.0), (sx * 0.62, -0.05, 3.2), 0.012, w)                 # Tassels.
            mb.cylinder((sx * 0.62, -0.05, 3.2), (sx * 0.62, -0.05, 2.95), 0.02, 0.05, "emblem", w, segments=5)
        bones = hanging(mb, race, 0, -0.06, 4.0, 1.1, 2.3, 0.36, False)
        kit.save(mb, FAMILY, "banner_%s_standard" % race, colors(race), mech=kit.Mech(bones).clip("sway", 3.0, sway))
    return build


def wall_banner(race):
    """A long banner on its bracket; the wall it hangs from is behind it (+Y)."""
    def build():
        mb = kit.begin()
        for sx in (-0.5, 0.5):
            beam(mb, (sx, 0.3, 4.5), (sx, -0.2, 4.5), 0.03, "iron")
            beam(mb, (sx, 0.3, 4.1), (sx, -0.15, 4.5), 0.02, "iron")
        mb.cylinder((-0.7, -0.2, 4.5), (0.7, -0.2, 4.5), 0.035, 0.035, "pole_dark", segments=6)
        for sx in (-1, 1):
            mb.sphere((sx * 0.7, -0.2, 4.5), 0.06, "gold" if race != "orc" else "bone", segments=6, rings=4)
        bones = hanging(mb, race, 0, -0.2, 4.47, 1.2, 3.4, 0.4)
        kit.save(mb, FAMILY, "banner_%s_wall" % race, colors(race), mech=kit.Mech(bones).clip("sway", 4.0, sway))
    return build


def border(race):
    """Where one town's land ends."""
    def build():
        mb = kit.begin()
        _main, _second, _emblem, mark, top_kind, _post = RACES[race]
        if race in ("orc", "foxfolk", "elf"):                                    # A carved post.
            mb.cylinder((0, 0, 0), (0, 0, 1.5), 0.2, 0.16, "post", segments=7)
            mb.box((0, -0.12, 1.0), (0.5, 0.14, 0.6), "post")
            mb.box((0, 0, 1.55), (0.5, 0.4, 0.1), "plank_dark")
            sign(mb, mark, 0, -0.2, 1.0, 0.2, -0.015, None)
            finial(mb, top_kind, 0, 0, 1.6)
        else:   # A boundary stone.
            mb.box((0, 0, 0.1), (0.8, 0.6, 0.2), "stone_dark")
            mb.cylinder((0, 0, 0.2), (0, 0, 1.3), 0.36, 0.28, "post", segments=4)
            mb.cylinder((0, 0, 1.3), (0, 0, 1.5), 0.3, 0.0, "post", segments=4)
            mb.box((0, -0.24, 0.8), (0.4, 0.05, 0.5), "stone_dark")
            sign(mb, mark, 0, -0.27, 0.8, 0.16, -0.015, None)
            if race == "frogfolk":
                mb.sphere((0.15, -0.2, 0.3), 0.14, "moss", segments=5, rings=3)
                mb.sphere((-0.2, 0.15, 1.0), 0.12, "moss", segments=5, rings=3)
        mb.cylinder((0.45, 0.25, 0), (0.45, 0.25, 2.6), 0.035, 0.025, "pole", segments=6)
        w = {"pennant": 1.0}
        solid(mb, [(0.48, 0.235, 2.55), (1.3, 0.235, 2.3), (0.48, 0.235, 2.05)], (0, 0.03, 0), "cloth", w)
        solid(mb, [(0.48, 0.23, 2.42), (0.9, 0.23, 2.3), (0.48, 0.23, 2.18)], (0, 0.04, 0), "cloth_second", w)
        pose = lambda t: {"pennant": [(kit.Z, 18.0 * math.sin(TAU * t))]}   # noqa: E731
        mech = kit.Mech([("pennant", (0.48, 0.25, 2.3), (1.3, 0.25, 2.3), None)]).clip("flutter", 1.6, pose)
        kit.save(mb, FAMILY, "banner_%s_border" % race, colors(race), mech=mech)
    return build


MODELS = {}
for _race in RACES:
    MODELS["banner_%s_flag" % _race] = flag(_race)
    MODELS["banner_%s_standard" % _race] = standard(_race)
    MODELS["banner_%s_wall" % _race] = wall_banner(_race)
    MODELS["banner_%s_border" % _race] = border(_race)

kit.run(MODELS, FAMILY)
