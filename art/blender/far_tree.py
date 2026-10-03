"""The far version of a tree (phase 52): the same tree in a few hundred
triangles, for where it is small on screen.

It is made from the finished model, whatever built it, so every tree gets
one the same way:

  * The big welded pieces (the trunk with its thick branches; a giant's
    faceted canopy) are kept, reduced by edge collapse.
  * The small pieces of the same materials as those (twigs) become three-sided
    spikes of two segments, the largest first, as many as fit.
  * Everything else above the ground (leaves, flowers, fruit, the cores of
    the clumps) is grouped by where it is into a few masses; each mass is a
    faceted ellipsoid of the color of its leaves seen from afar: their
    colors mixed by how much each covers.
  * What lies on the ground (grass, stones, fallen petals) is left out.

Building again gives the same file: nothing here is random but the turn of
each mass, which comes from a seed.
"""

import math
import random

import bmesh
import bpy
from mathutils import Matrix, Vector

import common
import studies

BIG = 60          # An island with this many triangles is a welded piece.
GROUND = 0.3      # Islands that do not rise above this are on the ground (m).
SPIKE = 10        # Triangles of a twig's spike.
MASS = 20         # Triangles of a mass (an icosahedron).
ICO = [(-1, 1.618, 0), (1, 1.618, 0), (-1, -1.618, 0), (1, -1.618, 0), (0, -1, 1.618), (0, 1, 1.618),
       (0, -1, -1.618), (0, 1, -1.618), (1.618, 0, -1), (1.618, 0, 1), (-1.618, 0, -1), (-1.618, 0, 1)]
ICO_FACES = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2),
             (10, 7, 6), (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11),
             (6, 2, 10), (8, 6, 7), (9, 8, 1)]


def islands(bm):
    """The connected pieces of the mesh, as lists of faces."""
    seen = set()
    out = []
    for face in bm.faces:
        if face.index in seen:
            continue
        seen.add(face.index)
        piece, stack = [], [face]
        while stack:
            f = stack.pop()
            piece.append(f)
            for e in f.edges:
                for g in e.link_faces:
                    if g.index not in seen:
                        seen.add(g.index)
                        stack.append(g)
        out.append(piece)
    return out


def tris(faces):
    return sum(len(f.verts) - 2 for f in faces)


def reduce(faces, names, target, out):
    """Adds `faces` to `out`, collapsed to about `target` triangles."""
    tmp = bmesh.new()
    verts = {}
    for f in faces:
        new = tmp.faces.new([verts.setdefault(v.index, tmp.verts.new(v.co)) for v in f.verts])
        new.material_index = f.material_index
    mesh = bpy.data.meshes.new("far_tmp")
    tmp.to_mesh(mesh)
    tmp.free()
    small = studies.decimate_to(mesh, target)
    made = {}
    for p in small.polygons:
        if len(set(p.vertices)) < 3:
            continue
        face = out.bm.faces.new([made.setdefault(i, out.bm.verts.new(small.vertices[i].co)) for i in p.vertices])
        face.material_index = out._material_index(names[p.material_index])
        face.smooth = False
    bpy.data.meshes.remove(small)
    bpy.data.meshes.remove(mesh)


def spike(faces, names, out, foot):
    """A twig as two three-sided segments ending in a point; it starts at
    its end nearer to `foot` (the middle of the trunk, seen from above)."""
    points = list({v.index: v.co.copy() for f in faces for v in f.verts}.values())
    a = max(points, key=lambda p: (p - points[0]).length)
    b = max(points, key=lambda p: (p - a).length)

    def away(p):
        return (p.x - foot.x) ** 2 + (p.y - foot.y) ** 2

    base, tip = (a, b) if away(a) <= away(b) else (b, a)
    axis = tip - base
    length = axis.length
    if length < 1e-4:
        return
    axis /= length
    middle = [p for p in points if 0.35 <= (p - base).dot(axis) / length <= 0.65]
    mid = sum(middle, Vector()) / len(middle) if middle else base + axis * (length * 0.5)
    # A tube's surface is its girth times its length (a three-sided one's
    # girth is 5.2 radii); the foot of a twig is thicker than its middle.
    r0 = max(0.02, 1.3 * sum(f.calc_area() for f in faces) / (5.2 * length))
    side = axis.orthogonal().normalized()
    other = axis.cross(side)

    def ring(center, radius):
        return [out.bm.verts.new(center + (side * math.cos(k * math.tau / 3) + other * math.sin(k * math.tau / 3)) * radius)
                for k in range(3)]

    low, high, top = ring(base, r0), ring(mid, r0 * 0.6), out.bm.verts.new(tip)
    mat = out._material_index(names[faces[0].material_index])
    made = [out.bm.faces.new(list(reversed(low)))]
    for k in range(3):
        j = (k + 1) % 3
        made.append(out.bm.faces.new((low[k], low[j], high[j], high[k])))
        made.append(out.bm.faces.new((high[k], high[j], top)))
    for f in made:
        f.material_index = mat
        f.smooth = False


def masses(faces, count):
    """Groups faces by place into `count` groups (k-means on their centers,
    weighted by area, from the same start every time)."""
    items = [(f.calc_center_median(), f.calc_area(), f.material_index, leafy) for f, leafy in faces]
    items = [it for it in items if it[1] > 0.0]
    if not items:
        return []
    count = max(1, min(count, len(items)))
    # Start: the points farthest from each other.
    centers = [max(items, key=lambda it: (it[0].z, it[0].x, it[0].y))[0].copy()]
    while len(centers) < count:
        centers.append(max(items, key=lambda it: min((it[0] - c).length_squared for c in centers))[0].copy())
    groups = []
    for _ in range(12):
        groups = [[] for _ in centers]
        for it in items:
            groups[min(range(len(centers)), key=lambda i: (it[0] - centers[i]).length_squared)].append(it)
        for i, group in enumerate(groups):
            weight = sum(it[1] for it in group)
            if weight > 0.0:
                centers[i] = sum((it[0] * it[1] for it in group), Vector()) / weight
    out = []
    for center, group in zip(centers, groups):
        weight = sum(it[1] for it in group)
        if weight <= 0.0:
            continue
        radii = Vector([max(0.22, 1.75 * math.sqrt(sum(it[1] * (it[0][k] - center[k]) ** 2 for it in group) / weight))
                        for k in range(3)])
        # The color of the leaves, not of the dark cores under them.
        by_material = {}
        for it in [it for it in group if it[3]] or group:
            by_material[it[2]] = by_material.get(it[2], 0.0) + it[1]
        out.append((center, radii, by_material))
    return out


def mixed(by_material, names, colors, made):
    """The material for a mass: its materials' colors mixed by area, as a
    new material (the same mix gives the same one). `made`: name -> color."""
    total = sum(by_material.values())
    mix = [0.0, 0.0, 0.0]
    for m, area in sorted(by_material.items()):
        c = colors.get(names[m], (0.8, 0.8, 0.8))
        for k in range(3):
            mix[k] += c[k] * area / total
    color = tuple(round(v * 96.0) / 96.0 for v in mix)
    for name, c in made.items():
        if c == color:
            return name
    name = f"far_{len(made) + 1}"
    made[name] = color
    return name


def make(mb, colors, limit=300, seed=1):
    """The far version of the tree in `mb` (not changed): a MeshBuilder, with
    the colors of its own materials (the masses') in `far_colors`."""
    bm = mb.bm
    bm.faces.ensure_lookup_table()
    bm.faces.index_update()
    bm.verts.index_update()
    names = list(mb.materials)
    pieces = islands(bm)
    bark = {i for i, name in enumerate(names) if name.startswith("bark")}

    def thick(p):
        """A piece of bark too thick for a twig: part of a trunk built in
        pieces (a palm's rings). A tube's surface is its girth by its length."""
        if not all(f.material_index in bark for f in p):
            return False
        lo = Vector([min(v.co[k] for f in p for v in f.verts) for k in range(3)])
        hi = Vector([max(v.co[k] for f in p for v in f.verts) for k in range(3)])
        return sum(f.calc_area() for f in p) / (5.2 * max(0.05, (hi - lo).length)) > 0.12

    big = [p for p in pieces if tris(p) >= BIG or thick(p)]
    trunk_materials = {f.material_index for p in big for f in p} | bark
    twigs, foliage = [], []
    for p in pieces:
        if any(p is b for b in big):
            continue
        top = max(v.co.z for f in p for v in f.verts)
        if top < GROUND or all(names[f.material_index] in ("grass", "stone") for f in p):
            continue  # Grass, stones, fallen petals.
        if all(f.material_index in trunk_materials for f in p) and big:
            # Of the trunk's own colors: a twig (or a knot, which makes a short spike).
            twigs.append(p)
            continue
        foliage.append(p)

    out = common.MeshBuilder()
    # A leaf is a small piece; a clump's core, a bigger one.
    leaves = [(f, tris(p) <= 8) for p in foliage for f in p]
    leaf_area = sum(f.calc_area() for f, _ in leaves)
    # The budget: masses first (they are the silhouette of a tree in leaf),
    # then the welded pieces, then twigs with what is left.
    mass_count = 0
    if leaves:
        mass_count = max(3, min((limit * 55 // 100) // MASS, int(round(leaf_area / 6.0)) + 3))
    welded_budget = max(40, (limit - mass_count * MASS) * (70 if twigs else 100) // 100) if big else 0
    area = sum(f.calc_area() for p in big for f in p) or 1.0
    for p in sorted(big, key=lambda p: -tris(p)):
        share = sum(f.calc_area() for f in p) / area
        reduce(p, names, max(12, int(welded_budget * share)), out)

    rnd = random.Random(seed)
    groups = masses(leaves, mass_count)

    def inside(point, own):
        for i, (c, r, _) in enumerate(groups):
            if i != own and sum(((point[k] - c[k]) / r[k]) ** 2 for k in range(3)) < 0.8:
                return True
        return False

    out.far_colors = {}
    for own, (center, radii, by_material) in enumerate(groups):
        material = mixed(by_material, names, colors, out.far_colors)
        rot = Matrix.Rotation(rnd.uniform(0.0, math.tau), 3, "Z")
        pts = []
        for p in ICO:
            d = rot @ Vector(p).normalized()
            pts.append(center + Vector((d.x * radii.x, d.y * radii.y, d.z * radii.z)))
        keep = [f for f in ICO_FACES if not inside((pts[f[0]] + pts[f[1]] + pts[f[2]]) / 3.0, own)]
        verts = {i: out.bm.verts.new(pts[i]) for i in sorted({i for f in keep for i in f})}
        for f in keep:
            face = out.bm.faces.new([verts[i] for i in f])
            face.material_index = out._material_index(material)
            face.smooth = False

    def weight(p):
        lo = Vector([min(v.co[k] for f in p for v in f.verts) for k in range(3)])
        hi = Vector([max(v.co[k] for f in p for v in f.verts) for k in range(3)])
        return (hi - lo).length * sum(f.calc_area() for f in p)

    left = limit - sum(len(f.verts) - 2 for f in out.bm.faces)
    trunk = [v.co for p in big for f in p for v in f.verts]
    foot = sum(trunk, Vector()) / len(trunk) if trunk else Vector()
    for p in sorted(twigs, key=lambda p: (-round(weight(p), 6), p[0].index))[:max(0, left // SPIKE)]:
        spike(p, names, out, foot)
    return out
