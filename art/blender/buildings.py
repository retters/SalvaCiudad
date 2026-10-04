"""Buildings: one model per building of the core mod (phase 18).

Every model fills its footprint (width along X, depth along Y, in meters),
stands on Z = 0 and has its door on the -Y side, like house_small.glb.
Most are a timber-framed cottage of the right size with the tools of the
trade next to it: logs at the woodcutter's, a wheel at the mill, an anvil
at the blacksmith's, and so on.
"""

import math
import os

import common
from common import MeshBuilder

COLORS = {
    "plaster": common.rgb(0xE6DCC4),
    "plaster_warm": common.rgb(0xE8CFA6),
    "timber": common.rgb(0x5A3B24),
    "wood": common.rgb(0x8A6038),
    "wood_light": common.rgb(0xB08A5A),
    "roof": common.rgb(0x9A4A2E),
    "roof_dark": common.rgb(0x7E3A24),
    "thatch": common.rgb(0xC9A55A),
    "thatch_dark": common.rgb(0xA8863F),
    "slate": common.rgb(0x5A6470),
    "slate_dark": common.rgb(0x46505A),
    "stone": common.rgb(0x9A938A),
    "stone_dark": common.rgb(0x78726A),
    "brick": common.rgb(0xA0553A),
    "door": common.rgb(0x6B4A2E),
    "window": common.rgb(0x2B3440),
    "torch_flame": common.rgb(0xF2A63A),
    "shutter": common.rgb(0x4F6B4A),
    "log": common.rgb(0x7A5232),
    "log_end": common.rgb(0xC8A06A),
    "hay": common.rgb(0xD8B85A),
    "cloth_red": common.rgb(0xA8403A),
    "cloth_blue": common.rgb(0x3F5E8C),
    "cloth_green": common.rgb(0x4F7A44),
    "cloth_white": common.rgb(0xE8E4D8),
    "iron": common.rgb(0x44484E),
    "gold": common.rgb(0xC9A441),
    "water": common.rgb(0x4A7FA0),
    "leaves": common.rgb(0x4E7A34),
    "flowers": common.rgb(0xC86A8A),
    "flowers_y": common.rgb(0xE0C040),
    "soil": common.rgb(0x6A4A30),
    "clay": common.rgb(0xB06A48),
    "charcoal": common.rgb(0x2E2A28),
    "hide": common.rgb(0x9A7050),
    "fish": common.rgb(0x9AA8B0),
    "berries": common.rgb(0xA8243A),
    "bread": common.rgb(0xC08A48),
    "bell": common.rgb(0xB8923A),
    # Recolored per house by the game (phase 31); these are the preview colors.
    "var_roof": common.rgb(0x9A4A2E),
    "var_roof_dark": common.rgb(0x7E3A24),
    "var_walls": common.rgb(0xE6DCC4),
    "var_shutter": common.rgb(0x4F6B4A),
}


# --- Pieces ------------------------------------------------------------------------------


def sloped_slab(mb, x0, x1, y_outer, y_inner, z_outer, z_inner, thick, mat):
    """A roof slab from an eave (y_outer, z_outer) up to the ridge (y_inner, z_inner)."""
    ys = sorted((y_outer, y_inner))
    verts = mb.prism([(x0, ys[0]), (x1, ys[0]), (x1, ys[1]), (x0, ys[1])], 0.0, thick, mat)
    span = abs(y_outer - y_inner) or 1e-6
    for v in verts:
        t = abs(v.co.y - y_outer) / span
        v.co.z += z_outer + (z_inner - z_outer) * t
    return verts


def gable_roof(mb, cx, cy, w, d, wall_h, rise, overhang, mats, rows=5, gable="plaster"):
    """A two-slope roof along X over a w x d block, in alternating rows."""
    ridge = wall_h + rise
    for side in (-1, 1):
        for r in range(rows):
            t0 = r / rows
            t1 = min(1.0, (r + 1) / rows + 0.05)
            y_out = cy + side * (d / 2 + overhang) * (1 - t0)
            y_in = cy + side * (d / 2 + overhang) * (1 - t1)
            z_out = wall_h - 0.12 + (ridge - wall_h + 0.12) * t0
            z_in = wall_h - 0.12 + (ridge - wall_h + 0.12) * t1
            sloped_slab(mb, cx - w / 2 - overhang, cx + w / 2 + overhang, y_out, y_in, z_out, z_in, 0.08,
                        mats[r % len(mats)])
    for x in (cx - w / 2, cx + w / 2):
        end = mb.prism([(cy - d / 2, wall_h), (cy + d / 2, wall_h), (cy, ridge - 0.05)], x - 0.05, x + 0.05, gable)
        for v in end:
            v.co.x, v.co.y, v.co.z = v.co.z, v.co.x, v.co.y
    mb.box((cx, cy, ridge + 0.03), (w + 2 * overhang, 0.2, 0.12), mats[-1])
    return ridge


def cottage(mb, cx, cy, w, d, h, roof=("roof", "roof_dark"), walls="plaster", chimney=True, door=True,
            windows=True, rise=None, shutter="shutter", gable="plaster", chimney_x=0.28):
    """A timber-framed house block of w x d x h with its door on -Y. Returns the ridge height."""
    t = 0.14
    mb.box((cx, cy, 0.18), (w + 0.1, d + 0.1, 0.36), "stone")
    mb.box((cx, cy, 0.36 + (h - 0.36) / 2), (w, d, h - 0.36), walls)
    for x in (cx - w / 2, cx + w / 2):
        for y in (cy - d / 2, cy + d / 2):
            mb.box((x, y, 0.36 + (h - 0.36) / 2), (t, t, h - 0.36), "timber")
    for y in (cy - d / 2, cy + d / 2):
        mb.box((cx, y, 0.42), (w, t, t), "timber")
        mb.box((cx, y, h - 0.05), (w, t, t), "timber")
        if h > 2.2:
            mb.box((cx, y, h * 0.58), (w, t * 0.8, t * 0.8), "timber")
    for x in (cx - w / 2, cx + w / 2):
        mb.box((x, cy, 0.42), (t, d, t), "timber")
        mb.box((x, cy, h - 0.05), (t, d, t), "timber")
    if door:
        mb.box((cx, cy - d / 2 - 0.04, 1.1), (0.95, 0.06, 1.6), "timber")
        mb.box((cx, cy - d / 2 - 0.06, 1.05), (0.78, 0.06, 1.45), "door")
    if windows and w >= 3.0:
        for x in (cx - w * 0.32, cx + w * 0.32):
            for y, face in ((cy - d / 2, -1), (cy + d / 2, 1)):
                mb.box((x, y + face * 0.04, h * 0.62), (0.7, 0.06, 0.6), "timber")
                mb.box((x, y + face * 0.06, h * 0.62), (0.54, 0.06, 0.44), "window")
                for side in (-1, 1):
                    mb.box((x + side * 0.45, y + face * 0.06, h * 0.62), (0.24, 0.05, 0.52), shutter)
    ridge = gable_roof(mb, cx, cy, w, d, h, rise if rise is not None else max(1.2, d * 0.42), 0.35, list(roof),
                       gable=gable)
    if chimney:
        mb.box((cx + w * chimney_x, cy + d * 0.18, ridge - 0.2), (0.5, 0.5, 1.6), "stone")
        mb.box((cx + w * chimney_x, cy + d * 0.18, ridge + 0.62), (0.62, 0.62, 0.1), "stone_dark")
    return ridge


def log_pile(mb, cx, cy, length=1.8, rows=3):
    for r in range(rows):
        n = rows - r + 1
        for i in range(n):
            y = cy + (i - (n - 1) / 2) * 0.32
            z = 0.16 + r * 0.28
            mb.cylinder((cx - length / 2, y, z), (cx + length / 2, y, z), 0.15, 0.15, "log", segments=7)
            for x in (cx - length / 2, cx + length / 2):
                mb.cylinder((x - 0.01, y, z), (x + 0.01, y, z), 0.13, 0.13, "log_end", segments=7)


def barrel(mb, cx, cy, h=0.9, r=0.35, mat="wood"):
    mb.cylinder((cx, cy, 0), (cx, cy, h / 2), r * 0.85, r, mat, segments=10)
    mb.cylinder((cx, cy, h / 2), (cx, cy, h), r, r * 0.85, mat, segments=10)
    for z in (h * 0.2, h * 0.8):
        mb.cylinder((cx, cy, z - 0.03), (cx, cy, z + 0.03), r * 0.96, r * 0.96, "iron", segments=10)


def crate(mb, cx, cy, s=0.6, mat="wood_light", z=0.0, top=None):
    mb.box((cx, cy, z + s / 2), (s, s, s), mat)
    if top:
        mb.box((cx, cy, z + s + 0.06), (s * 0.8, s * 0.8, 0.12), top)


def fence(mb, x0, y0, x1, y1, posts=4, h=0.9):
    for i in range(posts + 1):
        t = i / posts
        mb.box((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, h / 2), (0.1, 0.1, h), "timber")
    for z in (h * 0.45, h * 0.85):
        mb.cylinder((x0, y0, z), (x1, y1, z), 0.04, 0.04, "wood", segments=5)


def stall(mb, cx, cy, w, cloth):
    for x in (cx - w / 2, cx + w / 2):
        for y in (cy - 0.6, cy + 0.6):
            mb.box((x, y, 1.1), (0.1, 0.1, 2.2), "timber")
    mb.box((cx, cy, 0.8), (w, 1.1, 0.1), "wood")
    sloped_slab(mb, cx - w / 2 - 0.1, cx + w / 2 + 0.1, cy - 0.85, cy + 0.7, 2.0, 2.4, 0.05, cloth)


# Walls, palisades, gates and traps follow the ground (the game's
# follows_ground): no foundations.
ON_GROUND = ("palisade", "stone_wall", "gate", "trap", "torch")
FOUNDATION_DEPTH = 4.5


def foundation(mb):
    """Stone foundations under the whole plot (phase 65).

    The game puts the floor (Z = 0) level with the ground at the door, on
    slopes of up to 4 m: downhill, this is what shows under the building.
    It stays inside the model's own outline, so the game scales it the same.
    """
    xs = [v.co.x for v in mb.bm.verts]
    ys = [v.co.y for v in mb.bm.verts]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    w, d = max(xs) - min(xs), max(ys) - min(ys)
    top = -0.05   # Just under the floor: on level ground the terrain covers it.
    mb.box((cx, cy, top - 0.2), (w, d, 0.4), "stone")
    rest = FOUNDATION_DEPTH - 0.4
    mb.box((cx, cy, top - 0.4 - rest / 2), (w - 0.2, d - 0.2, rest), "stone_dark")
    # Courses of lighter stone, a meter apart.
    for k in range(1, 4):
        mb.box((cx, cy, top - 0.4 - k * 1.0), (w - 0.08, d - 0.08, 0.1), "stone")


def export(folder, name, mb):
    if name not in ON_GROUND:
        foundation(mb)
    obj = mb.to_object(name, COLORS)
    common.export_glb(os.path.join(folder, name + ".glb"), [obj])


# --- Buildings -----------------------------------------------------------------------------


def town_center(folder):
    common.reset_scene()
    mb = MeshBuilder()
    # A long hall with a bell tower on the right.
    cottage(mb, -0.6, 0.3, 5.6, 4.6, 3.2, roof=("slate", "slate_dark"), walls="plaster_warm", chimney=True)
    mb.box((2.9, -0.3, 2.4), (1.6, 1.6, 4.8), "stone")
    for z in (0.6, 1.8, 3.0, 4.2):
        mb.box((2.9, -1.12, z), (1.66, 0.04, 0.1), "stone_dark")
    mb.box((2.9, -0.3, 5.3), (1.8, 1.8, 1.0), "timber")
    for dx, dy in ((-0.6, -0.6), (0.6, -0.6), (-0.6, 0.6), (0.6, 0.6)):
        mb.box((2.9 + dx, -0.3 + dy, 5.3), (0.14, 0.14, 1.0), "wood")
    mb.cylinder((2.9, -0.3, 4.95), (2.9, -0.3, 5.55), 0.32, 0.16, "bell", segments=10)
    pyramid = mb.prism([(2.0, -1.2), (3.8, -1.2), (3.8, 0.6), (2.0, 0.6)], 5.8, 5.85, "slate")
    for v in pyramid:
        if v.co.z > 5.82:
            v.co.x, v.co.y, v.co.z = 2.9, -0.3, 7.0
    # A flag on the hall.
    mb.cylinder((-2.9, -1.9, 0), (-2.9, -1.9, 4.2), 0.05, 0.04, "timber", segments=6)
    mb.box((-2.5, -1.9, 3.85), (0.8, 0.03, 0.5), "cloth_red")
    export(folder, "town_center", mb)


def house(folder, name, w, d, h, roof, walls="plaster"):
    common.reset_scene()
    mb = MeshBuilder()
    cottage(mb, 0, 0.2, w - 0.8, d - 1.0, h, roof=roof, walls=walls)
    # A small garden patch by the door.
    mb.box((-(w - 0.8) / 2 + 0.5, -d / 2 + 0.3, 0.1), (0.9, 0.5, 0.2), "soil")
    for i in range(3):
        mb.sphere((-(w - 0.8) / 2 + 0.2 + i * 0.3, -d / 2 + 0.3, 0.3), 0.14, "leaves", segments=6, rings=4)
    export(folder, name, mb)


VAR = {"roof": ("var_roof", "var_roof_dark"), "walls": "var_walls", "shutter": "var_shutter", "gable": "var_walls"}


def upper_windows(mb, cx, cy, w, d, z):
    """A row of small windows with shutters on the front and back, at height z."""
    for x in (cx - w * 0.3, cx, cx + w * 0.3):
        for y, face in ((cy - d / 2, -1), (cy + d / 2, 1)):
            mb.box((x, y + face * 0.04, z), (0.6, 0.06, 0.52), "timber")
            mb.box((x, y + face * 0.06, z), (0.46, 0.06, 0.38), "window")
            for side in (-1, 1):
                mb.box((x + side * 0.38, y + face * 0.06, z), (0.2, 0.05, 0.44), "var_shutter")


def garden_patch(mb, x, y):
    mb.box((x, y, 0.1), (0.9, 0.5, 0.2), "soil")
    for i in range(3):
        mb.sphere((x - 0.3 + i * 0.3, y, 0.3), 0.14, "leaves", segments=6, rings=4)


def rain_barrel(mb, x, y):
    mb.cylinder((x, y, 0), (x, y, 0.8), 0.32, 0.3, "wood", segments=8)
    for z in (0.15, 0.65):
        mb.cylinder((x, y, z), (x, y, z + 0.06), 0.33, 0.33, "iron", segments=8)


def lean_to(mb, x0, x1, y0, y1, h_low, h_high):
    """A shed against a wall: posts, a board wall and a one-slope roof."""
    mb.box(((x0 + x1) / 2, (y0 + y1) / 2, h_low / 2), (x1 - x0, y1 - y0, h_low), "wood")
    for x in (x0, x1):
        for y in (y0, y1):
            mb.box((x, y, h_low / 2), (0.12, 0.12, h_low), "timber")
    sloped_slab(mb, x0 - 0.15, x1 + 0.15, y0 - 0.2, y1, h_low, h_high, 0.08, "var_roof_dark")


def house_variant(folder, name, level, style):
    """A home at `level` (0 to 2) in one of three styles (0 to 2), made to
    fill the house footprint like house.glb. Roof, walls and shutters use the
    var_* materials, which the game recolors per house."""
    common.reset_scene()
    mb = MeshBuilder()
    w, d = 5.2, 4.0  # The main block, inside the 6 x 5 m lot.
    if level == 0:
        # A one-floor cottage.
        if style == 0:
            cottage(mb, 0, 0.2, w, d, 2.6, chimney_x=0.28, **VAR)
            garden_patch(mb, -w / 2 + 0.5, -2.2)
        elif style == 1:
            cottage(mb, 0.45, 0.2, w - 0.9, d, 2.5, chimney_x=-0.3, **VAR)
            lean_to(mb, -2.6, -1.72, -1.2, 1.4, 1.5, 2.1)
            log_pile(mb, -2.2, -1.9, length=1.2, rows=2)
        else:
            cottage(mb, 0, 0.35, w - 0.4, d - 0.3, 2.4, rise=1.9, chimney=False, **VAR)
            rain_barrel(mb, 2.3, -1.6)
            garden_patch(mb, -1.6, -2.2)
    elif level == 1:
        # Bigger: a half floor under the roof, a wing or a porch.
        if style == 0:
            cottage(mb, 0, 0.2, w, d, 3.3, chimney_x=0.3, **VAR)
            upper_windows(mb, 0, 0.2, w, d, 2.75)
            garden_patch(mb, -w / 2 + 0.5, -2.2)
        elif style == 1:
            cottage(mb, 0.6, 0.55, w - 1.2, d - 0.7, 3.0, chimney_x=0.25, **VAR)
            cottage(mb, -1.95, -0.45, 1.8, 2.8, 2.4, door=False, windows=False, chimney=False, rise=1.0,
                    **VAR)
            rain_barrel(mb, 2.5, -1.7)
        else:
            cottage(mb, 0, 0.5, w, d - 0.6, 3.1, chimney_x=-0.3, **VAR)
            # A porch roof over the door, on two posts, with a bench.
            for x in (-1.0, 1.0):
                mb.box((x, -2.1, 1.1), (0.14, 0.14, 2.2), "timber")
            sloped_slab(mb, -1.3, 1.3, -2.35, -1.45, 2.15, 2.55, 0.08, "var_roof_dark")
            mb.box((1.6, -1.8, 0.25), (1.0, 0.35, 0.08), "wood")
            for x in (1.2, 2.0):
                mb.box((x, -1.8, 0.12), (0.08, 0.3, 0.24), "wood")
    else:
        # Two floors.
        if style == 0:
            # Stone below, plaster above.
            mb.box((0, 0.2, 1.1), (w + 0.1, d + 0.1, 2.2), "stone")
            mb.box((0, -d / 2 + 0.16, 0.95), (0.95, 0.06, 1.7), "timber")
            mb.box((0, -d / 2 + 0.14, 0.9), (0.78, 0.06, 1.55), "door")
            for x in (-1.6, 1.6):
                mb.box((x, -d / 2 + 0.14, 1.3), (0.6, 0.06, 0.6), "window")
            # The upper floor on the stone one: a cottage block raised 2.2 m.
            before = set(mb.bm.verts)
            cottage(mb, 0, 0.2, w + 0.3, d + 0.3, 2.3, door=False, windows=False, chimney=False, **VAR)
            for v in mb.bm.verts:
                if v not in before:
                    v.co.z += 2.2
            upper_windows(mb, 0, 0.2, w + 0.3, d + 0.3, 3.4)
            mb.box((w * 0.3, 0.9, 5.3), (0.55, 0.55, 3.2), "stone")
        elif style == 1:
            cottage(mb, -0.35, 0.2, w - 0.7, d, 4.2, chimney_x=-0.3, **VAR)
            upper_windows(mb, -0.35, 0.2, w - 0.7, d, 3.2)
            # A stone chimney stack on the right end.
            mb.box((2.55, 0.2, 3.0), (0.8, 1.2, 6.0), "stone")
            mb.box((2.55, 0.2, 6.05), (0.95, 1.35, 0.12), "stone_dark")
        else:
            cottage(mb, 0.5, 0.6, w - 1.0, d - 0.8, 4.0, chimney_x=0.25, **VAR)
            upper_windows(mb, 0.5, 0.6, w - 1.0, d - 0.8, 3.0)
            cottage(mb, -1.9, -0.35, 2.0, 3.0, 2.6, door=True, windows=False, chimney=False, rise=1.1, **VAR)
            garden_patch(mb, 1.8, -2.2)
    export(folder, name, mb)


def storehouse(folder, name, w, d, food=False):
    common.reset_scene()
    mb = MeshBuilder()
    # A barn on stone pillars with wide doors; sacks and crates outside.
    for x in (-w / 2 + 0.8, 0, w / 2 - 0.8):
        for y in (-d / 2 + 1.2, d / 2 - 0.6):
            mb.box((x, y, 0.25), (0.4, 0.4, 0.5), "stone")
    mb.box((0, 0.3, 0.55), (w - 1.0, d - 1.6, 0.1), "wood")
    mb.box((0, 0.3, 0.6 + 1.4), (w - 1.0, d - 1.6, 2.8), "wood")
    for x in range(int((w - 1.0) / 0.5) + 1):
        xx = -(w - 1.0) / 2 + x * 0.5
        for y in (-(d - 1.6) / 2 + 0.3 - 0.02, (d - 1.6) / 2 + 0.3 + 0.02):
            mb.box((xx, y, 2.0), (0.06, 0.04, 2.8), "timber")
    mb.box((0, -(d - 1.6) / 2 + 0.3 - 0.05, 1.6), (1.8, 0.06, 2.0), "door")
    mb.box((0, -(d - 1.6) / 2 + 0.3 - 0.07, 1.6), (0.06, 0.06, 2.0), "timber")
    gable_roof(mb, 0, 0.3, w - 1.0, d - 1.6, 3.4, 1.8, 0.4, ["thatch", "thatch_dark"] if food else ["roof", "roof_dark"])
    if food:
        for i in range(3):
            barrel(mb, -w / 2 + 0.6 + i * 0.75, -d / 2 + 0.45, h=0.7, r=0.28)
    else:
        crate(mb, w / 2 - 0.6, -d / 2 + 0.5)
        crate(mb, w / 2 - 1.3, -d / 2 + 0.5, s=0.5)
        crate(mb, w / 2 - 0.6, -d / 2 + 0.5, s=0.45, z=0.6)
    export(folder, name, mb)


def workshop(folder, name, w, d, extras, roof=("roof", "roof_dark"), walls="plaster", chimney=True):
    """A cottage at the back of the plot and the trade's yard in front."""
    common.reset_scene()
    mb = MeshBuilder()
    bw, bd = w - 0.6, d * 0.55
    cy = d / 2 - bd / 2 - 0.2
    cottage(mb, 0, cy, bw, bd, 2.4, roof=roof, walls=walls, chimney=chimney, rise=1.1)
    extras(mb, w, d)
    export(folder, name, mb)


def woodcutter_yard(mb, w, d):
    log_pile(mb, -0.6, -d / 2 + 0.7, length=2.0)
    mb.cylinder((1.3, -d / 2 + 0.8, 0), (1.3, -d / 2 + 0.8, 0.5), 0.3, 0.3, "log", segments=8)
    mb.box((1.3, -d / 2 + 0.8, 0.85), (0.05, 0.12, 0.6), "wood")  # An axe.
    mb.box((1.3, -d / 2 + 0.8, 0.62), (0.2, 0.05, 0.14), "iron")


def forager_yard(mb, w, d):
    for i, (x, y) in enumerate(((-1.2, -d / 2 + 0.6), (-0.4, -d / 2 + 0.8), (0.8, -d / 2 + 0.6))):
        mb.cylinder((x, y, 0), (x, y, 0.35), 0.25, 0.3, "wood_light", segments=8)
        mb.sphere((x, y, 0.35), 0.24, "berries" if i % 2 == 0 else "leaves", segments=7, rings=4, scale=(1, 1, 0.5))


def stonecutter_yard(mb, w, d):
    for i, (x, y, s) in enumerate(((-1.2, -d / 2 + 0.7, 0.6), (-0.4, -d / 2 + 0.6, 0.5), (-0.8, -d / 2 + 0.7, 0.45))):
        mb.box((x, y, s / 2 + (0.6 if i == 2 else 0)), (s, s * 0.8, s), "stone")
    mb.box((1.2, -d / 2 + 0.8, 0.35), (0.9, 0.7, 0.7), "stone_dark")


def splitter_yard(mb, w, d):
    mb.cylinder((-1.2, -d / 2 + 0.7, 0), (-1.2, -d / 2 + 0.7, 0.45), 0.28, 0.28, "log", segments=8)
    for r in range(3):
        for i in range(5 - r):
            mb.box((0.2 + i * 0.3 + r * 0.15, -d / 2 + 0.6, 0.12 + r * 0.22), (0.26, 0.9, 0.2), "log_end" if i % 2 else "log")


def farm_yard(mb, w, d):
    for i in range(2):
        mb.cylinder((-1.4 + i * 0.9, -d / 2 + 0.7, 0), (-1.4 + i * 0.9, -d / 2 + 0.7, 0.8), 0.4, 0.3, "hay", segments=9)
    mb.box((1.2, -d / 2 + 0.8, 0.3), (1.1, 0.6, 0.12), "wood")  # A cart bed.
    for x in (0.8, 1.6):
        mb.cylinder((x, -d / 2 + 0.45, 0.3), (x, -d / 2 + 0.43, 0.3), 0.3, 0.3, "wood", segments=10)
    fence(mb, -w / 2 + 0.2, -d / 2 + 0.1, -w / 2 + 0.2, d / 2 - 0.2, posts=3)


def orchard_yard(mb, w, d):
    for x in (-1.4, 1.2):
        mb.cylinder((x, -d / 2 + 0.8, 0), (x, -d / 2 + 0.8, 1.0), 0.1, 0.08, "log", segments=6)
        mb.sphere((x, -d / 2 + 0.8, 1.5), 0.65, "leaves", segments=8, rings=5)
        for k in range(4):
            a = k * 1.6
            mb.sphere((x + 0.55 * math.cos(a), -d / 2 + 0.8 + 0.55 * math.sin(a), 1.3), 0.08, "berries", segments=5, rings=3)
    crate(mb, 0, -d / 2 + 0.5, s=0.5, top="berries")


def hunter_yard(mb, w, d):
    for x in (-1.4, -0.2):
        mb.box((x, -d / 2 + 0.7, 0.8), (0.08, 0.08, 1.6), "timber")
    mb.cylinder((-1.45, -d / 2 + 0.7, 1.5), (-0.15, -d / 2 + 0.7, 1.5), 0.04, 0.04, "wood", segments=5)
    mb.box((-0.8, -d / 2 + 0.72, 1.05), (0.8, 0.03, 0.85), "hide")
    mb.box((1.2, -d / 2 + 0.7, 0.35), (0.7, 0.5, 0.7), "wood_light")


def explorer_yard(mb, w, d):
    # A signpost, a table with a map on it, travel packs and a pennant.
    y = -d / 2 + 0.7
    mb.box((1.7, y, 1.0), (0.1, 0.1, 2.0), "timber")
    mb.box((1.95, y, 1.75), (0.6, 0.04, 0.18), "wood_light")
    mb.box((1.45, y, 1.45), (0.6, 0.04, 0.18), "wood_light")
    mb.box((-1.0, y, 0.72), (1.0, 0.6, 0.06), "wood")
    for dx in (-0.42, 0.42):
        for dy in (-0.22, 0.22):
            mb.box((-1.0 + dx, y + dy, 0.35), (0.07, 0.07, 0.7), "timber")
    mb.box((-1.0, y, 0.76), (0.7, 0.42, 0.02), "cloth_white")
    crate(mb, 0.35, y - 0.1, 0.45)
    mb.sphere((0.9, y, 0.24), 0.26, "hide", segments=6, rings=4)
    mb.cylinder((-2.0, y, 0), (-2.0, y, 3.0), 0.05, 0.04, "timber", segments=6)
    mb.box((-1.65, y, 2.7), (0.7, 0.03, 0.4), "cloth_green")


def fisher_yard(mb, w, d):
    hull = mb.prism([(-1.0, -0.3), (1.0, -0.3), (1.3, 0.0), (1.0, 0.3), (-1.0, 0.3), (-1.3, 0.0)], 0.0, 0.35, "wood")
    for v in hull:
        v.co.y += -d / 2 + 0.6
        v.co.x += -0.6
    for x in (1.0, 1.8):
        mb.box((x, -d / 2 + 0.7, 0.7), (0.08, 0.08, 1.4), "timber")
    mb.cylinder((0.95, -d / 2 + 0.7, 1.3), (1.85, -d / 2 + 0.7, 1.3), 0.03, 0.03, "wood", segments=5)
    for k in range(4):
        mb.box((1.1 + k * 0.2, -d / 2 + 0.7, 1.1), (0.08, 0.03, 0.35), "fish")


def herbalist_yard(mb, w, d):
    for i in range(3):
        x = -1.0 + i * 0.8
        mb.cylinder((x, -d / 2 + 0.5, 0), (x, -d / 2 + 0.5, 0.35), 0.2, 0.24, "clay", segments=8)
        mb.sphere((x, -d / 2 + 0.5, 0.45), 0.2, "leaves", segments=6, rings=4)
        mb.sphere((x + 0.08, -d / 2 + 0.45, 0.58), 0.07, "flowers", segments=5, rings=3)


def compost_yard(mb, w, d):
    for i in range(3):
        x = -1.4 + i * 1.3
        for side in (-0.5, 0.5):
            mb.box((x + side, -d / 2 + 1.0, 0.4), (0.06, 1.0, 0.8), "wood")
        mb.box((x, -d / 2 + 0.5, 0.4), (1.0, 0.06, 0.8), "wood")
        mb.box((x, -d / 2 + 1.0, 0.3), (0.95, 0.95, 0.6), "soil")


def mill_extras(mb, w, d):
    # A windmill: a round stone tower in front with four sails.
    x, y = -0.2, -d / 2 + 1.2
    mb.cylinder((x, y, 0), (x, y, 4.2), 1.1, 0.8, "stone", segments=12)
    mb.cylinder((x, y, 4.2), (x, y, 5.2), 0.95, 0.1, "thatch", segments=12)
    hub = (x, y - 0.95, 3.8)
    mb.cylinder((x, y - 0.6, 3.8), hub, 0.12, 0.12, "timber", segments=6)
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        tip = (x + 2.2 * math.cos(a), y - 0.97, 3.8 + 2.2 * math.sin(a))
        mb.cylinder(hub, tip, 0.05, 0.05, "timber", segments=4)
        # The sail: a flat cloth along the outer part of the arm.
        start = (x + 0.6 * math.cos(a), y - 1.0, 3.8 + 0.6 * math.sin(a))
        mb.cylinder(start, tip, 0.24, 0.24, "cloth_white", segments=4)


def bakery_yard(mb, w, d):
    mb.sphere((1.2, -d / 2 + 0.9, 0.2), 0.8, "brick", segments=10, rings=6, scale=(1, 1, 0.8))
    mb.box((1.2, -d / 2 + 0.15, 0.35), (0.4, 0.1, 0.4), "charcoal")
    crate(mb, -1.0, -d / 2 + 0.5, s=0.5, top="bread")


def brewery_yard(mb, w, d):
    for i in range(3):
        barrel(mb, -1.4 + i * 0.75, -d / 2 + 0.5)
    barrel(mb, -1.0, -d / 2 + 0.5, h=0.8, r=0.33)
    mb.cylinder((1.2, -d / 2 + 0.8, 0), (1.2, -d / 2 + 0.8, 1.0), 0.6, 0.6, "iron", segments=12)


def tannery_yard(mb, w, d):
    for i in range(3):
        x = -1.4 + i * 1.0
        mb.cylinder((x, -d / 2 + 0.6, 0), (x, -d / 2 + 0.6, 0.5), 0.4, 0.42, "wood", segments=10)
        mb.cylinder((x, -d / 2 + 0.6, 0.45), (x, -d / 2 + 0.6, 0.47), 0.36, 0.36, "clay" if i % 2 else "soil", segments=10)
    mb.box((1.6, -d / 2 + 0.7, 0.7), (0.06, 0.06, 1.4), "timber")
    mb.box((1.6, -d / 2 + 0.72, 1.0), (0.03, 0.7, 0.7), "hide")


def weaver_yard(mb, w, d):
    for x in (-1.2, 0.0):
        for y in (-d / 2 + 0.4, -d / 2 + 1.1):
            mb.box((x, y, 0.6), (0.08, 0.08, 1.2), "timber")
    mb.box((-0.6, -d / 2 + 0.75, 0.9), (1.2, 0.7, 0.05), "cloth_white")
    for i, c in enumerate(("cloth_red", "cloth_blue", "cloth_green")):
        mb.cylinder((1.0 + i * 0.35, -d / 2 + 0.5, 0.15), (1.0 + i * 0.35, -d / 2 + 1.0, 0.15), 0.14, 0.14, c, segments=8)


def tailor_yard(mb, w, d):
    mb.box((-0.9, -d / 2 + 0.5, 0.45), (1.6, 0.6, 0.9), "wood_light")
    for i, c in enumerate(("cloth_blue", "cloth_red", "cloth_green")):
        mb.box((-1.4 + i * 0.5, -d / 2 + 0.5, 0.95), (0.4, 0.45, 0.1), c)
    mb.box((1.3, -d / 2 + 0.5, 1.1), (0.08, 0.08, 2.2), "timber")
    mb.box((1.3, -d / 2 + 0.45, 1.75), (0.7, 0.05, 0.45), "cloth_blue")


def cobbler_yard(mb, w, d):
    mb.box((-0.8, -d / 2 + 0.5, 0.4), (1.2, 0.6, 0.8), "wood_light")
    for i in range(3):
        mb.box((-1.2 + i * 0.35, -d / 2 + 0.5, 0.9), (0.26, 0.12, 0.16), "hide")
    mb.box((1.2, -d / 2 + 0.1, 2.0), (0.7, 0.05, 0.4), "wood")  # A sign.
    mb.box((1.2, -d / 2 + 0.08, 2.0), (0.3, 0.05, 0.15), "hide")


def clay_pit_yard(mb, w, d):
    mb.prism([(-1.8, -d / 2 + 0.2), (0.4, -d / 2 + 0.2), (0.4, -d / 2 + 1.6), (-1.8, -d / 2 + 1.6)], 0.0, 0.05, "clay")
    mb.sphere((1.3, -d / 2 + 0.8, 0.0), 0.7, "clay", segments=8, rings=5, scale=(1, 1, 0.6))
    mb.box((0.8, -d / 2 + 0.4, 0.3), (0.06, 0.06, 0.6), "wood")


def kiln_yard(mb, w, d):
    mb.sphere((-0.8, -d / 2 + 1.0, 0.0), 1.1, "brick", segments=12, rings=7, scale=(1, 1, 1.1))
    mb.box((-0.8, -d / 2 - 0.05, 0.35), (0.5, 0.2, 0.6), "charcoal")
    for r in range(2):
        for i in range(3):
            mb.box((1.1 + i * 0.3, -d / 2 + 0.6, 0.1 + r * 0.2), (0.26, 0.5, 0.18), "brick")


def charcoal_yard(mb, w, d):
    mb.sphere((-0.4, -d / 2 + 1.0, 0.0), 1.3, "charcoal", segments=12, rings=7, scale=(1, 1, 0.7))
    mb.sphere((-0.4, -d / 2 + 1.0, 0.0), 1.32, "soil", segments=8, rings=4, scale=(1, 1, 0.3))
    log_pile(mb, 1.4, -d / 2 + 0.6, length=1.0, rows=2)


def mine_extras(mb, w, d):
    # A timber-framed entrance into a mound of rock.
    mb.sphere((0, d / 2 - 1.2, 0.0), 2.4, "stone_dark", segments=12, rings=7, scale=(1.1, 0.9, 0.9))
    for x in (-0.8, 0.8):
        mb.box((x, -0.2, 1.1), (0.25, 0.25, 2.2), "timber")
    mb.box((0, -0.2, 2.25), (2.0, 0.3, 0.3), "timber")
    mb.box((0, 0.05, 1.05), (1.3, 0.1, 2.0), "charcoal")
    mb.box((1.6, -d / 2 + 0.6, 0.3), (0.8, 0.5, 0.35), "wood")
    mb.sphere((1.6, -d / 2 + 0.6, 0.5), 0.3, "clay", segments=6, rings=4, scale=(1.2, 0.8, 0.5))


def smelter_yard(mb, w, d):
    mb.cylinder((-1.0, -d / 2 + 1.0, 0), (-1.0, -d / 2 + 1.0, 3.4), 0.9, 0.6, "stone", segments=10)
    mb.cylinder((-1.0, -d / 2 + 1.0, 3.4), (-1.0, -d / 2 + 1.0, 3.6), 0.7, 0.7, "stone_dark", segments=10)
    mb.box((-1.0, -d / 2 + 0.1, 0.4), (0.5, 0.2, 0.5), "charcoal")
    log_pile(mb, 1.2, -d / 2 + 0.6, length=1.0, rows=2)


def blacksmith_yard(mb, w, d):
    mb.box((-1.0, -d / 2 + 0.8, 0.45), (1.0, 0.9, 0.9), "stone")
    mb.box((-1.0, -d / 2 + 0.8, 0.92), (0.7, 0.6, 0.06), "charcoal")
    mb.cylinder((0.8, -d / 2 + 0.7, 0), (0.8, -d / 2 + 0.7, 0.5), 0.25, 0.25, "log", segments=8)
    mb.box((0.8, -d / 2 + 0.7, 0.62), (0.55, 0.22, 0.2), "iron")
    mb.box((1.1, -d / 2 + 0.7, 0.64), (0.2, 0.12, 0.12), "iron")


def smokehouse_yard(mb, w, d):
    mb.box((-0.8, -d / 2 + 0.8, 0.9), (1.2, 1.0, 1.8), "stone")
    mb.box((-0.8, -d / 2 + 0.8, 1.9), (1.3, 1.1, 0.15), "slate")
    mb.box((-0.8, -d / 2 + 0.25, 0.8), (0.5, 0.06, 1.0), "door")
    crate(mb, 1.0, -d / 2 + 0.5, s=0.5, top="hide")


def bowyer_yard(mb, w, d):
    mb.box((-0.8, -d / 2 + 0.5, 0.45), (1.4, 0.6, 0.9), "wood_light")
    for i in range(4):
        x = -1.3 + i * 0.3
        arc = [(x, -d / 2 + 0.5, 0.9 + 0.8 * k / 6 * 2) for k in range(7)]
        for a, b in zip(arc, arc[1:]):
            bend = 0.12 * math.sin(math.pi * (a[2] - 0.9) / 1.6)
            mb.cylinder((a[0] + bend, a[1], a[2]), (b[0] + 0.12 * math.sin(math.pi * (b[2] - 0.9) / 1.6), b[1], b[2]),
                        0.025, 0.025, "wood", segments=4)
    mb.box((1.2, -d / 2 + 0.5, 0.6), (0.06, 0.06, 1.2), "timber")
    mb.sphere((1.2, -d / 2 + 0.45, 1.25), 0.3, "hay", segments=8, rings=5)  # A target.
    mb.sphere((1.2, -d / 2 + 0.2, 1.25), 0.12, "cloth_red", segments=6, rings=4, scale=(1, 0.3, 1))


def armory_yard(mb, w, d):
    blacksmith_yard(mb, w, d)
    for i in range(3):
        mb.box((1.6 + (i - 1) * 0.15, -d / 2 + 1.2, 0.8), (0.04, 0.04, 1.6), "wood")
        mb.cylinder((1.6 + (i - 1) * 0.15, -d / 2 + 1.2, 1.6), (1.6 + (i - 1) * 0.15, -d / 2 + 1.2, 1.85), 0.05, 0.0,
                    "iron", segments=4)


def well(folder):
    common.reset_scene()
    mb = MeshBuilder()
    mb.cylinder((0, 0, 0), (0, 0, 0.8), 0.8, 0.8, "stone", segments=12)
    mb.cylinder((0, 0, 0.78), (0, 0, 0.8), 0.62, 0.62, "water", segments=12)
    for x in (-0.75, 0.75):
        mb.box((x, 0, 1.3), (0.12, 0.12, 1.4), "timber")
    mb.cylinder((-0.8, 0, 1.6), (0.8, 0, 1.6), 0.08, 0.08, "wood", segments=6)
    mb.box((0, 0, 1.6 - 0.45), (0.02, 0.02, 0.9), "wood")
    barrel(mb, 0, 0, h=0.3, r=0.16)
    gable_roof(mb, 0, 0, 1.6, 1.3, 2.0, 0.6, 0.15, ["roof", "roof_dark"], rows=2)
    export(folder, "well", mb)


def chapel(folder):
    common.reset_scene()
    mb = MeshBuilder()
    cottage(mb, 0, 0.8, 4.4, 5.6, 3.4, roof=("slate", "slate_dark"), walls="plaster_warm", chimney=False,
            windows=False, rise=2.2)
    for y in (-0.8, 0.8, 2.4):
        for x in (-2.24, 2.24):
            mb.box((x, y, 2.0), (0.06, 0.4, 1.1), "window")
    # A bell tower at the front with a spire.
    mb.box((0, -2.8, 2.6), (1.6, 1.6, 5.2), "stone")
    mb.box((0, -3.62, 1.1), (0.8, 0.06, 1.6), "door")
    spire = mb.prism([(-0.9, -3.7), (0.9, -3.7), (0.9, -1.9), (-0.9, -1.9)], 5.2, 5.25, "slate_dark")
    for v in spire:
        if v.co.z > 5.22:
            v.co.x, v.co.y, v.co.z = 0.0, -2.8, 7.8
    mb.box((0, -2.8, 8.1), (0.06, 0.06, 0.6), "gold")
    mb.box((0, -2.8, 8.2), (0.35, 0.06, 0.06), "gold")
    export(folder, "chapel", mb)


def tavern(folder):
    common.reset_scene()
    mb = MeshBuilder()
    cottage(mb, 0, 0.6, 5.2, 4.2, 3.0, walls="plaster_warm")
    for x in (-1.6, 1.6):
        mb.box((x, -2.3, 0.4), (1.1, 0.5, 0.06), "wood")  # Tables outside.
        mb.box((x, -2.3, 0.2), (0.1, 0.1, 0.4), "timber")
    barrel(mb, 2.4, -2.4, h=0.8, r=0.3)
    mb.box((-2.3, -1.6, 2.4), (0.06, 0.9, 0.06), "timber")
    mb.box((-2.3, -2.05, 2.0), (0.04, 0.5, 0.5), "wood")  # The sign.
    mb.cylinder((-2.3, -2.05, 1.95), (-2.3, -2.05, 2.15), 0.12, 0.12, "gold", segments=8)
    export(folder, "tavern", mb)


def market(folder):
    common.reset_scene()
    mb = MeshBuilder()
    stall(mb, -2.2, -1.0, 2.6, "cloth_red")
    stall(mb, 2.2, -1.0, 2.6, "cloth_blue")
    stall(mb, 0, 1.6, 3.0, "cloth_green")
    for x, y, top in ((-2.8, -0.9, "berries"), (-1.8, -0.9, "bread"), (2.0, -0.9, "fish"), (2.8, -0.9, "cloth_white"),
                      (-0.6, 1.7, "hide"), (0.6, 1.7, "hay")):
        crate(mb, x, y, s=0.4, z=0.85, top=top)
    barrel(mb, 3.6, 2.2, h=0.8, r=0.3)
    barrel(mb, -3.6, 2.2, h=0.8, r=0.3)
    export(folder, "market", mb)


def garden(folder):
    common.reset_scene()
    mb = MeshBuilder()
    mb.box((0, 0, 0.05), (2.8, 2.8, 0.1), "soil")
    for i in range(9):
        x = -1.0 + (i % 3) * 1.0
        y = -1.0 + (i // 3) * 1.0
        mb.sphere((x, y, 0.25), 0.32, "leaves", segments=7, rings=4)
        mb.sphere((x + 0.1, y - 0.1, 0.5), 0.1, "flowers" if i % 2 else "flowers_y", segments=5, rings=3)
    fence(mb, -1.4, -1.4, 1.4, -1.4, posts=4, h=0.5)
    fence(mb, -1.4, 1.4, 1.4, 1.4, posts=4, h=0.5)
    export(folder, "garden", mb)


def campfire(folder):
    """A ring of stones with logs leaning together; the game adds the flames and the smoke."""
    common.reset_scene()
    mb = MeshBuilder()
    mb.cylinder((0, 0, 0), (0, 0, 0.06), 0.85, 0.85, "soil", segments=10)
    for i in range(9):
        a = i * 2 * math.pi / 9
        mb.sphere((0.62 * math.cos(a), 0.62 * math.sin(a), 0.12), 0.17, "stone" if i % 2 else "stone_dark",
                  segments=6, rings=4, scale=(1.0, 1.0, 0.75))
    for i in range(5):
        a = i * 2 * math.pi / 5 + 0.3
        mb.cylinder((0.42 * math.cos(a), 0.42 * math.sin(a), 0.08), (0.04 * math.cos(a), 0.04 * math.sin(a), 0.62),
                    0.07, 0.05, "log", segments=6)
    mb.cylinder((0, 0, 0.05), (0, 0, 0.14), 0.3, 0.26, "charcoal", segments=8)
    # A log to sit on.
    mb.cylinder((-0.7, -0.88, 0.14), (0.7, -0.88, 0.14), 0.14, 0.14, "log", segments=7)
    export(folder, "campfire", mb)


def torch(folder):
    """A standing torch (phase 69): a post in a few stones with a burning head, which glows at night."""
    common.reset_scene()
    mb = MeshBuilder()
    for i in range(5):
        a = i * 2 * math.pi / 5
        mb.sphere((0.2 * math.cos(a), 0.2 * math.sin(a), 0.07), 0.12, "stone" if i % 2 else "stone_dark",
                  segments=6, rings=4, scale=(1.0, 1.0, 0.7))
    mb.cylinder((0, 0, 0), (0, 0, 2.1), 0.07, 0.055, "log", segments=6)
    # The head: a wrapped bundle, and the flame over it.
    mb.cylinder((0, 0, 2.0), (0, 0, 2.3), 0.09, 0.13, "timber", segments=6)
    mb.cylinder((0, 0, 2.3), (0, 0, 2.5), 0.12, 0.09, "torch_flame", segments=6)
    mb.cylinder((0, 0, 2.5), (0.03, 0, 2.78), 0.09, 0.0, "torch_flame", segments=5)
    export(folder, "torch", mb)


def statue(folder):
    common.reset_scene()
    mb = MeshBuilder()
    mb.box((0, 0, 0.3), (2.4, 2.4, 0.6), "stone")
    mb.box((0, 0, 0.9), (1.2, 1.2, 0.6), "stone_dark")
    # A robed figure holding a staff.
    mb.cylinder((0, 0, 1.2), (0, 0, 2.6), 0.45, 0.28, "stone", segments=10)
    mb.sphere((0, 0, 2.85), 0.25, "stone", segments=8, rings=6)
    mb.cylinder((0.45, -0.1, 1.2), (0.45, -0.1, 3.4), 0.05, 0.05, "stone_dark", segments=6)
    mb.cylinder((0.25, 0, 2.3), (0.45, -0.1, 2.3), 0.09, 0.08, "stone", segments=6)
    export(folder, "statue", mb)


def bathhouse(folder):
    common.reset_scene()
    mb = MeshBuilder()
    cottage(mb, 0, 0.4, 5.2, 3.4, 2.6, roof=("slate", "slate_dark"), walls="plaster_warm")
    mb.box((0, -1.9, 0.15), (3.6, 1.0, 0.3), "stone")
    mb.box((0, -1.9, 0.29), (3.2, 0.7, 0.02), "water")
    export(folder, "bathhouse", mb)


def healer(folder, name, w, d, tier2=False):
    common.reset_scene()
    mb = MeshBuilder()
    cottage(mb, 0, 0.3, w - 0.8, d - 1.4, 2.6 if not tier2 else 3.0,
            roof=("slate", "slate_dark") if tier2 else ("thatch", "thatch_dark"), walls="plaster_warm")
    herbalist_yard(mb, w, d)
    mb.box((w / 2 - 0.5, -d / 2 + 0.2, 1.6), (0.06, 0.06, 1.6), "timber")
    mb.box((w / 2 - 0.5, -d / 2 + 0.18, 2.2), (0.5, 0.05, 0.5), "cloth_white")
    mb.box((w / 2 - 0.5, -d / 2 + 0.15, 2.2), (0.3, 0.05, 0.08), "cloth_red")
    mb.box((w / 2 - 0.5, -d / 2 + 0.15, 2.2), (0.08, 0.05, 0.3), "cloth_red")
    export(folder, name, mb)


def trading_post(folder):
    common.reset_scene()
    mb = MeshBuilder()
    cottage(mb, 0, 1.2, 5.6, 3.4, 2.8, walls="plaster_warm")
    stall(mb, -1.5, -1.8, 2.4, "cloth_red")
    for x in (0.8, 1.5, 2.2):
        crate(mb, x, -2.4, s=0.55)
    barrel(mb, 2.2, -1.6, h=0.8, r=0.3)
    mb.cylinder((-3.0, -3.0, 0), (-3.0, -3.0, 3.2), 0.05, 0.04, "timber", segments=6)
    mb.box((-2.6, -3.0, 2.9), (0.8, 0.03, 0.5), "cloth_blue")
    export(folder, "trading_post", mb)


def vault(folder):
    """A squat stone strongroom with an iron-bound door and a gold seal (phase 28)."""
    common.reset_scene()
    mb = MeshBuilder()
    mb.box((0, 0.3, 0.2), (4.4, 3.8, 0.4), "stone_dark")
    mb.box((0, 0.3, 1.6), (4.0, 3.4, 2.8), "stone")
    for z in (0.9, 1.6, 2.3):  # Courses of the masonry.
        mb.box((0, -1.42, z), (4.02, 0.04, 0.06), "stone_dark")
    for x in (-2.0, 2.0):  # Buttresses at the corners.
        for y in (-1.4, 2.0):
            mb.box((x, y, 1.4), (0.5, 0.5, 2.8), "stone_dark")
    mb.box((0, 0.3, 3.1), (4.3, 3.7, 0.2), "stone_dark")
    gable_roof(mb, 0, 0.3, 4.0, 3.4, 3.2, 1.0, 0.25, ["slate", "slate_dark"], rows=3)
    # The door: planks under iron bands, with a round seal.
    mb.box((0, -1.46, 1.05), (1.1, 0.08, 1.7), "door")
    for z in (0.5, 1.05, 1.6):
        mb.box((0, -1.52, z), (1.14, 0.04, 0.1), "iron")
    mb.cylinder((0, -1.56, 1.9), (0, -1.5, 1.9), 0.16, 0.16, "gold", segments=10)
    for x in (-1.3, 1.3):  # Barred slits.
        mb.box((x, -1.46, 2.1), (0.2, 0.06, 0.5), "window")
        mb.box((x, -1.5, 2.1), (0.04, 0.04, 0.5), "iron")
    for x, y in ((1.5, -2.0), (1.9, -1.9)):  # Chests by the door.
        crate(mb, x, y, s=0.4, mat="wood", top="gold")
    export(folder, "vault", mb)


def palisade(folder):
    common.reset_scene()
    mb = MeshBuilder()
    for i in range(5):
        x = -0.8 + i * 0.4
        mb.cylinder((x, 0, 0), (x, 0, 2.4), 0.19, 0.19, "log", segments=7)
        mb.cylinder((x, 0, 2.4), (x, 0, 2.8), 0.19, 0.0, "log_end", segments=7)
    mb.box((0, 0.22, 1.6), (2.0, 0.08, 0.14), "timber")
    export(folder, "palisade", mb)


def stone_wall(folder):
    common.reset_scene()
    mb = MeshBuilder()
    mb.box((0, 0, 1.3), (2.0, 1.2, 2.6), "stone")
    for i in range(3):
        mb.box((-0.7 + i * 0.7, 0, 2.8), (0.45, 1.2, 0.4), "stone_dark")
    for z in (0.7, 1.5):
        mb.box((0, -0.61, z), (2.0, 0.02, 0.06), "stone_dark")
    export(folder, "stone_wall", mb)


def gate(folder):
    common.reset_scene()
    mb = MeshBuilder()
    for x in (-1.75, 1.75):
        mb.box((x, 0, 1.8), (0.5, 0.6, 3.6), "log")
        mb.box((x, 0, 3.7), (0.6, 0.7, 0.2), "timber")
    mb.box((0, 0, 3.3), (4.0, 0.4, 0.3), "timber")
    for x in (-0.75, 0.75):
        mb.box((x, -0.05, 1.3), (1.45, 0.12, 2.6), "wood")
        for z in (0.6, 2.0):
            mb.box((x, -0.12, z), (1.45, 0.04, 0.12), "iron")
    export(folder, "gate", mb)


def watchtower(folder):
    common.reset_scene()
    mb = MeshBuilder()
    for x in (-1.2, 1.2):
        for y in (-1.2, 1.2):
            mb.cylinder((x, y, 0), (x * 0.85, y * 0.85, 5.0), 0.16, 0.13, "log", segments=7)
    for z in (1.6, 3.2):
        for s in (-1, 1):
            mb.box((0, s * 1.1, z), (2.3, 0.08, 0.1), "timber")
            mb.box((s * 1.1, 0, z), (0.08, 2.3, 0.1), "timber")
    mb.box((0, 0, 5.05), (2.8, 2.8, 0.15), "wood")
    for s in (-1, 1):
        mb.box((0, s * 1.35, 5.6), (2.8, 0.1, 1.0), "wood")
        mb.box((s * 1.35, 0, 5.6), (0.1, 2.8, 1.0), "wood")
    for x in (-1.3, 1.3):
        for y in (-1.3, 1.3):
            mb.box((x, y, 6.6), (0.1, 0.1, 1.2), "timber")
    gable_roof(mb, 0, 0, 2.6, 2.6, 7.2, 0.9, 0.2, ["roof", "roof_dark"], rows=2)
    export(folder, "watchtower", mb)


def trap(folder):
    common.reset_scene()
    mb = MeshBuilder()
    mb.box((0, 0, 0.03), (1.6, 1.6, 0.06), "soil")
    for i in range(4):
        for j in range(4):
            x = -0.6 + i * 0.4
            y = -0.6 + j * 0.4
            mb.cylinder((x, y, 0.05), (x, y, 0.4), 0.05, 0.0, "wood", segments=4)
    for k in range(3):
        mb.box((-0.5 + k * 0.5, 0, 0.1), (0.4, 1.4, 0.04), "hay")
    export(folder, "trap", mb)


def barracks(folder):
    common.reset_scene()
    mb = MeshBuilder()
    cottage(mb, 0, 0.9, 7.0, 3.6, 2.8, roof=("slate", "slate_dark"), walls="stone")
    # A training yard with dummies and a weapon rack.
    fence(mb, -3.8, -2.8, 3.8, -2.8, posts=8)
    for x in (-2.0, 0.0):
        mb.box((x, -1.7, 0.8), (0.1, 0.1, 1.6), "timber")
        mb.box((x, -1.7, 1.3), (0.6, 0.08, 0.08), "timber")
        mb.sphere((x, -1.7, 1.6), 0.22, "hay", segments=6, rings=4)
    mb.box((2.2, -1.6, 0.9), (1.2, 0.2, 0.08), "timber")
    for i in range(4):
        mb.cylinder((1.75 + i * 0.3, -1.65, 0), (1.75 + i * 0.3, -1.65, 1.7), 0.03, 0.03, "wood", segments=4)
        mb.cylinder((1.75 + i * 0.3, -1.65, 1.7), (1.75 + i * 0.3, -1.65, 1.95), 0.05, 0.0, "iron", segments=4)
    mb.cylinder((3.6, 2.6, 0), (3.6, 2.6, 4.5), 0.05, 0.04, "timber", segments=6)
    mb.box((3.2, 2.6, 4.2), (0.8, 0.03, 0.5), "cloth_red")
    export(folder, "barracks", mb)


# --- Construction sites (phase 67) ---------------------------------------------------------

SITE_WALL = 0.35     # Thickness of the foundation.
SITE_HEIGHT = 0.4    # Height of the foundation.


def footprints():
    """The distinct footprint sizes (w, d) of the buildings of core, read
    from its definitions, in order."""
    import json
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "..", "..", "data", "mods", "core", "defs", "buildings.json")
    with open(path, encoding="utf-8") as f:
        defs = json.load(f)["defs"]
    return sorted({(int(d["size"][0]), int(d["size"][1])) for d in defs if d.get("type") == "building"})


def site_frame_height(w, d):
    """3 m for the smallest footprints, up to 5 m for the largest (8 m)."""
    return 3.0 + 2.0 * max(0.0, min(1.0, (max(w, d) - 2) / 6.0))


def stone_run(mb, x0, y0, x1, y1, first=0):
    """A stretch of the foundation from (x0, y0) to (x1, y1): blocks about
    a meter long, of two greys and slightly uneven heights."""
    length = math.hypot(x1 - x0, y1 - y0)
    n = max(1, round(length))
    along_x = abs(x1 - x0) > abs(y1 - y0)
    for i in range(n):
        t = (i + 0.5) / n
        h = SITE_HEIGHT - (0.05 if (i + first) % 2 else 0.0)
        size = (length / n, SITE_WALL, h) if along_x else (SITE_WALL, length / n, h)
        mb.box((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, h / 2), size, "stone" if (i + first) % 2 else "stone_dark")


def site_foundation(mb, w, d):
    """The dirt floor and the low stone outline around the footprint, with
    a gap for the door in the middle of the -Y side."""
    mb.box((0, 0, 0.03), (w - 0.1, d - 0.1, 0.06), "soil")
    x, y = (w - SITE_WALL) / 2, (d - SITE_WALL) / 2
    door = min(1.0, w * 0.35) / 2
    stone_run(mb, -w / 2, -y, -door, -y)
    stone_run(mb, door, -y, w / 2, -y, 1)
    stone_run(mb, -w / 2, y, w / 2, y, 1)
    stone_run(mb, -x, -d / 2 + SITE_WALL, -x, d / 2 - SITE_WALL)
    stone_run(mb, x, -d / 2 + SITE_WALL, x, d / 2 - SITE_WALL, 1)


def plank_pile(mb, cx, cy, length):
    """Planks stacked along X, the top ones askew."""
    for layer, count in enumerate((3, 3, 2)):
        for i in range(count):
            y = cy + (i - (count - 1) / 2) * 0.24
            mb.box((cx + 0.05 * layer, y, 0.06 + 0.03 + layer * 0.06), (length, 0.2, 0.05),
                   "wood_light" if (i + layer) % 2 else "wood", rotation_z=0.05 * layer)


def site_ladder(mb, foot, top, width=0.42):
    """A ladder from `foot` to `top` (both x, z), on the plane Y = foot's y."""
    (x0, y, z0), (x1, _, z1) = foot, top
    for side in (-1, 1):
        mb.cylinder((x0, y + side * width / 2, z0), (x1, y + side * width / 2, z1), 0.03, 0.03, "wood", segments=4)
    rungs = max(3, int(math.hypot(x1 - x0, z1 - z0) / 0.32))
    for i in range(1, rungs + 1):
        t = i / (rungs + 1)
        x, z = x0 + (x1 - x0) * t, z0 + (z1 - z0) * t
        mb.cylinder((x, y - width / 2, z), (x, y + width / 2, z), 0.022, 0.022, "wood_light", segments=4)


def site_frame(mb, w, d):
    """Stage 2: posts on the foundation, plates and rails between them,
    corner braces, and inside the +X wall a scaffold with a ladder."""
    h = site_frame_height(w, d)
    t = 0.16
    x, y = (w - SITE_WALL) / 2, (d - SITE_WALL) / 2
    nx, ny = max(1, round(2 * x / 2.5)), max(1, round(2 * y / 2.5))
    xs = [-x + 2 * x * i / nx for i in range(nx + 1)]
    ys = [-y + 2 * y * i / ny for i in range(ny + 1)]
    z0 = SITE_HEIGHT - 0.05
    posts = [(px, py) for px in xs for py in (-y, y)] + [(px, py) for px in (-x, x) for py in ys[1:-1]]
    for px, py in posts:
        mb.box((px, py, (z0 + h) / 2), (t, t, h - z0), "timber")
    rail = z0 + (h - z0) * 0.5
    for py in (-y, y):
        mb.box((0, py, h - t / 2), (2 * x + t, t, t), "timber")
        if py > 0:   # The front stays open under the plate, for the door.
            mb.box((0, py, rail), (2 * x, t * 0.7, t * 0.7), "wood")
    for px in (-x, x):
        mb.box((px, 0, h - t / 2), (t, 2 * y + t, t), "timber")
        mb.box((px, 0, rail), (t * 0.7, 2 * y, t * 0.7), "wood")
    for px in xs[1:-1]:   # Tie beams across.
        mb.box((px, 0, h - t / 2), (t * 0.8, 2 * y, t * 0.8), "wood")
    # Braces from each corner post up to the plates.
    reach = min(0.9, x * 0.8, y * 0.8)
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.cylinder((sx * x, sy * y, h - t - reach), (sx * (x - reach), sy * y, h - t), 0.05, 0.05, "wood",
                        segments=4)
            mb.cylinder((sx * x, sy * y, h - t - reach), (sx * x, sy * (y - reach), h - t), 0.05, 0.05, "wood",
                        segments=4)
    # The scaffold: four poles, ledgers, a plank platform and a brace.
    outer = w / 2 - SITE_WALL - 0.25
    inner = outer - 0.6
    half = min(d - 1.2, 3.0) / 2
    deck = h * 0.55
    for px in (inner, outer):
        for py in (-half, half):
            mb.cylinder((px, py, 0.06), (px, py, deck + 1.0), 0.04, 0.035, "wood", segments=5)
        for z in (deck - 0.06, deck + 0.9):
            mb.cylinder((px, -half, z), (px, half, z), 0.03, 0.03, "wood", segments=4)
    for py in (-half, half):
        mb.cylinder((inner, py, deck - 0.06), (outer, py, deck - 0.06), 0.03, 0.03, "wood", segments=4)
        mb.cylinder((inner, py, 0.3), (outer, py, deck - 0.2), 0.025, 0.025, "wood", segments=4)
    for i, px in enumerate((inner + 0.1, inner + 0.3, inner + 0.5)):
        mb.box((px, 0, deck), (0.19, 2 * half + 0.3, 0.05), "wood_light" if i % 2 else "wood")
    foot = max(-w / 2 + SITE_WALL + 0.1, inner - 0.08 - deck * 0.3)
    site_ladder(mb, (foot, 0.0, 0.06), (inner - 0.08, 0.0, deck + 0.35))


def site(folder, w, d, stage):
    """A construction site of a w x d footprint: site_<w>x<d>_<stage>.glb.
    Stage 1 is the foundations (a low stone outline, a dirt floor, stakes
    and a pile of planks); stage 2 adds the timber frame with its scaffold
    and ladder. Stage 3 is the finished building's own model."""
    common.reset_scene()
    mb = MeshBuilder()
    site_foundation(mb, w, d)
    inner_x, inner_y = w / 2 - SITE_WALL, d / 2 - SITE_WALL
    if stage == 1:
        # Stakes with a red rag, marking the corners and the door.
        marks = [(sx * (inner_x - 0.25), sy * (inner_y - 0.25)) for sx in (-1, 1) for sy in (-1, 1)]
        marks += [(sx * min(1.0, w * 0.35) / 2, -d / 2 + 0.12) for sx in (-1, 1)]
        for i, (px, py) in enumerate(marks):
            mb.box((px, py, 0.45), (0.06, 0.06, 0.9), "wood", rotation_z=0.3 * i)
            mb.box((px, py, 0.84), (0.09, 0.09, 0.1), "cloth_red", rotation_z=0.3 * i)
    if stage == 1 or w >= 4:
        length = max(0.7, min(1.8, w - 2.2))
        mb_x = -inner_x + 0.35 + length / 2 if w >= 4 else 0.0
        plank_pile(mb, mb_x, inner_y - 0.55 if d >= 3 else 0.0, length)
    if stage == 2:
        site_frame(mb, w, d)
    export(folder, f"site_{w}x{d}_{stage}", mb)


def sites(folder):
    os.makedirs(folder, exist_ok=True)
    for w, d in footprints():
        for stage in (1, 2):
            site(folder, w, d, stage)


def make_all(folder, only=None):
    """`only`: ["sites"] builds just the construction sites."""
    if only and "sites" in only:
        sites(folder)
        return
    os.makedirs(folder, exist_ok=True)
    town_center(folder)
    # Homes: three looks for each level (phase 31).
    for level, names in enumerate((("house", "house_2", "house_3"), ("house_l2", "house_l2_2", "house_l2_3"),
                                   ("house_l3", "house_l3_2", "house_l3_3"))):
        for style, name in enumerate(names):
            house_variant(folder, name, level, style)
    storehouse(folder, "storehouse", 7, 6)
    storehouse(folder, "granary", 8, 7, food=True)
    shops = (
        ("woodcutter", 5, 5, woodcutter_yard, ("thatch", "thatch_dark")),
        ("forager", 5, 5, forager_yard, ("thatch", "thatch_dark")),
        ("stonecutter", 5, 5, stonecutter_yard, ("slate", "slate_dark")),
        ("firewood_splitter", 5, 4, splitter_yard, ("thatch", "thatch_dark")),
        ("farm", 6, 5, farm_yard, ("thatch", "thatch_dark")),
        ("orchard", 5, 5, orchard_yard, ("thatch", "thatch_dark")),
        ("hunter", 5, 4, hunter_yard, ("thatch", "thatch_dark")),
        ("fisher", 5, 4, fisher_yard, ("thatch", "thatch_dark")),
        ("explorer", 5, 4, explorer_yard, ("thatch", "thatch_dark")),
        ("herbalist", 4, 4, herbalist_yard, ("thatch", "thatch_dark")),
        ("compost_yard", 5, 5, compost_yard, ("thatch", "thatch_dark")),
        ("mill", 5, 5, mill_extras, ("roof", "roof_dark")),
        ("bakery", 5, 5, bakery_yard, ("roof", "roof_dark")),
        ("brewery", 5, 5, brewery_yard, ("roof", "roof_dark")),
        ("tannery", 5, 5, tannery_yard, ("thatch", "thatch_dark")),
        ("weaver", 5, 5, weaver_yard, ("roof", "roof_dark")),
        ("tailor", 5, 5, tailor_yard, ("roof", "roof_dark")),
        ("cobbler", 5, 5, cobbler_yard, ("roof", "roof_dark")),
        ("clay_pit", 5, 5, clay_pit_yard, ("thatch", "thatch_dark")),
        ("kiln", 5, 5, kiln_yard, ("slate", "slate_dark")),
        ("charcoal_kiln", 5, 5, charcoal_yard, ("thatch", "thatch_dark")),
        ("iron_mine", 5, 4, mine_extras, ("slate", "slate_dark")),
        ("smelter", 5, 5, smelter_yard, ("slate", "slate_dark")),
        ("blacksmith", 5, 5, blacksmith_yard, ("slate", "slate_dark")),
        ("smokehouse", 5, 5, smokehouse_yard, ("roof", "roof_dark")),
        ("bowyer", 5, 5, bowyer_yard, ("roof", "roof_dark")),
        ("armory", 5, 5, armory_yard, ("slate", "slate_dark")),
    )
    for name, w, d, extras, roof in shops:
        workshop(folder, name, w, d, extras, roof=roof)
    well(folder)
    chapel(folder)
    tavern(folder)
    market(folder)
    garden(folder)
    statue(folder)
    campfire(folder)
    torch(folder)
    healer(folder, "healer", 4, 4)
    healer(folder, "physician", 6, 6, tier2=True)
    bathhouse(folder)
    trading_post(folder)
    vault(folder)
    palisade(folder)
    stone_wall(folder)
    gate(folder)
    watchtower(folder)
    trap(folder)
    barracks(folder)
    sites(folder)
