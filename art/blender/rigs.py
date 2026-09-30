"""Skeletons and procedural animations for the zoo animals (phase 44).

A template (Quadruped) turns a few points declared by a zoo spec into a
skeleton with fixed bone names, binds the model to it and keys its clips.
Every animal of a family gets the same clips from the same code:

- idle, walk, run, eat loop; die plays once and holds its last pose;
- clips are animated in place; walk and run keep each planted foot moving
  back at the clip's speed, which is saved in the model as the extras
  "<clip>_speed" (m/s) on the skeleton, so the game can match the clip to
  how fast the animal really moves and the feet do not slide;
- legs are posed by two-bone inverse kinematics toward a foot path (planted
  on the ground, then lifted forward in an arc), so feet never sink.

Weights: the welded surface is bound by distance to the body and leg bones
(up to 4 bones per vertex, blending near the joints); each separate detail
piece (ears, eyes, tail links) is bound whole to its nearest bone.
"""

import math

import bpy
from mathutils import Quaternion, Vector

import common

FPS = 30
X = Vector((1, 0, 0))
Y = Vector((0, 1, 0))
Z = Vector((0, 0, 1))
LEGS = ("FL", "FR", "HL", "HR")  # Front/hind, left (+X)/right (-X).


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def segment_distance(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.dot(ab), 1e-12)))
    return (p - (a + ab * t)).length


class Bone:
    def __init__(self, name, head, tail, parent=None, surface=False, fade=None, around=None):
        self.name = name
        self.head = Vector(head)
        self.tail = Vector(tail)
        self.parent = parent
        self.surface = surface  # Binds the welded surface (not only details).
        self.fade = fade        # (z_full, z_zero): influence fades out upward.
        self.around = around    # (x, y, radius): influence only near this vertical axis.

    def reach(self, p):
        """How much this bone may pull on a surface point (0 to 1)."""
        r = 1.0
        if self.fade is not None:
            z_full, z_zero = self.fade
            r = max(0.0, min(1.0, (z_zero - p.z) / (z_zero - z_full)))
        if self.around is not None:
            x, y, radius = self.around
            d = math.hypot(p.x - x, p.y - y)
            r *= max(0.0, min(1.0, (radius - d) / (radius * 0.25)))
        return r


class Gait:
    """A walk or run cycle. `phases` gives each leg's offset in the cycle."""

    def __init__(self, speed, frames, duty, lift, crouch, bob, phases, nod=3.0, wag=15.0):
        self.speed = speed      # m/s the planted feet move back at.
        self.frames = frames    # Frames per cycle at 30 fps.
        self.duty = duty        # Share of the cycle each foot is planted.
        self.lift = lift        # How high a foot rises while swinging (m).
        self.crouch = crouch    # How much lower the body goes than at rest (m).
        self.bob = bob          # Up and down, twice per cycle (m).
        self.phases = phases
        self.nod = nod          # Head nod, degrees.
        self.wag = wag          # Tail swing, degrees.

    @property
    def stride(self):
        """How far a planted foot travels back during one stance."""
        return self.speed * self.duty * self.frames / FPS


WALK_PHASES = {"HL": 0.0, "FL": 0.25, "HR": 0.5, "FR": 0.75}  # Lateral sequence.
TROT_PHASES = {"FL": 0.0, "HR": 0.0, "FR": 0.5, "HL": 0.5}    # Diagonal pairs.


class Quadruped:
    """Four legs, a body, chest, neck, head, two ears and a tail.

    body: (rear, front) of the root bone, which carries the hind body.
    chest, neck, head: (start, end) of each bone, from the body forward.
    ears: (start, end) of the left ear (+X); the right one is mirrored.
    tail: points from the root of the tail to its tip (3 bones: 4 points).
    legs: for the left front and left hind leg (+X), the points
        (hip, knee, ankle, toe); the right legs are mirrored. The hip lies
        inside the body; the ankle is where the leg meets the hoof or paw.
    leg_exit: height below which the surface follows the legs fully, and
        the height above which it follows only the body.
    leg_reach: how far from a leg's axis its joint rings are cut (m).
    """

    def __init__(self, body, chest, neck, head, ears, tail, legs, leg_exit, walk, run,
                 blend=0.08, leg_reach=0.15, idle_frames=90, eat_frames=90, die_frames=45, lie_height=None):
        self.walk = walk
        self.run = run
        self.blend = blend
        self.idle_frames = idle_frames
        self.eat_frames = eat_frames
        self.die_frames = die_frames
        self.lie_height = lie_height  # Height of the spine when lying on its side.
        self.leg_exit = leg_exit
        self.leg_reach = leg_reach
        fade = leg_exit
        b = [Bone("body", *body, surface=True),
             Bone("chest", *chest, parent="body", surface=True),
             Bone("neck", *neck, parent="chest", surface=True),
             Bone("head", *head, parent="neck", surface=True)]
        for side, sx in (("L", 1.0), ("R", -1.0)):
            a, e = (Vector(p) for p in ears)
            b.append(Bone(f"ear.{side}", (a.x * sx, a.y, a.z), (e.x * sx, e.y, e.z), parent="head"))
        parent = "body"
        for i, (p, q) in enumerate(zip(tail, tail[1:])):
            b.append(Bone(f"tail.{i + 1}", p, q, parent=parent))
            parent = f"tail.{i + 1}"
        self.leg_points = {}
        for leg in LEGS:
            src = legs["F" if leg[0] == "F" else "H"]
            sx = 1.0 if leg[1] == "L" else -1.0
            hip, knee, ankle, toe = (Vector((p[0] * sx, p[1], p[2])) for p in src)
            self.leg_points[leg] = (hip, knee, ankle, toe)
            # Leg bones only pull on the leg itself: near its axis and below
            # where it leaves the body (a low belly is as close to the knee
            # as to the spine).
            around = (hip.x, hip.y, leg_reach)
            b.append(Bone(f"leg_upper.{leg}", hip, knee, parent="body", surface=True, fade=fade, around=around))
            b.append(Bone(f"leg_lower.{leg}", knee, ankle, parent=f"leg_upper.{leg}", surface=True, fade=fade,
                          around=around))
            b.append(Bone(f"foot.{leg}", ankle, toe, parent=f"leg_lower.{leg}", surface=True, fade=fade,
                          around=around))
        self.bones = b
        self.by_name = {x.name: x for x in b}

    # ------------------------------------------------------------ binding

    def cuts(self):
        """Rings cut around each leg where it bends (the knee and where it
        leaves the body). Decimation leaves long triangles from the hoof to
        the belly; without vertices at a joint the leg would bend like a
        rubber wedge. Same form as Spec.cuts: (point, normal, region)."""
        out = []
        for leg in LEGS:
            hip, knee, ankle, toe = self.leg_points[leg]
            axis = (hip.x, hip.y)

            def near(c, n, axis=axis):
                return math.hypot(c.x - axis[0], c.y - axis[1]) < self.leg_reach and c.z < self.leg_exit[1]
            out.append((knee, (0, 0, 1), near))
            out.append((Vector((hip.x, hip.y, self.leg_exit[0])), (0, 0, 1), near))
        return out

    def bind(self, mb):
        """Writes bone weights into the builder's vertices."""
        bm = mb.bm
        bm.verts.ensure_lookup_table()
        surface = [x for x in self.bones if x.surface]
        feet = [x for x in self.bones if x.name.startswith("foot.")]
        for v in bm.verts[:mb.detail_from]:
            # Hooves and paws are rigid: below the ankle only the foot counts,
            # or they would tilt with the leg and dig into the ground.
            foot = min(feet, key=lambda x: segment_distance(v.co, x.head, x.tail))
            if v.co.z <= foot.head.z:
                v[mb.deform][mb._group_index(foot.name)] = 1.0
                continue
            cands = []
            for bone in surface:
                reach = bone.reach(v.co)
                if reach <= 0.0:
                    continue
                # A faded bone counts as farther away, so it only wins near the leg.
                d = segment_distance(v.co, bone.head, bone.tail) + (1.0 - reach) * self.blend * 3
                cands.append((d, bone.name))
            d0 = min(d for d, _ in cands)
            weights = sorted(((max(0.0, 1.0 - (d - d0) / self.blend) ** 2, n) for d, n in cands), reverse=True)[:4]
            total = sum(w for w, _ in weights)
            for w, n in weights:
                if w > 0.0:
                    v[mb.deform][mb._group_index(n)] = w / total
        # Detail pieces: connected groups of vertices, each on one bone.
        seen = set()
        for v in bm.verts[mb.detail_from:]:
            if v.index in seen:
                continue
            piece, stack = [], [v]
            seen.add(v.index)
            while stack:
                u = stack.pop()
                piece.append(u)
                for e in u.link_edges:
                    w = e.other_vert(u)
                    if w.index not in seen:
                        seen.add(w.index)
                        stack.append(w)
            center = sum((u.co for u in piece), Vector()) / len(piece)
            bone = min(self.bones, key=lambda x: segment_distance(center, x.head, x.tail))
            group = mb._group_index(bone.name)
            for u in piece:
                u[mb.deform][group] = 1.0

    def build_armature(self, name):
        data = bpy.data.armatures.new(name)
        arm = bpy.data.objects.new(name, data)
        bpy.context.scene.collection.objects.link(arm)
        common.select_only([arm])
        bpy.ops.object.mode_set(mode="EDIT")
        for bone in self.bones:
            eb = data.edit_bones.new(bone.name)
            eb.head = bone.head
            eb.tail = bone.tail
            eb.roll = 0.0
            if bone.parent:
                eb.parent = data.edit_bones[bone.parent]
                eb.use_connect = False
        bpy.ops.object.mode_set(mode="OBJECT")
        return arm

    # -------------------------------------------------------------- poses

    def leg_pose(self, leg, target, pitch, dz, pivot, lift_toe=0.0):
        """Two-bone IK in the side plane: local X rotations (degrees) of the
        leg's bones so the ankle reaches `target` with the body pitched by
        `pitch` (radians, about X through `pivot`) and lowered by `dz`."""
        hip, knee, ankle, toe = self.leg_points[leg]
        rot = Quaternion(X, pitch)
        hip_now = pivot + rot @ (hip - pivot) + Vector((0, 0, dz))
        l1, l2 = (knee - hip).length, (ankle - knee).length
        dy, dzz = target.y - hip_now.y, target.z - hip_now.z
        d = max(abs(l1 - l2) + 1e-4, min(l1 + l2 - 1e-4, math.hypot(dy, dzz)))
        base = math.atan2(dy, -dzz)
        a = math.acos(max(-1.0, min(1.0, (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d))))
        # The joint that shows below the body points forward on a front leg
        # (the carpus) and back on a hind leg (the hock).
        bend = -1.0 if leg[0] == "F" else 1.0
        phi1 = base + a * bend
        knee_now = Vector((0, hip_now.y + l1 * math.sin(phi1), hip_now.z - l1 * math.cos(phi1)))
        phi2 = math.atan2(target.y - knee_now.y, -(target.z - knee_now.z))
        r1 = math.atan2((knee - hip).y, -(knee - hip).z)
        r2 = math.atan2((ankle - knee).y, -(ankle - knee).z)
        # d1, d2: world turns of the bones; each local turn is what its
        # parent chain has not turned yet. The foot stays level (plus lift_toe).
        d1, d2 = phi1 - r1, phi2 - r2
        return {
            f"leg_upper.{leg}": [(X, math.degrees(d1 - pitch))],
            f"leg_lower.{leg}": [(X, math.degrees(d2 - d1))],
            f"foot.{leg}": [(X, math.degrees(lift_toe - d2))],
        }

    def planted(self, rot, pitch=0.0, dz=0.0):
        """Poses every leg with its foot where it stands at rest."""
        pivot = self.by_name["body"].head
        for leg in LEGS:
            rot.update(self.leg_pose(leg, self.leg_points[leg][2], pitch, dz, pivot))
        return rot

    def tail_rot(self, rot, side_deg, up_deg=0.0):
        for bone in self.bones:
            if bone.name.startswith("tail."):
                rot[bone.name] = [(Z, side_deg), (X, up_deg)]

    def gait_pose(self, g, t):
        p = 2 * math.pi * t
        dz = -g.crouch + g.bob * math.cos(2 * p)
        pivot = self.by_name["body"].head
        rot = {}
        for leg in LEGS:
            ankle = self.leg_points[leg][2]
            psi = (t + g.phases[leg]) % 1.0
            if psi < g.duty:
                u = psi / g.duty
                y = ankle.y - g.stride / 2 + g.stride * u
                z = ankle.z
                toe = 0.0
            else:
                u = (psi - g.duty) / (1 - g.duty)
                y = ankle.y + g.stride / 2 - g.stride * smooth(u)
                z = ankle.z + g.lift * math.sin(math.pi * u)
                toe = math.radians(-25.0) * math.sin(math.pi * u)  # The hoof tips back while it swings.
            rot.update(self.leg_pose(leg, Vector((ankle.x, y, z)), 0.0, dz, pivot, toe))
        rot["neck"] = [(X, -g.nod * 0.5 * math.cos(2 * p))]
        rot["head"] = [(X, g.nod * math.cos(2 * p)), (Z, 2.0 * math.sin(p))]
        rot["chest"] = [(Z, -2.0 * math.sin(p))]
        for side in ("L", "R"):
            rot[f"ear.{side}"] = [(X, 8.0 * math.cos(2 * p + 0.6))]
        self.tail_rot(rot, g.wag * math.sin(p), 5.0 * math.cos(2 * p))
        return rot, Vector((0, 0, dz)), {}

    def idle_pose(self, t):
        p = 2 * math.pi * t
        breath = math.sin(3 * p)  # Three breaths per loop.
        dz = -0.004 * breath
        rot = self.planted({}, 0.0, dz)
        rot["chest"] = [(X, 1.2 * breath)]
        look = math.sin(p)
        rot["neck"] = [(Z, 6.0 * look)]
        rot["head"] = [(Z, 8.0 * look), (X, -2.0 * breath)]
        # An ear flick in the second half of the loop.
        flick = math.sin(math.pi * max(0.0, min(1.0, (t - 0.6) / 0.08)))
        rot["ear.L"] = [(X, 15.0 * flick)]
        rot["ear.R"] = [(X, 4.0 * breath)]
        self.tail_rot(rot, 18.0 * math.sin(2 * p), 3.0 * breath)
        return rot, Vector((0, 0, dz)), {}

    def eat_pose(self, t):
        # Head goes down, roots about, and comes back up: starts and ends
        # at the idle pose, so switching clips does not jump.
        down = smooth(t / 0.2) * (1 - smooth((t - 0.8) / 0.2))
        root = math.sin(2 * math.pi * 6 * t) * smooth((t - 0.2) / 0.05) * (1 - smooth((t - 0.75) / 0.05))
        pitch = math.radians(5.0) * down
        dz = -0.02 * down
        rot = self.planted({}, pitch, dz)
        rot["body"] = [(X, math.degrees(pitch))]
        rot["neck"] = [(X, 20.0 * down)]
        rot["head"] = [(X, 25.0 * down + 6.0 * root)]
        rot["ear.L"] = [(X, 10.0 * down)]
        rot["ear.R"] = [(X, 10.0 * down)]
        self.tail_rot(rot, 25.0 * math.sin(2 * math.pi * 4 * t) * down)
        return rot, Vector((0, 0, dz)), {}

    def die_pose(self, t):
        # Knees give way, then it rolls onto its right side (-X) and lies still.
        sag = smooth(t / 0.35)
        roll = smooth((t - 0.3) / 0.45)
        pivot = self.by_name["body"].head
        lie = self.lie_height if self.lie_height is not None else pivot.z * 0.6
        dz = -0.08 * sag * (1 - roll) + (lie - pivot.z) * roll
        buckle = self.planted({}, 0.0, -0.08 * sag)
        rot = {}
        for name, value in buckle.items():
            deg = value[0][1] * (1 - roll) + (8.0 if name.startswith("leg_upper") else 0.0) * roll
            rot[name] = [(X, deg)]
        rot["body"] = [(Y, -88.0 * roll)]
        rot["neck"] = [(X, 10.0 * sag), (Y, -10.0 * roll)]
        rot["head"] = [(X, 12.0 * sag), (Y, -8.0 * roll)]
        for side in ("L", "R"):
            rot[f"ear.{side}"] = [(X, -15.0 * roll)]
        self.tail_rot(rot, 0.0, -20.0 * roll)
        return rot, Vector((0, 0, dz)), {}

    def clips(self):
        """(name, frames, loops, pose function, speed or None)."""
        return [
            ("idle", self.idle_frames, True, self.idle_pose, None),
            ("walk", self.walk.frames, True, lambda t: self.gait_pose(self.walk, t), self.walk.speed),
            ("run", self.run.frames, True, lambda t: self.gait_pose(self.run, t), self.run.speed),
            ("eat", self.eat_frames, True, self.eat_pose, None),
            ("die", self.die_frames, False, self.die_pose, None),
        ]


def pose_key(arm, frame, rotations, offset):
    """Keys every bone at `frame`. `rotations` maps a bone to a list of
    (armature axis, degrees) applied in order; the root bone ("body") also
    moves by `offset` (armature space)."""
    for pb in arm.pose.bones:
        rest = pb.bone.matrix_local.to_3x3()
        q = Quaternion()
        for axis, deg in rotations.get(pb.name, []):
            q = Quaternion(Vector(axis), math.radians(deg)) @ q
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = (rest.transposed() @ q.to_matrix() @ rest).to_quaternion()
        pb.keyframe_insert(data_path="rotation_quaternion", frame=frame)
        pb.location = rest.transposed() @ offset if pb.parent is None else Vector((0, 0, 0))
        pb.keyframe_insert(data_path="location", frame=frame)


def add_clip(arm, name, frames, loops, pose_fn):
    action = bpy.data.actions.new(name)
    action.use_fake_user = True
    arm.animation_data_create()
    arm.animation_data.action = action
    for f in range(frames + 1):
        t = (f % frames) / frames if loops else f / frames
        rot, offset, _ = pose_fn(t)
        pose_key(arm, f, rot, offset)
    return action


def export_rigged(spec, mb, path):
    """Binds the finished builder to the spec's skeleton, keys the clips
    and exports the model with its animations."""
    rig = spec.rig
    rig.bind(mb)
    arm = rig.build_armature(spec.name + "_rig")
    mesh = mb.to_object(spec.name, spec.colors)
    mesh.parent = arm
    mod = mesh.modifiers.new("Armature", "ARMATURE")
    mod.object = arm
    for name, frames, loops, pose_fn, speed in rig.clips():
        add_clip(arm, name, frames, loops, pose_fn)
        if speed is not None:
            arm[f"{name}_speed"] = speed
    arm.animation_data.action = None
    for pb in arm.pose.bones:
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
    common.export_glb(path, [arm, mesh], animations=True, extras=True)
