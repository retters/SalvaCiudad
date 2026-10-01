"""Skeleton and procedural animations for the birds of the zoo (phase 46):
rooster, eagle, penguin and flamingo share this template.

Bones: body (the root, from the hips to the base of the neck), neck.1 to
neck.N, head, tail (and tail.2 when the tail has two bones), wing.L/R (and
wing.2.L, wing.3.L for a wing that unfolds) and, on each side, leg_upper,
leg_lower and foot (".L" is the bird's left, +X). The joint between
leg_upper and leg_lower is the one that shows below the body and bends
backward. A spec adds its own bones (a comb, a wattle) with extra_bones and
makes them swing with `dangles`.

Clips, all in place:
- idle: breathing, quick looks around, a tail flick and a wing twitch;
- walk and run: the planted foot moves back at the clip's speed, which
  comes from what the legs can reach; the head bobs (it holds still over the
  ground, then darts forward) or the body waddles, as the Step says;
- eat: the body tips forward and the neck curls down until the beak's tip
  touches the ground (worked out, not hand-tuned), then it pecks;
- die: falls on its right side, plays once;
- fly or swim (when given): the body pitched, the wings beating, the legs
  tucked; its speed is saved like the walk's.

Weights: the welded surface follows body, neck, head (and the thighs, when
they are welded) by distance, blending around the joints. A spec says which
bone each detail piece follows with tag(); untagged pieces are bound by
distance like the surface.
"""

import math

from mathutils import Matrix, Quaternion, Vector

import rigs
from rigs import FPS, X, Y, Z, Bone, Pose, smooth

SIDES = (("L", 1.0), ("R", -1.0))


def tag(mb, verts, bone):
    """Says which bone a detail piece follows. `bone` is a bone name, or a
    function point -> [(bone name, weight)] for a piece that bends (a long
    feather). Use it in Spec.details() with what plate(), sphere() or
    cylinder() return."""
    tags = mb.__dict__.setdefault("bone_tags", {})
    for v in verts:
        tags[v] = bone
    return verts


def mirrored(p, sx):
    return Vector((p[0] * sx, p[1], p[2]))


class Step:
    """A walk or run cycle on two legs; the stride and the speed come from
    the legs (Bird.stride)."""

    def __init__(self, frames, duty, crouch, lift, bob=0.0, head_bob=0.0, waddle=0.0, sway=0.0, lean=0.0,
                 wings=0.0, tail=6.0, tail_up=0.0, phases=(0.0, 0.5), toe=25.0, hop=0.0, reach=0.9):
        self.frames = frames      # Frames per cycle at 30 fps.
        self.duty = duty          # Share of the cycle each foot is planted.
        self.crouch = crouch      # How much lower the hips go than at rest (m).
        self.lift = lift          # How high a foot rises while swinging (m).
        self.bob = bob            # Up and down of the body, twice per cycle (m).
        self.head_bob = head_bob  # Degrees the neck tilts back and forth to hold the head still.
        self.waddle = waddle      # Degrees the body rolls over the planted foot.
        self.sway = sway          # Sideways shift over the planted foot (m).
        self.lean = lean          # Degrees the body pitches forward.
        self.wings = wings        # Degrees the wings are held out.
        self.tail = tail          # Degrees the tail swings.
        self.tail_up = tail_up    # Degrees the tail is held up, off the ground.
        self.phases = phases      # Offset of the left and right leg in the cycle.
        self.toe = toe            # Degrees the toes point down while the foot swings.
        self.hop = hop            # Extra rise of the body while both feet are in the air (m).
        self.reach = reach        # Share of what the legs can reach that the stride uses.
        self.stride = 0.0         # Filled by the Bird.
        self.speed = 0.0


class Bird(rigs.Rig):
    """body: (hips, base of the neck) of the root bone.
    neck: points from the base of the neck to the head (2 to 5 points).
    head: (start, end) of the head bone.
    beak_tip: the point of the beak that touches the ground when eating.
    tail: points of the tail (2 or 3: one or two bones).
    legs: (hip, joint, ankle, toe) of the left leg (+X), mirrored for the
        right one; or {"L": points, "R": points} when they differ. `joint`
        is the visible joint; `ankle` is where the leg meets the foot.
    folded: the side whose leg is folded at rest ("R" for the flamingo), or
        None. It stays folded in idle and eat and steps in walk and run.
    wings: points of the left wing from the shoulder to the tip (2 to 4:
        up to 3 bones), mirrored; None for no wing bones.
    wing_sides: for each left wing bone, where its feathers hang from the
        bone at rest; that side trails behind when the wing opens.
    leg_exit: (z_full, z_zero) when the thighs are part of the welded
        surface: below z_full it follows the leg, above z_zero only the body.
    neck_reach: cut a ring at every neck joint, within this distance (m).
    dangles: {bone: (axis, degrees)}: loose parts that swing behind the
        movement (comb, wattle, long tail feathers).
    eat: dict(pitch, crouch, head, height, curl, frames, pecks, peck): the
        body pitches `pitch` degrees and lowers `crouch` m, the head ends
        pitched `head` degrees and the beak's tip `height` m above ground;
        `curl` fixes the degrees each neck bone bends instead of working
        them out (a penguin only dips its head).
    air: dict(name, frames, beats, pitch, lift, amp, mid, sweep, lag,
        tuck, foot, tail, head, speed, bob): the fly or swim clip, or None.
    """

    def __init__(self, body, neck, head, beak_tip, tail, legs, walk, run, wings=None, wing_sides=None,
                 folded=None, leg_exit=None, leg_reach=0.08, neck_reach=None, blend=0.05, dangles=None,
                 eat=None, air=None, idle_frames=120, die_frames=40, lie_height=0.1, die_droop=35.0,
                 look=30.0, wing_twitch=8.0, extra_bones=()):
        self.blend = blend
        self.leg_exit = leg_exit
        self.leg_reach = leg_reach
        self.neck_reach = neck_reach
        self.folded = folded
        self.dangles = dict(dangles or {})
        self.eat = dict(pitch=30.0, crouch=0.02, head=70.0, height=0.02, curl=None, frames=90, pecks=4,
                        peck=0.25)
        self.eat.update(eat or {})
        self.air = None
        if air is not None:
            self.air = dict(name="fly", frames=16, beats=1, pitch=0.0, lift=0.2, amp=40.0, mid=5.0, sweep=0.0,
                            lag=0.6, tuck=40.0, foot=0.0, tail=0.0, head=0.0, speed=3.0, bob=0.02)
            self.air.update(air)
        self.idle_frames = idle_frames
        self.die_frames = die_frames
        self.lie_height = lie_height
        self.die_droop = die_droop
        self.look = look
        self.wing_twitch = wing_twitch
        self.beak_tip = Vector(beak_tip)

        b = [Bone("body", *body, surface=True)]
        self.neck = []
        parent = "body"
        for i, (p, q) in enumerate(zip(neck, neck[1:])):
            name = f"neck.{i + 1}"
            b.append(Bone(name, p, q, parent=parent, surface=True))
            self.neck.append(name)
            parent = name
        b.append(Bone("head", *head, parent=parent, surface=True))
        self.tail = []
        parent = "body"
        for i, (p, q) in enumerate(zip(tail, tail[1:])):
            name = "tail" if i == 0 else f"tail.{i + 1}"
            b.append(Bone(name, p, q, parent=parent))
            self.tail.append(name)
            parent = name
        self.wings = {}       # side -> [bone names], shoulder first.
        self.wing_side = {}   # bone -> where its feathers hang at rest.
        for side, sx in SIDES:
            parent = "body"
            self.wings[side] = []
            pts = wings or []
            for i, (p, q) in enumerate(zip(pts, pts[1:])):
                name = f"wing.{side}" if i == 0 else f"wing.{i + 1}.{side}"
                p, q = mirrored(p, sx), mirrored(q, sx)
                b.append(Bone(name, p, q, parent=parent))
                hang = mirrored(wing_sides[i], sx) if wing_sides else Vector((0, 1, 0))
                d = (q - p).normalized()
                self.wing_side[name] = (hang - d * hang.dot(d)).normalized()
                self.wings[side].append(name)
                parent = name
        self.leg = {}         # side -> (hip, joint, ankle, toe) at rest.
        self.stand_at = {}    # side -> where the ankle is when standing.
        self.level = {}       # side -> the foot bone's turn when flat on the ground.
        for side, sx in SIDES:
            src = legs[side] if isinstance(legs, dict) else [mirrored(p, sx) for p in legs]
            hip, joint, ankle, toe = (Vector(p) for p in src)
            self.leg[side] = (hip, joint, ankle, toe)
            limits = {}
            if leg_exit is not None:
                limits = dict(surface=True, fade=leg_exit, around=(hip.x, hip.y, leg_reach))
            b.append(Bone(f"leg_upper.{side}", hip, joint, parent="body", **limits))
            b.append(Bone(f"leg_lower.{side}", joint, ankle, parent=f"leg_upper.{side}"))
            b.append(Bone(f"foot.{side}", ankle, toe, parent=f"leg_lower.{side}"))
        for side, sx in SIDES:
            other = "R" if side == "L" else "L"
            hip, joint, ankle, toe = self.leg[side]
            if side == folded:
                o = self.leg[other]
                self.stand_at[side] = Vector((-o[2].x, o[2].y, o[2].z))
                flat = Vector((-(o[3] - o[2]).x, (o[3] - o[2]).y, (o[3] - o[2]).z))
                # The folded foot turns about X to lie flat, pointing forward.
                self.level[side] = self.basis_turn(flat, toe - ankle)
            else:
                self.stand_at[side] = ankle.copy()
                self.level[side] = Quaternion()
        self.set_bones(b + list(extra_bones))
        self.walk, self.run = walk, run
        for g in (walk, run):
            g.stride = self.stride(g)
            g.speed = g.stride * FPS / (g.duty * g.frames)
        self._eat_curl = self.eat["curl"]

    @staticmethod
    def basis_turn(now, rest):
        """The turn that takes the direction `rest` to `now`, keeping X."""
        def basis(f):
            f = Vector(f).normalized()
            s = (X - f * X.dot(f)).normalized()
            return Matrix((f, s, f.cross(s))).transposed()
        return (basis(now) @ basis(rest).transposed()).to_quaternion()

    def stride(self, g):
        """How far a planted foot can travel under the hips at the gait's
        crouch, with a margin for the body's sway and roll."""
        best = 1e9
        for side, _ in SIDES:
            hip, joint, ankle, toe = self.leg[side]
            length = ((joint - hip).length + (ankle - joint).length) * 0.985
            height = hip.z - self.stand_at[side].z - g.crouch - abs(g.bob)
            reach = math.sqrt(max(0.0, length ** 2 - height ** 2)) - abs(self.stand_at[side].y - hip.y)
            best = min(best, reach)
        return max(0.0, 2 * best * g.reach)

    # ------------------------------------------------------------ binding

    def bind(self, mb):
        """Writes the bone weights: tagged vertices follow their tag, all
        the others are bound by distance like the welded surface. (The
        base bind() tells surface from details by vertex order, which
        bmesh does not keep once the cuts have merged vertices: new
        vertices fill the gaps.)"""
        tags = getattr(mb, "bone_tags", {})
        for v in mb.bm.verts:
            bone = tags.get(v)
            if bone is None:
                weights = self.surface_weights(v.co)
            elif callable(bone):
                weights = bone(v.co)
            else:
                weights = [(bone, 1.0)]
            weights = sorted(((w, n) for n, w in weights if w > 0.0), reverse=True)[:4]
            total = sum(w for w, _ in weights)
            for w, n in weights:
                v[mb.deform][mb._group_index(n)] = w / total

    def cuts(self):
        """Rings where the welded surface bends: where each welded thigh
        leaves the body and, with neck_reach, at every neck joint."""
        out = []
        if self.leg_exit is not None:
            for side, _ in SIDES:
                hip = self.leg[side][0]

                def near(c, n, hip=hip):
                    return math.hypot(c.x - hip.x, c.y - hip.y) < self.leg_reach and c.z < self.leg_exit[1]
                out.append((Vector((hip.x, hip.y, self.leg_exit[0])), (0, 0, 1), near))
        if self.neck_reach is not None:
            chain = [self.by_name[n] for n in self.neck] + [self.by_name["head"]]
            for a, c in zip(chain, chain[1:]):
                at = c.head
                normal = ((a.tail - a.head).normalized() + (c.tail - c.head).normalized()).normalized()

                def near(p, n, at=at):
                    return (p - at).length < self.neck_reach
                out.append((at, normal, near))
        return out

    def surface_weights(self, p):
        cands = []
        for bone in self.bones:
            reach = bone.reach(p) if bone.surface else 0.0
            if reach <= 0.0:
                continue
            # A faded bone counts as farther away, so it only wins near the leg.
            d = rigs.segment_distance(p, bone.head, bone.tail) + (1.0 - reach) * self.blend * 3
            cands.append((d, bone.name))
        d0 = min(d for d, _ in cands)
        return [(n, max(0.0, 1.0 - (d - d0) / self.blend) ** 2) for d, n in cands]

    # -------------------------------------------------------------- poses

    def plant(self, pose, side, target=None, toe=0.0):
        """Puts the ankle of a leg at `target` (standing place by default),
        the visible joint bent backward and the foot flat."""
        sx = 1.0 if side == "L" else -1.0
        target = self.stand_at[side] if target is None else target
        pose.limb(f"leg_upper.{side}", f"leg_lower.{side}", target, Vector((sx * 0.05, 1.0, 0.25)))
        pose.set_world(f"foot.{side}", Quaternion(X, math.radians(toe)) @ self.level[side])

    def stand(self, pose, both=False):
        for side, _ in SIDES:
            if both or side != self.folded:
                self.plant(pose, side)

    def swing(self, pose, wave):
        """Loose parts follow `wave` (-1 to 1)."""
        for bone, (axis, degrees) in self.dangles.items():
            pose.turn(bone, axis, degrees * wave)

    def wings_out(self, pose, degrees, flutter=0.0):
        """Holds the wings away from the body by turning them at the shoulder."""
        for side, sx in SIDES:
            if self.wings[side]:
                pose.turn(self.wings[side][0], Y, -sx * (degrees + flutter))

    def turn_neck(self, pose, axis, degrees, head_share=0.5):
        """Spreads a turn over the neck and the head."""
        for name in self.neck:
            pose.turn(name, axis, degrees * (1 - head_share) / len(self.neck))
        pose.turn("head", axis, degrees * head_share)

    def idle_pose(self, t):
        p = 2 * math.pi * t
        breath = math.sin(3 * p)
        pose = Pose(self, (0, 0, -0.002 * (1 + breath)))
        pose.turn("body", X, 0.6 * breath)
        self.stand(pose)

        # Quick looks: the head snaps to a side, holds, and snaps again.
        def snap(at, width=0.035):
            return smooth((t - at) / width)
        yaw = self.look * (snap(0.1) - 1.7 * snap(0.32) + 1.1 * snap(0.55) - 0.4 * snap(0.8))
        tilt = 12.0 * (snap(0.55) - snap(0.8))
        self.turn_neck(pose, Z, yaw, 0.6)
        pose.turn("head", Y, tilt)
        pose.turn("head", X, -1.5 * breath)
        flick = math.sin(math.pi * max(0.0, min(1.0, (t - 0.42) / 0.07)))
        if self.tail:
            pose.turn(self.tail[0], X, 10.0 * flick + 1.5 * breath)
        twitch = math.sin(math.pi * max(0.0, min(1.0, (t - 0.68) / 0.06)))
        twitch += math.sin(math.pi * max(0.0, min(1.0, (t - 0.76) / 0.06)))
        self.wings_out(pose, self.wing_twitch * twitch)
        self.swing(pose, 0.25 * breath + 0.5 * (snap(0.1, 0.07) - snap(0.17, 0.07))
                   - 0.5 * (snap(0.32, 0.07) - snap(0.39, 0.07)))
        return pose.q, pose.offset, {}

    def gait_pose(self, g, t):
        p = 2 * math.pi * t
        # Over the left foot at the middle of its stance, then over the right.
        over = math.cos(2 * math.pi * (t + g.phases[0] - g.duty / 2))
        air = 0.0
        if g.hop:  # Both feet leave the ground together.
            u = ((t + g.phases[0]) % 1.0 - g.duty) / (1 - g.duty)
            air = g.hop * math.sin(math.pi * max(0.0, min(1.0, u)))
        pose = Pose(self, (g.sway * over, 0, -g.crouch - g.bob * math.cos(2 * p) + air))
        pose.set_world("body", Quaternion(Y, math.radians(g.waddle * over)) @ Quaternion(X, math.radians(g.lean))
                       @ Quaternion(Z, math.radians(3.0 * math.sin(p))))
        for (side, sx), phase in zip(SIDES, g.phases):
            at = self.stand_at[side]
            psi = (t + phase) % 1.0
            if psi < g.duty:
                u = psi / g.duty
                target, toe = Vector((at.x, at.y - g.stride / 2 + g.stride * u, at.z)), 0.0
            else:
                u = (psi - g.duty) / (1 - g.duty)
                target = Vector((at.x, at.y + g.stride / 2 - g.stride * smooth(u),
                                 at.z + g.lift * math.sin(math.pi * u) + air))
                toe = g.toe * math.sin(math.pi * u) * (1 - u)
            self.plant(pose, side, target, toe)
        # The head holds still over the ground while a foot is planted,
        # then darts forward: once per step.
        phi = (2 * t + 0.15) % 1.0
        hold = 0.62
        back = -1 + 2 * phi / hold if phi < hold else 1 - 2 * smooth((phi - hold) / (1 - hold))
        for name in self.neck:
            pose.turn(name, X, -g.head_bob * back / len(self.neck))
        pose.set_world("head", Quaternion(Z, math.radians(-2.0 * math.sin(p)))
                       @ Quaternion(X, math.radians(g.lean * 0.3)))
        if self.tail:
            pose.turn(self.tail[0], X, g.tail_up + g.tail * 0.5 * math.cos(2 * p + 0.5))
            pose.turn(self.tail[0], Z, g.tail * math.sin(p))
        self.wings_out(pose, g.wings, g.wings * 0.3 * math.sin(2 * p))
        self.swing(pose, math.sin(2 * p - 0.9))
        return pose.q, pose.offset, {}

    def bent(self, amount, curl):
        """The eating posture: `amount` (0 to 1) of the way down, the neck
        curled by `curl` degrees per bone."""
        e = self.eat
        pose = Pose(self, (0, 0, -e["crouch"] * amount))
        pose.turn("body", X, e["pitch"] * amount)
        self.stand(pose)
        for name in self.neck:
            pose.turn(name, X, curl * amount)
        pose.set_world("head", Quaternion(X, math.radians(e["head"] * amount)))
        return pose

    def beak_height(self, pose):
        head = self.by_name["head"]
        return (pose.head("head") + pose.world("head") @ (self.beak_tip - head.head)).z

    def eat_curl(self):
        """Degrees each neck bone bends so the beak's tip ends at the
        height asked for (or as low as the neck allows)."""
        if self._eat_curl is None:
            target, step = self.eat["height"], 2.0
            best, prev = (1e9, 0.0), None
            curl = -90.0
            while curl <= 150.0:
                z = self.beak_height(self.bent(1.0, curl))
                if z < best[0]:
                    best = (z, curl)
                if prev is not None and prev[0] > target >= z:
                    lo, hi = prev[1], curl  # Refine between the two samples.
                    for _ in range(30):
                        mid = (lo + hi) / 2
                        if self.beak_height(self.bent(1.0, mid)) > target:
                            lo = mid
                        else:
                            hi = mid
                    best = (target, (lo + hi) / 2)
                    break
                prev = (z, curl)
                curl += step
            self._eat_curl = best[1]
        return self._eat_curl

    def eat_pose(self, t):
        e = self.eat
        down = smooth(t / 0.22) * (1 - smooth((t - 0.8) / 0.2))
        inside = smooth((t - 0.22) / 0.04) * (1 - smooth((t - 0.76) / 0.04))
        peck = (0.5 - 0.5 * math.cos(2 * math.pi * e["pecks"] * (t - 0.22) / 0.58)) * inside
        pose = self.bent(down * (1 - e["peck"] * peck), self.eat_curl())
        if self.tail:
            pose.turn(self.tail[0], X, -e["pitch"] * 0.4 * down)
        self.swing(pose, (2 * peck - 1) * inside)
        return pose.q, pose.offset, {}

    def die_pose(self, t):
        # The legs give way, then it rolls onto its right side and lies still.
        sag = smooth(t / 0.35)
        roll = smooth((t - 0.25) / 0.45)
        pivot = self.by_name["body"].head
        drop = min(0.5 * (pivot.z - self.lie_height), 0.08)
        up = Pose(self, (0, 0, -drop * sag))
        self.stand(up)
        pose = Pose(self, (0, 0, -drop * sag * (1 - roll) + (self.lie_height - pivot.z) * roll))
        pose.set_world("body", Quaternion(Y, math.radians(-88.0 * roll)))
        for name, q in up.q.items():
            pose.q[name] = q.slerp(Quaternion(), roll)   # The legs go limp.
        for name in self.neck + ["head"]:
            bone = self.by_name[name]
            axis = (bone.tail - bone.head).normalized().cross(-X)
            if axis.length > 1e-3:   # Droops toward the ground side.
                pose.turn(name, axis.normalized(), self.die_droop * roll / (len(self.neck) + 1))
            pose.turn(name, X, 10.0 * sag * (1 - roll))
        if self.tail:
            pose.turn(self.tail[0], X, -15.0 * roll)
        self.wings_out(pose, 12.0 * math.sin(math.pi * roll))
        self.swing(pose, math.sin(math.pi * roll))
        return pose.q, pose.offset, {}

    def open_wings(self, pose, elevation, sweep=0.0):
        """Spreads the wings: bone i of each wing points sideways, raised by
        elevation(i) degrees and swept back by `sweep` (one number, or one
        per bone: forward at the arm and back at the hand), its feathers
        trailing behind."""
        sweeps = sweep if isinstance(sweep, (tuple, list)) else [sweep] * 3
        for side, sx in SIDES:
            for i, name in enumerate(self.wings[side]):
                e = math.radians(elevation(i))
                b = self.by_name[name]
                pose.orient(name, Vector((sx * math.cos(e), sweeps[i], math.sin(e))), Vector((0, 1, 0)),
                            rest_forward=b.tail - b.head, rest_side=self.wing_side[name])

    def air_pose(self, t):
        a = self.air
        p = 2 * math.pi * a["beats"] * t
        pose = Pose(self, (0, 0, a["lift"] - a["bob"] * math.sin(p)))
        pitch = a["pitch"] + 2.0 * math.sin(p + 1.0)
        pose.set_world("body", Quaternion(X, math.radians(pitch)))
        n = len(self.neck) + 1
        for i, name in enumerate(self.neck + ["head"]):   # The head looks ahead.
            share = (i + 1) / n
            pose.set_world(name, Quaternion(X, math.radians(pitch * (1 - share) + a["head"] * share)))
        for side, _ in SIDES:
            pose.turn(f"leg_upper.{side}", X, a["tuck"])
            pose.turn(f"leg_lower.{side}", X, -a["tuck"] * 1.6)
            pose.turn(f"foot.{side}", X, a["foot"])
        if self.tail:
            pose.turn(self.tail[0], X, a["tail"] + 4.0 * math.sin(p + 0.5))
        self.open_wings(pose, lambda i: a["mid"] + a["amp"] * (1 + 0.25 * i) * math.sin(p - a["lag"] * i),
                        a["sweep"])
        self.swing(pose, 0.6 * math.sin(p - 1.0))
        return pose.q, pose.offset, {}

    def clips(self):
        w, r = self.walk, self.run
        out = [
            ("idle", self.idle_frames, True, self.idle_pose, None),
            ("walk", w.frames, True, lambda t: self.gait_pose(w, t), w.speed),
            ("run", r.frames, True, lambda t: self.gait_pose(r, t), r.speed),
            ("eat", self.eat["frames"], True, self.eat_pose, None),
            ("die", self.die_frames, False, self.die_pose, None),
        ]
        if self.air is not None:
            out.append((self.air["name"], self.air["frames"], True, self.air_pose, self.air["speed"]))
        return out
