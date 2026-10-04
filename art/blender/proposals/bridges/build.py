"""Proposal models of the `bridges` family: bridges, a modular bridge kit,
docks and boats.

    blender --background --factory-startup --python art/blender/proposals/bridges/build.py -- [ids]
"""

import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import _kit as kit  # noqa: E402
import parts  # noqa: E402

# bridges, modkit, docks and boats hold the list that was asked for; the
# numbered modules are later batches of ideas, in the order they were made.
MODULES = ("bridges", "modkit", "docks", "boats", "extras", "extras2", "extras3", "extras4", "extras5", "extras6",
           "extras7", "extras8")
MODELS = {}
for module in MODULES:
    MODELS.update(importlib.import_module(module).MODELS)

kit.run(MODELS, parts.FAMILY)
