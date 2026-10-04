"""Timber-framed village houses, as in the reference picture: four levels in
two shapes, inside the 6 x 5 m lot of the game's house. Roof, walls and
shutters use the var_* materials, which the game recolors per house."""

import math
import random

import parts as P
from parts import game

ROOFV = ("var_roof", "var_roof_dark")


def house(mb, rig, level=1, style=0, seed=0, extras=True):
    rnd = random.Random(seed + level * 7 + style)
    cx, cy = 0.0, 0.45
    w, d = (4.6, 3.2) if style != 1 else (3.5, 3.6)
    floors = (1, 2, 2, 3)[level - 1]
    h = (2.5, 2.4, 2.6, 2.5)[level - 1]
    z, W, D = 0.0, w, d
    for k in range(floors):
        if k == 0:
            if level >= 3:
                P.stone_block(mb, cx, cy, 0, W, D, h, rnd, density=0.3)
            else:
                mb.box((cx, cy, 0.25), (W + 0.16, D + 0.16, 0.5), "stone")
                P.framed_block(mb, cx, cy, 0.5, W, D, h - 0.5, infill="var_walls", spacing=1.2)
        else:
            W, D = W + 0.36, D + 0.36
            mb.box((cx, cy, z + 0.08), (W + 0.1, D + 0.1, 0.16), "timber")
            m = max(4, int(W / 0.7))
            for i in range(m):
                x = cx - W / 2 + 0.15 + i * (W - 0.3) / (m - 1)
                for sy in (-1, 1):
                    mb.box((x, cy + sy * (D / 2 - 0.08), z - 0.08), (0.13, 0.4, 0.16), "timber")
            P.framed_block(mb, cx, cy, z + 0.16, W, D, h - 0.16, infill="var_walls", spacing=1.15, cross=(k == floors - 1))
        zc = z + h * (0.6 if k == 0 else 0.55)
        with P.face(mb, cx, cy, W, D, "front") as L:
            if k == 0:
                dx = -L * 0.26 if style != 1 else 0.0
                P.plank_door(mb, dx, 0.5 if level < 3 else 0.1, w=0.95, h=1.6)
                mb.box((dx, -0.35, 0.12 if level >= 3 else 0.25), (1.3, 0.6, 0.24 if level >= 3 else 0.5), "stone")
                if style != 1:
                    P.window(mb, L * 0.22, zc, w=0.8, h=0.75, shutter="var_shutter", flowers=level >= 2)
                else:
                    for x in (-L * 0.33, L * 0.33):
                        P.window(mb, x, zc, w=0.42, h=0.75, shutter=None)
            else:
                xs = (-L * 0.27, L * 0.27) if style == 1 or L < 5 else (-L * 0.32, 0, L * 0.32)
                if style == 2:
                    xs = (-L * 0.3,)
                for i, x in enumerate(xs):
                    P.window(mb, x, zc, w=0.6, h=0.75, shutter="var_shutter", flowers=(i == 0 and k == 1), lit=(i == 1 and k == 1))
        with P.face(mb, cx, cy, W, D, "back") as L:
            for x in (-L * 0.27, L * 0.27):
                P.window(mb, x, zc, w=0.6, h=0.7, shutter="var_shutter")
        for side in ("left", "right"):
            with P.face(mb, cx, cy, W, D, side) as L:
                if k > 0 or side == "right":
                    P.window(mb, 0, zc, w=0.55, h=0.7, shutter="var_shutter" if k else None)
        z += h
    rise = (2.0, 2.3, 2.5, 2.9)[level - 1] * (1.0 if style != 1 else 1.12)
    if style != 1:
        top = P.gable_roof(mb, cx, cy, W, D, z, rise, ROOFV, rows=6, overhang=0.36, gable="var_walls", end_overhang=0.3)
        ends = ("left", "right")
    else:
        with mb.placed((cx, cy, 0), math.pi / 2):
            top = P.gable_roof(mb, 0, 0, D, W, z, rise, ROOFV, rows=6, overhang=0.36, gable="var_walls", end_overhang=0.3)
        ends = ("front", "back")
    for side in ends:   # A king post, a collar and a little window in each gable.
        with P.face(mb, cx, cy, W, D, side) as L:
            mb.box((0, 0, z + rise * 0.45), (0.13, 0.13, rise * 0.9), "timber")
            mb.box((0, 0, z + rise * 0.5), (L * 0.5, 0.13, 0.13), "timber")
            mb.box((0, 0, z + 0.02), (L, 0.14, 0.14), "timber")
            if level >= 2:
                P.window(mb, 0.0, z + rise * 0.27, w=0.45, h=0.5, shutter=None, lit=(side == "front"))
    # The chimney.
    chx = cx + (W * 0.3 if style == 0 else W * 0.22 if style == 1 else -W * 0.25)
    P.chimney(mb, chx, cy + D * 0.22, z + rise * 0.3, top + 0.8, w=0.55, mat="brick" if level >= 3 else "stone", cap="stone_dark",
              pots=1 if level < 3 else 2)
    fy = cy - D / 2
    f0 = cy - d / 2
    if style == 2:   # A cross wing with its own gable toward the street.
        bw, bd = 2.1, 1.0
        bx, by = cx + W / 2 - bw / 2 - 0.1, f0 - bd / 2 + 0.3
        z0 = 0.5
        if level >= 3:
            P.stone_block(mb, bx, by, 0, bw, bd + 0.6, h, rnd, density=0.3)
            z0 = h
        else:
            mb.box((bx, by, 0.25), (bw + 0.16, bd + 0.76, 0.5), "stone")
        grow = 0.2 if level >= 3 else 0.0
        P.framed_block(mb, bx, by, z0, bw + grow, bd + 0.6 + grow, z - z0, infill="var_walls", spacing=1.05, cross=True)
        with mb.placed((bx, by + 0.6, 0), math.pi / 2):
            P.gable_roof(mb, 0, 0, bd + 1.8, bw + grow + 0.1, z, 1.5, ROOFV, rows=4, overhang=0.3, gable="var_walls", end_overhang=0.3)
        for k in range(floors):
            dd = bd + 0.6 + (grow if k > 0 else 0.0)
            with P.face(mb, bx, by, bw, dd, "front"):
                P.window(mb, 0, k * h + h * 0.58, w=0.7, h=0.8, shutter="var_shutter", flowers=(k == 1), lit=(k == 0))
        with P.face(mb, bx, by, bw, bd + 0.6 + grow, "front"):
            mb.box((0, 0, z + 0.65), (0.12, 0.12, 1.2), "timber")
    if not extras:
        return
    if level == 1:
        # A lean-to shed, a vegetable patch behind a wicker fence, a bench.
        x0 = cx + w / 2
        mb.box((x0 + 0.5, cy + 0.3, 0.9), (1.0, 2.0, 1.8), "plank")
        game.sloped_slab(mb, x0 - 0.05, x0 + 1.15, cy - 0.9, cy + 1.45, 1.75, 2.1, 0.08, "var_roof_dark")
        game.garden_patch(mb, -1.9, -2.1)
        game.garden_patch(mb, -0.8, -2.1)
        game.fence(mb, -2.9, -2.45, 0.2, -2.45, posts=4, h=0.6)
        mb.box((1.5, f0 - 0.3, 0.4), (1.1, 0.35, 0.07), "wood")
        for s in (-0.45, 0.45):
            mb.box((1.5 + s, f0 - 0.3, 0.2), (0.07, 0.3, 0.4), "timber")
    elif level == 2:
        # A porch over the door, a rain barrel, firewood.
        dx = -w * 0.26 if style != 1 else 0.0
        for s in (-1, 1):
            mb.box((dx + s * 0.75, f0 - 0.9, 1.15), (0.12, 0.12, 2.3), "timber")
        game.sloped_slab(mb, dx - 1.0, dx + 1.0, f0 - 1.2, f0 - 0.1, 2.2, 2.6, 0.08, "var_roof_dark")
        if style != 2:
            game.rain_barrel(mb, cx + w / 2 - 0.2, f0 - 0.45)
        game.log_pile(mb, cx - w / 2 - 0.1, cy + 0.2, length=1.0, rows=2)
        game.garden_patch(mb, 1.6 if style != 2 else -1.9, -2.3)
    elif level == 3:
        # An oriel on the upper floor, a hanging shop sign, a dormer.
        if style != 1:
            ox = cx - W * 0.28
            mb.box((ox, fy - 0.3, h + 1.35), (1.3, 0.6, 1.9), "var_walls")
            for s in (-1, 1):
                mb.box((ox + s * 0.65, fy - 0.6, h + 1.35), (0.1, 0.1, 1.9), "timber")
                P.beam(mb, (ox + s * 0.6, fy, h - 0.5), (ox + s * 0.6, fy - 0.55, h + 0.4), 0.08, "timber")
            mb.box((ox, fy - 0.62, h + 1.5), (0.9, 0.06, 0.9), "glow")
            mb.box((ox, fy - 0.66, h + 1.5), (0.05, 0.04, 0.9), "timber")
            mb.box((ox, fy - 0.66, h + 1.5), (0.9, 0.04, 0.05), "timber")
            game.sloped_slab(mb, ox - 0.8, ox + 0.8, fy - 0.75, fy + 0.05, h + 2.3, h + 2.75, 0.08, "var_roof_dark")
            if style == 0:
                P.dormer(mb, cx + 1.2, fy + 0.6, z + 0.6, w=0.9, h=0.75, depth=1.1, mats=ROOFV, walls="var_walls")
        sx = cx + W / 2 - 0.35 if style != 2 else cx - W / 2 + 0.35
        with mb.placed((sx, fy, 0), -math.pi / 2):
            P.hanging_sign(mb, rig, 0, 0, h + 1.9 if style != 2 else h - 0.4, arm=1.0, board=(0.7, 0.55))
        if style != 2:
            game.barrel(mb, cx + w / 2 - 0.3, f0 - 0.5, h=0.8, r=0.3)
            game.crate(mb, cx + w / 2 - 1.0, f0 - 0.45, s=0.5)
    else:
        # A corner turret with its own pointed roof, a balcony, a dormer and a weathercock.
        tx, ty = cx - W / 2 + 0.1, fy + 0.1
        mb.cylinder((tx, ty, h - 1.0), (tx, ty, h + 0.2), 0.15, 0.85, "timber", segments=10)
        mb.cylinder((tx, ty, h + 0.2), (tx, ty, z + 0.6), 0.85, 0.85, "var_walls", segments=10)
        for i in range(10):
            a = P.TAU * i / 10
            mb.box((tx + 0.84 * math.cos(a), ty + 0.84 * math.sin(a), (h + 0.2 + z + 0.6) / 2), (0.08, 0.1, z + 0.4 - h), "timber", rotation_z=a)
        for zz in (h + 1.4, h + 1.4 + 2.5):
            for a in (-2.2, -1.2):
                mb.box((tx + 0.86 * math.cos(a), ty + 0.86 * math.sin(a), zz), (0.12, 0.4, 0.7), "glow" if zz < h + 2 else "window", rotation_z=a)
        P.cone_roof(mb, tx, ty, z + 0.6, 0.85, 2.6, ROOFV, rows=5, seg=10, eave=0.3, finial="gold")
        if style == 0:
            bx = cx + W * 0.2
            mb.box((bx, fy - 0.45, 2 * h + 0.05), (1.6, 0.9, 0.1), "plank")
            for s in (-1, 1):
                P.beam(mb, (bx + s * 0.7, fy, 2 * h - 0.7), (bx + s * 0.7, fy - 0.8, 2 * h), 0.08, "timber")
                mb.box((bx + s * 0.75, fy - 0.85, 2 * h + 0.5), (0.07, 0.07, 0.9), "timber")
            mb.box((bx, fy - 0.85, 2 * h + 0.9), (1.6, 0.07, 0.07), "timber")
            mb.box((bx, fy - 0.85, 2 * h + 0.5), (1.5, 0.04, 0.6), "var_shutter")
            P.dormer(mb, cx + 0.9, fy + 0.6, z + 0.65, w=0.9, h=0.75, depth=1.1, mats=ROOFV, walls="var_walls")
        vx, vy = (cx + W * 0.4, cy) if style != 1 else (cx, cy + D * 0.4)
        mb.cylinder((vx, vy, top), (vx, vy, top + 0.8), 0.025, 0.025, "iron", segments=5)
        if style != 2:
            game.barrel(mb, cx + w / 2 - 0.3, f0 - 0.5, h=0.8, r=0.3)
            mb.box((cx + 1.2, f0 - 0.4, 1.9), (0.14, 0.14, 0.3), "glow")
            mb.box((cx + 1.2, f0 - 0.2, 2.1), (0.06, 0.5, 0.06), "iron")


def make(name, colors, **kw):
    def build():
        mb = P.begin()
        rig = P.Rig()
        house(mb, rig, **kw)
        P.finish(mb, name, colors, rig)
    return build


BLUE = P.palette(var_roof=0x3F5F9E, var_roof_dark=0x324B80, var_shutter=0x8E3E2A)
THATCH = P.palette(var_roof=0xC9A55A, var_roof_dark=0xA8863F)
SLATE = P.palette(var_roof=0x5A6470, var_roof_dark=0x46505A, var_walls=0xE8CFA6, var_shutter=0x3F5E8C)

MODELS = {}
for _level in (1, 2, 3, 4):
    for _style, _tag in ((0, "wide"), (1, "gabled"), (2, "wing")):
        _name = "bld_house_l%d_%s" % (_level, _tag)
        MODELS[_name] = make(_name, THATCH if _level == 1 else P.BASE, level=_level, style=_style)
MODELS["bld_house_l4_wide_blue"] = make("bld_house_l4_wide_blue", BLUE, level=4, style=0)
MODELS["bld_house_l4_gabled_blue"] = make("bld_house_l4_gabled_blue", BLUE, level=4, style=1)
MODELS["bld_house_l3_wide_slate"] = make("bld_house_l3_wide_slate", SLATE, level=3, style=0)
MODELS["bld_house_l2_gabled_blue"] = make("bld_house_l2_gabled_blue", BLUE, level=2, style=1)
MODELS["bld_house_l4_wing_blue"] = make("bld_house_l4_wing_blue", BLUE, level=4, style=2)
