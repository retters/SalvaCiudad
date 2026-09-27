"""Props: trees (pine, oak), a boulder, an iron ore outcrop, a berry bush,
an herb plant and a small half-timbered house with architectural details
(beams, window frames, shutters, door, chimney, roof tiles in rows)."""

import math
import os

import common
from common import MeshBuilder

COLORS = {
    "bark": common.rgb(0x5C3F28),
    "needles": common.rgb(0x3F6B35),
    "needles_dark": common.rgb(0x2F5429),
    "rock": common.rgb(0x8A8580),
    "rock_dark": common.rgb(0x6E6A66),
    "moss": common.rgb(0x5E7440),
    "plaster": common.rgb(0xE6DCC4),
    "timber": common.rgb(0x5A3B24),
    "roof": common.rgb(0x9A4A2E),
    "roof_dark": common.rgb(0x7E3A24),
    "stone": common.rgb(0x9A938A),
    "door": common.rgb(0x6B4A2E),
    "window": common.rgb(0x2B3440),
    "shutter": common.rgb(0x4F6B4A),
    "leaves": common.rgb(0x4E7A34),
    "leaves_dark": common.rgb(0x3D6629),
    "ore": common.rgb(0x8A4E34),
    "ore_dark": common.rgb(0x5E3526),
    "bush": common.rgb(0x3F6B32),
    "berries": common.rgb(0xA8243A),
    "herb": common.rgb(0x5E8A44),
    "flowers": common.rgb(0x9C6AC8),
    "cloud": common.rgb(0xF4F6F8),
    "cloud_shade": common.rgb(0xDDE3EA),
}


def lumpy(verts, amount, seed):
    """Deterministic lumps on a sphere: push vertices by a fixed pattern."""
    ordered = sorted(verts, key=lambda v: (round(v.co.z, 4), round(v.co.x, 4), round(v.co.y, 4)))
    cx = sum(v.co.x for v in verts) / len(verts)
    cy = sum(v.co.y for v in verts) / len(verts)
    for i, v in enumerate(ordered):
        k = 1.0 + amount * math.sin(i * 2.3 + seed) + amount * 0.5 * math.cos(i * 5.1 + seed)
        v.co.x = cx + (v.co.x - cx) * k
        v.co.y = cy + (v.co.y - cy) * k


def oak_tree(folder):
    common.reset_scene()
    mb = MeshBuilder()
    mb.cylinder((0, 0, 0), (0, 0, 2.6), 0.28, 0.2, "bark", segments=8)
    mb.cylinder((0, 0, 2.2), (0.9, 0.3, 3.4), 0.12, 0.07, "bark", segments=6)
    mb.cylinder((0, 0, 2.4), (-0.7, -0.5, 3.5), 0.12, 0.07, "bark", segments=6)
    # A rounded crown of overlapping leaf clumps.
    clumps = ((0, 0, 4.1, 1.6), (1.0, 0.4, 3.6, 1.1), (-0.9, -0.5, 3.7, 1.15), (0.2, -1.0, 3.5, 1.0),
              (-0.3, 1.0, 3.8, 1.05), (0.1, 0.1, 5.0, 1.0))
    for i, (x, y, z, r) in enumerate(clumps):
        verts = mb.sphere((x, y, z), r, "leaves" if i % 2 == 0 else "leaves_dark", segments=9, rings=6,
                          scale=(1.0, 1.0, 0.85))
        lumpy(verts, 0.08, i)
    obj = mb.to_object("tree_oak", COLORS)
    common.export_glb(os.path.join(folder, "tree_oak.glb"), [obj])


def ore_rock(folder, name="ore_rock", seed=1.7, scale=(1.15, 1.0, 0.75),
             veins=((0.45, -0.45, 0.75, 0.28), (-0.5, -0.3, 0.55, 0.24), (0.1, 0.55, 0.85, 0.22),
                    (-0.15, -0.65, 0.35, 0.2)), knob=(0.75, 0.3, 0.3)):
    common.reset_scene()
    mb = MeshBuilder()
    verts = mb.sphere((0, 0, 0.5), 0.8, "rock_dark", segments=9, rings=6, scale=scale)
    lumpy(verts, 0.12, seed)
    for v in verts:
        if v.co.z < 0.05:
            v.co.z = 0.0
    # Rusty veins of iron ore breaking the surface.
    for x, y, z, r in veins:
        mb.sphere((x, y, z), r, "ore", segments=6, rings=4, scale=(1.2, 0.9, 0.8))
    mb.sphere(knob, 0.3, "ore_dark", segments=7, rings=5)
    obj = mb.to_object(name, COLORS)
    common.export_glb(os.path.join(folder, name + ".glb"), [obj])


def berry_bush(folder, name="berry_bush",
               puffs=((0, 0, 0.45, 0.55), (0.4, 0.2, 0.35, 0.4), (-0.35, 0.25, 0.35, 0.42), (0.05, -0.35, 0.33, 0.38)),
               berries=14, reach=(0.6, 0.47), height=(0.3, 0.35)):
    common.reset_scene()
    mb = MeshBuilder()
    for i, (x, y, z, r) in enumerate(puffs):
        verts = mb.sphere((x, y, z), r, "bush", segments=8, rings=5, scale=(1.0, 1.0, 0.8))
        lumpy(verts, 0.1, i)
    # Berries in small groups on the outside.
    for i in range(berries):
        a = i * 2.399963
        h = height[0] + height[1] * ((i * 7) % 5) / 5.0
        r = reach[0] if h < height[0] + height[1] * 0.55 else reach[1]
        mb.sphere((math.cos(a) * r, math.sin(a) * r, h), 0.06, "berries", segments=5, rings=3)
    obj = mb.to_object(name, COLORS)
    common.export_glb(os.path.join(folder, name + ".glb"), [obj])


def herb(folder):
    common.reset_scene()
    mb = MeshBuilder()
    for i in range(7):
        a = i * 2.399963
        tip = (math.cos(a) * 0.18, math.sin(a) * 0.18, 0.35 + 0.08 * (i % 3))
        mb.cylinder((0, 0, 0), tip, 0.03, 0.012, "herb", segments=4)
        mb.sphere(tip, 0.045, "flowers", segments=5, rings=3)
    mb.sphere((0, 0, 0.06), 0.14, "herb", segments=7, rings=4, scale=(1.0, 1.0, 0.5))
    obj = mb.to_object("herb", COLORS)
    common.export_glb(os.path.join(folder, "herb.glb"), [obj])


def pine_tree(folder):
    common.reset_scene()
    mb = MeshBuilder()
    mb.cylinder((0, 0, 0), (0, 0, 1.9), 0.2, 0.12, "bark", segments=7)
    # Four stacked tiers, alternating two greens, each turned a little.
    tiers = ((1.1, 3.4, 1.45), (2.1, 4.3, 1.15), (3.0, 5.1, 0.85), (3.9, 5.8, 0.55))
    for i, (z0, z1, r) in enumerate(tiers):
        mat = "needles" if i % 2 == 0 else "needles_dark"
        verts = mb.cylinder((0, 0, z0), (0, 0, z1), r, 0.0, mat, segments=8)
        angle = i * 0.35
        c, s = math.cos(angle), math.sin(angle)
        for v in verts:
            x, y = v.co.x, v.co.y
            v.co.x, v.co.y = x * c - y * s, x * s + y * c
    obj = mb.to_object("tree_pine", COLORS)
    common.export_glb(os.path.join(folder, "tree_pine.glb"), [obj])


def rock_variant(folder, name, parts, seed):
    """A boulder made of several lumpy stones: (x, y, z, r, sx, sy, sz, mat)."""
    common.reset_scene()
    mb = MeshBuilder()
    for n, (x, y, z, r, sx, sy, sz, mat) in enumerate(parts):
        verts = mb.sphere((x, y, z), r, mat, segments=8, rings=6, scale=(sx, sy, sz))
        lumpy(verts, 0.13, seed + n * 1.3)
        for v in verts:
            if v.co.z < 0.03:
                v.co.z = 0.0
    obj = mb.to_object(name, COLORS)
    common.export_glb(os.path.join(folder, name + ".glb"), [obj])


def rock(folder):
    common.reset_scene()
    mb = MeshBuilder()
    verts = mb.sphere((0, 0, 0.45), 0.75, "rock", segments=9, rings=6, scale=(1.2, 1.0, 0.7))
    # Deterministic lumps: push vertices in and out by a fixed pattern.
    for i, v in enumerate(sorted(verts, key=lambda v: (round(v.co.z, 4), round(v.co.x, 4), round(v.co.y, 4)))):
        k = 1.0 + 0.12 * math.sin(i * 2.3) + 0.06 * math.cos(i * 5.1)
        v.co.x *= k
        v.co.y *= k
        if v.co.z < 0.05:
            v.co.z = 0.0
    top = mb.sphere((0.25, -0.1, 0.78), 0.32, "moss", segments=7, rings=4, scale=(1.3, 1.0, 0.35))
    del top
    mb.sphere((-0.7, 0.35, 0.2), 0.32, "rock_dark", segments=7, rings=5, scale=(1.0, 0.9, 0.7))
    obj = mb.to_object("rock", COLORS)
    common.export_glb(os.path.join(folder, "rock.glb"), [obj])


def house(folder):
    """A 5 x 4 m house facing -Y (the door side)."""
    common.reset_scene()
    mb = MeshBuilder()
    w, d, h = 2.5, 2.0, 2.6   # Half width, half depth, wall height.
    # Stone footing and plaster walls.
    mb.box((0, 0, 0.2), (2 * w + 0.12, 2 * d + 0.12, 0.4), "stone")
    mb.box((0, 0, 0.4 + (h - 0.4) / 2), (2 * w, 2 * d, h - 0.4), "plaster")
    # Timber frame: corner posts, sill, top plate, a middle beam and braces.
    t = 0.14
    for x in (-w, w):
        for y in (-d, d):
            mb.box((x, y, 0.4 + (h - 0.4) / 2), (t, t, h - 0.4), "timber")
    for y in (-d, d):
        mb.box((0, y, 0.45), (2 * w, t, t), "timber")
        mb.box((0, y, h - 0.05), (2 * w, t, t), "timber")
        mb.box((0, y, 1.55), (2 * w, t * 0.8, t * 0.8), "timber")
        for x in (-w / 2, w / 2):
            mb.box((x, y, 0.4 + (h - 0.4) / 2), (t * 0.9, t, h - 0.4), "timber")
    for x in (-w, w):
        mb.box((x, 0, 0.45), (t, 2 * d, t), "timber")
        mb.box((x, 0, h - 0.05), (t, 2 * d, t), "timber")
    # Diagonal braces on the long walls.
    for y in (-d - 0.01, d + 0.01):
        for x0, sign in ((-w, 1), (w, -1)):
            length = math.hypot(w / 2, 1.1)
            angle = math.atan2(1.1, w / 2)
            cx = x0 + sign * w / 4
            verts = mb.box((cx, y, 1.0), (length, t * 0.7, t * 0.7), "timber")
            c, s = math.cos(angle * sign), math.sin(angle * sign)
            for v in verts:
                dx, dz = v.co.x - cx, v.co.z - 1.0
                v.co.x, v.co.z = cx + dx * c - dz * s, 1.0 + dx * s + dz * c

    # Door with a frame on the front (-Y); windows with shutters.
    mb.box((0, -d - 0.04, 1.2), (1.0, 0.06, 1.7), "timber")
    mb.box((0, -d - 0.06, 1.15), (0.82, 0.06, 1.55), "door")
    for x in (-1.6, 1.6):
        for y, face in ((-d, -1), (d, 1)):
            mb.box((x, y + face * 0.04, 1.75), (0.8, 0.06, 0.7), "timber")
            mb.box((x, y + face * 0.06, 1.75), (0.62, 0.06, 0.52), "window")
            for side in (-1, 1):
                mb.box((x + side * 0.52, y + face * 0.06, 1.75), (0.28, 0.05, 0.6), "shutter")
            mb.box((x, y + face * 0.12, 1.35), (0.9, 0.18, 0.06), "timber")  # Sill.

    # Roof: two slopes of overlapping tile rows, gables and a chimney.
    ridge = h + 1.9
    eave = 0.45
    rows = 6
    for side in (-1, 1):
        for r in range(rows):
            t0 = r / rows
            t1 = (r + 1) / rows + 0.04
            y0 = side * (d + eave) * (1 - t0)
            y1 = side * (d + eave) * (1 - min(t1, 1.0))
            z0 = h - 0.15 + (ridge - (h - 0.15)) * t0
            z1 = h - 0.15 + (ridge - (h - 0.15)) * min(t1, 1.0)
            mat = "roof" if r % 2 == 0 else "roof_dark"
            ys = sorted((y0, y1))
            pts = [(-w - eave, ys[0]), (w + eave, ys[0]), (w + eave, ys[1]), (-w - eave, ys[1])]
            verts = mb.prism(pts, 0.0, 0.08, mat)
            # Shear the slab to follow the slope.
            for v in verts:
                frac = (abs(v.co.y) - abs(y1)) / max(1e-6, abs(y0) - abs(y1)) if side > 0 else \
                       (abs(v.co.y) - abs(y1)) / max(1e-6, abs(y0) - abs(y1))
                v.co.z += z1 + (z0 - z1) * frac
    for x in (-w, w):
        gable = mb.prism([(-d, h), (d, h), (0, ridge - 0.05)], x - 0.05, x + 0.05, "plaster")
        for v in gable:
            v.co.x, v.co.y, v.co.z = v.co.z, v.co.x, v.co.y
        mb.box((x * 1.0, 0, h + 0.8), (0.12, 0.12, 1.6), "timber")
    mb.box((0, 0, ridge + 0.04), (2 * w + 2 * eave, 0.22, 0.14), "roof_dark")
    mb.box((1.4, 0.8, ridge - 0.3), (0.55, 0.55, 1.8), "stone")
    mb.box((1.4, 0.8, ridge + 0.62), (0.68, 0.68, 0.1), "stone")

    obj = mb.to_object("house_small", COLORS)
    common.export_glb(os.path.join(folder, "house_small.glb"), [obj])


CLOUD_PUFFS = ((0.0, 0.0, 0.55, 1.0), (1.1, 0.2, 0.45, 0.8), (-1.1, -0.1, 0.42, 0.75), (0.45, -0.45, 0.75, 0.7),
               (-0.5, 0.4, 0.7, 0.65), (1.8, -0.1, 0.3, 0.5))


def cloud(folder, name="cloud", puffs=CLOUD_PUFFS):
    """A low-poly cloud: a few lumpy, flattened puffs, about 4 m long (the
    game scales it up)."""
    common.reset_scene()
    mb = MeshBuilder()
    for i, (x, y, z, r) in enumerate(puffs):
        verts = mb.sphere((x, y, z), r, "cloud" if i % 3 else "cloud_shade", segments=7, rings=5,
                          scale=(1.25, 1.0, 0.7))
        lumpy(verts, 0.12, i * 1.9)
        for v in verts:
            if v.co.z < 0.2:
                v.co.z = 0.2 + (v.co.z - 0.2) * 0.3  # Flatter underside.
    obj = mb.to_object(name, COLORS)
    common.export_glb(os.path.join(folder, name + ".glb"), [obj])


def make_all(folder):
    os.makedirs(folder, exist_ok=True)
    pine_tree(folder)
    oak_tree(folder)
    rock(folder)
    ore_rock(folder)
    berry_bush(folder)
    herb(folder)
    house(folder)
    cloud(folder)
    variants(folder)


def variants(folder):
    """More looks of the same things (phase 31)."""
    # Boulders: a tall stone leaning on a small one, and a low flat group.
    rock_variant(folder, "rock_2", ((0.0, 0.0, 0.6, 0.6, 0.9, 0.8, 1.35, "rock"),
                                    (0.55, 0.3, 0.2, 0.35, 1.1, 1.0, 0.7, "rock_dark"),
                                    (-0.1, -0.2, 1.05, 0.22, 1.2, 1.0, 0.4, "moss")), 0.7)
    rock_variant(folder, "rock_3", ((-0.35, 0.1, 0.25, 0.55, 1.4, 1.0, 0.55, "rock"),
                                    (0.5, -0.25, 0.2, 0.45, 1.2, 1.1, 0.5, "rock_dark"),
                                    (0.1, 0.5, 0.15, 0.3, 1.0, 1.0, 0.6, "rock"),
                                    (-0.4, 0.05, 0.5, 0.25, 1.5, 1.1, 0.3, "moss")), 2.9)
    ore_rock(folder, "ore_rock_2", seed=3.1, scale=(0.9, 1.05, 1.05),
             veins=((0.3, -0.55, 0.9, 0.26), (-0.45, 0.1, 1.0, 0.22), (0.5, 0.35, 0.5, 0.24)), knob=(-0.6, -0.4, 0.3))
    ore_rock(folder, "ore_rock_3", seed=5.3, scale=(1.35, 1.1, 0.6),
             veins=((0.7, -0.3, 0.55, 0.25), (-0.6, -0.45, 0.45, 0.24), (-0.1, 0.6, 0.6, 0.2),
                    (0.2, -0.1, 0.8, 0.22), (-0.9, 0.3, 0.3, 0.2)), knob=(0.9, 0.45, 0.25))
    # Bushes: taller and narrow, and low and wide.
    berry_bush(folder, "berry_bush_2", puffs=((0, 0, 0.6, 0.45), (0.15, 0.1, 0.95, 0.35), (-0.2, 0.15, 0.35, 0.38)),
               berries=12, reach=(0.48, 0.4), height=(0.35, 0.6))
    berry_bush(folder, "berry_bush_3", puffs=((-0.45, 0, 0.3, 0.45), (0.1, 0.15, 0.32, 0.5), (0.6, -0.1, 0.28, 0.42),
                                              (0.0, -0.4, 0.25, 0.38), (0.3, 0.5, 0.25, 0.35)),
               berries=18, reach=(0.75, 0.6), height=(0.2, 0.3))
    # Clouds: a long flat one, a tall heap and a small pair.
    cloud(folder, "cloud_2", ((-2.4, 0.0, 0.35, 0.7), (-1.3, 0.2, 0.4, 0.85), (0.0, -0.1, 0.45, 0.9),
                              (1.3, 0.15, 0.4, 0.8), (2.4, -0.05, 0.35, 0.65), (0.6, -0.4, 0.3, 0.55)))
    cloud(folder, "cloud_3", ((0.0, 0.0, 0.6, 1.1), (0.9, 0.2, 0.55, 0.85), (-0.9, -0.1, 0.5, 0.8),
                              (0.2, 0.0, 1.4, 0.85), (-0.4, 0.2, 2.0, 0.6), (0.5, -0.2, 1.1, 0.7)))
    cloud(folder, "cloud_4", ((0.0, 0.0, 0.4, 0.7), (0.8, 0.1, 0.35, 0.55), (-2.0, 0.6, 0.35, 0.5),
                              (-2.6, 0.4, 0.3, 0.4)))
