"""Pieces shared by the proposal families written with MeshBuilder: flat
polygons with thickness, beams, wheels, logs, rocks, crates, barrels, sacks.

A family merges COLORS into its own colors, since the pieces name their
materials ("plank", "iron", "rope", "stone"...).
"""

import math

from mathutils import Matrix, Vector

import common

TAU = 2 * math.pi
C = common.rgb
COLORS = {
    "pole": C(0x7A5232), "pole_dark": C(0x5A3B24), "bark": C(0x6B4A2E), "log_end": C(0xC8A06A),
    "plank": C(0xA07A4A), "plank_dark": C(0x7E5C36), "plank_light": C(0xC09A64),
    "rope": C(0xB89A64), "leather": C(0x6B4A2E), "iron": C(0x44484E), "steel": C(0x9AA2AA), "gold": C(0xC9A441),
    "stone": C(0x9A938A), "stone_dark": C(0x78726A), "stone_light": C(0xB4AEA4),
    "sack": C(0xC8B48A), "window": C(0xF6D070), "hay": C(0xD8B85A), "hay_dark": C(0xB89640),
}


def solid(mb, ring, offset, mat, weights=None):
    """A flat polygon (3D points) given a thickness: extruded along `offset`."""
    off = Vector(offset)
    a = [mb.bm.verts.new(Vector(p)) for p in ring]
    b = [mb.bm.verts.new(Vector(p) + off) for p in ring]
    n = len(ring)
    mb.bm.faces.new(list(reversed(a)))
    mb.bm.faces.new(b)
    for i in range(n):
        j = (i + 1) % n
        mb.bm.faces.new((a[i], a[j], b[j], b[i]))
    return mb._finish(a + b, mat, weights)


def mark(mb):
    """What the builder holds now; see moved(). The vertices themselves are
    remembered, not how many there are: a cone that ends in a point merges
    vertices, and after that new ones no longer come last."""
    return set(mb.bm.verts)


def moved(mb, start, at, rot=0.0):
    """Moves what was built since mark() to `at`, turned `rot` degrees around Z."""
    m = Matrix.Translation((at[0], at[1], at[2] if len(at) > 2 else 0.0)) @ Matrix.Rotation(math.radians(rot), 4, "Z")
    for v in mb.bm.verts:
        if v not in start:
            v.co = m @ v.co


def beam(mb, a, b, r, mat, weights=None):
    """A square beam between two points (`r` is half its diagonal)."""
    mb.cylinder(a, b, r, r, mat, weights, segments=4)


def log(mb, a, b, r, weights=None, mat="bark"):
    a, b = Vector(a), Vector(b)
    d = (b - a).normalized()
    mb.cylinder(a, b, r, r * 0.92, mat, weights, segments=7)
    mb.cylinder(a - d * 0.006, a + d * 0.02, r * 0.78, r * 0.78, "log_end", weights, segments=7)
    mb.cylinder(b - d * 0.02, b + d * 0.006, r * 0.72, r * 0.72, "log_end", weights, segments=7)


def rope(mb, a, b, r=0.014, weights=None):
    mb.cylinder(a, b, r, r, "rope", weights, segments=4)


def rock(mb, x, y, z, r, rnd, mat=None, weights=None):
    mat = mat or rnd.choice(("stone", "stone_dark", "stone_light"))
    mb.sphere((x, y, z), r, mat, weights, segments=6, rings=4,
              scale=(rnd.uniform(0.85, 1.25), rnd.uniform(0.85, 1.25), rnd.uniform(0.55, 0.8)))


def crate(mb, x, y, z, s, h=None, weights=None):
    h = h or s
    mb.box((x, y, z + h / 2), (s, s, h), "plank", weights)
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.box((x + sx * s / 2, y + sy * s / 2, z + h / 2), (0.07, 0.07, h + 0.03), "plank_dark", weights)
    mb.box((x, y, z + h + 0.012), (s + 0.04, s + 0.04, 0.035), "plank_dark", weights)
    mb.box((x, y, z + h + 0.035), (s * 0.82, s * 0.22, 0.03), "plank", weights)


def barrel(mb, x, y, z=0.0, h=0.85, r=0.3, weights=None):
    mb.cylinder((x, y, z), (x, y, z + h * 0.5), r * 0.86, r, "plank", weights, segments=10)
    mb.cylinder((x, y, z + h * 0.5), (x, y, z + h), r, r * 0.86, "plank", weights, segments=10)
    for k in (0.18, 0.5, 0.82):
        rr = r * (0.9 + 0.12 * (1 - abs(k - 0.5) * 2))
        mb.cylinder((x, y, z + h * k - 0.025), (x, y, z + h * k + 0.025), rr, rr, "iron", weights, segments=10)


def sack(mb, x, y, z, r=0.26, weights=None):
    mb.sphere((x, y, z + r * 0.75), r, "sack", weights, segments=7, rings=5, scale=(1.0, 0.85, 0.9))
    mb.cylinder((x, y, z + r * 1.35), (x, y, z + r * 1.7), r * 0.2, r * 0.3, "sack", weights, segments=6)
    mb.cylinder((x, y, z + r * 1.38), (x, y, z + r * 1.46), r * 0.24, r * 0.24, "rope", weights, segments=6)


def stump(mb, x, y, h=0.42, r=0.24):
    mb.cylinder((x, y, 0), (x, y, h), r * 1.12, r, "bark", segments=8)
    mb.cylinder((x, y, h - 0.01), (x, y, h + 0.012), r * 0.86, r * 0.86, "log_end", segments=8)


def lantern(mb, x, y, z, weights=None):
    mb.box((x, y, z + 0.02), (0.14, 0.14, 0.04), "iron", weights)
    mb.box((x, y, z + 0.13), (0.1, 0.1, 0.18), "window", weights)
    mb.box((x, y, z + 0.24), (0.14, 0.14, 0.04), "iron", weights)
    mb.cylinder((x, y, z + 0.26), (x, y, z + 0.34), 0.05, 0.01, "iron", weights, segments=5)


def gable_roof(mb, cx, cy, w, d, eave, rise, mats, over=0.25, rows=3, thick=0.07, gable=None):
    """A roof with its ridge along X; the slopes pass through the top of the walls."""
    slope = rise / (d / 2)
    for side in (-1, 1):
        for r in range(rows):
            u0, u1 = r / rows, min(1.0, (r + 1) / rows + 0.06)
            y0, y1 = (d / 2 + over) * (1 - u0), (d / 2 + over) * (1 - u1)
            z0, z1 = eave + rise - slope * y0, eave + rise - slope * y1
            solid(mb, [(cx - w / 2 - over, cy + side * y0, z0), (cx + w / 2 + over, cy + side * y0, z0),
                       (cx + w / 2 + over, cy + side * y1, z1), (cx - w / 2 - over, cy + side * y1, z1)], (0, side * thick * 0.4, thick), mats[r % len(mats)])
    mb.box((cx, cy, eave + rise + thick), (w + 2 * over + 0.04, 0.16, 0.1), mats[-1])
    if gable:
        for sx in (-1, 1):
            solid(mb, [(cx + sx * w / 2, cy - d / 2, eave), (cx + sx * w / 2, cy + d / 2, eave), (cx + sx * w / 2, cy, eave + rise)], (-sx * 0.07, 0, 0), gable)


def shed_roof(mb, cx, cy, w, d, low, high, mats, over=0.2, rows=3, thick=0.07):
    """A single slope: low at the front (-Y), high at the back."""
    slope = (high - low) / d
    for r in range(rows):
        u0, u1 = r / rows, min(1.0, (r + 1) / rows + 0.06)
        y0, y1 = cy - d / 2 - over + (d + 2 * over) * u0, cy - d / 2 - over + (d + 2 * over) * u1
        z0, z1 = low + slope * (y0 - (cy - d / 2)), low + slope * (y1 - (cy - d / 2))
        solid(mb, [(cx - w / 2 - over, y0, z0), (cx + w / 2 + over, y0, z0), (cx + w / 2 + over, y1, z1), (cx - w / 2 - over, y1, z1)],
              (0, -thick * 0.3, thick), mats[r % len(mats)])


def plank_box(mb, cx, cy, w, d, z0, z1, mats=("plank", "plank_light"), open_front=False):
    """Walls of vertical boards around a w x d rectangle."""
    def run(x0, y0, x1, y1):
        n = max(1, round(math.hypot(x1 - x0, y1 - y0) / 0.3))
        for k in range(n):
            u = (k + 0.5) / n
            horizontal = abs(x1 - x0) > abs(y1 - y0)
            size = ((abs(x1 - x0) / n, 0.06) if horizontal else (0.06, abs(y1 - y0) / n)) + (z1 - z0,)
            mb.box((x0 + (x1 - x0) * u, y0 + (y1 - y0) * u, (z0 + z1) / 2), size, mats[k % len(mats)])
    run(cx - w / 2, cy + d / 2, cx + w / 2, cy + d / 2)
    run(cx - w / 2, cy - d / 2, cx - w / 2, cy + d / 2)
    run(cx + w / 2, cy - d / 2, cx + w / 2, cy + d / 2)
    if not open_front:
        run(cx - w / 2, cy - d / 2, cx + w / 2, cy - d / 2)
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.box((cx + sx * w / 2, cy + sy * d / 2, (z0 + z1) / 2), (0.1, 0.1, z1 - z0 + 0.04), "plank_dark")


def merged(*poses):
    def pose(t):
        turns, moves = {}, {}
        for p in poses:
            a, b = p(t)
            turns.update(a)
            moves.update(b)
        return turns, moves
    return pose


SPOKES = 8   # A wheel looks the same every 360 / SPOKES degrees.


def wheel(mb, center, r, bone, width=0.09, mat="plank_dark", tire="iron"):
    """A spoked wheel in the YZ plane (its axle along X), weighted to `bone`
    (None for one that does not turn)."""
    x, y, z = center
    w = {bone: 1.0} if bone else None
    n = SPOKES * 2
    for i in range(n):
        a0, a1 = TAU * i / n, TAU * (i + 1) / n
        p0 = (x, y + math.cos(a0) * r, z + math.sin(a0) * r)
        p1 = (x, y + math.cos(a1) * r, z + math.sin(a1) * r)
        beam(mb, p0, p1, width * 0.62, mat, w)
        q0 = (x, y + math.cos(a0) * (r + width * 0.3), z + math.sin(a0) * (r + width * 0.3))
        q1 = (x, y + math.cos(a1) * (r + width * 0.3), z + math.sin(a1) * (r + width * 0.3))
        beam(mb, q0, q1, width * 0.42, tire, w)
    for i in range(SPOKES):
        a = TAU * i / SPOKES
        beam(mb, (x, y, z), (x, y + math.cos(a) * r, z + math.sin(a) * r), width * 0.32, mat, w)
    mb.cylinder((x - width * 0.9, y, z), (x + width * 0.9, y, z), r * 0.2, r * 0.2, mat, w, segments=8)
    mb.cylinder((x - width * 1.1, y, z), (x + width * 1.1, y, z), r * 0.09, r * 0.09, tire, w, segments=6)


def wheel_turn(speed, seconds, r):
    """(degrees a wheel of radius r turns in a looping clip, the speed that
    matches exactly): the turn is rounded to the wheel's symmetry so the
    clip closes."""
    step = 360.0 / SPOKES
    steps = max(1, round(speed * seconds / (TAU * r) * 360.0 / step))
    degrees = steps * step
    return degrees, degrees / 360.0 * TAU * r / seconds
