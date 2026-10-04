"""Minotaur: a bull-headed giant 2.3 m tall with horns, a nose ring, a fur
mane over the shoulders, a leather kilt, hooves and a double-bladed axe.
It shares the goblins' and trolls' builder and skeleton. Clips: idle, walk,
attack (an overhead chop) and die (falls on its back). Variants: brown,
black with red eyes, and white."""

from mathutils import Vector

import _parts as P
import goblin
from _parts import hull, bar, rock, seg, spike, ball

PTS = goblin.scaled(goblin.TROLL, 0.93)
SHAPE = dict(chest=(0.24, 0.17, 0.18), chest_y=0.0, belly=(0.17, 0.145, 0.15), belly_y=-0.01, arm=0.06, leg=0.066,
             foot=(0.1, 0.06, 0.07))


def head(mb):
    h = PTS["top_z"]
    c = Vector((0, -0.06 * h, PTS["neck_z"] + 0.07 * h))
    goblin.lumps(mb, c, (0.1 * h, 0.11 * h, 0.1 * h), "skin", "head", 5, 16)
    hull(mb, [c + Vector(o) * h for o in ((-0.06, -0.08, 0.0), (0.06, -0.08, 0.0), (-0.07, -0.2, -0.04),
                                          (0.07, -0.2, -0.04), (-0.06, -0.19, -0.1), (0.06, -0.19, -0.1),
                                          (-0.05, -0.06, -0.09), (0.05, -0.06, -0.09))], "muzzle", "head")
    for s in (-1, 1):
        ball(mb, c + Vector((s * 0.055, -0.09, 0.03)) * h, 0.014 * h, "eye", "head")
        ball(mb, c + Vector((s * 0.03, -0.205, -0.06)) * h, 0.012 * h, "pupil", "head")       # Nostrils.
        a, b, t = (c + Vector(o) * h for o in ((s * 0.08, 0.0, 0.06), (s * 0.2, -0.02, 0.1), (s * 0.24, -0.1, 0.24)))
        seg(mb, a, b, 0.035 * h, 0.028 * h, "tooth", "head", sides=5)
        spike(mb, b, t, 0.028 * h, "tooth", "head", sides=5)
        P.plate(mb, [c + Vector((s * 0.09, 0.02, 0.02)) * h, c + Vector((s * 0.09, 0.05, -0.02)) * h,
                     c + Vector((s * 0.18, 0.06, -0.01)) * h], 0.016 * h, "skin_shade", "head")   # Ears.
    mb.cylinder(c + Vector((0, -0.2, -0.085)) * h, c + Vector((0, -0.205, -0.085)) * h, 0.03 * h, 0.03 * h, "iron",
                weights={"head": 1.0}, segments=6)
    for i, (x, y, z, r) in enumerate(((0.0, 0.08, 0.02, 0.13), (0.14, 0.06, -0.06, 0.1), (-0.14, 0.06, -0.06, 0.1),
                                      (0.0, 0.1, -0.12, 0.14))):
        rock(mb, c + Vector((x, y, z)) * h, (r * h, r * h * 0.9, r * h), "hair", "chest" if i else "head", count=10,
             seed=30 + i)


def axe(mb):
    hd = Vector((-PTS["hand"][0], PTS["hand"][1], PTS["hand"][2] + 0.06))
    a, b = hd + Vector((0, 0.3, -0.03)), hd + Vector((0, -1.25, 0.25))
    seg(mb, a, b, 0.035, 0.03, "wood", "hand.R", sides=6)
    d = (b - a).normalized()
    up = Vector((0, 0, 1)) - d * d.z
    up.normalize()
    c = b - d * 0.2
    for s in (-1, 1):
        hull(mb, [c + d * 0.12 + Vector((0.02, 0, 0)), c + d * 0.12 - Vector((0.02, 0, 0)), c - d * 0.12 + Vector((0.02, 0, 0)),
                  c - d * 0.12 - Vector((0.02, 0, 0)), c + up * s * 0.34 + d * 0.3, c + up * s * 0.38,
                  c + up * s * 0.34 - d * 0.3], "iron", "hand.R")
    spike(mb, b, b + d * 0.18, 0.035, "iron", "hand.R")


def build(name, color, hair, eye=0xF2D23A):
    def make():
        mb = P.kit.begin()
        goblin.brute(mb, PTS, SHAPE)
        head(mb)
        axe(mb)
        colors = goblin.skin(color)
        colors.update(P.palette(hair=hair, muzzle=P._mix(color, 0xFFFFFF, 0.35), eye=eye, tooth=0xE6D8B8))
        P.kit.save(mb, P.FAMILY, name, colors, mech=goblin.mech(PTS, "troll"))
    return make


MODELS = {"monster_minotaur": build("monster_minotaur", 0x7A5236, 0x3A2A20),
          "monster_minotaur_black": build("monster_minotaur_black", 0x34302E, 0x1A1818, eye=0xE0342A),
          "monster_minotaur_white": build("monster_minotaur_white", 0xD8D2C4, 0x8A8478)}
