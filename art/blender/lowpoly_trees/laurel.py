"""Laurel tree: several trunks, dark green leaves and bunches of
cream-white flowers; ochre and olive in autumn, still with its flowers."""

import _tree

BARK = (0x9A683B, 0x65401F)  # The second set of pictures is lit brighter.

SPECS = _tree.variants(
    "laurel", {"bloom": [0x86AE36, 0x55812A, 0x2E4F14], "autumn": [0xE2A62A, 0xB98A1A, 0x7C7A24]}, seed=768,
    hairpins=True, bark=BARK, accents=("flower", 40, 0.24, 0xF1ECCB), thin=0.04, square=0.09)
