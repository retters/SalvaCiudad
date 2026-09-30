"""Strawberry: a red heart-shaped berry, point down, with small yellow seeds
lying on its facets and a green star of leaves with a short stalk on top.
Real size (8 cm).

The berry is not remeshed: welding primitives leaves a crease where the
round shoulders meet the point, so it is lathed from a profile as staggered
rings of triangles, the regular faceting of the reference. Only the small
green knob under the stalk goes through the usual remesh."""

import math
import random

from mathutils import Vector

import common
import studies

# The berry's profile, bottom to top: (height, radius). The point and the
# top center close it below and above.
PROFILE = [(0.005, 0.007), (0.012, 0.016), (0.021, 0.025), (0.031, 0.031), (0.042, 0.035),
           (0.053, 0.036), (0.062, 0.032), (0.069, 0.022)]
POINT_Z = 0.0
TOP_Z = 0.068            # Center of the top, a little sunk under the leaves.
COLUMNS = 12
SEED_GAPS = range(1, 7)  # Gaps between rings that carry seeds.
KNOB = ((0.0, 0.0, 0.07), (0.007, 0.007, 0.005))
LEAVES = 7


def shoulder_z(r):
    """Height of the profile's upper part at radius r."""
    pts = PROFILE[5:] + [(TOP_Z, 0.0)]
    for (z0, r0), (z1, r1) in zip(pts, pts[1:]):
        if r1 <= r <= r0:
            return z0 + (z1 - z0) * (r0 - r) / (r0 - r1)
    return PROFILE[5][0]


class Strawberry(studies.Spec):
    name = "strawberry"
    colors = {
        "red": common.rgb(0xE0262E),
        "red_light": common.rgb(0xEE3F40),
        "red_shade": common.rgb(0xC41C26),
        "seed": common.rgb(0xFFD84A),
        "leaf": common.rgb(0x3FAE35),
        "leaf_dark": common.rgb(0x2E8C2A),
    }
    ellipsoids = [KNOB]
    capsules = []
    budget = 40
    max_tris = 1000

    def paint(self, c, n):
        return "leaf"

    def details(self, mb):
        for center, normal, meridian in self.berry(mb):
            side = normal.cross(meridian).normalized()
            up = side.cross(normal).normalized()
            c = center + normal * 0.0006
            studies.plate(mb, [c - up * 0.0036, c + side * 0.0021, c + up * 0.0036, c - side * 0.0021],
                          0.0012, "seed")
        self.calyx(mb)

    def berry(self, mb):
        """Lathes the berry; returns where the seeds go: (center, outward
        normal, direction up the berry) of every other upward triangle."""
        bm = mb.bm
        rnd = random.Random(11)
        step = math.tau / COLUMNS
        rings = []
        for k, (z, r) in enumerate(PROFILE):
            off = 0.5 * (k % 2)
            ring = []
            for i in range(COLUMNS):
                a = (i + off) * step
                rr = r * (1.0 + rnd.uniform(-0.04, 0.04))
                ring.append(bm.verts.new((rr * math.cos(a) * 1.03, rr * math.sin(a),
                                          z + rnd.uniform(-0.001, 0.001))))
            rings.append(ring)
        mats = {k: mb._material_index(k) for k in ("red", "red_light", "red_shade")}
        seeds = []

        def face(verts):
            f = bm.faces.new(verts)
            x = rnd.random()
            f.material_index = mats["red_light" if x < 0.18 else "red_shade" if x < 0.36 else "red"]
            f.smooth = False
            return f

        for k in range(len(rings) - 1):
            lo, hi = rings[k], rings[k + 1]
            for i in range(COLUMNS):
                j = (i + 1) % COLUMNS
                # Upper vertex i sits between lower i and i+1 when the upper
                # ring is the offset one (k even); else upper i+1 does.
                if k % 2 == 0:
                    up = face((lo[i], lo[j], hi[i]))
                    face((hi[i], lo[j], hi[j]))
                else:
                    up = face((lo[i], lo[j], hi[j]))
                    face((hi[i], lo[i], hi[j]))
                if k in SEED_GAPS and (i + k) % 2 == 0:
                    up.normal_update()
                    c = up.calc_center_median()
                    n = up.normal.copy()
                    if n.dot(Vector((c.x, c.y, 0.0))) < 0:
                        n = -n
                    top = max(up.verts, key=lambda v: v.co.z).co
                    seeds.append((c, n, (top - c).normalized()))
        for ring, z in ((rings[0], POINT_Z), (rings[-1], TOP_Z)):
            c = bm.verts.new((0, 0, z))
            for i in range(COLUMNS):
                face((ring[i], ring[(i + 1) % COLUMNS], c))
        return seeds

    def calyx(self, mb):
        """Pointed leaves lying on the shoulders, and the stalk."""
        mid_r = PROFILE[-1][1] * 0.55
        for i in range(LEAVES):
            a = i * math.tau / LEAVES + 0.2
            d = Vector((math.cos(a), math.sin(a), 0.0))
            s = Vector((-d.y, d.x, 0.0))
            length = 0.024 + 0.003 * (i % 2)
            z_mid = max(shoulder_z(mid_r), TOP_Z) + 0.0032
            pts = [Vector((0, 0, TOP_Z + 0.004)),
                   d * mid_r + s * 0.0085 + Vector((0, 0, z_mid)),
                   d * length + Vector((0, 0, shoulder_z(length) + 0.0018)),
                   d * mid_r - s * 0.0085 + Vector((0, 0, z_mid))]
            studies.plate(mb, pts, 0.0016, "leaf" if i % 2 else "leaf_dark")
        top = Vector((0, 0, TOP_Z + 0.002))
        mb.cylinder(top, top + Vector((0.0015, 0, 0.011)), 0.0026, 0.002, "leaf", segments=6)


SPECS = [Strawberry()]
