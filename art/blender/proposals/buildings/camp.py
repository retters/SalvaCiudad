"""Tents: a knight's pavilion, a scout camp tent with its banner (as in the
reference picture) and the big top of a traveling fair."""

import math

import parts as P
from parts import game, TAU


def cone_panels(mb, x, y, z, r, h, mats, n=12, r_top=0.06, skip=(), turn=0.0):
    """A cone or frustum of cloth in n panels of alternating colors; panel
    0 is centered on the front (-Y)."""
    for i in range(n):
        if i in skip:
            continue
        a0 = -math.pi / 2 - math.pi / n + TAU * i / n + turn
        a1 = a0 + TAU / n
        pts = [(x + r * math.cos(a0), y + r * math.sin(a0)), (x + r * math.cos(a1), y + r * math.sin(a1)),
               (x + r_top * math.cos(a1), y + r_top * math.sin(a1)), (x + r_top * math.cos(a0), y + r_top * math.sin(a0))]
        verts = mb.prism(pts, z, z + 0.05, mats[i % len(mats)])
        for v in verts:
            if math.hypot(v.co.x - x, v.co.y - y) < (r + r_top) / 2:
                v.co.z += h


def wall_panels(mb, x, y, z, r, h, mats, n=12, skip=(), thick=0.05):
    rr = r * math.cos(math.pi / n)
    width = 2 * r * math.sin(math.pi / n) + 0.02
    for i in range(n):
        if i in skip:
            continue
        a = -math.pi / 2 + TAU * i / n
        mb.box((x + rr * math.cos(a), y + rr * math.sin(a), z + h / 2), (thick, width, h), mats[i % len(mats)], rotation_z=a)


def guy_ropes(mb, x, y, z, r, n=6, reach=1.1, turn=0.3):
    for i in range(n):
        a = TAU * i / n + turn
        c, s = math.cos(a), math.sin(a)
        P.beam(mb, (x + r * c, y + r * s, z), (x + (r + reach) * c, y + (r + reach) * s, 0.05), 0.025, "rope")
        mb.cylinder((x + (r + reach) * c, y + (r + reach) * s, 0), (x + (r + reach + 0.1) * c, y + (r + reach + 0.1) * s, 0.3),
                    0.04, 0.03, "timber", segments=5)


def pavilion(mb, rig, mats=("stripe_a", "stripe_b")):
    x, y, r, wh, n = 0.0, 0.3, 2.3, 1.9, 12
    mb.cylinder((x, y, 0), (x, y, wh - 0.05), r - 0.25, r - 0.25, "charcoal", segments=12)
    wall_panels(mb, x, y, 0, r, wh, mats, n, skip=(0,))
    cone_panels(mb, x, y, wh, r + 0.2, 2.9, mats, n, r_top=0.08)
    wall_panels(mb, x, y, wh - 0.32, r + 0.2, 0.34, mats[::-1], n)
    mb.cylinder((x, y, wh + 2.7), (x, y, wh + 3.2), 0.12, 0.05, "gold", segments=6)
    P.flag(mb, rig, x, y, wh + 3.0, pole=1.5, length=1.1, mat="banner")
    # The door flaps tied back, a carpet and the knight's shield and lance.
    fy = y - r * math.cos(math.pi / n)
    for s in (-1, 1):
        P.prism_xz(mb, [(s * 0.6, wh), (s * 0.62, 0.0), (s * 0.95, 0.0)][::s], fy - 0.08, fy - 0.03, mats[1])
        mb.box((s * 0.7, fy - 0.06, 0.9), (0.2, 0.06, 0.06), "rope")
    mb.box((x, fy - 0.5, 0.02), (1.3, 1.6, 0.04), "cloth_red")
    mb.box((x, fy - 0.5, 0.025), (1.0, 1.3, 0.04), "banner2")
    guy_ropes(mb, x, y, wh, r + 0.2)
    sx, sy = 2.2, -2.3
    for s in (-0.25, 0.25):
        P.beam(mb, (sx + s, sy + 0.3, 0), (sx, sy, 1.3), 0.04, "timber")
    P.beam(mb, (sx, sy - 0.35, 0), (sx, sy, 1.3), 0.04, "timber")
    P.prism_xz(mb, [(sx - 0.3, 1.2), (sx - 0.3, 0.75), (sx, 0.45), (sx + 0.3, 0.75), (sx + 0.3, 1.2)][::-1], sy - 0.14,
               sy - 0.08, "banner")
    mb.box((sx, sy - 0.15, 0.85), (0.12, 0.03, 0.5), "banner2")
    mb.cylinder((sx + 0.5, sy + 0.2, 0), (sx + 0.42, sy + 0.1, 3.0), 0.035, 0.03, "wood", segments=5)
    mb.cylinder((sx + 0.42, sy + 0.1, 3.0), (sx + 0.41, sy + 0.09, 3.35), 0.06, 0.0, "iron", segments=5)
    # A camp table with a jug, and a chest.
    P.table(mb, -2.2, -2.3, w=1.1, d=0.7, benches=False)
    mb.box((-2.3, -1.2, 0.25), (0.8, 0.5, 0.5), "wood")
    mb.box((-2.3, -1.2, 0.52), (0.84, 0.54, 0.08), "iron")


def wolf_banner(mb, rig, x, y, h=4.2, w=1.1, length=2.2, mat="banner", emblem="white"):
    """A tall pole with a crossbar and a hanging banner with a wolf's head,
    which sways (clip `wave`). Faces -Y."""
    mb.cylinder((x, y, 0), (x, y, h), 0.07, 0.05, "timber", segments=6)
    mb.box((x, y - 0.05, h - 0.3), (w + 0.4, 0.07, 0.07), "timber")
    for s in (-1, 1):
        mb.sphere((x + s * (w / 2 + 0.2), y - 0.05, h - 0.3), 0.07, "gold", segments=5, rings=3)
    mb.cylinder((x, y, h), (x, y, h + 0.3), 0.06, 0.0, "gold", segments=5)
    zt = h - 0.33
    half = length / 2
    names = []
    for k in range(2):
        name = rig.name("banner") + "_%d" % k
        z0, z1 = zt - k * half, zt - (k + 1) * half
        with mb.bone(name):
            if k == 0:
                mb.box((x, y - 0.1, (z0 + z1) / 2), (w, 0.04, half), mat)
                c = (z0 + z1) / 2 - 0.1
                P.prism_xz(mb, [(x - 0.26, c + 0.12), (x, c - 0.3), (x + 0.26, c + 0.12), (x + 0.18, c + 0.34),
                                (x - 0.18, c + 0.34)], y - 0.135, y - 0.1, emblem)
                for s in (-1, 1):
                    P.prism_xz(mb, [(x + s * 0.26, c + 0.3), (x + s * 0.1, c + 0.34), (x + s * 0.22, c + 0.56)][::s],
                               y - 0.135, y - 0.1, emblem)
            else:
                P.prism_xz(mb, [(x - w / 2, z0), (x - w / 2, z1 + 0.3), (x - w / 4, z1), (x, z1 + 0.3), (x + w / 4, z1),
                                (x + w / 2, z1 + 0.3), (x + w / 2, z0)][::-1], y - 0.12, y - 0.08, mat)
        head = mb.world((x, y - 0.1, z0))
        rig.bone(name, head, mb.world((x, y - 0.1, z1)), names[-1] if names else None)
        names.append(name)
    axis = mb.world_dir((1, 0, 0))
    rig.add("wave", 2.4, lambda t: {names[0]: [(axis, 5 * math.sin(TAU * t))],
                                    names[1]: [(axis, 9 * math.sin(TAU * t - 0.9))]})


def camp_tent(mb, rig, cloth=("canvas", "canvas_dark")):
    w, y0, y1, h = 3.4, -1.0, 2.6, 2.4
    cx = -0.6
    P.prism_xz(mb, [(cx - w / 2, 0), (cx + w / 2, 0), (cx, h)], y0, y1, cloth[0])
    P.prism_xz(mb, [(cx - w / 2 + 0.5, 0), (cx + w / 2 - 0.5, 0), (cx, h - 0.7)], y0 - 0.02, y0 + 0.05, "charcoal")
    for s in (-1, 1):
        P.prism_xz(mb, [(cx + s * (w / 2 - 0.05), 0.0), (cx + s * (w / 2 - 0.5), 0.0), (cx + s * 0.25, h - 0.45)][::s],
                   y0 - 0.07, y0 - 0.02, cloth[1])
        P.beam(mb, (cx + s * (w / 2 + 0.15), y0 - 0.12, 0), (cx - s * 0.12, y0 - 0.12, h + 0.35), 0.09, "timber")
        P.beam(mb, (cx + s * (w / 2 + 0.15), y1 + 0.1, 0), (cx - s * 0.12, y1 + 0.1, h + 0.35), 0.09, "timber")
        for yy in (y0 + 0.5, (y0 + y1) / 2, y1 - 0.5):
            P.beam(mb, (cx + s * (w / 2 - 0.2), yy, 0.3), (cx + s * (w / 2 + 0.7), yy, 0.0), 0.02, "rope")
        mb.box((cx + s * (w / 4), (y0 + y1) / 2, h / 2 + 0.03), (0.04, y1 - y0, 0.05), cloth[1])
    mb.cylinder((cx, y0 - 0.5, h + 0.12), (cx, y1 + 0.4, h + 0.12), 0.06, 0.06, "timber", segments=6)
    # Supplies by the entrance: crates, a barrel, a bedroll, a cooking tripod.
    game.crate(mb, cx + 1.3, y0 - 0.9, s=0.6)
    game.crate(mb, cx + 1.9, y0 - 0.7, s=0.5, top="hide")
    game.crate(mb, cx + 1.45, y0 - 0.85, s=0.45, z=0.6)
    game.barrel(mb, cx + 2.3, y0 + 0.1, h=0.8, r=0.3)
    mb.cylinder((cx - 0.6, y0 - 0.5, 0.16), (cx + 0.3, y0 - 0.5, 0.16), 0.16, 0.16, "cloth_green", segments=8)
    for xx in (cx - 0.35, cx + 0.05):
        mb.cylinder((xx - 0.03, y0 - 0.5, 0.16), (xx + 0.03, y0 - 0.5, 0.16), 0.17, 0.17, "hide", segments=8)
    tx, ty = 2.2, -2.2
    for i in range(3):
        a = TAU * i / 3 + 0.5
        P.beam(mb, (tx + 0.55 * math.cos(a), ty + 0.55 * math.sin(a), 0), (tx, ty, 1.3), 0.035, "iron")
    mb.box((tx, ty, 0.95), (0.02, 0.02, 0.6), "iron")
    mb.sphere((tx, ty, 0.55), 0.22, "charcoal", segments=6, rings=4, scale=(1, 1, 0.8))
    for i in range(6):
        a = TAU * i / 6
        mb.sphere((tx + 0.45 * math.cos(a), ty + 0.45 * math.sin(a), 0.08), 0.13, "rock" if i % 2 else "rock_dark",
                  segments=5, rings=3, scale=(1, 1, 0.7))
    mb.cylinder((tx, ty, 0.05), (tx, ty, 0.3), 0.2, 0.0, "ember", segments=5)
    # The banner of the company.
    wolf_banner(mb, rig, cx - w / 2 - 0.8, y0 - 1.0)


def big_top(mb, rig, mats=("stripe_a", "stripe_b"), wagon=True):
    x, y, r, wh, n = -0.6, 0.6, 4.0, 2.4, 16
    mb.cylinder((x, y, 0), (x, y, wh - 0.05), r - 0.25, r - 0.25, "charcoal", segments=16)
    wall_panels(mb, x, y, 0, r, wh, mats, n, skip=(0,))
    cone_panels(mb, x, y, wh, r + 0.25, 2.6, mats, n, r_top=1.5)
    wall_panels(mb, x, y, wh - 0.36, r + 0.25, 0.38, mats[::-1], n)
    wall_panels(mb, x, y, wh + 2.6, 1.5, 0.5, mats[::-1], n)
    cone_panels(mb, x, y, wh + 3.1, 1.75, 1.7, mats, n, r_top=0.08)
    P.flag(mb, rig, x, y, wh + 4.6, pole=1.8, length=1.4, mat="banner", pennant=False, height=0.7)
    guy_ropes(mb, x, y, wh, r + 0.25, n=8, reach=1.0, turn=0.9)
    # The entrance: a striped awning on two poles with a sign board.
    fy = y - r * math.cos(math.pi / n)
    for s in (-1, 1):
        mb.cylinder((x + s * 1.2, fy - 1.6, 0), (x + s * 1.2, fy - 1.6, 2.6), 0.07, 0.06, "timber", segments=6)
        mb.sphere((x + s * 1.2, fy - 1.6, 2.65), 0.1, "gold", segments=5, rings=3)
        P.prism_xz(mb, [(x + s * 0.75, wh - 0.1), (x + s * 0.8, 0.0), (x + s * 1.15, 0.0)][::s], fy - 0.1, fy - 0.04, mats[1])
    for i in range(4):
        x0 = x - 1.3 + i * 0.65
        game.sloped_slab(mb, x0, x0 + 0.66, fy - 1.8, fy + 0.1, 2.35, 2.9, 0.05, mats[i % 2])
    mb.box((x, fy - 1.82, 2.75), (2.0, 0.08, 0.5), "banner2")
    mb.box((x, fy - 1.87, 2.75), (1.6, 0.04, 0.26), "banner")
    mb.box((x, fy - 0.9, 0.02), (1.6, 2.2, 0.04), "cloth_red")
    # Strings of pennants from the roof to four masts.
    for i, (px, py) in enumerate(((x - 4.6, y - 3.6), (x + 4.6, y - 3.6), (x - 4.4, y + 3.8), (x + 4.4, y + 3.8))):
        if abs(px) > 5.7:
            px = math.copysign(5.7, px)
        mb.cylinder((px, py, 0), (px, py, 3.4), 0.06, 0.05, "timber", segments=6)
        ax, ay, az = x + (r * 0.55) * (1 if px > x else -1), y + (r * 0.55) * (1 if py > y else -1), wh + 1.4
        P.beam(mb, (px, py, 3.3), (ax, ay, az), 0.02, "rope")
        for k in range(1, 6):
            t = k / 6
            bx, by, bz = px + (ax - px) * t, py + (ay - py) * t, 3.3 + (az - 3.3) * t
            with mb.placed((bx, by, 0), math.atan2(ay - py, ax - px)):
                P.prism_xz(mb, [(-0.14, bz), (0.14, bz), (0, bz - 0.34)], -0.015, 0.015,
                           ("stripe_a", "banner2", "banner", "cloth_green")[(k + i) % 4])
    # A ticket booth.
    bx, by = x + 3.0, fy - 1.6
    mb.box((bx, by, 0.55), (1.2, 1.0, 1.1), mats[0])
    for s in (-1, 1):
        mb.box((bx + s * 0.55, by - 0.45, 1.1), (0.08, 0.08, 2.2), "timber")
        mb.box((bx + s * 0.55, by + 0.45, 1.1), (0.08, 0.08, 2.2), "timber")
    mb.box((bx, by - 0.5, 1.13), (1.3, 0.3, 0.06), "wood")
    P.pyramid_roof(mb, bx, by, 2.2, 1.2, 1.0, 0.7, mats, rows=2, overhang=0.25, finial="gold")
    if wagon:
        with mb.placed((x + 4.3, y + 1.2, 0), math.pi / 2):
            mb.box((0, 0, 1.35), (3.0, 1.5, 1.5), "stripe_a")
            for i in range(5):
                mb.box((-1.2 + i * 0.6, -0.76, 1.35), (0.06, 0.04, 1.5), "banner2")
            mb.box((0, 0, 0.55), (3.2, 1.6, 0.14), "timber")
            arc = mb.prism([(-1.6, -0.85), (1.6, -0.85), (1.6, 0.85), (-1.6, 0.85)], 2.1, 2.5, "banner")
            for v in arc:
                if v.co.z > 2.3:
                    v.co.y *= 0.55
            with mb.placed((0, -0.75, 0)):
                P.window(mb, 0.5, 1.5, w=0.5, h=0.5, shutter=None, frame="banner2")
            for sx in (-1.0, 1.0):
                for sy in (-1, 1):
                    mb.cylinder((sx, sy * 0.82, 0.5), (sx, sy * 0.92, 0.5), 0.5, 0.5, "wood", segments=10)
                    mb.cylinder((sx, sy * 0.8, 0.5), (sx, sy * 0.95, 0.5), 0.12, 0.12, "banner2", segments=6)
            P.beam(mb, (1.6, 0, 0.6), (2.9, 0, 0.35), 0.08, "timber")
            mb.box((-1.75, 0, 0.3), (0.4, 0.8, 0.08), "timber")
            mb.box((-1.6, 0, 1.3), (0.06, 0.7, 1.4), "door")
    game.barrel(mb, x - 3.6, fy - 1.2, h=0.8, r=0.3)
    game.crate(mb, x - 4.3, fy - 0.9, s=0.6)


def make(name, fn, colors, **kw):
    def build():
        mb = P.begin()
        rig = P.Rig()
        fn(mb, rig, **kw)
        P.finish(mb, name, colors, rig)
    return build


BLUE = dict(stripe_a=0x2F4FA6, stripe_b=0xE2C24A, banner=0xB03A30, banner2=0xF0E8D0)
GREEN = dict(stripe_a=0x3E7A46, stripe_b=0xEFE6D0, banner=0x3E7A46)

MODELS = {
    "bld_pavilion_red": make("bld_pavilion_red", pavilion, P.BASE),
    "bld_pavilion_blue": make("bld_pavilion_blue", pavilion, P.palette(**BLUE)),
    "bld_pavilion_green": make("bld_pavilion_green", pavilion, P.palette(**GREEN)),
    "bld_camp_tent": make("bld_camp_tent", camp_tent, P.BASE),
    "bld_camp_tent_hide": make("bld_camp_tent_hide", camp_tent, P.palette(banner=0x8E1C24), cloth=("hide", "hide_dark")),
    "bld_fair_tent_red": make("bld_fair_tent_red", big_top, P.BASE),
    "bld_fair_tent_blue": make("bld_fair_tent_blue", big_top, P.palette(**BLUE)),
    "bld_market_tent_green": make("bld_market_tent_green", big_top, P.palette(**GREEN), wagon=False),
}
