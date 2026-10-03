"""Shared generator of the giant trees: one tree, two states.

A giant is a rare landmark tree, 22 to 45 m tall, in the two states of the
reference pictures ("Arboles 7.png" with leaves, "Arboles 8.png" without):
"bloom" and "bare". Both states are built from one definition, so the
trunk, the roots and every branch are identical in the two; only, with
leaves, what the leaves swallow for good (the end of a twig inside a
clump) is not built.

Each giant has its own module (giant_baobab.py...), a subclass of Giant
that fills in shape() what the tree is made of:

  * welded parts (self.capsules, self.ellipsoids): the trunk, the roots
    and the thick branches, which the remesh and collapse of
    studies.build_final turn into one faceted surface. roots() and knobs()
    add the usual ones: roots all around the foot, and bumps that make
    the bark of a thick trunk as knobbly as in the pictures;
  * thin branches (self.lines, or limb(), which splits a branch into its
    welded start and its thin end): tapered closed tubes;
  * clumps of leaves (self.blobs): dark faceted cores covered with small
    folded squares in three tones, as the ordinary trees of _tree.py;
  * whatever else it needs, built directly in both() (both states) and
    foliage() (with leaves only): mushroom caps, hanging leaves, tufts.

Four of them (baobab, cherry, mangrove and ginkgo) take their branches and
their clumps from the pictures, traced by _giant_trace.py into
_giant_traced.py: Skeleton gives the flat tracing its depth, exactly as
_tree.py does for the ordinary trees (the method is copied from there, with
its lengths scaled, so that this file does not depend on that one). The
pictures only show the limbs that spread to the sides, so the limbs are
also copied toward the back (see Skeleton.around): the front view stays
that of the picture and the tree is full all around.

Around the foot, a ring of stones, grass tufts and small flowers; with
leaves it has more grass and flowers, between the same stones.

The game culls back faces, so every piece is closed, or two-sided, except
the folded leaves, which lie on their clump's core and are seen from
outside only (see fold_keeps_side for the one trap there).

Everything random comes from random.Random with the seed given to the tree,
so building again gives the same files. With the environment variable
TREE_DEBUG set, every model prints where its triangles went.
"""

import math
import os
import random

import bmesh
from mathutils import Matrix, Vector

import common
import studies

STATES = ("bloom", "bare")
LIMITS = {"bloom": 6000, "bare": 4000}
LIGHT = Vector((-0.35, -0.5, 0.8)).normalized()  # Where the pictures are lit from.
UNIT = 4.0  # A giant is about four times an ordinary tree; lengths taken from _tree.py are scaled by it.
# Twig simplification tolerances, from fine to coarse.
STEPS = [0.025 * UNIT * 1.1 ** i for i in range(34)]
OCTA = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
OCTA_FACES = [(0, 2, 4), (2, 1, 4), (1, 3, 4), (3, 0, 4), (2, 0, 5), (1, 2, 5), (3, 1, 5), (0, 3, 5)]
ICO = [(-1, 1.618, 0), (1, 1.618, 0), (-1, -1.618, 0), (1, -1.618, 0), (0, -1, 1.618), (0, 1, 1.618),
       (0, -1, -1.618), (0, 1, -1.618), (1.618, 0, -1), (1.618, 0, 1), (-1.618, 0, -1), (-1.618, 0, 1)]
ICO_FACES = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2),
             (10, 7, 6), (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11),
             (6, 2, 10), (8, 6, 7), (9, 8, 1)]


# ------------------------------------------------------------ flat helpers

def simplify(points, keep, tolerance):
    """Douglas-Peucker on 3D points; the indices in `keep` stay. Returns
    the indices kept."""
    n = len(points)
    stay = [False] * n
    stay[0] = stay[-1] = True
    for i in keep:
        stay[i] = True
    anchors = [i for i in range(n) if stay[i]]
    stack = list(zip(anchors, anchors[1:]))
    while stack:
        a, b = stack.pop()
        pa, pb = points[a], points[b]
        d = (pb[0] - pa[0], pb[1] - pa[1], pb[2] - pa[2])
        dd = d[0] * d[0] + d[1] * d[1] + d[2] * d[2] or 1e-12
        worst, at = 0.0, None
        for i in range(a + 1, b):
            q = (points[i][0] - pa[0], points[i][1] - pa[1], points[i][2] - pa[2])
            t = max(0.0, min(1.0, (q[0] * d[0] + q[1] * d[1] + q[2] * d[2]) / dd))
            e = math.sqrt((q[0] - d[0] * t) ** 2 + (q[1] - d[1] * t) ** 2 + (q[2] - d[2] * t) ** 2)
            if e > worst:
                worst, at = e, i
        if at is not None and worst > tolerance:
            stay[at] = True
            stack += [(a, at), (at, b)]
    return [i for i in range(n) if stay[i]]


def mix(a, b, t):
    """A color between two 0xRRGGBB colors."""
    out = 0
    for shift in (16, 8, 0):
        out |= int(round(((a >> shift) & 255) * (1.0 - t) + ((b >> shift) & 255) * t)) << shift
    return out


def tones(light, mid, dark):
    """Three material colors from the lit, middle and shaded colors sampled
    in a picture: the game lights the model itself, so the darkest tone is
    not as dark as the picture's shade."""
    return [light, mix(light, mid, 0.55), mix(mid, dark, 0.3)]


def bark_tones(light, mid):
    """The three bark colors (light, main, shade) from the lit and the
    middle colors sampled in a picture."""
    return [mix(light, mid, 0.15), mix(light, mid, 0.48), mix(light, mid, 0.9)]


def noise(c):
    """A fixed pseudo-random number in 0..1 for a place."""
    h = math.sin(c[0] * 12.9898 + c[1] * 78.233 + c[2] * 37.719) * 43758.5453
    return h - math.floor(h)


class Branch:
    """A branch in space: points, radii, its parent and the vertex of the
    parent it starts at."""

    def __init__(self, parent, vertex, flat):
        self.parent = parent
        self.vertex = vertex
        self.flat = [(x, z) for x, z, r in flat]
        self.radii = [r for x, z, r in flat]
        self.points = []
        self.children = []
        self.welded = 0   # How many of its first vertices are thick enough to weld.
        self.sign = 1
        cum = [0.0]
        for a, b in zip(self.flat, self.flat[1:]):
            cum.append(cum[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
        self.along = cum
        self.length = cum[-1]


class Skeleton:
    """A traced tree's branches placed in space, and its canopy."""

    def __init__(self, data, o):
        self.o = o
        self.rnd = random.Random(o["seed"])
        self.outline = data["outline"]
        self.branches = [Branch(p, v, pts) for p, v, pts in data["branches"]]
        self.skip()
        self.foot()
        for i, b in enumerate(self.branches):
            if b.parent >= 0:
                self.branches[b.parent].children.append(i)
        self.place()
        self.weld()
        self.blobs = self.place_blobs(list(data["blobs"]) + list(o["more_blobs"]))
        self.around()

    # ---------------------------------------------------------------- trunk

    def skip(self):
        """Leaves out the branches that end in one of the circles of the
        "skip" option (x, z, radius), with all that grows from them: spurs
        of the tracing inside the trunk's own outline."""
        gone = set()
        for i, b in enumerate(self.branches):
            x, z = b.flat[-1]
            if b.parent in gone or (i and any(math.hypot(x - sx, z - sz) < sr for sx, sz, sr in self.o["skip"])):
                gone.add(i)
        index, kept = {}, []
        for i, b in enumerate(self.branches):
            if i not in gone:
                index[i] = len(kept)
                kept.append(b)
        for b in kept:
            b.parent = index.get(b.parent, -1)
        self.branches = kept

    def foot(self):
        """The tracing starts above the roots: the trunk goes on down to the
        ground through the points of the "foot" option (x, z, radius, from
        the ground up). Its thickness never grows on the way up by more
        than a fork explains."""
        trunk = self.branches[0]
        extra = list(self.o["foot"])
        limit = self.o["trunk_max"]
        radii = []
        for v in trunk.radii:
            limit = min(limit * 1.03, v)
            radii.append(limit)
        flat = extra + [(p[0], p[1], r) for p, r in zip(trunk.flat, radii)]
        for b in self.branches:
            if b.parent == 0:
                b.vertex += len(extra)
        self.branches[0] = Branch(-1, 0, flat)
        scale = self.o["thick"]
        for b in self.branches:
            b.radii = [r * scale for r in b.radii]

    # ---------------------------------------------------------------- depth

    def dome(self, x, z, inset=0.0, scale=1.0):
        """How far in front of (or behind) the picture's plane the dome's
        surface is at a place of the picture."""
        lo = hi = weight = 0.0
        for oz, a, b in self.outline:
            w = max(0.0, 1.0 - abs(oz - z) / (0.9 * UNIT))
            lo, hi, weight = lo + a * w, hi + b * w, weight + w
        if not weight:
            return 0.0
        lo, hi = lo / weight, hi / weight
        half = (hi - lo) * 0.5 * self.o["depth"] * scale - inset
        if half <= 0.0:
            return 0.0
        v = half * half - (x - (hi + lo) * 0.5) ** 2
        return math.sqrt(v) if v > 0 else 0.0

    def place(self):
        """Gives every branch its depth. Seen from above, a branch turns
        away from its parent's direction by `lean` degrees, to one side or
        the other in turn with its siblings, so the branches fan out all
        around as they do in the picture's plane; and a branch that the
        picture shows short, near the middle, is one that comes forward or
        goes back as far as the dome."""
        o, rnd = self.o, self.rnd
        branches = self.branches
        # Sides: balanced by size among the branches that leave the trunk,
        # in turn along every other branch.
        weight = [b.length for b in branches]
        for i in range(len(branches) - 1, 0, -1):
            weight[branches[i].parent] += weight[i]
        side = {1: 0.0, -1: 0.0}
        first = rnd.choice((1, -1))
        for i in sorted(branches[0].children, key=lambda i: -weight[i]):
            sign = first if side[first] <= side[-first] else -first
            side[sign] += weight[i]
            branches[i].sign = sign
        for b in branches[1:]:
            sign = rnd.choice((1, -1))
            for c in sorted(b.children, key=lambda c: branches[c].vertex):
                branches[c].sign = sign
                sign = -sign
        turn = [0.0] * len(branches)  # Degrees out of the picture's plane.
        for i, b in enumerate(branches):
            if i == 0:
                b.sign = first
                y0 = 0.0
            else:
                parent = branches[b.parent]
                y0 = parent.points[b.vertex][1]
                turn[i] = max(-o["spread"], min(o["spread"], turn[b.parent] + b.sign * rnd.uniform(*o["lean"])))
            tx, tz = b.flat[-1]
            dy = abs(tx - b.flat[0][0]) * math.tan(math.radians(turn[i]))
            out = 1 if turn[i] > 0 else (-1 if turn[i] < 0 else b.sign)
            far = out * self.dome(tx, tz) * rnd.uniform(0.6, 1.0) - y0
            if far * out > abs(dy):
                dy = far
            # The branch leans as it goes up or out; where it hangs it
            # goes straight down, under where it got to.
            gain = [0.0]
            for (ax, az), (bx, bz) in zip(b.flat, b.flat[1:]):
                step = math.hypot(bx - ax, bz - az)
                fall = max(0.0, az - bz) / (step or 1.0)
                gain.append(gain[-1] + step * max(o["droop"], 1.0 - fall))
            reach = o["slope"] * gain[-1]
            dy = max(-reach, min(reach, dy))
            # Not far beyond the dome.
            limit = max(self.dome(tx, tz, scale=o["over"] / o["depth"]), abs(y0) * 0.8)
            dy = max(-limit, min(limit, y0 + dy)) - y0
            if i == 0:
                dy *= o["trunk_lean"]
            power = 2.0 if i == 0 else o["bow"]
            ys = [y0 + dy * (g / (gain[-1] or 1.0)) ** power for g in gain]
            # A zigzag out of the plane as the traced one in it, so the
            # twigs are not straight seen from the side.
            for k in range(1, len(ys) - 1):
                if i and b.radii[k] < o["weld"]:
                    ys[k] += rnd.uniform(-1.0, 1.0) * o["wiggle"] * (b.along[k + 1] - b.along[k - 1]) * 0.5
            b.points = [(x, y, z) for (x, z), y in zip(b.flat, ys)]

    def weld(self):
        """Marks the thick start of every branch, which goes to the remesh."""
        limit = self.o["weld"]
        for b in self.branches:
            if b.parent >= 0 and self.branches[b.parent].welded <= b.vertex:
                continue  # It starts on a thin part.
            n = 0
            while n < len(b.radii) and b.radii[n] >= limit:
                n += 1
            b.welded = n if n >= 2 else 0

    def capsules(self):
        out = []
        for b in self.branches:
            if b.welded < 2:
                continue
            forks = [self.branches[c].vertex for c in b.children if self.branches[c].vertex < b.welded]
            kept = simplify(b.points[:b.welded], forks, 0.04 * UNIT)
            for i, j in zip(kept, kept[1:]):
                out.append((b.points[i], b.points[j], b.radii[i], b.radii[j]))
        return out

    # ---------------------------------------------------------------- twigs

    def twigs(self, budget):
        """The thin parts as polylines (points, radii), simplified as much
        as it takes to fit the triangle budget."""
        chosen = None
        for tolerance in STEPS:
            chosen = self.twigs_at(tolerance, tolerance * self.o["prune"])
            if sum(self.cost(pts, radii) for pts, radii in chosen) <= budget:
                break
        if os.environ.get("TREE_DEBUG"):
            print(f"GIANT twigs: {len(chosen)} within {tolerance:.2f} m, of {len(self.branches)} branches")
        return chosen

    def cost(self, points, radii):
        sides = 4 if radii[0] > self.o["square"] else 3
        return (len(points) - 2) * sides * 2 + sides + sides - 2

    def twigs_at(self, tolerance, shortest):
        branches = self.branches
        alive = [True] * len(branches)
        for i in range(len(branches) - 1, 0, -1):
            b = branches[i]
            if b.welded < 2 and b.length < shortest and not any(alive[c] for c in b.children):
                alive[i] = False
        out = []
        low = self.o["thin"]
        for i, b in enumerate(branches):
            start = max(b.welded - 1, 0)
            if not alive[i] or start >= len(b.points) - 1:
                continue
            forks = [branches[c].vertex - start for c in b.children if alive[c] and branches[c].vertex > start]
            kept = simplify(b.points[start:], forks, tolerance)
            pts = [b.points[start + k] for k in kept]
            radii = [max(low, b.radii[start + k]) for k in kept]
            out.append((pts, radii))
        return out

    # --------------------------------------------------------------- canopy

    def place_blobs(self, flat):
        """Every traced ellipse becomes a clump: (center, radii). Front to
        back it spans the branches seen through it in the picture and, in a
        filled canopy, the dome; a span too long for one clump is two, one
        in front and one behind."""
        o = self.o
        points = [p for b in self.branches for p in b.points]
        out = []
        for x, z, a, r, *_ in flat:
            if z < o["canopy_from"]:
                continue
            a, r = a * o["clump"], r * o["clump"] * o["clump_tall"]
            near = [p[1] for p in points if ((p[0] - x) / a) ** 2 + ((p[2] - z) / r) ** 2 < 1.0]
            depth = self.dome(x, z, a * 0.8) if o["fill"] else 0.0
            lo, hi = (min(near), max(near)) if near else (0.0, 0.0)
            if depth > 0.5 * a:
                lo, hi = min(lo, -depth), max(hi, depth)
            ry = (hi - lo) * 0.5 + a * 0.6
            if ry <= a * max(1.35, o["solid"]):
                out.append(((x, (lo + hi) * 0.5, z), (a, max(ry, a * 0.85), r)))
            else:
                out.append(((x, lo + a * 0.4, z), (a, a, r)))
                out.append(((x, hi - a * 0.4, z), (a, a, r)))

        # A clump must hold a branch, or touch one that does: none floats.
        def holds(blob, p):
            c, rad = blob
            return ((p[0] - c[0]) / rad[0]) ** 2 + ((p[1] - c[1]) / rad[1]) ** 2 + ((p[2] - c[2]) / rad[2]) ** 2 < 1.0

        def touch(m, n):
            (c, rad), (d, sad) = m, n
            return (((c[0] - d[0]) / (rad[0] + sad[0])) ** 2 + ((c[1] - d[1]) / (rad[1] + sad[1])) ** 2
                    + ((c[2] - d[2]) / (rad[2] + sad[2])) ** 2) < 0.7

        good = [any(holds(blob, p) for p in points) for blob in out]
        changed = True
        while changed:
            changed = False
            for i, blob in enumerate(out):
                if not good[i] and any(good[j] and touch(blob, other) for j, other in enumerate(out)):
                    good[i] = changed = True
        return [(Vector(c), Vector(r)) for (c, r), ok in zip(out, good) if ok]


    # ------------------------------------------------------------- all around

    def around(self):
        """The picture shows the limbs that spread to the sides; a giant
        has as many toward the back and, high up, toward the front. Each
        limb that leaves the trunk above "back_from" is copied, turned
        about the trunk to point away from the viewer, with its twigs and
        its clumps; those above "front_from" are also copied toward the
        viewer. A copy is a little smaller than its limb, and simpler."""
        o, rnd = self.o, random.Random(self.o["seed"] + 71)
        branches = self.branches
        count = len(branches)
        side = 1
        for i in sorted(branches[0].children, key=lambda i: branches[i].vertex):
            start = Vector(branches[0].points[branches[i].vertex])
            if start.z < o["back_from"]:
                continue
            members, level = [i], {i: 0}
            for j in range(i + 1, count):
                if branches[j].parent in level:
                    level[j] = level[branches[j].parent] + 1
                    members.append(j)
            if sum(branches[j].length for j in members) < o["clone_min"]:
                continue
            # The copies are seen from behind or from far: their finest twigs are left out.
            members = [j for j in members if level[j] <= o["clone_depth"]]
            tip = Vector(branches[i].points[-1]) - start
            here = math.atan2(tip.y, tip.x)
            targets = [math.radians(90.0 + side * rnd.uniform(12.0, 48.0))]
            if start.z >= o["front_from"]:
                targets.append(math.radians(-90.0 - side * rnd.uniform(12.0, 48.0)))
            side = -side
            mine = [k for k, (c, r) in enumerate(self.blobs)
                    if any(inside(Vector(p), c, r) for j in members for p in branches[j].points)]
            for target in targets:
                scale = rnd.uniform(*o["clone_scale"])
                turn = Matrix.Rotation(target - here, 3, "Z") * scale
                index = {}
                for j in members:
                    b = branches[j]
                    copy = Branch(index.get(b.parent, 0), b.vertex, [(0.0, 0.0, r * scale) for r in b.radii])
                    copy.points = [tuple(start + turn @ (Vector(p) - start)) for p in b.points]
                    copy.along = [v * scale for v in b.along]
                    copy.length = b.length * scale
                    copy.welded = 0
                    index[j] = len(branches)
                    branches[copy.parent].children.append(len(branches))
                    branches.append(copy)
                for k in mine:
                    c, r = self.blobs[k]
                    self.blobs.append((start + turn @ (c - start), r * scale))
        self.weld()

# ----------------------------------------------------------- mesh helpers

def tube(mb, points, radii, sides, mat):
    """A tapered tube along a polyline, flat at its start (inside its
    parent) and closed to a point at its end: a closed piece. `radii` has
    one value per point (the last is not used)."""
    bm = mb.bm
    pts = [Vector(p) for p in points]
    n = len(pts)
    rings, u = [], None
    for i in range(n - 1):
        d = (pts[i + 1] - pts[max(i - 1, 0)]).normalized()
        if u is not None:
            u = u - d * u.dot(d)
        if u is None or u.length < 1e-5:
            u = d.orthogonal()
        u.normalize()
        v = d.cross(u)
        rings.append([bm.verts.new(pts[i] + (u * math.cos(k * math.tau / sides) + v * math.sin(k * math.tau / sides))
                                   * radii[i]) for k in range(sides)])
    tip = bm.verts.new(pts[-1])
    bm.faces.new(list(reversed(rings[0])))
    for a, b in zip(rings, rings[1:]):
        for k in range(sides):
            j = (k + 1) % sides
            bm.faces.new((a[k], a[j], b[j], b[k]))
    last = rings[-1]
    for k in range(sides):
        bm.faces.new((last[k], last[(k + 1) % sides], tip))
    return mb._finish([v for r in rings for v in r] + [tip], mat, None)


def tube_cost(points, sides):
    """Triangles of a tube()."""
    return (len(points) - 2) * sides * 2 + sides + sides - 2


def spike(mb, base, tip, radius, mat, sides=3):
    """A closed pointed blade or needle: a pyramid from `base` to `tip`."""
    return tube(mb, [base, tip], [radius], sides, mat)


def fold_corners(center, normal, u, half_u, half_v, lift):
    v = normal.cross(u).normalized()
    up = normal * lift
    return [center + u * half_u + up, center + v * half_v, center - u * half_u + up, center - v * half_v]


def fold_keeps_side(corners, normal):
    """Whether a folded leaf keeps facing `normal` when the model is made.

    MeshBuilder.to_object recalculates every normal, and Blender turns each
    separate open piece so that it faces away from a point half way between
    the origin and the piece (it means the middle of the piece, but divides
    it by the number of faces: two). So a leaf that faces the foot of the
    tree would be turned around, and seen only from inside the canopy."""
    a, b, c, d = corners
    middle = (a + b + c + d) / 8.0
    for tri in ((a, b, c), (a, c, d)):
        n = (tri[1] - tri[0]).cross(tri[2] - tri[0]).normalized()
        if n.dot(normal) < 0:
            n = -n
        if any(n.dot((p - middle).normalized()) < 0.03 for p in corners):
            return False
    return True


def fold(mb, corners, mat):
    """A small square folded along its first diagonal: two triangles, seen
    from one side only (a leaf lying on its clump)."""
    bm = mb.bm
    a, b, c, d = (bm.verts.new(p) for p in corners)
    bm.faces.new((a, b, c))
    bm.faces.new((a, c, d))
    return mb._finish([a, b, c, d], mat, None)


def card(mb, corners, thick, mat):
    """A flat four-sided leaf seen from both sides: a tetrahedron squashed
    flat, its corners (in order around it) pushed alternately to one side
    and the other by half of `thick` (a leaf hanging in the air)."""
    bm = mb.bm
    c = [Vector(p) for p in corners]
    up = (c[2] - c[0]).cross(c[3] - c[1]).normalized() * (thick * 0.5)
    v = [bm.verts.new(p + (up if i % 2 == 0 else -up)) for i, p in enumerate(c)]
    bm.faces.new((v[0], v[1], v[2]))
    bm.faces.new((v[0], v[2], v[3]))
    bm.faces.new((v[0], v[3], v[1]))
    bm.faces.new((v[1], v[3], v[2]))
    return mb._finish(v, mat, None)


def solid(mb, points, faces, mat):
    """A closed piece from its points and faces (indices)."""
    verts = [mb.bm.verts.new(p) for p in points]
    for f in faces:
        mb.bm.faces.new([verts[i] for i in f])
    return mb._finish(verts, mat, None)


def star(mb, rnd, center, radius, height, points, mats, inner=0.55, rise=0.0, tilt=0.12, under=0.3):
    """A closed star-shaped tier of leaves: a low cone whose rim goes in and
    out, `points` times (a tier of a small conifer, a tuft of pointed
    leaves). The rim's points are `rise` above its notches (below, if
    negative); the underside is hollow, up to `under` of the height.
    `mats` are the materials of the lit and the other upper faces and of
    the underside. Returns the triangles used."""
    center = Vector(center)
    lean = Vector((rnd.uniform(-tilt, tilt), rnd.uniform(-tilt, tilt), 0.0))
    phase = rnd.uniform(0.0, math.tau)
    rim = []
    for k in range(points * 2):
        a = phase + k * math.pi / points
        out = k % 2 == 0
        r = radius * (rnd.uniform(0.85, 1.1) if out else inner * rnd.uniform(0.85, 1.15))
        p = Vector((math.cos(a) * r, math.sin(a) * r, rise if out else 0.0))
        p.z += lean.x * p.x + lean.y * p.y
        rim.append(center + p)
    top = center + Vector((0.0, 0.0, height))
    low = center + Vector((0.0, 0.0, height * under))
    bm = mb.bm
    verts = [bm.verts.new(p) for p in rim] + [bm.verts.new(top), bm.verts.new(low)]
    n = len(rim)
    for k in range(n):
        j = (k + 1) % n
        normal = (rim[j] - rim[k]).cross(top - rim[k]).normalized()
        face = bm.faces.new((verts[k], verts[j], verts[n]))
        face.material_index = mb._material_index(mats[0] if normal.dot(LIGHT) + rnd.uniform(-0.25, 0.25) > 0.45
                                                 else mats[1])
        face.smooth = False
        face = bm.faces.new((verts[j], verts[k], verts[n + 1]))
        face.material_index = mb._material_index(mats[2])
        face.smooth = False
    return 2 * n


def random_unit(rnd):
    z = rnd.uniform(-1.0, 1.0)
    a = rnd.uniform(0.0, math.tau)
    s = math.sqrt(1.0 - z * z)
    return Vector((s * math.cos(a), s * math.sin(a), z))


def sphere_points(count, rnd):
    """Evenly spread directions (a golden spiral), slightly jittered."""
    golden = math.pi * (3 - math.sqrt(5))
    phase = rnd.uniform(0.0, math.tau)
    out = []
    for i in range(count):
        z = 1 - 2 * (i + 0.5) / count
        s = math.sqrt(1 - z * z)
        a = phase + i * golden + rnd.uniform(-0.2, 0.2)
        out.append(Vector((s * math.cos(a), s * math.sin(a), z)))
    return out


def scaled(d, radii):
    return Vector((d.x * radii.x, d.y * radii.y, d.z * radii.z))


def inside(p, center, radii, k=1.0):
    q = p - center
    return (q.x / radii.x) ** 2 + (q.y / radii.y) ** 2 + (q.z / radii.z) ** 2 < k * k


def stretch(d, radii):
    """How much area the ellipsoid has around direction d, relative to the
    unit sphere."""
    return radii.x * radii.y * radii.z * math.sqrt((d.x / radii.x) ** 2 + (d.y / radii.y) ** 2
                                                   + (d.z / radii.z) ** 2)


def ellipsoid_area(radii):
    p = 1.6075
    a, b, c = radii.x ** p, radii.y ** p, radii.z ** p
    return 4 * math.pi * ((a * b + a * c + b * c) / 3.0) ** (1 / p)


# -------------------------------------------------------------------- spec

DEFAULTS = {
    "seed": 1,
    "depth": 0.8,           # Fullness of the dome front to back (1: as deep as wide).
    "slope": 1.5,           # How far out of the picture's plane a branch may lean, per meter of its length.
    "lean": (28.0, 58.0),   # Turn of a branch away from its parent, seen from above, degrees (a range).
    "spread": 76.0,         # Most a branch turns out of the picture's plane, degrees.
    "over": 1.18,           # A branch ends within a dome this many times as wide as the tree.
    "wiggle": 0.35,         # Zigzag of the twigs out of the picture's plane, per meter.
    "droop": 0.1,           # How much a twig that hangs straight down still leans.
    "bow": 1.0,             # Below 1 a branch leans early and then goes on straighter.
    "trunk_lean": 0.0,      # How much of its lean out of the picture's plane the trunk keeps.
    "back_from": 1e9,       # Limbs leaving the trunk above this height are copied toward the back.
    "front_from": 1e9,      # And those above this height, toward the front too.
    "clone_min": 2.5 * UNIT,  # Only limbs with this much length of branches are copied.
    "clone_scale": (0.8, 0.95),
    "clone_depth": 1,       # A copy has its limb's branches down to this level.
    "trunk_max": 1e9,       # The traced trunk is never thicker than this (its roots read as trunk in the picture).
    "foot": (),             # The trunk below the tracing: (x, z, radius) from the ground up.
    "skip": (),             # Traced branches left out: those ending in a circle (x, z, radius).
    "prune": 4.0,           # Twigs shorter than this many times the tolerance are dropped.
    "thick": 1.0,           # Scale of every traced radius.
    "weld": 0.3,            # Branches thicker than this are welded by the remesh.
    "voxel": 0.16,          # Remesh voxel size.
    "budget": 1500,         # Triangles of the welded surface.
    "thin": 0.1,            # Thinnest twig radius.
    "twig_scale": 1.0,      # Scale of the radius of the traced twigs (the tubes).
    "square": 0.26,         # Twigs thicker than this have four sides.
    "twigs": 2400,          # Triangles for the traced twigs, at most.
    "canopy_from": 0.0,     # Clumps traced below this height are left out.
    "more_blobs": (),       # Clumps added by hand to the traced ones: (x, z, radius along x, radius along z).
    "clump": 1.0,           # Scale of the traced clumps.
    "clump_tall": 1.0,      # Scale of their height only.
    "fill": True,           # The canopy is closed front and back as a dome (False: only where branches are).
    "leaf": 1.7,            # Side of a leaf square, at most.
    "cover": 1.1,           # Leaf area over clump area.
    "core": 0.88,           # Core radius over clump radius (0: no cores).
    "small": 1.5,           # Clumps smaller than this (largest radius) have an octahedron for a core.
    "solid": 3.0,           # A clump is stretched front to back up to this many radii; beyond, it is two.
    "hide_twigs": 0.92,     # With leaves, twigs end where they go this deep into a clump for good (0: never).
    "ruffle": 0.38,         # How much the leaves tilt away from their clump's surface.
    "under": -0.5,          # No leaves where a clump faces further down than this (normal's Z).
    "vines": 0,             # Vines hanging under the canopy (the mangrove's).
    "ring": (6.0, 8.0),     # The ring of stones, grass and flowers around the foot: its radii.
    "stones": 16,
    "tufts": 14,
    "flowers": 12,
    "stone_size": (0.55, 1.1),
    "lush": (8, 10),        # Grass tufts and flowers added to the ring in the state with leaves.
}

GROUND = {"grass": 0x5E8F2E, "stone": 0xB9B0A8, "flower": 0xF0C234}


class Giant(studies.Spec):
    """One giant in one state. `bark` and `leaves` are three colors each
    (light, middle, dark); the options are those of DEFAULTS. A subclass
    gives `traced` (the name of its tracing, or None) and shape()."""

    tone_material = None
    tones = 0.0
    far_limit = 600  # Triangles of its far version (far_tree.py).
    traced = None
    light_bark = True  # Three tones of bark; False: two (a tree that needs its materials for something else).

    def __init__(self, tree, state, bark, leaves=(), **options):
        self.name = f"{tree}_{state}"
        self.tree = tree
        self.state = state
        self.o = dict(DEFAULTS, **options)
        self.max_tris = LIMITS[state]
        self.budget = self.o["budget"]
        self.remesh_voxel = self.o["voxel"]
        names = dict(zip(("bark_light", "bark", "bark_shade"), bark))
        names.update(GROUND)
        if state == "bloom":
            names.update(zip(("leaf_1", "leaf_2", "leaf_3"), leaves))
        names.update(self.more_colors())
        self.colors = {k: common.rgb(v) for k, v in names.items()}
        self.ellipsoids = []
        self.capsules = []
        self.lines = []   # Thin branches built by hand: (points, radii, sides).
        self.blobs = []   # Clumps of leaves: (center, radii).
        self.skeleton = None
        if self.traced:
            from _giant_traced import TREES
            self.skeleton = Skeleton(TREES[self.traced], self.o)
            self.capsules += self.skeleton.capsules()
            self.blobs += self.skeleton.blobs
        self.shape()

    # ------------------------------------------------------ for subclasses

    def more_colors(self):
        """Materials besides the bark's, the leaves' and the ground's."""
        return {}

    def shape(self):
        """Fills capsules, ellipsoids, lines and blobs."""

    def both(self, mb):
        """Pieces built directly in both states."""

    def foliage(self, mb, budget):
        """What only the state with leaves has, in `budget` triangles."""
        self.clumps(mb, budget)

    def limb(self, points, radii, sides=None):
        """A branch given by hand: its thick start is welded, its thin end
        is a tube."""
        n = 0
        while n < len(radii) and radii[n] >= self.o["weld"]:
            n += 1
        if n >= 2:
            for i in range(n - 1):
                self.capsules.append((tuple(points[i]), tuple(points[i + 1]), radii[i], radii[i + 1]))
            points, radii = points[n - 1:], radii[n - 1:]
        if len(points) >= 2:
            self.lines.append(([Vector(p) for p in points], list(radii), sides))

    def roots(self, count, path, seed, sway=0.25, wobble=0.12, center=(0.0, 0.0), phase=0.0):
        """Roots all around the foot. `path` is one root seen from the
        side, from the trunk to its tip: (distance from the axis, height,
        radius). Each root goes its own way: `sway` (of the angle between
        two roots) and `wobble` (sideways, of its distance). Returns the
        directions of the roots."""
        rnd = random.Random(seed)
        out = []
        for i in range(count):
            a = phase + (i + rnd.uniform(-sway, sway)) * math.tau / count
            d = Vector((math.cos(a), math.sin(a), 0.0))
            side = Vector((-d.y, d.x, 0.0))
            reach = rnd.uniform(0.88, 1.1)
            pts = []
            for k, (dist, z, r) in enumerate(path):
                grow = 1.0 + (reach - 1.0) * k / (len(path) - 1)
                off = side * (rnd.uniform(-wobble, wobble) * dist if k else 0.0)
                pts.append((Vector((center[0], center[1], z)) + d * dist * grow + off, r))
            for (p, r), (q, t) in zip(pts, pts[1:]):
                self.capsules.append((tuple(p), tuple(q), r, t))
            out.append(d)
        return out

    def axis(self, z):
        """Where the trunk's center line is at a height (a traced tree)."""
        pts = self.skeleton.branches[0].points
        for a, b in zip(pts, pts[1:]):
            if a[2] <= z <= b[2] and b[2] > a[2]:
                t = (z - a[2]) / (b[2] - a[2])
                return Vector((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, z))
        return Vector((pts[0][0], pts[0][1], z))

    def knobs(self, count, z0, z1, size, seed, axis=None, out=0.45):
        """Bumps all over the trunk between two heights, so that its bark
        is as knobbly as in the pictures (and keeps small facets where it
        would otherwise be one smooth cone). Each is an ellipsoid of about
        `size` (a range) sunk into the surface, `out` of its radius
        showing."""
        rnd = random.Random(seed)
        axis = axis or self.axis
        golden = math.pi * (3 - math.sqrt(5))
        found = []
        for i in range(count):
            z = z0 + (z1 - z0) * (i + rnd.random()) / count
            a = i * golden + rnd.uniform(-0.3, 0.3)
            d = Vector((math.cos(a), math.sin(a), 0.0))
            start = axis(z)
            t = 0.0
            while studies.sdf(self, start + d * t) < 0.0 and t < 40.0:
                t += 0.2
            r = rnd.uniform(*size)
            c = start + d * (t - r * (1.0 - out))
            found.append((tuple(c), (r, r, r * rnd.uniform(1.1, 1.7))))
        self.ellipsoids += found

    # ------------------------------------------------------------- painting

    def paint(self, c, n):
        v = n.dot(LIGHT) + (noise(c) - 0.5) * 1.3
        return "bark_light" if v > 0.6 and self.light_bark else ("bark_shade" if v < -0.22 else "bark")

    def bark_tone(self, rnd):
        r = rnd.random()
        return "bark" if r < 0.6 else ("bark_shade" if r < 0.85 or not self.light_bark else "bark_light")

    # -------------------------------------------------------------- details

    def details(self, mb):
        rnd = random.Random(self.o["seed"] + 23)
        drop_crumbs(mb)
        welded = studies.triangles(mb)
        self.ground(mb)
        ground = studies.triangles(mb) - welded
        # The same twigs in both states: what the bare tree affords.
        lines = [(pts, radii, sides or (4 if radii[0] > self.o["square"] else 3)) for pts, radii, sides in self.lines]
        if self.skeleton:
            used = sum(tube_cost(pts, sides) for pts, radii, sides in lines)
            budget = min(self.o["twigs"], LIMITS["bare"] - welded - ground - used - self.reserve())
            for pts, radii in self.skeleton.twigs(budget):
                lines.append((pts, [r * self.o["twig_scale"] for r in radii], 4 if radii[0] > self.o["square"] else 3))
        hide = self.state == "bloom" and self.o["core"] and self.o["hide_twigs"]
        for points, radii, sides in lines:
            mat = self.bark_tone(rnd)
            if hide:
                # What a clump swallows for good is not seen under its
                # leaves: the twig ends just inside it (or is left out, if
                # it is all inside).
                keep = len(points)
                while keep and any(inside(Vector(points[keep - 1]), c, r, self.o["hide_twigs"])
                                   for c, r in self.blobs):
                    keep -= 1
                if keep == 0:
                    continue
                points, radii = points[:keep + 1], radii[:keep + 1]
            tube(mb, points, radii, sides, mat)
        twigs = studies.triangles(mb) - welded - ground
        self.both(mb)
        both = studies.triangles(mb) - welded - ground - twigs
        if self.state == "bloom":
            self.foliage(mb, self.max_tris - studies.triangles(mb) - 4)
        total = studies.triangles(mb)
        if os.environ.get("TREE_DEBUG") or total > self.max_tris:
            print(f"GIANT {self.name}: welded {welded}, ground {ground}, twigs {twigs}, both states {both}, "
                  f"foliage {total - welded - ground - twigs - both} of {len(self.blobs)} blobs, total {total}"
                  + ("  OVER THE LIMIT" if total > self.max_tris else ""))

    def reserve(self):
        """Triangles the bare state keeps for both()."""
        return 0

    def tone(self, rnd, normal):
        """Material of a leaf, by the light."""
        v = normal.dot(LIGHT) + rnd.uniform(-0.5, 0.5)
        return "leaf_1" if v > 0.6 else ("leaf_2" if v > 0.08 else "leaf_3")

    def clumps(self, mb, budget, blobs=None):
        """Cores and leaves of the canopy, in `budget` triangles."""
        o = self.o
        rnd = random.Random(o["seed"] + 37)
        blobs = self.blobs if blobs is None else blobs
        if not blobs or budget < 40:
            return

        def hidden(p, own, k):
            return any(i != own and inside(p, c, r, k) for i, (c, r) in enumerate(blobs))

        bm = mb.bm
        used = 0
        if o["core"]:
            for own, (c, r) in enumerate(blobs):
                rot = Matrix.Rotation(rnd.uniform(0.0, math.tau), 3, random_unit(rnd))
                small = max(r) < o["small"]
                pts = [c + scaled(rot @ Vector(p).normalized(), r) * (o["core"] * rnd.uniform(0.92, 1.06))
                       for p in (OCTA if small else ICO)]
                faces = [f for f in (OCTA_FACES if small else ICO_FACES)
                         if not hidden((pts[f[0]] + pts[f[1]] + pts[f[2]]) / 3.0, own, o["core"] * 0.9)]
                if not faces:
                    continue
                verts = {i: bm.verts.new(pts[i]) for i in sorted({i for f in faces for i in f})}
                for f in faces:
                    face = bm.faces.new([verts[i] for i in f])
                    face.material_index = mb._material_index("leaf_3")  # The inside of the canopy is in the shade.
                    face.smooth = False
                used += len(faces)
        # Leaves: spread evenly over what each clump shows of itself.
        probes = 60
        shown, weight = [], []
        for own, (c, r) in enumerate(blobs):
            total = seen = top = 0.0
            for d in sphere_points(probes, rnd):
                w = stretch(d, r)
                total += w
                top = max(top, w)
                if Vector((d.x / r.x, d.y / r.y, d.z / r.z)).normalized().z < o["under"]:
                    continue
                if not hidden(c + scaled(d, r) * 1.03, own, 0.97):
                    seen += w
            shown.append(seen / total)
            weight.append((total / probes, top))
        areas = [ellipsoid_area(r) * f for (c, r), f in zip(blobs, shown)]
        area = sum(areas)
        left = budget - used
        count = left / 2.3  # A leaf is two triangles; the two-sided ones, four.
        if count < 1 or not area:
            return
        size = min(o["leaf"], math.sqrt(o["cover"] * area / count))
        # Candidate leaves of every clump, more than fit, in no order; each
        # clump then takes its share of the triangles, and what some cannot
        # use goes to the others.
        candidates = []
        for own, (c, r) in enumerate(blobs):
            found = []
            if shown[own]:
                mean, top = weight[own]
                want = min(count, o["cover"] * area / (size * size)) * areas[own] / area
                # All around; kept where the clump is seen, and thinned so
                # that the stretched sides are as dense as the ends.
                for d in sphere_points(max(8, int(round(1.5 * want / shown[own] * top / mean))), rnd):
                    if rnd.random() > stretch(d, r) / top:
                        continue
                    p = c + scaled(d, r) * rnd.uniform(0.97, 1.13)
                    normal = Vector((d.x / r.x, d.y / r.y, d.z / r.z)).normalized()
                    if hidden(p, own, 0.97) or normal.z < o["under"]:
                        continue
                    normal = (normal + random_unit(rnd) * o["ruffle"]).normalized()
                    u = normal.cross(random_unit(rnd)).normalized()
                    half = size * rnd.uniform(0.82, 1.12) * 0.7071
                    corners = fold_corners(p, normal, u, half, half * rnd.uniform(0.8, 1.2),
                                           size * rnd.uniform(0.06, 0.18))
                    found.append((corners, fold_keeps_side(corners, normal), self.tone(rnd, normal)))
                rnd.shuffle(found)
            candidates.append(found)
        taken = [0] * len(blobs)
        spent = 0

        def take(own, allowance):
            """Builds leaves of a clump while they fit in `allowance` triangles."""
            nonlocal spent
            cost = 0
            while taken[own] < len(candidates[own]):
                corners, keeps, mat = candidates[own][taken[own]]
                tris = 2 if keeps else 4
                if cost + tris > allowance or spent + tris > left:
                    break
                if keeps:
                    fold(mb, corners, mat)
                else:
                    card(mb, corners, 0.03 * UNIT, mat)  # Blender would turn a fold around: two-sided.
                taken[own] += 1
                cost += tris
                spent += tris

        for own in range(len(blobs)):
            take(own, max(8.0, left * areas[own] / area))
        for _ in range(40):  # What is left over, a leaf at a time all around.
            before = spent
            for own in range(len(blobs)):
                take(own, 4)
            if spent == before:
                break

    def ground(self, mb):
        """The ring around the foot: stones, grass tufts and small flowers."""
        o = self.o
        rnd = random.Random(o["seed"] + 53)
        r_in, r_out = o["ring"]
        kinds = ["stone"] * o["stones"] + ["tuft"] * o["tufts"] + ["flower"] * o["flowers"]
        slots = len(kinds)
        order = list(range(slots))
        rnd.shuffle(order)
        for slot, kind in zip(order, kinds):
            a = (slot + rnd.uniform(-0.3, 0.3)) * math.tau / slots
            c = Vector((math.cos(a), math.sin(a), 0.0)) * rnd.uniform(r_in, r_out)
            if kind == "tuft":
                for i in range(3):
                    b = c + Vector((rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3), -0.05))
                    tip = b + Vector((rnd.uniform(-0.45, 0.45), rnd.uniform(-0.45, 0.45), rnd.uniform(0.8, 1.5)))
                    spike(mb, b, tip, rnd.uniform(0.16, 0.24), "grass")
            elif kind == "flower":
                # A low bud: a small pyramid.
                size = rnd.uniform(0.22, 0.34)
                spike(mb, c + Vector((0, 0, -0.03)), c + Vector((rnd.uniform(-0.1, 0.1), rnd.uniform(-0.1, 0.1),
                                                                 size * 1.3)), size, "flower")
            else:
                stone(mb, rnd, c, rnd.uniform(*o["stone_size"]))
        if self.state != "bloom":
            return
        # With leaves, the ring is lusher: more grass and flowers between the same stones.
        rnd = random.Random(o["seed"] + 59)
        tufts, flowers = o["lush"]
        for k in range(tufts + flowers):
            a = rnd.uniform(0.0, math.tau)
            c = Vector((math.cos(a), math.sin(a), 0.0)) * rnd.uniform(r_in - 0.4, r_out + 0.3)
            if k < tufts:
                for i in range(3):
                    b = c + Vector((rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3), -0.05))
                    tip = b + Vector((rnd.uniform(-0.45, 0.45), rnd.uniform(-0.45, 0.45), rnd.uniform(0.8, 1.6)))
                    spike(mb, b, tip, rnd.uniform(0.16, 0.24), "grass")
            else:
                size = rnd.uniform(0.24, 0.38)
                spike(mb, c + Vector((0, 0, -0.03)), c + Vector((rnd.uniform(-0.1, 0.1), rnd.uniform(-0.1, 0.1),
                                                                 size * 1.3)), size, "flower")


def drop_crumbs(mb):
    """Deletes the stray pieces of one or two triangles that the remesh
    sometimes leaves beside the welded surface."""
    bm = mb.bm
    seen, crumbs = set(), []
    for f in bm.faces:
        if f in seen:
            continue
        island, stack = [], [f]
        seen.add(f)
        while stack:
            g = stack.pop()
            island.append(g)
            for v in g.verts:
                for h in v.link_faces:
                    if h not in seen:
                        seen.add(h)
                        stack.append(h)
        if len(island) < 4:
            crumbs += island
    if crumbs:
        bmesh.ops.delete(bm, geom=crumbs, context="FACES")


def stone(mb, rnd, c, size):
    """A faceted stone lying on the ground: five sides and a tilted top."""
    phase = rnd.uniform(0.0, math.tau)
    stretch_x = rnd.uniform(0.8, 1.35)
    low = [c + Vector((math.cos(phase + k * math.tau / 5) * size * rnd.uniform(0.85, 1.2) * stretch_x,
                       math.sin(phase + k * math.tau / 5) * size * rnd.uniform(0.85, 1.2), -0.06))
           for k in range(5)]
    top = [c + Vector((math.cos(phase + 0.4 + k * math.tau / 5) * size * 0.6 * stretch_x,
                       math.sin(phase + 0.4 + k * math.tau / 5) * size * 0.6, size * rnd.uniform(0.55, 1.0)))
           for k in range(5)]
    faces = [(k, (k + 1) % 5, 5 + (k + 1) % 5, 5 + k) for k in range(5)] + [(5, 6, 7, 8, 9), (4, 3, 2, 1, 0)]
    return solid(mb, low + top, faces, "stone")


def variants(cls, tree, bark, leaves=(), **options):
    """The two states of one giant."""
    return [cls(tree, state, bark, leaves, **options) for state in STATES]
