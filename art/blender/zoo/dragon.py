"""Dragon: red, standing on four legs, with an orange-yellow belly, a long
S-curved neck and a long tail ending in a spade, golden horns and spikes
along the back, and big bat wings raised: membrane panels stretched
between finger bones."""

import math
import random

from mathutils import Quaternion, Vector

import common
import rigs
import studies

X_LEG = 0.55
FRONT_LEG = [((X_LEG * 0.9, -0.95, 1.55), (X_LEG * 1.05, -0.72, 0.85), 0.32, 0.21),
             ((X_LEG * 1.05, -0.72, 0.85), (X_LEG * 1.05, -1.05, 0.17), 0.2, 0.16),
             ((X_LEG * 1.05, -1.03, 0.14), (X_LEG * 1.05, -1.38, 0.12), 0.18, 0.13)]
HIND_LEG = [((X_LEG, 0.65, 1.1), (X_LEG * 1.05, 1.05, 0.55), 0.32, 0.19),
            ((X_LEG * 1.05, 1.05, 0.55), (X_LEG * 1.05, 0.9, 0.17), 0.17, 0.16),
            ((X_LEG * 1.05, 0.92, 0.14), (X_LEG * 1.05, 0.56, 0.12), 0.18, 0.13)]
THIGH = ((X_LEG * 0.9, 0.55, 1.3), (0.32, 0.6, 0.62))
NECK = [(0.0, -1.4, 2.05), (0.0, -1.95, 2.65), (0.0, -2.15, 3.15), (0.0, -2.3, 3.38)]
NECK_R = [0.45, 0.33, 0.27, 0.26]
TAIL = [(0.0, 1.2, 1.7), (0.0, 2.1, 1.3), (0.15, 2.9, 0.85), (0.55, 3.5, 0.55), (1.05, 3.85, 0.4)]
TAIL_R = [0.42, 0.3, 0.2, 0.13, 0.08]
HEAD_Z = 3.42
HEAD = ((0.0, -2.42, HEAD_Z), (0.31, 0.42, 0.3))
SNOUT = ((0.0, -2.6, HEAD_Z - 0.06), (0.0, -3.1, HEAD_Z - 0.16), 0.23, 0.15)
JAW = ((0.0, -2.45, HEAD_Z - 0.22), (0.0, -2.95, HEAD_Z - 0.3), 0.17, 0.1)
EYE = (0.25, -2.66, HEAD_Z + 0.08)
# Wing, right side: shoulder, elbow, wrist, the finger tips (front to
# back) and where the membrane meets the back.
SHOULDER, ELBOW, WRIST = Vector((0.42, -0.75, 2.3)), Vector((1.25, -0.55, 3.35)), Vector((1.7, -0.15, 4.25))
FINGERS = [Vector(p) for p in ((2.6, 0.35, 4.45), (2.55, 1.25, 3.7), (2.15, 1.95, 2.8), (1.45, 2.1, 2.1))]
BACK = Vector((0.36, 1.0, 2.15))
SPINE = [(0.0, -2.2, HEAD_Z - 0.1), (0.0, -1.95, 2.65), (0.0, -1.4, 2.05), (0.0, -0.9, 1.9), (0.0, 0.4, 1.7),
         (0.0, 1.2, 1.7), (0.0, 2.1, 1.3), (0.15, 2.9, 0.85), (0.55, 3.5, 0.55)]


def tone_faces(mb, mat, share, seed=11):
    """Facet tones for a second material (finish() only tones one): turns a
    share of its faces into <mat>_light and <mat>_shade."""
    if mat not in mb.materials:
        return
    rnd = random.Random(seed)
    main = mb.materials.index(mat)
    light, shade = mb._material_index(mat + "_light"), mb._material_index(mat + "_shade")
    for f in mb.bm.faces:
        if f.material_index == main:
            r = rnd.random()
            if r < share * 0.5:
                f.material_index = light
            elif r < share:
                f.material_index = shade


def near_capsule(c, caps, margin):
    """Whether point c is within `margin` of any of the capsules."""
    for a, b, ra, rb in caps:
        a, b = Vector(a), Vector(b)
        ba = b - a
        h = max(0.0, min(1.0, (c - a).dot(ba) / ba.dot(ba)))
        if (c - a - ba * h).length < ra + (rb - ra) * h + margin:
            return True
    return False


def mirror(p, s):
    return Vector((s * p[0], p[1], p[2]))


def legs():
    return [(mirror(a, s), mirror(b, s), ra, rb) for s in (-1, 1) for a, b, ra, rb in FRONT_LEG + HIND_LEG]


def surface(spec, inside, direction):
    """Marches from a point inside the body along direction to the surface."""
    p, d = Vector(inside), Vector(direction).normalized()
    for _ in range(200):
        if studies.sdf(spec, p) > 0.0:
            return p
        p = p + d * 0.01
    return p


def halved(points, radii, count):
    """The polyline with its first `count` segments cut in two (more bones
    where the tail is long), and the radius at each point."""
    pts, rs = [Vector(points[0])], [radii[0]]
    for i, (a, b) in enumerate(zip(points, points[1:])):
        if i < count:
            pts.append((Vector(a) + Vector(b)) / 2)
            rs.append((radii[i] + radii[i + 1]) / 2)
        pts.append(Vector(b))
        rs.append(radii[i + 1])
    return pts, rs


TAIL_BONES, TAIL_BONES_R = halved(TAIL, TAIL_R, 2)   # Six bones.
NECK_MID = Vector((0.0, -2.2, 3.25))                 # Between the second neck bone and the head.
FINGER_BONES = ("finger.1", "finger.2", "finger.3", "finger.4")
# The axis the fingers close about like a fan (left wing): across the
# plane of the first and the last finger.
WING_FAN = (FINGERS[0] - WRIST).cross(FINGERS[3] - WRIST).normalized()
WING_ARM = (ELBOW - SHOULDER).normalized()


def mirrored(axis, degrees, s):
    """A turn of the left side (s = 1) as it is on the right side (s = -1)."""
    return (axis, degrees) if s > 0 else (Vector((-axis[0], axis[1], axis[2])), -degrees)


class DragonRig(rigs.Quadruped):
    """A quadruped with a neck of two bones, a long tail of six (welded
    surface) and bat wings: arm, forearm and four fingers each, with the
    membrane stretched between them. Adds the fly clip."""

    fly_frames = 24
    fly_speed = 9.0
    SOFT = 0.15  # Width of the weight transition between bones (m).

    def __init__(self, **points):
        wings = []
        for side, s in (("L", 1.0), ("R", -1.0)):
            sh, el, wr = mirror(SHOULDER, s), mirror(ELBOW, s), mirror(WRIST, s)
            wings.append(rigs.Bone(f"wing_arm.{side}", sh, el, parent="chest"))
            wings.append(rigs.Bone(f"wing_fore.{side}", el, wr, parent=f"wing_arm.{side}"))
            for name, tip in zip(FINGER_BONES, FINGERS):
                wings.append(rigs.Bone(f"{name}.{side}", wr, mirror(tip, s), parent=f"wing_fore.{side}"))
        super().__init__(tail=TAIL_BONES, extra_bones=wings, **points)
        # A second neck bone between the template's neck and the head.
        neck, head = self.by_name["neck"], self.by_name["head"]
        neck2 = rigs.Bone("neck.2", neck.tail, head.head, parent="neck", surface=True)
        head.parent = "neck.2"
        bones = list(self.bones)
        bones.insert(bones.index(head), neck2)
        self.set_bones(bones)
        # How thick the body is along each bone that carries welded surface
        # (start, end): weights go by the distance to that thickness, so
        # the belly, far from the spine, does not follow the legs.
        self.radii = {"body": (0.5, 0.66), "chest": (0.68, 0.5), "neck": (0.45, 0.33), "neck.2": (0.33, 0.27),
                      "head": (0.32, 0.16)}
        for i, (r0, r1) in enumerate(zip(TAIL_BONES_R, TAIL_BONES_R[1:])):
            self.radii[f"tail.{i + 1}"] = (r0, r1)
        for leg in rigs.LEGS:
            front = leg[0] == "F"
            self.radii[f"leg_upper.{leg}"] = (0.3, 0.21) if front else (0.34, 0.19)
            self.radii[f"leg_lower.{leg}"] = (0.2, 0.16) if front else (0.17, 0.16)
        # Where the membrane's corners are at rest, and what each follows.
        self.anchors = []
        for side, s in (("L", 1.0), ("R", -1.0)):
            wr = mirror(WRIST, s)
            ends = [(mirror(tip, s), f"{name}.{side}") for name, tip in zip(FINGER_BONES, FINGERS)]
            ends.append((mirror(BACK, s), "body"))
            self.anchors += [(mirror(SHOULDER, s), [("chest", 1.0)]), (mirror(ELBOW, s), [(f"wing_arm.{side}", 1.0)]),
                             (wr, [(f"wing_fore.{side}", 1.0)])]
            self.anchors += [(p, [(bone, 1.0)]) for p, bone in ends]
            for (p0, b0), (p1, b1) in zip(ends, ends[1:]):
                self.anchors.append((membrane_dip(p0, p1, wr), [(b0, 0.5), (b1, 0.5)]))

    # ------------------------------------------------------------ binding

    def surface_weights(self, p):
        feet = [x for x in self.bones if x.name.startswith("foot.")]
        foot = min(feet, key=lambda x: rigs.segment_distance(p, x.head, x.tail))
        if p.z <= foot.head.z:
            return [(foot.name, 1.0)]  # The feet are rigid, as in the template.
        cands = []
        for name, (r0, r1) in self.radii.items():
            bone = self.by_name[name]
            ab = bone.tail - bone.head
            t = max(0.0, min(1.0, (p - bone.head).dot(ab) / ab.dot(ab)))
            cands.append(((p - (bone.head + ab * t)).length - (r0 + (r1 - r0) * t), name))
        d0 = min(d for d, _ in cands)
        return [(n, max(0.0, 1.0 - (d - d0) / self.SOFT) ** 2) for d, n in cands]

    def nearest(self, piece, names):
        bones = [self.by_name[n] for n in names]
        return min(bones, key=lambda b: min(rigs.segment_distance(v.co, b.head, b.tail) for v in piece)).name

    def piece_bone(self, center, piece):
        side = "L" if center.x > 0 else "R"
        if center.z < 0.32 and abs(center.x) > 0.3 and center.y < 2.0:
            return self.nearest(piece, [f"foot.F{side}", f"foot.H{side}"])   # Claws.
        if center.z > 2.0 and abs(center.x) > 0.4:
            # Wing bones, joints and the thumb claw.
            return self.nearest(piece, [f"{n}.{side}" for n in ("wing_arm", "wing_fore") + FINGER_BONES])
        if center.y < -2.5 or (center.y < -1.5 and center.z > HEAD_Z - 0.3 and abs(center.x) > 0.1):
            return "head"   # Eyes, nostrils and horns.
        # Spikes and the tail's fin: the nearest bone of the spine.
        return self.nearest(piece, [b.name for b in self.bones
                                    if b.name in ("body", "chest", "neck", "neck.2") or b.name.startswith("tail.")])

    def piece_weights(self, center, piece):
        """Membrane panels stretch: each corner follows the bone it hangs from."""
        def anchor(p):
            return min(self.anchors, key=lambda a: (a[0] - p).length)
        if len(piece) != 6 or any((anchor(v.co)[0] - v.co).length > 0.03 for v in piece):
            return None
        return lambda p: anchor(p)[1]

    # -------------------------------------------------------------- poses

    def leg_pose(self, leg, target, pitch, dz, pivot, lift_toe=0.0):
        """As the template's, but the elbow of a front leg points backward
        (the template bends a front leg's joint forward, as a hoofed
        animal's carpus)."""
        if leg[0] == "H":
            return super().leg_pose(leg, target, pitch, dz, pivot, lift_toe)
        hip, knee, ankle, toe = self.leg_points[leg]
        hip_now = pivot + Quaternion(rigs.X, pitch) @ (hip - pivot) + Vector((0, 0, dz))
        l1, l2 = (knee - hip).length, (ankle - knee).length
        dy, dzz = target.y - hip_now.y, target.z - hip_now.z
        d = max(abs(l1 - l2) + 1e-4, min(l1 + l2 - 1e-4, math.hypot(dy, dzz)))
        phi1 = math.atan2(dy, -dzz) + math.acos(max(-1.0, min(1.0, (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d))))
        knee_now = Vector((0, hip_now.y + l1 * math.sin(phi1), hip_now.z - l1 * math.cos(phi1)))
        phi2 = math.atan2(target.y - knee_now.y, -(target.z - knee_now.z))
        d1 = phi1 - math.atan2((knee - hip).y, -(knee - hip).z)
        d2 = phi2 - math.atan2((ankle - knee).y, -(ankle - knee).z)
        return {
            f"leg_upper.{leg}": [(rigs.X, math.degrees(d1 - pitch))],
            f"leg_lower.{leg}": [(rigs.X, math.degrees(d2 - d1))],
            f"foot.{leg}": [(rigs.X, math.degrees(lift_toe - d2))],
        }

    def wings(self, rot, fold=0.0, drop=0.0, flat=0.0, flex=0.0, sway=0.0):
        """Turns of the wing bones. fold: 0 raised and open as at rest, 1
        the fingers closed like a fan and the forearm folded back. drop:
        degrees the whole wing comes down from its raised rest. flat:
        degrees the wing turns about its arm (trailing edge up). flex:
        degrees the outer wing lags behind (bends down, or up if
        negative). sway: degrees of the small movement of a wing held
        still (the left one leads)."""
        for side, s in (("L", 1.0), ("R", -1.0)):
            lead = sway if s > 0 else sway * 0.7
            rot[f"wing_arm.{side}"] = [mirrored(WING_ARM, flat, s), mirrored(rigs.Y, drop + lead, s),
                                       mirrored(rigs.Z, 20.0 * fold, s)]
            rot[f"wing_fore.{side}"] = [mirrored(WING_FAN, 30.0 * fold, s), mirrored(rigs.Y, flex + lead * 0.5, s)]
            for i, name in enumerate(FINGER_BONES):
                rot[f"{name}.{side}"] = [mirrored(WING_FAN, (62.0, 40.0, 20.0, 0.0)[i] * fold, s),
                                         mirrored(rigs.Y, flex * (1.2 - 0.15 * i) + lead * 0.5, s)]

    def tail_wave(self, rot, p, swing, lift=()):
        """A wave running down the tail, side to side; `lift` raises each bone."""
        for i in range(len(TAIL_BONES) - 1):
            up = lift[i] if i < len(lift) else 0.0
            rot[f"tail.{i + 1}"] = [(rigs.Z, swing * (0.5 + 0.25 * i) * math.sin(p - 0.8 * i)), (rigs.X, up)]

    def pose_extra(self, clip, t, rot):
        p = 2 * math.pi * t
        if clip == "fly":
            return
        # The second neck bone bends as the first.
        rot["neck.2"] = [(axis, deg * 0.8) for axis, deg in rot.get("neck", [])]
        if clip == "die":
            roll = rigs.smooth((t - 0.3) / 0.45)
            self.wings(rot, fold=0.6 + 0.4 * roll, sway=6.0 * math.sin(6 * p) * (1 - roll))
            rot["wing_arm.L"].append((rigs.Y, -90.0 * roll))
            rot["wing_arm.R"].append((rigs.Y, 35.0 * roll))
            self.tail_wave(rot, 0.0, 0.0, [8.0 * roll] * 6)
        elif clip in ("walk", "run"):
            self.wings(rot, fold=0.6 if clip == "walk" else 0.5, sway=3.0 * math.sin(2 * p + 0.8),
                       flex=4.0 * math.sin(2 * p))
            # The body is lower than at rest: the tail's root lifts a
            # little, so the fin at its tip stays above the ground.
            self.tail_wave(rot, p, 6.0 if clip == "walk" else 9.0, [3.0])
        else:
            self.wings(rot, fold=0.6, sway=2.5 * math.sin(p * (2 if clip == "eat" else 1)))
            self.tail_wave(rot, p, 5.0)
        if clip == "eat":
            # The long neck swings the head down to the ground and the
            # jaws tear at what lies there.
            down = rigs.smooth(t / 0.2) * (1 - rigs.smooth((t - 0.8) / 0.2))
            tear = (math.sin(2 * math.pi * 5 * t) * rigs.smooth((t - 0.2) / 0.05)
                    * (1 - rigs.smooth((t - 0.75) / 0.05)))
            rot["chest"] = [(rigs.X, 10.0 * down)]
            rot["neck"] = [(rigs.X, 47.0 * down + 2.0 * tear)]
            rot["neck.2"] = [(rigs.X, 34.0 * down + 2.0 * tear)]
            rot["head"] = [(rigs.X, -30.0 * down - 6.0 * tear)]

    def fly_pose(self, t):
        p = 2 * math.pi * t
        beat = math.sin(p)
        dz = 0.2 * math.sin(p - 2.0)  # The body rises after each downstroke.
        pivot = self.by_name["body"].head
        rot = {}
        # Legs tucked back under the body.
        for leg in rigs.LEGS:
            hip = self.leg_points[leg][0]
            back, down = (0.75, 0.85) if leg[0] == "F" else (0.95, 0.6)
            swing = 0.05 * math.sin(p + (0.0 if leg[0] == "F" else 1.0))
            target = Vector((hip.x, hip.y + back + swing, hip.z - down + dz))
            rot.update(self.leg_pose(leg, target, 0.0, dz, pivot, math.radians(40.0)))
        # The neck stretches forward and the head stays level.
        nod = 3.0 * math.sin(p - 1.0)
        rot["chest"] = [(rigs.X, -2.0 * beat)]
        rot["neck"] = [(rigs.X, 26.0 + nod)]
        rot["neck.2"] = [(rigs.X, 18.0 + nod)]
        rot["head"] = [(rigs.X, -36.0 - 2 * nod)]
        self.tail_wave(rot, p, 5.0, [20.0 + 4.0 * math.sin(p - 1.0), 2.0, 4.0, 2.0, -2.0, -8.0])
        self.wings(rot, drop=45.0 + 38.0 * beat, flat=24.0 + 10.0 * math.cos(p), flex=20.0 * math.sin(p - 1.1))
        return rot, Vector((0, 0, dz)), {}

    def clips(self):
        return super().clips() + [("fly", self.fly_frames, True, self.fly_pose, self.fly_speed)]


def membrane_dip(f0, f1, wrist):
    """The corner of the membrane between two finger tips: its edge dips
    toward the wrist (a scalloped edge)."""
    return f0.lerp(f1, 0.5).lerp(wrist, 0.18)


class Dragon(studies.Spec):
    name = "dragon"
    colors = {
        "red": common.rgb(0xD23A2A),
        "red_light": common.rgb(0xE04A34),
        "red_shade": common.rgb(0xB82E24),
        "belly": common.rgb(0xF6A623),
        "belly_light": common.rgb(0xFBC040),
        "belly_shade": common.rgb(0xEB8F1C),
        "membrane": common.rgb(0xF08A2A),
        "membrane_dark": common.rgb(0xE0602A),
        "horn": common.rgb(0xF2C230),
        "eye": common.rgb(0xFFE24A),
        "nostril": common.rgb(0x3A1410),
    }
    ellipsoids = [
        ((0.0, -0.9, 1.8), (0.68, 0.95, 0.68)),   # Chest.
        ((0.0, 0.35, 1.65), (0.62, 1.0, 0.62)),   # Belly and hips.
        THIGH, ((-THIGH[0][0], THIGH[0][1], THIGH[0][2]), THIGH[1]),
        HEAD,
    ]
    budget = 1400
    max_tris = 3000
    tone_material = "red"
    rig = DragonRig(
        body=((0, 1.2, 1.7), (0, -0.3, 1.75)),
        chest=((0, -0.3, 1.75), NECK[0]),
        neck=(NECK[0], NECK[1]),
        head=(NECK_MID, (0, -3.1, 3.3)),
        ears=((0.2, -2.3, HEAD_Z + 0.2), (0.26, -2.0, HEAD_Z + 0.5)),  # No ears: nothing follows these.
        legs={
            # Front: shoulder, elbow (it points back), wrist, toes.
            "F": (FRONT_LEG[0][0], FRONT_LEG[0][1], (X_LEG * 1.05, -1.05, 0.26), (X_LEG * 1.05, -1.5, 0.0)),
            "H": ((X_LEG, 0.6, 1.3), HIND_LEG[0][1], (X_LEG * 1.05, 0.9, 0.26), (X_LEG * 1.05, 0.4, 0.0)),
        },
        leg_exit=(1.05, 1.2),
        leg_reach=0.5,
        walk=rigs.Gait(speed=1.4, frames=24, duty=0.62, lift=0.2, crouch=0.06, bob=0.015,
                       phases=rigs.WALK_PHASES, nod=2.0),
        run=rigs.Gait(speed=3.6, frames=16, duty=0.4, lift=0.35, crouch=0.08, bob=0.04,
                      phases=rigs.TROT_PHASES, nod=3.0),
        lie_height=0.7,
        blend=0.15,
    )

    def __init__(self):
        self.capsules = (legs() + [SNOUT, JAW]
                         + [(a, b, ra, rb) for a, b, ra, rb in zip(NECK, NECK[1:], NECK_R, NECK_R[1:])]
                         + [(a, b, ra, rb) for a, b, ra, rb in zip(TAIL, TAIL[1:], TAIL_R, TAIL_R[1:])])
        self.legs = legs()

    def paint(self, c, n):
        if near_capsule(c, self.legs, 0.03):
            return "red"
        if n.z < -0.3 and abs(c.x) < 0.5:
            return "belly"  # Underside of the body, the tail and the jaw.
        if c.y < -1.25 and n.y < -0.35 and abs(c.x) < 0.25 and 1.7 < c.z < HEAD_Z - 0.25:
            return "belly"  # Front of the neck.
        return "red"

    def details(self, mb):
        tone_faces(mb, "belly", 0.3)
        for s in (-1, 1):
            self.wing(mb, s)
            mb.sphere(mirror(EYE, s), 0.05, "eye", segments=6, rings=4)
            mb.sphere(mirror((0.08, -3.22, HEAD_Z - 0.12), s), 0.03, "nostril", segments=6, rings=3)
            # Horns: two swept-back golden cones, bent once, and a small one on the cheek.
            base, bend, tip = (mirror((0.17, -2.3, HEAD_Z + 0.2), s), mirror((0.26, -2.0, HEAD_Z + 0.53), s),
                               mirror((0.3, -1.6, HEAD_Z + 0.68), s))
            mb.cylinder(base, bend, 0.1, 0.06, "horn", segments=6)
            mb.cylinder(bend, tip, 0.06, 0.004, "horn", segments=6)
            mb.cylinder(mirror((0.26, -2.35, HEAD_Z - 0.1), s), mirror((0.45, -2.05, HEAD_Z - 0.02), s),
                        0.06, 0.004, "horn", segments=5)
            # Claws: three golden cones on each foot.
            for leg in (FRONT_LEG, HIND_LEG):
                b = Vector(leg[2][1])
                for dx in (-0.1, 0.0, 0.1):
                    root = mirror(b, s) + Vector((dx, 0.02, -0.04))
                    mb.cylinder(root, root + Vector((dx * 0.4, -0.16, -0.06)), 0.045, 0.004, "horn", segments=5)
        self.spikes(mb)
        # Spade-shaped fin at the tail tip.
        t = Vector(TAIL[-1])
        d = (t - Vector(TAIL[-2])).normalized()
        side = d.cross(Vector((0, 0, 1))).cross(d).normalized()  # Upright, seen from the side.
        studies.plate(mb, [t - d * 0.1, t + side * 0.3 + d * 0.12, t + d * 0.6, t - side * 0.3 + d * 0.12],
                      0.06, "red")

    def wing(self, mb, s):
        sh, el, wr = mirror(SHOULDER, s), mirror(ELBOW, s), mirror(WRIST, s)
        tips = [mirror(f, s) for f in FINGERS]
        back = mirror(BACK, s)
        # Arm and finger bones.
        mb.cylinder(sh, el, 0.16, 0.12, "red", segments=6)
        mb.sphere(el, 0.12, "red", segments=6, rings=4)
        mb.cylinder(el, wr, 0.12, 0.08, "red", segments=6)
        mb.sphere(wr, 0.09, "red", segments=6, rings=4)
        mb.cylinder(wr, wr + (wr - el).normalized() * 0.25, 0.06, 0.004, "horn", segments=5)  # Thumb claw.
        for f in tips:
            mb.cylinder(wr, f, 0.06, 0.02, "red", segments=5)
        # Membrane: from the wrist, one pair of triangles per gap between
        # fingers, dipping toward the wrist between the tips (scalloped edge).
        ends = tips + [back]
        for i, (f0, f1) in enumerate(zip(ends, ends[1:])):
            dip = membrane_dip(f0, f1, wr)
            mat = "membrane" if i % 2 == 0 else "membrane_dark"
            studies.plate(mb, [wr, f0, dip], 0.03, mat)
            studies.plate(mb, [wr, dip, f1], 0.03, mat)
        # Between the arm and the body.
        studies.plate(mb, [el, wr, back], 0.03, "membrane_dark")
        studies.plate(mb, [sh, el, back], 0.03, "membrane_dark")

    def spikes(self, mb):
        """Golden triangular spikes along the back, from the head to the tail."""
        pts = [Vector(p) for p in SPINE]
        for i, (a, b) in enumerate(zip(pts, pts[1:])):
            seg = (b - a).length
            count = max(1, int(seg / 0.32))
            for k in range(count):
                c = a.lerp(b, (k + 0.5) / count)
                tangent = (b - a).normalized()
                up = Vector((0, 0, 1)) - tangent * tangent.z
                up.normalize()
                top = surface(self, c, up) - up * 0.04
                size = 0.2 * (1.0 - 0.55 * max(0.0, c.y - 1.2) / 2.4)
                studies.flap(mb, top - tangent * size * 0.55, top + tangent * size * 0.55,
                             top + up * size * 1.1 + tangent * size * 0.5, 0.05, "horn")


SPECS = [Dragon()]
