"""Magnolia: big pink cup-shaped flowers at the ends of the twigs and few
leaves, on an open spreading tree; in autumn, bunches of red and orange
leaves in their place."""

import _tree

BARK = (0x9A683B, 0x65401F)  # The second set of pictures is lit brighter.

SPECS = _tree.variants(
    "magnolia", {"bloom": [0xF9BADA, 0xEE86BC, 0xC4508E], "autumn": [0xF9A45C, 0xEF5627, 0xCF301A]}, seed=64,
    hairpins=True, bark=BARK, foliage="flowers", flower=(0.72, 0.46), greens=16, thin=0.04, square=0.09,
    colors={"leaf_4": 0x5E9A3A})
