"""Renders preview images of the exported models, to review them without
opening Blender's interface.

    blender --background --factory-startup --python art/blender/preview.py -- <models folder> <output folder>
"""

import math
import os
import sys

import bpy
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
MODELS = os.path.abspath(args[0])
OUT = os.path.abspath(args[1])
os.makedirs(OUT, exist_ok=True)

# Where each accessory is pinned on each body: (bone, rest position of the
# bone start). Mirrors the attach points the game uses.
HEAD_BASE = {"human_male": 1.53, "human_female": 1.53 * 0.95}
HIPS_BASE = {"human_male": 0.95, "human_female": 0.95 * 0.95}


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.render.resolution_x = 900
    scene.render.resolution_y = 600
    scene.render.film_transparent = False
    world = bpy.data.worlds.new("w")
    world.color = (0.55, 0.62, 0.7)
    scene.world = world
    return scene


def load(name, offset=(0, 0, 0)):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(MODELS, name))
    new = [o for o in bpy.data.objects if o not in before]
    for o in new:
        if o.parent is None:
            o.location = Vector(o.location) + Vector(offset)
    return new


def camera(location, target, lens=50):
    cam_data = bpy.data.cameras.new("cam")
    cam_data.lens = lens
    cam = bpy.data.objects.new("cam", cam_data)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = location
    direction = Vector(target) - Vector(location)
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = cam


def ground():
    bpy.ops.mesh.primitive_plane_add(size=40)
    plane = bpy.context.active_object
    mat = bpy.data.materials.new("ground")
    mat.diffuse_color = (0.35, 0.45, 0.25, 1)
    plane.data.materials.append(mat)


def render(name):
    bpy.context.scene.render.filepath = os.path.join(OUT, name)
    bpy.ops.render.render(write_still=True)


def set_action(objs, action_name, frame):
    for o in objs:
        if o.type == "ARMATURE":
            if o.animation_data is None:
                o.animation_data_create()
            action = bpy.data.actions.get(action_name)
            o.animation_data.action = action
            if action is not None and hasattr(o.animation_data, "action_slot") and action.slots:
                o.animation_data.action_slot = action.slots[0]
    bpy.context.scene.frame_set(frame)


# 1. The two bodies with accessories, idle.
reset()
ground()
male = load("characters/human_male.glb", (-0.6, 0, 0))
load("characters/beard.glb", (-0.6, 0, HEAD_BASE["human_male"]))
load("characters/hat_straw.glb", (-0.6, 0, HEAD_BASE["human_male"]))
load("characters/apron_male.glb", (-0.6, 0, HIPS_BASE["human_male"]))
female = load("characters/human_female.glb", (0.6, 0, 0))
load("characters/hat_cap.glb", (0.6, 0, HEAD_BASE["human_female"]))
load("characters/apron_female.glb", (0.6, 0, HIPS_BASE["human_female"]))
set_action(male + female, "idle", 0)
camera((2.2, -4.2, 1.9), (0, 0, 1.0), lens=45)
render("characters_front.png")
camera((0.3, -1.6, 1.6), (0.6, 0, 1.55), lens=60)
render("faces.png")

# 2. Walk cycle, side view.
for frame in (0, 8, 15, 23):
    reset()
    ground()
    body = load("characters/human_male.glb")
    set_action(body, "walk", frame)
    camera((4.2, -0.2, 1.1), (0, 0, 0.95), lens=50)
    render(f"walk_{frame:02d}.png")

# 3. Props.
reset()
ground()
load("props/house_small.glb", (0, 0, 0))
load("trees/pine_bloom.glb", (5.5, 2.5, 0))
load("props/rock.glb", (-4.2, -1.5, 0))
load("characters/human_male.glb", (1.8, -3.0, 0))
camera((9.0, -13.0, 6.5), (0, 0, 2.0), lens=40)
render("props.png")
