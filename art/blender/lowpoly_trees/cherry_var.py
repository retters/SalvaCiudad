"""Cherry (variant): a wide crown of pink blossom on spreading limbs; red
and salmon in autumn."""

import _tree

BARK = (0x9A683B, 0x65401F)  # The second set of pictures is lit brighter.

SPECS = _tree.variants(
    "cherry_var", {"bloom": [0xFBB8D0, 0xF07FA8, 0xC0507C], "autumn": [0xFBA475, 0xF0603F, 0xBE2C2A]}, seed=1069,
    hairpins=True, bark=BARK, thin=0.04, square=0.09)
