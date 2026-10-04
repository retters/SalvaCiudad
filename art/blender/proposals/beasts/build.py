"""Builds the `beasts` proposal family: great fantasy beasts and bosses, sea
creatures and the pets and working animals the `creatures` family did not
get to, all with a skeleton and clips. The models go to
art/studies/propuestas/beasts.

    blender --background --factory-startup --python art/blender/proposals/beasts/build.py -- [ids]

Every module of this folder named b_*.py defines MODELS: a map from a model
id to the function that builds and saves it. _bq.py holds the shared pieces
and borrows the rigid-piece helpers of the `creatures` family (read-only).
"""

import importlib
import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import _bq as B  # noqa: E402

MODELS = {}
for file in sorted(os.listdir(HERE)):
    name = file[:-3]
    if not file.endswith(".py") or not file.startswith("b_"):
        continue
    try:
        MODELS.update(importlib.import_module(name).MODELS)
    except Exception:  # A half-written module must not stop the others.
        traceback.print_exc()
        print("PROPOSAL FAILED module", name)

B.P.kit.run(MODELS, B.FAMILY)
