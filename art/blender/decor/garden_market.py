"""Decorations: garden structures and market/trade props.

Run with Blender to write every model:

    blender --background --factory-startup --python art/blender/decor/garden_market.py -- <output folder>

Same conventions as buildings.py: meters, Z up, front toward -Y, standing on
Z = 0 and centered; square footprints of 2, 3 or 4 m.
"""

import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import bmesh
from mathutils import Matrix, Vector

import buildings
import common
from common import MeshBuilder

buildings.COLORS.update({
    "gm_hedge": common.rgb(0x3F6B2E),
    "gm_hedge_light": common.rgb(0x5C8A3A),
    "gm_vine": common.rgb(0x6A9A3C),
    "gm_paving": common.rgb(0xB0A898),
    "gm_paving_dark": common.rgb(0x938B7C),
    "gm_grass": common.rgb(0x6F9A4A),
    "gm_terracotta": common.rgb(0xB8623C),
    "gm_terracotta_dark": common.rgb(0x8E4A2C),
    "gm_awning_red": common.rgb(0xB8403A),
    "gm_awning_white": common.rgb(0xEDE6D2),
    "gm_rope": common.rgb(0xC8B88A),
    "gm_apple": common.rgb(0xC83A2E),
    "gm_cabbage": common.rgb(0x8AB85A),
    "gm_pumpkin": common.rgb(0xD8842A),
    "gm_linen_blue": common.rgb(0x6A8AB8),
    "gm_linen_yellow": common.rgb(0xD8B84A),
    "gm_bloom_white": common.rgb(0xF0ECE0),
    "gm_bloom_purple": common.rgb(0x8A5AA8),
    "gm_sail": common.rgb(0xE4DCC0),
})


# --- Pieces ------------------------------------------------------------------------------


def obox(mb, center, size, matrix, mat):
    """A box with any orientation: `matrix` is a 3x3 or 4x4 rotation."""
    m = (Matrix.Translation(Vector(center)) @ matrix.to_4x4()
         @ Matrix.Diagonal((size[0], size[1], size[2], 1.0)))
    r = bmesh.ops.create_cube(mb.bm, size=1.0, matrix=m)
    return mb._finish(r["verts"], mat, None)


def ground(mb, size, mat, h=0.06):
    """A thin slab over the whole plot, 0.1 m inside the edge."""
    s = size - 0.2
    mb.box((0, 0, h / 2), (s, s, h), mat)


def paving(mb, size):
    """Stone slabs in a checker of two grays."""
    s = size - 0.2
    n = size
    step = s / n
    for i in range(n):
        for j in range(n):
            mat = "gm_paving" if (i + j) % 2 else "gm_paving_dark"
            mb.box((-s / 2 + (i + 0.5) * step, -s / 2 + (j + 0.5) * step, 0.03), (step, step, 0.06), mat)


def wheel(mb, x, y, z, r):
    """A spoked cart wheel whose axle runs along X."""
    mb.cylinder((x - 0.05, y, z), (x + 0.05, y, z), r, r, "timber", segments=12)
    mb.cylinder((x - 0.06, y, z), (x + 0.06, y, z), r * 0.8, r * 0.8, "wood_light", segments=12)
    mb.cylinder((x - 0.09, y, z), (x + 0.09, y, z), r * 0.22, r * 0.22, "iron", segments=6)
    for k in range(4):
        a = k * math.pi / 4
        dy, dz = math.cos(a) * r * 0.8, math.sin(a) * r * 0.8
        for side in (-0.07, 0.07):
            mb.cylinder((x + side, y - dy, z - dz), (x + side, y + dy, z + dz), 0.025, 0.025, "timber", segments=4)


def bush(mb, x, y, z, r, mat="leaves", flat=0.8):
    mb.sphere((x, y, z), r, mat, segments=7, rings=4, scale=(1, 1, flat))


def clay_pot(mb, x, y, r, h):
    mb.cylinder((x, y, 0), (x, y, h), r * 0.7, r, "gm_terracotta", segments=10)
    mb.cylinder((x, y, h), (x, y, h + h * 0.16), r * 1.1, r * 1.1, "gm_terracotta_dark", segments=10)
    mb.cylinder((x, y, h + h * 0.1), (x, y, h + h * 0.18), r * 0.92, r * 0.92, "soil", segments=10)


def blooms(mb, points, r=0.07):
    mats = ("flowers", "flowers_y", "gm_bloom_white", "gm_bloom_purple")
    for i, p in enumerate(points):
        mb.sphere(p, r, mats[i % 4], segments=5, rings=3)


def striped_awning(mb, x0, x1, y_front, y_back, z_front, z_back, stripes):
    step = (x1 - x0) / stripes
    for i in range(stripes):
        mat = "gm_awning_red" if i % 2 == 0 else "gm_awning_white"
        buildings.sloped_slab(mb, x0 + i * step, x0 + (i + 1) * step, y_front, y_back, z_front, z_back, 0.05, mat)
        # The scalloped valance hanging at the front.
        mb.box((x0 + (i + 0.5) * step, y_front, z_front - 0.1), (step, 0.04, 0.2 if i % 2 == 0 else 0.14), mat)


def heap(mb, x, y, z, mat, r=0.09):
    """A little heap of round goods on a tray."""
    for dx, dy in ((-r, -r), (r, -r), (-r, r), (r, r)):
        mb.sphere((x + dx, y + dy, z + r * 0.7), r, mat, segments=6, rings=3)
    mb.sphere((x, y, z + r * 1.9), r, mat, segments=6, rings=3)


# --- Models ------------------------------------------------------------------------------


def market_stall(folder):
    common.reset_scene()
    mb = MeshBuilder()
    paving(mb, 3)
    for x in (-1.15, 1.15):
        mb.box((x, -0.55, 1.0), (0.1, 0.1, 2.0), "timber")
        mb.box((x, 0.75, 1.25), (0.1, 0.1, 2.5), "timber")
    # Counter with a plank front, and a shelf at the back.
    mb.box((0, -0.45, 0.82), (2.4, 0.75, 0.08), "wood")
    mb.box((0, -0.8, 0.45), (2.3, 0.05, 0.7), "wood_light")
    for x in (-0.75, 0, 0.75):
        mb.box((x, -0.83, 0.45), (0.05, 0.03, 0.7), "timber")
    mb.box((0, 0.7, 1.0), (2.3, 0.3, 0.06), "wood")
    mb.box((0, 0.84, 0.65), (2.3, 0.04, 1.3), "wood_light")
    striped_awning(mb, -1.35, 1.35, -1.25, 0.95, 1.95, 2.55, 6)
    # Goods on the counter: trays of apples, cabbages, pumpkins and bread.
    for x, mat in ((-0.9, "gm_apple"), (-0.3, "gm_cabbage"), (0.3, "gm_pumpkin")):
        mb.box((x, -0.5, 0.89), (0.46, 0.46, 0.06), "wood_light")
        heap(mb, x, -0.5, 0.92, mat)
    mb.box((0.9, -0.5, 0.89), (0.46, 0.46, 0.06), "wood_light")
    for k in range(3):
        mb.cylinder((0.75, -0.62 + k * 0.12, 0.96), (1.05, -0.62 + k * 0.12, 0.96), 0.05, 0.06, "bread", segments=5)
    for k in range(4):
        mb.cylinder((-0.9 + k * 0.6, 0.7, 1.03), (-0.9 + k * 0.6, 0.7, 1.28), 0.1, 0.07,
                    ("clay", "wood", "gm_terracotta", "wood")[k], segments=7)
    # Around the stall.
    buildings.barrel(mb, 1.05, 0.2, h=0.7, r=0.25)
    buildings.crate(mb, -1.0, 0.15, s=0.5, top="gm_apple")
    mb.cylinder((-1.0, -1.1, 0.06), (-1.0, -1.1, 0.4), 0.2, 0.26, "thatch_dark", segments=8)
    heap(mb, -1.0, -1.1, 0.34, "gm_pumpkin", r=0.1)
    buildings.export(folder, "decor_market_stall", mb)


def hedge_square(folder):
    common.reset_scene()
    mb = MeshBuilder()
    ground(mb, 3, "gm_grass")
    h, t, e = 0.8, 0.45, 1.4 - 0.225
    # Hedge walls with an opening at the front.
    for cx, cy, sx, sy in ((0, e, 2.8, t), (-e, 0, t, 1.9), (e, 0, t, 1.9),
                           (-0.9, -e, 1.0, t), (0.9, -e, 1.0, t)):
        mb.box((cx, cy, 0.06 + h / 2), (sx, sy, h), "gm_hedge")
        mb.box((cx, cy, 0.06 + h + 0.03), (sx - 0.1, sy - 0.1, 0.06), "gm_hedge_light")
    # Rounded finials on the corners and beside the opening.
    for x in (-e + 0.03, e - 0.03):
        for y in (-e + 0.03, e - 0.03):
            mb.sphere((x, y, 1.05), 0.25, "gm_hedge_light", segments=8, rings=5)
    for x in (-0.55, 0.55):
        mb.sphere((x, -e + 0.03, 1.0), 0.22, "gm_hedge_light", segments=8, rings=5)
    # Gravel path and a round flower bed inside.
    mb.box((0, -0.75, 0.075), (0.7, 1.3, 0.03), "gm_paving")
    mb.cylinder((0, 0.15, 0.06), (0, 0.15, 0.2), 0.62, 0.62, "stone", segments=10)
    mb.cylinder((0, 0.15, 0.2), (0, 0.15, 0.24), 0.52, 0.52, "soil", segments=10)
    bush(mb, 0, 0.15, 0.4, 0.3, "leaves")
    pts = []
    for k in range(8):
        a = k * math.pi / 4
        pts.append((math.cos(a) * 0.38, 0.15 + math.sin(a) * 0.38, 0.3))
    blooms(mb, pts, 0.09)
    blooms(mb, [(0, 0.15, 0.68)], 0.1)
    buildings.export(folder, "decor_hedge_square", mb)


def hay_cart(folder):
    common.reset_scene()
    mb = MeshBuilder()
    ground(mb, 3, "soil", h=0.04)
    z = 0.62
    # Bed, side rails and stakes.
    mb.box((0, 0.2, z), (1.3, 2.0, 0.1), "wood")
    for x in (-0.65, 0.65):
        mb.box((x, 0.2, z + 0.3), (0.06, 2.0, 0.08), "timber")
        mb.box((x, 0.2, z + 0.52), (0.06, 2.0, 0.08), "timber")
        for y in (-0.75, -0.1, 0.55, 1.15):
            mb.box((x, y, z + 0.35), (0.08, 0.08, 0.6), "timber")
    mb.box((0, 1.18, z + 0.3), (1.3, 0.06, 0.5), "wood_light")
    mb.cylinder((-0.8, 0.35, 0.5), (0.8, 0.35, 0.5), 0.05, 0.05, "iron", segments=6)
    for x in (-0.8, 0.8):
        wheel(mb, x, 0.35, 0.5, 0.46)
    # Shafts resting on the ground at the front.
    for x in (-0.45, 0.45):
        mb.cylinder((x, -0.75, z), (x, -1.32, 0.12), 0.045, 0.04, "timber", segments=5)
    mb.cylinder((-0.45, -1.2, 0.2), (0.45, -1.2, 0.2), 0.035, 0.035, "timber", segments=5)
    # The load of hay, heaped over the rails.
    mb.box((0, 0.2, z + 0.4), (1.22, 1.9, 0.7), "hay")
    mb.sphere((0, 0.2, z + 0.75), 0.8, "hay", segments=9, rings=5, scale=(0.9, 1.3, 0.75))
    mb.sphere((0.15, -0.25, z + 0.95), 0.5, "thatch", segments=7, rings=4, scale=(1, 1.2, 0.7))
    mb.sphere((-0.2, 0.7, z + 0.9), 0.5, "thatch", segments=7, rings=4, scale=(1, 1.1, 0.7))
    # A pitchfork stuck in the hay and a loose pile beside the cart.
    mb.cylinder((0.3, 0.5, z + 1.0), (0.55, 0.75, z + 1.95), 0.025, 0.025, "wood_light", segments=5)
    mb.sphere((-1.05, -0.9, 0.2), 0.34, "hay", segments=7, rings=4, scale=(1, 1, 0.7))
    buildings.export(folder, "decor_hay_cart", mb)


def gazebo(folder):
    common.reset_scene()
    mb = MeshBuilder()
    n, r = 8, 1.75

    def ring(rad):
        return [(math.cos((k + 0.5) * 2 * math.pi / n) * rad, math.sin((k + 0.5) * 2 * math.pi / n) * rad)
                for k in range(n)]

    ground(mb, 4, "gm_grass")
    mb.prism(ring(r + 0.12), 0.06, 0.2, "stone")
    mb.prism(ring(r), 0.2, 0.3, "wood_light")
    posts = ring(r - 0.15)
    for k, (x, y) in enumerate(posts):
        mb.box((x, y, 1.35), (0.13, 0.13, 2.1), "timber")
        x2, y2 = posts[(k + 1) % n]
        mb.cylinder((x, y, 2.3), (x2, y2, 2.3), 0.06, 0.06, "timber", segments=5)
        # Railings on every side but the front one (the side facing -Y).
        if (y + y2) / 2 > -1.2:
            mb.cylinder((x, y, 1.0), (x2, y2, 1.0), 0.045, 0.045, "wood", segments=5)
            mb.cylinder((x, y, 0.45), (x2, y2, 0.45), 0.035, 0.035, "wood", segments=5)
            for t in (0.25, 0.5, 0.75):
                px, py = x + (x2 - x) * t, y + (y2 - y) * t
                mb.box((px, py, 0.72), (0.05, 0.05, 0.55), "wood_light")
        else:
            mb.box(((x + x2) / 2, (y + y2) / 2 - 0.2, 0.13), (0.9, 0.3, 0.14), "stone")
    # Octagonal roof in two tiers, with a finial.
    rot = Matrix.Rotation(math.pi / n, 4, "Z")
    for z0, z1, r0, r1, mat in ((2.38, 3.0, 1.88, 0.75, "roof"), (3.0, 3.1, 0.85, 0.8, "roof_dark"),
                                (3.1, 3.55, 0.75, 0.05, "roof")):
        for v in mb.cylinder((0, 0, z0), (0, 0, z1), r0, r1, mat, segments=n):
            v.co = rot @ v.co
    mb.cylinder((0, 0, 3.5), (0, 0, 3.8), 0.04, 0.02, "iron", segments=5)
    mb.sphere((0, 0, 3.62), 0.09, "gold", segments=6, rings=4)
    # A round table with a flower pot, and a bench inside.
    mb.cylinder((0, 0.1, 0.3), (0, 0.1, 0.95), 0.08, 0.08, "timber", segments=6)
    mb.cylinder((0, 0.1, 0.95), (0, 0.1, 1.02), 0.5, 0.5, "wood", segments=8)
    mb.box((0, 1.15, 0.68), (1.1, 0.35, 0.07), "wood")
    for x in (-0.45, 0.45):
        mb.box((x, 1.15, 0.48), (0.08, 0.3, 0.36), "timber")
    mb.cylinder((0, 0.1, 1.02), (0, 0.1, 1.1), 0.1, 0.13, "gm_terracotta", segments=6)
    blooms(mb, [(-0.07, 0.05, 1.16), (0.07, 0.16, 1.16)], 0.08)
    buildings.export(folder, "decor_gazebo", mb)


def barrel_stack(folder):
    common.reset_scene()
    mb = MeshBuilder()
    paving(mb, 2)
    buildings.barrel(mb, -0.5, 0.48, h=0.85, r=0.33)
    buildings.barrel(mb, 0.2, 0.52, h=0.85, r=0.33)
    # A third barrel lying on the two.
    for a, b, r1, r2 in ((-0.55, -0.15, 0.25, 0.3), (-0.15, 0.25, 0.3, 0.25)):
        mb.cylinder((a, 0.5, 1.12), (b, 0.5, 1.12), r1, r2, "wood", segments=10)
    for x in (-0.45, 0.15):
        mb.cylinder((x - 0.03, 0.5, 1.12), (x + 0.03, 0.5, 1.12), 0.285, 0.285, "iron", segments=10)
    mb.cylinder((-0.56, 0.5, 1.12), (-0.55, 0.5, 1.12), 0.2, 0.2, "wood_light", segments=10)
    # Crates: two stacked, one open with apples.
    mb.box((0.55, -0.1, 0.36), (0.6, 0.6, 0.6), "wood_light")
    for z in (0.14, 0.58):
        mb.box((0.55, -0.1, z), (0.63, 0.63, 0.07), "timber")
    mb.box((0.5, -0.05, 0.86), (0.45, 0.45, 0.4), "wood", rotation_z=0.35)
    mb.box((0.5, -0.05, 1.07), (0.48, 0.48, 0.04), "timber", rotation_z=0.35)
    mb.box((-0.35, -0.45, 0.28), (0.7, 0.5, 0.44), "wood_light", rotation_z=-0.15)
    mb.box((-0.35, -0.45, 0.5), (0.6, 0.4, 0.04), "soil", rotation_z=-0.15)
    heap(mb, -0.48, -0.43, 0.48, "gm_apple", r=0.08)
    heap(mb, -0.2, -0.47, 0.48, "gm_apple", r=0.08)
    # A sack leaning on the crates.
    mb.sphere((0.3, -0.65, 0.26), 0.24, "gm_sail", segments=7, rings=5, scale=(1, 0.9, 1.1))
    mb.cylinder((0.3, -0.65, 0.48), (0.3, -0.65, 0.6), 0.06, 0.1, "gm_sail", segments=6)
    buildings.export(folder, "decor_barrel_stack", mb)


def potted_tree(folder):
    common.reset_scene()
    mb = MeshBuilder()
    paving(mb, 2)
    clay_pot(mb, 0, 0, 0.6, 0.7)
    mb.cylinder((0, 0, 0.3), (0, 0, 0.36), 0.56, 0.57, "gm_terracotta_dark", segments=10)
    mb.cylinder((0, 0, 0.75), (0.05, 0, 1.7), 0.11, 0.08, "log", segments=6)
    mb.cylinder((0.05, 0, 1.5), (0.4, 0.15, 2.0), 0.05, 0.04, "log", segments=5)
    mb.cylinder((0.05, 0, 1.4), (-0.35, -0.1, 1.9), 0.05, 0.04, "log", segments=5)
    mb.sphere((0.05, 0, 2.2), 0.62, "leaves", segments=8, rings=5, scale=(1, 1, 0.85))
    mb.sphere((0.45, 0.2, 2.0), 0.42, "gm_hedge_light", segments=7, rings=4)
    mb.sphere((-0.42, -0.15, 1.95), 0.42, "gm_hedge", segments=7, rings=4)
    mb.sphere((0.0, -0.3, 2.55), 0.36, "gm_hedge_light", segments=7, rings=4)
    # Oranges.
    for p in ((0.5, -0.2, 2.2), (-0.55, -0.45, 2.1), (0.1, -0.6, 2.4), (-0.2, 0.5, 2.3),
              (0.75, 0.3, 2.15), (-0.1, -0.35, 2.85), (0.35, 0.5, 2.5), (-0.75, 0.0, 1.85)):
        mb.sphere(p, 0.09, "gm_pumpkin", segments=5, rings=3)
    for k in range(6):
        a = k * math.pi / 3 + 0.3
        bush(mb, math.cos(a) * 0.38, math.sin(a) * 0.38, 0.86, 0.14, "gm_vine")
    buildings.export(folder, "decor_potted_tree", mb)


def clothesline(folder):
    common.reset_scene()
    mb = MeshBuilder()
    ground(mb, 3, "gm_grass")
    for x in (-1.25, 1.25):
        mb.box((x, 0, 1.05), (0.12, 0.12, 2.0), "timber")
        mb.box((x, 0, 1.95), (0.1, 0.9, 0.1), "timber")
        mb.cylinder((x, 0.0, 0.06), (x, 0, 0.3), 0.16, 0.1, "stone", segments=6)
    # Two sagging lines between the cross arms.
    for y in (-0.38, 0.38):
        for a, b, za, zb in ((-1.25, -0.4, 1.95, 1.84), (-0.4, 0.4, 1.84, 1.84), (0.4, 1.25, 1.84, 1.95)):
            mb.cylinder((a, y, za), (b, y, zb), 0.015, 0.015, "gm_rope", segments=4)
    # Laundry: (x, line, width, length, color).
    wash = ((-0.85, -0.38, 0.45, 0.7, "cloth_white"), (-0.3, -0.38, 0.4, 1.0, "gm_linen_blue"),
            (0.3, -0.38, 0.5, 0.55, "cloth_red"), (0.85, -0.38, 0.35, 0.85, "gm_linen_yellow"),
            (-0.6, 0.38, 0.7, 1.1, "cloth_white"), (0.25, 0.38, 0.45, 0.6, "cloth_green"),
            (0.85, 0.38, 0.4, 0.8, "gm_linen_blue"))
    for x, y, w, l, mat in wash:
        top = 1.84 + max(0.0, abs(x) - 0.4) * 0.13
        obox(mb, (x, y, top - l / 2), (w, 0.04, l), Matrix.Rotation(0.06 * (1 if x > 0 else -1), 3, "X"), mat)
        for px in (x - w * 0.35, x + w * 0.35):
            mb.box((px, y, top + 0.01), (0.03, 0.06, 0.08), "wood_light")
    # Sleeves: the red piece is a shirt.
    mb.box((0.3, -0.38, 1.72), (0.85, 0.035, 0.2), "cloth_red")
    # The laundry basket and a wash tub.
    mb.cylinder((0.75, -0.95, 0.06), (0.75, -0.95, 0.38), 0.24, 0.32, "thatch_dark", segments=8)
    mb.sphere((0.75, -0.95, 0.38), 0.27, "cloth_white", segments=7, rings=4, scale=(1, 1, 0.5))
    mb.cylinder((-0.7, 0.95, 0.06), (-0.7, 0.95, 0.4), 0.36, 0.4, "wood", segments=10)
    mb.cylinder((-0.7, 0.95, 0.38), (-0.7, 0.95, 0.42), 0.34, 0.34, "water", segments=10)
    mb.cylinder((-0.7, 0.95, 0.2), (-0.7, 0.95, 0.25), 0.4, 0.4, "iron", segments=10)
    buildings.export(folder, "decor_clothesline", mb)


def pergola(folder):
    common.reset_scene()
    mb = MeshBuilder()
    ground(mb, 4, "gm_grass")
    mb.box((0, 0, 0.075), (1.9, 3.8, 0.03), "gm_paving")
    xs, ys = (-1.45, 1.45), (-1.5, 0, 1.5)
    for x in xs:
        for y in ys:
            mb.box((x, y, 0.2), (0.3, 0.3, 0.3), "stone")
            mb.box((x, y, 1.4), (0.16, 0.16, 2.2), "timber")
        mb.box((x, 0, 2.55), (0.14, 3.7, 0.16), "timber")
    for k in range(7):
        y = -1.65 + k * 0.55
        mb.box((0, y, 2.69), (3.7, 0.1, 0.12), "wood")
    # Vines: climbing up the posts and spreading over the top.
    for x in xs:
        for y in ys:
            s = 1 if x < 0 else -1
            for z, r in ((0.8, 0.2), (1.9, 0.23)):
                mb.sphere((x + s * 0.08, y + (0.08 if z < 1 else -0.08), z), r, "gm_vine", segments=6, rings=3)
    clumps = ((-1.3, -1.4, 0.5), (-1.2, -0.3, 0.6), (-1.3, 1.0, 0.55), (1.3, -1.0, 0.55), (1.25, 0.2, 0.5),
              (1.3, 1.4, 0.5), (-0.4, 1.45, 0.45), (0.3, -1.45, 0.45), (0.1, 0.3, 0.4), (-0.5, -0.7, 0.35),
              (0.6, 0.9, 0.4))
    for i, (x, y, r) in enumerate(clumps):
        mb.sphere((x, y, 2.78), r, "gm_vine" if i % 2 else "leaves", segments=6, rings=3, scale=(1, 1, 0.4))
    # Hanging bunches of grapes.
    for x, y in ((-0.9, -1.1), (0.8, -0.55), (-0.3, 0.0), (0.9, 0.55), (-0.8, 1.1), (0.2, 1.65), (0.1, -1.65)):
        mb.cylinder((x, y, 2.63), (x, y, 2.3), 0.09, 0.03, "gm_bloom_purple", segments=5)
    # A bench at the back, and flower pots at the front.
    mb.box((0, 1.2, 0.5), (1.3, 0.4, 0.07), "wood")
    mb.box((0, 1.4, 0.8), (1.3, 0.06, 0.4), "wood")
    for x in (-0.55, 0.55):
        mb.box((x, 1.25, 0.28), (0.08, 0.4, 0.4), "timber")
    for x in (-0.7, 0.7):
        clay_pot(mb, x, -1.55, 0.2, 0.3)
        bush(mb, x, -1.55, 0.48, 0.2, "leaves")
        blooms(mb, [(x - 0.08, -1.62, 0.62), (x + 0.1, -1.5, 0.62), (x, -1.45, 0.66)], 0.07)
    buildings.export(folder, "decor_pergola", mb)


def haystacks(folder):
    common.reset_scene()
    mb = MeshBuilder()
    ground(mb, 3, "soil", h=0.04)
    for x, y, r, h in ((-0.55, 0.5, 0.75, 1.9), (0.75, 0.15, 0.6, 1.5), (-0.3, -0.8, 0.5, 1.15)):
        mb.cylinder((x, y, 0.04), (x, y, h * 0.4), r * 0.92, r, "hay", segments=9)
        mb.cylinder((x, y, h * 0.4), (x, y, h * 0.8), r, r * 0.5, "thatch", segments=9)
        mb.cylinder((x, y, h * 0.8), (x, y, h), r * 0.5, 0.06, "hay", segments=9)
        mb.cylinder((x, y, h - 0.1), (x, y, h + 0.3), 0.035, 0.03, "timber", segments=5)
        mb.cylinder((x, y, h * 0.4 - 0.02), (x, y, h * 0.4 + 0.02), r * 1.02, r * 1.02, "gm_rope", segments=9)
    # A hay bale, loose hay and a pitchfork leaning on a stack.
    mb.box((0.85, -0.95, 0.24), (0.8, 0.45, 0.4), "thatch", rotation_z=0.3)
    for t in (-0.2, 0.2):
        mb.box((0.85 + t * math.cos(0.3), -0.95 + t * math.sin(0.3), 0.24), (0.04, 0.47, 0.42), "gm_rope",
               rotation_z=0.3)
    bush(mb, 0.1, -0.2, 0.12, 0.3, "hay", flat=0.5)
    mb.cylinder((1.3, 0.95, 0.05), (1.05, 0.55, 1.5), 0.025, 0.025, "wood_light", segments=5)
    for d in (-0.07, 0.0, 0.07):
        mb.cylinder((1.05 + d, 0.55 - d, 1.5), (1.0 + d, 0.47 - d, 1.78), 0.012, 0.01, "iron", segments=4)
    mb.cylinder((0.98, 0.62, 1.5), (1.12, 0.48, 1.5), 0.014, 0.014, "iron", segments=4)
    buildings.export(folder, "decor_haystacks", mb)


def garden_arch(folder):
    common.reset_scene()
    mb = MeshBuilder()
    ground(mb, 2, "gm_grass")
    mb.box((0, 0, 0.075), (0.9, 1.8, 0.03), "gm_paving")
    r, zc, n = 0.68, 1.55, 6
    for y in (-0.3, 0.3):
        for x in (-r, r):
            mb.box((x, y, 0.06 + zc / 2), (0.09, 0.09, zc), "wood_light")
        prev = (r, zc)
        for k in range(1, n + 1):
            a = k * math.pi / n
            cur = (math.cos(a) * r, zc + math.sin(a) * r)
            mb.cylinder((prev[0], y, prev[1]), (cur[0], y, cur[1]), 0.045, 0.045, "wood_light", segments=5)
            prev = cur
    # Rungs between the two hoops, like a ladder bent over the path.
    for z in (0.5, 1.0, 1.5):
        for x in (-r, r):
            mb.cylinder((x, -0.3, z), (x, 0.3, z), 0.025, 0.025, "wood", segments=4)
    for k in range(1, n):
        a = k * math.pi / n
        mb.cylinder((math.cos(a) * r, -0.3, zc + math.sin(a) * r), (math.cos(a) * r, 0.3, zc + math.sin(a) * r),
                    0.025, 0.025, "wood", segments=4)
    # The climbing rose: leaf clumps up both sides and over the top, with blooms.
    clumps = ((-r, 0.1, 0.35, 0.22), (-r, -0.1, 0.85, 0.2), (-r, 0.12, 1.35, 0.2), (-0.58, -0.05, 1.9, 0.21),
              (-0.3, 0.1, 2.14, 0.2), (0.15, -0.1, 2.2, 0.2), (0.52, 0.1, 1.98, 0.2), (r, -0.1, 1.5, 0.19),
              (r, 0.1, 0.4, 0.21), (r, 0.0, 0.95, 0.16))
    for i, (x, y, z, rr) in enumerate(clumps):
        mb.sphere((x, y, z), rr, "leaves" if i % 2 else "gm_vine", segments=7, rings=4, scale=(0.9, 1.5, 1))
        s = -1 if i % 2 else 1
        for p in ((x + 0.05, y - rr * 1.4, z + 0.06 * s), (x - 0.06, y + rr * 1.4, z - 0.06 * s),
                  (x + 0.1 * s, y + 0.1 * s, z + rr * 0.9)):
            mb.sphere(p, 0.07, "flowers", segments=5, rings=3)
    buildings.export(folder, "decor_garden_arch", mb)


def windmill_small(folder):
    common.reset_scene()
    mb = MeshBuilder()
    ground(mb, 2, "gm_grass")
    cy = 0.2
    rot = Matrix.Translation((0, cy, 0)) @ Matrix.Rotation(math.pi / 8, 4, "Z") @ Matrix.Translation((0, -cy, 0))
    for z0, z1, r0, r1, mat in ((0.06, 0.4, 0.7, 0.67, "stone"), (0.4, 2.3, 0.63, 0.42, "plaster"),
                                (2.3, 2.42, 0.5, 0.5, "timber"), (2.42, 3.0, 0.53, 0.04, "roof")):
        for v in mb.cylinder((0, cy, z0), (0, cy, z1), r0, r1, mat, segments=8):
            v.co = rot @ v.co
    mb.box((0, cy - 0.56, 0.75), (0.34, 0.08, 0.7), "door")
    mb.box((0, cy - 0.47, 1.6), (0.2, 0.1, 0.26), "window")
    # The sails: an X of four lattice blades in front of the tower.
    hub = Vector((0, cy - 0.62, 2.2))
    mb.cylinder((0, cy - 0.3, 2.2), tuple(hub), 0.06, 0.06, "timber", segments=6)
    mb.cylinder(tuple(hub), tuple(hub + Vector((0, -0.08, 0))), 0.12, 0.09, "iron", segments=6)
    for k in range(4):
        m = Matrix.Rotation(math.pi / 4 + k * math.pi / 2, 3, "Y")
        obox(mb, hub + m @ Vector((0, -0.03, 0.5)), (0.05, 0.05, 1.0), m, "timber")
        obox(mb, hub + m @ Vector((0.14, -0.02, 0.62)), (0.24, 0.025, 0.7), m, "gm_sail")
        for t in (0.33, 0.62, 0.92):
            obox(mb, hub + m @ Vector((0.14, -0.04, t)), (0.26, 0.03, 0.03), m, "timber")
    # Sacks of flour by the door.
    for x, y in ((0.5, -0.62), (0.7, -0.42)):
        mb.sphere((x, y, 0.22), 0.17, "gm_sail", segments=6, rings=4, scale=(1, 1, 1.2))
    buildings.export(folder, "decor_windmill_small", mb)


def topiary(folder):
    common.reset_scene()
    mb = MeshBuilder()
    paving(mb, 2)
    # A square planter with three trimmed tiers, and two small cones beside it.
    mb.box((0, 0.15, 0.3), (0.9, 0.9, 0.5), "wood")
    for z in (0.14, 0.5):
        mb.box((0, 0.15, z), (0.95, 0.95, 0.07), "timber")
    mb.box((0, 0.15, 0.56), (0.8, 0.8, 0.04), "soil")
    mb.cylinder((0, 0.15, 0.55), (0, 0.15, 2.5), 0.06, 0.04, "log", segments=5)
    for z, r in ((1.0, 0.5), (1.72, 0.38), (2.28, 0.27)):
        mb.sphere((0, 0.15, z), r, "gm_hedge", segments=9, rings=6, scale=(1, 1, 0.82))
    mb.cylinder((0, 0.15, 2.5), (0, 0.15, 2.85), 0.13, 0.0, "gm_hedge_light", segments=7)
    for x in (-0.66, 0.66):
        clay_pot(mb, x, -0.62, 0.2, 0.32)
        mb.cylinder((x, -0.62, 0.36), (x, -0.62, 1.15), 0.22, 0.0, "gm_hedge_light", segments=8)
    blooms(mb, [(-0.3, -0.2, 0.62), (0.3, -0.2, 0.62), (-0.3, 0.5, 0.62), (0.3, 0.5, 0.62)], 0.08)
    buildings.export(folder, "decor_topiary", mb)


def firewood_rack(folder):
    common.reset_scene()
    mb = MeshBuilder()
    ground(mb, 2, "soil", h=0.04)
    # Posts, base rails and a small lean-to roof.
    for x in (-0.8, 0.8):
        mb.box((x, 0.45, 0.95), (0.1, 0.1, 1.85), "timber")
        mb.box((x, -0.25, 0.8), (0.1, 0.1, 1.55), "timber")
    for y in (-0.25, 0.45):
        mb.box((0, y, 0.12), (1.7, 0.08, 0.08), "timber")
    buildings.sloped_slab(mb, -0.88, 0.88, -0.48, 0.62, 1.5, 1.95, 0.06, "roof")
    for k in range(4):
        x = -0.66 + k * 0.44
        buildings.sloped_slab(mb, x - 0.02, x + 0.02, -0.5, 0.64, 1.53, 1.98, 0.04, "roof_dark")
    # Split logs stacked across the rack, ends showing at the front.
    for row in range(4):
        for i in range(5):
            x = -0.58 + i * 0.29 + (0.07 if row % 2 else 0)
            if x > 0.66:
                continue
            z = 0.3 + row * 0.27
            mb.cylinder((x, -0.35, z), (x, 0.52, z), 0.135, 0.135, "log", segments=6)
            mb.cylinder((x, -0.36, z), (x, -0.35, z), 0.11, 0.11, "log_end", segments=6)
    # The chopping block with an axe, and a few split pieces.
    mb.cylinder((0.45, -0.68, 0.04), (0.45, -0.68, 0.4), 0.2, 0.19, "log", segments=8)
    mb.cylinder((0.45, -0.68, 0.4), (0.45, -0.68, 0.41), 0.17, 0.17, "log_end", segments=8)
    mb.cylinder((0.42, -0.68, 0.42), (0.75, -0.68, 0.88), 0.022, 0.022, "wood_light", segments=5)
    obox(mb, (0.45, -0.68, 0.5), (0.16, 0.03, 0.14), Matrix.Rotation(-0.6, 3, "Y"), "iron")
    for x, y, a in ((-0.4, -0.7, 0.4), (-0.15, -0.76, -0.3), (-0.6, -0.62, 1.2)):
        mb.box((x, y, 0.1), (0.4, 0.1, 0.1), "log_end", rotation_z=a)
    buildings.export(folder, "decor_firewood_rack", mb)


def fish_rack(folder):
    common.reset_scene()
    mb = MeshBuilder()
    ground(mb, 3, "soil", h=0.04)
    # Two A-frames carrying three poles hung with fish.
    for x in (-1.2, 1.2):
        mb.cylinder((x, -0.75, 0.04), (x, 0.0, 2.05), 0.05, 0.04, "timber", segments=5)
        mb.cylinder((x, 0.75, 0.04), (x, 0.0, 2.05), 0.05, 0.04, "timber", segments=5)
        mb.cylinder((x, -0.46, 0.85), (x, 0.46, 0.85), 0.035, 0.035, "timber", segments=5)
    poles = ((0.0, 1.98), (-0.27, 1.3), (0.27, 1.3))
    for y, z in poles:
        mb.cylinder((-1.32, y, z), (1.32, y, z), 0.035, 0.035, "wood", segments=5)
    for j, (y, z) in enumerate(poles):
        for i in range(7):
            x = -0.96 + i * 0.32 + (0.08 if j == 1 else 0)
            l = 0.42 + ((i * 3 + j) % 3) * 0.06
            # Tail up, body down: a flattened spindle.
            verts = mb.cylinder((x, y, z - 0.1), (x, y, z - 0.1 - l * 0.35), 0.03, 0.085, "fish", segments=4)
            verts += mb.cylinder((x, y, z - 0.1 - l * 0.35), (x, y, z - 0.1 - l), 0.085, 0.02, "fish", segments=4)
            for v in verts:
                v.co.y = y + (v.co.y - y) * 0.4
            mb.box((x, y, z - 0.09), (0.12, 0.02, 0.06), "slate")
    # A basket of fresh fish and a barrel of salt.
    mb.cylinder((0.8, -1.05, 0.04), (0.8, -1.05, 0.36), 0.25, 0.32, "thatch_dark", segments=8)
    for k in range(3):
        mb.cylinder((0.62, -1.15 + k * 0.1, 0.38), (0.98, -1.05 + k * 0.06, 0.4), 0.03, 0.07, "fish", segments=5)
    buildings.barrel(mb, -0.9, 1.05, h=0.7, r=0.26)
    mb.cylinder((-0.9, 1.05, 0.7), (-0.9, 1.05, 0.73), 0.2, 0.2, "cloth_white", segments=10)
    buildings.export(folder, "decor_fish_rack", mb)


def small_gable(mb, cx, cy, w, d, z, rise, mat, over=0.1):
    """A little gable roof with its ridge along X, over a w x d box whose top is at z."""
    for s in (-1, 1):
        buildings.sloped_slab(mb, cx - w / 2 - over, cx + w / 2 + over, cy + s * (d / 2 + over), cy,
                              z - 0.05, z + rise, 0.06, mat)


def chicken(mb, x, y, angle, mat="cloth_white"):
    dx, dy = math.cos(angle), math.sin(angle)
    mb.sphere((x, y, 0.2), 0.13, mat, segments=6, rings=4, scale=(1, 1, 0.9))
    mb.sphere((x - dx * 0.13, y - dy * 0.13, 0.27), 0.06, mat, segments=5, rings=3)
    mb.sphere((x + dx * 0.12, y + dy * 0.12, 0.34), 0.07, mat, segments=5, rings=3)
    mb.box((x + dx * 0.12, y + dy * 0.12, 0.42), (0.04, 0.04, 0.05), "gm_awning_red")
    mb.cylinder((x + dx * 0.17, y + dy * 0.17, 0.33), (x + dx * 0.24, y + dy * 0.24, 0.31), 0.02, 0.0, "flowers_y",
                segments=4)
    for s in (-0.04, 0.04):
        mb.cylinder((x - dy * s, y + dx * s, 0.04), (x - dy * s, y + dx * s, 0.12), 0.012, 0.012, "flowers_y",
                    segments=3)


def scarecrow(folder):
    common.reset_scene()
    mb = MeshBuilder()
    ground(mb, 3, "soil", h=0.04)
    # Ridges of earth with cabbages, and a few pumpkins.
    for k in range(5):
        y = -1.1 + k * 0.55
        mb.box((0, y, 0.08), (2.6, 0.32, 0.1), "timber")
        for i in range(6):
            x = -1.1 + i * 0.44
            if abs(x) < 0.3 and k == 2:
                continue
            mb.sphere((x, y, 0.2), 0.12, "gm_cabbage" if k % 2 else "leaves", segments=6, rings=3)
    for x, y, r in ((-0.9, -1.15, 0.17), (0.7, -1.1, 0.2), (1.05, 0.3, 0.16)):
        mb.sphere((x, y, 0.06 + r * 0.8), r, "gm_pumpkin", segments=7, rings=4, scale=(1, 1, 0.8))
    # The scarecrow: a pole, a cross arm, an old coat stuffed with straw and a hat.
    mb.cylinder((0, 0, 0.04), (0, 0, 2.0), 0.05, 0.04, "timber", segments=5)
    mb.cylinder((-0.85, 0, 1.55), (0.85, 0, 1.55), 0.035, 0.035, "timber", segments=5)
    mb.box((0, 0, 1.3), (0.46, 0.24, 0.68), "cloth_blue")
    mb.box((0, -0.125, 1.25), (0.1, 0.02, 0.5), "gm_linen_yellow")
    for s in (-1, 1):
        mb.cylinder((s * 0.2, 0, 1.55), (s * 0.7, 0, 1.55), 0.09, 0.07, "cloth_blue", segments=6)
        mb.sphere((s * 0.78, 0, 1.55), 0.1, "hay", segments=6, rings=3)
        mb.cylinder((s * 0.12, 0, 0.98), (s * 0.16, 0, 0.5), 0.09, 0.07, "timber", segments=6)
        mb.sphere((s * 0.16, 0, 0.47), 0.09, "hay", segments=6, rings=3)
    mb.sphere((0, 0, 1.3), 0.3, "hay", segments=6, rings=3, scale=(1, 0.6, 0.3))
    mb.sphere((0, 0, 1.84), 0.2, "gm_sail", segments=7, rings=5)
    for s in (-0.07, 0.07):
        mb.box((s, -0.19, 1.87), (0.04, 0.03, 0.04), "charcoal")
    mb.cylinder((0, -0.19, 1.82), (0, -0.3, 1.8), 0.03, 0.0, "gm_pumpkin", segments=4)
    mb.cylinder((0, 0, 1.96), (0, 0, 1.99), 0.36, 0.36, "thatch_dark", segments=9)
    mb.cylinder((0, 0, 1.99), (0, 0, 2.3), 0.2, 0.05, "thatch_dark", segments=9)
    # A crow on one arm.
    mb.sphere((0.55, 0, 1.72), 0.08, "charcoal", segments=5, rings=3, scale=(1.5, 1, 1))
    mb.sphere((0.66, 0, 1.79), 0.05, "charcoal", segments=5, rings=3)
    mb.cylinder((0.7, 0, 1.79), (0.78, 0, 1.77), 0.02, 0.0, "flowers_y", segments=4)
    buildings.export(folder, "decor_scarecrow", mb)


def beehives(folder):
    common.reset_scene()
    mb = MeshBuilder()
    ground(mb, 2, "gm_grass")
    # A bench with two straw skeps under a little roof.
    for x in (-0.7, 0.7):
        mb.box((x, 0.55, 0.85), (0.08, 0.08, 1.6), "timber")
        mb.box((x, 0.1, 0.7), (0.08, 0.08, 1.3), "timber")
    mb.box((0, 0.32, 0.5), (1.6, 0.6, 0.07), "wood")
    buildings.sloped_slab(mb, -0.85, 0.85, -0.15, 0.75, 1.32, 1.72, 0.06, "thatch")
    for x in (-0.36, 0.36):
        for z0, z1, r0, r1, mat in ((0.54, 0.74, 0.27, 0.28, "hay"), (0.74, 0.92, 0.28, 0.22, "thatch"),
                                    (0.92, 1.06, 0.22, 0.1, "hay"), (1.06, 1.1, 0.1, 0.04, "thatch")):
            mb.cylinder((x, 0.34, z0), (x, 0.34, z1), r0, r1, mat, segments=9)
        mb.box((x, 0.07, 0.6), (0.1, 0.04, 0.07), "charcoal")
    # Two box hives on the grass.
    for x, y, a, h in ((-0.5, -0.5, 0.2, 2), (0.45, -0.55, -0.25, 3)):
        mb.box((x, y, 0.12), (0.5, 0.5, 0.12), "stone", rotation_z=a)
        for k in range(h):
            mb.box((x, y, 0.3 + k * 0.24), (0.44, 0.44, 0.22), "gm_linen_yellow" if k % 2 else "plaster",
                   rotation_z=a)
        mb.box((x, y, 0.22 + h * 0.24), (0.52, 0.52, 0.06), "wood", rotation_z=a)
        mb.box((x + math.sin(a) * 0.22, y - math.cos(a) * 0.22, 0.24), (0.16, 0.03, 0.04), "charcoal", rotation_z=a)
    # Bees and flowers.
    for p in ((-0.2, -0.1, 0.9), (0.1, -0.3, 1.2), (0.6, 0.0, 0.8), (-0.6, -0.2, 1.0), (0.0, 0.0, 1.45),
              (0.3, -0.7, 1.15), (-0.45, -0.75, 0.85)):
        mb.box(p, (0.05, 0.05, 0.05), "gold")
    blooms(mb, [(-0.05, -0.75, 0.14), (0.0, -0.3, 0.14), (-0.8, 0.0, 0.14), (0.82, -0.1, 0.14), (0.1, -0.82, 0.14),
                (-0.82, -0.82, 0.14)], 0.08)
    buildings.export(folder, "decor_beehives", mb)


def vegetable_patch(folder):
    common.reset_scene()
    mb = MeshBuilder()
    ground(mb, 3, "gm_grass")
    # Two raised beds framed with planks.
    for cx in (-0.7, 0.6):
        mb.box((cx, 0.5, 0.14), (1.0, 1.6, 0.2), "wood")
        mb.box((cx, 0.5, 0.16), (0.88, 1.48, 0.2), "soil")
    for i in range(5):
        y = -0.1 + i * 0.3
        mb.sphere((-0.92, y, 0.32), 0.13, "gm_cabbage", segments=6, rings=3)
        mb.cylinder((-0.5, y, 0.26), (-0.5, y, 0.5), 0.06, 0.1, "leaves", segments=5)
        mb.cylinder((-0.5, y, 0.24), (-0.5, y, 0.3), 0.05, 0.05, "gm_pumpkin", segments=5)
    # Bean poles with climbers, and pumpkins.
    for i in range(3):
        y = 0.0 + i * 0.5
        for dx in (-0.14, 0.14):
            mb.cylinder((0.38 + dx, y, 0.25), (0.38, y, 1.45), 0.02, 0.02, "wood_light", segments=4)
        mb.cylinder((0.38, y, 0.3), (0.38, y, 1.25), 0.17, 0.06, "gm_vine", segments=6)
    mb.cylinder((0.38, 0.0, 1.38), (0.38, 1.0, 1.38), 0.02, 0.02, "wood_light", segments=4)
    for y, r in ((-0.02, 0.16), (0.45, 0.19), (0.92, 0.15)):
        mb.sphere((0.85, y, 0.26 + r * 0.7), r, "gm_pumpkin", segments=7, rings=4, scale=(1, 1, 0.8))
        bush(mb, 0.82, y + 0.22, 0.3, 0.1, "leaves", flat=0.5)
    # The wheelbarrow, full of the harvest.
    wx, wy = 0.1, -1.0
    mb.cylinder((wx - 0.95, wy, 0.2), (wx - 0.87, wy, 0.2), 0.19, 0.19, "timber", segments=10)
    mb.cylinder((wx - 0.97, wy, 0.2), (wx - 0.85, wy, 0.2), 0.05, 0.05, "iron", segments=6)
    mb.box((wx - 0.25, wy, 0.48), (0.85, 0.6, 0.28), "wood")
    mb.box((wx - 0.25, wy, 0.6), (0.75, 0.5, 0.06), "soil")
    for s in (-0.26, 0.26):
        mb.cylinder((wx - 0.91, wy + s * 0.3, 0.2), (wx + 0.75, wy + s, 0.56), 0.03, 0.03, "timber", segments=4)
        mb.cylinder((wx + 0.1, wy + s, 0.4), (wx + 0.15, wy + s, 0.06), 0.03, 0.03, "timber", segments=4)
    heap(mb, wx - 0.45, wy, 0.6, "gm_cabbage", r=0.1)
    heap(mb, wx - 0.05, wy, 0.6, "gm_pumpkin", r=0.1)
    # A spade stuck in the ground and a watering bucket.
    mb.cylinder((1.15, -1.05, 0.25), (1.15, -1.05, 1.15), 0.02, 0.02, "wood_light", segments=4)
    mb.box((1.15, -1.05, 0.2), (0.16, 0.03, 0.26), "iron")
    mb.cylinder((-1.1, -1.1, 0.06), (-1.1, -1.1, 0.34), 0.12, 0.15, "wood", segments=8)
    mb.cylinder((-1.1, -1.1, 0.32), (-1.1, -1.1, 0.35), 0.13, 0.13, "water", segments=8)
    buildings.export(folder, "decor_vegetable_patch", mb)


def dovecote(folder):
    common.reset_scene()
    mb = MeshBuilder()
    ground(mb, 2, "gm_grass")
    mb.cylinder((0, 0, 0.06), (0, 0, 0.3), 0.45, 0.38, "stone", segments=8)
    mb.cylinder((0, 0, 0.3), (0, 0, 1.6), 0.1, 0.09, "timber", segments=6)
    for k in range(4):
        a = k * math.pi / 2 + math.pi / 4
        mb.cylinder((0, 0, 1.15), (math.cos(a) * 0.45, math.sin(a) * 0.45, 1.6), 0.035, 0.035, "timber", segments=4)
    mb.cylinder((0, 0, 1.6), (0, 0, 1.68), 0.72, 0.72, "wood", segments=8)
    mb.cylinder((0, 0, 1.68), (0, 0, 2.4), 0.55, 0.55, "plaster", segments=8)
    mb.cylinder((0, 0, 2.02), (0, 0, 2.07), 0.68, 0.68, "wood", segments=8)
    # Pigeon holes in two rows, all around.
    for k in range(8):
        a = k * math.pi / 4 + math.pi / 8
        for z in (1.82, 2.22):
            mb.box((math.cos(a) * 0.5, math.sin(a) * 0.5, z), (0.06, 0.16, 0.2), "window", rotation_z=a)
    mb.cylinder((0, 0, 2.4), (0, 0, 2.95), 0.8, 0.12, "slate", segments=8)
    mb.cylinder((0, 0, 2.95), (0, 0, 3.05), 0.16, 0.16, "plaster", segments=8)
    mb.cylinder((0, 0, 3.05), (0, 0, 3.3), 0.22, 0.0, "slate_dark", segments=8)
    # Doves on the ledges, the roof and the ground.
    for x, y, z, a in ((0.2, -0.6, 1.76, 0.5), (-0.55, -0.3, 1.76, 2.5), (0.6, 0.1, 2.15, 0.0), (-0.3, -0.35, 2.8, 4.0),
                       (0.55, -0.6, 0.14, 1.0), (-0.6, 0.55, 0.14, 3.0)):
        mb.sphere((x, y, z), 0.09, "cloth_white", segments=5, rings=3, scale=(1.3, 1.3, 1))
        mb.sphere((x + math.cos(a) * 0.1, y + math.sin(a) * 0.1, z + 0.08), 0.05, "cloth_white", segments=5, rings=3)
    buildings.export(folder, "decor_dovecote", mb)


def chicken_coop(folder):
    common.reset_scene()
    mb = MeshBuilder()
    ground(mb, 3, "soil", h=0.04)
    # The hen house on stilts at the back, with a ramp.
    cx, cy, w, d = -0.5, 0.65, 1.4, 1.1
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.box((cx + sx * (w / 2 - 0.08), cy + sy * (d / 2 - 0.08), 0.25), (0.1, 0.1, 0.5), "timber")
    mb.box((cx, cy, 0.9), (w, d, 0.8), "wood_light")
    for x in (cx - w / 2, cx, cx + w / 2):
        mb.box((x, cy - d / 2 - 0.01, 0.9), (0.06, 0.03, 0.8), "timber")
    mb.box((cx - 0.35, cy - d / 2 - 0.01, 0.75), (0.34, 0.03, 0.42), "window")
    mb.box((cx + 0.35, cy - d / 2 - 0.01, 1.05), (0.3, 0.03, 0.2), "window")
    small_gable(mb, cx, cy, w, d, 1.3, 0.45, "thatch", over=0.08)
    for x in (cx - w / 2 + 0.02, cx + w / 2 - 0.02):
        for v in mb.box((x, cy, 1.5), (0.04, d, 0.44), "wood_light"):
            if v.co.z > 1.5:
                v.co.y = cy
    buildings.sloped_slab(mb, cx - 0.52, cx - 0.18, cy - d / 2 - 0.85, cy - d / 2, 0.05, 0.52, 0.04, "wood")
    for t in (0.2, 0.45, 0.7):
        mb.box((cx - 0.35, cy - d / 2 - 0.85 * (1 - t), 0.08 + 0.47 * t), (0.34, 0.03, 0.03), "timber")
    # The fenced run.
    e = 1.33
    buildings.fence(mb, -e, -e, e, -e, posts=5, h=0.6)
    buildings.fence(mb, e, -e, e, e, posts=5, h=0.6)
    buildings.fence(mb, -e, -e, -e, 0.0, posts=3, h=0.6)
    buildings.fence(mb, 0.3, e, e, e, posts=2, h=0.6)
    # Hens, a rooster on the fence post, a trough and a nest with eggs.
    chicken(mb, 0.1, -0.7, 0.5)
    chicken(mb, 0.75, -0.3, 2.6, "bread")
    chicken(mb, -0.75, -0.9, -0.4)
    chicken(mb, 0.9, 0.7, 4.0, "hide")
    mb.box((0.45, -1.0, 0.1), (0.7, 0.2, 0.12), "wood")
    mb.box((0.45, -1.0, 0.16), (0.62, 0.13, 0.02), "hay")
    mb.sphere((0.75, 0.2, 0.08), 0.24, "hay", segments=7, rings=4, scale=(1, 1, 0.45))
    for dx, dy in ((-0.06, 0), (0.06, 0.04), (0, -0.07)):
        mb.sphere((0.75 + dx, 0.2 + dy, 0.2), 0.05, "gm_bloom_white", segments=5, rings=3, scale=(1, 1, 1.25))
    buildings.export(folder, "decor_chicken_coop", mb)


def pottery_stall(folder):
    common.reset_scene()
    mb = MeshBuilder()
    paving(mb, 3)
    # A shelf rack at the back under a plain green canopy.
    for x in (-1.2, 1.2):
        mb.box((x, 0.95, 1.2), (0.1, 0.1, 2.3), "timber")
        mb.box((x, -0.6, 1.0), (0.1, 0.1, 1.9), "timber")
    for i in range(4):
        buildings.sloped_slab(mb, -1.35 + i * 0.675, -0.675 + i * 0.675, -1.2, 1.15, 1.85, 2.4, 0.05,
                              "cloth_green" if i % 2 == 0 else "gm_awning_white")
    pots = ("gm_terracotta", "clay", "gm_terracotta_dark", "gm_linen_blue", "gm_awning_white")
    for j, z in enumerate((0.5, 1.05, 1.6)):
        mb.box((0, 0.9, z), (2.4, 0.4, 0.06), "wood")
        for i in range(5):
            x = -0.9 + i * 0.45
            k = (i + j * 2) % 5
            h = 0.2 + ((i + j) % 3) * 0.06
            if (i + j) % 2:
                mb.cylinder((x, 0.9, z + 0.03), (x, 0.9, z + 0.03 + h), 0.09, 0.13, pots[k], segments=6)
            else:
                mb.cylinder((x, 0.9, z + 0.03), (x, 0.9, z + 0.03 + h * 0.6), 0.08, 0.14, pots[k], segments=6)
                mb.cylinder((x, 0.9, z + 0.03 + h * 0.6), (x, 0.9, z + 0.03 + h * 1.2), 0.14, 0.06, pots[k], segments=6)
    # A low table with plates and jugs at the front.
    mb.box((-0.2, -0.45, 0.6), (1.7, 0.7, 0.07), "wood")
    for x in (-0.95, 0.55):
        for y in (-0.72, -0.18):
            mb.box((x, y, 0.33), (0.08, 0.08, 0.54), "timber")
    for i, x in enumerate((-0.85, -0.45, -0.05, 0.4)):
        mb.cylinder((x, -0.6, 0.64), (x, -0.6, 0.68), 0.1, 0.16, pots[(i + 3) % 5], segments=8)
        mb.cylinder((x + 0.05, -0.3, 0.64), (x + 0.05, -0.3, 0.84), 0.1, 0.06, pots[i % 5], segments=7)
        mb.cylinder((x + 0.05, -0.3, 0.84), (x + 0.05, -0.3, 0.92), 0.06, 0.08, pots[i % 5], segments=7)
    # Big amphorae and a stack of bowls on the ground.
    for x, y, s, mat in ((1.0, -0.2, 1.0, "gm_terracotta"), (1.05, -0.85, 0.8, "clay"), (-1.1, -1.1, 0.7, "gm_terracotta_dark")):
        mb.cylinder((x, y, 0.06), (x, y, 0.06 + 0.4 * s), 0.12 * s, 0.26 * s, mat, segments=8)
        mb.cylinder((x, y, 0.06 + 0.4 * s), (x, y, 0.06 + 0.7 * s), 0.26 * s, 0.1 * s, mat, segments=8)
        mb.cylinder((x, y, 0.06 + 0.7 * s), (x, y, 0.06 + 0.82 * s), 0.1 * s, 0.14 * s, mat, segments=8)
    for k in range(3):
        mb.cylinder((0.35, -1.1, 0.06 + k * 0.07), (0.35, -1.1, 0.14 + k * 0.07), 0.12, 0.2, pots[k + 2], segments=8)
    buildings.export(folder, "decor_pottery_stall", mb)


def flower_cart(folder):
    common.reset_scene()
    mb = MeshBuilder()
    paving(mb, 2)
    z = 0.55
    mb.box((0, 0.1, z), (0.9, 1.3, 0.08), "wood")
    for x in (-0.45, 0.45):
        mb.box((x, 0.1, z + 0.14), (0.05, 1.3, 0.24), "cloth_green")
    for y in (-0.55, 0.75):
        mb.box((0, y, z + 0.14), (0.9, 0.05, 0.24), "cloth_green")
    mb.cylinder((-0.6, 0.3, 0.42), (0.6, 0.3, 0.42), 0.04, 0.04, "iron", segments=5)
    for x in (-0.6, 0.6):
        wheel(mb, x, 0.3, 0.42, 0.37)
    for x in (-0.38, 0.38):
        mb.cylinder((x, -0.5, z), (x, -0.88, z + 0.12), 0.03, 0.03, "timber", segments=4)
        mb.cylinder((x, -0.4, z - 0.04), (x, -0.45, 0.06), 0.03, 0.03, "timber", segments=4)
    mb.cylinder((-0.38, -0.86, z + 0.12), (0.38, -0.86, z + 0.12), 0.025, 0.025, "timber", segments=4)
    # Tiers of flowers in the cart.
    mats = ("flowers", "flowers_y", "gm_bloom_white", "gm_bloom_purple", "gm_apple")
    n = 0
    for j, y in enumerate((-0.35, 0.1, 0.55)):
        for i, x in enumerate((-0.27, 0.0, 0.27)):
            zz = z + 0.28 + j * 0.1
            mb.sphere((x, y, zz), 0.17, "leaves" if (i + j) % 2 else "gm_vine", segments=6, rings=3)
            for dx, dy in ((-0.07, -0.06), (0.08, -0.02), (0.0, 0.08)):
                mb.sphere((x + dx, y + dy, zz + 0.14), 0.065, mats[n % 5], segments=4, rings=2)
            n += 1
    # Pots and a bucket of cut flowers beside it.
    for x, y, mat in ((-0.68, -0.68, "flowers_y"), (0.7, -0.7, "gm_bloom_purple")):
        clay_pot(mb, x, y, 0.15, 0.24)
        bush(mb, x, y, 0.38, 0.15, "leaves")
        for dx, dy in ((-0.06, -0.05), (0.07, 0.0), (0.0, 0.07)):
            mb.sphere((x + dx, y + dy, 0.5), 0.065, mat, segments=4, rings=2)
    buildings.export(folder, "decor_flower_cart", mb)


def kennel(folder):
    common.reset_scene()
    mb = MeshBuilder()
    ground(mb, 2, "gm_grass")
    cx, cy, w, d, h = 0.15, 0.25, 1.0, 1.1, 0.7
    mb.box((cx, cy, 0.1), (w + 0.1, d + 0.1, 0.1), "timber")
    mb.box((cx, cy, 0.15 + h / 2), (w, d, h), "wood_light")
    # Roof with its ridge front to back, and the gable over the door.
    for s in (-1, 1):
        verts = mb.box((cx + s * (w / 4 + 0.05), cy, 0.0), (w / 2 + 0.1, d + 0.18, 0.07), "roof")
        for v in verts:
            v.co.z = 0.15 + h + 0.47 - abs(v.co.x - cx) * 0.8 + (0.07 if v.co.z > 0 else 0.0)
    for y in (cy - d / 2 + 0.02, cy + d / 2 - 0.02):
        for v in mb.box((cx, y, 0.15 + h + 0.2), (w, 0.04, 0.4), "wood_light"):
            if v.co.z > 0.15 + h + 0.2:
                v.co.x = cx
    mb.box((cx, cy - d / 2 - 0.01, 0.42), (0.42, 0.03, 0.5), "window")
    mb.cylinder((cx, cy - d / 2 - 0.025, 0.67), (cx, cy - d / 2 + 0.005, 0.67), 0.21, 0.21, "window", segments=8)
    mb.box((cx, cy - d / 2 - 0.02, 0.98), (0.4, 0.03, 0.1), "timber")
    # The dog, lying in front with its bone and bowl.
    dx, dy = -0.45, -0.55
    mb.sphere((dx, dy, 0.2), 0.2, "hide", segments=7, rings=4, scale=(1.5, 0.9, 0.75))
    mb.sphere((dx + 0.32, dy - 0.05, 0.3), 0.14, "hide", segments=6, rings=4)
    mb.box((dx + 0.45, dy - 0.07, 0.26), (0.14, 0.1, 0.08), "hide")
    mb.box((dx + 0.52, dy - 0.07, 0.29), (0.04, 0.05, 0.04), "charcoal")
    for s in (-0.1, 0.07):
        mb.box((dx + 0.28, dy - 0.05 + s, 0.38), (0.07, 0.03, 0.14), "timber")
        mb.box((dx + 0.3, dy + s * 1.5, 0.09), (0.26, 0.07, 0.07), "hide")
    mb.cylinder((dx - 0.28, dy, 0.2), (dx - 0.42, dy + 0.1, 0.12), 0.04, 0.02, "hide", segments=4)
    mb.cylinder((0.3, -0.72, 0.06), (0.3, -0.72, 0.16), 0.13, 0.17, "gm_terracotta", segments=8)
    mb.cylinder((0.3, -0.72, 0.15), (0.3, -0.72, 0.17), 0.14, 0.14, "water", segments=8)
    mb.cylinder((0.6, -0.55, 0.1), (0.82, -0.7, 0.1), 0.025, 0.025, "gm_bloom_white", segments=5)
    for x, y in ((0.6, -0.55), (0.82, -0.7)):
        for s in (-0.03, 0.03):
            mb.sphere((x + s * 0.6, y + s, 0.1), 0.04, "gm_bloom_white", segments=5, rings=3)
    # The stake and its chain.
    mb.cylinder((0.78, -0.3, 0.06), (0.78, -0.3, 0.4), 0.04, 0.04, "timber", segments=5)
    buildings.export(folder, "decor_kennel", mb)


def rug_tent(folder):
    common.reset_scene()
    mb = MeshBuilder()
    paving(mb, 3)
    # A merchant tent: four poles, a pointed canvas roof and a striped valance.
    e = 1.15
    for x in (-e, e):
        for y in (-e, e):
            mb.cylinder((x, y, 0.06), (x, y, 2.0), 0.045, 0.045, "timber", segments=5)
    rot = Matrix.Rotation(math.pi / 4, 4, "Z")
    for v in mb.cylinder((0, 0, 1.95), (0, 0, 3.0), 1.84, 0.05, "gm_linen_blue", segments=4):
        v.co = rot @ v.co
    mb.cylinder((0, 0, 2.95), (0, 0, 3.25), 0.03, 0.02, "timber", segments=4)
    mb.sphere((0, 0, 3.18), 0.08, "gold", segments=5, rings=3)
    for k in range(6):
        t = -1.08 + k * 0.432
        mat = "gm_linen_yellow" if k % 2 == 0 else "gm_linen_blue"
        hgt = 0.26 if k % 2 == 0 else 0.18
        for s in (-1, 1):
            mb.box((t, s * 1.29, 1.97 - hgt / 2), (0.432, 0.03, hgt), mat)
            mb.box((s * 1.29, t, 1.97 - hgt / 2), (0.03, 0.432, hgt), mat)
    # A rug hung at the back and rugs laid on the ground.
    mb.cylinder((-e, e - 0.05, 1.7), (e, e - 0.05, 1.7), 0.03, 0.03, "wood", segments=4)
    for x, w, l, mat, trim in ((-0.55, 0.9, 1.3, "gm_awning_red", "gm_linen_yellow"),
                               (0.55, 0.8, 1.1, "cloth_blue", "gm_awning_white")):
        mb.box((x, e - 0.08, 1.7 - l / 2), (w, 0.04, l), mat)
        mb.box((x, e - 0.105, 1.7 - l / 2), (w * 0.6, 0.02, l * 0.7), trim)
        mb.box((x, e - 0.12, 1.7 - l / 2), (w * 0.35, 0.02, l * 0.45), mat)
    for x, y, w, l, a, mat, trim in ((-0.3, -0.35, 1.3, 0.9, 0.1, "gm_awning_red", "gm_awning_white"),
                                     (0.5, -0.75, 1.0, 0.7, -0.2, "cloth_green", "gm_linen_yellow")):
        zz = 0.08 if mat == "gm_awning_red" else 0.11
        mb.box((x, y, zz), (w, l, 0.03), mat, rotation_z=a)
        mb.box((x, y, zz + 0.012), (w * 0.75, l * 0.65, 0.02), trim, rotation_z=a)
        mb.box((x, y, zz + 0.022), (w * 0.5, l * 0.35, 0.02), mat, rotation_z=a)
    # Rolled rugs, standing and lying, and cushions.
    for x, y, h, mat in ((0.95, 0.75, 1.3, "gm_bloom_purple"), (0.75, 0.9, 1.1, "gm_awning_red"),
                         (1.0, 0.5, 0.9, "gm_linen_yellow")):
        mb.cylinder((x, y, 0.06), (x, y, h), 0.12, 0.12, mat, segments=7)
        mb.cylinder((x, y, h), (x, y, h + 0.01), 0.07, 0.07, "gm_awning_white", segments=7)
    for k, mat in enumerate(("cloth_blue", "gm_linen_yellow", "cloth_green")):
        mb.cylinder((-1.1, 0.2 + (k % 2) * 0.12 + (0.06 if k == 2 else 0), 0.18 + (0.2 if k == 2 else 0)),
                    (-0.1, 0.2 + (k % 2) * 0.12 + (0.06 if k == 2 else 0) + 0.25 * (1 if k < 2 else 1),
                     0.18 + (0.2 if k == 2 else 0)), 0.12, 0.12, mat, segments=7)[0:0]
    for x, y, mat in ((-0.85, -0.95, "gm_bloom_purple"), (-0.6, -1.05, "gm_linen_yellow")):
        mb.sphere((x, y, 0.2), 0.2, mat, segments=6, rings=4, scale=(1, 1, 0.5))
    buildings.export(folder, "decor_rug_tent", mb)


def scale_stand(folder):
    common.reset_scene()
    mb = MeshBuilder()
    paving(mb, 2)
    # A sturdy table with the big balance on it.
    mb.box((0, 0.2, 0.75), (1.5, 0.8, 0.08), "wood")
    for x in (-0.65, 0.65):
        for y in (-0.1, 0.5):
            mb.box((x, y, 0.38), (0.1, 0.1, 0.66), "timber")
    mb.box((0, 0.2, 0.3), (1.3, 0.06, 0.06), "timber")
    mb.cylinder((0, 0.2, 0.79), (0, 0.2, 0.86), 0.2, 0.14, "iron", segments=8)
    mb.cylinder((0, 0.2, 0.86), (0, 0.2, 1.75), 0.04, 0.03, "iron", segments=6)
    mb.sphere((0, 0.2, 1.8), 0.07, "gold", segments=6, rings=4)
    # The beam, tilted: the loaded pan hangs lower.
    a, b = Vector((-0.55, 0.2, 1.62)), Vector((0.55, 0.2, 1.78))
    mb.cylinder(tuple(a), tuple(b), 0.025, 0.025, "gold", segments=5)
    for p, mat in ((a, "gm_apple"), (b, None)):
        pan = Vector((p.x, p.y, p.z - 0.5))
        for k in range(3):
            ang = k * 2 * math.pi / 3 + 0.5
            mb.cylinder(tuple(p), (pan.x + math.cos(ang) * 0.2, pan.y + math.sin(ang) * 0.2, pan.z + 0.04),
                        0.008, 0.008, "iron", segments=3)
        mb.cylinder(tuple(pan), (pan.x, pan.y, pan.z + 0.05), 0.12, 0.23, "gold", segments=9)
        if mat:
            heap(mb, pan.x, pan.y, pan.z + 0.03, mat, r=0.07)
        else:
            mb.cylinder((pan.x, pan.y, pan.z + 0.04), (pan.x, pan.y, pan.z + 0.16), 0.08, 0.06, "iron", segments=6)
    # A row of weights on the table, sacks of grain and a crate of apples.
    for k in range(4):
        r = 0.07 - k * 0.012
        mb.cylinder((-0.25 + k * 0.17, -0.08, 0.79), (-0.25 + k * 0.17, -0.08, 0.79 + r * 2), r, r * 0.8, "iron", segments=6)
    for x, y, s in ((-0.6, -0.6, 1.0), (-0.2, -0.68, 0.85)):
        mb.sphere((x, y, 0.06 + 0.26 * s), 0.25 * s, "gm_sail", segments=7, rings=5, scale=(1, 0.9, 1.15))
        mb.cylinder((x, y, 0.06 + 0.5 * s), (x, y, 0.06 + 0.62 * s), 0.06 * s, 0.1 * s, "gm_sail", segments=6)
    mb.cylinder((-0.2, -0.68, 0.56), (-0.2, -0.68, 0.58), 0.08, 0.08, "hay", segments=6)
    buildings.crate(mb, 0.55, -0.6, s=0.5, top="gm_apple")
    buildings.export(folder, "decor_scale_stand", mb)


def grape_trellis(folder):
    common.reset_scene()
    mb = MeshBuilder()
    ground(mb, 3, "gm_grass")
    for j, y in enumerate((-0.75, 0.15, 1.05)):
        mb.box((0, y, 0.08), (2.7, 0.4, 0.06), "soil")
        for x in (-1.25, 0, 1.25):
            mb.box((x, y, 0.8), (0.09, 0.09, 1.5), "timber")
        for z in (0.85, 1.45):
            mb.cylinder((-1.25, y, z), (1.25, y, z), 0.018, 0.018, "gm_rope", segments=4)
        for i, x in enumerate((-0.62, 0.62)):
            mb.cylinder((x, y, 0.1), (x + 0.05, y, 0.9), 0.045, 0.03, "log", segments=5)
            mb.sphere((x - 0.28, y, 1.2), 0.36, "gm_vine" if (i + j) % 2 else "leaves", segments=6, rings=3,
                      scale=(1, 0.45, 0.95))
            mb.sphere((x + 0.3, y, 1.12), 0.34, "leaves" if (i + j) % 2 else "gm_vine", segments=6, rings=3,
                      scale=(1, 0.45, 0.95))
            for dx, dz in ((-0.4, 0.95), (0.0, 0.88), (0.42, 0.8)):
                mb.cylinder((x + dx, y - 0.14, dz), (x + dx, y - 0.14, dz - 0.26), 0.08, 0.02, "gm_bloom_purple",
                            segments=5)
    # A basket of picked grapes at the front.
    mb.cylinder((0.9, -1.2, 0.06), (0.9, -1.2, 0.3), 0.16, 0.2, "thatch_dark", segments=8)
    heap(mb, 0.9, -1.2, 0.26, "gm_bloom_purple", r=0.07)
    buildings.export(folder, "decor_grape_trellis", mb)


def tool_corner(folder):
    common.reset_scene()
    mb = MeshBuilder()
    paving(mb, 2)
    # A rain barrel under a wooden spout, on a stone slab.
    mb.box((-0.45, 0.4, 0.1), (0.85, 0.85, 0.1), "stone")
    for a, b, r1, r2 in ((0.14, 0.6, 0.33, 0.4), (0.6, 1.1, 0.4, 0.34)):
        mb.cylinder((-0.45, 0.4, a), (-0.45, 0.4, b), r1, r2, "wood", segments=10)
    for z in (0.32, 0.92):
        mb.cylinder((-0.45, 0.4, z - 0.03), (-0.45, 0.4, z + 0.03), 0.385, 0.385, "iron", segments=10)
    mb.cylinder((-0.45, 0.4, 1.08), (-0.45, 0.4, 1.11), 0.3, 0.3, "water", segments=10)
    mb.box((-0.45, 0.82, 1.2), (0.1, 0.1, 2.3), "timber")
    obox(mb, (-0.45, 0.6, 1.85), (0.14, 0.6, 0.08), Matrix.Rotation(-0.5, 3, "X"), "wood_light")
    # A rail with garden tools leaning on it.
    for x in (0.1, 0.82):
        mb.box((x, 0.8, 0.7), (0.08, 0.08, 1.3), "timber")
    mb.box((0.46, 0.8, 1.25), (0.85, 0.06, 0.08), "wood")
    for x in (0.25, 0.47, 0.68):
        mb.cylinder((x, 0.45, 0.08), (x, 0.74, 1.65), 0.022, 0.022, "wood_light", segments=4)
    mb.box((0.25, 0.43, 0.2), (0.18, 0.03, 0.28), "iron")
    mb.box((0.47, 0.42, 0.1), (0.3, 0.04, 0.04), "timber")
    for d in (-0.12, -0.04, 0.04, 0.12):
        mb.box((0.47 + d, 0.4, 0.05), (0.02, 0.02, 0.1), "iron")
    mb.box((0.68, 0.38, 0.1), (0.16, 0.14, 0.03), "iron")
    # A bucket, a watering can, a stack of pots and a sack.
    mb.cylinder((0.55, -0.35, 0.06), (0.55, -0.35, 0.36), 0.14, 0.18, "wood", segments=8)
    mb.cylinder((0.55, -0.35, 0.33), (0.55, -0.35, 0.37), 0.16, 0.16, "water", segments=8)
    mb.cylinder((0.0, -0.6, 0.06), (0.0, -0.6, 0.34), 0.15, 0.13, "iron", segments=8)
    mb.cylinder((0.1, -0.6, 0.15), (0.38, -0.6, 0.36), 0.03, 0.025, "iron", segments=5)
    mb.cylinder((0.38, -0.6, 0.36), (0.42, -0.6, 0.39), 0.03, 0.06, "iron", segments=6)
    mb.box((-0.14, -0.6, 0.25), (0.05, 0.04, 0.2), "iron")
    for k in range(3):
        mb.cylinder((-0.6, -0.55, 0.06 + k * 0.1), (-0.6, -0.55, 0.3 + k * 0.1), 0.11, 0.16, "gm_terracotta",
                    segments=8)
    bush(mb, -0.25, -0.2, 0.14, 0.14, "leaves")
    blooms(mb, [(-0.25, -0.25, 0.26), (-0.2, -0.14, 0.25)], 0.06)
    buildings.export(folder, "decor_tool_corner", mb)


def wine_press(folder):
    common.reset_scene()
    mb = MeshBuilder()
    paving(mb, 2)
    cy = 0.2
    # The frame: two heavy posts, a base beam and a top beam.
    mb.box((0, cy, 0.2), (1.7, 0.5, 0.28), "timber")
    for x in (-0.74, 0.74):
        mb.box((x, cy, 1.1), (0.16, 0.22, 1.9), "timber")
    mb.box((0, cy, 2.05), (1.76, 0.3, 0.22), "timber")
    # The slatted tub with iron hoops, its tray and spout.
    mb.cylinder((0, cy, 0.34), (0, cy, 0.42), 0.62, 0.62, "wood", segments=10)
    mb.cylinder((0, cy, 0.42), (0, cy, 1.0), 0.5, 0.5, "wood_light", segments=10)
    for z in (0.55, 0.88):
        mb.cylinder((0, cy, z - 0.03), (0, cy, z + 0.03), 0.52, 0.52, "iron", segments=10)
    mb.cylinder((0, cy, 0.99), (0, cy, 1.02), 0.44, 0.44, "gm_bloom_purple", segments=10)
    mb.box((0, cy - 0.68, 0.37), (0.14, 0.24, 0.06), "wood")
    # The screw, the press plate and the turning bar.
    mb.cylinder((0, cy, 1.05), (0, cy, 1.15), 0.4, 0.4, "wood", segments=10)
    mb.cylinder((0, cy, 1.15), (0, cy, 2.3), 0.06, 0.06, "iron", segments=6)
    for k in range(6):
        mb.cylinder((0, cy, 1.22 + k * 0.12), (0, cy, 1.25 + k * 0.12), 0.085, 0.085, "iron", segments=6)
    mb.cylinder((-0.5, cy - 0.35, 1.55), (0.5, cy + 0.35, 1.55), 0.035, 0.035, "wood_light", segments=5)
    mb.box((0, cy, 1.55), (0.2, 0.2, 0.14), "iron", rotation_z=0.6)
    # A bucket of juice under the spout, a basket of grapes and a small cask.
    mb.cylinder((0, -0.6, 0.06), (0, -0.6, 0.3), 0.13, 0.17, "wood", segments=8)
    mb.cylinder((0, -0.6, 0.27), (0, -0.6, 0.31), 0.15, 0.15, "gm_bloom_purple", segments=8)
    mb.cylinder((-0.62, -0.6, 0.06), (-0.62, -0.6, 0.32), 0.18, 0.24, "thatch_dark", segments=8)
    heap(mb, -0.62, -0.6, 0.28, "gm_bloom_purple", r=0.08)
    buildings.barrel(mb, 0.62, -0.58, h=0.55, r=0.22)
    buildings.export(folder, "decor_wine_press", mb)


def smith_rack(folder):
    common.reset_scene()
    mb = MeshBuilder()
    paving(mb, 2)
    # A display board on two posts under a narrow roof.
    for x in (-0.8, 0.8):
        mb.box((x, 0.6, 1.05), (0.1, 0.1, 2.0), "timber")
    mb.box((0, 0.62, 1.2), (1.6, 0.05, 1.3), "wood_light")
    for z in (0.6, 1.8):
        mb.box((0, 0.58, z), (1.6, 0.06, 0.08), "timber")
    buildings.sloped_slab(mb, -0.9, 0.9, 0.2, 0.85, 2.0, 2.2, 0.05, "roof")
    y = 0.56
    # Two swords, a round shield, an axe and a row of horseshoe hooks.
    for x in (-0.6, -0.35):
        mb.box((x, y, 1.2), (0.07, 0.02, 0.8), "stone")
        mb.box((x, y, 1.62), (0.24, 0.04, 0.05), "gold")
        mb.box((x, y, 1.71), (0.04, 0.04, 0.16), "timber")
    mb.cylinder((0.1, y - 0.03, 1.3), (0.1, y + 0.02, 1.3), 0.3, 0.3, "cloth_red", segments=10)
    mb.cylinder((0.1, y - 0.05, 1.3), (0.1, y - 0.03, 1.3), 0.31, 0.31, "iron", segments=10)[0:0]
    mb.cylinder((0.1, y - 0.06, 1.3), (0.1, y - 0.03, 1.3), 0.26, 0.26, "cloth_red", segments=10)
    mb.cylinder((0.1, y - 0.1, 1.3), (0.1, y - 0.06, 1.3), 0.04, 0.09, "gold", segments=6)
    mb.box((0.58, y, 1.2), (0.04, 0.04, 0.9), "wood_light")
    mb.box((0.58 - 0.12, y, 1.52), (0.24, 0.03, 0.22), "iron")
    for x in (-0.5, -0.25, 0.0, 0.25, 0.5):
        mb.box((x, y, 0.78), (0.12, 0.03, 0.12), "iron")
        mb.box((x, y - 0.005, 0.76), (0.06, 0.04, 0.1), "wood_light")
    # The anvil on its stump, with a hammer, and a tub of blades.
    mb.cylinder((-0.3, -0.35, 0.06), (-0.3, -0.35, 0.5), 0.26, 0.24, "log", segments=8)
    mb.box((-0.3, -0.35, 0.56), (0.3, 0.2, 0.12), "iron")
    mb.box((-0.3, -0.35, 0.68), (0.5, 0.24, 0.12), "iron")
    mb.cylinder((-0.05, -0.35, 0.68), (0.14, -0.35, 0.7), 0.07, 0.01, "iron", segments=5)
    mb.cylinder((-0.45, -0.4, 0.77), (-0.15, -0.3, 0.77), 0.018, 0.018, "wood_light", segments=4)
    mb.box((-0.43, -0.39, 0.77), (0.08, 0.14, 0.07), "charcoal", rotation_z=0.32)
    mb.cylinder((0.5, -0.5, 0.06), (0.5, -0.5, 0.5), 0.2, 0.24, "wood", segments=8)
    mb.cylinder((0.5, -0.5, 0.28), (0.5, -0.5, 0.33), 0.235, 0.235, "iron", segments=8)
    for dx, dy, lean in ((-0.08, 0.0, -0.1), (0.07, 0.06, 0.1), (0.02, -0.08, 0.02)):
        mb.box((0.5 + dx + lean * 0.5, -0.5 + dy, 0.75), (0.05, 0.02, 0.6), "stone")
        mb.box((0.5 + dx + lean * 0.5, -0.5 + dy, 1.06), (0.16, 0.04, 0.04), "gold")
        mb.box((0.5 + dx + lean * 0.5, -0.5 + dy, 1.14), (0.035, 0.035, 0.14), "timber")
    buildings.export(folder, "decor_smith_rack", mb)


MODELS = (market_stall, hedge_square, hay_cart, gazebo, barrel_stack, potted_tree, clothesline, pergola,
          haystacks, garden_arch, windmill_small, topiary, firewood_rack, fish_rack,
          scarecrow, beehives, vegetable_patch, dovecote, chicken_coop, pottery_stall, flower_cart, kennel,
          rug_tent, scale_stand, grape_trellis, tool_corner, wine_press, smith_rack)


def make_all(folder):
    os.makedirs(folder, exist_ok=True)
    for model in MODELS:
        model(folder)


if __name__ == "__main__":
    make_all(sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else ".")
