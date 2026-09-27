"""Renders one preview per tree species: every size in a row, next to a
villager for scale.

    blender --background --factory-startup --python art/blender/preview_trees.py -- <models folder> <output folder> [species...]
"""

import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import trees  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:]
MODELS = os.path.abspath(args[0])
OUT = os.path.abspath(args[1])
ONLY = args[2:]
os.makedirs(OUT, exist_ok=True)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.render.resolution_x = 1200
    scene.render.resolution_y = 700
    world = bpy.data.worlds.new("w")
    world.color = (0.55, 0.62, 0.7)
    scene.world = world


def load(path, offset):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    for o in bpy.data.objects:
        if o not in before and o.parent is None:
            o.location = Vector(o.location) + Vector(offset)


def ground(size):
    bpy.ops.mesh.primitive_plane_add(size=size)
    mat = bpy.data.materials.new("ground")
    mat.diffuse_color = (0.35, 0.45, 0.25, 1)
    bpy.context.active_object.data.materials.append(mat)


for sp in trees.SPECIES:
    if ONLY and sp.id not in ONLY:
        continue
    reset()
    x = 0.0
    tallest = 0.0
    for size in sp.sizes:
        name, height = trees.SIZES[size]
        width = height * sp.crown_width * 1.1 + 1.0
        x += width * 0.5
        load(os.path.join(MODELS, "props", "tree_%s_%s.glb" % (sp.id, name)), (x, 0, 0))
        x += width * 0.5 + 1.5
        tallest = max(tallest, height)
    load(os.path.join(MODELS, "characters", "human_male.glb"), (-1.5, 0, 0))
    ground(max(x, tallest) * 3)
    center = Vector((x * 0.5 - 1.0, 0, tallest * 0.45))
    distance = max(x * 1.05, tallest * 1.6) + 4.0
    cam_data = bpy.data.cameras.new("cam")
    cam_data.lens = 35
    cam = bpy.data.objects.new("cam", cam_data)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = center + Vector((0, -distance, tallest * 0.15))
    cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = cam
    bpy.context.scene.render.filepath = os.path.join(OUT, "tree_%s.png" % sp.id)
    bpy.ops.render.render(write_still=True)
