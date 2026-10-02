"""Giant mushroom: a cluster of thick grey-brown trunks carrying purple-blue
mushroom caps, one huge and many small, pale and gilled underneath. About
22 m tall and 16 m wide.

Its two states are those of the pictures, and both keep the caps: "bloom"
has vivid caps with light spots; "bare" has duller caps without spots.

All made by hand from the pictures: the three trunks, and every cap seen
there (where it is, how wide and how tall) with the stem that carries it,
plus four caps toward the back."""

import math
import random

from mathutils import Vector

import _giant

# The trunks: points (x, y, z, radius) from the ground up.
TRUNKS = [
    [(0.0, 0.0, -0.4, 2.9), (0.0, 0.0, 2.0, 2.4), (0.1, 0.0, 5.0, 1.8), (0.2, 0.0, 10.0, 1.4), (0.0, 0.0, 15.0, 1.05),
     (-0.2, 0.0, 18.2, 0.95)],
    [(-4.1, -0.3, -0.4, 1.9), (-3.5, -0.3, 3.5, 1.45), (-3.8, -0.2, 6.3, 1.15), (-4.5, 0.0, 8.6, 0.8)],
    [(4.0, 0.2, -0.4, 1.9), (3.5, 0.2, 3.5, 1.45), (3.5, 0.1, 6.3, 1.15), (3.3, 0.0, 8.2, 0.8)],
]
# The caps: center of the rim (x, y, z), radius, height, sides, and the
# points of its stem from the trunk it grows on (None: it sits on the main
# trunk). First those of the pictures, then four toward the back.
CAPS = [
    ((-0.2, 0.0, 17.3), 7.6, 4.7, 18, None),
    ((-5.0, 3.2, 15.4), 3.4, 2.2, 11, [(-0.6, 0.5, 13.2), (-3.2, 2.2, 14.3)]),
    ((5.1, 1.0, 13.9), 2.5, 1.9, 10, [(0.8, 0.3, 10.8), (3.5, 0.8, 12.0)]),
    ((6.3, -0.5, 11.0), 1.9, 1.4, 9, [(3.3, 0.0, 8.0), (5.3, -0.3, 9.4)]),
    ((-3.0, 0.8, 12.25), 1.75, 1.25, 9, [(-0.8, 0.3, 10.4), (-2.4, 0.7, 11.1)]),
    ((-6.5, -0.4, 10.0), 2.45, 1.7, 10, [(-4.3, 0.0, 7.6), (-6.0, -0.3, 8.6)]),
    ((-2.4, -2.6, 9.9), 2.15, 1.25, 10, [(-3.6, -0.6, 7.0), (-2.8, -2.0, 8.4)]),
    ((3.4, -2.4, 9.05), 1.6, 0.9, 9, [(3.4, -0.5, 6.4), (3.4, -1.8, 7.8)]),
    ((4.9, -1.7, 8.2), 0.7, 0.45, 7, [(3.6, -0.6, 6.8), (4.6, -1.4, 7.4)]),
    ((2.5, 1.5, 13.2), 0.65, 0.42, 7, [(0.9, 0.6, 12.2), (2.1, 1.3, 12.5)]),
    ((-5.1, -1.2, 3.9), 1.05, 0.7, 8, [(-4.2, -0.9, 1.4), (-5.0, -1.2, 2.6)]),
    ((5.2, -1.0, 3.8), 0.55, 0.36, 7, [(4.3, -0.5, 1.6), (5.0, -0.9, 2.8)]),
    ((5.7, -1.6, 2.5), 0.4, 0.26, 6, [(4.6, -0.8, 1.2), (5.5, -1.5, 1.8)]),
    ((1.6, 4.6, 12.0), 2.3, 1.6, 10, [(0.4, 0.8, 9.2), (1.3, 3.4, 10.4)]),
    ((3.4, 3.6, 7.4), 1.6, 1.0, 9, [(3.6, 0.8, 5.0), (3.5, 2.8, 6.2)]),
    ((-3.6, 3.2, 7.0), 1.5, 1.0, 9, [(-3.8, 0.6, 4.6), (-3.7, 2.4, 5.8)]),
    ((-1.4, 3.6, 4.2), 1.0, 0.65, 8, [(-0.8, 1.6, 2.2), (-1.3, 3.2, 3.2)]),
]
UP = Vector((0.0, 0.0, 1.0))
COLORS = {
    "bloom": {"cap": 0x7566DC, "cap_light": 0xA08CF4, "cap_dark": 0x4C44A6, "gill": 0xD0C2EC},
    "bare": {"cap": 0x8C86C2, "cap_light": 0xB2A6DA, "cap_dark": 0x5E5A94, "gill": 0xC9BBDE},
}
# Rings of a cap from the top down: (share of the radius, share of the
# height). The last of the large one is the middle of the gills.
SMALL_RINGS = [(0.8, 0.62), (1.0, 0.16), (0.98, 0.0)]
LARGE_RINGS = [(0.46, 0.9), (0.82, 0.6), (1.0, 0.15), (0.98, 0.0), (0.5, 0.24)]
HUGE_RINGS = [(0.3, 0.96), (0.6, 0.83), (0.85, 0.57), (1.0, 0.13), (0.985, 0.0), (0.5, 0.22)]


class Mushroom(_giant.Giant):
    light_bark = False

    def more_colors(self):
        return COLORS[self.state]

    def shape(self):
        seed = self.o["seed"]
        for trunk in TRUNKS:
            for a, b in zip(trunk, trunk[1:]):
                self.capsules.append((a[:3], b[:3], a[3], b[3]))
        self.roots(7, [(1.6, 3.0, 1.2), (2.8, 1.2, 0.95), (4.0, -0.3, 0.5)], seed + 6, phase=0.4)
        self.roots(3, [(0.8, 2.0, 0.8), (1.9, -0.3, 0.42)], seed + 8, center=(-4.0, -0.3), phase=2.6, sway=0.1)
        self.roots(3, [(0.8, 2.0, 0.8), (1.9, -0.3, 0.42)], seed + 9, center=(3.9, 0.2), phase=-0.9, sway=0.1)
        self.knobs(30, 1.5, 16.5, (0.55, 0.95), seed + 7, axis=lambda z: Vector((0.1, 0.0, z)), out=0.4)
        self.knobs(9, 1.5, 7.5, (0.45, 0.7), seed + 10, axis=lambda z: Vector((-3.7, -0.3, z)), out=0.4)
        self.knobs(9, 1.5, 7.5, (0.45, 0.7), seed + 11, axis=lambda z: Vector((3.6, 0.2, z)), out=0.4)
        for center, radius, height, sides, stem in CAPS:
            if stem is None:
                continue
            # The stem bows up into the middle of its cap.
            top = Vector(center) + UP * height * 0.3
            pts = [Vector(stem[0]), Vector(stem[1]), top.lerp(Vector(stem[1]), 0.35) + UP * 0.15 * radius, top]
            thick = min(0.8, 0.22 + 0.2 * radius)
            self.limb(pts, [thick, thick * 0.85, thick * 0.72, thick * 0.62], 5)

    def both(self, mb):
        rnd = random.Random(self.o["seed"] + 29)
        for center, radius, height, sides, stem in CAPS:
            self.cap(mb, rnd, Vector(center), radius, height, sides, stem)

    def cap(self, mb, rnd, center, radius, height, sides, stem):
        """A mushroom cap: a faceted dome with a dark rim, hollow and gilled
        underneath; closed. It leans a little away from its trunk."""
        tilt = Vector((0.0, 0.0, 0.0))
        if stem is not None:
            tilt = Vector((center.x, center.y, 0.0)).normalized() * rnd.uniform(0.03, 0.12)
        small = radius < 1.3
        rings = SMALL_RINGS if small else (HUGE_RINGS if radius > 5.0 else LARGE_RINGS)
        phase = rnd.uniform(0.0, math.tau)

        def at(r, z, k, jitter=0.04):
            a = phase + k * math.tau / sides
            r *= radius * rnd.uniform(1.0 - jitter, 1.0 + jitter)
            p = Vector((math.cos(a) * r, math.sin(a) * r, z * height))
            p.z -= tilt.x * p.x + tilt.y * p.y
            return center + p

        bm = mb.bm
        loops = [[bm.verts.new(at(r, z, k + 0.5 * (i % 2))) for k in range(sides)] for i, (r, z) in enumerate(rings)]
        top = bm.verts.new(center + UP * height
                           + Vector((rnd.uniform(-0.05, 0.05), rnd.uniform(-0.05, 0.05), 0.0)) * radius)
        under = bm.verts.new(center + UP * height * 0.36)
        rim = len(rings) - (2 if small else 3)  # The loop of the rim's upper edge.

        def face(verts, mat):
            f = bm.faces.new(verts)
            f.material_index = mb._material_index(mat)
            f.smooth = False

        def skin(k, a, b, shifted):
            """The two triangles between loop a and the loop b under it, at
            side k; `shifted`: b is the one turned half a side."""
            j = (k + 1) % sides
            if shifted:
                return [(a[k], b[k], a[j]), (a[j], b[k], b[j])]
            return [(a[k], b[k], b[j]), (a[k], b[j], a[j])]

        def upper(verts):
            n = (verts[1].co - verts[0].co).cross(verts[2].co - verts[0].co).normalized()
            v = abs(n.dot(_giant.LIGHT)) + rnd.uniform(-0.3, 0.3)
            return "cap_light" if v > 0.85 else ("cap_dark" if v < 0.2 else "cap")

        for k in range(sides):
            tri = (loops[0][k], loops[0][(k + 1) % sides], top)
            face(tri, upper(tri))
        for i in range(rim):
            for k in range(sides):
                for tri in skin(k, loops[i], loops[i + 1], i % 2 == 0):
                    face(tri, upper(tri))
        for k in range(sides):  # The rim's band.
            for tri in skin(k, loops[rim], loops[rim + 1], rim % 2 == 0):
                face(tri, "cap_dark")
        low = loops[rim + 1]
        if not small:
            for k in range(sides):  # The gills: pale wedges, every third one in the shade.
                for tri in skin(k, loops[rim + 1], loops[rim + 2], (rim + 1) % 2 == 0):
                    face(tri, "cap_light" if k % 3 == 2 else "gill")
            low = loops[rim + 2]
        for k in range(sides):
            face((low[(k + 1) % sides], low[k], under), "cap_light" if (k % 3 == 2 and not small) else "gill")
        if self.state != "bloom" or radius < 1.5:
            return
        # Light spots lying on the dome, in a loose ring around its top.
        for k in range(int(radius * 4.0) + 2):
            a = rnd.uniform(0.0, math.tau)
            i = rnd.randrange(rim)
            (r0, z0), (r1, z1) = rings[i], rings[i + 1]
            f = rnd.uniform(0.1, 0.85)
            r, z = (r0 + (r1 - r0) * f) * radius, (z0 + (z1 - z0) * f) * height
            p = Vector((math.cos(a) * r, math.sin(a) * r, z))
            p.z -= tilt.x * p.x + tilt.y * p.y
            normal = Vector((math.cos(a) * height * (z0 - z1), math.sin(a) * height * (z0 - z1),
                             radius * (r1 - r0))).normalized()
            u = normal.cross(UP).normalized()
            v = normal.cross(u)
            size = rnd.uniform(0.1, 0.17) * radius ** 0.5
            c = center + p + normal * (0.05 * radius ** 0.5 + 0.05)
            _giant.card(mb, [c + u * size * 1.3, c + v * size, c - u * size * 1.3, c - v * size], 0.05, "gill")


SPECS = _giant.variants(
    Mushroom, "giant_mushroom", _giant.bark_tones(0xB88E76, 0x6E5048), seed=4806, voxel=0.14, budget=1700,
    ring=(5.4, 7.4), stones=16, tufts=16, flowers=12, stone_size=(0.6, 1.3), lush=(30, 34))
