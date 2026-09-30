"""Elephant: blue-grey with lighter and darker facets, pillar legs, big flat
ears, a trunk of tapering capsules hanging almost to the ground, white
tusks and a thin tail with a dark tuft."""

from mathutils import Vector

import common
import studies

LEG_X = 0.5
FRONT_Y, HIND_Y = -0.62, 0.95
# The trunk, from the face down to the slightly curled tip.
TRUNK = [(0, -1.78, 2.2), (0, -1.97, 1.78), (0, -2.05, 1.3), (0, -2.03, 0.85), (0, -1.97, 0.5),
         (0, -2.03, 0.28), (0, -2.14, 0.24)]
TRUNK_R = [0.27, 0.21, 0.165, 0.135, 0.115, 0.1, 0.095]
TAIL = [(0, 1.52, 2.25), (0, 1.62, 1.9), (0, 1.66, 1.5)]


def on_surface(spec, origin, direction, sink=0.0):
    """The point where a ray from inside the spec's shape leaves it, moved
    `sink` back inside (details that must touch the skin: eyes)."""
    o, d = Vector(origin), Vector(direction).normalized()
    t = 0.0
    while studies.sdf(spec, o + d * t) < 0.0 and t < 5.0:
        t += 0.004
    return o + d * (t - sink)


class Elephant(studies.Spec):
    name = "elephant"
    budget = 1100
    max_tris = 2000
    tone_material = "elephant"
    colors = {
        "elephant": common.rgb(0x6F809E),
        "elephant_light": common.rgb(0x8090AC),
        "elephant_shade": common.rgb(0x5E6D8A),
        "ear": common.rgb(0x7888A5),
        "tusk": common.rgb(0xF3EDE0),
        "eye": common.rgb(0x151012),
    }
    ellipsoids = [
        ((0, 0.2, 1.95), (0.8, 1.2, 0.9)),        # Body.
        ((0, -0.45, 2.12), (0.78, 0.62, 0.88)),   # Shoulders.
        ((0, 0.95, 1.9), (0.72, 0.6, 0.82)),      # Rump.
        ((0, -1.3, 2.42), (0.6, 0.52, 0.64)),     # Head.
        ((0, -1.62, 2.26), (0.44, 0.3, 0.48)),    # Face.
        ((0, -1.78, 1.95), (0.2, 0.12, 0.12)),    # Mouth.
    ]
    capsules = [(a, b, ra, rb) for a, b, ra, rb in zip(TRUNK, TRUNK[1:], TRUNK_R, TRUNK_R[1:])]
    for _x in (-LEG_X, LEG_X):
        capsules += [
            ((_x, FRONT_Y, 1.65), (_x, FRONT_Y, 0.3), 0.33, 0.28),
            ((_x, FRONT_Y - 0.02, 0.0), (_x, FRONT_Y - 0.02, 0.25), 0.31, 0.3),
            ((_x * 0.95, HIND_Y, 1.7), (_x, HIND_Y + 0.03, 0.3), 0.36, 0.28),
            ((_x, HIND_Y + 0.02, 0.0), (_x, HIND_Y + 0.02, 0.25), 0.31, 0.3),
        ]
    del _x

    def paint(self, c, n):
        return "elephant"

    def details(self, mb):
        for s in (-1, 1):
            eye = on_surface(self, (s * 0.2, -1.5, 2.5), (s, -0.55, 0.05), 0.02)
            mb.sphere(eye, 0.05, "eye", segments=6, rings=4)
            # A big ear fanned back from the side of the head, folded once
            # so its two halves catch the light differently.
            top, mid, bottom = (s * 0.5, -1.18, 2.88), (s * 0.58, -1.12, 2.45), (s * 0.55, -1.1, 1.98)
            back = (s * 1.1, -0.7, 2.35)
            studies.plate(mb, [top, (s * 0.8, -0.94, 3.02), (s * 1.03, -0.76, 2.78), back, mid], 0.06, "ear")
            studies.plate(mb, [mid, back, (s * 1.02, -0.75, 1.9), (s * 0.8, -0.92, 1.55), bottom], 0.06,
                          "elephant_shade")
            # A tusk curving forward and up from the mouth.
            pts = [Vector((s * 0.2, -1.8, 2.0)), Vector((s * 0.25, -2.08, 1.78)),
                   Vector((s * 0.26, -2.38, 1.78)), Vector((s * 0.22, -2.56, 1.95))]
            radii = [0.075, 0.062, 0.045, 0.0]
            for (a, b), (ra, rb) in zip(zip(pts, pts[1:]), zip(radii, radii[1:])):
                mb.cylinder(a, b, ra, rb, "tusk", segments=6)
        for a, b in zip(TAIL, TAIL[1:]):
            mb.cylinder(a, b, 0.05, 0.04, "elephant", segments=5)
        studies.plate(mb, [(0, 1.64, 1.56), (0.0, 1.7, 1.5), (0, 1.72, 1.32), (0, 1.63, 1.36)], 0.06, "eye")


SPECS = [Elephant()]
