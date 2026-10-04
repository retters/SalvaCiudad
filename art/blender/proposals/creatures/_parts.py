"""Shared pieces of the `creatures` proposal family.

Two kinds of creature are built here:

- organic ones, with the zoo technique (a studies.Spec welded by remesh);
  see quad.py for the four-legged generator;
- rigid or segmented ones (skeletons, golems, spiders, chests): faceted
  pieces, each bound whole to one bone of a kit.Mech, animated by turning
  and moving bones. The helpers below build those pieces and turn poses
  worked out with rigs.Pose (two-bone inverse kinematics) or given in world
  space into what kit.Mech.clip() expects.
"""

import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROPOSALS = os.path.dirname(HERE)
sys.path.insert(0, PROPOSALS)

import _kit as kit  # noqa: E402  (adds art/blender to the path)

sys.path.insert(0, os.path.join(os.path.dirname(PROPOSALS), "zoo"))

import bmesh  # noqa: E402
from mathutils import Quaternion, Vector  # noqa: E402

import common  # noqa: E402
import rigs  # noqa: E402
import studies  # noqa: E402
from rigs import FPS, Pose, X, Y, Z, smooth  # noqa: E402,F401

FAMILY = "creatures"
SIDES = (("L", 1.0), ("R", -1.0))


# ------------------------------------------------------------------ colors

def _mix(hex_color, other, t):
    out = 0
    for shift in (16, 8, 0):
        a, b = (hex_color >> shift) & 255, (other >> shift) & 255
        out |= int(round(a + (b - a) * t)) << shift
    return out


def shades(name, hex_color, light=0.14, dark=0.14):
    """A material with its lighter and darker facet tones."""
    return {name: common.rgb(hex_color),
            name + "_light": common.rgb(_mix(hex_color, 0xFFFFFF, light)),
            name + "_shade": common.rgb(_mix(hex_color, 0x000000, dark))}


def palette(**colors):
    return {name: common.rgb(value) for name, value in colors.items()}


# ------------------------------------------------------------ rigid pieces

def _w(bone):
    return {bone: 1.0} if bone else None


def hull(mb, points, mat, bone=None):
    """The convex hull of the points: a faceted solid piece."""
    tmp = bmesh.new()
    verts = [tmp.verts.new(Vector(p)) for p in points]
    res = bmesh.ops.convex_hull(tmp, input=verts)
    inner = [v for v in res["geom_interior"] if isinstance(v, bmesh.types.BMVert)]
    if inner:
        bmesh.ops.delete(tmp, geom=inner, context="VERTS")
    mapping = {v: mb.bm.verts.new(v.co) for v in tmp.verts}
    for f in tmp.faces:
        mb.bm.faces.new([mapping[v] for v in f.verts])
    tmp.free()
    return mb._finish(list(mapping.values()), mat, _w(bone))


def rock(mb, center, radii, mat, bone=None, count=14, seed=1, jitter=0.1):
    """A faceted lump: the hull of points scattered on an ellipsoid."""
    rnd = random.Random(seed)
    golden = math.pi * (3 - math.sqrt(5))
    pts = []
    for i in range(count):
        z = 1 - 2 * (i + 0.5) / count
        s = math.sqrt(1 - z * z)
        a = i * golden + rnd.uniform(-0.3, 0.3)
        k = 1.0 + rnd.uniform(-jitter, jitter)
        pts.append((center[0] + s * math.cos(a) * radii[0] * k, center[1] + s * math.sin(a) * radii[1] * k,
                    center[2] + z * radii[2] * k))
    return hull(mb, pts, mat, bone)


def bar(mb, a, b, width, depth, mat, bone=None, side=(1, 0, 0), taper=1.0):
    """A box from a to b, `width` across `side` and `depth` the other way;
    `taper` scales its section at b."""
    a, b = Vector(a), Vector(b)
    axis = (b - a).normalized()
    u = Vector(side) - axis * Vector(side).dot(axis)
    u = u.normalized() if u.length > 1e-6 else axis.orthogonal().normalized()
    v = axis.cross(u)
    pts = []
    for p, k in ((a, 1.0), (b, taper)):
        for su in (-1, 1):
            for sv in (-1, 1):
                pts.append(p + u * (su * width * 0.5 * k) + v * (sv * depth * 0.5 * k))
    return hull(mb, pts, mat, bone)


def seg(mb, a, b, ra, rb, mat, bone=None, sides=6):
    """A tapered faceted limb from a to b."""
    return mb.cylinder(a, b, ra, rb, mat, weights=_w(bone), segments=sides)


def spike(mb, base, tip, radius, mat, bone=None, sides=4):
    return mb.cylinder(base, tip, radius, 0.0, mat, weights=_w(bone), segments=sides)


def box(mb, center, size, mat, bone=None, rotation_z=0.0):
    return mb.box(center, size, mat, weights=_w(bone), rotation_z=rotation_z)


def ball(mb, center, radius, mat, bone=None, segments=6, rings=4, scale=(1, 1, 1)):
    return mb.sphere(center, radius, mat, weights=_w(bone), segments=segments, rings=rings, scale=scale)


def plate(mb, points, thickness, mat, bone=None):
    """A thin flat piece (a wing membrane, a fin, a rag) with volume."""
    verts = studies.plate(mb, points, thickness, mat)
    if bone:
        g = mb._group_index(bone)
        for v in verts:
            v[mb.deform][g] = 1.0
    return verts


def weigh(mb, verts, weights):
    """Sets the weights {bone: weight} of some vertices."""
    for v in verts:
        for bone, w in weights.items():
            v[mb.deform][mb._group_index(bone)] = w


# ------------------------------------------------------------------- poses

def aa(q):
    """A quaternion as the list of (axis, degrees) that kit.Mech keys."""
    q = Quaternion(q)
    if abs(q.angle) < 1e-7:
        return []
    return [(tuple(q.axis), math.degrees(q.angle))]


def from_pose(pose, moves=None):
    """A rigs.Pose as (turns, moves) for kit.Mech.clip(); the pose's offset
    moves the root bone, and `moves` adds more bone moves."""
    out = {"root": tuple(pose.offset)}
    out.update(moves or {})
    return {name: aa(q) for name, q in pose.q.items()}, out


def world_pose(mech, turn=None, place=None):
    """(turns, moves) from world-space data: `turn` maps a bone to its turn
    from rest in armature space, `place` to where its head is. A bone not
    named follows its parent rigidly. For pieces that fly apart."""
    turn, place = turn or {}, place or {}
    turns, moves, wq, wp = {}, {}, {}, {}
    for b in mech.bones:   # Parents first.
        if b.parent is None:
            pq, natural = Quaternion(), b.head.copy()
        else:
            parent = mech.by_name[b.parent]
            pq = wq[b.parent]
            natural = wp[b.parent] + pq @ (b.head - parent.head)
        q = Quaternion(turn[b.name]) if b.name in turn else pq.copy()
        at = Vector(place[b.name]) if b.name in place else natural
        wq[b.name], wp[b.name] = q, at
        local = pq.inverted() @ q
        if abs(local.angle) > 1e-7:
            turns[b.name] = aa(local)
        move = pq.inverted() @ (at - natural)
        if move.length > 1e-9:
            moves[b.name] = tuple(move)
    return turns, moves


def piece_info(mb):
    """{bone: (center, half sizes sorted)} of the vertices bound to each
    bone, read from the builder before it is saved; for collapse()."""
    groups = {}
    for v in mb.bm.verts:
        for g, w in v[mb.deform].items():
            if w > 0.5:
                groups.setdefault(mb.groups[g], []).append(v.co.copy())
    info = {}
    for bone, pts in groups.items():
        lo = Vector([min(p[i] for p in pts) for i in range(3)])
        hi = Vector([max(p[i] for p in pts) for i in range(3)])
        info[bone] = ((lo + hi) * 0.5, sorted((hi - lo) * 0.5))
    return info


def collapse(mech, t, info, spread=0.35, seed=3, start=0.08, fall=0.5, keep=(), rest=0.8):
    """A die clip for a creature made of loose hard parts: every piece
    drops to the ground, tumbling, and ends lying near where it stood, the
    lowest ones first. `info` is piece_info() of the model; the bones in
    `keep` stay with their parent."""
    rnd = random.Random(seed)
    top = max(c.z for c, _ in info.values()) or 1.0
    turn, place = {}, {}
    for b in mech.bones:
        if b.name == "root" or b.name in keep or b.name not in info:
            continue
        center, half = info[b.name]
        yaw = rnd.uniform(0, math.tau)
        tip = Vector((math.cos(yaw), math.sin(yaw), 0.0))
        target = Quaternion(Z, rnd.uniform(-1.0, 1.0)) @ Quaternion(tip, rnd.uniform(1.1, 2.0))
        out = Vector((center.x, center.y, 0.0))
        out = out.normalized() if out.length > 1e-3 else tip
        r = spread * rnd.uniform(0.2, 1.0)
        end = Vector((center.x + out.x * r + rnd.uniform(-0.3, 0.3) * spread,
                      center.y + out.y * r + rnd.uniform(-0.3, 0.3) * spread, max(0.02, half[1] * rest)))
        t0 = start + (1.0 - fall - start) * (center.z / top) * 0.6
        u = max(0.0, min(1.0, (t - t0) / fall))
        now = Vector((center.x + (end.x - center.x) * u, center.y + (end.y - center.y) * u,
                      center.z + (end.z - center.z) * u * u))       # Falls faster and faster.
        q = Quaternion().slerp(target, smooth(u))
        turn[b.name] = q
        place[b.name] = now - q @ (center - b.head)
    return world_pose(mech, turn, place)


def pulse(t, a, b, c=None, d=None):
    """0 before a, rises to 1 at b, holds to c and falls back to 0 at d."""
    c = b if c is None else c
    d = c if d is None else d
    up = smooth((t - a) / max(b - a, 1e-6))
    down = 1.0 - smooth((t - c) / max(d - c, 1e-6)) if d > c else (1.0 if t <= c else 0.0)
    return up * down


def step(t, phase, duty, stride, lift):
    """A foot's path in a walk cycle: (dy, dz, swing) with dy from -stride/2
    (front) to +stride/2 (back) while planted, then lifted forward in an arc;
    `swing` is 0 while planted and 0..1 along the swing."""
    psi = (t + phase) % 1.0
    if psi < duty:
        return -stride / 2 + stride * psi / duty, 0.0, 0.0
    u = (psi - duty) / (1 - duty)
    return stride / 2 - stride * smooth(u), lift * math.sin(math.pi * u), u


def save(mb, name, colors, mech, k=1.0):
    """Saves a rigid creature, optionally at another size: the same model
    and clips scaled by k (a spiderling, a hatchling, a king). The poses
    are worked out at the original size, where the clips' numbers are;
    only what is exported is scaled: the mesh, the bones, the bone moves
    and the saved speeds."""
    if k == 1.0:
        return kit.save(mb, FAMILY, name, colors, mech=mech)
    for v in mb.bm.verts:
        v.co *= k
    out = kit.Mech([(b.name, tuple(b.head * k), tuple(b.tail * k), None if b.parent == "root" else b.parent)
                    for b in mech.bones if b.name != "root"])

    def wrap(pose):
        def scaled(t):
            posed = pose(t)
            turns, moves = posed if isinstance(posed, tuple) else (posed, {})
            return turns, {bone: tuple(c * k for c in move) for bone, move in moves.items()}
        return scaled

    for clip, frames, loops, pose, speed in mech.clips():
        out._clips.append((clip, frames, loops, wrap(pose), None if speed is None else speed * k))
    return kit.save(mb, FAMILY, name, colors, mech=out)


# ------------------------------------------------------------------ bipeds

class Biped(kit.Mech):
    """A two-legged skeleton of rigid parts with the villagers' bone names
    (hips, chest, head, upper_arm, lower_arm, hand, thigh, shin, foot; ".L"
    is +X). `pts` gives the left side's joints: waist_z, neck_z, top_z and
    the points shoulder, elbow, wrist, hand, hip, knee, ankle, toe."""

    def __init__(self, pts, extra=()):
        self.pts = pts
        hip_z = pts["hip"][2]
        bones = [("hips", (0, 0, hip_z), (0, 0, pts["waist_z"]), None),
                 ("chest", (0, 0, pts["waist_z"]), (0, 0, pts["neck_z"]), "hips"),
                 ("head", (0, 0, pts["neck_z"]), (0, 0, pts["top_z"]), "chest")]
        for side, sx in SIDES:
            def m(name, sx=sx):
                p = pts[name]
                return (p[0] * sx, p[1], p[2])
            bones += [(f"upper_arm.{side}", m("shoulder"), m("elbow"), "chest"),
                      (f"lower_arm.{side}", m("elbow"), m("wrist"), f"upper_arm.{side}"),
                      (f"hand.{side}", m("wrist"), m("hand"), f"lower_arm.{side}"),
                      (f"thigh.{side}", m("hip"), m("knee"), "hips"),
                      (f"shin.{side}", m("knee"), m("ankle"), f"thigh.{side}"),
                      (f"foot.{side}", m("ankle"), m("toe"), f"shin.{side}")]
        super().__init__(bones + list(extra))
        self.ankle = {s: self.by_name[f"foot.{s}"].head.copy() for s, _ in SIDES}
        hip, knee, ankle = (Vector(pts[n]) for n in ("hip", "knee", "ankle"))
        self.leg = (knee - hip).length + (ankle - knee).length
        self.hip_height = hip.z - ankle.z

    def stride(self, crouch, reach=0.97):
        height = self.hip_height - crouch
        return 2 * math.sqrt(max(0.0, (self.leg * reach) ** 2 - height ** 2))

    def stand(self, pose, shift=None):
        """Plants both feet where they rest (plus `shift` {side: (x, y)})."""
        for side, sx in SIDES:
            ankle = self.ankle[side].copy()
            if shift:
                ankle += Vector((shift[side][0], shift[side][1], 0))
            pose.limb(f"thigh.{side}", f"shin.{side}", ankle, Vector((sx * 0.15, -1, 0.2)))
            pose.set_world(f"foot.{side}", Quaternion())

    def arm(self, pose, side, swing=0.0, bend=8.0, out=0.0):
        sx = 1.0 if side == "L" else -1.0
        pose.turn(f"upper_arm.{side}", X, swing)
        pose.turn(f"upper_arm.{side}", Y, out * sx)
        pose.turn(f"lower_arm.{side}", X, -bend)

    def gait(self, t, frames, duty, crouch, lift, stride=None, lean=3.0, swing=22.0, bend=10.0, sway=0.01,
             bob=0.012, twist=6.0, arms=("L", "R")):
        """A walk or run pose; returns (pose, speed)."""
        stride = self.stride(crouch) if stride is None else stride
        p = 2 * math.pi * t
        pose = Pose(self, (sway * math.sin(p), 0, -crouch + bob * math.cos(2 * p)))
        pose.turn("hips", Z, twist * 0.6 * math.sin(p))
        pose.turn("chest", X, lean)
        pose.turn("chest", Z, -twist * math.sin(p))
        pose.turn("head", X, -lean * 0.6)
        for (side, sx), phase in zip(SIDES, (0.0, 0.5)):
            ankle = self.ankle[side]
            dy, dz, u = step(t, phase, duty, stride, lift)
            psi = (t + phase) % 1.0
            front = math.cos(math.pi * psi / duty) if psi < duty else -math.cos(math.pi * u)
            toe = 25.0 * math.sin(math.pi * u) * (1 - u) if u else 0.0
            pose.limb(f"thigh.{side}", f"shin.{side}", Vector((ankle.x, ankle.y + dy, ankle.z + dz)),
                      Vector((sx * 0.1, -1, 0.3)))
            pose.set_world(f"foot.{side}", Quaternion(X, math.radians(toe)))
            if side in arms:
                self.arm(pose, side, swing * front, bend + swing * 0.4 * max(0.0, -front))
        return pose, stride * FPS / (duty * frames)

    def gait_speed(self, frames, duty, crouch, stride=None):
        stride = self.stride(crouch) if stride is None else stride
        return stride * FPS / (duty * frames)

    def idle(self, t, breath=1.0, look=6.0):
        p = 2 * math.pi * t
        b = math.sin(2 * p)
        pose = Pose(self, (0, 0, -0.004 * (1 + b)))
        self.stand(pose)
        pose.turn("chest", X, 1.5 * b * breath)
        pose.turn("head", Z, look * math.sin(p))
        for side, _ in SIDES:
            self.arm(pose, side, 1.5 * b, 8.0 + 2.0 * b)
        return pose
