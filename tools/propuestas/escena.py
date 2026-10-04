"""Writes docs/propuestas/escena_arboles.js: a few of the game's own trees as
base64, so the sample scene (docs/propuestas/escena.html) is not bare. The
trees are not proposals, so they are kept out of the catalog.

    python tools/propuestas/escena.py
"""

import base64
import json
import os

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TREES = os.path.join(REPO, "data", "mods", "core", "models", "trees")
OUT = os.path.join(REPO, "docs", "propuestas", "escena_arboles.js")
NAMES = ("pine_bloom", "cypress_bloom", "birch_bloom", "elm_1_bloom", "maple_bloom")


def main():
    trees = {}
    for name in NAMES:
        path = os.path.join(TREES, name + ".glb")
        if not os.path.isfile(path):
            print("falta", path)
            continue
        with open(path, "rb") as f:
            trees[name] = base64.b64encode(f.read()).decode("ascii")
    temp = OUT + ".tmp"
    with open(temp, "w", encoding="utf-8", newline="\n") as f:
        f.write("window.ESCENA_ARBOLES = " + json.dumps(trees) + ";\n")
    os.replace(temp, OUT)
    print("escena: %d árboles, %d KB" % (len(trees), os.path.getsize(OUT) // 1024))


if __name__ == "__main__":
    main()
