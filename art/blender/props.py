"""Props: a boulder, an iron ore outcrop, a berry bush,
an herb plant and a small half-timbered house with architectural details
(beams, window frames, shutters, door, chimney, roof tiles in rows).
Since phase 67 also the piles of goods shown at construction sites and
storages (pile_<what>_<level>), the merchant's hand cart and the settlers'
wagon."""

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
    # Piles and the cart (phase 67).
    "log": common.rgb(0x7A5232),
    "log_dark": common.rgb(0x64422A),
    "log_end": common.rgb(0xC8A06A),
    "block": common.rgb(0x8C8A88),
    "block_light": common.rgb(0xA3A19E),
    "block_dark": common.rgb(0x6F6D6C),
    "sack": common.rgb(0xCDB98E),
    "sack_dark": common.rgb(0xB39E74),
    "rope": common.rgb(0x8A6A3C),
    "plank": common.rgb(0xB08A5A),
    "plank_dark": common.rgb(0x8A6038),
    "wicker": common.rgb(0xB88E52),
    "wicker_dark": common.rgb(0x8E6A3A),
    "apples": common.rgb(0xC8342A),
    "grain": common.rgb(0xD8B85A),
    "greens": common.rgb(0x4E8A34),
    "iron": common.rgb(0x44484E),
    "awning": common.rgb(0xA8403A),
    "awning_light": common.rgb(0xE8E4D8),
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


# --- Piles of goods and the merchant's cart (phase 67) ------------------------------------


def pile_log(mb, x0, x1, y, z, r, mat="log"):
    mb.cylinder((x0, y, z), (x1, y, z), r, r, mat, segments=7)
    for x in (x0, x1):
        mb.cylinder((x - 0.006, y, z), (x + 0.006, y, z), r * 0.86, r * 0.86, "log_end", segments=7)


def pile_crate(mb, cx, cy, z, s, turn=0.0):
    """A crate of side s standing at height z: planks with darker battens."""
    mb.box((cx, cy, z + s / 2), (s - 0.03, s - 0.03, s - 0.02), "plank", rotation_z=turn)
    for dz in (0.05, s - 0.05):
        mb.box((cx, cy, z + dz), (s, s, 0.07), "plank_dark", rotation_z=turn)
    c, n = math.cos(turn), math.sin(turn)
    for sx in (-1, 1):
        for sy in (-1, 1):
            dx, dy = sx * (s - 0.07) / 2, sy * (s - 0.07) / 2
            mb.box((cx + dx * c - dy * n, cy + dx * n + dy * c, z + s / 2), (0.07, 0.07, s), "plank_dark",
                   rotation_z=turn)


def pile_sack(mb, cx, cy, z, turn=0.0, seed=0.0, mat="sack"):
    """A full sack lying down at height z, its tied neck toward its +X."""
    c, n = math.cos(turn), math.sin(turn)
    verts = mb.sphere((0, 0, 0), 0.3, mat, segments=7, rings=5, scale=(1.1, 0.75, 0.42))
    lumpy(verts, 0.07, seed)
    verts += mb.cylinder((0.3, 0, 0.0), (0.4, 0, 0.02), 0.035, 0.03, "rope", segments=5)
    verts += mb.cylinder((0.4, 0, 0.02), (0.47, 0, 0.04), 0.03, 0.07, mat, segments=5)
    for v in verts:
        x, y = v.co.x, v.co.y
        v.co.x, v.co.y, v.co.z = cx + x * c - y * n, cy + x * n + y * c, max(z, z + 0.125 + v.co.z)


def pile_basket(mb, cx, cy, z, fill, r=0.3, h=0.38):
    """A round basket standing at height z, heaped with `fill`."""
    mb.cylinder((cx, cy, z), (cx, cy, z + h * 0.5), r * 0.78, r * 0.92, "wicker_dark", segments=8)
    mb.cylinder((cx, cy, z + h * 0.5), (cx, cy, z + h), r * 0.92, r, "wicker", segments=8)
    mb.cylinder((cx, cy, z + h - 0.02), (cx, cy, z + h + 0.03), r * 1.06, r * 1.06, "wicker_dark", segments=8)
    mb.sphere((cx, cy, z + h + 0.02), r * 0.9, fill, segments=8, rings=4, scale=(1.0, 1.0, 0.35))


def pile_stone(mb, x, y, z, r, scale, seed, mat):
    verts = mb.sphere((x, y, z), r, mat, segments=6, rings=4, scale=scale)
    lumpy(verts, 0.12, seed)
    for v in verts:
        v.co.z = max(v.co.z, 0.0)


# How many items each level of a pile holds: 1 a few, 2 about half, 3 full.
PILE_COUNTS = {"logs": (3, 7, 12), "stone": (3, 6, 10), "sacks": (3, 7, 12), "crates": (2, 4, 8),
               "baskets": (2, 4, 5)}

# Logs: (y, z); 1.4 m long, lying along X.
PILE_LOGS = ((-0.3, 0.13), (0.0, 0.13), (0.3, 0.13), (-0.58, 0.13), (0.58, 0.13), (-0.15, 0.36), (0.15, 0.36),
             (-0.44, 0.36), (0.44, 0.36), (0.0, 0.59), (-0.29, 0.59), (0.29, 0.59))
# Stones: (x, y, z, radius, scale).
PILE_STONES = ((-0.3, -0.25, 0.2, 0.3, (1.1, 1.0, 0.8)), (0.35, -0.3, 0.18, 0.27, (1.0, 1.1, 0.8)),
               (0.05, 0.3, 0.2, 0.3, (1.2, 0.9, 0.8)), (-0.5, 0.35, 0.17, 0.25, (1.0, 1.0, 0.8)),
               (0.52, 0.2, 0.18, 0.26, (0.9, 1.1, 0.85)), (0.0, -0.55, 0.15, 0.22, (1.2, 0.9, 0.8)),
               (-0.15, 0.0, 0.52, 0.28, (1.1, 1.0, 0.75)), (0.3, 0.0, 0.5, 0.25, (1.0, 1.0, 0.8)),
               (-0.1, 0.38, 0.5, 0.22, (1.0, 0.9, 0.8)), (0.08, 0.05, 0.8, 0.22, (1.1, 1.0, 0.7)))
# Sacks: (x, y, z, turn in degrees).
PILE_SACKS = ((-0.33, -0.5, 0.0, 0), (-0.33, 0.0, 0.0, 6), (0.38, -0.5, 0.0, 180), (-0.33, 0.5, 0.0, -5),
              (0.38, 0.0, 0.0, 174), (0.38, 0.5, 0.0, 184), (0.02, -0.28, 0.21, 92), (0.02, 0.3, 0.21, 88),
              (-0.38, 0.0, 0.2, 80), (0.42, 0.02, 0.2, 100), (0.0, -0.05, 0.4, 4), (0.05, 0.38, 0.38, 176))
# Crates: (x, y, z, side, turn in degrees).
PILE_CRATES = ((-0.36, -0.36, 0.0, 0.66, 0), (0.38, -0.33, 0.0, 0.6, 8), (-0.36, 0.38, 0.0, 0.62, -4),
               (0.38, 0.38, 0.0, 0.66, 0), (-0.3, -0.25, 0.66, 0.56, 12), (0.34, 0.3, 0.66, 0.52, -9),
               (-0.32, 0.38, 0.62, 0.48, 3), (0.3, -0.3, 0.6, 0.44, 30))
# Baskets: (x, y, z, what it holds).
PILE_BASKETS = ((-0.36, -0.36, 0.0, "apples"), (0.36, 0.36, 0.0, "grain"), (0.36, -0.36, 0.0, "greens"),
                (-0.36, 0.36, 0.0, "apples"), (0.0, 0.0, 0.4, "grain"))


def pile(folder, what, level):
    """One fill level (1 to 3) of a pile of goods, about 1.5 x 1.5 m, its
    origin at the center of its base: props/pile_<what>_<level>.glb."""
    common.reset_scene()
    mb = MeshBuilder()
    count = PILE_COUNTS[what][level - 1]
    if what == "logs":
        for i, (y, z) in enumerate(PILE_LOGS[:count]):
            shift = 0.04 * math.sin(i * 2.1)
            pile_log(mb, -0.7 + shift, 0.7 + shift, y, z, 0.13, "log" if i % 3 else "log_dark")
    elif what == "stone":
        for i, (x, y, z, r, scale) in enumerate(PILE_STONES[:count]):
            pile_stone(mb, x, y, z, r, scale, i * 1.7, ("block", "block_dark", "block_light")[i % 3])
    elif what == "sacks":
        for i, (x, y, z, turn) in enumerate(PILE_SACKS[:count]):
            pile_sack(mb, x, y, z, math.radians(turn), i * 1.3, "sack" if i % 3 else "sack_dark")
    elif what == "crates":
        for x, y, z, s, turn in PILE_CRATES[:count]:
            pile_crate(mb, x, y, z, s, math.radians(turn))
    elif what == "baskets":
        for x, y, z, fill in PILE_BASKETS[:count]:
            pile_basket(mb, x, y, z, fill)
    name = f"pile_{what}_{level}"
    obj = mb.to_object(name, COLORS)
    common.export_glb(os.path.join(folder, name + ".glb"), [obj])


def piles(folder):
    for what in sorted(PILE_COUNTS):
        for level in (1, 2, 3):
            pile(folder, what, level)


def cart(folder):
    """The merchant's hand cart: two wheels, two shafts toward -Y (its
    front), loaded with crates, sacks and a barrel under a cloth awning.
    2.2 m long (2.3 m with the awning's overhang), 1.3 m wide, standing on Z = 0."""
    common.reset_scene()
    mb = MeshBuilder()
    bed = 0.62            # Height of the floor of the cart.
    y0, y1 = -0.55, 0.9   # The bed, front to back.
    half = 0.5            # Half width of the bed.
    mid = (y0 + y1) / 2
    mb.box((0, mid, bed - 0.04), (2 * half, y1 - y0, 0.08), "plank")
    for x in (-half, half):
        mb.box((x, mid, bed + 0.13), (0.05, y1 - y0, 0.26), "plank_dark")
    for y in (y0, y1):
        mb.box((0, y, bed + 0.13), (2 * half, 0.05, 0.26), "plank_dark")
    # The shafts a person pulls it by, joined by a bar, and the legs it rests on.
    for x in (-0.42, 0.42):
        mb.cylinder((x, y1 - 0.1, bed - 0.12), (x, -1.3, bed + 0.1), 0.035, 0.03, "timber", segments=5)
        mb.box((x, y0 + 0.08, (bed - 0.1) / 2), (0.07, 0.07, bed - 0.1), "timber")
    mb.cylinder((-0.46, -1.24, bed + 0.09), (0.46, -1.24, bed + 0.09), 0.028, 0.028, "timber", segments=5)
    # Wheels and axle.
    wy, wr = 0.35, 0.45
    mb.cylinder((-0.6, wy, wr), (0.6, wy, wr), 0.04, 0.04, "iron", segments=6)
    for x in (-0.61, 0.61):
        mb.cylinder((x - 0.03, wy, wr), (x + 0.03, wy, wr), wr, wr, "timber", segments=12)
        mb.cylinder((x - 0.04, wy, wr), (x + 0.04, wy, wr), wr * 0.8, wr * 0.8, "plank", segments=12)
        mb.cylinder((x - 0.05, wy, wr), (x + 0.05, wy, wr), 0.08, 0.08, "iron", segments=6)
    # The load.
    pile_crate(mb, -0.2, 0.55, bed, 0.5)
    pile_crate(mb, 0.26, 0.6, bed, 0.36, math.radians(10))
    pile_crate(mb, -0.2, 0.52, bed + 0.5, 0.34, math.radians(-14))
    pile_sack(mb, -0.12, -0.2, bed, math.radians(95), 0.4)
    pile_sack(mb, -0.08, -0.12, bed + 0.2, math.radians(80), 1.9, "sack_dark")
    bx, by, br, bh = 0.24, 0.1, 0.2, 0.55
    mb.cylinder((bx, by, bed), (bx, by, bed + bh / 2), br * 0.85, br, "plank_dark", segments=8)
    mb.cylinder((bx, by, bed + bh / 2), (bx, by, bed + bh), br, br * 0.85, "plank_dark", segments=8)
    for z in (bed + bh * 0.2, bed + bh * 0.8):
        mb.cylinder((bx, by, z - 0.02), (bx, by, z + 0.02), br * 0.97, br * 0.97, "iron", segments=8)
    # The awning: four posts and a striped cloth, higher at the front.
    top_front, top_back = 1.95, 1.75
    for x in (-half, half):
        mb.cylinder((x, y0, bed), (x, y0, top_front), 0.03, 0.03, "timber", segments=5)
        mb.cylinder((x, y1, bed), (x, y1, top_back), 0.03, 0.03, "timber", segments=5)
    strips = 5
    a0, a1 = y0 - 0.12, y1 + 0.12
    for i in range(strips):
        x0 = -0.62 + 1.24 * i / strips
        x1 = -0.62 + 1.24 * (i + 1) / strips
        verts = mb.prism([(x0, a0), (x1, a0), (x1, a1), (x0, a1)], 0.0, 0.035,
                         "awning" if i % 2 == 0 else "awning_light")
        for v in verts:
            v.co.z += top_front + (top_back - top_front) * (v.co.y - y0) / (y1 - y0)
    obj = mb.to_object("cart", COLORS)
    common.export_glb(os.path.join(folder, "cart.glb"), [obj])


def wagon(folder):
    """The settlers' wagon (phase 74), made from the merchant's cart: four
    wheels, a pole toward -Y (its front), the goods a new town starts with
    under a canvas cover on hoops, open at both ends. 2.6 m long without
    the pole, 1.5 m wide over the wheels, 2.1 m tall, standing on Z = 0. In
    the game it is a building of 2 x 2 m: it sticks out a little."""
    common.reset_scene()
    mb = MeshBuilder()
    bed = 0.7             # Height of the floor of the wagon.
    y0, y1 = -1.2, 1.2    # The bed, front to back.
    half = 0.55           # Half width of the bed.
    mid = (y0 + y1) / 2
    mb.box((0, mid, bed - 0.04), (2 * half, y1 - y0, 0.08), "plank")
    for x in (-half, half):
        mb.box((x, mid, bed + 0.17), (0.05, y1 - y0, 0.34), "plank_dark")
    for y in (y0, y1):
        mb.box((0, y, bed + 0.17), (2 * half, 0.05, 0.34), "plank_dark")
    # The pole the oxen pull it by, resting on the ground.
    mb.cylinder((0, y0 + 0.2, bed - 0.14), (0, y0 - 1.1, 0.12), 0.045, 0.035, "timber", segments=5)
    mb.cylinder((-0.4, y0 - 0.95, 0.2), (0.4, y0 - 0.95, 0.2), 0.03, 0.03, "timber", segments=5)
    # Two axles: smaller wheels at the front.
    for wy, wr in ((y0 + 0.45, 0.4), (y1 - 0.5, 0.5)):
        mb.cylinder((-0.68, wy, wr), (0.68, wy, wr), 0.04, 0.04, "iron", segments=6)
        mb.box((0, wy, (bed - 0.08 + wr) / 2), (0.9, 0.1, bed - 0.08 - wr), "timber")
        for x in (-0.69, 0.69):
            mb.cylinder((x - 0.03, wy, wr), (x + 0.03, wy, wr), wr, wr, "timber", segments=12)
            mb.cylinder((x - 0.04, wy, wr), (x + 0.04, wy, wr), wr * 0.8, wr * 0.8, "plank", segments=12)
            mb.cylinder((x - 0.05, wy, wr), (x + 0.05, wy, wr), 0.08, 0.08, "iron", segments=6)
    # The load, seen through the open ends.
    pile_crate(mb, -0.22, 0.85, bed, 0.5)
    pile_crate(mb, 0.26, 0.9, bed, 0.38, math.radians(10))
    pile_crate(mb, -0.2, 0.84, bed + 0.5, 0.34, math.radians(-14))
    pile_sack(mb, -0.15, -0.85, bed, math.radians(95), 0.4)
    pile_sack(mb, 0.2, -0.8, bed, math.radians(70), 1.3, "sack_dark")
    pile_sack(mb, 0.0, -0.78, bed + 0.2, math.radians(85), 1.9)
    bx, by, br, bh = 0.25, 0.25, 0.2, 0.55
    mb.cylinder((bx, by, bed), (bx, by, bed + bh / 2), br * 0.85, br, "plank_dark", segments=8)
    mb.cylinder((bx, by, bed + bh / 2), (bx, by, bed + bh), br, br * 0.85, "plank_dark", segments=8)
    for z in (bed + bh * 0.2, bed + bh * 0.8):
        mb.cylinder((bx, by, z - 0.02), (bx, by, z + 0.02), br * 0.97, br * 0.97, "iron", segments=8)
    # The cover: an arch of canvas from side to side, in three lengths with
    # a hoop of wood showing between them and at the ends.
    base = bed + 0.34
    top = 2.1

    def arch(radius_x, height, steps=6):
        """Half an ellipse as a polygon of (x, z), counter-clockwise."""
        points = []
        for i in range(steps + 1):
            a = math.pi * i / steps
            points.append((radius_x * math.cos(a), base + height * math.sin(a)))
        return points

    def span(ya, yb, radius_x, height, mat):
        # A prism stands along Z: laid down along Y (a quarter turn about X).
        verts = mb.prism(arch(radius_x, height), 0.0, yb - ya, mat)
        for v in verts:
            x, depth, up = v.co.x, v.co.z, v.co.y
            v.co.x, v.co.y, v.co.z = x, yb - depth, up

    cover_y0, cover_y1 = y0 + 0.1, y1 - 0.1
    third = (cover_y1 - cover_y0) / 3
    for i in range(3):
        ya = cover_y0 + third * i
        span(ya + 0.03, ya + third - 0.03, half + 0.06, top - base, "canvas" if i != 1 else "canvas_light")
    for i in range(4):
        y = cover_y0 + third * i
        span(y - 0.03, y + 0.03, half + 0.09, top - base + 0.03, "timber")
    obj = mb.to_object("wagon", dict(COLORS, canvas=common.rgb(0xD8CBAA), canvas_light=common.rgb(0xE6DCC0)))
    common.export_glb(os.path.join(folder, "wagon.glb"), [obj])


def arrow_flight(folder):
    """An arrow as it flies (phase 67): lying along Y with its head toward
    -Y (the front), centered on the origin, so the game only has to turn it
    about the vertical. Bigger than life (1.2 m) to be seen from above."""
    common.reset_scene()
    mb = MeshBuilder()
    mb.cylinder((0, 0.6, 0), (0, -0.48, 0), 0.022, 0.022, "arrow_shaft", segments=5)
    mb.cylinder((0, -0.48, 0), (0, -0.62, 0), 0.05, 0.0, "arrow_head", segments=5)
    # The fletching: two fins across each other.
    mb.box((0, 0.5, 0), (0.012, 0.2, 0.13), "arrow_feather")
    mb.box((0, 0.5, 0), (0.13, 0.2, 0.012), "arrow_feather")
    obj = mb.to_object("arrow_flight", dict(COLORS, arrow_shaft=common.rgb(0xB08A5A), arrow_head=common.rgb(0x5A6068),
                                            arrow_feather=common.rgb(0xE8E4D8)))
    common.export_glb(os.path.join(folder, "arrow_flight.glb"), [obj])


def make_all(folder):
    os.makedirs(folder, exist_ok=True)
    rock(folder)
    ore_rock(folder)
    berry_bush(folder)
    herb(folder)
    house(folder)
    cloud(folder)
    variants(folder)
    piles(folder)
    cart(folder)
    wagon(folder)
    arrow_flight(folder)


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
