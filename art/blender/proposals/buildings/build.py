"""Elaborate buildings offered as proposals: castles, inns, mills and more.

    blender --background --factory-startup --python art/blender/proposals/buildings/build.py -- [ids]
"""

import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import _kit as kit  # noqa: E402

MODULES = ("castles", "wooden", "inns", "mills", "civic", "trades", "town", "camp", "fantasy", "races", "extra", "works", "culture", "houses", "workshops", "more", "last", "small", "variants")

MODELS = {}
for module in MODULES:
    if os.path.exists(os.path.join(HERE, module + ".py")):
        MODELS.update(importlib.import_module(module).MODELS)

kit.run(MODELS, "buildings")
