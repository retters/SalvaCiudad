"""A third batch of the `bridges` family: an aqueduct, a bridge under
construction, a sluice, a harbor chain, a port warehouse, salt pans, a house
on stilts, a buoy and three more small boats."""

import math

import bmesh

from parts import (B, BRICK, ROOFS, STONE, arch, barrel, blocks, chain, crate, jit, lantern, log, parapet, planks_x,
                   rail, roof_y, rope, sack, sag, save, smoothstep)
from bridges import stone_bridge
from boats import Hull, finish, floating, merge
from docks import DZ, WATER, ladder, mooring_post, wood_deck
import _kit as kit
import buildings

MODELS = {}


def model(name, fn, **kw):
    MODELS[name] = lambda: fn(name, **kw)


# --- Aqueduct ------------------------------------------------------------------------


def aqueduct(name, pal=STONE, arches=5, span=3.2, pier_w=0.8, width=1.6, height=6.0):
    b = B()
    length = arches * span + (arches + 1) * pier_w
    x0 = -length / 2
    y0, y1 = -width / 2, width / 2
    ring = 0.22
    zs = height - 2.6

    def top(x):
        return height - 0.5

    for i in range(arches + 1):
        xp = x0 + pier_w / 2 + i * (span + pier_w)
        b.box((xp, 0, (zs - 3.0) / 2), (pier_w + 2 * ring, width + 0.1, zs + 3.0), pal["body"])
        b.box((xp, 0, zs - 0.1), (pier_w + 2 * ring + 0.14, width + 0.24, 0.2), pal["trim"])
        b.box((xp, 0, 0.3), (pier_w + 2 * ring + 0.3, width + 0.4, 0.6), pal["trim"])
        b.xz([(xp - pier_w / 2, zs), (xp + pier_w / 2, zs), (xp + pier_w / 2, top(0)), (xp - pier_w / 2, top(0))],
             y0, y1, pal["body"])
        blocks(b, xp - 0.4, xp + 0.4, y0 - 0.05, 0.8, zs - 0.5, pal, face=-1, count=3, seed=i)
        blocks(b, xp - 0.4, xp + 0.4, y1 + 0.05, 0.8, zs - 0.5, pal, face=1, count=3, seed=i + 9)
        if i < arches:
            xc = xp + pier_w / 2 + span / 2
            arch(b, xc, span / 2 - ring, span / 2 - ring, zs, top, y0, y1, pal, n=7, ring=ring)
    # The channel on top, with water running in it.
    b.box((0, 0, height - 0.45), (length + 0.2, width + 0.2, 0.12), pal["trim"])
    for s in (-1, 1):
        b.box((0, s * (width / 2 - 0.12), height - 0.2), (length + 0.2, 0.24, 0.4), pal["body"])
        b.box((0, s * (width / 2 - 0.12), height + 0.03), (length + 0.2, 0.3, 0.07), pal["cap"])
    b.box((0, 0, height - 0.2), (length + 0.2, width - 0.48, 0.3), "water")
    save(b, name)


# --- A stone bridge being built ------------------------------------------------------


def bridge_site(name, pal=STONE, span=7.0, width=4.0, abut=2.5, hump=1.7, zs=-0.6, deep=-3.0, ring=0.28):
    b = B()
    length = span + 2 * abut
    x0, x1 = -length / 2, length / 2
    y0, y1 = -width / 2, width / 2
    n = 9

    def top(x):
        x = max(x0, min(x1, x))
        return hump * 0.5 * (1 + math.cos(2 * math.pi * x / length))

    half = span / 2 - ring
    rise = min(top(-half * 0.4) - 0.2 - ring - zs, half * 1.1)
    arch(b, 0, half, rise, zs, top, y0, y1, pal, n=n, ring=ring, keep=(0, 1, 2, 3, 7, 8))
    for s, xa in ((-1, x0), (1, x1 - abut)):
        xb = xa + abut
        for k in range(5):
            xk, xl = xa + abut * k / 5, xa + abut * (k + 1) / 5
            b.xz([(xk, zs), (xl, zs), (xl, top(xl)), (xk, top(xk))], y0, y1, pal["body"])
        lo, hi = (xa, xb + ring) if s < 0 else (xa - ring, xb)
        b.box(((lo + hi) / 2, 0, (deep + zs) / 2), (hi - lo, width + 0.2, zs - deep), pal["body"])
        b.box(((lo + hi) / 2, 0, zs - 0.12), (hi - lo + 0.1, width + 0.34, 0.24), pal["trim"])
    parapet(b, x0, x0 + 2.0, y1 - 0.15, top, pal)
    # The centering: wooden ribs with boards on top that carry the stones until the arch closes.
    def pt(i, r_off):
        a = math.pi * i / n
        return (-(half - r_off) * math.cos(a), zs + (rise - r_off) * math.sin(a))

    for y in (y0 + 0.3, 0.0, y1 - 0.3):
        for i in range(n):
            (xa, za), (xb, zb) = pt(i, 0.16), pt(i + 1, 0.16)
            b.beam((xa, y, za), (xb, y, zb), 0.12, 0.16, "timber")
        b.box((0, y, zs - 0.1), (2 * half, 0.14, 0.16), "timber")
        b.box((0, y, zs + (rise - 0.2) / 2 - 0.05), (0.14, 0.14, rise - 0.3), "timber")
        for s in (-1, 1):
            b.beam((0, y, zs), (s * half * 0.62, y, zs + rise * 0.72), 0.1, 0.1, "wood")
            b.cyl((s * (half - 0.3), y, deep), (s * (half - 0.3), y, zs - 0.18), 0.1, "wood", seg=6)
            b.cyl((s * 0.9, y, deep), (s * 0.9, y, zs - 0.18), 0.1, "wood", seg=6)
    for i in range(n):
        (xa, za), (xb, zb) = pt(i, 0.04), pt(i + 1, 0.04)
        b.beam((xa, 0, za), (xb, 0, zb), width + 0.3, 0.05, "plank" if i % 2 else "plank_b")
    # A work platform, a ramp of boards, cut stones waiting and a hoist.
    planks_x(b, -1.2, 1.2, 1.2, z=zs + rise + 0.35, yc=y0 - 0.75)
    for x in (-1.1, 1.1):
        b.cyl((x, y0 - 1.25, deep), (x, y0 - 1.25, zs + rise + 1.3), 0.08, "timber", seg=6)
        b.box((x, y0 - 0.75, zs + rise + 0.25), (0.1, 1.1, 0.1), "timber")
    b.box((0, y0 - 1.25, zs + rise + 1.25), (2.3, 0.07, 0.07), "wood")
    for k in range(5):
        b.box((x1 - 1.6 + (k % 3) * 0.55, -0.9 + (k // 3) * 0.7, top(x1 - 1.3) + 0.2 + 0.0), (0.5, 0.6, 0.35),
              pal["cap"] if k % 2 else pal["ring"][1], rz=jit(k, 0.2))
    hx = x0 + 2.0
    b.box((hx, 0.8, top(hx) + 1.6), (0.18, 0.18, 3.2), "timber")
    b.beam((hx, 0.8, top(hx) + 3.1), (hx + 2.4, 0.4, top(hx) + 3.6), 0.14, 0.14, "timber")
    b.beam((hx, 0.8, top(hx) + 1.6), (hx + 1.3, 0.6, top(hx) + 3.35), 0.1, 0.1, "wood")
    rope(b, [(hx + 2.4, 0.4, top(hx) + 3.55), (hx + 2.4, 0.4, top(hx) + 1.9)], r=0.025)
    b.box((hx + 2.4, 0.4, top(hx) + 1.65), (0.6, 0.5, 0.4), pal["cap"])
    save(b, name)


def shrine(b, top, length, width, pal):
    y = width / 2 - 0.15
    z = top(0.0)
    b.box((0, y, z + 0.9), (0.7, 0.5, 2.0), pal["body"])
    b.box((0, y - 0.2, z + 1.35), (0.44, 0.14, 0.7), "window")
    b.xz([(-0.5, z + 1.9), (0.5, z + 1.9), (0, z + 2.45)], y - 0.33, y + 0.33, "slate")
    b.cyl((0, y - 0.25, z + 1.05), (0, y - 0.25, z + 1.45), 0.08, "gold", r2=0.05, seg=6)
    b.sphere((0, y - 0.25, z + 1.53), 0.09, "gold", seg=6, rings=4)
    b.box((0, y - 0.32, z + 0.98), (0.6, 0.2, 0.06), pal["cap"])
    for e in (-1, 1):
        b.box((e * 0.2, y - 0.34, z + 1.07), (0.06, 0.06, 0.12), "lantern")
        b.sphere((e * 0.5, y - 0.3, z + 1.0 + 0.06), 0.1, "flowers" if e > 0 else "flowers_y", seg=5, rings=3)
    b.cyl((0, y, z + 2.45), (0, y, z + 2.75), 0.025, "iron", seg=4)
    b.sphere((0, y, z + 2.8), 0.08, "gold", seg=6, rings=4)
    return None


# --- Sluice, harbor chain, warehouse, salt pans, stilt house, buoy --------------------


def sluice(name, pal=STONE):
    b = B()
    for s in (-1, 1):   # Two masonry walls and a low weir between them.
        b.box((s * 3.0, 0, -1.3), (2.0, 2.4, 3.4), pal["body"])
        b.box((s * 3.0, 0, 0.45), (2.1, 2.5, 0.16), pal["cap"])
        blocks(b, s * 3.0 - 0.8, s * 3.0 + 0.8, -1.2, -2.4, 0.2, pal, face=-1, count=4, seed=s)
        blocks(b, s * 3.0 - 0.8, s * 3.0 + 0.8, 1.2, -2.4, 0.2, pal, face=1, count=4, seed=s + 3)
    b.box((0, 0, -2.2), (4.0, 2.0, 1.6), pal["trim"])
    # Gate frame with a windlass, and a footbridge over the top.
    for s in (-1, 1):
        b.box((s * 1.85, 0, 1.3), (0.26, 0.3, 3.6), "timber")
    b.box((0, 0, 3.0), (4.1, 0.34, 0.26), "timber")
    b.cyl((-1.6, 0, 2.5), (1.6, 0, 2.5), 0.14, "wood_light", seg=8)
    for s in (-1, 1):
        for k in range(4):
            a = k * math.pi / 2
            b.cyl((s * 2.05, 0, 2.5), (s * 2.05, math.cos(a) * 0.5, 2.5 + math.sin(a) * 0.5), 0.03, "wood", seg=5)
    planks_x(b, -4.0, 4.0, 1.0, z=0.6, yc=0.75)
    for s in (-1, 1):
        b.box((0, 0.75 + s * 0.4, 0.45), (8.0, 0.12, 0.14), "timber")
    rail(b, [(x, 1.2, 0.6) for x in (-3.9, -2.0, 0.0, 2.0, 3.9)], h=0.9)
    g = b.bone("gate")
    for k in range(6):
        g.box((0, 0, -1.3 + k * 0.32 + 0.16), (3.4, 0.1, 0.3), "wood" if k % 2 else "wood_light")
    for x in (-1.2, 0.0, 1.2):
        g.box((x, -0.07, -0.35), (0.12, 0.05, 1.95), "iron")
    for x in (-1.0, 1.0):
        chain(g, (x, 0, 0.6), (x, 0, 2.4), link=0.2)
    mech = kit.Mech([("gate", (0, 0, -1.3), (0, 0, -0.8), None)])
    mech.clip("open", 3.0, lambda t: ({}, {"gate": (0.0, 0.0, 1.5 * smoothstep(t))}), loops=False)
    mech.clip("close", 3.0, lambda t: ({}, {"gate": (0.0, 0.0, 1.5 * (1 - smoothstep(t)))}), loops=False)
    save(b, name, mech=mech)


def harbor_chain(name, pal=STONE, gap=12.0):
    b = B()
    for s in (-1, 1):
        x = s * (gap / 2 + 1.6)
        b.cyl((x, 0, -3.0), (x, 0, 0.0), 1.9, pal["trim"], r2=1.75, seg=10)
        b.cyl((x, 0, 0.0), (x, 0, 4.6), 1.7, pal["body"], r2=1.5, seg=10)
        b.cyl((x, 0, 4.6), (x, 0, 4.85), 1.75, pal["trim"], seg=10)
        for k in range(10):
            if k % 2:
                continue
            a = 2 * math.pi * (k + 0.5) / 10
            b.box((x + math.cos(a) * 1.55, math.sin(a) * 1.55, 5.15), (0.6, 0.4, 0.6), pal["body"], rz=a + math.pi / 2)
        b.box((x, 1.62, 0.9), (0.9, 0.2, 1.8), pal["trim"])
        b.box((x, 1.72, 0.85), (0.7, 0.08, 1.6), "door")
        b.box((x - s * 1.55, 0, 0.6), (0.3, 0.7, 0.7), "charcoal")     # The port the chain comes out of.
        for k in range(3):
            a = k * 2.0 + 1.0
            b.box((x + math.cos(a) * 1.58, math.sin(a) * 1.58, 3.0), (0.14, 0.3, 0.8), "window", rz=a + math.pi / 2)
        b.cyl((x, 0, 4.85), (x, 0, 7.0), 0.04, "timber", seg=5)
        flag = [(0, 6.5), (0, 6.95), (0.8, 6.7)]
        b.solid([(x, fy, fz) for fy, fz in flag], [(x + 0.03, fy, fz) for fy, fz in flag], "cloth_red")
    c = b.bone("chain")
    pts = sag((-gap / 2 - 0.1, 0, 0.6), (gap / 2 + 0.1, 0, 0.6), 0.75, 12)
    for p, q in zip(pts, pts[1:]):
        chain(c, p, q, link=0.42)
    for k in (3, 6, 9):   # Floats keep the chain at the surface.
        p = pts[k]
        log(c, (p[0], -0.9, p[2] - 0.1), (p[0], 0.9, p[2] - 0.1), 0.24, seg=7)
    mech = kit.Mech([("chain", (0, 0, 0.6), (0, 0, 1.1), None)])
    mech.clip("lower", 3.0, lambda t: ({}, {"chain": (0.0, 0.0, -1.8 * smoothstep(t))}), loops=False)
    mech.clip("raise", 3.0, lambda t: ({}, {"chain": (0.0, 0.0, -1.8 * (1 - smoothstep(t)))}), loops=False)
    save(b, name, mech=mech)


def warehouse(name, roof="shingle"):
    b = B()
    w, d = 6.0, 6.0
    wood_deck(b, -3, 3, -5, 3, brace=False)
    cy = 0.0
    wall_h = DZ + 3.4
    b.box((0, cy, DZ + 1.7), (w, d, 3.4), "wood")
    for k in range(12):
        z = DZ + 0.15 + k * 0.28
        for s in (-1, 1):
            b.box((s * (w / 2 + 0.01), cy, z), (0.05, d - 0.2, 0.25), "wood" if k % 2 else "wood_light")
        b.box((0, cy + d / 2 + 0.01, z), (w - 0.2, 0.05, 0.25), "wood" if k % 2 else "wood_light")
    for x in (-w / 2, 0, w / 2):
        for y in (-d / 2, d / 2):
            b.box((x, cy + y, DZ + 1.7), (0.2, 0.2, 3.4), "timber")
    for y in (-d / 2, d / 2):
        b.box((0, cy + y, wall_h - 0.1), (w, 0.2, 0.2), "timber")
        b.box((0, cy + y, DZ + 1.9), (w, 0.14, 0.14), "timber")
    # Big doors toward the water and a loft door under the hoist beam.
    for s in (-1, 1):
        b.box((s * 0.72, cy - d / 2 - 0.05, DZ + 1.05), (1.4, 0.08, 2.1), "door")
        b.box((s * 0.72, cy - d / 2 - 0.1, DZ + 1.5), (1.3, 0.04, 0.08), "iron")
        b.box((s * 0.72, cy - d / 2 - 0.1, DZ + 0.5), (1.3, 0.04, 0.08), "iron")
    b.box((0, cy - d / 2 - 0.04, DZ + 2.2), (3.1, 0.1, 0.16), "timber")
    ridge = roof_y(b, 0, cy, w, d, wall_h, 2.2, 0.4, list(ROOFS[roof]), rows=6, gables=(-1, 1))
    b.box((0, cy - d / 2 - 0.07, wall_h + 0.75), (0.9, 0.06, 1.1), "door")
    b.box((0, cy - d / 2 - 1.0, ridge - 0.45), (0.2, 2.6, 0.22), "timber")
    b.cyl((-0.16, cy - d / 2 - 2.1, ridge - 0.65), (0.16, cy - d / 2 - 2.1, ridge - 0.65), 0.16, "wood_light", seg=8)
    load = b.bone("load")
    lx, ly, lz = 0.0, cy - d / 2 - 2.1, ridge - 0.8
    rope(load, [(lx, ly, lz), (lx, ly, lz - 2.6)], r=0.025)
    load.box((lx, ly, lz - 2.68), (0.1, 0.1, 0.16), "iron")
    for s in (-1, 1):
        for e in (-1, 1):
            rope(load, [(lx, ly, lz - 2.7), (lx + s * 0.35, ly + e * 0.35, lz - 3.1)], r=0.018)
    load.box((lx, ly, lz - 3.45), (0.75, 0.75, 0.7), "wood_light")
    load.box((lx, ly, lz - 3.45), (0.8, 0.12, 0.76), "wood")
    # Goods on the apron, mooring posts and a lantern.
    crate(b, -2.2, -3.6, z=DZ, s=0.7)
    crate(b, -2.25, -4.35, z=DZ, s=0.6, rz=0.2)
    crate(b, -2.2, -3.7, z=DZ + 0.7, s=0.55, rz=0.4)
    barrel(b, 2.3, -3.5, z=DZ)
    barrel(b, 2.35, -4.2, z=DZ)
    barrel(b, 1.7, -3.9, z=DZ, mat="wood_dark")
    sack(b, 1.2, -3.3, z=DZ)
    for x in (-3.12, 3.12):
        mooring_post(b, x, -4.85)
    lantern(b, -1.9, cy - d / 2 - 0.3, DZ + 2.9)
    b.box((-1.9, cy - d / 2 - 0.15, DZ + 2.93), (0.06, 0.4, 0.06), "iron")
    mech = kit.Mech([("load", (lx, ly, lz), (lx, ly, lz + 0.4), None)])
    mech.clip("lift", 5.0, lambda t: ({}, {"load": (0.0, 0.0, 2.2 * (0.5 - 0.5 * math.cos(2 * math.pi * t)))}))
    save(b, name, mech=mech)


def saltworks(name):
    b = B()
    # Six shallow pans between low clay banks, at different stages of drying.
    stages = ("water", "water", "stone_light", "water", "cloth_white", "cloth_white")
    k = 0
    for ix in range(3):
        for iy in range(2):
            x, y = -2.7 + ix * 2.7, -2.4 + iy * 2.6
            b.box((x, y, 0.06), (2.6, 2.5, 0.2), "clay")
            b.box((x, y, 0.13), (2.2, 2.1, 0.1), stages[k])
            if stages[k] == "cloth_white":
                for j in range(3):
                    px, py_ = x - 0.6 + j * 0.6, y + jit(j + k, 0.5)
                    b.cyl((px, py_, 0.15), (px, py_, 0.55), 0.32, "cloth_white", r2=0.02, seg=7)
            k += 1
    b.box((0, -3.95, -0.1), (8.2, 0.5, 0.5), "clay")
    for x in (-1.35, 1.35):   # Little sluice boards between the sea and the pans.
        b.box((x, -3.95, 0.25), (0.5, 0.08, 0.45), "wood")
    # A shadoof lifts the brine: a pole with a counterweight on a forked post.
    px, py = 3.6, -4.3
    b.cyl((px, py, -0.4), (px, py, 2.4), 0.09, "timber", seg=6)
    for s in (-1, 1):
        b.cyl((px, py, 2.3), (px + s * 0.18, py, 2.75), 0.05, "timber", seg=5)
    arm = b.bone("arm")
    arm.cyl((px, py + 1.3, 2.2), (px, py - 2.2, 2.9), 0.05, "wood_light", seg=6)
    arm.box((px, py + 1.25, 2.15), (0.4, 0.4, 0.4), "stone_dark")
    bucket = b.bone("bucket")
    rope(bucket, [(px, py - 2.2, 2.9), (px, py - 2.2, 0.9)], r=0.018)
    bucket.cyl((px, py - 2.2, 0.55), (px, py - 2.2, 0.9), 0.16, "wood", r2=0.2, seg=7)
    # A shed for the dry salt, with sacks, rakes and a barrow.
    for x in (-3.9, -1.9):
        for y in (1.9, 3.6):
            b.box((x, y, 1.0), (0.12, 0.12, 2.0), "timber")
    roof_y(b, -2.9, 2.75, 2.1, 1.8, 2.0, 0.8, 0.3, ["thatch", "thatch_dark"], rows=3)
    for j in range(5):
        sack(b, -3.5 + (j % 3) * 0.55, 2.4 + (j // 3) * 0.6, z=0.0)
    sack(b, -3.2, 2.7, z=0.38)
    b.box((-2.9, 2.75, 0.03), (2.2, 1.9, 0.06), "plank_b")
    for j in range(2):
        b.cyl((0.6 + j * 0.5, 3.2, 0.0), (0.2 + j * 0.5, 2.0, 1.5), 0.025, "wood_light", seg=4)
        b.box((0.6 + j * 0.5, 3.24, 0.03), (0.5, 0.06, 0.06), "wood")
    barrel(b, 2.6, 2.6)
    barrel(b, 3.3, 2.9, mat="wood_dark")
    ay, az = py, 2.5
    ry, rz = -2.2, 0.4

    def dip(t):
        up = 0.5 - 0.5 * math.cos(2 * math.pi * t)
        a = math.radians(24 * up)
        ny = ry * math.cos(a) - rz * math.sin(a)
        nz = ry * math.sin(a) + rz * math.cos(a)
        return {"arm": [(kit.X, 24 * up)]}, {"bucket": (0.0, ny - ry, nz - rz)}

    mech = kit.Mech([("arm", (px, ay, az), (px, ay, az + 0.4), None),
                     ("bucket", (px, py - 2.2, 2.9), (px, py - 2.2, 3.3), None)])
    mech.clip("dip", 4.0, dip)
    save(b, name, mech=mech)


def stilt_house(name, roof=("thatch", "thatch_dark"), walls="plaster"):
    b = B()
    z = 0.9
    wood_deck(b, -3, 3, -3, 2.5, z=z, brace=True)
    # Gangway from the shore (+Y) up to the platform.
    n = 8
    for i in range(n):
        ya, yb = 5.5 - 3.0 * i / n, 5.5 - 3.0 * (i + 1) / n
        b.beam((0, ya, 0.05 + (z - 0.05) * i / n - 0.03), (0, yb, 0.05 + (z - 0.05) * (i + 1) / n - 0.03), 1.2, 0.06,
               "plank" if i % 2 else "plank_b")
    for s in (-1, 1):
        b.beam((s * 0.5, 5.5, -0.05), (s * 0.5, 2.5, z - 0.15), 0.1, 0.14, "timber")
        rail(b, [(s * 0.6, 5.3, 0.1), (s * 0.6, 3.9, 0.5), (s * 0.6, 2.6, z)], h=0.9, mid=False)
    before = len(b.mb.bm.verts)
    buildings.cottage(b.mb, 0.3, 0.3, 4.2, 3.4, 2.5, roof=roof, walls=walls, gable=walls, chimney=True)
    b.mb.bm.verts.ensure_lookup_table()
    bmesh.ops.translate(b.mb.bm, verts=b.mb.bm.verts[before:], vec=(0, 0, z - 0.05))
    # A railed porch toward the water, a ladder down to a boat, nets and a barrel.
    rail(b, [(-2.9, -2.9, z), (0.0, -2.9, z), (2.9, -2.9, z)], h=0.9)
    rail(b, [(-2.9, -2.9, z), (-2.9, -0.2, z), (-2.9, 2.4, z)], h=0.9)
    rail(b, [(2.9, -2.9, z), (2.9, -1.2, z)], h=0.9)
    ladder(b, 2.2, -3.0, z + 0.3, -1.2)
    barrel(b, -2.3, -2.3, z=z)
    for k in range(3):
        b.sphere((1.6 + jit(k, 0.2), -2.2 + jit(k, 0.2, 2), z + 0.15 + 0.1 * k), 0.3 - 0.05 * k, "net", seg=6, rings=4,
                 scale=(1.2, 1, 0.5))
    lantern(b, -1.5, -1.5, z + 2.3)
    b.box((-1.5, -1.45, z + 2.33), (0.06, 0.3, 0.06), "iron")
    h = Hull(3.6, 1.3, 0.26, 0.36, stern_w=0.55, sheer_bow=0.2, sheer_stern=0.08, stern_rise=0.3, n=9, thick=0.06)
    hb = b.at(dx=1.2, dy=-4.3, dz=WATER, rz=80)
    h.build(hb)
    h.deck(hb, 0.04, 0.08, 0.995, mat="plank_b")
    for t in (0.36, 0.64):
        h.thwart(hb, t)
    save(b, name)


def buoy(name, paint="paint_red"):
    root = B()
    b = root.bone("hull")
    b.cyl((0, 0, -0.45), (0, 0, 0.0), 0.3, "wood", r2=0.42, seg=9)
    b.cyl((0, 0, 0.0), (0, 0, 0.5), 0.42, paint, r2=0.3, seg=9)
    for z in (-0.25, 0.3):
        b.cyl((0, 0, z - 0.03), (0, 0, z + 0.03), 0.4, "iron", seg=9)
    b.cyl((0, 0, 0.5), (0, 0, 2.1), 0.04, "timber", seg=5)
    b.solid([(0, 0, 2.05), (0, 0, 1.6), (0, 0.55, 1.82)], [(0.03, 0, 2.05), (0.03, 0, 1.6), (0.03, 0.55, 1.82)], paint)
    b.sphere((0, 0, 2.15), 0.09, "gold", seg=6, rings=4)
    chain(root, (0, 0, -0.45), (0.5, 0.3, -2.6), link=0.2)
    root.box((0.5, 0.3, -2.75), (0.5, 0.5, 0.35), "stone_dark")
    finish(root, name, [], [("bob", 2.5, floating(7.0, 5.0, 0.06), None)])


# --- Small boats ---------------------------------------------------------------------


def coracle(name):
    root = B()
    b = root.bone("hull")
    bones = []
    h = Hull(1.9, 1.6, 0.26, 0.24, tm=0.5, bow_p=0.42, stern_p=0.42, sheer_bow=0.03, sheer_stern=0.03, bow_rise=0.35,
             stern_rise=0.35, n=10, flat=0.75, thick=0.04)
    h.build(b, strakes=("hide", "hide", "wood_dark"), inner="thatch_dark", rail="thatch", posts=False, keel=False)
    h.deck(b, 0.03, 0.04, 0.96, mat="thatch_dark", alt="hay")
    for t in (0.25, 0.5, 0.75):
        b.box((0, h.y(t), h.top(t) - 0.02), (2 * h.w(t), 0.04, 0.03), "wood")
    b.box((0, 0, h.top(0.5) - 0.04), (0.04, 1.7, 0.03), "wood")
    h.thwart(b, 0.55, drop=0.06, wide=0.24)
    bones.append(("paddle", (0.3, -0.5, 0.45), (0.3, -0.5, 0.75), "hull"))
    p = b.bone("paddle")
    p.cyl((0.2, -0.35, 0.95), (0.35, -0.75, -0.2), 0.025, "wood", seg=5)
    p.beam((0.33, -0.7, -0.02), (0.37, -0.82, -0.38), 0.15, 0.03, "wood_light")
    stroke = lambda t: ({"paddle": [(kit.Z, 20 * math.sin(2 * math.pi * t)),
                                    (kit.X, 8 * (1 - math.cos(2 * math.pi * t)))]}, {})
    finish(root, name, bones, [("bob", 2.5, floating(6.0, 4.0, 0.03), None),
                               ("row", 1.6, merge(floating(4.0, 3.0, 0.02), stroke), 0.9)])


def punt(name, cargo="reeds"):
    root = B()
    b = root.bone("hull")
    bones = []
    h = Hull(5.6, 1.25, 0.2, 0.3, tm=0.5, bow_p=0.22, stern_w=0.75, stern_p=0.3, sheer_bow=0.14, sheer_stern=0.1,
             bow_rise=0.75, stern_rise=0.6, n=10, flat=0.92, thick=0.05)
    h.build(b, strakes=("wood", "wood_dark", "wood_dark"), inner="wood_light", keel=False, posts=False)
    h.deck(b, 0.03, 0.04, 0.99, mat="plank", alt="plank_b")
    h.deck(b, h.top(0.9) - 0.03, 0.84, 0.99, mat="wood")
    h.thwart(b, 0.3, drop=0.08, wide=0.22)
    if cargo == "reeds":
        for k in range(5):
            x = -0.3 + (k % 3) * 0.3
            z = 0.17 + (k // 3) * 0.22
            b.cyl((x, h.y(0.38), z), (x, h.y(0.72), z), 0.14, "hay" if k % 2 else "thatch", seg=6)
            b.cyl((x, h.y(0.5), z), (x, h.y(0.52), z), 0.15, "rope", seg=6)
    else:
        crate(b, 0.0, h.y(0.45), z=0.03, s=0.6)
        sack(b, -0.1, h.y(0.62), z=0.03)
        sack(b, 0.2, h.y(0.7), z=0.03)
    bones.append(("pole", (0.45, h.y(0.9), 1.2), (0.45, h.y(0.9), 1.5), "hull"))
    p = b.bone("pole")
    p.cyl((0.3, h.y(0.82), 2.6), (0.7, h.y(1.0) + 0.5, -1.4), 0.03, "wood_light", seg=5)
    push = lambda t: ({"pole": [(kit.X, 10 * math.sin(2 * math.pi * t))]},
                      {"pole": (0.0, 0.0, 0.25 * (0.5 - 0.5 * math.cos(2 * math.pi * t)))})
    finish(root, name, bones, [("bob", 3.0, floating(3.0, 1.0, 0.02), None),
                               ("row", 2.4, merge(floating(2.0, 1.0, 0.02), push), 1.0)])


def houseboat(name, roof="shingle", walls="plaster_warm"):
    root = B()
    b = root.bone("hull")
    h = Hull(9.0, 3.4, 0.45, 0.6, tm=0.5, bow_p=0.32, stern_w=0.78, stern_p=0.4, sheer_bow=0.2, sheer_stern=0.1,
             bow_rise=0.6, stern_rise=0.3, n=12, flat=0.88, thick=0.09)
    h.build(b, strakes=("paint_green", "wood", "tar"), inner="wood")
    dz = 0.25
    h.deck(b, dz, 0.05, 0.97, mat="plank", alt="plank_b", steps=20)
    cy, cw, cd, ch = 0.9, 2.5, 4.6, 1.9
    b.box((0, cy, dz + ch / 2), (cw, cd, ch), walls)
    for x in (-cw / 2, cw / 2):
        for y in (-cd / 2, 0, cd / 2):
            b.box((x, cy + y, dz + ch / 2), (0.12, 0.12, ch), "timber")
        b.box((x, cy, dz + ch - 0.06), (0.12, cd, 0.12), "timber")
        for y in (-1.2, 1.2):
            s = 1 if x > 0 else -1
            b.box((x + s * 0.03, cy + y, dz + 1.15), (0.06, 0.7, 0.55), "window")
            b.box((x + s * 0.14, cy + y, dz + 0.78), (0.2, 0.8, 0.14), "wood")
            for k in range(3):
                b.sphere((x + s * 0.14, cy + y - 0.25 + k * 0.25, dz + 0.9), 0.09,
                         ("flowers", "flowers_y", "leaves")[k], seg=5, rings=3)
    b.box((0, cy - cd / 2 - 0.03, dz + 0.8), (0.8, 0.06, 1.55), "door")
    roof_y(b, 0, cy, cw, cd, dz + ch, 0.9, 0.25, list(ROOFS[roof]), rows=4, gables=(-1, 1), gable_mat=walls)
    b.cyl((0.6, cy + 1.4, dz + ch + 0.3), (0.6, cy + 1.4, dz + ch + 1.5), 0.13, "iron", seg=7)
    b.cyl((0.6, cy + 1.4, dz + ch + 1.5), (0.6, cy + 1.4, dz + ch + 1.6), 0.19, "iron", seg=7)
    # A line of washing at the bow, a chair, a barrel and a fishing rod.
    for x in (-1.0, 1.0):
        b.cyl((x, h.y(0.1), dz), (x, h.y(0.1), dz + 1.7), 0.035, "timber", seg=5)
    rope(b, sag((-1.0, h.y(0.1), dz + 1.65), (1.0, h.y(0.1), dz + 1.65), 0.1, 5), r=0.012)
    for k, mat in enumerate(("cloth_white", "cloth_red", "cloth_blue")):
        b.box((-0.6 + k * 0.6, h.y(0.1), dz + 1.25), (0.4, 0.03, 0.6), mat)
    barrel(b, 0.9, h.y(0.2), z=dz, h=0.6, r=0.25)
    b.box((-0.7, h.y(0.22), dz + 0.4), (0.45, 0.45, 0.06), "wood")
    b.box((-0.7, h.y(0.22) + 0.2, dz + 0.65), (0.45, 0.05, 0.5), "wood")
    for dx in (-0.18, 0.18):
        b.box((-0.7 + dx, h.y(0.22), dz + 0.2), (0.05, 0.4, 0.4), "timber")
    b.cyl((1.3, h.y(0.93), dz), (1.9, h.y(1.0) + 1.8, dz + 2.2), 0.02, "wood_light", seg=4)
    lantern(b, 0, cy - cd / 2 - 0.25, dz + ch - 0.05)
    finish(root, name, [], [("bob", 4.0, floating(1.5, 0.8, 0.03), None)])


model("bridge_aqueduct", aqueduct)
model("bridge_aqueduct_brick", aqueduct, pal=BRICK)
model("bridge_stone_arch_site", bridge_site)
model("bridge_stone_arch_shrine", stone_bridge, extra=shrine)
model("dock_sluice", sluice)
model("dock_harbor_chain", harbor_chain)
model("dock_warehouse", warehouse)
model("dock_warehouse_tile", warehouse, roof="tile")
model("dock_saltworks", saltworks)
model("dock_stilt_house", stilt_house)
model("dock_stilt_house_wood", stilt_house, roof=("shingle", "shingle_dark"), walls="wood_light")
model("dock_buoy", buoy)
model("dock_buoy_green", buoy, paint="paint_green")
model("boat_coracle", coracle)
model("boat_punt", punt)
model("boat_punt_cargo", punt, cargo="goods")
model("boat_houseboat", houseboat)
model("boat_houseboat_tile", houseboat, roof="tile", walls="plaster")
