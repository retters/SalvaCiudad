"""Smaller buildings: a farmstead, a well house with a treadwheel, a wash
house, a beacon tower, a wayside shrine, a forager's hut and a clay pit
with a pug mill."""

import math
import random

import parts as P
import houses
from civic import storey
from mills import sack, hand_cart
from parts import game, TAU

THATCH = ("thatch", "thatch_dark")
SHINGLE = ("shingle", "shingle_dark")


def farmstead(mb, rig, seed=160):
    rnd = random.Random(seed)
    # The farmhouse at the back left, a byre at the right, a yard between them.
    with mb.placed((-2.9, 2.2, 0)):
        houses.house(mb, rig, level=2, style=0, seed=4, extras=False)
    bx, by, bw, bd, bh = 3.2, 1.6, 4.2, 5.4, 2.6
    mb.box((bx, by, 0.2), (bw + 0.2, bd + 0.2, 0.4), "stone")
    P.plank_block(mb, bx, by, 0.4, bw, bd, bh - 0.4)
    with mb.placed((bx, by, 0), math.pi / 2):
        P.gable_roof(mb, 0, 0, bd, bw, bh, 2.2, THATCH, rows=5, overhang=0.5, gable="plank", end_overhang=0.4)
    with P.face(mb, bx, by, bw, bd, "front"):
        P.plank_door(mb, 0, 0.4, w=1.8, h=2.0, double=True)
        mb.box((0, -0.04, bh + 0.9), (0.9, 0.08, 0.9), "timber")
        mb.box((0, -0.07, bh + 0.9), (0.7, 0.08, 0.7), "hay")
    with P.face(mb, bx, by, bw, bd, "left") as L:
        for x in (-L * 0.25, L * 0.25):
            P.window(mb, x, 1.7, w=0.6, h=0.5, shutter=None)
    # A pigsty with a low wall, a hen house on legs, a dung heap.
    px, py = 4.3, -3.2
    for x, y, w, d in ((px, py - 1.0, 2.6, 0.2), (px, py + 1.0, 2.6, 0.2), (px - 1.3, py, 0.2, 2.2), (px + 1.3, py, 0.2, 2.2)):
        mb.box((x, y, 0.35), (w, d, 0.7), "wall")
    mb.box((px + 0.6, py + 0.5, 0.5), (1.2, 0.9, 1.0), "plank")
    game.sloped_slab(mb, px - 0.1, px + 1.3, py - 0.1, py + 1.05, 1.0, 1.3, 0.07, "thatch")
    mb.box((px - 0.5, py - 0.4, 0.05), (1.4, 1.0, 0.1), "earth_dark")
    for s, c in ((-0.6, "flowers"), (-0.1, "bone")):   # Two pigs.
        mb.sphere((px + s, py - 0.4, 0.32), 0.26, c, segments=6, rings=4, scale=(1.5, 0.9, 0.85))
        mb.sphere((px + s - 0.36, py - 0.4, 0.34), 0.14, c, segments=5, rings=3)
    hx, hy = -0.4, -3.4
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.box((hx + sx * 0.5, hy + sy * 0.4, 0.4), (0.07, 0.07, 0.8), "timber")
    mb.box((hx, hy, 1.15), (1.2, 1.0, 0.8), "plank")
    with mb.placed((hx, hy, 0)):
        P.gable_roof(mb, 0, 0, 1.2, 1.0, 1.55, 0.45, SHINGLE, rows=2, overhang=0.15, gable="plank", barge=None, thick=0.06)
    mb.box((hx, hy - 0.52, 1.0), (0.3, 0.04, 0.35), "charcoal")
    P.beam(mb, (hx, hy - 0.55, 0.8), (hx, hy - 1.3, 0.05), 0.05, "wood")
    for x, y in ((hx + 1.0, hy - 0.6), (hx - 0.9, hy - 0.9), (hx + 0.3, hy - 1.5)):   # Hens.
        mb.sphere((x, y, 0.16), 0.13, "white", segments=5, rings=3, scale=(1.3, 0.9, 1))
        mb.sphere((x + 0.14, y, 0.28), 0.07, "white", segments=4, rings=3)
        mb.box((x + 0.14, y, 0.36), (0.06, 0.02, 0.05), "band")
    mb.sphere((1.2, -3.8, 0), 0.9, "earth_dark", segments=7, rings=4, scale=(1.2, 1, 0.5))
    mb.box((1.7, -3.2, 0.6), (0.05, 0.05, 1.2), "wood")
    # The yard: a well, a plough, a cart, a fence with a gate.
    P.well(mb, 0.2, 0.2, roof=THATCH)
    with mb.placed((-3.4, -2.2, 0), 0.4):
        P.beam(mb, (-0.9, 0, 0.75), (0.7, 0, 0.3), 0.07, "timber")
        P.beam(mb, (-0.9, 0, 0.75), (-1.3, 0.25, 1.0), 0.05, "timber")
        P.beam(mb, (-0.9, 0, 0.75), (-1.3, -0.25, 1.0), 0.05, "timber")
        P.prism_xz(mb, [(0.2, 0.45), (0.7, 0.3), (0.5, 0.0), (0.1, 0.05)], -0.03, 0.03, "iron")
        mb.cylinder((0.9, -0.05, 0.28), (0.9, 0.05, 0.28), 0.28, 0.28, "wood", segments=8)
    hand_cart(mb, -1.6, -3.9, 0.1)
    game.fence(mb, -5.6, -4.6, -1.0, -4.6, posts=5, h=1.0)
    game.fence(mb, 0.6, -4.6, 2.6, -4.6, posts=2, h=1.0)
    game.fence(mb, -5.6, -4.6, -5.6, 0.0, posts=5, h=1.0)
    for x, y in ((-5.0, -3.6), (-4.3, -3.8)):
        P.hay_bale(mb, x, y)


def well_house(mb, rig, seed=162):
    rnd = random.Random(seed)
    # A deep well under a tiled roof, drawn by a treadwheel.
    mb.box((0, 0, 0.06), (5.4, 4.4, 0.12), "paving")
    mb.cylinder((-0.6, 0.2, 0.1), (-0.6, 0.2, 1.0), 1.0, 0.95, "wall", segments=12)
    mb.cylinder((-0.6, 0.2, 0.96), (-0.6, 0.2, 1.04), 1.08, 1.08, "wall_light", segments=12)
    mb.cylinder((-0.6, 0.2, 1.02), (-0.6, 0.2, 1.06), 0.75, 0.75, "charcoal", segments=12)
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.box((sx * 2.3, 0.2 + sy * 1.5, 1.6), (0.2, 0.2, 3.0), "timber")
            P.beam(mb, (sx * 2.3, 0.2 + sy * 1.5, 2.4), (sx * 1.6, 0.2 + sy * 1.5, 3.05), 0.1, "timber")
    top = P.gable_roof(mb, 0, 0.2, 4.8, 3.2, 3.1, 1.6, ("tile_red", "tile_red_dark"), rows=5, overhang=0.45, gable=None, barge="timber")
    for sy in (-1, 1):
        mb.box((0, 0.2 + sy * 1.5, 3.05), (4.8, 0.18, 0.18), "timber")
    # The axle, the rope drum over the well and the treadwheel beside it.
    mb.box((-0.6, 0.2, 2.5), (0.2, 0.2, 0.2), "iron")
    with mb.bone("wheel"):
        mb.cylinder((-1.5, 0.2, 2.5), (2.1, 0.2, 2.5), 0.09, 0.09, "timber", segments=8)
        mb.cylinder((-1.1, 0.2, 2.5), (-0.1, 0.2, 2.5), 0.22, 0.22, "rope", segments=8)
        wx, R = 1.3, 1.25
        for s in (-1, 1):
            xs = wx + s * 0.4
            for i in range(12):
                a0, a1 = TAU * i / 12, TAU * (i + 1) / 12
                P.beam(mb, (xs, 0.2 + R * math.cos(a0), 2.5 + R * math.sin(a0)), (xs, 0.2 + R * math.cos(a1), 2.5 + R * math.sin(a1)), 0.1, "wood")
            for i in range(3):
                a = TAU * i / 6
                P.beam(mb, (xs, 0.2 - R * math.cos(a), 2.5 - R * math.sin(a)), (xs, 0.2 + R * math.cos(a), 2.5 + R * math.sin(a)), 0.08, "timber")
        for i in range(12):
            with mb.placed(matrix=P.turn_x((wx, 0.2, 2.5), TAU * (i + 0.5) / 12)):
                mb.box((wx, 0.2 + R - 0.02, 2.5), (0.8, 0.04, 0.6), "plank")
    rig.bone("wheel", (0, 0.2, 2.5), (1, 0.2, 2.5), None)
    with mb.bone("bucket"):
        mb.box((-0.6, 0.2, 1.9), (0.03, 0.03, 1.2), "rope")
        mb.cylinder((-0.6, 0.2, 1.05), (-0.6, 0.2, 1.4), 0.2, 0.24, "wood", segments=8)
        mb.cylinder((-0.6, 0.2, 1.2), (-0.6, 0.2, 1.25), 0.25, 0.25, "iron", segments=8)
    rig.bone("bucket", (-0.6, 0.2, 2.5), (-0.6, 0.2, 1.5), None)

    def draw(t):
        up = 0.5 - 0.5 * math.cos(TAU * t)
        return {"wheel": [(P.kit.X, 360 * up)]}, {"bucket": (0, 0, 0.45 * up)}

    rig.add("turn", 6.0, draw)
    # A stone trough fed by a spout, buckets and a yoke.
    mb.box((-0.6, -1.9, 0.4), (2.2, 0.8, 0.6), "wall")
    mb.box((-0.6, -1.9, 0.68), (1.9, 0.5, 0.06), "water")
    P.beam(mb, (-0.6, -0.7, 1.0), (-0.6, -1.6, 0.85), 0.07, "plank")
    for x in (1.6, 2.1):
        mb.cylinder((x, -1.8, 0.12), (x, -1.8, 0.45), 0.16, 0.2, "wood", segments=7)
    P.beam(mb, (1.3, -1.9, 0.5), (2.4, -1.7, 0.5), 0.04, "wood_light")


def wash_house(mb, rig, seed=164):
    rnd = random.Random(seed)
    # A long basin of running water under an open roof, with sloping stones to scrub on.
    w, d = 7.0, 3.6
    mb.box((0, 0.3, 0.06), (w + 0.8, d + 1.6, 0.12), "paving")
    mb.box((0, 0.3, 0.3), (w - 0.6, 1.6, 0.5), "wall")
    mb.box((0, 0.3, 0.53), (w - 1.0, 1.2, 0.05), "water")
    for sy in (-1, 1):
        P.prism_yz(mb, [(0.3 + sy * 0.8, 0.55), (0.3 + sy * 1.25, 0.4), (0.3 + sy * 1.25, 0.12), (0.3 + sy * 0.8, 0.12)][::sy], -w / 2 + 0.3,
                   w / 2 - 0.3, "wall_light")
    for sx in (-1, 0, 1):
        for sy in (-1, 1):
            mb.box((sx * w / 2, 0.3 + sy * d / 2, 1.3), (0.18, 0.18, 2.5), "timber")
            if sx:
                P.beam(mb, (sx * w / 2, 0.3 + sy * d / 2, 1.9), (sx * (w / 2 - 0.6), 0.3 + sy * d / 2, 2.5), 0.09, "timber")
    for sy in (-1, 1):
        mb.box((0, 0.3 + sy * d / 2, 2.55), (w + 0.2, 0.18, 0.18), "timber")
    P.gable_roof(mb, 0, 0.3, w, d, 2.6, 1.3, ("tile_red", "tile_red_dark"), rows=5, overhang=0.5, gable=None, barge="timber")
    mb.box((0, 0.3 + d / 2 - 0.02, 1.3), (w, 0.1, 2.4), "wall")
    # The spring: a stone spout at one end, an overflow at the other.
    mb.box((-w / 2 + 0.1, 0.3, 0.9), (0.5, 0.7, 1.4), "wall")
    mb.box((-w / 2 + 0.45, 0.3, 1.2), (0.4, 0.14, 0.12), "wall_light")
    mb.box((-w / 2 + 0.62, 0.3, 0.85), (0.06, 0.1, 0.6), "foam")
    mb.box((w / 2 + 0.6, 0.3, 0.1), (1.6, 0.4, 0.1), "water")
    # Laundry on lines, tubs, baskets of linen and a paddle.
    for x in (-3.0, 3.0):
        mb.box((x, -2.6, 1.0), (0.09, 0.09, 2.0), "timber")
    mb.cylinder((-3.1, -2.6, 1.9), (3.1, -2.6, 1.9), 0.02, 0.02, "rope", segments=4)
    for i, c in enumerate(("cloth_white", "cloth_blue", "cloth_white", "cloth_red", "white", "cloth_green", "cloth_white")):
        mb.box((-2.5 + i * 0.82, -2.6, 1.9 - (0.45 if i % 2 else 0.6)), (0.6, 0.04, 0.9 if i % 2 else 1.2), c)
    for x, y in ((-2.2, -1.2), (1.6, -1.3)):
        mb.cylinder((x, y, 0.12), (x, y, 0.5), 0.42, 0.48, "wood", segments=10)
        mb.cylinder((x, y, 0.44), (x, y, 0.47), 0.42, 0.42, "foam", segments=10)
    for x, y in ((0.2, -1.4), (2.6, -1.0)):
        mb.cylinder((x, y, 0.12), (x, y, 0.42), 0.26, 0.32, "thatch_dark", segments=8)
        mb.sphere((x, y, 0.44), 0.26, "cloth_white", segments=6, rings=4, scale=(1, 1, 0.5))
    mb.box((-1.0, -1.3, 0.2), (0.12, 0.6, 0.04), "wood_light")


def beacon_tower(mb, rig, seed=166):
    rnd = random.Random(seed)
    x, y, r, h = 0.0, 0.2, 1.6, 8.0
    P.round_tower(mb, x, y, r, h, rnd, slits=3, taper=0.4)
    q = (r + 0.4) * math.cos(math.pi / 14)
    with mb.placed((x, y - q + 0.02, 0)):
        P.arched_door(mb, 0, 0.1, w=0.9, h=1.9)
    P.round_battlements(mb, x, y, h, r)
    # The fire basket on its iron frame; the flame flickers (clip `burn`).
    for i in range(4):
        a = TAU * i / 4 + 0.78
        P.beam(mb, (x + 0.9 * math.cos(a), y + 0.9 * math.sin(a), h), (x + 0.45 * math.cos(a), y + 0.45 * math.sin(a), h + 1.5), 0.07, "iron")
    mb.cylinder((x, y, h + 1.4), (x, y, h + 1.9), 0.45, 0.75, "iron", segments=8)
    for i in range(6):
        a = TAU * i / 6
        mb.box((x + 0.5 * math.cos(a), y + 0.5 * math.sin(a), h + 1.85), (0.5, 0.14, 0.14), "log", rotation_z=a + 0.5)
    with mb.bone("flame"):
        mb.cylinder((x, y, h + 1.85), (x, y, h + 3.2), 0.6, 0.0, "ember", segments=6)
        mb.cylinder((x + 0.15, y, h + 1.85), (x + 0.25, y + 0.1, h + 2.8), 0.4, 0.0, "lava", segments=5)
        mb.cylinder((x - 0.2, y - 0.1, h + 1.85), (x - 0.3, y - 0.15, h + 2.6), 0.32, 0.0, "torch_flame", segments=5)
    rig.bone("flame", (x, y, h + 1.85), (x, y, h + 2.85), None)
    rig.add("burn", 1.2, lambda t: {"flame": [(P.kit.Z, 360 * t), (P.kit.X, 6 * math.sin(TAU * 2 * t))]})
    # An outside stair to a door halfway up, a wood store, a signal flag.
    for i in range(14):
        t = (i + 0.5) / 14
        a = 0.4 + 2.4 * t
        z = 0.15 + 3.4 * t
        rr = r + 0.4 * (1 - z / h) + 0.5
        mb.box((x + rr * math.cos(a), y + rr * math.sin(a), z / 2), (1.0, 0.6, z), "wall_dark", rotation_z=a)
    game.log_pile(mb, -2.6, -1.8, length=1.6, rows=3)
    with mb.placed((2.4, -2.0, 0)):
        mb.box((0, 0, 0.9), (1.6, 1.2, 0.1), "plank")
        for sx in (-1, 1):
            for sy in (-1, 1):
                mb.box((sx * 0.7, sy * 0.5, 0.45), (0.1, 0.1, 0.9), "timber")
        game.log_pile(mb, 0, 0, length=1.2, rows=2)
    P.flag(mb, rig, x + r + 0.2, y, h + 0.6, pole=2.2, length=1.2, mat="band", stripe="banner2")


def wayside_shrine(mb, rig, seed=168):
    rnd = random.Random(seed)
    # A tiny chapel: one room, a porch on two columns, a bell cote.
    cx, cy, w, d, h = 0.0, 0.8, 2.8, 3.0, 2.8
    storey(mb, rnd, "stone", cx, cy, 0, w, d, h, plinth=0.5)
    with mb.placed((cx, cy - 0.6, 0), math.pi / 2):
        top = P.gable_roof(mb, 0, 0, d + 1.4, w, h, 1.7, ("tile_red", "tile_red_dark"), rows=5, overhang=0.35, gable="wall", end_overhang=0.2)
    fy = cy - d / 2
    for s in (-1, 1):
        mb.cylinder((cx + s * 1.1, fy - 1.2, 0.2), (cx + s * 1.1, fy - 1.2, h), 0.16, 0.13, "trim", segments=8)
        mb.box((cx + s * 1.1, fy - 1.2, 0.1), (0.44, 0.44, 0.2), "trim")
        mb.box((cx + s * 1.1, fy - 0.6, h - 0.05), (0.16, 1.3, 0.16), "timber")
    mb.box((cx, fy - 0.7, 0.08), (2.8, 1.5, 0.16), "paving")
    with P.face(mb, cx, cy, w, d, "front"):
        P.arched_door(mb, 0, 0.16, w=1.0, h=2.0)
    for side in ("left", "right"):
        with P.face(mb, cx, cy, w, d, side):
            P.arched_window(mb, 0, 1.0, w=0.5, h=1.1)
    mb.box((cx, fy - 1.35, h + 1.25), (0.7, 0.3, 0.9), "wall")
    mb.box((cx, fy - 1.37, h + 1.2), (0.36, 0.34, 0.5), "charcoal")
    with mb.bone("bell"):
        mb.cylinder((cx, fy - 1.35, h + 1.05), (cx, fy - 1.35, h + 1.35), 0.15, 0.08, "bell", segments=8)
    rig.bone("bell", (cx, fy - 1.35, h + 1.4), (cx, fy - 1.35, h + 1.0), None)
    rig.add("ring", 1.2, lambda t: {"bell": [(P.kit.X, 26 * math.sin(TAU * t))]})
    P.prism_xz(mb, [(cx - 0.45, h + 1.7), (cx + 0.45, h + 1.7), (cx, h + 2.1)], fy - 1.55, fy - 1.15, "tile_red")
    mb.box((cx, fy - 1.35, h + 2.4), (0.07, 0.07, 0.6), "gold")
    mb.box((cx, fy - 1.35, h + 2.5), (0.3, 0.07, 0.07), "gold")
    # Offerings, candles, a bench, a milestone and flowers.
    for i in range(3):
        mb.cylinder((cx - 0.4 + i * 0.4, fy - 0.2, 0.16), (cx - 0.4 + i * 0.4, fy - 0.2, 0.4), 0.04, 0.04, "white", segments=5)
        mb.cylinder((cx - 0.4 + i * 0.4, fy - 0.2, 0.4), (cx - 0.4 + i * 0.4, fy - 0.2, 0.5), 0.03, 0.0, "torch_flame", segments=4)
    mb.box((2.0, -1.2, 0.42), (0.4, 1.3, 0.08), "wall_light")
    for s in (-0.5, 0.5):
        mb.box((2.0, -1.2 + s, 0.2), (0.34, 0.12, 0.4), "wall_dark")
    mb.box((-2.0, -2.2, 0.4), (0.4, 0.25, 0.8), "wall_light")
    mb.cylinder((-2.0, -2.325, 0.8), (-2.0, -2.075, 0.8), 0.2, 0.2, "wall_light", segments=8)
    for i in range(6):
        x, y = rnd.uniform(-2.2, 2.2), rnd.uniform(-2.6, -1.9)
        mb.sphere((x, y, 0.12), 0.15, "leaves", segments=5, rings=3)
        mb.sphere((x, y, 0.27), 0.08, rnd.choice(("flowers", "flowers_y", "cloth_white")), segments=5, rings=3)


def forager_hut(mb, rig, seed=170):
    rnd = random.Random(seed)
    # A round hut of wattle with a deep thatch.
    x, y, r = -0.9, 1.0, 1.9
    mb.cylinder((x, y, 0), (x, y, 0.3), r + 0.1, r + 0.1, "stone", segments=12)
    mb.cylinder((x, y, 0.3), (x, y, 2.0), r, r, "plaster_warm", segments=12)
    for i in range(12):
        a = TAU * i / 12
        mb.box((x + r * math.cos(a), y + r * math.sin(a), 1.15), (0.1, 0.12, 1.7), "timber", rotation_z=a)
    P.cone_roof(mb, x, y, 1.9, r, 2.8, THATCH, rows=6, eave=0.6, power=1.0, finial=None)
    mb.cylinder((x, y, 4.5), (x, y, 4.9), 0.2, 0.3, "thatch_dark", segments=6)
    q = r * math.cos(math.pi / 12)
    with mb.placed((x, y - q - 0.02, 0)):
        P.plank_door(mb, 0, 0.3, w=0.9, h=1.55)
    # Drying racks of mushrooms and herbs, baskets of berries, nuts and roots.
    for rx, n, c in ((2.2, 6, "bone"), (2.2, 6, "leaves")):
        ry = -0.4 if c == "bone" else 0.6
        for sx in (-0.9, 0.9):
            mb.box((rx + sx, ry, 0.8), (0.08, 0.08, 1.6), "timber")
        for z in (0.9, 1.5):
            mb.cylinder((rx - 0.95, ry, z), (rx + 0.95, ry, z), 0.025, 0.025, "wood", segments=4)
            for i in range(n):
                xx = rx - 0.75 + i * 0.3
                if c == "bone":
                    mb.cylinder((xx, ry, z - 0.2), (xx, ry, z - 0.08), 0.03, 0.03, c, segments=4)
                    mb.cylinder((xx, ry, z - 0.3), (xx, ry, z - 0.2), 0.02, 0.09, "band" if i % 2 else "clay", segments=6)
                else:
                    mb.cylinder((xx, ry, z - 0.02), (xx, ry, z - 0.4), 0.02, 0.09, c if i % 2 else "hay", segments=5)
    for i, (bx, by, c) in enumerate(((-2.6, -2.2, "berries"), (-1.9, -2.5, "leaves"), (-1.2, -2.2, "clay"), (0.2, -2.6, "bone"), (0.9, -2.2, "berries"))):
        mb.cylinder((bx, by, 0), (bx, by, 0.34), 0.24, 0.3, "thatch_dark", segments=8)
        mb.sphere((bx, by, 0.35), 0.24, c, segments=6, rings=4, scale=(1, 1, 0.5))
    mb.box((2.6, -2.4, 0.7), (1.3, 0.7, 0.07), "wood")
    for s in (-0.55, 0.55):
        mb.box((2.6 + s, -2.4, 0.35), (0.07, 0.6, 0.7), "timber")
    for i in range(3):
        mb.cylinder((2.2 + i * 0.4, -2.4, 0.74), (2.2 + i * 0.4, -2.4, 0.95), 0.1, 0.08, "clay", segments=6)
    mb.cylinder((-3.2, 0.4, 0), (-3.2, 0.4, 1.3), 0.03, 0.03, "wood", segments=4)
    mb.cylinder((-3.2, 0.4, 1.3), (-3.05, 0.4, 1.5), 0.03, 0.02, "wood", segments=4)


def clay_pit(mb, rig, seed=172):
    rnd = random.Random(seed)
    # The pit: bands of clay around a puddle, ringed by spoil heaps.
    px, py = -1.6, 1.2
    for k, (rr, z) in enumerate(((3.4, 0.0), (2.6, 0.12), (1.8, 0.24))):
        pts = [(px + rr * math.cos(TAU * i / 10) * 1.15, py + rr * math.sin(TAU * i / 10) * 0.85) for i in range(10)]
        mb.prism(pts, 0.0, 0.04 + 0.01 * k, "clay" if k % 2 == 0 else "tile_red_dark")
    mb.cylinder((px, py, 0.1), (px, py, 0.14), 1.0, 1.0, "water_dark", segments=9)
    for _ in range(7):
        a = rnd.uniform(0, TAU)
        mb.sphere((px + 3.0 * math.cos(a) * 1.1, py + 3.0 * math.sin(a) * 0.8, 0.3), rnd.uniform(0.35, 0.6), "clay", segments=6, rings=4,
                  scale=(1, 1, 0.6))
    for sx in (-0.3, 0.3):
        mb.box((px + 1.6, py - 1.6 + sx, 0.25), (1.8, 0.2, 0.06), "plank", rotation_z=-0.7)
    # The pug mill: a tub with a shaft turned by a long beam (clip `turn`).
    mx, my = 2.8, -0.6
    mb.cylinder((mx, my, 0), (mx, my, 1.0), 0.9, 1.0, "wood", segments=12)
    for z in (0.2, 0.8):
        mb.cylinder((mx, my, z - 0.04), (mx, my, z + 0.04), 1.03, 1.03, "iron", segments=12)
    mb.cylinder((mx, my, 0.9), (mx, my, 0.95), 0.85, 0.85, "clay", segments=12)
    mb.box((mx, my - 1.05, 0.25), (0.4, 0.3, 0.3), "clay")
    with mb.bone("mill"):
        mb.cylinder((mx, my, 0.2), (mx, my, 2.0), 0.1, 0.1, "timber", segments=8)
        P.beam(mb, (mx, my, 1.9), (mx + 3.0, my, 1.3), 0.11, "timber")
        P.beam(mb, (mx, my, 1.2), (mx + 1.2, my, 1.66), 0.07, "timber")
        for a in (0.0, 2.1, 4.2):
            mb.box((mx + 0.4 * math.cos(a), my + 0.4 * math.sin(a), 1.05), (0.7, 0.06, 0.2), "iron", rotation_z=a)
        mb.box((mx + 3.0, my, 0.95), (0.06, 0.06, 0.7), "rope")
        mb.box((mx + 3.0, my, 0.6), (0.5, 0.08, 0.08), "wood")
    rig.bone("mill", (mx, my, 0.2), (mx, my, 1.2), None)
    rig.add("turn", 8.0, lambda t: {"mill": [(P.kit.Z, 360 * t)]})
    # Moulding table, rows of raw bricks drying, a barrow, a shelter and spades.
    mb.box((1.2, -3.6, 0.75), (1.8, 0.8, 0.08), "wood")
    for s in (-0.8, 0.8):
        mb.box((1.2 + s, -3.6, 0.37), (0.08, 0.7, 0.74), "timber")
    for i in range(4):
        mb.box((0.6 + i * 0.4, -3.6, 0.84), (0.3, 0.5, 0.1), "clay")
    for r in range(4):
        for i in range(7):
            mb.box((-4.4 + i * 0.5, -3.0 - r * 0.42, 0.07), (0.4, 0.3, 0.12), "clay" if (i + r) % 3 else "brick")
    with mb.placed((4.6, 2.6, 0)):
        for sx in (-1, 1):
            mb.box((sx * 0.9, -0.7, 0.9), (0.12, 0.12, 1.8), "timber")
            mb.box((sx * 0.9, 0.7, 1.2), (0.12, 0.12, 2.4), "timber")
        game.sloped_slab(mb, -1.2, 1.2, -1.0, 0.9, 1.8, 2.45, 0.08, "thatch")
        mb.box((0, 0.7, 1.0), (1.8, 0.06, 2.0), "plank")
        mb.box((0, 0, 0.35), (1.2, 0.5, 0.06), "wood")
    for i in range(2):
        mb.box((3.6 + i * 0.25, 1.9, 0.6), (0.05, 0.05, 1.2), "wood")
        mb.box((3.6 + i * 0.25, 1.9, 0.12), (0.2, 0.04, 0.26), "iron")


def barrow(mb, x, y, rot=0.0, load="earth_dark"):
    with mb.placed((x, y, 0), rot):
        tub = mb.prism([(-0.5, -0.35), (0.5, -0.35), (0.5, 0.35), (-0.5, 0.35)], 0.35, 0.7, "plank")
        for v in tub:
            if v.co.z < 0.5:
                v.co.x *= 0.6
                v.co.y *= 0.7
        mb.sphere((0, 0, 0.7), 0.3, load, segments=6, rings=4, scale=(1.3, 0.9, 0.5))
        mb.cylinder((-0.5, -0.06, 0.25), (-0.5, 0.06, 0.25), 0.25, 0.25, "wood", segments=8)
        for s in (-1, 1):
            P.beam(mb, (0.4, s * 0.3, 0.5), (1.2, s * 0.3, 0.6), 0.04, "timber")
            mb.box((0.3, s * 0.3, 0.17), (0.05, 0.05, 0.35), "timber")


def compost_yard(mb, rig, seed=174):
    rnd = random.Random(seed)
    # Three timber bins: fresh, rotting and ready.
    for i, (top, hh) in enumerate((("hay", 1.0), ("earth", 0.8), ("earth_dark", 0.55))):
        x = -2.6 + i * 1.9
        for s in (-0.85, 0.85):
            mb.box((x + s, 1.4, 0.6), (0.1, 1.9, 1.2), "plank")
            for z in (0.3, 0.7, 1.1):
                mb.box((x + s, 1.4, z), (0.12, 1.92, 0.04), "plank_dark")
        mb.box((x, 2.35, 0.6), (1.7, 0.1, 1.2), "plank")
        for sx in (-0.85, 0.85):
            for sy in (0.45, 2.35):
                mb.box((x + sx, 1.4 - 0.95 + (sy - 0.45), 0.7), (0.14, 0.14, 1.4), "timber")
        mb.box((x, 1.4, hh / 2), (1.6, 1.8, hh), "earth" if i else "hay")
        mb.sphere((x, 1.4, hh), 0.75, top, segments=7, rings=4, scale=(1.05, 1.15, 0.4))
        mb.box((x, 0.47, 0.25 + 0.2 * i), (1.7, 0.08, 0.5 + 0.4 * i) if i < 2 else (1.7, 0.08, 0.3), "plank_dark")
    for k, (lx, c) in enumerate(((-2.6, "leaves"), (-0.7, "bone"))):   # Scraps on the fresh heaps.
        for j in range(4):
            mb.sphere((lx - 0.4 + j * 0.25, 1.2 + 0.2 * (j % 2), 1.3 - 0.2 * k), 0.1, c if j % 2 else "clay", segments=5, rings=3)
    # A roofed rack of tools, a barrow of finished compost, a dung heap, a water butt.
    tx, ty = 3.4, 1.6
    for s in (-0.7, 0.7):
        mb.box((tx, ty + s, 1.0), (0.1, 0.1, 2.0), "timber")
    game.sloped_slab(mb, tx - 0.5, tx + 0.5, ty - 1.0, ty + 1.0, 2.0, 2.3, 0.07, "thatch")
    mb.box((tx, ty, 1.5), (0.08, 1.4, 0.08), "timber")
    for i in range(3):
        y = ty - 0.4 + i * 0.4
        mb.cylinder((tx - 0.1, y, 0.1), (tx - 0.15, y, 1.9), 0.03, 0.03, "wood", segments=4)
        if i == 1:
            mb.box((tx - 0.15, y, 0.15), (0.04, 0.22, 0.3), "iron")
        else:
            for k in (-0.08, 0, 0.08):
                mb.box((tx - 0.15, y + k, 0.2), (0.03, 0.02, 0.3), "iron")
    barrow(mb, 0.6, -1.8, 0.3)
    mb.sphere((-2.6, -2.0, 0), 1.1, "earth_dark", segments=7, rings=4, scale=(1.2, 1, 0.55))
    for i in range(4):
        mb.sphere((-2.6 + rnd.uniform(-0.6, 0.6), -2.0 + rnd.uniform(-0.5, 0.5), 0.5), 0.14, "hay", segments=5, rings=3)
    game.rain_barrel(mb, 3.2, -1.6)
    game.fence(mb, -3.9, -3.2, 3.9, -3.2, posts=7, h=0.8)


def latrine(mb, rig, seed=176):
    rnd = random.Random(seed)
    # A row of four privies over a stone-lined cesspit, with the night-soil cart behind.
    w, d = 4.8, 1.8
    mb.box((0, 0.6, 0.45), (w + 0.6, d + 1.0, 0.9), "wall")
    mb.box((0, 0.6, 0.92), (w + 0.7, d + 1.1, 0.08), "wall_light")
    P.plank_block(mb, 0, 0.6, 0.96, w, d, 2.1)
    game.sloped_slab(mb, -w / 2 - 0.3, w / 2 + 0.3, 0.6 - d / 2 - 0.5, 0.6 + d / 2 + 0.2, 3.5, 3.0, 0.1, "shingle")
    with P.face(mb, 0, 0.6, w, d, "front") as L:
        for i in range(4):
            x = -L / 2 + (i + 0.5) * L / 4
            mb.box((x, -0.04, 2.0), (0.9, 0.08, 1.8), "timber")
            mb.box((x, -0.07, 2.0), (0.76, 0.08, 1.66), "plank_dark")
            P.prism_xz(mb, [(x - 0.12, 2.5), (x + 0.12, 2.5), (x, 2.66)], -0.13, -0.1, "charcoal")
            mb.box((x + 0.28, -0.12, 1.9), (0.05, 0.05, 0.2), "iron")
    with mb.placed((0, 0.6 - d / 2 - 1.0, 0)):
        P.stairs(mb, 0, 0, 0, 0.96, w - 0.6, 1.0, mat="wall_dark")
    mb.box((0, 0.6 + d / 2 + 0.3, 0.55), (1.2, 0.1, 0.6), "charcoal")   # The clean-out hatch.
    # The cart with its barrels, a shovel, a lime heap, a wash trough.
    with mb.placed((2.6, 3.0, 0), 0.2):
        mb.box((0, 0, 0.6), (2.0, 1.0, 0.1), "plank")
        for sx in (-0.6, 0.6):
            for sy in (-1, 1):
                mb.cylinder((sx, sy * 0.52, 0.45), (sx, sy * 0.62, 0.45), 0.45, 0.45, "wood", segments=10)
        for sx in (-0.5, 0.35):
            mb.cylinder((sx, 0, 0.65), (sx, 0, 1.35), 0.36, 0.32, "wood", segments=8)
            mb.cylinder((sx, 0, 1.0), (sx, 0, 1.06), 0.36, 0.36, "iron", segments=8)
        P.beam(mb, (1.0, 0, 0.6), (2.2, 0, 0.3), 0.07, "timber")
    mb.sphere((-2.8, 2.8, 0), 0.7, "white", segments=7, rings=4, scale=(1.1, 1, 0.55))
    P.beam(mb, (-2.2, 2.4, 0), (-2.5, 2.9, 1.2), 0.035, "wood")
    mb.box((-3.2, -1.8, 0.4), (1.2, 0.5, 0.5), "wall")
    mb.box((-3.2, -1.8, 0.63), (1.0, 0.3, 0.05), "water")
    mb.box((3.2, -1.6, 1.0), (0.1, 0.1, 2.0), "timber")
    mb.box((3.2, -1.8, 1.9), (0.08, 0.5, 0.06), "timber")
    mb.box((3.2, -1.96, 1.65), (0.18, 0.18, 0.26), "glow")


def ratcatcher(mb, rig, seed=178):
    rnd = random.Random(seed)
    with mb.placed((-0.8, 1.0, 0)):
        houses.house(mb, rig, level=1, style=1, seed=6, extras=False)
    # Cages and traps, a terrier's kennel, cats on the fence, the sign of the rat.
    for i, (x, y, zz) in enumerate(((1.8, -1.6, 0), (2.5, -1.7, 0), (2.1, -1.65, 0.45), (3.0, -0.4, 0))):
        mb.box((x, y, zz + 0.04), (0.6, 0.45, 0.06), "wood")
        mb.box((x, y, zz + 0.42), (0.6, 0.45, 0.04), "wood")
        for sx in (-0.27, -0.09, 0.09, 0.27):
            for sy in (-0.2, 0.2):
                mb.box((x + sx, y + sy, zz + 0.23), (0.025, 0.025, 0.36), "iron")
        if i % 2 == 0:
            mb.sphere((x, y, zz + 0.16), 0.1, "charcoal", segments=5, rings=3, scale=(1.6, 0.9, 0.9))
    for x, y in ((-3.0, -2.2), (-2.3, -2.5), (-1.5, -2.2)):
        mb.box((x, y, 0.03), (0.5, 0.3, 0.05), "wood")
        P.beam(mb, (x - 0.2, y, 0.06), (x + 0.15, y, 0.25), 0.02, "iron")
        mb.box((x + 0.18, y, 0.07), (0.08, 0.08, 0.04), "flowers_y")
    kx, ky = 3.0, 1.6
    mb.box((kx, ky, 0.4), (1.0, 1.2, 0.8), "plank")
    mb.box((kx, ky - 0.61, 0.32), (0.45, 0.04, 0.55), "charcoal")
    with mb.placed((kx, ky, 0), math.pi / 2):
        P.gable_roof(mb, 0, 0, 1.2, 1.0, 0.8, 0.45, SHINGLE, rows=2, overhang=0.15, gable="plank", barge=None, thick=0.06)
    mb.sphere((kx, ky - 1.0, 0.22), 0.2, "bone", segments=6, rings=4, scale=(1.5, 0.8, 0.9))   # The terrier.
    mb.sphere((kx - 0.3, ky - 1.0, 0.36), 0.13, "bone", segments=5, rings=3)
    mb.cylinder((kx + 0.28, ky - 1.0, 0.28), (kx + 0.45, ky - 1.0, 0.5), 0.04, 0.02, "bone", segments=4)
    game.fence(mb, -3.6, -3.2, 3.6, -3.2, posts=6, h=0.9)
    for x, c in ((-1.2, "charcoal"), (0.9, "thatch_dark")):   # Cats on the rail.
        mb.sphere((x, -3.2, 1.02), 0.16, c, segments=6, rings=4, scale=(1.5, 0.8, 0.9))
        mb.sphere((x - 0.24, -3.2, 1.12), 0.11, c, segments=5, rings=3)
        for s in (-0.05, 0.05):
            mb.cylinder((x - 0.26, -3.2 + s, 1.2), (x - 0.27, -3.2 + s, 1.3), 0.03, 0.0, c, segments=3)
        P.beam(mb, (x + 0.22, -3.2, 1.02), (x + 0.42, -3.2, 0.8), 0.03, c)
    with mb.placed((-0.8 + 1.4, 1.0 + 0.45 - 1.8 - 0.25, 0), -math.pi / 2):
        P.hanging_sign(mb, rig, 0, 0, 2.3, arm=0.9, board=(0.7, 0.5), emblem="charcoal")


def make(name, fn, colors=None, **kw):
    def build():
        mb = P.begin()
        rig = P.Rig()
        fn(mb, rig, **kw)
        P.finish(mb, name, colors or P.BASE, rig)
    return build


MODELS = {
    "bld_farmstead": make("bld_farmstead", farmstead, P.palette(var_roof=0xC9A55A, var_roof_dark=0xA8863F)),
    "bld_well_house": make("bld_well_house", well_house),
    "bld_wash_house": make("bld_wash_house", wash_house),
    "bld_beacon_tower": make("bld_beacon_tower", beacon_tower),
    "bld_wayside_shrine": make("bld_wayside_shrine", wayside_shrine),
    "bld_forager_hut": make("bld_forager_hut", forager_hut),
    "bld_clay_pit": make("bld_clay_pit", clay_pit),
    "bld_compost_yard": make("bld_compost_yard", compost_yard),
    "bld_latrine": make("bld_latrine", latrine),
    "bld_ratcatcher": make("bld_ratcatcher", ratcatcher, P.palette(var_roof=0x7A5A3C, var_roof_dark=0x614530)),
}
