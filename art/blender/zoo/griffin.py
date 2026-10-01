"""Griffin: an eagle's front (white head, yellow hooked beak, brown
feathered chest, yellow scaly legs with dark talons) on a lion's hind body
(tawny legs and a tail ending in a dark tuft), with big brown wings raised
as layered feather plates."""

import math
import random

from mathutils import Quaternion, Vector

import common
import rigs
import studies

X_FRONT, X_HIND = 0.24, 0.25
TAIL = [(0.0, 0.85, 1.28), (0.0, 1.15, 1.05), (0.03, 1.45, 0.88), (0.08, 1.72, 0.92), (0.12, 1.92, 1.08)]
TAIL_R = [0.075, 0.06, 0.05, 0.045, 0.04]
TUFT = ((0.13, 1.99, 1.16), (0.08, 0.1, 0.12))
HEAD_C = (0.0, -1.02, 2.12)
EYE = (0.135, -1.16, 2.19)
# Where the white of the head and neck begins: a slanted plane.
WHITE_P, WHITE_N = Vector((0.0, -0.8, 1.78)), Vector((0.0, -0.55, 1.0)).normalized()
BEAK_Y = -1.225     # In front of this the head is the yellow beak.
SCALES_Z = 0.52     # Below this the eagle legs are yellow.
LION_P, LION_N = Vector((0.0, 0.12, 0.0)), Vector((0.0, 1.0, 0.35)).normalized()
# The wing's leading edge, shoulder to tip (right side, x > 0).
WING_EDGE = [(0.26, -0.38, 1.7), (0.66, -0.3, 2.15), (1.02, -0.12, 2.58), (1.3, 0.18, 2.92)]


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


def polyline_at(points, t):
    """The point and the unit tangent at t (0..1, by length) along a polyline."""
    pts = [Vector(p) for p in points]
    lengths = [(b - a).length for a, b in zip(pts, pts[1:])]
    d = t * sum(lengths)
    for (a, b), seg in zip(zip(pts, pts[1:]), lengths):
        if d <= seg or b is pts[-1]:
            return a.lerp(b, min(1.0, d / seg)), (b - a).normalized()
        d -= seg


def feather(mb, base, edge, direction, length, width, lift, mat):
    """A long feather plate from `base` along `direction`, `width` across
    (along `edge`), moved `lift` along the wing's normal."""
    across = (edge - direction * edge.dot(direction)).normalized()
    n = across.cross(direction).normalized() * lift
    pts = [base - across * width * 0.5, base + across * width * 0.5,
           base + direction * length * 0.82 + across * width * 0.42, base + direction * length,
           base + direction * length * 0.82 - across * width * 0.42]
    studies.plate(mb, [p + n for p in pts], 0.02, mat)


def wing(mb, s):
    """A raised wing on side s: an arm along the leading edge, a covert
    panel and a fan of long flight feathers pointing back."""
    edge = [Vector((s * x, y, z)) for x, y, z in WING_EDGE]
    for i, (a, b) in enumerate(zip(edge, edge[1:])):
        mb.cylinder(a, b, 0.085 - i * 0.02, 0.065 - i * 0.02, "wing", segments=6)
        if i:
            mb.sphere(a, 0.085 - i * 0.02, "wing", segments=6, rings=4)
    count = 11
    for i in range(count):
        t = i / (count - 1)
        base, tangent = polyline_at(edge, 0.08 + t * 0.92)
        # Back and down near the body, fanning back and up at the tip.
        direction = Vector((s * (0.3 + 0.25 * t), 1.0, -0.75 + 0.95 * t)).normalized()
        length = 0.7 + 0.55 * t - 0.25 * t * t
        mat = "feather_dark" if i % 2 else "feather"
        feather(mb, base, tangent, direction, length, 0.36, s * 0.006 * i, mat)
        if i % 2 == 0 and i < count - 1:
            # Short covert feathers over the feathers' bases.
            feather(mb, base + tangent * 0.08, tangent, direction, length * 0.45, 0.34,
                    s * (0.006 * count + 0.015), "wing")


WING_BONES = ("wing_arm", "wing_fore", "wing_hand")
# The axis the wing closes about like a fan (left wing): across the plane
# of the leading edge and the feathers.
WING_FAN = Vector((-0.48, 0.3, 0.36)).normalized()
WING_ARM = (Vector(WING_EDGE[1]) - Vector(WING_EDGE[0])).normalized()


def mirrored(axis, degrees, s):
    """A turn of the left side (s = 1) as it is on the right side (s = -1)."""
    return (axis, degrees) if s > 0 else (Vector((-axis[0], axis[1], axis[2])), -degrees)


class GriffinRig(rigs.Quadruped):
    """A quadruped with a bending tail (welded surface) and two wings of
    three bones; adds the fly clip."""

    fly_frames = 20
    fly_speed = 7.0

    def __init__(self, **points):
        wings = []
        for side, s in (("L", 1.0), ("R", -1.0)):
            edge = [Vector((s * x, y, z)) for x, y, z in WING_EDGE]
            parent = "chest"
            for name, a, b in zip(WING_BONES, edge, edge[1:]):
                wings.append(rigs.Bone(f"{name}.{side}", a, b, parent=parent))
                parent = f"{name}.{side}"
        super().__init__(extra_bones=wings, **points)
        for bone in self.bones:
            if bone.name.startswith("tail."):
                bone.surface = True  # The tail is part of the welded surface.

    def piece_bone(self, center, piece):
        side = "L" if center.x > 0 else "R"
        if center.z > 1.2 and center.y > -0.6 and abs(center.x) > 0.15:
            # Wing pieces follow the wing bone their base is on: the bone
            # nearest to any of their vertices.
            bones = [self.by_name[f"{name}.{side}"] for name in WING_BONES]
            return min(bones, key=lambda b: min(rigs.segment_distance(v.co, b.head, b.tail) for v in piece)).name
        if center.z < 0.2:
            return f"foot.F{side}"  # Talons.
        return "head"               # Eyes, brows and the hook of the beak.

    # -------------------------------------------------------------- poses

    def leg_pose(self, leg, target, pitch, dz, pivot, lift_toe=0.0):
        """As the template's, but the front legs are an eagle's: the joint
        where the feathers end is the heel and bends backward, as a hind
        leg's hock does (the template bends a front leg's joint forward)."""
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
        """Turns of the wing bones. fold: 0 raised as at rest, 1 closed like
        a fan and swept back. drop: degrees the whole wing comes down from
        its raised rest. flat: degrees the wing turns about its leading edge
        (trailing edge up). flex: degrees the outer wing lags behind (bends
        down, or up if negative). sway: degrees of the small movement of a
        wing held still (the left one leads)."""
        for side, s in (("L", 1.0), ("R", -1.0)):
            lead = sway if s > 0 else sway * 0.7
            rot[f"wing_arm.{side}"] = [
                mirrored(WING_ARM, flat, s),
                mirrored(rigs.Y, drop + lead, s),
                mirrored(rigs.Z, 30.0 * fold, s),
                mirrored(WING_FAN, 12.0 * fold, s),
            ]
            rot[f"wing_fore.{side}"] = [mirrored(WING_FAN, 38.0 * fold, s), mirrored(rigs.Y, flex + lead * 0.5, s)]
            rot[f"wing_hand.{side}"] = [mirrored(WING_FAN, 45.0 * fold, s), mirrored(rigs.Y, flex * 1.3, s)]

    def pose_extra(self, clip, t, rot):
        p = 2 * math.pi * t
        if clip == "fly":
            return
        if clip == "die":
            # The wings close and fall over the back as it rolls on its side.
            roll = rigs.smooth((t - 0.3) / 0.45)
            self.wings(rot, fold=0.5 + 0.2 * roll, sway=6.0 * math.sin(6 * p) * (1 - roll))
            rot["wing_arm.L"].append((rigs.Y, -70.0 * roll))
            rot["wing_arm.R"].append((rigs.Y, 38.0 * roll))
        elif clip in ("walk", "run"):
            self.wings(rot, fold=0.5 if clip == "walk" else 0.4, sway=3.0 * math.sin(2 * p + 0.8),
                       flex=4.0 * math.sin(2 * p))
        else:
            self.wings(rot, fold=0.5, sway=2.5 * math.sin(p * (2 if clip == "eat" else 1)))
        if clip == "eat":
            # A tall animal: the neck reaches much further down than the
            # template's, and the beak tears at what it holds.
            down = rigs.smooth(t / 0.2) * (1 - rigs.smooth((t - 0.8) / 0.2))
            tear = (math.sin(2 * math.pi * 5 * t) * rigs.smooth((t - 0.2) / 0.05)
                    * (1 - rigs.smooth((t - 0.75) / 0.05)))
            rot["chest"] = [(rigs.X, 18.0 * down)]
            rot["neck"] = [(rigs.X, 55.0 * down + 5.0 * tear)]
            rot["head"] = [(rigs.X, 30.0 * down - 9.0 * tear)]

    def fly_pose(self, t):
        p = 2 * math.pi * t
        beat = math.sin(p)
        dz = 0.12 * math.sin(p - 2.0)  # The body rises after each downstroke.
        pivot = self.by_name["body"].head
        rot = {}
        # Legs tucked: the front ones folded back under the chest, the hind
        # ones trailing.
        for leg in rigs.LEGS:
            hip = self.leg_points[leg][0]
            back, down = (0.55, 0.75) if leg[0] == "F" else (0.7, 0.62)
            swing = 0.03 * math.sin(p + (0.0 if leg[0] == "F" else 1.0))
            target = Vector((hip.x, hip.y + back + swing, hip.z - down + dz))
            rot.update(self.leg_pose(leg, target, 0.0, dz, pivot, math.radians(35.0)))
        rot["chest"] = [(rigs.X, -2.0 * beat)]
        rot["neck"] = [(rigs.X, 14.0 + 3.0 * math.sin(p - 1.0))]
        rot["head"] = [(rigs.X, -8.0 - 3.0 * math.sin(p - 1.0))]
        # The tail streams behind with a wave running down it.
        tail = [b.name for b in self.bones if b.name.startswith("tail.")]
        for i, name in enumerate(tail):
            rot[name] = [(rigs.X, (38.0, -8.0, -22.0, -28.0, -20.0)[i] + 7.0 * math.sin(p - 0.9 * i))]
        self.wings(rot, drop=42.0 + 40.0 * beat, flat=28.0 + 10.0 * math.cos(p),
                   flex=22.0 * math.sin(p - 1.1))
        return rot, Vector((0, 0, dz)), {}

    def clips(self):
        return super().clips() + [("fly", self.fly_frames, True, self.fly_pose, self.fly_speed)]


class Griffin(studies.Spec):
    name = "griffin"
    colors = {
        "brown": common.rgb(0x8A5530),
        "brown_light": common.rgb(0x9C6538),
        "brown_shade": common.rgb(0x774628),
        "tawny": common.rgb(0xB9854A),
        "tawny_light": common.rgb(0xC8955A),
        "tawny_shade": common.rgb(0xA6743E),
        "white": common.rgb(0xF3F0E8),
        "yellow": common.rgb(0xF2B324),
        "wing": common.rgb(0x9A6236),
        "feather": common.rgb(0x7A4A28),
        "feather_dark": common.rgb(0x5E391F),
        "claw": common.rgb(0x2A2220),
        "eye": common.rgb(0x151012),
    }
    ellipsoids = [
        ((0.0, -0.42, 1.32), (0.36, 0.5, 0.42)),       # Chest.
        ((0.0, 0.35, 1.22), (0.32, 0.55, 0.36)),       # Hind body.
        ((X_HIND * 0.9, 0.55, 1.02), (0.14, 0.3, 0.34)),   # Thighs.
        ((-X_HIND * 0.9, 0.55, 1.02), (0.14, 0.3, 0.34)),
        (HEAD_C, (0.19, 0.24, 0.2)),                   # Head.
        ((0.0, -1.3, 2.07), (0.085, 0.14, 0.1)),       # Beak.
        TUFT,
    ]
    capsules = [((0.0, -0.7, 1.55), (0.0, -0.95, 1.98), 0.27, 0.19)] + [
        cap for s in (-1, 1) for cap in (
            ((s * X_FRONT, -0.55, 1.15), (s * X_FRONT, -0.66, 0.55), 0.14, 0.09),   # Eagle thigh.
            ((s * X_FRONT, -0.66, 0.55), (s * X_FRONT, -0.7, 0.08), 0.065, 0.06),   # Scaly leg.
            ((s * X_HIND, 0.55, 0.95), (s * X_HIND, 0.8, 0.45), 0.13, 0.085),       # Lion leg to the hock.
            ((s * X_HIND, 0.8, 0.45), (s * X_HIND, 0.7, 0.1), 0.08, 0.075),
            ((s * X_HIND, 0.72, 0.075), (s * X_HIND, 0.55, 0.075), 0.085, 0.075),   # Paw.
        )] + [(a, b, ra, rb) for a, b, ra, rb in zip(TAIL, TAIL[1:], TAIL_R, TAIL_R[1:])]
    cuts = [
        (WHITE_P, WHITE_N, lambda c, n: c.y < -0.5 and c.z > 1.4),
        ((0, BEAK_Y, 0), (0, 1, 0), lambda c, n: c.z > 1.85),
        ((0, 0, SCALES_Z), (0, 0, 1), lambda c, n: c.y < -0.3),
        (LION_P, LION_N, lambda c, n: True),
    ]
    budget = 1200
    max_tris = 3000
    tone_material = "brown"
    rig = GriffinRig(
        body=((0, 0.8, 1.25), (0, -0.1, 1.28)),
        chest=((0, -0.1, 1.28), (0, -0.65, 1.5)),
        neck=((0, -0.65, 1.5), (0, -0.95, 1.98)),
        head=((0, -0.95, 1.98), (0, -1.4, 2.06)),
        ears=((0.1, -0.95, 2.26), (0.12, -0.9, 2.32)),  # No ears: nothing follows these.
        tail=TAIL + [TUFT[0]],
        legs={
            # The hips are high inside the body, above the feet, so the
            # nearly straight legs can stride without the body sinking.
            # Front (eagle): the joint is where the feathers end.
            "F": ((X_FRONT, -0.66, 1.3), (X_FRONT, -0.66, 0.55), (X_FRONT, -0.7, 0.08), (X_FRONT, -0.94, 0.0)),
            "H": ((X_HIND, 0.62, 1.15), (X_HIND, 0.8, 0.45), (X_HIND, 0.7, 0.14), (X_HIND, 0.5, 0.0)),
        },
        leg_exit=(0.85, 1.05),
        leg_reach=0.45,
        walk=rigs.Gait(speed=1.1, frames=26, duty=0.62, lift=0.14, crouch=0.05, bob=0.012,
                       phases=rigs.WALK_PHASES, wag=8.0),
        run=rigs.Gait(speed=3.0, frames=16, duty=0.4, lift=0.25, crouch=0.07, bob=0.03,
                      phases=rigs.TROT_PHASES, nod=4.0, wag=10.0),
        lie_height=0.42,
        blend=0.12,
    )

    def paint(self, c, n):
        if c.y < -0.3 and c.z < SCALES_Z:
            return "yellow"
        if c.y < -0.5 and c.z > 1.4 and (c - WHITE_P).dot(WHITE_N) > 0:
            return "yellow" if c.y < BEAK_Y else "white"
        if c.y > 1.85:
            return "feather_dark"  # Tail tuft.
        if (c - LION_P).dot(LION_N) > 0:
            return "tawny"
        return "brown"

    def on_head(self, direction, lift):
        """The head's surface seen from its center along direction, lifted."""
        d = Vector(direction).normalized()
        p = Vector(HEAD_C)
        while studies.sdf(self, p) < 0.0:
            p += d * 0.005
        return p + d * lift

    def details(self, mb):
        tone_faces(mb, "tawny", 0.3)
        # Beak hook: a cone curving down in front of the beak.
        mb.cylinder((0, -1.38, 2.09), (0, -1.47, 2.02), 0.055, 0.035, "yellow", segments=6)
        mb.cylinder((0, -1.47, 2.02), (0, -1.46, 1.93), 0.035, 0.004, "yellow", segments=6)
        for s in (-1, 1):
            mb.sphere((s * EYE[0], EYE[1], EYE[2]), 0.03, "eye", segments=6, rings=4)
            # A heavy brow over the eye.
            brow = [self.on_head((s * x, y, z), 0.012) for x, y, z in
                    ((0.45, -0.25, 0.6), (0.6, -0.75, 0.42), (0.35, -0.75, 0.6))]
            studies.flap(mb, *brow, 0.03, "white")
            wing(mb, s)
            # Eagle talons: three toes forward, one back, dark claws.
            x = s * X_FRONT
            ankle = Vector((x, -0.7, 0.06))
            for dx, dy in ((-0.09, -0.2), (0.0, -0.24), (0.09, -0.2), (0.0, 0.16)):
                tip = ankle + Vector((dx, dy, -0.03))
                mb.cylinder(ankle, tip, 0.04, 0.03, "yellow", segments=5)
                d = (tip - ankle).normalized()
                # (The claw's point stays just above the ground.)
                mb.cylinder(tip, tip + d * 0.07 + Vector((0, 0, -0.016)), 0.028, 0.003, "claw", segments=5)


SPECS = [Griffin()]
