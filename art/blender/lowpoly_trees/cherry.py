"""Japanese cherries: pink blossom, red and orange in autumn. Four trees:
1 (wide and dense), 2 (open, with separate clumps and a leaning trunk),
weeping (curtains of hanging twigs) and 3 (round and dense)."""

import _tree

BLOOM = [0xFCC0DD, 0xEE88B5, 0xC45E8B]

SPECS = (
    _tree.variants("cherry_1", {"bloom": BLOOM, "autumn": [0xFCAB72, 0xEC5042, 0xBE383B]}, seed=1311, petals=14)
    + _tree.variants("cherry_2", {"bloom": BLOOM, "autumn": [0xF9B764, 0xF17A47, 0xC8452F]}, seed=1512, petals=12,
                     solid=1.0, fill=False, clump=0.78)
    + _tree.variants("cherry_weeping", {"bloom": BLOOM, "autumn": [0xF9B967, 0xEE7A48, 0xCE4537]}, seed=1113,
                     petals=6, hang=1.0, hang_slope=2.0, hang_limb=0.14, prune=6.0, square=0.2, thin=0.036,
                     hang_leaf=(0.4, 0.42), slope=3.0, droop=0.05)
    + _tree.variants("cherry_3", {"bloom": BLOOM, "autumn": [0xFCB861, 0xF0703A, 0xC23A2C]}, seed=1214)
)
