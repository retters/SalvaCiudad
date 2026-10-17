"""Renders the pictures of the interface mockups (docs/propuestas/interfaz):
building and item thumbnails and villager portraits, from the game's own
models. Runs headless and never touches the user's Blender scenes:

    blender --background --factory-startup --python tools/propuestas/interfaz_miniaturas.py -- jobs.json

jobs.json is a list of {"glb", "out", "kind", "size", "palette", "yaw"};
kind is "building", "item" or "portrait". tools/propuestas/interfaz.py
writes it and runs this script.
"""

import json
import math
import sys

import bpy
from mathutils import Matrix, Vector


def srgb_to_linear(hex_color):
    h = hex_color.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255.0
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return out


def setup_scene(size):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    for engine in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            scene.render.engine = engine
            break
        except TypeError:
            continue
    scene.render.resolution_x = size
    scene.render.resolution_y = size
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.view_settings.view_transform = "Standard"
    world = bpy.data.worlds.new("world")
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.55, 0.6, 0.68, 1.0)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.9
    scene.world = world
    sun = bpy.data.lights.new("sun", "SUN")
    sun.energy = 3.2
    sun.angle = math.radians(8)
    sun_obj = bpy.data.objects.new("sun", sun)
    sun_obj.rotation_euler = (math.radians(50), math.radians(10), math.radians(-35))
    scene.collection.objects.link(sun_obj)
    return scene


def import_model(path, palette):
    bpy.ops.import_scene.gltf(filepath=path)
    meshes = []
    for o in bpy.context.scene.objects:
        if o.type != "MESH":
            continue
        if o.name.startswith("Icosphere"):  # A helper sphere some animals carry: not drawn.
            o.hide_render = True
            continue
        meshes.append(o)
    for o in bpy.context.scene.objects:
        if o.type == "ARMATURE":
            o.data.pose_position = "REST"
    for mat in bpy.data.materials:
        slot = mat.name.split(".")[0].lower()
        if slot in palette and mat.node_tree:
            bsdf = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
            if bsdf:
                bsdf.inputs["Base Color"].default_value = (*srgb_to_linear(palette[slot]), 1.0)
    return meshes


def world_points(meshes):
    deps = bpy.context.evaluated_depsgraph_get()
    pts = []
    for o in meshes:
        ev = o.evaluated_get(deps)
        mesh = ev.to_mesh()
        mw = ev.matrix_world
        pts.extend(mw @ v.co for v in mesh.vertices)
        ev.to_mesh_clear()
    return pts


def head_frame(meshes):
    """Center and size of the head, from the 'head' bone when there is one."""
    for o in bpy.context.scene.objects:
        if o.type == "ARMATURE":
            bone = o.data.bones.get("head")
            if bone:
                a = o.matrix_world @ bone.head_local
                b = o.matrix_world @ bone.tail_local
                return (a + b) * 0.5 + Vector((0, 0, 0.02)), max((b - a).length, 0.18)
    pts = world_points(meshes)
    top = max(p.z for p in pts)
    return Vector((0, 0, top * 0.9)), top * 0.12


def hide_below_ground(scene):
    """Foundations reach under the ground for slopes: a holdout plane at
    Z = 0 leaves them out of the picture."""
    bpy.ops.mesh.primitive_plane_add(size=500.0, location=(0, 0, 0.001))
    plane = bpy.context.active_object
    mat = bpy.data.materials.new("holdout")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    hold = nodes.new("ShaderNodeHoldout")
    mat.node_tree.links.new(hold.outputs[0], out.inputs["Surface"])
    plane.data.materials.append(mat)
    plane.visible_shadow = False


def render(job):
    size = int(job.get("size", 256))
    scene = setup_scene(size)
    meshes = import_model(job["glb"], job.get("palette", {}))
    cam_data = bpy.data.cameras.new("cam")
    cam = bpy.data.objects.new("cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    yaw = math.radians(job.get("yaw", 35))
    kind = job["kind"]
    if kind == "portrait":
        center, head = head_frame(meshes)
        el = math.radians(4)
        d = Vector((math.sin(yaw) * math.cos(el), -math.cos(yaw) * math.cos(el), math.sin(el)))
        cam_data.type = "ORTHO"
        cam_data.ortho_scale = head * 3.0
        cam.location = center + d * 10.0 - Vector((0, 0, head * 0.35))
        cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    else:
        el = math.radians(30 if kind == "building" else 34)
        d = Vector((math.sin(yaw) * math.cos(el), -math.cos(yaw) * math.cos(el), math.sin(el)))
        pts = [p for p in world_points(meshes) if p.z > -0.02] or world_points(meshes)
        if kind == "building":
            hide_below_ground(scene)
        mid = sum(pts, Vector()) / max(1, len(pts))
        rot = (-d).to_track_quat("-Z", "Y")
        cam.rotation_euler = rot.to_euler()
        inv = rot.to_matrix().transposed()
        local = [inv @ (p - mid) for p in pts]
        xs = [p.x for p in local]
        ys = [p.y for p in local]
        w = max(xs) - min(xs)
        h = max(ys) - min(ys)
        cx = (max(xs) + min(xs)) * 0.5
        cy = (max(ys) + min(ys)) * 0.5
        cam_data.type = "ORTHO"
        cam_data.ortho_scale = max(w, h) * 1.1
        cam.location = mid + rot.to_matrix() @ Vector((cx, cy, 0)) + d * 200.0
        cam_data.clip_end = 1000.0
    scene.render.filepath = job["out"]
    bpy.ops.render.render(write_still=True)


def main():
    jobs = json.load(open(sys.argv[sys.argv.index("--") + 1], encoding="utf-8"))
    for job in jobs:
        try:
            render(job)
            print("OK", job["out"])
        except Exception as e:  # One broken model must not stop the rest.
            print("FAILED", job["out"], e)


main()
