"""Builds the low-poly animals and plants of art/blender/zoo with the
production technique (studies.build_final: remesh + collapse).

    blender --background --factory-startup --python art/blender/zoo_build.py -- <output folder> [names]

Every module in art/blender/zoo defines SPECS, a list of studies.Spec
objects; a module is named after its spec (lion.py builds "lion"). With
names, only those modules are loaded and built, so a half-edited module
elsewhere does not stop the build.
"""

import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "zoo"))

import studies  # noqa: E402


def load_specs(only):
    specs = []
    for file in sorted(os.listdir(os.path.join(HERE, "zoo"))):
        if file.endswith(".py") and not file.startswith("_") and (not only or file[:-3] in only):
            specs += importlib.import_module(file[:-3]).SPECS
    return specs


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = os.path.abspath(args[0] if args else "art/studies/animals")
    only = set(args[1:])
    specs = [s for s in load_specs(only) if not only or s.name in only]
    missing = only - {s.name for s in specs}
    if missing:
        print("ZOO unknown names:", ", ".join(sorted(missing)))
    for spec in specs:
        studies.build_final(spec, out)


main()
