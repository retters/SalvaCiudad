"""A modular bridge kit: pieces that an algorithm chains along X to build a
bridge of any even length.

Module: 2 m along X, 4 m wide, deck 1 m above the banks (Z = 0). Every piece
has its origin in the center of its footprint. Rule for a bridge of L meters
(even, 10 or more): an abutment (4 m ramp) at each end, the second one turned
180 degrees; between them spans of 4 m, plus one of 2 m, placed first, when
(L - 8) is not a multiple of 4; a pier under every joint between two spans;
a pair of end posts at the foot of each ramp.
"""

import math

from parts import (B, BRICK, ROOFS, STONE, WOOD, arch, blocks, chain, lantern, log, parapet, pier, pilaster, planks_x,
                   rail, road, roof_x, save, smoothstep)
from bridges import trestle_bent
import _kit as kit

MODELS = {}
H = 1.0        # Deck height above the banks.
W = 4.0        # Width of the bridge.
ZS = -0.6      # Where the masonry arches spring from.
DEEP = -4.0    # How far the supports go below the banks.
RING = 0.25
PIER = 0.8     # Thickness of a masonry pier, shared by the two spans it carries.
MATERIALS = {"wood": WOOD, "stone": STONE, "brick": BRICK}


def _edges(b, xa, xb, top, pal):
    """Road, parapets and string course of a masonry piece."""
    road(b, xa, xb, -W / 2 + 0.3, W / 2 - 0.3, top, pal["road"])
    for y, face in ((-W / 2, -1), (W / 2, 1)):
        parapet(b, xa, xb, y - face * 0.15, top, pal)
        n = max(1, round(xb - xa))
        for k in range(n):
            xk, xl = xa + (xb - xa) * k / n, xa + (xb - xa) * (k + 1) / n
            b.xz([(xk, top(xk) - 0.22), (xl, top(xl) - 0.22), (xl, top(xl) - 0.06), (xk, top(xk) - 0.06)],
                 min(y, y + face * 0.05), max(y, y + face * 0.05), pal["trim"])


def abutment(b, kind):
    """The ramp from the bank (x = -2, Z = 0) up to the deck (x = +2, Z = H)."""
    pal = MATERIALS[kind]

    def top(x):
        return H * smoothstep((x + 2) / 4)

    if kind == "wood":
        planks_x(b, -2, 2, W - 0.2, zf=top, mats=pal["deck"])
        n = 6
        for y in (-W / 2 + 0.3, 0.0, W / 2 - 0.3):
            for i in range(n):
                xa, xb = -2 + 4 * i / n, -2 + 4 * (i + 1) / n
                b.beam((xa, y, top(xa) - 0.17), (xb, y, top(xb) - 0.17), 0.16, 0.2, pal["trim"])
        # Log cribbing under the high end, and its piles in the water.
        for k in range(5):
            z = H - 0.45 - k * 0.32
            if k % 2 == 0:
                log(b, (1.7, -W / 2 - 0.1, z), (1.7, W / 2 + 0.1, z), 0.16, bark=pal["body"], seg=7)
                log(b, (0.3, -W / 2 - 0.1, z - 0.3), (0.3, W / 2 + 0.1, z - 0.3), 0.16, bark=pal["body"], seg=7)
            else:
                for y in (-W / 2 + 0.2, W / 2 - 0.2):
                    log(b, (-0.2, y, z), (2.0, y, z), 0.16, bark=pal["body"], seg=7)
        for y in (-W / 2 + 0.25, W / 2 - 0.25):
            b.cyl((1.75, y, DEEP), (1.75, y, H - 0.3), 0.13, pal["body"], r2=0.11, seg=7)
        for s in (-1, 1):
            pts = [(x, s * (W / 2 - 0.18), top(x)) for x in (-1.5, -0.25, 1.0)]
            rail(b, pts, h=1.0, mat=pal["trim"], rail_mat=pal["body"])
            b.beam((1.0, s * (W / 2 - 0.18), top(1.0) + 0.94), (2.0, s * (W / 2 - 0.18), H + 0.94), 0.08, 0.08,
                   pal["body"])
            b.beam((1.0, s * (W / 2 - 0.18), top(1.0) + 0.5), (2.0, s * (W / 2 - 0.18), H + 0.5), 0.05, 0.06,
                   pal["body"])
    else:
        n = 8
        for i in range(n):
            xa, xb = -2 + 4 * i / n, -2 + 4 * (i + 1) / n
            b.xz([(xa, -1.0), (xb, -1.0), (xb, top(xb)), (xa, top(xa))], -W / 2, W / 2, pal["body"])
        b.box((1.4 + RING / 2, 0, (DEEP + ZS) / 2), (1.2 + RING, W + 0.2, ZS - DEEP), pal["body"])
        b.box((1.4 + RING / 2, 0, ZS - 0.12), (1.3 + RING, W + 0.34, 0.24), pal["trim"])
        b.box((1.4 + RING / 2, 0, DEEP + 0.25), (1.5 + RING, W + 0.5, 0.5), pal["trim"])
        blocks(b, -1.4, 1.8, -W / 2, -0.8, 0.0, pal, face=-1, count=4, seed=1)
        blocks(b, -1.4, 1.8, W / 2, -0.8, 0.0, pal, face=1, count=4, seed=2)
        _edges(b, -2, 2, top, pal)


def span(b, kind, size):
    """A stretch of level deck, `size` meters long (2 or 4)."""
    pal = MATERIALS[kind]
    half = size / 2
    if kind == "wood":
        for y in (-W / 2 + 0.3, 0.0, W / 2 - 0.3):
            b.box((0, y, H - 0.17), (size, 0.16, 0.2), pal["trim"])
        planks_x(b, -half, half, W - 0.2, z=H, mats=pal["deck"])
        for s in (-1, 1):
            y = s * (W / 2 - 0.18)
            xs = (-0.5, 0.5) if size <= 2 else (-1.5, 0.0, 1.5)
            rail(b, [(x, y, H) for x in xs], h=1.0, mat=pal["trim"], rail_mat=pal["body"])
            for x0, x1 in ((-half, xs[0]), (xs[-1], half)):
                b.beam((x0, y, H + 0.94), (x1, y, H + 0.94), 0.08, 0.08, pal["body"])
                b.beam((x0, y, H + 0.5), (x1, y, H + 0.5), 0.05, 0.06, pal["body"])
            # Knee braces from the deck down toward the piers.
            for e in (-1, 1):
                b.beam((e * (half - 0.05), s * (W / 2 - 0.3), H - 0.9), (e * (half - 0.85), s * (W / 2 - 0.3),
                                                                        H - 0.28), 0.1, 0.12, pal["trim"])
    else:
        def top(x):
            return H

        opening = half - PIER / 2 - RING
        rise = min(H - 0.2 - RING - ZS, opening * 1.1)
        arch(b, 0, opening, rise, ZS, top, -W / 2, W / 2, pal, n=7 if size > 2 else 5, ring=RING)
        for e in (-1, 1):
            xa, xb = sorted((e * half, e * (half - PIER / 2)))
            b.xz([(xa, ZS), (xb, ZS), (xb, H), (xa, H)], -W / 2, W / 2, pal["body"])
        _edges(b, -half, half, top, pal)


def support(b, kind):
    """The pier under a joint between two spans, down to Z = DEEP."""
    pal = MATERIALS[kind]
    if kind == "wood":
        for dx in (-0.22, 0.22):
            trestle_bent(b, dx, W, H - 0.45, pal, deep=DEEP, splay=0.3)
        for y in (-W / 2 + 0.05, W / 2 - 0.05):
            b.box((0, y, -0.3), (0.7, 0.1, 0.16), pal["trim"])
        # An ice breaker of two leaning logs on the upstream face.
        b.cyl((0, W / 2 + 1.3, DEEP), (0, W / 2 + 0.2, 0.2), 0.13, pal["body"], seg=7)
    else:
        pier(b, 0, PIER + 2 * RING, -W / 2, W / 2, DEEP, ZS, pal)
        blocks(b, -0.4, 0.4, -W / 2, DEEP + 0.8, ZS - 0.5, pal, face=-1, count=3, seed=3)


def posts(b, kind):
    """A pair of end posts with lanterns, across the way."""
    pal = MATERIALS[kind]
    for s in (-1, 1):
        y = s * (W / 2 - 0.15)
        if kind == "wood":
            b.box((0, y, 1.2), (0.24, 0.24, 2.4), pal["trim"])
            b.box((0, y, 2.44), (0.34, 0.34, 0.1), pal["body"])
            b.xy([(-0.15, y - 0.15), (0.15, y - 0.15), (0.15, y + 0.15), (-0.15, y + 0.15)], 2.49, 2.75,
                 pal["cap"], shrink=0.1)
            b.box((0, y - s * 0.3, 2.1), (0.08, 0.6, 0.08), pal["trim"])
            lantern(b, 0, y - s * 0.5, 2.06)
            b.box((0, y, 0.12), (0.4, 0.4, 0.24), "stone")
        else:
            pilaster(b, 0, y, 0.0, pal, s=0.56, h=1.5)
            b.box((0, y, 2.1), (0.06, 0.06, 0.5), "iron")
            lantern(b, 0, y, 2.6)


def demo(name, kind, spans=(2, 4, 4)):
    b = B()
    total = 8 + sum(spans)
    x = -total / 2
    abutment(b.at(dx=x + 2), kind)
    posts(b.at(dx=x + 0.3), kind)
    x += 4
    for i, size in enumerate(spans):
        span(b.at(dx=x + size / 2), kind, size)
        if i > 0:
            support(b.at(dx=x), kind)
        x += size
    abutment(b.at(dx=x + 2, rz=180), kind)
    posts(b.at(dx=total / 2 - 0.3), kind)
    save(b, name)


def covered_span(b, roof="shingle"):
    """A 4 m span of the wooden kit with walls and a roof: chained, they
    make a covered bridge of any length."""
    span(b, "wood", 4)
    wall_h = H + 2.5
    for s in (-1, 1):
        y = s * (W / 2 - 0.12)
        for x in (-1.9, 0.0, 1.9):
            b.box((x, y, H + 1.25), (0.18, 0.18, 2.5), "timber")
        b.box((0, y, wall_h - 0.1), (4.0, 0.18, 0.2), "timber")
        for xa, xb in ((-1.9, 0.0), (0.0, 1.9)):
            b.beam((xa + 0.1, y, H + 1.1), (xb - 0.1, y, wall_h - 0.2), 0.08, 0.1, "wood")
            b.beam((xa + 0.1, y, wall_h - 0.2), (xb - 0.1, y, H + 1.1), 0.08, 0.1, "wood")
    for x in (-1.9, 1.9):
        b.box((x, 0, wall_h - 0.1), (0.16, W - 0.2, 0.16), "timber")
    roof_x(b, 0, 0, 4.0, W, wall_h, 1.3, 0.35, list(ROOFS[roof]), rows=5)


def covered_demo(name, roof="shingle"):
    b = B()
    abutment(b.at(dx=-8), "wood")
    posts(b.at(dx=-9.7), "wood")
    for i in range(3):
        covered_span(b.at(dx=-4 + i * 4), roof)
        if i > 0:
            support(b.at(dx=-6 + i * 4), "wood")
    abutment(b.at(dx=8, rz=180), "wood")
    posts(b.at(dx=9.7), "wood")
    for e in (-1, 1):   # A gable closes each end of the roof.
        b.yz([(-W / 2, H + 2.5), (W / 2, H + 2.5), (0, H + 3.75)], e * 6 - 0.05, e * 6 + 0.05, "wood_light")
        lantern(b, e * 6.1, 0, H + 2.35)
    save(b, name)


def covered_piece(name, roof):
    b = B()
    covered_span(b, roof)
    save(b, name)


for _roof in ("shingle", "thatch", "tile"):
    MODELS["bridge_kit_wood_covered_%s" % _roof] = (lambda r=_roof: covered_piece("bridge_kit_wood_covered_%s" % r, r))
MODELS["bridge_kit_wood_covered_demo"] = lambda: covered_demo("bridge_kit_wood_covered_demo")


def draw_span(name):
    """A 4 m span of the kit that lifts, to let boats through: it replaces
    any 4 m span and brings its own piles at both ends."""
    b = B()
    pal = WOOD
    hinge, tip, post_h = -1.9, 1.7, H + 3.4
    arm = tip - hinge
    leaf_w = W - 0.7
    yb = leaf_w / 2 - 0.05
    for y in (-1, 1):
        yp = y * (W / 2 - 0.15)
        b.cyl((hinge, yp, DEEP), (hinge, yp, H - 0.3), 0.14, pal["body"], seg=7)
        b.box((hinge, yp, (H + post_h) / 2 - 0.15), (0.24, 0.24, post_h - H + 0.3), pal["trim"])
        b.beam((hinge - 0.1, yp, H + 0.1), (hinge - 0.1, yp * 0.55, H + 2.4), 0.1, 0.12, pal["body"])
        b.cyl((1.9, yp, DEEP), (1.9, yp, H - 0.3), 0.14, pal["body"], seg=7)
    for x in (hinge, 1.9):
        b.box((x, 0, H - 0.3), (0.24, W + 0.1, 0.2), pal["trim"])
    b.cyl((hinge, -W / 2, post_h), (hinge, W / 2, post_h), 0.08, "iron", seg=7)
    b.box((hinge, 0, post_h - 0.9), (0.16, W - 0.3, 0.16), pal["trim"])
    bm = b.bone("beam")
    for y in (-1, 1):
        bm.box(((tip + hinge - 1.7) / 2, y * yb, post_h + 0.02), (tip - hinge + 1.7, 0.16, 0.2), pal["trim"])
    bm.box((hinge - 1.6, 0, post_h + 0.02), (0.18, 2 * yb + 0.3, 0.18), pal["trim"])
    bm.box((hinge - 1.3, 0, post_h - 0.38), (0.8, 2 * yb - 0.2, 0.55), "stone_dark")
    bm.box((tip, 0, post_h + 0.02), (0.14, 2 * yb + 0.3, 0.14), pal["trim"])
    ch = b.bone("chain")
    for y in (-1, 1):
        chain(ch, (tip, y * yb, H + 0.02), (tip, y * yb, post_h - 0.08))
    lf = b.bone("leaf")
    planks_x(lf, hinge + 0.03, 2.0, leaf_w, z=H, step=0.3, thick=0.09)
    for y in (-1, 0, 1):
        lf.box(((hinge + 2.0) / 2, y * (leaf_w / 2 - 0.12), H - 0.17), (2.0 - hinge - 0.1, 0.16, 0.16), pal["trim"])
    for x in (hinge + 0.4, tip):
        lf.box((x, 0, H + 0.012), (0.1, leaf_w + 0.04, 0.03), "iron")
    mech = kit.Mech([("leaf", (hinge, 0, H - 0.05), (hinge, 0, H + 0.5), None),
                     ("beam", (hinge, 0, post_h), (hinge, 0, post_h + 0.5), None),
                     ("chain", (tip, 0, H + 1.5), (tip, 0, H + 2.0), None)])

    def pose(angle):
        a = math.radians(angle)
        return ({"leaf": [(kit.Y, -angle)], "beam": [(kit.Y, -angle)]},
                {"chain": (arm * (math.cos(a) - 1), 0.0, arm * math.sin(a))})

    mech.clip("open", 3.0, lambda t: pose(70 * smoothstep(t)), loops=False)
    mech.clip("close", 3.0, lambda t: pose(70 * (1 - smoothstep(t))), loops=False)
    save(b, name, mech=mech)


MODELS["bridge_kit_wood_draw"] = lambda: draw_span("bridge_kit_wood_draw")


def piece(name, fn, *args):
    def build():
        b = B()
        fn(b, *args)
        save(b, name)
    MODELS[name] = build


for _kind in MATERIALS:
    piece("bridge_kit_%s_abutment" % _kind, abutment, _kind)
    piece("bridge_kit_%s_span2" % _kind, span, _kind, 2)
    piece("bridge_kit_%s_span4" % _kind, span, _kind, 4)
    piece("bridge_kit_%s_pier" % _kind, support, _kind)
    piece("bridge_kit_%s_posts" % _kind, posts, _kind)
    MODELS["bridge_kit_%s_demo" % _kind] = (lambda k=_kind: demo("bridge_kit_%s_demo" % k, k))
MODELS["bridge_kit_stone_demo_long"] = lambda: demo("bridge_kit_stone_demo_long", "stone", (4, 4, 4, 4, 4))
