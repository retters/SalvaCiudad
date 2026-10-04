"""The `walls` proposal family: a modular wall system (2 m module) in some
twenty wall types, with gates, towers, fences, defenses, siege engines and
assembled demos (forts, castles, slopes, kit sheets, rule-generated towns).

    blender --background --factory-startup --python art/blender/proposals/walls/build.py -- [ids]

Every run rewrites catalogo.json from catalog_data.py, listing the models
whose .glb exists.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import _kit as kit  # noqa: E402
import registry  # noqa: E402
from wallkit import FAMILY  # noqa: E402

import wall_models  # noqa: E402,F401  (registers the models)

for name in ("gates", "towers", "fences", "defenses", "forts", "extras", "castle", "siege", "more", "more2",
             "autotile"):
    if os.path.isfile(os.path.join(HERE, name + ".py")):
        __import__(name)

import catalog_data  # noqa: E402


def write_catalog():
    folder = kit.out_folder(FAMILY)
    groups = []
    for g in catalog_data.GROUPS:
        models = [e for gid, e in registry.ENTRIES
                  if gid == g["id"] and os.path.isfile(os.path.join(folder, e["id"] + ".glb"))]
        models.sort(key=lambda e: 0 if "_demo_" in e["id"] else 1)   # The assembled demo first.
        if models:
            groups.append(dict(g, modelos=models))
    known = {g["id"] for g in catalog_data.GROUPS}
    missing = sorted({gid for gid, _ in registry.ENTRIES if gid not in known})
    if missing:
        print("PROPOSAL groups without catalog text:", ", ".join(missing))
    path = os.path.join(HERE, "catalogo.json")
    with open(path + ".tmp", "w", encoding="utf-8", newline="\n") as f:
        json.dump({"familia": FAMILY, "grupos": groups}, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(path + ".tmp", path)
    print("PROPOSAL catalog: %d groups, %d models" % (len(groups), sum(len(g["modelos"]) for g in groups)))


if "--catalog" not in kit.args():
    kit.run(registry.MODELS, FAMILY)
write_catalog()
