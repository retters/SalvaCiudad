"""Weapon 38: throwing knives. One model with the three pieces of the
picture side by side: two kunai (a leaf blade, a grip wound with red cord
and a dark ring) and a small barbed knife with a red grip and a steel
pommel. (The picture shows the kunai point down; the model stands them
point up.)"""

import common
import studies
import _parts_c as parts

KUNAI_X = (-0.09, -0.012)
KNIFE_X = 0.085
# The kunai blade: (height, half width) from the neck to the tip.
KUNAI = [(0.092, 0.007), (0.128, 0.029), (0.19, 0.017), (0.25, 0.0)]
# The barbed knife: rows of (notched edge, ridge, barbed edge) as (x, z).
KNIFE = [
    [(-0.012, 0.1), (-0.002, 0.1), (0.012, 0.1)],
    [(-0.03, 0.115), (-0.003, 0.117), (0.03, 0.115)],
    [(-0.03, 0.132), (-0.003, 0.134), (0.043, 0.138)],
    [(-0.023, 0.148), (-0.004, 0.15), (0.027, 0.148)],
    [(-0.033, 0.166), (-0.004, 0.168), (0.045, 0.174)],
    [(-0.033, 0.184), (-0.005, 0.186), (0.029, 0.184)],
    [(-0.026, 0.204), (-0.006, 0.206), (0.044, 0.211)],
    [(-0.037, 0.222), (-0.008, 0.224), (0.028, 0.222)],
    [(-0.04, 0.246), (-0.012, 0.248), (0.034, 0.25)],
    [(-0.014, 0.29)] * 3,
]


class ThrowingKnives(studies.Spec):
    name = "w38_throwing_knives"
    colors = {
        **parts.shades("steel", 0xAEA8B4, 0xE9E5E8, 0x7A7484),
        **parts.shades("red", 0xC4242A, shade=0x7E1E24),
        "dark": common.rgb(0x4A4450),
        "blue": common.rgb(0x4A6CB0),
    }
    max_tris = 600
    grip = (KUNAI_X[1], 0.0, 0.07)

    def details(self, mb):
        parts.begin(mb, self)
        for k, x in enumerate(KUNAI_X):
            parts.ring(mb, (x, 0.0, 0.024), 0.016, 0.008, "dark", count=6, sides=4, phase=0.5236)
            parts.loft(mb, [(x, 0, 0.042), (x, 0, 0.056), (x, 0, 0.07), (x, 0, 0.084), (x, 0, 0.098)],
                       [0.008, 0.0105, 0.008, 0.0105, 0.008], 5, ["red", "red", "blue" if k == 0 else "red", "red"],
                       twist=0.4)
            grid = [[(x - w, z), (x, z + (0.004 if 0 < w else 0.0)), (x + w, z)] for z, w in KUNAI]
            parts.shell(mb, grid, (0.0, 0.007, 0.0), ["steel_light", "steel_shade"])
        x = KNIFE_X
        parts.loft(mb, [(x, 0, 0.0), (x, 0, 0.014), (x, 0, 0.032)], [0.007, 0.021, 0.012], 5, "dark",
                   tones="light")
        parts.wrap(mb, (x, 0, 0.03), (x, 0, 0.106), 0.0125, 3, "red", bulge=0.003, seed=3)
        parts.shell(mb, [[(x + px, z) for px, z in row] for row in KNIFE], (0.0, 0.006, 0.0),
                    ["steel", "steel_light"])


SPECS = [ThrowingKnives()]
