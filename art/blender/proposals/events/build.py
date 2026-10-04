"""Events and disasters proposals: what the map shows when something happens
to the town. See ../LEEME.md.

    blender --background --factory-startup --python art/blender/proposals/events/build.py -- [ids]
"""

import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import _kit as kit  # noqa: E402
import _shapes  # noqa: E402
import common  # noqa: E402
from _shapes import TAU, barrel, beam, crate, log, rock, rope, sack, solid, wheel  # noqa: E402

FAMILY = "events"
C = common.rgb
COLORS = {
    **_shapes.COLORS,
    "dust": C(0x8A8274), "dust_light": C(0xA8A090), "dust_dark": C(0x6A6458), "cloud": C(0x5A5E6A), "cloud_dark": C(0x444852), "cloud_light": C(0x7A7E8A),
    "glow_bolt": C(0xF4F6FF), "rain": C(0x9AC0E0), "water": C(0x4A8FC0), "water_mud": C(0x7A7458), "snow": C(0xF0F4F8), "snow_shade": C(0xD0DCE8),
    "soil": C(0x6A4A30), "soil_dark": C(0x4A3422), "dry": C(0xC0A070), "dry_dark": C(0x8A6E48), "cave": C(0x14110F), "grass": C(0x6A9440),
    "char": C(0x2A2624), "char_light": C(0x44403C), "ash": C(0x8A8884), "flame": C(0xF2A23A), "ember": C(0xD8502A), "leaf": C(0x3E6E38), "leaf_dry": C(0x9A8A4A),
    "locust": C(0x7A8A3A), "locust_dark": C(0x5A6A2A), "rat": C(0x5E564E), "rat_dark": C(0x443E38), "bone": C(0xE0D8C0), "shroud": C(0xD8D2C0),
    "lime": C(0xECE8DC), "bell": C(0xB8923A), "thatch": C(0xC9A55A), "thatch_dark": C(0xA8863F), "paint_red": C(0xB8362E), "wheat": C(0xD8B85A),
}


def phase(t, a, b):
    return kit.smooth(min(1.0, max(0.0, (t - a) / (b - a))))


def flames(mb, x, y, z, s, w, n=4):
    for k in range(n):
        a = TAU * k / n
        mb.cylinder((x + math.cos(a) * 0.16 * s, y + math.sin(a) * 0.16 * s, z), (x + math.cos(a) * 0.08 * s, y + math.sin(a) * 0.08 * s, z + (0.5 + 0.2 * (k % 2)) * s), 0.13 * s, 0.0,
                    "flame" if k % 2 else "ember", w, segments=5)
    mb.cylinder((x, y, z), (x, y, z + 0.95 * s), 0.14 * s, 0.0, "flame", w, segments=5)


def tornado():
    """A whirlwind 10 m tall that walks across the map."""
    mb = kit.begin()
    rnd = random.Random(41)
    bones = ("a", "b", "c")
    n = 9
    for k in range(n):
        z0, z1 = 10.0 * k / n, 10.0 * (k + 1) / n + 0.15
        r0, r1 = 0.35 + 0.33 * k ** 1.25, 0.35 + 0.33 * (k + 1) ** 1.25
        off = 0.25 + 0.12 * k
        a = k * 1.9
        mb.cylinder((math.cos(a) * off, math.sin(a) * off, z0), (math.cos(a + 0.6) * off, math.sin(a + 0.6) * off, z1), r0, r1, ("dust", "dust_light", "dust_dark")[k % 3],
                    {bones[k % 3]: 1.0}, segments=10)
    mb.cylinder((0, 0, 9.9), (0, 0, 10.6), 5.4, 6.4, "cloud", {"a": 1.0}, segments=12)
    mb.cylinder((0, 0, 10.5), (0, 0, 11.2), 6.4, 5.0, "cloud_dark", {"b": 1.0}, segments=12)
    for k in range(14):                                                          # What it has picked up.
        a, z = rnd.uniform(0, TAU), rnd.uniform(0.6, 8.5)
        r = 0.8 + 0.4 * z + rnd.uniform(0, 0.6)
        w = {bones[k % 3]: 1.0}
        kind = k % 4
        if kind == 0:
            mb.box((math.cos(a) * r, math.sin(a) * r, z), (0.9, 0.16, 0.05), "plank", w, rotation_z=a + 1.0)
        elif kind == 1:
            mb.box((math.cos(a) * r, math.sin(a) * r, z), (0.5, 0.4, 0.06), "thatch", w, rotation_z=a)
        elif kind == 2:
            mb.sphere((math.cos(a) * r, math.sin(a) * r, z), 0.2, "leaf", w, segments=5, rings=3)
        else:
            log(mb, (math.cos(a) * r, math.sin(a) * r, z), (math.cos(a + 0.3) * r, math.sin(a + 0.3) * r, z + 0.4), 0.07, w)
    mb.cylinder((0, 0, 0), (0, 0, 0.06), 2.6, 2.6, "dust_dark", segments=12)     # The scar it leaves.
    for k in range(8):
        a = TAU * k / 8
        mb.sphere((math.cos(a) * 1.7, math.sin(a) * 1.7, 0.1), 0.5, "dust_light", {"c": 1.0}, segments=5, rings=3, scale=(1, 1, 0.5))

    def spin(t):
        sway = (0.5 * math.sin(TAU * t), 0.4 * math.sin(TAU * 2 * t), 0)
        return {"a": [(kit.Z, 360.0 * 2 * t)], "b": [(kit.Z, 360.0 * 3 * t)], "c": [(kit.Z, 360.0 * 4 * t)]}, {"b": sway}

    mech = kit.Mech([("a", (0, 0, 0), (0, 0, 1.0), None), ("b", (0, 0, 3.0), (0, 0, 4.0), None), ("c", (0, 0, 6.0), (0, 0, 7.0), None)]).clip("spin", 3.0, spin)
    kit.save(mb, FAMILY, "event_tornado", COLORS, mech=mech)


def storm_cloud():
    """A storm standing over one place, with its rain and its bolt."""
    mb = kit.begin()
    rnd = random.Random(42)
    w = {"cloud": 1.0}
    for k in range(14):
        a = rnd.uniform(0, TAU)
        r = rnd.uniform(0.0, 3.2)
        mb.sphere((math.cos(a) * r, math.sin(a) * r * 0.8, 8.0 + rnd.uniform(-0.3, 0.9)), rnd.uniform(1.3, 2.1), rnd.choice(("cloud", "cloud_dark", "cloud_light")), w,
                  segments=7, rings=5, scale=(1.2, 1.0, 0.6))
    wr = {"rain": 1.0}
    for i in range(7):
        for j in range(6):
            x, y = -3.0 + 1.0 * i + rnd.uniform(-0.3, 0.3), -2.2 + 0.9 * j + rnd.uniform(-0.3, 0.3)
            z = rnd.uniform(0.0, 1.6)
            while z < 7.4:
                mb.box((x, y, z + 0.25), (0.035, 0.035, 0.5), "rain", wr)
                z += 1.6
    wb = {"bolt": 1.0}
    pts = [(0.4, 0.2, 7.6), (-0.3, 0.0, 6.0), (0.5, -0.1, 4.8), (-0.1, 0.1, 3.0), (0.7, 0.0, 1.8), (0.3, 0.0, 0.0)]
    for p, q in zip(pts, pts[1:]):
        beam(mb, p, q, 0.09, "glow_bolt", wb)
    beam(mb, pts[2], (1.5, -0.2, 3.9), 0.05, "glow_bolt", wb)
    mb.cylinder((0, 0, 0), (0, 0, 0.05), 3.8, 3.8, "water_mud", segments=12)

    def storm(t):
        strike = 1.0 if 0.6 < t < 0.68 or 0.72 < t < 0.76 else 0.0
        return {}, {"rain": (0, 0, -1.6 * ((t * 4) % 1.0)), "bolt": (0, 0, 0.0 if strike else 9.5), "cloud": (0.3 * math.sin(TAU * t), 0, 0)}

    mech = kit.Mech([("cloud", (0, 0, 8.0), (0, 0, 9.0), None), ("rain", (0, 0, 4.0), (0, 0, 3.0), None), ("bolt", (0, 0, 7.6), (0, 0, 0.0), None)])
    mb_rest_fix = mech.clip("storm", 4.0, storm)
    kit.save(mb, FAMILY, "event_storm_cloud", COLORS, mech=mb_rest_fix)


def flood():
    """A flooded plot, 6 x 6 m: what floats, and what still shows above the water."""
    mb = kit.begin()
    mb.box((0, 0, 0.14), (6.0, 6.0, 0.28), "water_mud")
    mb.box((0, 0, 0.29), (5.6, 5.6, 0.02), "water")
    for k in range(5):                                                           # A fence up to its top rail.
        mb.cylinder((-2.4 + 1.2 * k, 2.2, 0), (-2.4 + 1.2 * k, 2.2, 0.75), 0.06, 0.05, "pole", segments=6)
    beam(mb, (-2.5, 2.2, 0.6), (2.5, 2.2, 0.6), 0.035, "pole_dark")
    mb.box((-1.8, -1.6, 0.5), (1.4, 1.2, 0.5), "plank")                          # The top of a shed.
    solid(mb, [(-2.6, -2.3, 0.75), (-1.0, -2.3, 0.75), (-1.0, -1.6, 1.25), (-2.6, -1.6, 1.25)], (0, 0, 0.07), "thatch")
    solid(mb, [(-2.6, -0.9, 0.75), (-1.0, -0.9, 0.75), (-1.0, -1.6, 1.25), (-2.6, -1.6, 1.25)], (0, 0, 0.07), "thatch_dark")
    w = {"drift": 1.0}
    solid(mb, [(0.6, -0.4, 0.26), (2.0, -0.2, 0.26), (1.9, 0.8, 0.5), (0.5, 0.6, 0.5)], (0, 0, 0.08), "thatch", w)   # A piece of roof adrift.
    beam(mb, (0.5, -0.5, 0.3), (0.4, 0.7, 0.52), 0.04, "pole_dark", w)
    w2 = {"bob": 1.0}
    mb.cylinder((1.6, -2.0, 0.3), (2.3, -1.8, 0.3), 0.26, 0.26, "plank", w2, segments=9)
    mb.cylinder((1.7, -1.97, 0.3), (1.78, -1.95, 0.3), 0.275, 0.275, "iron", w2, segments=9)
    mb.box((-0.3, 1.0, 0.3), (0.5, 0.5, 0.3), "plank_light", w2, rotation_z=0.5)
    mb.box((2.2, 1.6, 0.3), (0.9, 0.14, 0.06), "plank_dark", w2, rotation_z=-0.6)

    def pose(t):
        return ({"drift": [(kit.Z, 8.0 * math.sin(TAU * t))], "bob": [(kit.X, 5.0 * math.sin(TAU * 2 * t))]},
                {"drift": (0.15 * math.sin(TAU * t), 0, 0.03 * math.sin(TAU * 2 * t)), "bob": (0, 0, 0.04 * math.sin(TAU * 2 * t + 1.0))})

    mech = kit.Mech([("drift", (1.2, 0.2, 0.3), (1.2, 0.2, 0.8), None), ("bob", (1.0, 0, 0.3), (1.0, 0, 0.8), None)]).clip("float", 5.0, pose)
    kit.save(mb, FAMILY, "event_flood", COLORS, mech=mech)


def sandbags(name, corner):
    """A wall of sandbags against the river: a 4 m run, or its corner."""
    def build():
        mb = kit.begin()

        def run(x0, y0, x1, y1, rows=4):
            length = math.hypot(x1 - x0, y1 - y0)
            rot = math.atan2(y1 - y0, x1 - x0)
            nx, ny = -math.sin(rot), math.cos(rot)
            for row in range(rows):
                width = 2 if row < 2 else 1
                n = int(length / 0.62)
                for d in range(width):
                    off = (d - (width - 1) / 2) * 0.42
                    for k in range(n + (row % 2)):
                        u = (k + 0.5 - 0.5 * (row % 2)) / n
                        u = min(1.0, max(0.0, u))
                        mb.sphere((x0 + (x1 - x0) * u + nx * off, y0 + (y1 - y0) * u + ny * off, 0.12 + 0.21 * row), 0.3,
                                  "sack" if (k + row + d) % 3 else "hay_dark", segments=6, rings=4, scale=(1.05, 0.72, 0.42))
        if corner:
            run(-2.0, 0, 0.1, 0)
            run(0, -0.1, 0, 2.0)
        else:
            run(-2.0, 0, 2.0, 0)
            beam(mb, (1.2, -0.7, 0), (1.5, -0.5, 1.2), 0.022, "pole")                     # A shovel and bags waiting.
            mb.box((1.2, -0.7, 0.08), (0.2, 0.26, 0.03), "iron")
            sack(mb, -1.0, -0.9, 0.0, 0.24)
            mb.sphere((0.2, -1.0, 0.0), 0.5, "dry", segments=7, rings=4, scale=(1.2, 1, 0.4))
        kit.save(mb, FAMILY, name, COLORS)
    return build


def sinkhole():
    mb = kit.begin()
    rnd = random.Random(44)
    for r, z, mat in ((3.0, 0.03, "soil"), (2.5, 0.045, "soil_dark"), (1.9, 0.06, "cave")):
        mb.cylinder((0, 0, 0), (0, 0, z), r, r, mat, segments=11)
    for k in range(11):                                                          # Slabs of turf tipping in.
        a = TAU * k / 11 + rnd.uniform(-0.1, 0.1)
        r = rnd.uniform(2.3, 2.9)
        x, y = math.cos(a) * r, math.sin(a) * r
        tilt = rnd.uniform(0.15, 0.4)
        solid(mb, [(x - math.sin(a) * 0.5, y + math.cos(a) * 0.5, 0.25), (x + math.sin(a) * 0.5, y - math.cos(a) * 0.5, 0.25),
                   (x + math.sin(a) * 0.4 - math.cos(a) * 0.8, y - math.cos(a) * 0.4 - math.sin(a) * 0.8, 0.25 - tilt),
                   (x - math.sin(a) * 0.4 - math.cos(a) * 0.8, y + math.cos(a) * 0.4 - math.sin(a) * 0.8, 0.25 - tilt)], (0, 0, -0.22), "grass" if k % 3 else "soil")
    for k in range(7):
        a = rnd.uniform(0, TAU)
        beam(mb, (math.cos(a) * 3.0, math.sin(a) * 3.0, 0.035), (math.cos(a + 0.15) * 4.2, math.sin(a + 0.15) * 4.2, 0.035), 0.03, "cave")
    for k in range(4):                                                           # A fence going down with the ground.
        x = 1.2 + 0.9 * k
        drop = max(0.0, 0.5 - 0.25 * k)
        mb.cylinder((x, -1.9 - 0.1 * k, -drop), (x - drop * 0.6, -1.9 - 0.1 * k, 0.9 - drop), 0.05, 0.045, "pole", segments=6)
    beam(mb, (0.9, -1.9, 0.25), (3.9, -2.2, 0.7), 0.03, "pole_dark")
    wheel(mb, (-1.6, 0.6, 0.35), 0.5, None, 0.08)
    mb.box((-1.3, 1.2, 0.2), (1.2, 0.7, 0.1), "plank", rotation_z=0.4)
    for _ in range(8):
        rock(mb, rnd.uniform(-1.4, 1.4), rnd.uniform(-1.4, 1.4), 0.08, rnd.uniform(0.15, 0.3), rnd, "soil_dark")
    kit.save(mb, FAMILY, "event_sinkhole", COLORS)


def fissure():
    """A crack 9 m long that an earthquake opened."""
    mb = kit.begin()
    rnd = random.Random(45)
    pts = [(-4.5, 0.2), (-3.0, -0.5), (-1.6, 0.4), (0.0, -0.3), (1.5, 0.5), (3.0, -0.2), (4.5, 0.3)]
    for k, ((x0, y0), (x1, y1)) in enumerate(zip(pts, pts[1:])):
        w0 = 0.15 + 0.5 * math.sin(math.pi * k / 6)
        w1 = 0.15 + 0.5 * math.sin(math.pi * (k + 1) / 6)
        solid(mb, [(x0, y0 - w0, 0.0), (x1, y1 - w1, 0.0), (x1, y1 + w1, 0.0), (x0, y0 + w0, 0.0)], (0, 0, 0.05), "cave")
        solid(mb, [(x0, y0 - w0 * 0.3, 0.0), (x1, y1 - w1 * 0.3, 0.0), (x1, y1 + w1 * 0.3, 0.0), (x0, y0 + w0 * 0.3, 0.0)], (0, 0, 0.06), "ember")
        for side in (-1, 1):                                                     # The ground heaved up along both lips.
            lift = rnd.uniform(0.2, 0.55)
            solid(mb, [(x0, y0 + side * w0, 0.05), (x1, y1 + side * w1, 0.05), (x1, y1 + side * (w1 + 1.1), 0.0), (x0, y0 + side * (w0 + 1.1), 0.0)],
                  (0, 0, lift), "soil" if (k + side) % 2 else "grass")
    for _ in range(10):
        rock(mb, rnd.uniform(-4.0, 4.0), rnd.choice((-1, 1)) * rnd.uniform(1.4, 2.0), 0.1, rnd.uniform(0.15, 0.35), rnd)
    mb.box((2.0, 1.6, 0.5), (0.5, 0.5, 1.0), "stone", rotation_z=0.3)            # What is left of a wall.
    mb.box((2.6, 1.9, 0.2), (0.5, 0.4, 0.3), "stone_light", rotation_z=0.9)
    w = {"smoke": 1.0}
    for k in range(4):
        mb.sphere((-2.0 + 1.3 * k, 0.1 * (k % 2), 0.6 + 0.3 * (k % 2)), 0.3 + 0.06 * k, "ash", w, segments=5, rings=3)
    pose = lambda t: ({}, {"smoke": (0.1 * math.sin(TAU * t), 0, 0.25 * math.sin(TAU * t))})   # noqa: E731
    kit.save(mb, FAMILY, "event_fissure", COLORS, mech=kit.Mech([("smoke", (0, 0, 0.6), (0, 0, 1.2), None)]).clip("smoke", 4.0, pose))


def drought_field():
    mb = kit.begin()
    rnd = random.Random(46)
    mb.box((0, 0, 0.04), (4.0, 4.0, 0.08), "dry")
    for _ in range(26):
        x, y, a = rnd.uniform(-1.8, 1.8), rnd.uniform(-1.8, 1.8), rnd.uniform(0, TAU)
        d = rnd.uniform(0.3, 0.8)
        beam(mb, (x, y, 0.082), (x + math.cos(a) * d, y + math.sin(a) * d, 0.082), 0.02, "dry_dark")
        beam(mb, (x + math.cos(a) * d, y + math.sin(a) * d, 0.082), (x + math.cos(a + 1.1) * d * 0.7 + math.cos(a) * d, y + math.sin(a + 1.1) * d * 0.7 + math.sin(a) * d, 0.082),
             0.016, "dry_dark")
    for i in range(6):
        for j in range(5):
            if rnd.random() < 0.35:
                continue
            x, y = -1.6 + 0.64 * i + rnd.uniform(-0.1, 0.1), -1.5 + 0.7 * j + rnd.uniform(-0.1, 0.1)
            lean = rnd.uniform(-0.25, 0.25)
            mb.cylinder((x, y, 0.08), (x + lean, y + lean * 0.5, 0.5), 0.02, 0.012, "leaf_dry", segments=4)
            mb.cylinder((x + lean, y + lean * 0.5, 0.5), (x + lean * 2.4, y + lean, 0.38), 0.016, 0.0, "hay_dark", segments=4)
    mb.sphere((1.2, -1.3, 0.2), 0.16, "bone", segments=6, rings=4, scale=(1.4, 0.9, 0.8))   # What the drought took.
    mb.box((1.42, -1.3, 0.15), (0.16, 0.14, 0.1), "bone")
    for s in (-1, 1):
        mb.cylinder((1.1, -1.3 + s * 0.1, 0.3), (0.95, -1.3 + s * 0.3, 0.45), 0.03, 0.0, "bone", segments=4)
    mb.cylinder((-1.5, 1.5, 0.08), (-1.5, 1.5, 0.4), 0.14, 0.18, "plank_light", segments=8)
    mb.cylinder((-1.5, 1.5, 0.09), (-1.5, 1.5, 0.1), 0.13, 0.13, "cave", segments=8)
    kit.save(mb, FAMILY, "event_drought_field", COLORS)


def locusts():
    """A field of 4 x 4 m being stripped by a cloud of locusts."""
    mb = kit.begin()
    rnd = random.Random(47)
    mb.box((0, 0, 0.04), (4.0, 4.0, 0.08), "soil")
    for i in range(7):
        for j in range(7):
            x, y = -1.7 + 0.57 * i, -1.7 + 0.57 * j
            eaten = (i + j) > 6 + rnd.randrange(-1, 2)
            if eaten:
                mb.cylinder((x, y, 0.08), (x, y, 0.3), 0.02, 0.015, "leaf_dry", segments=4)
            else:
                mb.cylinder((x, y, 0.08), (x, y, 0.75), 0.03, 0.02, "leaf", segments=4)
                mb.cylinder((x, y, 0.7), (x, y, 0.95), 0.05, 0.02, "wheat", segments=5)
    bones = ("a", "b", "c")
    for k in range(110):
        a = rnd.uniform(0, TAU)
        r = rnd.uniform(0.2, 2.6) ** 0.9
        z = rnd.uniform(0.5, 3.2) if k % 4 else rnd.uniform(0.3, 1.0)
        mb.box((0.6 + math.cos(a) * r, 0.6 + math.sin(a) * r * 0.8, z), (0.14, 0.05, 0.05), "locust" if k % 3 else "locust_dark", {bones[k % 3]: 1.0}, rotation_z=a + 1.6)

    def swarm(t):
        return ({"a": [(kit.Z, 360.0 * t)], "b": [(kit.Z, -360.0 * t)], "c": [(kit.Z, 720.0 * t)]},
                {"a": (0, 0, 0.2 * math.sin(TAU * 2 * t)), "b": (0, 0, 0.25 * math.sin(TAU * 3 * t)), "c": (0, 0, 0.15 * math.sin(TAU * 2 * t + 2.0))})

    mech = kit.Mech([(b, (0.6, 0.6, 1.5), (0.6, 0.6, 2.2), None) for b in bones]).clip("swarm", 4.0, swarm)
    kit.save(mb, FAMILY, "event_locusts", COLORS, mech=mech)


def conifer(mb, x, y, h, burnt, w=None, rnd=None):
    mb.cylinder((x, y, 0), (x, y, h * 0.5), 0.2, 0.12, "char" if burnt else "bark", segments=6)
    tiers = 3
    for k in range(tiers):
        z0 = h * (0.25 + 0.22 * k)
        r = h * (0.3 - 0.07 * k)
        mb.cylinder((x, y, z0), (x, y, z0 + h * 0.34), r, 0.0, ("char_light" if k % 2 else "char") if burnt else "leaf", segments=7)
        if w and rnd:
            for _ in range(2):
                a = rnd.uniform(0, TAU)
                flames(mb, x + math.cos(a) * r * 0.5, y + math.sin(a) * r * 0.5, z0 + h * 0.1, 0.7 + 0.2 * k, w, 3)


def wildfire():
    """A stand of pines burning: 8 x 8 m of fire that moves with the wind."""
    mb = kit.begin()
    rnd = random.Random(48)
    mb.cylinder((0, 0, 0), (0, 0, 0.04), 4.2, 4.2, "char_light", segments=12)
    mb.cylinder((0.5, 0, 0), (0.5, 0, 0.05), 2.6, 2.6, "char", segments=10)
    spots = [(-2.2, 1.0, 4.6), (-0.4, 2.2, 5.4), (1.4, 1.0, 4.2), (-1.0, -0.6, 5.0), (1.0, -1.6, 4.4), (2.6, -0.4, 3.8), (-2.6, -1.8, 4.0)]
    for k, (x, y, h) in enumerate(spots):
        conifer(mb, x, y, h, k < 5, {"fa" if k % 2 else "fb": 1.0} if 0 < k < 6 else None, rnd)
    for k in range(9):
        a = TAU * k / 9
        flames(mb, math.cos(a) * rnd.uniform(1.5, 3.6), math.sin(a) * rnd.uniform(1.5, 3.6), 0.04, rnd.uniform(0.6, 1.1), {"fa" if k % 2 else "fb": 1.0}, 3)
    for _ in range(14):
        mb.box((rnd.uniform(-3.0, 3.0), rnd.uniform(-3.0, 3.0), 0.06), (0.14, 0.14, 0.05), "ember", rotation_z=rnd.uniform(0, 3))
    ws = {"smoke": 1.0}
    for k in range(6):
        mb.sphere((-0.5 + 0.5 * k, 0.4 * (k % 2), 6.0 + 0.6 * k), 0.7 + 0.14 * k, "ash" if k % 2 else "cloud", ws, segments=6, rings=4)

    def burn(t):
        return ({"fa": [(kit.Z, 20.0 * math.sin(TAU * 3 * t))], "fb": [(kit.Z, -20.0 * math.sin(TAU * 2 * t))]},
                {"fa": (0, 0, 0.1 * math.sin(TAU * 4 * t)), "fb": (0, 0, 0.1 * math.sin(TAU * 3 * t + 1.0)), "smoke": (0.4 * math.sin(TAU * t), 0, 0.4 * math.sin(TAU * t))})

    mech = kit.Mech([("fa", (0, 0, 0), (0, 0, 1), None), ("fb", (0.2, 0, 0), (0.2, 0, 1), None), ("smoke", (0, 0, 6.0), (0, 0, 7.0), None)]).clip("burn", 3.0, burn)
    kit.save(mb, FAMILY, "event_wildfire", COLORS, mech=mech)


def burnt_forest():
    mb = kit.begin()
    rnd = random.Random(49)
    mb.cylinder((0, 0, 0), (0, 0, 0.04), 4.2, 4.2, "char_light", segments=12)
    for k in range(9):
        a = TAU * k / 9 + rnd.uniform(-0.2, 0.2)
        r = rnd.uniform(0.6, 3.4)
        x, y, h = math.cos(a) * r, math.sin(a) * r, rnd.uniform(1.2, 4.5)
        mb.cylinder((x, y, 0), (x + rnd.uniform(-0.2, 0.2), y, h), 0.2, 0.07, "char", segments=6)
        for _ in range(2):
            z = rnd.uniform(0.4, 0.9) * h
            b = rnd.uniform(0, TAU)
            beam(mb, (x, y, z), (x + math.cos(b) * 0.7, y + math.sin(b) * 0.7, z + 0.4), 0.035, "char_light")
    log(mb, (-2.6, -2.0, 0.16), (0.6, -2.8, 0.16), 0.16, None, "char")
    for _ in range(10):
        mb.sphere((rnd.uniform(-3.2, 3.2), rnd.uniform(-3.2, 3.2), 0.0), rnd.uniform(0.3, 0.6), "ash", segments=5, rings=3, scale=(1, 1, 0.2))
    for k in range(5):                                                           # The first green coming back.
        x, y = rnd.uniform(-2.5, 2.5), rnd.uniform(-2.5, 2.5)
        mb.cylinder((x, y, 0.04), (x, y, 0.35), 0.1, 0.0, "grass", segments=5)
    kit.save(mb, FAMILY, "event_burnt_forest", COLORS)


def lightning_tree():
    mb = kit.begin()
    mb.cylinder((0, 0, 0), (0, 0, 0.05), 1.8, 1.8, "char_light", segments=9)
    mb.cylinder((0, 0, 0), (0, 0, 1.8), 0.42, 0.34, "bark", segments=8)
    mb.cylinder((-0.12, 0, 1.8), (-0.4, 0.1, 4.6), 0.26, 0.08, "char", segments=6)      # One half still stands.
    beam(mb, (-0.25, 0.05, 3.0), (-1.2, 0.3, 3.9), 0.05, "char_light")
    beam(mb, (-0.33, 0.08, 3.8), (0.2, -0.5, 4.5), 0.04, "char_light")
    mb.cylinder((0.16, 0, 1.75), (0.2, 0, 1.95), 0.2, 0.0, "char", segments=5)
    mb.box((0.02, 0, 1.3), (0.08, 0.5, 1.0), "ember")                            # The split still glows.
    log(mb, (0.6, -0.4, 0.3), (3.6, -1.6, 0.22), 0.22, None, "char_light")       # The other half on the ground.
    for k in range(3):
        beam(mb, (1.6 + 0.6 * k, -0.8 - 0.25 * k, 0.3), (1.9 + 0.6 * k, -0.2 - 0.3 * k, 0.9), 0.04, "char")
    w = {"fire": 1.0}
    flames(mb, 0.1, 0.0, 1.8, 0.8, w)
    flames(mb, 2.2, -1.05, 0.4, 0.6, w, 3)
    pose = lambda t: ({"fire": [(kit.Z, 18.0 * math.sin(TAU * 3 * t))]}, {"fire": (0, 0, 0.06 * math.sin(TAU * 4 * t))})   # noqa: E731
    kit.save(mb, FAMILY, "event_lightning_tree", COLORS, mech=kit.Mech([("fire", (0.1, 0, 1.0), (0.1, 0, 2.0), None)]).clip("burn", 2.0, pose))


def snowdrift(name, big):
    """Snow across the road, or what an avalanche brings down."""
    def build():
        mb = kit.begin()
        rnd = random.Random(50 + big)
        if not big:
            for k in range(7):
                mb.sphere((-1.8 + 0.6 * k, rnd.uniform(-0.3, 0.3), 0.0), rnd.uniform(0.9, 1.3), "snow" if k % 2 else "snow_shade", segments=7, rings=5,
                          scale=(1.0, 1.3, rnd.uniform(0.6, 0.9)))
            mb.cylinder((1.2, -0.6, 0), (1.25, -0.6, 2.2), 0.06, 0.05, "pole", segments=6)       # A signpost up to its board.
            mb.box((1.5, -0.62, 1.9), (0.7, 0.05, 0.22), "plank")
            mb.sphere((1.5, -0.62, 2.03), 0.12, "snow", segments=5, rings=3, scale=(2.6, 0.5, 0.4))
            wheel(mb, (-0.9, -1.0, 0.55), 0.5, None, 0.08)
            beam(mb, (-0.6, -1.2, 0.7), (0.4, -1.9, 0.5), 0.04, "pole_dark")
        else:
            for k in range(22):
                u = rnd.random()
                x, y = rnd.uniform(-1, 1) * (1.2 + 3.2 * u), 4.0 - 8.0 * u
                mb.sphere((x, y, 0.0), rnd.uniform(1.0, 1.8) * (1.2 - 0.4 * u), "snow" if k % 3 else "snow_shade", segments=7, rings=5, scale=(1.2, 1.2, 0.5 + 0.5 * (1 - u)))
            for _ in range(12):
                rock(mb, rnd.uniform(-3.4, 3.4), rnd.uniform(-3.8, 1.5), rnd.uniform(0.3, 0.9), rnd.uniform(0.3, 0.7), rnd)
            for k in range(5):
                x, y = rnd.uniform(-3.0, 3.0), rnd.uniform(-3.5, 0.5)
                a = rnd.uniform(0, TAU)
                log(mb, (x, y, 0.5), (x + math.cos(a) * 2.2, y + math.sin(a) * 2.2, 1.1), 0.14)
                mb.cylinder((x + math.cos(a) * 1.5, y + math.sin(a) * 1.5, 0.9), (x + math.cos(a) * 2.6, y + math.sin(a) * 2.6, 1.2), 0.5, 0.0, "leaf", segments=6)
            solid(mb, [(-0.9, -4.2, 0.3), (0.7, -4.4, 0.4), (0.9, -3.6, 0.9), (-0.7, -3.4, 0.8)], (0, 0, 0.08), "thatch_dark")   # A roof it carried off.
        kit.save(mb, FAMILY, name, COLORS)
    return build


def plague_cart():
    """The cart that goes round for the dead, with its bell."""
    mb = kit.begin()
    for sx in (-0.85, 0.85):
        wheel(mb, (sx, 0, 0.6), 0.6, None, 0.09)
    mb.cylinder((-0.85, 0, 0.6), (0.85, 0, 0.6), 0.05, 0.05, "iron", segments=6)
    mb.box((0, 0, 0.82), (1.4, 2.4, 0.1), "plank_dark")
    for sx in (-1, 1):
        mb.box((sx * 0.7, 0, 1.05), (0.06, 2.4, 0.4), "plank")
        beam(mb, (sx * 0.5, -1.2, 0.8), (sx * 0.45, -2.9, 0.75), 0.04, "pole")              # The shafts: a man pulls it.
    mb.box((0, 1.2, 1.05), (1.4, 0.06, 0.4), "plank")
    beam(mb, (-0.45, -2.8, 0.75), (0.45, -2.8, 0.75), 0.035, "pole_dark")
    mb.cylinder((0.0, -1.3, 0.0), (0.0, -1.2, 0.8), 0.04, 0.04, "pole_dark", segments=5)
    for k, (x, y, rot) in enumerate(((-0.3, 0.2, 0.05), (0.3, -0.1, -0.08), (0.0, 0.3, 0.2))):   # Shrouded shapes.
        z = 0.98 + 0.2 * (k // 2)
        mb.sphere((x, y, z), 0.24, "shroud", segments=7, rings=5, scale=(0.9, 3.6, 0.7))
        mb.sphere((x + rot, y + 0.75, z + 0.03), 0.15, "shroud", segments=6, rings=4)
        for d in (-0.4, 0.3):
            mb.cylinder((x - 0.22, y + d, z), (x + 0.22, y + d, z), 0.17, 0.17, "rope", segments=6)
    mb.cylinder((0.62, 1.1, 0.87), (0.62, 1.1, 2.3), 0.035, 0.03, "pole", segments=5)        # A pole with the bell and a lantern.
    beam(mb, (0.62, 1.1, 2.25), (0.2, 1.1, 2.3), 0.025, "pole")
    w = {"bell": 1.0}
    mb.cylinder((0.25, 1.1, 2.25), (0.25, 1.1, 2.05), 0.04, 0.13, "bell", w, segments=8)
    mb.sphere((0.25, 1.1, 2.02), 0.035, "iron", w, segments=5, rings=3)
    _shapes.lantern(mb, -0.62, 1.1, 1.26)
    mb.cylinder((-0.3, -0.95, 0.87), (-0.3, -0.95, 1.15), 0.12, 0.15, "plank_light", segments=8)   # Quicklime.
    mb.cylinder((-0.3, -0.95, 1.11), (-0.3, -0.95, 1.14), 0.13, 0.13, "lime", segments=8)
    beam(mb, (0.3, -1.0, 0.9), (0.5, -0.2, 1.4), 0.02, "pole")
    pose = lambda t: ({"bell": [(kit.Y, 30.0 * math.sin(TAU * 2 * t))]}, {})   # noqa: E731
    kit.save(mb, FAMILY, "event_plague_cart", COLORS, mech=kit.Mech([("bell", (0.25, 1.1, 2.28), (0.25, 1.1, 2.05), None)]).clip("ring", 2.0, pose))


def rats():
    """Rats in the grain."""
    mb = kit.begin()
    rnd = random.Random(52)
    sack(mb, 0.0, 0.0, 0.0, 0.3)
    sack(mb, 0.5, 0.2, 0.0, 0.28)
    mb.sphere((-0.5, -0.1, 0.12), 0.26, "sack", segments=7, rings=5, scale=(1.5, 0.9, 0.5))     # One gnawed open.
    mb.sphere((-0.9, -0.3, 0.0), 0.35, "wheat", segments=7, rings=4, scale=(1.2, 1.0, 0.25))
    crate(mb, 0.2, 0.8, 0.0, 0.5)
    for k in range(14):
        ring = 1.0 + 0.35 * (k % 3)
        a = TAU * k / 14 + rnd.uniform(-0.15, 0.15)
        w = {"run_a" if k % 2 else "run_b": 1.0}
        x, y = math.cos(a) * ring, math.sin(a) * ring
        d = 1 if k % 2 else -1
        tx, ty = -math.sin(a) * d, math.cos(a) * d                                # Each one faces the way it runs.
        mb.sphere((x, y, 0.08), 0.085, "rat" if k % 3 else "rat_dark", w, segments=5, rings=3, scale=(1.9 if abs(tx) > abs(ty) else 1.0, 1.9 if abs(ty) >= abs(tx) else 1.0, 0.9))
        mb.sphere((x + tx * 0.15, y + ty * 0.15, 0.1), 0.05, "rat_dark", w, segments=4, rings=3)
        mb.cylinder((x - tx * 0.14, y - ty * 0.14, 0.07), (x - tx * 0.4, y - ty * 0.4, 0.05), 0.012, 0.004, "sack", w, segments=4)
    pose = lambda t: ({"run_a": [(kit.Z, 360.0 * t)], "run_b": [(kit.Z, -360.0 * t)]}, {})   # noqa: E731
    mech = kit.Mech([("run_a", (0, 0, 0), (0, 0, 0.5), None), ("run_b", (0, 0, 0.02), (0, 0, 0.5), None)]).clip("scurry", 5.0, pose)
    kit.save(mb, FAMILY, "event_rats", COLORS, mech=mech)


def bounty():
    """A good year: the harvest heaped up for the feast."""
    mb = kit.begin()
    rnd = random.Random(53)
    mb.box((0, 0, 0.45), (2.6, 1.0, 0.08), "plank")
    for sx in (-1.1, 1.1):
        for sy in (-0.4, 0.4):
            mb.box((sx, sy, 0.22), (0.08, 0.08, 0.44), "pole_dark")
    for k in range(5):                                                           # Sheaves, pumpkins, baskets, bread.
        x = -2.0 + 1.0 * k
        mb.cylinder((x, 0.9, 0), (x, 0.9, 0.9), 0.2, 0.12, "wheat", segments=7)
        mb.cylinder((x, 0.9, 0.9), (x, 0.9, 1.25), 0.12, 0.3, "hay", segments=7)
        mb.cylinder((x, 0.9, 0.5), (x, 0.9, 0.58), 0.19, 0.19, "rope", segments=7)
    for k in range(6):
        mb.sphere((-1.5 + 0.6 * k + rnd.uniform(-0.1, 0.1), -0.9, 0.2), rnd.uniform(0.2, 0.3), "ember" if k % 2 else "flame", segments=7, rings=5, scale=(1, 1, 0.75))
    for k in range(4):
        x = -0.9 + 0.6 * k
        mb.cylinder((x, 0, 0.49), (x, 0, 0.7), 0.16, 0.22, "rope", segments=8)
        for i in range(4):
            mb.sphere((x + 0.08 * math.cos(i * 1.6), 0.08 * math.sin(i * 1.6), 0.72), 0.08, ("paint_red", "leaf", "flame", "wheat")[(i + k) % 4], segments=5, rings=3)
    mb.sphere((1.0, 0.25, 0.56), 0.16, "hay_dark", segments=6, rings=4, scale=(1.6, 1, 0.7))
    barrel(mb, 1.9, -0.2, 0.0, 0.85, 0.3)
    barrel(mb, -1.9, -0.2, 0.0, 0.85, 0.3)
    for sx in (-1.6, 1.6):
        mb.cylinder((sx, 0.5, 0), (sx, 0.5, 2.6), 0.05, 0.04, "pole", segments=6)
    w = {"garland": 1.0}
    for k in range(9):
        u0, u1 = k / 9, (k + 1) / 9
        p0 = (-1.6 + 3.2 * u0, 0.5, 2.5 - 0.5 * math.sin(math.pi * u0))
        p1 = (-1.6 + 3.2 * u1, 0.5, 2.5 - 0.5 * math.sin(math.pi * u1))
        rope(mb, p0, p1, 0.012)
        solid(mb, [(p0[0], 0.5, p0[2]), (p1[0], 0.5, p1[2]), ((p0[0] + p1[0]) / 2, 0.5, (p0[2] + p1[2]) / 2 - 0.3)], (0, 0.02, 0), ("paint_red", "flame", "leaf")[k % 3], w)
    pose = lambda t: ({"garland": [(kit.X, 10.0 * math.sin(TAU * t))]}, {})   # noqa: E731
    kit.save(mb, FAMILY, "event_bounty", COLORS, mech=kit.Mech([("garland", (0, 0.5, 2.5), (1.0, 0.5, 2.5), None)]).clip("sway", 3.0, pose))


MODELS = {
    "event_tornado": tornado,
    "event_storm_cloud": storm_cloud,
    "event_flood": flood,
    "event_sandbags": sandbags("event_sandbags", False),
    "event_sandbags_corner": sandbags("event_sandbags_corner", True),
    "event_sinkhole": sinkhole,
    "event_fissure": fissure,
    "event_drought_field": drought_field,
    "event_locusts": locusts,
    "event_wildfire": wildfire,
    "event_burnt_forest": burnt_forest,
    "event_lightning_tree": lightning_tree,
    "event_snowdrift": snowdrift("event_snowdrift", 0),
    "event_avalanche": snowdrift("event_avalanche", 1),
    "event_plague_cart": plague_cart,
    "event_rats": rats,
    "event_bounty": bounty,
}

kit.run(MODELS, FAMILY)
