"""Enemy lair proposals: the places hostile creatures come from (camps,
nests, altars, portals), so that a threat has a home on the map that can be
found, watched and destroyed. See ../LEEME.md.

    blender --background --factory-startup --python art/blender/proposals/lairs/build.py -- [ids]
"""

import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import _kit as kit  # noqa: E402
import _shapes  # noqa: E402
import common  # noqa: E402
from _shapes import TAU, barrel, beam, crate, log, mark, moved, rock, rope, sack, solid  # noqa: E402

FAMILY = "lairs"
C = common.rgb
COLORS = {
    **_shapes.COLORS,
    "hide": C(0x9A7050), "hide_dark": C(0x7A5438), "hide_pale": C(0xB8946A), "bone": C(0xE4DCC8), "bone_dark": C(0xC0B49A),
    "goblin_red": C(0xA8322A), "goblin_paint": C(0xE8D040), "orc_red": C(0x8E2A24), "orc_black": C(0x2A2624),
    "soil": C(0x6A4A30), "soil_dark": C(0x4A3422), "scorch": C(0x2A2420), "ash": C(0x4A4642), "grass_dead": C(0x8A8A4A),
    "flame": C(0xF08A24), "flame_core": C(0xFFF0B0), "ember": C(0xE85820), "smoke": C(0x8A8A8A),
    "web": C(0xE8E8E0), "cocoon": C(0xD8D8CC), "egg": C(0xF0F0E0), "bark_dead": C(0x6A625A), "cave": C(0x14110F),
    "dark_stone": C(0x3E3A40), "dark_stone_light": C(0x5A5560), "glow_necro": C(0x60FF90), "glow_portal": C(0xB060FF),
    "glow_portal_core": C(0xF0D0FF), "glow_wisp": C(0xA0E8FF), "glow_slime": C(0x7AE04A), "slime": C(0x4A9A3A), "slime_dark": C(0x357A2A),
    "cloth_black": C(0x2A262E), "cloth_red": C(0xA83A34), "candle": C(0xF0E8D0), "water_deep": C(0x2F6A9A), "water": C(0x4A8FC0),
    "foam": C(0xF0F6FA), "tentacle": C(0x8A3A5A), "tentacle_light": C(0xD88AA0), "rubbish": C(0x7A6A4A), "rat": C(0x5A5048),
    "eye": C(0x101010), "mushroom": C(0xB8362E), "mushroom_stem": C(0xEADFC8), "moss": C(0x5E8A3A),
}


def flames(mb, x, y, z, s, bone, outer="flame", core="flame_core"):
    w = {bone: 1.0}
    mb.cylinder((x, y, z), (x, y, z + 0.3 * s), 0.14 * s, 0.2 * s, outer, w, segments=5)
    mb.cylinder((x, y, z + 0.3 * s), (x, y, z + 0.85 * s), 0.2 * s, 0.0, outer, w, segments=5)
    mb.cylinder((x, y, z + 0.02), (x, y, z + 0.5 * s), 0.1 * s, 0.0, core, w, segments=5)
    return (bone, (x, y, z), (x, y, z + 0.4 * s), None)


def flame_pose(bone, s=1.0, phase=0.0):
    return lambda t: ({bone: [(kit.Z, 360 * t), (kit.X, 9 * math.sin(TAU * 3 * t + phase))]}, {bone: (0, 0, 0.05 * s * math.sin(TAU * 4 * t + phase))})


def campfire(mb, x, y, s, bone, rnd, outer="flame", core="flame_core"):
    for i in range(7):
        a = TAU * i / 7
        rock(mb, x + math.cos(a) * 0.5 * s, y + math.sin(a) * 0.5 * s, 0.08, 0.16 * s, rnd)
    mb.cylinder((x, y, 0), (x, y, 0.05), 0.42 * s, 0.4 * s, "ash", segments=8)
    for i in range(4):
        a = TAU * i / 4 + 0.4
        log(mb, (x + math.cos(a) * 0.38 * s, y + math.sin(a) * 0.38 * s, 0.06), (x - math.cos(a) * 0.05, y - math.sin(a) * 0.05, 0.42 * s), 0.06 * s)
    return flames(mb, x, y, 0.12, s, bone, outer, core)


def merged(*poses):
    def pose(t):
        turns, moves = {}, {}
        for p in poses:
            a, b = p(t)
            turns.update(a)
            moves.update(b)
        return turns, moves
    return pose


def skull(mb, x, y, z, s=1.0, w=None, rot=0.0):
    start = mark(mb)
    mb.sphere((0, 0, 0), 0.13 * s, "bone", w, segments=6, rings=5, scale=(1.0, 1.1, 1.0))
    mb.box((0, -0.07 * s, -0.12 * s), (0.13 * s, 0.1 * s, 0.09 * s), "bone", w)
    for sx in (-1, 1):
        mb.box((sx * 0.05 * s, -0.125 * s, 0.0), (0.045 * s, 0.03 * s, 0.05 * s), "eye", w)
    moved(mb, start, (x, y, z), rot)


def bones_pile(mb, x, y, n, rnd, spread=0.6):
    for _ in range(n):
        a, d = rnd.uniform(0, TAU), rnd.uniform(0, spread)
        px, py = x + math.cos(a) * d, y + math.sin(a) * d
        b = rnd.uniform(0, TAU)
        beam(mb, (px, py, 0.05), (px + math.cos(b) * 0.4, py + math.sin(b) * 0.4, 0.05 + rnd.uniform(0, 0.15)), 0.035, "bone" if rnd.random() < 0.7 else "bone_dark")


def hut(mb, x, y, r, h, mat, mat2, rnd, door_angle=-1.57, skull_top=True):
    """A crude cone of hides on poles."""
    n = 7
    for i in range(n):
        a0, a1 = TAU * i / n + door_angle + TAU / (2 * n), TAU * (i + 1) / n + door_angle + TAU / (2 * n)
        if i == n - 1:
            continue   # The gap is the door.
        solid(mb, [(x + math.cos(a0) * r, y + math.sin(a0) * r, 0), (x + math.cos(a1) * r, y + math.sin(a1) * r, 0), (x, y, h)],
              (math.cos((a0 + a1) / 2) * 0.04, math.sin((a0 + a1) / 2) * 0.04, 0.02), mat if i % 2 else mat2)
    for i in range(n):
        a = TAU * i / n + door_angle + TAU / (2 * n)
        mb.cylinder((x + math.cos(a) * r * 1.02, y + math.sin(a) * r * 1.02, 0), (x - math.cos(a) * 0.12, y - math.sin(a) * 0.12, h + 0.35), 0.035, 0.025, "pole_dark", segments=5)
    mb.cylinder((x, y, 0), (x, y, 0.03), r * 0.9, r * 0.9, "soil_dark", segments=8)
    if skull_top:
        skull(mb, x + math.cos(door_angle) * r * 0.55, y + math.sin(door_angle) * r * 0.55, h * 0.62, 0.9, None, math.degrees(door_angle) + 90)


def spikes(mb, x0, y0, x1, y1, n, rnd, h=1.3):
    for k in range(n):
        u = (k + 0.5) / n
        x, y = x0 + (x1 - x0) * u, y0 + (y1 - y0) * u
        lean = rnd.uniform(-0.25, 0.25)
        mb.cylinder((x, y, 0), (x + lean, y - 0.25, h * rnd.uniform(0.85, 1.15)), 0.06, 0.01, "pole_dark", segments=5)


def banner(mb, x, y, h, cloth, emblem, prefix):
    """A ragged war banner; returns its bones and pose."""
    mb.cylinder((x, y, 0), (x, y, h), 0.05, 0.04, "pole_dark", segments=6)
    beam(mb, (x - 0.45, y, h - 0.15), (x + 0.45, y, h - 0.15), 0.03, "pole_dark")
    b1, b2 = prefix + "cloth", prefix + "rag"
    fy = y - 0.04
    solid(mb, [(x - 0.4, fy, h - 0.17), (x + 0.4, fy, h - 0.17), (x + 0.4, fy, h - 0.95), (x - 0.4, fy, h - 0.95)], (0, 0.02, 0), cloth, {b1: 1.0})
    for k in range(4):
        x0 = x - 0.4 + 0.2 * k
        solid(mb, [(x0, fy, h - 0.95), (x0 + 0.2, fy, h - 0.95), (x0 + 0.1, fy, h - 1.25 - 0.08 * (k % 2))], (0, 0.02, 0), cloth, {b2: 1.0})
    solid(mb, [(x - 0.16, fy - 0.01, h - 0.45), (x + 0.16, fy - 0.01, h - 0.45), (x + 0.12, fy - 0.01, h - 0.68), (x, fy - 0.01, h - 0.8), (x - 0.12, fy - 0.01, h - 0.68)],
          (0, 0.04, 0), emblem, {b1: 1.0})
    for sx in (-1, 1):
        mb.box((x + sx * 0.06, fy - 0.015, h - 0.56), (0.05, 0.05, 0.06), cloth, {b1: 1.0})
    skull(mb, x, y, h + 0.1, 0.9)
    bones = [(b1, (x, fy, h - 0.17), (x, fy, h - 0.95), None), (b2, (x, fy, h - 0.95), (x, fy, h - 1.3), b1)]
    pose = lambda t: ({b1: [(kit.X, 7 * math.sin(TAU * t))], b2: [(kit.X, 14 * math.sin(TAU * t - 1.2))]}, {})   # noqa: E731
    return bones, pose


# --- Models -------------------------------------------------------------------------------------


def goblin_camp():
    mb = kit.begin()
    rnd = random.Random(1)
    mb.cylinder((0, 0, 0), (0, 0, 0.03), 5.2, 5.0, "soil", segments=12)
    hut(mb, -2.6, 1.8, 1.3, 1.9, "hide", "hide_dark", rnd, -0.6)
    hut(mb, 2.5, 2.2, 1.5, 2.2, "hide_pale", "hide", rnd, -2.4)
    hut(mb, 0.2, 3.6, 1.1, 1.6, "hide_dark", "hide", rnd, -1.57)
    fire = campfire(mb, 0, 0, 1.1, "fire", rnd)
    for sx in (-0.9, 0.9):   # A spit with something on it.
        mb.cylinder((sx, 0, 0), (sx, 0, 0.9), 0.035, 0.03, "pole_dark", segments=5)
    beam(mb, (-1.0, 0, 0.88), (1.0, 0, 0.88), 0.02, "pole")
    mb.sphere((0, 0, 0.88), 0.16, "hide_dark", segments=6, rings=4, scale=(1.6, 1, 1))
    bones, pose = banner(mb, -3.6, -1.6, 3.0, "goblin_red", "goblin_paint", "b_")
    mb.cylinder((3.4, -1.4, 0), (3.4, -1.4, 0.06), 1.0, 1.0, "soil_dark", segments=8)   # A cage of sticks.
    for i in range(10):
        a = TAU * i / 10
        mb.cylinder((3.4 + math.cos(a) * 0.8, -1.4 + math.sin(a) * 0.8, 0), (3.4 + math.cos(a) * 0.7, -1.4 + math.sin(a) * 0.7, 1.4), 0.03, 0.025, "pole", segments=5)
    mb.cylinder((3.4, -1.4, 1.38), (3.4, -1.4, 1.45), 0.75, 0.75, "pole_dark", segments=8)
    bones_pile(mb, 3.4, -1.4, 5, rnd, 0.4)
    crate(mb, -1.4, -2.6, 0.0, 0.55)   # Loot.
    sack(mb, -0.8, -2.9, 0.0, 0.24)
    sack(mb, -1.9, -3.1, 0.0, 0.2)
    barrel(mb, -2.2, -2.5, 0.0, 0.7, 0.26)
    mb.box((-1.4, -2.6, 0.62), (0.3, 0.2, 0.08), "gold")
    spikes(mb, -4.6, -3.6, -1.6, -4.9, 7, rnd)
    spikes(mb, 1.8, -4.8, 4.6, -3.2, 7, rnd)
    for a in (0.7, 2.6):
        skull(mb, math.cos(a) * 4.4, math.sin(a) * 4.4, 1.3, 1.0, None, math.degrees(a) + 90)
        mb.cylinder((math.cos(a) * 4.4, math.sin(a) * 4.4, 0), (math.cos(a) * 4.4, math.sin(a) * 4.4, 1.2), 0.04, 0.03, "pole_dark", segments=5)
    mech = kit.Mech([fire] + bones).clip("idle", 3.0, merged(flame_pose("fire", 1.1), pose))
    kit.save(mb, FAMILY, "lair_goblin_camp", COLORS, mech=mech)


def goblin_hut(name, mushroom):
    def build():
        mb = kit.begin()
        rnd = random.Random(2)
        if mushroom:   # A hollowed giant mushroom.
            mb.cylinder((0, 0, 0), (0, 0, 1.5), 0.9, 0.7, "mushroom_stem", segments=8)
            mb.cylinder((0, 0, 1.4), (0, 0, 1.7), 1.9, 1.6, "mushroom", segments=9)
            mb.cylinder((0, 0, 1.7), (0, 0, 2.5), 1.6, 0.3, "mushroom", segments=9)
            for i in range(6):
                a = TAU * i / 6 + 0.3
                mb.sphere((math.cos(a) * 1.1, math.sin(a) * 1.1, 1.95), 0.2, "mushroom_stem", segments=6, rings=3, scale=(1, 1, 0.4))
            solid(mb, [(-0.3, -0.86, 0), (0.3, -0.86, 0), (0.3, -0.82, 0.8), (0, -0.8, 1.05), (-0.3, -0.82, 0.8)], (0, -0.04, 0), "cave")
            mb.box((0.55, -0.72, 1.0), (0.3, 0.05, 0.3), "window")
            mb.cylinder((0.5, 0.3, 2.2), (0.6, 0.35, 2.9), 0.08, 0.07, "pole_dark", segments=6)
        else:
            hut(mb, 0, 0, 1.4, 2.1, "hide", "hide_dark", rnd)
        skull(mb, 1.5, -1.2, 1.1, 1.0)
        mb.cylinder((1.5, -1.2, 0), (1.5, -1.2, 1.0), 0.04, 0.03, "pole_dark", segments=5)
        bones_pile(mb, -1.4, -1.3, 4, rnd, 0.35)
        sack(mb, -1.0, -1.6, 0.0, 0.2)
        kit.save(mb, FAMILY, name, COLORS)
    return build


def bandit_hideout():
    mb = kit.begin()
    rnd = random.Random(3)
    for x, y, r in ((-2.4, 2.0, 1.5), (-0.6, 2.9, 1.8), (1.6, 2.6, 1.5), (3.0, 1.4, 1.2), (-3.3, 0.6, 1.0)):
        rock(mb, x, y, r * 0.55, r, rnd)
    for sx in (-1.6, 1.4):
        mb.cylinder((sx, -0.6, 0), (sx, -0.6, 1.9), 0.07, 0.06, "pole", segments=6)
    solid(mb, [(-2.0, -0.9, 1.85), (1.8, -0.9, 1.85), (1.6, 1.9, 2.6), (-1.8, 1.9, 2.6)], (0, 0, 0.05), "hide_dark")
    solid(mb, [(-2.0, -0.9, 1.9), (-0.2, -0.9, 1.9), (-0.3, 1.9, 2.65), (-1.8, 1.9, 2.65)], (0, 0, 0.03), "moss")
    mb.box((0.2, 1.0, 0.04), (1.0, 2.0, 0.08), "hide_pale")           # Bedrolls under it.
    mb.box((-1.0, 1.0, 0.04), (0.9, 2.0, 0.08), "hide")
    crate(mb, 2.2, -1.2, 0.0, 0.7)                                    # What they have taken.
    crate(mb, 2.9, -0.6, 0.0, 0.55)
    crate(mb, 2.3, -1.2, 0.76, 0.45)
    barrel(mb, 1.5, -1.9, 0.0, 0.85, 0.3)
    mb.box((3.2, -1.6, 0.2), (0.7, 0.45, 0.4), "plank_dark")           # A chest left open.
    mb.box((3.2, -1.6, 0.42), (0.6, 0.36, 0.06), "gold")
    solid(mb, [(2.85, -1.38, 0.4), (3.55, -1.38, 0.4), (3.55, -1.2, 0.75), (2.85, -1.2, 0.75)], (0, 0.05, 0.02), "plank_dark")
    fire = campfire(mb, 0, -2.4, 0.9, "fire", rnd)
    log(mb, (-1.4, -3.3, 0.18), (0.2, -3.6, 0.18), 0.18)
    mb.cylinder((-3.6, -2.2, 0), (-3.6, -2.2, 3.2), 0.07, 0.05, "pole_dark", segments=6)   # A lookout pole with a rag.
    solid(mb, [(-3.6, -2.22, 3.1), (-2.9, -2.22, 2.95), (-3.6, -2.22, 2.75)], (0, 0.02, 0), "cloth_red", {"rag": 1.0})
    for k in range(3):
        beam(mb, (-3.3 + 0.25 * k, -1.2, 0.0), (-3.2 + 0.25 * k, -0.9, 1.5), 0.02, "pole")          # Spears against a rock.
        mb.cylinder((-3.2 + 0.25 * k, -0.9, 1.5), (-3.18 + 0.25 * k, -0.85, 1.75), 0.04, 0.0, "steel", segments=4)
    rag = lambda t: ({"rag": [(kit.Z, 18 * math.sin(TAU * t)), (kit.Y, 6 * math.sin(TAU * 2 * t))]}, {})   # noqa: E731
    mech = kit.Mech([fire, ("rag", (-3.6, -2.2, 2.95), (-2.9, -2.2, 2.95), None)]).clip("idle", 3.0, merged(flame_pose("fire", 0.9), rag))
    kit.save(mb, FAMILY, "lair_bandit_hideout", COLORS, mech=mech)


def orc_war_camp():
    mb = kit.begin()
    rnd = random.Random(4)
    mb.cylinder((0, 0, 0), (0, 0, 0.03), 7.0, 6.8, "soil", segments=12)
    # The chieftain's tent: hides over big tusks.
    for i in range(8):
        a0, a1 = TAU * i / 8 + 0.39, TAU * (i + 1) / 8 + 0.39
        if i == 5:
            continue
        solid(mb, [(math.cos(a0) * 2.6, 3.2 + math.sin(a0) * 2.6, 0), (math.cos(a1) * 2.6, 3.2 + math.sin(a1) * 2.6, 0), (0, 3.2, 3.6)],
              (math.cos((a0 + a1) / 2) * 0.05, math.sin((a0 + a1) / 2) * 0.05, 0.02), "hide" if i % 2 else "orc_red")
    for sx in (-1, 1):
        for k in range(4):
            a0, a1 = 0.5 * k, 0.5 * (k + 1)
            beam(mb, (sx * (1.1 - 0.5 * math.sin(a0)), 0.9, 2.3 * math.sin(a0) * 0.9 + 0.0), (sx * (1.1 - 0.5 * math.sin(a1)), 0.9, 2.3 * math.sin(a1) * 0.9), 0.1 - 0.02 * k, "bone")
    skull(mb, 0, 0.75, 2.5, 2.0)
    fire = campfire(mb, 0, -1.2, 1.6, "fire", rnd)
    b1, p1 = banner(mb, -4.4, 0.6, 4.2, "orc_black", "orc_red", "l_")
    b2, p2 = banner(mb, 4.4, 0.6, 4.2, "orc_red", "orc_black", "r_")
    bones = [fire] + b1 + b2
    for k, (x, y) in enumerate(((-3.2, -3.0), (-2.2, -3.6))):   # War drums.
        mb.cylinder((x, y, 0), (x, y, 0.75), 0.42, 0.5, "hide_dark", segments=9)
        mb.cylinder((x, y, 0.75), (x, y, 0.8), 0.52, 0.52, "hide_pale", segments=9)
        for i in range(9):
            a = TAU * i / 9
            rope(mb, (x + math.cos(a) * 0.52, y + math.sin(a) * 0.52, 0.78), (x + math.cos(a + 0.3) * 0.43, y + math.sin(a + 0.3) * 0.43, 0.05), 0.012)
        bone = "stick%d" % k
        beam(mb, (x + 0.1, y - 0.1, 0.84), (x + 0.5, y - 0.6, 1.2), 0.03, "bone", {bone: 1.0})
        bones.append((bone, (x + 0.5, y - 0.6, 1.2), (x + 0.1, y - 0.1, 0.84), None))
    for sx in (2.4, 3.3):   # A rack of cleavers and axes.
        mb.cylinder((sx, -3.4, 0), (sx, -3.2, 1.5), 0.05, 0.04, "pole_dark", segments=5)
    beam(mb, (2.2, -3.25, 1.4), (3.5, -3.25, 1.4), 0.04, "pole_dark")
    for k in range(3):
        x = 2.5 + 0.35 * k
        beam(mb, (x, -3.6, 0.0), (x, -3.28, 1.6), 0.025, "pole")
        solid(mb, [(x - 0.2, -3.3, 1.35), (x + 0.2, -3.3, 1.35), (x + 0.25, -3.3, 1.7), (x - 0.15, -3.3, 1.75)], (0, 0.03, 0), "steel")
    for a0, a1 in ((3.5, 4.3), (5.1, 5.9)):   # Stretches of spiked palisade.
        for k in range(8):
            a = a0 + (a1 - a0) * k / 7
            mb.cylinder((math.cos(a) * 6.4, math.sin(a) * 6.4, 0), (math.cos(a) * 6.6, math.sin(a) * 6.6, 2.0 + 0.3 * (k % 2)), 0.14, 0.02, "bark_dead", segments=6)
    bones_pile(mb, 4.6, -1.8, 9, rnd, 0.9)
    skull(mb, 4.6, -1.8, 0.35, 1.3)

    def drums(t):
        return {"stick0": [(kit.X, 25 * max(0.0, math.sin(TAU * 4 * t)))], "stick1": [(kit.X, 25 * max(0.0, math.sin(TAU * 4 * t + math.pi)))]}, {}

    mech = kit.Mech(bones).clip("idle", 3.0, merged(flame_pose("fire", 1.6), p1, p2, drums))
    kit.save(mb, FAMILY, "lair_orc_war_camp", COLORS, mech=mech)


def spider_nest(name, cave):
    def build():
        mb = kit.begin()
        rnd = random.Random(5 if cave else 6)
        anchors = []
        if cave:
            for x, y, r in ((-2.2, 1.6, 1.7), (0, 2.6, 2.1), (2.3, 1.7, 1.6), (-3.0, 0.2, 1.1), (3.1, 0.3, 1.1)):
                rock(mb, x, y, r * 0.6, r, rnd, "stone_dark")
            solid(mb, [(-1.4, 0.8, 0), (1.4, 0.8, 0), (1.6, 0.9, 1.5), (0.6, 1.0, 2.3), (-0.6, 1.0, 2.3), (-1.6, 0.9, 1.5)], (0, 0.6, 0), "cave")
            anchors = [(-1.5, 0.7, 1.6), (1.5, 0.7, 1.6), (0, 0.8, 2.3), (-1.3, 0.6, 0.1), (1.3, 0.6, 0.1)]
        else:
            for x, y, h in ((-2.4, 0.4, 4.2), (2.3, 0.2, 4.6), (0.2, 2.6, 3.8)):
                mb.cylinder((x, y, 0), (x + 0.1, y, h), 0.28, 0.12, "bark_dead", segments=7)
                for k in range(3):
                    a = rnd.uniform(0, TAU)
                    beam(mb, (x + 0.05, y, h * (0.5 + 0.15 * k)), (x + math.cos(a) * 1.2, y + math.sin(a) * 1.2, h * (0.62 + 0.15 * k)), 0.06, "bark_dead")
            anchors = [(-2.3, 0.4, 3.6), (2.35, 0.2, 3.8), (0.25, 2.6, 3.3), (-2.35, 0.4, 0.8), (2.3, 0.2, 0.9)]
        center = (0.0, 0.6 if cave else 0.9, 1.3 if cave else 2.3)
        for p in anchors:   # The web: spokes and two rings.
            beam(mb, p, center, 0.02, "web")
        for u in (0.35, 0.7):
            ring = [tuple(center[i] + (p[i] - center[i]) * u for i in range(3)) for p in anchors]
            order = [0, 2, 1, 4, 3]
            for i in range(5):
                beam(mb, ring[order[i]], ring[order[(i + 1) % 5]], 0.015, "web")
        bones = []
        for i, (x, y, z, r) in enumerate(((-0.9, 0.3, 1.3, 0.3), (0.9, 0.2, 1.6, 0.36), (0.1, 1.3, 1.1, 0.26))):   # Cocoons that sway.
            b = "cocoon%d" % i
            top = (x, y + (0.5 if cave else 0.6), z + 1.2)
            rope(mb, top, (x, y, z + r * 1.4), 0.015, {b: 1.0})
            mb.sphere((x, y, z), r, "cocoon", {b: 1.0}, segments=6, rings=5, scale=(1, 1, 1.7))
            for k in range(3):
                mb.cylinder((x, y, z - r * 0.8 + r * 0.8 * k), (x, y, z - r * 0.8 + r * 0.8 * k + 0.03), r * 0.95, r * 0.95, "web", {b: 1.0}, segments=6)
            bones.append((b, top, (x, y, z), None))
        for _ in range(9):   # Eggs.
            a, d = rnd.uniform(0, TAU), rnd.uniform(0.4, 1.6)
            mb.sphere((math.cos(a) * d, -0.6 + math.sin(a) * d * 0.6, 0.12), rnd.uniform(0.1, 0.17), "egg", segments=6, rings=4)
        bones_pile(mb, 1.8, -1.2, 6, rnd, 0.6)
        skull(mb, 1.8, -1.2, 0.14, 1.0)
        sway = lambda t: ({"cocoon%d" % i: [(kit.X, 6 * math.sin(TAU * t + i * 1.5)), (kit.Y, 4 * math.sin(TAU * t + i))] for i in range(3)}, {})   # noqa: E731
        kit.save(mb, FAMILY, name, COLORS, mech=kit.Mech(bones).clip("sway", 4.0, sway))
    return build


def necromancer_altar():
    mb = kit.begin()
    rnd = random.Random(7)
    mb.cylinder((0, 0, 0), (0, 0, 0.12), 4.0, 3.8, "dark_stone", segments=10)
    mb.cylinder((0, 0, 0.12), (0, 0, 0.16), 2.6, 2.6, "dark_stone_light", segments=10)
    for i in range(5):   # A pentagon of lines that glow.
        a0, a1 = TAU * i / 5 + 0.31, TAU * (i + 2) / 5 + 0.31
        beam(mb, (math.cos(a0) * 2.3, math.sin(a0) * 2.3, 0.17), (math.cos(a1) * 2.3, math.sin(a1) * 2.3, 0.17), 0.04, "glow_necro")
    mb.box((0, 0, 0.55), (1.8, 0.9, 0.8), "dark_stone")
    mb.box((0, 0, 0.98), (2.1, 1.1, 0.12), "dark_stone_light")
    for k in range(3):
        skull(mb, -0.6 + 0.6 * k, -0.2, 1.17, 0.9)
    mb.box((0.0, 0.25, 1.08), (0.5, 0.35, 0.08), "cloth_black")
    mb.box((0.0, 0.25, 1.13), (0.44, 0.3, 0.03), "bone")
    bones, poses = [], []
    for i, sx in enumerate((-2.9, 2.9)):
        mb.cylinder((sx, 0, 0.12), (sx, 0, 1.4), 0.1, 0.07, "dark_stone", segments=6)
        mb.cylinder((sx, 0, 1.4), (sx, 0, 1.65), 0.14, 0.3, "iron", segments=7)
        b = "fire%d" % i
        bones.append(flames(mb, sx, 0, 1.62, 0.8, b, "glow_necro", "flame_core"))
        poses.append(flame_pose(b, 0.8, i * 1.7))
    for i in range(5):   # Standing stones around.
        a = TAU * i / 5 + 0.31 + TAU / 10
        mb.cylinder((math.cos(a) * 3.4, math.sin(a) * 3.4, 0.1), (math.cos(a) * 3.3, math.sin(a) * 3.3, 2.2 + 0.4 * (i % 2)), 0.4, 0.22, "dark_stone", segments=5)
        mb.box((math.cos(a) * 3.05, math.sin(a) * 3.05, 1.3), (0.08, 0.08, 0.5), "glow_necro", rotation_z=a)
    for sx in (-1.6, 1.7):   # Open graves in front.
        mb.box((sx, -4.6, 0.02), (1.0, 2.0, 0.04), "cave")
        mb.sphere((sx + 0.9, -4.6, 0.0), 0.6, "soil_dark", segments=7, rings=3, scale=(0.8, 1.5, 0.5))
        solid(mb, [(sx - 0.3, -3.5, 0.0), (sx + 0.3, -3.5, 0.0), (sx + 0.3, -3.5, 0.75), (sx, -3.5, 0.95), (sx - 0.3, -3.5, 0.75)], (0, 0.12, 0), "dark_stone_light")
    beam(mb, (-1.4, -4.9, 0.05), (-1.9, -4.2, 0.4), 0.04, "bone")
    w = {"orb": 1.0}
    mb.cylinder((0, 0.25, 1.75), (0, 0.25, 1.95), 0.0, 0.16, "glow_necro", w, segments=5)
    mb.cylinder((0, 0.25, 1.95), (0, 0.25, 2.3), 0.16, 0.0, "glow_necro", w, segments=5)
    bones.append(("orb", (0, 0.25, 1.95), (0, 0.25, 2.3), None))
    poses.append(lambda t: ({"orb": [(kit.Z, 360 * t)]}, {"orb": (0, 0, 0.1 * math.sin(TAU * 2 * t))}))
    bones_pile(mb, 2.2, -2.4, 6, rnd, 0.7)
    kit.save(mb, FAMILY, "lair_necromancer_altar", COLORS, mech=kit.Mech(bones).clip("idle", 4.0, merged(*poses)))


def dragon_hoard():
    mb = kit.begin()
    rnd = random.Random(8)
    for x, y, r in ((-4.0, 3.0, 2.6), (-1.4, 4.6, 3.2), (2.0, 4.4, 3.0), (4.4, 2.6, 2.4), (-5.2, 0.6, 1.6), (5.4, 0.4, 1.7), (0.2, 6.6, 2.6)):
        rock(mb, x, y, r * 0.6, r, rnd, "stone_dark")
    solid(mb, [(-2.6, 1.4, 0), (2.6, 1.4, 0), (3.0, 1.6, 2.6), (1.4, 1.9, 4.0), (-1.4, 1.9, 4.0), (-3.0, 1.6, 2.6)], (0, 1.4, 0), "cave")
    mb.cylinder((0, -2.0, 0), (0, -2.0, 0.04), 5.2, 4.8, "scorch", segments=11)
    for x, y, r in ((0.0, -0.8, 1.5), (-1.3, -0.2, 0.9), (1.4, -0.3, 1.0), (0.3, -2.0, 0.8)):   # The hoard.
        mb.sphere((x, y, 0.0), r, "gold", segments=8, rings=4, scale=(1.0, 1.0, 0.55))
    for _ in range(14):
        a, d = rnd.uniform(0, TAU), rnd.uniform(1.6, 3.2)
        mb.cylinder((math.cos(a) * d, -1.0 + math.sin(a) * d * 0.8, 0.04), (math.cos(a) * d, -1.0 + math.sin(a) * d * 0.8, 0.07), 0.09, 0.09, "gold", segments=7)
    mb.box((1.9, -1.9, 0.25), (0.8, 0.5, 0.5), "plank_dark")
    mb.cylinder((1.5, -1.9, 0.5), (2.3, -1.9, 0.5), 0.25, 0.25, "plank", segments=8)
    mb.cylinder((-1.2, -1.5, 0.3), (-1.0, -1.3, 1.4), 0.03, 0.03, "steel", segments=5)      # A sword stuck in the gold.
    beam(mb, (-1.2, -1.3, 1.1), (-0.85, -1.45, 1.15), 0.025, "gold")
    mb.cylinder((0.6, -0.4, 0.7), (0.6, -0.4, 1.0), 0.16, 0.2, "gold", segments=8)           # A crown and a cup.
    for i in range(6):
        a = TAU * i / 6
        mb.cylinder((0.6 + math.cos(a) * 0.19, -0.4 + math.sin(a) * 0.19, 1.0), (0.6 + math.cos(a) * 0.2, -0.4 + math.sin(a) * 0.2, 1.12), 0.03, 0.0, "gold", segments=4)
    for a in (2.4, 3.4, 4.6, 5.6):   # Burnt trees and bones of knights.
        x, y = math.cos(a) * 5.4, -1.0 + math.sin(a) * 4.6
        mb.cylinder((x, y, 0), (x + 0.2, y, 1.8), 0.16, 0.05, "scorch", segments=6)
    bones_pile(mb, -3.2, -2.6, 10, rnd, 1.0)
    skull(mb, -3.2, -2.6, 0.16, 1.2)
    mb.cylinder((-3.6, -1.9, 0.1), (-3.6, -1.9, 0.14), 0.4, 0.4, "steel", segments=9)        # A shield.
    bones = []
    for i in range(3):
        b = "smoke%d" % i
        for k in range(3):
            mb.sphere((0.2 * k * (1 if i % 2 else -1), 1.6, 3.2 + 0.7 * k), 0.5 + 0.15 * k, "smoke", {b: 1.0}, segments=6, rings=4, scale=(1, 1, 0.8))
        bones.append((b, (0, 1.6, 3.0), (0, 1.6, 4.0), None))

    def smoke(t):
        turns, moves = {}, {}
        for i in range(3):
            s = (t + i / 3) % 1.0
            moves["smoke%d" % i] = (0.3 * s, -0.8 * s, 2.0 * s)
            turns["smoke%d" % i] = [(kit.Z, 100 * s)]
        return turns, moves

    kit.save(mb, FAMILY, "lair_dragon_hoard", COLORS, mech=kit.Mech(bones).clip("smoke", 5.0, smoke))


def troll_cave():
    mb = kit.begin()
    rnd = random.Random(9)
    for x, y, r in ((-2.6, 2.2, 2.0), (0, 3.2, 2.5), (2.7, 2.3, 2.0), (-3.8, 0.4, 1.3), (3.8, 0.5, 1.3)):
        rock(mb, x, y, r * 0.6, r, rnd)
    mb.sphere((0, 3.0, 2.2), 3.4, "moss", segments=8, rings=4, scale=(1.2, 0.8, 0.35))
    solid(mb, [(-1.7, 1.2, 0), (1.7, 1.2, 0), (2.0, 1.3, 1.8), (0.8, 1.5, 2.9), (-0.8, 1.5, 2.9), (-2.0, 1.3, 1.8)], (0, 0.8, 0), "cave")
    fire = campfire(mb, 0, -1.4, 1.2, "fire", rnd)
    for i in range(3):   # A cauldron on three stones.
        a = TAU * i / 3
        rock(mb, math.cos(a) * 0.6, -1.4 + math.sin(a) * 0.6, 0.25, 0.3, rnd, "stone_dark")
    mb.cylinder((0, -1.4, 0.55), (0, -1.4, 1.2), 0.55, 0.8, "iron", segments=9)
    mb.cylinder((0, -1.4, 1.15), (0, -1.4, 1.2), 0.72, 0.72, "slime", segments=9)
    beam(mb, (0.2, -1.3, 1.2), (0.9, -0.8, 2.2), 0.04, "bone")
    log(mb, (2.4, -1.6, 0.25), (3.0, 0.4, 1.6), 0.22, mat="bark_dead")      # Its club, with a spike.
    mb.cylinder((2.95, 0.3, 1.5), (3.3, 0.6, 1.7), 0.07, 0.0, "steel", segments=4)
    bones_pile(mb, -2.6, -1.6, 12, rnd, 1.0)
    for k in range(3):
        skull(mb, -2.9 + 0.4 * k, -1.2 - 0.3 * k, 0.15 + 0.2 * (k == 1), 1.2)
    mb.cylinder((-3.6, -3.0, 0), (-3.6, -3.0, 1.6), 0.06, 0.05, "pole_dark", segments=5)   # A sign: keep out.
    mb.box((-3.6, -3.05, 1.4), (0.8, 0.05, 0.45), "plank")
    for sx in (-0.2, 0.2):
        beam(mb, (-3.6 + sx, -3.09, 1.55), (-3.6 - sx, -3.09, 1.25), 0.03, "goblin_red")
    kit.save(mb, FAMILY, "lair_troll_cave", COLORS, mech=kit.Mech([fire]).clip("idle", 3.0, flame_pose("fire", 1.2)))


def slime_pool():
    mb = kit.begin()
    rnd = random.Random(10)
    mb.cylinder((0, 0, 0), (0, 0, 0.06), 3.0, 2.8, "slime_dark", segments=11)
    mb.cylinder((0, 0, 0.05), (0, 0, 0.1), 2.4, 2.4, "slime", segments=11)
    mb.cylinder((0.3, -0.2, 0.09), (0.3, -0.2, 0.13), 1.3, 1.3, "glow_slime", segments=9)
    bones = []
    for i in range(6):
        b = "bubble%d" % i
        a, d = rnd.uniform(0, TAU), rnd.uniform(0.3, 1.9)
        x, y = math.cos(a) * d, math.sin(a) * d
        mb.sphere((x, y, -0.08), rnd.uniform(0.18, 0.34), "glow_slime" if i % 2 else "slime", {b: 1.0}, segments=6, rings=4, scale=(1, 1, 0.75))
        bones.append((b, (x, y, 0), (x, y, 0.3), None))
    for i in range(8):
        a = TAU * i / 8 + rnd.uniform(-0.2, 0.2)
        rock(mb, math.cos(a) * 2.8, math.sin(a) * 2.8, 0.2, rnd.uniform(0.3, 0.5), rnd, "stone_dark")
        mb.sphere((math.cos(a) * 2.75, math.sin(a) * 2.75, 0.42), 0.26, "slime", segments=6, rings=3, scale=(1.2, 1.2, 0.4))
    for k in range(4):   # A skeleton half dissolved.
        beam(mb, (-1.2 + 0.12 * k, 1.0, 0.1), (-1.25 + 0.12 * k, 1.5, 0.22), 0.025, "bone")
    skull(mb, -1.0, 0.8, 0.2, 1.0)
    beam(mb, (-0.9, 1.6, 0.12), (-0.3, 2.3, 0.3), 0.03, "bone")
    mb.cylinder((1.5, 1.2, 0.1), (1.9, 1.5, 1.0), 0.03, 0.03, "steel", segments=5)

    def bubble(t):
        moves = {}
        for i in range(6):
            s = (t * 2 + i / 6) % 1.0
            moves["bubble%d" % i] = (0, 0, 0.28 * math.sin(math.pi * min(1.0, s * 1.6)) if s < 0.625 else -0.12)
        return {}, moves

    kit.save(mb, FAMILY, "lair_slime_pool", COLORS, mech=kit.Mech(bones).clip("bubble", 4.0, bubble))


def portal():
    mb = kit.begin()
    rnd = random.Random(11)
    mb.cylinder((0, 0, 0), (0, 0, 0.2), 3.2, 3.0, "dark_stone", segments=10)
    mb.cylinder((0, 0, 0.2), (0, 0, 0.3), 2.4, 2.3, "dark_stone_light", segments=10)
    for k in range(3):
        mb.box((0, -2.6 - 0.35 * k, 0.1 - 0.03 * k), (2.0, 0.4, 0.2 - 0.06 * k), "dark_stone_light")
    n = 12
    for i in range(n):   # The arch: a ring of blocks standing on the dais.
        a0, a1 = math.pi * i / n * 1.6 - 0.3 * math.pi, math.pi * (i + 1) / n * 1.6 - 0.3 * math.pi
        p0 = (math.cos(a0) * 2.0, 0, 2.0 + math.sin(a0) * 2.0)
        p1 = (math.cos(a1) * 2.0, 0, 2.0 + math.sin(a1) * 2.0)
        mb.cylinder(p0, p1, 0.36, 0.36, "dark_stone" if i % 2 else "dark_stone_light", segments=4)
        if i % 3 == 1:
            mid = ((p0[0] + p1[0]) / 2, -0.3, (p0[2] + p1[2]) / 2)
            mb.box(mid, (0.14, 0.06, 0.3), "glow_portal")
    w = {"swirl": 1.0}
    for k, (r, mat) in enumerate(((1.65, "glow_portal"), (1.15, "glow_portal_core"), (0.6, "glow_portal"))):
        for i in range(8):
            a0, a1 = TAU * i / 8 + 0.4 * k, TAU * (i + 0.7) / 8 + 0.4 * k
            solid(mb, [(math.cos(a0) * r, -0.02 * k, 2.0 + math.sin(a0) * r), (math.cos(a1) * r, -0.02 * k, 2.0 + math.sin(a1) * r),
                       (math.cos(a1) * r * 0.62, -0.02 * k, 2.0 + math.sin(a1) * r * 0.62), (math.cos(a0) * r * 0.7, -0.02 * k, 2.0 + math.sin(a0) * r * 0.7)],
                  (0, 0.04, 0), mat, {"swirl%d" % k: 1.0})
    for i in range(5):
        a = TAU * i / 5
        mb.cylinder((math.cos(a) * 2.9, 1.0 + math.sin(a) * 0.4, 1.4 + 0.4 * (i % 2)), (math.cos(a) * 2.9, 1.0 + math.sin(a) * 0.4, 1.8 + 0.4 * (i % 2)), 0.1, 0.0,
                    "glow_portal", {"shards": 1.0}, segments=4)
    for a in (0.8, 2.3, 4.0, 5.4):
        rock(mb, math.cos(a) * 3.4, math.sin(a) * 3.4, 0.25, 0.4, rnd, "dark_stone")
    bones = [("swirl%d" % k, (0, 0, 2.0), (0, -0.5, 2.0), None) for k in range(3)] + [("shards", (0, 1.0, 1.6), (0, 1.0, 2.2), None)]

    def swirl(t):
        return ({"swirl0": [(kit.Y, 360 * t)], "swirl1": [(kit.Y, -720 * t)], "swirl2": [(kit.Y, 1080 * t)], "shards": [(kit.Z, 360 * t)]},
                {"shards": (0, 0, 0.15 * math.sin(TAU * 2 * t))})

    kit.save(mb, FAMILY, "lair_portal", COLORS, mech=kit.Mech(bones).clip("swirl", 6.0, swirl))


def rat_burrow():
    mb = kit.begin()
    rnd = random.Random(12)
    mb.sphere((0, 0.4, 0), 1.6, "rubbish", segments=8, rings=4, scale=(1.3, 1.0, 0.55))
    mb.sphere((1.0, -0.2, 0), 0.9, "soil_dark", segments=7, rings=4, scale=(1.2, 1.0, 0.5))
    for x, y, z in ((-0.6, -0.72, 0.3), (0.5, -0.76, 0.25), (1.5, -0.7, 0.18)):
        mb.cylinder((x, y, z), (x, y - 0.06, z), 0.17, 0.17, "cave", segments=7)
    sack(mb, -1.3, -0.9, 0.0, 0.26)
    solid(mb, [(-1.5, -1.2, 0.02), (-1.0, -1.25, 0.02), (-0.9, -1.0, 0.02), (-1.4, -0.9, 0.02)], (0, 0, 0.02), "hay")     # Spilled grain.
    for _ in range(7):
        a, d = rnd.uniform(0, TAU), rnd.uniform(0.6, 1.5)
        mb.box((math.cos(a) * d, 0.4 + math.sin(a) * d * 0.7, 0.75 - d * 0.25), (0.25, 0.2, 0.12), rnd.choice(("plank_dark", "bone_dark", "hide_dark")), rotation_z=a)
    beam(mb, (0.2, 0.6, 0.7), (0.9, 1.2, 1.2), 0.03, "bone")
    bones = []
    for i, (x, y, rot) in enumerate(((0.2, -1.4, 20), (-0.9, -1.5, 160), (1.9, -1.2, -40))):   # Rats.
        b = "rat%d" % i
        start = mark(mb)
        mb.sphere((0, 0, 0.09), 0.09, "rat", {b: 1.0}, segments=6, rings=4, scale=(1.0, 1.9, 0.9))
        mb.sphere((0, -0.18, 0.11), 0.055, "rat", {b: 1.0}, segments=5, rings=4, scale=(1, 1.3, 1))
        for sx in (-1, 1):
            mb.sphere((sx * 0.04, -0.15, 0.17), 0.025, "hide_pale", {b: 1.0}, segments=4, rings=3)
        mb.cylinder((0, 0.16, 0.07), (0.06, 0.42, 0.03), 0.012, 0.004, "hide_pale", {b: 1.0}, segments=4)
        moved(mb, start, (x, y), rot)
        bones.append((b, (x, y, 0.09), (x, y - 0.2, 0.09), None))

    def scurry(t):
        return ({"rat%d" % i: [(kit.Z, 25 * math.sin(TAU * (i + 1) * t + i))] for i in range(3)},
                {"rat%d" % i: (0.25 * math.sin(TAU * t + i * 2), 0.15 * math.sin(TAU * 2 * t + i), 0) for i in range(3)})

    kit.save(mb, FAMILY, "lair_rat_burrow", COLORS, mech=kit.Mech(bones).clip("scurry", 3.0, scurry))


def whirlpool():
    """A sea monster's whirlpool: its waterline is Z = 0."""
    mb = kit.begin()
    bones = []
    for k, (r, mat) in enumerate(((5.0, "water"), (3.6, "water_deep"), (2.2, "water"), (1.0, "water_deep"))):
        b = "ring%d" % k
        mb.cylinder((0, 0, -0.1 - 0.25 * k), (0, 0, -0.05 - 0.25 * k), r, r, mat, {b: 1.0}, segments=10)
        for i in range(5):
            a0, a1 = TAU * i / 5 + k, TAU * (i + 0.5) / 5 + k
            solid(mb, [(math.cos(a0) * r * 0.95, math.sin(a0) * r * 0.95, -0.04 - 0.25 * k), (math.cos(a1) * r * 0.95, math.sin(a1) * r * 0.95, -0.04 - 0.25 * k),
                       (math.cos(a1) * r * 0.82, math.sin(a1) * r * 0.82, -0.04 - 0.25 * k), (math.cos(a0) * r * 0.86, math.sin(a0) * r * 0.86, -0.04 - 0.25 * k)],
                  (0, 0, 0.03), "foam", {b: 1.0})
        bones.append((b, (0, 0, -0.1 - 0.25 * k), (0, 0, 0.4), None))
    for i in range(5):   # Tentacles of what lives below.
        a = TAU * i / 5 + 0.3
        base = (math.cos(a) * 2.6, math.sin(a) * 2.6, -0.6)
        prev = None
        for s in range(4):
            b = "arm%d_%d" % (i, s)
            z0, z1 = -0.6 + 0.85 * s, -0.6 + 0.85 * (s + 1)
            out = 0.25 * s
            p0 = (base[0] + math.cos(a) * out * 0.3, base[1] + math.sin(a) * out * 0.3, z0)
            p1 = (base[0] + math.cos(a) * (out + 0.25) * 0.3, base[1] + math.sin(a) * (out + 0.25) * 0.3, z1)
            mb.cylinder(p0, p1, 0.34 - 0.075 * s, 0.34 - 0.075 * (s + 1) + 0.01, "tentacle", {b: 1.0}, segments=6)
            mb.sphere(((p0[0] + p1[0]) / 2 - math.cos(a) * 0.2, (p0[1] + p1[1]) / 2 - math.sin(a) * 0.2, (z0 + z1) / 2), 0.09 - 0.015 * s, "tentacle_light", {b: 1.0},
                      segments=5, rings=3)
            bones.append((b, p0, p1, prev))
            prev = b
    for a, d in ((1.0, 4.2), (3.9, 4.4)):   # Wreckage going round.
        mb.box((math.cos(a) * d, math.sin(a) * d, 0.05), (1.2, 0.25, 0.1), "plank_dark", {"ring0": 1.0}, rotation_z=a + 1.2)
    mb.cylinder((math.cos(5.2) * 3.9, math.sin(5.2) * 3.9, -0.2), (math.cos(5.2) * 3.9, math.sin(5.2) * 3.9, 0.3), 0.28, 0.28, "plank", {"ring0": 1.0}, segments=8)

    def churn(t):
        turns = {"ring%d" % k: [(kit.Z, 360.0 * (k + 1) * t)] for k in range(4)}
        for i in range(5):
            a = TAU * i / 5 + 0.3
            axis = (-math.sin(a), math.cos(a), 0)
            for s in range(4):
                turns["arm%d_%d" % (i, s)] = [(axis, (8 + 6 * s) * math.sin(TAU * t + i * 1.3 - 0.7 * s))]
        return turns, {}

    kit.save(mb, FAMILY, "lair_whirlpool", COLORS, mech=kit.Mech(bones).clip("churn", 8.0, churn))


def haunted_tree():
    mb = kit.begin()
    rnd = random.Random(14)
    mb.cylinder((0, 0, 0), (0.1, 0, 2.2), 0.9, 0.6, "bark_dead", segments=8)
    mb.cylinder((0.1, 0, 2.2), (-0.2, 0.1, 4.4), 0.6, 0.35, "bark_dead", segments=8)
    for a, z0, length, up in ((0.4, 3.6, 2.6, 1.6), (2.2, 3.2, 2.2, 1.9), (3.6, 4.0, 2.4, 1.2), (5.0, 3.4, 2.0, 2.0), (1.3, 4.3, 1.6, 2.2)):
        mid = (math.cos(a) * length * 0.6, math.sin(a) * length * 0.6, z0 + up * 0.5)
        tip = (math.cos(a + 0.4) * length, math.sin(a + 0.4) * length, z0 + up)
        beam(mb, (-0.1, 0.05, z0), mid, 0.16, "bark_dead")
        beam(mb, mid, tip, 0.09, "bark_dead")
        beam(mb, mid, (mid[0] + math.cos(a - 0.9) * 0.9, mid[1] + math.sin(a - 0.9) * 0.9, mid[2] + 0.7), 0.05, "bark_dead")
    for i in range(6):
        a = TAU * i / 6
        beam(mb, (math.cos(a) * 0.6, math.sin(a) * 0.6, 0.3), (math.cos(a) * 1.9, math.sin(a) * 1.9, 0.0), 0.16, "bark_dead")
    for sx in (-1, 1):   # A face in the bark.
        solid(mb, [(sx * 0.12, -0.78, 1.7), (sx * 0.4, -0.72, 1.85), (sx * 0.34, -0.74, 1.5)], (0, -0.04, 0), "cave")
        mb.box((sx * 0.27, -0.8, 1.68), (0.07, 0.03, 0.07), "glow_wisp")
    solid(mb, [(-0.3, -0.84, 1.0), (0.3, -0.84, 1.0), (0.22, -0.8, 0.7), (0, -0.82, 0.55), (-0.22, -0.8, 0.7)], (0, -0.04, 0), "cave")
    bones = []
    for i in range(5):   # Wisps that circle it.
        b, o = "wisp%d" % i, "orbit%d" % i
        r, z = 1.6 + 0.4 * (i % 3), 1.2 + 0.7 * i
        mb.sphere((r, 0, z), 0.12, "glow_wisp", {b: 1.0}, segments=6, rings=4)
        mb.cylinder((r, 0.1, z), (r, 0.45, z - 0.05), 0.07, 0.0, "glow_wisp", {b: 1.0}, segments=4)
        bones += [(o, (0, 0, z), (0, 0, z + 0.3), None), (b, (r, 0, z), (r, 0.2, z), o)]
    for sx, sy in ((-2.6, -1.4), (2.4, -1.8)):   # Old graves at its foot.
        solid(mb, [(sx - 0.3, sy, 0), (sx + 0.3, sy, 0), (sx + 0.3, sy, 0.7), (sx, sy, 0.9), (sx - 0.3, sy, 0.7)], (0, 0.12, 0), "dark_stone_light")
    skull(mb, 0.9, -1.2, 0.13, 1.0)

    def haunt(t):
        turns, moves = {}, {}
        for i in range(5):
            turns["orbit%d" % i] = [(kit.Z, 360.0 * (1 if i % 2 else -1) * ((i % 2) + 1) * t)]
            moves["wisp%d" % i] = (0, 0, 0.25 * math.sin(TAU * (2 + i % 2) * t + i))
        return turns, moves

    kit.save(mb, FAMILY, "lair_haunted_tree", COLORS, mech=kit.Mech(bones).clip("haunt", 8.0, haunt))


MODELS = {
    "lair_goblin_camp": goblin_camp,
    "lair_goblin_hut": goblin_hut("lair_goblin_hut", False),
    "lair_goblin_hut_mushroom": goblin_hut("lair_goblin_hut_mushroom", True),
    "lair_bandit_hideout": bandit_hideout,
    "lair_orc_war_camp": orc_war_camp,
    "lair_spider_nest": spider_nest("lair_spider_nest", False),
    "lair_spider_nest_cave": spider_nest("lair_spider_nest_cave", True),
    "lair_necromancer_altar": necromancer_altar,
    "lair_dragon_hoard": dragon_hoard,
    "lair_troll_cave": troll_cave,
    "lair_slime_pool": slime_pool,
    "lair_portal": portal,
    "lair_rat_burrow": rat_burrow,
    "lair_whirlpool": whirlpool,
    "lair_haunted_tree": haunted_tree,
}

kit.run(MODELS, FAMILY)
