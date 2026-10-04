"""Nature proposals: terrain features, resource outcrops, dens, small
plants that sway and insects that fly. See ../LEEME.md.

    blender --background --factory-startup --python art/blender/proposals/nature/build.py -- [ids]
"""

import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import _kit as kit  # noqa: E402
import _shapes  # noqa: E402
import common  # noqa: E402
from _shapes import TAU, beam, log, rock, solid  # noqa: E402

FAMILY = "nature"
C = common.rgb
COLORS = {
    **_shapes.COLORS,
    "grass": C(0x6A9440), "grass_dark": C(0x4F7A34), "grass_light": C(0x8AB050), "reed": C(0x7A9A48),
    "reed_top": C(0x6A4424), "fern": C(0x3C8838), "moss": C(0x5E8A3A), "leaf": C(0x4E7A34),
    "water": C(0x4A8FC0), "water_light": C(0x7AB8E0), "water_deep": C(0x2F6A9A), "foam": C(0xF0F6FA),
    "soil": C(0x6A4A30), "soil_dark": C(0x4A3422), "mud": C(0x5A4632), "mud_light": C(0x7A6248),
    "sand": C(0xE0CFA0), "sand_dark": C(0xC8B480), "shell": C(0xF0D8C8), "coral": C(0xE86A5A), "starfish": C(0xE8843A),
    "snow": C(0xF2F6FA), "snow_shade": C(0xD4E0EC), "ice": C(0xBFE4F0), "carrot": C(0xE8843A),
    "coal": C(0x2A2826), "coal_shine": C(0x4A4A52), "clay": C(0xB06A48), "clay_dark": C(0x8E5236),
    "glow_crystal": C(0x8AE8FF), "glow_crystal_violet": C(0xC08AFF), "glow_lava": C(0xFF6A20), "glow_firefly": C(0xE8FF70),
    "glow_meteor": C(0x70FFB0), "lava_rock": C(0x2E2624), "smoke": C(0x9A9A9A), "steam": C(0xE8EEF2),
    "honey": C(0xE0A030), "bee": C(0xE8C020), "eye": C(0x101010), "egg": C(0xE8E4D0), "nest": C(0x8A6A3A),
    "wing_orange": C(0xF08A24), "wing_blue": C(0x4A8AE0), "wing_white": C(0xF4F0E0), "wing_clear": C(0xBFE4F0),
    "dragonfly": C(0x2E8A7A), "mushroom_cap": C(0xB8362E), "mushroom_stem": C(0xEADFC8), "bone": C(0xE4DCC8),
    "cave": C(0x14110F), "sulfur": C(0xD8C840),
}


def blob(mb, x, y, z, r, mat, scale=(1, 1, 1), w=None, seg=6, rings=4):
    mb.sphere((x, y, z), r, mat, w, segments=seg, rings=rings, scale=scale)


def rock_face(mb, x0, x1, height, rnd, lean=0.35, gap=None, depth=3.0):
    """A cliff face toward -Y made of boulders in front of a solid core."""
    width = x1 - x0
    mb.box(((x0 + x1) / 2, depth / 2 + 0.7, height / 2 - 0.2), (width, depth, height + 0.4), "stone_dark")
    z = 0.3
    while z < height:
        x = x0 + rnd.uniform(0.2, 0.7)
        while x < x1:
            r = rnd.uniform(0.75, 1.15)
            if not (gap and gap[0] < x < gap[1]):
                rock(mb, x, 0.6 + lean * z + rnd.uniform(-0.25, 0.25), z + rnd.uniform(-0.15, 0.15), r, rnd)
            x += r * rnd.uniform(1.1, 1.5)
        z += 0.85
    mb.box(((x0 + x1) / 2, depth / 2 + 0.9 + lean * height * 0.5, height + 0.05), (width, depth - lean * height * 0.6, 0.3), "grass")
    for _ in range(int(width * 1.2)):
        blob(mb, rnd.uniform(x0 + 0.3, x1 - 0.3), 0.9 + lean * height + rnd.uniform(0, 0.6), height + 0.2, rnd.uniform(0.25, 0.45), "grass_dark",
             (1, 1, 0.5))


def merged(*poses):
    def pose(t):
        turns, moves = {}, {}
        for p in poses:
            a, b = p(t)
            turns.update(a)
            moves.update(b)
        return turns, moves
    return pose


# --- Water --------------------------------------------------------------------------------------


def waterfall(name, height):
    def build():
        mb = kit.begin()
        rnd = random.Random(int(height * 10))
        lean = 0.12
        rock_face(mb, -4.0, 4.0, height, rnd, lean, gap=(-1.3, 1.3))
        top_y, bot_y = 0.42, 0.42   # The water falls straight down a notch in the cliff.
        mb.box((0, 1.65, height / 2), (2.4, 2.4, height), "stone_dark")
        mb.box((0, top_y + 1.9, height + 0.12), (2.0, 3.8, 0.25), "water")
        solid(mb, [(-0.95, top_y, height + 0.2), (0.95, top_y, height + 0.2), (1.15, bot_y, 0.1), (-1.15, bot_y, 0.1)], (0, -0.14, 0), "water")
        solid(mb, [(-0.5, top_y - 0.14, height + 0.2), (0.5, top_y - 0.14, height + 0.2), (0.65, bot_y - 0.14, 0.1), (-0.65, bot_y - 0.14, 0.1)],
              (0, -0.06, 0), "water_light")
        spacing = 1.4
        slope = (bot_y - top_y) / (height + 0.1)
        bones = []
        for b, offset in (("fall_a", 0.0), ("fall_b", 0.7)):
            z = height + 0.1 - offset
            k = 0
            while z > 0.5:
                for xx in ((-0.75, 0.1, 0.8) if k % 2 == 0 else (-0.3, 0.45, -0.95)):
                    yy = top_y + slope * (height + 0.2 - z) - 0.23
                    mb.box((xx + rnd.uniform(-0.06, 0.06), yy, z), (0.14, 0.05, rnd.uniform(0.35, 0.6)), "foam", {b: 1.0})
                z -= spacing
                k += 1
            bones.append((b, (0, top_y, height), (0, top_y, height - 1.0), None))
        mb.cylinder((0, -2.4, 0), (0, -2.4, 0.1), 3.4, 3.3, "water", segments=10)
        mb.cylinder((0, -2.2, 0.1), (0, -2.2, 0.13), 2.2, 2.2, "water_light", segments=10)
        for i in range(12):
            a = TAU * i / 12 + rnd.uniform(-0.1, 0.1)
            if math.sin(a) > 0.75:
                continue
            rock(mb, math.cos(a) * 3.4, -2.4 + math.sin(a) * 3.4, 0.12, rnd.uniform(0.3, 0.55), rnd)
        for xx, yy, r in ((-0.7, 0.0, 0.5), (0.0, -0.25, 0.6), (0.75, 0.0, 0.5), (-0.3, -0.7, 0.35), (0.45, -0.7, 0.35)):
            blob(mb, xx, yy, 0.25, r, "foam", (1, 1, 0.75), {"foam": 1.0})
        for xx in (-1.0, -0.4, 0.3, 0.9):
            blob(mb, xx, top_y - 0.05, height + 0.3, 0.3, "foam", (1, 1, 0.6))
        bones.append(("foam", (0, 0, 0.2), (0, 0, 0.7), None))

        def flow(t):
            d = (0, slope * spacing * t, -spacing * t)
            return {}, {"fall_a": d, "fall_b": d, "foam": (0, 0, 0.07 * math.sin(TAU * 2 * t))}

        kit.save(mb, FAMILY, name, COLORS, mech=kit.Mech(bones).clip("flow", 1.0, flow))
    return build


def cliff(name, corner):
    def build():
        mb = kit.begin()
        rnd = random.Random(5 if corner else 4)
        rock_face(mb, -3.0, 3.0, 4.0, rnd)
        if corner:
            start = _shapes.mark(mb)
            rock_face(mb, -3.0, 3.0, 4.0, random.Random(6))
            _shapes.moved(mb, start, (-3.6, 3.6), -90)
        for _ in range(6):
            rock(mb, rnd.uniform(-2.8, 2.8), rnd.uniform(-0.8, 0.1), 0.15, rnd.uniform(0.2, 0.45), rnd)
        kit.save(mb, FAMILY, name, COLORS)
    return build


def hot_spring():
    mb = kit.begin()
    rnd = random.Random(8)
    mb.cylinder((0, 0, 0), (0, 0, 0.12), 2.3, 2.1, "stone_light", segments=10)
    mb.cylinder((0, 0, 0.1), (0, 0, 0.16), 1.8, 1.8, "water_light", segments=10)
    mb.cylinder((0.2, 0.1, 0.14), (0.2, 0.1, 0.18), 1.0, 1.0, "water", segments=8)
    for i in range(11):
        a = TAU * i / 11 + rnd.uniform(-0.1, 0.1)
        rock(mb, math.cos(a) * 2.1, math.sin(a) * 2.1, 0.2, rnd.uniform(0.3, 0.5), rnd, rnd.choice(("stone_light", "stone", "sulfur")))
    bones = []
    for i in range(4):
        b = "steam%d" % i
        a = TAU * i / 4 + 0.5
        x, y = math.cos(a) * 0.8, math.sin(a) * 0.8
        for k in range(3):
            blob(mb, x + 0.1 * k, y, 0.5 + 0.55 * k, 0.3 - 0.07 * k, "steam", (1, 1, 0.8), {b: 1.0})
        bones.append((b, (x, y, 0.3), (x, y, 1.0), None))

    def steam(t):
        moves, turns = {}, {}
        for i in range(4):
            s = (t + i / 4) % 1.0
            moves["steam%d" % i] = (0.15 * math.sin(TAU * s), 0, 1.1 * s)
            turns["steam%d" % i] = [(kit.Z, 120 * s)]
        return turns, moves

    kit.save(mb, FAMILY, "nature_hot_spring", COLORS, mech=kit.Mech(bones).clip("steam", 4.0, steam))


def geyser():
    mb = kit.begin()
    rnd = random.Random(9)
    for r, z, mat in ((2.0, 0.0, "stone"), (1.5, 0.15, "stone_light"), (1.0, 0.3, "sulfur"), (0.6, 0.42, "stone_light")):
        mb.cylinder((0, 0, z), (0, 0, z + 0.18), r, r * 0.85, mat, segments=9)
    mb.cylinder((0, 0, 0.55), (0, 0, 0.62), 0.35, 0.35, "water_light", segments=8)
    for i in range(7):
        a = TAU * i / 7
        rock(mb, math.cos(a) * 1.9, math.sin(a) * 1.9, 0.15, rnd.uniform(0.2, 0.4), rnd)
    w = {"jet": 1.0}
    mb.cylinder((0, 0, 0.6), (0, 0, 4.4), 0.3, 0.22, "water_light", w, segments=7)
    for k in range(5):
        blob(mb, rnd.uniform(-0.2, 0.2), rnd.uniform(-0.2, 0.2), 4.4 + 0.25 * k, 0.4 - 0.04 * k, "foam", (1, 1, 0.8), w)
    for i in range(6):
        a = TAU * i / 6
        blob(mb, math.cos(a) * 0.5, math.sin(a) * 0.5, 4.1, 0.2, "foam", (1, 1, 0.7), w)

    def erupt(t):
        if t < 0.15:
            up = 0.0
        elif t < 0.3:
            up = 5.0 * kit.smooth((t - 0.15) / 0.15)
        elif t < 0.6:
            up = 5.0 + 0.3 * math.sin(TAU * (t - 0.3) / 0.3 * 3)
        else:
            up = 5.0 * (1 - kit.smooth((t - 0.6) / 0.25)) if t < 0.85 else 0.0
        return {"jet": [(kit.Z, 360 * t)]}, {"jet": (0, 0, up - 5.2)}

    kit.save(mb, FAMILY, "nature_geyser", COLORS, mech=kit.Mech([("jet", (0, 0, 0), (0, 0, 1), None)]).clip("erupt", 6.0, erupt))


def lava_vent():
    mb = kit.begin()
    rnd = random.Random(10)
    for i in range(9):
        a = TAU * i / 9
        r = rnd.uniform(1.2, 1.5)
        mb.cylinder((math.cos(a) * r, math.sin(a) * r, 0), (math.cos(a) * r * 0.55, math.sin(a) * r * 0.55, rnd.uniform(0.8, 1.3)), 0.75, 0.3, "lava_rock",
                    segments=5)
    mb.cylinder((0, 0, 0.3), (0, 0, 0.5), 0.8, 0.7, "glow_lava", segments=8)
    for a, length in ((0.3, 2.6), (2.4, 2.0), (4.3, 2.3)):   # Cracks that glow.
        beam(mb, (math.cos(a) * 1.2, math.sin(a) * 1.2, 0.04), (math.cos(a) * length, math.sin(a) * length, 0.03), 0.07, "glow_lava")
    for _ in range(8):
        a, d = rnd.uniform(0, TAU), rnd.uniform(1.8, 2.8)
        rock(mb, math.cos(a) * d, math.sin(a) * d, 0.1, rnd.uniform(0.2, 0.4), rnd, "lava_rock")
    bones = []
    for i in range(3):
        b = "smoke%d" % i
        for k in range(3):
            blob(mb, 0.15 * k * (1 if i % 2 else -1), 0.1 * i, 1.0 + 0.7 * k, 0.4 + 0.12 * k, "smoke", (1, 1, 0.8), {b: 1.0})
        bones.append((b, (0, 0, 0.6), (0, 0, 1.4), None))
    for i in range(5):
        a = TAU * i / 5
        mb.box((math.cos(a) * 0.3, math.sin(a) * 0.3, 0.7 + 0.2 * i), (0.07, 0.07, 0.07), "glow_lava", {"embers": 1.0}, rotation_z=a)
    bones.append(("embers", (0, 0, 0.6), (0, 0, 1.2), None))

    def smoke(t):
        turns, moves = {"embers": [(kit.Z, 360 * t)]}, {"embers": (0, 0, 1.2 * t)}
        for i in range(3):
            s = (t + i / 3) % 1.0
            moves["smoke%d" % i] = (0.4 * s, 0.1 * math.sin(TAU * s), 1.6 * s)
            turns["smoke%d" % i] = [(kit.Z, 90 * s)]
        return turns, moves

    kit.save(mb, FAMILY, "nature_lava_vent", COLORS, mech=kit.Mech(bones).clip("smoke", 4.0, smoke))


def mud_pit():
    mb = kit.begin()
    rnd = random.Random(11)
    mb.cylinder((0, 0, 0), (0, 0, 0.06), 2.4, 2.3, "soil_dark", segments=10)
    mb.cylinder((0, 0, 0.05), (0, 0, 0.1), 2.0, 2.0, "mud", segments=10)
    mb.cylinder((0.3, -0.2, 0.09), (0.3, -0.2, 0.12), 1.1, 1.1, "mud_light", segments=8)
    bones = []
    for i in range(5):
        b = "bubble%d" % i
        a, d = rnd.uniform(0, TAU), rnd.uniform(0.3, 1.5)
        x, y = math.cos(a) * d, math.sin(a) * d
        blob(mb, x, y, -0.05, rnd.uniform(0.16, 0.28), "mud_light", (1, 1, 0.7), {b: 1.0})
        bones.append((b, (x, y, 0), (x, y, 0.3), None))
    for i in range(9):
        a = TAU * i / 9 + rnd.uniform(-0.2, 0.2)
        blob(mb, math.cos(a) * 2.3, math.sin(a) * 2.3, 0.1, rnd.uniform(0.25, 0.4), "grass_dark", (1, 1, 0.6))
    for a in (0.6, 3.5):   # Reeds and a bone: something sank here.
        for k in range(3):
            mb.cylinder((math.cos(a) * 2.0 + 0.1 * k, math.sin(a) * 2.0, 0), (math.cos(a) * 2.0 + 0.14 * k, math.sin(a) * 2.0, 1.1 + 0.2 * k), 0.02, 0.015,
                        "reed", segments=4)
    beam(mb, (-0.8, 0.5, 0.05), (-0.3, 0.9, 0.35), 0.04, "bone")

    def bubble(t):
        moves = {}
        for i in range(5):
            s = (t * 2 + i / 5) % 1.0
            moves["bubble%d" % i] = (0, 0, 0.22 * math.sin(math.pi * min(1.0, s * 1.6)) if s < 0.625 else -0.1)
        return {}, moves

    kit.save(mb, FAMILY, "nature_mud_pit", COLORS, mech=kit.Mech(bones).clip("bubble", 4.0, bubble))


# --- Plants that sway ---------------------------------------------------------------------------


def blade(mb, x, y, h, lean, a, mat, w, width=0.09):
    """A grass blade: a thin triangle leaning toward angle a."""
    tx, ty = x + math.cos(a) * lean, y + math.sin(a) * lean
    px, py = -math.sin(a) * width / 2, math.cos(a) * width / 2
    solid(mb, [(x - px, y - py, 0), (x + px, y + py, 0), (tx, ty, h)], (math.cos(a) * 0.02, math.sin(a) * 0.02, 0), mat, w)


def sway_pose(bones, amp=6.0):
    def pose(t):
        return {b: [(kit.X, amp * math.sin(TAU * t + i * 0.9)), (kit.Y, amp * 0.6 * math.sin(TAU * 2 * t + i * 1.7))] for i, b in enumerate(bones)}, {}
    return pose


def grass(name, kind):
    def build():
        mb = kit.begin()
        rnd = random.Random({"tuft": 1, "tall": 2, "reeds": 3, "fern": 4}[kind])
        bones = []
        clumps = {"tuft": 5, "tall": 7, "reeds": 6, "fern": 3}[kind]
        for c in range(clumps):
            b = "sway%d" % (c % 3)
            cx, cy = (rnd.uniform(-0.7, 0.7), rnd.uniform(-0.7, 0.7)) if clumps > 1 else (0, 0)
            if kind in ("tuft", "tall"):
                h = 0.35 if kind == "tuft" else 0.95
                for _ in range(7):
                    a = rnd.uniform(0, TAU)
                    blade(mb, cx + rnd.uniform(-0.08, 0.08), cy + rnd.uniform(-0.08, 0.08), h * rnd.uniform(0.7, 1.2), h * rnd.uniform(0.15, 0.4), a,
                          rnd.choice(("grass", "grass_dark", "grass_light")), {b: 1.0}, 0.07 if kind == "tuft" else 0.06)
                if kind == "tall" and c % 2 == 0:
                    mb.cylinder((cx, cy, 0), (cx + 0.06, cy, h * 1.25), 0.012, 0.01, "grass_light", {b: 1.0}, segments=4)
                    blob(mb, cx + 0.065, cy, h * 1.3, 0.05, "hay", (1, 1, 2.0), {b: 1.0}, 5, 3)
            elif kind == "reeds":
                for _ in range(4):
                    x, y, h = cx + rnd.uniform(-0.15, 0.15), cy + rnd.uniform(-0.15, 0.15), rnd.uniform(1.3, 1.9)
                    mb.cylinder((x, y, 0), (x + 0.05, y, h), 0.018, 0.012, "reed", {b: 1.0}, segments=4)
                    mb.cylinder((x + 0.045, y, h * 0.8), (x + 0.05, y, h * 0.96), 0.04, 0.04, "reed_top", {b: 1.0}, segments=6)
                    blade(mb, x, y, h * 0.6, 0.3, rnd.uniform(0, TAU), "reed", {b: 1.0}, 0.05)
            else:
                for k in range(8):
                    a = TAU * k / 8 + rnd.uniform(-0.2, 0.2)
                    for s in range(3):   # A frond in three falling pieces.
                        r0, r1 = 0.22 * s, 0.22 * (s + 1)
                        z0, z1 = 0.35 * math.sin(s / 3 * 2.4) + 0.05, 0.35 * math.sin((s + 1) / 3 * 2.4) + 0.05
                        wd = 0.16 - 0.045 * s
                        px, py = -math.sin(a) * wd, math.cos(a) * wd
                        solid(mb, [(cx + math.cos(a) * r0 - px, cy + math.sin(a) * r0 - py, z0), (cx + math.cos(a) * r0 + px, cy + math.sin(a) * r0 + py, z0),
                                   (cx + math.cos(a) * r1 + px * 0.6, cy + math.sin(a) * r1 + py * 0.6, z1),
                                   (cx + math.cos(a) * r1 - px * 0.6, cy + math.sin(a) * r1 - py * 0.6, z1)], (0, 0, 0.015),
                              "fern" if k % 2 else "grass_dark", {b: 1.0})
            if b not in [n for n, *_r in bones]:
                bones.append((b, (0, 0, 0), (0, 0, 0.5), None))
        if kind == "reeds":
            mb.cylinder((0, 0, 0), (0, 0, 0.04), 1.1, 1.1, "water", segments=9)
        names = [n for n, *_r in bones]
        kit.save(mb, FAMILY, name, COLORS, mech=kit.Mech(bones).clip("sway", 4.0, sway_pose(names, 4.0 if kind == "fern" else 7.0)))
    return build


# --- Insects ------------------------------------------------------------------------------------


def flyer(mb, prefix, at, body, wing, size=1.0, wings=2, glow=False):
    """A small flying thing at `at` with its bones: an orbit bone at the
    center of its circle, the body and the wings."""
    x, y, z = at
    orbit, bone = prefix + "orbit", prefix + "body"
    w = {bone: 1.0}
    s = size
    if glow:
        blob(mb, x, y, z, 0.05 * s, body, (1, 1, 1), w, 5, 3)
        return [(orbit, (0, 0, z), (0, 0, z + 0.3), None), (bone, at, (x, y - 0.1, z), orbit)], []
    mb.cylinder((x, y - 0.06 * s, z), (x, y + 0.07 * s, z), 0.012 * s, 0.008 * s, body, w, segments=4)
    blob(mb, x, y - 0.07 * s, z, 0.018 * s, "eye", (1, 1, 1), w, 4, 3)
    bones = [(orbit, (0, 0, z), (0, 0, z + 0.3), None), (bone, at, (x, y - 0.1, z), orbit)]
    flaps = []
    for side in (-1, 1):
        for k in range(wings // 2):
            wb = "%swing_%s%d" % (prefix, "l" if side < 0 else "r", k)
            yy = y - 0.03 * s + 0.07 * s * k
            ring = [(x, yy - 0.04 * s, z), (x + side * 0.11 * s, yy - 0.07 * s, z), (x + side * 0.13 * s, yy + 0.02 * s, z), (x, yy + 0.04 * s, z)]
            solid(mb, ring, (0, 0, 0.004), wing, {wb: 1.0})
            bones.append((wb, (x, yy, z), (x + side * 0.1, yy, z), bone))
            flaps.append((wb, side))
    return bones, flaps


def insects(name, kind):
    def build():
        mb = kit.begin()
        rnd = random.Random({"butterflies": 1, "fireflies": 2, "bees": 3, "dragonflies": 4}[kind])
        bones, parts = [], []
        if kind == "butterflies":
            for i in range(4):   # Flowers to fly over.
                x, y = rnd.uniform(-0.6, 0.6), rnd.uniform(-0.6, 0.6)
                mb.cylinder((x, y, 0), (x, y, 0.35), 0.012, 0.01, "grass_dark", segments=4)
                blob(mb, x, y, 0.37, 0.06, rnd.choice(("wing_white", "wing_orange", "bee")), (1, 1, 0.5), None, 5, 3)
            specs = [("b0_", 0.5, 0.7, "wing_orange", 1.0, 1), ("b1_", 0.35, 1.0, "wing_blue", 0.9, -1), ("b2_", 0.65, 1.3, "wing_white", 0.8, 1)]
            for prefix, radius, z, wing, size, turn in specs:
                b, flaps = flyer(mb, prefix, (radius, 0, z), "eye", wing, 1.3 * size, 2)
                bones += b
                parts.append((prefix, flaps, turn, 12, 55, 0.12))
        elif kind == "fireflies":
            for i in range(9):
                prefix = "f%d_" % i
                b, flaps = flyer(mb, prefix, (rnd.uniform(0.2, 0.9), 0, rnd.uniform(0.4, 1.6)), "glow_firefly", None, rnd.uniform(0.8, 1.3), glow=True)
                bones += b
                parts.append((prefix, [], 1 if i % 2 else -1, 0, 0, 0.18))
            for _ in range(5):
                blade(mb, rnd.uniform(-0.6, 0.6), rnd.uniform(-0.6, 0.6), 0.5, 0.15, rnd.uniform(0, TAU), "grass_dark", None)
        elif kind == "bees":
            log(mb, (-0.5, 0, 0.3), (0.5, 0, 0.3), 0.3)
            mb.cylinder((0.5, 0, 0.3), (0.52, 0, 0.3), 0.2, 0.2, "cave", segments=7)
            mb.cylinder((0.45, 0, 0.22), (0.56, 0, 0.2), 0.1, 0.08, "honey", segments=6)
            for i in range(6):
                prefix = "e%d_" % i
                b, flaps = flyer(mb, prefix, (rnd.uniform(0.25, 0.7), 0, rnd.uniform(0.5, 1.2)), "bee", "wing_clear", 0.8, 2)
                bones += b
                parts.append((prefix, flaps, 1 if i % 2 else -1, 30, 40, 0.06))
        else:
            mb.cylinder((0, 0, 0), (0, 0, 0.04), 1.2, 1.2, "water", segments=9)
            for _ in range(5):
                x, y, h = rnd.uniform(-0.8, 0.8), rnd.uniform(-0.8, 0.8), rnd.uniform(0.7, 1.2)
                mb.cylinder((x, y, 0), (x + 0.04, y, h), 0.016, 0.012, "reed", segments=4)
            for i in range(3):
                prefix = "d%d_" % i
                b, flaps = flyer(mb, prefix, (0.4 + 0.25 * i, 0, 0.6 + 0.3 * i), "dragonfly", "wing_clear", 2.2, 4)
                bones += b
                parts.append((prefix, flaps, 1 if i % 2 else -1, 30, 25, 0.05))

        def fly(t):
            turns, moves = {}, {}
            for i, (prefix, flaps, turn, beats, amp, bob) in enumerate(parts):
                laps = (i % 2) + 1
                turns[prefix + "orbit"] = [(kit.Z, 360.0 * laps * turn * t + 0.0)]
                moves[prefix + "body"] = (0, 0, bob * math.sin(TAU * (3 + i % 3) * t + i))
                turns[prefix + "body"] = [(kit.Z, 90.0 * turn)]
                for wb, side in flaps:
                    turns[wb] = [(kit.Y, -side * amp * (0.5 + 0.5 * math.sin(TAU * beats * t + i)))]
            return turns, moves

        kit.save(mb, FAMILY, name, COLORS, mech=kit.Mech(bones).clip("fly", 6.0, fly))
    return build


def anthill():
    mb = kit.begin()
    rnd = random.Random(14)
    for r, z in ((0.9, 0.0), (0.65, 0.25), (0.4, 0.5), (0.2, 0.72)):
        blob(mb, rnd.uniform(-0.04, 0.04), rnd.uniform(-0.04, 0.04), z, r, "soil" if z < 0.6 else "soil_dark", (1, 1, 0.55), None, 8, 4)
    mb.cylinder((0, 0, 0.82), (0, 0, 0.86), 0.06, 0.06, "cave", segments=6)
    for _ in range(12):
        a, d = rnd.uniform(0, TAU), rnd.uniform(0.9, 1.3)
        mb.box((math.cos(a) * d, math.sin(a) * d, 0.02), (0.05, 0.05, 0.04), "soil_dark")
    spacing, count = 0.25, 7
    for b, off in (("ants_a", 0.0), ("ants_b", spacing / 2)):   # Two files, going and coming.
        side = 1 if b == "ants_a" else -1
        for k in range(count):
            y = -0.9 - spacing * k - off
            mb.box((side * 0.05, y, 0.025), (0.03, 0.07, 0.03), "eye", {b: 1.0})
            if side < 0 and k % 3 == 0:
                mb.box((side * 0.05, y, 0.06), (0.05, 0.05, 0.03), "grass_light", {b: 1.0})
    blob(mb, 0, -2.9, 0.04, 0.25, "grass_light", (1, 1.4, 0.3))

    def march(t):
        return {}, {"ants_a": (0, spacing * t, 0), "ants_b": (0, -spacing * t, 0)}

    bones = [("ants_a", (0, -1, 0), (0, -1.3, 0), None), ("ants_b", (0, -1, 0), (0, -1.3, 0), None)]
    kit.save(mb, FAMILY, "nature_anthill", COLORS, mech=kit.Mech(bones).clip("march", 1.5, march))


def bee_tree():
    mb = kit.begin()
    rnd = random.Random(15)
    mb.cylinder((0, 0, 0), (0, 0, 1.2), 0.75, 0.5, "bark", segments=8)
    mb.cylinder((0, 0, 1.2), (0.1, 0, 3.2), 0.5, 0.4, "bark", segments=8)
    mb.cylinder((0.1, 0, 3.2), (0.1, 0, 3.4), 0.4, 0.15, "pole_dark", segments=7)
    for a, z0, length in ((0.6, 2.6, 1.4), (2.6, 2.2, 1.1), (4.4, 2.9, 0.9)):
        beam(mb, (0.05, 0, z0), (math.cos(a) * length, math.sin(a) * length, z0 + 0.7), 0.09, "bark")
    for i in range(5):
        a = TAU * i / 5
        beam(mb, (math.cos(a) * 0.5, math.sin(a) * 0.5, 0.2), (math.cos(a) * 1.2, math.sin(a) * 1.2, 0.0), 0.12, "bark")
    solid(mb, [(-0.2, -0.47, 1.5), (0.2, -0.47, 1.5), (0.26, -0.45, 2.0), (0, -0.44, 2.3), (-0.26, -0.45, 2.0)], (0, -0.03, 0), "cave")
    for k in range(4):   # Combs inside the hollow.
        mb.box((-0.12 + 0.08 * k, -0.5, 1.9 - 0.04 * k), (0.05, 0.04, 0.3 + 0.03 * k), "honey")
    mb.cylinder((0, -0.52, 1.5), (0, -0.5, 1.2), 0.03, 0.0, "honey", segments=5)
    bones, parts = [], []
    for i in range(7):
        prefix = "e%d_" % i
        b, flaps = flyer(mb, prefix, (rnd.uniform(0.3, 0.9), 0, rnd.uniform(1.4, 2.4)), "bee", "wing_clear", 0.9, 2)
        b[0] = (b[0][0], (0, -0.7, b[0][2][2] - 0.3), (0, -0.7, b[0][2][2]), None)
        b[1] = (b[1][0], b[1][1], b[1][2], b[1][3])
        bones += b
        parts.append((prefix, flaps, 1 if i % 2 else -1))

    def buzz(t):
        turns, moves = {}, {}
        for i, (prefix, flaps, turn) in enumerate(parts):
            turns[prefix + "orbit"] = [(kit.Z, 360.0 * ((i % 3) + 1) * turn * t)]
            moves[prefix + "body"] = (0, 0, 0.08 * math.sin(TAU * (2 + i % 3) * t + i))
            turns[prefix + "body"] = [(kit.Z, 90.0 * turn)]
            for wb, side in flaps:
                turns[wb] = [(kit.Y, -side * 40 * (0.5 + 0.5 * math.sin(TAU * 36 * t + i)))]
        return turns, moves

    kit.save(mb, FAMILY, "nature_bee_tree", COLORS, mech=kit.Mech(bones).clip("buzz", 6.0, buzz))


# --- Outcrops, dens, remains ---------------------------------------------------------------------


def deposit(name, kind):
    def build():
        mb = kit.begin()
        rnd = random.Random({"gold": 1, "coal": 2, "clay": 3, "crystal": 4, "sulfur": 5}[kind])
        if kind == "clay":
            mb.box((0, 0.8, 0.6), (4.0, 1.6, 1.2), "clay")
            mb.box((0, 0.9, 1.25), (4.0, 1.4, 0.12), "grass")
            for k in range(4):
                mb.box((0, -0.1 - 0.35 * k, 0.45 - 0.14 * k), (3.6 - 0.3 * k, 0.4, 0.3), "clay_dark" if k % 2 else "clay")
            for _ in range(6):
                blob(mb, rnd.uniform(-1.6, 1.6), rnd.uniform(-1.6, -0.9), 0.08, rnd.uniform(0.15, 0.3), "clay", (1, 1, 0.6))
            mb.cylinder((1.2, -0.9, 0), (1.5, -0.4, 1.0), 0.02, 0.02, "pole", segments=5)
            mb.box((1.18, -0.93, 0.1), (0.2, 0.04, 0.26), "steel")
            mb.cylinder((-1.2, -1.2, 0), (-1.2, -1.2, 0.3), 0.2, 0.25, "plank", segments=8)
            mb.cylinder((-1.2, -1.2, 0.27), (-1.2, -1.2, 0.31), 0.22, 0.22, "clay", segments=8)
        else:
            base = {"gold": "stone", "coal": "stone_dark", "crystal": "stone_dark", "sulfur": "stone_light"}[kind]
            for _ in range(9):
                a, d = rnd.uniform(0, TAU), rnd.uniform(0, 1.1)
                rock(mb, math.cos(a) * d, math.sin(a) * d, rnd.uniform(0.3, 0.7), rnd.uniform(0.6, 1.0), rnd, base)
            if kind == "gold":
                for _ in range(8):   # Veins and nuggets.
                    a, z = rnd.uniform(0, TAU), rnd.uniform(0.3, 1.1)
                    r = 1.75 - z * 0.45
                    beam(mb, (math.cos(a) * r, math.sin(a) * r, z), (math.cos(a + 0.5) * r, math.sin(a + 0.5) * r, z + rnd.uniform(-0.3, 0.3)), 0.1, "gold")
                for _ in range(5):
                    a, d = rnd.uniform(0, TAU), rnd.uniform(1.3, 1.7)
                    blob(mb, math.cos(a) * d * 1.2, math.sin(a) * d * 1.2, 0.07, 0.13, "gold")
            elif kind == "coal":
                for k in range(4):
                    mb.box((rnd.uniform(-0.2, 0.2), -0.75 - 0.05 * k, 0.25 + 0.28 * k), (1.9 - 0.25 * k, 0.5, 0.2), "coal" if k % 2 == 0 else "coal_shine",
                           rotation_z=rnd.uniform(-0.1, 0.1))
                for _ in range(10):
                    a, d = rnd.uniform(3.3, 6.0), rnd.uniform(1.1, 1.8)
                    mb.box((math.cos(a) * d, math.sin(a) * d, 0.07), (rnd.uniform(0.12, 0.25),) * 2 + (0.14,), "coal", rotation_z=a)
            elif kind == "crystal":
                for i in range(9):
                    a, d = rnd.uniform(0, TAU), rnd.uniform(0.2, 1.1)
                    h = rnd.uniform(0.8, 2.0)
                    tip = (math.cos(a) * (d + 0.4), math.sin(a) * (d + 0.4), 0.5 + h)
                    mat = "glow_crystal" if i % 3 else "glow_crystal_violet"
                    mid = (math.cos(a) * (d + 0.3), math.sin(a) * (d + 0.3), 0.5 + h * 0.75)
                    mb.cylinder((math.cos(a) * d, math.sin(a) * d, 0.4), mid, 0.16, 0.2, mat, segments=5)
                    mb.cylinder(mid, tip, 0.2, 0.0, mat, segments=5)
            else:
                for _ in range(10):
                    a, d = rnd.uniform(0, TAU), rnd.uniform(0.4, 1.4)
                    blob(mb, math.cos(a) * d, math.sin(a) * d, rnd.uniform(0.2, 1.0), rnd.uniform(0.15, 0.3), "sulfur", (1, 1, 0.6))
        kit.save(mb, FAMILY, name, COLORS)
    return build


def den(name, kind):
    def build():
        mb = kit.begin()
        rnd = random.Random({"wolf": 1, "bear": 2, "rabbit": 3}[kind])
        if kind == "rabbit":
            for x, y, r in ((0, 0.3, 1.3), (-1.1, -0.2, 0.8), (1.0, -0.3, 0.9)):
                blob(mb, x, y, 0, r, "grass", (1, 1, 0.45), None, 8, 4)
            for x, y, a in ((0.0, -0.75, 0), (-1.15, -0.9, -20), (1.1, -1.05, 15)):
                mb.cylinder((x, y, 0.22), (x + math.sin(math.radians(a)) * 0.1, y - 0.1, 0.2), 0.22, 0.2, "soil_dark", segments=7)
                mb.cylinder((x, y - 0.11, 0.21), (x, y - 0.12, 0.21), 0.16, 0.16, "cave", segments=7)
                blob(mb, x, y - 0.4, 0.02, 0.3, "soil", (1, 1.3, 0.3))
            for x, y in ((0.5, -1.5), (0.6, -1.4)):
                mb.cylinder((x, y, 0.03), (x + 0.25, y - 0.05, 0.03), 0.05, 0.01, "carrot", segments=5)
        else:
            big = kind == "bear"
            s = 1.5 if big else 1.0
            for _ in range(12):
                a, d = rnd.uniform(0.2, 2.94), rnd.uniform(0.9, 1.7) * s
                rock(mb, math.cos(a) * d, 0.6 + math.sin(a) * d * 0.7, rnd.uniform(0.2, 1.0) * s, rnd.uniform(0.7, 1.1) * s, rnd)
            blob(mb, 0, 1.3 * s, 0.5 * s, 2.0 * s, "grass", (1.2, 0.9, 0.55), None, 8, 4)
            for sx in (-1, 1):
                rock(mb, sx * 0.95 * s, -0.2, 0.5 * s, 0.7 * s, rnd, "stone_dark")
            rock(mb, 0, -0.1, 1.55 * s, 0.9 * s, rnd, "stone")
            solid(mb, [(-0.6 * s, -0.42, 0), (0.6 * s, -0.42, 0), (0.7 * s, -0.4, 0.7 * s), (0.3 * s, -0.38, 1.15 * s), (-0.3 * s, -0.38, 1.15 * s),
                       (-0.7 * s, -0.4, 0.7 * s)], (0, 0.5, 0), "cave")
            for _ in range(5 if not big else 8):   # What is left of its meals.
                a, d = rnd.uniform(3.6, 5.8), rnd.uniform(1.2, 2.4) * s
                x, y = math.cos(a) * d, math.sin(a) * d
                beam(mb, (x, y, 0.04), (x + rnd.uniform(-0.4, 0.4), y + rnd.uniform(-0.3, 0.3), 0.04), 0.035, "bone")
            if big:
                log(mb, (2.2, -1.2, 0.2), (3.2, 0.4, 0.2), 0.2)
                for k in range(4):   # Claw marks on the log.
                    mb.box((2.55 + 0.1 * k, -0.6 + 0.16 * k, 0.4), (0.03, 0.3, 0.02), "log_end", rotation_z=0.55)
            else:
                blob(mb, -1.6, -1.3, 0.05, 0.14, "bone", (1, 1.2, 0.9))
        kit.save(mb, FAMILY, name, COLORS)
    return build


def stump(name, kind):
    def build():
        mb = kit.begin()
        rnd = random.Random({"mushrooms": 1, "hollow_log": 2, "sprout": 3}[kind])
        if kind == "hollow_log":
            for i in range(8):
                a0, a1 = TAU * i / 8, TAU * (i + 1) / 8
                r = 0.55
                solid(mb, [(-1.4, math.cos(a0) * r, 0.5 + math.sin(a0) * r), (1.4, math.cos(a0) * r, 0.5 + math.sin(a0) * r),
                           (1.4, math.cos(a1) * r, 0.5 + math.sin(a1) * r), (-1.4, math.cos(a1) * r, 0.5 + math.sin(a1) * r)],
                      (0, -math.cos((a0 + a1) / 2) * 0.1, -math.sin((a0 + a1) / 2) * 0.1), "bark" if i % 3 else "moss")
            for sx in (-1, 1):
                mb.cylinder((sx * 1.3, 0, 0.5), (sx * 1.32, 0, 0.5), 0.46, 0.46, "cave", segments=8)
            for _ in range(5):
                blob(mb, rnd.uniform(-1.2, 1.2), rnd.uniform(-0.2, 0.2), 1.0, rnd.uniform(0.12, 0.25), "moss", (1.5, 1, 0.4))
        else:
            mb.cylinder((0, 0, 0), (0, 0, 0.55), 0.6, 0.45, "bark", segments=8)
            mb.cylinder((0, 0, 0.54), (0, 0, 0.57), 0.4, 0.4, "log_end", segments=8)
            mb.cylinder((0, 0, 0.565), (0, 0, 0.58), 0.2, 0.2, "plank", segments=8)
            for i in range(5):
                a = TAU * i / 5 + 0.3
                beam(mb, (math.cos(a) * 0.4, math.sin(a) * 0.4, 0.15), (math.cos(a) * 1.0, math.sin(a) * 1.0, 0.0), 0.1, "bark")
        if kind == "mushrooms":
            for _ in range(7):
                a, d = rnd.uniform(0, TAU), rnd.uniform(0.5, 0.95)
                x, y, h = math.cos(a) * d, math.sin(a) * d, rnd.uniform(0.12, 0.3)
                mb.cylinder((x, y, 0), (x, y, h), 0.035, 0.03, "mushroom_stem", segments=5)
                mb.cylinder((x, y, h), (x, y, h + 0.1), 0.12, 0.02, "mushroom_cap", segments=6)
            for k in range(3):   # Shelf fungus on the bark.
                a = 1.0 + 0.5 * k
                solid(mb, [(math.cos(a - 0.3) * 0.5, math.sin(a - 0.3) * 0.5, 0.2 + 0.12 * k), (math.cos(a + 0.3) * 0.5, math.sin(a + 0.3) * 0.5, 0.2 + 0.12 * k),
                           (math.cos(a) * 0.78, math.sin(a) * 0.78, 0.22 + 0.12 * k)], (0, 0, 0.04), "log_end")
        elif kind == "sprout":
            mb.cylinder((0.15, 0.1, 0.55), (0.2, 0.12, 1.3), 0.03, 0.02, "grass_dark", segments=5)
            for k in range(4):
                a = TAU * k / 4
                solid(mb, [(0.2, 0.12, 1.0 + 0.1 * k), (0.2 + math.cos(a) * 0.25, 0.12 + math.sin(a) * 0.25, 1.12 + 0.1 * k),
                           (0.2 + math.cos(a + 0.5) * 0.14, 0.12 + math.sin(a + 0.5) * 0.14, 1.02 + 0.1 * k)], (0, 0, 0.012), "grass_light")
            mb.cylinder((0.7, -0.5, 0.0), (0.2, -0.1, 0.62), 0.02, 0.02, "pole", segments=5)      # An axe left in it.
            mb.box((0.2, -0.1, 0.63), (0.05, 0.22, 0.14), "steel", rotation_z=0.67)
        kit.save(mb, FAMILY, name, COLORS)
    return build


def nest():
    mb = kit.begin()
    rnd = random.Random(20)
    rock(mb, 0, 0, 0.3, 0.75, rnd, "stone")
    rock(mb, 0.6, 0.3, 0.2, 0.45, rnd, "stone_dark")
    for i in range(12):
        a0, a1 = TAU * i / 12, TAU * (i + 1.6) / 12
        beam(mb, (math.cos(a0) * 0.32, math.sin(a0) * 0.32, 0.72 + 0.03 * (i % 3)), (math.cos(a1) * 0.36, math.sin(a1) * 0.36, 0.76 + 0.03 * ((i + 1) % 3)), 0.035,
             "nest" if i % 2 else "hay_dark")
    mb.cylinder((0, 0, 0.66), (0, 0, 0.72), 0.28, 0.32, "nest", segments=8)
    for x, y in ((-0.08, 0.02), (0.08, 0.06), (0.0, -0.1)):
        blob(mb, x, y, 0.78, 0.075, "egg", (1, 1, 1.3), None, 6, 4)
    solid(mb, [(0.3, -0.2, 0.74), (0.5, -0.3, 0.76), (0.42, -0.14, 0.75)], (0, 0, 0.01), "wing_white")
    kit.save(mb, FAMILY, "nature_nest", COLORS)


def beach(name, kind):
    def build():
        mb = kit.begin()
        rnd = random.Random({"driftwood": 1, "shells": 2, "tide_pool": 3}[kind])
        blob(mb, 0, 0, -0.02, 1.25, "sand", (1.15, 1.0, 0.08), None, 9, 4)
        if kind == "driftwood":
            log(mb, (-1.3, 0.2, 0.16), (1.1, -0.3, 0.2), 0.16, mat="bark_dead" if "bark_dead" in COLORS else "plank_light")
            beam(mb, (0.2, -0.1, 0.25), (0.7, 0.5, 0.75), 0.06, "plank_light")
            beam(mb, (-0.5, 0.05, 0.25), (-0.8, -0.5, 0.6), 0.05, "plank_light")
            for _ in range(3):
                blob(mb, rnd.uniform(-1, 1), rnd.uniform(-0.8, 0.8), 0.04, 0.08, "shell", (1, 1.3, 0.5), None, 5, 3)
        elif kind == "shells":
            for _ in range(9):
                x, y = rnd.uniform(-1.0, 1.0), rnd.uniform(-0.8, 0.8)
                mb.cylinder((x, y, 0.03), (x + 0.03, y + 0.2, 0.08), 0.14, 0.0, rnd.choice(("shell", "coral", "wing_white")), segments=6)
            for x, y in ((0.3, -0.2), (-0.7, 0.4)):
                for k in range(5):
                    a = TAU * k / 5
                    solid(mb, [(x, y, 0.04), (x + math.cos(a - 0.35) * 0.07, y + math.sin(a - 0.35) * 0.07, 0.04), (x + math.cos(a) * 0.24, y + math.sin(a) * 0.24, 0.04),
                               (x + math.cos(a + 0.35) * 0.07, y + math.sin(a + 0.35) * 0.07, 0.04)], (0, 0, 0.03), "starfish")
            for _ in range(3):
                x, y = rnd.uniform(-1, 1), rnd.uniform(-0.8, 0.8)
                for k in range(3):
                    beam(mb, (x, y, 0.02), (x + rnd.uniform(-0.15, 0.15), y + rnd.uniform(-0.15, 0.15), 0.3 + 0.1 * k), 0.035, "coral")
        else:
            mb.cylinder((0, 0, 0.04), (0, 0, 0.08), 0.9, 0.9, "water_light", segments=9)
            for i in range(9):
                a = TAU * i / 9
                rock(mb, math.cos(a) * 1.0, math.sin(a) * 1.0, 0.1, rnd.uniform(0.2, 0.35), rnd, "stone_dark")
            for k in range(5):
                a = TAU * k / 5
                solid(mb, [(0.2, 0.1, 0.085), (0.2 + math.cos(a - 0.35) * 0.06, 0.1 + math.sin(a - 0.35) * 0.06, 0.085), (0.2 + math.cos(a) * 0.2, 0.1 + math.sin(a) * 0.2, 0.085),
                           (0.2 + math.cos(a + 0.35) * 0.06, 0.1 + math.sin(a + 0.35) * 0.06, 0.085)], (0, 0, 0.02), "starfish")
            for x, y in ((-0.4, 0.3), (-0.2, -0.4), (0.5, -0.3)):
                blob(mb, x, y, 0.1, 0.08, "coral", (1, 1, 0.7), None, 5, 3)
        kit.save(mb, FAMILY, name, COLORS)
    return build


def winter(name, kind):
    def build():
        mb = kit.begin()
        rnd = random.Random({"drift": 1, "floe": 2, "snowman": 3}[kind])
        if kind == "drift":
            for x, y, r in ((0, 0, 1.4), (1.1, 0.4, 0.9), (-1.0, -0.3, 1.0), (0.3, -0.9, 0.7)):
                blob(mb, x, y, 0, r, "snow" if r > 0.8 else "snow_shade", (1.2, 1, 0.4), None, 8, 4)
            rock(mb, -0.3, 0.6, 0.35, 0.5, rnd, "stone_dark")
            blob(mb, -0.3, 0.6, 0.62, 0.4, "snow", (1.1, 1.1, 0.35))
        elif kind == "floe":
            pts = [(1.8, 0.2), (1.2, 1.3), (-0.3, 1.6), (-1.6, 0.8), (-1.9, -0.5), (-0.6, -1.4), (1.0, -1.2)]
            solid(mb, [(x, y, -0.35) for x, y in pts], (0, 0, 0.5), "ice")
            solid(mb, [(x * 0.9, y * 0.9, 0.15) for x, y in pts], (0, 0, 0.1), "snow")
            for x, y, h in ((0.6, 0.3, 0.9), (0.2, 0.6, 0.5)):
                mb.cylinder((x, y, 0.2), (x + 0.1, y, 0.2 + h), 0.35, 0.0, "ice", segments=5)
        else:
            for z, r in ((0.45, 0.5), (1.1, 0.36), (1.6, 0.25)):
                blob(mb, 0, 0, z, r, "snow", (1, 1, 0.95), None, 8, 6)
            mb.cylinder((0, -0.24, 1.6), (0, -0.48, 1.58), 0.045, 0.0, "carrot", segments=5)
            for sx in (-1, 1):
                mb.box((sx * 0.09, -0.22, 1.68), (0.04, 0.03, 0.04), "eye")
                beam(mb, (sx * 0.3, 0, 1.15), (sx * 0.8, -0.1, 1.45), 0.02, "pole_dark")
            for k in range(3):
                mb.box((0, -0.35 + 0.015 * k, 1.0 + 0.12 * k), (0.05, 0.03, 0.05), "eye")
            mb.cylinder((0, 0, 1.8), (0, 0, 1.84), 0.28, 0.28, "eye", segments=8)
            mb.cylinder((0, 0, 1.84), (0, 0, 2.1), 0.18, 0.17, "eye", segments=8)
            mb.cylinder((0, 0, 1.36), (0, 0, 1.44), 0.3, 0.28, "mushroom_cap", segments=8)
            mb.box((0.2, -0.22, 1.2), (0.1, 0.05, 0.35), "mushroom_cap")
            blob(mb, 0, 0, 0, 1.0, "snow_shade", (1.2, 1.2, 0.12), None, 8, 3)
        kit.save(mb, FAMILY, name, COLORS)
    return build


def meteorite():
    mb = kit.begin()
    rnd = random.Random(30)
    for i in range(12):   # The rim of the crater.
        a = TAU * i / 12
        blob(mb, math.cos(a) * 2.3, math.sin(a) * 2.3, 0.05, rnd.uniform(0.6, 0.85), "soil" if i % 2 else "soil_dark", (1, 1, 0.5))
    mb.cylinder((0, 0, 0.0), (0, 0, 0.06), 1.9, 1.7, "lava_rock", segments=10)
    for a, length in ((0.5, 1.6), (2.2, 1.4), (3.6, 1.7), (5.2, 1.3)):
        beam(mb, (math.cos(a) * 0.5, math.sin(a) * 0.5, 0.07), (math.cos(a) * length, math.sin(a) * length, 0.07), 0.05, "glow_meteor")
    w = {"core": 1.0}
    blob(mb, 0, 0, 0.5, 0.7, "lava_rock", (1, 0.9, 0.8), None, 6, 4)
    for a, z in ((0.2, 0.8), (1.9, 0.5), (3.4, 0.9), (4.8, 0.6), (5.7, 1.0)):
        mb.cylinder((math.cos(a) * 0.4, math.sin(a) * 0.4, z), (math.cos(a) * 0.75, math.sin(a) * 0.75, z + 0.3), 0.12, 0.0, "glow_meteor", segments=4)
    for i in range(4):
        a = TAU * i / 4
        mb.cylinder((math.cos(a) * 1.0, math.sin(a) * 1.0, 1.3), (math.cos(a) * 1.0, math.sin(a) * 1.0, 1.6), 0.07, 0.0, "glow_meteor", w, segments=4)
        mb.cylinder((math.cos(a) * 1.0, math.sin(a) * 1.0, 1.1), (math.cos(a) * 1.0, math.sin(a) * 1.0, 1.3), 0.0, 0.07, "glow_meteor", w, segments=4)
    for _ in range(6):
        a, d = rnd.uniform(0, TAU), rnd.uniform(2.6, 3.4)
        rock(mb, math.cos(a) * d, math.sin(a) * d, 0.08, rnd.uniform(0.12, 0.25), rnd, "lava_rock")
    pose = lambda t: ({"core": [(kit.Z, 180 * t)]}, {"core": (0, 0, 0.15 * math.sin(TAU * t))})   # noqa: E731
    kit.save(mb, FAMILY, "nature_meteorite", COLORS, mech=kit.Mech([("core", (0, 0, 1.0), (0, 0, 1.6), None)]).clip("hum", 4.0, pose))


COLORS["bark_dead"] = C(0x8A8278)

MODELS = {
    "nature_waterfall": waterfall("nature_waterfall", 6.0),
    "nature_waterfall_tall": waterfall("nature_waterfall_tall", 10.0),
    "nature_cliff": cliff("nature_cliff", False),
    "nature_cliff_corner": cliff("nature_cliff_corner", True),
    "nature_hot_spring": hot_spring,
    "nature_geyser": geyser,
    "nature_lava_vent": lava_vent,
    "nature_mud_pit": mud_pit,
    "nature_grass_tuft": grass("nature_grass_tuft", "tuft"),
    "nature_grass_tall": grass("nature_grass_tall", "tall"),
    "nature_grass_reeds": grass("nature_grass_reeds", "reeds"),
    "nature_grass_fern": grass("nature_grass_fern", "fern"),
    "nature_insects_butterflies": insects("nature_insects_butterflies", "butterflies"),
    "nature_insects_fireflies": insects("nature_insects_fireflies", "fireflies"),
    "nature_insects_bees": insects("nature_insects_bees", "bees"),
    "nature_insects_dragonflies": insects("nature_insects_dragonflies", "dragonflies"),
    "nature_anthill": anthill,
    "nature_bee_tree": bee_tree,
    "nature_deposit_gold": deposit("nature_deposit_gold", "gold"),
    "nature_deposit_coal": deposit("nature_deposit_coal", "coal"),
    "nature_deposit_clay": deposit("nature_deposit_clay", "clay"),
    "nature_deposit_crystal": deposit("nature_deposit_crystal", "crystal"),
    "nature_deposit_sulfur": deposit("nature_deposit_sulfur", "sulfur"),
    "nature_den_wolf": den("nature_den_wolf", "wolf"),
    "nature_den_bear": den("nature_den_bear", "bear"),
    "nature_den_rabbit": den("nature_den_rabbit", "rabbit"),
    "nature_stump_mushrooms": stump("nature_stump_mushrooms", "mushrooms"),
    "nature_stump_hollow_log": stump("nature_stump_hollow_log", "hollow_log"),
    "nature_stump_sprout": stump("nature_stump_sprout", "sprout"),
    "nature_nest": nest,
    "nature_beach_driftwood": beach("nature_beach_driftwood", "driftwood"),
    "nature_beach_shells": beach("nature_beach_shells", "shells"),
    "nature_beach_tide_pool": beach("nature_beach_tide_pool", "tide_pool"),
    "nature_winter_drift": winter("nature_winter_drift", "drift"),
    "nature_winter_floe": winter("nature_winter_floe", "floe"),
    "nature_winter_snowman": winter("nature_winter_snowman", "snowman"),
    "nature_meteorite": meteorite,
}

kit.run(MODELS, FAMILY)
