"""Shared pieces of the `folk` proposal family: townspeople by trade,
fighters and race variants, all built on the game's own characters
(art/blender/people: the welded body of _human.Human, the helpers of
lizardfolk.Folk and the skeleton of rigs_human.Humanoid), so they share the
game's proportions, bone names and clips.

What this module adds:

- Townsfolk: a data-driven human. A dict of options picks the body, the
  clothes, the hair, the hat, what is carried in each hand and on the back.
- TownClips: a mixin for any of the game's character skeletons that keeps
  only the clips a character names (spec.clip_names) and holds the carried
  tools properly while standing, walking and running (spec.carry_r/l).
- Tools are part of the model, bound to the hand bone and built the way the
  game's separate tools are held: the long axis along the hand's forward
  direction (-Y while the arm hangs at rest). The game's own clips (chop,
  shoot, work, fish_stand) therefore swing them correctly.
"""

import contextlib
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROPOSALS = os.path.dirname(HERE)
sys.path.insert(0, PROPOSALS)

import _kit as kit  # noqa: E402  (adds art/blender to the path)

sys.path.insert(0, os.path.join(os.path.dirname(PROPOSALS), "people"))

from mathutils import Quaternion, Vector  # noqa: E402

import common  # noqa: E402
import rigs_human  # noqa: E402
import studies  # noqa: E402
from lizardfolk import (Folk, FolkRig, belt, blob, buckle, collar, hip_ring, hull, land, panel, sheet,  # noqa: E402
                        skirt, spike, sym, tube)
from rigs import Bone, Pose, X, Z, smooth  # noqa: E402

FAMILY = "folk"
lerp = rigs_human.lerp


# ------------------------------------------------------------------ colors

def mix(a, b, t):
    out = 0
    for shift in (16, 8, 0):
        x, y = (a >> shift) & 255, (b >> shift) & 255
        out |= int(round(x + (y - x) * t)) << shift
    return out


def shaded(colors):
    """Every material with its lighter and darker facet tones."""
    out = {}
    for name, value in colors.items():
        out[name] = common.rgb(value)
        out[name + "_light"] = common.rgb(mix(value, 0xFFFFFF, 0.13))
        out[name + "_shade"] = common.rgb(mix(value, 0x000000, 0.15))
    return out


# Materials every character may use. The first eight are the game's palette
# slots (common.PALETTE_SLOTS), so the game could recolor them as it does
# with its villagers.
BASE = dict(
    skin=0xF0B284, hair=0x6A3B2A, top=0x8A6A44, bottom=0x4B4450, shoes=0x5A3626, belt=0x70432B, hat=0x7A5636,
    apron=0xE8E0D0, accent=0xB8382E, metal=0x8A8FA0, metal_dark=0x5A5E6E, wood=0x8A6038, wood_dark=0x5E4028,
    gold=0xE2B13C, white=0xEEE8DC, straw=0xD9B95A, eye=0x1A1414, flame=0xF08A1E, flame_core=0xF8E060,
    bone=0xE6DCC8, rope=0xB89A62, glass=0x9AD8F0, parchment=0xE8D8A8, dark=0x2A2630, green=0x4E8A3A, red=0xB8382E,
    fur=0x8A6A4A, cape=0x8A2E2A, bread=0xC98A46,
)


# ------------------------------------------------------------- the skeleton

def pulse(t, a, b, c=None, d=None):
    """0 before a, rises to 1 at b, holds to c and falls back to 0 at d."""
    c = b if c is None else c
    d = c if d is None else d
    up = smooth((t - a) / max(b - a, 1e-6))
    down = 1.0 - smooth((t - c) / max(d - c, 1e-6)) if d > c else (1.0 if t <= c else 0.0)
    return up * down


# How a hand carries its tool while standing and walking: where the wrist
# is from the shoulder (x outward, of a 1.8 m body) and where the tool
# points (None: the hand just follows the forearm).
CARRY = {
    "staff": ((0.07, -0.25, -0.28), (0, 0, 1)),          # Upright, its butt on the ground.
    "cane": ((0.09, -0.2, -0.5), (0, 0, 1)),             # A short stick under the palm.
    "low": ((0.08, -0.2, -0.38), (0, -0.55, 0.83)),      # A one-handed tool, tilted forward.
    "shoulder": ((0.02, -0.2, -0.2), (0, 0.8, 0.6)),     # A long tool resting on the shoulder.
    "aim": ((-0.02, -0.3, -0.3), (0, -1, 0.1)),          # Pointing ahead (a crossbow).
    "raised": ((0.1, -0.24, -0.12), (0, -0.15, 1)),      # Held up (a torch, a bell, a lantern).
    "hang": ((0.06, -0.24, -0.32), (0, 0, 1)),           # Something hanging below the hand (a basket).
    "guard": ((-0.1, -0.26, -0.28), None),               # The forearm across the body (a shield).
    "chest": ((-0.1, -0.24, -0.3), None),                # A hand on the chest (a book, a lute).
}


def carry(spec, clip, t, pose):
    """Changes a clip's pose for what the character carries."""
    k = spec.k
    hunch = getattr(spec, "hunch", 0.0)
    if hunch:
        pose.turn("spine", X, hunch)
        pose.turn("neck", X, -hunch * 0.5)
    if clip not in ("idle", "walk", "run"):
        return
    for side, sx in (("R", -1.0), ("L", 1.0)):
        style = getattr(spec, "carry_" + side.lower(), None)
        if not style:
            continue
        off, forward = CARRY[style]
        target = pose.head(f"upper_arm.{side}") + Vector((sx * off[0], off[1], off[2])) * k
        if clip != "idle" and style in ("staff", "cane"):
            target.z += 0.05 * k        # Lifted off the ground while walking.
        pose.limb(f"upper_arm.{side}", f"lower_arm.{side}", target, Vector((sx * 0.6, 0.5, -1.0)))
        if forward is not None:
            pose.orient(f"hand.{side}", forward, Vector((1, 0, 0)))
        else:
            pose.q.pop(f"hand.{side}", None)


class TownClips:
    """Mixin for a character skeleton: keeps the clips the character names
    in spec.clip_names, a list of (name in the model, pose) where pose is one
    of the game's clips or one of the poses below, and holds the tools."""

    def clip_props(self):
        return {}   # The tools are part of the model.

    def clips(self):
        raw = {c[0]: c for c in super().clips()}
        w, r = self.walk, self.run
        own = {
            "dig": (40, self.dig_pose), "strike": (30, self.strike_pose), "thrust": (36, self.thrust_pose),
            "cast": (60, self.cast_pose), "wave": (45, self.wave_pose), "aim": (75, self.aim_pose),
            "play": (60, self.play_pose), "dance": (48, self.dance_pose), "sow": (48, self.sow_pose),
            "write": (60, self.write_pose),
        }
        out = []
        for name, source in self.spec.clip_names:
            if source in own:
                frames, fn = own[source]
                out.append((name, frames, True, self.carried(source, self.with_cloth(fn)), None))
            else:
                _, frames, loops, fn, speed = raw[source]
                out.append((name, frames, loops, self.carried(source, fn), speed))
        return out

    def with_cloth(self, fn):
        def pose_fn(t):
            q, offset, more = fn(t)
            if hasattr(self, "cloth"):
                pose = Pose(self, offset)
                pose.q = q
                self.cloth(pose)
            return q, offset, more
        return pose_fn

    def carried(self, name, fn):
        def pose_fn(t):
            q, offset, more = fn(t)
            pose = Pose(self, offset)
            pose.q = q
            carry(self.spec, name, t, pose)
            return pose.q, pose.offset, more
        return pose_fn

    # ------------------------------------------------------------- poses

    def swing(self, t, up=0.45, hold=0.55, hit=0.67):
        """0: the tool in its target; 1: wound up."""
        if t < up:
            return smooth(t / up)
        if t < hold:
            return 1.0
        if t < hit:
            return 1.0 - ((t - hold) / (hit - hold)) ** 2
        return 0.03 * math.sin(math.pi * (t - hit) / (1.0 - hit))

    def dig_pose(self, t):
        """A two-handed blow at the ground in front (a hoe, a pick, a spade)."""
        k = self.k
        w = self.swing(t)
        pose = Pose(self, (0, 0, (-0.1 + 0.06 * w) * k))
        self.stand(pose, {"L": (0.04, -0.16), "R": (-0.05, 0.12)}, yaw=-8.0)
        pose.turn("spine", X, lerp(24.0, 2.0, w))
        pose.turn("chest", X, lerp(10.0, -4.0, w))
        pose.set_world("head", Quaternion(X, math.radians(14.0)))
        strike = Vector((-0.05, -0.42, 0.86)) * k
        wound = Vector((-0.2, -0.1, 1.5)) * k
        grip = strike.lerp(wound, w) + Vector((0, -0.18, 0.1)) * k * math.sin(math.pi * w)
        direction = Vector((0.1, -0.75, -0.65)).normalized().slerp(Vector((-0.1, 0.5, 0.86)).normalized(), w)
        self.hold(pose, grip, direction, hand="R", other=0.24)
        return pose.q, pose.offset, {}

    def strike_pose(self, t):
        """A one-handed blow forward with what the right hand holds."""
        k = self.k
        w = self.swing(t, 0.4, 0.5, 0.62)
        pose = Pose(self, (0, -0.05 * k * (1 - w), -0.045 * k))
        self.stand(pose, {"L": (0.03, -0.18), "R": (-0.04, 0.12)})
        pose.turn("hips", Z, lerp(12.0, -10.0, w))
        pose.turn("spine", X, lerp(10.0, -2.0, w))
        pose.turn("chest", Z, lerp(16.0, -20.0, w))
        low = Vector((-0.04, -0.48, 1.12)) * k
        high = Vector((-0.3, -0.02, 1.6)) * k
        grip = low.lerp(high, w) + Vector((-0.08, -0.15, 0.1)) * k * math.sin(math.pi * w)
        direction = Vector((0.25, -0.95, 0.1)).normalized().slerp(Vector((-0.1, 0.35, 0.93)).normalized(), w)
        self.hold(pose, grip, direction, hand="R", other=None)
        pose.limb("upper_arm.L", "lower_arm.L", pose.head("upper_arm.L") + Vector((-0.08, -0.28, -0.24)) * k,
                  Vector((0.6, 0.5, -1.0)))
        return pose.q, pose.offset, {}

    def thrust_pose(self, t):
        """A two-handed thrust with a long weapon."""
        k = self.k
        pull = pulse(t, 0.0, 0.3, 0.36, 0.46)
        push = pulse(t, 0.36, 0.46, 0.56, 0.95)
        pose = Pose(self, (0, (0.04 * pull - 0.14 * push) * k, (-0.06 - 0.03 * push) * k))
        pose.turn("hips", Z, -28.0 + 8.0 * pull - 10.0 * push)
        self.stand(pose, {"L": (0.02, -0.22 - 0.1 * push), "R": (-0.06, 0.16)}, yaw=-20.0)
        pose.turn("spine", X, 6.0 + 8.0 * push)
        pose.set_world("head", Quaternion())
        grip = Vector((-0.17, 0.02 + 0.16 * pull - 0.34 * push, 1.14)) * k
        self.hold(pose, grip, Vector((0.14, -1.0, 0.03)), hand="R", other=-0.36)
        return pose.q, pose.offset, {}

    def cast_pose(self, t):
        """Raises the right hand's staff and reaches out with the left."""
        k = self.k
        up = pulse(t, 0.0, 0.35, 0.65, 1.0)
        tremble = math.sin(2 * math.pi * 6 * t) * up
        pose = Pose(self, (0, 0, -0.01 * k))
        self.stand(pose)
        pose.turn("spine", X, -6.0 * up)
        pose.turn("head", X, -10.0 * up)
        a, b = Vector((-0.07, -0.25, -0.28)), Vector((-0.13, -0.3, 0.1))
        pose.limb("upper_arm.R", "lower_arm.R", pose.head("upper_arm.R") + a.lerp(b, up) * k,
                  Vector((-0.6, 0.5, -1.0)))
        pose.orient("hand.R", Vector((0, -0.25 * up, 1)), Vector((1, 0, 0)))
        a, b = Vector((0.08, -0.06, -0.5)), Vector((0.1, -0.42, 0.06 + 0.02 * tremble))
        pose.limb("upper_arm.L", "lower_arm.L", pose.head("upper_arm.L") + a.lerp(b, up) * k,
                  Vector((0.6, 0.5, -1.0)))
        pose.aim("hand.L", Vector((0.0, -0.8, 0.5)).lerp(Vector((0, 0, -1)), 1 - up))
        return pose.q, pose.offset, {}

    def wave_pose(self, t):
        """Shakes what the right hand holds up (a bell, a mug, a hand out)."""
        k = self.k
        p = 2 * math.pi * t
        shake = math.sin(4 * p)
        pose = Pose(self, (0.006 * k * math.sin(p), 0, -0.006 * k))
        self.stand(pose)
        pose.turn("chest", Z, 5.0 * math.sin(p))
        pose.turn("head", Z, 12.0 * math.sin(p))
        pose.limb("upper_arm.R", "lower_arm.R",
                  pose.head("upper_arm.R") + Vector((-0.1, -0.3, 0.0 + 0.07 * shake)) * k, Vector((-0.6, 0.5, -1.0)))
        pose.orient("hand.R", Vector((0.25 * shake, -0.2, 1)), Vector((1, 0, 0)))
        self.hang_arm(pose, "L", 2.0 * math.sin(p), 10.0)
        return pose.q, pose.offset, {}

    def aim_pose(self, t):
        """Shoulders a crossbow, shoots and lowers it."""
        k = self.k
        up = pulse(t, 0.0, 0.25, 0.8, 1.0)
        kick = pulse(t, 0.55, 0.58, 0.6, 0.7)
        pose = Pose(self, (0, 0, -0.03 * k))
        pose.turn("hips", Z, -30.0)
        self.stand(pose, {"L": (0.0, -0.18), "R": (-0.08, 0.14)}, yaw=-20.0)
        pose.turn("chest", Z, -8.0 * up)
        pose.set_world("head", Quaternion(Z, math.radians(-6.0)))
        grip = Vector((-0.14, -0.25, 1.05)).lerp(Vector((-0.1, -0.3, 1.42)), up) * k + Vector((0, 0.05, 0.01)) * k * kick
        direction = Vector((0.1, -0.9, -0.4)).normalized().slerp(Vector((0.12, -1.0, 0.03 * kick)).normalized(), up)
        self.hold(pose, grip, direction, hand="R", other=-0.26)
        return pose.q, pose.offset, {}

    def play_pose(self, t):
        """Plays what hangs on the chest (a lute): the left hand on its
        neck, the right one strumming."""
        k = self.k
        p = 2 * math.pi * t
        strum = math.sin(6 * p)
        pose = Pose(self, (0.01 * k * math.sin(p), 0, -0.012 * k * (1 + math.sin(2 * p))))
        self.stand(pose)
        pose.turn("hips", Z, 5.0 * math.sin(p))
        pose.turn("head", Z, 10.0 * math.sin(p))
        pose.turn("head", Y_AXIS, 6.0 * math.sin(2 * p))
        at, turn = pose.head("chest"), pose.world("chest")
        rest = self.by_name["chest"].head
        right = Vector((-0.1, -0.27, 1.17 + 0.035 * strum)) * k
        left = Vector((0.29, -0.2, 1.36)) * k
        pose.limb("upper_arm.R", "lower_arm.R", at + turn @ (right - rest), Vector((-0.8, 0.4, -0.6)))
        pose.limb("upper_arm.L", "lower_arm.L", at + turn @ (left - rest), Vector((0.6, 0.6, -1.0)))
        return pose.q, pose.offset, {}

    def dance_pose(self, t):
        """A hopping folk dance: arms up, hips turning, a kick on each beat."""
        k = self.k
        p = 2 * math.pi * t
        hop = abs(math.sin(2 * p))
        pose = Pose(self, (0.03 * k * math.sin(p), 0, (-0.05 + 0.05 * hop) * k))
        pose.turn("hips", Z, 14.0 * math.sin(p))
        for side, sx, phase in (("L", 1.0, 0.0), ("R", -1.0, 0.5)):
            ankle = self.rest[side]["ankle"]
            lift = max(0.0, math.sin(p + phase * 2 * math.pi))
            pose.limb(f"thigh.{side}", f"shin.{side}",
                      Vector((ankle.x, ankle.y - 0.22 * k * lift, ankle.z + 0.16 * k * lift)),
                      Vector((sx * 0.2, -1, 0.3)))
            pose.set_world(f"foot.{side}", Quaternion(X, math.radians(20.0 * lift)))
            raised = 0.5 + 0.5 * math.sin(p + phase * 2 * math.pi)
            pose.limb(f"upper_arm.{side}", f"lower_arm.{side}",
                      pose.head(f"upper_arm.{side}") + Vector((sx * 0.22, -0.1, 0.05 + 0.25 * raised)) * k,
                      Vector((sx * 1.0, 0.3, -0.6)))
        pose.turn("chest", Z, -10.0 * math.sin(p))
        pose.turn("head", Z, 8.0 * math.sin(p))
        return pose.q, pose.offset, {}

    def sow_pose(self, t):
        """Throws seed (or feed, or alms) from the right hand in a wide arc."""
        k = self.k
        a = pulse(t, 0.1, 0.45, 0.5, 0.9)
        pose = Pose(self, (0, 0, -0.015 * k))
        self.stand(pose, {"L": (0.02, -0.08), "R": (-0.02, 0.06)})
        pose.turn("chest", Z, 22.0 - 44.0 * a)
        pose.turn("head", Z, 10.0 - 20.0 * a)
        s, e = Vector((0.12, -0.26, -0.34)), Vector((-0.3, -0.36, -0.12))
        pose.limb("upper_arm.R", "lower_arm.R", pose.head("upper_arm.R") + s.lerp(e, a) * k,
                  Vector((-0.6, 0.5, -1.0)))
        pose.limb("upper_arm.L", "lower_arm.L", pose.head("upper_arm.L") + Vector((-0.1, -0.24, -0.3)) * k,
                  Vector((0.6, 0.5, -1.0)))
        return pose.q, pose.offset, {}

    def write_pose(self, t):
        """Reads or writes on what the left hand holds: the right hand
        moves over it and the head nods."""
        k = self.k
        p = 2 * math.pi * t
        pose = Pose(self, (0, 0, -0.008 * k))
        self.stand(pose)
        pose.turn("spine", X, 4.0)
        pose.set_world("head", Quaternion(X, math.radians(16.0 + 3.0 * math.sin(p))))
        pose.limb("upper_arm.L", "lower_arm.L", pose.head("upper_arm.L") + Vector((-0.1, -0.26, -0.26)) * k,
                  Vector((0.6, 0.5, -1.0)))
        pose.limb("upper_arm.R", "lower_arm.R",
                  pose.head("upper_arm.R") + Vector((0.1 + 0.04 * math.sin(5 * p), -0.3, -0.22 + 0.015 * math.cos(7 * p))) * k,
                  Vector((-0.6, 0.5, -1.0)))
        return pose.q, pose.offset, {}


Y_AXIS = Vector((0, 1, 0))
TownRig = type("TownRig", (TownClips, FolkRig), {})


def with_clips(rig):
    """Gives a game character's skeleton the TownClips behavior."""
    rig.__class__ = type("Town" + type(rig).__name__, (TownClips, type(rig)), {})
    return rig


# ------------------------------------------------------------------- tools

def tool_frame(spec, side):
    """T(a, b, c): a point of a tool held in a hand, in meters of the 1.8 m
    body: c along the tool (up when it is held upright), b away from the
    holder, a to the side. At rest the tool lies along -Y through the hand."""
    h = Vector(spec.parts["hand." + side][1])
    k = spec.k
    return lambda a, b, c: h + Vector((a, -c, -b)) * k


def rod(mb, T, k, c0, c1, r, mat, a=0.0, b=0.0, r1=None, sides=5):
    return mb.cylinder(T(a, b, c0), T(a, b, c1), r * k, (r if r1 is None else r1) * k, mat, segments=sides)


def slab(mb, T, lo, hi, mat):
    """A box between two corners given in the tool's frame."""
    return hull(mb, [T(a, b, c) for a in (lo[0], hi[0]) for b in (lo[1], hi[1]) for c in (lo[2], hi[2])], mat)


def t_hull(mb, T, points, mat, mirror=True):
    pts = []
    for a, b, c in points:
        pts.append(T(a, b, c))
        if mirror and a:
            pts.append(T(-a, b, c))
    return hull(mb, pts, mat)


def tool_staff(mb, T, k, top=0.72, mat="wood"):
    rod(mb, T, k, -1.16, top, 0.019, mat)


def tool_crook(mb, T, k):
    tool_staff(mb, T, k, 0.7)
    tube(mb, [T(0, 0, 0.68), T(0, 0.04, 0.82), T(0, 0.13, 0.88), T(0, 0.21, 0.82), T(0, 0.2, 0.72)],
         [0.019 * k, 0.018 * k, 0.017 * k, 0.016 * k, 0.014 * k], "wood", sides=5)


def tool_cane(mb, T, k):
    rod(mb, T, k, -0.93, 0.0, 0.016, "wood_dark")
    rod(mb, T, k, -0.01, 0.03, 0.03, "wood_dark", sides=6)


def tool_pointer(mb, T, k):
    rod(mb, T, k, -0.06, 0.7, 0.012, "wood_dark", r1=0.006, sides=4)


def tool_hoe(mb, T, k):
    rod(mb, T, k, -0.28, 1.02, 0.018, "wood")
    slab(mb, T, (-0.075, 0.0, 0.98), (0.075, 0.2, 1.01), "metal")
    slab(mb, T, (-0.02, -0.02, 0.96), (0.02, 0.03, 1.03), "metal_dark")


def tool_pitchfork(mb, T, k):
    rod(mb, T, k, -1.16, 0.55, 0.018, "wood")
    slab(mb, T, (-0.1, -0.012, 0.55), (0.1, 0.012, 0.58), "metal")
    for a in (-0.09, 0.0, 0.09):
        rod(mb, T, k, 0.57, 0.88, 0.011, "metal", a=a, r1=0.003, sides=4)


def tool_scythe(mb, T, k):
    rod(mb, T, k, -1.16, 0.7, 0.018, "wood")
    t_hull(mb, T, [(0.0, 0.0, 0.7), (0.0, 0.0, 0.64), (0.0, 0.3, 0.74), (0.0, 0.62, 0.6), (0.006, 0.3, 0.68),
                   (-0.006, 0.3, 0.68)], "metal", mirror=False)


def tool_axe(mb, T, k):
    rod(mb, T, k, -0.3, 0.62, 0.02, "wood")
    t_hull(mb, T, [(0.014, -0.03, 0.46), (0.014, -0.03, 0.6), (0.014, 0.06, 0.48), (0.014, 0.06, 0.58),
                   (0.0, 0.17, 0.4), (0.0, 0.17, 0.66)], "metal")


def tool_pick(mb, T, k):
    rod(mb, T, k, -0.28, 0.8, 0.02, "wood")
    for s in (-1, 1):
        mb.cylinder(T(0, 0, 0.77), T(0, s * 0.3, 0.7), 0.032 * k, 0.004 * k, "metal", segments=4)
    slab(mb, T, (-0.03, -0.04, 0.73), (0.03, 0.04, 0.81), "metal_dark")


def tool_shovel(mb, T, k):
    rod(mb, T, k, -0.28, 0.8, 0.018, "wood")
    t_hull(mb, T, [(0.085, 0.0, 0.78), (0.085, 0.012, 0.98), (0.0, 0.02, 1.08), (0.0, -0.012, 0.78),
                   (0.07, -0.012, 0.9)], "metal")
    slab(mb, T, (-0.05, -0.012, -0.3), (0.05, 0.012, -0.27), "wood_dark")


def tool_hammer(mb, T, k):
    rod(mb, T, k, -0.1, 0.32, 0.016, "wood")
    slab(mb, T, (-0.035, -0.085, 0.27), (0.035, 0.085, 0.35), "metal_dark")


def tool_mallet(mb, T, k):
    rod(mb, T, k, -0.1, 0.3, 0.016, "wood")
    mb.cylinder(T(0, -0.09, 0.3), T(0, 0.09, 0.3), 0.05 * k, 0.05 * k, "wood_dark", segments=6)


def tool_trowel(mb, T, k):
    rod(mb, T, k, -0.06, 0.08, 0.016, "wood")
    t_hull(mb, T, [(0.05, 0.0, 0.09), (0.0, 0.0, 0.3), (0.05, 0.008, 0.09), (0.0, 0.008, 0.3)], "metal")


def tool_saw(mb, T, k):
    slab(mb, T, (-0.012, -0.03, -0.07), (0.012, 0.05, 0.07), "wood")
    t_hull(mb, T, [(0.003, -0.03, 0.07), (0.003, 0.075, 0.07), (0.003, -0.03, 0.6), (0.003, 0.03, 0.6)], "metal")


def tool_peel(mb, T, k):
    """A baker's peel standing upright, with a loaf on its blade."""
    rod(mb, T, k, -1.16, 0.34, 0.016, "wood")
    slab(mb, T, (-0.13, -0.012, 0.34), (0.13, 0.012, 0.64), "wood")
    blob(mb, T(0, 0.05, 0.5), (0.09 * k, 0.11 * k, 0.05 * k), "bread", count=10, seed=3)


def tool_rolling_pin(mb, T, k):
    mb.cylinder(T(-0.17, 0, 0.02), T(0.17, 0, 0.02), 0.03 * k, 0.03 * k, "wood", segments=6)
    mb.cylinder(T(-0.24, 0, 0.02), T(0.24, 0, 0.02), 0.012 * k, 0.012 * k, "wood_dark", segments=4)


def tool_rod(mb, T, k):
    """A fishing rod with a float hanging from its tip."""
    rod(mb, T, k, -0.22, 1.0, 0.014, "wood", r1=0.009)
    rod(mb, T, k, 1.0, 2.0, 0.009, "wood_dark", r1=0.004)
    mb.cylinder(T(0, 0, 2.0), T(0, 0.3, 1.75), 0.003 * k, 0.003 * k, "white", segments=3)
    blob(mb, T(0, 0.3, 1.73), (0.02 * k, 0.02 * k, 0.03 * k), "red", count=8, seed=2)


def tool_bow(mb, T, k):
    pts = [(0.2, -0.68), (0.1, -0.46), (0.025, -0.22), (0.0, 0.0), (0.025, 0.22), (0.1, 0.46), (0.2, 0.68)]
    tube(mb, [T(a, 0, c) for a, c in pts], [r * k for r in (0.008, 0.012, 0.015, 0.018, 0.015, 0.012, 0.008)],
         "wood", sides=4)
    mb.cylinder(T(0.2, 0, -0.68), T(0.2, 0, 0.68), 0.003 * k, 0.003 * k, "white", segments=3)


def tool_crossbow(mb, T, k):
    slab(mb, T, (-0.022, -0.035, -0.28), (0.022, 0.03, 0.42), "wood")
    t_hull(mb, T, [(0.0, -0.01, 0.4), (0.0, 0.025, 0.4), (0.0, -0.01, 0.36), (0.36, -0.01, 0.27), (0.36, 0.02, 0.27),
                   (0.36, 0.0, 0.25)], "metal")
    mb.cylinder(T(-0.36, 0.01, 0.26), T(0.36, 0.01, 0.26), 0.004 * k, 0.004 * k, "white", segments=3)
    rod(mb, T, k, 0.05, 0.46, 0.006, "wood_dark", b=0.04, sides=3)


def tool_sword(mb, T, k, length=0.8, mat="metal"):
    rod(mb, T, k, -0.07, 0.07, 0.016, "belt")
    slab(mb, T, (-0.09, -0.016, 0.07), (0.09, 0.016, 0.1), "gold")
    t_hull(mb, T, [(0.032, 0.0, 0.1), (0.028, 0.0, length * 0.9), (0.0, 0.0, length), (0.0, 0.009, 0.1),
                   (0.0, -0.009, 0.1), (0.0, 0.007, length * 0.9), (0.0, -0.007, length * 0.9)], mat)
    blob(mb, T(0, 0, -0.085), (0.024 * k, 0.024 * k, 0.024 * k), "gold", count=8, seed=1)


def tool_dagger(mb, T, k):
    tool_sword(mb, T, k, length=0.36)


def tool_club(mb, T, k):
    rod(mb, T, k, -0.1, 0.25, 0.02, "wood", r1=0.03, sides=6)
    rod(mb, T, k, 0.25, 0.62, 0.03, "wood_dark", r1=0.055, sides=6)
    for i in range(5):
        a = i * 2.4
        d = Vector((math.cos(a), math.sin(a), 0.0))
        spike(mb, T(d.x * 0.04, d.y * 0.04, 0.4 + 0.045 * i), T(d.x * 0.1, d.y * 0.1, 0.4 + 0.045 * i), 0.03 * k,
              "metal")


def tool_mace(mb, T, k):
    rod(mb, T, k, -0.1, 0.5, 0.017, "wood_dark")
    blob(mb, T(0, 0, 0.56), (0.07 * k, 0.07 * k, 0.07 * k), "metal", count=12, seed=5)
    for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        spike(mb, T(d[0] * 0.05, d[1] * 0.05, 0.56), T(d[0] * 0.12, d[1] * 0.12, 0.56), 0.04 * k, "metal_dark")
    spike(mb, T(0, 0, 0.61), T(0, 0, 0.7), 0.04 * k, "metal_dark")


def tool_spear(mb, T, k, top=0.82):
    rod(mb, T, k, -1.16, top, 0.017, "wood")
    t_hull(mb, T, [(0.04, 0.0, top + 0.06), (0.0, 0.0, top + 0.28), (0.0, 0.012, top + 0.04), (0.0, -0.012, top + 0.04),
                   (0.0, 0.0, top - 0.02)], "metal")


def tool_pike(mb, T, k):
    tool_spear(mb, T, k, top=1.75)


def tool_halberd(mb, T, k):
    tool_spear(mb, T, k, top=0.95)
    t_hull(mb, T, [(0.006, 0.02, 0.72), (0.006, 0.02, 0.92), (0.0, 0.2, 0.66), (0.0, 0.2, 0.98), (0.006, 0.12, 0.82)],
           "metal")
    mb.cylinder(T(0, -0.02, 0.84), T(0, -0.16, 0.8), 0.022 * k, 0.003 * k, "metal", segments=4)


def tool_banner(mb, T, k, mat="accent"):
    rod(mb, T, k, -1.16, 1.25, 0.018, "wood_dark")
    blob(mb, T(0, 0, 1.28), (0.035 * k, 0.035 * k, 0.05 * k), "gold", count=8, seed=4)
    t_hull(mb, T, [(0.0, 0.0, 1.2), (0.0, 0.0, 0.62), (0.5, 0.0, 1.2), (0.5, 0.0, 0.74), (0.36, 0.0, 0.62),
                   (0.0, 0.012, 0.9), (0.5, 0.012, 0.97)], mat, mirror=False)


def tool_torch(mb, T, k):
    rod(mb, T, k, -0.16, 0.36, 0.02, "wood_dark", r1=0.03)
    blob(mb, T(0, 0, 0.44), (0.06 * k, 0.06 * k, 0.09 * k), "flame", count=10, seed=6)
    spike(mb, T(0, 0, 0.46), T(0.02, 0.0, 0.68), 0.07 * k, "flame_core")
    spike(mb, T(-0.03, 0.02, 0.44), T(-0.05, 0.03, 0.58), 0.045 * k, "flame")


def tool_bell(mb, T, k):
    rod(mb, T, k, -0.03, 0.07, 0.016, "wood_dark")
    mb.cylinder(T(0, 0, -0.03), T(0, 0, -0.2), 0.03 * k, 0.095 * k, "gold", segments=7)
    blob(mb, T(0, 0, -0.22), (0.022 * k, 0.022 * k, 0.022 * k), "metal_dark", count=8, seed=2)


def tool_mug(mb, T, k):
    mb.cylinder(T(0, 0.06, -0.06), T(0, 0.06, 0.1), 0.05 * k, 0.055 * k, "wood", segments=7)
    mb.cylinder(T(0, 0.06, 0.1), T(0, 0.06, 0.13), 0.056 * k, 0.05 * k, "white", segments=7)
    slab(mb, T, (-0.012, -0.02, -0.03), (0.012, 0.02, 0.07), "metal")


def tool_scales(mb, T, k):
    """Hangs below the hand that holds it up."""
    rod(mb, T, k, -0.1, 0.03, 0.008, "gold", sides=4)
    slab(mb, T, (-0.19, -0.008, -0.115), (0.19, 0.008, -0.095), "gold")
    for s in (-1, 1):
        mb.cylinder(T(s * 0.18, 0, -0.1), T(s * 0.18, 0, -0.27), 0.003 * k, 0.003 * k, "rope", segments=3)
        mb.cylinder(T(s * 0.18, 0, -0.27), T(s * 0.18, 0, -0.3), 0.075 * k, 0.045 * k, "gold", segments=7)
    blob(mb, T(0.18, 0, -0.255), (0.035 * k, 0.035 * k, 0.02 * k), "red", count=8, seed=3)


def tool_lantern(mb, T, k):
    rod(mb, T, k, -0.1, 0.03, 0.006, "metal_dark", sides=4)
    slab(mb, T, (-0.05, -0.05, -0.13), (0.05, 0.05, -0.1), "metal_dark")
    slab(mb, T, (-0.04, -0.04, -0.27), (0.04, 0.04, -0.13), "flame_core")
    slab(mb, T, (-0.05, -0.05, -0.3), (0.05, 0.05, -0.27), "metal_dark")
    for a in (-1, 1):
        for b in (-1, 1):
            rod(mb, T, k, -0.28, -0.12, 0.006, "metal_dark", a=a * 0.045, b=b * 0.045, sides=3)


def tool_book(mb, T, k, mat="red"):
    slab(mb, T, (-0.08, -0.03, -0.02), (0.08, 0.03, 0.2), mat)
    slab(mb, T, (-0.07, -0.022, -0.012), (0.085, 0.022, 0.19), "parchment")


def tool_scroll(mb, T, k):
    mb.cylinder(T(-0.12, 0.03, 0.26), T(0.12, 0.03, 0.26), 0.022 * k, 0.022 * k, "parchment", segments=6)
    slab(mb, T, (-0.11, 0.025, -0.02), (0.11, 0.035, 0.26), "parchment")
    mb.cylinder(T(-0.12, 0.03, -0.03), T(0.12, 0.03, -0.03), 0.018 * k, 0.018 * k, "parchment", segments=6)
    blob(mb, T(0.05, 0.045, 0.02), (0.022 * k, 0.012 * k, 0.022 * k), "red", count=8, seed=1)


def tool_quill(mb, T, k):
    spike(mb, T(0, 0, -0.05), T(0.0, 0.03, 0.22), 0.035 * k, "white", thickness=0.008 * k)


def tool_chest(mb, T, k):
    """A small strongbox carried by its handle (hangs below the hand)."""
    slab(mb, T, (-0.16, -0.1, -0.3), (0.16, 0.1, -0.12), "wood")
    slab(mb, T, (-0.165, -0.105, -0.16), (0.165, 0.105, -0.11), "wood_dark")
    for a in (-0.11, 0.11):
        slab(mb, T, (a - 0.015, -0.108, -0.305), (a + 0.015, 0.108, -0.105), "metal")
    slab(mb, T, (-0.025, 0.1, -0.2), (0.025, 0.115, -0.15), "gold")
    rod(mb, T, k, -0.11, 0.0, 0.008, "metal", sides=4)


def tool_basket(mb, T, k, fill="green"):
    """A handled basket hanging below the hand."""
    mb.cylinder(T(0, 0, -0.34), T(0, 0, -0.16), 0.11 * k, 0.15 * k, "straw", segments=8)
    blob(mb, T(0, 0, -0.15), (0.12 * k, 0.12 * k, 0.05 * k), fill, count=12, seed=7)
    tube(mb, [T(-0.14, 0, -0.16), T(-0.09, 0, -0.03), T(0, 0, 0.01), T(0.09, 0, -0.03), T(0.14, 0, -0.16)],
         [0.01 * k] * 5, "straw", sides=4)


def tool_bucket(mb, T, k):
    mb.cylinder(T(0, 0, -0.36), T(0, 0, -0.14), 0.09 * k, 0.12 * k, "wood", segments=8)
    mb.cylinder(T(0, 0, -0.16), T(0, 0, -0.145), 0.105 * k, 0.108 * k, "glass", segments=8)
    tube(mb, [T(-0.12, 0, -0.15), T(-0.08, 0, -0.03), T(0, 0, 0.0), T(0.08, 0, -0.03), T(0.12, 0, -0.15)],
         [0.007 * k] * 5, "metal_dark", sides=4)


def tool_holy_staff(mb, T, k):
    """A staff topped with a golden sun disc."""
    tool_staff(mb, T, k, 0.74, "white")
    mb.cylinder(T(0, -0.012, 0.86), T(0, 0.012, 0.86), 0.09 * k, 0.09 * k, "gold", segments=8)
    for i in range(8):
        a = i * math.tau / 8
        spike(mb, T(math.cos(a) * 0.085, 0, 0.86 + math.sin(a) * 0.085),
              T(math.cos(a) * 0.15, 0, 0.86 + math.sin(a) * 0.15), 0.04 * k, "gold", thickness=0.012 * k)


def tool_crystal_staff(mb, T, k, crystal="glass"):
    tool_staff(mb, T, k, 0.7, "wood_dark")
    mb.cylinder(T(0, 0, 0.7), T(0, 0, 0.8), 0.0, 0.06 * k, crystal, segments=5)
    mb.cylinder(T(0, 0, 0.8), T(0, 0, 0.98), 0.06 * k, 0.0, crystal, segments=5)
    for i in range(3):
        a = i * math.tau / 3
        spike(mb, T(math.cos(a) * 0.02, math.sin(a) * 0.02, 0.66), T(math.cos(a) * 0.08, math.sin(a) * 0.08, 0.8),
              0.03 * k, "wood_dark")


def tool_skull_staff(mb, T, k):
    tool_staff(mb, T, k, 0.72, "dark")
    blob(mb, T(0, 0.01, 0.8), (0.065 * k, 0.07 * k, 0.075 * k), "bone", count=12, seed=3)
    slab(mb, T, (-0.035, 0.02, 0.7), (0.035, 0.07, 0.75), "bone")
    for s in (-1, 1):
        blob(mb, T(s * 0.028, 0.065, 0.8), (0.016 * k, 0.012 * k, 0.018 * k), "eye", count=8, seed=2)
        spike(mb, T(s * 0.05, 0.0, 0.84), T(s * 0.13, -0.02, 0.98), 0.03 * k, "bone")


def tool_ladle(mb, T, k):
    rod(mb, T, k, -0.08, 0.3, 0.01, "metal_dark", sides=4)
    blob(mb, T(0, 0.03, 0.33), (0.045 * k, 0.045 * k, 0.03 * k), "metal", count=8, seed=2)


def tool_flower(mb, T, k):
    for i, (a, c) in enumerate(((-0.04, 0.2), (0.0, 0.25), (0.045, 0.19))):
        rod(mb, T, k, -0.05, c, 0.006, "green", a=a * 0.5, sides=3)
        blob(mb, T(a, 0, c + 0.02), (0.035 * k, 0.035 * k, 0.03 * k), ("red", "white", "gold")[i], count=8, seed=i)


def tool_hand_out(mb, T, k):
    """A begging bowl."""
    mb.cylinder(T(0, 0.05, -0.02), T(0, 0.05, 0.05), 0.04 * k, 0.07 * k, "wood_dark", segments=7)


TOOLS = {name[len("tool_"):]: fn for name, fn in list(globals().items()) if name.startswith("tool_") and callable(fn)
         and name != "tool_frame"}


def add_shield(spec, mb, kind):
    """A shield on the left forearm of any of the game's characters: round
    (wood with a painted center and a boss) or kite (painted, with a cross)."""
    k = spec.k
    part = spec.parts["forearm.L"]
    a, b = Vector(part[1]), Vector(part[2])
    c = a.lerp(b, 0.55) + Vector((max(part[3], part[4]) + 0.03 * k, 0, 0))
    if kind == "round":
        mb.cylinder(c, c + Vector((0.03 * k, 0, 0)), 0.3 * k, 0.28 * k, "wood", segments=10)
        mb.cylinder(c + Vector((0.028 * k, 0, 0)), c + Vector((0.036 * k, 0, 0)), 0.19 * k, 0.19 * k, "accent",
                    segments=10)
        blob(mb, c + Vector((0.04 * k, 0, 0)), (0.05 * k, 0.07 * k, 0.07 * k), "metal", count=10, seed=2)
    else:
        pts = []
        for y, z in ((-0.21, 0.3), (0.21, 0.3), (-0.22, 0.05), (0.22, 0.05), (0.0, -0.42), (0.0, 0.34)):
            pts += [c + Vector((0.0, y * k, z * k)), c + Vector((0.035 * k, y * 0.94 * k, z * 0.94 * k))]
        pts.append(c + Vector((0.07 * k, 0, 0.05 * k)))
        hull(mb, pts, "accent")
        mb.box(c + Vector((0.058 * k, 0, 0.08 * k)), (0.03 * k, 0.07 * k, 0.4 * k), "gold")
        mb.box(c + Vector((0.058 * k, 0, 0.14 * k)), (0.03 * k, 0.3 * k, 0.07 * k), "gold")


@contextlib.contextmanager
def held(spec, mb, bone):
    """The pieces added inside follow `bone`, whichever of the game's three
    ways of marking detail pieces the character uses (Folk.tag,
    Adventurer.mark or Figure.mark)."""
    if hasattr(spec, "tag"):
        spec.tag(mb, bone)
        yield
        spec.done(mb)
    elif hasattr(spec, "claim"):
        spec.mark(mb, bone)
        yield
        spec.mark(mb, None)
    else:
        spec.mark(mb, None)     # Closes what the character left unmarked.
        yield
        spec.mark(mb, bone)


# What the tools are made of, for characters that bring their own colors.
TOOL_COLORS = ("metal", "metal_dark", "wood", "wood_dark", "gold", "white", "accent", "belt", "straw", "rope",
               "flame", "flame_core", "red", "green", "glass", "parchment", "dark", "bone", "bread")


class Equipped:
    """Mixin that gives one of the game's own characters (art/blender/people)
    a tool in each hand, a shield, and the clips of TownClips. Set as class
    attributes: right, left, carry_r, carry_l, shield, clip_names."""

    far_tris = 0
    right = left = carry_r = carry_l = shield = None
    hunch = 0.0
    clip_names = (("idle", "idle"), ("walk", "walk"))

    def make_rig(self):
        return with_clips(super().make_rig())

    def details(self, mb):
        super().details(mb)
        for side, tool in (("R", self.right), ("L", self.left)):
            if tool:
                with held(self, mb, "hand." + side):
                    TOOLS[tool](mb, tool_frame(self, side), self.k)
        if self.shield:
            with held(self, mb, "lower_arm.L"):
                add_shield(self, mb, self.shield)


def race_variant(base, name, recolor=None, accent=0xB8382E, **attrs):
    """A function that builds `base` (a character class of the game) with
    other colors ({material: hex}; its light and shade tones follow), tools
    and clips (see Equipped)."""
    def make():
        colors = dict(base.colors)
        for mat, value in (recolor or {}).items():
            for key, tone in shaded({mat: value}).items():
                if key == mat or key in colors:
                    colors[key] = tone
        for key, tone in shaded({m: BASE[m] for m in TOOL_COLORS}).items():
            colors.setdefault(key, tone)
        colors.update(shaded({"accent": accent}))
        cls = type(name, (Equipped, base), dict(attrs, name=name, colors=colors))
        kit.build_zoo_spec(cls(), FAMILY)
    return make


# --------------------------------------------------------------- the human

DEFAULTS = dict(
    height=1.78, female=False, build=1.0, shoulder=None, head_size=0.92, belly=0.0,
    sleeves="long",        # long, short or none.
    legs="trousers",       # trousers or bare.
    boot=0.3,              # Height of the boots' rim (1.8 m body).
    gloves=None,           # Material of the hands, or None for skin.
    hair_style="short", beard=None, hat_style=None,
    skirt=None, skirt_mat="bottom",   # Hem height of a skirt or robe hanging from the belt.
    apron=False, tabard=False, armor=None, cape=None, collar=None, mask=False,
    right=None, left=None, carry_r=None, carry_l=None, shield=None, back=None, extras=(),
    hunch=0.0, colors=None,
    clips=(("idle", "idle"), ("walk", "walk")),
)


class Townsfolk(Folk):
    """A human of the town, described by options (see DEFAULTS)."""

    far_tris = 0        # Proposals have no far version.
    budget = 1000
    max_tris = 8000

    def __init__(self, name, **opts):
        o = dict(DEFAULTS)
        unknown = set(opts) - set(o)
        assert not unknown, "unknown options: %s" % ", ".join(sorted(unknown))
        o.update(opts)
        self.o = o
        self.name = name
        self.height = o["height"]
        self.female = o["female"]
        self.build = o["build"]
        self.head_size = o["head_size"]
        if o["shoulder"]:
            self.shoulder = o["shoulder"]
        self.jaw = 0.86 if o["female"] else 1.0
        self.BELT = 1.1
        self.HANG = 0.92 - o["skirt"] if o["skirt"] is not None else 0.42
        self.CAPE = {"long": 1.17, "short": 0.72}.get(o["cape"], 1.0)
        self.hunch = o["hunch"]
        self.carry_r = o["carry_r"]
        self.carry_l = o["carry_l"]
        self.clip_names = list(o["clips"])
        self.colors = shaded(dict(BASE, **(o["colors"] or {})))
        super().__init__()
        k = self.k
        self.level_cut(self.BELT, lambda c, n: 0.9 * k < c.z < 1.3 * k)
        self.level_cut(o["boot"], lambda c, n: c.z < 0.6 * k)
        for side in (".L", ".R"):
            if o["sleeves"] == "short":
                self.limb_cut("upper_arm" + side, 0.6)
            hand = self.parts["hand" + side]
            self.cuts.append(((0, 0, hand[1][2] + 0.035 * k), (0, 0, 1), self.near("hand" + side)))
        if o["tabard"]:
            for s in (-1, 1):
                self.cuts.append(((s * 0.105 * k, 0, 0), (1, 0, 0),
                                  lambda c, n: 1.0 * k < c.z < 1.5 * k and abs(c.x) < 0.2 * k))

    def make_rig(self):
        return TownRig(self, self.extra_bones(), self.part_bones())

    def extra_bones(self):
        if self.o["cape"]:
            return [Bone("cape", self.V(0, 0.125, 1.47), self.V(0, 0.16, 1.0), parent="chest")]
        return []

    def customize(self, parts):
        o = self.o
        self.small_head(parts)
        j = self.joints()
        for side, x in ((".L", 1), (".R", -1)):   # Fists.
            h = j["hand"]
            parts["hand" + side] = self.ellipsoid((h[0] * x, h[1], h[2] + 0.02), (0.04, 0.05, 0.052))
        belly = o["belly"]
        if belly:
            b = self.build
            parts["waist"] = self.ellipsoid((0, -0.03 * belly, 1.14),
                                            ((0.145 + 0.07 * belly) * b, (0.1 + 0.11 * belly) * b, 0.16))
            parts["hips"] = self.ellipsoid((0, 0.005 - 0.015 * belly, 0.97),
                                           ((0.165 + 0.04 * belly) * b, (0.115 + 0.05 * belly) * b, 0.13))

    def paint(self, c, n):
        k, zone, o = self.k, self.zone(c), self.o
        if zone in ("head", "jaw", "neck"):
            return "skin"
        if zone.startswith("hand"):
            return o["gloves"] or "skin"
        if zone.startswith("foot"):
            return "shoes"
        legs = "bottom" if o["legs"] == "trousers" else "skin"
        if zone.startswith("shin"):
            return "shoes" if c.z < o["boot"] * k else legs
        if zone.startswith("thigh"):
            return legs
        if zone.startswith("forearm"):
            return "top" if o["sleeves"] == "long" else "skin"
        if zone.startswith("upper_arm"):
            if o["sleeves"] == "none":
                return "skin"
            if o["sleeves"] == "short":
                part = self.parts[zone]
                a, b = Vector(part[1]), Vector(part[2])
                return "top" if (c - a).dot(b - a) / (b - a).dot(b - a) < 0.6 else "skin"
            return "top"
        if zone.startswith("shoulder") and o["sleeves"] == "none":
            return "skin"
        if c.z < self.BELT * k and not zone.startswith(("chest", "bust")):
            return o["skirt_mat"] if o["skirt"] is not None else "bottom"
        if o["tabard"] and abs(c.x) < 0.105 * k:
            return "accent"
        return "top"

    # ------------------------------------------------------------ details

    def details(self, mb):
        k, o, rig = self.k, self.o, self.rig
        self.begin(mb)
        self.head(mb)
        self.face(mb, brow="hair")
        if o["hair_style"]:
            getattr(self, "hair_" + o["hair_style"])(mb)
        if o["beard"]:
            self.beard(mb, o["beard"])
        if o["mask"]:
            self.mask(mb)
        if o["hat_style"]:
            getattr(self, "hat_" + o["hat_style"])(mb)
        if o["collar"]:
            self.tag(mb, "chest")
            collar(mb, (0.0, 0.005 * k), 1.44 * k, 1.56 * k, (0.175 * k, 0.15 * k), (0.12 * k, 0.118 * k), o["collar"],
                   drop=0.04 * k, lean=0.02 * k)
        self.tag(mb, "hips")
        at = belt(mb, self, self.BELT * k, 0.055 * k, "belt", pad=0.013 * k)
        buckle(mb, at, "metal", size=0.05 * k)
        self.at = at
        if o["skirt"] is not None:
            self.skirt_piece(mb, at)
        if o["tabard"]:
            self.tag(mb, rig.drape)
            for angle in (0, 180):
                panel(mb, at, angle, 0.2 * k, 0.34 * k, "accent", point=0.08 * k, flare=0.03 * k, thickness=0.016 * k,
                      dz=-0.02 * k)
        if o["apron"]:
            self.apron(mb, at)
        if o["armor"]:
            self.armor(mb, o["armor"])
        if o["cape"]:
            self.cape(mb)
        if o["shield"]:
            self.shield(mb, o["shield"])
        for item in ([o["back"]] if isinstance(o["back"], str) else list(o["back"] or [])) + list(o["extras"]):
            getattr(self, "item_" + item)(mb)
        for side, tool in (("R", o["right"]), ("L", o["left"])):
            if tool:
                with self.bound(mb, "hand." + side):
                    TOOLS[tool](mb, tool_frame(self, side), k)
        self.fingers(mb, o["gloves"] or "skin")
        self.tone(mb, ["top", "bottom", "metal", "hat"], 0.3)
        self.done(mb)

    # --------------------------------------------------------------- head

    def dome(self, mb, mat, scale=1.0, low=0.055, back=-0.06, crown=0.15):
        """A cap over the skull: hair, a coif, a helmet."""
        s = scale
        pts = [(0.0, -0.108 * s, low + 0.012), (0.075 * s, -0.098 * s, low), (0.104 * s, -0.035 * s, low - 0.012),
               (0.104 * s, 0.05 * s, low - 0.045), (0.072 * s, 0.124 * s, back), (0.0, 0.14 * s, back),
               (0.0, -0.035 * s, crown), (0.062 * s, 0.02 * s, crown - 0.016), (0.0, 0.085 * s, crown - 0.014),
               (0.085 * s, -0.04 * s, 0.105)]
        with self.bound(mb, "head"):
            return hull(mb, [self.hp(*p) for p in sym(pts)], mat)

    def hair_short(self, mb):
        self.dome(mb, "hair", 1.03)

    def hair_long(self, mb):
        self.dome(mb, "hair", 1.03)
        self.hair_hull(mb, "hair", [(0.1, 0.03, 0.03), (0.108, 0.06, -0.1), (0.1, 0.1, -0.25), (0.0, 0.145, -0.27),
                                    (0.0, 0.15, 0.0), (0.07, 0.135, 0.05), (0.09, 0.035, -0.19)])

    def hair_bun(self, mb):
        self.dome(mb, "hair", 1.03)
        with self.bound(mb, "head"):
            blob(mb, self.hp(0, 0.13, 0.1), tuple(r * self.head_size * self.k for r in (0.06, 0.06, 0.06)), "hair",
                 count=12, seed=4)

    def hair_ponytail(self, mb):
        u = self.head_size * self.k
        self.dome(mb, "hair", 1.03)
        with self.bound(mb, "head"):
            tube(mb, [self.hp(0, 0.12, 0.07), self.hp(0, 0.19, 0.02), self.hp(0, 0.2, -0.12), self.hp(0, 0.17, -0.27)],
                 [0.03 * u, 0.04 * u, 0.035 * u, 0.0], "hair", sides=5)

    def hair_balding(self, mb):
        self.hair_hull(mb, "hair", [(0.1, 0.02, 0.035), (0.1, 0.02, -0.03), (0.092, 0.09, -0.05), (0.0, 0.136, 0.05),
                                    (0.0, 0.13, -0.075), (0.075, 0.12, 0.05)])

    def hair_bald(self, mb):
        pass

    def beard(self, mb, style):
        tip = {"short": -0.165, "long": -0.31, "full": -0.23}[style]
        wide = 0.075 if style != "short" else 0.062
        self.hair_hull(mb, "hair", [(0.062, -0.086, -0.056), (0.0, -0.113, -0.06), (wide, -0.06, -0.12),
                                    (0.03, -0.09, tip + 0.03), (0.0, -0.1, tip), (0.075, -0.02, -0.07)])

    def mask(self, mb):
        """A cloth over the nose and mouth."""
        self.hair_hull(mb, "dark", [(0.078, -0.07, -0.02), (0.0, -0.118, -0.02), (0.06, -0.085, -0.125),
                                    (0.0, -0.105, -0.14), (0.085, -0.02, -0.03), (0.075, -0.01, -0.1)])

    def hat_straw(self, mb):
        u = self.head_size * self.k
        self.dome(mb, "straw", 1.08, low=0.06, crown=0.17)
        with self.bound(mb, "head"):
            mb.cylinder(self.hp(0, 0.01, 0.05), self.hp(0, 0.01, 0.095), 0.27 * u, 0.11 * u, "straw", segments=9)

    def hat_hood(self, mb, mat="hat"):
        self.hair_hull(mb, mat, [(0.098, -0.078, 0.1), (0.0, -0.088, 0.145), (0.112, -0.072, 0.0),
                                 (0.1, -0.066, -0.1), (0.0, -0.06, -0.145), (0.115, 0.06, 0.08), (0.0, 0.15, 0.1),
                                 (0.0, 0.21, 0.0), (0.1, 0.1, -0.12), (0.0, 0.13, -0.15), (0.0, 0.0, 0.158),
                                 (0.075, 0.0, 0.142)])
        k = self.k
        with self.bound(mb, "chest"):
            collar(mb, (0.0, 0.005 * k), 1.43 * k, 1.56 * k, (0.2 * k, 0.16 * k), (0.12 * k, 0.118 * k), mat,
                   drop=0.05 * k, lean=0.02 * k)

    def hat_cap(self, mb, mat="hat"):
        self.dome(mb, mat, 1.07, low=0.062, crown=0.16)

    def hat_coif(self, mb):
        """A white linen cap tied under the chin."""
        self.dome(mb, "white", 1.06, low=0.06, back=-0.1)

    def hat_scarf(self, mb):
        """A headscarf knotted behind."""
        u = self.head_size * self.k
        self.dome(mb, "hat", 1.07, low=0.058, back=-0.09)
        with self.bound(mb, "head"):
            spike(mb, self.hp(0, 0.13, -0.05), self.hp(0.02, 0.17, -0.22), 0.1 * u, "hat", thickness=0.03 * u)

    def hat_feather(self, mb):
        """A cap with a peak in front and a feather."""
        u = self.head_size * self.k
        self.dome(mb, "hat", 1.07, low=0.06, crown=0.165)
        with self.bound(mb, "head"):
            spike(mb, self.hp(0, -0.09, 0.08), self.hp(0, -0.24, 0.06), 0.17 * u, "hat", thickness=0.035 * u)
            spike(mb, self.hp(0.08, 0.0, 0.1), self.hp(0.13, 0.16, 0.3), 0.05 * u, "accent", thickness=0.012 * u)

    def hat_kettle(self, mb):
        u = self.head_size * self.k
        self.dome(mb, "metal", 1.1, low=0.055, crown=0.165)
        with self.bound(mb, "head"):
            mb.cylinder(self.hp(0, 0.01, 0.04), self.hp(0, 0.01, 0.075), 0.19 * u, 0.12 * u, "metal_dark", segments=8)

    def hat_helm(self, mb, plume=None):
        u = self.head_size * self.k
        self.dome(mb, "metal", 1.1, low=0.045, back=-0.09, crown=0.165)
        with self.bound(mb, "head"):
            hull(mb, [self.hp(*p) for p in ((-0.014, -0.118, 0.07), (0.014, -0.118, 0.07), (-0.012, -0.122, -0.04),
                                           (0.012, -0.122, -0.04), (0.0, -0.105, 0.0))], "metal_dark")
            for s in (-1, 1):
                hull(mb, [self.hp(s * x, y, z) for x, y, z in ((0.1, -0.06, 0.04), (0.105, 0.03, 0.03),
                                                               (0.09, -0.075, -0.09), (0.098, 0.0, -0.1),
                                                               (0.085, -0.04, -0.03))], "metal")
            if plume:
                tube(mb, [self.hp(0, -0.06, 0.16), self.hp(0, 0.0, 0.25), self.hp(0, 0.12, 0.24),
                          self.hp(0, 0.22, 0.1), self.hp(0, 0.25, -0.04)],
                     [0.02 * u, 0.045 * u, 0.055 * u, 0.045 * u, 0.0], plume, sides=5, flat=0.5)

    def hat_plume(self, mb):
        self.hat_helm(mb, plume="accent")

    def hat_mitre(self, mb):
        self.hair_hull(mb, "white", [(0.095, 0.0, 0.06), (0.0, -0.105, 0.065), (0.0, 0.12, 0.05), (0.08, 0.0, 0.24),
                                     (0.0, -0.05, 0.25), (0.0, 0.06, 0.25), (0.0, 0.0, 0.37)])
        self.hair_hull(mb, "gold", [(0.1, 0.0, 0.055), (0.0, -0.11, 0.06), (0.0, 0.125, 0.045), (0.1, 0.0, 0.09),
                                    (0.0, -0.11, 0.095), (0.0, 0.125, 0.08), (0.075, -0.08, 0.075),
                                    (0.075, 0.09, 0.065)])

    def hat_crown(self, mb):
        u = self.head_size * self.k
        with self.bound(mb, "head"):
            mb.cylinder(self.hp(0, 0.01, 0.075), self.hp(0, 0.01, 0.125), 0.108 * u, 0.112 * u, "gold", segments=8)
            for i in range(8):
                a = i * math.tau / 8
                p = Vector((math.sin(a) * 0.105, 0.01 - math.cos(a) * 0.105, 0.0))
                spike(mb, self.hp(p.x, p.y, 0.12), self.hp(p.x * 1.08, p.y * 1.08, 0.19), 0.05 * u, "gold",
                      thickness=0.02 * u)
            blob(mb, self.hp(0, -0.1, 0.105), (0.018 * u, 0.012 * u, 0.018 * u), "red", count=8, seed=1)

    def hat_wizard(self, mb):
        u = self.head_size * self.k
        with self.bound(mb, "head"):
            mb.cylinder(self.hp(0, 0.01, 0.055), self.hp(0, 0.01, 0.085), 0.23 * u, 0.12 * u, "hat", segments=9)
            tube(mb, [self.hp(0, 0.01, 0.075), self.hp(0, 0.02, 0.2), self.hp(0, 0.06, 0.33), self.hp(0, 0.14, 0.4)],
                 [0.115 * u, 0.085 * u, 0.045 * u, 0.0], "hat", sides=7)
            mb.cylinder(self.hp(0, 0.01, 0.085), self.hp(0, 0.012, 0.115), 0.118 * u, 0.11 * u, "gold", segments=7)

    def hat_toque(self, mb):
        u = self.head_size * self.k
        with self.bound(mb, "head"):
            mb.cylinder(self.hp(0, 0.01, 0.055), self.hp(0, 0.01, 0.14), 0.108 * u, 0.112 * u, "white", segments=8)
            blob(mb, self.hp(0, 0.01, 0.19), (0.15 * u, 0.15 * u, 0.075 * u), "white", count=16, seed=5)

    def hat_bandana(self, mb):
        u = self.head_size * self.k
        self.dome(mb, "accent", 1.06, low=0.06, back=-0.03)
        with self.bound(mb, "head"):
            spike(mb, self.hp(0.03, 0.13, 0.03), self.hp(0.1, 0.2, -0.12), 0.06 * u, "accent", thickness=0.02 * u)

    def hat_circlet(self, mb):
        u = self.head_size * self.k
        with self.bound(mb, "head"):
            mb.cylinder(self.hp(0, 0.012, 0.062), self.hp(0, 0.012, 0.085), 0.112 * u, 0.112 * u, "gold", segments=8)
            blob(mb, self.hp(0, -0.102, 0.075), (0.018 * u, 0.012 * u, 0.02 * u), "glass", count=8, seed=1)

    def hat_veil(self, mb):
        """A bride's veil: a white cloth falling behind, with a flower crown."""
        self.hat_circlet(mb)
        self.hair_hull(mb, "white", [(0.1, 0.02, 0.1), (0.0, 0.0, 0.15), (0.14, 0.12, -0.2), (0.0, 0.2, -0.3),
                                     (0.0, 0.15, 0.08), (0.12, 0.1, -0.5), (0.0, 0.2, -0.55)])

    # ------------------------------------------------------------ clothes

    def skirt_piece(self, mb, at):
        k, o = self.k, self.o
        hem = o["skirt"]
        self.tag(mb, self.rig.drape)
        angles = (0, 40, 85, 132, 180, 228, 275, 320)
        top = [at(a, dz=-0.02 * k) for a in angles]
        hips = hip_ring(self, angles, 0.95 * k, 0.024 * k)
        flare = 1.2 + 0.5 * (0.92 - hem)
        low = [Vector((p.x * (flare + (0.05 if i % 2 else 0.0)), p.y * (flare + (0.05 if i % 2 else 0.0)) - 0.01 * k,
                       hem * k)) for i, p in enumerate(hips)]
        skirt(mb, [top, hips, low], o["skirt_mat"], inner="dark", thickness=0.012 * k, closed=True)

    def chest_point(self, x, z, off=0.012):
        k = self.k
        p = land(self, (x * k, -1.0, z * k), (0, 1, 0))
        return (p if p is not None else self.V(x, -0.1, z)) + Vector((0, -off * k, 0))

    def apron(self, mb, at):
        k = self.k
        self.tag(mb, self.rig.torso)
        # The bib: flat, as far forward as the chest's most forward point.
        probes = [self.chest_point(x, z) for x in (-0.07, 0.0, 0.07) for z in (1.3, 1.34, 1.4)]
        y = min(p.y for p in probes) - 0.004 * k
        low = [self.chest_point(0.115, 1.13), self.chest_point(-0.115, 1.13)]
        studies.plate(mb, [Vector((-0.085 * k, y, 1.42 * k)), Vector((0.085 * k, y, 1.42 * k)), low[0], low[1]],
                      0.014 * k, "apron")
        for s in (-1, 1):   # Its straps over the shoulders.
            studies.plate(mb, [Vector((s * 0.085 * k, y, 1.42 * k)), Vector((s * 0.06 * k, y, 1.42 * k)),
                               self.V(s * 0.07, -0.02, 1.535), self.V(s * 0.095, -0.02, 1.53)], 0.012 * k, "apron")
        self.tag(mb, self.rig.drape)
        long = self.o["skirt"] is not None
        panel(mb, at, 0, 0.3 * k, (0.5 if long else 0.42) * k, "apron", flare=(0.07 if long else -0.012) * k,
              thickness=0.016 * k, dz=0.02 * k, lift=0.006 * k, taper=1.15)

    def armor(self, mb, kind):
        """breastplate: a steel cuirass; +pauldrons: with shoulder plates;
        leather: a leather jerkin's hard chest piece."""
        k, V, rig = self.k, self.V, self.rig
        mat = "belt" if kind == "leather" else "metal"
        sx = self.shoulder / 0.2
        self.tag(mb, rig.torso)
        hull(mb, [V(*p) for p in sym([
            (0.11 * sx, -0.105, 1.43), (0.0, -0.135, 1.44), (0.175 * sx, -0.03, 1.37), (0.0, -0.17, 1.31),
            (0.15 * sx, -0.09, 1.2), (0.0, -0.15, 1.165), (0.135 * sx, -0.08, 1.165), (0.12 * sx, 0.105, 1.42),
            (0.17 * sx, 0.04, 1.37), (0.14 * sx, 0.095, 1.185), (0.0, 0.13, 1.32), (0.0, 0.116, 1.175)])], mat)
        if kind == "pauldrons":
            for s in (-1, 1):
                self.tag(mb, rig.shoulder("L" if s > 0 else "R"))
                sh = self.J("shoulder", s) + Vector((s * 0.005, 0.0, 0.02)) * k
                hull(mb, [sh + Vector((s * x, y, z)) * k for x, y, z in (
                    (-0.07, 0.07, 0.08), (-0.07, -0.07, 0.08), (0.0, 0.0, 0.115), (0.07, 0.11, 0.02), (0.07, -0.11, 0.02),
                    (0.13, 0.09, -0.07), (0.13, -0.09, -0.07), (0.15, 0.0, -0.04))], "metal_dark")

    def cape(self, mb):
        k, V = self.k, self.V
        short = self.o["cape"] == "short"
        self.tag(mb, self.rig.cape)
        levels = ((1.47, 0.16, 0.125), (1.25, 0.21, 0.14), (1.0, 0.25, 0.16), (0.78, 0.28, 0.17)) if short else \
            ((1.47, 0.17, 0.125), (1.1, 0.26, 0.15), (0.7, 0.32, 0.18), (0.3, 0.36, 0.2))
        rows = []
        for z, half, y in levels:
            row = []
            for i in range(7):
                x = (i / 3.0 - 1.0) * half
                fold = 0.05 if i % 2 else 0.0
                wrap = -0.05 * abs(i / 3.0 - 1.0) ** 2
                row.append(V(x, y + fold * (1.5 - z) + wrap, z))
            rows.append(row)
        sheet(mb, rows, 0.014 * k, "cape")

    def shield(self, mb, kind):
        self.tag(mb, "lower_arm.L")
        add_shield(self, mb, kind)

    # -------------------------------------------------- back and belt items

    def item_load(self, mb):
        """A carrier's frame on the back with a crate, a sack and a roll."""
        k, V = self.k, self.V
        self.tag(mb, "chest")
        for x in (-0.15, 0.15):
            mb.cylinder(V(x, 0.15, 0.95), V(x, 0.17, 1.72), 0.016 * k, 0.016 * k, "wood_dark", segments=4)
        mb.box(V(0, 0.3, 1.02), (0.36 * k, 0.26 * k, 0.03 * k), "wood_dark")
        mb.box(V(0, 0.31, 1.2), (0.4 * k, 0.3 * k, 0.32 * k), "wood")
        for x in (-0.14, 0.14):
            mb.box(V(x, 0.31, 1.2), (0.03 * k, 0.31 * k, 0.33 * k), "wood_dark")
        blob(mb, V(0, 0.3, 1.52), (0.2 * k, 0.16 * k, 0.17 * k), "rope", count=16, seed=9)
        mb.cylinder(V(-0.24, 0.29, 1.74), V(0.24, 0.29, 1.74), 0.07 * k, 0.07 * k, "accent", segments=7)
        for s in (-1, 1):   # Straps over the shoulders.
            studies.plate(mb, [V(s * 0.1, -0.11, 1.44), V(s * 0.14, -0.11, 1.44), V(s * 0.15, 0.13, 1.5),
                               V(s * 0.11, 0.13, 1.5)], 0.02 * k, "belt")

    def item_quiver(self, mb):
        k, V = self.k, self.V
        self.tag(mb, "chest")
        a, b = V(-0.12, 0.16, 1.1), V(0.12, 0.17, 1.58)
        mb.cylinder(a, b, 0.05 * k, 0.06 * k, "belt", segments=6)
        d = (b - a).normalized()
        for i, off in enumerate(((0.02, 0, 0), (-0.02, 0.01, 0), (0, -0.015, 0.01))):
            p = b + Vector(off) * k
            mb.cylinder(p, p + d * 0.16 * k, 0.006 * k, 0.006 * k, "wood", segments=3)
            spike(mb, p + d * 0.1 * k, p + d * 0.2 * k, 0.04 * k, ("white", "accent", "white")[i], thickness=0.008 * k)

    def item_pack(self, mb):
        k, V = self.k, self.V
        self.tag(mb, "chest")
        mb.box(V(0, 0.2, 1.3), (0.3 * k, 0.16 * k, 0.34 * k), "belt")
        mb.box(V(0, 0.21, 1.45), (0.32 * k, 0.18 * k, 0.1 * k), "wood_dark")
        mb.cylinder(V(-0.17, 0.2, 1.52), V(0.17, 0.2, 1.52), 0.055 * k, 0.055 * k, "accent", segments=6)

    def item_basket_back(self, mb):
        k, V = self.k, self.V
        self.tag(mb, "chest")
        mb.cylinder(V(0, 0.24, 1.02), V(0, 0.26, 1.5), 0.12 * k, 0.17 * k, "straw", segments=8)
        blob(mb, V(0, 0.26, 1.5), (0.15 * k, 0.15 * k, 0.07 * k), "green", count=14, seed=5)

    def item_sack(self, mb):
        """A sack over the left shoulder."""
        k, V = self.k, self.V
        self.tag(mb, "chest")
        blob(mb, V(0.13, 0.2, 1.42), (0.2 * k, 0.2 * k, 0.27 * k), "apron", count=18, seed=6)
        blob(mb, V(0.15, 0.02, 1.6), (0.06 * k, 0.09 * k, 0.06 * k), "apron", count=8, seed=3)

    def item_fish(self, mb):
        """Two fish hanging from the belt."""
        k = self.k
        self.tag(mb, "hips")
        p = self.at(-70)
        for i, dx in enumerate((0.0, 0.05)):
            c = p + Vector((-0.02 * k, dx * k, -0.16 * k))
            blob(mb, c, (0.025 * k, 0.04 * k, 0.11 * k), "metal", count=10, seed=i)
            spike(mb, c + Vector((0, 0, -0.1 * k)), c + Vector((0, 0, -0.17 * k)), 0.06 * k, "metal_dark",
                  thickness=0.01 * k)

    def item_purse(self, mb):
        k = self.k
        self.tag(mb, "hips")
        p = self.at(60)
        blob(mb, p + Vector((0.02 * k, 0, -0.09 * k)), (0.05 * k, 0.045 * k, 0.065 * k), "gold", count=10, seed=2)

    def item_keys(self, mb):
        k = self.k
        self.tag(mb, "hips")
        p = self.at(-60)
        for i in range(3):
            mb.box(p + Vector(((-0.02 - 0.012 * i) * k, 0.012 * i * k, (-0.08 - 0.02 * i) * k)),
                   (0.012 * k, 0.012 * k, 0.09 * k), "metal")

    def item_pouch(self, mb):
        k = self.k
        self.tag(mb, "hips")
        p = self.at(-55)
        mb.box(p + Vector((-0.02 * k, -0.01 * k, -0.07 * k)), (0.09 * k, 0.05 * k, 0.1 * k), "belt")

    def item_scabbard(self, mb):
        """A sword hanging at the left hip."""
        k = self.k
        self.tag(mb, "hips")
        p = self.at(80) + Vector((0.01 * k, 0, 0))
        mb.cylinder(p + Vector((0, -0.05 * k, 0.0)), p + Vector((0.03 * k, 0.3 * k, -0.52 * k)), 0.025 * k, 0.015 * k,
                    "belt", segments=5)
        mb.cylinder(p + Vector((0, -0.05 * k, 0.0)), p + Vector((-0.01 * k, -0.13 * k, 0.12 * k)), 0.016 * k, 0.016 * k,
                    "dark", segments=5)
        mb.box(p + Vector((0, -0.055 * k, 0.01 * k)), (0.03 * k, 0.03 * k, 0.14 * k), "gold")

    def item_lute(self, mb):
        """A lute hanging on the chest from a strap."""
        k, V = self.k, self.V
        self.tag(mb, "chest")
        blob(mb, V(-0.08, -0.2, 1.16), (0.15 * k, 0.07 * k, 0.19 * k), "wood", count=18, seed=8)
        mb.cylinder(V(-0.08, -0.265, 1.16), V(-0.08, -0.275, 1.16), 0.0, 0.045 * k, "dark", segments=7)
        mb.cylinder(V(0.0, -0.21, 1.24), V(0.33, -0.2, 1.4), 0.022 * k, 0.018 * k, "wood_dark", segments=5)
        mb.box(V(0.36, -0.19, 1.41), (0.09 * k, 0.03 * k, 0.05 * k), "wood_dark", rotation_z=0.0)
        studies.plate(mb, [V(0.1, -0.11, 1.46), V(0.14, -0.11, 1.46), V(-0.1, -0.13, 1.25), V(-0.14, -0.13, 1.27)],
                      0.014 * k, "belt")

    def item_bedroll(self, mb):
        k, V = self.k, self.V
        self.tag(mb, "chest")
        mb.cylinder(V(-0.2, 0.17, 1.2), V(0.2, 0.17, 1.2), 0.07 * k, 0.07 * k, "accent", segments=7)

    def item_medal(self, mb):
        """A chain of office on the chest."""
        k = self.k
        self.tag(mb, "chest")
        for x in (-0.07, 0.07):
            studies.plate(mb, [self.chest_point(x * 1.5, 1.44), self.chest_point(x * 1.5 + 0.02, 1.44),
                               self.chest_point(0.012, 1.3), self.chest_point(-0.012, 1.3)], 0.012 * k, "gold")
        blob(mb, self.chest_point(0, 1.28, 0.02), (0.035 * k, 0.014 * k, 0.035 * k), "gold", count=8, seed=2)

    def item_satchel(self, mb):
        """A messenger's bag at the right hip, on a strap across the chest."""
        k, V = self.k, self.V
        self.tag(mb, "hips")
        p = self.at(-80)
        mb.box(p + Vector((-0.04 * k, 0, -0.1 * k)), (0.08 * k, 0.24 * k, 0.2 * k), "belt")
        mb.box(p + Vector((-0.045 * k, 0, -0.04 * k)), (0.09 * k, 0.25 * k, 0.09 * k), "wood_dark")
        self.tag(mb, self.rig.torso)
        studies.plate(mb, [self.chest_point(0.13, 1.44), self.chest_point(0.17, 1.42), self.chest_point(-0.12, 1.12),
                           self.chest_point(-0.16, 1.14)], 0.014 * k, "belt")


def person(name, **opts):
    """A function that builds and saves the Townsfolk described by opts."""
    def make():
        kit.build_zoo_spec(Townsfolk(name, **opts), FAMILY)
    return make
