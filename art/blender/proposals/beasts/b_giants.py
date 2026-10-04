"""Two-legged great enemies and the centaur:

- giant: a bearded giant 9.7 m tall with a tree trunk for a club, on the
  goblins' and trolls' builder and skeleton (creatures/goblin.py, read-only);
  clips idle, walk, attack (an overhead smash) and die;
- demon: a horned demon 4.6 m tall with bat wings, a tail, a blade of fire
  and a whip of fire that cracks with every blow; same clips, the wings,
  the tail and the whip move in all of them;
- centaur archer: a horse's body (the Beast of _bq.py) with a man's torso,
  a bow and a quiver; clips idle, walk, run, attack (kicks forward), shoot
  and die.
"""

import math

from mathutils import Vector

import _bq as B
from _bq import hull, spike, seg, ball, plate, lump, rock, bar, Pose, X, Y, Z

import goblin  # creatures/goblin.py


def _lumps(mb, center, radii, mat, bone, seed, count=14, tones=True):
    return lump(mb, center, radii, mat, bone, seed=seed, count=count, tones=tones)


goblin.lumps = _lumps      # The same lumps with their facet tones in a fixed order (repeatable builds).

GIANT_SHAPE = dict(chest=(0.2, 0.14, 0.17), chest_y=0.0, belly=(0.17, 0.14, 0.14), belly_y=-0.015, arm=0.05, leg=0.062,
                   foot=(0.13, 0.055, 0.05))
DEMON_SHAPE = dict(chest=(0.24, 0.16, 0.18), chest_y=0.0, belly=(0.15, 0.12, 0.13), belly_y=-0.01, arm=0.058, leg=0.066,
                   foot=(0.14, 0.06, 0.055))


def human_head(mb, c, s, bone, beard=True, hair="hair", skin="skin"):
    """A man's head centered at c, `s` its height."""
    def hp(x, y, z):
        return c + Vector((x, y, z)) * s
    lump(mb, c, (0.36 * s, 0.42 * s, 0.46 * s), skin, bone, seed=5, count=18, jitter=0.04)
    lump(mb, hp(0, 0.1, 0.12), (0.39 * s, 0.4 * s, 0.42 * s), hair, bone, seed=6, count=14, tones=False)
    spike(mb, hp(0, -0.36, 0.05), hp(0, -0.56, -0.08), 0.09 * s, skin + "_shade", bone, sides=4)       # Nose.
    hull(mb, [hp(-0.28, -0.36, 0.14), hp(0.28, -0.36, 0.14), hp(-0.28, -0.3, 0.24), hp(0.28, -0.3, 0.24), hp(0, -0.42, 0.2)],
         hair, bone)                                                                                # Brow.
    for sx in (-1, 1):
        ball(mb, hp(sx * 0.15, -0.37, 0.08), 0.05 * s, "eye", bone, segments=5, rings=3)
        ball(mb, hp(sx * 0.37, 0.0, 0.0), 0.09 * s, skin + "_shade", bone, segments=5, rings=3, scale=(0.5, 1, 1.3))
    if beard:
        hull(mb, [hp(-0.3, -0.3, -0.12), hp(0.3, -0.3, -0.12), hp(-0.26, -0.05, -0.3), hp(0.26, -0.05, -0.3),
                  hp(-0.14, -0.4, -0.7), hp(0.14, -0.4, -0.7), hp(0, -0.48, -0.4), hp(0, -0.3, -0.9)], hair, bone)
    return hp


def fix_smash(m, pts, hunch=14.0, arm=0.0):
    """Replaces the trolls' attack clip by the same overhead smash with the
    feet planted after the hips lean (in the original they sink a little,
    which shows at these sizes); `arm` stops the blow that many degrees
    higher (a bigger fist)."""
    h = pts["top_z"]

    def smash(t):
        w = B.pulse(t, 0.0, 0.4, 0.46, 0.56)
        s = B.pulse(t, 0.46, 0.56, 0.66, 1.0)
        pose = Pose(m, (0, (0.02 * w - 0.06 * s) * h, (-0.03 - 0.07 * s) * h))
        pose.turn("hips", X, 12.0 * s)
        m.stand(pose)
        pose.turn("chest", X, hunch - 16.0 * w + 26.0 * s)
        pose.turn("chest", Z, 12.0 * w - 12.0 * s)
        pose.turn("head", X, -hunch - 10.0 * s)
        pose.turn("upper_arm.R", X, -14.0 - 150.0 * w - (50.0 + arm) * s)
        pose.turn("lower_arm.R", X, -28.0 - 40.0 * w + 10.0 * s)
        pose.turn("hand.R", X, -20.0 * w + 30.0 * s)
        m.arm(pose, "L", -30.0 * w + 10.0 * s, 20.0, out=10.0 + 10.0 * w)
        return B.P.from_pose(pose)
    m._clips = [c if c[0] != "attack" else (c[0], c[1], c[2], smash, c[4]) for c in m._clips]


def add_bones(m, bones):
    m.set_bones(m.bones + [B.P.rigs.Bone(name, head, tail, parent) for name, head, tail, parent in bones])


def giant(name, skin, hair, k=4.0, frost=False):
    pts = goblin.scaled(goblin.TROLL, k)
    h = pts["top_z"]
    mb = B.P.kit.begin()
    goblin.brute(mb, pts, GIANT_SHAPE)
    c = Vector((0, -0.03 * h, pts["neck_z"] + 0.085 * h))
    seg(mb, (0, 0, pts["neck_z"] - 0.03 * h), c, 0.05 * h, 0.045 * h, "skin_shade", "head")
    human_head(mb, c, 0.2 * h, "head")
    goblin.club(mb, pts, 1.15 * k, 0.16 * k, spikes=frost, mat="wood" if not frost else "ice")
    hand = Vector((-pts["hand"][0], pts["hand"][1] - 1.0 * k, pts["hand"][2] + 0.28 * k))
    if not frost:                                               # Stubs of branches on the trunk.
        for i, d in enumerate(((1, 0, 0.6), (-0.8, 0, 0.8), (0.3, 0, 1))):
            d = Vector(d).normalized()
            seg(mb, hand + Vector((0, 0.3 * k * i, -0.06 * k * i)), hand + Vector((0, 0.3 * k * i, -0.06 * k * i)) + d * 0.3 * k,
                0.05 * k, 0.03 * k, "wood_dark", "hand.R", sides=5)
    # A fur mantle over the shoulders and bracers.
    for sx in (-1, 1):
        lump(mb, (sx * 0.15 * h, 0.02 * h, pts["neck_z"] - 0.01 * h), (0.12 * h, 0.11 * h, 0.05 * h), "fur", "chest",
             seed=20 + sx, count=12, tones=False)
        side = "L" if sx > 0 else "R"
        w = Vector((pts["wrist"][0] * sx, pts["wrist"][1], pts["wrist"][2]))
        mb.cylinder(w + Vector((0, 0, 0.02 * h)), w + Vector((0, 0, 0.07 * h)), 0.05 * h, 0.055 * h, "leather_dark",
                    weights={f"lower_arm.{side}": 1.0}, segments=7)
    lump(mb, (0, 0.06 * h, pts["neck_z"] - 0.03 * h), (0.16 * h, 0.07 * h, 0.09 * h), "fur", "chest", seed=24, count=12,
         tones=False)
    ball(mb, (0, -GIANT_SHAPE["belly"][1] * h * 1.02, pts["waist_z"]), 0.035 * h, "tooth", "hips", segments=6, rings=4)
    cols = goblin.skin(skin)
    cols.update(B.palette(hair=hair, fur=0x6A5A4A if not frost else 0xE8EEF2, eye=0x1A1412 if not frost else 0x8ADCFF,
                          ice=0xA8DCF4, ice_dark=0x6FB8E8))
    m = goblin.mech(pts, "troll")
    fix_smash(m, pts, arm=8.0)
    B.P.kit.save(mb, B.FAMILY, name, cols, mech=m)


def demon(name, skin, k=1.9):
    pts = goblin.scaled(goblin.TROLL, k)
    h = pts["top_z"]
    mb = B.P.kit.begin()
    goblin.brute(mb, pts, DEMON_SHAPE)
    c = Vector((0, -0.05 * h, pts["neck_z"] + 0.07 * h))

    def hp(x, y, z):
        return c + Vector((x, y, z)) * h
    lump(mb, c, (0.085 * h, 0.095 * h, 0.085 * h), "skin", "head", seed=5, count=16)
    hull(mb, [hp(-0.07, -0.08, -0.03), hp(0.07, -0.08, -0.03), hp(-0.055, -0.12, -0.1), hp(0.055, -0.12, -0.1),
              hp(-0.07, 0.0, -0.06), hp(0.07, 0.0, -0.06), hp(0, -0.13, -0.06)], "skin_shade", "head")       # Jaw.
    hull(mb, [hp(-0.075, -0.09, 0.025), hp(0.075, -0.09, 0.025), hp(-0.075, -0.07, 0.05), hp(0.075, -0.07, 0.05),
              hp(0, -0.105, 0.035)], "skin_shade", "head")                                               # Brow.
    for sx in (-1, 1):
        ball(mb, hp(sx * 0.036, -0.088, 0.008), 0.014 * h, "fire_c", "head", segments=5, rings=3)
        spike(mb, hp(sx * 0.04, -0.115, -0.07), hp(sx * 0.05, -0.13, -0.01), 0.013 * h, "tooth", "head")
        B.horn(mb, hp(sx * 0.06, 0.0, 0.05), [hp(sx * 0.17, 0.03, 0.08), hp(sx * 0.24, -0.02, 0.17), hp(sx * 0.22, -0.1, 0.27)],
               0.04 * h, "horn", "head", sides=6)
    # Cracks of fire on the chest and a crown of flames.
    for i in range(5):
        a = i * 1.3
        zc = pts["waist_z"] + 0.1 * h + 0.045 * h * i
        plate(mb, [(-0.02 * h + 0.05 * h * math.sin(a), -DEMON_SHAPE["chest"][1] * h * 1.0, zc),
                   (0.03 * h + 0.05 * h * math.sin(a), -DEMON_SHAPE["chest"][1] * h * 1.02, zc + 0.01 * h),
                   (0.01 * h + 0.05 * h * math.sin(a + 1), -DEMON_SHAPE["chest"][1] * h * 1.0, zc + 0.05 * h)], 0.03 * h,
              "fire_b", "chest")
    for i in range(4):
        spike(mb, hp(-0.03 + 0.02 * i, 0.03, 0.07), hp(-0.045 + 0.03 * i, 0.07, 0.17 + 0.02 * (i % 2)), 0.02 * h, "fire_b", "head")
    # Wings on the back.
    bones = []
    for side, sx in B.SIDES:
        sh = Vector((sx * 0.1 * h, 0.14 * h, pts["neck_z"] - 0.06 * h))
        el = sh + Vector((sx * 0.3 * h, 0.12 * h, 0.3 * h))
        tip = el + Vector((sx * 0.55 * h, 0.1 * h, -0.05 * h))
        B.wing_membrane(mb, sx, sh, el, tip, Vector((sx * 0.06 * h, 0.16 * h, pts["waist_z"])), arm="skin", dark="skin_shade",
                        claw="horn", r=0.03 * h, chord=0.42 * h, thick=0.012 * h)
        bones += [(f"wing.1.{side}", tuple(sh), tuple(el), "chest"), (f"wing.2.{side}", tuple(el), tuple(tip), f"wing.1.{side}")]
    # Tail.
    hip = pts["hip"][2]
    tail = [Vector((0, 0.1 * h, hip + 0.04 * h)), Vector((0, 0.26 * h, hip - 0.03 * h)), Vector((0, 0.4 * h, hip - 0.08 * h)),
            Vector((0, 0.52 * h, hip - 0.08 * h)), Vector((0, 0.62 * h, hip - 0.02 * h))]
    B.chain(mb, "tail", tail, [0.05 * h, 0.04 * h, 0.03 * h, 0.022 * h, 0.012 * h], ("skin", "skin_shade"))
    spike(mb, tail[-1], tail[-1] + Vector((0, 0.09 * h, 0.01 * h)), 0.035 * h, "horn", "tail.4")
    bones += B.chain_bones("tail", tail, "hips")[0]
    # A blade of fire in the right hand (the club's shape), a whip of fire in the left.
    goblin.club(mb, pts, 1.2 * k, 0.1 * k, spikes=False, mat="blade")
    hand = Vector((pts["hand"][0], pts["hand"][1], pts["hand"][2]))
    whip = [hand + Vector((0, -0.02 * h, 0.0)) + Vector((0.02 * h * i, -0.09 * h * i, 0.035 * h * i - 0.002 * h * i * i))
            for i in range(8)]
    whip_r = [0.02 * h * (1 - 0.1 * i) for i in range(8)]
    B.chain(mb, "whip", whip, whip_r, ("fire_a", "fire_b", "fire_c"), sides=5)
    for i in range(7):
        if i % 2 == 0:
            spike(mb, whip[i + 1], whip[i + 1] + Vector((0, -0.02 * h, 0.07 * h)), 0.016 * h, "fire_c", f"whip.{i + 1}")
    bones += B.chain_bones("whip", whip, "hand.L")[0]
    m = goblin.mech(pts, "troll")
    fix_smash(m, pts)
    add_bones(m, bones)

    def live(strike):
        def fn(pose, t):
            p = 2 * math.pi * t
            hit = B.pulse(t, 0.46, 0.56, 0.66, 1.0) if strike else 0.0
            wind = B.pulse(t, 0.0, 0.4, 0.46, 0.56) if strike else 0.0
            for side, sx in B.SIDES:
                pose.turn(f"wing.1.{side}", Y, -sx * (6.0 * math.sin(p) + 30.0 * wind - 16.0 * hit))
                pose.turn(f"wing.1.{side}", Z, sx * (14.0 + 4.0 * math.sin(p)))
                pose.turn(f"wing.2.{side}", Y, sx * (34.0 + 8.0 * math.sin(p + 0.6) - 26.0 * wind))
            for i in range(4):
                pose.turn(f"tail.{i + 1}", Z, 9.0 * math.sin(p - i * 0.8))
            for i in range(7):
                pose.turn(f"whip.{i + 1}", Z, 10.0 * math.sin(2 * p - i * 0.9) * (1 - hit))
                pose.turn(f"whip.{i + 1}", X, 4.0 * math.sin(2 * p - i * 0.9 + 1.2) - 12.0 * wind + 2.0 * hit)
            if strike:                                          # The whip arm lashes forward.
                pose.turn("upper_arm.L", X, 30.0 * wind - 60.0 * hit)
        return fn
    for clip in ("idle", "walk"):
        B.extend(m, clip, live(False))
    B.extend(m, "attack", live(True))
    cols = goblin.skin(skin)
    cols.update(B.palette(horn=0x1E1A1C, membrane=0x4A1418, eye=0xFFE27A, fire_a=0xE8501E, fire_b=0xFF9A2A, fire_c=0xFFE27A, blade=0xFF9A2A,
                          blade_dark=0xE8501E, leather=0x2A2226, leather_dark=0x1A1418, tooth=0xEFE6CC))
    B.P.kit.save(mb, B.FAMILY, name, cols, mech=m)


def centaur(name, coat, skin, hair, k=1.15):
    mb = B.P.kit.begin()
    q = B.Beast(L=1.15, zs=1.42, w=0.19, hl=1.12, fb=-0.1, hb=0.16, ankle=0.11, toe=0.1)
    q.trunk(mb, "coat", (0.29, 0.42, 0.36), (0.28, 0.5, 0.33), (0.29, 0.42, 0.35))
    q.legs(mb, 0.1, 0.05, "coat", "coat_shade", foot="hoof", foot_mat="hoof", foot_r=0.065, hind=1.1)
    y = -0.62
    torso = [(0, y + 0.06, 1.4), (0, y, 1.78), (0, y - 0.02, 2.2)]
    h = q.neck(mb, torso, [0.25, 0.2, 0.1], ("coat", "skin"))
    lump(mb, (0, y - 0.01, 2.0), (0.24, 0.15, 0.2), "skin", "neck.2", seed=4, count=14)            # Chest.
    mb.cylinder((0, y, 1.74), (0, y, 1.8), 0.215, 0.215, "leather", weights={"neck.1": 1.0}, segments=8)   # Belt.
    human_head(mb, h + Vector((0, -0.02, 0.14)), 0.27, "head", beard=True)
    q.tail(mb, [(0, 0.62, 1.44), (0, 0.84, 1.32), (0, 0.93, 0.92), (0, 0.91, 0.47)], [0.06, 0.1, 0.09, 0.03], ("hair",))
    for side, sx in B.SIDES:
        sh, el, wr = Vector((sx * 0.27, y, 2.1)), Vector((sx * 0.31, y + 0.03, 1.8)), Vector((sx * 0.31, y - 0.1, 1.55))
        ball(mb, sh, 0.085, "skin", f"arm_up.{side}", segments=6, rings=4)
        seg(mb, sh, el, 0.065, 0.05, "skin", f"arm_up.{side}")
        seg(mb, el, wr, 0.05, 0.04, "skin_shade", f"arm_low.{side}")
        ball(mb, wr + Vector((0, -0.02, -0.03)), 0.05, "skin", f"arm_low.{side}", segments=5, rings=3)
        q.bones += [(f"arm_up.{side}", tuple(sh), tuple(el), "neck.2"), (f"arm_low.{side}", tuple(el), tuple(wr), f"arm_up.{side}")]
    # The bow in the left hand: across the forearm, so it stands upright when the arm is raised to aim.
    g = Vector((0.31, y - 0.12, 1.52))
    limb = [g + Vector((0, d, 0.02 + 0.5 * (abs(d) / 0.62) ** 2)) for d in (-0.62, -0.42, -0.2, 0.0, 0.2, 0.42, 0.62)]
    for a, b in zip(limb, limb[1:]):
        seg(mb, a, b, 0.018, 0.018, "wood", "arm_low.L", sides=5)
    seg(mb, limb[0], limb[-1], 0.004, 0.004, "string", "arm_low.L", sides=3)
    # An arrow in the right hand and a quiver on the back.
    r = Vector((-0.31, y - 0.12, 1.52))
    seg(mb, r + Vector((0, 0, 0.08)), r + Vector((0, 0, -0.62)), 0.008, 0.008, "wood", "arm_low.R", sides=4)
    spike(mb, r + Vector((0, 0, -0.62)), r + Vector((0, 0, -0.72)), 0.02, "iron", "arm_low.R")
    seg(mb, (0.08, y + 0.17, 1.8), (-0.1, y + 0.2, 2.3), 0.06, 0.07, "leather", "neck.2", sides=6)
    for i in range(3):
        spike(mb, (-0.1 + 0.03 * i, y + 0.2, 2.42), (-0.1 + 0.03 * i, y + 0.2, 2.3), 0.03, "feather", "neck.2", sides=3)
    q.mech()

    def arms(pose, t):
        p = 2 * math.pi * t
        pose.turn("arm_up.L", X, -18.0 + 2.0 * math.sin(2 * p))
        pose.turn("arm_low.L", X, -30.0)
        pose.turn("arm_up.R", X, 6.0 + 2.0 * math.sin(2 * p))
        pose.turn("arm_low.R", X, -16.0)
    q.clips(walk=dict(frames=24, duty=0.64, lift=0.12, crouch=0.05, nod=1.0, wag=5.0),
            run=dict(frames=13, duty=0.4, lift=0.2, crouch=0.09, nod=1.5, lean=2.0), jaw=0.0, extra_idle=arms,
            extra_walk=arms, wide=0.6, idle_look=6.0)
    m = q.m

    def shoot(t):
        aim = B.pulse(t, 0.0, 0.25, 0.75, 1.0)
        draw = B.pulse(t, 0.2, 0.5, 0.6, 0.64)
        pose = Pose(m, (0, 0, -0.01 * aim))
        q.stand(pose)
        pose.turn("neck.2", Z, -28.0 * aim)                  # The chest turns: the bow arm leads.
        pose.turn("head", Z, 22.0 * aim)
        pose.turn("arm_up.L", X, -18.0 - 70.0 * aim)
        pose.turn("arm_up.L", Z, 26.0 * aim)
        pose.turn("arm_low.L", X, -30.0 + 22.0 * aim)
        pose.turn("arm_up.R", X, 6.0 - 86.0 * aim)
        pose.turn("arm_up.R", Z, 20.0 * aim)
        pose.turn("arm_low.R", X, -16.0 - 20.0 * aim - 95.0 * draw)
        q.tail_pose(pose, lambda i: 6.0 * math.sin(2 * math.pi * t - i))
        return B.P.from_pose(pose)
    m.clip("shoot", 2.0, shoot)
    cols = {**B.shades("coat", coat), **B.shades("skin", skin),
            **B.palette(hair=hair, hoof=0x2A2624, eye=0x151012, wood=0x7A5636, string=0xE8E0C8, iron=0x8A8F96,
                        leather=0x5E3F36, feather=0xC8302A)}
    B.save(mb, name, cols, m, k)


MODELS = {
    "boss_giant": B.builder(giant, "boss_giant", 0xC9A27A, 0x6A4A32),
    "boss_giant_frost": B.builder(giant, "boss_giant_frost", 0x9FB8C8, 0xE8EEF2, frost=True),
    "boss_demon": B.builder(demon, "boss_demon", 0x7A2A26),
    "mythic_centaur_archer": B.builder(centaur, "mythic_centaur_archer", 0x6A4A32, 0xC9946A, 0x2E2420),
}
