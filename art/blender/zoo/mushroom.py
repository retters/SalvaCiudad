"""Mushroom: a fly agaric. A red domed cap with a flat cream underside and
white spots that follow its surface, on a thick cream stem with a slight
ring and a swollen base."""

import math

from mathutils import Vector
from mathutils.bvhtree import BVHTree

import common
import studies

CAP = ((0.0, 0.0, 0.172), (0.132, 0.132, 0.082))
UNDER_Z = 0.158          # The cap's flat underside.
# The stem, a faceted prism: (height, radius) rings, bottom first.
STEM = [(0.0, 0.05), (0.018, 0.054), (0.05, 0.045), (0.172, 0.036)]
STEM_SIDES = 9
RING_Z = (0.122, 0.104)  # The ring's top (on the stem) and its flared bottom.
# Spots: (elevation above the cap's rim in degrees, azimuth in degrees, radius).
SPOTS = [(84, 200, 0.019)] + [(56, 30 + i * 72, 0.02 - 0.002 * (i % 2)) for i in range(5)] + [
    (24, 66 + i * 51.4, 0.016 + 0.003 * (i % 3 == 0)) for i in range(7)]


def surface(tree, origin, direction):
    """Where a ray from outside the model hits it: (point, outward normal)."""
    d = Vector(direction).normalized()
    hit, normal, _, _ = tree.ray_cast(Vector(origin), d)
    if hit is None:
        return None, None
    if normal.dot(d) > 0.0:
        normal = -normal
    return hit, normal


def surface_plate(mb, tree, point, normal, points_2d, thickness, mat, lift=0.0):
    """A flat piece lying on the surface around point: points_2d are (u, v)
    offsets on the tangent plane; each is dropped onto the surface, so the
    piece follows its curve, and the piece is lifted half its thickness plus
    lift above it."""
    u = normal.orthogonal().normalized()
    v = normal.cross(u)
    pts = []
    for a, b in points_2d:
        p = point + u * a + v * b
        hit, _ = surface(tree, p + normal * 0.05, -normal)
        pts.append((hit if hit is not None else p) + normal * (thickness * 0.5 + lift))
    return studies.plate(mb, pts, thickness, mat)


def blob(radius, count, seed):
    """An irregular convex polygon of about the given radius."""
    return [(radius * (0.85 + 0.15 * math.sin(seed + i * 2.3)) * math.cos(i * math.tau / count + seed),
             radius * (0.85 + 0.15 * math.sin(seed + i * 2.3)) * math.sin(i * math.tau / count + seed))
            for i in range(count)]


def stem_radius(z):
    for (z0, r0), (z1, r1) in zip(STEM, STEM[1:]):
        if z <= z1:
            return r0 + (r1 - r0) * max(0.0, (z - z0) / (z1 - z0))
    return STEM[-1][1]


def loft(mb, rings, sides, mat):
    """A closed prism through (height, radius) rings around the Z axis."""
    bm = mb.bm
    loops = [[bm.verts.new((r * math.cos(i * math.tau / sides), r * math.sin(i * math.tau / sides), z))
              for i in range(sides)] for z, r in rings]
    for a, b in zip(loops, loops[1:]):
        for i in range(sides):
            j = (i + 1) % sides
            bm.faces.new((a[i], a[j], b[j], b[i]))
    bm.faces.new(list(reversed(loops[0])))
    bm.faces.new(loops[-1])
    return mb._finish([v for loop in loops for v in loop], mat, None)


class Mushroom(studies.Spec):
    name = "mushroom"
    colors = {
        "cap": common.rgb(0xE0322A),
        "cap_light": common.rgb(0xEC4A3A),
        "cap_shade": common.rgb(0xC92820),
        "spot": common.rgb(0xFAF6EC),
        "gill": common.rgb(0xF0E2C4),
        "stem": common.rgb(0xF4ECD8),
        "ring": common.rgb(0xE6D8B8),
    }
    ellipsoids = [CAP]
    capsules = []
    cuts = [((0, 0, UNDER_Z), (0, 0, 1), lambda c, n: True)]
    budget = 420
    max_tris = 1000
    tone_material = "cap"
    tones = 0.3

    def paint(self, c, n):
        return "cap" if c[2] > UNDER_Z + 0.001 else "gill"

    def details(self, mb):
        self.flatten_underside(mb)
        loft(mb, STEM, STEM_SIDES, "stem")
        tree = BVHTree.FromBMesh(mb.bm)
        center = Vector(CAP[0])
        for k, (elev, azim, radius) in enumerate(SPOTS):
            e, a = math.radians(elev), math.radians(azim)
            d = Vector((math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e)))
            hit, normal = surface(tree, center + d * 0.5, -d)
            if hit is not None:
                surface_plate(mb, tree, hit, normal, blob(radius, 6, k * 1.7), 0.003, "spot")
        # The ring: a short cone flaring down from the stem.
        mb.cylinder((0, 0, RING_Z[0]), (0, 0, RING_Z[1]), stem_radius(RING_Z[0]) - 0.002,
                    stem_radius(RING_Z[1]) + 0.012, "ring", segments=STEM_SIDES)

    def flatten_underside(self, mb):
        """Presses the lower half of the cap onto a flat underside and paints
        it like gills."""
        bm = mb.bm
        for v in bm.verts:
            if v.co.z < UNDER_Z:
                v.co.z = UNDER_Z
        bm.normal_update()
        gill = mb._material_index("gill")
        for f in bm.faces:
            if all(abs(v.co.z - UNDER_Z) < 1e-4 for v in f.verts):
                f.material_index = gill


SPECS = [Mushroom()]
