"""Water supply proposals: wells that work, cisterns, a modular aqueduct,
wooden pipes and what a town needs to put out a fire. See ../LEEME.md.

    blender --background --factory-startup --python art/blender/proposals/water/build.py -- [ids]
"""

import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import _kit as kit  # noqa: E402
import _shapes  # noqa: E402
import common  # noqa: E402
from _shapes import TAU, barrel, beam, gable_roof, log, rock, rope, shed_roof, solid  # noqa: E402

FAMILY = "water"
C = common.rgb
COLORS = {
    **_shapes.COLORS,
    "water": C(0x4A8FC0), "water_light": C(0x7AB8E0), "brick": C(0xA0553A), "brick_dark": C(0x84422C), "tile": C(0x9A4A2E), "tile_dark": C(0x7E3A24),
    "shingle": C(0x6A5038), "shingle_dark": C(0x54402C), "thatch": C(0xC9A55A), "thatch_dark": C(0xA8863F), "cave": C(0x14110F), "moss": C(0x5E8A3A),
    "copper": C(0xB8703A), "paint_red": C(0xB8362E), "paint_white": C(0xECE6D6), "grass": C(0x6A9440), "soil": C(0x6A4A30), "bell": C(0xB8923A),
    "bronze": C(0x9A7A3A),
}
STONE = {"wall": "stone", "dark": "stone_dark", "light": "stone_light"}
BRICK = {"wall": "brick", "dark": "brick_dark", "light": "stone_light"}


def ring_wall(mb, x, y, r, z0, z1, pal, n=10):
    mb.cylinder((x, y, z0), (x, y, z1), r, r, pal["wall"], segments=n)
    mb.cylinder((x, y, z1 - 0.02), (x, y, z1 + 0.1), r + 0.06, r + 0.06, pal["light"], segments=n)
    mb.cylinder((x, y, z1 + 0.06), (x, y, z1 + 0.11), r - 0.16, r - 0.16, "cave", segments=n)
    for k in range(n // 2):
        a = TAU * k / (n // 2) + 0.3
        mb.box((x + math.cos(a) * r, y + math.sin(a) * r, (z0 + z1) / 2 + 0.1 * (k % 2)), (0.3, 0.1, 0.16), pal["dark"], rotation_z=a + math.pi / 2)


def windlass(mb, x, y, z, half, bone, depth_bone):
    """A crank and drum over a well; its bucket hangs from `depth_bone`."""
    w = {bone: 1.0}
    mb.cylinder((x - half, y, z), (x + half, y, z), 0.09, 0.09, "plank_dark", w, segments=8)
    mb.cylinder((x - half - 0.25, y, z), (x - half, y, z), 0.025, 0.025, "iron", w, segments=5)
    beam(mb, (x - half - 0.25, y, z), (x - half - 0.25, y, z - 0.25), 0.02, "iron", w)
    mb.cylinder((x - half - 0.42, y, z - 0.25), (x - half - 0.25, y, z - 0.25), 0.03, 0.03, "pole", w, segments=6)
    for k in range(4):
        mb.cylinder((x - 0.12 + 0.08 * k, y, z), (x - 0.06 + 0.08 * k, y, z), 0.105, 0.105, "rope", w, segments=8)
    wb = {depth_bone: 1.0}
    rope(mb, (x, y, z - 0.09), (x, y, z - 0.95), 0.012, wb)
    mb.cylinder((x, y, z - 1.3), (x, y, z - 1.0), 0.14, 0.17, "plank_light", wb, segments=8)
    mb.cylinder((x, y, z - 1.04), (x, y, z - 1.01), 0.15, 0.15, "water", wb, segments=8)
    for sx in (-1, 1):
        rope(mb, (x + sx * 0.15, y, z - 1.0), (x, y, z - 0.93), 0.008, wb)
    return [(bone, (x, y, z), (x + 0.5, y, z), None), (depth_bone, (x, y, z - 0.09), (x, y, z - 1.0), None)]


def draw_pose(bone, depth_bone, travel=0.7):
    def pose(t):
        s = 0.5 - 0.5 * math.cos(TAU * t)   # Down and up again.
        return {bone: [(kit.X, 360.0 * 2 * s)]}, {depth_bone: (0, 0, -travel * s)}
    return pose


def well(name, style):
    def build():
        mb = kit.begin()
        pal = BRICK if style == "brick" else STONE
        mb.cylinder((0, 0, 0), (0, 0, 0.12), 1.5, 1.4, pal["dark"], segments=10)
        ring_wall(mb, 0, 0, 0.8, 0.1, 0.95, pal)
        if style == "log":
            for sx in (-1, 1):
                log(mb, (sx * 0.95, 0, 0), (sx * 0.95, 0, 2.5), 0.09)
            gable_roof(mb, 0, 0, 2.0, 1.4, 2.5, 0.7, ("thatch", "thatch_dark"), 0.25, 2, 0.07)
        else:
            for sx in (-1, 1):
                mb.box((sx * 0.95, 0, 1.4), (0.2, 0.2, 2.6), pal["wall"])
                mb.box((sx * 0.95, 0, 2.72), (0.3, 0.3, 0.1), pal["light"])
            gable_roof(mb, 0, 0, 2.1, 1.5, 2.75, 0.8, ("tile", "tile_dark") if style == "brick" else ("shingle", "shingle_dark"), 0.25, 3, 0.07)
        bones = windlass(mb, 0, 0, 2.15, 0.85, "crank", "bucket")
        mb.cylinder((1.3, -0.8, 0.12), (1.3, -0.8, 0.45), 0.15, 0.19, "plank_light", segments=8)
        mb.cylinder((1.3, -0.8, 0.41), (1.3, -0.8, 0.44), 0.16, 0.16, "water", segments=8)
        kit.save(mb, FAMILY, name, COLORS, mech=kit.Mech(bones).clip("draw", 6.0, draw_pose("crank", "bucket")))
    return build


def pump_well():
    """A dwarf-made well: a cast pump with a long handle over a stone basin."""
    mb = kit.begin()
    mb.cylinder((0, 0, 0), (0, 0, 0.14), 1.3, 1.2, "stone_dark", segments=8)
    mb.cylinder((0, 0, 0.14), (0, 0, 1.3), 0.16, 0.13, "iron", segments=8)
    mb.cylinder((0, 0, 1.3), (0, 0, 1.5), 0.2, 0.2, "bronze", segments=8)
    mb.cylinder((0, 0, 1.5), (0, 0, 1.7), 0.13, 0.0, "bronze", segments=8)
    mb.cylinder((0, -0.1, 1.05), (0, -0.55, 0.95), 0.06, 0.05, "iron", segments=6)
    mb.cylinder((0, -0.55, 0.95), (0, -0.55, 0.85), 0.05, 0.06, "bronze", segments=6)
    w = {"handle": 1.0}
    beam(mb, (0, 0.1, 1.35), (0, 1.3, 1.75), 0.035, "iron", w)
    mb.cylinder((-0.1, 1.3, 1.75), (0.1, 1.3, 1.75), 0.045, 0.045, "pole", w, segments=6)
    beam(mb, (0, 0.1, 1.35), (0, 0.0, 1.6), 0.03, "iron", w)
    for i in range(8):   # The basin under the spout.
        a0, a1 = TAU * i / 8, TAU * (i + 1) / 8
        solid(mb, [(math.cos(a0) * 0.55, -0.6 + math.sin(a0) * 0.45, 0.14), (math.cos(a1) * 0.55, -0.6 + math.sin(a1) * 0.45, 0.14),
                   (math.cos(a1) * 0.6, -0.6 + math.sin(a1) * 0.5, 0.5), (math.cos(a0) * 0.6, -0.6 + math.sin(a0) * 0.5, 0.5)],
              (math.cos((a0 + a1) / 2) * 0.08, math.sin((a0 + a1) / 2) * 0.08, 0), "stone" if i % 2 else "stone_light")
    mb.cylinder((0, -0.6, 0.4), (0, -0.6, 0.44), 0.5, 0.5, "water", segments=8)
    ws = {"stream": 1.0}
    mb.cylinder((0, -0.55, 0.85), (0, -0.56, 0.44), 0.03, 0.04, "water_light", ws, segments=5)
    pose = lambda t: ({"handle": [(kit.X, 20.0 * math.sin(TAU * 2 * t))]}, {"stream": (0, 0, 0.04 * math.sin(TAU * 4 * t))})   # noqa: E731
    mech = kit.Mech([("handle", (0, 0.1, 1.35), (0, 1.3, 1.75), None), ("stream", (0, -0.55, 0.85), (0, -0.55, 0.44), None)]).clip("pump", 3.0, pose)
    kit.save(mb, FAMILY, "well_pump", COLORS, mech=mech)


def horse_gin():
    """A deep well raised by a horse walking round a capstan."""
    mb = kit.begin()
    import _animals
    COLORS.update(_animals.COLORS)
    ring_wall(mb, 0, -3.4, 0.9, 0.0, 0.8, STONE)
    for sx in (-1, 1):
        log(mb, (sx * 1.1, -3.4, 0), (sx * 0.2, -3.4, 3.0), 0.09)
    mb.cylinder((-0.3, -3.4, 2.9), (0.3, -3.4, 2.9), 0.2, 0.2, "plank_dark", segments=8)      # The headgear pulley.
    rope(mb, (0, -3.4, 2.7), (0, -3.4, 0.9), 0.015)
    rope(mb, (0, -3.3, 3.05), (0, -0.2, 1.75), 0.015)
    mb.cylinder((0, 0, 0), (0, 0, 0.2), 0.5, 0.45, "stone_dark", segments=8)
    w = {"capstan": 1.0}
    mb.cylinder((0, 0, 0.2), (0, 0, 2.0), 0.14, 0.12, "pole_dark", w, segments=8)
    mb.cylinder((0, 0, 1.45), (0, 0, 1.95), 0.4, 0.4, "plank", w, segments=10)
    for zz in (1.45, 1.9):
        mb.cylinder((0, 0, zz), (0, 0, zz + 0.05), 0.46, 0.46, "plank_dark", w, segments=10)
    beam(mb, (0, 0, 1.3), (2.8, 0, 1.25), 0.06, "pole", w)                                   # The sweep the horse pulls.
    mb.cylinder((0, 0, 0.02), (0, 0, 0.05), 3.3, 3.3, "soil", segments=14)                    # The track it has worn.
    mb.cylinder((0, 0, 0.03), (0, 0, 0.06), 2.3, 2.3, "grass", segments=14)
    horse = _animals.draft_animal(mb, 0.0, "h_", "horse", "coat_brown", "mane_dark", x=2.8)
    bones = [("capstan", (0, 0, 0.2), (0, 0, 2.0), None)]
    for name, head, tail, parent in horse["bones"]:
        bones.append((name, head, tail, parent or "capstan"))

    def turn(t):
        turns, moves = horse["gait"]((t * 8) % 1.0, 16.0)
        turns["capstan"] = [(kit.Z, -360.0 * t)]
        return turns, moves

    kit.save(mb, FAMILY, "well_horse_gin", COLORS, mech=kit.Mech(bones).clip("turn", 12.0, turn))


def cistern(name, pal):
    def build():
        mb = kit.begin()
        mb.box((0, 0, 0.2), (6.0, 5.0, 0.4), pal["dark"])
        mb.box((0, 0, 0.55), (5.6, 4.6, 0.3), pal["wall"])
        n = 6
        for i in range(n):   # A low vault over the tank.
            a0, a1 = math.pi * i / n, math.pi * (i + 1) / n
            solid(mb, [(-2.8, math.cos(a0) * 2.3, 0.7 + math.sin(a0) * 1.1), (2.8, math.cos(a0) * 2.3, 0.7 + math.sin(a0) * 1.1), (2.8, math.cos(a1) * 2.3, 0.7 + math.sin(a1) * 1.1),
                       (-2.8, math.cos(a1) * 2.3, 0.7 + math.sin(a1) * 1.1)], (0, -math.cos((a0 + a1) / 2) * 0.15, -math.sin((a0 + a1) / 2) * 0.15), pal["wall"] if i % 2 else pal["light"])
        for sx in (-1, 1):
            solid(mb, [(sx * 2.8, -2.3, 0.7), (sx * 2.8, 2.3, 0.7), (sx * 2.8, 1.6, 1.5), (sx * 2.8, 0, 1.8), (sx * 2.8, -1.6, 1.5)], (-sx * 0.2, 0, 0), pal["dark"])
        mb.box((0, -2.5, 0.9), (1.2, 0.5, 1.0), pal["wall"])                                   # The door to the steps down.
        mb.box((0, -2.77, 0.85), (0.8, 0.06, 0.8), "plank_dark")
        mb.box((0, -2.8, 0.85), (0.5, 0.03, 0.06), "iron")
        ring_wall(mb, 1.6, 0, 0.45, 1.6, 2.1, pal, 8)                                          # The draw shaft on top.
        w = {"lid": 1.0}
        mb.cylinder((1.6, 0, 2.2), (1.6, 0, 2.26), 0.5, 0.5, "plank", w, segments=8)
        mb.box((1.6, -0.3, 2.3), (0.2, 0.06, 0.06), "iron", w)
        for k in range(4):                                                                   # Gutters bring the rain from the roofs.
            beam(mb, (-3.6 + 0.0, -1.5 + 1.0 * k, 2.6), (-2.2, -1.5 + 1.0 * k, 1.5), 0.06, "plank_dark")
        mb.box((-3.6, 0, 2.62), (0.14, 3.6, 0.14), "plank_dark")
        for sy in (-1.7, 1.7):
            mb.cylinder((-3.6, sy, 0), (-3.6, sy, 2.6), 0.07, 0.06, "pole", segments=6)
        mb.cylinder((2.4, -2.9, 0), (2.4, -2.9, 0.3), 0.16, 0.2, "plank_light", segments=8)

        def lift(up):
            return lambda t: ({"lid": [(kit.X, 75.0 * (kit.smooth(t) if up else 1 - kit.smooth(t)))]}, {})

        mech = kit.Mech([("lid", (1.6, 0.5, 2.2), (1.6, 0.0, 2.2), None)]).clip("open", 1.2, lift(True), loops=False).clip("close", 1.2, lift(False), loops=False)
        kit.save(mb, FAMILY, name, COLORS, mech=mech)
    return build


def water_tower():
    mb = kit.begin()
    for sx in (-1, 1):
        for sy in (-1, 1):
            log(mb, (sx * 1.5, sy * 1.5, 0), (sx * 1.1, sy * 1.1, 4.6), 0.11)
    for z, k in ((1.5, 1.37), (3.2, 1.22)):
        for s in (-1, 1):
            beam(mb, (-k, s * k, z), (k, s * k, z), 0.05, "pole_dark")
            beam(mb, (s * k, -k, z), (s * k, k, z), 0.05, "pole_dark")
    for s in (-1, 1):
        beam(mb, (-1.37, s * 1.37, 1.5), (1.22, s * 1.22, 3.2), 0.04, "pole_dark")
        beam(mb, (s * 1.37, 1.37, 1.5), (s * 1.22, -1.22, 3.2), 0.04, "pole_dark")
    mb.box((0, 0, 4.65), (2.8, 2.8, 0.12), "plank_dark")
    mb.cylinder((0, 0, 4.7), (0, 0, 6.6), 1.3, 1.4, "plank", segments=12)
    for zz in (4.9, 5.6, 6.3):
        mb.cylinder((0, 0, zz), (0, 0, zz + 0.07), 1.34 + 0.05 * (zz - 4.7), 1.34 + 0.05 * (zz - 4.7), "iron", segments=12)
    mb.cylinder((0, 0, 6.6), (0, 0, 7.5), 1.55, 0.0, "shingle", segments=12)
    mb.cylinder((0.6, -1.25, 4.9), (0.6, -1.8, 4.6), 0.07, 0.06, "iron", segments=6)        # The spout and its pull chain.
    mb.cylinder((0.6, -1.8, 4.6), (0.6, -1.8, 4.3), 0.06, 0.1, "iron", segments=6)
    rope(mb, (0.6, -1.8, 4.5), (0.9, -1.8, 1.4), 0.012)
    for sy in (-0.2, 0.2):                                                                   # A ladder.
        beam(mb, (-1.9, sy, 0), (-1.3, sy, 6.4), 0.035, "pole")
    for k in range(15):
        u = (k + 0.5) / 15.5
        beam(mb, (-1.9 + 0.6 * u, -0.2, 6.4 * u), (-1.9 + 0.6 * u, 0.2, 6.4 * u), 0.022, "pole_dark")
    barrel(mb, 0.6, -1.8, 0.0, 0.9, 0.34)
    kit.save(mb, FAMILY, "water_tower", COLORS)


def aqueduct(name, pal, piece):
    """A 4 m module along X, its channel 5 m up; the pier stands under a joint."""
    def build():
        mb = kit.begin()
        top, w_ = 5.0, 1.4

        def channel(x0, x1):
            mb.box(((x0 + x1) / 2, 0, top - 0.2), (x1 - x0, w_, 0.4), pal["wall"])
            for sy in (-1, 1):
                mb.box(((x0 + x1) / 2, sy * (w_ / 2 - 0.1), top + 0.2), (x1 - x0, 0.2, 0.4), pal["wall"])
                mb.box(((x0 + x1) / 2, sy * (w_ / 2 - 0.1), top + 0.43), (x1 - x0 + 0.02, 0.26, 0.06), pal["light"])
            mb.box(((x0 + x1) / 2, 0, top + 0.12), (x1 - x0, w_ - 0.4, 0.14), "water")

        def pier(x):
            mb.box((x, 0, (top - 2.0) / 2 - 1.0), (1.0, w_ + 0.1, top - 2.0 + 2.0), pal["wall"])       # 2 m more under the ground, for hollows.
            mb.box((x, 0, top - 2.05), (1.2, w_ + 0.3, 0.14), pal["light"])
            mb.box((x, 0, 0.25), (1.3, w_ + 0.4, 0.5), pal["dark"])

        def arch(x0, x1):
            n = 7
            cx, r = (x0 + x1) / 2, (x1 - x0) / 2 - 0.5
            for i in range(n):   # The ring of the arch and the wall above it.
                a0, a1 = math.pi * i / n, math.pi * (i + 1) / n
                p0 = (cx + math.cos(a0) * r, top - 2.0 + math.sin(a0) * r)
                p1 = (cx + math.cos(a1) * r, top - 2.0 + math.sin(a1) * r)
                solid(mb, [(p0[0], -w_ / 2, p0[1]), (p1[0], -w_ / 2, p1[1]), (p1[0], -w_ / 2, top - 0.4), (p0[0], -w_ / 2, top - 0.4)], (0, w_, 0), pal["wall"])
                solid(mb, [(p0[0], -w_ / 2 - 0.04, p0[1]), (p1[0], -w_ / 2 - 0.04, p1[1]), (cx + math.cos(a1) * (r + 0.3), -w_ / 2 - 0.04, top - 2.0 + math.sin(a1) * (r + 0.3)),
                           (cx + math.cos(a0) * (r + 0.3), -w_ / 2 - 0.04, top - 2.0 + math.sin(a0) * (r + 0.3))], (0, w_ + 0.08, 0), pal["dark"] if i % 2 else pal["light"])

        if piece == "span":
            channel(-2.0, 2.0)
            arch(-2.0, 2.0)
        elif piece == "pier":
            pier(0.0)
        elif piece == "end":   # Where the water falls into a basin.
            channel(-2.0, 0.6)
            arch(-2.0, 2.0)
            pier(2.0)
            mb.box((0.9, 0, top - 0.1), (0.6, w_ - 0.5, 0.1), pal["light"])
            mb.box((1.15, 0, 2.6), (0.12, w_ - 0.6, 4.9), "water_light")
            ring_wall(mb, 1.3, 0, 1.3, 0.0, 0.6, pal, 10)
            mb.cylinder((1.3, 0, 0.5), (1.3, 0, 0.56), 1.15, 1.15, "water", segments=10)
        else:   # A demo of 16 m: four spans, the piers between them and the end.
            for k in range(3):
                x = -6.0 + 4.0 * k
                channel(x - 2.0, x + 2.0)
                arch(x - 2.0, x + 2.0)
            for k in range(4):
                pier(-8.0 + 4.0 * k)
            channel(4.0, 6.6)
            arch(4.0, 8.0)
            pier(8.0)
            mb.box((6.9, 0, top - 0.1), (0.6, w_ - 0.5, 0.1), pal["light"])
            mb.box((7.15, 0, 2.6), (0.12, w_ - 0.6, 4.9), "water_light")
            ring_wall(mb, 7.3, 0, 1.3, 0.0, 0.6, pal, 10)
            mb.cylinder((7.3, 0, 0.5), (7.3, 0, 0.56), 1.15, 1.15, "water", segments=10)
        kit.save(mb, FAMILY, name, COLORS)
    return build


def log_pipe(name, piece):
    """A 4 m length of bored-log pipe on trestles, 1.2 m up."""
    def build():
        mb = kit.begin()

        def trestle(x, y, rot=0.0):
            c, s = math.cos(rot), math.sin(rot)
            for k in (-1, 1):
                beam(mb, (x + c * 0 - s * k * 0.45, y + s * 0 + c * k * 0.45, 0), (x - s * k * 0.08, y + c * k * 0.08, 1.15), 0.045, "pole_dark")
            beam(mb, (x - s * 0.3, y + c * 0.3, 0.6), (x + s * 0.3, y - c * 0.3, 0.6), 0.03, "pole_dark")

        def pipe(a, b):
            log(mb, a, b, 0.17)
            for end in (a, b):
                mb.cylinder(end, (end[0] + (b[0] - a[0]) * 0.01, end[1] + (b[1] - a[1]) * 0.01, end[2]), 0.2, 0.2, "iron", segments=8)

        if piece == "straight":
            pipe((-2.0, 0, 1.3), (2.0, 0, 1.3))
            trestle(-1.3, 0)
            trestle(1.3, 0)
        elif piece == "corner":
            pipe((-2.0, 0, 1.3), (0.1, 0, 1.3))
            pipe((0, -0.1, 1.3), (0, 2.0, 1.3))
            mb.box((0, 0, 1.3), (0.5, 0.5, 0.5), "plank_dark")
            trestle(-1.3, 0)
            trestle(0, 1.3, math.pi / 2)
            mb.cylinder((0, 0, 0), (0, 0, 1.05), 0.09, 0.08, "pole_dark", segments=6)
        else:   # The public tap at the end of the line.
            pipe((-2.0, 0, 1.3), (0.0, 0, 1.3))
            trestle(-1.3, 0)
            mb.box((0.15, 0, 0.8), (0.4, 0.4, 1.6), "stone")
            mb.box((0.15, 0, 1.63), (0.5, 0.5, 0.08), "stone_light")
            mb.cylinder((0.35, 0, 1.1), (0.7, 0, 1.0), 0.05, 0.04, "bronze", segments=6)
            mb.box((0.5, 0, 1.2), (0.05, 0.2, 0.05), "bronze")
            mb.cylinder((0.9, 0, 0), (0.9, 0, 0.5), 0.55, 0.6, "stone", segments=9)
            mb.cylinder((0.9, 0, 0.42), (0.9, 0, 0.46), 0.5, 0.5, "water", segments=9)
            mb.cylinder((0.7, 0, 1.0), (0.72, 0, 0.46), 0.025, 0.035, "water_light", segments=5)
            mb.cylinder((1.7, -0.5, 0), (1.7, -0.5, 0.32), 0.15, 0.19, "plank_light", segments=8)
        kit.save(mb, FAMILY, name, COLORS)
    return build


def fire_post():
    """What a street keeps ready for a fire."""
    mb = kit.begin()
    mb.box((0, 0.5, 0.06), (3.2, 1.4, 0.12), "stone_dark")
    for sx in (-1.5, 1.5):
        mb.cylinder((sx, 1.0, 0), (sx, 1.0, 2.6), 0.07, 0.06, "paint_red", segments=6)
    beam(mb, (-1.7, 1.0, 2.5), (1.7, 1.0, 2.5), 0.05, "paint_red")
    beam(mb, (-1.6, 1.0, 1.4), (1.6, 1.0, 1.4), 0.04, "paint_red")
    shed_roof(mb, 0, 0.7, 3.2, 1.2, 2.5, 2.9, ("shingle", "shingle_dark"), 0.2, 2)
    for k in range(6):                                                                    # Buckets on their hooks.
        x = -1.25 + 0.5 * k
        mb.cylinder((x, 0.9, 1.05), (x, 0.9, 1.35), 0.11, 0.14, "leather", segments=8)
        mb.cylinder((x, 0.9, 1.32), (x, 0.9, 1.36), 0.145, 0.145, "paint_red", segments=8)
        rope(mb, (x, 0.9, 1.36), (x, 1.0, 1.42), 0.01)
    for sy, zz in ((0.92, 2.2), (0.92, 1.9)):                                              # Fire hooks to pull down thatch.
        beam(mb, (-1.5, sy, zz), (1.4, sy, zz), 0.02, "pole")
        beam(mb, (1.4, sy, zz), (1.55, sy, zz - 0.15), 0.02, "iron")
    for sy in (0.3, 0.55):                                                                # A ladder lying across.
        beam(mb, (-1.5, sy, 0.2), (1.5, sy, 0.2), 0.03, "pole")
    for k in range(9):
        beam(mb, (-1.4 + 0.35 * k, 0.3, 0.2), (-1.4 + 0.35 * k, 0.55, 0.2), 0.018, "pole_dark")
    barrel(mb, -1.1, -0.1, 0.12, 1.0, 0.4)
    barrel(mb, 1.1, -0.1, 0.12, 1.0, 0.4)
    for sx in (-1.1, 1.1):
        mb.cylinder((sx, -0.1, 1.08), (sx, -0.1, 1.12), 0.33, 0.33, "water", segments=10)
    w = {"bell": 1.0}
    beam(mb, (1.7, 1.0, 2.5), (2.2, 1.0, 2.5), 0.03, "iron")
    mb.cylinder((2.1, 1.0, 2.45), (2.1, 1.0, 2.2), 0.05, 0.16, "bell", w, segments=8)
    mb.sphere((2.1, 1.0, 2.16), 0.04, "iron", w, segments=5, rings=3)
    pose = lambda t: ({"bell": [(kit.Y, 28.0 * math.sin(TAU * 4 * t) * max(0.0, 1 - t))]}, {})   # noqa: E731
    kit.save(mb, FAMILY, "water_fire_post", COLORS, mech=kit.Mech([("bell", (2.1, 1.0, 2.48), (2.1, 1.0, 2.2), None)]).clip("ring", 2.0, pose, loops=False))


def wall_fountain():
    mb = kit.begin()
    mb.box((0, 0.3, 1.2), (2.4, 0.5, 2.4), "stone")
    mb.box((0, 0.3, 2.45), (2.6, 0.6, 0.14), "stone_light")
    solid(mb, [(-1.0, 0.05, 2.5), (1.0, 0.05, 2.5), (0, 0.05, 3.0)], (0, 0.5, 0), "stone")
    mb.sphere((0, 0.02, 1.6), 0.26, "bronze", segments=8, rings=5, scale=(1, 0.6, 1))        # A lion's head.
    for sx in (-1, 1):
        mb.sphere((sx * 0.2, 0.0, 1.78), 0.09, "bronze", segments=5, rings=3)
        mb.box((sx * 0.09, -0.14, 1.66), (0.05, 0.03, 0.04), "cave")
    mb.cylinder((0, -0.1, 1.5), (0, -0.25, 1.45), 0.05, 0.04, "bronze", segments=6)
    for i in range(6):
        a0, a1 = math.pi + math.pi * i / 6, math.pi + math.pi * (i + 1) / 6
        solid(mb, [(math.cos(a0) * 0.9, 0.05 + math.sin(a0) * 0.8, 0.0), (math.cos(a1) * 0.9, 0.05 + math.sin(a1) * 0.8, 0.0),
                   (math.cos(a1) * 0.95, 0.05 + math.sin(a1) * 0.85, 0.65), (math.cos(a0) * 0.95, 0.05 + math.sin(a0) * 0.85, 0.65)],
              (math.cos((a0 + a1) / 2) * 0.1, math.sin((a0 + a1) / 2) * 0.1, 0), "stone_light" if i % 2 else "stone")
    mb.box((0, -0.3, 0.52), (1.6, 0.8, 0.06), "water")
    w = {"stream": 1.0}
    mb.cylinder((0, -0.25, 1.45), (0, -0.4, 0.56), 0.03, 0.045, "water_light", w, segments=5)
    for sx in (-1, 1):
        mb.sphere((sx * 0.9, 0.0, 2.6), 0.14, "stone_light", segments=6, rings=4)
    pose = lambda t: ({}, {"stream": (0.01 * math.sin(TAU * 6 * t), 0, 0.03 * math.sin(TAU * 4 * t))})   # noqa: E731
    kit.save(mb, FAMILY, "water_wall_fountain", COLORS, mech=kit.Mech([("stream", (0, -0.25, 1.45), (0, -0.4, 0.56), None)]).clip("flow", 2.0, pose))


MODELS = {
    "well_stone": well("well_stone", "stone"),
    "well_brick": well("well_brick", "brick"),
    "well_log": well("well_log", "log"),
    "well_pump": pump_well,
    "well_horse_gin": horse_gin,
    "water_cistern": cistern("water_cistern", STONE),
    "water_cistern_brick": cistern("water_cistern_brick", BRICK),
    "water_tower": water_tower,
    "water_wall_fountain": wall_fountain,
    "water_fire_post": fire_post,
    "water_pipe_straight": log_pipe("water_pipe_straight", "straight"),
    "water_pipe_corner": log_pipe("water_pipe_corner", "corner"),
    "water_pipe_tap": log_pipe("water_pipe_tap", "tap"),
}
for _key, _pal in (("stone", STONE), ("brick", BRICK)):
    for _piece in ("demo", "span", "pier", "end"):
        _name = "aqueduct_%s_%s" % (_key, _piece)
        MODELS[_name] = aqueduct(_name, _pal, _piece)

kit.run(MODELS, FAMILY)
