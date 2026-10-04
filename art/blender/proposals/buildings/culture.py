"""Culture and care: an infirmary, a monastery with its cloister, a round
timber theater, a caravanserai and an observatory."""

import math
import random

import parts as P
import castles
from camp import cone_panels
from civic import storey, round_window, railing_ring
from extra import bell_tower, rose_window
from mills import sack, hand_cart
from parts import game, TAU

ROOF = ("roof", "roof_dark")


def arcade(mb, L, n, h=3.0, d=0.5, open_h=2.4, z0=0.0, mat="wall"):
    """A row of n arches along local X centered on 0 (wall face frame: the
    arcade stands on the plane y = 0)."""
    w = L / n
    for i in range(n):
        with mb.placed((-L / 2 + (i + 0.5) * w, 0, 0)):
            P.arch_wall(mb, w, d, h, w - 0.6, open_h, mat=mat, inner="wall_dark", z0=z0)
            P.arch_trim(mb, 0, -d / 2, z0, w - 0.6, open_h, t=0.14, depth=0.06)


def herb_beds(mb, x, y, nx=2, ny=2, w=1.3, d=0.8):
    kinds = ("leaves", "flowers", "leaf_light", "flowers_y", "magic")
    for i in range(nx):
        for j in range(ny):
            bx, by = x + i * (w + 0.4), y + j * (d + 0.4)
            mb.box((bx, by, 0.1), (w, d, 0.2), "wall_dark")
            mb.box((bx, by, 0.17), (w - 0.16, d - 0.16, 0.1), "soil")
            for k in range(3):
                mb.sphere((bx - w * 0.3 + k * w * 0.3, by, 0.3), 0.14, kinds[(i * 2 + j + k) % len(kinds)], segments=5, rings=3)


def infirmary(mb, rig, seed=110):
    rnd = random.Random(seed)
    cx, cy, w, d, h = 0.0, 1.6, 10.0, 4.6, 4.2
    storey(mb, rnd, "stone", cx, cy, 0, w, d, h)
    top = P.gable_roof(mb, cx, cy, w, d, h, 2.8, ROOF, rows=7, overhang=0.4, gable="wall", barge="wall_light")
    with P.face(mb, cx, cy, w, d, "back") as L:
        for i in range(5):
            P.arched_window(mb, -L / 2 + (i + 0.5) * L / 5, 1.4, w=0.7, h=1.8)
    for side in ("left", "right"):
        with P.face(mb, cx, cy, w, d, side):
            P.arched_window(mb, 0, 1.4, w=1.0, h=2.0)
            round_w = 0.5
            mb.cylinder((0, 0.03, h + 1.0), (0, -0.1, h + 1.0), round_w + 0.14, round_w + 0.14, "trim", segments=10)
            mb.cylinder((0, 0.0, h + 1.0), (0, -0.13, h + 1.0), round_w, round_w, "window", segments=10)
    # The loggia along the front, where the sick take the air.
    ly = cy - d / 2 - 1.5
    with mb.placed((cx, ly - 0.25, 0)):
        arcade(mb, w, 5, h=3.0, open_h=2.5)
    for sx in (-1, 1):
        mb.box((cx + sx * (w / 2 - 0.25), ly + 0.6, 1.5), (0.5, 1.8, 3.0), "wall")
    P.prism_yz(mb, [(ly - 0.7, 3.0), (cy - d / 2, 3.9), (cy - d / 2, 4.02), (ly - 0.7, 3.12)], cx - w / 2 - 0.2, cx + w / 2 + 0.2, "roof_dark")
    mb.box((cx, ly + 0.5, 0.06), (w, 2.2, 0.12), "paving")
    with P.face(mb, cx, cy, w, d, "front") as L:
        P.arched_door(mb, 0, 0.1, w=1.3, h=2.3)
        for x in (-3.6, -1.9, 1.9, 3.6):
            P.arched_window(mb, x, 1.2, w=0.6, h=1.4)
    for x in (-3.0, 3.0):  # Cots in the loggia.
        mb.box((cx + x, ly + 0.6, 0.45), (1.8, 0.8, 0.12), "wood")
        mb.box((cx + x, ly + 0.6, 0.56), (1.7, 0.7, 0.12), "cloth_white")
        mb.box((cx + x - 0.65, ly + 0.6, 0.66), (0.35, 0.5, 0.1), "white")
        for sx in (-0.8, 0.8):
            mb.box((cx + x + sx, ly + 0.6, 0.25), (0.08, 0.7, 0.5), "timber")
    # A bell cote on the ridge, the banner of the healers, chimneys.
    mb.box((cx, cy, top + 0.6), (0.9, 0.5, 1.2), "wall")
    mb.box((cx, cy - 0.02, top + 0.6), (0.45, 0.6, 0.6), "charcoal")
    mb.cylinder((cx, cy, top + 0.45), (cx, cy, top + 0.8), 0.18, 0.1, "bell", segments=8)
    P.prism_xz(mb, [(cx - 0.6, top + 1.2), (cx + 0.6, top + 1.2), (cx, top + 1.7)], cy - 0.3, cy + 0.3, "roof")
    P.chimney(mb, cx - 3.6, cy + 0.9, h + 1.0, top + 1.0, w=0.65, pots=2)
    P.chimney(mb, cx + 3.6, cy + 0.9, h + 1.0, top + 1.0, w=0.65, pots=2)
    with mb.placed((cx - w / 2 - 0.9, ly - 0.6, 0)):
        mb.cylinder((0, 0, 0), (0, 0, 3.4), 0.06, 0.05, "timber", segments=6)
        mb.box((0.35, 0, 3.05), (0.7, 0.04, 0.6), "white")
        mb.box((0.35, -0.03, 3.05), (0.4, 0.03, 0.12), "leaves")
        mb.box((0.35, -0.03, 3.05), (0.12, 0.03, 0.4), "leaves")
    # The physic garden and the well.
    herb_beds(mb, 0.9, -3.9, nx=3, ny=1)
    herb_beds(mb, -4.3, -3.9, nx=2, ny=1)
    P.well(mb, -1.2, -3.6)


def monastery(mb, rig, seed=112):
    rnd = random.Random(seed)
    # The church along the north side of the cloister, its tower at the west end.
    with mb.placed((1.0, 6.0, 0)):
        castles.hall(mb, rnd, 12.0, 5.6, 6.0, 4.0, door_end="left", chimney=False, dormers=False, windows=4, buttress=True)
        mb.cylinder((6.0, 0, 0), (6.0, 0, 5.4), 2.4, 2.4, "wall", segments=12)
        P.cone_roof(mb, 6.0, 0, 5.4, 2.4, 2.8, ROOF, rows=4, eave=0.3, power=1.0, finial="gold")
        for a in (-0.9, 0, 0.9):
            round_window(mb, 6.0, 0, 2.4 * math.cos(math.pi / 12), a, 3.0, w=0.6, h=2.0)
    bell_tower(mb, rig, rnd, -6.6, 6.0, 3.4, 9.0, 5.5, door=True, pinnacles=False)
    with P.face(mb, -6.6, 6.0, 3.4, 3.4, "left"):
        P.arched_door(mb, 0, 0.05, w=1.3, h=2.5)
    # Three ranges around the cloister garth: dormitory (east), refectory (south), cellar (west).
    gx0, gx1, gy0, gy1 = -4.2, 4.8, -5.0, 3.0
    ranges = (("right", gx1 + 2.2, (gy0 + gy1) / 2 - 1.0, gy1 - gy0 + 2.4, 4.0, math.pi / 2),
              ("front", (gx0 + gx1) / 2, gy0 - 2.2, gx1 - gx0 + 8.8, 4.0, 0.0),
              ("left", gx0 - 2.2, (gy0 + gy1) / 2 - 1.0, gy1 - gy0 + 2.4, 4.0, math.pi / 2))
    for name, x, y, length, depth, turn in ranges:
        with mb.placed((x, y, 0), turn):
            storey(mb, rnd, "stone", 0, 0, 0, length, depth, 5.6)
            mb.box((0, 0, 3.0), (length + 0.12, depth + 0.12, 0.14), "wall_light")
            P.gable_roof(mb, 0, 0, length, depth, 5.6, 2.4, ROOF, rows=6, overhang=0.35, gable="wall", barge="wall_light")
            for side in ("front", "back"):
                with P.face(mb, 0, 0, length, depth, side) as L:
                    n = max(3, int(L / 2.2))
                    for i in range(n):
                        xx = -L / 2 + (i + 0.5) * L / n
                        P.arched_window(mb, xx, 3.6, w=0.55, h=1.2)
                        P.arrow_slit(mb, xx, 1.6, h=0.9)
    P.chimney(mb, 0.3, gy0 - 2.2 + 0.8, 6.4, 9.2, w=0.9, pots=3)
    with P.face(mb, (gx0 + gx1) / 2, gy0 - 2.2, gx1 - gx0 + 8.8, 4.0, "front"):
        P.arched_door(mb, 0, 0.05, w=1.8, h=2.9)
        P.wall_banner(mb, -2.2, 5.0, w=0.8, h=1.6)
        P.wall_banner(mb, 2.2, 5.0, w=0.8, h=1.6)
    # The cloister walk: arcades on the four sides of the garth, under lean-to roofs.
    mb.box(((gx0 + gx1) / 2, (gy0 + gy1) / 2, 0.04), (gx1 - gx0, gy1 - gy0, 0.08), "grass")
    wx, wy = gx1 - gx0, gy1 - gy0
    for (ox, oy, turn, L) in (((gx0 + gx1) / 2, gy0 + 1.6, math.pi, wx - 3.2), ((gx0 + gx1) / 2, gy1 - 1.6, 0.0, wx - 3.2),
                              (gx0 + 1.6, (gy0 + gy1) / 2, math.pi / 2, wy - 3.2), (gx1 - 1.6, (gy0 + gy1) / 2, -math.pi / 2, wy - 3.2)):
        with mb.placed((ox, oy, 0), turn):
            arcade(mb, L, max(2, int(L / 1.5)), h=2.6, d=0.4, open_h=2.0)
            P.prism_yz(mb, [(-0.4, 2.6), (1.7, 3.5), (1.7, 3.62), (-0.4, 2.72)], -L / 2 - 1.6, L / 2 + 1.6, "roof_dark")
    P.well(mb, (gx0 + gx1) / 2, (gy0 + gy1) / 2)
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.sphere(((gx0 + gx1) / 2 + sx * 1.6, (gy0 + gy1) / 2 + sy * 1.2, 0.4), 0.45, "hedge", segments=6, rings=4)
    # Outside the gate: a vegetable plot, beehives and barrels of the monks' beer.
    herb_beds(mb, 5.4, -9.4, nx=2, ny=1)
    for x in (-6.4, -5.6, -6.0):
        game.barrel(mb, x, -8.2 - (0.5 if x == -6.0 else 0), h=0.9, r=0.34)
    P.dome(mb, -8.2, -8.6, 0.45, 0.3, 0.42, ("thatch", "thatch_dark"), rows=3, seg=8, eave=0.0)
    mb.box((-8.2, -8.6, 0.22), (0.8, 0.6, 0.45), "wood")


def theater(mb, rig, seed=114):
    rnd = random.Random(seed)
    x, y, R, n = 0.0, 0.6, 5.2, 12
    h1, h2 = 2.8, 2.6
    q = R * math.cos(math.pi / n)
    width = 2 * R * math.sin(math.pi / n)
    mb.cylinder((x, y, 0), (x, y, 0.06), 3.2, 3.2, "earth", segments=12)
    for i in range(n):
        a = -math.pi / 2 + TAU * i / n
        with mb.placed((x + q * math.cos(a), y + q * math.sin(a), 0), a + math.pi / 2):
            # The outer wall of one bay: plaster and timber, a window on each floor.
            mb.box((0, 0.1, (h1 + h2) / 2), (width + 0.02, 0.2, h1 + h2), "plaster_warm")
            mb.box((0, 0.1, 0.25), (width + 0.06, 0.3, 0.5), "stone")
            P.timber_face(mb, width, 0.5, h1, spacing=width, braces=False, rail=False)
            P.timber_face(mb, width, h1, h1 + h2, spacing=width / 2, braces=False, rail=True, cross=False)
            if i == 0:
                P.plank_door(mb, 0, 0.1, w=1.5, h=2.2, double=True)
                P.wall_banner(mb, 0, h1 + h2 - 0.3, w=0.9, h=1.9)
            else:
                P.window(mb, 0, h1 + h2 * 0.5, w=0.5, h=0.6, shutter=None)
                if i % 2:
                    P.window(mb, 0, 1.7, w=0.5, h=0.6, shutter=None)
            # The gallery fronts toward the yard.
            mb.box((0, 2.0, h1), (width * 0.62, 0.12, 0.16), "timber")
            mb.box((0, 2.0, h1 + 0.45), (width * 0.62, 0.06, 0.7), "plank")
            mb.box((0, 1.1, h1 - 0.02), (width * 0.8, 1.9, 0.1), "plank_dark")
            for s in (-1, 1):
                mb.box((s * width * 0.31, 2.0, (h1 + h2) / 2), (0.14, 0.14, h1 + h2), "timber")
    zr = h1 + h2
    cone_panels(mb, x, y, zr - 0.15, R + 0.45, 1.5, ("thatch", "thatch_dark"), n, r_top=4.15)
    cone_panels(mb, x, y, zr + 1.35, 4.2, -1.1, ("thatch_dark", "thatch"), n, r_top=2.75)
    # The stage at the back, under its own roof, and the tiring-house turret.
    sy0 = y + 0.6
    mb.box((x, sy0 + 1.2, 0.6), (4.2, 2.4, 1.2), "plank")
    mb.box((x, sy0 - 0.02, 0.6), (4.24, 0.06, 1.2), "cloth_red")
    for s in (-1, 1):
        mb.cylinder((x + s * 1.8, sy0 + 0.3, 1.2), (x + s * 1.8, sy0 + 0.3, 4.6), 0.12, 0.1, "band", segments=8)
    mb.box((x, sy0 + 1.2, 4.7), (4.4, 2.6, 0.16), "timber")
    P.pyramid_roof(mb, x, sy0 + 1.2, 4.78, 4.4, 2.6, 1.3, ("thatch", "thatch_dark"), rows=3, overhang=0.2, ridge=2.0)
    mb.box((x, sy0 + 2.5, 3.0), (4.0, 0.2, 3.6), "plaster_warm")
    for xx in (-1.2, 1.2):
        mb.box((x + xx, sy0 + 2.38, 2.1), (0.8, 0.06, 1.8), "cloth_blue")
    mb.box((x, sy0 + 2.38, 2.2), (0.9, 0.06, 2.0), "door")
    tx, ty = x, y + q - 1.0
    mb.box((tx, ty, zr + 1.2), (2.2, 2.0, 3.0), "plaster_warm")
    for side in P.SIDES:
        with P.face(mb, tx, ty, 2.2, 2.0, side) as L:
            P.timber_face(mb, L, zr - 0.3, zr + 2.7, spacing=1.1, braces=False)
    tip = P.pyramid_roof(mb, tx, ty, zr + 2.7, 2.2, 2.0, 1.6, ("thatch", "thatch_dark"), rows=3, overhang=0.3)
    P.flag(mb, rig, tx, ty, tip - 0.2, pole=2.4, length=1.6, height=0.9, pennant=False)
    # Outside: a playbill board, a ticket table and torches.
    fy = y - q
    mb.box((x + 2.2, fy - 0.8, 0.9), (0.1, 0.1, 1.8), "timber")
    mb.box((x + 2.2, fy - 0.85, 1.5), (0.9, 0.06, 0.7), "wood_light")
    mb.box((x + 2.2, fy - 0.89, 1.5), (0.6, 0.02, 0.45), "white")
    P.table(mb, x - 2.4, fy - 1.0, w=1.2, d=0.7, benches=False)
    for s in (-1, 1):
        mb.cylinder((x + s * 1.2, fy - 0.3, 0), (x + s * 1.2, fy - 0.3, 2.0), 0.06, 0.05, "log", segments=6)
        mb.cylinder((x + s * 1.2, fy - 0.3, 2.0), (x + s * 1.2, fy - 0.3, 2.45), 0.12, 0.0, "torch_flame", segments=6)


def caravanserai(mb, rig, seed=116):
    rnd = random.Random(seed)
    W, D, H, T = 15.0, 13.0, 4.2, 0.7
    cy = 0.0
    mb.box((0, cy, 0.03), (W, D, 0.06), "sand")
    # The outer wall, with the great gate in the front.
    gw = 5.0
    for x, y, w, d in (((-W / 2 - gw / 2) / 2 - 0.0 + 0.0, cy - D / 2 + T / 2, W / 2 - gw / 2, T), ((W / 2 + gw / 2) / 2, cy - D / 2 + T / 2, W / 2 - gw / 2, T),
                       (0, cy + D / 2 - T / 2, W, T), (-W / 2 + T / 2, cy, T, D), (W / 2 - T / 2, cy, T, D)):
        mb.box((x, y, H / 2), (w, d, H), "wall")
        mb.box((x, y, 0.3), (w + 0.2, d + 0.2, 0.6), "wall_dark")
        mb.box((x, y, H + 0.08), (w + 0.16, d + 0.16, 0.16), "wall_light")
    for side in P.SIDES:
        with P.face(mb, 0, cy, W, D, side) as L:
            P.scatter_face(mb, rnd, L - 6 if side == "front" else L - 1, 0.8, H - 0.4, density=0.12)
            if side != "front":
                for i in range(int(L / 2.4)):
                    mb.box((-L / 2 + (i + 0.5) * L / int(L / 2.4), -0.03, H - 0.9), (0.5, 0.08, 0.5), "wall_dark")
    with mb.placed((0, cy - D / 2 + 0.6, 0)):
        P.arch_wall(mb, gw, 1.6, 6.0, 3.0, 4.2)
        P.arch_trim(mb, 0, -0.8, 0, 3.0, 4.2, t=0.3, depth=0.14, seg=6)
        P.battlements(mb, 0, 0, 6.0, gw, 1.6, merlon=0.5, gap=0.4, low=0.3, high=0.5, out=0.15)
        for s in (-1, 1):
            with mb.placed((0, -0.8, 0)):
                P.wall_banner(mb, s * 2.0, 5.2, w=0.7, h=2.2)
            mb.box((s * 1.42, 0.5, 1.9), (0.12, 1.4, 3.6), "door")
        mb.box((0, 0, 0.04), (3.0, 3.6, 0.08), "paving")
    # Corner turrets with small domes.
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * (W / 2 - 0.2), cy + sy * (D / 2 - 0.2)
            mb.cylinder((x, y, 0), (x, y, H + 1.2), 1.0, 0.95, "wall", segments=10)
            mb.cylinder((x, y, H + 1.2), (x, y, H + 1.35), 1.1, 1.1, "wall_light", segments=10)
            P.dome(mb, x, y, H + 1.35, 0.95, 1.0, ("teal", "teal_dark"), rows=3, seg=10, eave=0.1, finial="gold")
    # Stalls and stables under a lean-to roof along the inside of three walls.
    depth = 2.4
    for (ox, oy, turn, L) in ((0, cy + D / 2 - T, 0.0, W - 2 * T - 0.4), (-W / 2 + T, cy + 0.6, math.pi / 2, D - 2 * T - 2.8),
                              (W / 2 - T, cy + 0.6, -math.pi / 2, D - 2 * T - 2.8)):
        with mb.placed((ox, oy, 0), turn):
            # Local frame: the wall is at y = 0 and the yard toward +Y... turned so the yard is toward -Y.
            n = max(3, int(L / 2.6))
            for i in range(n + 1):
                xx = -L / 2 + i * L / n
                mb.box((xx, -depth, 1.3), (0.2, 0.2, 2.6), "timber")
                if i < n:
                    mb.box((xx + L / n / 2, -depth / 2, 0.9), (0.08, depth, 1.6), "plank") if i % 2 else None
                    kind = (i * 3 + int(turn * 2)) % 4
                    cxx = xx + L / n / 2
                    if kind == 0:
                        game.crate(mb, cxx - 0.4, -0.8, s=0.6)
                        game.crate(mb, cxx + 0.3, -0.7, s=0.5)
                    elif kind == 1:
                        sack(mb, cxx - 0.3, -0.7)
                        sack(mb, cxx + 0.3, -0.9, s=0.9)
                    elif kind == 2:
                        P.hay_bale(mb, cxx, -0.7)
                        mb.box((cxx, -1.6, 0.4), (1.2, 0.4, 0.3), "wood")
                    else:
                        game.barrel(mb, cxx - 0.3, -0.7, h=0.85, r=0.32)
                        game.barrel(mb, cxx + 0.4, -0.8, h=0.85, r=0.32)
            mb.box((0, -depth, 2.55), (L + 0.2, 0.2, 0.2), "timber")
            P.prism_yz(mb, [(-depth - 0.5, 2.55), (0.0, 3.5), (0.0, 3.62), (-depth - 0.5, 2.67)], -L / 2 - 0.2, L / 2 + 0.2, "tile_red")
            for i in range(0, n, 2):
                x0 = -L / 2 + i * L / n
                P.prism_yz(mb, [(-depth - 0.52, 2.57), (0.0, 3.52), (0.0, 3.66), (-depth - 0.52, 2.71)], x0, x0 + L / n * 0.5, "tile_red_dark")
    # The yard: a fountain, loaded carts and an awning for the traders.
    mb.cylinder((0, cy - 0.6, 0), (0, cy - 0.6, 0.5), 1.4, 1.4, "wall", segments=10)
    mb.cylinder((0, cy - 0.6, 0.47), (0, cy - 0.6, 0.52), 1.15, 1.15, "water", segments=10)
    mb.cylinder((0, cy - 0.6, 0.4), (0, cy - 0.6, 1.3), 0.16, 0.12, "wall_light", segments=6)
    mb.cylinder((0, cy - 0.6, 1.3), (0, cy - 0.6, 1.42), 0.4, 0.5, "wall_light", segments=8)
    hand_cart(mb, -3.2, cy - 2.6, 0.3)
    hand_cart(mb, 3.4, cy - 2.2, 2.6)
    for i, c in enumerate(("stripe_a", "stripe_b", "teal")):
        x0 = 2.2 + i * 0.9
        game.sloped_slab(mb, x0, x0 + 0.91, cy - 4.9, cy - 3.4, 2.2, 2.5, 0.05, c)
    for xx in (2.2, 4.9):
        for yy in (cy - 4.9, cy - 3.4):
            mb.box((xx, yy, 1.15), (0.08, 0.08, 2.3), "timber")
    mb.box((3.55, cy - 4.2, 0.4), (2.2, 0.8, 0.8), "wood")
    for i, c in enumerate(("cloth_red", "cloth_blue", "gold", "cloth_green")):
        mb.box((2.8 + i * 0.5, cy - 4.2, 0.86), (0.4, 0.6, 0.12), c)
    P.flag(mb, rig, 0, cy - D / 2 + 0.6, 7.1, pole=2.0, length=1.4)


def observatory(mb, rig, seed=118):
    rnd = random.Random(seed)
    x, y, r, h = 0.0, 0.6, 2.7, 6.0
    P.round_tower(mb, x, y, r, h, rnd, slits=0, bands=True)
    q = r * math.cos(math.pi / 14)
    with mb.placed((x, y - q - 0.02, 0)):
        P.arched_door(mb, 0, 0.1, w=1.1, h=2.1)
    for a, z in ((0.5, 2.4), (2.6, 2.4), (-2.2, 4.4), (0.9, 4.6), (2.2, 4.6), (-math.pi / 2, 4.4)):
        round_window(mb, x, y, q, a, z, w=0.5, h=0.9)
    mb.cylinder((x, y, h - 0.5), (x, y, h), r, r + 0.3, "wall", segments=14)
    mb.cylinder((x, y, h), (x, y, h + 0.3), r + 0.32, r + 0.32, "wall_light", segments=14)
    railing_ring(mb, x, y, h + 0.3, r + 0.2, n=14, h=0.8)
    # The dome, which turns with its telescope (clip `turn`).
    with mb.bone("dome"):
        mb.cylinder((x, y, h + 0.3), (x, y, h + 0.8), r - 0.5, r - 0.5, "copper_dark", segments=12)
        P.dome(mb, x, y, h + 0.8, r - 0.5, 2.1, ("copper", "copper_dark"), rows=5, seg=12, eave=0.08)
        for k in range(7):  # The slit: dark panels following the curve of the dome.
            f = math.radians(8 + k * 13)
            mb.box((x, y - (r - 0.5) * 0.97 * math.cos(f), h + 0.8 + 2.1 * 0.97 * math.sin(f)), (0.9, 0.5, 0.5), "charcoal")
        P.beam(mb, (x, y - 0.3, h + 1.4), (x, y - 3.1, h + 3.3), 0.22, "brass")
        mb.cylinder((x, y - 3.0, h + 3.23), (x, y - 3.35, h + 3.47), 0.28, 0.3, "brass", segments=8)
        mb.cylinder((x, y - 3.34, h + 3.46), (x, y - 3.37, h + 3.48), 0.22, 0.22, "glass", segments=8)
    rig.bone("dome", (x, y, h + 0.8), (x, y, h + 1.8), None)
    rig.add("turn", 12.0, lambda t: {"dome": [(P.kit.Z, 70 * math.sin(TAU * t))]})
    # The stair around the tower up to a gallery door.
    n = 18
    for i in range(n):
        t = (i + 0.5) / n
        a = -0.6 + 3.2 * t
        z = 0.15 + 3.6 * t
        rr = r + 0.6
        mb.box((x + rr * math.cos(a), y + rr * math.sin(a), z / 2), (1.1, 0.62, z), "wall_dark", rotation_z=a)
    a = -0.6 + 3.2 + 0.15
    mb.box((x + (r + 0.6) * math.cos(a), y + (r + 0.6) * math.sin(a), 1.9), (1.2, 1.0, 3.8), "wall_dark", rotation_z=a)
    mb.box((x + q * math.cos(a), y + q * math.sin(a), 4.7), (0.24, 0.8, 1.7), "door", rotation_z=a)
    # In the yard: an armillary sphere, a sundial, a star chart on a table.
    ax, ay = 2.9, -2.6
    mb.cylinder((ax, ay, 0), (ax, ay, 0.9), 0.3, 0.2, "wall_light", segments=8)
    for k in range(3):
        m = P.turn_x((ax, ay, 1.55), k * 1.05) @ P.turn_y((ax, ay, 1.55), k * 0.7)
        with mb.placed(matrix=m):
            for i in range(12):
                a0, a1 = TAU * i / 12, TAU * (i + 1) / 12
                P.beam(mb, (ax + 0.6 * math.cos(a0), ay + 0.6 * math.sin(a0), 1.55), (ax + 0.6 * math.cos(a1), ay + 0.6 * math.sin(a1), 1.55),
                       0.04, "brass")
    mb.sphere((ax, ay, 1.55), 0.16, "gold", segments=6, rings=4)
    mb.cylinder((-2.9, -2.8, 0), (-2.9, -2.8, 0.8), 0.22, 0.16, "wall_light", segments=8)
    mb.cylinder((-2.9, -2.8, 0.8), (-2.9, -2.8, 0.88), 0.4, 0.4, "wall_light", segments=10)
    P.prism_xz(mb, [(-3.1, 0.88), (-2.7, 0.88), (-2.7, 1.15)], -2.82, -2.78, "brass")
    P.table(mb, -0.2, -3.6, w=1.3, d=0.8, benches=False)
    mb.box((-0.2, -3.6, 0.79), (0.9, 0.6, 0.02), "cloth_blue")


def make(name, fn, colors, **kw):
    def build():
        mb = P.begin()
        rig = P.Rig()
        fn(mb, rig, **kw)
        P.finish(mb, name, colors, rig)
    return build


SLATE = dict(roof=0x5A6470, roof_dark=0x46505A)
RED = dict(roof=0xB0503A, roof_dark=0x8E3E2A)

MODELS = {
    "bld_infirmary_stone": make("bld_infirmary_stone", infirmary, P.palette(**RED)),
    "bld_infirmary_slate": make("bld_infirmary_slate", infirmary, P.palette(**SLATE)),
    "bld_monastery_stone": make("bld_monastery_stone", monastery, P.palette(**RED)),
    "bld_monastery_sandstone": make("bld_monastery_sandstone", monastery, P.SANDSTONE_RED),
    "bld_theater": make("bld_theater", theater, P.BASE),
    "bld_caravanserai_sandstone": make("bld_caravanserai_sandstone", caravanserai, P.SANDSTONE_RED),
    "bld_caravanserai_stone": make("bld_caravanserai_stone", caravanserai, P.palette(banner=0x3E7A46)),
    "bld_observatory": make("bld_observatory", observatory, P.BASE),
}
