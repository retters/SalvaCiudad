"""Weapon 4: a scimitar. A wide curved silver blade with a darker bevel
along its back, a gold collar, a curved wrapped grip and a gold end cap."""

import common
import studies

import _parts_a as parts

# Points measured on the reference picture (4x crop of item 4).
P = parts.pixels(0.00099, 180, 939)

# The blade from the tip down: (back, ridge, edge).
BLADE = [
    ((190, 42), (190, 42), (190, 42)),
    ((170, 125), (186, 135), (232, 122)),
    ((152, 205), (190, 215), (268, 200)),
    ((141, 330), (207, 330), (291, 300)),
    ((136, 450), (206, 440), (287, 410)),
    ((124, 565), (180, 555), (255, 525)),
    ((106, 650), (152, 645), (212, 625)),
    ((98, 692), (130, 705), (166, 716)),
]
GRIP = [(119, 728), (104, 785), (101, 838), (112, 880), (128, 908)]


class Scimitar(studies.Spec):
    name = "w04_scimitar"
    colors = {
        "steel": common.rgb(0xD6D2D9),
        "steel_light": common.rgb(0xE6E3E9),
        "steel_shade": common.rgb(0x82839A),
        "gold": common.rgb(0xF2AC1C),
        "gold_shade": common.rgb(0xD08A0E),
        "grip": common.rgb(0x7A4528),
    }
    max_tris = 500
    grip = (-0.077, 0.0, 0.126)

    def details(self, mb):
        rows = []
        for back, ridge, edge in BLADE:
            rows.append([(*P(*back), 0.005), (*P(*ridge), 0.012), (*P(*edge), 0.0)])
        rows[0] = [(*P(*BLADE[0][0]), 0.0)] * 3
        parts.ridged(mb, rows, lambda i, j: "steel_shade" if j == 0 else ("steel_light", "steel")[i % 2])
        # The collar, set square to the base of the blade.
        cx, cz = P(124, 716)
        parts.lathe(mb, [(-0.014, 1.0), (0.014, 1.0)], ["gold"], origin=(cx, 0.0, cz), axis=(0.38, 0.0, 0.925),
                    section=[(0.064, 0.024), (-0.064, 0.024), (-0.064, -0.024), (0.064, -0.024)])
        path = [(x, 0.0, z) for x, z in (P(*p) for p in GRIP)]
        parts.tube(mb, path, [0.024, 0.027, 0.023, 0.027, 0.024], "grip", sides=6)
        ex, ez = P(122, 897)
        parts.lathe(mb, [(0.0, 1.0), (0.03, 1.0)], ["gold_shade"], origin=(ex, 0.0, ez), axis=(0.5, 0.0, -0.866),
                    section=[(0.031, 0.023), (-0.031, 0.023), (-0.031, -0.023), (0.031, -0.023)])


SPECS = [Scimitar()]
