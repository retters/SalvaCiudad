"""Acacia: a wide flat umbrella of green on bare spreading limbs; orange
and red in autumn."""

import _tree

BARK = (0x9A683B, 0x65401F)  # The second set of pictures is lit brighter.

SPECS = _tree.variants(
    "acacia", {"bloom": [0xA4C730, 0x6F961D, 0x3F5A10], "autumn": [0xFBB227, 0xF57E1E, 0xCC4410]}, seed=763,
    hairpins=True, bark=BARK, thin=0.04, square=0.09)
