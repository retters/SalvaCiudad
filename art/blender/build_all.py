"""Builds every SalvaCiudad model.

    blender --background --factory-startup --python art/blender/build_all.py -- data/mods/core/models [only]

`only` limits the build to one group: characters, props, trees, buildings
or animals. After
"trees", species ids limit it further (for example: trees oak elm).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import animals  # noqa: E402
import buildings  # noqa: E402
import human  # noqa: E402
import props  # noqa: E402
import trees  # noqa: E402


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = os.path.abspath(args[0] if args else "data/mods/core/models")
    only = args[1] if len(args) > 1 else None
    if only in (None, "characters"):
        human.make_all(os.path.join(out, "characters"))
    if only in (None, "props"):
        props.make_all(os.path.join(out, "props"))
    if only in (None, "trees"):
        trees.make_all(os.path.join(out, "props"), args[2:] if only == "trees" else None)
    if only in (None, "buildings"):
        buildings.make_all(os.path.join(out, "buildings"))
    if only in (None, "animals"):
        animals.make_all(os.path.join(out, "animals"))
    print("SalvaCiudad models written to", out)


main()
