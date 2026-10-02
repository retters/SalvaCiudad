"""Birch: white bark with dark marks (in the three states), light green
leaves in separate clumps; yellow in autumn."""

import _tree

SPECS = _tree.variants(
    "birch", {"bloom": [0xB7DD55, 0x7DB02B, 0x456F17], "autumn": [0xFBCB32, 0xF0A012, 0xD0700A]}, seed=1161,
    hairpins=True, bark=(0xF3EDE0, 0xC4B8A9), marks=10, colors={"mark": 0x4A3A30}, solid=1.0, fill=False, clump=0.9,
    thick=1.7, thin=0.05, square=0.12, show_trunk=True)
