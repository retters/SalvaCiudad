"""Fox-folk: white plaster between red posts on stone footings, dark tiled
roofs that sweep up at the corners, paper screens, paper lanterns, torii."""

import math

import rparts as p
from rparts import TAU, face

TILES = ("f_tile", "f_tile_light")


def frame(mb, cx, cy, z0, w, d, h, plinth=0.3, spacing=1.4):
    """A plastered storey between red posts, on a stone footing."""
    if plinth:
        mb.box((cx, cy, z0 + plinth / 2), (w + 0.5, d + 0.5, plinth), "f_stone")
        mb.box((cx, cy, z0 + plinth - 0.04), (w + 0.6, d + 0.6, 0.08), "f_stone_dark")
    zb = z0 + plinth
    mb.box((cx, cy, zb + h / 2), (w, d, h), "f_plaster")
    for side in p.SIDES:
        with face(mb, cx, cy, w, d, side, zb) as L:
            n = max(1, round(L / spacing))
            for i in range(n + 1):
                mb.box((-L / 2 + L * i / n, 0, h / 2), (0.2, 0.2, h), "f_red")
            mb.box((0, 0, h - 0.1), (L + 0.2, 0.22, 0.2), "f_red_dark")
            mb.box((0, 0, 0.08), (L + 0.2, 0.16, 0.16), "f_wood")
            mb.box((0, -0.02, h * 0.62), (L, 0.1, 0.1), "f_wood")
    return zb + h


def swept_hip(mb, cx, cy, z, w, d, h, over=0.7, rows=4, tips=0.6, ridge=0.0):
    p.hip_roof(mb, cx, cy, z, w, d, h, TILES, rows=rows, over=over, ridge=ridge, power=1.7, lip=0.05)
    mb.box((cx, cy, z - 0.05), (w + 2 * over - 0.1, d + 2 * over - 0.1, 0.1), "f_red_dark")
    p.eave_tips(mb, cx, cy, z, w, d, "f_tile", over, tips)
    for sx in (-1, 1):                                                          # Red rafter ends under the eaves.
        for sy in (-1, 1):
            p.beam(mb, (cx + sx * w / 2, cy + sy * d / 2, z - 0.12), (cx + sx * (w / 2 + over - 0.1), cy + sy * (d / 2 + over - 0.1), z - 0.02), 0.12, "f_red")
    return z + h


def swept_gable(mb, cx, cy, z, w, d, rise, axis="x", over=0.6):
    """A tiled gable whose slopes sag and whose ridge ends in gold tails."""
    if axis == "y":
        with mb.placed((cx, cy, 0), math.pi / 2):
            return swept_gable(mb, 0, 0, z, d, w, rise, "x", over)
    top = p.gable(mb, cx, cy, z, w, d, rise, TILES, rows=5, over=over, end_over=0.45, fill="f_plaster", thick=0.11, power=1.5, ridge_mat="f_tile")
    for s in (-1, 1):
        x = cx + s * (w / 2 + 0.45)
        p.arc(mb, [(x - s * 0.3, cy, top + 0.2), (x, cy, top + 0.4), (x + s * 0.12, cy, top + 0.75)], 0.1, "gold", 0.3)
        for side in (-1, 1):                                                    # Red barge boards along the sag.
            pts = []
            zr = p.gable_profile(z, d, rise, over, 1.5)
            for i in range(5):
                y = (d / 2 + over) * (1 - i / 4)
                pts.append((x, cy + side * y, zr(y) + 0.02))
            for a, b in zip(pts, pts[1:]):
                p.beam(mb, a, b, 0.14, "f_red")
        mb.cylinder((cx + s * (w / 2 - 0.02), cy, z + rise * 0.45), (cx + s * (w / 2 + 0.06), cy, z + rise * 0.45), 0.22, 0.22, "f_red", segments=8)
    return top


def shoji(mb, x, z, w=1.0, h=1.6, cols=2):
    """A paper screen in a wooden grid (face frame); z is its foot."""
    mb.box((x, -0.03, z + h / 2), (w + 0.12, 0.1, h + 0.12), "f_wood")
    mb.box((x, -0.06, z + h / 2), (w, 0.08, h), "paper")
    for i in range(1, cols):
        mb.box((x - w / 2 + w * i / cols, -0.1, z + h / 2), (0.04, 0.03, h), "f_wood")
    for k in range(1, 4):
        mb.box((x, -0.1, z + h * k / 4), (w, 0.03, 0.035), "f_wood")


def torii(mb, x, y, w=3.0, h=3.4, rot=0.0):
    with mb.placed((x, y, 0), rot):
        for s in (-1, 1):
            mb.cylinder((s * w / 2, 0, 0), (s * w / 2, 0, 0.3), 0.26, 0.22, "f_stone_dark", segments=8)
            mb.cylinder((s * w / 2 * 1.03, 0, 0.3), (s * w / 2 * 0.97, 0, h), 0.17, 0.15, "f_red", segments=8)
        mb.box((0, 0, h * 0.8), (w + 0.5, 0.18, 0.22), "f_red")
        mb.box((0, 0, h * 0.9), (0.2, 0.2, h * 0.2), "f_red")
        for s in (-1, 1):                                                       # The top beam lifts at both ends.
            p.prism_xz(mb, [(0, h), (s * (w / 2 + 0.75), h + 0.26), (s * (w / 2 + 0.8), h + 0.5), (0, h + 0.24)][::s], -0.14, 0.14, "f_red")
            p.prism_xz(mb, [(0, h + 0.24), (s * (w / 2 + 0.8), h + 0.5), (s * (w / 2 + 0.86), h + 0.64), (0, h + 0.36)][::s], -0.2, 0.2, "f_tile")


def stone_lantern(mb, x, y, s=1.0):
    mb.cylinder((x, y, 0), (x, y, 0.16 * s), 0.3 * s, 0.26 * s, "f_stone_dark", segments=6)
    mb.cylinder((x, y, 0.16 * s), (x, y, 0.9 * s), 0.1 * s, 0.1 * s, "f_stone", segments=6)
    mb.cylinder((x, y, 0.9 * s), (x, y, 1.0 * s), 0.26 * s, 0.26 * s, "f_stone_dark", segments=6)
    mb.box((x, y, 1.15 * s), (0.3 * s, 0.3 * s, 0.3 * s), "paper")
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.box((x + sx * 0.15 * s, y + sy * 0.15 * s, 1.15 * s), (0.06 * s, 0.06 * s, 0.3 * s), "f_stone")
    mb.cylinder((x, y, 1.3 * s), (x, y, 1.55 * s), 0.38 * s, 0.06 * s, "f_stone_dark", segments=6)
    mb.sphere((x, y, 1.58 * s), 0.07 * s, "f_stone", segments=5, rings=3)


def maple(mb, x, y, h=2.4, r=0.8):
    p.tree(mb, x, y, h, r, "f_wood_dark", ("f_red", "clay", "aw_yellow"))


def fox_statue(mb, x, y, s=1.0, flip=1):
    """A stone fox sitting on a plinth, looking to the front."""
    mb.box((x, y, 0.3 * s), (0.7 * s, 0.9 * s, 0.6 * s), "f_stone")
    mb.box((x, y, 0.63 * s), (0.8 * s, 1.0 * s, 0.08 * s), "f_stone_dark")
    mb.sphere((x, y + 0.1 * s, 1.0 * s), 0.3 * s, "white", segments=7, rings=5, scale=(0.85, 1.0, 1.2))
    mb.cylinder((x, y - 0.12 * s, 0.67 * s), (x, y - 0.14 * s, 1.25 * s), 0.12 * s, 0.14 * s, "white", segments=6)
    mb.sphere((x, y - 0.18 * s, 1.5 * s), 0.2 * s, "white", segments=7, rings=5)
    mb.cylinder((x, y - 0.3 * s, 1.46 * s), (x, y - 0.55 * s, 1.4 * s), 0.1 * s, 0.03 * s, "white", segments=5)
    for sx in (-1, 1):
        mb.cylinder((x + sx * 0.11 * s, y - 0.12 * s, 1.62 * s), (x + sx * 0.15 * s, y - 0.1 * s, 1.9 * s), 0.08 * s, 0.0, "white", segments=4)
    p.arc(mb, [(x + flip * 0.1 * s, y + 0.35 * s, 0.75 * s), (x + flip * 0.3 * s, y + 0.5 * s, 1.2 * s), (x + flip * 0.2 * s, y + 0.45 * s, 1.75 * s)], 0.14 * s, "white", 0.5)
    mb.box((x, y - 0.25 * s, 1.22 * s), (0.3 * s, 0.06, 0.2 * s), "f_red")        # Its red bib.


def lantern_row(mb, rig, a, b, n=4, sag=0.4, drop=0.1, size=0.8):
    """A cord from a to b with paper lanterns hanging from it."""
    pts = []
    for i in range(n * 2 + 1):
        u = i / (n * 2)
        pts.append((a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u, a[2] + (b[2] - a[2]) * u - sag * math.sin(math.pi * u)))
    for q, r in zip(pts, pts[1:]):
        mb.cylinder(q, r, 0.012, 0.012, "f_wood_dark", segments=4)
    for i in range(1, n * 2, 2):
        p.hang_lantern(mb, rig, pts[i][0], pts[i][1], pts[i][2], drop, "paper", "paper" if (i // 2) % 2 else "f_red", "f_wood_dark", size)


def veranda(mb, cx, cy, z, w, d):
    mb.box((cx, cy, z - 0.05), (w, d, 0.1), "f_wood")
    for i in range(max(2, round(w / 1.2)) + 1):
        x = cx - w / 2 + 0.1 + (w - 0.2) * i / max(2, round(w / 1.2))
        mb.box((x, cy - d / 2 + 0.1, (z - 0.1) / 2), (0.12, 0.12, z - 0.1), "f_wood_dark")


def stepping_stones(mb, x, y0, y1, n=3):
    for k in range(n):
        y = y0 + (y1 - y0) * (k + 0.5) / n
        mb.cylinder((x + 0.12 * (k % 2) - 0.06, y, 0), (x + 0.12 * (k % 2) - 0.06, y, 0.07), 0.3, 0.27, "f_stone", segments=7)


def house(level):
    def build():
        mb = p.begin()
        rig = p.Rig()
        if level == 1:
            w, d, h = 2.8, 2.4, 2.0
            top = frame(mb, 0, 0.3, 0, w, d, h)
            with face(mb, 0, 0.3, w, d, "front", 0.3):
                p.round_door(mb, -0.35, 0.02, 0.72, "f_wood", "f_red", "gold")
                shoji(mb, 0.85, 0.75, 0.6, 0.8, 2)
            swept_hip(mb, 0, 0.3, top, w, d, 1.5, 0.6, 4, 0.5, 0.5)
            mb.box((0, 0.3, top + 1.55), (1.0, 0.24, 0.2), "f_tile")
            p.hang_lantern(mb, rig, 1.6, -1.3, top - 0.02, 0.1, "paper", "paper", "f_red", 0.8)
            stepping_stones(mb, -0.35, -1.9, -1.1, 2)
            stone_lantern(mb, -1.5, -1.5, 0.8)
        elif level == 2:
            w, d, h = 4.8, 3.2, 2.2
            cy = 0.6
            top = frame(mb, 0, cy, 0, w, d, h, 0.4)
            veranda(mb, 0, cy - d / 2 - 0.55, 0.4, w + 0.6, 1.1)
            with face(mb, 0, cy, w, d, "front", 0.4):
                shoji(mb, -1.2, 0.18, 1.6, 1.7, 3)
                p.round_door(mb, 0.75, 0.05, 0.75, "f_wood", "f_red", "gold")
                shoji(mb, 1.95, 0.8, 0.6, 0.8, 2)
            for side in ("left", "right"):
                with face(mb, 0, cy, w, d, side, 0.4):
                    p.round_win(mb, 0, 1.35, 0.36, "f_wood", "paper")
            swept_gable(mb, 0, cy, top, w, d, 1.6, "x", 0.75)
            for sx in (-1, 1):
                mb.cylinder((sx * (w / 2 + 0.2), cy - d / 2 - 1.0, 0.4), (sx * (w / 2 + 0.2), cy - d / 2 - 1.0, top - 0.25), 0.08, 0.08, "f_red", segments=6)
                p.hang_lantern(mb, rig, sx * (w / 2 - 0.5), cy - d / 2 - 0.95, top - 0.35, 0.1, "paper", "paper", "f_red", 0.9)
            stepping_stones(mb, 0.75, -2.5, -1.6, 2)
            stone_lantern(mb, -2.2, -2.0)
            maple(mb, 2.5, -1.9, 2.2, 0.7)
        else:
            w, d, h = 6.8, 4.2, 2.4
            cy = 0.6
            top = frame(mb, 0, cy, 0, w, d, h, 0.45)
            veranda(mb, 0, cy - d / 2 - 0.55, 0.45, w + 0.6, 1.1)
            with face(mb, 0, cy, w, d, "front", 0.45):
                shoji(mb, -2.3, 0.18, 1.7, 1.8, 3)
                p.round_door(mb, 0, 0.05, 0.85, "f_wood", "f_red", "gold")
                shoji(mb, 2.3, 0.18, 1.7, 1.8, 3)
            for side in ("left", "right"):
                with face(mb, 0, cy, w, d, side, 0.45):
                    shoji(mb, 0, 0.6, 1.4, 1.2, 3)
            swept_hip(mb, 0, cy, top, w, d, 1.5, 0.85, 3, 0.7, 3.0)               # The skirt roof between the floors.
            uw, ud, uh = 4.4, 2.8, 2.0
            utop = frame(mb, 0, cy, top + 0.5, uw, ud, uh, 0.0, 1.1)
            with face(mb, 0, cy, uw, ud, "front", top + 0.5):
                for x in (-1.1, 0, 1.1):
                    shoji(mb, x, 0.7, 0.8, 1.0, 2)
                mb.box((0, -0.5, 0.55), (uw + 0.2, 0.08, 0.08), "f_red")           # A balcony rail.
                for k in range(9):
                    mb.box((-uw / 2 + uw * k / 8, -0.5, 0.3), (0.06, 0.06, 0.5), "f_red")
            swept_gable(mb, 0, cy, utop, uw, ud, 1.6, "x", 0.8)
            for sx in (-1, 1):
                mb.cylinder((sx * (w / 2 + 0.2), cy - d / 2 - 1.0, 0.45), (sx * (w / 2 + 0.2), cy - d / 2 - 1.0, top - 0.25), 0.09, 0.09, "f_red", segments=6)
            lantern_row(mb, rig, (-w / 2 - 0.2, cy - d / 2 - 1.0, top - 0.35), (w / 2 + 0.2, cy - d / 2 - 1.0, top - 0.35), 5, 0.3, 0.08, 0.8)
            stepping_stones(mb, 0, -3.0, -1.7, 3)
            stone_lantern(mb, -1.4, -2.6)
            stone_lantern(mb, 1.4, -2.6)
            maple(mb, 3.5, -2.2, 2.6, 0.85)
            maple(mb, -3.6, -2.3, 2.0, 0.65)
        p.finish(mb, "race_fox_house_%d" % level, rig)
    return build


def center():
    """The lantern hall: three swept roofs behind a torii, 12 x 13 m."""
    mb = p.begin()
    rig = p.Rig()
    cy = 1.4
    mb.box((0, cy, 0.3), (11.0, 9.0, 0.6), "f_stone")
    mb.box((0, cy, 0.62), (11.2, 9.2, 0.08), "f_stone_dark")
    p.stairs(mb, 0, cy - 4.5 - 1.4, 0, 0.66, 3.4, 1.4, "f_stone_dark", 0.17)
    z = 0.66
    tiers = ((8.4, 6.4, 2.8, 1.0), (5.8, 4.2, 2.3, 0.9), (3.6, 2.6, 2.0, 0.8))
    for k, (w, d, h, over) in enumerate(tiers):
        top = frame(mb, 0, cy, z, w, d, h, 0.0, 1.4)
        with face(mb, 0, cy, w, d, "front", z):
            if k == 0:
                p.round_door(mb, 0, 0.05, 1.2, "f_wood", "f_red", "gold")
                for sx in (-1, 1):
                    shoji(mb, sx * 2.8, 0.25, 1.7, 2.0, 3)
            else:
                n = 3 if k == 1 else 1
                for i in range(n):
                    shoji(mb, (i - (n - 1) / 2) * 1.6, 0.75, 1.0, 1.1, 2)
                mb.box((0, -0.55, 0.6), (w + 0.6, 0.08, 0.08), "f_red")
                for i in range(int(w / 0.5) + 1):
                    mb.box((-w / 2 - 0.2 + (w + 0.4) * i / int(w / 0.5), -0.55, 0.33), (0.06, 0.06, 0.55), "f_red")
        for side in ("left", "right"):
            with face(mb, 0, cy, w, d, side, z):
                shoji(mb, 0, 0.6, min(2.0, d * 0.45), 1.3, 3)
        if k < 2:
            swept_hip(mb, 0, cy, top, w, d, 1.5, over, 3, 0.8, w * 0.5)
            z = top + 0.55
        else:
            rtop = swept_hip(mb, 0, cy, top, w, d, 2.4, over, 5, 0.8, 0.0)
            mb.cylinder((0, cy, rtop - 0.3), (0, cy, rtop + 2.6), 0.07, 0.03, "gold", segments=6)   # The spire of rings.
            for i in range(5):
                mb.cylinder((0, cy, rtop + 0.3 + 0.38 * i), (0, cy, rtop + 0.4 + 0.38 * i), 0.4 - 0.06 * i, 0.4 - 0.06 * i, "gold", segments=8)
            mb.sphere((0, cy, rtop + 2.65), 0.14, "gold", segments=6, rings=4)
    ty = cy - 4.5 - 3.4
    torii(mb, 0, ty, 4.0, 4.4)
    for sx in (-1, 1):
        fox_statue(mb, sx * 2.7, cy - 4.5 - 1.6, 1.3, sx)
        stone_lantern(mb, sx * 4.6, cy - 4.5 - 0.8, 1.2)
        lantern_row(mb, rig, (sx * 2.0, ty, 3.6), (sx * 4.9, cy - 3.4, 3.3), 3, 0.5, 0.08, 0.9)
        mb.cylinder((sx * 5.0, cy - 3.3, 0.66), (sx * 5.0, cy - 3.3, 3.5), 0.1, 0.09, "f_red", segments=6)
        px = sx * 5.2                                                           # Tall banners on poles with a top arm.
        mb.cylinder((px, ty + 1.6, 0), (px, ty + 1.6, 5.2), 0.06, 0.05, "f_wood_dark", segments=5)
        with mb.placed((px, ty + 1.6, 0), 0):
            p.hang_banner(mb, rig, -sx * 0.35, 0, 5.0, 0.6, 3.4, "f_red", "white", "f_wood_dark", 3)
        maple(mb, sx * 5.0, cy + 4.0, 3.4, 1.1)
    p.finish(mb, "race_fox_center", rig)


def workshop():
    """The potters' shed: a wheel under the eaves and a kiln behind the curtain."""
    mb = p.begin()
    rig = p.Rig()
    w, d, h = 5.0, 3.4, 2.3
    cy = 0.5
    mb.box((0, cy, 0.12), (w + 0.5, d + 0.5, 0.24), "f_stone")
    for sx in (-1, 0, 1):
        for sy in (-1, 1):
            mb.box((sx * w / 2, cy + sy * d / 2, 0.24 + h / 2), (0.2, 0.2, h), "f_red")
    mb.box((0, cy + d / 2, 0.24 + h / 2), (w, 0.12, h), "f_plaster")
    mb.box((-w / 2, cy + 0.6, 0.24 + h / 2), (0.12, d - 1.2, h), "f_plaster")
    for sy in (-1, 1):
        mb.box((0, cy + sy * d / 2, 0.24 + h - 0.1), (w + 0.2, 0.22, 0.2), "f_red_dark")
    top = swept_gable(mb, 0, cy, 0.24 + h, w, d, 1.4, "x", 0.8)
    for k in range(3):                                                          # The door curtain, in three strips.
        name = rig.name("noren")
        x = -1.9 + 0.75 * k
        with mb.bone(name):
            mb.box((x, cy - d / 2 - 0.04, 0.24 + h - 0.75), (0.7, 0.04, 1.1), "noren")
            mb.cylinder((x, cy - d / 2 - 0.07, 0.24 + h - 0.7), (x, cy - d / 2 - 0.03, 0.24 + h - 0.7), 0.18, 0.18, "white", segments=8)
        p.sway(mb, rig, name, (x, cy - d / 2 - 0.04, 0.24 + h - 0.2), 7.0, 3.0, "wave", (1, 0, 0), (x, cy - d / 2 - 0.04, 0.24 + h - 1.3))
    mb.cylinder((1.3, cy - 0.6, 0.24), (1.3, cy - 0.6, 0.7), 0.3, 0.3, "f_wood", segments=8)   # The wheel and the pot on it.
    with mb.bone("wheel"):
        mb.cylinder((1.3, cy - 0.6, 0.7), (1.3, cy - 0.6, 0.78), 0.45, 0.45, "f_stone_dark", segments=10)
        p.lathe(mb, 1.3, cy - 0.6, 0.78, [(0.14, 0), (0.24, 0.16), (0.16, 0.36), (0.2, 0.44)], ("clay",), 8)
        mb.box((1.62, cy - 0.6, 0.8), (0.08, 0.08, 0.05), "f_wood_dark")
    p.spin(mb, rig, "wheel", (1.3, cy - 0.6, 0.7), (0, 0, 1), 2.0, "turn")
    for z in (0.9, 1.5):                                                        # Shelves of finished ware.
        mb.box((0.4, cy + d / 2 - 0.3, 0.24 + z), (2.6, 0.4, 0.06), "f_wood")
        for k in range(6):
            x = -0.7 + 0.44 * k
            p.lathe(mb, x, cy + d / 2 - 0.3, 0.27 + z, [(0.08, 0), (0.15, 0.1), (0.1, 0.26), (0.12, 0.3)], ("clay" if (k + int(z * 2)) % 3 else "white", "noren" if k % 2 else "clay_dark"), 7)
    kx, ky = 3.9, 1.0                                                           # The kiln.
    p.dome(mb, kx, ky, 0, 1.2, 1.7, ("clay", "clay_dark"), 4, 9, 0.0)
    mb.box((kx, ky - 1.1, 0.4), (0.7, 0.3, 0.8), "clay_dark")
    mb.box((kx, ky - 1.22, 0.35), (0.4, 0.1, 0.45), "ember")
    mb.cylinder((kx, ky + 0.5, 1.2), (kx, ky + 0.5, 2.9), 0.28, 0.22, "clay_dark", segments=7)
    p.smoke(mb, rig, kx, ky + 0.5, 2.95, 0.3)
    for k in range(4):
        p.log(mb, (kx + 1.0, ky - 1.6 + 0.0, 0.1 + 0.2 * k), (kx + 1.0, ky - 0.6, 0.1 + 0.2 * k), 0.1)
    p.hang_lantern(mb, rig, w / 2 + 0.55, cy - d / 2 - 0.5, 0.24 + h - 0.1, 0.1, "paper", "paper", "f_red", 0.9)
    stone_lantern(mb, -3.0, -1.6, 0.9)
    p.finish(mb, "race_fox_workshop", rig)


def storehouse():
    """The plaster store: thick white walls, a dark tiled foot, a heavy door."""
    mb = p.begin()
    rig = p.Rig()
    w, d, h = 4.4, 3.6, 3.6
    cy = 0.4
    mb.box((0, cy, 0.2), (w + 0.5, d + 0.5, 0.4), "f_stone")
    p.tbox(mb, 0, cy, 0.4, 0.4 + h, w, d, w - 0.3, d - 0.3, "f_plaster")
    p.tbox(mb, 0, cy, 0.4, 1.6, w + 0.1, d + 0.1, w + 0.02, d + 0.02, "f_tile")          # The tiled foot, with its white joints.
    for side in p.SIDES:
        with face(mb, 0, cy, w, d, side, 0.4) as L:
            for k in range(int(L / 0.6) + 1):
                x = -L / 2 + L * k / int(L / 0.6)
                p.beam(mb, (x, -0.06, 0.05), (min(x + 0.6, L / 2), -0.06, 0.65), 0.05, "white")
                p.beam(mb, (x, -0.06, 0.6), (min(x + 0.6, L / 2), -0.06, 1.2), 0.05, "white")
            mb.box((0, -0.06, 1.22), (L + 0.1, 0.1, 0.1), "white")
    with face(mb, 0, cy, w, d, "front", 0.4):
        mb.box((0, -0.1, 1.05), (1.9, 0.24, 2.3), "f_plaster_dark")
        for sx in (-1, 1):
            name = "door_l" if sx < 0 else "door_r"
            with mb.bone(name):
                mb.box((sx * 0.42, -0.26, 1.0), (0.8, 0.14, 2.0), "f_wood_dark")
                for zz in (0.4, 1.0, 1.6):
                    mb.box((sx * 0.42, -0.34, zz), (0.8, 0.03, 0.09), "gold")
                mb.sphere((sx * 0.12, -0.36, 1.0), 0.07, "gold", segments=5, rings=3)
            p.hinge(mb, rig, name, (sx * 0.84, -0.26, 1.0), (0, 0, 1), -sx * 100.0, 2.5)
        mb.box((0, -0.06, 2.9), (0.7, 0.12, 0.5), "f_wood_dark")                  # A small barred window, and the crest.
        for k in range(3):
            mb.box((-0.2 + 0.2 * k, -0.13, 2.9), (0.05, 0.04, 0.5), "gold")
    top = swept_gable(mb, 0, cy, 0.4 + h, w - 0.3, d - 0.3, 1.5, "x", 0.6)
    for s in (-1, 1):
        mb.cylinder((s * (w / 2 - 0.14), cy, 0.4 + h + 0.4), (s * (w / 2 - 0.08), cy, 0.4 + h + 0.4), 0.3, 0.3, "f_red", segments=8)
    for k, (x, z) in enumerate(((2.9, 0.3), (2.9 + 0.0, 0.3), (3.5, 0.3), (3.2, 0.82))):    # Rice bales.
        y = -1.2 + (0.0 if k != 1 else 0.9)
        mb.cylinder((x, y - 0.4, z), (x, y + 0.4, z), 0.3, 0.3, "hay", segments=8)
        for yy in (-0.25, 0.25):
            mb.cylinder((x, y + yy - 0.03, z), (x, y + yy + 0.03, z), 0.31, 0.31, "hay_dark", segments=8)
    p.barrel(mb, -2.9, -1.3, 0, 0.9, 0.34)
    p.barrel(mb, -3.0, -0.5, 0, 0.9, 0.34)
    p.hang_lantern(mb, rig, -1.4, cy - d / 2 - 0.5, 0.4 + h - 0.3, 0.1, "paper", "paper", "f_red", 0.9)
    p.hang_lantern(mb, rig, 1.4, cy - d / 2 - 0.5, 0.4 + h - 0.3, 0.1, "paper", "f_red", "f_wood_dark", 0.9)
    p.finish(mb, "race_fox_storehouse", rig)


def tea_house():
    """The tea house: a pavilion on a deck in its garden, behind a torii, 8 x 8 m."""
    mb = p.begin()
    rig = p.Rig()
    w, d, h = 3.6, 3.0, 2.0
    cy = 1.3
    zd = 0.55
    mb.box((0, cy, zd - 0.06), (w + 2.0, d + 2.0, 0.12), "f_wood")                # The deck on its posts.
    for sx in (-1, 0, 1):
        for sy in (-1, 1):
            mb.box((sx * (w / 2 + 0.85), cy + sy * (d / 2 + 0.85), (zd - 0.12) / 2), (0.14, 0.14, zd - 0.12), "f_wood_dark")
    top = frame(mb, 0, cy, zd, w, d, h, 0.0, 1.2)
    with face(mb, 0, cy, w, d, "front", zd):
        mb.box((0, -0.04, 0.85), (1.5, 0.12, 1.7), "dark")                        # Open screens: the room is seen from the garden.
        shoji(mb, -1.25, 0.1, 0.8, 1.6, 2)
        shoji(mb, 1.25, 0.1, 0.8, 1.6, 2)
    for side in ("left", "right", "back"):
        with face(mb, 0, cy, w, d, side, zd):
            p.round_win(mb, 0, 1.1, 0.42, "f_wood", "paper")
    rtop = swept_hip(mb, 0, cy, top, w, d, 1.7, 1.1, 4, 0.7, 0.6)
    mb.box((0, cy, rtop + 0.06), (1.1, 0.24, 0.2), "f_tile")
    mb.sphere((0, cy, rtop + 0.3), 0.14, "gold", segments=6, rings=4)
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.cylinder((sx * (w / 2 + 0.8), cy + sy * (d / 2 + 0.8), zd), (sx * (w / 2 + 0.8), cy + sy * (d / 2 + 0.8), top - 0.1), 0.07, 0.07, "f_red", segments=6)
    ty = cy - d / 2 - 0.55                                                       # The low table with the pot and cups.
    mb.box((0, ty, zd + 0.3), (1.1, 0.6, 0.06), "f_wood_dark")
    for sx in (-0.45, 0.45):
        mb.box((sx, ty, zd + 0.14), (0.08, 0.5, 0.28), "f_wood_dark")
    mb.sphere((0.1, ty, zd + 0.45), 0.14, "f_stone_dark", segments=7, rings=5, scale=(1, 1, 0.8))
    mb.cylinder((0.22, ty, zd + 0.46), (0.36, ty, zd + 0.54), 0.03, 0.02, "f_stone_dark", segments=4)
    for sx in (-0.35, -0.15):
        mb.cylinder((sx, ty + 0.1, zd + 0.33), (sx, ty + 0.1, zd + 0.42), 0.04, 0.055, "white", segments=6)
    p.smoke(mb, rig, 0.1, ty, zd + 0.6, 0.1, "white", 3)
    for sx in (-0.8, 0.8):
        mb.box((sx, ty, zd + 0.04), (0.45, 0.45, 0.08), "f_red")                   # Cushions.
    p.stairs(mb, 0, cy - d / 2 - 1.5, 0, zd - 0.12, 1.2, 0.5, "f_stone", 0.2)
    torii(mb, 0, -3.3, 2.4, 3.0)
    stepping_stones(mb, 0, -3.0, -1.5, 4)
    p.pond(mb, 2.7, -1.6, 1.2, 1.5, 10, "f_stone", "water")                      # The garden pond and the water basin.
    p.lily(mb, 2.5, -1.9, 0.13, 0.26, True, 0.5)
    p.lily(mb, 3.0, -1.2, 0.13, 0.22, False, 2.0)
    mb.cylinder((-2.6, -1.2, 0), (-2.6, -1.2, 0.45), 0.36, 0.3, "f_stone_dark", segments=7)
    mb.cylinder((-2.6, -1.2, 0.4), (-2.6, -1.2, 0.47), 0.24, 0.24, "water", segments=7)
    p.beam(mb, (-3.1, -1.2, 0), (-3.1, -1.2, 0.9), 0.07, "tea")
    p.beam(mb, (-3.15, -1.2, 0.8), (-2.65, -1.2, 0.62), 0.06, "tea")
    for k in range(5):                                                          # A row of tea bushes.
        mb.sphere((-3.4 + 0.0 * k, 0.2 + 0.7 * k, 0.3), 0.42, "tea" if k % 2 else "leaf_dark", segments=6, rings=4, scale=(1, 1, 0.75))
    stone_lantern(mb, -1.5, -2.6, 1.0)
    stone_lantern(mb, 1.4, -3.4, 0.9)
    maple(mb, 3.2, 1.6, 3.0, 0.95)
    lantern_row(mb, rig, (-1.2, -3.3, 2.5), (-w / 2 - 0.8, cy - d / 2 - 0.8, top - 0.2), 2, 0.3, 0.08, 0.8)
    lantern_row(mb, rig, (1.2, -3.3, 2.5), (w / 2 + 0.8, cy - d / 2 - 0.8, top - 0.2), 2, 0.3, 0.08, 0.8)
    p.finish(mb, "race_fox_tea_house", rig)


def tower():
    """A fire-watch tower: red posts, a bell under a swept roof."""
    mb = p.begin()
    rig = p.Rig()
    mb.box((0, 0, 0.2), (3.0, 3.0, 0.4), "f_stone")
    zf = 5.6
    for sx in (-1, 1):
        for sy in (-1, 1):
            p.beam(mb, (sx * 1.2, sy * 1.2, 0.4), (sx * 0.85, sy * 0.85, zf + 2.0), 0.24, "f_red")
    for z in (1.6, 3.2, 4.6):                                                   # Ties and crossed braces.
        k = 1.2 - 0.35 * (z - 0.4) / (zf + 1.6)
        for a, b in (((-k, -k), (k, -k)), ((k, -k), (k, k)), ((k, k), (-k, k)), ((-k, k), (-k, -k))):
            p.beam(mb, (a[0], a[1], z), (b[0], b[1], z), 0.14, "f_red_dark")
            if z < 4.0:
                p.beam(mb, (a[0], a[1], z), (b[0], b[1], z + 1.5), 0.08, "f_wood")
    mb.box((0, 0, zf), (2.9, 2.9, 0.14), "f_wood")                               # The watch floor and its rail.
    for sx in (-1, 1):
        mb.box((sx * 1.4, 0, zf + 0.8), (0.08, 2.9, 0.08), "f_red")
        mb.box((0, sx * 1.4, zf + 0.8), (2.9, 0.08, 0.08), "f_red")
        for k in range(7):
            mb.box((sx * 1.4, -1.35 + 0.45 * k, zf + 0.45), (0.06, 0.06, 0.7), "f_red")
            mb.box((-1.35 + 0.45 * k, sx * 1.4, zf + 0.45), (0.06, 0.06, 0.7), "f_red")
    top = swept_hip(mb, 0, 0, zf + 2.0, 1.9, 1.9, 1.5, 0.9, 4, 0.6, 0.0)
    mb.cylinder((0, 0, top - 0.2), (0, 0, top + 0.7), 0.06, 0.0, "gold", segments=5)
    mb.sphere((0, 0, top + 0.1), 0.12, "gold", segments=6, rings=4)
    mb.box((0, 0, zf + 1.9), (1.8, 0.14, 0.14), "f_red_dark")
    with mb.bone("bell"):                                                       # The alarm bell.
        p.lathe(mb, 0, 0, zf + 1.0, [(0.4, 0), (0.36, 0.3), (0.24, 0.6), (0.08, 0.75)], ("bronze", "bronze", "copper"), 8)
        mb.cylinder((0, 0, zf + 1.75), (0, 0, zf + 1.9), 0.03, 0.03, "iron", segments=4)
        mb.sphere((0, 0, zf + 0.98), 0.09, "iron", segments=5, rings=3)
    p.sway(mb, rig, "bell", (0, 0, zf + 1.9), 16.0, 1.6, "ring", (1, 0, 0), (0, 0, zf + 1.0))
    for k in range(17):                                                         # The ladder.
        mb.box((0, -1.55 - 0.02 * (16 - k), 0.5 + 0.31 * k), (0.55, 0.06, 0.05), "f_wood")
    for sx in (-1, 1):
        p.beam(mb, (sx * 0.28, -1.9, 0.4), (sx * 0.28, -1.5, zf + 0.4), 0.07, "f_wood_dark")
        p.hang_lantern(mb, rig, sx * 1.75, -1.75, zf + 1.95, 0.1, "paper", "paper" if sx < 0 else "f_red", "f_wood_dark", 0.9)
    stone_lantern(mb, 1.9, -1.6, 0.9)
    p.finish(mb, "race_fox_tower", rig)


MODELS = {
    "race_fox_tea_house": tea_house, "race_fox_tower": tower,
    "race_fox_house_1": house(1), "race_fox_house_2": house(2), "race_fox_house_3": house(3),
    "race_fox_center": center, "race_fox_workshop": workshop, "race_fox_storehouse": storehouse,
}
