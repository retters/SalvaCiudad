"""Modeling-technique studies: builds one creature with ten different
low-poly techniques, so the best one can be chosen for each animal.

A creature is described by a Spec (see tiger_studies.py): primitive parts,
a stick skeleton, loft sections, a box-model recipe, a paint function and
the small details (eyes, nose, ears). Every technique builds the main
surface with the material "base"; the surface is cut along the stripe
bands, paint() then gives each face its real material from where it is,
and the details are added on top.

Conventions as the other models: meters, standing on Z = 0, head toward -Y.

build_final() is the production path: technique 06 (remesh + collapse),
chosen by Salvador for every animal, with the triangle limit enforced.
"""

import math
import os
import random

import bmesh
import bpy
from mathutils import Vector

import common
from common import MeshBuilder

K_META = 1.0 / 0.575  # A lone metaball reaches ~0.575 x radius x size.


class Spec:
    name = "creature"
    colors = {}
    ellipsoids = []     # (center, radii)
    capsules = []       # (a, b, radius_a, radius_b)
    skeleton = ({}, [])  # joints {name: (pos, (rx, ry))}, edges [(a, b)], root = first joint
    loft = []           # Main tube sections (y, z, rx, rz), tail end first.
    loft_capsules = []  # Capsules added to the loft tube (legs, tail).
    box = None          # dict: body (center, radii), legs [[(point, radius)...]], head [...], tail [...]
    budget = 1000       # Triangles for the decimated techniques.
    max_tris = 1500     # Limit for the final model, details included (build_final).
    tone_material = None  # Material that gets lighter/darker facets.
    tones = 0.3         # Share of tone_material faces made lighter or darker.
    voxel = 0.05        # Voxel size of the voxel technique (10).
    remesh_voxel = None  # Remesh voxel size; None: about 1/110 of the largest size.
    bands = []          # Stripe bands: (point, normal, half width, region(c, n) -> bool).
    # Single cuts where a color border must be crisp (hooves, socks, a
    # beak's base): (point, normal, region(c, n) -> bool). paint() decides
    # the colors; the cut only makes sure there is an edge there.
    cuts = []
    # Flat caps (snouts, beaks, trunk tips): (base point, outward axis,
    # radius, depth, material). See flat_cap().
    caps = []
    rig = None          # A rigs.Quadruped (or other template): skeleton and animations.

    def paint(self, c, n):
        return "base"

    def details(self, mb):
        pass


# ------------------------------------------------------------------ helpers

def in_band(spec, c, n):
    for p, no, hw, region in spec.bands:
        if abs((c - p).dot(no)) < hw and region(c, n):
            return True
    return False


def cut_bands(mb, spec):
    """Cuts the surface along both edges of every stripe band and along the
    single cuts, so painting by face gives crisp borders on large faces."""
    bm = mb.bm
    bm.normal_update()
    planes = [(p + no * (hw * side), no, region) for p, no, hw, region in spec.bands for side in (-1, 1)]
    cuts = list(spec.cuts) + (spec.rig.cuts() if spec.rig is not None else [])
    planes += [(Vector(p), Vector(no).normalized(), region) for p, no, region in cuts]
    for plane, no, region in planes:
        faces = []
        for f in bm.faces:
            d = [(v.co - plane).dot(no) for v in f.verts]
            if min(d) < 0.0 < max(d) and (region(f.calc_center_median(), f.normal)
                                           or any(region(v.co, f.normal) for v in f.verts)):
                faces.append(f)
        if not faces:
            continue
        geom = list({v for f in faces for v in f.verts}) + list({e for f in faces for e in f.edges}) + faces
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=plane, plane_no=no)
        bm.normal_update()
    # Cuts that graze a vertex leave slivers; merge them away.
    bmesh.ops.dissolve_degenerate(bm, dist=1e-4, edges=list(bm.edges))
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-4)
    bm.normal_update()


def finish(mb, spec, tones=0.0, seed=7, cut=True):
    """Cuts the stripes, paints the 'base' faces, adds facet tones and the
    details."""
    bm = mb.bm
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.normal_update()
    if cut and (spec.bands or spec.cuts or spec.rig is not None):
        cut_bands(mb, spec)
    if "base" in mb.materials:
        base = mb.materials.index("base")
        for f in bm.faces:
            if f.material_index == base:
                f.material_index = mb._material_index(spec.paint(f.calc_center_median(), f.normal))
    # Where each cap ended up, for details placed on it (nostrils).
    mb.cap_centers = [flat_cap(mb, *cap) for cap in spec.caps]
    if tones and spec.tone_material in mb.materials:
        rnd = random.Random(seed)
        main = mb.materials.index(spec.tone_material)
        light = mb._material_index(spec.tone_material + "_light")
        shade = mb._material_index(spec.tone_material + "_shade")
        for f in bm.faces:
            if f.material_index == main:
                r = rnd.random()
                if r < tones * 0.5:
                    f.material_index = light
                elif r < tones:
                    f.material_index = shade
    for f in bm.faces:
        f.smooth = False
    # Vertices from here on are the separate detail pieces; a skeleton
    # binds them whole to one bone (rigs.bind).
    bm.verts.index_update()
    mb.detail_from = len(bm.verts)
    spec.details(mb)
    return mb


def inside(c, center, radii):
    """Whether point c is inside the ellipsoid (center, radii); for paint()."""
    return (((c[0] - center[0]) / radii[0]) ** 2 + ((c[1] - center[1]) / radii[1]) ** 2
            + ((c[2] - center[2]) / radii[2]) ** 2) <= 1.0


def flat_cap(mb, base, axis, radius, depth, mat):
    """Makes the tip of a protrusion a flat disk of another color (a pig's
    snout, a trunk tip): the part of the surface beyond `base` along `axis`
    and within `radius` of the axis is cut `depth` behind its tip, what is in
    front is flattened onto the cut and painted `mat`. Following the real
    surface avoids the edges that poke through a glued-on disk."""
    bm = mb.bm
    base, axis = Vector(base), Vector(axis).normalized()

    def along(p):
        return (p - base).dot(axis)

    def inside_cap(p):
        d = p - base
        return along(p) > 0.0 and (d - axis * d.dot(axis)).length < radius

    near = [v for v in bm.verts if inside_cap(v.co)]
    if not near:
        return None
    cut = max(along(v.co) for v in near) - depth
    faces = list({f for v in near for f in v.link_faces})
    geom = list({v for f in faces for v in f.verts}) + list({e for f in faces for e in f.edges}) + faces
    bmesh.ops.bisect_plane(bm, geom=geom, plane_co=base + axis * cut, plane_no=axis)
    for v in bm.verts:
        if inside_cap(v.co) and along(v.co) > cut:
            v.co -= axis * (along(v.co) - cut)
    bmesh.ops.remove_doubles(bm, verts=[v for v in bm.verts if inside_cap(v.co)], dist=1e-4)
    bmesh.ops.dissolve_degenerate(bm, dist=1e-4, edges=list(bm.edges))
    index = mb._material_index(mat)
    for f in bm.faces:
        if all(inside_cap(v.co) and abs(along(v.co) - cut) < 1e-4 for v in f.verts):
            f.material_index = index
    bm.normal_update()
    return base + axis * cut  # The center of the cap, to place nostrils on.


def plate(mb, points, thickness, mat):
    """A thin flat piece from a convex polygon (wing, fin, leaf, ear...).
    The points should be roughly on one plane, in order around it."""
    pts = [Vector(p) for p in points]
    center = sum(pts, Vector()) / len(pts)
    n = Vector()
    for i in range(len(pts)):
        n += (pts[i] - center).cross(pts[(i + 1) % len(pts)] - center)
    n = n.normalized() * (thickness * 0.5)
    front = [mb.bm.verts.new(p + n) for p in pts]
    back = [mb.bm.verts.new(p - n) for p in pts]
    mb.bm.faces.new(front)
    mb.bm.faces.new(list(reversed(back)))
    for i in range(len(pts)):
        j = (i + 1) % len(pts)
        mb.bm.faces.new((back[i], back[j], front[j], front[i]))
    return mb._finish(front + back, mat, None)


def flap(mb, a, b, tip, thickness, mat):
    """A thin triangular flap (an ear) from the base a-b to the tip."""
    a, b, tip = Vector(a), Vector(b), Vector(tip)
    n = (b - a).cross(tip - a).normalized() * (thickness * 0.5)
    front = [mb.bm.verts.new(p + n) for p in (a, b, tip)]
    back = [mb.bm.verts.new(p - n) for p in (a, b, tip)]
    mb.bm.faces.new(front)
    mb.bm.faces.new(list(reversed(back)))
    for i in range(3):
        j = (i + 1) % 3
        mb.bm.faces.new((back[i], back[j], front[j], front[i]))
    return mb._finish(front + back, mat, None)


def add_mesh(mb, mesh, mat="base"):
    """Copies a Blender mesh into the builder (skipping doubled faces)."""
    verts = [mb.bm.verts.new(v.co) for v in mesh.vertices]
    for poly in mesh.polygons:
        fv = [verts[i] for i in poly.vertices]
        if len(set(fv)) < 3 or mb.bm.faces.get(fv) is not None:
            continue
        f = mb.bm.faces.new(fv)
        f.material_index = mb._material_index(mat)
    return verts


def evaluated_mesh(obj):
    dg = bpy.context.evaluated_depsgraph_get()
    return bpy.data.meshes.new_from_object(obj.evaluated_get(dg))


def with_modifiers(mesh, setup):
    """Runs a mesh through modifiers added by setup(obj); returns the result."""
    obj = bpy.data.objects.new("tmp", mesh)
    bpy.context.scene.collection.objects.link(obj)
    setup(obj)
    out = evaluated_mesh(obj)
    bpy.data.objects.remove(obj)
    return out


def decimate_to(mesh, triangles):
    tris = sum(len(p.vertices) - 2 for p in mesh.polygons)

    def setup(obj):
        dec = obj.modifiers.new("dec", "DECIMATE")
        dec.decimate_type = "COLLAPSE"
        dec.ratio = min(1.0, triangles / max(1, tris))
    return with_modifiers(mesh, setup)


def ground(mesh):
    for v in mesh.vertices:
        v.co.z = max(v.co.z, 0.0)
    return mesh


def capsule_points(a, b):
    return Vector(a), Vector(b)


def sdf(spec, p):
    d = 1e9
    for c, r in spec.ellipsoids:
        q = Vector(((p.x - c[0]) / r[0], (p.y - c[1]) / r[1], (p.z - c[2]) / r[2]))
        d = min(d, (q.length - 1.0) * min(r))
    for a, b, ra, rb in spec.capsules:
        a, b = Vector(a), Vector(b)
        pa, ba = p - a, b - a
        h = max(0.0, min(1.0, pa.dot(ba) / ba.dot(ba)))
        d = min(d, (pa - ba * h).length - (ra + (rb - ra) * h))
    return d


# --------------------------------------------------------------- techniques

def t01_primitives(spec):
    """Primitive assembly: low-segment spheres and tapered cylinders."""
    mb = MeshBuilder()
    for c, r in spec.ellipsoids:
        mb.sphere(c, 1.0, "base", segments=10, rings=7, scale=r)
    for a, b, ra, rb in spec.capsules:
        mb.cylinder(a, b, ra, rb, "base", segments=7)
    return finish(mb, spec)


def hull(mb, points):
    tmp = bmesh.new()
    verts = [tmp.verts.new(p) for p in points]
    res = bmesh.ops.convex_hull(tmp, input=verts)
    bmesh.ops.delete(tmp, geom=[v for v in res["geom_interior"] if isinstance(v, bmesh.types.BMVert)],
                     context="VERTS")
    mapping = {v: mb.bm.verts.new(v.co) for v in tmp.verts}
    for f in tmp.faces:
        mb.bm.faces.new([mapping[v] for v in f.verts])
    tmp.free()
    mb._finish(list(mapping.values()), "base", None)


def ellipsoid_points(c, r, count, rnd):
    golden = math.pi * (3 - math.sqrt(5))
    pts = []
    for i in range(count):
        z = 1 - 2 * (i + 0.5) / count
        s = math.sqrt(1 - z * z)
        a = i * golden + rnd.uniform(-0.25, 0.25)
        k = rnd.uniform(0.94, 1.04)
        pts.append(Vector((c[0] + s * math.cos(a) * r[0] * k, c[1] + s * math.sin(a) * r[1] * k,
                           c[2] + z * r[2] * k)))
    return pts


def ring_points(center, axis, radius, count, phase):
    axis = Vector(axis).normalized()
    u = axis.orthogonal().normalized()
    v = axis.cross(u)
    return [Vector(center) + (u * math.cos(phase + i * math.tau / count)
                              + v * math.sin(phase + i * math.tau / count)) * radius for i in range(count)]


def t02_convex_hulls(spec):
    """Convex hulls of scattered points: irregular paper-craft facets."""
    rnd = random.Random(3)
    mb = MeshBuilder()
    for c, r in spec.ellipsoids:
        area = r[0] * r[1] + r[1] * r[2] + r[0] * r[2]
        hull(mb, ellipsoid_points(c, r, max(14, int(area * 260)), rnd))
    for a, b, ra, rb in spec.capsules:
        a, b = Vector(a), Vector(b)
        pts = []
        for t, r in ((0.0, ra), (0.5, (ra + rb) / 2), (1.0, rb)):
            pts += ring_points(a.lerp(b, t), b - a, r, 5, rnd.uniform(0, 1))
        hull(mb, pts)
    return finish(mb, spec, tones=0.3)


def ico_into(mb, subdiv, transform, rnd):
    m = bmesh.new()
    bmesh.ops.create_icosphere(m, subdivisions=subdiv, radius=1.0)
    mapping = {v: mb.bm.verts.new(transform(v.co * rnd.uniform(0.96, 1.03))) for v in m.verts}
    for f in m.faces:
        mb.bm.faces.new([mapping[v] for v in f.verts])
    m.free()
    mb._finish(list(mapping.values()), "base", None)


def t03_icospheres(spec):
    """Icosphere parts: even triangles everywhere with a slight jitter."""
    rnd = random.Random(5)
    mb = MeshBuilder()
    for c, r in spec.ellipsoids:
        ico_into(mb, 2 if max(r) > 0.15 else 1,
                 lambda p, c=c, r=r: Vector((c[0] + p.x * r[0], c[1] + p.y * r[1], c[2] + p.z * r[2])), rnd)
    for a, b, ra, rb in spec.capsules:
        a, b = Vector(a), Vector(b)
        axis = b - a
        rot = Vector((0, 0, 1)).rotation_difference(axis.normalized()).to_matrix()
        mid, half = (a + b) * 0.5, axis.length * 0.5

        def tf(p, rot=rot, mid=mid, half=half, ra=ra, rb=rb):
            t = (p.z + 1) * 0.5
            r = ra + (rb - ra) * t
            return mid + rot @ Vector((p.x * r, p.y * r, p.z * (half + r * 0.5)))
        ico_into(mb, 1, tf, rnd)
    return finish(mb, spec, tones=0.3)


def t04_metaballs(spec):
    """Metaballs melted into one blob, then decimated: soft joints."""
    mball = bpy.data.metaballs.new("mball")
    mball.resolution = 0.03
    mball.render_resolution = 0.03
    mball.threshold = 0.6
    obj = bpy.data.objects.new("mball", mball)
    bpy.context.scene.collection.objects.link(obj)
    for c, r in spec.ellipsoids:
        e = mball.elements.new(type="ELLIPSOID")
        e.co = c
        e.radius = 1.0
        e.size_x, e.size_y, e.size_z = (x * K_META * 0.92 for x in r)
    for a, b, ra, rb in spec.capsules:
        a, b = Vector(a), Vector(b)
        e = mball.elements.new(type="CAPSULE")
        e.co = (a + b) * 0.5
        e.radius = (ra + rb) * 0.5 * K_META * 0.95
        e.size_x = (b - a).length * 0.5
        e.rotation = Vector((1, 0, 0)).rotation_difference((b - a).normalized())
    bpy.context.view_layer.update()
    mesh = evaluated_mesh(obj)
    bpy.data.objects.remove(obj)
    mb = MeshBuilder()
    add_mesh(mb, ground(decimate_to(mesh, spec.budget)))
    return finish(mb, spec, tones=0.25)


def primitive_union(spec):
    mb = MeshBuilder()
    for c, r in spec.ellipsoids:
        mb.sphere(c, 1.0, "base", segments=18, rings=12, scale=r)
    for a, b, ra, rb in spec.capsules:
        mb.cylinder(a, b, ra, rb, "base", segments=12)
        mb.sphere(a, ra, "base", segments=10, rings=6)
        mb.sphere(b, rb, "base", segments=10, rings=6)
    return mb.to_object("union", {}).data


def bounds(spec):
    lo = [min(c[i] - r[i] for c, r in spec.ellipsoids) if spec.ellipsoids else 1e9 for i in range(3)]
    hi = [max(c[i] + r[i] for c, r in spec.ellipsoids) if spec.ellipsoids else -1e9 for i in range(3)]
    for a, b, ra, rb in spec.capsules:
        for i in range(3):
            lo[i] = min(lo[i], a[i] - ra, b[i] - rb)
            hi[i] = max(hi[i], a[i] + ra, b[i] + rb)
    return Vector(lo), Vector(hi)


def remesh_voxel(spec):
    if spec.remesh_voxel:
        return spec.remesh_voxel
    lo, hi = bounds(spec)
    return min(0.05, max(0.001, max(hi - lo) / 110.0))


def remeshed(spec, voxel, decimate):
    def setup(obj):
        rem = obj.modifiers.new("rem", "REMESH")
        rem.mode = "VOXEL"
        rem.voxel_size = voxel
        rem.adaptivity = 0.0
        dec = obj.modifiers.new("dec", "DECIMATE")
        for k, v in decimate.items():
            setattr(dec, k, v)
        tri = obj.modifiers.new("tri", "TRIANGULATE")
        tri.quad_method = "BEAUTY"
    return with_modifiers(primitive_union(spec), setup)


def t05_remesh_planar(spec):
    """Welded voxel remesh, then planar decimation: few big flat facets."""
    mesh = remeshed(spec, 0.035, {"decimate_type": "DISSOLVE", "angle_limit": common.radians(24)})
    mb = MeshBuilder()
    add_mesh(mb, ground(mesh))
    return finish(mb, spec)


def remesh_collapse_mesh(spec, budget=None):
    mesh = remeshed(spec, remesh_voxel(spec), {"decimate_type": "COLLAPSE", "ratio": 1.0})
    return ground(decimate_to(mesh, budget or spec.budget))


def t06_remesh_collapse(spec, budget=None):
    """Welded voxel remesh reduced by edge collapse: even triangles."""
    mb = MeshBuilder()
    add_mesh(mb, remesh_collapse_mesh(spec, budget))
    return finish(mb, spec, tones=spec.tones)


def t07_skin_modifier(spec):
    """Skin modifier over a stick skeleton, smoothed once and decimated."""
    joints, edges = spec.skeleton
    names = list(joints)
    mesh = bpy.data.meshes.new("skel")
    mesh.from_pydata([joints[n][0] for n in names], [(names.index(a), names.index(b)) for a, b in edges], [])
    obj = bpy.data.objects.new("skel", mesh)
    bpy.context.scene.collection.objects.link(obj)
    skin = obj.modifiers.new("skin", "SKIN")
    skin.branch_smoothing = 0.6
    layer = mesh.skin_vertices[0].data
    for i, n in enumerate(names):
        layer[i].radius = joints[n][1]
        layer[i].use_root = i == 0
    sub = obj.modifiers.new("sub", "SUBSURF")
    sub.levels = 1
    sub.render_levels = 1
    result = evaluated_mesh(obj)
    bpy.data.objects.remove(obj)
    mb = MeshBuilder()
    add_mesh(mb, ground(decimate_to(result, spec.budget)))
    return finish(mb, spec)


def t08_loft(spec):
    """Lofted octagonal sections along the spine, tapered prisms for the
    limbs: the classic hand-made game-art way."""
    mb = MeshBuilder()
    sides = 8
    rings = []
    for y, z, rx, rz in spec.loft:
        rings.append([mb.bm.verts.new((math.cos(a) * rx, y, z + math.sin(a) * rz))
                      for a in [math.pi / sides + i * math.tau / sides for i in range(sides)]])
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(sides):
            j = (i + 1) % sides
            mb.bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
    mb.bm.faces.new(rings[0])
    mb.bm.faces.new(list(reversed(rings[-1])))
    mb._finish([v for r in rings for v in r], "base", None)
    for a, b, ra, rb in spec.loft_capsules:
        mb.cylinder(a, b, ra, rb, "base", segments=6)
    return finish(mb, spec)


def t09_box_model(spec):
    """Box modeling: a subdivided, slightly rounded cube with the legs,
    head and tail extruded out of its faces along paths."""
    mb = MeshBuilder()
    bm = mb.bm
    mb._material_index("base")
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.subdivide_edges(bm, edges=list(bm.edges), cuts=2, use_grid_fill=True)
    (cx, cy, cz), (rx, ry, rz) = spec.box["body"]
    for v in bm.verts:
        p = v.co.copy()
        p = p.lerp(p.normalized() * 0.5 * math.sqrt(3) * 0.62, 0.55)
        v.co = Vector((cx + p.x * 2 * rx, cy + p.y * 2 * ry, cz + p.z * 2 * rz))
    bm.normal_update()

    def face_near(target, normal):
        best = None
        for f in bm.faces:
            if f.normal.dot(Vector(normal)) < 0.6:
                continue
            d = (f.calc_center_median() - Vector(target)).length
            if best is None or d < best[0]:
                best = (d, f)
        return best[1]

    def extrude_path(faces, path):
        for point, radius in path:
            res = bmesh.ops.extrude_face_region(bm, geom=faces)
            new_verts = [e for e in res["geom"] if isinstance(e, bmesh.types.BMVert)]
            bmesh.ops.delete(bm, geom=faces, context="FACES")
            center = sum((v.co for v in new_verts), Vector()) / len(new_verts)
            far = max((v.co - center).length for v in new_verts) or 1.0
            for v in new_verts:
                v.co = Vector(point) + (v.co - center) * (radius / far)
            faces = [f for f in {f for v in new_verts for f in v.link_faces}
                     if all(x in new_verts for x in f.verts)]
            bm.normal_update()
        return faces

    for path in spec.box["legs"]:
        top = path[0][0]
        extrude_path([face_near((top[0], top[1], cz - rz), (0, 0, -1))], path)
    front = [f for f in bm.faces if f.normal.y < -0.6 and f.calc_center_median().z > cz - rz * 0.3]
    extrude_path(front, spec.box["head"])
    extrude_path([face_near((0, cy + ry, cz + rz * 0.4), (0, 1, 0))], spec.box["tail"])
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    return finish(mb, spec)


def t10_voxels(spec):
    """Voxels: the shape sampled on a grid of cubes, each voxel painted."""
    size = spec.voxel
    lo = [min(c[i] - r[i] for c, r in spec.ellipsoids) - 0.3 for i in range(3)]
    hi = [max(c[i] + r[i] for c, r in spec.ellipsoids) + 0.3 for i in range(3)]
    for a, b, ra, rb in spec.capsules:
        for i in range(3):
            lo[i] = min(lo[i], a[i] - ra, b[i] - rb)
            hi[i] = max(hi[i], a[i] + ra, b[i] + rb)
    rng = [range(math.floor(lo[i] / size), math.ceil(hi[i] / size) + 1) for i in range(3)]
    cells = {}
    for i in rng[0]:
        for j in rng[1]:
            for k in range(0, rng[2].stop):
                p = Vector((i * size, j * size, (k + 0.5) * size))
                if sdf(spec, p) < 0.0:
                    cells[(i, j, k)] = p
    e = size * 0.5
    mats = {}
    for key, p in cells.items():
        n = Vector((sdf(spec, p + Vector((e, 0, 0))) - sdf(spec, p - Vector((e, 0, 0))),
                    sdf(spec, p + Vector((0, e, 0))) - sdf(spec, p - Vector((0, e, 0))),
                    sdf(spec, p + Vector((0, 0, e))) - sdf(spec, p - Vector((0, 0, e)))))
        mats[key] = spec.paint(p, n.normalized() if n.length > 0 else Vector((0, 0, 1)))
    mb = MeshBuilder()
    vert_cache = {}

    def vert(ix, iy, iz):
        if (ix, iy, iz) not in vert_cache:
            vert_cache[(ix, iy, iz)] = mb.bm.verts.new(((ix - 0.5) * size, (iy - 0.5) * size, iz * size))
        return vert_cache[(ix, iy, iz)]

    for (i, j, k), mat in mats.items():
        for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
            if (i + d[0], j + d[1], k + d[2]) in cells:
                continue
            axis = [a for a in range(3) if d[a] != 0][0]
            base = [i, j, k]
            if d[axis] > 0:
                base[axis] += 1
            u, v = [a for a in range(3) if a != axis]
            quad = []
            for du, dv in ((0, 0), (1, 0), (1, 1), (0, 1)):
                c = list(base)
                c[u] += du
                c[v] += dv
                quad.append(vert(*c))
            face = mb.bm.faces.new(quad)
            face.material_index = mb._material_index(mat)
    return finish(mb, spec, cut=False)


def t11_painted_faces(spec):
    """Reference: the remesh-collapse surface painted face by face without
    cutting the stripes first, to show what the cuts are worth."""
    mb = MeshBuilder()
    add_mesh(mb, remesh_collapse_mesh(spec))
    return finish(mb, spec, tones=0.3, cut=False)


TECHNIQUES = [
    ("01_primitives", t01_primitives),
    ("02_convex_hulls", t02_convex_hulls),
    ("03_icospheres", t03_icospheres),
    ("04_metaballs", t04_metaballs),
    ("05_remesh_planar", t05_remesh_planar),
    ("06_remesh_collapse", t06_remesh_collapse),
    ("07_skin_modifier", t07_skin_modifier),
    ("08_loft", t08_loft),
    ("09_box_model", t09_box_model),
    ("10_voxels", t10_voxels),
    ("11_painted_faces", t11_painted_faces),
]


def build_all(spec, out, only=()):
    os.makedirs(out, exist_ok=True)
    for suffix, build in TECHNIQUES:
        name = f"{spec.name}_{suffix}"
        if only and not any(o in name for o in only):
            continue
        if suffix == "11_painted_faces" and not spec.bands:
            continue
        common.reset_scene()
        mb = build(spec)
        obj = mb.to_object(name, spec.colors)
        tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
        common.export_glb(os.path.join(out, name + ".glb"), [obj])
        print(f"STUDY {name}: {tris} triangles")


def triangles(mb):
    return sum(len(f.verts) - 2 for f in mb.bm.faces)


def build_final(spec, out):
    """Builds the production model (technique 06) as <out>/<name>.glb,
    lowering the decimation budget until the whole model, stripes and
    details included, fits in spec.max_tris. Returns the triangle count."""
    budget = spec.budget
    for attempt in range(6):
        common.reset_scene()
        mb = t06_remesh_collapse(spec, budget)
        tris = triangles(mb)
        if tris <= spec.max_tris or attempt == 5:
            break
        mb.bm.free()
        budget = int(budget * max(0.5, min(0.95, spec.max_tris / tris)))
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, spec.name + ".glb")
    if spec.rig is not None:
        import rigs
        rigs.export_rigged(spec, mb, path)
    else:
        obj = mb.to_object(spec.name, spec.colors)
        common.export_glb(path, [obj])
    status = "" if tris <= spec.max_tris else f"  OVER THE LIMIT {spec.max_tris}"
    print(f"MODEL {spec.name}: {tris} triangles (budget {budget}){status}")
    return tris
