"""Giant ginkgo: a thick golden-brown trunk on big roots, with many separate
clumps of yellow-orange leaves on short branches all the way up, and small
ginkgos at its foot; bare, the branches without leaves. About 30 m tall and
23 m wide.

The branches and the clumps are traced from the pictures; the foot, the
roots and the small trees are made here."""

import math
import random

from mathutils import Vector

import _giant

# The small trees at the foot: where each stands (x, y), its height, how far
# it leans along X, and the radius of its trunk.
SAPLINGS = [(5.4, -1.2, 7.6, 1.9, 0.45), (6.9, 1.6, 4.4, 0.9, 0.32), (-5.2, -1.6, 7.8, -1.0, 0.42),
            (-6.3, 1.2, 5.4, -0.8, 0.32), (-1.5, 6.0, 6.6, -0.8, 0.4)]


class Ginkgo(_giant.Giant):
    traced = "giant_ginkgo"

    def shape(self):
        seed = self.o["seed"]
        rnd = random.Random(seed + 9)
        self.roots(7, [(1.8, 5.0, 1.5), (3.4, 2.4, 1.3), (4.9, 0.9, 0.95), (6.4, -0.3, 0.5)], seed + 5, wobble=0.15)
        self.knobs(34, 1.5, 17.0, (0.7, 1.15), seed + 7, out=0.36)
        for x, y, height, lean, radius in SAPLINGS:
            foot = Vector((x, y, -0.3))
            top = Vector((x + lean, y + rnd.uniform(-0.6, 0.6), height))
            bend = Vector((rnd.uniform(-0.8, 0.8), rnd.uniform(-0.8, 0.8), 0.0))
            pts = [foot, foot.lerp(top, 0.3) + bend, foot.lerp(top, 0.62) - bend * 0.7, top]
            self.lines.append((pts, [radius, radius * 0.8, radius * 0.6, 0.0], 4))
            # A fork of twigs at its top, under its clump of leaves.
            for k in range(4):
                a = (k + rnd.uniform(-0.3, 0.3)) * math.tau / 4
                d = Vector((math.cos(a), math.sin(a), rnd.uniform(0.5, 1.1))).normalized()
                start = pts[2].lerp(pts[3], rnd.uniform(-0.2, 0.6))
                mid = start + d * height * 0.16
                end = mid + (d + Vector((0, 0, 0.8))).normalized() * height * 0.12
                self.lines.append(([start, mid, end], [radius * 0.5, radius * 0.34, 0.0], 3))
            r = height * rnd.uniform(0.17, 0.2)
            self.blobs.append((top + Vector((0, 0, r * 0.25)), Vector((r * 1.25, r * 1.15, r * 0.72))))


SPECS = _giant.variants(
    Ginkgo, "giant_ginkgo", _giant.bark_tones(0xEBAA6D, 0xA3714D), _giant.tones(0xFBD428, 0xEE9C11, 0xCD7409),
    seed=4407, foot=[(0.0, -0.4, 2.7), (0.0, 1.2, 2.6)], trunk_max=2.45, back_from=8.0, fill=False, solid=1.4,
    clump=1.12, leaf=1.5,
    twig_scale=1.2, voxel=0.18, budget=1600, ring=(6.2, 8.2), stones=16, tufts=16, flowers=10)
