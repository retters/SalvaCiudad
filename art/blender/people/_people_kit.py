"""What the characters of the three reference sheets share: faceted
pieces of any material, thin strips, facet tones, distances to the welded
parts of the body and small helpers for symmetric points.

It was repeated in adventurer_man.py, lizardfolk.py and dark_elf_man.py
(D-4411); those modules still hold what only their own group uses, and
pass these names on to the characters that import from them.
"""

import math
import random

import bmesh
from mathutils import Vector

# ------------------------------------------------------------------ pieces


def hull(mb, points, mat):
    """A convex solid around the points, with the given material."""
    tmp = bmesh.new()
    verts = [tmp.verts.new(Vector(p)) for p in points]
    res = bmesh.ops.convex_hull(tmp, input=verts)
    bmesh.ops.delete(tmp, geom=[v for v in res["geom_interior"] if isinstance(v, bmesh.types.BMVert)],
                     context="VERTS")
    mapping = {v: mb.bm.verts.new(v.co) for v in tmp.verts}
    for f in tmp.faces:
        mb.bm.faces.new([mapping[v] for v in f.verts])
    tmp.free()
    return mb._finish(list(mapping.values()), mat, None)


def strip(mb, points, normals, widths, thickness, mat):
    """A thin strip along `points`; at each point its flat side faces
    `normals[i]` and it is `widths[i]` wide (widths may be one number)."""
    pts = [Vector(p) for p in points]
    if not isinstance(widths, (list, tuple)):
        widths = [widths] * len(pts)
    rows = []
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        n = Vector(normals[i]).normalized()
        across = t.cross(n).normalized() * (widths[i] * 0.5)
        off = n * (thickness * 0.5)
        rows.append([mb.bm.verts.new(p + a + o) for a in (-across, across) for o in (off, -off)])
    faces = []
    for r0, r1 in zip(rows, rows[1:]):
        faces += [(r0[0], r0[2], r1[2], r1[0]), (r0[3], r0[1], r1[1], r1[3]),
                  (r0[1], r0[0], r1[0], r1[1]), (r0[2], r0[3], r1[3], r1[2])]
    faces.append((rows[0][0], rows[0][1], rows[0][3], rows[0][2]))
    faces.append((rows[-1][2], rows[-1][3], rows[-1][1], rows[-1][0]))
    for f in faces:
        mb.bm.faces.new(f)
    return mb._finish([v for r in rows for v in r], mat, None)


def ribbon(mb, centers, widths, side_axis, thickness, mat):
    """A strip whose flat faces look the same way all along (side_axis)."""
    return strip(mb, centers, [side_axis] * len(centers), list(widths), thickness, mat)


def tone_faces(mb, mat, share, seed=11):
    """Facet tones for another material (finish() only tones one): turns a
    share of its faces into <mat>_light and <mat>_shade."""
    if mat not in mb.materials:
        return
    rnd = random.Random(seed)
    main = mb.materials.index(mat)
    light, shade = mb._material_index(mat + "_light"), mb._material_index(mat + "_shade")
    for f in mb.bm.faces:
        if f.material_index == main:
            r = rnd.random()
            if r < share * 0.5:
                f.material_index = light
            elif r < share:
                f.material_index = shade


# ------------------------------------------------------------------ the body's parts


def part_distance(part, c):
    """Distance from point c to a welded part (negative inside)."""
    c = Vector(c)
    if part[0] == "ellipsoid":
        center, r = part[1], part[2]
        q = Vector(((c.x - center[0]) / r[0], (c.y - center[1]) / r[1], (c.z - center[2]) / r[2]))
        return (q.length - 1.0) * min(r)
    a, b = Vector(part[1]), Vector(part[2])
    ab = b - a
    t = max(0.0, min(1.0, (c - a).dot(ab) / max(ab.dot(ab), 1e-12)))
    return (c - (a + ab * t)).length - (part[3] + (part[4] - part[3]) * t)


def along(part, c):
    """Where point c is along a capsule part: 0 at its start, 1 at its end."""
    a, b = Vector(part[1]), Vector(part[2])
    ab = b - a
    return (Vector(c) - a).dot(ab) / ab.dot(ab)


# ------------------------------------------------------------------ points


def sym(points):
    """The points plus their mirror images (those with x != 0)."""
    out = []
    for x, y, z in points:
        out.append((x, y, z))
        if x:
            out.append((-x, y, z))
    return out


def sym_y(points):
    """The points plus their mirror images across the XZ plane (y != 0)."""
    out = []
    for x, y, z in points:
        out.append((x, y, z))
        if y:
            out.append((x, -y, z))
    return out


def mirror(p, x):
    """The point with its x times `x` (-1: the other side)."""
    return (p[0] * x, p[1], p[2])


def lerp(a, b, t):
    """The point at share t of the way from a to b."""
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def arc(a0, a1, count):
    """`count` angles in radians from a0 to a1 degrees (0 = +X, -90 = the
    front, 90 = the back; growing counter-clockwise seen from above)."""
    return [math.radians(a0 + (a1 - a0) * i / (count - 1)) for i in range(count)]
