"""Frog: a small ambient critter, 0.2 m long so it reads from the game's
camera. A wedge body with bulging eyes, a pale throat that pulses, short
front legs and long hind legs folded in a Z. Rigid parts. Clips: idle (the
throat pulses, it blinks its weight from side to side), walk (a hop: the
hind legs unfold behind it in the air) and die (flips belly up). Variants:
green frog, brown toad and a blue poison frog."""

import math

from mathutils import Vector

import _parts as P
from _parts import X, Y, Z, Pose, hull, ball, bar, seg

K = 0.2
GREEN = P.palette(skin=0x6CA83A, skin_dark=0x4A8A2A, belly=0xE8E2A8, eye=0xF2D23A, pupil=0x151012)
TOAD = P.palette(skin=0x8A6A42, skin_dark=0x6A4E30, belly=0xD8C8A0, eye=0xE8A83A, pupil=0x151012)
POISON = P.palette(skin=0x2E6AD8, skin_dark=0x1A1A24, belly=0x8AB8F0, eye=0x151012, pupil=0x151012)

FRONT = [(0.24, -0.2, 0.22), (0.33, -0.24, 0.09), (0.36, -0.4, 0.0)]
HIND = [(0.2, 0.3, 0.17), (0.42, 0.04, 0.14), (0.4, 0.42, 0.06), (0.5, 0.08, 0.0)]


def V(p, s=1.0):
    return Vector((p[0] * s, p[1], p[2])) * K


def body(mb):
    hull(mb, [V(p) for p in ((-0.3, -0.25, 0.14), (0.3, -0.25, 0.14), (-0.26, 0.42, 0.06), (0.26, 0.42, 0.06),
                             (-0.2, -0.5, 0.2), (0.2, -0.5, 0.2), (0, -0.56, 0.24), (-0.24, -0.2, 0.42),
                             (0.24, -0.2, 0.42), (-0.18, 0.4, 0.22), (0.18, 0.4, 0.22), (0, 0.48, 0.12),
                             (-0.16, -0.48, 0.34), (0.16, -0.48, 0.34))], "skin", "body")
    hull(mb, [V(p) for p in ((-0.2, -0.46, 0.2), (0.2, -0.46, 0.2), (-0.22, -0.2, 0.15), (0.22, -0.2, 0.15),
                             (0, -0.4, 0.1), (0, -0.2, 0.08))], "belly", "throat")
    for s in (-1, 1):
        ball(mb, V((0.15, -0.3, 0.42), s), 0.085 * K, "skin_dark", "body")
        ball(mb, V((0.19, -0.33, 0.43), s), 0.055 * K, "eye", "body")
        ball(mb, V((0.225, -0.35, 0.43), s), 0.028 * K, "pupil", "body")
        ball(mb, V((0.12, 0.1, 0.36), s), 0.05 * K, "skin_dark", "body", scale=(1, 1.6, 0.5))       # A spot.
        side = "L" if s > 0 else "R"
        a, b, c = (V(p, s) for p in FRONT)
        seg(mb, a, b, 0.05 * K, 0.035 * K, "skin", f"arm.{side}", sides=5)
        hull(mb, [b + Vector(o) * K for o in ((-0.03, 0.02, 0.0), (0.03, 0.02, 0.0), (-0.08 * s, -0.14, -0.085),
                                              (0.02 * s, -0.17, -0.085), (0.08 * s, -0.12, -0.085), (0, -0.02, 0.03))],
             "skin_dark", f"arm.{side}")
        h, k, an, t = (V(p, s) for p in HIND)
        seg(mb, h, k, 0.08 * K, 0.055 * K, "skin", f"thigh.{side}", sides=5)
        seg(mb, k, an, 0.055 * K, 0.035 * K, "skin_dark", f"shin.{side}", sides=5)
        hull(mb, [an + Vector(o) * K for o in ((-0.03, 0.0, -0.03), (0.03, 0.0, -0.03), (0, 0, 0.02))]
             + [t + Vector(o) * K for o in ((-0.07, -0.02, 0.0), (0.07, -0.02, 0.0), (0, -0.08, 0.0), (0, 0.0, 0.02))],
             "skin", f"foot.{side}")


def mech():
    bones = [("body", tuple(V((0, 0.4, 0.14))), tuple(V((0, -0.5, 0.26))), None),
             ("throat", tuple(V((0, -0.2, 0.14))), tuple(V((0, -0.46, 0.16))), "body")]
    for side, s in P.SIDES:
        h, k, an, t = (tuple(V(p, s)) for p in HIND)
        a, b, c = (tuple(V(p, s)) for p in FRONT)
        bones += [(f"arm.{side}", a, b, "body"), (f"thigh.{side}", h, k, "body"), (f"shin.{side}", k, an, f"thigh.{side}"),
                  (f"foot.{side}", an, t, f"shin.{side}")]
    m = P.kit.Mech(bones)

    def hind(turns, e):
        """Unfolds the hind legs backward by e (0 folded, 1 straight)."""
        for side, s in P.SIDES:
            turns[f"thigh.{side}"] = [(Z, 141.0 * e * s)]
            turns[f"shin.{side}"] = [(Z, -144.0 * e * s)]
            turns[f"foot.{side}"] = [(Z, 166.0 * e * s), (X, -30.0 * e)]

    def idle(t):
        p = 2 * math.pi * t
        pulse = 0.5 + 0.5 * math.sin(6 * p)
        turns = {"body": [(Z, 3.0 * math.sin(p)), (X, -0.8 * (1 + math.sin(2 * p)))]}
        return turns, {"throat": (0, -0.01 * K * pulse, -0.045 * K * pulse)}

    def hop(t):
        squat = P.pulse(t, 0.0, 0.1, 0.14, 0.24)
        u = max(0.0, min(1.0, (t - 0.18) / 0.5))
        air = math.sin(math.pi * u)
        ext = P.pulse(t, 0.16, 0.3, 0.42, 0.68)
        tilt = -14.0 * squat - 24.0 * air * (1 - u) + 16.0 * air * u
        turns = {"body": [(X, tilt)]}
        hind(turns, ext)
        for side, s in P.SIDES:
            turns[f"arm.{side}"] = [(X, 40.0 * air * (1 - u) - 30.0 * air * u)]
        dz = 0.5 * K * abs(math.sin(math.radians(tilt))) + 0.01 * K
        return turns, {"root": (0, 0, -0.03 * K * squat + 0.55 * K * air + dz * (1 - air))}

    def bite(t):
        w = P.pulse(t, 0.0, 0.3, 0.36, 0.46)
        b = P.pulse(t, 0.36, 0.46, 0.54, 0.95)
        tilt = -12.0 * w + 9.0 * b
        turns = {"body": [(X, tilt)]}
        hind(turns, 0.5 * b)
        dz = 0.95 * K * math.sin(math.radians(max(0.0, tilt))) + 0.12 * K * math.sin(math.pi * b)
        return turns, {"root": (0, (0.08 * w - 0.5 * b) * K, dz), "throat": (0, 0, -0.04 * K * w)}

    def die(t):
        jump = math.sin(math.pi * min(1.0, t / 0.6))
        roll = P.smooth((t - 0.1) / 0.5)
        turns = {"body": [(Y, 180.0 * roll)]}
        hind(turns, 0.45 * roll)
        for side, s in P.SIDES:
            turns[f"arm.{side}"] = [(Y, -40.0 * roll * s)]
        return turns, {"root": (0, 0, 0.5 * K * jump + 0.26 * K * roll), "throat": (0, 0, -0.02 * K * roll)}

    m.clip("idle", 2.0, idle)
    m.clip("walk", 0.9, hop)
    m.clip("attack", 0.9, bite)
    m.clip("die", 1.0, die, loops=False)
    return m


def build(name, colors, k=0.2):
    def make():
        global K
        K = k
        mb = P.kit.begin()
        body(mb)
        P.kit.save(mb, P.FAMILY, name, colors, mech=mech())
    return make


MODELS = {"animal_frog": build("animal_frog", GREEN), "animal_toad": build("animal_toad", TOAD),
          "animal_frog_poison": build("animal_frog_poison", POISON),
          "monster_giant_toad": build("monster_giant_toad", dict(TOAD, **P.palette(skin=0x6A7A42, skin_dark=0x4A5A30)),
                                      k=1.4)}
