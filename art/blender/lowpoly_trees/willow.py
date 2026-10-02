"""Weeping willow: thick arching limbs and curtains of long pointed leaves
hanging almost to the ground; yellow and orange in autumn; without leaves,
the hanging twigs."""

import _tree

BARK = (0x9A683B, 0x65401F)  # The second set of pictures is lit brighter.

SPECS = _tree.variants(
    "willow", {"bloom": [0xBBD547, 0x8FB02C, 0x5C7C1E], "autumn": [0xF9C63A, 0xEC8C12, 0xCF5C0C]}, seed=762,
    hairpins=True, bark=BARK, curtain={"count": 48, "bottom": (0.7, 1.9), "from": 2.6}, hang=1.0, hang_slope=0.2,
    hang_shape="diamond", hang_leaf=(0.36, 0.74), square=0.2, thin=0.04, prune=6.0)
