"""Buildings for the other races of the game: a foxfolk burrow, a frogfolk
pond house, a lizardfolk step pyramid, a catfolk tower house and a dark
elf spire."""

import math
import random

import parts as P
from civic import railing_ring, round_window
from parts import game, TAU


def fox_burrow(mb, rig, seed=90):
    rnd = random.Random(seed)
    # Two grassy mounds; the big one is the home.
    mb.sphere((0, 1.75, 0), 3.7, "grass", segments=10, rings=6, scale=(1.0, 0.85, 0.72))
    mb.sphere((-2.6, 2.0, 0), 2.2, "grass_dark", segments=8, rings=5, scale=(1.0, 0.9, 0.7))
    for _ in range(12):
        a = rnd.uniform(0.3, math.pi - 0.3)
        r = rnd.uniform(1.0, 3.0)
        mb.sphere((r * math.cos(a), 1.75 + r * math.sin(a) * 0.8, 3.7 * 0.72 * math.sqrt(max(0.05, 1 - (r / 3.7) ** 2)) - 0.1),
                  rnd.uniform(0.3, 0.6), rnd.choice(("grass_dark", "leaf_light")), segments=5, rings=3, scale=(1, 1, 0.4))
    # The front: a stone-framed wall cut into the mound, a round door and round windows.
    fy = -1.5
    P.prism_xz(mb, [(-2.4, 0), (2.4, 0), (2.0, 1.5), (1.0, 2.25), (-1.0, 2.25), (-2.0, 1.5)], fy, fy + 1.2, "plaster_warm")
    for x0, z0, x1, z1 in ((-2.4, 0, -2.0, 1.5), (-2.0, 1.5, -1.0, 2.25), (-1.0, 2.25, 1.0, 2.25), (1.0, 2.25, 2.0, 1.5),
                           (2.0, 1.5, 2.4, 0)):
        P.beam(mb, (x0, fy - 0.04, z0), (x1, fy - 0.04, z1), 0.22, "timber")
    mb.cylinder((0, fy + 0.05, 1.0), (0, fy - 0.12, 1.0), 0.98, 0.98, "stone", segments=12)
    with mb.bone("door"):
        mb.cylinder((0, fy - 0.08, 1.0), (0, fy - 0.2, 1.0), 0.8, 0.8, "band", segments=12)
        mb.box((0, fy - 0.22, 1.0), (1.5, 0.03, 0.1), "iron")
        mb.sphere((0, fy - 0.24, 1.0), 0.09, "brass", segments=6, rings=4)
    rig.bone("door", (-0.8, fy - 0.14, 1.0), (-0.8, fy - 0.14, 2.0), None)
    rig.add("open", 1.5, lambda t: {"door": [(P.kit.Z, -105 * P.kit.smooth(t))]}, loops=False)
    rig.add("close", 1.5, lambda t: {"door": [(P.kit.Z, -105 * (1 - P.kit.smooth(t)))]}, loops=False)
    mb.cylinder((0, fy - 0.02, 1.0), (0, fy - 0.07, 1.0), 0.78, 0.78, "charcoal", segments=12)
    for x in (-1.55, 1.55):
        mb.cylinder((x, fy + 0.05, 1.05), (x, fy - 0.1, 1.05), 0.42, 0.42, "timber", segments=10)
        mb.cylinder((x, fy, 1.05), (x, fy - 0.13, 1.05), 0.32, 0.32, "glow", segments=10)
        mb.box((x, fy - 0.14, 1.05), (0.64, 0.03, 0.04), "timber")
        mb.box((x, fy - 0.14, 1.05), (0.04, 0.03, 0.64), "timber")
        mb.box((x, fy - 0.22, 0.6), (0.8, 0.24, 0.16), "wood")
        for i in range(3):
            mb.sphere((x - 0.25 + i * 0.25, fy - 0.24, 0.74), 0.11, ("flowers", "flowers_y", "magic")[i], segments=5, rings=3)
    mb.box((0, fy - 0.5, 0.06), (1.4, 0.9, 0.12), "stone")
    # A chimney and a little tree on the mound, a pantry door in the small mound.
    P.chimney(mb, 1.5, 2.3, 1.8, 3.6, w=0.5, mat="stone", cap="stone_dark")
    mb.cylinder((-0.8, 2.4, 2.3), (-0.9, 2.5, 3.6), 0.12, 0.08, "bark", segments=6)
    mb.sphere((-0.9, 2.5, 4.1), 0.9, "leaf", segments=7, rings=5, scale=(1, 1, 0.8))
    mb.cylinder((-2.6, 0.02, 0.6), (-2.6, -0.1, 0.6), 0.6, 0.6, "stone", segments=10)
    mb.cylinder((-2.6, -0.05, 0.6), (-2.6, -0.16, 0.6), 0.46, 0.46, "wood", segments=10)
    # The garden: a wicker fence, vegetable rows, a lantern, a mailbox, stepping stones.
    for sx in (-1, 1):
        game.fence(mb, sx * 0.9, -3.7, sx * 3.6, -3.7, posts=3, h=0.6)
    game.fence(mb, 3.6, -3.7, 3.6, -1.2, posts=3, h=0.6)
    game.fence(mb, -3.6, -3.7, -3.6, -1.6, posts=3, h=0.6)
    for i in range(3):
        mb.box((2.2, -2.0 - i * 0.55, 0.06), (1.8, 0.35, 0.12), "soil")
        for k in range(4):
            mb.sphere((1.5 + k * 0.45, -2.0 - i * 0.55, 0.2), 0.13, ("leaves", "berries", "flowers_y")[i], segments=5, rings=3)
    for i in range(4):
        mb.cylinder((0.1 * (-1) ** i, -2.4 - i * 0.55, 0), (0.1 * (-1) ** i, -2.4 - i * 0.55, 0.06), 0.28, 0.28, "stone", segments=7)
    mb.box((-1.5, -3.2, 0.9), (0.08, 0.08, 1.8), "timber")
    mb.box((-1.5, -3.4, 1.7), (0.08, 0.5, 0.06), "timber")
    mb.box((-1.5, -3.6, 1.45), (0.2, 0.2, 0.3), "glow")
    mb.box((-2.6, -3.4, 0.5), (0.07, 0.07, 1.0), "timber")
    mb.box((-2.6, -3.4, 1.05), (0.3, 0.45, 0.25), "band")


def frog_pond_house(mb, rig, seed=92):
    rnd = random.Random(seed)
    pts = [(3.8 * math.cos(TAU * i / 14), 0.2 + 3.7 * math.sin(TAU * i / 14)) for i in range(14)]
    mb.prism([(x * 1.06, 0.2 + (y - 0.2) * 1.06) for x, y in pts], 0.0, 0.06, "earth")
    mb.prism(pts, 0.03, 0.1, "water")

    def hut(x, y, r, wall_h, dome_h, door_a):
        mb.cylinder((x, y, 0.75), (x, y, 0.9), r + 0.5, r + 0.5, "plank", segments=10)
        for i in range(6):
            a = TAU * i / 6 + 0.3
            mb.cylinder((x + (r + 0.2) * math.cos(a), y + (r + 0.2) * math.sin(a), -0.3),
                        (x + (r + 0.2) * math.cos(a), y + (r + 0.2) * math.sin(a), 0.78), 0.1, 0.09, "log", segments=6)
        mb.cylinder((x, y, 0.9), (x, y, 0.9 + wall_h), r, r, "thatch_dark", segments=10)
        for i in range(10):
            a = TAU * i / 10
            mb.box((x + r * math.cos(a), y + r * math.sin(a), 0.9 + wall_h / 2), (0.08, 0.08, wall_h), "moss", rotation_z=a)
        P.dome(mb, x, y, 0.9 + wall_h, r, dome_h, ("thatch", "moss", "thatch"), rows=4, seg=10, eave=0.45, finial=None)
        mb.cylinder((x, y, 0.9 + wall_h + dome_h - 0.1), (x, y, 0.9 + wall_h + dome_h + 0.35), 0.16, 0.22, "thatch_dark", segments=6)
        c, s = math.cos(door_a), math.sin(door_a)
        q = r * math.cos(math.pi / 10)
        mb.cylinder((x + (q - 0.05) * c, y + (q - 0.05) * s, 0.9 + wall_h * 0.5), (x + (q + 0.06) * c, y + (q + 0.06) * s, 0.9 + wall_h * 0.5),
                    wall_h * 0.48, wall_h * 0.48, "moss", segments=10)
        mb.cylinder((x + (q + 0.02) * c, y + (q + 0.02) * s, 0.9 + wall_h * 0.48), (x + (q + 0.1) * c, y + (q + 0.1) * s, 0.9 + wall_h * 0.48),
                    wall_h * 0.38, wall_h * 0.38, "charcoal", segments=10)
        for k in (1.7, -1.7):
            round_window(mb, x, y, q, door_a + k, 0.9 + wall_h * 0.6, w=0.32, h=0.32, glass="glow", frame="moss")

    hut(0.3, 1.0, 1.7, 1.4, 1.7, -math.pi / 2)
    hut(-2.2, -0.6, 1.0, 1.0, 1.1, -0.9)
    # Walkways from the shore and between the huts.
    for (x0, y0, z0), (x1, y1, z1) in (((0.3, -4.2, 0.1), (0.3, -1.2, 0.85)), ((-1.5, -0.2, 0.85), (-0.9, 0.3, 0.85))):
        L = math.hypot(x1 - x0, y1 - y0)
        n = max(2, int(L / 0.45))
        for i in range(n):
            t = (i + 0.5) / n
            mb.box((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, z0 + (z1 - z0) * t), (1.0, L / n * 0.85, 0.07), "plank",
                   rotation_z=math.atan2(y1 - y0, x1 - x0) - math.pi / 2)
    for y in (-3.2, -2.0):
        for s in (-1, 1):
            mb.cylinder((0.3 + s * 0.55, y, -0.2), (0.3 + s * 0.55, y, 1.3 + (y + 3.2) * 0.2), 0.06, 0.05, "log", segments=5)
    # Lily pads with flowers, and cattails that sway.
    for i in range(9):
        a = rnd.uniform(0, TAU)
        r = rnd.uniform(2.3, 3.4)
        x, y = r * math.cos(a), 0.2 + r * math.sin(a)
        if abs(x - 0.3) < 0.9 and y < -1.0:
            continue
        mb.cylinder((x, y, 0.1), (x, y, 0.13), rnd.uniform(0.28, 0.45), 0.3, "leaf_light" if i % 2 else "leaf", segments=7)
        if i % 3 == 0:
            mb.cylinder((x, y, 0.13), (x, y, 0.28), 0.06, 0.15, "flowers", segments=6)
    names = []
    for i, (x, y) in enumerate(((3.3, -1.6), (3.5, 0.8), (-3.5, 1.6), (-3.0, -2.6), (1.6, 3.6), (-1.0, 3.8))):
        name = "reeds%d" % i
        with mb.bone(name):
            for k in range(3):
                ox, oy = 0.18 * math.cos(k * 2.1), 0.18 * math.sin(k * 2.1)
                hh = 1.5 + 0.25 * k
                mb.cylinder((x + ox, y + oy, 0), (x + ox, y + oy, hh), 0.025, 0.02, "moss", segments=4)
                mb.cylinder((x + ox, y + oy, hh - 0.35), (x + ox, y + oy, hh - 0.05), 0.06, 0.06, "bark_dark", segments=6)
                mb.cylinder((x + ox * 2, y + oy * 2, 0), (x + ox * 3.5, y + oy * 3.5, 0.9), 0.04, 0.0, "leaf", segments=4)
        rig.bone(name, (x, y, 0), (x, y, 1.0), None)
        names.append(name)
    rig.add("sway", 3.0, lambda t: {n: [(P.kit.X, 5 * math.sin(TAU * t + i)), (P.kit.Y, 3 * math.sin(TAU * t + 2 * i))]
                                    for i, n in enumerate(names)})
    # A fish trap, a drum, a lantern on a pole, a totem.
    mb.cylinder((2.4, -3.2, 0.25), (3.2, -3.4, 0.25), 0.25, 0.12, "thatch_dark", segments=7)
    mb.box((-1.2, -3.9, 1.0), (0.1, 0.1, 2.0), "log")
    mb.sphere((-1.2, -3.9, 2.15), 0.2, "glow", segments=6, rings=4)
    mb.cylinder((2.2, 3.1, 0), (2.2, 3.1, 1.8), 0.26, 0.2, "bark", segments=7)
    mb.sphere((2.2, 3.1, 1.95), 0.36, "moss", segments=7, rings=5, scale=(1.2, 1, 0.75))
    for s in (-1, 1):
        mb.sphere((2.2 + s * 0.2, 3.0, 2.2), 0.12, "glow", segments=5, rings=3)


def lizard_pyramid(mb, rig, seed=94):
    rnd = random.Random(seed)
    z = 0.0
    tiers = ((9.4, 1.5), (7.4, 1.4), (5.4, 1.3), (3.6, 1.2))
    for i, (w, h) in enumerate(tiers):
        mb.box((0, 0.3, z + h / 2), (w, w, h), "wall")
        mb.box((0, 0.3, z + h - 0.12), (w + 0.2, w + 0.2, 0.24), "wall_light")
        mb.box((0, 0.3, z + 0.14), (w + 0.12, w + 0.12, 0.28), "wall_dark")
        for side in P.SIDES:
            with P.face(mb, 0, 0.3, w, w, side) as L:
                P.scatter_face(mb, rnd, L - 1.0, z + 0.3, z + h - 0.3, density=0.3, size=(0.6, 0.3))
                if side != "front":
                    for k in range(int(w / 1.8)):
                        x = -L / 2 + (k + 0.5) * L / int(w / 1.8)
                        mb.box((x, -0.03, z + h * 0.55), (0.5, 0.08, 0.5), "wall_dark")
                        mb.box((x, -0.06, z + h * 0.55), (0.22, 0.08, 0.22), "band")
        z += h
    top = z
    # The stair up the front, between two ramps with serpent heads.
    fy = 0.3 - tiers[0][0] / 2
    run = fy - 0.9, 0.3 - tiers[-1][0] / 2
    n = 22
    for i in range(n):
        t0, t1 = i / n, (i + 1) / n
        y0 = run[0] + (run[1] - run[0]) * t0
        mb.box((0, (y0 + run[1]) / 2, top * t1 / 2), (2.2, run[1] - y0, top * t1), "wall_light" if i % 2 else "wall")
    for s in (-1, 1):
        P.prism_yz(mb, [(run[0] - 0.3, 0), (run[1], 0), (run[1], top + 0.35), (run[0] - 0.3, 0.5)], s * 1.1 - 0.25 + (0.25 if s > 0 else -0.25),
                   s * 1.1 + 0.25 + (0.25 if s > 0 else -0.25), "wall_dark")
        hx = s * 1.35
        mb.box((hx, run[0] - 0.7, 0.45), (0.7, 0.9, 0.7), "wall")
        mb.box((hx, run[0] - 1.25, 0.3), (0.55, 0.5, 0.32), "wall_light")
        for e in (-1, 1):
            mb.box((hx + e * 0.24, run[0] - 1.0, 0.68), (0.12, 0.14, 0.14), "gold")
            mb.cylinder((hx + e * 0.15, run[0] - 1.45, 0.2), (hx + e * 0.15, run[0] - 1.48, -0.02), 0.05, 0.0, "bone", segments=4)
    # The shrine on top, with a sun disc that turns, and braziers.
    mb.box((0, 0.5, top + 1.1), (2.6, 2.2, 2.2), "wall")
    mb.box((0, 0.5, top + 2.3), (3.0, 2.6, 0.3), "wall_light")
    mb.box((0, 0.5, top + 2.6), (2.2, 1.8, 0.3), "wall_dark")
    mb.box((0, -0.62, top + 0.9), (1.0, 0.1, 1.8), "charcoal")
    mb.box((0, -0.66, top + 1.95), (1.4, 0.14, 0.24), "gold")
    for s in (-1, 1):
        mb.box((s * 0.65, -0.66, top + 0.9), (0.24, 0.14, 1.8), "wall_light")
        mb.cylinder((s * 1.45, -1.1, top), (s * 1.45, -1.1, top + 0.8), 0.14, 0.24, "wall_dark", segments=6)
        mb.cylinder((s * 1.45, -1.1, top + 0.8), (s * 1.45, -1.1, top + 1.3), 0.2, 0.0, "ember", segments=6)
    with mb.bone("sun"):
        mb.cylinder((0, 0.56, top + 4.1), (0, 0.44, top + 4.1), 0.85, 0.85, "gold", segments=12)
        for i in range(8):
            a = TAU * i / 8
            mb.cylinder((0.85 * math.cos(a), 0.5, top + 4.1 + 0.85 * math.sin(a)), (1.35 * math.cos(a), 0.5, top + 4.1 + 1.35 * math.sin(a)),
                        0.16, 0.0, "gold", segments=4)
        mb.cylinder((0, 0.6, top + 4.1), (0, 0.4, top + 4.1), 0.4, 0.4, "lava", segments=10)
    mb.box((0, 0.5, top + 3.0), (0.3, 0.3, 0.6), "wall_dark")
    rig.bone("sun", (0, 0.5, top + 4.1), (0, -0.5, top + 4.1), None)
    rig.add("turn", 10.0, lambda t: {"sun": [(P.kit.Y, 360 * t)]})
    for sx in (-1, 1):
        with mb.placed((sx * 3.2, fy, 0)):
            P.wall_banner(mb, 0, 1.4, w=0.8, h=1.2, mat="banner", stripe="gold")
    # Palms at the back corners.
    for x, y in ((-4.4, 4.4), (4.3, 4.2)):
        prev = (x, y, 0.0)
        for i in range(1, 5):
            p = (x + 0.12 * i * i * (1 if x < 0 else -1) * 0.4, y, 1.1 * i)
            mb.cylinder(prev, p, 0.2 - 0.02 * i, 0.18 - 0.02 * i, "bark", segments=6)
            prev = p
        for k in range(6):
            a = TAU * k / 6
            mb.cylinder(prev, (prev[0] + 1.5 * math.cos(a), prev[1] + 1.5 * math.sin(a), prev[2] - 0.5), 0.3, 0.0, "leaf", segments=4)


def cat_tower_house(mb, rig, seed=96):
    rnd = random.Random(seed)
    cx, cy, w, h = 0.2, 0.6, 3.8, 7.6
    mb.box((cx, cy, 0.3), (w + 0.2, w + 0.2, 0.6), "stone")
    P.framed_block(mb, cx, cy, 0.6, w, w, h - 0.6, infill="plaster_warm", spacing=1.3)
    for z in (3.0, 5.3):
        mb.box((cx, cy, z), (w + 0.16, w + 0.16, 0.16), "timber")
    with P.face(mb, cx, cy, w, w, "front"):
        P.arched_door(mb, 0, 0.6, w=1.0, h=1.9, frame="timber")
        mb.box((0, -0.5, 0.3), (1.6, 0.9, 0.6), "stone")
        for z in (4.2, 6.5):
            mb.cylinder((0.9, 0.02, z), (0.9, -0.1, z), 0.45, 0.45, "timber", segments=10)
            mb.cylinder((0.9, 0.0, z), (0.9, -0.13, z), 0.34, 0.34, "glow", segments=10)

    def balcony(side, z, x=0.0, cloth=("stripe_a", "stripe_b")):
        with P.face(mb, cx, cy, w, w, side):
            mb.box((x, -0.7, z), (2.0, 1.4, 0.1), "plank")
            for s in (-1, 1):
                P.beam(mb, (x + s * 0.8, 0, z - 0.9), (x + s * 0.8, -1.25, z - 0.05), 0.08, "timber")
                mb.box((x + s * 0.95, -1.35, z + 0.45), (0.07, 0.07, 0.9), "timber")
                mb.box((x + s * 0.95, -0.7, z + 0.85), (0.06, 1.3, 0.06), "timber")
            mb.box((x, -1.35, z + 0.85), (2.0, 0.06, 0.06), "timber")
            mb.box((x, -0.02, z + 1.0), (0.9, 0.1, 1.8), "timber")
            mb.box((x, -0.05, z + 0.95), (0.7, 0.1, 1.6), "charcoal")
            for i in range(4):
                x0 = x - 1.1 + i * 0.55
                game.sloped_slab(mb, x0, x0 + 0.56, -1.55, 0.0, z + 1.9, z + 2.4, 0.05, cloth[i % 2])
            mb.sphere((x - 0.5, -0.8, z + 0.14), 0.26, "cloth_red", segments=6, rings=4, scale=(1, 1, 0.4))
            mb.sphere((x + 0.4, -0.5, z + 0.14), 0.22, "cloth_blue", segments=6, rings=4, scale=(1, 1, 0.4))

    balcony("left", 3.1)
    balcony("front", 5.4, x=-0.6, cloth=("banner2", "teal"))
    balcony("right", 3.9, cloth=("teal", "stripe_b"))
    # Plank ramps from one perch to the next.
    with P.face(mb, cx, cy, w, w, "left"):
        P.beam(mb, (1.6, -1.2, 0.1), (1.0, -1.2, 3.1), 0.09, "timber")
        for i in range(8):
            t = (i + 0.5) / 8
            mb.box((1.6 - 0.6 * t, -1.2, 0.1 + 3.0 * t), (0.5, 0.1, 0.05), "wood")
    # The roof terrace: a parapet, a pergola with cloth, cushions, and an onion-domed turret.
    mb.box((cx, cy, h + 0.08), (w + 0.5, w + 0.5, 0.16), "timber")
    for side in P.SIDES:
        with P.face(mb, cx, cy, w + 0.5, w + 0.5, side) as L:
            mb.box((0, 0.1, h + 0.5), (L, 0.2, 0.7), "plaster_warm")
            mb.box((0, 0.1, h + 0.88), (L + 0.05, 0.28, 0.08), "timber")
    for sx in (-1, 1):
        for sy in (-1, 0.2):
            mb.box((cx + sx * 1.5, cy + sy * 1.5, h + 1.4), (0.1, 0.1, 2.5), "timber")
    game.sloped_slab(mb, cx - 1.8, cx + 1.8, cy - 1.9, cy + 0.5, h + 2.75, h + 2.5, 0.05, "stripe_b")
    game.sloped_slab(mb, cx - 1.8, cx - 0.6, cy - 1.92, cy + 0.52, h + 2.78, h + 2.53, 0.05, "stripe_a")
    game.sloped_slab(mb, cx + 0.6, cx + 1.8, cy - 1.92, cy + 0.52, h + 2.78, h + 2.53, 0.05, "stripe_a")
    for i, c in enumerate(("cloth_red", "banner2", "cloth_blue")):
        mb.sphere((cx - 0.9 + i * 0.8, cy - 0.6, h + 0.3), 0.3, c, segments=6, rings=4, scale=(1, 1, 0.4))
    tx, ty = cx + 1.1, cy + 1.2
    mb.cylinder((tx, ty, h), (tx, ty, h + 2.6), 0.75, 0.75, "plaster_warm", segments=10)
    round_window(mb, tx, ty, 0.72, -math.pi / 2, h + 1.6, w=0.3, h=0.6, glass="glow", frame="timber")
    mb.cylinder((tx, ty, h + 2.6), (tx, ty, h + 2.75), 0.9, 0.9, "timber", segments=10)
    for i, (r0, r1, dz) in enumerate(((0.85, 1.0, 0.5), (1.0, 0.75, 0.5), (0.75, 0.3, 0.5), (0.3, 0.0, 0.9))):
        z0 = h + 2.75 + sum(q[2] for q in ((0.85, 1.0, 0.5), (1.0, 0.75, 0.5), (0.75, 0.3, 0.5), (0.3, 0.0, 0.9))[:i])
        mb.cylinder((tx, ty, z0), (tx, ty, z0 + dz), r0, r1, "teal" if i % 2 else "teal_dark", segments=10)
    mb.sphere((tx, ty, h + 5.2), 0.1, "gold", segments=6, rings=4)
    # At the foot: a fish rack, cushions, baskets, a lantern.
    for x in (-2.6, -1.6):
        mb.box((x, -2.4, 0.8), (0.07, 0.07, 1.6), "timber")
    mb.cylinder((-2.65, -2.4, 1.5), (-1.55, -2.4, 1.5), 0.03, 0.03, "wood", segments=5)
    for k in range(4):
        mb.box((-2.45 + k * 0.25, -2.4, 1.28), (0.09, 0.04, 0.38), "fish")
    mb.cylinder((2.4, -2.2, 0), (2.4, -2.2, 0.4), 0.3, 0.36, "thatch_dark", segments=8)
    mb.sphere((2.4, -2.2, 0.42), 0.27, "cloth_red", segments=6, rings=4, scale=(1, 1, 0.5))
    mb.sphere((1.7, -2.6, 0.22), 0.22, "cloth_white", segments=7, rings=5)
    mb.box((-2.9, -0.4, 1.0), (0.08, 0.08, 2.0), "timber")
    mb.box((-2.9, -0.65, 1.9), (0.08, 0.5, 0.06), "timber")
    mb.sphere((-2.9, -0.85, 1.6), 0.18, "glow", segments=6, rings=4, scale=(1, 1, 1.3))


def dark_elf_spire(mb, rig, seed=98):
    rnd = random.Random(seed)

    def spire(x, y, r, h, lean=(0.0, 0.0), glow=3):
        tipx, tipy = x + lean[0], y + lean[1]
        mb.cylinder((x, y, 0), (x + lean[0] * 0.55, y + lean[1] * 0.55, h * 0.6), r, r * 0.72, "wall", segments=6)
        mb.cylinder((x + lean[0] * 0.55, y + lean[1] * 0.55, h * 0.6), (tipx, tipy, h), r * 0.72, 0.0, "wall_dark", segments=6)
        mb.cylinder((x, y, 0), (x, y, 0.8), r + 0.35, r + 0.1, "wall_dark", segments=6)
        for i in range(glow):
            a = -math.pi / 2 + (i - (glow - 1) / 2) * 1.05
            z = h * (0.2 + 0.13 * i)
            k = z / (h * 0.6)
            rr = (r + (r * 0.72 - r) * min(1, k)) * 0.87
            mb.box((x + lean[0] * 0.55 * k + rr * math.cos(a), y + lean[1] * 0.55 * k + rr * math.sin(a), z), (0.16, 0.2, 1.3), "magic",
                   rotation_z=a)
        for i in range(3):  # Shards growing from the flanks.
            a = rnd.uniform(0, TAU)
            z = rnd.uniform(h * 0.25, h * 0.55)
            mb.cylinder((x + r * 0.6 * math.cos(a), y + r * 0.6 * math.sin(a), z),
                        (x + (r + 0.9) * math.cos(a), y + (r + 0.9) * math.sin(a), z + 1.6), 0.25, 0.0, "wall_light", segments=5)
        return tipx, tipy

    spire(0.0, 0.8, 1.7, 17.0, glow=3)
    spire(-2.3, -0.4, 1.0, 10.0, lean=(-0.5, -0.2), glow=2)
    spire(2.2, 0.2, 1.1, 12.0, lean=(0.5, 0.0), glow=2)
    spire(0.6, 2.9, 0.8, 8.0, lean=(0.2, 0.5), glow=1)
    # The door: a pointed arch that glows.
    with mb.placed((0, 0.8 - 1.7 * 0.87 - 0.02, 0)):
        P.prism_xz(mb, [(-0.75, 0), (0.75, 0), (0.75, 1.7), (0, 2.9), (-0.75, 1.7)], -0.16, 0.1, "trim")
        P.prism_xz(mb, [(-0.5, 0), (0.5, 0), (0.5, 1.6), (0, 2.45), (-0.5, 1.6)], -0.2, 0.0, "magic")
        mb.box((0, -0.7, 0.1), (1.8, 1.4, 0.2), "wall_dark")
    # A bridge between two spires, high up.
    P.beam(mb, (-2.5, -0.5, 6.4), (0, 0.6, 7.2), 0.3, "wall_dark")
    P.beam(mb, (2.4, 0.2, 8.0), (0.2, 0.8, 8.8), 0.3, "wall_dark")
    for (ax, ay, az), (bx, by, bz) in (((-2.5, -0.5, 6.4), (0, 0.6, 7.2)), ((2.4, 0.2, 8.0), (0.2, 0.8, 8.8))):
        for t in (0.3, 0.5, 0.7):
            mb.cylinder((ax + (bx - ax) * t, ay + (by - ay) * t, az + (bz - az) * t - 0.2),
                        (ax + (bx - ax) * t, ay + (by - ay) * t, az + (bz - az) * t - 1.0), 0.12, 0.0, "wall_light", segments=4)
    # A balcony ring on the great spire and banners.
    mb.cylinder((0.0, 0.8, 9.6), (0.0, 0.8, 9.8), 2.0, 2.2, "wall_dark", segments=6)
    railing_ring(mb, 0.0, 0.8, 9.8, 2.05, n=6, h=0.8, post="trim", rail="trim")
    P.flag(mb, rig, -2.8, -0.6, 9.2, pole=1.8, length=1.6, height=0.9, mat="purple", stripe="magic")
    P.flag(mb, rig, 2.7, 0.2, 11.2, pole=1.8, length=1.6, height=0.9, mat="purple", stripe="magic")
    # Shards of crystal that float around the tip.
    with mb.bone("shards"):
        for i in range(5):
            a = TAU * i / 5
            x, y, z = 2.4 * math.cos(a), 0.8 + 2.4 * math.sin(a), 14.6 + 0.5 * math.sin(i * 2.0)
            mb.cylinder((x, y, z), (x, y, z + 0.8), 0.22, 0.0, "magic", segments=5)
            mb.cylinder((x, y, z), (x, y, z - 0.6), 0.22, 0.0, "crystal", segments=5)
    rig.bone("shards", (0, 0.8, 14.6), (0, 0.8, 15.6), None)
    rig.add("float", 8.0, lambda t: ({"shards": [(P.kit.Z, 360 * t)]}, {"shards": (0, 0, 0.35 * math.sin(TAU * 2 * t))}))
    # Jagged rock and mushrooms that glow at the foot.
    for i in range(12):
        a = rnd.uniform(0, TAU)
        r = rnd.uniform(2.6, 3.4)
        mb.cylinder((r * math.cos(a), 0.6 + r * math.sin(a), 0), (r * 1.08 * math.cos(a), 0.6 + r * 1.08 * math.sin(a), rnd.uniform(0.8, 2.2)),
                    rnd.uniform(0.3, 0.55), 0.0, rnd.choice(("wall_dark", "wall", "wall_light")), segments=5)
    for x, y in ((-1.6, -2.6), (1.4, -2.8), (2.0, -2.3), (-2.2, -2.2)):
        mb.cylinder((x, y, 0), (x, y, 0.3), 0.05, 0.04, "bone", segments=5)
        mb.cylinder((x, y, 0.3), (x, y, 0.45), 0.2, 0.03, "magic", segments=6)


def dwarf_house(mb, rig, seed=99):
    rnd = random.Random(seed)
    # A squat house of great stones under a slab roof covered with turf.
    cx, cy, w, d, h = 0.0, 0.8, 5.2, 4.2, 2.3
    P.stone_block(mb, cx, cy, 0, w, d, h, rnd, density=0.45, plinth=0.5)
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = cx + sx * w / 2, cy + sy * d / 2
            butt = mb.prism([(x - 0.5, y - 0.5), (x + 0.5, y - 0.5), (x + 0.5, y + 0.5), (x - 0.5, y + 0.5)], 0.0, h + 0.1, "wall_dark")
            for v in butt:
                if v.co.z > 1.0:
                    v.co.x = x + (v.co.x - x) * 0.55
                    v.co.y = y + (v.co.y - y) * 0.55
    mb.box((cx, cy, h + 0.12), (w + 0.7, d + 0.7, 0.24), "wall_dark")
    P.pyramid_roof(mb, cx, cy, h + 0.24, w + 0.3, d + 0.3, 1.1, ("wall", "wall_dark"), rows=3, overhang=0.2, ridge=1.6)
    mb.box((cx, cy, h + 1.3), (2.2, 1.0, 0.16), "grass")
    for i in range(6):
        mb.sphere((cx + rnd.uniform(-1.6, 1.6), cy + rnd.uniform(-1.2, 1.2), h + 0.9), rnd.uniform(0.3, 0.5), "grass_dark" if i % 2 else "grass",
                  segments=5, rings=3, scale=(1, 1, 0.4))
    with P.face(mb, cx, cy, w, d, "front"):
        P.arched_door(mb, 0, 0.05, w=1.2, h=1.7, frame="wall_light", iron="gold")
        for x in (-1.7, 1.7):
            mb.box((x, -0.03, 1.3), (0.7, 0.14, 0.7), "wall_light")
            mb.box((x, -0.07, 1.3), (0.44, 0.12, 0.44), "lava")
            mb.box((x, -0.14, 1.3), (0.44, 0.03, 0.05), "iron")
            mb.box((x, -0.14, 1.3), (0.05, 0.03, 0.44), "iron")
        mb.box((0, -0.04, 2.05), (w - 0.6, 0.08, 0.14), "gold")
        for i in range(7):
            mb.box((-1.8 + i * 0.6, -0.09, 2.05), (0.1, 0.04, 0.28), "gold")
    mb.box((cx + 1.6, cy + 0.9, h + 1.3), (0.9, 0.9, 2.0), "wall_dark")
    mb.box((cx + 1.6, cy + 0.9, h + 2.36), (1.1, 1.1, 0.14), "wall")
    mb.box((cx + 1.6, cy + 0.9, h + 2.45), (0.6, 0.6, 0.06), "ember")
    # Outside: an anvil, kegs, a stone bench, an ore barrow.
    ax, ay = -2.6, -2.2
    mb.box((ax, ay, 0.3), (0.6, 0.5, 0.6), "wall_dark")
    mb.box((ax, ay, 0.68), (0.6, 0.26, 0.16), "iron")
    mb.cylinder((ax + 0.3, ay, 0.7), (ax + 0.6, ay, 0.72), 0.1, 0.0, "iron", segments=6)
    for x, y in ((2.2, -1.9), (2.8, -2.1), (2.5, -1.4)):
        game.barrel(mb, x, y, h=0.8, r=0.32)
    mb.box((0.9, -2.6, 0.42), (1.6, 0.45, 0.1), "wall_light")
    for s in (-0.6, 0.6):
        mb.box((0.9 + s, -2.6, 0.2), (0.14, 0.4, 0.4), "wall_dark")
    P.rocks(mb, rnd, -3.2, 0.6, 0.7, n=5, mats=("rock_dark", "gold", "rock"), size=0.4)


def lizard_house(mb, rig, seed=97):
    rnd = random.Random(seed)
    # A reed house on stilts with a steep palm roof and a sun terrace.
    z0 = 1.1
    cx, cy, w, d, h = -0.6, 1.0, 4.2, 3.4, 2.0
    for x in (-2.9, -0.6, 1.7, 3.6):
        for y in (-1.6, 1.0, 2.8):
            mb.cylinder((x, y, 0), (x, y, z0), 0.11, 0.1, "bark", segments=6)
    mb.box((0.4, 0.6, z0 + 0.06), (7.0, 4.8, 0.12), "plank")
    mb.box((cx, cy, z0 + 0.12 + h / 2), (w, d, h), "thatch_dark")
    for side in P.SIDES:
        with P.face(mb, cx, cy, w, d, side) as L:
            n = int(L / 0.6)
            for i in range(n + 1):
                mb.cylinder((-L / 2 + i * L / n, 0, z0 + 0.12), (-L / 2 + i * L / n, 0, z0 + 0.12 + h), 0.05, 0.05, "tusk", segments=5)
            for z in (z0 + 0.5, z0 + 1.3):
                mb.box((0, -0.02, z), (L, 0.06, 0.06), "rope")
    with P.face(mb, cx, cy, w, d, "front"):
        mb.box((0.4, -0.04, z0 + 1.0), (1.0, 0.1, 1.7), "charcoal")
        mb.box((0.4, -0.08, z0 + 1.9), (1.3, 0.1, 0.14), "bark")
        for i, c in enumerate(("band", "banner2", "teal")):
            mb.box((0.0 + i * 0.4, -0.1, z0 + 1.6), (0.3, 0.03, 0.5), c)
        mb.cylinder((-1.2, 0.02, z0 + 1.2), (-1.2, -0.1, z0 + 1.2), 0.3, 0.3, "gold", segments=8)
    with mb.placed((cx, cy, 0), math.pi / 2):   # The gable, and the door under it, face the front.
        P.gable_roof(mb, 0, 0, d, w, z0 + 0.12 + h, 3.0, ("thatch", "leaf_dark", "thatch"), rows=6, overhang=0.5, gable="thatch_dark",
                     end_overhang=0.7, barge="bark")
    # The basking terrace: a flat warm rock, clay jars, drying fish, a ramp.
    mb.box((2.7, 0.4, z0 + 0.3), (1.6, 2.0, 0.3), "rock")
    mb.box((2.7, 0.4, z0 + 0.46), (1.3, 1.6, 0.06), "sand")
    for x, y in ((3.4, 2.4), (2.8, 2.6)):
        mb.cylinder((x, y, z0 + 0.12), (x, y, z0 + 0.6), 0.16, 0.26, "clay", segments=7)
        mb.cylinder((x, y, z0 + 0.6), (x, y, z0 + 0.7), 0.26, 0.14, "clay", segments=7)
    for x in (2.0, 3.6):
        mb.box((x, -1.6, z0 + 0.9), (0.07, 0.07, 1.6), "bark")
    mb.cylinder((1.95, -1.6, z0 + 1.6), (3.65, -1.6, z0 + 1.6), 0.025, 0.025, "rope", segments=4)
    for i in range(5):
        mb.box((2.2 + i * 0.3, -1.6, z0 + 1.38), (0.09, 0.04, 0.38), "fish")
    P.prism_yz(mb, [(-3.6, 0.0), (-1.7, z0 + 0.02), (-1.7, z0 + 0.12), (-3.6, 0.1)], -1.2, 0.0, "plank")
    for i in range(5):
        t = (i + 0.5) / 5
        mb.box((-0.6, -3.6 + 1.9 * t, 0.08 + (z0 + 0.04) * t), (1.2, 0.08, 0.06), "bark")
    # Feathered totems and a palm.
    for i, x in enumerate((-3.4, 4.4)):
        mb.cylinder((x, -2.6, 0), (x, -2.6, 2.6), 0.14, 0.1, "bark", segments=6)
        mb.box((x, -2.68, 2.0), (0.34, 0.1, 0.5), "gold" if i else "teal")
        for k, c in enumerate(("band", "banner2", "teal")):
            mb.cylinder((x, -2.6, 2.6), (x + (k - 1) * 0.35, -2.6, 3.3), 0.07, 0.0, c, segments=4)
    px, py = 4.2, 3.0
    prev = (px, py, 0.0)
    for i in range(1, 6):
        p = (px - 0.08 * i * i, py, 1.0 * i)
        mb.cylinder(prev, p, 0.2 - 0.02 * i, 0.18 - 0.02 * i, "bark", segments=6)
        prev = p
    for k in range(7):
        a = TAU * k / 7
        mb.cylinder(prev, (prev[0] + 1.6 * math.cos(a), prev[1] + 1.6 * math.sin(a), prev[2] - 0.5), 0.3, 0.0, "leaf", segments=4)


def make(name, fn, colors, **kw):
    def build():
        mb = P.begin()
        rig = P.Rig()
        fn(mb, rig, **kw)
        P.finish(mb, name, colors, rig)
    return build


OBSIDIAN = dict(wall=0x3A3446, wall_dark=0x282430, wall_light=0x5A4E72, trim=0x1E1A24, magic=0xC050E0, crystal=0xE090F0,
                purple=0x5B2A7A)
JUNGLE = dict(wall=0xC8B487, wall_dark=0xA89468, wall_light=0xDCCBA0, banner=0x2E7A5A)

MODELS = {
    "bld_fox_burrow": make("bld_fox_burrow", fox_burrow, P.BASE),
    "bld_frog_pond_house": make("bld_frog_pond_house", frog_pond_house, P.BASE),
    "bld_lizard_pyramid": make("bld_lizard_pyramid", lizard_pyramid, P.palette(**JUNGLE)),
    "bld_lizard_pyramid_mossy": make("bld_lizard_pyramid_mossy", lizard_pyramid,
                                     P.palette(wall=0x8A9278, wall_dark=0x6A7458, wall_light=0xA4AC90, banner=0x8E2A24)),
    "bld_cat_tower_house": make("bld_cat_tower_house", cat_tower_house, P.BASE),
    "bld_dark_elf_spire": make("bld_dark_elf_spire", dark_elf_spire, P.palette(**OBSIDIAN)),
    "bld_dwarf_house": make("bld_dwarf_house", dwarf_house, P.palette(wall=0x8E8A84, wall_dark=0x6E6A66, wall_light=0xA8A49C)),
    "bld_lizard_house": make("bld_lizard_house", lizard_house, P.BASE),
}
