"""Giant mangrove: a trunk standing on a cage of arching stilt roots, under
a wide green canopy with hanging vines; bare, the same roots and a
spreading crown of branches. About 25 m tall and 22 m wide.

The crown (branches and clumps) is traced from the pictures; the stilt
roots and the vines are made here."""

import math
import random

from mathutils import Vector

import _giant


class Mangrove(_giant.Giant):
    traced = "giant_mangrove"

    def stilt(self, angle, reach, height, steps=5, knee=(0.85, 0.58), lift=0.0):
        """A root's center line: it leaves the trunk going down and out,
        bends at its knee (given as shares of its reach and its height) and
        plunges into the ground at `reach` from the axis."""
        d = Vector((math.cos(angle), math.sin(angle), 0.0))
        a, b, c = (0.5, height), (reach * knee[0], height * knee[1]), (reach, -0.5)
        out = []
        for i in range(steps + 1):
            t = i / steps
            r = a[0] * (1 - t) ** 2 + 2 * b[0] * t * (1 - t) + c[0] * t * t
            z = a[1] * (1 - t) ** 2 + 2 * b[1] * t * (1 - t) + c[1] * t * t
            out.append(d * r + Vector((0.0, 0.0, z + lift * math.sin(math.pi * t))))
        return out

    def shape(self):
        rnd = random.Random(self.o["seed"] + 5)
        self.droppers = []
        count = 14
        for i in range(count):
            # The longest roots are those seen at both sides in the picture.
            a = i * math.tau / count + rnd.uniform(-0.12, 0.12) if i else 0.0
            wide = abs(math.cos(a)) ** 0.7
            reach = (5.8 + 4.9 * wide) * rnd.uniform(0.92, 1.05)
            height = rnd.uniform(8.6, 11.2)
            pts = self.stilt(a, reach, height, knee=(0.8 + 0.12 * wide, rnd.uniform(0.5, 0.62)),
                             lift=rnd.uniform(-0.3, 0.5))
            side = Vector((-math.sin(a), math.cos(a), 0.0))
            pts = [p + side * rnd.uniform(-0.5, 0.5) * (0 < k < len(pts) - 1) for k, p in enumerate(pts)]
            radii = [0.8, 0.7, 0.6, 0.52, 0.44, 0.36]
            for k in range(len(pts) - 1):
                self.capsules.append((tuple(pts[k]), tuple(pts[k + 1]), radii[k], radii[k + 1]))
            # Thinner roots drop from it to the ground, leaning out or aside.
            for k in (1, 2, 3) if reach > 8.5 else ((2, 3) if reach > 7.0 else (2,)):
                start = pts[k].lerp(pts[k + 1], rnd.uniform(0.1, 0.6))
                turn = a + rnd.uniform(-0.9, 0.9)
                lean = Vector((math.cos(turn), math.sin(turn), 0.0)) * rnd.uniform(0.6, 2.2)
                end = Vector((start.x, start.y, -0.5)) + lean
                knee = start.lerp(end, 0.45) + lean * 0.25 + Vector((0, 0, 0.5))
                self.droppers.append(([start, knee, end], [0.36, 0.27, 0.2]))
        # Short steep roots under the trunk, between the long ones.
        for i in range(7):
            a = (i + 0.5) * math.tau / 7 + rnd.uniform(-0.25, 0.25)
            pts = self.stilt(a, rnd.uniform(2.2, 4.4), rnd.uniform(6.0, 8.5), steps=3, knee=(0.7, 0.5))
            radii = [0.6, 0.5, 0.42, 0.34]
            for k in range(3):
                self.capsules.append((tuple(pts[k]), tuple(pts[k + 1]), radii[k], radii[k + 1]))

    def reserve(self):
        return sum(_giant.tube_cost(pts, 4) for pts, radii in self.droppers)

    def both(self, mb):
        rnd = random.Random(self.o["seed"] + 29)
        for pts, radii in self.droppers:
            _giant.tube(mb, pts, radii, 4, self.bark_tone(rnd))

    def foliage(self, mb, budget):
        vines = self.vines(mb)
        self.clumps(mb, budget - vines)

    def vines(self, mb):
        """Vines hanging under the canopy; returns the triangles used."""
        rnd = random.Random(self.o["seed"] + 43)
        used = 0
        low = sorted(self.blobs, key=lambda b: b[0].z - b[1].z)[:max(4, len(self.blobs) // 2)]
        for i in range(self.o["vines"]):
            c, r = low[i % len(low)]
            a, k = rnd.uniform(0.0, math.tau), rnd.uniform(0.2, 0.8)
            top = c + Vector((math.cos(a) * r.x * k, math.sin(a) * r.y * k, -r.z * 0.55))
            if math.hypot(top.x, top.y) < 3.5:
                continue  # Not through the trunk.
            length = rnd.uniform(2.5, 6.5)
            pts = [top]
            for step in range(1, 4):
                pts.append(top + Vector((rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3), -length * step / 3)))
            _giant.tube(mb, pts, [0.16, 0.14, 0.11], 3, "leaf_3" if rnd.random() < 0.6 else "leaf_2")
            used += _giant.tube_cost(pts, 3)
            # A leaf or two along it.
            for _ in range(2):
                p = pts[rnd.randrange(1, 3)] + Vector((0, 0, rnd.uniform(-0.6, 0.6)))
                turn = rnd.uniform(0.0, math.tau)
                u = Vector((math.cos(turn), math.sin(turn), 0.0)) * 0.3
                down = Vector((0.0, 0.0, -rnd.uniform(0.7, 1.1)))
                _giant.card(mb, [p, p + u + down * 0.4, p + down, p - u + down * 0.4], 0.08, "leaf_2")
                used += 4
        return used


SPECS = _giant.variants(
    Mangrove, "giant_mangrove", _giant.bark_tones(0xCB8F63, 0x724D3B), _giant.tones(0xA6C533, 0x506C29, 0x314216),
    seed=4304, foot=[(0.0, 8.6, 1.85), (0.1, 11.2, 1.6)], back_from=13.0, front_from=17.0, vines=22, clump=1.1,
    twig_scale=1.2, voxel=0.13, budget=1850, ring=(6.5, 10.2), stones=16, tufts=14, flowers=10)
