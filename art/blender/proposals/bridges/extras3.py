"""A fourth batch of the `bridges` family: a truss bridge, a log bridge for
carts, a causeway, a winter crossing over the ice, a boat ramp, a mussel
farm, a fish pen, a signal mast, a fish market, a junk and an ice yacht."""

import math

from parts import (B, BRICK, STONE, TARRED, WOOD, arch, barrel, blocks, crate, flame, jit, lantern, lerp, log, net,
                   planks_x, planks_y, rail, road, rock, rope, sack, sag, save, smoothstep)
from bridges import stone_bridge
from boats import Hull, finish, floating, flutter, merge, pennant, rudder, sail, waving
from docks import DZ, WATER, fish, ladder, mooring_post, pile, wood_deck
from extras import gate_tower
from extras2 import harbor_chain, sluice
import _kit as kit

MODELS = {}


def model(name, fn, **kw):
    MODELS[name] = lambda: fn(name, **kw)


# --- Bridges -------------------------------------------------------------------------


def truss(name, pal=WOOD, length=12.0, width=3.6):
    b = B()
    half = length / 2
    zd = 0.3
    high = 2.6
    for s in (-1, 1):   # Stone abutments: no pier stands in the water.
        b.box((s * (half - 0.6), 0, -1.45), (1.2, width + 0.5, 3.1), "stone")
        b.box((s * (half - 0.6), 0, 0.03), (1.3, width + 0.6, 0.16), "stone_dark")
        blocks(b, s * (half - 1.1), s * (half - 0.1), -width / 2 - 0.25, -2.6, -0.3, STONE, face=-1, count=4, seed=s)
        b.beam((s * (half + 0.5), 0, 0.0), (s * half, 0, zd - 0.02), width - 0.6, 0.08, pal["deck"][1])
    for y in (-width / 2 + 0.5, 0.0, width / 2 - 0.5):
        b.box((0, y, zd - 0.19), (length, 0.18, 0.24), pal["trim"])
    for k in range(7):
        x = -half + 0.5 + k * (length - 1.0) / 6
        b.box((x, 0, zd - 0.37), (0.18, width + 0.3, 0.16), pal["trim"])
    planks_x(b, -half, half, width - 0.5, z=zd, mats=pal["deck"])
    xs = [-4.0, -2.0, 0.0, 2.0, 4.0]
    for s in (-1, 1):
        y = s * (width / 2 - 0.05)
        b.box((0, y, zd + 0.1), (length, 0.2, 0.26), pal["trim"])                      # Bottom chord.
        b.box((0, y, zd + high), (8.0 + 0.2, 0.2, 0.24), pal["trim"])                   # Top chord.
        for e in (-1, 1):
            b.beam((e * (half - 0.1), y, zd + 0.2), (e * 4.0, y, zd + high), 0.2, 0.24, pal["trim"])
            b.box((e * 4.0, y + s * 0.11, zd + high), (0.5, 0.03, 0.34), "iron")
            b.box((e * (half - 0.25), y + s * 0.11, zd + 0.15), (0.6, 0.03, 0.36), "iron")
        for x in xs:
            b.box((x, y, zd + high / 2 + 0.1), (0.16, 0.16, high - 0.2), pal["body"])
        for xa, xb in zip(xs, xs[1:]):
            lo, hi = (xa, xb) if xa < 0 else (xb, xa)
            b.beam((lo, y, zd + 0.22), (hi, y, zd + high - 0.12), 0.1, 0.14, pal["body"])
        b.box((0, y, zd + 1.0), (8.0, 0.06, 0.08), pal["body"])
    for x in (-4.0, 0.0, 4.0):   # The frames across that keep the two trusses upright.
        b.box((x, 0, zd + high), (0.16, width, 0.18), pal["trim"])
        for s in (-1, 1):
            b.beam((x, s * (width / 2 - 0.1), zd + high - 0.7), (x, s * (width / 2 - 0.8), zd + high - 0.08), 0.1, 0.1,
                   pal["body"])
    for e in (-1, 1):
        lantern(b, e * 4.0, 0, zd + high - 0.1)
    save(b, name)


def log_cart(name, length=8.0, width=3.0):
    b = B()
    half = length / 2
    n = 7
    for i in range(n):
        y = -width / 2 + 0.22 + i * (width - 0.44) / (n - 1)
        log(b, (-half + jit(i, 0.15), y, 0.0), (half + jit(i, 0.15, 2), y, 0.0), 0.22, seg=7)
    for s in (-1, 1):
        log(b, (s * (half - 0.6), -width / 2 - 0.3, -0.38), (s * (half - 0.6), width / 2 + 0.3, -0.38), 0.2, seg=7)
        log(b, (-half + 0.3, s * (width / 2 - 0.15), 0.36), (half - 0.3, s * (width / 2 - 0.15), 0.36), 0.16, seg=7)
        for x in (-half + 0.8, 0.0, half - 0.8):
            b.cyl((x, s * (width / 2 - 0.15), 0.3), (x, s * (width / 2 - 0.15), 0.42), 0.19, "rope", seg=7)
    # Earth and gravel packed over the logs make it fit for carts.
    for k in range(8):
        xa, xb = -half + 0.3 + k * (length - 0.6) / 8, -half + 0.3 + (k + 1) * (length - 0.6) / 8
        b.box(((xa + xb) / 2, jit(k, 0.05), 0.22), (xb - xa + 0.02, width - 0.75 + jit(k, 0.1, 3), 0.08),
              "soil" if k in (0, 7) else "road")
    for k in range(2):
        b.cyl((jit(k, 1.0), -0.3, -3.0), (jit(k, 1.0), -0.3, -0.2), 0.14, "timber", seg=7)
        b.cyl((jit(k, 1.0), 0.6, -3.0), (jit(k, 1.0), 0.6, -0.2), 0.14, "timber", seg=7)
    save(b, name)


def causeway(name, pal=STONE, length=4.0, width=4.0, high=0.6):
    b = B()
    half = length / 2

    def top(x):
        return high

    # A raised road over marsh or shallows, with a culvert that lets the water through.
    arch(b, 0, 0.45, 0.45, -0.5, top, -width / 2, width / 2, pal, n=5, ring=0.18)
    for e in (-1, 1):
        xa, xb = sorted((e * 0.63, e * half))
        b.xz([(xa, -1.6), (xb, -1.6), (xb, high), (xa, high)], -width / 2, width / 2, pal["body"])
        blocks(b, xa + 0.1, xb - 0.1, -width / 2, -0.3, high - 0.2, pal, face=-1, count=3, seed=e)
        blocks(b, xa + 0.1, xb - 0.1, width / 2, -0.3, high - 0.2, pal, face=1, count=3, seed=e + 3)
    b.box((0, 0, -1.05), (1.3, width, 1.1), pal["body"])
    road(b, -half, half, -width / 2 + 0.25, width / 2 - 0.25, top, pal["road"])
    for s in (-1, 1):
        b.box((0, s * (width / 2 - 0.12), high + 0.06), (length, 0.24, 0.12), pal["cap"])
        for x in (-half + 0.5, half - 0.5):
            b.box((x, s * (width / 2 - 0.12), high + 0.3), (0.3, 0.26, 0.5), pal["trim"])
        # Loose stones at the foot of each face.
        for k in range(4):
            rock(b, -half + 0.5 + k * 1.0 + jit(k, 0.2, s), s * (width / 2 + 0.3), 0.4, -1.2, -0.1 + jit(k, 0.1, s + 2),
                 seed=k + s, mat="stone_dark" if k % 2 else "stone")
    save(b, name)


def ice_crossing(name, length=10.0, width=3.0):
    b = B()
    half = length / 2
    ice = WATER
    # Board ramps from each bank down to the ice, and a path of straw between them.
    for s in (-1, 1):
        b.beam((s * half, 0, 0.0), (s * (half - 1.2), 0, ice + 0.03), width - 0.6, 0.07, "plank")
        for y in (-0.9, 0.9):
            b.beam((s * half, y, -0.08), (s * (half - 1.2), y, ice - 0.05), 0.12, 0.12, "timber")
    for k in range(10):
        xa = -half + 1.2 + k * (length - 2.4) / 10
        xb = xa + (length - 2.4) / 10
        b.box(((xa + xb) / 2, jit(k, 0.08), ice + 0.02), (xb - xa + 0.02, width - 1.0 + jit(k, 0.2, 2), 0.04),
              "hay" if k % 2 else "thatch_dark")
    # A crack bridged with planks.
    b.box((0.9, 0, ice + 0.005), (0.35, width + 1.0, 0.01), "water")
    for y in (-0.6, 0.0, 0.6):
        b.box((0.9, y, ice + 0.06), (1.3, 0.45, 0.05), "plank_b")
    # Stakes with red rags mark the safe way, with a rope between them.
    for s in (-1, 1):
        pts = []
        for k in range(5):
            x = -half + 1.3 + k * (length - 2.6) / 4
            y = s * (width / 2 - 0.2)
            b.cyl((x, y, ice - 0.4), (x + jit(k, 0.06, s), y, ice + 1.3), 0.045, "timber", seg=5)
            b.solid([(x, y, ice + 1.28), (x, y, ice + 1.0), (x + 0.35, y, ice + 1.1)],
                    [(x, y + 0.02, ice + 1.28), (x, y + 0.02, ice + 1.0), (x + 0.35, y + 0.02, ice + 1.1)], "cloth_red")
            pts.append((x, y, ice + 0.95))
        for p, q in zip(pts, pts[1:]):
            rope(b, sag(p, q, 0.12, 4), r=0.015)
    # A brazier on a sledge to warm up half way.
    sx, sy = -1.4, width / 2 + 0.6
    for y in (-0.3, 0.3):
        b.box((sx, sy + y, ice + 0.05), (1.3, 0.07, 0.1), "wood")
    b.box((sx, sy, ice + 0.14), (1.0, 0.7, 0.06), "plank")
    b.cyl((sx, sy, ice + 0.17), (sx, sy, ice + 0.45), 0.25, "iron", r2=0.35, seg=8)
    fl = b.bone("flame")
    flame(fl, sx, sy, ice + 0.42, s=0.55)
    mech = kit.Mech([("flame", (sx, sy, ice + 0.42), (sx, sy, ice + 0.8), None)])
    mech.clip("flicker", 1.5, lambda t: ({"flame": [(kit.Z, 360 * t), (kit.X, 6 * math.sin(4 * math.pi * t))]},
                                         {"flame": (0.0, 0.0, 0.03 * math.sin(6 * math.pi * t))}))
    save(b, name, mech=mech)


# --- Works on the shore --------------------------------------------------------------


def boat_ramp(name):
    b = B()

    def zs(y):
        return lerp(0.1, -0.9, (3.5 - y) / 7.0)

    for x in (-0.7, 0.7):
        b.beam((x, 3.5, zs(3.5)), (x, -3.5, zs(-3.5)), 0.18, 0.18, "timber")
    for k in range(8):
        y = 3.1 - k * 0.9
        log(b, (-1.2, y, zs(y) + 0.14), (1.2, y, zs(y) + 0.14), 0.09, seg=6)
    # A capstan to haul the boats out, and a boat turned over on trestles for the winter.
    b.cyl((0, 4.3, 0.0), (0, 4.3, 0.8), 0.2, "wood", seg=8)
    b.cyl((0, 4.3, 0.8), (0, 4.3, 0.9), 0.25, "timber", seg=8)
    for k in range(4):
        a = k * math.pi / 2 + 0.3
        b.cyl((0, 4.3, 0.68), (math.cos(a) * 0.8, 4.3 + math.sin(a) * 0.8, 0.7), 0.03, "wood_light", seg=5)
    for k in range(3):
        b.cyl((0, 4.3, 0.25 + k * 0.08), (0, 4.3, 0.32 + k * 0.08), 0.23, "rope", seg=8)
    rope(b, [(0, 4.1, 0.4), (0, 1.9, zs(1.9) + 0.5)], r=0.02)
    h = Hull(3.8, 1.4, 0.28, 0.38, stern_w=0.55, sheer_bow=0.2, sheer_stern=0.08, stern_rise=0.3, n=9, thick=0.06)
    hb = b.at(dy=0.2, dz=zs(0.2) + 0.55)
    h.build(hb, strakes=("paint_blue", "wood_light", "wood"))
    h.deck(hb, 0.04, 0.08, 0.995, mat="plank_b")
    for t in (0.36, 0.64):
        h.thwart(hb, t)
    up = b.at(dx=2.6, dy=2.2, dz=1.1, rz=10).turn("Y", 180)
    h.build(up, strakes=("wood", "wood_dark", "tar"))
    for y in (1.2, 3.2):
        for s in (-1, 1):
            b.beam((2.6 + s * 0.6, y, 0.0), (2.6 + s * 0.15, y, 0.72), 0.07, 0.07, "timber")
        b.box((2.6, y, 0.72), (1.4, 0.1, 0.1), "timber")
    for k in range(2):
        b.cyl((-2.0 + k * 0.25, 3.8, 0.0), (-2.2 + k * 0.25, 3.0, 2.3), 0.03, "wood_light", seg=5)
        b.box((-2.2 + k * 0.25, 3.0, 2.3), (0.03, 0.16, 0.5), "wood_light")
    barrel(b, -2.2, 1.6, mat="tar")
    save(b, name)


def mussel_farm(name):
    b = B()
    for ix in range(4):
        x = -3.0 + ix * 2.0
        pts = []
        for iy in range(5):
            y = -3.6 + iy * 1.6
            pile(b, x + jit(ix * 5 + iy, 0.06), y, 0.95 + jit(ix + iy, 0.15, 2), deep=-2.5, r=0.08)
            pts.append((x, y, 0.75))
        for p, q in zip(pts, pts[1:]):
            rope(b, sag(p, q, 0.45, 6), r=0.025)
            for k in (1, 3, 5):   # Ropes of mussels hang into the water.
                t = k / 6
                px, py = lerp(p[0], q[0], t), lerp(p[1], q[1], t)
                pz = 0.75 - 0.45 * 4 * t * (1 - t)
                b.cyl((px, py, pz), (px, py, pz - 1.7), 0.012, "rope", seg=4)
                for j in range(4):
                    b.sphere((px + jit(k + j, 0.03), py, pz - 0.3 - j * 0.35), 0.11 + 0.02 * j,
                             "charcoal" if (j + k) % 2 else "slate_dark", seg=5, rings=3, scale=(1, 1, 1.5))
    # A work raft with baskets, moored between two rows.
    for i in range(5):
        log(b, (-0.9 + i * 0.45, -1.3, WATER + 0.03), (-0.9 + i * 0.45, 1.3, WATER + 0.03), 0.2, seg=7)
    planks_y(b, -1.1, 1.1, 2.0, z=WATER + 0.32, step=0.3)
    for k in range(2):
        cx, cy = -0.4 + k * 0.8, 0.3 - k * 0.6
        b.cyl((cx, cy, WATER + 0.32), (cx, cy, WATER + 0.6), 0.24, "thatch_dark", r2=0.3, seg=8)
        b.sphere((cx, cy, WATER + 0.6), 0.24, "slate_dark", seg=6, rings=4, scale=(1, 1, 0.45))
    save(b, name)


def fish_pen(name):
    b = B()
    r = 2.6
    corners = [(-r, -r), (r, -r), (r, r), (-r, r)]
    for i in range(4):
        (xa, ya), (xb, yb) = corners[i], corners[(i + 1) % 4]
        for k in range(4):
            t = k / 4
            pile(b, lerp(xa, xb, t), lerp(ya, yb, t) - 1.5, 0.45, deep=-2.5, r=0.09)
        net(b, (xa, ya - 1.5, 0.3), (xb, yb - 1.5, 0.3), (xa, ya - 1.5, -1.9), (xb, yb - 1.5, -1.9), n=10, r=0.015)
        b.beam((xa, ya - 1.5, 0.35), (xb, yb - 1.5, 0.35), 0.08, 0.1, "timber")
    # A walkway from the shore and along the near side, with a feeding stage.
    wood_deck(b, -0.6, 0.6, 1.1, 4.0, brace=False)
    wood_deck(b, -3.0, 3.0, 0.3, 1.1, brace=False)
    wood_deck(b, 1.4, 3.0, -1.2, 0.3, brace=False)
    rail(b, [(-2.9, 0.35, DZ), (-1.0, 0.35, DZ), (1.0, 0.35, DZ)], h=0.8, mid=False)
    barrel(b, 2.5, -0.6, z=DZ, h=0.6, r=0.26)
    b.cyl((1.8, -0.5, DZ), (1.8, -0.5, DZ + 0.3), 0.24, "thatch_dark", r2=0.3, seg=8)
    b.cyl((2.2, 0.0, DZ), (2.6, -1.4, DZ + 1.6), 0.025, "wood_light", seg=5)
    b.cyl((2.6, -1.4, DZ + 1.6), (2.62, -1.46, DZ + 1.7), 0.2, "net", seg=7)
    for k in range(7):   # Fish near the surface.
        a = k * 0.9
        x, y = math.cos(a) * 1.4 + jit(k, 0.3), math.sin(a) * 1.4 - 1.5
        b.cyl((x, y, WATER - 0.05), (x + math.cos(a + 1.5) * 0.45, y + math.sin(a + 1.5) * 0.45, WATER - 0.05), 0.09,
              "fish", r2=0.02, seg=5)
    save(b, name)


def signal_mast(name):
    b = B()
    b.cyl((0, 0, -0.3), (0, 0, 0.5), 1.3, "stone", r2=1.15, seg=8)
    b.cyl((0, 0, 0.5), (0, 0, 0.62), 1.25, "stone_dark", seg=8)
    high = 10.0
    b.cyl((0, 0, 0.5), (0, 0, high), 0.14, "timber", r2=0.08, seg=7)
    b.sphere((0, 0, high + 0.1), 0.14, "gold", seg=6, rings=4)
    b.cyl((-2.2, 0, 7.5), (2.2, 0, 7.5), 0.06, "wood", seg=6)
    b.cyl((0, 0, 6.2), (0, 0, 6.5), 0.3, "wood", r2=0.38, seg=8)
    for k in range(4):
        a = k * math.pi / 2 + math.pi / 4
        rope(b, [(0, 0, 6.2), (math.cos(a) * 1.05, math.sin(a) * 1.05, 0.6)], r=0.018)
        b.box((math.cos(a) * 1.05, math.sin(a) * 1.05, 0.68), (0.12, 0.12, 0.14), "iron")
    for s in (-1, 1):
        rope(b, [(s * 2.2, 0, 7.5), (0, 0, 9.4)], r=0.015)
        rope(b, [(s * 2.0, 0, 7.5), (s * 0.9, 0.3, 0.62)], r=0.012)
    # Three signal flags on the starboard halyard and a ball on the port one, each on a bone.
    f = b.bone("flags")
    x = 2.0
    for k, mat in enumerate(("cloth_red", "paint_yellow", "cloth_blue")):
        z = 6.9 - k * 0.75
        f.solid([(x, 0, z), (x, 0, z - 0.6), (x, 0.85, z - 0.6), (x, 0.85, z)],
                [(x + 0.03, 0, z), (x + 0.03, 0, z - 0.6), (x + 0.03, 0.85, z - 0.6), (x + 0.03, 0.85, z)], mat)
    ball = b.bone("ball")
    ball.sphere((-2.0, 0, 6.8), 0.3, "charcoal", seg=7, rings=5)
    ball.cyl((-2.0, 0, 6.4), (-2.0, 0, 7.2), 0.02, "rope", seg=4)
    b.box((0.5, -0.9, 0.9), (0.5, 0.4, 0.55), "wood")       # The chest of flags.
    b.box((0.5, -0.9, 1.2), (0.54, 0.44, 0.06), "iron")
    mech = kit.Mech([("flags", (2.0, 0, 6.9), (2.0, 0, 7.3), None), ("ball", (-2.0, 0, 6.8), (-2.0, 0, 7.2), None)])
    mech.clip("raise", 3.0, lambda t: ({}, {"flags": (0.0, 0.0, -4.5 * (1 - smoothstep(t))),
                                             "ball": (0.0, 0.0, -4.5 * smoothstep(t))}), loops=False)
    mech.clip("lower", 3.0, lambda t: ({}, {"flags": (0.0, 0.0, -4.5 * smoothstep(t)),
                                             "ball": (0.0, 0.0, -4.5 * (1 - smoothstep(t)))}), loops=False)
    mech.clip("wave", 2.0, lambda t: ({"flags": [(kit.Z, 14 * math.sin(2 * math.pi * t))]}, {}))
    save(b, name, mech=mech)


def fish_market(name):
    b = B()
    wood_deck(b, -4, 4, -2.5, 2.5)
    cloths = ("cloth_blue", "cloth_white", "cloth_red")
    for k in range(3):
        x = -2.7 + k * 2.7
        for dx in (-1.0, 1.0):
            for dy in (-0.6, 0.6):
                b.box((x + dx, 0.6 + dy, DZ + 1.1), (0.1, 0.1, 2.2), "timber")
        b.box((x, 0.2, DZ + 0.8), (2.0, 1.0, 0.1), "wood")
        b.box((x, 0.2, DZ + 0.4), (1.9, 0.06, 0.8), "wood_light")
        ring = [(x - 1.2, -0.35, DZ + 1.9), (x + 1.2, -0.35, DZ + 1.9), (x + 1.2, 1.35, DZ + 2.35),
                (x - 1.2, 1.35, DZ + 2.35)]
        b.solid(ring, [(px, py, pz + 0.05) for px, py, pz in ring], cloths[k])
        b.box((x, -0.36, DZ + 1.82), (2.4, 0.04, 0.2), cloths[(k + 1) % 3])
        # The catch laid out on the counter.
        b.box((x - 0.4, 0.2, DZ + 0.87), (0.9, 0.7, 0.05), "cloth_white" if k != 1 else "stone_light")
        for j in range(4):
            b.cyl((x - 0.75 + j * 0.22, 0.0, DZ + 0.94), (x - 0.7 + j * 0.22, 0.42, DZ + 0.94), 0.07, "fish", r2=0.015,
                  seg=5)
        b.cyl((x + 0.6, 0.2, DZ + 0.85), (x + 0.6, 0.2, DZ + 1.1), 0.2, "thatch_dark", r2=0.26, seg=8)
        for j in range(3):
            b.box((x + 0.6 + jit(j + k, 0.08), 0.2 + jit(j, 0.08, 2), DZ + 1.12), (0.08, 0.26, 0.05), "fish",
                  rz=j * 0.9)
        for j in range(3):
            fish(b, x - 0.7 + j * 0.7, 1.1, DZ + 2.1, s=0.34)
        b.cyl((x - 0.9, 1.1, DZ + 2.12), (x + 0.9, 1.1, DZ + 2.12), 0.025, "wood_light", seg=5)
    # Scales, barrels of salted fish, crates with ice and mooring posts.
    b.box((3.4, -1.6, DZ + 0.75), (0.08, 0.08, 1.5), "timber")
    b.box((3.4, -1.6, DZ + 1.5), (0.9, 0.05, 0.05), "iron")
    for s in (-1, 1):
        rope(b, [(3.4 + s * 0.42, -1.6, DZ + 1.5), (3.4 + s * 0.42, -1.6, DZ + 1.05)], r=0.01)
        b.cyl((3.4 + s * 0.42, -1.6, DZ + 1.0), (3.4 + s * 0.42, -1.6, DZ + 1.05), 0.2, "bell", r2=0.22, seg=8)
    barrel(b, -3.5, -1.8, z=DZ)
    barrel(b, -2.8, -1.9, z=DZ, mat="wood_dark")
    crate(b, 1.2, -1.8, z=DZ, s=0.6)
    b.box((1.2, -1.8, DZ + 0.62), (0.5, 0.5, 0.06), "cloth_white")
    crate(b, 2.0, -1.9, z=DZ, s=0.55, rz=0.2)
    for x in (-4.12, 4.12):
        mooring_post(b, x, -2.35)
    ladder(b, -1.5, -2.5, DZ + 0.4, -1.4)
    save(b, name)


# --- Boats ---------------------------------------------------------------------------


def junk(name, sails=("cloth_red", "roof_dark"), trim="paint_red"):
    root = B()
    b = root.bone("hull")
    bones = []
    h = Hull(11.0, 3.6, 0.9, 1.2, tm=0.5, bow_p=0.42, stern_w=0.7, stern_p=0.5, sheer_bow=0.7, sheer_stern=1.5,
             bow_rise=0.7, stern_rise=0.45, n=14, thick=0.1)
    h.build(b, strakes=(trim, "wood", "wood_dark"), inner="wood")
    dz = 0.85
    h.deck(b, dz, 0.05, 0.98, mat="plank", alt="plank_b", steps=20)
    # A high poop with a cabin, a rail and two red lanterns.
    ya, yb = h.y(0.74), h.y(1.0) + 0.1
    zc = h.top(0.95) + 0.1
    wc = h.w(0.85)
    b.box((0, (ya + yb) / 2, zc), (2 * wc, yb - ya, 0.12), "plank_b")
    b.box((0, ya + 0.06, (dz + zc) / 2), (2 * h.half_at(0.74, dz + 0.3) + 0.1, 0.12, zc - dz), "wood_light")
    b.box((0, ya - 0.01, dz + 0.6), (0.6, 0.06, 1.2), "door")
    for s in (-1, 1):
        b.cyl((s * 0.9, ya - 0.02, dz + 0.9), (s * 0.9, ya - 0.08, dz + 0.9), 0.25, "window", seg=8)
        b.box((s * (wc - 0.06), (ya + yb) / 2, zc + 0.75), (0.1, yb - ya, 0.1), trim)
        for k in range(4):
            b.box((s * (wc - 0.06), lerp(ya + 0.1, yb - 0.1, k / 3), zc + 0.4), (0.09, 0.09, 0.7), "timber")
        b.box((s * (wc - 0.06), yb - 0.1, zc + 1.3), (0.06, 0.06, 1.2), "timber")
        lantern(b, s * (wc - 0.06), yb - 0.35, zc + 1.8, glow="paint_red", frame="gold", s=0.26)
        b.box((s * (wc - 0.06), yb - 0.22, zc + 1.84), (0.05, 0.3, 0.05), "timber")
        b.beam((s * 0.8, ya - 0.9, dz), (s * 0.8, ya, zc), 0.45, 0.06, "wood")
        # An eye painted on each bow, to find the way.
        t = 0.1
        b.cyl((s * (h.w(t) + 0.02), h.y(t), h.top(t) - 0.4), (s * (h.w(t) + 0.07), h.y(t), h.top(t) - 0.4), 0.22,
              "cloth_white", seg=8)
        b.cyl((s * (h.w(t) + 0.06), h.y(t) - 0.03, h.top(t) - 0.4), (s * (h.w(t) + 0.1), h.y(t) - 0.03, h.top(t) - 0.4),
              0.1, "charcoal", seg=6)
    b.box((0, yb - 0.05, zc + 0.75), (2 * wc, 0.1, 0.1), trim)
    rudder(b, h, size=1.0)

    def batten_sail(prefix, y, base, height, wide, bands, rake=0.0):
        b.cyl((0, y, base), (0, y - rake, base + height), 0.13, "timber", r2=0.08, seg=7)
        b.sphere((0, y - rake, base + height + 0.08), 0.1, "gold", seg=6, rings=4)
        ys = y - rake * 0.7 - 0.2
        z_top, z_bot = base + height - 0.5, base + 1.1
        sail(b, bones, prefix, wide, ys, z_top, z_bot, sails, bulge=0.25, bands=bands, strips=4, top_scale=0.8)
        for j in range(bands + 1):
            v = j / bands
            z = lerp(z_top, z_bot, v)
            w = wide * lerp(0.8, 1.0, v) + 0.3
            bone = b.bone("%s%d" % (prefix, min(j, bands - 1)))
            bone.cyl((-w / 2, ys - 0.06 - 0.2 * math.sin(math.pi * v * 0.8), z),
                     (w / 2, ys - 0.06 - 0.2 * math.sin(math.pi * v * 0.8), z), 0.04, "wood_light", seg=5)
        rope(b, [(0, y - rake, base + height), (wide / 2, y + 2.0, h.top(0.6))], r=0.015)

    batten_sail("main", h.y(0.5), dz, 8.0, 4.6, 6)
    batten_sail("fore", h.y(0.2), dz, 5.6, 3.0, 4, rake=0.6)
    pennant(b, bones, h.y(0.5), dz + 8.2, mat=sails[0], size=1.2)
    crate(b, -1.0, h.y(0.36), z=dz, s=0.65)
    crate(b, 0.9, h.y(0.34), z=dz, s=0.6, rz=0.3)
    barrel(b, 1.0, h.y(0.62), z=dz)
    sack(b, -1.0, h.y(0.64), z=dz)
    sack(b, -0.6, h.y(0.67), z=dz)
    finish(root, name, bones, [("bob", 4.0, merge(floating(2.0, 1.0, 0.05), waving(3, 12)), None),
                               ("sail", 4.0, merge(floating(3.0, 1.2, 0.06), flutter("main", 6, amp=1.2),
                                                   flutter("fore", 4, amp=1.5), waving()), 2.5)])


def sloop(name, sails=("canvas", "canvas_shade"), strake="paint_blue"):
    """A small boat with fore-and-aft sails, like the one in the owner's reference picture."""
    root = B()
    b = root.bone("hull")
    bones = []
    h = Hull(8.0, 2.7, 0.7, 0.8, stern_w=0.5, sheer_bow=0.5, sheer_stern=0.2, n=12, thick=0.08)
    h.build(b, strakes=(strake, "wood", "wood_dark"))
    dz = 0.35
    h.deck(b, dz, 0.05, 0.99, mat="plank", alt="plank_b", steps=16)
    yc = h.y(0.66)
    b.box((0, yc, dz + 0.35), (1.5, 2.0, 0.7), "wood_light")
    b.box((0, yc, dz + 0.74), (1.7, 2.2, 0.08), "wood_dark")
    for s in (-1, 1):
        b.cyl((s * 0.76, yc, dz + 0.42), (s * 0.79, yc, dz + 0.42), 0.16, "window", seg=8)
    b.box((0, yc - 1.01, dz + 0.3), (0.5, 0.05, 0.56), "door")
    ym = h.y(0.36)
    top = dz + 8.0
    b.cyl((0, ym, dz), (0, ym, top), 0.1, "timber", r2=0.06, seg=7)
    bow = (0, h.y(0) - 1.5, h.top(0) + 0.35)
    b.beam((0, h.y(0.08), h.top(0.05)), bow, 0.09, 0.09, "timber")
    rope(b, [(0, ym, top - 0.3), bow], r=0.015)
    for s in (-1, 1):
        rope(b, [(0, ym, top - 1.0), (s * h.w(0.42), h.y(0.42), h.top(0.42))], r=0.015)
    rope(b, [(0, ym, top - 0.2), (0, h.y(1.0), h.top(1.0))], r=0.012)
    # Mainsail: strips from the mast to the leech, on a bone that swings with the boom.
    zb, zt = dz + 1.35, top - 0.5
    bones.append(("main", (0, ym, zb), (0, ym, zb + 0.3), "hull"))
    m = b.bone("main")
    m.cyl((0, ym + 0.1, zb - 0.05), (0, ym + 4.4, zb - 0.12), 0.05, "wood", seg=6)
    strips = 6
    for j in range(strips):
        v0, v1 = j / strips, (j + 1) / strips
        ring = []
        for v, u in ((v0, 0.0), (v0, 0.5), (v0, 1.0), (v1, 1.0), (v1, 0.5), (v1, 0.0)):
            chord = 4.2 * (1 - v) + 0.05
            ring.append((0.28 * math.sin(math.pi * u * 0.8) * (1 - v * 0.6), ym + 0.14 + chord * u, lerp(zb, zt, v)))
        m.solid(ring, [(x + 0.035, y, z) for x, y, z in ring], sails[j % len(sails)])
    # Jib: from the masthead down to the bowsprit, on its own bone.
    bones.append(("jib", bow, (bow[0], bow[1], bow[2] + 0.3), "hull"))
    jb = b.bone("jib")
    head = (0, ym - 0.25, top - 1.3)
    clew = (0.3, ym - 0.5, dz + 1.3)
    for j in range(3):
        v0, v1 = j / 3, (j + 1) / 3
        ring = [tuple(lerp(bow[k], head[k], v0) for k in range(3)),
                tuple(lerp(clew[k], head[k], v0) for k in range(3)),
                tuple(lerp(clew[k], head[k], v1) for k in range(3)),
                tuple(lerp(bow[k], head[k], v1) for k in range(3))]
        jb.solid(ring, [(x + 0.035, y, z) for x, y, z in ring], sails[(j + 1) % len(sails)])
    rudder(b, h, size=0.7)
    pennant(b, bones, ym, top + 0.05, mat="cloth_red", size=0.8)
    crate(b, -0.5, h.y(0.25), z=dz, s=0.5)
    barrel(b, 0.5, h.y(0.24), z=dz, h=0.6, r=0.24)
    swing = lambda t: ({"main": [(kit.Z, 5 * math.sin(4 * math.pi * t))],
                        "jib": [(kit.Z, 3 * math.sin(4 * math.pi * t + 1.0))]}, {})
    finish(root, name, bones, [("bob", 3.0, merge(floating(3.0, 1.5, 0.04), waving(2, 10)), None),
                               ("sail", 4.0, merge(floating(5.0, 1.5, 0.05), swing, waving()), 2.8)])


def ice_yacht(name, sail_mats=("canvas", "canvas_shade")):
    root = B()
    b = root.bone("hull")
    bones = []
    # A long plank, a cross plank with two runners and a steering runner aft. It stands on the ice at Z = 0.
    b.box((0, 0.3, 0.42), (0.5, 5.4, 0.1), "plank")
    b.box((0, -1.2, 0.36), (3.4, 0.4, 0.1), "plank_b")
    for s in (-1, 1):
        b.beam((s * 1.6, -1.2, 0.33), (0, 0.6, 0.38), 0.08, 0.08, "timber")
        b.box((s * 1.6, -1.2, 0.2), (0.1, 0.5, 0.3), "timber")
        b.box((s * 1.6, -1.2, 0.045), (0.04, 1.3, 0.09), "iron")
        b.box((s * 1.6, -1.95, 0.08), (0.04, 0.25, 0.09), "iron", rz=0.0)
    bones.append(("skate", (0, 2.7, 0.3), (0, 2.7, 0.6), "hull"))
    sk = b.bone("skate")
    sk.box((0, 2.7, 0.2), (0.1, 0.4, 0.3), "timber")
    sk.box((0, 2.7, 0.045), (0.04, 0.9, 0.09), "iron")
    sk.beam((0, 2.7, 0.5), (0, 1.9, 0.85), 0.05, 0.05, "wood")
    for s in (-1, 1):   # A small box of a cockpit with a bench and cargo.
        b.box((s * 0.45, 1.7, 0.62), (0.06, 1.6, 0.34), "wood")
    b.box((0, 2.5, 0.62), (0.96, 0.06, 0.34), "wood")
    b.box((0, 0.9, 0.62), (0.96, 0.06, 0.34), "wood")
    b.box((0, 2.2, 0.62), (0.84, 0.3, 0.06), "wood_light")
    sack(b, -0.15, 1.35, z=0.47, r=0.22)
    crate(b, 0.2, 1.3, z=0.47, s=0.4)
    ym = -1.0
    b.cyl((0, ym, 0.4), (0, ym, 5.6), 0.09, "timber", r2=0.05, seg=7)
    b.cyl((-1.6, ym + 0.2, 1.25), (1.6, ym + 0.2, 1.25), 0.05, "wood", seg=6)
    sail(b, bones, "sail", 3.0, ym + 0.2, 5.2, 1.3, sail_mats, bulge=0.35, bands=3, strips=6, top_scale=0.08)
    for s in (-1, 1):
        rope(b, [(0, ym, 5.4), (s * 1.6, -1.2, 0.42)], r=0.015)
    rope(b, [(0, ym, 5.4), (0, 2.9, 0.48)], r=0.015)
    rope(b, [(0, ym, 5.4), (0, -2.3, 0.47)], r=0.015)
    pennant(b, bones, ym, 5.6, mat="cloth_red", size=0.7)
    steer = lambda t: ({"skate": [(kit.Z, 8 * math.sin(2 * math.pi * t))]}, {})
    finish(root, name, bones, [("sail", 3.0, merge(flutter("sail", amp=2.0), waving(3, 14), steer), 6.0)])


model("bridge_truss", truss)
model("bridge_truss_tarred", truss, pal=TARRED)
model("bridge_log_cart", log_cart)
model("bridge_causeway", causeway)
model("bridge_causeway_brick", causeway, pal=BRICK)
model("bridge_ice_crossing", ice_crossing)
model("bridge_fortified_brick", stone_bridge, arches=2, span=6.0, pier_w=2.0, abut=2.5, hump=1.3, pal=BRICK,
      extra=gate_tower)
model("dock_sluice_brick", sluice, pal=BRICK)
model("dock_harbor_chain_brick", harbor_chain, pal=BRICK)
model("dock_boat_ramp", boat_ramp)
model("dock_mussel_farm", mussel_farm)
model("dock_fish_pen", fish_pen)
model("dock_signal_mast", signal_mast)
model("dock_fish_market", fish_market)
model("boat_junk", junk)
model("boat_junk_gold", junk, sails=("paint_yellow", "thatch_dark"), trim="paint_green")
model("boat_ice_yacht", ice_yacht)
model("boat_sloop", sloop)
model("boat_sloop_red", sloop, sails=("cloth_red", "roof_dark"), strake="wood_dark")


# --- Small works ---------------------------------------------------------------------


def plank_ditch(name, length=4.0, width=1.0):
    """Two planks over a brook or an irrigation ditch."""
    b = B()
    for s in (-1, 1):
        b.box((0, s * (width / 4 + 0.01), 0.1), (length, width / 2 - 0.03, 0.07), "plank" if s > 0 else "plank_b",
              rz=0.01 * s)
    for x in (-length / 2 + 0.3, 0.0, length / 2 - 0.3):
        b.box((x, 0, 0.045), (0.14, width + 0.06, 0.05), "timber")
    for e in (-1, 1):
        rock(b, e * (length / 2 - 0.2), 0, 0.55, -0.4, 0.06, seed=e + 2, mat="stone", shrink=0.85, squash=1.3)
        b.cyl((e * (length / 2 - 0.5), width / 2 + 0.1, -0.4), (e * (length / 2 - 0.5), width / 2 + 0.1, 1.0), 0.04,
              "timber", seg=5)
    yr = width / 2 + 0.1
    rope(b, sag((-length / 2 + 0.5, yr, 0.95), (length / 2 - 0.5, yr, 0.95), 0.12, 6), r=0.018)
    save(b, name)


def reed_blind(name):
    """A hunter's blind for waterfowl, on a small stage among the reeds."""
    b = B()
    wood_deck(b, -1.5, 1.5, -1.5, 1.5, brace=False)
    wood_deck(b, -0.5, 0.5, 1.5, 3.5, brace=False)
    for x in (-1.3, 1.3):
        for y in (-1.3, 1.0):
            b.cyl((x, y, DZ), (x, y, DZ + 1.7), 0.05, "timber", seg=5)
    # Walls and roof of bundled reeds, open toward the water (-Y) through a slit.
    for k in range(9):
        x = -1.3 + k * 0.325
        for y, lo, hi in ((1.0, 0.0, 1.7), (-1.3, 0.0, 0.85), (-1.3, 1.3, 1.7)):
            b.cyl((x, y, DZ + lo), (x + jit(k, 0.03), y, DZ + hi), 0.15, "hay" if k % 2 else "thatch", seg=5)
    for k in range(8):
        y = -1.3 + k * 0.33
        for x in (-1.3, 1.3):
            b.cyl((x, y, DZ), (x, y + jit(k, 0.03), DZ + 1.7), 0.15, "thatch_dark" if k % 2 else "hay", seg=5)
    for k in range(9):
        x = -1.45 + k * 0.36
        b.cyl((x, -1.5, DZ + 1.65), (x, 1.2, DZ + 2.05), 0.16, "thatch" if k % 2 else "thatch_dark", seg=5)
    # Reeds around, wooden decoys on the water, a bow and the day's ducks.
    for k in range(26):
        a = k * 0.9
        r = 2.2 + jit(k, 0.5)
        x, y = math.cos(a) * r, math.sin(a) * r * 0.9 - 0.3
        b.cyl((x, y, WATER - 0.5), (x + jit(k, 0.15, 2), y, 0.9 + jit(k, 0.4, 3)), 0.03, "leaves", r2=0.01, seg=4)
        if k % 3 == 0:
            b.cyl((x + jit(k, 0.15, 2), y, 0.8 + jit(k, 0.4, 3)), (x + jit(k, 0.15, 2), y, 1.05 + jit(k, 0.4, 3)), 0.04,
                  "timber", seg=4)
    for k, (x, y) in enumerate(((-0.6, -3.2), (0.5, -3.6), (1.4, -2.9))):
        b.sphere((x, y, WATER + 0.06), 0.16, "wood" if k % 2 else "paint_green", seg=6, rings=4, scale=(0.8, 1.4, 0.7))
        b.sphere((x, y - 0.18, WATER + 0.2), 0.08, "paint_green", seg=5, rings=3)
        b.cyl((x, y - 0.24, WATER + 0.2), (x, y - 0.34, WATER + 0.19), 0.03, "paint_yellow", r2=0.01, seg=4)
    b.cyl((0.9, 0.7, DZ), (1.1, 0.9, DZ + 1.5), 0.02, "wood_light", seg=4)
    for k in range(3):
        fish(b, -0.9 + k * 0.25, 0.92, DZ + 1.3, s=0.3, mat="hide")
    save(b, name)


def ice_house(name):
    """A half-buried cellar for ice cut from the river in winter."""
    b = B()
    w, d = 4.0, 5.0
    b.box((0, 0.3, 0.5), (w, d - 0.6, 1.0), "stone")
    for k in range(5):   # A turf mound over the vault.
        t = k / 5
        b.box((0, 0.3, 1.0 + 0.22 * k), (w * (1 - 0.18 * k) + 0.3, (d - 0.6) * (1 - 0.1 * k) + 0.3, 0.24),
              "leaves" if k % 2 else "moss")
    blocks(b, -1.8, 1.8, -2.2, 0.2, 0.9, STONE, face=-1, count=5, seed=4)
    # The entrance toward -Y: a stone porch with a thick door, a few steps down.
    b.box((0, -2.3, 0.75), (1.8, 0.5, 1.5), "stone_dark")
    b.box((0, -2.57, 0.65), (0.9, 0.08, 1.3), "door")
    for z in (0.3, 1.0):
        b.box((0, -2.62, z), (0.86, 0.04, 0.07), "iron")
    b.xz([(-1.0, 1.5), (1.0, 1.5), (0, 2.0)], -2.6, -2.0, "stone")
    # A sledge loaded with blocks of ice, a stack of blocks under straw and an ice saw.
    for y in (-0.35, 0.35):
        b.box((2.9, -1.5 + y, 0.06), (1.6, 0.08, 0.12), "wood")
    b.box((2.9, -1.5, 0.16), (1.3, 0.9, 0.06), "plank")
    for k in range(4):
        b.box((2.6 + (k % 2) * 0.6, -1.5, 0.37 + (k // 2) * 0.37), (0.55, 0.7, 0.35),
              "crystal_glow" if k % 2 else "marble_shade")
    rope(b, [(3.7, -1.5, 0.12), (4.4, -1.5, 0.5)], r=0.02)
    for k in range(6):
        b.box((-2.9 + (k % 3) * 0.6, -1.6 - (k // 3) * 0.7, 0.18), (0.55, 0.65, 0.35),
              "marble_shade" if k % 2 else "crystal_glow")
    b.box((-2.3, -1.95, 0.4), (1.9, 1.5, 0.08), "hay")
    b.beam((-3.6, -0.6, 0.0), (-3.3, -0.2, 1.5), 0.03, 0.14, "iron")
    b.box((-3.28, -0.18, 1.55), (0.3, 0.06, 0.06), "wood")
    save(b, name)


def watering_place(name):
    """A paved ramp into the water for livestock, with a trough and a hitching rail."""
    b = B()

    def zf(y):
        return lerp(0.02, -0.75, (3.0 - y) / 6.0)

    n = 8
    k = 0
    for iy in range(n):
        for ix in range(5):
            k += 1
            x = -2.0 + ix * 1.0 + jit(k, 0.06)
            y = 2.6 - iy * 0.75
            rock(b, x, y, 0.56, -1.2, zf(y) + jit(k, 0.03, 2), seed=k, mat=("stone", "stone_dark", "road")[k % 3],
                 sides=6, shrink=0.9)
    for s in (-1, 1):   # Curbs of stakes and a rail, so the animals keep to the ramp.
        for i in range(5):
            y = 2.8 - i * 1.4
            b.cyl((s * 2.7, y, -1.2), (s * 2.7, y, zf(y) + 1.0), 0.07, "timber", seg=6)
        b.beam((s * 2.7, 2.8, zf(2.8) + 0.9), (s * 2.7, -2.8, zf(-2.8) + 0.9), 0.07, 0.07, "wood")
        b.beam((s * 2.7, 2.8, zf(2.8) + 0.5), (s * 2.7, -2.8, zf(-2.8) + 0.5), 0.05, 0.05, "wood")
    # A hollowed-log trough on the shore, fed by a wooden gutter, and a hitching rail.
    log(b, (-1.6, 3.9, 0.3), (1.6, 3.9, 0.3), 0.32, seg=8)
    b.box((0, 3.9, 0.5), (2.9, 0.4, 0.2), "water")
    for x in (-1.3, 1.3):
        b.box((x, 3.9, 0.05), (0.2, 0.7, 0.14), "timber")
    b.beam((2.9, 3.2, 0.4), (1.5, 3.85, 0.62), 0.16, 0.08, "wood")
    for x in (-3.6, -2.2):
        b.box((x, 4.4, 0.55), (0.12, 0.12, 1.1), "timber")
    b.cyl((-3.8, 4.4, 1.0), (-2.0, 4.4, 1.0), 0.05, "wood_light", seg=6)
    b.cyl((3.3, 4.3, 0.0), (3.3, 4.3, 0.5), 0.3, "hay", seg=7)
    b.cyl((3.3, 4.3, 0.2), (3.3, 4.3, 0.26), 0.31, "rope", seg=7)
    save(b, name)


model("bridge_plank_ditch", plank_ditch)
model("dock_reed_blind", reed_blind)
model("dock_ice_house", ice_house)
model("dock_watering_place", watering_place)
