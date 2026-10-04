"""Goblins and trolls: chunky two-legged brutes made of faceted lumps, one
per bone, sharing one builder with different measures.

- Goblin: 1.1 m, green, a big head with long ears and a hooked nose, a
  leather loincloth and a jagged dagger. Clips: idle, walk, run, attack (a
  stab) and die (falls on its back). Variants: scout (green), brute (bigger,
  darker, with a spiked club).
- Troll: 2.5 m, gray-green, hunched, long arms, a pot belly, tusks and a
  tree-trunk club. Clips: idle, walk, attack (an overhead smash) and die.
  Variants: forest troll, ogre (tan and fat), frost troll.
"""

import math

from mathutils import Vector

import _parts as P
from _parts import X, Y, Z, Pose, hull, bar, rock, seg, spike, ball, box, plate


def scaled(pts, k):
    return {n: (v * k if isinstance(v, float) else tuple(c * k for c in v)) for n, v in pts.items()}


GOBLIN = {
    "waist_z": 0.52, "neck_z": 0.78, "top_z": 1.08,
    "shoulder": (0.17, 0.0, 0.74), "elbow": (0.21, 0.01, 0.56), "wrist": (0.23, -0.02, 0.4),
    "hand": (0.235, -0.03, 0.33),
    "hip": (0.08, 0.0, 0.42), "knee": (0.09, -0.02, 0.24), "ankle": (0.09, 0.01, 0.05), "toe": (0.09, -0.12, 0.015),
}
TROLL = {
    "waist_z": 1.25, "neck_z": 2.0, "top_z": 2.42,
    "shoulder": (0.62, 0.0, 1.9), "elbow": (0.76, 0.02, 1.36), "wrist": (0.8, -0.06, 0.86),
    "hand": (0.8, -0.08, 0.66),
    "hip": (0.26, 0.0, 1.0), "knee": (0.28, -0.03, 0.56), "ankle": (0.28, 0.02, 0.14), "toe": (0.28, -0.3, 0.03),
}


def lumps(mb, center, radii, mat, bone, seed, count=14, tones=True):
    verts = rock(mb, center, radii, mat, bone, count=count, seed=seed, jitter=0.07)
    if tones:
        import random
        rnd = random.Random(seed)
        for f in {f for v in verts for f in v.link_faces}:
            r = rnd.random()
            if r < 0.22:
                f.material_index = mb._material_index(mat + "_light")
            elif r < 0.44:
                f.material_index = mb._material_index(mat + "_shade")
    return verts


def brute(mb, pts, shape):
    """The shared body. `shape` gives radii in units of the body's height."""
    h = pts["top_z"]
    s = shape

    def R(*r):
        return tuple(x * h for x in r)

    neck, waist, hip = pts["neck_z"], pts["waist_z"], pts["hip"][2]
    lumps(mb, (0, s["chest_y"] * h, (neck + waist) * 0.5 + 0.02 * h), R(*s["chest"]), "skin", "chest", 1, 20)
    lumps(mb, (0, s["belly_y"] * h, (waist + hip) * 0.5 + 0.02 * h), R(*s["belly"]), "skin", "hips", 2, 16)
    for side, sx in P.SIDES:
        def m(name):
            p = pts[name]
            return Vector((p[0] * sx, p[1], p[2]))
        i = 10 if sx > 0 else 20
        a = s["arm"] * h
        lumps(mb, m("shoulder"), (a * 1.25, a * 1.2, a * 1.15), "skin", f"upper_arm.{side}", i + 1, 10)
        seg(mb, m("shoulder"), m("elbow"), a, a * 0.85, "skin", f"upper_arm.{side}")
        seg(mb, m("elbow"), m("wrist"), a * 0.95, a * 0.8, "skin_shade", f"lower_arm.{side}")
        ball(mb, m("elbow"), a * 0.98, "skin", f"lower_arm.{side}")
        lumps(mb, (m("wrist") + m("hand")) * 0.5 + Vector((0, -0.01 * h, -0.01 * h)), (a * 1.15, a * 1.3, a * 1.5),
              "skin", f"hand.{side}", i + 2, 10)
        g = s["leg"] * h
        seg(mb, m("hip") + Vector((0, 0, 0.02 * h)), m("knee"), g * 1.25, g * 0.9, "skin", f"thigh.{side}")
        ball(mb, m("knee"), g * 0.98, "skin_shade", f"shin.{side}")
        seg(mb, m("knee"), m("ankle"), g * 0.92, g * 0.72, "skin", f"shin.{side}")
        x, fl, fw, fh = m("ankle").x, s["foot"][0] * h, s["foot"][1] * h, s["foot"][2] * h
        hull(mb, [(x - fw, fl * 0.35, 0.0), (x + fw, fl * 0.35, 0.0), (x - fw * 1.25, -fl, 0.0),
                  (x + fw * 1.25, -fl, 0.0), (x - fw * 0.8, fl * 0.3, fh), (x + fw * 0.8, fl * 0.3, fh),
                  (x - fw, -fl * 0.6, fh * 0.6), (x + fw, -fl * 0.6, fh * 0.6)], "skin_shade", f"foot.{side}")
    # Loincloth and belt.
    bw, bd = s["belly"][0] * h, s["belly"][1] * h
    mb.cylinder((0, s["belly_y"] * h, waist - 0.03 * h), (0, s["belly_y"] * h, waist + 0.02 * h), bw * 1.02, bw * 1.04,
                "leather_dark", weights={"hips": 1.0}, segments=8)
    for y, drop in ((-1, 0.2), (1, 0.16)):
        yy = s["belly_y"] * h + y * bd * 0.95
        hull(mb, [(-bw * 0.6, yy, waist), (bw * 0.6, yy, waist), (-bw * 0.5, yy + y * 0.02 * h, waist - drop * h),
                  (bw * 0.5, yy + y * 0.02 * h, waist - drop * h), (0, yy + y * 0.025 * h, waist - (drop + 0.05) * h),
                  (-bw * 0.6, yy - y * 0.02 * h, waist), (bw * 0.6, yy - y * 0.02 * h, waist)], "leather", "hips")


def goblin_head(mb, pts):
    h = pts["top_z"]
    c = Vector((0, -0.02 * h, pts["neck_z"] + 0.13 * h))
    lumps(mb, c, (0.14 * h, 0.15 * h, 0.13 * h), "skin", "head", 5, 18)
    seg(mb, (0, 0, pts["neck_z"] - 0.03 * h), c + Vector((0, 0.01 * h, -0.08 * h)), 0.05 * h, 0.05 * h, "skin_shade",
        "head")
    for s in (-1, 1):
        base = c + Vector((s * 0.12 * h, 0.02 * h, 0.02 * h))
        plate(mb, [base + Vector((0, -0.03, 0.04)) * h, base + Vector((0, 0.03, -0.04)) * h,
                   base + Vector((s * 0.24, 0.07, 0.1)) * h], 0.02 * h, "skin_shade", "head")
        ball(mb, c + Vector((s * 0.058, -0.125, 0.03)) * h, 0.03 * h, "eye", "head")
        ball(mb, c + Vector((s * 0.06, -0.15, 0.03)) * h, 0.013 * h, "pupil", "head")
        spike(mb, c + Vector((s * 0.05, -0.12, -0.085)) * h, c + Vector((s * 0.055, -0.14, -0.04)) * h, 0.014 * h,
              "tooth", "head")
    spike(mb, c + Vector((0, -0.12, 0.0)) * h, c + Vector((0, -0.25, -0.05)) * h, 0.04 * h, "skin_shade", "head", sides=5)
    box(mb, c + Vector((0, -0.135, -0.08)) * h, (0.11 * h, 0.03 * h, 0.018 * h), "pupil", "head")


def troll_head(mb, pts):
    h = pts["top_z"]
    c = Vector((0, -0.05 * h, pts["neck_z"] + 0.07 * h))
    lumps(mb, c, (0.085 * h, 0.095 * h, 0.085 * h), "skin", "head", 5, 16)
    hull(mb, [c + Vector(o) * h for o in ((-0.07, -0.08, -0.03), (0.07, -0.08, -0.03), (-0.06, -0.1, -0.09),
                                          (0.06, -0.1, -0.09), (-0.07, 0.0, -0.06), (0.07, 0.0, -0.06),
                                          (0, -0.115, -0.06))], "skin_shade", "head")          # Jaw.
    for s in (-1, 1):
        plate(mb, [c + Vector((s * 0.075, 0.0, 0.02)) * h, c + Vector((s * 0.075, 0.03, -0.02)) * h,
                   c + Vector((s * 0.15, 0.04, 0.04)) * h], 0.014 * h, "skin_shade", "head")
        ball(mb, c + Vector((s * 0.035, -0.085, 0.015)) * h, 0.014 * h, "eye", "head")
        spike(mb, c + Vector((s * 0.045, -0.1, -0.06)) * h, c + Vector((s * 0.055, -0.115, 0.0)) * h, 0.014 * h,
              "tooth", "head")
    hull(mb, [c + Vector(o) * h for o in ((-0.07, -0.09, 0.03), (0.07, -0.09, 0.03), (-0.07, -0.07, 0.05),
                                          (0.07, -0.07, 0.05), (0, -0.1, 0.045))], "skin_shade", "head")   # Brow.
    spike(mb, c + Vector((0, -0.085, 0.0)) * h, c + Vector((0, -0.16, -0.035)) * h, 0.03 * h, "skin_shade", "head",
          sides=5)
    # A tuft of hair and moss on the shoulders.
    for i, d in enumerate(((0, 0.3, 1), (0.4, 0.5, 0.8), (-0.4, 0.5, 0.8))):
        d = Vector(d).normalized()
        spike(mb, c + d * 0.06 * h, c + d * 0.15 * h, 0.03 * h, "hair", "head")


def dagger(mb, pts):
    hd = Vector((-pts["hand"][0], pts["hand"][1], pts["hand"][2] + 0.03))
    bar(mb, hd + Vector((0, 0.04, 0)), hd + Vector((0, -0.05, 0)), 0.025, 0.025, "leather", "hand.R")
    bar(mb, hd + Vector((0, -0.05, -0.04)), hd + Vector((0, -0.05, 0.04)), 0.03, 0.02, "iron", "hand.R")
    hull(mb, [hd + Vector(o) for o in ((0.006, -0.06, 0.03), (-0.006, -0.06, 0.03), (0.006, -0.06, -0.03),
                                       (-0.006, -0.06, -0.03), (0.005, -0.2, 0.04), (-0.005, -0.2, 0.04),
                                       (0, -0.36, 0.0), (0.005, -0.22, -0.02), (-0.005, -0.22, -0.02))],
         "iron", "hand.R")


def club(mb, pts, length, r, spikes=True, mat="wood"):
    hd = Vector((-pts["hand"][0], pts["hand"][1], pts["hand"][2] + 0.04 * length))
    a = hd + Vector((0, 0.16 * length, -0.01 * length))
    b = hd + Vector((0, -length, 0.22 * length))
    seg(mb, a, hd.lerp(b, 0.45), r * 0.45, r * 0.7, mat, "hand.R", sides=6)
    seg(mb, hd.lerp(b, 0.45), b, r * 0.7, r, mat + "_dark", "hand.R", sides=6)
    ball(mb, b, r * 0.95, mat, "hand.R")
    if spikes:
        axis = (b - a).normalized()
        for i in range(6):
            at = hd.lerp(b, 0.6 + 0.07 * i)
            d = Vector((math.cos(i * 2.2), 0, math.sin(i * 2.2)))
            d = (d - axis * d.dot(axis)).normalized()
            spike(mb, at + d * r * 0.7, at + d * r * 1.7, r * 0.3, "tooth", "hand.R")


def mech(pts, kind):
    m = P.Biped(pts)
    h = pts["top_z"]
    big = kind == "troll"
    walk = dict(frames=34, duty=0.64, crouch=0.07 * h, lift=0.06 * h) if big else \
        dict(frames=14, duty=0.6, crouch=0.09 * h, lift=0.07 * h)
    run = dict(frames=10, duty=0.4, crouch=0.11 * h, lift=0.1 * h)
    hunch = 14.0 if big else 10.0

    def carry(pose, sway=0.0):
        """The weapon arm bent forward; the other hangs."""
        pose.turn("upper_arm.R", X, -14.0 + sway)
        pose.turn("lower_arm.R", X, -40.0 if not big else -28.0)

    def idle(t):
        p = 2 * math.pi * t
        pose = Pose(m, (0.01 * h * math.sin(p), 0, -0.03 * h - 0.006 * h * math.sin(2 * p)))
        m.stand(pose)
        pose.turn("chest", X, hunch + 2.0 * math.sin(2 * p))
        pose.turn("head", X, -hunch * 0.6)
        pose.turn("head", Z, 16.0 * math.sin(p) if not big else 8.0 * math.sin(p))
        m.arm(pose, "L", 3.0 * math.sin(2 * p), 14.0, out=5.0)
        carry(pose, 3.0 * math.sin(2 * p))
        return P.from_pose(pose)

    def gait(g, lean, swing):
        def pose_fn(t):
            pose, _ = m.gait(t, lean=lean, swing=swing, bend=16.0, sway=0.02 * h, bob=0.015 * h, twist=8.0,
                             arms=("L",), **g)
            pose.turn("head", X, -lean * 0.3)
            carry(pose, 8.0 * math.sin(2 * math.pi * t))
            return P.from_pose(pose)
        return pose_fn

    def stab(t):
        w = P.pulse(t, 0.0, 0.3, 0.36, 0.46)
        s = P.pulse(t, 0.36, 0.46, 0.54, 0.95)
        pose = Pose(m, (0, (0.05 * w - 0.16 * s) * h, (-0.05 - 0.04 * s) * h))
        m.stand(pose, {"L": (0, -0.1 * h * s), "R": (0, 0.0)})
        pose.turn("hips", Z, 14.0 * w - 16.0 * s)
        pose.turn("chest", X, hunch + 10.0 * s)
        pose.turn("chest", Z, 18.0 * w - 20.0 * s)
        pose.turn("head", X, -hunch)
        pose.turn("upper_arm.R", X, 30.0 * w - 85.0 * s)
        pose.turn("lower_arm.R", X, -90.0 * w - 8.0 * s - 20.0 * (1 - max(w, s)))
        m.arm(pose, "L", -20.0 * w + 20.0 * s, 30.0, out=10.0)
        return P.from_pose(pose)

    def smash(t):
        w = P.pulse(t, 0.0, 0.4, 0.46, 0.56)
        s = P.pulse(t, 0.46, 0.56, 0.66, 1.0)
        pose = Pose(m, (0, (0.02 * w - 0.06 * s) * h, (-0.03 - 0.07 * s) * h))
        m.stand(pose)
        pose.turn("hips", X, 12.0 * s)
        pose.turn("chest", X, hunch - 16.0 * w + 26.0 * s)
        pose.turn("chest", Z, 12.0 * w - 12.0 * s)
        pose.turn("head", X, -hunch - 10.0 * s)
        pose.turn("upper_arm.R", X, -14.0 - 150.0 * w - 50.0 * s)
        pose.turn("lower_arm.R", X, -28.0 - 40.0 * w + 10.0 * s)
        pose.turn("hand.R", X, -20.0 * w + 30.0 * s)
        m.arm(pose, "L", -30.0 * w + 10.0 * s, 20.0, out=10.0 + 10.0 * w)
        return P.from_pose(pose)

    def die(t):
        stagger = P.pulse(t, 0.0, 0.2, 0.25, 0.4)
        a = P.smooth((t - 0.2) / 0.55)
        hip = pts["hip"][2]
        back = (0.13 if not big else 0.17) * h
        bounce = 0.02 * h * math.sin(math.pi * min(1.0, max(0.0, (t - 0.75) / 0.25)))
        pose = Pose(m, (0, 0.25 * hip * a, -(hip - back) * a * a + bounce))
        pose.turn("hips", X, 6.0 * stagger - 88.0 * a)
        pose.turn("chest", X, hunch * (1 - a) - 6.0 * stagger)
        pose.turn("head", X, -12.0 * stagger + 8.0 * a)
        pose.turn("head", Z, 20.0 * a)
        for side, sx in P.SIDES:
            pose.turn(f"upper_arm.{side}", Y, (20.0 * stagger + 55.0 * a) * sx)
            pose.turn(f"lower_arm.{side}", X, -20.0 * (1 - a) - 10.0)
            pose.turn(f"thigh.{side}", Y, 10.0 * a * sx)
            pose.turn(f"thigh.{side}", X, (8.0 if sx > 0 else -4.0) * a)
            pose.turn(f"shin.{side}", X, (14.0 if sx > 0 else 4.0) * a)
        pose.turn("hand.R", X, 82.0 * a)                     # The weapon ends flat on the ground.
        return P.from_pose(pose)

    m.clip("idle", 3.0 if not big else 4.0, idle)
    m.clip("walk", walk["frames"] / P.FPS, gait(walk, hunch, 18.0),
           speed=m.gait_speed(walk["frames"], walk["duty"], walk["crouch"]))
    if not big:
        m.clip("run", run["frames"] / P.FPS, gait(run, hunch + 12.0, 34.0),
               speed=m.gait_speed(run["frames"], run["duty"], run["crouch"]))
    m.clip("attack", 0.8 if not big else 1.5, stab if not big else smash)
    m.clip("die", 1.2 if not big else 1.8, die, loops=False)
    return m


GOBLIN_SHAPE = dict(chest=(0.15, 0.12, 0.13), chest_y=0.0, belly=(0.135, 0.115, 0.1), belly_y=-0.01, arm=0.04,
                    leg=0.048, foot=(0.14, 0.05, 0.05))
TROLL_SHAPE = dict(chest=(0.26, 0.18, 0.18), chest_y=0.01, belly=(0.21, 0.19, 0.16), belly_y=-0.035, arm=0.062,
                   leg=0.07, foot=(0.14, 0.065, 0.06))
OGRE_SHAPE = dict(TROLL_SHAPE, belly=(0.25, 0.24, 0.19), belly_y=-0.05, chest=(0.25, 0.19, 0.17))

BASE = P.palette(leather=0x85543C, leather_dark=0x5E3F36, iron=0x7A7F86, eye=0xF2D23A, pupil=0x1A1412,
                 tooth=0xEFE6CC, wood=0x7A5636, wood_dark=0x5A3E28, hair=0x3A2E28)


def skin(hex_color):
    return {**BASE, **P.shades("skin", hex_color, light=0.12, dark=0.16)}


def goblin(name, color, k=1.0, weapon="dagger"):
    def make():
        pts = scaled(GOBLIN, k)
        mb = P.kit.begin()
        brute(mb, pts, GOBLIN_SHAPE)
        goblin_head(mb, pts)
        if weapon == "dagger":
            dagger(mb, pts)
        elif weapon == "staff":          # A shaman: a staff topped with a skull, and feathers on the head.
            club(mb, pts, 0.85 * k, 0.03 * k, spikes=False)
            hd = Vector((-pts["hand"][0], pts["hand"][1] - 0.85 * k, pts["hand"][2] + 0.25 * k))
            rock(mb, hd, (0.06 * k, 0.07 * k, 0.06 * k), "tooth", "hand.R", count=10, seed=3)
            c = Vector((0, 0.0, pts["neck_z"] + 0.24 * pts["top_z"]))
            for i, x in enumerate((-0.08, -0.03, 0.03, 0.08)):
                plate(mb, [c + Vector((x * k - 0.02 * k, 0.03 * k, 0)), c + Vector((x * k + 0.02 * k, 0.03 * k, 0)),
                           c + Vector((x * 1.6 * k, 0.07 * k, 0.2 * k))], 0.012 * k, "eye" if i % 2 else "feather", "head")
        else:
            club(mb, pts, 0.5 * k, 0.07 * k)
        P.kit.save(mb, P.FAMILY, name, dict(skin(color), **P.palette(feather=0xC8302A)), mech=mech(pts, "goblin"))
    return make


def troll(name, color, shape=TROLL_SHAPE, hair=None):
    def make():
        pts = dict(TROLL)
        mb = P.kit.begin()
        brute(mb, pts, shape)
        troll_head(mb, pts)
        club(mb, pts, 1.25, 0.17)
        for s in (-1, 1):
            rock(mb, (s * 0.56, 0.1, 2.12), (0.2, 0.2, 0.09), "hair", "chest", count=10, seed=8 + s)
        colors = skin(color)
        if hair is not None:
            colors.update(P.palette(hair=hair))
        P.kit.save(mb, P.FAMILY, name, colors, mech=mech(pts, "troll"))
    return make


MODELS = {
    "enemy_goblin": goblin("enemy_goblin", 0x7FA63A),
    "enemy_goblin_shaman": goblin("enemy_goblin_shaman", 0x5E9A7A, weapon="staff"),
    "enemy_goblin_brute": goblin("enemy_goblin_brute", 0x5E7A3A, k=1.3, weapon="club"),
    "monster_troll": troll("monster_troll", 0x6F8A6A, hair=0x4E6A32),
    "monster_ogre": troll("monster_ogre", 0xC9A27A, shape=OGRE_SHAPE, hair=0x5A4636),
    "monster_troll_frost": troll("monster_troll_frost", 0x9FB8C8, hair=0xE8EEF2),
}
