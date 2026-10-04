"""Race architecture proposals: a set of buildings for each non-human race,
so that a town of that race looks its own. See ../LEEME.md.

    blender --background --factory-startup --python art/blender/proposals/races/build.py -- [ids]

One module per race (dwarf, elf, dark_elf, orc, cat, fox, lizard, frog), each
with a MODELS table; rparts.py has what they share.
"""

import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import _kit as kit  # noqa: E402
import rparts  # noqa: E402

MODELS = {}
for _race in ("dwarf", "elf", "dark_elf", "orc", "cat", "fox", "lizard", "frog"):
    if os.path.exists(os.path.join(HERE, _race + ".py")):
        MODELS.update(importlib.import_module(_race).MODELS)

kit.run(MODELS, rparts.FAMILY)
