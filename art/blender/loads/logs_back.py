"""Load: a bundle of six short logs carried on the back, tied with two
leather straps.

Placement (see _load_kit): the bundle lies wholly behind the plane Y = 0
(toward +Y, behind the character), stands on Z = 0 and the logs lie along
X. `grip` = (0, 0, 0.24) is the point that touches the middle of the
character's back. Size: 0.72 wide (X), 0.34 deep (Y), 0.48 high (Z).
"""

import studies
import _load_kit as kit

# The logs: (y, z, radius, shift along X, length).
LOGS = [(0.095, 0.085, 0.072, 0.00, 0.70), (0.245, 0.09, 0.076, 0.01, 0.66),
        (0.09, 0.235, 0.074, -0.01, 0.68), (0.24, 0.24, 0.07, 0.01, 0.72),
        (0.10, 0.385, 0.07, 0.01, 0.66), (0.245, 0.385, 0.074, -0.01, 0.70)]


class LogsBack(studies.Spec):
    name = "logs_back"
    colors = kit.colors("bark", "wood_end", "leather")
    max_tris = 300
    grip = (0.0, 0.0, 0.24)

    def details(self, mb):
        for i, (y, z, r, dx, length) in enumerate(LOGS):
            kit.log(mb, (dx - length / 2, y, z), (dx + length / 2, y, z), r, bark="bark" if i % 3 else "bark_shade")
        for x in (-0.2, 0.2):
            kit.strap(mb, kit.rect(x, 0.012, 0.328, 0.012, 0.468, cut=0.045), (1, 0, 0), 0.05, 0.012, "leather")


SPECS = [LogsBack()]
