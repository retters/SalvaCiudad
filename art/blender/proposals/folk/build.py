"""Builds the `folk` proposal family: townspeople by trade, fighters, race
variants and riders on mounts, all with a skeleton and clips. The models go
to art/studies/propuestas/folk.

    blender --background --factory-startup --python art/blender/proposals/folk/build.py -- [ids]

Every module of this folder that does not start with "_" and is not this
script defines MODELS: a map from a model id to the function that builds
and saves it.
"""

import importlib
import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import _folk as F  # noqa: E402

MODELS = {}
for file in sorted(os.listdir(HERE)):
    name = file[:-3]
    if not file.endswith(".py") or file.startswith("_") or name == "build":
        continue
    try:
        MODELS.update(importlib.import_module(name).MODELS)
    except Exception:  # A half-written module must not stop the others.
        traceback.print_exc()
        print("PROPOSAL FAILED module", name)

F.kit.run(MODELS, F.FAMILY)
