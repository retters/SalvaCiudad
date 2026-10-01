"""Guayacans: yellow blossom, yellow to orange in autumn. Four trees:
1 and 2 (wide domes), 3 (open, separate clumps on bare branches) and 4 (a
wide, low umbrella)."""

import _tree

BLOOM = [0xFCDD25, 0xF2BD08, 0xD39C07]

SPECS = (
    _tree.variants("guayacan_1", {"bloom": BLOOM, "autumn": [0xFBC416, 0xF5990A, 0xDD6E06]}, seed=241)
    + _tree.variants("guayacan_2", {"bloom": BLOOM, "autumn": [0xFCAB2E, 0xF78B1B, 0xDE5C0E]}, seed=942)
    + _tree.variants("guayacan_3", {"bloom": BLOOM, "autumn": [0xFABF1A, 0xF49F0F, 0xDC760D]}, seed=643, solid=1.0,
                     fill=False)
    + _tree.variants("guayacan_4", {"bloom": BLOOM, "autumn": [0xFBBD13, 0xF4920E, 0xE2601A]}, seed=1144)
)
