"""More two-legged enemies on the goblins' and trolls' builder and
skeleton (goblin.py), each with its own head and gear:

- cyclops: 2.8 m, one big eye, a horn, a pot belly and a club;
- werewolf: 1.9 m, a wolf's head, ears, fangs, claws, a mane of fur spikes
  and a tail; fast clips (idle, walk, run, attack, die);
- zombie: 1.75 m, pale green, a slack jaw, sunken eyes and torn rags; slow
  clips (idle, walk, attack, die).
"""

from mathutils import Vector

import _parts as P
import goblin
from _parts import hull, bar, rock, seg, spike, ball, box, plate

CYCLOPS_PTS = goblin.scaled(goblin.TROLL, 1.15)
WOLF_PTS = goblin.scaled(goblin.GOBLIN, 1.75)
ZOMBIE_PTS = goblin.scaled(goblin.GOBLIN, 1.6)
WOLF_SHAPE = dict(chest=(0.165, 0.13, 0.14), chest_y=-0.01, belly=(0.115, 0.1, 0.1), belly_y=0.0, arm=0.044, leg=0.05,
                  foot=(0.13, 0.045, 0.05))
ZOMBIE_SHAPE = dict(chest=(0.125, 0.085, 0.125), chest_y=0.0, belly=(0.105, 0.08, 0.1), belly_y=0.0, arm=0.034,
                    leg=0.043, foot=(0.1, 0.04, 0.04))


def cyclops():
    pts = CYCLOPS_PTS
    h = pts["top_z"]
    mb = P.kit.begin()
    goblin.brute(mb, pts, goblin.OGRE_SHAPE)
    c = Vector((0, -0.05 * h, pts["neck_z"] + 0.08 * h))
    goblin.lumps(mb, c, (0.1 * h, 0.105 * h, 0.1 * h), "skin", "head", 5, 16)
    ball(mb, c + Vector((0, -0.085, 0.02)) * h, 0.042 * h, "tooth", "head", segments=8, rings=5)          # The eye.
    ball(mb, c + Vector((0, -0.118, 0.02)) * h, 0.022 * h, "eye", "head")
    ball(mb, c + Vector((0, -0.136, 0.02)) * h, 0.011 * h, "pupil", "head")
    hull(mb, [c + Vector(o) * h for o in ((-0.07, -0.09, 0.055), (0.07, -0.09, 0.055), (-0.07, -0.07, 0.08),
                                          (0.07, -0.07, 0.08), (0, -0.115, 0.07))], "skin_shade", "head")   # Brow.
    spike(mb, c + Vector((0, -0.05, 0.09)) * h, c + Vector((0, -0.09, 0.19)) * h, 0.03 * h, "tooth", "head", sides=5)
    box(mb, c + Vector((0, -0.095, -0.055)) * h, (0.09 * h, 0.03 * h, 0.018 * h), "pupil", "head")
    for s in (-1, 1):
        spike(mb, c + Vector((s * 0.03, -0.1, -0.06)) * h, c + Vector((s * 0.035, -0.11, -0.025)) * h, 0.012 * h,
              "tooth", "head")
        plate(mb, [c + Vector((s * 0.09, 0.0, 0.02)) * h, c + Vector((s * 0.09, 0.03, -0.03)) * h,
                   c + Vector((s * 0.15, 0.04, 0.02)) * h], 0.014 * h, "skin_shade", "head")
    goblin.club(mb, pts, 1.5, 0.2, spikes=False)
    colors = goblin.skin(0xB89A7A)
    colors.update(P.palette(eye=0x3F86C8))
    P.kit.save(mb, P.FAMILY, "monster_cyclops", colors, mech=goblin.mech(pts, "troll"))


def werewolf(name, fur, eye):
    def make():
        pts = WOLF_PTS
        h = pts["top_z"]
        mb = P.kit.begin()
        goblin.brute(mb, pts, WOLF_SHAPE)
        c = Vector((0, -0.04 * h, pts["neck_z"] + 0.08 * h))
        goblin.lumps(mb, c, (0.08 * h, 0.09 * h, 0.08 * h), "skin", "head", 5, 14)
        hull(mb, [c + Vector(o) * h for o in ((-0.045, -0.06, 0.02), (0.045, -0.06, 0.02), (-0.03, -0.19, -0.01),
                                              (0.03, -0.19, -0.01), (-0.045, -0.06, -0.05), (0.045, -0.06, -0.05),
                                              (-0.028, -0.18, -0.05), (0.028, -0.18, -0.05))], "skin_shade", "head")
        ball(mb, c + Vector((0, -0.195, -0.01)) * h, 0.016 * h, "pupil", "head")
        for s in (-1, 1):
            ball(mb, c + Vector((s * 0.04, -0.075, 0.03)) * h, 0.012 * h, "eye", "head")
            plate(mb, [c + Vector((s * 0.03, 0.0, 0.07)) * h, c + Vector((s * 0.075, 0.02, 0.04)) * h,
                       c + Vector((s * 0.07, 0.01, 0.16)) * h], 0.014 * h, "skin_shade", "head")
            spike(mb, c + Vector((s * 0.025, -0.17, -0.045)) * h, c + Vector((s * 0.025, -0.175, -0.085)) * h, 0.008 * h,
                  "tooth", "head")
            wrist = Vector((pts["hand"][0] * s, pts["hand"][1], pts["hand"][2]))
            for dx in (-0.02, 0.0, 0.02):
                spike(mb, wrist + Vector((dx * h, -0.01 * h, -0.02 * h)), wrist + Vector((dx * 1.4 * h, -0.05 * h, -0.08 * h)),
                      0.008 * h, "tooth", "hand.L" if s > 0 else "hand.R")
        for i in range(6):                                   # A mane down the back.
            z = pts["neck_z"] + 0.04 * h - i * 0.045 * h
            spike(mb, (0, 0.1 * h, z), (0, 0.2 * h, z + 0.05 * h), 0.035 * h, "hair", "chest" if i < 5 else "hips")
        hip = pts["hip"][2]
        seg(mb, (0, 0.1 * h, hip + 0.05 * h), (0, 0.3 * h, hip - 0.1 * h), 0.04 * h, 0.05 * h, "hair", "hips")
        spike(mb, (0, 0.3 * h, hip - 0.1 * h), (0, 0.4 * h, hip - 0.22 * h), 0.05 * h, "hair", "hips")
        colors = goblin.skin(fur)
        colors.update(P.palette(hair=P._mix(fur, 0x000000, 0.4), eye=eye, leather=0x4A4A52, leather_dark=0x34343A))
        P.kit.save(mb, P.FAMILY, name, colors, mech=goblin.mech(pts, "goblin"))
    return make


def zombie(name, skin_color, cloth):
    def make():
        pts = ZOMBIE_PTS
        h = pts["top_z"]
        mb = P.kit.begin()
        goblin.brute(mb, pts, ZOMBIE_SHAPE)
        c = Vector((0, -0.01 * h, pts["neck_z"] + 0.085 * h))
        seg(mb, (0, 0, pts["neck_z"] - 0.02 * h), c + Vector((0, 0.01, -0.05)) * h, 0.03 * h, 0.03 * h, "skin_shade", "head")
        goblin.lumps(mb, c, (0.062 * h, 0.07 * h, 0.075 * h), "skin", "head", 5, 16)
        hull(mb, [c + Vector(o) * h for o in ((-0.045, -0.055, -0.05), (0.045, -0.055, -0.05), (-0.04, -0.06, -0.1),
                                              (0.04, -0.06, -0.1), (-0.045, 0.0, -0.06), (0.045, 0.0, -0.06),
                                              (0.01, -0.07, -0.085))], "skin_shade", "head")     # A slack jaw, askew.
        box(mb, c + Vector((0.004, -0.062, -0.052)) * h, (0.06 * h, 0.02 * h, 0.022 * h), "pupil", "head")
        for s in (-1, 1):
            box(mb, c + Vector((s * 0.026, -0.06, 0.012)) * h, (0.026 * h, 0.02 * h, 0.022 * h), "pupil", "head")
            ball(mb, c + Vector((s * 0.026, -0.068, 0.012)) * h, 0.006 * h, "eye", "head", segments=4, rings=3)
        for i, d in enumerate(((0.3, 0.3, 1), (-0.5, 0.2, 0.9), (0.0, 0.8, 0.6))):                # Tufts of hair.
            d = Vector(d).normalized()
            spike(mb, c + d * 0.05 * h, c + d * 0.1 * h, 0.02 * h, "hair", "head")
        # A torn tunic over the chest, with a ragged hem.
        w, z0, z1 = 0.135 * h, pts["waist_z"] - 0.02 * h, pts["neck_z"] - 0.03 * h
        hull(mb, [(-w, -0.095 * h, z1), (w, -0.095 * h, z1), (-w, 0.095 * h, z1), (w, 0.095 * h, z1),
                  (-w * 0.9, -0.09 * h, z0), (w * 0.9, -0.09 * h, z0), (-w * 0.9, 0.09 * h, z0), (w * 0.9, 0.09 * h, z0)],
             "cloth", "chest")
        for i in range(5):
            x = (-0.1 + 0.05 * i) * h
            plate(mb, [(x - 0.022 * h, -0.092 * h, z0), (x + 0.022 * h, -0.092 * h, z0),
                       (x + 0.01 * h * (i % 2), -0.1 * h, z0 - (0.05 + 0.03 * (i % 3)) * h)], 0.012 * h, "cloth", "hips")
        colors = goblin.skin(skin_color)
        colors.update(P.palette(cloth=cloth, eye=0xD8E04A, hair=0x3A3A32, leather=P._mix(cloth, 0x000000, 0.3),
                                leather_dark=P._mix(cloth, 0x000000, 0.5)))
        P.kit.save(mb, P.FAMILY, name, colors, mech=goblin.mech(pts, "troll"))
    return make


MODELS = {
    "monster_cyclops": cyclops,
    "enemy_werewolf": werewolf("enemy_werewolf", 0x6A5E56, 0xF2D23A),
    "enemy_werewolf_black": werewolf("enemy_werewolf_black", 0x2E2C32, 0xE0342A),
    "enemy_zombie": zombie("enemy_zombie", 0x8AA07A, 0x6A5A4A),
    "enemy_zombie_plague": zombie("enemy_zombie_plague", 0x9A8AA0, 0x4A5A3A),
}
