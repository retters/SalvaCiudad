"""Skeletons and procedural animations for the swimmers (phase 46): the
templates Fish (shark), SeaTurtle and Tentacled (octopus). See rigs.py for
how a template binds a model and keys its clips.

The models rest on Z = 0 and the game lifts them into the water. Clips are
animated in place; the swim clips save their speed ("swim_speed"), and may
go below Z = 0 (a flipper's down stroke), as the die clips do. Every other
clip stays above the ground, so the animal can also be shown on the bottom.

Only the root bone of a skeleton can move (rigs.pose_key); what must slide
(a turtle's head pulled into its shell) hangs from two hidden bones that
fold like an elbow (SeaTurtle.head_to).
"""

import math

from mathutils import Quaternion, Vector

from rigs import FPS, X, Y, Z, Bone, Pose, Rig, segment_distance, smooth

TAU = 2 * math.pi


def chain_weights(p, joints, names, soft=0.5, firm=()):
    """Weights of a point along a chain of bones (`joints` has one point
    more than `names`): its nearest bone, blending with the next one over
    `soft` of the bone's length on each side of a joint, so the chain bends
    as a curve and not as a folding ruler. A bone named in `firm` is rigid
    from joint to joint (a foot): its neighbours do all the blending."""
    best = None
    for i, (a, b) in enumerate(zip(joints, joints[1:])):
        ab = b - a
        u = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.dot(ab), 1e-12)))
        d = (p - (a + ab * u)).length
        if best is None or d < best[0]:
            best = (d, i, u)
    _, i, u = best
    if names[i] in firm:
        return [(names[i], 1.0)]
    for j, near in ((i - 1, u), (i + 1, 1.0 - u)):
        if 0 <= j < len(names) and near < soft:
            w = (1.0 - near / soft) * (1.0 if names[j] in firm else 0.5)
            return [(names[i], 1.0 - w), (names[j], w)]
    return [(names[i], 1.0)]


def pulse(t, start, end, ramp):
    """0 outside (start, end), 1 inside, with smooth ramps."""
    return smooth((t - start) / ramp) * (1.0 - smooth((t - end + ramp) / ramp))


# ---------------------------------------------------------------- fish

class Fish(Rig):
    """A body that bends sideways along its spine, for a shark or a fish.

    spine: points from the snout to the end of the tail stalk. The first
        bone is "head"; the second, "body", is the root (the gills: the
        head stays steady while the rest swings); then "spine.1"... to the
        tail. The surface blends along the whole chain.
    fins: {name: (start, end, parent)}: one rigid bone per fin. The
        template moves "fin.L", "fin.R" (pectoral), "dorsal" and the tail
        lobes "lobe.U", "lobe.L" if they exist; other fins follow the
        nearest bone.
    jaw: (hinge, tip, upper normal, lower normal) or None: the lower jaw
        turns about X through the hinge; the two planes through the hinge
        are the lips of the open mouth (normals pointing away from the
        mouth). The surface between them (the inside of the mouth) stretches
        between the jaw and the head.
    swim, fast: (frames, speed m/s, degrees of bend per bone at the tail).
    """

    def __init__(self, spine, fins, jaw=None, swim=(24, 1.6, 13.0), fast=(14, 3.6, 19.0), jaw_blend=0.12,
                 idle_frames=90, eat_frames=60, bite_frames=36, die_frames=75, bite_lift=0.16, die_rise=0.5):
        pts = [Vector(p) for p in spine]
        self.joints = pts
        self.swim, self.fast = swim, fast
        self.jaw = None
        self.jaw_blend = jaw_blend
        self.idle_frames, self.eat_frames, self.bite_frames, self.die_frames = (
            idle_frames, eat_frames, bite_frames, die_frames)
        self.bite_lift, self.die_rise = bite_lift, die_rise
        b = [Bone("body", pts[1], pts[2], surface=True),
             Bone("head", pts[1], pts[0], parent="body", surface=True)]
        self.back = ["body"]  # From the root to the tail.
        for i in range(2, len(pts) - 1):
            b.append(Bone(f"spine.{i - 1}", pts[i], pts[i + 1], parent=self.back[-1], surface=True))
            self.back.append(f"spine.{i - 1}")
        self.chain = ["head"] + self.back
        if jaw is not None:
            hinge, tip, upper_n, lower_n = (Vector(v) for v in jaw)
            self.jaw = (hinge, upper_n.normalized(), lower_n.normalized())
            b.append(Bone("jaw", hinge, tip, parent="head", surface=True))
        for name, (start, end, parent) in fins.items():
            b.append(Bone(name, start, end, parent=parent))
        self.set_bones(b)

    # ------------------------------------------------------------ binding

    def jaw_weight(self, p):
        if self.jaw is None:
            return 0.0
        hinge, upper_n, lower_n = self.jaw
        if p.y >= hinge.y:
            return 0.0
        above, below = (p - hinge).dot(upper_n), (p - hinge).dot(lower_n)
        if below >= 0.0:
            w = 1.0
        elif above >= 0.0:
            w = 0.0
        else:  # Inside the mouth: from the upper lip (0) to the lower one (1).
            w = above / (above + below)
        return w * smooth((hinge.y - p.y) / self.jaw_blend)

    def surface_weights(self, p):
        w = self.jaw_weight(p)
        return [("jaw", w)] + [(n, x * (1.0 - w)) for n, x in chain_weights(p, self.joints, self.chain)]

    def piece_bone(self, center, piece):
        if self.jaw is not None:
            hinge, upper_n, lower_n = self.jaw
            # A tooth of the lower lip: nearer the lower lip's plane.
            if (center.y < hinge.y and (center - hinge).dot(upper_n) < 0.02
                    and abs((center - hinge).dot(lower_n)) < abs((center - hinge).dot(upper_n))):
                return "jaw"
        bones = [b for b in self.bones if b.name != "jaw"]
        return min(bones, key=lambda b: segment_distance(center, b.head, b.tail)).name

    # -------------------------------------------------------------- poses

    def wave(self, rot, phase, amp, lag=2.4, steady=0.22):
        """A wave travelling down the body: each bone bends a little more
        and a little later than the one before. The root turns slightly the
        other way, as a swimming fish's head does."""
        n = len(self.back) - 1
        total = 0.0
        for k, name in enumerate(self.back[1:], 1):
            a = amp * (0.2 + 0.8 * (k / n) ** 1.5) * math.sin(phase - lag * k / n)
            rot[name] = [(Z, a)]
            total += a
        rot["body"] = [(Z, -steady * amp * math.sin(phase - lag * 0.45))]
        rot["head"] = [(Z, 0.5 * steady * amp * math.sin(phase - lag * 0.45))]
        for lobe in ("lobe.U", "lobe.L"):
            if lobe in self.by_name:  # The lobes trail behind the stalk.
                rot[lobe] = [(Z, amp * 0.9 * math.sin(phase - lag * 1.25))]
        return total

    def fins_pose(self, rot, lift, sweep=0.0):
        """Pectoral fins: `lift` degrees up from rest, `sweep` back."""
        for name, sx in (("fin.L", 1.0), ("fin.R", -1.0)):
            if name in self.by_name:
                rot[name] = [(Y, -lift * sx), (Z, sweep * sx)]

    def idle_pose(self, t):
        p = TAU * t
        rot = {}
        self.wave(rot, 2 * p, 3.5, lag=2.0)
        self.fins_pose(rot, 4.0 + 4.0 * math.sin(p))
        if "dorsal" in self.by_name:
            rot["dorsal"] = [(Y, 2.0 * math.sin(2 * p - 1.0))]
        return rot, Vector((0, 0, 0.02 * (1 - math.cos(p)))), {}

    def swim_pose(self, t, amp, lean):
        p = TAU * t
        rot = {}
        self.wave(rot, p, amp)
        self.fins_pose(rot, lean + 2.0 * math.sin(2 * p), sweep=lean)
        if "dorsal" in self.by_name:
            rot["dorsal"] = [(Y, 0.25 * amp * math.sin(p - 1.2))]
        # The body sways against the tail.
        return rot, Vector((0.004 * amp * math.sin(p - 0.6), 0, 0)), {}

    def eat_pose(self, t):
        """Three bites in place, starting and ending at rest."""
        on = pulse(t, 0.0, 1.0, 0.15)
        chew = 0.5 - 0.5 * math.cos(TAU * 3 * t)  # 0 open, 1 shut... three times.
        rot = {}
        self.wave(rot, TAU * 2 * t, 3.0 * on, lag=2.0)
        rot["head"] = rot["head"] + [(X, -6.0 * on + 5.0 * on * chew)]
        rot["jaw"] = [(X, on * (10.0 - 40.0 * chew * chew))]
        self.fins_pose(rot, 6.0 * on)
        return rot, Vector((0, 0, self.bite_lift * 0.7 * on)), {}

    def bite_pose(self, t):
        """Rears back with the mouth opening, lunges and snaps it shut."""
        back = pulse(t, 0.0, 0.42, 0.3)                      # Rearing back.
        lunge = smooth((t - 0.36) / 0.12) * (1 - smooth((t - 0.62) / 0.38))
        shut = smooth((t - 0.44) / 0.06) * (1 - smooth((t - 0.7) / 0.25))
        up = pulse(t, 0.0, 1.0, 0.3)
        rot = {}
        self.wave(rot, TAU * 2 * t, 5.0 * up + 8.0 * lunge)
        rot["head"] = rot["head"] + [(X, -12.0 * back * (1 - shut) + 4.0 * shut)]
        rot["jaw"] = [(X, 14.0 * back * (1 - shut) - 30.0 * shut)]
        self.fins_pose(rot, 8.0 * up, sweep=14.0 * lunge)
        return rot, Vector((0, 0.14 * back - 0.5 * lunge, self.bite_lift * up)), {}

    def die_pose(self, t):
        """Rolls belly up, goes limp and drifts up."""
        roll = smooth(t / 0.6)
        limp = smooth(t / 0.4)
        drift = math.sin(TAU * 0.75 * t) * (1 - 0.6 * t)
        rot = {}
        n = len(self.back) - 1
        for k, name in enumerate(self.back[1:], 1):
            rot[name] = [(Z, (5.0 * limp + 3.0 * drift) * (k / n)), (X, -3.0 * limp)]
        rot["body"] = [(Y, 180.0 * roll), (X, 8.0 * limp)]
        rot["head"] = [(Z, -3.0 * drift)]
        if self.jaw is not None:
            rot["jaw"] = [(X, 9.0 * limp)]
        self.fins_pose(rot, 25.0 * limp, sweep=10.0 * limp)
        for lobe in ("lobe.U", "lobe.L"):
            if lobe in self.by_name:
                rot[lobe] = [(Z, 14.0 * limp)]
        return rot, Vector((0, 0, self.die_rise * smooth(t / 0.9))), {}

    def clips(self):
        out = [
            ("idle", self.idle_frames, True, self.idle_pose, None),
            ("swim", self.swim[0], True, lambda t: self.swim_pose(t, self.swim[2], 4.0), self.swim[1]),
            ("swim_fast", self.fast[0], True, lambda t: self.swim_pose(t, self.fast[2], 12.0), self.fast[1]),
        ]
        if self.jaw is not None:
            out += [("eat", self.eat_frames, True, self.eat_pose, None),
                    ("bite", self.bite_frames, True, self.bite_pose, None)]
        return out + [("die", self.die_frames, False, self.die_pose, None)]


# -------------------------------------------------------------- turtle

FLIPPERS = (("FL", 1.0), ("FR", -1.0), ("HL", 1.0), ("HR", -1.0))


class SeaTurtle(Rig):
    """A rigid shell with a head, four flippers of two bones and a tail.

    body: (start, end) of the root bone; it turns about its start, the
        middle of the shell.
    head: (neck base, beak tip). The head hangs from two hidden bones
        ("neck.1", "neck.2") so it can slide into the shell.
    neck_fade: (y where the surface is all shell, y where it is all head).
    flippers: for the left front ("F") and left hind ("H") flipper, the
        points (shoulder, elbow, tip); the right ones are mirrored. Bones
        "flipper.FL.1", "flipper.FL.2"...; the outer half of a front
        flipper is "foot.FL": it is what the turtle crawls on, and
        rig_check measures the bones named foot.
    plant: the point of the left front flipper that rests on the ground;
        while crawling it moves straight back at the walk's speed, and
        while swimming, during the down stroke, at the swim's speed.
    feet: False names the outer halves "flipper.FL.2" and does not save the
        walk's speed (rig_check wants feet to check a walk's speed).
    tail: (start, end).
    hide_pull: how far back the head goes into the shell (m).
    """

    def __init__(self, body, head, neck_fade, flippers, plant, tail, walk_speed=0.3, swim_speed=0.9, hide_pull=0.33,
                 feet=True,
                 idle_frames=120, walk_frames=40, swim_frames=32, eat_frames=90, hide_frames=36,
                 die_frames=50, back_height=0.13):
        self.neck_fade = neck_fade
        self.walk_speed, self.swim_speed, self.hide_pull = walk_speed, swim_speed, hide_pull
        self.idle_frames, self.walk_frames, self.swim_frames = idle_frames, walk_frames, swim_frames
        self.eat_frames, self.hide_frames, self.die_frames = eat_frames, hide_frames, die_frames
        self.back_height = back_height  # How far the shell's middle rises to lie on its back.
        neck, beak = Vector(head[0]), Vector(head[1])
        self.neck = neck
        # The hidden elbow behind the neck: long enough to pull the head in
        # and to stretch it out a little.
        self.slide = neck + Vector((0, 0.4, 0))
        elbow = neck + Vector((0, 0.2, 0.13))
        b = [Bone("body", *body, surface=True),
             Bone("neck.1", self.slide, elbow, parent="body"),
             Bone("neck.2", elbow, neck, parent="neck.1"),
             Bone("head", neck, beak, parent="neck.2", surface=True),
             Bone("tail", *tail, parent="body")]
        self.flipper_points = {}
        self.flipper_bones = {}
        self.feet = feet
        self.plant = Vector(plant)
        for name, sx in FLIPPERS:
            pts = [Vector((p[0] * sx, p[1], p[2])) for p in flippers[name[0]]]
            self.flipper_points[name] = pts
            names = (f"flipper.{name}.1", f"foot.{name}" if feet and name[0] == "F" else f"flipper.{name}.2")
            self.flipper_bones[name] = names
            b.append(Bone(names[0], pts[0], pts[1], parent="body"))
            b.append(Bone(names[1], pts[1], pts[2], parent=names[0]))
        self.set_bones(b)

    # ------------------------------------------------------------ binding

    def surface_weights(self, p):
        y_body, y_head = self.neck_fade
        w = smooth((y_body - p.y) / (y_body - y_head))
        return [("body", 1.0 - w), ("head", w)]

    def nearest_flipper(self, center):
        return min(self.flipper_points, key=lambda n: min(
            segment_distance(center, a, b) for a, b in zip(self.flipper_points[n], self.flipper_points[n][1:])))

    def piece_bone(self, center, piece):
        bones = [b for b in self.bones if not b.name.startswith("neck.")]
        return min(bones, key=lambda b: segment_distance(center, b.head, b.tail)).name

    def piece_weights(self, center, piece):
        """A flipper made of one piece bends at its elbow; one made of a
        piece per bone keeps each piece rigid."""
        if not self.piece_bone(center, piece).startswith(("flipper.", "foot.")):
            return None
        name = self.nearest_flipper(center)
        pts = self.flipper_points[name]
        along = [(v.co - pts[0]).dot((pts[2] - pts[0]).normalized()) for v in piece]
        elbow = (pts[1] - pts[0]).dot((pts[2] - pts[0]).normalized())
        if max(along) < elbow + 0.02 or min(along) > elbow - 0.02:
            return None  # All on one side of the elbow.
        return lambda p: chain_weights(p, pts, self.flipper_bones[name], soft=0.35)

    # -------------------------------------------------------------- poses

    def head_to(self, pose, shift=(0, 0, 0), turns=()):
        """Slides the head by `shift` (in the shell's frame) with the hidden
        neck bones and turns it: `turns` is a list of (axis, degrees)."""
        body = pose.world("body")
        target = pose.head("neck.1") + body @ (self.neck - self.slide + Vector(shift))
        pose.limb("neck.1", "neck.2", target, body @ Z)
        q = Quaternion()
        for axis, deg in turns:
            q = Quaternion(Vector(axis), math.radians(deg)) @ q
        pose.set_world("head", body @ q)

    def flipper(self, pose, name, forward=0.0, up=0.0, bend=0.0, fold=0.0):
        """Swings a flipper `forward` (degrees, about the vertical), lifts
        it `up`, bends its outer half up by `bend` and swings that half
        forward by `fold`."""
        sx = 1.0 if name[1] == "L" else -1.0
        inner, outer = self.flipper_bones[name]
        pose.turn(inner, Z, -forward * sx)
        pose.turn(inner, Y, -up * sx)
        pose.turn(outer, Z, -fold * sx)
        pose.turn(outer, Y, -bend * sx)

    def row(self, pose, name, y, body_yaw, up=0.0, bend=0.0):
        """Turns a front flipper about the vertical until the point it
        rests on is `y` behind where it is at rest, whatever the shell has
        turned (`body_yaw`, degrees about Z); then lifts it as flipper()."""
        sx = 1.0 if name[1] == "L" else -1.0
        inner, outer = self.flipper_bones[name]
        shoulder = self.flipper_points[name][0]
        r0 = Vector((self.plant.x * sx - shoulder.x, self.plant.y - shoulder.y))
        s = max(-1.0, min(1.0, (self.plant.y + y - pose.head(inner).y) / r0.length))
        angle = (math.asin(s) if sx > 0 else math.pi - math.asin(s)) - math.atan2(r0.y, r0.x)
        pose.turn(inner, Z, math.degrees(angle) - body_yaw)
        pose.turn(inner, Y, -up * sx)
        pose.turn(outer, Y, -bend * sx)

    def idle_pose(self, t):
        p = TAU * t
        pose = Pose(self)
        look = math.sin(p) + 0.35 * math.sin(2 * p + 0.8)
        self.head_to(pose, (0, -0.012 * (1 + math.sin(2 * p)), 0.006 * (1 + math.sin(p + 1.0))),
                     [(X, -3.0 - 3.0 * math.sin(2 * p + 0.5)), (Z, 16.0 * look)])
        self.flipper(pose, "FL", forward=4.0 * math.sin(p + 0.4))
        self.flipper(pose, "FR", forward=4.0 * math.sin(p + 2.6))
        self.flipper(pose, "HL", forward=6.0 * math.sin(2 * p))
        self.flipper(pose, "HR", forward=6.0 * math.sin(2 * p + 1.9))
        pose.turn("tail", Z, 14.0 * math.sin(2 * p + 0.3))
        return pose.q, Vector(), {}

    def walk_pose(self, t):
        """Crawling: diagonal flippers row back together on the ground,
        then lift and swing forward; the shell turns a little with them.
        The front flippers' resting points move straight back at the
        walk's speed, so they do not slide."""
        p = TAU * t
        duty = 0.6
        stride = self.walk_speed * duty * self.walk_frames / FPS
        yaw = 3.0 * math.sin(p)
        pose = Pose(self)
        pose.turn("body", Z, yaw)
        for name, phase, reach, lift in (("FL", 0.0, 0.0, 13.0), ("HR", 0.0, 12.0, 9.0),
                                         ("FR", 0.5, 0.0, 13.0), ("HL", 0.5, 12.0, 9.0)):
            psi = (t + phase) % 1.0
            if psi < duty:
                back, up = 2 * psi / duty - 1, 0.0
            else:
                u = (psi - duty) / (1 - duty)
                back, up = 1 - 2 * smooth(u), lift * math.sin(math.pi * u)
            if name[0] == "F":
                self.row(pose, name, 0.5 * stride * back, yaw, up, 0.6 * up)
            else:
                self.flipper(pose, name, -reach * back, up, 0.6 * up)
        self.head_to(pose, (0, -0.015 * (1 + math.cos(2 * p)), 0), [(X, -2.0), (Z, -3.0 * math.sin(p))])
        pose.turn("tail", Z, 10.0 * math.sin(p + 1.0))
        return pose.q, Vector(), {}

    def swim_pose(self, t):
        """The front flippers beat like wings: down and back, pushing the
        water at the swim's speed, then up and forward with their tips
        trailing; the hind ones trail behind and steer."""
        p = TAU * t
        duty = 0.5
        travel = self.swim_speed * duty * self.swim_frames / FPS
        pose = Pose(self)
        pose.turn("body", X, 2.0 * math.sin(p + 2.2))
        for name in ("FL", "FR"):
            if t < duty:
                u = t / duty
                self.row(pose, name, travel * (u - 0.5), 0.0, up=-26.0 * math.sin(math.pi * u))
            else:
                u = (t - duty) / (1 - duty)
                self.row(pose, name, travel * (0.5 - smooth(u)), 0.0, up=30.0 * math.sin(math.pi * u),
                         bend=20.0 * math.sin(math.pi * u))
        for name, lag in (("HL", 0.0), ("HR", 0.5)):
            self.flipper(pose, name, forward=-22.0 + 5.0 * math.sin(p + lag), up=6.0 * math.sin(p + 3.0 + lag),
                         bend=6.0 * math.sin(p + 2.0))
        self.head_to(pose, (0, -0.03, 0.005), [(X, -4.0 - 3.0 * math.sin(p + 2.2))])
        pose.turn("tail", X, 6.0 * math.sin(p + 1.5))
        return pose.q, Vector((0, 0, 0.025 * math.sin(p + 2.6))), {}

    def eat_pose(self, t):
        """Stretches the neck down and pecks, starting and ending at rest."""
        down = pulse(t, 0.0, 1.0, 0.2)
        peck = math.sin(TAU * 5 * t) * pulse(t, 0.18, 0.82, 0.06)
        pose = Pose(self)
        self.head_to(pose, (0, -0.065 * down - 0.01 * peck, -0.012 * down), [(X, 11.0 * down + 5.0 * peck)])
        for name in ("FL", "FR"):
            self.flipper(pose, name, forward=-4.0 * down)
        pose.turn("tail", Z, 10.0 * down * math.sin(TAU * 3 * t))
        return pose.q, Vector(), {}

    def hide_pose(self, t):
        """Head, flippers and tail pulled in under the shell."""
        s = smooth(t / 0.85)
        late = smooth((t - 0.1) / 0.85)
        pose = Pose(self)
        self.head_to(pose, (0, self.hide_pull * s, -0.055 * s), [(X, 3.0 * s)])
        for name in ("FL", "FR"):
            self.flipper(pose, name, forward=-92.0 * late, fold=-28.0 * late)
        for name in ("HL", "HR"):
            self.flipper(pose, name, forward=130.0 * late)
        pose.turn("tail", Z, 80.0 * late)
        return pose.q, Vector(), {}

    def die_pose(self, t):
        """Tips over onto its back; head and flippers go limp."""
        roll = smooth((t - 0.1) / 0.6)
        limp = smooth(t / 0.5)
        settle = smooth((t - 0.6) / 0.4)
        pose = Pose(self)
        pose.turn("body", Y, 180.0 * roll - 6.0 * math.sin(math.pi * settle))
        self.head_to(pose, (0, -0.02 * limp, 0), [(X, -22.0 * limp * roll + 8.0 * limp * (1 - roll)), (Z, 12.0 * limp)])
        for name in ("FL", "FR"):
            self.flipper(pose, name, forward=8.0 * limp, up=24.0 * roll, bend=14.0 * roll)
        for name in ("HL", "HR"):
            self.flipper(pose, name, forward=-10.0 * limp, up=18.0 * roll)
        pose.turn("tail", X, -15.0 * roll)
        return pose.q, Vector((0, 0, self.back_height * math.sin(math.pi * 0.5 * roll))), {}

    def clips(self):
        return [
            ("idle", self.idle_frames, True, self.idle_pose, None),
            ("walk", self.walk_frames, True, self.walk_pose, self.walk_speed if self.feet else None),
            ("swim", self.swim_frames, True, self.swim_pose, self.swim_speed),
            ("eat", self.eat_frames, True, self.eat_pose, None),
            ("hide", self.hide_frames, False, self.hide_pose, None),
            ("die", self.die_frames, False, self.die_pose, None),
        ]


# ------------------------------------------------------------- octopus

class Tentacled(Rig):
    """A body with a mantle on top and tentacles that lie on the ground
    around it, each a chain of bones.

    body: (start, end) of the root bone, at the base of the tentacles.
    mantle: (start, end) of the bone of the big head above; mantle_fade:
        (z where the surface is all body, z where it is all mantle).
    core: (a, b, radius): the capsule that the body and mantle fill; the
        surface nearer to it than to a tentacle follows body and mantle.
    arms: for each tentacle, its joints from the body outward and the
        tentacle's radius at each (bones "arm.<n>.1"...). `flat` is how
        many of the first joints lie along the ground; the bones after
        them are the curl at the tip. The tentacle crawls on the last
        bone on the ground, "foot.<n>", which is rigid from joint to joint;
        rig_check measures the bones named foot.
    feet: False names that bone "arm.<n>.3" and does not save the walk's
        speed (rig_check wants feet to check a walk's speed).
    walk_pull: how far the feet are drawn in toward the body to crawl, so
        that a tentacle has slack to reach forward (m).
    """

    def __init__(self, body, mantle, mantle_fade, core, arms, flat=4, blend=0.07, walk_speed=0.12,
                 walk_pull=0.06, walk_lift=0.05, feet=True,
                 swim_speed=1.2, idle_frames=120, walk_frames=48, swim_frames=40, eat_frames=90,
                 die_frames=60, swim_tilt=60.0):
        self.mantle_fade = mantle_fade
        self.core = (Vector(core[0]), Vector(core[1]), core[2])
        self.blend = blend
        self.flat = flat
        self.walk_speed, self.swim_speed, self.swim_tilt = walk_speed, swim_speed, swim_tilt
        self.walk_pull, self.walk_lift, self.feet = walk_pull, walk_lift, feet
        self.firm = set()
        self.idle_frames, self.walk_frames, self.swim_frames = idle_frames, walk_frames, swim_frames
        self.eat_frames, self.die_frames = eat_frames, die_frames
        b = [Bone("body", *body, surface=True), Bone("mantle", *mantle, parent="body", surface=True)]
        self.arms = []  # (joints, radii, bone names, outward direction, side axis).
        for k, arm in enumerate(arms):
            joints = [Vector(p) for p, _ in arm]
            radii = [r for _, r in arm]
            names = [f"arm.{k + 1}.{i + 1}" for i in range(len(joints) - 1)]
            if feet:
                names[flat - 2] = f"foot.{k + 1}"
            self.firm.add(names[flat - 2])
            out = Vector((joints[0].x, joints[0].y, 0.0)).normalized()
            for i, name in enumerate(names):
                b.append(Bone(name, joints[i], joints[i + 1], parent=names[i - 1] if i else "body", surface=True))
            self.arms.append((joints, radii, names, out, Z.cross(out)))
        self.set_bones(b)

    # ------------------------------------------------------------ binding

    def surface_weights(self, p):
        a, b, radius = self.core
        groups = [(segment_distance(p, a, b) - radius, None)]
        for arm in self.arms:
            joints, radii = arm[0], arm[1]
            groups.append((min(segment_distance(p, q, r) - (rq + rr) * 0.5
                               for q, r, rq, rr in zip(joints, joints[1:], radii, radii[1:])), arm))
        d0 = min(d for d, _ in groups)
        out = []
        for d, arm in groups:
            w = max(0.0, 1.0 - (d - d0) / self.blend) ** 2
            if w <= 0.0:
                continue
            if arm is None:
                z0, z1 = self.mantle_fade
                m = smooth((p.z - z0) / (z1 - z0))
                out += [("body", w * (1.0 - m)), ("mantle", w * m)]
            else:
                out += [(n, w * x) for n, x in chain_weights(p, arm[0], arm[2], firm=self.firm)]
        return out

    def piece_bone(self, center, piece):
        return "body"  # The eyes.

    # -------------------------------------------------------------- poses

    def arm(self, pose, k, lift=0.0, swing=0.0, curl=0.0, bend=0.0):
        """Poses tentacle k: `lift` raises it whole from its base, `swing`
        turns it about the vertical (counter-clockwise from above), `bend`
        arches the part on the ground upward, and `curl` tightens (or, if
        negative, opens) the curl at its tip. Degrees; bend and curl are
        per bone."""
        joints, radii, names, out, side = self.arms[k]
        pose.turn(names[0], Z, swing)
        pose.turn(names[0], side, -lift)
        for name in names[1:self.flat - 1]:
            pose.turn(name, side, -bend)
        for name in names[self.flat - 1:]:
            pose.turn(name, side, -curl)

    def breathe(self, pose, phase, amount=1.0):
        pose.turn("mantle", X, amount * 3.5 * math.sin(phase))
        pose.turn("mantle", Y, amount * 2.5 * math.sin(phase * 0.5 + 0.7))

    def idle_pose(self, t):
        p = TAU * t
        pose = Pose(self)
        self.breathe(pose, 2 * p)
        for k in range(len(self.arms)):
            ph = p + k * 2.4
            self.arm(pose, k, swing=5.0 * math.sin(ph), curl=11.0 * (1 - math.cos(ph + 0.9)),
                     lift=1.5 * (1 - math.cos(ph + 0.9)))
        return pose.q, Vector(), {}

    def walk_pose(self, t):
        """Crawling toward -Y: each tentacle lifts its foot and reaches
        forward, then lays it down and pulls back, its neighbours half a
        cycle away. A foot on the ground moves straight back at the walk's
        speed, flat, while the tentacle arches behind it."""
        p = TAU * t
        duty = 0.6
        stride = self.walk_speed * duty * self.walk_frames / FPS
        n = len(self.arms)
        pose = Pose(self)
        pose.turn("mantle", X, 5.0 + 3.0 * math.sin(2 * p))
        pose.turn("mantle", Y, 3.0 * math.sin(p))
        for k, (joints, radii, names, out, side) in enumerate(self.arms):
            psi = (t + 0.5 * (k % 2) + 0.25 * (k // 2) / (n // 2)) % 1.0
            if psi < duty:
                back, lift = 2 * psi / duty - 1, 0.0
            else:
                u = (psi - duty) / (1 - duty)
                back, lift = 1 - 2 * smooth(u), math.sin(math.pi * u)
            foot = self.flat - 2
            target = (joints[foot] - out * self.walk_pull + Y * (0.5 * stride * back)
                      + Z * (self.walk_lift * lift))
            pose.limb(names[foot - 2], names[foot - 1], target, Z)
            pose.set_world(names[foot], Quaternion())
            for name in names[foot + 1:]:
                pose.turn(name, side, -9.0 * (1 - back * out.y))
        return pose.q, Vector(), {}

    def swim_pose(self, t):
        """Jetting, mantle first: the tentacles close together behind the
        body in a quick stroke, trail, and open again slowly."""
        shut = smooth(t / 0.22) * (1 - smooth((t - 0.5) / 0.5))
        surge = math.sin(TAU * (t - 0.08))
        pose = Pose(self)
        pose.turn("body", X, self.swim_tilt)
        pose.turn("mantle", X, 6.0 - 5.0 * shut)
        for k in range(len(self.arms)):
            self.arm(pose, k, lift=10.0 - 78.0 * shut, bend=-4.0 * shut, curl=4.0 - 26.0 * shut)
        tilt = math.radians(self.swim_tilt)
        ahead = Vector((0, -math.sin(tilt), math.cos(tilt)))
        return pose.q, ahead * (0.07 * surge), {}

    def eat_pose(self, t):
        """The two front tentacles carry food under the body, in turn."""
        on = pulse(t, 0.0, 1.0, 0.18)
        pose = Pose(self)
        pose.turn("mantle", X, 9.0 * on + 3.0 * on * math.sin(TAU * 4 * t))
        front = sorted(range(len(self.arms)), key=lambda k: self.arms[k][3].y)[:2]
        for k in range(len(self.arms)):
            if k in front:
                grab = on * (0.6 + 0.4 * math.sin(TAU * 3 * t + (0.0 if k == front[0] else math.pi)))
                self.arm(pose, k, lift=22.0 * grab, bend=10.0 * grab, curl=24.0 * grab,
                         swing=14.0 * grab * self.arms[k][3].x / abs(self.arms[k][3].x))
            else:
                self.arm(pose, k, curl=6.0 * on * (1 + math.sin(TAU * 2 * t + k)))
        return pose.q, Vector(), {}

    def die_pose(self, t):
        """Goes limp: the mantle flops back and the tentacles fall open,
        flat on the ground."""
        limp = smooth(t / 0.7)
        flop = smooth((t - 0.15) / 0.75)
        pose = Pose(self)
        pose.turn("mantle", X, -68.0 * flop)
        pose.turn("mantle", Y, 14.0 * flop)
        pose.turn("body", X, -8.0 * flop)
        for k, (joints, radii, names, out, side) in enumerate(self.arms):
            pose.turn(names[0], Z, 6.0 * limp * math.sin(k * 2.1))
            # The curl unrolls until every bone lies along the ground.
            for name in names[self.flat - 1:]:
                pose.aim(name, out)
                pose.q[name] = Quaternion().slerp(pose.q[name], limp * 0.92)
        return pose.q, Vector((0, 0, -0.03 * limp)), {}

    def clips(self):
        return [
            ("idle", self.idle_frames, True, self.idle_pose, None),
            ("walk", self.walk_frames, True, self.walk_pose, self.walk_speed if self.feet else None),
            ("swim", self.swim_frames, True, self.swim_pose, self.swim_speed),
            ("eat", self.eat_frames, True, self.eat_pose, None),
            ("die", self.die_frames, False, self.die_pose, None),
        ]
