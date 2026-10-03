"""Load: a wooden crate carried on the back with two leather straps.

Placement (see _load_kit): the crate lies wholly behind the plane Y = 0
(toward +Y, behind the character) and stands on Z = 0. `grip` =
(0, 0, 0.22) is the point that touches the middle of the character's back.
Size: 0.48 wide (X), 0.34 deep (Y), 0.44 high (Z).
"""

import studies
import _load_kit as kit


class CrateBack(studies.Spec):
    name = "crate_back"
    colors = kit.colors("plank", "leather")
    max_tris = 300
    grip = (0.0, 0.0, 0.22)

    def details(self, mb):
        kit.crate(mb, (0.0, 0.17, 0.014), (0.48, 0.31, 0.41))
        for x in (-0.12, 0.12):
            kit.strap(mb, kit.rect(x, 0.012, 0.328, 0.012, 0.428), (1, 0, 0), 0.05, 0.012, "leather")


SPECS = [CrateBack()]
