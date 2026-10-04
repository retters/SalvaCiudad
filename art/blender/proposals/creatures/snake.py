"""Giant snake and basilisk: a body of fourteen overlapping segments, each
on its own bone, placed along a wave in world space so the whole body
slithers; the neck is raised and the head has a jaw of fangs and a forked
tongue. Clips: idle (the raised head sways, the tongue flicks), walk
(slithers), attack (the head darts forward) and die (it writhes and ends
limp on its side). The basilisk is bigger and green, with a crest of
spines and glowing eyes. A small viper is the ambient variant."""

import math

from mathutils import Quaternion, Vector

import _parts as P
from _parts import X, Y, Z, hull, seg, spike, ball, plate

N = 14               # Body segments, head first.
RAISED = 4           # Segments of the raised neck.


def layout(k):
    """Rest centers of the joints: the neck comes up in an S, the rest lies
    straight back on the ground. Returns N + 1 points and their radii."""
    pts, radii = [], []
    seg_len = 0.3 * k
    for i in range(N + 1):
        r = (0.085 + 0.045 * math.sin(math.pi * min(1.0, (i + 1) / 8.0)) ** 0.8) * k
        if i > 8:
            r = (0.13 - 0.016 * (i - 8)) * k
        radii.append(max(r, 0.02 * k))
    # The body from the first ground joint back.
    ground = [Vector((0, (i - RAISED) * seg_len, radii[i])) for i in range(RAISED, N + 1)]
    neck = []
    for i in range(RAISED):
        u = (RAISED - i) / RAISED                              # 1 at the head.
        neck.append(Vector((0, -0.28 * k * u * u, radii[RAISED] + 0.85 * k * u ** 0.9)))
    return neck + ground, radii


def body(mb, k, basilisk):
    pts, radii = layout(k)
    for i in range(N):
        a, b = pts[i], pts[i + 1]
        over = (b - a).normalized() * 0.03 * k
        mat = "scale" if i % 2 == 0 else "scale_dark"
        seg(mb, a - over, b + over, radii[i], radii[i + 1], mat, f"seg.{i + 1}", sides=6)
        d = (b - a).normalized()
        up = Vector((0, 0, 1)) - d * d.z
        if up.length < 0.2:
            up = Vector((0, 1, 0))
        up.normalize()
        mid = (a + b) * 0.5
        if basilisk and i < 9:                                 # Spines along the back.
            spike(mb, mid + up * radii[i] * 0.8, mid + up * (radii[i] + (0.2 - 0.015 * i) * k) + d * 0.06 * k,
                  0.035 * k, "crest", f"seg.{i + 1}")
        else:                                                  # A diamond on the back of each segment.
            hull(mb, [mid + up * radii[i] * 0.93 + o for o in (d * 0.09 * k, -d * 0.09 * k, Vector((0.05 * k, 0, 0)),
                                                              Vector((-0.05 * k, 0, 0)))]
                 + [mid + up * (radii[i] * 0.93 + 0.02 * k)], "mark", f"seg.{i + 1}")
    # Head: a wedge in front of the first joint, a lower jaw, eyes, fangs, tongue.
    h = pts[0]
    w = 0.13 * k

    def hp(x, y, z):
        return h + Vector((x, y, z)) * k
    hull(mb, [hp(-0.12, 0.06, 0.0), hp(0.12, 0.06, 0.0), hp(-0.13, -0.08, 0.01), hp(0.13, -0.08, 0.01),
              hp(-0.07, -0.34, -0.02), hp(0.07, -0.34, -0.02), hp(-0.09, 0.04, 0.1), hp(0.09, 0.04, 0.1),
              hp(-0.08, -0.14, 0.09), hp(0.08, -0.14, 0.09), hp(0, -0.36, 0.02)], "scale", "head")
    hull(mb, [hp(-0.1, 0.02, -0.01), hp(0.1, 0.02, -0.01), hp(-0.06, -0.3, -0.03), hp(0.06, -0.3, -0.03),
              hp(-0.08, 0.0, -0.07), hp(0.08, 0.0, -0.07), hp(0, -0.3, -0.06)], "belly", "jaw")
    for s in (-1, 1):
        ball(mb, hp(s * 0.095, -0.12, 0.06), 0.03 * k, "eye", "head")
        spike(mb, hp(s * 0.05, -0.3, -0.02), hp(s * 0.05, -0.31, -0.11), 0.014 * k, "fang", "head", sides=4)
        if basilisk:
            for j in range(3):                                 # A crown of horns.
                spike(mb, hp(s * (0.03 + 0.03 * j), 0.0 + 0.02 * j, 0.09),
                      hp(s * (0.05 + 0.06 * j), 0.1 + 0.03 * j, 0.24 - 0.04 * j), 0.025 * k, "crest", "head")
    plate(mb, [hp(-0.012, -0.3, -0.035), hp(0.012, -0.3, -0.035), hp(0.03, -0.46, -0.04), hp(0.0, -0.42, -0.04),
               hp(-0.03, -0.46, -0.04)], 0.008 * k, "tongue", "tongue")
    return pts, radii, w


def mech(k, pts, radii):
    bones = [("head", tuple(pts[0]), tuple(pts[0] + Vector((0, -0.34 * k, 0))), None),
             ("jaw", tuple(pts[0] + Vector((0, 0.02 * k, -0.01 * k))), tuple(pts[0] + Vector((0, -0.3 * k, -0.04 * k))),
              "head"),
             ("tongue", tuple(pts[0] + Vector((0, -0.28 * k, -0.035 * k))),
              tuple(pts[0] + Vector((0, -0.46 * k, -0.04 * k))), "head")]
    for i in range(N):
        bones.append((f"seg.{i + 1}", tuple(pts[i]), tuple(pts[i + 1]), None))
    m = P.kit.Mech(bones)
    length = 0.3 * k * (N - RAISED)
    wavelength = length / 1.25
    amp = 0.2 * k

    def side(y, phase, a):
        """Sideways offset of the body at distance y behind the neck's base."""
        grow = P.smooth(y / (0.5 * k))                          # No wave under the raised neck.
        return a * grow * math.sin(2 * math.pi * (y / wavelength) + phase)

    def shape(phase, a, lift=1.0, lunge=0.0, sway=0.0, roll=0.0, drop=0.0):
        """World joints for a wave of amplitude `a`; `lift` scales how high
        the neck is raised, `lunge` throws the head forward, `sway` moves it
        sideways, `roll` turns the body on its side and `drop` lays the
        head on the ground."""
        joints = []
        for i in range(N + 1):
            p = pts[i].copy()
            if i < RAISED:
                u = (RAISED - i) / RAISED
                p.z = radii[i] + (p.z - radii[i]) * lift * (1 - drop)
                p.y -= lunge * u ** 1.5 * k
                p.z -= lunge * 0.35 * u * k * (1 - drop)
                p.x += sway * u * k + side(0.0, phase, a) * (1 - u)
                p.y *= 1.0 if not drop else 1.0 + 0.5 * drop * u
            else:
                p.x += side(p.y, phase, a)
            joints.append(p)
        # Keep every segment its own length (no gaps): from the neck's base
        # toward the head, then toward the tail; nothing below the ground.
        for i in range(RAISED - 1, -1, -1):
            d = (joints[i] - joints[i + 1]).normalized()
            joints[i] = joints[i + 1] + d * (pts[i] - pts[i + 1]).length
            joints[i].z = max(joints[i].z, radii[i] + (0.09 * k if i == 0 else 0.0))
        for i in range(RAISED + 1, N + 1):
            d = (joints[i] - joints[i - 1]).normalized()
            joints[i] = joints[i - 1] + d * (pts[i] - pts[i - 1]).length
        turn, place = {}, {}
        for i in range(N):
            rest = (pts[i + 1] - pts[i]).normalized()
            now = (joints[i + 1] - joints[i]).normalized()
            q = rest.rotation_difference(now)
            if roll:
                q = Quaternion(now, math.radians(roll)) @ q
            turn[f"seg.{i + 1}"] = q
            place[f"seg.{i + 1}"] = joints[i]
        # The head looks along the first segment, flattened toward level.
        first = (joints[0] - joints[1])
        yaw = math.atan2(-first.x, -first.y) if first.length > 1e-6 else 0.0
        head = Quaternion(Z, -yaw * 0.6 + math.radians(sway * 30.0))
        if roll:
            head = Quaternion(Y, math.radians(roll)) @ head
        turn["head"], place["head"] = head, joints[0]
        return turn, place

    def finish(turn, place, jaw=0.0, tongue=0.0, flick=0.0):
        turns, moves = P.world_pose(m, turn, place)
        if jaw:
            turns["jaw"] = [(X, jaw)]
        if tongue or flick:
            turns["tongue"] = [(X, flick)]
            moves["tongue"] = (0, -tongue * k, 0)
        return turns, moves

    def idle(t):
        p = 2 * math.pi * t
        f = P.pulse(t, 0.2, 0.24, 0.3, 0.34) + P.pulse(t, 0.6, 0.64, 0.7, 0.74)
        turn, place = shape(0.6 + 0.15 * math.sin(p), amp * 0.8, lift=1.0 + 0.04 * math.sin(2 * p),
                            sway=0.12 * math.sin(p))
        return finish(turn, place, tongue=-0.08 + 0.2 * f, flick=10.0 * math.sin(40 * t) * f)

    def slither(t):
        turn, place = shape(2 * math.pi * t, amp, lift=0.75, lunge=0.1, sway=0.05 * math.sin(2 * math.pi * t))
        return finish(turn, place, tongue=-0.08)

    def attack(t):
        w = P.pulse(t, 0.0, 0.3, 0.36, 0.44)
        s = P.pulse(t, 0.36, 0.44, 0.5, 0.95)
        turn, place = shape(0.6, amp * 0.8, lift=1.0 + 0.12 * w - 0.25 * s, lunge=-0.25 * w + 1.1 * s)
        return finish(turn, place, jaw=38.0 * max(w * 0.6, s), tongue=-0.08)

    def die(t):
        writhe = 1.0 - P.smooth(t / 0.6)
        a = P.smooth((t - 0.3) / 0.6)
        turn, place = shape(0.6 + 9.0 * t * writhe, amp * (0.8 + 0.6 * writhe * math.sin(20 * t)),
                            lift=1.0 - a, lunge=0.3 * a, roll=75.0 * a, drop=a)
        return finish(turn, place, jaw=30.0 * a, tongue=0.05 * a)

    m.clip("idle", 3.0, idle)
    m.clip("walk", 1.2, slither)
    m.clip("attack", 0.9, attack)
    m.clip("die", 1.5, die, loops=False)
    return m


def colors(scale, dark, belly, mark, eye=0xF2D23A, crest=0xD9B24A):
    return P.palette(scale=scale, scale_dark=dark, belly=belly, mark=mark, eye=eye, fang=0xF2EAD6, tongue=0xC8302A,
                     crest=crest)


def build(name, palette, k=1.0, basilisk=False):
    def make():
        mb = P.kit.begin()
        pts, radii, _ = body(mb, k, basilisk)
        P.kit.save(mb, P.FAMILY, name, palette, mech=mech(k, pts, radii))
    return make


MODELS = {
    "enemy_snake_giant": build("enemy_snake_giant", colors(0x7A8A3A, 0x5A6A2A, 0xD8CC8A, 0x2E3A1A)),
    "monster_basilisk": build("monster_basilisk", colors(0x2E8A6A, 0x1E6A52, 0xC8D89A, 0x1A4A3A, eye=0xFF5A2A), k=1.6,
                              basilisk=True),
    "animal_viper": build("animal_viper", colors(0x8A6A4A, 0x5A4632, 0xD8C8A8, 0x2A2018), k=0.3),
}
