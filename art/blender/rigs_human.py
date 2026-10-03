"""Skeleton and procedural animations for the low-poly characters
(art/blender/people), shared by every character (phase 48).

The 17 bones have the names of the game's villagers (human.py): hips,
spine, chest, neck, head, and on each side upper_arm, lower_arm, hand,
thigh, shin and foot (".L" is the character's left, +X). A character adds
its own bones (a tail, a cape, a ponytail) with extra_bones and poses them
in pose_extra().

Clips, all in place:
- idle, walk and run (the planted foot moves back at the clip's speed);
- chop: a two-handed swing of an axe at a trunk in front;
- shoot: raise a bow, draw, hold, release and lower it;
- fish_cast (plays once), fish_stand and fish_sit (sitting on the ground),
  holding a rod.
The tool is a separate model. It goes in the hand named by the model's
extras "<clip>_prop" ("axe:hand.R"), with the tool's long axis (its +Z)
along the hand's forward direction: -Y while the arm hangs at rest.

Weights: each point of the welded surface follows the bone of its nearest
body part, blending with the next bone only around the joint between them.
"""

import math

from mathutils import Quaternion, Vector

import rigs
from rigs import FPS, X, Y, Z, Bone, Pose, smooth

SIDES = (("L", 1.0), ("R", -1.0))
# Which bone each welded body part follows; limbs get their side's suffix.
PART_BONES = {
    "head": "head", "jaw": "head", "neck": "neck", "chest": "chest", "bust": "chest", "waist": "spine",
    "hips": "hips", "shoulder": "upper_arm", "upper_arm": "upper_arm", "forearm": "lower_arm", "hand": "hand",
    "thigh": "thigh", "shin": "shin", "foot": "foot",
}


def lerp(a, b, t):
    return a + (b - a) * t


class Humanoid(rigs.Rig):
    """spec: the people._human.Human being rigged. Its limb bones follow
    the spec's limb parts, so a character posed differently at rest (an arm
    raised to hold a staff) gets bones along its own limbs.
    part_bones: {welded part name: bone} for parts the character added.
    """

    def __init__(self, spec, extra_bones=(), part_bones=None):
        self.spec = spec
        k = self.k = spec.k
        self.blend = 0.045 * k
        self.part_bones = dict(part_bones or {})
        joints = spec.joints()
        z = spec.z

        def joint(name, sx):
            p = joints[name]
            return Vector(spec.P(p[0] * sx, p[1], p[2]))

        def capsule(part, a, b):
            """The ends of a limb's part, or the body's own joints."""
            p = spec.parts.get(part)
            return (Vector(p[1]), Vector(p[2])) if p is not None and p[0] == "capsule" else (a, b)

        hip_z = joints["hip"][2] * k
        b = [Bone("hips", (0, 0, hip_z), (0, 0, z["waist"])),
             Bone("spine", (0, 0, z["waist"]), (0, 0, z["chest"]), parent="hips"),
             Bone("chest", (0, 0, z["chest"]), (0, 0, z["neck"]), parent="spine"),
             Bone("neck", (0, 0, z["neck"]), (0, 0, z["chin"]), parent="chest"),
             Bone("head", (0, 0, z["chin"]), (0, 0, z["top"]), parent="neck")]
        self.rest = {}
        for side, sx in SIDES:
            shoulder, elbow = capsule(f"upper_arm.{side}", joint("shoulder", sx), joint("elbow", sx))
            elbow, wrist = capsule(f"forearm.{side}", elbow, joint("wrist", sx))
            hand = spec.parts.get(f"hand.{side}")
            hand = Vector(hand[1]) if hand is not None else joint("hand", sx)
            hip, knee = capsule(f"thigh.{side}", joint("hip", sx), joint("knee", sx))
            knee, ankle = capsule(f"shin.{side}", knee, joint("ankle", sx))
            toe = joint("toe", sx)
            toe = Vector((ankle.x, toe.y, toe.z))
            b += [Bone(f"upper_arm.{side}", shoulder, elbow, parent="chest"),
                  Bone(f"lower_arm.{side}", elbow, wrist, parent=f"upper_arm.{side}"),
                  Bone(f"hand.{side}", wrist, wrist + (hand - wrist) * 2.0, parent=f"lower_arm.{side}"),
                  Bone(f"thigh.{side}", hip, knee, parent="hips"),
                  Bone(f"shin.{side}", knee, ankle, parent=f"thigh.{side}"),
                  Bone(f"foot.{side}", ankle, toe, parent=f"shin.{side}")]
            self.rest[side] = {"shoulder": shoulder, "wrist": wrist, "hip": hip, "ankle": ankle}
        self.set_bones(b + list(extra_bones))
        self.arm = (self.by_name["lower_arm.L"].head - self.by_name["upper_arm.L"].head).length + \
            (self.by_name["lower_arm.L"].tail - self.by_name["lower_arm.L"].head).length
        self.leg = min((self.rest[s]["hip"] - self.by_name[f"shin.{s}"].head).length
                       + (self.rest[s]["ankle"] - self.by_name[f"shin.{s}"].head).length for s, _ in SIDES)
        # Gaits: the stride is what the legs can reach at the gait's crouch.
        # The walk is brisk: the villagers of the game cover 2 m a second.
        self.walk = self.gait(frames=16, duty=0.6, crouch=0.045, lift=0.09)
        self.run = self.gait(frames=18, duty=0.38, crouch=0.075, lift=0.17)

    def gait(self, frames, duty, crouch, lift):
        hip, ankle = self.rest["L"]["hip"], self.rest["L"]["ankle"]
        height = hip.z - ankle.z - crouch * self.k
        half = math.sqrt(max(0.0, (self.leg * 0.985) ** 2 - height ** 2))
        stride = 2 * half
        return {"frames": frames, "duty": duty, "crouch": crouch * self.k, "lift": lift * self.k,
                "stride": stride, "speed": stride * FPS / (duty * frames)}

    # ------------------------------------------------------------ binding

    def bone_of_part(self, part):
        if part in self.part_bones:
            return self.part_bones[part]
        base, dot, side = part.partition(".")
        if base in PART_BONES:
            bone = PART_BONES[base]
            return f"{bone}.{side}" if side in ("L", "R") and f"{bone}.{side}" in self.by_name else bone
        return None

    def part_distance(self, p, part):
        if part[0] == "ellipsoid":
            c, r = part[1], part[2]
            q = Vector(((p.x - c[0]) / r[0], (p.y - c[1]) / r[1], (p.z - c[2]) / r[2]))
            return (q.length - 1.0) * min(r)
        return rigs.segment_distance(p, Vector(part[1]), Vector(part[2])) - max(part[3], part[4])

    def nearest_bone(self, p):
        """The bone of the body part nearest to p. A part the character
        added without saying its bone follows the bone nearest to it."""
        best, bone = 1e9, None
        for name, part in self.spec.parts.items():
            d = self.part_distance(p, part)
            if d < best:
                best, bone = d, self.bone_of_part(name)
                if bone is None:
                    bone = min(self.bones[:17], key=lambda b: rigs.segment_distance(p, b.head, b.tail)).name
        return bone

    def surface_weights(self, p):
        name = self.nearest_bone(p)
        bone = self.by_name[name]
        # Feet are rigid, so boots stay flat on the ground.
        if name.startswith(("foot.", "shin.")) and p.z <= self.by_name["foot." + name[-1]].head.z:
            return [("foot." + name[-1], 1.0)]
        weights = [(name, 1.0)]
        # Blend with the parent across the joint at this bone's start, and
        # with each child across the joint at the child's start.
        links = [(bone.parent, bone.head, bone.tail - bone.head)] if bone.parent else []
        links += [(c.name, c.head, c.head - c.tail) for c in self.bones if c.parent == name]
        for other, at, inward in links:
            reach = (p - at).length
            if reach > self.blend * 4:
                continue
            depth = (p - at).dot(inward.normalized())  # How far into this bone's side.
            w = max(0.0, min(0.5, 0.5 - depth / (2 * self.blend)))
            weights.append((other, w * max(0.0, 1.0 - reach / (self.blend * 4))))
        return weights

    def cuts(self):
        """Rings at the knees and elbows, so the limbs bend there."""
        out = []
        for side, _ in SIDES:
            for upper, lower in ((f"thigh.{side}", f"shin.{side}"), (f"upper_arm.{side}", f"lower_arm.{side}")):
                at = self.by_name[lower].head
                normal = (self.by_name[lower].tail - self.by_name[upper].head).normalized()

                def near(c, n, at=at, pair=(upper, lower)):
                    return (c - at).length < 0.16 * self.k and self.nearest_bone(c) in pair
                out.append((at, normal, near))
        return out

    # -------------------------------------------------------------- poses

    def stand(self, pose, feet=None, yaw=0.0):
        """Plants the feet: at their rest places, or at `feet`, offsets
        {side: (x, y)} in meters of a 1.8 m body; the feet turn by `yaw`."""
        for side, sx in SIDES:
            ankle = self.rest[side]["ankle"].copy()
            if feet:
                ankle += Vector((feet[side][0], feet[side][1], 0)) * self.k
            forward = Quaternion(Z, math.radians(yaw)) @ Vector((0, -1, 0))
            pose.limb(f"thigh.{side}", f"shin.{side}", ankle, forward + Vector((sx * 0.15, 0, 0.2)))
            pose.set_world(f"foot.{side}", Quaternion(Z, math.radians(yaw)))

    def hold(self, pose, grip, direction, hand="R", other=0.26, side=None):
        """Both hands on a tool: the `hand` at `grip`, the other one `other`
        meters (of a 1.8 m body) behind it along the tool, toward its butt.
        The hand turns so the tool points along `direction`."""
        direction = Vector(direction).normalized()
        second = "L" if hand == "R" else "R"
        sx = 1.0 if hand == "L" else -1.0
        pose.limb(f"upper_arm.{hand}", f"lower_arm.{hand}", grip, Vector((sx * 0.6, 0.5, -1.0)))
        pose.orient(f"hand.{hand}", direction, side if side is not None else Vector((1, 0, 0)))
        if other is not None:
            pose.limb(f"upper_arm.{second}", f"lower_arm.{second}", Vector(grip) - direction * other * self.k,
                      Vector((-sx * 0.6, 0.5, -1.0)))
            pose.aim(f"hand.{second}", direction.cross(Vector((0, 0, 1))) * sx + Vector((0, -0.4, -0.3)))

    def hang_arm(self, pose, side, swing=0.0, bend=8.0):
        pose.turn(f"upper_arm.{side}", X, swing)
        pose.turn(f"lower_arm.{side}", X, -bend)

    def gait_pose(self, g, t, lean, arm_swing, arm_bend, sway):
        p = 2 * math.pi * t
        k = self.k
        pose = Pose(self, (sway * k * math.sin(p), 0, -g["crouch"] + 0.012 * k * math.cos(2 * p)))
        pose.turn("hips", Z, 4.0 * math.sin(p))
        pose.turn("spine", X, lean)
        pose.turn("chest", Z, -7.0 * math.sin(p))
        pose.turn("neck", X, -lean * 0.6)
        pose.turn("head", Z, 3.0 * math.sin(p))
        for (side, sx), phase in zip(SIDES, (0.0, 0.5)):
            ankle = self.rest[side]["ankle"]
            psi = (t + phase) % 1.0
            if psi < g["duty"]:
                u = psi / g["duty"]
                y, zz, toe = ankle.y - g["stride"] / 2 + g["stride"] * u, ankle.z, 0.0
                front = math.cos(math.pi * u)        # 1: this leg forward; -1: back.
            else:
                u = (psi - g["duty"]) / (1 - g["duty"])
                y = ankle.y + g["stride"] / 2 - g["stride"] * smooth(u)
                zz = ankle.z + g["lift"] * math.sin(math.pi * u)
                toe = 25.0 * math.sin(math.pi * u) * (1 - u)   # Toes down as the foot leaves the ground.
                front = -math.cos(math.pi * u)
            pose.limb(f"thigh.{side}", f"shin.{side}", Vector((ankle.x, y, zz)), Vector((sx * 0.1, -1, 0.3)))
            pose.set_world(f"foot.{side}", Quaternion(X, math.radians(toe)))
            # The arm swings against its leg.
            self.hang_arm(pose, side, arm_swing * front, arm_bend + arm_swing * 0.4 * max(0.0, -front))
        return pose.q, pose.offset, {}

    def idle_pose(self, t):
        p = 2 * math.pi * t
        breath = math.sin(3 * p)
        pose = Pose(self, (0.004 * self.k * math.sin(p), 0, -0.004 * self.k * (1 + breath)))
        self.stand(pose)
        pose.turn("spine", X, 0.8 * breath)
        pose.turn("chest", X, 1.2 * breath)
        pose.turn("neck", Z, 5.0 * math.sin(p))
        pose.turn("head", Z, 7.0 * math.sin(p))
        pose.turn("head", X, -1.5 * breath)
        for side, sx in SIDES:
            self.hang_arm(pose, side, 1.5 * breath, 8.0 + 2.0 * breath)
        return pose.q, pose.offset, {}

    def chop_pose(self, t):
        k = self.k
        # 0: the axe in the trunk; 1: wound up over the right shoulder.
        if t < 0.45:
            w = smooth(t / 0.45)
        elif t < 0.55:
            w = 1.0
        elif t < 0.67:
            w = 1.0 - ((t - 0.55) / 0.12) ** 2   # Speeds up into the strike.
        else:
            w = 0.03 * math.sin(math.pi * (t - 0.67) / 0.33)  # A small recoil.
        pose = Pose(self, (0, 0, (-0.07 + 0.03 * w) * k))
        pose.turn("hips", Z, lerp(10.0, -12.0, w))
        self.stand(pose, {"L": (0.05, -0.14), "R": (-0.06, 0.12)}, yaw=-12.0)
        pose.turn("spine", Z, lerp(8.0, -14.0, w))
        pose.turn("spine", X, lerp(12.0, 0.0, w))
        pose.turn("chest", Z, lerp(10.0, -18.0, w))
        pose.set_world("head", Quaternion(X, math.radians(8.0)))
        strike = Vector((0.06, -0.36, 1.1)) * k
        wound = Vector((-0.24, -0.02, 1.52)) * k
        arc = Vector((-0.1, -0.2, 0.12)) * k * math.sin(math.pi * w)   # The grip travels on an arc.
        grip = strike.lerp(wound, w) + arc
        direction = Vector((0.5, -0.85, -0.1)).normalized().slerp(Vector((-0.3, 0.55, 0.78)).normalized(), w)
        self.hold(pose, grip, direction, hand="R", other=0.24, side=Vector((1, 0.3, 0)))
        return pose.q, pose.offset, {}

    def work_pose(self, t):
        """Hammering on something at waist height in front, with the right
        hand; the left one steadies the piece. The trades without a clip of
        their own use it."""
        k = self.k
        # 0: the hammer on the piece; 1: raised by the right shoulder.
        if t < 0.5:
            w = smooth(t / 0.5)
        elif t < 0.64:
            w = 1.0 - ((t - 0.5) / 0.14) ** 2    # Speeds up into the blow.
        else:
            w = 0.04 * math.sin(math.pi * (t - 0.64) / 0.36)  # A small bounce.
        pose = Pose(self, (0, 0, (-0.05 + 0.015 * w) * k))
        self.stand(pose, {"L": (0.03, -0.1), "R": (-0.03, 0.08)})
        pose.turn("spine", X, lerp(14.0, 6.0, w))
        pose.turn("chest", X, lerp(8.0, 2.0, w))
        pose.turn("chest", Z, lerp(4.0, -8.0, w))
        pose.set_world("head", Quaternion(X, math.radians(14.0)))
        low = Vector((-0.1, -0.4, 1.02)) * k
        high = Vector((-0.24, -0.22, 1.42)) * k
        grip = low.lerp(high, w) + Vector((0, -0.08, 0.04)) * k * math.sin(math.pi * w)
        direction = Vector((0.15, -0.95, -0.25)).normalized().slerp(Vector((0.0, -0.25, 0.97)).normalized(), w)
        self.hold(pose, grip, direction, hand="R", other=None, side=Vector((1, 0, 0)))
        pose.limb("upper_arm.L", "lower_arm.L", Vector((0.14, -0.36, 0.98)) * k, Vector((0.6, 0.5, -1.0)))
        pose.aim("hand.L", Vector((-0.3, -0.8, -0.5)))
        return pose.q, pose.offset, {}

    def shoot_pose(self, t):
        k = self.k
        up = smooth(t / 0.2) * (1 - smooth((t - 0.8) / 0.2))          # Bow raised.
        draw = smooth((t - 0.2) / 0.3) if t < 0.7 else 0.0            # String drawn; let go at 0.7.
        after = smooth((t - 0.7) / 0.05) * (1 - smooth((t - 0.8) / 0.2))
        pose = Pose(self, (0, 0, -0.03 * k))
        turned = -50.0   # The body turns to the right: the left shoulder leads.
        pose.turn("hips", Z, turned)
        self.stand(pose, {"L": (-0.02, -0.2), "R": (-0.1, 0.16)}, yaw=turned * 0.7)
        pose.turn("spine", Z, -10.0 * up)
        pose.turn("chest", Z, -15.0 * up)
        pose.set_world("head", Quaternion(Z, math.radians(-8.0)))   # Looks at the target.
        shoulder = pose.head("upper_arm.L")
        lowered = shoulder + Vector((0.1, -0.22, -0.42)) * k
        aimed = shoulder + Vector((0.0, -1.0, 0.04)) * self.arm * 0.96
        bow = lowered.lerp(aimed, up)
        pose.limb("upper_arm.L", "lower_arm.L", bow, Vector((0.5, 0.2, -1.0)))
        # The bow stands upright when aimed, the string toward the archer.
        pose.orient("hand.L", Vector((0, -0.75, 0.35)).normalized().slerp(Vector((0, 0, 1)), up),
                    Vector((0.4, 1, 0)).lerp(Vector((0, 1, 0)), up))
        chin = pose.head("head") + Vector((0.02, -0.05, 0.02)) * k
        string = bow + Vector((0.0, 0.12, 0.0)) * k
        resting = pose.head("upper_arm.R") + Vector((-0.04, -0.2, -0.4)) * k
        hand = resting.lerp(string.lerp(chin, draw), up) + Vector((0, 0.07, 0)) * k * after
        pose.limb("upper_arm.R", "lower_arm.R", hand, Vector((-0.5, 0.9, 0.25)))
        pose.aim("hand.R", (bow - hand) + Vector((0, 0, -0.1)))
        return pose.q, pose.offset, {}

    def rod_pose(self, pose, grip, direction, t, tug=1.0):
        """Holds the rod with small movements and a tug in the middle."""
        p = 2 * math.pi * t
        pull = math.sin(math.pi * max(0.0, min(1.0, (t - 0.55) / 0.12))) * tug
        direction = Vector(direction).normalized()
        direction = (direction + Vector((0.02 * math.sin(p), 0, 0.03 * math.sin(2 * p) + 0.25 * pull))).normalized()
        grip = Vector(grip) + Vector((0, 0.03 * pull, 0.01 * math.sin(p) + 0.04 * pull)) * self.k
        self.hold(pose, grip, direction, hand="R", other=0.2)

    def fish_stand_pose(self, t):
        k = self.k
        p = 2 * math.pi * t
        pose = Pose(self, (0.006 * k * math.sin(p), 0, -0.02 * k))
        self.stand(pose, {"L": (0.03, -0.06), "R": (-0.03, 0.05)})
        pose.turn("spine", X, 4.0 + 1.0 * math.sin(2 * p))
        pose.turn("head", X, 8.0)
        pose.turn("head", Z, 4.0 * math.sin(p))
        self.rod_pose(pose, Vector((-0.1, -0.3, 1.08)) * k, (0, -0.8, 0.6), t)
        return pose.q, pose.offset, {}

    def fish_cast_pose(self, t):
        k = self.k
        back = smooth(t / 0.4) * (1 - smooth((t - 0.5) / 0.18))   # The rod goes back, then whips forward.
        pose = Pose(self, (0, 0, -0.02 * k))
        self.stand(pose, {"L": (0.03, -0.06), "R": (-0.03, 0.05)})
        pose.turn("spine", X, lerp(4.0, -8.0, back))
        pose.turn("chest", Z, -12.0 * back)
        pose.turn("head", X, 8.0 * (1 - back))
        grip = (Vector((-0.1, -0.3, 1.08)).lerp(Vector((-0.2, -0.05, 1.5)), back)) * k
        direction = Vector((0, -0.8, 0.6)).normalized().slerp(Vector((-0.1, 0.55, 0.83)).normalized(), back)
        self.hold(pose, grip, direction, hand="R", other=0.2)
        return pose.q, pose.offset, {}

    def fish_sit_pose(self, t):
        k = self.k
        p = 2 * math.pi * t
        seat = 0.11 * k   # Height of the hip joints when sitting on the ground.
        pose = Pose(self, (0, 0.12 * k, seat - self.by_name["hips"].head.z))
        pose.turn("hips", X, -14.0)   # Leans back a little on the seat.
        for side, sx in SIDES:
            ankle = self.rest[side]["ankle"]
            target = Vector((ankle.x + sx * 0.05 * k, -0.5 * k, ankle.z))
            pose.limb(f"thigh.{side}", f"shin.{side}", target, Vector((sx * 0.25, -0.2, 1.0)))
            pose.set_world(f"foot.{side}", Quaternion())
        pose.turn("spine", X, 16.0 + 1.0 * math.sin(2 * p))
        pose.turn("chest", X, 10.0)
        pose.set_world("head", Quaternion(X, math.radians(6.0)) @ Quaternion(Z, math.radians(4.0 * math.sin(p))))
        self.rod_pose(pose, Vector((-0.1, -0.34, 0.5)) * k, (0, -0.85, 0.5), t)
        return pose.q, pose.offset, {}

    def clips(self):
        w, r = self.walk, self.run
        return [
            ("idle", 90, True, self.idle_pose, None),
            ("walk", w["frames"], True, lambda t: self.gait_pose(w, t, 2.0, 20.0, 10.0, 0.012), w["speed"]),
            ("run", r["frames"], True, lambda t: self.gait_pose(r, t, 9.0, 38.0, 70.0, 0.008), r["speed"]),
            ("chop", 40, True, self.chop_pose, None),
            ("shoot", 75, True, self.shoot_pose, None),
            ("fish_cast", 40, False, self.fish_cast_pose, None),
            ("fish_stand", 120, True, self.fish_stand_pose, None),
            ("fish_sit", 120, True, self.fish_sit_pose, None),
            ("work", 30, True, self.work_pose, None),
        ]

    def clip_props(self):
        return {"chop": "axe:hand.R", "shoot": "bow:hand.L", "fish_cast": "rod:hand.R",
                "fish_stand": "rod:hand.R", "fish_sit": "rod:hand.R", "work": "hammer:hand.R"}
