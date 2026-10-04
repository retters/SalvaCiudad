"""Crafts proposals: one work station per trade, small enough to stand by a
house, each showing its work. See ../LEEME.md.

    blender --background --factory-startup --python art/blender/proposals/crafts/build.py -- [ids]
"""

import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import _kit as kit  # noqa: E402
import _shapes  # noqa: E402
import common  # noqa: E402
from _shapes import TAU, barrel, beam, crate, log, rope, sack, shed_roof, solid, wheel  # noqa: E402

FAMILY = "crafts"
C = common.rgb
COLORS = {
    **_shapes.COLORS,
    "clay": C(0xB8704A), "clay_wet": C(0x8A5A44), "clay_dark": C(0x8A5234), "glaze": C(0x3A7A8A), "linen": C(0xE0D8C0), "wool": C(0xECE6D6), "thread_red": C(0xB8362E),
    "thread_blue": C(0x2E5A9A), "thread_yellow": C(0xD8A83A), "hide": C(0xB08A60), "hide_dark": C(0x7A5A3A), "tan_water": C(0x6A5238), "wax": C(0xECE6D6),
    "flame": C(0xF2A23A), "ember": C(0xD8502A), "glass": C(0x9AD8E0), "glass_hot": C(0xFFB04A), "brick": C(0xA0553A), "brick_dark": C(0x84422C), "cave": C(0x14110F),
    "apple": C(0xC8402E), "apple_green": C(0x9AB840), "juice": C(0xC8922E), "cheese": C(0xE8C860), "milk": C(0xF4F0E4), "olive": C(0x5A6A2E), "oil": C(0xC8B040),
    "feather": C(0xE8E0D0), "parchment": C(0xE6D8B0), "ink": C(0x2E2A26), "meat": C(0xB84A4A), "meat_fat": C(0xE8C8B8), "wicker": C(0xB08A4A),
    "wicker_dark": C(0x8A6A34), "shingle": C(0x6A5038), "shingle_dark": C(0x54402C), "thatch": C(0xC9A55A), "thatch_dark": C(0xA8863F), "water": C(0x4A8FC0),
    "soap": C(0xD8E0C0), "bronze": C(0x9A7A3A),
}


def floor(mb, w, d, mat="stone_dark"):
    mb.box((0, 0, 0.04), (w, d, 0.08), mat)


def bench(mb, x, y, w, d, h=0.8, mat="plank", z0=0.08):
    mb.box((x, y, z0 + h), (w, d, 0.07), mat)
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.box((x + sx * (w / 2 - 0.07), y + sy * (d / 2 - 0.07), z0 + h / 2), (0.08, 0.08, h), "pole_dark")


def canopy(mb, w, d, low=2.1, high=2.6, mats=("thatch", "thatch_dark")):
    for sx in (-1, 1):
        mb.cylinder((sx * (w / 2 - 0.1), -d / 2 + 0.1, 0), (sx * (w / 2 - 0.1), -d / 2 + 0.1, low), 0.06, 0.05, "pole", segments=6)
        mb.cylinder((sx * (w / 2 - 0.1), d / 2 - 0.1, 0), (sx * (w / 2 - 0.1), d / 2 - 0.1, high), 0.06, 0.05, "pole", segments=6)
    shed_roof(mb, 0, 0, w, d, low, high, mats, 0.2, 3)


def loom():
    """An upright loom: the heddle bar goes up and down and the cloth grows."""
    mb = kit.begin()
    floor(mb, 3.0, 2.4, "plank_dark")
    for sx in (-1, 1):
        mb.box((sx * 0.9, 0.3, 1.1), (0.12, 0.14, 2.1), "pole")
        beam(mb, (sx * 0.9, 0.3, 1.6), (sx * 0.9, 1.0, 0.1), 0.04, "pole_dark")
    mb.cylinder((-1.0, 0.3, 2.1), (1.0, 0.3, 2.1), 0.07, 0.07, "pole_dark", segments=6)
    mb.cylinder((-1.0, 0.3, 0.5), (1.0, 0.3, 0.5), 0.09, 0.09, "linen", segments=8)        # The cloth already woven, rolled.
    mb.box((0, 0.27, 0.95), (1.5, 0.02, 0.8), "linen")
    for k in range(3):
        mb.box((0, 0.26, 0.7 + 0.25 * k), (1.5, 0.02, 0.05), ("thread_red", "thread_blue", "thread_yellow")[k])
    for k in range(16):                                                          # The warp, weighted with stones.
        x = -0.72 + 0.096 * k
        rope(mb, (x, 0.3, 2.05), (x, 0.3 + 0.04 * (k % 2), 1.35), 0.006)
        if k % 4 == 0:
            mb.sphere((x, 0.5, 0.25), 0.07, "stone", segments=5, rings=3)
            rope(mb, (x, 0.34, 1.35), (x, 0.5, 0.3), 0.005)
    w = {"heddle": 1.0}
    mb.cylinder((-0.95, 0.2, 1.4), (0.95, 0.2, 1.4), 0.03, 0.03, "pole_dark", w, segments=5)
    ws = {"shuttle": 1.0}
    mb.box((0, 0.22, 1.36), (0.3, 0.05, 0.05), "plank_light", ws)
    mb.box((0, 0.22, 1.36), (0.16, 0.06, 0.04), "thread_red", ws)
    for k, mat in enumerate(("thread_red", "thread_blue", "thread_yellow", "wool")):          # A basket of yarn.
        mb.sphere((1.2 + 0.12 * (k % 2), -0.6 + 0.14 * (k // 2), 0.3), 0.1, mat, segments=6, rings=4)
    mb.cylinder((1.26, -0.53, 0.08), (1.26, -0.53, 0.28), 0.18, 0.24, "wicker", segments=8)
    mb.box((0, -0.5, 0.35), (0.9, 0.35, 0.06), "plank")
    for sx in (-0.35, 0.35):
        mb.box((sx, -0.5, 0.2), (0.06, 0.3, 0.26), "pole_dark")

    def weave(t):
        return {}, {"heddle": (0, -0.1 * (0.5 + 0.5 * math.sin(TAU * 2 * t)), 0), "shuttle": (0.65 * math.sin(TAU * t), 0, 0)}

    mech = kit.Mech([("heddle", (0, 0.2, 1.4), (0.5, 0.2, 1.4), None), ("shuttle", (0, 0.22, 1.36), (0.3, 0.22, 1.36), None)]).clip("weave", 2.0, weave)
    kit.save(mb, FAMILY, "craft_loom", COLORS, mech=mech)


def potter():
    mb = kit.begin()
    floor(mb, 3.2, 2.6)
    canopy(mb, 3.2, 2.6)
    mb.cylinder((0, -0.2, 0.08), (0, -0.2, 0.3), 0.5, 0.5, "plank_dark", segments=10)       # The kick wheel.
    mb.cylinder((0, -0.2, 0.3), (0, -0.2, 0.8), 0.05, 0.05, "iron", segments=6)
    w = {"wheel": 1.0}
    mb.cylinder((0, -0.2, 0.8), (0, -0.2, 0.86), 0.32, 0.32, "plank", w, segments=10)
    mb.cylinder((0, -0.2, 0.86), (0, -0.2, 1.05), 0.12, 0.17, "clay_wet", w, segments=8)
    mb.cylinder((0, -0.2, 1.05), (0, -0.2, 1.2), 0.17, 0.11, "clay_wet", w, segments=8)
    mb.box((0.14, -0.2, 0.95), (0.05, 0.05, 0.08), "clay_dark", w)                          # A lump, so the turning shows.
    mb.box((0, 0.4, 0.45), (0.5, 0.3, 0.08), "plank")
    bench(mb, -1.0, 0.8, 1.0, 0.6)
    for k in range(5):
        x = -1.35 + 0.18 * k
        mb.cylinder((x, 0.8, 0.92), (x, 0.8, 1.05 + 0.04 * (k % 2)), 0.06, 0.08, "clay", segments=7)
        mb.cylinder((x, 0.8, 1.05 + 0.04 * (k % 2)), (x, 0.8, 1.15 + 0.04 * (k % 2)), 0.08, 0.05, "clay", segments=7)
    mb.box((1.0, 0.7, 0.5), (0.9, 0.9, 0.9), "brick")                                       # A small kiln.
    mb.cylinder((1.0, 0.7, 0.95), (1.0, 0.7, 1.5), 0.5, 0.2, "brick_dark", segments=8)
    mb.box((1.0, 0.24, 0.4), (0.4, 0.04, 0.4), "cave")
    mb.box((1.0, 0.23, 0.3), (0.3, 0.04, 0.18), "flame")
    mb.sphere((-1.1, -0.8, 0.08), 0.35, "clay_wet", segments=7, rings=4, scale=(1.2, 1, 0.6))
    mb.cylinder((0.7, -0.8, 0.08), (0.7, -0.8, 0.36), 0.14, 0.18, "plank_light", segments=8)
    mb.cylinder((0.7, -0.8, 0.33), (0.7, -0.8, 0.35), 0.15, 0.15, "water", segments=8)
    pose = lambda t: ({"wheel": [(kit.Z, 360.0 * t)]}, {})   # noqa: E731
    kit.save(mb, FAMILY, "craft_potter", COLORS, mech=kit.Mech([("wheel", (0, -0.2, 0.8), (0, -0.2, 1.2), None)]).clip("turn", 1.2, pose))


def tanner():
    mb = kit.begin()
    rnd = random.Random(3)
    floor(mb, 4.0, 3.0, "plank_dark")
    for k in range(2):                                                           # Soaking pits.
        x = -1.1 + 1.2 * k
        mb.cylinder((x, -0.7, 0.08), (x, -0.7, 0.55), 0.5, 0.55, "plank", segments=10)
        mb.cylinder((x, -0.7, 0.5), (x, -0.7, 0.53), 0.47, 0.47, "tan_water", segments=10)
        for z in (0.2, 0.42):
            mb.cylinder((x, -0.7, z), (x, -0.7, z + 0.04), 0.56, 0.56, "iron", segments=10)
    solid(mb, [(-1.3, -0.9, 0.56), (-0.9, -0.9, 0.56), (-0.9, -0.5, 0.6), (-1.3, -0.5, 0.6)], (0, 0, 0.03), "hide_dark")
    for k in range(2):                                                           # Hides laced to frames to dry.
        x = -0.9 + 1.9 * k
        for sx in (-0.6, 0.6):
            beam(mb, (x + sx, 1.1, 0), (x + sx, 0.75, 1.9), 0.04, "pole")
        for z, dy in ((0.25, 1.05), (1.85, 0.76)):
            beam(mb, (x - 0.65, dy, z), (x + 0.65, dy, z), 0.035, "pole")
        solid(mb, [(x - 0.45, 1.0, 0.45), (x + 0.4, 1.0, 0.5), (x + 0.5, 0.82, 1.55), (x, 0.8, 1.7), (x - 0.5, 0.82, 1.5)], (0, -0.03, 0), "hide" if k else "hide_dark")
        for _ in range(8):
            a = rnd.uniform(0, TAU)
            rope(mb, (x + math.cos(a) * 0.45, 0.92, 1.05 + math.sin(a) * 0.5), (x + math.cos(a) * 0.62, 0.93, 1.05 + math.sin(a) * 0.78), 0.006)
    log(mb, (1.5, -1.2, 0.5), (1.5, -0.2, 0.9), 0.18)                             # The beam hides are scraped on.
    beam(mb, (1.3, -1.2, 0), (1.5, -1.15, 0.5), 0.04, "pole_dark")
    beam(mb, (1.7, -1.2, 0), (1.5, -1.15, 0.5), 0.04, "pole_dark")
    solid(mb, [(1.3, -0.9, 0.72), (1.7, -0.9, 0.72), (1.75, -0.3, 0.95), (1.25, -0.3, 0.95)], (0, 0, 0.03), "hide")
    w = {"knife": 1.0}
    beam(mb, (1.25, -0.6, 0.9), (1.75, -0.6, 0.9), 0.02, "steel", w)
    for sx in (1.22, 1.78):
        mb.cylinder((sx, -0.6, 0.9), (sx, -0.6, 1.0), 0.025, 0.025, "pole", w, segments=5)
    barrel(mb, -1.7, 0.2, 0.08, 0.8, 0.3)
    sack(mb, 1.7, 0.6, 0.08, 0.22)
    pose = lambda t: ({}, {"knife": (0, 0.22 * math.sin(TAU * t), 0.09 * math.sin(TAU * t))})   # noqa: E731
    kit.save(mb, FAMILY, "craft_tanner", COLORS, mech=kit.Mech([("knife", (1.5, -0.6, 0.9), (1.5, -0.3, 0.95), None)]).clip("scrape", 1.6, pose))


def cooper():
    mb = kit.begin()
    floor(mb, 3.4, 2.6, "plank_dark")
    mb.cylinder((0, 0, 0.08), (0, 0, 0.2), 0.42, 0.42, "plank_dark", segments=10)           # A barrel half raised: staves splayed in a hoop.
    for k in range(12):
        a = TAU * k / 12
        mb.box((math.cos(a) * 0.36, math.sin(a) * 0.36, 0.55), (0.06, 0.17, 0.9), "plank" if k % 2 else "plank_light", rotation_z=a)
        mb.box((math.cos(a) * 0.46, math.sin(a) * 0.46, 0.98), (0.06, 0.17, 0.2), "plank" if k % 2 else "plank_light", rotation_z=a)
    mb.cylinder((0, 0, 0.3), (0, 0, 0.36), 0.41, 0.41, "iron", segments=12)
    w = {"hoop": 1.0}
    mb.cylinder((0, 0, 0.72), (0, 0, 0.78), 0.44, 0.44, "iron", w, segments=12)
    mb.cylinder((0, 0, 0.08), (0, 0, 0.3), 0.14, 0.0, "flame", segments=5)                  # A fire inside softens the wood.
    bench(mb, 1.1, 0.7, 1.0, 0.5, 0.7)
    for k in range(3):
        mb.cylinder((0.8 + 0.25 * k, 0.7, 0.86), (0.8 + 0.25 * k, 0.72, 0.86), 0.2 - 0.02 * k, 0.2 - 0.02 * k, "iron", segments=10)
    mb.cylinder((1.35, 0.6, 0.86), (1.35, 0.6, 1.0), 0.05, 0.05, "pole", segments=6)
    barrel(mb, -1.1, 0.7, 0.08, 0.9, 0.34)
    barrel(mb, -1.2, -0.6, 0.08, 0.6, 0.26)
    for k in range(7):
        mb.box((1.0 + 0.09 * k, -0.8, 0.5), (0.06, 0.16, 0.9), "plank_light", rotation_z=0.2)
    pose = lambda t: ({}, {"hoop": (0, 0, -0.25 * (0.5 - 0.5 * math.cos(TAU * t)))})   # noqa: E731
    kit.save(mb, FAMILY, "craft_cooper", COLORS, mech=kit.Mech([("hoop", (0, 0, 0.75), (0, 0, 0.4), None)]).clip("drive", 2.0, pose))


def wheelwright():
    mb = kit.begin()
    floor(mb, 3.6, 2.8, "plank_dark")
    canopy(mb, 3.6, 2.8, 2.2, 2.7, ("shingle", "shingle_dark"))
    mb.cylinder((0, 0, 0.08), (0, 0, 0.6), 0.12, 0.1, "pole_dark", segments=6)              # A wheel flat on its stand, being spoked.
    w = {"wheel": 1.0}
    start = _shapes.mark(mb)
    wheel(mb, (0, 0, 0), 0.62, "wheel", 0.09)
    for v in mb.bm.verts:                                                        # Laid flat: its axle up.
        if v not in start:
            x, y, z = v.co
            v.co = (y, z, x + 0.66)
    for sx, y in ((-1.4, 0.9), (1.4, 0.9)):
        wheel(mb, (sx, y, 0.6), 0.52, None, 0.08)
    bench(mb, 0, 1.0, 1.4, 0.5)
    for k in range(5):
        beam(mb, (-0.5 + 0.2 * k, 0.9, 0.93), (-0.45 + 0.2 * k, 1.15, 0.93), 0.025, "plank_light")
    mb.box((0.5, 1.0, 0.94), (0.2, 0.08, 0.08), "iron")
    for k in range(4):
        a0, a1 = math.pi * k / 4, math.pi * (k + 1) / 4
        beam(mb, (-1.3 + math.cos(a0) * 0.5, -0.9, 0.12 + math.sin(a0) * 0.5), (-1.3 + math.cos(a1) * 0.5, -0.9, 0.12 + math.sin(a1) * 0.5), 0.05, "plank")
    log(mb, (0.7, -1.0, 0.2), (1.6, -0.8, 0.2), 0.12)
    pose = lambda t: ({"wheel": [(kit.Z, 45.0 * kit.smooth(t))]}, {})   # noqa: E731
    kit.save(mb, FAMILY, "craft_wheelwright", COLORS, mech=kit.Mech([("wheel", (0, 0, 0.66), (0, 0, 1.0), None)]).clip("turn", 2.0, pose))


def chandler():
    """Candles dipped again and again on a wheel over hot tallow."""
    mb = kit.begin()
    floor(mb, 2.8, 2.4)
    mb.box((0, 0, 0.35), (0.9, 0.9, 0.55), "brick")
    mb.box((0, -0.46, 0.3), (0.36, 0.04, 0.3), "cave")
    mb.box((0, -0.47, 0.22), (0.26, 0.04, 0.14), "flame")
    mb.cylinder((0, 0, 0.62), (0, 0, 0.95), 0.34, 0.38, "iron", segments=10)
    mb.cylinder((0, 0, 0.9), (0, 0, 0.93), 0.35, 0.35, "wax", segments=10)
    mb.cylinder((0.9, 0, 0.08), (0.9, 0, 2.0), 0.05, 0.045, "pole", segments=6)
    beam(mb, (0.9, 0, 1.95), (0, 0, 1.95), 0.035, "pole_dark")
    w = {"rack": 1.0}
    mb.cylinder((0, 0, 1.55), (0, 0, 1.93), 0.02, 0.02, "iron", w, segments=4)
    for k in range(8):
        a = TAU * k / 8
        beam(mb, (0, 0, 1.55), (math.cos(a) * 0.6, math.sin(a) * 0.6, 1.55), 0.015, "pole", w)
        x, y = math.cos(a) * 0.55, math.sin(a) * 0.55
        rope(mb, (x, y, 1.55), (x, y, 1.45), 0.004, w)
        mb.cylinder((x, y, 1.45), (x, y, 1.15), 0.02 + 0.004 * (k % 3), 0.026 + 0.004 * (k % 3), "wax", w, segments=5)
    bench(mb, -1.0, 0.6, 0.7, 0.5, 0.7)
    for k in range(6):
        mb.cylinder((-1.2 + 0.08 * k, 0.6, 0.86), (-1.2 + 0.08 * k, 0.6, 1.1), 0.02, 0.02, "wax", segments=5)
    crate(mb, -0.9, -0.7, 0.08, 0.45)
    pose = lambda t: ({"rack": [(kit.Z, 360.0 * t)]}, {})   # noqa: E731
    kit.save(mb, FAMILY, "craft_chandler", COLORS, mech=kit.Mech([("rack", (0, 0, 1.55), (0, 0, 1.9), None)]).clip("dip", 6.0, pose))


def glassblower():
    mb = kit.begin()
    floor(mb, 3.6, 2.8)
    mb.cylinder((0, 0.6, 0.08), (0, 0.6, 1.3), 0.9, 0.8, "brick", segments=10)              # The furnace: a dome with its glory hole.
    mb.sphere((0, 0.6, 1.3), 0.8, "brick_dark", segments=10, rings=6, scale=(1, 1, 0.8))
    mb.cylinder((0, 0.6, 1.9), (0, 0.6, 2.5), 0.2, 0.16, "brick", segments=8)
    mb.box((0, -0.24, 1.1), (0.4, 0.1, 0.36), "cave")
    mb.box((0, -0.26, 1.08), (0.3, 0.06, 0.24), "flame")
    mb.box((0, -0.26, 0.4), (0.4, 0.08, 0.3), "cave")
    mb.box((0, -0.28, 0.32), (0.28, 0.06, 0.14), "ember")
    w = {"pipe": 1.0}
    mb.cylinder((0.0, -0.4, 1.15), (0.0, -1.7, 1.2), 0.018, 0.018, "iron", w, segments=5)     # The blowpipe with its gather.
    mb.sphere((0.0, -0.5, 1.15), 0.11, "glass_hot", w, segments=7, rings=5)
    for sx in (-0.35, 0.35):                                                     # The arms of the bench it rolls on.
        mb.box((sx, -1.2, 0.6), (0.08, 0.9, 1.0), "plank_dark")
    mb.box((0, -1.2, 0.5), (0.7, 0.5, 0.06), "plank")
    bench(mb, 1.3, 0.4, 0.8, 0.6)
    for k in range(5):
        x = 1.05 + 0.13 * k
        mb.cylinder((x, 0.4, 0.92), (x, 0.4, 1.0 + 0.05 * (k % 2)), 0.05, 0.06, "glass", segments=7)
        mb.cylinder((x, 0.4, 1.0 + 0.05 * (k % 2)), (x, 0.4, 1.12 + 0.05 * (k % 2)), 0.06, 0.025, "glass", segments=7)
    mb.cylinder((-1.3, -0.6, 0.08), (-1.3, -0.6, 0.5), 0.2, 0.25, "plank_light", segments=8)
    mb.cylinder((-1.3, -0.6, 0.45), (-1.3, -0.6, 0.48), 0.21, 0.21, "water", segments=8)
    mb.sphere((-1.3, 0.6, 0.08), 0.35, "sack", segments=7, rings=4, scale=(1.2, 1, 0.6))     # Sand.
    pose = lambda t: ({"pipe": [(kit.Y, 360.0 * t)]}, {"pipe": (0, 0.08 * math.sin(TAU * t), 0)})   # noqa: E731
    kit.save(mb, FAMILY, "craft_glassblower", COLORS, mech=kit.Mech([("pipe", (0, -0.4, 1.15), (0, -1.7, 1.2), None)]).clip("gather", 3.0, pose))


def press(name, kind):
    """A screw press: cider, oil or cheese, by what is put under it."""
    def build():
        mb = kit.begin()
        floor(mb, 3.2, 2.6, "plank_dark")
        for sx in (-0.8, 0.8):
            mb.box((sx, 0, 1.2), (0.2, 0.24, 2.3), "pole")
        mb.box((0, 0, 2.3), (1.9, 0.3, 0.24), "pole_dark")
        mb.box((0, 0, 0.3), (1.9, 1.0, 0.2), "pole_dark")
        mb.box((0, 0, 0.45), (1.3, 0.9, 0.12), "plank")
        w = {"screw": 1.0}
        mb.cylinder((0, 0, 1.0), (0, 0, 2.5), 0.07, 0.07, "pole_dark", w, segments=8)
        for k in range(7):
            mb.cylinder((0, 0, 1.2 + 0.18 * k), (0, 0, 1.25 + 0.18 * k), 0.095, 0.095, "pole", w, segments=8)
        beam(mb, (-0.9, 0, 2.6), (0.9, 0, 2.6), 0.035, "pole", w)
        mb.box((0, 0, 0.98), (1.0, 0.7, 0.1), "plank_dark", w)
        juice = {"cider": "juice", "oil": "oil", "cheese": "milk"}[kind]
        if kind == "cheese":
            for k in range(2):
                mb.cylinder((-0.3 + 0.6 * k, 0, 0.51), (-0.3 + 0.6 * k, 0, 0.9), 0.24, 0.24, "plank_light", segments=10)
                mb.cylinder((-0.3 + 0.6 * k, 0, 0.88), (-0.3 + 0.6 * k, 0, 0.92), 0.2, 0.2, "cheese", segments=10)
        else:
            for k in range(4):
                mb.box((0, 0, 0.56 + 0.1 * k), (0.95, 0.65, 0.08), "sack" if k % 2 else ("apple" if kind == "cider" else "olive"))
        beam(mb, (0.6, -0.4, 0.45), (0.9, -0.9, 0.3), 0.03, "plank")              # The spout and the tub under it.
        mb.cylinder((0.95, -1.0, 0.08), (0.95, -1.0, 0.36), 0.22, 0.26, "plank_light", segments=8)
        mb.cylinder((0.95, -1.0, 0.32), (0.95, -1.0, 0.35), 0.23, 0.23, juice, segments=8)
        if kind == "cider":
            mb.cylinder((-1.2, -0.8, 0.08), (-1.2, -0.8, 0.4), 0.3, 0.36, "wicker", segments=9)
            for k in range(7):
                mb.sphere((-1.2 + 0.14 * math.cos(k), -0.8 + 0.14 * math.sin(k), 0.44), 0.08, "apple" if k % 2 else "apple_green", segments=5, rings=3)
            barrel(mb, 1.2, 0.8, 0.08, 0.8, 0.3)
        elif kind == "oil":
            for k in range(3):
                mb.cylinder((-1.2 + 0.3 * k, 0.8, 0.08), (-1.2 + 0.3 * k, 0.8, 0.45), 0.1, 0.14, "clay", segments=8)
                mb.cylinder((-1.2 + 0.3 * k, 0.8, 0.45), (-1.2 + 0.3 * k, 0.8, 0.6), 0.14, 0.06, "clay", segments=8)
            sack(mb, -1.2, -0.8, 0.08, 0.24)
        else:
            bench(mb, -1.1, 0.7, 0.8, 0.5, 0.7)
            for k in range(3):
                mb.cylinder((-1.3 + 0.2 * k, 0.7, 0.86), (-1.3 + 0.2 * k, 0.7, 0.98), 0.12, 0.12, "cheese", segments=9)
            mb.cylinder((1.2, 0.8, 0.08), (1.2, 0.8, 0.5), 0.18, 0.14, "steel", segments=8)   # A milk churn.

        def squeeze(t):
            s = 0.5 - 0.5 * math.cos(TAU * t)
            return {"screw": [(kit.Z, 720.0 * s)]}, {"screw": (0, 0, -0.14 * s)}

        kit.save(mb, FAMILY, name, COLORS, mech=kit.Mech([("screw", (0, 0, 1.0), (0, 0, 2.5), None)]).clip("press", 5.0, squeeze))
    return build


def fletcher():
    """Bows and arrows: a tillering frame, a shaving horse and bundles of shafts."""
    mb = kit.begin()
    floor(mb, 3.4, 2.4, "plank_dark")
    mb.box((0, 0.9, 1.1), (0.14, 0.14, 2.1), "pole")                              # The tiller: a bow drawn against a notched post.
    w = {"bow": 1.0}
    for s in (-1, 1):
        pts = [(0.0, 0.0), (0.45, -0.05), (0.85, -0.22)]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            beam(mb, (s * x0, 0.8 + y0, 1.95), (s * x1, 0.8 + y1, 1.95), 0.03, "plank_light", w)
    ws = {"string": 1.0}
    rope(mb, (-0.85, 0.58, 1.95), (0, 0.5, 1.95), 0.006, ws)
    rope(mb, (0.85, 0.58, 1.95), (0, 0.5, 1.95), 0.006, ws)
    rope(mb, (0, 0.5, 1.95), (0, 0.5, 0.5), 0.008, ws)
    bench(mb, -1.0, -0.4, 1.2, 0.5, 0.75)
    for k in range(6):                                                           # Arrows in the making.
        y = -0.55 + 0.06 * k
        beam(mb, (-1.5, y, 0.88), (-0.6, y, 0.88), 0.01, "plank_light")
        solid(mb, [(-1.5, y, 0.88), (-1.35, y, 0.88), (-1.4, y, 0.94)], (0, 0.004, 0), "feather")
        mb.cylinder((-0.6, y, 0.88), (-0.52, y, 0.88), 0.016, 0.0, "steel", segments=4)
    mb.cylinder((1.1, -0.6, 0.08), (1.1, -0.6, 0.7), 0.16, 0.2, "leather", segments=8)
    for k in range(7):
        a = TAU * k / 7
        beam(mb, (1.1 + math.cos(a) * 0.08, -0.6 + math.sin(a) * 0.08, 0.3), (1.1 + math.cos(a) * 0.12, -0.6 + math.sin(a) * 0.12, 1.05), 0.01, "plank_light")
        mb.sphere((1.1 + math.cos(a) * 0.12, -0.6 + math.sin(a) * 0.12, 1.07), 0.03, "feather", segments=4, rings=3)
    for k in range(4):
        beam(mb, (1.4, 0.2 + 0.1 * k, 0.1), (1.5, 0.9 + 0.05 * k, 1.7), 0.022, "plank" if k % 2 else "plank_light")
    crate(mb, -1.3, 0.8, 0.08, 0.45)

    def draw(t):
        s = 0.5 - 0.5 * math.cos(TAU * t)
        return {}, {"string": (0, -0.3 * s, 0), "bow": (0, -0.06 * s, 0)}

    mech = kit.Mech([("bow", (0, 0.8, 1.95), (0.5, 0.8, 1.95), None), ("string", (0, 0.5, 1.95), (0, 0.5, 1.0), None)]).clip("tiller", 3.0, draw)
    kit.save(mb, FAMILY, "craft_fletcher", COLORS, mech=mech)


def basketmaker():
    mb = kit.begin()
    rnd = random.Random(5)
    floor(mb, 3.0, 2.4, "plank_dark")
    w = {"basket": 1.0}
    mb.cylinder((0, 0, 0.08), (0, 0, 0.14), 0.3, 0.3, "wicker_dark", w, segments=10)         # One half woven: stakes standing up.
    mb.cylinder((0, 0, 0.14), (0, 0, 0.42), 0.3, 0.36, "wicker", w, segments=10)
    for k in range(10):
        a = TAU * k / 10
        beam(mb, (math.cos(a) * 0.35, math.sin(a) * 0.35, 0.4), (math.cos(a) * 0.45, math.sin(a) * 0.45, 0.95), 0.012, "wicker_dark", w)
    for k, (x, y, r, h) in enumerate(((1.0, 0.6, 0.3, 0.4), (1.1, -0.5, 0.22, 0.5), (-1.0, 0.7, 0.35, 0.3), (-0.9, 0.7, 0.25, 0.3))):
        z = 0.08 if k < 3 else 0.4
        mb.cylinder((x, y, z), (x, y, z + h), r * 0.8, r, "wicker" if k % 2 else "wicker_dark", segments=9)
        mb.cylinder((x, y, z + h), (x, y, z + h + 0.03), r * 1.05, r * 1.05, "wicker_dark", segments=9)
    for k in range(12):                                                          # Bundles of osier soaking and waiting.
        beam(mb, (-1.3 + rnd.uniform(-0.05, 0.05), -0.9 + 0.03 * k, 0.12 + 0.01 * (k % 3)), (0.2, -0.95 + 0.03 * k, 0.12 + 0.01 * (k % 3)), 0.012, "wicker" if k % 2 else "wicker_dark")
    mb.box((-0.5, -0.9, 0.2), (0.14, 0.5, 0.06), "rope")
    _shapes.stump(mb, 0.0, 0.8, 0.4, 0.2)
    pose = lambda t: ({"basket": [(kit.Z, 360.0 * t)]}, {})   # noqa: E731
    kit.save(mb, FAMILY, "craft_basketmaker", COLORS, mech=kit.Mech([("basket", (0, 0, 0.1), (0, 0, 0.6), None)]).clip("weave", 6.0, pose))


def scribe():
    mb = kit.begin()
    floor(mb, 2.6, 2.2, "plank_dark")
    canopy(mb, 2.6, 2.2, 2.1, 2.5, ("shingle", "shingle_dark"))
    for sx in (-0.5, 0.5):                                                       # A sloped desk.
        mb.box((sx, 0, 0.5), (0.08, 0.6, 0.9), "pole_dark")
    solid(mb, [(-0.6, -0.4, 0.95), (0.6, -0.4, 0.95), (0.6, 0.35, 1.25), (-0.6, 0.35, 1.25)], (0, 0, 0.05), "plank")
    solid(mb, [(-0.35, -0.3, 1.02), (0.35, -0.3, 1.02), (0.35, 0.25, 1.24), (-0.35, 0.25, 1.24)], (0, 0, 0.012), "parchment")
    for k in range(5):
        solid(mb, [(-0.25, -0.2 + 0.09 * k, 1.075 + 0.036 * k), (0.2 - 0.05 * (k % 2), -0.2 + 0.09 * k, 1.075 + 0.036 * k), (0.2 - 0.05 * (k % 2), -0.18 + 0.09 * k, 1.083 + 0.036 * k),
                   (-0.25, -0.18 + 0.09 * k, 1.083 + 0.036 * k)], (0, 0, 0.006), "ink")
    w = {"quill": 1.0}
    beam(mb, (0.1, -0.1, 1.12), (0.3, -0.2, 1.5), 0.008, "feather", w)
    solid(mb, [(0.2, -0.15, 1.3), (0.34, -0.22, 1.56), (0.28, -0.14, 1.5)], (0.01, 0.01, 0), "feather", w)
    mb.cylinder((0.5, 0.25, 1.28), (0.5, 0.25, 1.36), 0.04, 0.03, "ink")
    mb.box((0, -0.8, 0.45), (0.5, 0.4, 0.08), "plank")                           # His stool, a chest of scrolls, a candle.
    for sx in (-0.2, 0.2):
        mb.box((sx, -0.8, 0.25), (0.06, 0.3, 0.36), "pole_dark")
    mb.box((-0.9, 0.5, 0.33), (0.6, 0.45, 0.5), "plank_dark")
    for k in range(5):
        mb.cylinder((-1.1 + 0.1 * k, 0.4, 0.62), (-1.1 + 0.1 * k, 0.6, 0.62), 0.04, 0.04, "parchment", segments=6)
    mb.cylinder((-0.5, 0.3, 1.24), (-0.5, 0.3, 1.42), 0.025, 0.025, "wax", segments=5)
    mb.cylinder((-0.5, 0.3, 1.42), (-0.5, 0.3, 1.5), 0.02, 0.0, "flame", segments=4)
    pose = lambda t: ({}, {"quill": (-0.3 * (0.5 - 0.5 * math.cos(TAU * t)), 0.01 * math.sin(TAU * 8 * t), 0.01 * math.sin(TAU * 8 * t))})   # noqa: E731
    kit.save(mb, FAMILY, "craft_scribe", COLORS, mech=kit.Mech([("quill", (0.1, -0.1, 1.12), (0.3, -0.2, 1.5), None)]).clip("write", 3.0, pose))


def butcher():
    mb = kit.begin()
    floor(mb, 3.2, 2.4)
    canopy(mb, 3.2, 2.4, 2.2, 2.6, ("shingle", "shingle_dark"))
    mb.cylinder((0, -0.2, 0.08), (0, -0.2, 0.85), 0.4, 0.36, "bark", segments=9)             # The block.
    mb.cylinder((0, -0.2, 0.85), (0, -0.2, 0.9), 0.36, 0.36, "log_end", segments=9)
    mb.sphere((0.05, -0.2, 0.96), 0.14, "meat", segments=6, rings=4, scale=(1.4, 1, 0.6))
    w = {"cleaver": 1.0}
    mb.box((-0.2, -0.2, 1.3), (0.22, 0.02, 0.16), "steel", w)
    mb.cylinder((-0.34, -0.2, 1.3), (-0.55, -0.2, 1.3), 0.02, 0.02, "pole_dark", w, segments=5)
    beam(mb, (-1.4, 0.9, 2.2), (1.4, 0.9, 2.2), 0.04, "pole_dark")                # The rail of hooks.
    for k in range(5):
        x = -1.1 + 0.55 * k
        rope(mb, (x, 0.9, 2.2), (x, 0.9, 2.0), 0.01)
        if k % 2:
            mb.sphere((x, 0.9, 1.7), 0.18, "meat", segments=7, rings=5, scale=(0.8, 0.7, 1.7))
            mb.sphere((x + 0.05, 0.8, 1.75), 0.06, "meat_fat", segments=4, rings=3)
        else:
            for i in range(3):
                mb.cylinder((x - 0.08 + 0.08 * i, 0.9, 2.0), (x - 0.08 + 0.08 * i, 0.9, 1.5), 0.035, 0.035, "meat", segments=5)
    bench(mb, 1.0, -0.5, 0.9, 0.6)
    mb.box((1.0, -0.5, 0.93), (0.7, 0.4, 0.03), "plank_dark")
    for k in range(3):
        mb.sphere((0.8 + 0.2 * k, -0.5, 0.99), 0.08, "meat" if k % 2 else "meat_fat", segments=5, rings=3, scale=(1.3, 1, 0.6))
    barrel(mb, -1.2, -0.5, 0.08, 0.7, 0.28)

    def chop(t):
        lift = kit.smooth(min(1.0, t / 0.6)) - kit.smooth(min(1.0, max(0.0, (t - 0.6) / 0.15)))
        return {"cleaver": [(kit.Y, 20.0 * lift)]}, {"cleaver": (0, 0, -0.28 * (1 - lift))}

    kit.save(mb, FAMILY, "craft_butcher", COLORS, mech=kit.Mech([("cleaver", (-0.55, -0.2, 1.3), (-0.1, -0.2, 1.3), None)]).clip("chop", 1.4, chop))


def soap_boiler():
    mb = kit.begin()
    floor(mb, 3.0, 2.4)
    for k in range(4):
        a = TAU * k / 4 + 0.4
        mb.sphere((math.cos(a) * 0.5, math.sin(a) * 0.5, 0.2), 0.2, "stone", segments=5, rings=3)
    mb.cylinder((0, 0, 0.08), (0, 0, 0.35), 0.2, 0.0, "flame", segments=5)
    mb.sphere((0, 0, 0.75), 0.6, "iron", segments=10, rings=6, scale=(1, 1, 0.8))
    mb.cylinder((0, 0, 0.9), (0, 0, 1.02), 0.56, 0.6, "iron", segments=10)
    mb.cylinder((0, 0, 0.98), (0, 0, 1.03), 0.52, 0.52, "soap", segments=10)
    w = {"paddle": 1.0}
    beam(mb, (0.25, 0, 0.9), (0.6, -0.3, 2.0), 0.03, "pole", w)
    bench(mb, -1.0, 0.6, 0.9, 0.6, 0.7)
    for i in range(3):
        for j in range(2):
            mb.box((-1.25 + 0.25 * i, 0.5 + 0.22 * j, 0.89), (0.2, 0.16, 0.1), "soap")
    barrel(mb, 1.1, 0.7, 0.08, 0.8, 0.3)                                         # Ash lye and tallow.
    mb.sphere((1.0, -0.7, 0.08), 0.3, "stone_light", segments=6, rings=4, scale=(1.2, 1, 0.5))
    mb.cylinder((-1.1, -0.7, 0.08), (-1.1, -0.7, 0.4), 0.16, 0.2, "plank_light", segments=8)
    pose = lambda t: ({"paddle": [(kit.Z, 360.0 * t)]}, {})   # noqa: E731
    kit.save(mb, FAMILY, "craft_soap_boiler", COLORS, mech=kit.Mech([("paddle", (0, 0, 0.9), (0, 0, 2.0), None)]).clip("stir", 3.0, pose))


MODELS = {
    "craft_loom": loom, "craft_potter": potter, "craft_tanner": tanner, "craft_cooper": cooper, "craft_wheelwright": wheelwright,
    "craft_chandler": chandler, "craft_glassblower": glassblower,
    "craft_press_cider": press("craft_press_cider", "cider"), "craft_press_oil": press("craft_press_oil", "oil"), "craft_press_cheese": press("craft_press_cheese", "cheese"),
    "craft_fletcher": fletcher, "craft_basketmaker": basketmaker, "craft_scribe": scribe, "craft_butcher": butcher, "craft_soap_boiler": soap_boiler,
}

kit.run(MODELS, FAMILY)
