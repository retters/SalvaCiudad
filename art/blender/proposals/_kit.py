"""Shared helpers for the proposal models: models offered to the user for
review in docs/propuestas, not in the game yet.

Every family is a folder of art/blender/proposals with its own build script
and a catalogo.json (see docs/propuestas/LEEME.md). The models go to
art/studies/propuestas/<family>/<id>.glb, which is not versioned.

    import _kit as kit

    mb = kit.begin()                      # Empty scene and a MeshBuilder.
    mb.box(...)                           # common.MeshBuilder pieces.
    kit.save(mb, "walls", "wall_stone_straight", COLORS)

A model with rigid moving parts (a water wheel, a gate, a cart's wheels)
gives each moving piece the weight of one bone and declares a Mech:

    mb.cylinder(a, b, r, r, "wood", weights={"wheel": 1.0})
    mech = kit.Mech([("wheel", (0, 0, 1.5), (0, 0.5, 1.5), None)])
    mech.clip("turn", 4.0, lambda t: {"wheel": [(kit.Y, 360 * t)]})
    kit.save(mb, "buildings", "watermill", COLORS, mech=mech)

Conventions are the game's (docs/ARTE.md): meters, Z up, front toward -Y,
standing on Z = 0 with the origin at the center of the base, flat shading,
plain colored materials.
"""

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import bpy  # noqa: E402
from mathutils import Quaternion, Vector  # noqa: E402

import common  # noqa: E402
import rigs  # noqa: E402
from common import MeshBuilder  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
OUT = os.path.join(REPO, "art", "studies", "propuestas")
FPS = rigs.FPS
X, Y, Z = rigs.X, rigs.Y, rigs.Z
smooth = rigs.smooth


def out_folder(family):
    folder = os.path.join(OUT, family)
    os.makedirs(folder, exist_ok=True)
    return folder


def begin():
    """Empties the scene and returns a new MeshBuilder."""
    common.reset_scene()
    return MeshBuilder()


def args():
    """The names given after "--" on Blender's command line."""
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


class Mech(rigs.Rig):
    """A skeleton of rigid parts: every vertex follows one bone whole.

    `bones` is a list of (name, head, tail, parent or None), parents first.
    A bone without a parent hangs from "root", which every model has and
    which holds whatever was built without weights. A bone turns around its
    head, so put the head on the axle or the hinge.
    """

    def __init__(self, bones=()):
        made = [rigs.Bone("root", (0, 0, 0), (0, 0, 0.5))]
        for name, head, tail, parent in bones:
            made.append(rigs.Bone(name, head, tail, parent or "root"))
        self.set_bones(made)
        self._clips = []

    def clip(self, name, seconds, pose, loops=True, speed=None):
        """Adds a clip. `pose(t)`, with t from 0 to 1, returns the turns
        {bone: [(armature axis, degrees), ...]} or a pair (turns, moves)
        where moves is {bone: (dx, dy, dz)} in meters. Both are relative to
        the bone's parent. A looping clip must end as it starts. `speed`
        (m/s) is saved as "<clip>_speed" for clips that travel (a cart)."""
        self._clips.append((name, max(1, round(seconds * FPS)), loops, pose, speed))
        return self

    def clips(self):
        return list(self._clips)


def _key(arm, frame, turns, moves):
    for pb in arm.pose.bones:
        rest = pb.bone.matrix_local.to_3x3()
        q = Quaternion()
        for axis, deg in turns.get(pb.name, []):
            q = Quaternion(Vector(axis), math.radians(deg)) @ q
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = (rest.transposed() @ q.to_matrix() @ rest).to_quaternion()
        pb.keyframe_insert(data_path="rotation_quaternion", frame=frame)
        pb.location = rest.transposed() @ Vector(moves.get(pb.name, (0, 0, 0)))
        pb.keyframe_insert(data_path="location", frame=frame)


def _bind_rest_to_root(mb, mech):
    """Vertices built without weights follow the root bone."""
    known = {b.name for b in mech.bones}
    for group in mb.groups:
        assert group in known, "weights name a bone the Mech does not have: " + group
    root = mb._group_index("root")
    for v in mb.bm.verts:
        if not v[mb.deform]:
            v[mb.deform][root] = 1.0


def save(mb, family, name, colors, mech=None, extras=None):
    """Exports the builder as art/studies/propuestas/<family>/<name>.glb and
    returns the path. With `mech`, the model gets its skeleton and clips.
    `extras` are custom properties saved in the model (a dict)."""
    path = os.path.join(out_folder(family), name + ".glb")
    if mech is None:
        obj = mb.to_object(name, colors)
        for key, value in (extras or {}).items():
            obj[key] = value
        common.export_glb(path, [obj], extras=bool(extras))
    else:
        _bind_rest_to_root(mb, mech)
        mesh = mb.to_object(name, colors)
        arm = mech.build_armature(name + "_rig")
        mesh.parent = arm
        mod = mesh.modifiers.new("Armature", "ARMATURE")
        mod.object = arm
        for clip, frames, loops, pose, speed in mech.clips():
            action = bpy.data.actions.new(clip)
            action.use_fake_user = True
            arm.animation_data_create()
            arm.animation_data.action = action
            for f in range(frames + 1):
                t = (f % frames) / frames if loops else f / frames
                posed = pose(t)
                turns, moves = posed if isinstance(posed, tuple) else (posed, {})
                _key(arm, f, turns, moves)
            if speed is not None:
                arm[f"{clip}_speed"] = speed
            if not loops:
                arm[f"{clip}_loops"] = 0
        for key, value in (extras or {}).items():
            arm[key] = value
        if arm.animation_data:
            arm.animation_data.action = None
        for pb in arm.pose.bones:
            pb.rotation_mode = "QUATERNION"
            pb.rotation_quaternion = (1, 0, 0, 0)
            pb.location = (0, 0, 0)
        common.export_glb(path, [arm, mesh], animations=True, extras=True)
    tris = _triangles(path)
    print("PROPOSAL %s/%s.glb %d tris" % (family, name, tris))
    return path


def _triangles(path):
    import json
    import struct
    with open(path, "rb") as f:
        data = f.read()
    doc = json.loads(data[20:20 + struct.unpack_from("<I", data, 12)[0]])
    total = 0
    for mesh in doc.get("meshes", []):
        for prim in mesh.get("primitives", []):
            if "indices" in prim:
                total += doc["accessors"][prim["indices"]]["count"] // 3
    return total


def build_zoo_spec(spec, family):
    """Builds a studies.Spec (the remesh technique of the zoo animals and the
    characters, with its skeleton and clips) into the family's folder."""
    import studies
    studies.build_final(spec, out_folder(family))
    print("PROPOSAL %s/%s.glb" % (family, spec.name))


# Set by whoever runs a family's script from another script (build_all.py,
# for the models that go into the game): the ids to build, in place of the
# command line's.
SELECT = None


def run(models, family):
    """The usual main of a family script: `models` maps a model id to a
    function without arguments that builds and saves it. Builds the ids
    given on the command line (or in SELECT), or all of them."""
    asked = args() if SELECT is None else list(SELECT)
    wanted = [a for a in asked if a in models]
    if not wanted and SELECT is None:
        wanted = list(models)
    unknown = [a for a in asked if a not in models]
    if unknown:
        print("PROPOSAL unknown names:", ", ".join(unknown))
    failed = []
    for name in wanted:
        try:
            models[name]()
        except Exception as error:  # One broken model must not stop the batch.
            import traceback
            traceback.print_exc()
            failed.append("%s (%s)" % (name, error))
    print("PROPOSAL built %d of %d in %s" % (len(wanted) - len(failed), len(wanted), family))
    for line in failed:
        print("PROPOSAL FAILED", line)
