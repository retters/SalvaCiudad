"""Builds every SalvaCiudad model.

    blender --background --factory-startup --python art/blender/build_all.py -- data/mods/core/models [only]

`only` limits the build to one group: characters, tools, loads, props,
trees, buildings, animals or proposals. After "trees" or "characters", names
limit it further (for example: trees cherry_1 pine); "buildings sites" builds
only the construction sites; after "proposals", family names (piles).
"""

import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import buildings  # noqa: E402
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


# The people of the game (phase 57): the low-poly characters of
# art/blender/people, with the villagers' skeleton and their clips. Which
# race and sex each one is, races.json says.
GAME_PEOPLE = ("adventurer_man", "adventurer_woman", "knight_man", "knight_woman", "mage", "cleric",
               "dwarf_man", "dwarf_woman", "high_elf_man", "high_elf_woman", "dark_elf_man", "dark_elf_woman",
               "catfolk", "foxfolk", "frogfolk", "lizardfolk", "orc")

# The tools the characters hold while a clip plays ("<clip>_prop" in the
# model names the kind): kind -> spec of art/blender/weapons. The game
# knows them by these file names (src/game/builtin_models.h).
# The arrow is not held: it is what a bow shoots (phase 67).
GAME_TOOLS = {"axe": "w07_battle_axe", "bow": "w13_long_bow", "rod": "w18_fishing_rod", "hammer": "w33_stone_hammer",
              "arrow": "w17_arrow"}


def make_people(folder, only=None):
    sys.path.insert(0, os.path.join(HERE, "people"))
    for name in GAME_PEOPLE:
        if only and name not in only:
            continue
        for spec in importlib.import_module(name).SPECS:
            studies.build_final(spec, folder)


def make_tools(folder):
    sys.path.insert(0, os.path.join(HERE, "weapons"))
    for kind, name in sorted(GAME_TOOLS.items()):
        for spec in importlib.import_module(name).SPECS:
            spec.name = kind   # The file is named after what the tool is.
            studies.build_final(spec, folder)


def make_loads(folder):
    """What a villager carries (phase 67): every spec of art/blender/loads,
    rigid models the game pins to the chest bone ("<what>_back" on the back,
    "<what>_arms" in the arms; see loads/_load_kit.py for where they go)."""
    sys.path.insert(0, os.path.join(HERE, "loads"))
    for file in sorted(os.listdir(os.path.join(HERE, "loads"))):
        if not file.endswith(".py") or file.startswith("_"):
            continue
        for spec in importlib.import_module(file[:-3]).SPECS:
            studies.build_final(spec, folder)


def make_animals(folder):
    sys.path.insert(0, os.path.join(HERE, "zoo"))
    for name in GAME_ANIMALS:
        for spec in importlib.import_module(name).SPECS:
            studies.build_final(spec, folder)


def make_proposals(out, only=None):
    """The proposal models that are in the game (phase 89):
    art/blender/proposals/game.json lists them. Each is built by its
    family's own script into art/studies/propuestas (or, for an entry with
    "game": true, its lighter version without a skeleton into
    art/studies/propuestas_game), checked against the triangle limit of its
    class and copied to its folder of the game's models. `only`: family names, to build just those. Returns the problems
    found (a model over its limit is not copied)."""
    import json
    import runpy
    import shutil
    folder = os.path.join(HERE, "proposals")
    sys.path.insert(0, folder)
    import _kit as kit
    with open(os.path.join(folder, "game.json"), encoding="utf-8") as f:
        doc = json.load(f)
    problems = []
    for entry in doc["models"]:
        family = entry["family"]
        if only and family not in only:
            continue
        limit = doc["limits"][entry["class"]]
        # "ids": a list of models, or {model: the name it takes in the game}.
        names = entry["ids"]
        named = names if isinstance(names, dict) else {name: name for name in names}
        ids = [name + suffix for name in named for suffix in entry.get("each", [""])]
        game_name = {name + suffix: named[name] + suffix for name in named for suffix in entry.get("each", [""])}
        script = os.path.join(folder, family)
        before = set(sys.modules)
        kit.SELECT = ids
        kit.GAME = bool(entry.get("game"))
        built_in = kit.OUT_GAME if kit.GAME else kit.OUT
        try:
            runpy.run_path(os.path.join(script, "build.py"), run_name="__main__")
        finally:
            kit.SELECT = None
            kit.GAME = False
            # A family's own modules must not be taken for the next family's.
            for name in set(sys.modules) - before:
                if os.path.dirname(getattr(sys.modules[name], "__file__", None) or "") == script:
                    del sys.modules[name]
            while script in sys.path:
                sys.path.remove(script)
        os.makedirs(os.path.join(out, entry["to"]), exist_ok=True)
        for name in ids:
            built = os.path.join(built_in, family, name + ".glb")
            if not os.path.isfile(built):
                problems.append("%s/%s was not built" % (family, name))
                continue
            triangles = kit._triangles(built)
            if triangles > limit:
                problems.append("%s/%s has %d triangles, over the %d of a %s" % (family, name, triangles, limit, entry["class"]))
                continue
            shutil.copyfile(built, os.path.join(out, entry["to"], game_name[name] + ".glb"))
    for line in problems:
        print("PROPOSAL PROBLEM", line)
    return problems


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = os.path.abspath(args[0] if args else "data/mods/core/models")
    only = args[1] if len(args) > 1 else None
    if only in (None, "characters"):
        make_people(os.path.join(out, "characters"), args[2:] if only == "characters" else None)
    if only in (None, "tools"):
        make_tools(os.path.join(out, "tools"))
    if only in (None, "loads"):
        make_loads(os.path.join(out, "loads"))
    if only in (None, "props"):
        props.make_all(os.path.join(out, "props"))
    if only in (None, "trees"):
        make_trees(os.path.join(out, "trees"), args[2:] if only == "trees" else None)
    if only in (None, "buildings"):
        buildings.make_all(os.path.join(out, "buildings"), args[2:] if only == "buildings" else None)
    if only in (None, "decor"):
        # The decorations (ruins, nature, statues, plaza, garden and market): one module per theme.
        sys.path.insert(0, os.path.join(HERE, "decor"))
        for theme in ("ruins", "nature", "statues", "plaza", "garden_market"):
            importlib.import_module(theme).make_all(os.path.join(out, "buildings"))
    if only in (None, "animals"):
        make_animals(os.path.join(out, "animals"))
    if only in (None, "proposals"):
        if make_proposals(out, args[2:] if only == "proposals" else None):
            sys.exit(1)
    print("SalvaCiudad models written to", out)


main()
