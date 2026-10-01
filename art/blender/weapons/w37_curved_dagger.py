"""Weapon 37: curved dagger. A long silver blade that sweeps to one side,
a wooden guard with a small blue stone, a grip wound with green cord under
red and dark bands, and a dark six-sided ring for a pommel. (The picture
shows it point down; the model stands point up.)"""

import common
import studies
import _parts_c as parts

BLADE_Z = (0.212, 0.5)
ROWS = 8
SWEEP = 0.085       # How far the tip ends to the right of the grip.
RING = ((0.0, 0.0, 0.031), 0.021, 0.01)


def blade_grid():
    """Rows of (belly edge, bevel line, spine) from the guard to the tip."""
    z0, z1 = BLADE_Z
    grid = []
    for i in range(ROWS):
        t = i / (ROWS - 1)
        z = z0 + (z1 - z0) * t
        center = SWEEP * t ** 2.2
        half = 0.024 * (1.0 + 0.45 * t) * (1.0 - t ** 2.4)
        if i == ROWS - 1:
            grid.append([(SWEEP, z)] * 3)
            continue
        slope = 2.2 * SWEEP * t ** 1.2 / (z1 - z0)           # The blade leans as it sweeps.
        grid.append([(center - half, z + half * slope), (center - half * 0.45, z + half * 0.45 * slope),
                     (center + half, z - half * slope)])
    return grid


class CurvedDagger(studies.Spec):
    name = "w37_curved_dagger"
    colors = {
        "steel": common.rgb(0xD2CFCC),
        **parts.shades("green", 0x7CC43A, shade=0x3E8A3A),
        "red": common.rgb(0xD4402C),
        "dark": common.rgb(0x4A3A3C),
        "wood": common.rgb(0x7A4638),
        "gem": common.rgb(0x3C9CDC),
    }
    max_tris = 600
    grip = (0.0, 0.0, 0.16)

    def details(self, mb):
        parts.begin(mb, self)
        parts.ring(mb, RING[0], RING[1], RING[2], "dark", count=6, sides=4, phase=0.5236)
        parts.stack(mb, [(0.056, 0.072, 0.0135, 0.0135, "red"), (0.072, 0.1, 0.012, 0.012, "dark"),
                         (0.1, 0.113, 0.0135, 0.0135, "red"), (0.113, 0.18, 0.011, 0.011, "dark")], 6,
                    tones=0.4, seed=2)
        parts.wrap(mb, (0, 0, 0.113), (0, 0, 0.178), 0.0145, 2, "green", seed=5, bulge=0.003)
        # The guard: a wooden wedge, wide at the blade.
        parts.loft(mb, [(0.0, 0, 0.172), (0.0, 0, 0.192), (0.002, 0, 0.22)],
                   [(0.016, 0.012), (0.03, 0.015), (0.038, 0.013)], 4, "wood", tones="light", phase=0.785)
        parts.loft(mb, [(0.0, -0.011, 0.203), (0.0, -0.021, 0.203)], [(0.006, 0.008), 0.0], 4, "gem", ref=(0, 0, 1))
        parts.shell(mb, blade_grid(), (0.0, 0.006, 0.0045),
                    ["steel", "steel"])


SPECS = [CurvedDagger()]
