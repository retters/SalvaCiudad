"""Bald eagle, perched upright: a dark brown body with its wings folded
along the sides, a white head and tail, a big yellow hooked beak and
yellow legs with dark talons."""

import bmesh
from mathutils import Vector

import common
import studies

HEAD = ((0.0, -0.07, 0.725), (0.092, 0.115, 0.09))
EYE = (0.07, -0.13, 0.755)
NECK_PLANE = (Vector((0, 0, 0.64)), Vector((0, -0.35, 1)).normalized())
LEG_X = 0.07


def hull(mb, points, mat):
    """A convex solid around the points (a beak, a talon)."""
    tmp = bmesh.new()
    verts = [tmp.verts.new(p) for p in points]
    res = bmesh.ops.convex_hull(tmp, input=verts)
    bmesh.ops.delete(tmp, geom=[v for v in res["geom_interior"] if isinstance(v, bmesh.types.BMVert)],
                     context="VERTS")
    mapping = {v: mb.bm.verts.new(v.co) for v in tmp.verts}
    for f in tmp.faces:
        mb.bm.faces.new([mapping[v] for v in f.verts])
    tmp.free()
    return mb._finish(list(mapping.values()), mat, None)


def mirror(points, s):
    return [(s * x, y, z) for x, y, z in points]


# Folded wing (right side, x > 0), outline from the shoulder down to the tip.
WING = [(0.12, -0.09, 0.55), (0.13, 0.0, 0.61), (0.16, 0.1, 0.54), (0.12, 0.27, 0.14),
        (0.09, 0.22, 0.12), (0.14, -0.05, 0.36)]
# The long flight feathers at the lower end, a darker layer on the wing.
PRIMARIES = [(0.14, 0.05, 0.36), (0.16, 0.11, 0.42), (0.125, 0.28, 0.1), (0.1, 0.24, 0.1),
             (0.13, 0.03, 0.3)]
TAIL = [(-0.05, 0.12, 0.3), (0.05, 0.12, 0.3), (0.11, 0.4, 0.05), (0.0, 0.45, 0.025), (-0.11, 0.4, 0.05)]


class Eagle(studies.Spec):
    name = "eagle"
    colors = {
        "brown": common.rgb(0x5A3A24),
        "brown_light": common.rgb(0x6C4830),
        "brown_shade": common.rgb(0x4A2E1C),
        "dark": common.rgb(0x3A2517),
        "white": common.rgb(0xF4F2EE),
        "yellow": common.rgb(0xF2B928),
        "eye": common.rgb(0x151012),
    }
    ellipsoids = [
        ((0.0, 0.03, 0.42), (0.145, 0.14, 0.24)),    # Body.
        ((0.0, -0.04, 0.48), (0.13, 0.11, 0.16)),    # Chest.
        ((0.0, 0.0, 0.58), (0.12, 0.11, 0.08)),      # Shoulders.
        HEAD,
        ((0.0, -0.15, 0.7), (0.05, 0.05, 0.045)),    # Face, under the beak.
        ((LEG_X, -0.02, 0.2), (0.06, 0.07, 0.1)),    # Feathered thighs.
        ((-LEG_X, -0.02, 0.2), (0.06, 0.07, 0.1)),
    ]
    capsules = [((0.0, -0.02, 0.58), (0.0, -0.06, 0.7), 0.085, 0.075)]  # Neck.
    cuts = [(NECK_PLANE[0], NECK_PLANE[1], lambda c, n: 0.52 < c.z < 0.75)]
    budget = 380
    max_tris = 800
    tone_material = "brown"
    tones = 0.35

    def paint(self, c, n):
        p, no = NECK_PLANE
        return "white" if (c - p).dot(no) > 0 else "brown"

    def details(self, mb):
        for s in (-1, 1):
            mb.sphere((s * EYE[0], EYE[1], EYE[2]), 0.015, "eye", segments=6, rings=4)
            studies.plate(mb, mirror(WING, s), 0.035, "brown")
            studies.plate(mb, [(x + 0.012, y, z) for x, y, z in mirror(PRIMARIES, s)] if s > 0 else
                          [(x - 0.012, y, z) for x, y, z in mirror(PRIMARIES, s)], 0.02, "dark")
            # Leg, three toes forward and one back, each with a dark talon.
            x = s * LEG_X
            mb.cylinder((x, -0.03, 0.14), (x, -0.04, 0.02), 0.018, 0.015, "yellow", segments=5)
            for dx, dy in ((-0.035, -0.07), (0.0, -0.08), (0.035, -0.07), (0.0, 0.04)):
                tip = Vector((x + dx, -0.04 + dy, 0.012))
                mb.cylinder((x, -0.04, 0.015), tip, 0.011, 0.008, "yellow", segments=4)
                d = (tip - Vector((x, -0.04, 0.015))).normalized()
                mb.cylinder(tip, tip + d * 0.02 - Vector((0, 0, 0.01)), 0.007, 0.0, "dark", segments=3)
        studies.plate(mb, TAIL, 0.03, "white")
        # Beak: a big hooked hull out of the face.
        hull(mb, [(-0.032, -0.14, 0.74), (0.032, -0.14, 0.74), (-0.036, -0.145, 0.69), (0.036, -0.145, 0.69),
                  (0.0, -0.155, 0.755), (-0.02, -0.225, 0.73), (0.02, -0.225, 0.73), (0.0, -0.255, 0.71),
                  (0.0, -0.25, 0.67), (-0.016, -0.21, 0.69), (0.016, -0.21, 0.69)], "yellow")


SPECS = [Eagle()]
