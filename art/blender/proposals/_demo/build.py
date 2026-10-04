"""Two small models that exercise the proposal kit: a static crate and a
signpost whose board swings.

    blender --background --factory-startup --python art/blender/proposals/_demo/build.py
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import _kit as kit  # noqa: E402
import common  # noqa: E402

FAMILY = "_demo"
COLORS = {
    "wood": common.rgb(0x8A6038),
    "wood_light": common.rgb(0xB08A5A),
    "iron": common.rgb(0x44484E),
}


def crate():
    mb = kit.begin()
    mb.box((0, 0, 0.3), (0.6, 0.6, 0.6), "wood_light")
    for x in (-0.3, 0.3):
        for y in (-0.3, 0.3):
            mb.box((x, y, 0.3), (0.08, 0.08, 0.64), "wood")
    kit.save(mb, FAMILY, "demo_crate", COLORS)


def swing_sign():
    mb = kit.begin()
    mb.cylinder((0, 0, 0), (0, 0, 2.4), 0.07, 0.06, "wood")
    mb.box((0.45, 0, 2.2), (1.0, 0.07, 0.07), "wood")
    mb.box((0.55, 0, 1.85), (0.6, 0.04, 0.5), "wood_light", weights={"board": 1.0})
    for x in (0.32, 0.78):
        mb.box((x, 0, 2.13), (0.03, 0.03, 0.1), "iron", weights={"board": 1.0})
    mech = kit.Mech([("board", (0.55, 0, 2.17), (0.55, 0, 1.6), None)])
    mech.clip("swing", 2.0, lambda t: {"board": [(kit.X, 14 * math.sin(2 * math.pi * t))]})
    kit.save(mb, FAMILY, "demo_swing_sign", COLORS, mech=mech)


kit.run({"demo_crate": crate, "demo_swing_sign": swing_sign}, FAMILY)
