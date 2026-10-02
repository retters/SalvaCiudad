"""Dragon tree: a stout trunk whose branches end in spiky rosettes of sword
leaves, forming an umbrella; orange and yellow in autumn."""

import _tree

BARK = (0x9A683B, 0x65401F)  # The second set of pictures is lit brighter.

SPECS = _tree.variants(
    "dragon_tree", {"bloom": [0x9EC143, 0x5F8A2A, 0x2C4A15], "autumn": [0xF5B52A, 0xEC8418, 0xC74C13]}, seed=1271,
    hairpins=True, bark=BARK, foliage="rosettes", rosette=(30, 1.6, 0.16, 1.3), canopy_from=3.0, thin=0.04,
    square=0.09)
