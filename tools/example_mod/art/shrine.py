"""The example mod's shrine: a small stone shrine with a pitched roof.

    blender --background --factory-startup --python tools/example_mod/art/shrine.py -- tools/example_mod/models

It reuses the helpers of the base game's scripts (art/blender/common.py).
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "art", "blender"))

import common  # noqa: E402
from common import MeshBuilder  # noqa: E402

COLORS = {
    "stone": common.rgb(0xA49C90),
    "stone_dark": common.rgb(0x7E776E),
    "roof": common.rgb(0x5E7A8C),
    "gold": common.rgb(0xD9A441),
}


def shrine(folder):
    common.reset_scene()
    mb = MeshBuilder()
    mb.box((0, 0, 0.15), (3.2, 3.2, 0.3), "stone_dark")
    mb.box((0, 0, 0.4), (2.6, 2.6, 0.2), "stone")
    for x in (-1.0, 1.0):
        for y in (-1.0, 1.0):
            mb.cylinder((x, y, 0.5), (x, y, 2.4), 0.16, 0.14, "stone", segments=8)
    mb.box((0, 0, 2.5), (2.6, 2.6, 0.2), "stone_dark")
    roof = mb.prism([(-1.6, 2.6), (1.6, 2.6), (0, 3.6)], -1.6, 1.6, "roof")
    for v in roof:
        v.co.x, v.co.y, v.co.z = v.co.z, v.co.x, v.co.y
    mb.box((0, 0, 0.9), (0.6, 0.6, 0.8), "stone")
    mb.sphere((0, 0, 1.5), 0.25, "gold", segments=10, rings=6)
    obj = mb.to_object("shrine", COLORS)
    common.export_glb(os.path.join(folder, "shrine.glb"), [obj])


args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
out = os.path.abspath(args[0] if args else os.path.join(HERE, "..", "models"))
os.makedirs(out, exist_ok=True)
shrine(out)
print("shrine written to", out)
