"""Stockpile proposals: a pile for each resource the game has no pile for,
in the three levels of the game's own piles (phase 67): each level keeps the
pieces of the one before in the same place, so a pile grows without jumps.
About 1.5 x 1.5 m, standing on Z = 0, origin at the center. See ../LEEME.md.

    blender --background --factory-startup --python art/blender/proposals/piles/build.py -- [ids]
"""

import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import _kit as kit  # noqa: E402
import _shapes  # noqa: E402
import common  # noqa: E402
from _shapes import TAU, barrel, beam, crate, log, rock, sack, solid  # noqa: E402

FAMILY = "piles"
C = common.rgb
COLORS = {
    **_shapes.COLORS,
    "brick": C(0xA0553A), "brick_dark": C(0x84422C), "tile": C(0x9A4A2E), "tile_dark": C(0x7E3A24), "clay": C(0xB06A48), "clay_dark": C(0x8E5236),
    "coal": C(0x2A2826), "coal_shine": C(0x4A4A52), "ore": C(0x6A5A52), "ore_rust": C(0x9A5A3A), "ingot": C(0x5A5E66), "ingot_light": C(0x7A7E86),
    "wheat": C(0xE0B84A), "wheat_dark": C(0xC09A34), "barley": C(0xD8C87A), "flax": C(0xB8C070), "bread": C(0xC08A48), "bread_dark": C(0x9A6A34),
    "cabbage": C(0x7AAA5A), "carrot": C(0xE8843A), "apple": C(0xC83A2A), "apple_green": C(0x9AC04A), "meat": C(0x9A4A34), "meat_fat": C(0xE8D0C0),
    "fish": C(0x9AA8B0), "fish_dark": C(0x6A7A86), "smoked": C(0x7A4A2A), "herb": C(0x5A9A4A), "herb_flower": C(0xB07AD0), "beet": C(0x8A2A5A),
    "turnip": C(0xECE6DA), "berry": C(0xA8243A), "hide": C(0x9A7050), "hide_dark": C(0x7A5438), "fur": C(0x7A6A58), "leather_roll": C(0x8A5A34),
    "linen": C(0xECE6D6), "linen_shade": C(0xD0C8B4), "cloth_red": C(0xB8423A), "cloth_blue": C(0x3F5E8C), "cloth_green": C(0x4F7A44),
    "shoe": C(0x5A3B24), "wicker": C(0xB08A4A), "wicker_dark": C(0x8A6A34), "bow_wood": C(0x8A6038), "string": C(0xE8E0C8), "water": C(0x4A8FC0),
    "cloth_yellow": C(0xE0B840), "cheese": C(0xE8C050), "milk": C(0xF4F0E4), "honey": C(0xE0A030), "wool": C(0xF0ECE0),
}


def tray(x, y, z, w=0.6, d=0.45):
    def put(mb):
        mb.box((x, y, z + 0.03), (w, d, 0.06), "plank")
        for sx in (-1, 1):
            mb.box((x + sx * w / 2, y, z + 0.08), (0.04, d, 0.1), "plank_dark")
    return put


def basket(x, y, z, r, fill, n=5, seed=1):
    def put(mb):
        rnd = random.Random(seed)
        mb.cylinder((x, y, z), (x, y, z + r * 1.1), r * 0.75, r, "wicker", segments=8)
        mb.cylinder((x, y, z + r * 1.05), (x, y, z + r * 1.12), r * 1.03, r * 1.03, "wicker_dark", segments=8)
        for _ in range(n):
            a, d = rnd.uniform(0, TAU), rnd.uniform(0, r * 0.6)
            mb.sphere((x + math.cos(a) * d, y + math.sin(a) * d, z + r * 1.15), r * 0.3, fill if isinstance(fill, str) else rnd.choice(fill), segments=5, rings=3)
    return put


def crate_of(x, y, z, s, fill, seed=1):
    def put(mb):
        rnd = random.Random(seed)
        crate(mb, x, y, z, s, s * 0.7)
        for _ in range(5):
            mb.sphere((x + rnd.uniform(-s * 0.3, s * 0.3), y + rnd.uniform(-s * 0.3, s * 0.3), z + s * 0.72), s * 0.17, fill if isinstance(fill, str) else rnd.choice(fill),
                      segments=5, rings=3)
    return put


def rack(mb, w=1.3, h=1.5, y=0.0):
    for sx in (-w / 2, w / 2):
        mb.cylinder((sx, y - 0.3, 0), (sx, y, h), 0.035, 0.03, "pole_dark", segments=5)
        mb.cylinder((sx, y + 0.3, 0), (sx, y, h), 0.035, 0.03, "pole_dark", segments=5)
    beam(mb, (-w / 2 - 0.1, y, h), (w / 2 + 0.1, y, h), 0.03, "pole")


# Each kind returns its pieces in the order they are added as the pile grows.


def bricks(rnd):
    out = []
    for layer in range(6):
        for i in range(4):
            for j in range(2 + (layer < 3)):
                def put(mb, layer=layer, i=i, j=j):
                    along = layer % 2 == 0
                    x, y = (-0.48 + 0.32 * i, -0.2 + 0.2 * j) if along else (-0.3 + 0.2 * j * 1.5, -0.48 + 0.32 * i)
                    mb.box((x, y, 0.05 + 0.1 * layer), (0.3, 0.14, 0.09) if along else (0.14, 0.3, 0.09), "brick" if (i + j + layer) % 3 else "brick_dark")
                out.append(put)
    return out


def roof_tiles(rnd):
    out = []
    for stack, (x, y) in enumerate(((-0.4, -0.3), (0.3, -0.35), (-0.35, 0.35), (0.35, 0.3), (0.0, 0.0))):
        for k in range(7):
            def put(mb, x=x, y=y, k=k, stack=stack):
                mb.box((x, y, 0.03 + 0.05 * k), (0.45, 0.3, 0.04), "tile" if (k + stack) % 2 else "tile_dark", rotation_z=0.15 * stack)
            out.append(put)
    return out


def clay(rnd):
    out = []
    for i in range(14):
        def put(mb, i=i):
            layer = i // 5
            a, d = TAU * i / 5 + i * 0.7, (0.45 * (i % 3) / 2.0 + 0.05) * (1 - 0.3 * layer)
            mb.sphere((math.cos(a) * d, math.sin(a) * d, 0.14 + 0.2 * layer), 0.24 - 0.02 * layer, "clay" if i % 2 else "clay_dark", segments=6, rings=4, scale=(1.1, 1, 0.7))
        out.append(put)
    return out


def planks(rnd):
    out = []
    for layer in range(6):
        for i in range(4):
            def put(mb, layer=layer, i=i):
                mb.box((-0.36 + 0.24 * i + 0.03 * (layer % 2), 0.02 * (i % 2), 0.035 + 0.07 * layer), (0.22, 1.4, 0.06), "plank" if (i + layer) % 2 else "plank_light")
            out.append(put)
    return out


def iron(rnd):
    out = []
    for layer in range(5):
        for i in range(4 - layer // 2):
            def put(mb, layer=layer, i=i):
                along = layer % 2 == 0
                p = -0.36 + 0.24 * i + 0.06 * (layer // 2)
                mb.box((p, 0, 0.04 + 0.08 * layer) if along else (0, p, 0.04 + 0.08 * layer), (0.2, 0.7, 0.07) if along else (0.7, 0.2, 0.07),
                       "ingot" if (i + layer) % 2 else "ingot_light")
            out.append(put)
    return out


def tools(rnd):
    def box_of_tools(x, y, s):
        def put(mb):
            crate(mb, x, y, 0.0, s)
            for k in range(3):
                beam(mb, (x - 0.1 + 0.1 * k, y, s * 0.6), (x - 0.2 + 0.2 * k, y + 0.1, s + 0.6), 0.018, "pole")
            mb.box((x - 0.2, y + 0.1, s + 0.6), (0.2, 0.04, 0.08), "steel")
            mb.box((x + 0.2, y + 0.1, s + 0.55), (0.06, 0.16, 0.14), "ingot")
        return put
    return [box_of_tools(-0.35, -0.3, 0.55), box_of_tools(0.35, 0.3, 0.5), box_of_tools(0.3, -0.4, 0.45),
            lambda mb: beam(mb, (-0.7, 0.2, 0.0), (-0.45, 0.6, 1.3), 0.02, "pole"), lambda mb: mb.box((-0.7, 0.2, 0.12), (0.2, 0.03, 0.26), "steel"),
            box_of_tools(-0.35, 0.45, 0.45)]


def firewood(rnd):
    out = []
    for row in range(5):
        for k in range(7 - row % 2):
            def put(mb, row=row, k=k):
                x = -0.6 + 0.2 * k + (0.1 if row % 2 else 0)
                log(mb, (x, -0.35, 0.09 + 0.17 * row), (x, 0.35, 0.09 + 0.17 * row), 0.09)
            out.append(put)
    return out


def coal(rnd):
    out = [lambda mb: [mb.box((sx * 0.72, 0, 0.2), (0.06, 1.44, 0.4), "plank_dark") for sx in (-1, 1)] + [mb.box((0, sy * 0.72, 0.2), (1.44, 0.06, 0.4), "plank_dark") for sy in (-1, 1)]]
    for i in range(26):
        def put(mb, i=i):
            r2 = random.Random(i)
            layer = i // 9
            a, d = r2.uniform(0, TAU), r2.uniform(0, 0.55 - 0.15 * layer)
            mb.box((math.cos(a) * d, math.sin(a) * d, 0.1 + 0.18 * layer), (r2.uniform(0.18, 0.3),) * 2 + (0.2,), "coal" if i % 3 else "coal_shine", rotation_z=a)
        out.append(put)
    return out


def ore(rnd):
    out = []
    for i in range(16):
        def put(mb, i=i):
            r2 = random.Random(i + 40)
            layer = i // 7
            a, d = r2.uniform(0, TAU), r2.uniform(0.05, 0.55 - 0.18 * layer)
            rock(mb, math.cos(a) * d, math.sin(a) * d, 0.14 + 0.22 * layer, r2.uniform(0.16, 0.24), r2, "ore" if i % 3 else "ore_rust")
        out.append(put)
    return out


def gold(rnd):
    out = [lambda mb: mb.box((0.3, 0.3, 0.2), (0.6, 0.45, 0.4), "plank_dark"), lambda mb: mb.box((0.3, 0.3, 0.42), (0.52, 0.36, 0.06), "gold")]
    for layer in range(4):
        for i in range(3 - layer // 2):
            out.append(lambda mb, layer=layer, i=i: mb.box((-0.5 + 0.2 * i + 0.1 * (layer // 2), -0.3, 0.035 + 0.07 * layer), (0.17, 0.4, 0.06), "gold"))
    out.append(lambda mb: [mb.cylinder((-0.2 + 0.12 * k, 0.35 - 0.1 * k, 0.0), (-0.2 + 0.12 * k, 0.35 - 0.1 * k, 0.02), 0.06, 0.06, "gold", segments=7) for k in range(4)])
    return out


def sheaves(mat, dark):
    def kind(rnd):
        out = []
        for i, (x, y) in enumerate(((-0.4, -0.35), (0.4, -0.3), (0.0, 0.1), (-0.4, 0.45), (0.42, 0.45), (0.0, -0.6))):
            def put(mb, x=x, y=y):
                mb.cylinder((x, y, 0), (x, y, 0.75), 0.24, 0.1, mat, segments=7)
                mb.cylinder((x, y, 0.75), (x, y, 1.0), 0.1, 0.2, dark, segments=7)
                mb.cylinder((x, y, 0.5), (x, y, 0.56), 0.16, 0.16, "rope", segments=7)
            out.append(put)
        return out
    return kind


def bread(rnd):
    out = []
    for i, (x, y, z) in enumerate(((-0.35, -0.3, 0.0), (0.35, -0.3, 0.0), (0.0, 0.35, 0.0), (-0.17, -0.25, 0.3), (0.2, 0.1, 0.3), (0.0, -0.1, 0.6))):
        out.append(tray(x, y, z))
        for k in range(3):
            out.append(lambda mb, x=x, y=y, z=z, k=k: mb.sphere((x - 0.18 + 0.18 * k, y, z + 0.13), 0.1, "bread" if k % 2 else "bread_dark", segments=6, rings=4, scale=(1, 1.6, 0.8)))
    return out


def vegetables(rnd):
    spots = ((-0.38, -0.35, 0.0), (0.38, -0.35, 0.0), (-0.38, 0.38, 0.0), (0.38, 0.38, 0.0), (0.0, 0.0, 0.42), (0.0, -0.4, 0.42))
    return [crate_of(x, y, z, 0.6, ("cabbage", "carrot", "cabbage"), i) for i, (x, y, z) in enumerate(spots)]


def fruit(rnd):
    spots = ((-0.4, -0.35, 0.0), (0.4, -0.3, 0.0), (0.0, 0.4, 0.0), (-0.4, 0.42, 0.0), (0.42, 0.42, 0.0), (0.0, -0.05, 0.32))
    return [basket(x, y, z, 0.28, ("apple", "apple", "apple_green"), 7, i) for i, (x, y, z) in enumerate(spots)]


def berries(rnd):
    spots = ((-0.4, -0.35, 0.0), (0.4, -0.3, 0.0), (0.0, 0.4, 0.0), (-0.4, 0.42, 0.0), (0.42, 0.42, 0.0), (0.0, -0.05, 0.3))
    return [basket(x, y, z, 0.24, "berry", 9, i) for i, (x, y, z) in enumerate(spots)]


def roots(rnd):
    spots = ((-0.38, -0.35, 0.0), (0.38, -0.35, 0.0), (-0.38, 0.38, 0.0), (0.38, 0.38, 0.0), (0.0, 0.0, 0.42), (0.0, 0.42, 0.42))
    return [crate_of(x, y, z, 0.6, ("beet", "turnip", "beet"), i + 10) for i, (x, y, z) in enumerate(spots)]


def hanging(kind):
    """Things hung from a rack: meat, smoked meat, fish, herbs."""
    def make(rnd):
        out = [rack]
        for i in range(9):
            def put(mb, i=i):
                x = -0.56 + 0.14 * i
                if kind == "meat":
                    mb.cylinder((x, 0, 1.45), (x, 0, 0.9 + 0.05 * (i % 2)), 0.05, 0.13, "meat", segments=6)
                    mb.sphere((x, 0, 0.9 + 0.05 * (i % 2)), 0.13, "meat" if i % 2 else "meat_fat", segments=6, rings=4)
                elif kind == "smoked":
                    for k in range(3):
                        mb.cylinder((x, 0, 1.42 - 0.2 * k), (x, 0.0, 1.26 - 0.2 * k), 0.045, 0.045, "smoked", segments=6)
                elif kind == "fish":
                    solid(mb, [(x, -0.06, 1.42), (x, 0.06, 1.42), (x, 0.09, 1.15), (x, 0.0, 0.95), (x, -0.09, 1.15)], (0.03, 0, 0), "fish" if i % 2 else "fish_dark")
                    solid(mb, [(x, 0.0, 0.98), (x, 0.08, 0.86), (x, -0.08, 0.86)], (0.03, 0, 0), "fish_dark")
                else:
                    mb.cylinder((x, 0, 1.45), (x, 0, 1.0), 0.03, 0.1, "herb", segments=5)
                    mb.sphere((x, 0, 0.98), 0.07, "herb_flower" if i % 3 == 0 else "herb", segments=5, rings=3)
            out.append(put)
        return out
    return make


def beer(rnd):
    spots = ((-0.36, -0.36, 0.0), (0.36, -0.36, 0.0), (-0.36, 0.36, 0.0), (0.36, 0.36, 0.0), (0.0, 0.0, 0.86))
    return [(lambda mb, x=x, y=y, z=z: barrel(mb, x, y, z, 0.85, 0.32)) for x, y, z in spots]


def hides(rnd):
    out = []
    for k in range(8):
        def put(mb, k=k):
            r2 = random.Random(k)
            mat = ("hide", "fur", "hide_dark")[k % 3]
            dx, dy = r2.uniform(-0.05, 0.05), r2.uniform(-0.05, 0.05)
            solid(mb, [(-0.5 + dx, -0.55 + dy, 0.04 * k), (0.5 + dx, -0.55 + dy, 0.04 * k), (0.62 + dx, 0.0 + dy, 0.04 * k), (0.5 + dx, 0.55 + dy, 0.04 * k),
                       (-0.5 + dx, 0.55 + dy, 0.04 * k), (-0.62 + dx, 0.0 + dy, 0.04 * k)], (0, 0, 0.035), mat)
        out.append(put)
    return out


def rolls(mats, r=0.13, length=1.0):
    def kind(rnd):
        out = []
        for layer in range(3):
            for i in range(4 - layer):
                def put(mb, layer=layer, i=i):
                    x = -0.42 + 0.28 * i + 0.14 * layer
                    z = r + layer * r * 1.75
                    mat = mats[(i + layer) % len(mats)]
                    mb.cylinder((x, -length / 2, z), (x, length / 2, z), r, r, mat, segments=8)
                    mb.cylinder((x, -length / 2 - 0.01, z), (x, -length / 2, z), r * 0.5, r * 0.5, "plank_dark", segments=6)
                out.append(put)
        return out
    return kind


def folded(mats):
    def kind(rnd):
        out = [tray(-0.35, -0.3, 0.0, 0.62, 0.5), tray(0.35, -0.3, 0.0, 0.62, 0.5), tray(0.0, 0.35, 0.0, 0.62, 0.5)]
        for stack, (x, y) in enumerate(((-0.35, -0.3), (0.35, -0.3), (0.0, 0.35))):
            for k in range(5):
                out.append(lambda mb, x=x, y=y, k=k, stack=stack: mb.box((x, y, 0.1 + 0.075 * k), (0.5 - 0.02 * k, 0.4, 0.07), mats[(k + stack) % len(mats)]))
        return out
    return kind


def shoes(rnd):
    out = [lambda mb: [mb.box((0, 0.3, 0.3 + 0.4 * k), (1.3, 0.4, 0.05), "plank") for k in range(3)] + [mb.box((sx * 0.65, 0.3, 0.55), (0.05, 0.4, 1.1), "plank_dark") for sx in (-1, 1)]]
    for shelf in range(3):
        for i in range(4):
            def put(mb, shelf=shelf, i=i):
                x, z = -0.45 + 0.3 * i, 0.33 + 0.4 * shelf
                for s in (-0.06, 0.06):
                    mb.box((x + s, 0.25, z + 0.04), (0.09, 0.26, 0.08), "shoe")
                    mb.box((x + s, 0.33, z + 0.14), (0.09, 0.1, 0.14), "shoe")
            out.append(put)
    return out


def bows(rnd):
    out = [rack]
    for i in range(8):
        def put(mb, i=i):
            x = -0.5 + 0.14 * i
            pts = [(x, -0.22 + 0.44 * abs(math.sin(math.pi * k / 6)) * 0.0 + 0.16 * math.sin(math.pi * k / 6), 0.1 + 0.22 * k) for k in range(7)]
            for a, b in zip(pts, pts[1:]):
                beam(mb, a, b, 0.016, "bow_wood")
            mb.cylinder(pts[0], pts[-1], 0.004, 0.004, "string", segments=3)
        out.append(put)
    return out


def weapons(rnd):
    out = [rack]
    for i in range(8):
        def put(mb, i=i):
            x = -0.5 + 0.14 * i
            if i % 2:
                mb.cylinder((x, -0.3, 0.0), (x, -0.02, 1.9), 0.018, 0.018, "pole", segments=5)
                mb.cylinder((x, -0.02, 1.9), (x, 0.01, 2.15), 0.04, 0.0, "steel", segments=4)
            else:
                mb.box((x, 0.12, 0.75), (0.07, 0.02, 1.0), "steel")
                mb.box((x, 0.12, 1.28), (0.24, 0.04, 0.05), "ingot")
                mb.cylinder((x, 0.12, 1.3), (x, 0.12, 1.48), 0.022, 0.022, "leather", segments=5)
        out.append(put)
    out.append(lambda mb: mb.cylinder((0.55, -0.45, 0.4), (0.55, -0.5, 0.42), 0.36, 0.36, "cloth_blue", segments=9))
    out.append(lambda mb: mb.cylinder((-0.5, -0.45, 0.4), (-0.5, -0.5, 0.42), 0.36, 0.36, "cloth_red", segments=9))
    return out


def dairy(rnd):
    out = [lambda mb: [mb.box((0, 0.3, 0.3 + 0.4 * k), (1.3, 0.45, 0.05), "plank") for k in range(3)] + [mb.box((sx * 0.65, 0.3, 0.55), (0.05, 0.45, 1.1), "plank_dark") for sx in (-1, 1)]]
    for shelf in range(3):
        for i in range(3):
            out.append(lambda mb, shelf=shelf, i=i: mb.cylinder((-0.4 + 0.4 * i, 0.3, 0.33 + 0.4 * shelf), (-0.4 + 0.4 * i, 0.3, 0.47 + 0.4 * shelf), 0.16, 0.16, "cheese", segments=8))
    for i in range(3):
        def can(mb, i=i):
            x = -0.45 + 0.45 * i
            mb.cylinder((x, -0.4, 0), (x, -0.4, 0.5), 0.15, 0.15, "steel", segments=8)
            mb.cylinder((x, -0.4, 0.5), (x, -0.4, 0.62), 0.15, 0.08, "steel", segments=8)
        out.append(can)
    return out


def honey(rnd):
    out = []
    for i, (x, y, z) in enumerate(((-0.35, -0.3, 0.0), (0.0, -0.3, 0.0), (0.35, -0.3, 0.0), (-0.2, 0.2, 0.0), (0.2, 0.2, 0.0), (-0.17, -0.3, 0.32), (0.17, -0.3, 0.32), (0.0, 0.2, 0.32))):
        def put(mb, x=x, y=y, z=z):
            mb.cylinder((x, y, z), (x, y, z + 0.26), 0.13, 0.15, "clay", segments=8)
            mb.cylinder((x, y, z + 0.26), (x, y, z + 0.3), 0.16, 0.16, "linen", segments=8)
            mb.cylinder((x, y, z + 0.22), (x, y, z + 0.25), 0.155, 0.155, "rope", segments=8)
        out.append(put)
    return out


def wool(rnd):
    out = []
    for i, (x, y, z) in enumerate(((-0.35, -0.35, 0.0), (0.35, -0.35, 0.0), (-0.35, 0.35, 0.0), (0.35, 0.35, 0.0), (0.0, 0.0, 0.42), (0.0, -0.4, 0.42))):
        def put(mb, x=x, y=y, z=z):
            mb.sphere((x, y, z + 0.24), 0.32, "wool", segments=7, rings=5, scale=(1.05, 1.0, 0.75))
            for k in (-0.12, 0.12):
                mb.cylinder((x + k - 0.01, y, z + 0.24), (x + k + 0.01, y, z + 0.24), 0.26, 0.26, "rope", segments=8)
        out.append(put)
    return out


def hay(rnd):
    out = []
    for i, (x, y, z) in enumerate(((-0.36, -0.36, 0.0), (0.36, -0.36, 0.0), (-0.36, 0.36, 0.0), (0.36, 0.36, 0.0), (0.0, -0.2, 0.42), (0.0, 0.3, 0.42))):
        def put(mb, x=x, y=y, z=z, i=i):
            mb.box((x, y, z + 0.2), (0.68, 0.5, 0.4), "hay" if i % 2 else "hay_dark")
            for k in (-0.18, 0.18):
                mb.box((x + k, y, z + 0.2), (0.03, 0.52, 0.42), "rope")
        out.append(put)
    return out


KINDS = {
    "bricks": bricks, "roof_tiles": roof_tiles, "clay": clay, "planks": planks, "iron": iron, "tools": tools,
    "firewood": firewood, "coal": coal, "iron_ore": ore, "gold": gold,
    "wheat": sheaves("wheat", "wheat_dark"), "barley": sheaves("barley", "wheat_dark"), "flax": sheaves("flax", "herb"), "bread": bread, "vegetables": vegetables,
    "fruit": fruit, "berries": berries, "roots": roots, "meat": hanging("meat"), "smoked": hanging("smoked"), "fish": hanging("fish"), "herbs": hanging("herbs"),
    "beer": beer, "cheese": dairy, "honey": honey, "hay": hay,
    "hides": hides, "leather": rolls(("leather_roll", "hide_dark")), "linen": rolls(("linen", "linen_shade", "cloth_blue", "cloth_red"), 0.11, 0.9),
    "clothes": folded(("linen", "cloth_blue", "cloth_red", "cloth_green", "cloth_yellow")), "shoes": shoes, "bows": bows, "weapons": weapons, "wool": wool,
}


def pile(kind, level):
    def build():
        mb = kit.begin()
        pieces = KINDS[kind](random.Random(1))
        fixed = 1 if kind in ("meat", "smoked", "fish", "herbs", "bows", "weapons", "coal", "shoes", "cheese") else 0   # The rack or bin is there from the start.
        rest = len(pieces) - fixed
        count = fixed + max(1, math.ceil(rest * (0.34, 0.67, 1.0)[level - 1]))
        for put in pieces[:count]:
            put(mb)
        kit.save(mb, FAMILY, "pile_%s_%d" % (kind, level), COLORS)
    return build


MODELS = {"pile_%s_%d" % (kind, level): pile(kind, level) for kind in KINDS for level in (1, 2, 3)}

kit.run(MODELS, FAMILY)
