"""Biome proposals: what tells one biome from another on the ground (the
game's eleven biomes share rocks and bushes today), and the landmarks of
five biomes the game does not have: swamp, desert, tundra, volcanic and
jungle. See ../LEEME.md.

    blender --background --factory-startup --python art/blender/proposals/biomes/build.py -- [ids]
"""

import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import _kit as kit  # noqa: E402
import _shapes  # noqa: E402
import common  # noqa: E402
from _shapes import TAU, beam, log, merged, rock, solid  # noqa: E402

FAMILY = "biomes"
C = common.rgb
COLORS = {
    **_shapes.COLORS,
    "grass": C(0x6A9440), "grass_dark": C(0x4F7A34), "grass_dry": C(0xC8B060), "grass_gold": C(0xD8B850), "moss": C(0x5E8A3A), "lichen": C(0xB8C8A0),
    "leaf": C(0x4E7A34), "leaf_dark": C(0x3A5E28), "leaf_olive": C(0x8A9A6A), "leaf_jungle": C(0x2E8A3A), "leaf_light": C(0x7AB84A),
    "soil": C(0x6A4A30), "soil_dark": C(0x4A3422), "mud": C(0x5A4632), "sand": C(0xE0CFA0), "sand_dark": C(0xC8B480), "sand_red": C(0xC88A5A),
    "snow": C(0xF2F6FA), "snow_shade": C(0xD4E0EC), "ice": C(0xBFE4F0), "ice_deep": C(0x8AC4E0), "water": C(0x4A8FC0), "water_bog": C(0x5A7A4A),
    "white_flower": C(0xF4F0E4), "pink": C(0xF0A0C0), "purple": C(0x9A6AD0), "blue_berry": C(0x3A4A8A), "black_berry": C(0x3A2040), "red": C(0xC83A2A),
    "lavender": C(0x8C6CD0), "agave": C(0x6A9A8A), "termite": C(0xB07A4A), "thorn": C(0x8A8A5A), "coconut": C(0x6A4A2A), "egg": C(0xF0ECE0),
    "bark_dead": C(0x8A8278), "bark_olive": C(0x7A7060), "bark_mangrove": C(0x6A5A4A), "hang_moss": C(0x8AA07A), "bone": C(0xE4DCC8),
    "obsidian": C(0x1A1820), "obsidian_shine": C(0x4A4860), "basalt": C(0x3A3A40), "basalt_light": C(0x5A5A62), "glow_lava": C(0xFF6A20),
    "glow_shroom": C(0x70F0D0), "glow_stone": C(0xB0A0FF), "idol": C(0x8A8A7A), "idol_moss": C(0x5A7A3A), "fur": C(0x7A5A3A), "cave": C(0x14110F),
    "palm_trunk": C(0x8A6A4A), "palm_leaf": C(0x4E8A3A), "apple": C(0xC83A2A), "apple_green": C(0x9AC04A), "petal": C(0xF4B8D4), "petal_purple": C(0xB890E0),
    "orange": C(0xE8843A),
}


def blob(mb, x, y, z, r, mat, scale=(1, 1, 1), w=None, seg=6, rings=4):
    mb.sphere((x, y, z), r, mat, w, segments=seg, rings=rings, scale=scale)


def blade(mb, x, y, h, lean, a, mat, w=None, width=0.07):
    tx, ty = x + math.cos(a) * lean, y + math.sin(a) * lean
    px, py = -math.sin(a) * width / 2, math.cos(a) * width / 2
    solid(mb, [(x - px, y - py, 0), (x + px, y + py, 0), (tx, ty, h)], (math.cos(a) * 0.02, math.sin(a) * 0.02, 0), mat, w)


def sway(names, amp=6.0):
    return lambda t: ({b: [(kit.X, amp * math.sin(TAU * t + i)), (kit.Y, amp * 0.6 * math.sin(TAU * 2 * t + i * 1.7))] for i, b in enumerate(names)}, {})


def palm(mb, x, y, h, rnd, w=None):
    lean = rnd.uniform(-0.6, 0.6)
    pts = [(x + lean * (k / 4) ** 2, y, h * k / 4) for k in range(5)]
    for k, (a, b) in enumerate(zip(pts, pts[1:])):
        mb.cylinder(a, b, 0.16 - 0.02 * k, 0.14 - 0.02 * k, "palm_trunk", w, segments=6)
    tx, ty, tz = pts[-1]
    for i in range(7):
        a = TAU * i / 7 + rnd.uniform(-0.2, 0.2)
        mid = (tx + math.cos(a) * 0.9, ty + math.sin(a) * 0.9, tz + 0.25)
        tip = (tx + math.cos(a) * 1.9, ty + math.sin(a) * 1.9, tz - 0.5)
        px, py = -math.sin(a) * 0.22, math.cos(a) * 0.22
        solid(mb, [(tx, ty, tz), (mid[0] - px, mid[1] - py, mid[2]), tip, (mid[0] + px, mid[1] + py, mid[2])], (0, 0, 0.03), "palm_leaf" if i % 2 else "leaf", w)
    for i in range(3):
        blob(mb, tx + math.cos(i * 2.1) * 0.18, ty + math.sin(i * 2.1) * 0.18, tz - 0.12, 0.1, "coconut", (1, 1, 1), w, 5, 3)


def save(mb, name, bones=None, clip=None, seconds=4.0, pose=None):
    if bones:
        kit.save(mb, FAMILY, name, COLORS, mech=kit.Mech(bones).clip(clip, seconds, pose))
    else:
        kit.save(mb, FAMILY, name, COLORS)


# --- The game's biomes ----------------------------------------------------------------------------


def mountain_crag():
    mb = kit.begin()
    rnd = random.Random(1)
    for x, y, r, h in ((0, 0, 1.4, 5.5), (1.2, 0.5, 1.0, 3.6), (-1.1, 0.4, 1.1, 4.2), (0.3, -1.1, 0.9, 2.6), (-0.6, -1.0, 0.7, 1.8)):
        mb.cylinder((x, y, 0), (x + rnd.uniform(-0.3, 0.3), y + rnd.uniform(-0.3, 0.3), h), r, r * 0.35, rnd.choice(("stone", "stone_dark")), segments=6)
        blob(mb, x, y, h, r * 0.4, "snow", (1, 1, 0.5))
    for i in range(10):   # An eagle's nest on the highest ledge.
        a0, a1 = TAU * i / 10, TAU * (i + 1.5) / 10
        beam(mb, (math.cos(a0) * 0.4, math.sin(a0) * 0.4, 5.6), (math.cos(a1) * 0.45, math.sin(a1) * 0.45, 5.68), 0.04, "pole_dark")
    for k in range(2):
        blob(mb, -0.1 + 0.2 * k, 0, 5.68, 0.09, "egg", (1, 1, 1.3))
    for _ in range(8):
        a, d = rnd.uniform(0, TAU), rnd.uniform(1.8, 2.8)
        rock(mb, math.cos(a) * d, math.sin(a) * d, 0.2, rnd.uniform(0.25, 0.5), rnd)
    save(mb, "biome_mountain_crag")


def mountain_scree():
    mb = kit.begin()
    rnd = random.Random(2)
    for _ in range(34):
        x, y = rnd.uniform(-2.6, 2.6), rnd.uniform(-2.0, 2.0)
        r = rnd.uniform(0.2, 0.75) * (1.2 - abs(x) / 3.5)
        rock(mb, x, y, r * 0.45, r, rnd)
    for _ in range(6):
        blob(mb, rnd.uniform(-2.4, 2.4), rnd.uniform(-1.8, 1.8), 0.3, 0.3, "lichen", (1.3, 1.0, 0.3))
    save(mb, "biome_mountain_scree")


def alpine_flowers():
    mb = kit.begin()
    rnd = random.Random(3)
    bones = ["sway0", "sway1", "sway2"]
    blob(mb, 0, 0, 0, 1.6, "grass", (1.1, 1, 0.1), None, 9, 3)
    for i in range(22):
        x, y = rnd.uniform(-1.3, 1.3), rnd.uniform(-1.2, 1.2)
        w = {bones[i % 3]: 1.0}
        mb.cylinder((x, y, 0.05), (x, y, 0.3), 0.012, 0.01, "grass_dark", w, segments=4)
        blob(mb, x, y, 0.32, 0.06, rnd.choice(("white_flower", "white_flower", "purple", "blue_berry")), (1, 1, 0.6), w, 5, 3)
    for _ in range(4):
        rock(mb, rnd.uniform(-1.3, 1.3), rnd.uniform(-1.2, 1.2), 0.12, 0.25, rnd)
    save(mb, "biome_mountain_alpine_flowers", [(b, (0, 0, 0.05), (0, 0, 0.3), None) for b in bones], "sway", 4.0, sway(bones, 5))


def boreal_frozen_pond():
    mb = kit.begin()
    rnd = random.Random(4)
    pts = [(2.2, 0.3), (1.4, 1.6), (-0.4, 2.0), (-2.0, 1.0), (-2.3, -0.6), (-0.8, -1.7), (1.2, -1.5)]
    solid(mb, [(x, y, 0.0) for x, y in pts], (0, 0, 0.08), "ice")
    solid(mb, [(x * 0.6, y * 0.6, 0.08) for x, y in pts], (0, 0, 0.02), "ice_deep")
    for a, length in ((0.4, 1.4), (2.2, 1.1), (3.9, 1.5), (5.3, 0.9)):   # Cracks.
        beam(mb, (math.cos(a) * 0.2, math.sin(a) * 0.2, 0.105), (math.cos(a) * length, math.sin(a) * length, 0.105), 0.02, "snow")
    for i in range(12):
        a = TAU * i / 12
        blob(mb, math.cos(a) * 2.3, math.sin(a) * 1.9, 0.05, rnd.uniform(0.3, 0.5), "snow" if i % 2 else "snow_shade", (1.2, 1, 0.45))
    for k in range(4):
        mb.cylinder((1.7 + 0.1 * k, -0.9, 0.05), (1.75 + 0.12 * k, -0.9, 0.9 + 0.2 * k), 0.015, 0.01, "grass_dry", segments=4)
    save(mb, "biome_boreal_frozen_pond")


def boreal_snowy_log():
    mb = kit.begin()
    rnd = random.Random(5)
    log(mb, (-1.8, 0.2, 0.3), (1.7, -0.3, 0.26), 0.3)
    for k in range(5):
        blob(mb, -1.4 + 0.7 * k, 0.15 - 0.1 * k * 0.5, 0.56, 0.3, "snow", (1.4, 0.9, 0.35))
    for a, x in ((60, -0.6), (-70, 0.5), (80, 1.2)):
        rad = math.radians(a)
        beam(mb, (x, 0, 0.4), (x + 0.2, math.sin(rad) * 0.9, 0.4 + abs(math.cos(rad)) * 0.7 + 0.3), 0.05, "bark")
    for _ in range(5):
        x, y = rnd.uniform(-1.6, 1.6), rnd.uniform(0.6, 1.2)
        mb.cylinder((x, y, 0), (x, y, 0.16), 0.035, 0.03, "white_flower", segments=5)
        mb.cylinder((x, y, 0.16), (x, y, 0.24), 0.1, 0.02, "red", segments=6)
    blob(mb, 0, -0.9, 0, 1.3, "snow_shade", (1.5, 0.6, 0.15), None, 8, 3)
    save(mb, "biome_boreal_snowy_log")


def berry_heath(name, berry, leaf):
    def build():
        mb = kit.begin()
        rnd = random.Random(6 if berry == "blue_berry" else 7)
        for _ in range(9):
            x, y, r = rnd.uniform(-1.3, 1.3), rnd.uniform(-1.2, 1.2), rnd.uniform(0.35, 0.6)
            blob(mb, x, y, r * 0.45, r, rnd.choice((leaf, "leaf_dark")), (1.2, 1.0, 0.7), None, 7, 4)
            for _ in range(5):
                a, d = rnd.uniform(0, TAU), rnd.uniform(0, r * 0.9)
                blob(mb, x + math.cos(a) * d, y + math.sin(a) * d, r * 0.75, 0.06, berry, (1, 1, 1), None, 5, 3)
        if berry == "black_berry":
            for _ in range(8):   # Brambles arch out of the thicket.
                a = rnd.uniform(0, TAU)
                beam(mb, (math.cos(a) * 0.8, math.sin(a) * 0.8, 0.5), (math.cos(a) * 1.8, math.sin(a) * 1.8, 0.15), 0.02, "thorn")
        kit.save(mb, FAMILY, name, COLORS)
    return build


def petal_carpet(name, mat):
    def build():
        mb = kit.begin()
        rnd = random.Random(8 if mat == "petal" else 9)
        bones = ["drift0", "drift1"]
        for i in range(60):
            a, d = rnd.uniform(0, TAU), abs(rnd.gauss(0, 1.0))
            mb.box((math.cos(a) * d, math.sin(a) * d, 0.02), (rnd.uniform(0.08, 0.16), rnd.uniform(0.06, 0.1), 0.012), mat if i % 3 else "white_flower", rotation_z=a)
        for i in range(12):   # A few still falling.
            w = {bones[i % 2]: 1.0}
            mb.box((rnd.uniform(-1.2, 1.2), rnd.uniform(-1.2, 1.2), rnd.uniform(0.4, 2.2)), (0.1, 0.07, 0.012), mat, w, rotation_z=rnd.uniform(0, 3))
        pose = lambda t: ({"drift0": [(kit.Z, 360 * t)], "drift1": [(kit.Z, -360 * t)]}, {"drift0": (0.2 * math.sin(TAU * t), 0, 0.15 * math.sin(TAU * 2 * t)),   # noqa: E731
                                                                                          "drift1": (0, 0.2 * math.sin(TAU * t), 0.15 * math.sin(TAU * 2 * t + 1.5))})
        save(mb, name, [(b, (0, 0, 1.2), (0, 0, 1.8), None) for b in bones], "drift", 6.0, pose)
    return build


def reed_bank():
    mb = kit.begin()
    rnd = random.Random(10)
    solid(mb, [(-2.5, -1.0, 0.0), (2.5, -1.0, 0.0), (2.5, 0.2, 0.0), (-2.5, 0.2, 0.0)], (0, 0, 0.06), "water")
    blob(mb, 0, 0.8, 0, 2.6, "grass", (1, 0.4, 0.12), None, 9, 3)
    bones = ["sway0", "sway1", "sway2"]
    for i in range(16):
        x, y, h = rnd.uniform(-2.2, 2.2), rnd.uniform(-0.5, 0.4), rnd.uniform(1.0, 1.7)
        w = {bones[i % 3]: 1.0}
        mb.cylinder((x, y, 0), (x + 0.05, y, h), 0.02, 0.012, "grass_dark", w, segments=4)
        mb.cylinder((x + 0.045, y, h * 0.8), (x + 0.05, y, h * 0.97), 0.045, 0.045, "soil_dark", w, segments=6)
        blade(mb, x, y, h * 0.6, 0.3, rnd.uniform(0, TAU), "grass", w, 0.06)
    for _ in range(7):
        rock(mb, rnd.uniform(-2.3, 2.3), rnd.uniform(0.1, 0.5), 0.1, rnd.uniform(0.15, 0.3), rnd)
    save(mb, "biome_riverside_reed_bank", [(b, (0, 0, 0), (0, 0, 0.6), None) for b in bones], "sway", 4.0, sway(bones, 6))


def beaver_dam():
    """A dam of sticks across a stream, with the lodge: the water stands higher behind it. Waterline Z = 0."""
    mb = kit.begin()
    rnd = random.Random(11)
    mb.box((0, 1.6, -0.02), (7.0, 3.0, 0.1), "water")
    mb.box((0, -1.6, -0.5), (7.0, 3.0, 0.1), "water")
    for _ in range(70):
        x = rnd.uniform(-3.2, 3.2)
        y = rnd.uniform(-0.5, 0.5)
        a = rnd.uniform(0, TAU)
        length = rnd.uniform(0.6, 1.4)
        z = rnd.uniform(-0.5, 0.25) * (1 - abs(y))
        beam(mb, (x - math.cos(a) * length / 2, y - math.sin(a) * length / 2, z), (x + math.cos(a) * length / 2, y + math.sin(a) * length / 2, z + rnd.uniform(-0.1, 0.2)), 0.045,
             rnd.choice(("bark", "pole_dark", "bark_dead")))
    blob(mb, 0, 0, -0.35, 0.6, "mud", (5.5, 1.0, 0.8), None, 8, 3)
    blob(mb, 1.6, 2.2, -0.1, 1.1, "mud", (1, 1, 0.7), None, 8, 4)                  # The lodge.
    for _ in range(26):
        a, u = rnd.uniform(0, TAU), rnd.uniform(0.2, 1.0)
        beam(mb, (1.6 + math.cos(a) * 1.1 * u, 2.2 + math.sin(a) * 1.1 * u, 0.55 * (1 - u) + 0.05), (1.6 + math.cos(a + 0.5) * 1.0 * u, 2.2 + math.sin(a + 0.5) * 1.0 * u, 0.7 * (1 - u) + 0.1),
             0.04, rnd.choice(("bark", "bark_dead")))
    for x, y in ((-3.4, -0.9), (3.5, 0.9)):   # Gnawed stumps on the banks.
        mb.cylinder((x, y, -0.3), (x, y, 0.3), 0.16, 0.14, "bark", segments=7)
        mb.cylinder((x, y, 0.3), (x, y, 0.55), 0.14, 0.0, "log_end", segments=7)
    w = {"beaver": 1.0}
    blob(mb, -1.2, 1.3, 0.02, 0.2, "fur", (1, 1.6, 0.7), w)
    blob(mb, -1.2, 1.02, 0.08, 0.11, "fur", (1, 1.2, 0.9), w)
    solid(mb, [(-1.3, 1.6, 0.02), (-1.1, 1.6, 0.02), (-1.08, 1.95, 0.02), (-1.32, 1.95, 0.02)], (0, 0, 0.03), "soil_dark", w)
    pose = lambda t: ({"beaver": [(kit.Z, 20 * math.sin(TAU * t))]}, {"beaver": (0.5 * math.sin(TAU * t), 0.3 * math.sin(TAU * 2 * t), 0)})   # noqa: E731
    save(mb, "biome_riverside_beaver_dam", [("beaver", (-1.2, 1.3, 0), (-1.2, 1.0, 0), None)], "swim", 6.0, pose)


def olive_tree():
    mb = kit.begin()
    rnd = random.Random(12)
    mb.cylinder((0, 0, 0), (0.15, 0.05, 0.9), 0.4, 0.26, "bark_olive", segments=7)
    mb.cylinder((0.15, 0.05, 0.9), (-0.1, 0.1, 1.7), 0.28, 0.2, "bark_olive", segments=7)
    for a, length in ((0.3, 1.5), (1.9, 1.3), (3.4, 1.6), (4.9, 1.2)):
        tip = (-0.1 + math.cos(a) * length, 0.1 + math.sin(a) * length, 2.5 + rnd.uniform(0, 0.5))
        beam(mb, (-0.1, 0.1, 1.6), tip, 0.1, "bark_olive")
        for _ in range(3):
            blob(mb, tip[0] + rnd.uniform(-0.5, 0.5), tip[1] + rnd.uniform(-0.5, 0.5), tip[2] + rnd.uniform(-0.1, 0.5), rnd.uniform(0.5, 0.8), rnd.choice(("leaf_olive", "leaf_dark")),
                 (1, 1, 0.7), None, 7, 4)
            blob(mb, tip[0] + rnd.uniform(-0.6, 0.6), tip[1] + rnd.uniform(-0.6, 0.6), tip[2] - 0.25, 0.05, "black_berry", (1, 1, 1.4), None, 5, 3)
    for i in range(5):
        a = TAU * i / 5
        beam(mb, (math.cos(a) * 0.3, math.sin(a) * 0.3, 0.2), (math.cos(a) * 0.9, math.sin(a) * 0.9, 0.0), 0.1, "bark_olive")
    save(mb, "biome_mediterranean_olive_tree")


def lavender_rocks():
    mb = kit.begin()
    rnd = random.Random(13)
    bones = ["sway0", "sway1"]
    for _ in range(5):
        rock(mb, rnd.uniform(-1.2, 1.2), rnd.uniform(-1.0, 1.0), 0.2, rnd.uniform(0.3, 0.6), rnd, "stone_light")
    for i in range(7):
        x, y = rnd.uniform(-1.3, 1.3), rnd.uniform(-1.2, 1.2)
        w = {bones[i % 2]: 1.0}
        blob(mb, x, y, 0.15, 0.28, "leaf_olive", (1, 1, 0.6), w)
        for _ in range(6):
            a = rnd.uniform(0, TAU)
            mb.cylinder((x + math.cos(a) * 0.1, y + math.sin(a) * 0.1, 0.2), (x + math.cos(a) * 0.22, y + math.sin(a) * 0.22, 0.6), 0.02, 0.03, "lavender", w, segments=4)
    mb.cylinder((1.0, 0.9, 0), (1.0, 0.9, 0.05), 0.5, 0.45, "sand_dark", segments=8)
    for i in range(7):   # An agave.
        a = TAU * i / 7
        solid(mb, [(1.0 + math.cos(a - 0.3) * 0.1, 0.9 + math.sin(a - 0.3) * 0.1, 0.05), (1.0 + math.cos(a + 0.3) * 0.1, 0.9 + math.sin(a + 0.3) * 0.1, 0.05),
                   (1.0 + math.cos(a) * 0.55, 0.9 + math.sin(a) * 0.55, 0.5)], (0, 0, 0.05), "agave")
    save(mb, "biome_mediterranean_lavender", [(b, (0, 0, 0.1), (0, 0, 0.5), None) for b in bones], "sway", 4.0, sway(bones, 4))


def termite_mound():
    mb = kit.begin()
    rnd = random.Random(14)
    for x, y, r, h in ((0, 0, 0.7, 2.6), (0.5, 0.3, 0.45, 1.6), (-0.4, 0.4, 0.4, 1.3), (0.2, -0.5, 0.35, 1.0)):
        mb.cylinder((x, y, 0), (x + rnd.uniform(-0.1, 0.1), y, h * 0.6), r, r * 0.6, "termite", segments=7)
        mb.cylinder((x, y, h * 0.6), (x + rnd.uniform(-0.1, 0.1), y, h), r * 0.6, r * 0.12, "termite", segments=7)
    for _ in range(5):
        a = rnd.uniform(0, TAU)
        mb.cylinder((math.cos(a) * 0.55, math.sin(a) * 0.55, rnd.uniform(0.3, 1.4)), (math.cos(a) * 0.6, math.sin(a) * 0.6, rnd.uniform(0.3, 1.4)), 0.07, 0.07, "cave", segments=6)
    for _ in range(6):
        blade(mb, rnd.uniform(-1.4, 1.4), rnd.uniform(-1.3, 1.3), rnd.uniform(0.4, 0.8), 0.2, rnd.uniform(0, TAU), "grass_dry")
    for a in range(5):   # A thorn bush beside it.
        beam(mb, (1.3, -0.8, 0.0), (1.3 + math.cos(a * 1.3) * 0.7, -0.8 + math.sin(a * 1.3) * 0.7, 0.8), 0.03, "thorn")
    save(mb, "biome_dry_termite_mound")


def savanna_grass():
    mb = kit.begin()
    rnd = random.Random(15)
    bones = ["sway0", "sway1", "sway2"]
    for i in range(70):
        x, y = rnd.uniform(-1.8, 1.8), rnd.uniform(-1.8, 1.8)
        blade(mb, x, y, rnd.uniform(0.8, 1.5), rnd.uniform(0.1, 0.4), rnd.uniform(0, TAU), rnd.choice(("grass_gold", "grass_dry", "grass_gold")), {bones[i % 3]: 1.0}, 0.06)
    save(mb, "biome_savanna_tall_grass", [(b, (0, 0, 0), (0, 0, 0.6), None) for b in bones], "sway", 4.0, sway(bones, 8))


def kopje():
    mb = kit.begin()
    rnd = random.Random(16)
    for x, y, r, z in ((0, 0, 1.6, 0.9), (1.8, 0.4, 1.2, 0.7), (-1.6, 0.3, 1.3, 0.75), (0.4, 0.6, 1.1, 2.2), (-0.5, -0.9, 0.9, 0.5), (1.0, -1.0, 0.8, 0.45), (0.2, 0.3, 0.7, 3.2)):
        mb.sphere((x, y, z), r, rnd.choice(("sand_red", "stone", "sand_dark")), segments=7, rings=5, scale=(1.1, 1.0, 0.8))
    for _ in range(8):
        blade(mb, rnd.uniform(-2.8, 2.8), rnd.uniform(-2.2, -1.4), rnd.uniform(0.6, 1.0), 0.2, rnd.uniform(0, TAU), "grass_gold")
    mb.cylinder((-2.4, 1.0, 0), (-2.2, 1.1, 1.6), 0.12, 0.07, "bark_dead", segments=6)
    for a in (0.5, 2.5, 4.4):
        beam(mb, (-2.2, 1.1, 1.5), (-2.2 + math.cos(a) * 0.9, 1.1 + math.sin(a) * 0.9, 2.0), 0.04, "bark_dead")
    save(mb, "biome_savanna_kopje")


def waterhole():
    mb = kit.begin()
    rnd = random.Random(17)
    mb.cylinder((0, 0, 0), (0, 0, 0.05), 2.8, 2.6, "mud", segments=11)
    mb.cylinder((0, 0, 0.04), (0, 0, 0.08), 1.9, 1.9, "water", segments=10)
    for i in range(14):   # Cracked mud around it.
        a = TAU * i / 14
        beam(mb, (math.cos(a) * 2.0, math.sin(a) * 2.0, 0.055), (math.cos(a + 0.2) * 2.7, math.sin(a + 0.2) * 2.7, 0.055), 0.02, "soil_dark")
    for _ in range(10):
        a = rnd.uniform(0, TAU)
        blade(mb, math.cos(a) * 2.9, math.sin(a) * 2.9, rnd.uniform(0.5, 1.0), 0.2, a, "grass_gold")
    for a in (0.6, 0.9, 1.2):   # Tracks of what comes to drink.
        for k in range(4):
            mb.cylinder((math.cos(a) * (2.1 + 0.25 * k), math.sin(a) * (2.1 + 0.25 * k), 0.05), (math.cos(a) * (2.1 + 0.25 * k), math.sin(a) * (2.1 + 0.25 * k), 0.06), 0.06, 0.06, "soil_dark",
                        segments=5)
    beam(mb, (-1.6, -1.2, 0.08), (-0.9, -1.9, 0.3), 0.05, "bone")
    save(mb, "biome_savanna_waterhole")


def mangrove():
    """Mangrove roots standing in the water: waterline Z = 0."""
    mb = kit.begin()
    rnd = random.Random(18)
    mb.cylinder((0, 0, 0.9), (0.1, 0, 3.2), 0.22, 0.14, "bark_mangrove", segments=7)
    for i in range(9):   # Arched roots down into the water.
        a = TAU * i / 9 + rnd.uniform(-0.1, 0.1)
        r = rnd.uniform(0.9, 1.4)
        mid = (math.cos(a) * r * 0.6, math.sin(a) * r * 0.6, 0.8)
        beam(mb, (0, 0, 1.3 + 0.1 * (i % 3)), mid, 0.06, "bark_mangrove")
        beam(mb, mid, (math.cos(a) * r, math.sin(a) * r, -0.8), 0.05, "bark_mangrove")
    for a, length in ((0.3, 1.2), (2.4, 1.0), (4.3, 1.3)):
        tip = (math.cos(a) * length, math.sin(a) * length, 3.4)
        beam(mb, (0.08, 0, 2.8), tip, 0.06, "bark_mangrove")
        for _ in range(3):
            blob(mb, tip[0] + rnd.uniform(-0.4, 0.4), tip[1] + rnd.uniform(-0.4, 0.4), tip[2] + rnd.uniform(0, 0.5), rnd.uniform(0.5, 0.8), rnd.choice(("leaf", "leaf_jungle")), (1, 1, 0.7),
                 None, 7, 4)
    blob(mb, 0.1, 0, 3.9, 0.9, "leaf_dark", (1, 1, 0.7), None, 7, 4)
    mb.cylinder((0, 0, -0.04), (0, 0, 0.0), 2.0, 2.0, "water", segments=10)
    save(mb, "biome_coast_mangrove")


def turtle_nest():
    mb = kit.begin()
    rnd = random.Random(19)
    blob(mb, 0, 0, -0.02, 1.4, "sand", (1.1, 1, 0.1), None, 9, 3)
    mb.cylinder((0, 0, 0.03), (0, 0, 0.08), 0.6, 0.5, "sand_dark", segments=9)
    for i in range(9):
        a, d = TAU * i / 9, 0.25 if i % 2 else 0.1
        blob(mb, math.cos(a) * d, math.sin(a) * d, 0.12, 0.08, "egg")
    for k in range(6):   # The mother's tracks back to the sea.
        mb.box((-0.25, -0.8 - 0.25 * k, 0.03), (0.2, 0.08, 0.02), "sand_dark", rotation_z=0.5)
        mb.box((0.25, -0.9 - 0.25 * k, 0.03), (0.2, 0.08, 0.02), "sand_dark", rotation_z=-0.5)
    for _ in range(3):
        blob(mb, rnd.uniform(-1.0, 1.0), rnd.uniform(0.6, 1.0), 0.05, 0.13, "coconut")
    save(mb, "biome_coast_turtle_nest")


def fallen_fruit():
    mb = kit.begin()
    rnd = random.Random(20)
    mb.cylinder((0, 0, 0), (0.1, 0, 1.4), 0.2, 0.14, "bark", segments=7)
    for a, length in ((0.4, 1.0), (2.3, 0.9), (4.2, 1.1)):
        tip = (0.1 + math.cos(a) * length, math.sin(a) * length, 2.0)
        beam(mb, (0.1, 0, 1.3), tip, 0.07, "bark")
        blob(mb, tip[0], tip[1], tip[2] + 0.2, 0.75, "leaf" if a < 3 else "leaf_light", (1, 1, 0.75), None, 7, 4)
        for _ in range(3):
            blob(mb, tip[0] + rnd.uniform(-0.5, 0.5), tip[1] + rnd.uniform(-0.5, 0.5), tip[2] - 0.15, 0.08, "apple")
    blob(mb, 0.1, 0, 2.6, 0.8, "leaf", (1, 1, 0.7), None, 7, 4)
    for _ in range(14):
        a, d = rnd.uniform(0, TAU), rnd.uniform(0.4, 1.6)
        blob(mb, math.cos(a) * d, math.sin(a) * d, 0.07, 0.08, rnd.choice(("apple", "apple", "apple_green")))
    mb.cylinder((1.2, -0.9, 0), (1.2, -0.9, 0.3), 0.22, 0.28, "plank_light", segments=8)
    for _ in range(5):
        blob(mb, 1.2 + rnd.uniform(-0.12, 0.12), -0.9 + rnd.uniform(-0.12, 0.12), 0.32, 0.08, "apple")
    save(mb, "biome_orchard_wild_apple")


def glow_mushrooms():
    mb = kit.begin()
    rnd = random.Random(21)
    for i in range(11):
        x, y, h = rnd.uniform(-1.2, 1.2), rnd.uniform(-1.1, 1.1), rnd.uniform(0.3, 1.5)
        mb.cylinder((x, y, 0), (x + rnd.uniform(-0.1, 0.1), y, h), 0.05 + h * 0.04, 0.04 + h * 0.03, "white_flower", segments=6)
        mb.cylinder((x, y, h), (x, y, h + h * 0.3), 0.18 + h * 0.3, 0.03, "glow_shroom" if i % 3 else "purple", segments=8)
        mb.cylinder((x, y, h - 0.03), (x, y, h), 0.14 + h * 0.25, 0.18 + h * 0.3, "white_flower", segments=8)
    log(mb, (-1.4, 0.9, 0.2), (0.6, 1.3, 0.22), 0.2, mat="bark_dead")
    for _ in range(5):
        blob(mb, rnd.uniform(-1.3, 0.5), rnd.uniform(0.9, 1.3), 0.4, 0.14, "moss", (1.4, 1, 0.4))
    save(mb, "biome_enchanted_glow_mushrooms")


def fairy_stones():
    mb = kit.begin()
    rnd = random.Random(22)
    bones, parts = [], []
    blob(mb, 0, 0, 0, 1.7, "grass_dark", (1, 1, 0.08), None, 9, 3)
    for i in range(6):
        a = TAU * i / 6
        b = "stone%d" % i
        x, y, z = math.cos(a) * 1.1, math.sin(a) * 1.1, 0.9 + 0.4 * (i % 3)
        mb.sphere((x, y, z), 0.28, "stone_dark" if i % 2 else "stone", {b: 1.0}, segments=6, rings=4, scale=(1.0, 0.8, 1.3))
        mb.box((x, y - 0.24, z), (0.1, 0.03, 0.16), "glow_stone", {b: 1.0}, rotation_z=a + 1.57)
        bones.append((b, (x, y, z), (x, y, z + 0.3), None))
        parts.append((b, i))
    mb.cylinder((0, 0, 0.0), (0, 0, 0.5), 0.5, 0.35, "stone", segments=7)
    mb.cylinder((0, 0, 0.5), (0, 0, 0.56), 0.3, 0.3, "glow_stone", segments=7)
    for _ in range(8):
        a, d = rnd.uniform(0, TAU), rnd.uniform(0.6, 1.6)
        mb.cylinder((math.cos(a) * d, math.sin(a) * d, 0.02), (math.cos(a) * d, math.sin(a) * d, 0.22), 0.012, 0.01, "grass", segments=4)
        blob(mb, math.cos(a) * d, math.sin(a) * d, 0.24, 0.05, "glow_shroom", (1, 1, 0.7), None, 5, 3)
    pose = lambda t: ({b: [(kit.Z, 360 * t * (1 if i % 2 else -1))] for b, i in parts}, {b: (0, 0, 0.18 * math.sin(TAU * t + i * 1.05)) for b, i in parts})   # noqa: E731
    save(mb, "biome_enchanted_fairy_stones", bones, "float", 6.0, pose)


# --- Five biomes the game does not have ------------------------------------------------------------


def swamp_dead_tree():
    mb = kit.begin()
    rnd = random.Random(23)
    mb.cylinder((0, 0, -0.3), (0.2, 0, 2.0), 0.5, 0.28, "bark_dead", segments=7)
    mb.cylinder((0.2, 0, 2.0), (-0.1, 0.1, 4.2), 0.28, 0.14, "bark_dead", segments=7)
    bones = []
    for i, (a, z0, length) in enumerate(((0.5, 2.6, 1.8), (2.4, 3.0, 1.5), (4.0, 2.3, 1.6), (5.4, 3.5, 1.2))):
        tip = (math.cos(a) * length, math.sin(a) * length, z0 + 0.6)
        beam(mb, (0.1, 0.05, z0), tip, 0.08, "bark_dead")
        b = "moss%d" % i
        for k in range(3):   # Hanging moss.
            u = 0.4 + 0.25 * k
            px, py, pz = 0.1 + (tip[0] - 0.1) * u, 0.05 + (tip[1] - 0.05) * u, z0 + 0.6 * u
            mb.cylinder((px, py, pz), (px, py, pz - rnd.uniform(0.5, 1.1)), 0.07, 0.01, "hang_moss", {b: 1.0}, segments=5)
        bones.append((b, (tip[0] * 0.6, tip[1] * 0.6, z0 + 0.4), (tip[0] * 0.6, tip[1] * 0.6, z0 - 0.4), None))
    for i in range(6):   # Knees coming out of the water.
        a, d = TAU * i / 6 + 0.3, rnd.uniform(0.9, 1.6)
        mb.cylinder((math.cos(a) * d, math.sin(a) * d, -0.3), (math.cos(a) * d, math.sin(a) * d, rnd.uniform(0.2, 0.6)), 0.12, 0.04, "bark_dead", segments=6)
    mb.cylinder((0, 0, -0.03), (0, 0, 0.0), 2.3, 2.3, "water_bog", segments=10)
    for _ in range(5):
        a, d = rnd.uniform(0, TAU), rnd.uniform(0.8, 2.0)
        mb.cylinder((math.cos(a) * d, math.sin(a) * d, 0.0), (math.cos(a) * d, math.sin(a) * d, 0.02), 0.22, 0.22, "leaf", segments=7)
    names = [b for b, *_r in bones]
    save(mb, "biome_swamp_dead_tree", bones, "sway", 5.0, sway(names, 7))


def bog_pool():
    mb = kit.begin()
    rnd = random.Random(24)
    mb.cylinder((0, 0, 0), (0, 0, 0.05), 2.4, 2.3, "mud", segments=11)
    mb.cylinder((0, 0, 0.04), (0, 0, 0.08), 1.9, 1.9, "water_bog", segments=10)
    bones = []
    for i in range(3):
        b = "gas%d" % i
        a, d = rnd.uniform(0, TAU), rnd.uniform(0.3, 1.2)
        blob(mb, math.cos(a) * d, math.sin(a) * d, -0.05, 0.14, "glow_shroom", (1, 1, 0.8), {b: 1.0})
        bones.append((b, (math.cos(a) * d, math.sin(a) * d, 0), (math.cos(a) * d, math.sin(a) * d, 0.3), None))
    for _ in range(4):
        a, d = rnd.uniform(0, TAU), rnd.uniform(0.3, 1.5)
        mb.cylinder((math.cos(a) * d, math.sin(a) * d, 0.08), (math.cos(a) * d, math.sin(a) * d, 0.1), 0.25, 0.25, "leaf", segments=7)
    for i in range(10):
        a = TAU * i / 10
        blob(mb, math.cos(a) * 2.4, math.sin(a) * 2.4, 0.1, rnd.uniform(0.3, 0.45), "moss", (1, 1, 0.6))
        if i % 3 == 0:
            blade(mb, math.cos(a) * 2.2, math.sin(a) * 2.2, 1.2, 0.3, a, "grass_dark")

    def gas(t):
        moves = {}
        for i in range(3):
            s = (t * 2 + i / 3) % 1.0
            moves["gas%d" % i] = (0, 0, 0.7 * s if s < 0.7 else -0.1)
        return {}, moves

    save(mb, "biome_swamp_bog_pool", bones, "bubble", 4.0, gas)


def dune():
    mb = kit.begin()
    pts_n = 9
    for layer, (h, shift, mat) in enumerate(((1.6, 0.0, "sand"), (1.0, 2.2, "sand_dark"))):
        crest = [(-3.5 + 7.0 * i / (pts_n - 1), 0.8 * math.sin(i * 0.8 + layer) + shift, h * (0.5 + 0.5 * math.sin(math.pi * i / (pts_n - 1)))) for i in range(pts_n)]
        for (a, b) in zip(crest, crest[1:]):
            solid(mb, [(a[0], a[1] - 2.2, 0.0), (b[0], b[1] - 2.2, 0.0), b, a], (0, 0.02, -0.02), mat)                          # The long windward slope.
            solid(mb, [a, b, (b[0], b[1] + 0.8, 0.0), (a[0], a[1] + 0.8, 0.0)], (0, 0.02, 0.02), "sand_dark" if layer == 0 else "sand_red")   # The steep lee side.
    rnd = random.Random(25)
    for _ in range(5):
        blade(mb, rnd.uniform(-3, 3), rnd.uniform(-2.6, -2.0), 0.5, 0.15, rnd.uniform(0, TAU), "grass_dry")
    save(mb, "biome_desert_dune")


def oasis():
    mb = kit.begin()
    rnd = random.Random(26)
    blob(mb, 0, 0, -0.03, 3.4, "sand", (1.1, 1, 0.08), None, 10, 3)
    mb.cylinder((0, 0, 0.02), (0, 0, 0.07), 1.8, 1.7, "grass", segments=10)
    mb.cylinder((0.2, 0, 0.06), (0.2, 0, 0.1), 1.3, 1.3, "water", segments=10)
    bones = []
    for i, (x, y, h) in enumerate(((-1.6, 0.6, 4.2), (1.5, 1.0, 3.4), (0.3, -1.7, 3.8))):
        b = "palm%d" % i
        palm(mb, x, y, h, rnd, {b: 1.0})
        bones.append((b, (x, y, 0), (x, y, h), None))
    for _ in range(8):
        a = rnd.uniform(0, TAU)
        blade(mb, math.cos(a) * 1.6, math.sin(a) * 1.6, rnd.uniform(0.5, 1.0), 0.2, a, "grass")
    for _ in range(5):
        rock(mb, rnd.uniform(-2.6, 2.6), rnd.uniform(-2.4, 2.4), 0.1, 0.25, rnd, "sand_red")
    names = [b for b, *_r in bones]
    save(mb, "biome_desert_oasis", bones, "sway", 5.0, sway(names, 2.5))


def desert_bones():
    mb = kit.begin()
    rnd = random.Random(27)
    blob(mb, 0, 0, -0.03, 2.4, "sand", (1.2, 1, 0.08), None, 9, 3)
    beam(mb, (-1.6, 0, 0.3), (1.6, 0, 0.5), 0.09, "bone")
    for k in range(7):   # Ribs half buried.
        x = -1.2 + 0.4 * k
        for s in (-1, 1):
            beam(mb, (x, 0, 0.35 + 0.02 * k), (x, s * 0.7, 0.9), 0.045, "bone")
            beam(mb, (x, s * 0.7, 0.9), (x, s * 0.5, 0.05), 0.04, "bone")
    blob(mb, 2.0, 0, 0.3, 0.32, "bone", (1.5, 0.9, 0.8))
    for s in (-1, 1):
        mb.cylinder((2.2, s * 0.2, 0.4), (2.5, s * 0.6, 0.9), 0.06, 0.0, "bone", segments=5)
    for _ in range(4):
        rock(mb, rnd.uniform(-2, 2), rnd.uniform(-1.6, -1.2), 0.1, 0.2, rnd, "sand_red")
    mb.cylinder((-2.0, 1.2, 0), (-2.0, 1.2, 0.9), 0.14, 0.12, "agave", segments=7)   # A cactus.
    for s in (-1, 1):
        beam(mb, (-2.0, 1.2, 0.4), (-2.0 + s * 0.3, 1.2, 0.5), 0.07, "agave")
        beam(mb, (-2.0 + s * 0.3, 1.2, 0.5), (-2.0 + s * 0.3, 1.2, 0.9), 0.07, "agave")
    save(mb, "biome_desert_bones")


def ice_spikes():
    mb = kit.begin()
    rnd = random.Random(28)
    blob(mb, 0, 0, -0.02, 2.2, "snow", (1.1, 1, 0.12), None, 9, 3)
    for _ in range(11):
        a, d = rnd.uniform(0, TAU), rnd.uniform(0, 1.4)
        h = rnd.uniform(1.0, 4.0) * (1.2 - d / 2.0)
        mb.cylinder((math.cos(a) * d, math.sin(a) * d, 0), (math.cos(a) * d * 1.15, math.sin(a) * d * 1.15, h), rnd.uniform(0.25, 0.45), 0.0, rnd.choice(("ice", "ice_deep", "ice")), segments=5)
    for _ in range(6):
        a, d = rnd.uniform(0, TAU), rnd.uniform(1.4, 2.0)
        blob(mb, math.cos(a) * d, math.sin(a) * d, 0.1, rnd.uniform(0.3, 0.5), "snow_shade", (1.2, 1, 0.5))
    save(mb, "biome_tundra_ice_spikes")


def frozen_beast():
    """A beast of another age caught in the ice up to its shoulders."""
    mb = kit.begin()
    blob(mb, 0, 0, 1.2, 1.0, "fur", (1.0, 1.6, 1.0), None, 8, 5)
    blob(mb, 0, -1.5, 1.5, 0.6, "fur", (1.0, 1.1, 1.1), None, 7, 5)
    for sx in (-1, 1):
        for sy in (-0.8, 0.8):
            mb.cylinder((sx * 0.5, sy, 1.0), (sx * 0.5, sy, 0.1), 0.28, 0.24, "fur", segments=6)
        mb.cylinder((sx * 0.3, -1.9, 1.3), (sx * 0.6, -2.5, 0.9), 0.08, 0.06, "bone", segments=5)     # Tusks.
        mb.cylinder((sx * 0.6, -2.5, 0.9), (sx * 0.45, -2.8, 1.5), 0.06, 0.0, "bone", segments=5)
    mb.cylinder((0, -2.0, 1.4), (0, -2.3, 0.5), 0.16, 0.08, "fur", segments=6)
    pts = [(1.7, -3.0), (2.0, 1.2), (0.6, 2.4), (-1.5, 2.0), (-2.1, -0.6), (-1.2, -3.2)]
    for (a, b) in zip(pts, pts[1:] + pts[:1]):   # The ice around it, in clear slabs.
        solid(mb, [(a[0], a[1], 0), (b[0], b[1], 0), (b[0] * 0.85, b[1] * 0.85, 1.3), (a[0] * 0.85, a[1] * 0.85, 1.3)], (-a[0] * 0.02, -a[1] * 0.02, 0), "ice")
    solid(mb, [(x * 0.85, y * 0.85, 1.25) for x, y in pts], (0, 0, 0.1), "ice_deep")   # The beast's back and head rise out of it.
    for x, y, h in ((1.2, 1.0, 2.2), (-1.3, 0.6, 1.9), (0.9, -2.4, 1.8)):
        mb.cylinder((x, y, 1.2), (x * 1.1, y * 1.1, h + 0.6), 0.4, 0.0, "ice", segments=5)
    for x, y in ((2.4, 0.0), (-2.5, 1.0), (0.5, 3.0)):
        blob(mb, x, y, 0.1, 0.5, "snow", (1.2, 1, 0.5))
    save(mb, "biome_tundra_frozen_beast")


def obsidian():
    mb = kit.begin()
    rnd = random.Random(30)
    blob(mb, 0, 0, -0.02, 2.0, "basalt", (1.1, 1, 0.1), None, 9, 3)
    for _ in range(12):
        a, d = rnd.uniform(0, TAU), rnd.uniform(0, 1.3)
        h = rnd.uniform(0.6, 2.4)
        lean = rnd.uniform(-0.4, 0.4)
        mb.cylinder((math.cos(a) * d, math.sin(a) * d, 0), (math.cos(a) * d + lean, math.sin(a) * d + lean, h), rnd.uniform(0.15, 0.35), 0.0, rnd.choice(("obsidian", "obsidian", "obsidian_shine")),
                    segments=4)
    for a, length in ((0.6, 1.8), (2.8, 1.5), (4.6, 1.7)):
        beam(mb, (math.cos(a) * 0.3, math.sin(a) * 0.3, 0.05), (math.cos(a) * length, math.sin(a) * length, 0.05), 0.05, "glow_lava")
    save(mb, "biome_volcanic_obsidian")


def basalt_columns():
    mb = kit.begin()
    rnd = random.Random(31)
    for i in range(-3, 4):
        for j in range(-2, 3):
            x, y = i * 0.62 + (0.31 if j % 2 else 0), j * 0.54
            h = max(0.3, 3.2 - 0.5 * math.hypot(x, y * 1.3) + rnd.uniform(-0.4, 0.4))
            mb.cylinder((x, y, 0), (x, y, h), 0.35, 0.35, "basalt" if (i + j) % 2 else "basalt_light", segments=6)
    for _ in range(5):
        a, d = rnd.uniform(0, TAU), rnd.uniform(2.4, 3.0)
        mb.cylinder((math.cos(a) * d, math.sin(a) * d * 0.7, 0.2), (math.cos(a) * d + 0.9, math.sin(a) * d * 0.7 + 0.3, 0.2), 0.3, 0.3, "basalt", segments=6)
    save(mb, "biome_volcanic_basalt_columns")


def jungle_idol():
    mb = kit.begin()
    rnd = random.Random(32)
    mb.box((0, 0, 0.25), (2.4, 2.0, 0.5), "idol")
    mb.box((0, 0, 1.6), (1.8, 1.4, 2.2), "idol")
    mb.box((0, 0, 2.95), (2.1, 1.6, 0.5), "idol")
    for sx in (-1, 1):   # A face: eyes, nose, a mouth of teeth.
        mb.box((sx * 0.45, -0.72, 2.0), (0.4, 0.06, 0.3), "cave")
        mb.box((sx * 0.45, -0.75, 2.0), (0.14, 0.04, 0.14), "glow_shroom")
        mb.box((sx * 1.0, 0, 1.7), (0.25, 0.6, 0.9), "idol")
    mb.box((0, -0.76, 1.55), (0.3, 0.12, 0.6), "idol")
    mb.box((0, -0.72, 0.95), (1.1, 0.06, 0.3), "cave")
    for k in range(5):
        mb.box((-0.44 + 0.22 * k, -0.75, 1.02), (0.14, 0.05, 0.16), "bone")
    for _ in range(14):
        blob(mb, rnd.uniform(-1.1, 1.1), rnd.uniform(-0.8, 0.8), rnd.choice((0.55, 3.25, 2.75)), rnd.uniform(0.2, 0.4), "idol_moss", (1.3, 1, 0.35))
    for i in range(8):   # Vines over it and giant leaves at its foot.
        x = -1.0 + 0.28 * i
        mb.cylinder((x, -0.74, 3.2), (x + rnd.uniform(-0.2, 0.2), -0.78, rnd.uniform(1.4, 2.6)), 0.03, 0.02, "leaf_jungle", segments=4)
    for i in range(7):
        a = TAU * i / 7
        solid(mb, [(math.cos(a) * 1.5, math.sin(a) * 1.5, 0.05), (math.cos(a - 0.25) * 2.2, math.sin(a - 0.25) * 2.2, 0.7), (math.cos(a) * 2.9, math.sin(a) * 2.9, 0.4),
                   (math.cos(a + 0.25) * 2.2, math.sin(a + 0.25) * 2.2, 0.7)], (0, 0, 0.04), "leaf_jungle" if i % 2 else "leaf_light")
    save(mb, "biome_jungle_idol")


def jungle_plants():
    mb = kit.begin()
    rnd = random.Random(33)
    bones = ["sway0", "sway1"]
    for i in range(9):   # Giant leaves on tall stems.
        a, d = rnd.uniform(0, TAU), rnd.uniform(0, 0.9)
        x, y, h = math.cos(a) * d, math.sin(a) * d, rnd.uniform(1.2, 2.6)
        w = {bones[i % 2]: 1.0}
        tx, ty = x + math.cos(a) * 0.6, y + math.sin(a) * 0.6
        mb.cylinder((x, y, 0), (tx, ty, h), 0.04, 0.03, "leaf_dark", w, segments=5)
        px, py = -math.sin(a) * 0.5, math.cos(a) * 0.5
        solid(mb, [(tx, ty, h), (tx + math.cos(a) * 0.5 - px, ty + math.sin(a) * 0.5 - py, h + 0.15), (tx + math.cos(a) * 1.5, ty + math.sin(a) * 1.5, h - 0.4),
                   (tx + math.cos(a) * 0.5 + px, ty + math.sin(a) * 0.5 + py, h + 0.15)], (0, 0, 0.03), "leaf_jungle" if i % 2 else "leaf_light", w)
    for i in range(3):   # And a flower as big as a head.
        x, y = rnd.uniform(-1.2, 1.2), rnd.uniform(-1.2, 1.2)
        mb.cylinder((x, y, 0), (x, y, 0.7), 0.04, 0.03, "leaf_dark", segments=5)
        for k in range(6):
            a = TAU * k / 6
            solid(mb, [(x, y, 0.7), (x + math.cos(a - 0.4) * 0.25, y + math.sin(a - 0.4) * 0.25, 0.85), (x + math.cos(a) * 0.5, y + math.sin(a) * 0.5, 0.8),
                       (x + math.cos(a + 0.4) * 0.25, y + math.sin(a + 0.4) * 0.25, 0.85)], (0, 0, 0.03), ("red", "orange", "purple")[i])
        blob(mb, x, y, 0.78, 0.1, "grass_gold")
    save(mb, "biome_jungle_plants", [(b, (0, 0, 0), (0, 0, 1.0), None) for b in bones], "sway", 5.0, sway(bones, 4))


MODELS = {
    "biome_mountain_crag": mountain_crag,
    "biome_mountain_scree": mountain_scree,
    "biome_mountain_alpine_flowers": alpine_flowers,
    "biome_boreal_frozen_pond": boreal_frozen_pond,
    "biome_boreal_snowy_log": boreal_snowy_log,
    "biome_boreal_blueberries": berry_heath("biome_boreal_blueberries", "blue_berry", "leaf_dark"),
    "biome_temperate_brambles": berry_heath("biome_temperate_brambles", "black_berry", "leaf"),
    "biome_flowering_petals": petal_carpet("biome_flowering_petals", "petal"),
    "biome_flowering_petals_purple": petal_carpet("biome_flowering_petals_purple", "petal_purple"),
    "biome_riverside_reed_bank": reed_bank,
    "biome_riverside_beaver_dam": beaver_dam,
    "biome_mediterranean_olive_tree": olive_tree,
    "biome_mediterranean_lavender": lavender_rocks,
    "biome_dry_termite_mound": termite_mound,
    "biome_savanna_tall_grass": savanna_grass,
    "biome_savanna_kopje": kopje,
    "biome_savanna_waterhole": waterhole,
    "biome_coast_mangrove": mangrove,
    "biome_coast_turtle_nest": turtle_nest,
    "biome_orchard_wild_apple": fallen_fruit,
    "biome_enchanted_glow_mushrooms": glow_mushrooms,
    "biome_enchanted_fairy_stones": fairy_stones,
    "biome_swamp_dead_tree": swamp_dead_tree,
    "biome_swamp_bog_pool": bog_pool,
    "biome_desert_dune": dune,
    "biome_desert_oasis": oasis,
    "biome_desert_bones": desert_bones,
    "biome_tundra_ice_spikes": ice_spikes,
    "biome_tundra_frozen_beast": frozen_beast,
    "biome_volcanic_obsidian": obsidian,
    "biome_volcanic_basalt_columns": basalt_columns,
    "biome_jungle_idol": jungle_idol,
    "biome_jungle_plants": jungle_plants,
}

kit.run(MODELS, FAMILY)
