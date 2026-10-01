"""Weapon 12: a glaive. A big curved silver blade (a dark body with a
bright bevelled edge) held by a neck on a dark socket with a pointed cap,
a gold band, a brown shaft and a dark steel butt. The shaft stands on
X = 0; the blade reaches toward +X."""

import common
import studies

import _parts_a as parts

P = parts.pixels(0.00206, 90, 995)  # 4x crop of item 12.

# The blade from its tip down to its lower point: (back, where the bright
# bevel starts, edge).
BLADE = [
    ((240, 25), (240, 25), (240, 25)),
    ((218, 120), (241, 122), (290, 120)),
    ((188, 200), (256, 200), (302, 200)),
    ((147, 292), (229, 300), (281, 300)),
    ((161, 348), (219, 360), (262, 362)),
    ((150, 400), (207, 420), (241, 422)),
    ((152, 470), (218, 492), (243, 492)),
    ((240, 552), (240, 552), (240, 552)),
]


class Glaive(studies.Spec):
    name = "w12_glaive"
    colors = {
        "steel": common.rgb(0xD2CED6),
        "steel_light": common.rgb(0xE8E4E8),
        "iron": common.rgb(0x69657A),
        "iron_dark": common.rgb(0x443E4A),
        "wood": common.rgb(0x7A4228),
        "gold": common.rgb(0xEDA316),
    }
    max_tris = 500
    grip = (0.0, 0.0, 0.6)

    def details(self, mb):
        parts.lathe(mb, [(0.0, 0.0), (0.06, 0.07), (0.12, 0.072), (0.168, 0.05)],
                    ["iron_dark", "iron_dark", "iron"], sides=6)
        parts.lathe(mb, [(0.16, 0.043), (0.96, 0.043)], ["wood"], sides=6)
        parts.lathe(mb, [(0.955, 0.06), (1.04, 0.06)], ["gold"], sides=6)
        parts.lathe(mb, [(1.04, 0.054), (1.12, 0.054), (1.12, 0.059), (1.235, 0.059), (1.235, 0.054), (1.34, 0.054),
                         (1.34, 0.072), (1.385, 0.072), (1.435, 0.0)],
                    ["iron_dark", "wood", "wood", "wood", "iron_dark", "iron_dark", "iron_dark", "iron"], sides=6)
        # The neck between the socket and the blade.
        (x0, z0), (x1, z1) = P(100, 462), P(160, 404)
        parts.bevel_plate(mb, [(x0, z0), (x1, z0 + 0.025), (x1, z1 - 0.01), (x0, z1)], 0.026, 0.012, "iron_dark",
                          edge=0.014)
        rows = [[(*P(*back), 0.006), (*P(*bevel), 0.016), (*P(*edge), 0.0)] for back, bevel, edge in BLADE]
        for i in (0, -1):
            rows[i] = [(rows[i][0][0], rows[i][0][1], 0.0)] * 3
        parts.ridged(mb, rows, lambda i, j: "iron" if j == 0 else ("steel_light", "steel")[i % 2])


SPECS = [Glaive()]
