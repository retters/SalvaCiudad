"""Shared generator of the low-poly trees: one tree, three states.

A tree is defined once, by what _trace.py read from the reference pictures
(_traced.py: its branches as flat polylines with their thickness, and the
clumps of its canopy as ellipses) plus a few options. Its three states,
"bloom", "autumn" and "bare", are built from that same definition, so the
trunk and every branch and twig are identical in the three; only, with
leaves, the ends of twigs that are buried inside a clump are not built.

How the flat tracing becomes a tree:

  * Depth. Seen from the front the model is the picture: X and Z are the
    traced ones. Every branch gets its Y by turning away from its parent,
    seen from above, to one side or the other in turn; and a branch near
    the middle of the picture is one that comes forward or goes back, up
    to the surface of a dome whose width at every height is the outline
    of the tree.
  * Trunk and thick branches: tapering capsules welded by the remesh and
    collapse of studies.build_final into one faceted surface.
  * Thin branches and twigs: three- or four-sided tapered tubes ending in a
    point, built directly. They are simplified and the shortest are dropped
    until the bare tree fits its triangle limit.
  * Foliage: every traced clump is a dark faceted core (a rough icosahedron
    that hides what is behind) covered with small folded squares in three
    tones, as many as the triangle limit allows. Hanging twigs (weeping
    trees) carry flat four-sided leaves along them instead. In autumn every
    leaf takes the color the autumn picture has at its place.
  * Around the foot: grass tufts, stones and, for some, fallen petals.

The trees of the second set of pictures (_traced2.py) add, as options:
other bark colors, a pale lower trunk and dark marks across it; flowers or
rosettes of sword leaves at the twig tips instead of clumps; fruit or
flowers on the clumps; a share of leaves of a fourth color; and, for the
weeping ones, strands hung all around from the limbs (the picture's own
hanging twigs cross each other too much to be traced). The trees that are
not traced at all (pine, cypress, palm) are in _built.py.

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

from mathutils import Matrix, Vector

import common
import studies
from _traced import TREES

try:  # The second set of pictures (see _trace.py).
    from _traced2 import TREES as _SECOND
    TREES.update(_SECOND)
except ImportError:
    pass

STATES = ("bloom", "autumn", "bare")
LIMITS = {"bloom": 2500, "autumn": 2500, "bare": 1500}
LIGHT = Vector((-0.35, -0.5, 0.8)).normalized()  # Where the pictures are lit from.
# Twig simplification tolerances, from fine to coarse.
STEPS = [0.025 * 1.1 ** i for i in range(30)]
OCTA = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
OCTA_FACES = [(0, 2, 4), (2, 1, 4), (1, 3, 4), (3, 0, 4), (2, 0, 5), (1, 2, 5), (3, 1, 5), (0, 3, 5)]
ICO = [(-1, 1.618, 0), (1, 1.618, 0), (-1, -1.618, 0), (1, -1.618, 0), (0, -1, 1.618), (0, 1, 1.618),
       (0, -1, -1.618), (0, 1, -1.618), (1.618, 0, -1), (1.618, 0, 1), (-1.618, 0, -1), (-1.618, 0, 1)]
ICO_FACES = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2),
             (10, 7, 6), (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11),
             (6, 2, 10), (8, 6, 7), (9, 8, 1)]


# ------------------------------------------------------------ flat helpers

def dist3(a, b):
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2)


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
    """The tree's branches placed in space, and its canopy."""

    def __init__(self, name, o):
        data = TREES[name]
        self.o = o
        self.rnd = random.Random(o["seed"])
        self.outline = data["outline"]
        self.autumn = data["autumn"]
        traced = data["branches"]
        if o["curtain"]:
            traced = self.without_hanging(traced)
        self.branches = [Branch(p, v, pts) for p, v, pts in traced]
        self.foot()
        for i, b in enumerate(self.branches):
            if b.parent >= 0:
                self.branches[b.parent].children.append(i)
        self.place()
        if o["curtain"]:
            self.curtain()
        self.weld()
        self.blobs = self.place_blobs(data["blobs"])

    # -------------------------------------------------------------- curtain

    def without_hanging(self, traced):
        """The traced branches without their hanging twigs (a weeping tree's
        are too many, and cross each other in the picture): the limbs stay,
        up to where they turn down for good, and curtain() hangs new strands
        from them all around."""
        limb = self.o["curtain"]["limb"]
        out, index = [], {}
        cut = {}  # Kept branch: its last vertex.
        for i, (parent, vertex, pts) in enumerate(traced):
            if parent >= 0 and (parent not in index or vertex > cut[parent]):
                continue
            if i and pts[0][2] < limb and pts[-1][1] < pts[0][1] - 0.4:
                continue  # A hanging twig.
            apex = max(range(len(pts)), key=lambda k: pts[k][1])
            last = len(pts) - 1
            for k in range(apex + 1, len(pts)):
                if pts[k][2] < limb and pts[k][1] < pts[apex][1] - 0.35:
                    last = k
                    break
            if last < 1:
                continue
            index[i] = len(out)
            cut[i] = last
            out.append((index.get(parent, -1), vertex, pts[:last + 1]))
        return out

    def curtain(self):
        """Hangs strands all around a weeping tree: each starts on the
        nearest branch, arches to a place on the crown's dome and falls
        from there."""
        c = self.o["curtain"]
        rnd = random.Random(self.o["seed"] + 5)
        half = [(z, (hi - lo) * 0.5, (hi + lo) * 0.5) for z, lo, hi in self.outline]
        widest = max(h for z, h, m in half)
        crown = [(z, h, m) for z, h, m in half if z > c["from"]]
        places = [(i, k, Vector(p)) for i, b in enumerate(self.branches) for k, p in enumerate(b.points)
                  if b.radii[k] < 0.2 and p[2] > c["from"]]
        for j in range(c["count"]):
            angle = (j + rnd.uniform(-0.35, 0.35)) * math.tau / c["count"]
            rho = math.sqrt(rnd.uniform(c["inner"] ** 2, 1.0))
            # The highest place of the dome that far out.
            z, h, m = max((t for t in crown if t[1] >= rho * widest * 0.97), default=crown[0])
            radial = Vector((math.cos(angle), math.sin(angle) * self.o["depth"], 0.0))
            top = Vector((m, 0.0, z - 0.1)) + radial * (rho * widest)
            i, k, root = min(places, key=lambda q: (q[2] - top).length)
            reach = (top - root).length
            if reach > c["reach"]:
                top = root + (top - root) * (c["reach"] / reach)
            radial = Vector((top.x, top.y, 0.0))
            radial = radial.normalized() if radial.length > 0.2 else Vector((math.cos(angle), math.sin(angle), 0.0))
            end = rnd.uniform(*c["bottom"])
            end = min(end, top.z - c["least"])
            knee = top + radial * 0.25 + Vector((0.0, 0.0, -0.45))
            tip = Vector((knee.x, knee.y, end)) + radial * rnd.uniform(0.1, 0.45)
            r = min(c["radius"], self.branches[i].radii[k])
            strand = Branch(i, k, [(q.x, q.z, r * f) for q, f in zip((root, top, knee, tip), (1.0, 0.85, 0.7, 0.45))])
            strand.points = [tuple(q) for q in (root, top, knee, tip)]
            self.branches[i].children.append(len(self.branches))
            self.branches.append(strand)

    # ---------------------------------------------------------------- trunk

    def foot(self):
        """The tracing starts above the grass: the trunk goes on down to
        the origin, widening. Its thickness never grows on the way up by
        more than a fork explains."""
        trunk = self.branches[0]
        (x, z), r = trunk.flat[0], trunk.radii[0]
        extra = [(0.0, -0.06, r * self.o["flare"]), (x * 0.3, 0.24, r * (1.0 + (self.o["flare"] - 1.0) * 0.45))]
        limit = 1e9
        radii = []
        for v in trunk.radii:
            limit = min(limit * 1.03, v)
            radii.append(limit)
        flat = [(x, z, r) for x, z, r in extra] + [(p[0], p[1], r) for p, r in zip(trunk.flat, radii)]
        if self.o["straight"]:
            # A very thick trunk's traced center line wanders: a straight
            # line instead, up to that height.
            top = next((i for i, p in enumerate(flat) if p[1] > self.o["straight"]), len(flat) - 1)
            flat = [(flat[top][0] * max(0.0, z) / flat[top][1], z, r) if i < top else (x, z, r)
                    for i, (x, z, r) in enumerate(flat)]
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
            w = max(0.0, 1.0 - abs(oz - z) / 0.9)
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
            kept = simplify(b.points[:b.welded], forks, 0.04)
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
        """Every traced ellipse becomes a clump: (center, radii, autumn
        color). Front to back it spans the branches seen through it in the
        picture and, in a filled canopy, the dome; a span too long for one
        clump is two, one in front and one behind."""
        o = self.o
        points = [p for b in self.branches for p in b.points]
        out = []
        for x, z, a, r, color in flat:
            if z < o["canopy_from"]:
                continue
            a, r = a * o["clump"], r * o["clump"]
            near = [p[1] for p in points if ((p[0] - x) / a) ** 2 + ((p[2] - z) / r) ** 2 < 1.0]
            depth = self.dome(x, z, a * 0.8) if o["fill"] else 0.0
            lo, hi = (min(near), max(near)) if near else (0.0, 0.0)
            if depth > 0.5 * a:
                lo, hi = min(lo, -depth), max(hi, depth)
            ry = (hi - lo) * 0.5 + a * 0.6
            if ry <= a * max(1.35, o["solid"]):
                out.append(((x, (lo + hi) * 0.5, z), (a, max(ry, a * 0.85), r), color))
            else:
                out.append(((x, lo + a * 0.4, z), (a, a, r), color))
                out.append(((x, hi - a * 0.4, z), (a, a, r), color))
        if o["show_trunk"]:
            # The clumps in front of the trunk go behind it, so that it is
            # seen from the front all the way up, as in the picture.
            trunk = self.branches[0].points
            moved = []
            for (x, y, z), (a, ry, r), color in out:
                k = max((j for j in range(len(trunk)) if trunk[j][2] <= z), default=None)
                if k is not None and k < len(trunk) - 1:
                    f = (z - trunk[k][2]) / ((trunk[k + 1][2] - trunk[k][2]) or 1.0)
                    tx = trunk[k][0] + (trunk[k + 1][0] - trunk[k][0]) * f
                    if abs(x - tx) < a * 0.8 and y - ry < 0.3:
                        y = ry + 0.3
                moved.append(((x, y, z), (a, ry, r), color))
            out = moved
        # A clump must hold a branch, or touch one that does: none floats.
        def holds(blob, p):
            c, rad, _ = blob
            return ((p[0] - c[0]) / rad[0]) ** 2 + ((p[1] - c[1]) / rad[1]) ** 2 + ((p[2] - c[2]) / rad[2]) ** 2 < 1.0

        def touch(m, n):
            (c, rad, _), (d, sad, _) = m, n
            return (((c[0] - d[0]) / (rad[0] + sad[0])) ** 2 + ((c[1] - d[1]) / (rad[1] + sad[1])) ** 2
                    + ((c[2] - d[2]) / (rad[2] + sad[2])) ** 2) < 0.7

        good = [any(holds(blob, p) for p in points) for blob in out]
        changed = True
        while changed:
            changed = False
            for i, blob in enumerate(out):
                if not good[i] and any(good[j] and touch(blob, other) for j, other in enumerate(out)):
                    good[i] = changed = True
        return [blob for blob, ok in zip(out, good) if ok]


# ----------------------------------------------------------- mesh helpers

def tube(mb, points, radii, sides, mat, split=False):
    """A tapered tube along a polyline, flat at its start (inside its
    parent) and closed to a point at its end: a closed piece. With `split`,
    a tube that turns back on itself is built as two, one up to the turn
    and one from it: in one piece its rings would cross, and Blender might
    turn the whole of it inside out when the model is made."""
    bm = mb.bm
    pts = [Vector(p) for p in points]
    n = len(pts)
    if split:
        for i in range(1, n - 1):
            if (pts[i] - pts[i - 1]).dot(pts[i + 1] - pts[i]) < 0.0:
                return (tube(mb, pts[:i + 1], radii[:i], sides, mat)
                        + tube(mb, pts[i:], radii[i:], sides, mat, True))
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


def ground(mb, rnd, r0, tufts, stones):
    """Grass tufts and stones around the foot of a trunk of radius r0."""
    slots = tufts + stones
    order = list(range(slots))
    rnd.shuffle(order)
    bm = mb.bm
    for slot, kind in zip(order, ["tuft"] * tufts + ["stone"] * stones):
        a = (slot + rnd.uniform(-0.3, 0.3)) * math.tau / slots
        c = Vector((math.cos(a), math.sin(a), 0.0)) * (r0 * rnd.uniform(1.15, 1.7))
        if kind == "tuft":
            for i in range(3):
                b = c + Vector((rnd.uniform(-0.09, 0.09), rnd.uniform(-0.09, 0.09), -0.02))
                tip = b + Vector((rnd.uniform(-0.16, 0.16), rnd.uniform(-0.16, 0.16), rnd.uniform(0.28, 0.5)))
                tube(mb, [b, tip], [rnd.uniform(0.06, 0.085)], 3, "grass")
        else:
            size = rnd.uniform(0.14, 0.22)
            phase = rnd.uniform(0.0, math.tau)
            low = [bm.verts.new(c + Vector((math.cos(phase + k * math.tau / 4) * size * rnd.uniform(0.85, 1.2),
                                            math.sin(phase + k * math.tau / 4) * size * rnd.uniform(0.85, 1.2),
                                            -0.02))) for k in range(4)]
            top = [bm.verts.new(c + Vector((math.cos(phase + 0.5 + k * math.tau / 4) * size * 0.55,
                                            math.sin(phase + 0.5 + k * math.tau / 4) * size * 0.55,
                                            size * rnd.uniform(0.6, 1.0)))) for k in range(4)]
            for k in range(4):
                j = (k + 1) % 4
                bm.faces.new((low[k], low[j], top[j], top[k]))
            bm.faces.new(top)
            bm.faces.new(list(reversed(low)))
            mb._finish(low + top, "stone", None)


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


def nearest(color, palette):
    def parts(c):
        return (c >> 16) & 255, (c >> 8) & 255, c & 255
    r, g, b = parts(color)
    return min(range(len(palette)), key=lambda i: sum((p - q) ** 2 for p, q in zip(parts(palette[i]), (r, g, b))))


# -------------------------------------------------------------------- spec

DEFAULTS = {
    "seed": 1,
    "depth": 0.8,           # Fullness of the dome front to back (1: as deep as wide).
    "slope": 1.5,           # How far out of the picture's plane a branch may lean, per meter of its length.
    "lean": (20.0, 44.0),   # Turn of a branch away from its parent, seen from above, degrees (a range).
    "spread": 68.0,         # Most a branch turns out of the picture's plane, degrees.
    "over": 1.18,           # A branch ends within a dome this many times as wide as the tree.
    "wiggle": 0.35,         # Zigzag of the twigs out of the picture's plane, per meter.
    "droop": 0.1,           # How much a twig that hangs straight down still leans.
    "bow": 1.0,             # Below 1 a branch leans early and then goes on straighter.
    "flare": 1.6,           # How much the trunk widens at the ground.
    "prune": 4.0,           # Twigs shorter than this many times the tolerance are dropped.
    "thick": 1.0,           # Scale of every radius.
    "weld": 0.075,          # Branches thicker than this are welded by the remesh.
    "voxel": 0.045,         # Remesh voxel size.
    "budget": 300,          # Triangles of the welded trunk.
    "thin": 0.028,          # Thinnest twig radius.
    "square": 0.065,       # Twigs thicker than this have four sides.
    "canopy_from": 0.0,     # Clumps traced below this height are left out.
    "clump": 1.0,           # Scale of the traced clumps.
    "fill": True,           # The canopy is closed front and back as a dome (False: only where branches are).
    "leaf": 0.5,            # Side of a leaf square, at most.
    "cover": 1.1,           # Leaf area over clump area.
    "core": 0.88,           # Core radius over clump radius (0: no cores).
    "small": 0.6,           # Clumps smaller than this (largest radius) have an octahedron for a core.
    "solid": 3.0,           # A clump is stretched front to back up to this many radii; beyond, it is two.
    "hide_twigs": 0.92,     # With leaves, twigs end where they go this deep into a clump for good (0: never).
    "ruffle": 0.38,         # How much the leaves tilt away from their clump's surface.
    "under": -0.5,          # No leaves where a clump faces further down than this (normal's Z).
    "hang": 0.0,            # Share of the foliage triangles for leaves hanging along the twigs.
    "hang_slope": -0.3,     # A twig hangs when its direction's Z is below this.
    "hang_leaf": (0.2, 0.3),  # Half width and half length of a hanging leaf.
    "hang_limb": 0.0,       # Welded branches thinner than this carry hanging leaves too.
    "autumn_keep": 0.92,    # Share of the leaves left in autumn.
    "tufts": 5,
    "stones": 4,
    "petals": 0,            # Fallen petals or leaves on the ground.
    # What the trees of the second set of pictures need.
    "bark": None,           # (lit color, shade color) of the bark; None: the usual browns.
    "pale": None,           # (height, color): the trunk below it is paler (a baobab's bottle).
    "roots": True,          # Root stubs around the foot.
    "hairpins": False,      # Twigs that turn back on themselves are built in two pieces (see tube).
    "straight": 0.0,        # The trunk is straight up to this height (a baobab's bottle).
    "show_trunk": False,    # No clump in front of the trunk (a birch's white trunk shows all the way up).
    "marks": 0,             # Dark marks across the trunk (a birch), of the color "mark" in `colors`.
    "colors": None,         # More materials: {name: color}.
    "foliage": "clumps",    # "clumps" of leaf squares; "flowers" at the twig tips (a magnolia);
                            # "rosettes" of sword leaves at the branch ends (a dragon tree).
    "flower": (0.55, 0.26),  # Height and radius of a flower.
    "greens": 0,            # With flowers: so many small leaves of the color "leaf_4" among them.
    "rosette": (16, 1.0, 0.12, 1.0),  # Leaves in a rosette, their length and half width, and how far apart.
    "accents": None,        # ("fruit" or "flower", count, size, color): pieces of another color on the clumps.
    "sprinkle": None,       # (color, share): in bloom, that share of the leaves are of that fourth color.
    "curtain": None,        # A weeping tree's strands (see Skeleton.curtain): {"count", "bottom": (low, high),
                            # "from", "inner", "reach", "least", "radius", "limb"}.
    "hang_shape": "card",   # Hanging leaves: "card" (blunt) or "diamond" (pointed at both ends).
    "hang_taper": 0.0,      # How much narrower the hanging leaves are at the end of their twig (a raceme).
}
CURTAIN = {"count": 60, "bottom": (0.8, 2.0), "from": 2.5, "inner": 0.3, "reach": 1.8, "least": 0.8,
           "radius": 0.034, "limb": 0.07}

BARK = {"bark": 0x8C5E33, "bark_shade": 0x62401F}
GROUND = {"grass": 0x4F9A32, "stone": 0xC9BCAD}


class Tree(studies.Spec):
    """One tree in one state. `leaves` maps "bloom" and "autumn" to three
    colors (light, mid, dark for bloom; any three for autumn); the options
    are those of DEFAULTS."""

    tone_material = None
    tones = 0.0
    far_limit = 300  # Triangles of its far version (far_tree.py).

    def __init__(self, tree, state, leaves, **options):
        self.name = f"{tree}_{state}"
        self.tree = tree
        self.state = state
        self.o = dict(DEFAULTS, **options)
        if self.o["curtain"]:
            self.o["curtain"] = dict(CURTAIN, **self.o["curtain"])
        self.max_tris = LIMITS[state]
        self.budget = self.o["budget"]
        self.remesh_voxel = self.o["voxel"]
        self.palette = leaves.get(state, ())
        bark = BARK
        if self.o["bark"]:
            bark = {"bark": self.o["bark"][0], "bark_shade": self.o["bark"][1]}
        self.colors = {k: common.rgb(v) for k, v in {**bark, **GROUND}.items()}
        for i, c in enumerate(self.palette):
            self.colors[f"leaf_{i + 1}"] = common.rgb(c)
        if not self.o["stones"]:
            del self.colors["stone"]
        more = dict(self.o["colors"] or {})
        if self.o["pale"]:
            more["bark_pale"] = self.o["pale"][1]
        if self.o["accents"]:
            more["accent"] = self.o["accents"][3]
        if state == "bloom" and self.o["sprinkle"]:
            more["leaf_4"] = self.o["sprinkle"][0]
        for k, v in more.items():
            if state != "bare" or not k.startswith(("leaf", "accent")):
                self.colors[k] = common.rgb(v)
        self.skeleton = Skeleton(tree, self.o)
        self.tones_seen = {}
        self.ellipsoids = []
        self.capsules = self.skeleton.capsules()
        # Roots: short stubs spreading from the foot.
        rnd = random.Random(self.o["seed"] + 11)
        r = self.skeleton.branches[0].radii[2]
        for i in range(5 if self.o["roots"] else 0):
            a = (i + rnd.uniform(-0.25, 0.25)) * math.tau / 5
            d = (math.cos(a), math.sin(a))
            reach = r * rnd.uniform(1.25, 1.7)
            self.capsules.append(((d[0] * r * 0.3, d[1] * r * 0.3, 0.5), (d[0] * reach, d[1] * reach, -0.03),
                                  r * 0.55, r * 0.3))

    def paint(self, c, n):
        h = math.sin(c.x * 12.9898 + c.y * 78.233 + c.z * 37.719) * 43758.5453
        h -= math.floor(h)
        shade = n.dot(LIGHT) + (h - 0.5) * 0.9 < -0.12
        if self.o["pale"] and c.z < self.o["pale"][0]:
            # Its shade is the lit color of the branches; more facets of it, for a bottle is one big surface.
            return "bark" if n.dot(LIGHT) + (h - 0.5) * 1.5 < 0.3 else "bark_pale"
        return "bark_shade" if shade else "bark"

    # -------------------------------------------------------------- details

    def details(self, mb):
        rnd = random.Random(self.o["seed"] + 23)
        welded = studies.triangles(mb)
        base = self.o["tufts"] * 12 + self.o["stones"] * 12
        twigs = self.skeleton.twigs(LIMITS["bare"] - welded - base - 4)
        hide = self.state != "bare" and self.o["core"] and self.o["hide_twigs"] and self.o["hang"] < 1.0
        cores = self.blobs() if hide else []
        for points, radii in twigs:
            sides = 4 if radii[0] > self.o["square"] else 3
            mat = "bark" if rnd.random() < 0.7 else "bark_shade"
            if cores:
                # What a clump swallows for good is not seen under its
                # leaves: the twig ends just inside it (or is left out, if
                # it is all inside).
                keep = len(points)
                while keep and any(inside(Vector(points[keep - 1]), c, r, self.o["hide_twigs"])
                                   for c, r, _ in cores):
                    keep -= 1
                if keep == 0:
                    continue
                points, radii = points[:keep + 1], radii[:keep + 1]
            tube(mb, points, radii, sides, mat, self.o["hairpins"])
        if self.o["marks"]:
            self.marks(mb)
        self.ground(mb)
        if self.state == "bare":
            return
        petals = self.o["petals"]
        left = self.max_tris - studies.triangles(mb) - petals * 4 - 4
        if self.o["foliage"] != "clumps":
            before = studies.triangles(mb)
            tips = [Vector(points[-1]) for points, radii in twigs if points[-1][2] > self.o["canopy_from"]]
            (self.flowers if self.o["foliage"] == "flowers" else self.rosettes)(mb, tips, left)
            self.fallen(mb, petals)
            if os.environ.get("TREE_DEBUG"):
                print(f"TREE {self.name}: welded {welded}, twigs and ground {before - welded}, "
                      f"{self.o['foliage']} {studies.triangles(mb) - before - petals * 4}")
            return
        if self.o["accents"]:
            left -= self.accents(mb)
        hanging = int(left * self.o["hang"])
        if hanging:
            hanging = self.hanging(mb, twigs, hanging)
        before = studies.triangles(mb)
        self.clumps(mb, left - hanging)
        self.fallen(mb, petals)
        if os.environ.get("TREE_DEBUG"):
            print(f"TREE {self.name}: welded {welded}, twigs and ground {before - hanging - welded}, hanging {hanging}, "
                  f"clumps {studies.triangles(mb) - before - petals * 4} of {len(self.skeleton.blobs)} blobs, "
                  f"{getattr(self, 'cards', 0)} leaves as cards")

    def autumn_tone(self, p, fallback):
        """Which of the three autumn colors the picture has at a place."""
        best, at = 0.6 ** 2, None
        for x, z, color in self.skeleton.autumn:
            d = (x - p.x) ** 2 + (z - p.z) ** 2
            if d < best:
                best, at = d, color
        if at is None:
            return fallback
        if at not in self.tones_seen:
            self.tones_seen[at] = nearest(at, self.palette)
        return self.tones_seen[at]

    def tone(self, rnd, normal, main, p=None):
        """Material of a leaf: by the light in bloom; in autumn, the color
        the picture has there (or its clump's), with some of the others."""
        if self.o["sprinkle"] and self.state == "bloom" and rnd.random() < self.o["sprinkle"][1]:
            return "leaf_4"
        if self.state == "autumn":
            if p is not None:
                main = self.autumn_tone(p, main)
            i = main if rnd.random() < 0.7 else rnd.randrange(3)
        else:
            v = normal.dot(LIGHT) + rnd.uniform(-0.5, 0.5)
            i = 0 if v > 0.6 else (1 if v > 0.08 else 2)
        return f"leaf_{i + 1}"

    def blobs(self):
        """The clumps as (center, radii, main tone)."""
        return [(Vector(c), Vector(r), nearest(color, self.palette) if self.state == "autumn" else 2)
                for c, r, color in self.skeleton.blobs]

    def clumps(self, mb, budget):
        """Cores and leaves of the canopy, in `budget` triangles."""
        o = self.o
        rnd = random.Random(o["seed"] + 37)
        blobs = self.blobs()
        if not blobs or budget < 40:
            return

        def hidden(p, own, k):
            return any(i != own and inside(p, c, r, k) for i, (c, r, _) in enumerate(blobs))

        bm = mb.bm
        used = 0
        if o["core"]:
            for own, (c, r, main) in enumerate(blobs):
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
                    if self.state == "bloom":
                        tone = 2  # The inside of the canopy is in the shade.
                    else:
                        tone = self.autumn_tone((pts[f[0]] + pts[f[1]] + pts[f[2]]) / 3.0, main)
                    face.material_index = mb._material_index(f"leaf_{tone + 1}")
                    face.smooth = False
                used += len(faces)
        # Leaves: spread evenly over what each clump shows of itself.
        probes = 60
        shown, weight = [], []
        for own, (c, r, _) in enumerate(blobs):
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
        areas = [ellipsoid_area(r) * f for (c, r, _), f in zip(blobs, shown)]
        area = sum(areas)
        left = budget - used
        if self.state == "autumn":
            left = int(left * o["autumn_keep"])
        count = left / 2.3  # A leaf is two triangles; the two-sided ones, four.
        if count < 1 or not area:
            return
        size = min(o["leaf"], math.sqrt(o["cover"] * area / count))
        # Candidate leaves of every clump, more than fit, in no order; each
        # clump then takes its share of the triangles, and what some cannot
        # use goes to the others.
        candidates = []
        for own, (c, r, main) in enumerate(blobs):
            found = []
            if shown[own]:
                mean, top = weight[own]
                want = count * areas[own] / area
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
                    found.append((corners, fold_keeps_side(corners, normal), self.tone(rnd, normal, main, p)))
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
                    card(mb, corners, 0.03, mat)  # Blender would turn a fold around: two-sided.
                    self.cards += 1
                taken[own] += 1
                cost += tris
                spent += tris

        self.cards = 0
        for own in range(len(blobs)):
            take(own, max(8.0, left * areas[own] / area))
        for _ in range(40):  # What is left over, a leaf at a time all around.
            before = spent
            for own in range(len(blobs)):
                take(own, 4)
            if spent == before:
                break

    def hanging(self, mb, twigs, budget):
        """Leaves hanging along the twigs that droop (all of them, in a
        weeping tree); returns the triangles used."""
        o = self.o
        rnd = random.Random(o["seed"] + 41)
        lines = [points for points, radii in twigs]
        lines += [(a, b) for a, b, ra, rb in self.capsules if max(ra, rb) < o["hang_limb"]]
        spans = []
        along = []  # Of each span: how far along its twig it starts and ends (0 to 1).
        for points in lines:
            lengths = [dist3(a, b) for a, b in zip(points, points[1:])]
            whole, done = sum(lengths) or 1.0, 0.0
            for (a, b), step in zip(zip(points, points[1:]), lengths):
                a, b = Vector(a), Vector(b)
                if (b - a).length > 1e-6 and (b - a).normalized().z < o["hang_slope"]:
                    spans.append((a, b))
                    along.append((done / whole, (done + step) / whole))
                done += step
        total = sum((b - a).length for a, b in spans)
        count = budget // 4
        if not total or not count:
            return 0
        step = total / count
        half_w, half_l = o["hang_leaf"]
        blobs = self.blobs()
        down = Vector((0.0, 0.0, -1.0))
        used = 0
        carry = rnd.uniform(0.0, step)
        for (a, b), (f0, f1) in zip(spans, along):
            length = (b - a).length
            d = (b - a) / length
            t = carry
            while t < length:
                p = a + d * t
                axis = (d * (0.45 if d.z < 0 else -0.25) + down).normalized()
                out = Vector((p.x, p.y, 0.0))
                out = out.normalized() if out.length > 0.3 else random_unit(rnd)
                normal = out + random_unit(rnd) * 0.8
                normal = (normal - axis * normal.dot(axis)).normalized()
                side = axis.cross(normal)
                k = rnd.uniform(0.8, 1.2)
                w, length_k = half_w * k, half_l * k * rnd.uniform(0.85, 1.15)
                c = p + axis * (length_k * 0.8) + side * rnd.uniform(-0.12, 0.12) + normal * rnd.uniform(-0.06, 0.06)
                lean = side * rnd.uniform(-0.3, 0.3) * w
                main = 0
                if self.state == "autumn" and blobs:
                    main = min(blobs, key=lambda q: (q[0].x - p.x) ** 2 + (q[0].z - p.z) ** 2)[2]
                if o["hang_taper"]:
                    w *= 1.0 - o["hang_taper"] * (f0 + (f1 - f0) * t / length)
                if o["hang_shape"] == "diamond":
                    corners = [c - axis * length_k, c - side * w - axis * (length_k * 0.2),
                               c + axis * length_k + lean, c + side * w - axis * (length_k * 0.2)]
                else:
                    corners = [c - axis * length_k + side * w * 0.75, c - axis * length_k - side * w * 0.75,
                               c + axis * length_k - side * w * 0.55 + lean,
                               c + axis * length_k + side * w * 0.55 + lean]
                card(mb, corners, 0.03, self.tone(rnd, normal + LIGHT * 0.5, main, p))
                used += 4
                t += step
            carry = t - length
        return used

    def ground(self, mb):
        """Grass tufts and stones around the foot."""
        ground(mb, random.Random(self.o["seed"] + 53), self.skeleton.branches[0].radii[0],
               self.o["tufts"], self.o["stones"])

    def marks(self, mb):
        """Dark marks across the trunk (a birch): flat lenses lying on it."""
        rnd = random.Random(self.o["seed"] + 71)
        trunk = self.skeleton.branches[0]
        pts, radii = [Vector(q) for q in trunk.points], trunk.radii
        top = max((q.z for q, r in zip(pts, radii) if r > 0.1), default=1.0)
        up = Vector((0.0, 0.0, 1.0))
        for i in range(self.o["marks"]):
            z = 0.45 + (top - 0.45) * (i + rnd.uniform(0.1, 0.9)) / self.o["marks"]
            k = max(j for j in range(len(pts) - 1) if pts[j].z <= z)
            f = (z - pts[k].z) / ((pts[k + 1].z - pts[k].z) or 1.0)
            center, r = pts[k].lerp(pts[k + 1], f), radii[k] + (radii[k + 1] - radii[k]) * f
            angle = rnd.uniform(0.0, math.tau)
            out = Vector((math.cos(angle), math.sin(angle), 0.0))
            side = up.cross(out)
            w, h = r * rnd.uniform(0.5, 0.9), rnd.uniform(0.05, 0.085)
            c = center + out * r
            sunk = out * (w * w / (2.0 * r))  # The ends follow the trunk around.
            card(mb, [c - side * w - sunk, c - up * h, c + side * w - sunk, c + up * h], 0.08, "mark")

    def flowers(self, mb, tips, budget):
        """Big cup-shaped flowers at the ends of the twigs (a magnolia), and
        a few small leaves among them. In autumn the same pieces are the
        tree's bunches of colored leaves. A flower is a closed piece: a
        bowl, five petals standing on its rim and the hollow between them."""
        o = self.o
        rnd = random.Random(o["seed"] + 73)
        bm = mb.bm
        height, radius = o["flower"]
        rnd.shuffle(tips)
        chosen = []
        for p in tips:  # Not on top of each other.
            if all((p - q).length > radius * 1.5 for q in chosen):
                chosen.append(p)
        chosen = chosen[:max(0, (budget - o["greens"] * 4) // 20)]
        for p in chosen:
            out = Vector((p.x, p.y, 0.0))
            out = out.normalized() if out.length > 0.3 else Vector((0.0, 0.0, 0.0))
            axis = (Vector((0.0, 0.0, 1.0)) + out * 0.6 + random_unit(rnd) * 0.3).normalized()
            u = axis.orthogonal().normalized()
            v = axis.cross(u)
            h, r = height * rnd.uniform(0.8, 1.15), radius * rnd.uniform(0.85, 1.15)
            phase = rnd.uniform(0.0, math.tau)

            def at(k, rr, hh):
                a = phase + k * math.tau / 5
                return bm.verts.new(p + axis * (h * hh) + (u * math.cos(a) + v * math.sin(a)) * (r * rr))

            base = bm.verts.new(p - axis * (h * 0.12))
            heart = bm.verts.new(p + axis * (h * 0.3))
            rim = [at(k, 1.0, 0.42) for k in range(5)]
            petals = [at(k + 0.5, 0.82, 1.0) for k in range(5)]
            main = self.autumn_tone(p, rnd.randrange(3)) if self.state == "autumn" else 0
            for k in range(5):
                j = (k + 1) % 5
                faces = ((base, rim[j], rim[k]), (rim[k], rim[j], petals[k]),
                         (heart, rim[k], petals[k]), (heart, petals[k], rim[j]))
                if self.state == "autumn":
                    tones = (main, main if k % 2 else (main + 1) % 3, (main + 2) % 3, main)
                else:
                    tones = (1 if k % 2 else 2, 0, 1, 2)
                for verts, tone in zip(faces, tones):
                    f = bm.faces.new(verts)
                    f.material_index = mb._material_index(f"leaf_{tone + 1}")
                    f.smooth = False
        if self.state == "bloom":
            for p in tips[:o["greens"]]:
                c = p + random_unit(rnd) * 0.3 - Vector((0.0, 0.0, 0.25))
                normal = random_unit(rnd)
                u = normal.orthogonal().normalized()
                v = normal.cross(u)
                card(mb, [c + u * 0.36, c + v * 0.17, c - u * 0.36, c - v * 0.17], 0.03, "leaf_4")

    def rosettes(self, mb, tips, budget):
        """Balls of sword leaves at the ends of the branches (a dragon
        tree): the twig tips are gathered in groups, a rosette each, with a
        small dark heart."""
        o = self.o
        rnd = random.Random(o["seed"] + 79)
        most, length, width, apart = o["rosette"]
        groups = []
        for p in sorted(tips, key=lambda q: (-q.z, q.x, q.y)):
            near = next((g for g in groups if (g[0] - p).length < apart), None)
            if near:
                near.append(p)
            else:
                groups.append([p])
        if not groups:
            return
        leaves = min(most, (budget // len(groups) - 8) // 4)
        middle = sum((sum(g, Vector()) / len(g) for g in groups), Vector()) / len(groups)
        dark = "leaf_3"
        for g in groups:
            c = sum(g, Vector()) / len(g)
            away = (c - Vector((middle.x, middle.y, middle.z - 2.0))).normalized()
            main = self.autumn_tone(c, rnd.randrange(3)) if self.state == "autumn" else 0
            if self.state == "autumn":
                dark = f"leaf_{main + 1}"
            verts = [mb.bm.verts.new(c + Vector(q) * (length * 0.42)) for q in OCTA]
            for f in OCTA_FACES:
                mb.bm.faces.new([verts[i] for i in f])
            mb._finish(verts, dark, None)
            made = 0
            for d in sphere_points(leaves * 2, rnd):
                if made >= leaves:
                    break
                if d.dot(away) < -0.1 or d.z < -0.45:
                    continue  # None toward the inside of the tree, nor straight down.
                long = length * rnd.uniform(0.75, 1.1)
                side = d.cross(random_unit(rnd)).normalized()
                mid = c + d * (long * 0.35)
                card(mb, [c, mid + side * width, c + d * long, mid - side * width], 0.05,
                     self.tone(rnd, (d + away * 0.6).normalized(), main, c + d * long * 0.5))
                made += 1

    def accents(self, mb):
        """Fruit or flowers on the clumps (an apple tree, a laurel); returns
        the triangles used."""
        kind, count, size, _ = self.o["accents"]
        rnd = random.Random(self.o["seed"] + 83)
        blobs = self.blobs()
        if not blobs:
            return 0
        areas = [ellipsoid_area(r) for c, r, _ in blobs]
        before = studies.triangles(mb)
        made = 0
        for _ in range(count * 12):
            if made >= count:
                break
            own = rnd.choices(range(len(blobs)), areas)[0]
            c, r, _ = blobs[own]
            d = random_unit(rnd)
            if d.z < -0.25:
                continue
            p = c + scaled(d, r) * 1.06
            if any(i != own and inside(p, c2, r2, 1.02) for i, (c2, r2, _) in enumerate(blobs)):
                continue
            normal = Vector((d.x / r.x, d.y / r.y, d.z / r.z)).normalized()
            u = normal.orthogonal().normalized()
            v = normal.cross(u)
            if kind == "fruit":
                pts = [p + normal * size, p - normal * size, p + u * size, p - u * size, p + v * size, p - v * size]
                verts = [mb.bm.verts.new(q) for q in pts]
                for a, b, e in ((0, 2, 4), (0, 4, 3), (0, 3, 5), (0, 5, 2), (1, 4, 2), (1, 3, 4), (1, 5, 3), (1, 2, 5)):
                    mb.bm.faces.new((verts[a], verts[b], verts[e]))
                mb._finish(verts, "accent", None)
            else:  # A bunch of three flat flowers.
                for k in range(3):
                    a = k * math.tau / 3 + rnd.uniform(-0.4, 0.4)
                    q = p + (u * math.cos(a) + v * math.sin(a)) * (size * 0.9) + normal * rnd.uniform(0.0, 0.08)
                    turn = rnd.uniform(0.0, math.tau)
                    e, f = u * math.cos(turn) + v * math.sin(turn), v * math.cos(turn) - u * math.sin(turn)
                    card(mb, [q + e * size, q + f * size, q - e * size, q - f * size], 0.06, "accent")
            made += 1
        return studies.triangles(mb) - before

    def fallen(self, mb, count):
        """Petals or leaves lying on the ground under the canopy."""
        rnd = random.Random(self.o["seed"] + 67)
        for _ in range(count):
            a, r = rnd.uniform(0.0, math.tau), 0.7 + 2.2 * math.sqrt(rnd.random())
            c = Vector((math.cos(a) * r, math.sin(a) * r, 0.03))
            turn = rnd.uniform(0.0, math.tau)
            u = Vector((math.cos(turn), math.sin(turn), 0.0))
            v = Vector((-u.y, u.x, 0.0))
            half = rnd.uniform(0.1, 0.16)
            card(mb, [c + u * half, c + v * half * 0.8, c - u * half, c - v * half * 0.8], 0.04,
                 f"leaf_{rnd.randrange(3) + 1}")


def variants(tree, leaves, **options):
    """The three states of one tree."""
    return [Tree(tree, state, leaves, **options) for state in STATES]
