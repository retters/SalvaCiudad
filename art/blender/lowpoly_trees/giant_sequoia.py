"""Giant sequoia: a very tall, tapering, fluted red-brown trunk with small
conifer boughs high up and a pointed top, and four small conifers standing
around its foot (they are part of the model); bare, the boughs and the
small trees are tiers of bare branches. About 45 m tall.

All made by hand from the pictures: the trunk's width at every height, the
height and the reach of each bough seen at its sides, and where the small
trees stand."""

import math
import random

from mathutils import Vector

import _giant

# The trunk: (height, radius), without its ridges.
PROFILE = [(-0.5, 5.6), (3.0, 4.9), (6.0, 4.4), (10.0, 3.75), (15.0, 3.0), (25.0, 2.15), (35.0, 1.4), (41.0, 0.75),
           (44.5, 0.22)]
# The boughs: (height, direction seen from above in degrees, 0 = right and
# 270 = toward the viewer, how far its tips are from the trunk's surface).
# First those seen at both sides in the pictures, then those in between.
BOUGHS = [(21.0, 176, 7.0), (26.5, 190, 6.2), (31.0, 172, 5.2), (36.0, 186, 4.4), (39.6, 170, 3.0),
          (19.0, 8, 3.2), (24.5, -10, 6.8), (29.5, 12, 6.2), (33.5, -6, 5.2), (40.2, 6, 2.8),
          (22.5, 95, 6.0), (28.0, 70, 5.4), (34.0, 110, 4.4), (38.0, 60, 3.2), (27.4, 132, 5.0),
          (36.8, 236, 3.0), (32.6, 304, 3.0)]
# The small conifers: (x, y, height, tiers of branches, where the tiers start as a share of the height).
CONIFERS = [(-7.7, 2.6, 21.5, 6, 0.4), (7.8, 2.0, 21.5, 6, 0.4), (-10.6, -1.6, 9.0, 5, 0.2), (10.8, -2.2, 11.6, 5, 0.2)]


def radius(z):
    for (z0, r0), (z1, r1) in zip(PROFILE, PROFILE[1:]):
        if z <= z1:
            return r0 + (r1 - r0) * max(0.0, z - z0) / (z1 - z0)
    return PROFILE[-1][1]


class Sequoia(_giant.Giant):

    def shape(self):
        rnd = random.Random(self.o["seed"] + 5)
        self.tiers = []  # Of the small conifers: (center, radius).
        for (z0, r0), (z1, r1) in zip(PROFILE, PROFILE[1:]):
            self.capsules.append(((0, 0, z0), (0, 0, z1), r0, r1))
        # Ridges all the way up, each spreading into a root at the ground.
        count = 11
        for i in range(count):
            a = (i + rnd.uniform(-0.25, 0.25)) * math.tau / count
            top = rnd.uniform(30.0, 40.0)
            heights = [-0.5, 1.4, 4.0, 9.0, 16.0, 24.0, top]
            pts = []
            for k, z in enumerate(heights):
                drift = a + 0.012 * z * (1 if i % 2 else -1)  # The ridges twist a little.
                d = Vector((math.cos(drift), math.sin(drift), 0.0))
                r = radius(z)
                out = (1.42, 1.08, 0.88, 0.84, 0.82, 0.8, 0.7)[k] * rnd.uniform(0.96, 1.04)
                pts.append((d * r * out + Vector((0, 0, z)), r * (0.2, 0.32, 0.36, 0.36, 0.36, 0.35, 0.3)[k]))
            for (p, r), (q, t) in zip(pts, pts[1:]):
                self.capsules.append((tuple(p), tuple(q), r, t))
        up = Vector((0.0, 0.0, 1.0))
        for z, angle, reach in BOUGHS:
            a = math.radians(angle + rnd.uniform(-6.0, 6.0))
            d = Vector((math.cos(a), math.sin(a), 0.0))
            side = Vector((-d.y, d.x, 0.0))
            r = radius(z)
            # A thick stub out of the trunk, then a flat spray of twigs that turn up at their ends.
            base = d * r * 0.4 + up * (z - 0.5)
            stub = d * (r + 1.5) + up * (z + 0.2)
            self.capsules.append((tuple(base), tuple(stub), 0.8, 0.5))
            tip = stub + d * (reach - 1.5) + up * rnd.uniform(0.6, 1.4)
            main = [stub, stub.lerp(tip, 0.45) + up * rnd.uniform(-0.5, 0.1) + side * rnd.uniform(-0.4, 0.4),
                    stub.lerp(tip, 0.8) + side * rnd.uniform(-0.3, 0.3), tip]
            self.lines.append((main, [0.44, 0.32, 0.2, 0.0], 4))
            turn = rnd.choice((1, -1))
            for t in (0.12, 0.4, 0.66):
                q = stub.lerp(tip, t)
                w = (d * 0.62 + side * turn * 0.78).normalized()
                length = (reach - 1.5) * (0.62 - 0.3 * t) * rnd.uniform(0.85, 1.15) + 0.6
                knee = q + w * length * 0.6 + up * rnd.uniform(-0.2, 0.3)
                self.lines.append(([q, knee, q + w * length + up * rnd.uniform(0.8, 1.6)], [0.24, 0.17, 0.0], 3))
                fork = (d * 0.9 - side * turn * 0.3).normalized()
                self.lines.append(([knee, knee + fork * length * 0.45 + up * rnd.uniform(0.5, 1.1)], [0.15, 0.0], 3))
                turn = -turn
            self.blobs.append((d * (r + reach * 0.5) + up * (z + 0.9),
                               Vector((reach * 0.68, reach * 0.6, reach * 0.3 + 0.5))))
        # The top: twigs around the tip, under a cone of leaves.
        for k, (z, size) in enumerate(((38.6, 3.6), (41.4, 2.7), (43.6, 1.7))):
            self.blobs.append((Vector((0.0, 0.0, z)), Vector((size, size, size * 0.62))))
            for j in range(3):
                a = (j + k * 0.4) * math.tau / 3 + rnd.uniform(-0.3, 0.3)
                d = Vector((math.cos(a), math.sin(a), 0.0))
                q = up * (z + 0.4)
                self.lines.append(([q, q + d * size * 0.45 + up * 0.3, q + d * size * 0.8 + up * 1.1],
                                   [0.2, 0.13, 0.0], 3))
        for x, y, height, tiers, low in CONIFERS:
            self.conifer(rnd, Vector((x, y, 0.0)), height, tiers, low)

    def conifer(self, rnd, foot, height, tiers, low):
        """A small conifer: a thin trunk with tiers of branches."""
        up = Vector((0.0, 0.0, 1.0))
        r = height * 0.042 + 0.12
        lean = Vector((rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3), 0.0))
        trunk = [foot - up * 0.4, foot + lean + up * height * 0.45, foot + up * height * 0.8, foot + up * height]
        self.lines.append((trunk, [r, r * 0.72, r * 0.36, 0.0], 5))
        for k in range(tiers):
            t = low + (0.93 - low) * k / (tiers - 1)
            length = height * (0.27 * (1.0 - t) + 0.07)
            at = foot + lean * min(1.0, t / 0.45) * (1.0 if t < 0.45 else (1.0 - t) / 0.55) + up * height * t
            self.tiers.append((at, length))
            if self.state == "bloom":
                continue  # Its leaves hide them.
            for j in range(3):
                a = (j + k * 0.5) * math.tau / 3 + rnd.uniform(-0.25, 0.25)
                d = Vector((math.cos(a), math.sin(a), 0.0))
                self.lines.append(([at, at + d * length * 0.55 - up * length * 0.1,
                                    at + d * length + up * length * 0.2], [r * 0.34, r * 0.24, 0.0], 3))

    def foliage(self, mb, budget):
        rnd = random.Random(self.o["seed"] + 61)
        # The pointed top.
        _giant.spike(mb, Vector((0, 0, 43.8)), Vector((0.2, 0.0, 46.4)), 1.0, "leaf_2", sides=5)
        used = 8
        # The small conifers: every tier of branches is a jagged cone of leaves.
        for at, length in self.tiers:
            used += _giant.star(mb, rnd, at - Vector((0, 0, length * 0.22)), length * 1.05, length * 0.95 + 0.5, 7,
                                ("leaf_2", "leaf_3", "leaf_3"), inner=0.62, rise=-length * 0.12)
        self.clumps(mb, budget - used)


SPECS = _giant.variants(
    Sequoia, "giant_sequoia", _giant.bark_tones(0xE5874F, 0x8D5036), _giant.tones(0x7F994E, 0x425730, 0x25331D),
    seed=4502, voxel=0.2, budget=1350, small=1.2, ring=(8.6, 10.6), stones=18, tufts=16, flowers=10)
