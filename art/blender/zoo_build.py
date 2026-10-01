"""Builds low-poly models from spec folders with the production technique
(studies.build_final: remesh + collapse).

    blender --background --factory-startup --python art/blender/zoo_build.py -- <output folder> [names]
    blender --background --factory-startup --python art/blender/zoo_build.py -- <output folder> specs=<folder> [names]

The specs are read from art/blender/zoo unless `specs=<folder>` names
another folder of art/blender (people, weapons, lowpoly_trees). Every module
there defines SPECS, a list of studies.Spec objects, and is named after its
first spec (lion.py builds "lion"); modules starting with "_" are helpers.
With names, only the modules with those names are loaded, so a half-edited
module elsewhere does not stop the build; a name may also be a spec inside
a loaded module (a tree's "cherry_1_autumn").
"""

import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import studies  # noqa: E402


def load_specs(folder, only):
    """(module name, spec) for the specs of `folder`. A module is loaded
    when no names are given, when it is named, or when a name starts with
    its own (one of its specs)."""
    sys.path.insert(0, os.path.join(HERE, folder))
    specs = []
    for file in sorted(os.listdir(os.path.join(HERE, folder))):
        name = file[:-3]
        if not file.endswith(".py") or file.startswith("_"):
            continue
        if only and not any(o == name or o.startswith(name + "_") for o in only):
            continue
        specs += [(name, spec) for spec in importlib.import_module(name).SPECS]
    return specs


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = os.path.abspath(args[0] if args else "art/studies/animals")
    folder = "zoo"
    only = set()
    for a in args[1:]:
        if a.startswith("specs="):
            folder = a[len("specs="):]
        else:
            only.add(a)
    if not folder.replace("_", "").isalnum() or not os.path.isdir(os.path.join(HERE, folder)):
        print("ZOO unknown specs folder:", folder)
        return
    specs = load_specs(folder, only)
    # A module's name asks for all its specs; a spec's name, for that one.
    wanted = [spec for module, spec in specs if not only or module in only or spec.name in only]
    missing = only - {spec.name for spec in wanted} - {module for module, _ in specs}
    if missing:
        print("ZOO unknown names:", ", ".join(sorted(missing)))
    for spec in wanted:
        studies.build_final(spec, out)


main()
