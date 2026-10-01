"""Weapon 3: a broad sword. A wide silver blade with a flat darker band
down the middle, a dark cross-guard with a red gem, a wrapped grip and a
dark pommel with a red gem."""

import common
import studies

import _parts_a as parts


class BroadSword(studies.Spec):
    name = "w03_broad_sword"
    colors = {
        "steel": common.rgb(0xC6C2CE),
        "steel_light": common.rgb(0xEEEAEC),
        "steel_shade": common.rgb(0x9698AA),
        "iron": common.rgb(0x574A52),
        "red": common.rgb(0xE01A1C),
        "grip": common.rgb(0x6E3E24),
    }
    max_tris = 500
    grip = (0.0, 0.0, 0.165)

    def details(self, mb):
        parts.bevel_plate(mb, [(0.0, 0.0), (0.04, 0.046), (0.026, 0.08), (-0.026, 0.08), (-0.04, 0.046)],
                          0.019, 0.011, "iron", edge=0.009)
        parts.gem(mb, (0.0, 0.0, 0.042), 0.02, 0.025, 0.012, "red", base=0.019)
        parts.wrapped(mb, 0.074, 0.255, 0.028, 4, "grip")
        parts.cross_guard(mb, [(0.03, 0.298, 0.029, 0.023), (0.105, 0.304, 0.026, 0.02),
                               (0.146, 0.318, 0.02, 0.012), (0.16, 0.34, 0.0, 0.0)], ("iron", "iron"))
        parts.kite(mb, 0.386, 0.303, 0.218, 0.066, 0.025, 0.017, "iron")
        parts.gem(mb, (0.0, 0.0, 0.303), 0.04, 0.048, 0.02, "red", base=0.025)
        parts.blade(mb, 0.073, 0.33, 0.925, 1.05, 0.013,
                    ("steel", "steel_light", "steel_light", "steel", "steel_shade"), ridge=0.027)


SPECS = [BroadSword()]
