"""Decoration models: petrified people and monuments.

People turned to stone in the middle of what they were doing, standing on the
ground or a rough slab, and a few monuments. Run with Blender:

    blender --background --factory-startup --python art/blender/decor/statues.py -- <output folder>

Conventions as in buildings.py: meters, Z up, front toward -Y, on Z = 0,
centered on the origin and inside a square footprint of 2 or 3 meters.
"""

import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import common  # noqa: E402
import buildings  # noqa: E402
from common import MeshBuilder  # noqa: E402

buildings.COLORS.update({
    "stat_stone": common.rgb(0x93918B),
    "stat_stone_light": common.rgb(0xADAAA2),
    "stat_stone_dark": common.rgb(0x6C6A66),
    "stat_slab": common.rgb(0x8A877E),
    "stat_moss": common.rgb(0x5F7D3A),
    "stat_moss_dark": common.rgb(0x48632E),
    "stat_earth": common.rgb(0x6B5238),
    "stat_niche": common.rgb(0x2A2622),
    "stat_totem_wood": common.rgb(0x7A5232),
    "stat_totem_red": common.rgb(0xA63C30),
    "stat_totem_teal": common.rgb(0x2F7F7A),
    "stat_totem_cream": common.rgb(0xE2D6B4),
    "stat_totem_black": common.rgb(0x26221F),
    "stat_bronze": common.rgb(0xB08A3A),
    "stat_flame": common.rgb(0xE8842A),
    "stat_flame_core": common.rgb(0xF4CC4A),
})

S = "stat_stone"
SL = "stat_stone_light"
SD = "stat_stone_dark"


# --- Pieces ------------------------------------------------------------------------------

def extrude(mb, points, offset, mat):
    """A flat polygon of 3D points extruded by the vector `offset`."""
    bm = mb.bm
    a = [bm.verts.new(p) for p in points]
    b = [bm.verts.new((p[0] + offset[0], p[1] + offset[1], p[2] + offset[2])) for p in points]
    bm.faces.new(a)
    bm.faces.new(list(reversed(b)))
    n = len(points)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((a[i], b[i], b[j], a[j]))
    return mb._finish(a + b, mat, None)


def taper(mb, cx, cy, z0, z1, w0, w1, mat, d0=None, d1=None):
    """A four-sided block that narrows from (w0 x d0) at z0 to (w1 x d1) at z1."""
    d0 = w0 if d0 is None else d0
    d1 = w1 if d1 is None else d1
    bm = mb.bm
    corners = ((-1, -1), (1, -1), (1, 1), (-1, 1))
    lo = [bm.verts.new((cx + sx * w0 / 2, cy + sy * d0 / 2, z0)) for sx, sy in corners]
    hi = [bm.verts.new((cx + sx * w1 / 2, cy + sy * d1 / 2, z1)) for sx, sy in corners]
    bm.faces.new(list(reversed(lo)))
    bm.faces.new(hi)
    for i in range(4):
        j = (i + 1) % 4
        bm.faces.new((lo[i], lo[j], hi[j], hi[i]))
    return mb._finish(lo + hi, mat, None)


def rough_slab(mb, radius, h=0.12, mat="stat_slab", seed=0, cx=0.0, cy=0.0, sides=9):
    """An irregular low slab of rock: the ground a petrified figure stands on."""
    pts = []
    for i in range(sides):
        a = 2 * math.pi * i / sides
        r = radius * (0.84 + 0.16 * math.sin(i * 2.3 + seed * 1.7))
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    mb.prism(pts, 0.0, h, mat)


def rock(mb, x, y, r, mat=SD, z=0.0, squash=0.7):
    mb.sphere((x, y, z + r * squash * 0.5), r, mat, segments=5, rings=3, scale=(1.0, 0.8, squash))


def moss(mb, x, y, z, r=0.14, mat="stat_moss", flat=0.35):
    mb.sphere((x, y, z), r, mat, segments=6, rings=3, scale=(1.0, 0.85, flat))


POSE = {
    "pelvis": (0, 0, 0.95), "chest": (0, 0, 1.42), "head": (0, 0, 1.67), "face": (0, -1, 0),
    "sh_l": (-0.22, 0, 1.40), "el_l": (-0.29, 0.0, 1.12), "ha_l": (-0.29, -0.06, 0.86),
    "sh_r": (0.22, 0, 1.40), "el_r": (0.29, 0.0, 1.12), "ha_r": (0.29, -0.06, 0.86),
    "hip_l": (-0.10, 0, 0.93), "kn_l": (-0.11, -0.03, 0.50), "ft_l": (-0.12, 0, 0.06),
    "hip_r": (0.10, 0, 0.93), "kn_r": (0.11, -0.03, 0.50), "ft_r": (0.12, 0, 0.06),
    "toe_l": (0, -0.17, -0.02), "toe_r": (0, -0.17, -0.02),
}


def figure(mb, pose, at=(0, 0, 0), yaw=0.0, scale=1.0, mat=S, skirt=False, legs=True, skirt_z=0.0):
    """A person made of tapered cylinders, about 1.8 m tall at scale 1.

    `pose` overrides joints of POSE (local meters, front toward -Y). Returns
    the function that maps a local point to the model, to attach props.
    """
    p = dict(POSE)
    p.update(pose)
    c, s = math.cos(yaw), math.sin(yaw)

    def T(q):
        x, y, z = q[0] * scale, q[1] * scale, q[2] * scale
        return (at[0] + x * c - y * s, at[1] + x * s + y * c, at[2] + z)

    def limb(a, b, r1, r2, seg=6):
        mb.cylinder(T(a), T(b), r1 * scale, r2 * scale, mat, segments=seg)

    def add(a, b):
        return (a[0] + b[0], a[1] + b[1], a[2] + b[2])

    limb(p["pelvis"], p["chest"], 0.17, 0.22, seg=8)
    limb(p["sh_l"], p["sh_r"], 0.085, 0.085)
    limb(p["chest"], p["head"], 0.07, 0.07)
    mb.sphere(T(p["head"]), 0.15 * scale, mat, segments=8, rings=5)
    f = p["face"]
    n = math.sqrt(f[0] ** 2 + f[1] ** 2 + f[2] ** 2)
    nose = add(p["head"], (f[0] / n * 0.15, f[1] / n * 0.15, f[2] / n * 0.15 - 0.02))
    mb.sphere(T(nose), 0.04 * scale, mat, segments=4, rings=3)
    for side in ("l", "r"):
        limb(p["sh_" + side], p["el_" + side], 0.075, 0.065)
        limb(p["el_" + side], p["ha_" + side], 0.065, 0.05)
        mb.sphere(T(p["ha_" + side]), 0.065 * scale, mat, segments=5, rings=3)
    if skirt:
        base = (p["pelvis"][0], p["pelvis"][1], skirt_z)
        limb(base, add(p["pelvis"], (0, 0, 0.12)), 0.40, 0.18, seg=9)
    elif legs:
        limb(p["hip_l"], p["hip_r"], 0.11, 0.11)
        for side in ("l", "r"):
            limb(p["hip_" + side], p["kn_" + side], 0.105, 0.085)
            limb(p["kn_" + side], p["ft_" + side], 0.085, 0.06)
            limb(p["ft_" + side], add(p["ft_" + side], p["toe_" + side]), 0.065, 0.05, seg=5)
    return T


def begin():
    common.reset_scene()
    return MeshBuilder()


# --- Petrified people --------------------------------------------------------------------

def petrified_runner(folder):
    """A villager caught running, looking back over the shoulder."""
    mb = begin()
    rough_slab(mb, 0.86, 0.1, seed=1)
    z = 0.1
    T = figure(mb, {
        "pelvis": (0, 0, 0.92), "chest": (0, -0.22, 1.36), "head": (0.02, -0.28, 1.61), "face": (0.75, 0.65, 0.05),
        "sh_l": (-0.22, -0.24, 1.35), "el_l": (-0.30, -0.46, 1.20), "ha_l": (-0.26, -0.64, 1.40),
        "sh_r": (0.22, -0.18, 1.35), "el_r": (0.33, 0.08, 1.20), "ha_r": (0.42, 0.30, 1.28),
        "hip_l": (-0.10, 0, 0.90), "kn_l": (-0.11, 0.20, 0.50), "ft_l": (-0.11, 0.60, 0.42),
        "toe_l": (0, 0.08, -0.15),
        "hip_r": (0.10, 0, 0.90), "kn_r": (0.10, -0.40, 0.62), "ft_r": (0.10, -0.38, 0.07),
    }, at=(0, 0.05, z))
    # The tunic, blown back.
    taper(mb, 0, 0.1, z + 0.72, z + 1.02, 0.44, 0.36, SD, d0=0.4, d1=0.3)
    moss(mb, *T((-0.2, -0.24, 1.44)), r=0.11)
    moss(mb, 0.5, 0.45, 0.11, r=0.2)
    moss(mb, -0.55, -0.3, 0.11, r=0.16, mat="stat_moss_dark")
    rock(mb, -0.55, 0.5, 0.16, z=0.08)
    buildings.export(folder, "decor_petrified_runner", mb)


def petrified_kneeling(folder):
    """A kneeling figure shielding its face with both arms."""
    mb = begin()
    rough_slab(mb, 0.84, 0.1, seed=2)
    z = 0.1
    T = figure(mb, {
        "pelvis": (0, 0.14, 0.50), "chest": (0, 0.0, 0.96), "head": (0, -0.08, 1.19), "face": (0, -1, -0.5),
        "sh_l": (-0.22, 0.0, 0.94), "el_l": (-0.32, -0.34, 1.02), "ha_l": (0.05, -0.36, 1.36),
        "sh_r": (0.22, 0.0, 0.94), "el_r": (0.32, -0.34, 1.00), "ha_r": (-0.07, -0.40, 1.24),
        "hip_l": (-0.11, 0.14, 0.46), "kn_l": (-0.15, -0.30, 0.10), "ft_l": (-0.14, 0.42, 0.07),
        "hip_r": (0.11, 0.14, 0.46), "kn_r": (0.15, -0.30, 0.10), "ft_r": (0.14, 0.42, 0.07),
        "toe_l": (0, 0.14, -0.02), "toe_r": (0, 0.14, -0.02),
    }, at=(0, -0.05, z))
    # A cloak falling down the back.
    mb.cylinder(T((0, 0.40, 0.0)), T((0, 0.08, 0.99)), 0.36, 0.2, SD, segments=7)
    moss(mb, *T((0.0, 0.16, 1.0)), r=0.14)
    moss(mb, -0.5, 0.3, 0.11, r=0.2, mat="stat_moss_dark")
    moss(mb, 0.45, -0.5, 0.11, r=0.15)
    rock(mb, 0.58, 0.3, 0.15, z=0.08)
    rock(mb, -0.6, -0.4, 0.11, z=0.08, mat=S)
    buildings.export(folder, "decor_petrified_kneeling", mb)


def sword(mb, hand, tip, mat=SL):
    """A blade from the hand toward `tip`, with a cross guard."""
    hx, hy, hz = hand
    dx, dy, dz = tip[0] - hx, tip[1] - hy, tip[2] - hz
    n = math.sqrt(dx * dx + dy * dy + dz * dz)
    ux, uy, uz = dx / n, dy / n, dz / n
    mb.cylinder((hx - ux * 0.14, hy - uy * 0.14, hz - uz * 0.14), (hx + ux * 0.1, hy + uy * 0.1, hz + uz * 0.1),
                0.03, 0.03, mat, segments=5)
    g = (hx + ux * 0.1, hy + uy * 0.1, hz + uz * 0.1)
    mb.cylinder((g[0] - 0.14, g[1], g[2]), (g[0] + 0.14, g[1], g[2]), 0.03, 0.03, mat, segments=5)
    mb.cylinder(g, tip, 0.045, 0.012, mat, segments=4)


def petrified_warrior(folder):
    """A warrior with the sword raised and the shield forward."""
    mb = begin()
    rough_slab(mb, 0.86, 0.1, seed=3)
    z = 0.1
    T = figure(mb, {
        "pelvis": (0, 0.02, 0.90), "chest": (0, -0.04, 1.38), "head": (0, -0.07, 1.63),
        "sh_r": (0.23, -0.02, 1.37), "el_r": (0.44, 0.08, 1.58), "ha_r": (0.40, -0.04, 1.90),
        "sh_l": (-0.23, -0.06, 1.37), "el_l": (-0.34, -0.24, 1.14), "ha_l": (-0.20, -0.42, 1.20),
        "hip_l": (-0.11, 0.02, 0.88), "kn_l": (-0.19, -0.26, 0.52), "ft_l": (-0.22, -0.30, 0.06),
        "hip_r": (0.11, 0.02, 0.88), "kn_r": (0.20, 0.18, 0.48), "ft_r": (0.26, 0.42, 0.06),
        "toe_r": (0.12, -0.12, -0.02),
    }, at=(0, 0.05, z))
    sword(mb, T((0.40, -0.04, 1.90)), T((0.30, -0.34, 2.72)))
    # Round shield on the forearm, and a pointed helmet.
    mb.cylinder(T((-0.24, -0.47, 1.2)), T((-0.24, -0.53, 1.2)), 0.32, 0.30, SD, segments=9)
    mb.cylinder(T((-0.24, -0.53, 1.2)), T((-0.24, -0.59, 1.2)), 0.09, 0.05, SL, segments=6)
    mb.cylinder(T((0, -0.07, 1.68)), T((0, -0.07, 1.92)), 0.165, 0.02, SD, segments=8)
    taper(mb, 0, 0.07, z + 0.74, z + 1.0, 0.46, 0.38, SD, d0=0.34, d1=0.3)
    moss(mb, *T((-0.24, -0.5, 1.5)), r=0.1)
    moss(mb, *T((0.2, 0.0, 1.46)), r=0.1, mat="stat_moss_dark")
    moss(mb, 0.5, -0.45, 0.11, r=0.2)
    moss(mb, -0.5, 0.5, 0.11, r=0.17, mat="stat_moss_dark")
    rock(mb, 0.6, 0.1, 0.13, z=0.08)
    buildings.export(folder, "decor_petrified_warrior", mb)


def petrified_mother(folder):
    """A mother in a long dress, holding a child against her chest."""
    mb = begin()
    rough_slab(mb, 0.82, 0.1, seed=4)
    z = 0.1
    T = figure(mb, {
        "head": (0.04, -0.07, 1.65), "face": (0.3, -1, -0.6),
        "sh_l": (-0.21, 0, 1.40), "el_l": (-0.30, -0.14, 1.12), "ha_l": (0.0, -0.33, 1.10),
        "sh_r": (0.21, 0, 1.40), "el_r": (0.31, -0.14, 1.16), "ha_r": (0.10, -0.34, 1.30),
    }, at=(0, 0.05, z), skirt=True)
    # The child, wrapped, with the head on her shoulder.
    mb.cylinder(T((-0.14, -0.26, 1.08)), T((0.10, -0.25, 1.32)), 0.12, 0.10, SL, segments=7)
    mb.sphere(T((0.15, -0.24, 1.43)), 0.105, SL, segments=7, rings=4)
    # Head scarf and shawl.
    mb.cylinder(T((0.04, 0.0, 1.5)), T((0.04, -0.04, 1.8)), 0.21, 0.12, SD, segments=7)
    taper(mb, 0, 0.19, z + 0.9, z + 1.46, 0.5, 0.44, SD, d0=0.12, d1=0.1)
    moss(mb, *T((-0.2, 0.02, 1.47)), r=0.1)
    moss(mb, *T((0.3, 0.2, 0.3)), r=0.14, mat="stat_moss_dark", flat=0.6)
    moss(mb, -0.5, -0.4, 0.11, r=0.2)
    moss(mb, 0.5, 0.45, 0.11, r=0.16, mat="stat_moss_dark")
    rock(mb, -0.6, 0.35, 0.14, z=0.08)
    buildings.export(folder, "decor_petrified_mother", mb)


def petrified_pair(folder):
    """Two people reaching for each other, their hands a little apart."""
    mb = begin()
    rough_slab(mb, 1.36, 0.1, seed=5, sides=11)
    z = 0.1
    reach = {
        "pelvis": (0, 0, 0.92), "chest": (0, -0.2, 1.36), "head": (0, -0.3, 1.60), "face": (0, -1, 0.1),
        "sh_l": (-0.22, -0.2, 1.35), "el_l": (-0.33, 0.04, 1.16), "ha_l": (-0.40, 0.26, 1.02),
        "sh_r": (0.22, -0.22, 1.35), "el_r": (0.20, -0.50, 1.40), "ha_r": (0.14, -0.76, 1.44),
        "hip_l": (-0.10, 0, 0.90), "kn_l": (-0.11, -0.34, 0.56), "ft_l": (-0.11, -0.36, 0.06),
        "hip_r": (0.10, 0, 0.90), "kn_r": (0.11, 0.18, 0.48), "ft_r": (0.11, 0.48, 0.10),
        "toe_r": (0, -0.12, -0.08),
    }
    a = figure(mb, reach, at=(-0.82, -0.12, z), yaw=math.pi / 2)
    taper(mb, -0.85, -0.12, z + 0.72, z + 1.0, 0.4, 0.3, S, d0=0.42, d1=0.36)
    # The other falls to one knee, the arm stretched up toward the first.
    fall = {
        "pelvis": (0, 0.05, 0.56), "chest": (0, -0.14, 1.0), "head": (0, -0.2, 1.25), "face": (0, -1, 0.5),
        "sh_l": (-0.22, -0.14, 0.99), "el_l": (-0.18, -0.42, 1.14), "ha_l": (-0.14, -0.70, 1.36),
        "sh_r": (0.22, -0.14, 0.99), "el_r": (0.34, -0.12, 0.70), "ha_r": (0.36, -0.30, 0.44),
        "hip_l": (-0.11, 0.05, 0.54), "kn_l": (-0.13, -0.38, 0.10), "ft_l": (-0.13, 0.34, 0.07),
        "toe_l": (0, 0.14, -0.02),
        "hip_r": (0.11, 0.05, 0.54), "kn_r": (0.14, -0.36, 0.52), "ft_r": (0.14, -0.40, 0.06),
    }
    b = figure(mb, fall, at=(0.78, -0.12, z), yaw=-math.pi / 2, mat=SL)
    taper(mb, 0.8, -0.12, z + 0.4, z + 0.66, 0.4, 0.34, SD, d0=0.42, d1=0.36)
    moss(mb, *a((0.2, -0.2, 1.44)), r=0.1)
    moss(mb, *b((0, 0.0, 1.06)), r=0.12, mat="stat_moss_dark")
    moss(mb, 0.0, 0.7, 0.11, r=0.26)
    moss(mb, -0.3, -0.9, 0.11, r=0.2, mat="stat_moss_dark")
    moss(mb, 0.9, 0.75, 0.11, r=0.17)
    rock(mb, 0.25, 0.95, 0.2, z=0.08)
    rock(mb, -0.9, 0.8, 0.15, z=0.08, mat=S)
    rock(mb, 0.5, -0.95, 0.13, z=0.08)
    buildings.export(folder, "decor_petrified_pair", mb)


def petrified_sunken(folder):
    """A figure half sunk in the ground, one arm still reaching up."""
    mb = begin()
    rough_slab(mb, 0.86, 0.06, mat="stat_earth", seed=6)
    # The heaved-up earth around the body.
    mb.sphere((0, 0.08, 0.02), 0.6, "stat_earth", segments=9, rings=4, scale=(1.0, 0.95, 0.38))
    T = figure(mb, {
        "pelvis": (0, 0.22, -0.20), "chest": (0, 0.0, 0.42), "head": (0.03, -0.1, 0.68), "face": (0.2, -0.7, 0.7),
        "sh_r": (0.22, 0.0, 0.42), "el_r": (0.36, -0.10, 0.74), "ha_r": (0.28, -0.22, 1.10),
        "sh_l": (-0.22, 0.0, 0.40), "el_l": (-0.44, -0.20, 0.30), "ha_l": (-0.50, -0.50, 0.10),
    }, at=(0, 0.1, 0), legs=False)
    # Fingers spread on the reaching hand.
    for dx in (-0.05, 0.0, 0.05):
        mb.cylinder(T((0.28, -0.22, 1.12)), T((0.28 + dx * 1.6, -0.25, 1.24)), 0.018, 0.012, S, segments=4)
    # A knee breaking the surface behind, and slabs of cracked ground.
    mb.sphere((0.16, 0.62, 0.1), 0.13, S, segments=6, rings=4)
    for i, (x, y, r) in enumerate(((0.55, -0.35, 0.3), (-0.55, 0.45, 0.6), (0.6, 0.4, 1.9), (-0.25, -0.62, 2.6))):
        mb.box((x, y, 0.1), (0.36, 0.26, 0.1), SD if i % 2 else "stat_slab", rotation_z=r)
    moss(mb, *T((-0.2, 0.02, 0.5)), r=0.1)
    moss(mb, 0.35, 0.6, 0.16, r=0.18, mat="stat_moss_dark")
    moss(mb, -0.6, -0.1, 0.1, r=0.16)
    buildings.export(folder, "decor_petrified_sunken", mb)


# --- Monuments ---------------------------------------------------------------------------

def obelisk(folder):
    mb = begin()
    mb.box((0, 0, 0.1), (1.7, 1.7, 0.2), SD)
    mb.box((0, 0, 0.32), (1.3, 1.3, 0.24), S)
    taper(mb, 0, 0, 0.44, 0.9, 0.86, 0.78, SL)
    mb.box((0, 0, 0.94), (0.86, 0.86, 0.08), SD)
    taper(mb, 0, 0, 0.98, 3.5, 0.62, 0.4, S)
    taper(mb, 0, 0, 3.5, 3.95, 0.4, 0.02, "stat_bronze")
    # Carved bands and a worn sign on the front.
    for zz in (1.5, 2.2, 2.9):
        w = 0.62 - (zz - 0.98) / 2.52 * 0.22 + 0.03
        mb.box((0, 0, zz), (w, w, 0.07), SD)
    mb.box((0, -0.4, 0.68), (0.4, 0.04, 0.26), SD)
    moss(mb, -0.5, -0.55, 0.22, r=0.2)
    moss(mb, 0.45, 0.3, 0.46, r=0.15, mat="stat_moss_dark")
    moss(mb, 0.62, -0.5, 0.22, r=0.14, mat="stat_moss_dark")
    buildings.export(folder, "decor_obelisk", mb)


def stone_arch(folder):
    mb = begin()
    spring = 2.0
    for sx in (-1, 1):
        x = sx * 1.0
        mb.box((x, 0, 0.12), (0.72, 0.86, 0.24), SD)
        mb.box((x, 0, 0.24 + (spring - 0.34) / 2), (0.5, 0.64, spring - 0.34), S)
        for zz in (0.75, 1.3):
            mb.box((x, 0, zz), (0.53, 0.67, 0.05), SD)
        mb.box((x, 0, spring - 0.05), (0.64, 0.78, 0.1), SL)
    # Wedge stones of the arch, the keystone a little bigger.
    n = 9
    for i in range(n):
        a0 = math.pi * i / n
        a1 = math.pi * (i + 1) / n
        key = i == n // 2
        r0, r1 = (0.72, 1.36) if key else (0.75, 1.25)
        y = 0.36 if key else 0.32
        pts = [(r0 * math.cos(a0), -y, spring + r0 * math.sin(a0)), (r1 * math.cos(a0), -y, spring + r1 * math.sin(a0)),
               (r1 * math.cos(a1), -y, spring + r1 * math.sin(a1)), (r0 * math.cos(a1), -y, spring + r0 * math.sin(a1))]
        extrude(mb, pts, (0, 2 * y, 0), SL if key else (S if i % 2 else SD))
    # Paving through it, a fallen block, moss.
    mb.box((0, 0, 0.03), (1.5, 1.2, 0.06), "stat_slab")
    mb.box((0.35, -0.95, 0.12), (0.5, 0.34, 0.24), S, rotation_z=0.5)
    rock(mb, -0.6, 0.95, 0.17)
    moss(mb, 1.0, 0.0, spring + 0.02, r=0.3, flat=0.2)
    moss(mb, -0.6, 0.0, spring + 1.08, r=0.22, mat="stat_moss_dark")
    moss(mb, -1.1, -0.45, 0.25, r=0.18)
    moss(mb, 0.4, -0.9, 0.25, r=0.14, mat="stat_moss_dark")
    buildings.export(folder, "decor_stone_arch", mb)


def totem_pole(folder):
    mb = begin()
    rough_slab(mb, 0.7, 0.14, seed=7)
    w = "stat_totem_wood"
    mb.cylinder((0, 0, 0.1), (0, 0, 0.5), 0.34, 0.32, w, segments=10)

    def face(z0, h, r, main, eye, beak=None, ears=False):
        mb.cylinder((0, 0, z0), (0, 0, z0 + h), r, r * 0.96, main, segments=10)
        mb.cylinder((0, 0, z0 + h - 0.06), (0, 0, z0 + h), r + 0.03, r + 0.03, "stat_totem_black", segments=10)
        for sx in (-1, 1):
            mb.box((sx * r * 0.42, -r * 0.88, z0 + h * 0.62), (r * 0.46, 0.08, h * 0.26), "stat_totem_cream")
            mb.box((sx * r * 0.42, -r * 0.93, z0 + h * 0.62), (r * 0.2, 0.06, h * 0.14), eye)
            if ears:
                extrude(mb, [(sx * r * 0.5, -0.06, z0 + h), (sx * (r + 0.02), -0.06, z0 + h),
                             (sx * r * 0.85, -0.06, z0 + h + 0.24)], (0, 0.12, 0), main)
        if beak:
            mb.cylinder((0, -r * 0.8, z0 + h * 0.42), (0, -r - 0.34, z0 + h * 0.26), 0.13, 0.02, beak, segments=5)
        else:
            mb.box((0, -r * 0.93, z0 + h * 0.22), (r * 0.9, 0.08, h * 0.16), "stat_totem_cream")
            mb.box((0, -r * 0.97, z0 + h * 0.22), (r * 0.7, 0.05, h * 0.05), "stat_totem_black")

    face(0.5, 0.8, 0.36, "stat_totem_red", "stat_totem_black", ears=False)
    face(1.3, 0.75, 0.33, "stat_totem_teal", "stat_totem_black", ears=True)
    face(2.05, 0.7, 0.3, w, "stat_totem_red")
    face(2.75, 0.65, 0.28, "stat_totem_cream", "stat_totem_black", beak="stat_bronze")
    # Wings of the bird on top.
    for sx in (-1, 1):
        extrude(mb, [(sx * 0.24, -0.04, 3.2), (sx * 0.86, -0.04, 3.36), (sx * 0.84, -0.04, 3.02),
                     (sx * 0.26, -0.04, 2.9)], (0, 0.08, 0), "stat_totem_red")
        extrude(mb, [(sx * 0.4, -0.07, 3.16), (sx * 0.74, -0.07, 3.24), (sx * 0.73, -0.07, 3.08),
                     (sx * 0.4, -0.07, 3.0)], (0, 0.03, 0), "stat_totem_teal")
    mb.cylinder((0, 0, 3.4), (0, 0, 3.62), 0.2, 0.04, "stat_totem_red", segments=6)
    moss(mb, 0.4, 0.3, 0.15, r=0.18)
    rock(mb, -0.5, -0.4, 0.14, z=0.1)
    buildings.export(folder, "decor_totem_pole", mb)


def roadside_shrine(folder):
    mb = begin()
    mb.box((0, 0, 0.06), (1.5, 1.4, 0.12), "stat_slab")
    mb.box((0, 0.1, 0.2), (1.0, 0.9, 0.18), SD)
    taper(mb, 0, 0.1, 0.29, 1.2, 0.74, 0.62, S, d0=0.66, d1=0.56)
    mb.box((0, 0.1, 1.25), (0.84, 0.76, 0.1), SL)
    # The little house with the niche.
    mb.box((0, 0.1, 1.7), (0.72, 0.64, 0.8), "plaster")
    mb.box((0, -0.2, 1.68), (0.44, 0.08, 0.6), "stat_niche")
    extrude(mb, [(-0.22, -0.24, 1.98), (0.22, -0.24, 1.98), (0, -0.24, 2.12)], (0, 0.03, 0), "stat_niche")
    # A small figure and a candle inside, an offering shelf.
    mb.cylinder((0, -0.25, 1.4), (0, -0.25, 1.74), 0.09, 0.05, "stat_bronze", segments=6)
    mb.sphere((0, -0.25, 1.8), 0.06, "stat_bronze", segments=6, rings=4)
    mb.box((0, -0.33, 1.36), (0.6, 0.2, 0.05), "wood")
    mb.cylinder((0.2, -0.36, 1.38), (0.2, -0.36, 1.5), 0.025, 0.025, "cloth_white", segments=5)
    mb.sphere((0.2, -0.36, 1.53), 0.03, "flowers_y", segments=4, rings=3)
    mb.sphere((-0.2, -0.36, 1.43), 0.06, "flowers", segments=5, rings=3)
    # Gable roof with the ridge front to back, and a cross on top.
    for sx in (-1, 1):
        extrude(mb, [(0, -0.38, 2.5), (sx * 0.52, -0.38, 2.04), (sx * 0.52, -0.38, 2.14), (0, -0.38, 2.62)],
                (0, 0.92, 0), "roof" if sx < 0 else "roof_dark")
    extrude(mb, [(-0.36, -0.22, 2.1), (0.36, -0.22, 2.1), (0, -0.22, 2.46)], (0, 0.64, 0), "plaster")
    mb.box((0, -0.2, 2.82), (0.05, 0.05, 0.4), "iron")
    mb.box((0, -0.2, 2.88), (0.22, 0.05, 0.05), "iron")
    # Flowers left at its foot.
    for i, (x, y) in enumerate(((-0.5, -0.5), (-0.3, -0.58), (0.45, -0.52), (0.58, -0.3))):
        mb.sphere((x, y, 0.2), 0.1, "leaves", segments=5, rings=3)
        mb.sphere((x, y - 0.02, 0.3), 0.055, "flowers" if i % 2 else "flowers_y", segments=5, rings=3)
    moss(mb, -0.4, 0.45, 0.3, r=0.16)
    moss(mb, 0.3, 0.1, 1.31, r=0.12, mat="stat_moss_dark")
    buildings.export(folder, "decor_roadside_shrine", mb)


def wayside_cross(folder):
    mb = begin()
    rough_slab(mb, 0.84, 0.14, seed=8)
    mb.box((0, 0, 0.26), (1.1, 0.9, 0.24), SD, rotation_z=0.06)
    mb.box((0, 0, 0.5), (0.8, 0.62, 0.24), S)
    taper(mb, 0, 0, 0.62, 2.9, 0.34, 0.24, SL, d0=0.24, d1=0.18)
    cz = 2.25
    mb.box((0, 0, cz), (1.44, 0.19, 0.26), SL)
    # The ring around the crossing.
    n = 12
    for i in range(n):
        a0 = 2 * math.pi * i / n
        a1 = 2 * math.pi * (i + 1) / n
        r0, r1 = 0.4, 0.52
        pts = [(r0 * math.cos(a0), -0.07, cz + r0 * math.sin(a0)), (r1 * math.cos(a0), -0.07, cz + r1 * math.sin(a0)),
               (r1 * math.cos(a1), -0.07, cz + r1 * math.sin(a1)), (r0 * math.cos(a1), -0.07, cz + r0 * math.sin(a1))]
        extrude(mb, pts, (0, 0.14, 0), S)
    mb.sphere((0, -0.1, cz), 0.1, SD, segments=6, rings=4, scale=(1, 0.5, 1))
    for zz in (1.0, 1.45):
        mb.box((0, -0.11, zz), (0.2, 0.04, 0.2), SD)
    moss(mb, -0.45, -0.3, 0.4, r=0.2)
    moss(mb, 0.3, 0.2, 0.63, r=0.14, mat="stat_moss_dark")
    moss(mb, -0.5, 0.0, cz + 0.14, r=0.12, flat=0.3)
    moss(mb, 0.55, -0.5, 0.15, r=0.18, mat="stat_moss_dark")
    rock(mb, 0.62, 0.4, 0.14, z=0.12)
    buildings.export(folder, "decor_wayside_cross", mb)


def hero_statue(folder):
    """A hero on a proper pedestal, both hands on the sword planted before him."""
    mb = begin()
    mb.box((0, 0, 0.1), (2.7, 2.7, 0.2), SD)
    mb.box((0, 0, 0.32), (2.1, 2.1, 0.24), S)
    mb.box((0, 0, 0.52), (1.5, 1.5, 0.16), SL)
    taper(mb, 0, 0, 0.6, 1.6, 1.2, 1.08, S)
    mb.box((0, 0, 1.67), (1.34, 1.34, 0.14), SL)
    mb.box((0, -0.6, 1.12), (0.7, 0.05, 0.4), "stat_bronze")
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.cylinder((sx * 1.15, sy * 1.15, 0.2), (sx * 1.15, sy * 1.15, 0.75), 0.13, 0.1, SD, segments=6)
            mb.sphere((sx * 1.15, sy * 1.15, 0.8), 0.13, SL, segments=6, rings=4)
    z = 1.74
    k = 1.25
    T = figure(mb, {
        "head": (0, -0.02, 1.68), "face": (0, -1, 0.15),
        "sh_l": (-0.24, 0, 1.40), "el_l": (-0.30, -0.20, 1.14), "ha_l": (-0.03, -0.36, 1.06),
        "sh_r": (0.24, 0, 1.40), "el_r": (0.30, -0.20, 1.14), "ha_r": (0.03, -0.36, 1.12),
        "ft_l": (-0.2, 0.02, 0.06), "kn_l": (-0.16, -0.03, 0.5),
        "ft_r": (0.2, 0.02, 0.06), "kn_r": (0.16, -0.03, 0.5),
    }, at=(0, 0.1, z), scale=k, mat=SL)
    sword(mb, T((0, -0.36, 1.0)), T((0, -0.36, 0.02)), mat="stat_bronze")
    # Cape, crown and chest plate.
    taper(mb, 0, 0.1 + 0.2 * k, z + 0.12, z + 1.44 * k, 0.74, 0.5, S, d0=0.14, d1=0.1)
    mb.cylinder(T((0, -0.02, 1.76)), T((0, -0.02, 1.86)), 0.13 * k, 0.16 * k, "stat_bronze", segments=8)
    taper(mb, 0, 0.1, z + 0.72 * k, z + 1.0 * k, 0.5, 0.44, S, d0=0.36, d1=0.32)
    buildings.export(folder, "decor_hero_statue", mb)


def sundial(folder):
    mb = begin()
    # A ring of paving stones.
    n = 10
    for i in range(n):
        a0 = 2 * math.pi * i / n + 0.03
        a1 = 2 * math.pi * (i + 1) / n - 0.03
        r0, r1 = 0.5, 0.88
        pts = [(r0 * math.cos(a0), r0 * math.sin(a0), 0.0), (r1 * math.cos(a0), r1 * math.sin(a0), 0.0),
               (r1 * math.cos(a1), r1 * math.sin(a1), 0.0), (r0 * math.cos(a1), r0 * math.sin(a1), 0.0)]
        extrude(mb, pts, (0, 0, 0.07 + 0.02 * (i % 3)), "stat_slab" if i % 2 else SD)
    mb.cylinder((0, 0, 0), (0, 0, 0.2), 0.5, 0.46, SD, segments=10)
    mb.cylinder((0, 0, 0.2), (0, 0, 0.32), 0.36, 0.3, S, segments=10)
    mb.cylinder((0, 0, 0.32), (0, 0, 0.92), 0.2, 0.17, SL, segments=8)
    mb.cylinder((0, 0, 0.92), (0, 0, 1.02), 0.24, 0.42, S, segments=10)
    mb.cylinder((0, 0, 1.02), (0, 0, 1.1), 0.56, 0.56, SL, segments=12)
    mb.cylinder((0, 0, 1.1), (0, 0, 1.115), 0.47, 0.47, "stat_bronze", segments=12)
    # The gnomon, and the hour marks around the dial.
    extrude(mb, [(-0.015, 0.36, 1.11), (-0.015, -0.34, 1.11), (-0.015, 0.36, 1.5)], (0.03, 0, 0), "iron")
    for i in range(9):
        a = math.pi + math.pi * i / 8
        mb.box((0.4 * math.cos(a), 0.4 * math.sin(a), 1.12), (0.035, 0.1, 0.02), "iron", rotation_z=a + math.pi / 2)
    moss(mb, 0.4, 0.3, 0.2, r=0.15)
    moss(mb, -0.6, -0.35, 0.1, r=0.16, mat="stat_moss_dark")
    buildings.export(folder, "decor_sundial", mb)


# --- More petrified people ---------------------------------------------------------------

def scatter(mb, radius, seed, n=6, z=0.11):
    """Moss patches and a couple of stones around the rim of a slab."""
    for i in range(n):
        a = seed * 1.3 + i * 2 * math.pi / n + 0.4 * math.sin(i * 1.7 + seed)
        r = radius * (0.74 + 0.1 * math.sin(i * 1.9 + seed))
        size = 0.15 + 0.05 * math.sin(i * 2.9 + seed)
        if i % 3 == 2:
            rock(mb, r * math.cos(a), r * math.sin(a), size * 0.8, z=z - 0.03, mat=S if i % 2 else SD)
        else:
            moss(mb, r * math.cos(a), r * math.sin(a), z, r=size, mat="stat_moss" if i % 2 else "stat_moss_dark")


def mossy(mb, T, points, r=0.1):
    """Moss growing on a figure, at local points of it."""
    for i, q in enumerate(points):
        moss(mb, *T(q), r=r, mat="stat_moss" if i % 2 else "stat_moss_dark", flat=0.45)


def petrified_child(folder):
    """A child bending to reach a toy horse dropped on the ground."""
    mb = begin()
    rough_slab(mb, 0.84, 0.1, seed=11)
    z = 0.1
    T = figure(mb, {
        "pelvis": (0, 0.12, 0.84), "chest": (0, -0.22, 1.12), "head": (0, -0.42, 1.30), "face": (0, -1, -0.7),
        "sh_l": (-0.22, -0.22, 1.12), "el_l": (-0.36, 0.0, 1.0), "ha_l": (-0.44, 0.22, 1.1),
        "sh_r": (0.22, -0.24, 1.12), "el_r": (0.24, -0.52, 0.94), "ha_r": (0.2, -0.80, 0.74),
        "hip_l": (-0.10, 0.12, 0.82), "kn_l": (-0.12, -0.2, 0.5), "ft_l": (-0.12, -0.1, 0.06),
        "hip_r": (0.10, 0.12, 0.82), "kn_r": (0.12, 0.3, 0.46), "ft_r": (0.12, 0.62, 0.14),
        "toe_r": (0, -0.1, -0.1),
    }, at=(0, 0.25, z), scale=0.66)
    mb.sphere(T((0, -0.4, 1.36)), 0.11, SD, segments=6, rings=3)   # Hair.
    # The toy horse on wheels, lying just out of reach.
    x, y = 0.16, -0.5
    mb.box((x, y, z + 0.16), (0.1, 0.3, 0.1), SL)
    mb.cylinder((x, y - 0.12, z + 0.18), (x, y - 0.2, z + 0.34), 0.045, 0.04, SL, segments=5)
    mb.box((x, y - 0.24, z + 0.34), (0.07, 0.14, 0.07), SL)
    for dy in (-0.1, 0.1):
        mb.cylinder((x - 0.08, y + dy, z + 0.06), (x + 0.08, y + dy, z + 0.06), 0.06, 0.06, SD, segments=6)
    mossy(mb, T, [(-0.1, -0.05, 1.12), (0.12, 0.12, 0.94)])
    scatter(mb, 0.8, 11)
    buildings.export(folder, "decor_petrified_child", mb)


def petrified_archer(folder):
    """An archer with the bow fully drawn, aiming to the front."""
    mb = begin()
    rough_slab(mb, 0.86, 0.1, seed=12)
    z = 0.1
    T = figure(mb, {
        "head": (-0.02, -0.02, 1.66), "face": (-1, -0.25, 0),
        "sh_l": (-0.22, 0, 1.40), "el_l": (-0.50, -0.03, 1.42), "ha_l": (-0.78, -0.05, 1.44),
        "sh_r": (0.22, 0, 1.40), "el_r": (0.36, -0.16, 1.46), "ha_r": (0.04, -0.17, 1.47),
        "kn_l": (-0.22, -0.03, 0.5), "ft_l": (-0.32, 0, 0.06), "toe_l": (-0.15, -0.06, -0.02),
        "kn_r": (0.2, -0.03, 0.5), "ft_r": (0.28, 0, 0.06),
    }, at=(0, 0.12, z), yaw=math.pi / 2)
    # Bow, string and arrow.
    grip = (-0.80, -0.08, 1.44)
    for s in (-1, 1):
        mid = (-0.72, -0.08, 1.44 + s * 0.34)
        tip = (-0.52, -0.08, 1.44 + s * 0.64)
        mb.cylinder(T(grip), T(mid), 0.03, 0.025, SD, segments=5)
        mb.cylinder(T(mid), T(tip), 0.025, 0.012, SD, segments=5)
        mb.cylinder(T(tip), T((0.04, -0.12, 1.47)), 0.008, 0.008, SL, segments=3)
    mb.cylinder(T((0.06, -0.12, 1.47)), T((-0.92, -0.08, 1.45)), 0.014, 0.014, SL, segments=4)
    mb.cylinder(T((-0.92, -0.08, 1.45)), T((-1.0, -0.08, 1.45)), 0.03, 0.004, SL, segments=4)
    # Quiver on the back and a hood.
    mb.cylinder(T((0.12, 0.2, 0.95)), T((-0.12, 0.2, 1.55)), 0.07, 0.08, SD, segments=6)
    mb.cylinder(T((0, 0.03, 1.6)), T((0.02, 0.1, 1.86)), 0.19, 0.03, SD, segments=7)
    taper(mb, 0, 0.12, z + 0.74, z + 1.0, 0.36, 0.3, SD, d0=0.44, d1=0.4)
    mossy(mb, T, [(0.22, 0.02, 1.47), (-0.5, -0.03, 1.5)])
    scatter(mb, 0.8, 12)
    buildings.export(folder, "decor_petrified_archer", mb)


def petrified_smith(folder):
    """A blacksmith with the hammer raised over the anvil."""
    mb = begin()
    rough_slab(mb, 0.86, 0.1, seed=13)
    z = 0.1
    T = figure(mb, {
        "chest": (0, -0.06, 1.40), "head": (0, -0.12, 1.64), "face": (0, -1, -0.4),
        "sh_r": (0.25, -0.04, 1.39), "el_r": (0.42, 0.06, 1.62), "ha_r": (0.34, -0.02, 1.92),
        "sh_l": (-0.25, -0.06, 1.39), "el_l": (-0.30, -0.26, 1.14), "ha_l": (-0.12, -0.50, 1.02),
        "kn_l": (-0.16, -0.14, 0.5), "ft_l": (-0.2, -0.12, 0.06),
        "kn_r": (0.17, 0.08, 0.5), "ft_r": (0.22, 0.2, 0.06),
    }, at=(0, 0.3, z))
    # Hammer.
    mb.cylinder(T((0.34, -0.06, 1.84)), T((0.34, 0.14, 2.24)), 0.025, 0.025, SD, segments=5)
    mb.box(T((0.34, 0.15, 2.26)), (0.12, 0.26, 0.12), SD)
    # Leather apron, as a slab down the front.
    taper(mb, 0, 0.3 - 0.17, z + 0.45, z + 1.3, 0.34, 0.3, SD, d0=0.06, d1=0.06)
    # Anvil on its stump, with a bar held on it.
    ax, ay = -0.05, -0.38
    mb.cylinder((ax, ay, z), (ax, ay, z + 0.5), 0.24, 0.22, SD, segments=8)
    taper(mb, ax, ay, z + 0.5, z + 0.66, 0.2, 0.14, S, d0=0.22, d1=0.16)
    mb.box((ax, ay, z + 0.74), (0.42, 0.2, 0.16), SL)
    mb.cylinder((ax + 0.2, ay, z + 0.76), (ax + 0.46, ay, z + 0.8), 0.08, 0.01, SL, segments=5)
    mb.cylinder(T((-0.12, -0.5, 1.02)), (ax + 0.05, ay, z + 0.84), 0.02, 0.02, SD, segments=4)
    mossy(mb, T, [(-0.24, -0.04, 1.47), (0.1, 0.1, 1.44)])
    moss(mb, ax - 0.12, ay - 0.16, z + 0.3, r=0.12, flat=0.7)
    scatter(mb, 0.8, 13)
    buildings.export(folder, "decor_petrified_smith", mb)


def petrified_dancer(folder):
    """A dancer caught in a turn, one arm over the head and the skirt flared."""
    mb = begin()
    rough_slab(mb, 0.86, 0.1, seed=14)
    z = 0.1
    T = figure(mb, {
        "pelvis": (0.04, 0, 0.95), "chest": (-0.04, 0, 1.42), "head": (-0.1, -0.02, 1.66), "face": (-0.5, -1, 0.3),
        "sh_l": (-0.25, 0, 1.38), "el_l": (-0.42, -0.04, 1.66), "ha_l": (-0.2, -0.08, 1.92),
        "sh_r": (0.17, 0, 1.42), "el_r": (0.46, -0.06, 1.36), "ha_r": (0.72, -0.12, 1.50),
    }, at=(0, 0.05, z), skirt=True, skirt_z=0.35)
    # The skirt lifted by the turn, the legs under it, one on tiptoe.
    mb.cylinder(T((0.04, 0, 0.36)), T((0.04, 0, 0.7)), 0.62, 0.3, SD, segments=9)
    mb.cylinder(T((-0.04, 0, 0.8)), T((-0.06, 0, 0.0)), 0.09, 0.06, S, segments=6)
    mb.cylinder(T((0.14, 0, 0.8)), T((0.3, 0.1, 0.42)), 0.09, 0.07, S, segments=6)
    mb.cylinder(T((0.3, 0.1, 0.42)), T((0.12, 0.2, 0.14)), 0.07, 0.05, S, segments=6)
    # Hair in a bun, a ribbon trailing from the raised hand.
    mb.sphere(T((-0.06, 0.12, 1.76)), 0.09, SD, segments=6, rings=3)
    mb.cylinder(T((0.72, -0.12, 1.5)), T((0.6, 0.2, 1.2)), 0.03, 0.015, SL, segments=4)
    mossy(mb, T, [(0.2, 0.0, 1.5), (-0.3, 0.2, 0.48), (0.4, -0.2, 0.48)])
    scatter(mb, 0.8, 14)
    buildings.export(folder, "decor_petrified_dancer", mb)


def petrified_merchant(folder):
    """A merchant crouched over a sack, looking up at what is coming."""
    mb = begin()
    rough_slab(mb, 0.86, 0.1, seed=15)
    z = 0.1
    T = figure(mb, {
        "pelvis": (0, 0.2, 0.50), "chest": (0, -0.08, 0.90), "head": (0.02, -0.2, 1.13), "face": (0.5, -0.5, 0.7),
        "sh_l": (-0.22, -0.08, 0.90), "el_l": (-0.38, -0.36, 0.72), "ha_l": (-0.14, -0.66, 0.6),
        "sh_r": (0.22, -0.08, 0.90), "el_r": (0.38, -0.36, 0.72), "ha_r": (0.16, -0.66, 0.5),
        "hip_l": (-0.11, 0.2, 0.46), "kn_l": (-0.2, -0.22, 0.10), "ft_l": (-0.16, 0.48, 0.07),
        "hip_r": (0.11, 0.2, 0.46), "kn_r": (0.2, -0.22, 0.10), "ft_r": (0.16, 0.48, 0.07),
        "toe_l": (0, 0.14, -0.02), "toe_r": (0, 0.14, -0.02),
    }, at=(0, 0.1, z))
    # The sack and its tied neck, a coin purse, a wide hat.
    mb.sphere(T((0, -0.42, 0.34)), 0.3, SD, segments=7, rings=5, scale=(1.0, 0.9, 1.1))
    mb.cylinder(T((0, -0.42, 0.62)), T((0.03, -0.45, 0.8)), 0.07, 0.11, SD, segments=6)
    mb.sphere(T((0.42, -0.3, 0.08)), 0.1, SL, segments=5, rings=3)
    mb.cylinder(T((0.02, -0.17, 1.22)), T((0.0, -0.13, 1.26)), 0.3, 0.3, SD, segments=9)
    mb.cylinder(T((0.0, -0.13, 1.26)), T((-0.02, -0.1, 1.4)), 0.16, 0.13, SD, segments=7)
    # Coat over the back.
    mb.cylinder(T((0, 0.44, 0.0)), T((0, 0.0, 0.92)), 0.36, 0.22, S, segments=7)
    mossy(mb, T, [(0.1, 0.12, 0.9), (-0.2, 0.4, 0.5), (0.1, -0.5, 0.64)])
    scatter(mb, 0.8, 15)
    buildings.export(folder, "decor_petrified_merchant", mb)


def petrified_elder(folder):
    """A stooped old man in a long robe, leaning on a staff, a hand raised."""
    mb = begin()
    rough_slab(mb, 0.84, 0.1, seed=16)
    z = 0.1
    T = figure(mb, {
        "pelvis": (0, 0.05, 0.92), "chest": (0, -0.14, 1.30), "head": (0, -0.30, 1.48), "face": (0, -1, 0.1),
        "sh_l": (-0.21, -0.14, 1.29), "el_l": (-0.30, -0.36, 1.18), "ha_l": (-0.22, -0.56, 1.44),
        "sh_r": (0.21, -0.14, 1.29), "el_r": (0.34, -0.22, 1.02), "ha_r": (0.34, -0.48, 1.12),
    }, at=(0, 0.15, z), skirt=True)
    mb.cylinder(T((0.34, -0.5, 0.0)), T((0.34, -0.46, 1.8)), 0.035, 0.03, SD, segments=5)
    mb.sphere(T((0.34, -0.46, 1.84)), 0.07, SD, segments=5, rings=3)
    # Beard, hood and wide sleeves.
    mb.cylinder(T((0, -0.4, 1.44)), T((0, -0.4, 1.08)), 0.1, 0.02, SL, segments=5)
    mb.cylinder(T((0, -0.2, 1.38)), T((0, -0.24, 1.7)), 0.2, 0.1, SD, segments=7)
    mb.cylinder(T((-0.30, -0.36, 1.18)), T((-0.24, -0.5, 1.38)), 0.12, 0.08, SD, segments=6)
    mb.cylinder(T((0.34, -0.22, 1.02)), T((0.34, -0.42, 1.1)), 0.12, 0.08, SD, segments=6)
    mossy(mb, T, [(0.0, 0.0, 1.38), (-0.25, 0.2, 0.3), (0.2, -0.3, 0.2), (0.34, -0.46, 1.9)])
    scatter(mb, 0.8, 16)
    buildings.export(folder, "decor_petrified_elder", mb)


def petrified_deer(folder):
    """A stag turned to stone with one foreleg lifted and the head raised."""
    mb = begin()
    rough_slab(mb, 0.86, 0.1, seed=17)
    z = 0.1
    mb.cylinder((0, 0.42, z + 0.92), (0, -0.2, z + 0.98), 0.2, 0.23, S, segments=8)
    mb.sphere((0, 0.44, z + 0.92), 0.2, S, segments=7, rings=4)
    mb.sphere((0, -0.22, z + 0.99), 0.23, S, segments=7, rings=4)
    mb.cylinder((0, -0.22, z + 1.05), (0, -0.42, z + 1.52), 0.14, 0.09, S, segments=7)
    mb.sphere((0, -0.44, z + 1.56), 0.11, S, segments=6, rings=4)
    mb.cylinder((0, -0.46, z + 1.57), (0, -0.72, z + 1.48), 0.085, 0.045, S, segments=6)
    mb.cylinder((0, 0.6, z + 1.0), (0, 0.72, z + 0.9), 0.05, 0.03, SL, segments=5)
    for s in (-1, 1):
        # Ears and antlers.
        mb.cylinder((s * 0.08, -0.4, z + 1.62), (s * 0.24, -0.34, z + 1.7), 0.04, 0.01, S, segments=4)
        a = (s * 0.06, -0.42, z + 1.64)
        b = (s * 0.2, -0.36, z + 1.92)
        c = (s * 0.34, -0.5, z + 2.18)
        mb.cylinder(a, b, 0.03, 0.025, SL, segments=4)
        mb.cylinder(b, c, 0.025, 0.01, SL, segments=4)
        mb.cylinder(b, (s * 0.16, -0.58, z + 2.02), 0.02, 0.008, SL, segments=4)
        mb.cylinder((s * 0.27, -0.43, z + 2.05), (s * 0.4, -0.34, z + 2.2), 0.018, 0.008, SL, segments=4)
        # Hind legs.
        mb.cylinder((s * 0.12, 0.42, z + 0.9), (s * 0.13, 0.56, z + 0.48), 0.1, 0.05, S, segments=6)
        mb.cylinder((s * 0.13, 0.56, z + 0.48), (s * 0.13, 0.5, z + 0.0), 0.045, 0.035, S, segments=5)
    # Forelegs: one standing, one lifted.
    mb.cylinder((-0.12, -0.2, z + 0.9), (-0.12, -0.2, z + 0.46), 0.08, 0.045, S, segments=6)
    mb.cylinder((-0.12, -0.2, z + 0.46), (-0.12, -0.18, z + 0.0), 0.04, 0.035, S, segments=5)
    mb.cylinder((0.12, -0.2, z + 0.9), (0.12, -0.4, z + 0.58), 0.08, 0.045, S, segments=6)
    mb.cylinder((0.12, -0.4, z + 0.58), (0.12, -0.3, z + 0.26), 0.04, 0.035, S, segments=5)
    moss(mb, 0.0, 0.2, z + 1.16, r=0.16, flat=0.3)
    moss(mb, 0.0, -0.15, z + 1.2, r=0.1, mat="stat_moss_dark", flat=0.4)
    moss(mb, 0.1, 0.5, z + 1.08, r=0.1, mat="stat_moss_dark", flat=0.4)
    scatter(mb, 0.8, 17)
    buildings.export(folder, "decor_petrified_deer", mb)


def petrified_huddle(folder):
    """Three people huddled together: two adults sheltering a child."""
    mb = begin()
    rough_slab(mb, 1.3, 0.1, seed=18, sides=11)
    z = 0.1
    hug = {
        "chest": (0, -0.16, 1.38), "head": (0, -0.3, 1.58), "face": (0, -1, -0.6),
        "sh_l": (-0.22, -0.16, 1.37), "el_l": (-0.42, -0.42, 1.2), "ha_l": (-0.26, -0.72, 1.14),
        "sh_r": (0.22, -0.16, 1.37), "el_r": (0.42, -0.42, 1.26), "ha_r": (0.2, -0.72, 1.3),
        "ft_l": (-0.16, 0.05, 0.06), "ft_r": (0.16, 0.12, 0.06),
    }
    small = {
        "head": (0, -0.04, 1.62), "face": (0, -1, -0.3),
        "el_l": (-0.3, -0.2, 1.2), "ha_l": (-0.1, -0.3, 1.4), "el_r": (0.3, -0.2, 1.2), "ha_r": (0.1, -0.3, 1.46),
    }

    def place(angle, r):
        return (r * math.cos(angle), r * math.sin(angle), z), angle - math.pi / 2

    at, yaw = place(math.radians(150), 0.62)
    a = figure(mb, hug, at=at, yaw=yaw)
    mb.cylinder(a((0, 0.16, 0.2)), a((0, 0.0, 1.4)), 0.34, 0.24, SD, segments=7)   # Cloak.
    at, yaw = place(math.radians(335), 0.66)
    b = figure(mb, hug, at=at, yaw=yaw, skirt=True, mat=SL)
    mb.cylinder(b((0, -0.1, 1.46)), b((0, -0.22, 1.78)), 0.2, 0.1, SD, segments=7)   # Scarf.
    d = figure(mb, small, at=(0.0, -0.12, z), yaw=math.radians(10), scale=0.6, mat=SL)
    mossy(mb, a, [(0.2, -0.1, 1.46), (-0.1, 0.3, 0.7)], r=0.12)
    mossy(mb, b, [(-0.2, -0.14, 1.45), (0.2, 0.3, 0.3)], r=0.12)
    mossy(mb, d, [(0, 0, 1.9)], r=0.07)
    scatter(mb, 1.3, 18, n=7)
    buildings.export(folder, "decor_petrified_huddle", mb)


# --- More monuments ----------------------------------------------------------------------

def flame_pillar(folder):
    """A pillar carrying a bowl with a flame that never goes out."""
    mb = begin()
    mb.cylinder((0, 0, 0), (0, 0, 0.16), 0.86, 0.86, SD, segments=8)
    mb.cylinder((0, 0, 0.16), (0, 0, 0.34), 0.62, 0.58, S, segments=8)
    mb.cylinder((0, 0, 0.34), (0, 0, 0.5), 0.4, 0.34, SL, segments=8)
    mb.cylinder((0, 0, 0.5), (0, 0, 2.0), 0.26, 0.22, S, segments=8)
    for zz in (0.9, 1.6):
        mb.cylinder((0, 0, zz), (0, 0, zz + 0.07), 0.275, 0.27, SD, segments=8)
    mb.cylinder((0, 0, 2.0), (0, 0, 2.12), 0.24, 0.36, SL, segments=8)
    mb.cylinder((0, 0, 2.12), (0, 0, 2.42), 0.3, 0.62, "stat_bronze", segments=10)
    mb.cylinder((0, 0, 2.40), (0, 0, 2.44), 0.56, 0.56, "charcoal", segments=10)
    # The flame: three tongues.
    mb.cylinder((0, 0, 2.42), (0.02, 0, 3.1), 0.26, 0.02, "stat_flame", segments=6)
    mb.cylinder((0.16, 0.08, 2.42), (0.24, 0.1, 2.84), 0.15, 0.01, "stat_flame_core", segments=5)
    mb.cylinder((-0.14, -0.1, 2.42), (-0.22, -0.14, 2.92), 0.16, 0.01, "stat_flame_core", segments=5)
    mb.cylinder((-0.05, 0.16, 2.42), (-0.08, 0.26, 2.74), 0.12, 0.01, "stat_flame", segments=5)
    moss(mb, 0.5, -0.4, 0.17, r=0.16)
    moss(mb, -0.4, 0.3, 0.35, r=0.14, mat="stat_moss_dark")
    buildings.export(folder, "decor_flame_pillar", mb)


def memorial_wall(folder):
    """A wall of dressed stone with bronze plaques and a wreath."""
    mb = begin()
    mb.box((0, 0.2, 0.08), (2.7, 1.5, 0.16), SD)
    mb.box((0, 0.5, 0.26), (2.5, 0.7, 0.2), S)
    mb.box((0, 0.55, 1.3), (2.3, 0.4, 1.9), SL)
    mb.box((0, 0.55, 2.3), (2.44, 0.5, 0.14), S)
    extrude(mb, [(-0.7, 0.35, 2.37), (0.7, 0.35, 2.37), (0, 0.35, 2.75)], (0, 0.4, 0), S)
    for s in (-1, 1):
        mb.box((s * 1.18, 0.5, 1.3), (0.26, 0.56, 1.92), S)
        mb.cylinder((s * 1.18, 0.5, 2.37), (s * 1.18, 0.5, 2.5), 0.12, 0.16, SD, segments=6)
        mb.sphere((s * 1.18, 0.5, 2.6), 0.14, SL, segments=6, rings=4)
        mb.box((s * 0.62, 0.34, 1.35), (0.56, 0.04, 1.1), "stat_bronze")
        for k in range(5):
            mb.box((s * 0.62, 0.315, 1.72 - k * 0.19), (0.42, 0.02, 0.05), SD)
    mb.box((0, 0.34, 1.55), (0.46, 0.04, 0.7), "stat_bronze")
    for k in range(3):
        mb.box((0, 0.315, 1.72 - k * 0.17), (0.32, 0.02, 0.05), SD)
    # A wreath leaning on the wall and candles on the step.
    n = 8
    for i in range(n):
        a = 2 * math.pi * i / n
        mb.sphere((0.26 * math.cos(a), 0.26 - 0.03 * math.sin(a), 0.72 + 0.26 * math.sin(a)), 0.09,
                  "leaves" if i % 3 else "flowers", segments=5, rings=3)
    for x in (-0.8, -0.6, 0.7):
        mb.cylinder((x, 0.02, 0.16), (x, 0.02, 0.34), 0.035, 0.035, "cloth_white", segments=5)
        mb.sphere((x, 0.02, 0.38), 0.035, "stat_flame_core", segments=4, rings=3)
    moss(mb, 1.1, 0.0, 0.17, r=0.2)
    moss(mb, -1.18, 0.5, 2.38, r=0.14, mat="stat_moss_dark")
    moss(mb, -1.0, -0.3, 0.17, r=0.16, mat="stat_moss_dark")
    for v in mb.bm.verts:   # Built off-center; put it in the middle of the plot.
        v.co.y -= 0.2
    buildings.export(folder, "decor_memorial_wall", mb)


def wings(mb, T, mat, spread=1.0):
    """Two feathered wings rising from the shoulder blades of a figure."""
    for s in (-1, 1):
        y = 0.2
        root = (s * 0.08, y, 1.3)
        extrude(mb, [T(root), T((s * 0.5 * spread, y + 0.1, 2.05)), T((s * 0.78 * spread, y + 0.12, 1.9)),
                     T((s * 0.62 * spread, y + 0.1, 1.2))], (0, 0.06, 0), mat)
        extrude(mb, [T((s * 0.16, y, 1.1)), T((s * 0.62 * spread, y + 0.1, 1.2)), T((s * 0.66 * spread, y + 0.14, 0.62)),
                     T((s * 0.3, y + 0.04, 0.5))], (0, 0.05, 0), mat)


def angel(folder):
    """An angel with open wings and joined hands, on a round plinth."""
    mb = begin()
    mb.cylinder((0, 0, 0), (0, 0, 0.18), 0.86, 0.84, SD, segments=10)
    mb.cylinder((0, 0, 0.18), (0, 0, 0.36), 0.62, 0.58, S, segments=10)
    mb.cylinder((0, 0, 0.36), (0, 0, 1.1), 0.44, 0.4, SL, segments=8)
    mb.cylinder((0, 0, 1.1), (0, 0, 1.2), 0.5, 0.5, S, segments=8)
    mb.box((0, -0.4, 0.74), (0.36, 0.04, 0.3), "stat_bronze")
    z = 1.2
    T = figure(mb, {
        "head": (0, -0.05, 1.66), "face": (0, -1, -0.4),
        "el_l": (-0.28, -0.14, 1.14), "ha_l": (-0.03, -0.3, 1.3),
        "el_r": (0.28, -0.14, 1.14), "ha_r": (0.03, -0.3, 1.3),
    }, at=(0, -0.02, z), mat=SL, skirt=True)
    wings(mb, T, S)
    mb.cylinder(T((0, -0.02, 1.52)), T((0, 0.04, 1.84)), 0.19, 0.14, S, segments=7)   # Hair.
    for i in range(8):   # Halo.
        a0 = 2 * math.pi * i / 8
        a1 = 2 * math.pi * (i + 1) / 8
        mb.cylinder(T((0.17 * math.cos(a0), 0.17 * math.sin(a0), 1.92)), T((0.17 * math.cos(a1), 0.17 * math.sin(a1), 1.92)),
                    0.018, 0.018, "stat_bronze", segments=4)
    moss(mb, 0.5, -0.45, 0.19, r=0.16)
    moss(mb, -0.3, 0.4, 0.37, r=0.14, mat="stat_moss_dark")
    buildings.export(folder, "decor_angel", mb)


def king_throne(folder):
    """A stone king seated on a high-backed throne, sword across the knees."""
    mb = begin()
    mb.box((0, 0, 0.1), (2.6, 2.6, 0.2), SD)
    mb.box((0, 0.1, 0.32), (2.0, 2.0, 0.24), S)
    # Throne.
    mb.box((0, 0.2, 0.84), (1.3, 1.2, 0.8), S)
    mb.box((0, 0.72, 2.0), (1.3, 0.24, 1.54), S)
    extrude(mb, [(-0.65, 0.6, 2.77), (0.65, 0.6, 2.77), (0, 0.6, 3.2)], (0, 0.24, 0), S)
    for s in (-1, 1):
        mb.box((s * 0.56, 0.1, 1.4), (0.2, 1.0, 0.34), SD)
        mb.sphere((s * 0.56, -0.4, 1.6), 0.12, SL, segments=6, rings=4)
        mb.sphere((s * 0.6, 0.72, 2.86), 0.11, "stat_bronze", segments=6, rings=4)
    k = 1.2
    z = 1.24 - 0.72 * k
    T = figure(mb, {
        "pelvis": (0, 0.12, 0.78), "chest": (0, 0.14, 1.28), "head": (0, 0.1, 1.53),
        "sh_l": (-0.23, 0.14, 1.26), "el_l": (-0.36, 0.0, 1.0), "ha_l": (-0.36, -0.3, 0.98),
        "sh_r": (0.23, 0.14, 1.26), "el_r": (0.36, 0.0, 1.0), "ha_r": (0.3, -0.3, 0.9),
        "hip_l": (-0.12, 0.12, 0.76), "kn_l": (-0.16, -0.36, 0.76), "ft_l": (-0.17, -0.4, 0.3),
        "hip_r": (0.12, 0.12, 0.76), "kn_r": (0.16, -0.36, 0.76), "ft_r": (0.17, -0.4, 0.3),
    }, at=(0, 0.2, z), scale=k, mat=SL)
    mb.box((0, -0.3, z + 0.2 * k), (0.7, 0.4, 0.14), SD)   # Footstool.
    # Crown, beard, cloak over the shoulders and the sword on the knees.
    mb.cylinder(T((0, 0.1, 1.62)), T((0, 0.1, 1.76)), 0.14 * k, 0.18 * k, "stat_bronze", segments=8)
    mb.cylinder(T((0, -0.03, 1.48)), T((0, -0.06, 1.2)), 0.1 * k, 0.02, S, segments=5)
    taper(mb, 0, 0.2 + 0.24 * k, z + 0.8 * k, z + 1.36 * k, 0.8, 0.62, SD, d0=0.16, d1=0.14)
    mb.cylinder(T((0.5, -0.34, 0.9)), T((-0.62, -0.34, 0.9)), 0.04, 0.015, "stat_bronze", segments=4)
    mb.cylinder(T((0.36, -0.34, 0.8)), T((0.36, -0.34, 1.0)), 0.025, 0.025, "stat_bronze", segments=4)
    moss(mb, 0.8, -0.8, 0.21, r=0.2)
    moss(mb, -0.3, 0.72, 3.0, r=0.14, mat="stat_moss_dark")
    moss(mb, -0.9, 0.3, 0.45, r=0.18, mat="stat_moss_dark")
    buildings.export(folder, "decor_king_throne", mb)


def guardian_lions(folder):
    """Two seated stone lions on plinths, guarding the way between them."""
    mb = begin()
    mb.box((0, 0, 0.04), (2.7, 1.9, 0.08), "stat_slab")
    for s in (-1, 1):
        x = s * 0.88
        mb.box((x, 0.1, 0.2), (0.86, 1.5, 0.24), SD)
        mb.box((x, 0.1, 0.5), (0.7, 1.34, 0.4), S)
        mb.box((x, 0.1, 0.73), (0.78, 1.42, 0.08), SL)
        z = 0.77
        # Haunches, body rising to the chest, mane and head.
        mb.sphere((x, 0.42, z + 0.24), 0.3, S, segments=7, rings=4, scale=(1.0, 1.1, 0.9))
        mb.cylinder((x, 0.4, z + 0.3), (x, -0.12, z + 0.78), 0.26, 0.24, S, segments=7)
        mb.sphere((x, -0.16, z + 0.92), 0.3, SD, segments=7, rings=5)
        mb.sphere((x, -0.42, z + 1.0), 0.19, SL, segments=7, rings=4)
        mb.box((x, -0.6, z + 0.94), (0.18, 0.16, 0.14), SL)
        mb.box((x, -0.68, z + 0.97), (0.07, 0.04, 0.05), SD)
        for e in (-1, 1):
            mb.sphere((x + e * 0.14, -0.36, z + 1.17), 0.06, SL, segments=5, rings=3)
            mb.cylinder((x + e * 0.14, -0.2, z + 0.7), (x + e * 0.15, -0.34, z + 0.06), 0.08, 0.06, S, segments=6)
            mb.box((x + e * 0.15, -0.4, z + 0.05), (0.14, 0.22, 0.1), S)
            mb.box((x + e * 0.3, 0.3, z + 0.05), (0.14, 0.4, 0.1), S)
        mb.cylinder((x - s * 0.2, 0.66, z + 0.06), (x - s * 0.34, 0.2, z + 0.06), 0.04, 0.03, S, segments=5)
        mb.sphere((x - s * 0.34, 0.16, z + 0.07), 0.07, SD, segments=5, rings=3)
        moss(mb, x + s * 0.1, 0.5, z + 0.5, r=0.14, flat=0.4)
        moss(mb, x - s * 0.3, -0.5, 0.78, r=0.12, mat="stat_moss_dark")
    moss(mb, 0.0, 0.6, 0.09, r=0.2, mat="stat_moss_dark")
    buildings.export(folder, "decor_guardian_lions", mb)


MODELS_MORE = (petrified_child, petrified_archer, petrified_smith, petrified_dancer, petrified_merchant,
               petrified_elder, petrified_deer, petrified_huddle, flame_pillar, memorial_wall, angel,
               king_throne, guardian_lions)


def petrified_dog(folder):
    """A dog turned to stone while barking, forelegs braced and tail up."""
    mb = begin()
    rough_slab(mb, 0.84, 0.1, seed=21)
    z = 0.1
    mb.cylinder((0, 0.36, z + 0.56), (0, -0.16, z + 0.5), 0.15, 0.18, S, segments=7)
    mb.sphere((0, 0.38, z + 0.56), 0.15, S, segments=6, rings=4)
    mb.sphere((0, -0.18, z + 0.5), 0.18, S, segments=6, rings=4)
    mb.cylinder((0, -0.2, z + 0.56), (0, -0.4, z + 0.8), 0.12, 0.1, S, segments=6)
    mb.sphere((0, -0.42, z + 0.84), 0.13, S, segments=6, rings=4)
    # Open muzzle.
    mb.cylinder((0, -0.46, z + 0.87), (0, -0.7, z + 0.9), 0.08, 0.05, S, segments=5)
    mb.cylinder((0, -0.46, z + 0.8), (0, -0.64, z + 0.74), 0.06, 0.035, SD, segments=5)
    mb.cylinder((0, 0.48, z + 0.62), (0, 0.66, z + 0.96), 0.045, 0.02, S, segments=5)
    for s in (-1, 1):
        mb.cylinder((s * 0.09, -0.36, z + 0.92), (s * 0.15, -0.3, z + 1.08), 0.05, 0.01, SD, segments=4)
        mb.cylinder((s * 0.1, -0.2, z + 0.46), (s * 0.12, -0.42, z + 0.22), 0.06, 0.045, S, segments=5)
        mb.cylinder((s * 0.12, -0.42, z + 0.22), (s * 0.12, -0.5, z + 0.0), 0.045, 0.04, S, segments=5)
        mb.cylinder((s * 0.1, 0.36, z + 0.52), (s * 0.12, 0.5, z + 0.26), 0.08, 0.045, S, segments=5)
        mb.cylinder((s * 0.12, 0.5, z + 0.26), (s * 0.12, 0.42, z + 0.0), 0.045, 0.04, S, segments=5)
    mb.cylinder((0, -0.3, z + 0.66), (0, -0.3, z + 0.72), 0.125, 0.12, SD, segments=6)   # Collar.
    moss(mb, 0, 0.15, z + 0.7, r=0.12, flat=0.35)
    moss(mb, 0, 0.4, z + 0.7, r=0.08, mat="stat_moss_dark", flat=0.4)
    scatter(mb, 0.8, 21, n=7)
    buildings.export(folder, "decor_petrified_dog", mb)


def dragon_statue(folder):
    """A stone dragon coiled on a rock, wings half open, head raised."""
    mb = begin()
    mb.cylinder((0, 0, 0), (0, 0, 0.2), 1.34, 1.3, SD, segments=10)
    mb.sphere((0, 0.1, 0.2), 0.95, "stat_slab", segments=8, rings=4, scale=(1.0, 0.95, 0.55))
    # The body: a spiral of segments from the tail up to the neck.
    pts = []
    n = 12
    for i in range(n + 1):
        t = i / n
        a = math.radians(200) - t * math.radians(400)
        r = 0.95 - 0.6 * t
        pts.append((r * math.cos(a), 0.1 + r * math.sin(a), 0.42 + 0.75 * t * t + 0.25 * t,
                    0.04 + 0.17 * min(1.0, t * 2.5)))
    for i in range(n):
        p, q = pts[i], pts[i + 1]
        mb.cylinder(p[:3], q[:3], p[3], q[3], S, segments=6)
        if i % 2 == 1:   # Spines along the back.
            mb.cylinder((q[0], q[1], q[2] + q[3] * 0.8), (q[0], q[1], q[2] + q[3] + 0.16), 0.05, 0.005, SD, segments=4)
    top = pts[-1]
    neck = (top[0] + 0.05, top[1] - 0.25, top[2] + 0.6)
    mb.cylinder(top[:3], neck, 0.17, 0.12, S, segments=6)
    head = (neck[0], neck[1] - 0.12, neck[2] + 0.06)
    mb.sphere(head, 0.17, S, segments=6, rings=4)
    mb.cylinder(head, (head[0], head[1] - 0.46, head[2] - 0.04), 0.13, 0.07, S, segments=5)
    mb.cylinder((head[0], head[1] - 0.05, head[2] - 0.1), (head[0], head[1] - 0.4, head[2] - 0.2), 0.08, 0.04, SD, segments=5)
    for s in (-1, 1):
        mb.cylinder((head[0] + s * 0.09, head[1] + 0.05, head[2] + 0.1), (head[0] + s * 0.18, head[1] + 0.34, head[2] + 0.3),
                    0.045, 0.008, SL, segments=4)
        # Wings from the upper coil.
        w = (top[0] + s * 0.12, top[1] + 0.1, top[2] + 0.1)
        tip = (s * 1.2, 0.5, top[2] + 0.95)
        mb.cylinder(w, tip, 0.05, 0.015, SD, segments=4)
        extrude(mb, [w, tip, (s * 1.15, 0.75, top[2] + 0.2), (s * 0.7, 0.6, top[2] - 0.1), (s * 0.3, 0.4, top[2] - 0.05)],
                (0, 0.04, 0), S)
        # Forelegs gripping the rock.
        mb.cylinder((s * 0.3, -0.35, 0.95), (s * 0.5, -0.62, 0.62), 0.09, 0.06, S, segments=5)
        mb.box((s * 0.52, -0.68, 0.58), (0.18, 0.22, 0.1), SD)
    moss(mb, 0.9, -0.7, 0.22, r=0.22)
    moss(mb, -0.6, -0.5, 0.56, r=0.2, mat="stat_moss_dark")
    moss(mb, -1.0, 0.5, 0.22, r=0.18, mat="stat_moss_dark")
    moss(mb, 0.3, 0.9, 0.42, r=0.16)
    buildings.export(folder, "decor_dragon_statue", mb)


MODELS_MORE = MODELS_MORE + (petrified_dog, dragon_statue)


MODELS = (petrified_runner, petrified_kneeling, petrified_warrior, petrified_mother, petrified_pair,
          petrified_sunken, obelisk, stone_arch, totem_pole, roadside_shrine, wayside_cross, hero_statue,
          sundial)


def make_all(folder):
    os.makedirs(folder, exist_ok=True)
    for model in MODELS + MODELS_MORE:
        model(folder)


if __name__ == "__main__":
    if "--" in sys.argv:
        make_all(sys.argv[sys.argv.index("--") + 1])
