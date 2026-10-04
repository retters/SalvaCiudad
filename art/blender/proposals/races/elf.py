"""Elves: round houses of white stone and living wood, roofs like leaves and
bells of verdigris, branches for posts, lanterns hanging everywhere."""

import math

import rparts as p
from rparts import TAU, solid

ROOF = ("e_roof", "e_roof_dark")


def on_round(mb, cx, cy, r, a, z=0.0):
    """The face frame on a round wall at angle a (-pi/2 is the front)."""
    return mb.placed((cx + r * 0.955 * math.cos(a), cy + r * 0.955 * math.sin(a), z), a + math.pi / 2)


def bell_roof(mb, x, y, z, r, h, mats=ROOF, seg=10, curl=True):
    """A roof like a closed flower: wide eave, swept in, a curled tip."""
    prof = [(r + 0.4, 0), (r * 0.92, h * 0.16), (r * 0.62, h * 0.4), (r * 0.36, h * 0.64), (r * 0.16, h * 0.86), (0.05, h * 1.08)]
    p.lathe(mb, x, y, z, prof, mats, seg)
    mb.cylinder((x, y, z - 0.06), (x, y, z + 0.02), r + 0.42, r + 0.42, "e_wood", segments=seg)
    if curl:
        p.arc(mb, [(x, y, z + h * 1.02), (x + 0.05, y, z + h * 1.22), (x + 0.22, y, z + h * 1.32), (x + 0.36, y, z + h * 1.24)], 0.05, "gold", 0.5)
    return z + h * 1.08


def leaf_roof(mb, cx, cy, z, w, d, rise, mats=ROOF, n=8, over=0.45, lift=0.7, axis="x", fill="e_white"):
    """A roof like a leaf laid over the house: its ridge and its eaves rise
    toward the two pointed ends."""
    if axis == "y":
        with mb.placed((cx, cy, 0), math.pi / 2):
            return leaf_roof(mb, 0, 0, z, d, w, rise, mats, n, over, lift, "x", fill)
    L = w / 2 + 0.9
    half = d / 2 + over

    def at(u):
        return L * u, half * (1 - 0.26 * u * u), z - 0.2 + lift * 0.5 * u * u, z + rise + lift * abs(u) ** 2.2

    ridge = []
    for i in range(n):
        u0, u1 = -1 + 2 * i / n, -1 + 2 * (i + 1) / n
        (x0, h0, e0, r0), (x1, h1, e1, r1) = at(u0), at(u1)
        for side in (-1, 1):
            solid(mb, [(cx + x0, cy + side * h0, e0), (cx + x1, cy + side * h1, e1), (cx + x1, cy, r1), (cx + x0, cy, r0)], (0, 0, 0.1), mats[i % len(mats)])
        ridge.append((cx + x0, cy, r0 + 0.1))
    ridge.append((cx + L, cy, at(1)[3] + 0.1))
    p.arc(mb, ridge, 0.07, "e_wood")
    for s in (-1, 1):                                                           # Curled tips.
        p.arc(mb, [(cx + s * L, cy, at(1)[3] + 0.1), (cx + s * (L + 0.3), cy, at(1)[3] + 0.4), (cx + s * (L + 0.2), cy, at(1)[3] + 0.7)], 0.06, "gold", 0.4)
    if fill:
        u = (w / 2) / L
        for s in (-1, 1):
            p.prism_yz(mb, [(cy - d / 2, z - 0.02), (cy + d / 2, z - 0.02), (cy, at(u)[3])], cx + s * w / 2 - 0.08, cx + s * w / 2 + 0.08, fill)
    return z + rise + lift


def round_house(mb, x, y, r, h, ribs=8, seg=10, wall="e_white"):
    mb.cylinder((x, y, 0), (x, y, h), r, r * 0.97, wall, segments=seg)
    mb.cylinder((x, y, 0), (x, y, 0.35), r + 0.14, r + 0.05, "e_white_dark", segments=seg)
    for k in range(ribs):                                                       # Living posts that lean into the wall.
        a = TAU * (k + 0.5) / ribs
        c, s = math.cos(a), math.sin(a)
        p.arc(mb, [(x + c * (r + 0.28), y + s * (r + 0.28), 0), (x + c * (r + 0.1), y + s * (r + 0.1), h * 0.5), (x + c * (r + 0.02), y + s * (r + 0.02), h)], 0.09, "e_wood", 0.7)


def door(mb, w=0.95, h=1.75, x=0.0, z=0.0):
    """A leaf-green door under two branches that meet (face frame)."""
    p.arch_door(mb, x, z, w, h, "e_white_dark", "e_door", None)
    mb.sphere((x + w * 0.3, -0.14, z + h * 0.45), 0.05, "gold", segments=5, rings=3)
    for s in (-1, 1):
        p.arc(mb, [(x + s * (w / 2 + 0.3), -0.12, z), (x + s * (w / 2 + 0.22), -0.14, z + h * 0.6), (x + s * (w * 0.3), -0.14, z + h + 0.12), (x - s * 0.1, -0.14, z + h + 0.34)], 0.07, "e_wood", 0.5)
    mb.sphere((x, -0.16, z + h + 0.34), 0.14, "leaf_light", segments=5, rings=3)


def window(mb, x=0.0, z=0.9, w=0.45, h=1.0):
    p.arch_door(mb, x, z, w, h, "e_wood", "window", None, 0.1)


def lamp_post(mb, rig, x, y, h=2.6, side=1, rot=0.0):
    """A bent branch with a lantern hanging from its tip."""
    with mb.placed((x, y, 0), rot):
        p.arc(mb, [(0, 0, 0), (0.04 * side, 0, h * 0.5), (0.2 * side, 0, h * 0.85), (0.55 * side, 0, h), (0.8 * side, 0, h * 0.95)], 0.07, "e_wood", 0.5)
        mb.sphere((0.4 * side, 0, h + 0.05), 0.15, "leaf_light", segments=5, rings=3)
        p.hang_lantern(mb, rig, 0.8 * side, 0, h * 0.95, 0.2, "drop", "window", "gold")


def flowers(mb, rnd, x0, x1, y0, y1, n):
    for _ in range(n):
        x, y = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
        mb.sphere((x, y, 0.08), 0.14, "leaf", segments=5, rings=3, scale=(1, 1, 0.6))
        mb.sphere((x + 0.03, y - 0.03, 0.17), 0.06, rnd.choice(("flower", "flower_w", "e_blue")), segments=4, rings=3)


def vines(mb, rnd, cx, cy, r, z0, z1, n, a0=0.0, a1=TAU):
    for _ in range(n):
        a = rnd.uniform(a0, a1)
        mb.sphere((cx + math.cos(a) * r, cy + math.sin(a) * r, rnd.uniform(z0, z1)), rnd.uniform(0.14, 0.24), rnd.choice(("leaf", "leaf_light", "leaf_dark")), segments=5, rings=3, scale=(1, 1, 0.8))


def basket(mb, x, y, z=0.0, fruit="flower"):
    mb.cylinder((x, y, z), (x, y, z + 0.28), 0.2, 0.26, "sisal", segments=7)
    for k in range(4):
        mb.sphere((x + 0.1 * math.cos(k * 1.7), y + 0.1 * math.sin(k * 1.7), z + 0.3), 0.09, fruit, segments=5, rings=3)


def house(level):
    def build():
        mb = p.begin()
        rig = p.Rig()
        rnd = p.random.Random(60 + level)
        F = -math.pi / 2
        if level == 1:
            round_house(mb, 0, 0.2, 1.55, 2.1, 7)
            with on_round(mb, 0, 0.2, 1.72, F):
                door(mb, 0.9, 1.65)
            with on_round(mb, 0, 0.2, 1.55, F + TAU * 0.3):
                window(mb, 0, 0.9, 0.4, 0.8)
            bell_roof(mb, 0, 0.2, 2.1, 1.55, 2.2)
            lamp_post(mb, rig, 1.6, -1.5, 2.3, -1)
            flowers(mb, rnd, -1.9, -0.8, -1.8, -1.3, 4)
        elif level == 2:
            round_house(mb, -0.6, 0.3, 2.0, 2.5, 8)
            round_house(mb, 1.75, 0.6, 1.2, 2.0, 5)
            with on_round(mb, -0.6, 0.3, 2.17, F):
                door(mb, 1.0, 1.8)
            for a in (F - TAU * 0.2, F + TAU * 0.2):
                with on_round(mb, -0.6, 0.3, 2.0, a):
                    window(mb)
            with on_round(mb, 1.75, 0.6, 1.2, F + 0.3):
                p.round_win(mb, 0, 1.25, 0.3, "e_wood", "window")
            bell_roof(mb, -0.6, 0.3, 2.5, 2.0, 2.9)
            bell_roof(mb, 1.75, 0.6, 2.0, 1.2, 1.8, curl=False)
            mb.sphere((1.75, 0.6, 4.05), 0.1, "gold", segments=6, rings=4)
            vines(mb, rnd, -0.6, 0.3, 2.05, 0.4, 2.3, 7, 0.2, 2.6)
            lamp_post(mb, rig, -2.6, -1.9, 2.7, 1)
            p.tree(mb, 2.5, -1.7, 2.6, 0.75)
            flowers(mb, rnd, 0.6, 2.0, -2.2, -1.2, 5)
        else:
            w, d, h = 5.6, 3.8, 2.7
            cx, cy = -0.9, 0.5
            mb.box((cx, cy, h / 2), (w, d, h), "e_white")
            mb.box((cx, cy, 0.2), (w + 0.24, d + 0.24, 0.4), "e_white_dark")
            for sx in range(5):                                                 # Branch posts along the walls.
                for sy in (-1, 1):
                    x = cx - w / 2 + w * sx / 4
                    p.arc(mb, [(x, cy + sy * (d / 2 + 0.25), 0), (x, cy + sy * (d / 2 + 0.08), h * 0.55), (x, cy + sy * (d / 2 + 0.02), h)], 0.1, "e_wood", 0.7)
            with p.face(mb, cx, cy, w, d, "front"):
                door(mb, 1.05, 1.9, -0.7)
                for x in (-2.1, 0.7, 2.0):
                    window(mb, x, 0.8, 0.5, 1.3)
            with p.face(mb, cx, cy, w, d, "left"):
                window(mb, 0, 0.8, 0.5, 1.3)
            leaf_roof(mb, cx, cy, h, w, d, 1.7, n=8)
            tx, ty, tr, th = 2.6, 1.2, 1.3, 5.0                                 # A slender tower with its balcony.
            round_house(mb, tx, ty, tr, th, 6, 8)
            mb.cylinder((tx, ty, 3.3), (tx, ty, 3.45), tr + 0.7, tr + 0.75, "e_wood", segments=10)
            p.ring(mb, tx, ty, 4.1, tr + 0.72, 0.07, "e_wood", 10)
            for k in range(10):
                a = TAU * k / 10
                p.beam(mb, (tx + math.cos(a) * (tr + 0.72), ty + math.sin(a) * (tr + 0.72), 3.45), (tx + math.cos(a) * (tr + 0.72), ty + math.sin(a) * (tr + 0.72), 4.1), 0.05, "e_wood")
            for a in (F, F + TAU / 3, F - TAU / 3):
                with on_round(mb, tx, ty, tr, a, 3.45):
                    window(mb, 0, 0.0, 0.5, 1.2)
            with on_round(mb, tx, ty, tr, F):
                window(mb, 0, 1.2, 0.4, 1.0)
            bell_roof(mb, tx, ty, th, tr, 2.6)
            for k, a in enumerate((F - 0.5, F + 1.2, F + 2.6)):
                p.hang_lantern(mb, rig, tx + math.cos(a) * (tr + 0.7), ty + math.sin(a) * (tr + 0.7), 3.3, 0.15, "drop", "window", "gold")
            vines(mb, rnd, tx, ty, tr + 0.05, 0.4, 3.0, 8, -1.0, 1.6)
            lamp_post(mb, rig, -3.4, -2.3, 2.8, 1)
            flowers(mb, rnd, -3.4, 2.5, -2.6, -1.8, 8)
        p.finish(mb, "race_elf_house_%d" % level, rig)
    return build


def center():
    """The moon hall: a great bell over a ring of white columns, 14 x 13 m."""
    mb = p.begin()
    rig = p.Rig()
    rnd = p.random.Random(67)
    cy = 0.8
    for r, z in ((5.6, 0.2), (5.2, 0.4), (4.8, 0.6)):
        mb.cylinder((0, cy, z - 0.2), (0, cy, z), r, r, "e_white_dark" if z < 0.5 else "e_white", segments=14)
    R = 4.3
    for k in range(12):                                                         # The colonnade.
        a = TAU * k / 12 + TAU / 24
        x, y = math.cos(a) * R, cy + math.sin(a) * R
        mb.cylinder((x, y, 0.6), (x, y, 0.85), 0.3, 0.24, "e_white_dark", segments=8)
        mb.cylinder((x, y, 0.85), (x, y, 4.2), 0.2, 0.16, "e_white", segments=8)
        p.arc(mb, [(x, y, 3.6), (x * 0.96, cy + (y - cy) * 0.96, 4.3), (x * 0.86, cy + (y - cy) * 0.86, 4.7)], 0.09, "e_wood", 0.8)
        if k % 2 == 0:
            p.hang_lantern(mb, rig, x * 1.06, cy + (y - cy) * 1.06, 4.3, 0.3, "drop", "window", "gold", 1.3)
    mb.cylinder((0, cy, 4.5), (0, cy, 4.8), R + 0.5, R + 0.5, "e_white", segments=14)
    mb.cylinder((0, cy, 4.42), (0, cy, 4.52), R + 0.6, R + 0.6, "gold", segments=14)
    round_house(mb, 0, cy, 3.0, 4.5, 0, 12)                                     # The hall inside the ring.
    F = -math.pi / 2
    with on_round(mb, 0, cy, 3.17, F):
        door(mb, 1.6, 2.9, 0, 0.6)
    for k in range(1, 12):
        with on_round(mb, 0, cy, 3.0, F + TAU * k / 12):
            window(mb, 0, 1.3, 0.55, 2.2)
    bell_roof(mb, 0, cy, 4.8, R + 0.3, 5.2, seg=14, curl=False)
    mb.cylinder((0, cy, 10.2), (0, cy, 10.5), 0.5, 0.6, "gold", segments=8)
    with mb.bone("moon"):                                                       # A moon of crystal floats over the tip.
        mb.sphere((0, cy, 11.6), 0.6, "moon", segments=8, rings=6)
        p.ring(mb, 0, cy, 11.6, 0.9, 0.06, "gold", 12, "y")
    p.bob(mb, rig, "moon", (0, cy, 11.6), 0.15, 8.0, "float")
    for k in range(4):
        a = TAU * k / 4 + TAU / 8
        p.arc(mb, [(math.cos(a) * 0.45, cy + math.sin(a) * 0.45, 10.4), (math.cos(a) * 0.9, cy + math.sin(a) * 0.9, 10.9), (math.cos(a) * 1.0, cy + math.sin(a) * 1.0, 11.4)], 0.06, "gold", 0.4)
    p.stairs(mb, 0, cy - 5.9, 0, 0.6, 3.0, 1.3, "e_white", 0.2)
    for sx in (-1, 1):                                                          # Two leaf-roofed wings.
        wx = sx * 5.6
        mb.box((wx, cy + 0.6, 1.3), (2.4, 4.4, 2.6), "e_white")
        mb.box((wx, cy + 0.6, 0.2), (2.6, 4.6, 0.4), "e_white_dark")
        with p.face(mb, wx, cy + 0.6, 2.4, 4.4, "front"):
            window(mb, 0, 0.7, 0.6, 1.5)
        with p.face(mb, wx, cy + 0.6, 2.4, 4.4, "right" if sx > 0 else "left"):
            for x in (-1.3, 0, 1.3):
                window(mb, x, 0.7, 0.5, 1.4)
        leaf_roof(mb, wx, cy + 0.6, 2.6, 2.4, 4.4, 1.5, n=8, axis="y", lift=0.8)
        p.flag(mb, rig, sx * 3.4, cy - 4.6, 0.6, 3.6, 1.4, 0.6, "e_roof", "white", pole_mat="e_wood")
        lamp_post(mb, rig, sx * 1.9, cy - 5.4, 2.8, -sx)
    mb.cylinder((0, cy - 7.0, 0), (0, cy - 7.0, 0.3), 1.3, 1.2, "e_white", segments=10)   # A small pool before the steps.
    mb.cylinder((0, cy - 7.0, 0.2), (0, cy - 7.0, 0.32), 1.0, 1.0, "e_blue", segments=10)
    vines(mb, rnd, 0, cy, 3.05, 0.8, 4.0, 12, 0.3, 2.8)
    flowers(mb, rnd, -6.5, 6.5, -6.0, -5.2, 10)
    p.tree(mb, -6.0, cy + 4.6, 4.6, 1.3)
    p.tree(mb, 6.2, cy + 4.4, 5.2, 1.4)
    p.finish(mb, "race_elf_center", rig)


def workshop():
    """The bowyers' and weavers' pavilion: open, under a leaf."""
    mb = p.begin()
    rig = p.Rig()
    rnd = p.random.Random(68)
    w, d, h = 5.0, 3.6, 2.6
    mb.box((0, 0.2, 0.1), (w + 0.6, d + 0.6, 0.2), "e_white_dark")
    for sx in (-1, 0, 1):
        for sy in (-1, 1):
            x, y = sx * w / 2, 0.2 + sy * d / 2
            p.arc(mb, [(x * 1.06, y + sy * 0.15, 0.2), (x, y, h * 0.55), (x * 0.96, y - sy * 0.12, h)], 0.11, "e_wood", 0.75)
            p.arc(mb, [(x, y, h * 0.6), (x * 0.9 + 0.3, y - sy * 0.35, h * 0.9)], 0.06, "e_wood", 0.6)
    mb.box((0, 0.2 + d / 2, 1.0), (w, 0.12, 1.6), "e_white")                     # A low wall at the back.
    leaf_roof(mb, 0, 0.2, h, w, d, 1.5, n=8, fill=None)
    mb.box((-1.4, 0.3, 1.1), (0.1, 1.3, 1.8), "e_wood")                          # The loom.
    mb.box((-0.5, 0.3, 1.1), (0.1, 1.3, 1.8), "e_wood")
    mb.box((-0.95, 0.3, 1.95), (1.0, 1.3, 0.1), "e_wood")
    mb.box((-0.95, 0.3, 0.9), (0.04, 1.2, 1.5), "linen")
    mb.box((-0.95, 0.3, 0.5), (0.06, 1.2, 0.5), "e_roof_light")
    mb.box((1.4, 0.6, 0.85), (1.6, 0.8, 0.08), "e_wood")                        # The bowyer's bench and rack.
    for sx in (-0.6, 0.6):
        mb.box((1.4 + sx, 0.6, 0.5), (0.1, 0.7, 0.7), "e_bark")
    for k in range(4):
        x = 0.7 + 0.42 * k
        p.arc(mb, [(x, 1.85, 0.25), (x, 1.7, 0.9), (x, 1.85, 1.55)], 0.035, "wood_light")
    mb.box((1.3, 1.85, 0.9), (1.7, 0.06, 0.06), "e_bark")
    basket(mb, 2.0, -1.2, 0.2, "e_roof_light")
    basket(mb, -2.1, -1.3, 0.2, "flower_w")
    for sx in (-1, 1):
        p.hang_lantern(mb, rig, sx * 2.2, -1.75, 2.45, 0.2, "drop", "window", "gold")
    flowers(mb, rnd, -3.0, 3.0, -2.6, -2.2, 5)
    p.finish(mb, "race_elf_workshop", rig)


def storehouse():
    """The root larder: a hollow stump under a bell of leaves."""
    mb = p.begin()
    rig = p.Rig()
    rnd = p.random.Random(69)
    r, h = 2.1, 2.9
    mb.cylinder((0, 0.3, 0), (0, 0.3, h), r + 0.25, r - 0.15, "e_bark", segments=10)
    for k in range(9):                                                          # Roots.
        a = TAU * k / 9 + 0.3
        if abs(math.sin(a) + 1) < 0.12:
            continue
        c, s = math.cos(a), math.sin(a)
        p.arc(mb, [(c * (r - 0.1), 0.3 + s * (r - 0.1), 1.3), (c * (r + 0.5), 0.3 + s * (r + 0.5), 0.5), (c * (r + 1.2), 0.3 + s * (r + 1.2), 0.0)], 0.3, "e_bark", 0.35)
    F = -math.pi / 2
    with on_round(mb, 0, 0.3, r + 0.1, F):
        p.round_door(mb, 0, 0.1, 0.85, "e_wood", "e_door", "gold")
    for a in (F - 0.9, F + 0.9):
        with on_round(mb, 0, 0.3, r - 0.02, a):
            p.round_win(mb, 0, 1.9, 0.26, "e_wood", "window")
    bell_roof(mb, 0, 0.3, h, r - 0.1, 2.4)
    for k in range(5):                                                          # Shelf mushrooms up the bark.
        a = 0.4 + 0.5 * k
        mb.cylinder((math.cos(a) * (r + 0.1), 0.3 + math.sin(a) * (r + 0.1), 0.9 + 0.35 * k), (math.cos(a) * (r + 0.1), 0.3 + math.sin(a) * (r + 0.1), 1.0 + 0.35 * k), 0.4, 0.3, "e_white_dark", segments=6)
    vines(mb, rnd, 0, 0.3, r + 0.1, 1.6, 2.8, 8, 2.2, 5.6)
    basket(mb, 1.5, -2.0, 0, "flower")
    basket(mb, 2.0, -1.5, 0, "leaf_light")
    basket(mb, -1.6, -2.0, 0, "gold")
    p.sack(mb, -2.1, -1.5, 0, 0.24)
    lamp_post(mb, rig, -2.7, -0.6, 2.4, 1, -0.6)
    p.finish(mb, "race_elf_storehouse", rig)


def moon_pool():
    """A pool that holds the moon, under three ribs of white stone: 8 x 8 m."""
    mb = p.begin()
    rig = p.Rig()
    rnd = p.random.Random(65)
    for r, z, mat in ((3.7, 0.15, "e_white_dark"), (3.3, 0.3, "e_white"), (2.9, 0.48, "e_white_dark")):
        mb.cylinder((0, 0, 0), (0, 0, z), r, r, mat, segments=14)
    mb.cylinder((0, 0, 0.3), (0, 0, 0.5), 2.5, 2.5, "e_blue", segments=14)
    mb.cylinder((0, 0, 0.3), (0, 0, 0.52), 1.1, 1.1, "moon", segments=12)        # The moon in the water.
    for k in range(3):
        a = TAU * k / 3 + math.pi / 2
        c, s = math.cos(a), math.sin(a)
        p.arc(mb, [(c * 3.1, s * 3.1, 0.3), (c * 3.2, s * 3.2, 2.2), (c * 2.5, s * 2.5, 3.9), (c * 1.3, s * 1.3, 4.9), (c * 0.5, s * 0.5, 5.2)], 0.16, "e_white", 0.45)
        mb.cylinder((c * 3.1, s * 3.1, 0.3), (c * 3.1, s * 3.1, 0.7), 0.3, 0.22, "e_white_dark", segments=8)
        for i, (rr, zz) in enumerate(((3.25, 1.6), (2.75, 3.5), (1.7, 4.7))):
            mb.sphere((c * rr, s * rr, zz), 0.2, ("leaf", "leaf_light", "leaf_dark")[i], segments=5, rings=3)
        p.hang_lantern(mb, rig, c * 1.95, s * 1.95, 4.4, 0.35, "drop", "window", "gold", 1.2)
    with mb.bone("moon"):                                                       # A crescent hangs in the air over it.
        n = 9
        for i in range(n):
            a0, a1 = math.radians(215 - 250 * i / n), math.radians(215 - 250 * (i + 1) / n)
            t0, t1 = 0.03 + 0.2 * math.sin(math.pi * i / n), 0.03 + 0.2 * math.sin(math.pi * (i + 1) / n)
            mb.cylinder((math.cos(a0) * 0.75, 0, 3.4 + math.sin(a0) * 0.75), (math.cos(a1) * 0.75, 0, 3.4 + math.sin(a1) * 0.75), t0, t1, "moon", segments=6)
        p.shard(mb, 0.25, 0, 3.5, 0.1, 0.4, "e_blue")
    p.bob(mb, rig, "moon", (0, 0, 3.4), 0.15, 10.0, "float")
    for k in range(6):                                                          # Standing stones with a mark of light.
        a = TAU * k / 6 + TAU / 12
        if abs(math.cos(a)) < 0.3 and math.sin(a) < 0:
            continue
        x, y = math.cos(a) * 3.3, math.sin(a) * 3.3
        mb.box((x, y, 0.75), (0.34, 0.34, 1.0), "e_white", rotation_z=a)
        mb.cylinder((x, y, 1.25), (x, y, 1.6), 0.2, 0.0, "e_white_dark", segments=4)
        mb.box((x + math.cos(a) * 0.17, y + math.sin(a) * 0.17, 0.85), (0.04, 0.12, 0.4), "e_blue", rotation_z=a)
    for k in range(4):
        a = 0.5 + 1.5 * k
        p.lily(mb, math.cos(a) * 1.8, math.sin(a) * 1.8, 0.5, 0.3, k % 2 == 0, a)
    p.stairs(mb, 0, -3.95, 0, 0.3, 1.6, 0.5, "e_white", 0.15)
    for sx in (-1, 1):
        mb.box((sx * 2.0, -3.6, 0.42), (1.2, 0.4, 0.08), "e_white")              # Benches.
        for s2 in (-0.4, 0.4):
            mb.box((sx * 2.0 + s2, -3.6, 0.2), (0.12, 0.3, 0.4), "e_white_dark")
    flowers(mb, rnd, -3.9, 3.9, -3.9, -3.2, 6)
    flowers(mb, rnd, -3.9, -3.2, -2.0, 3.0, 5)
    p.tree(mb, 3.2, 3.2, 3.6, 1.0)
    p.finish(mb, "race_elf_moon_pool", rig)


def tower():
    """A slender watch post of white stone and living wood."""
    mb = p.begin()
    rig = p.Rig()
    rnd = p.random.Random(66)
    r, h = 1.15, 7.5
    round_house(mb, 0, 0, r, h, 5, 9)
    F = -math.pi / 2
    with mb.placed((0, -r - 0.12, 0), 0):
        door(mb, 0.85, 1.7)
    for k, z in enumerate((2.6, 4.4)):
        with mb.placed((0, -r * 0.93, z), 0):
            window(mb, 0, 0, 0.4, 0.9)
    mb.cylinder((0, 0, h - 1.7), (0, 0, h - 1.5), r + 0.3, r + 1.0, "e_wood", segments=10)        # The watch gallery.
    p.ring(mb, 0, 0, h - 0.7, r + 0.98, 0.07, "e_wood", 10)
    for k in range(10):
        a = TAU * k / 10
        p.beam(mb, (math.cos(a) * (r + 0.98), math.sin(a) * (r + 0.98), h - 1.5), (math.cos(a) * (r + 0.98), math.sin(a) * (r + 0.98), h - 0.7), 0.05, "e_wood")
    for k in range(5):
        a = F + TAU * k / 5
        with mb.placed((math.cos(a) * r * 0.9, math.sin(a) * r * 0.9, h - 1.5), a + math.pi / 2):
            p.arch_door(mb, 0, 0, 0.5, 1.2, "e_wood", "dark" if k == 0 else "window", None, 0.1)
    bell_roof(mb, 0, 0, h, r, 2.8, seg=9)
    for a in (F - 0.9, F + 0.9, F + math.pi):
        p.hang_lantern(mb, rig, math.cos(a) * (r + 0.95), math.sin(a) * (r + 0.95), h - 1.5, 0.15, "drop", "window", "gold")
    p.flag(mb, rig, 0.9, 0.9, h - 1.5, 3.4, 1.2, 0.5, "e_roof", "white", pole_mat="e_wood")
    vines(mb, rnd, 0, 0, r + 0.05, 0.4, 4.5, 10, 0.2, 3.0)
    p.finish(mb, "race_elf_tower", rig)


def shrine():
    """The seed shrine: a seed of light floats in an arch of two living trees, 4 x 4 m."""
    mb = p.begin()
    rig = p.Rig()
    rnd = p.random.Random(62)
    mb.cylinder((0, 0, 0), (0, 0, 0.2), 1.9, 1.8, "e_white_dark", segments=10)
    mb.cylinder((0, 0, 0.2), (0, 0, 0.36), 1.4, 1.35, "e_white", segments=10)
    for sx in (-1, 1):                                                          # Two saplings bent into an arch.
        p.arc(mb, [(sx * 1.25, 0.3, 0.2), (sx * 1.35, 0.3, 1.6), (sx * 1.0, 0.3, 2.9), (sx * 0.35, 0.3, 3.6), (0, 0.3, 3.7)], 0.16, "e_bark", 0.5)
        for i, (x, z) in enumerate(((1.45, 1.9), (1.05, 3.1), (0.45, 3.75), (1.3, 2.6))):
            mb.sphere((sx * x, 0.3, z), 0.34 - 0.03 * i, ("leaf", "leaf_light", "leaf_dark", "leaf_light")[i], segments=6, rings=4)
        p.hang_lantern(mb, rig, sx * 0.75, 0.3, 3.25, 0.3, "drop", "window", "gold")
    mb.cylinder((0, 0.3, 0.36), (0, 0.3, 0.9), 0.3, 0.2, "e_white", segments=8)      # The bowl.
    mb.cylinder((0, 0.3, 0.9), (0, 0.3, 1.1), 0.25, 0.6, "e_white", segments=8)
    mb.cylinder((0, 0.3, 1.04), (0, 0.3, 1.12), 0.5, 0.5, "e_blue", segments=8)
    with mb.bone("seed"):
        p.shard(mb, 0, 0.3, 1.9, 0.2, 0.6, "window")
        p.ring(mb, 0, 0.3, 1.9, 0.4, 0.035, "gold", 8)
        for k in range(3):
            a = TAU * k / 3
            mb.sphere((math.cos(a) * 0.55, 0.3 + math.sin(a) * 0.55, 1.9), 0.06, "leaf_light", segments=4, rings=3)
    p.bob(mb, rig, "seed", (0, 0.3, 1.9), 0.1, 8.0, "float")
    flowers(mb, rnd, -1.8, 1.8, -1.9, -1.3, 6)
    for k in range(6):
        a = TAU * k / 6 + 0.5
        mb.sphere((math.cos(a) * 1.1, math.sin(a) * 1.1, 0.42), 0.09, ("flower", "flower_w", "e_blue")[k % 3], segments=5, rings=3)
    p.finish(mb, "race_elf_shrine", rig)


def market_stall():
    """A stand under a leaf between two branches, 3 x 2 m."""
    mb = p.begin()
    rig = p.Rig()
    for sx in (-1, 1):
        for sy in (-1, 1):
            p.arc(mb, [(sx * 1.35, sy * 0.8, 0), (sx * 1.25, sy * 0.72, 1.3), (sx * 1.15, sy * 0.6, 2.2)], 0.09, "e_wood", 0.7)
    leaf_roof(mb, 0, 0, 2.2, 2.3, 1.4, 0.8, n=6, over=0.35, lift=0.5, fill=None)
    mb.box((0, -0.5, 0.82), (2.4, 0.6, 0.08), "e_wood")
    for sx in (-1.0, 1.0):
        p.arc(mb, [(sx, -0.5, 0), (sx * 0.95, -0.5, 0.8)], 0.1, "e_bark")
    basket(mb, -0.8, -0.5, 0.86, "flower")
    basket(mb, -0.2, -0.5, 0.86, "leaf_light")
    for k in range(4):                                                          # Bottles of cordial.
        mb.cylinder((0.4 + 0.2 * k, -0.5, 0.86), (0.4 + 0.2 * k, -0.5, 1.1), 0.06, 0.06, ("e_blue", "e_roof_light", "window")[k % 3], segments=6)
        mb.cylinder((0.4 + 0.2 * k, -0.5, 1.1), (0.4 + 0.2 * k, -0.5, 1.22), 0.03, 0.02, "e_white", segments=5)
    basket(mb, 0.9, 0.4, 0, "gold")
    p.sack(mb, -0.9, 0.4, 0, 0.22)
    for sx in (-1, 1):
        p.hang_lantern(mb, rig, sx * 1.25, -0.95, 2.1, 0.15, "drop", "window", "gold", 0.9)
    p.finish(mb, "race_elf_market_stall", rig)


def well():
    """A spring basin of white stone under a small bell of leaves."""
    mb = p.begin()
    rig = p.Rig()
    mb.cylinder((0, 0, 0), (0, 0, 0.16), 1.4, 1.3, "e_white_dark", segments=9)
    mb.cylinder((0, 0, 0.16), (0, 0, 0.75), 0.95, 1.05, "e_white", segments=9)
    mb.cylinder((0, 0, 0.72), (0, 0, 0.82), 1.12, 1.12, "e_white_dark", segments=9)
    mb.cylinder((0, 0, 0.7), (0, 0, 0.84), 0.85, 0.85, "e_blue", segments=9)
    for k in range(3):
        a = TAU * k / 3 + math.pi / 2
        c, s = math.cos(a), math.sin(a)
        p.arc(mb, [(c * 1.0, s * 1.0, 0.8), (c * 1.05, s * 1.05, 1.7), (c * 0.85, s * 0.85, 2.5)], 0.08, "e_wood", 0.7)
    bell_roof(mb, 0, 0, 2.5, 0.75, 1.3, seg=9)
    with mb.bone("pail"):                                                       # A silver pail on its cord.
        mb.cylinder((0, 0, 2.5), (0, 0, 1.6), 0.012, 0.012, "rope", segments=4)
        mb.cylinder((0, 0, 1.3), (0, 0, 1.6), 0.13, 0.17, "moon", segments=8)
        p.ring(mb, 0, 0, 1.6, 0.17, 0.03, "gold", 8)
    p.sway(mb, rig, "pail", (0, 0, 2.5), 5.0, 3.0, "sway", (1, 0, 0), (0, 0, 1.5))
    p.lily(mb, 0.35, 0.3, 0.84, 0.22, True, 0.4)
    for k in range(4):
        a = 0.8 + 1.5 * k
        mb.sphere((math.cos(a) * 1.25, math.sin(a) * 1.25, 0.14), 0.16, "leaf", segments=5, rings=3)
    p.finish(mb, "race_elf_well", rig)


def lantern_tree():
    """A silver tree hung with lanterns."""
    mb = p.begin()
    rig = p.Rig()
    mb.cylinder((0, 0, 0), (0, 0, 0.22), 1.1, 1.0, "e_white", segments=9)
    p.arc(mb, [(0, 0, 0.2), (0.1, 0, 1.5), (-0.05, 0.05, 2.8), (0.05, 0, 3.8)], 0.2, "e_white_dark", 0.45)
    for k in range(6):
        a = TAU * k / 6 + 0.3
        c, s = math.cos(a), math.sin(a)
        z0 = 2.0 + 0.3 * (k % 3)
        tip = (c * (1.3 + 0.2 * (k % 2)), s * (1.3 + 0.2 * (k % 2)), z0 + 1.0)
        p.arc(mb, [(0, 0, z0), (c * 0.6, s * 0.6, z0 + 0.7), tip], 0.07, "e_white_dark", 0.4)
        mb.sphere((tip[0], tip[1], tip[2] + 0.12), 0.26, ("moon", "e_roof_light", "leaf_light")[k % 3], segments=6, rings=4)
        p.hang_lantern(mb, rig, tip[0], tip[1], tip[2], 0.3 + 0.15 * (k % 2), "drop", "window" if k % 2 else "e_blue", "gold")
    mb.sphere((0.05, 0, 4.0), 0.4, "moon", segments=6, rings=4)
    p.finish(mb, "race_elf_lantern_tree", rig)


MODELS = {
    "race_elf_shrine": shrine, "race_elf_market_stall": market_stall, "race_elf_well": well, "race_elf_lantern_tree": lantern_tree,
    "race_elf_moon_pool": moon_pool, "race_elf_tower": tower,
    "race_elf_house_1": house(1), "race_elf_house_2": house(2), "race_elf_house_3": house(3),
    "race_elf_center": center, "race_elf_workshop": workshop, "race_elf_storehouse": storehouse,
}
