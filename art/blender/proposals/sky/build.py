"""Sky proposals: what a fantasy town sends up into the air, and where it
ties it down. See ../LEEME.md.

    blender --background --factory-startup --python art/blender/proposals/sky/build.py -- [ids]
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import _kit as kit  # noqa: E402
import _shapes  # noqa: E402
import common  # noqa: E402
from _shapes import TAU, barrel, beam, crate, log, rope, sack, solid  # noqa: E402

FAMILY = "sky"
C = common.rgb
COLORS = {
    **_shapes.COLORS,
    "canvas": C(0xD8CCA8), "canvas_dark": C(0xB8AC88), "cloth_red": C(0xB8362E), "cloth_blue": C(0x2E5A9A), "cloth_yellow": C(0xD8A83A), "cloth_green": C(0x3E7A4A),
    "cloth_violet": C(0x6A4A9A), "brass": C(0xC9A441), "copper": C(0xB8703A), "flame": C(0xF2A23A), "ember": C(0xD8502A), "glow_blue": C(0x7AD8FF),
    "glow_white": C(0xF4F6FF), "cloud": C(0xECF0F4), "cloud_shade": C(0xC8D4E0), "shingle": C(0x6A5038), "shingle_dark": C(0x54402C), "wicker": C(0xB08A4A),
    "wicker_dark": C(0x8A6A34), "carpet": C(0x9A3A3A), "carpet_b": C(0xD8A83A), "carpet_c": C(0x2E5A9A), "paper": C(0xF0E6C8), "straw": C(0xC9A55A),
    "feather": C(0xE8E0D0), "feather_dark": C(0x8A7A62),
}


def envelope(mb, cx, cy, cz, long, r, mats, w=None, n=10, rings=9):
    """A cigar of gores along Y: the gas bag of an airship."""
    def at(u, a):
        rr = r * math.sin(math.pi * u) ** 0.7
        return (cx + math.cos(a) * rr, cy - long / 2 + long * u, cz + math.sin(a) * rr)
    for i in range(rings):
        u0, u1 = max(0.02, i / rings), min(0.98, (i + 1) / rings)
        for k in range(n):
            a0, a1 = TAU * k / n, TAU * (k + 1) / n
            p = [at(u0, a0), at(u0, a1), at(u1, a1), at(u1, a0)]
            mid = at((u0 + u1) / 2, (a0 + a1) / 2)
            off = ((cx - mid[0]) * 0.05, 0, (cz - mid[2]) * 0.05)
            solid(mb, p, off, mats[k % len(mats)], w)
    for u in (0.02, 0.98):
        tip = (cx, cy - long / 2 + long * (0.0 if u < 0.5 else 1.0), cz)
        base = [at(u, TAU * k / n) for k in range(n)]
        for k in range(n):
            solid(mb, [base[k], base[(k + 1) % n], tip], (0, 0.03 if u < 0.5 else -0.03, 0), mats[k % len(mats)], w)


def propeller(mb, x, y, z, r, bone, blades=3):
    w = {bone: 1.0}
    mb.cylinder((x, y, z), (x, y + 0.25, z), 0.09, 0.05, "brass", w, segments=6)
    for k in range(blades):
        a = TAU * k / blades
        solid(mb, [(x, y + 0.1, z), (x + math.cos(a - 0.25) * r, y + 0.06, z + math.sin(a - 0.25) * r), (x + math.cos(a + 0.12) * r, y + 0.16, z + math.sin(a + 0.12) * r)],
              (0, 0.03, 0), "plank_light", w)
    return (bone, (x, y, z), (x, y + 0.5, z), None)


def airship():
    """A great airship: 22 m of gas bag over a hull like a small ship."""
    mb = kit.begin()
    w = {"ship": 1.0}
    lift = 6.0
    envelope(mb, 0, 0, lift + 7.2, 22.0, 3.6, ("canvas", "cloth_red", "canvas", "canvas_dark"), w, 10, 9)
    for sx in (-1, 0, 1):                                                         # Tail fins.
        if sx:
            solid(mb, [(sx * 2.0, 8.0, lift + 7.2), (sx * 5.0, 10.5, lift + 7.2), (sx * 4.6, 11.0, lift + 7.2), (sx * 1.4, 10.4, lift + 7.2)], (0, 0, 0.1), "cloth_red", w)
        else:
            solid(mb, [(0, 8.0, lift + 9.4), (0, 10.5, lift + 12.2), (0, 11.0, lift + 11.8), (0, 10.4, lift + 8.6)], (0.1, 0, 0), "cloth_red", w)
    hull = [(-1.6, -5.5), (1.6, -5.5), (2.0, 0.0), (1.6, 4.5), (-1.6, 4.5), (-2.0, 0.0)]
    solid(mb, [(x, y, lift) for x, y in hull], (0, 0, 0.25), "plank_dark", w)       # The hull.
    solid(mb, [(-1.4, -5.5, lift), (1.4, -5.5, lift), (0, -8.0, lift + 0.6)], (0, 0, 0.25), "plank_dark", w)
    for k in range(len(hull)):
        (x0, y0), (x1, y1) = hull[k], hull[(k + 1) % len(hull)]
        solid(mb, [(x0, y0, lift + 0.2), (x1, y1, lift + 0.2), (x1 * 1.08, y1, lift + 1.3), (x0 * 1.08, y0, lift + 1.3)], (-x0 * 0.04, 0, 0), "plank" if k % 2 else "plank_light", w)
    solid(mb, [(-1.4, -5.5, lift + 0.2), (0, -8.0, lift + 0.8), (0, -8.2, lift + 1.6), (-1.5, -5.5, lift + 1.3)], (0.06, 0, 0), "plank", w)
    solid(mb, [(1.4, -5.5, lift + 0.2), (0, -8.0, lift + 0.8), (0, -8.2, lift + 1.6), (1.5, -5.5, lift + 1.3)], (-0.06, 0, 0), "plank_light", w)
    mb.box((0, 3.0, lift + 1.5), (2.6, 2.6, 1.9), "plank", w)                     # The cabin aft.
    solid(mb, [(-1.5, 1.5, lift + 2.4), (1.5, 1.5, lift + 2.4), (1.5, 4.6, lift + 2.4), (-1.5, 4.6, lift + 2.4)], (0, 0, 0.12), "shingle", w)
    for sx in (-1, 1):
        mb.box((sx * 1.31, 3.0, lift + 1.6), (0.04, 0.8, 0.6), "window", w)
        mb.cylinder((sx * 1.9, -3.0, lift + 1.3), (sx * 1.9, -3.0, lift + 1.75), 0.14, 0.14, "brass", w, segments=7)   # Lamps.
    mb.cylinder((0, -4.2, lift + 0.25), (0, -4.2, lift + 1.5), 0.05, 0.05, "pole", w, segments=5)   # The wheel.
    for k in range(8):
        a = TAU * k / 8
        beam(mb, (0, -4.15, lift + 1.5), (math.cos(a) * 0.35, -4.15, lift + 1.5 + math.sin(a) * 0.35), 0.015, "pole_dark", w)
    for k in range(3):
        crate(mb, -0.9 + 0.9 * k, -1.5, lift + 0.25, 0.6, 0.55, w)
    barrel(mb, 1.2, 0.4, lift + 0.25, 0.8, 0.3, w)
    for k in range(6):                                                           # The rigging that hangs the hull from the bag.
        y = -6.0 + 2.4 * k
        for sx in (-1, 1):
            rope(mb, (sx * 1.9, y, lift + 1.3), (sx * 2.6, y, lift + 5.2), 0.02, w)
    bones = [("ship", (0, 0, lift), (0, 0, lift + 2.0), None)]
    for sx, name in ((-1, "prop_l"), (1, "prop_r")):
        beam(mb, (sx * 1.9, 4.2, lift + 1.0), (sx * 3.0, 4.6, lift + 1.0), 0.07, "pole_dark", w)
        b = propeller(mb, sx * 3.0, 4.7, lift + 1.0, 1.0, name)
        bones.append((b[0], b[1], b[2], "ship"))
    mb.cylinder((0, -3.5, 0), (0, -3.5, 0.6), 0.5, 0.35, "stone", segments=8)     # Its mooring block and the line.
    rope(mb, (0, -3.5, 0.6), (0, -6.5, lift + 0.5), 0.025)
    for k in range(4):
        sack(mb, 1.5 + 0.5 * k, 2.0, 0.0, 0.26)

    def fly(t):
        bob = 0.25 * math.sin(TAU * t)
        return ({"prop_l": [(kit.Y, 360.0 * 4 * t)], "prop_r": [(kit.Y, -360.0 * 4 * t)], "ship": [(kit.Y, 1.5 * math.sin(TAU * t + 1.0))]}, {"ship": (0, 0, bob)})

    kit.save(mb, FAMILY, "sky_airship", COLORS, mech=kit.Mech(bones).clip("fly", 6.0, fly))


def mooring_mast():
    """Where airships tie up: a mast with a ring, a gangway and a stair."""
    mb = kit.begin()
    for sx in (-1, 1):
        for sy in (-1, 1):
            log(mb, (sx * 1.6, sy * 1.6, 0), (sx * 0.5, sy * 0.5, 9.0), 0.12)
    for z, k in ((2.5, 1.3), (5.0, 1.0), (7.5, 0.7)):
        for s in (-1, 1):
            beam(mb, (-k, s * k, z), (k, s * k, z), 0.05, "pole_dark")
            beam(mb, (s * k, -k, z), (s * k, k, z), 0.05, "pole_dark")
        beam(mb, (-k, -k, z), (k * 0.8, k * 0.8, z + 2.3), 0.035, "pole_dark")
    mb.box((0, 0, 9.05), (2.4, 2.4, 0.12), "plank")
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.cylinder((sx * 1.1, sy * 1.1, 9.1), (sx * 1.1, sy * 1.1, 10.1), 0.04, 0.04, "pole", segments=5)
    for s in (-1, 1):
        beam(mb, (-1.1, s * 1.1, 10.0), (1.1, s * 1.1, 10.0), 0.03, "pole")
    beam(mb, (1.1, -1.1, 10.0), (1.1, 1.1, 10.0), 0.03, "pole")                    # The side of the gangway stays open.
    mb.cylinder((0, 0, 9.1), (0, 0, 12.5), 0.09, 0.06, "pole", segments=6)
    for i in range(10):                                                          # The mooring ring.
        a0, a1 = TAU * i / 10, TAU * (i + 1) / 10
        beam(mb, (math.cos(a0) * 0.4, 0, 12.9 + math.sin(a0) * 0.4), (math.cos(a1) * 0.4, 0, 12.9 + math.sin(a1) * 0.4), 0.04, "iron")
    mb.box((-2.6, 0, 9.05), (3.0, 1.0, 0.1), "plank_light")                      # The gangway out over the void.
    for sy in (-0.5, 0.5):
        beam(mb, (-1.1, sy, 10.0), (-4.1, sy, 10.0), 0.02, "rope")
        beam(mb, (-4.1, sy, 9.1), (-4.1, sy, 10.0), 0.03, "pole")
        beam(mb, (-1.2, sy, 8.4), (-4.0, sy, 9.0), 0.04, "pole_dark")
    steps = 22                                                                   # A stair winding up inside.
    for k in range(steps):
        a = TAU * k / 8
        mb.box((math.cos(a) * 0.55, math.sin(a) * 0.55, 0.3 + 8.6 * k / steps), (0.8, 0.3, 0.06), "plank", rotation_z=a)
    mb.cylinder((0, 0, 0), (0, 0, 9.0), 0.08, 0.08, "pole_dark", segments=6)
    w = {"sock": 1.0}
    for k in range(3):
        mb.cylinder((0.1 + 0.4 * k, 0, 12.3), (0.5 + 0.4 * k, 0, 12.3), 0.16 - 0.035 * k, 0.125 - 0.035 * k, "cloth_red" if k % 2 == 0 else "canvas", w, segments=6)
    _shapes.lantern(mb, 1.1, -1.1, 10.1)
    crate(mb, 0.7, 0.7, 9.1, 0.5)
    pose = lambda t: ({"sock": [(kit.Z, 20.0 * math.sin(TAU * t)), (kit.Y, 6.0 * math.sin(TAU * 2 * t))]}, {})   # noqa: E731
    kit.save(mb, FAMILY, "sky_mooring_mast", COLORS, mech=kit.Mech([("sock", (0.08, 0, 12.3), (1.3, 0, 12.3), None)]).clip("wind", 3.0, pose))


def glider():
    """A hang glider on its launch ramp."""
    mb = kit.begin()
    solid(mb, [(-1.5, 3.0, 0), (1.5, 3.0, 0), (1.5, 3.0, 2.2), (-1.5, 3.0, 2.2)], (0, 0.2, 0), "pole_dark")     # The ramp: a platform that tips forward.
    solid(mb, [(-1.5, 3.2, 2.2), (1.5, 3.2, 2.2), (1.5, -1.5, 1.2), (-1.5, -1.5, 1.2)], (0, 0, 0.1), "plank")
    for sx in (-1.4, 1.4):
        for y, h in ((-1.4, 1.2), (0.8, 1.7)):
            mb.cylinder((sx, y, 0), (sx, y, h), 0.08, 0.07, "pole", segments=6)
        beam(mb, (sx, -1.4, 0.2), (sx, 0.8, 1.5), 0.04, "pole_dark")
    w = {"glider": 1.0}
    z = 3.4
    for sx in (-1, 1):                                                           # The wing: cloth on three spars.
        solid(mb, [(0, -1.3, z + 0.1), (sx * 4.2, 0.9, z + 0.4), (sx * 3.6, 1.5, z + 0.35), (0, 1.3, z)], (0, 0, 0.04), "cloth_yellow" if sx < 0 else "cloth_red", w)
        beam(mb, (0, -1.3, z + 0.12), (sx * 4.2, 0.9, z + 0.42), 0.035, "pole", w)
        beam(mb, (0, 0.2, z + 0.02), (sx * 3.8, 1.3, z + 0.35), 0.025, "pole", w)
        rope(mb, (sx * 2.5, 0.3, z + 0.25), (sx * 0.4, 0, z - 1.3), 0.01, w)
    beam(mb, (0, -1.4, z + 0.12), (0, 1.5, z), 0.04, "pole_dark", w)
    for sx in (-0.4, 0.4):                                                       # The frame the flier hangs in.
        beam(mb, (0, 0, z), (sx, -0.2, z - 1.3), 0.025, "pole", w)
    beam(mb, (-0.4, -0.2, z - 1.3), (0.4, -0.2, z - 1.3), 0.03, "pole_dark", w)
    solid(mb, [(-0.25, 0.1, z - 0.5), (0.25, 0.1, z - 0.5), (0.25, 1.2, z - 0.6), (-0.25, 1.2, z - 0.6)], (0, 0, 0.04), "leather", w)
    for k in range(2):
        rope(mb, (0, 0.2 + 0.8 * k, z), (0, 0.3 + 0.8 * k, z - 0.55), 0.01, w)
    pose = lambda t: ({"glider": [(kit.Y, 5.0 * math.sin(TAU * t)), (kit.X, 3.0 * math.sin(TAU * 2 * t))]}, {"glider": (0, 0, 0.12 * math.sin(TAU * 2 * t))})   # noqa: E731
    kit.save(mb, FAMILY, "sky_glider", COLORS, mech=kit.Mech([("glider", (0, 0, z), (0, 1.0, z), None)]).clip("hover", 4.0, pose))


def kite_signal():
    """A great kite flown from a winch: seen from as far as it flies high."""
    mb = kit.begin()
    mb.box((0, 0, 0.1), (1.4, 1.0, 0.2), "plank_dark")
    for sx in (-0.45, 0.45):
        mb.box((sx, 0, 0.6), (0.1, 0.14, 0.9), "pole")
    mb.cylinder((-0.4, 0, 0.9), (0.4, 0, 0.9), 0.18, 0.18, "rope", segments=8)
    mb.cylinder((-0.6, 0, 0.9), (0.6, 0, 0.9), 0.03, 0.03, "iron", segments=5)
    beam(mb, (0.6, 0, 0.9), (0.6, 0, 1.2), 0.02, "iron")
    w = {"kite": 1.0}
    top = (0.0, 3.0, 9.0)
    rope(mb, (0, 0, 1.05), top, 0.012)
    kx, ky, kz = top
    solid(mb, [(kx, ky, kz + 1.4), (kx + 1.0, ky, kz + 0.3), (kx, ky, kz - 1.6), (kx - 1.0, ky, kz + 0.3)], (0, 0.04, 0), "cloth_red", w)
    solid(mb, [(kx, ky - 0.01, kz + 0.9), (kx + 0.5, ky - 0.01, kz + 0.3), (kx, ky - 0.01, kz - 0.6), (kx - 0.5, ky - 0.01, kz + 0.3)], (0, 0.06, 0), "cloth_yellow", w)
    beam(mb, (kx, ky + 0.05, kz + 1.4), (kx, ky + 0.05, kz - 1.6), 0.02, "pole", w)
    beam(mb, (kx - 1.0, ky + 0.05, kz + 0.3), (kx + 1.0, ky + 0.05, kz + 0.3), 0.02, "pole", w)
    wt = {"tail": 1.0}
    for k in range(5):
        z0 = kz - 1.6 - 0.5 * k
        rope(mb, (kx, ky, z0), (kx, ky, z0 - 0.5), 0.008, wt)
        solid(mb, [(kx - 0.18, ky, z0 - 0.25), (kx + 0.18, ky, z0 - 0.15), (kx + 0.18, ky, z0 - 0.35), (kx - 0.18, ky, z0 - 0.45)], (0, 0.02, 0),
              ("cloth_blue", "cloth_yellow", "cloth_green")[k % 3], wt)

    def fly(t):
        sx, sz = 0.5 * math.sin(TAU * t), 0.25 * math.sin(TAU * 2 * t)
        return ({"kite": [(kit.Y, 10.0 * math.sin(TAU * t))], "tail": [(kit.Y, 22.0 * math.sin(TAU * 2 * t + 1.0))]}, {"kite": (sx, 0, sz), "tail": (0, 0, 0)})

    mech = kit.Mech([("kite", top, (kx, ky, kz + 1.0), None), ("tail", (kx, ky, kz - 1.6), (kx, ky, kz - 3.0), "kite")]).clip("fly", 4.0, fly)
    kit.save(mb, FAMILY, "sky_kite_signal", COLORS, mech=mech)


def flying_carpet(name, mats):
    def build():
        mb = kit.begin()
        w = {"carpet": 1.0}
        z = 1.2
        n = 6
        for k in range(n):
            y0, y1 = -1.5 + 3.0 * k / n, -1.5 + 3.0 * (k + 1) / n
            z0, z1 = z + 0.1 * math.sin(k * 1.4), z + 0.1 * math.sin((k + 1) * 1.4)
            solid(mb, [(-1.0, y0, z0), (1.0, y0, z0), (1.0, y1, z1), (-1.0, y1, z1)], (0, 0, 0.05), mats[0], w)
            solid(mb, [(-0.75, y0, z0 + 0.03), (0.75, y0, z0 + 0.03), (0.75, y1, z1 + 0.03), (-0.75, y1, z1 + 0.03)], (0, 0, 0.03), mats[1] if k in (0, n - 1) else mats[2], w)
        for sx in (-0.9, -0.3, 0.3, 0.9):
            for sy, zz in ((-1.5, z), (1.5, z + 0.1 * math.sin(n * 1.4))):
                mb.cylinder((sx, sy, zz), (sx, sy + (0.25 if sy > 0 else -0.25), zz - 0.1), 0.03, 0.01, "gold", w, segments=4)
        mb.sphere((0, 0.5, z + 0.25), 0.3, mats[1], w, segments=7, rings=4, scale=(1.2, 1.2, 0.5))   # A cushion, a lamp and the luggage.
        _shapes.lantern(mb, 0.6, -0.9, z + 0.1, w)
        mb.box((-0.5, -0.6, z + 0.28), (0.5, 0.4, 0.34), "plank_dark", w)
        for k in range(5):
            a = TAU * k / 5
            mb.sphere((math.cos(a) * 0.9, math.sin(a) * 1.3, z - 0.5 - 0.1 * (k % 2)), 0.06, "glow_blue", w, segments=4, rings=3)
        mb.cylinder((0, 0, 0), (0, 0, 0.02), 1.3, 1.3, "stone_dark", segments=10)                 # Its shadow on the landing stone.
        pose = lambda t: ({"carpet": [(kit.X, 3.0 * math.sin(TAU * t)), (kit.Y, 2.5 * math.sin(TAU * t + 1.5))]}, {"carpet": (0, 0, 0.15 * math.sin(TAU * t))})   # noqa: E731
        kit.save(mb, FAMILY, name, COLORS, mech=kit.Mech([("carpet", (0, 0, z), (0, 1.0, z), None)]).clip("hover", 4.0, pose))
    return build


def cloud_platform():
    """A tamed cloud with a railing: the lift of a mages' tower."""
    mb = kit.begin()
    w = {"cloud": 1.0}
    z = 3.0
    for k in range(9):
        a = TAU * k / 9
        mb.sphere((math.cos(a) * 1.3, math.sin(a) * 1.3, z), 0.9, "cloud" if k % 2 else "cloud_shade", w, segments=7, rings=5, scale=(1, 1, 0.6))
    mb.sphere((0, 0, z + 0.1), 1.4, "cloud", w, segments=8, rings=5, scale=(1, 1, 0.45))
    mb.cylinder((0, 0, z + 0.45), (0, 0, z + 0.55), 1.5, 1.5, "plank", w, segments=10)
    for k in range(10):
        a = TAU * k / 10
        if k == 7:
            continue                                                            # The way in (-Y).
        mb.cylinder((math.cos(a) * 1.4, math.sin(a) * 1.4, z + 0.55), (math.cos(a) * 1.4, math.sin(a) * 1.4, z + 1.5), 0.035, 0.03, "brass", w, segments=5)
        a1 = TAU * (k + 1) / 10
        if k != 6:
            beam(mb, (math.cos(a) * 1.4, math.sin(a) * 1.4, z + 1.45), (math.cos(a1) * 1.4, math.sin(a1) * 1.4, z + 1.45), 0.025, "brass", w)
    for k in range(3):
        mb.sphere((0.4 * (k - 1), 0.3 * (k % 2), z - 0.9 - 0.5 * k), 0.3 - 0.07 * k, "cloud_shade", w, segments=5, rings=3)
    mb.cylinder((0, 0, 0), (0, 0, 0.12), 1.8, 1.7, "stone", segments=10)          # The stone it comes down to.
    for k in range(5):
        a = TAU * k / 5
        mb.box((math.cos(a) * 1.3, math.sin(a) * 1.3, 0.14), (0.2, 0.05, 0.02), "glow_blue", rotation_z=a)
    pose = lambda t: ({"cloud": [(kit.Z, 20.0 * math.sin(TAU * t))]}, {"cloud": (0, 0, 2.0 * (0.5 - 0.5 * math.cos(TAU * t)))})   # noqa: E731
    kit.save(mb, FAMILY, "sky_cloud_platform", COLORS, mech=kit.Mech([("cloud", (0, 0, z), (0, 0, z + 1.0), None)]).clip("rise", 8.0, pose))


def griffin_roost():
    """A roost on a post where the flying mounts are kept: a great nest under a roof, with a ladder and a landing perch."""
    mb = kit.begin()
    log(mb, (0, 0, 0), (0, 0, 6.0), 0.3)
    for k in range(4):
        a = TAU * k / 4 + TAU / 8
        beam(mb, (0, 0, 4.2), (math.cos(a) * 2.2, math.sin(a) * 2.2, 6.0), 0.1, "pole_dark")
    mb.cylinder((0, 0, 6.0), (0, 0, 6.2), 3.0, 3.0, "plank", segments=10)
    for k in range(14):                                                          # The nest: a ring of woven branches full of straw.
        a0, a1 = TAU * k / 14, TAU * (k + 1) / 14
        mb.cylinder((math.cos(a0) * 2.0, math.sin(a0) * 2.0, 6.5), (math.cos(a1) * 2.0, math.sin(a1) * 2.0, 6.5 + 0.1 * (k % 2)), 0.32, 0.3, "wicker" if k % 2 else "wicker_dark", segments=6)
    mb.cylinder((0, 0, 6.2), (0, 0, 6.5), 1.9, 1.9, "straw", segments=10)
    for k in range(3):
        mb.sphere((-0.5 + 0.5 * k, 0.3 * (k % 2), 6.65), 0.3, "paper", segments=7, rings=5, scale=(1, 1, 1.3))   # Eggs.
    for k in range(4):
        a = TAU * k / 4
        x, y = math.cos(a) * 2.8, math.sin(a) * 2.8
        mb.cylinder((x, y, 6.2), (x, y, 9.0), 0.08, 0.07, "pole", segments=6)
    mb.cylinder((0, 0, 8.9), (0, 0, 10.6), 3.5, 0.15, "shingle", segments=8)
    mb.cylinder((0, 0, 8.9), (0, 0, 9.05), 3.55, 3.4, "shingle_dark", segments=8)
    beam(mb, (2.5, -2.0, 6.3), (5.5, -4.4, 6.6), 0.12, "pole")                    # The landing perch.
    beam(mb, (2.6, -2.1, 4.6), (4.6, -3.7, 6.4), 0.07, "pole_dark")
    for sx in (-0.25, 0.25):                                                     # The ladder up.
        beam(mb, (-3.2 + 0.0, sx, 0), (-2.6, sx, 6.2), 0.04, "pole")
    for k in range(14):
        u = (k + 0.5) / 14
        beam(mb, (-3.2 + 0.6 * u, -0.25, 6.2 * u), (-3.2 + 0.6 * u, 0.25, 6.2 * u), 0.025, "pole_dark")
    for k in range(6):                                                           # Feathers and bones below.
        solid(mb, [(1.0 + 0.3 * k, 1.0 + 0.2 * (k % 3), 0.02), (1.3 + 0.3 * k, 1.1 + 0.2 * (k % 3), 0.02), (1.1 + 0.3 * k, 1.5 + 0.2 * (k % 3), 0.02)], (0, 0, 0.02),
              "feather" if k % 2 else "feather_dark")
    barrel(mb, -1.2, -1.2, 0.0, 0.85, 0.3)
    w = {"flag": 1.0}
    mb.cylinder((0, 0, 10.6), (0, 0, 12.0), 0.03, 0.02, "pole", segments=5)
    solid(mb, [(0.03, -0.015, 11.95), (1.1, -0.015, 11.7), (0.03, -0.015, 11.45)], (0, 0.03, 0), "cloth_blue", w)
    pose = lambda t: ({"flag": [(kit.Z, 18.0 * math.sin(TAU * t))]}, {})   # noqa: E731
    kit.save(mb, FAMILY, "sky_griffin_roost", COLORS, mech=kit.Mech([("flag", (0.03, 0, 11.7), (1.1, 0, 11.7), None)]).clip("flutter", 1.8, pose))


def sky_lantern():
    """Paper lanterns let go into the night."""
    mb = kit.begin()
    mb.box((0, 0, 0.4), (1.6, 0.8, 0.06), "plank")
    for sx in (-0.7, 0.7):
        for sy in (-0.3, 0.3):
            mb.box((sx, sy, 0.2), (0.07, 0.07, 0.4), "pole_dark")
    for k in range(3):                                                           # Some still folded on the table.
        mb.box((-0.5 + 0.5 * k, 0, 0.47), (0.36, 0.36, 0.08), ("paper", "cloth_red", "cloth_yellow")[k])
    bones = []
    for k, (x, y, z, mat) in enumerate(((0.3, 0.4, 2.2, "paper"), (-1.2, 1.4, 4.0, "cloth_red"), (1.5, 2.2, 5.6, "cloth_yellow"), (-0.4, 3.0, 7.4, "paper"), (2.2, 0.6, 3.4, "cloth_red"))):
        w = {"l%d" % k: 1.0}
        mb.cylinder((x, y, z), (x, y, z + 0.55), 0.2, 0.3, mat, w, segments=8)
        mb.cylinder((x, y, z + 0.55), (x, y, z + 0.65), 0.3, 0.2, mat, w, segments=8)
        mb.cylinder((x, y, z + 0.02), (x, y, z + 0.2), 0.08, 0.0, "flame", w, segments=5)
        for i in range(4):
            a = TAU * i / 4
            rope(mb, (x + math.cos(a) * 0.19, y + math.sin(a) * 0.19, z), (x, y, z - 0.12), 0.004, w)
        bones.append(("l%d" % k, (x, y, z), (x, y, z + 0.6), None))

    def rise(t):
        return {}, {"l%d" % k: (0.2 * math.sin(TAU * t + k), 0.15 * math.sin(TAU * t + 2 * k), 0.3 * math.sin(TAU * t + 1.3 * k)) for k in range(5)}

    kit.save(mb, FAMILY, "sky_lanterns", COLORS, mech=kit.Mech(bones).clip("drift", 6.0, rise))


MODELS = {
    "sky_airship": airship,
    "sky_mooring_mast": mooring_mast,
    "sky_glider": glider,
    "sky_kite_signal": kite_signal,
    "sky_carpet_red": flying_carpet("sky_carpet_red", ("carpet", "carpet_b", "carpet_c")),
    "sky_carpet_blue": flying_carpet("sky_carpet_blue", ("carpet_c", "carpet_b", "carpet")),
    "sky_cloud_platform": cloud_platform,
    "sky_griffin_roost": griffin_roost,
    "sky_lanterns": sky_lantern,
}

kit.run(MODELS, FAMILY)
