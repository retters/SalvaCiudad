"""Rooster: orange neck and back, a red wing patch, a dark blue breast and
thighs, a fan of iridescent sickle tail feathers (teal, green and blue
ribbons), a red comb and wattle, a yellow beak and yellow legs with toes."""

import math

from mathutils import Vector

import common
import studies

HEAD = ((0.0, -0.115, 0.47), (0.048, 0.058, 0.052))
BREAST = ((0.0, -0.05, 0.28), (0.11, 0.12, 0.125))
BACK = ((0.0, 0.07, 0.3), (0.1, 0.13, 0.105))
EYE = (0.036, -0.145, 0.482)
LEG_X = 0.045
TAIL_BASE = Vector((0.0, 0.15, 0.35))
# Sickle feathers: (start angle up from +Y in degrees, length, curl in
# degrees, x offset, material), back to front.
FEATHERS = [
    (62, 0.27, 115, 0.0, "blue"),
    (86, 0.34, 145, -0.03, "green"),
    (86, 0.34, 145, 0.03, "green"),
    (104, 0.39, 160, 0.012, "teal"),
    (122, 0.32, 165, -0.012, "blue"),
]


def ribbon(mb, centers, widths, side_axis, thickness, mat):
    """A thin curved strip (a feather) along `centers`: at every point the
    strip is `widths[i]` wide, across the line and away from side_axis
    (the direction its flat faces look to)."""
    side_axis = Vector(side_axis).normalized()
    pts = [Vector(c) for c in centers]
    off = side_axis * (thickness * 0.5)
    rows = []
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        across = t.cross(side_axis).normalized() * (widths[i] * 0.5)
        rows.append([mb.bm.verts.new(p + a + o) for a in (-across, across) for o in (off, -off)])
    # Each row: [left front, left back, right front, right back].
    faces = []
    for r0, r1 in zip(rows, rows[1:]):
        faces.append((r0[0], r0[2], r1[2], r1[0]))   # Front.
        faces.append((r0[3], r0[1], r1[1], r1[3]))   # Back.
        faces.append((r0[1], r0[0], r1[0], r1[1]))   # Left edge.
        faces.append((r0[2], r0[3], r1[3], r1[2]))   # Right edge.
    faces.append((rows[0][0], rows[0][1], rows[0][3], rows[0][2]))
    faces.append((rows[-1][2], rows[-1][3], rows[-1][1], rows[-1][0]))
    for f in faces:
        mb.bm.faces.new(f)
    return mb._finish([v for r in rows for v in r], mat, None)


def sickle(start, length, curl, stations=5):
    pts = []
    p = Vector(TAIL_BASE)
    step = length / (stations - 1)
    for i in range(stations):
        pts.append(p.copy())
        a = math.radians(start - curl * (i + 0.5) / (stations - 1))
        p += Vector((0.0, math.cos(a), math.sin(a))) * step
    return pts


class Rooster(studies.Spec):
    name = "rooster"
    colors = {
        "orange": common.rgb(0xF08A1C),
        "orange_light": common.rgb(0xF7AE34),
        "orange_shade": common.rgb(0xE0701A),
        "red": common.rgb(0xD8302A),
        "blue": common.rgb(0x1F3F86),
        "green": common.rgb(0x2E9A48),
        "teal": common.rgb(0x16A0A0),
        "yellow": common.rgb(0xF4BE2A),
        "eye": common.rgb(0x151012),
    }
    ellipsoids = [
        BREAST, BACK, HEAD,
        ((LEG_X, 0.02, 0.2), (0.045, 0.065, 0.065)),    # Thighs.
        ((-LEG_X, 0.02, 0.2), (0.045, 0.065, 0.065)),
        ((0.0, 0.17, 0.35), (0.05, 0.06, 0.06)),      # Tail root.
    ]
    capsules = [((0.0, -0.06, 0.33), (0.0, -0.1, 0.45), 0.078, 0.052)]  # Neck.
    budget = 320
    max_tris = 800
    tone_material = "orange"
    tones = 0.35

    def __init__(self):
        breast = Vector((0, -1, -0.35)).normalized()
        self.cuts = [
            ((0, -0.03, 0.3), breast, lambda c, n: c.z < 0.38),     # Breast border.
            ((0, 0, 0.255), (0, 0, 1), lambda c, n: abs(c.x) > 0.06),  # Wing bottom.
        ]
        self.breast_plane = (Vector((0, -0.03, 0.3)), breast)

    def paint(self, c, n):
        p, no = self.breast_plane
        if c.z < 0.255 and abs(c.x) > 0.02 and c.y > -0.03 or c.z < 0.18:
            return "blue"  # Thighs and underside.
        if (c - p).dot(no) > 0 and c.z < 0.38:
            return "blue"  # Breast.
        if abs(c.x) > 0.06 and 0.255 < c.z < 0.35 and -0.03 < c.y < 0.17:
            return "red"  # Wing.
        if c.z > 0.44 and c.y < -0.09:
            return "red"  # Face.
        if c.y > 0.14:
            return "blue" if c.z < 0.3 else "orange"
        return "orange"

    def details(self, mb):
        for start, length, curl, x, mat in FEATHERS:
            # Side feathers fan out sideways toward their tips.
            pts = [p + Vector((x * (1 + 1.6 * i / 4), 0, 0)) for i, p in enumerate(sickle(start, length, curl))]
            widths = [0.045, 0.065, 0.06, 0.042, 0.01]
            ribbon(mb, pts, widths, (1, 0, 0), 0.01, mat)
        for s in (-1, 1):
            mb.sphere((s * EYE[0], EYE[1], EYE[2]), 0.01, "eye", segments=5, rings=3)
            # Leg, and three toes forward and one back.
            x = s * LEG_X
            mb.cylinder((x, 0.02, 0.17), (x, 0.0, 0.015), 0.015, 0.012, "yellow", segments=5)
            for dx, dy in ((-0.028, -0.05), (0.0, -0.06), (0.028, -0.05), (0.0, 0.035)):
                mb.cylinder((x, 0.0, 0.01), (x + dx, dy, 0.006), 0.009, 0.005, "yellow", segments=3)
        # Beak: a cone out of the face.
        mb.cylinder((0, -0.16, 0.468), (0, -0.215, 0.458), 0.018, 0.0, "yellow", segments=5)
        # Comb: three rounded points along the top of the head.
        for y, h in ((-0.15, 0.045), (-0.115, 0.06), (-0.08, 0.05)):
            studies.plate(mb, [(0, y - 0.02, 0.5), (0, y + 0.02, 0.505), (0, y + 0.012, 0.505 + h * 0.8),
                               (0, y, 0.505 + h), (0, y - 0.014, 0.505 + h * 0.8)], 0.014, "red")
        # Wattle under the beak.
        studies.plate(mb, [(0, -0.145, 0.45), (0, -0.18, 0.445), (0, -0.175, 0.405), (0, -0.158, 0.395),
                           (0, -0.14, 0.42)], 0.016, "red")


SPECS = [Rooster()]
