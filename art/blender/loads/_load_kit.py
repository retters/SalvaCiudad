"""Shared pieces of the loads a villager carries (phase 67): logs, boulders,
straps, baskets and food. Not a model itself (its name starts with "_").

Where a load goes (the game pins every load to the `chest` bone; sizes are
for a 1.8 m body and the game scales them for smaller ones):

- A BACK load ("<what>_back") lies wholly on the +Y side of the plane
  Y = 0 (behind the character) and stands on Z = 0. Its `grip`,
  (0, 0, half its height), is the point that touches the middle of the
  character's back: (0, +0.115, 1.32) of a 1.8 m body at rest, that is,
  the start of the chest bone moved back to the surface of the back.
- An ARMS load ("<what>_arms") lies wholly on the -Y side of the plane
  Y = 0 (in front of the character) and stands on Z = 0. Its `grip`,
  (0, 0, ARMS_GRIP_Z), is the point that touches the middle of the chest:
  (0, -0.115, 1.32) of a 1.8 m body at rest. The bottom of the load is then
  just above the hands of the clips carry_walk and carry_idle
  (rigs_human.Humanoid.CARRY_HAND).

In both, the model's up is +Z and its left and right are the character's.
"""

import math
import random

import bmesh
from mathutils import Vector

import common
import studies

# How far above its bottom an arms load touches the middle of the chest.
ARMS_GRIP_Z = 0.14

COLORS = {
    "bark": common.rgb(0x7A5232),
    "bark_shade": common.rgb(0x64422A),
    "wood_end": common.rgb(0xC8A06A),
    "leather": common.rgb(0x6E4428),
    "stone": common.rgb(0x8C8A88),
    "stone_light": common.rgb(0xA3A19E),
    "stone_shade": common.rgb(0x6F6D6C),
    "cloth": common.rgb(0xCDB98E),
    "cloth_shade": common.rgb(0xB39E74),
    "rope": common.rgb(0x8A6A3C),
    "wicker": common.rgb(0xB88E52),
    "wicker_dark": common.rgb(0x8E6A3A),
    "plank": common.rgb(0xB08A5A),
    "plank_dark": common.rgb(0x8A6038),
    "carrot": common.rgb(0xE07A28),
    "tomato": common.rgb(0xC8342A),
    "tomato_light": common.rgb(0xDC4A38),
    "tomato_shade": common.rgb(0xA82A24),
    "leaf": common.rgb(0x4E8A34),
    "leaf_dark": common.rgb(0x3A6C2A),
    "bread": common.rgb(0xD9A45A),
    "bread_dark": common.rgb(0xB67C3A),
}


def colors(*names):
    """The colors of the materials whose name starts with one of `names`."""
    return {k: v for k, v in COLORS.items() if any(k == n or k.startswith(n + "_") for n in names)}


def log(mb, a, b, radius, sides=6, bark="bark", end="wood_end"):
    """A log from a to b: bark around it and pale wood on both cut ends."""
    verts = mb.cylinder(a, b, radius, radius, bark, segments=sides)
    index = mb._material_index(end)
    for f in {f for v in verts for f in v.link_faces}:
        if len(f.verts) == sides:   # The two caps (the sides are quads).
            f.material_index = index
    return verts


def boulder(mb, center, radii, mat, seed, count=16):
    """A faceted stone: the convex hull of points scattered on an ellipsoid,
    its faces in the material and its "_light" and "_shade" tones."""
    rnd = random.Random(seed)
    tmp = bmesh.new()
    verts = [tmp.verts.new(p) for p in studies.ellipsoid_points(center, radii, count, rnd)]
    res = bmesh.ops.convex_hull(tmp, input=verts)
    bmesh.ops.delete(tmp, geom=[v for v in res["geom_interior"] if isinstance(v, bmesh.types.BMVert)],
                     context="VERTS")
    mapping = {v: mb.bm.verts.new(v.co) for v in tmp.verts}
    faces = [mb.bm.faces.new([mapping[v] for v in f.verts]) for f in tmp.faces]
    tmp.free()
    out = mb._finish(list(mapping.values()), mat, None)
    # Tones by where the face is, so the result does not depend on face order.
    light, shade = mb._material_index(mat + "_light"), mb._material_index(mat + "_shade")
    for f in faces:
        c = f.calc_center_median()
        r = math.sin(c.x * 91.7 + c.y * 57.3 + c.z * 133.1 + seed) * 0.5 + 0.5
        if r < 0.25:
            f.material_index = light
        elif r < 0.5:
            f.material_index = shade
    return out


def strap(mb, points, axis, width, thick, mat, closed=True):
    """A flat band along a path of points that lie around a load (a strap,
    a hoop, a basket's handle): `width` along `axis`, standing `thick` out
    from the path, away from the path's center."""
    pts = [Vector(p) for p in points]
    axis = Vector(axis).normalized() * (width * 0.5)
    center = sum(pts, Vector()) / len(pts)
    rows = []
    for p in pts:
        out = p - center
        out -= axis * (out.dot(axis) / axis.dot(axis))
        out = out.normalized() * thick
        rows.append([mb.bm.verts.new(q) for q in (p - axis, p + out - axis, p + out + axis, p + axis)])
    n = len(rows)
    for i in range(n if closed else n - 1):
        a, b = rows[i], rows[(i + 1) % n]
        for k in range(3):   # One edge, the outer face, the other edge.
            mb.bm.faces.new((a[k], a[k + 1], b[k + 1], b[k]))
    if not closed:
        for row in (rows[0], rows[-1]):
            mb.bm.faces.new(row)
    return mb._finish([v for row in rows for v in row], mat, None)


def rect(x, y0, y1, z0, z1, cut=0.0):
    """The corners of a rectangle on the plane X = x, to strap() a load;
    with `cut`, its corners are cut off by that much (round loads)."""
    if not cut:
        return [(x, y0, z0), (x, y1, z0), (x, y1, z1), (x, y0, z1)]
    return [(x, y0 + cut, z0), (x, y1 - cut, z0), (x, y1, z0 + cut), (x, y1, z1 - cut),
            (x, y1 - cut, z1), (x, y0 + cut, z1), (x, y0, z1 - cut), (x, y0, z0 + cut)]


def ring(center, rx, ry, sides, phase=0.0):
    """Points of a horizontal ellipse, to strap() a round load."""
    return [(center[0] + rx * math.cos(phase + i * math.tau / sides),
             center[1] + ry * math.sin(phase + i * math.tau / sides), center[2]) for i in range(sides)]


def lathe(mb, center, rings, sides, squash=1.0, top=None, phase=None):
    """A faceted solid of revolution about Z at `center`: `rings` are
    (radius, height, material of the faces up to the next ring), from the
    bottom up. `squash` flattens it along Y. `top`: material of its lid."""
    phase = math.pi / sides if phase is None else phase
    loops = []
    for r, h, _ in rings:
        loops.append([mb.bm.verts.new((center[0] + r * math.cos(phase + k * math.tau / sides),
                                       center[1] + r * squash * math.sin(phase + k * math.tau / sides),
                                       center[2] + h)) for k in range(sides)])
    faces = []
    for i, (a, b) in enumerate(zip(loops, loops[1:])):
        for k in range(sides):
            j = (k + 1) % sides
            faces.append((mb.bm.faces.new((a[k], a[j], b[j], b[k])), rings[i][2]))
    faces.append((mb.bm.faces.new(list(reversed(loops[0]))), rings[0][2]))
    faces.append((mb.bm.faces.new(loops[-1]), top or rings[-1][2]))
    verts = mb._finish([v for loop in loops for v in loop], rings[0][2], None)
    for f, mat in faces:
        f.material_index = mb._material_index(mat)
    return verts


def crate(mb, center, size, band=0.045):
    """A wooden crate (center of its bottom, size): a box of planks with
    darker posts at its corners and battens around its top and bottom."""
    cx, cy, cz = center
    w, d, h = size
    mb.box((cx, cy, cz + h / 2), (w - 0.016, d - 0.016, h - 0.012), "plank")
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.box((cx + sx * (w - band) / 2, cy + sy * (d - band) / 2, cz + h / 2), (band, band, h), "plank_dark")
    for z in (cz + band / 2, cz + h - band / 2):
        for sy in (-1, 1):
            mb.box((cx, cy + sy * (d - band * 0.5) / 2, z), (w - 2 * band, band * 0.5, band), "plank_dark")


def carrot(mb, base, tip, radius=0.028):
    """A carrot from its leafy end to its point, with a tuft of leaves."""
    base, tip = Vector(base), Vector(tip)
    mb.cylinder(base, tip, radius, 0.004, "carrot", segments=4)
    mb.cylinder(base, base + (base - tip).normalized() * 0.09, 0.012, 0.04, "leaf", segments=4)


def tomato(mb, center, radius=0.045, seed=1):
    return boulder(mb, center, (radius, radius, radius * 0.9), "tomato", seed, count=8)


def bread(mb, a, b, radius=0.05):
    """A loaf from a to b: pale crust with darker ends."""
    a, b = Vector(a), Vector(b)
    d = b - a
    mb.cylinder(a + d * 0.2, a + d * 0.8, radius, radius, "bread", segments=5)
    mb.cylinder(a, a + d * 0.2, radius * 0.5, radius, "bread_dark", segments=5)
    mb.cylinder(a + d * 0.8, b, radius, radius * 0.5, "bread_dark", segments=5)


def greens(mb, base, height=0.14, spread=0.07, mat="leaf"):
    """A bunch of leaves standing up from `base`."""
    base = Vector(base)
    for i, (dx, dy) in enumerate(((1, 0.2), (-0.6, 0.8), (-0.5, -0.9))):
        tip = base + Vector((dx * spread, dy * spread, height * (1.0 - 0.15 * i)))
        side = Vector((-dy, dx, 0)).normalized() * spread * 0.6
        studies.flap(mb, base - side * 0.4, base + side * 0.4 + Vector((0, 0, height * 0.35)), tip, 0.012,
                     mat if i != 1 else mat + "_dark")
