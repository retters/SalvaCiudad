"""Signs and states of buildings: a hanging trade sign for each kind of
building, and a burnt ruin for each footprint size the game uses (like the
construction sites of phase 67, which are also generic by footprint).
See ../LEEME.md.

    blender --background --factory-startup --python art/blender/proposals/states/build.py -- [ids]
"""

import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import _kit as kit  # noqa: E402
import _shapes  # noqa: E402
import common  # noqa: E402
from _shapes import TAU, beam, rock, solid  # noqa: E402

FAMILY = "states"
C = common.rgb
COLORS = {
    **_shapes.COLORS,
    "board": C(0x8A6038), "board_edge": C(0x5A3B24), "paint_white": C(0xECE6D6), "paint_red": C(0xB8362E), "paint_blue": C(0x2F4E8C),
    "paint_yellow": C(0xE8B830), "paint_green": C(0x4F7A44), "paint_black": C(0x22201E), "bread": C(0xC08A48), "fish": C(0x9AA8B0),
    "meat": C(0x9A4A34), "hide": C(0x9A7050), "brick": C(0xA0553A), "water": C(0x4A8FC0), "wheat": C(0xE0B84A), "glass": C(0x7AD0C0),
    "char": C(0x1E1A18), "char_light": C(0x3A3430), "ash": C(0x6A6662), "ash_light": C(0x8E8A86), "ember": C(0xE85820), "smoke": C(0x7A7A7A),
    "stone_burnt": C(0x5A5650),
}
FOOTPRINTS = ((2, 2), (3, 3), (4, 2), (4, 4), (5, 4), (5, 5), (6, 5), (6, 6), (6, 8), (7, 6), (7, 7), (8, 6), (8, 7), (8, 8))


# --- Trade signs ----------------------------------------------------------------------------------
# The emblem is drawn on the plane of the board: (x across, z up), centered on the board.


def flat(mb, w, points, mat, depth=0.02):
    """The same shape on both faces of the board."""
    for side in (-1, 1):
        solid(mb, [(px, side * 0.025, 2.2 + pz) for px, pz in points], (0, side * depth, 0), mat, w)


def circle(cx, cz, r, n=10, squash=1.0):
    return [(cx + math.cos(TAU * i / n) * r, cz + math.sin(TAU * i / n) * r * squash) for i in range(n)]


def emblem(mb, w, kind):
    if kind == "bakery":      # A loaf with three cuts.
        flat(mb, w, circle(0, 0, 0.2, 10, 0.6), "bread")
        for k in (-0.09, 0, 0.09):
            flat(mb, w, [(k - 0.03, -0.06), (k + 0.01, -0.06), (k + 0.04, 0.06), (k, 0.06)], "board_edge", 0.03)
    elif kind == "tavern":    # A mug with foam.
        flat(mb, w, [(-0.12, -0.16), (0.08, -0.16), (0.08, 0.1), (-0.12, 0.1)], "paint_yellow")
        flat(mb, w, [(-0.14, 0.1), (0.1, 0.1), (0.1, 0.17), (-0.14, 0.17)], "paint_white")
        flat(mb, w, [(0.08, -0.08), (0.17, -0.08), (0.17, 0.05), (0.08, 0.05)], "paint_yellow")
    elif kind == "brewery":   # A barrel.
        flat(mb, w, [(-0.14, -0.17), (0.14, -0.17), (0.19, 0), (0.14, 0.17), (-0.14, 0.17), (-0.19, 0)], "board")
        for k in (-0.1, 0.1):
            flat(mb, w, [(-0.17, k - 0.02), (0.17, k - 0.02), (0.17, k + 0.02), (-0.17, k + 0.02)], "iron", 0.03)
    elif kind == "blacksmith":   # An anvil.
        flat(mb, w, [(-0.2, 0.04), (0.2, 0.04), (0.14, 0.13), (-0.12, 0.13), (-0.24, 0.1)], "iron")
        flat(mb, w, [(-0.08, -0.08), (0.08, -0.08), (0.06, 0.04), (-0.06, 0.04)], "iron")
        flat(mb, w, [(-0.15, -0.16), (0.15, -0.16), (0.12, -0.08), (-0.12, -0.08)], "iron")
    elif kind == "tailor":    # Scissors.
        for s in (-1, 1):
            flat(mb, w, [(s * 0.02, -0.02), (s * 0.06, 0.2), (0, 0.02)], "steel")
            flat(mb, w, circle(s * 0.07, -0.11, 0.055, 8), "paint_red")
            flat(mb, w, circle(s * 0.07, -0.11, 0.025, 6), "board", 0.03)
    elif kind == "cobbler":   # A boot.
        flat(mb, w, [(-0.1, -0.17), (0.17, -0.17), (0.17, -0.08), (0.03, -0.02), (0.03, 0.17), (-0.1, 0.17)], "hide")
        flat(mb, w, [(-0.1, -0.2), (0.17, -0.2), (0.17, -0.17), (-0.1, -0.17)], "paint_black")
    elif kind == "weaver":    # A spool of thread.
        flat(mb, w, [(-0.1, -0.12), (0.1, -0.12), (0.1, 0.12), (-0.1, 0.12)], "paint_blue")
        for k in (-0.15, 0.15):
            flat(mb, w, [(-0.15, k - 0.03), (0.15, k - 0.03), (0.15, k + 0.03), (-0.15, k + 0.03)], "board_edge", 0.03)
    elif kind == "herbalist":   # A leaf.
        flat(mb, w, [(0, -0.2), (0.14, -0.04), (0.1, 0.12), (0, 0.2), (-0.1, 0.12), (-0.14, -0.04)], "paint_green")
        flat(mb, w, [(-0.012, -0.2), (0.012, -0.2), (0.012, 0.16), (-0.012, 0.16)], "paint_white", 0.03)
    elif kind == "physician":   # A flask of red potion.
        flat(mb, w, circle(0, -0.06, 0.14, 10), "paint_red")
        flat(mb, w, [(-0.045, 0.04), (0.045, 0.04), (0.045, 0.17), (-0.045, 0.17)], "glass")
        flat(mb, w, [(-0.06, 0.17), (0.06, 0.17), (0.06, 0.2), (-0.06, 0.2)], "board_edge")
    elif kind == "market":    # Scales.
        flat(mb, w, [(-0.012, -0.18), (0.012, -0.18), (0.012, 0.18), (-0.012, 0.18)], "gold")
        flat(mb, w, [(-0.2, 0.13), (0.2, 0.13), (0.2, 0.16), (-0.2, 0.16)], "gold")
        for s in (-1, 1):
            flat(mb, w, [(s * 0.19 - 0.08, -0.06), (s * 0.19 + 0.08, -0.06), (s * 0.19 + 0.05, -0.1), (s * 0.19 - 0.05, -0.1)], "gold")
            flat(mb, w, [(s * 0.19 - 0.008, -0.06), (s * 0.19 + 0.008, -0.06), (s * 0.19 + 0.008, 0.13), (s * 0.19 - 0.008, 0.13)], "gold")
    elif kind == "trading_post":   # Coins.
        for cx, cz in ((-0.08, -0.08), (0.09, -0.05), (0.0, 0.09)):
            flat(mb, w, circle(cx, cz, 0.1, 9), "gold")
            flat(mb, w, circle(cx, cz, 0.05, 6), "paint_yellow", 0.03)
    elif kind == "vault":     # A key.
        flat(mb, w, circle(-0.12, 0, 0.09, 9), "gold")
        flat(mb, w, circle(-0.12, 0, 0.04, 6), "board", 0.03)
        flat(mb, w, [(-0.04, -0.02), (0.2, -0.02), (0.2, 0.02), (-0.04, 0.02)], "gold")
        for k in (0.1, 0.17):
            flat(mb, w, [(k, -0.09), (k + 0.03, -0.09), (k + 0.03, -0.02), (k, -0.02)], "gold")
    elif kind == "woodcutter":   # An axe.
        flat(mb, w, [(-0.16, -0.2), (-0.12, -0.2), (0.08, 0.2), (0.04, 0.2)], "plank_light")
        flat(mb, w, [(0.0, 0.04), (0.19, 0.0), (0.2, 0.17), (0.07, 0.2)], "steel")
    elif kind == "stonecutter":   # A pick.
        flat(mb, w, [(-0.02, -0.2), (0.02, -0.2), (0.02, 0.14), (-0.02, 0.14)], "plank_light")
        flat(mb, w, [(-0.22, 0.06), (0, 0.14), (0.22, 0.06), (0.2, 0.1), (0, 0.19), (-0.2, 0.1)], "steel")
    elif kind == "fisher":    # A fish.
        flat(mb, w, [(-0.2, 0), (-0.06, 0.1), (0.1, 0.06), (0.13, 0), (0.1, -0.06), (-0.06, -0.1)], "fish")
        flat(mb, w, [(0.11, 0), (0.22, 0.1), (0.22, -0.1)], "fish")
        flat(mb, w, circle(-0.11, 0.025, 0.02, 5), "paint_black", 0.03)
    elif kind == "hunter":    # A bow and an arrow.
        pts = [(0.1 * math.cos(a) * 1.6 - 0.05, 0.2 * math.sin(a)) for a in [(-1.3 + 0.52 * k) for k in range(6)]]
        for a, b in zip(pts, pts[1:]):
            flat(mb, w, [a, b, (b[0] - 0.03, b[1]), (a[0] - 0.03, a[1])], "plank_light")
        flat(mb, w, [(-0.2, -0.008), (0.16, -0.008), (0.16, 0.008), (-0.2, 0.008)], "paint_white")
        flat(mb, w, [(0.14, -0.04), (0.22, 0), (0.14, 0.04)], "steel")
    elif kind == "farm":      # A sheaf of wheat.
        for s in (-1, 0, 1):
            flat(mb, w, [(s * 0.02 - 0.012, -0.2), (s * 0.02 + 0.012, -0.2), (s * 0.1 + 0.012, 0.08), (s * 0.1 - 0.012, 0.08)], "wheat")
            flat(mb, w, [(s * 0.1 - 0.035, 0.06), (s * 0.1 + 0.035, 0.06), (s * 0.12 + 0.02, 0.2), (s * 0.12 - 0.02, 0.2)], "wheat")
        flat(mb, w, [(-0.06, -0.1), (0.06, -0.1), (0.06, -0.06), (-0.06, -0.06)], "paint_red", 0.03)
    elif kind == "mill":      # Four sails.
        for i in range(4):
            a = TAU * i / 4 + 0.4
            c, s = math.cos(a), math.sin(a)
            flat(mb, w, [(c * 0.03 - s * 0.01, s * 0.03 + c * 0.01), (c * 0.21 - s * 0.06, s * 0.21 + c * 0.06), (c * 0.21 + s * 0.02, s * 0.21 - c * 0.02), (c * 0.03 + s * 0.01, s * 0.03 - c * 0.01)],
                 "paint_white")
        flat(mb, w, circle(0, 0, 0.04, 6), "board_edge", 0.03)
    elif kind == "smokehouse":   # A ham.
        flat(mb, w, [(-0.1, -0.15), (0.12, -0.12), (0.17, 0.02), (0.06, 0.12), (-0.1, 0.1), (-0.17, -0.02)], "meat")
        flat(mb, w, [(0.04, 0.1), (0.1, 0.2), (0.13, 0.18), (0.08, 0.08)], "paint_white")
    elif kind == "tannery":   # A stretched hide.
        flat(mb, w, [(-0.12, -0.2), (0.12, -0.2), (0.2, -0.1), (0.12, 0), (0.2, 0.14), (0.1, 0.2), (-0.1, 0.2), (-0.2, 0.14), (-0.12, 0), (-0.2, -0.1)], "hide")
    elif kind == "armory":    # A shield over a sword.
        flat(mb, w, [(-0.014, -0.22), (0.014, -0.22), (0.014, 0.22), (-0.014, 0.22)], "steel")
        flat(mb, w, [(-0.15, 0.14), (0.15, 0.14), (0.15, 0.0), (0, -0.16), (-0.15, 0.0)], "paint_blue", 0.03)
        flat(mb, w, [(-0.04, 0.1), (0.04, 0.1), (0.04, -0.04), (0, -0.08), (-0.04, -0.04)], "paint_white", 0.04)
    elif kind == "bowyer":    # A strung bow.
        pts = [(0.14 * math.cos(a) - 0.04, 0.21 * math.sin(a)) for a in [(-1.4 + 0.56 * k) for k in range(6)]]
        for a, b in zip(pts, pts[1:]):
            flat(mb, w, [a, b, (b[0] - 0.035, b[1]), (a[0] - 0.035, a[1])], "plank_light")
        flat(mb, w, [(pts[0][0] - 0.02, pts[0][1]), (pts[0][0] - 0.012, pts[0][1]), (pts[-1][0] - 0.012, pts[-1][1]), (pts[-1][0] - 0.02, pts[-1][1])], "paint_white")
    elif kind == "bathhouse":   # A tub and steam.
        flat(mb, w, [(-0.18, -0.02), (0.18, -0.02), (0.14, -0.17), (-0.14, -0.17)], "board")
        flat(mb, w, [(-0.16, -0.02), (0.16, -0.02), (0.16, 0.02), (-0.16, 0.02)], "water", 0.03)
        for k in (-0.08, 0.0, 0.08):
            flat(mb, w, [(k - 0.012, 0.06), (k + 0.012, 0.06), (k + 0.03, 0.19), (k + 0.006, 0.19)], "paint_white")
    elif kind == "chapel":    # A bell.
        flat(mb, w, [(-0.16, -0.12), (0.16, -0.12), (0.1, -0.04), (0.08, 0.12), (0, 0.18), (-0.08, 0.12), (-0.1, -0.04)], "gold")
        flat(mb, w, circle(0, -0.16, 0.035, 6), "gold")
    elif kind == "kiln":      # Stacked bricks.
        for r, k, off in ((0, 0, 0.0), (0, 1, 0.0), (1, 0, 0.09), (2, 0, 0.0), (2, 1, 0.0)):
            flat(mb, w, [(-0.18 + 0.19 * k + off, -0.16 + 0.11 * r), (-0.01 + 0.19 * k + off, -0.16 + 0.11 * r), (-0.01 + 0.19 * k + off, -0.07 + 0.11 * r),
                         (-0.18 + 0.19 * k + off, -0.07 + 0.11 * r)], "brick")
    elif kind == "smelter":   # An ingot under a flame.
        flat(mb, w, [(-0.18, -0.18), (0.18, -0.18), (0.13, -0.06), (-0.13, -0.06)], "steel")
        flat(mb, w, [(0, 0.2), (0.1, 0.04), (0.05, -0.03), (-0.05, -0.03), (-0.1, 0.04)], "paint_red")
        flat(mb, w, [(0, 0.11), (0.045, 0.02), (-0.045, 0.02)], "paint_yellow", 0.03)
    elif kind == "inn":       # A bed.
        flat(mb, w, [(-0.2, -0.1), (0.2, -0.1), (0.2, 0.0), (-0.2, 0.0)], "paint_red")
        flat(mb, w, [(-0.22, -0.18), (-0.18, -0.18), (-0.18, 0.14), (-0.22, 0.14)], "board_edge")
        flat(mb, w, [(0.18, -0.18), (0.22, -0.18), (0.22, 0.04), (0.18, 0.04)], "board_edge")
        flat(mb, w, [(-0.17, 0.0), (-0.05, 0.0), (-0.05, 0.07), (-0.17, 0.07)], "paint_white")
    elif kind == "stable":    # A horseshoe.
        n = 9
        outer = [(math.cos(-0.5 + (math.pi + 1.0) * i / (n - 1)) * 0.19, math.sin(-0.5 + (math.pi + 1.0) * i / (n - 1)) * 0.2) for i in range(n)]
        inner = [(x * 0.62, z * 0.62) for x, z in outer]
        for i in range(n - 1):
            flat(mb, w, [outer[i], outer[i + 1], inner[i + 1], inner[i]], "steel")
    else:                     # explorer: a compass rose.
        for i in range(4):
            a = TAU * i / 4
            c, s = math.cos(a), math.sin(a)
            flat(mb, w, [(c * 0.22, s * 0.22), (-s * 0.05, c * 0.05), (s * 0.05, -c * 0.05)], "paint_red" if i == 1 else "paint_white")
        flat(mb, w, circle(0, 0, 0.045, 6), "gold", 0.03)


def sign(kind):
    def build():
        mb = kit.begin()
        mb.box((0, 0.06, 2.75), (0.14, 0.12, 0.5), "iron")                          # The plate on the wall (the wall is at +Y).
        beam(mb, (0, 0.0, 2.9), (0, -1.0, 2.9), 0.03, "iron")
        beam(mb, (0, 0.0, 2.55), (0, -0.55, 2.88), 0.02, "iron")
        mb.cylinder((0, -1.0, 2.9), (0, -1.08, 2.9), 0.04, 0.0, "iron", segments=5)
        w = {"board": 1.0}
        for y in (-0.3, -0.8):
            mb.cylinder((0, y, 2.88), (0, y, 2.62), 0.012, 0.012, "iron", w, segments=4)
        # The board hangs across the street, so its faces look along X; it is drawn in X-Z and turned.
        start = _shapes.mark(mb)
        solid(mb, [(-0.34, -0.03, 1.86), (0.34, -0.03, 1.86), (0.34, -0.03, 2.54), (0.0, -0.03, 2.62), (-0.34, -0.03, 2.54)], (0, 0.06, 0), "board_edge", w)
        solid(mb, [(-0.3, -0.04, 1.9), (0.3, -0.04, 1.9), (0.3, -0.04, 2.5), (0.0, -0.04, 2.57), (-0.3, -0.04, 2.5)], (0, 0.08, 0), "board", w)
        emblem(mb, w, kind)
        _shapes.moved(mb, start, (0, -0.55), 90)
        pose = lambda t: ({"board": [(kit.Y, 6 * math.sin(TAU * t))]}, {})   # noqa: E731
        kit.save(mb, FAMILY, "sign_" + kind, COLORS, mech=kit.Mech([("board", (0, -0.55, 2.88), (0, -0.55, 2.2), None)]).clip("swing", 3.0, pose))
    return build


SIGNS = ("bakery", "tavern", "brewery", "blacksmith", "tailor", "cobbler", "weaver", "herbalist", "physician", "market", "trading_post", "vault",
         "woodcutter", "stonecutter", "fisher", "hunter", "farm", "mill", "smokehouse", "tannery", "armory", "bowyer", "bathhouse", "chapel", "kiln",
         "smelter", "inn", "stable", "explorer")


# --- Burnt ruins by footprint ---------------------------------------------------------------------


def ruin(w, d):
    def build():
        mb = kit.begin()
        rnd = random.Random(w * 10 + d)
        x0, x1, y0, y1 = -w / 2 + 0.2, w / 2 - 0.2, -d / 2 + 0.2, d / 2 - 0.2
        mb.box((0, 0, 0.03), (w - 0.3, d - 0.3, 0.06), "ash")
        door = min(1.2, w * 0.3)
        for xa, xb in ((x0, -door / 2), (door / 2, x1)):                               # What is left of the foundations.
            mb.box(((xa + xb) / 2, y0, 0.2), (xb - xa, 0.3, 0.4), "stone_burnt")
        mb.box((0, y1, 0.25), (x1 - x0, 0.3, 0.5), "stone_burnt")
        for x in (x0, x1):
            mb.box((x, 0, 0.22), (0.3, y1 - y0, 0.44), "stone_burnt")
        posts = [(x0, y0), (x1, y0), (x0, y1), (x1, y1)]
        for k in range(1, int(w // 2.5) + 1):
            x = x0 + (x1 - x0) * k / (int(w // 2.5) + 1)
            posts += [(x, y1), (x, y0) if abs(x) > door / 2 + 0.3 else (x, y1)]
        for k in range(1, int(d // 2.5) + 1):
            y = y0 + (y1 - y0) * k / (int(d // 2.5) + 1)
            posts += [(x0, y), (x1, y)]
        for x, y in posts:                                                            # Charred posts, broken at different heights.
            h = rnd.uniform(0.7, 2.8)
            mb.cylinder((x, y, 0.3), (x + rnd.uniform(-0.15, 0.15), y + rnd.uniform(-0.15, 0.15), h), 0.11, 0.07, "char", segments=6)
            mb.cylinder((x, y, 0.3), (x, y, 0.6), 0.12, 0.12, "char_light", segments=6)
        for _ in range(int(w * d / 5) + 2):                                            # Fallen beams.
            a = rnd.uniform(0, TAU)
            cx, cy = rnd.uniform(x0 + 0.5, x1 - 0.5), rnd.uniform(y0 + 0.5, y1 - 0.5)
            length = rnd.uniform(1.0, min(w, d) * 0.55)
            p0 = (max(x0, min(x1, cx - math.cos(a) * length / 2)), max(y0, min(y1, cy - math.sin(a) * length / 2)), rnd.uniform(0.1, 0.25))
            p1 = (max(x0, min(x1, cx + math.cos(a) * length / 2)), max(y0, min(y1, cy + math.sin(a) * length / 2)), rnd.uniform(0.1, 0.9))
            beam(mb, p0, p1, 0.09, rnd.choice(("char", "char_light")))
        for _ in range(int(w * d / 6) + 2):                                            # Heaps of ash and rubble, with embers.
            x, y = rnd.uniform(x0 + 0.4, x1 - 0.4), rnd.uniform(y0 + 0.4, y1 - 0.4)
            mb.sphere((x, y, 0.05), rnd.uniform(0.3, 0.6), rnd.choice(("ash", "ash_light")), segments=6, rings=3, scale=(1.2, 1.0, 0.35))
            if rnd.random() < 0.5:
                mb.box((x + 0.1, y, 0.2), (0.12, 0.1, 0.06), "ember", rotation_z=rnd.uniform(0, 3))
            if rnd.random() < 0.4:
                rock(mb, x - 0.3, y + 0.2, 0.12, 0.2, rnd, "stone_burnt")
        if w >= 4 and d >= 4:                                                          # The chimney often stands.
            cx, cy = x1 - 0.8, y1 - 0.7
            mb.box((cx, cy, 1.4), (0.7, 0.7, 2.8), "stone_burnt")
            mb.box((cx, cy, 2.9), (0.5, 0.5, 0.6 + 0.2 * (w % 2)), "stone_burnt")
        bones = []
        wisps = max(1, int(w * d / 14))
        for i in range(wisps):
            b = "smoke%d" % i
            x, y = rnd.uniform(x0 + 0.5, x1 - 0.5), rnd.uniform(y0 + 0.5, y1 - 0.5)
            for k in range(3):
                mb.sphere((x + 0.1 * k, y, 0.6 + 0.55 * k), 0.28 + 0.08 * k, "smoke", {b: 1.0}, segments=6, rings=4, scale=(1, 1, 0.8))
            bones.append((b, (x, y, 0.4), (x, y, 1.2), None))

        def smolder(t):
            turns, moves = {}, {}
            for i in range(wisps):
                s = (t + i / wisps) % 1.0
                moves["smoke%d" % i] = (0.4 * s, 0.1 * math.sin(TAU * s), 1.5 * s)
                turns["smoke%d" % i] = [(kit.Z, 90 * s)]
            return turns, moves

        kit.save(mb, FAMILY, "ruin_%dx%d" % (w, d), COLORS, mech=kit.Mech(bones).clip("smolder", 5.0, smolder))
    return build


MODELS = {"sign_" + kind: sign(kind) for kind in SIGNS}
MODELS.update({"ruin_%dx%d" % (w, d): ruin(w, d) for w, d in FOOTPRINTS})

kit.run(MODELS, FAMILY)
