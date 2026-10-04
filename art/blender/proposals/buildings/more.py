"""More working buildings: a lumber camp, a great storehouse, a barracks
with its yard, a winery with a screw press and a salt works."""

import math
import random

import parts as P
from civic import storey
from mills import sack, hand_cart
from parts import game, TAU

SHINGLE = ("shingle", "shingle_dark")
ROOF = ("roof", "roof_dark")


def lumber_camp(mb, rig, seed=120):
    rnd = random.Random(seed)
    # The loggers' cabin.
    cx, cy, w, d, h = -1.8, 1.6, 4.4, 3.4, 2.6
    mb.box((cx, cy, 0.15), (w + 0.5, d + 0.5, 0.3), "stone")
    P.log_block(mb, cx, cy, 0.3, w, d, h - 0.3)
    top = P.gable_roof(mb, cx, cy, w, d, h, 2.0, SHINGLE, rows=5, overhang=0.5, gable="plank", end_overhang=0.45)
    with P.face(mb, cx, cy, w + 0.34, d + 0.34, "front") as L:
        P.plank_door(mb, -0.9, 0.3, w=0.95, h=1.7)
        P.window(mb, 1.0, 1.6, w=0.65, h=0.65)
    P.chimney(mb, cx + 1.4, cy + 0.6, h + 0.5, top + 0.9, w=0.6, mat="stone", cap="stone_dark")
    # A shed roof over the saw horse, with a log being cut by a two-man saw.
    sx, sy = 2.6, 1.8
    for ax in (-1, 1):
        for ay in (-1, 1):
            mb.box((sx + ax * 1.4, sy + ay * 1.0, 1.3), (0.16, 0.16, 2.6), "log")
    game.sloped_slab(mb, sx - 1.8, sx + 1.8, sy - 1.5, sy + 1.3, 2.4, 3.0, 0.1, "shingle")
    game.sloped_slab(mb, sx - 1.8, sx + 1.8, sy - 1.5, sy - 0.6, 2.45, 2.66, 0.1, "shingle_dark")
    for ax in (-0.7, 0.7):
        for s in (-1, 1):
            P.beam(mb, (sx + ax, sy + s * 0.45, 0), (sx + ax, sy - s * 0.15, 0.95), 0.07, "timber")
    mb.cylinder((sx - 1.3, sy, 0.95), (sx + 1.3, sy, 0.95), 0.26, 0.24, "log", segments=8)
    for ax in (-1.31, 1.31):
        mb.cylinder((sx + ax - 0.01, sy, 0.95), (sx + ax + 0.01, sy, 0.95), 0.22, 0.22, "log_end", segments=8)
    with mb.bone("saw"):
        mb.box((sx + 0.2, sy, 1.15), (0.03, 1.5, 0.16), "iron")
        for s in (-1, 1):
            mb.box((sx + 0.2, sy + s * 0.8, 1.2), (0.06, 0.06, 0.34), "wood")
    rig.bone("saw", (sx + 0.2, sy, 1.15), (sx + 0.2, sy + 1.0, 1.15), None)
    rig.add("saw", 1.2, lambda t: ({}, {"saw": (0, 0.3 * math.sin(TAU * t), 0)}))
    # Great stacks of logs, a timber wagon, stumps, a chopping block and axes.
    game.log_pile(mb, -3.0, -2.6, length=3.2, rows=4)
    game.log_pile(mb, 0.6, -3.0, length=3.0, rows=3)
    with mb.placed((3.6, -2.2, 0), 0.25):
        mb.box((0, 0, 0.62), (2.8, 0.2, 0.14), "timber")
        for x in (-1.0, 1.0):
            mb.box((x, 0, 0.62), (0.2, 1.3, 0.16), "timber")
            for s in (-1, 1):
                mb.cylinder((x, s * 0.62, 0.55), (x, s * 0.72, 0.55), 0.55, 0.55, "wood", segments=10)
                mb.cylinder((x, s * 0.6, 0.55), (x, s * 0.75, 0.55), 0.12, 0.12, "iron", segments=6)
                mb.box((x, s * 0.5, 1.05), (0.1, 0.1, 0.8), "timber")
        for i, (yy, zz) in enumerate(((-0.25, 0.9), (0.25, 0.9), (0.0, 1.3))):
            mb.cylinder((-1.6, yy, zz), (1.7, yy, zz), 0.24, 0.22, "log", segments=7)
            mb.cylinder((-1.61, yy, zz), (-1.59, yy, zz), 0.2, 0.2, "log_end", segments=7)
        P.beam(mb, (1.4, 0, 0.62), (2.9, 0, 0.3), 0.08, "timber")
    for x, y in ((-4.3, -0.4), (4.6, 0.2), (0.2, -1.2)):
        mb.cylinder((x, y, 0), (x, y, 0.35), 0.32, 0.26, "log", segments=8)
        mb.cylinder((x, y, 0.35), (x, y, 0.37), 0.24, 0.24, "log_end", segments=8)
    mb.box((0.2, -1.2, 0.72), (0.05, 0.12, 0.7), "wood")
    mb.box((0.2, -1.2, 0.48), (0.22, 0.05, 0.14), "iron")
    for i in range(3):
        mb.box((cx - 1.9 + i * 0.25, cy - d / 2 - 0.35, 0.6), (0.05, 0.05, 1.2), "wood")
        mb.box((cx - 1.9 + i * 0.25, cy - d / 2 - 0.35, 1.15), (0.2, 0.05, 0.12), "iron")


def great_storehouse(mb, rig, upper="timber", roof=("tile_red", "tile_red_dark"), seed=122, goods="mixed"):
    rnd = random.Random(seed)
    cx, cy, w, d, h1, h2 = 0.0, 1.0, 9.6, 5.6, 3.4, 2.8
    storey(mb, rnd, "stone", cx, cy, 0, w, d, h1, plinth=0.9)
    z1 = h1 + 0.2
    W, D = w + 0.5, d + 0.5
    mb.box((cx, cy, h1 + 0.1), (W + 0.1, D + 0.1, 0.2), "timber")
    storey(mb, rnd, upper, cx, cy, z1, W, D, h2, plinth=0, cross=True)
    top = P.gable_roof(mb, cx, cy, W, D, z1 + h2, 3.2, roof, rows=7, overhang=0.45,
                       gable={"brick": "brick", "stone": "wall"}.get(upper, "plaster"), end_overhang=0.4)
    # The loading dock along the front, with wide doors and a ramp.
    fy = cy - d / 2
    mb.box((cx, fy - 0.9, 0.45), (w, 1.8, 0.9), "wall_dark")
    mb.box((cx, fy - 0.9, 0.93), (w + 0.1, 1.9, 0.08), "plank")
    with mb.placed((cx - w / 2 - 2.0, fy - 0.9, 0), -math.pi / 2):
        P.stairs(mb, 0, 0.0, 0, 0.9, 1.6, 2.0, mat="wall_dark")
    P.prism_xz(mb, [(cx + w / 2, 0), (cx + w / 2 + 3.0, 0), (cx + w / 2, 0.95)], fy - 1.7, fy - 0.1, "plank")
    with P.face(mb, cx, cy, w, d, "front") as L:
        for x in (-2.6, 2.6):
            P.plank_door(mb, x, 0.95, w=2.2, h=2.2, double=True)
        P.window(mb, 0, 2.3, w=0.7, h=0.7, shutter=None)
    with P.face(mb, cx, cy, W, D, "front") as L:
        for x in (-L * 0.38, -L * 0.14, L * 0.14, L * 0.38):
            P.window(mb, x, z1 + h2 * 0.5, w=0.6, h=0.7, shutter=None)
    # A hoist dormer in the middle of the roof.
    hz = z1 + h2
    mb.box((cx, fy + 0.5, hz + 1.0), (1.8, 1.6, 2.0), "plaster" if upper == "timber" else "wall")
    mb.box((cx, fy - 0.33, hz + 0.9), (1.1, 0.08, 1.5), "door")
    with mb.placed((cx, fy + 0.5, 0), math.pi / 2):
        P.gable_roof(mb, 0, 0, 2.2, 1.8, hz + 2.0, 0.9, roof, rows=3, overhang=0.2, gable="plank", barge=None, thick=0.07)
    mb.box((cx, fy - 0.9, hz + 2.5), (0.16, 1.6, 0.16), "timber")
    with mb.bone("load"):
        mb.box((cx, fy - 1.5, hz + 1.3), (0.03, 0.03, 2.3), "rope")
        mb.box((cx, fy - 1.5, hz - 0.1), (0.7, 0.7, 0.6), "wood_light")
        mb.box((cx, fy - 1.5, hz - 0.1), (0.74, 0.1, 0.64), "timber")
    rig.bone("load", (cx, fy - 1.5, hz + 2.4), (cx, fy - 1.5, hz + 1.4), None)
    rig.add("lift", 4.0, lambda t: {"load": [(P.kit.X, 5 * math.sin(TAU * t)), (P.kit.Y, 3 * math.sin(TAU * t * 2))]})
    for side in ("left", "right"):
        with P.face(mb, cx, cy, W, D, side) as L:
            P.window(mb, 0, z1 + h2 * 0.5, w=0.6, h=0.7, shutter=None)
            P.window(mb, 0, z1 + h2 + 1.2, w=0.5, h=0.6, shutter=None)
    # Goods on the dock and in the yard.
    if goods == "grain":
        for i, x in enumerate((-4.3, -3.8, -3.3, -4.05, -3.55, 0.2, 0.7, 3.9, 4.4)):
            sack(mb, x, fy - 1.2 + (0.1 if i % 2 else -0.1), 0.97 + (0.45 if i in (3, 4) else 0.0), s=0.95)
        for x, y in ((-1.9, -3.6), (-1.2, -3.8), (-0.5, -3.5), (-1.5, -3.1)):   # Sheaves of wheat.
            mb.cylinder((x, y, 0), (x, y, 0.9), 0.3, 0.12, "hay", segments=7)
            mb.cylinder((x, y, 0.85), (x, y, 1.25), 0.1, 0.3, "thatch", segments=7)
            mb.cylinder((x, y, 0.55), (x, y, 0.62), 0.2, 0.2, "rope", segments=7)
        for x in (1.4, 2.0):
            with mb.placed((x, fy - 1.1, 0.97)):
                game.barrel(mb, 0, 0, h=0.85, r=0.32)
    else:
        for x, s, zz in ((-4.2, 0.7, 0), (-3.4, 0.6, 0), (-3.9, 0.55, 0.7), (0.4, 0.6, 0), (4.2, 0.7, 0)):
            game.crate(mb, x, fy - 1.2, s=s, z=0.97 + zz)
        for x in (-0.6, 1.3, 1.9):
            with mb.placed((x, fy - 1.1, 0.97)):
                game.barrel(mb, 0, 0, h=0.85, r=0.32)
        for x, y in ((-1.6, -3.6), (-1.0, -3.9), (-1.3, -3.3)):
            sack(mb, x, y)
    hand_cart(mb, 2.6, -3.9, 0.1)


def meeting_hall(mb, rig, seed=130):
    with mb.placed((1.3, 0, 0)):   # Centered on its lot.
        meeting_hall_parts(mb, rig, seed)


def meeting_hall_parts(mb, rig, seed):
    """The first town center: a log longhouse with a bell on a frame, a
    notice board, a store shed and the settlers' flag."""
    rnd = random.Random(seed)
    cx, cy, w, d, h = -0.4, 1.4, 7.4, 4.4, 2.9
    mb.box((cx, cy, 0.2), (w + 0.5, d + 0.5, 0.4), "stone")
    P.log_block(mb, cx, cy, 0.4, w, d, h - 0.4)
    top = P.gable_roof(mb, cx, cy, w, d, h, 2.6, ("thatch", "thatch_dark"), rows=6, overhang=0.6, gable="plank", end_overhang=0.5)
    with P.face(mb, cx, cy, w + 0.34, d + 0.34, "front") as L:
        P.plank_door(mb, 0, 0.4, w=1.6, h=1.9, double=True)
        for x in (-L * 0.34, L * 0.34):
            P.window(mb, x, 1.7, w=0.8, h=0.7)
        mb.box((0, -0.06, 2.7), (2.2, 0.08, 0.5), "wood_light")
        mb.box((0, -0.11, 2.7), (1.6, 0.03, 0.24), "banner")
    for sx in (-1, 1):   # Carved posts crossing over each gable.
        x = cx + sx * (w / 2 + 0.5)
        P.beam(mb, (x, cy - 0.5, top - 0.4), (x, cy + 0.5, top + 0.9), 0.09, "timber")
        P.beam(mb, (x, cy + 0.5, top - 0.4), (x, cy - 0.5, top + 0.9), 0.09, "timber")
    P.chimney(mb, cx + 2.2, cy + 0.6, h + 0.8, top + 0.9, w=0.7, mat="stone", cap="stone_dark")
    # The porch over the door.
    fy = cy - d / 2
    for s in (-1, 1):
        mb.box((cx + s * 1.3, fy - 1.3, 1.2), (0.18, 0.18, 2.4), "log")
    mb.box((cx, fy - 1.3, 2.45), (3.0, 0.18, 0.18), "timber")
    game.sloped_slab(mb, cx - 1.7, cx + 1.7, fy - 1.7, fy - 0.1, 2.4, 3.0, 0.12, "thatch_dark")
    mb.box((cx, fy - 0.8, 0.2), (2.8, 1.6, 0.4), "plank")
    # The bell on its frame: it swings (clip `ring`).
    bx, by = 3.0, -2.6
    for s in (-1, 1):
        mb.box((bx + s * 0.6, by, 1.3), (0.16, 0.16, 2.6), "timber")
        P.beam(mb, (bx + s * 0.6, by - 0.6, 0), (bx + s * 0.6, by, 1.4), 0.08, "timber")
        P.beam(mb, (bx + s * 0.6, by + 0.6, 0), (bx + s * 0.6, by, 1.4), 0.08, "timber")
    mb.box((bx, by, 2.6), (1.5, 0.18, 0.18), "timber")
    game.sloped_slab(mb, bx - 0.9, bx + 0.9, by - 0.5, by + 0.02, 2.75, 3.05, 0.06, "thatch")
    game.sloped_slab(mb, bx - 0.9, bx + 0.9, by + 0.5, by - 0.02, 2.75, 3.05, 0.06, "thatch")
    with mb.bone("bell"):
        mb.cylinder((bx, by, 1.75), (bx, by, 2.2), 0.34, 0.2, "bell", segments=8)
        mb.cylinder((bx, by, 2.2), (bx, by, 2.5), 0.2, 0.08, "bell", segments=8)
        mb.cylinder((bx, by, 1.95), (bx, by, 1.6), 0.04, 0.07, "iron", segments=5)
        mb.box((bx, by, 1.35), (0.03, 0.03, 0.6), "rope")
    rig.bone("bell", mb.world((bx, by, 2.55)), mb.world((bx, by, 1.6)), None)
    rig.add("ring", 1.6, lambda t: {"bell": [(P.kit.X, 24 * math.sin(TAU * t))]})
    # A notice board, a store shed, barrels and crates of the settlers, the flag.
    mb.box((-3.4, -2.8, 0.9), (0.12, 0.12, 1.8), "timber")
    mb.box((-2.2, -2.8, 0.9), (0.12, 0.12, 1.8), "timber")
    mb.box((-2.8, -2.8, 1.35), (1.3, 0.08, 0.9), "wood_light")
    for i in range(3):
        mb.box((-3.15 + i * 0.35, -2.85, 1.4 - 0.1 * (i % 2)), (0.26, 0.02, 0.34), "white")
    with mb.placed((cx - w / 2 - 1.3, cy + 0.4, 0)):
        for sx in (-1, 1):
            mb.box((sx * 0.8, -1.0, 0.9), (0.14, 0.14, 1.8), "timber")
            mb.box((sx * 0.8, 1.0, 1.2), (0.14, 0.14, 2.4), "timber")
        game.sloped_slab(mb, -1.1, 1.1, -1.4, 1.2, 1.8, 2.5, 0.1, "thatch")
        mb.box((0, 1.0, 1.0), (1.6, 0.06, 2.0), "plank")
        game.crate(mb, -0.3, 0.3, s=0.6)
        game.crate(mb, 0.35, 0.2, s=0.5)
        game.crate(mb, -0.2, 0.3, s=0.45, z=0.6)
        sack(mb, 0.2, -0.6)
    for x, y in ((1.2, -2.6), (1.8, -2.9), (-0.6, -3.0)):
        game.barrel(mb, x, y, h=0.85, r=0.32)
    P.flag(mb, rig, -4.4, -2.6, 0, pole=5.0, length=1.6, height=0.9, pennant=False)


def barracks(mb, rig, seed=124):
    rnd = random.Random(seed)
    cx, cy, w, d, h = 0.0, 3.0, 12.0, 4.6, 3.6
    storey(mb, rnd, "stone", cx, cy, 0, w, d, h)
    top = P.gable_roof(mb, cx, cy, w, d, h, 2.8, ROOF, rows=7, overhang=0.4, gable="wall", barge="wall_light")
    with P.face(mb, cx, cy, w, d, "front") as L:
        for x in (-3.0, 3.0):
            P.arched_door(mb, x, 0.05, w=1.2, h=2.2)
        for x in (-5.0, -1.2, 1.2, 5.0):
            P.arched_window(mb, x, 1.2, w=0.6, h=1.3)
        P.wall_banner(mb, 0, 3.3, w=0.9, h=1.8)
    for x in (-4.0, -1.3, 1.3, 4.0):
        P.dormer(mb, x, cy - d / 2 + 0.6, h + 0.65, w=0.9, h=0.75, depth=1.1, mats=ROOF, walls="wall")
    for x in (-5.0, 5.0):
        P.chimney(mb, x, cy + 0.9, h + 1.0, top + 0.9, w=0.7, pots=2)
    # The drill yard, walled, with a gate between two posts and the standard.
    y0 = -4.6
    for sx in (-1, 1):
        mb.box((sx * 6.0, (y0 + cy - d / 2) / 2, 0.8), (0.5, cy - d / 2 - y0, 1.6), "wall")
        mb.box((sx * 6.0, (y0 + cy - d / 2) / 2, 1.66), (0.62, cy - d / 2 - y0, 0.12), "wall_light")
        mb.box((sx * 3.8, y0, 0.8), (4.9, 0.5, 1.6), "wall")
        mb.box((sx * 3.8, y0, 1.66), (5.0, 0.62, 0.12), "wall_light")
        mb.box((sx * 1.3, y0, 1.3), (0.7, 0.7, 2.6), "wall")
        mb.box((sx * 1.3, y0, 2.66), (0.85, 0.85, 0.14), "wall_light")
        mb.cylinder((sx * 1.3, y0, 2.7), (sx * 1.3, y0, 3.1), 0.14, 0.24, "iron", segments=6)
        mb.cylinder((sx * 1.3, y0, 3.1), (sx * 1.3, y0, 3.5), 0.18, 0.0, "ember", segments=5)
    mb.box((0, -0.9, 0.03), (11.5, 6.6, 0.06), "sand")
    P.flag(mb, rig, 0, -0.6, 0, pole=6.0, length=1.8, height=1.0, pennant=False)
    mb.cylinder((0, -0.6, 0), (0, -0.6, 0.4), 0.5, 0.4, "wall", segments=8)
    # Dummies, a rack of pikes, archery butts, benches.
    for x, y in ((-4.2, -1.0), (-3.0, -2.2), (-4.6, -3.0)):
        mb.box((x, y, 0.8), (0.1, 0.1, 1.6), "timber")
        mb.box((x, y, 1.25), (0.75, 0.09, 0.09), "timber")
        mb.sphere((x, y, 1.62), 0.2, "hay", segments=6, rings=4)
        mb.box((x, y, 1.05), (0.34, 0.2, 0.5), "hay")
        mb.cylinder((x + 0.4, y - 0.1, 1.25), (x + 0.4, y - 0.16, 1.25), 0.26, 0.26, "banner", segments=8)
    for x, y in ((4.9, -1.0), (5.0, -3.0)):
        for s in (-0.3, 0.3):
            P.beam(mb, (x + 0.3, y + s, 0), (x, y, 1.5), 0.05, "timber")
        mb.cylinder((x, y, 1.1), (x - 0.18, y, 1.16), 0.55, 0.55, "hay", segments=10)
        mb.cylinder((x - 0.18, y, 1.16), (x - 0.21, y, 1.17), 0.36, 0.36, "stripe_b", segments=10)
        mb.cylinder((x - 0.21, y, 1.17), (x - 0.24, y, 1.18), 0.16, 0.16, "stripe_a", segments=8)
    for s in (-0.9, 0.9):
        mb.box((2.4 + s, 0.2, 0.75), (0.09, 0.09, 1.5), "timber")
    mb.box((2.4, 0.2, 1.35), (1.9, 0.09, 0.09), "timber")
    mb.box((2.4, 0.2, 0.2), (1.9, 0.3, 0.08), "timber")
    for i in range(6):
        x = 1.65 + i * 0.3
        mb.cylinder((x, 0.15, 0.22), (x, 0.08, 2.4), 0.03, 0.03, "wood", segments=4)
        mb.cylinder((x, 0.08, 2.4), (x, 0.07, 2.75), 0.06, 0.0, "iron", segments=4)
    for x in (-2.0, -5.0):
        mb.box((x, 0.3, 0.42), (1.6, 0.36, 0.07), "wood")
        for s in (-0.65, 0.65):
            mb.box((x + s, 0.3, 0.21), (0.08, 0.3, 0.42), "wall_dark")


def winery(mb, rig, seed=126):
    rnd = random.Random(seed)
    # The press house: stone below, a wide door, a tiled roof.
    cx, cy, w, d, h = -1.4, 1.6, 5.6, 4.2, 3.2
    storey(mb, rnd, "stone", cx, cy, 0, w, d, h)
    top = P.gable_roof(mb, cx, cy, w, d, h, 2.2, ("tile_red", "tile_red_dark"), rows=6, overhang=0.45, gable="wall")
    with P.face(mb, cx, cy, w, d, "front") as L:
        P.arched_door(mb, -1.0, 0.05, w=1.7, h=2.4)
        P.arched_window(mb, 1.6, 1.3, w=0.7, h=1.2)
    with P.face(mb, cx, cy, w, d, "left"):
        P.arched_window(mb, 0, 1.3, w=0.7, h=1.2)
    # A cellar door in a turfed mound beside it.
    mb.sphere((cx + w / 2 + 1.6, cy + 0.6, 0), 1.9, "grass", segments=8, rings=5, scale=(1, 1.1, 0.6))
    mb.box((cx + w / 2 + 1.6, cy - 1.3, 0.75), (1.5, 0.5, 1.5), "wall")
    mb.box((cx + w / 2 + 1.6, cy - 1.56, 0.7), (1.0, 0.06, 1.3), "door")
    mb.box((cx + w / 2 + 1.6, cy - 1.6, 0.7), (1.0, 0.03, 0.1), "iron")
    # The screw press under a canopy: its beam turns (clip `turn`).
    px, py = 2.2, -2.2
    for ax in (-1, 1):
        for ay in (-1, 1):
            mb.box((px + ax * 1.3, py + ay * 1.1, 1.4), (0.14, 0.14, 2.8), "timber")
    P.pyramid_roof(mb, px, py, 2.8, 2.8, 2.4, 0.9, ("tile_red", "tile_red_dark"), rows=3, overhang=0.3, ridge=0.6)
    mb.cylinder((px, py, 0), (px, py, 0.7), 0.95, 1.0, "wood", segments=12)
    for z in (0.15, 0.55):
        mb.cylinder((px, py, z - 0.04), (px, py, z + 0.04), 1.02, 1.02, "iron", segments=12)
    mb.cylinder((px, py, 0.62), (px, py, 0.68), 0.85, 0.85, "berries", segments=12)
    mb.box((px, py - 1.1, 0.25), (0.3, 0.5, 0.08), "wood")
    mb.cylinder((px, py - 1.55, 0), (px, py - 1.55, 0.35), 0.3, 0.34, "wood", segments=8)
    mb.cylinder((px, py - 1.55, 0.3), (px, py - 1.55, 0.33), 0.28, 0.28, "berries", segments=8)
    for s in (-1, 1):
        mb.box((px + s * 0.85, py, 1.3), (0.2, 0.2, 2.6), "timber")
    mb.box((px, py, 2.5), (2.0, 0.3, 0.3), "timber")
    with mb.bone("screw"):
        mb.cylinder((px, py, 0.7), (px, py, 2.6), 0.09, 0.09, "wood_light", segments=8)
        mb.cylinder((px, py, 0.7), (px, py, 0.82), 0.8, 0.8, "wood", segments=12)
        mb.box((px, py, 1.5), (2.6, 0.1, 0.1), "wood")
        for s in (-1, 1):
            mb.sphere((px + s * 1.3, py, 1.5), 0.09, "wood_light", segments=5, rings=3)
    rig.bone("screw", (px, py, 0.7), (px, py, 1.7), None)
    rig.add("turn", 6.0, lambda t: {"screw": [(P.kit.Z, 360 * t)]})
    # Rows of vines on stakes, baskets of grapes, barrels.
    for r in range(3):
        y = -3.6 + r * 0.0
        x0 = -4.4 + r * 1.3
        for k in range(4):
            yy = -3.8 + k * 0.85
            mb.box((x0, yy, 0.6), (0.06, 0.06, 1.2), "timber")
            mb.sphere((x0, yy, 0.85), 0.32, "leaves" if (k + r) % 2 else "leaf_light", segments=6, rings=4, scale=(0.9, 1.2, 1))
            mb.sphere((x0 + 0.14, yy, 0.6), 0.1, "berries", segments=5, rings=3, scale=(1, 1, 1.4))
        mb.box((x0, -2.5, 1.15), (0.04, 3.0, 0.04), "rope")
    for x, y in ((0.2, -3.4), (0.8, -3.7)):
        mb.cylinder((x, y, 0), (x, y, 0.4), 0.26, 0.32, "thatch_dark", segments=8)
        mb.sphere((x, y, 0.4), 0.26, "berries", segments=6, rings=4, scale=(1, 1, 0.5))
    for i in range(3):
        mb.cylinder((cx - 1.6 + i * 0.8, cy - d / 2 - 1.0, 0.38), (cx - 1.6 + i * 0.8, cy - d / 2 - 0.2, 0.38), 0.38, 0.38, "wood", segments=10)
        for yy in (-0.85, -0.35):
            mb.cylinder((cx - 1.6 + i * 0.8, cy - d / 2 + yy - 0.03, 0.38), (cx - 1.6 + i * 0.8, cy - d / 2 + yy + 0.03, 0.38), 0.4, 0.4, "iron",
                        segments=10)
    P.chimney(mb, cx + 1.6, cy + 1.0, h + 0.6, top + 0.8, w=0.6)


def salt_works(mb, rig, seed=128):
    rnd = random.Random(seed)
    # Evaporation pans: shallow clay basins of brine, whiter as they dry.
    for i in range(3):
        for j in range(2):
            x, y = -3.4 + i * 2.5, -3.2 + j * 2.0
            mb.box((x, y, 0.1), (2.3, 1.8, 0.2), "clay")
            mb.box((x, y, 0.19), (2.0, 1.5, 0.04), ("water", "glass", "white")[(i + j) % 3])
            if (i + j) % 3 == 2:
                for k in range(3):
                    mb.sphere((x - 0.6 + k * 0.6, y, 0.2), 0.24, "white", segments=6, rings=4, scale=(1, 1, 0.6))
    # A sluice channel from the shore with a little gate.
    mb.box((-4.9, -2.2, 0.08), (0.5, 4.0, 0.16), "clay")
    mb.box((-4.9, -2.2, 0.15), (0.3, 4.0, 0.04), "water")
    for s in (-1, 1):
        mb.box((-4.9 + s * 0.3, -0.4, 0.5), (0.1, 0.1, 1.0), "timber")
    mb.box((-4.9, -0.4, 0.95), (0.8, 0.1, 0.1), "timber")
    mb.box((-4.9, -0.4, 0.5), (0.45, 0.05, 0.6), "plank")
    # The boiling house: an open shed with iron pans over a brick furnace.
    cx, cy, w, d = 0.6, 2.2, 6.0, 3.2
    for ax in (-1, 0, 1):
        for ay in (-1, 1):
            mb.box((cx + ax * w / 2, cy + ay * d / 2, 1.3), (0.18, 0.18, 2.6), "timber")
    top = P.gable_roof(mb, cx, cy, w, d, 2.6, 1.6, SHINGLE, rows=5, overhang=0.5, gable=None, barge="timber")
    mb.box((cx, cy + d / 2 - 0.05, 1.0), (w, 0.08, 2.0), "plank")
    mb.box((cx - 0.6, cy, 0.4), (3.6, 1.6, 0.8), "brick")
    for x in (-1.5, 0.3):
        mb.box((cx + x, cy, 0.86), (1.5, 1.3, 0.14), "iron")
        mb.box((cx + x, cy, 0.92), (1.3, 1.1, 0.04), "white")
        mb.box((cx + x, cy - 0.82, 0.3), (0.5, 0.06, 0.4), "ember")
    P.chimney(mb, cx + 1.7, cy + 0.2, 0, top + 0.6, w=0.7, mat="brick", cap="stone_dark", pots=0)
    # Salt drying in cone-shaped baskets, sacks, a rake and firewood.
    for i in range(4):
        x = cx + 2.4 + (i % 2) * 0.6
        y = cy - 2.4 - (i // 2) * 0.6
        mb.cylinder((x, y, 0), (x, y, 0.6), 0.08, 0.28, "thatch_dark", segments=8)
        mb.cylinder((x, y, 0.6), (x, y, 0.85), 0.26, 0.0, "white", segments=8)
    for x, y in ((4.4, 1.2), (4.9, 1.6), (4.6, 2.2)):
        sack(mb, x, y, mat="white")
    mb.sphere((4.4, 3.4, 0), 0.9, "white", segments=7, rings=4, scale=(1.2, 1, 0.6))
    P.beam(mb, (-2.4, 0.2, 0), (-2.0, 0.8, 1.9), 0.035, "wood")
    mb.box((-2.42, 0.18, 0.06), (0.6, 0.08, 0.08), "wood")
    game.log_pile(mb, -3.6, 2.6, length=1.8, rows=3)


def make(name, fn, colors=None, **kw):
    def build():
        mb = P.begin()
        rig = P.Rig()
        fn(mb, rig, **kw)
        P.finish(mb, name, colors or P.BASE, rig)
    return build


SLATE = dict(roof=0x5A6470, roof_dark=0x46505A)

MODELS = {
    "bld_lumber_camp": make("bld_lumber_camp", lumber_camp),
    "bld_storehouse_great_timber": make("bld_storehouse_great_timber", great_storehouse),
    "bld_storehouse_great_brick": make("bld_storehouse_great_brick", great_storehouse, upper="brick", roof=("slate", "slate_dark")),
    "bld_barracks_great_stone": make("bld_barracks_great_stone", barracks, P.palette(**SLATE)),
    "bld_barracks_great_blue": make("bld_barracks_great_blue", barracks, P.STONE_BLUE),
    "bld_barracks_great_sandstone": make("bld_barracks_great_sandstone", barracks, P.SANDSTONE_RED),
    "bld_winery": make("bld_winery", winery),
    "bld_salt_works": make("bld_salt_works", salt_works),
    "bld_granary_great_thatch": make("bld_granary_great_thatch", great_storehouse, roof=("thatch", "thatch_dark"), goods="grain"),
    "bld_granary_great_tiles": make("bld_granary_great_tiles", great_storehouse, upper="stone", goods="grain"),
    "bld_meeting_hall": make("bld_meeting_hall", meeting_hall),
    "bld_meeting_hall_shingles": make("bld_meeting_hall_shingles", meeting_hall,
                                      P.palette(thatch=0x7A5A3C, thatch_dark=0x614530, banner=0x3E7A46)),
}
