"""Builds the `creatures` proposal family: pets, domestic animals, hostile
enemies, fantasy monsters and small ambient critters, all with a skeleton
and clips. The models go to art/studies/propuestas/creatures.

    blender --background --factory-startup --python art/blender/proposals/creatures/build.py -- [ids]

Every module of this folder that does not start with "_" and is not this
script or quad.py (the shared four-legged generator) defines MODELS: a map
from a model id to the function that builds and saves it.
"""

import importlib
import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import _parts as P  # noqa: E402

SKIP = {"build", "quad"}
MODELS = {}
for file in sorted(os.listdir(HERE)):
    name = file[:-3]
    if not file.endswith(".py") or file.startswith("_") or name in SKIP:
        continue
    try:
        MODELS.update(importlib.import_module(name).MODELS)
    except Exception:  # A half-written module must not stop the others.
        traceback.print_exc()
        print("PROPOSAL FAILED module", name)

P.kit.run(MODELS, P.FAMILY)
