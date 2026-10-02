"""Animates a model made with Tripo and exports it for the viewer.

    blender --background --factory-startup --python art/blender/tripo_build.py -- <model.fbx> [name=<name>] [out=<folder>] [options]

Two kinds of model, told apart by the file:

A four-legged animal with Tripo's auto-rig (option length=<meters>):

The model keeps its own mesh and texture. Tripo's skeleton only says where
the joints are: its bone names are not reliable (a front leg may hang from
a bone called "Head"), so the legs, the tail and the head are found by
shape, and the model gets the template's bones, weights and clips (idle,
walk, run, eat, die). The model is turned to face -Y, scaled to `length`
(nose to tail tip; default: as it comes) and stood on Z = 0.

A standing character without a skeleton (see tripo_character.py). Options:
height=<meters> (default 1.7), tris=<triangles> (default 3000),
image=<picture the model was generated from> and crop=x0,y0,x1,y1 (the
character's box in that picture, in pixels) to take its colors from it, and
front=+x|-x|+y|-y if the side it faces is guessed wrong.

Writes <out>/<name>.glb (default: art/studies/tripo/<file name>.glb).
A rigged model whose skeleton has no four chains of bones reaching the
ground is refused.
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import common  # noqa: E402
import rigs  # noqa: E402
import tripo_character  # noqa: E402

MAX_NAME = 48


def chains(arm):
    """Chains of bones without branches, each as (bones, joints in world
    space), from the bone after a branching to a leaf."""
    out = []
    for bone in arm.data.bones:
        if bone.children:
            continue
        chain = [bone]
        while chain[0].parent is not None and len(chain[0].parent.children) == 1:
            chain.insert(0, chain[0].parent)
        joints = [arm.matrix_world @ chain[0].head_local] + [arm.matrix_world @ b.tail_local for b in chain]
        out.append((chain, joints))
    return out


def leg_points(joints, height, foot):
    """(hip, knee, ankle, toe) from a leg chain's joints. The ankle is the
    lowest joint clearly above the ground; the knee, the joint between hip
    and ankle farthest from the line that joins them."""
    above = [j for j in joints if j.z > 0.05 * height]
    hip, ankle = above[0], above[-1]
    between = above[1:-1] or [hip.lerp(ankle, 0.5)]
    axis = (ankle - hip).normalized()
    knee = max(between, key=lambda j: ((j - hip) - axis * (j - hip).dot(axis)).length)
    return hip, knee, ankle, Vector((ankle.x, ankle.y - foot, 0.0))


def character(mesh, name, out, options):
    height = float(options.get("height", 1.7))
    triangles = int(options.get("tris", 3000))
    if not 0.2 <= height <= 10.0 or not 300 <= triangles <= 200000:
        print("TRIPO height must be between 0.2 and 10 m, and tris between 300 and 200000")
        return
    crop = None
    if "crop" in options:
        parts = options["crop"].split(",")
        if len(parts) != 4 or not all(p.strip().lstrip("-").isdigit() for p in parts):
            print("TRIPO crop must be x0,y0,x1,y1 in pixels")
            return
        crop = tuple(int(p) for p in parts)
    picture = options.get("image")
    if picture is not None and not os.path.isfile(picture):
        print("TRIPO image not found:", picture)
        return
    front = options.get("front")
    if front not in (None, "+x", "-x", "+y", "-y"):
        print("TRIPO front must be +x, -x, +y or -y")
        return
    os.makedirs(out, exist_ok=True)
    problem = tripo_character.build(mesh, name, os.path.join(out, name + ".glb"), height, triangles,
                                    picture=picture, crop=crop, front=front)
    if problem:
        print("TRIPO", name + ":", problem)


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if not args:
        print("TRIPO usage: tripo_build.py -- <model.fbx> [name=...] [length=meters] [out=folder]")
        return
    source = os.path.abspath(args[0])
    options = dict(a.split("=", 1) for a in args[1:] if "=" in a)
    name = options.get("name") or os.path.splitext(os.path.basename(source))[0]
    name = "".join(c if c.isalnum() or c in "_-" else "_" for c in name)[:MAX_NAME] or "model"
    out = os.path.abspath(options.get("out", os.path.join(HERE, "..", "studies", "tripo")))
    length = float(options["length"]) if "length" in options else None
    if length is not None and not 0.05 <= length <= 50.0:
        print("TRIPO length must be between 0.05 and 50 m")
        return

    scene = common.reset_scene()
    bpy.ops.import_scene.fbx(filepath=source)
    # The importer sets the scene to the file's frame rate; the clips are
    # keyed at 30 fps from frame 0.
    scene.render.fps, scene.render.fps_base = rigs.FPS, 1.0
    scene.frame_start = scene.frame_end = 0
    arm = next((o for o in bpy.data.objects if o.type == "ARMATURE"), None)
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    if len(meshes) != 1:
        print("TRIPO expected one mesh")
        return
    mesh = meshes[0]
    bpy.context.view_layer.update()
    if arm is None:
        character(mesh, name, out, options)
        return

    # 1. What Tripo's skeleton says, in world space.
    points = [mesh.matrix_world @ v.co for v in mesh.data.vertices]
    height = max(p.z for p in points) - min(p.z for p in points)
    ground = min(p.z for p in points)
    found = chains(arm)
    legs = sorted((c for c in found if c[1][-1].z - ground < 0.25 * height and len(c[1]) >= 3),
                  key=lambda c: c[1][-1].z)[:4]
    if len(legs) != 4:
        print(f"TRIPO not a quadruped: {len(legs)} chains of bones reach the ground")
        return
    others = [c for c in found if c not in legs]
    center = sum((c[1][0] for c in legs), Vector()) / 4
    tails = [c for c in others if any("tail" in b.name.lower() for b in c[0])]
    if tails:
        back = (tails[0][1][-1] - center).to_2d().normalized()
    else:  # The head is the free chain that ends highest; the tail is behind.
        head = max(others, key=lambda c: c[1][-1].z) if others else None
        back = -(head[1][-1] - center).to_2d().normalized() if head else Vector((0, 1))
    legs.sort(key=lambda c: c[1][0].to_2d().dot(back))
    front, hind = legs[:2], legs[2:]
    back = (sum((c[1][0] for c in hind), Vector()) / 2 - sum((c[1][0] for c in front), Vector()) / 2).to_2d().normalized()

    # 2. Face -Y, stand on Z = 0, the hips' center over the origin, to scale.
    turn = Matrix.Rotation(math.atan2(back.x, back.y), 4, "Z")   # Brings `back` onto +Y.
    extent = [(turn @ p).y for p in points]
    scale = length / (max(extent) - min(extent)) if length else 1.0
    place = Matrix.Scale(scale, 4) @ turn @ Matrix.Translation(Vector((-center.x, -center.y, -ground)))

    def moved(p):
        return place @ p

    mesh.data.transform(place @ mesh.matrix_world)
    mesh.parent = None
    mesh.matrix_world = Matrix.Identity(4)
    for mod in list(mesh.modifiers):
        mesh.modifiers.remove(mod)
    mesh.vertex_groups.clear()
    tail_joints = [moved(j) for j in tails[0][1]] if tails else []
    leg_joints = {}
    for group, pair in (("F", front), ("H", hind)):
        pair = sorted(pair, key=lambda c: moved(c[1][0]).x)   # Right (-X), then left.
        leg_joints[group + "R"], leg_joints[group + "L"] = ([moved(j) for j in c[1]] for c in pair)
    bpy.data.objects.remove(arm)
    mesh.name = mesh.data.name = name
    for i, mat in enumerate(mesh.data.materials):
        mat.name = name if i == 0 else f"{name}_{i}"

    # 3. The template's joints.
    verts = [v.co.copy() for v in mesh.data.vertices]
    height = max(p.z for p in verts)
    total = max(p.y for p in verts) - min(p.y for p in verts)
    leg_data = {leg: leg_points(joints, height, 0.07 * total) for leg, joints in leg_joints.items()}
    leg_length = min((p[1] - p[0]).length + (p[2] - p[1]).length for p in leg_data.values())

    def middle(a, b, lift):
        m = (leg_data[a][0] + leg_data[b][0]) * 0.5
        return Vector((m.x, m.y, m.z + lift * height))

    rear, shoulders = middle("HL", "HR", 0.1), middle("FL", "FR", 0.08)
    by_y = sorted(verts, key=lambda p: p.y)
    nose = sum(by_y[:max(1, len(by_y) // 200)], Vector()) / max(1, len(by_y) // 200)
    rump = sum(by_y[-max(1, len(by_y) // 200):], Vector()) / max(1, len(by_y) // 200)
    waist = rear.lerp(shoulders, 0.55)
    head_base = shoulders.lerp(nose, 0.45)
    head_base.z = max(head_base.z, shoulders.z)
    tail = [j for j in tail_joints if j.y > rear.y] or [Vector((rear.x, rear.y + 0.05 * total, rear.z))]
    if rump.y > tail[-1].y + 0.03 * total:
        tail.append(rump)
    while len(tail) < 3:   # At least two tail bones.
        tail.insert(-1, tail[-2].lerp(tail[-1], 0.5)) if len(tail) > 1 else tail.append(tail[0] + Vector((0, 0.1 * total, 0)))
    top = max((p for p in verts if p.y < head_base.y), key=lambda p: p.z, default=head_base)

    class TripoRig(rigs.Beast):
        tail_reach = 0.1 * total
        eat = (8.0, 8.0, 30.0, 20.0)

    lowest_hip = min(p[0].z for p in leg_data.values())
    rig = TripoRig(
        body=(rear, waist), chest=(waist, shoulders), neck=(shoulders, head_base), head=(head_base, nose),
        ears=(Vector((0.05 * total, top.y, top.z - 0.05 * height)), Vector((0.06 * total, top.y, top.z))),
        tail=tail[:5],
        legs=leg_data,
        leg_exit=(lowest_hip * 0.62, lowest_hip * 0.82),
        leg_reach=0.13 * total,
        walk=rigs.Gait(speed=1.6 * leg_length, frames=16, duty=0.62, lift=0.1 * leg_length,
                       crouch=0.09 * leg_length, bob=0.015 * leg_length, phases=rigs.WALK_PHASES, wag=10.0),
        run=rigs.Gait(speed=7.0 * leg_length, frames=10, duty=0.3, lift=0.2 * leg_length,
                      crouch=0.16 * leg_length, bob=0.025 * leg_length, phases=rigs.GALLOP_PHASES, nod=4.0, wag=6.0),
        lie_height=0.3 * height,
        blend=0.08 * leg_length,
    )

    # 4. Weights from the template, then the skeleton, the clips and the file.
    groups = {}
    for v in mesh.data.vertices:
        weights = sorted(((w, n) for n, w in rig.surface_weights(v.co) if w > 0.0), reverse=True)[:4]
        norm = sum(w for w, _ in weights)
        for w, bone in weights:
            if bone not in groups:
                groups[bone] = mesh.vertex_groups.new(name=bone)
            groups[bone].add([v.index], w / norm, "REPLACE")
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, name + ".glb")
    rigs.animate(rig, mesh, name, path, images=True)
    tris = sum(len(p.vertices) - 2 for p in mesh.data.polygons)
    print(f"TRIPO {name}: {tris} triangles, {len(rig.bones)} bones, {total:.2f} m long, {height:.2f} m tall, "
          f"walk {rig.walk.speed:.2f} m/s, run {rig.run.speed:.2f} m/s -> {path}")


main()
