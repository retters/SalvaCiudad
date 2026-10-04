"""Mills: a watermill, a water-powered sawmill, a tower windmill and a post
mill. The wheels and the sails turn (clip `turn`)."""

import math
import random

import parts as P
from parts import game, TAU
from mathutils import Matrix, Vector


def water_wheel(mb, rig, x, y, z, R, width=0.9, paddles=12, spokes=8, seconds=6.0, direction=1):
    """A wheel whose axle runs along X through (x, y, z)."""
    name = rig.name("wheel")
    with mb.bone(name):
        mb.cylinder((x - width / 2 - 0.9, y, z), (x + width / 2 + 0.45, y, z), 0.13, 0.13, "timber", segments=8)
        mb.cylinder((x - width / 2 - 0.06, y, z), (x + width / 2 + 0.06, y, z), 0.3, 0.3, "wood", segments=8)
        for sx in (-1, 1):
            xs = x + sx * width / 2
            n = 16
            for i in range(n):
                a0, a1 = TAU * i / n, TAU * (i + 1) / n
                for rr in (R, R - 0.5):
                    P.beam(mb, (xs, y + rr * math.cos(a0), z + rr * math.sin(a0)),
                           (xs, y + rr * math.cos(a1), z + rr * math.sin(a1)), 0.11, "wood")
            for i in range(spokes):
                a = TAU * i / spokes
                P.beam(mb, (xs, y, z), (xs, y + (R - 0.05) * math.cos(a), z + (R - 0.05) * math.sin(a)), 0.09, "timber")
        for i in range(paddles):
            with mb.placed(matrix=P.turn_x((x, y, z), TAU * (i + 0.5) / paddles)):
                mb.box((x, y + R - 0.22, z), (width + 0.12, 0.6, 0.06), "plank")
    head = mb.world((x, y, z))
    axis = mb.world_dir((1, 0, 0))
    rig.bone(name, head, head + axis, None)
    rig.add("turn", seconds, lambda t: {name: [(axis, 360 * t * direction)]})
    return name


def mill_race(mb, x, y0, y1, w=1.2, flume=None, wheel=None):
    """A stone-lined channel along Y centered on x, with water; `flume` is
    (height, y of its end) for an overshot trough coming from +Y."""
    L = y1 - y0
    yc = (y0 + y1) / 2
    mb.box((x, yc, 0.12), (w, L, 0.24), "water")
    mb.box((x + w / 2 + 0.2, yc, 0.3), (0.4, L, 0.6), "wall")
    mb.box((x + w / 2 + 0.2, yc, 0.62), (0.5, L, 0.08), "wall_light")
    mb.box((x - w / 2 - 0.08, yc, 0.3), (0.16, L, 0.6), "wall_dark")
    for y in (y0 + 0.4, y1 - 0.4):
        mb.box((x, y, 0.3), (w * 0.9, 0.5, 0.08), "foam")
    if wheel:
        mb.box((x, wheel, 0.27), (w * 0.8, 1.4, 0.06), "foam")
    # A sluice gate at the upstream end.
    for sx in (-1, 1):
        mb.box((x + sx * (w / 2 + 0.05), y1 - 0.2, 0.9), (0.14, 0.14, 1.8), "timber")
    mb.box((x, y1 - 0.2, 1.75), (w + 0.4, 0.16, 0.14), "timber")
    mb.box((x, y1 - 0.2, 1.0), (w, 0.08, 0.9), "plank")
    if flume:
        fz, fy = flume
        mb.box((x, (fy + y1) / 2, fz), (w * 0.75, y1 - fy, 0.08), "plank")
        for sx in (-1, 1):
            mb.box((x + sx * w * 0.375, (fy + y1) / 2, fz + 0.2), (0.07, y1 - fy, 0.4), "plank_dark")
        mb.box((x, (fy + y1) / 2 + 0.1, fz + 0.2), (w * 0.62, y1 - fy - 0.2, 0.06), "water")
        for yy in (fy + 0.9, y1 - 0.5):
            for sx in (-1, 1):
                mb.box((x + sx * (w / 2 + 0.05), yy, fz / 2), (0.14, 0.14, fz), "timber")
            mb.box((x, yy, fz - 0.1), (w + 0.4, 0.14, 0.14), "timber")
        mb.box((x, fy - 0.08, fz - 0.25), (w * 0.55, 0.08, 0.6), "foam")


def sack(mb, x, y, z=0.0, s=1.0, mat="canvas"):
    mb.sphere((x, y, z + 0.28 * s), 0.3 * s, mat, segments=6, rings=4, scale=(1, 0.8, 1.0))
    mb.cylinder((x, y, z + 0.5 * s), (x, y, z + 0.66 * s), 0.07 * s, 0.11 * s, mat, segments=5)


def millstone(mb, x, y, z, r=0.55, lean=0.25):
    mb.cylinder((x, y, z + r), (x, y - 0.2, z + r + 0.2 * lean), r, r, "wall_dark", segments=12)
    mb.cylinder((x, y + 0.01, z + r), (x, y - 0.21, z + r + 0.2 * lean), 0.1, 0.1, "charcoal", segments=6)


def hand_cart(mb, x, y, rot=0.0):
    with mb.placed((x, y, 0), rot):
        mb.box((0, 0, 0.55), (1.5, 0.9, 0.1), "plank")
        for sy in (-1, 1):
            mb.box((0, sy * 0.45, 0.75), (1.5, 0.06, 0.34), "plank_dark")
            mb.cylinder((0, sy * 0.52, 0.42), (0, sy * 0.6, 0.42), 0.42, 0.42, "wood", segments=10)
            mb.cylinder((0, sy * 0.5, 0.42), (0, sy * 0.63, 0.42), 0.1, 0.1, "iron", segments=6)
            P.beam(mb, (0.7, sy * 0.35, 0.55), (1.7, sy * 0.35, 0.3), 0.07, "timber")
        mb.box((-0.75, 0, 0.75), (0.06, 0.9, 0.34), "plank_dark")
        sack(mb, -0.2, 0.1, 0.6)
        sack(mb, 0.3, -0.1, 0.6, s=0.9)


def watermill(mb, rig, upper="timber", roof=("roof", "roof_dark"), overshot=False, seed=6):
    rnd = random.Random(seed)
    cx, cy, w, d, h1, h2 = -0.9, 0.3, 6.0, 5.4, 3.0, 2.5
    P.stone_block(mb, cx, cy, 0, w, d, h1, rnd, density=0.3)
    z1 = h1 + 0.2
    W, D = w + 0.5, d + 0.5
    mb.box((cx, cy, h1 + 0.1), (W + 0.1, D + 0.1, 0.2), "timber")
    if upper == "stone":
        P.stone_block(mb, cx, cy, z1, w, d, h2, rnd, plinth=0, density=0.3)
        W, D = w, d
    elif upper == "log":
        P.log_block(mb, cx, cy, z1, W, D, h2)
    else:
        P.framed_block(mb, cx, cy, z1, W, D, h2, infill="plaster", cross=True)
    gable = {"stone": "wall", "log": "plank"}.get(upper, "plaster")
    with mb.placed((cx, cy, 0), math.pi / 2):
        top = P.gable_roof(mb, 0, 0, D, W, z1 + h2, 2.9, roof, rows=7, overhang=0.45, gable=gable,
                           end_overhang=0.4)
    # Front: door, windows, the loading door and its hoist under the gable.
    with P.face(mb, cx, cy, w, d, "front") as L:
        P.arched_door(mb, -0.9, 0.05, w=1.2, h=2.1, frame="wall_light")
        P.window(mb, 1.6, 1.8, w=0.7, h=0.8, frame="wall_light", shutter=None)
    e = 0.34 if upper == "log" else 0.0
    with P.face(mb, cx, cy, W + e, D + e, "front") as L:
        P.plank_door(mb, 0, z1 + 0.15, w=1.0, h=1.6)
        for x in (-L * 0.34, L * 0.34):
            P.window(mb, x, z1 + h2 * 0.55, w=0.6, h=0.7)
        mb.box((0, -0.6, z1 + h2 + 1.5), (0.16, 1.5, 0.16), "timber")
        mb.box((0, -1.2, z1 + h2 + 0.6), (0.03, 0.03, 1.7), "rope")
    sack(mb, cx, cy - D / 2 - 1.2, z1 + h2 - 0.75, s=0.9)
    for side in ("left", "back"):
        with P.face(mb, cx, cy, w, d, side) as L:
            for x in (-L * 0.25, L * 0.25):
                P.window(mb, x, 1.8, w=0.6, h=0.7, frame="wall_light", shutter=None)
        with P.face(mb, cx, cy, W + e, D + e, side) as L:
            for x in (-L * 0.25, L * 0.25):
                P.window(mb, x, z1 + h2 * 0.55, w=0.6, h=0.7)
    P.chimney(mb, cx - 1.6, cy + 1.2, z1 + h2 + 0.8, top + 0.8, w=0.7, mat="wall", cap="wall_dark")
    # The wheel and its race on the right side.
    wx = cx + w / 2 + 0.85
    R = 2.1 if not overshot else 1.9
    wz = 2.2 if not overshot else 2.05
    mill_race(mb, wx, -3.9, 3.9, w=1.3, flume=(wz + R + 0.3, 0.2) if overshot else None, wheel=cy - 0.6)
    water_wheel(mb, rig, wx, cy, wz, R, width=0.95, direction=-1 if overshot else 1)
    mb.box((cx + w / 2 + 0.1, cy, wz), (0.3, 0.9, 0.9), "wall_light")  # The bearing block on the wall.
    mb.box((wx + 0.95, cy, wz / 2), (0.3, 0.5, wz), "timber")           # The outer bearing post.
    mb.box((wx + 0.95, cy, wz + 0.1), (0.4, 0.7, 0.3), "timber")
    # A footbridge over the race.
    mb.box((wx + 0.1, -3.0, 0.72), (2.4, 1.1, 0.1), "plank")
    for sy in (-1, 1):
        for sx in (-1, 1):
            mb.box((wx + 0.1 + sx * 1.1, -3.0 + sy * 0.5, 1.15), (0.08, 0.08, 0.9), "timber")
        mb.box((wx + 0.1, -3.0 + sy * 0.5, 1.55), (2.3, 0.07, 0.07), "timber")
    # The yard on the left: sacks, a millstone, a cart.
    millstone(mb, cx + 2.2, cy - d / 2 - 0.25, 0.0)
    for i, (x, y) in enumerate(((cx - 2.4, -3.0), (cx - 1.9, -3.1), (cx - 2.2, -3.5))):
        sack(mb, x, y)
    sack(mb, cx - 2.15, -3.1, 0.45, s=0.9)
    hand_cart(mb, cx - 0.3, -3.6, 0.15)
    game.barrel(mb, cx - 2.6, cy + d / 2 + 0.5, h=0.8, r=0.3)


def sawmill(mb, rig, roof=("shingle", "shingle_dark"), seed=8):
    rnd = random.Random(seed)
    cx, cy, w, d = -1.2, 0.6, 6.4, 3.8
    x0, x1 = cx - w / 2, cx + w / 2
    # Stone piers and a plank floor.
    for x in (x0 + 0.3, cx, x1 - 0.3):
        for y in (cy - d / 2 + 0.3, cy + d / 2 - 0.3):
            mb.box((x, y, 0.25), (0.6, 0.6, 0.5), "wall")
    mb.box((cx, cy, 0.56), (w, d, 0.12), "plank")
    for i in range(1, 8):
        mb.box((cx, cy - d / 2 + i * d / 8, 0.625), (w, 0.03, 0.01), "plank_dark")
    # Posts, braces and the roof.
    for x in (x0 + 0.1, cx, x1 - 0.1):
        for sy in (-1, 1):
            y = cy + sy * (d / 2 - 0.1)
            mb.box((x, y, 2.1), (0.2, 0.2, 3.0), "timber")
            P.beam(mb, (x, y, 2.9), (x + (0.6 if x < x1 - 0.5 else -0.6), y, 3.55), 0.1, "timber")
    for sy in (-1, 1):
        mb.box((cx, cy + sy * (d / 2 - 0.1), 3.6), (w + 0.2, 0.2, 0.2), "timber")
    mb.box((cx, cy + d / 2 - 0.05, 1.5), (w - 0.3, 0.08, 1.8), "plank")  # The back wall, half high.
    P.gable_roof(mb, cx, cy, w, d, 3.7, 1.7, roof, rows=5, overhang=0.5, gable=None, barge="timber")
    for x in (x0, x1):
        mb.box((x, cy, 3.75), (0.16, d, 0.16), "timber")
        mb.box((x, cy, 4.5), (0.14, 0.14, 1.5), "timber")
    # The saw frame and the blade, which goes up and down.
    sx = cx + 1.0
    for sy in (-1, 1):
        mb.box((sx, cy + sy * 0.75, 2.0), (0.22, 0.22, 2.9), "timber")
    mb.box((sx, cy, 3.4), (0.26, 1.8, 0.24), "timber")
    with mb.bone("saw"):
        mb.box((sx, cy, 2.75), (0.14, 1.2, 0.1), "wood")
        mb.box((sx, cy, 0.95), (0.14, 1.2, 0.1), "wood")
        for sy in (-1, 1):
            mb.box((sx, cy + sy * 0.55, 1.85), (0.1, 0.1, 1.8), "wood")
        mb.box((sx, cy, 1.85), (0.03, 0.22, 1.8), "iron")
        for i in range(8):
            mb.cylinder((sx, cy - 0.11, 1.05 + i * 0.22), (sx, cy - 0.2, 1.0 + i * 0.22), 0.05, 0.0, "iron", segments=4)
    rig.bone("saw", (sx, cy, 0.9), (sx, cy, 1.9), None)
    rig.add("turn", 6.0, lambda t: ({}, {"saw": (0, 0, 0.3 * math.sin(TAU * 6 * t))}))
    # The log on its carriage, half sawn into boards.
    mb.box((cx - 0.6, cy, 0.72), (4.4, 1.0, 0.12), "wood")
    for x in (cx - 2.4, cx - 0.9, cx + 0.5):
        mb.cylinder((x, cy - 0.6, 0.7), (x, cy + 0.6, 0.7), 0.1, 0.1, "iron", segments=6)
    mb.cylinder((x0 + 0.3, cy, 1.2), (sx, cy, 1.2), 0.42, 0.42, "log", segments=8)
    mb.cylinder((x0 + 0.28, cy, 1.2), (x0 + 0.31, cy, 1.2), 0.36, 0.36, "log_end", segments=8)
    for i in range(4):
        mb.box((sx + 0.9, cy - 0.27 + i * 0.18, 1.2), (1.7, 0.1, 0.62 - 0.1 * abs(i - 1.5)), "log_end")
    # The wheel, its race and the crank that drives the saw.
    wx = x1 + 1.0
    mill_race(mb, wx, -3.4, 3.4, w=1.3, wheel=cy - 0.6)
    water_wheel(mb, rig, wx, cy, 1.95, 1.85, width=0.95)
    mb.box((x1 + 0.05, cy, 1.0), (0.3, 0.6, 2.0), "timber")
    mb.box((wx + 0.95, cy, 1.0), (0.3, 0.5, 2.0), "timber")
    # Timber in and boards out.
    game.log_pile(mb, cx - 1.6, -2.6, length=2.6, rows=3)
    for r in range(5):
        for i in range(4):
            mb.box((cx + 2.0, -3.0 + i * 0.27, 0.06 + r * 0.11), (2.6, 0.24, 0.09), "log_end" if (i + r) % 2 else "wood_light")
    for x in (cx + 1.0, cx + 3.0):
        mb.box((x, -2.6, 0.03), (0.12, 1.2, 0.06), "timber")
    mb.cylinder((cx - 3.6, -1.6, 0), (cx - 3.6, -1.6, 0.5), 0.3, 0.3, "log", segments=8)
    mb.box((cx - 3.6, -1.6, 0.85), (0.05, 0.12, 0.7), "wood")
    mb.box((cx - 3.6, -1.6, 0.6), (0.22, 0.05, 0.14), "iron")


def sails(mb, rig, hub, length, n=4, width=1.35, cloth=True, seconds=8.0, shaft=1.8):
    """Lattice sails turning about an axle along Y; the hub faces -Y."""
    hx, hy, hz = hub
    name = rig.name("sails")
    with mb.bone(name):
        mb.cylinder((hx, hy + shaft, hz), (hx, hy - 0.5, hz), 0.15, 0.15, "timber", segments=8)
        mb.cylinder((hx, hy - 0.12, hz), (hx, hy - 0.46, hz), 0.34, 0.26, "wood", segments=8)
        y = hy - 0.3
        for k in range(n):
            with mb.placed(matrix=P.turn_y(hub, TAU * k / n + 0.5)):
                mb.box((hx + length / 2, y, hz), (length, 0.13, 0.15), "timber")
                x0, x1 = hx + length * 0.2, hx + length
                for z in (hz + width * 0.5, hz + width):
                    mb.box(((x0 + x1) / 2, y, z), (x1 - x0, 0.06, 0.07), "wood")
                m = max(3, int((x1 - x0) / 0.55))
                for i in range(m + 1):
                    mb.box((x0 + (x1 - x0) * i / m, y, hz + width / 2), (0.07, 0.06, width), "wood")
                if cloth:
                    mb.box(((x0 + x1) / 2, y + 0.045, hz + width / 2 + 0.04), (x1 - x0 - 0.12, 0.025, width - 0.14),
                           "canvas")
    head = mb.world(hub)
    axis = mb.world_dir((0, 1, 0))
    rig.bone(name, head, head - axis, None)
    rig.add("turn", seconds, lambda t: {name: [(axis, 360 * t)]})


def tower_mill(mb, rig, seg=14, cap=("shingle", "shingle_dark"), smock=False, seed=2):
    rnd = random.Random(seed)
    x, y, h, r1, taper = 0.0, 0.3, 10.5, 2.0, 0.9

    def r_at(z):
        return (r1 + taper * (1 - z / h)) * (math.cos(math.pi / seg) if seg > 8 else 0.94)

    P.round_tower(mb, x, y, r1, h, rnd, seg=seg, slits=0, bands=False, taper=taper,
                  density=0.0 if smock else 0.22)
    if smock:  # A wooden mill on a stone base: boards and corner posts.
        mb.cylinder((x, y, 0), (x, y, 1.6), r1 + taper + 0.2, r1 + taper * 0.85 + 0.2, "stone", segments=seg)
        for i in range(seg):
            a = TAU * i / seg
            P.beam(mb, (x + (r1 + taper * 0.85 + 0.03) * math.cos(a), y + (r1 + taper * 0.85 + 0.03) * math.sin(a), 1.6),
                   (x + (r1 + 0.03) * math.cos(a), y + (r1 + 0.03) * math.sin(a), h), 0.12, "timber")
        for z in (3.4, 5.4, 7.4, 9.2):
            rr = r1 + taper * (1 - z / h) + 0.03
            mb.cylinder((x, y, z - 0.05), (x, y, z + 0.05), rr, rr - 0.01, "wall_dark", segments=seg)
    # Door and windows.
    with mb.placed((x, y - r_at(1.0) - 0.02, 0)):
        P.arched_door(mb, 0, 0.1, w=1.1, h=2.0, frame="trim")
    for i, (a, z) in enumerate(((-math.pi / 2, 5.6), (-math.pi / 2, 8.4), (0.3, 2.2), (0.3, 6.6), (math.pi - 0.3, 2.2),
                                (math.pi - 0.3, 6.6), (math.pi / 2, 4.6), (math.pi / 2, 8.2))):
        rr = r_at(z)
        mb.box((x + (rr - 0.02) * math.cos(a), y + (rr - 0.02) * math.sin(a), z), (0.22, 0.8, 1.0), "trim", rotation_z=a)
        mb.box((x + (rr + 0.02) * math.cos(a), y + (rr + 0.02) * math.sin(a), z), (0.22, 0.55, 0.78), "window",
               rotation_z=a)
    # The stage: a gallery around the tower to reach the sails.
    gz = 3.3
    rg = r1 + taper * (1 - gz / h) + 1.15
    mb.cylinder((x, y, gz - 0.14), (x, y, gz), rg, rg, "plank", segments=16)
    for i in range(16):
        a = TAU * (i + 0.5) / 16
        c, s = math.cos(a), math.sin(a)
        if i % 2 == 0:
            P.beam(mb, (x + (rg - 1.25) * c, y + (rg - 1.25) * s, gz - 1.3), (x + (rg - 0.1) * c, y + (rg - 0.1) * s, gz - 0.1),
                   0.11, "timber")
        mb.box((x + (rg - 0.08) * c, y + (rg - 0.08) * s, gz + 0.5), (0.09, 0.09, 1.0), "timber", rotation_z=a)
        a2 = TAU * (i + 1.5) / 16
        for zz in (gz + 0.5, gz + 0.98):
            P.beam(mb, (x + (rg - 0.08) * c, y + (rg - 0.08) * s, zz),
                   (x + (rg - 0.08) * math.cos(a2), y + (rg - 0.08) * math.sin(a2), zz), 0.06, "wood")
    with mb.placed((x + rg - 0.2, y + 0.9, 0), 0.0):  # The stair up to the stage, on the right.
        P.stairs(mb, 0, -4.2, 0, gz - 0.1, 1.0, 3.6, mat="plank", solid=False)
        for sx in (-0.5, 0.5):
            P.beam(mb, (sx, -4.2, 0), (sx, -0.6, gz - 0.14), 0.1, "timber")
    # The cap, the wind shaft and the tail pole.
    mb.cylinder((x, y, h), (x, y, h + 0.3), r1 + 0.18, r1 + 0.18, "timber", segments=seg)
    P.dome(mb, x, y, h + 0.3, r1 + 0.1, 2.1, cap, rows=4, seg=12, finial="timber")
    hub = (x, y - r1 - 0.75, h + 1.0)
    mb.box((x, y - r1 * 0.75, h + 1.0), (1.3, r1 * 0.9, 1.2), cap[1])
    P.prism_xz(mb, [(-0.75, h + 1.6), (0.75, h + 1.6), (0, h + 2.1)], y - r1 * 0.75 - r1 * 0.45, y - r1 * 0.3, cap[0])
    sails(mb, rig, hub, 6.1, shaft=r1 + 1.0)
    P.beam(mb, (x, y + r1 - 0.2, h + 0.5), (x, y + rg + 0.2, gz + 1.2), 0.11, "timber")
    for sx in (-1, 1):
        P.beam(mb, (x + sx * 1.1, y + r1 * 0.7, h + 0.4), (x, y + rg + 0.2, gz + 1.2), 0.07, "timber")
    mb.cylinder((x - 0.02, y + rg + 0.2, gz + 1.0), (x + 0.02, y + rg + 0.2, gz + 1.0), 0.3, 0.3, "wood", segments=8)
    # Sacks and a millstone at the door.
    sack(mb, x - 1.3, y - r_at(0) - 0.6)
    sack(mb, x - 1.8, y - r_at(0) - 0.4, s=0.9)
    millstone(mb, x + 1.5, y - r_at(0) - 0.35, 0.0)


def post_mill(mb, rig, roof=("shingle", "shingle_dark"), body="plank", seed=1):
    with mb.placed((0, -0.5, 0)):
        for a in (0.0, math.pi / 2):
            mb.box((0, 0, 0.62), (4.6, 0.32, 0.32), "timber", rotation_z=a)
            for s in (-1, 1):
                c, sn = math.cos(a) * s, math.sin(a) * s
                mb.box((2.05 * c, 2.05 * sn, 0.23), (0.7, 0.7, 0.46), "wall", rotation_z=a)
                P.beam(mb, (1.9 * c, 1.9 * sn, 0.75), (0.15 * c, 0.15 * sn, 2.5), 0.16, "timber")
        mb.box((0, 0, 1.9), (0.5, 0.5, 2.9), "timber")
        z0, w, d, h = 2.5, 3.2, 3.8, 4.2
        mb.box((0, 0, z0 - 0.1), (w + 0.2, d + 0.2, 0.25), "timber")
        P.plank_block(mb, 0, 0, z0, w, d, h, mat=body, dark="plank_dark" if body == "plank" else "timber")
        with mb.placed((0, 0, 0), math.pi / 2):
            top = P.gable_roof(mb, 0, 0, d, w, z0 + h, 1.7, roof, rows=5, overhang=0.3, gable=body, end_overhang=0.3)
        with P.face(mb, 0, 0, w, d, "front"):
            P.window(mb, 0, z0 + 1.2, w=0.5, h=0.6, shutter=None)
        for side in ("left", "right"):
            with P.face(mb, 0, 0, w, d, side):
                P.window(mb, 0.6, z0 + 2.6, w=0.5, h=0.6, shutter=None)
        with P.face(mb, 0, 0, w, d, "back"):
            P.plank_door(mb, 0, z0 + 0.1, w=0.9, h=1.7)
            mb.box((0, -0.5, z0 + 0.02), (1.6, 1.0, 0.1), "plank")  # The porch.
            for sx in (-1, 1):
                mb.box((sx * 0.75, -0.95, z0 + 0.5), (0.08, 0.08, 1.0), "timber")
        # The ladder and the tail pole, down to the ground at the back.
        yb = d / 2 + 1.0
        for sx in (-0.45, 0.45):
            P.beam(mb, (sx, yb, z0), (sx, yb + 1.9, 0.05), 0.1, "timber")
        for i in range(9):
            t = (i + 0.5) / 9
            mb.box((0, yb + 1.9 * t, z0 * (1 - t)), (0.9, 0.22, 0.06), "plank")
        P.beam(mb, (0, d / 2, z0 + 0.3), (0, yb + 2.4, 0.9), 0.1, "timber")
        mb.cylinder((-0.03, yb + 2.4, 0.5), (0.03, yb + 2.4, 0.5), 0.45, 0.45, "wood", segments=8)
        sails(mb, rig, (0, -d / 2 - 0.55, z0 + h - 0.9), 4.7, width=1.15, seconds=7.0, shaft=1.2)
        sack(mb, 2.0, -1.2)
        sack(mb, 2.4, -0.8, s=0.9)


MIRRORED = ("watermill", "sawmill")  # Their wheel goes on the left, where the review camera sees it.


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


def roofed(roof, **roles):
    return P.palette(**dict(P.ROOFS[roof], **roles))


WOODEN = dict(wall=0x9A7044, wall_dark=0x7C5834, wall_light=0xAE8454, trim=0x5A3B24)
BRICK = dict(wall=0xA65A3E, wall_dark=0x844432, wall_light=0xBE7252, trim=0xCFC8B8)
WHITE = dict(wall=0xECE6D6, wall_dark=0xD6CEBA, wall_light=0xF6F2E6, trim=0x5A3B24)

MODELS = {
    "bld_watermill_timber_tiles": make("bld_watermill_timber_tiles", watermill, roofed("tiles"), upper="timber"),
    "bld_watermill_timber_thatch": make("bld_watermill_timber_thatch", watermill, roofed("thatch"), upper="timber",
                                        overshot=True),
    "bld_watermill_stone_slate": make("bld_watermill_stone_slate", watermill, roofed("slate"), upper="stone"),
    "bld_watermill_log_shingles": make("bld_watermill_log_shingles", watermill, roofed("shingles"), upper="log",
                                       overshot=True),
    "bld_watermill_timber_blue": make("bld_watermill_timber_blue", watermill, roofed("blue"), upper="timber"),
    "bld_windmill_tower_blue": make("bld_windmill_tower_blue", tower_mill, P.BASE, cap=("roof", "roof_dark")),
    "bld_sawmill_water": make("bld_sawmill_water", sawmill, P.BASE),
    "bld_sawmill_water_thatch": make("bld_sawmill_water_thatch", sawmill, P.BASE, roof=("thatch", "thatch_dark")),
    "bld_windmill_tower_stone": make("bld_windmill_tower_stone", tower_mill, P.BASE),
    "bld_windmill_tower_brick": make("bld_windmill_tower_brick", tower_mill, P.palette(**BRICK),
                                     cap=("slate", "slate_dark")),
    "bld_windmill_tower_white": make("bld_windmill_tower_white", tower_mill, P.palette(**WHITE),
                                     cap=("tile_red", "tile_red_dark")),
    "bld_windmill_smock_wood": make("bld_windmill_smock_wood", tower_mill, P.palette(**WOODEN), seg=8, smock=True),
    "bld_windmill_tower_sandstone": make("bld_windmill_tower_sandstone", tower_mill,
                                         P.palette(wall=0xD4BC8C, wall_dark=0xB69C6E, wall_light=0xE6D4AA, trim=0xF0E4C4),
                                         cap=("tile_red", "tile_red_dark")),
    "bld_windmill_post": make("bld_windmill_post", post_mill, P.BASE),
    "bld_windmill_post_white": make("bld_windmill_post_white", post_mill, P.BASE, body="plaster",
                                    roof=("tile_red", "tile_red_dark")),
}
