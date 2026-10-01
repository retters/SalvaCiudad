"""Jacarandas: purple blossom, purple mixed with yellow and orange in
autumn. Four trees: 1 (wide dome), 2 (wide, with a lower skirt), 3 (round)
and 4 (a flat umbrella on bare spreading branches)."""

import _tree

BLOOM = [0xB283F6, 0x8560D8, 0x5B41AC]

SPECS = (
    _tree.variants("jacaranda_1", {"bloom": BLOOM, "autumn": [0xF7B757, 0xDD8236, 0x9167A6]}, seed=1221, petals=14)
    + _tree.variants("jacaranda_2", {"bloom": BLOOM, "autumn": [0xF5B048, 0xD17529, 0x9167A6]}, seed=1122)
    + _tree.variants("jacaranda_3", {"bloom": BLOOM, "autumn": [0xF4B757, 0xD48025, 0x9167A6]}, seed=223)
    + _tree.variants("jacaranda_4", {"bloom": BLOOM, "autumn": [0xF7B756, 0xD87E33, 0x9167A6]}, seed=124)
)
