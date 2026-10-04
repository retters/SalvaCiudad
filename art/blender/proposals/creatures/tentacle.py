"""Kraken tentacle: a 4.5 m arm that comes out of the water at the coast,
in nine tapering segments with a row of suckers and a paddle tip, on a
ring of foam. The origin is at the water's surface. Clips: idle (sways),
attack (rears back and slams down in front), emerge (rises out of the
water, once) and die (thrashes and sinks, once). Variants: red, deep blue
and pale green. A second model is a short "feeler" a third of the size."""

import math

from mathutils import Vector

import _parts as P
from _parts import X, Y, Z, Pose, hull, seg, ball, plate

N = 9
RED = P.palette(skin=0xB8402E, skin_dark=0x8A2A22, belly=0xE8B8A8, sucker=0xF2D8CC, foam=0xECF4F8)
BLUE = P.palette(skin=0x2E4A7A, skin_dark=0x1E3258, belly=0xA8C0D8, sucker=0xDCE8F0, foam=0xECF4F8)
GREEN = P.palette(skin=0x6A9A6A, skin_dark=0x4A7A52, belly=0xD8E8C0, sucker=0xF0F4E0, foam=0xECF4F8)


def joints(k):
    """Rest joints: straight up with a lazy S, thinner toward the tip."""
    pts, radii = [], []
    for i in range(N + 1):
        u = i / N
        pts.append(Vector((0, 0.22 * k * math.sin(u * math.pi * 1.6), 0.5 * k * i - 0.3 * k)))
        radii.append((0.36 - 0.3 * u ** 0.8) * k)
    return pts, radii


def body(mb, k):
    pts, radii = joints(k)
    for i in range(N):
        a, b = pts[i], pts[i + 1]
        over = (b - a).normalized() * 0.04 * k
        seg(mb, a - over, b + over, radii[i], radii[i + 1], "skin" if i % 2 else "skin_dark", f"seg.{i + 1}", sides=7)
        mid = (a + b) * 0.5
        r = (radii[i] + radii[i + 1]) * 0.5
        hull(mb, [mid + Vector(o) for o in ((-r * 0.6, -r * 0.8, -0.2 * k), (r * 0.6, -r * 0.8, -0.2 * k),
                                            (-r * 0.6, -r * 0.8, 0.2 * k), (r * 0.6, -r * 0.8, 0.2 * k),
                                            (0, -r * 1.02, 0.0))], "belly", f"seg.{i + 1}")
        for dz in (-0.12, 0.12):
            ball(mb, mid + Vector((0, -r * 1.0, dz * k)), r * 0.3, "sucker", f"seg.{i + 1}", scale=(1, 0.5, 1))
    tip = pts[-1]
    plate(mb, [tip + Vector(o) * k for o in ((-0.06, 0, -0.05), (0.06, 0, -0.05), (0.16, 0, 0.2), (0, 0, 0.42),
                                             (-0.16, 0, 0.2))], 0.06 * k, "skin", f"seg.{N}")
    for i in range(8):                                        # Foam where it breaks the surface.
        a = i * math.tau / 8
        hull(mb, [(math.cos(a + d) * r * k, math.sin(a + d) * r * k, z * k) for d, r, z in
                  ((-0.3, 0.42, 0.0), (0.3, 0.42, 0.0), (-0.35, 0.72, 0.0), (0.35, 0.72, 0.0), (0, 0.55, 0.07))],
             "foam", "foam")
    return pts


def mech(k, pts):
    bones = [("foam", (0, 0, 0), (0, 0, 0.1 * k), None)]
    parent = None
    for i in range(N):
        bones.append((f"seg.{i + 1}", tuple(pts[i]), tuple(pts[i + 1]), parent))
        parent = f"seg.{i + 1}"
    m = P.kit.Mech(bones)

    def bend(pose, fn):
        for i in range(N):
            x, y = fn(i)
            pose.turn(f"seg.{i + 1}", X, x)
            pose.turn(f"seg.{i + 1}", Y, y)

    def foam(turns, moves, t, sunk=0.0):
        turns["foam"] = [(Z, 20.0 * math.sin(2 * math.pi * t))]
        moves["foam"] = (0, 0, 0.02 * k * math.sin(4 * math.pi * t) - 0.3 * k * sunk)
        return turns, moves

    def idle(t):
        p = 2 * math.pi * t
        pose = Pose(m, (0, 0, 0.05 * k * math.sin(p)))
        bend(pose, lambda i: (5.0 * math.sin(p - i * 0.6), 6.0 * math.sin(p * 2 - i * 0.5) * min(1.0, i / 3)))
        turns, moves = P.from_pose(pose)
        moves["seg.1"] = moves.pop("root")
        return foam(turns, moves, t)

    def attack(t):
        w = P.pulse(t, 0.0, 0.34, 0.4, 0.5)
        s = P.pulse(t, 0.4, 0.5, 0.62, 1.0)
        pose = Pose(m, (0, 0, 0.2 * k * w - 0.1 * k * s))
        bend(pose, lambda i: (-7.0 * w + s * (22.0 if i < 4 else 2.0), 0.0))      # Folds near the surface.
        turns, moves = P.from_pose(pose)
        moves["seg.1"] = moves.pop("root")
        return foam(turns, moves, t)

    def under(a):
        """The arm curled and pulled below the surface by `a` (0 to 1)."""
        pose = Pose(m, (0, 0, -5.0 * k * a))
        bend(pose, lambda i: (0.0, 0.0))
        return pose

    def emerge(t):
        a = 1.0 - P.smooth(t / 0.7)
        pose = under(a)
        wob = math.sin(14 * t) * (1 - t)
        bend(pose, lambda i: (18.0 * a + 4.0 * wob, 6.0 * wob))
        turns, moves = P.from_pose(pose)
        moves["seg.1"] = moves.pop("root")
        return foam(turns, moves, t, sunk=0.0)

    def die(t):
        thrash = math.sin(22 * t) * (1 - P.smooth(t / 0.6))
        a = P.smooth((t - 0.3) / 0.7)
        pose = under(a)
        bend(pose, lambda i: (10.0 * thrash + 14.0 * a, 12.0 * thrash * math.cos(i)))
        turns, moves = P.from_pose(pose)
        moves["seg.1"] = moves.pop("root")
        return foam(turns, moves, t, sunk=a)

    m.clip("idle", 3.0, idle)
    m.clip("attack", 1.5, attack)
    m.clip("emerge", 1.4, emerge, loops=False)
    m.clip("die", 2.0, die, loops=False)
    return m


def build(name, colors, k=1.0):
    def make():
        mb = P.kit.begin()
        pts = body(mb, k)
        P.kit.save(mb, P.FAMILY, name, colors, mech=mech(k, pts))
    return make


MODELS = {"monster_kraken_tentacle": build("monster_kraken_tentacle", RED),
          "monster_kraken_tentacle_blue": build("monster_kraken_tentacle_blue", BLUE),
          "monster_kraken_feeler": build("monster_kraken_feeler", GREEN, k=0.35)}
