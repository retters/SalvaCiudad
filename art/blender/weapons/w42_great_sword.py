"""Weapon 42: great sword. A very long blade, blue on one half and silver
on the other, with a blue inlay under a gold point, a gold winged guard
with a blue stone, a dark banded grip and a gold pommel. The small dagger
that floats beside it in the picture (steel point, wooden grip, gold band,
blue crystal foot) is included at its upper left, as drawn."""

import common
import studies
import _parts_c as parts

# The blade: (height, half width) from the guard to under the gold point.
BLADE = [(0.43, 0.058), (0.5, 0.073), (0.56, 0.066), (1.225, 0.066), (1.3, 0.04), (1.42, 0.0)]
POINT = [(1.19, 0.0), (1.285, 0.032), (1.345, 0.056), (1.5, 0.0)]     # The gold point over the blade's end.
INLAY = [(0.93, 0.0), (1.12, 0.019), (1.275, 0.013)]                  # The blue inlay under it.
BASE = [(0.44, 0.02), (0.5, 0.017), (0.6, 0.0)]                       # The blue wedge at the blade's foot.
DAGGER_X = -0.15


def spine(rows, bump=0.0):
    """Grid rows (left edge, ridge, right edge) from (height, half width)."""
    return [[(-w, z), (0.0, z + (bump if w > 0 else 0.0)), (w, z)] for z, w in rows]


class GreatSword(studies.Spec):
    name = "w42_great_sword"
    colors = {
        "steel": common.rgb(0xE4E6EE),      # The silver half of the blade and the dagger's point.
        "blade": common.rgb(0x8AA6D4),      # The blue half.
        "blue": common.rgb(0x2362C2),
        **parts.shades("gold", 0xEDB947, shade=0xC08E36),
        "grip": common.rgb(0x372E34),
        "wood": common.rgb(0x7E5636),       # The grip's bands and the dagger's grip.
    }
    max_tris = 600
    grip = (0.0, 0.0, 0.2)

    def details(self, mb):
        parts.begin(mb, self)
        # Pommel: a flattened gold diamond. Grip: dark, with two brown bands.
        parts.loft(mb, [(0, 0, 0.0), (0, 0, 0.05), (0, 0, 0.1)], [0.0, (0.055, 0.032), (0.022, 0.02)], 4, "gold",
                   tones="light")
        parts.stack(mb, [(0.09, 0.15, 0.027, 0.028, "grip"), (0.15, 0.175, 0.031, 0.031, "wood"),
                         (0.175, 0.24, 0.028, 0.028, "grip"), (0.24, 0.265, 0.031, 0.031, "wood"),
                         (0.265, 0.32, 0.028, 0.027, "grip")], 6)
        # Guard: a diamond boss with a blue stone, and two wings that curl up.
        parts.loft(mb, [(0, 0, 0.285), (0, 0, 0.375), (0, 0, 0.47)], [0.0, (0.076, 0.034), 0.0], 4, "gold",
                   tones="light")
        parts.loft(mb, [(0, -0.047, 0.375), (0, -0.03, 0.375), (0, 0.03, 0.375), (0, 0.047, 0.375)],
                   [0.0, (0.036, 0.052), (0.036, 0.052), 0.0], 4, "blue", tones="light", ref=(0, 0, 1))
        for s in (-1, 1):
            parts.loft(mb, [(s * 0.035, 0, 0.365), (s * 0.105, 0, 0.366), (s * 0.15, 0, 0.395), (s * 0.178, 0, 0.465)],
                       [(0.04, 0.026), (0.036, 0.024), (0.028, 0.02), 0.0], 4, "gold", tones="light")
        # The blade and what lies on it.
        parts.shell(mb, spine(BLADE), (0.0, 0.016, 0.0),
                    ["blade", "steel"])
        parts.shell(mb, spine(INLAY), (0.016, 0.021, 0.016), ["blue", "blue"])
        parts.shell(mb, spine(BASE), (0.017, 0.021, 0.017), ["blue", "blue"])
        parts.shell(mb, spine(POINT), (0.014, 0.027, 0.014), ["gold", "gold_shade"])
        # The companion dagger.
        x = DAGGER_X
        parts.loft(mb, [(x, 0, 0.87), (x, 0, 0.955), (x, 0, 0.985)], [0.0, 0.016, 0.014], 4, "blue", tones="light")
        parts.stack(mb, [(0.98, 1.012, 0.024, 0.024, "gold"), (1.012, 1.29, 0.021, 0.019, "wood")], 6, at=(x, 0),
                    tones=0.5, seed=7)
        parts.loft(mb, [(x, 0, 1.285), (x, 0, 1.31), (x, 0, 1.47)], [(0.016, 0.01), (0.018, 0.009), 0.0], 4,
                   "steel", tones="light")


SPECS = [GreatSword()]
