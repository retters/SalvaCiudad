"""One building idea per race: a dwarf hall carved in the rock, an elf
tree house and an orc war hut."""

import math
import random

import parts as P
from camp import cone_panels, wall_panels
from civic import railing_ring, round_window
from parts import game, TAU


def dwarf_hall(mb, rig, seed=60):
    rnd = random.Random(seed)
    # The mountain: big faceted boulders behind the carved front.
    for i in range(14):
        x = rnd.uniform(-4.2, 4.2)
        r = rnd.uniform(2.2, 3.2)
        sy = rnd.uniform(0.55, 0.75)
        y = max(rnd.uniform(-0.4, 3.0), -0.9 + r * sy)   # Never through the carved front.
        z = rnd.uniform(0.5, 3.6) * (1 - abs(x) / 7)
        mb.sphere((x, y, z), r, rnd.choice(("rock", "rock", "rock_dark")), segments=7, rings=5,
                  scale=(rnd.uniform(0.9, 1.2), sy, rnd.uniform(0.8, 1.1)))
    mb.sphere((0, 2.4, 4.8), 2.8, "rock", segments=7, rings=5, scale=(1.3, 0.6, 1.0))
    mb.cylinder((0.6, 2.2, 7.0), (0.9, 2.3, 8.4), 0.9, 0.0, "rock_dark", segments=6)
    # The carved front: a stepped slab of dressed stone.
    fy = -1.6
    for w, z0, z1 in ((9.0, 0.0, 3.6), (7.0, 3.6, 5.0), (4.6, 5.0, 6.2), (2.2, 6.2, 7.0)):
        mb.box((0, fy + 0.6, (z0 + z1) / 2), (w, 1.4, z1 - z0), "wall")
        mb.box((0, fy + 0.55, z1 - 0.12), (w + 0.2, 1.5, 0.24), "wall_light")
        mb.box((0, fy - 0.12, z1 - 0.45), (w - 0.4, 0.06, 0.16), "gold")
    with mb.placed((0, fy - 0.1, 0)):
        P.scatter_face(mb, rnd, 8.6, 0.6, 3.2, density=0.3, size=(0.7, 0.35))
        # The great door.
        P.arch_trim(mb, 0, 0, 0, 2.6, 4.0, mat="wall_light", t=0.4, depth=0.2, seg=4)
        mb.box((0, 0.05, 1.35), (2.6, 0.2, 2.7), "door")
        mb.cylinder((0, 0.15, 2.7), (0, -0.05, 2.7), 1.3, 1.3, "door", segments=8)
        mb.box((0, -0.08, 2.0), (0.08, 0.06, 4.0), "iron")
        for z in (0.7, 1.7, 2.7):
            mb.box((0, -0.08, z), (2.6, 0.06, 0.16), "iron")
            for s in (-1, 1):
                mb.sphere((s * 0.9, -0.12, z), 0.08, "gold", segments=5, rings=3)
        for s in (-1, 1):
            mb.cylinder((s * 0.35, -0.1, 1.9), (s * 0.35, -0.16, 1.9), 0.16, 0.16, "gold", segments=8)
        # Crossed axes over the door.
        for s in (-1, 1):
            P.beam(mb, (s * 0.6, -0.12, 4.5), (-s * 0.6, -0.12, 5.7), 0.05, "timber")
            P.prism_xz(mb, [(-s * 0.75, 5.35), (-s * 0.4, 5.55), (-s * 0.3, 5.95), (-s * 0.85, 5.85)][::s], -0.18, -0.1, "iron")
        # Windows lit by the forges, with runes of gold between them.
        for x in (-3.4, -2.3, 2.3, 3.4):
            mb.box((x, -0.02, 2.2), (0.6, 0.12, 1.0), "wall_light")
            mb.box((x, -0.05, 2.2), (0.36, 0.12, 0.76), "lava")
        for i, x in enumerate((-2.6, -1.9, 1.9, 2.6)):
            mb.box((x, -0.04, 4.3), (0.12, 0.06, 0.5), "gold")
            mb.box((x + (0.12 if i % 2 else -0.12), -0.04, 4.4), (0.2, 0.06, 0.1), "gold")
        P.wall_banner(mb, -2.85, 3.3, w=0.8, h=1.9, mat="banner", stripe="gold")
        P.wall_banner(mb, 2.85, 3.3, w=0.8, h=1.9, mat="banner", stripe="gold")
    # Two massive pillars with braziers, and the stair.
    for s in (-1, 1):
        px, py = s * 2.4, fy - 1.3
        mb.box((px, py, 0.3), (1.3, 1.3, 0.6), "wall_dark")
        mb.box((px, py, 1.9), (1.0, 1.0, 2.6), "wall")
        for z in (1.0, 2.9):
            mb.box((px, py, z), (1.12, 1.12, 0.2), "gold")
        mb.box((px, py, 3.35), (1.3, 1.3, 0.3), "wall_light")
        mb.cylinder((px, py, 3.5), (px, py, 3.85), 0.3, 0.55, "iron", segments=8)
        mb.cylinder((px, py, 3.85), (px, py, 4.5), 0.42, 0.0, "ember", segments=6)
        mb.cylinder((px, py, 3.85), (px + 0.1, py, 4.25), 0.25, 0.0, "lava", segments=5)
    with mb.placed((0, fy - 2.6, 0)):
        mb.box((0, 1.3, 0.1), (3.2, 2.6, 0.2), "wall_dark")
        mb.box((0, 1.7, 0.25), (3.0, 1.8, 0.14), "wall_light")
    # Chimneys of the forges coming out of the rock.
    for x, y, z in ((-3.0, 2.0, 5.6), (3.4, 1.6, 5.0)):
        mb.box((x, y, z - 1.5), (0.9, 0.9, 3.0), "wall_dark")
        mb.box((x, y, z + 0.06), (1.1, 1.1, 0.16), "wall")
        mb.box((x, y, z + 0.16), (0.6, 0.6, 0.06), "ember")
    # An ore cart on its rails from a side adit.
    mb.box((4.2, fy + 0.15, 1.0), (1.5, 0.3, 2.0), "charcoal")
    for s in (-1, 1):
        mb.box((4.2 + s * 0.85, fy + 0.1, 1.05), (0.25, 0.4, 2.1), "timber")
    mb.box((4.2, fy + 0.1, 2.2), (2.0, 0.4, 0.28), "timber")
    for s in (-1, 1):
        mb.box((4.2 + s * 0.35, fy - 1.4, 0.05), (0.07, 2.8, 0.08), "iron")
    for i in range(5):
        mb.box((4.2, fy - 0.2 - i * 0.6, 0.02), (1.1, 0.16, 0.05), "timber")
    with mb.placed((4.2, fy - 1.9, 0)):
        tub = mb.prism([(-0.45, -0.6), (0.45, -0.6), (0.45, 0.6), (-0.45, 0.6)], 0.3, 0.95, "iron")
        for v in tub:
            if v.co.z < 0.5:
                v.co.x *= 0.7
        mb.sphere((0, 0, 0.95), 0.42, "gold", segments=6, rings=4, scale=(0.9, 1.2, 0.45))
    P.rocks(mb, rnd, -4.4, -2.8, 0.9, n=6, size=0.6)
    for x in (-3.9, -3.3):
        with mb.placed((x, fy - 0.6, 0)):
            game.barrel(mb, 0, 0, h=0.9, r=0.34)


def leaf_ball(mb, rnd, x, y, z, r):
    mb.sphere((x, y, z), r, rnd.choice(("leaf", "leaf", "leaf_dark", "leaf_light")), segments=7, rings=5,
              scale=(1.0, rnd.uniform(0.85, 1.0), rnd.uniform(0.6, 0.75)))


def elf_hut(mb, x, y, z, r, h, roof_h, door_a=None):
    """A round elven room with tall glowing windows and a bell-shaped roof."""
    mb.cylinder((x, y, z), (x, y, z + h), r, r * 0.92, "white", segments=10)
    mb.cylinder((x, y, z), (x, y, z + 0.2), r + 0.06, r + 0.06, "wood_light", segments=10)
    for i in range(10):
        a = TAU * i / 10
        P.beam(mb, (x + r * math.cos(a), y + r * math.sin(a), z), (x + r * 0.92 * math.cos(a), y + r * 0.92 * math.sin(a), z + h),
               0.07, "wood_light")
    for i in range(5):
        a = TAU * i / 5 + 0.3
        if door_a is not None and abs((a - door_a + math.pi) % TAU - math.pi) < 0.5:
            continue
        round_window(mb, x, y, r * 0.93, a, z + h * 0.55, w=0.35, h=h * 0.5, glass="glow", frame="wood_light")
    if door_a is not None:
        c, s = math.cos(door_a), math.sin(door_a)
        mb.box((x + r * 0.93 * c, y + r * 0.93 * s, z + 0.9), (0.2, 0.8, 1.8), "wood_light", rotation_z=door_a)
        mb.box((x + r * 0.96 * c, y + r * 0.96 * s, z + 0.85), (0.2, 0.6, 1.6), "teal_dark", rotation_z=door_a)
    P.cone_roof(mb, x, y, z + h, r * 0.92, roof_h, ("copper", "copper_dark"), rows=5, seg=10, eave=0.45, power=0.62,
                finial="gold")


def elf_tree_house(mb, rig, seed=62):
    rnd = random.Random(seed)
    # The great tree.
    mb.cylinder((0, 0, 0), (0, 0, 6.5), 1.55, 1.15, "bark", segments=9)
    mb.cylinder((0, 0, 6.5), (0.2, 0.1, 11.0), 1.15, 0.7, "bark", segments=9)
    for i in range(6):
        a = TAU * i / 6 + 0.4
        mb.cylinder((0.9 * math.cos(a), 0.9 * math.sin(a), 1.5), (2.7 * math.cos(a), 2.7 * math.sin(a), -0.1), 0.55, 0.14,
                    "bark_dark" if i % 2 else "bark", segments=6)
    branches = [((0.5, 0.3, 7.4), (4.2, 1.6, 9.2)), ((-0.4, 0.4, 8.0), (-3.6, 2.4, 10.0)), ((0, -0.5, 8.8), (0.6, -3.4, 10.6)),
                ((0.2, 0.3, 9.6), (1.8, 3.2, 11.6)), ((-0.3, -0.2, 9.4), (-3.0, -2.2, 11.0))]
    for a, b in branches:
        mb.cylinder(a, b, 0.42, 0.16, "bark", segments=6)
        leaf_ball(mb, rnd, b[0], b[1], b[2] + 0.6, rnd.uniform(2.0, 2.6))
    for i in range(6):
        a = TAU * i / 6
        leaf_ball(mb, rnd, 0.2 + 2.0 * math.cos(a), 0.1 + 2.0 * math.sin(a), 12.2 + rnd.uniform(-0.4, 0.6), rnd.uniform(2.0, 2.7))
    leaf_ball(mb, rnd, 0.2, 0.1, 13.8, 2.6)
    # The lower terrace, around the trunk.
    z1, r1 = 3.6, 3.7
    mb.cylinder((0, 0, z1 - 0.14), (0, 0, z1), r1, r1, "plank", segments=12)
    mb.cylinder((0, 0, z1 - 0.3), (0, 0, z1 - 0.14), r1 - 0.2, r1 - 0.05, "wood_light", segments=12)
    for i in range(8):
        a = TAU * i / 8 + 0.2
        P.beam(mb, (1.35 * math.cos(a), 1.35 * math.sin(a), z1 - 1.7), ((r1 - 0.3) * math.cos(a), (r1 - 0.3) * math.sin(a), z1 - 0.2),
               0.12, "bark_dark")
    railing_ring(mb, 0, 0, z1, r1 - 0.1, n=12, h=0.9, post="wood_light", rail="rope")
    elf_hut(mb, -2.0, -1.3, z1, 1.45, 2.2, 2.6, door_a=-1.0)
    elf_hut(mb, 2.1, 1.3, z1, 1.25, 2.0, 2.3, door_a=2.4)
    # The stair winding up the trunk.
    n = 16
    for i in range(n):
        t = (i + 0.5) / n
        a = -2.2 + 4.6 * t
        z = 0.2 + (z1 - 0.3) * t
        rr = 1.55 - 0.25 * (z / 6.5) + 0.6
        mb.box((rr * math.cos(a), rr * math.sin(a), z), (1.15, 0.6, 0.12), "wood_light", rotation_z=a)
        if i % 2 == 0:
            mb.box(((rr + 0.5) * math.cos(a), (rr + 0.5) * math.sin(a), z + 0.5), (0.06, 0.06, 1.0), "wood_light", rotation_z=a)
    # The upper terrace, with an open pavilion.
    z2, cx2, cy2, r2 = 6.9, 0.9, -1.0, 2.5
    mb.cylinder((cx2, cy2, z2 - 0.14), (cx2, cy2, z2), r2, r2, "plank", segments=10)
    for i in range(4):
        a = TAU * i / 4 + 0.9
        P.beam(mb, (0.3, -0.1, z2 - 1.6), (cx2 + (r2 - 0.4) * math.cos(a), cy2 + (r2 - 0.4) * math.sin(a), z2 - 0.15), 0.11,
               "bark_dark")
    railing_ring(mb, cx2, cy2, z2, r2 - 0.1, n=10, h=0.9, post="wood_light", rail="rope")
    px, py = cx2 + 0.7, cy2 - 0.8
    for i in range(6):
        a = TAU * i / 6
        mb.cylinder((px + 1.05 * math.cos(a), py + 1.05 * math.sin(a), z2), (px + 1.0 * math.cos(a), py + 1.0 * math.sin(a), z2 + 2.1),
                    0.06, 0.05, "white", segments=5)
    P.cone_roof(mb, px, py, z2 + 2.1, 1.0, 2.2, ("copper", "copper_dark"), rows=5, seg=10, eave=0.4, power=0.62, finial="gold")
    mb.cylinder((px, py, z2), (px, py, z2 + 0.6), 0.3, 0.2, "white", segments=6)
    mb.sphere((px, py, z2 + 0.85), 0.25, "crystal", segments=6, rings=4)
    # A ladder between the terraces.
    for s in (-0.25, 0.25):
        P.beam(mb, (2.6 + s, -1.6, z1), (2.3 + s, -1.9, z2), 0.05, "wood_light")
    for i in range(8):
        t = (i + 0.5) / 8
        mb.box((2.6 - 0.3 * t, -1.6 - 0.3 * t, z1 + (z2 - z1) * t), (0.5, 0.05, 0.05), "wood_light")
    # A rope bridge to a lookout on a smaller tree.
    tx, ty = -4.0, -3.4
    mb.cylinder((tx, ty, 0), (tx, ty, 7.6), 0.5, 0.28, "bark", segments=7)
    leaf_ball(mb, rnd, tx, ty, 8.4, 1.7)
    zl = 5.6
    mb.cylinder((tx, ty, zl - 0.12), (tx, ty, zl), 1.3, 1.3, "plank", segments=8)
    railing_ring(mb, tx, ty, zl, 1.2, n=8, h=0.8, post="wood_light", rail="rope")
    ax, ay, az = -1.0, -3.2 * 0.72, z2 - 0.1
    ax, ay = cx2 - r2 * 0.75, cy2 - r2 * 0.6
    m = 9
    prev = None
    for i in range(m + 1):
        t = i / m
        bx, by = ax + (tx + 1.1 - ax) * t, ay + (ty + 0.5 - ay) * t
        bz = az + (zl - az) * t - 0.55 * math.sin(math.pi * t)
        if prev:
            ang = math.atan2(by - prev[1], bx - prev[0])
            mb.box(((bx + prev[0]) / 2, (by + prev[1]) / 2, (bz + prev[2]) / 2), (0.34, 0.8, 0.06), "wood_light", rotation_z=ang)
            for s in (-1, 1):
                ox, oy = -math.sin(ang) * 0.4 * s, math.cos(ang) * 0.4 * s
                P.beam(mb, (prev[0] + ox, prev[1] + oy, prev[2] + 0.85), (bx + ox, by + oy, bz + 0.85), 0.025, "rope")
                P.beam(mb, (bx + ox, by + oy, bz), (bx + ox, by + oy, bz + 0.85), 0.02, "rope")
        prev = (bx, by, bz)
    # Lanterns hanging from the branches, which sway.
    names = []
    for i, (lx, ly, lz) in enumerate(((3.6, 1.4, 8.6), (-3.0, 2.0, 9.4), (0.5, -3.0, 10.0), (-2.6, -1.9, 10.4))):
        name = "lantern%d" % i
        with mb.bone(name):
            mb.box((lx, ly, lz - 0.7), (0.02, 0.02, 1.4), "rope")
            mb.sphere((lx, ly, lz - 1.55), 0.2, "glow", segments=6, rings=4, scale=(1, 1, 1.25))
            mb.cylinder((lx, ly, lz - 1.33), (lx, ly, lz - 1.25), 0.12, 0.04, "gold", segments=6)
        rig.bone(name, (lx, ly, lz), (lx, ly, lz - 1.0), None)
        names.append(name)
    rig.add("sway", 3.0, lambda t: {n: [(P.kit.X, 7 * math.sin(TAU * t + i * 1.3)), (P.kit.Y, 4 * math.sin(TAU * t + i * 2.1 + 1))]
                                    for i, n in enumerate(names)})
    # At the foot: mushrooms and flowers.
    for i in range(7):
        a = rnd.uniform(0, TAU)
        rr = rnd.uniform(2.6, 4.2)
        x, y = rr * math.cos(a), rr * math.sin(a)
        if i % 2:
            mb.cylinder((x, y, 0), (x, y, 0.3), 0.06, 0.05, "bone", segments=5)
            mb.cylinder((x, y, 0.3), (x, y, 0.48), 0.22, 0.03, "band", segments=7)
        else:
            mb.sphere((x, y, 0.15), 0.22, "leaf_light", segments=5, rings=3)
            mb.sphere((x, y, 0.33), 0.09, rnd.choice(("flowers", "flowers_y", "magic")), segments=5, rings=3)


def skull(mb, x, y, z, s=1.0, horns=True):
    mb.sphere((x, y, z), 0.26 * s, "bone", segments=6, rings=4, scale=(1, 1.1, 1))
    mb.box((x, y - 0.2 * s, z - 0.2 * s), (0.26 * s, 0.24 * s, 0.2 * s), "bone")
    for sx in (-1, 1):
        mb.box((x + sx * 0.1 * s, y - 0.25 * s, z + 0.02 * s), (0.09 * s, 0.06 * s, 0.09 * s), "charcoal")
        if horns:
            mb.cylinder((x + sx * 0.2 * s, y, z + 0.1 * s), (x + sx * 0.6 * s, y - 0.1 * s, z + 0.5 * s), 0.08 * s, 0.0, "tusk",
                        segments=5)


def tusk(mb, x, y, lean, h=3.4, r=0.26, side=1):
    """A great curved tusk rising from (x, y), leaning toward -side in X."""
    prev = (x, y, 0.0)
    n = 5
    for i in range(1, n + 1):
        t = i / n
        p = (x - side * lean * t * t, y, h * math.sin(t * math.pi / 2))
        mb.cylinder(prev, p, r * (1 - (i - 1) / n) + 0.03, r * (1 - i / n) + 0.02 * (i < n), "tusk", segments=6)
        prev = p


def orc_hut(mb, rig, seed=64):
    rnd = random.Random(seed)
    x, y, r, wh, n = 0.0, 0.5, 2.7, 1.8, 12
    mb.cylinder((x, y, 0), (x, y, wh - 0.05), r - 0.2, r - 0.2, "charcoal", segments=12)
    wall_panels(mb, x, y, 0, r, wh, ("hide", "hide_dark"), n, skip=(0,), thick=0.1)
    for i in range(n):
        a = -math.pi / 2 + math.pi / n + TAU * i / n
        mb.cylinder((x + r * math.cos(a), y + r * math.sin(a), 0), (x + (r - 0.1) * math.cos(a), y + (r - 0.1) * math.sin(a), wh + 0.5),
                    0.11, 0.08, "log", segments=6)
    cone_panels(mb, x, y, wh, r + 0.35, 2.9, ("hide_dark", "hide", "fur"), n, r_top=0.4)
    for i in range(6):
        a = TAU * i / 6 + 0.2
        P.beam(mb, (x + 0.45 * math.cos(a), y + 0.45 * math.sin(a), wh + 2.6), (x - 0.5 * math.cos(a), y - 0.5 * math.sin(a), wh + 4.0),
               0.06, "log")
    mb.cylinder((x, y, wh + 2.8), (x, y, wh + 2.95), 0.42, 0.42, "charcoal", segments=8)
    for i in range(10):  # Patches stitched on the roof.
        a = rnd.uniform(0, TAU)
        t = rnd.uniform(0.2, 0.7)
        rr = (r + 0.35) * (1 - t) + 0.4 * t + 0.03
        mb.box((x + rr * math.cos(a), y + rr * math.sin(a), wh + 2.9 * t + 0.05), (0.1, 0.6, 0.5), rnd.choice(("fur", "hide_dark")),
               rotation_z=a)
    # The entrance between two great tusks, under a horned skull.
    fy = y - r * math.cos(math.pi / n)
    tusk(mb, -1.5, fy - 0.3, 1.1, side=-1)
    tusk(mb, 1.5, fy - 0.3, 1.1, side=1)
    skull(mb, 0, fy - 0.35, 3.2, s=1.6)
    mb.box((0, fy - 0.2, 2.2), (1.9, 0.14, 0.2), "log")
    for s in (-1, 1):
        mb.box((s * 0.85, fy - 0.2, 1.1), (0.2, 0.2, 2.2), "log")
        mb.cylinder((s * 0.85, fy - 0.4, 1.5), (s * 0.85, fy - 0.33, 1.5), 0.38, 0.38, "iron" if s < 0 else "blood", segments=8)
        mb.cylinder((s * 0.85, fy - 0.45, 1.5), (s * 0.85, fy - 0.4, 1.5), 0.12, 0.12, "tusk", segments=6)
    # War banners on poles topped with skulls.
    for i, (bx, by) in enumerate(((-3.3, -2.6), (3.3, -2.2))):
        mb.cylinder((bx, by, 0), (bx, by, 4.4), 0.09, 0.06, "log", segments=6)
        skull(mb, bx, by - 0.02, 4.55, s=0.9, horns=(i == 0))
        P.flag(mb, rig, bx, by, 2.0, pole=2.1, length=1.5, height=1.0, mat="blood", stripe="charcoal", pennant=True, speed=0.8)
    # Sharpened stakes around the back.
    for i in range(11):
        a = 0.15 + (math.pi - 0.3) * i / 10
        c, s = math.cos(a), math.sin(a)
        mb.cylinder((x + 3.5 * c, y + 3.5 * s, 0), (x + 4.3 * c, y + 4.3 * s, 1.5), 0.1, 0.0, "log", segments=5)
    # The war drum, the fire with a spit, and a rack of crude weapons.
    dx, dy = -2.4, -3.2
    mb.cylinder((dx, dy, 0.25), (dx, dy, 0.95), 0.5, 0.58, "log", segments=10)
    mb.cylinder((dx, dy, 0.95), (dx, dy, 1.0), 0.6, 0.6, "hide", segments=10)
    for i in range(3):
        a = TAU * i / 3
        P.beam(mb, (dx + 0.6 * math.cos(a), dy + 0.6 * math.sin(a), 0), (dx + 0.4 * math.cos(a), dy + 0.4 * math.sin(a), 0.5), 0.05,
               "tusk")
    fx, fyy = 1.6, -3.3
    for i in range(7):
        a = TAU * i / 7
        mb.sphere((fx + 0.6 * math.cos(a), fyy + 0.6 * math.sin(a), 0.1), 0.17, "rock" if i % 2 else "rock_dark", segments=5, rings=3,
                  scale=(1, 1, 0.7))
    mb.cylinder((fx, fyy, 0.05), (fx, fyy, 0.7), 0.32, 0.0, "ember", segments=6)
    mb.cylinder((fx + 0.1, fyy, 0.05), (fx + 0.12, fyy, 0.45), 0.2, 0.0, "lava", segments=5)
    for s in (-1, 1):
        mb.box((fx + s * 0.8, fyy, 0.55), (0.07, 0.07, 1.1), "log")
    mb.cylinder((fx - 0.9, fyy, 1.05), (fx + 0.9, fyy, 1.05), 0.03, 0.03, "iron", segments=5)
    mb.sphere((fx, fyy, 1.05), 0.22, "hide_dark", segments=6, rings=4, scale=(1.6, 0.8, 0.8))
    wx, wy = 3.6, 0.6
    for s in (-0.5, 0.5):
        mb.box((wx, wy + s, 0.7), (0.1, 0.1, 1.4), "log")
    mb.box((wx, wy, 1.25), (0.08, 1.1, 0.08), "log")
    for i in range(3):
        yy = wy - 0.3 + i * 0.3
        mb.cylinder((wx - 0.1, yy, 0.05), (wx - 0.18, yy, 1.9), 0.035, 0.035, "wood", segments=4)
        P.prism_yz(mb, [(yy - 0.28, 1.5), (yy, 1.6), (yy + 0.28, 1.5), (yy + 0.2, 1.9), (yy - 0.2, 1.9)], wx - 0.2, wx - 0.14,
                   "iron")


def make(name, fn, colors, **kw):
    def build():
        mb = P.begin()
        rig = P.Rig()
        fn(mb, rig, **kw)
        P.finish(mb, name, colors, rig)
    return build


MODELS = {
    "bld_dwarf_hall": make("bld_dwarf_hall", dwarf_hall, P.palette(banner=0x8E2A24, wall=0x8E8A84, wall_dark=0x6E6A66,
                                                                 wall_light=0xA8A49C)),
    "bld_elf_tree_house": make("bld_elf_tree_house", elf_tree_house, P.BASE),
    "bld_elf_tree_house_autumn": make("bld_elf_tree_house_autumn", elf_tree_house,
                                      P.palette(leaf=0xC8782A, leaf_dark=0xA85A22, leaf_light=0xE0A83A)),
    "bld_orc_war_hut": make("bld_orc_war_hut", orc_hut, P.BASE),
}
