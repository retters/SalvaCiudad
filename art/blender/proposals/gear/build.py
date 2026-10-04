"""Gear proposals: the tools of the trades in three tiers (stone, iron,
steel), weapons and armor the game does not have yet, things to carry and
a few magic items. See ../LEEME.md.

    blender --background --factory-startup --python art/blender/proposals/gear/build.py -- [ids]

Like art/blender/weapons, every item stands on Z = 0 with its long axis
along Z and its wide side toward -Y, and saves its `grip` (where a hand
holds it) in the model.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import _kit as kit  # noqa: E402
import _shapes  # noqa: E402
import common  # noqa: E402
from _shapes import TAU, beam, rope, solid  # noqa: E402

FAMILY = "gear"
C = common.rgb
COLORS = {
    **_shapes.COLORS,
    "head_stone": C(0x8E8A84), "head_stone_dark": C(0x6A6660), "head_iron": C(0x5A5E66), "head_iron_dark": C(0x3E4248),
    "head_steel": C(0xB8C0C8), "head_steel_dark": C(0x8A929A), "brass": C(0xC8A040), "copper": C(0xB8703A),
    "wicker": C(0xB08A4A), "wicker_dark": C(0x8A6A34), "net": C(0xC8C0A0), "water": C(0x4A8FC0),
    "cloth_blue": C(0x2F4E8C), "cloth_red": C(0xA83A34), "emblem": C(0xECE8DC), "hide": C(0x9A7050), "fur": C(0x7A6A58),
    "drum_skin": C(0xE0D0B0), "string": C(0xE8E0C8), "page": C(0xF0E6C8), "book": C(0x6A2A4A), "glow_magic": C(0x8AE8FF),
    "glow_rune": C(0xC08AFF), "window": C(0xF6D070), "bone": C(0xE4DCC8), "chain": C(0x6A6E74), "padding": C(0x8A3A34),
}
TIERS = ("stone", "iron", "steel")
TIER_ES = {"stone": "piedra", "iron": "hierro", "steel": "acero"}


def shaft(mb, length, r=0.02, mat="pole", z0=0.0, w=None):
    mb.cylinder((0, 0, z0), (0, 0, z0 + length), r, r * 0.9, mat, w, segments=6)


def lashing(mb, z, r=0.035, n=3):
    for k in range(n):
        mb.cylinder((0, 0, z + 0.025 * k), (0, 0, z + 0.025 * k + 0.02), r, r, "rope", segments=6)


def head_mats(tier):
    return "head_" + tier, "head_" + tier + "_dark"


def fat(tier):
    return 1.35 if tier == "stone" else 1.0


def save(mb, name, grip, mech=None):
    kit.save(mb, FAMILY, name, COLORS, mech=mech, extras={"grip": [float(v) for v in grip]})


# --- Tools in tiers -----------------------------------------------------------------------------


def pickaxe(mb, tier):
    m, d = head_mats(tier)
    k = fat(tier)
    shaft(mb, 0.92)
    for sx in (-1, 1):
        mb.cylinder((0, 0, 0.87), (sx * 0.17, 0, 0.86), 0.035 * k, 0.028 * k, m, segments=4)
        mb.cylinder((sx * 0.17, 0, 0.86), (sx * 0.34, 0, 0.79), 0.028 * k, 0.004, m, segments=4)
    mb.box((0, 0, 0.87), (0.07 * k, 0.07 * k, 0.09), d)
    if tier == "stone":
        lashing(mb, 0.78)
    return (0, 0, 0.3)


def shovel(mb, tier):
    m, d = head_mats(tier)
    k = fat(tier)
    shaft(mb, 0.95)
    beam(mb, (-0.09, 0, 0.03), (0.09, 0, 0.03), 0.022, "pole_dark")
    for sx in (-1, 1):
        beam(mb, (sx * 0.09, 0, 0.03), (0, 0, 0.16), 0.016, "pole_dark")
    mb.cylinder((0, 0, 0.9), (0, 0, 1.02), 0.026, 0.03, d, segments=6)
    solid(mb, [(-0.11 * k, -0.012, 1.0), (0.11 * k, -0.012, 1.0), (0.12 * k, -0.03, 1.2), (0, -0.04, 1.32), (-0.12 * k, -0.03, 1.2)], (0, 0.014 * k, 0), m)
    return (0, 0, 0.45)


def hoe(mb, tier):
    m, d = head_mats(tier)
    k = fat(tier)
    shaft(mb, 1.3)
    mb.cylinder((0, 0.03, 1.27), (0, -0.1, 1.29), 0.02, 0.018, d, segments=5)
    solid(mb, [(-0.07 * k, -0.1, 1.31), (0.07 * k, -0.1, 1.31), (0.085 * k, -0.14, 1.1), (-0.085 * k, -0.14, 1.1)], (0, -0.012 * k, 0), m)
    if tier == "stone":
        lashing(mb, 1.2)
    return (0, 0, 0.6)


def scythe(mb, tier):
    m, d = head_mats(tier)
    k = fat(tier)
    mb.cylinder((0, 0, 0), (0.05, 0, 0.8), 0.02, 0.02, "pole", segments=6)
    mb.cylinder((0.05, 0, 0.8), (0, 0, 1.55), 0.02, 0.018, "pole", segments=6)
    for z in (0.45, 0.95):
        beam(mb, (0.03, 0, z), (0.03, -0.14, z + 0.03), 0.016, "pole_dark")
    blade = [(0.0, 1.57), (-0.25, 1.62), (-0.5, 1.58), (-0.72, 1.46), (-0.5, 1.5), (-0.25, 1.53), (0.0, 1.5)]
    solid(mb, [(x, -0.005 * k, z) for x, z in blade[:4]] + [(x, -0.005 * k, z) for x, z in blade[4:]], (0, 0.01 * k, 0), m)
    mb.box((0, 0, 1.54), (0.05, 0.05, 0.08), d)
    return (0.03, 0, 0.7)


def sickle(mb, tier):
    m, _d = head_mats(tier)
    k = fat(tier)
    mb.cylinder((0, 0, 0), (0, 0, 0.14), 0.02, 0.016, "pole", segments=6)
    mb.cylinder((0, 0, 0.0), (0, 0, 0.02), 0.025, 0.025, "pole_dark", segments=6)
    pts = []
    for i in range(7):
        a = -0.5 + 3.3 * i / 6
        pts.append((0.13 - 0.15 * math.cos(a), 0.27 + 0.15 * math.sin(a) * 1.0))
    for (x0, z0), (x1, z1) in zip(pts, pts[1:]):
        mb.cylinder((x0, 0, z0), (x1, 0, z1), 0.016 * k, 0.012 * k if (x1, z1) != pts[-1] else 0.002, m, segments=4)
    mb.cylinder((0, 0, 0.14), pts[0][:1] + (0,) + pts[0][1:], 0.014, 0.016 * k, m, segments=4)
    return (0, 0, 0.07)


def pitchfork(mb, tier):
    m, d = head_mats(tier)
    k = fat(tier)
    shaft(mb, 1.25)
    beam(mb, (-0.1, 0, 1.25), (0.1, 0, 1.25), 0.016 * k, d)
    for sx in (-0.1, 0.0, 0.1):
        mb.cylinder((sx, 0, 1.25), (sx, -0.03, 1.55), 0.012 * k, 0.002, m, segments=4)
    if tier == "stone":
        lashing(mb, 1.15)
    return (0, 0, 0.55)


def sledge(mb, tier):
    m, d = head_mats(tier)
    k = fat(tier)
    shaft(mb, 0.85, 0.022)
    mb.box((0, 0, 0.82), (0.24 * k, 0.09 * k, 0.09 * k), m)
    for sx in (-1, 1):
        mb.box((sx * 0.115 * k, 0, 0.82), (0.02, 0.1 * k, 0.1 * k), d)
    if tier == "stone":
        lashing(mb, 0.7)
    return (0, 0, 0.3)


def saw(mb, tier):
    m, d = head_mats(tier)
    for sx in (-0.3, 0.3):
        beam(mb, (sx, 0, 0.0), (sx, 0, 0.5), 0.02, "pole")
    beam(mb, (-0.3, 0, 0.28), (0.3, 0, 0.28), 0.018, "pole_dark")
    rope(mb, (-0.3, 0, 0.48), (0.3, 0, 0.48), 0.008)
    beam(mb, (0, 0, 0.48), (0, 0.0, 0.33), 0.008, "pole_dark")
    solid(mb, [(-0.3, -0.003, 0.02), (0.3, -0.003, 0.02), (0.3, -0.003, 0.06), (-0.3, -0.003, 0.06)], (0, 0.006, 0), m)
    for i in range(12):
        x = -0.28 + 0.05 * i
        solid(mb, [(x, -0.003, 0.02), (x + 0.045, -0.003, 0.02), (x + 0.02, -0.003, -0.0)], (0, 0.006, 0), d)
    return (0.3, 0, 0.35)


TIERED = {"pickaxe": pickaxe, "shovel": shovel, "hoe": hoe, "scythe": scythe, "sickle": sickle, "pitchfork": pitchfork,
          "sledge": sledge, "saw": saw}


def tiered(kind, tier):
    def build():
        mb = kit.begin()
        grip = TIERED[kind](mb, tier)
        save(mb, "tool_%s_%s" % (kind, tier), grip)
    return build


# --- Other tools --------------------------------------------------------------------------------


def rake():
    mb = kit.begin()
    shaft(mb, 1.4)
    beam(mb, (-0.2, 0, 1.4), (0.2, 0, 1.4), 0.02, "pole_dark")
    for i in range(8):
        mb.cylinder((-0.175 + 0.05 * i, 0, 1.4), (-0.175 + 0.05 * i, -0.09, 1.38), 0.008, 0.004, "pole", segments=4)
    for sx in (-1, 1):
        beam(mb, (sx * 0.12, 0, 1.4), (0, 0, 1.22), 0.01, "pole_dark")
    save(mb, "tool_rake", (0, 0, 0.6))


def tongs():
    mb = kit.begin()
    for sx in (-1, 1):
        beam(mb, (sx * 0.05, 0, 0.0), (-sx * 0.012, 0, 0.42), 0.012, "head_iron")
        beam(mb, (-sx * 0.012, 0, 0.42), (-sx * 0.04, 0, 0.5), 0.014, "head_iron_dark")
        beam(mb, (-sx * 0.04, 0, 0.5), (-sx * 0.01, 0, 0.6), 0.014, "head_iron_dark")
    mb.cylinder((0, -0.02, 0.42), (0, 0.02, 0.42), 0.018, 0.018, "head_steel", segments=6)
    mb.box((0, 0, 0.6), (0.07, 0.05, 0.05), "copper")   # A piece of hot metal in its jaws.
    save(mb, "tool_tongs", (0, 0, 0.12))


def shears():
    mb = kit.begin()
    for sx in (-1, 1):
        solid(mb, [(sx * 0.012, -0.004, 0.14), (sx * 0.05, -0.004, 0.16), (sx * 0.004, -0.004, 0.36)], (0, 0.008, 0), "head_steel")
        beam(mb, (sx * 0.03, 0, 0.15), (sx * 0.035, 0, 0.04), 0.008, "head_iron")
    for i in range(5):
        a0, a1 = math.pi + math.pi * i / 5, math.pi + math.pi * (i + 1) / 5
        beam(mb, (math.cos(a0) * 0.035, 0, 0.04 + math.sin(a0) * 0.035), (math.cos(a1) * 0.035, 0, 0.04 + math.sin(a1) * 0.035), 0.008, "head_iron")
    mb.sphere((0.09, 0, 0.07), 0.07, "emblem", segments=6, rings=4, scale=(1, 1, 0.8))   # A tuft of wool.
    save(mb, "tool_shears", (0, 0, 0.1))


def net():
    mb = kit.begin()
    shaft(mb, 1.5, 0.018)
    ring = [(0.24 * math.cos(TAU * i / 8), 0.0, 1.72 + 0.24 * math.sin(TAU * i / 8)) for i in range(8)]
    for a, b in zip(ring, ring[1:] + ring[:1]):
        beam(mb, a, b, 0.012, "pole_dark")
    for i in range(8):
        a, b = ring[i], ring[(i + 1) % 8]
        solid(mb, [a, b, (0, 0.5, 1.6)], (0, 0.004, 0), "net" if i % 2 else "wicker")
    mb.sphere((0, 0.3, 1.63), 0.06, "head_steel", segments=5, rings=3, scale=(1, 2, 0.7))   # A fish in it.
    save(mb, "tool_net", (0, 0, 0.6))


def bucket(yoke):
    def build():
        mb = kit.begin()

        def one(x, z):
            mb.cylinder((x, 0, z), (x, 0, z + 0.3), 0.12, 0.15, "plank", segments=9)
            for zz in (0.05, 0.22):
                mb.cylinder((x, 0, z + zz), (x, 0, z + zz + 0.03), 0.125 + 0.1 * zz, 0.125 + 0.1 * zz, "head_iron", segments=9)
            mb.cylinder((x, 0, z + 0.26), (x, 0, z + 0.29), 0.135, 0.135, "water", segments=9)
            for sx in (-1, 1):
                rope(mb, (x + sx * 0.14, 0, z + 0.3), (x, 0, z + 0.55), 0.01)

        if yoke:
            for sx in (-0.6, 0.6):
                one(sx, 0.0)
                rope(mb, (sx, 0, 0.55), (sx, 0, 1.0), 0.01)
            for k in range(4):
                x0, x1 = -0.62 + 0.31 * k, -0.62 + 0.31 * (k + 1)
                z0 = 1.0 + 0.1 * math.sin(math.pi * k / 4)
                z1 = 1.0 + 0.1 * math.sin(math.pi * (k + 1) / 4)
                beam(mb, (x0, 0, z0), (x1, 0, z1), 0.03, "pole")
            save(mb, "tool_bucket_yoke", (0, 0, 1.1))
        else:
            one(0.0, 0.0)
            save(mb, "tool_bucket", (0, 0, 0.55))
    return build


def watering_can():
    mb = kit.begin()
    mb.cylinder((0, 0, 0), (0, 0, 0.26), 0.11, 0.1, "copper", segments=9)
    mb.cylinder((0, 0, 0.26), (0, 0, 0.28), 0.105, 0.105, "brass", segments=9)
    mb.cylinder((0.09, 0, 0.06), (0.3, 0, 0.3), 0.025, 0.015, "copper", segments=6)
    mb.cylinder((0.3, 0, 0.3), (0.34, 0, 0.33), 0.03, 0.045, "brass", segments=7)
    for i in range(5):
        a0, a1 = -0.5 + 0.8 * i, -0.5 + 0.8 * (i + 1)
        beam(mb, (-0.1 - 0.08 * math.cos(a0) * 0.5 - 0.02, 0, 0.16 + 0.1 * math.sin(a0)), (-0.1 - 0.08 * math.cos(a1) * 0.5 - 0.02, 0, 0.16 + 0.1 * math.sin(a1)), 0.01, "brass")
    save(mb, "tool_watering_can", (-0.16, 0, 0.18))


def basket(kind):
    def build():
        mb = kit.begin()
        if kind == "hand":
            mb.cylinder((0, 0, 0), (0, 0, 0.2), 0.14, 0.2, "wicker", segments=9)
            for zz in (0.05, 0.12, 0.19):
                mb.cylinder((0, 0, zz), (0, 0, zz + 0.02), 0.15 + 0.3 * zz, 0.15 + 0.3 * zz, "wicker_dark", segments=9)
            for i in range(6):
                a0, a1 = math.pi * i / 6, math.pi * (i + 1) / 6
                beam(mb, (math.cos(a0) * 0.2, 0, 0.2 + math.sin(a0) * 0.2), (math.cos(a1) * 0.2, 0, 0.2 + math.sin(a1) * 0.2), 0.012, "wicker_dark")
            for x, y, mat in ((-0.06, 0.03, "cloth_red"), (0.07, -0.02, "cloth_red"), (0.0, 0.07, "brass"), (0.02, -0.07, "padding")):
                mb.sphere((x, y, 0.21), 0.05, mat, segments=5, rings=3)
            save(mb, "tool_basket", (0, 0, 0.4))
        else:
            mb.cylinder((0, 0, 0), (0, 0, 0.55), 0.14, 0.22, "wicker", segments=9)
            for k in range(5):
                mb.cylinder((0, 0, 0.06 + 0.11 * k), (0, 0, 0.08 + 0.11 * k), 0.15 + 0.016 * k, 0.15 + 0.016 * k, "wicker_dark", segments=9)
            for sx in (-1, 1):
                solid(mb, [(sx * 0.1, -0.2, 0.5), (sx * 0.14, -0.2, 0.5), (sx * 0.14, -0.22, 0.1), (sx * 0.1, -0.22, 0.1)], (0, -0.012, 0), "leather")
            mb.sphere((0, 0, 0.55), 0.18, "wicker_dark", segments=7, rings=3, scale=(1, 1, 0.35))
            for x, y in ((-0.06, 0.04), (0.08, 0.0), (0.0, -0.08)):
                mb.cylinder((x, y, 0.5), (x, y, 0.72), 0.02, 0.015, "emblem", segments=5)
                mb.cylinder((x, y, 0.7), (x, y, 0.76), 0.06, 0.01, "padding", segments=6)
            save(mb, "tool_basket_back", (0, -0.2, 0.3))
    return build


def lantern():
    mb = kit.begin()
    mb.box((0, 0, 0.02), (0.14, 0.14, 0.04), "head_iron")
    mb.box((0, 0, 0.15), (0.1, 0.1, 0.22), "window")
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.box((sx * 0.055, sy * 0.055, 0.15), (0.018, 0.018, 0.24), "head_iron")
    mb.box((0, 0, 0.28), (0.15, 0.15, 0.03), "head_iron")
    mb.cylinder((0, 0, 0.29), (0, 0, 0.36), 0.06, 0.015, "head_iron", segments=5)
    for i in range(5):
        a0, a1 = math.pi * i / 5, math.pi * (i + 1) / 5
        beam(mb, (math.cos(a0) * 0.07, 0, 0.36 + math.sin(a0) * 0.07), (math.cos(a1) * 0.07, 0, 0.36 + math.sin(a1) * 0.07), 0.007, "head_iron")
    save(mb, "tool_lantern", (0, 0, 0.43))


def spyglass():
    mb = kit.begin()
    for z0, z1, r in ((0.0, 0.16, 0.022), (0.16, 0.34, 0.028), (0.34, 0.55, 0.034)):
        mb.cylinder((0, 0, z0), (0, 0, z1), r, r, "brass", segments=8)
        mb.cylinder((0, 0, z1 - 0.02), (0, 0, z1), r + 0.004, r + 0.004, "leather", segments=8)
    mb.cylinder((0, 0, 0.55), (0, 0, 0.56), 0.03, 0.03, "window", segments=8)
    save(mb, "tool_spyglass", (0, 0, 0.2))


def instrument(kind):
    def build():
        mb = kit.begin()
        if kind == "lute":
            mb.sphere((0, 0, 0.2), 0.17, "plank_light", segments=8, rings=5, scale=(1.0, 0.5, 1.25))
            mb.cylinder((0, -0.085, 0.2), (0, -0.09, 0.2), 0.06, 0.06, "pole_dark", segments=8)
            mb.box((0, -0.04, 0.6), (0.05, 0.03, 0.42), "pole_dark")
            mb.box((0, -0.02, 0.83), (0.07, 0.04, 0.1), "plank")
            for sx in (-0.012, 0.0, 0.012):
                mb.cylinder((sx, -0.09, 0.12), (sx, -0.06, 0.8), 0.002, 0.002, "string", segments=3)
            for k in range(4):
                beam(mb, (-0.05 if k % 2 else 0.05, -0.02, 0.8 + 0.02 * (k // 2)), (-0.09 if k % 2 else 0.09, -0.02, 0.8 + 0.02 * (k // 2)), 0.006, "pole")
            save(mb, "gear_lute", (0, 0, 0.5))
        elif kind == "drum":
            mb.cylinder((0, 0, 0.03), (0, 0, 0.33), 0.18, 0.18, "cloth_red", segments=10)
            for z in (0.0, 0.33):
                mb.cylinder((0, 0, z), (0, 0, z + 0.03), 0.195, 0.195, "brass", segments=10)
            mb.cylinder((0, 0, 0.355), (0, 0, 0.36), 0.18, 0.18, "drum_skin", segments=10)
            for i in range(10):
                a0, a1 = TAU * i / 10, TAU * (i + 0.5) / 10
                rope(mb, (math.cos(a0) * 0.19, math.sin(a0) * 0.19, 0.03 if i % 2 else 0.33), (math.cos(a1) * 0.19, math.sin(a1) * 0.19, 0.33 if i % 2 else 0.03), 0.006)
            for sx in (-1, 1):
                mb.cylinder((sx * 0.05, -0.05, 0.37), (sx * 0.2, -0.3, 0.42), 0.012, 0.01, "pole", segments=5)
                mb.sphere((sx * 0.05, -0.05, 0.375), 0.022, "pole_dark", segments=5, rings=3)
            save(mb, "gear_drum", (0, 0, 0.2))
        else:
            pts = [(0.0, 0.0, 0.0), (0.02, 0.0, 0.12), (0.07, 0.0, 0.24), (0.15, 0.0, 0.34), (0.26, 0.0, 0.4)]
            radii = [0.012, 0.02, 0.03, 0.045, 0.07]
            for i in range(4):
                mb.cylinder(pts[i], pts[i + 1], radii[i], radii[i + 1], "bone", segments=7)
            mb.cylinder((0, 0, -0.02), (0, 0, 0.02), 0.016, 0.016, "brass", segments=7)
            mb.cylinder(pts[3], (0.17, 0, 0.355), 0.05, 0.052, "brass", segments=7)
            rope(mb, (0.02, 0, 0.1), (0.2, 0, 0.37), 0.006)
            save(mb, "gear_horn", (0.03, 0, 0.15))
    return build


# --- Weapons and armor --------------------------------------------------------------------------


def polearm(kind):
    def build():
        mb = kit.begin()
        if kind == "halberd":
            shaft(mb, 1.9, 0.02)
            mb.cylinder((0, 0, 1.85), (0, 0, 2.25), 0.03, 0.0, "head_steel", segments=4)
            solid(mb, [(0.02, -0.006, 1.6), (0.2, -0.006, 1.55), (0.24, -0.006, 1.72), (0.2, -0.006, 1.9), (0.02, -0.006, 1.86)], (0, 0.012, 0), "head_steel")
            solid(mb, [(-0.02, -0.006, 1.68), (-0.16, -0.006, 1.7), (-0.02, -0.006, 1.8)], (0, 0.012, 0), "head_steel_dark")
            mb.cylinder((0, 0, 1.55), (0, 0, 1.9), 0.028, 0.028, "head_iron", segments=6)
            save(mb, "weapon_halberd", (0, 0, 0.8))
        elif kind == "pike":
            shaft(mb, 3.2, 0.02)
            mb.cylinder((0, 0, 3.15), (0, 0, 3.3), 0.026, 0.03, "head_iron", segments=6)
            mb.cylinder((0, 0, 3.3), (0, 0, 3.6), 0.035, 0.0, "head_steel", segments=4)
            solid(mb, [(0.0, -0.004, 3.1), (0.25, -0.004, 3.05), (0.0, -0.004, 2.95)], (0, 0.008, 0), "cloth_blue")
            save(mb, "weapon_pike", (0, 0, 1.2))
        else:
            shaft(mb, 1.5, 0.014)
            mb.cylinder((0, 0, 1.45), (0, 0, 1.75), 0.02, 0.0, "head_steel", segments=4)
            mb.cylinder((0, 0, 0.6), (0, 0, 0.8), 0.018, 0.018, "leather", segments=6)
            save(mb, "weapon_javelin", (0, 0, 0.7))
    return build


def flail():
    mb = kit.begin()
    shaft(mb, 0.6, 0.02)
    mb.cylinder((0, 0, 0.56), (0, 0, 0.62), 0.028, 0.028, "head_iron", segments=6)
    w, bones = None, []
    prev = None
    for k in range(4):   # A chain that swings.
        b = "link%d" % k
        z = 0.62 + 0.07 * k
        mb.box((0, 0, z + 0.035), (0.03 if k % 2 else 0.012, 0.012 if k % 2 else 0.03, 0.06), "chain", {b: 1.0})
        bones.append((b, (0, 0, z), (0, 0, z + 0.07), prev))
        prev = b
    w = {"ball": 1.0}
    mb.sphere((0, 0, 0.99), 0.075, "head_iron", w, segments=7, rings=5)
    for i in range(8):
        a, up = TAU * i / 8, (0.6 if i % 2 else -0.6)
        d = (math.cos(a) * math.cos(up), math.sin(a) * math.cos(up), math.sin(up))
        mb.cylinder((d[0] * 0.06, d[1] * 0.06, 0.99 + d[2] * 0.06), (d[0] * 0.13, d[1] * 0.13, 0.99 + d[2] * 0.13), 0.018, 0.0, "head_steel", w, segments=4)
    bones.append(("ball", (0, 0, 0.9), (0, 0, 1.0), prev))

    def swing(t):
        turns = {"link%d" % k: [(kit.X, 14 * math.sin(TAU * t - 0.5 * k)), (kit.Y, 14 * math.cos(TAU * t - 0.5 * k))] for k in range(4)}
        turns["ball"] = [(kit.X, 10 * math.sin(TAU * t - 2.0)), (kit.Y, 10 * math.cos(TAU * t - 2.0))]
        return turns, {}

    save(mb, "weapon_flail", (0, 0, 0.2), kit.Mech(bones).clip("swing", 1.2, swing))


def mace():
    mb = kit.begin()
    shaft(mb, 0.6, 0.02)
    mb.cylinder((0, 0, 0.0), (0, 0, 0.04), 0.03, 0.03, "head_iron", segments=6)
    mb.cylinder((0, 0, 0.14), (0, 0, 0.26), 0.024, 0.024, "leather", segments=6)
    mb.cylinder((0, 0, 0.55), (0, 0, 0.8), 0.035, 0.035, "head_iron", segments=6)
    for i in range(6):
        a = TAU * i / 6
        solid(mb, [(math.cos(a) * 0.03, math.sin(a) * 0.03, 0.57), (math.cos(a) * 0.1, math.sin(a) * 0.1, 0.66), (math.cos(a) * 0.03, math.sin(a) * 0.03, 0.78)],
              (-math.sin(a) * 0.012, math.cos(a) * 0.012, 0), "head_steel")
    mb.cylinder((0, 0, 0.8), (0, 0, 0.87), 0.03, 0.0, "head_steel", segments=5)
    save(mb, "weapon_mace", (0, 0, 0.2))


def throwing_axe():
    mb = kit.begin()
    mb.cylinder((0, 0, 0), (0.02, 0, 0.42), 0.016, 0.014, "pole", segments=6)
    solid(mb, [(0.0, -0.007, 0.33), (0.14, -0.007, 0.28), (0.16, -0.007, 0.42), (0.0, -0.007, 0.41)], (0, 0.014, 0), "head_steel")
    mb.cylinder((0, 0, 0.02), (0, 0, 0.12), 0.019, 0.019, "leather", segments=6)
    save(mb, "weapon_throwing_axe", (0, 0, 0.07))


def wolf_head(mb, cx, y, cz, s, mat, depth):
    def pts(points):
        return [(cx + px * s, y, cz + pz * s) for px, pz in points]
    solid(mb, pts([(-0.27, 0.16), (-0.18, -0.08), (0, -0.32), (0.18, -0.08), (0.27, 0.16), (0.11, 0.27), (-0.11, 0.27)]), (0, -depth, 0), mat)
    for sx in (-1, 1):
        solid(mb, pts([(sx * 0.27, 0.16), (sx * 0.11, 0.27), (sx * 0.25, 0.46)]), (0, -depth, 0), mat)


def shield(kind):
    def build():
        mb = kit.begin()
        if kind == "kite":
            for name, cloth in (("blue", "cloth_blue"),):
                solid(mb, [(-0.3, 0, 1.0), (0.3, 0, 1.0), (0.34, 0, 0.7), (0.2, 0, 0.25), (0, 0, 0.0), (-0.2, 0, 0.25), (-0.34, 0, 0.7)], (0, 0.03, 0), cloth)
                solid(mb, [(-0.33, -0.006, 1.03), (0.33, -0.006, 1.03), (0.33, -0.006, 0.97), (-0.33, -0.006, 0.97)], (0, 0.042, 0), "head_steel")
                wolf_head(mb, 0, 0.0, 0.62, 0.72, "emblem", 0.012)
            for z in (0.75, 0.5):
                beam(mb, (-0.1, 0.05, z), (0.1, 0.05, z), 0.012, "leather")
            save(mb, "armor_shield_kite_wolf", (0, 0.05, 0.62))
        else:
            mb.cylinder((0, 0, 0.2), (0, 0.03, 0.2), 0.2, 0.2, "head_iron", segments=10)
            mb.cylinder((0, -0.01, 0.2), (0, 0, 0.2), 0.21, 0.21, "head_steel", segments=10)
            mb.sphere((0, -0.02, 0.2), 0.07, "head_steel", segments=7, rings=4, scale=(1, 0.6, 1))
            beam(mb, (-0.06, 0.05, 0.2), (0.06, 0.05, 0.2), 0.012, "leather")
            save(mb, "armor_shield_buckler", (0, 0.05, 0.2))
    return build


def helmet(kind):
    def build():
        mb = kit.begin()
        if kind == "leather":
            mb.sphere((0, 0, 0.1), 0.12, "leather", segments=8, rings=5, scale=(1, 1.1, 1.0))
            mb.cylinder((0, 0, 0.06), (0, 0, 0.1), 0.125, 0.125, "hide", segments=8)
            for sx in (-1, 1):
                solid(mb, [(sx * 0.11, -0.03, 0.08), (sx * 0.11, 0.05, 0.08), (sx * 0.1, 0.02, -0.06)], (sx * 0.012, 0, 0), "leather")
        elif kind == "kettle":
            mb.sphere((0, 0, 0.1), 0.12, "head_iron", segments=8, rings=5)
            mb.cylinder((0, 0, 0.07), (0, 0, 0.05), 0.12, 0.2, "head_steel", segments=10)
            mb.cylinder((0, 0, 0.2), (0, 0, 0.24), 0.02, 0.0, "head_steel", segments=5)
        else:
            mb.cylinder((0, 0, -0.05), (0, 0, 0.18), 0.13, 0.125, "head_steel", segments=8)
            mb.cylinder((0, 0, 0.18), (0, 0, 0.24), 0.125, 0.07, "head_steel_dark", segments=8)
            mb.box((0, -0.125, 0.08), (0.2, 0.012, 0.025), "head_iron_dark")
            mb.box((0, -0.125, 0.06), (0.025, 0.012, 0.2), "brass")
            for k in range(3):
                for sx in (-1, 1):
                    mb.box((sx * (0.04 + 0.025 * k), -0.126, -0.0), (0.008, 0.012, 0.05), "head_iron_dark")
            solid(mb, [(0, 0.02, 0.24), (0, 0.2, 0.3), (0, 0.24, 0.1), (0, 0.1, 0.2)], (0.012, 0, 0), "cloth_red")
        save(mb, "armor_helmet_" + kind, (0, 0, 0.0))
    return build


def armor_stand(tier):
    def build():
        mb = kit.begin()
        body, trim = {"leather": ("leather", "hide"), "iron": ("head_iron", "head_iron_dark"), "steel": ("head_steel", "brass")}[tier]
        mb.box((0, 0, 0.03), (0.5, 0.5, 0.06), "plank_dark")
        mb.cylinder((0, 0, 0.06), (0, 0, 1.55), 0.035, 0.03, "pole", segments=6)
        beam(mb, (-0.35, 0, 1.38), (0.35, 0, 1.38), 0.025, "pole_dark")
        mb.cylinder((0, 0, 0.82), (0, 0, 1.12), 0.17, 0.21, body, segments=8)
        mb.cylinder((0, 0, 1.12), (0, 0, 1.4), 0.21, 0.19, body, segments=8)
        mb.cylinder((0, 0, 0.8), (0, 0, 0.86), 0.19, 0.19, trim, segments=8)
        for sx in (-1, 1):
            mb.sphere((sx * 0.27, 0, 1.38), 0.1, body if tier != "steel" else trim, segments=7, rings=4, scale=(1.1, 1, 0.8))
            for k in range(3 if tier != "leather" else 2):
                solid(mb, [(sx * 0.02, -0.19, 0.8 - 0.14 * k), (sx * 0.19, -0.16, 0.8 - 0.14 * k), (sx * 0.2, -0.17, 0.62 - 0.14 * k), (sx * 0.02, -0.2, 0.62 - 0.14 * k)],
                      (0, -0.012, 0), body if k % 2 == 0 else trim)
        if tier == "leather":
            mb.sphere((0, 0, 1.63), 0.12, "leather", segments=8, rings=5)
        elif tier == "iron":
            mb.sphere((0, 0, 1.63), 0.12, "head_iron", segments=8, rings=5)
            mb.cylinder((0, 0, 1.6), (0, 0, 1.58), 0.12, 0.2, "head_iron_dark", segments=10)
        else:
            mb.cylinder((0, 0, 1.5), (0, 0, 1.72), 0.13, 0.125, "head_steel", segments=8)
            mb.cylinder((0, 0, 1.72), (0, 0, 1.78), 0.125, 0.07, "head_steel_dark", segments=8)
            mb.box((0, -0.125, 1.62), (0.2, 0.012, 0.025), "head_iron_dark")
            solid(mb, [(0, 0.02, 1.78), (0, 0.2, 1.84), (0, 0.24, 1.64), (0, 0.1, 1.74)], (0.012, 0, 0), "cloth_red")
            solid(mb, [(-0.2, 0.18, 1.38), (0.2, 0.18, 1.38), (0.26, 0.2, 0.5), (-0.26, 0.2, 0.5)], (0, 0.012, 0), "cloth_blue")
        save(mb, "armor_stand_" + tier, (0, 0, 0.0))
    return build


# --- Magic --------------------------------------------------------------------------------------


def spellbook():
    mb = kit.begin()
    w = {"book": 1.0}
    for sx, bone in ((-1, "cover_l"), (1, "cover_r")):
        wc = {bone: 1.0}
        solid(mb, [(0, -0.16, 1.2), (sx * 0.24, -0.16, 1.2), (sx * 0.24, 0.16, 1.2), (0, 0.16, 1.2)], (0, 0, -0.02), "book", wc)
        solid(mb, [(sx * 0.01, -0.15, 1.2), (sx * 0.23, -0.15, 1.2), (sx * 0.23, 0.15, 1.2), (sx * 0.01, 0.15, 1.2)], (0, 0, 0.025), "page", wc)
        for k in range(4):
            mb.box((sx * 0.12, -0.09 + 0.06 * k, 1.228), (0.15, 0.012, 0.004), "glow_rune", wc)
    mb.box((0, 0, 1.19), (0.03, 0.33, 0.04), "book", w)
    solid(mb, [(0, -0.15, 1.225), (0.01, -0.15, 1.42), (0.01, 0.15, 1.42), (0, 0.15, 1.225)], (0.004, 0, 0), "page", {"page": 1.0})
    for i in range(5):
        a = TAU * i / 5
        mb.cylinder((math.cos(a) * 0.42, math.sin(a) * 0.42, 1.25), (math.cos(a) * 0.42, math.sin(a) * 0.42, 1.36), 0.03, 0.0, "glow_magic", {"motes": 1.0}, segments=4)
        mb.cylinder((math.cos(a) * 0.42, math.sin(a) * 0.42, 1.16), (math.cos(a) * 0.42, math.sin(a) * 0.42, 1.25), 0.0, 0.03, "glow_magic", {"motes": 1.0}, segments=4)
    bones = [("book", (0, 0, 1.2), (0, 0.2, 1.2), None), ("cover_l", (0, 0, 1.2), (-0.2, 0, 1.2), "book"), ("cover_r", (0, 0, 1.2), (0.2, 0, 1.2), "book"),
             ("page", (0, 0, 1.225), (0, 0, 1.4), "book"), ("motes", (0, 0, 1.2), (0, 0, 1.5), None)]

    def hover(t):
        flap = 10 * math.sin(TAU * t)
        return ({"cover_l": [(kit.Y, 12 + flap)], "cover_r": [(kit.Y, -12 - flap)], "page": [(kit.Y, 80 * math.sin(TAU * t))], "motes": [(kit.Z, 360 * t)],
                 "book": [(kit.X, 6 * math.sin(TAU * t))]}, {"book": (0, 0, 0.06 * math.sin(TAU * t)), "motes": (0, 0, 0.05 * math.sin(TAU * 2 * t))})

    save(mb, "magic_spellbook", (0, 0, 1.2), kit.Mech(bones).clip("hover", 4.0, hover))


def wand():
    mb = kit.begin()
    mb.cylinder((0, 0, 0), (0.01, 0, 0.2), 0.016, 0.012, "pole_dark", segments=6)
    mb.cylinder((0.01, 0, 0.2), (-0.01, 0, 0.38), 0.012, 0.008, "pole", segments=6)
    mb.cylinder((0, 0, 0.0), (0, 0, 0.03), 0.02, 0.02, "brass", segments=6)
    w = {"spark": 1.0}
    mb.cylinder((-0.01, 0, 0.38), (-0.01, 0, 0.42), 0.0, 0.03, "glow_magic", w, segments=4)
    mb.cylinder((-0.01, 0, 0.42), (-0.01, 0, 0.5), 0.03, 0.0, "glow_magic", w, segments=4)
    pose = lambda t: ({"spark": [(kit.Z, 360 * t)]}, {"spark": (0, 0, 0.01 * math.sin(TAU * 2 * t))})   # noqa: E731
    save(mb, "magic_wand", (0, 0, 0.08), kit.Mech([("spark", (-0.01, 0, 0.42), (-0.01, 0, 0.5), None)]).clip("glow", 2.0, pose))


MODELS = {}
for _kind in TIERED:
    for _tier in TIERS:
        MODELS["tool_%s_%s" % (_kind, _tier)] = tiered(_kind, _tier)
MODELS.update({
    "tool_rake": rake, "tool_tongs": tongs, "tool_shears": shears, "tool_net": net,
    "tool_bucket": bucket(False), "tool_bucket_yoke": bucket(True), "tool_watering_can": watering_can,
    "tool_basket": basket("hand"), "tool_basket_back": basket("back"), "tool_lantern": lantern, "tool_spyglass": spyglass,
    "gear_lute": instrument("lute"), "gear_drum": instrument("drum"), "gear_horn": instrument("horn"),
    "weapon_halberd": polearm("halberd"), "weapon_pike": polearm("pike"), "weapon_javelin": polearm("javelin"),
    "weapon_flail": flail, "weapon_mace": mace, "weapon_throwing_axe": throwing_axe,
    "armor_shield_kite_wolf": shield("kite"), "armor_shield_buckler": shield("buckler"),
    "armor_helmet_leather": helmet("leather"), "armor_helmet_kettle": helmet("kettle"), "armor_helmet_great": helmet("great"),
    "armor_stand_leather": armor_stand("leather"), "armor_stand_iron": armor_stand("iron"), "armor_stand_steel": armor_stand("steel"),
    "magic_spellbook": spellbook, "magic_wand": wand,
})

kit.run(MODELS, FAMILY)
