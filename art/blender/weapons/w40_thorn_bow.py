"""Weapon 40: thorn bow. A thick green bow patched with yellow-green and
amber, with gold thorns along the limbs and a gold crown at the top, two
steel thorns crossing under the crown, a dark spiked ball on the upper
limb, a stud at the grip and a pale string."""

import random

from mathutils import Vector

import common
import studies
import _parts_c as parts

X0 = -0.022   # Shift that centers the whole bow, thorns included, on X = 0.
# The limb from the bottom tip to the top tip: (x, z, radius).
LIMB = [(0.105, 0.045, 0.02), (0.05, 0.14, 0.031), (-0.04, 0.3, 0.039), (-0.105, 0.48, 0.041),
        (-0.135, 0.62, 0.042), (-0.14, 0.7, 0.044), (-0.135, 0.78, 0.042), (-0.105, 0.92, 0.041),
        (-0.04, 1.08, 0.039), (0.04, 1.22, 0.032), (0.1, 1.31, 0.021)]
PATCHES = (0.24, 0.07)   # Share of the limb's facets that are yellow-green, and amber.
BALL = ((0.035, 0.0, 1.0), 0.058)
BALL_SPIKES = [(1, 0, 0.35), (0.6, 0, -0.9), (0.35, 0, 1), (0.4, -0.85, 0.3), (0.4, 0.85, 0.3),
               (-0.15, -0.8, -0.6), (-0.15, 0.8, -0.6), (0.95, 0.0, -0.3)]


def p(x, z, y=0.0):
    return (x + X0, y, z)


def smooth(nodes):
    """The nodes with one more between each pair, on a smooth curve
    (Catmull-Rom) through them."""
    out = []
    for i in range(len(nodes) - 1):
        a, b = Vector(nodes[i]), Vector(nodes[i + 1])
        before = Vector(nodes[max(i - 1, 0)])
        after = Vector(nodes[min(i + 2, len(nodes) - 1)])
        out += [a, (a + b) * 0.5625 - (before + after) * 0.0625]
    return out + [Vector(nodes[-1])]


class ThornBow(studies.Spec):
    name = "w40_thorn_bow"
    colors = {
        **parts.shades("green", 0x3F7A3E, shade=0x2A5632),
        "leaf": common.rgb(0x7EAC48),
        "amber": common.rgb(0xB87A2E),
        "gold": common.rgb(0xE0B63E),
        "iron": common.rgb(0x34343C),
        "steel": common.rgb(0xDCDCDA),     # The thorn points, the string and the stud.
    }
    max_tris = 600
    grip = (LIMB[5][0] + X0, 0.0, LIMB[5][1])

    def details(self, mb):
        parts.begin(mb, self)
        nodes = smooth(LIMB)
        limb = parts.loft(mb, [p(x, z) for x, z, _ in nodes], [(r, r * 1.1) for _, _, r in nodes], 6, "green",
                          tones=0.6, seed=8, twist=0.2)
        # Patches of other colors on scattered facets, as in the picture.
        rnd = random.Random(11)
        leaf, amber = mb._material_index("leaf"), mb._material_index("amber")
        faces = {f for v in limb for f in v.link_faces}
        for f in mb.bm.faces:   # In the builder's order, so every build paints the same facets.
            r = rnd.random() if f in faces else 1.0
            if r < PATCHES[0] + PATCHES[1]:
                f.material_index = leaf if r < PATCHES[0] else amber
        parts.loft(mb, [p(0.103, 0.06), p(0.1, 1.3)], [0.0035, 0.0035], 3, "steel", ref=(1, 0, 0))
        # Gold: the foot, the crown, and thorns along the limbs and around the grip.
        gold = [((0.1, 0.075), (0.145, 0.0), 0.028), ((0.085, 0.07), (0.035, 0.02), 0.018),
                ((0.095, 1.29), (0.094, 1.41), 0.027), ((0.08, 1.275), (0.03, 1.39), 0.025),
                ((-0.105, 0.56), (-0.01, 0.6), 0.034), ((-0.1, 0.87), (-0.03, 0.845), 0.026),
                ((-0.15, 0.7), (-0.235, 0.7), 0.028), ((-0.16, 0.74), (-0.2, 0.815), 0.022),
                ((-0.16, 0.66), (-0.2, 0.585), 0.022)]
        for a, b, r in gold:
            parts.spike(mb, p(*a), p(*b), r, "gold")
        # The long gold fin on the outer side of the lower limb.
        parts.loft(mb, [p(-0.125, 0.43), p(-0.105, 0.31), p(-0.03, 0.15)], [(0.02, 0.016), (0.04, 0.02), 0.0], 4,
                   "gold", tones="light")
        # Steel thorns under the crown: dark at the root, bright at the point.
        for a, b in (((0.1, 1.29), (0.28, 1.36)), ((-0.03, 1.12), (-0.165, 1.225))):
            a, b = Vector(p(*a)), Vector(p(*b))
            parts.loft(mb, [a, a.lerp(b, 0.45), b], [0.016, 0.024, 0.0], 4, ["iron", "steel"], tones="light")
        # The spiked ball.
        center = Vector(p(BALL[0][0], BALL[0][2]))
        parts.ico(mb, center, BALL[1], "iron", subdiv=1, tilt=0.4)
        for d in BALL_SPIKES:
            d = Vector(d).normalized()
            parts.spike(mb, center + d * (BALL[1] * 0.7), center + d * (BALL[1] + 0.045), 0.024, "iron", sides=3)
        parts.ico(mb, p(-0.14, 0.7, -0.046), 0.022, "steel", subdiv=1, scale=(1.0, 0.5, 1.0), tones=None)


SPECS = [ThornBow()]
