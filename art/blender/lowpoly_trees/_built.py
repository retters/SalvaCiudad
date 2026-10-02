"""Trees built from numbers, not traced: the pine, the cypress and the palm.

Their shapes are regular (tiers of boughs, a column, a crown of fronds), so
a few measures taken from the reference pictures describe them better than
a tracing would. As the traced trees of _tree.py, each is defined once and
built in three states, "bloom", "autumn" and "bare", with the same trunk
and branches; what its foliage buries (the boughs under a pine's tiers, the
branches inside a cypress) is not built with leaves.

The game culls back faces: every piece here is a closed solid.
"""

import math
import random

from mathutils import Vector

import common
import studies
import _tree
from _tree import LIGHT, LIMITS, STATES, card, tube

UP = Vector((0.0, 0.0, 1.0))
DEFAULTS = {
    "seed": 1,
    "bark": (0x8C5E33, 0x62401F),
    "tufts": 5,
    "stones": 5,
    "budget": 150,      # Triangles of the welded trunk.
    "voxel": 0.04,
}


def profile(table, t):
    """Linear interpolation in a table of (t, value) pairs."""
    for (t0, v0), (t1, v1) in zip(table, table[1:]):
        if t <= t1:
            return v0 + (v1 - v0) * (t - t0) / ((t1 - t0) or 1.0)
    return table[-1][1]


class Built(studies.Spec):
    """What the three have in common: colors, the welded trunk, the ground."""

    tone_material = None
    tones = 0.0
    defaults = {}

    def __init__(self, tree, state, leaves, **options):
        self.name = f"{tree}_{state}"
        self.state = state
        self.o = dict(DEFAULTS, **dict(self.defaults, **options))
        self.max_tris = LIMITS[state]
        self.budget = self.o["budget"]
        self.remesh_voxel = self.o["voxel"]
        self.palette = leaves.get(state, ())
        self.colors = {"bark": common.rgb(self.o["bark"][0]), "bark_shade": common.rgb(self.o["bark"][1]),
                       "grass": common.rgb(_tree.GROUND["grass"]), "stone": common.rgb(_tree.GROUND["stone"])}
        for i, c in enumerate(self.palette):
            self.colors[f"leaf_{i + 1}"] = common.rgb(c)
        self.ellipsoids = []
        self.capsules = self.trunk()

    def trunk(self):
        return []

    def stem(self, height, low, high, foot=1.5):
        """A straight welded trunk up to where it is too thin for the
        remesh, with root stubs; self.stem_top is where it ends."""
        rnd = random.Random(self.o["seed"] + 11)
        thin = 0.07
        top = height * min(1.0, (low - thin) / ((low - high) or 1.0))
        steps = 4
        pts = [(0.0, 0.0, top * i / steps) for i in range(steps + 1)]
        radii = [low + (high - low) * (p[2] / height) for p in pts]
        radii[0] *= foot ** 0.5
        caps = [(a, b, ra, rb) for a, b, ra, rb in zip(pts, pts[1:], radii, radii[1:])]
        for i in range(5):
            a = (i + rnd.uniform(-0.25, 0.25)) * math.tau / 5
            d = (math.cos(a), math.sin(a))
            reach = low * rnd.uniform(1.3, 1.8)
            caps.append(((d[0] * low * 0.3, d[1] * low * 0.3, 0.45), (d[0] * reach, d[1] * reach, -0.03),
                         low * 0.55, low * 0.3))
        self.stem_top = (top, radii[-1])
        return caps

    def paint(self, c, n):
        h = math.sin(c.x * 12.9898 + c.y * 78.233 + c.z * 37.719) * 43758.5453
        h -= math.floor(h)
        return "bark_shade" if n.dot(LIGHT) + (h - 0.5) * 0.9 < -0.12 else "bark"

    def tone(self, rnd, normal, main=None, shift=0.0):
        """Material of a piece of foliage: by the light in bloom; in autumn
        mostly its part's own color, `main`."""
        if self.state == "autumn" and main is not None:
            return f"leaf_{(main if rnd.random() < 0.65 else rnd.randrange(3)) + 1}"
        v = normal.dot(LIGHT) + shift + rnd.uniform(-0.4, 0.4)
        return f"leaf_{(0 if v > 0.55 else (1 if v > 0.0 else 2)) + 1}"

    def bark(self, rnd):
        return "bark" if rnd.random() < 0.7 else "bark_shade"

    def face(self, mb, verts, mat):
        f = mb.bm.faces.new(verts)
        f.material_index = mb._material_index(mat)
        f.smooth = False
        return f

    def details(self, mb):
        self.build(mb, self.state != "bare")
        _tree.ground(mb, random.Random(self.o["seed"] + 53), self.o["foot"] * 1.5, self.o["tufts"],
                     self.o["stones"])


# -------------------------------------------------------------------- pine

class Pine(Built):
    """Tiers of drooping pointed boughs around a straight trunk. Each tier
    is one closed star-shaped skirt; without leaves, its boughs."""

    defaults = {
        "height": 7.0,
        "foot": 0.25,       # Trunk radius at the ground.
        # The tiers, from the lowest: (height of the tips, radius, boughs).
        "tiers": [(1.1, 2.55, 10), (2.05, 2.25, 10), (2.9, 1.95, 9), (3.7, 1.65, 8), (4.45, 1.35, 7), (5.15, 1.05, 7),
                  (5.8, 0.75, 6), (6.35, 0.45, 5)],
    }

    def trunk(self):
        return self.stem(self.o["height"], self.o["foot"], 0.03)

    def rise(self, radius):
        """How far above its tips a tier meets the trunk."""
        return 0.36 + 0.5 * radius

    def build(self, mb, leaves):
        o = self.o
        rnd = random.Random(o["seed"] + 23)
        top, r = self.stem_top
        tube(mb, [(0, 0, top - 0.1), (0, 0, o["height"])], [r], 4, "bark")
        for index, (z, radius, count) in enumerate(o["tiers"]):
            phase = rnd.uniform(0.0, math.tau)
            angles = [phase + (j + rnd.uniform(-0.18, 0.18)) * math.tau / count for j in range(count)]
            reach = [radius * rnd.uniform(0.86, 1.06) for _ in range(count)]
            drop = [rnd.uniform(-0.1, 0.1) * radius for _ in range(count)]
            if leaves:
                self.tier(mb, rnd, z, radius, angles, reach, drop, index)
            else:
                self.boughs(mb, rnd, z, radius, angles, reach, drop)

    def tier(self, mb, rnd, z, radius, angles, reach, drop, index):
        bm = mb.bm
        count = len(angles)
        rise = self.rise(radius)
        last = index == len(self.o["tiers"]) - 1
        apex = bm.verts.new((0, 0, z + rise * (1.9 if last else 1.0)))
        under = bm.verts.new((0, 0, z + rise * 0.3))
        tips, notches, mids = [], [], []
        for j in range(count):
            a = angles[j]
            b = a + ((angles[(j + 1) % count] - a) % math.tau) * 0.5
            d, e = Vector((math.cos(a), math.sin(a), 0)), Vector((math.cos(b), math.sin(b), 0))
            tips.append(bm.verts.new(d * reach[j] + UP * (z + drop[j])))
            notches.append(bm.verts.new(e * (radius * rnd.uniform(0.6, 0.72))
                                        + UP * (z + rise * rnd.uniform(0.22, 0.32))))
            mids.append(bm.verts.new(d * (radius * 0.5) + UP * (z + rise * rnd.uniform(0.6, 0.7))))
        main = rnd.randrange(3)

        def top(*verts):
            n = (verts[1].co - verts[0].co).cross(verts[2].co - verts[0].co).normalized()
            if n.z < 0:
                n = -n
            self.face(mb, verts, self.tone(rnd, n, main, -0.2))

        for j in range(count):
            k = (j + 1) % count
            top(apex, mids[j], mids[k])
            top(mids[j], notches[j - 1], tips[j])
            top(mids[j], tips[j], notches[j])
            top(mids[j], notches[j], mids[k])
            dark = "leaf_3" if self.state != "autumn" else f"leaf_{main + 1}"
            self.face(mb, (under, tips[j], notches[j - 1]), dark)
            self.face(mb, (under, notches[j], tips[j]), dark)

    def boughs(self, mb, rnd, z, radius, angles, reach, drop):
        rise = self.rise(radius)
        thick = 0.045 + 0.03 * radius
        for a, far, low in zip(angles, reach, drop):
            d = Vector((math.cos(a), math.sin(a), 0))
            side = Vector((-d.y, d.x, 0))
            pts = [UP * (z + rise * 0.8), d * (far * 0.5) + UP * (z + rise * 0.42 + 0.05 * radius),
                   d * far + UP * (z + low)]
            tube(mb, pts, [thick, thick * 0.75], 3, self.bark(rnd))
            for t, s in ((rnd.uniform(0.4, 0.55), 1), (rnd.uniform(0.6, 0.78), -1)):
                p = pts[1].lerp(pts[2], (t - 0.5) * 2.0) if t > 0.5 else pts[0].lerp(pts[1], t * 2.0)
                q = p + (d * 0.6 + side * (s * 0.55) - UP * 0.3).normalized() * (far * rnd.uniform(0.2, 0.3))
                tube(mb, [p, q], [thick * 0.7], 3, self.bark(rnd))


# ----------------------------------------------------------------- cypress

class Cypress(Built):
    """A column of foliage: a dark closed core covered with sprays, pointed
    blades that go up overlapping each other like scales (each a closed
    piece with a lit and a shaded half). Without leaves, branches that go
    up hugging the trunk."""

    defaults = {
        "height": 6.65,
        "foot": 0.27,
        "from": 0.55,           # Where the foliage starts.
        # Radius of the column along its height (0 the bottom, 1 the top).
        "shape": [(0.0, 0.42), (0.1, 0.84), (0.28, 1.12), (0.5, 1.1), (0.7, 0.9), (0.85, 0.6), (0.95, 0.3), (1.0, 0.0)],
        "rings": 9,             # Rows of sprays, and sprays around in each.
        "around": 8,
        "spray": 1.45,          # Length of a spray.
        "branches": 30,
    }

    def trunk(self):
        return self.stem(self.o["height"] - 0.3, self.o["foot"], 0.03, foot=1.3)

    def radius(self, z):
        o = self.o
        return profile(o["shape"], (z - o["from"]) / (o["height"] - o["from"]))

    def build(self, mb, leaves):
        o = self.o
        rnd = random.Random(o["seed"] + 23)
        top, r = self.stem_top
        tube(mb, [(0, 0, top - 0.1), (0, 0, o["height"] - 0.05)], [r], 4, "bark")
        if leaves:
            self.column(mb, rnd)
        else:
            self.branches(mb, rnd)

    def column(self, mb, rnd):
        o = self.o
        bm = mb.bm
        n = o["around"]
        span = o["height"] - o["from"]
        main = rnd.randrange(3)
        dark = "leaf_3" if self.state != "autumn" else f"leaf_{main + 1}"
        # The core: a plain spindle a little inside the sprays.
        levels = [o["from"] + span * t for t in (0.0, 0.12, 0.3, 0.52, 0.72, 0.88)]
        rings = [[bm.verts.new((self.radius(z) * 0.8 * math.cos((i + 0.5 * (k % 2)) * math.tau / 6),
                                self.radius(z) * 0.8 * math.sin((i + 0.5 * (k % 2)) * math.tau / 6), z))
                  for i in range(6)] for k, z in enumerate(levels)]
        bottom, apex = bm.verts.new((0, 0, o["from"] - 0.1)), bm.verts.new((0, 0, o["height"] - 0.25))
        for low, high in zip(rings, rings[1:]):
            for i in range(6):
                self.face(mb, (low[i], low[(i + 1) % 6], high[(i + 1) % 6], high[i]), dark)
        for i in range(6):
            self.face(mb, (bottom, rings[0][(i + 1) % 6], rings[0][i]), dark)
            self.face(mb, (apex, rings[-1][i], rings[-1][(i + 1) % 6]), dark)
        # The sprays, row over row, each row half a step around from the last.
        for k in range(o["rings"]):
            z = o["from"] + span * 0.88 * (k / (o["rings"] - 1)) ** 0.95 - 0.1
            for i in range(n):
                a = (i + 0.5 * (k % 2) + rnd.uniform(-0.15, 0.15)) * math.tau / n
                d = Vector((math.cos(a), math.sin(a), 0))
                side = Vector((-d.y, d.x, 0))
                long = o["spray"] * rnd.uniform(0.85, 1.15) * (1.0 - 0.25 * k / o["rings"])
                tip_z = min(z + long, o["height"] + (0.0 if k == o["rings"] - 1 else -0.2))
                low_r, tip_r = self.radius(z + 0.1) * 0.82, self.radius(tip_z) * rnd.uniform(1.0, 1.12) + 0.06
                half = max(0.2, self.radius(z + long * 0.3) * math.pi / n * 1.05)
                left = bm.verts.new(d * low_r - side * half + UP * z)
                right = bm.verts.new(d * low_r + side * half + UP * z)
                tip = bm.verts.new(d * tip_r + UP * tip_z)
                ridge = bm.verts.new(d * (self.radius(z + long * 0.35) * 1.08 + 0.1)
                                     + side * rnd.uniform(-0.3, 0.3) * half + UP * (z + long * 0.35))
                self.face(mb, (left, ridge, tip), self.tone(rnd, (d - side * 0.9 + UP * 0.3).normalized(), main))
                self.face(mb, (ridge, right, tip), self.tone(rnd, (d + side * 0.9 + UP * 0.3).normalized(), main))
                self.face(mb, (left, right, ridge), self.tone(rnd, (d - UP * 0.6).normalized(), main, -0.3))
                self.face(mb, (right, left, tip), dark)

    def branches(self, mb, rnd):
        o = self.o
        count = o["branches"]
        for i in range(count):
            z = 0.7 + (o["height"] - 2.6) * (i + rnd.uniform(0.0, 1.0)) / count
            a = i * 2.39996 + rnd.uniform(-0.3, 0.3)
            d = Vector((math.cos(a), math.sin(a), 0))
            long = (1.5 + 1.2 * (1.0 - z / o["height"])) * rnd.uniform(0.85, 1.15)
            long = min(long, o["height"] - 0.15 - z)
            pts = [UP * z]
            for t, f in ((0.22, 0.6), (0.55, 0.95), (1.0, 0.8)):
                zz = z + long * t
                pts.append(d * (max(0.1, self.radius(zz)) * f) + UP * zz)
            thick = 0.095 * (1.2 - z / o["height"])
            tube(mb, pts, [thick, thick * 0.8, thick * 0.55], 3, self.bark(rnd))
            p = pts[1].lerp(pts[2], rnd.uniform(0.1, 0.7))
            turn = Vector((-d.y, d.x, 0)) * rnd.choice((-1, 1))
            tube(mb, [p, p + (UP + turn * 0.4 + d * 0.15).normalized() * (long * 0.45)], [thick * 0.55], 3,
                 self.bark(rnd))


# -------------------------------------------------------------------- palm

class Palm(Built):
    """A ringed trunk and a crown of arching fronds. A frond is a rib with a
    pair of pointed leaflets on every stretch (each a thin closed piece);
    without leaves, the rib and bristles in their place."""

    defaults = {
        "height": 4.5,          # Where the crown is.
        "foot": 0.32,
        "neck": 0.23,           # Trunk radius under the crown.
        "rings": 11,
        # The fronds in rows from the top one: (count, elevation in degrees, length).
        "rows": [(5, 64.0, 2.9), (6, 38.0, 3.5), (6, 12.0, 3.4)],
        "bend": 66.0,           # How many degrees a frond turns down along its length.
        "stretches": 9,
        "leaflet": 1.0,         # Longest leaflet.
        "budget": 0,
    }

    def build(self, mb, leaves):
        o = self.o
        rnd = random.Random(o["seed"] + 23)
        # The trunk: stacked rings, each wider at its top (the old leaf bases).
        step = (o["height"] - 0.6) / o["rings"]
        for i in range(o["rings"]):
            r = o["foot"] + (o["neck"] - o["foot"]) * (i / (o["rings"] - 1)) ** 0.7
            lean = Vector((rnd.uniform(-0.012, 0.012), rnd.uniform(-0.012, 0.012), 0))
            mb.cylinder(Vector((0, 0, i * step - (0.05 if i == 0 else 0.0))) + lean,
                        Vector((0, 0, (i + 1) * step + 0.03)),
                        r * (1.18 if i == 0 else 0.9), r * 1.1, self.bark(rnd), segments=7)
        # The bulb under the crown.
        z0 = o["rings"] * step
        mb.cylinder((0, 0, z0 - 0.02), (0, 0, z0 + 0.38), o["neck"] * 1.0, o["neck"] * 1.55, "bark_shade", segments=7)
        mb.cylinder((0, 0, z0 + 0.36), (0, 0, o["height"] + 0.2), o["neck"] * 1.55, o["neck"] * 0.7, "bark", segments=7)
        number = 0
        for row, (count, elevation, length) in enumerate(o["rows"]):
            phase = rnd.uniform(0.0, math.tau)
            for j in range(count):
                a = phase + (j + rnd.uniform(-0.2, 0.2)) * math.tau / count
                self.frond(mb, rnd, a, math.radians(elevation + rnd.uniform(-7, 7)), length * rnd.uniform(0.92, 1.08),
                           leaves, row, number)
                number += 1

    def frond(self, mb, rnd, azimuth, elevation, length, leaves, row, number):
        o = self.o
        k = o["stretches"]
        d = Vector((math.cos(azimuth), math.sin(azimuth), 0))
        side = Vector((-d.y, d.x, 0))
        p = Vector((0, 0, o["height"])) + d * 0.12
        rib, along = [p], []
        bend = math.radians(o["bend"] * rnd.uniform(0.85, 1.12))
        for i in range(k):
            e = elevation - bend * ((i + 0.5) / k) ** 1.25
            t = d * math.cos(e) + UP * math.sin(e)
            p = p + t * (length / k)
            rib.append(p)
            along.append(t)
        thick = 0.06
        tube(mb, [rib[0], rib[k // 3], rib[2 * k // 3], rib[-1]], [thick, thick * 0.8, thick * 0.55], 3,
             self.bark(rnd))
        main = (number + row) % 3
        for i in range(k):
            t = along[i]
            down = t.cross(side)
            if down.z > 0:
                down = -down
            f = (i + 0.5) / k
            w = o["leaflet"] * (0.35 + 0.65 * math.sin(math.pi * min(1.0, f * 1.25 + 0.12)) ** 0.7)
            w *= rnd.uniform(0.9, 1.1)
            mid = rib[i].lerp(rib[i + 1], 0.5)
            ends = [mid + side * (s * w) + down * (w * 0.5) + t * (w * 0.45) for s in (1, -1)]
            if leaves:  # A pointed leaflet to each side.
                up = -down
                half = t * (length / k * 0.62)
                for s, q in zip((1, -1), ends):
                    knee = mid.lerp(q, 0.38)
                    card(mb, [mid, knee + half, q, knee - half], 0.04,
                         self.tone(rnd, (up + side * (0.5 * s)).normalized(), main, 0.15 - 0.25 * row))
            else:  # A bristle on one side and the other in turn.
                q = ends[i % 2]
                tube(mb, [mid, mid.lerp(q, 0.85)], [thick * 0.45], 3, self.bark(rnd))


def variants(kind, tree, leaves, **options):
    """The three states of one built tree."""
    return [kind(tree, state, leaves, **options) for state in STATES]
