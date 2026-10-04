"""Town buildings: apothecary, bank and mint, library and school, arena
and a warehouse on a wharf."""

import math
import random

import parts as P
from civic import storey
from mills import sack
from parts import game, TAU

ROOF = ("roof", "roof_dark")


def apothecary(mb, rig, seed=40):
    rnd = random.Random(seed)
    cx, cy, w, d, h1, h2 = 0.4, 0.9, 4.2, 4.4, 2.8, 2.5
    storey(mb, rnd, "stone", cx, cy, 0, w, d, h1)
    z1 = h1 + 0.2
    W, D = w + 0.6, d + 0.6
    mb.box((cx, cy, h1 + 0.1), (W + 0.1, D + 0.1, 0.2), "timber")
    for i in range(6):
        mb.box((cx - W / 2 + 0.2 + i * (W - 0.4) / 5, cy - D / 2 + 0.1, h1 - 0.08), (0.16, 0.5, 0.18), "timber")
    storey(mb, rnd, "timber", cx, cy, z1, W, D, h2, plinth=0, cross=True)
    with mb.placed((cx, cy, 0), math.pi / 2):
        top = P.gable_roof(mb, 0, 0, D, W, z1 + h2, 3.2, ("teal", "teal_dark"), rows=7, overhang=0.4, gable="plaster",
                           end_overhang=0.45)
    with P.face(mb, cx, cy, W, D, "front"):
        for x in (-1.2, 1.2):
            P.window(mb, x, z1 + h2 * 0.55, w=0.6, h=0.8, flowers=True)
        P.window(mb, 0, z1 + h2 + 1.1, w=0.55, h=0.65, shutter=None, lit=True)
        mb.box((0, 0, z1 + h2 + 2.1), (0.14, 0.14, 1.6), "timber")
        mb.box((0, 0, z1 + h2 + 1.75), (W * 0.42, 0.14, 0.14), "timber")
        # Bundles of herbs drying under the jetty.
        for i in range(5):
            x = -1.6 + i * 0.3
            mb.cylinder((x, -0.25, h1 - 0.15), (x, -0.25, h1 - 0.6), 0.03, 0.1, "leaves" if i % 2 else "hay", segments=5)
    for side in ("left", "right"):
        with P.face(mb, cx, cy, W, D, side) as L:
            for x in (-L * 0.25, L * 0.25):
                P.window(mb, x, z1 + h2 * 0.55, w=0.6, h=0.8)
    with P.face(mb, cx, cy, w, d, "front"):
        P.plank_door(mb, 1.2, 0.1, w=0.95, h=1.8)
        # The shop window: a bay with rows of bottles.
        mb.box((-0.7, -0.25, 1.5), (2.0, 0.5, 1.5), "timber")
        mb.box((-0.7, -0.3, 1.5), (1.8, 0.46, 1.3), "window")
        mb.box((-0.7, -0.25, 2.3), (2.2, 0.7, 0.12), "teal_dark")
        mb.box((-0.7, -0.25, 0.6), (2.0, 0.5, 0.3), "timber")
        for r in range(2):
            mb.box((-0.7, -0.52, 1.05 + r * 0.6), (1.8, 0.1, 0.05), "wood_light")
            for i in range(6):
                c = ("magic", "berries", "glow", "crystal", "leaves", "cloth_blue")[(i + r * 2) % 6]
                bx = -1.45 + i * 0.3
                mb.cylinder((bx, -0.54, 1.08 + r * 0.6), (bx, -0.54, 1.3 + r * 0.6), 0.07, 0.07, c, segments=6)
                mb.cylinder((bx, -0.54, 1.3 + r * 0.6), (bx, -0.54, 1.4 + r * 0.6), 0.03, 0.03, "wood_light", segments=5)
    with mb.placed((cx - W / 2 + 0.4, cy - D / 2, 0), -math.pi / 2):
        P.hanging_sign(mb, rig, 0, 0, z1 + 1.5, arm=1.1, board=(0.8, 0.7), emblem="leaves", board_mat="plaster")
    P.chimney(mb, cx + 1.3, cy + 0.8, z1 + h2 + 1.0, top + 1.0, w=0.6, mat="brick", cap="stone_dark")
    # A glasshouse against the left wall.
    gx0, gx1, gy0, gy1 = cx - w / 2 - 1.7, cx - w / 2, cy - 1.6, cy + 1.6
    mb.box(((gx0 + gx1) / 2, (gy0 + gy1) / 2, 0.25), (gx1 - gx0, gy1 - gy0, 0.5), "stone")
    mb.box(((gx0 + gx1) / 2, (gy0 + gy1) / 2, 1.1), (gx1 - gx0 - 0.1, gy1 - gy0 - 0.1, 1.2), "glass")
    with mb.placed(((gx0 + gx1) / 2, (gy0 + gy1) / 2, 0), -math.pi / 2):
        L = gy1 - gy0
        game.sloped_slab(mb, -L / 2, L / 2, -(gx1 - gx0) / 2, (gx1 - gx0) / 2, 1.7, 2.5, 0.06, "glass")
        for i in range(5):
            x = -L / 2 + i * L / 4
            game.sloped_slab(mb, x - 0.04, x + 0.04, -(gx1 - gx0) / 2 - 0.02, (gx1 - gx0) / 2, 1.74, 2.54, 0.06, "timber")
    for i in range(5):
        y = gy0 + i * (gy1 - gy0) / 4
        mb.box((gx0, y, 1.1), (0.08, 0.08, 1.3), "timber")
    for y in (gy0, gy1):
        mb.box(((gx0 + gx1) / 2, y, 1.1), (gx1 - gx0, 0.08, 1.3), "timber" if False else "glass")
        for x in (gx0, (gx0 + gx1) / 2):
            mb.box((x, y, 1.2), (0.08, 0.1, 1.5), "timber")
    mb.box((gx0, (gy0 + gy1) / 2, 1.72), (0.1, gy1 - gy0 + 0.1, 0.1), "timber")
    # The physic garden in front.
    for i, (x, y) in enumerate(((-2.2, -2.6), (-1.0, -2.6), (-2.2, -1.6))):
        mb.box((x, y, 0.12), (1.0, 0.7, 0.24), "wood")
        mb.box((x, y, 0.2), (0.86, 0.56, 0.14), "soil")
        for k in range(3):
            mb.sphere((x - 0.28 + k * 0.28, y, 0.36), 0.13, ("leaves", "flowers", "flowers_y", "magic")[(i + k) % 4],
                      segments=5, rings=3)
    game.barrel(mb, cx + w / 2 - 0.2, cy - d / 2 - 0.5, h=0.8, r=0.3)


def bank(mb, rig, walls="stone", seed=42):
    rnd = random.Random(seed)
    cx, cy, w, d, h = 0.0, 1.0, 6.6, 5.2, 5.4
    storey(mb, rnd, walls, cx, cy, 0, w, d, h, plinth=0.9)
    mb.box((cx, cy, h + 0.12), (w + 0.5, d + 0.5, 0.24), "trim")
    mb.box((cx, cy, h - 0.25), (w + 0.2, d + 0.2, 0.14), "trim")
    P.pyramid_roof(mb, cx, cy, h + 0.24, w, d, 1.7, ("slate", "slate_dark"), rows=4, overhang=0.3, ridge=w - d + 1.0)
    # The portico: steps, four columns and a pediment with a gold coin.
    fy = cy - d / 2
    with mb.placed((cx, fy, 0)):
        for i in range(3):
            mb.box((0, -1.0 - i * 0.3, 0.45 - i * 0.15), (5.4 + i * 0.5, 2.0 + i * 0.6, 0.3 - 0.0), "trim")
        for x in (-2.2, -0.9, 0.9, 2.2):
            mb.box((x, -1.6, 0.75), (0.56, 0.56, 0.3), "trim")
            mb.cylinder((x, -1.6, 0.9), (x, -1.6, 4.0), 0.24, 0.2, "trim", segments=10)
            mb.box((x, -1.6, 4.08), (0.56, 0.56, 0.2), "trim")
        mb.box((0, -0.95, 4.4), (5.3, 1.9, 0.45), "trim")
        P.prism_xz(mb, [(-2.8, 4.62), (2.8, 4.62), (0, 5.9)], -1.95, -0.1, "trim")
        P.prism_xz(mb, [(-2.2, 4.75), (2.2, 4.75), (0, 5.7)], -2.0, -1.9, "wall")
        mb.cylinder((0, -1.95, 5.1), (0, -2.06, 5.1), 0.3, 0.3, "gold", segments=10)
        # The door, bound in iron, and barred windows.
        P.arched_door(mb, 0, 0.6, w=1.5, h=2.7, door="iron", iron="gold")
        for x in (-2.3, 2.3):
            for z in (1.5, 3.4):
                mb.box((x, -0.03, z), (0.9, 0.12, 1.1), "trim")
                mb.box((x, -0.06, z), (0.7, 0.1, 0.9), "window")
                for k in range(3):
                    mb.box((x - 0.22 + k * 0.22, -0.13, z), (0.04, 0.04, 0.9), "iron")
    for side in ("left", "right", "back"):
        with P.face(mb, cx, cy, w, d, side) as L:
            for x in (-L * 0.27, L * 0.27):
                for z in (1.9, 3.8):
                    mb.box((x, -0.03, z), (0.9, 0.12, 1.1), "trim")
                    mb.box((x, -0.06, z), (0.7, 0.1, 0.9), "window")
                    for k in range(3):
                        mb.box((x - 0.22 + k * 0.22, -0.13, z), (0.04, 0.04, 0.9), "iron")
    # The mint's furnace chimney, strongboxes and a lantern.
    P.chimney(mb, cx + 2.2, cy + 1.6, h, h + 3.2, w=0.8, mat="brick", cap="trim", pots=0)
    for x, y, s in ((cx + 3.0, fy - 0.9, 0.55), (cx + 3.5, fy - 0.3, 0.45)):
        mb.box((x, y, s / 2), (s * 1.3, s, s), "wood")
        mb.box((x, y, s + 0.04), (s * 1.34, s * 1.04, 0.1), "iron")
        mb.box((x, y - s / 2 - 0.02, s * 0.6), (0.12, 0.04, 0.16), "gold")
    for sx in (-1, 1):
        mb.box((cx + sx * 3.1, fy - 2.4, 1.1), (0.12, 0.12, 2.2), "iron")
        mb.box((cx + sx * 3.1, fy - 2.4, 2.35), (0.26, 0.26, 0.34), "glow")
        mb.box((cx + sx * 3.1, fy - 2.4, 2.56), (0.32, 0.32, 0.08), "iron")


def library(mb, rig, walls="brick", seed=44):
    rnd = random.Random(seed)
    cx, cy, w, d, h = 0.0, 0.9, 7.8, 5.0, 6.0
    storey(mb, rnd, walls, cx, cy, 0, w, d, h)
    mb.box((cx, cy, 3.1), (w + 0.14, d + 0.14, 0.16), "trim")
    top = P.gable_roof(mb, cx, cy, w, d, h, 2.8, ROOF, rows=7, overhang=0.4,
                       gable="brick" if walls == "brick" else "wall")
    for side in ("front", "back"):
        with P.face(mb, cx, cy, w, d, side) as L:
            for x in (-L * 0.36, -L * 0.2, L * 0.2, L * 0.36) if side == "front" else (-L * 0.33, -L * 0.11, L * 0.11, L * 0.33):
                P.arched_window(mb, x, 0.9, w=0.75, h=1.8)
                P.arched_window(mb, x, 3.7, w=0.75, h=1.8)
    for side in ("left", "right"):
        with P.face(mb, cx, cy, w, d, side) as L:
            for z in (0.9, 3.7):
                P.arched_window(mb, 0, z, w=1.0, h=1.9)
    # The entrance bay, with its own gable.
    bw, bd = 2.6, 1.0
    by = cy - d / 2 - bd / 2
    storey(mb, rnd, walls, cx, by, 0, bw, bd, h)
    with mb.placed((cx, by + 0.6, 0), math.pi / 2):
        P.gable_roof(mb, 0, 0, bd + 1.6, bw, h, 1.7, ROOF, rows=4, overhang=0.3, gable="brick" if walls == "brick" else "wall",
                     end_overhang=0.3)
    with P.face(mb, cx, by, bw, bd, "front"):
        P.arched_door(mb, 0, 0.3, w=1.4, h=2.6)
        mb.box((0, -0.5, 0.15), (2.4, 1.0, 0.3), "trim")
        mb.cylinder((0, 0.02, 4.4), (0, -0.1, 4.4), 0.75, 0.75, "trim", segments=12)
        mb.cylinder((0, 0.0, 4.4), (0, -0.14, 4.4), 0.58, 0.58, "window", segments=12)
        mb.box((0, -0.15, 4.4), (1.16, 0.04, 0.06), "trim")
        mb.box((0, -0.15, 4.4), (0.06, 0.04, 1.16), "trim")
        # An open book carved over the door.
        for s in (-1, 1):
            P.prism_xz(mb, [(0, 3.25), (s * 0.5, 3.35), (s * 0.5, 3.75), (0, 3.65)][::s], -0.12, -0.04, "white")
    # A cupola with the school bell on the ridge.
    bz = top - 0.2
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.box((cx + sx * 0.5, cy + sy * 0.5, bz + 0.8), (0.14, 0.14, 1.6), "timber")
    mb.box((cx, cy, bz + 0.1), (1.3, 1.3, 0.3), "timber")
    P.pyramid_roof(mb, cx, cy, bz + 1.6, 1.2, 1.2, 1.3, ROOF, rows=3, overhang=0.3, finial="gold")
    mb.box((cx, cy, bz + 1.5), (1.1, 0.12, 0.12), "timber")
    with mb.bone("bell"):
        mb.cylinder((cx, cy, bz + 0.75), (cx, cy, bz + 1.2), 0.36, 0.2, "bell", segments=8)
        mb.cylinder((cx, cy, bz + 1.2), (cx, cy, bz + 1.45), 0.2, 0.08, "bell", segments=8)
        mb.cylinder((cx, cy, bz + 0.95), (cx, cy, bz + 0.6), 0.04, 0.07, "iron", segments=5)
    rig.bone("bell", (cx, cy, bz + 1.5), (cx, cy, bz + 0.6), None)
    rig.add("ring", 1.6, lambda t: {"bell": [(P.kit.Y, 24 * math.sin(TAU * t))]})
    P.chimney(mb, cx + 3.0, cy + 1.0, h + 0.8, top + 1.0, w=0.65, mat="brick", cap="trim", pots=2)
    # The school yard: benches, a slate on an easel, a sundial.
    for x in (-2.6, -1.4):
        mb.box((x, -3.0, 0.4), (0.9, 0.3, 0.06), "wood")
        for s in (-0.35, 0.35):
            mb.box((x + s, -3.0, 0.2), (0.07, 0.26, 0.4), "timber")
    for s in (-0.3, 0.3):
        P.beam(mb, (-3.5 + s, -2.9, 0), (-3.5, -2.6, 1.5), 0.05, "timber")
    P.beam(mb, (-3.5, -2.2, 0), (-3.5, -2.6, 1.5), 0.05, "timber")
    P.prism_yz(mb, [(-2.95, 0.6), (-2.85, 0.6), (-2.62, 1.4), (-2.72, 1.4)], -3.95, -3.05, "charcoal")
    mb.cylinder((2.8, -3.0, 0), (2.8, -3.0, 0.9), 0.22, 0.16, "trim", segments=8)
    mb.cylinder((2.8, -3.0, 0.9), (2.8, -3.0, 0.98), 0.36, 0.36, "trim", segments=10)
    P.prism_xz(mb, [(2.65, 0.98), (2.95, 0.98), (2.95, 1.2)], -3.02, -2.98, "brass")


def arena(mb, rig, seed=46):
    rnd = random.Random(seed)
    A, B = 7.2, 4.6
    pts = [(A * math.cos(TAU * i / 20), -0.8 + B * math.sin(TAU * i / 20)) for i in range(20)]
    mb.prism(pts, 0.0, 0.08, "sand")
    for _ in range(14):
        a, k = rnd.uniform(0, TAU), rnd.uniform(0, 0.8)
        mb.box((A * k * math.cos(a), -0.8 + B * k * math.sin(a), 0.085), (rnd.uniform(0.5, 1.2), rnd.uniform(0.3, 0.8), 0.01),
               "sand_dark")
    # The plank barrier around the sand, open at the front for the gate.
    n = 20
    for i in range(n):
        (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % n]
        if (y0 + y1) / 2 < -0.8 - B * 0.93:
            continue
        L = math.hypot(x1 - x0, y1 - y0)
        a = math.atan2(y1 - y0, x1 - x0)
        mb.box(((x0 + x1) / 2, (y0 + y1) / 2, 0.6), (L + 0.05, 0.1, 1.1), "plank", rotation_z=a)
        mb.box(((x0 + x1) / 2, (y0 + y1) / 2, 1.18), (L + 0.1, 0.16, 0.08), "timber", rotation_z=a)
        mb.box((x0, y0, 0.7), (0.18, 0.18, 1.4), "timber", rotation_z=a)
    # The gate: two masts with banners.
    for sx in (-1, 1):
        mb.box((sx * 1.3, -0.8 - B - 0.1, 1.8), (0.3, 0.3, 3.6), "timber")
        P.flag(mb, rig, sx * 1.3, -0.8 - B - 0.1, 3.6, pole=1.8, length=1.3, pennant=True)
        with mb.placed((sx * 1.3, -0.8 - B - 0.25, 0)):
            P.wall_banner(mb, 0, 3.3, w=0.7, h=1.8)
    mb.box((0, -0.8 - B - 0.1, 3.5), (2.9, 0.24, 0.24), "timber")
    # The stand along the back: three tiers under a striped awning.
    sy = -0.8 + B + 0.4
    for t in range(3):
        y = sy + t * 0.8
        z = 0.9 + t * 0.55
        mb.box((0, y, z), (9.0, 0.8, 0.1), "plank")
        mb.box((0, y + 0.36, z - 0.28), (9.0, 0.08, 0.5), "plank_dark")
        for x in (-4.3, -2.15, 0, 2.15, 4.3):
            mb.box((x, y, z / 2), (0.16, 0.16, z), "timber")
    for x in (-4.4, -2.2, 0, 2.2, 4.4):
        mb.box((x, sy - 0.45, 1.7), (0.14, 0.14, 3.4), "timber")
        mb.box((x, sy + 2.1, 2.0), (0.14, 0.14, 4.0), "timber")
    for i in range(8):
        x0 = -4.6 + i * 1.15
        game.sloped_slab(mb, x0, x0 + 1.16, sy - 0.9, sy + 2.3, 3.3, 4.05, 0.05, "stripe_a" if i % 2 else "stripe_b")
    mb.box((0, sy + 2.1, 1.6), (9.0, 0.08, 3.0), "plank")
    with mb.placed((-5.2, sy - 0.2, 0), -math.pi / 2):
        P.stairs(mb, 0, 0, 0, 0.9, 0.9, 1.1, mat="plank")
    for sx in (-1, 1):
        P.flag(mb, rig, sx * 4.4, sy + 2.1, 4.0, pole=1.6, length=1.1)
    # In the ring: a tilt rail, dummies, targets, a weapon rack.
    mb.box((0, -0.8, 0.95), (7.0, 0.08, 0.1), "timber")
    for i in range(6):
        mb.box((-3.4 + i * 1.36, -0.8, 0.5), (0.1, 0.1, 1.0), "timber")
        if i < 5:
            mb.box((-2.72 + i * 1.36, -0.8, 0.6), (1.26, 0.03, 0.5), "stripe_a" if i % 2 else "stripe_b")
    for x, y in ((-4.6, 0.8), (-3.6, 1.8), (-5.0, -2.0)):
        mb.box((x, y, 0.8), (0.1, 0.1, 1.6), "timber")
        mb.box((x, y, 1.25), (0.75, 0.09, 0.09), "timber")
        mb.sphere((x, y, 1.62), 0.2, "hay", segments=6, rings=4)
        mb.box((x, y, 1.05), (0.34, 0.2, 0.5), "hay")
    for x, y in ((4.8, 1.2), (5.4, -0.2)):
        for s in (-0.3, 0.3):
            P.beam(mb, (x + 0.3, y + s, 0), (x, y, 1.5), 0.05, "timber")
        mb.cylinder((x, y, 1.1), (x - 0.18, y, 1.16), 0.55, 0.55, "hay", segments=10)
        mb.cylinder((x - 0.18, y, 1.16), (x - 0.21, y, 1.17), 0.36, 0.36, "stripe_b", segments=10)
        mb.cylinder((x - 0.21, y, 1.17), (x - 0.24, y, 1.18), 0.16, 0.16, "stripe_a", segments=8)
    for x in (3.4, 4.4):
        mb.box((x, -3.6, 0.7), (0.08, 0.08, 1.4), "timber")
    mb.box((3.9, -3.6, 1.2), (1.1, 0.08, 0.08), "timber")
    for i in range(4):
        x = 3.5 + i * 0.27
        mb.cylinder((x, -3.65, 0.1), (x, -3.7, 1.9), 0.03, 0.03, "wood", segments=4)
        mb.cylinder((x, -3.7, 1.9), (x, -3.71, 2.2), 0.06, 0.0, "iron", segments=4)


def wharf_warehouse(mb, rig, roof=("tile_red", "tile_red_dark"), walls="plank", seed=48):
    rnd = random.Random(seed)
    z0 = 0.6
    # The stone quay at the back and the timber wharf in front, on piles.
    mb.box((0, 2.4, z0 / 2), (12.0, 5.0, z0), "wall")
    mb.box((0, 2.4, z0 - 0.03), (12.1, 5.1, 0.08), "wall_light")
    mb.box((0, -2.5, z0 - 0.08), (12.0, 4.9, 0.14), "plank")
    for i in range(1, 9):
        mb.box((0, -4.95 + i * 4.9 / 9, z0 - 0.005), (12.0, 0.03, 0.01), "plank_dark")
    for x in (-5.7, -3.4, -1.1, 1.1, 3.4, 5.7):
        for y in (-4.7, -2.6):
            mb.cylinder((x, y, -0.8), (x, y, z0 + (0.7 if y < -4 else -0.1)), 0.16, 0.14, "log", segments=6)
            if y < -4:
                mb.cylinder((x, y, z0 + 0.7), (x, y, z0 + 0.78), 0.18, 0.18, "iron", segments=6)
    with mb.placed((0, 0, z0)):
        cx, cy, w, d, h = -1.2, 2.5, 8.6, 4.4, 3.6
        if walls == "stone":
            storey(mb, rnd, "stone", cx, cy, 0, w, d, h)
        else:
            mb.box((cx, cy, 0.15), (w + 0.2, d + 0.2, 0.3), "wall_dark")
            P.plank_block(mb, cx, cy, 0.3, w, d, h - 0.3)
        P.gable_roof(mb, cx, cy, w, d, h, 2.6, roof, rows=6, overhang=0.5, gable="plank", end_overhang=0.4)
        with P.face(mb, cx, cy, w, d, "front") as L:
            P.plank_door(mb, 0, 0.1, w=2.4, h=2.6, double=True)
            for x in (-L * 0.35, L * 0.35):
                P.window(mb, x, 2.2, w=0.7, h=0.7, shutter=None)
        with P.face(mb, cx, cy, w, d, "right"):
            mb.box((0, -0.04, h + 0.7), (1.1, 0.08, 1.2), "timber")
            mb.box((0, -0.07, h + 0.7), (0.9, 0.08, 1.0), "door")
            mb.box((0, -0.6, h + 1.7), (0.16, 1.4, 0.16), "timber")
            mb.box((0, -1.2, h + 1.0), (0.03, 0.03, 1.3), "rope")
            game.crate(mb, 0, -1.2, s=0.5, z=h - 0.1)
        # The crane: a mast with a jib that swings a crate from the boat to the wharf.
        mx, my = 3.9, -2.4
        mb.box((mx, my, 0.2), (1.2, 1.2, 0.4), "timber")
        mb.box((mx, my, 2.2), (0.3, 0.3, 4.4), "timber")
        for a in range(4):
            c, s = math.cos(a * math.pi / 2), math.sin(a * math.pi / 2)
            P.beam(mb, (mx + 0.9 * c, my + 0.9 * s, 0.3), (mx, my, 1.9), 0.1, "timber")
        with mb.bone("jib"):
            P.beam(mb, (mx, my, 3.4), (mx, my - 2.9, 5.0), 0.16, "timber")
            P.beam(mb, (mx, my, 4.4), (mx, my - 1.6, 4.3), 0.08, "timber")
            mb.cylinder((mx - 0.08, my - 2.9, 5.0), (mx + 0.08, my - 2.9, 5.0), 0.2, 0.2, "wood", segments=8)
            mb.box((mx, my - 2.9, 3.6), (0.04, 0.04, 2.6), "rope")
            mb.box((mx, my - 2.9, 2.1), (0.7, 0.7, 0.6), "wood_light")
            mb.box((mx, my - 2.9, 2.1), (0.74, 0.1, 0.64), "timber")
            mb.box((mx, my - 2.9, 2.1), (0.1, 0.74, 0.64), "timber")
            P.beam(mb, (mx, my - 2.9, 5.0), (mx, my + 0.1, 3.0), 0.03, "rope")
        rig.bone("jib", mb.world((mx, my, 3.4)), mb.world((mx, my, 4.4)), None)
        rig.add("load", 6.0, lambda t: {"jib": [(P.kit.Z, 55 - 55 * math.cos(TAU * t))]})
        # The treadwheel that works it.
        with mb.bone("treadwheel"):
            for sx in (-1, 1):
                for i in range(10):
                    a0, a1 = TAU * i / 10, TAU * (i + 1) / 10
                    P.beam(mb, (mx + 1.0 + sx * 0.35, my + 0.95 * math.cos(a0), 1.25 + 0.95 * math.sin(a0)),
                           (mx + 1.0 + sx * 0.35, my + 0.95 * math.cos(a1), 1.25 + 0.95 * math.sin(a1)), 0.09, "wood")
                for i in range(4):
                    a = TAU * i / 8
                    P.beam(mb, (mx + 1.0 + sx * 0.35, my - 0.95 * math.cos(a), 1.25 - 0.95 * math.sin(a)),
                           (mx + 1.0 + sx * 0.35, my + 0.95 * math.cos(a), 1.25 + 0.95 * math.sin(a)), 0.07, "timber")
            for i in range(10):
                with mb.placed(matrix=P.turn_x((mx + 1.0, my, 1.25), TAU * (i + 0.5) / 10)):
                    mb.box((mx + 1.0, my + 0.93, 1.25), (0.72, 0.04, 0.5), "plank")
            mb.cylinder((mx + 0.1, my, 1.25), (mx + 1.6, my, 1.25), 0.09, 0.09, "timber", segments=6)
        rig.bone("treadwheel", mb.world((mx + 1.0, my, 1.25)), mb.world((mx + 2.0, my, 1.25)), None)
        rig.add("load", 6.0, lambda t: {"treadwheel": [(P.kit.X, 360 * math.sin(TAU * t))]})
        mb.box((mx + 1.75, my, 0.7), (0.2, 0.3, 1.4), "timber")
        # Cargo on the wharf.
        for x, y, s, zz in ((-4.8, -1.4, 0.7, 0), (-4.0, -1.5, 0.6, 0), (-4.5, -1.45, 0.55, 0.7), (-3.2, -3.6, 0.6, 0),
                            (0.6, -1.2, 0.6, 0)):
            game.crate(mb, x, y, s=s, z=zz)
        for x, y in ((-1.6, -3.4), (-1.0, -3.7), (-1.3, -2.9), (1.6, -1.1)):
            with mb.placed((x, y, 0)):
                game.barrel(mb, 0, 0, h=0.85, r=0.32)
        for x, y in ((-5.2, -3.8), (-4.7, -4.0)):
            with mb.placed((0, 0, 0)):
                sack(mb, x, y)
        mb.cylinder((0.8, -4.2, 0), (0.8, -4.2, 0.12), 0.4, 0.4, "rope", segments=10)
        mb.cylinder((0.8, -4.2, 0.12), (0.8, -4.2, 0.22), 0.3, 0.3, "rope", segments=10)
        mb.box((5.6, -0.6, 1.2), (0.12, 0.12, 2.4), "timber")
        mb.box((5.6, -0.6, 2.5), (0.26, 0.26, 0.34), "glow")
    # A barge moored at the wharf.
    with mb.placed((0.5, -6.3, -0.25)):
        hull = mb.prism([(-3.2, -0.9), (2.6, -0.9), (3.6, 0.0), (2.6, 0.9), (-3.2, 0.9)], 0.0, 0.9, "wood")
        for v in hull:
            if v.co.z < 0.1:
                v.co.x *= 0.85
                v.co.y *= 0.6
        mb.box((-0.3, 0, 0.86), (5.6, 1.5, 0.06), "plank_dark")
        mb.box((-2.6, 0, 1.15), (0.9, 1.3, 0.6), "plank")
        game.crate(mb, 0.2, 0.2, s=0.6, z=0.88)
        game.crate(mb, 0.9, -0.2, s=0.5, z=0.88)
        with mb.placed((-1.0, 0, 0.88)):
            game.barrel(mb, 0, 0.1, h=0.8, r=0.3)
        mb.cylinder((1.9, 0, 0.88), (1.9, 0, 4.2), 0.07, 0.05, "timber", segments=6)
        mb.cylinder((0.9, 0, 3.6), (2.9, 0, 3.6), 0.04, 0.04, "timber", segments=5)
        mb.cylinder((0.9, 0, 2.9), (2.9, 0, 2.9), 0.16, 0.16, "canvas", segments=6)


def make(name, fn, colors, **kw):
    def build():
        mb = P.begin()
        rig = P.Rig()
        fn(mb, rig, **kw)
        P.finish(mb, name, colors, rig)
    return build


SLATE = dict(roof=0x5A6470, roof_dark=0x46505A)
RED = dict(roof=0xB0503A, roof_dark=0x8E3E2A)

MODELS = {
    "bld_apothecary": make("bld_apothecary", apothecary, P.BASE),
    "bld_apothecary_red": make("bld_apothecary_red", apothecary, P.palette(teal=0xB0503A, teal_dark=0x8E3E2A)),
    "bld_bank_stone": make("bld_bank_stone", bank, P.BASE),
    "bld_bank_brick": make("bld_bank_brick", bank, P.BASE, walls="brick"),
    "bld_library_brick": make("bld_library_brick", library, P.palette(**SLATE)),
    "bld_library_stone_blue": make("bld_library_stone_blue", library, P.BASE, walls="stone"),
    "bld_library_stone": make("bld_library_stone", library, P.palette(**RED), walls="stone"),
    "bld_arena": make("bld_arena", arena, P.BASE),
    "bld_arena_blue": make("bld_arena_blue", arena, P.palette(stripe_a=0x2F4FA6, banner=0xB03A30)),
    "bld_wharf_warehouse": make("bld_wharf_warehouse", wharf_warehouse, P.BASE),
    "bld_wharf_warehouse_stone": make("bld_wharf_warehouse_stone", wharf_warehouse, P.BASE, walls="stone",
                                      roof=("slate", "slate_dark")),
}
