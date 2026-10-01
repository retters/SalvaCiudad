"""American elms: green, turning yellow and orange in autumn. Four trees:
1 (open layers), 2 (drooping twigs), 3 (tall and round) and 4 (wide and
flat, in layers)."""

import _tree

BLOOM = [0x90B649, 0x668A38, 0x3F6022]

SPECS = (
    _tree.variants("elm_1", {"bloom": BLOOM, "autumn": [0xECA420, 0xCF7A14, 0x6F7A27]}, seed=231)
    + _tree.variants("elm_2", {"bloom": BLOOM, "autumn": [0xF4A024, 0xDC681A, 0xB4962A]}, seed=832, hang=0.5,
                     hang_leaf=(0.26, 0.3), clump=0.9)
    + _tree.variants("elm_3", {"bloom": BLOOM, "autumn": [0xF38E3C, 0xE26522, 0x5E6418]}, seed=33)
    + _tree.variants("elm_4", {"bloom": BLOOM, "autumn": [0xEDA12D, 0xE0701E, 0x6A6A1C]}, seed=1234)
)
