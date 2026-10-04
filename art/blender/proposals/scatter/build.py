"""Ground scatter proposals: the small things that cover the terrain between
buildings: rocks, grass, flowers, bushes, what lies on the ground.
See ../LEEME.md.

    blender --background --factory-startup --python art/blender/proposals/scatter/build.py -- [ids]
"""

import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import _kit as kit  # noqa: E402
import _shapes  # noqa: E402
import common  # noqa: E402
from _shapes import TAU, beam, log, solid  # noqa: E402

FAMILY = "scatter"
C = common.rgb
COLORS = {
    **_shapes.COLORS,
    "moss": C(0x5E8A3A), "moss_dark": C(0x47702E), "sand_stone": C(0xC8A870), "sand_stone_dark": C(0xA88850), "sand_stone_light": C(0xDCC090),
    "grass": C(0x6A9440), "grass_light": C(0x86B050), "grass_dark": C(0x4E7A34), "grass_dry": C(0xC0A860), "grass_dry_dark": C(0x9A8448),
    "leaf": C(0x4E8A3C), "leaf_light": C(0x7AB050), "leaf_dark": C(0x386A30), "stem": C(0x5E8A3A), "reed": C(0x7A9A4A), "reed_head": C(0x6A4A2E),
    "petal_red": C(0xD8402E), "petal_yellow": C(0xF0C830), "petal_blue": C(0x4A7AD8), "petal_white": C(0xF4F0E8), "petal_violet": C(0x9A5AC8),
    "petal_pink": C(0xE88AA8), "heart": C(0x7A4A1E), "berry": C(0xC8283A), "berry_blue": C(0x3A4A9A), "thorn": C(0x6A5A40),
    "leaf_fall_a": C(0xD8792E), "leaf_fall_b": C(0xC84A2E), "leaf_fall_c": C(0xE0B040), "water": C(0x4A8FC0), "mud": C(0x6A5238), "soil": C(0x6A4A30),
    "soil_dark": C(0x4A3422), "cap_brown": C(0xA8763E), "cap_red": C(0xC83A2E), "cap_spot": C(0xF4F0E8), "stalk": C(0xE8E0CC), "bone": C(0xE0D8C0),
    "cave": C(0x14110F), "ice": C(0xD8ECF4),
}
STONES = {
    "stone": ("stone", "stone_dark", "stone_light"),
    "mossy": ("stone", "stone_dark", "moss"),
    "sandstone": ("sand_stone", "sand_stone_dark", "sand_stone_light"),
}


def lump(mb, x, y, z, r, mat, rnd, flat=0.75, w=None):
    mb.sphere((x, y, z), r, mat, w, segments=6, rings=4, scale=(rnd.uniform(0.85, 1.3), rnd.uniform(0.85, 1.3), flat * rnd.uniform(0.8, 1.2)))


def boulders(name, kind, size, seed):
    """A group of rocks: 0 a scatter of small ones, 1 a boulder with its chips, 2 an outcrop taller than a man."""
    def build():
        mb = kit.begin()
        rnd = random.Random(seed)
        a, b, c = STONES[kind]
        if size == 0:
            for _ in range(7):
                lump(mb, rnd.uniform(-0.9, 0.9), rnd.uniform(-0.9, 0.9), 0.05, rnd.uniform(0.12, 0.32), rnd.choice((a, b, a)), rnd)
        elif size == 1:
            lump(mb, 0, 0, 0.35, 0.8, a, rnd, 0.8)
            lump(mb, 0.7, 0.3, 0.2, 0.5, b, rnd)
            lump(mb, -0.6, -0.5, 0.15, 0.35, a, rnd)
            for _ in range(4):
                lump(mb, rnd.uniform(-1.3, 1.3), rnd.uniform(-1.2, 1.2), 0.05, rnd.uniform(0.1, 0.2), b, rnd)
            lump(mb, 0.05, 0.05, 0.85, 0.45, c, rnd, 0.35)
        else:
            for k, (x, y, h, r) in enumerate(((0, 0, 2.6, 1.0), (0.9, 0.4, 1.8, 0.8), (-0.8, 0.5, 1.4, 0.75), (0.2, -0.9, 1.0, 0.7), (-0.9, -0.6, 0.6, 0.55))):
                mb.cylinder((x, y, 0), (x + rnd.uniform(-0.15, 0.15), y + rnd.uniform(-0.15, 0.15), h), r, r * rnd.uniform(0.45, 0.7), a if k % 2 == 0 else b, segments=6)
                lump(mb, x, y, h, r * 0.55, c if k < 2 else a, rnd, 0.4)
            for _ in range(6):
                lump(mb, rnd.uniform(-1.9, 1.9), rnd.uniform(-1.8, 1.8), 0.08, rnd.uniform(0.15, 0.35), b, rnd)
        if kind == "mossy":
            for _ in range(3 + 2 * size):
                mb.sphere((rnd.uniform(-0.8, 0.8) * (0.6 + 0.5 * size), rnd.uniform(-0.8, 0.8) * (0.6 + 0.5 * size), 0.04), rnd.uniform(0.2, 0.4), "moss_dark", segments=5, rings=3,
                          scale=(1.3, 1.3, 0.25))
        kit.save(mb, FAMILY, name, COLORS)
    return build


def rock_arch():
    mb = kit.begin()
    rnd = random.Random(5)
    for sx in (-1, 1):
        mb.cylinder((sx * 2.2, 0, 0), (sx * 1.9, 0, 3.0), 1.1, 0.8, "sand_stone" if sx < 0 else "sand_stone_dark", segments=6)
    n = 7
    for i in range(n):
        a0, a1 = math.pi * i / n, math.pi * (i + 1) / n
        mb.cylinder((math.cos(a0) * 2.0, 0.1 * math.sin(3 * a0), 2.9 + math.sin(a0) * 1.3), (math.cos(a1) * 2.0, 0.1 * math.sin(3 * a1), 2.9 + math.sin(a1) * 1.3), 0.75, 0.75,
                    ("sand_stone", "sand_stone_light", "sand_stone_dark")[i % 3], segments=6)
    for _ in range(8):
        lump(mb, rnd.uniform(-3.2, 3.2), rnd.uniform(-1.6, 1.6), 0.1, rnd.uniform(0.2, 0.5), rnd.choice(("sand_stone", "sand_stone_dark")), rnd)
    kit.save(mb, FAMILY, "scatter_rock_arch", COLORS)


def rock_spires():
    mb = kit.begin()
    rnd = random.Random(6)
    for x, y, h, r in ((0, 0, 4.2, 0.7), (1.3, 0.6, 2.8, 0.55), (-1.1, 0.8, 2.0, 0.5), (0.5, -1.2, 1.4, 0.45)):
        z, k = 0.0, 0
        while z < h:
            step = rnd.uniform(0.35, 0.6)
            rr = r * (1 - 0.5 * z / h) * rnd.uniform(0.85, 1.15)
            mb.cylinder((x, y, z), (x, y, z + step), rr, rr * 0.92, ("sand_stone", "sand_stone_dark", "sand_stone_light")[k % 3], segments=6)
            z += step
            k += 1
        mb.cylinder((x, y, z), (x, y, z + 0.3), r * 0.75, r * 0.6, "stone_dark", segments=6)   # The hard cap that kept it standing.
    kit.save(mb, FAMILY, "scatter_rock_spires", COLORS)


def blades(mb, rnd, x, y, n, h, mats, spread, w=None, r=0.035):
    for _ in range(n):
        bx, by = x + rnd.uniform(-spread, spread), y + rnd.uniform(-spread, spread)
        lx, ly = rnd.uniform(-0.25, 0.25) * h, rnd.uniform(-0.25, 0.25) * h
        hh = h * rnd.uniform(0.6, 1.1)
        mb.cylinder((bx, by, 0), (bx + lx, by + ly, hh), r, 0.0, rnd.choice(mats), w, segments=3)


def sway(deg=6.0):
    return lambda t: ({"top": [(kit.X, deg * math.sin(TAU * t)), (kit.Y, deg * 0.5 * math.sin(TAU * t + 1.0))]}, {})


def grass(name, kind):
    def build():
        mb = kit.begin()
        rnd = random.Random(len(name))
        w = {"top": 1.0}
        if kind == "tuft":
            for k in range(5):
                blades(mb, rnd, rnd.uniform(-0.6, 0.6), rnd.uniform(-0.6, 0.6), 9, 0.4, ("grass", "grass_light", "grass_dark"), 0.12, w)
        elif kind == "dry":
            for k in range(5):
                blades(mb, rnd, rnd.uniform(-0.6, 0.6), rnd.uniform(-0.6, 0.6), 9, 0.5, ("grass_dry", "grass_dry_dark"), 0.12, w)
        elif kind == "tall":
            for k in range(9):
                blades(mb, rnd, rnd.uniform(-0.9, 0.9), rnd.uniform(-0.9, 0.9), 8, 1.1, ("grass", "grass_light", "grass_dry"), 0.15, w, 0.04)
        elif kind == "reeds":
            mb.cylinder((0, 0, 0), (0, 0, 0.03), 1.1, 1.1, "water", segments=9)
            for k in range(16):
                x, y = rnd.uniform(-0.8, 0.8), rnd.uniform(-0.8, 0.8)
                h = rnd.uniform(1.2, 1.9)
                lean = rnd.uniform(-0.1, 0.1)
                mb.cylinder((x, y, 0), (x + lean, y, h), 0.02, 0.015, "reed", w, segments=4)
                if k % 2:
                    mb.cylinder((x + lean, y, h - 0.1), (x + lean * 1.05, y, h + 0.2), 0.045, 0.04, "reed_head", w, segments=5)
                solid(mb, [(x, y - 0.01, 0.1), (x + 0.3, y - 0.01, 0.8), (x + 0.02, y - 0.01, 0.5)], (0, 0.02, 0), "reed", w)
        elif kind == "fern":
            for k in range(8):
                a = TAU * k / 8 + rnd.uniform(-0.2, 0.2)
                pts = [(0.1, 0.1), (0.4, 0.5), (0.8, 0.6), (1.1, 0.35)]
                for i, ((r0, z0), (r1, z1)) in enumerate(zip(pts, pts[1:])):
                    wide = 0.22 - 0.06 * i
                    solid(mb, [(math.cos(a) * r0 - math.sin(a) * wide, math.sin(a) * r0 + math.cos(a) * wide, z0), (math.cos(a) * r0 + math.sin(a) * wide, math.sin(a) * r0 - math.cos(a) * wide, z0),
                               (math.cos(a) * r1 + math.sin(a) * wide * 0.6, math.sin(a) * r1 - math.cos(a) * wide * 0.6, z1),
                               (math.cos(a) * r1 - math.sin(a) * wide * 0.6, math.sin(a) * r1 + math.cos(a) * wide * 0.6, z1)], (0, 0, 0.02), "leaf" if (k + i) % 2 else "leaf_dark", w)
        else:   # Clover.
            mb.cylinder((0, 0, 0), (0, 0, 0.04), 0.9, 0.9, "grass_dark", segments=9)
            for _ in range(40):
                x, y = rnd.uniform(-0.75, 0.75), rnd.uniform(-0.75, 0.75)
                mb.sphere((x, y, 0.08), 0.07, "grass_light" if rnd.random() < 0.7 else "leaf", w, segments=4, rings=3, scale=(1, 1, 0.4))
            for _ in range(6):
                x, y = rnd.uniform(-0.7, 0.7), rnd.uniform(-0.7, 0.7)
                mb.cylinder((x, y, 0.05), (x, y, 0.2), 0.008, 0.008, "stem", w, segments=3)
                mb.sphere((x, y, 0.22), 0.04, "petal_white", w, segments=4, rings=3)
        mech = kit.Mech([("top", (0, 0, 0), (0, 0, 0.5), None)]).clip("sway", 3.0, sway(3.0 if kind in ("fern", "clover") else 6.0))
        kit.save(mb, FAMILY, name, COLORS, mech=mech)
    return build


def flowers(name, petals, tall=False):
    def build():
        mb = kit.begin()
        rnd = random.Random(len(name) * 7)
        w = {"top": 1.0}
        blades(mb, rnd, 0, 0, 30, 0.25, ("grass", "grass_light"), 0.8, w, 0.03)
        n = 9 if tall else 16
        for k in range(n):
            x, y = rnd.uniform(-0.75, 0.75), rnd.uniform(-0.75, 0.75)
            h = rnd.uniform(1.3, 1.9) if tall else rnd.uniform(0.25, 0.5)
            mat = petals[k % len(petals)]
            mb.cylinder((x, y, 0), (x, y, h), 0.03 if tall else 0.012, 0.02 if tall else 0.01, "stem", w, segments=4)
            if tall:   # A sunflower: a dark heart in a ring of petals, facing the sun.
                mb.cylinder((x, y - 0.02, h), (x, y - 0.06, h + 0.02), 0.13, 0.13, "heart", w, segments=8)
                for i in range(8):
                    a = TAU * i / 8
                    solid(mb, [(x + math.cos(a - 0.3) * 0.13, y - 0.04, h + math.sin(a - 0.3) * 0.13), (x + math.cos(a + 0.3) * 0.13, y - 0.04, h + math.sin(a + 0.3) * 0.13),
                               (x + math.cos(a) * 0.3, y - 0.04, h + math.sin(a) * 0.3)], (0, 0.015, 0), mat, w)
                solid(mb, [(x, y, h * 0.5), (x + 0.3, y, h * 0.55), (x + 0.05, y, h * 0.62)], (0, 0.02, 0), "leaf", w)
            else:
                mb.sphere((x, y, h + 0.02), 0.07, mat, w, segments=5, rings=3, scale=(1, 1, 0.6))
                mb.sphere((x, y, h + 0.05), 0.03, "petal_yellow" if mat != "petal_yellow" else "heart", w, segments=4, rings=3)
        mech = kit.Mech([("top", (0, 0, 0), (0, 0, 0.5), None)]).clip("sway", 3.0, sway(4.0))
        kit.save(mb, FAMILY, name, COLORS, mech=mech)
    return build


def bush(name, kind):
    def build():
        mb = kit.begin()
        rnd = random.Random(len(name) * 3)
        thorn = kind == "thorn"
        mats = ("thorn", "leaf_dark") if thorn else ("leaf", "leaf_light", "leaf_dark")
        blobs = []
        for k in range(7):
            a = TAU * k / 7
            r = 0.0 if k == 0 else 0.55
            p = (math.cos(a) * r, math.sin(a) * r, 0.45 + (0.35 if k == 0 else rnd.uniform(-0.1, 0.1)))
            s = rnd.uniform(0.42, 0.6)
            blobs.append((p, s))
            mb.sphere(p, s, mats[k % len(mats)], segments=6, rings=4, scale=(1, 1, 0.8))
        mb.cylinder((0, 0, 0), (0, 0, 0.4), 0.07, 0.05, "bark", segments=5)
        if thorn:
            for _ in range(16):
                p, s = rnd.choice(blobs)
                a, b = rnd.uniform(0, TAU), rnd.uniform(0.2, 1.2)
                d = (math.cos(a) * math.cos(b), math.sin(a) * math.cos(b), math.sin(b))
                mb.cylinder((p[0] + d[0] * s * 0.8, p[1] + d[1] * s * 0.8, p[2] + d[2] * s * 0.6), (p[0] + d[0] * (s + 0.25), p[1] + d[1] * (s + 0.25), p[2] + d[2] * (s * 0.8 + 0.25)),
                            0.03, 0.0, "stone_light", segments=4)
        dots = {"flowers": ("petal_white", "petal_pink"), "berries": ("berry",), "blueberries": ("berry_blue",)}.get(kind)
        if dots:
            for _ in range(22):
                p, s = rnd.choice(blobs)
                a, b = rnd.uniform(0, TAU), rnd.uniform(0.0, 1.3)
                d = (math.cos(a) * math.cos(b), math.sin(a) * math.cos(b), math.sin(b) * 0.8)
                mb.sphere((p[0] + d[0] * s, p[1] + d[1] * s, p[2] + d[2] * s), 0.05 if kind != "flowers" else 0.06, rnd.choice(dots), segments=4, rings=3)
        kit.save(mb, FAMILY, name, COLORS)
    return build


def leaves_pile():
    mb = kit.begin()
    rnd = random.Random(11)
    mb.sphere((0, 0, 0), 0.9, "leaf_fall_a", segments=8, rings=4, scale=(1.2, 1.0, 0.35))
    for _ in range(40):
        a, d = rnd.uniform(0, TAU), rnd.uniform(0, 1.5)
        z = max(0.02, 0.32 * (1 - d / 1.1))
        mb.box((math.cos(a) * d, math.sin(a) * d, z), (0.14, 0.1, 0.02), rnd.choice(("leaf_fall_a", "leaf_fall_b", "leaf_fall_c")), rotation_z=rnd.uniform(0, 3))
    beam(mb, (0.6, -0.5, 0.05), (1.5, -1.3, 0.6), 0.02, "pole")                   # A rake left in it.
    mb.box((0.6, -0.5, 0.06), (0.4, 0.04, 0.04), "pole_dark", rotation_z=0.7)
    kit.save(mb, FAMILY, "scatter_leaves_pile", COLORS)


def puddle():
    mb = kit.begin()
    rnd = random.Random(12)
    for x, y, r in ((0, 0, 0.9), (0.7, 0.4, 0.6), (-0.6, -0.5, 0.5)):
        mb.cylinder((x, y, 0), (x, y, 0.02), r + 0.12, r + 0.12, "mud", segments=9)
        mb.cylinder((x, y, 0), (x, y, 0.03), r, r, "water", segments=9)
    for _ in range(5):
        lump(mb, rnd.uniform(-1.2, 1.2), rnd.uniform(-1.0, 1.0), 0.03, 0.08, "stone", rnd)
    w = {"ripple": 1.0}
    for r in (0.25, 0.45):
        for i in range(8):
            a0, a1 = TAU * i / 8, TAU * (i + 1) / 8
            beam(mb, (math.cos(a0) * r, math.sin(a0) * r, 0.035), (math.cos(a1) * r, math.sin(a1) * r, 0.035), 0.008, "ice", w)
    pose = lambda t: ({"ripple": [(kit.Z, 45.0 * t)]}, {"ripple": (0, 0, -0.012 * (0.5 - 0.5 * math.cos(TAU * t)))})   # noqa: E731
    kit.save(mb, FAMILY, "scatter_puddle", COLORS, mech=kit.Mech([("ripple", (0, 0, 0.03), (0, 0, 0.3), None)]).clip("drip", 2.0, pose))


def molehills():
    mb = kit.begin()
    rnd = random.Random(13)
    for k in range(5):
        x, y = rnd.uniform(-1.3, 1.3), rnd.uniform(-1.3, 1.3)
        mb.cylinder((x, y, 0), (x, y, 0.22), 0.34, 0.1, "soil" if k % 2 else "soil_dark", segments=7)
        for _ in range(4):
            lump(mb, x + rnd.uniform(-0.35, 0.35), y + rnd.uniform(-0.35, 0.35), 0.02, 0.06, "soil_dark", rnd)
    w = {"mole": 1.0}
    mb.sphere((0.0, 0.0, 0.1), 0.1, "pole_dark", w, segments=6, rings=4)           # One looks out.
    mb.sphere((0.0, -0.09, 0.12), 0.03, "petal_pink", w, segments=4, rings=3)
    mb.cylinder((0, 0, 0), (0, 0, 0.2), 0.36, 0.14, "soil", segments=7)
    pose = lambda t: ({}, {"mole": (0, 0, 0.16 * max(0.0, math.sin(TAU * t)) - 0.05)})   # noqa: E731
    kit.save(mb, FAMILY, "scatter_molehills", COLORS, mech=kit.Mech([("mole", (0, 0, 0.1), (0, 0, 0.3), None)]).clip("peek", 4.0, pose))


def tracks(name, kind):
    """Prints pressed in the ground: they say what passed and which way."""
    def build():
        mb = kit.begin()
        for k in range(7):
            y = -1.5 + 0.5 * k
            x = 0.12 if k % 2 else -0.12
            if kind == "wolf":
                mb.cylinder((x, y, 0), (x, y, 0.012), 0.07, 0.07, "soil_dark", segments=6)
                for i in range(4):                                               # Four toes ahead of the pad.
                    a = math.radians(60 + 20 * i)
                    tx, ty = x + 0.09 * math.cos(a), y - 0.09 * math.sin(a)
                    mb.cylinder((tx, ty, 0), (tx, ty, 0.012), 0.028, 0.028, "soil_dark", segments=5)
            elif kind == "boot":
                mb.box((x * 1.6, y, 0.006), (0.12, 0.2, 0.012), "soil_dark")
                mb.box((x * 1.6, y + 0.16, 0.006), (0.1, 0.08, 0.012), "soil_dark")
            else:   # Something with three long claws.
                for i in (-1, 0, 1):
                    beam(mb, (x * 3, y + 0.25, 0.01), (x * 3 + i * 0.28, y - 0.35, 0.01), 0.035, "soil_dark")
                mb.cylinder((x * 3, y + 0.28, 0), (x * 3, y + 0.28, 0.015), 0.16, 0.16, "soil_dark", segments=6)
        kit.save(mb, FAMILY, name, COLORS)
    return build


def mossy_log():
    mb = kit.begin()
    rnd = random.Random(14)
    log(mb, (-1.6, 0, 0.3), (1.6, 0.2, 0.28), 0.3)
    mb.cylinder((-1.62, 0, 0.3), (-1.55, 0, 0.3), 0.2, 0.2, "cave", segments=7)   # Hollow at one end.
    for _ in range(7):
        x = rnd.uniform(-1.3, 1.3)
        mb.sphere((x, 0.02 + 0.06 * x, 0.52), rnd.uniform(0.2, 0.35), "moss" if rnd.random() < 0.6 else "moss_dark", segments=5, rings=3, scale=(1.4, 0.8, 0.35))
    for k in range(5):
        x = -0.8 + 0.4 * k
        mb.cylinder((x, -0.28, 0.3), (x, -0.4, 0.34), 0.03, 0.02, "stalk", segments=4)
        mb.cylinder((x, -0.36, 0.33), (x, -0.44, 0.4), 0.11, 0.02, "cap_brown", segments=6)
    beam(mb, (0.6, 0.1, 0.5), (0.9, 0.5, 1.1), 0.03, "bark")
    kit.save(mb, FAMILY, "scatter_log_mossy", COLORS)


def mushrooms(name, red):
    def build():
        mb = kit.begin()
        rnd = random.Random(15 + red)
        for k in range(7):
            x, y = rnd.uniform(-0.6, 0.6), rnd.uniform(-0.6, 0.6)
            h = rnd.uniform(0.12, 0.4)
            r = h * rnd.uniform(0.45, 0.7)
            mb.cylinder((x, y, 0), (x, y, h), r * 0.3, r * 0.22, "stalk", segments=5)
            mb.cylinder((x, y, h - 0.02), (x, y, h + r * 0.6), r, r * 0.15, "cap_red" if red else "cap_brown", segments=7)
            if red:
                for i in range(4):
                    a = TAU * i / 4 + k
                    mb.sphere((x + math.cos(a) * r * 0.5, y + math.sin(a) * r * 0.5, h + r * 0.3), r * 0.14, "cap_spot", segments=4, rings=3)
        blades(mb, rnd, 0, 0, 14, 0.2, ("grass", "grass_dark"), 0.7)
        kit.save(mb, FAMILY, name, COLORS)
    return build


def roots():
    mb = kit.begin()
    rnd = random.Random(16)
    for k in range(6):
        a = TAU * k / 6 + rnd.uniform(-0.2, 0.2)
        pts = [(0.2, 0.35), (0.8, 0.25), (1.5, 0.3), (2.1, 0.05)]
        for i, ((r0, z0), (r1, z1)) in enumerate(zip(pts, pts[1:])):
            b = a + 0.15 * i * (1 if k % 2 else -1)
            mb.cylinder((math.cos(b) * r0, math.sin(b) * r0, z0), (math.cos(b + 0.15) * r1, math.sin(b + 0.15) * r1, z1), 0.16 - 0.04 * i, 0.12 - 0.04 * i, "bark", segments=5)
    mb.cylinder((0, 0, 0), (0, 0, 0.5), 0.5, 0.36, "bark", segments=7)
    for _ in range(5):
        mb.sphere((rnd.uniform(-1.5, 1.5), rnd.uniform(-1.5, 1.5), 0.05), 0.2, "moss", segments=5, rings=3, scale=(1.3, 1.3, 0.3))
    kit.save(mb, FAMILY, "scatter_roots", COLORS)


def ice_patch():
    mb = kit.begin()
    for k, (x, y, r) in enumerate(((0, 0, 1.2), (0.9, 0.5, 0.7), (-0.8, -0.6, 0.6))):
        mb.cylinder((x, y, 0), (x, y, 0.03), r, r, "ice", segments=8)
    for k in range(4):
        a = TAU * k / 4 + 0.4
        beam(mb, (0, 0, 0.035), (math.cos(a) * 0.9, math.sin(a) * 0.9, 0.035), 0.01, "petal_white")
    for k in range(5):
        a = TAU * k / 5
        mb.cylinder((math.cos(a) * 1.3, math.sin(a) * 1.2, 0), (math.cos(a) * 1.3, math.sin(a) * 1.2, 0.3 + 0.1 * (k % 2)), 0.08, 0.0, "ice", segments=4)
    kit.save(mb, FAMILY, "scatter_ice_patch", COLORS)


MODELS = {}
for _kind in STONES:
    for _size, _label in enumerate(("small", "boulder", "outcrop")):
        _name = "scatter_rocks_%s_%s" % (_kind, _label)
        MODELS[_name] = boulders(_name, _kind, _size, len(_kind) * 10 + _size)
MODELS.update({
    "scatter_rock_arch": rock_arch, "scatter_rock_spires": rock_spires,
    "scatter_grass_tuft": grass("scatter_grass_tuft", "tuft"), "scatter_grass_dry": grass("scatter_grass_dry", "dry"),
    "scatter_grass_tall": grass("scatter_grass_tall", "tall"), "scatter_reeds": grass("scatter_reeds", "reeds"),
    "scatter_fern": grass("scatter_fern", "fern"), "scatter_clover": grass("scatter_clover", "clover"),
    "scatter_flowers_red": flowers("scatter_flowers_red", ("petal_red",)), "scatter_flowers_yellow": flowers("scatter_flowers_yellow", ("petal_yellow",)),
    "scatter_flowers_blue": flowers("scatter_flowers_blue", ("petal_blue", "petal_violet")), "scatter_flowers_white": flowers("scatter_flowers_white", ("petal_white",)),
    "scatter_flowers_mixed": flowers("scatter_flowers_mixed", ("petal_red", "petal_yellow", "petal_blue", "petal_white", "petal_pink")),
    "scatter_sunflowers": flowers("scatter_sunflowers", ("petal_yellow",), True),
    "scatter_bush": bush("scatter_bush", "plain"), "scatter_bush_flowers": bush("scatter_bush_flowers", "flowers"),
    "scatter_bush_berries": bush("scatter_bush_berries", "berries"), "scatter_bush_blueberries": bush("scatter_bush_blueberries", "blueberries"),
    "scatter_bush_thorn": bush("scatter_bush_thorn", "thorn"),
    "scatter_leaves_pile": leaves_pile, "scatter_puddle": puddle, "scatter_molehills": molehills,
    "scatter_tracks_wolf": tracks("scatter_tracks_wolf", "wolf"), "scatter_tracks_boot": tracks("scatter_tracks_boot", "boot"),
    "scatter_tracks_beast": tracks("scatter_tracks_beast", "beast"),
    "scatter_log_mossy": mossy_log, "scatter_mushrooms_brown": mushrooms("scatter_mushrooms_brown", 0), "scatter_mushrooms_red": mushrooms("scatter_mushrooms_red", 1),
    "scatter_roots": roots, "scatter_ice_patch": ice_patch,
})

kit.run(MODELS, FAMILY)
