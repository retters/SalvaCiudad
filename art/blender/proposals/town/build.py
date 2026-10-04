"""Town life proposals: a graveyard for the dead, a training yard for the
garrison and what a festival needs. See ../LEEME.md.

    blender --background --factory-startup --python art/blender/proposals/town/build.py -- [ids]
"""

import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import _kit as kit  # noqa: E402
import _shapes  # noqa: E402
import common  # noqa: E402
from _shapes import (TAU, barrel, beam, crate, gable_roof, log, mark, merged, moved, plank_box, rock, rope, shed_roof, solid, wheel)  # noqa: E402

FAMILY = "town"
C = common.rgb
COLORS = {
    **_shapes.COLORS,
    "grave_stone": C(0xA8A49C), "grave_dark": C(0x7A766E), "grave_light": C(0xC8C4BA), "grave_moss": C(0x6E8A4A),
    "soil": C(0x6A4A30), "soil_dark": C(0x4A3422), "grass": C(0x6A9440), "grass_dark": C(0x4F7A34),
    "flowers": C(0xC86A8A), "flowers_y": C(0xE0C040), "flowers_w": C(0xF4F0E4), "leaf": C(0x4E7A34),
    "glow_rune": C(0x7AD8FF), "glow_lantern": C(0xFFD890), "bone": C(0xE4DCC8), "eye": C(0x101010), "cave": C(0x14110F),
    "thatch": C(0xC9A55A), "thatch_dark": C(0xA8863F), "shingle": C(0x6A5038), "shingle_dark": C(0x54402C),
    "tile": C(0x9A4A2E), "tile_dark": C(0x7E3A24), "flame": C(0xF08A24), "flame_core": C(0xFFF0B0), "ember": C(0xE85820),
    "cloth_white": C(0xECE6D6), "cloth_red": C(0xB8423A), "cloth_blue": C(0x3F5E8C), "cloth_yellow": C(0xE0B840), "cloth_green": C(0x4F7A44),
    "straw": C(0xD8B85A), "straw_dark": C(0xB89640), "paint_red": C(0xB8362E), "paint_white": C(0xECE6D6), "paint_blue": C(0x2F4E8C),
    "paint_yellow": C(0xE8B830), "window": C(0xF6D070), "sand": C(0xD8C89A), "horse_white": C(0xECE6DA), "horse_brown": C(0x8A5A3A),
    "horse_black": C(0x3A3230), "horse_grey": C(0x9A968E), "bread": C(0xC08A48),
}


def flames(mb, x, y, z, s, bone):
    w = {bone: 1.0}
    mb.cylinder((x, y, z), (x, y, z + 0.3 * s), 0.14 * s, 0.2 * s, "flame", w, segments=5)
    mb.cylinder((x, y, z + 0.3 * s), (x, y, z + 0.85 * s), 0.2 * s, 0.0, "flame", w, segments=5)
    mb.cylinder((x, y, z + 0.02), (x, y, z + 0.5 * s), 0.1 * s, 0.0, "flame_core", w, segments=5)
    return (bone, (x, y, z), (x, y, z + 0.4 * s), None)


def flame_pose(bone, s=1.0, phase=0.0):
    return lambda t: ({bone: [(kit.Z, 360 * t), (kit.X, 9 * math.sin(TAU * 3 * t + phase))]}, {bone: (0, 0, 0.05 * s * math.sin(TAU * 4 * t + phase))})


def headstone(mb, x, y, kind, rot=0.0, mat="grave_stone"):
    start = mark(mb)
    if kind == "round":
        solid(mb, [(-0.28, 0, 0), (0.28, 0, 0), (0.28, 0, 0.6), (0.18, 0, 0.82), (0, 0, 0.9), (-0.18, 0, 0.82), (-0.28, 0, 0.6)], (0, 0.14, 0), mat)
    elif kind == "cross":
        mb.box((0, 0.07, 0.5), (0.14, 0.12, 1.0), mat)
        mb.box((0, 0.07, 0.7), (0.56, 0.12, 0.14), mat)
        mb.box((0, 0.07, 0.06), (0.4, 0.3, 0.12), "grave_dark")
    elif kind == "slab":
        mb.box((0, 0.07, 0.4), (0.5, 0.14, 0.8), mat)
        mb.box((0, 0.07, 0.83), (0.6, 0.2, 0.08), "grave_dark")
    else:   # A plain wooden cross.
        mb.box((0, 0.04, 0.45), (0.08, 0.07, 0.9), "plank_dark")
        mb.box((0, 0.04, 0.62), (0.46, 0.07, 0.08), "plank_dark")
    mb.box((0, -0.02, 0.45), (0.24, 0.02, 0.03), "grave_dark")
    mb.box((0, -0.02, 0.36), (0.18, 0.02, 0.03), "grave_dark")
    moved(mb, start, (x, y), rot)


def mound(mb, x, y, rnd, flowers=True):
    mb.sphere((x, y - 0.95, 0.0), 0.5, "soil", segments=7, rings=3, scale=(0.8, 1.8, 0.3))
    if flowers:
        for _ in range(3):
            mb.sphere((x + rnd.uniform(-0.25, 0.25), y - rnd.uniform(0.3, 0.6), 0.12), 0.07, rnd.choice(("flowers", "flowers_y", "flowers_w")), segments=5, rings=3)


# --- Graveyard -----------------------------------------------------------------------------------


def plot(name, race):
    def build():
        mb = kit.begin()
        rnd = random.Random({"human": 1, "dwarf": 2, "elf": 3, "orc": 4}[race])
        mb.box((0, 0, 0.03), (6.0, 6.0, 0.06), "grass_dark" if race != "orc" else "soil")
        bones, poses = [], []
        if race == "human":
            kinds = ["round", "cross", "slab", "wood", "round", "cross", "round", "slab", "wood"]
            for i in range(9):
                x, y = -2.0 + 2.0 * (i % 3), 2.2 - 2.0 * (i // 3)
                headstone(mb, x, y, kinds[i], rnd.uniform(-6, 6), rnd.choice(("grave_stone", "grave_light", "grave_dark")))
                mound(mb, x, y, rnd, i % 2 == 0)
            for sx in (-1, 1):
                for sy in (-1, 1):
                    mb.box((sx * 2.9, sy * 2.9, 0.45), (0.16, 0.16, 0.9), "grave_dark")
        elif race == "dwarf":
            for i in range(6):
                x, y = -1.9 + 1.9 * (i % 3), 1.6 - 2.6 * (i // 3)
                mb.box((x, y, 0.2), (1.1, 2.0, 0.4), "grave_dark")
                mb.box((x, y, 0.45), (0.95, 1.85, 0.1), "grave_stone")
                solid(mb, [(x - 0.4, y + 1.0, 0.4), (x + 0.4, y + 1.0, 0.4), (x + 0.4, y + 1.0, 1.2), (x, y + 1.0, 1.5), (x - 0.4, y + 1.0, 1.2)], (0, 0.2, 0), "grave_stone")
                for k in range(3):
                    mb.box((x, y + 0.98, 0.7 + 0.2 * k), (0.3 - 0.06 * k, 0.03, 0.06), "glow_rune")
                mb.box((x, y - 0.2, 0.52), (0.12, 0.7, 0.05), "iron")       # A hammer carved on the lid.
                mb.box((x, y + 0.2, 0.52), (0.4, 0.2, 0.05), "iron")
        elif race == "elf":
            for i in range(6):
                x, y = -1.9 + 1.9 * (i % 3), 1.4 - 2.6 * (i // 3)
                mb.cylinder((x, y, 0), (x + 0.05, y, 1.6), 0.08, 0.04, "bark", segments=6)     # A tree planted for each one.
                for k in range(3):
                    mb.sphere((x + rnd.uniform(-0.2, 0.2), y + rnd.uniform(-0.2, 0.2), 1.6 + 0.3 * k), 0.45 - 0.08 * k, "leaf" if k % 2 else "grass", segments=6, rings=4)
                mb.sphere((x, y - 0.5, 0.1), 0.2, "grave_light", segments=6, rings=4, scale=(1.2, 1, 0.6))
                b = "charm%d" % i
                rope(mb, (x + 0.3, y - 0.1, 1.5), (x + 0.3, y - 0.1, 1.15), 0.008, {b: 1.0})
                mb.sphere((x + 0.3, y - 0.1, 1.08), 0.07, "glow_lantern", {b: 1.0}, segments=5, rings=4)
                beam(mb, (x + 0.05, y, 1.5), (x + 0.3, y - 0.1, 1.5), 0.02, "bark")
                bones.append((b, (x + 0.3, y - 0.1, 1.5), (x + 0.3, y - 0.1, 1.1), None))
                poses.append((lambda b, i: (lambda t: ({b: [(kit.X, 8 * math.sin(TAU * t + i)), (kit.Y, 6 * math.sin(TAU * t + i * 2))]}, {})))(b, i))
        else:
            for i in range(5):
                x, y = rnd.uniform(-2.2, 2.2), rnd.uniform(-2.0, 2.2)
                for k in range(6):   # A cairn of stones and bones.
                    a = TAU * k / 6
                    rock(mb, x + math.cos(a) * 0.4, y + math.sin(a) * 0.4, 0.15, 0.25, rnd, "grave_dark")
                rock(mb, x, y, 0.45, 0.32, rnd, "grave_stone")
                mb.sphere((x, y, 0.82), 0.14, "bone", segments=6, rings=5)
                for sx in (-1, 1):
                    mb.box((x + sx * 0.05, y - 0.13, 0.83), (0.045, 0.03, 0.05), "eye")
                beam(mb, (x + 0.5, y, 0.0), (x + 0.42, y + 0.05, 1.5), 0.025, "pole_dark")           # His weapon.
                solid(mb, [(x + 0.28, y + 0.05, 1.2), (x + 0.6, y + 0.05, 1.15), (x + 0.62, y + 0.05, 1.5), (x + 0.3, y + 0.05, 1.55)], (0, 0.03, 0), "steel")
        if poses:
            kit.save(mb, FAMILY, name, COLORS, mech=kit.Mech(bones).clip("sway", 4.0, merged(*poses)))
        else:
            kit.save(mb, FAMILY, name, COLORS)
    return build


def crypt():
    mb = kit.begin()
    mb.box((0, 0.5, 0.15), (5.0, 6.0, 0.3), "grave_dark")
    mb.box((0, 1.0, 1.5), (4.0, 4.4, 2.4), "grave_stone")
    for k in range(4):
        mb.box((0, 1.0, 0.7 + 0.6 * k), (4.05, 4.45, 0.05), "grave_dark")
    gable_roof(mb, 0, 1.0, 4.0, 4.4, 2.7, 1.1, ("grave_dark", "grave_stone"), 0.3, 2, 0.1, gable=None)
    for sx in (-1, 1):
        solid(mb, [(sx * 2.0, -1.2, 2.7), (sx * 2.0, 3.2, 2.7), (sx * 2.0, 1.0, 3.8)], (-sx * 0.1, 0, 0), "grave_stone")
        mb.cylinder((sx * 1.2, -1.5, 0.3), (sx * 1.2, -1.5, 2.6), 0.2, 0.17, "grave_light", segments=8)
        mb.box((sx * 1.2, -1.5, 2.68), (0.5, 0.5, 0.16), "grave_light")
    mb.box((0, -1.5, 2.85), (3.2, 0.7, 0.2), "grave_light")
    solid(mb, [(-1.7, -1.6, 2.95), (1.7, -1.6, 2.95), (0, -1.6, 3.7)], (0, 0.2, 0), "grave_stone")
    mb.box((0, -1.22, 1.3), (1.2, 0.08, 2.0), "iron")                                      # The door, of iron bars.
    mb.box((0, -1.2, 1.3), (1.0, 0.08, 1.8), "cave")
    for k in range(5):
        mb.box((-0.4 + 0.2 * k, -1.27, 1.3), (0.04, 0.04, 1.8), "iron")
    for k in range(3):
        mb.box((0, -2.2 - 0.35 * k, 0.24 - 0.08 * k), (2.0, 0.4, 0.12), "grave_light")
    bones = []
    for i, sx in enumerate((-1, 1)):
        mb.cylinder((sx * 2.0, -2.0, 0.3), (sx * 2.0, -2.0, 1.4), 0.08, 0.06, "iron", segments=6)
        mb.cylinder((sx * 2.0, -2.0, 1.4), (sx * 2.0, -2.0, 1.6), 0.1, 0.22, "iron", segments=7)
        bones.append(flames(mb, sx * 2.0, -2.0, 1.58, 0.6, "fire%d" % i))
    mb.sphere((0, 1.0, 3.9), 0.25, "grave_light", segments=7, rings=5)
    mb.box((0, 1.0, 4.3), (0.12, 0.12, 0.6), "grave_light")
    mb.box((0, 1.0, 4.4), (0.4, 0.12, 0.12), "grave_light")
    kit.save(mb, FAMILY, "grave_crypt", COLORS, mech=kit.Mech(bones).clip("burn", 3.0, merged(flame_pose("fire0", 0.6), flame_pose("fire1", 0.6, 1.5))))


def mausoleum():
    mb = kit.begin()
    for k in range(3):
        mb.box((0, 0, 0.12 + 0.24 * k), (8.0 - 0.8 * k, 9.0 - 0.8 * k, 0.24), "grave_light" if k % 2 else "grave_stone")
    mb.box((0, 0.6, 2.6), (5.0, 5.6, 3.8), "grave_stone")
    for sx in (-2.4, -0.8, 0.8, 2.4):
        mb.cylinder((sx, -2.9, 0.72), (sx, -2.9, 4.2), 0.26, 0.22, "grave_light", segments=8)
        mb.box((sx, -2.9, 0.82), (0.7, 0.7, 0.2), "grave_stone")
        mb.box((sx, -2.9, 4.28), (0.66, 0.66, 0.16), "grave_stone")
    mb.box((0, -1.2, 4.55), (6.2, 4.6, 0.4), "grave_light")
    solid(mb, [(-3.1, -3.5, 4.75), (3.1, -3.5, 4.75), (0, -3.5, 5.9)], (0, 0.5, 0), "grave_stone")
    mb.box((0, 0.6, 4.6), (5.4, 6.0, 0.3), "grave_light")
    mb.cylinder((0, 0.6, 4.75), (0, 0.6, 5.3), 2.2, 2.2, "grave_stone", segments=10)
    mb.sphere((0, 0.6, 5.3), 2.15, "grave_dark", segments=10, rings=5, scale=(1, 1, 0.7))
    mb.cylinder((0, 0.6, 6.8), (0, 0.6, 7.4), 0.12, 0.0, "gold", segments=6)
    mb.box((0, -2.22, 2.0), (1.5, 0.08, 2.6), "iron")
    mb.box((0, -2.24, 2.0), (1.3, 0.06, 2.4), "cave")
    for sx in (-1.6, 1.6):                                                               # Two mourning figures.
        mb.cylinder((sx, -2.5, 0.72), (sx, -2.5, 1.7), 0.3, 0.2, "grave_light", segments=7)
        mb.sphere((sx, -2.55, 1.85), 0.16, "grave_light", segments=6, rings=5)
        mb.box((sx, -2.6, 1.55), (0.5, 0.2, 0.14), "grave_light")
    kit.save(mb, FAMILY, "grave_mausoleum", COLORS)


def lychgate():
    mb = kit.begin()
    for sx in (-1, 1):
        mb.box((sx * 1.5, 0, 0.5), (0.5, 0.9, 1.0), "grave_stone")
        mb.box((sx * 1.5, 0, 1.7), (0.22, 0.22, 1.5), "pole_dark")
        mb.box((sx * 3.0, 0, 0.6), (2.5, 0.5, 1.2), "grave_stone")                         # Stubs of the graveyard wall.
        mb.box((sx * 3.0, 0, 1.25), (2.6, 0.6, 0.12), "grave_dark")
        for sy in (-0.7, 0.7):
            beam(mb, (sx * 1.5, sy * 0.4, 1.9), (sx * 1.5, sy, 2.45), 0.05, "pole_dark")
    gable_roof(mb, 0, 0, 3.6, 2.0, 2.45, 1.0, ("shingle", "shingle_dark"), 0.3, 3, 0.07, gable="plank")
    bones = []
    for sx, bone in ((-1, "leaf_l"), (1, "leaf_r")):
        w = {bone: 1.0}
        x0 = sx * 1.25
        for k in range(6):
            x = x0 - sx * (0.1 + 0.22 * k)
            mb.box((x, 0, 1.0), (0.04, 0.04, 1.7 - 0.08 * abs(k - 2.5)), "iron", w)
            mb.cylinder((x, 0, 1.85 - 0.04 * abs(k - 2.5)), (x, 0, 2.0 - 0.04 * abs(k - 2.5)), 0.035, 0.0, "iron", w, segments=4)
        for zz in (0.3, 1.5):
            mb.box((x0 - sx * 0.62, 0, zz), (1.25, 0.05, 0.06), "iron", w)
        bones.append((bone, (x0, 0, 0.2), (x0, 0, 1.8), None))
    mb.box((0, 0, 2.3), (0.5, 0.05, 0.6), "plank_dark")
    mb.box((0, -0.04, 2.35), (0.08, 0.03, 0.4), "grave_light")
    mb.box((0, -0.04, 2.42), (0.26, 0.03, 0.08), "grave_light")

    def swing(opening):
        def pose(t):
            s = kit.smooth(t) if opening else 1 - kit.smooth(t)
            return {"leaf_l": [(kit.Z, 85.0 * s)], "leaf_r": [(kit.Z, -85.0 * s)]}, {}
        return pose

    mech = kit.Mech(bones).clip("open", 2.0, swing(True), loops=False).clip("close", 2.0, swing(False), loops=False)
    kit.save(mb, FAMILY, "grave_lychgate", COLORS, mech=mech)


def digger_shed():
    mb = kit.begin()
    plank_box(mb, 0, 0.3, 2.6, 2.0, 0.1, 2.0)
    mb.box((0, 0.3, 0.05), (2.8, 2.2, 0.1), "grave_dark")
    shed_roof(mb, 0, 0.3, 2.6, 2.0, 2.0, 2.6, ("shingle", "shingle_dark"), 0.25)
    mb.box((-0.5, -0.73, 1.0), (0.8, 0.04, 1.75), "plank_dark")
    for k in range(2):
        beam(mb, (0.5 + 0.3 * k, -1.1, 0.0), (0.7 + 0.2 * k, -0.74, 1.7), 0.02, "pole")
        mb.box((0.5 + 0.3 * k, -1.11, 0.14), (0.2, 0.03, 0.28), "steel")
    start = mark(mb)                                                                     # A coffin leaning on the wall.
    solid(mb, [(-0.25, 0, 0), (0.25, 0, 0), (0.36, 0, 1.4), (0.22, 0, 1.9), (-0.22, 0, 1.9), (-0.36, 0, 1.4)], (0, 0.3, 0), "plank")
    solid(mb, [(-0.2, -0.02, 0.05), (0.2, -0.02, 0.05), (0.3, -0.02, 1.4), (0.18, -0.02, 1.85), (-0.18, -0.02, 1.85), (-0.3, -0.02, 1.4)], (0, 0.02, 0), "plank_light")
    mb.box((0, -0.04, 1.3), (0.06, 0.02, 0.5), "plank_dark")
    mb.box((0, -0.04, 1.4), (0.3, 0.02, 0.06), "plank_dark")
    moved(mb, start, (1.9, 0.2), -12)
    mb.sphere((-2.0, -0.6, 0.0), 0.7, "soil", segments=7, rings=3, scale=(1, 1, 0.5))
    bone = "lantern"
    w = {bone: 1.0}
    beam(mb, (-1.25, -0.7, 1.8), (-1.25, -1.2, 1.8), 0.025, "iron")
    mb.cylinder((-1.25, -1.15, 1.8), (-1.25, -1.15, 1.6), 0.01, 0.01, "iron", w, segments=4)
    mb.box((-1.25, -1.15, 1.45), (0.16, 0.16, 0.28), "window", w)
    mb.box((-1.25, -1.15, 1.61), (0.2, 0.2, 0.04), "iron", w)
    mb.box((-1.25, -1.15, 1.29), (0.2, 0.2, 0.04), "iron", w)
    pose = lambda t: ({bone: [(kit.X, 6 * math.sin(TAU * t)), (kit.Y, 4 * math.sin(TAU * 2 * t))]}, {})   # noqa: E731
    kit.save(mb, FAMILY, "grave_digger_shed", COLORS, mech=kit.Mech([(bone, (-1.25, -1.15, 1.8), (-1.25, -1.15, 1.3), None)]).clip("swing", 4.0, pose))


def pyre(name, lit):
    def build():
        mb = kit.begin()
        rnd = random.Random(5)
        mb.cylinder((0, 0, 0), (0, 0, 0.04), 2.2, 2.1, "soil_dark", segments=10)
        for layer in range(4):
            for k in range(4):
                off = -0.9 + 0.6 * k
                z = 0.16 + 0.3 * layer
                if layer % 2 == 0:
                    log(mb, (-1.3, off, z), (1.3, off, z), 0.15)
                else:
                    log(mb, (off * 1.3, -1.0, z), (off * 1.3, 1.0, z), 0.15)
        mb.box((0, 0, 1.4), (2.0, 0.7, 0.08), "plank")
        mb.sphere((0, 0, 1.6), 0.3, "cloth_white", segments=7, rings=4, scale=(3.0, 0.9, 0.6))    # The wrapped body.
        for k in range(3):
            mb.cylinder((-0.6 + 0.6 * k - 0.02, 0, 1.6), (-0.6 + 0.6 * k + 0.02, 0, 1.6), 0.29 - 0.03 * abs(k - 1), 0.29 - 0.03 * abs(k - 1), "rope", segments=8)
        mb.cylinder((0.3, -0.5, 1.45), (-0.6, -0.5, 1.5), 0.02, 0.02, "steel", segments=4)        # His sword and shield.
        mb.cylinder((0.9, 0, 1.75), (0.9, 0, 1.79), 0.3, 0.3, "cloth_red", segments=9)
        for a in (0.5, 2.0, 3.6, 5.2):
            for k in range(3):
                mb.sphere((math.cos(a) * 2.0 + rnd.uniform(-0.2, 0.2), math.sin(a) * 2.0 + rnd.uniform(-0.2, 0.2), 0.1), 0.09, rnd.choice(("flowers", "flowers_y", "flowers_w")),
                          segments=5, rings=3)
        if not lit:
            mb.cylinder((1.9, -1.2, 0), (1.7, -1.0, 1.3), 0.03, 0.025, "pole", segments=5)        # A torch waiting.
            mb.cylinder((1.7, -1.0, 1.3), (1.67, -0.97, 1.5), 0.05, 0.06, "rope", segments=6)
            kit.save(mb, FAMILY, name, COLORS)
            return
        bones, poses = [], []
        for i, (x, y, s) in enumerate(((0, 0, 2.2), (-0.8, 0.3, 1.5), (0.8, -0.2, 1.6), (-0.3, -0.6, 1.2), (0.4, 0.6, 1.3))):
            b = "fire%d" % i
            bones.append(flames(mb, x, y, 1.0, s, b))
            poses.append(flame_pose(b, s, i * 1.3))
        for i in range(6):
            a = TAU * i / 6
            mb.box((math.cos(a) * 0.6, math.sin(a) * 0.6, 2.6 + 0.4 * i), (0.07, 0.07, 0.07), "ember", {"sparks": 1.0}, rotation_z=a)
        bones.append(("sparks", (0, 0, 2.5), (0, 0, 3.5), None))
        poses.append(lambda t: ({"sparks": [(kit.Z, 360 * t)]}, {"sparks": (0, 0, 1.5 * t)}))
        kit.save(mb, FAMILY, name, COLORS, mech=kit.Mech(bones).clip("burn", 4.0, merged(*poses)))
    return build


def bier_cart():
    mb = kit.begin()
    mb.box((0, 0, 0.8), (1.0, 2.4, 0.08), "plank_dark")
    wheel(mb, (-0.62, 0.2, 0.5), 0.5, "axle", width=0.07)
    wheel(mb, (0.62, 0.2, 0.5), 0.5, "axle", width=0.07)
    mb.cylinder((-0.62, 0.2, 0.5), (0.62, 0.2, 0.5), 0.035, 0.035, "iron", {"axle": 1.0}, segments=6)
    for sx in (-1, 1):
        beam(mb, (sx * 0.4, -1.2, 0.8), (sx * 0.4, -2.3, 0.9), 0.035, "pole")
        beam(mb, (sx * 0.4, 1.1, 0.78), (sx * 0.4, 1.15, 0.0), 0.03, "pole_dark")
    solid(mb, [(-0.25, -1.0, 0.84), (0.25, -1.0, 0.84), (0.38, -0.3, 0.84), (0.24, 1.0, 0.84), (-0.24, 1.0, 0.84), (-0.38, -0.3, 0.84)], (0, 0, 0.4), "plank")
    solid(mb, [(-0.22, -0.95, 1.24), (0.22, -0.95, 1.24), (0.34, -0.3, 1.24), (0.2, 0.95, 1.24), (-0.2, 0.95, 1.24), (-0.34, -0.3, 1.24)], (0, 0, 0.03), "plank_light")
    mb.box((0, -0.4, 1.28), (0.06, 0.6, 0.02), "plank_dark")
    mb.box((0, -0.5, 1.28), (0.34, 0.07, 0.02), "plank_dark")
    for k in range(5):
        mb.sphere((-0.15 + 0.08 * k, 0.5, 1.3), 0.07, ("flowers", "flowers_w", "flowers_y")[k % 3], segments=5, rings=3)
    pose = lambda t: ({"axle": [(kit.X, 360 * t)]}, {})   # noqa: E731
    kit.save(mb, FAMILY, "grave_bier_cart", COLORS, mech=kit.Mech([("axle", (0, 0.2, 0.5), (0.5, 0.2, 0.5), None)]).clip("roll", 3.0, pose))


def open_grave():
    mb = kit.begin()
    rnd = random.Random(7)
    mb.box((0, 0, 0.02), (4.0, 4.0, 0.04), "grass_dark")
    mb.box((0, 0, 0.03), (1.1, 2.3, 0.05), "cave")
    mb.sphere((1.3, 0.2, 0.0), 0.9, "soil", segments=8, rings=4, scale=(0.9, 1.5, 0.6))
    headstone(mb, 0, 1.5, "round", 3)
    beam(mb, (1.1, -0.9, 0.3), (1.4, -1.1, 1.5), 0.02, "pole")
    mb.box((1.1, -0.9, 0.36), (0.2, 0.03, 0.28), "steel")
    start = mark(mb)
    solid(mb, [(-0.25, -1.0, 0.0), (0.25, -1.0, 0.0), (0.38, -0.3, 0.0), (0.24, 1.0, 0.0), (-0.24, 1.0, 0.0), (-0.38, -0.3, 0.0)], (0, 0, 0.4), "plank")
    mb.box((0, -0.4, 0.42), (0.06, 0.6, 0.02), "plank_dark")
    mb.box((0, -0.5, 0.42), (0.34, 0.07, 0.02), "plank_dark")
    moved(mb, start, (-1.3, -0.1), 8)
    for k in range(2):
        beam(mb, (-1.9, -0.6 + 1.0 * k, 0.05), (-0.5, -0.6 + 1.0 * k, 0.05), 0.03, "pole_dark")   # Ropes to lower it.
    for _ in range(5):
        mb.sphere((rnd.uniform(-0.4, 0.4), 2.0 + rnd.uniform(-0.1, 0.2), 0.1), 0.08, rnd.choice(("flowers", "flowers_w", "flowers_y")), segments=5, rings=3)
    kit.save(mb, FAMILY, "grave_open", COLORS)


# --- Training yard -------------------------------------------------------------------------------


def dummy(name, kind):
    def build():
        mb = kit.begin()
        mb.box((0, 0, 0.06), (0.9, 0.9, 0.12), "plank_dark")
        for a in range(4):
            beam(mb, (math.cos(TAU * a / 4) * 0.4, math.sin(TAU * a / 4) * 0.4, 0.1), (0, 0, 0.6), 0.04, "pole_dark")
        w = {"dummy": 1.0}
        mb.cylinder((0, 0, 0.1), (0, 0, 1.9), 0.07, 0.06, "pole", w, segments=7)
        if kind == "pell":   # A bare post, hacked.
            mb.cylinder((0, 0, 0.6), (0, 0, 1.9), 0.14, 0.12, "bark", w, segments=8)
            for k in range(5):
                mb.box((0.1, -0.08, 0.9 + 0.2 * k), (0.12, 0.05, 0.03), "log_end", w, rotation_z=0.5)
        else:
            mb.cylinder((0, 0, 0.9), (0, 0, 1.5), 0.24, 0.28, "straw", w, segments=8)
            mb.cylinder((0, 0, 1.1), (0, 0, 1.16), 0.28, 0.28, "rope", w, segments=8)
            beam(mb, (-0.75, 0, 1.4), (0.75, 0, 1.4), 0.05, "pole", w)
            for sx in (-1, 1):
                mb.cylinder((sx * 0.3, 0, 1.4), (sx * 0.72, 0, 1.4), 0.1, 0.08, "straw_dark", w, segments=7)
            mb.sphere((0, 0, 1.75), 0.2, "straw", w, segments=7, rings=5)
            mb.cylinder((0, 0, 1.78), (0, 0, 1.98), 0.21, 0.15, "steel", w, segments=8)         # An old helmet.
            mb.cylinder((-0.72, -0.08, 1.4), (-0.72, -0.14, 1.4), 0.32, 0.32, "paint_red", w, segments=9)   # And a shield.
            mb.sphere((-0.72, -0.16, 1.4), 0.07, "steel", w, segments=6, rings=4)
            if kind == "target":
                mb.cylinder((0, -0.27, 1.2), (0, -0.29, 1.2), 0.2, 0.2, "paint_white", w, segments=9)
                mb.cylinder((0, -0.29, 1.2), (0, -0.3, 1.2), 0.1, 0.1, "paint_red", w, segments=8)
        pose = lambda t: ({"dummy": [(kit.X, 7 * math.sin(TAU * 3 * t) * max(0.0, 1 - t * 1.4)), (kit.Z, 10 * math.sin(TAU * 2 * t) * max(0.0, 1 - t * 1.4))]}, {})   # noqa: E731
        kit.save(mb, FAMILY, name, COLORS, mech=kit.Mech([("dummy", (0, 0, 0.1), (0, 0, 1.0), None)]).clip("hit", 1.5, pose))
    return build


def archery_butts():
    mb = kit.begin()
    rnd = random.Random(8)
    for i, x in enumerate((-2.2, 0.0, 2.2)):
        for sx in (-0.45, 0.45):
            beam(mb, (x + sx, 0.5, 0.0), (x + sx * 0.5, 0.05, 1.7), 0.04, "pole")
        beam(mb, (x, 0.9, 0.0), (x, 0.1, 1.6), 0.04, "pole_dark")
        for k, (r, mat) in enumerate(((0.6, "straw"), (0.5, "paint_white"), (0.36, "paint_blue"), (0.22, "paint_red"), (0.09, "paint_yellow"))):
            mb.cylinder((x, 0.0 - 0.012 * k, 1.1), (x, -0.1 - 0.012 * k, 1.12), r, r, mat, segments=10)
        for _ in range(2 + i):
            ax, az = x + rnd.uniform(-0.3, 0.3), 1.1 + rnd.uniform(-0.3, 0.3)
            mb.cylinder((ax, -0.15, az), (ax + rnd.uniform(-0.05, 0.05), -0.8, az + 0.1), 0.012, 0.012, "pole", segments=4)
            solid(mb, [(ax, -0.62, az + 0.07), (ax, -0.8, az + 0.1), (ax, -0.78, az + 0.16)], (0.012, 0, 0), "paint_red")
    for x in (-1.1, 1.1):                                                                # The shooting line, 7 m away.
        mb.box((x, -7.0, 0.03), (1.6, 0.14, 0.06), "paint_white")
    mb.box((3.2, -7.0, 0.5), (0.5, 0.5, 1.0), "plank")
    for k in range(5):
        mb.cylinder((3.05 + 0.07 * k, -7.0, 1.0), (3.05 + 0.07 * k, -6.95, 1.6), 0.012, 0.012, "pole", segments=4)
    kit.save(mb, FAMILY, "train_archery_butts", COLORS)


def quintain():
    mb = kit.begin()
    mb.cylinder((0, 0, 0), (0, 0, 0.3), 0.6, 0.45, "stone", segments=8)
    mb.cylinder((0, 0, 0.3), (0, 0, 2.6), 0.1, 0.08, "pole", segments=7)
    w = {"arm": 1.0}
    beam(mb, (-1.6, 0, 2.6), (1.6, 0, 2.6), 0.07, "pole_dark", w)
    mb.cylinder((0, 0, 2.55), (0, 0, 2.75), 0.14, 0.14, "iron", w, segments=7)
    mb.cylinder((-1.6, -0.02, 2.3), (-1.6, -0.1, 2.3), 0.38, 0.38, "paint_red", w, segments=9)       # The shield to hit.
    mb.cylinder((-1.6, -0.1, 2.3), (-1.6, -0.13, 2.3), 0.2, 0.2, "paint_white", w, segments=8)
    rope(mb, (1.6, 0, 2.55), (1.6, 0, 1.6), 0.02, w)
    mb.sphere((1.6, 0, 1.4), 0.26, "sack", w, segments=7, rings=5, scale=(1, 1, 1.2))               # The sandbag that hits back.
    pose = lambda t: ({"arm": [(kit.Z, 360 * 2 * kit.smooth(min(1.0, t * 1.6)))]}, {})   # noqa: E731
    kit.save(mb, FAMILY, "train_quintain", COLORS, mech=kit.Mech([("arm", (0, 0, 2.6), (0, 0, 3.0), None)]).clip("spin", 3.0, pose))


def sparring_ring():
    mb = kit.begin()
    mb.box((0, 0, 0.04), (6.4, 6.4, 0.08), "sand")
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.cylinder((sx * 3.0, sy * 3.0, 0), (sx * 3.0, sy * 3.0, 1.3), 0.09, 0.08, "pole", segments=7)
    for zz in (0.6, 1.1):
        for s in (-1, 1):
            rope(mb, (-3.0, s * 3.0, zz), (3.0, s * 3.0, zz), 0.03)
            rope(mb, (s * 3.0, -3.0, zz), (s * 3.0, 3.0, zz), 0.03)
    for sx in (-0.9, 0.9):                                                               # A rack of wooden swords.
        mb.cylinder((4.2, sx, 0), (4.2, sx, 1.4), 0.05, 0.045, "pole_dark", segments=6)
    beam(mb, (4.2, -1.0, 1.3), (4.2, 1.0, 1.3), 0.04, "pole_dark")
    beam(mb, (4.2, -1.0, 0.5), (4.2, 1.0, 0.5), 0.04, "pole_dark")
    for k in range(5):
        y = -0.7 + 0.35 * k
        beam(mb, (4.3, y, 0.1), (4.25, y, 1.6), 0.025, "plank_light")
        mb.box((4.27, y, 0.6), (0.04, 0.24, 0.04), "plank_dark")
    for k, mat in enumerate(("paint_red", "paint_blue")):
        mb.cylinder((4.1, -1.6 - 0.8 * k, 0.45), (4.0, -1.6 - 0.8 * k, 0.5), 0.4, 0.4, mat, segments=9)
    mb.box((-4.2, 0, 0.45), (0.4, 2.4, 0.07), "plank")
    for sy in (-1.0, 1.0):
        mb.box((-4.2, sy, 0.22), (0.36, 0.08, 0.44), "plank_dark")
    barrel(mb, -4.2, 1.9, 0.0, 0.8, 0.28)
    kit.save(mb, FAMILY, "train_sparring_ring", COLORS)


def obstacle_course():
    mb = kit.begin()
    for k in range(6):                                                                   # A wall to climb.
        mb.box((-4.0, 0, 0.2 + 0.4 * k), (0.2, 2.4, 0.38), "plank" if k % 2 else "plank_light")
    for sy in (-1.2, 1.2):
        mb.cylinder((-4.0, sy, 0), (-4.0, sy, 2.6), 0.09, 0.08, "pole_dark", segments=6)
    rope(mb, (-4.15, 0.5, 2.4), (-4.2, 0.5, 0.2), 0.03)
    for k in range(4):                                                                   # Logs to jump.
        log(mb, (-2.0 + 1.2 * k, -1.2, 0.35 + 0.1 * (k % 2)), (-2.0 + 1.2 * k, 1.2, 0.35 + 0.1 * (k % 2)), 0.14)
        for sy in (-1.0, 1.0):
            mb.cylinder((-2.0 + 1.2 * k, sy, 0), (-2.0 + 1.2 * k, sy, 0.3 + 0.1 * (k % 2)), 0.05, 0.05, "pole_dark", segments=5)
    log(mb, (3.0, 0, 0.9), (7.0, 0, 0.9), 0.13)                                            # A beam to walk.
    for x in (3.2, 6.8):
        beam(mb, (x, -0.4, 0), (x, 0, 0.8), 0.05, "pole_dark")
        beam(mb, (x, 0.4, 0), (x, 0, 0.8), 0.05, "pole_dark")
    for sy in (-1.0, 1.0):                                                               # And a frame of ropes.
        mb.cylinder((8.6, sy, 0), (8.6, sy, 3.4), 0.1, 0.08, "pole", segments=6)
    beam(mb, (8.6, -1.2, 3.3), (8.6, 1.2, 3.3), 0.08, "pole_dark")
    for k in range(3):
        rope(mb, (8.6, -0.6 + 0.6 * k, 3.25), (8.6, -0.6 + 0.6 * k, 0.3), 0.03)
        for j in range(4):
            mb.sphere((8.6, -0.6 + 0.6 * k, 0.6 + 0.7 * j), 0.06, "rope", segments=5, rings=3)
    kit.save(mb, FAMILY, "train_obstacle_course", COLORS)


def jousting_list():
    mb = kit.begin()
    for k in range(13):                                                                  # The tilt barrier.
        mb.cylinder((-6.0 + 1.0 * k, 0, 0), (-6.0 + 1.0 * k, 0, 1.25), 0.06, 0.05, "pole_dark", segments=6)
    for k in range(12):
        mb.box((-5.5 + 1.0 * k, 0, 0.75), (1.0, 0.05, 0.9), "paint_red" if k % 2 else "paint_white")
    beam(mb, (-6.0, 0, 1.25), (6.0, 0, 1.25), 0.05, "pole")
    bones = []
    for i, x in enumerate((-6.6, 6.6)):
        mb.cylinder((x, 0, 0), (x, 0, 4.0), 0.07, 0.05, "pole", segments=6)
        b = "pennant%d" % i
        solid(mb, [(x, 0.02, 3.9), (x, 1.4, 3.6), (x, 0.02, 3.3)], (0.025, 0, 0), "cloth_blue" if i else "cloth_red", {b: 1.0})
        bones.append((b, (x, 0, 3.6), (x, 1.0, 3.6), None))
    for sy in (-2.6, 2.6):                                                               # The lanes, of sand.
        mb.box((0, sy / 2 * 1.0, 0.02), (13.0, 2.0, 0.04), "sand")
    for sx in (-0.5, 0.5):                                                               # A rack of lances.
        mb.cylinder((7.6 + sx, -2.6, 0), (7.6 + sx, -2.6, 1.3), 0.05, 0.045, "pole_dark", segments=6)
    beam(mb, (7.0, -2.6, 1.2), (8.2, -2.6, 1.2), 0.04, "pole_dark")
    for k in range(4):
        x = 7.2 + 0.27 * k
        mb.cylinder((x, -2.9, 0), (x, -2.6, 3.4), 0.035, 0.012, ("paint_red", "paint_white", "paint_blue", "paint_yellow")[k], segments=6)
        mb.cylinder((x, -2.82, 0.7), (x, -2.78, 0.95), 0.1, 0.035, "steel", segments=7)
    pose = lambda t: ({"pennant0": [(kit.Z, 14 * math.sin(TAU * 2 * t)), (kit.Y, 5 * math.sin(TAU * t))],   # noqa: E731
                       "pennant1": [(kit.Z, 14 * math.sin(TAU * 2 * t + 1.4)), (kit.Y, 5 * math.sin(TAU * t + 1))]}, {})
    kit.save(mb, FAMILY, "train_jousting_list", COLORS, mech=kit.Mech(bones).clip("wave", 2.0, pose))


def grandstand():
    mb = kit.begin()
    for k in range(4):                                                                   # Tiers of benches.
        mb.box((0, 0.9 * k, 0.5 + 0.5 * k), (8.0, 0.9, 0.1), "plank")
        mb.box((0, 0.9 * k - 0.4, 0.25 + 0.5 * k), (8.0, 0.08, 0.5 + 0.0), "plank_dark")
        for sx in (-3.9, 0.0, 3.9):
            mb.box((sx, 0.9 * k, (0.5 + 0.5 * k) / 2), (0.14, 0.8, 0.5 + 0.5 * k), "pole_dark")
    for sx in (-4.0, 4.0):
        mb.cylinder((sx, -0.5, 0), (sx, -0.5, 3.6), 0.09, 0.08, "pole", segments=6)
        mb.cylinder((sx, 3.2, 0), (sx, 3.2, 4.6), 0.09, 0.08, "pole", segments=6)
    for k in range(8):                                                                   # A striped awning.
        x0, x1 = -4.2 + 1.05 * k, -4.2 + 1.05 * (k + 1)
        solid(mb, [(x0, -0.9, 3.5), (x1, -0.9, 3.5), (x1, 3.4, 4.6), (x0, 3.4, 4.6)], (0, 0, 0.04), "cloth_red" if k % 2 else "cloth_white")
        solid(mb, [(x0, -0.9, 3.5), (x1, -0.9, 3.5), ((x0 + x1) / 2, -0.9, 3.15)], (0, -0.03, 0), "cloth_yellow")
    mb.box((0, 2.9, 2.6), (2.0, 0.7, 0.9), "cloth_blue")                                   # The lord's box.
    mb.box((0, 2.5, 3.1), (2.2, 0.08, 0.08), "gold")
    for sx in (-0.5, 0.5):
        mb.box((sx, 3.0, 2.5), (0.6, 0.6, 1.3), "plank_dark")
    bones = []
    for i, sx in enumerate((-4.0, 4.0)):
        b = "flag%d" % i
        mb.cylinder((sx, 3.2, 4.6), (sx, 3.2, 6.0), 0.04, 0.03, "pole", segments=5)
        solid(mb, [(sx, 3.22, 5.95), (sx, 4.3, 5.7), (sx, 3.22, 5.4)], (0.025, 0, 0), "cloth_blue", {b: 1.0})
        bones.append((b, (sx, 3.2, 5.7), (sx, 4.2, 5.7), None))
    pose = lambda t: ({"flag0": [(kit.Z, 14 * math.sin(TAU * 2 * t))], "flag1": [(kit.Z, 14 * math.sin(TAU * 2 * t + 1.2))]}, {})   # noqa: E731
    kit.save(mb, FAMILY, "train_grandstand", COLORS, mech=kit.Mech(bones).clip("wave", 2.0, pose))


# --- Festival ------------------------------------------------------------------------------------


def maypole():
    mb = kit.begin()
    rnd = random.Random(9)
    mb.cylinder((0, 0, 0), (0, 0, 0.25), 0.7, 0.55, "stone", segments=9)
    for k in range(12):                                                                  # A pole painted in a spiral.
        mb.cylinder((0, 0, 0.25 + 0.5 * k), (0, 0, 0.75 + 0.5 * k), 0.09, 0.09, "paint_red" if k % 2 else "paint_white", segments=8)
    w = {"crown": 1.0}
    for i in range(10):                                                                  # A wreath of leaves and flowers.
        a = TAU * i / 10
        mb.sphere((math.cos(a) * 0.7, math.sin(a) * 0.7, 5.6), 0.2, "leaf" if i % 2 else "grass", w, segments=6, rings=4)
        mb.sphere((math.cos(a + 0.3) * 0.75, math.sin(a + 0.3) * 0.75, 5.75), 0.09, ("flowers", "flowers_y", "flowers_w")[i % 3], w, segments=5, rings=3)
    for i in range(4):
        a = TAU * i / 4
        beam(mb, (0, 0, 6.1), (math.cos(a) * 0.7, math.sin(a) * 0.7, 5.6), 0.02, "rope", w)
    mb.sphere((0, 0, 6.3), 0.14, "gold", w, segments=7, rings=5)
    cloths = ("cloth_red", "cloth_yellow", "cloth_blue", "cloth_white", "cloth_green", "cloth_red", "cloth_yellow", "cloth_blue")
    for i in range(8):                                                                   # Ribbons out to the dancers' hands.
        a = TAU * i / 8
        solid(mb, [(math.cos(a) * 0.1, math.sin(a) * 0.1, 6.0), (math.cos(a) * 3.2, math.sin(a) * 3.2, 1.3), (math.cos(a + 0.05) * 3.2, math.sin(a + 0.05) * 3.2, 1.3),
                   (math.cos(a + 0.6) * 0.1, math.sin(a + 0.6) * 0.1, 6.0)], (0, 0, 0.02), cloths[i], w)
        mb.sphere((math.cos(a + 0.025) * 3.2, math.sin(a + 0.025) * 3.2, 1.25), 0.08, cloths[i], w, segments=5, rings=3)
    for _ in range(14):
        a, d = rnd.uniform(0, TAU), rnd.uniform(1.0, 3.8)
        mb.sphere((math.cos(a) * d, math.sin(a) * d, 0.06), 0.07, rnd.choice(("flowers", "flowers_y", "flowers_w")), segments=5, rings=3)
    pose = lambda t: ({"crown": [(kit.Z, 360 * t)]}, {"crown": (0, 0, 0.05 * math.sin(TAU * 8 * t))})   # noqa: E731
    kit.save(mb, FAMILY, "fest_maypole", COLORS, mech=kit.Mech([("crown", (0, 0, 5.6), (0, 0, 6.3), None)]).clip("dance", 12.0, pose))


def feast_tent():
    mb = kit.begin()
    for sx in (-3.0, 0.0, 3.0):
        for sy in (-4.0, 4.0):
            mb.cylinder((sx, sy, 0), (sx, sy, 2.4 if sx else 3.6), 0.08, 0.07, "pole", segments=6)
    mb.cylinder((0, 0, 0), (0, 0, 3.7), 0.09, 0.08, "pole", segments=6)
    for k in range(8):                                                                   # A striped roof.
        y0, y1 = -4.3 + 1.075 * k, -4.3 + 1.075 * (k + 1)
        mat = "cloth_red" if k % 2 else "cloth_white"
        for sx in (-1, 1):
            solid(mb, [(sx * 3.3, y0, 2.3), (sx * 3.3, y1, 2.3), (0, y1, 3.7), (0, y0, 3.7)], (0, 0, 0.04), mat)
            solid(mb, [(sx * 3.3, y0, 2.3), (sx * 3.3, y1, 2.3), (sx * 3.3, (y0 + y1) / 2, 1.95)], (sx * 0.03, 0, 0), "cloth_yellow")
    for sx in (-1.4, 1.4):                                                               # Two long tables with benches.
        mb.box((sx, 0, 0.78), (1.0, 6.4, 0.07), "plank")
        for sy in (-2.8, 0.0, 2.8):
            mb.box((sx, sy, 0.38), (0.8, 0.1, 0.76), "plank_dark")
        for s in (-1, 1):
            mb.box((sx + s * 0.8, 0, 0.45), (0.3, 6.2, 0.06), "plank_light")
        for k in range(6):
            y = -2.6 + 1.04 * k
            mb.cylinder((sx - 0.2, y, 0.82), (sx - 0.2, y, 0.94), 0.05, 0.055, "plank_dark", segments=6)
            mb.sphere((sx + 0.2, y + 0.3, 0.88), 0.12, "bread", segments=6, rings=4, scale=(1.3, 0.9, 0.6))
        mb.cylinder((sx, 0, 0.82), (sx, 0, 0.9), 0.3, 0.36, "plank_dark", segments=9)
        mb.sphere((sx, 0, 0.98), 0.22, "cloth_red", segments=7, rings=4, scale=(1.3, 1, 0.6))
    for k in range(3):
        barrel(mb, -2.6 + 0.7 * k, 4.6, 0.0, 0.9, 0.32)
    bones = []
    for i, y in enumerate((-2.6, 0.0, 2.6)):
        b = "lamp%d" % i
        rope(mb, (0, y, 3.65), (0, y, 3.1), 0.01, {b: 1.0})
        mb.box((0, y, 2.95), (0.2, 0.2, 0.3), "window", {b: 1.0})
        mb.box((0, y, 3.12), (0.24, 0.24, 0.04), "iron", {b: 1.0})
        bones.append((b, (0, y, 3.65), (0, y, 3.0), None))
    pose = lambda t: ({"lamp%d" % i: [(kit.X, 5 * math.sin(TAU * t + i)), (kit.Y, 4 * math.sin(TAU * t + i * 2))] for i in range(3)}, {})   # noqa: E731
    kit.save(mb, FAMILY, "fest_feast_tent", COLORS, mech=kit.Mech(bones).clip("swing", 4.0, pose))


def puppet_theatre():
    mb = kit.begin()
    plank_box(mb, 0, 0, 1.8, 1.0, 0.0, 1.3, ("paint_red", "paint_yellow"))
    for sx in (-0.9, 0.9):
        mb.box((sx, -0.5, 1.6), (0.1, 0.1, 3.2), "paint_blue")
        mb.box((sx, 0.5, 1.6), (0.1, 0.1, 3.2), "paint_blue")
    mb.box((0, 0.5, 2.2), (1.8, 0.05, 1.8), "cloth_blue")
    mb.box((0, -0.5, 2.9), (1.9, 0.08, 0.5), "paint_red")
    solid(mb, [(-1.0, -0.56, 3.15), (1.0, -0.56, 3.15), (0, -0.56, 3.8)], (0, 0.1, 0), "paint_yellow")
    for sx in (-1, 1):                                                                   # Curtains drawn aside.
        solid(mb, [(sx * 0.85, -0.52, 2.65), (sx * 0.5, -0.52, 2.65), (sx * 0.72, -0.52, 1.35), (sx * 0.85, -0.52, 1.3)], (0, -0.03, 0), "cloth_red")
    bones = []
    for i, (x, mat, hat) in enumerate(((-0.35, "cloth_green", "paint_yellow"), (0.35, "cloth_red", "paint_blue"))):
        b = "puppet%d" % i
        w = {b: 1.0}
        mb.cylinder((x, -0.2, 1.3), (x, -0.2, 1.75), 0.16, 0.1, mat, w, segments=7)
        mb.sphere((x, -0.2, 1.88), 0.13, "cloth_white", w, segments=7, rings=5)
        mb.cylinder((x, -0.2, 1.98), (x, -0.2, 2.25), 0.12, 0.0, hat, w, segments=6)
        mb.box((x, -0.33, 1.9), (0.04, 0.03, 0.04), "paint_red", w)
        for sx in (-1, 1):
            beam(mb, (x + sx * 0.1, -0.2, 1.65), (x + sx * 0.3, -0.25, 1.8), 0.035, mat, w)
        bones.append((b, (x, -0.2, 1.3), (x, -0.2, 1.9), None))
    for k in range(3):                                                                   # Benches for the children.
        mb.box((0, -2.0 - 0.9 * k, 0.3), (2.4, 0.3, 0.06), "plank")
        for sx in (-1.0, 1.0):
            mb.box((sx, -2.0 - 0.9 * k, 0.15), (0.08, 0.26, 0.3), "plank_dark")

    def show(t):
        return ({"puppet0": [(kit.Y, 14 * math.sin(TAU * 2 * t)), (kit.Z, 20 * math.sin(TAU * t))], "puppet1": [(kit.Y, 14 * math.sin(TAU * 2 * t + 2)), (kit.Z, -20 * math.sin(TAU * t))]},
                {"puppet0": (0, 0, 0.12 * abs(math.sin(TAU * 2 * t))), "puppet1": (0, 0, 0.12 * abs(math.sin(TAU * 2 * t + 1.57)))})

    kit.save(mb, FAMILY, "fest_puppet_theatre", COLORS, mech=kit.Mech(bones).clip("show", 4.0, show))


def skittles():
    mb = kit.begin()
    mb.box((0, 0, 0.03), (1.6, 9.0, 0.06), "sand")
    for sx in (-1, 1):
        mb.box((sx * 0.85, 0, 0.1), (0.1, 9.0, 0.2), "plank_dark")
    mb.box((0, 4.5, 0.25), (1.8, 0.1, 0.5), "plank")
    for i, (x, y) in enumerate(((0, 3.2), (-0.2, 3.5), (0.2, 3.5), (-0.4, 3.8), (0.0, 3.8), (0.4, 3.8), (-0.2, 4.1), (0.2, 4.1), (0, 2.9))):
        mb.cylinder((x, y, 0.06), (x, y, 0.3), 0.07, 0.05, "plank_light", segments=7)
        mb.sphere((x, y, 0.36), 0.06, "paint_red" if i == 8 else "plank_light", segments=6, rings=4)
    mb.sphere((0.1, -3.6, 0.17), 0.11, "plank_dark", segments=8, rings=5)
    mb.sphere((0.5, -4.1, 0.17), 0.11, "plank_dark", segments=8, rings=5)
    mb.box((1.6, -3.8, 0.45), (0.4, 1.6, 0.07), "plank")                                   # A bench with mugs.
    for sy in (-4.4, -3.2):
        mb.box((1.6, sy, 0.22), (0.36, 0.08, 0.44), "plank_dark")
    for k in range(2):
        mb.cylinder((1.6, -4.1 + 0.5 * k, 0.49), (1.6, -4.1 + 0.5 * k, 0.61), 0.05, 0.055, "plank_dark", segments=6)
    mb.box((-1.5, 4.2, 0.6), (0.06, 0.5, 0.7), "plank_dark")                               # The score, in chalk.
    for k in range(4):
        mb.box((-1.54, 4.05 + 0.1 * k, 0.75), (0.02, 0.03, 0.25), "paint_white")
    kit.save(mb, FAMILY, "fest_skittles", COLORS)


def lantern_pole():
    mb = kit.begin()
    mb.cylinder((0, 0, 0), (0, 0, 0.3), 0.5, 0.4, "stone", segments=8)
    mb.cylinder((0, 0, 0.3), (0, 0, 5.0), 0.08, 0.06, "pole", segments=7)
    bones, poses = [], []
    cloths = ("cloth_red", "cloth_yellow", "cloth_white", "cloth_blue", "cloth_green")
    for i in range(10):
        a = TAU * i / 10 * 1.7
        z = 4.7 - 0.33 * i
        r = 0.5 + 0.13 * i
        beam(mb, (0, 0, z + 0.2), (math.cos(a) * r, math.sin(a) * r, z + 0.25), 0.02, "pole_dark")
        b = "lamp%d" % i
        w = {b: 1.0}
        x, y = math.cos(a) * r, math.sin(a) * r
        rope(mb, (x, y, z + 0.25), (x, y, z + 0.05), 0.008, w)
        mb.sphere((x, y, z - 0.1), 0.16, "glow_lantern" if i % 2 else cloths[i % 5], w, segments=7, rings=5, scale=(1, 1, 1.15))
        for zz in (z + 0.06, z - 0.27):
            mb.cylinder((x, y, zz), (x, y, zz + 0.03), 0.08, 0.08, "pole_dark", w, segments=6)
        bones.append((b, (x, y, z + 0.25), (x, y, z - 0.2), None))
        poses.append((lambda b, i: (lambda t: ({b: [(kit.X, 9 * math.sin(TAU * t + i)), (kit.Y, 7 * math.sin(TAU * t + i * 1.7))]}, {})))(b, i))
    mb.sphere((0, 0, 5.1), 0.14, "gold", segments=7, rings=5)
    kit.save(mb, FAMILY, "fest_lantern_pole", COLORS, mech=kit.Mech(bones).clip("sway", 4.0, merged(*poses)))


def carousel():
    mb = kit.begin()
    mb.cylinder((0, 0, 0), (0, 0, 0.2), 3.0, 2.9, "plank_dark", segments=12)
    mb.cylinder((0, 0, 0.2), (0, 0, 3.6), 0.16, 0.13, "paint_red", segments=8)
    w = {"turn": 1.0}
    mb.cylinder((0, 0, 0.2), (0, 0, 0.32), 2.7, 2.7, "plank", w, segments=12)
    coats = ("horse_white", "horse_brown", "horse_black", "horse_grey")
    for i in range(4):
        a = TAU * i / 4
        x, y = math.cos(a) * 1.9, math.sin(a) * 1.9
        start = mark(mb)
        mb.cylinder((0, 0, 0.32), (0, 0, 2.9), 0.03, 0.03, "gold", w, segments=6)
        mb.sphere((0, 0, 1.15), 0.2, coats[i], w, segments=7, rings=5, scale=(1.0, 2.2, 1.0))
        mb.cylinder((0, -0.3, 1.25), (0, -0.55, 1.65), 0.13, 0.09, coats[i], w, segments=6)
        mb.cylinder((0, -0.52, 1.68), (0, -0.82, 1.52), 0.1, 0.06, coats[i], w, segments=6)
        for sx in (-0.1, 0.1):
            for sy, lean in ((-0.25, -0.2), (0.3, 0.2)):
                mb.cylinder((sx, sy, 1.0), (sx, sy + lean, 0.55), 0.05, 0.035, coats[i], w, segments=5)
        mb.cylinder((0, 0.42, 1.2), (0, 0.6, 0.85), 0.05, 0.02, "eye", w, segments=5)
        mb.box((0, 0.02, 1.36), (0.3, 0.4, 0.06), ("cloth_red", "cloth_blue", "cloth_yellow", "cloth_green")[i], w)
        moved(mb, start, (x, y), math.degrees(a))
    for i in range(8):                                                                   # A striped canopy.
        a0, a1 = TAU * i / 8, TAU * (i + 1) / 8
        solid(mb, [(math.cos(a0) * 3.1, math.sin(a0) * 3.1, 2.9), (math.cos(a1) * 3.1, math.sin(a1) * 3.1, 2.9), (0, 0, 3.9)], (0, 0, 0.05),
              "cloth_red" if i % 2 else "cloth_white", w)
        solid(mb, [(math.cos(a0) * 3.1, math.sin(a0) * 3.1, 2.9), (math.cos(a1) * 3.1, math.sin(a1) * 3.1, 2.9), (math.cos((a0 + a1) / 2) * 3.1, math.sin((a0 + a1) / 2) * 3.1, 2.55)],
              (math.cos((a0 + a1) / 2) * 0.03, math.sin((a0 + a1) / 2) * 0.03, 0), "cloth_yellow", w)
    mb.sphere((0, 0, 4.0), 0.16, "gold", w, segments=7, rings=5)
    beam(mb, (2.9, 0, 0.9), (3.9, 0, 0.9), 0.04, "pole", w)                                 # The bar to push it round.
    pose = lambda t: ({"turn": [(kit.Z, 360 * t)]}, {})   # noqa: E731
    kit.save(mb, FAMILY, "fest_carousel", COLORS, mech=kit.Mech([("turn", (0, 0, 0.3), (0, 0, 1.5), None)]).clip("turn", 10.0, pose))


MODELS = {
    "grave_plot_human": plot("grave_plot_human", "human"),
    "grave_plot_dwarf": plot("grave_plot_dwarf", "dwarf"),
    "grave_plot_elf": plot("grave_plot_elf", "elf"),
    "grave_plot_orc": plot("grave_plot_orc", "orc"),
    "grave_crypt": crypt,
    "grave_mausoleum": mausoleum,
    "grave_lychgate": lychgate,
    "grave_digger_shed": digger_shed,
    "grave_pyre": pyre("grave_pyre", False),
    "grave_pyre_lit": pyre("grave_pyre_lit", True),
    "grave_bier_cart": bier_cart,
    "grave_open": open_grave,
    "train_dummy": dummy("train_dummy", "straw"),
    "train_dummy_target": dummy("train_dummy_target", "target"),
    "train_dummy_pell": dummy("train_dummy_pell", "pell"),
    "train_archery_butts": archery_butts,
    "train_quintain": quintain,
    "train_sparring_ring": sparring_ring,
    "train_obstacle_course": obstacle_course,
    "train_jousting_list": jousting_list,
    "train_grandstand": grandstand,
    "fest_maypole": maypole,
    "fest_feast_tent": feast_tent,
    "fest_puppet_theatre": puppet_theatre,
    "fest_skittles": skittles,
    "fest_lantern_pole": lantern_pole,
    "fest_carousel": carousel,
}

kit.run(MODELS, FAMILY)
