"""Example of a weapon built only from direct pieces (not listed: the
name starts with "_"). Copy the idea, not the shape."""

import common
import studies


class ExampleDagger(studies.Spec):
    name = "example_dagger"
    colors = {"steel": common.rgb(0xC8CCD4), "grip": common.rgb(0x6B4226), "gold": common.rgb(0xE0A82E)}
    max_tris = 400
    grip = (0.0, 0.0, 0.06)  # Where a hand holds it (for the game, later).

    def details(self, mb):
        mb.cylinder((0, 0, 0.0), (0, 0, 0.12), 0.014, 0.014, "grip", segments=6)
        mb.box((0, 0, 0.125), (0.08, 0.02, 0.012), "gold")
        # A flat blade: a diamond cross-section tapering to the tip.
        studies.plate(mb, [(-0.02, 0, 0.13), (0.02, 0, 0.13), (0.02, 0, 0.3), (0, 0, 0.36), (-0.02, 0, 0.3)],
                      0.008, "steel")


SPECS = [ExampleDagger()]
