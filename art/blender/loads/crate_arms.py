"""Load: a small wooden crate held in the arms.

Placement (see _load_kit): the crate lies wholly in front of the plane
Y = 0 (toward -Y, in front of the character) and stands on Z = 0. `grip` =
(0, 0, 0.14) is the point that touches the middle of the character's
chest; the bottom of the crate rests on the hands.
Size: 0.44 wide (X), 0.30 deep (Y), 0.29 high (Z).
"""

import studies
import _load_kit as kit


class CrateArms(studies.Spec):
    name = "crate_arms"
    colors = kit.colors("plank")
    max_tris = 300
    grip = (0.0, 0.0, kit.ARMS_GRIP_Z)

    def details(self, mb):
        kit.crate(mb, (0.0, -0.155, 0.0), (0.44, 0.29, 0.28), band=0.04)
        # The planks of the lid.
        for x in (-0.14, 0.0, 0.14):
            mb.box((x, -0.155, 0.283), (0.12, 0.27, 0.012), "plank" if x else "plank_dark")


SPECS = [CrateArms()]
