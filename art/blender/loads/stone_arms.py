"""Load: three grey stones held in the arms.

Placement (see _load_kit): the stones lie wholly in front of the plane
Y = 0 (toward -Y, in front of the character) and stand on Z = 0. `grip` =
(0, 0, 0.14) is the point that touches the middle of the character's
chest; the bottom of the load rests on the forearms.
Size: 0.52 wide (X), 0.31 deep (Y), 0.37 high (Z).
"""

import studies
import _load_kit as kit


class StoneArms(studies.Spec):
    name = "stone_arms"
    colors = kit.colors("stone")
    max_tris = 300
    grip = (0.0, 0.0, kit.ARMS_GRIP_Z)

    def details(self, mb):
        kit.boulder(mb, (-0.11, -0.165, 0.135), (0.15, 0.14, 0.135), "stone", 4, count=16)
        kit.boulder(mb, (0.135, -0.16, 0.115), (0.125, 0.125, 0.115), "stone", 5, count=14)
        kit.boulder(mb, (0.02, -0.135, 0.27), (0.12, 0.11, 0.1), "stone", 6, count=12)


SPECS = [StoneArms()]
