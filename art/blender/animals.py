"""Animals: deer, boar, wolf and bear, low-poly and standing on Z = 0 with
the head toward -Y (the front, like the buildings and the characters).
They have no skeleton: the game makes them trot by bobbing them up and
down (phase 18; animated rigs are for later)."""

import os

import common
from common import MeshBuilder

COLORS = {
    "deer": common.rgb(0x8A5A34),
    "deer_light": common.rgb(0xD8C0A0),
    "antler": common.rgb(0xD0C0A0),
    "boar": common.rgb(0x4A3A30),
    "boar_dark": common.rgb(0x2E2420),
    "tusk": common.rgb(0xE8E0D0),
    "wolf": common.rgb(0x7A7A80),
    "wolf_light": common.rgb(0xC8C8CC),
    "bear": common.rgb(0x4E3424),
    "bear_dark": common.rgb(0x3A2618),
    "nose": common.rgb(0x1E1A18),
    "eye": common.rgb(0x101010),
}


def legs(mb, xs, ys, top, r, mat, foot=None):
    for x in xs:
        for y in ys:
            mb.cylinder((x, y, 0), (x, y, top), r * 0.8, r, mat, segments=6)
            if foot:
                mb.box((x, y - 0.02, 0.04), (r * 2.2, r * 2.6, 0.08), foot)


def eyes(mb, x, y, z):
    for s in (-1, 1):
        mb.sphere((s * x, y, z), 0.025, "eye", segments=5, rings=3)


def deer(folder):
    common.reset_scene()
    mb = MeshBuilder()
    mb.sphere((0, 0.05, 0.95), 0.4, "deer", segments=9, rings=6, scale=(0.75, 1.55, 0.8))
    mb.sphere((0, 0.05, 0.85), 0.3, "deer_light", segments=7, rings=5, scale=(0.7, 1.4, 0.6))
    legs(mb, (-0.16, 0.16), (-0.42, 0.45), 0.85, 0.05, "deer", foot="nose")
    mb.cylinder((0, -0.5, 1.1), (0, -0.72, 1.55), 0.13, 0.1, "deer", segments=7)
    mb.sphere((0, -0.85, 1.58), 0.14, "deer", segments=7, rings=5, scale=(0.8, 1.5, 0.85))
    mb.sphere((0, -1.05, 1.53), 0.045, "nose", segments=5, rings=3)
    eyes(mb, 0.09, -0.9, 1.63)
    for s in (-1, 1):
        mb.sphere((s * 0.12, -0.75, 1.72), 0.06, "deer", segments=5, rings=3, scale=(1.5, 0.5, 1.0))
        base = (s * 0.07, -0.8, 1.7)
        tip = (s * 0.25, -0.7, 2.05)
        mb.cylinder(base, tip, 0.025, 0.015, "antler", segments=4)
        mb.cylinder((s * 0.17, -0.74, 1.88), (s * 0.12, -0.88, 2.0), 0.015, 0.01, "antler", segments=4)
    mb.sphere((0, 0.62, 1.05), 0.07, "deer_light", segments=5, rings=3)
    export(folder, "deer", mb)


def boar(folder):
    common.reset_scene()
    mb = MeshBuilder()
    mb.sphere((0, 0.05, 0.5), 0.36, "boar", segments=9, rings=6, scale=(0.85, 1.6, 0.9))
    mb.sphere((0, -0.1, 0.72), 0.2, "boar_dark", segments=7, rings=4, scale=(0.6, 2.2, 0.5))  # The bristly back.
    legs(mb, (-0.17, 0.17), (-0.35, 0.4), 0.35, 0.06, "boar_dark")
    mb.sphere((0, -0.58, 0.48), 0.2, "boar", segments=7, rings=5, scale=(0.9, 1.3, 0.9))
    mb.cylinder((0, -0.75, 0.42), (0, -0.92, 0.38), 0.1, 0.09, "boar", segments=7)
    mb.cylinder((0, -0.92, 0.38), (0, -0.94, 0.38), 0.09, 0.09, "nose", segments=7)
    for s in (-1, 1):
        mb.cylinder((s * 0.08, -0.85, 0.34), (s * 0.13, -0.93, 0.46), 0.018, 0.005, "tusk", segments=4)
        mb.sphere((s * 0.13, -0.5, 0.66), 0.05, "boar_dark", segments=5, rings=3, scale=(1.0, 0.5, 1.4))
    eyes(mb, 0.1, -0.68, 0.55)
    export(folder, "boar", mb)


def wolf(folder):
    common.reset_scene()
    mb = MeshBuilder()
    mb.sphere((0, 0.05, 0.62), 0.3, "wolf", segments=9, rings=6, scale=(0.75, 1.7, 0.85))
    mb.sphere((0, -0.2, 0.55), 0.24, "wolf_light", segments=7, rings=5, scale=(0.7, 1.1, 0.8))
    legs(mb, (-0.13, 0.13), (-0.35, 0.38), 0.55, 0.045, "wolf", foot="wolf_light")
    mb.cylinder((0, -0.4, 0.72), (0, -0.55, 0.9), 0.14, 0.12, "wolf", segments=7)
    mb.sphere((0, -0.62, 0.92), 0.15, "wolf", segments=7, rings=5, scale=(0.9, 1.1, 0.9))
    mb.cylinder((0, -0.72, 0.88), (0, -0.92, 0.84), 0.07, 0.05, "wolf_light", segments=6)
    mb.sphere((0, -0.93, 0.85), 0.035, "nose", segments=5, rings=3)
    eyes(mb, 0.07, -0.73, 0.97)
    for s in (-1, 1):
        mb.cylinder((s * 0.08, -0.6, 1.02), (s * 0.1, -0.58, 1.17), 0.05, 0.0, "wolf", segments=4)
    mb.cylinder((0, 0.55, 0.7), (0, 0.95, 0.45), 0.08, 0.04, "wolf", segments=6)
    export(folder, "wolf", mb)


def bear(folder):
    common.reset_scene()
    mb = MeshBuilder()
    mb.sphere((0, 0.1, 0.85), 0.6, "bear", segments=10, rings=7, scale=(0.85, 1.35, 0.9))
    mb.sphere((0, -0.3, 1.05), 0.4, "bear_dark", segments=8, rings=5, scale=(0.9, 1.0, 0.8))  # The shoulder hump.
    legs(mb, (-0.3, 0.3), (-0.45, 0.55), 0.6, 0.13, "bear_dark")
    mb.sphere((0, -0.85, 1.0), 0.28, "bear", segments=8, rings=6)
    mb.cylinder((0, -1.05, 0.95), (0, -1.25, 0.9), 0.13, 0.1, "bear", segments=7)
    mb.sphere((0, -1.26, 0.9), 0.05, "nose", segments=5, rings=3)
    eyes(mb, 0.11, -1.06, 1.08)
    for s in (-1, 1):
        mb.sphere((s * 0.19, -0.82, 1.24), 0.08, "bear", segments=6, rings=4)
    export(folder, "bear", mb)


def export(folder, name, mb):
    obj = mb.to_object(name, COLORS)
    common.export_glb(os.path.join(folder, name + ".glb"), [obj])


def make_all(folder):
    os.makedirs(folder, exist_ok=True)
    deer(folder)
    boar(folder)
    wolf(folder)
    bear(folder)
