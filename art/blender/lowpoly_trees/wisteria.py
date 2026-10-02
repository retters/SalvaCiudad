"""Wisteria: a canopy of purple flowers whose clusters hang in curtains,
with some green leaves among them; red, orange and yellow in autumn;
without leaves, the hanging twigs."""

import _tree

BARK = (0x9A683B, 0x65401F)  # The second set of pictures is lit brighter.

SPECS = _tree.variants(
    "wisteria", {"bloom": [0xC592EC, 0x9A66D6, 0x764CB8], "autumn": [0xFAB72E, 0xF07A18, 0xD03C14]}, seed=66,
    hairpins=True, bark=BARK, curtain={"count": 36, "bottom": (1.2, 3.0), "from": 2.8, "inner": 0.45}, hang=0.55,
    hang_slope=2.0, hang_shape="diamond", hang_leaf=(0.42, 0.46), hang_taper=0.55, hang_limb=0.12,
    sprinkle=(0x93A843, 0.08), square=0.2, thin=0.04, prune=6.0, core=0.72, leaf=0.4, clump=0.85)
