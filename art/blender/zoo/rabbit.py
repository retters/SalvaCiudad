"""Rabbit: white, sitting upright on its haunches, with long upright ears
(pink on the inside), a pink nose and a round tail."""

import math

from mathutils import Matrix, Quaternion, Vector

import common
import rigs
import studies

HEAD = ((0.0, -0.1, 0.27), (0.068, 0.078, 0.064))
MUZZLE = ((0.0, -0.162, 0.25), (0.042, 0.036, 0.036))
EYE = (0.047, -0.143, 0.285)
EARS_X = 0.03


def ear(s, lean):
    """Outline of an ear, base on the head top, tip up and a bit back."""
    x0 = s * EARS_X
    pivot = Vector((x0, -0.08, 0.3))
    turn = Matrix.Rotation(s * 0.35, 3, "Z")  # Opened outward a little.
    return [pivot + turn @ (Vector(p) - pivot) for p in (
        (x0 - s * 0.018, -0.1, 0.315), (x0 + s * 0.028, -0.095, 0.315), (x0 + s * (0.035 + lean), -0.06, 0.4),
        (x0 + s * (0.022 + lean * 1.5), -0.04, 0.47), (x0 + s * lean * 1.5, -0.035, 0.48),
        (x0 - s * (0.012 - lean), -0.055, 0.4))]


class Hop:
    """A hopping gait: both hind feet push together, then both front paws
    land together. Times are shares of the cycle."""

    def __init__(self, speed, frames, hind_duty, front_at, front_duty, pitch, rock, rise, bounce, lift, ears):
        self.speed = speed            # m/s the planted feet move back at.
        self.frames = frames          # Frames per cycle at 30 fps.
        self.hind_duty = hind_duty    # The hind feet are planted from 0 to this.
        self.front_at = front_at      # When the front paws land.
        self.front_duty = front_duty  # How long they stay planted.
        self.pitch = pitch            # How far the body leans forward (degrees).
        self.rock = rock              # How much that changes during a hop.
        self.rise = rise              # How much higher the body is than sitting (m).
        self.bounce = bounce          # Up and down, once per hop (m).
        self.lift = lift              # How high the feet rise while swinging (m).
        self.ears = ears              # How far back the ears lie (degrees).

    def stride(self, duty):
        return self.speed * duty * self.frames / rigs.FPS


class RabbitRig(rigs.Quadruped):
    """A rabbit sitting on its haunches: the hind feet lie flat on the
    ground under the thighs. It moves in hops, so the gaits and the weights
    of the template (made for legs hanging below a body) are replaced."""

    # How thick the body is around each bone: weights go by the distance to
    # the surface around the bone, so the thin legs do not lose against the trunk.
    RADIUS = {"body": 0.1, "chest": 0.075, "neck": 0.05, "head": 0.062, "leg_upper.H": 0.045,
              "leg_lower.H": 0.028, "leg_upper.F": 0.02, "leg_lower.F": 0.019}
    SOFT = 0.018  # Width of the weight transition between bones (m).

    def __init__(self, hop, bound, **points):
        super().__init__(walk=hop, run=bound, **points)

    def cuts(self):
        """Rings around the front legs at the elbow and under the chest."""
        out = []
        for leg in ("FL", "FR"):
            hip, knee, ankle, toe = self.leg_points[leg]

            def near(c, n, knee=knee):
                return math.hypot(c.x - knee.x, c.y - knee.y) < 0.04 and c.z < 0.15
            out.append((knee, (0, 0, 1), near))
            out.append((Vector((knee.x, knee.y, 0.13)), (0, 0, 1), near))
        return out

    def surface_weights(self, p):
        # The feet are rigid: the long hind feet and the front paws.
        for leg in rigs.LEGS:
            hip, knee, ankle, toe = self.leg_points[leg]
            if leg[0] == "H":
                on_foot = (rigs.segment_distance(p, ankle, toe) < 0.042 and p.z < 0.05
                           and abs(p.x) > 0.045 and p.x * ankle.x > 0)
            else:
                on_foot = p.z < ankle.z + 0.006 and p.y < -0.08 and p.x * ankle.x > 0
            if on_foot:
                return [(f"foot.{leg}", 1.0)]
        cands = []
        for bone in self.bones:
            radius = self.RADIUS.get(bone.name, self.RADIUS.get(bone.name[:-1]))
            if radius is not None:
                cands.append((rigs.segment_distance(p, bone.head, bone.tail) - radius, bone.name))
        d0 = min(d for d, _ in cands)
        return [(n, max(0.0, 1.0 - (d - d0) / self.SOFT) ** 2) for d, n in cands]

    def piece_bone(self, center, piece):
        if center.z > 0.33:
            return "ear.L" if center.x > 0 else "ear.R"
        return "head"  # Eyes and nose.

    # -------------------------------------------------------------- poses

    def legs(self, pose, targets=None, tilt=None):
        """Brings each ankle to its target (where it rests, unless given),
        knees forward and elbows back, with the feet level unless tilted."""
        for leg in rigs.LEGS:
            ankle = self.leg_points[leg][2]
            target = (targets or {}).get(leg, ankle)
            pole = (0, -1, 0.4) if leg[0] == "H" else (0, 1, 0.2)
            pose.limb(f"leg_upper.{leg}", f"leg_lower.{leg}", target, pole)
            pose.set_world(f"foot.{leg}", Quaternion(rigs.X, math.radians((tilt or {}).get(leg, 0.0))))

    def hop_pose(self, g, t):
        pose = rigs.Pose(self)
        pitch = g.pitch + g.rock * math.cos(2 * math.pi * (t - 0.6))
        pose.offset = Vector((0, 0, g.rise + g.bounce * math.sin(2 * math.pi * (t - 0.12))))
        pose.turn("body", rigs.X, pitch)
        pose.turn("neck", rigs.X, -pitch * 0.5)
        pose.turn("head", rigs.X, -pitch * 0.45)
        for side, phase in (("L", 0.0), ("R", 0.5)):
            pose.turn(f"ear.{side}", rigs.X, -g.ears - 6.0 * math.sin(2 * math.pi * (t - 0.2) + phase))
        targets, tilt = {}, {}
        for leg in rigs.LEGS:
            ankle = self.leg_points[leg][2]
            toe = self.leg_points[leg][3]
            if leg[0] == "H":
                psi, duty, lift = t, g.hind_duty, g.lift
            else:
                psi, duty, lift = (t - g.front_at) % 1.0, g.front_duty, g.lift * 0.7
            stride = g.stride(duty)
            if psi < duty:
                y, z = ankle.y - stride / 2 + stride * psi / duty, ankle.z
            else:
                # Swings forward leaving and reaching the ground at the
                # speed of the ground (a cubic), so it does not slide as it lands.
                u = (psi - duty) / (1 - duty)
                m = stride * (1 - duty) / duty
                y = (ankle.y + stride / 2 * (1 - 2 * u * u * (3 - 2 * u))
                     + m * (u * (1 - u) ** 2 - u * u * (1 - u)))
                z = ankle.z + lift * math.sin(math.pi * u)
                # The toes trail while in the air, never lower than the heel was.
                droop = math.degrees(math.asin(min(1.0, 0.6 * lift / (toe - ankle).length)))
                tilt[leg] = droop * math.sin(math.pi * u) ** 2
            targets[leg] = Vector((ankle.x, y, z))
        self.legs(pose, targets, tilt)
        return pose.q, pose.offset, {}

    def idle_pose(self, t):
        # Sitting: breathing, a twitching nose and a flick of each ear.
        pose = rigs.Pose(self)
        breath = math.sin(2 * math.pi * 3 * t)
        sniff = (math.sin(2 * math.pi * 18 * t) * rigs.smooth((t - 0.1) / 0.05)
                 * (1 - rigs.smooth((t - 0.45) / 0.05)))
        look = math.sin(2 * math.pi * t)
        pose.turn("chest", rigs.X, 1.0 * breath)
        pose.turn("neck", rigs.Z, 8.0 * look)
        pose.turn("head", rigs.Z, 10.0 * look)
        pose.turn("head", rigs.X, 2.5 * sniff - 1.5 * breath)
        for side, at, sign in (("L", 0.55, 1.0), ("R", 0.75, -1.0)):
            flick = math.sin(math.pi * max(0.0, min(1.0, (t - at) / 0.1)))
            pose.turn(f"ear.{side}", rigs.Y, sign * 14.0 * flick)
            pose.turn(f"ear.{side}", rigs.X, -8.0 * flick + 2.0 * breath)
        return pose.q, pose.offset, {}

    def eat_pose(self, t):
        # Leans forward with the head low and nibbles; starts and ends sitting.
        down = rigs.smooth(t / 0.2) * (1 - rigs.smooth((t - 0.8) / 0.2))
        nibble = (math.sin(2 * math.pi * 14 * t) * rigs.smooth((t - 0.2) / 0.05)
                  * (1 - rigs.smooth((t - 0.75) / 0.05)))
        pose = rigs.Pose(self, (0, 0, 0.022 * down))
        pose.turn("body", rigs.X, 16.0 * down)
        pose.turn("neck", rigs.X, 22.0 * down)
        pose.turn("head", rigs.X, 26.0 * down + 4.0 * nibble)
        for side in ("L", "R"):
            pose.turn(f"ear.{side}", rigs.X, -30.0 * down + 3.0 * nibble)
        self.legs(pose)
        return pose.q, pose.offset, {}

    def die_pose(self, t):
        # A last small jump, then it falls on its right side and lies still.
        jump = math.sin(math.pi * min(1.0, t / 0.3))
        roll = rigs.smooth((t - 0.2) / 0.45)
        pivot = self.by_name["body"].head
        pose = rigs.Pose(self, (0, 0, 0.04 * jump * (1 - roll) + (self.lie_height - pivot.z) * roll))
        pose.turn("body", rigs.X, 25.0 * roll)
        pose.turn("body", rigs.Y, -88.0 * roll)
        pose.turn("neck", rigs.X, -15.0 * roll)
        for side in ("L", "R"):
            pose.turn(f"ear.{side}", rigs.X, -35.0 * roll)
            pose.turn(f"leg_upper.H{side}", rigs.X, -25.0 * roll)
            pose.turn(f"leg_lower.H{side}", rigs.X, -20.0 * roll)
            pose.turn(f"leg_upper.F{side}", rigs.X, 20.0 * roll)
        return pose.q, pose.offset, {}

    def clips(self):
        return [
            ("idle", self.idle_frames, True, self.idle_pose, None),
            ("walk", self.walk.frames, True, lambda t: self.hop_pose(self.walk, t), self.walk.speed),
            ("run", self.run.frames, True, lambda t: self.hop_pose(self.run, t), self.run.speed),
            ("eat", self.eat_frames, True, self.eat_pose, None),
            ("die", self.die_frames, False, self.die_pose, None),
        ]


class Rabbit(studies.Spec):
    name = "rabbit"
    colors = {
        "fur": common.rgb(0xF2F0EE),
        "fur_light": common.rgb(0xFBFAF9),
        "fur_shade": common.rgb(0xDEDBD8),
        "pink": common.rgb(0xF0A3B4),
        "eye": common.rgb(0x151012),
    }
    ellipsoids = [
        ((0.0, 0.03, 0.105), (0.1, 0.12, 0.1)),        # Haunches.
        ((0.0, -0.04, 0.17), (0.078, 0.08, 0.1)),      # Chest.
        ((0.06, 0.04, 0.085), (0.045, 0.1, 0.075)),    # Thighs.
        ((-0.06, 0.04, 0.085), (0.045, 0.1, 0.075)),
        HEAD, MUZZLE,
        ((0.0, -0.13, 0.225), (0.03, 0.03, 0.022)),    # Chin.
        ((0.0, 0.145, 0.08), (0.035, 0.03, 0.035)),    # Tail.
    ]
    capsules = [((0.0, -0.05, 0.2), (0.0, -0.09, 0.26), 0.055, 0.05)] + [  # Neck.
        cap for s in (-1, 1) for cap in (
            ((s * 0.075, 0.06, 0.028), (s * 0.07, -0.07, 0.02), 0.03, 0.022),      # Hind feet.
            ((s * 0.035, -0.08, 0.14), (s * 0.035, -0.105, 0.02), 0.02, 0.018),   # Front legs.
            ((s * 0.035, -0.105, 0.015), (s * 0.035, -0.13, 0.015), 0.018, 0.016),  # Front paws.
        )]
    budget = 420
    max_tris = 800
    tone_material = "fur"
    tones = 0.3
    rig = RabbitRig(
        hop=Hop(speed=0.4, frames=18, hind_duty=0.4, front_at=0.5, front_duty=0.35, pitch=20.0, rock=8.0,
                rise=0.03, bounce=0.012, lift=0.035, ears=10.0),
        bound=Hop(speed=1.4, frames=10, hind_duty=0.35, front_at=0.5, front_duty=0.3, pitch=28.0, rock=8.0,
                  rise=0.05, bounce=0.02, lift=0.035, ears=35.0),
        body=((0, 0.1, 0.1), (0, -0.02, 0.15)),
        chest=((0, -0.02, 0.15), (0, -0.06, 0.21)),
        neck=((0, -0.06, 0.21), (0, -0.09, 0.262)),
        head=((0, -0.09, 0.262), (0, -0.2, 0.255)),
        ears=((0.03, -0.085, 0.31), (0.06, -0.04, 0.47)),
        tail=[(0, 0.12, 0.08), (0, 0.14, 0.08), (0, 0.16, 0.085), (0, 0.18, 0.09)],
        legs={
            # Front: shoulder, elbow, wrist, toes. Hind: hip, knee (at the
            # front of the thigh), heel and toes of the foot on the ground.
            "F": ((0.035, -0.075, 0.15), (0.035, -0.092, 0.085), (0.035, -0.105, 0.022), (0.035, -0.14, 0.005)),
            "H": ((0.062, 0.07, 0.1), (0.066, -0.03, 0.085), (0.075, 0.065, 0.03), (0.07, -0.09, 0.012)),
        },
        leg_exit=(0.1, 0.14),
        lie_height=0.105,
    )

    def paint(self, c, n):
        return "fur"

    def details(self, mb):
        for s in (-1, 1):
            mb.sphere((s * EYE[0], EYE[1], EYE[2]), 0.012, "eye", segments=6, rings=4)
            outer = ear(s, 0.012)
            studies.plate(mb, outer, 0.012, "fur")
            # The pink inside, a smaller copy just in front of the ear.
            mid = sum(outer, Vector()) / len(outer)
            inner = [mid + (p - mid) * 0.7 + Vector((0, -0.007, 0)) for p in outer]
            studies.plate(mb, inner, 0.006, "pink")
        mb.sphere((0.0, -0.197, 0.262), 0.012, "pink", segments=6, rings=3, scale=(1.2, 0.6, 0.8))


SPECS = [Rabbit()]
