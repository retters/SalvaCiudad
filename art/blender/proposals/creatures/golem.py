"""Stone golem: 2.5 m of boulders held by iron bands, with a glowing rune
on the chest and moss on the shoulders. Rigid rocks, one or two per bone.
Clips: idle, walk (slow and heavy), attack (both fists slam the ground) and
die (it crumbles into rubble). Variants by material: gray stone, brick-red
clay and dark iron-bound basalt."""

import math

from mathutils import Vector

import _parts as P
from _parts import X, Z, Pose, hull, bar, rock, box, seg

PTS = {
    "waist_z": 1.2, "neck_z": 2.08, "top_z": 2.5,
    "shoulder": (0.74, 0.0, 1.95), "elbow": (0.88, 0.0, 1.42), "wrist": (0.9, -0.06, 0.92),
    "hand": (0.9, -0.08, 0.62),
    "hip": (0.3, 0.0, 0.98), "knee": (0.32, -0.02, 0.56), "ankle": (0.32, 0.02, 0.16), "toe": (0.32, -0.3, 0.03),
}

STONE = {**P.shades("stone", 0x8E9196), **P.palette(stone_dark=0x62666C, iron=0x44484E, rune=0x5CE0FF,
                                                    moss=0x5E8A3A)}
CLAY = {**P.shades("stone", 0xB5694A), **P.palette(stone_dark=0x8A4A34, iron=0x4A3A32, rune=0xFFC44A,
                                                   moss=0x7A8A3A)}
BASALT = {**P.shades("stone", 0x4A4C54), **P.palette(stone_dark=0x2E3036, iron=0x9A7A3A, rune=0xFF5A2A,
                                                     moss=0x3A4A3A)}


def rocks(mb, center, radii, bone, seed, count=16):
    """A boulder whose facets take three tones."""
    verts = rock(mb, center, radii, "stone", bone, count=count, seed=seed, jitter=0.14)
    import random
    rnd = random.Random(seed)
    for f in {f for v in verts for f in v.link_faces}:
        r = rnd.random()
        if r < 0.25:
            f.material_index = mb._material_index("stone_light")
        elif r < 0.5:
            f.material_index = mb._material_index("stone_shade")
    return verts


def body(mb):
    rocks(mb, (0, 0.02, 1.72), (0.62, 0.42, 0.46), "chest", 1, 22)
    rocks(mb, (0, 0.0, 1.18), (0.42, 0.33, 0.3), "hips", 2, 16)
    rocks(mb, (0, -0.08, 2.26), (0.22, 0.24, 0.22), "head", 3, 14)
    hull(mb, [(-0.2, -0.26, 2.3), (0.2, -0.26, 2.3), (-0.22, -0.2, 2.38), (0.22, -0.2, 2.38), (-0.2, -0.1, 2.3),
              (0.2, -0.1, 2.3)], "stone_dark", "head")                                       # Brow.
    for s in (-1, 1):
        box(mb, (s * 0.09, -0.285, 2.26), (0.07, 0.04, 0.035), "rune", "head")               # Eyes.
        rock(mb, (s * 0.66, 0.05, 2.14), (0.2, 0.2, 0.1), "moss", "chest", count=10, seed=7 + int(s))
    # Rune on the chest and an iron band around the waist.
    for a, b in (((0, -0.44, 1.92), (0, -0.44, 1.6)), ((-0.1, -0.43, 1.84), (0.1, -0.43, 1.84)),
                 ((-0.08, -0.43, 1.7), (0, -0.44, 1.6)), ((0.08, -0.43, 1.7), (0, -0.44, 1.6))):
        bar(mb, a, b, 0.035, 0.03, "rune", "chest", side=(0, 1, 0))
    mb.cylinder((0, 0, 1.3), (0, 0, 1.42), 0.44, 0.47, "iron", weights={"hips": 1.0}, segments=10)
    for side, s in P.SIDES:
        def m(name):
            p = PTS[name]
            return Vector((p[0] * s, p[1], p[2]))
        i = 10 if s > 0 else 20
        rocks(mb, m("shoulder") + Vector((s * 0.02, 0, 0.02)), (0.3, 0.3, 0.27), f"upper_arm.{side}", i + 1, 14)
        rocks(mb, (m("shoulder") + m("elbow")) * 0.5 + Vector((0, 0, -0.08)), (0.19, 0.2, 0.27),
              f"upper_arm.{side}", i + 2, 12)
        rocks(mb, (m("elbow") + m("wrist")) * 0.5, (0.24, 0.25, 0.36), f"lower_arm.{side}", i + 3, 16)
        mb.cylinder(m("elbow") + Vector((0, -0.02, -0.14)), m("elbow") + Vector((0, -0.025, -0.24)), 0.27, 0.27,
                    "iron", weights={f"lower_arm.{side}": 1.0}, segments=8)
        rocks(mb, m("wrist") + Vector((0, -0.02, -0.2)), (0.26, 0.27, 0.25), f"hand.{side}", i + 4, 14)
        rocks(mb, (m("hip") + m("knee")) * 0.5, (0.23, 0.24, 0.3), f"thigh.{side}", i + 5, 14)
        rocks(mb, (m("knee") + m("ankle")) * 0.5 + Vector((0, 0, 0.02)), (0.21, 0.22, 0.28), f"shin.{side}",
              i + 6, 14)
        x = m("ankle").x
        hull(mb, [(x - 0.2, 0.2, 0.0), (x + 0.2, 0.2, 0.0), (x - 0.22, -0.34, 0.0), (x + 0.22, -0.34, 0.0),
                  (x - 0.17, 0.17, 0.22), (x + 0.17, 0.17, 0.22), (x - 0.18, -0.24, 0.16), (x + 0.18, -0.24, 0.16),
                  (x, -0.38, 0.06)], "stone_dark", f"foot.{side}")


def mech(info):
    m = P.Biped(PTS)
    walk = dict(frames=40, duty=0.66, crouch=0.09, lift=0.14)
    speed = m.gait_speed(walk["frames"], walk["duty"], walk["crouch"])

    def idle(t):
        p = 2 * math.pi * t
        pose = Pose(m, (0, 0, -0.02 - 0.012 * math.sin(p)))
        m.stand(pose)
        pose.turn("chest", X, 5.0 + 2.0 * math.sin(p))
        pose.turn("head", Z, 12.0 * math.sin(p))
        for side, sx in P.SIDES:
            m.arm(pose, side, 3.0 * math.sin(p + sx), 12.0, out=6.0)
        return P.from_pose(pose)

    def walk_pose(t):
        pose, _ = m.gait(t, lean=7.0, swing=16.0, bend=14.0, sway=0.07, bob=0.03, twist=8.0, **walk)
        for side, sx in P.SIDES:
            pose.turn(f"upper_arm.{side}", P.Y, 6.0 * sx)
        return P.from_pose(pose)

    def attack(t):
        w = P.pulse(t, 0.0, 0.38, 0.45, 0.55)     # Both fists over the head.
        s = P.pulse(t, 0.45, 0.55, 0.68, 1.0)     # They come down on the ground in front.
        shake = math.sin(40 * t) * P.pulse(t, 0.55, 0.57, 0.6, 0.72)
        pose = Pose(m, (0, -0.1 * s, -0.03 - 0.18 * s + 0.01 * shake))
        m.stand(pose)
        pose.turn("hips", X, 22.0 * s)
        pose.turn("chest", X, -12.0 * w + 34.0 * s)
        pose.turn("head", X, -10.0 * w - 18.0 * s)
        for side, sx in P.SIDES:
            pose.turn(f"upper_arm.{side}", X, -165.0 * w - 86.0 * s)
            pose.turn(f"upper_arm.{side}", P.Y, (14.0 * w - 16.0 * s) * sx)
            pose.turn(f"lower_arm.{side}", X, -30.0 * w - 8.0 * s)
        return P.from_pose(pose)

    m.clip("idle", 4.0, idle)
    m.clip("walk", walk["frames"] / P.FPS, walk_pose, speed=speed)
    m.clip("attack", 1.6, attack)
    m.clip("die", 1.8, lambda t: P.collapse(m, t, info, spread=0.8, seed=5, fall=0.55), loops=False)
    return m


def build(name, colors, k=1.0):
    def make():
        mb = P.kit.begin()
        body(mb)
        P.save(mb, name, colors, mech(P.piece_info(mb)), k)
    return make


MODELS = {"monster_golem_stone": build("monster_golem_stone", STONE),
          "monster_golem_clay": build("monster_golem_clay", CLAY),
          "monster_golem_basalt": build("monster_golem_basalt", BASALT),
          "monster_golem_servant": build("monster_golem_servant", STONE, k=0.55)}
