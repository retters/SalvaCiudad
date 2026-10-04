"""Wonders and monuments: the big late works a town builds in stages, and
the smaller prestige pieces. See ../LEEME.md and parts.py.

    blender --background --factory-startup --python art/blender/proposals/wonders/build.py -- [ids]
"""

import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import _kit as kit  # noqa: E402
import parts  # noqa: E402

MODELS = {}
for _module in ("civic", "civic2", "civic3", "races", "arcane", "monuments"):
    if os.path.isfile(os.path.join(HERE, _module + ".py")):
        MODELS.update(importlib.import_module(_module).MODELS)

kit.run(MODELS, parts.FAMILY)
