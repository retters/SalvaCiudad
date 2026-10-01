"""Weapon 34: crystal axe. Two crescent blades of light-blue crystal with
deep-blue inner faces around a pointed crystal core, on a wooden shaft with
a stone collar, a blue cord wrap and a faceted stone butt."""

import common
import studies
import _parts_c as parts

HEAD_Z = 0.93
# One blade, right side: rows from the top horn to the bottom horn; each row
# is (cutting edge, the line where the light rim meets the dark face, root),
# as (x, z) from the head's center.
BLADE = [
    [(0.092, 0.22)] * 3,
    [(0.15, 0.188), (0.125, 0.168), (0.112, 0.16)],
    [(0.19, 0.125), (0.155, 0.11), (0.118, 0.1)],
    [(0.212, 0.05), (0.168, 0.045), (0.042, 0.068)],
    [(0.217, -0.02), (0.17, -0.018), (0.036, 0.0)],
    [(0.205, -0.09), (0.16, -0.078), (0.042, -0.068)],
    [(0.18, -0.15), (0.145, -0.125), (0.105, -0.095)],
    [(0.14, -0.205)] * 3,
]
THICK = (0.0, 0.013, 0.02)
RIM = ["ice_light", "ice", "ice_light", "ice", "ice_light", "ice", "ice"]
FACE = ["deep", "deep_shade", "deep", "deep", "deep_shade", "deep", "deep_shade"]


class CrystalAxe(studies.Spec):
    name = "w34_crystal_axe"
    colors = {
        **parts.shades("ice", 0x62C0EC, light=0xA8DAF2),
        **parts.shades("deep", 0x3050B8, shade=0x1E3A90),
        "wood": common.rgb(0x8A4622),
        "wrap": common.rgb(0x2488CC),
        "stone": common.rgb(0xA8A2A0),
    }
    max_tris = 600
    grip = (0.0, 0.0, 0.38)

    def details(self, mb):
        parts.begin(mb, self)
        parts.loft(mb, [(0, 0, 0.0), (0, 0, 0.028), (0, 0, 0.06), (0, 0, 0.085)], [0.02, 0.043, 0.04, 0.027], 6,
                   "stone", tones="light", phase=0.4)
        parts.loft(mb, [(0, 0, 0.075), (0.003, 0, 0.42), (0, 0, 0.8)], [0.026, 0.026, 0.027], 6, "wood",
                   tones=0.5, seed=5, twist=0.2)
        parts.wrap(mb, (0.002, 0, 0.245), (0.003, 0, 0.52), 0.034, 4, "wrap", seed=2)
        parts.loft(mb, [(0, 0, 0.765), (0, 0, 0.785), (0, 0, 0.815)], [0.036, 0.04, 0.037], 6, "stone",
                   tones="light")
        # The crystal core: a prism between the blades that ends in a spike.
        parts.loft(mb, [(0, 0, 0.805), (0, 0, 0.86), (0, 0, 1.01), (0.004, 0, 1.11)], [0.03, 0.04, 0.045, 0.0], 6,
                   "ice", tones="light", phase=0.5)
        for s in (-1, 1):
            grid = [[(s * x, HEAD_Z + z) for x, z in row] for row in BLADE]
            parts.shell(mb, grid, THICK, [RIM, FACE])


SPECS = [CrystalAxe()]
