"""Flamingo: pink, standing on one leg with the other folded, a long
S-curved neck made of a chain of capsules, a bent pale beak with a black
tip and the wings folded against the body as plates."""

import random

from mathutils import Vector

import common
import studies

BODY = ((0.0, 0.02, 0.86), (0.13, 0.22, 0.13))
REAR = ((0.0, 0.2, 0.88), (0.085, 0.15, 0.075))
HEAD = ((0.0, -0.13, 1.3), (0.045, 0.065, 0.048))
# The neck: a chain of points from the chest to the head, S-curved.
NECK = [(0.0, -0.15, 0.9), (0.0, -0.22, 0.98), (0.0, -0.2, 1.06), (0.0, -0.12, 1.12),
        (0.0, -0.08, 1.19), (0.0, -0.1, 1.26), (0.0, -0.13, 1.3)]
NECK_R = [0.07, 0.042, 0.034, 0.03, 0.03, 0.032, 0.04]
EYE = (0.035, -0.16, 1.315)
# The standing leg (hip, ankle, foot) and the folded one.
STAND = [(0.035, 0.04, 0.8), (0.035, 0.05, 0.42), (0.035, 0.02, 0.012)]
FOLD = [(-0.04, 0.05, 0.8), (-0.045, -0.03, 0.54), (-0.04, 0.16, 0.62)]


# Wing feather rows: (height, half height, lift off the body, [(front, back, material)]).
WING_ROWS = [
    (0.83, 0.04, 0.008, [(-0.08, 0.12, "wing")]),
    (0.88, 0.042, 0.014, [(-0.13, 0.03, "wing"), (0.01, 0.19, "wing")]),
    (0.93, 0.036, 0.02, [(-0.1, 0.1, "wing"), (0.12, 0.27, "black")]),
]


def flank_x(y, z):
    """How far the body surface is from the middle at (y, z)."""
    x = 0.03
    for c, r in (BODY, REAR):
        t = 1.0 - ((y - c[1]) / r[1]) ** 2 - ((z - c[2]) / r[2]) ** 2
        if t > 0.0:
            x = max(x, r[0] * t ** 0.5)
    return x


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


def chain(mb, points, r0, r1, mat, segments=5):
    """Tapered cylinders along a polyline, with a small ball at each bend."""
    n = len(points) - 1
    for i, (a, b) in enumerate(zip(points, points[1:])):
        ra, rb = r0 + (r1 - r0) * i / n, r0 + (r1 - r0) * (i + 1) / n
        mb.cylinder(a, b, ra, rb, mat, segments=segments)
        if 0 < i + 1 < n:
            mb.sphere(b, rb * 1.1, mat, segments=5, rings=3)


class Flamingo(studies.Spec):
    name = "flamingo"
    colors = {
        "pink": common.rgb(0xF08AA8),
        "pink_light": common.rgb(0xF7A2BC),
        "pink_shade": common.rgb(0xE07596),
        "wing": common.rgb(0xE8607F),
        "black": common.rgb(0x1C1618),
        "beak": common.rgb(0xF6E6DC),
        "leg": common.rgb(0xE56E8E),
        "eye": common.rgb(0x151012),
    }
    ellipsoids = [BODY, REAR, HEAD]
    capsules = [(a, b, ra, rb) for a, b, ra, rb in zip(NECK, NECK[1:], NECK_R, NECK_R[1:])]
    budget = 400
    max_tris = 1000
    tone_material = "pink"

    def paint(self, c, n):
        return "pink"

    def details(self, mb):
        # Beak: straight out from the face, then bent down to a black tip.
        base, bend, tip = Vector((0, -0.18, 1.305)), Vector((0, -0.245, 1.29)), Vector((0, -0.265, 1.22))
        mb.cylinder(base, bend, 0.026, 0.019, "beak", segments=6)
        mb.sphere(bend, 0.019, "beak", segments=6, rings=3)
        mid = bend.lerp(tip, 0.45)
        mb.cylinder(bend, mid, 0.019, 0.015, "beak", segments=6)
        mb.cylinder(mid, tip, 0.015, 0.003, "black", segments=6)
        for s in (-1, 1):
            mb.sphere((s * EYE[0], EYE[1], EYE[2]), 0.009, "eye", segments=6, rings=4)
            # Folded wing: rows of feathers laid on the flank like shingles,
            # the upper rows over the lower ones, black flight feathers at the back.
            for z, h, lift, feathers in WING_ROWS:
                for y0, y1, mat in feathers:
                    pts = [(y0, z + h), (y1, z + h * 0.6), (y1 + 0.05, z), (y1, z - h * 0.6), (y0, z - h)]
                    studies.plate(mb, [(s * (flank_x(y, zz) + lift), y, zz) for y, zz in pts], 0.012, mat)
        for leg in (STAND, FOLD):
            chain(mb, leg, 0.017, 0.012, "leg")
            mb.sphere(leg[1], 0.02, "leg", segments=6, rings=4)
        # Webbed foot on the ground and the folded one's toes.
        x, y = STAND[2][0], STAND[2][1]
        studies.plate(mb, [(x, y + 0.02, 0.0), (x + 0.05, y - 0.09, 0.0), (x - 0.05, y - 0.09, 0.0)],
                      0.015, "leg")
        f = Vector(FOLD[2])
        studies.plate(mb, [f, f + Vector((0.025, 0.06, -0.02)), f + Vector((-0.025, 0.06, -0.02))],
                      0.012, "leg")


SPECS = [Flamingo()]
