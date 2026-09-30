"""Lion: golden body with lighter muzzle and belly, a big faceted mane of
rust spikes around the face and down the chest, and a tufted tail."""

import math

from mathutils import Vector

import common
import studies

X = 0.2  # Half the distance between left and right legs.
HEAD = ((0, -1.02, 1.22), (0.19, 0.2, 0.19))
MUZZLE = ((0, -1.2, 1.12), (0.12, 0.12, 0.1))
MANE = [((0, -0.86, 1.18), (0.36, 0.27, 0.4)),   # Around the head.
        ((0, -0.7, 0.92), (0.3, 0.24, 0.34))]    # Down the chest.
FACE_Y = -1.06  # In front of this the head is golden; behind it, mane.
TAIL = [(0, 0.82, 0.95), (0, 1.06, 0.86), (0, 1.25, 0.66), (0.03, 1.36, 0.48), (0.07, 1.42, 0.36)]
TAIL_R = [0.06, 0.05, 0.045, 0.042, 0.04]


def mane_back_y(z):
    """The mane ends behind along a slanted line: further back up high."""
    return -0.5 + 0.35 * (z - 1.0)


def legs_capsules():
    caps = []
    for s in (-1, 1):
        x = s * X
        caps += [
            ((x * 0.9, -0.5, 0.86), (x, -0.5, 0.45), 0.145, 0.11),        # Front upper leg.
            ((x, -0.5, 0.45), (x, -0.53, 0.1), 0.1, 0.085),            # Front lower leg.
            ((x, -0.52, 0.07), (x, -0.68, 0.075), 0.085, 0.078),         # Front paw.
            ((x * 0.9, 0.55, 0.72), (x, 0.72, 0.33), 0.135, 0.09),       # Hind leg to the hock.
            ((x, 0.72, 0.33), (x, 0.64, 0.1), 0.085, 0.078),             # Hind lower leg.
            ((x, 0.66, 0.07), (x, 0.5, 0.075), 0.08, 0.074),           # Hind paw.
        ]
    return caps


class Lion(studies.Spec):
    name = "lion"
    max_tris = 2000
    budget = 1000
    colors = {
        "gold": common.rgb(0xE8A73A),
        "gold_light": common.rgb(0xF0B84E),
        "gold_shade": common.rgb(0xD8942C),
        "cream": common.rgb(0xF3D9A0),
        "mane": common.rgb(0xB9571F),
        "mane_dark": common.rgb(0x8F3E17),
        "nose": common.rgb(0x3B2521),
        "eye": common.rgb(0x151012),
    }
    ellipsoids = [
        ((0, -0.38, 0.87), (0.28, 0.45, 0.3)),    # Chest.
        ((0, 0.0, 0.85), (0.25, 0.42, 0.26)),     # Belly.
        ((0, 0.4, 0.87), (0.24, 0.43, 0.27)),     # Hips.
        ((X * 0.85, 0.52, 0.73), (0.12, 0.24, 0.26)),   # Thighs.
        ((-X * 0.85, 0.52, 0.73), (0.12, 0.24, 0.26)),
        HEAD, MUZZLE,
    ] + MANE
    capsules = ([((0, -0.62, 0.95), (0, -0.88, 1.12), 0.22, 0.2)] + legs_capsules()
                + [(a, b, ra, rb) for a, b, ra, rb in zip(TAIL, TAIL[1:], TAIL_R, TAIL_R[1:])])
    cuts = [((0, FACE_Y, 0), (0, 1, 0), lambda c, n: c.z > 0.8 and c.y < -0.9)]
    tone_material = "gold"

    def __init__(self):
        # The slanted back edge of the mane, as a cut so its border is crisp.
        n = Vector((0, 1, -0.35)).normalized()
        self.cuts = self.cuts + [((0, -0.5, 1.0), n, lambda c, nn: c.z > 0.6 and c.y < -0.2)]

    def is_mane(self, c):
        return FACE_Y < c.y < mane_back_y(c.z) and c.z > 0.6 and c.y < -0.4

    def paint(self, c, n):
        if c.y < -1.14 and c.z < 1.16:
            return "cream"  # Muzzle and chin.
        if self.is_mane(c):
            return "mane"
        if -0.55 < c.y < 0.8 and c.z < 0.68 and n.z < -0.1 and abs(c.x) < 0.2:
            return "cream"  # Belly.
        return "gold"

    def details(self, mb):
        hc = Vector(HEAD[0])
        # Mane spikes: faceted cones in rings around the face, pointing out
        # and back, lighter and darker by turns.
        k = 0
        for ring, (y, reach, length, count) in enumerate(((-0.98, 0.31, 0.16, 13), (-0.8, 0.37, 0.18, 11),
                                                          (-0.62, 0.32, 0.15, 9))):
            for i in range(count):
                a = (i + 0.5 * (ring % 2)) / count * math.tau
                d = Vector((math.sin(a), 0.0, math.cos(a)))
                if ring > 0 and d.z < -0.5:
                    continue  # The chest part is covered by the first ring.
                base = Vector((d.x * reach, y, hc.z + d.z * reach * 1.05))
                if base.z < 0.7:
                    continue
                way = (d + Vector((0, 0.9, -0.25))).normalized()
                tip = base + way * length * (0.85 + 0.15 * ((i * 7 + ring) % 3))
                mb.cylinder(base - way * 0.04, tip, 0.12, 0.0, "mane" if k % 2 else "mane_dark", segments=4)
                k += 1
        for s in (-1, 1):
            mb.sphere((s * 0.085, -1.18, 1.27), 0.024, "eye", segments=6, rings=4)
            studies.flap(mb, (s * 0.06, -1.07, 1.36), (s * 0.17, -1.05, 1.32), (s * 0.16, -1.09, 1.46),
                         0.03, "gold")
        mb.sphere((0, -1.31, 1.16), 0.045, "nose", segments=6, rings=4, scale=(1.0, 0.5, 0.6))
        # Tail tuft.
        tip = Vector(TAIL[-1])
        mb.sphere(tip + Vector((0.005, 0.01, -0.07)), 0.07, "mane_dark", segments=6, rings=4,
                  scale=(1.0, 1.0, 1.5))


SPECS = [Lion()]
