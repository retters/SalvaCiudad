"""Cactus: a green saguaro-like column with two arms bending up, all with
vertical ribs, small pale spines on the ribs and a pink flower on top, in an
octagonal terracotta pot with a rim and dark soil.

The column and the arms are swept tubes with a star-shaped section: the
ribs are real geometry, which a remeshed and decimated surface loses (it
turns a column into a few long triangles). Only the domed soil goes
through the usual remesh."""

import math
import random

from mathutils import Vector

import common
import studies

RIBS = 8
RIB_INNER = 0.82  # Groove radius / rib radius.
# Tube paths: [(point, radius)...], root first; the last end gets a dome.
COLUMN = [((0.0, 0.0, 0.27), 0.112), ((0.0, 0.0, 0.46), 0.112), ((0.0, 0.0, 0.64), 0.108),
          ((0.0, 0.0, 0.77), 0.104)]
ARMS = [
    [((0.02, 0.0, 0.42), 0.066), ((0.15, 0.0, 0.42), 0.066), ((0.205, 0.0, 0.47), 0.064),
     ((0.222, 0.0, 0.54), 0.063), ((0.225, 0.0, 0.63), 0.062)],
    [((-0.02, 0.0, 0.53), 0.06), ((-0.14, 0.0, 0.53), 0.06), ((-0.19, 0.0, 0.575), 0.058),
     ((-0.205, 0.0, 0.64), 0.057), ((-0.207, 0.0, 0.70), 0.056)],
]
POT_Z = (0.0, 0.25)       # Pot body, bottom and top.
POT_R = (0.13, 0.165)     # Pot body radius at the bottom and the top.
RIM = (0.23, 0.31, 0.19)  # Rim bottom, top and radius.
SOIL = ((0.0, 0.0, 0.3), (0.172, 0.172, 0.022))


def sweep(mb, path, mat_for, rnd):
    """A tube with a star-shaped section (RIBS ribs) along path, open at
    the root and domed at the end. Returns the rings as (center, tangent,
    rib crest vertices) for placing spines; mat_for(rnd) picks each face's
    material."""
    bm = mb.bm
    pts = [Vector(p) for p, _ in path]
    radii = [r for _, r in path]
    tangents = [(pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized() for i in range(len(pts))]
    t0 = tangents[0]
    ref = Vector((1, 0, 0)) if abs(t0.x) < 0.9 else Vector((0, 0, 1))
    normal = (ref - t0 * t0.dot(ref)).normalized()
    frames = []
    for i, t in enumerate(tangents):
        if i:
            normal = tangents[i - 1].rotation_difference(t) @ normal
        frames.append((pts[i], t, normal.copy(), radii[i]))
    # The dome: two shrinking rings past the end.
    tip, t, n, r = frames[-1]
    frames += [(tip + t * (r * 0.5), t, n, r * 0.8), (tip + t * (r * 0.85), t, n, r * 0.45)]
    rings = []
    count = 2 * RIBS
    for fc, ft, fn, fr in frames:
        fb = ft.cross(fn)
        rings.append([bm.verts.new(fc + (fn * math.cos(m * math.pi / RIBS) + fb * math.sin(m * math.pi / RIBS))
                                   * (fr * (1.0 if m % 2 == 0 else RIB_INNER))) for m in range(count)])

    def face(verts):
        f = bm.faces.new(verts)
        f.material_index = mb._material_index(mat_for(rnd))
        f.smooth = False

    for a, b in zip(rings, rings[1:]):
        for m in range(count):
            k = (m + 1) % count
            face((a[m], a[k], b[k], b[m]))
    # The root end stays open: it is always buried (in the soil, in the column).
    apex = bm.verts.new(tip + t * r)
    for m in range(count):
        face((rings[-1][m], rings[-1][(m + 1) % count], apex))
    return [(c, t, ring[0::2]) for (c, t, _, _), ring in zip(frames, rings)], apex.co.copy()


def green(rnd):
    x = rnd.random()
    return "green_light" if x < 0.14 else "green_shade" if x < 0.3 else "green"


class Cactus(studies.Spec):
    name = "cactus"
    colors = {
        "green": common.rgb(0x4CB83A),
        "green_light": common.rgb(0x62CB4A),
        "green_shade": common.rgb(0x3FA030),
        "spine": common.rgb(0xF2EFD0),
        "petal": common.rgb(0xF06BB0),
        "pollen": common.rgb(0xFFD23A),
        "pot": common.rgb(0xD4733A),
        "pot_shade": common.rgb(0xBC6230),
        "soil": common.rgb(0x4A3226),
    }
    ellipsoids = [SOIL]
    capsules = []
    budget = 60
    max_tris = 1000

    def paint(self, c, n):
        return "soil"

    def details(self, mb):
        rnd = random.Random(5)
        self.pot(mb)
        rings, apex = sweep(mb, COLUMN, green, rnd)
        # Spines on every other rib, alternating between the rings.
        for i, (c, t, crests) in enumerate(rings[1:3], start=1):
            for j, v in enumerate(crests):
                if (j + i) % 2 == 0 and not (abs((v.co - c).x) > 0.08 and 0.4 < c.z < 0.6):
                    self.spine(mb, v.co, (v.co - c).normalized(), t)
        for arm in ARMS:
            rings, _ = sweep(mb, arm, green, rnd)
            for i, (c, t, crests) in enumerate(rings[2:4], start=2):
                for j, v in enumerate(crests):
                    if (j + i) % 2 == 0 and (v.co - c).z > -0.03 and abs((v.co - c).y) < 0.05:
                        self.spine(mb, v.co, (v.co - c).normalized(), t)
        self.flower(mb, apex - Vector((0, 0, 0.004)))

    def pot(self, mb):
        body = mb.cylinder((0, 0, POT_Z[0]), (0, 0, POT_Z[1]), POT_R[0], POT_R[1], "pot", segments=8)
        rim = mb.cylinder((0, 0, RIM[0]), (0, 0, RIM[1]), RIM[2], RIM[2], "pot", segments=8)
        # Every other side of the pot a little darker, like its facets.
        shade = mb._material_index("pot_shade")
        for verts in (body, rim):
            for f in {f for v in verts for f in v.link_faces if abs(f.normal.z) < 0.5}:
                c = f.calc_center_median()
                if int(math.floor((math.atan2(c.y, c.x) % math.tau) / (math.tau / 8))) % 2:
                    f.material_index = shade

    def flower(self, mb, c):
        for i in range(5):
            a = i * math.tau / 5 + 0.3
            d = Vector((math.cos(a), math.sin(a), 0.0))
            s = Vector((-d.y, d.x, 0.0))
            studies.plate(mb, [c + d * 0.01, c + d * 0.04 + s * 0.024 + Vector((0, 0, 0.014)),
                               c + d * 0.072 + Vector((0, 0, 0.034)),
                               c + d * 0.04 - s * 0.024 + Vector((0, 0, 0.014))], 0.007, "petal")
        mb.sphere(c + Vector((0, 0, 0.014)), 0.018, "pollen", segments=6, rings=4)

    def spine(self, mb, base, d, t):
        """A small pale spike on a rib crest, pointing out and a little
        along the tube."""
        side = d.cross(t).normalized() * 0.006
        base = base - d * 0.004
        studies.flap(mb, base - side, base + side, base + d * 0.03 + t * 0.008, 0.003, "spine")


SPECS = [Cactus()]
