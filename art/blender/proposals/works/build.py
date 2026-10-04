"""Building works proposals: the cranes, scaffolds and yards a town puts up
while it builds. See ../LEEME.md.

    blender --background --factory-startup --python art/blender/proposals/works/build.py -- [ids]
"""

import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import _kit as kit  # noqa: E402
import _shapes  # noqa: E402
import common  # noqa: E402
from _shapes import TAU, barrel, beam, crate, log, rock, rope, shed_roof, solid, wheel  # noqa: E402

FAMILY = "works"
C = common.rgb
COLORS = {
    **_shapes.COLORS,
    "brick": C(0xA0553A), "brick_dark": C(0x84422C), "brick_raw": C(0xB88A62), "clay": C(0x9A6A48), "lime": C(0xECE8DC), "sand": C(0xD8C088),
    "soil": C(0x6A4A30), "grass": C(0x6A9440), "cave": C(0x14110F), "sawdust": C(0xE0C690), "shingle": C(0x6A5038), "shingle_dark": C(0x54402C),
    "thatch": C(0xC9A55A), "thatch_dark": C(0xA8863F), "flame": C(0xF2A23A), "ember": C(0xD8502A), "charcoal": C(0x2A2624), "water": C(0x4A8FC0),
    "paint_red": C(0xB8362E), "paint_white": C(0xECE6D6), "parchment": C(0xE6D8B0), "ink": C(0x2E2A26), "cobble": C(0x8A8680), "cobble_dark": C(0x6E6A64),
}


def phase(t, a, b):
    """0 before a, 1 after b, eased in between."""
    return kit.smooth(min(1.0, max(0.0, (t - a) / (b - a))))


def hoist(mb, x, y, top, low, bone, r=0.014, still=None):
    """A rope that seems to shorten: its upper half hangs still and the lower
    half rides up into it with the load. Returns how far the load may rise."""
    mid = (top + low) / 2
    rope(mb, (x, y, top), (x, y, mid), r, still)
    rope(mb, (x, y, mid), (x, y, low), r * 0.96, {bone: 1.0})
    return top - mid


def ladder(mb, a, b, half=0.2):
    """A ladder between the middles of its two ends."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    flat = math.hypot(dx, dy)
    nx, ny = (1.0, 0.0) if flat < 1e-6 else (-dy / flat, dx / flat)
    for s in (-1, 1):
        beam(mb, (a[0] + nx * half * s, a[1] + ny * half * s, a[2]), (b[0] + nx * half * s, b[1] + ny * half * s, b[2]), 0.035, "pole")
    n = max(2, int(math.dist(a, b) / 0.38))
    for k in range(n):
        u = (k + 0.5) / n
        p = [a[i] + (b[i] - a[i]) * u for i in range(3)]
        beam(mb, (p[0] - nx * half, p[1] - ny * half, p[2]), (p[0] + nx * half, p[1] + ny * half, p[2]), 0.022, "pole_dark")


def deck(mb, x0, x1, y0, y1, z, mats=("plank", "plank_light"), weights=None):
    n = max(1, round((y1 - y0) / 0.3))
    for k in range(n):
        mb.box(((x0 + x1) / 2, y0 + (y1 - y0) * (k + 0.5) / n, z), (x1 - x0, (y1 - y0) / n - 0.02, 0.05), mats[k % len(mats)], weights)


def ashlar(mb, x, y, z, rnd, cols=3, rows=2, layers=2):
    """A neat stack of dressed blocks."""
    for l in range(layers):
        for i in range(cols):
            for j in range(rows):
                if l == layers - 1 and rnd.random() < 0.3:
                    continue
                mb.box((x + 0.52 * i, y + 0.36 * j, z + 0.14 + 0.28 * l), (0.5, 0.34, 0.27), rnd.choice(("stone", "stone_light", "stone_light")))


def windlass(mb, x, y, z, half, bone, along_x=True):
    """A drum between two posts with a crank at its end."""
    w = {bone: 1.0}
    ax = (1, 0) if along_x else (0, 1)
    for s in (-1, 1):
        mb.box((x + ax[0] * s * half, y + ax[1] * s * half, z / 2 + 0.1), (0.14, 0.14, z + 0.2), "pole")
    a = (x - ax[0] * (half + 0.3), y - ax[1] * (half + 0.3), z)
    b = (x + ax[0] * (half + 0.3), y + ax[1] * (half + 0.3), z)
    mb.cylinder(a, b, 0.035, 0.035, "iron", w, segments=6)
    mb.cylinder((x - ax[0] * (half - 0.12), y - ax[1] * (half - 0.12), z), (x + ax[0] * (half - 0.12), y + ax[1] * (half - 0.12), z), 0.12, 0.12, "plank_dark", w, segments=8)
    mb.cylinder((x - ax[0] * 0.15, y - ax[1] * 0.15, z), (x + ax[0] * 0.15, y + ax[1] * 0.15, z), 0.14, 0.14, "rope", w, segments=8)
    for s in (-1, 1):   # A crank at each end, a quarter turn apart.
        e = (x + ax[0] * s * (half + 0.3), y + ax[1] * s * (half + 0.3), z)
        tip = (e[0], e[1], e[2] + 0.3) if s > 0 else (e[0] + ax[1] * 0.3, e[1] + ax[0] * 0.3, e[2])
        beam(mb, e, tip, 0.022, "iron", w)
        mb.cylinder(tip, (tip[0] + ax[0] * s * 0.28, tip[1] + ax[1] * s * 0.28, tip[2]), 0.03, 0.03, "pole", w, segments=6)
    return (bone, (x, y, z), (x + ax[0] * 0.5, y + ax[1] * 0.5, z), None)


def treadwheel_crane():
    """The great crane of a cathedral yard: men walk inside the wheel."""
    mb = kit.begin()
    rnd = random.Random(3)
    for sx in (-1.5, 1.5):
        beam(mb, (sx, -1.8, 0.12), (sx, 3.8, 0.12), 0.14, "pole_dark")
    for y in (-1.6, 0.0, 3.6):
        beam(mb, (-1.7, y, 0.22), (1.7, y, 0.22), 0.12, "pole_dark")
    mb.box((0, 0, 3.3), (0.32, 0.32, 6.2), "pole")
    for sx in (-1.5, 1.5):
        beam(mb, (sx, 0, 0.3), (0, 0, 3.8), 0.09, "pole_dark")
    beam(mb, (0, 3.6, 0.3), (0, 0.1, 4.8), 0.09, "pole_dark")
    beam(mb, (0, 0.7, 5.5), (0, -3.3, 7.7), 0.13, "pole")                       # The jib and its strut.
    beam(mb, (0, -0.1, 4.0), (0, -2.0, 6.95), 0.08, "pole_dark")
    mb.box((0, 0, 6.45), (0.4, 0.4, 0.14), "iron")
    mb.cylinder((-0.09, -3.2, 7.5), (0.09, -3.2, 7.5), 0.17, 0.17, "plank_dark", segments=8)
    mb.cylinder((-0.29, 0.6, 5.72), (-0.11, 0.6, 5.72), 0.15, 0.15, "plank_dark", segments=8)
    for x in (-1.0, 1.45):                                                      # The wheel stands behind the mast.
        mb.box((x, 2.0, 1.1), (0.18, 0.24, 2.0), "pole")
        beam(mb, (x, 3.4, 0.3), (x, 2.1, 1.7), 0.06, "pole_dark")
        beam(mb, (x, 0.6, 0.3), (x, 1.9, 1.7), 0.06, "pole_dark")
    w = {"wheel": 1.0}
    for x in (0.0, 1.2):
        wheel(mb, (x, 2.0, 2.0), 1.6, "wheel", 0.1, "plank", "plank_dark")
    for i in range(22):
        a = TAU * i / 22
        beam(mb, (0.0, 2.0 + math.cos(a) * 1.56, 2.0 + math.sin(a) * 1.56), (1.2, 2.0 + math.cos(a) * 1.56, 2.0 + math.sin(a) * 1.56), 0.07, "plank_light" if i % 2 else "plank", w)
    mb.cylinder((-0.95, 2.0, 2.0), (1.4, 2.0, 2.0), 0.11, 0.11, "pole_dark", w, segments=8)
    mb.cylinder((-0.75, 2.0, 2.0), (-0.25, 2.0, 2.0), 0.2, 0.2, "rope", w, segments=8)
    rope(mb, (-0.5, 2.0, 2.18), (-0.2, 0.6, 5.86), 0.018)
    rope(mb, (-0.2, 0.6, 5.86), (0, -3.2, 7.66), 0.018)
    travel = hoist(mb, 0, -3.2, 7.4, 0.95, "load", 0.018)
    wl = {"load": 1.0}
    mb.box((0, -3.2, 0.3), (1.0, 0.7, 0.6), "stone_light", wl)
    for sx in (-1, 1):
        rope(mb, (sx * 0.5, -3.2, 0.6), (0, -3.2, 0.97), 0.012, wl)
        rope(mb, (sx * 0.5, -3.2, 0.0), (sx * 0.5, -3.2, 0.6), 0.012, wl)
    mb.box((0, -3.2, 0.97), (0.08, 0.08, 0.1), "iron", wl)
    ashlar(mb, 2.2, -3.0, 0.0, rnd, 3, 2, 3)
    ladder(mb, (-1.9, 1.4, 0), (-1.2, 2.0, 2.0))

    def lift(t):
        s = 0.5 - 0.5 * math.cos(TAU * t)
        return {"wheel": [(kit.X, 540.0 * s)]}, {"load": (0, 0, travel * s)}

    mech = kit.Mech([("wheel", (0.6, 2.0, 2.0), (1.1, 2.0, 2.0), None), ("load", (0, -3.2, 0.95), (0, -3.2, 0.3), None)]).clip("lift", 12.0, lift)
    kit.save(mb, FAMILY, "works_crane_treadwheel", COLORS, mech=mech)


def sheerlegs():
    """Three poles lashed at the top with a windlass: the crane of a village."""
    mb = kit.begin()
    top = (0, 0, 5.2)
    for a in (90, 210, 330):
        log(mb, (math.cos(math.radians(a)) * 2.2, math.sin(math.radians(a)) * 2.2, 0), top, 0.1)
    mb.cylinder((0, 0, 4.95), (0, 0, 5.2), 0.2, 0.17, "rope", segments=8)
    mb.cylinder((-0.07, 0, 4.7), (0.07, 0, 4.7), 0.14, 0.14, "plank_dark", segments=8)
    rope(mb, (0, 0, 4.95), (0, 0, 4.8), 0.02)
    bone = windlass(mb, 0, 1.5, 1.0, 0.45, "crank")
    rope(mb, (0, 1.5, 1.14), (0, 0.05, 4.8), 0.014)
    travel = hoist(mb, 0, 0, 4.6, 0.75, "load")
    wl = {"load": 1.0}
    beam(mb, (-1.9, 0, 0.3), (1.9, 0, 0.3), 0.16, "plank", wl)                  # A roof beam going up.
    for sx in (-1, 1):
        rope(mb, (sx * 1.0, 0, 0.42), (0, 0, 0.77), 0.012, wl)
        mb.cylinder((sx * 1.0, -0.13, 0.3), (sx * 1.0, 0.13, 0.3), 0.125, 0.125, "rope", wl, segments=6)

    def lift(t):
        s = 0.5 - 0.5 * math.cos(TAU * t)
        return {"crank": [(kit.X, 720.0 * s)]}, {"load": (0, 0, min(travel, 1.9) * s)}

    kit.save(mb, FAMILY, "works_sheerlegs", COLORS, mech=kit.Mech([bone, ("load", (0, 0, 0.75), (0, 0, 0.3), None)]).clip("lift", 8.0, lift))


def scaffold(name, levels, with_hoist=False):
    """A 4 m bay of pole scaffold; the wall it serves stands behind it (+Y)."""
    def build():
        mb = kit.begin()
        rnd = random.Random(levels)
        depth, step = 1.3, 2.0
        top = levels * step
        xs = (-1.9, 0.0, 1.9)
        for x in xs:
            for y in (-depth / 2, depth / 2):
                mb.cylinder((x, y, 0), (x, y, top + 1.15), 0.055, 0.045, "pole", segments=6)
        for lv in range(1, levels + 1):
            z = lv * step
            for y in (-depth / 2, depth / 2):
                beam(mb, (-2.0, y, z - 0.1), (2.0, y, z - 0.1), 0.04, "pole_dark")
            for x in xs:
                beam(mb, (x, -depth / 2 - 0.1, z - 0.03), (x, depth / 2 + 0.3, z - 0.03), 0.04, "pole_dark")   # The putlogs reach into the wall.
                for y in (-depth / 2, depth / 2):
                    mb.cylinder((x, y, z - 0.17), (x, y, z + 0.02), 0.075, 0.075, "rope", segments=6)
            deck(mb, -2.0, 2.0, -depth / 2 + 0.06, depth / 2 - 0.06, z + 0.03)
            beam(mb, (-2.0, -depth / 2, z + 1.0), (2.0, -depth / 2, z + 1.0), 0.03, "pole")
        for lv in range(levels):
            s = 1 if lv % 2 == 0 else -1
            beam(mb, (-1.9 * s, -depth / 2 - 0.06, lv * step + 0.1), (0, -depth / 2 - 0.06, (lv + 1) * step - 0.15), 0.03, "pole_dark")
            beam(mb, (0, -depth / 2 - 0.06, lv * step + 0.1), (1.9 * s, -depth / 2 - 0.06, (lv + 1) * step - 0.15), 0.03, "pole_dark")
            x0, x1 = (0.5, 1.5) if lv % 2 == 0 else (-0.5, -1.5)
            ladder(mb, (x0, 0.25, lv * step + 0.06), (x1, 0.25, (lv + 1) * step + 0.75), 0.18)
        mb.cylinder((-1.2, -0.2, top + 0.06), (-1.2, -0.2, top + 0.34), 0.13, 0.16, "plank_light", segments=8)   # What the masons left up there.
        mb.cylinder((-1.2, -0.2, top + 0.3), (-1.2, -0.2, top + 0.33), 0.14, 0.14, "lime", segments=8)
        for k in range(4):
            mb.box((-0.5 + 0.3 * (k % 2), 0.3, top + 0.13 + 0.14 * (k // 2)), (0.28, 0.2, 0.13), rnd.choice(("stone", "stone_light")))
        mech = None
        if with_hoist:
            beam(mb, (1.9, depth / 2, top + 1.05), (1.9, -depth / 2 - 1.1, top + 1.05), 0.05, "pole")
            mb.cylinder((1.83, -depth / 2 - 0.95, top + 0.9), (1.97, -depth / 2 - 0.95, top + 0.9), 0.12, 0.12, "plank_dark", segments=8)
            rope(mb, (1.9, -depth / 2 - 0.95, top + 1.05), (1.9, -depth / 2 - 0.95, top + 0.95), 0.014)
            travel = hoist(mb, 1.9, -depth / 2 - 0.95, top + 0.8, 0.75, "load")
            wl = {"load": 1.0}
            mb.cylinder((1.9, -depth / 2 - 0.95, 0.1), (1.9, -depth / 2 - 0.95, 0.5), 0.26, 0.32, "rope", wl, segments=8)     # A basket of stone.
            for k in range(5):
                a = TAU * k / 5
                mb.box((1.9 + math.cos(a) * 0.14, -depth / 2 - 0.95 + math.sin(a) * 0.14, 0.52), (0.18, 0.16, 0.14), "stone_light" if k % 2 else "stone", wl, rotation_z=a)
            for sx in (-1, 1):
                rope(mb, (1.9 + sx * 0.3, -depth / 2 - 0.95, 0.5), (1.9, -depth / 2 - 0.95, 0.77), 0.01, wl)
            rope(mb, (1.9, -depth / 2 - 1.1, top + 0.95), (2.3, -depth / 2 - 1.6, 0.9), 0.012)                               # The fall a man pulls from the ground.

            def lift(t):
                s = 0.5 - 0.5 * math.cos(TAU * t)
                return {}, {"load": (0, 0, travel * s)}

            mech = kit.Mech([("load", (1.9, -depth / 2 - 0.95, 0.75), (1.9, -depth / 2 - 0.95, 0.1), None)]).clip("lift", 7.0, lift)
        kit.save(mb, FAMILY, name, COLORS, mech=mech)
    return build


def sawpit():
    """A log on tall trestles and the long saw two men pull through it."""
    mb = kit.begin()
    for x in (-1.6, 1.6):
        for sy in (-1, 1):
            beam(mb, (x - 0.4, sy * 0.95, 0), (x, sy * 0.45, 2.1), 0.07, "pole_dark")
            beam(mb, (x + 0.4, sy * 0.95, 0), (x, sy * 0.45, 2.1), 0.07, "pole_dark")
        beam(mb, (x, -0.8, 2.1), (x, 0.8, 2.1), 0.09, "pole")
    log(mb, (-2.6, 0, 2.42), (0.62, 0, 2.42), 0.26)
    for k, sy in enumerate((-0.17, -0.06, 0.06, 0.17)):                           # The end already sawn into boards.
        mb.box((1.65, sy, 2.42), (2.06, 0.09, 0.44 - 0.1 * abs(k - 1.5)), "plank_light" if k % 2 else "log_end")
    mb.box((-0.3, 0.5, 2.24), (3.2, 0.3, 0.05), "plank_light")
    w = {"saw": 1.0}
    mb.box((0.62, 0, 2.05), (0.02, 0.15, 2.3), "steel", w)
    for z in (3.25, 0.85):
        beam(mb, (0.62, -0.28, z), (0.62, 0.28, z), 0.028, "pole", w)
        mb.box((0.62, 0, z), (0.05, 0.08, 0.12), "iron", w)
    mb.sphere((0.62, 0, 0.0), 0.75, "sawdust", segments=8, rings=4, scale=(1.1, 0.9, 0.28))
    for layer in range(5):                                                       # Boards stacked on stickers to season.
        for k in range(4):
            if layer == 4 and k > 1:
                continue
            mb.box((-0.2, -2.6 + 0.31 * k, 0.16 + 0.11 * layer), (3.6, 0.28, 0.05), "plank_light" if (layer + k) % 2 else "plank")
        for x in (-1.6, -0.2, 1.2):
            mb.box((x, -2.14, 0.105 + 0.11 * layer), (0.06, 1.24, 0.05), "plank_dark")
    log(mb, (-2.2, 2.1, 0.26), (2.2, 2.1, 0.26), 0.26)
    log(mb, (-2.0, 2.66, 0.24), (2.3, 2.66, 0.24), 0.24)
    log(mb, (-2.1, 2.38, 0.7), (2.1, 2.38, 0.7), 0.23)
    ladder(mb, (-2.2, -1.2, 0), (-1.75, -0.5, 2.3))
    pose = lambda t: ({}, {"saw": (0, 0, 0.38 * math.sin(TAU * t))})   # noqa: E731
    kit.save(mb, FAMILY, "works_sawpit", COLORS, mech=kit.Mech([("saw", (0.62, 0, 3.25), (0.62, 0, 0.85), None)]).clip("saw", 1.4, pose))


def stonecutter():
    """The banker where a mason dresses blocks, under a lean-to."""
    mb = kit.begin()
    rnd = random.Random(8)
    for sx in (-1.9, 1.9):
        mb.cylinder((sx, -1.2, 0), (sx, -1.2, 2.3), 0.08, 0.07, "pole", segments=6)
        mb.cylinder((sx, 1.2, 0), (sx, 1.2, 2.9), 0.08, 0.07, "pole", segments=6)
    shed_roof(mb, 0, 0, 3.8, 2.4, 2.3, 2.9, ("shingle", "shingle_dark"), 0.3, 3)
    mb.box((0, 0, 0.35), (0.9, 0.7, 0.7), "stone_dark")                          # The banker and the block on it.
    mb.box((0, 0, 0.95), (0.7, 0.5, 0.5), "stone_light")
    mb.box((0.2, -0.13, 1.21), (0.3, 0.24, 0.03), "stone")
    mb.cylinder((-0.2, 0.1, 1.2), (-0.2, 0.1, 1.34), 0.07, 0.07, "pole", segments=6)                # A mallet and chisels.
    mb.cylinder((-0.32, 0.1, 1.27), (-0.08, 0.1, 1.27), 0.02, 0.02, "pole_dark", segments=5)
    for k in range(3):
        beam(mb, (0.1 + 0.08 * k, 0.15, 1.21), (0.14 + 0.08 * k, -0.05, 1.21), 0.012, "steel")
    for _ in range(26):
        mb.box((rnd.uniform(-1.0, 1.0), rnd.uniform(-0.9, 0.7), 0.025), (rnd.uniform(0.05, 0.12), rnd.uniform(0.04, 0.1), 0.05), rnd.choice(("stone", "stone_light")), rotation_z=rnd.uniform(0, 3))
    ashlar(mb, 0.9, 0.5, 0.0, rnd, 2, 2, 3)
    for k in range(5):                                                           # Arch stones cut to a template.
        a0, a1 = math.pi * 0.2 * k, math.pi * 0.2 * (k + 1)
        solid(mb, [(-2.9 + math.cos(a0) * 0.6, -0.6, math.sin(a0) * 0.6), (-2.9 + math.cos(a0) * 0.95, -0.6, math.sin(a0) * 0.95),
                   (-2.9 + math.cos(a1) * 0.95, -0.6, math.sin(a1) * 0.95), (-2.9 + math.cos(a1) * 0.6, -0.6, math.sin(a1) * 0.6)], (0, 0.4, 0),
              "stone_light" if k % 2 else "stone")
    for k in range(3):                                                           # Templates hung at the back.
        mb.box((-1.2 + 0.7 * k, 1.12, 1.7), (0.45, 0.02, 0.5 - 0.1 * k), "plank_light")
    beam(mb, (-1.9, 1.2, 2.0), (1.9, 1.2, 2.0), 0.04, "pole_dark")
    for _ in range(4):
        rock(mb, rnd.uniform(1.6, 2.6), rnd.uniform(-1.9, -0.9), 0.25, rnd.uniform(0.3, 0.5), rnd)
    mb.cylinder((1.4, 0.2, 0.9), (1.4, 0.2, 0.9 + 0.5), 0.02, 0.02, "iron", segments=5)
    kit.save(mb, FAMILY, "works_stonecutter", COLORS)


def mortar_pit():
    mb = kit.begin()
    rnd = random.Random(4)
    mb.box((0, 0, 0.14), (2.4, 1.8, 0.28), "plank_dark")
    mb.box((0, 0, 0.22), (2.16, 1.56, 0.16), "lime")
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.box((sx * 1.2, sy * 0.9, 0.22), (0.1, 0.1, 0.5), "pole_dark")
    beam(mb, (0.3, 0.2, 0.3), (1.3, -1.4, 1.5), 0.025, "pole")                     # A hoe left in the mix.
    mb.box((0.3, 0.2, 0.32), (0.3, 0.05, 0.2), "iron", rotation_z=0.6)
    mb.sphere((-2.4, 0.2, 0.0), 1.0, "sand", segments=9, rings=5, scale=(1.1, 1.0, 0.55))
    mb.sphere((-0.3, 2.0, 0.0), 0.8, "lime", segments=8, rings=5, scale=(1.2, 0.9, 0.45))
    for k in range(5):
        rock(mb, -0.9 + 0.3 * k + rnd.uniform(-0.1, 0.1), 2.0 + rnd.uniform(-0.3, 0.3), 0.3, 0.16, rnd, "lime")
    for sx in (-0.35, 0.35):                                                      # A sieve leaning on its prop.
        beam(mb, (-2.2 + sx, -1.9, 0), (-2.2 + sx, -1.3, 1.2), 0.03, "pole")
    beam(mb, (-2.55, -1.9, 0.02), (-1.85, -1.9, 0.02), 0.03, "pole")
    beam(mb, (-2.55, -1.3, 1.2), (-1.85, -1.3, 1.2), 0.03, "pole")
    solid(mb, [(-2.52, -1.88, 0.05), (-1.88, -1.88, 0.05), (-1.88, -1.32, 1.17), (-2.52, -1.32, 1.17)], (0, 0.01, 0.005), "iron")
    beam(mb, (-2.2, -1.3, 1.2), (-2.2, -0.75, 0), 0.025, "pole_dark")
    barrel(mb, 1.9, 1.2, 0.0, 0.9, 0.34)
    mb.cylinder((1.9, 1.2, 0.86), (1.9, 1.2, 0.9), 0.27, 0.27, "water", segments=10)
    barrel(mb, 2.5, 0.6, 0.0, 0.9, 0.34)
    for x, y in ((1.6, -1.0), (2.0, -0.6)):
        mb.cylinder((x, y, 0), (x, y, 0.3), 0.13, 0.17, "plank_light", segments=8)
        mb.cylinder((x, y, 0.26), (x, y, 0.29), 0.15, 0.15, "lime", segments=8)
    solid(mb, [(0.6, -1.7, 0.25), (1.2, -1.7, 0.25), (1.2, -1.7, 0.55), (0.6, -1.7, 0.45)], (0, 0.35, 0), "plank")      # A hod.
    beam(mb, (0.9, -1.5, 0.3), (0.9, -1.5, 0.0), 0.03, "pole")
    kit.save(mb, FAMILY, "works_mortar_pit", COLORS)


def lime_kiln():
    mb = kit.begin()
    rnd = random.Random(5)
    mb.cylinder((0, 0, 0), (0, 0, 3.0), 1.9, 1.5, "stone", segments=12)
    mb.cylinder((0, 0, 3.0), (0, 0, 3.2), 1.62, 1.56, "stone_light", segments=12)
    mb.cylinder((0, 0, 3.16), (0, 0, 3.23), 1.15, 1.15, "ember", segments=12)
    for k in range(14):
        a = rnd.uniform(0.2, TAU - 0.2) + math.pi / 2
        z = rnd.uniform(0.4, 2.7)
        r = 1.9 - 0.4 * z / 3.0
        mb.box((math.cos(a) * r, math.sin(a) * r, z), (0.5, 0.12, 0.26), rnd.choice(("stone_dark", "stone_light")), rotation_z=a + math.pi / 2)
    mb.box((0, -1.75, 0.6), (1.1, 0.6, 1.2), "stone_dark")                       # The draw arch.
    mb.box((0, -1.8, 1.26), (1.3, 0.7, 0.14), "stone_light")
    mb.box((0, -2.06, 0.5), (0.7, 0.04, 0.9), "cave")
    mb.box((0, -2.07, 0.3), (0.56, 0.04, 0.4), "ember")
    mb.box((0, -2.08, 0.2), (0.36, 0.04, 0.2), "flame")
    mb.sphere((0, -2.7, 0.0), 0.5, "lime", segments=8, rings=4, scale=(1.2, 1.0, 0.4))
    solid(mb, [(-1.1, 1.2, 0), (-1.1, 5.4, 0), (-1.1, 1.2, 2.9)], (2.2, 0, 0), "soil")              # The ramp it is charged from.
    solid(mb, [(-0.8, 1.3, 2.92), (-0.8, 5.3, 0.06), (0.8, 5.3, 0.06), (0.8, 1.3, 2.92)], (0, 0, 0.05), "sand")
    for k in range(8):
        rock(mb, 2.6 + rnd.uniform(-0.7, 0.7), 0.8 + rnd.uniform(-0.8, 0.8), 0.2 + 0.25 * (k % 2), rnd.uniform(0.28, 0.45), rnd, "stone_light")
    for k in range(9):
        rock(mb, -2.6 + rnd.uniform(-0.6, 0.6), -0.6 + rnd.uniform(-0.6, 0.6), 0.12 + 0.2 * (k % 2), rnd.uniform(0.18, 0.3), rnd, "charcoal")
    w = {"fire": 1.0}
    for k in range(6):
        a = TAU * k / 6
        mb.cylinder((math.cos(a) * 0.55, math.sin(a) * 0.55, 3.2), (math.cos(a) * 0.4, math.sin(a) * 0.4, 3.75 + 0.3 * (k % 2)), 0.26, 0.0, "flame" if k % 2 else "ember", w, segments=5)
    mb.cylinder((0, 0, 3.2), (0, 0, 4.3), 0.3, 0.0, "flame", w, segments=5)
    pose = lambda t: ({"fire": [(kit.Z, 14.0 * math.sin(TAU * 2 * t))]}, {"fire": (0, 0, 0.07 * math.sin(TAU * 3 * t))})   # noqa: E731
    kit.save(mb, FAMILY, "works_lime_kiln", COLORS, mech=kit.Mech([("fire", (0, 0, 3.2), (0, 0, 4.2), None)]).clip("burn", 2.0, pose))


def brickyard():
    mb = kit.begin()
    rnd = random.Random(6)
    for layer in range(8):                                                       # The clamp: bricks stacked to be fired where they stand.
        inset = 0.06 * layer
        mb.box((1.2, 1.2, 0.11 + 0.22 * layer), (3.0 - inset * 2, 2.2 - inset * 2, 0.2), "brick" if layer % 2 else "brick_dark")
    mb.box((1.2, 1.2, 1.8), (2.3, 1.5, 0.08), "clay")
    for k in range(3):
        mb.box((0.3 + 0.9 * k, 0.08, 0.2), (0.3, 0.08, 0.3), "cave")
        mb.box((0.3 + 0.9 * k, 0.07, 0.12), (0.22, 0.06, 0.14), "flame" if k != 1 else "ember")
    w = {"smoke": 1.0}
    for k in range(4):
        mb.sphere((0.4 + 0.55 * k, 1.2 + 0.3 * (k % 2), 2.0 + 0.2 * (k % 2)), 0.22 + 0.05 * k, "lime", w, segments=6, rings=4)
    for row in range(3):                                                         # The hacks: raw bricks drying under thatch.
        y = -2.6 + 0.8 * row
        for layer in range(3):
            mb.box((-1.6, y, 0.08 + 0.15 * layer), (3.2, 0.34, 0.13), "brick_raw" if (layer + row) % 2 else "clay")
        solid(mb, [(-3.3, y - 0.3, 0.5), (0.1, y - 0.3, 0.5), (0.1, y, 0.66), (-3.3, y, 0.66)], (0, 0, 0.04), "thatch")
        solid(mb, [(-3.3, y + 0.3, 0.5), (0.1, y + 0.3, 0.5), (0.1, y, 0.66), (-3.3, y, 0.66)], (0, 0, 0.04), "thatch_dark")
    mb.box((1.8, -2.0, 0.75), (1.4, 0.7, 0.06), "plank")                         # The moulder's table.
    for sx in (-0.6, 0.6):
        for sy in (-0.28, 0.28):
            mb.box((1.8 + sx, -2.0 + sy, 0.36), (0.07, 0.07, 0.72), "pole_dark")
    mb.box((1.6, -2.0, 0.83), (0.3, 0.16, 0.1), "plank_light")
    mb.box((1.6, -2.0, 0.85), (0.24, 0.1, 0.08), "clay")
    mb.sphere((2.2, -2.0, 0.78), 0.2, "clay", segments=6, rings=4, scale=(1, 1, 0.6))
    mb.sphere((3.0, -1.2, 0.0), 0.7, "clay", segments=8, rings=5, scale=(1.1, 1.0, 0.5))
    mb.cylinder((2.7, -2.7, 0), (2.7, -2.7, 0.3), 0.13, 0.17, "plank_light", segments=8)
    for k in range(6):
        mb.box((3.2, 0.4 + 0.24 * k, 0.07 + 0.0 * k), (0.2, 0.1, 0.12), rnd.choice(("brick", "brick_dark")), rotation_z=rnd.uniform(-0.2, 0.2))
    pose = lambda t: ({}, {"smoke": (0.05 * math.sin(TAU * t), 0, 0.12 * math.sin(TAU * t))})   # noqa: E731
    kit.save(mb, FAMILY, "works_brickyard", COLORS, mech=kit.Mech([("smoke", (1.2, 1.2, 1.9), (1.2, 1.2, 2.6), None)]).clip("fire", 4.0, pose))


def frame(name, w, d, bays):
    """A timber frame half raised: what a house looks like before its walls."""
    def build():
        mb = kit.begin()
        post = 2.6
        plate = 0.4 + post
        for sx in (-1, 1):
            mb.box((sx * w / 2, 0, 0.12), (0.34, d + 0.34, 0.24), "stone")
            beam(mb, (sx * w / 2, -d / 2, 0.32), (sx * w / 2, d / 2, 0.32), 0.11, "plank")
        for sy in (-1, 1):
            mb.box((0, sy * d / 2, 0.12), (w + 0.34, 0.34, 0.24), "stone_dark")
            beam(mb, (-w / 2, sy * d / 2, 0.32), (w / 2, sy * d / 2, 0.32), 0.11, "plank")
        xs = [-w / 2 + w * k / bays for k in range(bays + 1)]
        for i, x in enumerate(xs):
            for sy in (-1, 1):
                mb.box((x, sy * d / 2, 0.4 + post / 2), (0.16, 0.16, post), "plank")
                if i < bays:
                    beam(mb, (x, sy * d / 2, plate - 0.9), (x + 0.8, sy * d / 2, plate), 0.05, "plank_dark")
                beam(mb, (x, sy * d / 2, plate - 0.8), (x, sy * (d / 2 - 0.75), plate), 0.05, "plank_dark")
            beam(mb, (x, -d / 2, plate), (x, d / 2, plate), 0.1, "plank_dark")
        for sy in (-1, 1):
            beam(mb, (-w / 2 - 0.12, sy * d / 2, plate + 0.06), (w / 2 + 0.12, sy * d / 2, plate + 0.06), 0.1, "plank")
            for i in range(bays):                                                # Rails where the wattle will go.
                beam(mb, (xs[i], sy * d / 2, 0.4 + post * 0.5), (xs[i + 1], sy * d / 2, 0.4 + post * 0.5), 0.045, "plank_light")
        rise = d * 0.48
        done = max(1, (bays + 1) * 2 // 3)
        for x in xs[:done]:
            for sy in (-1, 1):
                beam(mb, (x, sy * (d / 2 + 0.3), plate - 0.1), (x, 0, plate + rise), 0.06, "plank_light")
            beam(mb, (x, 0, plate), (x, 0, plate + rise), 0.06, "plank_dark")
            beam(mb, (x, -d * 0.25, plate + rise * 0.5), (x, d * 0.25, plate + rise * 0.5), 0.045, "plank_dark")
        beam(mb, (xs[0] - 0.15, 0, plate + rise), (xs[done - 1] + 0.15, 0, plate + rise), 0.07, "plank")
        if done > 1:
            for k in range(3):                                                   # The first battens.
                u = 0.25 + 0.25 * k
                beam(mb, (xs[0] - 0.1, d / 2 * (1 - u) + 0.05, plate + rise * u + 0.07), (xs[done - 1] + 0.1, d / 2 * (1 - u) + 0.05, plate + rise * u + 0.07), 0.03, "plank_light")
        for k in range(6):
            beam(mb, (w / 2 + 0.7 + 0.15 * k, -d / 2, 0.07 + 0.12 * (k % 2)), (w / 2 + 0.7 + 0.15 * k, d / 2 - 0.4, 0.07 + 0.12 * (k % 2)), 0.06, "plank_light")
        ladder(mb, (xs[done - 1] + 0.6, -d / 2 - 1.1, 0), (xs[done - 1] + 0.6, -d / 2 - 0.1, plate + 0.5))
        mb.cylinder((-w / 2 - 0.7, -d / 2 + 0.3, 0), (-w / 2 - 0.7, -d / 2 + 0.3, 0.3), 0.15, 0.19, "plank_light", segments=8)
        for k in range(8):
            mb.cylinder((-w / 2 - 0.75 + 0.04 * (k % 3), -d / 2 + 0.26 + 0.04 * (k // 3), 0.25), (-w / 2 - 0.75 + 0.05 * (k % 3), -d / 2 + 0.28 + 0.05 * (k // 3), 0.42), 0.015, 0.01, "pole", segments=4)
        kit.save(mb, FAMILY, name, COLORS)
    return build


def pile_driver():
    """A ram hauled up between two leads and let fall on the pile."""
    mb = kit.begin()
    for sx in (-1.0, 1.0):
        beam(mb, (sx, -1.2, 0.1), (sx, 2.4, 0.1), 0.11, "pole_dark")
    for y in (-1.0, 2.2):
        beam(mb, (-1.2, y, 0.2), (1.2, y, 0.2), 0.1, "pole_dark")
    for sx in (-1, 1):
        mb.box((sx * 0.32, -1.0, 2.95), (0.14, 0.18, 5.5), "pole")
        beam(mb, (sx * 1.0, 2.2, 0.25), (sx * 0.32, -0.9, 5.4), 0.07, "pole_dark")
        beam(mb, (sx * 1.1, -1.0, 0.25), (sx * 0.34, -1.0, 2.6), 0.05, "pole_dark")
    mb.box((0, -1.0, 5.76), (0.95, 0.3, 0.2), "pole_dark")
    mb.cylinder((-0.07, -1.0, 6.0), (0.07, -1.0, 6.0), 0.17, 0.17, "plank_dark", segments=8)
    for sx in (-1, 1):
        mb.box((sx * 0.12, -1.0, 5.98), (0.04, 0.12, 0.36), "iron")
    bone = windlass(mb, 0, 1.5, 1.0, 0.45, "crank")
    rope(mb, (0, 1.5, 1.14), (0, -0.85, 6.1), 0.014)
    travel = hoist(mb, 0, -1.0, 5.86, 2.3, "ram")
    wr = {"ram": 1.0}
    mb.box((0, -1.0, 1.85), (0.46, 0.5, 0.9), "plank_dark", wr)
    for z in (1.5, 1.85, 2.2):
        mb.box((0, -1.0, z), (0.5, 0.54, 0.08), "iron", wr)
    mb.box((0, -1.0, 2.32), (0.08, 0.08, 0.1), "iron", wr)
    log(mb, (0, -1.0, 0.0), (0, -1.0, 1.38), 0.17)                              # The pile under it.
    mb.cylinder((0, -1.0, 1.25), (0, -1.0, 1.4), 0.19, 0.19, "iron", segments=8)
    for k in range(1, 4):
        log(mb, (1.0 * k + 0.6, -1.0, 0.0), (1.0 * k + 0.6, -1.0, 0.55), 0.17)
    log(mb, (-2.6, -0.2, 0.17), (-2.6, 3.4, 0.17), 0.17)
    log(mb, (-2.2, 0.0, 0.17), (-2.2, 3.5, 0.17), 0.17)
    log(mb, (-2.4, -0.1, 0.47), (-2.4, 3.3, 0.47), 0.17)

    def drive(t):
        if t < 0.78:
            s = kit.smooth(t / 0.78)
        else:
            s = 1.0 - ((t - 0.78) / 0.22) ** 2                                   # It falls faster and faster.
        return {"crank": [(kit.X, 360.0 * 2 * s)]}, {"ram": (0, 0, travel * s)}

    kit.save(mb, FAMILY, "works_pile_driver", COLORS, mech=kit.Mech([bone, ("ram", (0, -1.0, 2.3), (0, -1.0, 1.4), None)]).clip("drive", 4.0, drive))


def survey():
    """A plot staked out before anything is built on it."""
    mb = kit.begin()
    half = 2.0
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.cylinder((sx * half, sy * half, 0), (sx * half, sy * half, 0.6), 0.04, 0.03, "pole", segments=5)
            solid(mb, [(sx * half, sy * half, 0.58), (sx * half + 0.25, sy * half, 0.5), (sx * half, sy * half, 0.42)], (0, 0.01, 0), "paint_red")
    for s in (-1, 1):
        rope(mb, (-half, s * half, 0.35), (half, s * half, 0.35), 0.008)
        rope(mb, (s * half, -half, 0.35), (s * half, half, 0.35), 0.008)
    rope(mb, (-half, -half, 0.35), (half, half, 0.35), 0.006)
    mb.cylinder((0.6, -0.4, 0), (0.6, -0.4, 1.7), 0.03, 0.025, "pole_dark", segments=6)       # A groma: a cross with four plumb lines.
    for a in (0.3, 0.3 + math.pi / 2):
        beam(mb, (0.6 - math.cos(a) * 0.45, -0.4 - math.sin(a) * 0.45, 1.72), (0.6 + math.cos(a) * 0.45, -0.4 + math.sin(a) * 0.45, 1.72), 0.018, "plank_light")
    for k in range(4):
        a = 0.3 + math.pi / 2 * k
        x, y = 0.6 + math.cos(a) * 0.43, -0.4 + math.sin(a) * 0.43
        rope(mb, (x, y, 1.7), (x, y, 1.15), 0.005)
        mb.cylinder((x, y, 1.15), (x, y, 1.05), 0.03, 0.0, "iron", segments=5)
    for k in range(6):                                                           # A measuring rod painted in feet.
        mb.cylinder((-1.4 + 0.33 * k, -2.5, 0.03), (-1.07 + 0.33 * k, -2.5, 0.03), 0.025, 0.025, "paint_red" if k % 2 else "paint_white", segments=5)
    mb.box((2.9, 0.6, 0.8), (1.0, 0.7, 0.05), "plank")                           # The plan on its table.
    for sx in (-0.42, 0.42):
        for sy in (-0.28, 0.28):
            mb.box((2.9 + sx, 0.6 + sy, 0.4), (0.06, 0.06, 0.78), "pole_dark")
    mb.box((2.9, 0.6, 0.83), (0.8, 0.55, 0.012), "parchment")
    mb.box((2.9, 0.6, 0.838), (0.5, 0.3, 0.004), "ink")
    mb.box((2.9, 0.6, 0.84), (0.44, 0.24, 0.004), "parchment")
    mb.box((2.9, 0.6, 0.842), (0.02, 0.24, 0.004), "ink")
    mb.sphere((3.25, 0.82, 0.86), 0.05, "stone", segments=5, rings=3)
    for k in range(5):                                                           # Spare stakes and a mallet.
        beam(mb, (2.4 + 0.07 * k, -1.2, 0.03), (2.44 + 0.07 * k, -0.6, 0.03), 0.03, "pole")
    mb.cylinder((2.9, -1.0, 0.07), (3.15, -1.0, 0.07), 0.07, 0.07, "pole_dark", segments=6)
    beam(mb, (3.02, -1.0, 0.07), (3.02, -0.5, 0.05), 0.02, "pole")
    kit.save(mb, FAMILY, "works_survey", COLORS)


def paving():
    """A street being cobbled: 4 x 2 m, half laid."""
    mb = kit.begin()
    rnd = random.Random(11)
    mb.box((0, 0, 0.04), (4.0, 2.0, 0.08), "sand")
    for i in range(9):
        for j in range(8):
            if i + rnd.random() * 1.5 > 8.6:
                continue
            x = -1.9 + 0.24 * i + (0.12 if j % 2 else 0.0)
            mb.box((x, -0.88 + 0.25 * j, 0.11), (0.21, 0.22, 0.1 + rnd.uniform(0, 0.03)), rnd.choice(("cobble", "cobble", "cobble_dark", "stone_light")))
    for sy in (-1, 1):
        for x in (-2.0, 2.0):
            mb.cylinder((x, sy * 1.05, 0), (x, sy * 1.05, 0.35), 0.025, 0.02, "pole", segments=5)
        rope(mb, (-2.0, sy * 1.05, 0.25), (2.0, sy * 1.05, 0.25), 0.006)
    mb.cylinder((0.9, 0.2, 0.08), (0.9, 0.2, 0.5), 0.16, 0.13, "pole_dark", segments=8)         # The rammer.
    mb.cylinder((0.9, 0.2, 0.08), (0.9, 0.2, 0.14), 0.17, 0.17, "iron", segments=8)
    mb.cylinder((0.9, 0.2, 0.5), (0.9, 0.2, 1.25), 0.03, 0.03, "pole", segments=6)
    beam(mb, (0.68, 0.2, 1.1), (1.12, 0.2, 1.1), 0.022, "pole")
    for _ in range(22):
        mb.box((2.7 + rnd.uniform(-0.5, 0.5), -0.3 + rnd.uniform(-0.5, 0.5), 0.06 + rnd.uniform(0, 0.25)), (0.2, 0.2, 0.12), rnd.choice(("cobble", "cobble_dark", "stone_light")),
               rotation_z=rnd.uniform(0, 3))
    mb.sphere((2.6, 1.3, 0.0), 0.6, "sand", segments=8, rings=4, scale=(1.2, 1.0, 0.45))
    beam(mb, (2.3, 1.2, 0.2), (3.3, 1.9, 0.05), 0.022, "pole")                    # A shovel in the sand.
    mb.box((2.3, 1.2, 0.2), (0.2, 0.24, 0.03), "iron", rotation_z=0.6)
    mb.box((1.4, -0.6, 0.1), (0.5, 0.06, 0.04), "plank_light")                   # A kneeling board and a paviour's hammer.
    beam(mb, (1.5, 0.75, 0.1), (1.85, 0.6, 0.1), 0.018, "pole")
    mb.box((1.5, 0.75, 0.11), (0.06, 0.16, 0.06), "iron", rotation_z=-0.4)
    kit.save(mb, FAMILY, "works_paving", COLORS)


def wall_crane():
    """A small slewing crane on top of a wall under construction."""
    mb = kit.begin()
    rnd = random.Random(2)
    top = 3.0
    mb.box((0, 0, top / 2), (4.0, 1.2, top), "stone")
    for k in range(12):
        mb.box((rnd.uniform(-1.8, 1.8), -0.61, rnd.uniform(0.3, top - 0.3)), (0.5, 0.03, 0.26), rnd.choice(("stone_dark", "stone_light")))
    for k in range(5):                                                           # The course being laid.
        mb.box((-1.75 + 0.52 * k, 0.3, top + 0.14), (0.5, 0.5, 0.28), "stone_light" if k % 2 else "stone")
    mb.box((1.2, 0, top + 0.08), (0.9, 0.9, 0.16), "pole_dark")
    mb.cylinder((1.2, 0, top), (1.2, 0, top + 2.4), 0.09, 0.08, "pole", segments=8)
    wj = {"jib": 1.0}
    mb.cylinder((1.2, 0, top + 0.9), (1.2, 0, top + 2.45), 0.12, 0.12, "pole_dark", wj, segments=8)
    beam(mb, (1.2, 0, top + 2.35), (1.2, -2.2, top + 2.65), 0.08, "pole", wj)
    beam(mb, (1.2, 0, top + 1.1), (1.2, -1.5, top + 2.5), 0.05, "pole_dark", wj)
    beam(mb, (1.2, 0, top + 2.35), (1.2, 0.8, top + 2.2), 0.07, "pole", wj)
    mb.box((1.2, 0.85, top + 2.05), (0.3, 0.3, 0.4), "stone_dark", wj)           # A counterweight.
    mb.cylinder((1.13, -2.1, top + 2.5), (1.27, -2.1, top + 2.5), 0.12, 0.12, "plank_dark", wj, segments=8)
    mb.cylinder((0.95, -0.25, top + 1.3), (1.45, -0.25, top + 1.3), 0.08, 0.08, "rope", wj, segments=8)
    rope(mb, (1.2, -0.3, top + 1.36), (1.2, -2.05, top + 2.6), 0.012, wj)
    travel = hoist(mb, 1.2, -2.1, top + 2.4, 0.8, "load", 0.014, wj)
    wl = {"load": 1.0}
    mb.box((1.2, -2.1, 0.25), (0.6, 0.45, 0.4), "stone_light", wl)
    for sx in (-1, 1):
        rope(mb, (1.2 + sx * 0.3, -2.1, 0.45), (1.2, -2.1, 0.82), 0.01, wl)
        rope(mb, (1.2 + sx * 0.3, -2.1, 0.05), (1.2 + sx * 0.3, -2.1, 0.45), 0.01, wl)
    ashlar(mb, -1.6, -2.4, 0.0, rnd, 3, 2, 2)
    rise = min(travel, top + 0.75)

    def set_stone(t):
        up = phase(t, 0.0, 0.32) - phase(t, 0.72, 1.0)
        turn = phase(t, 0.32, 0.5) - phase(t, 0.54, 0.72)
        return {"jib": [(kit.Z, -120.0 * turn)], "load": [(kit.Z, -120.0 * turn)]}, {"load": (0, 0, rise * up)}

    mech = kit.Mech([("jib", (1.2, 0, top + 0.9), (1.2, 0, top + 2.4), None), ("load", (1.2, 0, 0.8), (1.2, 0, 0.2), None)]).clip("set_stone", 9.0, set_stone)
    kit.save(mb, FAMILY, "works_crane_wall", COLORS, mech=mech)


def demolition():
    """A wall coming down and what is saved from it."""
    mb = kit.begin()
    rnd = random.Random(9)
    heights = (2.6, 2.3, 2.5, 1.7, 1.1, 0.6, 0.3)
    for k, h in enumerate(heights):
        x = -1.8 + 0.6 * k
        mb.box((x, 0, h / 2), (0.6, 0.5, h), "stone" if k % 2 else "stone_light")
        if h > 1.0:
            mb.box((x, -0.26, h * 0.5), (0.5, 0.03, 0.24), "stone_dark")
    for x in (-1.6, -0.6):                                                       # Shores holding what still stands.
        beam(mb, (x, -1.9, 0), (x, -0.25, 2.0), 0.07, "pole")
        mb.box((x, -1.95, 0.06), (0.4, 0.3, 0.12), "plank_dark")
    for _ in range(26):
        rock(mb, rnd.uniform(0.2, 2.6), rnd.uniform(-1.2, 1.2), rnd.uniform(0.05, 0.3), rnd.uniform(0.12, 0.3), rnd)
    mb.sphere((1.6, 0.1, 0.0), 1.1, "sand", segments=8, rings=4, scale=(1.3, 1.1, 0.25))
    ashlar(mb, -2.2, 1.6, 0.0, rnd, 4, 2, 2)                                     # Stone worth using again.
    for k in range(4):
        beam(mb, (-0.2 + 0.16 * k, 1.5, 0.07), (-0.1 + 0.16 * k, 3.4, 0.07), 0.06, "plank_dark")
    beam(mb, (2.9, -1.0, 0), (2.7, -1.0, 1.0), 0.025, "pole")                    # A pick and a crowbar.
    beam(mb, (2.5, -1.0, 0.98), (2.9, -1.0, 1.02), 0.025, "iron")
    beam(mb, (0.6, -0.4, 1.0), (1.0, -1.3, 0.0), 0.02, "iron")
    kit.save(mb, FAMILY, "works_demolition", COLORS)


def carpenter_yard():
    """Where the frame of a house is cut and tried together on the ground."""
    mb = kit.begin()
    rnd = random.Random(12)
    for x in (-1.3, 1.3):                                                        # A beam on trestles, half squared.
        for sy in (-1, 1):
            beam(mb, (x - 0.3, sy * 0.45, 0), (x, sy * 0.12, 0.75), 0.05, "pole_dark")
            beam(mb, (x + 0.3, sy * 0.45, 0), (x, sy * 0.12, 0.75), 0.05, "pole_dark")
        beam(mb, (x, -0.4, 0.75), (x, 0.4, 0.75), 0.06, "pole")
    log(mb, (-2.3, 0, 0.98), (0.2, 0, 0.98), 0.2)
    beam(mb, (0.2, 0, 0.98), (2.3, 0, 0.98), 0.2, "plank_light")
    for _ in range(30):
        mb.box((rnd.uniform(-0.2, 2.2), rnd.uniform(-0.7, 0.7), 0.015), (rnd.uniform(0.08, 0.2), 0.05, 0.03), "sawdust", rotation_z=rnd.uniform(0, 3))
    beam(mb, (1.0, -0.2, 1.14), (1.5, -0.5, 1.14), 0.02, "pole")                  # An adze on the beam.
    mb.box((1.0, -0.2, 1.14), (0.05, 0.14, 0.04), "iron", rotation_z=0.5)
    z = 0.09                                                                     # A roof truss laid out flat to be pegged.
    beam(mb, (-2.6, -3.4, z), (2.6, -3.4, z), 0.09, "plank")
    beam(mb, (-2.6, -3.4, z + 0.1), (0, -1.4, z + 0.1), 0.07, "plank_light")
    beam(mb, (2.6, -3.4, z + 0.1), (0, -1.4, z + 0.1), 0.07, "plank_light")
    beam(mb, (0, -3.4, z + 0.05), (0, -1.4, z + 0.05), 0.07, "plank_dark")
    beam(mb, (-1.3, -2.4, z + 0.16), (1.3, -2.4, z + 0.16), 0.05, "plank_dark")
    for layer in range(3):                                                       # Timber squared and waiting.
        for k in range(4 - layer):
            beam(mb, (-2.2, 2.0 + 0.25 * k + 0.12 * layer, 0.1 + 0.19 * layer), (2.2, 2.0 + 0.25 * k + 0.12 * layer, 0.1 + 0.19 * layer), 0.12, "plank" if (k + layer) % 2 else "plank_light")
    crate(mb, 3.0, 0.4, 0.0, 0.6, 0.4)                                           # The tool chest and a shaving horse.
    mb.box((3.0, -1.2, 0.5), (0.3, 1.3, 0.07), "plank")
    for sy in (-0.5, 0.5):
        for sx in (-0.2, 0.2):
            beam(mb, (3.0 + sx * 1.6, -1.2 + sy, 0), (3.0 + sx * 0.5, -1.2 + sy, 0.5), 0.03, "pole_dark")
    beam(mb, (3.0, -1.5, 0.2), (3.0, -1.6, 0.95), 0.04, "pole")
    mb.box((3.0, -1.6, 0.95), (0.24, 0.1, 0.1), "plank_dark")
    kit.save(mb, FAMILY, "works_carpenter_yard", COLORS)


def lodge():
    """The masons' lodge: a shed with a plaster floor where the master draws the work full size."""
    mb = kit.begin()
    rnd = random.Random(7)
    w, d = 5.0, 3.0
    mb.box((0, 0, 0.06), (w + 0.4, d + 0.4, 0.12), "stone_dark")
    mb.box((0, -0.2, 0.13), (w - 0.4, d - 0.6, 0.03), "lime")                     # The tracing floor.
    for r in (0.7, 1.1):
        for i in range(8):
            a0, a1 = math.pi * i / 8, math.pi * (i + 1) / 8
            beam(mb, (-0.6 + math.cos(a0) * r, -1.2 + math.sin(a0) * r, 0.15), (-0.6 + math.cos(a1) * r, -1.2 + math.sin(a1) * r, 0.15), 0.008, "ink")
    beam(mb, (-1.9, -1.2, 0.15), (0.7, -1.2, 0.15), 0.008, "ink")
    beam(mb, (-0.6, -1.2, 0.15), (-0.6, 0.2, 0.15), 0.008, "ink")
    for sx in (-1, 1):
        mb.box((sx * w / 2, d / 2, 1.5), (0.16, 0.16, 3.0), "pole")
        mb.box((sx * w / 2, -d / 2, 1.2), (0.16, 0.16, 2.4), "pole")
        for k in range(8):
            y = -d / 2 + (d / 8) * (k + 0.5)
            mb.box((sx * w / 2, y, 1.2 + 0.035 * k * 0.0 + 0.6 * 0), (0.06, d / 8 - 0.01, 2.3), "plank" if k % 2 else "plank_light") if sx < 0 else None
    for k in range(16):
        mb.box((-w / 2 + (w / 16) * (k + 0.5), d / 2, 1.45), (w / 16 - 0.01, 0.06, 2.8), "plank" if k % 2 else "plank_light")
    mb.box((0, d / 2, 1.5), (0.16, 0.16, 3.0), "pole")
    mb.box((0, -d / 2, 1.2), (0.16, 0.16, 2.4), "pole")
    shed_roof(mb, 0, 0, w, d, 2.4, 3.0, ("shingle", "shingle_dark"), 0.35, 4)
    mb.box((1.5, 0.8, 0.85), (1.6, 0.8, 0.06), "plank")                          # The drawing table.
    for sx in (-0.7, 0.7):
        for sy in (-0.3, 0.3):
            mb.box((1.5 + sx, 0.8 + sy, 0.48), (0.07, 0.07, 0.72), "pole_dark")
    mb.box((1.4, 0.8, 0.885), (1.0, 0.6, 0.012), "parchment")
    mb.box((1.4, 0.8, 0.893), (0.6, 0.02, 0.004), "ink")
    mb.box((1.4, 0.8, 0.893), (0.02, 0.4, 0.004), "ink")
    beam(mb, (2.0, 0.6, 0.9), (2.2, 1.0, 0.9), 0.012, "iron")                     # Compasses and a square.
    beam(mb, (2.0, 0.6, 0.9), (2.25, 0.75, 0.9), 0.012, "iron")
    for k in range(4):                                                           # Templates on the back wall.
        mb.box((-2.0 + 0.6 * k, d / 2 - 0.06, 1.9), (0.4, 0.02, 0.6 - 0.1 * (k % 2)), "plank_light")
        solid(mb, [(-2.2 + 0.6 * k, d / 2 - 0.07, 1.2), (-1.85 + 0.6 * k, d / 2 - 0.07, 1.2), (-1.85 + 0.6 * k, d / 2 - 0.07, 1.4), (-2.0 + 0.6 * k, d / 2 - 0.07, 1.5),
                   (-2.2 + 0.6 * k, d / 2 - 0.07, 1.4)], (0, 0.02, 0), "plank_dark")
    mb.box((0.6, 0.9, 0.3), (0.5, 0.4, 0.34), "stone_light")                     # A carved capital on show.
    mb.box((0.6, 0.9, 0.52), (0.62, 0.52, 0.1), "stone_light")
    mb.cylinder((0.6, 0.9, 0.13), (0.6, 0.9, 0.3), 0.18, 0.24, "stone", segments=8)
    for _ in range(3):
        rock(mb, rnd.uniform(2.9, 3.5), rnd.uniform(-1.4, 0.4), 0.2, rnd.uniform(0.25, 0.4), rnd)
    kit.save(mb, FAMILY, "works_lodge", COLORS)


MODELS = {
    "works_crane_treadwheel": treadwheel_crane,
    "works_sheerlegs": sheerlegs,
    "works_crane_wall": wall_crane,
    "works_scaffold_1": scaffold("works_scaffold_1", 1),
    "works_scaffold_2": scaffold("works_scaffold_2", 2),
    "works_scaffold_3": scaffold("works_scaffold_3", 3),
    "works_scaffold_hoist": scaffold("works_scaffold_hoist", 2, True),
    "works_sawpit": sawpit,
    "works_stonecutter": stonecutter,
    "works_mortar_pit": mortar_pit,
    "works_lime_kiln": lime_kiln,
    "works_brickyard": brickyard,
    "works_frame_small": frame("works_frame_small", 4.0, 4.0, 2),
    "works_frame_long": frame("works_frame_long", 8.0, 5.0, 4),
    "works_pile_driver": pile_driver,
    "works_survey": survey,
    "works_paving": paving,
    "works_demolition": demolition,
    "works_carpenter_yard": carpenter_yard,
    "works_lodge": lodge,
}

kit.run(MODELS, FAMILY)
