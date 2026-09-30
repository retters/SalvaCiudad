"""Shared helpers for the SalvaCiudad Blender model scripts.

Every model is built from code so it can be regenerated, improved and varied
(decision D-007). Scripts run headless and never touch the user's scenes:

    blender --background --factory-startup --python art/blender/build_all.py -- <output folder>

Conventions (see docs/ARTE.md): meters, Blender Z up, characters face -Y
(glTF +Z after export), models stand on Z = 0.
"""

import json
import math
import struct

import bmesh
import bpy
from mathutils import Matrix, Vector


# Material names that the game recolors per instance with a palette slot.
# Anything else keeps its own base color.
PALETTE_SLOTS = ("skin", "hair", "top", "bottom", "shoes", "belt", "hat", "apron")


def reset_scene():
    """Empties the file so each model starts from the same state."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = 30
    scene.frame_start = 0
    scene.frame_end = 0
    return scene


def material(name, rgb, roughness=0.9):
    """A plain colored material; reused if it already exists."""
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        bsdf.inputs["Base Color"].default_value = (rgb[0], rgb[1], rgb[2], 1.0)
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Metallic"].default_value = 0.0
        mat.diffuse_color = (rgb[0], rgb[1], rgb[2], 1.0)
    return mat


class MeshBuilder:
    """Collects bmesh parts with a material and optional bone weights."""

    def __init__(self):
        self.bm = bmesh.new()
        self.deform = self.bm.verts.layers.deform.verify()
        self.materials = []   # Material names, index = material slot.
        self.groups = []      # Vertex group (bone) names, index = group.

    def _material_index(self, name):
        if name not in self.materials:
            self.materials.append(name)
        return self.materials.index(name)

    def _group_index(self, name):
        if name not in self.groups:
            self.groups.append(name)
        return self.groups.index(name)

    def _finish(self, geom, mat, weights):
        verts = [e for e in geom if isinstance(e, bmesh.types.BMVert)]
        faces = {f for v in verts for f in v.link_faces}
        index = self._material_index(mat)
        for f in faces:
            f.material_index = index
            f.smooth = False
        for v in verts:
            for bone, w in (weights or {}).items():
                v[self.deform][self._group_index(bone)] = w
        return verts

    def sphere(self, center, radius, mat, weights=None, segments=10, rings=7, scale=(1, 1, 1)):
        m = Matrix.Translation(Vector(center)) @ Matrix.Diagonal((*scale, 1.0))
        r = bmesh.ops.create_uvsphere(self.bm, u_segments=segments, v_segments=rings, radius=radius, matrix=m)
        return self._finish(r["verts"], mat, weights)

    def cylinder(self, a, b, r1, r2, mat, weights=None, segments=8):
        """A tapered cylinder from point a to point b."""
        a, b = Vector(a), Vector(b)
        axis = b - a
        rot = Vector((0, 0, 1)).rotation_difference(axis.normalized()).to_matrix().to_4x4()
        m = Matrix.Translation((a + b) * 0.5) @ rot
        r = bmesh.ops.create_cone(self.bm, cap_ends=True, cap_tris=False, segments=segments,
                                  radius1=r1, radius2=r2, depth=axis.length, matrix=m)
        return self._finish(r["verts"], mat, weights)

    def box(self, center, size, mat, weights=None, rotation_z=0.0):
        m = (Matrix.Translation(Vector(center)) @ Matrix.Rotation(rotation_z, 4, "Z")
             @ Matrix.Diagonal((size[0], size[1], size[2], 1.0)))
        r = bmesh.ops.create_cube(self.bm, size=1.0, matrix=m)
        return self._finish(r["verts"], mat, weights)

    def prism(self, points, z0, z1, mat, weights=None):
        """Extrudes a convex polygon (list of (x, y), counter-clockwise) from z0 to z1."""
        bottom = [self.bm.verts.new((x, y, z0)) for x, y in points]
        top = [self.bm.verts.new((x, y, z1)) for x, y in points]
        faces = [self.bm.faces.new(list(reversed(bottom))), self.bm.faces.new(top)]
        n = len(points)
        for i in range(n):
            j = (i + 1) % n
            faces.append(self.bm.faces.new((bottom[i], bottom[j], top[j], top[i])))
        return self._finish(bottom + top, mat, weights)

    def to_object(self, name, colors):
        """Creates the object; `colors` maps material names to RGB."""
        mesh = bpy.data.meshes.new(name)
        bmesh.ops.recalc_face_normals(self.bm, faces=self.bm.faces)
        self.bm.to_mesh(mesh)
        self.bm.free()
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.scene.collection.objects.link(obj)
        for mat_name in self.materials:
            mesh.materials.append(material(mat_name, colors.get(mat_name, (0.8, 0.8, 0.8))))
        for group in self.groups:
            obj.vertex_groups.new(name=group)
        return obj


def select_only(objects):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objects:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]


def export_glb(path, objects, animations=False, extras=False):
    """Exports the given objects with fixed options, so output is reproducible.
    With extras, the objects' custom properties go into the file (node
    "extras"), for data the game reads from the model."""
    select_only(objects)
    bpy.ops.export_scene.gltf(
        filepath=path,
        export_format="GLB",
        use_selection=True,
        export_yup=True,
        export_apply=True,
        export_normals=True,
        export_tangents=False,
        export_materials="EXPORT",
        export_image_format="NONE",
        export_vertex_color="NONE",
        export_extras=extras,
        export_copyright="",
        export_skins=True,
        export_def_bones=False,
        export_rest_position_armature=True,
        export_morph=False,
        export_animations=animations,
        export_animation_mode="ACTIONS",
        export_force_sampling=True,
        export_frame_step=1,
        export_optimize_animation_size=False,
        export_anim_slide_to_zero=True,
        export_current_frame=False,
    )
    canonicalize_triangle_order(path)


def canonicalize_triangle_order(path):
    """Sorts the triangles of every indexed primitive in place.

    Blender's exporter does not keep the same face order between runs;
    the order does not matter for drawing, so a fixed order makes the file
    identical every time (decision D-402). Each triangle is rotated to
    start at its lowest index, which keeps its winding.
    """
    with open(path, "rb") as f:
        data = bytearray(f.read())
    json_len = struct.unpack_from("<I", data, 12)[0]
    doc = json.loads(bytes(data[20:20 + json_len]))
    bin_start = 20 + json_len + 8
    formats = {5121: "B", 5123: "H", 5125: "I"}
    for mesh in doc.get("meshes", []):
        for prim in mesh.get("primitives", []):
            if prim.get("mode", 4) != 4 or "indices" not in prim:
                continue
            acc = doc["accessors"][prim["indices"]]
            view = doc["bufferViews"][acc["bufferView"]]
            fmt = formats[acc["componentType"]]
            offset = bin_start + view.get("byteOffset", 0) + acc.get("byteOffset", 0)
            count = acc["count"]
            idx = struct.unpack_from("<%d%s" % (count, fmt), data, offset)
            tris = [idx[i:i + 3] for i in range(0, count - count % 3, 3)]
            tris = sorted(min(t[k:] + t[:k] for k in range(3)) for t in tris)
            flat = [i for t in tris for i in t]
            struct.pack_into("<%d%s" % (len(flat), fmt), data, offset, *flat)
    with open(path, "wb") as f:
        f.write(bytes(data))


def rgb(hex_color):
    """0xRRGGBB (sRGB) to linear RGB for Blender materials."""
    def lin(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return (lin((hex_color >> 16) & 255), lin((hex_color >> 8) & 255), lin(hex_color & 255))


def radians(deg):
    return deg * math.pi / 180.0
