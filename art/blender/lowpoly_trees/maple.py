"""Maple: a round dense crown of red and orange leaves (also in "bloom":
it is a red maple); deeper reds in autumn."""

import _tree

BARK = (0x9A683B, 0x65401F)  # The second set of pictures is lit brighter.

SPECS = _tree.variants(
    "maple", {"bloom": [0xFA8B2E, 0xE9481F, 0xB52C16], "autumn": [0xFBAB20, 0xEC4214, 0xA8200B]}, seed=765,
    hairpins=True, bark=BARK, thin=0.04, square=0.09)
