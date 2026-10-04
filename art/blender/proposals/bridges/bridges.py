"""Bridges of the `bridges` family. Every bridge runs along X, stands on the
ground of the banks at Z = 0 and sends its supports below 0 into the river."""

import math

from parts import (B, BRICK, CRYSTAL, MARBLE, MOSSY, ROOFS, STONE, TARRED, WOOD, arch, barrel_y, blocks, chain, jit,
                   lantern, lerp, log, parapet, pier, pilaster, planks_x, rail, road, rock, rope, sag, save,
                   smoothstep)
import _kit as kit
import buildings

MODELS = {}


def model(name, fn, **kw):
    MODELS[name] = lambda: fn(name, **kw)


# --- Log footbridge ------------------------------------------------------------------


def log_foot(name, double=False, length=9.0):
    b = B()
    half = length / 2
    if double:
        r = 0.34
        for s in (-1, 1):
            log(b, (-half, s * 0.38, 0.0), (half, s * 0.38, 0.0), r, r2=r * 0.88, seg=9)
        planks_x(b, -half + 0.4, half - 0.4, 1.35, z=r + 0.06, step=0.28)
        top = r + 0.06
        sides = (-1, 1)
        rail_y = 0.66
    else:
        r = 0.44
        log(b, (-half, 0, 0.02), (half, 0, 0.02), r, r2=r * 0.84, seg=10)
        b.box((0, 0, 0.02 + r * 0.9), (length - 0.8, 0.52, 0.1), "log_end")
        top = 0.02 + r * 0.9 + 0.05
        # Branch stubs and a root flare at the thick end.
        for i, x in enumerate((-3.1, -1.2, 1.5, 3.2)):
            s = -1
            b.cyl((x, s * 0.3, 0.05), (x + 0.15, s * 0.78, 0.3 + jit(i, 0.1)), 0.09, "log", r2=0.06, seg=6)
            b.cyl((x + 0.148, s * 0.775, 0.298 + jit(i, 0.1)), (x + 0.153, s * 0.79, 0.306 + jit(i, 0.1)), 0.05,
                  "log_end", seg=6)
        for i in range(5):
            a = math.pi * (0.2 + i * 0.4)
            b.cyl((-half + 0.3, 0, 0.02), (-half - 0.25, math.cos(a) * 0.75, 0.02 + math.sin(a) * 0.7), 0.16, "log",
                  r2=0.04, seg=5)
        sides = (1,)
        rail_y = 0.6
    # Flat stones as a step on each bank.
    for s in (-1, 1):
        rock(b, s * (half - 0.25), 0.05 if double else -0.02, 0.5, -0.2, top * 0.55, seed=s + 3, mat="stone",
             shrink=0.8)
    for s in sides:
        xs = [-half + 0.9 + i * (length - 1.8) / 4 for i in range(5)]
        for i, x in enumerate(xs):
            b.cyl((x, s * (rail_y - 0.12), -0.1), (x, s * rail_y, top + 1.0), 0.05, "wood", r2=0.04, seg=6)
            b.cyl((x, s * (rail_y - 0.06), top * 0.6), (x, s * (rail_y - 0.06), top * 0.6 + 0.08), 0.085, "rope",
                  seg=6)
        for xa, xb in zip(xs, xs[1:]):
            b.cyl((xa - 0.15, s * rail_y, top + 0.92), (xb + 0.15, s * rail_y, top + 0.92), 0.04, "wood_light",
                  seg=6)
        for x in xs:
            b.cyl((x, s * rail_y, top + 0.86), (x, s * rail_y, top + 0.98), 0.065, "rope", seg=6)
    save(b, name)


# --- Plank bridge on trestles --------------------------------------------------------


def trestle_bent(b, x, width, z_top, pal, deep=-3.0, splay=0.35):
    """Two splayed piles, a cap beam and a cross brace, across the bridge."""
    y = width / 2 - 0.25
    for s in (-1, 1):
        b.cyl((x, s * (y + splay), deep), (x, s * y, z_top), 0.12, pal["body"], r2=0.1, seg=7)
    b.box((x, 0, z_top + 0.09), (0.22, width + 0.2, 0.18), pal["trim"])
    zb = max(deep + 0.6, -1.6)
    for s in (-1, 1):
        b.beam((x + 0.1 * s, -s * (y + 0.12), zb), (x + 0.1 * s, s * y, z_top - 0.1), 0.07, 0.14, pal["trim"])


def plank_trestle(name, pal=WOOD, length=10.0, width=3.0, rails=True, extra=None):
    b = B()
    half = length / 2
    zd = 0.3
    bents = max(1, round(length / 2.5) - 1)
    for i in range(bents):
        trestle_bent(b, -half + (i + 1) * length / (bents + 1), width, zd - 0.45, pal)
    for y in (-width / 2 + 0.3, 0.0, width / 2 - 0.3):
        b.box((0, y, zd - 0.17), (length - 0.3, 0.16, 0.2), pal["trim"])
    planks_x(b, -half + 0.5, half - 0.5, width, z=zd, mats=pal["deck"])
    for s in (-1, 1):
        # Bank sill of logs and the short ramp up to the deck.
        log(b, (s * (half - 0.45), -width / 2 - 0.1, -0.02), (s * (half - 0.45), width / 2 + 0.1, -0.02), 0.2,
            bark=pal["body"], seg=7)
        for k in range(2):
            xa = s * (half - 0.5 + k * 0.25)
            xb = s * (half - 0.25 + k * 0.25)
            b.beam((xa, 0, zd - 0.035 - k * 0.14), (xb, 0, zd - 0.175 - k * 0.14), width - 0.05, 0.07,
                   pal["deck"][k % 2])
    if rails:
        for s in (-1, 1):
            n = max(2, round(length / 2.0))
            pts = [(-half + 0.6 + i * (length - 1.2) / n, s * (width / 2 - 0.08), zd) for i in range(n + 1)]
            rail(b, pts, h=1.0, mat=pal["trim"], rail_mat=pal["body"])
    save(b, name, mech=extra(b, length, width, zd, pal) if extra else None)


# --- Rope suspension bridge ----------------------------------------------------------


def rope_bridge(name, length=12.0, width=1.4, planks=36, pal=WOOD):
    b = B()
    half = length / 2
    run = half - 1.4           # Half-length of the hanging part.
    drop = 0.6
    base = 0.72                # The ends stand on a plinth, so the sag stays above the banks.

    def zf(x):
        return base - drop * (1 - (x / run) ** 2)

    # End frames: two posts, a lintel, a threshold and anchor stakes.
    for s in (-1, 1):
        x = s * run
        for y in (-1, 1):
            b.cyl((x, y * (width / 2 + 0.12), -0.4), (x, y * (width / 2 + 0.12), base + 2.3), 0.11, pal["trim"],
                  r2=0.09, seg=7)
            b.cyl((x, y * (width / 2 + 0.12), base + 1.0), (x, y * (width / 2 + 0.12), base + 1.12), 0.14, "rope",
                  seg=7)
            stake = (x + s * 0.65, y * (width / 2 + 0.45), 0.0)
            b.cyl((stake[0] + s * 0.1, stake[1], -0.3), (stake[0] - s * 0.08, stake[1], 0.45), 0.06, pal["body"],
                  seg=6)
            rope(b, [(x, y * (width / 2 + 0.12), base + 1.06), (stake[0], stake[1], 0.3)], r=0.028)
        b.box((x, 0, base + 2.15), (0.14, width + 0.6, 0.14), pal["trim"])
        planks_x(b, min(x, x + s * 0.7), max(x, x + s * 0.7), width + 0.1, z=base + 0.01, mats=pal["deck"],
                 step=0.23)
        b.box((x + s * 0.35, 0, (base - 0.06) / 2), (0.7, width + 0.3, base - 0.06), "stone_dark")
        b.box((x + s * 0.85, 0, 0.22), (0.3, width - 0.1, 0.44), "stone")
        b.box((x + s * 1.15, 0, 0.11), (0.3, width - 0.1, 0.22), "stone_dark")
    # Hanging deck: every board is a bone, so the bridge can sway.
    step = 2 * run / planks
    bones = []
    for i in range(planks):
        xa, xb = -run + i * step, -run + (i + 1) * step
        xm = (xa + xb) / 2
        name_i = "p%02d" % i
        bones.append((name_i, (xm, 0, zf(xm) + 1.0), (xm, 0, zf(xm) + 1.3), None))
        p = b.bone(name_i)
        p.beam((xa + 0.02, 0, zf(xa) - 0.03), (xb - 0.02, 0, zf(xb) - 0.03), width + jit(i, 0.05), 0.05,
               pal["deck"][i % 2])
        for y in (-1, 1):
            ye = y * (width / 2 - 0.08)
            p.cyl((xa, ye, zf(xa) - 0.07), (xb, ye, zf(xb) - 0.07), 0.03, "rope", seg=5)
            yh = y * (width / 2 + 0.1)
            p.cyl((xa, yh, zf(xa) + 1.05), (xb, yh, zf(xb) + 1.05), 0.03, "rope", seg=5)
            if i % 3 == 1:
                p.cyl((xm, ye, zf(xm) - 0.05), (xm, yh, zf(xm) + 1.05), 0.015, "rope", seg=4)
                p.cyl((xm, ye, zf(xm) - 0.05), (xm + step * 1.4, yh, zf(xm + step * 1.4) + 1.05), 0.012, "rope",
                      seg=4)
    mech = kit.Mech(bones)

    def sway(t):
        turns, moves = {}, {}
        for i in range(planks):
            u = (i + 0.5) / planks
            amp = math.sin(math.pi * u)
            w = math.sin(2 * math.pi * t)
            turns["p%02d" % i] = [(kit.X, -7.0 * amp * w)]
            moves["p%02d" % i] = (0.0, 0.0, 0.05 * math.sin(2 * math.pi * u) * math.sin(4 * math.pi * t))
        return turns, moves

    mech.clip("sway", 3.0, sway)
    save(b, name, mech=mech)


# --- Stone and brick arch bridges ----------------------------------------------------


def stone_bridge(name, arches=1, span=7.0, width=4.0, pier_w=1.0, abut=2.5, hump=1.7, pal=STONE, zs=-0.6,
                 deep=-3.0, broken=(), ring=0.28, n=9, moss=False, lamps=False, extra=None, level=False):
    b = B()
    length = arches * span + (arches - 1) * pier_w + 2 * abut
    x0, x1 = -length / 2, length / 2
    y0, y1 = -width / 2, width / 2

    def top(x):
        x = max(x0, min(x1, x))
        if level:   # A level road between two ramps, instead of one long hump.
            return hump * smoothstep(min(x - x0, x1 - x) / abut)
        return hump * 0.5 * (1 + math.cos(2 * math.pi * x / length))

    gaps = []
    for i in range(arches):
        xc = x0 + abut + span / 2 + i * (span + pier_w)
        half = span / 2 - ring
        rise = min(top(xc - half * 0.4) - 0.2 - ring - zs, half * 1.1)
        if i in broken:
            keep = (0, 1, n - 2, n - 1)
            cut = (half + ring) * math.cos(math.pi * 2 / n)
            gaps.append((xc - cut, xc + cut))
            for k in range(9):   # Fallen stones under the gap.
                rock(b, xc + jit(k, half * 0.9, 1), jit(k, width * 0.6, 2), 0.35 + abs(jit(k, 0.25, 3)), deep,
                     deep + 0.5 + abs(jit(k, 0.5, 4)), seed=k, mat=pal["body"] if k % 2 else pal["trim"])
            for s in (-1, 1):   # Jagged stones on the broken edges.
                for k in range(3):
                    xs = xc + s * (cut + 0.25 + k * 0.1)
                    b.box((xs, y0 + 0.6 + k * 1.2, top(xs) + 0.1), (0.5, 0.7, 0.3 + 0.1 * k), pal["trim"],
                          rz=jit(k, 0.4, s))
        else:
            keep = None
        arch(b, xc, half, rise, zs, top, y0, y1, pal, n=n, ring=ring, keep=keep)
        if i < arches - 1:
            xj = xc + span / 2 + pier_w / 2
            b.xz([(xj - pier_w / 2, zs), (xj + pier_w / 2, zs), (xj + pier_w / 2, top(xj + pier_w / 2)),
                  (xj - pier_w / 2, top(xj - pier_w / 2))], y0, y1, pal["body"])
            pier(b, xj, pier_w + 2 * ring, y0, y1, deep, zs, pal)
            for y in (y0, y1):
                b.box((xj, y, lerp(zs, top(xj), 0.5) + 0.1), (pier_w * 0.7, 0.16, top(xj) - zs + 0.2), pal["trim"])
    for s, xa in ((-1, x0), (1, x1 - abut)):
        xb = xa + abut
        slices = max(2, round(abut * 2))
        for k in range(slices):   # In slices, so the fill follows the curve of the road.
            xk, xl = xa + abut * k / slices, xa + abut * (k + 1) / slices
            b.xz([(xk, zs), (xl, zs), (xl, top(xl)), (xk, top(xk))], y0, y1, pal["body"])
        lo, hi = (xa, xb + ring) if s < 0 else (xa - ring, xb)
        b.box(((lo + hi) / 2, 0, (deep + zs) / 2), (hi - lo, width + 0.2, zs - deep), pal["body"])
        b.box(((lo + hi) / 2, 0, zs - 0.12), (hi - lo + 0.1, width + 0.34, 0.24), pal["trim"])
        blocks(b, lo, hi, y0 - 0.1, deep + 0.3, zs - 0.4, pal, face=-1, count=5, seed=s)
        blocks(b, lo, hi, y1 + 0.1, deep + 0.3, zs - 0.4, pal, face=1, count=5, seed=s + 7)
    # Road, string course and parapets, leaving out the broken stretches.
    cuts = sorted(gaps)
    stretches = []
    start = x0
    for ga, gb in cuts:
        stretches.append((start, ga))
        start = gb
    stretches.append((start, x1))
    for xa, xb in stretches:
        road(b, xa, xb, y0 + 0.3, y1 - 0.3, top, pal["road"])
        for y, face in ((y0, -1), (y1, 1)):
            parapet(b, xa, xb, y + -face * 0.15, top, pal)
            m = max(1, round(xb - xa))
            for k in range(m):
                xk, xl = lerp(xa, xb, k / m), lerp(xa, xb, (k + 1) / m)
                b.xz([(xk, top(xk) - 0.22), (xl, top(xl) - 0.22), (xl, top(xl) - 0.06), (xk, top(xk) - 0.06)],
                     min(y, y + face * 0.05), max(y, y + face * 0.05), pal["trim"])
    for x in (x0 + 0.27, x1 - 0.27):
        for y in (y0 + 0.15, y1 - 0.15):
            pilaster(b, x, y, top(x), pal)
            if lamps:
                lantern(b, x, y, top(x) + 1.95)
                b.box((x, y, top(x) + 1.75), (0.06, 0.06, 0.5), "iron")
    if moss:
        for k in range(14):
            x = jit(k, length * 0.48, 11)
            if any(ga - 0.3 < x < gb + 0.3 for ga, gb in gaps):
                continue
            y = (y0 + 0.15) if k % 2 else (y1 - 0.15)
            b.box((x, y, top(x) + 1.02), (0.7 + jit(k, 0.3), 0.44, 0.08), "moss")
            b.box((x, y0 - 0.03 if k % 2 else y1 + 0.03, top(x) - 0.5 + jit(k, 0.3, 2)), (0.6, 0.08, 0.5), "moss")
    save(b, name, mech=extra(b, top, length, width, pal) if extra else None)


# --- Covered wooden bridge -----------------------------------------------------------


def covered(name, roof="shingle", length=10.0, width=4.0):
    b = B()
    half = length / 2
    zd = 0.3
    for s in (-1, 1):
        b.box((s * (half - 0.7), 0, -1.45), (1.4, width + 0.4, 3.1), "stone")
        b.box((s * (half - 0.7), 0, 0.02), (1.5, width + 0.5, 0.16), "stone_dark")
        blocks(b, s * (half - 1.3), s * (half - 0.1), -width / 2 - 0.2, -2.6, -0.3, STONE, face=-1, count=4, seed=s)
        b.beam((s * (half + 0.55), 0, 0.0), (s * half, 0, zd - 0.02), width - 0.5, 0.08, "plank_b")
    pier(b, 0, 0.9, -width / 2, width / 2, -3.0, -0.05, STONE)
    for y in (-width / 2 + 0.3, -0.6, 0.6, width / 2 - 0.3):
        b.box((0, y, zd - 0.2), (length, 0.2, 0.26), "timber")
    planks_x(b, -half, half, width - 0.1, z=zd)
    wall_h = zd + 2.5
    bays = 5
    xs = [-half + 0.15 + i * (length - 0.3) / bays for i in range(bays + 1)]
    for s in (-1, 1):
        y = s * (width / 2 - 0.12)
        for x in xs:
            b.box((x, y, zd + 1.25), (0.2, 0.2, 2.5), "timber")
        b.box((0, y, wall_h - 0.1), (length - 0.1, 0.2, 0.2), "timber")
        b.box((0, y, zd + 1.05), (length - 0.1, 0.14, 0.14), "timber")
        for k in range(4):   # Lower wall of boards.
            b.box((0, y + s * 0.04, zd + 0.14 + k * 0.24), (length - 0.3, 0.05, 0.22),
                  "wood" if k % 2 else "wood_light")
        for i in range(bays):   # Braces above the boards: an X in every bay.
            xa, xb = xs[i] + 0.1, xs[i + 1] - 0.1
            b.beam((xa, y, zd + 1.15), (xb, y, wall_h - 0.2), 0.08, 0.1, "wood")
            b.beam((xa, y, wall_h - 0.2), (xb, y, zd + 1.15), 0.08, 0.1, "wood")
    for x in xs:   # Tie beams and knee braces.
        b.box((x, 0, wall_h - 0.1), (0.16, width - 0.2, 0.16), "timber")
        for s in (-1, 1):
            b.beam((x, s * (width / 2 - 0.2), wall_h - 0.75), (x, s * (width / 2 - 0.85), wall_h - 0.15), 0.1, 0.1,
                   "timber")
    buildings.gable_roof(b.mb, 0, 0, length - 0.1, width, wall_h, 1.3, 0.35, list(ROOFS[roof]), rows=5,
                         gable="wood_light")
    for s in (-1, 1):
        lantern(b, s * (half - 0.05), 0, wall_h - 0.2)
    save(b, name)


# --- Drawbridge ----------------------------------------------------------------------


def drawbridge(name, pal=STONE, width=4.0):
    b = B()
    leaf_w = width - 0.7
    hinge = -2.5
    tip = 2.1
    post_h = 4.2
    arm = tip - hinge
    for s in (-1, 1):
        xc = s * 3.75
        b.box((xc, 0, -1.5), (2.5, width, 3.0), pal["body"])
        b.box((xc, 0, -0.1), (2.56, width + 0.12, 0.2), pal["trim"])
        b.box((xc, 0, -2.7), (2.8, width + 0.4, 0.6), pal["trim"])
        road(b, xc - 1.25, xc + 1.25, -width / 2 + 0.3, width / 2 - 0.3, lambda x: 0.0, pal["road"])
        blocks(b, xc - 1.1, xc + 1.1, -width / 2, -2.2, -0.4, pal, face=-1, count=5, seed=s)
        blocks(b, xc - 1.1, xc + 1.1, width / 2, -2.2, -0.4, pal, face=1, count=5, seed=s + 4)
        for y in (-1, 1):
            parapet(b, xc - 1.25, xc + 1.25, y * (width / 2 - 0.15), lambda x: 0.0, pal, h=0.85)
            pilaster(b, s * 4.75, y * (width / 2 - 0.15), 0.0, pal)
    # The frame that carries the balance beams, on the hinge side.
    for y in (-1, 1):
        yp = y * (width / 2 - 0.15)
        b.box((hinge, yp, post_h / 2), (0.26, 0.26, post_h), "timber")
        b.beam((hinge - 1.9, yp, 0.85), (hinge - 0.1, yp, 3.0), 0.14, 0.18, "wood")
        b.box((hinge, yp, 0.5), (0.4, 0.4, 1.0), pal["body"])
    b.cyl((hinge, -width / 2 - 0.05, post_h), (hinge, width / 2 + 0.05, post_h), 0.09, "iron", seg=7)
    b.box((hinge, 0, 3.3), (0.18, width - 0.3, 0.18), "timber")
    bm = b.bone("beam")
    yb = leaf_w / 2 - 0.05
    for y in (-1, 1):
        bm.box(((tip + hinge - 2.3) / 2, y * yb, post_h + 0.02), (tip - hinge + 2.3, 0.18, 0.22), "timber")
    bm.box((hinge - 2.15, 0, post_h + 0.02), (0.2, 2 * yb + 0.3, 0.2), "timber")
    bm.box((hinge - 1.75, 0, post_h - 0.42), (1.0, 2 * yb - 0.2, 0.6), "stone_dark")
    bm.box((hinge - 1.75, 0, post_h - 0.42), (0.14, 2 * yb - 0.1, 0.68), "iron")
    bm.box((tip, 0, post_h + 0.02), (0.16, 2 * yb + 0.3, 0.16), "timber")
    ch = b.bone("chain")
    for y in (-1, 1):
        chain(ch, (tip, y * yb, 0.02), (tip, y * yb, post_h - 0.08))
    lf = b.bone("leaf")
    planks_x(lf, hinge + 0.03, 2.5, leaf_w, z=0.0, step=0.3, thick=0.09)
    for y in (-1, 0, 1):
        lf.box(((hinge + 2.5) / 2, y * (leaf_w / 2 - 0.12), -0.17), (2.5 - hinge - 0.1, 0.16, 0.16), "timber")
    for x in (hinge + 0.4, 0.0, tip):
        lf.box((x, 0, 0.012), (0.1, leaf_w + 0.04, 0.03), "iron")
    for y in (-1, 1):
        lf.cyl((tip, y * yb - 0.07, 0.03), (tip, y * yb + 0.07, 0.03), 0.07, "iron", seg=6)
    mech = kit.Mech([("leaf", (hinge, 0, -0.05), (hinge, 0, 0.5), None),
                     ("beam", (hinge, 0, post_h), (hinge, 0, post_h + 0.5), None),
                     ("chain", (tip, 0, 2.0), (tip, 0, 2.5), None)])

    def pose(angle):
        a = math.radians(angle)
        return ({"leaf": [(kit.Y, -angle)], "beam": [(kit.Y, -angle)]},
                {"chain": (arm * (math.cos(a) - 1), 0.0, arm * math.sin(a))})

    mech.clip("open", 3.0, lambda t: pose(72 * smoothstep(t)), loops=False)
    mech.clip("close", 3.0, lambda t: pose(72 * (1 - smoothstep(t))), loops=False)
    save(b, name, mech=mech)


# --- Pontoon bridge ------------------------------------------------------------------


def pontoon(name, floats="barrels", length=12.0, width=3.0, sections=4):
    b = B()
    half = length / 2
    sec = 2.4
    xs0 = -sections * sec / 2
    zd = 0.12
    for s in (-1, 1):
        xe = s * abs(xs0)
        log(b, (s * (half - 0.3), -width / 2 - 0.15, 0.0), (s * (half - 0.3), width / 2 + 0.15, 0.0), 0.17, seg=7)
        b.beam((s * (half - 0.1), 0, 0.03), (xe, 0, zd - 0.035), width - 0.1, 0.07, "plank_b")
        for y in (-1, 1):
            px, py = s * (half - 0.45), y * (width / 2 + 0.3)
            b.cyl((px, py, -0.5), (px, py, 1.0), 0.1, "timber", r2=0.08, seg=7)
            rope(b, sag((px, py, 0.75), (xe - s * 0.25, y * (width / 2 - 0.1), zd + 0.1), 0.12, 4), r=0.03)
    bones = []
    for i in range(sections):
        xc = xs0 + sec * (i + 0.5)
        bone = "sec%d" % i
        bones.append((bone, (xc, 0, -0.35), (xc, 0, 0.2), None))
        p = b.bone(bone)
        planks_x(p, xc - sec / 2 + 0.03, xc + sec / 2 - 0.03, width, z=zd)
        for y in (-width / 2 + 0.2, 0.0, width / 2 - 0.2):
            p.box((xc, y, zd - 0.14), (sec - 0.08, 0.14, 0.14), "timber")
        if floats == "barrels":
            for dx in (-0.72, 0.72):
                for dy in (-0.72, 0.72):
                    barrel_y(p, xc + dx, dy, zd - 0.21 - 0.36, 1.35, 0.36)
                rope(p, [(xc + dx, -width / 2 + 0.2, zd - 0.2), (xc + dx, -width / 2 + 0.2, zd - 0.95),
                         (xc + dx, width / 2 - 0.2, zd - 0.95), (xc + dx, width / 2 - 0.2, zd - 0.2)], r=0.025)
        else:
            # A punt across the bridge, its ends sticking out up and down the river.
            p.yz([(-2.3, zd - 0.21), (-1.6, zd - 0.95), (1.6, zd - 0.95), (2.3, zd - 0.21)], xc - 0.75, xc + 0.75,
                 "wood_dark")
            p.yz([(-2.36, zd - 0.21), (-2.36, zd - 0.11), (2.36, zd - 0.11), (2.36, zd - 0.21)], xc - 0.8,
                 xc + 0.8, "timber")
            for y in (-1, 1):
                p.box((xc, y * 1.95, zd - 0.09), (1.4, 0.55, 0.04), "wood_light")
                p.cyl((xc, y * 2.2, zd - 0.1), (xc, y * 2.2, zd + 0.35), 0.06, "timber", seg=6)
        for y in (-1, 1):
            for dx in (-sec / 2 + 0.2, sec / 2 - 0.2):
                p.cyl((xc + dx, y * (width / 2 - 0.08), zd), (xc + dx, y * (width / 2 - 0.08), zd + 0.95), 0.045,
                      "timber", seg=6)
            rope(p, sag((xc - sec / 2 + 0.2, y * (width / 2 - 0.08), zd + 0.9),
                        (xc + sec / 2 - 0.2, y * (width / 2 - 0.08), zd + 0.9), 0.1, 4), r=0.025)
    mech = kit.Mech(bones)

    def bob(t):
        turns, moves = {}, {}
        for i in range(sections):
            ph = 2 * math.pi * t + i * 1.4
            turns["sec%d" % i] = [(kit.X, 2.2 * math.sin(ph + 0.8)), (kit.Y, 1.2 * math.sin(ph))]
            moves["sec%d" % i] = (0.0, 0.0, 0.05 * math.sin(ph))
        return turns, moves

    mech.clip("bob", 3.0, bob)
    save(b, name, mech=mech)


# --- Stepping stones and fords -------------------------------------------------------


def stepping_stones(name, length=8.0, mat="stone"):
    b = B()
    n = round(length / 0.9)
    for i in range(n):
        x = -length / 2 + (i + 0.5) * length / n
        y = 0.28 * (1 if i % 2 else -1) + jit(i, 0.12, 2)
        b_top = 0.02 + abs(jit(i, 0.1, 5))
        rock(b, x, y, 0.42 + jit(i, 0.06, 7), -1.4, b_top, seed=i, mat=mat if i % 3 else "stone_dark", sides=7,
             shrink=0.78, squash=1.15)
        if i % 4 == 1:
            b.box((x + 0.1, y, b_top + 0.01), (0.3, 0.35, 0.03), "moss", rz=jit(i, 1.0))
    for s in (-1, 1):
        rock(b, s * (length / 2 + 0.1), 0, 0.7, -0.6, 0.1, seed=20 + s, mat="stone_dark", shrink=0.85, squash=1.3)
    save(b, name)


def ford(name, length=8.0, width=4.0):
    b = B()
    k = 0
    for ix in range(round(length / 0.8)):
        for iy in range(round(width / 0.8)):
            k += 1
            x = -length / 2 + 0.4 + ix * 0.8 + jit(k, 0.14, 1)
            y = -width / 2 + 0.4 + iy * 0.8 + jit(k, 0.14, 2)
            dip = 0.35 * (1 - (2 * x / length) ** 2)
            rock(b, x, y, 0.46, -0.9, 0.07 - dip + jit(k, 0.04, 3), seed=k,
                 mat=("stone", "stone_dark", "road")[k % 3], sides=6, shrink=0.82)
    for s in (-1, 1):
        for y in (-1, 1):
            px, py = s * (length / 2 - 0.3), y * (width / 2 + 0.25)
            b.cyl((px, py, -0.6), (px, py, 1.3), 0.08, "timber", r2=0.06, seg=6)
            b.cyl((px, py, 1.05), (px, py, 1.25), 0.085, "paint_red", seg=6)
    for y in (-1, 1):
        py = y * (width / 2 + 0.25)
        rope(b, sag((-length / 2 + 0.3, py, 1.0), (length / 2 - 0.3, py, 1.0), 0.45, 10), r=0.025)
    save(b, name)


# --- Fantasy bridges -----------------------------------------------------------------


def living_root(name, length=9.0, width=2.4):
    b = B()
    half = length / 2

    def top(x):
        x = max(-half, min(half, x))
        return 0.75 * 0.5 * (1 + math.cos(2 * math.pi * x / length))

    n = 16
    for k, y0 in enumerate((-0.9, -0.45, 0.0, 0.45, 0.9)):
        pts = []
        for i in range(n + 1):
            x = -half - 0.3 + i * (length + 0.6) / n
            pts.append((x, y0 + 0.11 * math.sin(x * 1.7 + k * 1.3), top(x) - 0.2 + 0.05 * math.sin(x * 2.3 + k * 2)))
        for p, q in zip(pts, pts[1:]):
            b.cyl(p, q, 0.21, "root" if k % 2 else "root_light", seg=6)
    for i in range(7):   # Roots that weave across the others.
        x = -half + 0.6 + i * (length - 1.6) / 6
        s = 1 if i % 2 else -1
        b.cyl((x, -s * 1.0, top(x) - 0.12), (x + 0.9, s * 1.0, top(x + 0.9) - 0.12), 0.1, "root", seg=5)
    for i in range(12):   # Moss and flat stones to walk on.
        x = -half + 0.5 + i * (length - 1.0) / 11
        b.beam((x - 0.3, jit(i, 0.2), top(x - 0.3) + 0.0), (x + 0.3, jit(i, 0.2), top(x + 0.3) + 0.0),
               1.5 + jit(i, 0.2, 3), 0.07, "moss" if i % 3 else "stone_moss")
    for s in (-1, 1):
        pts = []
        for i in range(n + 1):
            x = -half + i * length / n
            pts.append((x, s * (1.12 + 0.06 * math.sin(x * 2.1 + s)), top(x) + 0.95 + 0.07 * math.sin(x * 1.5 + s)))
        for p, q in zip(pts, pts[1:]):
            b.cyl(p, q, 0.07, "root_light", seg=5)
        for i in range(1, n, 2):
            p = pts[i]
            b.cyl((p[0] + 0.25 * (1 if i % 4 == 1 else -1), s * 0.95, top(p[0]) - 0.15), p, 0.05, "root", seg=5)
            if i % 4 == 3:
                b.cyl(p, (p[0], p[1], p[2] - 0.5 - abs(jit(i, 0.3))), 0.02, "moss", seg=4)
                b.sphere((p[0], p[1], p[2] - 0.55 - abs(jit(i, 0.3))), 0.12, "leaves", seg=5, rings=3)
        # The living trees the bridge grows from, one on each bank.
        for e in (-1, 1):
            tx, ty = e * (half + 0.1), s * 1.35
            if e * s > 0:
                b.cyl((tx, ty, -0.4), (tx + e * 0.15, ty, 1.6), 0.4, "root", r2=0.27, seg=7)
                b.cyl((tx + e * 0.15, ty, 1.6), (tx - e * 0.2, ty + s * 0.2, 3.3), 0.27, "root", r2=0.14, seg=7)
                for a in range(4):
                    ang = a * 1.6 + 0.4
                    b.cyl((tx, ty, 0.5), (tx + math.cos(ang) * 0.9, ty + math.sin(ang) * 0.9, -0.3), 0.16, "root",
                          r2=0.06, seg=5)
                for a, (dx, dy, dz, r) in enumerate(((0, 0, 3.7, 1.1), (0.8, 0.3, 3.2, 0.8), (-0.7, -0.4, 3.3, 0.85),
                                                     (0.1, 0.7, 3.0, 0.7))):
                    b.sphere((tx - e * 0.2 + dx, ty + s * 0.2 + dy, dz), r, "leaves" if a % 2 == 0 else "moss",
                             seg=6, rings=4, scale=(1, 1, 0.75))
                b.cyl((tx, ty, 1.3), (tx - e * 1.2, s * 1.15, top(tx - e * 1.2) + 0.95), 0.09, "root_light", seg=5)
            else:
                b.cyl((tx, ty * 0.85, -0.3), (tx - e * 0.4, s * 1.12, top(tx) + 0.98), 0.12, "root", r2=0.07, seg=5)
    for i in range(6):   # Aerial roots that reach for the water.
        x = -half + 1.2 + i * (length - 2.4) / 5
        y = jit(i, 0.8, 4)
        b.cyl((x, y, top(x) - 0.3), (x + jit(i, 0.2, 6), y, -1.6 - abs(jit(i, 0.8, 5))), 0.06, "root", r2=0.02,
              seg=4)
    save(b, name)


def crystal_cluster(b, x, y, z, s=1.0, seed=0, pal=CRYSTAL):
    for k in range(5):
        a = k * 1.26 + seed
        lean = 0.25 + 0.2 * abs(jit(k, 1, seed))
        h = s * (0.5 + 0.9 * abs(jit(k, 1, seed + 2)))
        if k == 0:
            lean, h = 0.05, s * 1.6
        p0 = (x + math.cos(a) * 0.15 * s * (k > 0), y + math.sin(a) * 0.15 * s * (k > 0), z)
        p1 = (p0[0] + math.cos(a) * lean * h, p0[1] + math.sin(a) * lean * h, z + h)
        r = s * (0.16 if k else 0.22)
        mat = (pal["body"], pal["trim"], pal["glow"])[k % 3]
        b.cyl(p0, p1, r, mat, seg=6)
        p2 = (p1[0] + (p1[0] - p0[0]) * 0.22, p1[1] + (p1[1] - p0[1]) * 0.22, p1[2] + h * 0.25)
        b.cyl(p1, p2, r, mat, r2=0.01, seg=6)


def elven(name, pal=MARBLE, length=10.0, width=3.0, crystals=False):
    b = B()
    half = length / 2
    hump = 1.3

    def top(x):
        x = max(-half, min(half, x))
        return hump * 0.5 * (1 + math.cos(2 * math.pi * x / length))

    def under(x):
        return top(x) - 0.26 - 1.7 * (abs(x) / half) ** 2.4

    n = 20
    for i in range(n):
        xa, xb = -half + i * length / n, -half + (i + 1) * length / n
        b.xz([(xa, top(xa) - 0.2), (xb, top(xb) - 0.2), (xb, top(xb)), (xa, top(xa))], -width / 2, width / 2,
             pal["ring"][i % 2])
        for s in (-1, 1):   # Two slender ribs carry the deck.
            ya, yb = sorted((s * (width / 2 - 0.05), s * (width / 2 - 0.4)))
            b.xz([(xa, under(xa)), (xb, under(xb)), (xb, top(xb) - 0.2), (xa, top(xa) - 0.2)], ya, yb, pal["body"])
            yc, yd = sorted((s * (width / 2 + 0.03), s * (width / 2 - 0.05)))
            b.xz([(xa, top(xa) - 0.16), (xb, top(xb) - 0.16), (xb, top(xb) - 0.06), (xa, top(xa) - 0.06)], yc, yd,
                 pal["cap"])
    # A second, lower arch that springs from the water and kisses the deck.
    m = 12
    for s in (-1, 1):
        y = s * (width / 2 - 0.22)
        pts = [(-half * 0.92 * math.cos(math.pi * i / m), y, -2.2 + (under(0.0) + 2.2) * math.sin(math.pi * i / m))
               for i in range(m + 1)]
        for p, q in zip(pts, pts[1:]):
            b.beam(p, q, 0.2, 0.16, pal["trim"])
    for s in (-1, 1):   # Railing of pointed arches.
        y = s * (width / 2 - 0.1)
        k = 12
        xs = [-half + 0.25 + i * (length - 0.5) / k for i in range(k + 1)]
        for i, x in enumerate(xs):
            b.cyl((x, y, top(x)), (x, y, top(x) + 0.95), 0.04, pal["body"], seg=6)
            b.sphere((x, y, top(x) + 1.0), 0.07, pal["cap"], seg=6, rings=4)
        for xa, xb in zip(xs, xs[1:]):
            xm = (xa + xb) / 2
            b.beam((xa, y, top(xa) + 0.9), (xb, y, top(xb) + 0.9), 0.07, 0.06, pal["body"])
            b.beam((xa, y, top(xa) + 0.1), (xm, y, top(xm) + 0.78), 0.04, 0.04, pal["trim"])
            b.beam((xb, y, top(xb) + 0.1), (xm, y, top(xm) + 0.78), 0.04, 0.04, pal["trim"])
        for e in (-1, 1):   # A curved lamp post at each corner.
            x = e * (half - 0.25)
            pts = [(x, y, 0.0), (x, y, 1.6), (x - e * 0.1, y - s * 0.05, 2.3), (x - e * 0.4, y - s * 0.2, 2.75),
                   (x - e * 0.8, y - s * 0.4, 2.85)]
            for p, q in zip(pts, pts[1:]):
                b.cyl(p, q, 0.06, pal["body"], seg=6)
            lantern(b, x - e * 0.8, y - s * 0.4, 2.8, glow=pal["glow"], frame=pal["cap"], s=0.2)
            if crystals:
                crystal_cluster(b, e * (half - 0.2), s * (width / 2 + 0.5), -0.2, 1.1, seed=e * 2 + s, pal=pal)
    if crystals:
        for i in range(5):
            x = -half + 1.5 + i * (length - 3.0) / 4
            for s in (-1, 1):
                p = (x, s * (width / 2 - 0.2), under(x) + 0.05)
                b.cyl(p, (x, s * (width / 2 - 0.2), under(x) - 0.5 - 0.3 * (i % 2)), 0.12, pal["glow"], r2=0.01,
                      seg=6)
    save(b, name)


# --- Registry ------------------------------------------------------------------------

model("bridge_log_foot", log_foot)
model("bridge_log_foot_double", log_foot, double=True)
model("bridge_plank_trestle", plank_trestle)
model("bridge_plank_trestle_tarred", plank_trestle, pal=TARRED)
model("bridge_plank_trestle_short", plank_trestle, length=6.0, rails=False)
model("bridge_rope", rope_bridge)
model("bridge_rope_long", rope_bridge, length=18.0, planks=54)
model("bridge_stone_arch", stone_bridge)
model("bridge_stone_arch_brick", stone_bridge, pal=BRICK)
model("bridge_stone_arch_mossy", stone_bridge, pal=MOSSY, moss=True)
MULTI = {"span": 4.5, "abut": 1.5, "hump": 2.2}
model("bridge_stone_multi", stone_bridge, arches=4, lamps=True, **MULTI)
model("bridge_stone_multi_3", stone_bridge, arches=3, span=4.5, abut=1.75, hump=1.9)
model("bridge_stone_multi_5", stone_bridge, arches=5, span=4.6, abut=1.5, hump=2.5, lamps=True)
model("bridge_stone_multi_brick", stone_bridge, arches=4, pal=BRICK, **MULTI)
model("bridge_stone_multi_level", stone_bridge, arches=4, span=4.5, abut=4.5, hump=2.4, level=True, lamps=True)
model("bridge_ruined", stone_bridge, arches=4, pal=MOSSY, broken=(1, 2), moss=True, **MULTI)
model("bridge_ruined_single", stone_bridge, pal=MOSSY, broken=(0,), moss=True)
model("bridge_covered", covered, roof="shingle")
model("bridge_covered_thatch", covered, roof="thatch")
model("bridge_covered_tile", covered, roof="tile")
model("bridge_draw", drawbridge)
model("bridge_draw_brick", drawbridge, pal=BRICK)
model("bridge_pontoon", pontoon)
model("bridge_pontoon_boats", pontoon, floats="boats")
model("bridge_stepping_stones", stepping_stones)
model("bridge_ford", ford)
model("bridge_living_root", living_root)
model("bridge_elven", elven)
model("bridge_crystal", elven, pal=CRYSTAL, crystals=True)
