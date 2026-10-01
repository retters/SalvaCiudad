"""Quiver (reference 16): a tapered brown leather case with a collar and a
base band, and five red-fletched arrows sticking out of its open top."""

import math

from mathutils import Vector

import studies
from _parts_b import fletching, shades, tone, tube

# The arrows: (x at the mouth, lean in degrees to +X, nock height, y).
ARROWS = [(-0.056, -8.0, 0.66, 0.012), (-0.03, -3.0, 0.7, -0.012), (-0.004, 1.0, 0.715, 0.014),
          (0.022, 4.0, 0.735, -0.012), (0.046, 7.0, 0.74, 0.012)]


class Quiver(studies.Spec):
    name = "w16_quiver"
    colors = {**shades("leather", 0x7F4529, 0.14), "dark": shades("d", 0x36190F)["d"],
              "shaft": shades("s", 0x5E3220)["s"], "red": shades("r", 0xDC1C1B)["r"],
              "red_shade": shades("r", 0xA81414)["r"]}
    max_tris = 600
    grip = (0.0, 0.06, 0.34)

    def details(self, mb):
        def r(k):
            return (0.062 * k, 0.092 * k)   # Depth (Y) and width (X) of the hexagonal case.

        body = tube(mb, [
            ((0, 0, 0.0), r(0.78), "leather_shade"), ((0, 0, 0.04), r(0.8), "leather"),
            ((0, 0, 0.04), r(0.72), "leather"), ((0, 0, 0.47), r(0.9), "leather_light"),
            ((0, 0, 0.47), r(1.0), "leather_light"), ((0, 0, 0.545), r(1.03), "dark"),
            ((0, 0, 0.545), r(0.86), "dark"), ((0, 0, 0.52), r(0.86), "dark"), ((0, 0, 0.519), r(0.86), "dark"),
        ], sides=6)
        tone(mb, body, "leather", seed=4, share=0.6)
        for x, lean, top, y in ARROWS:
            a = math.radians(lean)
            d = Vector((math.sin(a), 0.0, math.cos(a)))
            foot = Vector((x, y, 0.5))
            nock = foot + d * ((top - 0.5) / d.z)
            mb.cylinder(foot, nock, 0.006, 0.006, "shaft", segments=3)
            fletching(mb, nock + d * 0.012, -d, 0.1, 0.034, 0.03, (0,), "red", start=0.0)
            fletching(mb, nock + d * 0.012, -d, 0.1, 0.034, 0.03, (180,), "red_shade", start=0.0)


SPECS = [Quiver()]
