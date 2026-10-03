"""Builds every SalvaCiudad model.

    blender --background --factory-startup --python art/blender/build_all.py -- data/mods/core/models [only]

`only` limits the build to one group: characters, props, trees, buildings
or animals. After
"trees", tree names limit it further (for example: trees cherry_1 pine).
"""

import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import buildings  # noqa: E402
import human  # noqa: E402
import props  # noqa: E402
import studies  # noqa: E402

# The wild animals of the game (phase 47), in the order of sim::CreatureKind:
# the low-poly zoo specs of art/blender/zoo, with their skeleton and clips.
GAME_ANIMALS = ("deer", "boar", "wolf", "bear")


# The trees (phase 53): every spec of art/blender/lowpoly_trees, one model
# per state, each with its far version. An evergreen looks the same all
# year, so only its "bloom" is built.
EVERGREEN = ("pine", "cypress", "palm", "laurel", "dragon_tree")


def make_trees(folder, only=None):
    """`only`: names of trees ("cherry_1", "pine"), to build just those."""
    sys.path.insert(0, os.path.join(HERE, "lowpoly_trees"))
    for file in sorted(os.listdir(os.path.join(HERE, "lowpoly_trees"))):
        if not file.endswith(".py") or file.startswith("_"):
            continue
        for spec in importlib.import_module(file[:-3]).SPECS:
            tree, state = spec.name.rsplit("_", 1)
            if only and tree not in only:
                continue
            if tree in EVERGREEN and state != "bloom":
                continue
            studies.build_final(spec, folder)


def make_animals(folder):
    sys.path.insert(0, os.path.join(HERE, "zoo"))
    for name in GAME_ANIMALS:
        for spec in importlib.import_module(name).SPECS:
            studies.build_final(spec, folder)


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = os.path.abspath(args[0] if args else "data/mods/core/models")
    only = args[1] if len(args) > 1 else None
    if only in (None, "characters"):
        human.make_all(os.path.join(out, "characters"))
    if only in (None, "props"):
        props.make_all(os.path.join(out, "props"))
    if only in (None, "trees"):
        make_trees(os.path.join(out, "trees"), args[2:] if only == "trees" else None)
    if only in (None, "buildings"):
        buildings.make_all(os.path.join(out, "buildings"))
    if only in (None, "animals"):
        make_animals(os.path.join(out, "animals"))
    print("SalvaCiudad models written to", out)


main()
