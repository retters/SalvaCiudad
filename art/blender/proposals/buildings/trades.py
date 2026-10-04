"""Working buildings: stable, granary on stilts, fishing hut on stilts,
forge with bellows, mine head with a winch, guard house and market hall."""

import math
import random

import parts as P
import castles
from civic import storey
from mills import sack, hand_cart
from parts import game, TAU

SHINGLE = ("shingle", "shingle_dark")
THATCH = ("thatch", "thatch_dark")
ROOF = ("roof", "roof_dark")


def horse_head(mb, x, z, coat="fur"):
    """A horse looking out over a stall door (wall face frame)."""
    P.beam(mb, (x, 0.1, z - 0.3), (x, -0.45, z + 0.25), 0.3, coat)
    mb.box((x, -0.62, z + 0.22), (0.22, 0.55, 0.26), coat)
    mb.box((x, -0.88, z + 0.17), (0.18, 0.16, 0.2), "charcoal")
    for s in (-1, 1):
        mb.cylinder((x + s * 0.08, -0.42, z + 0.34), (x + s * 0.1, -0.4, z + 0.52), 0.05, 0.0, coat, segments=4)
    mb.box((x, -0.2, z + 0.28), (0.06, 0.5, 0.2), "charcoal")


def stable(mb, rig, walls="plank", roof=THATCH, seed=22):
    rnd = random.Random(seed)
    cx, cy, w, d, h = 0.0, 1.0, 9.0, 4.4, 2.9
    if walls == "stone":
        storey(mb, rnd, "stone", cx, cy, 0, w, d, h)
    else:
        mb.box((cx, cy, 0.15), (w + 0.2, d + 0.2, 0.3), "stone")
        P.plank_block(mb, cx, cy, 0.3, w, d, h - 0.3)
    top = P.gable_roof(mb, cx, cy, w, d, h, 2.5, roof, rows=6, overhang=0.6, gable="plank", end_overhang=0.4)
    with P.face(mb, cx, cy, w, d, "front") as L:
        n = 4
        for i in range(n):
            x = -L / 2 + (i + 0.5) * L / n
            mb.box((x, -0.02, 1.25), (1.5, 0.1, 2.1), "timber")
            mb.box((x, -0.05, 1.75), (1.3, 0.1, 0.95), "charcoal")
            mb.box((x, -0.08, 0.75), (1.3, 0.08, 1.05), "plank_dark")
            P.beam(mb, (x - 0.6, -0.13, 0.3), (x + 0.6, -0.13, 1.2), 0.06, "timber")
            mb.box((x, -0.13, 1.24), (1.3, 0.05, 0.08), "iron")
            if i in (0, 2):
                horse_head(mb, x + 0.1, 1.6, "fur" if i == 0 else "bone")
    # The hay loft door in the left gable, with its hoist.
    with P.face(mb, cx, cy, w, d, "left"):
        mb.box((0, -0.04, h + 0.8), (1.1, 0.08, 1.1), "timber")
        mb.box((0, -0.07, h + 0.8), (0.9, 0.08, 0.9), "hay")
        mb.box((0, -0.5, h + 1.75), (0.14, 1.2, 0.14), "timber")
        mb.box((0, -1.0, h + 1.2), (0.03, 0.03, 1.0), "rope")
        P.window(mb, -1.0, 1.6, w=0.6, h=0.6, shutter=None)
    with P.face(mb, cx, cy, w, d, "right"):
        P.plank_door(mb, 0, 0.3, w=1.4, h=2.0, double=True)
    # The paddock in front.
    y0 = cy - d / 2 - 3.2
    game.fence(mb, -4.6, y0, 1.2, y0, posts=6, h=1.1)
    game.fence(mb, 2.6, y0, 4.6, y0, posts=2, h=1.1)
    game.fence(mb, -4.6, y0, -4.6, cy - d / 2 - 0.3, posts=3, h=1.1)
    game.fence(mb, 4.6, y0, 4.6, cy - d / 2 - 0.3, posts=3, h=1.1)
    mb.box((-3.0, y0 + 0.6, 0.38), (1.8, 0.55, 0.32), "wood")
    mb.box((-3.0, y0 + 0.6, 0.5), (1.6, 0.4, 0.1), "water")
    for sx in (-0.7, 0.7):
        mb.box((-3.0 + sx, y0 + 0.6, 0.12), (0.12, 0.5, 0.24), "timber")
    for x, y in ((3.6, y0 + 0.8), (3.6, y0 + 1.5)):
        P.hay_bale(mb, x, y)
    P.hay_bale(mb, 3.6, y0 + 1.15, z=0.6)
    game.barrel(mb, 0.5, cy - d / 2 - 0.5, h=0.8, r=0.3)
    mb.box((1.4, cy - d / 2 - 0.5, 0.5), (0.08, 0.08, 1.0), "timber")  # A pitchfork leaning.
    for s in (-0.08, 0, 0.08):
        mb.box((1.4 + s, cy - d / 2 - 0.5, 1.1), (0.02, 0.02, 0.25), "iron")


def staddle_granary(mb, rig, roof=THATCH, seed=24):
    w, d, z0, h = 4.6, 3.4, 1.4, 2.3
    for sx in (-1, 0, 1):
        for sy in (-1, 1):
            x, y = sx * (w / 2 - 0.3), 0.3 + sy * (d / 2 - 0.3)
            mb.cylinder((x, y, 0), (x, y, z0 - 0.25), 0.3, 0.2, "wall", segments=8)
            mb.cylinder((x, y, z0 - 0.25), (x, y, z0 - 0.1), 0.55, 0.5, "wall_light", segments=10)
    mb.box((0, 0.3, z0 - 0.02), (w + 0.3, d + 0.3, 0.18), "timber")
    P.plank_block(mb, 0, 0.3, z0 + 0.07, w, d, h)
    for side in ("front", "back"):
        with P.face(mb, 0, 0.3, w, d, side) as L:
            for i in range(3):
                x = -L / 2 + (i + 0.5) * L / 3
                if side == "front" and i == 1:
                    continue
                for k in range(4):
                    mb.box((x, -0.03, z0 + 1.0 + k * 0.22), (0.9, 0.06, 0.07), "charcoal")
    with P.face(mb, 0, 0.3, w, d, "front"):
        P.plank_door(mb, 0, z0 + 0.1, w=0.9, h=1.6)
    P.gable_roof(mb, 0, 0.3, w, d, z0 + 0.07 + h, 2.0, roof, rows=5, overhang=0.7, gable="plank", end_overhang=0.5)
    # A ladder that is taken away at night, sacks and a cat's worth of crates.
    for sx in (-0.3, 0.3):
        P.beam(mb, (sx, -2.6, 0), (sx, 0.3 - d / 2 - 0.1, z0 + 0.1), 0.08, "timber")
    for i in range(5):
        t = (i + 0.5) / 5
        mb.box((0, -2.6 + (0.3 - d / 2 - 0.1 + 2.6) * t, (z0 + 0.1) * t), (0.6, 0.05, 0.05), "wood")
    sack(mb, 1.5, -2.2)
    sack(mb, 2.0, -2.0, s=0.9)
    sack(mb, 1.75, -2.1, 0.45, s=0.85)
    game.crate(mb, -1.9, -2.2, s=0.6, top="hay")


def fishing_hut(mb, rig, roof=SHINGLE, seed=26):
    z0 = 1.3
    # Piles and the deck.
    for x in (-2.6, -0.9, 0.9, 2.6):
        for y in (-3.4, -1.2, 1.0, 3.2):
            mb.cylinder((x, y, -0.3), (x, y, z0 + (1.0 if (abs(x) > 2 and y < 0) else 0.0)), 0.13, 0.11, "log", segments=6)
    for x in (-2.6, 2.6):
        P.beam(mb, (x, -3.4, 0.3), (x, -1.2, z0 - 0.15), 0.07, "timber")
        P.beam(mb, (x, 3.2, 0.3), (x, 1.0, z0 - 0.15), 0.07, "timber")
    mb.box((0, -0.1, z0 - 0.08), (5.6, 7.0, 0.12), "plank")
    for i in range(1, 12):
        mb.box((-2.8 + i * 5.6 / 12, -0.1, z0 - 0.015), (0.03, 7.0, 0.01), "plank_dark")
    for x in (-2.6, 2.6):
        mb.box((x, -2.3, z0 + 0.9), (0.06, 2.3, 0.06), "rope")
    # The hut at the back of the deck.
    cy, w, d, h = 1.5, 3.6, 3.0, 2.2
    P.plank_block(mb, 0.6, cy, z0, w, d, h)
    P.gable_roof(mb, 0.6, cy, w, d, z0 + h, 1.5, roof, rows=4, overhang=0.45, gable="plank")
    with P.face(mb, 0.6, cy, w, d, "front"):
        P.plank_door(mb, -0.7, z0, w=0.85, h=1.6)
        P.window(mb, 0.8, z0 + 1.2, w=0.6, h=0.6, shutter=None, lit=True)
    P.chimney(mb, 1.6, cy + 0.6, z0 + h + 0.4, z0 + h + 2.3, w=0.4, mat="iron", cap="charcoal", pots=0)
    # A rack of drying fish, nets, a barrel, a lantern.
    for x in (-2.4, -1.2):
        mb.box((x, cy + 0.2, z0 + 0.9), (0.08, 0.08, 1.8), "timber")
    mb.cylinder((-2.45, cy + 0.2, z0 + 1.7), (-1.15, cy + 0.2, z0 + 1.7), 0.03, 0.03, "wood", segments=5)
    for k in range(5):
        mb.box((-2.3 + k * 0.25, cy + 0.2, z0 + 1.48), (0.09, 0.04, 0.38), "fish")
    mb.box((1.9, -2.6, z0 + 0.12), (1.2, 0.9, 0.2), "rope")
    with mb.placed((-2.0, -0.6, z0)):
        game.barrel(mb, 0, 0, h=0.8, r=0.3)
    game.crate(mb, -1.2, -0.7, s=0.5, z=z0, top="fish")
    mb.box((2.6, -3.4, z0 + 1.15), (0.2, 0.2, 0.3), "glow")
    # Steps down to the shore at the back and a ladder to the boat at the front.
    with mb.placed((-1.9, 3.4, 0), math.pi):
        P.stairs(mb, 0, -1.6, 0, z0 - 0.02, 1.0, 1.6, mat="plank", solid=False)
        for sx in (-0.5, 0.5):
            P.beam(mb, (sx, -1.6, 0), (sx, 0, z0 - 0.1), 0.08, "timber")
    # The rowboat tied at the front.
    with mb.placed((-0.8, -4.2, 0.0), 0.1):
        hull = mb.prism([(-1.3, -0.45), (1.2, -0.45), (1.75, 0.0), (1.2, 0.45), (-1.3, 0.45)], 0.0, 0.5, "wood")
        for v in hull:
            if v.co.z < 0.1:
                v.co.x *= 0.8
                v.co.y *= 0.6
        mb.box((0.0, 0, 0.47), (2.3, 0.72, 0.06), "plank_dark")
        for x in (-0.6, 0.5):
            mb.box((x, 0, 0.52), (0.25, 0.86, 0.05), "plank")
        P.beam(mb, (-0.2, 0.2, 0.55), (1.0, 0.75, 0.75), 0.04, "wood_light")


def forge(mb, rig, walls="stone", roof=("tile_red", "tile_red_dark"), seed=28):
    rnd = random.Random(seed)
    # The closed shop at the back and the open smithy in front of it.
    cx, cy, w, d, h = 0.0, 1.9, 7.0, 3.0, 3.0
    storey(mb, rnd, walls, cx, cy, 0, w, d, h)
    top = P.gable_roof(mb, cx, cy - 1.0, w, d + 2.0, h, 2.4, roof, rows=6, overhang=0.4,
                       gable="wall" if walls == "stone" else "brick", end_overhang=0.3)
    for sx in (-1, 0.15, 1):
        x = cx + sx * (w / 2 - 0.1)
        mb.box((x, cy - d / 2 - 1.9, h / 2), (0.22, 0.22, h), "timber")
        P.beam(mb, (x, cy - d / 2 - 1.9, h - 0.9), (x, cy - d / 2 - 1.2, h - 0.1), 0.1, "timber")
    mb.box((cx, cy - d / 2 - 1.9, h - 0.05), (w + 0.2, 0.22, 0.22), "timber")
    for sx in (-1, 1):
        mb.box((cx + sx * (w / 2 - 0.1), cy - d / 2 - 0.95, h - 0.05), (0.2, 1.9, 0.2), "timber")
    mb.box((cx, cy - d / 2 - 1.0, 0.04), (w, 2.0, 0.08), "paving")
    with P.face(mb, cx, cy, w, d, "front"):
        P.plank_door(mb, 2.3, 0.1, w=1.0, h=1.8)
        P.window(mb, 0.4, 1.7, w=0.7, h=0.7, shutter=None, lit=True)
    # The hearth with its hood and chimney, on the left.
    hx, hy = cx - 2.2, cy - d / 2 - 0.55
    mb.box((hx, hy, 0.45), (1.7, 1.1, 0.9), "brick")
    mb.box((hx, hy, 0.92), (1.8, 1.2, 0.1), "wall_dark")
    mb.box((hx, hy - 0.05, 0.99), (1.2, 0.7, 0.08), "charcoal")
    for i in range(5):
        mb.sphere((hx - 0.4 + i * 0.2, hy - 0.05 + 0.1 * (i % 2), 1.04), 0.11, "ember" if i % 2 else "lava",
                  segments=5, rings=3)
    hood = mb.prism([(hx - 0.9, hy - 0.6), (hx + 0.9, hy - 0.6), (hx + 0.9, hy + 0.55), (hx - 0.9, hy + 0.55)], 1.9, 2.9,
                    "brick")
    for v in hood:
        if v.co.z > 2.4:
            v.co.x = hx + (v.co.x - hx) * 0.45
            v.co.y = hy + 0.2 + (v.co.y - hy) * 0.45
    for sx in (-1, 1):
        mb.box((hx + sx * 0.8, hy + 0.45, 1.45), (0.2, 0.2, 1.0), "brick")
    P.chimney(mb, hx, hy + 0.2, 2.9, top + 1.2, w=0.8, mat="brick", cap="wall_dark", pots=0)
    # The bellows, which pump.
    bx, by, bz = hx + 1.9, hy, 1.05
    mb.box((bx + 0.1, by, bz - 0.5), (1.3, 0.12, 0.9), "timber")
    mb.cylinder((bx - 0.85, by, bz), (bx - 1.25, by, bz), 0.06, 0.04, "iron", segments=6)
    P.prism_xz(mb, [(bx - 0.85, bz - 0.07), (bx + 0.75, bz - 0.2), (bx + 0.75, bz - 0.12), (bx - 0.85, bz)],
               by - 0.45, by + 0.45, "wood")
    P.prism_xz(mb, [(bx - 0.8, bz), (bx + 0.7, bz - 0.12), (bx + 0.7, bz + 0.22), (bx - 0.8, bz + 0.05)],
               by - 0.38, by + 0.38, "hide")
    with mb.bone("bellows"):
        P.prism_xz(mb, [(bx - 0.85, bz + 0.04), (bx + 0.75, bz + 0.28), (bx + 0.75, bz + 0.36), (bx - 0.85, bz + 0.11)],
                   by - 0.45, by + 0.45, "wood")
        mb.cylinder((bx + 0.75, by, bz + 0.34), (bx + 1.35, by, bz + 0.5), 0.04, 0.04, "wood_light", segments=5)
    rig.bone("bellows", (bx - 0.85, by, bz + 0.05), (bx + 0.2, by, bz + 0.2), None)
    rig.add("pump", 1.6, lambda t: {"bellows": [(P.kit.Y, 5 + 7 * math.sin(TAU * t))]})
    # The anvil on its stump, the quench trough, the grindstone, tools.
    ax, ay = cx + 0.3, cy - d / 2 - 1.2
    mb.cylinder((ax, ay, 0), (ax, ay, 0.55), 0.32, 0.3, "log", segments=8)
    mb.box((ax, ay, 0.62), (0.3, 0.22, 0.14), "iron")
    mb.box((ax, ay, 0.76), (0.62, 0.26, 0.16), "iron")
    mb.cylinder((ax + 0.3, ay, 0.78), (ax + 0.6, ay, 0.8), 0.1, 0.0, "iron", segments=6)
    mb.box((ax - 0.1, ay - 0.05, 0.9), (0.3, 0.05, 0.05), "wood")
    mb.box((ax + 0.05, ay - 0.05, 0.9), (0.1, 0.14, 0.1), "iron")
    mb.box((cx + 1.6, ay - 0.2, 0.3), (1.0, 0.5, 0.6), "wood")
    mb.box((cx + 1.6, ay - 0.2, 0.58), (0.86, 0.36, 0.06), "water")
    gx, gy = cx + 3.0, cy - d / 2 - 2.6
    for s in (-1, 1):
        P.beam(mb, (gx + s * 0.25, gy - 0.3, 0), (gx + s * 0.25, gy, 0.75), 0.07, "timber")
        P.beam(mb, (gx + s * 0.25, gy + 0.3, 0), (gx + s * 0.25, gy, 0.75), 0.07, "timber")
    mb.cylinder((gx - 0.12, gy, 0.75), (gx + 0.12, gy, 0.75), 0.42, 0.42, "wall_dark", segments=12)
    mb.box((cx - 0.9, cy - d / 2 - 0.12, 1.7), (1.3, 0.08, 0.1), "timber")  # The tool rack on the wall.
    for i in range(4):
        mb.box((cx - 1.4 + i * 0.33, cy - d / 2 - 0.16, 1.35), (0.05, 0.05, 0.7), "wood" if i % 2 else "iron")
        mb.box((cx - 1.4 + i * 0.33, cy - d / 2 - 0.16, 1.02), (0.16, 0.06, 0.12), "iron")
    mb.sphere((cx - 3.0, cy - d / 2 - 2.5, 0.0), 0.75, "charcoal", segments=8, rings=5, scale=(1.2, 1, 0.6))
    game.barrel(mb, cx + 3.0, cy - d / 2 - 0.5, h=0.8, r=0.3)
    with mb.placed((cx + 3.2, cy - d / 2 - 1.95, 0), -math.pi / 2):  # A horseshoe sign.
        P.hanging_sign(mb, rig, 0, 0, 2.6, arm=1.0, board=(0.7, 0.6), emblem="iron")


def mine_head(mb, rig, seed=30):
    rnd = random.Random(seed)
    sx0, sy0 = -0.6, 0.6
    # The shaft collar.
    for side in P.SIDES:
        with P.face(mb, sx0, sy0, 2.6, 2.6, side) as L:
            mb.box((0, 0.2, 0.4), (L, 0.4, 0.8), "wall")
            mb.box((0, 0.2, 0.84), (L + 0.1, 0.5, 0.1), "wall_light")
    mb.box((sx0, sy0, 0.05), (1.9, 1.9, 0.1), "charcoal")
    # The headframe: four legs leaning in, braces and the roofed sheave house.
    top = 5.2
    for ax in (-1, 1):
        for ay in (-1, 1):
            P.beam(mb, (sx0 + ax * 1.7, sy0 + ay * 1.7, 0), (sx0 + ax * 0.7, sy0 + ay * 0.7, top), 0.2, "timber")
    for z, k in ((1.9, 1.33), (3.6, 1.0)):
        for ax in (-1, 1):
            mb.box((sx0 + ax * k, sy0, z), (0.14, 2 * k, 0.14), "timber")
            mb.box((sx0, sy0 + ax * k, z), (2 * k, 0.14, 0.14), "timber")
    for ax in (-1, 1):
        P.beam(mb, (sx0 + ax * 1.33, sy0 - 1.33, 1.9), (sx0 + ax * 1.0, sy0 + 1.0, 3.6), 0.09, "timber")
        P.beam(mb, (sx0 - 1.33, sy0 + ax * 1.33, 1.9), (sx0 + 1.0, sy0 + ax * 1.0, 3.6), 0.09, "timber")
    mb.box((sx0, sy0, top + 0.9), (1.7, 1.7, 1.8), "plank")
    for side in P.SIDES:
        with P.face(mb, sx0, sy0, 1.7, 1.7, side) as L:
            for x in (-L / 2, L / 2):
                mb.box((x, 0, top + 0.9), (0.14, 0.14, 1.8), "timber")
            mb.box((0, -0.02, top + 0.9), (0.05, 0.05, 1.8), "plank_dark")
    P.pyramid_roof(mb, sx0, sy0, top + 1.8, 1.7, 1.7, 1.3, SHINGLE, rows=3, overhang=0.4, finial="timber")
    # The bucket and its rope, which go up and down (the rope hides in the sheave house).
    travel = 1.7
    with mb.bone("bucket"):
        mb.cylinder((sx0, sy0, 0.5), (sx0, sy0, 1.15), 0.36, 0.44, "wood", segments=8)
        mb.cylinder((sx0, sy0, 0.62), (sx0, sy0, 0.68), 0.41, 0.41, "iron", segments=8)
        mb.cylinder((sx0, sy0, 1.0), (sx0, sy0, 1.06), 0.45, 0.45, "iron", segments=8)
        mb.sphere((sx0, sy0, 1.15), 0.36, "rock_dark", segments=6, rings=4, scale=(1, 1, 0.5))
        for s in (-1, 1):
            P.beam(mb, (sx0 + s * 0.4, sy0, 1.1), (sx0, sy0, 1.7), 0.03, "iron")
        mb.box((sx0, sy0, 1.7 + (top - 1.7) / 2), (0.05, 0.05, top - 1.7), "rope")
    rig.bone("bucket", (sx0, sy0, 0.5), (sx0, sy0, 1.5), None)
    # The winch beside the shaft: a drum with two cranks.
    wx, wy = sx0 + 2.9, sy0
    for s in (-1, 1):
        mb.box((wx, wy + s * 0.75, 0.6), (0.2, 0.16, 1.2), "timber")
        P.beam(mb, (wx - 0.5, wy + s * 0.75, 0), (wx, wy + s * 0.75, 0.9), 0.08, "timber")
        P.beam(mb, (wx + 0.5, wy + s * 0.75, 0), (wx, wy + s * 0.75, 0.9), 0.08, "timber")
    with mb.bone("drum"):
        mb.cylinder((wx, wy - 0.62, 1.05), (wx, wy + 0.62, 1.05), 0.26, 0.26, "wood", segments=8)
        mb.cylinder((wx, wy - 0.4, 1.05), (wx, wy + 0.4, 1.05), 0.31, 0.31, "rope", segments=8)
        for s in (-1, 1):
            mb.cylinder((wx, wy + s * 0.62, 1.05), (wx, wy + s * 1.0, 1.05), 0.04, 0.04, "iron", segments=5)
            mb.box((wx, wy + s * 1.0, 1.05 + s * 0.18), (0.05, 0.05, 0.4), "iron")
            mb.cylinder((wx, wy + s * 1.0, 1.05 + s * 0.36), (wx, wy + s * 1.3, 1.05 + s * 0.36), 0.035, 0.035, "wood_light",
                        segments=5)
    rig.bone("drum", (wx, wy, 1.05), (wx, wy + 1, 1.05), None)
    P.beam(mb, (wx - 0.25, wy, 1.2), (sx0 + 0.2, sy0, top + 0.3), 0.03, "rope")

    def lift(t):
        up = 0.5 - 0.5 * math.cos(TAU * t)
        return {"drum": [(P.kit.Y, 540 * up)]}, {"bucket": (0, 0, travel * up)}

    rig.add("lift", 6.0, lift)
    # Rails and an ore cart, the ore heap, a tool shed.
    for s in (-1, 1):
        mb.box((sx0 + s * 0.35, -2.6, 0.06), (0.07, 3.0, 0.08), "iron")
    for i in range(5):
        mb.box((sx0, -1.3 - i * 0.6, 0.03), (1.1, 0.16, 0.06), "timber")
    with mb.placed((sx0, -2.9, 0)):
        tub = mb.prism([(-0.45, -0.6), (0.45, -0.6), (0.45, 0.6), (-0.45, 0.6)], 0.3, 0.95, "plank_dark")
        for v in tub:
            if v.co.z < 0.5:
                v.co.x *= 0.7
        mb.sphere((0, 0, 0.95), 0.42, "rock_dark", segments=6, rings=4, scale=(0.9, 1.2, 0.5))
        for sx in (-1, 1):
            for sy in (-1, 1):
                mb.cylinder((sx * 0.33, sy * 0.35, 0.22), (sx * 0.4, sy * 0.35, 0.22), 0.18, 0.18, "iron", segments=8)
    P.rocks(mb, rnd, 2.6, -2.6, 1.0, n=9, mats=("rock_dark", "rock", "clay"), size=0.55)
    with mb.placed((-3.0, 2.2, 0)):
        P.plank_block(mb, 0, 0, 0, 1.8, 2.4, 2.0)
        game.sloped_slab(mb, -1.1, 1.1, -1.5, 1.4, 2.0, 2.6, 0.1, "shingle")
        with P.face(mb, 0, 0, 1.8, 2.4, "front"):
            P.plank_door(mb, 0, 0.0, w=0.8, h=1.6)
    for i in range(2):
        mb.box((-3.2 + i * 0.25, 0.7, 0.7), (0.05, 0.05, 1.4), "wood")
        mb.box((-3.2 + i * 0.25, 0.7, 1.4), (0.4, 0.06, 0.08), "iron")
    mb.box((2.3, 3.2, 1.0), (0.1, 0.1, 2.0), "timber")
    mb.box((2.3, 3.0, 1.9), (0.1, 0.5, 0.08), "timber")
    mb.box((2.3, 2.8, 1.65), (0.2, 0.2, 0.3), "glow")


def guard_house(mb, rig, seed=32):
    rnd = random.Random(seed)
    cx, cy, w, d, h = -0.8, 0.8, 5.0, 4.4, 4.4
    P.stone_block(mb, cx, cy, 0, w, d, h, rnd, band=(h * 0.55,))
    P.battlements(mb, cx, cy, h, w, d)
    mb.box((cx, cy, h + 0.5), (w - 1.6, d - 1.6, 1.0), "wall")
    P.pyramid_roof(mb, cx, cy, h + 1.0, w - 1.6, d - 1.6, 1.9, ROOF, rows=4, overhang=0.35, ridge=0.6, finial="gold")
    with P.face(mb, cx, cy, w, d, "front"):
        P.arched_door(mb, -0.6, 0.05, w=1.3, h=2.3)
        P.window(mb, 1.4, 1.7, w=0.6, h=0.7, shutter=None, frame="trim")
        for i in range(3):
            mb.box((1.4 - 0.2 + i * 0.2, -0.12, 1.7), (0.04, 0.04, 0.7), "iron")
        P.wall_banner(mb, 1.4, 4.0, w=0.8, h=1.5)
        P.arrow_slit(mb, -0.6, 3.4, h=0.8)
    with P.face(mb, cx, cy, w, d, "left"):
        P.arrow_slit(mb, -0.9, 2.0)
        P.arrow_slit(mb, 0.9, 2.0)
    castles.tower(mb, rig, rnd, cx + w / 2 + 0.5, cy + d / 2 - 0.9, 1.45, 7.6, top="crown", flag=True)
    # The yard: a weapon rack, a brazier, a bench, a sentry box.
    y = cy - d / 2 - 1.3
    for x in (cx - 2.0, cx - 0.9):
        mb.box((x, y, 0.75), (0.08, 0.08, 1.5), "timber")
    mb.box((cx - 1.45, y, 1.3), (1.2, 0.08, 0.08), "timber")
    mb.box((cx - 1.45, y, 0.25), (1.2, 0.3, 0.08), "timber")
    for i in range(4):
        x = cx - 1.9 + i * 0.3
        mb.cylinder((x, y - 0.05, 0.25), (x, y - 0.12, 2.1), 0.03, 0.03, "wood", segments=4)
        mb.cylinder((x, y - 0.12, 2.1), (x, y - 0.13, 2.4), 0.06, 0.0, "iron", segments=4)
    bx, by = cx + 1.6, y - 0.4
    for i in range(3):
        a = TAU * i / 3
        P.beam(mb, (bx + 0.35 * math.cos(a), by + 0.35 * math.sin(a), 0), (bx, by, 0.8), 0.05, "iron")
    mb.cylinder((bx, by, 0.75), (bx, by, 1.0), 0.2, 0.36, "iron", segments=8)
    mb.cylinder((bx, by, 1.0), (bx, by, 1.3), 0.26, 0.0, "ember", segments=6)
    with mb.placed((cx + w / 2 + 0.9, cy - d / 2 - 1.6, 0)):
        P.plank_block(mb, 0, 0, 0, 1.1, 1.1, 2.1)
        mb.box((0, -0.53, 1.0), (0.7, 0.08, 1.8), "charcoal")
        P.pyramid_roof(mb, 0, 0, 2.1, 1.1, 1.1, 0.9, ROOF, rows=2, overhang=0.2)
        for k in range(3):
            P.prism_xz(mb, [(-0.55, 0.3 + k * 0.6), (0.55, 0.6 + k * 0.6), (0.55, 0.9 + k * 0.6), (-0.55, 0.6 + k * 0.6)],
                       0.56, 0.58, "banner")


def market_hall(mb, rig, upper="timber", roof=("tile_red", "tile_red_dark"), seed=34):
    rnd = random.Random(seed)
    cx, cy, w, d, h1, h2 = 0.0, 0.3, 10.4, 6.0, 3.3, 2.6
    mb.box((cx, cy, 0.05), (w + 0.6, d + 0.6, 0.1), "paving")
    xs = [cx - w / 2 + 0.25 + i * (w - 0.5) / 4 for i in range(5)]
    for x in xs:
        for sy in (-1, 1):
            y = cy + sy * (d / 2 - 0.25)
            mb.box((x, y, 0.35), (0.6, 0.6, 0.6), "wall")
            mb.box((x, y, 0.6 + (h1 - 0.6) / 2), (0.3, 0.3, h1 - 0.6), "timber")
            for s in (-1, 1):
                if xs[0] - 0.1 < x + s * 0.8 < xs[-1] + 0.1:
                    P.beam(mb, (x, y, h1 - 0.9), (x + s * 0.8, y, h1 - 0.05), 0.11, "timber")
        mb.box((x, cy, h1 - 0.12), (0.26, d - 0.5, 0.26), "timber")
        for sy in (-1, 1):
            P.beam(mb, (x, cy + sy * (d / 2 - 0.25), h1 - 0.9), (x, cy + sy * (d / 2 - 1.1), h1 - 0.1), 0.1, "timber")
    z1 = h1 + 0.2
    W, D = w + 0.4, d + 0.4
    mb.box((cx, cy, h1 + 0.1), (W + 0.1, D + 0.1, 0.22), "timber")
    storey(mb, rnd, upper, cx, cy, z1, W, D, h2, plinth=0, cross=True)
    for side in ("front", "back"):
        with P.face(mb, cx, cy, W, D, side) as L:
            for i in range(4):
                P.window(mb, -L / 2 + (i + 0.5) * L / 4, z1 + h2 * 0.55, w=0.9, h=1.0, shutter=None)
    for side in ("left", "right"):
        with P.face(mb, cx, cy, W, D, side) as L:
            P.window(mb, 0, z1 + h2 * 0.55, w=0.9, h=1.0, shutter=None)
    zr = z1 + h2
    P.pyramid_roof(mb, cx, cy, zr, W, D, 3.0, roof, rows=6, overhang=0.5, ridge=W - D)
    # A cupola with a weathervane on the ridge.
    mb.box((cx, cy, zr + 3.3), (1.3, 1.3, 1.2), "plaster")
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.box((cx + sx * 0.62, cy + sy * 0.62, zr + 3.3), (0.12, 0.12, 1.2), "timber")
    for side in P.SIDES:
        with P.face(mb, cx, cy, 1.3, 1.3, side):
            mb.box((0, -0.03, zr + 3.4), (0.6, 0.06, 0.7), "window")
    tip = P.pyramid_roof(mb, cx, cy, zr + 3.9, 1.3, 1.3, 1.6, roof, rows=3, overhang=0.3)
    mb.cylinder((cx, cy, tip - 0.1), (cx, cy, tip + 0.9), 0.03, 0.03, "iron", segments=5)
    with mb.bone("vane"):
        P.prism_xz(mb, [(cx - 0.5, tip + 0.75), (cx + 0.2, tip + 0.75), (cx + 0.55, tip + 0.87), (cx + 0.2, tip + 0.99),
                        (cx - 0.5, tip + 0.99)], cy - 0.015, cy + 0.015, "gold")
    rig.bone("vane", (cx, cy, tip + 0.6), (cx, cy, tip + 1.1), None)
    rig.add("turn", 6.0, lambda t: {"vane": [(P.kit.Z, 35 * math.sin(TAU * t) + 15 * math.sin(2 * TAU * t))]})
    # The stair up to the hall at the right end.
    with mb.placed((cx + w / 2 + 0.9, cy + d / 2 - 0.4, 0), math.pi):
        P.stairs(mb, 0, 0, 0, z1, 1.2, 4.6, mat="plank", solid=False, step=0.28)
        for sx in (-0.6, 0.6):
            P.beam(mb, (sx, 0, 0), (sx, 4.6, z1 - 0.1), 0.12, "timber")
        mb.box((0.6, 2.3, z1 / 2 + 0.9), (0.06, 4.6, 0.06), "timber")
    # Stalls under the hall.
    goods = ("berries", "bread", "fish", "cloth_white", "hide", "hay", "leaves", "cloth_red")
    for i in range(4):
        x = (xs[i] + xs[i + 1]) / 2
        for j, sy in enumerate((-1, 1)):
            y = cy + sy * 1.5
            mb.box((x, y, 0.8), (1.7, 0.8, 0.08), "wood")
            for sx in (-0.7, 0.7):
                mb.box((x + sx, y, 0.4), (0.1, 0.7, 0.8), "timber")
            for k in range(3):
                game.crate(mb, x - 0.5 + k * 0.5, y, s=0.36, z=0.84, top=goods[(i * 2 + j + k) % len(goods)])
    game.barrel(mb, cx - w / 2 - 0.1, cy - d / 2 - 0.2, h=0.9, r=0.33)
    game.barrel(mb, cx - w / 2 + 0.6, cy - d / 2 - 0.3, h=0.8, r=0.3)
    hand_cart(mb, cx + 2.0, cy - d / 2 - 1.0, 0.2)


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
    "bld_stable_plank_thatch": make("bld_stable_plank_thatch", stable, P.BASE),
    "bld_stable_stone_tiles": make("bld_stable_stone_tiles", stable, P.BASE, walls="stone",
                                   roof=("tile_red", "tile_red_dark")),
    "bld_granary_stilts_thatch": make("bld_granary_stilts_thatch", staddle_granary, P.BASE),
    "bld_granary_stilts_tiles": make("bld_granary_stilts_tiles", staddle_granary, P.BASE,
                                     roof=("tile_red", "tile_red_dark")),
    "bld_fishing_hut_stilts": make("bld_fishing_hut_stilts", fishing_hut, P.BASE),
    "bld_fishing_hut_stilts_thatch": make("bld_fishing_hut_stilts_thatch", fishing_hut, P.BASE, roof=THATCH),
    "bld_forge_stone": make("bld_forge_stone", forge, P.BASE),
    "bld_forge_brick": make("bld_forge_brick", forge, P.BASE, walls="brick", roof=("slate", "slate_dark")),
    "bld_mine_head": make("bld_mine_head", mine_head, P.BASE),
    "bld_guard_house_stone": make("bld_guard_house_stone", guard_house, P.STONE_BLUE),
    "bld_guard_house_sandstone": make("bld_guard_house_sandstone", guard_house, P.SANDSTONE_RED),
    "bld_market_hall_timber": make("bld_market_hall_timber", market_hall, P.BASE),
    "bld_market_hall_timber_blue": make("bld_market_hall_timber_blue", market_hall, P.BASE, roof=("roof", "roof_dark")),
    "bld_market_hall_brick": make("bld_market_hall_brick", market_hall, P.BASE, upper="brick",
                                  roof=("slate", "slate_dark")),
}
