"""Weapon 41: short spear. A long silver leaf head on a light-blue socket,
a gold ring and blue bindings on a wooden shaft, and a steel butt spike."""

import common
import studies
import _parts_c as parts

# The head: (height, half width) from its neck to the tip.
HEAD = [(1.035, 0.02), (1.085, 0.088), (1.25, 0.052), (1.5, 0.0)]


class ShortSpear(studies.Spec):
    name = "w41_short_spear"
    colors = {
        **parts.shades("steel", 0xD9DCE4, light=0xF8F7F7),
        **parts.shades("sky", 0x4AA6E0, shade=0x2C7CBC),
        "wood": common.rgb(0x9C542E),
        "iron": common.rgb(0x5E6E82),
        "gold": common.rgb(0xA07C44),
    }
    max_tris = 600
    grip = (0.0, 0.0, 0.62)

    def details(self, mb):
        parts.begin(mb, self)
        # The butt spike, then the shaft with its bindings.
        parts.loft(mb, [(0, 0, 0.0), (0, 0, 0.075), (0, 0, 0.13), (0, 0, 0.15)], [0.0, 0.04, 0.034, 0.03], 5,
                   "iron", tones="light", phase=0.3)
        parts.loft(mb, [(0, 0, 0.14), (0.002, 0, 0.4), (0.003, 0, 0.62), (0, 0, 0.96)],
                   [0.027, 0.028, 0.028, 0.028], 6, "wood", twist=0.2)
        parts.wrap(mb, (0, 0, 0.15), (0.001, 0, 0.25), 0.036, 2, "sky", seed=2)
        parts.wrap(mb, (0, 0, 0.835), (0, 0, 0.935), 0.036, 2, "sky", seed=6)
        parts.loft(mb, [(0, 0, 0.935), (0, 0, 0.95), (0, 0, 0.972)], [0.037, 0.041, 0.036], 6, "gold", tones=0.4)
        # The socket: a light-blue spike that runs up into the blade.
        parts.loft(mb, [(0, 0, 0.965), (0, 0, 1.04), (0, 0, 1.24)], [0.03, 0.034, 0.0], 4, "sky", tones="light",
                   phase=0.0)
        grid = [[(-w, z), (0.0, z + (0.03 if 0 < w else 0.0)), (w, z)] for z, w in HEAD]
        parts.shell(mb, grid, (0.0, 0.016, 0.0), ["steel", "steel_light"])


SPECS = [ShortSpear()]
