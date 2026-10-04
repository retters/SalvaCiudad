"""Treant: a walking tree 3.6 m tall. A bark trunk with a face (hollow
eyes that glow, a mouth), branch arms ending in twig fingers, root feet and
a crown of foliage. Rigid pieces on a two-legged skeleton. Clips: idle
(sways), walk (slow, rocking), attack (a branch sweeps down) and die (falls
forward like a felled tree). Variants: green, autumn and a dead, bare one.
"""

import math

from mathutils import Vector

import _parts as P
from _parts import X, Y, Z, Pose, hull, bar, rock, seg, spike, ball, box

PTS = {
    "waist_z": 1.45, "neck_z": 2.7, "top_z": 3.3,
    "shoulder": (0.55, 0.0, 2.45), "elbow": (1.0, -0.05, 2.0), "wrist": (1.15, -0.2, 1.45),
    "hand": (1.18, -0.28, 1.2),
    "hip": (0.3, 0.0, 1.2), "knee": (0.36, -0.05, 0.68), "ankle": (0.38, 0.03, 0.18), "toe": (0.38, -0.4, 0.04),
}

GREEN = P.palette(bark=0x6B4A32, bark_dark=0x4E3626, bark_light=0x86623E, leaf=0x4F8A36, leaf_light=0x6FA846,
                  leaf_dark=0x3A6A2A, eye=0xF2D23A, hollow=0x1E1612, cap=0xC8402E)
AUTUMN = dict(GREEN, **P.palette(leaf=0xD9822A, leaf_light=0xE8A83A, leaf_dark=0xB85A22, eye=0xFFE08A))
DEAD = dict(GREEN, **P.palette(bark=0x7A7268, bark_dark=0x5A544C, bark_light=0x948C80, eye=0x7CFFB0))


def body(mb, leaves=True):
    seg(mb, (0, 0, 1.4), (0, 0.02, 2.75), 0.5, 0.4, "bark", "chest", sides=8)
    seg(mb, (0, 0, 1.05), (0, 0, 1.5), 0.44, 0.52, "bark_dark", "hips", sides=8)
    seg(mb, (0, 0.02, 2.7), (0.05, 0.05, 3.3), 0.36, 0.2, "bark", "head", sides=7)
    for i, (x, y, z, r) in enumerate(((0.3, 0.3, 1.7, 0.12), (-0.35, 0.25, 2.2, 0.1), (0.1, 0.42, 2.5, 0.09))):
        rock(mb, (x, y, z), (r, r, r * 1.3), "bark_light", "chest", count=8, seed=i)        # Knots.
    # The face on the trunk.
    for s in (-1, 1):
        box(mb, (s * 0.17, -0.42, 2.32), (0.15, 0.1, 0.1), "hollow", "chest", rotation_z=-s * 0.3)
        ball(mb, (s * 0.17, -0.46, 2.32), 0.035, "eye", "chest")
        bar(mb, (s * 0.06, -0.47, 2.44), (s * 0.3, -0.45, 2.5), 0.06, 0.07, "bark_dark", "chest")   # Brows.
    spike(mb, (0, -0.44, 2.2), (0, -0.66, 2.1), 0.07, "bark_light", "chest", sides=5)       # A broken-branch nose.
    hull(mb, [(-0.2, -0.46, 1.95), (0.2, -0.46, 1.95), (-0.14, -0.47, 1.82), (0.14, -0.47, 1.82), (0, -0.4, 1.9),
              (0, -0.49, 1.8)], "hollow", "chest")                                            # Mouth.
    for side, s in P.SIDES:
        def m(name):
            p = PTS[name]
            return Vector((p[0] * s, p[1], p[2]))
        seg(mb, m("shoulder") + Vector((-s * 0.2, 0, 0.05)), m("elbow"), 0.2, 0.13, "bark", f"upper_arm.{side}")
        seg(mb, m("elbow"), m("wrist"), 0.13, 0.09, "bark_dark", f"lower_arm.{side}")
        ball(mb, m("elbow"), 0.14, "bark_light", f"lower_arm.{side}")
        for d in ((0.0, -0.3, -0.25), (s * 0.18, -0.1, -0.34), (-s * 0.12, -0.2, -0.3), (s * 0.05, 0.08, -0.36)):
            spike(mb, m("wrist"), m("wrist") + Vector(d) * 1.2, 0.055, "bark", f"hand.{side}", sides=4)
        spike(mb, m("elbow"), m("elbow") + Vector((s * 0.35, 0.1, 0.4)), 0.06, "bark", f"upper_arm.{side}", sides=4)
        seg(mb, m("hip") + Vector((0, 0, 0.1)), m("knee"), 0.24, 0.17, "bark", f"thigh.{side}")
        seg(mb, m("knee"), m("ankle") + Vector((0, 0, 0.02)), 0.17, 0.13, "bark_dark", f"shin.{side}")
        x = m("ankle").x
        for d in ((0.0, -0.5), (s * 0.34, -0.3), (-s * 0.2, -0.36), (s * 0.24, 0.26), (-s * 0.1, 0.3)):   # Roots.
            hull(mb, [(x - 0.1, 0.06, 0.0), (x + 0.1, 0.06, 0.0), (x - 0.1, -0.06, 0.0), (x + 0.1, -0.06, 0.0),
                      (x, 0.0, 0.26), (x + d[0], d[1], 0.0), (x + d[0] * 0.6, d[1] * 0.6, 0.11)], "bark",
                 f"foot.{side}")
        if leaves:
            rock(mb, m("elbow") + Vector((s * 0.4, 0.12, 0.5)), (0.3, 0.3, 0.24), "leaf_dark", f"upper_arm.{side}",
                 count=12, seed=7)
            rock(mb, m("shoulder") + Vector((s * 0.05, 0.1, 0.3)), (0.34, 0.34, 0.22), "leaf", "chest", count=12,
                 seed=8)
        else:
            spike(mb, m("shoulder"), m("shoulder") + Vector((s * 0.3, 0.2, 0.7)), 0.07, "bark", "chest", sides=4)
    # The crown.
    if leaves:
        for i, (x, y, z, r, mat) in enumerate(((0.05, 0.05, 3.55, 0.62, "leaf"), (0.5, 0.1, 3.3, 0.45, "leaf_dark"),
                                               (-0.5, 0.15, 3.35, 0.48, "leaf_light"),
                                               (0.0, 0.5, 3.3, 0.45, "leaf_dark"), (0.0, -0.4, 3.45, 0.4, "leaf_light"),
                                               (0.2, 0.0, 4.0, 0.38, "leaf_light"))):
            rock(mb, (x, y, z), (r, r, r * 0.8), mat, "head", count=14, seed=20 + i)
    else:
        for i, d in enumerate(((0.5, 0.1, 0.8), (-0.45, 0.2, 0.7), (0.1, -0.4, 0.75), (0.0, 0.5, 0.6), (0.15, 0.0, 1.0))):
            a = Vector((0.03, 0.04, 3.2))
            b = a + Vector(d) * 0.75
            seg(mb, a, b, 0.09, 0.05, "bark", "head", sides=5)
            spike(mb, b, b + Vector((d[0] * 0.5 + 0.1, d[1] * 0.5, 0.4)), 0.045, "bark_dark", "head", sides=4)
            spike(mb, b, b + Vector((d[0] * 0.5 - 0.2, d[1] * 0.4, 0.25)), 0.04, "bark_dark", "head", sides=4)
    for x, y, z in ((0.42, -0.2, 1.5), (0.46, -0.1, 1.75), (-0.44, 0.15, 1.4)):           # Shelf mushrooms.
        hull(mb, [(x * 0.9, y * 0.9, z), (x * 1.35, y * 1.35 - 0.08, z), (x * 1.35, y * 1.35 + 0.08, z),
                  (x * 1.1, y * 1.1, z + 0.06)], "cap", "chest" if z > 1.45 else "hips")


def mech():
    m = P.Biped(PTS)
    walk = dict(frames=44, duty=0.68, crouch=0.12, lift=0.16)

    def idle(t):
        p = 2 * math.pi * t
        pose = Pose(m, (0.03 * math.sin(p), 0, -0.05 - 0.015 * math.sin(2 * p)))
        m.stand(pose)
        pose.turn("chest", Y, 3.0 * math.sin(p))
        pose.turn("chest", X, 2.0 * math.sin(2 * p))
        pose.turn("head", Y, 4.0 * math.sin(p - 0.7))
        pose.turn("head", X, 3.0 * math.sin(2 * p - 0.7))
        for side, sx in P.SIDES:
            pose.turn(f"upper_arm.{side}", Y, 5.0 * math.sin(p + sx) * sx)
            pose.turn(f"lower_arm.{side}", X, -6.0 + 4.0 * math.sin(2 * p + sx))
        return P.from_pose(pose)

    def walk_pose(t):
        p = 2 * math.pi * t
        pose, _ = m.gait(t, lean=5.0, swing=12.0, bend=8.0, sway=0.1, bob=0.04, twist=7.0, **walk)
        pose.turn("chest", Y, -5.0 * math.sin(p))
        pose.turn("head", Y, -4.0 * math.sin(p - 0.6))
        pose.turn("head", X, 4.0 * math.sin(2 * p - 0.6))
        return P.from_pose(pose)

    def attack(t):
        w = P.pulse(t, 0.0, 0.4, 0.46, 0.56)
        s = P.pulse(t, 0.46, 0.56, 0.68, 1.0)
        pose = Pose(m, (0, -0.1 * s, -0.05 - 0.14 * s))
        m.stand(pose)
        pose.turn("hips", X, 10.0 * s)
        pose.turn("chest", X, -10.0 * w + 22.0 * s)
        pose.turn("chest", Z, 18.0 * w - 16.0 * s)
        pose.turn("head", X, 8.0 * s)
        pose.turn("upper_arm.R", Y, 70.0 * w + 6.0 * s)             # The branch goes up...
        pose.turn("upper_arm.R", X, -30.0 * w - 66.0 * s)            # ...and comes down in front.
        pose.turn("lower_arm.R", X, -20.0 * w - 14.0 * s)
        pose.turn("upper_arm.L", X, 14.0 * w - 20.0 * s)
        return P.from_pose(pose)

    def die(t):
        creak = P.pulse(t, 0.0, 0.2, 0.25, 0.4)
        a = P.smooth((t - 0.25) / 0.6) ** 1.6
        hip = PTS["hip"][2]
        bounce = 0.05 * math.sin(math.pi * min(1.0, max(0.0, (t - 0.85) / 0.15)))
        pose = Pose(m, (0, -0.2 * a, -(hip - 0.5) * a + bounce))
        pose.turn("hips", X, -5.0 * creak + 88.0 * a)
        pose.turn("chest", Y, 4.0 * creak)
        pose.turn("head", X, 6.0 * a)
        for side, sx in P.SIDES:
            pose.turn(f"upper_arm.{side}", Y, (10.0 * creak + 40.0 * a) * sx)
            pose.turn(f"upper_arm.{side}", X, -30.0 * a)
            pose.turn(f"thigh.{side}", Y, 8.0 * a * sx)
        return P.from_pose(pose)

    m.clip("idle", 5.0, idle)
    m.clip("walk", walk["frames"] / P.FPS, walk_pose, speed=m.gait_speed(walk["frames"], walk["duty"], walk["crouch"]))
    m.clip("attack", 1.8, attack)
    m.clip("die", 2.2, die, loops=False)
    return m


def build(name, colors, leaves=True, k=1.0):
    def make():
        mb = P.kit.begin()
        body(mb, leaves)
        P.save(mb, name, colors, mech(), k)
    return make


MODELS = {"monster_treant": build("monster_treant", GREEN), "monster_treant_autumn": build("monster_treant_autumn", AUTUMN),
          "monster_treant_dead": build("monster_treant_dead", DEAD, leaves=False),
          "monster_treant_sapling": build("monster_treant_sapling", GREEN, k=0.4)}
