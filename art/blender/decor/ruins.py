"""Decorations: ruins and abandoned things.

Ancient ruins (columns, an arch, a rune circle, a giant stone head, a tower
stump, a wall), abandoned buildings (a burnt cottage, a collapsed shed) and
wrecked objects (a cart, a boat, barrels and crates, an old well).

Same conventions as buildings.py: meters, Z up, front toward -Y, standing on
Z = 0, each model inside its square footprint (2, 3, 4 or 5 m).

    blender --background --factory-startup --python art/blender/decor/ruins.py -- <output folder>
"""

import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from mathutils import Euler, Matrix, Vector  # noqa: E402

import buildings  # noqa: E402
import common  # noqa: E402
from common import MeshBuilder  # noqa: E402

buildings.COLORS.update({
    "ruin_stone": common.rgb(0x8E8C80),
    "ruin_stone_dark": common.rgb(0x6A6A60),
    "ruin_stone_light": common.rgb(0xAAA898),
    "ruin_moss": common.rgb(0x5E7A3A),
    "ruin_ground": common.rgb(0x6F6A48),
    "ruin_rune": common.rgb(0x40E8D0),
    "ruin_rune_violet": common.rgb(0xB468F4),
    "ruin_charred": common.rgb(0x2A2522),
    "ruin_soot": common.rgb(0x8C8474),
    "ruin_ash": common.rgb(0x5A5650),
    "ruin_wood_old": common.rgb(0x6E5A44),
    "ruin_wood_grey": common.rgb(0x8A7C6A),
    "ruin_shadow": common.rgb(0x25282C),
    "ruin_murk": common.rgb(0x34463A),
    "ruin_rust": common.rgb(0x6A4030),
    "ruin_bone": common.rgb(0xD8D0B8),
    "ruin_obsidian": common.rgb(0x2E2C3C),
    "ruin_canvas": common.rgb(0xA89878),
    "ruin_rock": common.rgb(0x6E6860),
    "ruin_blade": common.rgb(0x7E848C),
})

S, SD, SL = "ruin_stone", "ruin_stone_dark", "ruin_stone_light"


# --- Pieces ------------------------------------------------------------------------------


def xform(verts, matrix):
    for v in verts:
        v.co = matrix @ v.co
    return verts


def pose(center, rot=(0.0, 0.0, 0.0)):
    return Matrix.Translation(Vector(center)) @ Euler(rot).to_matrix().to_4x4()


def tbox(mb, center, size, mat, rot=(0.0, 0.0, 0.0)):
    """A box tilted by the XYZ Euler angles `rot` (radians) around its center."""
    return xform(mb.box((0, 0, 0), size, mat), pose(center, rot))


def ground(mb, size, mat="ruin_ground"):
    """A patch of trodden earth that fills the footprint (0.1 m inside the edge)."""
    mb.box((0, 0, 0.025), (size - 0.2, size - 0.2, 0.05), mat)


def rubble(mb, seed, spots, mats=(S, SD), lo=0.16, hi=0.36):
    """Loose stones at the given (x, y) spots, a few per spot."""
    rnd = random.Random(seed)
    for x, y in spots:
        for _ in range(2):
            s = rnd.uniform(lo, hi)
            ox, oy = rnd.uniform(-0.18, 0.18), rnd.uniform(-0.18, 0.18)
            tbox(mb, (x + ox, y + oy, s * 0.35), (s, s * rnd.uniform(0.7, 1.2), s * 0.8), rnd.choice(mats),
                 (rnd.uniform(-0.4, 0.4), rnd.uniform(-0.4, 0.4), rnd.uniform(0, 3.1)))


def moss(mb, x, y, z, r=0.25, mat="ruin_moss", flat=0.45):
    mb.sphere((x, y, z), r, mat, segments=6, rings=4, scale=(1, 1, flat))


def bush(mb, x, y, r=0.3):
    mb.sphere((x, y, r * 0.7), r, "leaves", segments=6, rings=4, scale=(1, 1, 0.8))
    mb.sphere((x + r * 0.6, y + r * 0.3, r * 0.5), r * 0.7, "ruin_moss", segments=6, rings=4, scale=(1, 1, 0.8))


def ring(mb, r, thick, heights, mats, z0=0.0, phase=0.0):
    """A round wall of len(heights) blocks; a height of 0 leaves a gap."""
    n = len(heights)
    width = 2 * (r + thick / 2) * math.tan(math.pi / n)
    for i, h in enumerate(heights):
        if h <= 0:
            continue
        a = phase + i * 2 * math.pi / n
        mb.box((r * math.cos(a), r * math.sin(a), z0 + h / 2), (width, thick, h), mats[i % len(mats)],
               rotation_z=a + math.pi / 2)


def column(mb, x, y, z0, drums, r=0.26, capital=False, drum_h=0.5):
    """A column of stacked drums on a square plinth. Returns its top height."""
    mb.box((x, y, z0 + 0.09), (r * 2.6, r * 2.6, 0.18), SD)
    z = z0 + 0.18
    for i in range(drums):
        ox = 0.02 if i % 2 else -0.02
        mb.cylinder((x + ox, y, z), (x + ox, y, z + drum_h), r, r * 0.95, S if i % 2 else SL, segments=8)
        z += drum_h
    if capital:
        mb.cylinder((x, y, z), (x, y, z + 0.14), r * 0.95, r * 1.35, SD, segments=8)
        mb.box((x, y, z + 0.21), (r * 3.0, r * 3.0, 0.14), SL)
        z += 0.28
    return z


def wheel(mb, r=0.45):
    """A cart wheel at the origin with its axle along Y; returns its vertices."""
    g = []
    g += mb.cylinder((0, -0.05, 0), (0, 0.05, 0), r, r, "timber", segments=12)
    g += mb.cylinder((0, -0.06, 0), (0, 0.06, 0), r * 0.8, r * 0.8, "ruin_wood_grey", segments=12)
    for k in range(4):
        a = k * math.pi / 4
        g += tbox(mb, (0, 0, 0), (r * 1.7, 0.14, 0.07), "ruin_wood_old", (0, a, 0))
    g += mb.cylinder((0, -0.11, 0), (0, 0.11, 0), 0.1, 0.1, "iron", segments=8)
    return g


def lying_barrel(mb, a, b, r=0.3, mat="ruin_wood_old"):
    a, b = Vector(a), Vector(b)
    m = (a + b) / 2
    mb.cylinder(a, m, r * 0.85, r, mat, segments=10)
    mb.cylinder(m, b, r, r * 0.85, mat, segments=10)
    for t in (0.2, 0.8):
        p = a + (b - a) * t
        d = (b - a).normalized() * 0.03
        mb.cylinder(p - d, p + d, r * 0.97, r * 0.97, "ruin_rust", segments=10)


def glyph(mb, cx, cy, z, ang, kind, mat="ruin_rune", out=0.0):
    """A rune on a vertical face whose outward normal points along `ang`."""
    nx, ny = math.cos(ang), math.sin(ang)
    tx, ty = -ny, nx
    marks = {
        0: [(0, 0, 0.05, 0.3), (0.08, 0.08, 0.14, 0.05)],
        1: [(-0.07, 0, 0.05, 0.28), (0.07, 0, 0.05, 0.28), (0, 0.0, 0.14, 0.05)],
        2: [(0, 0.1, 0.2, 0.05), (0, -0.02, 0.05, 0.22), (0, -0.14, 0.12, 0.05)],
        3: [(0, 0, 0.1, 0.1), (0, 0.16, 0.2, 0.04), (0, -0.16, 0.2, 0.04)],
    }[kind % 4]
    for u, w, su, sw in marks:
        mb.box((cx + nx * out + tx * u, cy + ny * out + ty * u, z + w), (su, 0.05, sw), mat,
               rotation_z=ang + math.pi / 2)


# --- Ancient ruins -----------------------------------------------------------------------


def rune_circle(folder):
    """A cracked stone circle with an altar and standing stones carved with glowing runes."""
    common.reset_scene()
    mb = MeshBuilder()
    ground(mb, 4)
    mb.cylinder((0, 0, 0), (0, 0, 0.18), 1.88, 1.88, SD, segments=12)
    mb.cylinder((0, 0, 0.18), (0, 0, 0.3), 1.5, 1.5, S, segments=12)
    # Cracks across the dais.
    for a, length, off in ((0.5, 1.5, 0.3), (2.3, 1.1, -0.4), (4.0, 1.3, 0.2)):
        mb.box((math.cos(a) * 0.75, math.sin(a) * 0.75, 0.3), (length, 0.06, 0.03), "ruin_shadow",
               rotation_z=a + off)
    # A ring of small runes on the floor.
    for i in range(8):
        a = i * math.pi / 4 + 0.2
        mb.box((math.cos(a) * 0.95, math.sin(a) * 0.95, 0.31), (0.18, 0.07, 0.03),
               "ruin_rune" if i % 2 else "ruin_rune_violet", rotation_z=a + (0 if i % 2 else math.pi / 2))
    # The altar.
    mb.box((0, 0, 0.6), (0.8, 0.5, 0.6), SD)
    mb.box((0, 0, 0.96), (1.05, 0.7, 0.14), SL)
    glyph(mb, 0, -0.25, 0.6, -math.pi / 2, 3, "ruin_rune_violet", out=0.01)
    mb.cylinder((0, 0, 1.03), (0, 0, 1.25), 0.02, 0.14, "ruin_rune", segments=5)
    mb.cylinder((0, 0, 1.25), (0, 0, 1.5), 0.14, 0.02, "ruin_rune", segments=5)
    # Standing stones.
    heights = (1.9, 1.5, 2.1, 0.7, 1.7, 1.3)
    for i, h in enumerate(heights):
        a = math.radians(-90 - 30 + i * 60)
        x, y = math.cos(a) * 1.5, math.sin(a) * 1.5
        mb.box((x, y, 0.18 + h / 2), (0.52, 0.3, h), S if i % 2 else SL, rotation_z=a + math.pi / 2)
        if h > 1.0:
            mb.box((x, y, 0.18 + h + 0.06), (0.4, 0.24, 0.14), SD, rotation_z=a + math.pi / 2 + 0.2)
            mat = "ruin_rune" if i % 2 else "ruin_rune_violet"
            for side in (1, -1):
                glyph(mb, x, y, 0.18 + h * 0.68, a if side > 0 else a + math.pi, i, mat, out=0.14)
                glyph(mb, x, y, 0.18 + h * 0.32, a if side > 0 else a + math.pi, i + 1, mat, out=0.14)
        else:
            # The broken one: its top lies beside it.
            tbox(mb, (x * 0.72, y * 0.72 + 0.1, 0.45), (0.5, 0.3, 0.9), SL, (1.35, 0.0, a + 0.4))
    moss(mb, 1.5, -0.9, 0.18, 0.3)
    moss(mb, -1.1, 1.3, 0.18, 0.28)
    moss(mb, -0.3, 0.45, 0.3, 0.2)
    buildings.export(folder, "decor_rune_circle", mb)


def stone_head(folder):
    """A giant stone head, half buried and leaning."""
    common.reset_scene()
    mb = MeshBuilder()
    ground(mb, 3)
    g = []
    g += mb.sphere((0, 0, 0), 1.0, S, segments=10, rings=7, scale=(0.82, 0.9, 1.2))
    g += mb.cylinder((0, 0.02, 0.62), (0, 0.02, 1.0), 0.86, 0.8, SD, segments=10)       # Headdress.
    g += mb.cylinder((0, 0.02, 1.0), (0, 0.02, 1.22), 0.62, 0.5, SL, segments=10)
    g += mb.box((0, -0.74, 0.42), (1.2, 0.3, 0.2), SD)                                    # Brow.
    g += tbox(mb, (0, -0.86, 0.08), (0.26, 0.32, 0.62), SL, (-0.2, 0, 0))                 # Nose.
    for side in (-1, 1):
        g += mb.box((side * 0.34, -0.76, 0.24), (0.3, 0.14, 0.13), "ruin_shadow")         # Eyes.
        g += mb.box((side * 0.34, -0.8, 0.24), (0.1, 0.1, 0.07), "ruin_rune")
        g += mb.box((side * 0.82, -0.05, 0.1), (0.16, 0.34, 0.7), SD)                     # Ears.
    g += mb.box((0, -0.8, -0.42), (0.52, 0.14, 0.08), SD)                                 # Mouth.
    g += mb.box((0, -0.78, -0.52), (0.4, 0.14, 0.08), SL)
    g += mb.box((0.25, -0.82, 0.62), (0.05, 0.1, 0.36), "ruin_shadow")                    # A crack.
    xform(g, pose((0.05, 0.1, 0.6), (-0.38, 0.3, 0.2)))
    moss(mb, 0.55, 0.75, 1.3, 0.3)
    moss(mb, -0.75, 0.5, 0.5, 0.3)
    # The earth it sinks into.
    mb.sphere((0.05, 0.1, 0.0), 1.2, "ruin_ground", segments=8, rings=4, scale=(1, 1, 0.22))
    rubble(mb, 5, [(-1.05, -0.9), (1.05, -1.0), (-1.1, 0.9)])
    bush(mb, 1.0, 1.0, 0.28)
    bush(mb, -1.05, -0.2, 0.22)
    buildings.export(folder, "decor_stone_head", mb)


def broken_columns(folder):
    """A temple platform with columns broken at different heights."""
    common.reset_scene()
    mb = MeshBuilder()
    mb.box((0, 0, 0.1), (2.8, 2.8, 0.2), SD)
    mb.box((0, 0, 0.27), (2.4, 2.4, 0.14), S)
    mb.box((0.2, -0.3, 0.34), (1.4, 0.05, 0.02), "ruin_shadow", rotation_z=0.5)
    z0 = 0.34
    top = column(mb, -0.8, 0.8, z0, 5, capital=True)
    column(mb, 0.8, 0.8, z0, 4, capital=True)
    column(mb, -0.8, -0.8, z0, 2)
    column(mb, 0.8, -0.8, z0, 1)
    # What is left of the beam over the two back columns.
    mb.box((-0.55, 0.8, top + 0.15), (1.2, 0.5, 0.3), SD)
    tbox(mb, (0.95, 0.1, 0.48), (0.9, 0.44, 0.28), SD, (0.0, -0.12, 1.45))
    # Jagged tops of the broken ones.
    tbox(mb, (-0.8, -0.8, 1.56), (0.3, 0.3, 0.2), SL, (0.5, 0.3, 0.4))
    tbox(mb, (0.8, -0.8, 1.05), (0.28, 0.25, 0.16), S, (0.3, -0.5, 0.2))
    # Fallen drums.
    mb.cylinder((-0.3, -0.35, 0.6), (0.2, -0.1, 0.6), 0.26, 0.25, SL, segments=8)
    mb.cylinder((-1.0, -0.2, 0.6), (-0.9, 0.3, 0.6), 0.25, 0.24, S, segments=8)
    mb.cylinder((0.1, -1.05, 0.46), (0.1, -1.05, 0.9), 0.26, 0.25, S, segments=8)
    tbox(mb, (-0.15, 0.2, 0.45), (0.5, 0.5, 0.14), SL, (0.12, 0.1, 0.6))
    moss(mb, -0.8, 0.8, top + 0.3, 0.28)
    moss(mb, 1.1, -0.2, 0.34, 0.22)
    moss(mb, -1.15, -0.2, 0.2, 0.22)
    buildings.export(folder, "decor_broken_columns", mb)


def fallen_arch(folder):
    """A stone arch with half of its span on the ground."""
    common.reset_scene()
    mb = MeshBuilder()
    ground(mb, 4)
    mb.box((0, 0.3, 0.1), (3.7, 1.5, 0.2), SD)
    for x, h in ((-1.3, 1.9), (1.3, 1.9)):
        mb.box((x, 0.3, 0.3), (0.9, 0.9, 0.2), S)
        mb.box((x, 0.3, 0.4 + h / 2), (0.66, 0.66, h), SL if x < 0 else S)
        mb.box((x, 0.3, 0.4 + h * 0.5), (0.7, 0.7, 0.08), SD)
        mb.box((x, 0.3, 0.4 + h + 0.08), (0.86, 0.86, 0.16), SD)
    cz, radius = 2.46, 1.3
    standing = (172, 152, 132, 112, 12)
    for i, deg in enumerate(standing):
        t = math.radians(deg)
        tbox(mb, (radius * math.cos(t), 0.3, cz + radius * math.sin(t) + 0.1), (0.5, 0.62, 0.5),
             S if i % 2 else SL, (0, -(t + math.pi / 2), 0))
    # The fallen stones of the span.
    fallen = [((0.35, -0.75, 0.24), (0.2, 0.3, 0.5)), ((0.95, -0.35, 0.44), (0.5, 0.2, 1.2)),
              ((0.2, 0.25, 0.42), (0.1, -0.35, 0.2)), ((-0.35, -1.2, 0.24), (0.0, 0.1, 2.0)),
              ((1.1, -1.3, 0.26), (0.25, 0.0, 0.9)), ((0.75, 0.2, 0.75), (0.7, 0.3, 0.4))]
    for i, (c, r) in enumerate(fallen):
        tbox(mb, c, (0.5, 0.62, 0.46), S if i % 2 else SL, r)
    rubble(mb, 11, [(-0.9, -1.2), (1.45, -0.7), (-1.4, -1.35)])
    moss(mb, -1.3, 0.55, 2.46, 0.3)
    moss(mb, 0.4, -0.3, 0.5, 0.25)
    bush(mb, -1.5, 1.45, 0.3)
    bush(mb, 1.55, 1.45, 0.26)
    buildings.export(folder, "decor_fallen_arch", mb)


def tower_stump(folder):
    """The stump of a round tower, its wall spiralling down to rubble."""
    common.reset_scene()
    mb = MeshBuilder()
    ground(mb, 4)
    heights = [3.0, 3.3, 2.9, 2.3, 1.7, 1.2, 0.8, 0.5, 0.9, 0.0, 1.9, 2.5]
    ring(mb, 1.62, 0.4, heights, (S, SL))
    ring(mb, 1.64, 0.44, [min(h, 0.4) for h in heights], (SD,))
    ring(mb, 1.64, 0.44, [0.16 if h > 1.9 else 0 for h in heights], (SD,), z0=1.7)
    mb.cylinder((0, 0, 0), (0, 0, 0.12), 1.5, 1.5, "ruin_ash", segments=12)
    # Door jambs and a threshold.
    for side in (-1, 1):
        mb.box((side * 0.5, -1.62, 0.7 + side * 0.25), (0.2, 0.46, 1.4 + side * 0.5), SD)
    mb.box((0, -1.62, 0.08), (0.9, 0.5, 0.16), SL)
    # Arrow slits on the tall side.
    for i in (0, 2):
        a = i * math.pi / 6
        mb.box((1.83 * math.cos(a), 1.83 * math.sin(a), 2.2), (0.14, 0.06, 0.6), "ruin_shadow",
               rotation_z=a + math.pi / 2)
    # A broken floor beam and rubble inside and out.
    mb.cylinder((-0.9, 0.9, 0.2), (1.2, 0.7, 1.75), 0.09, 0.09, "ruin_wood_old", segments=6)
    mb.cylinder((-1.0, -0.4, 0.2), (0.6, 0.2, 0.25), 0.09, 0.09, "ruin_wood_old", segments=6)
    rubble(mb, 21, [(-0.4, 0.3), (0.5, -0.5), (-0.9, -0.2)], lo=0.2, hi=0.4)
    rubble(mb, 22, [(-1.45, -1.45), (-1.45, 1.45), (1.45, -1.45)], lo=0.18, hi=0.3)
    moss(mb, 1.4, 0.8, 3.3, 0.3)
    moss(mb, -1.4, 0.8, 1.2, 0.3)
    moss(mb, -1.2, -1.1, 0.5, 0.3)
    bush(mb, 1.55, 1.55, 0.26)
    buildings.export(folder, "decor_tower_stump", mb)


def ruined_wall(folder):
    """The corner of an old stone wall with a window."""
    common.reset_scene()
    mb = MeshBuilder()
    ground(mb, 3)
    y, t = 0.6, 0.42
    mb.box((0, y, 0.1), (2.7, t + 0.12, 0.2), SD)
    mb.box((-1.0, y, 1.5), (0.6, t, 2.6), S)                      # Left pier.
    mb.box((-0.35, y, 0.65), (0.7, t, 0.9), SL)                   # Under the window.
    mb.box((-0.35, y, 1.13), (0.8, t + 0.1, 0.1), SD)             # Sill.
    mb.box((-0.35, y, 2.35), (0.7, t, 0.5), SL)                   # Over the window.
    tbox(mb, (-0.52, y, 2.02), (0.3, t - 0.04, 0.2), SD, (0, -0.6, 0))
    tbox(mb, (-0.18, y, 2.02), (0.3, t - 0.04, 0.2), SD, (0, 0.6, 0))
    mb.box((0.3, y, 1.35), (0.6, t, 2.3), S)                      # Right pier.
    mb.box((0.8, y, 0.9), (0.42, t, 1.4), SL)
    mb.box((1.15, y, 0.5), (0.3, t, 0.6), S)
    # Broken top: odd blocks.
    tbox(mb, (-1.05, y, 2.88), (0.4, t, 0.24), SL, (0, 0.15, 0))
    mb.box((-0.5, y, 2.7), (0.36, t, 0.2), S)
    mb.box((0.2, y, 2.6), (0.34, t, 0.2), SL)
    mb.box((0.72, y, 1.7), (0.24, t, 0.2), S)
    # Courses.
    for z in (0.75, 1.5, 2.2):
        mb.box((-1.0, y, z), (0.64, t + 0.04, 0.05), SD)
        if z < 2.3:
            mb.box((0.3, y, z), (0.64, t + 0.04, 0.05), SD)
    # The side wall, almost gone.
    mb.box((-1.1, -0.1, 0.6), (t, 1.0, 1.0), SL)
    mb.box((-1.1, -0.85, 0.3), (t, 0.6, 0.4), S)
    mb.box((-1.1, 0.1, 1.2), (t, 0.5, 0.26), S)
    # Ivy up the left pier.
    for x, z, w, h in ((-1.05, 0.9, 0.4, 1.5), (-0.85, 1.9, 0.26, 0.8), (-1.15, 2.2, 0.2, 0.5)):
        mb.box((x, y - t / 2 - 0.03, z), (w, 0.06, h), "ruin_moss")
    moss(mb, 0.3, y, 2.5, 0.25)
    rubble(mb, 31, [(0.3, -0.2), (0.9, 0.0), (-0.3, -0.7), (0.9, -1.0)])
    tbox(mb, (0.1, -0.55, 0.2), (0.6, 0.4, 0.3), SL, (0.2, 0.1, 0.5))
    bush(mb, 1.0, 1.15, 0.24)
    bush(mb, -0.2, 1.15, 0.2)
    buildings.export(folder, "decor_ruined_wall", mb)


# --- Abandoned buildings -----------------------------------------------------------------


def burnt_wall(mb, x0, y0, x1, y1, h, z0=0.3, t=0.18):
    """A stretch of sooty wall with a charred top edge."""
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    length = math.hypot(x1 - x0, y1 - y0)
    a = math.atan2(y1 - y0, x1 - x0)
    mb.box((cx, cy, z0 + h / 2), (length, t, h), "ruin_soot", rotation_z=a)
    mb.box((cx, cy, z0 + h), (length, t + 0.02, 0.14), "ruin_charred", rotation_z=a)
    mb.box((cx, cy, z0 + 0.1), (length, t + 0.04, 0.12), "ruin_charred", rotation_z=a)


def burnt_cottage(folder):
    """A cottage after a fire: no roof, charred timbers, the chimney still standing."""
    common.reset_scene()
    mb = MeshBuilder()
    ground(mb, 5)
    w, d = 4.2, 3.6
    x0, x1, y0, y1 = -w / 2, w / 2, -d / 2 + 0.2, d / 2 + 0.2
    cy = (y0 + y1) / 2
    mb.box((0, cy, 0.15), (w + 0.2, d + 0.2, 0.3), "stone")
    mb.box((0, cy, 0.31), (w - 0.3, d - 0.3, 0.04), "ruin_ash")
    # Walls, clockwise from the front left, in stretches of different heights.
    burnt_wall(mb, x0, y0, -0.5, y0, 1.5)
    burnt_wall(mb, 0.5, y0, 1.3, y0, 1.9)
    burnt_wall(mb, 1.3, y0, x1, y0, 0.8)
    burnt_wall(mb, x0, y0, x0, cy, 2.0)
    burnt_wall(mb, x0, cy, x0, y1, 2.2)
    burnt_wall(mb, x0, y1, -0.6, y1, 2.2)
    burnt_wall(mb, -0.6, y1, 0.6, y1, 1.3)
    burnt_wall(mb, 0.6, y1, x1, y1, 1.8)
    burnt_wall(mb, x1, y1, x1, cy, 1.0)
    burnt_wall(mb, x1, cy, x1, y0, 0.5)
    # A window hole in the front.
    mb.box((-1.3, y0 - 0.02, 1.25), (0.6, 0.2, 0.5), "ruin_shadow")
    # Charred posts.
    for x, y, h, lean in ((x0, y0, 2.6, 0.0), (x1, y0, 1.1, 0.12), (x0, y1, 2.7, 0.0), (x1, y1, 2.3, -0.08),
                          (-0.5, y0, 2.1, 0.0), (0.5, y0, 2.2, 0.05)):
        tbox(mb, (x, y, 0.3 + h / 2), (0.16, 0.16, h), "ruin_charred", (lean, lean, 0))
    mb.box((0, y0, 2.3), (1.2, 0.16, 0.14), "ruin_charred")                         # Door lintel.
    # The left gable: two rafters still up.
    rise, half = 1.5, d / 2
    slope = math.atan2(rise, half)
    length = math.hypot(rise, half)
    for side in (-1, 1):
        tbox(mb, (x0, cy + side * half / 2, 2.5 + rise / 2), (0.14, length, 0.14), "ruin_charred",
             (-side * slope, 0, 0))
    mb.box((x0, cy, 2.5), (0.14, d, 0.14), "ruin_charred")
    # Fallen beams inside.
    mb.cylinder((x0 + 0.1, cy + 0.3, 2.4), (1.2, cy - 0.4, 0.45), 0.09, 0.09, "ruin_charred", segments=6)
    mb.cylinder((-1.2, y1 - 0.3, 0.42), (1.5, y0 + 0.5, 0.42), 0.09, 0.09, "ruin_charred", segments=6)
    mb.cylinder((-0.2, y1 - 0.1, 1.5), (0.3, cy - 0.3, 0.4), 0.08, 0.08, "ruin_charred", segments=6)
    tbox(mb, (0.9, cy + 0.6, 0.42), (1.3, 0.9, 0.08), "roof_dark", (0.12, -0.1, 0.4))   # Fallen roof.
    tbox(mb, (-0.8, cy - 0.6, 0.4), (0.9, 0.7, 0.08), "ruin_charred", (-0.1, 0.1, -0.3))
    # The chimney.
    mb.box((1.3, y1 - 0.25, 1.9), (0.7, 0.6, 3.2), "stone")
    mb.box((1.3, y1 - 0.25, 3.55), (0.82, 0.72, 0.12), "stone_dark")
    mb.box((1.3, y1 - 0.58, 0.75), (0.5, 0.1, 0.6), "ruin_shadow")
    mb.box((1.3, y1 - 0.25, 2.6), (0.74, 0.64, 0.5), "ruin_charred")
    rubble(mb, 41, [(1.7, cy - 0.5), (0.2, cy + 0.9)], mats=("ruin_ash", "ruin_charred"), lo=0.2, hi=0.4)
    rubble(mb, 42, [(2.0, -1.95), (-2.0, -1.95)], mats=("stone", "stone_dark"))
    bush(mb, -1.6, -2.05, 0.26)
    bush(mb, 2.1, 0.4, 0.22)
    buildings.export(folder, "decor_burnt_cottage", mb)


def collapsed_shed(folder):
    """A shed whose roof came down on one side."""
    common.reset_scene()
    mb = MeshBuilder()
    ground(mb, 3)
    # Back posts and wall still up, front posts snapped.
    for x in (-1.2, 1.2):
        mb.box((x, 1.15, 0.95), (0.14, 0.14, 1.9), "timber")
    tbox(mb, (-1.2, -1.0, 0.35), (0.14, 0.14, 0.75), "timber", (0.25, 0.2, 0))
    tbox(mb, (1.15, -1.05, 0.25), (0.14, 0.14, 0.55), "timber", (-0.2, -0.3, 0))
    for i in range(6):
        if i == 3:
            continue
        x = -1.0 + i * 0.4
        h = (1.6, 1.7, 1.3, 0, 1.75, 1.5)[i]
        mb.box((x, 1.2, h / 2 + 0.05), (0.36, 0.05, h), "ruin_wood_grey" if i % 2 else "ruin_wood_old")
    mb.box((0, 1.15, 1.8), (2.5, 0.1, 0.1), "timber")
    # The roof, hinged down from the back beam to the ground.
    a = math.radians(37)
    planks = []
    for i in range(7):
        if i == 4:
            continue
        x = -1.14 + i * 0.38
        length = (2.7, 2.6, 2.7, 2.3, 0, 2.7, 2.5)[i]
        planks += mb.box((x, -(2.7 - length) / 2 * (1 if i % 2 else -1), 0), (0.36, length, 0.06),
                         "ruin_wood_old" if i % 2 else "ruin_wood_grey")
    planks += mb.box((0, 0.6, -0.07), (2.5, 0.1, 0.1), "timber")
    planks += mb.box((0, -0.7, -0.07), (2.5, 0.1, 0.1), "timber")
    planks += mb.box((-0.8, 0.2, 0.05), (0.7, 0.9, 0.05), "thatch_dark")
    planks += mb.box((0.9, -0.5, 0.05), (0.6, 0.8, 0.05), "thatch")
    xform(planks, pose((0, 0.05, 1.0), (a, 0.06, 0)))
    # What was kept inside.
    buildings.crate(mb, 0.45, 0.6, s=0.5, mat="ruin_wood_grey")
    tbox(mb, (0.5, -1.08, 0.1), (1.1, 0.2, 0.05), "ruin_wood_old", (0, 0, 0.3))
    tbox(mb, (-0.6, -1.15, 0.1), (0.9, 0.18, 0.05), "ruin_wood_grey", (0, 0, -0.2))
    moss(mb, -0.6, -0.3, 0.86, 0.28)
    bush(mb, -1.15, 0.3, 0.2)
    bush(mb, 1.15, 0.2, 0.22)
    buildings.export(folder, "decor_collapsed_shed", mb)


# --- Wrecked objects ---------------------------------------------------------------------


def wrecked_cart(folder):
    """A cart down on one side, its wheel broken on the ground."""
    common.reset_scene()
    mb = MeshBuilder()
    ground(mb, 2)
    g = []
    g += mb.box((0, 0, 0), (1.3, 0.8, 0.08), "ruin_wood_grey")
    for side in (-1, 1):
        g += mb.box((0, side * 0.4, 0.2), (1.3, 0.06, 0.14), "ruin_wood_old")
        g += mb.box((0, side * 0.4, 0.38), (1.3, 0.06, 0.1), "ruin_wood_grey")
        for x in (-0.6, 0.0, 0.6):
            g += mb.box((x, side * 0.43, 0.22), (0.07, 0.05, 0.5), "timber")
    g += mb.box((0.65, 0, 0.22), (0.06, 0.8, 0.4), "ruin_wood_old")
    g += tbox(mb, (-0.62, 0.15, 0.3), (0.06, 0.4, 0.3), "ruin_wood_grey", (0.3, 0, 0))    # Broken tailboard.
    g += mb.cylinder((0, -0.6, -0.12), (0, 0.6, -0.12), 0.05, 0.05, "timber", segments=6)
    g += xform(wheel(mb, 0.42), pose((0, 0.55, -0.12)))
    for side in (-1, 1):
        g += mb.cylinder((0.6, side * 0.3, -0.04), (1.05, side * 0.26, -0.1), 0.035, 0.035, "timber", segments=5)
    g += mb.box((0.2, 0.1, 0.1), (0.4, 0.35, 0.14), "hay")
    xform(g, pose((-0.2, 0.12, 0.36), (math.radians(22), 0, 0.1)))
    # The broken wheel: a half on the ground, a piece leaning on the cart.
    half = [(0.4 * math.cos(math.radians(k * 30)), 0.4 * math.sin(math.radians(k * 30))) for k in range(7)]
    piece = mb.prism(half, 0.0, 0.08, "timber")
    piece += mb.prism([(x * 0.78, y * 0.78) for x, y in half], -0.01, 0.09, "ruin_wood_grey")
    xform(piece, pose((0.25, -0.7, 0.06), (0.0, 0.0, 0.3)))
    tbox(mb, (-0.45, -0.62, 0.2), (0.5, 0.08, 0.1), "timber", (0, 0.5, 0.3))
    tbox(mb, (-0.75, -0.3, 0.08), (0.4, 0.07, 0.06), "ruin_wood_old", (0, 0, 1.2))
    moss(mb, 0.72, -0.45, 0.05, 0.14)
    bush(mb, -0.72, 0.75, 0.14)
    buildings.export(folder, "decor_wrecked_cart", mb)


def wrecked_boat(folder):
    """A boat left overturned on land, with a hole in its hull."""
    common.reset_scene()
    mb = MeshBuilder()
    ground(mb, 3)
    xs = [-1.38, -1.2, -0.95, -0.6, -0.2, 0.25, 0.7, 1.05, 1.25]
    ws = [0.0, 0.14, 0.32, 0.5, 0.62, 0.66, 0.6, 0.5, 0.4]
    ks = [0.5, 0.6, 0.68, 0.76, 0.8, 0.8, 0.77, 0.72, 0.66]
    rows = []
    for x, w, k in zip(xs, ws, ks):
        w = max(w, 0.015)
        rows.append([mb.bm.verts.new(p) for p in
                     ((x, -w, 0), (x, -w * 0.94, k * 0.36), (x, -w * 0.62, k * 0.76), (x, 0, k),
                      (x, w * 0.62, k * 0.76), (x, w * 0.94, k * 0.36), (x, w, 0))])
    for i in range(len(rows) - 1):
        a, b = rows[i], rows[i + 1]
        for j in range(6):
            mb.bm.faces.new((a[j], a[j + 1], b[j + 1], b[j]))
        mb.bm.faces.new((a[6], a[0], b[0], b[6]))
    mb.bm.faces.new(rows[0])
    mb.bm.faces.new(list(reversed(rows[-1])))
    g = mb._finish([v for row in rows for v in row], "ruin_wood_grey", None)
    # Keel, strakes, the transom and the hole.
    g += mb.box((-0.02, 0, 0.76), (2.5, 0.07, 0.12), "timber")
    for side in (-1, 1):
        g += mb.box((0.3, side * 0.63, 0.04), (1.2, 0.06, 0.1), "ruin_wood_old")
    g += mb.box((1.26, 0, 0.3), (0.05, 0.6, 0.56), "ruin_wood_old")
    g += tbox(mb, (0.25, -0.3, 0.66), (0.62, 0.36, 0.05), "ruin_shadow", (0.5, 0, 0))
    for x in (0.1, 0.38):
        g += tbox(mb, (x, -0.3, 0.675), (0.06, 0.42, 0.05), "ruin_wood_old", (0.5, 0, 0))    # Ribs showing.
    g += tbox(mb, (0.6, -0.34, 0.65), (0.3, 0.07, 0.05), "ruin_wood_old", (0.5, 0, 0.5))
    # Seams between the planks.
    for side in (-1, 1):
        g += tbox(mb, (-0.05, side * 0.3, 0.635), (1.9, 0.03, 0.03), "ruin_wood_old", (-side * 0.5, 0, 0))
        g += mb.box((0.35, side * 0.6, 0.3), (1.3, 0.03, 0.03), "ruin_wood_old")
    xform(g, pose((0, 0.3, 0.14), (math.radians(-11), 0, math.radians(20))))
    # Propped on a rock; an oar and planks in the grass.
    tbox(mb, (0.75, -0.3, 0.14), (0.4, 0.34, 0.3), "stone", (0.2, 0.1, 0.5))
    tbox(mb, (-0.75, -0.8, 0.12), (0.32, 0.28, 0.26), "stone_dark", (0.1, 0.3, 0.2))
    mb.cylinder((-1.1, -1.2, 0.08), (0.7, -1.1, 0.08), 0.03, 0.03, "wood", segments=5)
    tbox(mb, (0.95, -1.08, 0.08), (0.5, 0.16, 0.03), "wood", (0, 0, 0.05))
    tbox(mb, (0.9, 1.05, 0.08), (0.7, 0.14, 0.04), "ruin_wood_old", (0, 0, -0.4))
    moss(mb, -0.35, 0.3, 0.92, 0.22)
    bush(mb, -1.1, 1.05, 0.22)
    bush(mb, 1.15, -0.4, 0.16)
    buildings.export(folder, "decor_wrecked_boat", mb)


def broken_barrels(folder):
    """Barrels and crates left to rot."""
    common.reset_scene()
    mb = MeshBuilder()
    ground(mb, 2)
    buildings.barrel(mb, -0.5, 0.5, h=0.8, r=0.3, mat="ruin_wood_old")
    mb.cylinder((-0.5, 0.5, 0.78), (-0.5, 0.5, 0.81), 0.2, 0.2, "ruin_shadow", segments=10)
    lying_barrel(mb, (-0.1, -0.55, 0.27), (0.6, -0.3, 0.27), r=0.28)
    mb.cylinder((-0.11, -0.553, 0.27), (-0.09, -0.547, 0.27), 0.19, 0.19, "ruin_shadow", segments=10)
    # A sound crate, a crushed one and loose staves.
    buildings.crate(mb, 0.45, 0.45, s=0.55, mat="ruin_wood_grey")
    for z in (0.15, 0.4):
        mb.box((0.45, 0.45, z), (0.58, 0.58, 0.05), "ruin_wood_old")
    tbox(mb, (0.3, 0.5, 0.72), (0.4, 0.4, 0.36), "ruin_wood_old", (0.25, 0.2, 0.5))
    tbox(mb, (-0.6, -0.45, 0.14), (0.5, 0.45, 0.05), "ruin_wood_grey", (0.3, 0.1, 0.3))
    tbox(mb, (-0.7, -0.6, 0.16), (0.05, 0.45, 0.3), "ruin_wood_grey", (0.1, -0.5, 0.3))
    tbox(mb, (-0.35, -0.75, 0.08), (0.45, 0.08, 0.04), "ruin_wood_old", (0, 0, -0.3))
    tbox(mb, (0.0, 0.05, 0.08), (0.4, 0.07, 0.04), "ruin_wood_old", (0, 0, 0.9))
    mb.cylinder((0.72, -0.72, 0.05), (0.72, -0.72, 0.09), 0.14, 0.14, "ruin_rust", segments=8)
    moss(mb, 0.45, 0.2, 0.1, 0.16)
    moss(mb, -0.5, 0.72, 0.3, 0.14)
    bush(mb, -0.05, 0.74, 0.12)
    buildings.export(folder, "decor_broken_barrels", mb)


def old_well(folder):
    """A well nobody draws from any more: broken rim, fallen beam, weeds."""
    common.reset_scene()
    mb = MeshBuilder()
    ground(mb, 2)
    heights = [0.8, 0.75, 0.8, 0.5, 0.3, 0.45, 0.8, 0.7, 0.8, 0.6]
    ring(mb, 0.6, 0.22, heights, ("stone", "stone_dark", S))
    mb.cylinder((0, 0, 0), (0, 0, 0.25), 0.55, 0.55, "ruin_murk", segments=10)
    mb.cylinder((0, 0, 0), (0, 0, 0.12), 0.8, 0.8, "stone_dark", segments=10)
    # One post leans, the other is a stump; the beam lies across the rim.
    tbox(mb, (-0.72, 0.05, 0.85), (0.11, 0.11, 1.7), "ruin_wood_old", (0.0, -0.14, 0))
    mb.box((0.72, 0.05, 0.4), (0.11, 0.11, 0.8), "ruin_wood_old")
    mb.cylinder((-0.6, 0.1, 1.5), (0.7, -0.35, 0.72), 0.06, 0.06, "ruin_wood_grey", segments=6)
    mb.box((-0.3, 0.0, 1.0), (0.02, 0.02, 0.6), "wood")
    # Fallen rim stones, weeds and ivy.
    rubble(mb, 61, [(0.55, -0.72), (0.8, -0.35)], mats=("stone", "stone_dark"), lo=0.14, hi=0.24)
    for a in (2.2, 3.4, 5.4):
        mb.box((0.72 * math.cos(a), 0.72 * math.sin(a), 0.4), (0.3, 0.05, 0.6), "ruin_moss",
               rotation_z=a + math.pi / 2)
    moss(mb, 0.1, 0.62, 0.8, 0.2)
    moss(mb, -0.2, -0.1, 0.25, 0.22, flat=0.2)
    bush(mb, -0.7, -0.7, 0.16)
    bush(mb, 0.65, 0.72, 0.14)
    buildings.export(folder, "decor_old_well", mb)


# --- More ruins --------------------------------------------------------------------------


def portal_gate(folder):
    """A ruined temple gate whose inner frame still glows."""
    common.reset_scene()
    mb = MeshBuilder()
    ground(mb, 4)
    mb.box((0, 0.1, 0.1), (3.7, 2.2, 0.2), SD)
    mb.box((0, 0.3, 0.3), (3.2, 1.5, 0.2), S)
    for x, h in ((-1.15, 3.0), (1.15, 2.1)):
        mb.box((x, 0.3, 0.4 + h / 2), (0.8, 0.9, h), SL if x < 0 else S)
        mb.box((x, 0.3, 0.55), (0.9, 1.0, 0.3), SD)
        mb.box((x, 0.3, 0.4 + h * 0.62), (0.84, 0.94, 0.1), SD)
        side = 1 if x < 0 else -1
        mb.box((x + side * 0.41, 0.3, 0.4 + h / 2), (0.06, 0.5, h), "ruin_rune_violet")
        for k, z in enumerate((1.2, 1.75)):
            glyph(mb, x, 0.3, z, -math.pi / 2, k + (0 if x < 0 else 2), "ruin_rune", out=0.44)
    mb.box((-1.15, 0.3, 3.48), (0.96, 1.0, 0.16), SD)
    mb.box((-0.5, 0.3, 3.8), (2.1, 0.9, 0.5), S)                               # What is left of the lintel.
    mb.box((-0.2, 0.3, 3.53), (1.0, 0.5, 0.06), "ruin_rune_violet")
    mb.box((0, 0.3, 0.41), (1.5, 0.5, 0.03), "ruin_rune_violet")
    tbox(mb, (1.15, 0.3, 2.6), (0.6, 0.7, 0.3), SL, (0.2, 0.25, 0.3))
    tbox(mb, (0.9, -1.2, 0.3), (1.1, 0.8, 0.45), S, (0.15, -0.2, 0.5))         # The fallen half.
    tbox(mb, (0.95, -1.2, 0.56), (0.5, 0.3, 0.05), "ruin_rune_violet", (0.15, -0.2, 0.5))
    rubble(mb, 71, [(-1.3, -1.3), (0.0, -1.3), (1.5, -0.3)])
    moss(mb, -0.6, 0.3, 4.05, 0.3)
    moss(mb, 1.2, 0.5, 2.75, 0.25)
    bush(mb, -1.5, 1.5, 0.26)
    bush(mb, 1.55, 1.45, 0.24)
    buildings.export(folder, "decor_portal_gate", mb)


def monolith(folder):
    """A dark monolith with glowing signs; shards of it hang in the air."""
    common.reset_scene()
    mb = MeshBuilder()
    ground(mb, 3)
    mb.cylinder((0, 0, 0), (0, 0, 0.16), 1.3, 1.3, SD, segments=8)
    mb.cylinder((0, 0, 0.16), (0, 0, 0.28), 0.9, 0.9, S, segments=8)
    for i in range(8):
        a = i * math.pi / 4 + 0.39
        mb.box((1.08 * math.cos(a), 1.08 * math.sin(a), 0.17), (0.2, 0.07, 0.03),
               "ruin_rune" if i % 2 else "ruin_rune_violet", rotation_z=a)
    mb.cylinder((0, 0, 0.28), (0, 0, 2.9), 0.55, 0.36, "ruin_obsidian", segments=4)
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        for j, z in enumerate((0.9, 1.5, 2.1)):
            r = (0.55 - 0.19 * (z - 0.28) / 2.62) * 0.707
            glyph(mb, 0, 0, z, a, k + j, "ruin_rune" if (k + j) % 2 else "ruin_rune_violet", out=r - 0.01)
    # The broken top and the shards that never fell.
    rnd = random.Random(7)
    tbox(mb, (0.05, 0.0, 3.0), (0.4, 0.4, 0.3), "ruin_obsidian", (0.3, 0.2, 0.8))
    for i in range(9):
        a = i * 2.4
        r = 0.25 + 0.1 * (i % 4) + (0.5 if i > 5 else 0)
        z = 3.3 + 0.12 * i if i <= 5 else 1.2 + 0.5 * (i - 6)
        s = rnd.uniform(0.14, 0.3)
        tbox(mb, (r * math.cos(a), r * math.sin(a), z), (s, s * 0.6, s * 1.4),
             "ruin_rune" if i in (2, 7) else "ruin_obsidian",
             (rnd.uniform(-0.8, 0.8), rnd.uniform(-0.8, 0.8), rnd.uniform(0, 3)))
    tbox(mb, (0.8, -0.7, 0.3), (0.4, 0.3, 0.3), "ruin_obsidian", (0.4, 0.3, 0.2))
    moss(mb, -0.9, -0.8, 0.16, 0.25)
    moss(mb, 0.7, 0.9, 0.16, 0.22)
    buildings.export(folder, "decor_monolith", mb)


def giant_sword(folder):
    """A giant's sword driven into the earth, rusted, its guard broken."""
    common.reset_scene()
    mb = MeshBuilder()
    ground(mb, 2)
    mb.sphere((0, 0, 0), 0.75, "ruin_ground", segments=8, rings=4, scale=(1, 1, 0.3))
    g = []
    g += mb.box((0, 0, 1.1), (0.4, 0.08, 2.2), "ruin_blade")
    g += mb.box((0, 0, 1.15), (0.1, 0.11, 2.0), "iron")
    for x, z, h in ((-0.15, 0.6, 0.4), (0.14, 1.3, 0.5), (-0.12, 1.85, 0.3)):
        g += mb.box((x, 0, z), (0.12, 0.1, h), "ruin_rust")
    g += mb.box((-0.12, 0, 2.26), (0.7, 0.18, 0.14), "iron")                    # One arm of the guard is gone.
    g += mb.box((-0.45, 0, 2.26), (0.1, 0.22, 0.22), "ruin_rust")
    g += mb.cylinder((0, 0, 2.33), (0, 0, 2.8), 0.07, 0.06, "timber", segments=6)
    for z in (2.45, 2.6):
        g += mb.cylinder((0, 0, z), (0, 0, z + 0.05), 0.08, 0.08, "ruin_rust", segments=6)
    g += mb.sphere((0, 0, 2.88), 0.13, "ruin_rust", segments=6, rings=4)
    xform(g, pose((-0.2, 0.1, -0.25), (0.1, 0.16, 0.35)))
    tbox(mb, (0.55, -0.5, 0.1), (0.36, 0.16, 0.12), "iron", (0.2, 0.1, 0.7))    # The broken arm.
    rubble(mb, 81, [(-0.6, -0.6), (0.6, 0.55)], lo=0.12, hi=0.2)
    moss(mb, -0.25, 0.2, 0.2, 0.2)
    bush(mb, 0.65, -0.05, 0.13)
    bush(mb, -0.65, 0.65, 0.13)
    buildings.export(folder, "decor_giant_sword", mb)


def colossus_hand(folder):
    """The hand of a fallen colossus, palm up, fingers curled."""
    common.reset_scene()
    mb = MeshBuilder()
    ground(mb, 3)
    g = []
    g += mb.box((0, 0, 0), (1.0, 1.1, 0.4), S)
    g += mb.box((0, 0.05, 0.2), (0.7, 0.7, 0.06), SD)
    for i in range(4):
        x = -0.38 + i * 0.25
        m = SL if i % 2 else S
        g += tbox(mb, (x, -0.72, 0.12), (0.22, 0.5, 0.28), m, (-0.55, 0, 0))
        if i == 2:
            continue                                                             # A broken finger.
        g += tbox(mb, (x, -0.98, 0.5), (0.21, 0.27, 0.5), m, (-0.15, 0, 0))
        g += tbox(mb, (x, -0.9, 0.85), (0.2, 0.34, 0.22), m, (0.5, 0, 0))
    g += tbox(mb, (0.66, -0.15, 0.2), (0.5, 0.3, 0.3), SL, (0, -0.6, 0.5))
    g += tbox(mb, (0.86, -0.32, 0.55), (0.26, 0.26, 0.42), SL, (0.2, -0.2, 0.5))
    g += mb.box((0, 0.85, -0.02), (0.8, 0.7, 0.36), S)                           # Wrist.
    g += mb.box((0, 0.8, -0.02), (0.9, 0.24, 0.46), SD)                          # A bracelet of signs.
    for x in (-0.25, 0.0, 0.25):
        g += mb.box((x, 0.8, 0.2), (0.12, 0.12, 0.05), "ruin_rune")
    g += tbox(mb, (0.1, 1.22, 0.0), (0.5, 0.2, 0.26), SD, (0.3, 0.2, 0.4))        # The broken end.
    xform(g, pose((-0.1, -0.05, 0.3), (0.12, 0.12, 0.3)))
    tbox(mb, (0.9, -1.0, 0.14), (0.22, 0.5, 0.24), S, (0.1, 0.1, 1.1))          # The fallen finger.
    mb.sphere((-0.1, 0.1, 0), 1.1, "ruin_ground", segments=8, rings=4, scale=(1, 1.1, 0.18))
    rubble(mb, 91, [(-1.05, -1.0), (1.0, 0.5), (-1.05, 0.9)])
    moss(mb, -0.2, 0.15, 0.58, 0.25)
    bush(mb, 0.95, 1.05, 0.22)
    buildings.export(folder, "decor_colossus_hand", mb)


def beast_skeleton(folder):
    """The bones of a giant beast: spine, ribs and a horned skull."""
    common.reset_scene()
    mb = MeshBuilder()
    ground(mb, 4)
    spine = [(-1.8, 0.1), (-1.3, 0.32), (-0.8, 0.7), (-0.2, 0.95), (0.4, 1.0), (0.95, 0.82)]
    for (xa, za), (xb, zb) in zip(spine, spine[1:]):
        mb.cylinder((xa, 0, za), (xb, 0, zb), 0.1, 0.1, "ruin_bone", segments=6)
        mb.sphere((xb, 0, zb), 0.13, "ruin_bone", segments=6, rings=4)
    for i, x in enumerate((-0.75, -0.4, -0.05, 0.3, 0.65)):
        zs = 0.72 + 0.28 * math.sin((i + 1) * 0.6)
        w = 0.62 + 0.16 * math.sin((i + 0.5) * 0.7)
        for side in (-1, 1):
            pts = [(x, 0, zs), (x, side * w * 0.8, zs - 0.12), (x, side * w * 1.15, zs * 0.45),
                   (x + 0.05, side * w * 0.8, 0.06)]
            keep = 1 if (i, side) in ((1, -1), (4, 1)) else 3                   # Two ribs are snapped.
            for a, b in list(zip(pts, pts[1:]))[:keep]:
                mb.cylinder(a, b, 0.055, 0.045, "ruin_bone", segments=5)
    mb.cylinder((-0.3, -1.2, 0.07), (0.25, -1.35, 0.07), 0.05, 0.04, "ruin_bone", segments=5)
    # The skull.
    g = []
    g += mb.box((0, 0, 0), (0.6, 0.56, 0.44), "ruin_bone")
    g += mb.box((0.45, 0, -0.07), (0.5, 0.36, 0.26), "ruin_bone")
    g += mb.box((0.4, 0, -0.26), (0.56, 0.3, 0.08), "ruin_bone")
    for side in (-1, 1):
        g += mb.box((0.12, side * 0.26, 0.04), (0.2, 0.1, 0.18), "ruin_shadow")
        g += mb.cylinder((-0.15, side * 0.25, 0.2), (-0.55, side * 0.5, 0.55), 0.09, 0.02, "ruin_bone", segments=5)
        for k in range(3):
            g += mb.box((0.3 + k * 0.14, side * 0.15, -0.2), (0.06, 0.05, 0.1), "ruin_bone")
    xform(g, pose((1.15, 0.05, 0.42), (0.1, 0.25, -0.15)))
    # Leg bones and a few growing things.
    for x, y, a in ((-0.6, 1.25, 0.3), (0.5, 1.3, -0.2), (0.9, -1.2, 0.5)):
        mb.cylinder((x, y, 0.08), (x + 0.6 * math.cos(a), y + 0.6 * math.sin(a), 0.08), 0.06, 0.05, "ruin_bone",
                    segments=5)
        mb.sphere((x, y, 0.09), 0.09, "ruin_bone", segments=5, rings=3)
    moss(mb, -0.2, 0.0, 1.0, 0.2)
    bush(mb, -1.5, 1.45, 0.26)
    bush(mb, -1.3, -1.4, 0.2)
    bush(mb, 1.55, 1.3, 0.2)
    buildings.export(folder, "decor_beast_skeleton", mb)


def abandoned_camp(folder):
    """A camp nobody came back to: a torn tent and a cold fire ring."""
    common.reset_scene()
    mb = MeshBuilder()
    ground(mb, 3)
    x0, x1, yr, zr = -1.25, 0.35, 0.6, 1.15
    buildings.sloped_slab(mb, x0, x1, 1.35, yr, 0.05, zr, 0.04, "ruin_canvas")
    buildings.sloped_slab(mb, x0, -0.55, -0.15, yr, 0.05, zr, 0.04, "ruin_canvas")
    buildings.sloped_slab(mb, -0.55, -0.1, 0.25, yr, 0.62, zr, 0.04, "ruin_canvas")        # Torn flaps.
    buildings.sloped_slab(mb, -0.1, x1, 0.42, yr, 0.86, zr, 0.04, "ruin_canvas")
    buildings.sloped_slab(mb, -0.9, -0.6, 1.0, 0.8, 0.5, 0.82, 0.05, "cloth_red")           # A patch.
    mb.cylinder((x0 - 0.1, yr, zr), (x1 + 0.1, yr, zr), 0.035, 0.035, "timber", segments=5)
    mb.box((x0, yr, zr / 2), (0.07, 0.07, zr), "timber")
    tbox(mb, (x1, yr, zr / 2), (0.07, 0.07, zr + 0.05), "timber", (0.0, 0.1, 0))
    mb.cylinder((-1.0, 0.75, 0.12), (-0.1, 0.8, 0.12), 0.11, 0.11, "cloth_blue", segments=6)   # A bedroll.
    # The fire ring.
    fx, fy = 0.6, -0.65
    for i in range(7):
        a = i * 2 * math.pi / 7
        mb.box((fx + 0.36 * math.cos(a), fy + 0.36 * math.sin(a), 0.1), (0.2, 0.16, 0.16), S if i % 2 else SD,
               rotation_z=a + 0.3)
    mb.cylinder((fx, fy, 0.04), (fx, fy, 0.08), 0.3, 0.3, "ruin_ash", segments=8)
    for a in (0.3, 1.5, 2.6):
        mb.cylinder((fx - 0.25 * math.cos(a), fy - 0.25 * math.sin(a), 0.1),
                    (fx + 0.25 * math.cos(a), fy + 0.25 * math.sin(a), 0.14), 0.04, 0.04, "ruin_charred", segments=5)
    # A log to sit on, a tipped pot, a crate.
    mb.cylinder((-0.9, -1.0, 0.16), (0.0, -1.15, 0.16), 0.15, 0.15, "log", segments=7)
    mb.cylinder((1.05, -0.05, 0.12), (1.25, 0.05, 0.14), 0.13, 0.11, "iron", segments=7)
    buildings.crate(mb, 1.0, 0.9, s=0.45, mat="ruin_wood_grey")
    tbox(mb, (0.9, 0.95, 0.52), (0.4, 0.3, 0.04), "ruin_wood_old", (0.2, 0.1, 0.4))
    moss(mb, -0.6, 1.0, 0.45, 0.2)
    bush(mb, -1.15, -0.3, 0.2)
    bush(mb, 1.1, -1.15, 0.16)
    buildings.export(folder, "decor_abandoned_camp", mb)


def dry_fountain(folder):
    """A fountain with a cracked, dry basin."""
    common.reset_scene()
    mb = MeshBuilder()
    ground(mb, 3)
    mb.cylinder((0, 0, 0), (0, 0, 0.12), 1.36, 1.36, SD, segments=8)
    ring(mb, 1.12, 0.24, [0.5, 0.5, 0.3, 0.5, 0.5, 0.5, 0.18, 0.5], (S, SL), z0=0.1, phase=math.pi / 8)
    ring(mb, 1.12, 0.3, [0.08, 0.08, 0, 0.08, 0.08, 0.08, 0, 0.08], (SD,), z0=0.6, phase=math.pi / 8)
    mb.cylinder((0, 0, 0.1), (0, 0, 0.16), 1.05, 1.05, "ruin_soot", segments=8)
    for a, length in ((0.4, 0.9), (2.5, 0.8), (4.3, 0.7)):
        mb.box((0.55 * math.cos(a), 0.55 * math.sin(a), 0.16), (length, 0.05, 0.02), "ruin_shadow",
               rotation_z=a + 0.4)
    mb.cylinder((0, 0, 0.16), (0, 0, 0.4), 0.4, 0.34, SD, segments=8)
    mb.cylinder((0, 0, 0.4), (0, 0, 1.25), 0.2, 0.16, SL, segments=8)
    mb.cylinder((0, 0, 1.25), (0, 0, 1.5), 0.2, 0.62, S, segments=8)
    mb.cylinder((0, 0, 1.49), (0, 0, 1.51), 0.5, 0.5, "ruin_shadow", segments=8)
    mb.cylinder((0, 0, 1.5), (0, 0, 1.8), 0.12, 0.09, SL, segments=6)
    tbox(mb, (0.02, 0, 1.85), (0.2, 0.18, 0.14), SD, (0.4, 0.3, 0))
    # Fallen pieces, dead leaves, moss.
    tbox(mb, (0.5, -0.45, 0.3), (0.5, 0.3, 0.2), S, (0.3, 0.2, 0.6))
    rubble(mb, 101, [(0.95, -0.95), (-0.6, 0.4)], lo=0.14, hi=0.24)
    rnd = random.Random(3)
    for _ in range(9):
        a, r = rnd.uniform(0, 6.28), rnd.uniform(0.35, 0.9)
        mb.box((r * math.cos(a), r * math.sin(a), 0.17), (0.12, 0.08, 0.02), rnd.choice(("thatch_dark", "clay")),
               rotation_z=rnd.uniform(0, 3))
    moss(mb, -0.75, -0.75, 0.6, 0.22)
    moss(mb, 0.3, 0.2, 1.5, 0.2)
    moss(mb, -0.4, 0.6, 0.16, 0.25, flat=0.2)
    bush(mb, -1.2, 1.2, 0.14)
    buildings.export(folder, "decor_dry_fountain", mb)


def mine_entrance(folder):
    """A boarded-up mine mouth in a rock, with rusted rails and a tipped cart."""
    common.reset_scene()
    mb = MeshBuilder()
    ground(mb, 4)
    mb.sphere((0, 0.55, 0.5), 1.0, "ruin_rock", segments=8, rings=6, scale=(1.75, 1.25, 2.0))
    mb.sphere((-1.1, 0.3, 0.2), 0.7, SD, segments=7, rings=5, scale=(1.0, 1.1, 1.5))
    mb.sphere((1.15, 0.5, 0.2), 0.65, SD, segments=7, rings=5, scale=(1.0, 1.2, 1.7))
    mb.sphere((0.3, 1.2, 0.3), 0.6, "ruin_rock", segments=7, rings=5, scale=(1.5, 1.0, 1.6))
    y = -0.72
    mb.box((0, y + 0.3, 0.8), (1.15, 0.7, 1.6), "ruin_shadow")
    for side in (-1, 1):
        tbox(mb, (side * 0.66, y, 0.9), (0.2, 0.5, 1.8), "timber", (0, side * 0.06, 0))
    tbox(mb, (0, y, 1.75), (1.7, 0.56, 0.2), "timber", (0, 0.05, 0))
    tbox(mb, (0.0, y - 0.3, 0.9), (1.5, 0.05, 0.18), "ruin_wood_grey", (0, 0.35, 0))       # Boards across.
    tbox(mb, (0.05, y - 0.3, 0.55), (1.45, 0.05, 0.18), "ruin_wood_old", (0, -0.2, 0))
    # Rails.
    for i in range(4):
        mb.box((0, -1.0 - i * 0.26, 0.07), (0.8, 0.12, 0.05), "ruin_wood_old")
    for side in (-1, 1):
        mb.box((side * 0.28, -1.3, 0.11), (0.05, 1.1, 0.05), "ruin_rust")
    # The cart, off the rails.
    g = []
    g += mb.box((0, 0, 0.3), (0.8, 0.55, 0.4), "ruin_rust")
    g += mb.box((0, 0, 0.5), (0.7, 0.45, 0.04), "ruin_shadow")
    g += mb.box((0, 0, 0.3), (0.84, 0.59, 0.06), "iron")
    for x in (-0.25, 0.25):
        for side in (-1, 1):
            g += mb.cylinder((x, side * 0.26, 0.1), (x, side * 0.32, 0.1), 0.12, 0.12, "iron", segments=8)
    xform(g, pose((1.3, -1.3, 0.12), (0.5, 0.0, 0.5)))
    rubble(mb, 111, [(-1.3, -1.2), (-0.8, -1.4), (1.5, -0.6)], mats=("ruin_rock", SD))
    moss(mb, -0.5, 0.4, 2.4, 0.4)
    moss(mb, 1.2, 0.3, 1.25, 0.3)
    bush(mb, -1.5, -0.5, 0.24)
    buildings.export(folder, "decor_mine_entrance", mb)


def rusted_plough(folder):
    """A plough left in its last furrow."""
    common.reset_scene()
    mb = MeshBuilder()
    ground(mb, 2)
    mb.box((0.0, 0.25, 0.06), (1.7, 0.3, 0.08), "soil")
    mb.box((0.0, -0.5, 0.06), (1.7, 0.25, 0.07), "soil")
    g = []
    g += mb.cylinder((-0.6, 0, 0.42), (0.7, 0, 0.36), 0.05, 0.05, "ruin_wood_grey", segments=6)
    for side in (-1, 1):
        g += mb.cylinder((-0.3, side * 0.06, 0.4), (-0.8, side * 0.26, 0.95), 0.035, 0.035, "ruin_wood_old",
                         segments=5)
    g += mb.cylinder((-0.62, -0.2, 0.75), (-0.62, 0.2, 0.75), 0.03, 0.03, "ruin_wood_old", segments=5)
    g += tbox(mb, (-0.1, 0, 0.2), (0.6, 0.07, 0.3), "ruin_rust", (0, 0.5, 0))                 # Share.
    g += tbox(mb, (-0.2, 0.1, 0.25), (0.5, 0.06, 0.34), "ruin_rust", (0.3, 0.5, 0.3))        # Mouldboard.
    g += mb.box((0.25, 0, 0.25), (0.06, 0.03, 0.4), "iron")                                 # Coulter.
    g += xform(wheel(mb, 0.24), pose((0.62, 0.0, 0.24)))
    xform(g, pose((-0.06, -0.1, 0.02), (0.3, 0.0, 0.15)))
    moss(mb, -0.3, 0.3, 0.1, 0.16)
    bush(mb, 0.6, 0.65, 0.14)
    bush(mb, -0.65, -0.6, 0.13)
    bush(mb, 0.3, -0.7, 0.1)
    buildings.export(folder, "decor_rusted_plough", mb)


def broken_bridge(folder):
    """The stub of a stone bridge: an abutment, the start of the span, a lone pier."""
    common.reset_scene()
    mb = MeshBuilder()
    ground(mb, 4)
    mb.box((0.6, 0, 0.04), (2.4, 3.4, 0.05), "ruin_soot")                       # The dry bed.
    for i, (x, h) in enumerate(((-1.7, 0.45), (-1.4, 0.9))):
        mb.box((x, 0, h / 2), (0.34, 1.7, h), SD if i else S)
    mb.box((-0.9, 0, 0.7), (0.9, 1.7, 1.4), S)
    mb.box((-0.9, 0, 0.3), (1.0, 1.8, 0.2), SD)
    mb.box((-0.35, 0, 1.25), (1.9, 1.7, 0.3), SL)                               # Deck.
    mb.box((-0.2, 0, 0.9), (0.6, 1.6, 0.5), S)                                  # Springing of the arch.
    tbox(mb, (0.25, 0, 1.0), (0.5, 1.6, 0.3), SD, (0, -0.5, 0))
    for side in (-1, 1):
        mb.box((-0.8, side * 0.78, 1.6), (1.0, 0.16, 0.4), S)
        mb.box((-0.05, side * 0.78, 1.52), (0.5, 0.16, 0.24), SL if side > 0 else S)
        mb.box((-1.25, side * 0.78, 1.86), (0.24, 0.22, 0.14), SD)
    tbox(mb, (0.58, 0.3, 1.36), (0.3, 0.7, 0.26), S, (0.1, 0.3, 0.2))           # Jagged end.
    # The pier on the other side, and what fell between.
    mb.box((1.4, 0, 0.5), (0.7, 1.5, 1.0), S)
    mb.box((1.4, 0, 0.14), (0.86, 1.66, 0.28), SD)
    tbox(mb, (1.4, -0.3, 1.08), (0.5, 0.6, 0.24), SL, (0.2, 0.1, 0.3))
    tbox(mb, (0.75, -0.2, 0.3), (0.7, 1.0, 0.28), SL, (0.1, 0.5, 0.2))
    rubble(mb, 121, [(0.6, 0.9), (0.4, -1.1), (1.0, 1.4), (0.1, 0.2)], lo=0.2, hi=0.38)
    moss(mb, -0.6, 0.3, 1.4, 0.3)
    moss(mb, 1.4, 0.4, 1.0, 0.25)
    bush(mb, -1.5, 1.5, 0.26)
    bush(mb, -1.5, -1.5, 0.22)
    bush(mb, 1.55, -1.5, 0.2)
    buildings.export(folder, "decor_broken_bridge", mb)


def overgrown_house(folder):
    """The front of an abandoned house, taken over by ivy and bushes."""
    common.reset_scene()
    mb = MeshBuilder()
    ground(mb, 4)
    w, y0, h = 3.4, -1.1, 2.4
    mb.box((0, 0.2, 0.12), (w + 0.2, 2.9, 0.24), "stone")
    # Front wall in three parts around the door.
    mb.box((-1.05, y0, 0.24 + h / 2), (1.3, 0.2, h), "ruin_soot")
    mb.box((1.05, y0, 0.24 + h / 2), (1.3, 0.2, h), "ruin_soot")
    mb.box((0, y0, 2.3), (0.8, 0.2, 0.68), "ruin_soot")
    for x in (-1.7, -0.4, 0.4, 1.7):
        mb.box((x, y0, 0.24 + h / 2), (0.16, 0.24, h), "timber")
    mb.box((0, y0, 0.24 + h), (w + 0.16, 0.24, 0.16), "timber")
    mb.box((0, y0, 1.96), (0.9, 0.24, 0.12), "timber")
    mb.box((0, y0 + 0.02, 1.1), (0.7, 0.1, 1.7), "ruin_shadow")
    tbox(mb, (-0.15, y0 - 0.3, 1.05), (0.7, 0.06, 1.6), "door", (0.0, 0.08, 1.1))   # The door hangs open.
    for x in (-1.05, 1.05):
        mb.box((x, y0 - 0.02, 1.5), (0.6, 0.2, 0.55), "ruin_shadow")
        mb.box((x, y0 - 0.1, 1.2), (0.7, 0.1, 0.06), "timber")
    tbox(mb, (-1.45, y0 - 0.13, 1.4), (0.24, 0.05, 0.55), "shutter", (0, 0.35, 0))
    mb.box((1.45, y0 - 0.13, 1.5), (0.24, 0.05, 0.55), "shutter")
    # Side walls falling away to the back, and two rafters.
    for side in (-1, 1):
        for k, hh in enumerate((2.0, 1.3, 0.6)):
            mb.box((side * 1.7, y0 + 0.5 + k * 0.85, 0.24 + hh / 2), (0.2, 0.85, hh), "ruin_soot")
    tbox(mb, (-1.7, y0 + 0.75, 3.2), (0.12, 2.0, 0.12), "timber", (0.75, 0, 0))
    tbox(mb, (0.3, 0.3, 0.75), (0.12, 2.6, 0.12), "timber", (0.35, 0, 0.5))
    # Green things everywhere.
    for x, z, sw, sh in ((-1.3, 1.1, 0.7, 1.9), (-0.75, 2.2, 0.5, 0.7), (1.4, 0.8, 0.5, 1.2), (0.9, 2.45, 0.9, 0.4),
                         (0.2, 2.5, 0.5, 0.3)):
        mb.box((x, y0 - 0.12, z), (sw, 0.06, sh), "ruin_moss" if z < 2 else "leaves")
    mb.sphere((0.5, 0.5, 1.0), 0.9, "leaves", segments=7, rings=5, scale=(1, 1, 1.1))
    mb.sphere((1.0, 0.9, 1.7), 0.6, "ruin_moss", segments=7, rings=5)
    mb.cylinder((0.6, 0.6, 0.2), (0.7, 0.7, 1.2), 0.12, 0.08, "log", segments=6)
    bush(mb, -1.0, 0.6, 0.4)
    bush(mb, -1.5, -1.6, 0.22)
    bush(mb, 1.3, -1.6, 0.2)
    moss(mb, -1.62, 0.3, 1.55, 0.25)
    rubble(mb, 131, [(-0.9, 1.3)], mats=("ruin_soot", "stone"))
    buildings.export(folder, "decor_overgrown_house", mb)


def sunken_stairs(folder):
    """A stairway between old kerbs that goes down into the dark under a carved doorway."""
    common.reset_scene()
    mb = MeshBuilder()
    ground(mb, 3)
    for side in (-1, 1):
        mb.box((side * 0.95, -0.2, 0.3), (0.34, 2.3, 0.6), S)
        mb.box((side * 0.95, -0.2, 0.63), (0.42, 2.36, 0.08), SD)
        mb.box((side * 0.95, -1.2, 0.85), (0.3, 0.3, 0.4), SL)                  # Newel stones.
    mats = (SL, S, S, SD, SD, "ruin_ash", "ruin_shadow")
    for i, mat in enumerate(mats):
        top = 0.52 - i * 0.075
        mb.box((0, -1.2 + i * 0.3, top / 2), (1.6, 0.31, top), mat)
    # The doorway the steps go under.
    for side in (-1, 1):
        mb.box((side * 0.85, 1.1, 0.95), (0.5, 0.5, 1.9), S if side < 0 else SL)
        mb.box((side * 0.58, 0.84, 0.75), (0.05, 0.04, 1.2), "ruin_rune")
    mb.box((0, 1.1, 1.75), (2.3, 0.56, 0.4), SD)
    mb.box((0, 1.12, 0.8), (1.2, 0.4, 1.6), "ruin_shadow")
    tbox(mb, (-0.4, 1.1, 2.05), (0.9, 0.5, 0.26), S, (0, 0.1, 0))
    glyph(mb, 0, 1.1, 1.75, -math.pi / 2, 3, "ruin_rune", out=0.27)
    glyph(mb, -0.5, 1.1, 1.75, -math.pi / 2, 1, "ruin_rune", out=0.27)
    glyph(mb, 0.5, 1.1, 1.75, -math.pi / 2, 2, "ruin_rune", out=0.27)
    # A cover slab pushed aside.
    tbox(mb, (0.75, -0.3, 0.72), (0.9, 1.1, 0.12), SL, (0.1, -0.35, 0.2))
    rubble(mb, 141, [(-0.3, -0.6), (1.15, -1.15)], lo=0.12, hi=0.22)
    moss(mb, -0.95, 0.2, 0.67, 0.25)
    moss(mb, 0.6, 1.1, 1.95, 0.28)
    bush(mb, -1.2, 1.1, 0.14)
    bush(mb, 1.22, 0.4, 0.13)
    buildings.export(folder, "decor_sunken_stairs", mb)


MODELS = (rune_circle, stone_head, broken_columns, fallen_arch, tower_stump, ruined_wall, burnt_cottage,
          collapsed_shed, wrecked_cart, wrecked_boat, broken_barrels, old_well, portal_gate, monolith,
          giant_sword, colossus_hand, beast_skeleton, abandoned_camp, dry_fountain, mine_entrance, rusted_plough,
          broken_bridge, overgrown_house, sunken_stairs)


def make_all(folder):
    os.makedirs(folder, exist_ok=True)
    for model in MODELS:
        model(folder)


if __name__ == "__main__":
    make_all(sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else ".")
