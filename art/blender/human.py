"""Villagers: male and female bodies for each race (humans, dwarves, elves
and catfolk, phase 19) with a shared bone layout, idle and walk animations,
and rigid accessories (hats, beard, aprons) that the game pins to a bone.

The races differ in proportions (dwarves short and broad, elves tall and
slender) and in a few parts: long pointed ears for elves, cat ears and a
tail for catfolk. The head keeps the same size so the hats fit all.

Bodies are built from overlapping low-poly parts, each bound to one bone.
The materials named in common.PALETTE_SLOTS are recolored per villager.
"""

import math
import os

import bpy
from mathutils import Matrix, Quaternion, Vector

import common
from common import MeshBuilder

WALK_FRAMES = 30   # One full stride cycle in 1 s at 30 fps.
IDLE_FRAMES = 60   # A slow breathing loop of 2 s.

# Preview colors; the game replaces the palette slots.
COLORS = {
    "skin": common.rgb(0xE0B08A),
    "hair": common.rgb(0x5A3A22),
    "top": common.rgb(0x8C6A3F),
    "bottom": common.rgb(0x4E5A3A),
    "shoes": common.rgb(0x3B2A1E),
    "belt": common.rgb(0x2E2016),
    "hat": common.rgb(0xC9A860),
    "apron": common.rgb(0xD8CFB8),
    "eyes": common.rgb(0x1C1612),
    "mouth": common.rgb(0x8A4B3E),
}


# Height factor below the head and width factor, by race.
RACES = {
    "human": (1.0, 1.0),
    "dwarf": (0.74, 1.28),
    "elf": (1.07, 0.9),
    "catfolk": (0.97, 0.95),
}


class Body:
    """Proportions of one body type, in meters."""

    def __init__(self, female, race="human"):
        self.female = female
        self.race = race
        height, width = RACES[race]
        self.k = (0.95 if female else 1.0) * height        # Height factor below the head.
        self.shoulder = (0.17 if female else 0.20) * width  # Half width at the shoulders.
        self.hip = (0.11 if female else 0.10) * width       # Half width between the legs.
        self.width = width

    def z(self, v):
        return v * self.k

    def bones(self):
        """name: (head, tail, parent)."""
        z, s, h = self.z, self.shoulder, self.hip
        head_base = z(1.53)
        b = {
            "hips": ((0, 0, z(0.95)), (0, 0, z(1.05)), None),
            "spine": ((0, 0, z(1.05)), (0, 0, z(1.28)), "hips"),
            "chest": ((0, 0, z(1.28)), (0, 0, z(1.45)), "spine"),
            "neck": ((0, 0, z(1.45)), (0, 0, head_base), "chest"),
            # The head keeps the same size for both bodies, so hats fit both.
            "head": ((0, 0, head_base), (0, 0, head_base + 0.27), "neck"),
        }
        for side, x in (("L", 1.0), ("R", -1.0)):
            b[f"upper_arm.{side}"] = ((x * s, 0, z(1.42)), (x * (s + 0.03), 0.0, z(1.14)), "chest")
            b[f"lower_arm.{side}"] = ((x * (s + 0.03), 0.0, z(1.14)), (x * (s + 0.04), -0.03, z(0.89)), f"upper_arm.{side}")
            b[f"hand.{side}"] = ((x * (s + 0.04), -0.03, z(0.89)), (x * (s + 0.045), -0.04, z(0.79)), f"lower_arm.{side}")
            b[f"thigh.{side}"] = ((x * h, 0, z(0.94)), (x * h, 0.0, z(0.51)), "hips")
            b[f"shin.{side}"] = ((x * h, 0.0, z(0.51)), (x * h, 0.02, z(0.09)), f"thigh.{side}")
            b[f"foot.{side}"] = ((x * h, 0.02, z(0.09)), (x * h, -0.14, z(0.03)), f"shin.{side}")
        return b


BONE_ORDER = ("hips", "spine", "chest", "neck", "head",
              "upper_arm.L", "lower_arm.L", "hand.L", "upper_arm.R", "lower_arm.R", "hand.R",
              "thigh.L", "shin.L", "foot.L", "thigh.R", "shin.R", "foot.R")


def build_armature(body, name):
    arm_data = bpy.data.armatures.new(name)
    arm = bpy.data.objects.new(name, arm_data)
    bpy.context.scene.collection.objects.link(arm)
    common.select_only([arm])
    bpy.ops.object.mode_set(mode="EDIT")
    specs = body.bones()
    for bone_name in BONE_ORDER:
        head, tail, parent = specs[bone_name]
        eb = arm_data.edit_bones.new(bone_name)
        eb.head = head
        eb.tail = tail
        eb.roll = 0.0
        if parent:
            eb.parent = arm_data.edit_bones[parent]
            eb.use_connect = False
    bpy.ops.object.mode_set(mode="OBJECT")
    return arm


def head_parts(mb, base, race="human"):
    """Head, face and hair around the head bone base (neck top)."""
    w = {"head": 1.0}
    mb.sphere((0, -0.005, base + 0.12), 0.13, "skin", w, segments=12, rings=8, scale=(0.95, 1.0, 1.1))
    for x in (-1, 1):
        mb.sphere((x * 0.047, -0.118, base + 0.135), 0.017, "eyes", w, segments=6, rings=4)
        if race == "elf":
            # Long ears pointing up and back.
            mb.cylinder((x * 0.12, 0.0, base + 0.1), (x * 0.2, 0.06, base + 0.24), 0.028, 0.004, "skin", w, segments=5)
        elif race == "catfolk":
            # Cat ears on top of the head, in the hair's color.
            mb.cylinder((x * 0.08, 0.02, base + 0.21), (x * 0.1, 0.03, base + 0.33), 0.05, 0.004, "hair", w, segments=4)
            mb.cylinder((x * 0.08, 0.005, base + 0.215), (x * 0.098, 0.015, base + 0.3), 0.03, 0.003, "skin", w,
                        segments=4)
        else:
            mb.sphere((x * 0.128, 0.0, base + 0.115), 0.03, "skin", w, segments=6, rings=4, scale=(0.5, 1.0, 1.3))
    mb.box((0, -0.132, base + 0.1), (0.032, 0.04, 0.055), "skin", w)
    mb.box((0, -0.121, base + 0.055), (0.05, 0.012, 0.012), "mouth", w)


def build_body(body):
    mb = MeshBuilder()
    z, s, h = body.z, body.shoulder, body.hip
    base = z(1.53)
    head_parts(mb, base, body.race)
    if body.female:
        # Longer hair: a cap plus a fall down the back, and a bun.
        mb.sphere((0, 0.018, base + 0.15), 0.138, "hair", {"head": 1.0}, segments=12, rings=8, scale=(1.0, 1.0, 0.86))
        mb.box((0, 0.085, base + 0.02), (0.22, 0.08, 0.26), "hair", {"head": 1.0})
        mb.sphere((0, 0.12, base + 0.2), 0.055, "hair", {"head": 1.0}, segments=8, rings=6)
    else:
        mb.sphere((0, 0.02, base + 0.16), 0.136, "hair", {"head": 1.0}, segments=12, rings=8, scale=(1.0, 1.0, 0.8))

    mb.cylinder((0, 0, z(1.44)), (0, 0, base + 0.03), 0.055, 0.052, "skin", {"neck": 1.0})

    # Torso.
    bw = body.width
    mb.cylinder((0, 0, z(1.18)), (0, 0, z(1.46)), 0.165 * bw, s + 0.005, "top", {"chest": 1.0}, segments=10)
    mb.cylinder((0, 0, z(0.99)), (0, 0, z(1.2)), (0.16 if not body.female else 0.15) * bw, 0.165 * bw, "top", {"spine": 1.0},
                segments=10)
    mb.cylinder((0, 0, z(0.97)), (0, 0, z(1.03)), (0.172 if not body.female else 0.16) * bw,
                (0.172 if not body.female else 0.16) * bw,
                "belt", {"hips": 1.0}, segments=10)
    for x in (-1, 1):
        mb.sphere((x * s, 0, z(1.42)), 0.068, "top", {"chest": 1.0}, segments=8, rings=6)

    if body.female:
        # A long skirt bound to the hips; the legs move underneath it.
        mb.cylinder((0, 0, z(1.0)), (0, 0, z(0.4)), 0.16 * bw, 0.3 * bw, "bottom", {"hips": 1.0}, segments=12)
    else:
        mb.cylinder((0, 0, z(0.84)), (0, 0, z(1.0)), 0.165 * bw, 0.17 * bw, "bottom", {"hips": 1.0}, segments=10)

    # Arms: sleeves, forearms and hands.
    specs = body.bones()
    for side in ("L", "R"):
        shoulder, elbow, _ = specs[f"upper_arm.{side}"]
        _, wrist, _ = specs[f"lower_arm.{side}"]
        _, hand_tip, _ = specs[f"hand.{side}"]
        r = (0.05 if body.female else 0.057) * bw
        mb.cylinder(shoulder, elbow, r, r * 0.85, "top", {f"upper_arm.{side}": 1.0})
        mb.sphere(elbow, r * 0.85, "top", {f"lower_arm.{side}": 1.0}, segments=8, rings=5)
        mb.cylinder(elbow, wrist, r * 0.8, r * 0.64, "skin", {f"lower_arm.{side}": 1.0})
        center = (Vector(wrist) + Vector(hand_tip)) * 0.5
        mb.sphere(center, 0.045, "skin", {f"hand.{side}": 1.0}, segments=8, rings=5, scale=(0.7, 0.95, 1.25))

    if body.race == "catfolk":
        # A tail from the small of the back, curving up.
        points = [(0, 0.14, z(0.98)), (0, 0.3, z(0.9)), (0, 0.44, z(0.95)), (0, 0.52, z(1.1)), (0, 0.55, z(1.25))]
        for i, (a, b) in enumerate(zip(points, points[1:])):
            r = 0.045 - i * 0.007
            mb.cylinder(a, b, r, r - 0.006, "hair", {"hips": 1.0}, segments=6)
        mb.sphere(points[-1], 0.03, "hair", {"hips": 1.0}, segments=6, rings=4)

    # Legs: trousers (or stockings under the skirt), boots.
    for side, x in (("L", 1.0), ("R", -1.0)):
        hip_joint, knee, _ = specs[f"thigh.{side}"]
        _, ankle, _ = specs[f"shin.{side}"]
        leg_mat = "bottom" if not body.female else "skin"
        r = (0.068 if not body.female else 0.06) * bw
        mb.cylinder(hip_joint, knee, r + 0.008, r - 0.006, leg_mat, {f"thigh.{side}": 1.0})
        mb.sphere(knee, r - 0.006, leg_mat, {f"shin.{side}": 1.0}, segments=8, rings=5)
        mb.cylinder(knee, (ankle[0], ankle[1], ankle[2] + 0.08), r - 0.008, r - 0.018, leg_mat, {f"shin.{side}": 1.0})
        mb.cylinder((ankle[0], ankle[1], ankle[2] + 0.12), (ankle[0], ankle[1], ankle[2] - 0.02), 0.052, 0.05, "shoes",
                    {f"shin.{side}": 1.0})
        mb.box((x * h, -0.045, z(0.035)), (0.09, 0.2, 0.07), "shoes", {f"foot.{side}": 1.0})

    return mb


def pose_key(arm, frame, rotations, hips_offset=(0, 0, 0)):
    """Keys every bone at `frame`. `rotations` maps bone -> list of
    (world axis, degrees) applied in order, expressed in armature space."""
    for pb in arm.pose.bones:
        rest = pb.bone.matrix_local.to_3x3()
        q = Quaternion()
        for axis, deg in rotations.get(pb.name, []):
            q = Quaternion(Vector(axis), math.radians(deg)) @ q
        local = (rest.transposed() @ q.to_matrix() @ rest).to_quaternion()
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = local
        pb.keyframe_insert(data_path="rotation_quaternion", frame=frame)
        if pb.name == "hips":
            pb.location = rest.transposed() @ Vector(hips_offset)
        else:
            pb.location = (0, 0, 0)
        pb.keyframe_insert(data_path="location", frame=frame)


X = (1, 0, 0)
Y = (0, 1, 0)
Z = (0, 0, 1)


def walk_pose(t):
    """t in [0, 1): one stride. Negative X rotation swings a limb forward."""
    p = 2 * math.pi * t
    rot = {}
    for side, sign in (("L", 1.0), ("R", -1.0)):
        swing = math.sin(p) * sign          # +1: this leg forward.
        rot[f"thigh.{side}"] = [(X, -26.0 * swing)]
        # The knee bends most while the leg swings through.
        lift = max(0.0, math.sin(p + (0 if sign > 0 else math.pi) - 0.9))
        rot[f"shin.{side}"] = [(X, 6.0 + 42.0 * lift)]
        rot[f"foot.{side}"] = [(X, -8.0 * swing - 10.0 * lift)]
        rot[f"upper_arm.{side}"] = [(X, 20.0 * swing), (Y, 6.0 * sign)]
        rot[f"lower_arm.{side}"] = [(X, -18.0 - 8.0 * max(0.0, -swing))]
    rot["hips"] = [(Z, 5.0 * math.sin(p))]
    rot["spine"] = [(X, -3.0), (Z, -4.0 * math.sin(p))]
    rot["chest"] = [(Z, -3.0 * math.sin(p))]
    rot["head"] = [(Z, 2.0 * math.sin(p))]
    bob = -0.025 * math.cos(2 * p)
    return rot, (0, 0, bob)


def idle_pose(t):
    p = 2 * math.pi * t
    breath = math.sin(p)
    rot = {
        "chest": [(X, 1.5 * breath)],
        "head": [(Z, 4.0 * math.sin(p * 0.5)), (X, -1.5 * breath)],
        "spine": [(Y, 1.0 * math.sin(p * 0.5))],
    }
    for side, sign in (("L", 1.0), ("R", -1.0)):
        rot[f"upper_arm.{side}"] = [(Y, 5.0 * sign), (X, 2.0 * breath)]
        rot[f"lower_arm.{side}"] = [(X, -10.0)]
        rot[f"thigh.{side}"] = [(X, 0.0)]
    return rot, (0, 0, -0.004 * breath)


def add_action(arm, name, frames, pose_fn):
    action = bpy.data.actions.new(name)
    action.use_fake_user = True
    arm.animation_data_create()
    arm.animation_data.action = action
    for f in range(frames + 1):
        rot, offset = pose_fn((f % frames) / frames)
        pose_key(arm, f, rot, offset)
    return action


def make_body_file(folder, female, race="human"):
    common.reset_scene()
    body = Body(female, race)
    name = race + ("_female" if female else "_male")
    arm = build_armature(body, name + "_rig")
    mesh = build_body(body).to_object(name, COLORS)
    mesh.parent = arm
    mod = mesh.modifiers.new("Armature", "ARMATURE")
    mod.object = arm
    add_action(arm, "idle", IDLE_FRAMES, idle_pose)
    add_action(arm, "walk", WALK_FRAMES, walk_pose)
    arm.animation_data.action = None
    for pb in arm.pose.bones:
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
    common.export_glb(os.path.join(folder, name + ".glb"), [arm, mesh], animations=True)


def make_accessory(folder, name, build):
    """A rigid mesh whose origin is the attach point: the start of the bone
    it is pinned to ('head': top of the neck; 'hips': the pelvis)."""
    common.reset_scene()
    mb = MeshBuilder()
    build(mb)
    obj = mb.to_object(name, COLORS)
    common.export_glb(os.path.join(folder, name + ".glb"), [obj])


def straw_hat(mb):
    mb.cylinder((0, 0, 0.2), (0, 0, 0.218), 0.27, 0.25, "hat", segments=14)
    mb.cylinder((0, 0, 0.21), (0, 0, 0.33), 0.145, 0.12, "hat", segments=12)
    mb.cylinder((0, 0, 0.215), (0, 0, 0.245), 0.148, 0.148, "belt", segments=12)


def felt_cap(mb):
    mb.sphere((0, 0.01, 0.2), 0.148, "hat", segments=12, rings=7, scale=(1.0, 1.05, 0.72))
    mb.cylinder((0, 0.02, 0.28), (0, 0.1, 0.36), 0.07, 0.02, "hat", segments=8)


def beard(mb):
    mb.sphere((0, -0.1, 0.045), 0.075, "hair", segments=10, rings=6, scale=(1.1, 0.55, 1.05))
    mb.box((0, -0.118, 0.075), (0.09, 0.02, 0.018), "hair")


def apron(width, depth, length, flare, band):
    def build(mb):
        # A slightly flared cloth in front of the waist, with a waistband.
        top = 0.1
        bottom = top - length
        v = [mb.bm.verts.new(p) for p in (
            (-width, -depth, top), (width, -depth, top), (width + flare, -depth - flare * 0.8, bottom),
            (-width - flare, -depth - flare * 0.8, bottom))]
        back = [mb.bm.verts.new((x, y + 0.012, zz)) for x, y, zz in (tuple(p.co) for p in v)]
        faces = [mb.bm.faces.new((v[0], v[1], v[2], v[3])), mb.bm.faces.new((back[3], back[2], back[1], back[0]))]
        for i in range(4):
            j = (i + 1) % 4
            faces.append(mb.bm.faces.new((v[j], v[i], back[i], back[j])))
        mb._finish(v + back, "apron", None)
        mb.cylinder((0, 0, top - 0.01), (0, 0, top + 0.03), band, band, "belt", segments=10)
    return build


def make_all(folder):
    os.makedirs(folder, exist_ok=True)
    for race in RACES:
        make_body_file(folder, female=False, race=race)
        make_body_file(folder, female=True, race=race)
    make_accessory(folder, "hat_straw", straw_hat)
    make_accessory(folder, "hat_cap", felt_cap)
    make_accessory(folder, "beard", beard)
    make_accessory(folder, "apron_male", apron(0.14, 0.18, 0.5, 0.02, 0.177))
    make_accessory(folder, "apron_female", apron(0.15, 0.2, 0.52, 0.12, 0.166))
