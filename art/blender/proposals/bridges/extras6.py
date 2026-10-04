"""A seventh batch of the `bridges` family: piers of the elves and of the
orcs, an ice-fishing hut and a floating mill."""

import math

from parts import (B, MARBLE, ROOFS, TARRED, barrel, chain, flame, jit, lantern, planks_y, plate, rail, roof_y, rope,
                   sack, save)
from bridges import crystal_cluster
from boats import Hull, finish, floating, merge
from docks import DZ, wood_deck
from extras import skull
import _kit as kit

MODELS = {}


def model(name, fn, **kw):
    MODELS[name] = lambda: fn(name, **kw)


def elven_pier(name, pal=MARBLE):
    """A slender pier that ends in a round terrace with a crystal light."""
    b = B()
    planks_y(b, -3.0, 3.6, 2.4, z=DZ, mats=pal["deck"], step=0.6, thick=0.12, gap=0.02, ragged=0.0)
    ye = -4.6
    b.cyl((0, ye, DZ - 0.14), (0, ye, DZ), 2.1, pal["body"], seg=10)
    b.cyl((0, ye, DZ - 0.24), (0, ye, DZ - 0.14), 2.2, pal["cap"], seg=10)
    for y in (3.0, 1.2, -0.6, -2.4):   # Slim columns with a small arch between each pair.
        for s in (-1, 1):
            b.cyl((s * 0.95, y, -3.0), (s * 0.95, y, DZ - 0.12), 0.13, pal["trim"], r2=0.1, seg=7)
        b.beam((-0.95, y, DZ - 0.5), (0, y, DZ - 0.2), 0.12, 0.1, pal["trim"])
        b.beam((0.95, y, DZ - 0.5), (0, y, DZ - 0.2), 0.12, 0.1, pal["trim"])
    for k in range(5):
        a = 2 * math.pi * k / 5 + 0.3
        cx, cy = math.cos(a) * 1.6, ye + math.sin(a) * 1.6
        b.cyl((cx, cy, -3.0), (cx, cy, DZ - 0.2), 0.13, pal["trim"], r2=0.1, seg=7)
    for s in (-1, 1):   # Railing with gold caps, and lamp posts that curve over the walk.
        rail(b, [(s * 1.1, y, DZ) for y in (3.5, 2.0, 0.5, -1.0, -2.6)], h=0.9, post=0.07, mat=pal["body"],
             rail_mat=pal["body"], cap=pal["cap"], top=0.06)
        for y in (2.0, -1.0):
            pts = [(s * 1.1, y, DZ + 0.9), (s * 1.1, y, DZ + 2.2), (s * 0.9, y, DZ + 2.8), (s * 0.5, y, DZ + 3.0)]
            for p, q in zip(pts, pts[1:]):
                b.cyl(p, q, 0.05, pal["body"], seg=6)
            lantern(b, s * 0.5, y, DZ + 2.95, glow=pal["glow"], frame=pal["cap"], s=0.2)
    n = 10
    for k in range(n):
        a = 2 * math.pi * k / n + math.pi / 2
        if abs(math.cos(a)) < 0.6 and math.sin(a) > 0:
            continue   # The gap where the walk comes in.
        x, y = math.cos(a) * 1.95, ye + math.sin(a) * 1.95
        b.cyl((x, y, DZ), (x, y, DZ + 0.9), 0.04, pal["body"], seg=6)
        b.sphere((x, y, DZ + 0.95), 0.07, pal["cap"], seg=6, rings=4)
        a2 = 2 * math.pi * (k + 1) / n + math.pi / 2
        if not (abs(math.cos(a2)) < 0.6 and math.sin(a2) > 0):
            nxt = (math.cos(a2) * 1.95, ye + math.sin(a2) * 1.95, DZ + 0.85)
            b.beam((x, y, DZ + 0.85), nxt, 0.06, 0.06, pal["body"])
    b.cyl((0, ye, DZ), (0, ye, DZ + 0.5), 0.45, pal["trim"], r2=0.35, seg=8)
    crystal_cluster(b, 0, ye, DZ + 0.5, 1.0, seed=2)
    for k in range(3):   # Steps down to the water for the boats.
        b.box((0, ye - 2.1 - k * 0.3, DZ - 0.2 - k * 0.22), (1.4, 0.3, 0.2), pal["ring"][k % 2])
    save(b, name)


def orc_pier(name):
    """A rough pier of tarred logs with skull posts, a hide awning and a fire."""
    b = B()
    wood_deck(b, -1.3, 1.3, -4, 3, pal=TARRED)
    for k, (x, y) in enumerate(((-1.5, -3.8), (1.5, -3.8), (-1.5, -0.5), (1.5, 2.6))):
        b.cyl((x, y, -3.0), (x + jit(k, 0.12), y, DZ + 2.2 + jit(k, 0.3, 2)), 0.15, "wood_dark", r2=0.1, seg=6)
        skull(b, x + jit(k, 0.12), y, DZ + 2.45 + jit(k, 0.3, 2), 0.2)
        for j in range(2):
            b.cyl((x, y, DZ + 0.5 + j * 0.5), (x, y, DZ + 0.58 + j * 0.5), 0.17, "hide", seg=6)
    for k in range(7):   # Stakes that bristle from the end, against boarders.
        x = -1.2 + k * 0.4
        tip = (x + jit(k, 0.1), -4.7, DZ + 0.35 + jit(k, 0.15, 3))
        b.cyl((x, -3.9, DZ - 0.2), tip, 0.06, "wood_dark", r2=0.01, seg=5)
    # A hide stretched as an awning, a war drum and a fire in an iron bowl.
    for x in (-1.1, 1.1):
        b.cyl((x, 0.6, DZ), (x, 0.6, DZ + 2.0), 0.06, "tar", seg=5)
        b.cyl((x, 2.4, DZ), (x, 2.4, DZ + 1.6), 0.06, "tar", seg=5)
    ring = [(-1.25, 0.5, DZ + 2.0), (1.25, 0.5, DZ + 2.0), (1.25, 2.5, DZ + 1.6), (-1.25, 2.5, DZ + 1.6)]
    b.solid(ring, [(x, y, z + 0.04) for x, y, z in ring], "hide")
    b.cyl((0.6, 1.6, DZ), (0.6, 1.6, DZ + 0.6), 0.4, "wood_dark", r2=0.45, seg=9)
    b.cyl((0.6, 1.6, DZ + 0.6), (0.6, 1.6, DZ + 0.64), 0.46, "hide", seg=9)
    barrel(b, -0.7, 1.9, z=DZ, mat="wood_dark")
    fx, fy = 0.0, -2.6
    b.cyl((fx, fy, DZ), (fx, fy, DZ + 0.45), 0.08, "iron", seg=6)
    b.cyl((fx, fy, DZ + 0.45), (fx, fy, DZ + 0.7), 0.25, "iron", r2=0.42, seg=8)
    f = b.bone("flame")
    flame(f, fx, fy, DZ + 0.66, s=0.7)
    for k in range(2):
        rope(b, [(-1.5, -3.8 + k * 3.3, DZ + 1.2), (-2.3, -3.4 + k * 3.3, -0.3)], r=0.025)
    mech = kit.Mech([("flame", (fx, fy, DZ + 0.66), (fx, fy, DZ + 1.0), None)])
    mech.clip("flicker", 1.5, lambda t: ({"flame": [(kit.Z, 360 * t), (kit.X, 6 * math.sin(4 * math.pi * t))]},
                                         {"flame": (0.0, 0.0, 0.03 * math.sin(6 * math.pi * t))}))
    save(b, name, mech=mech)


def ice_fishing(name):
    """A hut on runners for fishing through the ice. It stands on the ice at Z = 0."""
    b = B()
    for s in (-1, 1):
        b.box((s * 0.75, 0.6, 0.06), (0.1, 2.6, 0.12), "wood")
        b.beam((s * 0.75, -0.7, 0.06), (s * 0.75, -1.0, 0.3), 0.1, 0.1, "wood")
    b.box((0, 0.6, 0.15), (1.7, 2.1, 0.08), "plank")
    w, d, h = 1.6, 2.0, 1.9
    for k in range(7):
        z = 0.2 + 0.135 + k * 0.27
        for s in (-1, 1):
            b.box((s * w / 2, 0.6, z), (0.05, d, 0.25), "wood" if k % 2 else "wood_light")
        b.box((0, 0.6 + d / 2, z), (w, 0.05, 0.25), "wood" if k % 2 else "wood_light")
        if k > 4:
            b.box((0, 0.6 - d / 2, z), (w, 0.05, 0.25), "wood" if k % 2 else "wood_light")
    for s in (-1, 1):
        b.box((s * 0.55, 0.6 - d / 2, 0.2 + 0.675), (0.5, 0.05, 1.35), "wood_light")
        for y in (0.6 - d / 2, 0.6 + d / 2):
            b.box((s * w / 2, y, 0.2 + h / 2), (0.09, 0.09, h), "timber")
    b.box((0, 0.6 - d / 2 - 0.03, 0.2 + 0.7), (0.62, 0.04, 1.3), "hide")
    ring = [(-w / 2 - 0.15, 0.6 - d / 2 - 0.2, 0.2 + h + 0.25), (w / 2 + 0.15, 0.6 - d / 2 - 0.2, 0.2 + h + 0.25),
            (w / 2 + 0.15, 0.6 + d / 2 + 0.2, 0.2 + h - 0.1), (-w / 2 - 0.15, 0.6 + d / 2 + 0.2, 0.2 + h - 0.1)]
    b.solid(ring, [(x, y, z + 0.07) for x, y, z in ring], "shingle")
    b.box((0, 0.6, 0.2 + h + 0.18), (w + 0.4, 0.5, 0.06), "cloth_white")      # Snow on the roof.
    b.cyl((0.5, 1.3, 0.2 + h - 0.1), (0.5, 1.3, 0.2 + h + 0.7), 0.07, "iron", seg=6)
    # The hole in the ice with a tip-up line, the catch and the gear.
    hx, hy = 0.0, -2.0
    b.cyl((hx, hy, 0.0), (hx, hy, 0.012), 0.42, "water", seg=10)
    for k in range(8):
        a = k * 0.8
        b.box((hx + math.cos(a) * 0.52, hy + math.sin(a) * 0.52, 0.04), (0.16, 0.12, 0.08), "crystal_glow", rz=a)
    b.beam((hx - 0.5, hy, 0.0), (hx - 0.2, hy, 0.5), 0.04, 0.04, "timber")
    b.beam((hx + 0.5, hy, 0.0), (hx + 0.2, hy, 0.5), 0.04, 0.04, "timber")
    b.cyl((hx - 0.3, hy, 0.45), (hx + 0.3, hy, 0.45), 0.025, "wood", seg=5)
    b.cyl((hx, hy, 0.45), (hx + 0.05, hy - 0.2, 0.9), 0.015, "wood_light", seg=4)
    rope(b, [(hx, hy, 0.45), (hx, hy, 0.0)], r=0.008)
    b.solid([(hx + 0.05, hy - 0.2, 0.9), (hx + 0.05, hy - 0.2, 0.78), (hx + 0.2, hy - 0.2, 0.84)],
            [(hx + 0.05, hy - 0.22, 0.9), (hx + 0.05, hy - 0.22, 0.78), (hx + 0.2, hy - 0.22, 0.84)], "cloth_red")
    for k in range(4):
        b.cyl((1.1 + k * 0.16, -1.7 + jit(k, 0.1), 0.05), (1.15 + k * 0.16, -1.25 + jit(k, 0.1), 0.05), 0.07, "fish",
              r2=0.015, seg=5)
    b.cyl((-1.1, -1.5, 0.0), (-1.1, -1.5, 0.3), 0.22, "thatch_dark", r2=0.28, seg=8)
    b.cyl((-1.3, -0.9, 0.0), (-1.45, -0.6, 1.5), 0.03, "wood", seg=5)
    b.cyl((-1.3, -0.9, 0.0), (-1.32, -0.86, 0.3), 0.06, "iron", r2=0.02, seg=5)
    save(b, name)


def ship_mill(name, roof="shingle"):
    """A mill on a moored hull: the current turns its wheel, with no weir or mill race."""
    root = B()
    b = root.bone("hull")
    bones = []
    h = Hull(10.0, 3.6, 0.5, 0.65, tm=0.45, bow_p=0.35, stern_w=0.8, stern_p=0.4, sheer_bow=0.25, sheer_stern=0.1,
             bow_rise=0.6, stern_rise=0.3, n=12, flat=0.88, thick=0.09)
    h.build(b, strakes=("wood_dark", "wood", "tar"), inner="wood")
    dz = 0.3
    h.deck(b, dz, 0.05, 0.97, mat="plank", alt="plank_b", steps=20)
    cy, cw, cd, ch = 0.6, 2.6, 5.0, 2.4
    b.box((0, cy, dz + ch / 2), (cw, cd, ch), "plaster")
    for x in (-cw / 2, cw / 2):
        for y in (-cd / 2, 0, cd / 2):
            b.box((x, cy + y, dz + ch / 2), (0.14, 0.14, ch), "timber")
        b.box((x, cy, dz + ch - 0.07), (0.14, cd, 0.14), "timber")
        b.box((x, cy, dz + 1.2), (0.12, cd, 0.12), "timber")
    for y in (-cd / 2, cd / 2):
        b.box((0, cy + y, dz + ch - 0.07), (cw, 0.14, 0.14), "timber")
    b.box((0, cy - cd / 2 - 0.03, dz + 0.85), (0.85, 0.06, 1.6), "door")
    b.box((-cw / 2 - 0.03, cy + 1.2, dz + 1.6), (0.06, 0.6, 0.5), "window")
    roof_y(b, 0, cy, cw, cd, dz + ch, 1.1, 0.3, list(ROOFS[roof]), rows=4, gables=(-1, 1), gable_mat="plaster")
    # The wheel hangs between the hull and a float, on the starboard side.
    wy, az, r = cy + 0.4, 0.7, 1.75
    xw = h.w(0.55) + 0.95
    float_x = xw + 1.05
    b.yz([(wy - 2.2, 0.35), (wy - 1.7, -0.3), (wy + 1.7, -0.3), (wy + 2.2, 0.35)], float_x - 0.3, float_x + 0.3,
         "wood_dark")
    for y in (wy - 1.5, wy + 1.5):
        b.box(((float_x + 1.3) / 2 + 0.3, y, 0.45), (float_x - 0.9, 0.16, 0.16), "timber")
    for x in (h.w(0.55) + 0.08, float_x):
        b.box((x, wy, az), (0.3, 0.34, 0.36), "timber")
    bones.append(("wheel", (xw, wy, az), (xw, wy, az + 0.4), "hull"))
    w = b.bone("wheel")
    w.cyl((1.0, wy, az), (float_x + 0.1, wy, az), 0.1, "timber", seg=7)
    n = 10
    for sx in (-0.5, 0.5):
        for i in range(n):
            a0, a1 = 2 * math.pi * i / n, 2 * math.pi * (i + 1) / n
            w.beam((xw + sx, wy + r * 0.85 * math.cos(a0), az + r * 0.85 * math.sin(a0)),
                   (xw + sx, wy + r * 0.85 * math.cos(a1), az + r * 0.85 * math.sin(a1)), 0.07, 0.1, "wood")
    for i in range(n):
        a0 = 2 * math.pi * i / n
        yi, zi = wy + 0.2 * math.cos(a0), az + 0.2 * math.sin(a0)
        yo, zo = wy + r * math.cos(a0), az + r * math.sin(a0)
        plate(w, (xw - 0.5, yi, zi), (xw + 0.5, yi, zi), (xw + 0.5, yo, zo), (xw - 0.5, yo, zo), 0.05,
              "plank" if i % 2 else "plank_b")
    # Moored by chains to two piles upstream; a gangplank to the bank; flour and grain on deck.
    for s in (-1, 1):
        root.cyl((s * 2.6, h.y(0) - 3.0, -3.0), (s * 2.6, h.y(0) - 3.0, 0.9), 0.14, "timber", seg=7)
        chain(root, (s * 2.6, h.y(0) - 3.0, 0.6), (s * h.w(0.08), h.y(0.08), h.top(0.08)), link=0.3)
    b.beam((-h.w(0.5), h.y(0.3), dz), (-h.w(0.5) - 3.0, h.y(0.3), 0.0 + 0.35), 0.7, 0.07, "plank_b")
    for k in range(4):
        sack(b, -0.9 + (k % 2) * 0.5, h.y(0.14) + (k // 2) * 0.55, z=dz)
    sack(b, -0.65, h.y(0.14) + 0.25, z=dz + 0.36)
    barrel(b, 0.9, h.y(0.16), z=dz)
    lantern(b, 0, cy - cd / 2 - 0.25, dz + ch - 0.1)
    turn = lambda t: ({"wheel": [(kit.X, 360 * t)]}, {})
    finish(root, name, bones, [("turn", 6.0, merge(floating(0.8, 0.5, 0.02), turn), None)])


model("dock_elven_pier", elven_pier)
model("dock_orc_pier", orc_pier)
model("dock_ice_fishing", ice_fishing)
model("boat_ship_mill", ship_mill)
model("boat_ship_mill_thatch", ship_mill, roof="thatch")
