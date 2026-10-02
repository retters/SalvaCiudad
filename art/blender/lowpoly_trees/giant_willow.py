"""Giant weeping willow: a thick trunk on roots, limbs that arch out and
long curtains of yellow-green leaves hanging from them almost to the
ground; bare, the hanging strands alone. About 25 m tall and 22 m wide.

All made by hand from the pictures: the limbs seen in the bare picture
(X and Z as there, their depth given here), four more toward the back and
the front, and the strands that hang from all of them."""

import math
import random

from mathutils import Vector

import _giant

PROFILE = [(-0.4, 2.7), (2.0, 2.3), (5.0, 1.85), (9.0, 1.65), (12.6, 1.5)]
# The limbs: radius at the start, then points (x, y, z). The first six are
# those of the picture.
LIMBS = [
    (1.0, [(0.0, 0.0, 12.0), (-2.6, 1.0, 16.4), (-4.4, 2.0, 20.1), (-7.8, 3.0, 21.9), (-9.6, 3.4, 18.8)]),
    (0.8, [(-0.6, -0.3, 11.6), (-3.0, -1.6, 15.2), (-5.7, -3.0, 16.9), (-8.5, -4.0, 15.2)]),
    (0.95, [(0.4, 0.2, 13.0), (-0.5, 1.0, 19.5), (-1.4, 2.0, 24.2), (-3.6, 3.2, 23.2)]),
    (0.95, [(0.8, -0.2, 13.0), (2.9, -1.0, 19.5), (4.4, -2.4, 23.8), (6.4, -3.6, 21.8)]),
    (1.0, [(0.8, 0.2, 11.8), (5.4, 1.2, 18.6), (8.1, 2.5, 20.8), (10.3, 3.4, 16.8)]),
    (0.8, [(1.0, -0.4, 10.2), (6.0, -1.5, 12.4), (9.4, -3.0, 13.4), (10.7, -3.8, 11.4)]),
    (0.85, [(0.0, 0.6, 12.0), (-1.0, 4.0, 17.2), (-1.5, 7.4, 20.2), (-1.0, 10.0, 17.6)]),
    (0.75, [(0.6, 0.6, 13.0), (2.6, 4.2, 17.6), (4.6, 7.6, 19.4), (6.0, 9.4, 16.6)]),
    (0.85, [(0.2, -0.6, 12.2), (0.6, -4.0, 16.6), (1.0, -7.4, 19.6), (1.6, -9.8, 16.6)]),
    (0.75, [(-0.4, -0.6, 12.6), (-2.4, -4.0, 17.2), (-4.4, -7.0, 18.6), (-5.6, -8.8, 15.6)]),
    (0.6, [(0.3, 0.3, 14.0), (1.6, 2.6, 20.0), (3.6, 4.6, 22.6), (5.6, 6.2, 20.2)]),
    (0.6, [(-0.3, -0.3, 14.0), (-1.8, -2.6, 20.2), (-3.6, -4.6, 22.9), (-5.2, -6.2, 20.6)]),
    (0.6, [(0.5, -0.3, 14.0), (2.6, -3.0, 19.6), (5.0, -5.0, 22.0), (7.0, -6.4, 19.6)]),
    (0.6, [(-0.5, 0.3, 14.0), (-3.0, 3.4, 19.2), (-5.6, 5.4, 21.6), (-7.6, 7.0, 19.2)]),
]
UP = Vector((0.0, 0.0, 1.0))


def smooth(points, cuts=2):
    """The polyline bowed through its points (a Catmull-Rom spline)."""
    pts = [points[0]] + list(points) + [points[-1]]
    out = [points[0]]
    for i in range(1, len(pts) - 2):
        a, b, c, d = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
        for k in range(1, cuts + 1):
            t = k / cuts
            out.append(0.5 * ((2 * b) + (c - a) * t + (2 * a - 5 * b + 4 * c - d) * t * t
                              + (3 * b - a - 3 * c + d) * t ** 3))
    return out


class Willow(_giant.Giant):

    def shape(self):
        seed = self.o["seed"]
        rnd = random.Random(seed + 5)
        lean = 0.03
        for (z0, r0), (z1, r1) in zip(PROFILE, PROFILE[1:]):
            self.capsules.append(((z0 * lean, 0, z0), (z1 * lean, 0, z1), r0, r1))
        self.roots(8, [(1.3, 3.6, 1.25), (2.7, 1.5, 1.05), (4.4, -0.3, 0.5)], seed + 6, wobble=0.18)
        self.knobs(26, 1.5, 12.0, (0.6, 1.0), seed + 7, axis=lambda z: Vector((z * lean, 0.0, z)), out=0.4)
        self.strands = []  # Each: its points, from where it hangs down to its end.
        self.roof = []     # Where leaves lie over a limb: (point, direction of the limb).
        for thick, points in LIMBS:
            fine = smooth([Vector(p) for p in points])
            n = len(fine)
            self.limb(fine, [thick * (1.0 - 0.78 * i / (n - 1)) for i in range(n)], 4)
            cum = [0.0]
            for a, b in zip(fine, fine[1:]):
                cum.append(cum[-1] + (b - a).length)

            def at(s):
                i = max(j for j in range(n - 1) if cum[j] <= s)
                return fine[i].lerp(fine[i + 1], (s - cum[i]) / (cum[i + 1] - cum[i])), (fine[i + 1] - fine[i])

            # Strands hang along its outer part and from its end.
            count = max(4, int(round(cum[-1] * 0.6 / 1.9)))
            for k in range(count):
                p, _ = at(cum[-1] * (0.42 + 0.58 * (k + rnd.uniform(0.2, 0.8)) / count))
                self.strand(rnd, p, k / count)
            self.strand(rnd, fine[-1], 1.0)
            # Side branches that droop, with their own strands.
            turn = rnd.choice((1, -1))
            for share in (0.5, 0.74):
                p, along = at(cum[-1] * share)
                along.z = 0.0
                along.normalize()
                side = Vector((-along.y, along.x, 0.0)) * turn
                w = (along * 0.55 + side).normalized()
                length = rnd.uniform(2.6, 4.2)
                knee = p + w * length * 0.55 + UP * rnd.uniform(0.1, 0.6)
                end = p + w * length - UP * rnd.uniform(0.4, 1.2)
                self.lines.append(([p, knee, end], [thick * 0.3, thick * 0.2, 0.0], 3))
                self.strand(rnd, knee, share)
                self.strand(rnd, end, 1.0)
                self.roof.append((knee, w))
                turn = -turn
            s = cum[-1] * 0.22
            while s < cum[-1]:
                self.roof.append(at(s))
                s += 1.3

    def strand(self, rnd, top, share):
        """A hanging strand from `top` down, with a kink; those from the
        ends of the limbs (share 1) hang lowest, and those near the trunk
        are short, so that the trunk shows under the curtains."""
        low = rnd.uniform(2.6, 7.0) if share > 0.6 else rnd.uniform(5.0, 9.5)
        near = max(0.0, min(1.0, (7.5 - math.hypot(top.x, top.y)) / 3.5))
        low = min(low + near * rnd.uniform(4.0, 6.0), top.z - 4.0)
        out = Vector((top.x, top.y, 0.0))
        out = out.normalized() if out.length > 0.5 else Vector((1.0, 0.0, 0.0))
        t = rnd.uniform(0.35, 0.6)
        kink = out * 0.3 + Vector((rnd.uniform(-0.5, 0.5), rnd.uniform(-0.5, 0.5), 0.0))
        self.strands.append([top, Vector((top.x, top.y, top.z + (low - top.z) * t)) + kink,
                             Vector((top.x, top.y, low)) + out * 0.5])

    def both(self, mb):
        # With leaves, the strands are under them and are not built (as the
        # twigs that a clump of leaves swallows in the other trees).
        if self.state == "bloom":
            return
        rnd = random.Random(self.o["seed"] + 29)
        for pts in self.strands:
            _giant.tube(mb, pts, [0.28, 0.19], 3, self.bark_tone(rnd))

    def leaf(self, mb, rnd, p, down, normal, length):
        """A long pointed leaf hanging from p."""
        side = normal.cross(down).normalized()
        width = length * rnd.uniform(0.18, 0.23)
        corners = [p - down * 0.3, p + down * length * 0.36 + side * width, p + down * length,
                   p + down * length * 0.36 - side * width]
        _giant.card(mb, corners, 0.12, self.tone(rnd, normal * 0.8 + _giant.LIGHT * 0.3))

    def foliage(self, mb, budget):
        """Long pointed leaves, one over the next, down every strand and
        from the limbs themselves: the curtains."""
        rnd = random.Random(self.o["seed"] + 41)
        count = budget // 4
        # A limb's own leaves hang from it as from a short strand.
        falls = [(pts[0], pts[-1].z, pts) for pts in self.strands]
        falls += [(p + UP * 0.4, p.z - rnd.uniform(3.5, 6.0), None) for p, along in self.roof]
        total = sum(top.z - low for top, low, pts in falls)
        step = total / max(1, count)
        for top, low, pts in falls:
            out = Vector((top.x, top.y, 0.0))
            out = out.normalized() if out.length > 0.5 else Vector((1.0, 0.0, 0.0))
            # The leaves of one strand face the same way, more or less: a strip of the curtain.
            face = out + _giant.random_unit(rnd) * 0.45
            z = top.z + rnd.uniform(0.3, step)
            while z > low + 1.0 and count > 0:
                p = Vector((top.x, top.y, z))
                if pts:
                    i = 0 if z > pts[1].z else 1
                    p = pts[i].lerp(pts[i + 1], (pts[i].z - z) / max(0.01, pts[i].z - pts[i + 1].z))
                normal = face + _giant.random_unit(rnd) * 0.25
                normal.z = rnd.uniform(0.0, 0.2)
                normal.normalize()
                side = normal.cross(UP).normalized()
                p = p + side * rnd.uniform(-0.2, 0.2) + normal * rnd.uniform(0.05, 0.3)
                down = (-UP + normal * rnd.uniform(0.0, 0.14) + side * rnd.uniform(-0.08, 0.08)).normalized()
                normal = (normal - down * normal.dot(down)).normalized()
                self.leaf(mb, rnd, p, down, normal, min(rnd.uniform(3.2, 4.2), z - low + 1.8))
                count -= 1
                z -= step


SPECS = _giant.variants(
    Willow, "giant_willow", _giant.bark_tones(0xC99267, 0x8B6249), _giant.tones(0xBCCB34, 0x8FA636, 0x5E7528),
    seed=4705, voxel=0.15, budget=1150, ring=(4.6, 6.6), stones=16, tufts=14, flowers=12)
