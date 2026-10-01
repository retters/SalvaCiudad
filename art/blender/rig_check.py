"""Checks the animations of rigged zoo models (phase 44 criteria).

    blender --background --factory-startup --python art/blender/rig_check.py -- <model.glb> [...]

For each model, on the exported file itself:
- every looping clip ends in the pose it starts with (no jump);
- no vertex goes below the ground (Z = 0), except in the clips where the
  body leaves its feet (die, fish_sit, swim, fly);
- in the clips with a saved speed ("<clip>_speed" extras), each foot on the
  ground moves back at that speed (within 10 %), so it will not slide when
  the game moves the model at that speed.
Prints one line per check and "RIG OK" or "RIG FAILED" at the end.
"""

import os
import sys

import bpy
from mathutils import Vector

TOLERANCE_Z = 0.004     # m below the ground still accepted (rounding of the bake).
LOOP_TOLERANCE = 0.002  # m between the first and last pose of a loop.
SPEED_TOLERANCE = 0.10
GROUND = 0.006          # A foot vertex this close to the ground is planted.


def load(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    # The clips are baked at 30 fps; at Blender's default 24 the last frame
    # of a clip would fall between two frames.
    bpy.context.scene.render.fps = 30
    bpy.context.scene.render.fps_base = 1.0
    bpy.ops.import_scene.gltf(filepath=path)
    arm = next((o for o in bpy.data.objects if o.type == "ARMATURE"), None)
    if arm is None:
        return None, None
    # The importer may also add a mesh to draw the bones with; take the skinned one.
    mesh = max((o for o in bpy.data.objects if o.type == "MESH" and o.parent == arm),
               key=lambda o: len(o.data.vertices))
    return arm, mesh


def set_clip(arm, action):
    arm.animation_data.action = action
    if hasattr(arm.animation_data, "action_slot") and action.slots:
        arm.animation_data.action_slot = action.slots[0]


def positions(mesh, frame):
    bpy.context.scene.frame_set(frame)
    dg = bpy.context.evaluated_depsgraph_get()
    ev = mesh.evaluated_get(dg)
    m = ev.to_mesh()
    pts = [ev.matrix_world @ v.co for v in m.vertices]
    ev.to_mesh_clear()
    return pts


OFF_FEET = ("die", "fish_sit", "swim", "fly")


def clip_name(action, arm):
    # The importer may add the armature's name after the clip's name.
    suffix = "_" + arm.name
    return action.name[:-len(suffix)] if action.name.endswith(suffix) else action.name


def check(path):
    arm, mesh = load(path)
    if arm is None:
        print("  no skeleton")
        return True
    ok = True
    bones, clips = len(arm.data.bones), len(bpy.data.actions)
    if bones > 64 or clips > 16:   # The game's limits (model_limits).
        ok = False
    print(f"  {bones} bones, {clips} clips{'' if ok else ' TOO MANY'}")
    rest = [mesh.matrix_world @ v.co for v in mesh.data.vertices]
    # Foot vertices: those of each foot bone that are on the ground at rest.
    names = {g.index: g.name for g in mesh.vertex_groups}
    # Slim feet can rest a few millimeters above Z = 0: the lowest point of
    # the model at rest is where its feet stand.
    floor = max(0.0, min(p.z for p in rest))
    feet = {}
    for i, p in enumerate(rest):
        if p.z < floor + GROUND:
            for g in mesh.data.vertices[i].groups:
                if g.weight > 0.99 and names[g.group].startswith("foot"):
                    feet.setdefault(names[g.group], []).append(i)
    for action in sorted(bpy.data.actions, key=lambda a: a.name):
        name = clip_name(action, arm)
        set_clip(arm, action)
        start, end = (int(round(f)) for f in action.frame_range)
        frames = [positions(mesh, f) for f in range(start, end + 1)]
        low = min(p.z for pts in frames for p in pts)
        if not name.startswith(OFF_FEET):
            good = low >= -TOLERANCE_Z
            ok &= good
            print(f"  {name}: lowest point {low * 100:+.2f} cm {'ok' if good else 'BELOW THE GROUND'}")
        if arm.get(f"{name}_loops", 1):
            jump = max((a - b).length for a, b in zip(frames[0], frames[-1]))
            good = jump <= LOOP_TOLERANCE
            ok &= good
            print(f"  {name}: loop jump {jump * 1000:.2f} mm {'ok' if good else 'JUMPS'}")
        speed = arm.get(f"{name}_speed")
        if speed is None or name.startswith(OFF_FEET):
            continue   # No speed, or a speed through the air or the water.
        fps = bpy.context.scene.render.fps / bpy.context.scene.render.fps_base
        if not feet:
            ok = False
            print(f"  {name}: no foot vertices on the ground at rest, so its speed cannot be checked")
        for leg, idx in sorted(feet.items()):
            moves = []
            for a, b in zip(frames, frames[1:]):
                if max(a[i].z for i in idx) < floor + GROUND and max(b[i].z for i in idx) < floor + GROUND:
                    ya = sum(a[i].y for i in idx) / len(idx)
                    yb = sum(b[i].y for i in idx) / len(idx)
                    moves.append((yb - ya) * fps)
            if not moves:
                ok = False
                print(f"  {name} {leg}: never planted")
                continue
            v = sum(moves) / len(moves)
            good = abs(v - speed) <= SPEED_TOLERANCE * speed
            ok &= good
            print(f"  {name} {leg}: planted {len(moves)} frames, moves back at {v:.2f} m/s "
                  f"(clip speed {speed:.2f}) {'ok' if good else 'SLIDES'}")
    return ok


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    all_ok = True
    for path in args:
        print(os.path.basename(path))
        all_ok &= check(os.path.abspath(path))
    print("RIG OK" if all_ok else "RIG FAILED")


main()
