"""Weapon 35: jagged dagger. A slightly bent silver blade with a wavy dark
edge and a row of barbs along its back, a wooden guard, a grip wound with
red cloth and a steel claw for a pommel."""

import common
import studies
import _parts_c as parts

BLADE_Z = (0.245, 0.45)
ROWS = 13


def blade_grid():
    """Rows of (dark edge, ridge, barbed back) from the guard to the tip."""
    z0, z1 = BLADE_Z
    grid = []
    for i in range(ROWS):
        t = i / (ROWS - 1)
        z = z0 + (z1 - z0) * t
        center = 0.012 * (1.0 - (2.0 * t - 0.9) ** 2)       # The blade bows to the right.
        half = 0.03 * (1.0 - t ** 2.4) + 0.001
        if i == ROWS - 1:
            grid.append([(center + 0.006, z)] * 3)
            continue
        wave = 0.005 if i % 4 == 2 else 0.0                  # Notches on the dark edge.
        barb = 0.011 if i % 2 == 1 else -0.004               # Barbs on the back.
        lift = 0.005 if i % 2 == 1 else 0.0                  # Barbs point up.
        grid.append([(center - half + wave, z), (center - half * 0.3, z + 0.003), (center + half + barb, z + lift)])
    return grid


class JaggedDagger(studies.Spec):
    name = "w35_jagged_dagger"
    colors = {
        **parts.shades("steel", 0xD4D0DA, light=0xF0EFF3),
        "edge": common.rgb(0x767D95),
        **parts.shades("red", 0xC82219, shade=0x8E1C16),
        **parts.shades("wood", 0x8C4C34, shade=0x5E2E22),
    }
    max_tris = 600
    grip = (0.0, 0.0, 0.14)

    def details(self, mb):
        parts.begin(mb, self)
        # The claw pommel, hooked to the left.
        parts.loft(mb, [(0.0, 0, 0.07), (-0.004, 0, 0.04), (-0.016, 0, 0.0)], [0.012, (0.014, 0.01), 0.0], 5,
                   "steel", tones="light")
        parts.loft(mb, [(0.0, 0, 0.06), (0.002, 0, 0.15), (0.0, 0, 0.225)], [0.012, 0.013, 0.014], 6, "wood",
                   tones=0.5, seed=3)
        parts.wrap(mb, (0.001, 0, 0.1), (0.0, 0, 0.218), 0.018, 3, "red", seed=4, bulge=0.004)
        # The guard: a wooden block, wider than thick, a little askew.
        parts.loft(mb, [(-0.002, 0, 0.214), (0.0, 0, 0.232), (0.004, 0, 0.252)],
                   [(0.024, 0.014), (0.036, 0.017), (0.03, 0.014)], 4, "wood", tones="light", phase=0.785)
        rows = ROWS - 1
        parts.shell(mb, blade_grid(), (0.0, 0.007, 0.0),
                    ["edge", ["steel_light", "steel"] * rows])


SPECS = [JaggedDagger()]
