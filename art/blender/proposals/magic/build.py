"""Arcane works proposals: what a town with mages would build in its streets
and fields. See ../LEEME.md.

    blender --background --factory-startup --python art/blender/proposals/magic/build.py -- [ids]
"""

import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import _kit as kit  # noqa: E402
import _shapes  # noqa: E402
import common  # noqa: E402
from _shapes import TAU, beam, log, rock, rope, solid  # noqa: E402

FAMILY = "magic"
C = common.rgb
COLORS = {
    **_shapes.COLORS,
    "glow_blue": C(0x7AD8FF), "glow_violet": C(0xB98CFF), "glow_green": C(0x8CFFB0), "glow_gold": C(0xFFD66A), "glow_white": C(0xF4F6FF),
    "flame": C(0xF2A23A), "ember": C(0xD8502A), "obsidian": C(0x2A2630), "obsidian_light": C(0x443E50), "marble": C(0xE4E0D6), "marble_dark": C(0xC4BEB2),
    "moss": C(0x5E8A3A), "grass": C(0x6A9440), "leaf": C(0x4E8A3C), "leaf_light": C(0x7AB050), "soil": C(0x4A3828), "copper": C(0xB8703A), "bronze": C(0x9A7A3A),
    "cloth_violet": C(0x6A4A9A), "cloth_red": C(0x9A3A3A), "parchment": C(0xE6D8B0), "wax": C(0xECE6D6), "bone": C(0xE0D8C0), "cave": C(0x14110F),
    "brick": C(0xA0553A), "brick_dark": C(0x84422C), "water": C(0x4A8FC0), "feather": C(0xC84A3A), "dwarf_stone": C(0x5E5A5E), "dwarf_dark": C(0x444046),
}
# How each tradition builds: the stone it uses and the light of its magic.
STYLES = {
    "stone": {"wall": "stone", "dark": "stone_dark", "light": "stone_light", "glow": "glow_blue", "metal": "iron"},
    "obsidian": {"wall": "obsidian", "dark": "cave", "light": "obsidian_light", "glow": "glow_violet", "metal": "steel"},
    "elf": {"wall": "marble", "dark": "marble_dark", "light": "glow_white", "glow": "glow_green", "metal": "gold"},
    "dwarf": {"wall": "dwarf_stone", "dark": "dwarf_dark", "light": "stone", "glow": "glow_gold", "metal": "bronze"},
}


def crystal(mb, x, y, z, r, h, mat, w=None, lean=(0.0, 0.0), seg=6):
    mx, my = x + lean[0] * h * 0.75, y + lean[1] * h * 0.75
    mb.cylinder((x, y, z), (mx, my, z + h * 0.75), r * 0.8, r, mat, w, segments=seg)
    mb.cylinder((mx, my, z + h * 0.75), (x + lean[0] * h, y + lean[1] * h, z + h), r, 0.0, mat, w, segments=seg)


def shard(mb, x, y, z, r, h, mat, w=None):
    """A crystal pointed at both ends, to float."""
    mb.cylinder((x, y, z - h / 2), (x, y, z), 0.0, r, mat, w, segments=5)
    mb.cylinder((x, y, z), (x, y, z + h / 2), r, 0.0, mat, w, segments=5)


def cluster(mb, x, y, z, s, rnd, mats, n=5, w=None):
    crystal(mb, x, y, z, 0.16 * s, 1.0 * s, mats[0], w)
    for k in range(n):
        a = TAU * k / n + rnd.uniform(-0.3, 0.3)
        d = rnd.uniform(0.14, 0.24) * s
        crystal(mb, x + math.cos(a) * d, y + math.sin(a) * d, z, rnd.uniform(0.07, 0.12) * s, rnd.uniform(0.35, 0.7) * s, mats[(k + 1) % len(mats)], w,
                (math.cos(a) * 0.35, math.sin(a) * 0.35))


def rune_band(mb, x, y, z, r, n, mat, w=None, size=(0.04, 0.12, 0.2)):
    for k in range(n):
        a = TAU * k / n
        mb.box((x + math.cos(a) * r, y + math.sin(a) * r, z + 0.04 * (k % 2)), (size[0], size[1] * (0.7 + 0.3 * (k % 3)), size[2] * (1.0 - 0.3 * (k % 2))), mat, w, rotation_z=a)


def runes(mb, x, y, z0, z1, mat, n=5, face=-1, w=None):
    """A column of marks on a face that looks along Y."""
    rnd = random.Random(int(x * 100) + n)
    for k in range(n):
        z = z0 + (z1 - z0) * (k + 0.5) / n
        kind = rnd.randrange(3)
        if kind == 0:
            mb.box((x, y, z), (0.2, 0.02, 0.04), mat, w)
            mb.box((x, y, z), (0.04, 0.02, 0.18), mat, w)
        elif kind == 1:
            mb.box((x - 0.06, y, z), (0.04, 0.02, 0.2), mat, w)
            mb.box((x + 0.06, y, z + 0.03), (0.04, 0.02, 0.14), mat, w)
        else:
            mb.box((x, y, z + 0.07), (0.18, 0.02, 0.04), mat, w)
            mb.box((x, y, z - 0.07), (0.18, 0.02, 0.04), mat, w)
            mb.box((x + 0.07 * face, y, z), (0.04, 0.02, 0.14), mat, w)


def candle(mb, x, y, z, h=0.25, w=None):
    mb.cylinder((x, y, z), (x, y, z + h), 0.035, 0.03, "wax", w, segments=5)
    mb.cylinder((x, y, z + h), (x, y, z + h + 0.09), 0.025, 0.0, "flame", w, segments=4)


def stone_arch(mb, cx, y0, y1, z, r_in, r_out, mats, n=9, w=None):
    """A half ring standing in the XZ plane, `z` at its springing."""
    for i in range(n):
        a0, a1 = math.pi * i / n, math.pi * (i + 1) / n
        solid(mb, [(cx + math.cos(a0) * r_in, y0, z + math.sin(a0) * r_in), (cx + math.cos(a0) * r_out, y0, z + math.sin(a0) * r_out),
                   (cx + math.cos(a1) * r_out, y0, z + math.sin(a1) * r_out), (cx + math.cos(a1) * r_in, y0, z + math.sin(a1) * r_in)], (0, y1 - y0, 0), mats[i % len(mats)], w)


def ley_stone(name, style):
    """A standing stone on a line of power, with shards that circle it."""
    def build():
        mb = kit.begin()
        st = STYLES[style]
        rnd = random.Random(len(style))
        mb.cylinder((0, 0, 0), (0, 0, 0.14), 1.5, 1.35, st["dark"], segments=10)
        solid(mb, [(-0.55, -0.32, 0.1), (0.55, -0.32, 0.1), (0.42, -0.32, 3.1), (-0.1, -0.32, 3.7), (-0.42, -0.32, 3.0)], (0, 0.64, 0), st["wall"])
        solid(mb, [(-0.4, -0.37, 0.4), (0.4, -0.37, 0.4), (0.3, -0.37, 2.9), (-0.3, -0.37, 2.8)], (0, 0.74, 0), st["light"])
        runes(mb, 0, -0.385, 0.6, 2.7, st["glow"], 6)
        runes(mb, 0, 0.385, 0.6, 2.7, st["glow"], 5, 1)
        for k in range(7):
            a = TAU * k / 7 + 0.2
            rock(mb, math.cos(a) * 1.2, math.sin(a) * 1.2, 0.14, rnd.uniform(0.16, 0.26), rnd, st["wall"] if k % 2 else st["dark"])
        if style == "elf":
            for k in range(5):
                mb.sphere((rnd.uniform(-0.4, 0.4), rnd.choice((-0.36, 0.36)), rnd.uniform(0.2, 1.4)), 0.14, "moss", segments=5, rings=3, scale=(1, 0.4, 1))
        w = {"orbit": 1.0}
        for k in range(4):
            a = TAU * k / 4
            shard(mb, math.cos(a) * 1.25, math.sin(a) * 1.25, 1.9 + 0.35 * (k % 2), 0.11, 0.5, st["glow"], w)
        pose = lambda t: ({"orbit": [(kit.Z, 360.0 * t)]}, {"orbit": (0, 0, 0.12 * math.sin(TAU * 2 * t))})   # noqa: E731
        kit.save(mb, FAMILY, name, COLORS, mech=kit.Mech([("orbit", (0, 0, 1.5), (0, 0, 2.5), None)]).clip("hum", 8.0, pose))
    return build


def mana_well():
    mb = kit.begin()
    for k, (r, z) in enumerate(((2.2, 0.12), (1.9, 0.26))):
        mb.cylinder((0, 0, z - 0.14), (0, 0, z), r, r, "stone_dark" if k == 0 else "stone", segments=12)
    mb.cylinder((0, 0, 0.26), (0, 0, 0.8), 1.5, 1.5, "stone", segments=12)
    mb.cylinder((0, 0, 0.78), (0, 0, 0.9), 1.6, 1.6, "stone_light", segments=12)
    mb.cylinder((0, 0, 0.8), (0, 0, 0.92), 1.25, 1.25, "cave", segments=12)
    mb.cylinder((0, 0, 0.82), (0, 0, 0.86), 1.25, 1.25, "glow_blue", segments=12)
    rune_band(mb, 0, 0, 0.5, 1.51, 12, "glow_blue")
    for k in range(4):                                                           # Four claws of stone hold the air above it.
        a = TAU * k / 4 + TAU / 8
        pts = [(1.45, 0.9), (1.5, 1.9), (1.2, 2.7), (0.75, 3.2)]
        for (r0, z0), (r1, z1) in zip(pts, pts[1:]):
            mb.cylinder((math.cos(a) * r0, math.sin(a) * r0, z0), (math.cos(a) * r1, math.sin(a) * r1, z1), 0.17 - 0.03 * (z0 - 0.9), 0.14 - 0.03 * (z0 - 0.9), "stone", segments=6)
        crystal(mb, math.cos(a) * 0.72, math.sin(a) * 0.72, 3.15, 0.07, 0.3, "glow_blue", None, (-math.cos(a) * 0.6, -math.sin(a) * 0.6))
    w = {"orb": 1.0}
    mb.sphere((0, 0, 2.5), 0.42, "glow_blue", w, segments=8, rings=6)
    mb.sphere((0, 0, 2.5), 0.3, "glow_white", w, segments=6, rings=4, scale=(1.5, 1.5, 0.2))
    wd = {"drops": 1.0}
    for k in range(5):
        a = TAU * k / 5
        shard(mb, math.cos(a) * 0.5, math.sin(a) * 0.5, 1.3 + 0.25 * (k % 2), 0.05, 0.3, "glow_white", wd)

    def pose(t):
        return ({"orb": [(kit.Z, 360.0 * t)], "drops": [(kit.Z, -360.0 * t)]},
                {"orb": (0, 0, 0.12 * math.sin(TAU * t)), "drops": (0, 0, 0.3 * math.sin(TAU * 2 * t))})

    kit.save(mb, FAMILY, "magic_mana_well", COLORS, mech=kit.Mech([("orb", (0, 0, 2.5), (0, 0, 3.0), None), ("drops", (0, 0, 1.3), (0, 0, 1.8), None)]).clip("well_up", 6.0, pose))


def circle(name, kind):
    """A circle drawn to stay: for crossing the map, or for calling something up."""
    def build():
        mb = kit.begin()
        glow = "glow_blue" if kind == "teleport" else "glow_violet"
        dark = "stone_dark" if kind == "teleport" else "obsidian"
        for r, z, mat in ((2.5, 0.06, dark), (2.2, 0.075, glow), (2.08, 0.09, dark), (1.35, 0.105, glow), (1.26, 0.12, dark)):
            mb.cylinder((0, 0, 0), (0, 0, z), r, r, mat, segments=20)
        points = 6 if kind == "teleport" else 5
        skip = 2
        for k in range(points):
            a0, a1 = TAU * k / points + math.pi / 2, TAU * (k + skip) / points + math.pi / 2
            beam(mb, (math.cos(a0) * 2.0, math.sin(a0) * 2.0, 0.11), (math.cos(a1) * 2.0, math.sin(a1) * 2.0, 0.11), 0.03, glow)
        mb.cylinder((0, 0, 0), (0, 0, 0.135), 0.4, 0.4, glow, segments=10)
        for k in range(points):
            a = TAU * k / points + math.pi / 2
            x, y = math.cos(a) * 2.32, math.sin(a) * 2.32
            if kind == "teleport":
                mb.cylinder((x, y, 0), (x, y, 1.1), 0.2, 0.15, "stone", segments=6)
                mb.cylinder((x, y, 1.1), (x, y, 1.2), 0.2, 0.2, "stone_light", segments=6)
                crystal(mb, x, y, 1.2, 0.09, 0.45, glow)
            else:
                mb.cylinder((x, y, 0), (x, y, 0.7), 0.05, 0.03, "iron", segments=5)
                mb.cylinder((x, y, 0.7), (x, y, 0.74), 0.1, 0.1, "iron", segments=6)
                candle(mb, x, y, 0.74, 0.3)
        if kind == "summon":
            mb.sphere((0.9, -0.6, 0.2), 0.13, "bone", segments=6, rings=4)                    # What was asked for the calling.
            mb.box((0.9, -0.71, 0.18), (0.1, 0.03, 0.05), "cave")
            mb.cylinder((-0.8, 0.5, 0.12), (-0.8, 0.5, 0.26), 0.16, 0.2, "bronze", segments=8)
            mb.cylinder((-0.8, 0.5, 0.24), (-0.8, 0.5, 0.27), 0.17, 0.17, "ember", segments=8)
            mb.box((-0.2, -1.0, 0.16), (0.36, 0.26, 0.06), "cloth_violet", rotation_z=0.4)
            mb.box((-0.2, -1.0, 0.19), (0.3, 0.2, 0.02), "parchment", rotation_z=0.4)
        w = {"ring": 1.0}
        rune_band(mb, 0, 0, 1.3, 1.7, 10, glow, w, (0.03, 0.22, 0.28))
        w2 = {"ring2": 1.0}
        rune_band(mb, 0, 0, 2.0, 1.0, 6, glow, w2, (0.03, 0.2, 0.24))
        pose = lambda t: ({"ring": [(kit.Z, 360.0 * t)], "ring2": [(kit.Z, -720.0 * t)]}, {"ring": (0, 0, 0.1 * math.sin(TAU * 2 * t))})   # noqa: E731
        mech = kit.Mech([("ring", (0, 0, 1.3), (0, 0, 1.8), None), ("ring2", (0, 0, 2.0), (0, 0, 2.5), None)]).clip("turn", 10.0, pose)
        kit.save(mb, FAMILY, name, COLORS, mech=mech)
    return build


def crystal_bed(name, stage):
    """Crystals grown like a crop, 3 x 3 m."""
    def build():
        mb = kit.begin()
        rnd = random.Random(21)
        for s in (-1, 1):
            mb.box((0, s * 1.4, 0.12), (3.0, 0.2, 0.24), "stone")
            mb.box((s * 1.4, 0, 0.12), (0.2, 2.6, 0.24), "stone_dark")
        mb.box((0, 0, 0.09), (2.6, 2.6, 0.18), "soil")
        size = (0.3, 0.75, 1.5)[stage - 1]
        for i in range(4):
            for j in range(4):
                x, y = -0.9 + 0.6 * i + rnd.uniform(-0.1, 0.1), -0.9 + 0.6 * j + rnd.uniform(-0.1, 0.1)
                grow = rnd.uniform(0.7, 1.2)
                mats = ("glow_blue", "glow_violet", "glow_white") if stage == 3 else ("glow_violet", "obsidian_light") if stage == 2 else ("obsidian_light", "glow_violet")
                if stage == 1:
                    crystal(mb, x, y, 0.16, 0.05 * grow, size * grow, mats[(i + j) % 2])
                else:
                    cluster(mb, x, y, 0.16, size * grow, rnd, mats, 3 + stage)
        mb.cylinder((1.75, -1.2, 0), (1.75, -1.2, 0.32), 0.14, 0.18, "plank_light", segments=8)      # The water it is fed with.
        mb.cylinder((1.75, -1.2, 0.28), (1.75, -1.2, 0.31), 0.15, 0.15, "glow_blue", segments=8)
        if stage == 3:
            mb.box((-1.9, -1.0, 0.2), (0.5, 0.4, 0.4), "plank")
            cluster(mb, -1.9, -1.0, 0.4, 0.3, rnd, ("glow_blue", "glow_white"), 4)
        kit.save(mb, FAMILY, name, COLORS)
    return build


def alchemy():
    """An alchemist's yard: a still, a cauldron and what goes into them."""
    mb = kit.begin()
    rnd = random.Random(14)
    mb.box((0, 0.4, 0.05), (5.0, 3.4, 0.1), "stone_dark")
    for sx in (-2.3, 2.3):
        mb.cylinder((sx, 1.9, 0), (sx, 1.9, 2.9), 0.08, 0.07, "pole", segments=6)
        mb.cylinder((sx, -1.0, 0), (sx, -1.0, 2.3), 0.08, 0.07, "pole", segments=6)
    _shapes.shed_roof(mb, 0, 0.45, 4.8, 3.0, 2.3, 2.9, ("cloth_violet", "cloth_red"), 0.25, 4, 0.04)
    mb.box((-1.3, 1.0, 0.5), (1.0, 1.0, 0.8), "brick")                           # The still on its stove.
    mb.box((-1.3, 0.49, 0.35), (0.4, 0.04, 0.3), "cave")
    mb.box((-1.3, 0.48, 0.28), (0.3, 0.04, 0.14), "flame")
    mb.sphere((-1.3, 1.0, 1.25), 0.42, "copper", segments=8, rings=6)
    mb.cylinder((-1.3, 1.0, 1.55), (-1.3, 1.0, 1.95), 0.16, 0.22, "copper", segments=8)
    mb.sphere((-1.3, 1.0, 2.0), 0.22, "copper", segments=7, rings=5)
    mb.cylinder((-1.3, 1.0, 2.05), (-0.3, 1.0, 1.5), 0.06, 0.04, "copper", segments=6)
    mb.cylinder((-0.3, 1.0, 1.5), (-0.2, 1.0, 1.15), 0.04, 0.03, "copper", segments=6)
    mb.box((-0.2, 1.0, 0.45), (0.5, 0.5, 0.9), "plank_dark")
    mb.sphere((-0.2, 1.0, 1.03), 0.16, "glow_green", segments=7, rings=5)
    mb.cylinder((-0.2, 1.0, 1.12), (-0.2, 1.0, 1.25), 0.05, 0.06, "glow_white", segments=6)
    for k in range(3):                                                           # The cauldron on its tripod.
        a = TAU * k / 3 + 0.5
        beam(mb, (1.3 + math.cos(a) * 0.8, 0.2 + math.sin(a) * 0.8, 0.1), (1.3, 0.2, 2.0), 0.035, "iron")
    rope(mb, (1.3, 0.2, 2.0), (1.3, 0.2, 1.2), 0.012)
    mb.sphere((1.3, 0.2, 0.75), 0.5, "iron", segments=9, rings=6, scale=(1, 1, 0.85))
    mb.cylinder((1.3, 0.2, 0.9), (1.3, 0.2, 1.0), 0.47, 0.5, "iron", segments=9)
    mb.cylinder((1.3, 0.2, 0.96), (1.3, 0.2, 1.01), 0.43, 0.43, "glow_violet", segments=9)
    for k in range(4):
        log(mb, (1.3 + math.cos(k * 1.6) * 0.45, 0.2 + math.sin(k * 1.6) * 0.45, 0.16), (1.3 - math.cos(k * 1.6) * 0.2, 0.2 - math.sin(k * 1.6) * 0.2, 0.16), 0.06)
    mb.cylinder((1.3, 0.2, 0.1), (1.3, 0.2, 0.42), 0.2, 0.0, "flame", segments=5)
    w = {"bubbles": 1.0}
    for k in range(5):
        a = TAU * k / 5
        mb.sphere((1.3 + math.cos(a) * 0.22, 0.2 + math.sin(a) * 0.22, 1.02 + 0.03 * (k % 2)), 0.07 + 0.02 * (k % 3), "glow_violet", w, segments=5, rings=3)
    ws = {"steam": 1.0}
    for k in range(3):
        mb.sphere((1.3 + 0.12 * k - 0.12, 0.2, 1.5 + 0.22 * k), 0.12 + 0.04 * k, "glow_white", ws, segments=5, rings=3)
    mb.box((0.4, 1.7, 0.9), (2.2, 0.5, 0.06), "plank")                           # A bench of flasks.
    for sx in (-1.0, 1.0):
        mb.box((0.4 + sx, 1.7, 0.45), (0.08, 0.4, 0.86), "plank_dark")
    mb.box((0.4, 1.9, 1.5), (2.2, 0.2, 0.05), "plank")
    for k in range(9):
        x = -0.55 + 0.24 * k
        mat = ("glow_green", "glow_violet", "glow_blue", "glow_gold")[k % 4]
        z = 0.93 if k % 2 else 1.53
        y = 1.65 if k % 2 else 1.9
        mb.sphere((x, y, z + 0.08), 0.075, mat, segments=6, rings=4)
        mb.cylinder((x, y, z + 0.13), (x, y, z + 0.24), 0.025, 0.03, "glow_white", segments=5)
    for k in range(3):                                                           # Herbs hung to dry.
        mb.cylinder((-2.0 + 0.3 * k, 1.85, 1.9), (-2.0 + 0.3 * k, 1.85, 2.4), 0.09, 0.02, "leaf" if k % 2 else "leaf_light", segments=5)
    beam(mb, (-2.3, 1.85, 2.42), (-1.2, 1.85, 2.42), 0.02, "pole_dark")
    _shapes.barrel(mb, 2.0, 1.5, 0.1, 0.8, 0.3)
    _shapes.sack(mb, -2.0, -0.4, 0.1, 0.24)
    for _ in range(3):
        rock(mb, rnd.uniform(-1.9, -1.4), rnd.uniform(-0.9, -0.6), 0.2, 0.12, rnd, "glow_gold")

    def brew(t):
        return {"bubbles": [(kit.Z, 360.0 * t)]}, {"bubbles": (0, 0, 0.03 * math.sin(TAU * 4 * t)), "steam": (0.06 * math.sin(TAU * t), 0, 0.1 * math.sin(TAU * 2 * t))}

    mech = kit.Mech([("bubbles", (1.3, 0.2, 1.0), (1.3, 0.2, 1.3), None), ("steam", (1.3, 0.2, 1.5), (1.3, 0.2, 2.0), None)]).clip("brew", 4.0, brew)
    kit.save(mb, FAMILY, "magic_alchemy_yard", COLORS, mech=mech)


def golem_works():
    """A golem half put together under its gantry."""
    mb = kit.begin()
    rnd = random.Random(15)
    mb.box((0, 0, 0.06), (5.0, 4.0, 0.12), "stone_dark")
    for sx in (-2.0, 2.0):
        mb.box((sx, 0.6, 2.4), (0.24, 0.24, 4.8), "pole")
        beam(mb, (sx, -0.6, 0.1), (sx, 0.6, 2.0), 0.07, "pole_dark")
        beam(mb, (sx, 1.8, 0.1), (sx, 0.6, 2.0), 0.07, "pole_dark")
    mb.box((0, 0.6, 4.75), (4.5, 0.3, 0.3), "pole_dark")
    for sx in (-1, 1):
        beam(mb, (sx * 2.0, 0.6, 3.8), (sx * 1.2, 0.6, 4.6), 0.06, "pole_dark")
    for sx in (-0.5, 0.5):                                                       # Its legs stand ready.
        mb.box((sx, 0.6, 0.2), (0.6, 0.8, 0.28), "stone_dark")
        mb.box((sx, 0.65, 0.75), (0.45, 0.5, 0.85), "stone")
        mb.box((sx, 0.6, 1.3), (0.5, 0.55, 0.3), "stone_light")
    w = {"torso": 1.0}
    z = 1.75
    mb.box((0, 0.6, z + 0.25), (1.3, 0.75, 0.5), "stone", w)
    mb.box((0, 0.6, z + 0.9), (1.7, 0.9, 0.85), "stone_light", w)
    mb.box((0, 0.13, z + 0.9), (0.4, 0.06, 0.4), "cave", w)
    crystal(mb, 0, 0.1, z + 0.72, 0.12, 0.36, "glow_gold", w)
    mb.box((0, 0.55, z + 1.6), (0.6, 0.6, 0.55), "stone", w)
    for sx in (-1, 1):
        mb.box((sx * 0.15, 0.24, z + 1.65), (0.12, 0.04, 0.08), "glow_gold", w)
        mb.sphere((sx * 1.05, 0.6, z + 1.15), 0.34, "stone_dark", w, segments=6, rings=4)
        mb.cylinder((sx * 0.5, 0.6, z + 1.4), (sx * 0.3, 0.6, z + 2.6), 0.03, 0.03, "iron", w, segments=5)
    runes(mb, -0.55, 0.14, z + 0.6, z + 1.25, "glow_gold", 3, -1, w)
    runes(mb, 0.55, 0.14, z + 0.6, z + 1.25, "glow_gold", 3, 1, w)
    mb.cylinder((0, 0.6, z + 2.6), (0, 0.6, 4.6), 0.04, 0.04, "iron", segments=5)
    mb.box((0, 0.6, z + 2.6), (0.8, 0.1, 0.1), "iron", w)
    mb.box((1.7, -1.1, 0.5), (1.6, 0.8, 0.08), "plank")                          # An arm on the bench, the other on the floor.
    for sx in (-0.7, 0.7):
        mb.box((1.7 + sx, -1.1, 0.25), (0.1, 0.7, 0.5), "plank_dark")
    mb.box((1.4, -1.1, 0.72), (0.9, 0.4, 0.36), "stone")
    mb.box((2.1, -1.1, 0.74), (0.5, 0.5, 0.42), "stone_light")
    mb.box((-1.5, -1.2, 0.3), (0.42, 1.0, 0.38), "stone", rotation_z=0.5)
    mb.box((-1.15, -0.7, 0.32), (0.5, 0.5, 0.42), "stone_light", rotation_z=0.5)
    for _ in range(6):
        rock(mb, rnd.uniform(-2.2, -1.2), rnd.uniform(1.0, 1.7), 0.25, rnd.uniform(0.2, 0.35), rnd)
    mb.box((1.5, 1.5, 0.3), (0.5, 0.4, 0.4), "plank")
    cluster(mb, 1.5, 1.5, 0.5, 0.35, rnd, ("glow_gold", "glow_white"), 4)
    beam(mb, (2.3, -0.4, 0.12), (2.3, -0.4, 1.0), 0.025, "pole")
    mb.box((2.3, -0.4, 1.0), (0.26, 0.12, 0.14), "iron")
    pose = lambda t: ({}, {"torso": (0, 0, 0.35 * (0.5 - 0.5 * math.cos(TAU * t)))})   # noqa: E731
    kit.save(mb, FAMILY, "magic_golem_works", COLORS, mech=kit.Mech([("torso", (0, 0.6, 4.3), (0, 0.6, 1.75), None)]).clip("fit", 6.0, pose))


def scrying_pool():
    mb = kit.begin()
    mb.cylinder((0, 0, 0), (0, 0, 0.14), 2.3, 2.2, "marble_dark", segments=8)
    mb.cylinder((0, 0, 0.14), (0, 0, 0.6), 1.7, 1.7, "marble", segments=8)
    mb.cylinder((0, 0, 0.58), (0, 0, 0.68), 1.8, 1.8, "marble_dark", segments=8)
    mb.cylinder((0, 0, 0.6), (0, 0, 0.7), 1.45, 1.45, "cave", segments=8)
    mb.cylinder((0, 0, 0.6), (0, 0, 0.64), 1.45, 1.45, "glow_blue", segments=8)
    mb.cylinder((0, 0, 0.6), (0, 0, 0.65), 0.8, 0.8, "glow_white", segments=8)
    for k in range(3):                                                           # Three ribs meet over the water.
        a = TAU * k / 3 + math.pi / 2
        pts = [(1.75, 0.6), (1.85, 1.6), (1.5, 2.6), (0.8, 3.3), (0.0, 3.5)]
        for (r0, z0), (r1, z1) in zip(pts, pts[1:]):
            beam(mb, (math.cos(a) * r0, math.sin(a) * r0, z0), (math.cos(a) * r1, math.sin(a) * r1, z1), 0.09, "gold")
    mb.sphere((0, 0, 3.5), 0.16, "gold", segments=6, rings=4)
    w = {"mirror": 1.0}
    for i in range(12):
        a0, a1 = TAU * i / 12, TAU * (i + 1) / 12
        beam(mb, (math.cos(a0) * 0.75, 0, 2.1 + math.sin(a0) * 0.75), (math.cos(a1) * 0.75, 0, 2.1 + math.sin(a1) * 0.75), 0.06, "gold", w)
    mb.cylinder((0, -0.02, 2.1), (0, 0.02, 2.1), 0.72, 0.72, "glow_white", w, segments=12)
    for sx in (-1, 1):
        crystal(mb, sx * 0.75, 0, 2.05, 0.05, 0.3, "glow_blue", w, (sx * 0.8, 0))
    pose = lambda t: ({"mirror": [(kit.Z, 360.0 * t)]}, {"mirror": (0, 0, 0.1 * math.sin(TAU * 2 * t))})   # noqa: E731
    kit.save(mb, FAMILY, "magic_scrying_pool", COLORS, mech=kit.Mech([("mirror", (0, 0, 2.1), (0, 0, 2.9), None)]).clip("scry", 8.0, pose))


def ward(name, kind):
    """A ward set at the edge of what it protects."""
    def build():
        mb = kit.begin()
        w = {"top": 1.0}
        if kind == "pylon":
            mb.cylinder((0, 0, 0), (0, 0, 0.3), 0.6, 0.5, "stone_dark", segments=6)
            mb.cylinder((0, 0, 0.3), (0, 0, 2.4), 0.36, 0.24, "stone", segments=6)
            mb.cylinder((0, 0, 2.4), (0, 0, 2.55), 0.34, 0.34, "stone_light", segments=6)
            rune_band(mb, 0, 0, 1.2, 0.31, 6, "glow_blue")
            rune_band(mb, 0, 0, 1.9, 0.27, 6, "glow_blue")
            for k in range(3):
                a = TAU * k / 3
                beam(mb, (math.cos(a) * 0.25, math.sin(a) * 0.25, 2.55), (math.cos(a) * 0.32, math.sin(a) * 0.32, 3.0), 0.025, "iron")
            shard(mb, 0, 0, 3.05, 0.2, 0.7, "glow_blue", w)
        elif kind == "totem":
            log(mb, (0, 0, 0), (0, 0, 3.2), 0.24)
            for k in range(3):                                                   # Three faces, one over another.
                z = 0.7 + 0.85 * k
                mb.box((0, -0.2, z), (0.44, 0.12, 0.5), "plank_light" if k % 2 else "plank")
                for sx in (-1, 1):
                    mb.box((sx * 0.11, -0.27, z + 0.1), (0.09, 0.03, 0.07), "glow_green")
                mb.box((0, -0.27, z - 0.12), (0.24, 0.03, 0.06), "cave")
                mb.box((0, -0.3, z), (0.07, 0.08, 0.16), "plank_dark")
            for sx in (-1, 1):
                solid(mb, [(sx * 0.2, 0, 2.6), (sx * 1.1, 0, 2.9), (sx * 1.0, 0, 2.5), (sx * 0.2, 0, 2.3)], (0, 0.06, 0), "feather" if sx > 0 else "plank_light")
                rope(mb, (sx * 0.9, 0.03, 2.6), (sx * 0.9, 0.03, 2.0), 0.008)
                mb.sphere((sx * 0.9, 0.03, 1.95), 0.07, "bone", segments=5, rings=3)
            for k in range(5):
                a = TAU * k / 5
                rock(mb, math.cos(a) * 0.5, math.sin(a) * 0.5, 0.05, 0.16, random.Random(k), "stone")
            shard(mb, 0, 0, 3.6, 0.13, 0.45, "glow_green", w)
        else:   # A brazier that burns without wood.
            for k in range(3):
                a = TAU * k / 3 + 0.5
                beam(mb, (math.cos(a) * 0.6, math.sin(a) * 0.6, 0), (math.cos(a) * 0.2, math.sin(a) * 0.2, 1.5), 0.035, "iron")
            mb.cylinder((0, 0, 1.45), (0, 0, 1.75), 0.2, 0.46, "iron", segments=8)
            mb.cylinder((0, 0, 1.72), (0, 0, 1.78), 0.42, 0.42, "ember", segments=8)
            for k in range(4):
                a = TAU * k / 4
                mb.cylinder((math.cos(a) * 0.2, math.sin(a) * 0.2, 1.76), (math.cos(a) * 0.12, math.sin(a) * 0.12, 2.25 + 0.15 * (k % 2)), 0.14, 0.0, "glow_violet", w, segments=5)
            mb.cylinder((0, 0, 1.76), (0, 0, 2.7), 0.16, 0.0, "glow_white", w, segments=5)
        pose = lambda t: ({"top": [(kit.Z, 360.0 * t if kind != "brazier" else 16.0 * math.sin(TAU * 3 * t))]}, {"top": (0, 0, 0.08 * math.sin(TAU * 2 * t))})   # noqa: E731
        top = 3.05 if kind == "pylon" else 3.6 if kind == "totem" else 1.76
        kit.save(mb, FAMILY, name, COLORS, mech=kit.Mech([("top", (0, 0, top), (0, 0, top + 0.5), None)]).clip("guard", 4.0, pose))
    return build


def enchant_altar():
    mb = kit.begin()
    mb.cylinder((0, 0, 0), (0, 0, 0.14), 2.0, 1.9, "stone_dark", segments=8)
    mb.cylinder((0, 0, 0.14), (0, 0, 0.26), 1.5, 1.45, "stone", segments=8)
    mb.box((0, 0, 0.6), (1.5, 0.8, 0.7), "stone")
    mb.box((0, 0, 1.0), (1.8, 1.0, 0.14), "stone_light")
    runes(mb, -0.45, -0.41, 0.4, 0.85, "glow_violet", 2)
    runes(mb, 0.0, -0.41, 0.4, 0.85, "glow_violet", 3)
    runes(mb, 0.45, -0.41, 0.4, 0.85, "glow_violet", 4)
    mb.box((0, 0, 1.08), (1.2, 0.5, 0.02), "cloth_violet")
    mb.box((0.1, 0, 1.11), (1.1, 0.07, 0.025), "steel")                          # The blade being worked on.
    mb.box((-0.5, 0, 1.11), (0.05, 0.26, 0.04), "gold")
    mb.box((-0.65, 0, 1.11), (0.26, 0.05, 0.04), "leather")
    for k in range(4):
        mb.box((-0.2 + 0.22 * k, 0, 1.126), (0.08, 0.03, 0.006), "glow_violet")
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * 1.25, sy * 0.95
            mb.cylinder((x, y, 0.26), (x, y, 1.3), 0.05, 0.035, "iron", segments=5)
            mb.cylinder((x, y, 1.3), (x, y, 1.34), 0.1, 0.1, "iron", segments=6)
            candle(mb, x, y, 1.34, 0.22)
    w = {"book": 1.0}
    for sx in (-1, 1):                                                           # An open book hangs in the air.
        solid(mb, [(0, 0.25, 1.95), (sx * 0.36, 0.25, 2.07), (sx * 0.36, -0.2, 2.07), (0, -0.2, 1.95)], (0, 0, 0.05), "cloth_red", w)
        solid(mb, [(0, 0.22, 2.0), (sx * 0.32, 0.22, 2.11), (sx * 0.32, -0.17, 2.11), (0, -0.17, 2.0)], (0, 0, 0.03), "parchment", w)
    for k in range(3):
        shard(mb, math.cos(TAU * k / 3) * 0.6, math.sin(TAU * k / 3) * 0.6, 2.2, 0.05, 0.22, "glow_violet", w)
    pose = lambda t: ({"book": [(kit.Z, 360.0 * t)]}, {"book": (0, 0, 0.1 * math.sin(TAU * 2 * t))})   # noqa: E731
    kit.save(mb, FAMILY, "magic_enchant_altar", COLORS, mech=kit.Mech([("book", (0, 0, 2.0), (0, 0, 2.5), None)]).clip("float", 10.0, pose))


def storm_rod():
    """A mast that draws the lightning away from the roofs, and keeps it."""
    mb = kit.begin()
    mb.cylinder((0, 0, 0), (0, 0, 0.5), 1.4, 1.2, "stone_dark", segments=8)
    mb.cylinder((0, 0, 0.5), (0, 0, 1.6), 0.8, 0.6, "stone", segments=8)
    mb.cylinder((0, 0, 1.6), (0, 0, 1.75), 0.7, 0.7, "stone_light", segments=8)
    mb.cylinder((0, 0, 1.75), (0, 0, 9.0), 0.12, 0.05, "copper", segments=6)
    for k in range(5):
        z = 3.0 + 1.2 * k
        r = 0.6 - 0.08 * k
        for i in range(8):
            a0, a1 = TAU * i / 8, TAU * (i + 1) / 8
            beam(mb, (math.cos(a0) * r, math.sin(a0) * r, z), (math.cos(a1) * r, math.sin(a1) * r, z), 0.03, "copper")
        for i in range(2):
            a = TAU * i / 2 + k
            beam(mb, (0, 0, z), (math.cos(a) * r, math.sin(a) * r, z), 0.02, "copper")
            beam(mb, (0, 0, z), (-math.cos(a) * r, -math.sin(a) * r, z), 0.02, "copper")
    mb.sphere((0, 0, 9.1), 0.22, "copper", segments=7, rings=5)
    mb.cylinder((0, 0, 9.3), (0, 0, 10.0), 0.03, 0.0, "steel", segments=5)
    for k in range(4):                                                           # Chains to the ground and the jars it fills.
        a = TAU * k / 4 + TAU / 8
        rope(mb, (0, 0, 6.5), (math.cos(a) * 2.6, math.sin(a) * 2.6, 0.0), 0.012)
        mb.cylinder((math.cos(a) * 2.6, math.sin(a) * 2.6, 0), (math.cos(a) * 2.6, math.sin(a) * 2.6, 0.3), 0.05, 0.04, "iron", segments=5)
        b = TAU * k / 4
        x, y = math.cos(b) * 1.0, math.sin(b) * 1.0
        mb.cylinder((x, y, 0.5), (x, y, 1.0), 0.16, 0.18, "glow_blue", segments=8)
        mb.cylinder((x, y, 1.0), (x, y, 1.08), 0.19, 0.19, "copper", segments=8)
        mb.cylinder((x, y, 1.08), (x, y, 1.3), 0.02, 0.02, "copper", segments=4)
        mb.sphere((x, y, 1.33), 0.05, "copper", segments=5, rings=3)
    w = {"spark": 1.0}
    for k in range(3):
        a = TAU * k / 3
        z = 4.0 + 1.6 * k
        r = 0.55 - 0.1 * k
        p = (math.cos(a) * r, math.sin(a) * r, z)
        q = (math.cos(a + 0.5) * (r + 0.25), math.sin(a + 0.5) * (r + 0.25), z + 0.3)
        s = (math.cos(a + 0.2) * (r + 0.4), math.sin(a + 0.2) * (r + 0.4), z + 0.65)
        beam(mb, p, q, 0.025, "glow_white", w)
        beam(mb, q, s, 0.02, "glow_blue", w)
    pose = lambda t: ({"spark": [(kit.Z, 360.0 * 3 * t)]}, {"spark": (0, 0, 0.5 * math.sin(TAU * 2 * t))})   # noqa: E731
    kit.save(mb, FAMILY, "magic_storm_rod", COLORS, mech=kit.Mech([("spark", (0, 0, 4.0), (0, 0, 5.0), None)]).clip("charge", 3.0, pose))


def lamp(name, style):
    """A street lamp that needs no oil: a crystal hangs over its cradle."""
    def build():
        mb = kit.begin()
        st = STYLES[style]
        w = {"light": 1.0}
        if style == "elf":
            pts = [(0, 0.0), (0.05, 1.2), (-0.1, 2.3), (-0.45, 3.0), (-0.9, 3.2)]
            for (x0, z0), (x1, z1) in zip(pts, pts[1:]):
                mb.cylinder((x0, 0, z0), (x1, 0, z1), 0.09 - 0.012 * z0, 0.08 - 0.012 * z0, "pole", segments=6)
            for k in range(3):
                mb.sphere((-0.3 - 0.25 * k, 0.05 * (k - 1), 3.1 + 0.1 * (k % 2)), 0.16, "leaf_light" if k % 2 else "leaf", segments=5, rings=3)
            rope(mb, (-0.9, 0, 3.2), (-0.9, 0, 2.9), 0.008)
            shard(mb, -0.9, 0, 2.65, 0.13, 0.5, st["glow"], w)
            head = (-0.9, 0, 2.65)
        else:
            mb.cylinder((0, 0, 0), (0, 0, 0.35), 0.24, 0.16, st["dark"], segments=6)
            mb.cylinder((0, 0, 0.35), (0, 0, 2.7), 0.08, 0.06, st["metal"] if style != "dwarf" else st["wall"], segments=6)
            mb.cylinder((0, 0, 2.7), (0, 0, 2.8), 0.2, 0.2, st["metal"], segments=6)
            for k in range(4):
                a = TAU * k / 4 + TAU / 8
                beam(mb, (math.cos(a) * 0.17, math.sin(a) * 0.17, 2.8), (math.cos(a) * 0.3, math.sin(a) * 0.3, 3.15), 0.02, st["metal"])
                beam(mb, (math.cos(a) * 0.3, math.sin(a) * 0.3, 3.15), (math.cos(a) * 0.2, math.sin(a) * 0.2, 3.5), 0.02, st["metal"])
            if style == "dwarf":
                rune_band(mb, 0, 0, 1.4, 0.08, 4, st["glow"], None, (0.02, 0.06, 0.3))
            shard(mb, 0, 0, 3.2, 0.14, 0.55, st["glow"], w)
            head = (0, 0, 3.2)
        pose = lambda t: ({"light": [(kit.Z, 360.0 * t)]}, {"light": (0, 0, 0.05 * math.sin(TAU * 2 * t))})   # noqa: E731
        kit.save(mb, FAMILY, name, COLORS, mech=kit.Mech([("light", head, (head[0], head[1], head[2] + 0.4), None)]).clip("float", 6.0, pose))
    return build


def floating_island():
    """A piece of ground that came loose, moored with chains so it stays."""
    mb = kit.begin()
    rnd = random.Random(31)
    mb.sphere((0, 0, 0.0), 3.0, "soil", segments=10, rings=4, scale=(1.0, 0.9, 0.12))            # The hollow it left.
    for k in range(9):
        a = TAU * k / 9
        rock(mb, math.cos(a) * rnd.uniform(2.2, 3.0), math.sin(a) * rnd.uniform(2.0, 2.7), 0.1, rnd.uniform(0.25, 0.5), rnd)
    w = {"island": 1.0}
    base = 4.2
    mb.cylinder((0, 0, base), (0, 0, base + 0.5), 2.6, 3.0, "soil", w, segments=10)
    mb.cylinder((0, 0, base + 0.5), (0, 0, base + 0.75), 3.0, 2.9, "grass", w, segments=10)
    mb.cylinder((0.2, 0.1, base - 1.3), (0, 0, base), 1.4, 2.6, "stone_dark", w, segments=9)
    mb.cylinder((0.4, 0.2, base - 2.6), (0.2, 0.1, base - 1.3), 0.5, 1.4, "stone", w, segments=8)
    mb.cylinder((0.5, 0.2, base - 3.3), (0.4, 0.2, base - 2.6), 0.0, 0.5, "stone_dark", w, segments=7)
    for k in range(6):
        a = TAU * k / 6 + 0.4
        crystal(mb, math.cos(a) * 1.2, math.sin(a) * 1.1, base - 1.2, 0.12, -0.7, "glow_blue", w, (math.cos(a) * 0.4, math.sin(a) * 0.4))
    mb.cylinder((-1.0, 0.6, base + 0.75), (-0.9, 0.6, base + 2.6), 0.2, 0.13, "bark", w, segments=7)        # A tree that went up with it.
    for k, (dx, dy, dz, r) in enumerate(((0, 0, 3.2, 1.0), (0.6, 0.3, 2.8, 0.7), (-0.6, -0.2, 2.9, 0.75), (0.1, -0.5, 3.7, 0.6))):
        mb.sphere((-0.9 + dx, 0.6 + dy, base + dz), r, "leaf_light" if k % 2 else "leaf", w, segments=7, rings=5)
    mb.box((1.3, -0.4, base + 0.95), (0.9, 0.7, 0.4), "marble", w)                # A small shrine nobody remembers building.
    for sx in (-0.3, 0.3):
        mb.cylinder((1.3 + sx, -0.65, base + 1.15), (1.3 + sx, -0.65, base + 2.0), 0.07, 0.06, "marble", w, segments=6)
    solid(mb, [(0.8, -0.8, base + 2.0), (1.8, -0.8, base + 2.0), (1.3, -0.8, base + 2.4)], (0, 0.9, 0), "marble_dark", w)
    shard(mb, 1.3, -0.4, base + 1.55, 0.1, 0.36, "glow_blue", w)
    for _ in range(5):
        rock(mb, rnd.uniform(-2.2, 2.2), rnd.uniform(-2.0, 2.0), base + 0.8, rnd.uniform(0.15, 0.3), rnd, None, w)
    wf = {"fall": 1.0}
    mb.box((2.3, 1.2, base + 0.72), (0.9, 0.4, 0.05), "water", w)
    mb.box((2.85, 1.2, base - 1.7), (0.1, 0.34, 4.9), "glow_white", wf)          # Its spring still runs and falls off the edge.
    mb.cylinder((2.85, 1.2, 0), (2.85, 1.2, 0.12), 0.7, 0.7, "water")
    for k in range(4):                                                           # The moorings.
        a = TAU * k / 4 + TAU / 8
        gx, gy = math.cos(a) * 4.4, math.sin(a) * 4.0
        mb.cylinder((gx, gy, 0), (gx, gy, 0.5), 0.3, 0.2, "stone", segments=6)
        mb.cylinder((gx - 0.12, gy, 0.5), (gx + 0.12, gy, 0.5), 0.1, 0.1, "iron", segments=6)
        n = 9
        for i in range(n):
            u0, u1 = i / n, (i + 1) / n
            p0 = (gx + (math.cos(a) * 2.5 - gx) * u0, gy + (math.sin(a) * 2.3 - gy) * u0, 0.5 + (base + 0.1 - 0.5) * u0 - 0.5 * math.sin(math.pi * u0))
            p1 = (gx + (math.cos(a) * 2.5 - gx) * u1, gy + (math.sin(a) * 2.3 - gy) * u1, 0.5 + (base + 0.1 - 0.5) * u1 - 0.5 * math.sin(math.pi * u1))
            beam(mb, p0, p1, 0.035 if i % 2 else 0.05, "iron")
    pose = lambda t: ({}, {"island": (0, 0, 0.12 * math.sin(TAU * t)), "fall": (0, 0, 0.12 * math.sin(TAU * t) + 0.04 * math.sin(TAU * 6 * t))})   # noqa: E731
    mech = kit.Mech([("island", (0, 0, base), (0, 0, base + 1.0), None), ("fall", (2.85, 1.2, base), (2.85, 1.2, 0.0), None)]).clip("drift", 8.0, pose)
    kit.save(mb, FAMILY, "magic_floating_island", COLORS, mech=mech)


def herb_dome():
    """A dome of ribs where herbs that need warmth and light are grown."""
    mb = kit.begin()
    rnd = random.Random(17)
    mb.cylinder((0, 0, 0), (0, 0, 0.7), 2.7, 2.6, "stone", segments=12)
    mb.cylinder((0, 0, 0.68), (0, 0, 0.8), 2.75, 2.75, "stone_light", segments=12)
    mb.cylinder((0, 0, 0.6), (0, 0, 0.74), 2.35, 2.35, "soil", segments=12)
    mb.box((0, -2.65, 0.5), (1.0, 0.3, 1.0), "stone_dark")
    mb.box((0, -2.8, 0.45), (0.7, 0.06, 0.9), "plank_dark")
    for k in range(12):
        a = TAU * k / 12
        prev = None
        for i in range(7):
            b = (math.pi / 2) * i / 6
            p = (math.cos(a) * math.cos(b) * 2.6, math.sin(a) * math.cos(b) * 2.6, 0.8 + math.sin(b) * 2.6)
            if prev:
                beam(mb, prev, p, 0.035, "gold" if k % 3 == 0 else "bronze")
            prev = p
    for i in (2, 4):
        b = (math.pi / 2) * i / 6
        for k in range(12):
            a0, a1 = TAU * k / 12, TAU * (k + 1) / 12
            beam(mb, (math.cos(a0) * math.cos(b) * 2.6, math.sin(a0) * math.cos(b) * 2.6, 0.8 + math.sin(b) * 2.6),
                 (math.cos(a1) * math.cos(b) * 2.6, math.sin(a1) * math.cos(b) * 2.6, 0.8 + math.sin(b) * 2.6), 0.025, "bronze")
    w = {"sun": 1.0}
    mb.sphere((0, 0, 3.0), 0.3, "glow_gold", w, segments=8, rings=6)             # A small sun hangs under the top.
    for k in range(6):
        a = TAU * k / 6
        mb.cylinder((math.cos(a) * 0.35, math.sin(a) * 0.35, 3.0), (math.cos(a) * 0.6, math.sin(a) * 0.6, 3.0), 0.05, 0.0, "glow_gold", w, segments=4)
    for _ in range(16):
        r, a = rnd.uniform(0.3, 2.1), rnd.uniform(0, TAU)
        x, y = math.cos(a) * r, math.sin(a) * r
        kind = rnd.randrange(3)
        if kind == 0:
            mb.cylinder((x, y, 0.74), (x, y, 1.3), 0.03, 0.02, "leaf", segments=4)
            mb.sphere((x, y, 1.35), 0.11, rnd.choice(("glow_violet", "glow_blue", "glow_green")), segments=5, rings=3)
        elif kind == 1:
            mb.cylinder((x, y, 0.74), (x, y, 1.2), 0.22, 0.02, "leaf_light", segments=5)
        else:
            mb.sphere((x, y, 0.85), 0.22, "leaf", segments=5, rings=3)
            mb.sphere((x + 0.08, y, 1.0), 0.07, "glow_gold", segments=4, rings=3)
    pose = lambda t: ({"sun": [(kit.Z, 360.0 * t)]}, {"sun": (0, 0, 0.06 * math.sin(TAU * 2 * t))})   # noqa: E731
    kit.save(mb, FAMILY, "magic_herb_dome", COLORS, mech=kit.Mech([("sun", (0, 0, 3.0), (0, 0, 3.4), None)]).clip("shine", 8.0, pose))


def waygate(name, style):
    """An arch you walk through here and come out of far away."""
    def build():
        mb = kit.begin()
        st = STYLES[style]
        mb.box((0, 0, 0.1), (5.2, 2.6, 0.2), st["dark"])
        mb.box((0, -1.5, 0.05), (3.0, 0.5, 0.1), st["dark"])
        mb.box((0, 0, 0.28), (4.6, 2.0, 0.16), st["wall"])
        for sx in (-1, 1):
            mb.box((sx * 1.8, 0, 1.56), (0.8, 0.9, 2.4), st["wall"])
            mb.box((sx * 1.8, 0, 0.5), (1.0, 1.1, 0.3), st["dark"])
            mb.box((sx * 1.8, 0, 2.82), (1.0, 1.1, 0.16), st["light"])
            runes(mb, sx * 1.8, -0.46, 0.9, 2.6, st["glow"], 4, sx)
            runes(mb, sx * 1.8, 0.46, 0.9, 2.6, st["glow"], 4, -sx)
        stone_arch(mb, 0, -0.45, 0.45, 2.9, 1.4, 2.2, (st["wall"], st["light"]), 9)
        stone_arch(mb, 0, -0.5, 0.5, 2.9, 2.2, 2.36, (st["dark"],), 9)
        mb.box((0, 0, 5.3), (0.5, 1.0, 0.5), st["light"])                        # The keystone and what crowns it.
        crystal(mb, 0, 0, 5.5, 0.16, 0.7, st["glow"])
        if style == "elf":
            for k in range(8):
                a = math.pi * (k + 0.5) / 8
                mb.sphere((math.cos(a) * 2.35, rnd_y(k), 2.9 + math.sin(a) * 2.35), 0.2, "leaf_light" if k % 2 else "leaf", segments=5, rings=3)
        if style == "dwarf":
            for sx in (-1, 1):
                mb.box((sx * 1.8, -0.5, 1.5), (0.5, 0.12, 1.6), st["dark"])
                mb.box((sx * 1.8, -0.57, 2.0), (0.3, 0.04, 0.3), st["metal"])
        wm = {"veil": 1.0}
        mb.box((0, 0, 1.63), (2.8, 0.04, 2.54), st["glow"], wm)                   # The veil between the posts.
        n = 9
        for i in range(n):
            a0, a1 = math.pi * i / n, math.pi * (i + 1) / n
            solid(mb, [(0, -0.02, 2.9), (math.cos(a0) * 1.4, -0.02, 2.9 + math.sin(a0) * 1.4), (math.cos(a1) * 1.4, -0.02, 2.9 + math.sin(a1) * 1.4)], (0, 0.04, 0), st["glow"], wm)
        w = {"motes": 1.0}
        for k in range(6):
            a = TAU * k / 6
            shard(mb, math.cos(a) * 1.0, -0.2 if k % 2 else 0.2, 2.4 + math.sin(a) * 1.0, 0.05, 0.2, "glow_white", w)
        pose = lambda t: ({"motes": [(kit.Y, 360.0 * t)]}, {"veil": (0, 0.02 * math.sin(TAU * 4 * t), 0)})   # noqa: E731
        mech = kit.Mech([("motes", (0, 0, 2.4), (0, 0, 3.0), None), ("veil", (0, 0, 1.6), (0, 0, 2.6), None)]).clip("open", 8.0, pose)
        kit.save(mb, FAMILY, name, COLORS, mech=mech)
    return build


def rnd_y(k):
    return (-0.3, 0.2, -0.1, 0.35, -0.35, 0.1, 0.3, -0.2)[k % 8]


def rune_forge():
    """Where the dwarves hammer runes into what they forge."""
    mb = kit.begin()
    mb.box((0, 0, 0.08), (5.0, 4.0, 0.16), "dwarf_dark")
    mb.box((0, 1.3, 1.0), (2.4, 1.2, 1.8), "dwarf_stone")                        # The hearth, fed by a channel of molten stone.
    mb.box((0, 1.3, 1.95), (2.6, 1.4, 0.14), "stone")
    mb.box((0, 0.68, 0.9), (1.3, 0.06, 0.9), "cave")
    mb.box((0, 0.67, 0.65), (1.1, 0.06, 0.4), "ember")
    mb.box((0, 0.66, 0.55), (0.7, 0.06, 0.2), "flame")
    mb.box((0, 1.3, 2.9), (0.8, 0.8, 1.8), "dwarf_stone")
    mb.box((0, 1.3, 3.85), (1.0, 1.0, 0.14), "stone")
    runes(mb, -0.85, 0.69, 0.5, 1.7, "glow_gold", 4)
    runes(mb, 0.85, 0.69, 0.5, 1.7, "glow_gold", 4, 1)
    mb.box((1.9, 0.4, 0.17), (0.3, 3.0, 0.04), "cave")
    mb.box((1.9, 0.4, 0.18), (0.2, 2.9, 0.04), "ember")
    mb.box((1.9, -0.6, 0.19), (0.12, 0.8, 0.04), "flame")
    mb.box((1.55, 1.3, 0.3), (0.5, 0.3, 0.3), "ember")
    mb.box((0, -0.7, 0.45), (0.9, 0.7, 0.6), "dwarf_stone")                      # The anvil on its block.
    rune_band(mb, 0, -0.7, 0.45, 0.48, 8, "glow_gold", None, (0.03, 0.08, 0.2))
    mb.box((0, -0.7, 0.85), (0.5, 0.36, 0.22), "iron")
    mb.box((0, -0.7, 1.02), (0.9, 0.4, 0.14), "iron")
    mb.cylinder((0.45, -0.7, 1.02), (0.8, -0.7, 1.04), 0.09, 0.0, "iron", segments=6)
    mb.box((-0.05, -0.7, 1.11), (0.5, 0.08, 0.03), "ember")                      # The blade, still glowing.
    for k in range(3):
        mb.box((-0.2 + 0.15 * k, -0.7, 1.128), (0.06, 0.03, 0.006), "glow_gold")
    w = {"hammer": 1.0}
    beam(mb, (-1.2, -0.7, 1.9), (-0.2, -0.7, 1.9), 0.03, "pole", w)
    mb.box((-0.15, -0.7, 1.9), (0.22, 0.26, 0.36), "bronze", w)
    mb.box((-0.15, -0.84, 1.9), (0.12, 0.02, 0.2), "glow_gold", w)
    mb.cylinder((-1.4, -0.7, 0.16), (-1.4, -0.7, 1.9), 0.09, 0.07, "dwarf_stone", segments=6)   # The post it hangs from, held by no hand.
    mb.sphere((-1.4, -0.7, 1.9), 0.14, "glow_gold", segments=6, rings=4)
    mb.cylinder((-1.9, 0.9, 0.16), (-1.9, 0.9, 0.9), 0.36, 0.4, "plank_dark", segments=10)       # The quench tub and tools.
    mb.cylinder((-1.9, 0.9, 0.86), (-1.9, 0.9, 0.9), 0.33, 0.33, "water", segments=10)
    for k in range(3):
        beam(mb, (-1.3 + 0.12 * k, 0.6, 0.16), (-1.25 + 0.12 * k, 0.72, 1.2), 0.02, "iron")
    for k in range(4):
        mb.box((1.2 + 0.0 * k, -1.5 + 0.0 * k, 0.22 + 0.11 * k), (0.6 - 0.05 * k, 0.24, 0.1), "iron" if k % 2 else "bronze")

    def strike(t):
        lift = phase(t, 0.0, 0.6) - phase(t, 0.6, 0.72)   # Up slowly, down in a blink.
        return {"hammer": [(kit.Y, -52.0 * lift)]}, {}

    kit.save(mb, FAMILY, "magic_rune_forge", COLORS, mech=kit.Mech([("hammer", (-1.4, -0.7, 1.9), (-0.4, -0.7, 1.9), None)]).clip("strike", 1.6, strike))


def phase(t, a, b):
    return kit.smooth(min(1.0, max(0.0, (t - a) / (b - a))))


MODELS = {
    "magic_mana_well": mana_well,
    "magic_circle_teleport": circle("magic_circle_teleport", "teleport"),
    "magic_circle_summon": circle("magic_circle_summon", "summon"),
    "magic_crystal_bed_1": crystal_bed("magic_crystal_bed_1", 1),
    "magic_crystal_bed_2": crystal_bed("magic_crystal_bed_2", 2),
    "magic_crystal_bed_3": crystal_bed("magic_crystal_bed_3", 3),
    "magic_alchemy_yard": alchemy,
    "magic_golem_works": golem_works,
    "magic_scrying_pool": scrying_pool,
    "magic_ward_pylon": ward("magic_ward_pylon", "pylon"),
    "magic_ward_totem": ward("magic_ward_totem", "totem"),
    "magic_ward_brazier": ward("magic_ward_brazier", "brazier"),
    "magic_enchant_altar": enchant_altar,
    "magic_storm_rod": storm_rod,
    "magic_floating_island": floating_island,
    "magic_herb_dome": herb_dome,
    "magic_rune_forge": rune_forge,
}
for _style in STYLES:
    MODELS["magic_ley_stone_" + _style] = ley_stone("magic_ley_stone_" + _style, _style)
    MODELS["magic_waygate_" + _style] = waygate("magic_waygate_" + _style, _style)
    MODELS["magic_lamp_" + _style] = lamp("magic_lamp_" + _style, _style)

kit.run(MODELS, FAMILY)
