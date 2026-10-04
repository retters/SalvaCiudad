"""Crocodile: 3.6 m long, low and sprawling: an armored body with rows of
scutes, a long snout with a hinged lower jaw full of teeth, eyes on top of
the head, four short legs out to the sides and a tail of six segments.
Rigid plates; the legs are posed by inverse kinematics. Clips: idle (the
jaw gapes now and then), walk (the body and tail snake from side to side),
attack (a lunge and a snap) and die (rolls belly up). Variants: green river
crocodile, dark swamp one and a pale one."""

import math

from mathutils import Quaternion, Vector

import _parts as P
from _parts import X, Y, Z, Pose, hull, seg, spike, ball

GREEN = P.palette(hide=0x5A7A3A, hide_dark=0x3E5A2A, belly=0xD8CC8A, tooth=0xF2EAD6, eye=0xF2D23A, mouth=0xB85A5A)
DARK = P.palette(hide=0x3A4034, hide_dark=0x262A22, belly=0x8A8A6A, tooth=0xF2EAD6, eye=0xFF8A2A, mouth=0x8A3A3A)
PALE = P.palette(hide=0xC8C8A8, hide_dark=0xA0A084, belly=0xF0ECD8, tooth=0xFFFFFF, eye=0xE0342A, mouth=0xD88A8A)

LEGS = []
for side, s in P.SIDES:
    for name, y in (("F", -0.45), ("H", 0.55)):
        hip = Vector((0.26 * s, y, 0.24))
        knee = Vector((0.5 * s, y + 0.06, 0.3))
        ankle = Vector((0.56 * s, y - 0.06, 0.07))
        LEGS.append((name + side, hip, knee, ankle, ankle + Vector((0.02 * s, -0.2, -0.07)), s))
TAIL = [Vector((0, 0.95 + i * 0.36, 0.2 - 0.02 * i)) for i in range(7)]
NECK = Vector((0, -0.85, 0.24))


def slab(mb, y0, y1, w0, w1, top, mat, bone, z0=0.06):
    return hull(mb, [(-w0, y0, z0 + 0.06), (w0, y0, z0 + 0.06), (-w1, y1, z0 + 0.06), (w1, y1, z0 + 0.06),
                     (-w0 * 0.7, y0, z0), (w0 * 0.7, y0, z0), (-w1 * 0.7, y1, z0), (w1 * 0.7, y1, z0),
                     (-w0 * 0.7, y0, top), (w0 * 0.7, y0, top), (-w1 * 0.7, y1, top), (w1 * 0.7, y1, top)], mat, bone)


def body(mb):
    slab(mb, -0.87, -0.2, 0.26, 0.34, 0.42, "hide", "body")
    slab(mb, -0.22, 0.5, 0.34, 0.33, 0.44, "hide_dark", "body")
    slab(mb, 0.48, 0.98, 0.33, 0.2, 0.4, "hide", "body")
    slab(mb, -0.8, 0.9, 0.24, 0.2, 0.08, "belly", "body", z0=0.045)
    for i in range(8):                                        # Scutes along the back.
        y = -0.7 + i * 0.22
        for x in (-0.12, 0.12):
            spike(mb, (x, y, 0.4), (x, y + 0.05, 0.5), 0.05, "hide_dark", "body")
    # Head: skull, long upper snout, lower jaw.
    hull(mb, [NECK + Vector(o) for o in ((-0.22, 0.02, -0.12), (0.22, 0.02, -0.12), (-0.2, 0.02, 0.12),
                                         (0.2, 0.02, 0.12), (-0.2, -0.3, -0.04), (0.2, -0.3, -0.04),
                                         (-0.17, -0.3, 0.12), (0.17, -0.3, 0.12))], "hide", "head")
    hull(mb, [NECK + Vector(o) for o in ((-0.17, -0.28, -0.03), (0.17, -0.28, -0.03), (-0.15, -0.28, 0.1),
                                         (0.15, -0.28, 0.1), (-0.11, -0.95, -0.03), (0.11, -0.95, -0.03),
                                         (-0.1, -0.95, 0.05), (0.1, -0.95, 0.05), (0, -1.0, 0.0))], "hide", "head")
    hull(mb, [NECK + Vector(o) for o in ((-0.2, 0.0, -0.13), (0.2, 0.0, -0.13), (-0.19, 0.0, -0.05), (0.19, 0.0, -0.05),
                                         (-0.1, -0.93, -0.11), (0.1, -0.93, -0.11), (-0.1, -0.93, -0.05),
                                         (0.1, -0.93, -0.05))], "belly", "jaw")
    hull(mb, [NECK + Vector(o) for o in ((-0.14, -0.1, -0.048), (0.14, -0.1, -0.048), (-0.08, -0.9, -0.048),
                                         (0.08, -0.9, -0.048), (0, -0.5, -0.044))], "mouth", "jaw")
    for s in (-1, 1):
        ball(mb, NECK + Vector((s * 0.13, -0.2, 0.15)), 0.05, "hide_dark", "head")
        ball(mb, NECK + Vector((s * 0.15, -0.23, 0.16)), 0.028, "eye", "head")
        ball(mb, NECK + Vector((s * 0.05, -0.93, 0.06)), 0.025, "hide_dark", "head")              # Nostrils.
        for i in range(7):
            y = -0.34 - i * 0.09
            w = 0.16 - 0.008 * i
            spike(mb, NECK + Vector((s * w, y, -0.02)), NECK + Vector((s * w, y, -0.085)), 0.02, "tooth", "head",
                  sides=4)
            spike(mb, NECK + Vector((s * (w - 0.02), y - 0.045, -0.06)), NECK + Vector((s * (w - 0.02), y - 0.045, 0.0)),
                  0.018, "tooth", "jaw", sides=4)
    for i, (a, b) in enumerate(zip(TAIL, TAIL[1:])):
        w0, w1 = 0.2 - 0.03 * i, 0.17 - 0.03 * i
        h0, h1 = 0.4 - 0.05 * i, 0.35 - 0.05 * i
        hull(mb, [(-w0, a.y - 0.02, 0.08), (w0, a.y - 0.02, 0.08), (-w1, b.y + 0.02, 0.07), (w1, b.y + 0.02, 0.07),
                  (-w0 * 0.5, a.y - 0.02, h0), (w0 * 0.5, a.y - 0.02, h0), (-max(w1, 0.02) * 0.5, b.y + 0.02, h1),
                  (max(w1, 0.02) * 0.5, b.y + 0.02, h1)], "hide" if i % 2 else "hide_dark", f"tail.{i + 1}")
        spike(mb, (0, (a.y + b.y) / 2, h0 - 0.03), (0, (a.y + b.y) / 2 + 0.06, h0 + 0.1), 0.045, "hide_dark",
              f"tail.{i + 1}")
    for name, hip, knee, ankle, toe, s in LEGS:
        seg(mb, hip, knee, 0.1, 0.075, "hide", f"leg_upper.{name}")
        seg(mb, knee, ankle, 0.075, 0.055, "hide_dark", f"leg_lower.{name}")
        ball(mb, knee, 0.08, "hide", f"leg_lower.{name}")
        hull(mb, [(ankle.x - 0.07, ankle.y + 0.06, 0.0), (ankle.x + 0.07, ankle.y + 0.06, 0.0),
                  (ankle.x - 0.1, ankle.y - 0.2, 0.0), (ankle.x + 0.1, ankle.y - 0.2, 0.0),
                  (ankle.x, ankle.y + 0.03, 0.1), (ankle.x, ankle.y - 0.1, 0.05)], "hide_dark", f"foot.{name}")


def mech():
    bones = [("body", (0, 0.95, 0.24), (0, -0.85, 0.24), None), ("head", tuple(NECK), (0, -1.85, 0.24), "body"),
             ("jaw", tuple(NECK + Vector((0, 0, -0.06))), (0, -1.78, 0.14), "head")]
    parent = "body"
    for i, (a, b) in enumerate(zip(TAIL, TAIL[1:])):
        bones.append((f"tail.{i + 1}", tuple(a), tuple(b), parent))
        parent = f"tail.{i + 1}"
    for name, hip, knee, ankle, toe, s in LEGS:
        bones += [(f"leg_upper.{name}", hip, knee, "body"), (f"leg_lower.{name}", knee, ankle, f"leg_upper.{name}"),
                  (f"foot.{name}", ankle, toe, f"leg_lower.{name}")]
    m = P.kit.Mech(bones)
    frames, duty, stride, lift = 24, 0.66, 0.34, 0.07
    speed = stride * P.FPS / (duty * frames)
    phase = {"FL": 0.0, "HR": 0.0, "FR": 0.5, "HL": 0.5}
    n_tail = len(TAIL) - 1

    def legs(pose, targets=None):
        for name, hip, knee, ankle, toe, s in LEGS:
            pose.limb(f"leg_upper.{name}", f"leg_lower.{name}", (targets or {}).get(name, ankle),
                      Vector((s * 1.0, 0.3, 0.8)))
            pose.set_world(f"foot.{name}", Quaternion())

    def tail(pose, fn):
        for i in range(n_tail):
            pose.turn(f"tail.{i + 1}", Z, fn(i))

    def idle(t):
        p = 2 * math.pi * t
        gape = P.pulse(t, 0.4, 0.5, 0.7, 0.8)
        pose = Pose(m, (0, 0, 0.008 * math.sin(2 * p)))
        pose.turn("head", X, -20.0 * gape)
        pose.turn("head", Z, 5.0 * math.sin(p))
        pose.turn("jaw", X, 26.0 * gape)
        tail(pose, lambda i: 6.0 * math.sin(p - i * 0.7))
        legs(pose)
        return P.from_pose(pose)

    def walk(t):
        p = 2 * math.pi * t
        pose = Pose(m, (0.03 * math.sin(p), 0, 0.03 + 0.01 * math.cos(2 * p)))
        pose.turn("body", Z, 5.0 * math.sin(p))
        pose.turn("head", Z, -6.0 * math.sin(p))
        tail(pose, lambda i: -11.0 * math.sin(p - (i + 1) * 0.8))
        targets = {}
        for name, hip, knee, ankle, toe, s in LEGS:
            dy, dz, u = P.step(t, phase[name], duty, stride, lift)
            targets[name] = ankle + Vector((0, dy, dz))
        legs(pose, targets)
        return P.from_pose(pose)

    def attack(t):
        w = P.pulse(t, 0.0, 0.34, 0.4, 0.48)
        s = P.pulse(t, 0.4, 0.48, 0.56, 0.95)
        snap = P.pulse(t, 0.0, 0.3, 0.44, 0.5)
        pose = Pose(m, (0, 0.08 * w - 0.3 * s, 0.03 * w))
        pose.turn("body", X, -3.0 * w)
        pose.turn("head", X, -22.0 * snap)
        pose.turn("jaw", X, 34.0 * snap)
        tail(pose, lambda i: 8.0 * w - 10.0 * s)
        legs(pose)
        return P.from_pose(pose)

    def die(t):
        thrash = math.sin(24 * t) * (1 - P.smooth(t / 0.5))
        roll = P.smooth((t - 0.3) / 0.5)
        pose = Pose(m, (0.3 * roll, 0, 0.25 * math.sin(math.pi * roll) + 0.2 * roll))
        pose.turn("body", Y, 180.0 * roll)
        pose.turn("head", X, -10.0 * (1 - roll))
        pose.turn("jaw", X, 28.0)
        tail(pose, lambda i: 14.0 * thrash * math.cos(i) + 8.0 * roll)
        for name, hip, knee, ankle, toe, s in LEGS:
            pose.turn(f"leg_upper.{name}", Y, -s * 30.0 * roll + 10.0 * thrash)
            pose.turn(f"leg_lower.{name}", Y, s * 30.0 * roll)
        return P.from_pose(pose)

    m.clip("idle", 4.0, idle)
    m.clip("walk", frames / P.FPS, walk, speed=speed)
    m.clip("attack", 1.0, attack)
    m.clip("die", 1.6, die, loops=False)
    return m


def build(name, colors):
    def make():
        mb = P.kit.begin()
        body(mb)
        P.kit.save(mb, P.FAMILY, name, colors, mech=mech())
    return make


MODELS = {"enemy_crocodile": build("enemy_crocodile", GREEN), "enemy_crocodile_swamp": build("enemy_crocodile_swamp", DARK),
          "enemy_crocodile_pale": build("enemy_crocodile_pale", PALE)}
