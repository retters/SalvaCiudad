"""House annex proposals: small things built next to a house that give it
something (dry firewood, clean clothes, a place to play). See ../LEEME.md.

    blender --background --factory-startup --python art/blender/proposals/annexes/build.py -- [ids]

Every annex faces -Y, the side one walks up to.
"""

import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import _kit as kit  # noqa: E402
import _shapes  # noqa: E402
import common  # noqa: E402
from _shapes import (TAU, barrel, beam, crate, gable_roof, log, merged, plank_box, rock, rope, sack, shed_roof, solid,  # noqa: E402
                     wheel)

FAMILY = "annexes"
C = common.rgb
COLORS = {
    **_shapes.COLORS,
    "thatch": C(0xC9A55A), "thatch_dark": C(0xA8863F), "shingle": C(0x6A5038), "shingle_dark": C(0x54402C),
    "tile": C(0x9A4A2E), "tile_dark": C(0x7E3A24), "brick": C(0xA0553A), "brick_dark": C(0x84422C),
    "clay": C(0xC08A62), "clay_dark": C(0xA06E4A), "plaster": C(0xE6DCC4),
    "linen": C(0xECE6D6), "linen_shade": C(0xD8D0BC), "cloth_red": C(0xB8423A), "cloth_blue": C(0x3F5E8C),
    "cloth_green": C(0x4F7A44), "cloth_yellow": C(0xE0B840), "wool": C(0xF0ECE0),
    "grass": C(0x6A9440), "grass_dark": C(0x4F7A34), "soil": C(0x6A4A30), "soil_dark": C(0x4A3422), "mud": C(0x5A4632),
    "pig": C(0xE8A8A0), "pig_dark": C(0xC88880), "rabbit": C(0xC8B8A0), "eye": C(0x101010), "carrot": C(0xE8843A),
    "flame": C(0xF08A24), "flame_core": C(0xFFF0B0), "ember": C(0xE85820), "smoke": C(0xA0A0A0), "cave": C(0x14110F),
    "bread": C(0xC08A48), "water": C(0x4A8FC0), "candle": C(0xF0E8D0), "flowers": C(0xC86A8A), "flowers_y": C(0xE0C040),
    "dye_red": C(0xB02030), "dye_blue": C(0x2848A8), "dye_yellow": C(0xE0B020), "leaf": C(0x4E7A34),
    "window": C(0xF6D070),
}


def flames(mb, x, y, z, s, bone):
    w = {bone: 1.0}
    mb.cylinder((x, y, z), (x, y, z + 0.3 * s), 0.12 * s, 0.16 * s, "flame", w, segments=5)
    mb.cylinder((x, y, z + 0.3 * s), (x, y, z + 0.7 * s), 0.16 * s, 0.0, "flame", w, segments=5)
    mb.cylinder((x, y, z + 0.02), (x, y, z + 0.45 * s), 0.08 * s, 0.0, "flame_core", w, segments=5)
    return (bone, (x, y, z), (x, y, z + 0.4 * s), None)


def flame_pose(bone, s=1.0):
    return lambda t: ({bone: [(kit.Z, 360 * t), (kit.X, 8 * math.sin(TAU * 3 * t))]}, {bone: (0, 0, 0.03 * s * math.sin(TAU * 4 * t))})


def firewood(mb, x0, x1, y, z0, rows, rnd, depth=0.5):
    """Split firewood stacked between x0 and x1, the ends toward -Y."""
    r = 0.09
    for row in range(rows):
        n = int((x1 - x0) / (r * 2.05))
        for k in range(n):
            x = x0 + r + k * r * 2.05 + (r if row % 2 else 0)
            if x + r > x1:
                continue
            # Lighter than log(): five sides, and only the end one sees (a stack is a hundred of them).
            ya = y - depth / 2 + rnd.uniform(-0.03, 0.03)
            z = z0 + r + row * r * 1.8
            mb.cylinder((x, ya, z), (x, y + depth / 2, z), r, r * 0.92, "bark", segments=5)
            mb.cylinder((x, ya - 0.006, z), (x, ya + 0.02, z), r * 0.78, r * 0.78, "log_end", segments=5)


# --- Models -------------------------------------------------------------------------------------


def clothesline(name, colors):
    def build():
        mb = kit.begin()
        for sx in (-1, 1):
            mb.cylinder((sx * 1.8, 0, 0), (sx * 1.8, 0, 2.1), 0.06, 0.05, "pole", segments=6)
            beam(mb, (sx * 1.8, -0.35, 2.0), (sx * 1.8, 0.35, 2.0), 0.04, "pole_dark")
            for sy in (-0.3, 0.3):
                beam(mb, (sx * 1.8, sy, 2.0), (sx * 1.8, 0, 1.7), 0.025, "pole_dark")
        bones, poses = [], []
        items = [(-1.3, -0.3, "shirt"), (-0.45, -0.3, "sheet"), (0.75, -0.3, "trousers"), (-0.9, 0.3, "sheet"), (0.25, 0.3, "shirt"), (1.2, 0.3, "sock")]
        for i, (x, y, kind) in enumerate(items):
            rope(mb, (-1.8, y, 2.0), (1.8, y, 2.0), 0.012) if i in (0, 3) else None
            bone = "cloth%d" % i
            w = {bone: 1.0}
            mat = colors[i % len(colors)]
            z = 1.98
            if kind == "sheet":
                solid(mb, [(x - 0.45, y, z), (x + 0.45, y, z), (x + 0.45, y, z - 1.1), (x - 0.45, y, z - 1.1)], (0, 0.025, 0), mat, w)
                solid(mb, [(x - 0.45, y - 0.004, z - 0.9), (x + 0.45, y - 0.004, z - 0.9), (x + 0.45, y - 0.004, z - 1.0), (x - 0.45, y - 0.004, z - 1.0)],
                      (0, 0.033, 0), "linen_shade", w)
            elif kind == "shirt":
                solid(mb, [(x - 0.25, y, z), (x + 0.25, y, z), (x + 0.28, y, z - 0.75), (x - 0.28, y, z - 0.75)], (0, 0.025, 0), mat, w)
                for s in (-1, 1):
                    solid(mb, [(x + s * 0.25, y, z), (x + s * 0.55, y, z - 0.32), (x + s * 0.45, y, z - 0.45), (x + s * 0.25, y, z - 0.25)], (0, 0.025, 0), mat, w)
            elif kind == "trousers":
                solid(mb, [(x - 0.25, y, z), (x + 0.25, y, z), (x + 0.25, y, z - 0.35), (x - 0.25, y, z - 0.35)], (0, 0.025, 0), mat, w)
                for s in (-1, 1):
                    solid(mb, [(x + s * 0.25, y, z - 0.35), (x + s * 0.02, y, z - 0.35), (x + s * 0.06, y, z - 0.95), (x + s * 0.27, y, z - 0.95)], (0, 0.025, 0), mat, w)
            else:
                for s in (-0.12, 0.12):
                    solid(mb, [(x + s - 0.06, y, z), (x + s + 0.06, y, z), (x + s + 0.06, y, z - 0.3), (x + s + 0.18, y, z - 0.38), (x + s - 0.06, y, z - 0.4)],
                          (0, 0.025, 0), mat, w)
            for s in (-0.18, 0.18):
                mb.box((x + s, y + 0.012, z + 0.01), (0.03, 0.05, 0.08), "pole_dark", w)
            bones.append((bone, (x, y, 2.0), (x, y, 1.4), None))
            poses.append((bone, i))
        mb.cylinder((1.1, -0.9, 0), (1.1, -0.9, 0.35), 0.36, 0.42, "plank", segments=10)      # The wash tub.
        mb.cylinder((1.1, -0.9, 0.3), (1.1, -0.9, 0.34), 0.38, 0.38, "water", segments=10)
        solid(mb, [(0.95, -0.85, 0.2), (1.25, -0.85, 0.2), (1.25, -0.6, 0.75), (0.95, -0.6, 0.75)], (0, 0.03, 0.02), "plank_light")
        mb.cylinder((-0.9, -0.95, 0), (-0.9, -0.95, 0.3), 0.26, 0.32, "hay_dark", segments=8)   # A basket of laundry.
        mb.sphere((-0.9, -0.95, 0.32), 0.26, colors[0], segments=7, rings=4, scale=(1, 1, 0.5))

        def sway(t):
            return {b: [(kit.X, 9 * math.sin(TAU * t + i * 0.8)), (kit.Z, 4 * math.sin(TAU * 2 * t + i))] for b, i in poses}, {}

        kit.save(mb, FAMILY, name, COLORS, mech=kit.Mech(bones).clip("sway", 3.0, sway))
    return build


def woodshed(name, stone):
    def build():
        mb = kit.begin()
        rnd = random.Random(3)
        roof = ("tile", "tile_dark") if stone else ("thatch", "thatch_dark")
        if stone:
            mb.box((0, 0.65, 0.9), (3.2, 0.3, 1.8), "stone")
            for sx in (-1, 1):
                mb.box((sx * 1.5, 0, 0.75), (0.3, 1.3, 1.5), "stone_dark" if sx < 0 else "stone")
        else:
            for sx in (-1.5, 0, 1.5):
                mb.cylinder((sx, 0.65, 0), (sx, 0.65, 1.95), 0.07, 0.06, "pole", segments=6)
                mb.cylinder((sx, -0.6, 0), (sx, -0.6, 1.45), 0.07, 0.06, "pole", segments=6)
            for k in range(6):
                mb.box((0, 0.68, 0.2 + 0.3 * k), (3.1, 0.04, 0.26), "plank" if k % 2 else "plank_light")
        shed_roof(mb, 0, 0, 3.2, 1.4, 1.5, 2.0, roof, 0.25)
        mb.box((0, 0, 0.05), (3.0, 1.2, 0.1), "plank_dark")
        firewood(mb, -1.35, 1.35, 0.25, 0.1, 6, rnd)
        firewood(mb, -1.35, 0.3, -0.3, 0.1, 3, rnd)
        mb.cylinder((2.3, -0.6, 0), (2.3, -0.6, 0.45), 0.3, 0.28, "bark", segments=8)      # The chopping block.
        mb.cylinder((2.3, -0.6, 0.44), (2.3, -0.6, 0.46), 0.25, 0.25, "log_end", segments=8)
        mb.cylinder((2.3, -0.6, 0.5), (2.65, -0.75, 1.15), 0.022, 0.022, "pole", segments=5)
        mb.box((2.3, -0.6, 0.55), (0.05, 0.2, 0.16), "steel", rotation_z=0.4)
        for _ in range(5):
            a = rnd.uniform(0, TAU)
            log(mb, (2.3 + math.cos(a) * 0.6, -0.6 + math.sin(a) * 0.6, 0.07), (2.3 + math.cos(a) * 0.95, -0.6 + math.sin(a) * 0.95, 0.07), 0.07)
        kit.save(mb, FAMILY, name, COLORS)
    return build


def outhouse(name, brick):
    def build():
        mb = kit.begin()
        if brick:
            mb.box((0, 0, 1.05), (1.4, 1.4, 2.1), "brick")
            for k in range(7):
                mb.box((0, 0, 0.15 + 0.3 * k), (1.43, 1.43, 0.03), "brick_dark")
            shed_roof(mb, 0, 0, 1.4, 1.4, 2.1, 2.5, ("tile", "tile_dark"), 0.18)
        else:
            plank_box(mb, 0, 0, 1.3, 1.3, 0.1, 2.15)
            shed_roof(mb, 0, 0, 1.3, 1.3, 2.15, 2.5, ("shingle", "shingle_dark"), 0.18)
        mb.box((0, 0, 0.05), (1.5, 1.5, 0.1), "stone_dark")
        mb.box((0, -0.68 if not brick else -0.71, 1.05), (0.75, 0.05, 1.85), "plank_dark")
        for k in range(3):
            mb.box((-0.25 + 0.25 * k, -0.71 if not brick else -0.74, 1.05), (0.22, 0.02, 1.8), "plank" if k % 2 else "plank_light")
        y = -0.725 if not brick else -0.755
        solid(mb, [(-0.1, y, 1.6), (0.02, y, 1.52), (0.1, y, 1.6), (0.02, y, 1.74)], (0, -0.008, 0), "cave")     # A moon in the door.
        solid(mb, [(-0.02, y - 0.004, 1.6), (0.06, y - 0.004, 1.55), (0.11, y - 0.004, 1.61), (0.06, y - 0.004, 1.7)], (0, -0.008, 0), "plank_light")
        mb.box((0.28, y, 1.05), (0.04, 0.05, 0.14), "iron")
        mb.box((0, -0.95, 0.06), (0.8, 0.5, 0.12), "stone")
        mb.cylinder((0.9, -0.5, 0), (0.9, -0.5, 0.3), 0.14, 0.17, "plank_light", segments=8)
        mb.cylinder((0.45, 0.45, 2.3), (0.45, 0.45, 2.95), 0.05, 0.05, "plank_dark", segments=6)     # A vent pipe.
        kit.save(mb, FAMILY, name, COLORS)
    return build


def rain_barrel():
    mb = kit.begin()
    mb.box((0, 0, 0.1), (1.2, 1.2, 0.2), "stone")
    barrel(mb, 0, 0, 0.2, 1.1, 0.42)
    mb.cylinder((0, 0, 1.26), (0, 0, 1.3), 0.34, 0.34, "water", segments=10)
    mb.cylinder((0.6, 0.6, 0), (0.6, 0.6, 2.7), 0.06, 0.05, "pole", segments=6)       # The corner of an eave, with its gutter.
    solid(mb, [(-0.9, 0.62, 2.62), (0.75, 0.62, 2.5), (0.75, 0.62, 2.62), (-0.9, 0.62, 2.74)], (0, -0.14, 0), "plank_dark")
    solid(mb, [(-0.9, 0.5, 2.66), (0.75, 0.5, 2.54), (0.75, 0.5, 2.6), (-0.9, 0.5, 2.72)], (0, -0.03, 0), "plank")
    beam(mb, (0.7, 0.55, 2.5), (0.15, 0.1, 1.4), 0.045, "plank_dark")
    mb.cylinder((0.42, -0.02, 0.55), (0.56, -0.02, 0.5), 0.03, 0.03, "iron", segments=6)
    mb.cylinder((0.85, -0.3, 0), (0.85, -0.3, 0.3), 0.15, 0.19, "plank_light", segments=8)
    mb.cylinder((0.85, -0.3, 0.26), (0.85, -0.3, 0.29), 0.16, 0.16, "water", segments=8)
    for a in (2.5, 4.0):
        mb.sphere((math.cos(a) * 0.75, math.sin(a) * 0.75, 0.3), 0.14, "flowers" if a < 3 else "flowers_y", segments=6, rings=4)
        mb.cylinder((math.cos(a) * 0.75, math.sin(a) * 0.75, 0), (math.cos(a) * 0.75, math.sin(a) * 0.75, 0.2), 0.12, 0.15, "clay", segments=7)
    kit.save(mb, FAMILY, "annex_rain_barrel", COLORS)


def root_cellar():
    mb = kit.begin()
    rnd = random.Random(4)
    mb.sphere((0, 1.2, 0), 2.2, "grass", segments=9, rings=5, scale=(1.0, 1.15, 0.7))
    for _ in range(7):
        a = rnd.uniform(0.3, 2.8)
        mb.sphere((math.cos(a) * rnd.uniform(0.5, 1.6), 1.2 + math.sin(a) * rnd.uniform(0.3, 1.6), 1.3), rnd.uniform(0.2, 0.4), "grass_dark", segments=6, rings=3,
                  scale=(1, 1, 0.5))
    for sx in (-1, 1):
        mb.box((sx * 0.75, -0.75, 0.75), (0.4, 0.6, 1.5), "stone" if sx < 0 else "stone_dark")
    mb.box((0, -0.75, 1.65), (2.1, 0.7, 0.35), "stone_light")
    mb.box((0, -0.85, 0.72), (1.1, 0.08, 1.45), "plank_dark")
    for k in range(4):
        mb.box((-0.39 + 0.26 * k, -0.9, 0.72), (0.23, 0.03, 1.4), "plank" if k % 2 else "plank_light")
    for zz in (0.35, 1.1):
        mb.box((0, -0.92, zz), (1.1, 0.02, 0.08), "iron")
    mb.box((0.4, -0.93, 0.75), (0.05, 0.04, 0.16), "iron")
    for k in range(2):
        mb.box((0, -1.25 - 0.3 * k, 0.05), (1.3, 0.32, 0.1), "stone")
    mb.cylinder((0.6, 1.4, 1.4), (0.6, 1.4, 2.1), 0.07, 0.07, "plank_dark", segments=6)
    mb.cylinder((0.6, 1.4, 2.1), (0.6, 1.4, 2.2), 0.14, 0.03, "plank_dark", segments=6)
    crate(mb, 1.5, -1.1, 0.0, 0.5)
    sack(mb, -1.4, -1.1, 0.0, 0.26)
    sack(mb, -1.8, -0.8, 0.0, 0.22)
    barrel(mb, 1.55, -0.45, 0.0, 0.75, 0.27)
    kit.save(mb, FAMILY, "annex_root_cellar", COLORS)


def pen(mb, w, d, gate=True):
    for sx in (-1, 1):
        for k in range(4):
            mb.cylinder((sx * w / 2, -d / 2 + d * k / 3, 0), (sx * w / 2, -d / 2 + d * k / 3, 0.9), 0.05, 0.045, "pole", segments=6)
        for z in (0.35, 0.72):
            beam(mb, (sx * w / 2, -d / 2, z), (sx * w / 2, d / 2, z), 0.035, "pole_dark")
    for sy in (-1, 1):
        for k in range(1, 3):
            mb.cylinder((-w / 2 + w * k / 3, sy * d / 2, 0), (-w / 2 + w * k / 3, sy * d / 2, 0.9), 0.05, 0.045, "pole", segments=6)
        for z in (0.35, 0.72):
            if sy < 0 and gate:
                beam(mb, (-w / 2, sy * d / 2, z), (-w / 6, sy * d / 2, z), 0.035, "pole_dark")
                beam(mb, (w / 6, sy * d / 2, z), (w / 2, sy * d / 2, z), 0.035, "pole_dark")
                beam(mb, (-w / 6, sy * d / 2 - 0.05, z), (w / 6, sy * d / 2 - 0.05, z), 0.03, "plank_light")
            else:
                beam(mb, (-w / 2, sy * d / 2, z), (w / 2, sy * d / 2, z), 0.035, "pole_dark")


def pigsty():
    mb = kit.begin()
    pen(mb, 4.0, 3.0)
    mb.sphere((-0.4, -0.2, 0.0), 1.3, "mud", segments=8, rings=4, scale=(1.2, 0.9, 0.06))
    for sx in (0.9, 1.9):       # The shelter, in a corner.
        mb.cylinder((sx, 0.4, 0), (sx, 0.4, 1.0), 0.06, 0.05, "pole", segments=6)
    mb.box((1.4, 1.42, 0.65), (1.2, 0.06, 1.3), "plank")
    shed_roof(mb, 1.4, 0.9, 1.2, 1.1, 1.0, 1.4, ("thatch", "thatch_dark"), 0.18)
    mb.sphere((1.4, 0.95, 0.05), 0.5, "hay", segments=7, rings=3, scale=(1.1, 0.9, 0.3))
    log(mb, (-1.6, -1.1, 0.16), (-0.3, -1.1, 0.16), 0.17)                                # The trough.
    mb.box((-0.95, -1.1, 0.27), (1.15, 0.2, 0.05), "bread")
    w, wh, wt = {"pig": 1.0}, {"pig_head": 1.0}, {"pig_tail": 1.0}
    px, py = -0.75, -0.3
    mb.sphere((px, py, 0.42), 0.3, "pig", w, segments=8, rings=5, scale=(1.0, 1.65, 0.95))
    for sx in (-1, 1):
        for sy in (-0.28, 0.3):
            mb.cylinder((px + sx * 0.16, py + sy, 0.3), (px + sx * 0.16, py + sy, 0.0), 0.06, 0.045, "pig_dark", w, segments=5)
    mb.sphere((px, py - 0.5, 0.45), 0.2, "pig", wh, segments=7, rings=5, scale=(1, 1.1, 1))
    mb.cylinder((px, py - 0.66, 0.42), (px, py - 0.78, 0.4), 0.09, 0.08, "pig_dark", wh, segments=6)
    for sx in (-1, 1):
        solid(mb, [(px + sx * 0.08, py - 0.45, 0.6), (px + sx * 0.2, py - 0.5, 0.62), (px + sx * 0.14, py - 0.58, 0.5)], (0, 0.02, 0.01), "pig_dark", wh)
        mb.box((px + sx * 0.11, py - 0.64, 0.5), (0.03, 0.03, 0.03), "eye", wh)
    beam(mb, (px, py + 0.48, 0.5), (px + 0.05, py + 0.58, 0.56), 0.018, "pig_dark", wt)
    beam(mb, (px + 0.05, py + 0.58, 0.56), (px - 0.03, py + 0.62, 0.62), 0.016, "pig_dark", wt)
    bones = [("pig", (px, py, 0.42), (px, py - 0.4, 0.42), None), ("pig_head", (px, py - 0.4, 0.45), (px, py - 0.7, 0.45), "pig"),
             ("pig_tail", (px, py + 0.48, 0.5), (px, py + 0.6, 0.56), "pig")]

    def root(t):
        return {"pig_head": [(kit.X, -14 * (0.5 + 0.5 * math.sin(TAU * 2 * t))), (kit.Z, 8 * math.sin(TAU * t))],
                "pig_tail": [(kit.Z, 25 * math.sin(TAU * 4 * t))]}, {"pig": (0, 0, 0.01 * math.sin(TAU * 2 * t))}

    kit.save(mb, FAMILY, "annex_pigsty", COLORS, mech=kit.Mech(bones).clip("root", 3.0, root))


def rabbit_hutch():
    mb = kit.begin()
    for sx in (-0.9, 0.9):
        for sy in (-0.35, 0.35):
            mb.cylinder((sx, sy, 0), (sx, sy, 0.7), 0.05, 0.05, "pole", segments=6)
    mb.box((0, 0, 0.72), (2.0, 0.85, 0.06), "plank_dark")
    mb.box((0, 0.4, 1.1), (2.0, 0.05, 0.75), "plank")
    for sx in (-1, 1):
        mb.box((sx * 1.0, 0, 1.1), (0.05, 0.85, 0.75), "plank")
    mb.box((0, 0, 1.1), (0.05, 0.8, 0.75), "plank_light")
    mb.box((0.5, -0.4, 1.1), (0.95, 0.04, 0.7), "plank")                        # The closed half, with a round door.
    mb.cylinder((0.5, -0.43, 1.0), (0.5, -0.42, 1.0), 0.16, 0.16, "cave", segments=8)
    for k in range(7):                                                          # Bars on the open half.
        beam(mb, (-0.95 + 0.15 * k, -0.4, 0.75), (-0.95 + 0.15 * k, -0.4, 1.47), 0.012, "iron")
    shed_roof(mb, 0, 0, 2.0, 0.85, 1.48, 1.7, ("shingle", "shingle_dark"), 0.12, 2, 0.05)
    solid(mb, [(0.3, -0.42, 0.72), (0.7, -0.42, 0.72), (0.7, -1.3, 0.02), (0.3, -1.3, 0.02)], (0, 0, 0.04), "plank_light")   # A ramp.
    for k in range(5):
        mb.box((0.5, -0.55 - 0.16 * k, 0.66 - 0.127 * k), (0.4, 0.03, 0.03), "plank_dark")
    mb.sphere((-0.5, 0.05, 0.9), 0.15, "rabbit", segments=7, rings=5, scale=(1.0, 1.4, 1.0))
    mb.sphere((-0.5, -0.17, 1.0), 0.09, "rabbit", segments=6, rings=4)
    for sx in (-1, 1):
        mb.cylinder((-0.5 + sx * 0.04, -0.15, 1.07), (-0.5 + sx * 0.06, -0.1, 1.27), 0.03, 0.015, "rabbit", segments=4)
    mb.sphere((-0.5, 0.26, 0.92), 0.05, "wool", segments=5, rings=3)
    mb.sphere((0.9, -1.2, 0.12), 0.13, "wool", segments=7, rings=5, scale=(1.0, 1.4, 1.0))    # One that got out.
    mb.sphere((0.9, -1.38, 0.2), 0.08, "wool", segments=6, rings=4)
    for sx in (-1, 1):
        mb.cylinder((0.9 + sx * 0.035, -1.36, 0.26), (0.9 + sx * 0.05, -1.3, 0.44), 0.028, 0.012, "wool", segments=4)
    for k in range(3):
        mb.cylinder((-0.6 + 0.12 * k, -0.9, 0.03), (-0.55 + 0.12 * k, -0.7, 0.03), 0.04, 0.01, "carrot", segments=5)
    mb.sphere((-1.3, -0.5, 0.1), 0.3, "hay", segments=7, rings=4, scale=(1, 1, 0.6))
    kit.save(mb, FAMILY, "annex_rabbit_hutch", COLORS)


def bread_oven(name, brick):
    def build():
        mb = kit.begin()
        rnd = random.Random(6)
        body, body2 = ("brick", "brick_dark") if brick else ("clay", "clay_dark")
        mb.box((0, 0, 0.4), (1.8, 1.8, 0.8), "stone")
        mb.box((0, 0, 0.83), (1.95, 1.95, 0.08), "stone_dark")
        mb.sphere((0, 0.1, 0.87), 0.82, body, segments=9, rings=6, scale=(1.0, 1.0, 0.85))
        for k in range(3):
            mb.cylinder((0, 0.1, 1.05 + 0.18 * k), (0, 0.1, 1.09 + 0.18 * k), 0.83 * math.cos(0.25 + 0.3 * k) + 0.02, 0.83 * math.cos(0.3 + 0.3 * k) + 0.02, body2, segments=9)
        mb.box((0, -0.72, 1.12), (0.7, 0.3, 0.55), body2)                                   # The mouth.
        solid(mb, [(-0.24, -0.875, 0.88), (0.24, -0.875, 0.88), (0.24, -0.875, 1.15), (0, -0.875, 1.32), (-0.24, -0.875, 1.15)], (0, 0.03, 0), "cave")
        bones = [flames(mb, 0, -0.8, 0.87, 0.5, "fire")]
        mb.cylinder((0, 0.45, 1.4), (0, 0.45, 2.1), 0.16, 0.13, body2, segments=7)
        mb.cylinder((0, 0.45, 2.1), (0, 0.45, 2.18), 0.19, 0.19, "stone_dark", segments=7)
        for i in range(3):
            b = "smoke%d" % i
            mb.sphere((0, 0.45, 2.3), 0.16, "smoke", {b: 1.0}, segments=6, rings=4)
            bones.append((b, (0, 0.45, 2.3), (0, 0.45, 2.6), None))
        for sx in (-1.25, 1.25):
            mb.cylinder((sx, 0.7, 0), (sx, 0.7, 2.3), 0.06, 0.05, "pole", segments=6)
            mb.cylinder((sx, -0.9, 0), (sx, -0.9, 1.95), 0.06, 0.05, "pole", segments=6)
        shed_roof(mb, 0, -0.1, 2.5, 1.6, 1.95, 2.3, ("thatch", "thatch_dark") if not brick else ("tile", "tile_dark"), 0.25)
        beam(mb, (1.0, -1.3, 0.0), (1.2, -0.95, 1.7), 0.02, "pole")                           # The peel.
        solid(mb, [(1.08, -1.36, 0.0), (1.28, -1.24, 0.0), (1.22, -1.18, 0.4), (1.02, -1.3, 0.4)], (0.01, 0.02, 0), "plank_light")
        mb.box((-1.5, -0.4, 0.45), (0.5, 1.0, 0.06), "plank")                                 # A shelf of loaves.
        for sy in (-0.8, 0.0):
            mb.box((-1.5, sy, 0.22), (0.45, 0.06, 0.44), "plank_dark")
        for k in range(3):
            mb.sphere((-1.5, -0.7 + 0.3 * k, 0.55), 0.13, "bread", segments=6, rings=4, scale=(1.2, 0.9, 0.6))
        firewood(mb, 0.3, 1.2, -1.15, 0.0, 2, rnd, 0.4)

        def bake(t):
            turns, moves = flame_pose("fire", 0.5)(t)
            for i in range(3):
                s = (t + i / 3) % 1.0
                moves["smoke%d" % i] = (0.3 * s, 0, 1.3 * s)
                turns["smoke%d" % i] = [(kit.Z, 120 * s)]
            return turns, moves

        kit.save(mb, FAMILY, name, COLORS, mech=kit.Mech(bones).clip("bake", 4.0, bake))
    return build


def porch():
    mb = kit.begin()
    mb.box((0, 0, 0.15), (3.4, 1.8, 0.3), "plank_dark")
    for k in range(9):
        mb.box((-1.5 + 0.375 * k, 0, 0.31), (0.35, 1.78, 0.03), "plank" if k % 2 else "plank_light")
    mb.box((0, -1.05, 0.08), (1.0, 0.35, 0.16), "plank")
    for sx in (-1.6, 1.6):
        mb.cylinder((sx, -0.8, 0.3), (sx, -0.8, 2.4), 0.07, 0.06, "pole", segments=6)
        beam(mb, (sx, -0.8, 2.0), (sx * 0.78, -0.8, 2.4), 0.035, "pole_dark")
        beam(mb, (sx, -0.8, 0.95), (sx, 0.85, 0.95), 0.035, "pole_dark")
        for k in range(4):
            mb.box((sx, -0.5 + 0.4 * k, 0.62), (0.04, 0.04, 0.62), "plank_light")
    for sx in (-1.05, 1.05):
        beam(mb, (sx * 1.52, -0.8, 0.95), (sx * 0.5, -0.8, 0.95), 0.035, "pole_dark")
    mb.box((0, 0.88, 1.5), (3.4, 0.06, 2.4), "plaster")                                     # The wall of the house behind.
    mb.box((0.9, 0.84, 1.3), (0.85, 0.05, 1.9), "plank_dark")
    mb.box((-0.9, 0.84, 1.6), (0.7, 0.05, 0.6), "window")
    shed_roof(mb, 0, 0, 3.4, 1.8, 2.4, 2.9, ("shingle", "shingle_dark"), 0.25)
    w = {"chair": 1.0}
    cx, cy = -0.8, 0.0
    for sx in (-1, 1):                                                                      # A rocking chair.
        for k in range(4):
            a0, a1 = -0.5 + 0.25 * k, -0.5 + 0.25 * (k + 1)
            beam(mb, (cx + sx * 0.25, cy + math.sin(a0) * 0.9, 0.34 + 0.9 * (1 - math.cos(a0))), (cx + sx * 0.25, cy + math.sin(a1) * 0.9, 0.34 + 0.9 * (1 - math.cos(a1))),
                 0.025, "pole_dark", w)
        beam(mb, (cx + sx * 0.25, cy - 0.2, 0.38), (cx + sx * 0.25, cy - 0.22, 0.95), 0.025, "pole", w)
        beam(mb, (cx + sx * 0.25, cy + 0.22, 0.38), (cx + sx * 0.25, cy + 0.4, 1.5), 0.025, "pole", w)
        beam(mb, (cx + sx * 0.25, cy - 0.22, 0.95), (cx + sx * 0.25, cy + 0.3, 0.98), 0.025, "pole_dark", w)
    mb.box((cx, cy, 0.75), (0.5, 0.48, 0.05), "plank_light", w)
    solid(mb, [(cx - 0.25, cy + 0.26, 0.8), (cx + 0.25, cy + 0.26, 0.8), (cx + 0.25, cy + 0.4, 1.5), (cx - 0.25, cy + 0.4, 1.5)], (0, 0.03, 0), "plank_light", w)
    mb.box((cx, cy + 0.05, 0.79), (0.4, 0.36, 0.05), "cloth_red", w)
    mb.cylinder((0.2, -0.1, 0.33), (0.2, -0.1, 0.8), 0.04, 0.04, "pole", segments=6)       # A little table with a mug.
    mb.cylinder((0.2, -0.1, 0.8), (0.2, -0.1, 0.84), 0.28, 0.28, "plank", segments=8)
    mb.cylinder((0.25, -0.05, 0.84), (0.25, -0.05, 0.96), 0.05, 0.055, "clay", segments=7)
    for sx in (-1.4, 1.35):
        mb.cylinder((sx, -0.55, 0.33), (sx, -0.55, 0.58), 0.13, 0.17, "clay", segments=7)
        mb.sphere((sx, -0.55, 0.7), 0.2, "flowers" if sx < 0 else "flowers_y", segments=6, rings=4)
    pose = lambda t: ({"chair": [(kit.X, 7 * math.sin(TAU * t))]}, {})   # noqa: E731
    kit.save(mb, FAMILY, "annex_porch", COLORS, mech=kit.Mech([("chair", (cx, cy, 1.24), (cx, cy, 0.34), None)]).clip("rock", 2.5, pose))


def tool_shed():
    mb = kit.begin()
    plank_box(mb, 0, 0.2, 2.2, 1.6, 0.1, 2.0)
    mb.box((0, 0.2, 0.05), (2.4, 1.8, 0.1), "stone_dark")
    shed_roof(mb, 0, 0.2, 2.2, 1.6, 2.0, 2.5, ("shingle", "shingle_dark"), 0.22)
    mb.box((-0.35, -0.63, 1.0), (0.8, 0.04, 1.75), "cave")
    solid(mb, [(0.05, -0.62, 0.12), (0.05, -0.62, 1.87), (0.6, -1.15, 1.87), (0.6, -1.15, 0.12)], (0.03, 0.03, 0), "plank_light")     # The door, ajar.
    mb.box((0.7, -0.64, 1.3), (0.5, 0.03, 0.5), "window")
    for k, (x, kind) in enumerate(((1.35, "shovel"), (1.6, "rake"), (1.85, "hoe"))):                                                # Tools on the side wall.
        beam(mb, (x - 0.25, -0.75, 0.0), (1.14, -0.45 + 0.35 * k, 1.75), 0.02, "pole")
        if kind == "shovel":
            mb.box((x - 0.25, -0.76, 0.14), (0.2, 0.03, 0.28), "steel")
        elif kind == "rake":
            mb.box((x - 0.25, -0.76, 0.04), (0.4, 0.03, 0.05), "pole_dark")
        else:
            mb.box((x - 0.2, -0.78, 0.05), (0.18, 0.12, 0.03), "steel")
    mb.box((-1.5, -0.3, 0.75), (0.6, 1.0, 0.06), "plank")                                      # A bench with pots.
    for sy in (-0.7, 0.1):
        mb.box((-1.5, sy, 0.37), (0.5, 0.06, 0.74), "plank_dark")
    for k in range(3):
        mb.cylinder((-1.5, -0.6 + 0.3 * k, 0.78), (-1.5, -0.6 + 0.3 * k, 0.95), 0.08, 0.11, "clay", segments=7)
    mb.sphere((-1.5, -0.3, 1.02), 0.1, "leaf", segments=5, rings=3)
    crate(mb, -1.5, -0.3, 0.0, 0.45)
    kit.save(mb, FAMILY, "annex_tool_shed", COLORS)


def spinning_wheel():
    mb = kit.begin()
    mb.box((0, 0, 0.5), (0.2, 1.3, 0.08), "plank")
    solid(mb, [(-0.1, -0.65, 0.46), (0.1, -0.65, 0.46), (0.1, 0.65, 0.62), (-0.1, 0.65, 0.62)], (0, 0, 0.06), "plank_dark")
    for sy, h in ((-0.55, 0.5), (0.55, 0.62)):
        for sx in (-1, 1):
            beam(mb, (sx * 0.05, sy, h), (sx * 0.28, sy * 1.15, 0.0), 0.03, "pole")
    for sx in (-1, 1):
        beam(mb, (sx * 0.13, 0.35, 0.6), (sx * 0.13, 0.35, 1.15), 0.03, "pole_dark")
    wheel(mb, (0, 0.35, 1.1), 0.5, "wheel", width=0.05, mat="plank_light", tire="plank_dark")
    for sx in (-1, 1):
        beam(mb, (sx * 0.1, -0.5, 0.54), (sx * 0.1, -0.5, 0.95), 0.025, "pole_dark")
    mb.cylinder((-0.14, -0.5, 0.9), (0.14, -0.5, 0.9), 0.05, 0.05, "wool", segments=7)       # The bobbin.
    rope(mb, (0, -0.5, 0.94), (0, 0.35, 1.6), 0.008)
    rope(mb, (0, -0.5, 0.86), (0, 0.35, 0.6), 0.008)
    solid(mb, [(-0.12, -0.2, 0.06), (0.12, -0.2, 0.06), (0.12, 0.3, 0.14), (-0.12, 0.3, 0.14)], (0, 0, 0.03), "plank", {"treadle": 1.0})
    mb.cylinder((0.6, -0.5, 0), (0.6, -0.5, 0.45), 0.2, 0.2, "pole", segments=7)              # A stool.
    mb.cylinder((0.6, -0.5, 0.45), (0.6, -0.5, 0.5), 0.24, 0.24, "plank_light", segments=8)
    for x, y in ((-0.7, -0.4), (-0.75, 0.3)):                                                # Baskets of wool.
        mb.cylinder((x, y, 0), (x, y, 0.28), 0.22, 0.27, "hay_dark", segments=8)
        mb.sphere((x, y, 0.32), 0.24, "wool", segments=7, rings=4, scale=(1, 1, 0.6))
    for k, mat in enumerate(("cloth_red", "cloth_blue", "cloth_yellow")):
        mb.sphere((-0.3 + 0.12 * k, 0.95, 0.07), 0.07, mat, segments=6, rings=4)

    def spin(t):
        return {"wheel": [(kit.X, 360 * t)], "treadle": [(kit.X, 8 * math.sin(TAU * 2 * t))]}, {}

    mech = kit.Mech([("wheel", (0, 0.35, 1.1), (0.4, 0.35, 1.1), None), ("treadle", (0, -0.2, 0.08), (0, 0.3, 0.14), None)])
    kit.save(mb, FAMILY, "annex_spinning_wheel", COLORS, mech=mech.clip("spin", 2.0, spin))


def cart_shed():
    mb = kit.begin()
    for sx in (-1.7, 1.7):
        mb.cylinder((sx, -1.2, 0), (sx, -1.2, 2.0), 0.08, 0.07, "pole", segments=6)
        mb.cylinder((sx, 1.2, 0), (sx, 1.2, 2.6), 0.08, 0.07, "pole", segments=6)
        beam(mb, (sx, -1.2, 2.0), (sx, 1.2, 2.6), 0.06, "pole_dark")
        beam(mb, (sx, -1.2, 1.4), (sx * 0.72, -1.2, 2.0), 0.035, "pole_dark")
    for k in range(7):
        mb.box((0, 1.22, 0.2 + 0.34 * k), (3.4, 0.04, 0.3), "plank" if k % 2 else "plank_light")
    for k in range(4):
        mb.box((-1.72, -0.9 + 0.6 * k, 0.9), (0.04, 0.5, 1.7), "plank" if k % 2 else "plank_light")
    shed_roof(mb, 0, 0, 3.4, 2.4, 2.0, 2.6, ("thatch", "thatch_dark"), 0.3)
    # A hand cart inside (not animated: it is parked).
    mb.box((0.2, 0.1, 0.75), (1.1, 1.7, 0.08), "plank_dark")
    for sx in (-1, 1):
        mb.box((0.2 + sx * 0.55, 0.1, 0.95), (0.05, 1.7, 0.35), "plank")
        beam(mb, (0.2 + sx * 0.45, -0.75, 0.75), (0.2 + sx * 0.45, -1.75, 0.35), 0.035, "pole")
    mb.box((0.2, 0.93, 0.95), (1.1, 0.05, 0.35), "plank")
    wheel(mb, (-0.5, 0.2, 0.5), 0.5, "root")
    wheel(mb, (0.9, 0.2, 0.5), 0.5, "root")
    mb.cylinder((-0.5, 0.2, 0.5), (0.9, 0.2, 0.5), 0.04, 0.04, "iron", segments=6)
    sack(mb, 0.0, 0.3, 0.79, 0.24)
    sack(mb, 0.45, 0.0, 0.79, 0.22)
    for k in range(3):                                                                      # Harness on the back wall.
        mb.cylinder((-1.0 + 0.4 * k, 1.17, 1.8), (-1.0 + 0.4 * k, 1.12, 1.8), 0.16, 0.16, "leather", segments=8)
    barrel(mb, -1.3, 0.75, 0.0, 0.8, 0.28)
    kit.save(mb, FAMILY, "annex_cart_shed", COLORS)


def playground(name, kind):
    def build():
        mb = kit.begin()
        if kind == "swing":
            for sx in (-1.3, 1.3):
                for sy in (-0.8, 0.8):
                    log(mb, (sx, sy, 0), (sx * 0.96, 0, 2.5), 0.07)
            log(mb, (-1.5, 0, 2.5), (1.5, 0, 2.5), 0.08)
            bones = []
            for i, x in enumerate((-0.55, 0.55)):
                b = "swing%d" % i
                w = {b: 1.0}
                for sx in (-0.2, 0.2):
                    rope(mb, (x + sx, 0, 2.45), (x + sx, 0, 0.6), 0.015, w)
                mb.box((x, 0, 0.58), (0.5, 0.2, 0.04), "plank_light", w)
                bones.append((b, (x, 0, 2.45), (x, 0, 0.6), None))
            pose = lambda t: ({"swing0": [(kit.X, 26 * math.sin(TAU * t))], "swing1": [(kit.X, 18 * math.sin(TAU * t + 2.0))]}, {})   # noqa: E731
            kit.save(mb, FAMILY, name, COLORS, mech=kit.Mech(bones).clip("swing", 2.6, pose))
        else:
            log(mb, (-0.4, 0, 0.0), (-0.4, 0, 0.55), 0.12)
            log(mb, (0.4, 0, 0.0), (0.4, 0, 0.55), 0.12)
            mb.cylinder((-0.5, 0, 0.6), (0.5, 0, 0.6), 0.05, 0.05, "iron", segments=6)
            w = {"plank": 1.0}
            mb.box((0, 0, 0.68), (0.32, 3.4, 0.07), "plank_light", w)
            for sy in (-1, 1):
                mb.box((0, sy * 1.25, 0.82), (0.3, 0.04, 0.24), "plank_dark", w)
                mb.cylinder((-0.14, sy * 1.25, 0.94), (0.14, sy * 1.25, 0.94), 0.025, 0.025, "pole", w, segments=6)
                mb.box((0, sy * 1.5, 0.72), (0.3, 0.3, 0.03), "cloth_red" if sy < 0 else "cloth_blue", w)
            pose = lambda t: ({"plank": [(kit.X, 12 * math.sin(TAU * t))]}, {})   # noqa: E731
            kit.save(mb, FAMILY, name, COLORS, mech=kit.Mech([("plank", (0, 0, 0.62), (0, 1.0, 0.62), None)]).clip("rock", 2.4, pose))
    return build


def home_shrine(name, stone):
    def build():
        mb = kit.begin()
        if stone:
            mb.box((0, 0, 0.12), (0.9, 0.8, 0.24), "stone_dark")
            mb.box((0, 0, 0.7), (0.6, 0.5, 0.95), "stone")
            mb.box((0, 0.2, 1.55), (0.7, 0.14, 0.75), "stone")
            for sx in (-1, 1):
                mb.box((sx * 0.3, -0.02, 1.55), (0.1, 0.44, 0.75), "stone_light")
            gable_roof(mb, 0, 0, 0.74, 0.6, 1.92, 0.3, ("stone_dark", "stone"), 0.08, 1, 0.07, gable="stone_light")
            mb.box((0, -0.02, 1.2), (0.62, 0.52, 0.06), "stone_light")
        else:
            mb.cylinder((0, 0, 0), (0, 0, 1.2), 0.08, 0.07, "pole", segments=7)
            for i in range(4):
                a = TAU * i / 4 + 0.6
                rock(mb, math.cos(a) * 0.22, math.sin(a) * 0.22, 0.08, 0.16, random.Random(i))
            mb.box((0, -0.02, 1.2), (0.7, 0.5, 0.06), "plank")
            mb.box((0, 0.2, 1.55), (0.66, 0.05, 0.7), "plank_light")
            for sx in (-1, 1):
                mb.box((sx * 0.32, -0.02, 1.55), (0.05, 0.44, 0.7), "plank")
            gable_roof(mb, 0, 0, 0.7, 0.55, 1.9, 0.28, ("shingle", "shingle_dark"), 0.1, 2, 0.05, gable="plank_light")
        mb.cylinder((0, 0.05, 1.24), (0, 0.05, 1.3), 0.1, 0.08, "gold", segments=7)           # A small figure.
        mb.cylinder((0, 0.05, 1.3), (0, 0.05, 1.55), 0.07, 0.04, "linen", segments=6)
        mb.sphere((0, 0.05, 1.6), 0.055, "linen", segments=6, rings=4)
        for sx in (-0.18, 0.18):
            mb.cylinder((sx, -0.12, 1.24), (sx, -0.12, 1.38), 0.025, 0.025, "candle", segments=6)
        bones = [flames(mb, -0.18, -0.12, 1.38, 0.12, "flame_l"), flames(mb, 0.18, -0.12, 1.38, 0.12, "flame_r")]
        mb.sphere((0.05, -0.18, 1.27), 0.05, "bread", segments=5, rings=3, scale=(1.3, 1, 0.6))
        for k in range(3):
            mb.sphere((-0.05 - 0.05 * k, -0.2, 1.26), 0.03, "flowers" if k % 2 else "flowers_y", segments=5, rings=3)
        kit.save(mb, FAMILY, name, COLORS, mech=kit.Mech(bones).clip("burn", 3.0, merged(flame_pose("flame_l", 0.1), flame_pose("flame_r", 0.1))))
    return build


def compost_bin():
    mb = kit.begin()
    for k in range(4):
        x = -1.5 + 1.0 * k
        for sy in (-0.5, 0.5):
            mb.cylinder((x, sy, 0), (x, sy, 1.0), 0.05, 0.05, "pole", segments=6)
        for z in (0.15, 0.42, 0.69, 0.94):
            mb.box((x, 0, z), (0.04, 1.0, 0.16), "plank" if k % 2 else "plank_light")
    for z in (0.15, 0.42, 0.69, 0.94):
        mb.box((0, 0.5, z), (3.0, 0.04, 0.16), "plank")
    for k, (mat, h) in enumerate((("leaf", 0.75), ("soil", 0.55), ("soil_dark", 0.35))):
        mb.sphere((-1.0 + 1.0 * k, 0.05, 0.0), 0.5, mat, segments=7, rings=4, scale=(0.9, 0.85, h * 2))
    for z in (0.15, 0.42):
        mb.box((-1.0, -0.5, z), (0.95, 0.04, 0.16), "plank_light")
        mb.box((0.0, -0.5, z), (0.95, 0.04, 0.16), "plank_light")
    beam(mb, (1.8, -0.5, 0.0), (1.55, -0.45, 1.5), 0.02, "pole")                            # A pitchfork.
    for sx in (-0.08, 0, 0.08):
        beam(mb, (1.8 + sx, -0.5, 0.0), (1.8 + sx, -0.52, 0.3), 0.012, "iron")
    mb.cylinder((1.7, 0.4, 0), (1.7, 0.4, 0.3), 0.16, 0.2, "plank_light", segments=8)
    mb.sphere((1.7, 0.4, 0.32), 0.17, "leaf", segments=6, rings=3, scale=(1, 1, 0.5))
    kit.save(mb, FAMILY, "annex_compost_bin", COLORS)


def grindstone():
    mb = kit.begin()
    for sx in (-1, 1):
        beam(mb, (sx * 0.22, -0.5, 0.0), (sx * 0.22, -0.3, 0.85), 0.04, "pole")
        beam(mb, (sx * 0.22, 0.5, 0.0), (sx * 0.22, 0.3, 0.85), 0.04, "pole")
        beam(mb, (sx * 0.22, -0.4, 0.85), (sx * 0.22, 0.4, 0.85), 0.045, "pole_dark")
    w = {"stone": 1.0}
    mb.cylinder((-0.09, 0, 0.9), (0.09, 0, 0.9), 0.42, 0.42, "stone_light", w, segments=12)
    mb.cylinder((-0.1, 0, 0.9), (0.1, 0, 0.9), 0.12, 0.12, "stone_dark", w, segments=8)
    mb.cylinder((-0.4, 0, 0.9), (0.4, 0, 0.9), 0.025, 0.025, "iron", w, segments=6)
    beam(mb, (0.4, 0, 0.9), (0.4, 0.2, 0.9), 0.02, "iron", w)
    mb.cylinder((0.4, 0.2, 0.9), (0.55, 0.2, 0.9), 0.03, 0.03, "pole", w, segments=6)
    mb.box((0, 0, 0.38), (0.36, 0.7, 0.2), "plank_dark")                                    # The water trough under the stone.
    mb.box((0, 0, 0.47), (0.3, 0.64, 0.03), "water")
    mb.cylinder((0.8, -0.4, 0), (0.8, -0.4, 0.3), 0.14, 0.18, "plank_light", segments=8)
    beam(mb, (-0.7, -0.3, 0.0), (-0.45, 0.2, 0.9), 0.02, "pole")                            # An axe waiting its turn.
    mb.box((-0.7, -0.3, 0.1), (0.05, 0.2, 0.16), "steel", rotation_z=0.5)
    mb.cylinder((-0.8, 0.4, 0.0), (-0.3, 0.6, 0.03), 0.015, 0.025, "steel", segments=4)
    pose = lambda t: ({"stone": [(kit.X, 360 * t)]}, {})   # noqa: E731
    kit.save(mb, FAMILY, "annex_grindstone", COLORS, mech=kit.Mech([("stone", (0, 0, 0.9), (0.4, 0, 0.9), None)]).clip("turn", 2.0, pose))


def dye_vats():
    mb = kit.begin()
    mb.box((0, 0, 0.1), (3.2, 1.3, 0.2), "stone_dark")
    for k, mat in enumerate(("dye_red", "dye_blue", "dye_yellow")):
        x = -1.0 + 1.0 * k
        mb.cylinder((x, 0, 0.2), (x, 0, 0.85), 0.38, 0.45, "plank", segments=10)
        for z in (0.35, 0.7):
            mb.cylinder((x, 0, z), (x, 0, z + 0.05), 0.44, 0.44, "iron", segments=10)
        mb.cylinder((x, 0, 0.8), (x, 0, 0.84), 0.4, 0.4, mat, segments=10)
    beam(mb, (-1.0, 0.1, 0.5), (-0.7, -0.4, 1.6), 0.025, "pole")
    for sx in (-1.7, 1.7):
        mb.cylinder((sx, 1.1, 0), (sx, 1.1, 2.0), 0.05, 0.05, "pole", segments=6)
    beam(mb, (-1.8, 1.1, 1.95), (1.8, 1.1, 1.95), 0.03, "pole_dark")
    bones = []
    for i, mat in enumerate(("dye_red", "dye_blue", "dye_yellow", "linen", "dye_blue", "dye_red")):
        b = "cloth%d" % i
        x = -1.4 + 0.56 * i
        solid(mb, [(x - 0.22, 1.1, 1.93), (x + 0.22, 1.1, 1.93), (x + 0.22, 1.1, 0.75 + 0.1 * (i % 3)), (x - 0.22, 1.1, 0.75 + 0.1 * (i % 3))], (0, 0.025, 0), mat, {b: 1.0})
        bones.append((b, (x, 1.1, 1.95), (x, 1.1, 1.3), None))
    for k, mat in enumerate(("dye_red", "dye_yellow")):
        sack(mb, 1.9, -0.3 + 0.5 * k, 0.0, 0.2)
        mb.sphere((1.9, -0.3 + 0.5 * k, 0.36), 0.08, mat, segments=5, rings=3)

    def sway(t):
        return {"cloth%d" % i: [(kit.X, 8 * math.sin(TAU * t + i * 0.9))] for i in range(6)}, {}

    kit.save(mb, FAMILY, "annex_dye_vats", COLORS, mech=kit.Mech(bones).clip("sway", 3.0, sway))


def garden_table():
    mb = kit.begin()
    mb.box((0, 0, 0.78), (2.6, 0.9, 0.07), "plank")
    for k in range(4):
        mb.box((-0.97 + 0.65 * k, 0, 0.82), (0.6, 0.86, 0.02), "plank_light" if k % 2 else "plank")
    for sx in (-1.0, 1.0):
        beam(mb, (sx, -0.35, 0), (sx, 0.35, 0.75), 0.04, "pole_dark")
        beam(mb, (sx, 0.35, 0), (sx, -0.35, 0.75), 0.04, "pole_dark")
    for sy in (-0.85, 0.85):
        mb.box((0, sy, 0.45), (2.4, 0.32, 0.06), "plank")
        for sx in (-0.9, 0.9):
            mb.box((sx, sy, 0.22), (0.08, 0.28, 0.44), "plank_dark")
    mb.box((0, 0, 0.845), (0.9, 0.5, 0.012), "linen")
    mb.sphere((-0.2, 0.05, 0.92), 0.14, "bread", segments=6, rings=4, scale=(1.4, 0.9, 0.6))
    for x, y in ((0.3, -0.2), (-0.8, 0.2), (0.9, 0.15)):
        mb.cylinder((x, y, 0.84), (x, y, 0.97), 0.05, 0.055, "clay", segments=7)
    mb.cylinder((0.5, 0.15, 0.84), (0.5, 0.15, 0.9), 0.16, 0.2, "clay", segments=8)
    for k in range(4):
        mb.sphere((0.45 + 0.05 * k, 0.12 + 0.03 * (k % 2), 0.93), 0.05, "cloth_red" if k % 2 else "flowers_y", segments=5, rings=3)
    mb.cylinder((-0.75, -0.2, 0.84), (-0.75, -0.2, 1.1), 0.07, 0.04, "clay_dark", segments=7)     # A jug.
    for sx in (-1.5, 1.5):                                                                         # A string of lanterns overhead.
        mb.cylinder((sx, 0, 0), (sx, 0, 2.4), 0.05, 0.045, "pole", segments=6)
    rope(mb, (-1.5, 0, 2.35), (0, 0, 2.15), 0.012)
    rope(mb, (0, 0, 2.15), (1.5, 0, 2.35), 0.012)
    for x, z in ((-0.9, 2.2), (-0.3, 2.12), (0.3, 2.12), (0.9, 2.2)):
        mb.box((x, 0, z - 0.1), (0.1, 0.1, 0.14), "window")
        mb.box((x, 0, z - 0.02), (0.12, 0.12, 0.03), "iron")
    kit.save(mb, FAMILY, "annex_garden_table", COLORS)


MODELS = {
    "annex_clothesline": clothesline("annex_clothesline", ("linen", "linen_shade", "linen")),
    "annex_clothesline_color": clothesline("annex_clothesline_color", ("cloth_red", "linen", "cloth_blue", "cloth_yellow", "cloth_green")),
    "annex_woodshed": woodshed("annex_woodshed", False),
    "annex_woodshed_stone": woodshed("annex_woodshed_stone", True),
    "annex_outhouse": outhouse("annex_outhouse", False),
    "annex_outhouse_brick": outhouse("annex_outhouse_brick", True),
    "annex_rain_barrel": rain_barrel,
    "annex_root_cellar": root_cellar,
    "annex_pigsty": pigsty,
    "annex_rabbit_hutch": rabbit_hutch,
    "annex_bread_oven": bread_oven("annex_bread_oven", False),
    "annex_bread_oven_brick": bread_oven("annex_bread_oven_brick", True),
    "annex_porch": porch,
    "annex_tool_shed": tool_shed,
    "annex_spinning_wheel": spinning_wheel,
    "annex_cart_shed": cart_shed,
    "annex_playground_swing": playground("annex_playground_swing", "swing"),
    "annex_playground_seesaw": playground("annex_playground_seesaw", "seesaw"),
    "annex_home_shrine": home_shrine("annex_home_shrine", False),
    "annex_home_shrine_stone": home_shrine("annex_home_shrine_stone", True),
    "annex_compost_bin": compost_bin,
    "annex_grindstone": grindstone,
    "annex_dye_vats": dye_vats,
    "annex_garden_table": garden_table,
}

kit.run(MODELS, FAMILY)
