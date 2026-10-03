"""Decorations: natural elements and flowers (rocks, flower beds, fantasy flowers).

Every model is a square plot of 2, 3 or 4 meters standing on Z = 0, centered
on the origin, front toward -Y, and stays about 0.1 m inside its edge.

    blender --background --factory-startup --python art/blender/decor/nature.py -- <output folder>
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
    "nat_grass": common.rgb(0x6A9440),
    "nat_moss": common.rgb(0x5E8A3A),
    "nat_leaf": common.rgb(0x3F7030),
    "nat_leaf_light": common.rgb(0x6FA040),
    "nat_stem": common.rgb(0x4C8038),
    "nat_rock": common.rgb(0x8E8A84),
    "nat_rock_dark": common.rgb(0x6A6660),
    "nat_rock_light": common.rgb(0xB4AEA4),
    "nat_gravel": common.rgb(0xB8AE98),
    "nat_rose_red": common.rgb(0xC0202C),
    "nat_rose_pink": common.rgb(0xF08CA8),
    "nat_rose_white": common.rgb(0xF4EEE4),
    "nat_tulip_red": common.rgb(0xD83030),
    "nat_tulip_yellow": common.rgb(0xF0C828),
    "nat_tulip_purple": common.rgb(0x8A3CA8),
    "nat_tulip_orange": common.rgb(0xF08020),
    "nat_tulip_white": common.rgb(0xF6F0E8),
    "nat_sun_petal": common.rgb(0xF4C020),
    "nat_sun_core": common.rgb(0x5A3418),
    "nat_lavender": common.rgb(0x8C6CD0),
    "nat_lavender_leaf": common.rgb(0x7C9870),
    "nat_daisy": common.rgb(0xFAFAF2),
    "nat_daisy_core": common.rgb(0xF0B818),
    "nat_lily": common.rgb(0xF8F0F0),
    "nat_lily_orange": common.rgb(0xF07030),
    "nat_lily_pad": common.rgb(0x3E8048),
    "nat_reed_top": common.rgb(0x6A4424),
    "nat_blossom": common.rgb(0xE890C8),
    "nat_blossom_light": common.rgb(0xF8D0E8),
    "nat_glow_blue": common.rgb(0x40D8FF),
    "nat_glow_core": common.rgb(0xD8FCFF),
    "nat_glow_stem": common.rgb(0x2C7C78),
    "nat_shroom_stem": common.rgb(0xEADFC8),
    "nat_shroom_cap": common.rgb(0x9A3CC0),
    "nat_shroom_cap2": common.rgb(0xE85890),
    "nat_shroom_petal": common.rgb(0xFFA0D0),
    "nat_shroom_spot": common.rgb(0xFFF0A0),
    "nat_crystal_cyan": common.rgb(0x70E8F0),
    "nat_crystal_violet": common.rgb(0xB070F0),
    "nat_crystal_pink": common.rgb(0xF880C8),
    "nat_crystal_stem": common.rgb(0xC8E8F0),
    "nat_carn_green": common.rgb(0x5C9028),
    "nat_carn_dark": common.rgb(0x36601C),
    "nat_carn_mouth": common.rgb(0xB01848),
    "nat_carn_spot": common.rgb(0xE8D040),
    "nat_tooth": common.rgb(0xF4F0DC),
    "nat_fern": common.rgb(0x3C8838),
    "nat_bark": common.rgb(0x5C4028),
    "nat_shelf": common.rgb(0xD89048),
})

GOLDEN = 2.399963


# --- Helpers -------------------------------------------------------------------------------


def lumpy(verts, amount, seed):
    """Deterministic lumps on a sphere: push vertices by a fixed pattern."""
    ordered = sorted(verts, key=lambda v: (round(v.co.z, 4), round(v.co.x, 4), round(v.co.y, 4)))
    cx = sum(v.co.x for v in verts) / len(verts)
    cy = sum(v.co.y for v in verts) / len(verts)
    for i, v in enumerate(ordered):
        k = 1.0 + amount * math.sin(i * 2.3 + seed) + amount * 0.5 * math.cos(i * 5.1 + seed)
        v.co.x = cx + (v.co.x - cx) * k
        v.co.y = cy + (v.co.y - cy) * k


def stone(mb, x, y, z, r, scale, mat, seed, segments=7, rings=5, floor=0.0):
    """A lumpy stone resting on `floor`."""
    verts = mb.sphere((x, y, z), r, mat, segments=segments, rings=rings, scale=scale)
    lumpy(verts, 0.13, seed)
    for v in verts:
        if v.co.z < floor + 0.02:
            v.co.z = floor
    return verts


def puff(mb, x, y, z, r, mat, seed, sz=0.8, segments=7, rings=4):
    verts = mb.sphere((x, y, z), r, mat, segments=segments, rings=rings, scale=(1.0, 1.0, sz))
    lumpy(verts, 0.1, seed)
    return verts


def spike(mb, a, b, r, mat, segments=4):
    """A cone from a (wide) to b (the tip): a leaf, a petal, a thorn."""
    return mb.cylinder(a, b, r, 0.004, mat, segments=segments)


def xform(verts, m):
    for v in verts:
        v.co = m @ v.co


def bed(mb, size, fill="soil", edge="stone", corner="stone_dark"):
    """A raised bed with a stone edge that fills the plot; returns the top of the fill."""
    h = size / 2 - 0.1
    mb.box((0, 0, 0.07), (2 * h - 0.2, 2 * h - 0.2, 0.14), fill)
    for s in (-1, 1):
        mb.box((0, s * (h - 0.08), 0.1), (2 * h - 0.3, 0.16, 0.2), edge)
        mb.box((s * (h - 0.08), 0, 0.1), (0.16, 2 * h - 0.3, 0.2), edge)
        for t in (-1, 1):
            mb.box((s * (h - 0.09), t * (h - 0.09), 0.13), (0.18, 0.18, 0.26), corner)
    return 0.14


def ground(mb, size, mat, h=0.08):
    """A plain slab that fills the plot; returns its top."""
    w = size - 0.2
    mb.box((0, 0, h / 2), (w, w, h), mat)
    return h


def flower_head(mb, c, n, core_r, petal_len, petals, core_mat, petal_mat, petal_r=None, thick=0.05, cup=0.0):
    """A disk flower at c facing direction n: a round core and petals around it."""
    c, n = Vector(c), Vector(n).normalized()
    u = n.cross(Vector((0, 0, 1)))
    if u.length < 0.01:
        u = Vector((1, 0, 0))
    u.normalize()
    v = n.cross(u)
    mb.cylinder(c - n * thick * 0.5, c + n * thick * 0.5, core_r, core_r * 0.8, core_mat, segments=6)
    pr = petal_r if petal_r else core_r * 0.5
    for i in range(petals):
        a = 2 * math.pi * i / petals
        d = u * math.cos(a) + v * math.sin(a)
        spike(mb, c + d * core_r * 0.7, c + d * (core_r + petal_len) + n * cup, pr, petal_mat, segments=3)


def tris(mb):
    return sum(len(f.verts) - 2 for f in mb.bm.faces)


def finish(folder, name, mb):
    count = tris(mb)
    xs = [v.co.x for v in mb.bm.verts]
    ys = [v.co.y for v in mb.bm.verts]
    print("DECOR %s tris=%d x=[%.2f, %.2f] y=[%.2f, %.2f]" % (name, count, min(xs), max(xs), min(ys), max(ys)))
    buildings.export(folder, name, mb)


# --- Flower beds ---------------------------------------------------------------------------


def rose_bed(folder):
    """3 x 3: nine rose bushes in rows of red, pink and white."""
    common.reset_scene()
    mb = MeshBuilder()
    top = bed(mb, 3)
    colors = ("nat_rose_red", "nat_rose_pink", "nat_rose_white")
    for i in range(9):
        col, row = i % 3, i // 3
        x = -0.85 + col * 0.85
        y = -0.85 + row * 0.85
        r = 0.36 + 0.03 * ((i * 5) % 3)
        mb.cylinder((x, y, top), (x, y, top + 0.3), 0.05, 0.04, "timber", segments=4)
        puff(mb, x, y, top + 0.45, r, "nat_leaf" if i % 2 else "leaves", i * 1.7, sz=0.85)
        mat = colors[(col + row) % 3]
        for k in range(5):
            a = k * GOLDEN + i
            e = 0.25 + 0.3 * (k % 3)          # Elevation over the bush.
            d = r * 0.95
            px = x + math.cos(a) * math.cos(e) * d
            py = y + math.sin(a) * math.cos(e) * d
            pz = top + 0.45 + math.sin(e) * d * 0.85
            mb.sphere((px, py, pz), 0.085, mat, segments=5, rings=3)
    finish(folder, "decor_rose_bed", mb)


def tulip_bed(folder):
    """3 x 3: tulips in rows, one color per row."""
    common.reset_scene()
    mb = MeshBuilder()
    top = bed(mb, 3)
    colors = ("nat_tulip_red", "nat_tulip_yellow", "nat_tulip_purple", "nat_tulip_orange", "nat_tulip_white")
    for row in range(5):
        y = -0.96 + row * 0.48
        # A ridge of soil and a strip of leaves along the row.
        mb.box((0, y, top + 0.03), (2.3, 0.26, 0.06), "soil")
        for col in range(7):
            x = -1.02 + col * 0.34 + (0.06 if row % 2 else -0.06)
            h = 0.42 + 0.05 * ((col * 3 + row) % 3)
            z0 = top + 0.06
            mb.cylinder((x, y, z0), (x, y, z0 + h), 0.02, 0.02, "nat_stem", segments=3)
            side = 1 if (col + row) % 2 else -1
            spike(mb, (x, y, z0), (x + 0.1 * side, y + 0.07, z0 + 0.26), 0.05, "nat_leaf_light", segments=3)
            mb.cylinder((x, y, z0 + h - 0.02), (x, y, z0 + h + 0.15), 0.045, 0.085, colors[row], segments=5)
    finish(folder, "decor_tulip_bed", mb)


def sunflowers(folder):
    """2 x 2: a clump of tall sunflowers facing the front."""
    common.reset_scene()
    mb = MeshBuilder()
    top = bed(mb, 2)
    spots = ((-0.5, 0.45, 2.0), (0.05, 0.5, 2.3), (0.55, 0.4, 1.9), (-0.3, -0.05, 1.6), (0.35, -0.1, 1.7),
             (0.0, -0.5, 1.2), (-0.55, -0.5, 1.0), (0.55, -0.5, 1.05))
    for i, (x, y, h) in enumerate(spots):
        lean = 0.05 * ((i % 3) - 1)
        mb.cylinder((x, y, top), (x + lean, y - 0.05, top + h), 0.035, 0.028, "nat_stem", segments=4)
        for k in range(3):
            z = top + h * (0.25 + 0.22 * k)
            a = i + k * 2.2
            spike(mb, (x, y, z), (x + math.cos(a) * 0.26, y + math.sin(a) * 0.26, z + 0.08), 0.09, "nat_leaf",
                  segments=3)
        c = (x + lean, y - 0.1, top + h)
        flower_head(mb, c, (lean * 3, -1.0, 0.35), 0.16, 0.15, 10, "nat_sun_core", "nat_sun_petal", petal_r=0.07)
    finish(folder, "decor_sunflowers", mb)


def lavender(folder):
    """2 x 2: round lavender tufts in a bed."""
    common.reset_scene()
    mb = MeshBuilder()
    top = bed(mb, 2)
    for i, (x, y) in enumerate(((-0.4, -0.4), (0.4, -0.4), (-0.4, 0.4), (0.4, 0.4), (0.0, 0.0))):
        puff(mb, x, y, top + 0.14, 0.3, "nat_lavender_leaf", i * 2.1, sz=0.7, segments=6, rings=3)
        for k in range(11):
            a = k * GOLDEN + i
            d = 0.06 + 0.2 * ((k * 3) % 5) / 4.0
            lean = 1.0 + 0.5 * d / 0.26
            bx, by = x + math.cos(a) * d, y + math.sin(a) * d
            tx, ty = x + math.cos(a) * d * lean * 1.2, y + math.sin(a) * d * lean * 1.2
            h = 0.62 - d * 0.6
            mid = (bx + (tx - bx) * 0.6, by + (ty - by) * 0.6, top + 0.15 + h * 0.6)
            mb.cylinder((bx, by, top + 0.15), mid, 0.012, 0.012, "nat_lavender_leaf", segments=3)
            mb.cylinder(mid, (tx, ty, top + 0.15 + h), 0.045, 0.02, "nat_lavender", segments=4)
    finish(folder, "decor_lavender", mb)


def daisies(folder):
    """2 x 2: a low patch of daisies on grass."""
    common.reset_scene()
    mb = MeshBuilder()
    top = bed(mb, 2, fill="nat_grass")
    for i in range(14):
        a = i * GOLDEN
        d = 0.12 + 0.62 * math.sqrt(i / 13.0)
        x, y = math.cos(a) * d, math.sin(a) * d
        h = 0.22 + 0.1 * ((i * 7) % 4) / 3.0
        mb.cylinder((x, y, top), (x, y, top + h), 0.014, 0.014, "nat_stem", segments=3)
        spike(mb, (x, y, top), (x + math.cos(a + 1) * 0.14, y + math.sin(a + 1) * 0.14, top + 0.1), 0.05,
              "nat_leaf_light", segments=3)
        flower_head(mb, (x, y, top + h), (math.cos(a) * 0.3, math.sin(a) * 0.3 - 0.3, 1.0), 0.045, 0.085, 7,
                    "nat_daisy_core", "nat_daisy", petal_r=0.032, thick=0.04, cup=0.02)
    finish(folder, "decor_daisies", mb)


def lilies(folder):
    """2 x 2: tall lilies, white and orange, with open trumpets."""
    common.reset_scene()
    mb = MeshBuilder()
    top = bed(mb, 2)
    spots = ((-0.45, 0.4, 1.15), (0.4, 0.45, 1.25), (0.0, 0.0, 1.0), (-0.5, -0.4, 0.8), (0.5, -0.35, 0.85),
             (0.0, -0.55, 0.65))
    for i, (x, y, h) in enumerate(spots):
        mat = "nat_lily" if i % 2 == 0 else "nat_lily_orange"
        mb.cylinder((x, y, top), (x, y, top + h), 0.025, 0.02, "nat_stem", segments=4)
        for k in range(6):
            a = k * GOLDEN + i
            z = top + h * (0.1 + 0.11 * k)
            spike(mb, (x, y, z), (x + math.cos(a) * 0.28, y + math.sin(a) * 0.28, z + 0.12), 0.045, "nat_leaf",
                  segments=3)
        for k in range(2):
            a = i * 1.9 + k * 2.6 - 1.2
            n = Vector((math.cos(a) * 0.8, math.sin(a) * 0.8 - 0.3, 0.6)).normalized()
            c = Vector((x, y, top + h - 0.12 * k))
            mb.cylinder(c, c + n * 0.16, 0.025, 0.07, mat, segments=5)
            flower_head(mb, c + n * 0.16, n, 0.06, 0.15, 6, "nat_daisy_core", mat, petal_r=0.055, thick=0.03,
                        cup=0.05)
    finish(folder, "decor_lilies", mb)


def flowering_shrub(folder):
    """2 x 2: a big round shrub covered in pink blossom."""
    common.reset_scene()
    mb = MeshBuilder()
    top = bed(mb, 2)
    mb.cylinder((0, 0, top), (0, 0, top + 0.5), 0.1, 0.07, "timber", segments=5)
    puffs = ((0, 0, 0.85, 0.62), (0.38, 0.22, 0.6, 0.42), (-0.4, 0.2, 0.62, 0.42), (0.1, -0.4, 0.58, 0.42),
             (-0.2, 0.1, 1.25, 0.4))
    for i, (x, y, z, r) in enumerate(puffs):
        puff(mb, x, y, top + z, r, "nat_leaf" if i % 2 else "leaves", i * 1.3, sz=0.85, segments=8, rings=5)
        for k in range(10):
            a = k * GOLDEN + i * 0.7
            e = -0.1 + 1.3 * ((k * 3) % 10) / 10.0
            px = x + math.cos(a) * math.cos(e) * r * 0.97
            py = y + math.sin(a) * math.cos(e) * r * 0.97
            pz = top + z + math.sin(e) * r * 0.82
            mb.sphere((px, py, pz), 0.1, "nat_blossom" if k % 3 else "nat_blossom_light", segments=5, rings=3)
    finish(folder, "decor_flowering_shrub", mb)


def rose_arch(folder):
    """2 x 2: a wooden arch to walk under (along Y), overgrown with climbing roses."""
    common.reset_scene()
    mb = MeshBuilder()
    ground(mb, 2, "nat_gravel", 0.06)
    half, post_h, r = 0.62, 1.5, 0.62
    colors = ("nat_rose_red", "nat_rose_pink", "nat_rose_white")
    for sy in (-0.3, 0.3):
        for sx in (-1, 1):
            mb.box((sx * half, sy, post_h / 2), (0.09, 0.09, post_h), "timber")
        prev = None
        for k in range(7):
            a = math.pi * k / 6
            p = (math.cos(a) * r, sy, post_h + math.sin(a) * r)
            if prev:
                mb.cylinder(prev, p, 0.04, 0.04, "timber", segments=4)
            prev = p
    for k in range(7):                    # Rungs between the two hoops.
        a = math.pi * k / 6
        x, z = math.cos(a) * r, post_h + math.sin(a) * r
        mb.cylinder((x, -0.3, z), (x, 0.3, z), 0.025, 0.025, "wood", segments=4)
    for z in (0.5, 1.0):
        for sx in (-1, 1):
            mb.cylinder((sx * half, -0.3, z), (sx * half, 0.3, z), 0.025, 0.025, "wood", segments=4)
    # Planters at the feet, leaves climbing up and over, roses on them.
    n = 0
    for sx in (-1, 1):
        mb.box((sx * half, 0, 0.14), (0.4, 0.86, 0.22), "stone")
        mb.box((sx * half, 0, 0.26), (0.3, 0.76, 0.04), "soil")
        for k in range(4):
            z = 0.42 + k * 0.38
            y = 0.16 * (1 if k % 2 else -1)
            puff(mb, sx * (half + 0.02), y, z, 0.25 - 0.02 * k, "nat_leaf" if k % 2 else "leaves", n, segments=6,
                 rings=3)
            for j in range(2):
                a = j * 2.1 + k
                mb.sphere((sx * (half + 0.02) + math.cos(a) * 0.2 * sx, y + math.sin(a) * 0.22, z + 0.1 * (j - 1)),
                          0.07, colors[(n + j) % 3], segments=5, rings=3)
            n += 1
    for k in range(1, 6):
        a = math.pi * k / 6
        x, z = math.cos(a) * (r + 0.03), post_h + math.sin(a) * (r + 0.03)
        y = 0.14 * (1 if k % 2 else -1)
        puff(mb, x, y, z, 0.24, "leaves" if k % 2 else "nat_leaf", k * 1.9, segments=6, rings=4)
        for j in range(4):
            b = j * 1.6 + k
            mb.sphere((x + math.cos(b) * 0.17, y + (0.24 if j % 2 else -0.24), z + math.sin(b) * 0.17), 0.07,
                      colors[(k + j) % 3], segments=5, rings=3)
    finish(folder, "decor_rose_arch", mb)


# --- Fantasy flowers -----------------------------------------------------------------------


def glow_bells(folder):
    """2 x 2: arching stalks with hanging, glowing blue bells."""
    common.reset_scene()
    mb = MeshBuilder()
    top = bed(mb, 2, fill="nat_moss", edge="nat_rock_dark", corner="nat_rock")
    puff(mb, 0, 0, top + 0.05, 0.4, "nat_glow_stem", 0.4, sz=0.5, segments=7, rings=3)
    for i in range(5):
        a = i * 2 * math.pi / 5 + 0.3
        reach = 0.62 + 0.1 * (i % 2)
        h = 1.25 + 0.3 * ((i * 2) % 3)
        dx, dy = math.cos(a), math.sin(a)
        pts = []
        for k in range(6):
            t = k / 5.0
            d = reach * t ** 1.5
            z = top + h * math.sin(t * math.pi * 0.62) / math.sin(math.pi * 0.62) * (1.0 if t < 0.8 else 1.0)
            z = top + h * (1 - (1 - min(t / 0.7, 1.0)) ** 2) - (h * 0.25 * max(0.0, t - 0.7) / 0.3)
            pts.append(Vector((dx * d, dy * d, z)))
        for k in range(5):
            mb.cylinder(pts[k], pts[k + 1], 0.035 - 0.005 * k, 0.03 - 0.005 * k, "nat_glow_stem", segments=4)
        for k in (2, 3, 4, 5):
            p = pts[k]
            size = 0.1 + 0.035 * (k - 2)
            drop = 0.07
            mb.cylinder(p, p - Vector((0, 0, drop)), 0.008, 0.008, "nat_glow_stem", segments=3)
            mb.cylinder(p - Vector((0, 0, drop)), p - Vector((0, 0, drop + size * 1.5)), size * 0.35, size,
                        "nat_glow_blue", segments=6)
            mb.sphere(p - Vector((0, 0, drop + size * 1.5)), size * 0.5, "nat_glow_core", segments=5, rings=3)
        # A broad leaf at the foot of each stalk.
        b = a + 0.6
        spike(mb, (math.cos(b) * 0.15, math.sin(b) * 0.15, top + 0.05),
              (math.cos(b) * 0.7, math.sin(b) * 0.7, top + 0.4), 0.13, "nat_leaf", segments=4)
    finish(folder, "decor_glow_bells", mb)


def mushroom_flower(mb, x, y, z0, h, r, cap, seed):
    lean = 0.12 * math.sin(seed)
    tx, ty = x + lean, y + 0.1 * math.cos(seed * 1.7)
    mb.cylinder((x, y, z0), (tx, ty, z0 + h), r * 0.3, r * 0.2, "nat_shroom_stem", segments=7)
    # Petals under the cap, like a ruff.
    for k in range(8):
        a = 2 * math.pi * k / 8 + seed
        spike(mb, (tx + math.cos(a) * r * 0.25, ty + math.sin(a) * r * 0.25, z0 + h - 0.02),
              (tx + math.cos(a) * r * 1.25, ty + math.sin(a) * r * 1.25, z0 + h - r * 0.3), r * 0.26,
              "nat_shroom_petal", segments=3)
    verts = mb.sphere((tx, ty, z0 + h), r, cap, segments=8, rings=6, scale=(1.0, 1.0, 0.75))
    for v in verts:
        if v.co.z < z0 + h:
            v.co.z = z0 + h
    for k in range(5):
        a = k * GOLDEN + seed
        e = 0.35 + 0.9 * ((k * 2) % 5) / 5.0
        mb.sphere((tx + math.cos(a) * math.cos(e) * r * 0.95, ty + math.sin(a) * math.cos(e) * r * 0.95,
                   z0 + h + math.sin(e) * r * 0.72), r * 0.13, "nat_shroom_spot", segments=5, rings=3)


def mushroom_flowers(folder):
    """3 x 3: giant mushrooms with a ruff of petals under the cap."""
    common.reset_scene()
    mb = MeshBuilder()
    top = bed(mb, 3, fill="nat_moss", edge="nat_rock_dark", corner="nat_rock")
    mushroom_flower(mb, 0.15, 0.2, top, 2.3, 0.8, "nat_shroom_cap", 0.5)
    mushroom_flower(mb, -0.7, -0.35, top, 1.35, 0.55, "nat_shroom_cap2", 2.1)
    mushroom_flower(mb, 0.8, -0.5, top, 0.9, 0.42, "nat_shroom_cap", 3.9)
    mushroom_flower(mb, -0.2, -0.95, top, 0.45, 0.26, "nat_shroom_cap2", 5.2)
    mushroom_flower(mb, -0.95, 0.85, top, 0.55, 0.28, "nat_shroom_cap", 1.2)
    for i, (x, y) in enumerate(((0.95, 0.9), (0.2, -0.45), (-1.05, 0.2), (1.05, 0.15))):
        puff(mb, x, y, top + 0.05, 0.2, "nat_leaf_light", i * 1.1, sz=0.6, segments=6, rings=3)
    finish(folder, "decor_mushroom_flowers", mb)


def crystal(mb, a, b, r, mat, waist=0.35):
    """A double-pointed crystal from a to b, widest near a."""
    a, b = Vector(a), Vector(b)
    m = a + (b - a) * waist
    mb.cylinder(a, m, r * 0.25, r, mat, segments=4)
    mb.cylinder(m, b, r, 0.004, mat, segments=4)


def crystal_flowers(folder):
    """2 x 2: flowers of cut crystal growing out of dark rock."""
    common.reset_scene()
    mb = MeshBuilder()
    ground(mb, 2, "nat_rock_dark", 0.1)
    stone(mb, 0.0, 0.1, 0.12, 0.75, (1.0, 0.9, 0.35), "nat_rock", 0.7, floor=0.05)
    stone(mb, -0.55, -0.5, 0.12, 0.3, (1.0, 1.0, 0.6), "nat_rock_dark", 1.9, segments=6, rings=4, floor=0.05)
    stone(mb, 0.6, -0.45, 0.12, 0.26, (1.0, 1.0, 0.6), "nat_rock_dark", 3.1, segments=6, rings=4, floor=0.05)
    flowers = ((0.0, 0.2, 1.45, 0.42, "nat_crystal_cyan"), (-0.45, -0.15, 0.95, 0.32, "nat_crystal_violet"),
               (0.45, -0.2, 0.75, 0.28, "nat_crystal_pink"), (0.1, -0.6, 0.45, 0.2, "nat_crystal_cyan"),
               (-0.55, 0.55, 0.55, 0.22, "nat_crystal_pink"), (0.6, 0.5, 0.6, 0.22, "nat_crystal_violet"))
    for i, (x, y, h, r, mat) in enumerate(flowers):
        mb.cylinder((x, y, 0.15), (x, y, h), 0.03, 0.022, "nat_crystal_stem", segments=4)
        c = Vector((x, y, h))
        for k in range(5):
            a = 2 * math.pi * k / 5 + i
            d = Vector((math.cos(a), math.sin(a), 0.75))
            crystal(mb, c, c + d * r, r * 0.22, mat)
        crystal(mb, c - Vector((0, 0, 0.02)), c + Vector((0, 0, r * 1.25)), r * 0.2, "nat_crystal_stem", waist=0.3)
        # Two crystal leaves on the stem.
        for k in range(2):
            a = i * 1.3 + k * math.pi
            p = Vector((x, y, 0.2 + h * 0.3 * (k + 1) * 0.6))
            crystal(mb, p, p + Vector((math.cos(a) * 0.2, math.sin(a) * 0.2, 0.14)), 0.04, "nat_crystal_stem")
    # Raw shards at the foot.
    for k in range(5):
        a = k * GOLDEN + 0.4
        p = Vector((math.cos(a) * 0.72, math.sin(a) * 0.72, 0.08))
        crystal(mb, p, p + Vector((math.cos(a) * 0.06, math.sin(a) * 0.06, 0.26 + 0.05 * (k % 3))), 0.06,
                ("nat_crystal_cyan", "nat_crystal_violet", "nat_crystal_pink")[k % 3], waist=0.3)
    finish(folder, "decor_crystal_flowers", mb)


def jaw(mb, m, w, length, height, up):
    """Half of the carnivorous plant's head: local space has the hinge at the
    origin and the jaw reaching toward -Y; `up` is +1 (upper) or -1 (lower)."""
    verts = mb.sphere((0, -length, 0), 1.0, "nat_carn_green", segments=10, rings=6, scale=(w, length, height))
    for v in verts:
        if v.co.z * up < 0:
            v.co.z = 0.0
    xform(verts, m)
    ring = [(math.cos(2 * math.pi * k / 10) * w * 0.9, -length + math.sin(2 * math.pi * k / 10) * length * 0.9)
            for k in range(10)]
    xform(mb.prism(ring, -0.03 if up > 0 else 0.01, -0.01 if up > 0 else 0.03, "nat_carn_mouth"), m)
    for k in range(11):                   # Teeth around the front of the rim.
        a = math.pi * (1.0 + (k + 0.5) / 11.0) if up > 0 else math.pi * (1.0 + k / 10.0)
        p = Vector((math.cos(a) * w * 0.93, -length + math.sin(a) * length * 0.93, 0))
        tip = p + Vector((0, 0, -up * 0.22))
        spike(mb, m @ p, m @ tip, 0.055, "nat_tooth", segments=4)
    if up > 0:
        for k in range(7):                # Spots on the top of the head.
            a = k * GOLDEN
            d = 0.25 + 0.5 * ((k * 3) % 7) / 7.0
            lx, ly = math.cos(a) * d * w, -length + math.sin(a) * d * length
            lz = height * math.sqrt(max(0.0, 1 - d * d)) * 0.97
            verts = mb.sphere((lx, ly, lz), 0.09, "nat_carn_spot", segments=5, rings=3, scale=(1, 1, 0.5))
            xform(verts, m)


def carnivorous_plant(folder):
    """3 x 3: a huge flytrap-like plant with an open, toothed mouth."""
    common.reset_scene()
    mb = MeshBuilder()
    top = bed(mb, 3, fill="soil", edge="nat_rock_dark", corner="nat_rock")
    # A thick stalk rising at the back and bending to the front.
    pts = [Vector(p) for p in ((0, 0.75, top), (0, 0.95, 0.7), (0, 0.95, 1.3), (0, 0.75, 1.75), (0, 0.5, 1.95))]
    for k in range(4):
        mb.cylinder(pts[k], pts[k + 1], 0.24 - 0.03 * k, 0.21 - 0.03 * k, "nat_carn_dark", segments=7)
    hinge = Matrix.Translation(pts[-1] + Vector((0, 0.05, 0)))
    jaw(mb, hinge @ Matrix.Rotation(math.radians(-30), 4, "X"), 0.7, 0.78, 0.45, 1)
    jaw(mb, hinge @ Matrix.Rotation(math.radians(22), 4, "X"), 0.66, 0.72, 0.36, -1)
    # Tongue.
    mb.cylinder(pts[-1] + Vector((0, -0.2, -0.1)), pts[-1] + Vector((0, -1.0, -0.42)), 0.12, 0.06, "nat_rose_pink",
                segments=5)
    # Broad leaves around the foot.
    for k in range(7):
        a = 2 * math.pi * k / 7 + 0.25
        d = 1.15 if k % 2 else 0.95
        verts = spike(mb, (math.cos(a) * 0.15, 0.6 + math.sin(a) * 0.15, top + 0.1),
                      (math.cos(a) * d, 0.3 + math.sin(a) * d * 0.85, top + 0.3 + 0.2 * (k % 2)), 0.3,
                      "nat_carn_green" if k % 2 else "nat_leaf", segments=4)
    # Two smaller closed buds on thin stalks.
    for sx, y, h in ((-0.85, -0.5, 0.95), (0.9, -0.2, 1.2)):
        mb.cylinder((sx * 0.5, 0.5, top), (sx, y, h), 0.07, 0.05, "nat_carn_dark", segments=5)
        mb.sphere((sx, y - 0.08, h + 0.08), 0.2, "nat_carn_green", segments=7, rings=4, scale=(0.8, 1.2, 0.8))
        for j in range(4):
            spike(mb, (sx - 0.1 + j * 0.07, y - 0.3, h + 0.08), (sx - 0.1 + j * 0.07, y - 0.32, h - 0.03 + 0.2 * (j % 2)),
                  0.03, "nat_tooth", segments=3)
    # Weeds and a gnawed stone at the front of the bed.
    stone(mb, -0.75, -0.95, top + 0.08, 0.2, (1.2, 0.9, 0.7), "nat_rock", 1.1, segments=6, rings=4, floor=top)
    stone(mb, 0.9, -1.0, top + 0.06, 0.15, (1.0, 1.0, 0.7), "nat_rock_dark", 2.3, segments=6, rings=4, floor=top)
    for i, (x, y) in enumerate(((-0.3, -1.05), (0.45, -0.9), (1.05, 0.75), (-1.05, 0.8), (-1.05, -0.1))):
        grass_tuft(mb, x, y, top, i * 1.4, "nat_leaf_light")
    finish(folder, "decor_carnivorous_plant", mb)


# --- Rocks, water and woodland -------------------------------------------------------------


def grass_tuft(mb, x, y, z, seed, mat="nat_grass", h=0.3):
    for k in range(4):
        a = seed + k * 1.6
        spike(mb, (x, y, z), (x + math.cos(a) * 0.12, y + math.sin(a) * 0.12, z + h * (0.7 + 0.1 * k)), 0.045, mat,
              segments=3)


def standing_stone(folder):
    """2 x 2: a tall standing stone with a carved band, small stones at its foot."""
    common.reset_scene()
    mb = MeshBuilder()
    top = ground(mb, 2, "nat_grass")
    verts = mb.sphere((0, 0.1, 1.0), 1.0, "nat_rock", segments=8, rings=7, scale=(0.5, 0.36, 1.65))
    lumpy(verts, 0.1, 2.2)
    for v in verts:
        v.co.x += 0.1 * (v.co.z / 2.6) ** 2      # A slight lean.
        if v.co.z < top:
            v.co.z = top
    # A carved spiral, as a few dark studs, and a ring of lighter stone.
    for k in range(6):
        a = k * 1.05
        d = 0.03 + 0.03 * k
        mb.box((0.03 + math.cos(a) * d, -0.24, 1.5 + math.sin(a) * d), (0.05, 0.08, 0.05), "nat_rock_dark")
    puff(mb, 0.09, 0.1, 2.57, 0.26, "nat_moss", 1.0, sz=0.4, segments=6, rings=3)
    puff(mb, -0.3, 0.0, 0.5, 0.22, "nat_moss", 2.0, sz=0.9, segments=6, rings=3)
    ring = ((-0.6, -0.45, 0.24), (0.6, -0.5, 0.2), (0.56, 0.42, 0.24), (-0.6, 0.5, 0.22), (0.05, -0.68, 0.17),
            (0.0, 0.7, 0.18))
    for i, (x, y, r) in enumerate(ring):
        stone(mb, x, y, top + r * 0.4, r, (1.0, 0.9, 0.7), "nat_rock_dark" if i % 2 else "nat_rock_light", i * 1.4,
              segments=6, rings=4, floor=top)
    for i, (x, y) in enumerate(((-0.3, -0.62), (0.4, -0.3), (0.38, 0.62), (-0.7, 0.05), (0.75, -0.05))):
        grass_tuft(mb, x, y, top, i * 1.3, "nat_leaf_light")
    finish(folder, "decor_standing_stone", mb)


def mossy_boulders(folder):
    """3 x 3: a group of big mossy boulders."""
    common.reset_scene()
    mb = MeshBuilder()
    top = ground(mb, 3, "nat_grass")
    parts = ((-0.1, 0.3, 0.6, 0.95, (1.1, 0.95, 0.8), "nat_rock"), (0.75, -0.35, 0.4, 0.6, (1.0, 1.0, 0.8), "nat_rock_dark"),
             (-0.72, -0.65, 0.3, 0.48, (1.1, 0.9, 0.75), "nat_rock_light"), (0.8, 0.8, 0.25, 0.42, (1.0, 1.0, 0.7), "nat_rock"),
             (0.0, -0.95, 0.15, 0.28, (1.2, 0.9, 0.7), "nat_rock_dark"), (-0.95, 0.2, 0.15, 0.22, (1.0, 1.0, 0.7), "nat_rock_dark"))
    for i, (x, y, z, r, sc, mat) in enumerate(parts):
        stone(mb, x, y, top + z, r, sc, mat, i * 1.3 + 0.4, segments=8, rings=6, floor=top)
    for i, (x, y, z, r) in enumerate(((-0.15, 0.3, 1.3, 0.55), (0.75, -0.35, 0.82, 0.36), (-0.72, -0.65, 0.6, 0.26),
                                      (0.3, 0.75, 0.75, 0.3))):
        puff(mb, x, y, top + z, r, "nat_moss", i * 2.0, sz=0.35, segments=7, rings=3)
    for i, (x, y) in enumerate(((0.1, -0.6), (-1.1, -0.2), (1.15, 0.2), (-0.9, 1.0), (1.1, -1.0), (-0.3, -1.15))):
        grass_tuft(mb, x, y, top, i * 1.7, "nat_leaf_light")
    for i, (x, y) in enumerate(((0.45, -0.95), (-1.15, 0.65), (1.2, -0.45), (-0.45, 1.2))):
        mb.cylinder((x, y, top), (x, y, top + 0.2), 0.012, 0.012, "nat_stem", segments=3)
        flower_head(mb, (x, y, top + 0.2), (0, -0.3, 1), 0.04, 0.07, 6, "nat_daisy_core",
                    "nat_daisy" if i % 2 else "nat_lavender", petal_r=0.03, thick=0.03, cup=0.02)
    finish(folder, "decor_mossy_boulders", mb)


def rock_garden(folder):
    """3 x 3: raked gravel with three stone islands, a dwarf pine and a stone lantern."""
    common.reset_scene()
    mb = MeshBuilder()
    top = bed(mb, 3, fill="nat_gravel", edge="timber", corner="wood")
    for k in range(6):                    # Raked lines.
        y = -1.0 + k * 0.4
        mb.box((0, y, top + 0.01), (2.4, 0.06, 0.02), "nat_rock_light")
    islands = ((-0.6, 0.45, 0.6, "nat_moss"), (0.7, -0.5, 0.42, "nat_moss"), (0.65, 0.75, 0.3, "nat_moss"))
    for i, (x, y, r, mat) in enumerate(islands):
        mb.cylinder((x, y, top), (x, y, top + 0.05), r, r * 0.9, mat, segments=9)
    stone(mb, -0.7, 0.55, top + 0.45, 0.42, (0.9, 0.8, 1.6), "nat_rock", 0.6, segments=8, rings=6, floor=top)
    stone(mb, -0.3, 0.3, top + 0.2, 0.3, (1.1, 0.9, 0.8), "nat_rock_dark", 1.8, floor=top)
    stone(mb, 0.75, -0.5, top + 0.22, 0.32, (1.2, 0.9, 0.8), "nat_rock_light", 2.6, floor=top)
    stone(mb, 0.45, -0.7, top + 0.12, 0.17, (1.0, 1.0, 0.8), "nat_rock_dark", 3.3, segments=6, rings=4, floor=top)
    # Dwarf pine: a bent trunk with flat cushions of needles.
    mb.cylinder((0.65, 0.75, top), (0.5, 0.7, top + 0.45), 0.06, 0.045, "timber", segments=5)
    mb.cylinder((0.5, 0.7, top + 0.45), (0.75, 0.85, top + 0.8), 0.045, 0.03, "timber", segments=5)
    for i, (x, y, z, r) in enumerate(((0.35, 0.65, 0.5, 0.26), (0.8, 0.9, 0.85, 0.3), (0.55, 0.6, 0.98, 0.2))):
        puff(mb, x, y, top + z, r, "nat_leaf", i * 1.5, sz=0.4, segments=7, rings=3)
    # Stone lantern.
    x, y = -0.75, -0.7
    mb.cylinder((x, y, top), (x, y, top + 0.1), 0.2, 0.17, "stone_dark", segments=6)
    mb.cylinder((x, y, top + 0.1), (x, y, top + 0.5), 0.07, 0.07, "stone", segments=6)
    mb.box((x, y, top + 0.54), (0.3, 0.3, 0.08), "stone_dark")
    mb.box((x, y, top + 0.68), (0.2, 0.2, 0.2), "nat_daisy_core")
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.box((x + sx * 0.1, y + sy * 0.1, top + 0.68), (0.05, 0.05, 0.2), "stone")
    mb.cylinder((x, y, top + 0.78), (x, y, top + 0.98), 0.3, 0.03, "stone_dark", segments=4)
    finish(folder, "decor_rock_garden", mb)


def pond(folder):
    """4 x 4: a small pond ringed with stones, with water lilies and reeds."""
    common.reset_scene()
    mb = MeshBuilder()
    top = ground(mb, 4, "nat_grass")
    mb.cylinder((0, 0, top), (0, 0, top + 0.05), 1.55, 1.5, "soil", segments=14)
    verts = mb.cylinder((0, 0, top + 0.05), (0, 0, top + 0.09), 1.4, 1.4, "water", segments=14)
    for i in range(14):                   # Stones on the bank.
        a = 2 * math.pi * i / 14
        r = 0.2 + 0.07 * ((i * 5) % 3)
        d = 1.5 + 0.04 * (i % 2)
        if i in (3, 4):                   # The reeds stand here.
            continue
        stone(mb, math.cos(a) * d, math.sin(a) * d, top + r * 0.45, r, (1.1, 1.0, 0.75),
              ("nat_rock", "nat_rock_dark", "nat_rock_light")[i % 3], i * 1.1, segments=6, rings=4, floor=top)
    wz = top + 0.09
    pads = ((-0.5, -0.45, 0.27, True), (0.35, -0.75, 0.2, False), (0.65, 0.1, 0.3, True), (-0.2, 0.45, 0.22, False),
            (-0.85, 0.2, 0.18, False), (0.2, -0.2, 0.16, True), (0.85, -0.55, 0.15, False))
    for i, (x, y, r, flower) in enumerate(pads):
        mb.cylinder((x, y, wz), (x, y, wz + 0.02), r, r, "nat_lily_pad", segments=7)
        if flower:
            mat = "nat_lily" if i % 2 == 0 else "nat_rose_pink"
            for ring, (n, reach, lift) in enumerate(((7, 0.16, 0.06), (5, 0.1, 0.13))):
                for k in range(n):
                    a = 2 * math.pi * k / n + ring * 0.4
                    spike(mb, (x, y, wz + 0.03), (x + math.cos(a) * reach, y + math.sin(a) * reach, wz + 0.03 + lift),
                          0.05, mat, segments=3)
            mb.sphere((x, y, wz + 0.07), 0.035, "nat_daisy_core", segments=5, rings=3)
    # Reeds and cattails at the back.
    for k in range(12):
        a = 0.95 + 1.1 * k / 11.0
        d = 1.25 + 0.3 * ((k * 3) % 4) / 3.0
        x, y = math.cos(a) * d, math.sin(a) * d
        h = 0.9 + 0.5 * ((k * 5) % 4) / 3.0
        lean = 0.1 * math.sin(k * 1.9)
        if k % 2:
            mb.cylinder((x, y, top), (x + lean, y, top + h), 0.018, 0.014, "nat_stem", segments=3)
            mb.cylinder((x + lean, y, top + h - 0.05), (x + lean * 1.25, y, top + h + 0.2), 0.045, 0.045,
                        "nat_reed_top", segments=5)
        else:
            spike(mb, (x, y, top), (x + lean * 2, y + 0.05, top + h), 0.04, "nat_leaf_light", segments=3)
            spike(mb, (x, y, top), (x - lean * 3 - 0.1, y - 0.05, top + h * 0.7), 0.04, "nat_stem", segments=3)
    for i, (x, y) in enumerate(((-1.6, -1.6), (1.6, -1.55), (1.65, 1.6), (-1.6, 1.55), (1.75, 0.3), (-1.75, -0.4))):
        grass_tuft(mb, x, y, top, i * 1.9, "nat_leaf_light")
    # A flat stepping stone at the front.
    stone(mb, 0.0, -1.72, top + 0.03, 0.26, (1.3, 0.6, 0.3), "nat_rock_light", 5.0, segments=6, rings=4, floor=top)
    del verts
    finish(folder, "decor_pond", mb)


def fern(mb, x, y, z, seed, fronds=7, reach=0.5, mat="nat_fern"):
    for k in range(fronds):
        a = 2 * math.pi * k / fronds + seed
        dx, dy = math.cos(a), math.sin(a)
        mid = (x + dx * reach * 0.55, y + dy * reach * 0.55, z + reach * 0.6)
        mb.cylinder((x, y, z), mid, 0.02, 0.07, mat, segments=3)
        spike(mb, mid, (x + dx * reach, y + dy * reach, z + reach * 0.3), 0.07, mat, segments=3)


def fern_log(folder):
    """3 x 3: a woodland corner with a fallen log, ferns, mushrooms and a stump."""
    common.reset_scene()
    mb = MeshBuilder()
    top = ground(mb, 3, "nat_moss")
    # The fallen log, lying across, hollow-looking ends.
    a, b = Vector((-1.15, -0.35, top + 0.3)), Vector((1.0, 0.25, top + 0.3))
    mb.cylinder(a, b, 0.32, 0.28, "nat_bark", segments=8)
    d = (b - a).normalized()
    mb.cylinder(a - d * 0.02, a + d * 0.02, 0.26, 0.26, "log_end", segments=8)
    mb.cylinder(b - d * 0.02, b + d * 0.02, 0.22, 0.22, "log_end", segments=8)
    mb.cylinder(a - d * 0.03, a, 0.14, 0.14, "charcoal", segments=6)
    mb.cylinder(Vector((0.3, 0.05, top + 0.5)), Vector((0.5, -0.3, top + 0.95)), 0.07, 0.05, "nat_bark", segments=5)
    puff(mb, -0.3, -0.1, top + 0.58, 0.32, "nat_grass", 0.9, sz=0.3, segments=7, rings=3)
    # Shelf fungus on the log.
    for k in range(4):
        p = a + d * (0.9 + 0.28 * k)
        mb.cylinder((p.x + 0.08, p.y - 0.27, p.z + 0.02 + 0.05 * (k % 2)), (p.x + 0.08, p.y - 0.27, p.z + 0.06 + 0.05 * (k % 2)),
                    0.14, 0.1, "nat_shelf", segments=6)
    # A stump at the back.
    mb.cylinder((-0.8, 0.9, top), (-0.8, 0.9, top + 0.45), 0.34, 0.27, "nat_bark", segments=8)
    mb.cylinder((-0.8, 0.9, top + 0.45), (-0.8, 0.9, top + 0.47), 0.24, 0.24, "log_end", segments=8)
    for i, (x, y, r) in enumerate(((0.65, 0.7, 0.6), (-0.1, 0.75, 0.5), (0.85, -0.85, 0.45), (-0.9, -0.9, 0.42),
                                   (1.0, 0.2, 0.34), (-1.02, 0.25, 0.33))):
        fern(mb, x, y, top, i * 0.8, fronds=7, reach=r, mat="nat_fern" if i % 2 else "nat_leaf_light")
    # Little red toadstools.
    for i, (x, y, h) in enumerate(((0.1, -0.85, 0.2), (0.3, -0.95, 0.13), (-0.05, -1.05, 0.11), (-0.35, 1.2, 0.15))):
        mb.cylinder((x, y, top), (x, y, top + h), 0.03, 0.025, "nat_shroom_stem", segments=4)
        mb.cylinder((x, y, top + h), (x, y, top + h + 0.09), 0.1, 0.02, "nat_rose_red", segments=6)
    stone(mb, 0.55, -0.6, top + 0.1, 0.22, (1.2, 0.9, 0.7), "nat_rock", 2.4, segments=6, rings=4, floor=top)
    finish(folder, "decor_fern_log", mb)


# --- Second batch --------------------------------------------------------------------------

buildings.COLORS.update({
    "nat_cactus": common.rgb(0x4E8C50),
    "nat_cactus_light": common.rgb(0x7CB060),
    "nat_poppy": common.rgb(0xE83820),
    "nat_hyd_blue": common.rgb(0x6C8CE8),
    "nat_hyd_pink": common.rgb(0xE888C0),
    "nat_hyd_purple": common.rgb(0xA070D8),
    "nat_lotus": common.rgb(0xF8A0C8),
    "nat_lotus_light": common.rgb(0xFCE0EC),
    "nat_toadstool": common.rgb(0xD82828),
    "nat_bee": common.rgb(0xF0C020),
    "nat_geode": common.rgb(0x8040C0),
    "nat_geode_light": common.rgb(0xD0A0F8),
    "nat_bird": common.rgb(0x4878C0),
})


def petal(mb, base, yaw, pitch, length, width, mat, curl=0.2):
    """A flat, pointed petal from `base`, turned `yaw` around Z and raised by `pitch`."""
    verts = spike(mb, (0, 0, 0), (length, 0, 0), width, mat, segments=4)
    for v in verts:
        v.co.z = v.co.z * 0.25 + curl * length * (v.co.x / length) ** 2
    xform(verts, Matrix.Translation(Vector(base)) @ Matrix.Rotation(yaw, 4, "Z") @ Matrix.Rotation(-pitch, 4, "Y"))
    return verts


def small_flower(mb, x, y, z, h, mat, core="nat_daisy_core", size=0.07, seed=0.0, petals=5):
    mb.cylinder((x, y, z), (x, y, z + h), 0.014, 0.014, "nat_stem", segments=3)
    spike(mb, (x, y, z), (x + math.cos(seed) * 0.13, y + math.sin(seed) * 0.13, z + h * 0.5), 0.04, "nat_leaf_light",
          segments=3)
    flower_head(mb, (x, y, z + h), (math.cos(seed) * 0.3, -0.4, 1.0), size * 0.6, size, petals, core, mat,
                petal_r=size * 0.45, thick=0.03, cup=0.02)


def toadstool(mb, x, y, z, h, r, cap, spots=3, seed=0.0, spot="nat_daisy"):
    mb.cylinder((x, y, z), (x, y, z + h), r * 0.32, r * 0.25, "nat_shroom_stem", segments=5)
    verts = mb.sphere((x, y, z + h), r, cap, segments=7, rings=4, scale=(1, 1, 0.8))
    for v in verts:
        if v.co.z < z + h:
            v.co.z = z + h
    for k in range(spots):
        a = seed + k * 2.1
        mb.sphere((x + math.cos(a) * r * 0.6, y + math.sin(a) * r * 0.6, z + h + r * 0.6), r * 0.16, spot,
                  segments=5, rings=3)


def fairy_ring(folder):
    """3 x 3: a ring of red toadstools around a dark circle with floating lights."""
    common.reset_scene()
    mb = MeshBuilder()
    top = ground(mb, 3, "nat_grass")
    mb.cylinder((0, 0, top), (0, 0, top + 0.02), 0.8, 0.8, "nat_moss", segments=12)
    for i in range(9):
        a = 2 * math.pi * i / 9
        h = 0.3 + 0.18 * ((i * 3) % 4) / 3.0
        r = 0.2 + 0.07 * ((i * 5) % 3)
        toadstool(mb, math.cos(a) * 1.05, math.sin(a) * 1.05, top, h, r, "nat_toadstool", spots=2, seed=i)
    for i in range(6):                    # Fairy lights over the middle.
        a = i * GOLDEN
        d = 0.15 + 0.1 * i
        p = Vector((math.cos(a) * d, math.sin(a) * d, top + 0.5 + 0.22 * i))
        crystal(mb, p - Vector((0, 0, 0.07)), p + Vector((0, 0, 0.09)), 0.05, "nat_glow_core", waist=0.45)
    for i in range(4):
        a = i * 1.571 + 0.5
        small_flower(mb, math.cos(a) * 0.45, math.sin(a) * 0.45, top, 0.2, "nat_glow_blue", "nat_glow_core", seed=a)
    for i, (x, y) in enumerate(((-1.2, -1.2), (1.2, -1.2), (1.2, 1.2), (-1.2, 1.2))):
        grass_tuft(mb, x, y, top, i * 1.3, "nat_leaf_light")
    finish(folder, "decor_fairy_ring", mb)


def giant_lotus(folder):
    """3 x 3: a stone basin of water with one enormous lotus and its pads."""
    common.reset_scene()
    mb = MeshBuilder()
    top = bed(mb, 3, fill="water")
    for i, (x, y, r) in enumerate(((-0.8, -0.75, 0.36), (0.85, -0.7, 0.3), (0.9, 0.75, 0.34), (-0.85, 0.8, 0.28),
                                   (0.0, -1.0, 0.2))):
        mb.cylinder((x, y, top), (x, y, top + 0.025), r, r, "nat_lily_pad", segments=7)
    mb.cylinder((0, 0, top), (0, 0, top + 0.3), 0.12, 0.2, "nat_stem", segments=6)
    c = (0, 0, top + 0.3)
    for ring, (n, pitch, length, width, mat) in enumerate(((9, 0.25, 0.95, 0.3, "nat_lotus"),
                                                          (8, 0.75, 0.85, 0.28, "nat_lotus_light"),
                                                          (6, 1.2, 0.7, 0.24, "nat_lotus"))):
        for k in range(n):
            petal(mb, c, 2 * math.pi * k / n + ring * 0.35, pitch, length, width, mat, curl=0.25)
    mb.cylinder((0, 0, top + 0.3), (0, 0, top + 0.55), 0.14, 0.22, "nat_sun_petal", segments=7)
    for k in range(6):
        a = k * 1.05
        mb.sphere((math.cos(a) * 0.12, math.sin(a) * 0.12, top + 0.57), 0.045, "nat_glow_core", segments=5, rings=3)
    # A bud on a stalk beside it.
    mb.cylinder((-0.75, 0.1, top), (-0.9, 0.15, top + 0.7), 0.035, 0.03, "nat_stem", segments=4)
    crystal(mb, (-0.9, 0.15, top + 0.68), (-0.93, 0.16, top + 1.05), 0.13, "nat_lotus", waist=0.4)
    finish(folder, "decor_giant_lotus", mb)


def glow_stump(folder):
    """2 x 2: an old stump with a glowing hollow and glowing mushrooms."""
    common.reset_scene()
    mb = MeshBuilder()
    top = ground(mb, 2, "nat_moss")
    verts = mb.cylinder((0, 0.1, top), (0, 0.1, top + 0.75), 0.48, 0.36, "nat_bark", segments=9)
    lumpy(verts, 0.08, 1.3)
    mb.cylinder((0, 0.1, top + 0.75), (0, 0.1, top + 0.78), 0.3, 0.3, "log_end", segments=9)
    mb.cylinder((0.1, 0.2, top + 0.7), (0.2, 0.3, top + 1.15), 0.12, 0.02, "nat_bark", segments=5)  # A splinter.
    for k in range(6):                    # Roots.
        a = 2 * math.pi * k / 6 + 0.3
        spike(mb, (math.cos(a) * 0.3, 0.1 + math.sin(a) * 0.3, top + 0.2),
              (math.cos(a) * 0.8, 0.1 + math.sin(a) * 0.75, top), 0.14, "nat_bark", segments=4)
    # The hollow, lit from inside.
    mb.box((0, -0.3, top + 0.3), (0.26, 0.14, 0.36), "charcoal")
    mb.box((0, -0.34, top + 0.27), (0.18, 0.1, 0.26), "nat_glow_core")
    spots = ((-0.5, -0.45, 0.0, 0.3, 0.17), (-0.3, -0.62, 0.0, 0.2, 0.12), (0.55, -0.4, 0.0, 0.36, 0.2),
             (0.68, -0.1, 0.0, 0.18, 0.11), (-0.12, 0.05, 0.78, 0.2, 0.15), (0.05, -0.08, 0.78, 0.12, 0.09),
             (-0.62, 0.45, 0.0, 0.24, 0.14), (0.3, 0.7, 0.0, 0.22, 0.13))
    for i, (x, y, z, h, r) in enumerate(spots):
        toadstool(mb, x, y, top + z, h, r, "nat_glow_blue", spots=2, seed=i * 1.7, spot="nat_glow_core")
    for k in range(3):                    # Glowing shelves on the bark.
        a = 2.4 + k * 0.8
        z = top + 0.3 + 0.14 * k
        r = 0.44 - 0.1 * (z - top) / 0.75
        mb.cylinder((math.cos(a) * r, 0.1 + math.sin(a) * r, z), (math.cos(a) * r, 0.1 + math.sin(a) * r, z + 0.05),
                    0.15, 0.1, "nat_glow_blue", segments=6)
    puff(mb, -0.15, 0.25, top + 0.78, 0.2, "nat_grass", 0.5, sz=0.35, segments=6, rings=3)
    finish(folder, "decor_glow_stump", mb)


def poppies(folder):
    """2 x 2: red poppies with dark hearts."""
    common.reset_scene()
    mb = MeshBuilder()
    top = bed(mb, 2)
    for i in range(14):
        a = i * GOLDEN
        d = 0.1 + 0.6 * math.sqrt(i / 13.0)
        x, y = math.cos(a) * d, math.sin(a) * d
        h = 0.35 + 0.25 * ((i * 7) % 5) / 4.0
        p = Vector((x + math.cos(a) * 0.08, y + math.sin(a) * 0.08 - 0.03, top + h))
        mb.cylinder((x, y, top), p, 0.014, 0.014, "nat_stem", segments=3)
        spike(mb, (x, y, top), (x + math.cos(a + 2) * 0.16, y + math.sin(a + 2) * 0.16, top + 0.2), 0.05, "nat_leaf",
              segments=3)
        for k in range(4):
            petal(mb, p, k * 1.571 + i, 0.55, 0.15, 0.085, "nat_poppy", curl=0.3)
        mb.sphere(p + Vector((0, 0, 0.03)), 0.035, "charcoal", segments=5, rings=3)
    finish(folder, "decor_poppies", mb)


def hydrangeas(folder):
    """3 x 3: hydrangea bushes with big balls of blue, pink and purple flowers."""
    common.reset_scene()
    mb = MeshBuilder()
    top = bed(mb, 3)
    colors = ("nat_hyd_blue", "nat_hyd_pink", "nat_hyd_purple", "nat_rose_white")
    for i, (x, y) in enumerate(((-0.62, -0.62), (0.62, -0.62), (-0.62, 0.62), (0.62, 0.62))):
        r = 0.55
        puff(mb, x, y, top + 0.4, r, "nat_leaf" if i % 2 else "leaves", i * 1.9, sz=0.8, segments=8, rings=5)
        for k in range(6):
            a = k * GOLDEN + i
            e = 0.15 + 1.2 * ((k * 2) % 6) / 6.0
            px = x + math.cos(a) * math.cos(e) * r * 0.9
            py = y + math.sin(a) * math.cos(e) * r * 0.9
            pz = top + 0.4 + math.sin(e) * r * 0.75
            puff(mb, px, py, pz, 0.2, colors[(i + (k % 2)) % 4], k * 1.3, sz=0.85, segments=6, rings=4)
            spike(mb, (px, py, pz - 0.05), (px + math.cos(a) * 0.3, py + math.sin(a) * 0.3, pz - 0.12), 0.1,
                  "nat_leaf_light", segments=3)
    finish(folder, "decor_hydrangeas", mb)


def cacti(folder):
    """2 x 2: a gravel bed with a tall branching cactus, a barrel cactus and a prickly pear."""
    common.reset_scene()
    mb = MeshBuilder()
    top = bed(mb, 2, fill="nat_gravel", edge="clay", corner="brick")
    # Tall cactus with two arms.
    x, y = -0.1, 0.3
    mb.cylinder((x, y, top), (x, y, top + 1.5), 0.2, 0.18, "nat_cactus", segments=7)
    mb.sphere((x, y, top + 1.5), 0.18, "nat_cactus", segments=7, rings=4)
    for sx, z, up in ((1, 0.6, 0.55), (-1, 0.85, 0.4)):
        ex = x + sx * 0.4
        mb.cylinder((x, y, top + z), (ex, y, top + z + 0.08), 0.11, 0.11, "nat_cactus", segments=6)
        mb.cylinder((ex, y, top + z), (ex, y, top + z + up), 0.11, 0.1, "nat_cactus", segments=6)
        mb.sphere((ex, y, top + z + up), 0.1, "nat_cactus", segments=6, rings=4)
        mb.sphere((ex, y, top + z + up + 0.1), 0.05, "nat_rose_white", segments=5, rings=3)
    mb.sphere((x, y - 0.05, top + 1.68), 0.07, "nat_rose_pink", segments=5, rings=3)
    for k in range(10):                   # Thorns.
        a = k * GOLDEN
        z = top + 0.2 + 0.12 * k
        spike(mb, (x + math.cos(a) * 0.17, y + math.sin(a) * 0.17, z),
              (x + math.cos(a) * 0.3, y + math.sin(a) * 0.3, z + 0.03), 0.015, "nat_tooth", segments=3)
    # Barrel cactus with a flower on top.
    verts = mb.sphere((0.45, -0.4, top + 0.24), 0.3, "nat_cactus_light", segments=10, rings=5, scale=(1, 1, 0.95))
    for v in verts:                       # Ribs: pull every other meridian in.
        ang = math.atan2(v.co.y + 0.4, v.co.x - 0.45)
        if round(ang / (math.pi / 5)) % 2:
            v.co.x = 0.45 + (v.co.x - 0.45) * 0.82
            v.co.y = -0.4 + (v.co.y + 0.4) * 0.82
    flower_head(mb, (0.45, -0.4, top + 0.53), (0, 0, 1), 0.05, 0.09, 7, "nat_daisy_core", "nat_tulip_yellow",
                petal_r=0.04, thick=0.03, cup=0.04)
    # Prickly pear: flat pads.
    for i, (px, py, pz, r) in enumerate(((-0.5, -0.5, 0.2, 0.22), (-0.62, -0.5, 0.52, 0.17), (-0.36, -0.5, 0.5, 0.15),
                                        (-0.66, -0.5, 0.78, 0.12))):
        mb.sphere((px, py, top + pz), r, "nat_cactus" if i % 2 else "nat_cactus_light", segments=7, rings=4,
                  scale=(1, 0.35, 1.15))
    mb.sphere((-0.36, -0.5, top + 0.7), 0.05, "nat_poppy", segments=5, rings=3)
    mb.sphere((-0.66, -0.5, top + 0.93), 0.05, "nat_poppy", segments=5, rings=3)
    stone(mb, 0.6, 0.5, top + 0.08, 0.2, (1.1, 0.9, 0.7), "nat_rock", 1.4, segments=6, rings=4, floor=top)
    stone(mb, 0.1, -0.7, top + 0.05, 0.12, (1.1, 0.9, 0.7), "nat_rock_dark", 2.4, segments=6, rings=4, floor=top)
    finish(folder, "decor_cacti", mb)


def bird_bath(folder):
    """2 x 2: a stone bird bath with a bird on its rim, among flowers."""
    common.reset_scene()
    mb = MeshBuilder()
    top = bed(mb, 2, fill="nat_grass")
    mb.cylinder((0, 0, top), (0, 0, top + 0.1), 0.3, 0.26, "stone_dark", segments=8)
    mb.cylinder((0, 0, top + 0.1), (0, 0, top + 0.7), 0.13, 0.1, "stone", segments=8)
    mb.cylinder((0, 0, top + 0.7), (0, 0, top + 0.88), 0.16, 0.5, "stone", segments=10)
    mb.cylinder((0, 0, top + 0.88), (0, 0, top + 0.93), 0.5, 0.5, "stone_dark", segments=10)
    mb.cylinder((0, 0, top + 0.93), (0, 0, top + 0.94), 0.42, 0.42, "water", segments=10)
    # The bird.
    b = Vector((0.3, -0.33, top + 1.03))
    mb.sphere(b, 0.09, "nat_bird", segments=6, rings=4, scale=(1.3, 0.9, 0.9))
    mb.sphere(b + Vector((-0.1, 0, 0.08)), 0.06, "nat_bird", segments=6, rings=4)
    spike(mb, b + Vector((-0.15, 0, 0.08)), b + Vector((-0.22, 0, 0.07)), 0.02, "nat_tulip_orange", segments=3)
    spike(mb, b + Vector((0.08, 0, 0.02)), b + Vector((0.25, 0, 0.08)), 0.05, "cloth_blue", segments=3)
    mb.sphere(b + Vector((-0.02, 0, -0.03)), 0.06, "nat_rose_white", segments=5, rings=3)
    colors = ("nat_rose_pink", "nat_tulip_yellow", "nat_lavender", "nat_daisy", "nat_poppy")
    for i in range(14):
        a = 2 * math.pi * i / 14 + 0.2
        d = 0.56 + 0.12 * (i % 2)
        small_flower(mb, math.cos(a) * d, math.sin(a) * d, top, 0.22 + 0.1 * (i % 3), colors[i % 5], size=0.075,
                     seed=a)
    finish(folder, "decor_bird_bath", mb)


def beehive(folder):
    """2 x 2: a straw beehive on a wooden stand, bees around it, among flowers."""
    common.reset_scene()
    mb = MeshBuilder()
    top = bed(mb, 2, fill="nat_grass")
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.box((sx * 0.3, 0.15 + sy * 0.3, top + 0.2), (0.08, 0.08, 0.4), "timber")
    mb.box((0, 0.15, top + 0.43), (0.84, 0.84, 0.07), "wood")
    z = top + 0.465
    for k, (r, h) in enumerate(((0.36, 0.14), (0.37, 0.14), (0.34, 0.13), (0.28, 0.12), (0.19, 0.1), (0.09, 0.07))):
        mb.cylinder((0, 0.15, z), (0, 0.15, z + h), r, r * 0.93, "thatch" if k % 2 else "hay", segments=9)
        z += h
    mb.box((0, -0.2, top + 0.53), (0.14, 0.06, 0.09), "charcoal")
    mb.box((0, -0.3, top + 0.475), (0.3, 0.12, 0.02), "wood_light")
    for k in range(7):                    # Bees.
        a = k * GOLDEN
        p = Vector((math.cos(a) * (0.35 + 0.05 * k), -0.2 + math.sin(a) * 0.35, top + 0.6 + 0.12 * ((k * 3) % 5)))
        mb.box(p, (0.07, 0.04, 0.04), "nat_bee", rotation_z=a)
        mb.box(p + Vector((0, 0, 0.03)), (0.03, 0.09, 0.01), "nat_daisy", rotation_z=a)
    colors = ("nat_lavender", "nat_tulip_yellow", "nat_daisy", "nat_rose_pink")
    for i in range(12):
        if i < 8:
            x, y = -0.7 + 1.4 * (i / 7.0), -0.62 - 0.08 * (i % 2)
        else:
            x, y = (-0.68 if i % 2 else 0.68), -0.2 + 0.3 * ((i - 8) // 2)
        small_flower(mb, x, y, top, 0.2 + 0.1 * (i % 3), colors[i % 4], size=0.075, seed=i * 1.3)
    finish(folder, "decor_beehive", mb)


def stone_arch(folder):
    """3 x 3: a natural arch of weathered rock, mossy on top."""
    common.reset_scene()
    mb = MeshBuilder()
    top = ground(mb, 3, "nat_grass")
    mats = ("nat_rock", "nat_rock_dark", "nat_rock_light")
    for sx in (-1, 1):
        stone(mb, sx * 0.85, 0, top + 0.35, 0.46, (1.0, 1.1, 1.0), mats[0 if sx < 0 else 1], 1.0 + sx, segments=8,
              rings=6, floor=top)
        stone(mb, sx * 0.86, 0.05 * sx, top + 0.95, 0.4, (1.0, 1.05, 1.0), mats[2], 2.0 + sx, segments=8, rings=6,
              floor=-9)
    for k in range(7):
        a = math.pi * k / 6
        r = 0.36 + 0.05 * math.sin(a)
        stone(mb, math.cos(a) * 0.84, 0.06 * math.sin(k * 2.0), top + 1.3 + math.sin(a) * 0.75, r, (1.0, 1.1, 0.9),
              mats[k % 3], k * 1.7, segments=8, rings=5, floor=-9)
    for i, (x, z, r) in enumerate(((0.0, 2.38, 0.42), (-0.6, 2.05, 0.3), (0.75, 1.75, 0.26))):
        puff(mb, x, 0.0, top + z, r, "nat_moss", i * 1.2, sz=0.3, segments=7, rings=3)
    # Hanging vines under the arch.
    for i, (x, z, drop) in enumerate(((-0.25, 1.75, 0.5), (0.1, 1.8, 0.35), (0.38, 1.7, 0.6))):
        mb.cylinder((x, 0, top + z), (x + 0.03, -0.02, top + z - drop), 0.02, 0.012, "nat_leaf", segments=3)
        spike(mb, (x + 0.03, -0.02, top + z - drop), (x + 0.1, -0.05, top + z - drop - 0.14), 0.05, "nat_leaf_light",
              segments=3)
    for i, (x, y, r) in enumerate(((-0.9, -0.85, 0.26), (0.95, 0.9, 0.24), (0.7, -1.0, 0.18), (-1.0, 0.95, 0.2))):
        stone(mb, x, y, top + r * 0.4, r, (1.1, 0.9, 0.7), mats[i % 3], i * 2.1, segments=6, rings=4, floor=top)
    for i, (x, y) in enumerate(((0, -0.7), (0.3, 0.8), (-1.15, -0.3), (1.2, -0.4), (-0.4, -1.15), (-0.4, 1.1))):
        grass_tuft(mb, x, y, top, i * 1.1, "nat_leaf_light")
    finish(folder, "decor_natural_arch", mb)


def geode(folder):
    """2 x 2: a boulder split open, full of violet crystals."""
    common.reset_scene()
    mb = MeshBuilder()
    top = ground(mb, 2, "nat_gravel")
    cy, cz, r = 0.15, top + 0.55, 0.72
    verts = mb.sphere((0, cy, cz), r, "nat_rock_dark", segments=10, rings=7, scale=(1.05, 0.95, 1.0))
    lumpy(verts, 0.07, 0.9)
    for v in verts:
        if v.co.y < cy - 0.1:
            v.co.y = cy - 0.1             # The cut face, toward the front.
        if v.co.z < top:
            v.co.z = top
    f = cy - 0.1
    mb.cylinder((0, f + 0.01, cz), (0, f - 0.015, cz), 0.6, 0.6, "nat_rock_light", segments=10)
    mb.cylinder((0, f, cz), (0, f - 0.03, cz), 0.5, 0.5, "nat_geode", segments=10)
    for k in range(16):
        a = k * GOLDEN
        d = 0.44 * math.sqrt((k + 0.5) / 16.0)
        p = Vector((math.cos(a) * d, f - 0.02, cz + math.sin(a) * d))
        n = Vector((-math.cos(a) * 0.3, -1.0, -math.sin(a) * 0.3)).normalized()
        crystal(mb, p, p + n * (0.16 + 0.1 * (k % 3)), 0.06 + 0.012 * (k % 3),
                "nat_geode_light" if k % 3 == 0 else ("nat_geode" if k % 3 == 1 else "nat_crystal_violet"), waist=0.3)
    # The broken-off piece and loose crystals on the ground.
    stone(mb, -0.55, -0.55, top + 0.1, 0.26, (1.1, 0.9, 0.7), "nat_rock_dark", 2.2, segments=7, rings=4, floor=top)
    for k in range(4):
        p = Vector((-0.55 + 0.1 * math.cos(k * 1.6), -0.55 + 0.1 * math.sin(k * 1.6), top + 0.2))
        crystal(mb, p, p + Vector((0.08 * math.cos(k * 1.6), 0.08 * math.sin(k * 1.6), 0.2)), 0.05, "nat_geode_light",
                waist=0.3)
    for k in range(5):
        a = k * 1.3 - 0.4
        p = Vector((0.2 + math.cos(a) * 0.5, -0.6 + math.sin(a) * 0.12, top))
        crystal(mb, p, p + Vector((0.05 * math.cos(k), 0.03, 0.16 + 0.05 * (k % 2))), 0.05,
                "nat_geode" if k % 2 else "nat_crystal_violet", waist=0.3)
    finish(folder, "decor_geode", mb)


def wildflowers(folder):
    """3 x 3: a meadow patch of mixed wildflowers."""
    common.reset_scene()
    mb = MeshBuilder()
    top = bed(mb, 3, fill="nat_grass", edge="timber", corner="wood")
    colors = ("nat_poppy", "nat_daisy", "nat_lavender", "nat_tulip_yellow", "nat_hyd_blue", "nat_rose_pink")
    for i in range(15):
        a = i * GOLDEN
        d = 0.15 + 1.0 * math.sqrt(i / 14.0)
        x, y = math.cos(a) * d, math.sin(a) * d
        small_flower(mb, x, y, top, 0.22 + 0.3 * ((i * 7) % 5) / 4.0, colors[i % 6], size=0.11, seed=a,
                     petals=5 + i % 2)
    for i in range(8):
        a = i * GOLDEN + 1.0
        d = 0.3 + 0.85 * math.sqrt(i / 7.0)
        grass_tuft(mb, math.cos(a) * d, math.sin(a) * d, top, i * 1.9, "nat_leaf_light", h=0.35)
    finish(folder, "decor_wildflowers", mb)


# --- Third batch ---------------------------------------------------------------------------

buildings.COLORS.update({
    "nat_vine": common.rgb(0x3A4A22),
    "nat_iris_gold": common.rgb(0xF0B020),
    "nat_iris_red": common.rgb(0xD83838),
    "nat_iris_violet": common.rgb(0xA050E0),
    "nat_orchid": common.rgb(0xC050C0),
    "nat_orchid_light": common.rgb(0xF4E0F4),
})


def eye_vine(folder):
    """3 x 3: thorny vines rising from the ground, each ending in a watching eye."""
    common.reset_scene()
    mb = MeshBuilder()
    top = bed(mb, 3, fill="soil", edge="nat_rock_dark", corner="nat_rock")
    vines = ((0.0, 0.5, 2.3, 0.45, "nat_iris_gold"), (-0.75, 0.0, 1.5, 0.35, "nat_iris_red"),
             (0.75, -0.1, 1.15, 0.3, "nat_iris_violet"), (-0.15, -0.75, 0.7, 0.22, "nat_iris_gold"))
    for j, (bx, by, h, sway, iris) in enumerate(vines):
        pts = []
        for k in range(8):
            t = k / 7.0
            pts.append(Vector((bx + math.sin(t * 5.0 + j * 2.0) * sway * (0.3 + 0.7 * t) * 0.6,
                               by + math.cos(t * 4.0 + j) * sway * 0.4 - 0.25 * t * t, top + h * t)))
        for k in range(7):
            r = 0.11 - 0.008 * k
            mb.cylinder(pts[k], pts[k + 1], r, r - 0.008, "nat_vine", segments=4)
            a = k * GOLDEN + j
            m = (pts[k] + pts[k + 1]) * 0.5
            spike(mb, m, m + Vector((math.cos(a) * 0.2, math.sin(a) * 0.2, 0.05)), 0.035, "nat_tooth", segments=3)
        # The eye, looking to the front, in a cup of dark leaf.
        c = pts[-1] + Vector((0, -0.08, 0.1))
        r = 0.16 + 0.03 * (h / 2.3) * 2
        cup = mb.sphere(c, r * 1.12, "nat_vine", segments=7, rings=4)
        for v in cup:
            if v.co.y < c.y - r * 0.15:
                v.co.y = c.y - r * 0.15
        mb.sphere(c, r, "nat_tooth", segments=7, rings=4)
        mb.sphere(c + Vector((0, -r * 0.62, 0)), r * 0.55, iris, segments=6, rings=3)
        mb.sphere(c + Vector((0, -r * 1.0, 0)), r * 0.26, "charcoal", segments=5, rings=3)
        for k in range(5):                # Lashes of thorn around the eye.
            a = math.pi * (0.1 + 0.2 * k)
            spike(mb, c + Vector((math.cos(a) * r, -r * 0.1, math.sin(a) * r)),
                  c + Vector((math.cos(a) * r * 1.6, -r * 0.5, math.sin(a) * r * 1.6)), 0.03, "nat_vine", segments=3)
    for k in range(6):                    # Creepers on the soil.
        a = k * 1.05 + 0.4
        spike(mb, (math.cos(a) * 0.3, math.sin(a) * 0.3, top + 0.06), (math.cos(a) * 1.15, math.sin(a) * 1.15, top + 0.03),
              0.07, "nat_vine", segments=4)
        spike(mb, (math.cos(a) * 0.8, math.sin(a) * 0.8, top + 0.05), (math.cos(a) * 0.85, math.sin(a) * 0.85, top + 0.25),
              0.03, "nat_tooth", segments=3)
    finish(folder, "decor_eye_vine", mb)


def floating_petals(folder):
    """2 x 2: a glowing bud whose petals float in rings above it."""
    common.reset_scene()
    mb = MeshBuilder()
    top = bed(mb, 2, fill="nat_moss", edge="nat_rock_dark", corner="nat_rock")
    mb.cylinder((0, 0, top), (0, 0, top + 0.55), 0.07, 0.05, "nat_glow_stem", segments=5)
    for k in range(6):
        petal(mb, (0, 0, top + 0.03), k * 1.047, 0.3, 0.6, 0.2, "nat_leaf" if k % 2 else "nat_glow_stem", curl=0.15)
    for k in range(5):
        petal(mb, (0, 0, top + 0.55), k * 1.257, 0.9, 0.3, 0.12, "nat_glow_stem", curl=0.3)
    mb.sphere((0, 0, top + 0.68), 0.14, "nat_glow_core", segments=7, rings=5)
    rings = ((0.36, 0.95, 7, 0.34, "nat_lotus", 0.9), (0.55, 1.35, 8, 0.3, "nat_glow_blue", 0.5),
             (0.42, 1.8, 6, 0.26, "nat_crystal_violet", 0.15), (0.2, 2.15, 4, 0.2, "nat_lotus_light", -0.3))
    for j, (rad, z, n, length, mat, pitch) in enumerate(rings):
        for k in range(n):
            a = 2 * math.pi * k / n + j * 0.5
            zz = top + z + 0.06 * math.sin(k * 2.4)
            petal(mb, (math.cos(a) * rad * 0.45, math.sin(a) * rad * 0.45, zz), a, pitch, length, length * 0.38, mat,
                  curl=0.25)
    for k in range(5):                    # Sparks drifting up the middle.
        p = Vector((0.06 * math.cos(k * 2.0), 0.06 * math.sin(k * 2.0), top + 1.0 + 0.3 * k))
        crystal(mb, p - Vector((0, 0, 0.05)), p + Vector((0, 0, 0.07)), 0.035, "nat_glow_core", waist=0.45)
    finish(folder, "decor_floating_petals", mb)


def orchids(folder):
    """2 x 2: arching sprays of purple and white orchids over broad leaves."""
    common.reset_scene()
    mb = MeshBuilder()
    top = bed(mb, 2, fill="nat_bark")
    for j, (bx, by, h, direction) in enumerate(((-0.4, 0.35, 1.2, -0.3), (0.4, 0.4, 1.35, 0.3), (0.0, -0.1, 0.95, 0.1),
                                                (-0.45, -0.4, 0.7, -0.2), (0.45, -0.38, 0.75, 0.25))):
        for k in range(4):                # Broad strap leaves.
            petal(mb, (bx, by, top), j + k * 1.571, 0.45, 0.36, 0.13, "nat_leaf" if k % 2 else "nat_leaf_light",
                  curl=-0.15)
        pts = []
        for k in range(6):
            t = k / 5.0
            pts.append(Vector((bx + direction * t * t * 0.9, by - 0.22 * t * t, top + h * (1 - (1 - t) ** 2))))
        for k in range(5):
            mb.cylinder(pts[k], pts[k + 1], 0.018, 0.015, "nat_stem", segments=3)
        mat = "nat_orchid" if j % 2 == 0 else "nat_orchid_light"
        for k in (3, 4, 5):
            c = pts[k] + Vector((0, -0.04, -0.02))
            flower_head(mb, c, (direction * 0.5, -1.0, 0.25), 0.04, 0.11, 5, "nat_tulip_yellow", mat, petal_r=0.055,
                        thick=0.03, cup=0.02)
            spike(mb, c + Vector((0, -0.02, 0)), c + Vector((0, -0.1, -0.09)), 0.035,
                  "nat_orchid" if j % 2 else "nat_rose_red", segments=3)
    finish(folder, "decor_orchids", mb)


def bonsai_rock(folder):
    """2 x 2: a craggy rock in a stone tray with a twisted little tree growing from it."""
    common.reset_scene()
    mb = MeshBuilder()
    ground(mb, 2, "nat_gravel", 0.06)
    mb.box((0, 0, 0.14), (1.6, 1.3, 0.16), "stone_dark")
    mb.box((0, 0, 0.225), (1.46, 1.16, 0.03), "nat_moss")
    top = 0.23
    stone(mb, -0.2, 0.05, top + 0.45, 0.42, (1.0, 0.85, 1.7), "nat_rock", 0.8, segments=8, rings=6, floor=top)
    stone(mb, 0.2, 0.1, top + 0.25, 0.34, (1.1, 0.9, 1.2), "nat_rock_dark", 2.1, segments=7, rings=5, floor=top)
    stone(mb, -0.5, -0.2, top + 0.12, 0.2, (1.0, 1.0, 0.9), "nat_rock_light", 3.0, segments=6, rings=4, floor=top)
    pts = [Vector(p) for p in ((-0.15, 0.0, 1.25), (0.05, -0.1, 1.5), (0.3, -0.05, 1.6), (0.4, 0.05, 1.85),
                               (0.2, 0.1, 2.05))]
    for k in range(4):
        mb.cylinder(pts[k], pts[k + 1], 0.07 - 0.012 * k, 0.06 - 0.012 * k, "timber", segments=5)
    mb.cylinder(pts[1], Vector((-0.25, -0.2, 1.7)), 0.035, 0.02, "timber", segments=4)
    mb.cylinder(pts[2], Vector((0.62, -0.15, 1.55)), 0.03, 0.02, "timber", segments=4)
    pads = ((0.2, 0.1, 2.1, 0.34), (-0.3, -0.22, 1.76, 0.26), (0.66, -0.16, 1.58, 0.22), (0.5, 0.12, 1.92, 0.2))
    for i, (x, y, z, r) in enumerate(pads):
        puff(mb, x, y, z, r, "nat_leaf" if i % 2 else "leaves", i * 1.4, sz=0.45, segments=7, rings=4)
        for k in range(3):
            a = k * 2.1 + i
            mb.sphere((x + math.cos(a) * r * 0.6, y + math.sin(a) * r * 0.6, z + r * 0.3), 0.045, "nat_blossom",
                      segments=5, rings=3)
    # Roots gripping the rock.
    for k in range(3):
        a = k * 2.1 + 0.5
        mb.cylinder(pts[0], pts[0] + Vector((math.cos(a) * 0.22, math.sin(a) * 0.2, -0.4)), 0.035, 0.015, "timber",
                    segments=4)
    puff(mb, 0.35, -0.3, top + 0.03, 0.18, "nat_grass", 0.3, sz=0.5, segments=6, rings=3)
    finish(folder, "decor_bonsai_rock", mb)


# --- Fourth batch --------------------------------------------------------------------------

buildings.COLORS.update({
    "nat_bamboo": common.rgb(0x8CB048),
    "nat_bamboo_dark": common.rgb(0x5C8030),
    "nat_foam": common.rgb(0xE8F4F8),
    "nat_hedge": common.rgb(0x35602C),
})


def crystal_tree(folder):
    """3 x 3: a pale tree whose leaves are clusters of crystal."""
    common.reset_scene()
    mb = MeshBuilder()
    top = bed(mb, 3, fill="nat_moss", edge="nat_rock_dark", corner="nat_rock")
    trunk = [Vector(p) for p in ((0, 0.1, top), (0.08, 0.1, 0.7), (-0.05, 0.05, 1.3), (0.05, 0.1, 1.8))]
    for k in range(3):
        mb.cylinder(trunk[k], trunk[k + 1], 0.2 - 0.045 * k, 0.16 - 0.045 * k, "nat_shroom_stem", segments=6)
    for k in range(5):                    # Roots.
        a = k * 1.257 + 0.3
        spike(mb, (math.cos(a) * 0.12, 0.1 + math.sin(a) * 0.12, top + 0.15),
              (math.cos(a) * 0.6, 0.1 + math.sin(a) * 0.6, top), 0.09, "nat_shroom_stem", segments=4)
    mats = ("nat_crystal_cyan", "nat_crystal_violet", "nat_crystal_pink")
    branches = ((1, 0.75, 0.2, 1.65), (2, -0.8, 0.15, 2.0), (2, 0.5, -0.5, 2.25), (3, -0.3, 0.6, 2.5),
                (3, 0.2, 0.0, 2.75), (1, -0.6, -0.45, 1.45))
    for i, (start, x, y, z) in enumerate(branches):
        end = Vector((x, y + 0.1, z))
        mb.cylinder(trunk[start], end, 0.06, 0.03, "nat_shroom_stem", segments=4)
        for k in range(5):
            a = k * 1.257 + i
            d = Vector((math.cos(a) * 0.8, math.sin(a) * 0.8, 0.5 if k % 2 else -0.15))
            crystal(mb, end, end + d * (0.44 + 0.08 * (k % 3)), 0.12, mats[(i + (k == 0)) % 3], waist=0.4)
        crystal(mb, end, end + Vector((0, 0, 0.6)), 0.13, mats[i % 3], waist=0.4)
    for k in range(7):                    # Fallen shards.
        a = k * GOLDEN
        d = 0.75 + 0.35 * (k % 2)
        p = Vector((math.cos(a) * d, math.sin(a) * d, top - 0.02))
        crystal(mb, p, p + Vector((math.cos(a) * 0.05, math.sin(a) * 0.05, 0.22 + 0.06 * (k % 3))), 0.06, mats[k % 3],
                waist=0.3)
    finish(folder, "decor_crystal_tree", mb)


def bamboo(folder):
    """2 x 2: a clump of bamboo in a gravel bed."""
    common.reset_scene()
    mb = MeshBuilder()
    top = bed(mb, 2, fill="nat_gravel")
    for i in range(9):
        a = i * GOLDEN
        d = 0.08 + 0.45 * math.sqrt(i / 8.0)
        x, y = math.cos(a) * d, math.sin(a) * d + 0.1
        h = 2.7 - 0.2 * i + 0.3 * (i % 2)
        lean = Vector((math.cos(a) * 0.05, math.sin(a) * 0.05, 0))
        r = 0.05 - 0.002 * i
        mb.cylinder((x, y, top), Vector((x, y, top + h)) + lean * h, r, r * 0.6, "nat_bamboo", segments=5)
        for k in range(1, 4):
            t = k / 4.0
            p = Vector((x, y, top + h * t)) + lean * h * t
            mb.cylinder(p - Vector((0, 0, 0.02)), p + Vector((0, 0, 0.02)), r * 1.25, r * 1.25, "nat_bamboo_dark", segments=5)
        for k in range(5):                # Leaves near the top.
            t = 0.6 + 0.09 * k
            p = Vector((x, y, top + h * t)) + lean * h * t
            b = a + k * 2.2
            petal(mb, p, b, -0.25, 0.32, 0.06, "nat_leaf_light" if k % 2 else "nat_leaf", curl=-0.2)
    stone(mb, 0.55, -0.55, top + 0.08, 0.2, (1.1, 0.9, 0.7), "nat_rock", 1.4, segments=6, rings=4, floor=top)
    stone(mb, -0.6, -0.5, top + 0.06, 0.14, (1.1, 0.9, 0.7), "nat_rock_dark", 2.6, segments=6, rings=4, floor=top)
    finish(folder, "decor_bamboo", mb)


def topiary(folder):
    """2 x 2: a clipped three-ball topiary in a clay pot, with two pots of flowers."""
    common.reset_scene()
    mb = MeshBuilder()
    top = ground(mb, 2, "stone", 0.08)
    for i in range(3):                    # Paving joints.
        mb.box((-0.6 + 0.6 * i, 0, top), (0.03, 1.8, 0.012), "stone_dark")
        mb.box((0, -0.6 + 0.6 * i, top), (1.8, 0.03, 0.012), "stone_dark")
    mb.cylinder((0, 0.15, top), (0, 0.15, top + 0.45), 0.3, 0.42, "clay", segments=8)
    mb.cylinder((0, 0.15, top + 0.45), (0, 0.15, top + 0.52), 0.46, 0.46, "brick", segments=8)
    mb.cylinder((0, 0.15, top + 0.52), (0, 0.15, top + 0.53), 0.4, 0.4, "soil", segments=8)
    mb.cylinder((0, 0.15, top + 0.5), (0, 0.15, top + 2.2), 0.05, 0.035, "timber", segments=5)
    for z, r in ((0.95, 0.42), (1.6, 0.32), (2.1, 0.22)):
        mb.sphere((0, 0.15, top + z), r, "nat_hedge", segments=8, rings=6)
    for i, (x, y, mat) in enumerate(((-0.6, -0.55, "nat_rose_red"), (0.6, -0.55, "nat_tulip_yellow"))):
        mb.cylinder((x, y, top), (x, y, top + 0.25), 0.14, 0.2, "clay", segments=7)
        puff(mb, x, y, top + 0.32, 0.2, "nat_leaf_light", i * 1.3, sz=0.6, segments=6, rings=3)
        for k in range(5):
            a = k * 1.257 + i
            mb.sphere((x + math.cos(a) * 0.12, y + math.sin(a) * 0.12, top + 0.42), 0.055, mat, segments=5, rings=3)
        mb.sphere((x, y, top + 0.46), 0.055, mat, segments=5, rings=3)
    finish(folder, "decor_topiary_pot", mb)


def parterre(folder):
    """4 x 4: a formal garden: four hedged flower beds around an urn, gravel paths between."""
    common.reset_scene()
    mb = MeshBuilder()
    top = bed(mb, 4, fill="nat_gravel")
    pairs = (("nat_rose_red", "nat_rose_white"), ("nat_tulip_yellow", "nat_lavender"),
             ("nat_hyd_blue", "nat_rose_pink"), ("nat_tulip_orange", "nat_tulip_purple"))
    n = 0
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx, cy = sx * 1.0, sy * 1.0
            mb.box((cx, cy, top + 0.03), (1.2, 1.2, 0.06), "soil")
            mb.box((cx, cy, top + 0.12), (1.0, 1.0, 0.16), "nat_leaf_light")
            for t in (-1, 1):
                mb.box((cx, cy + t * 0.62, top + 0.12), (1.36, 0.14, 0.24), "nat_hedge")
                mb.box((cx + t * 0.62, cy, top + 0.12), (0.14, 1.1, 0.24), "nat_hedge")
            for i in range(9):
                x = cx - 0.36 + (i % 3) * 0.36
                y = cy - 0.36 + (i // 3) * 0.36
                mat = pairs[n][0] if i % 2 == 0 else pairs[n][1]
                mb.sphere((x, y, top + 0.3), 0.1, mat, segments=5, rings=3)
            # A clipped cone at the outer corner of each bed.
            mb.cylinder((sx * 1.62, sy * 1.62, top), (sx * 1.62, sy * 1.62, top + 0.8), 0.17, 0.02, "nat_hedge", segments=6)
            n += 1
    # The urn in the middle, overflowing with flowers.
    mb.cylinder((0, 0, top), (0, 0, top + 0.12), 0.28, 0.24, "stone_dark", segments=8)
    mb.cylinder((0, 0, top + 0.12), (0, 0, top + 0.4), 0.1, 0.1, "stone", segments=8)
    mb.cylinder((0, 0, top + 0.4), (0, 0, top + 0.75), 0.14, 0.34, "stone", segments=8)
    puff(mb, 0, 0, top + 0.8, 0.32, "nat_leaf", 0.7, sz=0.6, segments=7, rings=4)
    for k in range(8):
        a = k * GOLDEN
        d = 0.1 + 0.2 * (k % 3) / 2.0
        mb.sphere((math.cos(a) * d, math.sin(a) * d, top + 0.95 - d * 0.5), 0.07,
                  ("nat_rose_pink", "nat_rose_white", "nat_rose_red")[k % 3], segments=5, rings=3)
    finish(folder, "decor_parterre", mb)


def waterfall(folder):
    """3 x 3: water falling from a stack of rocks into a small stone-ringed pool."""
    common.reset_scene()
    mb = MeshBuilder()
    top = ground(mb, 3, "nat_grass")
    mats = ("nat_rock", "nat_rock_dark", "nat_rock_light")
    stone(mb, 0.0, 0.7, top + 0.55, 0.62, (1.5, 0.9, 1.1), mats[0], 0.6, segments=9, rings=6, floor=top)
    stone(mb, -0.55, 0.65, top + 0.9, 0.48, (1.0, 0.95, 1.5), mats[1], 1.7, segments=8, rings=6, floor=top)
    stone(mb, 0.55, 0.7, top + 0.85, 0.46, (1.0, 0.95, 1.5), mats[2], 2.9, segments=8, rings=6, floor=top)
    stone(mb, 0.0, 0.85, top + 1.45, 0.42, (1.6, 0.8, 0.8), mats[1], 4.0, segments=8, rings=5, floor=-9)
    # The pool and the falling water.
    mb.cylinder((0, -0.2, top), (0, -0.2, top + 0.05), 0.9, 0.86, "soil", segments=12)
    mb.cylinder((0, -0.2, top + 0.05), (0, -0.2, top + 0.08), 0.8, 0.8, "water", segments=12)
    mb.box((0, 0.5, top + 1.22), (0.36, 0.5, 0.06), "water")
    mb.box((0, 0.22, top + 0.66), (0.36, 0.07, 1.16), "water")
    mb.box((0, 0.2, top + 0.66), (0.12, 0.08, 1.1), "nat_foam")
    for k in range(5):
        a = math.pi * (1.1 + 0.2 * k)
        mb.sphere((math.cos(a) * 0.22, 0.15 + math.sin(a) * 0.12, top + 0.1), 0.08, "nat_foam", segments=5, rings=3)
    for i in range(9):
        a = math.pi * (0.95 + 1.1 * i / 8.0)
        r = 0.17 + 0.05 * (i % 3)
        stone(mb, math.cos(a) * 0.88, -0.2 + math.sin(a) * 0.88, top + r * 0.45, r, (1.1, 1.0, 0.75), mats[i % 3],
              i * 1.3, segments=6, rings=4, floor=top)
    mb.cylinder((0.35, -0.6, top + 0.08), (0.35, -0.6, top + 0.1), 0.18, 0.18, "nat_lily_pad", segments=7)
    mb.cylinder((-0.4, -0.45, top + 0.08), (-0.4, -0.45, top + 0.1), 0.14, 0.14, "nat_lily_pad", segments=7)
    for i, (x, z, r) in enumerate(((-0.55, 1.6, 0.3), (0.55, 1.5, 0.28), (0.0, 1.8, 0.3))):
        puff(mb, x, 0.75, top + z, r, "nat_moss", i * 1.2, sz=0.3, segments=7, rings=3)
    fern(mb, -1.05, 0.0, top, 0.4, fronds=6, reach=0.3)
    fern(mb, 1.05, -0.05, top, 1.4, fronds=6, reach=0.3, mat="nat_leaf_light")
    for i, (x, y) in enumerate(((-1.15, -1.1), (1.15, -1.15), (-1.2, 1.2), (1.2, 1.2))):
        grass_tuft(mb, x, y, top, i * 1.5, "nat_leaf_light")
    finish(folder, "decor_waterfall", mb)


# --- Fifth batch ---------------------------------------------------------------------------

buildings.COLORS.update({
    "nat_wisteria": common.rgb(0xA888E8),
    "nat_wisteria_dark": common.rgb(0x7450C0),
    "nat_pumpkin": common.rgb(0xE87818),
    "nat_pumpkin_light": common.rgb(0xF0A030),
    "nat_flame_red": common.rgb(0xE83018),
    "nat_flame_orange": common.rgb(0xFF8818),
    "nat_flame_yellow": common.rgb(0xFFE050),
    "nat_ash": common.rgb(0x3A3634),
})


def wisteria_pergola(folder):
    """3 x 3: a timber pergola hung with clusters of wisteria."""
    common.reset_scene()
    mb = MeshBuilder()
    top = ground(mb, 3, "nat_gravel", 0.06)
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.box((sx * 1.1, sy * 1.1, top + 0.05), (0.3, 0.3, 0.1), "stone")
            mb.box((sx * 1.1, sy * 1.1, top + 1.1), (0.14, 0.14, 2.1), "timber")
    for sy in (-1, 1):
        mb.box((0, sy * 1.1, top + 2.2), (2.7, 0.12, 0.14), "timber")
    for i in range(6):
        mb.box((-1.15 + 0.46 * i, 0, top + 2.32), (0.08, 2.7, 0.1), "wood")
    for i in range(18):                   # Hanging flower clusters.
        a = i * GOLDEN
        d = 0.25 + 0.95 * math.sqrt(i / 17.0)
        x, y = math.cos(a) * d, math.sin(a) * d
        drop = 0.4 + 0.3 * ((i * 7) % 4) / 3.0
        mb.cylinder((x, y, top + 2.25), (x, y, top + 2.25 - drop * 0.4), 0.04, 0.13, "nat_wisteria", segments=5)
        spike(mb, (x, y, top + 2.25 - drop * 0.4), (x, y, top + 2.25 - drop), 0.13, "nat_wisteria_dark", segments=5)
    for i, (x, y, r) in enumerate(((-0.7, -0.6, 0.5), (0.6, -0.7, 0.45), (0.75, 0.5, 0.5), (-0.5, 0.7, 0.48),
                                   (0.0, 0.0, 0.5))):
        puff(mb, x, y, top + 2.42, r, "nat_leaf" if i % 2 else "leaves", i * 1.6, sz=0.3, segments=7, rings=3)
    # The vine's trunk winds up one post.
    for k in range(6):
        a0, a1 = k * 1.3, (k + 1) * 1.3
        mb.cylinder((-1.1 + math.cos(a0) * 0.11, -1.1 + math.sin(a0) * 0.11, top + 0.35 * k),
                    (-1.1 + math.cos(a1) * 0.11, -1.1 + math.sin(a1) * 0.11, top + 0.35 * (k + 1)), 0.05, 0.045,
                    "nat_bark", segments=4)
    finish(folder, "decor_wisteria_pergola", mb)


def giant_dandelions(folder):
    """2 x 2: dandelions as tall as a person, their seeds drifting off."""
    common.reset_scene()
    mb = MeshBuilder()
    top = bed(mb, 2, fill="nat_grass")
    for j, (x, y, h, r) in enumerate(((0.05, 0.3, 2.1, 0.42), (-0.45, -0.2, 1.4, 0.34), (0.45, -0.3, 1.0, 0.28))):
        c = Vector((x + 0.05 * (j - 1), y, top + h))
        mb.cylinder((x, y, top), c, 0.04, 0.03, "nat_stem", segments=4)
        mb.sphere(c, r * 0.22, "nat_shroom_stem", segments=6, rings=4)
        for k in range(14):
            z = 1 - 2 * (k + 0.5) / 14.0
            a = k * GOLDEN
            d = Vector((math.cos(a) * math.sqrt(1 - z * z), math.sin(a) * math.sqrt(1 - z * z), z))
            mb.cylinder(c + d * r * 0.2, c + d * r * 0.8, 0.008, 0.008, "nat_daisy", segments=3)
            spike(mb, c + d * r, c + d * r * 0.72, r * 0.17, "nat_daisy", segments=3)
        for k in range(5):                # Jagged leaves.
            petal(mb, (x, y, top), j + k * 1.257, 0.3, 0.42, 0.13, "nat_leaf" if k % 2 else "nat_leaf_light", curl=-0.1)
    # A yellow flower still to turn, and seeds on the wind.
    mb.cylinder((-0.3, 0.55, top), (-0.3, 0.55, top + 0.6), 0.03, 0.025, "nat_stem", segments=4)
    flower_head(mb, (-0.3, 0.55, top + 0.6), (0, -0.4, 1), 0.08, 0.1, 9, "nat_tulip_orange", "nat_tulip_yellow",
                petal_r=0.05, thick=0.05, cup=0.03)
    for k in range(5):
        p = Vector((0.45 + 0.07 * k, 0.4 - 0.1 * math.sin(k * 1.7), top + 2.0 + 0.13 * k))
        mb.cylinder(p, p + Vector((0, 0, 0.12)), 0.006, 0.006, "nat_daisy", segments=3)
        spike(mb, p + Vector((0, 0, 0.17)), p + Vector((0, 0, 0.1)), 0.05, "nat_daisy", segments=4)
    finish(folder, "decor_giant_dandelions", mb)


def pumpkin_patch(folder):
    """3 x 3: pumpkins among their vines and leaves."""
    common.reset_scene()
    mb = MeshBuilder()
    top = bed(mb, 3, edge="timber", corner="wood")
    spots = ((-0.55, 0.45, 0.5), (0.6, 0.55, 0.36), (0.5, -0.55, 0.42), (-0.7, -0.65, 0.3), (0.0, -0.1, 0.26),
             (-0.05, 0.95, 0.22))
    for i, (x, y, r) in enumerate(spots):
        verts = mb.sphere((x, y, top + r * 0.68), r, "nat_pumpkin" if i % 2 == 0 else "nat_pumpkin_light",
                          segments=10, rings=5, scale=(1, 1, 0.75))
        for v in verts:                   # Ribs: pull every other meridian in.
            ang = math.atan2(v.co.y - y, v.co.x - x)
            if round(ang / (math.pi / 5)) % 2:
                v.co.x = x + (v.co.x - x) * 0.84
                v.co.y = y + (v.co.y - y) * 0.84
        mb.cylinder((x, y, top + r * 1.35), (x + 0.04, y, top + r * 1.35 + 0.14), 0.045, 0.03, "nat_stem", segments=5)
    prev = None
    for k in range(12):                   # A vine winding between them.
        t = k / 11.0
        p = Vector((-1.1 + 2.2 * t, 0.15 * math.sin(t * 9.0) + 0.1, top + 0.04))
        if prev is not None:
            mb.cylinder(prev, p, 0.03, 0.03, "nat_stem", segments=3)
        prev = p
    for i in range(10):
        a = i * GOLDEN
        d = 0.45 + 0.7 * ((i * 3) % 5) / 4.0
        x, y = math.cos(a) * d, math.sin(a) * d
        mb.cylinder((x, y, top), (x, y, top + 0.22), 0.015, 0.015, "nat_stem", segments=3)
        for k in range(3):
            petal(mb, (x, y, top + 0.22), a + k * 2.094, 0.1, 0.26, 0.13, "nat_leaf" if i % 2 else "nat_leaf_light",
                  curl=-0.1)
    finish(folder, "decor_pumpkin_patch", mb)


def fire_lilies(folder):
    """2 x 2: flowers of living flame growing out of ash."""
    common.reset_scene()
    mb = MeshBuilder()
    top = bed(mb, 2, fill="nat_ash", edge="nat_rock_dark", corner="nat_rock")
    spots = ((0.0, 0.25, 1.3, 0.42), (-0.5, -0.1, 0.85, 0.34), (0.5, 0.0, 0.7, 0.3), (-0.15, -0.55, 0.45, 0.26),
             (0.45, -0.55, 0.35, 0.22))
    for j, (x, y, h, s) in enumerate(spots):
        mb.cylinder((x, y, top), (x, y, top + h), 0.04, 0.03, "charcoal", segments=4)
        for k in range(2):
            petal(mb, (x, y, top + h * (0.3 + 0.25 * k)), j + k * 3.0, 0.5, s * 0.6, s * 0.2, "nat_rock_dark", curl=0.2)
        c = (x, y, top + h)
        for k in range(5):
            petal(mb, c, j + k * 1.257, 0.75, s, s * 0.34, "nat_flame_red", curl=0.45)
        for k in range(4):
            petal(mb, c, j + 0.6 + k * 1.571, 1.1, s * 0.9, s * 0.28, "nat_flame_orange", curl=0.3)
        crystal(mb, Vector(c), Vector(c) + Vector((0.03 * (j - 2), 0, s * 1.15)), s * 0.22, "nat_flame_yellow", waist=0.3)
    for k in range(6):                    # Embers rising.
        a = k * GOLDEN
        p = Vector((math.cos(a) * 0.3, 0.2 + math.sin(a) * 0.3, top + 1.9 + 0.12 * k))
        crystal(mb, p - Vector((0, 0, 0.04)), p + Vector((0, 0, 0.06)), 0.03, "nat_flame_yellow" if k % 2 else
                "nat_flame_orange", waist=0.45)
    for k in range(4):
        a = k * 1.7 + 0.5
        stone(mb, math.cos(a) * 0.68, math.sin(a) * 0.68, top + 0.04, 0.1, (1.1, 0.9, 0.7), "charcoal", k * 1.2,
              segments=6, rings=4, floor=top)
    finish(folder, "decor_fire_lilies", mb)


def stepping_stones(folder):
    """4 x 4: a winding path of flat stones across a lawn, with flowers and shrubs beside it."""
    common.reset_scene()
    mb = MeshBuilder()
    top = ground(mb, 4, "nat_grass")
    mats = ("nat_rock_light", "nat_rock", "nat_gravel")
    for i in range(8):
        t = i / 7.0
        x = 0.55 * math.sin(t * 5.0)
        y = -1.4 + 2.8 * t
        verts = mb.cylinder((x, y, top), (x, y, top + 0.06), 0.34 - 0.03 * (i % 2), 0.3 - 0.03 * (i % 2), mats[i % 3],
                            segments=7)
        lumpy(verts, 0.1, i * 1.7)
    for i, (x, y, r) in enumerate(((-1.3, 1.2, 0.42), (1.35, -0.2, 0.46), (-1.35, -1.25, 0.34))):
        puff(mb, x, y, top + r * 0.6, r, "nat_leaf" if i % 2 else "leaves", i * 1.5, sz=0.8, segments=8, rings=5)
        for k in range(5):
            a = k * GOLDEN + i
            mb.sphere((x + math.cos(a) * r * 0.75, y + math.sin(a) * r * 0.75, top + r * 0.6 + r * 0.45), 0.07,
                      ("nat_rose_white", "nat_blossom", "nat_tulip_yellow")[i], segments=5, rings=3)
    colors = ("nat_poppy", "nat_daisy", "nat_lavender", "nat_tulip_yellow", "nat_hyd_blue")
    spots = ((1.0, 1.3), (1.4, 1.0), (1.2, 1.6), (-1.0, 0.1), (-1.4, 0.3), (-1.2, -0.3), (1.1, -1.4), (1.5, -1.1),
             (0.9, -1.0), (-0.5, 1.6), (0.6, 0.6), (-0.6, -0.9))
    for i, (x, y) in enumerate(spots[:8]):
        small_flower(mb, x, y, top, 0.22 + 0.08 * (i % 3), colors[i % 5], size=0.1, seed=i * 1.3)
    for i, (x, y) in enumerate(((1.6, 0.6), (-1.6, 0.9), (-0.3, -1.6), (0.8, 1.7), (-1.7, -0.6), (1.7, -1.7))):
        grass_tuft(mb, x, y, top, i * 1.4, "nat_leaf_light")
    stone(mb, 1.2, 0.55, top + 0.12, 0.26, (1.1, 0.9, 0.8), "nat_rock_dark", 3.1, segments=7, rings=4, floor=top)
    finish(folder, "decor_stepping_stones", mb)


# --- Sixth batch ---------------------------------------------------------------------------


def moon_flowers(folder):
    """2 x 2: pale flowers that each cup a glowing orb."""
    common.reset_scene()
    mb = MeshBuilder()
    top = bed(mb, 2, fill="nat_moss", edge="nat_rock_dark", corner="nat_rock")
    spots = ((0.0, 0.3, 1.7, 0.2), (-0.5, -0.05, 1.15, 0.16), (0.5, 0.0, 0.9, 0.15), (0.0, -0.5, 0.5, 0.12))
    for j, (x, y, h, r) in enumerate(spots):
        lean = 0.12 * (j - 1.5)
        pts = [Vector((x + lean * t * t, y, top + h * t)) for t in (0.0, 0.35, 0.7, 1.0)]
        for k in range(3):
            mb.cylinder(pts[k], pts[k + 1], 0.035, 0.03, "nat_glow_stem", segments=4)
        c = pts[-1]
        for k in range(6):
            petal(mb, c, j + k * 1.047, 0.35, r * 2.2, r * 0.9, "nat_lotus" if k % 2 else "nat_daisy", curl=0.3)
        mb.sphere(c + Vector((0, 0, r * 1.15)), r, "nat_glow_core", segments=7, rings=5)
        for k in range(3):
            petal(mb, (x, y, top), j * 1.3 + k * 2.094, 0.35, 0.4, 0.13, "nat_glow_stem" if k % 2 else "nat_leaf", curl=0.1)
    for k in range(5):                    # Motes of light.
        a = k * GOLDEN
        p = Vector((math.cos(a) * 0.5, math.sin(a) * 0.5, top + 0.8 + 0.3 * k))
        crystal(mb, p - Vector((0, 0, 0.04)), p + Vector((0, 0, 0.06)), 0.03, "nat_glow_blue", waist=0.45)
    finish(folder, "decor_moon_flowers", mb)


def vine_trellis(folder):
    """2 x 2: a wooden fan trellis in a planter, covered by a flowering climber."""
    common.reset_scene()
    mb = MeshBuilder()
    top = ground(mb, 2, "nat_gravel", 0.06)
    mb.box((0, 0.35, top + 0.2), (1.7, 0.6, 0.4), "wood")
    mb.box((0, 0.35, top + 0.41), (1.56, 0.46, 0.03), "soil")
    for sx in (-1, 1):
        mb.box((sx * 0.8, 0.35, top + 0.22), (0.1, 0.66, 0.46), "timber")
    for k in range(5):                    # The fan of laths.
        a = math.pi * (0.25 + 0.125 * k)
        mb.cylinder((0, 0.5, top + 0.4), (math.cos(a) * 1.6 * 0.5, 0.5, top + 0.4 + math.sin(a) * 2.0), 0.03, 0.03,
                    "timber", segments=4)
    for z, w in ((1.0, 0.7), (1.6, 1.15), (2.15, 1.5)):
        mb.box((0, 0.5, top + z), (w, 0.05, 0.06), "wood_light")
    for i in range(12):                   # Leaves and flowers climbing the fan.
        t = (i + 1) / 13.0
        a = math.pi * (0.25 + 0.5 * ((i * 5) % 12) / 11.0)
        x = math.cos(a) * 0.8 * (0.3 + 0.7 * t)
        z = top + 0.55 + 1.75 * t
        puff(mb, x, 0.42, z, 0.2, "nat_leaf" if i % 2 else "leaves", i * 1.3, sz=0.8, segments=6, rings=3)
        flower_head(mb, (x + 0.08 * (1 if i % 2 else -1), 0.26, z + 0.05), (0, -1, 0.2), 0.035, 0.1, 6,
                    "nat_daisy_core", "nat_wisteria" if i % 3 else "nat_orchid", petal_r=0.05, thick=0.03, cup=0.02)
    for i, x in enumerate((-0.55, 0.0, 0.55)):
        puff(mb, x, 0.18, top + 0.48, 0.18, "nat_leaf_light", i * 1.1, sz=0.6, segments=6, rings=3)
    for i, (x, y) in enumerate(((-0.6, -0.5), (0.6, -0.55), (0.0, -0.7))):
        small_flower(mb, x, y, top, 0.2, ("nat_poppy", "nat_daisy", "nat_tulip_yellow")[i], size=0.08, seed=i * 2.0)
    finish(folder, "decor_vine_trellis", mb)


def herb_spiral(folder):
    """3 x 3: a spiral bed of stacked stones rising to the middle, planted all the way up."""
    common.reset_scene()
    mb = MeshBuilder()
    top = ground(mb, 3, "nat_grass")
    for k, (r, z) in enumerate(((1.2, 0.2), (0.85, 0.5), (0.5, 0.8))):
        mb.cylinder((0, 0, top), (0, 0, top + z), r, r - 0.05, "soil", segments=10)
    mats = ("nat_rock", "nat_rock_light", "nat_rock_dark")
    for i in range(21):                   # The spiral wall.
        t = i / 20.0
        a = t * 3.0 * math.pi
        r = 1.15 - 0.75 * t
        z = top + 0.12 + 0.7 * t
        stone(mb, math.cos(a) * r, math.sin(a) * r, z, 0.2, (1.0, 1.0, 1.0), mats[i % 3], i * 1.3, segments=6,
              rings=4, floor=-9)
    greens = ("nat_leaf_light", "nat_lavender_leaf", "nat_leaf", "leaves")
    blooms = ("nat_lavender", "nat_daisy", "nat_tulip_yellow", "nat_rose_pink")
    for i in range(14):
        t = (i + 0.5) / 14.0
        a = t * 3.0 * math.pi + 0.1
        r = max(0.92 - 0.9 * t, 0.0)
        z = top + 0.2 + 0.6 * t
        x, y = math.cos(a) * r, math.sin(a) * r
        puff(mb, x, y, z + 0.05, 0.17, greens[i % 4], i * 1.7, sz=0.8, segments=6, rings=3)
        if i % 2 == 0:
            spike(mb, (x, y, z + 0.1), (x, y, z + 0.42), 0.05, blooms[(i // 2) % 4], segments=4)
        else:
            mb.sphere((x, y, z + 0.2), 0.06, blooms[(i // 2) % 4], segments=5, rings=3)
    for i, (x, y) in enumerate(((-1.25, -1.25), (1.25, -1.25), (1.25, 1.25), (-1.25, 1.25))):
        grass_tuft(mb, x, y, top, i * 1.5, "nat_leaf_light")
    finish(folder, "decor_herb_spiral", mb)


MODELS = (rose_bed, tulip_bed, glow_bells, mushroom_flowers, crystal_flowers, carnivorous_plant, pond, rose_arch,
          sunflowers, lavender, standing_stone, mossy_boulders, rock_garden, fern_log, daisies, lilies,
          flowering_shrub, fairy_ring, giant_lotus, glow_stump, poppies, hydrangeas, cacti, bird_bath, beehive,
          stone_arch, geode, wildflowers, eye_vine, floating_petals, orchids, bonsai_rock,
          crystal_tree, bamboo, topiary, parterre, waterfall, wisteria_pergola, giant_dandelions,
          pumpkin_patch, fire_lilies, stepping_stones, moon_flowers, vine_trellis, herb_spiral)


def make_all(folder, only=None):
    os.makedirs(folder, exist_ok=True)
    for model in MODELS:
        if only and model.__name__ not in only:
            continue
        model(folder)


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if not args:
        raise SystemExit("usage: blender --background --factory-startup --python nature.py -- <output folder> [model ...]")
    make_all(args[0], set(args[1:]) or None)
