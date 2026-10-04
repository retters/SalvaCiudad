"""Wyvern: a two-legged dragon 4.5 m long with a 5 m wingspan: wings for
arms, a long neck, a horned head with a hinged jaw, a row of spines down
the back and a tail ending in a barbed sting. Rigid segments; the legs are
posed by inverse kinematics. Clips: idle (stands with the wings half
folded), walk, fly (the game gives the height), attack (the neck rears and
strikes with the jaws open) and die (the legs give way and it rolls on its
side). Variants: green, red and black."""

import math

from mathutils import Quaternion, Vector

import _parts as P
from _parts import X, Y, Z, Pose, hull, rock, seg, spike, ball, plate

NECK = [Vector(p) for p in ((0, -0.5, 1.42), (0, -0.85, 1.72), (0, -1.15, 2.0), (0, -1.42, 2.14))]
HEAD_TIP = Vector((0, -1.98, 2.06))
TAIL = [Vector(p) for p in ((0, 0.55, 1.2), (0, 1.0, 1.05), (0, 1.45, 0.86), (0, 1.9, 0.72), (0, 2.3, 0.64), (0, 2.65, 0.62))]
HIP, KNEE, ANKLE, TOE = (0.3, 0.3, 1.1), (0.38, 0.0, 0.6), (0.38, 0.3, 0.14), (0.38, -0.02, 0.0)
SHOULDER, ELBOW, TIP = (0.3, -0.35, 1.55), (1.1, -0.3, 1.9), (2.4, -0.1, 1.75)

GREEN = P.palette(scale=0x4E7A3A, scale_dark=0x35582A, belly=0xD8C87A, membrane=0x8A4A32, horn=0xE6D8B8, eye=0xF2D23A,
                  mouth=0x8A2A30)
RED = P.palette(scale=0xA83A2A, scale_dark=0x7A261E, belly=0xE8B86A, membrane=0x5A2A2A, horn=0x2A2420, eye=0xFFE27A,
                mouth=0x4A1418)
BLACK = P.palette(scale=0x34303C, scale_dark=0x201E26, belly=0x6A5A7A, membrane=0x5A3A7A, horn=0xC8C2D0, eye=0xC86AFF,
                  mouth=0x3A1A4A)


def body(mb):
    rock(mb, (0, -0.22, 1.36), (0.38, 0.5, 0.4), "scale", "body", count=20, seed=3)
    rock(mb, (0, 0.3, 1.22), (0.32, 0.45, 0.33), "scale_dark", "body", count=16, seed=5)
    hull(mb, [(-0.2, -0.6, 1.02), (0.2, -0.6, 1.02), (-0.2, 0.5, 0.94), (0.2, 0.5, 0.94), (0, -0.2, 0.9), (0, 0.3, 0.86),
              (-0.15, -0.6, 1.15), (0.15, -0.6, 1.15)], "belly", "body")
    for i in range(6):
        y = -0.5 + i * 0.2
        spike(mb, (0, y, 1.68 - 0.04 * i), (0, y + 0.1, 1.95 - 0.07 * i), 0.07, "horn", "body")
    for i, (a, b) in enumerate(zip(NECK, NECK[1:])):
        seg(mb, a - Vector((0, 0.05, 0.05)), b, 0.24 - 0.04 * i, 0.2 - 0.04 * i, "scale" if i % 2 else "scale_dark",
            f"neck.{i + 1}", sides=7)
        spike(mb, (a + b) * 0.5 + Vector((0, 0.1, 0.14)), (a + b) * 0.5 + Vector((0, 0.2, 0.34)), 0.05, "horn",
              f"neck.{i + 1}")
    h = NECK[-1]

    def hp(x, y, z):
        return h + Vector((x, y, z))
    hull(mb, [hp(-0.16, 0.08, -0.08), hp(0.16, 0.08, -0.08), hp(-0.15, 0.08, 0.14), hp(0.15, 0.08, 0.14),
              hp(-0.14, -0.2, 0.12), hp(0.14, -0.2, 0.12), hp(-0.08, -0.56, 0.0), hp(0.08, -0.56, 0.0),
              hp(-0.1, -0.55, -0.1), hp(0.1, -0.55, -0.1), hp(-0.15, -0.15, -0.08), hp(0.15, -0.15, -0.08)],
         "scale", "head")
    hull(mb, [hp(-0.14, 0.04, -0.1), hp(0.14, 0.04, -0.1), hp(-0.14, 0.04, -0.18), hp(0.14, 0.04, -0.18),
              hp(-0.08, -0.52, -0.11), hp(0.08, -0.52, -0.11), hp(-0.07, -0.5, -0.17), hp(0.07, -0.5, -0.17)],
         "belly", "jaw")
    hull(mb, [hp(-0.1, 0.0, -0.105), hp(0.1, 0.0, -0.105), hp(-0.06, -0.48, -0.105), hp(0.06, -0.48, -0.105),
              hp(0, -0.25, -0.1)], "mouth", "jaw")
    for s in (-1, 1):
        ball(mb, hp(s * 0.13, -0.12, 0.08), 0.04, "eye", "head")
        spike(mb, hp(s * 0.1, 0.06, 0.1), hp(s * 0.2, 0.42, 0.3), 0.06, "horn", "head", sides=5)
        spike(mb, hp(s * 0.14, 0.05, -0.02), hp(s * 0.26, 0.26, -0.04), 0.04, "horn", "head", sides=4)
        for i in range(5):
            y = -0.14 - i * 0.09
            spike(mb, hp(s * (0.13 - 0.012 * i), y, -0.08), hp(s * (0.13 - 0.012 * i), y, -0.15), 0.02, "horn", "head",
                  sides=4)
        side = "L" if s > 0 else "R"

        def m(p, s=s):
            return Vector((p[0] * s, p[1], p[2]))
        seg(mb, m(HIP), m(KNEE), 0.19, 0.12, "scale", f"thigh.{side}")
        seg(mb, m(KNEE), m(ANKLE), 0.11, 0.075, "scale_dark", f"shin.{side}")
        ball(mb, m(KNEE), 0.12, "scale", f"shin.{side}")
        x = ANKLE[0] * s
        hull(mb, [(x - 0.08, 0.36, 0.0), (x + 0.08, 0.36, 0.0), (x - 0.13, 0.05, 0.0), (x + 0.13, 0.05, 0.0),
                  (x - 0.06, 0.34, 0.2), (x + 0.06, 0.34, 0.2), (x, 0.1, 0.12)], "scale_dark", f"foot.{side}")
        for dx in (-0.11, 0.0, 0.11):
            spike(mb, (x + dx * 0.9, 0.08, 0.05), (x + dx * 1.3, -0.14, 0.0), 0.045, "horn", f"foot.{side}", sides=4)
        sh, el, tip = m(SHOULDER), m(ELBOW), m(TIP)
        back, mid, root = Vector((s * 1.0, 0.65, 1.5)), Vector((s * 1.9, 0.5, 1.6)), Vector((s * 0.25, 0.45, 1.3))
        plate(mb, [sh, el, back, root], 0.03, "membrane", f"wing.1.{side}")
        plate(mb, [el, tip, mid, back], 0.03, "membrane", f"wing.2.{side}")
        seg(mb, sh, el, 0.1, 0.07, "scale", f"wing.1.{side}")
        rock(mb, sh, (0.16, 0.16, 0.15), "scale_dark", f"wing.1.{side}", count=10, seed=7)
        for end in (tip, mid, back):
            seg(mb, el, end, 0.05, 0.02, "scale_dark", f"wing.2.{side}", sides=4)
        spike(mb, el, el + Vector((s * 0.05, -0.28, 0.08)), 0.04, "horn", f"wing.2.{side}", sides=4)
    for i, (a, b) in enumerate(zip(TAIL, TAIL[1:])):
        seg(mb, a - Vector((0, 0.06, 0)), b, 0.25 - 0.045 * i, 0.2 - 0.04 * i, "scale" if i % 2 else "scale_dark",
            f"tail.{i + 1}", sides=6)
        spike(mb, (a + b) * 0.5 + Vector((0, 0, 0.18 - 0.03 * i)), (a + b) * 0.5 + Vector((0, 0.1, 0.36 - 0.05 * i)), 0.045,
              "horn", f"tail.{i + 1}")
    t = TAIL[-1]
    hull(mb, [t + Vector(o) for o in ((0, -0.05, 0.03), (0, -0.05, -0.03), (0.16, 0.05, 0), (-0.16, 0.05, 0),
                                      (0, 0.42, 0.0), (0, 0.1, 0.05), (0, 0.1, -0.05))], "horn", f"tail.{len(TAIL) - 1}")


def mech():
    bones = [("body", (0, 0.5, 1.25), (0, -0.5, 1.35), None)]
    parent = "body"
    for i, (a, b) in enumerate(zip(NECK, NECK[1:])):
        bones.append((f"neck.{i + 1}", tuple(a), tuple(b), parent))
        parent = f"neck.{i + 1}"
    bones += [("head", tuple(NECK[-1]), tuple(HEAD_TIP), parent),
              ("jaw", tuple(NECK[-1] + Vector((0, 0.04, -0.1))), tuple(HEAD_TIP + Vector((0, 0.05, -0.2))), "head")]
    parent = "body"
    for i, (a, b) in enumerate(zip(TAIL, TAIL[1:])):
        bones.append((f"tail.{i + 1}", tuple(a), tuple(b), parent))
        parent = f"tail.{i + 1}"
    for side, s in P.SIDES:
        def m(p, s=s):
            return (p[0] * s, p[1], p[2])
        bones += [(f"thigh.{side}", m(HIP), m(KNEE), "body"), (f"shin.{side}", m(KNEE), m(ANKLE), f"thigh.{side}"),
                  (f"foot.{side}", m(ANKLE), m(TOE), f"shin.{side}"),
                  (f"wing.1.{side}", m(SHOULDER), m(ELBOW), "body"), (f"wing.2.{side}", m(ELBOW), m(TIP), f"wing.1.{side}")]
    m_ = P.kit.Mech(bones)
    n_neck, n_tail = len(NECK) - 1, len(TAIL) - 1
    frames, duty, stride, lift, crouch = 26, 0.64, 0.7, 0.2, 0.08
    speed = stride * P.FPS / (duty * frames)

    def stand(pose, targets=None):
        for side, s in P.SIDES:
            ankle = Vector((ANKLE[0] * s, ANKLE[1], ANKLE[2]))
            pose.limb(f"thigh.{side}", f"shin.{side}", (targets or {}).get(side, ankle), Vector((s * 0.2, -1.0, 0.3)))
            pose.set_world(f"foot.{side}", Quaternion())

    def neck(pose, bend, side=0.0, head=0.0, jaw=0.0):
        for i in range(n_neck):
            pose.turn(f"neck.{i + 1}", X, bend)
            pose.turn(f"neck.{i + 1}", Z, side)
        pose.turn("head", X, head)
        pose.turn("jaw", X, jaw)

    def tail(pose, fn, up=0.0):
        for i in range(n_tail):
            pose.turn(f"tail.{i + 1}", Z, fn(i))
            pose.turn(f"tail.{i + 1}", X, up)

    def wings(pose, raise_, fold):
        """Inner panel raised by `raise_` degrees, outer one folded down."""
        for side, s in P.SIDES:
            pose.turn(f"wing.1.{side}", Y, -s * raise_)
            pose.turn(f"wing.2.{side}", Y, s * fold)

    def idle(t):
        p = 2 * math.pi * t
        pose = Pose(m_, (0, 0, -0.03 - 0.02 * math.sin(2 * p)))
        pose.turn("body", X, 1.5 * math.sin(2 * p))
        stand(pose)
        neck(pose, 2.0 * math.sin(2 * p), 6.0 * math.sin(p), head=4.0 * math.sin(p + 1), jaw=6.0 * P.pulse(t, 0.6, 0.68, 0.72, 0.8))
        tail(pose, lambda i: 7.0 * math.sin(p - i * 0.7))
        wings(pose, 42.0 + 3.0 * math.sin(2 * p), 95.0)
        return P.from_pose(pose)

    def walk(t):
        p = 2 * math.pi * t
        pose = Pose(m_, (0.05 * math.sin(p), 0, -crouch + 0.03 * math.cos(2 * p)))
        pose.turn("body", Z, 4.0 * math.sin(p))
        pose.turn("body", Y, 3.0 * math.sin(p))
        targets = {}
        for (side, s), phase in zip(P.SIDES, (0.0, 0.5)):
            dy, dz, u = P.step(t, phase, duty, stride, lift)
            targets[side] = Vector((ANKLE[0] * s, ANKLE[1] + dy, ANKLE[2] + dz))
        stand(pose, targets)
        neck(pose, 3.0 * math.cos(2 * p), -3.0 * math.sin(p), head=-3.0 * math.cos(2 * p))
        tail(pose, lambda i: -9.0 * math.sin(p - (i + 1) * 0.6))
        wings(pose, 42.0 + 4.0 * math.cos(2 * p), 95.0)
        return P.from_pose(pose)

    def fly(t):
        p = 2 * math.pi * t
        pose = Pose(m_, (0, 0, 0.6 - 0.12 * math.sin(p + 1.2)))
        pose.turn("body", X, 10.0 + 3.0 * math.sin(p))
        neck(pose, 12.0, head=-30.0)
        tail(pose, lambda i: 3.0 * math.sin(p - i), up=5.0)
        for side, s in P.SIDES:
            pose.turn(f"thigh.{side}", X, 55.0)
            pose.turn(f"shin.{side}", X, -40.0)
            pose.turn(f"wing.1.{side}", Y, -s * (6.0 + 34.0 * math.sin(p)))
            pose.turn(f"wing.2.{side}", Y, -s * (26.0 * math.sin(p - 0.9) - 6.0))
        return P.from_pose(pose)

    def attack(t):
        w = P.pulse(t, 0.0, 0.34, 0.4, 0.48)
        s = P.pulse(t, 0.4, 0.48, 0.56, 0.95)
        pose = Pose(m_, (0, 0.1 * w - 0.3 * s, -0.03 - 0.06 * s))
        pose.turn("body", X, -8.0 * w + 7.0 * s)
        stand(pose)
        neck(pose, -12.0 * w + 9.0 * s, head=10.0 * w - 8.0 * s, jaw=30.0 * max(w * 0.7, s))
        tail(pose, lambda i: 0.0, up=3.0 * s + 5.0 * w)
        wings(pose, 42.0 + 25.0 * w - 10.0 * s, 95.0 - 60.0 * w)
        return P.from_pose(pose)

    def die(t):
        stagger = P.pulse(t, 0.0, 0.2, 0.25, 0.4)
        a = P.smooth((t - 0.2) / 0.6)
        pose = Pose(m_, (0.35 * a, 0, -0.8 * a))
        pose.turn("body", Y, 4.0 * stagger + 72.0 * a)
        pose.turn("body", X, 6.0 * a)
        neck(pose, 4.0 * a, side=-10.0 * a, head=12.0 * a, jaw=22.0 * a)
        tail(pose, lambda i: 6.0 * a, up=-3.0 * a)
        for side, s in P.SIDES:
            pose.turn(f"thigh.{side}", X, -30.0 * a)
            pose.turn(f"shin.{side}", X, 40.0 * a)
            pose.turn(f"wing.1.{side}", Y, -s * (42.0 - 30.0 * a) if s > 0 else -s * (42.0 + 20.0 * a))
            pose.turn(f"wing.2.{side}", Y, s * 95.0)
        return P.from_pose(pose)

    m_.clip("idle", 4.0, idle)
    m_.clip("walk", frames / P.FPS, walk, speed=speed)
    m_.clip("fly", 0.8, fly, speed=8.0)
    m_.clip("attack", 1.3, attack)
    m_.clip("die", 1.8, die, loops=False)
    return m_


def build(name, colors, k=1.0):
    def make():
        mb = P.kit.begin()
        body(mb)
        P.save(mb, name, colors, mech(), k)
    return make


MODELS = {"monster_wyvern": build("monster_wyvern", GREEN), "monster_wyvern_red": build("monster_wyvern_red", RED),
          "monster_wyvern_black": build("monster_wyvern_black", BLACK),
          "monster_wyvern_hatchling": build("monster_wyvern_hatchling", GREEN, k=0.3)}
