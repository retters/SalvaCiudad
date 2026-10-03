"""Renders one review image per model, to look at models without opening
Blender's interface.

    blender --background --factory-startup --python art/blender/study_preview.py -- <models folder> <output folder> [names]

For each <name>.glb in the models folder writes <output>/<name>.png: four
views in a 2 x 2 grid (front, side, three-quarter, and three-quarter with
the triangle edges drawn and the triangle count). A model with a skeleton
also gets <name>_anim.png: one row per animation, 8 frames seen from the
side. Also writes overview.png with the three-quarter view of every model.
With names, only those models (and no overview).
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

args = sys.argv[sys.argv.index("--") + 1:]
MODELS = os.path.abspath(args[0])
OUT = os.path.abspath(args[1])
ONLY = set(args[2:])
PANELS = os.path.join(OUT, "_panels")
os.makedirs(PANELS, exist_ok=True)
NAMES = sorted(f[:-4] for f in os.listdir(MODELS) if f.endswith(".glb") and (not ONLY or f[:-4] in ONLY))

PANEL_W, PANEL_H = 640, 520
STRIP_W, STRIP_H = 400, 325
STRIP_FRAMES = 8
LENS = 55.0  # Millimeters, on a 36 mm wide sensor.

# The tools shown in a character's hand while a clip plays ("<clip>_prop"
# in the model): kind -> (model in art/studies/weapons, degrees the tool is
# turned about its own long axis in the hand).
PROPS = {"axe": ("w07_battle_axe", 90.0), "bow": ("w13_long_bow", 0.0), "rod": ("w18_fishing_rod", 0.0),
         "hammer": ("w33_stone_hammer", 0.0)}
PROPS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "studies", "weapons")

# View name, direction from the model toward the camera, edges drawn.
VIEWS = [
    ("front", Vector((0.0, -1.0, 0.18)), False),
    ("side", Vector((-1.0, 0.0, 0.18)), False),
    ("3/4", Vector((-0.55, -0.85, 0.5)), False),
    ("wire", Vector((-0.55, -0.85, 0.5)), True),
]


def reset(width=PANEL_W, height=PANEL_H):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.fps = 30  # The clips are baked at 30 fps.
    scene.view_settings.view_transform = "Standard"
    world = bpy.data.worlds.new("w")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.42, 0.43, 0.45, 1)
    bg.inputs["Strength"].default_value = 0.9
    scene.world = world
    sun = bpy.data.lights.new("sun", "SUN")
    sun.energy = 3.2
    sun.angle = math.radians(8)
    sun_obj = bpy.data.objects.new("sun", sun)
    sun_obj.rotation_euler = (math.radians(50), math.radians(-10), math.radians(-35))
    scene.collection.objects.link(sun_obj)
    bpy.ops.mesh.primitive_plane_add(size=400)
    plane = bpy.context.active_object
    plane.name = "ground"
    mat = bpy.data.materials.new("ground")
    mat.use_nodes = True
    mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.36, 0.37, 0.39, 1)
    mat.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 1.0
    plane.data.materials.append(mat)


def load(name):
    """Imports a model in its rest pose; returns its mesh objects, its
    vertices (world) and its skeleton (or None)."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(MODELS, name + ".glb"))
    new = [o for o in bpy.data.objects if o not in before]
    arm = next((o for o in new if o.type == "ARMATURE"), None)
    # The importer may add a mesh to draw the bones with; skip it.
    meshes = [o for o in new if o.type == "MESH" and (arm is None or o.parent == arm)]
    if arm is not None:
        arm.animation_data.action = None
        arm.data.pose_position = "REST"
    bpy.context.view_layer.update()
    points = [o.matrix_world @ v.co for o in meshes for v in o.data.vertices]
    return meshes, points, arm


def camera_for(corners, direction, width=PANEL_W, height=PANEL_H):
    """Places a camera looking along -direction that fits all the points,
    leaving room at the bottom for the label."""
    direction = direction.normalized()
    lo = Vector([min(p[i] for p in corners) for i in range(3)])
    hi = Vector([max(p[i] for p in corners) for i in range(3)])
    target = (lo + hi) * 0.5
    forward = -direction
    right = forward.cross(Vector((0, 0, 1))).normalized()
    up = right.cross(forward)
    tan_w = 18.0 / LENS * 0.86
    tan_h = 18.0 / LENS * height / width * 0.78
    dist = 0.0
    for p in corners:
        rel = p - target
        dist = max(dist, rel.dot(direction) + max(abs(rel.dot(right)) / tan_w, abs(rel.dot(up)) / tan_h))
    # Shift the view down a little so the model sits above the label.
    target = target - up * (dist * tan_h * 0.08)
    data = bpy.data.cameras.new("cam")
    data.lens = LENS
    data.clip_start = dist * 0.01
    data.clip_end = dist * 20
    cam = bpy.data.objects.new("cam", data)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = target + direction * dist
    cam.rotation_euler = forward.to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = cam
    return cam, dist


def label(cam, dist, text):
    """White text hanging in front of the camera, at the bottom of the
    frame, closer to the camera than the model so it is never hidden."""
    k = dist * 0.1  # Distance of the text from the camera.
    curve = bpy.data.curves.new("label", "FONT")
    curve.body = text
    curve.size = 0.045 * k
    curve.align_x = "CENTER"
    obj = bpy.data.objects.new("label", curve)
    mat = bpy.data.materials.new("label")
    mat.use_nodes = True
    mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.95, 0.95, 0.95, 1)
    curve.materials.append(mat)
    obj.location = (0, -0.25 * k, -k)
    obj.parent = cam
    obj.visible_shadow = False
    bpy.context.scene.collection.objects.link(obj)
    return obj


def wireframe(meshes, size):
    """Draws the edges of the models as thin dark rods; returns the
    triangle count."""
    mat = bpy.data.materials.new("wire")
    mat.use_nodes = True
    mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.02, 0.02, 0.03, 1)
    tris = 0
    for o in meshes:
        tris += sum(len(p.vertices) - 2 for p in o.data.polygons)
        wire = o.copy()
        wire.data = o.data.copy()
        wire.data.materials.clear()
        wire.data.materials.append(mat)
        mod = wire.modifiers.new("wire", "WIREFRAME")
        mod.thickness = size * 0.0028
        mod.use_even_offset = False  # Even offset blows up on thin triangles.
        mod.use_replace = True
        wire.visible_shadow = False
        bpy.context.scene.collection.objects.link(wire)
    return tris


def render(path):
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


def compose(files, cols, out_path):
    """Tiles same-sized images (left to right, top to bottom) into one."""
    import numpy as np
    tiles = []
    for f in files:
        img = bpy.data.images.load(f)
        w, h = img.size
        tiles.append(np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4))
        bpy.data.images.remove(img)
    rows = math.ceil(len(tiles) / cols)
    sheet = np.empty((rows * h, cols * w, 4), dtype=np.float32)
    sheet[:, :] = tiles[0][h - 1, 0]  # The background color of a corner.
    for i, t in enumerate(tiles):
        r, c = i // cols, i % cols
        y0 = (rows - 1 - r) * h  # Blender images start at the bottom row.
        sheet[y0:y0 + h, c * w:(c + 1) * w] = t
    for c in range(1, cols):  # Thin dark lines between the tiles.
        sheet[:, c * w - 1:c * w + 1, :3] = 0.25
    for r in range(1, rows):
        sheet[r * h - 1:r * h + 1, :, :3] = 0.25
    img = bpy.data.images.new("sheet", cols * w, rows * h, alpha=True)
    img.pixels = sheet.ravel()
    img.filepath_raw = out_path
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)


def panel_path(name, view):
    return os.path.join(PANELS, f"{name}_{view.replace('/', '')}.png")


def evaluated_points(meshes):
    dg = bpy.context.evaluated_depsgraph_get()
    pts = []
    for o in meshes:
        ev = o.evaluated_get(dg)
        m = ev.to_mesh()
        pts += [ev.matrix_world @ v.co for v in m.vertices]
        ev.to_mesh_clear()
    return pts


def attach_prop(arm, spec):
    """Puts a tool in a hand: `spec` is "kind:bone". The tool's long axis
    (its +Z) goes along the hand's forward direction (-Y at rest), with
    its grip point at the middle of the hand. Returns its objects."""
    kind, _, bone_name = spec.partition(":")
    file = os.path.join(PROPS_DIR, PROPS.get(kind, ("", 0))[0] + ".glb")
    bone = arm.data.bones.get(bone_name)
    if kind not in PROPS or bone is None or not os.path.isfile(file):
        return []
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=file)
    new = [o for o in bpy.data.objects if o not in before and o.parent is None]
    grip = Vector(new[0].get("grip", (0, 0, 0))) if new else Vector()
    # The exporter turned the tool to Y up; its grip came back in Blender axes.
    hand = arm.matrix_world @ ((bone.head_local + bone.tail_local) * 0.5)
    place = (Matrix.Translation(hand) @ Matrix.Rotation(math.radians(90.0), 4, "X")
             @ Matrix.Rotation(math.radians(PROPS[kind][1]), 4, "Z") @ Matrix.Translation(-grip))
    # A bone parents at its tail.
    rest = arm.matrix_world @ bone.matrix_local @ Matrix.Translation((0, bone.length, 0))
    for o in new:
        world = place @ o.matrix_world
        o.parent = arm
        o.parent_type = "BONE"
        o.parent_bone = bone_name
        o.matrix_parent_inverse = rest.inverted()
        o.matrix_basis = world
    return new


def clip_frames(action, loops):
    start, end = (int(round(f)) for f in action.frame_range)
    if loops:  # The last frame repeats the first.
        return [start + round((end - start) * i / STRIP_FRAMES) for i in range(STRIP_FRAMES)]
    return [start + round((end - start) * i / (STRIP_FRAMES - 1)) for i in range(STRIP_FRAMES)]


def animation_strips(name):
    """One row per clip, 8 frames from the side, framed on the whole clip."""
    reset(STRIP_W, STRIP_H)
    meshes, _, arm = load(name)
    arm.data.pose_position = "POSE"
    rows = []
    props = []
    for action in sorted(bpy.data.actions, key=lambda a: a.name):
        suffix = "_" + arm.name   # The importer may add the armature's name.
        clip = action.name[:-len(suffix)] if action.name.endswith(suffix) else action.name
        arm.animation_data.action = action
        if hasattr(arm.animation_data, "action_slot") and action.slots:
            arm.animation_data.action_slot = action.slots[0]
        for o in props:
            bpy.data.objects.remove(o)
        props = attach_prop(arm, arm.get(f"{clip}_prop", ""))
        frames = clip_frames(action, loops=bool(arm.get(f"{clip}_loops", 1)))
        points = []
        for f in frames:
            bpy.context.scene.frame_set(f)
            points += evaluated_points(meshes + [o for o in props if o.type == "MESH"])
        for o in [o for o in bpy.data.objects if o.name.startswith(("cam", "label"))]:
            bpy.data.objects.remove(o)  # The previous clip's camera and label.
        cam, dist = camera_for(points, Vector((-1.0, 0.0, 0.18)), STRIP_W, STRIP_H)
        text = label(cam, dist, clip)
        start = frames[0]
        for i, f in enumerate(frames):
            bpy.context.scene.frame_set(f)
            text.data.body = f"{clip}  ·  {f - start}"
            path = os.path.join(PANELS, f"{name}_anim_{clip}_{i}.png")
            render(path)
            rows.append(path)
    compose(rows, STRIP_FRAMES, os.path.join(OUT, name + "_anim.png"))


for name in NAMES:
    for view, direction, wire in VIEWS:
        reset()
        meshes, corners, arm = load(name)
        cam, dist = camera_for(corners, direction)
        size = max((max(p[i] for p in corners) - min(p[i] for p in corners)) for i in range(3))
        text = f"{name}  ·  {view}"
        if wire:
            text = f"{wireframe(meshes, size)} triangles"
        label(cam, dist, text)
        render(panel_path(name, view))
    compose([panel_path(name, v) for v, _, _ in VIEWS], 2, os.path.join(OUT, name + ".png"))
    if arm is not None:
        animation_strips(name)

if not ONLY:
    compose([panel_path(n, "3/4") for n in NAMES], 6 if len(NAMES) > 12 else 4, os.path.join(OUT, "overview.png"))
for f in os.listdir(PANELS):
    os.remove(os.path.join(PANELS, f))
os.rmdir(PANELS)
