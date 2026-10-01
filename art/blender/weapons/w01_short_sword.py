"""Weapon 1: a short sword. A silver blade with one ridge, a gold cross-guard
with a pale blue gem, a wrapped brown grip and a gold pommel with a gem."""

import common
import studies

import _parts_a as parts


class ShortSword(studies.Spec):
    name = "w01_short_sword"
    colors = {
        "steel": common.rgb(0xBDBBC6),
        "steel_light": common.rgb(0xF4F1F2),
        "gold": common.rgb(0xF8B820),
        "gold_shade": common.rgb(0xD98E12),
        "grip": common.rgb(0x7A4424),
        "gem": common.rgb(0x8FB4DC),
    }
    max_tris = 500
    grip = (0.0, 0.0, 0.135)

    def details(self, mb):
        # Pommel: a gold plate that ends in a point, with a small gem.
        parts.bevel_plate(mb, [(0.0, 0.0), (0.034, 0.042), (0.024, 0.066), (-0.024, 0.066), (-0.034, 0.042)],
                          0.017, 0.009, "gold", "gold_shade", edge=0.008)
        parts.gem(mb, (0.0, 0.0, 0.036), 0.015, 0.019, 0.012, ("steel_light", "gem", "gem", "gem"), base=0.017)
        parts.wrapped(mb, 0.06, 0.218, 0.024, 4, "grip")
        parts.cross_guard(mb, [(0.02, 0.24, 0.02, 0.018), (0.078, 0.241, 0.021, 0.016),
                               (0.101, 0.243, 0.031, 0.012), (0.111, 0.243, 0.016, 0.006)],
                          ("gold_shade", "gold"))
        parts.kite(mb, 0.328, 0.25, 0.196, 0.044, 0.021, 0.011, "gold", "gold_shade")
        parts.gem(mb, (0.0, 0.0, 0.25), 0.024, 0.031, 0.016, ("steel_light", "gem", "gem", "gem"), base=0.021)
        parts.blade(mb, 0.046, 0.27, 0.665, 0.75, 0.011, ("steel", "steel_light", "steel_light", "steel"))


SPECS = [ShortSword()]
