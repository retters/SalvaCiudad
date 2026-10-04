"""Skeleton warrior: a walking skeleton with a rusty cap, a notched sword
in the right hand and a round wooden shield on the left arm. Rigid bones,
one per piece. Clips: idle, walk, attack (an overhead chop) and die (it
falls apart into a heap of bones). Variants: an archer's bow is not made;
the second model is an armored one with a darker, mossy bone."""

import math

from mathutils import Vector

import _parts as P
from _parts import X, Z, Pose, hull, bar, seg, spike, ball, rock, box

PTS = {
    "waist_z": 1.08, "neck_z": 1.5, "top_z": 1.78,
    "shoulder": (0.2, 0.0, 1.43), "elbow": (0.235, 0.01, 1.15), "wrist": (0.25, -0.02, 0.9),
    "hand": (0.255, -0.03, 0.8),
    "hip": (0.09, 0.0, 0.93), "knee": (0.095, -0.01, 0.5), "ankle": (0.1, 0.01, 0.08), "toe": (0.1, -0.16, 0.02),
}

COLORS = P.palette(bone=0xE6DCC2, bone_dark=0xC4B796, socket=0x1A1614, eye_glow=0x8CFFB8, iron=0x8A8F96,
                   rust=0x8A5236, wood=0x7A5636, wood_dark=0x5A3E28, leather=0x5E3F36)
MOSSY = dict(COLORS, **P.palette(bone=0xB9BF9C, bone_dark=0x8C9670, eye_glow=0xFF6A3A, iron=0x54585E,
                                 rust=0x3E4046, wood=0x4A3A30))


def body(mb, armored=False):
    # Skull: cranium, cheeks, jaw, dark sockets with a glowing point.
    rock(mb, (0, 0.0, 1.66), (0.088, 0.105, 0.095), "bone", "head", count=18, seed=2, jitter=0.04)
    hull(mb, [(-0.06, -0.09, 1.6), (0.06, -0.09, 1.6), (-0.05, -0.1, 1.53), (0.05, -0.1, 1.53),
              (-0.06, -0.02, 1.58), (0.06, -0.02, 1.58), (-0.045, -0.03, 1.52), (0.045, -0.03, 1.52)], "bone", "head")
    bar(mb, (0, -0.105, 1.545), (0, -0.105, 1.515), 0.085, 0.012, "bone_dark", "head")       # Teeth.
    for s in (-1, 1):
        box(mb, (s * 0.036, -0.092, 1.655), (0.036, 0.03, 0.034), "socket", "head")
        ball(mb, (s * 0.036, -0.1, 1.655), 0.009, "eye_glow", "head", segments=5, rings=3)
    box(mb, (0, -0.1, 1.61), (0.018, 0.02, 0.026), "socket", "head")                         # Nose.
    # A cap helmet, rusty.
    hull(mb, [(x, y, z) for x, y, z in ((-0.1, -0.11, 1.7), (0.1, -0.11, 1.7), (-0.1, 0.11, 1.69),
                                        (0.1, 0.11, 1.69), (-0.07, -0.07, 1.775), (0.07, -0.07, 1.775),
                                        (-0.07, 0.08, 1.77), (0.07, 0.08, 1.77), (0, 0.0, 1.79))], "rust", "head")
    bar(mb, (0, -0.115, 1.72), (0, -0.118, 1.6), 0.022, 0.012, "rust", "head")               # Nasal bar.
    # Spine, ribs, sternum, collar bones.
    seg(mb, (0, 0.035, 1.5), (0, 0.01, 1.58), 0.022, 0.024, "bone_dark", "chest", sides=5)
    for i in range(6):
        z = 1.1 + i * 0.066
        seg(mb, (0, 0.045, z), (0, 0.045, z + 0.05), 0.03, 0.026, "bone", "chest", sides=5)
    for i in range(3):
        z = 0.94 + i * 0.055
        seg(mb, (0, 0.045, z), (0, 0.045, z + 0.042), 0.03, 0.028, "bone", "hips", sides=5)
    for i in range(5):
        z = 1.42 - i * 0.062
        w = 0.14 - 0.012 * abs(i - 1.5)
        for s in (-1, 1):
            pts = [(0, 0.04, z), (s * w * 0.8, 0.045, z - 0.01), (s * w, -0.03, z - 0.03),
                   (s * w * 0.75, -0.1, z - 0.045), (s * 0.02, -0.12, z - 0.04)]
            for a, b in zip(pts, pts[1:]):
                seg(mb, a, b, 0.012, 0.012, "bone", "chest", sides=4)
    bar(mb, (0, -0.125, 1.4), (0, -0.125, 1.13), 0.045, 0.02, "bone_dark", "chest", taper=0.6)
    for s in (-1, 1):
        seg(mb, (0, -0.1, 1.44), (s * 0.2, 0.0, 1.44), 0.014, 0.016, "bone", "chest", sides=4)
        hull(mb, [(s * 0.06, 0.07, 1.42), (s * 0.19, 0.06, 1.43), (s * 0.15, 0.075, 1.25),
                  (s * 0.07, 0.085, 1.28), (s * 0.12, 0.05, 1.33)], "bone_dark", "chest")     # Shoulder blade.
    # Pelvis.
    hull(mb, [(-0.14, 0.02, 1.02), (0.14, 0.02, 1.02), (-0.1, 0.06, 0.9), (0.1, 0.06, 0.9), (-0.06, -0.05, 0.9),
              (0.06, -0.05, 0.9), (0, 0.07, 1.03), (0, -0.04, 0.99), (-0.12, -0.03, 0.98), (0.12, -0.03, 0.98)],
         "bone", "hips")
    for side, s in P.SIDES:
        def m(name):
            p = PTS[name]
            return Vector((p[0] * s, p[1], p[2]))
        # Arm.
        seg(mb, m("shoulder"), m("elbow"), 0.024, 0.018, "bone", f"upper_arm.{side}", sides=5)
        ball(mb, m("shoulder"), 0.034, "bone_dark", f"upper_arm.{side}")
        ball(mb, m("elbow"), 0.027, "bone_dark", f"lower_arm.{side}")
        for off in (-0.012, 0.012):
            seg(mb, m("elbow") + Vector((off, 0, 0)), m("wrist") + Vector((off, 0, 0)), 0.012, 0.01, "bone",
                f"lower_arm.{side}", sides=4)
        hull(mb, [m("wrist") + Vector(o) for o in ((-0.03, -0.02, 0.01), (0.03, -0.02, 0.01), (-0.03, 0.02, 0.01),
                                                    (0.03, 0.02, 0.01), (-0.025, -0.03, -0.11),
                                                    (0.025, -0.03, -0.11), (-0.02, 0.01, -0.11),
                                                    (0.02, 0.01, -0.11))], "bone", f"hand.{side}")
        # Leg.
        seg(mb, m("hip"), m("knee"), 0.03, 0.022, "bone", f"thigh.{side}", sides=5)
        ball(mb, m("hip"), 0.04, "bone_dark", f"thigh.{side}")
        ball(mb, m("knee"), 0.036, "bone_dark", f"shin.{side}")
        seg(mb, m("knee"), m("ankle"), 0.024, 0.017, "bone", f"shin.{side}", sides=5)
        seg(mb, m("knee") + Vector((s * 0.025, 0.02, -0.03)), m("ankle") + Vector((s * 0.02, 0.02, 0)), 0.01,
            0.009, "bone", f"shin.{side}", sides=4)
        x = PTS["ankle"][0] * s
        hull(mb, [(x - 0.04, 0.06, 0.0), (x + 0.04, 0.06, 0.0), (x - 0.05, -0.17, 0.0), (x + 0.05, -0.17, 0.0),
                  (x - 0.03, 0.05, 0.09), (x + 0.03, 0.05, 0.09), (x - 0.035, -0.1, 0.045),
                  (x + 0.035, -0.1, 0.045)], "bone", f"foot.{side}")
        if armored:
            rock(mb, m("shoulder") + Vector((s * 0.02, 0, 0.03)), (0.085, 0.08, 0.06), "iron",
                 f"upper_arm.{side}", count=12, seed=5)
    if armored:
        hull(mb, [(-0.16, -0.14, 1.42), (0.16, -0.14, 1.42), (-0.14, -0.15, 1.12), (0.14, -0.15, 1.12),
                  (-0.17, -0.06, 1.42), (0.17, -0.06, 1.42), (-0.15, -0.06, 1.12), (0.15, -0.06, 1.12),
                  (0, -0.175, 1.3)], "iron", "chest")                                     # Breastplate.
    # Sword in the right hand: the blade points forward.
    h = Vector((-0.255, -0.03, 0.82))
    bar(mb, h + Vector((0, 0.07, 0)), h + Vector((0, -0.07, 0)), 0.03, 0.03, "leather", "hand.R")
    ball(mb, h + Vector((0, 0.085, 0)), 0.024, "iron", "hand.R")
    bar(mb, h + Vector((0, -0.08, -0.09)), h + Vector((0, -0.08, 0.09)), 0.035, 0.03, "iron", "hand.R")
    bar(mb, h + Vector((0, -0.09, 0)), h + Vector((0, -0.7, 0.03)), 0.014, 0.07, "rust", "hand.R", taper=0.75)
    hull(mb, [h + Vector(o) for o in ((0.006, -0.7, 0.056), (-0.006, -0.7, 0.056), (0.006, -0.7, 0.004),
                                      (-0.006, -0.7, 0.004), (0, -0.8, 0.034))], "rust", "hand.R")
    # Round shield strapped to the left forearm, facing out.
    c = Vector((0.3, -0.01, 1.02))
    mb.cylinder(c, c + Vector((0.035, 0, 0)), 0.27, 0.26, "wood", weights={"lower_arm.L": 1.0}, segments=10)
    mb.cylinder(c + Vector((-0.004, 0, 0)), c + Vector((0.02, 0, 0)), 0.29, 0.29, "iron",
                weights={"lower_arm.L": 1.0}, segments=10)
    ball(mb, c + Vector((0.04, 0, 0)), 0.07, "iron", "lower_arm.L", scale=(0.6, 1, 1))
    for a in range(0, 180, 45):
        d = Vector((0, math.cos(math.radians(a)), math.sin(math.radians(a))))
        bar(mb, c + Vector((0.036, 0, 0)) - d * 0.25, c + Vector((0.036, 0, 0)) + d * 0.25, 0.006, 0.02, "wood_dark",
            "lower_arm.L", side=(1, 0, 0))


def mech(info):
    m = P.Biped(PTS)
    walk = dict(frames=22, duty=0.62, crouch=0.06, lift=0.09)
    speed = m.gait_speed(walk["frames"], walk["duty"], walk["crouch"])

    def guard(pose, lift=0.0):
        """Sword forward in the right hand, shield raised on the left arm."""
        pose.turn("upper_arm.R", X, -18.0 - lift)
        pose.turn("lower_arm.R", X, -48.0)
        pose.turn("upper_arm.L", X, -20.0)
        pose.turn("lower_arm.L", X, -70.0)
        pose.turn("lower_arm.L", Z, 30.0)

    def idle(t):
        p = 2 * math.pi * t
        pose = Pose(m, (0.006 * math.sin(p), 0, -0.012 - 0.004 * math.sin(2 * p)))
        m.stand(pose)
        pose.turn("chest", X, 4.0 + 1.5 * math.sin(2 * p))
        pose.turn("chest", Z, 3.0 * math.sin(p))
        pose.turn("head", Z, 14.0 * math.sin(p))
        pose.turn("head", X, 3.0 * math.sin(4 * p))       # The jaw chatters.
        guard(pose, 3.0 * math.sin(2 * p))
        return P.from_pose(pose)

    def walk_pose(t):
        pose, _ = m.gait(t, lean=6.0, sway=0.02, bob=0.015, twist=9.0, arms=(), **walk)
        guard(pose, 6.0 * math.sin(2 * math.pi * t))
        pose.turn("head", Z, 5.0 * math.sin(2 * math.pi * t))
        return P.from_pose(pose)

    def attack(t):
        w = P.pulse(t, 0.0, 0.34, 0.4, 0.5)        # The sword goes up and back.
        s = P.pulse(t, 0.4, 0.5, 0.58, 0.95)       # It comes down in front.
        pose = Pose(m, (0, -0.07 * s + 0.03 * w, -0.02 - 0.05 * s))
        m.stand(pose, {"L": (0, 0.0), "R": (0, 0.0)})
        pose.turn("hips", Z, 8.0 * w - 10.0 * s)
        pose.turn("chest", Z, 16.0 * w - 22.0 * s)
        pose.turn("chest", X, -6.0 * w + 16.0 * s)
        pose.turn("head", X, -4.0 * s)
        pose.turn("upper_arm.R", X, -18.0 - 135.0 * w - 62.0 * s)
        pose.turn("lower_arm.R", X, -48.0 - 30.0 * w + 30.0 * s)
        pose.turn("hand.R", X, -25.0 * w + 55.0 * s)
        pose.turn("upper_arm.L", X, -20.0 + 10.0 * s)
        pose.turn("lower_arm.L", X, -70.0)
        pose.turn("lower_arm.L", Z, 30.0 + 20.0 * w)
        return P.from_pose(pose)

    m.clip("idle", 3.0, idle)
    m.clip("walk", walk["frames"] / P.FPS, walk_pose, speed=speed)
    m.clip("attack", 1.0, attack)
    m.clip("die", 1.4, lambda t: P.collapse(m, t, info, spread=0.4, seed=11), loops=False)
    return m


def build(name, colors, armored=False):
    def make():
        mb = P.kit.begin()
        body(mb, armored)
        P.kit.save(mb, P.FAMILY, name, colors, mech=mech(P.piece_info(mb)))
    return make


MODELS = {"enemy_skeleton_warrior": build("enemy_skeleton_warrior", COLORS),
          "enemy_skeleton_champion": build("enemy_skeleton_champion", MOSSY, armored=True)}
