"""Farm proposals: livestock buildings with their animals, crops in three
stages of growth, irrigation and the yard of a farm. See ../LEEME.md.

    blender --background --factory-startup --python art/blender/proposals/farm/build.py -- [ids]
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
from _animals import draft_animal  # noqa: E402
from _shapes import (TAU, barrel, beam, gable_roof, log, merged, plank_box, rock, rope, sack, shed_roof, solid, wheel)  # noqa: E402

FAMILY = "farm"
C = common.rgb
COLORS = {
    **_shapes.COLORS, **_animals.COLORS,
    "thatch": C(0xC9A55A), "thatch_dark": C(0xA8863F), "shingle": C(0x6A5038), "shingle_dark": C(0x54402C),
    "tile": C(0x9A4A2E), "tile_dark": C(0x7E3A24), "barn_red": C(0x8E3A2E), "barn_red_dark": C(0x742E24), "barn_trim": C(0xE8E0D0),
    "plaster": C(0xE6DCC4), "cave": C(0x14110F), "soil": C(0x6A4A30), "soil_dark": C(0x553A26), "mud": C(0x5A4632),
    "sprout": C(0x7AB84A), "green": C(0x4F8A34), "green_dark": C(0x3A6A28), "wheat": C(0xE0B84A), "wheat_dark": C(0xC09A34),
    "barley": C(0xD8C87A), "barley_dark": C(0xB8A85A), "flax_blue": C(0x6A8AE0), "cabbage": C(0x7AAA5A), "cabbage_light": C(0xB4D68A),
    "pod": C(0xA8D060), "beet": C(0x8A2A5A), "turnip": C(0xECE6DA), "glass": C(0xBFE4F0), "glass_light": C(0xDCF2F8),
    "cheese": C(0xE8C050), "tomato": C(0xC83A2A), "grape": C(0x5A2A7A), "vine_leaf": C(0x5A8A34), "water": C(0x4A8FC0),
    "wicker": C(0xB08A4A), "milk": C(0xF4F0E4), "grass": C(0x6A9440),
}


def blade(mb, x, y, h, lean, a, mat, w, width=0.05):
    tx, ty = x + math.cos(a) * lean, y + math.sin(a) * lean
    px, py = -math.sin(a) * width / 2, math.cos(a) * width / 2
    solid(mb, [(x - px, y - py, 0.12), (x + px, y + py, 0.12), (tx, ty, 0.12 + h)], (math.cos(a) * 0.015, math.sin(a) * 0.015, 0), mat, w)


def sway_pose(bones, amp):
    def pose(t):
        return {b: [(kit.X, amp * math.sin(TAU * t + i * 1.1)), (kit.Y, amp * 0.6 * math.sin(TAU * 2 * t + i * 1.9))] for i, b in enumerate(bones)}, {}
    return pose


# --- Livestock -----------------------------------------------------------------------------------


def barn(name, stone):
    def build():
        mb = kit.begin()
        w, d, h = 10.0, 7.0, 3.4
        walls = ("stone", "stone_light") if stone else ("barn_red", "barn_red_dark")
        roof = ("tile", "tile_dark") if stone else ("thatch", "thatch_dark")
        mb.box((0, 0, 0.3), (w + 0.2, d + 0.2, 0.6), "stone_dark")
        if stone:
            mb.box((0, 0, (h + 0.6) / 2), (w, d, h - 0.6), "stone")
            for k in range(5):
                mb.box((0, 0, 1.0 + 0.5 * k), (w + 0.04, d + 0.04, 0.05), "stone_dark")
        else:
            plank_box(mb, 0, 0, w, d, 0.6, h, walls)
        gable_roof(mb, 0, 0, w, d, h, 3.0, roof, 0.45, 4, 0.09, gable=walls[0])
        mb.box((0, -d / 2 - 0.01, 2.1), (3.3, 0.06, 3.1), "barn_trim")                 # The great door, in its frame.
        mb.box((0, -d / 2 - 0.02, 2.05), (3.0, 0.06, 2.9), "cave")
        bones = []
        for sx, bone in ((-1, "door_l"), (1, "door_r")):
            wd = {bone: 1.0}
            x0, x1 = sx * 1.5, sx * 0.02
            solid(mb, [(x0, -d / 2 - 0.06, 0.62), (x1, -d / 2 - 0.06, 0.62), (x1, -d / 2 - 0.06, 3.48), (x0, -d / 2 - 0.06, 3.48)], (0, -0.07, 0), walls[0], wd)
            for zz in (0.8, 2.05, 3.3):
                mb.box(((x0 + x1) / 2, -d / 2 - 0.14, zz), (1.46, 0.03, 0.14), "barn_trim", wd)
            beam(mb, (x0 - sx * 0.05, -d / 2 - 0.15, 0.85), (x1 + sx * 0.03, -d / 2 - 0.15, 3.25), 0.05, "barn_trim", wd)
            bones.append((bone, (x0, -d / 2 - 0.08, 0.62), (x0, -d / 2 - 0.08, 3.4), None))
        for sx in (-3.5, 3.5):
            mb.box((sx, -d / 2 - 0.02, 2.3), (0.9, 0.06, 0.9), "barn_trim")
            mb.box((sx, -d / 2 - 0.04, 2.3), (0.7, 0.06, 0.7), "cave")
        mb.box((w / 2 + 0.02, 0, 4.6), (0.06, 1.3, 1.5), "cave")                          # The hayloft door, on the gable.
        mb.sphere((w / 2 + 0.1, 0, 4.2), 0.6, "hay", segments=7, rings=4, scale=(0.5, 1.0, 0.8))
        beam(mb, (w / 2 - 0.3, 0, 5.6), (w / 2 + 1.2, 0, 5.6), 0.08, "pole_dark")
        rope(mb, (w / 2 + 1.1, 0, 5.55), (w / 2 + 1.1, 0, 3.2), 0.02)
        mb.cylinder((w / 2 + 1.1, 0, 3.0), (w / 2 + 1.1, 0, 3.2), 0.1, 0.02, "iron", segments=6)
        mb.sphere((w / 2 + 1.6, 1.6, 0.0), 1.3, "hay", segments=8, rings=4, scale=(1, 1, 0.7))
        beam(mb, (w / 2 + 1.2, 0.9, 0.0), (w / 2 + 1.5, 1.4, 1.8), 0.025, "pole")
        barrel(mb, -w / 2 - 0.6, -2.4, 0.0)
        log(mb, (-w / 2 - 0.5, -1.4, 0.2), (-w / 2 - 0.5, 0.6, 0.2), 0.2)

        def swing(opening):
            def pose(t):
                s = kit.smooth(t) if opening else 1 - kit.smooth(t)
                return {"door_l": [(kit.Z, -100.0 * s)], "door_r": [(kit.Z, 100.0 * s)]}, {}
            return pose

        mech = kit.Mech(bones).clip("open", 2.0, swing(True), loops=False).clip("close", 2.0, swing(False), loops=False)
        kit.save(mb, FAMILY, name, COLORS, mech=mech)
    return build


def cowshed():
    mb = kit.begin()
    w, d = 9.0, 4.2
    mb.box((0, 0, 0.06), (w + 0.2, d + 0.2, 0.12), "stone_dark")
    plank_box(mb, 0, 0, w, d, 0.12, 2.3, open_front=True)
    for sx in (-1.5, 1.5):
        mb.box((sx, 0.3, 0.75), (0.08, d - 0.8, 1.2), "plank_dark")
        mb.cylinder((sx, -d / 2, 0.12), (sx, -d / 2, 2.3), 0.08, 0.07, "pole", segments=6)
    shed_roof(mb, 0, 0, w, d, 2.3, 3.1, ("thatch", "thatch_dark"), 0.3, 4)
    mb.box((0, 1.6, 0.6), (w - 0.4, 0.5, 0.5), "plank")                                # The manger along the back.
    mb.box((0, 1.6, 0.9), (w - 0.5, 0.4, 0.12), "hay")
    mb.box((0, 0, 0.14), (w - 0.3, d - 0.3, 0.05), "hay_dark")
    cows = [draft_animal(mb, 0.2, "c0_", "cow", "coat_cow", "mane_dark", x=-3.0, harness=False, turn=180),
            draft_animal(mb, 0.25, "c1_", "cow", "coat_ox", "mane_dark", x=0.0, harness=False, turn=180)]
    for k, (x, y) in enumerate(((2.6, -0.6), (3.2, -0.9), (2.9, -1.3))):                # Milk in the third stall.
        mb.cylinder((x, y, 0.14), (x, y, 0.5), 0.15, 0.18, "plank_light", segments=8)
        mb.cylinder((x, y, 0.46), (x, y, 0.49), 0.15, 0.15, "milk", segments=8)
    mb.cylinder((3.3, 0.6, 0.14), (3.3, 0.6, 0.55), 0.2, 0.16, "pole", segments=7)       # A milking stool and hay.
    mb.sphere((2.3, 1.0, 0.3), 0.7, "hay", segments=7, rings=4, scale=(1, 1, 0.7))
    feed = merged(lambda t: cows[0]["graze"](t), lambda t: cows[1]["graze"](t, 2.0))
    kit.save(mb, FAMILY, "farm_cowshed", COLORS, mech=kit.Mech(cows[0]["bones"] + cows[1]["bones"]).clip("feed", 6.0, feed))


def sheepfold(flock=True):
    """`flock` False: the fold alone, for the game (phase 107), which draws the animals it has."""
    mb = kit.begin()
    rnd = random.Random(2)
    r = 4.2
    n = 30
    for i in range(n):
        a = TAU * i / n
        if abs(a - 1.5 * math.pi) < 0.26:
            continue   # The gate.
        rock(mb, math.cos(a) * r, math.sin(a) * r, 0.3, rnd.uniform(0.42, 0.52), rnd)
        rock(mb, math.cos(a + 0.1) * r, math.sin(a + 0.1) * r, 0.75, rnd.uniform(0.3, 0.38), rnd)
    for sx in (-1.0, 1.0):
        mb.cylinder((sx, -r, 0), (sx, -r, 1.2), 0.07, 0.06, "pole", segments=6)
    for zz in (0.4, 0.8):
        beam(mb, (-1.0, -r - 0.06, zz), (1.0, -r - 0.06, zz), 0.035, "plank_light")
    beam(mb, (-1.0, -r - 0.06, 0.35), (1.0, -r - 0.06, 0.85), 0.03, "plank_light")
    for sx in (-1.5, 0.3):                                                             # A low shelter inside.
        mb.cylinder((sx, 2.6, 0), (sx, 2.6, 1.3), 0.06, 0.05, "pole", segments=6)
        mb.cylinder((sx, 1.4, 0), (sx, 1.4, 0.95), 0.06, 0.05, "pole", segments=6)
    shed_roof(mb, -0.6, 2.0, 2.0, 1.2, 0.95, 1.3, ("thatch", "thatch_dark"), 0.2, 2)
    mb.sphere((-0.6, 2.1, 0.0), 0.7, "hay", segments=7, rings=3, scale=(1.2, 0.8, 0.4))
    log(mb, (1.6, 1.8, 0.16), (2.9, 1.2, 0.16), 0.17)                                   # A trough.
    mb.box((2.25, 1.5, 0.27), (1.1, 0.2, 0.04), "water", rotation_z=-0.43)
    if not flock:
        kit.save(mb, FAMILY, "farm_sheepfold_empty", COLORS)
        return
    spots = [(-1.6, -1.2, 30, "wool"), (0.9, -0.4, -70, "wool"), (-0.2, 0.6, 160, "wool"), (2.2, -1.9, 100, "wool_dark"), (-2.6, 0.9, -130, "wool")]
    sheep = [draft_animal(mb, y, "s%d_" % i, "sheep", coat, "mane_dark", x=x, harness=False, turn=turn) for i, (x, y, turn, coat) in enumerate(spots)]
    poses = [(lambda s, i: (lambda t: s["graze"](t, i * 1.4)))(s, i) if i % 3 != 2 else s["idle"] for i, s in enumerate(sheep)]
    kit.save(mb, FAMILY, "farm_sheepfold", COLORS, mech=kit.Mech([b for s in sheep for b in s["bones"]]).clip("graze", 6.0, merged(*poses)))


# --- Crops in three stages -----------------------------------------------------------------------

ROWS = [-1.6 + 0.64 * i for i in range(6)]


def bed(mb):
    mb.box((0, 0, 0.04), (4.0, 4.0, 0.08), "soil")
    for x in ROWS:
        mb.box((x, 0, 0.1), (0.38, 3.8, 0.08), "soil_dark")


def crop(name, kind, stage):
    def build():
        mb = kit.begin()
        rnd = random.Random({"wheat": 1, "barley": 2, "flax": 3, "vegetables": 4, "beans": 5, "roots": 6}[kind] * 10 + stage)
        bed(mb)
        bones = ["sway0", "sway1", "sway2"]
        animated = False
        if kind in ("wheat", "barley", "flax"):
            animated = stage > 0
            tall = {"wheat": 0.95, "barley": 0.85, "flax": 0.7}[kind]
            h = (0.14, tall * 0.55, tall)[stage]
            count = (2, 4, 5)[stage]
            if stage == 0:
                mats = ("sprout",)
            elif stage == 1 or kind == "flax":
                mats = ("green", "green_dark", "sprout")
            else:
                mats = (kind, kind + "_dark")
            for i, x in enumerate(ROWS):
                w = {bones[i % 3]: 1.0} if animated else None
                for k in range(9):
                    y = -1.7 + 0.425 * k
                    for _ in range(count):
                        px, py = x + rnd.uniform(-0.1, 0.1), y + rnd.uniform(-0.12, 0.12)
                        hh = h * rnd.uniform(0.85, 1.15)
                        a = rnd.uniform(0, TAU)
                        lean = hh * rnd.uniform(0.05, 0.2)
                        blade(mb, px, py, hh, lean, a, rnd.choice(mats), w)
                        if stage == 2:
                            tx, ty = px + math.cos(a) * lean, py + math.sin(a) * lean
                            if kind == "flax":
                                mb.sphere((tx, ty, 0.12 + hh), 0.045, "flax_blue", w, segments=5, rings=3)
                            else:
                                droop = 0.1 if kind == "barley" else 0.0
                                mb.cylinder((tx, ty, 0.1 + hh), (tx + math.cos(a) * droop, ty + math.sin(a) * droop, 0.26 + hh - droop), 0.03, 0.012, kind, w, segments=4)
        elif kind == "vegetables":
            for i, x in enumerate(ROWS):
                for k in range(7):
                    y = -1.65 + 0.55 * k
                    if i % 2 == 0:   # Cabbages.
                        r = (0.05, 0.13, 0.23)[stage]
                        mb.sphere((x, y, 0.12 + r * 0.7), r, "cabbage" if stage else "sprout", segments=6, rings=4, scale=(1, 1, 0.8))
                        if stage == 2:
                            mb.sphere((x, y, 0.12 + r * 1.0), r * 0.6, "cabbage_light", segments=6, rings=4)
                    else:            # Carrots: only the tops show.
                        for _ in range((1, 3, 5)[stage]):
                            blade(mb, x + rnd.uniform(-0.05, 0.05), y + rnd.uniform(-0.05, 0.05), (0.08, 0.2, 0.34)[stage], 0.08, rnd.uniform(0, TAU), "sprout" if stage < 2 else "green", None, 0.06)
                        if stage == 2:
                            mb.cylinder((x, y, 0.1), (x, y, 0.16), 0.045, 0.04, "tomato", segments=5)
        elif kind == "beans":
            for x in ROWS[::2]:
                for k in range(4):
                    y = -1.5 + 1.0 * k
                    for j in range(3):   # A teepee of three poles.
                        a = TAU * j / 3 + 0.5
                        mb.cylinder((x + 0.32 + math.cos(a) * 0.3, y + math.sin(a) * 0.3, 0.1), (x + 0.32, y, 1.9), 0.02, 0.015, "pole", segments=4)
                        if stage == 0:
                            blade(mb, x + 0.32 + math.cos(a) * 0.3, y + math.sin(a) * 0.3, 0.14, 0.03, a, "sprout", None, 0.07)
                    if stage:
                        top = (0.9, 1.75)[stage - 1]
                        for z in [0.3 + 0.28 * n for n in range(int((top - 0.3) / 0.28) + 1)]:
                            rr = 0.3 * (1.9 - z) / 1.8 + 0.1
                            mb.sphere((x + 0.32, y, z), rr, "green" if int(z * 10) % 2 else "green_dark", segments=6, rings=3, scale=(1, 1, 0.6))
                            if stage == 2:
                                a = rnd.uniform(0, TAU)
                                mb.box((x + 0.32 + math.cos(a) * rr, y + math.sin(a) * rr, z - 0.08), (0.03, 0.03, 0.16), "pod")
        else:   # Roots: beets and turnips.
            for i, x in enumerate(ROWS):
                for k in range(7):
                    y = -1.65 + 0.55 * k
                    for _ in range((2, 4, 6)[stage]):
                        blade(mb, x + rnd.uniform(-0.04, 0.04), y + rnd.uniform(-0.04, 0.04), (0.1, 0.24, 0.36)[stage], (0.03, 0.1, 0.16)[stage], rnd.uniform(0, TAU),
                              ("sprout", "green", "green_dark")[stage], None, 0.09)
                    if stage == 2:
                        mb.sphere((x, y, 0.13), 0.09, "beet" if i % 2 else "turnip", segments=6, rings=4)
        if animated:
            mech = kit.Mech([(b, (0, 0, 0.12), (0, 0, 0.6), None) for b in bones]).clip("sway", 4.0, sway_pose(bones, 5.0 if stage == 2 else 3.0))
            kit.save(mb, FAMILY, name, COLORS, mech=mech)
        else:
            kit.save(mb, FAMILY, name, COLORS)
    return build


# --- The crops of the game (phase 90) --------------------------------------------------------------
#
# The proposals above are plots of 4 x 4 m with every stalk modeled (up to
# 5 500 triangles). A field of the game is drawn cell by cell, each cell of
# 2 x 2 m on its own piece of ground, and may have a hundred of them: so the
# game's plots are 2 x 2 m, with three furrows and 200 triangles at most,
# and a dense crop is a block with a few stalks standing out of it. They do
# not carry a skeleton: the game sways them in its vertex shader.

PLOT_ROWS = (-0.66, 0.0, 0.66)


def plot(name, kind, stage):
    def build():
        mb = kit.begin()
        rnd = random.Random({"wheat": 1, "barley": 2, "flax": 3, "vegetables": 4, "beans": 5, "roots": 6}[kind] * 100 + stage)

        def ridges():
            for x in PLOT_ROWS:
                mb.box((x, 0, 0.04), (0.4, 1.9, 0.08), "soil_dark")

        def tuft(x, y, h, mat, blades=2, lean=0.25, width=0.09):
            for _ in range(blades):
                a = rnd.uniform(0, TAU)
                tx, ty = x + math.cos(a) * h * lean, y + math.sin(a) * h * lean
                px, py = -math.sin(a) * width / 2, math.cos(a) * width / 2
                solid(mb, [(x - px, y - py, 0.06), (x + px, y + py, 0.06), (tx, ty, 0.06 + h)], (math.cos(a) * 0.02, math.sin(a) * 0.02, 0), mat)

        if kind in ("wheat", "barley", "flax"):
            tall = {"wheat": 0.95, "barley": 0.85, "flax": 0.7}[kind]
            if stage == 0:
                ridges()
                for x in PLOT_ROWS:
                    for k in range(5):
                        tuft(x + rnd.uniform(-0.08, 0.08), -0.8 + 0.4 * k + rnd.uniform(-0.08, 0.08), 0.16, "sprout", blades=1, width=0.07)
            else:
                # Each furrow as clumps of stalks: wider at the top, like a
                # sheaf, with a crown of ears (or of flowers) when ripe.
                ripe = stage == 2 and kind != "flax"
                tones = (kind, kind + "_dark") if ripe else ("green", "green_dark")
                crown = kind if ripe else "flax_blue" if stage == 2 else None
                h = tall * (0.55, 1.0)[stage - 1]
                if stage == 1:
                    ridges()
                for i, x in enumerate(PLOT_ROWS):
                    spots = (-0.64, 0.0, 0.64) if stage == 1 or i != 1 else (-0.32, 0.32)
                    for k, y in enumerate(spots):
                        px, py = x + rnd.uniform(-0.05, 0.05), y + rnd.uniform(-0.06, 0.06)
                        hh = h * rnd.uniform(0.9, 1.1)
                        body = hh * (0.8 if crown else 1.0)
                        mb.cylinder((px, py, 0.04), (px, py, body), 0.2, 0.33, tones[(i + k) % 2], segments=4)
                        if crown:
                            lean = 0.1 if kind == "barley" else 0.03
                            a = rnd.uniform(0, TAU)
                            mb.cylinder((px, py, body), (px + math.cos(a) * lean, py + math.sin(a) * lean, hh), 0.3, 0.1, crown, segments=4)
        elif kind == "vegetables":
            ridges()
            r = (0.07, 0.15, 0.24)[stage]
            for x in (PLOT_ROWS[0], PLOT_ROWS[2]):   # Cabbages on the outer furrows.
                for y in ((-0.6, 0.0, 0.6) if x < 0 else (-0.3, 0.45)):
                    mb.sphere((x, y, 0.08 + r * 0.7), r, ("sprout", "cabbage", "cabbage_light")[stage], segments=5, rings=3, scale=(1, 1, 0.8))
            for k in range(3):                       # Carrots in the middle: only the tops show.
                tuft(0.0, -0.6 + 0.6 * k, (0.1, 0.22, 0.36)[stage], "sprout" if stage < 2 else "green")
        elif kind == "beans":
            mb.box((0, 0, 0.04), (0.5, 1.9, 0.08), "soil_dark")
            for j in range(3):   # A teepee of three poles.
                a = TAU * j / 3 + 0.5
                mb.cylinder((math.cos(a) * 0.45, math.sin(a) * 0.45, 0.06), (0, 0, 1.9), 0.025, 0.018, "pole", segments=4)
                if stage == 0:
                    tuft(math.cos(a) * 0.45, math.sin(a) * 0.45, 0.16, "sprout", blades=1, width=0.08)
            if stage:
                top = (0.9, 1.7)[stage - 1]
                levels = (2, 4)[stage - 1]
                for n in range(levels):
                    z = 0.3 + (top - 0.3) * n / max(1, levels - 1)
                    rr = 0.38 * (1.9 - z) / 1.6 + 0.1
                    mb.sphere((0, 0, z), rr, "green" if n % 2 else "green_dark", segments=5, rings=3, scale=(1, 1, 0.6))
                    if stage == 2 and n < 3:
                        a = rnd.uniform(0, TAU)
                        mb.box((math.cos(a) * rr, math.sin(a) * rr, z - 0.08), (0.04, 0.04, 0.2), "pod")
        else:   # Roots: beets and turnips.
            ridges()
            for i, x in enumerate(PLOT_ROWS):
                for y in ((-0.6, 0.0, 0.6) if stage < 2 else (-0.45, 0.45)):
                    tuft(x, y, (0.12, 0.26, 0.38)[stage], ("sprout", "green", "green_dark")[stage])
                    if stage == 2:
                        mb.sphere((x, y, 0.1), 0.12, "beet" if i % 2 else "turnip", segments=4, rings=2)
        kit.save(mb, FAMILY, name, COLORS)
    return build


def vineyard(name, bare):
    def build():
        mb = kit.begin()
        rnd = random.Random(8)
        mb.box((0, 0, 0.03), (5.2, 6.4, 0.06), "soil")
        for x in (-1.7, 0.0, 1.7):
            for y in (-3.0, 0.0, 3.0):
                mb.cylinder((x, y, 0), (x, y, 1.6), 0.05, 0.045, "pole", segments=6)
            for zz in (0.8, 1.45):
                beam(mb, (x, -3.0, zz), (x, 3.0, zz), 0.012, "iron")
            for k in range(6):
                y = -2.5 + 1.0 * k
                beam(mb, (x, y, 0.05), (x + 0.05, y, 0.85), 0.04, "bark")
                beam(mb, (x + 0.05, y, 0.85), (x, y + 0.4, 1.45), 0.025, "bark")
                beam(mb, (x + 0.05, y, 0.85), (x, y - 0.4, 0.82), 0.025, "bark")
                if not bare:
                    for _ in range(4):
                        mb.sphere((x + rnd.uniform(-0.15, 0.15), y + rnd.uniform(-0.45, 0.45), rnd.uniform(0.9, 1.6)), rnd.uniform(0.2, 0.3), rnd.choice(("vine_leaf", "green")),
                                  segments=6, rings=3, scale=(0.7, 1.2, 0.8))
                    for _ in range(2):
                        gx, gy, gz = x + rnd.choice((-0.2, 0.2)), y + rnd.uniform(-0.3, 0.3), rnd.uniform(0.7, 1.1)
                        mb.cylinder((gx, gy, gz + 0.12), (gx, gy, gz - 0.12), 0.08, 0.02, "grape", segments=5)
        if not bare:
            mb.cylinder((2.4, -2.6, 0), (2.4, -2.6, 0.4), 0.26, 0.32, "wicker", segments=8)
            mb.sphere((2.4, -2.6, 0.42), 0.26, "grape", segments=7, rings=4, scale=(1, 1, 0.5))
        kit.save(mb, FAMILY, name, COLORS)
    return build


# --- Irrigation ----------------------------------------------------------------------------------


def canal(name, kind):
    """A 2 m piece of irrigation ditch along Y; the corner turns from south to east."""
    def build():
        mb = kit.begin()
        if kind == "corner":
            mb.box((0.0, -0.3, 0.06), (0.8, 1.4, 0.12), "water")
            mb.box((0.3, 0.0, 0.06), (1.4, 0.8, 0.12), "water")
            mb.box((-0.6, -0.2, 0.14), (0.4, 1.6, 0.28), "soil")
            mb.box((0.2, 0.6, 0.14), (2.0, 0.4, 0.28), "soil")
            mb.box((0.8, -0.7, 0.14), (0.4, 0.6, 0.28), "soil")
            mb.box((0.6, -0.5, 0.14), (0.4, 0.3, 0.28), "soil_dark")
        else:
            mb.box((0, 0, 0.06), (0.8, 2.0, 0.12), "water")
            for sx in (-1, 1):
                mb.box((sx * 0.6, 0, 0.14), (0.4, 2.0, 0.28), "soil")
                for k in range(3):
                    mb.sphere((sx * 0.72, -0.7 + 0.7 * k, 0.28), 0.14, "grass", segments=5, rings=3, scale=(1, 1.4, 0.5))
        if kind != "sluice":
            kit.save(mb, FAMILY, name, COLORS)
            return
        for sx in (-1, 1):
            mb.box((sx * 0.5, 0, 0.7), (0.12, 0.14, 1.4), "pole_dark")
        mb.box((0, 0, 1.36), (1.2, 0.16, 0.12), "pole_dark")
        w = {"gate": 1.0}
        mb.box((0, 0, 0.36), (0.86, 0.06, 0.62), "plank", w)
        mb.box((0, -0.04, 0.36), (0.86, 0.02, 0.08), "iron", w)
        mb.cylinder((0, 0, 0.66), (0, 0, 1.5), 0.025, 0.025, "iron", w, segments=5)
        mb.cylinder((-0.2, 0, 1.52), (0.2, 0, 1.52), 0.03, 0.03, "pole", w, segments=5)

        def lift(up):
            return lambda t: ({}, {"gate": (0, 0, 0.5 * (kit.smooth(t) if up else 1 - kit.smooth(t)))})

        mech = kit.Mech([("gate", (0, 0, 0.36), (0, 0, 1.0), None)]).clip("open", 1.5, lift(True), loops=False).clip("close", 1.5, lift(False), loops=False)
        kit.save(mb, FAMILY, name, COLORS, mech=mech)
    return build


def shadoof():
    mb = kit.begin()
    rnd = random.Random(3)
    mb.cylinder((0, -2.6, 0), (0, -2.6, 0.1), 1.0, 1.0, "water", segments=9)               # The pool it dips into.
    for i in range(9):
        a = TAU * i / 9
        rock(mb, math.cos(a) * 1.1, -2.6 + math.sin(a) * 1.1, 0.1, 0.2, rnd)
    log(mb, (0, 0, 0), (0, 0, 2.5), 0.11)
    for sx in (-1, 1):
        beam(mb, (0, 0, 2.4), (sx * 0.22, 0, 2.95), 0.05, "bark")
    w = {"lever": 1.0}
    beam(mb, (0, -3.0, 3.3), (0, 2.0, 2.3), 0.07, "pole", w)
    mb.cylinder((-0.3, 0, 2.8), (0.3, 0, 2.8), 0.04, 0.04, "pole_dark", w, segments=6)
    mb.sphere((0, 2.0, 2.2), 0.36, "stone", w, segments=6, rings=4)                         # The counterweight.
    rope(mb, (0, 1.8, 2.36), (0, 2.1, 2.5), 0.03, w)
    wb = {"bucket": 1.0}
    rope(mb, (0, -2.95, 3.28), (0, -2.95, 1.0), 0.015, wb)
    mb.cylinder((0, -2.95, 0.7), (0, -2.95, 1.0), 0.14, 0.18, "plank_light", wb, segments=8)
    mb.cylinder((0, -2.95, 0.96), (0, -2.95, 0.99), 0.15, 0.15, "water", wb, segments=8)
    mb.box((0.9, -1.2, 0.2), (0.5, 2.2, 0.1), "plank_dark")                                 # A chute to the field.
    mb.box((0.9, -1.2, 0.27), (0.36, 2.2, 0.04), "water")
    for y in (-2.0, -0.4):
        mb.box((0.9, y, 0.08), (0.6, 0.1, 0.16), "pole_dark")

    def lift(t):
        a = 14.0 * math.sin(TAU * t)
        return {"lever": [(kit.X, a)], "bucket": [(kit.X, -a)]}, {}

    mech = kit.Mech([("lever", (0, 0, 2.8), (0, -1.0, 2.9), None), ("bucket", (0, -2.95, 3.28), (0, -2.95, 2.3), "lever")]).clip("lift", 5.0, lift)
    kit.save(mb, FAMILY, "farm_shadoof", COLORS, mech=mech)


def noria():
    mb = kit.begin()
    mb.box((0, 0, 0.08), (1.4, 5.0, 0.16), "water")                                        # The channel it stands in.
    for sx in (-1, 1):
        mb.box((sx * 0.9, 0, 0.2), (0.4, 5.0, 0.4), "stone")
        beam(mb, (sx * 0.9, -1.2, 0.4), (sx * 0.9, 0, 1.9), 0.09, "pole")
        beam(mb, (sx * 0.9, 1.2, 0.4), (sx * 0.9, 0, 1.9), 0.09, "pole")
    wheel(mb, (-0.32, 0, 1.85), 1.6, "wheel", width=0.1)
    wheel(mb, (0.32, 0, 1.85), 1.6, "wheel", width=0.1)
    w = {"wheel": 1.0}
    mb.cylinder((-0.95, 0, 1.85), (0.95, 0, 1.85), 0.07, 0.07, "pole_dark", w, segments=7)
    for i in range(8):
        a = TAU * i / 8
        y, z = math.cos(a) * 1.6, 1.85 + math.sin(a) * 1.6
        mb.box((0, y, z), (0.5, 0.26, 0.26), "plank", w)
        mb.box((0, y, z), (0.44, 0.2, 0.28), "water", w)
    mb.box((1.3, 0.55, 3.2), (1.6, 0.5, 0.1), "plank_dark")                                # The trough that takes the water away.
    mb.box((1.3, 0.55, 3.28), (1.5, 0.36, 0.05), "water")
    for sx in (0.75, 1.9):
        mb.cylinder((sx, 0.55, 0), (sx, 0.55, 3.15), 0.06, 0.05, "pole", segments=6)
    mb.box((3.2, 0.55, 2.9), (2.3, 0.5, 0.1), "plank_dark", rotation_z=0.0)
    mb.box((3.2, 0.55, 2.98), (2.2, 0.36, 0.05), "water")
    for sx in (3.0, 4.2):
        mb.cylinder((sx, 0.55, 0), (sx, 0.55, 2.86), 0.06, 0.05, "pole", segments=6)
    pose = lambda t: ({"wheel": [(kit.X, 360 * t)]}, {})   # noqa: E731
    kit.save(mb, FAMILY, "farm_noria", COLORS, mech=kit.Mech([("wheel", (0, 0, 1.85), (0.5, 0, 1.85), None)]).clip("turn", 10.0, pose))


def windpump():
    mb = kit.begin()
    top = 5.6
    for sx in (-1, 1):
        for sy in (-1, 1):
            beam(mb, (sx * 1.0, sy * 1.0, 0), (sx * 0.25, sy * 0.25, top), 0.06, "pole")
    for k in range(4):
        z = 0.9 + 1.2 * k
        r = 1.0 - 0.75 * z / top
        for s in (-1, 1):
            beam(mb, (-r, s * r, z), (r, s * r, z), 0.035, "pole_dark")
            beam(mb, (s * r, -r, z), (s * r, r, z), 0.035, "pole_dark")
    mb.box((0, 0, top + 0.1), (0.7, 0.7, 0.12), "plank_dark")
    mb.cylinder((0, 0.3, top + 0.4), (0, -0.55, top + 0.4), 0.06, 0.06, "iron", segments=6)
    w = {"fan": 1.0}
    mb.cylinder((0, -0.5, top + 0.4), (0, -0.62, top + 0.4), 0.16, 0.16, "iron", w, segments=8)
    for i in range(8):
        a0, a1 = TAU * i / 8, TAU * (i + 0.6) / 8
        solid(mb, [(math.cos(a0) * 0.2, -0.58, top + 0.4 + math.sin(a0) * 0.2), (math.cos(a0) * 1.5, -0.6, top + 0.4 + math.sin(a0) * 1.5),
                   (math.cos(a1) * 1.5, -0.5, top + 0.4 + math.sin(a1) * 1.5), (math.cos(a1) * 0.2, -0.55, top + 0.4 + math.sin(a1) * 0.2)], (0, -0.02, 0),
              "plank_light" if i % 2 else "barn_trim", w)
    solid(mb, [(0, 0.3, top + 0.4), (0, 1.5, top + 0.9), (0, 1.7, top + 0.4), (0, 1.5, top - 0.1)], (0.03, 0, 0), "barn_red")   # The tail.
    wr = {"rod": 1.0}
    mb.cylinder((0, 0, 0.6), (0, 0, top + 0.3), 0.025, 0.025, "iron", wr, segments=5)
    mb.cylinder((0, 0, 0), (0, 0, 0.9), 0.12, 0.1, "iron", segments=7)
    mb.cylinder((0.1, 0, 0.6), (0.8, 0, 0.5), 0.04, 0.04, "iron", segments=6)
    log(mb, (0.6, -0.9, 0.2), (0.6, 1.1, 0.2), 0.22)                                       # The trough it fills.
    mb.box((0.6, 0.1, 0.36), (0.3, 1.8, 0.04), "water")

    def turn(t):
        return {"fan": [(kit.Y, 360 * 2 * t)]}, {"rod": (0, 0, 0.12 * math.sin(TAU * 2 * t))}

    mech = kit.Mech([("fan", (0, -0.55, top + 0.4), (0, -1.0, top + 0.4), None), ("rod", (0, 0, 0.6), (0, 0, top), None)]).clip("turn", 4.0, turn)
    kit.save(mb, FAMILY, "farm_windpump", COLORS, mech=mech)


def greenhouse():
    mb = kit.begin()
    rnd = random.Random(4)
    w, d, h = 4.0, 6.0, 2.0
    mb.box((0, 0, 0.2), (w + 0.2, d + 0.2, 0.4), "stone")
    for sx in (-1, 1):
        for k in range(4):
            y = -d / 2 + d * k / 3
            mb.box((sx * w / 2, y, 1.2), (0.09, 0.09, 1.6), "plank_dark")
        for k in range(3):
            y = -d / 2 + d * (k + 0.5) / 3
            mb.box((sx * w / 2, y, 1.2), (0.04, d / 3 - 0.1, 1.5), "glass" if k % 2 else "glass_light")
        mb.box((sx * w / 2, 0, 2.0), (0.1, d, 0.1), "plank_dark")
    for sy in (-1, 1):
        for sx in (-1.2, 1.2):
            mb.box((sx, sy * d / 2, 1.2), (w / 2 - 0.9, 0.04, 1.5), "glass")
        solid(mb, [(-w / 2, sy * d / 2, 2.0), (w / 2, sy * d / 2, 2.0), (0, sy * d / 2, 3.2)], (0, sy * 0.04, 0), "glass_light")
        for sx in (-0.5, 0.5):
            mb.box((sx, sy * d / 2, 1.2), (0.08, 0.08, 1.6), "plank_dark")
    mb.box((0, -d / 2 - 0.03, 1.15), (0.9, 0.05, 1.5), "plank")                             # The door.
    mb.box((0, -d / 2 - 0.05, 1.5), (0.6, 0.03, 0.6), "glass")
    for sx in (-1, 1):                                                                     # The glass roof, in panes.
        for k in range(4):
            y0, y1 = -d / 2 + d * k / 4, -d / 2 + d * (k + 1) / 4
            solid(mb, [(sx * (w / 2 + 0.1), y0 + 0.04, 1.95), (sx * (w / 2 + 0.1), y1 - 0.04, 1.95), (0, y1 - 0.04, 3.22), (0, y0 + 0.04, 3.22)], (0, 0, 0.04),
                  "glass" if (k + (sx > 0)) % 2 else "glass_light")
            beam(mb, (sx * (w / 2 + 0.1), y0, 1.98), (0, y0, 3.25), 0.035, "plank_dark")
        beam(mb, (sx * (w / 2 + 0.1), d / 2, 1.98), (0, d / 2, 3.25), 0.035, "plank_dark")
    beam(mb, (0, -d / 2, 3.25), (0, d / 2, 3.25), 0.05, "plank_dark")
    for sx in (-1.2, 1.2):                                                                 # Planters inside, seen through the door.
        mb.box((sx, 0, 0.6), (0.9, d - 0.8, 0.4), "plank")
        for k in range(7):
            y = -2.2 + 0.72 * k
            mb.sphere((sx, y, 1.0), 0.3, rnd.choice(("green", "green_dark", "sprout")), segments=6, rings=4, scale=(1, 1, 0.9))
            if k % 2:
                mb.sphere((sx + rnd.uniform(-0.2, 0.2), y, 1.15), 0.07, "tomato", segments=5, rings=3)
    barrel(mb, w / 2 + 0.6, -d / 2 + 0.6, 0.0, 0.8, 0.28)
    kit.save(mb, FAMILY, "farm_greenhouse", COLORS)


# --- Yard ----------------------------------------------------------------------------------------


def hay_barn():
    mb = kit.begin()
    for sx in (-3.0, 0.0, 3.0):
        for sy in (-2.0, 2.0):
            log(mb, (sx, sy, 0), (sx, sy, 3.4), 0.11)
        beam(mb, (sx, -2.0, 3.4), (sx, 2.0, 3.4), 0.08, "pole_dark")
    gable_roof(mb, 0, 0, 6.0, 4.0, 3.4, 1.9, ("thatch", "thatch_dark"), 0.5, 4, 0.1)
    for x, y, r in ((-1.7, 0.2, 1.6), (1.2, -0.2, 1.8), (0.0, 0.9, 1.3), (2.3, 0.8, 1.0)):
        mb.sphere((x, y, 0.0), r, "hay" if r > 1.2 else "hay_dark", segments=8, rings=4, scale=(1, 1, 0.95))
    beam(mb, (-3.3, -2.4, 0.0), (-2.6, -1.4, 3.3), 0.04, "pole")
    beam(mb, (-2.8, -2.6, 0.0), (-2.1, -1.6, 3.3), 0.04, "pole")
    for k in range(8):
        u = (k + 0.5) / 8.5
        beam(mb, (-3.3 + 0.7 * u, -2.4 + 1.0 * u, 3.3 * u), (-2.8 + 0.7 * u, -2.6 + 1.0 * u, 3.3 * u), 0.025, "pole_dark")
    beam(mb, (3.4, -2.5, 0.0), (3.1, -1.9, 1.6), 0.02, "pole")
    kit.save(mb, FAMILY, "farm_hay_barn", COLORS)


def silo(name, wood):
    def build():
        mb = kit.begin()
        body = "plank" if wood else "stone"
        mb.cylinder((0, 0, 0), (0, 0, 0.5), 1.9, 1.75, "stone_dark", segments=10)
        mb.cylinder((0, 0, 0.5), (0, 0, 6.2), 1.65, 1.55, body, segments=10)
        for k in range(5):
            z = 1.2 + 1.1 * k
            mb.cylinder((0, 0, z), (0, 0, z + 0.1), 1.68 - 0.017 * z, 1.68 - 0.017 * z, "iron" if wood else "stone_dark", segments=10)
        mb.cylinder((0, 0, 6.2), (0, 0, 6.45), 1.95, 1.95, "shingle_dark", segments=10)
        mb.cylinder((0, 0, 6.45), (0, 0, 8.6), 1.95, 0.0, "shingle", segments=10)
        mb.box((0, -1.62, 1.3), (0.9, 0.12, 1.7), "plank_dark")
        mb.box((0, -1.56, 4.6), (0.7, 0.12, 0.8), "cave")
        for sx in (-0.25, 0.25):
            beam(mb, (sx, -1.72, 2.2), (sx, -1.62, 4.2), 0.03, "pole")
        for k in range(6):
            beam(mb, (-0.25, -1.72 + 0.017 * k, 2.4 + 0.32 * k), (0.25, -1.72 + 0.017 * k, 2.4 + 0.32 * k), 0.02, "pole_dark")
        sack(mb, 1.2, -1.9, 0.0, 0.28)
        sack(mb, 1.7, -1.5, 0.0, 0.24)
        kit.save(mb, FAMILY, name, COLORS)
    return build


def dairy():
    mb = kit.begin()
    mb.box((0, 0.6, 0.1), (4.2, 3.4, 0.2), "stone_dark")
    mb.box((0, 0.6, 1.3), (4.0, 3.2, 2.2), "plaster")
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.box((sx * 2.0, 0.6 + sy * 1.6, 1.3), (0.14, 0.14, 2.25), "plank_dark")
    gable_roof(mb, 0, 0.6, 4.0, 3.2, 2.4, 1.5, ("thatch", "thatch_dark"), 0.35, 3, 0.09, gable="plaster")
    mb.box((-0.9, -1.02, 1.15), (0.9, 0.05, 1.9), "plank_dark")
    mb.box((0.9, -1.02, 1.5), (0.8, 0.05, 0.7), "window")
    mb.box((0.9, -1.2, 1.1), (1.2, 0.4, 0.06), "plank")                                    # A shelf of cheeses under the window.
    for k in range(4):
        mb.cylinder((0.45 + 0.3 * k, -1.2, 1.13), (0.45 + 0.3 * k, -1.2, 1.25), 0.13, 0.13, "cheese", segments=8)
    mb.cylinder((2.6, -1.5, 0), (2.6, -1.5, 0.9), 0.3, 0.22, "plank", segments=9)           # The churn.
    for zz in (0.2, 0.6):
        mb.cylinder((2.6, -1.5, zz), (2.6, -1.5, zz + 0.05), 0.3 - 0.09 * zz, 0.3 - 0.09 * zz, "iron", segments=9)
    mb.cylinder((2.6, -1.5, 0.9), (2.6, -1.5, 0.95), 0.24, 0.24, "plank_dark", segments=9)
    w = {"plunger": 1.0}
    mb.cylinder((2.6, -1.5, 0.6), (2.6, -1.5, 1.7), 0.025, 0.025, "pole", w, segments=5)
    mb.cylinder((2.5, -1.5, 1.7), (2.7, -1.5, 1.7), 0.03, 0.03, "pole_dark", w, segments=5)
    for k, (x, y) in enumerate(((-2.6, -1.4), (-3.0, -1.0), (-2.5, -0.8))):               # Milk cans.
        mb.cylinder((x, y, 0), (x, y, 0.55), 0.17, 0.17, "steel", segments=8)
        mb.cylinder((x, y, 0.55), (x, y, 0.7), 0.17, 0.09, "steel", segments=8)
        mb.cylinder((x, y, 0.7), (x, y, 0.74), 0.1, 0.1, "iron", segments=8)
    mb.cylinder((1.7, -1.9, 0), (1.7, -1.9, 0.4), 0.18, 0.18, "pole", segments=7)
    pose = lambda t: ({}, {"plunger": (0, 0, 0.16 * math.sin(TAU * t))})   # noqa: E731
    kit.save(mb, FAMILY, "farm_dairy", COLORS, mech=kit.Mech([("plunger", (2.6, -1.5, 0.9), (2.6, -1.5, 1.7), None)]).clip("churn", 1.0, pose))


def threshing_floor():
    mb = kit.begin()
    rnd = random.Random(6)
    mb.cylinder((0, 0, 0), (0, 0, 0.1), 3.3, 3.2, "stone_light", segments=12)
    for i in range(12):
        a = TAU * i / 12
        beam(mb, (math.cos(a) * 0.6, math.sin(a) * 0.6, 0.1), (math.cos(a) * 3.1, math.sin(a) * 3.1, 0.1), 0.02, "stone_dark")
    for a in (0.4, 1.5, 2.6, 3.7):                                                         # Stooks of sheaves.
        x, y = math.cos(a) * 2.1, math.sin(a) * 2.1
        mb.cylinder((x, y, 0.1), (x, y, 1.1), 0.5, 0.16, "wheat", segments=8)
        mb.cylinder((x, y, 1.1), (x, y, 1.45), 0.16, 0.34, "wheat_dark", segments=8)
        mb.cylinder((x, y, 0.75), (x, y, 0.82), 0.3, 0.3, "rope", segments=8)
    mb.sphere((0.2, 0.0, 0.1), 0.9, "wheat", segments=8, rings=4, scale=(1, 1, 0.4))        # The threshed grain.
    mb.sphere((1.5, -1.6, 0.1), 0.7, "hay", segments=7, rings=3, scale=(1.2, 1, 0.45))      # And the straw.
    for k in range(2):                                                                     # Flails.
        beam(mb, (-1.2 + 0.4 * k, -1.4, 0.14), (-0.4 + 0.4 * k, -2.4, 0.14), 0.025, "pole")
        beam(mb, (-0.4 + 0.4 * k, -2.4, 0.14), (0.1 + 0.4 * k, -2.5, 0.14), 0.035, "pole_dark")
    mb.cylinder((-1.9, 0.4, 0.1), (-1.9, 0.4, 0.2), 0.5, 0.56, "wicker", segments=9)        # A winnowing basket.
    mb.cylinder((-1.9, 0.4, 0.17), (-1.9, 0.4, 0.2), 0.48, 0.48, "wheat_dark", segments=9)
    for x, y in ((-3.5, -1.6), (-3.9, -1.1), (-3.4, -0.9)):
        sack(mb, x, y, 0.0, 0.28)
    kit.save(mb, FAMILY, "farm_threshing_floor", COLORS)


def feed_trough():
    mb = kit.begin()
    for sx in (-1.1, 1.1):
        for sy in (-0.25, 0.25):
            beam(mb, (sx, sy * 1.6, 0.0), (sx, sy * 0.6, 0.55), 0.04, "pole_dark")
    mb.box((0, 0, 0.6), (2.6, 0.5, 0.08), "plank_dark")
    for sy in (-1, 1):
        solid(mb, [(-1.3, sy * 0.25, 0.6), (1.3, sy * 0.25, 0.6), (1.3, sy * 0.36, 0.95), (-1.3, sy * 0.36, 0.95)], (0, sy * 0.04, 0), "plank")
    mb.box((0, 0, 0.82), (2.5, 0.5, 0.2), "hay")
    for sx in (-1.6, 1.6):                                                                 # A hay rack behind it.
        mb.cylinder((sx, 1.3, 0), (sx, 1.3, 1.7), 0.06, 0.05, "pole", segments=6)
    for k in range(9):
        x = -1.5 + 0.375 * k
        beam(mb, (x, 1.3, 0.7), (x, 0.9, 1.6), 0.02, "pole_dark")
        beam(mb, (x, 1.3, 0.7), (x, 1.7, 1.6), 0.02, "pole_dark")
    beam(mb, (-1.6, 0.9, 1.6), (1.6, 0.9, 1.6), 0.03, "pole")
    beam(mb, (-1.6, 1.7, 1.6), (1.6, 1.7, 1.6), 0.03, "pole")
    mb.sphere((0, 1.3, 1.35), 0.5, "hay", segments=7, rings=4, scale=(2.8, 0.7, 0.7))
    mb.box((2.2, 0.2, 0.15), (0.3, 0.3, 0.3), "barn_trim")                                 # A salt lick.
    kit.save(mb, FAMILY, "farm_feed_trough", COLORS)


MODELS = {
    "farm_barn": barn("farm_barn", False),
    "farm_barn_stone": barn("farm_barn_stone", True),
    "farm_cowshed": cowshed,
    "farm_sheepfold": sheepfold,
    "farm_sheepfold_empty": lambda: sheepfold(False),
    "farm_hay_barn": hay_barn,
    "farm_silo": silo("farm_silo", False),
    "farm_silo_wood": silo("farm_silo_wood", True),
    "farm_dairy": dairy,
    "farm_threshing_floor": threshing_floor,
    "farm_feed_trough": feed_trough,
    "farm_greenhouse": greenhouse,
    "farm_shadoof": shadoof,
    "farm_noria": noria,
    "farm_windpump": windpump,
    "farm_canal_straight": canal("farm_canal_straight", "straight"),
    "farm_canal_corner": canal("farm_canal_corner", "corner"),
    "farm_canal_sluice": canal("farm_canal_sluice", "sluice"),
    "farm_vineyard": vineyard("farm_vineyard", False),
    "farm_vineyard_bare": vineyard("farm_vineyard_bare", True),
}
for _kind in ("wheat", "barley", "flax", "vegetables", "beans", "roots"):
    for _stage in range(3):
        _name = "farm_crop_%s_%d" % (_kind, _stage + 1)
        MODELS[_name] = crop(_name, _kind, _stage)
        MODELS["crop_%s_%d" % (_kind, _stage + 1)] = plot("crop_%s_%d" % (_kind, _stage + 1), _kind, _stage)

kit.run(MODELS, FAMILY)
