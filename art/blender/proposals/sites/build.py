"""Places to find proposals: what explorers come across far from the town.
See ../LEEME.md.

    blender --background --factory-startup --python art/blender/proposals/sites/build.py -- [ids]
"""

import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import _kit as kit  # noqa: E402
import _shapes  # noqa: E402
import common  # noqa: E402
from _shapes import TAU, beam, log, rock, rope, solid, wheel  # noqa: E402

FAMILY = "sites"
C = common.rgb
COLORS = {
    **_shapes.COLORS,
    "cave": C(0x14110F), "moss": C(0x5E8A3A), "ivy": C(0x3E6E38), "grass": C(0x6A9440), "soil": C(0x6A4A30), "bone": C(0xE0D8C0), "bone_dark": C(0xB8AE94),
    "water_swamp": C(0x3A5660), "lily": C(0x6AA050), "rust": C(0x7A4A3A), "glow_eye": C(0xFFE06A), "glow_blue": C(0x7AD8FF), "glow_green": C(0x8CFFB0),
    "cap_red": C(0xC83A2E), "cap_white": C(0xECE6D6), "stem": C(0xE0D8C0), "marble": C(0xD8D4C8), "marble_dark": C(0xB4AEA2), "thatch": C(0xC9A55A),
    "thatch_dark": C(0xA8863F), "cloth_red": C(0x9A3A3A), "cloth_blue": C(0x2E5A9A), "crow": C(0x1E1E24), "leaf": C(0x4E8A3C), "leaf_light": C(0x7AB050),
    "paint_red": C(0xB8362E), "flame": C(0xF2A23A), "smoke": C(0x8A8884), "dry": C(0xB89A64),
}


def boulder_mound(mb, rnd, cx, cy, r, h, n=14, mats=("stone", "stone_dark", "stone_light")):
    for _ in range(n):
        a, d = rnd.uniform(0, TAU), rnd.uniform(0, 1) ** 0.6
        s = r * (0.55 - 0.3 * d) * rnd.uniform(0.8, 1.2)
        mb.sphere((cx + math.cos(a) * r * d, cy + math.sin(a) * r * d, h * (1 - d) * 0.8), s, rnd.choice(mats), segments=6, rings=4,
                  scale=(rnd.uniform(0.9, 1.3), rnd.uniform(0.9, 1.3), rnd.uniform(0.7, 1.0)))


def column(mb, x, y, z0, h, r=0.3, mat="marble", lean=(0.0, 0.0), broken=False):
    tx, ty = x + lean[0] * h, y + lean[1] * h
    mb.cylinder((x, y, z0), (x, y, z0 + 0.2), r * 1.4, r * 1.3, mat + "_dark", segments=8)
    mb.cylinder((x, y, z0 + 0.2), (tx, ty, z0 + h), r, r * 0.88, mat, segments=8)
    if broken:
        mb.cylinder((tx, ty, z0 + h), (tx + 0.05, ty, z0 + h + 0.15), r * 0.88, r * 0.3, mat + "_dark", segments=5)
    else:
        mb.cylinder((tx, ty, z0 + h), (tx, ty, z0 + h + 0.2), r * 1.0, r * 1.5, mat + "_dark", segments=8)


def ivy(mb, rnd, x, y, z0, z1, n=8, spread=0.5):
    for _ in range(n):
        mb.sphere((x + rnd.uniform(-spread, spread), y + rnd.uniform(-0.05, 0.05), rnd.uniform(z0, z1)), rnd.uniform(0.15, 0.3), "ivy" if rnd.random() < 0.6 else "moss",
                  segments=5, rings=3, scale=(1, 0.4, 1))


def crypt():
    """Steps down under a stone porch, shut by an iron gate."""
    mb = kit.begin()
    rnd = random.Random(71)
    mb.sphere((0, 1.2, 0.0), 3.4, "grass", segments=10, rings=6, scale=(1.0, 1.3, 0.75))        # The mound over the vault.
    mb.box((0, -0.9, 1.5), (3.4, 1.0, 3.0), "stone_dark")
    for sx in (-1, 1):
        mb.box((sx * 1.3, -1.7, 1.3), (0.7, 0.9, 2.6), "stone")
        mb.box((sx * 1.3, -1.7, 2.7), (0.9, 1.1, 0.2), "stone_light")
        mb.box((sx * 2.2, -1.9, 0.5), (0.8, 0.8, 1.0), "stone_dark")              # Plinths with hooded figures.
        mb.cylinder((sx * 2.2, -1.9, 1.0), (sx * 2.2, -1.9, 2.3), 0.32, 0.2, "stone_light", segments=7)
        mb.sphere((sx * 2.2, -1.9, 2.45), 0.2, "stone_light", segments=6, rings=4)
        mb.box((sx * 2.2, -2.08, 2.45), (0.16, 0.06, 0.14), "cave")
    mb.box((0, -1.7, 3.0), (3.6, 1.2, 0.5), "stone")
    solid(mb, [(-1.9, -2.3, 3.25), (1.9, -2.3, 3.25), (0, -2.3, 4.2)], (0, 1.2, 0), "stone_dark")
    mb.box((0, -2.32, 3.6), (0.12, 0.04, 0.6), "stone_light")
    mb.box((0, -2.32, 3.7), (0.4, 0.04, 0.12), "stone_light")
    mb.box((0, -1.5, 1.3), (1.9, 0.5, 2.6), "cave")
    for k in range(4):                                                           # Steps going down into the dark.
        mb.box((0, -2.6 + 0.3 * k, 0.12 - 0.0 * k), (1.9, 0.3, 0.24 - 0.05 * k), "stone_dark" if k % 2 else "stone")
    bones = []
    for sx, name in ((-1, "gate_l"), (1, "gate_r")):
        w = {name: 1.0}
        for k in range(4):
            x = sx * (0.12 + 0.22 * k)
            mb.cylinder((x, -2.1, 0.25), (x, -2.1, 2.3), 0.022, 0.022, "iron", w, segments=4)
            mb.cylinder((x, -2.1, 2.3), (x, -2.1, 2.45), 0.03, 0.0, "iron", w, segments=4)
        for z in (0.4, 1.3, 2.2):
            beam(mb, (sx * 0.05, -2.1, z), (sx * 0.9, -2.1, z), 0.02, "rust", w)
        bones.append((name, (sx * 0.93, -2.1, 0.25), (sx * 0.93, -2.1, 2.3), None))
    ivy(mb, rnd, -1.3, -2.18, 0.6, 2.4, 6, 0.3)
    for _ in range(5):
        rock(mb, rnd.uniform(-2.8, 2.8), rnd.uniform(-3.4, -2.6), 0.1, rnd.uniform(0.15, 0.3), rnd)

    def swing(opening):
        def pose(t):
            s = kit.smooth(t) if opening else 1 - kit.smooth(t)
            return {"gate_l": [(kit.Z, 80.0 * s)], "gate_r": [(kit.Z, -80.0 * s)]}, {}
        return pose

    mech = kit.Mech(bones).clip("open", 2.0, swing(True), loops=False).clip("close", 2.0, swing(False), loops=False)
    kit.save(mb, FAMILY, "site_crypt", COLORS, mech=mech)


def cave():
    """A cave mouth in a knoll of rock, with something watching from inside."""
    mb = kit.begin()
    rnd = random.Random(72)
    boulder_mound(mb, rnd, 0, 1.5, 4.0, 4.2, 22)
    mb.sphere((0, -1.1, 0.9), 1.5, "cave", segments=8, rings=5, scale=(1.0, 1.3, 1.0))
    for sx in (-1, 1):
        mb.sphere((sx * 1.7, -1.9, 0.8), 1.0, "stone_dark", segments=6, rings=4, scale=(0.8, 1.0, 1.5))
    mb.sphere((0, -1.6, 2.6), 1.5, "stone", segments=7, rings=4, scale=(1.5, 0.9, 0.6))
    for k in range(5):
        x = -0.9 + 0.45 * k
        mb.cylinder((x, -2.1, 2.2), (x, -2.1, 1.6 + 0.2 * (k % 2)), 0.12, 0.0, "stone_light", segments=5)
    for k in range(6):
        mb.sphere((rnd.uniform(-2.5, 2.5), rnd.uniform(0.5, 3.0), rnd.uniform(2.5, 3.8)), rnd.uniform(0.4, 0.7), "moss", segments=5, rings=3, scale=(1.3, 1.3, 0.4))
    for k in range(3):                                                           # Bones at the door.
        x = -1.0 + 1.0 * k
        mb.cylinder((x, -3.0, 0.05), (x + 0.5, -2.8, 0.05), 0.04, 0.04, "bone", segments=5)
        mb.sphere((x, -3.0, 0.05), 0.07, "bone", segments=4, rings=3)
    mb.sphere((1.3, -3.2, 0.14), 0.16, "bone", segments=6, rings=4)
    w = {"eyes": 1.0}
    for sx in (-1, 1):
        mb.sphere((sx * 0.16, -1.9, 1.0), 0.06, "glow_eye", w, segments=5, rings=3, scale=(1, 0.5, 0.7))
    pose = lambda t: ({}, {"eyes": (0.25 * math.sin(TAU * t), 0.3 * (0.5 - 0.5 * math.cos(TAU * 2 * t)), 0.05 * math.sin(TAU * 2 * t))})   # noqa: E731
    kit.save(mb, FAMILY, "site_cave", COLORS, mech=kit.Mech([("eyes", (0, -1.9, 1.0), (0, -1.5, 1.0), None)]).clip("watch", 6.0, pose))


def ruined_tower():
    mb = kit.begin()
    rnd = random.Random(73)
    n = 12
    heights = [7.5, 8.2, 7.0, 5.6, 4.0, 2.4, 1.4, 0.9, 1.6, 3.4, 5.4, 6.8]
    for i in range(n):
        a0, a1 = TAU * i / n, TAU * (i + 1) / n
        am = (a0 + a1) / 2
        h = heights[i]
        solid(mb, [(math.cos(a0) * 2.6, math.sin(a0) * 2.6, 0), (math.cos(a1) * 2.6, math.sin(a1) * 2.6, 0), (math.cos(a1) * 2.5, math.sin(a1) * 2.5, h),
                   (math.cos(a0) * 2.5, math.sin(a0) * 2.5, h - 0.5 * rnd.random())], (-math.cos(am) * 0.6, -math.sin(am) * 0.6, 0), "stone" if i % 2 else "stone_light")
        for _ in range(int(h)):
            z = rnd.uniform(0.4, max(0.5, h - 0.6))
            mb.box((math.cos(am) * 2.6, math.sin(am) * 2.6, z), (0.1, 0.6, 0.26), "stone_dark", rotation_z=am)
        if h > 5 and i % 3 == 0:
            mb.box((math.cos(am) * 2.6, math.sin(am) * 2.6, 4.4), (0.16, 0.3, 0.9), "cave", rotation_z=am)
    mb.cylinder((0, 0, 0), (0, 0, 0.3), 3.0, 2.8, "stone_dark", segments=12)
    mb.cylinder((0, 0, 0.3), (0, 0, 0.36), 2.0, 2.0, "soil", segments=12)
    for k in range(5):                                                           # What is left of the floors.
        a = TAU * (0.02 + 0.05 * k)
        beam(mb, (math.cos(a) * 2.1, math.sin(a) * 2.1, 4.0), (math.cos(a + 2.2) * 2.1, math.sin(a + 2.2) * 2.1, 4.0), 0.1, "pole_dark")
    for _ in range(16):
        a = rnd.uniform(TAU * 0.35, TAU * 0.75)
        d = rnd.uniform(2.9, 5.0)
        rock(mb, math.cos(a) * d, math.sin(a) * d, 0.15, rnd.uniform(0.25, 0.6), rnd)
    ivy(mb, rnd, -2.0, -1.7, 0.5, 5.0, 12, 0.9)
    mb.cylinder((-0.6, 0.4, 0.36), (-0.5, 0.4, 2.4), 0.1, 0.05, "bark", segments=6)                # A tree has grown inside.
    mb.sphere((-0.5, 0.4, 2.8), 0.9, "leaf", segments=7, rings=5)
    w = {"crows": 1.0}
    for k in range(3):
        a = TAU * k / 3
        x, y = math.cos(a) * 3.4, math.sin(a) * 3.4
        mb.sphere((x, y, 9.2 + 0.3 * k), 0.14, "crow", w, segments=5, rings=3, scale=(1, 1.8, 0.8))
        for s in (-1, 1):
            solid(mb, [(x, y, 9.24 + 0.3 * k), (x + math.cos(a) * 0.4 * s, y + math.sin(a) * 0.4 * s, 9.34 + 0.3 * k), (x - math.sin(a) * 0.14, y + math.cos(a) * 0.14, 9.24 + 0.3 * k)],
                  (0, 0, 0.02), "crow", w)
    pose = lambda t: ({"crows": [(kit.Z, 360.0 * t)]}, {"crows": (0, 0, 0.3 * math.sin(TAU * 2 * t))})   # noqa: E731
    kit.save(mb, FAMILY, "site_ruined_tower", COLORS, mech=kit.Mech([("crows", (0, 0, 9.2), (0, 0, 10.0), None)]).clip("circle", 8.0, pose))


def sunken_temple():
    """A temple the marsh has taken: 12 x 10 m of water, steps and columns."""
    mb = kit.begin()
    rnd = random.Random(74)
    mb.box((0, 0, 0.06), (12.0, 10.0, 0.12), "water_swamp")
    for k in range(3):
        mb.box((0, 0.8, 0.2 + 0.2 * k), (8.0 - 1.0 * k, 6.0 - 1.0 * k, 0.24), "marble_dark" if k % 2 else "marble")
    for i in range(4):
        for sy in (-1, 1):
            x = -2.4 + 1.6 * i
            fate = (i * 3 + (sy > 0)) % 4
            if fate == 0:
                column(mb, x, 0.8 + sy * 1.7, 0.8, 1.3, 0.3, "marble", (0, 0), True)
            elif fate == 1:
                column(mb, x, 0.8 + sy * 1.7, 0.8, 3.4, 0.3, "marble", (0.06, 0.03 * sy))
            else:
                column(mb, x, 0.8 + sy * 1.7, 0.8, 3.4, 0.3)
    mb.box((0.8, 2.5, 4.6), (3.6, 0.7, 0.4), "marble_dark")                       # A piece of the architrave still up.
    mb.cylinder((-4.0, -2.6, 0.2), (-1.6, -3.6, 0.3), 0.3, 0.27, "marble", segments=8)             # One fallen into the water.
    mb.box((0, 0.8, 1.2), (1.4, 1.0, 0.8), "marble_dark")                        # The idol on its base.
    mb.cylinder((0, 0.8, 1.6), (0, 0.8, 2.8), 0.45, 0.3, "stone_dark", segments=7)
    mb.sphere((0, 0.8, 3.0), 0.36, "stone_dark", segments=7, rings=5)
    for sx in (-1, 1):
        mb.sphere((sx * 0.14, 0.48, 3.05), 0.06, "glow_green", segments=5, rings=3)
        mb.cylinder((sx * 0.4, 0.8, 2.4), (sx * 0.9, 0.6, 2.9), 0.1, 0.07, "stone_dark", segments=5)
    for _ in range(14):
        x, y = rnd.uniform(-5.6, 5.6), rnd.uniform(-4.6, 4.6)
        if abs(x) < 4.2 and abs(y - 0.8) < 3.2:
            continue
        mb.cylinder((x, y, 0.12), (x, y, 0.14), rnd.uniform(0.25, 0.45), rnd.uniform(0.25, 0.45), "lily", segments=7)
    for _ in range(8):
        x, y = rnd.choice((-1, 1)) * rnd.uniform(4.4, 5.6), rnd.uniform(-4.5, 4.5)
        for k in range(3):
            mb.cylinder((x + 0.12 * k, y, 0.1), (x + 0.12 * k + 0.05, y, 1.2 + 0.2 * k), 0.025, 0.015, "dry", segments=4)
    ivy(mb, rnd, -2.4, -0.95, 1.0, 3.5, 7, 0.4)
    w = {"wisp": 1.0}
    for k in range(3):
        a = TAU * k / 3
        mb.sphere((math.cos(a) * 3.0, -3.0 + math.sin(a) * 1.2, 0.9 + 0.2 * k), 0.12, "glow_green", w, segments=5, rings=3)
    pose = lambda t: ({"wisp": [(kit.Z, 360.0 * t)]}, {"wisp": (0, 0, 0.25 * math.sin(TAU * 2 * t))})   # noqa: E731
    kit.save(mb, FAMILY, "site_sunken_temple", COLORS, mech=kit.Mech([("wisp", (0, -3.0, 0.9), (0, -3.0, 1.5), None)]).clip("wisps", 9.0, pose))


def stone_circle():
    mb = kit.begin()
    rnd = random.Random(75)
    mb.cylinder((0, 0, 0), (0, 0, 0.05), 6.5, 6.5, "grass", segments=16)
    n = 10
    for k in range(n):
        a = TAU * k / n
        x, y = math.cos(a) * 5.2, math.sin(a) * 5.2
        h = rnd.uniform(3.0, 3.8)
        if k == 7:   # One has fallen.
            mb.box((x * 1.15, y * 1.15, 0.35), (1.0, 3.4, 0.7), "stone", rotation_z=a + math.pi / 2 + 0.3)
            continue
        mb.box((x, y, h / 2), (0.75, 1.3, h), "stone" if k % 2 else "stone_light", rotation_z=a)
        mb.sphere((x, y, 0.1), 0.6, "moss", segments=5, rings=3, scale=(1.3, 1.3, 0.3))
        if k in (0, 1, 3, 4):                                                    # Lintels still in place.
            a1 = TAU * (k + 1) / n
            if k in (0, 3):
                mx, my = (x + math.cos(a1) * 5.2) / 2, (y + math.sin(a1) * 5.2) / 2
                mb.box((mx, my, 3.95), (0.8, 3.5, 0.5), "stone_dark", rotation_z=(a + a1) / 2)
    mb.box((0, 0, 0.45), (2.2, 1.2, 0.3), "stone_dark")                          # The altar stone.
    for sx in (-0.8, 0.8):
        mb.box((sx, 0, 0.15), (0.4, 1.0, 0.3), "stone")
    for k in range(5):
        a = TAU * k / 5
        mb.box((math.cos(a) * 0.7, math.sin(a) * 0.35, 0.61), (0.16, 0.03, 0.02), "glow_blue", rotation_z=a)
    w = {"light": 1.0}
    mb.cylinder((0, 0, 0.7), (0, 0, 4.5), 0.14, 0.02, "glow_blue", w, segments=6)
    for k in range(4):
        a = TAU * k / 4
        mb.sphere((math.cos(a) * 0.7, math.sin(a) * 0.7, 1.4 + 0.6 * k), 0.09, "glow_blue", w, segments=5, rings=3)
    pose = lambda t: ({"light": [(kit.Z, 360.0 * t)]}, {"light": (0, 0, 0.2 * math.sin(TAU * 2 * t))})   # noqa: E731
    kit.save(mb, FAMILY, "site_stone_circle", COLORS, mech=kit.Mech([("light", (0, 0, 0.7), (0, 0, 1.7), None)]).clip("awake", 8.0, pose))


def abandoned_mine():
    mb = kit.begin()
    rnd = random.Random(76)
    boulder_mound(mb, rnd, 0, 2.0, 3.6, 3.6, 18, ("stone", "stone_dark", "soil"))
    mb.box((0, -0.6, 1.0), (1.8, 1.6, 2.0), "cave")
    for sx in (-1, 1):
        log(mb, (sx * 1.0, -1.4, 0), (sx * 0.9, -1.4, 2.2), 0.13)
    log(mb, (-1.3, -1.4, 2.25), (1.3, -1.4, 2.2), 0.14)
    for k, (z, tilt) in enumerate(((0.6, 0.1), (1.2, -0.15), (1.75, 0.08))):      # Boarded up, badly.
        beam(mb, (-1.1, -1.55, z - tilt), (1.1, -1.55, z + tilt), 0.07, "plank_dark" if k % 2 else "plank")
    mb.box((1.6, -2.0, 1.0), (0.7, 0.05, 0.5), "plank_light")                    # A warning.
    mb.cylinder((1.6, -1.98, 0), (1.6, -1.98, 1.0), 0.04, 0.035, "pole", segments=5)
    beam(mb, (1.4, -2.04, 0.85), (1.8, -2.04, 1.15), 0.02, "paint_red")
    beam(mb, (1.4, -2.04, 1.15), (1.8, -2.04, 0.85), 0.02, "paint_red")
    for sx in (-0.3, 0.3):                                                       # Rails running out, and a cart off them.
        beam(mb, (sx, -1.4, 0.05), (sx, -4.6, 0.05), 0.03, "rust")
    for k in range(8):
        mb.box((0, -1.6 - 0.4 * k, 0.025), (0.9, 0.12, 0.05), "pole_dark")
    mb.box((-1.3, -3.4, 0.45), (0.8, 1.1, 0.5), "plank_dark", rotation_z=0.5)
    mb.box((-1.3, -3.4, 0.72), (0.84, 1.14, 0.05), "rust", rotation_z=0.5)
    for k in range(2):
        mb.cylinder((-1.75 + 0.5 * k, -3.2 - 0.5 * k, 0.18), (-1.65 + 0.5 * k, -3.14 - 0.5 * k, 0.18), 0.18, 0.18, "rust", segments=8)
    for _ in range(7):
        rock(mb, rnd.uniform(1.0, 2.6), rnd.uniform(-4.0, -2.6), 0.12, rnd.uniform(0.15, 0.3), rnd, rnd.choice(("stone_dark", "gold", "stone")))
    beam(mb, (2.4, -2.2, 0), (2.6, -2.0, 0.9), 0.02, "pole")
    beam(mb, (2.4, -2.1, 0.86), (2.8, -1.9, 0.9), 0.025, "rust")
    kit.save(mb, FAMILY, "site_abandoned_mine", COLORS)


def giant_bones():
    """The ribs of something that died here long ago: 14 m from skull to tail."""
    mb = kit.begin()
    rnd = random.Random(77)
    spine = [(0, -5.0 + 1.0 * k, 1.5 + 1.0 * math.sin(math.pi * k / 11)) for k in range(12)]
    for a, b in zip(spine, spine[1:]):
        mb.cylinder(a, b, 0.28, 0.26, "bone", segments=6)
        mb.cylinder(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2), ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + 0.1, (a[2] + b[2]) / 2 + 0.55), 0.12, 0.03, "bone_dark", segments=4)
    for k in range(2, 9):                                                        # Ribs: some whole, some broken.
        x0, y0, z0 = spine[k]
        r = 1.9 - 0.12 * abs(k - 5)
        for sx in (-1, 1):
            broken = (k * 3 + (sx > 0)) % 5 == 0
            pts = [(sx * r * math.sin(b), z0 - r * 0.9 * (1 - math.cos(b))) for b in (0.0, 0.5, 1.0, 1.5, 2.0, 2.4)]
            for (xa, za), (xb, zb) in zip(pts, pts[1:4] if broken else pts[1:]):
                mb.cylinder((xa, y0, max(0.05, za)), (xb, y0, max(0.05, zb)), 0.1, 0.085, "bone" if k % 2 else "bone_dark", segments=5)
    mb.sphere((0, -6.2, 1.1), 0.9, "bone", segments=8, rings=5, scale=(1.0, 1.5, 0.8))             # The skull.
    mb.box((0, -7.6, 0.75), (0.9, 1.6, 0.5), "bone")
    mb.box((0, -7.5, 0.35), (0.8, 1.5, 0.2), "bone_dark")
    for k in range(5):
        for sx in (-1, 1):
            mb.cylinder((sx * 0.38, -8.2 + 0.3 * k, 0.52), (sx * 0.38, -8.2 + 0.3 * k, 0.2), 0.07, 0.0, "bone", segments=4)
    for sx in (-1, 1):
        mb.sphere((sx * 0.5, -6.6, 1.3), 0.26, "cave", segments=6, rings=4)
        mb.cylinder((sx * 0.5, -5.8, 1.7), (sx * 1.3, -5.0, 2.9), 0.2, 0.0, "bone_dark", segments=5)
    for k in range(5):                                                           # The tail trails off into the grass.
        y = 6.0 + 0.9 * k
        mb.cylinder((0.3 * math.sin(k), y, 0.6 - 0.1 * k), (0.3 * math.sin(k + 1), y + 0.9, 0.5 - 0.1 * k), 0.2 - 0.03 * k, 0.17 - 0.03 * k, "bone", segments=5)
    for _ in range(10):
        mb.sphere((rnd.uniform(-2.5, 2.5), rnd.uniform(-5.0, 5.0), 0.0), rnd.uniform(0.4, 0.8), "moss" if rnd.random() < 0.5 else "grass", segments=5, rings=3, scale=(1.2, 1.2, 0.3))
    kit.save(mb, FAMILY, "site_giant_bones", COLORS)


def colossal_head():
    """The head of a statue as tall as a house, buried to the chin."""
    mb = kit.begin()
    rnd = random.Random(78)
    mb.sphere((0, 0, 0.0), 4.0, "soil", segments=9, rings=4, scale=(1.2, 1.1, 0.15))
    mb.sphere((0.3, 0.3, 2.0), 2.6, "stone", segments=9, rings=6, scale=(0.9, 1.0, 1.25))
    mb.box((0.25, -2.2, 2.1), (0.7, 0.9, 1.3), "stone_light")                    # Nose, brow, lips.
    mb.box((0.25, -2.15, 3.0), (2.8, 0.7, 0.4), "stone_light")
    mb.box((0.25, -2.2, 1.1), (1.3, 0.5, 0.3), "stone_dark")
    for sx in (-1, 1):
        mb.box((0.25 + sx * 0.85, -2.3, 2.6), (0.8, 0.3, 0.3), "cave")
        mb.sphere((0.25 + sx * 2.35, 0.3, 2.2), 0.7, "stone_dark", segments=6, rings=4, scale=(0.4, 0.9, 1.3))
    mb.cylinder((0.3, 0.3, 4.8), (0.3, 0.3, 5.6), 2.3, 1.9, "stone_dark", segments=9)             # What is left of a crown.
    for k in range(6):
        a = TAU * k / 6 + 0.3
        if k in (2, 5):
            continue
        mb.cylinder((0.3 + math.cos(a) * 1.9, 0.3 + math.sin(a) * 1.9, 5.5), (0.3 + math.cos(a) * 2.0, 0.3 + math.sin(a) * 2.0, 6.6), 0.35, 0.0, "stone_light", segments=4)
    beam(mb, (1.6, -2.0, 4.6), (0.9, -2.5, 1.6), 0.05, "cave")                    # A crack down the face.
    ivy(mb, rnd, -1.5, -2.0, 0.6, 4.0, 10, 0.9)
    for _ in range(9):
        rock(mb, rnd.uniform(-4.0, 4.0), rnd.uniform(-4.0, -2.6), 0.15, rnd.uniform(0.25, 0.6), rnd)
    mb.cylinder((3.6, -1.6, 0), (3.5, 0.6, 0.5), 0.7, 0.6, "stone", segments=7)   # A finger pointing out of the ground.
    kit.save(mb, FAMILY, "site_colossal_head", COLORS)


def battlefield():
    mb = kit.begin()
    rnd = random.Random(79)
    mb.cylinder((0, 0, 0), (0, 0, 0.04), 6.0, 6.0, "soil", segments=14)
    for k in range(9):                                                           # Spears and swords left standing in the ground.
        a, d = rnd.uniform(0, TAU), rnd.uniform(0.6, 5.0)
        x, y = math.cos(a) * d, math.sin(a) * d
        lean = rnd.uniform(-0.3, 0.3)
        if k % 3:
            mb.cylinder((x, y, 0), (x + lean, y + lean * 0.5, 1.9), 0.025, 0.02, "pole", segments=5)
            mb.cylinder((x + lean, y + lean * 0.5, 1.9), (x + lean * 1.1, y + lean * 0.55, 2.2), 0.045, 0.0, "rust", segments=4)
        else:
            mb.box((x, y, 0.45), (0.07, 0.015, 0.9), "rust", rotation_z=a)
            mb.box((x, y, 0.92), (0.24, 0.03, 0.04), "rust", rotation_z=a)
            mb.cylinder((x, y, 0.94), (x, y, 1.1), 0.02, 0.02, "leather", segments=5)
    for k in range(5):                                                           # Shields and helmets.
        a, d = rnd.uniform(0, TAU), rnd.uniform(1.0, 5.0)
        x, y = math.cos(a) * d, math.sin(a) * d
        mb.cylinder((x, y, 0.05), (x + 0.05, y, 0.12), 0.38, 0.38, ("cloth_red", "cloth_blue")[k % 2], segments=9)
        mb.sphere((x + 0.03, y, 0.13), 0.08, "rust", segments=5, rings=3)
        mb.sphere((x + 0.9, y + 0.4, 0.1), 0.14, "rust", segments=6, rings=4)
    for k in range(3):                                                           # Two torn banners, one still up.
        px, py = (-2.0, 2.4, 0.5)[k], (1.5, -1.0, 3.0)[k]
        tilt = (0.0, 0.9, 0.3)[k]
        mb.cylinder((px, py, 0), (px + tilt, py, 3.4 - tilt * 1.5), 0.04, 0.03, "pole", segments=5)
        top = 3.4 - tilt * 1.5
        solid(mb, [(px + tilt + 0.03, py - 0.01, top), (px + tilt + 1.0, py - 0.01, top - 0.2), (px + tilt + 0.6, py - 0.01, top - 0.5), (px + tilt + 0.9, py - 0.01, top - 0.9),
                   (px + tilt + 0.03, py - 0.01, top - 0.8)], (0, 0.02, 0), ("cloth_red", "cloth_blue", "cloth_red")[k], {"flag": 1.0} if k == 0 else None)
    wheel(mb, (3.2, 2.2, 0.3), 0.55, None, 0.09)
    mb.box((3.6, 2.9, 0.3), (1.2, 1.8, 0.4), "plank_dark", rotation_z=0.4)
    for _ in range(8):
        a, d = rnd.uniform(0, TAU), rnd.uniform(0.5, 5.5)
        mb.cylinder((math.cos(a) * d, math.sin(a) * d, 0.04), (math.cos(a) * d + 0.5, math.sin(a) * d + 0.2, 0.04), 0.03, 0.03, "bone", segments=4)
    w = {"crow": 1.0}
    mb.sphere((2.4 + 0.9, -1.0, 2.2), 0.13, "crow", w, segments=5, rings=3, scale=(1, 1.7, 0.9))
    mb.cylinder((3.3, -1.16, 2.25), (3.3, -1.3, 2.22), 0.03, 0.0, "pole", w, segments=4)

    def pose(t):
        return {"flag": [(kit.Z, 14.0 * math.sin(TAU * t))], "crow": [(kit.X, 14.0 * max(0.0, math.sin(TAU * 3 * t)))]}, {}

    mech = kit.Mech([("flag", (-1.97, 1.5, 3.0), (-1.0, 1.5, 3.0), None), ("crow", (3.3, -1.0, 2.1), (3.3, -1.2, 2.2), None)]).clip("idle", 3.0, pose)
    kit.save(mb, FAMILY, "site_battlefield", COLORS, mech=mech)


def hermit_hut():
    """Someone lives out here alone, and knows things."""
    mb = kit.begin()
    rnd = random.Random(80)
    boulder_mound(mb, rnd, 1.6, 1.6, 2.2, 2.6, 9)
    for k in range(9):                                                           # A round hut of wattle, leaning on the rock.
        a0, a1 = TAU * k / 9, TAU * (k + 1) / 9
        if k == 6:
            continue                                                            # The doorway (-Y).
        solid(mb, [(math.cos(a0) * 1.6 - 0.6, math.sin(a0) * 1.6, 0), (math.cos(a1) * 1.6 - 0.6, math.sin(a1) * 1.6, 0), (math.cos(a1) * 1.6 - 0.6, math.sin(a1) * 1.6, 1.5),
                   (math.cos(a0) * 1.6 - 0.6, math.sin(a0) * 1.6, 1.5)], (-math.cos((a0 + a1) / 2) * 0.12, -math.sin((a0 + a1) / 2) * 0.12, 0), "plank" if k % 2 else "plank_dark")
    mb.cylinder((-0.6, 0, 1.45), (-0.6, 0, 3.0), 2.1, 0.15, "thatch", segments=9)
    mb.cylinder((-0.6, 0, 1.45), (-0.6, 0, 1.6), 2.15, 2.0, "thatch_dark", segments=9)
    mb.box((-0.75, -1.5, 0.75), (0.8, 0.2, 1.5), "cave")
    solid(mb, [(-1.2, -1.62, 1.5), (-0.3, -1.62, 1.5), (-0.3, -1.62, 0.3), (-1.2, -1.62, 0.5)], (0, 0.03, 0), "leather")
    for k in range(4):                                                           # A small garden and what he gathers.
        mb.box((-3.0, -1.0 + 0.6 * k, 0.06), (1.2, 0.4, 0.12), "soil")
        for i in range(3):
            mb.sphere((-3.4 + 0.4 * i, -1.0 + 0.6 * k, 0.2), 0.12, "leaf_light" if (k + i) % 2 else "leaf", segments=5, rings=3)
    beam(mb, (0.6, -1.8, 0), (0.6, -1.8, 1.7), 0.035, "pole")
    beam(mb, (2.2, -1.8, 0), (2.2, -1.8, 1.7), 0.035, "pole")
    rope(mb, (0.6, -1.8, 1.6), (2.2, -1.8, 1.6), 0.008)
    for k in range(5):
        mb.cylinder((0.8 + 0.3 * k, -1.8, 1.6), (0.8 + 0.3 * k, -1.8, 1.2), 0.07, 0.02, "leaf" if k % 2 else "dry", segments=5)
    mb.cylinder((-0.2, -2.8, 0), (-0.2, -2.8, 0.1), 0.5, 0.5, "stone_dark", segments=8)             # His fire and his pot.
    mb.cylinder((-0.2, -2.8, 0.1), (-0.2, -2.8, 0.5), 0.16, 0.0, "flame", {"fire": 1.0}, segments=5)
    mb.sphere((-0.2, -2.8, 0.75), 0.22, "iron", segments=7, rings=4)
    for k in range(3):
        a = TAU * k / 3
        beam(mb, (-0.2 + math.cos(a) * 0.6, -2.8 + math.sin(a) * 0.6, 0), (-0.2, -2.8, 1.5), 0.025, "pole_dark")
    _shapes.stump(mb, -1.4, -2.8, 0.4, 0.22)
    w = {"smoke": 1.0}
    for k in range(3):
        mb.sphere((-0.6 + 0.12 * k, 0, 3.3 + 0.4 * k), 0.2 + 0.07 * k, "smoke", w, segments=5, rings=3)
    pose = lambda t: ({"fire": [(kit.Z, 20.0 * math.sin(TAU * 3 * t))]}, {"smoke": (0.1 * math.sin(TAU * t), 0, 0.2 * math.sin(TAU * t))})   # noqa: E731
    mech = kit.Mech([("fire", (-0.2, -2.8, 0.1), (-0.2, -2.8, 0.5), None), ("smoke", (-0.6, 0, 3.3), (-0.6, 0, 4.0), None)]).clip("idle", 3.0, pose)
    kit.save(mb, FAMILY, "site_hermit_hut", COLORS, mech=mech)


def fairy_ring():
    mb = kit.begin()
    rnd = random.Random(81)
    mb.cylinder((0, 0, 0), (0, 0, 0.04), 3.2, 3.2, "grass", segments=14)
    mb.cylinder((0, 0, 0), (0, 0, 0.05), 2.0, 2.0, "moss", segments=12)
    n = 13
    for k in range(n):
        a = TAU * k / n + rnd.uniform(-0.08, 0.08)
        x, y = math.cos(a) * 2.4, math.sin(a) * 2.4
        h = rnd.uniform(0.3, 0.9)
        big = k % 4 == 0
        if big:
            h *= 1.8
        mb.cylinder((x, y, 0), (x, y, h), 0.08 + 0.05 * big, 0.06 + 0.04 * big, "stem", segments=6)
        mb.cylinder((x, y, h - 0.02), (x, y, h + 0.22 + 0.15 * big), 0.34 + 0.3 * big, 0.04, "cap_red" if k % 3 else "glow_blue", segments=8)
        if k % 3:
            for i in range(4):
                b = TAU * i / 4 + k
                mb.sphere((x + math.cos(b) * 0.16, y + math.sin(b) * 0.16, h + 0.1), 0.045, "cap_white", segments=4, rings=3)
    w = {"motes": 1.0}
    for k in range(10):
        a = TAU * k / 10
        r = 0.6 + 1.2 * ((k * 7) % 10) / 10
        mb.sphere((math.cos(a) * r, math.sin(a) * r, 0.5 + 0.18 * ((k * 3) % 7)), 0.05, "glow_green" if k % 2 else "glow_blue", w, segments=4, rings=3)
    pose = lambda t: ({"motes": [(kit.Z, 360.0 * t)]}, {"motes": (0, 0, 0.15 * math.sin(TAU * 3 * t))})   # noqa: E731
    kit.save(mb, FAMILY, "site_fairy_ring", COLORS, mech=kit.Mech([("motes", (0, 0, 0.5), (0, 0, 1.2), None)]).clip("dance", 10.0, pose))


def ancient_gate():
    """A gateway standing alone where a city used to be."""
    mb = kit.begin()
    rnd = random.Random(82)
    for sx in (-1, 1):
        mb.box((sx * 2.6, 0, 0.4), (2.0, 2.4, 0.8), "marble_dark")
        mb.box((sx * 2.6, 0, 3.4), (1.5, 1.8, 5.2), "marble")
        for k in range(3):
            mb.box((sx * 2.6, -0.92, 1.6 + 1.5 * k), (1.0, 0.06, 0.9), "marble_dark")
        mb.box((sx * 2.6, 0, 6.1), (1.9, 2.2, 0.3), "marble_dark")
    n = 9
    for i in range(n):
        if i in (3, 4):
            continue                                                            # The crown of the arch is gone.
        a0, a1 = math.pi * i / n, math.pi * (i + 1) / n
        solid(mb, [(math.cos(a0) * 1.85, -0.8, 6.2 + math.sin(a0) * 1.85), (math.cos(a0) * 2.9, -0.8, 6.2 + math.sin(a0) * 2.9), (math.cos(a1) * 2.9, -0.8, 6.2 + math.sin(a1) * 2.9),
                   (math.cos(a1) * 1.85, -0.8, 6.2 + math.sin(a1) * 1.85)], (0, 1.6, 0), "marble" if i % 2 else "marble_dark")
    mb.box((0.6, -2.4, 0.5), (1.3, 1.5, 1.0), "marble", rotation_z=0.5)           # What fell from it.
    mb.box((-0.8, -3.0, 0.35), (1.0, 1.2, 0.7), "marble_dark", rotation_z=-0.3)
    for _ in range(9):
        rock(mb, rnd.uniform(-3.5, 3.5), rnd.uniform(-4.0, -1.8), 0.15, rnd.uniform(0.2, 0.5), rnd, rnd.choice(("marble", "marble_dark")))
    for k in range(6):                                                           # The road it stood on, half under the grass.
        mb.box((rnd.uniform(-0.2, 0.2), -4.5 + 1.6 * k, 0.03), (2.6, 1.4, 0.06), "stone_dark" if k % 2 else "stone")
        mb.sphere((rnd.uniform(-1.2, 1.2), -4.5 + 1.6 * k + 0.7, 0.0), 0.5, "grass", segments=5, rings=3, scale=(1.4, 0.8, 0.25))
    ivy(mb, rnd, -2.6, -0.95, 0.9, 5.5, 12, 0.6)
    ivy(mb, rnd, 2.6, 0.95, 0.9, 4.0, 8, 0.6)
    column(mb, 5.0, -1.0, 0.0, 2.2, 0.35, "marble", (0, 0), True)
    column(mb, -5.0, -1.0, 0.0, 4.2, 0.35)
    kit.save(mb, FAMILY, "site_ancient_gate", COLORS)


MODELS = {
    "site_crypt": crypt,
    "site_cave": cave,
    "site_ruined_tower": ruined_tower,
    "site_sunken_temple": sunken_temple,
    "site_stone_circle": stone_circle,
    "site_abandoned_mine": abandoned_mine,
    "site_giant_bones": giant_bones,
    "site_colossal_head": colossal_head,
    "site_battlefield": battlefield,
    "site_hermit_hut": hermit_hut,
    "site_fairy_ring": fairy_ring,
    "site_ancient_gate": ancient_gate,
}

kit.run(MODELS, FAMILY)
