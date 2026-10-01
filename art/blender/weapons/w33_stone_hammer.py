"""Weapon 33: stone hammer. A big rough block of grey rock bound with blue
bands and set with blue stones, on a wooden shaft with a long blue cord
wrap, a blue collar under the head and a faceted stone butt."""

from mathutils import Vector

import common
import studies
import _parts_c as parts

HEAD = (0.0, 0.0, 0.93)
HALF = (0.2, 0.125, 0.145)   # Half sizes of the block.
# Lumps at the corners of the block (x, y, z signs and a size), uneven on purpose.
LUMPS = [(-1, -1, -1, 0.085), (1, -1, -1, 0.075), (-1, 1, -1, 0.08), (1, 1, -1, 0.09),
         (-1, -1, 1, 0.075), (1, -1, 1, 0.09), (-1, 1, 1, 0.09), (1, 1, 1, 0.075)]


def corner(sx, sy, sz, r):
    return (HEAD[0] + sx * (HALF[0] - r), HEAD[1] + sy * (HALF[1] - r), HEAD[2] + sz * (HALF[2] - r))


def head_capsules():
    """The twelve edges of the block, as capsules between its corner lumps."""
    caps = []
    for i, a in enumerate(LUMPS):
        for b in LUMPS[i + 1:]:
            if sum(1 for k in range(3) if a[k] != b[k]) == 1:
                caps.append((corner(*a), corner(*b), a[3], b[3]))
    return caps


class StoneHammer(studies.Spec):
    name = "w33_stone_hammer"
    colors = {
        **parts.shades("rock", 0x6C6470, 0x8D8690, 0x4B4654),
        **parts.shades("blue", 0x2E6CC4, light=0x5A9CE6),
        "wood": common.rgb(0x9A5024),
        "butt": common.rgb(0xA89C96),
    }
    ellipsoids = [(HEAD, (HALF[0] * 0.97, HALF[1] * 0.97, HALF[2] * 0.97)),
                  ((HEAD[0] + 0.05, HEAD[1], HEAD[2] + 0.03), (0.13, HALF[1] * 1.04, 0.12)),
                  ((HEAD[0] - 0.09, HEAD[1] - 0.01, HEAD[2] - 0.02), (0.1, HALF[1] * 1.02, 0.13)),
                  ((-0.13, 0.04, 1.07), (0.06, 0.055, 0.045)),    # Knobs on top and at the back.
                  ((0.17, 0.085, 1.0), (0.06, 0.06, 0.07))]
    capsules = head_capsules()
    budget = 100
    max_tris = 600
    grip = (0.0, 0.0, 0.3)
    bands = [
        # The strap around the block, slightly tilted, and the one over its right end.
        (Vector((0.0, 0.0, 0.955)), Vector((0.16, 0.0, 1.0)).normalized(), 0.026, lambda c, n: abs(n.z) < 0.75),
        (Vector((0.105, 0.0, 0.93)), Vector((1.0, 0.0, 0.1)).normalized(), 0.022, lambda c, n: abs(n.x) < 0.75),
    ]

    def paint(self, c, n):
        return "blue" if studies.in_band(self, c, n) else "rock"

    def details(self, mb):
        parts.begin(mb, self)
        parts.retone(mb, "rock", 0.55)
        parts.loft(mb, [(0, 0, 0.0), (0, 0, 0.03), (0, 0, 0.068), (0, 0, 0.095)], [0.022, 0.047, 0.043, 0.028], 5,
                   "butt", tones="light", phase=0.4)
        parts.loft(mb, [(0, 0, 0.085), (0.002, 0, 0.45), (0, 0, 0.82)], [0.027, 0.027, 0.029], 5, "wood",
                   tones=0.5, seed=2, twist=0.2)
        parts.wrap(mb, (0, 0, 0.13), (0.001, 0, 0.5), 0.036, 4, "blue", seed=3, sides=5)
        parts.loft(mb, [(0, 0, 0.705), (0, 0, 0.725), (0, 0, 0.745)], [0.035, 0.04, 0.035], 5, "blue", tones=0.4)
        # Blue stones: one where the shaft meets the head, a stud and a side spike.
        parts.loft(mb, [(0.0, -0.1, 0.77), (0.0, -0.125, 0.815), (0.0, -0.12, 0.86)], [0.0, 0.04, 0.0], 5, "blue",
                   tones="light")
        parts.ico(mb, (-0.1, -0.118, 1.005), 0.026, "blue", scale=(1.0, 0.5, 1.2))
        parts.spike(mb, (-0.17, -0.02, 0.84), (-0.235, -0.03, 0.8), 0.03, "blue", ref=(0, 0, 1))


SPECS = [StoneHammer()]
