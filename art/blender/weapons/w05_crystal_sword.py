"""Weapon 5: a crystal sword. A light blue crystal blade, a dark steel
cross-guard with a blue gem, a dark banded grip and a blue crystal pommel."""

import common
import studies

import _parts_a as parts


class CrystalSword(studies.Spec):
    name = "w05_crystal_sword"
    colors = {
        "crystal": common.rgb(0x0A98DC),
        "crystal_light": common.rgb(0x62D6FC),
        "crystal_pale": common.rgb(0xC8F2FA),
        "iron": common.rgb(0x3A3B4A),
        "iron_light": common.rgb(0x6A6A7C),
        "wrap": common.rgb(0x2C4E78),
    }
    max_tris = 500
    grip = (0.0, 0.0, 0.15)

    def details(self, mb):
        parts.lathe(mb, [(0.0, 0.0), (0.046, 0.042), (0.073, 0.024)], ["crystal", "crystal_light"], sides=6)
        parts.wrapped(mb, 0.068, 0.235, 0.027, 4, lambda i, k: "wrap" if i % 4 in (1, 2) else "iron")
        parts.cross_guard(mb, [(0.03, 0.303, 0.028, 0.023), (0.108, 0.31, 0.025, 0.02),
                               (0.148, 0.326, 0.019, 0.012), (0.162, 0.348, 0.0, 0.0)],
                          ("iron", "iron_light"))
        parts.kite(mb, 0.37, 0.3, 0.215, 0.061, 0.025, 0.017, "iron", "iron_light")
        parts.gem(mb, (0.0, 0.0, 0.3), 0.034, 0.042, 0.02,
                  ("crystal_pale", "crystal_light", "crystal", "crystal"), base=0.025)
        parts.blade(mb, 0.058, 0.32, 0.927, 1.05, 0.013,
                    ("crystal", "crystal_light", "crystal_light", "crystal_pale"))


SPECS = [CrystalSword()]
