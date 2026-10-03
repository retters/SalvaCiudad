"""Plaza and street decorations: benches, lamp posts, a fountain, signs and the like.

Every model stands on a paved slab that fills most of its square footprint
(2, 3 or 4 meters), on Z = 0, centered on the origin, front toward -Y.

    blender --background --factory-startup --python art/blender/decor/plaza.py -- <output folder>
"""

import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from mathutils import Matrix, Vector

import buildings
import common
from common import MeshBuilder

buildings.COLORS.update({
    "plz_paving": common.rgb(0xB4AC9C),
    "plz_paving_dark": common.rgb(0x8C857A),
    "plz_paving_warm": common.rgb(0xA89880),
    "plz_glow": common.rgb(0xF4D272),
    "plz_paper": common.rgb(0xE9DFC2),
    "plz_water_light": common.rgb(0x86B8D0),
    "plz_bronze": common.rgb(0x8A6E3A),
    "plz_ink": common.rgb(0x3A3028),
    "plz_fire": common.rgb(0xF08A30),
    "plz_ember": common.rgb(0xD8482A),
})

SLAB = 0.12   # Height of the paved slab every model stands on.


# --- Helpers -------------------------------------------------------------------------------


def xform(verts, matrix):
    """Moves the vertices a MeshBuilder call returned (to tilt or turn a part)."""
    for v in verts:
        v.co = matrix @ v.co
    return verts


def turned(angle_z, origin=(0, 0, 0)):
    o = Vector(origin)
    return Matrix.Translation(o) @ Matrix.Rotation(angle_z, 4, "Z") @ Matrix.Translation(-o)


def paved_base(mb, size, tiles, mats=("plz_paving", "plz_paving_warm")):
    """A slab 0.1 m inside the footprint, with a grid of flagstones on it."""
    side = size - 0.2
    mb.box((0, 0, 0.04), (side, side, 0.08), "plz_paving_dark")
    step = (side - 0.06) / tiles
    for i in range(tiles):
        for j in range(tiles):
            x = -side / 2 + 0.03 + step * (i + 0.5)
            y = -side / 2 + 0.03 + step * (j + 0.5)
            mat = mats[(i + j) % 2]
            if (i * 7 + j * 3) % 5 == 0:
                mat = "stone"
            mb.box((x, y, 0.08 + (SLAB - 0.08) / 2), (step - 0.05, step - 0.05, SLAB - 0.08), mat)


def ring(mb, radius, z0, z1, thick, mat, segments=12):
    """A ring of blocks: the rim of a basin."""
    length = 2 * (radius + thick / 2) * math.tan(math.pi / segments)
    for k in range(segments):
        a = 2 * math.pi * k / segments
        mb.box((radius * math.cos(a), radius * math.sin(a), (z0 + z1) / 2),
               (thick, length, z1 - z0), mat, rotation_z=a)


def lantern(mb, x, y, z):
    """A four-sided lantern hanging from (x, y, z)."""
    mb.box((x, y, z - 0.04), (0.03, 0.03, 0.08), "iron")
    mb.cylinder((x, y, z - 0.2), (x, y, z - 0.08), 0.2, 0.03, "iron", segments=4)
    mb.box((x, y, z - 0.36), (0.2, 0.2, 0.3), "plz_glow", rotation_z=math.pi / 4)
    for k in range(4):
        a = k * math.pi / 2
        mb.box((x + 0.14 * math.cos(a), y + 0.14 * math.sin(a), z - 0.36), (0.03, 0.03, 0.32), "iron")
    mb.cylinder((x, y, z - 0.56), (x, y, z - 0.5), 0.1, 0.18, "iron", segments=4)


def plinth(mb, w, z0, h, mat="stone", cap="stone_dark"):
    mb.box((0, 0, z0 + h / 2), (w, w, h), mat)
    mb.box((0, 0, z0 + h + 0.04), (w + 0.1, w + 0.1, 0.08), cap)
    return z0 + h + 0.08


def bush(mb, x, y, z, r, flower=None):
    mb.sphere((x, y, z), r, "leaves", segments=7, rings=4, scale=(1, 1, 0.8))
    if flower:
        for k in range(2):
            a = k * 2.6 + x * 3 + y
            mb.sphere((x + r * 0.6 * math.cos(a), y + r * 0.6 * math.sin(a), z + r * 0.55), r * 0.28,
                      flower, segments=5, rings=3)


def planter_box(mb, x, y, w, d, z0, h, flower="flowers", mat="stone"):
    mb.box((x, y, z0 + h / 2), (w, d, h), mat)
    mb.box((x, y, z0 + h + 0.01), (w - 0.14, d - 0.14, 0.04), "soil")
    n = max(1, int(round(max(w, d) / 0.45)))
    for i in range(n):
        t = (i + 0.5) / n - 0.5
        px, py = (x + t * (w - 0.2), y) if w >= d else (x, y + t * (d - 0.2))
        bush(mb, px, py, z0 + h + 0.12, min(w, d) * 0.36, flower if i % 2 == 0 else "flowers_y")


def bench(mb, cx, cy, angle, length=1.5):
    """A wooden bench with a back; it faces -Y before turning."""
    m = turned(angle, (cx, cy, 0))
    z = SLAB
    for x in (-length / 2 + 0.12, length / 2 - 0.12):
        xform(mb.box((cx + x, cy, z + 0.21), (0.1, 0.46, 0.42), "stone_dark"), m)
        xform(mb.box((cx + x, cy + 0.2, z + 0.7), (0.08, 0.07, 0.56), "timber"), m)
    for k in range(3):
        xform(mb.box((cx, cy - 0.15 + k * 0.15, z + 0.45), (length, 0.13, 0.06), "wood"), m)
    for k in range(2):
        xform(mb.box((cx, cy + 0.25, z + 0.68 + k * 0.2), (length, 0.05, 0.15), "wood_light"), m)


# --- Models --------------------------------------------------------------------------------


def fountain(folder):
    common.reset_scene()
    mb = MeshBuilder()
    paved_base(mb, 4, 5)
    z = SLAB
    mb.cylinder((0, 0, z), (0, 0, z + 0.14), 1.78, 1.78, "stone_dark", segments=12)
    mb.cylinder((0, 0, z + 0.14), (0, 0, z + 0.4), 1.66, 1.66, "stone", segments=12)
    ring(mb, 1.52, z + 0.38, z + 0.66, 0.28, "stone")
    ring(mb, 1.52, z + 0.66, z + 0.72, 0.36, "stone_dark")
    mb.cylinder((0, 0, z + 0.4), (0, 0, z + 0.54), 1.45, 1.45, "water", segments=12)
    # The stem and its bowls.
    mb.cylinder((0, 0, z + 0.5), (0, 0, z + 0.8), 0.42, 0.34, "stone_dark", segments=8)
    mb.cylinder((0, 0, z + 0.8), (0, 0, z + 1.35), 0.22, 0.18, "stone", segments=8)
    mb.cylinder((0, 0, z + 1.35), (0, 0, z + 1.6), 0.2, 0.85, "stone", segments=12)
    mb.cylinder((0, 0, z + 1.6), (0, 0, z + 1.68), 0.9, 0.9, "stone_dark", segments=12)
    mb.cylinder((0, 0, z + 1.68), (0, 0, z + 1.71), 0.76, 0.76, "water", segments=12)
    mb.cylinder((0, 0, z + 1.68), (0, 0, z + 2.15), 0.14, 0.1, "stone", segments=8)
    mb.cylinder((0, 0, z + 2.15), (0, 0, z + 2.3), 0.1, 0.34, "stone", segments=8)
    mb.cylinder((0, 0, z + 2.3), (0, 0, z + 2.35), 0.36, 0.36, "stone_dark", segments=8)
    mb.cylinder((0, 0, z + 2.35), (0, 0, z + 2.38), 0.28, 0.28, "water", segments=8)
    mb.sphere((0, 0, z + 2.5), 0.13, "plz_bronze", segments=6, rings=4)
    mb.cylinder((0, 0, z + 2.6), (0, 0, z + 2.85), 0.05, 0.01, "plz_water_light", segments=5)
    # Water falling from bowl to bowl.
    for k in range(4):
        a = k * math.pi / 2 + math.pi / 4
        c, s = math.cos(a), math.sin(a)
        mb.cylinder((0.36 * c, 0.36 * s, z + 2.33), (0.42 * c, 0.42 * s, z + 1.7), 0.035, 0.05,
                    "plz_water_light", segments=5)
    for k in range(6):
        a = k * math.pi / 3
        c, s = math.cos(a), math.sin(a)
        mb.cylinder((0.9 * c, 0.9 * s, z + 1.66), (1.0 * c, 1.0 * s, z + 0.54), 0.03, 0.05,
                    "plz_water_light", segments=5)
        mb.cylinder((1.0 * c, 1.0 * s, z + 0.54), (1.0 * c, 1.0 * s, z + 0.56), 0.16, 0.16,
                    "plz_water_light", segments=6)
    buildings.export(folder, "decor_fountain", mb)


def lamp_post(folder):
    common.reset_scene()
    mb = MeshBuilder()
    paved_base(mb, 2, 3)
    z = plinth(mb, 0.5, SLAB, 0.4)
    mb.cylinder((0, 0, z), (0, 0, z + 0.3), 0.13, 0.08, "iron", segments=6)
    mb.cylinder((0, 0, z + 0.3), (0, 0, 3.2), 0.06, 0.05, "iron", segments=6)
    mb.cylinder((0, 0, 2.3), (0, 0, 2.38), 0.09, 0.09, "iron", segments=6)
    mb.sphere((0, 0, 3.24), 0.08, "iron", segments=6, rings=4)
    # A bracket with a brace, and the lantern under it.
    mb.cylinder((0, 0, 3.05), (0.55, 0, 3.05), 0.035, 0.03, "iron", segments=5)
    mb.cylinder((0, 0, 2.6), (0.42, 0, 3.03), 0.025, 0.025, "iron", segments=5)
    mb.sphere((0.58, 0, 3.05), 0.05, "iron", segments=5, rings=3)
    lantern(mb, 0.45, 0, 3.03)
    buildings.export(folder, "decor_lamp_post", mb)


def lamp_double(folder):
    common.reset_scene()
    mb = MeshBuilder()
    paved_base(mb, 2, 3)
    z = SLAB
    mb.cylinder((0, 0, z), (0, 0, z + 0.2), 0.42, 0.36, "stone_dark", segments=8)
    mb.cylinder((0, 0, z + 0.2), (0, 0, z + 0.6), 0.28, 0.24, "stone", segments=8)
    mb.cylinder((0, 0, z + 0.6), (0, 0, z + 0.68), 0.3, 0.3, "stone_dark", segments=8)
    mb.cylinder((0, 0, z + 0.68), (0, 0, 3.5), 0.08, 0.055, "timber", segments=6)
    mb.cylinder((0, 0, 3.5), (0, 0, 3.75), 0.09, 0.0, "iron", segments=6)
    mb.cylinder((-0.68, 0, 3.2), (0.68, 0, 3.2), 0.035, 0.035, "iron", segments=5)
    for s in (-1, 1):
        mb.cylinder((0, 0, 2.75), (s * 0.5, 0, 3.18), 0.025, 0.025, "iron", segments=5)
        mb.sphere((s * 0.7, 0, 3.2), 0.05, "iron", segments=5, rings=3)
        lantern(mb, s * 0.58, 0, 3.18)
    mb.cylinder((0, 0, 2.7), (0, 0, 2.78), 0.1, 0.1, "iron", segments=6)
    buildings.export(folder, "decor_lamp_double", mb)


def bench_pair(folder):
    common.reset_scene()
    mb = MeshBuilder()
    paved_base(mb, 3, 5)
    bench(mb, 0, 0.95, 0.0)
    bench(mb, 0, -0.95, math.pi)
    # A round planter between them.
    z = SLAB
    mb.cylinder((0, 0, z), (0, 0, z + 0.4), 0.4, 0.46, "stone", segments=8)
    mb.cylinder((0, 0, z + 0.4), (0, 0, z + 0.46), 0.5, 0.5, "stone_dark", segments=8)
    mb.cylinder((0, 0, z + 0.46), (0, 0, z + 0.48), 0.4, 0.4, "soil", segments=8)
    bush(mb, 0, 0, z + 0.62, 0.36, "flowers")
    buildings.export(folder, "decor_bench_pair", mb)


def arrow_board(mb, z, angle, length, mat):
    """A pointed board on the post, pointing along `angle`."""
    h = 0.22
    pts = [(0.0, -h / 2), (length - 0.2, -h / 2), (length, 0.0), (length - 0.2, h / 2), (0.0, h / 2)]
    verts = mb.prism(pts, -0.025, 0.025, mat)
    # The prism lies flat: stand it up (its Y becomes Z), then turn and lift it.
    place = Matrix.Translation((0, 0, z)) @ Matrix.Rotation(angle, 4, "Z")
    xform(verts, place @ Matrix.Translation((0.03, -0.09, 0)) @ Matrix.Rotation(math.pi / 2, 4, "X"))
    ink = mb.box((0, 0, 0), (length * 0.5, 0.012, 0.035), "plz_ink")
    xform(ink, place @ Matrix.Translation((0.03 + length * 0.42, -0.12, 0)))


def signpost(folder):
    common.reset_scene()
    mb = MeshBuilder()
    paved_base(mb, 2, 3)
    z = SLAB
    mb.cylinder((0, 0, z), (0, 0, z + 0.3), 0.34, 0.24, "stone", segments=7)
    for k in range(5):
        a = k * 1.26
        mb.sphere((0.36 * math.cos(a), 0.36 * math.sin(a), z + 0.08), 0.13, "stone_dark", segments=5, rings=3)
    mb.cylinder((0, 0, z + 0.2), (0, 0, 2.75), 0.075, 0.06, "timber", segments=6)
    mb.cylinder((0, 0, 2.75), (0, 0, 2.9), 0.09, 0.0, "timber", segments=6)
    arrow_board(mb, 2.5, common.radians(-15), 0.85, "wood_light")
    arrow_board(mb, 2.2, common.radians(170), 0.8, "wood")
    arrow_board(mb, 1.9, common.radians(-100), 0.7, "wood_light")
    arrow_board(mb, 1.6, common.radians(60), 0.6, "wood")
    buildings.export(folder, "decor_signpost", mb)


def notice_board(folder):
    common.reset_scene()
    mb = MeshBuilder()
    paved_base(mb, 2, 3)
    z = SLAB
    for x in (-0.72, 0.72):
        mb.box((x, 0, z + 0.1), (0.24, 0.3, 0.2), "stone_dark")
        mb.box((x, 0, z + 1.1), (0.12, 0.12, 2.2), "timber")
    mb.box((0, 0, z + 1.35), (1.36, 0.06, 1.0), "wood")
    mb.box((0, -0.01, z + 0.83), (1.36, 0.09, 0.07), "timber")
    mb.box((0, -0.01, z + 1.87), (1.36, 0.09, 0.07), "timber")
    # Papers pinned to it, a little crooked.
    papers = [(-0.4, 1.55, 0.3, 0.4, 0.06, "plz_paper"), (0.0, 1.45, 0.34, 0.26, -0.05, "cloth_white"),
              (0.42, 1.5, 0.26, 0.44, 0.03, "plz_paper"), (-0.3, 1.08, 0.36, 0.24, -0.04, "cloth_white"),
              (0.2, 1.1, 0.28, 0.3, 0.08, "plz_paper")]
    for px, pz, w, h, tilt, mat in papers:
        m = Matrix.Translation((px, -0.04, z + pz)) @ Matrix.Rotation(tilt, 4, "Y")
        xform(mb.box((0, 0, 0), (w, 0.012, h), mat), m)
        xform(mb.box((0, -0.006, h * 0.12), (w * 0.7, 0.012, 0.02), "plz_ink"), m)
        xform(mb.box((0, -0.006, -h * 0.1), (w * 0.7, 0.012, 0.02), "plz_ink"), m)
        xform(mb.box((0, -0.01, h * 0.4), (0.04, 0.02, 0.04), "cloth_red"), m)
    # A little shingled roof over it.
    for s in (-1, 1):
        m = Matrix.Translation((0, s * 0.2, z + 2.3)) @ Matrix.Rotation(s * common.radians(-32), 4, "X")
        xform(mb.box((0, 0, 0), (1.76, 0.56, 0.06), "roof"), m)
        xform(mb.box((0, s * 0.22, -0.02), (1.76, 0.12, 0.07), "roof_dark"), m)
    mb.box((0, 0, z + 2.46), (1.8, 0.1, 0.08), "roof_dark")
    mb.box((0, 0, z + 2.18), (1.56, 0.1, 0.1), "timber")
    buildings.export(folder, "decor_notice_board", mb)


def flagpole(folder):
    common.reset_scene()
    mb = MeshBuilder()
    paved_base(mb, 2, 3)
    z = SLAB
    mb.box((0, 0, z + 0.1), (1.0, 1.0, 0.2), "stone_dark")
    mb.box((0, 0, z + 0.3), (0.7, 0.7, 0.2), "stone")
    mb.box((0, 0, z + 0.55), (0.42, 0.42, 0.3), "stone")
    mb.box((0, 0, z + 0.72), (0.5, 0.5, 0.06), "stone_dark")
    mb.cylinder((0, 0, z + 0.7), (0, 0, 5.2), 0.06, 0.035, "wood_light", segments=6)
    mb.sphere((0, 0, 5.26), 0.09, "gold", segments=6, rings=4)
    mb.cylinder((0, 0, 4.0), (0, 0, 4.05), 0.07, 0.07, "iron", segments=6)
    # A long banner in three waving strips, with a forked tail.
    stand = Matrix.Rotation(math.pi / 2, 4, "X")
    top, bot = 5.05, 4.1
    strips = [(0.05, 0.3, 0.0, 0.07), (0.3, 0.52, 0.07, -0.05), (0.52, 0.7, -0.05, 0.05)]
    for x0, x1, y0, y1 in strips:
        ang = math.atan2(y1 - y0, x1 - x0)
        ln = math.hypot(x1 - x0, y1 - y0)
        m = Matrix.Translation((x0, y0, 0)) @ Matrix.Rotation(ang, 4, "Z") @ stand
        xform(mb.prism([(0, bot), (ln, bot), (ln, top), (0, top)], -0.01, 0.01, "cloth_red"), m)
        xform(mb.prism([(0, bot + 0.38), (ln, bot + 0.38), (ln, bot + 0.56), (0, bot + 0.56)],
                       -0.016, 0.016, "gold"), m)
    m = Matrix.Translation((0.7, 0.05, 0)) @ Matrix.Rotation(common.radians(-12), 4, "Z") @ stand
    xform(mb.prism([(0, bot + 0.56), (0.2, top), (0, top)], -0.01, 0.01, "cloth_red"), m)
    xform(mb.prism([(0, bot), (0.2, bot), (0, bot + 0.38)], -0.01, 0.01, "cloth_red"), m)
    buildings.export(folder, "decor_flagpole", mb)


def plaza_planter(folder):
    common.reset_scene()
    mb = MeshBuilder()
    paved_base(mb, 4, 5)
    z = SLAB
    # A raised octagonal bed with a small tree, and four stone bollards.
    mb.cylinder((0, 0, z), (0, 0, z + 0.12), 1.2, 1.2, "stone_dark", segments=8)
    ring(mb, 0.95, z + 0.1, z + 0.5, 0.22, "stone", segments=8)
    ring(mb, 0.95, z + 0.5, z + 0.56, 0.3, "stone_dark", segments=8)
    mb.cylinder((0, 0, z + 0.1), (0, 0, z + 0.44), 0.9, 0.9, "soil", segments=8)
    mb.cylinder((0, 0, z + 0.4), (0, 0, z + 1.5), 0.13, 0.09, "log", segments=6)
    mb.cylinder((0, 0, z + 1.2), (0.3, 0.15, z + 1.7), 0.06, 0.04, "log", segments=5)
    mb.sphere((0, 0, z + 2.05), 0.75, "leaves", segments=8, rings=5, scale=(1, 1, 0.85))
    mb.sphere((0.45, 0.25, z + 1.8), 0.45, "cloth_green", segments=7, rings=4)
    mb.sphere((-0.4, -0.2, z + 1.75), 0.42, "cloth_green", segments=7, rings=4)
    for k in range(5):
        a = k * 2 * math.pi / 5 + 0.3
        bush(mb, 0.6 * math.cos(a), 0.6 * math.sin(a), z + 0.52, 0.2, "flowers" if k % 2 else "flowers_y")
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * 1.55, sy * 1.55
            mb.cylinder((x, y, z), (x, y, z + 0.55), 0.14, 0.11, "stone", segments=6)
            mb.sphere((x, y, z + 0.6), 0.13, "stone_dark", segments=6, rings=4)
    buildings.export(folder, "decor_plaza_planter", mb)


def bell_frame(folder):
    common.reset_scene()
    mb = MeshBuilder()
    paved_base(mb, 3, 5)
    z = SLAB
    mb.box((0, 0, z + 0.08), (2.3, 1.5, 0.16), "stone_dark")
    for sx in (-1, 1):
        x = sx * 0.95
        mb.box((x, 0, z + 0.24), (0.2, 1.3, 0.16), "timber")
        mb.box((x, 0, z + 1.4), (0.16, 0.16, 2.5), "timber")
        for sy in (-1, 1):
            mb.cylinder((x, sy * 0.58, z + 0.3), (x, 0, z + 1.3), 0.05, 0.05, "wood", segments=5)
        mb.cylinder((x, 0, z + 1.9), (x - sx * 0.55, 0, z + 2.5), 0.05, 0.05, "wood", segments=5)
    mb.box((0, 0, z + 2.55), (2.2, 0.18, 0.18), "timber")
    # A little roof on the beam.
    for s in (-1, 1):
        m = Matrix.Translation((0, s * 0.3, z + 2.82)) @ Matrix.Rotation(s * common.radians(-30), 4, "X")
        xform(mb.box((0, 0, 0), (2.5, 0.75, 0.06), "roof"), m)
        xform(mb.box((0, s * 0.32, -0.02), (2.5, 0.12, 0.07), "roof_dark"), m)
    mb.box((0, 0, z + 3.03), (2.54, 0.1, 0.08), "roof_dark")
    # The bell, its yoke and its rope.
    mb.box((0, 0, z + 2.38), (0.5, 0.14, 0.16), "wood")
    mb.cylinder((0, 0, z + 2.14), (0, 0, z + 2.3), 0.2, 0.1, "bell", segments=10)
    mb.cylinder((0, 0, z + 1.7), (0, 0, z + 2.14), 0.34, 0.2, "bell", segments=10)
    mb.cylinder((0, 0, z + 1.6), (0, 0, z + 1.7), 0.44, 0.34, "bell", segments=10)
    mb.cylinder((0, 0, z + 1.58), (0, 0, z + 1.6), 0.38, 0.38, "plz_bronze", segments=10)
    mb.sphere((0, 0, z + 1.52), 0.08, "iron", segments=6, rings=4)
    mb.cylinder((0, 0, z + 1.5), (0.1, -0.25, z + 0.7), 0.02, 0.02, "wood_light", segments=4)
    buildings.export(folder, "decor_bell_frame", mb)


def hitching_post(folder):
    common.reset_scene()
    mb = MeshBuilder()
    paved_base(mb, 3, 5, mats=("plz_paving_warm", "plz_paving"))
    z = SLAB
    # The rail, at the back.
    for x in (-1.1, 0, 1.1):
        mb.cylinder((x, 0.85, z), (x, 0.85, z + 1.15), 0.09, 0.075, "timber", segments=6)
        mb.cylinder((x, 0.85, z + 1.15), (x, 0.85, z + 1.22), 0.1, 0.06, "timber", segments=6)
    mb.cylinder((-1.3, 0.85, z + 0.95), (1.3, 0.85, z + 0.95), 0.06, 0.06, "wood", segments=6)
    for x in (-0.55, 0.6):
        mb.cylinder((x - 0.01, 0.85, z + 0.95), (x + 0.03, 0.85, z + 0.95), 0.085, 0.085, "iron", segments=6)
        mb.cylinder((x, 0.82, z + 0.9), (x + 0.08, 0.6, z + 0.45), 0.018, 0.018, "wood_light", segments=4)
    # The trough: a hollowed stone block full of water.
    mb.box((0, -0.35, z + 0.07), (2.0, 0.7, 0.14), "stone_dark")
    for sy in (-1, 1):
        mb.box((0, -0.35 + sy * 0.34, z + 0.38), (2.1, 0.12, 0.48), "stone")
    for sx in (-1, 1):
        mb.box((sx * 0.99, -0.35, z + 0.38), (0.12, 0.56, 0.48), "stone")
    mb.box((0, -0.35, z + 0.3), (1.9, 0.6, 0.44), "water")
    # A bucket and a hay bale.
    buildings.barrel(mb, 1.05, 0.2, h=0.46, r=0.17)
    mb.box((-0.95, 0.25, z + 0.2), (0.7, 0.45, 0.4), "hay")
    for x in (-1.12, -0.78):
        mb.box((x, 0.25, z + 0.2), (0.04, 0.47, 0.42), "thatch_dark")
    buildings.export(folder, "decor_hitching_post", mb)


def planter_wall(folder):
    common.reset_scene()
    mb = MeshBuilder()
    paved_base(mb, 4, 5)
    z = SLAB
    # A low parapet like the one of a bridge, along the back, with piers and planters.
    y = 1.3
    mb.box((0, y, z + 0.08), (3.7, 0.6, 0.16), "stone_dark")
    for i in range(9):
        x = -1.6 + i * 0.4
        mb.box((x, y, z + 0.3), (0.37, 0.4, 0.26), "stone" if i % 2 else "plz_paving")
    for i in range(8):
        x = -1.4 + i * 0.4
        mb.box((x, y, z + 0.57), (0.37, 0.4, 0.26), "plz_paving" if i % 3 else "stone")
    mb.box((0, y, z + 0.74), (3.5, 0.5, 0.08), "stone_dark")
    for x in (-1.6, 0, 1.6):
        mb.box((x, y, z + 0.5), (0.5, 0.56, 1.0), "stone")
        mb.box((x, y, z + 1.04), (0.6, 0.66, 0.08), "stone_dark")
    for x in (-1.6, 1.6):
        mb.cylinder((x, y, z + 1.08), (x, y, z + 1.3), 0.14, 0.22, "clay", segments=7)
        bush(mb, x, y, z + 1.4, 0.24, "flowers")
    # Planters before the wall.
    for x in (-0.82, 0.82):
        planter_box(mb, x, 0.72, 1.1, 0.42, z, 0.34, "flowers" if x < 0 else "berries", mat="plz_paving_warm")
    # Side wings stepping down toward the front.
    for sx in (-1, 1):
        x = sx * 1.65
        mb.box((x, 0.55, z + 0.3), (0.36, 1.0, 0.6), "stone")
        mb.box((x, 0.55, z + 0.63), (0.44, 1.0, 0.07), "stone_dark")
        mb.box((x, -0.25, z + 0.2), (0.36, 0.6, 0.4), "plz_paving")
        mb.box((x, -0.25, z + 0.43), (0.44, 0.6, 0.07), "stone_dark")
        mb.cylinder((x, -0.75, z), (x, -0.75, z + 0.6), 0.2, 0.17, "stone", segments=6)
        mb.sphere((x, -0.75, z + 0.66), 0.17, "stone_dark", segments=6, rings=4)
    buildings.export(folder, "decor_planter_wall", mb)


def sundial(folder):
    common.reset_scene()
    mb = MeshBuilder()
    paved_base(mb, 2, 3)
    z = SLAB
    mb.cylinder((0, 0, z), (0, 0, z + 0.12), 0.8, 0.8, "stone_dark", segments=8)
    mb.cylinder((0, 0, z + 0.12), (0, 0, z + 0.24), 0.6, 0.6, "stone", segments=8)
    mb.cylinder((0, 0, z + 0.24), (0, 0, z + 0.4), 0.3, 0.24, "stone_dark", segments=8)
    mb.cylinder((0, 0, z + 0.4), (0, 0, z + 1.0), 0.19, 0.16, "stone", segments=8)
    mb.cylinder((0, 0, z + 1.0), (0, 0, z + 1.12), 0.16, 0.42, "stone", segments=8)
    mb.cylinder((0, 0, z + 1.12), (0, 0, z + 1.2), 0.48, 0.48, "stone_dark", segments=12)
    mb.cylinder((0, 0, z + 1.2), (0, 0, z + 1.23), 0.42, 0.42, "plz_bronze", segments=12)
    # Hour marks around the back half, and the gnomon: a triangle standing on the dial.
    for k in range(9):
        a = math.pi * k / 8
        mb.box((0.33 * math.cos(a), 0.33 * math.sin(a), z + 1.24), (0.1, 0.03, 0.012), "plz_ink", rotation_z=a)
    g = mb.prism([(-0.3, 0), (0.25, 0), (0.25, 0.32)], -0.015, 0.015, "gold")
    xform(g, Matrix.Translation((0, 0, z + 1.23)) @ Matrix.Rotation(math.pi / 2, 4, "Z")
          @ Matrix.Rotation(math.pi / 2, 4, "X"))
    buildings.export(folder, "decor_sundial_pillar", mb)


def pillory(folder):
    common.reset_scene()
    mb = MeshBuilder()
    paved_base(mb, 2, 3)
    z = SLAB
    # A plank platform with a step.
    mb.box((0, 0.1, z + 0.15), (1.6, 1.3, 0.1), "timber")
    for i in range(5):
        mb.box((-0.64 + i * 0.32, 0.1, z + 0.23), (0.3, 1.34, 0.06), "wood" if i % 2 else "wood_light")
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.box((sx * 0.72, 0.1 + sy * 0.57, z + 0.1), (0.12, 0.12, 0.2), "timber")
    mb.box((0, -0.72, z + 0.07), (0.8, 0.26, 0.14), "wood")
    top = z + 0.26
    for x in (-0.6, 0.6):
        mb.box((x, 0.2, top + 0.85), (0.14, 0.14, 1.7), "timber")
        mb.cylinder((x, 0.2, top + 1.7), (x, 0.2, top + 1.82), 0.1, 0.0, "timber", segments=4)
        mb.cylinder((x, 0.6, top), (x, 0.24, top + 0.7), 0.04, 0.04, "wood", segments=5)
    # The two boards, with holes for head and hands, and iron straps.
    mb.box((0, 0.2, top + 1.2), (1.3, 0.08, 0.22), "wood")
    mb.box((0, 0.2, top + 1.44), (1.3, 0.08, 0.22), "wood_light")
    for hx, r in ((0.0, 0.13), (-0.38, 0.07), (0.38, 0.07)):
        mb.cylinder((hx, 0.15, top + 1.32), (hx, 0.25, top + 1.32), r, r, "charcoal", segments=8)
    for x in (-0.62, 0.62):
        mb.box((x, 0.15, top + 1.32), (0.1, 0.03, 0.4), "iron")
    mb.box((0.56, 0.13, top + 1.32), (0.07, 0.05, 0.09), "iron")
    buildings.export(folder, "decor_pillory", mb)


def pitched_roof(mb, length, z, half, deg=30.0):
    """A small two-slope roof along X, its eaves at height z."""
    slope = half / math.cos(common.radians(deg))
    rise = half * math.tan(common.radians(deg))
    for s in (-1, 1):
        m = (Matrix.Translation((0, s * half / 2, z + rise / 2))
             @ Matrix.Rotation(s * common.radians(-deg), 4, "X"))
        xform(mb.box((0, 0, 0), (length, slope, 0.06), "roof"), m)
        xform(mb.box((0, s * (slope / 2 - 0.06), -0.02), (length, 0.12, 0.07), "roof_dark"), m)
    mb.box((0, 0, z + rise + 0.02), (length + 0.04, 0.1, 0.08), "roof_dark")
    return z + rise


def plaza_well(folder):
    common.reset_scene()
    mb = MeshBuilder()
    paved_base(mb, 3, 5)
    z = SLAB
    mb.cylinder((0, 0, z), (0, 0, z + 0.12), 1.2, 1.2, "stone_dark", segments=10)
    ring(mb, 0.72, z + 0.1, z + 0.8, 0.22, "stone", segments=10)
    ring(mb, 0.72, z + 0.8, z + 0.87, 0.3, "stone_dark", segments=10)
    mb.cylinder((0, 0, z + 0.1), (0, 0, z + 0.55), 0.66, 0.66, "water", segments=10)
    for x in (-1.0, 1.0):
        mb.box((x, 0, z + 1.25), (0.14, 0.14, 2.3), "timber")
        mb.cylinder((x, 0, z + 1.9), (x * 0.5, 0, z + 2.35), 0.04, 0.04, "wood", segments=5)
    mb.box((0, 0, z + 2.4), (2.2, 0.14, 0.14), "timber")
    # The windlass with its crank, the rope and the bucket.
    mb.cylinder((-1.0, 0, z + 1.5), (1.0, 0, z + 1.5), 0.09, 0.09, "wood", segments=7)
    mb.cylinder((-0.3, 0, z + 1.5), (0.3, 0, z + 1.5), 0.12, 0.12, "wood_light", segments=7)
    mb.cylinder((1.0, 0, z + 1.5), (1.2, 0, z + 1.5), 0.025, 0.025, "iron", segments=4)
    mb.cylinder((1.2, 0, z + 1.5), (1.2, 0, z + 1.25), 0.025, 0.025, "iron", segments=4)
    mb.cylinder((0.1, -0.1, z + 1.45), (0.1, -0.1, z + 1.1), 0.018, 0.018, "wood_light", segments=4)
    mb.cylinder((0.1, -0.1, z + 0.85), (0.1, -0.1, z + 1.1), 0.12, 0.15, "wood", segments=7)
    mb.cylinder((0.1, -0.1, z + 0.95), (0.1, -0.1, z + 1.0), 0.145, 0.15, "iron", segments=7)
    pitched_roof(mb, 2.6, z + 2.45, 0.8)
    buildings.export(folder, "decor_plaza_well", mb)


def market_cross(folder):
    common.reset_scene()
    mb = MeshBuilder()
    paved_base(mb, 3, 5)
    z = SLAB
    for k, r in enumerate((1.3, 1.02, 0.74)):
        mb.cylinder((0, 0, z + k * 0.2), (0, 0, z + k * 0.2 + 0.2), r, r, "stone" if k % 2 else "stone_dark",
                    segments=8)
    z += 0.6
    mb.box((0, 0, z + 0.3), (0.6, 0.6, 0.6), "stone")
    mb.box((0, 0, z + 0.64), (0.72, 0.72, 0.08), "stone_dark")
    mb.cylinder((0, 0, z + 0.68), (0, 0, z + 2.5), 0.17, 0.12, "stone", segments=8)
    mb.cylinder((0, 0, z + 2.5), (0, 0, z + 2.6), 0.14, 0.24, "stone_dark", segments=8)
    mb.box((0, 0, z + 2.66), (0.44, 0.44, 0.12), "stone")
    # The cross, with a ring behind its arms.
    mb.box((0, 0, z + 3.1), (0.16, 0.14, 0.9), "stone")
    mb.box((0, 0, z + 3.2), (0.7, 0.14, 0.16), "stone")
    ring_verts = []
    for k in range(8):
        a = k * math.pi / 4 + math.pi / 8
        ring_verts += mb.box((0.25 * math.cos(a), 0.25 * math.sin(a), 0), (0.06, 0.22, 0.08), "stone_dark",
                             rotation_z=a)
    xform(ring_verts, Matrix.Translation((0, 0, z + 3.2)) @ Matrix.Rotation(math.pi / 2, 4, "X"))
    # Offerings on the steps.
    bush(mb, 0.8, -0.75, SLAB + 0.3, 0.16, "flowers")
    buildings.crate(mb, -0.85, -0.7, s=0.3, z=SLAB + 0.2, top="bread")
    buildings.export(folder, "decor_market_cross", mb)


def brazier(mb, x, y):
    z = SLAB
    mb.cylinder((x, y, z), (x, y, z + 0.14), 0.36, 0.32, "stone_dark", segments=8)
    for k in range(3):
        a = k * 2 * math.pi / 3 + math.pi / 2
        c, s = math.cos(a), math.sin(a)
        mb.cylinder((x + 0.27 * c, y + 0.27 * s, z + 0.14), (x + 0.1 * c, y + 0.1 * s, z + 0.95), 0.025, 0.025,
                    "iron", segments=4)
    mb.cylinder((x, y, z + 0.55), (x, y, z + 0.58), 0.17, 0.17, "iron", segments=6)
    mb.cylinder((x, y, z + 0.9), (x, y, z + 1.15), 0.12, 0.32, "iron", segments=8)
    mb.cylinder((x, y, z + 1.15), (x, y, z + 1.2), 0.34, 0.34, "iron", segments=8)
    mb.cylinder((x, y, z + 1.2), (x, y, z + 1.24), 0.28, 0.28, "charcoal", segments=8)
    mb.cylinder((x, y, z + 1.22), (x, y, z + 1.75), 0.2, 0.0, "plz_fire", segments=5)
    mb.cylinder((x + 0.1, y + 0.05, z + 1.22), (x + 0.14, y + 0.05, z + 1.5), 0.1, 0.0, "plz_ember", segments=4)
    mb.cylinder((x - 0.1, y - 0.06, z + 1.22), (x - 0.13, y - 0.06, z + 1.55), 0.1, 0.0, "plz_glow", segments=4)


def brazier_pair(folder):
    common.reset_scene()
    mb = MeshBuilder()
    paved_base(mb, 2, 3)
    brazier(mb, -0.45, 0)
    brazier(mb, 0.45, 0)
    buildings.export(folder, "decor_brazier_pair", mb)


def flower_pedestal(folder):
    common.reset_scene()
    mb = MeshBuilder()
    paved_base(mb, 2, 3)
    z = SLAB
    mb.box((0, 0, z + 0.1), (1.3, 1.3, 0.2), "stone_dark")
    mb.box((0, 0, z + 0.3), (1.0, 1.0, 0.2), "stone")
    mb.box((0, 0, z + 0.8), (0.7, 0.7, 0.8), "stone")
    mb.box((0, -0.36, z + 0.8), (0.4, 0.03, 0.4), "plz_bronze")
    mb.box((0, 0, z + 1.25), (0.86, 0.86, 0.1), "stone_dark")
    mb.box((0, 0, z + 1.32), (0.66, 0.66, 0.06), "soil")
    # No statue: the pedestal has become a flower bed, with ivy hanging down.
    bush(mb, 0, 0, z + 1.55, 0.34, "flowers")
    bush(mb, 0.22, -0.2, z + 1.42, 0.18, "flowers_y")
    bush(mb, -0.24, 0.18, z + 1.42, 0.18, "berries")
    mb.box((0.36, 0.1, z + 1.0), (0.04, 0.2, 0.5), "leaves")
    mb.box((-0.1, 0.36, z + 1.05), (0.24, 0.04, 0.42), "leaves")
    mb.box((-0.36, -0.15, z + 1.12), (0.04, 0.16, 0.3), "cloth_green")
    for sx, sy in ((-1, -1), (1, 1)):
        mb.cylinder((sx * 0.62, sy * 0.62, z), (sx * 0.62, sy * 0.62, z + 0.3), 0.12, 0.17, "clay", segments=6)
        bush(mb, sx * 0.62, sy * 0.62, z + 0.4, 0.17, "flowers_y" if sx < 0 else "flowers")
    buildings.export(folder, "decor_flower_pedestal", mb)


def stage(folder):
    common.reset_scene()
    mb = MeshBuilder()
    paved_base(mb, 4, 5)
    z = SLAB
    # The platform: posts, a skirt and planks.
    cy, w, d, h = 0.4, 3.4, 2.4, 0.7
    for sx in (-1, 0, 1):
        for sy in (-1, 1):
            mb.box((sx * (w / 2 - 0.1), cy + sy * (d / 2 - 0.1), z + h / 2), (0.16, 0.16, h), "timber")
    mb.box((0, cy, z + h - 0.12), (w, d, 0.12), "timber")
    for i in range(8):
        mb.box((0, cy - d / 2 + (i + 0.5) * d / 8, z + h + 0.025), (w + 0.06, d / 8 - 0.02, 0.05),
               "wood" if i % 2 else "wood_light")
    mb.box((0, cy - d / 2 + 0.02, z + h * 0.4), (w - 0.3, 0.03, h * 0.6), "cloth_blue")
    for k in range(2):
        mb.box((-0.9, cy - d / 2 - 0.2 - k * 0.3, z + (h - 0.24 - k * 0.23) / 2),
               (0.9, 0.3, h - 0.24 - k * 0.23), "wood")
    top = z + h + 0.05
    # The backdrop: two masts, a beam, a curtain and pennants.
    by = cy + d / 2 - 0.12
    for x in (-1.55, 1.55):
        mb.box((x, by, top + 1.2), (0.12, 0.12, 2.4), "timber")
        mb.sphere((x, by, top + 2.46), 0.09, "gold", segments=6, rings=4)
    mb.box((0, by, top + 2.25), (3.3, 0.1, 0.12), "timber")
    for i in range(6):
        x = -1.25 + i * 0.5
        mb.box((x, by, top + 1.3), (0.48, 0.04 + 0.03 * (i % 2), 1.8), "cloth_red" if i % 2 else "roof_dark")
    mb.box((0, by - 0.03, top + 2.1), (3.0, 0.05, 0.14), "gold")
    # A lectern and a stool.
    mb.box((0.8, cy - 0.5, top + 0.5), (0.1, 0.1, 1.0), "timber")
    xform(mb.box((0, 0, 0), (0.5, 0.36, 0.05), "wood_light"),
          Matrix.Translation((0.8, cy - 0.5, top + 1.02)) @ Matrix.Rotation(common.radians(25), 4, "X"))
    mb.box((0.8, cy - 0.5, top + 0.03), (0.4, 0.4, 0.06), "wood")
    buildings.export(folder, "decor_stage", mb)


def milestone(folder):
    common.reset_scene()
    mb = MeshBuilder()
    paved_base(mb, 2, 3, mats=("plz_paving_warm", "plz_paving"))
    z = SLAB
    mb.box((0, 0, z + 0.08), (1.0, 0.8, 0.16), "stone_dark")
    xform(mb.box((0, 0, 0.55), (0.6, 0.3, 1.1), "stone"),
          Matrix.Translation((0, 0, z + 0.1)) @ Matrix.Rotation(common.radians(4), 4, "Y"))
    xform(mb.cylinder((0, -0.15, 1.1), (0, 0.15, 1.1), 0.3, 0.3, "stone", segments=10),
          Matrix.Translation((0, 0, z + 0.1)) @ Matrix.Rotation(common.radians(4), 4, "Y"))
    # Carved marks on the front, moss, rocks and tufts of grass around it.
    for k, wd in enumerate((0.3, 0.4, 0.22)):
        mb.box((0.06, -0.155, z + 1.05 - k * 0.2), (wd, 0.02, 0.06), "plz_ink")
    mb.box((-0.16, -0.16, z + 0.36), (0.22, 0.03, 0.3), "leaves")
    mb.sphere((0.55, -0.35, z + 0.08), 0.18, "stone_dark", segments=5, rings=3)
    mb.sphere((-0.6, 0.3, z + 0.06), 0.14, "stone", segments=5, rings=3)
    for gx, gy in ((-0.5, -0.4), (0.45, 0.42), (0.62, 0.05), (-0.3, 0.5)):
        for k in range(3):
            a = k * 2.1 + gx * 5
            mb.cylinder((gx, gy, z), (gx + 0.1 * math.cos(a), gy + 0.1 * math.sin(a), z + 0.3), 0.05, 0.0,
                        "leaves" if k else "cloth_green", segments=4)
    buildings.export(folder, "decor_milestone", mb)


def tree_bench(folder):
    common.reset_scene()
    mb = MeshBuilder()
    paved_base(mb, 4, 5)
    z = SLAB
    # A cobbled round, a ring of soil, the tree and a bench all around it.
    mb.cylinder((0, 0, z), (0, 0, z + 0.06), 1.8, 1.8, "plz_paving_dark", segments=12)
    ring(mb, 1.55, z + 0.04, z + 0.1, 0.3, "stone", segments=12)
    ring(mb, 1.2, z + 0.04, z + 0.09, 0.3, "plz_paving_warm", segments=12)
    mb.cylinder((0, 0, z + 0.04), (0, 0, z + 0.14), 0.5, 0.5, "soil", segments=8)
    mb.cylinder((0, 0, z), (0, 0, z + 1.2), 0.3, 0.2, "log", segments=7)
    mb.cylinder((0, 0, z + 1.2), (0, 0, z + 2.6), 0.2, 0.12, "log", segments=7)
    mb.cylinder((0, 0, z + 1.7), (0.7, 0.3, z + 2.5), 0.09, 0.05, "log", segments=5)
    mb.cylinder((0, 0, z + 1.9), (-0.6, -0.4, z + 2.6), 0.09, 0.05, "log", segments=5)
    mb.sphere((0, 0, z + 3.4), 1.15, "leaves", segments=8, rings=5, scale=(1, 1, 0.8))
    mb.sphere((0.85, 0.35, z + 2.9), 0.7, "cloth_green", segments=7, rings=4)
    mb.sphere((-0.75, -0.5, z + 2.95), 0.72, "cloth_green", segments=7, rings=4)
    mb.sphere((-0.3, 0.8, z + 3.0), 0.6, "leaves", segments=7, rings=4)
    ring(mb, 0.72, z + 0.42, z + 0.48, 0.2, "wood", segments=8)
    ring(mb, 0.93, z + 0.42, z + 0.48, 0.2, "wood_light", segments=8)
    ring(mb, 0.56, z + 0.48, z + 0.9, 0.05, "wood", segments=8)
    for k in range(8):
        a = k * math.pi / 4 + math.pi / 8
        mb.box((0.84 * math.cos(a), 0.84 * math.sin(a), z + 0.21), (0.4, 0.08, 0.42), "timber", rotation_z=a)
    buildings.export(folder, "decor_tree_bench", mb)


def banner_arch(folder):
    common.reset_scene()
    mb = MeshBuilder()
    paved_base(mb, 4, 5)
    z = SLAB
    # Two stone piers with timber masts, a beam between them, and pennants: the street passes under.
    for x in (-1.5, 1.5):
        mb.box((x, 0, z + 0.1), (0.8, 0.8, 0.2), "stone_dark")
        mb.box((x, 0, z + 0.65), (0.6, 0.6, 0.9), "stone")
        mb.box((x, 0, z + 1.14), (0.7, 0.7, 0.08), "stone_dark")
        mb.box((x, 0, z + 2.4), (0.18, 0.18, 2.5), "timber")
        mb.cylinder((x, 0, z + 3.65), (x, 0, z + 3.9), 0.12, 0.0, "roof_dark", segments=4)
        s = -1 if x > 0 else 1
        mb.cylinder((x, 0, z + 2.7), (x + s * 0.7, 0, z + 3.4), 0.05, 0.05, "wood", segments=5)
        lantern(mb, x, -0.3, z + 2.3)
        mb.cylinder((x, 0, z + 2.3), (x, -0.34, z + 2.3), 0.025, 0.025, "iron", segments=4)
        for sy in (-1, 1):
            bush(mb, x, sy * 0.62, z + 0.2, 0.2, "flowers" if sy < 0 else "flowers_y")
    mb.box((0, 0, z + 3.45), (3.4, 0.14, 0.16), "timber")
    stand = Matrix.Rotation(math.pi / 2, 4, "X")
    cloths = ("cloth_red", "gold", "cloth_blue", "cloth_white", "cloth_green")
    for i in range(9):
        x = -1.2 + i * 0.3
        drop = 0.5 if i % 2 == 0 else 0.36
        verts = mb.prism([(-0.13, 0), (0, -drop), (0.13, 0)], -0.01, 0.01, cloths[i % 5])
        xform(verts, Matrix.Translation((x, 0, z + 3.37)) @ Matrix.Rotation(0.12 * (i % 3 - 1), 4, "Z") @ stand)
    # A long cloth with the town colors, hung in the middle.
    mb.box((0, 0.0, z + 3.62), (1.6, 0.04, 0.36), "cloth_red")
    mb.box((0, -0.01, z + 3.62), (1.6, 0.05, 0.1), "gold")
    buildings.export(folder, "decor_banner_arch", mb)


def public_oven(folder):
    common.reset_scene()
    mb = MeshBuilder()
    paved_base(mb, 3, 5)
    z = SLAB
    # A stone table with a clay dome on it, its mouth to the front, and a chimney behind.
    mb.box((0.2, 0.3, z + 0.35), (2.0, 1.9, 0.7), "stone")
    mb.box((0.2, 0.3, z + 0.74), (2.1, 2.0, 0.08), "stone_dark")
    mb.sphere((0.2, 0.4, z + 0.78), 0.9, "plaster_warm", segments=10, rings=6, scale=(1, 1, 0.85))
    mb.box((0.2, -0.38, z + 1.02), (0.74, 0.3, 0.56), "brick")
    mb.box((0.2, -0.54, z + 0.98), (0.46, 0.04, 0.4), "charcoal")
    mb.box((0.2, -0.55, z + 0.84), (0.3, 0.04, 0.1), "plz_fire")
    mb.box((0.2, -0.38, z + 1.33), (0.84, 0.36, 0.08), "stone_dark")
    mb.box((0.2, 0.95, z + 1.5), (0.4, 0.4, 1.5), "brick")
    mb.box((0.2, 0.95, z + 2.28), (0.5, 0.5, 0.1), "stone_dark")
    mb.box((0.2, -0.3, z + 0.3), (0.7, 0.72, 0.36), "charcoal")
    for k in range(3):
        mb.cylinder((0.0 + k * 0.2, -0.64, z + 0.22), (0.0 + k * 0.2, -0.1, z + 0.22), 0.09, 0.09, "log", segments=6)
    # A peel leaning on it, and a bench with loaves.
    mb.cylinder((1.1, -0.9, z), (0.95, -0.72, z + 1.5), 0.025, 0.025, "wood_light", segments=4)
    xform(mb.box((0, 0, 0), (0.3, 0.04, 0.36), "wood_light"),
          Matrix.Translation((0.93, -0.7, z + 1.66)) @ Matrix.Rotation(0.7, 4, "Z"))
    mb.box((-1.1, -0.2, z + 0.55), (0.5, 1.4, 0.06), "wood")
    for y in (-0.8, 0.4):
        mb.box((-1.1, y, z + 0.26), (0.4, 0.08, 0.52), "timber")
    for k in range(4):
        mb.sphere((-1.1, -0.7 + k * 0.33, z + 0.64), 0.13, "bread", segments=6, rings=3, scale=(1.2, 0.9, 0.6))
    buildings.export(folder, "decor_public_oven", mb)


def cart_stand(folder):
    common.reset_scene()
    mb = MeshBuilder()
    paved_base(mb, 3, 5, mats=("plz_paving_warm", "plz_paving"))
    z = SLAB
    r = 0.42
    # A two-wheeled cart resting on its shafts, loaded.
    bed = z + r + 0.1
    mb.box((0, 0.25, bed), (1.2, 1.7, 0.08), "wood")
    for sx in (-1, 1):
        mb.box((sx * 0.62, 0.25, bed + 0.2), (0.06, 1.7, 0.36), "wood_light")
        mb.box((sx * 0.62, 0.25, bed + 0.4), (0.08, 1.76, 0.06), "timber")
        x = sx * 0.76
        mb.cylinder((x - 0.04, 0.3, z + r), (x + 0.04, 0.3, z + r), r, r, "timber", segments=12)
        mb.cylinder((x - 0.05, 0.3, z + r), (x + 0.05, 0.3, z + r), r - 0.08, r - 0.08, "wood_light", segments=12)
        mb.cylinder((x - 0.08, 0.3, z + r), (x + 0.08, 0.3, z + r), 0.09, 0.09, "iron", segments=6)
        for k in range(4):
            a = k * math.pi / 4
            mb.cylinder((x + sx * 0.055, 0.3 - (r - 0.06) * math.cos(a), z + r - (r - 0.06) * math.sin(a)),
                        (x + sx * 0.055, 0.3 + (r - 0.06) * math.cos(a), z + r + (r - 0.06) * math.sin(a)),
                        0.025, 0.025, "timber", segments=4)
        mb.cylinder((sx * 0.5, -0.55, bed - 0.04), (sx * 0.5, -1.3, z + 0.5), 0.04, 0.035, "timber", segments=5)
    mb.box((0, 1.1, bed + 0.2), (1.2, 0.06, 0.36), "wood_light")
    mb.cylinder((-0.7, 0.3, z + r), (0.7, 0.3, z + r), 0.045, 0.045, "iron", segments=5)
    mb.cylinder((-0.5, -1.28, z + 0.5), (0.5, -1.28, z + 0.5), 0.035, 0.035, "timber", segments=5)
    for sx in (-1, 1):
        mb.box((sx * 0.4, -0.45, z + (bed - z) / 2), (0.08, 0.08, bed - z), "timber")
    mb.cylinder((-0.3, -1.28, z), (-0.3, -1.28, z + 0.5), 0.03, 0.03, "wood", segments=4)
    mb.cylinder((0.3, -1.28, z), (0.3, -1.28, z + 0.5), 0.03, 0.03, "wood", segments=4)
    # The load: sacks, a crate and hay.
    mb.box((0, 0.75, bed + 0.26), (1.1, 0.6, 0.44), "hay")
    buildings.crate(mb, -0.26, 0.1, s=0.46, z=bed + 0.04, top="berries")
    mb.sphere((0.3, 0.15, bed + 0.24), 0.26, "plz_paper", segments=6, rings=4, scale=(1, 1.1, 0.8))
    mb.sphere((0.25, -0.3, bed + 0.2), 0.22, "hide", segments=6, rings=4, scale=(1, 1, 0.8))
    buildings.barrel(mb, 1.12, -0.9, h=0.6, r=0.24)
    buildings.export(folder, "decor_cart_stand", mb)


def crier_stand(folder):
    common.reset_scene()
    mb = MeshBuilder()
    paved_base(mb, 2, 3)
    z = SLAB
    # A little railed platform with steps, and a mast with a hand bell and a proclamation.
    h = 0.6
    mb.box((0, 0.2, z + h / 2), (1.2, 1.1, h), "timber")
    for i in range(4):
        mb.box((-0.45 + i * 0.3, 0.2, z + h + 0.025), (0.28, 1.16, 0.05), "wood" if i % 2 else "wood_light")
    mb.box((0, 0.2, z + h * 0.5), (1.24, 1.14, 0.08), "wood")
    for k in range(2):
        mb.box((0, -0.48 - k * 0.2, z + (0.4 - k * 0.2) / 2), (0.6, 0.2, 0.4 - k * 0.2), "wood")
    top = z + h + 0.05
    for x, y in ((-0.54, -0.28), (0.54, -0.28), (-0.54, 0.68), (0.54, 0.68)):
        mb.box((x, y, top + 0.4), (0.08, 0.08, 0.8), "timber")
    for sx in (-1, 1):
        mb.box((sx * 0.54, 0.2, top + 0.78), (0.06, 1.04, 0.06), "wood")
        mb.box((sx * 0.54, 0.2, top + 0.4), (0.04, 1.0, 0.05), "wood")
    mb.box((0, 0.68, top + 0.78), (1.14, 0.06, 0.06), "wood")
    mb.box((0, 0.7, top + 0.4), (1.0, 0.03, 0.5), "cloth_blue")
    mb.box((0, 0.68, top + 0.4), (0.34, 0.04, 0.34), "gold", rotation_z=0.0)
    mb.box((0.54, 0.68, top + 1.3), (0.08, 0.08, 1.2), "timber")
    mb.cylinder((0.54, 0.68, top + 1.8), (0.1, 0.5, top + 1.8), 0.03, 0.03, "iron", segments=4)
    mb.cylinder((0.14, 0.52, top + 1.5), (0.14, 0.52, top + 1.76), 0.14, 0.05, "bell", segments=8)
    mb.sphere((0.14, 0.52, top + 1.47), 0.04, "iron", segments=5, rings=3)
    mb.sphere((0.54, 0.68, top + 1.94), 0.07, "gold", segments=6, rings=4)
    # The proclamation, on a post at the front.
    mb.box((-0.2, -0.26, top + 0.2), (0.08, 0.08, 0.4), "timber")
    xform(mb.box((0, 0, 0), (0.4, 0.02, 0.5), "plz_paper"),
          Matrix.Translation((-0.2, -0.3, top + 0.62)) @ Matrix.Rotation(common.radians(-12), 4, "X"))
    for k in range(3):
        xform(mb.box((0, -0.012, 0.12 - k * 0.12), (0.28, 0.01, 0.03), "plz_ink"),
              Matrix.Translation((-0.2, -0.3, top + 0.62)) @ Matrix.Rotation(common.radians(-12), 4, "X"))
    buildings.export(folder, "decor_crier_stand", mb)


MODELS = (fountain, lamp_post, bench_pair, signpost, notice_board, flagpole, plaza_planter,
          bell_frame, hitching_post, lamp_double, planter_wall, sundial, pillory,
          plaza_well, market_cross, brazier_pair, flower_pedestal, stage, milestone, tree_bench, banner_arch,
          public_oven, cart_stand, crier_stand)


def make_all(folder):
    os.makedirs(folder, exist_ok=True)
    for model in MODELS:
        model(folder)


if __name__ == "__main__":
    make_all(sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else ".")
