"""Giant scorpion: a 1.6 m armored body on eight legs, two big pincers and
a segmented tail curled over its back with a sting. Rigid plates; the legs
are posed by inverse kinematics. Clips: idle, walk, attack (the sting
strikes forward over the head while the pincers snap) and die (legs fold,
tail and pincers drop). Variants: sand, black and red."""

import math

from mathutils import Quaternion, Vector

import _parts as P
from _parts import X, Y, Z, Pose, hull, rock, seg, spike, ball

ANGLES = (40.0, 12.0, -14.0, -40.0)
HIP_Y = (-0.2, 0.0, 0.2, 0.4)
LEGS = []
for side, s in P.SIDES:
    for i, (a, y) in enumerate(zip(ANGLES, HIP_Y)):
        d = Vector((math.cos(math.radians(a)) * s, -math.sin(math.radians(a)), 0.0))
        hip = Vector((0.24 * s, y, 0.3))
        tip = Vector((hip.x + d.x * 0.62, hip.y + d.y * 0.62, 0.0))
        LEGS.append((f"{side}{i + 1}", hip, hip + d * 0.3 + Vector((0, 0, 0.26)), tip + Vector((0, 0, 0.08)), tip, d))

# Tail joints, from the body up and forward over the back.
TAIL = [Vector(p) for p in ((0, 0.72, 0.34), (0, 1.0, 0.5), (0, 1.14, 0.8), (0, 1.02, 1.12), (0, 0.74, 1.3),
                            (0, 0.44, 1.28))]
STING = Vector((0, 0.2, 1.08))
ARM = [(0.2, -0.36, 0.3), (0.5, -0.62, 0.32), (0.44, -0.98, 0.34), (0.4, -1.3, 0.34)]

SAND = P.palette(shell=0xC9A45E, shell_dark=0x9A7438, joint=0x6B4A28, eye=0x1A1412, sting=0x3A1E14)
BLACK = P.palette(shell=0x34303A, shell_dark=0x222028, joint=0x5A4E66, eye=0xE0342A, sting=0xC8302A)
RED = P.palette(shell=0xB8402A, shell_dark=0x8A2A1E, joint=0x4A1E18, eye=0xF2D23A, sting=0x2A1410)


def body(mb):
    # Head plate and five body plates, each a little narrower.
    hull(mb, [(-0.26, -0.44, 0.24), (0.26, -0.44, 0.24), (-0.3, -0.1, 0.22), (0.3, -0.1, 0.22), (-0.2, -0.4, 0.4),
              (0.2, -0.4, 0.4), (-0.24, -0.1, 0.44), (0.24, -0.1, 0.44)], "shell", "body")
    for i in range(5):
        y0, w = -0.1 + i * 0.165, 0.31 - 0.035 * i
        hull(mb, [(-w, y0, 0.2), (w, y0, 0.2), (-w, y0 + 0.18, 0.2), (w, y0 + 0.18, 0.2), (-w * 0.8, y0, 0.45 - 0.01 * i),
                  (w * 0.8, y0, 0.45 - 0.01 * i), (-w * 0.75, y0 + 0.18, 0.42 - 0.01 * i),
                  (w * 0.75, y0 + 0.18, 0.42 - 0.01 * i)], "shell" if i % 2 else "shell_dark", "body")
    for s in (-1, 1):
        ball(mb, (s * 0.07, -0.4, 0.41), 0.03, "eye", "body")
        spike(mb, (s * 0.06, -0.44, 0.28), (s * 0.04, -0.56, 0.2), 0.035, "joint", "body")       # Mouth parts.
    for i, (a, b) in enumerate(zip(TAIL, TAIL[1:])):
        seg(mb, a, b, 0.11 - 0.008 * i, 0.1 - 0.008 * i, "shell" if i % 2 else "shell_dark", f"tail.{i + 1}", sides=6)
        ball(mb, a, 0.105 - 0.008 * i, "joint", f"tail.{i + 1}")
    rock(mb, TAIL[-1].lerp(STING, 0.3), (0.1, 0.12, 0.1), "shell_dark", "sting", count=10, seed=2)
    spike(mb, TAIL[-1].lerp(STING, 0.5), STING + Vector((0, -0.12, -0.2)), 0.05, "sting", "sting", sides=5)
    for side, s in P.SIDES:
        a0, a1, a2, a3 = (Vector((p[0] * s, p[1], p[2])) for p in ARM)
        seg(mb, a0, a1, 0.07, 0.06, "shell_dark", f"arm.1.{side}")
        seg(mb, a1, a2, 0.06, 0.08, "shell", f"arm.2.{side}")
        ball(mb, a1, 0.075, "joint", f"arm.2.{side}")
        # The claw: a fat palm, a fixed finger and a moving one.
        hull(mb, [a2 + Vector(o) for o in ((-0.1, 0.0, -0.07), (0.1, 0.0, -0.07), (-0.1, 0.0, 0.08), (0.1, 0.0, 0.08),
                                           (-0.12, -0.18, -0.06), (0.12, -0.18, -0.06), (-0.11, -0.18, 0.07),
                                           (0.11, -0.18, 0.07))], "shell", f"arm.2.{side}")
        spike(mb, a2 + Vector((s * 0.07, -0.16, 0.0)), a3 + Vector((s * 0.04, -0.06, 0.0)), 0.06, "shell_dark",
              f"arm.2.{side}", sides=5)
        spike(mb, a2 + Vector((-s * 0.07, -0.16, 0.0)), a3 + Vector((-s * 0.01, -0.06, 0.0)), 0.05, "shell_dark",
              f"pincer.{side}", sides=5)
    for name, hip, knee, ankle, tip, d in LEGS:
        seg(mb, hip, knee, 0.05, 0.04, "shell_dark", f"leg_upper.{name}", sides=5)
        ball(mb, knee, 0.05, "joint", f"leg_lower.{name}")
        seg(mb, knee, ankle, 0.04, 0.025, "shell", f"leg_lower.{name}", sides=5)
        spike(mb, ankle + Vector((0, 0, 0.02)), tip, 0.028, "joint", f"foot.{name}", sides=4)


def mech():
    bones = [("body", (0, 0.6, 0.3), (0, -0.4, 0.3), None)]
    parent = "body"
    for i, (a, b) in enumerate(zip(TAIL, TAIL[1:])):
        bones.append((f"tail.{i + 1}", tuple(a), tuple(b), parent))
        parent = f"tail.{i + 1}"
    bones.append(("sting", tuple(TAIL[-1]), tuple(STING), parent))
    for side, s in P.SIDES:
        a0, a1, a2, a3 = ((p[0] * s, p[1], p[2]) for p in ARM)
        bones += [(f"arm.1.{side}", a0, a1, "body"), (f"arm.2.{side}", a1, a2, f"arm.1.{side}"),
                  (f"pincer.{side}", (a2[0] - s * 0.07, a2[1] - 0.16, a2[2]), a3, f"arm.2.{side}")]
    for name, hip, knee, ankle, tip, d in LEGS:
        bones += [(f"leg_upper.{name}", hip, knee, "body"),
                  (f"leg_lower.{name}", knee, ankle, f"leg_upper.{name}"),
                  (f"foot.{name}", ankle, tip, f"leg_lower.{name}")]
    m = P.kit.Mech(bones)
    frames, duty, stride, lift = 14, 0.6, 0.26, 0.1
    speed = stride * P.FPS / (duty * frames)
    phase = {name: (0.0 if (int(name[1]) % 2 == 1) == (name[0] == "L") else 0.5) for name, *_ in LEGS}
    n_tail = len(TAIL) - 1

    def legs(pose, targets=None):
        for name, hip, knee, ankle, tip, d in LEGS:
            pose.limb(f"leg_upper.{name}", f"leg_lower.{name}", (targets or {}).get(name, ankle),
                      Vector((d.x * 0.4, d.y * 0.4, 1.0)))
            pose.set_world(f"foot.{name}", Quaternion())

    def tail(pose, curl, side=0.0):
        """curl > 0 straightens the tail forward over the head (a strike)."""
        for i in range(n_tail):
            pose.turn(f"tail.{i + 1}", X, curl)
            pose.turn(f"tail.{i + 1}", Z, side)
        pose.turn("sting", X, curl * 1.5)

    def claws(pose, open_deg, spread=0.0, lift=0.0):
        for side, s in P.SIDES:
            pose.turn(f"pincer.{side}", Z, -open_deg * s)
            pose.turn(f"arm.1.{side}", Z, spread * s)
            pose.turn(f"arm.1.{side}", X, -lift)

    def idle(t):
        p = 2 * math.pi * t
        pose = Pose(m, (0, 0, 0.015 * math.sin(2 * p)))
        tail(pose, 2.0 * math.sin(2 * p), 3.0 * math.sin(p))
        claws(pose, 14.0 * P.pulse(t, 0.3, 0.38, 0.42, 0.5) + 14.0 * P.pulse(t, 0.55, 0.63, 0.67, 0.75),
              4.0 * math.sin(p), 3.0 * math.sin(2 * p))
        legs(pose)
        return P.from_pose(pose)

    def walk(t):
        p = 2 * math.pi * t
        pose = Pose(m, (0, 0, 0.01 * math.cos(2 * p)))
        pose.turn("body", Z, 2.0 * math.sin(p))
        tail(pose, 2.0 * math.cos(2 * p), -4.0 * math.sin(p))
        claws(pose, 6.0, 5.0 * math.sin(p), 4.0)
        targets = {}
        for name, hip, knee, ankle, tip, d in LEGS:
            dy, dz, u = P.step(t, phase[name], duty, stride, lift)
            targets[name] = ankle + Vector((0, dy, dz))
        legs(pose, targets)
        return P.from_pose(pose)

    def attack(t):
        w = P.pulse(t, 0.0, 0.3, 0.36, 0.46)
        s = P.pulse(t, 0.36, 0.46, 0.52, 0.95)
        pose = Pose(m, (0, 0.06 * w - 0.16 * s, -0.03 * s))
        pose.turn("body", X, -5.0 * w + 9.0 * s)
        # The whole tail tips forward from its base while its end uncurls,
        # so the sting comes down in front of the head.
        for i, (back, strike) in enumerate(((-8.0, 34.0), (-6.0, 16.0), (0.0, -4.0), (4.0, -14.0), (4.0, -16.0))):
            pose.turn(f"tail.{i + 1}", X, back * w + strike * s)
        pose.turn("sting", X, 6.0 * w + 14.0 * s)
        claws(pose, 30.0 * w - 4.0 * s, 16.0 * w - 12.0 * s, 10.0 * w + 6.0 * s)
        legs(pose)
        return P.from_pose(pose)

    def die(t):
        shake = math.sin(45 * t) * (1 - P.smooth(t / 0.35))
        a = P.smooth((t - 0.2) / 0.6)
        pose = Pose(m, (0, 0, -0.1 * a))
        pose.turn("body", Y, 4.0 * shake + 6.0 * a)
        for i in range(n_tail):                       # The tail falls back and lies behind the body.
            pose.turn(f"tail.{i + 1}", X, (-30.0 if i == 0 else -36.0) * a)
        pose.turn("sting", X, -30.0 * a)
        claws(pose, 20.0 * a, -8.0 * a, -10.0 * a + 6.0 * shake)
        for name, hip, knee, ankle, tip, d in LEGS:
            hinge = d.cross(Vector((0, 0, 1)))
            pose.turn(f"leg_upper.{name}", hinge, 30.0 * a + 5.0 * shake)
            pose.turn(f"leg_lower.{name}", hinge, -70.0 * a)
        return P.from_pose(pose)

    m.clip("idle", 3.0, idle)
    m.clip("walk", frames / P.FPS, walk, speed=speed)
    m.clip("attack", 1.0, attack)
    m.clip("die", 1.4, die, loops=False)
    return m


def build(name, colors, k=1.0):
    def make():
        mb = P.kit.begin()
        body(mb)
        P.save(mb, name, colors, mech(), k)
    return make


MODELS = {"enemy_scorpion": build("enemy_scorpion", SAND), "enemy_scorpion_black": build("enemy_scorpion_black", BLACK),
          "enemy_scorpion_red": build("enemy_scorpion_red", RED),
          "animal_scorpion": build("animal_scorpion", SAND, k=0.12)}
