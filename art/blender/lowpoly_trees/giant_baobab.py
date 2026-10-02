"""Giant baobab: an enormous bottle trunk on buttress roots, with thick
short branches that end in flat dark-green crowns; bare, the branches fork
into many twigs. About 26 m tall and as wide.

The branches and the crowns are traced from the pictures; the foot, the
roots and the ridges that run up the trunk from each root are made here."""

import math
import random

from mathutils import Vector

import _giant


class Baobab(_giant.Giant):
    traced = "giant_baobab"

    def shape(self):
        rnd = random.Random(self.o["seed"] + 5)
        count = 9
        for i in range(count):
            a = (i + 0.35 + rnd.uniform(-0.2, 0.2)) * math.tau / count
            d = Vector((math.cos(a), math.sin(a), 0.0))
            side = Vector((-d.y, d.x, 0.0))
            axis = Vector((0.6, 0.0, 0.0))
            # A root: steep down the trunk's side, then out along the ground.
            path = [axis + d * 3.4 + Vector((0, 0, 8.0)),
                    axis + d * 4.2 + side * rnd.uniform(-0.3, 0.3) + Vector((0, 0, 4.6)),
                    axis + d * 5.0 + side * rnd.uniform(-0.4, 0.4) + Vector((0, 0, 2.6)),
                    axis + d * 6.4 + side * rnd.uniform(-0.6, 0.6) + Vector((0, 0, 1.0)),
                    axis + d * rnd.uniform(8.0, 9.0) + side * rnd.uniform(-1.0, 1.0) + Vector((0, 0, -0.35))]
            radii = [1.5, 1.5, 1.4, 1.1, 0.7]
            for k in range(4):
                self.capsules.append((tuple(path[k]), tuple(path[k + 1]), radii[k], radii[k + 1]))
            # The ridge it makes up the trunk.
            high = axis + d * 3.0 + side * rnd.uniform(-0.6, 0.6) + Vector((0, 0, rnd.uniform(12.0, 14.5)))
            self.capsules.append((tuple(path[0]), tuple(high), 1.5, 1.25))
        self.knobs(46, 2.5, 17.5, (0.8, 1.35), self.o["seed"] + 7, out=0.36)


SPECS = _giant.variants(
    Baobab, "giant_baobab", _giant.bark_tones(0xDD9B64, 0x8D6143), _giant.tones(0x99B944, 0x536D3C, 0x354625),
    seed=4101, foot=[(0.6, -0.4, 4.6), (0.6, 3.0, 4.6)], skip=[(-3.7, 6.2, 1.6)],
    back_from=9.0, fill=False, solid=1.4, clump=1.25, clump_tall=0.85, under=-0.25, twig_scale=1.25, weld=0.45,
    voxel=0.2, budget=1750, ring=(7.4, 9.4), stones=18, tufts=18, flowers=12)
