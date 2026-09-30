"""Pig studies: the same low-poly pig built with different modeling
techniques, so one can be chosen for the game.

    blender --background --factory-startup --python art/blender/pig_studies.py -- <output folder>

Every version shares the same proportions (PIG below), palette and
conventions as the other animals: meters, standing on Z = 0, head toward -Y.
"""

import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import common  # noqa: E402
from common import MeshBuilder  # noqa: E402

COLORS = {
    "pig": common.rgb(0xF2A0AC),
    "pig_light": common.rgb(0xF7B4BE),
    "pig_shade": common.rgb(0xE38E9B),
    "snout": common.rgb(0xE07F8E),
    "nostril": common.rgb(0x8A3A48),
    "hoof": common.rgb(0x9A5A62),
    "eye": common.rgb(0x151012),
}

# Shared proportions: (center, radii) ellipsoids and leg positions.
BODY = ((0.0, 0.08, 0.47), (0.28, 0.45, 0.27))
HEAD = ((0.0, -0.40, 0.54), (0.21, 0.19, 0.2))
SNOUT_A, SNOUT_B, SNOUT_R = (0.0, -0.54, 0.49), (0.0, -0.68, 0.47), 0.095
LEG_X, LEG_Y, LEG_TOP, LEG_R = (-0.14, 0.14), (-0.2, 0.34), 0.36, 0.065
HOOF_TOP = 0.06
EYE = (0.1, -0.555, 0.6)


# ---------------------------------------------------------------- details

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


def ears(mb, mat="pig"):
    for s in (-1, 1):
        flap(mb, (s * 0.05, -0.41, 0.71), (s * 0.18, -0.35, 0.65), (s * 0.19, -0.53, 0.84), 0.03, mat)


def tail(mb, mat="pig", r=0.018, segments=5):
    """A small curl: a chain of thin cylinders along a helix."""
    pts = []
    for i in range(10):
        t = i / 9.0
        ang = t * math.pi * 2.6
        pts.append((0.045 * math.sin(ang), 0.47 + 0.08 * t + 0.03 * (1 - math.cos(ang)) * 0.5,
                    0.53 + 0.045 * math.cos(ang) - 0.02 * t))
    for p, q in zip(pts, pts[1:]):
        mb.cylinder(p, q, r, r * 0.9, mat, segments=segments)


def eyes_only(mb):
    for s in (-1, 1):
        mb.sphere((s * EYE[0], EYE[1], EYE[2]), 0.024, "eye", segments=6, rings=4)


def face_details(mb, snout_disk=True):
    for s in (-1, 1):
        mb.sphere((s * EYE[0], EYE[1], EYE[2]), 0.024, "eye", segments=6, rings=4)
        mb.sphere((s * 0.035, SNOUT_B[1] - 0.004, SNOUT_B[2] + 0.005), 0.02, "nostril",
                  segments=6, rings=3, scale=(0.8, 0.4, 1.2))
    if snout_disk:
        mb.cylinder((0, SNOUT_B[1] + 0.012, SNOUT_B[2]), (0, SNOUT_B[1] - 0.001, SNOUT_B[2]),
                    SNOUT_R * 1.02, SNOUT_R * 0.98, "snout", segments=10)


def tones(mb, share=0.3, seed=7):
    """Paints some body faces a lighter or darker pink, like the facets of
    the reference picture. Deterministic, so the output is stable."""
    rnd = random.Random(seed)
    pig = mb.materials.index("pig")
    light = mb._material_index("pig_light")
    shade = mb._material_index("pig_shade")
    for f in mb.bm.faces:
        if f.material_index == pig:
            r = rnd.random()
            if r < share * 0.5:
                f.material_index = light
            elif r < share:
                f.material_index = shade


def snout_cap(mb, depth=0.035):
    """Makes the tip of a one-piece snout a flat disk: cuts the surface with
    a plane just behind the tip, flattens everything in front onto that
    plane and paints it the snout color. A glued-on disk would not follow
    the irregular surface, and pink edges would poke through it."""
    bm = mb.bm

    def in_snout(p):
        return abs(p.x) < SNOUT_R * 1.5 and abs(p.z - SNOUT_B[2]) < SNOUT_R * 1.5 and p.y < SNOUT_A[1]

    near = [v for v in bm.verts if in_snout(v.co)]
    cut = min(v.co.y for v in near) + depth
    faces = list({f for v in near for f in v.link_faces})
    geom = list({v for f in faces for v in f.verts}) + list({e for f in faces for e in f.edges}) + faces
    bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, cut, 0), plane_no=(0, 1, 0))
    for v in bm.verts:
        if in_snout(v.co) and v.co.y < cut:
            v.co.y = cut
    bmesh.ops.remove_doubles(bm, verts=[v for v in bm.verts if in_snout(v.co)], dist=1e-4)
    bmesh.ops.dissolve_degenerate(bm, dist=1e-4, edges=list(bm.edges))
    snout = mb._material_index("snout")
    for f in bm.faces:
        if all(in_snout(v.co) and abs(v.co.y - cut) < 1e-4 for v in f.verts):
            f.material_index = snout
    for s in (-1, 1):
        mb.sphere((s * 0.035, cut - 0.002, SNOUT_B[2] + 0.005), 0.02, "nostril",
                  segments=6, rings=3, scale=(0.8, 0.4, 1.2))


def classify(center):
    """Material of a face of a one-piece pig surface, by where it is."""
    c = Vector(center)
    if c.z < HOOF_TOP:
        return "hoof"
    return "pig"  # The snout tip is painted by snout_cap().


def add_mesh(mb, mesh, material_of=classify):
    """Copies a Blender mesh into the builder with flat faces."""
    verts = [mb.bm.verts.new(v.co) for v in mesh.vertices]
    for poly in mesh.polygons:
        fv = [verts[i] for i in poly.vertices]
        if len(set(fv)) < 3 or mb.bm.faces.get(fv) is not None:
            continue  # Decimation can leave doubled faces; one copy is enough.
        f = mb.bm.faces.new(fv)
        f.material_index = mb._material_index(material_of(poly.center))
        f.smooth = False
    return verts


def evaluated_mesh(obj):
    """The mesh of an object after its modifiers (or a metaball's surface)."""
    dg = bpy.context.evaluated_depsgraph_get()
    mesh = bpy.data.meshes.new_from_object(obj.evaluated_get(dg))
    return mesh


def primitive_union(mb, segments=16, rings=10):
    """The pig as overlapping smooth-ish primitives (input for remeshing)."""
    mb.sphere(BODY[0], 1.0, "pig", segments=segments, rings=rings, scale=BODY[1])
    mb.sphere(HEAD[0], 1.0, "pig", segments=segments, rings=rings, scale=HEAD[1])
    mb.cylinder(SNOUT_A, SNOUT_B, SNOUT_R, SNOUT_R, "pig", segments=segments)
    for x in LEG_X:
        for y in LEG_Y:
            mb.cylinder((x, y, 0), (x, y, LEG_TOP + 0.08), LEG_R * 0.9, LEG_R * 1.15, "pig", segments=10)


def temp_object(name, mb):
    obj = mb.to_object(name, COLORS)
    return obj


# ------------------------------------------------------------- techniques

def v01_primitives():
    """Primitive assembly: low-segment spheres and cylinders overlapping,
    the same way as the current deer, boar, wolf and bear."""
    mb = MeshBuilder()
    mb.sphere(BODY[0], 1.0, "pig", segments=10, rings=7, scale=BODY[1])
    mb.sphere(HEAD[0], 1.0, "pig", segments=9, rings=6, scale=HEAD[1])
    mb.cylinder(SNOUT_A, SNOUT_B, SNOUT_R, SNOUT_R * 0.95, "snout", segments=8)
    for x in LEG_X:
        for y in LEG_Y:
            mb.cylinder((x, y, HOOF_TOP), (x, y, LEG_TOP + 0.05), LEG_R * 0.9, LEG_R * 1.1, "pig", segments=6)
            mb.cylinder((x, y, 0), (x, y, HOOF_TOP), LEG_R * 0.95, LEG_R * 0.9, "hoof", segments=6)
    ears(mb)
    tail(mb)
    face_details(mb, snout_disk=False)
    return mb


def hull_points(center, radii, count, rnd, flatten_bottom=None):
    pts = []
    golden = math.pi * (3 - math.sqrt(5))
    for i in range(count):
        z = 1 - 2 * (i + 0.5) / count
        r = math.sqrt(1 - z * z)
        a = i * golden + rnd.uniform(-0.25, 0.25)
        p = Vector((r * math.cos(a), r * math.sin(a), z))
        p *= rnd.uniform(0.94, 1.04)
        q = Vector((center[0] + p.x * radii[0], center[1] + p.y * radii[1], center[2] + p.z * radii[2]))
        if flatten_bottom is not None:
            q.z = max(q.z, flatten_bottom)
        pts.append(q)
    return pts


def hull(mb, points, mat):
    tmp = bmesh.new()
    verts = [tmp.verts.new(p) for p in points]
    res = bmesh.ops.convex_hull(tmp, input=verts)
    bmesh.ops.delete(tmp, geom=[v for v in res["geom_interior"] if isinstance(v, bmesh.types.BMVert)],
                     context="VERTS")
    faces = [f for f in tmp.faces]
    mapping = {v: mb.bm.verts.new(v.co) for v in tmp.verts}
    new = []
    for f in faces:
        new.append(mb.bm.faces.new([mapping[v] for v in f.verts]))
    tmp.free()
    return mb._finish(list(mapping.values()), mat, None)


def v02_convex_hulls():
    """Convex hulls of scattered points: every part is a faceted 'gem' with
    irregular triangles, like paper craft."""
    rnd = random.Random(3)
    mb = MeshBuilder()
    hull(mb, hull_points(BODY[0], BODY[1], 46, rnd), "pig")
    hull(mb, hull_points(HEAD[0], HEAD[1], 26, rnd), "pig")
    snout = [Vector(SNOUT_A) + Vector((math.cos(a) * SNOUT_R, 0, math.sin(a) * SNOUT_R))
             for a in [i * math.tau / 7 + 0.2 for i in range(7)]]
    snout += [Vector(SNOUT_B) + Vector((math.cos(a) * SNOUT_R, 0, math.sin(a) * SNOUT_R))
              for a in [i * math.tau / 7 for i in range(7)]]
    hull(mb, snout, "snout")
    for x in LEG_X:
        for y in LEG_Y:
            pts = []
            for z, r in ((HOOF_TOP, LEG_R * 0.9), (LEG_TOP * 0.55, LEG_R), (LEG_TOP + 0.08, LEG_R * 1.25)):
                for i in range(5):
                    a = i * math.tau / 5 + rnd.uniform(-0.3, 0.3)
                    pts.append(Vector((x + math.cos(a) * r, y + math.sin(a) * r, z)))
            hull(mb, pts, "pig")
            hoof = [Vector((x + math.cos(a) * LEG_R * 0.95, y + math.sin(a) * LEG_R * 0.95, z))
                    for z in (0.0, HOOF_TOP) for a in [i * math.tau / 5 for i in range(5)]]
            hull(mb, hoof, "hoof")
    ears(mb)
    tail(mb, segments=4)
    face_details(mb, snout_disk=False)
    tones(mb, share=0.35)
    return mb


def v03_icospheres():
    """Icosphere parts: evenly sized triangles everywhere, stretched into
    ellipsoids, with a slight jitter so the light breaks on the facets."""
    rnd = random.Random(5)
    mb = MeshBuilder()

    def ico(center, radii, subdiv, mat):
        m = bmesh.new()
        bmesh.ops.create_icosphere(m, subdivisions=subdiv, radius=1.0)
        mapping = {}
        for v in m.verts:
            p = v.co * rnd.uniform(0.96, 1.03)
            mapping[v] = mb.bm.verts.new((center[0] + p.x * radii[0], center[1] + p.y * radii[1],
                                          center[2] + p.z * radii[2]))
        for f in m.faces:
            mb.bm.faces.new([mapping[v] for v in f.verts])
        m.free()
        mb._finish(list(mapping.values()), mat, None)

    ico(BODY[0], BODY[1], 2, "pig")
    ico(HEAD[0], HEAD[1], 2, "pig")
    ico(((SNOUT_A[0] + SNOUT_B[0]) / 2, (SNOUT_A[1] + SNOUT_B[1]) / 2 - 0.01, SNOUT_B[2]),
        (SNOUT_R, 0.08, SNOUT_R), 1, "snout")
    for x in LEG_X:
        for y in LEG_Y:
            ico((x, y, 0.22), (LEG_R * 1.1, LEG_R * 1.1, 0.2), 1, "pig")
            ico((x, y, 0.04), (LEG_R, LEG_R, 0.04), 1, "hoof")
    ears(mb)
    tail(mb, segments=4)
    face_details(mb, snout_disk=False)
    tones(mb, share=0.3)
    return mb


def v04_metaballs():
    """Metaballs melted into one smooth blob, then decimated: soft joints
    between body, head and legs, like a sculpt reduced to low poly."""
    mball = bpy.data.metaballs.new("pig_mball")
    mball.resolution = 0.03
    mball.render_resolution = 0.03
    mball.threshold = 0.6
    obj = bpy.data.objects.new("pig_mball", mball)
    bpy.context.scene.collection.objects.link(obj)

    def ellipsoid(center, radii, radius=1.0):
        e = mball.elements.new(type="ELLIPSOID")
        e.co = center
        e.radius = radius
        e.size_x, e.size_y, e.size_z = radii
        return e

    def capsule(center, half, radius, axis_rot):
        e = mball.elements.new(type="CAPSULE")
        e.co = center
        e.radius = radius
        e.size_x = half
        e.rotation = axis_rot
        return e

    # A lone element's surface reaches about 0.575 x radius x size; blending
    # adds a little, so the sizes are a bit under the target radii.
    k = 1.0 / 0.575
    ellipsoid(BODY[0], tuple(r * k * 0.93 for r in BODY[1]))
    ellipsoid(HEAD[0], tuple(r * k * 0.9 for r in HEAD[1]))
    down = Vector((1, 0, 0)).rotation_difference(Vector((0, 0, 1)))
    forward = Vector((1, 0, 0)).rotation_difference(Vector((0, 1, 0)))
    capsule((0, (SNOUT_A[1] + SNOUT_B[1]) / 2, SNOUT_B[2] + 0.01), 0.05, SNOUT_R * k * 0.9, forward)
    for x in LEG_X:
        for y in LEG_Y:
            capsule((x, y, 0.2), 0.16, LEG_R * k * 0.95, down)
    bpy.context.view_layer.update()
    mesh = evaluated_mesh(obj)
    bpy.data.objects.remove(obj)

    # Reduce the smooth surface to a few hundred faceted triangles.
    tmp = bpy.data.objects.new("pig_blob", mesh)
    bpy.context.scene.collection.objects.link(tmp)
    dec = tmp.modifiers.new("dec", "DECIMATE")
    dec.decimate_type = "COLLAPSE"
    dec.ratio = 700.0 / max(1, len(mesh.polygons) * 2)
    reduced = evaluated_mesh(tmp)
    bpy.data.objects.remove(tmp)

    mb = MeshBuilder()
    add_mesh(mb, clip_to_ground(reduced))
    ears(mb)
    tail(mb)
    snout_cap(mb)
    eyes_only(mb)
    tones(mb, share=0.25)
    return mb


def clip_to_ground(mesh):
    """Flattens anything under Z = 0 onto the ground (metaballs round the feet)."""
    for v in mesh.vertices:
        if v.co.z < 0.0:
            v.co.z = 0.0
    return mesh


def remeshed(mb_input, voxel, decimate):
    """Voxel-remeshes a pile of primitives into one surface, then applies the
    given decimate settings; returns the resulting mesh."""
    obj = temp_object("pig_union", mb_input)
    rem = obj.modifiers.new("rem", "REMESH")
    rem.mode = "VOXEL"
    rem.voxel_size = voxel
    rem.adaptivity = 0.0
    dec = obj.modifiers.new("dec", "DECIMATE")
    for k, v in decimate.items():
        setattr(dec, k, v)
    tri = obj.modifiers.new("tri", "TRIANGULATE")
    tri.quad_method = "BEAUTY"
    mesh = evaluated_mesh(obj)
    bpy.data.objects.remove(obj)
    return mesh


def v05_remesh_planar():
    """Voxel remesh of the primitives welded into one piece, then 'planar'
    decimation: few large flat facets, a cut-gem look."""
    src = MeshBuilder()
    primitive_union(src)
    mesh = remeshed(src, 0.035, {"decimate_type": "DISSOLVE", "angle_limit": common.radians(28)})
    mb = MeshBuilder()
    add_mesh(mb, clip_to_ground(mesh))
    ears(mb)
    tail(mb)
    snout_cap(mb)
    eyes_only(mb)
    return mb


def v06_remesh_collapse():
    """The same welded remesh, reduced by edge collapse: many even
    triangles, closest to the reference picture."""
    src = MeshBuilder()
    primitive_union(src)
    mesh = remeshed(src, 0.02, {"decimate_type": "COLLAPSE", "ratio": 0.02})
    mb = MeshBuilder()
    add_mesh(mb, clip_to_ground(mesh))
    ears(mb)
    tail(mb)
    snout_cap(mb)
    eyes_only(mb)
    tones(mb, share=0.3)
    return mb


def v07_skin_modifier():
    """Skin modifier: a stick skeleton (spine, neck, legs) with a radius per
    joint, skinned into a quad cage, smoothed once and decimated."""
    joints = {
        "tail": ((0, 0.5, 0.5), (0.1, 0.1)),
        "rump": ((0, 0.34, 0.47), (0.25, 0.24)),
        "belly": ((0, 0.08, 0.46), (0.3, 0.28)),
        "chest": ((0, -0.18, 0.48), (0.27, 0.26)),
        "neck": ((0, -0.36, 0.53), (0.21, 0.2)),
        "head": ((0, -0.5, 0.52), (0.16, 0.16)),
        "snout": ((0, -0.685, 0.47), (0.1, 0.1)),
    }
    edges = [("tail", "rump"), ("rump", "belly"), ("belly", "chest"), ("chest", "neck"),
             ("neck", "head"), ("head", "snout")]
    for i, x in enumerate(LEG_X):
        for j, y in enumerate(LEG_Y):
            top = "chest" if j == 0 else "rump"
            name = f"leg{i}{j}"
            joints[name + "_hip"] = ((x, y, 0.36), (0.08, 0.08))
            joints[name + "_foot"] = ((x, y, 0.0), (0.06, 0.06))
            edges += [(top, name + "_hip"), (name + "_hip", name + "_foot")]
    names = list(joints)
    mesh = bpy.data.meshes.new("pig_skel")
    mesh.from_pydata([joints[n][0] for n in names], [(names.index(a), names.index(b)) for a, b in edges], [])
    obj = bpy.data.objects.new("pig_skel", mesh)
    bpy.context.scene.collection.objects.link(obj)
    skin = obj.modifiers.new("skin", "SKIN")
    skin.branch_smoothing = 0.6
    layer = mesh.skin_vertices[0].data
    for i, n in enumerate(names):
        layer[i].radius = joints[n][1]
        layer[i].use_root = (n == "belly")
    sub = obj.modifiers.new("sub", "SUBSURF")
    sub.levels = 1
    sub.render_levels = 1
    dec = obj.modifiers.new("dec", "DECIMATE")
    dec.decimate_type = "COLLAPSE"
    dec.ratio = 0.45
    result = evaluated_mesh(obj)
    bpy.data.objects.remove(obj)
    mb = MeshBuilder()
    add_mesh(mb, clip_to_ground(result))
    ears(mb)
    tail(mb)
    snout_cap(mb)
    eyes_only(mb)
    return mb


def ring(mb, center, rx, rz, sides, phase=0.0, squash_top=1.0):
    pts = []
    for i in range(sides):
        a = phase + i * math.tau / sides
        z = math.sin(a) * rz
        if z > 0:
            z *= squash_top
        pts.append(mb.bm.verts.new((center[0] + math.cos(a) * rx, center[1], center[2] + z)))
    return pts


def loft(mb, sections, sides, mat, cap_start=True, cap_end=True):
    """Joins rings of vertices (y, z, rx, rz) into a tube along -Y."""
    rings = [ring(mb, (0, y, z), rx, rz, sides, phase=math.pi / sides) for y, z, rx, rz in sections]
    for r0, r1 in zip(rings, rings[1:]):
        for i in range(sides):
            j = (i + 1) % sides
            mb.bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
    if cap_start:
        mb.bm.faces.new(rings[0])
    if cap_end:
        mb.bm.faces.new(list(reversed(rings[-1])))
    return mb._finish([v for r in rings for v in r], mat, None)


def v08_loft():
    """Lofted cross sections: octagonal rings along the spine, the classic
    hand-made game-art way; clean and very light."""
    mb = MeshBuilder()
    body = [
        (0.52, 0.48, 0.08, 0.08),
        (0.47, 0.47, 0.2, 0.2),
        (0.36, 0.47, 0.27, 0.26),
        (0.12, 0.46, 0.29, 0.28),
        (-0.12, 0.47, 0.28, 0.27),
        (-0.28, 0.51, 0.24, 0.23),
        (-0.4, 0.54, 0.21, 0.2),
        (-0.52, 0.53, 0.16, 0.16),
        (-0.56, 0.5, 0.11, 0.11),
    ]
    loft(mb, body, 8, "pig", cap_end=False)
    snout = [(-0.56, 0.49, SNOUT_R, SNOUT_R), (-0.68, 0.47, SNOUT_R, SNOUT_R * 0.95)]
    loft(mb, snout, 8, "snout", cap_start=False)
    for x in LEG_X:
        for y in LEG_Y:
            mb.cylinder((x, y, HOOF_TOP), (x, y, LEG_TOP + 0.1), LEG_R * 0.85, LEG_R * 1.15, "pig", segments=6)
            mb.cylinder((x, y, 0), (x, y, HOOF_TOP), LEG_R * 0.9, LEG_R * 0.85, "hoof", segments=6)
    ears(mb)
    tail(mb, segments=4)
    face_details(mb, snout_disk=False)
    return mb


def v09_box_model():
    """Box modeling: a subdivided cube rounded a little, with the legs,
    head and snout extruded out of its faces."""
    mb = MeshBuilder()
    bm = mb.bm
    mb._material_index("pig")  # Slot 0, used by the cube's faces.
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.subdivide_edges(bm, edges=list(bm.edges), cuts=2, use_grid_fill=True)
    c, r = Vector(BODY[0]), Vector(BODY[1])
    for v in bm.verts:
        p = v.co.copy()
        sphere = p.normalized() * 0.5 * math.sqrt(3) * 0.62
        p = p.lerp(sphere, 0.7)
        v.co = Vector((c.x + p.x * 2 * r.x * 0.95, c.y + p.y * 2 * r.y * 0.92, c.z + p.z * 2 * r.z * 0.95))

    def face_near(target, normal):
        best = None
        for f in bm.faces:
            if f.normal.dot(Vector(normal)) < 0.7:
                continue
            d = (f.calc_center_median() - Vector(target)).length
            if best is None or d < best[0]:
                best = (d, f)
        return best[1]

    def extrude(faces, offset, scale=1.0, flatten=None):
        res = bmesh.ops.extrude_face_region(bm, geom=faces)
        new_verts = [e for e in res["geom"] if isinstance(e, bmesh.types.BMVert)]
        bmesh.ops.delete(bm, geom=faces, context="FACES")
        center = sum((v.co for v in new_verts), Vector()) / len(new_verts)
        for v in new_verts:
            v.co = center + (v.co - center) * scale + Vector(offset)
            if flatten is not None:
                v.co[flatten[0]] = flatten[1]
        new_faces = {f for v in new_verts for f in v.link_faces if all(x in new_verts for x in f.verts)}
        return list(new_faces), new_verts

    bm.normal_update()
    # Legs out of the four bottom corner faces.
    for x in LEG_X:
        for y in LEG_Y:
            f = face_near((x, y, BODY[0][2] - BODY[1][2]), (0, 0, -1))
            faces, vs = extrude([f], (0, 0, 0))
            for v in vs:
                v.co.z = HOOF_TOP
                v.co.x = x + (v.co.x - x) * 0.6
                v.co.y = y + (v.co.y - y) * 0.6
            bm.normal_update()
            faces2, vs2 = extrude(faces, (0, 0, 0))
            for v in vs2:
                v.co.z = 0.0
            for fc in {fc for v in vs2 for fc in v.link_faces}:
                fc.material_index = mb._material_index("hoof")
            bm.normal_update()
    # The head out of the whole front, then the snout out of its middle.
    front = [f for f in bm.faces if f.normal.y < -0.7 and f.calc_center_median().z > 0.3]
    head, hv = extrude(front, (0, -0.16, 0.06), scale=0.78)
    bm.normal_update()
    head2, hv2 = extrude(head, (0, -0.12, 0.0), scale=0.85)
    bm.normal_update()
    mid = face_near((0, -0.7, 0.5), (0, -1, 0))
    snout, sv = extrude([mid], (0, -0.1, -0.03), scale=1.05)
    for fc in {fc for v in sv for fc in v.link_faces}:
        fc.material_index = mb._material_index("snout")
    bm.normal_update()
    for f in bm.faces:
        f.smooth = False
    # Details are placed relative to the extruded head.
    snout_y = min(v.co.y for v in sv)
    snout_z = sum(v.co.z for v in sv) / len(sv)
    for s in (-1, 1):
        mb.sphere((s * 0.035, snout_y - 0.004, snout_z + 0.005), 0.02, "nostril", segments=6, rings=3,
                  scale=(0.8, 0.4, 1.2))
        mb.sphere((s * 0.11, snout_y + 0.12, snout_z + 0.1), 0.024, "eye", segments=6, rings=4)
    ears(mb)
    tail(mb)
    return mb


def sdf_pig(p):
    """Signed distance (approximate) of the pig, for the voxel version."""
    def ell(p, c, r):
        q = Vector(((p.x - c[0]) / r[0], (p.y - c[1]) / r[1], (p.z - c[2]) / r[2]))
        return (q.length - 1.0) * min(r)

    def capsule(p, a, b, r):
        a, b = Vector(a), Vector(b)
        pa, ba = p - a, b - a
        h = max(0.0, min(1.0, pa.dot(ba) / ba.dot(ba)))
        return (pa - ba * h).length - r

    d = min(ell(p, *BODY), ell(p, *HEAD), capsule(p, SNOUT_A, SNOUT_B, SNOUT_R))
    for x in LEG_X:
        for y in LEG_Y:
            d = min(d, capsule(p, (x, y, 0.0), (x, y, LEG_TOP), LEG_R))
    return d


def v10_voxels():
    """Voxels: the shape sampled on a grid of cubes, only the visible faces
    kept; a toy-block look. Eyes, nostrils and hooves are voxels too."""
    size = 0.055
    cells = {}
    xs = range(-6, 7)
    ys = range(-14, 11)
    zs = range(0, 14)
    for i in xs:
        for j in ys:
            for k in zs:
                p = Vector((i * size, j * size, (k + 0.5) * size))
                if sdf_pig(p) < 0.0:
                    cells[(i, j, k)] = "pig"
    for (i, j, k) in list(cells):
        p = Vector((i * size, j * size, (k + 0.5) * size))
        if k == 0:
            cells[(i, j, k)] = "hoof"
        elif p.y < SNOUT_A[1] - 0.02:
            cells[(i, j, k)] = "snout"
    # Front-most cells of the snout at the nostrils, eyes on the head.
    ymin = min(j for (i, j, k) in cells)
    snout_z = round(SNOUT_B[2] / size - 0.5)
    for i in (-1, 1):
        if (i, ymin, snout_z) in cells:
            cells[(i, ymin, snout_z)] = "nostril"
    eye_k = round(EYE[2] / size - 0.5)
    for s in (-1, 1):
        for j in ys:
            i = s * 2
            if (i, j, eye_k) in cells and (i, j - 1, eye_k) not in cells:
                cells[(i, j, eye_k)] = "eye"
                break
    # Ears: small slabs over the head; tail: a short stub.
    head_top = max(k for (i, j, k) in cells if j < -5)
    for s in (-1, 1):
        for di, dj, dk in ((2, -8, 1), (3, -8, 1), (2, -9, 1), (3, -9, 1), (3, -9, 2), (3, -10, 2)):
            cells[(s * di, dj, head_top + dk)] = "pig"
    tail_j = max(j for (i, j, k) in cells if i == 0 and k == 9) + 1
    cells[(0, tail_j, 9)] = "pig"
    cells[(0, tail_j, 10)] = "pig"

    mb = MeshBuilder()
    dirs = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))
    vert_cache = {}

    def vert(ix, iy, iz):
        key = (ix, iy, iz)
        if key not in vert_cache:
            vert_cache[key] = mb.bm.verts.new(((ix - 0.5) * size, (iy - 0.5) * size, iz * size))
        return vert_cache[key]

    for (i, j, k), mat in cells.items():
        for d in dirs:
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
            face.smooth = False
    return mb


VERSIONS = [
    ("pig_01_primitives", v01_primitives),
    ("pig_02_convex_hulls", v02_convex_hulls),
    ("pig_03_icospheres", v03_icospheres),
    ("pig_04_metaballs", v04_metaballs),
    ("pig_05_remesh_planar", v05_remesh_planar),
    ("pig_06_remesh_collapse", v06_remesh_collapse),
    ("pig_07_skin_modifier", v07_skin_modifier),
    ("pig_08_loft", v08_loft),
    ("pig_09_box_model", v09_box_model),
    ("pig_10_voxels", v10_voxels),
]


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = os.path.abspath(args[0] if args else "art/studies/pig")
    only = set(args[1:])
    os.makedirs(out, exist_ok=True)
    for name, build in VERSIONS:
        if only and not any(o in name for o in only):
            continue
        common.reset_scene()
        mb = build()
        obj = mb.to_object(name, COLORS)
        tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
        common.export_glb(os.path.join(out, name + ".glb"), [obj])
        print(f"PIG {name}: {tris} triangles")


main()
