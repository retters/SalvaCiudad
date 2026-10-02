"""Yellow oak: a round crown of bright yellow leaves in separate clumps;
orange in autumn."""

import _tree

BARK = (0x9A683B, 0x65401F)  # The second set of pictures is lit brighter.

SPECS = _tree.variants(
    "yellow_oak", {"bloom": [0xF8DC1C, 0xE5BF0A, 0xB89A06], "autumn": [0xFACA20, 0xF09408, 0xD06606]}, seed=367,
    hairpins=True, bark=BARK, thin=0.04, square=0.09)
