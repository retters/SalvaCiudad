"""Harpy: a winged woman-bird 1.5 m tall with a 3 m wingspan: a feathered
body, a wild-haired head, wings instead of arms (two feather panels a
side) and bird legs with talons. Modeled hovering 0.5 m above the ground;
the game gives the flying height. Clips: idle (hovers), fly, attack (rears
back and rakes with both talons) and die (falls, wings folding). Variants:
gray-brown, black with red hair, and white."""

import math

from mathutils import Vector

import _parts as P
from _parts import X, Y, Z, Pose, hull, rock, seg, spike, ball, plate

H = 0.5   # Height of the talons above the ground at rest.

BROWN = P.palette(skin=0xD8A888, feather=0x7A6A5A, feather_dark=0x4E4238, feather_light=0xB8A890, hair=0x3A2A22,
                  leg=0xD9A23A, claw=0x2A2420, eye=0xF2D23A, cloth=0x6A3A30)
BLACK = P.palette(skin=0xB8A0A8, feather=0x2E2A34, feather_dark=0x1A181E, feather_light=0x4A4454, hair=0xB8302A,
                  leg=0x8A7A5A, claw=0x141214, eye=0xFF5A2A, cloth=0x3A1E2A)
WHITE = P.palette(skin=0xE8C8B0, feather=0xECE8E0, feather_dark=0xC8C2B4, feather_light=0xFFFFFF, hair=0xD8C8A0,
                  leg=0xE8B030, claw=0x3A3028, eye=0x3F86C8, cloth=0x6FA8D8)

SHOULDER, ELBOW, TIP = (0.2, 0.02, H + 0.98), (0.75, 0.0, H + 1.1), (1.5, 0.08, H + 1.0)
HIP, KNEE, ANKLE = (0.1, 0.0, H + 0.42), (0.13, -0.1, H + 0.2), (0.13, -0.04, H + 0.03)


def body(mb):
    rock(mb, (0, 0.02, H + 0.52), (0.2, 0.18, 0.22), "feather", "body", count=16, seed=2)          # Feathered hips.
    rock(mb, (0, 0.0, H + 0.86), (0.2, 0.14, 0.2), "skin", "body", count=14, seed=3)               # Torso.
    hull(mb, [(-0.19, -0.13, H + 0.92), (0.19, -0.13, H + 0.92), (-0.17, -0.14, H + 0.76), (0.17, -0.14, H + 0.76),
              (0, -0.17, H + 0.86), (-0.19, 0.0, H + 0.92), (0.19, 0.0, H + 0.92), (-0.17, 0.0, H + 0.76),
              (0.17, 0.0, H + 0.76)], "cloth", "body")
    for a in range(5):                                                                          # Tail fan.
        ang = math.radians(-40 + a * 20)
        plate(mb, [(-0.04, 0.14, H + 0.42), (0.04, 0.14, H + 0.42),
                   (math.sin(ang) * 0.3 + 0.05, 0.42 + 0.06 * math.cos(ang), H + 0.2),
                   (math.sin(ang) * 0.3 - 0.05, 0.42 + 0.06 * math.cos(ang), H + 0.2)], 0.015,
              "feather_dark" if a % 2 else "feather", "tail")
    seg(mb, (0, 0, H + 1.02), (0, -0.01, H + 1.12), 0.055, 0.05, "skin", "head")
    rock(mb, (0, -0.02, H + 1.24), (0.11, 0.12, 0.13), "skin", "head", count=14, seed=4, jitter=0.04)
    spike(mb, (0, -0.12, H + 1.23), (0, -0.2, H + 1.19), 0.03, "leg", "head", sides=4)             # A beak of a nose.
    for i, d in enumerate(((0, 0.5, 1), (0.6, 0.4, 0.8), (-0.6, 0.4, 0.8), (0.4, 0.9, 0.3), (-0.4, 0.9, 0.3),
                           (0, 1, 0.1), (0.8, 0.3, 0.2), (-0.8, 0.3, 0.2))):
        d = Vector(d).normalized()
        c = Vector((0, 0.0, H + 1.27))
        spike(mb, c + d * 0.08, c + d * (0.3 if i < 5 else 0.36), 0.06, "hair", "head", sides=4)
    for s in (-1, 1):
        ball(mb, (s * 0.045, -0.125, H + 1.27), 0.018, "eye", "head")
        side = "L" if s > 0 else "R"

        def m(p, s=s):
            return Vector((p[0] * s, p[1], p[2]))
        sh, el, tip = m(SHOULDER), m(ELBOW), m(TIP)
        seg(mb, sh, el, 0.05, 0.035, "skin", f"wing.1.{side}", sides=5)
        seg(mb, el, tip, 0.035, 0.015, "feather_dark", f"wing.2.{side}", sides=4)
        # Feathers: long panels hanging behind the arm, in two rows.
        for i in range(4):
            a, b = sh.lerp(el, i / 4), sh.lerp(el, (i + 1) / 4)
            drop = 0.45 + 0.06 * i
            plate(mb, [a, b, b + Vector((0, 0.16, -drop)), a + Vector((0, 0.14, -drop + 0.05))], 0.014,
                  "feather" if i % 2 else "feather_light", f"wing.1.{side}")
        for i in range(5):
            a, b = el.lerp(tip, i / 5), el.lerp(tip, (i + 1) / 5)
            drop = 0.66 - 0.1 * i
            plate(mb, [a, b, b + Vector((s * 0.1, 0.2, -drop + 0.08)), a + Vector((s * 0.04, 0.18, -drop))], 0.014,
                  "feather_dark" if i % 2 else "feather", f"wing.2.{side}")
        hip, knee, ankle = m(HIP), m(KNEE), m(ANKLE)
        seg(mb, hip, knee, 0.085, 0.045, "feather", f"leg.{side}")
        seg(mb, knee, ankle, 0.03, 0.025, "leg", f"shin.{side}", sides=5)
        for dx, dy in ((-0.06, -0.1), (0.0, -0.13), (0.06, -0.1), (0.0, 0.08)):
            a = ankle + Vector((dx * 0.6, dy * 0.6, -0.02))
            seg(mb, ankle, a, 0.018, 0.014, "leg", f"foot.{side}", sides=4)
            spike(mb, a, ankle + Vector((dx, dy, -0.07)), 0.014, "claw", f"foot.{side}", sides=4)


def mech():
    bones = [("body", (0, 0, H + 0.45), (0, 0, H + 1.0), None), ("head", (0, 0, H + 1.05), (0, -0.02, H + 1.38), "body"),
             ("tail", (0, 0.14, H + 0.42), (0, 0.42, H + 0.2), "body")]
    for side, s in P.SIDES:
        def m(p, s=s):
            return (p[0] * s, p[1], p[2])
        bones += [(f"wing.1.{side}", m(SHOULDER), m(ELBOW), "body"), (f"wing.2.{side}", m(ELBOW), m(TIP), f"wing.1.{side}"),
                  (f"leg.{side}", m(HIP), m(KNEE), "body"), (f"shin.{side}", m(KNEE), m(ANKLE), f"leg.{side}"),
                  (f"foot.{side}", m(ANKLE), (ANKLE[0] * s, ANKLE[1] - 0.12, ANKLE[2] - 0.05), f"shin.{side}")]
    m_ = P.kit.Mech(bones)

    def flap(pose, phase, amp, mid=6.0, sweep=0.0):
        for side, s in P.SIDES:
            pose.turn(f"wing.1.{side}", Y, -s * (mid + amp * math.sin(phase)))
            pose.turn(f"wing.2.{side}", Y, -s * (amp * 0.7 * math.sin(phase - 0.9) - 8.0))
            pose.turn(f"wing.1.{side}", Z, s * sweep)

    def legs(pose, tuck, spread=0.0):
        for side, s in P.SIDES:
            pose.turn(f"leg.{side}", X, -tuck)
            pose.turn(f"shin.{side}", X, tuck * 1.5)
            pose.turn(f"leg.{side}", Y, spread * s)

    def idle(t):
        p = 2 * math.pi * t
        pose = Pose(m_, (0, 0, 0.1 + 0.07 * math.sin(2 * p + 1.2)))
        pose.turn("body", X, 4.0 * math.sin(p))
        pose.turn("head", Z, 14.0 * math.sin(p))
        pose.turn("tail", X, 8.0 * math.sin(2 * p))
        flap(pose, 2 * p, 30.0)
        legs(pose, 12.0 + 6.0 * math.sin(2 * p))
        return P.from_pose(pose)

    def fly(t):
        p = 2 * math.pi * t
        pose = Pose(m_, (0, 0, 0.2 + 0.07 * math.sin(p + 1.2)))
        pose.turn("body", X, 48.0)
        pose.turn("head", X, -38.0)
        pose.turn("tail", X, -30.0)
        flap(pose, p, 36.0)
        legs(pose, -30.0)
        return P.from_pose(pose)

    def attack(t):
        p = 2 * math.pi * t
        w = P.pulse(t, 0.0, 0.3, 0.36, 0.46)
        s = P.pulse(t, 0.36, 0.46, 0.56, 0.95)
        pose = Pose(m_, (0, 0.12 * w - 0.3 * s, 0.1 + 0.25 * w - 0.05 * s))
        pose.turn("body", X, -28.0 * w - 14.0 * s)
        pose.turn("head", X, 20.0 * w + 16.0 * s)
        flap(pose, 4 * p, 26.0, mid=18.0 * max(w, s))
        for side, sx in P.SIDES:
            pose.turn(f"leg.{side}", X, -40.0 * w - 85.0 * s)
            pose.turn(f"shin.{side}", X, 70.0 * w + 30.0 * s)
            pose.turn(f"foot.{side}", X, -30.0 * s)
            pose.turn(f"leg.{side}", Y, 10.0 * s * sx)
        return P.from_pose(pose)

    def die(t):
        fall = P.smooth((t - 0.1) / 0.6)
        land = P.smooth((t - 0.65) / 0.3)
        pose = Pose(m_, (0.15 * fall, 0.2 * fall, 0.1 - (H + 0.45 - 0.12) * fall * fall))
        pose.turn("body", X, -86.0 * fall)                     # Ends on its back.
        pose.turn("body", Y, 20.0 * math.sin(math.pi * fall))
        pose.turn("head", X, 14.0 * land)
        pose.turn("head", Z, 30.0 * land)
        for side, s in P.SIDES:
            fold = 40.0 * fall * (1 - land)
            pose.turn(f"wing.1.{side}", Y, -s * (6.0 + fold))
            pose.turn(f"wing.2.{side}", Y, -s * (-8.0 + fold * 1.3))
            pose.turn(f"wing.1.{side}", X, 84.0 * land)        # The wings end spread flat on the ground.
            pose.turn(f"leg.{side}", X, -20.0 * fall)
            pose.turn(f"shin.{side}", X, 50.0 * fall)
        return P.from_pose(pose)

    m_.clip("idle", 20 / P.FPS, idle)
    m_.clip("fly", 16 / P.FPS, fly, speed=6.0)
    m_.clip("attack", 1.2, attack)
    m_.clip("die", 1.4, die, loops=False)
    return m_


def build(name, colors):
    def make():
        mb = P.kit.begin()
        body(mb)
        P.kit.save(mb, P.FAMILY, name, colors, mech=mech())
    return make


# A gargoyle: the same body carved in stone, with ember eyes.
STONE = P.palette(skin=0x8E9196, feather=0x7A7E84, feather_dark=0x5E6268, feather_light=0x9EA2A8, hair=0x5E6268,
                  leg=0x6E7278, claw=0x44484E, eye=0xFF8A2A, cloth=0x6E7278)

MODELS = {"enemy_harpy": build("enemy_harpy", BROWN), "enemy_harpy_black": build("enemy_harpy_black", BLACK),
          "enemy_harpy_white": build("enemy_harpy_white", WHITE), "monster_gargoyle": build("monster_gargoyle", STONE)}
