"""Industry: a quarry with a crane, a bottle kiln, a blast furnace driven by
a water wheel, an apiary and a fire watch station."""

import math
import random

import parts as P
from civic import storey
from mills import water_wheel, mill_race, sack
from mathutils import Matrix
from parts import game, TAU


def jib_crane(mb, rig, mx, my, z0=0.0, h=4.6, reach=3.0, load="stone", clip="load", swing=60.0, start=-90.0):
    """A mast with a jib that swings its load (clip `load`). The jib points
    toward `start` degrees (0 = +X) and swings `swing` degrees from there."""
    mb.box((mx, my, z0 + 0.2), (1.3, 1.3, 0.4), "timber")
    mb.box((mx, my, z0 + h / 2), (0.3, 0.3, h), "timber")
    for a in range(4):
        c, s = math.cos(a * math.pi / 2 + 0.78), math.sin(a * math.pi / 2 + 0.78)
        P.beam(mb, (mx + 1.0 * c, my + 1.0 * s, z0 + 0.3), (mx, my, z0 + 2.0), 0.1, "timber")
    name = rig.name("jib")
    a0 = math.radians(start)
    c, s = math.cos(a0), math.sin(a0)
    tip = (mx + reach * c, my + reach * s, z0 + h + 0.8)
    with mb.bone(name):
        P.beam(mb, (mx, my, z0 + h - 1.2), tip, 0.16, "timber")
        P.beam(mb, (mx, my, z0 + h), (mx + reach * 0.55 * c, my + reach * 0.55 * s, z0 + h + 0.05), 0.08, "timber")
        mb.sphere(tip, 0.2, "wood", segments=6, rings=4)
        mb.box((tip[0], tip[1], tip[2] - 1.4), (0.04, 0.04, 2.8), "rope")
        if load == "stone":
            mb.box((tip[0], tip[1], tip[2] - 3.1), (0.9, 0.7, 0.6), "wall_light")
        else:
            mb.box((tip[0], tip[1], tip[2] - 3.1), (0.7, 0.7, 0.6), "wood_light")
        for sx in (-1, 1):
            P.beam(mb, (tip[0], tip[1], tip[2] - 2.5), (tip[0] + sx * 0.4, tip[1], tip[2] - 2.82), 0.025, "rope")
        P.beam(mb, tip, (mx, my, z0 + h - 2.0), 0.03, "rope")
    head = mb.world((mx, my, z0 + h - 1.2))
    rig.bone(name, head, head + P.Vector((0, 0, 1)), None)
    rig.add(clip, 6.0, lambda t: {name: [(P.kit.Z, swing * (0.5 - 0.5 * math.cos(TAU * t)))]})


def quarry(mb, rig, seed=100):
    rnd = random.Random(seed)
    # The worked face: three benches cut into the rock, each stepped back.
    for i, (y0, z1) in enumerate(((0.6, 2.2), (2.2, 4.4), (3.8, 6.4))):
        mb.box((0, (y0 + 5.0) / 2, z1 / 2), (11.6, 5.0 - y0, z1), "rock")
        mb.box((0, y0 + 0.02, z1 - 1.0), (11.6, 0.06, 2.0), "wall")
        for k in range(9):
            x = -5.4 + k * 1.3 + rnd.uniform(-0.2, 0.2)
            mb.box((x, y0 - 0.02, z1 - rnd.uniform(0.5, 1.6)), (0.05, 0.08, rnd.uniform(0.8, 1.8)), "rock_dark")
        for k in range(4):
            x = rnd.uniform(-5.0, 5.0)
            s = rnd.uniform(0.5, 0.9)
            mb.box((x, y0 + 0.6, z1 + s * 0.3), (s * 1.4, s, s * 0.6), "wall" if k % 2 else "wall_light", rotation_z=rnd.uniform(-0.3, 0.3))
    for _ in range(12):
        x = rnd.choice((-1, 1)) * rnd.uniform(4.6, 5.9)
        mb.sphere((x, rnd.uniform(1.0, 4.6), rnd.uniform(0.5, 5.0)), rnd.uniform(1.0, 1.6), rnd.choice(("rock", "rock_dark")), segments=6,
                  rings=4, scale=(0.8, 1, 1.1))
    mb.sphere((0, 5.2, 5.6), 2.2, "grass", segments=7, rings=4, scale=(2.8, 0.5, 0.35))
    # Ladders between the benches.
    for x, y0, z0, z1 in ((-3.2, 0.5, 0.0, 2.2), (2.6, 2.1, 2.2, 4.4)):
        for s in (-0.25, 0.25):
            P.beam(mb, (x + s, y0 - 0.5, z0), (x + s, y0 - 0.05, z1 + 0.5), 0.05, "timber")
        for k in range(6):
            t = (k + 0.5) / 6
            mb.box((x, y0 - 0.5 + 0.45 * t, z0 + (z1 + 0.5 - z0) * t), (0.5, 0.05, 0.05), "wood")
    # The crane, lifting a block from the first bench down to the yard.
    jib_crane(mb, rig, 1.0, -0.9, h=4.8, reach=2.6, start=75.0, swing=-150.0)
    # Dressed blocks, a sledge on rollers, a shed and tools.
    for i, (x, y, zz) in enumerate(((-3.6, -2.6, 0), (-2.5, -2.7, 0), (-3.1, -2.65, 0.6), (-4.6, -1.4, 0), (4.0, -3.4, 0))):
        mb.box((x, y, zz + 0.3), (1.0, 0.7, 0.6), "wall_light" if i % 2 else "wall")
    with mb.placed((3.6, -1.8, 0), 0.2):
        for k in range(3):
            mb.cylinder((-0.7 + k * 0.7, -0.5, 0.1), (-0.7 + k * 0.7, 0.5, 0.1), 0.1, 0.1, "log", segments=6)
        mb.box((0, 0, 0.26), (2.0, 0.8, 0.12), "plank")
        mb.box((0, 0, 0.62), (1.2, 0.7, 0.6), "wall_light")
    with mb.placed((-4.6, -3.6, 0)):
        for sx in (-1, 1):
            mb.box((sx * 0.9, -0.6, 1.0), (0.12, 0.12, 2.0), "timber")
            mb.box((sx * 0.9, 0.6, 1.3), (0.12, 0.12, 2.6), "timber")
        game.sloped_slab(mb, -1.2, 1.2, -0.9, 0.8, 2.0, 2.65, 0.08, "shingle")
        mb.box((0, 0.6, 1.0), (1.8, 0.06, 2.0), "plank")
        mb.box((0, 0, 0.4), (1.4, 0.5, 0.06), "wood")
        for s in (-0.6, 0.6):
            mb.box((s, 0, 0.2), (0.07, 0.45, 0.4), "timber")
    for i in range(3):
        mb.box((-0.9 + i * 0.25, -3.8, 0.55), (0.05, 0.05, 1.1), "wood")
        mb.box((-0.9 + i * 0.25, -3.8, 1.1), (0.3, 0.08, 0.1), "iron")
    P.rocks(mb, rnd, 1.5, -3.6, 0.9, n=7, size=0.45)


def bottle_kiln(mb, rig, seed=102):
    rnd = random.Random(seed)
    x, y = -1.6, 0.8
    mb.cylinder((x, y, 0), (x, y, 0.5), 2.5, 2.4, "wall_dark", segments=14)
    mb.cylinder((x, y, 0.5), (x, y, 2.8), 2.3, 2.3, "brick", segments=14)
    mb.cylinder((x, y, 2.8), (x, y, 6.0), 2.3, 1.1, "brick", segments=14)
    mb.cylinder((x, y, 6.0), (x, y, 7.6), 1.1, 0.85, "brick", segments=14)
    mb.cylinder((x, y, 7.6), (x, y, 7.8), 0.95, 0.95, "brick_dark", segments=14)
    mb.cylinder((x, y, 7.78), (x, y, 7.82), 0.7, 0.7, "charcoal", segments=10)
    for z, r in ((1.2, 2.33), (2.6, 2.33), (4.4, 1.72), (6.0, 1.12)):
        mb.cylinder((x, y, z - 0.06), (x, y, z + 0.06), r, r, "iron", segments=14)
    for _ in range(26):
        a, z = rnd.uniform(0, TAU), rnd.uniform(0.7, 2.6)
        q = 2.3 * math.cos(math.pi / 14) + 0.01
        mb.box((x + q * math.cos(a), y + q * math.sin(a), z), (0.14, rnd.uniform(0.35, 0.6), 0.2), rnd.choice(("brick_dark", "brick_light")),
               rotation_z=a)
    for i in range(6):  # Fire mouths around the base.
        a = -math.pi / 2 + TAU * i / 6
        q = 2.3 * math.cos(math.pi / 14)
        mb.box((x + q * math.cos(a), y + q * math.sin(a), 0.95), (0.3, 0.8, 0.9), "brick_dark", rotation_z=a)
        mb.box((x + (q + 0.08) * math.cos(a), y + (q + 0.08) * math.sin(a), 0.85), (0.3, 0.5, 0.6), "ember" if i % 2 == 0 else "charcoal",
               rotation_z=a)
    with mb.placed((x, y - 2.3 * math.cos(math.pi / 14) - 0.02, 0)):
        pass
    # The drying shed: racks of bricks and tiles under an open roof.
    sx, sy, w, d = 2.6, 1.6, 3.6, 4.4
    for ax in (-1, 1):
        for ay in (-1, 0, 1):
            mb.box((sx + ax * w / 2, sy + ay * d / 2, 1.2), (0.16, 0.16, 2.4), "timber")
    with mb.placed((sx, sy, 0), math.pi / 2):
        P.gable_roof(mb, 0, 0, d, w, 2.4, 1.2, ("tile_red", "tile_red_dark"), rows=4, overhang=0.4, gable=None, barge="timber")
    for r in range(3):
        mb.box((sx, sy, 0.5 + r * 0.6), (w - 0.5, d - 0.4, 0.06), "plank")
        for k in range(6):
            yy = sy - d / 2 + 0.5 + k * 0.65
            mb.box((sx - 0.7, yy, 0.62 + r * 0.6), (0.9, 0.4, 0.16), "brick" if (k + r) % 2 else "clay")
            mb.box((sx + 0.7, yy, 0.62 + r * 0.6), (0.9, 0.4, 0.16), "tile_red" if (k + r) % 2 else "clay")
    # Stacks of fired bricks and tiles, the clay heap, a barrow, firewood.
    for i, (bx, by) in enumerate(((1.6, -2.4), (2.8, -2.5), (4.0, -2.4))):
        for r in range(3 - (i == 2)):
            mb.box((bx, by, 0.12 + r * 0.24), (1.0, 0.7, 0.22), ("brick", "brick_dark")[r % 2] if i < 2 else "tile_red")
    mb.sphere((-3.6, -2.8, 0), 1.0, "clay", segments=7, rings=4, scale=(1.3, 1, 0.55))
    mb.box((-3.2, -2.2, 0.5), (0.06, 0.06, 1.0), "wood")
    with mb.placed((-1.2, -3.2, 0), 0.5):
        tub = mb.prism([(-0.5, -0.35), (0.5, -0.35), (0.5, 0.35), (-0.5, 0.35)], 0.35, 0.7, "plank")
        for v in tub:
            if v.co.z < 0.5:
                v.co.x *= 0.6
                v.co.y *= 0.7
        mb.sphere((0, 0, 0.7), 0.3, "clay", segments=6, rings=4, scale=(1.3, 0.9, 0.5))
        mb.cylinder((-0.5, -0.06, 0.25), (-0.5, 0.06, 0.25), 0.25, 0.25, "wood", segments=8)
        for s in (-1, 1):
            P.beam(mb, (0.4, s * 0.3, 0.5), (1.2, s * 0.3, 0.6), 0.04, "timber")
            mb.box((0.3, s * 0.3, 0.17), (0.05, 0.05, 0.35), "timber")
    game.log_pile(mb, -4.2, 2.6, length=1.6, rows=3)


def blast_furnace(mb, rig, seed=104):
    rnd = random.Random(seed)
    x, y, w, h = 0.2, 1.4, 4.4, 7.0
    stack = mb.prism([(x - w / 2, y - w / 2), (x + w / 2, y - w / 2), (x + w / 2, y + w / 2), (x - w / 2, y + w / 2)], 0.0, h, "wall")
    for v in stack:
        if v.co.z > h / 2:
            v.co.x = x + (v.co.x - x) * 0.62
            v.co.y = y + (v.co.y - y) * 0.62
    mb.box((x, y, 0.4), (w + 0.4, w + 0.4, 0.8), "wall_dark")
    for z in (2.2, 4.2, 6.0):
        k = 1 - 0.38 * z / h
        mb.box((x, y, z), (w * k + 0.12, w * k + 0.12, 0.2), "timber")
        for sx in (-1, 1):
            for sy in (-1, 1):
                mb.box((x + sx * (w * k / 2 + 0.04), y + sy * (w * k / 2 + 0.04), z), (0.14, 0.14, 0.34), "iron")
    mb.box((x, y, h + 0.25), (w * 0.62 + 0.3, w * 0.62 + 0.3, 0.5), "brick")
    mb.box((x, y, h + 0.52), (w * 0.45, w * 0.45, 0.06), "ember")
    for i in range(14):
        zz = rnd.uniform(1.0, 6.4)
        k = 1 - 0.38 * zz / h
        side = rnd.choice(P.SIDES)
        with P.face(mb, x, y, w * k, w * k, side) as L:
            mb.box((rnd.uniform(-L / 2 + 0.5, L / 2 - 0.5), 0, zz), (rnd.uniform(0.4, 0.7), 0.08, 0.28), rnd.choice(("wall_dark", "wall_light")))
    # The casting arch and the house in front, with a runner of molten iron and pigs in the sand.
    fy = y - w / 2
    mb.box((x, fy - 0.02, 1.0), (1.6, 0.2, 1.6), "charcoal")
    mb.cylinder((x, fy + 0.08, 1.8), (x, fy - 0.12, 1.8), 0.8, 0.8, "charcoal", segments=10)
    mb.box((x, fy - 0.1, 0.5), (0.5, 0.2, 0.5), "lava")
    for sx in (-1, 1):
        mb.box((x + sx * 2.3, fy - 2.6, 1.5), (0.2, 0.2, 3.0), "timber")
        mb.box((x + sx * 2.3, fy - 0.2, 1.9), (0.2, 0.2, 3.8), "timber")
    game.sloped_slab(mb, x - 2.7, x + 2.7, fy - 3.0, fy + 0.1, 2.9, 3.9, 0.1, "shingle")
    game.sloped_slab(mb, x - 2.7, x + 2.7, fy - 3.0, fy - 2.0, 2.95, 3.3, 0.1, "shingle_dark")
    mb.box((x, fy - 1.5, 0.05), (4.4, 2.8, 0.1), "sand_dark")
    mb.box((x, fy - 1.0, 0.12), (0.2, 1.8, 0.06), "lava")
    for i in range(5):
        mb.box((x - 1.2 + i * 0.6, fy - 2.0, 0.12), (0.3, 0.9, 0.08), "lava" if i < 2 else "iron")
    mb.box((x, fy - 1.95, 0.12), (2.8, 0.14, 0.06), "lava")
    # The charging bridge from the bank behind to the furnace top.
    bx0, bx1 = x - 0.9, x + 0.9
    P.prism_yz(mb, [(y + w * 0.31, h - 0.2), (y + 4.4, h - 0.2), (y + 4.4, h), (y + w * 0.31, h)], bx0, bx1, "plank")
    for yy in (y + 2.6, y + 4.3):
        for sx in (-1, 1):
            mb.box((x + sx * 0.85, yy, (h - 0.2) / 2), (0.2, 0.2, h - 0.2), "timber")
        P.beam(mb, (x - 0.85, yy, 0.4), (x + 0.85, yy, h - 1.0), 0.09, "timber")
    for sx in (-1, 1):
        mb.box((x + sx * 0.85, y + 3.0, h + 0.5), (0.06, 2.8, 0.06), "timber")
        for yy in (y + 1.7, y + 3.0, y + 4.3):
            mb.box((x + sx * 0.85, yy, h + 0.25), (0.07, 0.07, 0.5), "timber")
    with mb.placed((x, y + 3.6, h)):
        tub = mb.prism([(-0.4, -0.5), (0.4, -0.5), (0.4, 0.5), (-0.4, 0.5)], 0.2, 0.7, "plank_dark")
        mb.sphere((0, 0, 0.7), 0.35, "charcoal", segments=6, rings=4, scale=(0.9, 1.2, 0.5))
    # The wheel on the left that works the bellows.
    wx = x + w / 2 + 2.0
    mill_race(mb, wx, -3.6, 4.6, w=1.2, wheel=y - 0.6)
    water_wheel(mb, rig, wx, y, 1.9, 1.75, width=0.9)
    mb.box((wx - 0.95, y, 0.95), (0.3, 0.5, 1.9), "timber")
    mb.box((wx + 0.9, y, 0.95), (0.3, 0.5, 1.9), "timber")
    bxc, byc, bz = x + w / 2 + 0.45, y - 1.5, 1.0
    mb.box((bxc, byc, bz - 0.55), (0.9, 1.4, 0.9), "timber")
    P.prism_yz(mb, [(byc + 0.75, bz - 0.07), (byc - 0.75, bz - 0.2), (byc - 0.75, bz - 0.12), (byc + 0.75, bz)], bxc - 0.4, bxc + 0.4, "wood")
    P.prism_yz(mb, [(byc + 0.7, bz), (byc - 0.7, bz - 0.12), (byc - 0.7, bz + 0.22), (byc + 0.7, bz + 0.05)], bxc - 0.34, bxc + 0.34, "hide")
    with mb.bone("bellows"):
        P.prism_yz(mb, [(byc + 0.75, bz + 0.04), (byc - 0.75, bz + 0.28), (byc - 0.75, bz + 0.36), (byc + 0.75, bz + 0.11)], bxc - 0.4,
                   bxc + 0.4, "wood")
    head = mb.world((bxc, byc + 0.75, bz + 0.05))
    axis = mb.world_dir((1, 0, 0))
    rig.bone("bellows", head, mb.world((bxc, byc - 0.3, bz + 0.2)), None)
    rig.add("turn", 6.0, lambda t: {"bellows": [(axis, -5 - 7 * math.sin(TAU * 4 * t))]})
    # Heaps of ore and charcoal, and bars of iron.
    mb.sphere((x - 3.6, -1.6, 0), 1.2, "rock_dark", segments=7, rings=4, scale=(1.2, 1, 0.55))
    mb.sphere((x - 3.9, 1.0, 0), 1.1, "charcoal", segments=7, rings=4, scale=(1.1, 1, 0.6))
    mb.sphere((x - 3.2, -1.2, 0.5), 0.3, "clay", segments=5, rings=3)
    for r in range(3):
        for i in range(4 - r):
            mb.box((x - 2.6 + i * 0.3 + r * 0.15, -3.6, 0.07 + r * 0.14), (0.24, 0.8, 0.12), "iron")


def apiary(mb, rig, seed=106):
    rnd = random.Random(seed)
    # A roofed stand with a row of straw skeps.
    w = 4.4
    for sx in (-1, 0, 1):
        mb.box((sx * w / 2, 1.6, 1.0), (0.14, 0.14, 2.0), "timber")
        mb.box((sx * w / 2, 0.5, 0.8), (0.14, 0.14, 1.6), "timber")
    game.sloped_slab(mb, -w / 2 - 0.3, w / 2 + 0.3, 0.1, 1.9, 1.55, 2.1, 0.12, "thatch")
    game.sloped_slab(mb, -w / 2 - 0.3, w / 2 + 0.3, 0.1, 0.7, 1.6, 1.8, 0.12, "thatch_dark")
    mb.box((0, 1.6, 0.9), (w, 0.06, 1.8), "plank")
    for z in (0.55, 1.15):
        mb.box((0, 1.1, z), (w, 0.9, 0.07), "wood")
    for r, z in enumerate((0.59, 1.19)):
        for i in range(5):
            x = -w / 2 + 0.5 + i * (w - 1.0) / 4
            if r == 1 and i in (1, 3):
                continue
            P.dome(mb, x, 1.1, z, 0.3, 0.42, ("thatch", "thatch_dark"), rows=3, seg=8, eave=0.0)
            mb.box((x, 0.8, z + 0.06), (0.1, 0.04, 0.06), "charcoal")
    # Log hives, a honey press, jars, a smoker, flower beds.
    for x in (-2.6, -1.9):
        mb.cylinder((x, -1.2, 0), (x, -1.2, 0.9), 0.3, 0.28, "log", segments=8)
        mb.cylinder((x, -1.2, 0.9), (x, -1.2, 1.0), 0.38, 0.34, "thatch", segments=8)
        mb.box((x, -1.5, 0.35), (0.1, 0.04, 0.06), "charcoal")
    mb.box((1.8, -1.6, 0.4), (0.9, 0.6, 0.8), "wood")
    mb.cylinder((1.8, -1.6, 0.8), (1.8, -1.6, 1.3), 0.06, 0.06, "iron", segments=5)
    mb.box((1.8, -1.6, 1.3), (0.7, 0.06, 0.06), "timber")
    for i in range(3):
        mb.cylinder((2.6 + 0.0, -1.2 - i * 0.3, 0), (2.6, -1.2 - i * 0.3, 0.26), 0.11, 0.1, "gold", segments=6)
        mb.cylinder((2.6, -1.2 - i * 0.3, 0.26), (2.6, -1.2 - i * 0.3, 0.3), 0.08, 0.08, "wood_light", segments=6)
    for i in range(10):
        x, y = rnd.uniform(-2.6, 2.6), rnd.uniform(-2.8, -2.0)
        mb.sphere((x, y, 0.14), 0.18, "leaves", segments=5, rings=3)
        mb.sphere((x, y, 0.32), 0.09, rnd.choice(("flowers", "flowers_y", "magic", "cloth_white")), segments=5, rings=3)
    game.fence(mb, -2.9, -2.9, 2.9, -2.9, posts=6, h=0.7)
    # Bees circling the hives (clip `fly`).
    for k, (cx, cz, rr, n) in enumerate(((0.0, 1.7, 1.4, 7), (-2.2, 1.3, 0.7, 5))):
        name = "bees%d" % k
        with mb.bone(name):
            for i in range(n):
                a = TAU * i / n
                mb.sphere((cx + rr * (0.6 + 0.4 * ((i * 7) % 5) / 4) * math.cos(a),
                           (0.4 if k == 0 else -1.3) + rr * 0.6 * math.sin(a), cz + 0.3 * math.sin(i * 2.4)), 0.035, "gold", segments=4,
                          rings=3)
        rig.bone(name, (cx, 0.4 if k == 0 else -1.3, cz), (cx, 0.4 if k == 0 else -1.3, cz + 0.5), None)
    rig.add("fly", 3.0, lambda t: ({"bees0": [(P.kit.Z, 360 * t)], "bees1": [(P.kit.Z, -720 * t)]},
                                   {"bees0": (0, 0, 0.12 * math.sin(TAU * 3 * t)), "bees1": (0, 0, 0.1 * math.sin(TAU * 2 * t))}))


def fire_station(mb, rig, seed=108):
    rnd = random.Random(seed)
    # The engine shed, with the water cart in its open bay.
    cx, cy, w, d, h = -0.9, 1.0, 4.4, 4.2, 3.0
    storey(mb, rnd, "brick", cx, cy, 0, w, d, h)
    P.gable_roof(mb, cx, cy, w, d, h, 1.8, ("tile_red", "tile_red_dark"), rows=5, overhang=0.35, gable="brick")
    with P.face(mb, cx, cy, w, d, "front"):
        mb.box((0, -0.03, 1.3), (3.0, 0.14, 2.6), "trim")
        mb.box((0, -0.02, 1.25), (2.7, 0.16, 2.5), "charcoal")
        for s in (-1, 1):  # The doors, folded open.
            mb.box((s * 1.55, -0.7, 1.25), (0.1, 1.3, 2.4), "band")
            mb.box((s * 1.61, -0.7, 1.25), (0.04, 1.3, 0.1), "iron")
        # A row of buckets and a ladder on the wall.
        mb.box((0, -0.1, 2.75), (3.6, 0.06, 0.08), "iron")
    for i in range(5):
        bx = cx - 1.6 + i * 0.3
        mb.cylinder((bx, cy - d / 2 - 0.25, 2.3), (bx, cy - d / 2 - 0.25, 2.6), 0.1, 0.13, "hide", segments=6)
    with mb.placed((cx, cy - d / 2 - 1.6, 0)):   # The water cart.
        mb.cylinder((-0.9, 0, 0.95), (0.9, 0, 0.95), 0.55, 0.55, "wood", segments=10)
        for xx in (-0.6, 0, 0.6):
            mb.cylinder((xx - 0.04, 0, 0.95), (xx + 0.04, 0, 0.95), 0.57, 0.57, "iron", segments=10)
        mb.box((0, 0, 0.4), (2.2, 0.9, 0.1), "timber")
        for sx in (-0.7, 0.7):
            for sy in (-1, 1):
                mb.cylinder((sx, sy * 0.5, 0.42), (sx, sy * 0.6, 0.42), 0.42, 0.42, "wood", segments=10)
                mb.cylinder((sx, sy * 0.48, 0.42), (sx, sy * 0.63, 0.42), 0.1, 0.1, "band", segments=6)
        mb.box((0, 0, 1.6), (0.5, 0.3, 0.3), "brass")
        P.beam(mb, (0, 0, 1.6), (0.9, -0.5, 1.9), 0.05, "brass")
        P.beam(mb, (1.1, 0, 0.45), (2.4, 0, 0.3), 0.07, "timber")
    with P.face(mb, cx, cy, w, d, "left"):
        for s in (-0.2, 0.2):
            mb.box((0, -0.08 + 0, 1.6 + s), (3.6, 0.06, 0.06), "timber")
        for i in range(9):
            mb.box((-1.6 + i * 0.4, -0.08, 1.6), (0.05, 0.05, 0.4), "wood")
        P.window(mb, 1.2, 2.3, w=0.5, h=0.5, shutter=None)
    # The watch tower with its alarm bell.
    tx, ty, tw, th = 2.2, 1.6, 2.4, 9.0
    P.stone_block(mb, tx, ty, 0, tw, tw, th, rnd, wall="brick", dark="brick_dark", light="trim", band=(3.0, 6.0))
    with P.face(mb, tx, ty, tw, tw, "front"):
        P.arched_door(mb, 0, 0.05, w=0.9, h=1.9)
        P.arched_window(mb, 0, 4.0, w=0.5, h=1.1)
        P.arched_window(mb, 0, 6.8, w=0.5, h=1.1)
    mb.box((tx, ty, th + 0.08), (tw + 1.2, tw + 1.2, 0.16), "plank")
    for sx in (-1, 1):
        for sy in (-1, 1):
            P.beam(mb, (tx + sx * tw / 2, ty + sy * tw / 2, th - 1.0), (tx + sx * (tw / 2 + 0.5), ty + sy * (tw / 2 + 0.5), th), 0.1, "timber")
            mb.box((tx + sx * (tw / 2 + 0.5), ty + sy * (tw / 2 + 0.5), th + 1.3), (0.12, 0.12, 2.3), "timber")
    for side in P.SIDES:
        with P.face(mb, tx, ty, tw + 1.1, tw + 1.1, side) as L:
            mb.box((0, 0.03, th + 0.9), (L, 0.06, 0.06), "timber")
            mb.box((0, 0.03, th + 0.5), (L, 0.06, 0.06), "timber")
    tip = P.pyramid_roof(mb, tx, ty, th + 2.4, tw + 1.1, tw + 1.1, 1.8, ("tile_red", "tile_red_dark"), rows=4, overhang=0.3, finial="brass")
    mb.box((tx, ty, th + 2.3), (tw + 1.0, 0.12, 0.12), "timber")
    with mb.bone("bell"):
        mb.cylinder((tx, ty, th + 1.5), (tx, ty, th + 1.95), 0.36, 0.2, "bell", segments=8)
        mb.cylinder((tx, ty, th + 1.95), (tx, ty, th + 2.25), 0.2, 0.08, "bell", segments=8)
        mb.cylinder((tx, ty, th + 1.7), (tx, ty, th + 1.35), 0.04, 0.07, "iron", segments=5)
    rig.bone("bell", (tx, ty, th + 2.3), (tx, ty, th + 1.4), None)
    rig.add("ring", 0.8, lambda t: {"bell": [(P.kit.X, 28 * math.sin(TAU * t))]})
    P.flag(mb, rig, tx, ty, tip - 0.2, pole=1.6, length=1.1, mat="band", stripe="banner2")
    # A well with a trough and hooks on poles.
    P.well(mb, 3.0, -2.4, roof=("tile_red", "tile_red_dark"))
    for i in range(2):
        mb.cylinder((-3.4, -2.2 - i * 0.3, 0.1), (0.6, -2.2 - i * 0.3, 0.14), 0.035, 0.035, "wood", segments=5)
        mb.box((0.65, -2.2 - i * 0.3, 0.14), (0.06, 0.2, 0.06), "iron")


MIRRORED = ("blast_furnace",)


def make(name, fn, colors, **kw):
    def build():
        mb = P.begin()
        rig = P.Rig()
        if fn.__name__ in MIRRORED:
            with mb.placed(matrix=Matrix.Scale(-1, 4, (1, 0, 0))):
                fn(mb, rig, **kw)
        else:
            fn(mb, rig, **kw)
        P.finish(mb, name, colors, rig)
    return build


MODELS = {
    "bld_quarry": make("bld_quarry", quarry, P.BASE),
    "bld_quarry_sandstone": make("bld_quarry_sandstone", quarry,
                                 P.palette(rock=0xC4AA7C, rock_dark=0xA48C62, wall=0xD4BC8C, wall_light=0xE6D4AA)),
    "bld_bottle_kiln": make("bld_bottle_kiln", bottle_kiln, P.BASE),
    "bld_blast_furnace": make("bld_blast_furnace", blast_furnace, P.BASE),
    "bld_apiary": make("bld_apiary", apiary, P.BASE),
    "bld_fire_station": make("bld_fire_station", fire_station, P.BASE),
}
