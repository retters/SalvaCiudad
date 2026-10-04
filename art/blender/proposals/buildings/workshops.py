"""Craft workshops: a timber-framed house with the yard of its trade.
Tannery, weaver, tailor, cobbler, bowyer, armory, smokehouse and charcoal
burner: elaborate versions of the game's cottage-with-props workshops."""

import math
import random

import parts as P
import houses
from parts import game, TAU

OX, OY = -0.9, 0.9      # Where the house stands in the 8 x 7 m lot.
FRONT = OY + 0.45 - 1.6  # Its front wall.


def shop(mb, rig, level=2, style=0, seed=1):
    with mb.placed((OX, OY, 0)):
        houses.house(mb, rig, level=level, style=style, seed=seed, extras=False)


def sign(mb, rig, emblem, x=OX + 2.1, z=3.6):
    with mb.placed((x, FRONT - 0.2, 0), -math.pi / 2):
        P.hanging_sign(mb, rig, 0, 0, z, arm=1.0, board=(0.75, 0.6), emblem=emblem)


def hide_frame(mb, x, y, mat="hide", turn=0.0):
    with mb.placed((x, y, 0), turn):
        for s in (-0.5, 0.5):
            P.beam(mb, (s, 0.3, 0), (s, 0, 1.8), 0.05, "timber")
        mb.box((0, 0.02, 1.75), (1.2, 0.06, 0.06), "timber")
        mb.box((0, 0.13, 0.5), (1.2, 0.06, 0.06), "timber")
        P.prism_xz(mb, [(-0.38, 0.62), (0.38, 0.62), (0.46, 1.6), (0, 1.68), (-0.46, 1.6)], 0.04, 0.08, mat)


def vat(mb, x, y, liquid, r=0.55, h=0.55):
    mb.cylinder((x, y, 0), (x, y, h), r, r * 1.05, "wood", segments=10)
    for z in (h * 0.25, h * 0.8):
        mb.cylinder((x, y, z - 0.03), (x, y, z + 0.03), r * 1.07, r * 1.07, "iron", segments=10)
    mb.cylinder((x, y, h - 0.06), (x, y, h - 0.03), r * 0.92, r * 0.92, liquid, segments=10)


def tannery(mb, rig):
    shop(mb, rig, 2, 0)
    for i, c in enumerate(("clay", "soil", "tile_red_dark")):
        vat(mb, -3.0 + i * 1.25, -2.4, c)
    mb.box((1.2, -2.6, 0.15), (1.6, 1.0, 0.3), "wall")
    mb.box((1.2, -2.6, 0.29), (1.3, 0.7, 0.04), "white")
    hide_frame(mb, 3.0, -1.6, "hide", -0.3)
    hide_frame(mb, 3.2, 0.4, "fur", -math.pi / 2)
    for x in (2.4, 3.8):
        mb.box((x, 2.4, 1.0), (0.1, 0.1, 2.0), "timber")
    mb.cylinder((2.3, 2.4, 1.9), (3.9, 2.4, 1.9), 0.04, 0.04, "wood", segments=5)
    for i, c in enumerate(("hide", "hide_dark", "fur")):
        mb.box((2.7 + i * 0.4, 2.4, 1.45), (0.3, 0.05, 0.85), c)
    mb.sphere((-3.4, 0.2, 0), 0.7, "bark_dark", segments=6, rings=4, scale=(1, 1.2, 0.5))
    sign(mb, rig, "hide")


def weaver(mb, rig):
    shop(mb, rig, 2, 1)
    # The loom under a lean-to.
    lx, ly = 2.3, 0.6
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.box((lx + sx * 0.7, ly + sy * 0.8, 1.0), (0.1, 0.1, 2.0), "timber")
    game.sloped_slab(mb, lx - 1.0, lx + 1.0, ly - 1.2, ly + 1.1, 2.0, 2.5, 0.08, "var_roof_dark")
    for sy in (-1, 1):
        mb.box((lx, ly + sy * 0.55, 0.75), (0.08, 0.08, 1.5), "wood")
        mb.box((lx, ly + sy * 0.55, 1.5), (1.1, 0.07, 0.07), "wood")
    mb.cylinder((lx - 0.5, ly - 0.55, 0.9), (lx + 0.5, ly - 0.55, 0.9), 0.1, 0.1, "cloth_blue", segments=8)
    mb.cylinder((lx - 0.5, ly + 0.55, 1.2), (lx + 0.5, ly + 0.55, 1.2), 0.07, 0.07, "wood_light", segments=8)
    P.prism_yz(mb, [(ly - 0.55, 0.95), (ly + 0.55, 1.2), (ly + 0.55, 1.23), (ly - 0.55, 0.98)], lx - 0.45, lx + 0.45, "cloth_white")
    # Dye vats and cloth drying on lines.
    vat(mb, -3.0, -2.5, "cloth_blue")
    vat(mb, -1.8, -2.6, "cloth_red")
    vat(mb, -2.4, -1.6, "flowers_y", r=0.45)
    for x in (0.6, 3.6):
        mb.box((x, -2.6, 1.0), (0.09, 0.09, 2.0), "timber")
    mb.cylinder((0.5, -2.6, 1.9), (3.7, -2.6, 1.9), 0.025, 0.025, "rope", segments=4)
    for i, c in enumerate(("cloth_red", "cloth_blue", "flowers_y", "cloth_green", "cloth_white")):
        mb.box((0.95 + i * 0.6, -2.6, 1.42), (0.5, 0.04, 0.95), c)
    for i, c in enumerate(("cloth_green", "cloth_red", "cloth_white")):
        mb.cylinder((1.0 + i * 0.4, -1.4, 0.16), (1.0 + i * 0.4, -0.7, 0.16), 0.15, 0.15, c, segments=8)
    sign(mb, rig, "cloth_blue", x=OX - 1.4)


def tailor(mb, rig):
    shop(mb, rig, 3, 0, seed=3)
    for i, (x, c) in enumerate(((-3.0, "cloth_blue"), (-2.0, "cloth_red"), (2.6, "cloth_green"))):
        y = -2.3 if i < 2 else -2.0
        mb.cylinder((x, y, 0), (x, y, 0.06), 0.25, 0.25, "wood", segments=8)
        mb.box((x, y, 0.6), (0.06, 0.06, 1.2), "wood")
        torso = mb.prism([(x - 0.22, y - 0.14), (x + 0.22, y - 0.14), (x + 0.22, y + 0.14), (x - 0.22, y + 0.14)], 0.75, 1.5, c)
        for v in torso:
            if v.co.z < 1.0:
                v.co.x = x + (v.co.x - x) * 1.5
                v.co.y = y + (v.co.y - y) * 1.4
        mb.sphere((x, y, 1.62), 0.11, "wood_light", segments=6, rings=4)
        mb.box((x, y, 1.42), (0.62, 0.14, 0.12), c)
    mb.box((0.6, -2.4, 0.78), (1.7, 0.8, 0.07), "wood")
    for s in (-0.7, 0.7):
        mb.box((0.6 + s, -2.4, 0.38), (0.08, 0.7, 0.76), "timber")
    for i, c in enumerate(("cloth_red", "cloth_white", "cloth_blue", "flowers_y")):
        mb.cylinder((0.0 + i * 0.4, -2.7, 0.92), (0.0 + i * 0.4, -2.1, 0.92), 0.1, 0.1, c, segments=8)
    for i in range(3):
        x0 = 1.9 + i * 0.6
        game.sloped_slab(mb, x0, x0 + 0.61, -1.9, FRONT, 2.2, 2.6, 0.05, "stripe_b" if i % 2 else "cloth_blue")
    sign(mb, rig, "cloth_red", x=OX - 1.8, z=4.6)


def cobbler(mb, rig):
    shop(mb, rig, 2, 0, seed=5)
    # The great boot on a post.
    px, py = 3.0, -2.4
    mb.box((px, py, 1.3), (0.14, 0.14, 2.6), "timber")
    mb.box((px, py, 2.9), (0.5, 0.5, 0.9), "hide_dark")
    mb.box((px, py - 0.35, 2.6), (0.5, 0.8, 0.34), "hide_dark")
    mb.box((px, py - 0.3, 2.42), (0.56, 1.1, 0.08), "charcoal")
    mb.box((px, py, 3.36), (0.56, 0.56, 0.08), "hide")
    # A workbench with lasts and shoes, a rack of boots, rolls of leather.
    mb.box((-2.4, -2.3, 0.75), (1.8, 0.7, 0.08), "wood")
    for s in (-0.8, 0.8):
        mb.box((-2.4 + s, -2.3, 0.37), (0.08, 0.6, 0.74), "timber")
    for i in range(4):
        x = -3.1 + i * 0.45
        mb.box((x, -2.3, 0.87), (0.14, 0.34, 0.14), "hide" if i % 2 else "hide_dark")
        mb.box((x, -2.15, 0.98), (0.14, 0.12, 0.22), "hide" if i % 2 else "hide_dark")
    for r in range(2):
        mb.box((0.6, -1.3, 0.5 + r * 0.6), (1.4, 0.4, 0.05), "wood")
        for i in range(4):
            mb.box((0.1 + i * 0.35, -1.3, 0.6 + r * 0.6), (0.14, 0.3, 0.16), ("hide", "charcoal", "hide_dark", "band")[(i + r) % 4])
    for s in (-0.7, 0.7):
        mb.box((0.6 + s, -1.3, 0.6), (0.07, 0.4, 1.2), "timber")
    for i in range(3):
        mb.cylinder((1.4 + i * 0.35, -2.9, 0.16), (1.4 + i * 0.35, -2.2, 0.16), 0.15, 0.15, "hide" if i % 2 else "hide_dark", segments=8)
    sign(mb, rig, "hide_dark", x=OX - 1.8)


def bow(mb, x, y, z0, z1, lean=0.0, mat="wood"):
    pts = [(x + 0.22 * math.sin(math.pi * k / 6) + lean * k / 6, y, z0 + (z1 - z0) * k / 6) for k in range(7)]
    for a, b in zip(pts, pts[1:]):
        mb.cylinder(a, b, 0.025, 0.025, mat, segments=4)
    mb.cylinder(pts[0], pts[-1], 0.008, 0.008, "bone", segments=3)


def bowyer(mb, rig):
    shop(mb, rig, 2, 1, seed=7)
    mb.box((-2.6, -2.2, 0.9), (1.8, 0.1, 0.1), "timber")
    mb.box((-2.6, -2.2, 0.25), (1.8, 0.3, 0.08), "timber")
    for s in (-0.85, 0.85):
        mb.box((-2.6 + s, -2.2, 0.55), (0.09, 0.09, 1.1), "timber")
    for i in range(5):
        bow(mb, -3.3 + i * 0.35, -2.3, 0.3, 1.9, mat="wood" if i % 2 else "wood_light")
    for x, y in ((3.2, -0.6), (3.4, 1.2)):
        for s in (-0.3, 0.3):
            P.beam(mb, (x + 0.3, y + s, 0), (x, y, 1.5), 0.05, "timber")
        mb.cylinder((x, y, 1.1), (x - 0.18, y, 1.16), 0.55, 0.55, "hay", segments=10)
        mb.cylinder((x - 0.18, y, 1.16), (x - 0.21, y, 1.17), 0.36, 0.36, "stripe_b", segments=10)
        mb.cylinder((x - 0.21, y, 1.17), (x - 0.24, y, 1.18), 0.16, 0.16, "stripe_a", segments=8)
    mb.cylinder((1.0, -2.6, 0), (1.0, -2.6, 0.7), 0.26, 0.3, "wood", segments=8)
    for i in range(7):
        a = TAU * i / 7
        mb.cylinder((1.0 + 0.1 * math.cos(a), -2.6 + 0.1 * math.sin(a), 0.3), (1.0 + 0.18 * math.cos(a), -2.6 + 0.18 * math.sin(a), 1.15), 0.012,
                    0.012, "wood_light", segments=3)
        mb.box((1.0 + 0.18 * math.cos(a), -2.6 + 0.18 * math.sin(a), 1.1), (0.06, 0.01, 0.12), "white", rotation_z=a)
    for r in range(3):
        for i in range(4 - r):
            mb.cylinder((1.8 + i * 0.14 + r * 0.07, -1.2, 0.07 + r * 0.12), (1.8 + i * 0.14 + r * 0.07, -3.0, 0.07 + r * 0.12), 0.06, 0.06,
                        "wood_light", segments=5)
    sign(mb, rig, "wood_light", x=OX + 1.7, z=3.6)


def armory(mb, rig):
    shop(mb, rig, 3, 1, seed=9)
    # A rack of spears and halberds.
    for s in (-0.9, 0.9):
        mb.box((-2.6 + s, -2.3, 0.75), (0.09, 0.09, 1.5), "timber")
    mb.box((-2.6, -2.3, 1.35), (1.9, 0.09, 0.09), "timber")
    mb.box((-2.6, -2.3, 0.2), (1.9, 0.3, 0.08), "timber")
    for i in range(6):
        x = -3.35 + i * 0.3
        mb.cylinder((x, -2.35, 0.22), (x, -2.42, 2.2), 0.03, 0.03, "wood", segments=4)
        if i % 2:
            mb.cylinder((x, -2.42, 2.2), (x, -2.43, 2.55), 0.06, 0.0, "iron", segments=4)
        else:
            P.prism_xz(mb, [(x - 0.02, 2.0), (x + 0.22, 2.05), (x + 0.22, 2.35), (x - 0.02, 2.4)], -2.45, -2.4, "iron")
            mb.cylinder((x, -2.42, 2.2), (x, -2.43, 2.6), 0.04, 0.0, "iron", segments=4)
    # An armor stand, shields on the wall, a chest of swords, a grindstone.
    ax, ay = 2.6, -2.2
    mb.box((ax, ay, 0.8), (0.08, 0.08, 1.6), "timber")
    mb.box((ax, ay, 0.04), (0.6, 0.6, 0.08), "timber")
    torso = mb.prism([(ax - 0.26, ay - 0.16), (ax + 0.26, ay - 0.16), (ax + 0.26, ay + 0.16), (ax - 0.26, ay + 0.16)], 0.95, 1.55, "iron")
    for v in torso:
        if v.co.z < 1.2:
            v.co.x = ax + (v.co.x - ax) * 0.8
    mb.box((ax, ay, 1.5), (0.8, 0.2, 0.14), "iron")
    mb.sphere((ax, ay, 1.75), 0.16, "iron", segments=6, rings=4, scale=(1, 1, 1.15))
    mb.box((ax, ay - 0.15, 1.75), (0.2, 0.04, 0.05), "charcoal")
    for i, c in enumerate(("banner", "band", "banner2")):
        sx = 1.0 + i * 0.75
        mb.cylinder((sx, FRONT - 0.2, 1.5), (sx, FRONT - 0.27, 1.5), 0.32, 0.32, c, segments=8)
        mb.cylinder((sx, FRONT - 0.27, 1.5), (sx, FRONT - 0.31, 1.5), 0.1, 0.1, "iron", segments=6)
    mb.box((0.6, -2.6, 0.25), (1.0, 0.55, 0.5), "wood")
    for i in range(4):
        mb.box((0.25 + i * 0.22, -2.6, 0.75), (0.04, 0.03, 0.8), "iron")
        mb.box((0.25 + i * 0.22, -2.6, 0.42), (0.18, 0.04, 0.04), "brass")
    gx, gy = 3.4, -0.4
    for s in (-1, 1):
        P.beam(mb, (gx + s * 0.25, gy - 0.3, 0), (gx + s * 0.25, gy, 0.75), 0.07, "timber")
        P.beam(mb, (gx + s * 0.25, gy + 0.3, 0), (gx + s * 0.25, gy, 0.75), 0.07, "timber")
    mb.cylinder((gx - 0.12, gy, 0.75), (gx + 0.12, gy, 0.75), 0.42, 0.42, "wall_dark", segments=12)
    P.flag(mb, rig, 3.6, 2.6, 0, pole=4.2, length=1.2, mat="banner")


def smokehouse(mb, rig):
    rnd = random.Random(11)
    x, y, w, h = -1.0, 1.0, 3.0, 4.6
    P.stone_block(mb, x, y, 0, w, w, h, rnd, density=0.35)
    with P.face(mb, x, y, w, w, "front"):
        P.plank_door(mb, 0, 0.1, w=1.0, h=1.9)
        mb.box((0, -0.05, 3.2), (1.6, 0.1, 0.5), "charcoal")
        for k in range(4):
            mb.box((0, -0.12, 3.02 + k * 0.13), (1.7, 0.08, 0.05), "timber")
    # A louvered top that lets the smoke out, under a steep roof.
    mb.box((x, y, h + 0.5), (w - 0.5, w - 0.5, 1.0), "charcoal")
    for side in P.SIDES:
        with P.face(mb, x, y, w - 0.4, w - 0.4, side) as L:
            for k in range(5):
                mb.box((0, -0.02, h + 0.12 + k * 0.19), (L, 0.1, 0.07), "timber")
            for sx in (-L / 2, L / 2):
                mb.box((sx, 0, h + 0.5), (0.12, 0.12, 1.0), "timber")
    P.pyramid_roof(mb, x, y, h + 1.0, w - 0.4, w - 0.4, 2.0, ("shingle", "shingle_dark"), rows=4, overhang=0.4, finial="iron")
    # The fire box against the side, racks of fish and hams, firewood, a salting table.
    mb.box((x + w / 2 + 0.6, y, 0.5), (1.2, 1.4, 1.0), "brick")
    mb.box((x + w / 2 + 1.22, y, 0.4), (0.06, 0.6, 0.5), "ember")
    mb.box((x + w / 2 + 0.6, y, 1.04), (1.3, 1.5, 0.08), "stone_dark")
    for k, (ry, items, c) in enumerate(((-2.2, 6, "fish"), (-3.0, 4, "tile_red_dark"))):
        for sx in (-3.4, -1.0):
            mb.box((sx, ry, 0.9), (0.09, 0.09, 1.8), "timber")
        mb.cylinder((-3.5, ry, 1.75), (-0.9, ry, 1.75), 0.035, 0.035, "wood", segments=5)
        for i in range(items):
            xx = -3.2 + i * 2.0 / (items - 1)
            if k == 0:
                mb.box((xx, ry, 1.45), (0.1, 0.04, 0.5), c)
            else:
                mb.sphere((xx, ry, 1.4), 0.17, c, segments=6, rings=4, scale=(0.8, 0.6, 1.5))
                mb.box((xx, ry, 1.66), (0.02, 0.02, 0.16), "rope")
    game.log_pile(mb, 2.6, 2.4, length=1.6, rows=3)
    mb.box((2.2, -2.2, 0.75), (1.6, 0.8, 0.08), "wood")
    for s in (-0.7, 0.7):
        mb.box((2.2 + s, -2.2, 0.37), (0.08, 0.7, 0.74), "timber")
    for i in range(3):
        mb.box((1.8 + i * 0.4, -2.2, 0.83), (0.12, 0.5, 0.07), "fish")
    mb.box((2.9, -2.2, 0.9), (0.3, 0.3, 0.22), "white")
    game.barrel(mb, 3.4, -1.0, h=0.8, r=0.3)
    game.barrel(mb, 3.3, -0.2, h=0.8, r=0.3)


def charcoal_burner(mb, rig):
    rnd = random.Random(13)
    # The clamp: a mound of wood under turf, smoking through its vents.
    x, y = -0.8, 0.9
    mb.sphere((x, y, 0), 2.6, "earth", segments=12, rings=6, scale=(1, 1, 0.78))
    for _ in range(14):
        a, t = rnd.uniform(0, TAU), rnd.uniform(0.25, 0.9)
        rr = 2.6 * t
        mb.sphere((x + rr * math.cos(a), y + rr * math.sin(a), 2.6 * 0.78 * math.sqrt(1 - t * t) - 0.05), rnd.uniform(0.3, 0.55),
                  rnd.choice(("grass_dark", "earth_dark", "charcoal")), segments=5, rings=3, scale=(1, 1, 0.35))
    mb.cylinder((x, y, 1.9), (x, y, 2.15), 0.35, 0.25, "charcoal", segments=8)
    mb.cylinder((x, y, 2.1), (x, y, 2.2), 0.18, 0.18, "ember", segments=6)
    for i in range(7):
        a = TAU * i / 7 + 0.3
        mb.box((x + 2.5 * math.cos(a), y + 2.5 * math.sin(a), 0.25), (0.3, 0.3, 0.22), "ember" if i % 3 == 0 else "charcoal", rotation_z=a)
    for i in range(10):   # Logs showing where the turf is not yet laid.
        a = -1.9 + i * 0.07
        mb.cylinder((x + 2.2 * math.cos(a), y + 2.2 * math.sin(a), 0), (x + 1.3 * math.cos(a), y + 1.3 * math.sin(a), 1.5), 0.09, 0.08, "log", segments=5)
    # The burner's hut of poles and turf, wood stacks, baskets and sacks of charcoal, a rake and a ladder.
    hx, hy = 3.0, 1.8
    for i in range(9):
        a = TAU * i / 9
        if abs((a + math.pi / 2 + math.pi) % TAU - math.pi) < 0.4:
            continue
        mb.cylinder((hx + 1.2 * math.cos(a), hy + 1.2 * math.sin(a), 0), (hx, hy, 2.4), 0.07, 0.05, "log", segments=5)
    mb.cylinder((hx, hy, 0), (hx, hy, 2.1), 1.15, 0.08, "grass_dark", segments=9)
    mb.box((hx, hy - 1.0, 0.6), (0.7, 0.5, 1.2), "charcoal")
    game.log_pile(mb, -3.4, -2.6, length=1.6, rows=3)
    game.log_pile(mb, -1.4, -2.9, length=1.6, rows=2)
    for i, (bx, by) in enumerate(((1.4, -2.4), (2.1, -2.7), (2.7, -2.2))):
        mb.cylinder((bx, by, 0), (bx, by, 0.5), 0.3, 0.36, "thatch_dark", segments=8)
        mb.sphere((bx, by, 0.5), 0.3, "charcoal", segments=6, rings=4, scale=(1, 1, 0.5))
    for bx, by in ((3.6, -1.2), (3.7, -0.5)):
        mb.sphere((bx, by, 0.28), 0.3, "charcoal", segments=6, rings=4, scale=(1, 0.8, 1.0))
    P.beam(mb, (0.9, -1.6, 0), (0.4, -0.9, 1.9), 0.035, "wood")
    mb.box((0.38, -0.88, 1.95), (0.5, 0.06, 0.06), "iron")
    for s in (-0.2, 0.2):
        P.beam(mb, (x - 2.9 + s, y - 0.4, 0), (x - 1.5 + s, y, 1.7), 0.05, "timber")
    for k in range(5):
        t = (k + 0.5) / 5
        mb.box((x - 2.9 + 1.4 * t, y - 0.4 + 0.4 * t, 1.7 * t), (0.45, 0.05, 0.05), "wood", rotation_z=0.3)


def tavern(mb, rig):
    shop(mb, rig, 3, 2, seed=15)
    with mb.placed((OX - 2.3, FRONT - 0.2, 0), -math.pi / 2):
        P.hanging_sign(mb, rig, 0, 0, 3.7, arm=1.1, board=(0.8, 0.7), emblem="gold")
    P.table(mb, -1.6, -2.4, w=1.5)
    P.table(mb, 2.6, -1.6, w=1.4)
    for x, y in ((0.6, -2.6), (1.2, -2.8), (0.9, -2.2)):
        game.barrel(mb, x, y, h=0.85, r=0.32)
    mb.cylinder((2.4, 1.2, 0.36), (3.2, 1.2, 0.36), 0.36, 0.36, "wood", segments=10)
    for x in (2.5, 3.1):
        mb.box((x, 1.2, 0.1), (0.1, 0.6, 0.2), "timber")
    mb.box((-3.4, -1.0, 1.1), (0.1, 0.1, 2.2), "iron")
    mb.box((-3.4, -1.0, 2.35), (0.24, 0.24, 0.3), "glow")
    game.log_pile(mb, 2.8, 2.6, length=1.2, rows=2)


def healer(mb, rig):
    shop(mb, rig, 1, 2, seed=17)
    for i in range(3):
        for j in range(2):
            bx, by = -3.2 + i * 1.3, -2.9 + j * 0.9
            mb.box((bx, by, 0.1), (1.1, 0.7, 0.2), "wall_dark")
            mb.box((bx, by, 0.17), (0.95, 0.55, 0.1), "soil")
            for k in range(3):
                mb.sphere((bx - 0.3 + k * 0.3, by, 0.3), 0.13, ("leaves", "flowers", "leaf_light", "flowers_y", "magic")[(i + j * 2 + k) % 5],
                          segments=5, rings=3)
    mb.box((1.6, -2.4, 0.75), (1.4, 0.7, 0.07), "wood")
    for s in (-0.6, 0.6):
        mb.box((1.6 + s, -2.4, 0.37), (0.07, 0.6, 0.74), "timber")
    mb.cylinder((1.3, -2.4, 0.79), (1.3, -2.4, 0.95), 0.1, 0.14, "stone", segments=7)
    mb.cylinder((1.34, -2.4, 0.9), (1.5, -2.35, 1.12), 0.03, 0.03, "wood", segments=4)
    for i, c in enumerate(("magic", "berries", "leaves")):
        mb.cylinder((1.75 + i * 0.2, -2.4, 0.79), (1.75 + i * 0.2, -2.4, 0.97), 0.06, 0.05, c, segments=6)
    for x in (2.5, 3.5):
        mb.box((x, 0.6, 0.8), (0.08, 0.08, 1.6), "timber")
    mb.cylinder((2.4, 0.6, 1.5), (3.6, 0.6, 1.5), 0.025, 0.025, "wood", segments=4)
    for i in range(5):
        mb.cylinder((2.6 + i * 0.2, 0.6, 1.48), (2.6 + i * 0.2, 0.6, 1.1), 0.02, 0.09, "leaves" if i % 2 else "hay", segments=5)
    mb.cylinder((3.3, -2.6, 0), (3.3, -2.6, 3.0), 0.05, 0.04, "timber", segments=6)
    mb.box((3.0, -2.6, 2.7), (0.6, 0.04, 0.5), "white")
    mb.box((3.0, -2.63, 2.7), (0.36, 0.03, 0.1), "leaves")
    mb.box((3.0, -2.63, 2.7), (0.1, 0.03, 0.36), "leaves")


def explorer_lodge(mb, rig):
    shop(mb, rig, 2, 1, seed=19)
    mb.box((2.6, -2.4, 1.1), (0.12, 0.12, 2.2), "timber")
    for i, (z, a, c) in enumerate(((1.95, 0.3, "wood_light"), (1.65, -2.6, "plank"), (1.35, 1.2, "wood_light"))):
        with mb.placed((2.6, -2.4, 0), a):
            P.prism_xz(mb, [(0.05, z - 0.1), (0.7, z - 0.1), (0.9, z), (0.7, z + 0.1), (0.05, z + 0.1)], -0.09, -0.05, c)
    mb.box((-2.6, -2.4, 0.74), (1.4, 0.9, 0.07), "wood")
    for sx in (-0.6, 0.6):
        for sy in (-0.35, 0.35):
            mb.box((-2.6 + sx, -2.4 + sy, 0.36), (0.07, 0.07, 0.72), "timber")
    mb.box((-2.6, -2.4, 0.785), (1.1, 0.7, 0.02), "cloth_white")
    mb.box((-2.75, -2.3, 0.8), (0.4, 0.25, 0.01), "leaves")
    mb.box((-2.3, -2.55, 0.8), (0.3, 0.2, 0.01), "water")
    mb.cylinder((-2.1, -2.2, 0.8), (-2.1, -2.2, 0.88), 0.07, 0.07, "brass", segments=8)
    for x, y, s in ((0.4, -2.6, 0.3), (0.9, -2.3, 0.26), (0.6, -2.0, 0.24)):
        mb.sphere((x, y, s * 0.8), s, "hide" if s > 0.25 else "hide_dark", segments=6, rings=4, scale=(1, 0.8, 1.1))
        mb.cylinder((x - s * 0.9, y, s * 1.5), (x + s * 0.9, y, s * 1.5), s * 0.3, s * 0.3, "cloth_green", segments=6)
    tx, ty = 1.6, -3.0
    for i in range(3):
        a = TAU * i / 3 + 0.4
        P.beam(mb, (tx + 0.4 * math.cos(a), ty + 0.4 * math.sin(a), 0), (tx, ty, 1.3), 0.03, "timber")
    P.beam(mb, (tx - 0.3, ty + 0.1, 1.25), (tx + 0.45, ty - 0.15, 1.6), 0.07, "brass")
    game.crate(mb, 3.3, 0.6, s=0.6)
    game.crate(mb, 3.2, 1.3, s=0.5)
    P.flag(mb, rig, -3.4, -0.6, 0, pole=4.2, length=1.4, mat="cloth_green", stripe="banner2")


def firewood_shed(mb, rig):
    w, d = 5.2, 2.4
    for sx in (-1, 0, 1):
        mb.box((sx * w / 2, 1.2 + d / 2, 1.4), (0.16, 0.16, 2.8), "timber")
        mb.box((sx * w / 2, 1.2 - d / 2, 1.1), (0.16, 0.16, 2.2), "timber")
    game.sloped_slab(mb, -w / 2 - 0.4, w / 2 + 0.4, 1.2 - d / 2 - 0.5, 1.2 + d / 2 + 0.3, 2.1, 2.9, 0.1, "shingle")
    game.sloped_slab(mb, -w / 2 - 0.4, w / 2 + 0.4, 1.2 - d / 2 - 0.5, 1.2 - d / 2 + 0.4, 2.15, 2.4, 0.1, "shingle_dark")
    mb.box((0, 1.2 + d / 2, 1.3), (w, 0.06, 2.6), "plank")
    for sx in (-1, 1):
        mb.box((sx * w / 2, 1.2, 1.1), (0.06, d, 2.2), "plank")
    # The wall of split firewood: rows of billets seen end on.
    for half in (-1, 1):
        for r in range(7):
            for i in range(9):
                x = half * (0.2 + i * 0.26 + (0.13 if r % 2 else 0))
                if abs(x) > w / 2 - 0.2:
                    continue
                mb.box((x, 1.2 - 0.2, 0.14 + r * 0.24), (0.22, 1.5, 0.2), "log_end" if (i + r) % 3 else "log")
    # The chopping block, split billets, a sawbuck with a log.
    mb.cylinder((-1.4, -1.6, 0), (-1.4, -1.6, 0.5), 0.34, 0.3, "log", segments=8)
    mb.cylinder((-1.4, -1.6, 0.5), (-1.4, -1.6, 0.52), 0.26, 0.26, "log_end", segments=8)
    mb.box((-1.4, -1.6, 0.9), (0.05, 0.12, 0.7), "wood")
    mb.box((-1.4, -1.6, 0.64), (0.24, 0.05, 0.16), "iron")
    for i in range(8):
        a = i * 0.9
        mb.box((-1.4 + 0.9 * math.cos(a), -1.6 + 0.7 * math.sin(a), 0.07), (0.16, 0.5, 0.12), "log_end" if i % 2 else "log", rotation_z=a)
    for sx in (-0.5, 0.5):
        P.beam(mb, (1.6 + sx, -1.9, 0), (1.6 + sx, -1.3, 0.9), 0.06, "timber")
        P.beam(mb, (1.6 + sx, -1.3, 0), (1.6 + sx, -1.9, 0.9), 0.06, "timber")
    mb.cylinder((0.8, -1.6, 0.7), (2.5, -1.6, 0.7), 0.16, 0.15, "log", segments=7)
    mb.box((1.9, -1.6, 0.95), (0.03, 0.6, 0.3), "iron")
    mb.box((1.9, -1.9, 1.05), (0.05, 0.08, 0.3), "wood")


def orchard_house(mb, rig):
    shop(mb, rig, 1, 0, seed=21)
    rnd = random.Random(23)
    for tx, ty in ((2.9, -1.6), (3.1, 1.8), (-3.3, -2.4)):
        mb.cylinder((tx, ty, 0), (tx + 0.1, ty, 1.5), 0.16, 0.11, "bark", segments=6)
        for i in range(4):
            a = TAU * i / 4 + 0.5
            mb.sphere((tx + 0.1 + 0.6 * math.cos(a), ty + 0.6 * math.sin(a), 2.0 + 0.2 * (i % 2)), 0.75, "leaf" if i % 2 else "leaf_dark",
                      segments=6, rings=4, scale=(1, 1, 0.8))
        mb.sphere((tx + 0.1, ty, 2.6), 0.8, "leaf_light", segments=6, rings=4, scale=(1, 1, 0.8))
        for _ in range(9):
            a, z = rnd.uniform(0, TAU), rnd.uniform(1.7, 2.9)
            rr = rnd.uniform(0.75, 1.05)
            mb.sphere((tx + 0.1 + rr * math.cos(a), ty + rr * math.sin(a), z), 0.09, "berries", segments=5, rings=3)
    for s in (-0.22, 0.22):
        P.beam(mb, (2.2 + s, -2.2, 0), (2.6 + s, -1.8, 2.2), 0.04, "wood_light")
    for k in range(6):
        t = (k + 0.5) / 6
        mb.box((2.2 + 0.4 * t, -2.2 + 0.4 * t, 2.2 * t), (0.45, 0.04, 0.04), "wood_light")
    for x, y in ((0.6, -2.6), (1.2, -2.9), (-0.2, -2.9)):
        mb.cylinder((x, y, 0), (x, y, 0.34), 0.24, 0.3, "thatch_dark", segments=8)
        mb.sphere((x, y, 0.35), 0.24, "berries", segments=6, rings=4, scale=(1, 1, 0.5))
    # A small cider press and a cask.
    px, py = -1.2, -2.6
    mb.cylinder((px, py, 0.2), (px, py, 0.7), 0.5, 0.52, "wood", segments=10)
    mb.box((px, py, 0.1), (1.2, 1.0, 0.2), "timber")
    for s in (-1, 1):
        mb.box((px + s * 0.55, py, 0.8), (0.12, 0.12, 1.6), "timber")
    mb.box((px, py, 1.55), (1.3, 0.16, 0.16), "timber")
    mb.cylinder((px, py, 0.7), (px, py, 1.7), 0.05, 0.05, "iron", segments=6)
    mb.box((px, py, 1.75), (0.8, 0.06, 0.06), "wood")
    mb.cylinder((px, py - 0.75, 0), (px, py - 0.75, 0.28), 0.2, 0.24, "wood", segments=7)


def make(name, fn, colors=None):
    def build():
        mb = P.begin()
        rig = P.Rig()
        fn(mb, rig)
        P.finish(mb, name, colors or P.BASE, rig)
    return build


MODELS = {
    "bld_workshop_tannery": make("bld_workshop_tannery", tannery),
    "bld_workshop_weaver": make("bld_workshop_weaver", weaver),
    "bld_workshop_tailor": make("bld_workshop_tailor", tailor, P.palette(var_roof=0x5A6470, var_roof_dark=0x46505A)),
    "bld_workshop_cobbler": make("bld_workshop_cobbler", cobbler, P.palette(var_roof=0x7A5A3C, var_roof_dark=0x614530)),
    "bld_workshop_bowyer": make("bld_workshop_bowyer", bowyer, P.palette(var_roof=0xC9A55A, var_roof_dark=0xA8863F)),
    "bld_workshop_armory": make("bld_workshop_armory", armory, P.palette(var_roof=0x5A6470, var_roof_dark=0x46505A)),
    "bld_smokehouse_tower": make("bld_smokehouse_tower", smokehouse),
    "bld_charcoal_burner": make("bld_charcoal_burner", charcoal_burner),
    "bld_tavern_village": make("bld_tavern_village", tavern),
    "bld_tavern_village_blue": make("bld_tavern_village_blue", tavern, P.palette(var_roof=0x3F5F9E, var_roof_dark=0x324B80)),
    "bld_healer_hut": make("bld_healer_hut", healer, P.palette(var_roof=0xC9A55A, var_roof_dark=0xA8863F)),
    "bld_explorer_lodge": make("bld_explorer_lodge", explorer_lodge, P.palette(var_roof=0x7A5A3C, var_roof_dark=0x614530)),
    "bld_firewood_shed": make("bld_firewood_shed", firewood_shed),
    "bld_orchard_house": make("bld_orchard_house", orchard_house, P.palette(var_roof=0xC9A55A, var_roof_dark=0xA8863F)),
}
