"""Load: four logs held across in the arms.

Placement (see _load_kit): the logs lie wholly in front of the plane
Y = 0 (toward -Y, in front of the character), stand on Z = 0 and lie
along X. `grip` = (0, 0, 0.14) is the point that touches the middle of the
character's chest; the bottom of the load rests on the forearms.
Size: 0.84 wide (X), 0.30 deep (Y), 0.27 high (Z).
"""

import studies
import _load_kit as kit

# The logs: (y, z, radius, shift along X, length, how much farther forward
# its +X end is than its -X end).
LOGS = [(-0.085, 0.068, 0.068, -0.02, 0.78, 0.0), (-0.225, 0.066, 0.066, 0.02, 0.8, 0.03),
        (-0.09, 0.198, 0.062, 0.03, 0.74, -0.03), (-0.215, 0.2, 0.066, -0.02, 0.76, 0.02)]


class LogsArms(studies.Spec):
    name = "logs_arms"
    colors = kit.colors("bark", "wood_end")
    max_tris = 300
    grip = (0.0, 0.0, kit.ARMS_GRIP_Z)

    def details(self, mb):
        for i, (y, z, r, dx, length, skew) in enumerate(LOGS):
            kit.log(mb, (dx - length / 2, y + skew / 2, z), (dx + length / 2, y - skew / 2, z), r,
                    bark="bark" if i % 2 else "bark_shade")


SPECS = [LogsArms()]
