"""Load: a stuffed cloth sack carried on the back, tied at the top with a
rope and held by a leather belt.

Placement (see _load_kit): the sack lies wholly behind the plane Y = 0
(toward +Y, behind the character) and stands on Z = 0. `grip` =
(0, 0, 0.30) is the point that touches the middle of the character's back.
Size: 0.46 wide (X), 0.36 deep (Y), 0.62 high (Z).
"""

import math

import studies
import _load_kit as kit

CENTER = (0.0, 0.18, 0.0)
SQUASH = 0.75


class SackBack(studies.Spec):
    name = "sack_back"
    colors = kit.colors("cloth", "rope", "leather")
    max_tris = 300
    grip = (0.0, 0.0, 0.30)

    def details(self, mb):
        kit.lathe(mb, CENTER, [(0.11, 0.0, "cloth_shade"), (0.19, 0.06, "cloth"), (0.22, 0.2, "cloth"),
                               (0.2, 0.34, "cloth_shade"), (0.12, 0.45, "cloth"), (0.055, 0.5, "rope"),
                               (0.055, 0.53, "cloth"), (0.1, 0.62, "cloth_shade")], 7, squash=SQUASH)
        # A lump of what is inside.
        kit.boulder(mb, (0.1, 0.24, 0.27), (0.11, 0.1, 0.1), "cloth", 5, count=10)
        kit.strap(mb, kit.ring((0.0, 0.18, 0.2), 0.222, 0.222 * SQUASH, 7, math.pi / 7), (0, 0, 1), 0.05, 0.012,
                  "leather")


SPECS = [SackBack()]
