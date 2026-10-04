"""Road proposals: signs, warnings, lamps, obstacles, toll gate, paving,
steps and the small things a traveler meets on the way. See ../LEEME.md.

    blender --background --factory-startup --python art/blender/proposals/roads/build.py -- [ids]

A road runs along Y: what stands beside it is centered on the origin, and
what crosses it (an arch, a barrier, a fallen tree) spans X.
"""

import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import _kit as kit  # noqa: E402
import _shapes  # noqa: E402
import common  # noqa: E402
from _shapes import TAU, beam, log, mark, moved, rock, rope, solid  # noqa: E402

FAMILY = "roads"
C = common.rgb
COLORS = {
    **_shapes.COLORS,
    "ink": C(0x3A2A1C), "paint_white": C(0xECE6D6), "paint_red": C(0xB8362E), "paint_yellow": C(0xE8B830),
    "paint_blue": C(0x2F4E8C), "paint_black": C(0x22201E),
    "thatch": C(0xC9A55A), "thatch_dark": C(0xA8863F), "roof": C(0x9A4A2E), "roof_dark": C(0x7E3A24),
    "leaf": C(0x4E7A34), "leaf_dark": C(0x3A5E28), "bark_dead": C(0x8A8278), "moss": C(0x6A8A3A),
    "soil": C(0x6A4A30), "soil_dark": C(0x553A26), "gravel": C(0xA8A090), "cobble": C(0x8E8A84),
    "cobble_dark": C(0x6E6A64), "cobble_light": C(0xAAA59C), "flag": C(0xB0A694), "flag_dark": C(0x978E7E),
    "water": C(0x4A7FA0), "bell": C(0xB8923A), "bone": C(0xE4DCC8), "cloth_red": C(0xA83A34),
    "glow_rune": C(0x40D8FF), "glow_crystal": C(0x8AE8FF), "flame": C(0xF08A24), "flame_core": C(0xFFF0B0),
    "sawdust": C(0xD8B880), "feather": C(0x3A5E8C),
}


def stone_base(mb, x, y, r=0.3, seed=1, n=5):
    rnd = random.Random(seed)
    for i in range(n):
        a = TAU * i / n + rnd.uniform(-0.2, 0.2)
        rock(mb, x + math.cos(a) * r, y + math.sin(a) * r, 0.08, rnd.uniform(0.14, 0.2), rnd)


def hanging_lantern(mb, hook, bone, size=1.0):
    """A lantern hanging from `hook`, weighted to `bone` (which pivots there)."""
    x, y, z = hook
    w = {bone: 1.0}
    s = size
    mb.cylinder((x, y, z), (x, y, z - 0.18 * s), 0.012, 0.012, "iron", w, segments=4)
    mb.cylinder((x, y, z - 0.18 * s), (x, y, z - 0.26 * s), 0.02, 0.11 * s, "iron", w, segments=6)
    mb.box((x, y, z - 0.42 * s), (0.17 * s, 0.17 * s, 0.3 * s), "window", w)
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.box((x + sx * 0.09 * s, y + sy * 0.09 * s, z - 0.42 * s), (0.025, 0.025, 0.32 * s), "iron", w)
    mb.box((x, y, z - 0.59 * s), (0.22 * s, 0.22 * s, 0.04), "iron", w)
    return (bone, hook, (x, y, z - 0.5 * s), None)


def swing(bone, ax=6.0, ay=4.0, phase=0.0):
    return lambda t: ({bone: [(kit.X, ax * math.sin(TAU * t + phase)), (kit.Y, ay * math.sin(TAU * 2 * t + phase))]}, {})


def merged(*poses):
    def pose(t):
        turns, moves = {}, {}
        for p in poses:
            a, b = p(t)
            turns.update(a)
            moves.update(b)
        return turns, moves
    return pose


def board(mb, z, length=0.9, rot=0.0, lines=2, at=(0.0, 0.0), mat="plank_light", tip=True):
    """A pointing board starting at the post, turned `rot` degrees around Z."""
    start = mark(mb)
    h = 0.11
    ring = [(0.06, 0, z - h), (length - 0.14, 0, z - h)]
    ring += [(length, 0, z)] if tip else [(length, 0, z - h), (length, 0, z + h)]
    ring += [(length - 0.14, 0, z + h), (0.06, 0, z + h)]
    solid(mb, [(px, -0.02, pz) for px, _py, pz in ring], (0, 0.04, 0), mat)
    for k in range(lines):
        zz = z + 0.035 - 0.07 * k if lines > 1 else z
        for side in (-0.026, 0.026):
            mb.box((0.14 + (length - 0.4) / 2, side, zz), (length - 0.4 - 0.1 * k, 0.012, 0.022), "ink")
    moved(mb, start, at, rot)


def wolf_head(mb, cx, y, cz, s, mat, depth=0.03):
    def pts(points):
        return [(cx + px * s, y, cz + pz * s) for px, pz in points]
    solid(mb, pts([(-0.27, 0.16), (-0.18, -0.08), (0, -0.32), (0.18, -0.08), (0.27, 0.16), (0.11, 0.27), (-0.11, 0.27)]),
          (0, -depth, 0), mat)
    for sx in (-1, 1):
        solid(mb, pts([(sx * 0.27, 0.16), (sx * 0.11, 0.27), (sx * 0.25, 0.46)]), (0, -depth, 0), mat)


def skull(mb, x, y, z, s=1.0, weights=None):
    mb.sphere((x, y, z), 0.13 * s, "bone", weights, segments=6, rings=5, scale=(1.0, 1.1, 1.0))
    mb.box((x, y - 0.07 * s, z - 0.12 * s), (0.13 * s, 0.1 * s, 0.09 * s), "bone", weights)
    for sx in (-1, 1):
        mb.box((x + sx * 0.05 * s, y - 0.125 * s, z + 0.0), (0.045 * s, 0.03 * s, 0.05 * s), "paint_black", weights)
    mb.box((x, y - 0.135 * s, z - 0.06 * s), (0.025 * s, 0.02 * s, 0.035 * s), "paint_black", weights)


# --- Signs --------------------------------------------------------------------------------------


def signpost(name, arms):
    def build():
        mb = kit.begin()
        stone_base(mb, 0, 0)
        mb.cylinder((0, 0, 0), (0, 0, 2.9), 0.075, 0.06, "pole", segments=7)
        for i, (rot, length) in enumerate(arms):
            board(mb, 2.55 - 0.3 * i, length, rot, 2 - i % 2)
        for sx in (-1, 1):   # A little roof keeps the rain off the boards.
            solid(mb, [(0, -0.22, 3.05), (0, 0.22, 3.05), (sx * 0.32, 0.22, 2.86), (sx * 0.32, -0.22, 2.86)], (0, 0, 0.035), "roof")
        kit.save(mb, FAMILY, name, COLORS)
    return build


def warning(name, kind):
    def build():
        mb = kit.begin()
        stone_base(mb, 0, 0, seed=4)
        mb.cylinder((0, 0, 0), (0, 0, 2.5), 0.07, 0.06, "pole_dark", segments=7)
        y = -0.08
        if kind == "rockfall":
            solid(mb, [(-0.52, y, 1.55), (0.52, y, 1.55), (0, y, 2.45)], (0, 0.04, 0), "paint_red")
            solid(mb, [(-0.38, y - 0.01, 1.63), (0.38, y - 0.01, 1.63), (0, y - 0.01, 2.3)], (0, 0.03, 0), "paint_white")
            for px, pz, r in ((-0.12, 1.75, 0.1), (0.1, 1.72, 0.08), (0.0, 1.95, 0.07), (0.16, 1.9, 0.05)):
                solid(mb, [(px - r, y - 0.02, pz - r * 0.6), (px + r, y - 0.02, pz - r * 0.7), (px + r * 0.7, y - 0.02, pz + r * 0.8),
                           (px - r * 0.6, y - 0.02, pz + r)], (0, 0.02, 0), "paint_black")
        else:
            border = {"wolf": "paint_yellow", "skull": "paint_red", "flood": "paint_blue"}[kind]
            solid(mb, [(0, y, 1.45), (0.55, y, 2.0), (0, y, 2.55), (-0.55, y, 2.0)], (0, 0.04, 0), border)
            solid(mb, [(0, y - 0.01, 1.57), (0.43, y - 0.01, 2.0), (0, y - 0.01, 2.43), (-0.43, y - 0.01, 2.0)], (0, 0.03, 0),
                  "paint_white")
            if kind == "wolf":
                wolf_head(mb, 0, y - 0.01, 1.97, 0.72, "paint_black", 0.02)
                for sx in (-1, 1):
                    solid(mb, [(sx * 0.115, y - 0.035, 2.045), (sx * 0.035, y - 0.035, 2.0), (sx * 0.105, y - 0.035, 1.98)], (0, 0.01, 0),
                          "paint_yellow")
            elif kind == "skull":
                solid(mb, [(-0.17, y - 0.02, 1.98), (0.17, y - 0.02, 1.98), (0.2, y - 0.02, 2.14), (0.1, y - 0.02, 2.27),
                           (-0.1, y - 0.02, 2.27), (-0.2, y - 0.02, 2.14)], (0, 0.02, 0), "paint_black")
                solid(mb, [(-0.1, y - 0.02, 1.84), (0.1, y - 0.02, 1.84), (0.12, y - 0.02, 1.99), (-0.12, y - 0.02, 1.99)],
                      (0, 0.02, 0), "paint_black")
                for sx in (-1, 1):
                    mb.box((sx * 0.08, y - 0.035, 2.1), (0.07, 0.02, 0.07), "paint_white")
                    beam(mb, (sx * 0.22, y - 0.03, 1.72), (-sx * 0.22, y - 0.03, 1.86), 0.02, "paint_black")
            else:
                for k in range(3):
                    z0 = 1.82 + 0.16 * k
                    solid(mb, [(-0.3 + 0.03 * k, y - 0.02, z0), (-0.15, y - 0.02, z0 + 0.07), (0.0, y - 0.02, z0), (0.15, y - 0.02, z0 + 0.07),
                               (0.3 - 0.03 * k, y - 0.02, z0), (0.3 - 0.03 * k, y - 0.02, z0 - 0.05), (-0.3 + 0.03 * k, y - 0.02, z0 - 0.05)],
                          (0, 0.02, 0), "paint_blue")
        mb.box((0, -0.03, 1.25), (0.6, 0.03, 0.16), "plank_light")
        mb.box((0, -0.05, 1.25), (0.44, 0.012, 0.03), "ink")
        kit.save(mb, FAMILY, name, COLORS)
    return build


def warning_totem():
    mb = kit.begin()
    stone_base(mb, 0, 0, 0.35, seed=7, n=6)
    mb.cylinder((0, 0, 0), (0.08, 0, 3.2), 0.1, 0.07, "bark_dead", segments=7)
    beam(mb, (-0.75, 0, 2.3), (0.85, 0.05, 2.45), 0.05, "bark_dead")
    skull(mb, 0.09, -0.06, 3.3, 1.3)
    for sx, zz in ((-0.7, 2.05), (0.8, 2.2)):
        rope(mb, (sx, 0.0, zz + 0.28), (sx, 0, zz + 0.12))
        skull(mb, sx, -0.02, zz, 0.9, {"hang": 1.0} if sx > 0 else {"hang2": 1.0})
    for k, (px, pz) in enumerate(((-0.35, 2.0), (0.3, 2.05), (0.5, 2.0))):   # Red rags and feathers.
        solid(mb, [(px - 0.06, -0.03, pz + 0.3), (px + 0.06, -0.03, pz + 0.3), (px + 0.08, -0.03, pz - 0.25), (px - 0.02, -0.03, pz - 0.4)],
              (0, 0.015, 0), "cloth_red" if k != 1 else "feather", {"rag": 1.0})
    for a in (0.5, 2.2, 4.0):   # Bones at its foot.
        beam(mb, (math.cos(a) * 0.5, math.sin(a) * 0.5, 0.05), (math.cos(a + 0.6) * 0.95, math.sin(a + 0.6) * 0.95, 0.05), 0.035, "bone")
    mech = kit.Mech([("hang", (0.8, 0, 2.48), (0.8, 0, 2.1), None), ("hang2", (-0.7, 0, 2.33), (-0.7, 0, 2.0), None),
                     ("rag", (0, 0, 2.35), (0, 0, 1.8), None)])
    mech.clip("sway", 3.0, merged(swing("hang", 8, 4), swing("hang2", 7, 5, 1.3), swing("rag", 10, 2, 0.6)))
    kit.save(mb, FAMILY, "road_warning_totem", COLORS, mech=mech)


# --- Lamps --------------------------------------------------------------------------------------


def lantern_post(name, style):
    def build():
        mb = kit.begin()
        bones, pose = [], None
        if style == "wood":
            stone_base(mb, 0, 0, seed=2)
            mb.cylinder((0, 0, 0), (0, 0, 3.2), 0.08, 0.065, "pole", segments=7)
            beam(mb, (0, 0, 3.0), (0.75, 0, 3.0), 0.045, "pole_dark")
            beam(mb, (0, 0, 2.45), (0.55, 0, 2.98), 0.035, "pole_dark")
            bones.append(hanging_lantern(mb, (0.68, 0, 2.97), "lantern", 1.2))
            pose = swing("lantern")
        elif style == "iron":
            mb.cylinder((0, 0, 0), (0, 0, 0.5), 0.3, 0.22, "stone", segments=8)
            mb.cylinder((0, 0, 0.5), (0, 0, 0.6), 0.26, 0.26, "stone_light", segments=8)
            mb.cylinder((0, 0, 0.6), (0, 0, 3.4), 0.06, 0.045, "iron", segments=8)
            for zz in (1.0, 2.2):
                mb.cylinder((0, 0, zz), (0, 0, zz + 0.1), 0.085, 0.085, "iron", segments=8)
            for sx, bone in ((-1, "lantern_l"), (1, "lantern_r")):
                for k in range(5):   # A scrolled arm.
                    a0, a1 = math.pi * k / 5, math.pi * (k + 1) / 5
                    beam(mb, (sx * (0.32 - 0.32 * math.cos(a0)), 0, 3.25 + 0.2 * math.sin(a0)),
                         (sx * (0.32 - 0.32 * math.cos(a1)), 0, 3.25 + 0.2 * math.sin(a1)), 0.025, "iron")
                bones.append(hanging_lantern(mb, (sx * 0.64, 0, 3.24), bone, 1.1))
            mb.cylinder((0, 0, 3.4), (0, 0, 3.75), 0.05, 0.0, "iron", segments=6)
            pose = merged(swing("lantern_l", 5, 3), swing("lantern_r", 5, 3, 1.4))
        elif style == "stone":
            mb.box((0, 0, 0.15), (0.8, 0.8, 0.3), "stone_dark")
            mb.box((0, 0, 1.15), (0.5, 0.5, 1.7), "stone")
            mb.box((0, 0, 2.05), (0.66, 0.66, 0.12), "stone_light")
            for sx in (-1, 1):
                for sy in (-1, 1):
                    mb.box((sx * 0.22, sy * 0.22, 2.4), (0.08, 0.08, 0.6), "stone")
            mb.box((0, 0, 2.4), (0.36, 0.36, 0.5), "window")
            mb.cylinder((0, 0, 2.2), (0, 0, 2.55), 0.1, 0.0, "flame", {"flame": 1.0}, segments=5)
            for i in range(4):
                a0, a1 = TAU * (i + 0.5) / 4, TAU * (i + 1.5) / 4
                solid(mb, [(math.cos(a0) * 0.58, math.sin(a0) * 0.58, 2.7), (math.cos(a1) * 0.58, math.sin(a1) * 0.58, 2.7), (0, 0, 3.15)],
                      (0, 0, 0.05), "stone_dark" if i % 2 else "stone")
            bones.append(("flame", (0, 0, 2.2), (0, 0, 2.5), None))
            pose = lambda t: ({"flame": [(kit.Z, 360 * t), (kit.X, 8 * math.sin(TAU * 3 * t))]}, {"flame": (0, 0, 0.03 * math.sin(TAU * 4 * t))})   # noqa: E731
        else:   # A fantasy lamp: a crystal that floats over a twisted staff.
            stone_base(mb, 0, 0, seed=5)
            for k in range(6):
                a0, a1 = 1.1 * k, 1.1 * (k + 1)
                beam(mb, (math.cos(a0) * 0.07, math.sin(a0) * 0.07, 0.45 * k), (math.cos(a1) * 0.07, math.sin(a1) * 0.07, 0.45 * (k + 1)),
                     0.07 - 0.006 * k, "bark")
            for i in range(3):
                a = TAU * i / 3
                beam(mb, (0, 0, 2.7), (math.cos(a) * 0.3, math.sin(a) * 0.3, 3.1), 0.03, "bark")
            w = {"crystal": 1.0}
            mb.cylinder((0, 0, 3.05), (0, 0, 3.35), 0.0, 0.16, "glow_crystal", w, segments=5)
            mb.cylinder((0, 0, 3.35), (0, 0, 3.8), 0.16, 0.0, "glow_crystal", w, segments=5)
            bones.append(("crystal", (0, 0, 3.35), (0, 0, 3.8), None))
            pose = lambda t: ({"crystal": [(kit.Z, 360 * t)]}, {"crystal": (0, 0, 0.08 * math.sin(TAU * 2 * t))})   # noqa: E731
        clip = {"stone": "burn", "crystal": "float"}.get(style, "swing")
        kit.save(mb, FAMILY, name, COLORS, mech=kit.Mech(bones).clip(clip, 4.0, pose))
    return build


def town_arch(name, pillars):
    """An arch over the road, 5 m wide inside, with the town's sign and two lanterns."""
    def build():
        mb = kit.begin()
        for sx in (-1, 1):
            if pillars == "stone":
                mb.box((sx * 2.8, 0, 0.2), (0.9, 0.9, 0.4), "stone_dark")
                mb.box((sx * 2.8, 0, 1.9), (0.65, 0.65, 3.0), "stone")
                for zz in (1.1, 2.0, 2.9):
                    mb.box((sx * 2.8, 0, zz), (0.69, 0.69, 0.06), "stone_dark")
                mb.box((sx * 2.8, 0, 3.47), (0.85, 0.85, 0.14), "stone_light")
            else:
                stone_base(mb, sx * 2.8, 0, 0.3, seed=3 + sx)
                log(mb, (sx * 2.8, 0, 0), (sx * 2.8, 0, 3.9), 0.16)
                beam(mb, (sx * 2.8, 0, 2.7), (sx * 1.8, 0, 3.7), 0.06, "pole_dark")
        beam(mb, (-3.3, 0, 3.75), (3.3, 0, 3.75), 0.13, "pole_dark")
        beam(mb, (-3.0, 0, 4.05), (3.0, 0, 4.05), 0.07, "pole")
        for k in range(7):
            mb.box((-1.5 + 0.5 * k, 0, 3.9), (0.08, 0.1, 0.25), "pole")
        w = {"sign": 1.0}
        for sx in (-1, 1):
            rope(mb, (sx * 0.9, 0, 3.62), (sx * 0.9, 0, 3.35), 0.02, w)
        mb.box((0, 0, 3.0), (2.3, 0.07, 0.7), "plank_light", w)
        mb.box((0, 0, 3.0), (2.4, 0.05, 0.8), "plank_dark", w)
        for side in (-1, 1):
            wolf_head(mb, -0.8, side * 0.04, 2.98, 0.6, "paint_blue", side * 0.02)
            for k in range(2):
                mb.box((0.3, side * 0.045, 3.1 - 0.2 * k), (1.1 - 0.3 * k, 0.012, 0.06), "ink", w)
        bones = [("sign", (0, 0, 3.62), (0, 0, 3.0), None)]
        bones.append(hanging_lantern(mb, (-2.0, 0, 3.62), "lantern_l", 1.2))
        bones.append(hanging_lantern(mb, (2.0, 0, 3.62), "lantern_r", 1.2))
        mech = kit.Mech(bones).clip("swing", 4.0, merged(swing("sign", 4, 0), swing("lantern_l", 6, 4, 0.8), swing("lantern_r", 6, 4, 2.0)))
        kit.save(mb, FAMILY, name, COLORS, mech=mech)
    return build


# --- Gates, obstacles ----------------------------------------------------------------------------


def toll_gate():
    mb = kit.begin()
    for sy in (-0.16, 0.16):
        mb.box((-2.4, sy, 0.75), (0.16, 0.1, 1.5), "pole_dark")
    mb.box((-2.4, 0, 0.1), (0.5, 0.6, 0.2), "stone_dark")
    w = {"arm": 1.0}
    for k in range(9):   # The arm, striped.
        mb.box((-2.15 + 0.55 * k + 0.02, 0, 1.2), (0.56, 0.11, 0.11), "paint_red" if k % 2 == 0 else "paint_white", w)
    mb.box((-3.0, 0, 1.2), (0.7, 0.13, 0.13), "pole_dark", w)
    mb.box((-3.3, 0, 1.12), (0.4, 0.34, 0.4), "stone", w)
    mb.cylinder((-2.4, -0.24, 1.2), (-2.4, 0.24, 1.2), 0.04, 0.04, "iron", w, segments=6)
    rope(mb, (2.3, 0, 1.14), (2.3, 0.0, 0.7), 0.015, w)
    mb.box((2.75, 0, 0.55), (0.14, 0.14, 1.1), "pole_dark")          # The rest post, with a fork.
    for sy in (-0.1, 0.1):
        mb.box((2.75, sy, 1.17), (0.12, 0.05, 0.2), "pole_dark")
    # The toll keeper's booth, on the side of the road.
    bx, by = -3.6, 1.9
    mb.box((bx, by, 0.1), (1.9, 1.9, 0.2), "stone_dark")
    mb.box((bx, by, 1.2), (1.6, 1.6, 2.0), "plank")
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.box((bx + sx * 0.8, by + sy * 0.8, 1.2), (0.12, 0.12, 2.05), "pole_dark")
    mb.box((bx + 0.81, by - 0.2, 1.45), (0.03, 0.8, 0.6), "paint_black")   # The window to the road.
    mb.box((bx + 0.9, by - 0.2, 1.12), (0.25, 0.9, 0.06), "plank_light")
    mb.box((bx, by - 0.81, 1.0), (0.7, 0.03, 1.6), "pole_dark")
    for i in range(4):
        a0, a1 = TAU * (i + 0.5) / 4, TAU * (i + 1.5) / 4
        solid(mb, [(bx + math.cos(a0) * 1.45, by + math.sin(a0) * 1.45, 2.15), (bx + math.cos(a1) * 1.45, by + math.sin(a1) * 1.45, 2.15),
                   (bx, by, 3.1)], (0, 0, 0.07), "roof" if i % 2 else "roof_dark")
    mb.box((bx + 1.3, by - 0.9, 0.2), (0.5, 0.36, 0.3), "plank_dark")       # The coin chest.
    mb.cylinder((bx + 1.05, by - 0.9, 0.35), (bx + 1.55, by - 0.9, 0.35), 0.18, 0.18, "plank", segments=8)
    mb.box((bx + 1.3, by - 1.09, 0.3), (0.08, 0.02, 0.1), "gold")
    solid(mb, [(bx + 0.83, by + 0.45, 1.9), (bx + 0.83, by + 0.75, 1.9), (bx + 0.83, by + 0.75, 1.5), (bx + 0.83, by + 0.45, 1.5)],
          (0.03, 0, 0), "paint_yellow")
    mb.cylinder((bx + 0.87, by + 0.6, 1.7), (bx + 0.88, by + 0.6, 1.7), 0.1, 0.1, "gold", segments=8)

    def lift(up):
        def pose(t):
            s = kit.smooth(t)
            return {"arm": [(kit.Y, -78.0 * (s if up else 1 - s))]}, {}
        return pose

    mech = kit.Mech([("arm", (-2.4, 0, 1.2), (-1.4, 0, 1.2), None)])
    mech.clip("open", 1.6, lift(True), loops=False).clip("close", 1.6, lift(False), loops=False)
    kit.save(mb, FAMILY, "road_toll_gate", COLORS, mech=mech)


def fallen_tree(name, state):
    def build():
        mb = kit.begin()
        rnd = random.Random(12)
        bark = "bark_dead" if state == "dead" else "bark"
        gap = state == "cleared"
        if gap:   # Sawn through: the road is open again.
            log(mb, (-3.6, 0.3, 0.38), (-1.3, 0.05, 0.36), 0.38, mat=bark)
            log(mb, (1.3, -0.2, 0.33), (3.4, -0.45, 0.3), 0.33, mat=bark)
            for k, (px, py) in enumerate(((-0.6, 1.5), (0.1, 1.6), (0.75, 1.45))):
                log(mb, (px, py, 0.0), (px, py, 0.55), 0.36 - 0.02 * k, mat=bark)
            mb.cylinder((0, 0, 0), (0, 0, 0.03), 0.9, 0.7, "sawdust", segments=8)
            beam(mb, (-0.9, -0.9, 0.3), (0.6, -1.2, 0.34), 0.02, "steel")       # A two-man saw.
            for sx in (-0.95, 0.65):
                mb.cylinder((sx, -1.0 if sx < 0 else -1.3, 0.2), (sx, -1.0 if sx < 0 else -1.3, 0.5), 0.03, 0.03, "pole", segments=5)
        else:
            log(mb, (-3.6, 0.3, 0.38), (3.4, -0.45, 0.3), 0.38, mat=bark)
        # The torn roots and the stump it left.
        mb.cylinder((-3.75, 0.32, 0.5), (-3.55, 0.3, 0.5), 0.95, 0.75, "soil", segments=8)
        for i in range(7):
            a = TAU * i / 7
            beam(mb, (-3.7, 0.3, 0.5), (-4.0 + rnd.uniform(-0.1, 0.1), 0.3 + math.cos(a) * 1.05, 0.5 + math.sin(a) * 1.05), 0.05, bark)
        mb.sphere((-4.4, 0.5, 0.0), 0.9, "soil_dark", segments=7, rings=4, scale=(1.0, 1.3, 0.25))
        for px, py, pz, a, length in ((0.6, -0.1, 0.5, 60, 1.6), (1.6, -0.25, 0.45, -70, 1.4), (2.4, -0.35, 0.45, 75, 1.2),
                                      (2.9, -0.4, 0.4, -60, 1.0), (3.3, -0.44, 0.35, 10, 1.1)):
            if gap and px < 1.3:
                continue
            rad = math.radians(a)
            tip = (px + math.sin(rad) * 0.3 * length + 0.5, py + math.sin(rad) * length * 0.8, pz + abs(math.cos(rad)) * length * 0.5 + 0.2)
            beam(mb, (px, py, pz), tip, 0.07, bark)
            if state != "dead":
                for _ in range(2):
                    mb.sphere((tip[0] + rnd.uniform(-0.3, 0.3), tip[1] + rnd.uniform(-0.3, 0.3), tip[2] + rnd.uniform(-0.1, 0.2)),
                              rnd.uniform(0.4, 0.6), rnd.choice(("leaf", "leaf_dark")), segments=6, rings=4, scale=(1.0, 1.0, 0.7))
        if state == "dead":
            for px in (-2.0, -0.4, 1.4):
                mb.sphere((px, 0.1, 0.72), 0.25, "moss", segments=6, rings=3, scale=(1.6, 1.0, 0.3))
        kit.save(mb, FAMILY, name, COLORS)
    return build


def rockslide(name, big):
    def build():
        mb = kit.begin()
        rnd = random.Random(21 if big else 20)
        mb.sphere((0, 0, 0), 2.4 if big else 1.7, "soil", segments=8, rings=4, scale=(1.3, 1.0, 0.1))
        for _ in range(26 if big else 14):
            a, d = rnd.uniform(0, TAU), abs(rnd.gauss(0, 1.0 if big else 0.7))
            r = rnd.uniform(0.25, 0.9 if big else 0.6) * max(0.45, 1 - d / 3)
            rock(mb, math.cos(a) * d * 1.4, math.sin(a) * d, r * 0.5 + max(0.0, (1.2 if big else 0.6) - d * 0.5), r, rnd)
        if big:
            log(mb, (1.2, -1.6, 0.25), (2.9, 0.2, 0.9), 0.16, mat="bark_dead")
        kit.save(mb, FAMILY, name, COLORS)
    return build


def sentry_box():
    mb = kit.begin()
    mb.box((0, 0, 0.08), (1.5, 1.5, 0.16), "stone_dark")
    for k in range(6):   # Striped boards, open at the front.
        mat = "paint_blue" if k % 2 == 0 else "paint_white"
        mb.box((-0.55 + 0.22 * k, 0.6, 1.25), (0.22, 0.06, 2.2), mat)
        mb.box((-0.6, -0.55 + 0.22 * k, 1.25), (0.06, 0.22, 2.2), mat)
        mb.box((0.6, -0.55 + 0.22 * k, 1.25), (0.06, 0.22, 2.2), mat)
    for i in range(4):
        a0, a1 = TAU * (i + 0.5) / 4, TAU * (i + 1.5) / 4
        solid(mb, [(math.cos(a0) * 1.05, math.sin(a0) * 1.05, 2.35), (math.cos(a1) * 1.05, math.sin(a1) * 1.05, 2.35), (0, 0, 3.3)],
              (0, 0, 0.06), "roof" if i % 2 else "roof_dark")
    mb.sphere((0, 0, 3.4), 0.08, "gold", segments=6, rings=4)
    mb.cylinder((0.5, -0.9, 0), (0.42, -0.66, 2.3), 0.02, 0.02, "pole", segments=5)
    mb.cylinder((0.42, -0.66, 2.3), (0.4, -0.6, 2.55), 0.045, 0.0, "steel", segments=4)
    mb.cylinder((-1.1, -0.6, 0), (-1.1, -0.6, 0.7), 0.05, 0.05, "iron", segments=6)     # A brazier.
    mb.cylinder((-1.1, -0.6, 0.7), (-1.1, -0.6, 0.95), 0.14, 0.28, "iron", segments=8)
    w = {"flame": 1.0}
    mb.cylinder((-1.1, -0.6, 0.92), (-1.1, -0.6, 1.2), 0.2, 0.16, "flame", w, segments=5)
    mb.cylinder((-1.1, -0.6, 1.2), (-1.1, -0.6, 1.6), 0.16, 0.0, "flame", w, segments=5)
    mb.cylinder((-1.1, -0.6, 0.95), (-1.1, -0.6, 1.35), 0.09, 0.0, "flame_core", w, segments=5)
    pose = lambda t: ({"flame": [(kit.Z, 360 * t), (kit.X, 8 * math.sin(TAU * 3 * t))]}, {"flame": (0, 0, 0.04 * math.sin(TAU * 4 * t))})   # noqa: E731
    kit.save(mb, FAMILY, "road_sentry_box", COLORS, mech=kit.Mech([("flame", (-1.1, -0.6, 0.92), (-1.1, -0.6, 1.3), None)]).clip("burn", 4.0, pose))


def waystone():
    mb = kit.begin()
    rnd = random.Random(31)
    mb.cylinder((0, 0, 0), (0, 0, 0.25), 1.3, 1.15, "stone_dark", segments=8)
    profile = ((0.55, 0.25), (0.6, 1.2), (0.5, 2.2), (0.42, 3.0), (0.2, 3.5))
    for (r0, z0), (r1, z1) in zip(profile, profile[1:]):
        mb.cylinder((rnd.uniform(-0.03, 0.03), 0, z0), (rnd.uniform(-0.03, 0.03), 0, z1), r0, r1, "stone", segments=5)
    for i in range(5):   # Runes on each face.
        a = TAU * (i + 0.5) / 5 - TAU / 10
        for k in range(4):
            z = 0.8 + 0.55 * k
            r = 0.6 - 0.05 * k - 0.085
            start = mark(mb)
            mb.box((0, -r, z), (0.16 - 0.02 * k, 0.03, 0.05), "glow_rune")
            mb.box((0.04 if k % 2 else -0.04, -r, z + 0.1), (0.05, 0.03, 0.16), "glow_rune")
            moved(mb, start, (0, 0), math.degrees(a) + 90)
    w = {"shards": 1.0}
    for i in range(4):
        a = TAU * i / 4
        mb.cylinder((math.cos(a) * 0.95, math.sin(a) * 0.95, 1.6 + 0.3 * (i % 2)), (math.cos(a) * 0.95, math.sin(a) * 0.95, 2.0 + 0.3 * (i % 2)),
                    0.09, 0.0, "glow_crystal", w, segments=4)
        mb.cylinder((math.cos(a) * 0.95, math.sin(a) * 0.95, 1.35 + 0.3 * (i % 2)), (math.cos(a) * 0.95, math.sin(a) * 0.95, 1.6 + 0.3 * (i % 2)),
                    0.0, 0.09, "glow_crystal", w, segments=4)
    for i in range(6):
        a = TAU * i / 6
        rock(mb, math.cos(a) * 1.05, math.sin(a) * 1.05, 0.3, 0.16, rnd)
    pose = lambda t: ({"shards": [(kit.Z, 90 * t)]}, {"shards": (0, 0, 0.12 * math.sin(TAU * t))})   # noqa: E731
    kit.save(mb, FAMILY, "road_waystone", COLORS, mech=kit.Mech([("shards", (0, 0, 1.6), (0, 0, 2.2), None)]).clip("hum", 4.0, pose))


def trough():
    mb = kit.begin()
    log(mb, (-1.3, 0, 0.42), (1.3, 0, 0.42), 0.36)
    mb.box((0, 0, 0.66), (2.3, 0.44, 0.2), "bark")
    mb.box((0, 0, 0.74), (2.2, 0.36, 0.06), "water")
    for sx in (-1.0, 1.0):
        log(mb, (sx, -0.45, 0.14), (sx, 0.45, 0.14), 0.14)
    mb.cylinder((1.75, 0, 0), (1.75, 0, 1.3), 0.09, 0.07, "iron", segments=7)     # A hand pump.
    mb.cylinder((1.75, 0, 1.05), (1.45, 0, 0.95), 0.045, 0.04, "iron", segments=6)
    w = {"handle": 1.0}
    beam(mb, (1.75, 0, 1.3), (2.25, 0, 1.55), 0.03, "iron", w)
    mb.cylinder((2.2, -0.06, 1.53), (2.2, 0.06, 1.53), 0.04, 0.04, "pole", w, segments=6)
    for sx in (-1.9, -0.6, 0.6):   # A rail to tie the animals.
        mb.cylinder((sx, 1.1, 0), (sx, 1.1, 1.15), 0.06, 0.05, "pole", segments=6)
    beam(mb, (-2.1, 1.1, 1.08), (0.8, 1.1, 1.08), 0.05, "pole_dark")
    mb.cylinder((-1.9, -0.2, 0), (-1.9, -0.2, 0.32), 0.13, 0.17, "plank_light", segments=8)
    pose = lambda t: ({"handle": [(kit.Y, 22 * math.sin(TAU * t))]}, {})   # noqa: E731
    kit.save(mb, FAMILY, "road_trough", COLORS, mech=kit.Mech([("handle", (1.75, 0, 1.3), (2.25, 0, 1.55), None)]).clip("pump", 1.5, pose))


def rest_shelter():
    mb = kit.begin()
    for sx in (-1, 1):
        for sy in (-1, 1):
            log(mb, (sx * 1.6, sy * 1.0, 0), (sx * 1.6, sy * 1.0, 2.3), 0.09)
        beam(mb, (sx * 1.6, -1.2, 2.3), (sx * 1.6, 1.2, 2.3), 0.07, "pole_dark")
        beam(mb, (sx * 1.6, -1.0, 1.7), (sx * 1.6, -0.4, 2.3), 0.04, "pole_dark")
    for sy in (-1, 1):
        beam(mb, (-1.8, sy * 1.0, 2.36), (1.8, sy * 1.0, 2.36), 0.07, "pole_dark")
        for r in range(4):
            u0, u1 = r / 4, (r + 1) / 4 + 0.05
            solid(mb, [(-2.0, sy * 1.5 * (1 - u0), 2.3 + 0.95 * u0), (2.0, sy * 1.5 * (1 - u0), 2.3 + 0.95 * u0),
                       (2.0, sy * 1.5 * (1 - u1), 2.3 + 0.95 * u1), (-2.0, sy * 1.5 * (1 - u1), 2.3 + 0.95 * u1)],
                  (0, sy * 0.05, 0.08), "thatch" if r % 2 == 0 else "thatch_dark")
    beam(mb, (-2.1, 0, 3.3), (2.1, 0, 3.3), 0.08, "pole_dark")
    mb.box((0, 0.75, 0.45), (2.8, 0.4, 0.07), "plank")
    mb.box((0, 0.95, 0.85), (2.8, 0.06, 0.5), "plank")
    for sx in (-1.2, 0, 1.2):
        mb.box((sx, 0.75, 0.21), (0.08, 0.36, 0.42), "plank_dark")
    mb.box((0, -0.2, 0.72), (1.6, 0.7, 0.06), "plank_light")
    for sx in (-0.7, 0.7):
        mb.box((sx, -0.2, 0.35), (0.08, 0.6, 0.7), "plank_dark")
    mb.cylinder((0.3, -0.2, 0.75), (0.3, -0.2, 0.9), 0.06, 0.07, "plank_dark", segments=7)
    mb.box((-0.3, -0.25, 0.79), (0.3, 0.2, 0.08), "sack")
    board(mb, 1.9, 0.8, 0, 2, (1.62, -1.0))
    bone = hanging_lantern(mb, (0, 0, 2.3), "lantern", 1.1)
    kit.save(mb, FAMILY, "road_rest_shelter", COLORS, mech=kit.Mech([bone]).clip("swing", 4.0, swing("lantern")))


def weathervane():
    mb = kit.begin()
    mb.cylinder((0, 0, 0), (0, 0, 0.4), 0.45, 0.35, "stone", segments=8)
    mb.cylinder((0, 0, 0.4), (0, 0, 5.0), 0.06, 0.04, "pole", segments=7)
    for a, mat in ((0, "paint_red"), (90, "ink"), (180, "ink"), (270, "ink")):   # North is marked in red.
        rad = math.radians(a)
        beam(mb, (0, 0, 4.4), (math.sin(rad) * 0.6, -math.cos(rad) * 0.6, 4.4), 0.02, "iron")
        mb.box((math.sin(rad) * 0.68, -math.cos(rad) * 0.68, 4.4), (0.12, 0.12, 0.16), mat, rotation_z=rad)
    w = {"vane": 1.0}
    beam(mb, (0, -0.85, 4.9), (0, 0.8, 4.9), 0.02, "iron", w)
    solid(mb, [(-0.012, -0.85, 4.9), (-0.012, -0.6, 5.02), (-0.012, -0.6, 4.78)], (0.024, 0, 0), "iron", w)
    solid(mb, [(-0.012, 0.8, 5.05), (-0.012, 0.45, 4.9), (-0.012, 0.8, 4.75)], (0.024, 0, 0), "iron", w)
    # A rooster cut from a sheet of metal.
    rooster = [(-0.3, 5.0), (-0.12, 4.98), (0.08, 5.0), (0.28, 5.2), (0.34, 5.45), (0.2, 5.36), (0.1, 5.22), (-0.08, 5.24),
               (-0.14, 5.42), (-0.2, 5.56), (-0.3, 5.5), (-0.36, 5.42), (-0.3, 5.36), (-0.28, 5.2)]
    solid(mb, [(-0.012, py, pz) for py, pz in rooster[:7]] + [(-0.012, -0.28, 5.2)], (0.024, 0, 0), "gold", w)
    solid(mb, [(-0.012, py, pz) for py, pz in rooster[7:]], (0.024, 0, 0), "gold", w)
    solid(mb, [(-0.012, -0.22, 5.56), (-0.012, -0.16, 5.66), (-0.012, -0.28, 5.62)], (0.024, 0, 0), "paint_red", w)
    w2 = {"sock": 1.0}                                                # A wind sock lower on the pole.
    for k in range(4):
        r0, r1 = 0.14 - 0.03 * k, 0.11 - 0.03 * k
        mb.cylinder((0, 0.1 + 0.3 * k, 3.6 - 0.04 * k), (0, 0.4 + 0.3 * k, 3.56 - 0.04 * k), r0, r1, "paint_red" if k % 2 == 0 else "paint_white",
                    w2, segments=6)

    def turn(t):
        a = 35 * math.sin(TAU * t) + 14 * math.sin(TAU * 3 * t)
        return {"vane": [(kit.Z, a)], "sock": [(kit.Z, a * 0.8 + 6 * math.sin(TAU * 4 * t)), (kit.X, 6 * math.sin(TAU * 2 * t))]}, {}

    mech = kit.Mech([("vane", (0, 0, 4.9), (0, 0, 5.4), None), ("sock", (0, 0, 3.6), (0, 0.6, 3.6), None)]).clip("turn", 8.0, turn)
    kit.save(mb, FAMILY, "road_weathervane", COLORS, mech=mech)


def bell_post():
    mb = kit.begin()
    for sx in (-1, 1):
        stone_base(mb, sx * 0.9, 0, 0.25, seed=40 + sx, n=4)
        log(mb, (sx * 0.9, 0, 0), (sx * 0.9, 0, 3.0), 0.11)
        beam(mb, (sx * 0.9, 0, 2.3), (sx * 0.35, 0, 2.9), 0.045, "pole_dark")
    beam(mb, (-1.25, 0, 2.95), (1.25, 0, 2.95), 0.1, "pole_dark")
    for sx in (-1, 1):
        solid(mb, [(sx * 1.45, -0.5, 3.0), (sx * 1.45, 0.5, 3.0), (0, 0.5, 3.55), (0, -0.5, 3.55)], (0, 0, 0.05), "roof" if sx > 0 else "roof_dark")
    w = {"bell": 1.0}
    mb.box((0, 0, 2.78), (0.4, 0.14, 0.14), "plank_dark", w)
    profile = ((0.1, 2.7), (0.16, 2.55), (0.2, 2.3), (0.3, 2.12), (0.36, 2.05))
    for (r0, z0), (r1, z1) in zip(profile, profile[1:]):
        mb.cylinder((0, 0, z0), (0, 0, z1), r0, r1, "bell", w, segments=8)
    wc = {"clapper": 1.0}
    mb.cylinder((0, 0, 2.6), (0, 0, 2.1), 0.015, 0.015, "iron", wc, segments=4)
    mb.sphere((0, 0, 2.08), 0.07, "iron", wc, segments=6, rings=4)
    rope(mb, (0, 0, 2.05), (0.0, -0.12, 0.9), 0.018, wc)

    def ring(t):
        a = 24 * math.sin(TAU * 2 * t)
        return {"bell": [(kit.X, a)], "clapper": [(kit.X, 30 * math.sin(TAU * 2 * t - 1.2) - a)]}, {}

    mech = kit.Mech([("bell", (0, 0, 2.85), (0, 0, 2.2), None), ("clapper", (0, 0, 2.6), (0, 0, 2.1), "bell")]).clip("ring", 2.0, ring)
    kit.save(mb, FAMILY, "road_bell_post", COLORS, mech=mech)


# --- Paving, steps -----------------------------------------------------------------------------


def road_tile(name, kind):
    """A 4 x 4 m stretch of road along Y."""
    def build():
        mb = kit.begin()
        rnd = random.Random({"dirt": 1, "gravel": 2, "cobble": 3, "flag": 4}[kind])
        if kind == "dirt":
            mb.box((0, 0, 0.02), (3.4, 4.0, 0.04), "soil")
            for sx in (-0.75, 0.75):
                mb.box((sx, 0, 0.035), (0.3, 4.0, 0.03), "soil_dark")
            for _ in range(10):
                rock(mb, rnd.choice((-1, 1)) * rnd.uniform(1.4, 1.75), rnd.uniform(-1.9, 1.9), 0.04, rnd.uniform(0.06, 0.14), rnd)
            for _ in range(6):
                mb.sphere((rnd.choice((-1, 1)) * rnd.uniform(1.6, 1.9), rnd.uniform(-1.8, 1.8), 0.05), 0.16, "moss", segments=5, rings=3,
                          scale=(1, 1, 0.5))
        elif kind == "gravel":
            mb.box((0, 0, 0.03), (3.6, 4.0, 0.06), "gravel")
            for _ in range(40):
                mb.box((rnd.uniform(-1.7, 1.7), rnd.uniform(-1.95, 1.95), 0.065), (rnd.uniform(0.08, 0.2), rnd.uniform(0.08, 0.2), 0.02),
                       rnd.choice(("cobble", "cobble_light", "cobble_dark")), rotation_z=rnd.uniform(0, 3))
            for sx in (-1, 1):
                for k in range(8):
                    rock(mb, sx * 1.85, -1.75 + 0.5 * k, 0.05, rnd.uniform(0.1, 0.16), rnd)
        elif kind == "cobble":
            mb.box((0, 0, 0.02), (3.6, 4.0, 0.04), "cobble_dark")
            n = 9
            for i in range(n):
                for j in range(10):
                    shift = 0.2 if j % 2 else 0.0
                    mb.box((-1.6 + 0.4 * i + shift - 0.1, -1.8 + 0.4 * j, 0.05 + rnd.uniform(0, 0.03)),
                           (rnd.uniform(0.3, 0.37), rnd.uniform(0.3, 0.37), 0.06), rnd.choice(("cobble", "cobble", "cobble_light", "cobble_dark")))
            for sx in (-1, 1):
                for k in range(5):
                    mb.box((sx * 1.9, -1.6 + 0.8 * k, 0.07), (0.22, 0.76, 0.14), "stone_light" if k % 2 else "stone")
        else:
            mb.box((0, 0, 0.02), (3.6, 4.0, 0.04), "cobble_dark")
            y = -2.0
            while y < 1.99:
                depth = min(rnd.uniform(0.7, 1.1), 2.0 - y)
                x = -1.75
                while x < 1.74:
                    width = min(rnd.uniform(0.7, 1.3), 1.75 - x)
                    mb.box((x + width / 2, y + depth / 2, 0.06 + rnd.uniform(0, 0.02)), (width - 0.05, depth - 0.05, 0.08),
                           rnd.choice(("flag", "flag", "flag_dark")))
                    x += width
                y += depth
            for sx in (-1, 1):
                for k in range(4):
                    mb.box((sx * 1.9, -1.5 + 1.0 * k, 0.09), (0.26, 0.96, 0.18), "stone_light" if k % 2 else "stone")
                mb.box((sx * 1.72, 0, 0.03), (0.12, 4.0, 0.02), "water")   # A gutter.
        kit.save(mb, FAMILY, name, COLORS)
    return build


def stairs(name, material):
    """Steps that climb 1 m in 2.5 m, 2 m wide, for a road on a slope."""
    def build():
        mb = kit.begin()
        steps = 5
        for k in range(steps):
            z, y = 0.2 * (k + 1), -1.25 + 0.5 * k
            if material == "stone":
                mb.box((0, y + 0.25, z / 2), (2.0, 0.5, z), "stone" if k % 2 else "stone_light")
                mb.box((0, y + 0.02, z - 0.03), (2.04, 0.06, 0.07), "stone_dark")
            else:
                mb.box((0, y + 0.25, z / 2), (1.9, 0.5, z), "soil")
                log(mb, (-1.05, y + 0.06, z - 0.07), (1.05, y + 0.06, z - 0.07), 0.09)
                for sx in (-0.9, 0.9):
                    mb.cylinder((sx, y - 0.03, 0), (sx, y - 0.03, z + 0.06), 0.035, 0.03, "pole_dark", segments=5)
        if material == "stone":
            for sx in (-1, 1):
                solid(mb, [(sx * 1.0, -1.25, 0), (sx * 1.0, 1.25, 0), (sx * 1.0, 1.25, 1.35), (sx * 1.0, 0.9, 1.35), (sx * 1.0, -1.25, 0.5)],
                      (sx * 0.25, 0, 0), "stone_dark")
                mb.box((sx * 1.125, 1.07, 1.42), (0.35, 0.45, 0.14), "stone_light")
        else:
            for sx in (-1, 1):
                for k, (y, z) in enumerate(((-1.2, 0.0), (0.0, 0.5), (1.2, 1.0))):
                    mb.cylinder((sx * 1.05, y, z), (sx * 1.05, y, z + 1.0), 0.05, 0.04, "pole", segments=6)
                beam(mb, (sx * 1.05, -1.2, 0.95), (sx * 1.05, 1.2, 1.95), 0.035, "pole_dark")
        kit.save(mb, FAMILY, name, COLORS)
    return build


def culvert():
    """A stone slab bridge where a stream crosses under the road: 4 m of
    road along Y, 3 m wide, over a 2 m channel along X."""
    mb = kit.begin()
    for sy in (-1, 1):
        mb.box((0, sy * 1.5, 0.1), (3.4, 1.0, 1.2), "stone")
        mb.box((0, sy * 1.02, 0.45), (3.5, 0.08, 0.5), "stone_dark")
    mb.box((0, 0, 0.72), (3.0, 4.0, 0.22), "stone_light")
    for k in range(8):
        mb.box((0, -1.75 + 0.5 * k, 0.84), (2.5, 0.46, 0.04), "cobble" if k % 2 else "cobble_light")
    for sx in (-1, 1):
        for k in range(5):
            mb.box((sx * 1.38, -1.6 + 0.8 * k, 0.98), (0.24, 0.5, 0.36), "stone" if k % 2 else "stone_dark")
    mb.box((0, 0, -0.42), (5.4, 1.9, 0.1), "water")
    rnd = random.Random(50)
    for _ in range(10):
        rock(mb, rnd.choice((-1, 1)) * rnd.uniform(1.9, 2.6), rnd.choice((-1, 1)) * rnd.uniform(0.75, 1.0), -0.3, rnd.uniform(0.15, 0.3), rnd)
    kit.save(mb, FAMILY, "road_culvert", COLORS)


def cairn(name, flag):
    def build():
        mb = kit.begin()
        rnd = random.Random(60)
        z = 0.0
        for k, r in enumerate((0.55, 0.45, 0.36, 0.28, 0.2, 0.13)):
            mb.sphere((rnd.uniform(-0.05, 0.05), rnd.uniform(-0.05, 0.05), z + r * 0.55), r, rnd.choice(("stone", "stone_dark", "stone_light")),
                      segments=6, rings=4, scale=(rnd.uniform(1.0, 1.2), rnd.uniform(0.9, 1.1), 0.6))
            z += r * 1.0
        for a in (0.4, 2.5, 4.4):
            rock(mb, math.cos(a) * 0.7, math.sin(a) * 0.7, 0.1, 0.2, rnd)
        if not flag:
            kit.save(mb, FAMILY, name, COLORS)
            return
        mb.cylinder((0.25, 0.1, 0), (0.25, 0.1, 3.4), 0.04, 0.03, "pole", segments=6)
        bones = []
        for k in range(3):   # A long red pennant in three pieces.
            bone = "flag%d" % k
            y0, y1 = -0.02 - 0.4 * k, -0.02 - 0.4 * (k + 1)
            h0, h1 = 0.22 - 0.07 * k, 0.22 - 0.07 * (k + 1)
            solid(mb, [(0.24, 0.1 + y0, 3.15 - h0), (0.24, 0.1 + y0, 3.15 + h0), (0.24, 0.1 + y1, 3.15 + h1), (0.24, 0.1 + y1, 3.15 - h1)],
                  (0.02, 0, 0), "cloth_red", {bone: 1.0})
            bones.append((bone, (0.25, 0.1 + y0, 3.15), (0.25, 0.1 + y1, 3.15), "flag%d" % (k - 1) if k else None))

        def wave(t):
            return {"flag%d" % k: [(kit.Z, (10 + 6 * k) * math.sin(TAU * 2 * t - 0.9 * k)), (kit.X, 3 * math.sin(TAU * t - k))] for k in range(3)}, {}

        kit.save(mb, FAMILY, name, COLORS, mech=kit.Mech(bones).clip("wave", 2.0, wave))
    return build


MODELS = {
    "road_signpost": signpost("road_signpost", [(20, 0.95), (200, 0.85)]),
    "road_signpost_cross": signpost("road_signpost_cross", [(15, 0.95), (105, 0.85), (195, 0.9), (290, 0.8)]),
    "road_warning_wolf": warning("road_warning_wolf", "wolf"),
    "road_warning_skull": warning("road_warning_skull", "skull"),
    "road_warning_rockfall": warning("road_warning_rockfall", "rockfall"),
    "road_warning_flood": warning("road_warning_flood", "flood"),
    "road_warning_totem": warning_totem,
    "road_lantern_wood": lantern_post("road_lantern_wood", "wood"),
    "road_lantern_iron": lantern_post("road_lantern_iron", "iron"),
    "road_lantern_stone": lantern_post("road_lantern_stone", "stone"),
    "road_lantern_crystal": lantern_post("road_lantern_crystal", "crystal"),
    "road_town_arch": town_arch("road_town_arch", "wood"),
    "road_town_arch_stone": town_arch("road_town_arch_stone", "stone"),
    "road_toll_gate": toll_gate,
    "road_fallen_tree": fallen_tree("road_fallen_tree", "fresh"),
    "road_fallen_tree_dead": fallen_tree("road_fallen_tree_dead", "dead"),
    "road_fallen_tree_cleared": fallen_tree("road_fallen_tree_cleared", "cleared"),
    "road_rockslide": rockslide("road_rockslide", False),
    "road_rockslide_big": rockslide("road_rockslide_big", True),
    "road_sentry_box": sentry_box,
    "road_waystone": waystone,
    "road_trough": trough,
    "road_rest_shelter": rest_shelter,
    "road_weathervane": weathervane,
    "road_bell_post": bell_post,
    "road_tile_dirt": road_tile("road_tile_dirt", "dirt"),
    "road_tile_gravel": road_tile("road_tile_gravel", "gravel"),
    "road_tile_cobble": road_tile("road_tile_cobble", "cobble"),
    "road_tile_flagstone": road_tile("road_tile_flagstone", "flag"),
    "road_stairs_stone": stairs("road_stairs_stone", "stone"),
    "road_stairs_log": stairs("road_stairs_log", "log"),
    "road_culvert": culvert,
    "road_cairn": cairn("road_cairn", False),
    "road_cairn_flag": cairn("road_cairn_flag", True),
}

kit.run(MODELS, FAMILY)
