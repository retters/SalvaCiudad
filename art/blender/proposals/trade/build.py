"""Trade proposals: the market by what each stall sells, the public scales,
the pack train and the places where merchants deal. See ../LEEME.md.

    blender --background --factory-startup --python art/blender/proposals/trade/build.py -- [ids]
"""

import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import _animals  # noqa: E402
import _kit as kit  # noqa: E402
import _shapes  # noqa: E402
import common  # noqa: E402
from _shapes import TAU, barrel, beam, crate, gable_roof, log, rope, sack, shed_roof, solid, wheel  # noqa: E402

FAMILY = "trade"
C = common.rgb
COLORS = {
    **_shapes.COLORS, **_animals.COLORS,
    "awning_red": C(0xB8362E), "awning_white": C(0xECE6D6), "awning_blue": C(0x2E5A9A), "awning_green": C(0x3E7A4A), "awning_yellow": C(0xD8A83A),
    "awning_violet": C(0x6A4A9A), "awning_orange": C(0xD8792E), "awning_brown": C(0x7A5232),
    "fish": C(0x8AA6B8), "fish_dark": C(0x5A7688), "ice": C(0xD8ECF4), "bread": C(0xD8A45A), "bread_dark": C(0xA8743A), "cloth_a": C(0xB8362E), "cloth_b": C(0x2E5A9A),
    "cloth_c": C(0xD8A83A), "cloth_d": C(0x3E7A4A), "clay": C(0xB8704A), "clay_dark": C(0x8A5234), "glaze": C(0x3A7A8A), "veg_green": C(0x5E9A3A), "veg_orange": C(0xE08A2E),
    "veg_red": C(0xC83A2E), "veg_purple": C(0x6A3A6A), "meat": C(0xB84A4A), "meat_fat": C(0xE8C8B8), "spice_a": C(0xD8792E), "spice_b": C(0xC83A2E), "spice_c": C(0xE0C040),
    "glow_potion": C(0x8CFFB0), "shingle": C(0x6A5038), "shingle_dark": C(0x54402C), "thatch": C(0xC9A55A), "thatch_dark": C(0xA8863F), "brass": C(0xC9A441),
    "parchment": C(0xE6D8B0), "ink": C(0x2E2A26), "carpet": C(0x9A3A3A), "carpet_b": C(0xD8A83A), "canvas": C(0xD8CCA8), "canvas_dark": C(0xB8AC88), "cave": C(0x14110F),
    "bell": C(0xB8923A), "paint_white": C(0xECE6D6), "grass": C(0x6A9440),
}
STALLS = {
    "fish": ("awning_blue", "awning_white"), "bread": ("awning_yellow", "awning_white"), "cloth": ("awning_red", "awning_yellow"),
    "pottery": ("awning_orange", "awning_white"), "vegetables": ("awning_green", "awning_white"), "meat": ("awning_red", "awning_white"),
    "weapons": ("awning_brown", "awning_red"), "spices": ("awning_violet", "awning_yellow"),
}


def table(mb, x, y, w, d, h=0.85, mat="plank"):
    mb.box((x, y, h), (w, d, 0.06), mat)
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.box((x + sx * (w / 2 - 0.06), y + sy * (d / 2 - 0.06), h / 2), (0.07, 0.07, h), "pole_dark")


def goods(mb, kind, rnd):
    """What lies on a counter 2.6 m wide at y = -0.5, its top at 0.88."""
    z = 0.88
    if kind == "fish":
        mb.box((0, -0.5, z + 0.04), (2.3, 0.7, 0.08), "ice")
        for k in range(10):
            x, y = -1.0 + 0.22 * k, -0.5 + 0.2 * ((k % 3) - 1)
            mb.sphere((x, y, z + 0.11), 0.09, "fish" if k % 2 else "fish_dark", segments=6, rings=4, scale=(0.6, 2.2, 0.5))
            solid(mb, [(x, y + 0.2, z + 0.11), (x - 0.07, y + 0.3, z + 0.11), (x + 0.07, y + 0.3, z + 0.11)], (0, 0, 0.02), "fish_dark")
        barrel(mb, 1.6, 0.4, 0.0, 0.7, 0.28)
        for k in range(4):
            mb.sphere((0.9 - 0.5 * k, 0.5, 2.0), 0.08, "fish", segments=6, rings=4, scale=(0.6, 0.5, 2.4))   # Dried ones hung up.
    elif kind == "bread":
        for k in range(9):
            x, y = -1.0 + 0.25 * k, -0.5 + 0.18 * ((k % 3) - 1)
            if k % 3 == 0:
                mb.sphere((x, y, z + 0.09), 0.14, "bread", segments=7, rings=4, scale=(1, 1, 0.6))
            else:
                mb.sphere((x, y, z + 0.07), 0.08, "bread_dark" if k % 2 else "bread", segments=6, rings=4, scale=(1, 2.6, 0.8))
        mb.cylinder((1.0, -0.5, z), (1.0, -0.5, z + 0.22), 0.2, 0.26, "rope", segments=8)
        for k in range(4):
            mb.sphere((1.0 + 0.08 * math.cos(k * 1.6), -0.5 + 0.08 * math.sin(k * 1.6), z + 0.25), 0.08, "bread", segments=5, rings=3)
        for k in range(3):
            mb.cylinder((-0.6 + 0.6 * k, 0.5, 1.75), (-0.6 + 0.6 * k, 0.5, 2.05), 0.1, 0.1, "bread_dark", segments=7)   # Pretzel rings on a rod.
    elif kind == "cloth":
        for k, mat in enumerate(("cloth_a", "cloth_b", "cloth_c", "cloth_d", "awning_white")):
            mb.cylinder((-1.0 + 0.48 * k, -0.8, z + 0.12), (-1.0 + 0.48 * k, -0.2, z + 0.12), 0.12, 0.12, mat, segments=8)
        for k, mat in enumerate(("cloth_d", "cloth_a", "cloth_c")):
            mb.cylinder((-0.6 + 0.6 * k, -0.75, z + 0.34), (-0.6 + 0.6 * k, -0.25, z + 0.34), 0.11, 0.11, mat, segments=8)
        for k, mat in enumerate(("cloth_b", "cloth_c", "cloth_a", "cloth_d")):   # Lengths hung at the back.
            mb.box((-0.9 + 0.6 * k, 0.5, 1.5), (0.5, 0.04, 1.2), mat)
    elif kind == "pottery":
        for k in range(8):
            x, y = -1.05 + 0.3 * k, -0.5 + 0.15 * ((k % 2) * 2 - 1)
            h = 0.2 + 0.12 * (k % 3)
            mat = ("clay", "clay_dark", "glaze")[k % 3]
            mb.cylinder((x, y, z), (x, y, z + h * 0.6), 0.07, 0.12, mat, segments=8)
            mb.cylinder((x, y, z + h * 0.6), (x, y, z + h), 0.12, 0.06, mat, segments=8)
        for k in range(3):
            mb.cylinder((-1.6, -0.4 + 0.5 * k, 0), (-1.6, -0.4 + 0.5 * k, 0.5), 0.14, 0.22, "clay", segments=8)
            mb.cylinder((-1.6, -0.4 + 0.5 * k, 0.5), (-1.6, -0.4 + 0.5 * k, 0.7), 0.22, 0.12, "clay_dark", segments=8)
        for k in range(4):
            mb.cylinder((-0.7 + 0.45 * k, 0.5, 1.6), (-0.7 + 0.45 * k, 0.46, 1.6), 0.16, 0.16, "glaze" if k % 2 else "clay", segments=9)   # Plates on the back.
    elif kind == "vegetables":
        for k, mat in enumerate(("veg_green", "veg_orange", "veg_red", "veg_purple", "veg_green")):
            x = -1.05 + 0.52 * k
            mb.box((x, -0.5, z + 0.08), (0.46, 0.66, 0.16), "plank_light")
            for i in range(6):
                mb.sphere((x - 0.12 + 0.12 * (i % 3), -0.65 + 0.3 * (i // 3), z + 0.2), 0.09, mat, segments=5, rings=3)
        sack(mb, 1.6, 0.3, 0.0, 0.26)
        for k in range(3):
            mb.sphere((-1.6, -0.2 + 0.4 * k, 0.2), 0.22, "veg_orange", segments=7, rings=5, scale=(1, 1, 0.75))
    elif kind == "meat":
        mb.box((0, -0.5, z + 0.03), (2.3, 0.7, 0.05), "plank_dark")
        for k in range(5):
            mb.sphere((-0.9 + 0.45 * k, -0.5, z + 0.12), 0.13, "meat", segments=6, rings=4, scale=(1.4, 0.9, 0.6))
            mb.sphere((-0.9 + 0.45 * k, -0.42, z + 0.14), 0.06, "meat_fat", segments=5, rings=3)
        for k in range(4):                                                       # Hams and sausages hung up.
            x = -0.9 + 0.6 * k
            rope(mb, (x, 0.3, 2.1), (x, 0.3, 1.9), 0.01)
            if k % 2:
                mb.sphere((x, 0.3, 1.7), 0.16, "meat", segments=7, rings=5, scale=(0.8, 0.7, 1.5))
            else:
                for i in range(3):
                    mb.cylinder((x - 0.1 + 0.1 * i, 0.3, 1.9), (x - 0.1 + 0.1 * i, 0.3, 1.45), 0.035, 0.035, "meat", segments=5)
        mb.box((1.0, -0.5, z + 0.1), (0.08, 0.3, 0.02), "steel")
    elif kind == "weapons":
        for k in range(4):
            mb.box((-0.9 + 0.3 * k, -0.5, z + 0.02), (0.06, 0.7, 0.02), "steel")
            mb.box((-0.9 + 0.3 * k, -0.2, z + 0.03), (0.2, 0.04, 0.03), "brass")
        mb.sphere((0.6, -0.5, z + 0.12), 0.14, "steel", segments=7, rings=5)
        mb.sphere((1.0, -0.5, z + 0.12), 0.14, "iron", segments=7, rings=5)
        for k in range(3):                                                       # Shields and spears at the back.
            mb.cylinder((-0.8 + 0.8 * k, 0.5, 1.5), (-0.8 + 0.8 * k, 0.44, 1.5), 0.3, 0.3, ("cloth_a", "cloth_b", "cloth_d")[k], segments=9)
            mb.sphere((-0.8 + 0.8 * k, 0.42, 1.5), 0.07, "steel", segments=5, rings=3)
        for k in range(4):
            beam(mb, (1.5 + 0.08 * k, 0.4, 0), (1.45 + 0.08 * k, 0.5, 2.2), 0.02, "pole")
            mb.cylinder((1.45 + 0.08 * k, 0.5, 2.2), (1.45 + 0.08 * k, 0.51, 2.45), 0.035, 0.0, "steel", segments=4)
    else:   # Spices and potions.
        for k, mat in enumerate(("spice_a", "spice_b", "spice_c", "veg_green", "bread_dark", "spice_a")):
            x = -1.05 + 0.42 * k
            mb.cylinder((x, -0.6, z), (x, -0.6, z + 0.16), 0.15, 0.18, "sack", segments=8)
            mb.cylinder((x, -0.6, z + 0.14), (x, -0.6, z + 0.26), 0.16, 0.0, mat, segments=8)
        for k in range(7):
            x = -0.9 + 0.3 * k
            mb.sphere((x, -0.3, z + 0.07), 0.06, "glow_potion" if k % 2 else "glaze", segments=5, rings=3)
            mb.cylinder((x, -0.3, z + 0.11), (x, -0.3, z + 0.19), 0.02, 0.025, "paint_white", segments=5)
        mb.box((1.3, -0.3, z + 0.02), (0.3, 0.14, 0.02), "brass")                  # Small scales.
        mb.cylinder((1.3, -0.3, z), (1.3, -0.3, z + 0.3), 0.015, 0.015, "brass", segments=4)
        beam(mb, (1.1, -0.3, z + 0.3), (1.5, -0.3, z + 0.3), 0.012, "brass")
        for sx in (-1, 1):
            mb.cylinder((1.3 + sx * 0.2, -0.3, z + 0.14), (1.3 + sx * 0.2, -0.3, z + 0.16), 0.07, 0.08, "brass", segments=7)
        for k in range(5):
            mb.cylinder((-1.0 + 0.5 * k, 0.5, 1.85), (-1.0 + 0.5 * k, 0.5, 2.1), 0.1, 0.02, "veg_green" if k % 2 else "bread_dark", segments=5)


def stall(kind):
    def build():
        mb = kit.begin()
        rnd = random.Random(len(kind))
        a, b = STALLS[kind]
        for sx in (-1.4, 1.4):
            mb.cylinder((sx, -0.9, 0), (sx, -0.9, 2.1), 0.05, 0.045, "pole", segments=6)
            mb.cylinder((sx, 0.6, 0), (sx, 0.6, 2.6), 0.05, 0.045, "pole", segments=6)
        beam(mb, (-1.4, 0.6, 2.1), (1.4, 0.6, 2.1), 0.035, "pole_dark")
        n = 7
        for k in range(n):                                                       # A striped awning with a scalloped edge.
            x0, x1 = -1.6 + 3.2 * k / n, -1.6 + 3.2 * (k + 1) / n
            mat = a if k % 2 else b
            solid(mb, [(x0, -1.15, 2.05), (x1, -1.15, 2.05), (x1, 0.7, 2.62), (x0, 0.7, 2.62)], (0, 0, 0.04), mat)
            solid(mb, [(x0, -1.15, 2.05), (x1, -1.15, 2.05), ((x0 + x1) / 2, -1.15, 1.83)], (0, 0.03, 0), mat)
        table(mb, 0, -0.5, 2.6, 0.9)
        mb.box((0, -0.93, 0.5), (2.6, 0.04, 0.6), a)
        goods(mb, kind, rnd)
        crate(mb, 0.9, 0.2, 0.0, 0.45)
        kit.save(mb, FAMILY, "trade_stall_" + kind, COLORS)
    return build


def market_cross(name, roofed):
    """Where the market is held and bargains are sworn."""
    def build():
        mb = kit.begin()
        for k in range(3):
            r = 2.2 - 0.5 * k
            mb.cylinder((0, 0, 0.2 * k), (0, 0, 0.2 * (k + 1)), r, r, "stone" if k % 2 else "stone_dark", segments=8)
        mb.cylinder((0, 0, 0.6), (0, 0, 1.0), 0.4, 0.3, "stone_light", segments=8)
        mb.cylinder((0, 0, 1.0), (0, 0, 4.2), 0.2, 0.15, "stone", segments=8)
        mb.cylinder((0, 0, 4.2), (0, 0, 4.4), 0.3, 0.3, "stone_light", segments=8)
        mb.box((0, 0, 4.9), (0.16, 0.16, 1.0), "stone_light")
        mb.box((0, 0, 5.05), (0.7, 0.16, 0.16), "stone_light")
        mb.sphere((0, 0, 5.45), 0.12, "gold", segments=6, rings=4)
        if roofed:   # A butter cross: eight posts and a roof round the shaft.
            for k in range(8):
                a = TAU * k / 8 + TAU / 16
                x, y = math.cos(a) * 3.0, math.sin(a) * 3.0
                mb.cylinder((x, y, 0), (x, y, 2.6), 0.13, 0.11, "pole", segments=6)
                beam(mb, (x, y, 2.0), (math.cos(a) * 2.2, math.sin(a) * 2.2, 2.6), 0.05, "pole_dark")
                a1 = a + TAU / 8
                beam(mb, (x, y, 2.6), (math.cos(a1) * 3.0, math.sin(a1) * 3.0, 2.6), 0.07, "pole_dark")
                solid(mb, [(math.cos(a) * 3.4, math.sin(a) * 3.4, 2.55), (math.cos(a1) * 3.4, math.sin(a1) * 3.4, 2.55), (math.cos(a1) * 0.3, math.sin(a1) * 0.3, 4.0),
                           (math.cos(a) * 0.3, math.sin(a) * 0.3, 4.0)], (0, 0, 0.07), "shingle" if k % 2 else "shingle_dark")
            mb.cylinder((0, 0, 0), (0, 0, 0.05), 3.6, 3.6, "stone_dark", segments=8)
        else:
            w = {"bell": 1.0}
            beam(mb, (0, 0, 3.4), (0.6, 0, 3.5), 0.03, "iron")
            mb.cylinder((0.55, 0, 3.45), (0.55, 0, 3.2), 0.04, 0.14, "bell", w, segments=8)
            rope(mb, (0.55, 0, 3.2), (0.55, 0, 1.6), 0.01, w)
        mech = None if roofed else kit.Mech([("bell", (0.55, 0, 3.48), (0.55, 0, 3.2), None)]).clip(
            "ring", 2.0, lambda t: ({"bell": [(kit.Y, 26.0 * math.sin(TAU * 3 * t) * (1 - t))]}, {}), loops=False)
        kit.save(mb, FAMILY, name, COLORS, mech=mech)
    return build


def weigh_house():
    """The public scales: nothing is sold by weight until it has hung here."""
    mb = kit.begin()
    mb.box((0, 0, 0.08), (5.0, 4.0, 0.16), "stone_dark")
    for sx in (-2.2, 2.2):
        for sy in (-1.7, 1.7):
            mb.box((sx, sy, 1.7), (0.2, 0.2, 3.2), "pole")
            beam(mb, (sx, sy, 2.6), (sx * 0.72, sy, 3.25), 0.06, "pole_dark")
    gable_roof(mb, 0, 0, 4.6, 3.6, 3.3, 1.3, ("shingle", "shingle_dark"), 0.4, 4, 0.07)
    mb.box((0, 0, 3.3), (0.2, 3.6, 0.2), "pole_dark")
    mb.cylinder((0, 0, 3.2), (0, 0, 2.75), 0.03, 0.03, "iron", segments=5)
    w = {"beam": 1.0}
    beam(mb, (-1.5, 0, 2.7), (1.5, 0, 2.7), 0.06, "iron", w)
    mb.box((0, 0, 2.85), (0.06, 0.06, 0.4), "brass", w)
    mb.sphere((0, 0, 2.7), 0.09, "brass", w, segments=6, rings=4)
    bones = [("beam", (0, 0, 2.7), (0.5, 0, 2.7), None)]
    for sx, pan in ((-1, "pan_l"), (1, "pan_r")):
        wp = {pan: 1.0}
        for dx, dy in ((-0.4, -0.4), (0.4, -0.4), (0.4, 0.4), (-0.4, 0.4)):
            rope(mb, (sx * 1.5, 0, 2.7), (sx * 1.5 + dx, dy, 1.0), 0.012, wp)
        mb.box((sx * 1.5, 0, 0.97), (1.0, 1.0, 0.06), "plank_dark", wp)
        if sx < 0:
            sack(mb, -1.7, -0.1, 1.0, 0.25, wp)
            sack(mb, -1.3, 0.15, 1.0, 0.25, wp)
        else:
            for k in range(4):
                mb.cylinder((1.3 + 0.25 * (k % 2), -0.15 + 0.3 * (k // 2), 1.0), (1.3 + 0.25 * (k % 2), -0.15 + 0.3 * (k // 2), 1.2 + 0.05 * k), 0.1, 0.07, "iron", wp, segments=7)
        bones.append((pan, (sx * 1.5, 0, 2.7), (sx * 1.5, 0, 1.0), None))
    table(mb, 1.5, -1.3, 1.0, 0.6)
    mb.box((1.5, -1.3, 0.89), (0.5, 0.36, 0.03), "parchment")
    mb.box((1.5, -1.3, 0.9), (0.02, 0.3, 0.03), "ink")
    for k in range(5):
        mb.cylinder((-1.9 + 0.2 * k, -1.4, 0.16), (-1.9 + 0.2 * k, -1.4, 0.3 + 0.07 * k), 0.07 + 0.012 * k, 0.05 + 0.01 * k, "iron", segments=7)
    barrel(mb, -1.7, 1.3, 0.16, 0.85, 0.3)
    crate(mb, 1.7, 1.2, 0.16, 0.6)

    def weigh(t):
        tilt = 7.0 * math.sin(TAU * t) * (0.4 + 0.6 * math.cos(TAU * t / 2) ** 2)
        drop = 1.5 * math.sin(math.radians(tilt))
        return {"beam": [(kit.Y, tilt)]}, {"pan_l": (0, 0, drop), "pan_r": (0, 0, -drop)}

    kit.save(mb, FAMILY, "trade_weigh_house", COLORS, mech=kit.Mech(bones).clip("weigh", 5.0, weigh))


def pack_load(mb, y, w, kind):
    z = 1.62
    mb.box((0, y + 0.05, z - 0.02), (0.8, 0.9, 0.06), "carpet" if kind % 2 else "awning_blue", w)
    for sx in (-1, 1):
        if kind == 0:
            mb.box((sx * 0.52, y + 0.05, z - 0.25), (0.3, 0.7, 0.5), "plank", w)
            mb.box((sx * 0.52, y + 0.05, z - 0.25), (0.32, 0.1, 0.52), "iron", w)
        elif kind == 1:
            mb.sphere((sx * 0.5, y + 0.05, z - 0.3), 0.3, "sack", w, segments=7, rings=5, scale=(0.8, 1.2, 1.2))
        else:
            mb.cylinder((sx * 0.52, y - 0.3, z - 0.2), (sx * 0.52, y + 0.4, z - 0.2), 0.22, 0.22, "plank", w, segments=8)
            for d in (-0.15, 0.25):
                mb.cylinder((sx * 0.52, y + d, z - 0.2), (sx * 0.52, y + d + 0.05, z - 0.2), 0.23, 0.23, "iron", w, segments=8)
    if kind == 1:
        mb.cylinder((-0.3, y + 0.05, z + 0.12), (0.3, y + 0.05, z + 0.12), 0.14, 0.14, "carpet_b", w, segments=8)
    for d in (-0.2, 0.3):
        mb.cylinder((-0.62, y + d, z - 0.3), (0.62, y + d, z - 0.3), 0.012, 0.012, "rope", w, segments=4)


def caravan(name, count):
    """A pack train: horses roped nose to tail, each with its load."""
    def build():
        mb = kit.begin()
        coats = (("coat_brown", "mane_dark"), ("coat_grey", "mane_light"), ("coat_dark", "mane_dark"), ("coat_brown", "mane_light"), ("coat_grey", "mane_dark"))
        animals = []
        for k in range(count):
            y = -(count - 1) * 1.6 + 3.2 * k
            horse = _animals.draft_animal(mb, y, "h%d_" % k, "horse", coats[k % 5][0], coats[k % 5][1], harness=True)
            pack_load(mb, y, {"h%d_body" % k: 1.0}, k % 3)
            if k:
                rope(mb, (0, y - 1.4, 1.55), (0, y - 2.3, 1.45), 0.012, {"h%d_body" % k: 1.0})
            animals.append(horse)
        bones = [b for a in animals for b in a["bones"]]
        speed, cycles = 1.3, 2
        seconds = cycles * animals[0]["cycle"]

        def walk(t):
            turns, moves = {}, {}
            for i, a in enumerate(animals):
                swing = math.degrees(math.asin(min(0.5, speed * a["cycle"] / (4 * a["hip"]))))
                tt, mm = a["gait"]((t * cycles + 0.21 * i) % 1.0, swing)
                turns.update(tt)
                moves.update(mm)
            return turns, moves

        def idle(t):
            turns, moves = {}, {}
            for i, a in enumerate(animals):
                tt, mm = a["idle"]((t + 0.3 * i) % 1.0)
                turns.update(tt)
                moves.update(mm)
            return turns, moves

        mech = kit.Mech(bones).clip("idle", 4.0, idle).clip("walk", seconds, walk, speed=speed)
        kit.save(mb, FAMILY, name, COLORS, mech=mech)
    return build


def trading_post():
    """A log house with a yard for wagons, out where two roads meet."""
    mb = kit.begin()
    rnd = random.Random(61)
    mb.box((0, 0, 0.04), (10.0, 9.0, 0.08), "hay_dark")
    for k in range(12):                                                          # The house, of squared logs.
        mb.box((-1.5, 2.0, 0.2 + 0.24 * k), (5.6 + (0.2 if k % 2 else 0), 3.6 + (0 if k % 2 else 0.2), 0.22), "bark" if k % 2 else "pole")
    gable_roof(mb, -1.5, 2.0, 5.6, 3.6, 3.05, 1.5, ("shingle", "shingle_dark"), 0.45, 4, 0.08, "plank")
    mb.box((-1.5, 0.17, 1.1), (1.0, 0.08, 1.8), "plank_dark")
    mb.box((-1.5, 0.12, 1.1), (0.06, 0.06, 1.7), "iron")
    for sx in (-3.3, 0.3):
        mb.box((sx, 0.17, 1.6), (0.8, 0.08, 0.7), "window")
        mb.box((sx, 0.14, 1.6), (0.9, 0.04, 0.06), "plank_dark")
    mb.box((-3.2, 2.0, 4.6), (0.7, 0.7, 1.6), "stone")
    shed_roof(mb, -1.5, -0.6, 5.0, 1.4, 2.2, 2.7, ("shingle_dark", "shingle"), 0.2, 2)          # A porch with the counter under it.
    for sx in (-3.8, 0.8):
        mb.cylinder((sx, -1.2, 0), (sx, -1.2, 2.25), 0.07, 0.06, "pole", segments=6)
    table(mb, 0.0, -0.7, 1.4, 0.6)
    for k in range(3):
        mb.cylinder((-0.4 + 0.4 * k, -0.7, 0.88), (-0.4 + 0.4 * k, -0.7, 1.05), 0.1, 0.08, ("clay", "glaze", "brass")[k], segments=7)
    beam(mb, (1.0, -1.25, 2.4), (1.9, -1.25, 2.4), 0.03, "iron")
    w = {"sign": 1.0}
    mb.box((1.5, -1.25, 2.0), (0.7, 0.05, 0.6), "plank", w)
    mb.cylinder((1.5, -1.29, 2.05), (1.5, -1.27, 2.05), 0.16, 0.16, "brass", w, segments=8)
    mb.box((1.5, -1.3, 1.85), (0.36, 0.02, 0.05), "brass", w)
    for sx in (-0.3, 0.3):
        rope(mb, (1.5 + sx, -1.25, 2.4), (1.5 + sx, -1.25, 2.3), 0.008, w)
    for k in range(26):                                                          # A stockade round the yard.
        a = k / 26
        for x, y in ((-4.8 + 9.6 * a, 4.3), (4.8, -4.3 + 8.6 * a), (-4.8, -4.3 + 8.6 * a)):
            mb.cylinder((x, y, 0), (x, y, 1.9 + 0.12 * ((k * 7) % 3)), 0.13, 0.11, "bark" if k % 2 else "pole", segments=5)
    for k in range(9):
        x = 1.6 + 0.4 * k
        mb.cylinder((x, -4.3, 0), (x, -4.3, 1.9 + 0.12 * (k % 3)), 0.13, 0.11, "bark" if k % 2 else "pole", segments=5)
        mb.cylinder((-4.8 + 0.4 * k, -4.3, 0), (-4.8 + 0.4 * k, -4.3, 1.9 + 0.12 * (k % 3)), 0.13, 0.11, "bark" if k % 2 else "pole", segments=5)
    for sx in (-1.3, 1.5):                                                       # The gateway stays open by day.
        mb.cylinder((sx, -4.3, 0), (sx, -4.3, 3.0), 0.16, 0.14, "pole_dark", segments=6)
    beam(mb, (-1.4, -4.3, 2.9), (1.6, -4.3, 2.9), 0.1, "pole_dark")
    for sx in (-1, 1):
        wheel(mb, (3.2 + sx * 0.75, 0.4, 0.55), 0.55, None, 0.09)
    mb.box((3.2, 0.4, 0.85), (1.3, 2.4, 0.5), "plank")                           # A wagon unloading.
    beam(mb, (3.0, -0.8, 0.7), (2.9, -2.4, 0.3), 0.04, "pole")
    barrel(mb, 3.0, 2.6, 0.08, 0.85, 0.32)
    barrel(mb, 3.7, 2.7, 0.08, 0.85, 0.32)
    crate(mb, 2.2, -2.2, 0.08, 0.7)
    crate(mb, 2.9, -2.6, 0.08, 0.55)
    for k in range(4):
        sack(mb, -3.6 + 0.5 * k, -2.6 + 0.2 * (k % 2), 0.08, 0.26)
    for y in (-0.6, 1.2):                                                        # A hitching rail.
        mb.cylinder((3.9, y - 3.0, 0), (3.9, y - 3.0, 1.1), 0.06, 0.05, "pole", segments=6)
    beam(mb, (3.9, -3.7, 1.0), (3.9, -1.7, 1.0), 0.04, "pole_dark")
    mb.cylinder((-4.2, -3.6, 0), (-4.2, -3.6, 6.0), 0.07, 0.05, "pole", segments=6)
    wf = {"flag": 1.0}
    solid(mb, [(-4.15, -3.615, 5.9), (-3.0, -3.615, 5.55), (-4.15, -3.615, 5.2)], (0, 0.03, 0), "awning_yellow", wf)

    def idle(t):
        return {"sign": [(kit.X, 8.0 * math.sin(TAU * t))], "flag": [(kit.Z, 16.0 * math.sin(TAU * 2 * t))]}, {}

    mech = kit.Mech([("sign", (1.5, -1.25, 2.4), (1.5, -1.25, 1.7), None), ("flag", (-4.15, -3.6, 5.55), (-3.0, -3.6, 5.55), None)]).clip("idle", 4.0, idle)
    kit.save(mb, FAMILY, "trade_post", COLORS, mech=mech)


def merchant_pavilion():
    """A rich merchant's tent, open at the front, with what he has brought from far away."""
    mb = kit.begin()
    n = 8
    for k in range(n):
        a0, a1 = TAU * k / n, TAU * (k + 1) / n
        mat = "awning_violet" if k % 2 else "awning_yellow"
        solid(mb, [(math.cos(a0) * 2.6, math.sin(a0) * 2.6, 2.2), (math.cos(a1) * 2.6, math.sin(a1) * 2.6, 2.2), (0, 0, 4.2)], (0, 0, 0.05), mat)
        if 5 <= k <= 6:
            continue                                                            # The open front (-Y).
        solid(mb, [(math.cos(a0) * 2.5, math.sin(a0) * 2.5, 0), (math.cos(a1) * 2.5, math.sin(a1) * 2.5, 0), (math.cos(a1) * 2.5, math.sin(a1) * 2.5, 2.2),
                   (math.cos(a0) * 2.5, math.sin(a0) * 2.5, 2.2)], (-math.cos((a0 + a1) / 2) * 0.04, -math.sin((a0 + a1) / 2) * 0.04, 0), mat)
        solid(mb, [(math.cos(a0) * 2.62, math.sin(a0) * 2.62, 2.22), (math.cos(a1) * 2.62, math.sin(a1) * 2.62, 2.22),
                   (math.cos((a0 + a1) / 2) * 2.62, math.sin((a0 + a1) / 2) * 2.62, 1.95)], (0, 0, 0.02), "gold")
    for k in range(n):
        a = TAU * k / n
        mb.cylinder((math.cos(a) * 2.5, math.sin(a) * 2.5, 0), (math.cos(a) * 2.5, math.sin(a) * 2.5, 2.25), 0.05, 0.045, "pole", segments=6)
    mb.cylinder((0, 0, 0), (0, 0, 4.6), 0.07, 0.05, "pole_dark", segments=6)
    mb.sphere((0, 0, 4.65), 0.12, "gold", segments=6, rings=4)
    w = {"pennant": 1.0}
    solid(mb, [(0.03, -0.015, 5.3), (1.0, -0.015, 5.1), (0.03, -0.015, 4.9)], (0, 0.03, 0), "awning_red", w)
    mb.cylinder((0, 0, 4.7), (0, 0, 5.35), 0.02, 0.02, "pole_dark", segments=4)
    mb.cylinder((0, 0, 0), (0, 0, 0.03), 2.4, 2.4, "carpet", segments=8)
    mb.cylinder((0, 0, 0), (0, 0, 0.04), 1.5, 1.5, "carpet_b", segments=8)
    mb.cylinder((0, 0, 0), (0, 0, 0.05), 0.8, 0.8, "carpet", segments=8)
    table(mb, 0, 0.5, 1.6, 0.7, 0.6, "plank_dark")
    for k in range(5):
        mb.cylinder((-0.6 + 0.3 * k, 0.5, 0.63), (-0.6 + 0.3 * k, 0.5, 0.8 + 0.06 * (k % 2)), 0.07, 0.05, ("gold", "glaze", "brass", "glow_potion", "gold")[k], segments=7)
    mb.box((1.3, 0.9, 0.3), (0.8, 0.5, 0.5), "plank_dark")                        # A chest of coin.
    mb.box((1.3, 0.9, 0.57), (0.84, 0.54, 0.06), "iron")
    mb.box((1.3, 0.64, 0.4), (0.1, 0.03, 0.14), "gold")
    for k, mat in enumerate(("cloth_a", "cloth_b", "cloth_c")):
        mb.cylinder((-1.5, 0.3 + 0.3 * k, 0.14), (-0.9, 0.5 + 0.3 * k, 0.14), 0.12, 0.12, mat, segments=8)
    for k in range(3):
        mb.sphere((-1.2 + 0.5 * k, -1.2, 0.14), 0.3, ("awning_red", "awning_violet", "awning_yellow")[k], segments=7, rings=4, scale=(1, 1, 0.4))   # Cushions.
    _shapes.lantern(mb, 1.6, -1.6, 0.0)
    pose = lambda t: ({"pennant": [(kit.Z, 20.0 * math.sin(TAU * t))]}, {})   # noqa: E731
    kit.save(mb, FAMILY, "trade_pavilion", COLORS, mech=kit.Mech([("pennant", (0.03, 0, 5.1), (1.0, 0, 5.1), None)]).clip("flutter", 1.8, pose))


def money_changer():
    mb = kit.begin()
    mb.box((0, 0, 0.06), (3.0, 2.4, 0.12), "stone_dark")
    for sx in (-1.3, 1.3):
        mb.box((sx, 1.0, 1.4), (0.14, 0.14, 2.6), "pole")
        mb.box((sx, -1.0, 1.2), (0.14, 0.14, 2.2), "pole")
    shed_roof(mb, 0, 0, 2.8, 2.2, 2.25, 2.7, ("shingle", "shingle_dark"), 0.25, 3)
    for k in range(10):
        mb.box((-1.25 + 0.28 * k, 1.0, 1.3), (0.26, 0.06, 2.3), "plank" if k % 2 else "plank_light")
    for k in range(9):                                                           # Iron bars over the counter.
        mb.cylinder((-1.1 + 0.275 * k, -1.0, 1.0), (-1.1 + 0.275 * k, -1.0, 2.2), 0.018, 0.018, "iron", segments=4)
    mb.box((0, -1.0, 0.56), (2.6, 0.1, 0.88), "plank_dark")
    mb.box((0, -0.9, 1.02), (2.7, 0.5, 0.06), "plank")
    for k in range(4):                                                           # Stacks of coin.
        h = 0.05 + 0.03 * ((k * 3) % 4)
        mb.cylinder((-0.6 + 0.2 * k, -0.85, 1.05), (-0.6 + 0.2 * k, -0.85, 1.05 + h), 0.045, 0.045, "gold" if k % 2 else "steel", segments=7)
    mb.cylinder((0.5, -0.85, 1.05), (0.5, -0.85, 1.35), 0.015, 0.015, "brass", segments=4)
    beam(mb, (0.25, -0.85, 1.35), (0.75, -0.85, 1.35), 0.012, "brass")
    for sx in (-1, 1):
        mb.cylinder((0.5 + sx * 0.25, -0.85, 1.14), (0.5 + sx * 0.25, -0.85, 1.16), 0.08, 0.09, "brass", segments=7)
        rope(mb, (0.5 + sx * 0.25, -0.85, 1.35), (0.5 + sx * 0.25, -0.85, 1.16), 0.005)
    mb.box((0.6, 0.5, 0.42), (0.9, 0.6, 0.6), "iron")                            # The strongbox.
    mb.box((0.6, 0.5, 0.74), (0.94, 0.64, 0.06), "plank_dark")
    mb.box((0.6, 0.19, 0.5), (0.12, 0.03, 0.16), "brass")
    mb.box((-0.6, 0.4, 0.35), (0.4, 0.4, 0.46), "plank")
    w = {"sign": 1.0}
    beam(mb, (1.3, -1.0, 2.2), (2.0, -1.0, 2.2), 0.025, "iron")
    mb.cylinder((1.7, -1.03, 1.85), (1.7, -0.97, 1.85), 0.26, 0.26, "gold", w, segments=10)
    mb.box((1.7, -1.04, 1.85), (0.06, 0.02, 0.3), "ink", w)
    rope(mb, (1.7, -1.0, 2.2), (1.7, -1.0, 2.1), 0.008, w)
    pose = lambda t: ({"sign": [(kit.X, 7.0 * math.sin(TAU * t))]}, {})   # noqa: E731
    kit.save(mb, FAMILY, "trade_money_changer", COLORS, mech=kit.Mech([("sign", (1.7, -1.0, 2.2), (1.7, -1.0, 1.6), None)]).clip("swing", 3.0, pose))


def auction_block():
    mb = kit.begin()
    mb.box((0, 0, 0.5), (4.0, 3.0, 0.12), "plank")
    for sx in (-1.8, 0, 1.8):
        for sy in (-1.3, 1.3):
            mb.box((sx, sy, 0.25), (0.14, 0.14, 0.5), "pole_dark")
    for k in range(3):
        mb.box((0, -1.7 - 0.3 * k, 0.33 - 0.14 * k), (1.4, 0.3, 0.1), "plank_light")
    mb.box((-1.2, -0.9, 1.1), (0.6, 0.45, 1.1), "plank_dark")                    # The auctioneer's desk and gavel.
    mb.box((-1.2, -0.95, 1.68), (0.7, 0.55, 0.06), "plank")
    mb.cylinder((-1.3, -0.95, 1.74), (-1.1, -0.95, 1.74), 0.05, 0.05, "pole_dark", segments=6)
    beam(mb, (-1.2, -0.95, 1.74), (-1.2, -0.7, 1.74), 0.015, "pole")
    crate(mb, 0.8, 0.2, 0.56, 0.7)                                               # The lots.
    barrel(mb, 1.5, 0.6, 0.56, 0.8, 0.3)
    mb.cylinder((0.3, 0.9, 0.56), (0.3, 0.9, 1.1), 0.16, 0.24, "clay", segments=8)
    mb.cylinder((0.3, 0.9, 1.1), (0.3, 0.9, 1.3), 0.24, 0.12, "glaze", segments=8)
    for sx in (-1.9, 1.9):
        mb.cylinder((sx, 1.4, 0.5), (sx, 1.4, 3.2), 0.05, 0.04, "pole", segments=6)
    for k in range(7):
        x0, x1 = -1.9 + 3.8 * k / 7, -1.9 + 3.8 * (k + 1) / 7
        z0, z1 = 3.1 - 0.35 * math.sin(math.pi * k / 7), 3.1 - 0.35 * math.sin(math.pi * (k + 1) / 7)
        rope(mb, (x0, 1.4, z0), (x1, 1.4, z1), 0.01)
        solid(mb, [(x0, 1.39, z0), (x1, 1.39, z1), ((x0 + x1) / 2, 1.39, (z0 + z1) / 2 - 0.3)], (0, 0.02, 0), ("awning_red", "awning_yellow", "awning_blue")[k % 3])
    w = {"bell": 1.0}
    mb.cylinder((-1.9, -1.4, 0.5), (-1.9, -1.4, 2.4), 0.05, 0.04, "pole", segments=6)
    beam(mb, (-1.9, -1.4, 2.35), (-1.5, -1.4, 2.35), 0.025, "iron")
    mb.cylinder((-1.55, -1.4, 2.3), (-1.55, -1.4, 2.08), 0.04, 0.13, "bell", w, segments=8)
    pose = lambda t: ({"bell": [(kit.Y, 28.0 * math.sin(TAU * 4 * t) * (1 - t))]}, {})   # noqa: E731
    kit.save(mb, FAMILY, "trade_auction_block", COLORS, mech=kit.Mech([("bell", (-1.55, -1.4, 2.33), (-1.55, -1.4, 2.08), None)]).clip("ring", 2.0, pose, loops=False))


def peddler_cart():
    """A peddler's handcart, hung with everything he sells."""
    mb = kit.begin()
    for sx in (-0.65, 0.65):
        wheel(mb, (sx, 0, 0.5), 0.5, None, 0.08)
    mb.cylinder((-0.65, 0, 0.5), (0.65, 0, 0.5), 0.04, 0.04, "iron", segments=6)
    mb.box((0, 0, 0.75), (1.1, 1.8, 0.5), "plank")
    mb.box((0, 0, 1.02), (1.16, 1.86, 0.05), "plank_dark")
    for sx in (-0.5, 0.5):
        beam(mb, (sx, -0.9, 0.7), (sx, -2.0, 0.95), 0.03, "pole")
        mb.cylinder((sx, 0.8, 1.0), (sx, 0.8, 2.3), 0.035, 0.03, "pole", segments=5)
        mb.cylinder((sx, -0.8, 1.0), (sx, -0.8, 2.3), 0.035, 0.03, "pole", segments=5)
    mb.cylinder((0, 0.9, 0.0), (0, 0.85, 0.5), 0.035, 0.035, "pole_dark", segments=5)
    solid(mb, [(-0.7, -1.0, 2.3), (0.7, -1.0, 2.3), (0.7, 0, 2.6), (-0.7, 0, 2.6)], (0, 0, 0.04), "awning_green")
    solid(mb, [(-0.7, 1.0, 2.3), (0.7, 1.0, 2.3), (0.7, 0, 2.6), (-0.7, 0, 2.6)], (0, 0, 0.04), "awning_yellow")
    w = {"wares": 1.0}
    for k in range(5):                                                           # Pots, pans and ribbons swing as he walks.
        y = -0.7 + 0.35 * k
        rope(mb, (0.56, y, 2.3), (0.56, y, 1.95), 0.006, w)
        if k % 2:
            mb.cylinder((0.56, y, 1.75), (0.56, y, 1.95), 0.1, 0.13, "clay" if k == 1 else "brass", w, segments=7)
        else:
            mb.cylinder((0.52, y, 1.8), (0.6, y, 1.8), 0.15, 0.15, "iron", w, segments=8)
        mb.box((-0.56, y, 1.9), (0.02, 0.1, 0.7), ("cloth_a", "cloth_b", "cloth_c", "cloth_d", "cloth_a")[k], w)
    for k in range(6):
        mb.cylinder((-0.3 + 0.3 * (k % 3), -0.4 + 0.5 * (k // 3), 1.05), (-0.3 + 0.3 * (k % 3), -0.4 + 0.5 * (k // 3), 1.3), 0.09, 0.07, ("glaze", "clay", "brass")[k % 3], segments=7)
    sack(mb, 0.0, 0.55, 1.04, 0.2)
    pose = lambda t: ({"wares": [(kit.Y, 6.0 * math.sin(TAU * t))]}, {})   # noqa: E731
    kit.save(mb, FAMILY, "trade_peddler_cart", COLORS, mech=kit.Mech([("wares", (0, 0, 2.3), (0, 0.5, 2.3), None)]).clip("jingle", 1.6, pose))


def courier_post():
    """A relay post: a fresh horse always saddled, and the message goes on."""
    mb = kit.begin()
    mb.box((-1.0, 1.5, 1.3), (3.6, 2.6, 2.6), "plank")
    for k in range(13):
        mb.box((-2.7 + 0.28 * k, 0.18, 1.3), (0.26, 0.05, 2.6), "plank_light" if k % 2 else "plank")
    gable_roof(mb, -1.0, 1.5, 3.6, 2.6, 2.6, 1.2, ("shingle", "shingle_dark"), 0.35, 3, 0.07, "plank_dark")
    mb.box((-1.6, 0.14, 1.0), (0.9, 0.06, 1.8), "plank_dark")
    mb.box((-0.2, 0.14, 1.6), (0.7, 0.06, 0.6), "window")
    mb.box((-0.2, 0.1, 1.25), (0.9, 0.3, 0.06), "plank_dark")
    mb.box((-2.45, 0.1, 1.5), (0.5, 0.12, 0.7), "plank_dark")                    # Pigeonholes for letters by the door.
    for k in range(2):
        for j in range(3):
            mb.box((-2.57 + 0.24 * k, 0.03, 1.28 + 0.22 * j), (0.18, 0.02, 0.16), "cave")
            if (k + j) % 2:
                mb.box((-2.57 + 0.24 * k, 0.02, 1.26 + 0.22 * j), (0.14, 0.02, 0.08), "parchment")
    beam(mb, (0.8, 0.15, 2.5), (1.6, 0.15, 2.5), 0.025, "iron")
    w = {"sign": 1.0}
    mb.box((1.2, 0.15, 2.15), (0.6, 0.05, 0.5), "plank", w)
    solid(mb, [(1.0, 0.12, 2.05), (1.4, 0.12, 2.05), (1.4, 0.12, 2.28), (1.2, 0.12, 2.15), (1.0, 0.12, 2.28)], (0, -0.015, 0), "parchment", w)   # A letter.
    for sx in (-0.25, 0.25):
        rope(mb, (1.2 + sx, 0.15, 2.5), (1.2 + sx, 0.15, 2.4), 0.008, w)
    shed_roof(mb, 2.2, 1.6, 2.4, 2.6, 2.0, 2.5, ("thatch", "thatch_dark"), 0.2, 3)             # The stall for the relay horse.
    for sx in (1.1, 3.3):
        mb.cylinder((sx, 0.4, 0), (sx, 0.4, 2.05), 0.07, 0.06, "pole", segments=6)
        mb.cylinder((sx, 2.8, 0), (sx, 2.8, 2.5), 0.07, 0.06, "pole", segments=6)
    beam(mb, (1.1, 0.4, 1.0), (3.3, 0.4, 1.0), 0.04, "pole_dark")
    horse = _animals.draft_animal(mb, 1.4, "h_", "horse", "coat_grey", "mane_dark", x=2.2, harness=False)
    wb = {"h_body": 1.0}
    mb.box((2.2, 1.45, 1.66), (0.5, 0.6, 0.1), "leather", wb)                     # Saddle and saddlebags.
    for sx in (-1, 1):
        mb.box((2.2 + sx * 0.38, 1.7, 1.4), (0.14, 0.34, 0.3), "leather", wb)
        mb.box((2.2 + sx * 0.39, 1.7, 1.5), (0.15, 0.36, 0.05), "brass", wb)
    mb.cylinder((2.9, 0.9, 0), (2.9, 0.9, 0.4), 0.2, 0.26, "plank_light", segments=8)
    mb.sphere((-3.2, -0.6, 0.0), 0.5, "hay", segments=7, rings=4, scale=(1.2, 1.0, 0.6))
    mb.cylinder((-3.4, 0.6, 0), (-3.4, 0.6, 3.6), 0.06, 0.045, "pole", segments=6)             # A horn to announce the rider.
    mb.cylinder((-3.4, 0.5, 3.3), (-3.4, -0.1, 3.4), 0.03, 0.12, "brass", segments=7)

    def idle(t):
        turns, moves = horse["idle"](t)
        turns["sign"] = [(kit.X, 8.0 * math.sin(TAU * t))]
        return turns, moves

    mech = kit.Mech(horse["bones"] + [("sign", (1.2, 0.15, 2.5), (1.2, 0.15, 1.9), None)]).clip("idle", 4.0, idle)
    kit.save(mb, FAMILY, "trade_courier_post", COLORS, mech=mech)


MODELS = {"trade_stall_" + k: stall(k) for k in STALLS}
MODELS.update({
    "trade_market_cross": market_cross("trade_market_cross", False),
    "trade_market_cross_roofed": market_cross("trade_market_cross_roofed", True),
    "trade_weigh_house": weigh_house,
    "trade_caravan_3": caravan("trade_caravan_3", 3),
    "trade_caravan_5": caravan("trade_caravan_5", 5),
    "trade_post": trading_post,
    "trade_pavilion": merchant_pavilion,
    "trade_money_changer": money_changer,
    "trade_auction_block": auction_block,
    "trade_peddler_cart": peddler_cart,
    "trade_courier_post": courier_post,
})

kit.run(MODELS, FAMILY)
