"""Weapon 2: a long sword with a blue blade, a gold cross-guard whose arms
sweep up to a point, a big blue gem, a wrapped grip and a gold pommel."""

import common
import studies

import _parts_a as parts


class BlueSword(studies.Spec):
    name = "w02_blue_sword"
    colors = {
        "blue": common.rgb(0x2259C5),
        "blue_light": common.rgb(0x6A9DF2),
        "blue_pale": common.rgb(0xA8CCFB),
        "gold": common.rgb(0xF6BE3C),
        "gold_shade": common.rgb(0xD9962A),
        "grip": common.rgb(0x6E4028),
    }
    max_tris = 500
    grip = (0.0, 0.0, 0.17)

    def details(self, mb):
        parts.lathe(mb, [(0.0, 0.0), (0.022, 0.032), (0.05, 0.043), (0.076, 0.032)],
                    ["gold_shade", "gold_shade", "gold"], sides=6)
        parts.wrapped(mb, 0.07, 0.272, 0.03, 5, "grip")
        parts.cross_guard(mb, [(0.03, 0.322, 0.03, 0.023), (0.1, 0.328, 0.027, 0.02),
                               (0.138, 0.346, 0.024, 0.014), (0.153, 0.372, 0.0, 0.0)],
                          ("gold_shade", "gold"))
        parts.kite(mb, 0.425, 0.332, 0.248, 0.057, 0.025, 0.015, "gold", "gold_shade")
        parts.gem(mb, (0.0, 0.0, 0.334), 0.034, 0.052, 0.02, ("blue_pale", "blue_light", "blue", "blue"), base=0.025)
        parts.blade(mb, 0.061, 0.36, 0.896, 1.05, 0.013, ("blue", "blue_light", "blue_light", "blue_pale"))


SPECS = [BlueSword()]
