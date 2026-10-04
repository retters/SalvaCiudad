"""Camp and exploration proposals: tents, banners, fires, shelters and the
gear of people who sleep away from town. See ../LEEME.md.

    blender --background --factory-startup --python art/blender/proposals/camp/build.py -- [ids]
"""

import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mathutils import Matrix, Vector  # noqa: E402

import _kit as kit  # noqa: E402
import _shapes  # noqa: E402
import common  # noqa: E402
from _shapes import barrel, crate, lantern, log, mark, moved, rock, rope, sack, solid, stump  # noqa: E402

FAMILY = "camp"
TAU = 2 * math.pi
C = common.rgb
COLORS = {
    **_shapes.COLORS,
    "pole": C(0x7A5232), "pole_dark": C(0x5A3B24), "bark": C(0x6B4A2E), "log_end": C(0xC8A06A),
    "plank": C(0xA07A4A), "plank_dark": C(0x7E5C36),
    "canvas": C(0xE4D8B8), "canvas_trim": C(0xC2B48C), "canvas_shade": C(0xD0C29C),
    "hide": C(0x9A7050), "hide_trim": C(0x7A5438), "hide_shade": C(0x86603F),
    "cloth_blue": C(0x2F4E8C), "cloth_blue_trim": C(0x24396A), "cloth_blue_shade": C(0x29447A),
    "cloth_red": C(0xA83A34), "cloth_red_trim": C(0x7E2A26), "cloth_red_shade": C(0x94322E),
    "cloth_green": C(0x4A7A44), "cloth_green_trim": C(0x355A32), "cloth_green_shade": C(0x426C3C),
    "emblem_white": C(0xECE8DC), "emblem_gold": C(0xD8B040),
    "rope": C(0xB89A64), "leather": C(0x6B4A2E), "iron": C(0x44484E), "gold": C(0xC9A441),
    "stone": C(0x9A938A), "stone_dark": C(0x78726A), "stone_light": C(0xB4AEA4), "ash": C(0x4A4642),
    "flame": C(0xF08A24), "flame_mid": C(0xF8C030), "flame_core": C(0xFFF0B0), "ember": C(0xE85820),
    "blanket": C(0x8A3A34), "blanket_alt": C(0x3F5E8C), "pillow": C(0xE0D8C4),
    "thatch": C(0xC9A55A), "thatch_dark": C(0xA8863F), "leaf": C(0x4E7A34), "leaf_dark": C(0x3A5E28),
    "sack": C(0xC8B48A), "parchment": C(0xE8D8A8), "ink": C(0x5A3B24), "meat": C(0x9A4A34),
    "soup": C(0xB87A3A), "window": C(0xF6D070), "steel": C(0x9AA2AA), "fur": C(0x7A6A58),
}


# --- Pieces ---------------------------------------------------------------------------------


def bedroll(mb, x, y, rot=0.0, open_=False, mat="blanket"):
    start = mark(mb)
    if open_:
        mb.box((0, 0, 0.035), (0.8, 1.9, 0.07), "fur")
        mb.box((0, 0.12, 0.085), (0.74, 1.4, 0.05), mat)
        mb.box((0, -0.72, 0.11), (0.5, 0.3, 0.1), "pillow")
        mb.cylinder((-0.38, 0.86, 0.1), (0.38, 0.86, 0.1), 0.1, 0.1, mat, segments=8)
    else:
        mb.cylinder((-0.36, 0, 0.15), (0.36, 0, 0.15), 0.15, 0.15, mat, segments=9)
        mb.cylinder((-0.37, 0, 0.15), (0.37, 0, 0.15), 0.09, 0.09, "fur", segments=9)
        for sx in (-0.2, 0.2):
            mb.cylinder((sx - 0.025, 0, 0.15), (sx + 0.025, 0, 0.15), 0.158, 0.158, "leather", segments=9)
    moved(mb, start, (x, y), rot)


def log_seat(mb, x, y, rot=0.0, length=1.5):
    start = mark(mb)
    log(mb, (-length / 2, 0, 0.2), (length / 2, 0, 0.2), 0.2)
    mb.box((0, 0, 0.385), (length * 0.9, 0.24, 0.04), "log_end")
    moved(mb, start, (x, y), rot)


# --- Animated parts: each returns (bones, pose) ----------------------------------------------


def fire(mb, at=(0.0, 0.0), size=1.0, prefix="", stones=True, seed=3):
    """A fire with a stone ring; bones and a looping pose for its flames."""
    x, y = at
    rnd = random.Random(seed)
    s = size
    if stones:
        n = 9 if s > 1.2 else 8
        for i in range(n):
            a = TAU * i / n + rnd.uniform(-0.1, 0.1)
            rock(mb, x + math.cos(a) * 0.62 * s, y + math.sin(a) * 0.62 * s, 0.09 * s, rnd.uniform(0.15, 0.2) * s, rnd)
    mb.cylinder((x, y, 0), (x, y, 0.05), 0.5 * s, 0.46 * s, "ash", segments=9)
    for i in range(5):
        a = TAU * i / 5 + 0.3
        log(mb, (x + math.cos(a) * 0.42 * s, y + math.sin(a) * 0.42 * s, 0.07),
            (x - math.cos(a) * 0.06 * s, y - math.sin(a) * 0.06 * s, 0.5 * s), 0.07 * s)
    for i in range(4):
        a = TAU * i / 4 + 1.0
        mb.box((x + math.cos(a) * 0.2 * s, y + math.sin(a) * 0.2 * s, 0.08), (0.12 * s, 0.1 * s, 0.07), "ember",
               rotation_z=a)
    tongues = [
        ("a", (0.0, 0.0), 0.30, 1.15, "flame"),
        ("b", (0.07, -0.05), 0.20, 0.85, "flame_mid"),
        ("c", (-0.02, 0.03), 0.11, 0.6, "flame_core"),
        ("d", (-0.18, -0.1), 0.13, 0.6, "flame"),
        ("e", (0.16, 0.14), 0.12, 0.55, "flame_mid"),
    ]
    bones = []
    for name, (dx, dy), r, h, mat in tongues:
        bone = prefix + "flame_" + name
        base = (x + dx * s, y + dy * s, 0.16 * s)
        mb.cylinder(base, (base[0], base[1], base[2] + h * s * 0.45), r * s * 0.7, r * s, mat, {bone: 1.0}, segments=5)
        mb.cylinder((base[0], base[1], base[2] + h * s * 0.45), (base[0], base[1], base[2] + h * s), r * s, 0.0, mat,
                    {bone: 1.0}, segments=5)
        bones.append((bone, base, (base[0], base[1], base[2] + 0.4 * s), None))
    spark = prefix + "sparks"
    for i in range(5):
        a = rnd.uniform(0, TAU)
        d = rnd.uniform(0.05, 0.25) * s
        mb.box((x + math.cos(a) * d, y + math.sin(a) * d, (0.7 + 0.22 * i) * s), (0.04, 0.04, 0.04), "ember",
               {spark: 1.0}, rotation_z=a)
    bones.append((spark, (x, y, 0.5 * s), (x, y, 0.9 * s), None))

    def pose(t):
        turns, moves = {}, {}
        for i, (name, *_rest) in enumerate(tongues):
            ph = i * 1.7
            turns[prefix + "flame_" + name] = [
                (kit.Z, 360.0 * t * (1 if i % 2 == 0 else -1)),
                (kit.X, 9.0 * math.sin(TAU * 2 * t + ph)),
                (kit.Y, 7.0 * math.sin(TAU * 3 * t + ph * 1.3)),
            ]
            moves[prefix + "flame_" + name] = (0, 0, 0.05 * s * math.sin(TAU * 4 * t + ph))
        turns[spark] = [(kit.Z, 360.0 * t)]
        moves[spark] = (0.06 * s * math.sin(TAU * 2 * t), 0, 0.7 * s * t)
        return turns, moves

    return bones, pose


def banner(mb, at=(0.0, 0.0), cloth="cloth_blue", emblem="emblem_white", height=3.4, prefix=""):
    """A pole with a hanging banner and a wolf's head; bones and a `wave` pose."""
    x, y = at
    trim = cloth + "_trim"
    top = height - 0.3
    rnd = random.Random(11)
    for i in range(4):
        a = TAU * i / 4 + 0.4
        rock(mb, x + math.cos(a) * 0.2, y + math.sin(a) * 0.2, 0.08, 0.17, rnd)
    mb.cylinder((x, y, 0), (x, y, height), 0.055, 0.045, "pole", segments=7)
    mb.sphere((x, y, height + 0.06), 0.08, "gold", segments=6, rings=4)
    mb.cylinder((x - 0.62, y, top), (x + 0.62, y, top), 0.032, 0.032, "pole_dark", segments=6)
    for sx in (-0.62, 0.62):
        mb.sphere((x + sx, y, top), 0.05, "gold", segments=5, rings=3)
    rope(mb, (x - 0.5, y, top), (x, y, height - 0.04))
    rope(mb, (x + 0.5, y, top), (x, y, height - 0.04))
    fy = y - 0.05          # The cloth hangs just in front of the pole.
    thick = (0, 0.03, 0)
    b1, b2, bl, br = (prefix + n for n in ("cloth_top", "cloth_main", "cloth_tail_l", "cloth_tail_r"))
    z1, z2, z3 = top - 0.02, top - 0.3, top - 1.45
    hw = 0.52
    solid(mb, [(x - hw, fy, z1), (x + hw, fy, z1), (x + hw, fy, z2), (x - hw, fy, z2)], thick, trim, {b1: 1.0})
    for sx in (-0.34, 0.0, 0.34):   # Loops over the crossbar.
        mb.box((x + sx, y - 0.02, top), (0.12, 0.1, 0.1), trim, {b1: 1.0})
    solid(mb, [(x - hw, fy, z2), (x + hw, fy, z2), (x + hw, fy, z3), (x - hw, fy, z3)], thick, cloth, {b2: 1.0})
    for sx in (-1, 1):   # Side borders.
        solid(mb, [(x + sx * hw, fy - 0.008, z2), (x + sx * (hw - 0.07), fy - 0.008, z2),
                   (x + sx * (hw - 0.07), fy - 0.008, z3), (x + sx * hw, fy - 0.008, z3)], (0, 0.046, 0), trim, {b2: 1.0})
    for sx, bone in ((-1, bl), (1, br)):   # Two pointed tails.
        solid(mb, [(x + sx * hw, fy, z3), (x + sx * 0.02, fy, z3), (x + sx * 0.02, fy, z3 - 0.28),
                   (x + sx * hw * 0.52, fy, z3 - 0.55), (x + sx * hw, fy, z3 - 0.28)], thick, cloth, {bone: 1.0})
        solid(mb, [(x + sx * hw * 0.52, fy - 0.008, z3 - 0.55), (x + sx * hw * 0.3, fy - 0.008, z3 - 0.42),
                   (x + sx * hw * 0.74, fy - 0.008, z3 - 0.42)], (0, 0.046, 0), trim, {bone: 1.0})
    # The wolf's head, through the cloth so it shows on both sides.
    ey, eoff = fy - 0.012, (0, 0.054, 0)
    c = (z2 + z3) / 2 + 0.02

    def pts(points):
        return [(x + px, ey, c + pz) for px, pz in points]

    solid(mb, pts([(-0.27, 0.16), (-0.18, -0.08), (0, -0.32), (0.18, -0.08), (0.27, 0.16), (0.11, 0.27), (-0.11, 0.27)]),
          eoff, emblem, {b2: 1.0})
    for sx in (-1, 1):
        solid(mb, pts([(sx * 0.27, 0.16), (sx * 0.11, 0.27), (sx * 0.25, 0.46)]), eoff, emblem, {b2: 1.0})
        solid(mb, [(x + sx * 0.16, ey - 0.006, c + 0.1), (x + sx * 0.05, ey - 0.006, c + 0.045),
                   (x + sx * 0.15, ey - 0.006, c + 0.015)], (0, 0.066, 0), cloth, {b2: 1.0})
    solid(mb, [(x - 0.05, ey - 0.006, c - 0.22), (x + 0.05, ey - 0.006, c - 0.22), (x, ey - 0.006, c - 0.32)],
          (0, 0.066, 0), trim, {b2: 1.0})
    bones = [
        (b1, (x, fy, z1), (x, fy, z2), None),
        (b2, (x, fy, z2), (x, fy, z3), b1),
        (bl, (x - hw / 2, fy, z3), (x - hw / 2, fy, z3 - 0.5), b2),
        (br, (x + hw / 2, fy, z3), (x + hw / 2, fy, z3 - 0.5), b2),
    ]

    def pose(t):
        return {
            b1: [(kit.X, 5.0 * math.sin(TAU * t))],
            b2: [(kit.X, 8.0 * math.sin(TAU * t - 0.9)), (kit.Z, 3.0 * math.sin(TAU * t - 0.4))],
            bl: [(kit.X, 14.0 * math.sin(TAU * t - 1.8)), (kit.Z, 6.0 * math.sin(TAU * 2 * t))],
            br: [(kit.X, 14.0 * math.sin(TAU * t - 2.3)), (kit.Z, -6.0 * math.sin(TAU * 2 * t + 0.6))],
        }, {}

    return bones, pose


def merged(*poses):
    def pose(t):
        turns, moves = {}, {}
        for p in poses:
            a, b = p(t)
            turns.update(a)
            moves.update(b)
        return turns, moves
    return pose


# --- Static parts ------------------------------------------------------------------------------


def tent(mb, cloth="canvas", w=3.0, d=3.6, h=2.2, gear=True, emblem=None):
    """An A-frame tent, open toward -Y."""
    trim, shade = cloth + "_trim", cloth + "_shade"
    for y in (-d / 2, d / 2):
        for sx in (-1, 1):
            mb.cylinder((sx * (w / 2 + 0.06), y, 0), (-sx * 0.08, y, h + 0.22), 0.05, 0.04, "pole", segments=6)
    mb.cylinder((0, -d / 2 - 0.3, h), (0, d / 2 + 0.3, h), 0.05, 0.05, "pole_dark", segments=6)
    foot = 0.14
    for sx in (-1, 1):
        normal = Vector((sx * (h - foot), 0, w / 2)).normalized()

        def at(y, u, lift=0.0):
            p = Vector((sx * w / 2 * (1 - u), y, foot + (h + 0.03 - foot) * u))
            return p + normal * lift

        strips = 4
        for i in range(strips):   # Panels with a slight sag between the seams.
            y0, y1 = -d / 2 + d * i / strips, -d / 2 + d * (i + 1) / strips
            solid(mb, [at(y0, 0.16), at(y1, 0.16), at(y1, 1), at(y0, 1)], normal * 0.035, cloth if i % 2 == 0 else shade)
            solid(mb, [at(y0, 0), at(y1, 0), at(y1, 0.16), at(y0, 0.16)], normal * 0.045, trim)
            mb.box(tuple(at(y1 if i < strips - 1 else y0, 0, 0.0) + Vector((sx * 0.3, 0, -foot + 0.05))),
                   (0.06, 0.06, 0.2), "pole_dark")
            rope(mb, at(y1 if i < strips - 1 else y0, 0.02, 0.03),
                 at(y1 if i < strips - 1 else y0, 0, 0.0) + Vector((sx * 0.3, 0, -foot + 0.1)))
    # Back wall and the two front flaps, tied open.
    solid(mb, [(-w / 2, d / 2, foot), (w / 2, d / 2, foot), (0, d / 2, h)], (0, 0.035, 0), shade)
    for sx in (-1, 1):
        solid(mb, [(sx * w / 2, -d / 2, foot), (sx * w * 0.2, -d / 2 - 0.18, foot), (0, -d / 2, h)], (0, -0.035, 0), cloth)
        solid(mb, [(sx * w / 2, -d / 2 - 0.036, foot), (sx * w * 0.2, -d / 2 - 0.216, foot),
                   (sx * w * 0.2, -d / 2 - 0.2, foot + 0.28), (sx * w * 0.43, -d / 2 - 0.05, foot + 0.3)],
              (0, -0.012, 0), trim)
    for sy in (-1, 1):   # Guy ropes of the ridge.
        rope(mb, (0, sy * (d / 2 + 0.3), h), (0, sy * (d / 2 + 1.3), 0.06))
        mb.box((0, sy * (d / 2 + 1.3), 0.08), (0.06, 0.06, 0.2), "pole_dark")
    if emblem:
        solid(mb, [(-0.3, d / 2 + 0.036, 1.25), (0.3, d / 2 + 0.036, 1.25), (0, d / 2 + 0.036, 0.75)], (0, 0.02, 0), emblem)
    if gear:
        mb.box((0, 0.2, 0.02), (w * 0.72, d * 0.8, 0.04), "fur")
        bedroll(mb, -0.55, 0.5, 90, open_=True)
        crate(mb, 0.75, 1.15, 0.0, 0.5)
        lantern(mb, 0.75, 1.15, 0.57)
        sack(mb, 0.8, 0.45, 0.0, 0.22)


def supplies(mb, tarp="canvas"):
    crate(mb, -0.45, 0.25, 0.0, 0.7)
    crate(mb, 0.35, 0.3, 0.0, 0.6)
    crate(mb, -0.35, 0.3, 0.76, 0.5)
    barrel(mb, 0.55, -0.45)
    sack(mb, -0.2, -0.5, 0.0, 0.3)
    sack(mb, -0.75, -0.4, 0.0, 0.26)
    sack(mb, 0.0, -0.3, 0.0, 0.22)
    # A tarp thrown over the back crates.
    solid(mb, [(-0.92, 0.72, 0.2), (0.78, 0.72, 0.15), (0.72, 0.5, 0.7), (-0.86, 0.52, 1.3)], (0, 0.03, 0.02), tarp)
    solid(mb, [(-0.86, 0.52, 1.3), (0.72, 0.5, 0.7), (0.6, 0.0, 0.69), (-0.72, 0.02, 1.32)], (0, 0.0, 0.035), tarp + "_shade")
    rope(mb, (-0.9, 0.74, 0.25), (-1.05, 0.95, 0.0))
    rope(mb, (0.78, 0.74, 0.2), (0.95, 0.95, 0.0))


def lean_to(mb):
    """A shelter of branches against a ridge pole on two forked posts."""
    for sx in (-1.4, 1.4):
        mb.cylinder((sx, -0.9, 0), (sx, -0.9, 1.75), 0.07, 0.055, "bark", segments=6)
        mb.cylinder((sx, -0.9, 1.7), (sx - 0.12, -0.9, 1.98), 0.04, 0.03, "bark", segments=5)
        mb.cylinder((sx, -0.9, 1.7), (sx + 0.12, -0.9, 1.98), 0.04, 0.03, "bark", segments=5)
    log(mb, (-1.7, -0.9, 1.8), (1.7, -0.9, 1.8), 0.06)
    n = 9
    for i in range(n):
        xx = -1.5 + 3.0 * i / (n - 1)
        mb.cylinder((xx, -0.92, 1.84), (xx, 1.25, 0.04), 0.035, 0.03, "bark", segments=5)
    normal = Vector((0, 1.76, 2.15)).normalized()
    rows = 5
    for r in range(rows):
        u0, u1 = r / rows, (r + 1) / rows + 0.06
        y0, z0 = -0.92 + 2.17 * u0, 1.88 - 1.8 * u0
        y1, z1 = -0.92 + 2.17 * min(u1, 1.02), 1.88 - 1.8 * min(u1, 1.02)
        mat = ("thatch", "leaf", "thatch_dark", "leaf_dark", "thatch")[r]
        solid(mb, [(-1.6, y0, z0), (1.6, y0, z0), (1.6, y1, z1), (-1.6, y1, z1)], normal * (0.07 - 0.008 * r), mat)
    mb.box((0, 0.1, 0.05), (2.4, 1.3, 0.1), "leaf_dark")
    bedroll(mb, -0.5, 0.15, 90, open_=True, mat="blanket_alt")
    stump(mb, 1.0, -0.3, 0.35, 0.2)


def lookout(mb, roof=True):
    """A lookout platform on four leaning posts, with a ladder."""
    top = 4.2
    for sx in (-1, 1):
        for sy in (-1, 1):
            log(mb, (sx * 1.3, sy * 1.3, 0), (sx * 0.95, sy * 0.95, top), 0.1)
    for z, k in ((1.3, 1.19), (2.8, 1.07)):
        for s in (-1, 1):
            mb.cylinder((-k, s * k, z), (k, s * k, z), 0.05, 0.05, "pole_dark", segments=6)
            mb.cylinder((s * k, -k, z), (s * k, k, z), 0.05, 0.05, "pole_dark", segments=6)
    for s in (-1, 1):   # Diagonal braces.
        mb.cylinder((-1.19, s * 1.19, 1.3), (1.07, s * 1.07, 2.8), 0.04, 0.04, "pole_dark", segments=5)
        mb.cylinder((s * 1.19, 1.19, 1.3), (s * 1.07, -1.07, 2.8), 0.04, 0.04, "pole_dark", segments=5)
    for i in range(7):
        mb.box((-1.05 + 0.35 * i, 0, top + 0.04), (0.32, 2.4, 0.08), "plank" if i % 2 else "plank_dark")
    for s in (-1, 1):
        for t in (-1, 1):
            mb.box((s * 1.12, t * 1.12, top + 0.6), (0.09, 0.09, 1.1), "pole")
        mb.box((0, s * 1.12, top + 1.08), (2.3, 0.07, 0.08), "pole_dark")
        mb.box((0, s * 1.12, top + 0.6), (2.3, 0.05, 0.06), "pole_dark")
    mb.box((1.12, 0, top + 1.08), (0.07, 2.3, 0.08), "pole_dark")
    mb.box((1.12, 0, top + 0.6), (0.05, 2.3, 0.06), "pole_dark")
    mb.box((-1.12, 0.55, top + 1.08), (0.07, 1.2, 0.08), "pole_dark")   # A gap for the ladder.
    for sy in (-0.85, -0.35):
        mb.cylinder((-1.75, sy, 0), (-1.15, sy, top + 0.9), 0.04, 0.04, "pole", segments=5)
    for i in range(11):
        u = (i + 0.7) / 12.5
        mb.cylinder((-1.75 + 0.6 * u, -0.85, (top + 0.9) * u), (-1.75 + 0.6 * u, -0.35, (top + 0.9) * u), 0.03, 0.03,
                    "pole_dark", segments=5)
    if roof:
        for s in (-1, 1):
            for t in (-1, 1):
                mb.box((s * 1.12, t * 1.12, top + 1.6), (0.08, 0.08, 1.0), "pole")
        apex = (0, 0, top + 3.0)
        for i in range(4):
            a0, a1 = TAU * (i + 0.5) / 4, TAU * (i + 1.5) / 4
            p0 = (math.cos(a0) * 2.05, math.sin(a0) * 2.05, top + 2.0)
            p1 = (math.cos(a1) * 2.05, math.sin(a1) * 2.05, top + 2.0)
            solid(mb, [p0, p1, apex], (0, 0, 0.08), "thatch" if i % 2 else "thatch_dark")
    barrel(mb, 0.55, 0.6, top + 0.08, 0.6, 0.22)


def weapon_rack(mb):
    for sx in (-0.9, 0.9):
        mb.cylinder((sx, -0.3, 0), (sx, 0.05, 1.3), 0.04, 0.035, "pole", segments=6)
        mb.cylinder((sx, 0.3, 0), (sx, -0.05, 1.3), 0.04, 0.035, "pole", segments=6)
    mb.cylinder((-1.0, 0, 1.27), (1.0, 0, 1.27), 0.035, 0.035, "pole_dark", segments=6)
    mb.cylinder((-1.0, -0.2, 0.5), (1.0, -0.2, 0.5), 0.03, 0.03, "pole_dark", segments=6)
    for i, sx in enumerate((-0.6, -0.3, 0.0, 0.3)):   # Spears leaning on the bar.
        mb.cylinder((sx, -0.55, 0), (sx, 0.02, 2.0), 0.02, 0.02, "pole", segments=5)
        mb.cylinder((sx, 0.02, 2.0), (sx, 0.085, 2.26), 0.045, 0.0, "steel", segments=4)
    for sx, mat in ((0.62, "cloth_blue"), (-0.78, "cloth_red")):   # Round shields against the lower bar.
        mb.cylinder((sx, -0.3, 0.42), (sx, -0.25, 0.44), 0.34, 0.34, mat, segments=10)
        mb.cylinder((sx, -0.315, 0.415), (sx, -0.3, 0.42), 0.36, 0.36, "iron", segments=10)
        mb.sphere((sx, -0.32, 0.41), 0.08, "steel", segments=6, rings=4)
    mb.box((0.7, 0.25, 0.3), (0.1, 0.5, 0.06), "steel", rotation_z=0.4)   # An axe on the ground.
    mb.cylinder((0.5, -0.05, 0.02), (0.95, 0.6, 0.02), 0.02, 0.02, "pole", segments=5)


def map_table(mb):
    for sx in (-0.6, 0.6):
        for sy in (-0.35, 0.35):
            mb.cylinder((sx, sy, 0), (sx * 0.92, sy * 0.92, 0.78), 0.04, 0.04, "pole", segments=6)
    mb.box((0, 0, 0.8), (1.5, 0.9, 0.06), "plank")
    mb.box((0, 0, 0.775), (1.3, 0.7, 0.03), "plank_dark")
    mb.box((-0.1, 0.0, 0.838), (0.95, 0.65, 0.012), "parchment", rotation_z=0.08)
    solid(mb, [(-0.4, 0.1, 0.846), (-0.1, 0.2, 0.846), (0.05, -0.05, 0.846), (-0.25, -0.15, 0.846)], (0, 0, 0.004), "leaf")
    solid(mb, [(0.05, 0.1, 0.846), (0.25, 0.18, 0.846), (0.2, -0.1, 0.846)], (0, 0, 0.004), "cloth_blue")
    mb.cylinder((-0.52, 0.28, 0.83), (-0.52, 0.28, 0.9), 0.035, 0.03, "iron", segments=6)     # Inkwell.
    mb.cylinder((-0.52, 0.28, 0.9), (-0.44, 0.34, 1.12), 0.008, 0.02, "emblem_white", segments=4)   # Quill.
    lantern(mb, 0.58, 0.27, 0.83)
    mb.cylinder((0.5, -0.3, 0.845), (0.2, -0.36, 0.845), 0.03, 0.03, "parchment", segments=6)   # A rolled map.
    stump(mb, 0.0, -0.85, 0.45, 0.2)
    stump(mb, 1.1, 0.1, 0.45, 0.2)


def drying_rack(mb):
    for sx in (-1.2, 1.2):
        mb.cylinder((sx, -0.5, 0), (sx, 0.04, 1.9), 0.045, 0.035, "bark", segments=6)
        mb.cylinder((sx, 0.5, 0), (sx, -0.04, 1.9), 0.045, 0.035, "bark", segments=6)
    for z, k in ((1.85, 0.0), (1.15, 0.2), (1.15, -0.2)):
        mb.cylinder((-1.35, k, z), (1.35, k, z), 0.03, 0.03, "pole_dark", segments=6)
    for i, xx in enumerate((-0.75, 0.0, 0.75)):   # Stretched hides.
        mat = ("hide", "fur", "hide_shade")[i]
        solid(mb, [(xx - 0.3, 0, 1.82), (xx + 0.3, 0, 1.82), (xx + 0.38, 0, 1.3), (xx + 0.2, 0, 0.72),
                   (xx - 0.2, 0, 0.72), (xx - 0.38, 0, 1.3)], (0, 0.03, 0), mat)
        for sx in (-0.34, 0.34):
            solid(mb, [(xx + sx - 0.07, 0, 0.9), (xx + sx + 0.07, 0, 0.9), (xx + sx * 1.25, 0, 0.55)], (0, 0.03, 0), mat)
    for xx in (-0.9, -0.5, 0.4, 0.9):   # Strips of meat on the lower bars.
        mb.box((xx, 0.2, 0.98), (0.08, 0.03, 0.32), "meat")
        mb.box((xx + 0.15, -0.2, 0.96), (0.08, 0.03, 0.36), "meat")


# --- Models -------------------------------------------------------------------------------------


def tent_model(name, cloth, emblem=None):
    def build():
        mb = kit.begin()
        tent(mb, cloth, emblem=emblem)
        kit.save(mb, FAMILY, name, COLORS)
    return build


def command_tent():
    """A big wall tent with a banner at the door."""
    mb = kit.begin()
    w, d, wall, h = 5.0, 6.0, 1.5, 3.3
    cloth, trim, shade = "cloth_blue", "cloth_blue_trim", "canvas"
    for sx in (-1, 1):
        for i in range(4):
            y0, y1 = -d / 2 + d * i / 4, -d / 2 + d * (i + 1) / 4
            solid(mb, [(sx * w / 2, y0, 0.05), (sx * w / 2, y1, 0.05), (sx * w / 2, y1, wall), (sx * w / 2, y0, wall)],
                  (sx * 0.04, 0, 0), shade if i % 2 == 0 else "canvas_shade")
            normal = Vector((sx * (h - wall), 0, w / 2)).normalized()
            solid(mb, [(sx * (w / 2 + 0.15), y0, wall - 0.06), (sx * (w / 2 + 0.15), y1, wall - 0.06), (0, y1, h), (0, y0, h)],
                  normal * 0.045, cloth if i % 2 == 0 else trim)
            mb.cylinder((sx * w / 2, y0, 0), (sx * w / 2, y0, wall), 0.04, 0.04, "pole", segments=6)
            rope(mb, (sx * (w / 2 + 0.15), y0, wall - 0.05), (sx * (w / 2 + 1.0), y0, 0.05))
            mb.box((sx * (w / 2 + 1.0), y0, 0.08), (0.06, 0.06, 0.2), "pole_dark")
        mb.cylinder((sx * w / 2, d / 2, 0), (sx * w / 2, d / 2, wall), 0.04, 0.04, "pole", segments=6)
        # Scalloped valance along the eaves.
        for i in range(8):
            y0 = -d / 2 + d * i / 8
            solid(mb, [(sx * (w / 2 + 0.16), y0, wall - 0.05), (sx * (w / 2 + 0.16), y0 + d / 8, wall - 0.05),
                       (sx * (w / 2 + 0.16), y0 + d / 16, wall - 0.35)], (sx * 0.02, 0, 0), "emblem_gold")
    for sy in (-1, 1):
        mb.cylinder((0, sy * d / 2, 0), (0, sy * d / 2, h + 0.5), 0.07, 0.06, "pole_dark", segments=7)
        mb.sphere((0, sy * d / 2, h + 0.55), 0.1, "gold", segments=6, rings=4)
    mb.cylinder((0, -d / 2, h), (0, d / 2, h), 0.05, 0.05, "pole_dark", segments=6)
    solid(mb, [(-w / 2, d / 2, 0.05), (w / 2, d / 2, 0.05), (w / 2, d / 2, wall), (0, d / 2, h), (-w / 2, d / 2, wall)],
          (0, 0.04, 0), shade)
    for sx in (-1, 1):   # Front wall with a tied-back door.
        solid(mb, [(sx * w / 2, -d / 2, 0.05), (sx * 0.8, -d / 2, 0.05), (sx * 0.8, -d / 2, wall + 0.35), (sx * w / 2, -d / 2, wall)],
              (0, -0.04, 0), shade)
        solid(mb, [(sx * 0.8, -d / 2, wall + 0.35), (0, -d / 2, h), (sx * w / 2, -d / 2, wall)], (0, -0.04, 0), cloth)
        solid(mb, [(sx * 0.8, -d / 2 - 0.04, 0.05), (sx * 0.45, -d / 2 - 0.3, 0.05), (sx * 0.62, -d / 2 - 0.2, 1.0),
                   (0, -d / 2 - 0.04, wall + 1.1), (sx * 0.8, -d / 2 - 0.04, wall + 0.35)], (0, -0.03, 0), cloth)
    solid(mb, [(-0.8, -d / 2, wall + 0.35), (0.8, -d / 2, wall + 0.35), (0, -d / 2, h)], (0, -0.03, 0), trim)
    mb.box((0, 0.2, 0.03), (w * 0.86, d * 0.86, 0.06), "blanket")
    start = mark(mb)
    map_table(mb)
    moved(mb, start, (0.3, 0.9), 0)
    crate(mb, -1.7, 2.2, 0.0, 0.7)
    bones, pose = banner(mb, (-3.6, -2.2), "cloth_blue", "emblem_white", 3.6)
    mech = kit.Mech(bones).clip("wave", 3.0, pose)
    kit.save(mb, FAMILY, "camp_command_tent", COLORS, mech=mech)


def banner_model(name, cloth, emblem):
    def build():
        mb = kit.begin()
        bones, pose = banner(mb, (0, 0), cloth, emblem)
        kit.save(mb, FAMILY, name, COLORS, mech=kit.Mech(bones).clip("wave", 3.0, pose))
    return build


def fire_model(name, size, spit=False):
    def build():
        mb = kit.begin()
        bones, pose = fire(mb, (0, 0), size)
        if spit:
            for sx in (-1.25, 1.25):
                mb.cylinder((sx, 0, 0), (sx, 0, 1.45), 0.05, 0.04, "bark", segments=6)
                mb.cylinder((sx, 0, 1.4), (sx, -0.12, 1.62), 0.03, 0.025, "bark", segments=5)
                mb.cylinder((sx, 0, 1.4), (sx, 0.12, 1.62), 0.03, 0.025, "bark", segments=5)
            w = {"spit": 1.0}
            mb.cylinder((-1.5, 0, 1.5), (1.5, 0, 1.5), 0.025, 0.025, "iron", w, segments=6)
            mb.cylinder((1.5, 0, 1.5), (1.5, 0, 1.25), 0.02, 0.02, "iron", w, segments=5)
            mb.cylinder((1.42, 0, 1.25), (1.62, 0, 1.25), 0.03, 0.03, "pole_dark", w, segments=6)
            mb.sphere((0, 0, 1.5), 0.26, "meat", w, segments=7, rings=5, scale=(1.9, 0.9, 0.85))
            mb.sphere((-0.52, 0, 1.5), 0.12, "meat", w, segments=6, rings=4, scale=(1.2, 1, 1))
            mb.sphere((0.55, 0, 1.5), 0.1, "log_end", w, segments=6, rings=4)
            bones = bones + [("spit", (0, 0, 1.5), (0.5, 0, 1.5), None)]
            flames = pose
            pose = lambda t: ({**flames(t)[0], "spit": [(kit.X, 360.0 * t)]}, flames(t)[1])   # noqa: E731
            for a in (0.6, 2.2, 3.9):
                log_seat(mb, math.cos(a) * 2.6, math.sin(a) * 2.6, math.degrees(a) + 90, 1.6)
        kit.save(mb, FAMILY, name, COLORS, mech=kit.Mech(bones).clip("burn", 4.0, pose))
    return build


def cooking_tripod():
    mb = kit.begin()
    bones, pose = fire(mb, (0, 0), 0.8)
    for i in range(3):
        a = TAU * i / 3 + 0.5
        mb.cylinder((math.cos(a) * 0.95, math.sin(a) * 0.95, 0), (-math.cos(a) * 0.06, -math.sin(a) * 0.06, 2.1), 0.04, 0.03,
                    "bark", segments=6)
    mb.cylinder((0, 0, 1.94), (0, 0, 2.0), 0.09, 0.09, "rope", segments=6)
    w = {"pot": 1.0}
    mb.cylinder((0, 0, 1.92), (0, 0, 1.25), 0.012, 0.012, "iron", w, segments=4)
    mb.cylinder((0, 0, 0.82), (0, 0, 1.12), 0.2, 0.3, "iron", w, segments=9)
    mb.cylinder((0, 0, 1.12), (0, 0, 1.16), 0.33, 0.33, "iron", w, segments=9)
    mb.cylinder((0, 0, 1.13), (0, 0, 1.17), 0.27, 0.27, "soup", w, segments=9)
    for sx in (-1, 1):
        mb.cylinder((sx * 0.3, 0, 1.14), (0, 0, 1.27), 0.012, 0.012, "iron", w, segments=4)
    mb.cylinder((0.1, 0.05, 1.15), (0.3, 0.2, 1.5), 0.015, 0.015, "pole", w, segments=4)   # A ladle.
    bones = bones + [("pot", (0, 0, 1.92), (0, 0, 1.2), None)]
    flames = pose
    pose = lambda t: ({**flames(t)[0], "pot": [(kit.X, 3.0 * math.sin(TAU * t)), (kit.Y, 2.0 * math.sin(TAU * 2 * t))]},   # noqa: E731
                      flames(t)[1])
    stump(mb, 1.3, -0.5)
    mb.box((-1.2, -0.6, 0.12), (0.5, 0.35, 0.24), "plank")
    mb.cylinder((-1.2, -0.6, 0.24), (-1.2, -0.6, 0.3), 0.12, 0.14, "emblem_white", segments=8)
    kit.save(mb, FAMILY, "camp_cooking_tripod", COLORS, mech=kit.Mech(bones).clip("burn", 4.0, pose))


def beacon():
    """A signal fire on a stone base: a basket of iron bars on a post."""
    mb = kit.begin()
    rnd = random.Random(5)
    mb.cylinder((0, 0, 0), (0, 0, 0.5), 1.45, 1.35, "stone_dark", segments=8)
    mb.cylinder((0, 0, 0.5), (0, 0, 1.9), 1.2, 1.05, "stone", segments=8)
    mb.cylinder((0, 0, 1.9), (0, 0, 2.1), 1.2, 1.2, "stone_light", segments=8)
    for i in range(14):
        a = rnd.uniform(0, TAU)
        z = rnd.uniform(0.6, 1.7)
        r = 1.2 - 0.107 * (z - 0.5)
        mb.box((math.cos(a) * r, math.sin(a) * r, z), (0.3, 0.12, 0.18), rnd.choice(("stone_dark", "stone_light")),
               rotation_z=a + math.pi / 2)
    for i in range(5):   # Steps on the front.
        mb.box((0, -1.25 - 0.28 * (4 - i), 0.2 + 0.2 * i), (1.0, 0.3, 0.4 + 0.4 * i), "stone_dark")
    for i in range(4):
        a = TAU * i / 4 + 0.785
        mb.cylinder((math.cos(a) * 0.7, math.sin(a) * 0.7, 2.1), (math.cos(a) * 0.45, math.sin(a) * 0.45, 3.5), 0.07, 0.06,
                    "pole_dark", segments=6)
    mb.cylinder((0, 0, 3.45), (0, 0, 3.55), 0.75, 0.75, "iron", segments=8)
    for i in range(8):
        a = TAU * i / 8
        mb.cylinder((math.cos(a) * 0.7, math.sin(a) * 0.7, 3.5), (math.cos(a) * 0.95, math.sin(a) * 0.95, 4.3), 0.025, 0.025,
                    "iron", segments=4)
    mb.cylinder((0, 0, 4.25), (0, 0, 4.3), 0.97, 0.97, "iron", segments=8)
    start = mark(mb)
    bones, pose = fire(mb, (0, 0), 1.5, stones=False)
    moved(mb, start, (0, 0, 3.5))
    bones = [(n, (h[0], h[1], h[2] + 3.5), (t[0], t[1], t[2] + 3.5), p) for n, h, t, p in bones]
    log(mb, (1.6, 0.9, 0.12), (2.4, -0.2, 0.12), 0.12)
    log(mb, (1.75, 1.0, 0.12), (2.6, 0.0, 0.12), 0.11)
    log(mb, (1.75, 0.85, 0.32), (2.5, -0.1, 0.32), 0.11)
    kit.save(mb, FAMILY, "camp_signal_beacon", COLORS, mech=kit.Mech(bones).clip("burn", 4.0, pose))


def static(name, part):
    def build():
        mb = kit.begin()
        part(mb)
        kit.save(mb, FAMILY, name, COLORS)
    return build


def bedrolls(mb):
    bedroll(mb, -0.6, 0, 0, open_=True)
    bedroll(mb, 0.55, 0.55, 20)
    bedroll(mb, 0.6, -0.3, -15, mat="blanket_alt")
    sack(mb, 0.1, -0.75, 0.0, 0.2)


def seats(mb):
    log_seat(mb, 0, 0.55, 0, 1.8)
    stump(mb, -0.6, -0.5)
    stump(mb, 0.5, -0.6, 0.36, 0.2)
    mb.box((0.5, -0.6, 0.39), (0.14, 0.14, 0.05), "plank")
    mb.cylinder((0.5, -0.6, 0.42), (0.5, -0.6, 0.52), 0.05, 0.06, "iron", segments=7)   # A mug, as in the picture.


def explorer_camp(name, cloth, banner_cloth, emblem):
    """The whole camp of the reference picture on an 8 x 8 m plot."""
    def build():
        mb = kit.begin()
        start = mark(mb)
        tent(mb, cloth)
        moved(mb, start, (-0.6, 1.5))
        b1, p1 = fire(mb, (0.4, -2.0), 1.0)
        b2, p2 = banner(mb, (-3.2, -0.9), banner_cloth, emblem)
        log_seat(mb, 0.4, -3.4, 0, 1.7)
        log_seat(mb, 2.0, -1.9, 80, 1.5)
        stump(mb, -1.1, -2.3)
        bedroll(mb, 2.3, -3.3, 30)
        start = mark(mb)
        supplies(mb, cloth)
        moved(mb, start, (2.7, 1.6), -10)
        start = mark(mb)
        weapon_rack(mb)
        moved(mb, start, (-3.0, 2.2), 75)
        rnd = random.Random(8)
        for _ in range(7):
            rock(mb, rnd.uniform(-3.8, 3.8), rnd.uniform(-3.8, -2.8), 0.08, rnd.uniform(0.12, 0.3), rnd)
        mech = kit.Mech(b1 + b2).clip("idle", 6.0, merged(p1, lambda t: p2((t * 2) % 1.0)))
        kit.save(mb, FAMILY, name, COLORS, mech=mech)
    return build


MODELS = {
    "camp_tent": tent_model("camp_tent", "canvas"),
    "camp_tent_hide": tent_model("camp_tent_hide", "hide"),
    "camp_tent_blue": tent_model("camp_tent_blue", "cloth_blue", "emblem_white"),
    "camp_tent_red": tent_model("camp_tent_red", "cloth_red", "emblem_gold"),
    "camp_command_tent": command_tent,
    "camp_banner_wolf_blue": banner_model("camp_banner_wolf_blue", "cloth_blue", "emblem_white"),
    "camp_banner_wolf_red": banner_model("camp_banner_wolf_red", "cloth_red", "emblem_gold"),
    "camp_banner_wolf_green": banner_model("camp_banner_wolf_green", "cloth_green", "emblem_white"),
    "camp_fire_ring": fire_model("camp_fire_ring", 1.0),
    "camp_bonfire_spit": fire_model("camp_bonfire_spit", 1.5, spit=True),
    "camp_cooking_tripod": cooking_tripod,
    "camp_signal_beacon": beacon,
    "camp_bedrolls": static("camp_bedrolls", bedrolls),
    "camp_log_seats": static("camp_log_seats", seats),
    "camp_supplies": static("camp_supplies", supplies),
    "camp_lean_to": static("camp_lean_to", lean_to),
    "camp_lookout": static("camp_lookout", lookout),
    "camp_lookout_open": static("camp_lookout_open", lambda mb: lookout(mb, roof=False)),
    "camp_weapon_rack": static("camp_weapon_rack", weapon_rack),
    "camp_map_table": static("camp_map_table", map_table),
    "camp_drying_rack": static("camp_drying_rack", drying_rack),
    "camp_explorer": explorer_camp("camp_explorer", "canvas", "cloth_blue", "emblem_white"),
    "camp_explorer_hide": explorer_camp("camp_explorer_hide", "hide", "cloth_red", "emblem_gold"),
}

kit.run(MODELS, FAMILY)
