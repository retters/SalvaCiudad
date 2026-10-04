"""Ghost and wraith: a hooded, ragged robe floating 20 cm above the ground,
with no legs: a dark void for a face with two glowing eyes and bony hands
coming out of wide sleeves. Rigid panels on a few bones (body, head, two
arm bones a side, two robe segments that trail behind). Clips: idle (bobs
and sways), walk (glides leaning forward), attack (both claws reach out and
rake) and die (the empty robe drops in a heap). Variants: pale ghost, black
wraith with red eyes, and a lich with a crown, a staff and gold trim."""

import math

from mathutils import Vector

import _parts as P
from _parts import X, Y, Z, Pose, hull, bar, rock, seg, spike, ball, box, plate

PALE = P.palette(robe=0xC9D6DC, robe_dark=0x9FB2BC, void=0x1A2230, eye=0x8CF0FF, bone=0xE6E2D2, trim=0x9FB2BC,
                 gem=0x8CF0FF, wood=0x6B5A4A)
WRAITH = P.palette(robe=0x2E2A36, robe_dark=0x1E1B24, void=0x08070A, eye=0xFF4A2A, bone=0xB8B2A2, trim=0x4A1E2A,
                   gem=0xFF4A2A, wood=0x3A2E28)
LICH = P.palette(robe=0x4A2A5E, robe_dark=0x341E44, void=0x0E0A12, eye=0x7CFF8A, bone=0xE6DCC2, trim=0xD9B24A,
                 gem=0x7CFF8A, wood=0x3A2E28)

SHOULDER, ELBOW, WRIST, HAND = (0.26, 0.0, 1.52), (0.36, -0.08, 1.3), (0.38, -0.3, 1.2), (0.38, -0.42, 1.18)


def ring(z, rx, ry, y=0.0, n=6, phase=0.0):
    return [(math.cos(phase + i * math.tau / n) * rx, y + math.sin(phase + i * math.tau / n) * ry, z) for i in range(n)]


def body(mb, lich=False):
    # Torso: two stacked faceted cones.
    hull(mb, ring(1.6, 0.2, 0.15) + ring(1.42, 0.3, 0.2) + ring(1.05, 0.27, 0.2), "robe", "body")
    hull(mb, ring(1.08, 0.29, 0.22) + ring(0.7, 0.36, 0.3, 0.06), "robe_dark", "robe.1")
    hull(mb, ring(0.72, 0.37, 0.31, 0.06) + ring(0.42, 0.33, 0.3, 0.14), "robe", "robe.2")
    for i in range(7):                                      # Ragged strips at the hem.
        a = i * math.tau / 7 + 0.3
        c, s = math.cos(a), math.sin(a)
        top = Vector((c * 0.31, 0.14 + s * 0.28, 0.44))
        plate(mb, [top + Vector((-s * 0.09, c * 0.09, 0)), top + Vector((s * 0.09, -c * 0.09, 0)),
                   top + Vector((c * 0.03, s * 0.03 + 0.05, -0.2 - 0.06 * (i % 3)))], 0.02,
              "robe_dark" if i % 2 else "robe", "robe.2")
    bar(mb, (0, -0.2, 1.3), (0, -0.21, 0.6), 0.1, 0.02, "trim", "body", taper=0.8)          # A stole down the front.
    # Hood with a void inside, and the eyes.
    hull(mb, ring(1.62, 0.17, 0.17, 0.02) + ring(1.8, 0.2, 0.21, 0.0) + [(0, 0.06, 1.98), (0, 0.2, 1.9)], "robe_dark",
         "head")
    box(mb, (0, -0.15, 1.78), (0.24, 0.1, 0.24), "void", "head")
    for s in (-1, 1):
        ball(mb, (s * 0.055, -0.2, 1.8), 0.022, "eye", "head")
    if lich:
        for i in range(6):                                  # A crown.
            a = i * math.tau / 6
            p = Vector((math.cos(a) * 0.19, math.sin(a) * 0.2, 1.93))
            spike(mb, p, p + Vector((math.cos(a) * 0.03, math.sin(a) * 0.03, 0.13)), 0.035, "trim", "head")
        ball(mb, (0, -0.2, 1.97), 0.03, "gem", "head")
    for side, s in P.SIDES:
        def m(p):
            return Vector((p[0] * s, p[1], p[2]))
        rock(mb, m(SHOULDER), (0.12, 0.11, 0.1), "robe_dark", f"upper_arm.{side}", count=10, seed=4)
        seg(mb, m(SHOULDER), m(ELBOW), 0.085, 0.1, "robe", f"upper_arm.{side}")
        seg(mb, m(ELBOW), m(WRIST), 0.1, 0.14, "robe_dark", f"lower_arm.{side}")           # The sleeve widens.
        seg(mb, m(WRIST) + Vector((0, 0.03, 0)), m(HAND), 0.03, 0.035, "bone", f"hand.{side}", sides=5)
        for dx, dz in ((-0.035, 0.0), (0.0, 0.02), (0.035, 0.0), (0.0, -0.035)):
            spike(mb, m(HAND) + Vector((dx * 0.5, 0, dz * 0.5)), m(HAND) + Vector((dx, -0.13, dz - 0.03)), 0.012,
                  "bone", f"hand.{side}")
    if lich:                                                # A staff in the right hand, with a gem.
        h = Vector((-HAND[0], HAND[1] - 0.04, HAND[2]))
        seg(mb, h + Vector((0, 0, -0.75)), h + Vector((0, 0, 0.75)), 0.022, 0.026, "wood", "hand.R", sides=5)
        for a in range(3):
            d = Vector((math.cos(a * 2.09), math.sin(a * 2.09), 0))
            spike(mb, h + Vector((0, 0, 0.72)) + d * 0.02, h + Vector((0, 0, 0.92)) + d * 0.09, 0.02, "trim", "hand.R")
        rock(mb, h + Vector((0, 0, 0.88)), (0.06, 0.06, 0.08), "gem", "hand.R", count=10, seed=2)


def mech(info, lich=False):
    bones = [("body", (0, 0, 1.05), (0, 0, 1.6), None), ("head", (0, 0, 1.6), (0, 0, 1.95), "body"),
             ("robe.1", (0, 0.02, 1.08), (0, 0.06, 0.72), "body"), ("robe.2", (0, 0.06, 0.72), (0, 0.14, 0.4), "robe.1")]
    for side, s in P.SIDES:
        def m(p):
            return (p[0] * s, p[1], p[2])
        bones += [(f"upper_arm.{side}", m(SHOULDER), m(ELBOW), "body"),
                  (f"lower_arm.{side}", m(ELBOW), m(WRIST), f"upper_arm.{side}"),
                  (f"hand.{side}", m(WRIST), m(HAND), f"lower_arm.{side}")]
    m_ = P.kit.Mech(bones)

    def trail(pose, back, sway):
        pose.turn("robe.1", X, back * 0.6)
        pose.turn("robe.2", X, back * 0.6)
        pose.turn("robe.1", Y, sway)
        pose.turn("robe.2", Y, sway * 1.2)

    def arms(pose, lift=0.0, spread=0.0, bob=0.0):
        for side, s in P.SIDES:
            pose.turn(f"upper_arm.{side}", X, -lift + bob * s)
            pose.turn(f"upper_arm.{side}", Y, spread * s)
            pose.turn(f"hand.{side}", X, 10.0 * math.sin(bob * 0.2))

    def idle(t):
        p = 2 * math.pi * t
        pose = Pose(m_, (0.03 * math.sin(p), 0, 0.04 + 0.04 * math.sin(2 * p)))
        pose.turn("body", X, 3.0 * math.sin(2 * p + 0.5))
        pose.turn("head", Z, 14.0 * math.sin(p))
        trail(pose, 6.0 * math.sin(2 * p - 0.8), 4.0 * math.sin(p - 0.6))
        arms(pose, 4.0 * math.sin(2 * p), 4.0, 5.0 * math.sin(p))
        return P.from_pose(pose)

    def glide(t):
        p = 2 * math.pi * t
        pose = Pose(m_, (0.02 * math.sin(p), 0, 0.04 * math.sin(2 * p)))
        pose.turn("body", X, 16.0 + 2.0 * math.sin(2 * p))
        pose.turn("head", X, -12.0)
        trail(pose, 22.0 + 6.0 * math.sin(2 * p - 0.8), 9.0 * math.sin(p - 0.6))
        arms(pose, 24.0 + 5.0 * math.sin(2 * p), 6.0, 6.0 * math.sin(p))
        return P.from_pose(pose)

    def attack(t):
        w = P.pulse(t, 0.0, 0.32, 0.38, 0.48)
        s = P.pulse(t, 0.38, 0.48, 0.56, 0.95)
        pose = Pose(m_, (0, 0.08 * w - 0.3 * s, 0.1 * w - 0.05 * s))
        pose.turn("body", X, -12.0 * w + 26.0 * s)
        pose.turn("head", X, 8.0 * w - 20.0 * s)
        trail(pose, -10.0 * w + 30.0 * s, 0.0)
        for side, sx in P.SIDES:
            pose.turn(f"upper_arm.{side}", X, -70.0 * w - 30.0 * s)
            pose.turn(f"upper_arm.{side}", Y, (40.0 * w - 14.0 * s) * sx)
            pose.turn(f"lower_arm.{side}", X, -20.0 * w + 26.0 * s)
            pose.turn(f"hand.{side}", X, -30.0 * w + 40.0 * s)
        return P.from_pose(pose)

    def cast(t):
        """The lich raises the staff and the gem hand."""
        up = P.pulse(t, 0.0, 0.3, 0.7, 1.0)
        shake = math.sin(2 * math.pi * 6 * t) * P.pulse(t, 0.3, 0.35, 0.65, 0.7)
        pose = Pose(m_, (0, 0, 0.12 * up + 0.01 * shake))
        pose.turn("body", X, -8.0 * up)
        pose.turn("head", X, -10.0 * up)
        trail(pose, -8.0 * up, 4.0 * shake)
        pose.turn("upper_arm.R", X, -75.0 * up)
        pose.turn("lower_arm.R", X, 50.0 * up)
        pose.turn("hand.R", X, 25.0 * up + 4.0 * shake)
        pose.turn("upper_arm.L", X, -50.0 * up)
        pose.turn("upper_arm.L", Y, 30.0 * up)
        pose.turn("hand.L", X, -30.0 * up + 10.0 * shake)
        return P.from_pose(pose)

    m_.clip("idle", 3.0, idle)
    m_.clip("walk", 1.6, glide)
    m_.clip("attack", 1.1, attack)
    if lich:
        m_.clip("cast", 2.0, cast)
    m_.clip("die", 1.4, lambda t: P.collapse(m_, t, info, spread=0.25, seed=9, rest=0.5), loops=False)
    return m_


def build(name, colors, lich=False):
    def make():
        mb = P.kit.begin()
        body(mb, lich)
        P.kit.save(mb, P.FAMILY, name, colors, mech=mech(P.piece_info(mb), lich))
    return make


MODELS = {"enemy_ghost": build("enemy_ghost", PALE), "enemy_wraith": build("enemy_wraith", WRAITH),
          "enemy_lich": build("enemy_lich", LICH, lich=True)}
