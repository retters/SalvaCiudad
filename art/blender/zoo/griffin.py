"""Griffin: an eagle's front (white head, yellow hooked beak, brown
feathered chest, yellow scaly legs with dark talons) on a lion's hind body
(tawny legs and a tail ending in a dark tuft), with big brown wings raised
as layered feather plates."""

import random

from mathutils import Vector

import common
import studies

X_FRONT, X_HIND = 0.24, 0.25
TAIL = [(0.0, 0.85, 1.28), (0.0, 1.15, 1.05), (0.03, 1.45, 0.88), (0.08, 1.72, 0.92), (0.12, 1.92, 1.08)]
TAIL_R = [0.075, 0.06, 0.05, 0.045, 0.04]
TUFT = ((0.13, 1.99, 1.16), (0.08, 0.1, 0.12))
HEAD_C = (0.0, -1.02, 2.12)
EYE = (0.135, -1.16, 2.19)
# Where the white of the head and neck begins: a slanted plane.
WHITE_P, WHITE_N = Vector((0.0, -0.8, 1.78)), Vector((0.0, -0.55, 1.0)).normalized()
BEAK_Y = -1.225     # In front of this the head is the yellow beak.
SCALES_Z = 0.52     # Below this the eagle legs are yellow.
LION_P, LION_N = Vector((0.0, 0.12, 0.0)), Vector((0.0, 1.0, 0.35)).normalized()
# The wing's leading edge, shoulder to tip (right side, x > 0).
WING_EDGE = [(0.26, -0.38, 1.7), (0.66, -0.3, 2.15), (1.02, -0.12, 2.58), (1.3, 0.18, 2.92)]


def tone_faces(mb, mat, share, seed=11):
    """Facet tones for a second material (finish() only tones one): turns a
    share of its faces into <mat>_light and <mat>_shade."""
    if mat not in mb.materials:
        return
    rnd = random.Random(seed)
    main = mb.materials.index(mat)
    light, shade = mb._material_index(mat + "_light"), mb._material_index(mat + "_shade")
    for f in mb.bm.faces:
        if f.material_index == main:
            r = rnd.random()
            if r < share * 0.5:
                f.material_index = light
            elif r < share:
                f.material_index = shade


def polyline_at(points, t):
    """The point and the unit tangent at t (0..1, by length) along a polyline."""
    pts = [Vector(p) for p in points]
    lengths = [(b - a).length for a, b in zip(pts, pts[1:])]
    d = t * sum(lengths)
    for (a, b), seg in zip(zip(pts, pts[1:]), lengths):
        if d <= seg or b is pts[-1]:
            return a.lerp(b, min(1.0, d / seg)), (b - a).normalized()
        d -= seg


def feather(mb, base, edge, direction, length, width, lift, mat):
    """A long feather plate from `base` along `direction`, `width` across
    (along `edge`), moved `lift` along the wing's normal."""
    across = (edge - direction * edge.dot(direction)).normalized()
    n = across.cross(direction).normalized() * lift
    pts = [base - across * width * 0.5, base + across * width * 0.5,
           base + direction * length * 0.82 + across * width * 0.42, base + direction * length,
           base + direction * length * 0.82 - across * width * 0.42]
    studies.plate(mb, [p + n for p in pts], 0.02, mat)


def wing(mb, s):
    """A raised wing on side s: an arm along the leading edge, a covert
    panel and a fan of long flight feathers pointing back."""
    edge = [Vector((s * x, y, z)) for x, y, z in WING_EDGE]
    for i, (a, b) in enumerate(zip(edge, edge[1:])):
        mb.cylinder(a, b, 0.085 - i * 0.02, 0.065 - i * 0.02, "wing", segments=6)
        if i:
            mb.sphere(a, 0.085 - i * 0.02, "wing", segments=6, rings=4)
    count = 11
    for i in range(count):
        t = i / (count - 1)
        base, tangent = polyline_at(edge, 0.08 + t * 0.92)
        # Back and down near the body, fanning back and up at the tip.
        direction = Vector((s * (0.3 + 0.25 * t), 1.0, -0.75 + 0.95 * t)).normalized()
        length = 0.7 + 0.55 * t - 0.25 * t * t
        mat = "feather_dark" if i % 2 else "feather"
        feather(mb, base, tangent, direction, length, 0.36, s * 0.006 * i, mat)
        if i % 2 == 0 and i < count - 1:
            # Short covert feathers over the feathers' bases.
            feather(mb, base + tangent * 0.08, tangent, direction, length * 0.45, 0.34,
                    s * (0.006 * count + 0.015), "wing")


class Griffin(studies.Spec):
    name = "griffin"
    colors = {
        "brown": common.rgb(0x8A5530),
        "brown_light": common.rgb(0x9C6538),
        "brown_shade": common.rgb(0x774628),
        "tawny": common.rgb(0xB9854A),
        "tawny_light": common.rgb(0xC8955A),
        "tawny_shade": common.rgb(0xA6743E),
        "white": common.rgb(0xF3F0E8),
        "yellow": common.rgb(0xF2B324),
        "wing": common.rgb(0x9A6236),
        "feather": common.rgb(0x7A4A28),
        "feather_dark": common.rgb(0x5E391F),
        "claw": common.rgb(0x2A2220),
        "eye": common.rgb(0x151012),
    }
    ellipsoids = [
        ((0.0, -0.42, 1.32), (0.36, 0.5, 0.42)),       # Chest.
        ((0.0, 0.35, 1.22), (0.32, 0.55, 0.36)),       # Hind body.
        ((X_HIND * 0.9, 0.55, 1.02), (0.14, 0.3, 0.34)),   # Thighs.
        ((-X_HIND * 0.9, 0.55, 1.02), (0.14, 0.3, 0.34)),
        (HEAD_C, (0.19, 0.24, 0.2)),                   # Head.
        ((0.0, -1.3, 2.07), (0.085, 0.14, 0.1)),       # Beak.
        TUFT,
    ]
    capsules = [((0.0, -0.7, 1.55), (0.0, -0.95, 1.98), 0.27, 0.19)] + [
        cap for s in (-1, 1) for cap in (
            ((s * X_FRONT, -0.55, 1.15), (s * X_FRONT, -0.66, 0.55), 0.14, 0.09),   # Eagle thigh.
            ((s * X_FRONT, -0.66, 0.55), (s * X_FRONT, -0.7, 0.08), 0.065, 0.06),   # Scaly leg.
            ((s * X_HIND, 0.55, 0.95), (s * X_HIND, 0.8, 0.45), 0.13, 0.085),       # Lion leg to the hock.
            ((s * X_HIND, 0.8, 0.45), (s * X_HIND, 0.7, 0.1), 0.08, 0.075),
            ((s * X_HIND, 0.72, 0.075), (s * X_HIND, 0.55, 0.075), 0.085, 0.075),   # Paw.
        )] + [(a, b, ra, rb) for a, b, ra, rb in zip(TAIL, TAIL[1:], TAIL_R, TAIL_R[1:])]
    cuts = [
        (WHITE_P, WHITE_N, lambda c, n: c.y < -0.5 and c.z > 1.4),
        ((0, BEAK_Y, 0), (0, 1, 0), lambda c, n: c.z > 1.85),
        ((0, 0, SCALES_Z), (0, 0, 1), lambda c, n: c.y < -0.3),
        (LION_P, LION_N, lambda c, n: True),
    ]
    budget = 1200
    max_tris = 3000
    tone_material = "brown"

    def paint(self, c, n):
        if c.y < -0.3 and c.z < SCALES_Z:
            return "yellow"
        if c.y < -0.5 and c.z > 1.4 and (c - WHITE_P).dot(WHITE_N) > 0:
            return "yellow" if c.y < BEAK_Y else "white"
        if c.y > 1.85:
            return "feather_dark"  # Tail tuft.
        if (c - LION_P).dot(LION_N) > 0:
            return "tawny"
        return "brown"

    def on_head(self, direction, lift):
        """The head's surface seen from its center along direction, lifted."""
        d = Vector(direction).normalized()
        p = Vector(HEAD_C)
        while studies.sdf(self, p) < 0.0:
            p += d * 0.005
        return p + d * lift

    def details(self, mb):
        tone_faces(mb, "tawny", 0.3)
        # Beak hook: a cone curving down in front of the beak.
        mb.cylinder((0, -1.38, 2.09), (0, -1.47, 2.02), 0.055, 0.035, "yellow", segments=6)
        mb.cylinder((0, -1.47, 2.02), (0, -1.46, 1.93), 0.035, 0.004, "yellow", segments=6)
        for s in (-1, 1):
            mb.sphere((s * EYE[0], EYE[1], EYE[2]), 0.03, "eye", segments=6, rings=4)
            # A heavy brow over the eye.
            brow = [self.on_head((s * x, y, z), 0.012) for x, y, z in
                    ((0.45, -0.25, 0.6), (0.6, -0.75, 0.42), (0.35, -0.75, 0.6))]
            studies.flap(mb, *brow, 0.03, "white")
            wing(mb, s)
            # Eagle talons: three toes forward, one back, dark claws.
            x = s * X_FRONT
            ankle = Vector((x, -0.7, 0.06))
            for dx, dy in ((-0.09, -0.2), (0.0, -0.24), (0.09, -0.2), (0.0, 0.16)):
                tip = ankle + Vector((dx, dy, -0.03))
                mb.cylinder(ankle, tip, 0.04, 0.03, "yellow", segments=5)
                d = (tip - ankle).normalized()
                mb.cylinder(tip, tip + d * 0.07 + Vector((0, 0, -0.03)), 0.028, 0.003, "claw", segments=5)


SPECS = [Griffin()]
