"""Builds every SalvaCiudad model.

    blender --background --factory-startup --python art/blender/build_all.py -- data/models [only]

`only` limits the build to one group: characters or props.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import human  # noqa: E402
import props  # noqa: E402


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = os.path.abspath(args[0] if args else "data/models")
    only = args[1] if len(args) > 1 else None
    if only in (None, "characters"):
        human.make_all(os.path.join(out, "characters"))
    if only in (None, "props"):
        props.make_all(os.path.join(out, "props"))
    print("SalvaCiudad models written to", out)


main()
