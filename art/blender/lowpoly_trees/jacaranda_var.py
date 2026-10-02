"""Jacaranda (variant): a wide crown of purple blossom that hangs at the
sides; purple, pink and orange in autumn."""

import _tree

BARK = (0x9A683B, 0x65401F)  # The second set of pictures is lit brighter.

SPECS = _tree.variants(
    "jacaranda_var", {"bloom": [0xB387EC, 0x8259D6, 0x57359F], "autumn": [0xF5853E, 0xD37097, 0x8C4583]}, seed=1472,
    hairpins=True, bark=BARK, thin=0.04, square=0.09)
