"""Apple tree: a round green crown with red apples; orange in autumn,
still with its apples."""

import _tree

BARK = (0x9A683B, 0x65401F)  # The second set of pictures is lit brighter.

SPECS = _tree.variants(
    "apple", {"bloom": [0xA7C736, 0x6C9320, 0x3F5E13], "autumn": [0xF7A71E, 0xE8750E, 0xD04A12]}, seed=1373,
    hairpins=True, bark=BARK, accents=("fruit", 22, 0.2, 0xD8341C), thin=0.04, square=0.09)
