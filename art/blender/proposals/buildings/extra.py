"""More buildings beyond the list: cathedral, dovecote, great barn,
shipyard, brewery, bakery, bathhouse and hunting lodge."""

import math
import random

import parts as P
from civic import storey, round_window
from mills import sack, hand_cart
from parts import game, TAU

ROOF = ("roof", "roof_dark")


def rose_window(mb, x, z, r=1.3):
    """A round window with spokes, on a wall face."""
    mb.cylinder((x, 0.04, z), (x, -0.1, z), r + 0.22, r + 0.22, "trim", segments=14)
    mb.cylinder((x, 0.0, z), (x, -0.14, z), r, r, "window", segments=14)
    for i in range(4):
        a = math.pi * i / 4
        P.beam(mb, (x - r * math.cos(a), -0.15, z - r * math.sin(a)), (x + r * math.cos(a), -0.15, z + r * math.sin(a)), 0.06,
               "trim")
    mb.cylinder((x, -0.1, z), (x, -0.19, z), r * 0.28, r * 0.28, "trim", segments=10)
    mb.cylinder((x, -0.12, z), (x, -0.21, z), r * 0.17, r * 0.17, "glow", segments=10)


def bell_tower(mb, rig, rnd, x, y, w, h, spire, bell="bell", phase=0.0, door=True, pinnacles=True):
    """A square tower with an open belfry, a swinging bell (clip `ring`)
    and a spire. Returns the height of the tip."""
    P.stone_block(mb, x, y, 0, w, w, h, rnd, band=(h * 0.34, h * 0.67))
    with P.face(mb, x, y, w, w, "front"):
        if door:
            P.arched_door(mb, 0, 0.05, w=1.3, h=2.5)
        P.arched_window(mb, 0, h * 0.4, w=0.8, h=2.0)
        P.arched_window(mb, 0, h * 0.72, w=0.7, h=1.6)
    for side in ("left", "right", "back"):
        with P.face(mb, x, y, w, w, side):
            P.arched_window(mb, 0, h * 0.72, w=0.7, h=1.6)
            P.arrow_slit(mb, 0, h * 0.3)
    mb.box((x, y, h + 0.07), (w + 0.3, w + 0.3, 0.14), "wall_light")
    for side in P.SIDES:
        with P.face(mb, x, y, w, w, side):
            with mb.placed((0, 0.3, 0)):
                P.arch_wall(mb, w, 0.6, 3.0, w * 0.5, 2.4, z0=h + 0.14)
            P.arch_trim(mb, 0, 0, h + 0.14, w * 0.5, 2.4, t=0.18, depth=0.08)
    mb.box((x, y, h + 3.22), (w + 0.3, w + 0.3, 0.16), "wall_light")
    tip = P.pyramid_roof(mb, x, y, h + 3.3, w, w, spire, ROOF, rows=7, overhang=0.25)
    mb.box((x, y, tip + 0.45), (0.1, 0.1, 1.1), "gold")
    mb.box((x, y, tip + 0.7), (0.55, 0.1, 0.1), "gold")
    if pinnacles:
        for sx in (-1, 1):
            for sy in (-1, 1):
                px, py = x + sx * (w / 2 - 0.15), y + sy * (w / 2 - 0.15)
                mb.box((px, py, h + 3.7), (0.45, 0.45, 0.9), "wall")
                mb.cylinder((px, py, h + 4.15), (px, py, h + 5.6), 0.3, 0.0, "wall_light", segments=4)
    mb.box((x, y, h + 2.75), (w - 0.4, 0.2, 0.2), "timber")
    name = rig.name(bell)
    with mb.bone(name):
        mb.box((x, y, h + 2.55), (1.0, 0.22, 0.24), "timber")
        mb.cylinder((x, y, h + 1.4), (x, y, h + 2.1), 0.66, 0.4, "bell", segments=10)
        mb.cylinder((x, y, h + 2.1), (x, y, h + 2.45), 0.4, 0.2, "bell", segments=10)
        mb.cylinder((x, y, h + 1.7), (x, y, h + 1.15), 0.05, 0.1, "iron", segments=5)
    head = mb.world((x, y, h + 2.65))
    axis = mb.world_dir((1, 0, 0))
    rig.bone(name, head, head + P.Vector((0, 0, -1)), None)
    rig.add("ring", 2.0, lambda t: {name: [(axis, 26 * math.sin(TAU * t + phase))]})
    return tip


def cathedral(mb, rig, seed=70):
    rnd = random.Random(seed)
    with mb.placed((0, -1.0, 0)):
        nh, rise, hw = 8.6, 4.8, 3.6
        ny0, ny1 = -9.0, 11.0
        nyc, nlen = (ny0 + ny1) / 2, ny1 - ny0
        P.stone_block(mb, 0, nyc, 0, 2 * hw, nlen, nh, rnd)
        with mb.placed((0, nyc, 0), math.pi / 2):
            ridge = P.gable_roof(mb, 0, 0, nlen, 2 * hw, nh, rise, ROOF, rows=8, overhang=0.4, gable="wall", barge="wall_light")
        # Clerestory windows, aisles with their own windows, and flying buttresses.
        bays = 4
        ay0, ay1 = ny0 + 0.4, 2.2
        for sx, side in ((-1, "left"), (1, "right")):
            ax = sx * (hw + 1.3)
            P.stone_block(mb, ax, (ay0 + ay1) / 2, 0, 2.6, ay1 - ay0, 3.8, rnd, quoins=False)
            P.prism_xz(mb, [(sx * (hw + 2.9), 3.7), (sx * hw, 5.3), (sx * hw, 5.42), (sx * (hw + 2.9), 3.82)][::sx], ay0 - 0.2, ay1 + 0.2,
                       "roof")
            for k in range(1, 3):
                xk = sx * (hw + 2.9 * (1 - k / 3))
                P.prism_xz(mb, [(xk, 3.72 + 1.6 * k / 3 + 0.12), (xk - sx * 0.5, 3.72 + 1.6 * k / 3 + 0.36),
                                (xk - sx * 0.5, 3.72 + 1.6 * k / 3 + 0.4), (xk, 3.72 + 1.6 * k / 3 + 0.2)][::sx], ay0 - 0.2, ay1 + 0.2,
                           "roof_dark")
            for i in range(bays):
                y = ay0 + (i + 0.5) * (ay1 - ay0) / bays
                with mb.placed((sx * (hw + 2.6), y, 0), sx * math.pi / 2):
                    P.arched_window(mb, 0, 1.0, w=0.8, h=2.0)
                with mb.placed((sx * hw, y, 0), sx * math.pi / 2):
                    P.arched_window(mb, 0, 5.7, w=0.8, h=2.2)
            for i in range(bays + 1):
                y = ay0 + i * (ay1 - ay0) / bays
                px = sx * (hw + 2.9)
                mb.box((px, y, 3.2), (0.7, 0.6, 6.4), "wall")
                mb.box((px, y, 6.45), (0.85, 0.75, 0.14), "wall_light")
                mb.cylinder((px, y, 6.5), (px, y, 7.9), 0.36, 0.0, "wall_light", segments=4)
                P.beam(mb, (px, y, 5.9), (sx * (hw - 0.1), y, 7.7), 0.26, "wall")
        for sx in (-1, 1):  # Windows of the choir, east of the transept.
            for y in (9.0,):
                with mb.placed((sx * hw, y, 0), sx * math.pi / 2):
                    P.arched_window(mb, 0, 2.0, w=0.9, h=4.6)
        # The transept, with a rose window at each end.
        ty, tw, td = 5.6, 15.0, 5.6
        P.stone_block(mb, 0, ty, 0, tw, td, nh, rnd)
        P.gable_roof(mb, 0, ty, tw, td, nh, rise * 0.92, ROOF, rows=8, overhang=0.4, gable="wall", barge="wall_light")
        for side in ("left", "right"):
            with P.face(mb, 0, ty, tw, td, side):
                rose_window(mb, 0, 6.6, r=1.3)
                P.arched_door(mb, 0, 0.05, w=1.4, h=2.6)
                for x in (-1.6, 1.6):
                    P.arched_window(mb, x, 1.4, w=0.6, h=2.4)
        for side in ("front", "back"):
            with P.face(mb, 0, ty, tw, td, side):
                for x in (-5.9, 5.9):
                    P.arched_window(mb, x, 2.0, w=0.8, h=4.4)
        for sx in (-1, 1):
            for sy in (-1, 1):
                px, py = sx * (tw / 2 - 0.1), ty + sy * (td / 2 - 0.1)
                mb.box((px, py, nh / 2 + 0.6), (0.9, 0.9, nh + 1.2), "wall")
                mb.cylinder((px, py, nh + 1.2), (px, py, nh + 3.0), 0.6, 0.0, "wall_light", segments=4)
        # The lantern tower and spire over the crossing.
        cz = ridge - 1.2
        mb.box((0, ty, cz + 2.0), (3.6, 3.6, 4.0), "wall")
        mb.box((0, ty, cz + 4.05), (3.9, 3.9, 0.16), "wall_light")
        for side in P.SIDES:
            with P.face(mb, 0, ty, 3.6, 3.6, side):
                for x in (-0.8, 0.8):
                    P.arched_window(mb, x, cz + 1.9, w=0.6, h=1.6, sill=False)
        tip = P.pyramid_roof(mb, 0, ty, cz + 4.1, 3.6, 3.6, 9.5, ROOF, rows=9, overhang=0.2)
        mb.box((0, ty, tip + 0.5), (0.1, 0.1, 1.2), "gold")
        mb.box((0, ty, tip + 0.75), (0.6, 0.1, 0.1), "gold")
        for sx in (-1, 1):
            for sy in (-1, 1):
                mb.cylinder((sx * 1.65, ty + sy * 1.65, cz + 4.1), (sx * 1.65, ty + sy * 1.65, cz + 6.2), 0.32, 0.0, "wall_light",
                            segments=4)
        # The apse.
        mb.cylinder((0, ny1, 0), (0, ny1, nh - 0.6), hw - 0.1, hw - 0.1, "wall", segments=12)
        mb.cylinder((0, ny1, 0), (0, ny1, 0.7), hw + 0.15, hw + 0.05, "wall_dark", segments=12)
        P.cone_roof(mb, 0, ny1, nh - 0.6, hw - 0.1, 4.2, ROOF, rows=5, eave=0.35, power=1.0, finial="gold")
        for a in (0.35, math.pi / 2, math.pi - 0.35):
            round_window(mb, 0, ny1, (hw - 0.1) * math.cos(math.pi / 12), a, 4.2, w=0.8, h=4.2)
        # The west front: twin bell towers and the great portal between them.
        fy = -10.4
        for i, sx in enumerate((-1, 1)):
            bell_tower(mb, rig, rnd, sx * 3.7, fy, 4.2, 14.0, 8.0, phase=i * math.pi)
        mb.box((0, fy - 0.7, 6.3), (3.4, 2.4, 12.6), "wall")
        P.prism_xz(mb, [(-1.7, 12.6), (1.7, 12.6), (0, 14.8)], fy - 1.9, fy + 0.5, "wall")
        P.prism_xz(mb, [(-1.95, 12.5), (0, 15.05), (0, 15.3), (-1.95, 12.75)], fy - 2.0, fy - 1.85, "wall_light")
        P.prism_xz(mb, [(1.95, 12.5), (1.95, 12.75), (0, 15.3), (0, 15.05)], fy - 2.0, fy - 1.85, "wall_light")
        with mb.placed((0, fy - 1.9, 0)):
            P.arched_door(mb, 0, 0.35, w=2.2, h=3.8)
            P.arch_trim(mb, 0, -0.1, 0.35, 2.6, 4.0, t=0.3, depth=0.2, seg=6)
            rose_window(mb, 0, 9.4, r=1.35)
            for x in (-1.1, -0.55, 0, 0.55, 1.1):
                P.arched_window(mb, x, 5.4, w=0.3, h=1.4, sill=False, bars=False)
            mb.box((0, -0.1, 5.2), (3.4, 0.25, 0.16), "wall_light")
            mb.box((0, -0.1, 7.5), (3.4, 0.25, 0.16), "wall_light")
            mb.box((0, -0.14, 15.6), (0.1, 0.1, 1.0), "gold")
            mb.box((0, -0.14, 15.8), (0.5, 0.1, 0.1), "gold")
        for i in range(3):
            mb.box((0, fy - 3.0 - i * 0.35, 0.29 - i * 0.12), (9.0 + i * 0.6, 1.6, 0.12), "wall_light")


def dovecote(mb, rig, seed=72):
    rnd = random.Random(seed)
    x, y, r, h = 0.0, 0.2, 1.7, 5.0
    P.round_tower(mb, x, y, r, h, rnd, slits=0, bands=False, density=0.25)
    q = r * math.cos(math.pi / 14)
    with mb.placed((x, y - q - 0.02, 0)):
        P.arched_door(mb, 0, 0.1, w=0.9, h=1.8)
    for row, z in enumerate((2.6, 3.4, 4.2)):
        mb.cylinder((x, y, z - 0.28), (x, y, z - 0.22), r + 0.22, r + 0.22, "wall_light", segments=14)
        for i in range(10):
            a = TAU * (i + 0.5 * (row % 2)) / 10
            if z < 2.8 and abs((a + math.pi / 2 + math.pi) % TAU - math.pi) < 0.5:
                continue
            mb.box((x + (q + 0.01) * math.cos(a), y + (q + 0.01) * math.sin(a), z), (0.2, 0.3, 0.34), "window", rotation_z=a)
    mb.cylinder((x, y, h - 0.4), (x, y, h), r, r + 0.25, "wall", segments=14)
    P.cone_roof(mb, x, y, h, r + 0.25, 2.6, ("tile_red", "tile_red_dark"), rows=5, eave=0.3, finial=None)
    for i in range(6):
        a = TAU * i / 6
        mb.box((x + 0.45 * math.cos(a), y + 0.45 * math.sin(a), h + 2.5), (0.08, 0.08, 0.9), "timber", rotation_z=a)
    P.cone_roof(mb, x, y, h + 2.9, 0.5, 0.9, ("tile_red", "tile_red_dark"), rows=2, eave=0.2, seg=8, finial="gold")

    def dove(px, py, pz, turn=0.0, wings=None):
        with mb.placed((px, py, pz), turn):
            mb.sphere((0, 0, 0.1), 0.13, "white", segments=6, rings=4, scale=(1.5, 0.9, 0.9))
            mb.sphere((0.17, 0, 0.2), 0.07, "white", segments=5, rings=3)
            mb.cylinder((0.22, 0, 0.19), (0.3, 0, 0.18), 0.02, 0.0, "brass", segments=4)
            mb.box((-0.24, 0, 0.1), (0.2, 0.1, 0.03), "white_dark")
            if wings:
                for s, name in zip((-1, 1), wings):
                    with mb.bone(name):
                        mb.box((0, s * 0.26, 0.14), (0.2, 0.44, 0.025), "white_dark")
                        mb.box((0.02, s * 0.5, 0.14), (0.12, 0.2, 0.02), "white")

    for a, z in ((0.3, 3.18), (1.9, 2.38), (3.3, 3.98), (4.4, 3.18)):
        dove(x + (r + 0.12) * math.cos(a), y + (r + 0.12) * math.sin(a), z - 0.04, a + math.pi / 2)
    dove(x + 0.9, y - 0.5, h + 1.55, 0.6)
    # A dove that circles the tower, flapping (clip `fly`).
    with mb.bone("dove"):
        dove(x + 3.2, y, h + 1.6, math.pi / 2, wings=("wing_l", "wing_r"))
    rig.bone("dove", (x, y, h + 1.7), (x, y, h + 2.7), None)
    rig.bone("wing_l", (x + 3.2 + 0.08, y, h + 1.74), (x + 3.2 + 0.5, y, h + 1.74), "dove")
    rig.bone("wing_r", (x + 3.2 - 0.08, y, h + 1.74), (x + 3.2 - 0.5, y, h + 1.74), "dove")

    def fly(t):
        flap = 35 * math.sin(TAU * 8 * t)
        return ({"dove": [(P.kit.Z, 360 * t)], "wing_l": [(P.kit.Y, flap)], "wing_r": [(P.kit.Y, -flap)]},
                {"dove": (0, 0, 0.5 * math.sin(TAU * 2 * t))})

    rig.add("fly", 5.0, fly)
    # A feeding trough and sacks of grain.
    mb.box((1.6, -1.6, 0.3), (0.9, 0.4, 0.2), "wood")
    mb.box((1.6, -1.6, 0.36), (0.76, 0.26, 0.1), "hay")
    for s in (-0.35, 0.35):
        mb.box((1.6 + s, -1.6, 0.1), (0.08, 0.36, 0.2), "timber")
    sack(mb, -1.5, -1.6)


def gambrel_roof(mb, cx, cy, w, d, z, rise, mats, overhang=0.4, gable="plank"):
    """A barn roof with two slopes on each side, its ridge along X."""
    kx, kz = d / 2 * 0.52, rise * 0.68   # The knee of the roof.
    for side in (-1, 1):
        yo = cy + side * (d / 2 + overhang)
        zo = z - overhang * kz / (d / 2 - kx)
        yk = cy + side * kx
        for r in range(3):
            t0, t1 = r / 3, (r + 1) / 3
            game.sloped_slab(mb, cx - w / 2 - overhang, cx + w / 2 + overhang, yo + (yk - yo) * t0, yo + (yk - yo) * min(1, t1 + 0.03),
                             zo + (z + kz - zo) * t0 + (0.07 if r else 0), zo + (z + kz - zo) * t1, 0.1, mats[r % 2])
        for r in range(2):
            t0, t1 = r / 2, (r + 1) / 2
            game.sloped_slab(mb, cx - w / 2 - overhang, cx + w / 2 + overhang, yk + (cy - yk) * t0, yk + (cy - yk) * min(1, t1 + 0.03),
                             z + kz + (rise - kz) * t0 + 0.07, z + kz + (rise - kz) * t1, 0.1, mats[(r + 1) % 2])
    for x in (cx - w / 2, cx + w / 2):
        s = 1 if x > cx else -1
        P.prism_yz(mb, [(cy - d / 2, z - 0.02), (cy + d / 2, z - 0.02), (cy + kx, z + kz), (cy, z + rise), (cy - kx, z + kz)],
                   x - 0.12 * (s > 0), x + 0.12 * (s < 0), gable)
    mb.box((cx, cy, z + rise + 0.08), (w + 2 * overhang + 0.06, 0.26, 0.14), mats[1])
    return z + rise


def great_barn(mb, rig, roof=("tile_red", "tile_red_dark"), seed=74):
    rnd = random.Random(seed)
    cx, cy, w, d, h = -1.2, 0.6, 8.6, 6.4, 3.8
    mb.box((cx, cy, 0.3), (w + 0.3, d + 0.3, 0.6), "wall")
    P.plank_block(mb, cx, cy, 0.6, w, d, h - 0.6, mat="band", dark="tile_red_dark", post="white")
    top = gambrel_roof(mb, cx, cy, w, d, h, 3.6, roof, gable="band")
    with P.face(mb, cx, cy, w, d, "front") as L:
        mb.box((0, -0.04, 1.95), (3.2, 0.1, 3.1), "white")
        for s in (-1, 1):
            mb.box((s * 0.75, -0.08, 1.9), (1.4, 0.1, 2.8), "band")
            P.beam(mb, (s * 0.1, -0.14, 0.55), (s * 1.4, -0.14, 3.25), 0.07, "white")
            P.beam(mb, (s * 1.4, -0.14, 0.55), (s * 0.1, -0.14, 3.25), 0.07, "white")
        for x in (-3.0, 3.0):
            P.window(mb, x, 2.2, w=0.7, h=0.7, shutter=None, frame="white")
    with P.face(mb, cx, cy, w, d, "left"):
        mb.box((0, -0.04, h + 1.3), (1.3, 0.08, 1.4), "white")
        mb.box((0, -0.07, h + 1.3), (1.1, 0.08, 1.2), "hay")
        mb.box((0, -0.6, h + 2.6), (0.16, 1.4, 0.16), "timber")
        mb.box((0, -1.2, h + 1.9), (0.03, 0.03, 1.3), "rope")
        P.hay_bale(mb, 0, -1.2, z=h + 0.6, r=0.3, w=0.5)
        for x in (-1.8, 1.8):
            P.window(mb, x, 2.2, w=0.7, h=0.7, shutter=None, frame="white")
    # A weathervane on the ridge.
    mb.cylinder((cx, cy, top), (cx, cy, top + 1.2), 0.03, 0.03, "iron", segments=5)
    with mb.bone("vane"):
        P.prism_xz(mb, [(cx - 0.5, top + 0.95), (cx + 0.2, top + 0.95), (cx + 0.55, top + 1.07), (cx + 0.2, top + 1.19),
                        (cx - 0.5, top + 1.19)], cy - 0.015, cy + 0.015, "iron")
    rig.bone("vane", (cx, cy, top + 0.8), (cx, cy, top + 1.3), None)
    rig.add("turn", 6.0, lambda t: {"vane": [(P.kit.Z, 35 * math.sin(TAU * t) + 15 * math.sin(2 * TAU * t))]})
    # The silo.
    sx, sy = cx + w / 2 + 1.9, cy + 1.2
    P.round_tower(mb, sx, sy, 1.5, 7.0, rnd, slits=0, bands=True, density=0.2)
    mb.cylinder((sx, sy, 6.6), (sx, sy, 7.0), 1.5, 1.7, "wall", segments=14)
    P.cone_roof(mb, sx, sy, 7.0, 1.7, 2.4, roof, rows=4, eave=0.25, finial="iron")
    for i in range(12):
        mb.box((sx, sy - 1.5 - 0.06, 0.5 + i * 0.5), (0.5, 0.06, 0.06), "timber")
    for s in (-0.25, 0.25):
        mb.box((sx + s, sy - 1.56, 3.3), (0.06, 0.06, 6.2), "timber")
    # The yard: a hay wagon, bales, a fence.
    with mb.placed((cx - 2.6, -3.6, 0), 0.1):
        mb.box((0, 0, 0.7), (2.6, 1.3, 0.12), "plank")
        for s in (-1, 1):
            for x in (-0.9, 0.9):
                mb.cylinder((x, s * 0.72, 0.5), (x, s * 0.82, 0.5), 0.5, 0.5, "wood", segments=10)
            mb.box((0, s * 0.62, 1.05), (2.6, 0.06, 0.06), "timber")
            for x in (-1.2, 0, 1.2):
                mb.box((x, s * 0.62, 0.9), (0.06, 0.06, 0.4), "timber")
        mb.sphere((0, 0, 1.2), 0.9, "hay", segments=7, rings=4, scale=(1.4, 0.7, 0.6))
        P.beam(mb, (1.3, 0, 0.7), (2.6, 0, 0.3), 0.08, "timber")
    for x, y, z in ((1.4, -3.4, 0), (2.1, -3.5, 0), (1.75, -3.45, 0.62)):
        P.hay_bale(mb, x, y, z=z)
    game.fence(mb, 3.2, -4.2, 5.8, -4.2, posts=3, h=1.0)
    game.fence(mb, 5.8, -4.2, 5.8, -1.4, posts=3, h=1.0)


def shipyard(mb, rig, seed=76):
    rnd = random.Random(seed)
    # The slipway: two timber rails on sleepers running down to the water at the front.
    for s in (-1, 1):
        P.beam(mb, (s * 0.9 - 1.5, 4.0, 0.35), (s * 0.9 - 1.5, -6.6, -0.25), 0.22, "timber")
    for i in range(9):
        t = i / 8
        mb.box((-1.5, 4.0 - 10.6 * t, 0.12 - 0.5 * t), (3.4, 0.3, 0.24), "log")
    # The hull on the slip: keel, stem, sternpost, ribs and the first strakes.
    kx, y0, y1, kz = -1.5, -5.0, 3.6, 0.75
    mb.box((kx, (y0 + y1) / 2, kz), (0.26, y1 - y0, 0.3), "timber")
    P.beam(mb, (kx, y0, kz), (kx, y0 - 1.3, kz + 2.9), 0.2, "timber")
    P.beam(mb, (kx, y1, kz), (kx, y1 + 0.5, kz + 2.6), 0.2, "timber")
    n = 10
    stations = []
    for i in range(n):
        t = (i + 0.5) / n
        y = y0 + (y1 - y0) * t
        hw = 1.75 * math.sin(math.pi * (0.12 + 0.82 * t)) ** 0.7
        stations.append((y, hw))
        for s in (-1, 1):
            P.beam(mb, (kx, y, kz), (kx + s * hw * 0.75, y, kz + 0.75), 0.11, "wood_light")
            P.beam(mb, (kx + s * hw * 0.75, y, kz + 0.75), (kx + s * hw, y, kz + 2.3), 0.11, "wood_light")
        mb.box((kx, y, kz + 2.2), (2 * hw, 0.1, 0.1), "wood_light")
    for (ya, wa), (yb, wb) in zip(stations, stations[1:]):
        for s in (-1, 1):
            for f, z in ((0.45, kz + 0.42), (0.78, kz + 0.85), (0.9, kz + 1.35)):
                P.beam(mb, (kx + s * wa * f, ya, z), (kx + s * wb * f, yb, z), 0.2, "plank")
            P.beam(mb, (kx + s * wa, ya, kz + 2.3), (kx + s * wb, yb, kz + 2.3), 0.12, "timber")
    for y in (-3.6, -0.8, 2.0):  # Shores holding the hull upright.
        for s in (-1, 1):
            P.beam(mb, (kx + s * 3.0, y, 0.0), (kx + s * 1.6, y, kz + 1.5), 0.1, "log")
    # Scaffolding along the far side, with a walkway and a ladder.
    for y in (-4.0, -1.2, 1.6, 4.2):
        mb.box((kx + 3.4, y, 1.9), (0.14, 0.14, 3.8), "timber")
        mb.box((kx + 2.3, y, 1.9), (0.14, 0.14, 3.8), "timber")
        mb.box((kx + 2.85, y, 2.3), (1.2, 0.1, 0.1), "timber")
    mb.box((kx + 2.85, 0.1, 2.4), (1.0, 8.4, 0.08), "plank")
    mb.box((kx + 3.4, 0.1, 3.3), (0.07, 8.4, 0.07), "timber")
    for s in (-0.25, 0.25):
        P.beam(mb, (kx + 4.3, -2.6 + s, 0), (kx + 3.5, -2.6 + s, 2.4), 0.06, "timber")
    for i in range(6):
        t = (i + 0.5) / 6
        mb.box((kx + 4.3 - 0.8 * t, -2.6, 2.4 * t), (0.05, 0.5, 0.05), "wood")
    # Sheer legs to lift the timbers.
    for s in (-1, 1):
        P.beam(mb, (kx - 3.3, 0.4 + s * 1.3, 0), (kx - 1.4, 0.4, 5.6), 0.14, "log")
    P.beam(mb, (kx - 4.6, 0.4, 0), (kx - 1.4, 0.4, 5.6), 0.04, "rope")
    mb.box((kx - 1.4, 0.4, 4.6), (0.04, 0.04, 2.0), "rope")
    mb.box((kx - 1.4, 0.4, 3.5), (0.2, 1.6, 0.2), "wood_light")
    # The shed, timber stacks, tar barrels and a sawpit trestle.
    with mb.placed((3.9, 2.6, 0)):
        P.plank_block(mb, 0, 0, 0, 3.6, 3.4, 2.5)
        P.gable_roof(mb, 0, 0, 3.6, 3.4, 2.5, 1.5, ("shingle", "shingle_dark"), rows=4, overhang=0.4, gable="plank")
        with P.face(mb, 0, 0, 3.6, 3.4, "front"):
            P.plank_door(mb, -0.7, 0.0, w=1.0, h=1.8)
            P.window(mb, 0.9, 1.4, w=0.6, h=0.6, shutter=None)
    for r in range(4):
        for i in range(5):
            mb.box((4.0, -2.0 + i * 0.3, 0.08 + r * 0.14), (3.2, 0.26, 0.12), "log_end" if (i + r) % 2 else "wood_light")
    game.log_pile(mb, 4.0, -3.8, length=3.0, rows=3)
    for x, y in ((2.3, 0.2), (2.9, 0.4), (2.5, -0.4)):
        game.barrel(mb, x, y, h=0.8, r=0.3, mat="charcoal")
    mb.box((kx - 3.6, -3.6, 0.5), (0.9, 0.5, 0.06), "wood")
    for s in (-0.35, 0.35):
        mb.box((kx - 3.6 + s, -3.6, 0.25), (0.06, 0.45, 0.5), "timber")
    mb.box((kx - 3.6, -3.6, 0.58), (0.5, 0.05, 0.1), "iron")


def brewery(mb, rig, seed=78):
    rnd = random.Random(seed)
    cx, cy, w, d, h1, h2 = -0.8, 1.2, 6.0, 4.6, 3.0, 2.5
    storey(mb, rnd, "stone", cx, cy, 0, w, d, h1)
    z1 = h1 + 0.2
    W, D = w + 0.5, d + 0.5
    mb.box((cx, cy, h1 + 0.1), (W + 0.1, D + 0.1, 0.2), "timber")
    storey(mb, rnd, "timber", cx, cy, z1, W, D, h2, plinth=0, cross=True)
    top = P.gable_roof(mb, cx, cy, W, D, z1 + h2, 2.8, ROOF, rows=7, overhang=0.45, gable="plaster", end_overhang=0.35)
    with P.face(mb, cx, cy, w, d, "front") as L:
        P.plank_door(mb, 1.6, 0.1, w=1.5, h=2.1, double=True)
        P.arched_window(mb, -1.4, 1.0, w=1.0, h=1.6)
    with P.face(mb, cx, cy, W, D, "front") as L:
        for x in (-L * 0.3, 0, L * 0.3):
            P.window(mb, x, z1 + h2 * 0.55, w=0.65, h=0.8)
        mb.box((0, -0.6, z1 + h2 + 1.6), (0.16, 1.4, 0.16), "timber")
        mb.box((0, -1.2, z1 + h2 + 1.0), (0.03, 0.03, 1.2), "rope")
    with mb.placed((cx, cy - D / 2 - 1.2, z1 + h2 - 0.4)):
        game.barrel(mb, 0, 0, h=0.8, r=0.3)
    # The brewhouse lean-to on the right: a copper kettle on its furnace, with a tall chimney.
    x0, x1 = cx + w / 2, cx + w / 2 + 2.8
    y0, y1 = cy - d / 2 + 0.3, cy + d / 2
    for y in (y0, y1):
        mb.box((x1 - 0.1, y, 1.3), (0.18, 0.18, 2.6), "timber")
    mb.box(((x0 + x1) / 2, y1, 1.3), (x1 - x0, 0.12, 2.6), "plank")
    P.prism_xz(mb, [(x0, 3.3), (x1 + 0.3, 2.5), (x1 + 0.3, 2.62), (x0, 3.42)], y0 - 0.3, y1 + 0.2, "roof_dark")
    kx_, ky_ = (x0 + x1) / 2 + 0.1, (y0 + y1) / 2 + 0.4
    mb.cylinder((kx_, ky_, 0), (kx_, ky_, 0.8), 1.05, 1.0, "brick", segments=12)
    mb.box((kx_, ky_ - 1.0, 0.35), (0.5, 0.2, 0.45), "ember")
    mb.cylinder((kx_, ky_, 0.8), (kx_, ky_, 1.6), 0.95, 0.95, "copper", segments=12)
    P.dome(mb, kx_, ky_, 1.6, 0.85, 0.7, ("copper", "copper_dark"), rows=3, seg=12, eave=0.1)
    mb.cylinder((kx_, ky_, 2.2), (kx_, ky_, 2.9), 0.16, 0.14, "copper_dark", segments=8)
    P.beam(mb, (kx_, ky_, 2.9), (x0 + 0.1, ky_, 2.6), 0.12, "copper_dark")
    P.chimney(mb, x1 - 0.5, y1 - 0.5, 0, top + 0.8, w=0.8, mat="brick", cap="stone_dark", pots=0)
    # Barrels stacked in a pyramid, a dray with casks, sacks of malt, a row of hop poles.
    by = cy - d / 2 - 0.9
    for i in range(3):
        mb.cylinder((cx - 2.6 + i * 0.75, by - 0.45, 0.36), (cx - 2.6 + i * 0.75, by + 0.45, 0.36), 0.36, 0.36, "wood", segments=10)
        for yy in (by - 0.3, by + 0.3):
            mb.cylinder((cx - 2.6 + i * 0.75, yy - 0.03, 0.36), (cx - 2.6 + i * 0.75, yy + 0.03, 0.36), 0.375, 0.375, "iron",
                        segments=10)
    for i in range(2):
        mb.cylinder((cx - 2.22 + i * 0.75, by - 0.45, 0.99), (cx - 2.22 + i * 0.75, by + 0.45, 0.99), 0.36, 0.36, "wood",
                    segments=10)
    hand_cart(mb, cx + 1.4, -3.4, 0.2)
    sack(mb, cx + 4.6, -1.6)
    sack(mb, cx + 5.0, -1.2, s=0.9)
    for i in range(4):
        px, py = 4.2, -4.0 + i * 0.0
        px = 1.6 + i * 0.9
        mb.cylinder((px, -4.4, 0), (px, -4.4, 3.2), 0.05, 0.04, "timber", segments=5)
        for k in range(5):
            mb.sphere((px + 0.08 * (-1) ** k, -4.4, 0.5 + k * 0.55), 0.2, "leaves" if k % 2 else "leaf_light", segments=5,
                      rings=3, scale=(1, 1, 1.4))
    mb.box((2.95, -4.4, 3.15), (2.9, 0.04, 0.04), "rope")
    with mb.placed((cx - W / 2 + 0.4, cy - D / 2, 0), -math.pi / 2):
        P.hanging_sign(mb, rig, 0, 0, z1 + 1.6, arm=1.1, board=(0.8, 0.7), emblem="bread")


def bakery(mb, rig, seed=80):
    rnd = random.Random(seed)
    cx, cy, w, d, h = 0.6, 1.0, 4.6, 4.2, 3.0
    storey(mb, rnd, "timber", cx, cy, 0, w, d, h, plinth=0.7)
    with mb.placed((cx, cy, 0), math.pi / 2):
        top = P.gable_roof(mb, 0, 0, d, w, h, 2.6, ROOF, rows=6, overhang=0.4, gable="plaster", end_overhang=0.4)
    with P.face(mb, cx, cy, w, d, "front"):
        P.plank_door(mb, 1.3, 0.2, w=0.95, h=1.75)
        # The shop window with its shutter folded down as a counter, under an awning.
        mb.box((-0.6, -0.03, 1.75), (2.0, 0.12, 1.2), "timber")
        mb.box((-0.6, -0.06, 1.75), (1.8, 0.1, 1.0), "glow")
        mb.box((-0.6, -0.4, 1.12), (2.0, 0.75, 0.07), "wood")
        for sx in (-0.9, 0.9):
            P.beam(mb, (-0.6 + sx, -0.05, 0.6), (-0.6 + sx, -0.7, 1.1), 0.05, "timber")
        for i in range(5):
            mb.sphere((-1.3 + i * 0.35, -0.42, 1.24), 0.13, "bread", segments=6, rings=4, scale=(1.2, 0.9, 0.7))
        for i in range(3):
            mb.cylinder((-1.1 + i * 0.5, -0.12, 1.6), (-0.95 + i * 0.5, -0.12, 2.1), 0.07, 0.07, "bread", segments=6)
        for i in range(4):
            x0 = -1.7 + i * 0.55
            game.sloped_slab(mb, x0, x0 + 0.56, -1.2, 0.0, 2.25, 2.7, 0.05, "stripe_a" if i % 2 else "stripe_b")
        P.window(mb, 0, h + 1.0, w=0.55, h=0.65, shutter=None)
        mb.box((0, 0, h + 1.9), (0.14, 0.14, 1.4), "timber")
    with P.face(mb, cx, cy, w, d, "right") as L:
        for x in (-L * 0.25, L * 0.25):
            P.window(mb, x, 1.8, w=0.6, h=0.7)
    # The oven: a brick dome on a stone base against the left wall, with its chimney.
    ox, oy = cx - w / 2 - 1.3, cy + 0.3
    mb.box((ox, oy, 0.5), (2.6, 2.8, 1.0), "stone")
    mb.box((ox, oy, 1.03), (2.8, 3.0, 0.08), "stone_dark")
    P.dome(mb, ox, oy, 1.07, 1.15, 1.25, ("brick", "brick_dark"), rows=4, seg=12, eave=0.0)
    mb.box((ox, oy - 1.15, 1.5), (0.8, 0.3, 0.7), "brick_dark")
    mb.box((ox, oy - 1.28, 1.45), (0.55, 0.1, 0.5), "ember")
    P.chimney(mb, ox, oy + 0.6, 1.9, top + 0.4, w=0.6, mat="brick", cap="stone_dark", pots=0)
    P.beam(mb, (ox + 1.0, oy - 1.7, 0.05), (ox + 0.3, oy - 1.4, 1.9), 0.035, "wood")  # The peel.
    mb.box((ox + 0.28, oy - 1.39, 2.0), (0.34, 0.04, 0.4), "wood_light")
    game.log_pile(mb, ox, oy - 2.6, length=1.6, rows=2)
    sack(mb, cx + 2.0, cy - d / 2 - 0.5)
    sack(mb, cx + 1.5, cy - d / 2 - 0.9, s=0.9)
    game.crate(mb, cx - 0.4, cy - d / 2 - 1.6, s=0.5, top="bread")
    with mb.placed((cx + w / 2 - 0.3, cy - d / 2, 0), -math.pi / 2):
        P.hanging_sign(mb, rig, 0, 0, h + 0.5, arm=1.1, board=(0.8, 0.6), emblem="bread", board_mat="plaster")


def bathhouse(mb, rig, seed=82):
    rnd = random.Random(seed)
    cx, cy, w, d, h = 0.0, 1.4, 8.4, 4.8, 3.8
    storey(mb, rnd, "stone", cx, cy, 0, w, d, h)
    mb.box((cx, cy, h + 0.1), (w + 0.4, d + 0.4, 0.2), "trim")
    P.pyramid_roof(mb, cx, cy, h + 0.2, w, d, 1.3, ("tile_red", "tile_red_dark"), rows=3, overhang=0.3, ridge=w - d + 1.6)
    # The dome over the hot room, with an oculus.
    mb.cylinder((cx, cy, h + 0.2), (cx, cy, h + 1.5), 2.0, 2.0, "wall", segments=12)
    for i in range(6):
        round_window(mb, cx, cy, 2.0 * math.cos(math.pi / 12), TAU * i / 6 + 0.26, h + 1.0, w=0.4, h=0.5, glass="glow")
    P.dome(mb, cx, cy, h + 1.5, 2.0, 1.7, ("copper", "copper_dark"), rows=4, seg=12, eave=0.15)
    mb.cylinder((cx, cy, h + 3.1), (cx, cy, h + 3.35), 0.4, 0.3, "trim", segments=8)
    # The portico of three arches.
    py = cy - d / 2 - 0.9
    for i in range(3):
        with mb.placed((cx + (i - 1) * 2.2, py - 0.6, 0)):
            P.arch_wall(mb, 2.2, 0.5, 3.1, 1.5, 2.5, mat="wall", inner="wall_dark")
            P.arch_trim(mb, 0, -0.25, 0, 1.5, 2.5, t=0.18, depth=0.08)
    mb.box((cx, py + 0.1, 3.2), (6.9, 2.0, 0.2), "trim")
    P.prism_xz(mb, [(cx - 3.45, 3.3), (cx + 3.45, 3.3), (cx + 3.45, 3.45), (cx - 3.45, 3.45)], py - 0.95, cy - d / 2, "tile_red")
    mb.box((cx, py - 0.1, 0.1), (6.6, 1.9, 0.2), "paving")
    with P.face(mb, cx, cy, w, d, "front"):
        P.arched_door(mb, 0, 0.2, w=1.3, h=2.4)
        for x in (-3.5, 3.5):
            P.arched_window(mb, x, 1.4, w=0.6, h=1.4)
    for side in ("left", "right"):
        with P.face(mb, cx, cy, w, d, side) as L:
            for x in (-L * 0.25, L * 0.25):
                P.arched_window(mb, x, 1.6, w=0.6, h=1.4)
    # The furnace at the back, the open pool in front, benches and urns.
    P.chimney(mb, cx + 3.2, cy + d / 2 - 0.5, h, h + 3.0, w=0.8, mat="brick", cap="trim", pots=0)
    game.log_pile(mb, cx + 3.0, cy + d / 2 + 0.6, length=1.8, rows=2)
    qx, qy = cx, py - 2.4
    mb.box((qx, qy, 0.25), (6.0, 2.4, 0.5), "wall")
    mb.box((qx, qy, 0.52), (6.2, 2.6, 0.08), "trim")
    mb.box((qx, qy, 0.54), (5.2, 1.7, 0.08), "water")
    for sx in (-1, 1):
        mb.cylinder((qx + sx * 3.6, qy + 0.9, 0), (qx + sx * 3.6, qy + 0.9, 0.5), 0.2, 0.3, "clay", segments=8)
        mb.sphere((qx + sx * 3.6, qy + 0.9, 0.7), 0.3, "leaves", segments=6, rings=4)
        mb.box((qx + sx * 3.7, qy - 0.8, 0.4), (0.4, 1.2, 0.08), "trim")
        for yy in (-0.5, 0.5):
            mb.box((qx + sx * 3.7, qy - 0.8 + yy, 0.2), (0.34, 0.12, 0.4), "wall_dark")
        mb.box((qx + sx * 3.7, qy - 0.8, 0.47), (0.3, 0.5, 0.06), "cloth_white")


def hunting_lodge(mb, rig, seed=84):
    rnd = random.Random(seed)
    cx, cy, w, d, h = 0.0, 1.2, 6.0, 4.2, 2.9
    mb.box((cx, cy, 0.2), (w + 0.5, d + 0.5, 0.4), "stone")
    P.log_block(mb, cx, cy, 0.4, w, d, h - 0.4)
    top = P.gable_roof(mb, cx, cy, w, d, h, 2.5, ("shingle", "shingle_dark"), rows=6, overhang=0.5, gable="plank",
                       end_overhang=0.45)
    with P.face(mb, cx, cy, w + 0.34, d + 0.34, "front") as L:
        P.plank_door(mb, 0, 0.4, w=1.0, h=1.75)
        for x in (-L * 0.32, L * 0.32):
            P.window(mb, x, 1.75, w=0.65, h=0.65)
        # Antlers over the door.
        ay = -1.48   # Hung from the porch eave.
        mb.box((0, ay, 2.3), (0.5, 0.06, 0.4), "wood")
        mb.sphere((0, ay - 0.1, 2.25), 0.12, "bone", segments=5, rings=3, scale=(1, 1, 1.3))
        for s in (-1, 1):
            P.beam(mb, (s * 0.08, ay - 0.1, 2.35), (s * 0.5, ay - 0.15, 2.75), 0.04, "bone")
            P.beam(mb, (s * 0.3, ay - 0.12, 2.55), (s * 0.32, ay - 0.2, 2.9), 0.03, "bone")
            P.beam(mb, (s * 0.5, ay - 0.15, 2.75), (s * 0.75, ay - 0.2, 2.85), 0.03, "bone")
    # The porch.
    py = cy - d / 2 - 1.2
    mb.box((cx, py + 0.6, 0.3), (w, 1.3, 0.2), "plank")
    for sx in (-1, 0, 1):
        mb.box((cx + sx * (w / 2 - 0.15), py, 1.4), (0.16, 0.16, 2.2), "log")
    mb.box((cx, py, 2.5), (w + 0.2, 0.16, 0.16), "timber")
    game.sloped_slab(mb, cx - w / 2 - 0.3, cx + w / 2 + 0.3, py - 0.4, cy - d / 2 + 0.05, 2.5, 3.0, 0.1, "shingle_dark")
    mb.box((cx - 1.8, py + 0.7, 0.75), (1.4, 0.4, 0.07), "wood")
    for s in (-0.55, 0.55):
        mb.box((cx - 1.8 + s, py + 0.7, 0.56), (0.07, 0.36, 0.34), "timber")
    with mb.placed((0, 0, 0.4)):
        game.barrel(mb, cx + 2.3, py + 0.7, h=0.8, r=0.3)
    # The stone chimney on the right end.
    sx0 = cx + w / 2 + 0.4
    mb.box((sx0, cy, 1.5), (0.9, 1.6, 3.0), "stone")
    P.prism_yz(mb, [(cy - 0.8, 3.0), (cy + 0.8, 3.0), (cy + 0.4, 4.0), (cy - 0.4, 4.0)], sx0 - 0.45, sx0 + 0.45, "stone")
    P.chimney(mb, sx0, cy, 4.0, top + 1.0, w=0.8, mat="stone", cap="stone_dark", pots=0)
    with mb.placed((sx0 + 0.45, cy, 0), math.pi / 2):
        P.scatter_face(mb, rnd, 1.4, 0.3, top, ("stone_dark", "plaster"), density=0.5, size=(0.4, 0.25))
    # Hides on stretching frames, a game rack, a kennel, a target.
    for i, x in enumerate((-4.0, -2.9)):
        for s in (-0.45, 0.45):
            P.beam(mb, (x + s, -2.9 + 0.3, 0), (x + s, -2.9, 1.7), 0.05, "timber")
        mb.box((x, -2.9 + 0.02, 1.65), (1.1, 0.06, 0.06), "timber")
        mb.box((x, -2.9 + 0.13, 0.5), (1.1, 0.06, 0.06), "timber")
        P.prism_xz(mb, [(x - 0.35, 0.6), (x + 0.35, 0.6), (x + 0.42, 1.5), (x, 1.58), (x - 0.42, 1.5)], -2.86, -2.82,
                   "hide" if i else "fur")
    rx, ry = 3.6, -2.6
    for s in (-0.7, 0.7):
        mb.box((rx + s, ry, 1.0), (0.1, 0.1, 2.0), "timber")
    mb.cylinder((rx - 0.8, ry, 1.95), (rx + 0.8, ry, 1.95), 0.04, 0.04, "wood", segments=5)
    for i, c in enumerate(("fur", "hide", "bone")):
        mb.sphere((rx - 0.4 + i * 0.4, ry, 1.5), 0.14, c, segments=5, rings=4, scale=(0.9, 0.9, 2.2))
        mb.box((rx - 0.4 + i * 0.4, ry, 1.85), (0.02, 0.02, 0.2), "rope")
    kx_, ky_ = -3.6, 0.6
    mb.box((kx_, ky_, 0.4), (1.0, 1.2, 0.8), "plank")
    mb.box((kx_, ky_ - 0.61, 0.32), (0.45, 0.04, 0.55), "charcoal")
    with mb.placed((kx_, ky_, 0), math.pi / 2):
        P.gable_roof(mb, 0, 0, 1.2, 1.0, 0.8, 0.45, ("shingle", "shingle_dark"), rows=2, overhang=0.15, gable="plank", barge=None,
                     thick=0.06)
    tx, ty = 4.4, 0.4
    for s in (-0.3, 0.3):
        P.beam(mb, (tx + 0.3, ty + s, 0), (tx, ty, 1.5), 0.05, "timber")
    mb.cylinder((tx, ty, 1.1), (tx - 0.18, ty, 1.16), 0.55, 0.55, "hay", segments=10)
    mb.cylinder((tx - 0.18, ty, 1.16), (tx - 0.21, ty, 1.17), 0.36, 0.36, "stripe_b", segments=10)
    mb.cylinder((tx - 0.21, ty, 1.17), (tx - 0.24, ty, 1.18), 0.16, 0.16, "stripe_a", segments=8)
    game.log_pile(mb, cx - 1.6, cy + d / 2 + 0.6, length=1.8, rows=2)


def make(name, fn, colors, **kw):
    def build():
        mb = P.begin()
        rig = P.Rig()
        fn(mb, rig, **kw)
        P.finish(mb, name, colors, rig)
    return build


SLATE = dict(roof=0x5A6470, roof_dark=0x46505A)

MODELS = {
    "bld_cathedral_stone": make("bld_cathedral_stone", cathedral, P.palette(**SLATE)),
    "bld_cathedral_sandstone": make("bld_cathedral_sandstone", cathedral, P.SANDSTONE_RED),
    "bld_cathedral_blue": make("bld_cathedral_blue", cathedral, P.STONE_BLUE),
    "bld_dovecote": make("bld_dovecote", dovecote, P.BASE),
    "bld_great_barn_red": make("bld_great_barn_red", great_barn, P.palette(roof=0x5A6470), roof=("slate", "slate_dark")),
    "bld_great_barn_wood": make("bld_great_barn_wood", great_barn,
                                P.palette(band=0x9A7044, tile_red_dark=0x7C5834, white=0x5A3B24),
                                roof=("thatch", "thatch_dark")),
    "bld_shipyard": make("bld_shipyard", shipyard, P.BASE),
    "bld_brewery_tiles": make("bld_brewery_tiles", brewery, P.palette(roof=0xB0503A, roof_dark=0x8E3E2A)),
    "bld_brewery_slate": make("bld_brewery_slate", brewery, P.palette(**SLATE)),
    "bld_bakery_tiles": make("bld_bakery_tiles", bakery, P.palette(roof=0xB0503A, roof_dark=0x8E3E2A)),
    "bld_bakery_thatch": make("bld_bakery_thatch", bakery, P.palette(roof=0xC9A55A, roof_dark=0xA8863F)),
    "bld_bathhouse_stone": make("bld_bathhouse_stone", bathhouse, P.BASE),
    "bld_bathhouse_sandstone": make("bld_bathhouse_sandstone", bathhouse, P.SANDSTONE_RED),
    "bld_hunting_lodge": make("bld_hunting_lodge", hunting_lodge, P.BASE),
}
