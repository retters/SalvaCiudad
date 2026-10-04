"""The inn: two storeys, a jettied upper floor, a big chimney, a hanging
sign that swings, a stable lean-to, barrels and tables outside."""

import math
import random

import parts as P
from mills import hand_cart
from parts import game


def inn(mb, rig, walls="timber", roof=("roof", "roof_dark"), seed=4):
    rnd = random.Random(seed)
    cx, cy = -0.6, 1.2
    w, d, h1, h2 = 7.0, 5.0, 2.9, 2.6
    jet = 0.3 if walls != "log" else 0.0
    e = 0.34 if walls == "log" else 0.0   # Logs stand proud of the wall plane.
    W, D = w + 2 * jet, d + 2 * jet
    z1 = h1 + 0.2
    # Ground floor.
    if walls == "stone":
        P.stone_block(mb, cx, cy, 0, w, d, h1, rnd, density=0.3)
    elif walls == "log":
        mb.box((cx, cy, 0.2), (w + 0.5, d + 0.5, 0.4), "stone")
        P.log_block(mb, cx, cy, 0.4, w, d, h1 - 0.4)
    else:
        mb.box((cx, cy, 0.3), (w + 0.16, d + 0.16, 0.6), "stone")
        P.framed_block(mb, cx, cy, 0.6, w, d, h1 - 0.6, infill="plaster_warm")
    # The jetty: joists under the upper floor.
    mb.box((cx, cy, h1 + 0.1), (W + 0.1, D + 0.1, 0.2), "timber")
    if jet:
        n = 9
        for i in range(n):
            x = cx - W / 2 + 0.2 + i * (W - 0.4) / (n - 1)
            for sy in (-1, 1):
                mb.box((x, cy + sy * (D / 2 - 0.1), h1 - 0.08), (0.16, 0.5, 0.18), "timber")
    # Upper floor.
    if walls == "log":
        P.log_block(mb, cx, cy, z1, W, D, h2)
    else:
        P.framed_block(mb, cx, cy, z1, W, D, h2, infill="plaster_warm" if walls == "timber" else "plaster",
                       cross=True, spacing=1.25)
    top = P.gable_roof(mb, cx, cy, W, D, z1 + h2, 3.0, roof, rows=7, overhang=0.45,
                       gable="plank" if walls == "log" else "plaster_warm", end_overhang=0.35)
    if walls != "log":
        for sx in (-1, 1):  # A little frame on the gables.
            with P.face(mb, cx, cy, W + e, D + e, "right" if sx > 0 else "left"):
                mb.box((0, 0, z1 + h2 + 1.0), (0.14, 0.14, 2.0), "timber")
                mb.box((0, 0, z1 + h2 + 1.2), (D * 0.55, 0.14, 0.14), "timber")
                P.window(mb, 0, z1 + h2 + 0.6, w=0.5, h=0.5, shutter=None)
    # Windows and the door.
    with P.face(mb, cx, cy, w + e, d + e, "front") as L:
        P.plank_door(mb, 0, 0.3 if walls != "stone" else 0.1, w=1.1, h=1.8)
        for x in (-L * 0.34, L * 0.34):
            P.window(mb, x, 1.75, w=0.9, h=0.8, lit=True)
    with P.face(mb, cx, cy, w + e, d + e, "back") as L:
        for x in (-L * 0.3, 0, L * 0.3):
            P.window(mb, x, 1.75, w=0.7, h=0.7)
    with P.face(mb, cx, cy, W + e, D + e, "front") as L:
        for i, x in enumerate((-L * 0.36, -L * 0.12, L * 0.12, L * 0.36)):
            P.window(mb, x, z1 + h2 * 0.55, w=0.65, h=0.75, flowers=(i % 2 == 0), lit=(i == 1))
    with P.face(mb, cx, cy, W + e, D + e, "back") as L:
        for x in (-L * 0.3, 0, L * 0.3):
            P.window(mb, x, z1 + h2 * 0.55, w=0.65, h=0.75)
    with P.face(mb, cx, cy, W + e, D + e, "right") as L:
        P.window(mb, 0, z1 + h2 * 0.55, w=0.65, h=0.75)
    # Dormers on the front slope.
    for x in (cx - 1.9, cx + 1.9):
        P.dormer(mb, x, cy - D / 2 + 0.7, z1 + h2 + 0.75, w=1.0, h=0.8, depth=1.3, mats=roof,
                 walls="plank" if walls == "log" else "plaster_warm")
    # The porch over the door.
    px, py = cx, cy - d / 2
    for sx in (-1, 1):
        mb.box((px + sx * 1.0, py - 1.1, 1.2), (0.14, 0.14, 2.4), "timber")
        P.beam(mb, (px + sx * 1.0, py - 1.1, 1.8), (px + sx * 0.5, py - 1.1, 2.35), 0.09, "timber")
    mb.box((px, py - 1.1, 2.4), (2.3, 0.14, 0.14), "timber")
    game.sloped_slab(mb, px - 1.3, px + 1.3, py - 1.5, py + 0.0, 2.35, 2.95, 0.1, roof[1])
    mb.box((px, py - 0.6, 0.12), (2.2, 1.3, 0.24), "stone")
    mb.box((px + 1.0, py - 1.2, 2.05), (0.16, 0.16, 0.26), "glow")  # A lantern.
    mb.box((px + 1.0, py - 1.2, 2.22), (0.2, 0.2, 0.06), "iron")
    # The great chimney on the left end.
    sx0 = cx - W / 2 - 0.3
    mb.box((sx0, cy + 0.3, 1.6), (1.1, 1.9, 3.2), "stone")
    mb.box((sx0, cy + 0.3, 0.3), (1.3, 2.1, 0.6), "stone_dark")
    P.prism_yz(mb, [(cy + 0.3 - 0.95, 3.2), (cy + 0.3 + 0.95, 3.2), (cy + 0.3 + 0.5, 4.3), (cy + 0.3 - 0.5, 4.3)],
               sx0 - 0.55, sx0 + 0.55, "stone")
    P.chimney(mb, sx0, cy + 0.3, 4.3, top + 1.1, w=1.0, mat="stone", cap="stone_dark", pots=2)
    with mb.placed((sx0 - 0.55, cy + 0.3, 0), -math.pi / 2):
        P.scatter_face(mb, rnd, 1.8, 0.7, top, ("stone_dark", "plaster"), density=0.5, size=(0.4, 0.25))
    # The sign, sticking out over the street.
    with mb.placed((cx + W / 2 - 0.5, cy - D / 2, 0), -math.pi / 2):
        P.hanging_sign(mb, rig, 0, 0, z1 + 1.9, arm=1.3, board=(0.95, 0.75))
    # The stable lean-to on the right end.
    x0, x1 = cx + w / 2, cx + w / 2 + 1.9
    y0, y1 = cy - d / 2 + 0.6, cy + d / 2
    for y in (y0, (y0 + y1) / 2, y1):
        mb.box((x1 - 0.1, y, 1.0), (0.16, 0.16, 2.0), "timber")
    with mb.placed(((x0 + x1) / 2, (y0 + y1) / 2, 0), math.pi / 2):
        L = y1 - y0
        game.sloped_slab(mb, -L / 2 - 0.25, L / 2 + 0.25, -(x1 - x0) / 2 - 0.3, (x1 - x0) / 2, 2.0, 2.75, 0.1, roof[0])
        game.sloped_slab(mb, -L / 2 - 0.25, L / 2 + 0.25, -(x1 - x0) / 2 - 0.3, -(x1 - x0) / 2 + 0.4, 2.05, 2.28, 0.1,
                         roof[1])
    mb.box(((x0 + x1) / 2, y1, 1.0), (x1 - x0, 0.1, 2.0), "plank")
    mb.box(((x0 + x1) / 2, (y0 + y1) / 2, 0.9), (x1 - x0 - 0.2, 0.08, 1.0), "plank")  # Stall partition.
    P.hay_bale(mb, x0 + 0.8, y1 - 0.6)
    mb.box((x0 + 0.5, y0 + 1.0, 0.4), (0.5, 1.2, 0.3), "wood")  # Trough.
    mb.box((x0 + 0.5, y0 + 1.0, 0.52), (0.36, 1.05, 0.08), "water")
    # A hitching rail in front of the stable.
    for x in (x0 + 0.2, x1 - 0.2):
        mb.box((x, y0 - 1.3, 0.5), (0.12, 0.12, 1.0), "timber")
    mb.cylinder((x0, y0 - 1.3, 0.95), (x1, y0 - 1.3, 0.95), 0.06, 0.06, "wood", segments=6)
    # The yard: tables, barrels, firewood.
    P.table(mb, cx - 2.6, -3.1, w=1.6)
    P.table(mb, cx + 2.4, -3.3, w=1.6)
    for x, y, hh in ((cx - 1.5, py - 0.45, 0.9), (cx - 2.2, py - 0.4, 0.9), (cx - 1.85, py - 0.42, 0.0)):
        if hh:
            game.barrel(mb, x, y, h=hh, r=0.33)
    game.barrel(mb, cx + 1.6, py - 0.45, h=0.9, r=0.33)
    mb.cylinder((cx + 2.5, py - 0.5, 0.36), (cx + 3.3, py - 0.5, 0.36), 0.36, 0.36, "wood", segments=10)  # A keg on its side.
    for x in (cx + 2.6, cx + 3.2):
        mb.box((x, py - 0.5, 0.12), (0.1, 0.6, 0.24), "timber")
    game.log_pile(mb, cx - 2.0, cy + d / 2 + 0.5, length=1.6, rows=2)
    game.crate(mb, cx + 1.0, cy + d / 2 + 0.45, s=0.55)
    game.crate(mb, cx + 1.7, cy + d / 2 + 0.4, s=0.45)


def coaching_inn(mb, rig, roof=("roof", "roof_dark"), seed=5):
    """A big inn around a yard: a front range with a carriage arch, two
    wings with galleries, a stable and a well."""
    rnd = random.Random(seed)
    fy, fw, fd, h1, h2, aw = -3.4, 13.0, 4.0, 3.0, 2.6, 3.2
    for s in (-1, 1):
        P.stone_block(mb, s * (aw / 2 + (fw - aw) / 4), fy, 0, (fw - aw) / 2, fd, h1, rnd, density=0.3)
    with mb.placed((0, fy, 0)):
        P.arch_wall(mb, aw, fd, h1, 2.4, 2.7)
        P.arch_trim(mb, 0, -fd / 2, 0, 2.4, 2.7)
        mb.box((0, 0.5, 0.03), (2.4, fd + 2.0, 0.06), "paving")
        mb.box((1.0, -fd / 2 - 0.25, 2.5), (0.2, 0.2, 0.3), "glow")
        mb.box((1.0, -fd / 2 - 0.1, 2.75), (0.06, 0.5, 0.06), "iron")
    z1 = h1 + 0.2
    W, D = fw + 0.5, fd + 0.5
    mb.box((0, fy, h1 + 0.1), (W + 0.1, D + 0.1, 0.2), "timber")
    for i in range(14):
        mb.box((-W / 2 + 0.2 + i * (W - 0.4) / 13, fy - D / 2 + 0.1, h1 - 0.08), (0.16, 0.5, 0.18), "timber")
    P.framed_block(mb, 0, fy, z1, W, D, h2, infill="plaster_warm", cross=True, spacing=1.3)
    top = P.gable_roof(mb, 0, fy, W, D, z1 + h2, 2.8, roof, rows=7, overhang=0.45, gable="plaster_warm", end_overhang=0.35)
    with P.face(mb, 0, fy, fw, fd, "front"):
        P.plank_door(mb, -4.0, 0.1, w=1.1, h=1.8)
        for x in (-5.5, -2.6, 2.8, 4.2, 5.6):
            P.window(mb, x, 1.75, w=0.8, h=0.8, lit=(x < 0))
    with P.face(mb, 0, fy, W, D, "front") as L:
        for i in range(7):
            P.window(mb, -L / 2 + (i + 0.5) * L / 7, z1 + h2 * 0.55, w=0.65, h=0.75, flowers=(i % 3 == 0), lit=(i in (2, 5)))
    for x in (-4.2, 0, 4.2):
        P.dormer(mb, x, fy - D / 2 + 0.7, z1 + h2 + 0.72, w=1.0, h=0.8, depth=1.3, mats=roof, walls="plaster_warm")
    # The great chimney on the left end and the sign over the street.
    sx0 = -W / 2 - 0.3
    mb.box((sx0, fy, 1.6), (1.1, 1.9, 3.2), "stone")
    P.prism_yz(mb, [(fy - 0.95, 3.2), (fy + 0.95, 3.2), (fy + 0.5, 4.3), (fy - 0.5, 4.3)], sx0 - 0.55, sx0 + 0.55, "stone")
    P.chimney(mb, sx0, fy, 4.3, top + 1.1, w=1.0, mat="stone", cap="stone_dark", pots=2)
    with mb.placed((W / 2 - 0.5, fy - D / 2, 0), -math.pi / 2):
        P.hanging_sign(mb, rig, 0, 0, z1 + 1.9, arm=1.3, board=(0.95, 0.75))
    # The two wings behind, with galleries toward the yard.
    wy0, wlen, ww = fy + fd / 2, 7.2, 3.4
    wyc = wy0 + wlen / 2
    for s in (-1, 1):
        wx = s * (fw / 2 - ww / 2)
        if s < 0:   # The kitchen and the rooms.
            mb.box((wx, wyc, 0.3), (ww + 0.16, wlen, 0.6), "stone")
            P.framed_block(mb, wx, wyc, 0.6, ww, wlen, h1 - 0.6, infill="plaster_warm")
            with P.face(mb, wx, wyc, ww, wlen, "right") as L:
                P.plank_door(mb, 0, 0.4, w=0.95, h=1.7)
                P.window(mb, -L * 0.3, 1.75, w=0.6, h=0.7, lit=True)
        else:       # The stable, open to the yard.
            for i in range(4):
                y = wy0 + 0.2 + i * (wlen - 0.4) / 3
                mb.box((wx - ww / 2 + 0.1, y, h1 / 2), (0.2, 0.2, h1), "timber")
                mb.box((wx + ww / 2 - 0.1, y, h1 / 2), (0.2, 0.2, h1), "timber")
                if i < 3:
                    mb.box((wx + 0.3, y + (wlen - 0.4) / 3, 0.75), (ww - 0.9, 0.08, 1.5), "plank")
            mb.box((wx + ww / 2 - 0.05, wyc, h1 / 2), (0.1, wlen, h1), "plank")
            mb.box((wx, wy0 + wlen - 0.05, h1 / 2), (ww, 0.1, h1), "plank")
            P.hay_bale(mb, wx + 0.6, wy0 + 1.2)
            P.hay_bale(mb, wx + 0.6, wy0 + 3.4)
            mb.box((wx - 0.9, wy0 + 5.6, 0.4), (0.5, 1.4, 0.3), "wood")
            mb.box((wx - 0.9, wy0 + 5.6, 0.52), (0.36, 1.25, 0.08), "water")
        mb.box((wx, wyc, h1 + 0.1), (ww + 0.5, wlen + 0.1, 0.2), "timber")
        P.framed_block(mb, wx, wyc, z1, ww + 0.4, wlen, h2, infill="plaster_warm", spacing=1.2)
        with mb.placed((wx, wyc + 0.2, 0), math.pi / 2):
            P.gable_roof(mb, 0, 0, wlen + 0.4, ww + 0.4, z1 + h2, 2.2, roof, rows=6, overhang=0.4, gable="plaster_warm", end_overhang=0.35)
        inner = "right" if s < 0 else "left"
        outer = "left" if s < 0 else "right"
        with P.face(mb, wx, wyc, ww + 0.4, wlen, outer) as L:
            for x in (-L * 0.3, 0, L * 0.3):
                P.window(mb, x, z1 + h2 * 0.55, w=0.6, h=0.75)
        with P.face(mb, wx, wyc, ww + 0.4, wlen, inner) as L:
            for x in (-L * 0.28, L * 0.28):
                P.plank_door(mb, x, z1 + 0.05, w=0.8, h=1.7)
            P.window(mb, 0, z1 + h2 * 0.6, w=0.55, h=0.65, shutter=None, lit=True)
            # The gallery.
            mb.box((0, -0.6, z1 - 0.03), (L, 1.2, 0.1), "plank")
            mb.box((0, -1.15, z1 + 0.95), (L, 0.08, 0.08), "timber")
            for i in range(5):
                x = -L / 2 + 0.1 + i * (L - 0.2) / 4
                mb.box((x, -1.15, (z1 + 2.3) / 2), (0.13, 0.13, z1 + 2.3), "timber")
                if i < 4:
                    for k in range(1, 4):
                        mb.box((x + k * (L - 0.2) / 16, -1.15, z1 + 0.48), (0.05, 0.05, 0.9), "wood")
            game.sloped_slab(mb, -L / 2 - 0.1, L / 2 + 0.1, -1.45, 0.0, z1 + 2.2, z1 + 2.55, 0.07, roof[1])
        with P.face(mb, wx, wyc, ww + 0.4, wlen, "back") as L:
            P.window(mb, 0, z1 + h2 * 0.55, w=0.6, h=0.75)
    # A stair up to the left gallery, at the back.
    with mb.placed((-fw / 2 + ww + 0.85, wy0 + wlen + 0.4, 0), math.pi):
        P.stairs(mb, 0, 0, 0, z1 - 0.05, 0.9, 3.4, mat="plank", solid=False, step=0.27)
        for sx in (-0.45, 0.45):
            P.beam(mb, (sx, 0, 0), (sx, 3.4, z1 - 0.1), 0.09, "timber")
    # The yard: a well, a wagon, tables, barrels.
    mb.box((0, wyc, 0.03), (fw - 2 * ww - 0.4, wlen, 0.06), "paving")
    P.well(mb, 0.4, wyc + 1.6, roof=roof)
    hand_cart(mb, 1.2, wy0 + 1.4, 1.9)
    P.table(mb, -1.6, wy0 + 1.6, w=1.5)
    for x, y in ((-2.2, wy0 + 4.0), (-1.6, wy0 + 4.2), (-1.9, wy0 + 4.7)):
        game.barrel(mb, x, y, h=0.9, r=0.33)
    P.table(mb, -4.8, fy - fd / 2 - 1.3, w=1.6)
    for x in (3.2, 3.9):
        game.barrel(mb, x, fy - fd / 2 - 0.5, h=0.9, r=0.33)
    for x in (4.8, 6.2):
        mb.box((x, fy - fd / 2 - 1.5, 0.5), (0.12, 0.12, 1.0), "timber")
    mb.cylinder((4.7, fy - fd / 2 - 1.5, 0.95), (6.3, fy - fd / 2 - 1.5, 0.95), 0.06, 0.06, "wood", segments=6)


def make_coaching(name, roof):
    def build():
        mb = P.begin()
        rig = P.Rig()
        coaching_inn(mb, rig)
        P.finish(mb, name, P.palette(**P.ROOFS[roof]), rig)
    return build


def make(name, walls, roof):
    def build():
        mb = P.begin()
        rig = P.Rig()
        inn(mb, rig, walls)
        P.finish(mb, name, P.palette(**P.ROOFS[roof]), rig)
    return build


MODELS = {
    "bld_inn_timber_tiles": make("bld_inn_timber_tiles", "timber", "tiles"),
    "bld_inn_timber_thatch": make("bld_inn_timber_thatch", "timber", "thatch"),
    "bld_inn_timber_blue": make("bld_inn_timber_blue", "timber", "blue"),
    "bld_inn_stone_slate": make("bld_inn_stone_slate", "stone", "slate"),
    "bld_inn_stone_tiles": make("bld_inn_stone_tiles", "stone", "tiles"),
    "bld_inn_log_shingles": make("bld_inn_log_shingles", "log", "shingles"),
    "bld_inn_log_thatch": make("bld_inn_log_thatch", "log", "thatch"),
    "bld_inn_coaching_tiles": make_coaching("bld_inn_coaching_tiles", "tiles"),
    "bld_inn_coaching_slate": make_coaching("bld_inn_coaching_slate", "slate"),
    "bld_inn_coaching_thatch": make_coaching("bld_inn_coaching_thatch", "thatch"),
}
