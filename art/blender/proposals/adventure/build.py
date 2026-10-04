"""Adventure proposals: treasure to find, traps to set and the things a town
needs when sickness comes. See ../LEEME.md.

    blender --background --factory-startup --python art/blender/proposals/adventure/build.py -- [ids]
"""

import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import _kit as kit  # noqa: E402
import _shapes  # noqa: E402
import common  # noqa: E402
from _shapes import TAU, barrel, beam, log, mark, merged, moved, rock, rope, sack, shed_roof, solid  # noqa: E402

FAMILY = "adventure"
C = common.rgb
COLORS = {
    **_shapes.COLORS,
    "soil": C(0x6A4A30), "soil_dark": C(0x4A3422), "sand": C(0xE0CFA0), "grass": C(0x6A9440), "grass_dark": C(0x4F7A34), "leaf": C(0x4E7A34),
    "bone": C(0xE4DCC8), "eye": C(0x101010), "cave": C(0x14110F), "cloth_red": C(0xB8423A), "cloth_blue": C(0x3F5E8C), "cloth_yellow": C(0xE8C030),
    "cloth_black": C(0x2A262E), "canvas": C(0xE4D8B8), "canvas_shade": C(0xD0C29C), "parchment": C(0xE8D8A8), "clay": C(0xB06A48), "clay_dark": C(0x8E5236),
    "glow_relic": C(0xFFD060), "glow_gem": C(0x70E8F0), "gem_red": C(0xD03040), "net": C(0xC8C0A0), "wicker": C(0xB08A4A), "wicker_dark": C(0x8A6A34),
    "meat": C(0x9A4A34), "bell": C(0xB8923A), "herb": C(0x5A9A4A), "herb_flower": C(0xB07AD0), "smoke": C(0xB8B8B0), "ember": C(0xE85820),
    "water": C(0x4A8FC0), "steam": C(0xE8EEF2), "linen": C(0xECE6D6), "blanket": C(0x8A3A34), "bark_dead": C(0x8A8278), "barnacle": C(0xC8D0C0),
    "glass": C(0x7AD0C0), "thatch": C(0xC9A55A), "thatch_dark": C(0xA8863F), "flame": C(0xF08A24), "flame_core": C(0xFFF0B0),
}


# --- Treasure ------------------------------------------------------------------------------------


def chest_parts(mb, x, y, z, w, d, h, body, band, lid_bone, fill=True, s=1.0):
    """A chest with its lid weighted to `lid_bone` (hinged at the back); returns the bone."""
    mb.box((x, y, z + h / 2), (w, d, h), body)
    for sx in (-0.42, 0.0, 0.42):
        mb.box((x + sx * w, y, z + h / 2), (0.07 * s, d + 0.03, h + 0.02), band)
    mb.box((x, y, z + 0.03), (w + 0.04, d + 0.04, 0.06), band)
    if fill:
        mb.box((x, y, z + h - 0.02), (w - 0.1, d - 0.1, 0.06), "gold")
        mb.sphere((x - w * 0.2, y, z + h + 0.02), 0.07 * s, "gem_red", segments=5, rings=3)
        mb.sphere((x + w * 0.25, y + d * 0.1, z + h + 0.02), 0.06 * s, "glow_gem", segments=5, rings=3)
    wl = {lid_bone: 1.0}
    n = 5
    for i in range(n):   # A rounded lid.
        a0, a1 = math.pi * i / n, math.pi * (i + 1) / n
        solid(mb, [(x - w / 2 - 0.01, y + math.cos(a0) * d / 2, z + h + math.sin(a0) * d * 0.4), (x + w / 2 + 0.01, y + math.cos(a0) * d / 2, z + h + math.sin(a0) * d * 0.4),
                   (x + w / 2 + 0.01, y + math.cos(a1) * d / 2, z + h + math.sin(a1) * d * 0.4), (x - w / 2 - 0.01, y + math.cos(a1) * d / 2, z + h + math.sin(a1) * d * 0.4)],
              (0, -math.cos((a0 + a1) / 2) * 0.05, -math.sin((a0 + a1) / 2) * 0.05), body, wl)
    for sx in (-1, 1):
        solid(mb, [(x + sx * w / 2, y - d / 2, z + h), (x + sx * w / 2, y + d / 2, z + h), (x + sx * w / 2, y + d * 0.3, z + h + d * 0.32), (x + sx * w / 2, y, z + h + d * 0.4),
                   (x + sx * w / 2, y - d * 0.3, z + h + d * 0.32)], (-sx * 0.04, 0, 0), body, wl)
        mb.box((x + sx * 0.42 * w, y, z + h + d * 0.2), (0.07 * s, d + 0.05, d * 0.42), band, wl)
    mb.box((x, y - d / 2 - 0.02, z + h - 0.02), (0.12 * s, 0.04, 0.16 * s), "gold" if band != "gold" else "iron", wl)
    return (lid_bone, (x, y + d / 2, z + h), (x, y + d / 2 + 0.3, z + h), None)


def lid_clips(mech, bone, angle=100.0):
    mech.clip("open", 1.2, lambda t: ({bone: [(kit.X, -angle * kit.smooth(t))]}, {}), loops=False)
    mech.clip("close", 1.0, lambda t: ({bone: [(kit.X, -angle * (1 - kit.smooth(t)))]}, {}), loops=False)
    return mech


def chest(name, body, band):
    def build():
        mb = kit.begin()
        bone = chest_parts(mb, 0, 0, 0, 0.95, 0.6, 0.5, body, band, "lid")
        kit.save(mb, FAMILY, name, COLORS, mech=lid_clips(kit.Mech([bone]), "lid"))
    return build


def buried():
    mb = kit.begin()
    rnd = random.Random(1)
    mb.sphere((0, 0, 0), 1.3, "soil", segments=8, rings=4, scale=(1.1, 1.0, 0.3))
    mb.box((0, 0, 0.12), (0.9, 0.55, 0.4), "cave")
    start = mark(mb)
    bone = chest_parts(mb, 0, 0, 0, 0.8, 0.5, 0.42, "plank_dark", "iron", "lid", fill=False, s=0.85)
    moved(mb, start, (0, 0.0, -0.12), 8)
    mb.sphere((1.2, 0.3, 0.0), 0.7, "soil_dark", segments=7, rings=4, scale=(1, 1.2, 0.55))
    beam(mb, (1.0, -0.4, 0.3), (1.35, -0.9, 1.5), 0.02, "pole")
    mb.box((1.0, -0.4, 0.4), (0.2, 0.03, 0.28), "steel")
    for a in (0.785, 2.356):   # The X that marked the spot.
        beam(mb, (-1.6 + math.cos(a) * 0.4, -0.9 + math.sin(a) * 0.4, 0.03), (-1.6 - math.cos(a) * 0.4, -0.9 - math.sin(a) * 0.4, 0.03), 0.035, "cloth_red")
    solid(mb, [(-1.3, 0.7, 0.03), (-0.8, 0.8, 0.03), (-0.85, 1.15, 0.03), (-1.35, 1.05, 0.03)], (0, 0, 0.012), "parchment")
    for _ in range(4):
        rock(mb, rnd.uniform(-1.4, 1.4), rnd.uniform(-1.3, -1.0), 0.06, 0.12, rnd)
    kit.save(mb, FAMILY, "loot_buried", COLORS)


def strongbox():
    mb = kit.begin()
    mb.box((0, 0, 0.2), (0.6, 0.42, 0.4), "iron")
    for sx in (-0.3, 0.3):
        for sy in (-0.21, 0.21):
            mb.box((sx, sy, 0.2), (0.06, 0.06, 0.42), "steel")
    for zz in (0.04, 0.2, 0.37):
        mb.box((0, 0, zz), (0.63, 0.45, 0.04), "steel")
    mb.box((0, -0.23, 0.2), (0.12, 0.05, 0.14), "gold")
    for i in range(4):
        a0, a1 = math.pi * i / 4, math.pi * (i + 1) / 4
        beam(mb, (math.cos(a0) * 0.05, -0.24, 0.28 + math.sin(a0) * 0.06), (math.cos(a1) * 0.05, -0.24, 0.28 + math.sin(a1) * 0.06), 0.012, "steel")
    for sx in (-1, 1):
        for i in range(4):
            a0, a1 = math.pi * i / 4, math.pi * (i + 1) / 4
            beam(mb, (sx * 0.31, math.cos(a0) * 0.1, 0.3 + math.sin(a0) * 0.08), (sx * 0.31, math.cos(a1) * 0.1, 0.3 + math.sin(a1) * 0.08), 0.014, "steel")
    kit.save(mb, FAMILY, "loot_strongbox", COLORS)


def urns():
    mb = kit.begin()
    rnd = random.Random(3)

    def urn(x, y, s, broken=False, lean=0.0):
        prof = [(0.1, 0.0), (0.2, 0.15), (0.24, 0.35), (0.16, 0.55), (0.08, 0.62), (0.11, 0.72)]
        top = 4 if broken else len(prof)
        for (r0, z0), (r1, z1) in zip(prof[:top], prof[1:top]):
            mb.cylinder((x + lean * z0, y, z0 * s), (x + lean * z1, y, z1 * s), r0 * s, r1 * s, "clay" if z0 < 0.3 else "clay_dark", segments=8)
        if not broken:
            for sx in (-1, 1):
                beam(mb, (x + sx * 0.09 * s, y, 0.66 * s), (x + sx * 0.2 * s, y, 0.5 * s), 0.02 * s, "clay_dark")
        else:
            for k in range(4):
                a = TAU * k / 4 + 0.5
                solid(mb, [(x + math.cos(a) * 0.35 * s, y + math.sin(a) * 0.35 * s, 0.02), (x + math.cos(a + 0.5) * 0.4 * s, y + math.sin(a + 0.5) * 0.4 * s, 0.02),
                           (x + math.cos(a + 0.25) * 0.5 * s, y + math.sin(a + 0.25) * 0.5 * s, 0.05)], (0, 0, 0.02), "clay")

    urn(0, 0, 1.4)
    urn(0.6, -0.2, 1.0)
    urn(-0.55, 0.15, 1.1, broken=True)
    urn(0.2, 0.55, 0.9, lean=0.2)
    for _ in range(9):
        a, d = rnd.uniform(0, TAU), rnd.uniform(0.3, 0.75)
        mb.cylinder((-0.55 + math.cos(a) * d * 0.5, 0.15 + math.sin(a) * d * 0.5, 0.02), (-0.55 + math.cos(a) * d * 0.5, 0.15 + math.sin(a) * d * 0.5, 0.04), 0.045, 0.045, "gold", segments=6)
    mb.sphere((-0.5, 0.2, 0.3), 0.07, "gem_red", segments=5, rings=3)
    kit.save(mb, FAMILY, "loot_urns", COLORS)


def lost_backpack():
    mb = kit.begin()
    rnd = random.Random(4)
    mb.sphere((0, 0, 0.3), 0.3, "leather", segments=7, rings=5, scale=(1.1, 0.8, 1.3))
    mb.box((0, -0.22, 0.25), (0.34, 0.08, 0.26), "plank_dark")
    mb.cylinder((-0.3, 0, 0.72), (0.3, 0, 0.72), 0.1, 0.1, "cloth_blue", segments=8)
    for sx in (-0.15, 0.15):
        mb.cylinder((sx - 0.02, 0, 0.72), (sx + 0.02, 0, 0.72), 0.105, 0.105, "rope", segments=8)
    mb.cylinder((0.35, 0.1, 0.05), (0.75, -0.2, 0.05), 0.035, 0.035, "parchment", segments=6)
    mb.cylinder((-0.5, -0.4, 0.0), (-0.5, -0.4, 0.22), 0.07, 0.08, "leather", segments=6)     # A boot.
    mb.box((-0.5, -0.5, 0.05), (0.13, 0.2, 0.09), "leather")
    # The one who carried it.
    mb.sphere((0.9, 0.7, 0.13), 0.14, "bone", segments=6, rings=5)
    for sx in (-1, 1):
        mb.box((0.9 + sx * 0.05, 0.58, 0.14), (0.045, 0.03, 0.05), "eye")
    for k in range(5):
        beam(mb, (0.9 - 0.2 + 0.1 * k, 0.9, 0.05), (0.9 - 0.25 + 0.12 * k, 1.35, 0.14), 0.02, "bone")
    beam(mb, (0.9, 0.85, 0.06), (0.9, 1.7, 0.06), 0.03, "bone")
    for sx in (-1, 1):
        beam(mb, (0.9 + sx * 0.1, 1.7, 0.05), (0.9 + sx * 0.3, 2.3, 0.05), 0.03, "bone")
        beam(mb, (0.9 + sx * 0.2, 0.95, 0.05), (0.9 + sx * 0.55, 1.3 + 0.2 * sx, 0.05), 0.025, "bone")
    mb.cylinder((1.5, 1.2, 0.02), (1.3, 0.3, 0.05), 0.02, 0.02, "steel", segments=4)
    for _ in range(3):
        mb.sphere((rnd.uniform(-0.6, 1.6), rnd.uniform(-0.6, 2.2), 0.05), 0.2, "grass_dark", segments=5, rings=3, scale=(1, 1, 0.4))
    kit.save(mb, FAMILY, "loot_lost_backpack", COLORS)


def washed_crate():
    mb = kit.begin()
    rnd = random.Random(5)
    mb.sphere((0, 0, -0.02), 1.3, "sand", segments=9, rings=4, scale=(1.2, 1.0, 0.1))
    start = mark(mb)
    _shapes.crate(mb, 0, 0, -0.18, 0.8)
    moved(mb, start, (0, 0), 20)
    for _ in range(10):
        a = rnd.uniform(0, TAU)
        mb.sphere((math.cos(a) * 0.42, math.sin(a) * 0.42, rnd.uniform(0.05, 0.4)), 0.05, "barnacle", segments=5, rings=3)
    mb.cylinder((0.9, -0.5, 0.06), (1.2, -0.3, 0.1), 0.07, 0.07, "glass", segments=7)          # A bottle with a message.
    mb.cylinder((1.2, -0.3, 0.1), (1.32, -0.22, 0.12), 0.03, 0.025, "glass", segments=6)
    mb.cylinder((0.95, -0.47, 0.065), (1.12, -0.36, 0.09), 0.03, 0.03, "parchment", segments=5)
    log(mb, (-1.3, 0.4, 0.08), (-0.4, 0.9, 0.12), 0.09, mat="bark_dead")
    rope(mb, (-0.35, -0.3, 0.3), (-1.0, -0.8, 0.03), 0.03)
    kit.save(mb, FAMILY, "loot_washed_crate", COLORS)


def relic():
    mb = kit.begin()
    for k in range(3):
        mb.cylinder((0, 0, 0.14 * k), (0, 0, 0.14 * (k + 1)), 0.9 - 0.2 * k, 0.85 - 0.2 * k, "stone" if k % 2 else "stone_light", segments=8)
    mb.cylinder((0, 0, 0.42), (0, 0, 1.2), 0.2, 0.16, "stone_dark", segments=6)
    mb.cylinder((0, 0, 1.2), (0, 0, 1.3), 0.3, 0.3, "stone_light", segments=6)
    w = {"relic": 1.0}
    mb.cylinder((0, 0, 1.55), (0, 0, 1.75), 0.0, 0.17, "glow_relic", w, segments=6)
    mb.cylinder((0, 0, 1.75), (0, 0, 2.1), 0.17, 0.0, "glow_relic", w, segments=6)
    for i in range(3):
        a = TAU * i / 3
        mb.cylinder((math.cos(a) * 0.4, math.sin(a) * 0.4, 1.7), (math.cos(a) * 0.4, math.sin(a) * 0.4, 1.9), 0.05, 0.0, "glow_gem", {"ring": 1.0}, segments=4)
        mb.cylinder((math.cos(a) * 0.4, math.sin(a) * 0.4, 1.6), (math.cos(a) * 0.4, math.sin(a) * 0.4, 1.7), 0.0, 0.05, "glow_gem", {"ring": 1.0}, segments=4)
    for i in range(4):
        a = TAU * i / 4 + 0.4
        mb.box((math.cos(a) * 0.62, math.sin(a) * 0.62, 0.3), (0.1, 0.03, 0.14), "glow_gem", rotation_z=a + math.pi / 2)
    pose = lambda t: ({"relic": [(kit.Z, 360 * t)], "ring": [(kit.Z, -720 * t)]}, {"relic": (0, 0, 0.08 * math.sin(TAU * 2 * t)), "ring": (0, 0, 0.05 * math.sin(TAU * 2 * t + 1))})   # noqa: E731
    mech = kit.Mech([("relic", (0, 0, 1.75), (0, 0, 2.1), None), ("ring", (0, 0, 1.75), (0, 0, 2.0), None)]).clip("float", 6.0, pose)
    kit.save(mb, FAMILY, "loot_relic", COLORS, mech=mech)


# --- Traps ----------------------------------------------------------------------------------------


def bear_trap():
    mb = kit.begin()
    mb.cylinder((0, 0, 0.0), (0, 0, 0.03), 0.34, 0.34, "iron", segments=10)
    mb.cylinder((0, 0, 0.03), (0, 0, 0.05), 0.14, 0.14, "steel", segments=8)
    bones = []
    for side, bone in ((-1, "jaw_l"), (1, "jaw_r")):
        w = {bone: 1.0}
        n = 7
        for i in range(n):   # A half ring of teeth lying open.
            a0, a1 = math.pi * i / n, math.pi * (i + 1) / n
            p0 = (side * math.sin(a0) * 0.36, math.cos(a0) * 0.36, 0.05)
            p1 = (side * math.sin(a1) * 0.36, math.cos(a1) * 0.36, 0.05)
            beam(mb, p0, p1, 0.022, "iron", w)
            mid = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2, 0.05)
            mb.cylinder(mid, (mid[0] * 0.98, mid[1] * 0.98, 0.16), 0.02, 0.0, "steel", w, segments=4)
        bones.append((bone, (0, 0, 0.05), (0, 0.3, 0.05), None))
    for k in range(5):   # The chain and its stake.
        mb.box((0.4 + 0.1 * k, 0.05 * (k % 2), 0.03), (0.09, 0.05, 0.03), "iron", rotation_z=0.3 * (k % 2))
    mb.cylinder((0.95, 0.05, 0), (0.95, 0.05, 0.25), 0.03, 0.02, "pole_dark", segments=5)
    mb.box((-0.02, 0, 0.07), (0.1, 0.08, 0.05), "meat")

    def snap(t):
        s = min(1.0, t / 0.15) ** 2
        return {"jaw_l": [(kit.Y, 85.0 * s)], "jaw_r": [(kit.Y, -85.0 * s)]}, {}

    kit.save(mb, FAMILY, "trap_bear", COLORS, mech=kit.Mech(bones).clip("snap", 1.0, snap, loops=False))


def snare():
    mb = kit.begin()
    mb.cylinder((0, 0, 0), (0, 0, 0.5), 0.06, 0.05, "bark", segments=6)
    bones, prev = [], None
    n = 5
    for k in range(n):   # A sapling bent over, held by a peg.
        b = "bend%d" % k
        a0, a1 = 1.3 * k / n, 1.3 * (k + 1) / n
        p0 = (math.sin(a0) * 1.4, 0, 0.5 + 1.3 * math.sin(a0 * 0.9))
        p1 = (math.sin(a1) * 1.4, 0, 0.5 + 1.3 * math.sin(a1 * 0.9))
        mb.cylinder(p0, p1, 0.045 - 0.006 * k, 0.045 - 0.006 * (k + 1), "bark", {b: 1.0}, segments=5)
        if k > 2:
            mb.sphere(((p0[0] + p1[0]) / 2, 0.1, (p0[2] + p1[2]) / 2), 0.14, "leaf", {b: 1.0}, segments=5, rings=3)
        bones.append((b, p0, p1, prev))
        prev = b
    tip = (math.sin(1.3) * 1.4, 0, 0.5 + 1.3 * math.sin(1.3 * 0.9))
    w = {prev: 1.0}
    rope(mb, tip, (tip[0] + 0.25, 0, 0.3), 0.012, w)
    for i in range(8):   # The noose on the ground.
        a0, a1 = TAU * i / 8, TAU * (i + 1) / 8
        beam(mb, (tip[0] + 0.25 + math.cos(a0) * 0.2, math.sin(a0) * 0.2, 0.28), (tip[0] + 0.25 + math.cos(a1) * 0.2, math.sin(a1) * 0.2, 0.28), 0.012, "rope", w)
    mb.cylinder((tip[0] + 0.5, 0, 0), (tip[0] + 0.5, 0, 0.3), 0.03, 0.02, "pole_dark", segments=5)
    mb.sphere((tip[0] + 0.25, 0.0, 0.05), 0.06, "meat", segments=5, rings=3)

    def spring(t):
        s = min(1.0, t / 0.2) ** 2
        wobble = 6.0 * math.sin((t - 0.2) * 25) * max(0.0, 1 - t) if t > 0.2 else 0.0
        return {"bend%d" % k: [(kit.Y, -(13.0 * s) + (wobble if k else 0.0))] for k in range(n)}, {}

    kit.save(mb, FAMILY, "trap_snare", COLORS, mech=kit.Mech(bones).clip("spring", 1.5, spring, loops=False))


def net_trap():
    mb = kit.begin()
    mb.cylinder((-2.2, 0, 0), (-2.1, 0, 4.2), 0.2, 0.12, "bark", segments=7)
    beam(mb, (-2.1, 0, 3.9), (0.3, 0, 4.3), 0.09, "bark")
    for a, z in ((0.8, 3.2), (2.6, 3.6), (4.2, 3.0)):
        beam(mb, (-2.12, 0, z), (-2.12 + math.cos(a) * 1.0, math.sin(a) * 1.0, z + 0.5), 0.05, "bark")
        mb.sphere((-2.12 + math.cos(a) * 1.1, math.sin(a) * 1.1, z + 0.6), 0.5, "leaf", segments=6, rings=4)
    w = {"net": 1.0}
    n = 8
    for i in range(n):   # The net spread on the ground, its corners gathered to one rope.
        a0, a1 = TAU * i / n, TAU * (i + 1) / n
        solid(mb, [(0, 0, 0.05), (math.cos(a0) * 1.2, math.sin(a0) * 1.2, 0.05), (math.cos(a1) * 1.2, math.sin(a1) * 1.2, 0.05)], (0, 0, 0.015), "net" if i % 2 else "wicker", w)
        if i % 2 == 0:
            rope(mb, (math.cos(a0) * 1.2, math.sin(a0) * 1.2, 0.06), (0.25, 0, 4.2), 0.012, w)
    mb.sphere((0, 0, 0.08), 0.5, "grass_dark", w, segments=6, rings=3, scale=(1.4, 1.4, 0.15))   # Leaves that hide it.
    mb.sphere((0.1, 0.1, 0.14), 0.07, "meat", w, segments=5, rings=3)

    def lift(t):
        s = kit.smooth(min(1.0, t / 0.4))
        return {"net": [(kit.Z, 40 * s + 8 * math.sin(TAU * 2 * t) * (t > 0.4))]}, {"net": (0, 0, 2.2 * s)}

    kit.save(mb, FAMILY, "trap_net", COLORS, mech=kit.Mech([("net", (0, 0, 0.05), (0, 0, 1.0), None)]).clip("lift", 2.5, lift, loops=False))


def log_swing():
    mb = kit.begin()
    for sx in (-1.6, 1.6):
        log(mb, (sx, -0.5, 0), (sx, 0, 3.6), 0.11)
        log(mb, (sx, 0.5, 0), (sx, 0, 3.6), 0.11)
    log(mb, (-1.9, 0, 3.6), (1.9, 0, 3.6), 0.1)
    w = {"log": 1.0}
    for sx in (-1.0, 1.0):
        rope(mb, (sx, 0, 3.55), (sx, 0, 1.3), 0.025, w)
    log(mb, (-1.5, 0, 1.2), (1.5, 0, 1.2), 0.28, w)
    for sx in (-1.5, -0.75, 0.0, 0.75, 1.5):
        for a in (0.0, 2.1, 4.2):
            mb.cylinder((sx, math.cos(a) * 0.25, 1.2 + math.sin(a) * 0.25), (sx, math.cos(a) * 0.55, 1.2 + math.sin(a) * 0.55), 0.05, 0.0, "steel", w, segments=4)
    beam(mb, (2.4, -1.5, 0.15), (-2.4, -1.5, 0.15), 0.01, "rope")                             # The tripwire.
    for sx in (-2.4, 2.4):
        mb.cylinder((sx, -1.5, 0), (sx, -1.5, 0.25), 0.03, 0.02, "pole_dark", segments=5)
    pose = lambda t: ({"log": [(kit.X, 48 * math.sin(TAU * t))]}, {})   # noqa: E731
    kit.save(mb, FAMILY, "trap_log_swing", COLORS, mech=kit.Mech([("log", (0, 0, 3.55), (0, 0, 1.2), None)]).clip("swing", 2.4, pose))


def alarm_wire():
    mb = kit.begin()
    for sx in (-2.0, 0.0, 2.0):
        mb.cylinder((sx, 0, 0), (sx, 0, 0.9), 0.04, 0.03, "pole_dark", segments=5)
    w = {"wire": 1.0}
    rope(mb, (-2.0, 0, 0.8), (2.0, 0, 0.8), 0.01, w)
    rope(mb, (-2.0, 0, 0.3), (2.0, 0, 0.3), 0.01)
    for i in range(7):
        x = -1.7 + 0.55 * i
        if i % 2:
            mb.cylinder((x, 0, 0.8), (x, 0, 0.62), 0.03, 0.07, "bell", w, segments=7)
            mb.sphere((x, 0, 0.6), 0.02, "iron", w, segments=4, rings=3)
        else:
            mb.cylinder((x, 0, 0.78), (x, 0, 0.6), 0.05, 0.05, "steel", w, segments=6)
            mb.cylinder((x, 0, 0.8), (x, 0, 0.78), 0.006, 0.006, "rope", w, segments=3)
    solid(mb, [(2.0, -0.02, 0.9), (2.5, -0.02, 0.75), (2.0, -0.02, 0.6)], (0, 0.02, 0), "cloth_red")
    pose = lambda t: ({"wire": [(kit.X, 12 * math.sin(TAU * 6 * t) * max(0.0, 1 - t))]}, {"wire": (0, 0, 0.04 * math.sin(TAU * 8 * t) * max(0.0, 1 - t))})   # noqa: E731
    kit.save(mb, FAMILY, "trap_alarm_wire", COLORS, mech=kit.Mech([("wire", (0, 0, 0.8), (1.0, 0, 0.8), None)]).clip("ring", 2.0, pose, loops=False))


def cage_trap():
    mb = kit.begin()
    w_, d_, h_ = 1.6, 2.2, 1.3
    mb.box((0, 0, 0.04), (w_, d_, 0.08), "plank_dark")
    for sx in (-1, 1):
        for k in range(8):
            y = -d_ / 2 + d_ * k / 7
            mb.cylinder((sx * w_ / 2, y, 0.08), (sx * w_ / 2, y, h_), 0.035, 0.035, "pole", segments=5)
        beam(mb, (sx * w_ / 2, -d_ / 2, h_), (sx * w_ / 2, d_ / 2, h_), 0.045, "pole_dark")
    for k in range(6):
        x = -w_ / 2 + w_ * k / 5
        mb.cylinder((x, d_ / 2, 0.08), (x, d_ / 2, h_), 0.035, 0.035, "pole", segments=5)
        beam(mb, (x, -d_ / 2, h_), (x, d_ / 2, h_), 0.03, "pole")
    for sx in (-1, 1):                                                                 # Guides for the door.
        mb.cylinder((sx * w_ / 2, -d_ / 2, 0), (sx * w_ / 2, -d_ / 2, 2.6), 0.05, 0.045, "pole_dark", segments=6)
    beam(mb, (-w_ / 2, -d_ / 2, 2.6), (w_ / 2, -d_ / 2, 2.6), 0.045, "pole_dark")
    w = {"door": 1.0}
    for k in range(6):
        x = -w_ / 2 + 0.14 + (w_ - 0.28) * k / 5
        mb.cylinder((x, -d_ / 2, 1.35), (x, -d_ / 2, 2.55), 0.035, 0.035, "pole", w, segments=5)
    for zz in (1.4, 2.5):
        beam(mb, (-w_ / 2 + 0.1, -d_ / 2, zz), (w_ / 2 - 0.1, -d_ / 2, zz), 0.04, "pole_dark", w)
    rope(mb, (0, -d_ / 2, 2.55), (0, -d_ / 2, 2.62), 0.012, w)
    rope(mb, (0, -d_ / 2, 2.62), (0, 0.6, 1.25), 0.012)
    mb.box((0, 0.6, 0.14), (0.3, 0.2, 0.12), "meat")                                     # The bait, on its trigger.
    mb.cylinder((0, 0.6, 0.08), (0, 0.6, 1.25), 0.015, 0.015, "pole", segments=4)

    def drop(t):
        s = min(1.0, t / 0.25) ** 2
        bounce = 0.05 * math.sin((t - 0.25) * 30) * max(0.0, 0.6 - t) if t > 0.25 else 0.0
        return {}, {"door": (0, 0, -1.27 * s + bounce)}

    kit.save(mb, FAMILY, "trap_cage", COLORS, mech=kit.Mech([("door", (0, -d_ / 2, 1.4), (0, -d_ / 2, 2.5), None)]).clip("drop", 1.2, drop, loops=False))


def fish_trap():
    """A wicker creel in shallow water behind a V of stakes: its waterline is Z = 0."""
    mb = kit.begin()
    for side in (-1, 1):
        for k in range(7):
            x, y = side * (0.3 + 0.3 * k), -0.2 - 0.35 * k
            mb.cylinder((x, y, -0.6), (x, y, 0.35), 0.035, 0.03, "pole_dark", segments=5)
        beam(mb, (side * 0.3, -0.2, 0.15), (side * 2.1, -2.3, 0.15), 0.02, "wicker_dark")
        beam(mb, (side * 0.3, -0.2, -0.2), (side * 2.1, -2.3, -0.2), 0.02, "wicker_dark")
    n = 8
    for i in range(n):   # The creel: a cone of wicker lying under the water.
        a0, a1 = TAU * i / n, TAU * (i + 1) / n
        solid(mb, [(math.cos(a0) * 0.3, -0.1, -0.2 + math.sin(a0) * 0.3), (math.cos(a1) * 0.3, -0.1, -0.2 + math.sin(a1) * 0.3), (math.cos(a1) * 0.12, 1.2, -0.2 + math.sin(a1) * 0.12),
                   (math.cos(a0) * 0.12, 1.2, -0.2 + math.sin(a0) * 0.12)], (0, 0, 0.012), "wicker" if i % 2 else "wicker_dark")
    for yy in (0.2, 0.6, 1.0):
        r = 0.3 - 0.18 * (yy + 0.1) / 1.3
        for i in range(n):
            a0, a1 = TAU * i / n, TAU * (i + 1) / n
            beam(mb, (math.cos(a0) * r, yy, -0.2 + math.sin(a0) * r), (math.cos(a1) * r, yy, -0.2 + math.sin(a1) * r), 0.012, "wicker_dark")
    rope(mb, (0, 1.2, -0.2), (0.6, 1.9, 0.3), 0.012)
    mb.cylinder((0.6, 1.9, -0.5), (0.6, 1.9, 0.5), 0.04, 0.035, "pole", segments=5)
    kit.save(mb, FAMILY, "trap_fish", COLORS)


# --- Sickness -------------------------------------------------------------------------------------


def cot(mb, x, y, mat="blanket"):
    mb.box((x, y, 0.3), (0.8, 1.9, 0.07), "plank")
    for sx in (-0.35, 0.35):
        for sy in (-0.85, 0.85):
            mb.box((x + sx, y + sy, 0.15), (0.06, 0.06, 0.3), "plank_dark")
    mb.box((x, y + 0.15, 0.38), (0.74, 1.45, 0.08), mat)
    mb.box((x, y - 0.72, 0.4), (0.5, 0.3, 0.1), "linen")


def quarantine_tent():
    mb = kit.begin()
    w_, d_, h_ = 3.2, 4.0, 2.4
    for y in (-d_ / 2, d_ / 2):
        for sx in (-1, 1):
            mb.cylinder((sx * (w_ / 2 + 0.05), y, 0), (-sx * 0.08, y, h_ + 0.2), 0.05, 0.04, "pole", segments=6)
    mb.cylinder((0, -d_ / 2 - 0.3, h_), (0, d_ / 2 + 0.3, h_), 0.05, 0.05, "pole_dark", segments=6)
    for sx in (-1, 1):
        for i in range(4):
            y0, y1 = -d_ / 2 + d_ * i / 4, -d_ / 2 + d_ * (i + 1) / 4
            n = (sx * (h_ - 0.14), 0, w_ / 2)
            length = math.hypot(n[0], n[2])
            n = (n[0] / length * 0.035, 0, n[2] / length * 0.035)
            solid(mb, [(sx * w_ / 2, y0, 0.14), (sx * w_ / 2, y1, 0.14), (0, y1, h_ + 0.03), (0, y0, h_ + 0.03)], n, "canvas" if i % 2 else "canvas_shade")
    solid(mb, [(-w_ / 2, d_ / 2, 0.14), (w_ / 2, d_ / 2, 0.14), (0, d_ / 2, h_)], (0, 0.035, 0), "canvas_shade")
    for sx in (-1, 1):
        solid(mb, [(sx * w_ / 2, -d_ / 2, 0.14), (sx * w_ * 0.22, -d_ / 2 - 0.15, 0.14), (0, -d_ / 2, h_)], (0, -0.035, 0), "canvas")
    cot(mb, -0.7, 0.5)
    cot(mb, 0.7, 0.5, "cloth_blue")
    # A rope around it and the yellow flag that warns.
    posts = [(-3.0, -3.2), (3.0, -3.2), (3.0, 3.0), (-3.0, 3.0)]
    for i, (x, y) in enumerate(posts):
        mb.cylinder((x, y, 0), (x, y, 1.0), 0.04, 0.035, "pole_dark", segments=5)
        nx, ny = posts[(i + 1) % 4]
        if i != 0:
            rope(mb, (x, y, 0.9), (nx, ny, 0.9), 0.015)
        else:
            rope(mb, (x, y, 0.9), (-1.0, y, 0.9), 0.015)
            rope(mb, (1.0, y, 0.9), (nx, ny, 0.9), 0.015)
    mb.cylinder((1.0, -3.2, 0), (1.0, -3.2, 3.0), 0.045, 0.035, "pole", segments=6)
    w = {"flag": 1.0}
    solid(mb, [(1.0, -3.18, 2.95), (1.9, -3.18, 2.95), (1.9, -3.18, 2.35), (1.0, -3.18, 2.35)], (0, 0.02, 0), "cloth_yellow", w)
    solid(mb, [(1.2, -3.19, 2.8), (1.7, -3.19, 2.8), (1.7, -3.19, 2.5), (1.2, -3.19, 2.5)], (0, 0.04, 0), "cloth_black", w)
    mb.cylinder((-1.4, -2.6, 0), (-1.4, -2.6, 0.35), 0.18, 0.22, "plank_light", segments=8)       # Water and food left at the rope.
    mb.cylinder((-1.4, -2.6, 0.3), (-1.4, -2.6, 0.33), 0.19, 0.19, "water", segments=8)
    sack(mb, -1.9, -2.7, 0.0, 0.2)
    pose = lambda t: ({"flag": [(kit.Z, 14 * math.sin(TAU * 2 * t)), (kit.X, 4 * math.sin(TAU * t))]}, {})   # noqa: E731
    kit.save(mb, FAMILY, "health_quarantine_tent", COLORS, mech=kit.Mech([("flag", (1.0, -3.18, 2.65), (1.9, -3.18, 2.65), None)]).clip("wave", 2.0, pose))


def infirmary():
    mb = kit.begin()
    for sx in (-2.6, 0.0, 2.6):
        mb.cylinder((sx, -1.2, 0), (sx, -1.2, 2.1), 0.07, 0.06, "pole", segments=6)
        mb.cylinder((sx, 1.3, 0), (sx, 1.3, 2.8), 0.07, 0.06, "pole", segments=6)
    for k in range(7):
        mb.box((0, 1.33, 0.2 + 0.36 * k), (5.3, 0.04, 0.32), "plank" if k % 2 else "plank_light")
    shed_roof(mb, 0, 0.05, 5.4, 2.5, 2.1, 2.8, ("thatch", "thatch_dark"), 0.3, 4)
    mb.box((0, 0.05, 0.03), (5.2, 2.4, 0.06), "plank_dark")
    for i, x in enumerate((-1.75, 0.0, 1.75)):
        cot(mb, x, 0.2, ("blanket", "cloth_blue", "linen")[i])
    mb.box((2.3, -0.9, 0.4), (0.5, 0.5, 0.8), "plank")                                          # A table of remedies.
    for k in range(3):
        mb.cylinder((2.15 + 0.15 * k, -0.9, 0.8), (2.15 + 0.15 * k, -0.9, 0.98), 0.04, 0.03, ("glass", "clay", "glass")[k], segments=6)
    mb.cylinder((-2.3, -1.0, 0), (-2.3, -1.0, 0.3), 0.16, 0.2, "plank_light", segments=8)
    mb.cylinder((-2.3, -1.0, 0.26), (-2.3, -1.0, 0.29), 0.17, 0.17, "water", segments=8)
    for k in range(5):                                                                       # Herbs drying under the eave.
        mb.cylinder((-2.0 + 1.0 * k, -1.15, 2.05), (-2.0 + 1.0 * k, -1.15, 1.7), 0.02, 0.07, "herb", segments=5)
    solid(mb, [(-2.6, -1.25, 2.0), (-2.6, -1.25, 1.5), (-2.2, -1.25, 1.5), (-2.2, -1.25, 2.0)], (0, -0.02, 0), "linen")
    solid(mb, [(-2.45, -1.28, 1.9), (-2.35, -1.28, 1.9), (-2.35, -1.28, 1.6), (-2.45, -1.28, 1.6)], (0, -0.01, 0), "cloth_red")
    solid(mb, [(-2.55, -1.28, 1.8), (-2.25, -1.28, 1.8), (-2.25, -1.28, 1.7), (-2.55, -1.28, 1.7)], (0, -0.01, 0), "cloth_red")
    kit.save(mb, FAMILY, "health_infirmary", COLORS)


def fumigation():
    mb = kit.begin()
    mb.cylinder((0, 0, 0), (0, 0, 0.9), 0.07, 0.06, "iron", segments=6)
    for i in range(3):
        a = TAU * i / 3
        beam(mb, (0, 0, 0.3), (math.cos(a) * 0.4, math.sin(a) * 0.4, 0.0), 0.03, "iron")
    mb.cylinder((0, 0, 0.9), (0, 0, 1.15), 0.16, 0.34, "iron", segments=8)
    mb.cylinder((0, 0, 1.1), (0, 0, 1.16), 0.3, 0.3, "ember", segments=8)
    for k in range(4):
        mb.cylinder((0.12 * math.cos(k * 1.6), 0.12 * math.sin(k * 1.6), 1.14), (0.2 * math.cos(k * 1.6), 0.2 * math.sin(k * 1.6), 1.32), 0.04, 0.07, "herb", segments=5)
    bones = []
    for i in range(3):
        b = "smoke%d" % i
        for k in range(3):
            mb.sphere((0.1 * k * (1 if i % 2 else -1), 0, 1.5 + 0.5 * k), 0.22 + 0.08 * k, "smoke", {b: 1.0}, segments=6, rings=4, scale=(1, 1, 0.8))
        bones.append((b, (0, 0, 1.3), (0, 0, 2.0), None))
    for sx in (-1.4, 1.4):                                                                   # Bundles of herbs on two posts.
        mb.cylinder((sx, 0.3, 0), (sx, 0.3, 1.9), 0.045, 0.04, "pole", segments=5)
        for k in range(3):
            mb.cylinder((sx, 0.3, 1.85 - 0.3 * k), (sx + 0.25, 0.3, 1.7 - 0.3 * k), 0.03, 0.09, "herb" if k % 2 else "herb_flower", segments=5)

    def smoke(t):
        turns, moves = {}, {}
        for i in range(3):
            s = (t + i / 3) % 1.0
            moves["smoke%d" % i] = (0.5 * s, 0.15 * math.sin(TAU * s), 1.8 * s)
            turns["smoke%d" % i] = [(kit.Z, 120 * s)]
        return turns, moves

    kit.save(mb, FAMILY, "health_fumigation", COLORS, mech=kit.Mech(bones).clip("smoke", 4.0, smoke))


def bath_tub():
    mb = kit.begin()
    mb.box((0, 0, 0.04), (3.0, 2.4, 0.08), "plank_dark")
    mb.cylinder((0, 0, 0.08), (0, 0, 0.8), 0.7, 0.8, "plank", segments=10)
    for zz in (0.2, 0.6):
        mb.cylinder((0, 0, zz), (0, 0, zz + 0.05), 0.75 + 0.1 * zz, 0.75 + 0.1 * zz, "iron", segments=10)
    mb.cylinder((0, 0, 0.72), (0, 0, 0.76), 0.72, 0.72, "water", segments=10)
    bones = []
    for i in range(3):
        b = "steam%d" % i
        a = TAU * i / 3
        for k in range(2):
            mb.sphere((math.cos(a) * 0.3, math.sin(a) * 0.3, 1.0 + 0.4 * k), 0.2 - 0.05 * k, "steam", {b: 1.0}, segments=6, rings=4)
        bones.append((b, (math.cos(a) * 0.3, math.sin(a) * 0.3, 0.8), (math.cos(a) * 0.3, math.sin(a) * 0.3, 1.4), None))
    for k in range(3):                                                                       # A folding screen.
        x0, x1 = -1.4 + 0.9 * k, -1.4 + 0.9 * (k + 1)
        y0, y1 = (1.0, 1.15) if k % 2 == 0 else (1.15, 1.0)
        solid(mb, [(x0, y0, 0.1), (x1, y1, 0.1), (x1, y1, 1.8), (x0, y0, 1.8)], (0, 0.03, 0), "linen" if k % 2 else "cloth_blue")
        mb.cylinder((x0, y0, 0.08), (x0, y0, 1.85), 0.03, 0.03, "pole_dark", segments=5)
    mb.cylinder((1.3, 1.0, 0.08), (1.3, 1.0, 1.85), 0.03, 0.03, "pole_dark", segments=5)
    mb.box((1.2, -0.6, 0.3), (0.5, 0.4, 0.45), "plank_light")                                   # A stool with towels and soap.
    mb.box((1.2, -0.6, 0.57), (0.4, 0.3, 0.1), "linen")
    mb.box((1.2, -0.75, 0.64), (0.1, 0.07, 0.05), "cloth_yellow")
    mb.cylinder((-1.2, -0.7, 0.08), (-1.2, -0.7, 0.4), 0.15, 0.19, "plank_light", segments=8)
    mb.cylinder((-1.2, -0.7, 0.36), (-1.2, -0.7, 0.39), 0.16, 0.16, "water", segments=8)

    def steam(t):
        moves = {}
        for i in range(3):
            s = (t + i / 3) % 1.0
            moves["steam%d" % i] = (0.1 * math.sin(TAU * s), 0, 0.9 * s)
        return {}, moves

    kit.save(mb, FAMILY, "health_bath_tub", COLORS, mech=kit.Mech(bones).clip("steam", 4.0, steam))


MODELS = {
    "loot_chest": chest("loot_chest", "plank", "iron"),
    "loot_chest_iron": chest("loot_chest_iron", "iron", "steel"),
    "loot_chest_gold": chest("loot_chest_gold", "cloth_red", "gold"),
    "loot_buried": buried,
    "loot_strongbox": strongbox,
    "loot_urns": urns,
    "loot_lost_backpack": lost_backpack,
    "loot_washed_crate": washed_crate,
    "loot_relic": relic,
    "trap_bear": bear_trap,
    "trap_snare": snare,
    "trap_net": net_trap,
    "trap_log_swing": log_swing,
    "trap_alarm_wire": alarm_wire,
    "trap_cage": cage_trap,
    "trap_fish": fish_trap,
    "health_quarantine_tent": quarantine_tent,
    "health_infirmary": infirmary,
    "health_fumigation": fumigation,
    "health_bath_tub": bath_tub,
}

kit.run(MODELS, FAMILY)
