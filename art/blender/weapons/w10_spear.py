"""Weapon 10: a spear. A wide silver leaf head with a blue crystal set in
its base, a brown shaft with red wraps at both ends and a gold butt."""

import common
import studies

import _parts_a as parts


class Spear(studies.Spec):
    name = "w10_spear"
    colors = {
        "steel": common.rgb(0xDBD7DB),
        "steel_shade": common.rgb(0x8C8DA0),
        "crystal": common.rgb(0x3AA8E2),
        "red": common.rgb(0xC81A1C),
        "wood": common.rgb(0x6E3C22),
        "gold": common.rgb(0xD8A018),
    }
    max_tris = 500
    grip = (0.0, 0.0, 0.85)

    def details(self, mb):
        parts.lathe(mb, [(0.0, 0.0), (0.075, 0.046), (0.132, 0.034)], ["gold", "wood"], sides=6)
        parts.wrapped(mb, 0.128, 0.353, 0.05, 3, "red")
        parts.lathe(mb, [(0.35, 0.034), (0.984, 0.034)], ["wood"], sides=6)
        parts.wrapped(mb, 0.98, 1.21, 0.05, 3, "red")
        head = [[(-0.045, 1.2, 0.02), (0.0, 1.2, 0.036), (0.045, 1.2, 0.02)],
                [(-0.145, 1.384, 0.0), (0.0, 1.384, 0.044), (0.145, 1.384, 0.0)],
                [(0.0, 1.9, 0.0)] * 3]
        parts.ridged(mb, head, lambda i, j: ("steel_shade", "steel")[j])
        # The crystal: a kite that rises out of the lower half of the head.
        crystal = [[(0.0, 1.19, 0.04)] * 3,
                   [(-0.06, 1.335, 0.036), (0.0, 1.325, 0.068), (0.06, 1.335, 0.036)],
                   [(0.0, 1.5, 0.03)] * 3]
        parts.ridged(mb, crystal, "crystal")


SPECS = [Spear()]
