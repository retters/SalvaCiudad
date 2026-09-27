"""Builds every SalvaCiudad model.

    blender --background --factory-startup --python art/blender/build_all.py -- data/models [only]

`only` limits the build to one group: characters, props or trees. After
"trees", species ids limit it further (for example: trees oak elm).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import human  # noqa: E402
import props  # noqa: E402
import trees  # noqa: E402


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = os.path.abspath(args[0] if args else "data/models")
    only = args[1] if len(args) > 1 else None
    if only in (None, "characters"):
        human.make_all(os.path.join(out, "characters"))
    if only in (None, "props"):
        props.make_all(os.path.join(out, "props"))
    if only in (None, "trees"):
        trees.make_all(os.path.join(out, "props"), args[2:] if only == "trees" else None)
    print("SalvaCiudad models written to", out)


main()
