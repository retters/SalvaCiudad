"""Weapon 7: a battle axe. Two wide crescent blades (dark steel with a
bright bevelled edge) on a dark socket with collars and a pointed cap, a
wrapped brown shaft and a steel butt that ends in a spike."""

import common
import studies

import _parts_a as parts

P = parts.pixels(0.001075, 310, 1005)  # 4x crop of item 7.

# One blade from the socket outward: each row runs from its top to its
# bottom; the last row is the cutting edge.
BLADE = [
    ([(270, 185), (270, 222), (270, 258), (270, 294), (270, 330)], 0.022),
    ([(205, 172), (201, 215), (199, 258), (201, 300), (210, 348)], 0.019),
    ([(150, 112), (120, 190), (110, 270), (122, 350), (158, 428)], 0.013),
    ([(135, 30), (62, 150), (28, 270), (62, 390), (155, 500)], 0.0),
]


class BattleAxe(studies.Spec):
    name = "w07_battle_axe"
    colors = {
        "steel": common.rgb(0xC4C4D0),
        "steel_light": common.rgb(0xF2F0F4),
        "iron": common.rgb(0x48515F),
        "iron_dark": common.rgb(0x2C2E3A),
        "wood": common.rgb(0x96501F),
        "wood_dark": common.rgb(0x7A421E),
    }
    max_tris = 500
    grip = (0.0, 0.0, 0.36)

    def details(self, mb):
        parts.lathe(mb, [(0.0, 0.0), (0.06, 0.062), (0.125, 0.044)], ["iron_dark", "iron"], sides=6)
        parts.wrapped(mb, 0.12, 0.665, 0.036, 5, lambda i, k: ("wood", "wood_dark")[(i // 2) % 2])
        parts.lathe(mb, [(0.66, 0.058), (0.7, 0.058), (0.7, 0.049), (0.925, 0.049), (0.925, 0.058), (0.957, 0.058),
                         (1.0, 0.016)], ["iron_dark", "iron_dark", "iron", "iron_dark", "iron_dark", "iron"],
                    sides=8, phase=22.5)
        rows = [[(*P(*p), h) for p in pts] for pts, h in BLADE]

        def blade_mat(i, j):
            if i == 2:
                return ("steel_light", "steel")[j % 2]
            return "iron_dark" if i == 1 and j >= 2 else "iron"
        for mirror in (False, True):
            parts.ridged(mb, rows, blade_mat, parts.placer(mirror=mirror))


SPECS = [BattleAxe()]
