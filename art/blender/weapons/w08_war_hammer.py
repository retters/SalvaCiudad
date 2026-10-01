"""Weapon 8: a war hammer. A big grey block head with cut corners, a wider
middle and two yellow bands, a gold stud on top, a gold collar, a
wrapped brown shaft and a pointed gold pommel."""

import common
import studies

import _parts_a as parts

HEAD_Z = 0.83


class WarHammer(studies.Spec):
    name = "w08_war_hammer"
    colors = {
        "stone": common.rgb(0x857B7E),
        "stone_light": common.rgb(0x9C9296),
        "stone_dark": common.rgb(0x50474F),
        "yellow": common.rgb(0xFBC02A),
        "yellow_shade": common.rgb(0xE09A0C),
        "wood": common.rgb(0x6E3C22),
    }
    max_tris = 500
    grip = (0.0, 0.0, 0.38)

    def details(self, mb):
        parts.lathe(mb, [(0.0, 0.0), (0.088, 0.076), (0.148, 0.045)], ["yellow_shade", "yellow"], sides=6)
        parts.wrapped(mb, 0.14, 0.6, 0.036, 5, "wood")
        parts.lathe(mb, [(0.595, 0.056), (0.652, 0.056), (0.652, 0.046), (0.7, 0.05)],
                    ["yellow", "stone_dark", "stone_dark"], sides=8, phase=22.5)
        # The head, along X: end block, yellow band, wider middle.
        profile = [(-0.29, 0.085), (-0.265, 0.118), (-0.18, 0.118), (-0.18, 0.126), (-0.112, 0.126),
                   (-0.112, 0.138), (0.112, 0.138), (0.112, 0.126), (0.18, 0.126), (0.18, 0.118),
                   (0.265, 0.118), (0.29, 0.085)]
        mats = ["stone", "stone", "yellow", "yellow", "stone", "stone", "stone", "yellow", "yellow", "stone", "stone"]

        def head_mat(i, k):
            # Sides 2 to 4 look up and catch the light; 6, 7 and 0 look down.
            if mats[i] == "yellow":
                return "yellow_shade" if k in (6, 7, 0) else "yellow"
            if i in (0, len(mats) - 1):
                return "stone_light"
            return "stone_light" if k in (2, 3, 4) else "stone_dark" if k in (6, 7, 0) else "stone"
        parts.lathe(mb, profile, head_mat, origin=(0.0, 0.0, HEAD_Z), axis=(1.0, 0.0, 0.0),
                    section=parts.chamfered(0.55))
        parts.lathe(mb, [(HEAD_Z + 0.136, 0.04), (HEAD_Z + 0.158, 0.034)], ["yellow_shade"], sides=6)


SPECS = [WarHammer()]
