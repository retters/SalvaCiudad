"""Load: three big grey boulders carried on the back in a leather harness.

Placement (see _load_kit): the load lies wholly behind the plane Y = 0
(toward +Y, behind the character) and stands on Z = 0. `grip` =
(0, 0, 0.30) is the point that touches the middle of the character's back.
Size: 0.54 wide (X), 0.40 deep (Y), 0.62 high (Z).
"""

import math

import studies
import _load_kit as kit


def hoop(x, cy, cz, ry, rz, sides=8):
    """An upright oval around the stones, on the plane X = x."""
    return [(x, cy + ry * math.cos(i * math.tau / sides + math.pi / sides),
             cz + rz * math.sin(i * math.tau / sides + math.pi / sides)) for i in range(sides)]


class StoneBack(studies.Spec):
    name = "stone_back"
    colors = kit.colors("stone", "leather")
    max_tris = 300
    grip = (0.0, 0.0, 0.30)

    def details(self, mb):
        kit.boulder(mb, (0.0, 0.2, 0.2), (0.25, 0.175, 0.185), "stone", 1, count=18)
        kit.boulder(mb, (-0.07, 0.19, 0.44), (0.19, 0.16, 0.15), "stone", 2, count=16)
        kit.boulder(mb, (0.13, 0.21, 0.4), (0.13, 0.14, 0.13), "stone", 3, count=12)
        # The harness: two upright straps and one around the middle.
        for x, rz in ((-0.1, 0.28), (0.12, 0.255)):
            kit.strap(mb, hoop(x, 0.2, 0.3, 0.17, rz), (1, 0, 0), 0.045, 0.012, "leather")
        kit.strap(mb, kit.ring((0.0, 0.2, 0.27), 0.245, 0.17, 8, math.pi / 8), (0, 0, 1), 0.045, 0.012, "leather")


SPECS = [StoneBack()]
