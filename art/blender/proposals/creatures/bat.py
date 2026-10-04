"""Giant bat: a furry body the size of a dog with a 2.4 m wingspan, big
ears, red eyes and fangs. Rigid parts: each wing is two membrane panels on
two bones. It is modeled at flying height (1 m); the game gives the real
height. Clips: idle (hovering), fly, attack (a swoop and bite) and die
(tumbles to the ground). Variants: brown, black vampire and pale cave bat.
"""

import math

from mathutils import Vector

import _parts as P
from _parts import X, Y, Z, Pose, hull, rock, seg, spike, ball, plate

H = 1.0   # Flying height of the body.

BROWN = P.palette(fur=0x6A4E3A, fur_dark=0x4A3628, skin=0x8A5A52, membrane=0x5A3A3A, eye=0xE0342A, tooth=0xF2EAD6)
BLACK = P.palette(fur=0x2A262E, fur_dark=0x1A181E, skin=0x4A2A36, membrane=0x6A1E2A, eye=0xFFD23A, tooth=0xF2EAD6)
PALE = P.palette(fur=0xD8D2C4, fur_dark=0xB8B0A0, skin=0xE0A8A0, membrane=0xC89088, eye=0xC8302A, tooth=0xFFFFFF)


def body(mb):
    rock(mb, (0, 0.02, H), (0.17, 0.27, 0.17), "fur", "body", count=18, seed=3)
    rock(mb, (0, -0.1, H + 0.04), (0.19, 0.16, 0.16), "fur_dark", "body", count=12, seed=5)      # Ruff.
    rock(mb, (0, -0.32, H + 0.06), (0.12, 0.13, 0.11), "fur", "head", count=14, seed=7)
    hull(mb, [(-0.05, -0.42, H + 0.06), (0.05, -0.42, H + 0.06), (-0.04, -0.47, H + 0.03), (0.04, -0.47, H + 0.03),
              (-0.05, -0.42, H - 0.01), (0.05, -0.42, H - 0.01), (0, -0.48, H + 0.07)], "skin", "head")   # Snout.
    for s in (-1, 1):
        plate(mb, [(s * 0.04, -0.3, H + 0.14), (s * 0.12, -0.27, H + 0.1), (s * 0.17, -0.3, H + 0.38)], 0.02, "skin",
              "head")
        ball(mb, (s * 0.055, -0.42, H + 0.09), 0.022, "eye", "head")
        spike(mb, (s * 0.025, -0.455, H + 0.0), (s * 0.028, -0.47, H - 0.07), 0.012, "tooth", "head")
        seg(mb, (s * 0.06, 0.2, H - 0.1), (s * 0.07, 0.32, H - 0.24), 0.025, 0.015, "skin", "feet", sides=4)
        for dx in (-0.02, 0.0, 0.02):
            spike(mb, (s * 0.07, 0.32, H - 0.24), (s * 0.07 + dx, 0.3, H - 0.31), 0.008, "tooth", "feet", sides=3)
        side = "L" if s > 0 else "R"
        sh, el = Vector((s * 0.12, -0.08, H + 0.05)), Vector((s * 0.65, -0.12, H + 0.1))
        tip, mid, back = Vector((s * 1.2, -0.02, H + 0.05)), Vector((s * 1.0, 0.32, H)), Vector((s * 0.6, 0.42, H))
        root = Vector((s * 0.1, 0.28, H - 0.02))
        plate(mb, [sh, el, back, root], 0.014, "membrane", f"wing.1.{side}")
        plate(mb, [el, tip, mid, back], 0.014, "membrane", f"wing.2.{side}")
        seg(mb, sh, el, 0.035, 0.026, "skin", f"wing.1.{side}", sides=5)
        for end in (tip, mid, back):
            seg(mb, el, end, 0.02, 0.01, "skin", f"wing.2.{side}", sides=4)
        spike(mb, el, el + Vector((s * 0.02, -0.1, 0.03)), 0.015, "tooth", f"wing.2.{side}", sides=3)
    plate(mb, [(-0.1, 0.26, H - 0.02), (0.1, 0.26, H - 0.02), (0.0, 0.5, H - 0.04)], 0.012, "membrane", "body")   # Tail.


def mech():
    bones = [("body", (0, 0.2, H), (0, -0.2, H), None),
             ("head", (0, -0.2, H + 0.03), (0, -0.46, H + 0.06), "body"),
             ("feet", (0, 0.18, H - 0.08), (0, 0.32, H - 0.26), "body")]
    for side, s in P.SIDES:
        bones += [(f"wing.1.{side}", (s * 0.12, -0.08, H + 0.05), (s * 0.65, -0.12, H + 0.1), "body"),
                  (f"wing.2.{side}", (s * 0.65, -0.12, H + 0.1), (s * 1.2, -0.02, H + 0.05), f"wing.1.{side}")]
    m = P.kit.Mech(bones)

    def flap(pose, phase, amp, mid=8.0, sweep=0.0):
        """Wings up and down; the outer panel trails behind the inner one."""
        for side, s in P.SIDES:
            pose.turn(f"wing.1.{side}", Y, -s * (mid + amp * math.sin(phase)))
            pose.turn(f"wing.2.{side}", Y, -s * (amp * 0.75 * math.sin(phase - 0.9) - 10.0))
            pose.turn(f"wing.1.{side}", Z, s * sweep)

    def idle(t):
        p = 2 * math.pi * t
        pose = Pose(m, (0, 0, -0.07 * math.sin(2 * p + 1.2)))
        pose.turn("body", X, -32.0 + 3.0 * math.sin(p))
        pose.turn("head", X, 26.0)
        pose.turn("head", Z, 12.0 * math.sin(p))
        pose.turn("feet", X, 20.0 + 8.0 * math.sin(2 * p))
        flap(pose, 2 * p, 38.0)
        return P.from_pose(pose)

    def fly(t):
        p = 2 * math.pi * t
        pose = Pose(m, (0, 0, -0.06 * math.sin(p + 1.2)))
        pose.turn("body", X, 6.0 + 3.0 * math.sin(p))
        pose.turn("head", X, -8.0)
        pose.turn("feet", X, -40.0)
        flap(pose, p, 46.0)
        return P.from_pose(pose)

    def attack(t):
        p = 2 * math.pi * t
        dive = P.pulse(t, 0.05, 0.4, 0.46, 0.75)
        bite = P.pulse(t, 0.36, 0.44, 0.48, 0.58)
        pose = Pose(m, (0, -0.55 * dive, -0.5 * dive))
        pose.turn("body", X, -32.0 * (1 - dive) + 34.0 * dive)
        pose.turn("head", X, 26.0 * (1 - dive) - 30.0 * dive + 26.0 * bite)
        pose.turn("feet", X, 20.0 - 50.0 * dive)
        for side, s in P.SIDES:
            pose.turn(f"wing.1.{side}", Y, -s * ((8.0 + 38.0 * math.sin(3 * p)) * (1 - dive) + 30.0 * dive))
            pose.turn(f"wing.2.{side}", Y, -s * ((28.0 * math.sin(3 * p - 0.9) - 10.0) * (1 - dive) - 20.0 * dive))
            pose.turn(f"wing.1.{side}", Z, s * 40.0 * dive)
        return P.from_pose(pose)

    def die(t):
        hit = P.pulse(t, 0.0, 0.1, 0.12, 0.3)
        fall = P.smooth((t - 0.1) / 0.6)
        land = P.smooth((t - 0.6) / 0.3)
        pose = Pose(m, (0.2 * fall, 0, -(H - 0.16) * fall * fall))
        pose.turn("body", X, -32.0 * (1 - fall) - 10.0 * hit)
        pose.turn("body", Y, 540.0 * fall * (1 - 0.5 * fall) * 0.667)      # Spins and ends on its back.
        pose.turn("head", X, 26.0 * (1 - fall) + 14.0 * land)
        for side, s in P.SIDES:
            fold = 55.0 * fall * (1 - land) + 10.0 * land
            pose.turn(f"wing.1.{side}", Y, -s * (8.0 + fold))
            pose.turn(f"wing.2.{side}", Y, -s * (-10.0 + fold * 1.4 - 30.0 * land))
        return P.from_pose(pose)

    m.clip("idle", 16 / P.FPS, idle)
    m.clip("fly", 12 / P.FPS, fly, speed=5.0)
    m.clip("attack", 1.2, attack)
    m.clip("die", 1.3, die, loops=False)
    return m


def build(name, colors, k=1.0):
    def make():
        mb = P.kit.begin()
        body(mb)
        P.save(mb, name, colors, mech(), k)
    return make


MODELS = {"enemy_bat_giant": build("enemy_bat_giant", BROWN), "enemy_bat_vampire": build("enemy_bat_vampire", BLACK),
          "enemy_bat_cave": build("enemy_bat_cave", PALE), "animal_bat": build("animal_bat", BROWN, k=0.2)}
