"""Giant araucaria: a tall straight trunk with flat tiers of branches that
curve upward and end in dark-green spiky tufts, like umbrellas, and three
small araucarias at its foot; bare, the tiers of branches without tufts.
About 35 m tall and 27 m wide.

All made by hand from the pictures: the trunk's width at every height, the
height, the length and the rise of the limbs seen at both sides of each
tier, and where the small trees stand."""

import math
import random

from mathutils import Vector

import _giant

PROFILE = [(-0.4, 2.5), (1.4, 2.15), (4.0, 1.8), (15.0, 1.45), (25.0, 1.15), (31.2, 0.85)]
# The limbs: (height on the trunk, direction seen from above in degrees,
# 0 = right and 270 = toward the viewer, length, rise of its end). Three
# tiers; in each, first the two limbs seen at the sides in the pictures.
LIMBS = [
    (16.2, 180, 12.4, -1.2), (18.4, 0, 11.4, 0.2), (17.6, 118, 10.2, -0.4), (15.8, 52, 9.8, -0.6),
    (17.2, 268, 8.6, -0.3),
    (23.3, 180, 13.2, 0.4), (24.4, 0, 12.8, 0.6), (22.6, 62, 10.8, 0.2), (24.9, 124, 10.4, 0.5),
    (23.8, 272, 9.4, 0.3),
    (28.0, 180, 12.2, 2.6), (28.4, 0, 12.0, 3.0), (29.2, 92, 10.6, 2.8), (29.0, 268, 9.6, 2.8),
    (29.8, 46, 10.2, 2.6), (29.9, 137, 10.0, 2.6), (30.2, 224, 9.6, 2.4), (30.3, 316, 9.6, 2.4),
]
# The small araucarias: (x, y, height, radius of its crown).
SMALL = [(-5.8, -1.0, 9.8, 3.3), (4.9, 1.6, 13.7, 4.1), (8.1, -1.4, 7.3, 2.7)]
UP = Vector((0.0, 0.0, 1.0))


def radius(z):
    for (z0, r0), (z1, r1) in zip(PROFILE, PROFILE[1:]):
        if z <= z1:
            return r0 + (r1 - r0) * max(0.0, z - z0) / (z1 - z0)
    return PROFILE[-1][1]


class Araucaria(_giant.Giant):

    def shape(self):
        seed = self.o["seed"]
        rnd = random.Random(seed + 5)
        self.tufts = []   # Where a tuft of leaves sits: (center, radius).
        for (z0, r0), (z1, r1) in zip(PROFILE, PROFILE[1:]):
            self.capsules.append(((0, 0, z0), (0, 0, z1), r0, r1))
        self.roots(6, [(1.2, 2.6, 1.0), (2.4, 1.0, 0.8), (3.5, -0.3, 0.45)], seed + 6)
        self.knobs(26, 2.0, 30.0, (0.45, 0.75), seed + 7, axis=lambda z: Vector((0.0, 0.0, z)), out=0.4)
        for z, angle, length, rise in LIMBS:
            a = math.radians(angle + rnd.uniform(-7.0, 7.0))
            self.spray(rnd, UP * z, a, length - 0.9, rise, 0.85, radius(z))
        # The tip of the trunk forks into short twigs, the middle of the top umbrella.
        for k in range(4):
            a = (k + 0.5) * math.tau / 4 + rnd.uniform(-0.3, 0.3)
            d = Vector((math.cos(a), math.sin(a), 0.0))
            top = UP * 31.0
            end = top + d * 2.6 + UP * 3.2
            self.lines.append(([top, top + d * 1.2 + UP * 1.4, end], [0.34, 0.22, 0.0], 4))
            self.tufts.append((end + UP * 0.3, 2.3))
        self.tufts.append((UP * 34.9, 2.2))
        for x, y, height, crown in SMALL:
            foot = Vector((x, y, 0.0))
            r = height * 0.03 + 0.26
            lean = Vector((rnd.uniform(-0.5, 0.5), rnd.uniform(-0.4, 0.4), 0.0))
            fork = foot + UP * height * 0.76
            self.lines.append(([foot - UP * 0.4, foot + lean + UP * height * 0.4, fork, fork + UP * height * 0.2],
                               [r, r * 0.8, r * 0.6, 0.0], 5))
            for k in range(5):
                a = (k + rnd.uniform(-0.25, 0.25)) * math.tau / 5
                d = Vector((math.cos(a), math.sin(a), 0.0))
                start = fork - UP * rnd.uniform(0.0, height * 0.14)
                knee = start + d * crown * 0.55 + UP * height * 0.03
                end = start + d * crown + UP * height * 0.17
                self.lines.append(([start, knee, end], [r * 0.5, r * 0.36, 0.0], 3))
                self.tufts.append((end, crown * 0.5))
                if self.state == "bare":
                    self.lines.append(([knee, knee + d * crown * 0.2 + UP * height * 0.16], [r * 0.26, 0.0], 3))
            self.tufts.append((fork + UP * (height * 0.2), crown * 0.6))

    def spray(self, rnd, origin, angle, length, rise, thick, start):
        """A limb and its flat spray: it leaves the trunk level and thick,
        and opens like a hand into three branches that turn up at their
        ends; two of them fork once more. A tuft of leaves sits on every
        end; bare, short twigs point up from them."""
        d = Vector((math.cos(angle), math.sin(angle), 0.0))
        side = Vector((-d.y, d.x, 0.0))
        split = 0.36
        palm = origin + d * (start + length * split) + UP * (rise * split * split - 0.05 * length)
        mid = origin.lerp(palm, 0.5) + d * start * 0.5 + side * rnd.uniform(-0.03, 0.03) * length - UP * 0.2
        self.limb([origin + d * start * 0.3, mid, palm], [thick, thick * 0.86, thick * 0.66], 4)
        turn = rnd.choice((1, -1))
        for k, spread in enumerate((-0.62, 0.0, 0.62)):
            w = (d + side * (spread + rnd.uniform(-0.12, 0.12))).normalized()
            reach = length * (1.0 - split) * (1.0 if k == 1 else rnd.uniform(0.78, 0.92))
            lift = rise * (1.0 - split * split) + 0.13 * length
            knee = palm + w * reach * 0.5 + UP * (lift * 0.2 + rnd.uniform(-0.3, 0.3))
            end = palm + w * reach + UP * lift
            self.lines.append(([palm, knee, end], [thick * 0.6, thick * 0.4, 0.0], 3))
            size = min(3.0, 0.23 * length + 0.5)
            self.tufts.append((end - w * size * 0.6, size))  # Within the reach of the branch.
            twigs = [palm.lerp(knee, 0.7), knee.lerp(end, 0.3), knee.lerp(end, 0.72)]
            if k != 1:
                # The outer branches fork to the outside.
                out = (w + side * (1 if spread > 0 else -1) * 0.9).normalized()
                tip = knee + out * reach * 0.42 + UP * lift * 0.75
                self.lines.append(([knee, knee.lerp(tip, 0.55) - UP * 0.2, tip], [thick * 0.36, thick * 0.24, 0.0], 3))
                size = min(2.8, 0.21 * length + 0.5)
                self.tufts.append((tip - out * size * 0.5, size))
                twigs.append(knee.lerp(tip, 0.5))
            else:
                self.tufts.append((palm.lerp(knee, 0.6) + UP * (lift * 0.5 + 0.6), min(3.0, 0.22 * length + 0.5)))
                twigs.append(palm.lerp(knee, 0.6))
            if self.state == "bare":
                for p in twigs:
                    out = (w * rnd.uniform(-0.2, 0.6) + side * turn * rnd.uniform(0.1, 0.6) + UP).normalized()
                    self.lines.append(([p, p + out * rnd.uniform(1.4, 2.4)], [thick * 0.2, 0.0], 3))
                    turn = -turn

    def foliage(self, mb, budget):
        """The tufts: rosettes of pointed leaves that open upward, dark
        underneath."""
        rnd = random.Random(self.o["seed"] + 61)
        count = len(self.tufts)
        points = max(5, min(8, budget // (4 * count)))
        # What is left over gives the largest tufts one more leaf each.
        more = (budget - 4 * points * count) // 4 if points < 8 else 0
        rich = set(sorted(range(count), key=lambda i: -self.tufts[i][1])[:more])
        used = 0
        for i, (center, size) in enumerate(self.tufts):
            n = points + (i in rich)
            if used + 4 * n > budget:
                break
            size *= rnd.uniform(0.95, 1.15)
            used += _giant.star(mb, rnd, center - UP * 0.5, size, 0.55, n, ("leaf_1", "leaf_2", "leaf_3"),
                                inner=0.34, rise=0.5 * size, tilt=0.15, under=-1.0)


SPECS = _giant.variants(
    Araucaria, "giant_araucaria", _giant.bark_tones(0xC18D66, 0x76513D), _giant.tones(0x8BA246, 0x53682F, 0x2D3C1C),
    seed=4608, voxel=0.14, budget=1150, ring=(3.6, 9.6), stones=18, tufts=16, flowers=10)
