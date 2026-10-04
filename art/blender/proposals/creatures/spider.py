"""Giant spider: a 1.5 m body on eight jointed legs spanning 2.6 m, eight
red eyes, two fangs and a mark on the abdomen. Rigid segments; the legs
are posed by inverse kinematics so the feet stay planted. Clips: idle,
walk, attack (rears up and strikes with the front legs and fangs) and die
(rolls on its back and curls its legs). Variants: black, forest brown and
pale cave spider."""

import math

from mathutils import Quaternion, Vector

import _parts as P
from _parts import X, Y, Z, Pose, hull, rock, seg, spike, ball

ANGLES = (55.0, 20.0, -15.0, -50.0)      # Each leg's direction, degrees from +X toward the front.
HIP_Y = (-0.3, -0.12, 0.06, 0.24)
LEGS = []                                 # (name, hip, knee, ankle, tip, outward direction)
for side, s in P.SIDES:
    for i, (a, y) in enumerate(zip(ANGLES, HIP_Y)):
        d = Vector((math.cos(math.radians(a)) * s, -math.sin(math.radians(a)), 0.0))
        hip = Vector((0.24 * s, y, 0.48))
        tip = Vector((hip.x + d.x * 1.05, hip.y + d.y * 1.05, 0.0))
        LEGS.append((f"{side}{i + 1}", hip, hip + d * 0.45 + Vector((0, 0, 0.5)), tip + Vector((0, 0, 0.1)) - d * 0.03,
                     tip, d))

BLACK = P.palette(body=0x26222C, body_light=0x3A3442, leg=0x2E2934, joint=0x5A4E66, eye=0xE0342A, mark=0xD23A2A,
                  fang=0xE6DCC2)
BROWN = P.palette(body=0x6A4A2E, body_light=0x86623E, leg=0x5A3E28, joint=0x9A7A4A, eye=0x1A1412, mark=0xE0B84A,
                  fang=0x2A1E18)
PALE = P.palette(body=0xC9CDD2, body_light=0xE2E5E8, leg=0xB4B9C0, joint=0x8FA0B4, eye=0x54C8E8, mark=0x6FA8D8,
                 fang=0x4A5868)


def body(mb):
    rock(mb, (0, -0.12, 0.5), (0.3, 0.38, 0.2), "body_light", "body", count=18, seed=4)
    rock(mb, (0, 0.66, 0.62), (0.44, 0.52, 0.4), "body", "abdomen", count=26, seed=9)
    # The mark: an hourglass on top of the abdomen.
    for y0, y1 in ((0.42, 0.62), (0.82, 0.62)):
        hull(mb, [(-0.13, y0, 0.98), (0.13, y0, 0.98), (0, y1, 1.04), (-0.1, y0, 1.0), (0.1, y0, 1.0),
                  (0, y1, 1.0)], "mark", "abdomen")
    spike(mb, (0, 1.12, 0.6), (0, 1.26, 0.52), 0.07, "body_light", "abdomen", sides=5)    # Spinneret.
    # Eyes: two big ones in front, smaller ones around.
    for x, y, z, r in ((0.07, -0.47, 0.57, 0.045), (0.17, -0.41, 0.6, 0.03), (0.12, -0.38, 0.67, 0.025),
                       (0.23, -0.32, 0.6, 0.022)):
        for s in (-1, 1):
            ball(mb, (s * x, y, z), r, "eye", "body")
    for side, s in P.SIDES:
        seg(mb, (s * 0.09, -0.44, 0.44), (s * 0.08, -0.52, 0.34), 0.06, 0.045, "leg", f"fang.{side}", sides=5)
        spike(mb, (s * 0.08, -0.52, 0.35), (s * 0.04, -0.54, 0.16), 0.035, "fang", f"fang.{side}", sides=4)
        seg(mb, (s * 0.2, -0.4, 0.44), (s * 0.24, -0.62, 0.3), 0.035, 0.02, "joint", "body", sides=4)   # Palps.
    for name, hip, knee, ankle, tip, d in LEGS:
        seg(mb, hip, knee, 0.065, 0.05, "leg", f"leg_upper.{name}", sides=5)
        ball(mb, knee, 0.068, "joint", f"leg_lower.{name}")
        seg(mb, knee, ankle, 0.05, 0.028, "leg", f"leg_lower.{name}", sides=5)
        ball(mb, hip, 0.075, "joint", f"leg_upper.{name}")
        spike(mb, ankle + Vector((0, 0, 0.02)), tip, 0.03, "joint", f"foot.{name}", sides=4)


def mech():
    bones = [("body", (0, 0.25, 0.5), (0, -0.45, 0.5), None),
             ("abdomen", (0, 0.2, 0.55), (0, 1.0, 0.62), "body")]
    for side, s in P.SIDES:
        bones.append((f"fang.{side}", (s * 0.09, -0.44, 0.44), (s * 0.06, -0.53, 0.2), "body"))
    for name, hip, knee, ankle, tip, d in LEGS:
        bones += [(f"leg_upper.{name}", hip, knee, "body"),
                  (f"leg_lower.{name}", knee, ankle, f"leg_upper.{name}"),
                  (f"foot.{name}", ankle, tip, f"leg_lower.{name}")]
    m = P.kit.Mech(bones)
    frames, duty, stride, lift = 16, 0.6, 0.36, 0.16
    speed = stride * P.FPS / (duty * frames)
    # Alternating tetrapods: L1 R2 L3 R4 step together, then the other four.
    phase = {name: (0.0 if (int(name[1]) % 2 == 1) == (name[0] == "L") else 0.5) for name, *_ in LEGS}

    def legs(pose, targets=None):
        for name, hip, knee, ankle, tip, d in LEGS:
            at = (targets or {}).get(name, ankle)
            pose.limb(f"leg_upper.{name}", f"leg_lower.{name}", at, Vector((d.x * 0.4, d.y * 0.4, 1.0)))
            pose.set_world(f"foot.{name}", Quaternion())

    def idle(t):
        p = 2 * math.pi * t
        pose = Pose(m, (0, 0, 0.03 * math.sin(2 * p)))
        pose.turn("body", Z, 3.0 * math.sin(p))
        pose.turn("abdomen", X, 4.0 * math.sin(2 * p))
        for side, s in P.SIDES:
            pose.turn(f"fang.{side}", X, 10.0 * P.pulse(t, 0.4, 0.5, 0.52, 0.62) - 10.0 * P.pulse(t, 0.6, 0.7, 0.72, 0.8))
        legs(pose)
        return P.from_pose(pose)

    def walk(t):
        p = 2 * math.pi * t
        pose = Pose(m, (0, 0, 0.015 * math.cos(2 * p)))
        pose.turn("body", Z, 2.5 * math.sin(p))
        pose.turn("body", Y, 2.0 * math.sin(p))
        pose.turn("abdomen", Z, -5.0 * math.sin(p))
        pose.turn("abdomen", X, 3.0 * math.cos(2 * p))
        targets = {}
        for name, hip, knee, ankle, tip, d in LEGS:
            dy, dz, u = P.step(t, phase[name], duty, stride, lift)
            targets[name] = ankle + Vector((0, dy, dz))
        legs(pose, targets)
        return P.from_pose(pose)

    def attack(t):
        w = P.pulse(t, 0.0, 0.35, 0.42, 0.52)      # Rears up.
        s = P.pulse(t, 0.42, 0.52, 0.6, 1.0)       # Comes down on the prey.
        pose = Pose(m, (0, 0.1 * w - 0.22 * s, 0.3 * w - 0.03 * s))
        pose.turn("body", X, -30.0 * w + 10.0 * s)
        pose.turn("abdomen", X, 24.0 * w + 6.0 * s)
        targets = {}
        for name, hip, knee, ankle, tip, d in LEGS:
            if name[1] in "12":
                k = 1.0 if name[1] == "1" else 0.55
                targets[name] = ankle + Vector((-d.x * 0.25 * w * k, -0.1 * w - 0.3 * s * k, 0.85 * w * k + 0.05 * s))
        legs(pose, targets)
        for side, sx in P.SIDES:
            pose.turn(f"fang.{side}", X, -35.0 * w + 25.0 * s)
            pose.turn(f"fang.{side}", Z, 14.0 * w * sx)
        return P.from_pose(pose)

    def die(t):
        shake = math.sin(50 * t) * (1 - P.smooth(t / 0.3))
        roll = P.smooth((t - 0.15) / 0.45)
        curl = P.smooth((t - 0.35) / 0.6)
        pose = Pose(m, (0.25 * roll, 0, 0.35 * math.sin(math.pi * roll) + 0.04 * roll))
        pose.turn("body", Y, 180.0 * roll + 3.0 * shake)
        pose.turn("abdomen", X, -8.0 * curl)
        for name, hip, knee, ankle, tip, d in LEGS:
            hinge = d.cross(Vector((0, 0, 1)))
            pose.turn(f"leg_upper.{name}", hinge, 48.0 * curl + 6.0 * shake)
            pose.turn(f"leg_lower.{name}", hinge, -100.0 * curl)
            pose.turn(f"foot.{name}", hinge, -30.0 * curl)
        return P.from_pose(pose)

    m.clip("idle", 3.0, idle)
    m.clip("walk", frames / P.FPS, walk, speed=speed)
    m.clip("attack", 1.1, attack)
    m.clip("die", 1.5, die, loops=False)
    return m


def build(name, colors, k=1.0):
    def make():
        mb = P.kit.begin()
        body(mb)
        P.save(mb, name, colors, mech(), k)
    return make


MODELS = {"enemy_spider_giant": build("enemy_spider_giant", BLACK),
          "enemy_spider_forest": build("enemy_spider_forest", BROWN),
          "enemy_spider_cave": build("enemy_spider_cave", PALE),
          "enemy_spiderling": build("enemy_spiderling", BROWN, k=0.3),
          "monster_spider_queen": build("monster_spider_queen", dict(BLACK, **P.palette(body=0x3A1E4A, body_light=0x54306A,
                                                                                    mark=0xE8C23A, eye=0x8CFFB8)), k=1.7)}
