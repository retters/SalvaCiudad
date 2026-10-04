"""A fifth batch of the `bridges` family: a noria, a pier light, a sea
shrine, an outrigger canoe and a reed boat."""

import math

from parts import B, flame, jit, lerp, planks_y, plate, rock, rope, sack, sag, save
from boats import Hull, finish, floating, merge, pennant, waving
from docks import DZ, WATER, pile, stone_quay, wood_deck
import _kit as kit

MODELS = {}


def model(name, fn, **kw):
    MODELS[name] = lambda: fn(name, **kw)


def noria(name):
    """A water-lifting wheel on the bank: the current turns it, its pots
    fill below and empty into a wooden flume at the top."""
    b = B()
    cy, cz, r = -1.6, 1.3, 2.3
    # Frames: one on the shore, one on piles in the water.
    for y in (cy + 0.9, cy - 0.9):
        for s in (-1, 1):
            b.beam((s * 1.5, y, -1.6 if y < cy else 0.0), (0, y, cz + 0.1), 0.14, 0.16, "timber")
        b.box((0, y, cz), (0.4, 0.2, 0.3), "timber")
        b.box((0, y, 0.25 if y > cy else -0.2), (2.4, 0.12, 0.14), "wood")
    b.box((0, cy + 0.9, 0.06), (3.6, 0.5, 0.2), "stone")
    w = b.bone("wheel")
    w.cyl((0, cy - 1.05, cz), (0, cy + 1.05, cz), 0.12, "timber", seg=8)
    n = 12
    for y in (cy - 0.45, cy + 0.45):
        for i in range(n):
            a0, a1 = 2 * math.pi * i / n, 2 * math.pi * (i + 1) / n
            w.beam((r * math.cos(a0), y, cz + r * math.sin(a0)), (r * math.cos(a1), y, cz + r * math.sin(a1)),
                   0.08, 0.12, "wood")
        for i in range(6):
            a0 = math.pi * i / 6
            w.beam((r * math.cos(a0), y, cz + r * math.sin(a0)), (-r * math.cos(a0), y, cz - r * math.sin(a0)), 0.06,
                   0.08, "timber")
    for i in range(n):
        a0 = 2 * math.pi * (i + 0.5) / n
        xi, zi = (r - 0.4) * math.cos(a0), cz + (r - 0.4) * math.sin(a0)
        xo, zo = (r + 0.15) * math.cos(a0), cz + (r + 0.15) * math.sin(a0)
        plate(w, (xi, cy - 0.45, zi), (xo, cy - 0.45, zo), (xo, cy + 0.45, zo), (xi, cy + 0.45, zi), 0.05,
              "plank" if i % 2 else "plank_b")
        px, pz = (r + 0.12) * math.cos(a0), cz + (r + 0.12) * math.sin(a0)
        w.cyl((px, cy + 0.5, pz), (px, cy + 0.82, pz), 0.14, "clay", r2=0.1, seg=6)
    # The flume that takes the water to the fields, on trestles toward the shore.
    fz = cz + r - 0.45
    for k in range(5):
        ya, yb = cy + 0.75 + k * 1.2, cy + 0.75 + (k + 1) * 1.2
        za, zb = fz - k * 0.12, fz - (k + 1) * 0.12
        b.beam((0.9, ya, za), (0.9, yb, zb), 0.5, 0.06, "plank")
        b.beam((0.9, ya, za + 0.03), (0.9, yb, zb + 0.03), 0.34, 0.05, "water")
        for s in (-1, 1):
            b.beam((0.9 + s * 0.27, ya, za + 0.1), (0.9 + s * 0.27, yb, zb + 0.1), 0.05, 0.22, "wood")
        if k % 2 == 1:
            for s in (-1, 1):
                b.beam((0.9 + s * 0.7, yb, 0.0), (0.9 + s * 0.2, yb, zb - 0.03), 0.09, 0.09, "timber")
    b.box((0.9, cy + 0.7, fz + 0.05), (0.7, 0.5, 0.08), "plank_b")
    mech = kit.Mech([("wheel", (0, cy, cz), (0, cy, cz + 0.4), None)])
    mech.clip("turn", 8.0, lambda t: {"wheel": [(kit.Y, 360 * t)]})
    save(b, name, mech=mech)


def pier_light(name, kind="wood"):
    """The end of a pier with a light for the boats that come in at night."""
    b = B()
    if kind == "wood":
        wood_deck(b, -1, 1, -1, 1)
        pile(b, 0.7, -0.7, DZ + 4.0, r=0.13)
        b.beam((0.7, -0.7, DZ + 3.9), (0.1, -0.7, DZ + 4.2), 0.08, 0.08, "timber")
        b.beam((0.7, -0.7, DZ + 3.2), (0.3, -0.7, DZ + 4.05), 0.06, 0.06, "wood")
        bx, by, bz = 0.05, -0.7, DZ + 3.7
        rope(b, [(0.1, -0.7, DZ + 4.2), (bx, by, bz + 0.35)], r=0.02, mat="iron")
        for k in range(8):   # Rungs up the post to feed the fire.
            b.box((0.7, -0.55, DZ + 0.4 + k * 0.42), (0.4, 0.05, 0.05), "wood")
    else:
        stone_quay(b, -1, 1, -1, 1)
        b.cyl((0, 0, DZ), (0, 0, DZ + 0.5), 0.6, "stone_dark", r2=0.5, seg=8)
        b.cyl((0, 0, DZ + 0.5), (0, 0, DZ + 2.8), 0.42, "stone", r2=0.34, seg=8)
        b.cyl((0, 0, DZ + 2.8), (0, 0, DZ + 3.0), 0.55, "stone_dark", seg=8)
        bx, by, bz = 0.0, 0.0, DZ + 3.05
        for k in range(4):
            a = k * math.pi / 2 + math.pi / 4
            b.box((math.cos(a) * 0.42, math.sin(a) * 0.42, DZ + 3.5), (0.06, 0.06, 1.0), "iron")
        b.cyl((0, 0, DZ + 4.0), (0, 0, DZ + 4.5), 0.62, "slate", r2=0.05, seg=8)
    b.cyl((bx, by, bz), (bx, by, bz + 0.3), 0.2, "iron", r2=0.32, seg=8)
    f = b.bone("flame")
    flame(f, bx, by, bz + 0.25, s=0.55)
    mech = kit.Mech([("flame", (bx, by, bz + 0.25), (bx, by, bz + 0.6), None)])
    mech.clip("flicker", 1.5, lambda t: ({"flame": [(kit.Z, 360 * t), (kit.X, 6 * math.sin(4 * math.pi * t))]},
                                         {"flame": (0.0, 0.0, 0.03 * math.sin(6 * math.pi * t))}))
    save(b, name, mech=mech)


def sea_shrine(name, paint="paint_red"):
    """A small shrine on a rock off the shore, with a gate standing in the water."""
    b = B()
    for k in range(10):
        a = k * 0.66
        rock(b, math.cos(a) * 1.6 + jit(k, 0.3), math.sin(a) * 1.6 + jit(k, 0.3, 2), 1.0 + jit(k, 0.25, 3), -2.0,
             0.25 + abs(jit(k, 0.35, 4)), seed=k, mat="stone_dark" if k % 2 else "stone")
    rock(b, 0, 0, 1.7, -2.0, 0.75, seed=30, mat="stone", sides=8, shrink=0.85)
    z = 0.75
    b.box((0, 0, z + 0.1), (1.6, 1.4, 0.2), "stone_light")
    for x in (-0.6, 0.6):
        for y in (-0.5, 0.5):
            b.box((x, y, z + 0.9), (0.1, 0.1, 1.5), paint)
    b.box((0, 0.5, z + 0.9), (1.2, 0.06, 1.3), "wood_light")
    b.box((0, 0.2, z + 0.5), (0.7, 0.4, 0.5), "stone")
    b.sphere((0, 0.2, z + 0.95), 0.22, "gold", seg=7, rings=5, scale=(1, 1, 1.3))
    b.cyl((0, -0.3, z + 0.2), (0, -0.3, z + 0.35), 0.2, "stone_dark", r2=0.28, seg=8)
    b.cyl((0, -0.3, z + 0.33), (0, -0.3, z + 0.35), 0.26, "water", seg=8)
    # A roof with upturned eaves.
    for s in (-1, 1):
        ring = [(-1.1, s * 1.0, z + 1.75), (1.1, s * 1.0, z + 1.75), (0.9, 0, z + 2.3), (-0.9, 0, z + 2.3)]
        b.solid(ring, [(px, py, pz + 0.1) for px, py, pz in ring], "slate" if s > 0 else "slate_dark")
        for e in (-1, 1):
            b.beam((e * 1.1, s * 1.0, z + 1.8), (e * 1.3, s * 1.2, z + 2.05), 0.08, 0.08, "gold")
    b.box((0, 0, z + 2.42), (2.0, 0.14, 0.12), paint)
    b.box((0, -0.5, z + 1.65), (1.3, 0.08, 0.1), paint)
    # A bell on its own bone, and a rope with paper strips.
    bell = b.bone("bell")
    bell.cyl((0.35, -0.5, z + 1.25), (0.35, -0.5, z + 1.5), 0.13, "bell", r2=0.06, seg=8)
    bell.cyl((0.35, -0.5, z + 1.5), (0.35, -0.5, z + 1.62), 0.015, "rope", seg=4)
    bell.cyl((0.35, -0.5, z + 0.75), (0.35, -0.5, z + 1.25), 0.02, "rope", seg=4)
    rope(b, sag((-0.6, -0.52, z + 1.5), (0.1, -0.52, z + 1.5), 0.1, 4), r=0.02)
    for k in range(3):
        b.box((-0.45 + k * 0.18, -0.52, z + 1.3), (0.07, 0.02, 0.22), "cloth_white")
    # Steps down to a landing stone, and the gate in the water toward -Y.
    for k in range(3):
        b.box((0, -0.95 - k * 0.3, z - 0.1 - k * 0.2), (1.0, 0.3, 0.2), "stone_light" if k % 2 else "stone")
    gy = -4.0
    for x in (-1.3, 1.3):
        b.cyl((x, gy, -2.0), (x * 0.96, gy, 3.3), 0.16, paint, r2=0.13, seg=8)
        b.cyl((x, gy, WATER - 0.1), (x, gy, WATER + 0.25), 0.2, "charcoal", seg=8)
    b.box((0, gy, 3.4), (3.6, 0.26, 0.2), paint)
    b.box((0, gy, 3.55), (3.9, 0.3, 0.12), "charcoal")
    b.box((0, gy, 2.75), (3.0, 0.18, 0.16), paint)
    b.box((0, gy, 3.08), (0.16, 0.2, 0.5), paint)
    mech = kit.Mech([("bell", (0.35, -0.5, z + 1.62), (0.35, -0.5, z + 1.9), None)])
    mech.clip("ring", 2.0, lambda t: {"bell": [(kit.X, 16 * math.sin(4 * math.pi * t) * (1 - t))]})
    save(b, name, mech=mech)


def outrigger(name, sail_mats=("thatch", "thatch_dark")):
    root = B()
    b = root.bone("hull")
    bones = []
    h = Hull(7.0, 0.85, 0.3, 0.42, tm=0.5, bow_p=0.7, stern_p=0.7, sheer_bow=0.45, sheer_stern=0.35, bow_rise=0.9,
             stern_rise=0.85, n=12, flat=0.6, thick=0.06)
    h.build(b, strakes=("wood", "wood_dark", "wood_dark"), inner="wood_light", rail="paint_red", keel=False)
    h.deck(b, 0.04, 0.05, 0.95, mat="plank_b")
    for t in (0.3, 0.5, 0.7):
        h.thwart(b, t, drop=0.1, wide=0.2)
    # The float, on two curved booms to starboard, and a small platform between the hulls.
    ax = 2.3
    pts = [(ax, -2.2, 0.25), (ax, -1.6, 0.02), (ax, 1.4, 0.02), (ax, 2.0, 0.2)]
    for k, (p, q) in enumerate(zip(pts, pts[1:])):
        b.cyl(p, q, (0.08, 0.17, 0.17)[k], "wood_light", r2=(0.17, 0.17, 0.07)[k], seg=7)
    for y in (h.y(0.35), h.y(0.65)):
        boom = [(-0.5, y, h.top(0.5) + 0.03), (1.2, y, h.top(0.5) + 0.2), (ax, y, 0.2)]
        for p, q in zip(boom, boom[1:]):
            b.cyl(p, q, 0.05, "timber", seg=6)
        b.cyl((ax, y, 0.02), (ax, y, 0.22), 0.07, "rope", seg=6)
        b.cyl((0.42, y, h.top(0.5) + 0.02), (0.42, y, h.top(0.5) + 0.14), 0.08, "rope", seg=6)
    planks_y(b, h.y(0.37), h.y(0.63), 0.9, z=h.top(0.5) + 0.2, xc=1.05, step=0.3, thick=0.04)
    sack(b, 1.05, h.y(0.45), z=h.top(0.5) + 0.2, r=0.22)
    sack(b, 1.1, h.y(0.56), z=h.top(0.5) + 0.2, r=0.2)
    # A crab-claw sail between two spars, on a short mast.
    ym = h.y(0.42)
    b.cyl((0, ym, 0.04), (0, ym, 3.2), 0.06, "timber", r2=0.045, seg=6)
    bones.append(("sail0", (0, ym, 2.9), (0, ym, 3.2), "hull"))
    s = b.bone("sail0")
    tack = (0, h.y(0.12), h.top(0.12) + 0.1)
    upper = (0.5, ym + 2.2, 5.6)
    lower = (1.0, ym + 3.0, 2.0)
    s.cyl(tack, upper, 0.04, "wood_light", seg=5)
    s.cyl(tack, lower, 0.04, "wood_light", seg=5)
    strips = 5
    for j in range(strips):
        t0, t1 = j / strips, (j + 1) / strips
        def along(spar, t):
            return tuple(lerp(tack[k], spar[k], t) for k in range(3))

        if j == 0:   # The first strip starts at the tack: a triangle.
            ring = [tack, along(lower, t1), along(upper, t1)]
        else:
            ring = [along(upper, t0), along(lower, t0), along(lower, t1), along(upper, t1)]
        s.solid(ring, [(x + 0.03, y, z) for x, y, z in ring], sail_mats[j % len(sail_mats)])
    rope(b, [(0, ym, 3.1), (0.25, ym + 1.1, 3.8)], r=0.012)
    pennant(b, bones, ym, 3.2, mat="cloth_red", size=0.5)
    b.cyl((-0.35, h.y(0.9), h.top(0.9) + 0.5), (-0.5, h.y(1.0) + 0.6, -0.6), 0.03, "wood", seg=5)
    b.beam((-0.47, h.y(1.0) + 0.35, -0.1), (-0.5, h.y(1.0) + 0.62, -0.62), 0.03, 0.2, "wood_light")
    swing = lambda t: ({"sail0": [(kit.Z, 4 * math.sin(4 * math.pi * t))]}, {})
    finish(root, name, bones, [("bob", 3.0, merge(floating(2.0, 1.5, 0.03), waving(2, 10)), None),
                               ("sail", 4.0, merge(floating(2.5, 1.5, 0.04), swing, waving()), 3.0)])


def reed_boat(name):
    root = B()
    b = root.bone("hull")
    bones = []
    # Three bundles of reeds, the middle one lower, with the ends tied up into a point.
    for x, r, dz in ((-0.34, 0.24, 0.06), (0.34, 0.24, 0.06), (0.0, 0.26, -0.08)):
        pts = [(x * 0.2, -2.3, 0.75), (x * 0.7, -1.7, 0.25 + dz), (x, -0.8, 0.05 + dz), (x, 0.8, 0.05 + dz),
               (x * 0.7, 1.6, 0.2 + dz), (x * 0.25, 2.1, 0.55)]
        rs = (0.08, r * 0.8, r, r, r * 0.8, 0.09)
        for k, (p, q) in enumerate(zip(pts, pts[1:])):
            b.cyl(p, q, rs[k], "hay" if abs(x) > 0.1 else "thatch_dark", r2=rs[k + 1], seg=7)
        for y in (-0.7, 0.0, 0.7):   # Lashings around the straight part of each bundle.
            b.cyl((x, y - 0.035, 0.05 + dz), (x, y + 0.035, 0.05 + dz), r * 1.06, "rope", seg=7)
    for y in (-1.75, 1.65):   # The three bundles tied together where they rise.
        b.cyl((0, y - 0.04, 0.3), (0, y + 0.04, 0.3), 0.36, "rope", seg=7)
    b.box((0, 0.3, 0.3), (0.7, 0.9, 0.05), "thatch")
    sack(b, 0.0, -0.6, z=0.22, r=0.2)
    bones.append(("paddle", (0.45, 0.6, 0.5), (0.45, 0.6, 0.8), "hull"))
    p = b.bone("paddle")
    p.cyl((0.35, 0.5, 1.2), (0.6, 0.75, -0.25), 0.025, "wood", seg=5)
    p.beam((0.57, 0.72, -0.05), (0.62, 0.78, -0.42), 0.15, 0.03, "wood_light")
    stroke = lambda t: ({"paddle": [(kit.X, 20 * math.sin(2 * math.pi * t)),
                                    (kit.Y, 6 * (1 - math.cos(2 * math.pi * t)))]}, {})
    finish(root, name, bones, [("bob", 3.0, floating(3.5, 2.0, 0.03), None),
                               ("row", 1.8, merge(floating(2.0, 1.5, 0.02), stroke), 1.1)])


model("dock_noria", noria)
model("dock_pier_light", pier_light)
model("dock_quay_light", pier_light, kind="stone")
model("dock_sea_shrine", sea_shrine)
model("boat_outrigger", outrigger)
model("boat_reed", reed_boat)
