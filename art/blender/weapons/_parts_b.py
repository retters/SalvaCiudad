"""Shared pieces for the weapons 13 to 27: bows, arrows and shields, all
built directly as clean faceted solids (helper module, not listed).

- tube(): a faceted tube along a path (bow limbs, rods, stocks).
- Shield: a plate with a raised rim made from a 2D outline, with a painted
  face, flat emblems, folds and a bend or dome.
- lathe(), stud(), fletching(), tone(): bosses, rivets, vanes and facet
  tones.
"""

import math
import random

import bmesh
from mathutils import Vector

import common
import studies


# ------------------------------------------------------------------ colors

def shades(name, hex_color, k=0.14):
    """{name, name_light, name_shade}: a color and its lighter and darker
    facet tones (sRGB 0xRRGGBB in, linear RGB out)."""
    def scaled(f):
        c = [(hex_color >> s) & 255 for s in (16, 8, 0)]
        if f > 0:
            c = [round(x + (255 - x) * f) for x in c]
        else:
            c = [round(x * (1 + f)) for x in c]
        return common.rgb((c[0] << 16) | (c[1] << 8) | c[2])
    return {name: common.rgb(hex_color), name + "_light": scaled(k), name + "_shade": scaled(-k * 1.3)}


def tone(mb, verts, mat, seed=1, share=0.5, tones=("_light", "_shade")):
    """Gives a share of the faces of `verts` that have material `mat` one of
    its facet tones (mat_light, mat_shade), as build_final does for the
    welded surface."""
    rnd = random.Random(seed)
    main = mb._material_index(mat)
    others = [mb._material_index(mat + t) for t in tones]
    faces = sorted({f for v in verts if v.is_valid for f in v.link_faces},
                   key=lambda f: tuple(round(x, 4) for x in f.calc_center_median()))
    for f in faces:
        if f.material_index == main and rnd.random() < share:
            f.material_index = rnd.choice(others)


def picture(points, bottom, top, length, shift=(0.0, 0.0)):
    """Turns points measured on the reference picture (pixels, y down) into
    model points on the XZ plane: the line bottom-top becomes vertical and
    `length` meters long, and the whole set is centered on X and stands on
    Z = 0, then moved by `shift` (x, z) to make room for the thickness of
    the pieces. `points` is a dict; returns a dict of Vectors."""
    b = Vector((bottom[0], -bottom[1]))
    up = Vector((top[0], -top[1])) - b
    scale = length / up.length
    up.normalize()
    right = Vector((up.y, -up.x))
    out = {k: Vector(((Vector((p[0], -p[1])) - b).dot(right) * scale, 0.0,
                      (Vector((p[0], -p[1])) - b).dot(up) * scale)) for k, p in points.items()}
    xs = [p.x for p in out.values()]
    origin = Vector(((min(xs) + max(xs)) * 0.5 - shift[0], 0.0, min(p.z for p in out.values()) - shift[1]))
    return {k: p - origin for k, p in out.items()}


# ------------------------------------------------------------------- tubes

def tube(mb, stations, sides=4, phase=None, up=(0.0, 1.0, 0.0)):
    """A faceted tube through `stations`: (point, radius or (ru, rv), mat).
    `mat` paints the segment that starts at that station. Two stations at
    the same point with different radii make a step (a wrap, a band). `up`
    fixes the cross-section: ru is measured along it, rv across."""
    bm = mb.bm
    up = Vector(up)
    pts = [Vector(s[0]) for s in stations]
    if phase is None:
        phase = math.pi / sides
    rings = []
    for i, (_, radius, _) in enumerate(stations):
        a = b = i
        while a > 0 and (pts[a] - pts[i]).length < 1e-6:
            a -= 1
        while b < len(pts) - 1 and (pts[b] - pts[i]).length < 1e-6:
            b += 1
        t = (pts[b] - pts[a]).normalized()
        u = (up - t * up.dot(t)).normalized()
        v = t.cross(u)
        ru, rv = radius if isinstance(radius, tuple) else (radius, radius)
        rings.append([bm.verts.new(pts[i] + u * (ru * math.cos(phase + k * math.tau / sides))
                                   + v * (rv * math.sin(phase + k * math.tau / sides))) for k in range(sides)])
    verts = [v for r in rings for v in r]
    for i, (r0, r1) in enumerate(zip(rings, rings[1:])):
        index = mb._material_index(stations[i][2])
        for k in range(sides):
            j = (k + 1) % sides
            f = bm.faces.new((r0[k], r0[j], r1[j], r1[k]))
            f.material_index = index
    for ring, mat in ((list(reversed(rings[0])), stations[0][2]), (rings[-1], stations[-2][2])):
        f = bm.faces.new(ring)
        f.material_index = mb._material_index(mat)
    for f in {f for v in verts for f in v.link_faces}:
        f.smooth = False
    return verts


def lathe(mb, origin, axis, rings, sides, mat, phase=0.0):
    """A faceted solid of revolution: `rings` are (radius, height along
    axis) from the base up; a last radius of 0 closes it with a point."""
    bm = mb.bm
    origin, axis = Vector(origin), Vector(axis).normalized()
    u = axis.orthogonal().normalized()
    if abs(axis.y) > 0.9:  # Looking along Y: start the facets from +Z.
        u = Vector((0, 0, 1))
    v = axis.cross(u)
    loops = []
    for r, h in rings:
        if r <= 0.0:
            loops.append([bm.verts.new(origin + axis * h)])
        else:
            loops.append([bm.verts.new(origin + axis * h + (u * math.cos(phase + k * math.tau / sides)
                                                            + v * math.sin(phase + k * math.tau / sides)) * r)
                          for k in range(sides)])
    for a, b in zip(loops, loops[1:]):
        for k in range(sides):
            j = (k + 1) % sides
            if len(b) == 1:
                bm.faces.new((a[k], a[j], b[0]))
            else:
                bm.faces.new((a[k], a[j], b[j], b[k]))
    bm.faces.new(list(reversed(loops[0])))
    if len(loops[-1]) > 1:
        bm.faces.new(loops[-1])
    return mb._finish([v for loop in loops for v in loop], mat, None)


def spike(mb, base, tip, radius, mat, sides=4):
    """A faceted pyramid from a base center to its tip."""
    base, tip = Vector(base), Vector(tip)
    return lathe(mb, base, tip - base, [(radius, 0.0), (0.0, (tip - base).length)], sides, mat)


def fletching(mb, nock, toward_head, length, width, sweep, angles, mat, thickness=0.006, start=0.02):
    """Arrow vanes around a shaft: parallelograms whose outer edge is swept
    back, toward the nock. `angles` (degrees around the shaft, 0 = +X for an
    upright arrow) gives one vane each."""
    nock = Vector(nock)
    d = Vector(toward_head).normalized()
    side = d.cross(Vector((0, 1, 0)))
    if side.length < 1e-6:
        side = Vector((1, 0, 0))
    side.normalize()
    other = d.cross(side)
    verts = []
    for a in angles:
        out = side * math.cos(math.radians(a)) + other * math.sin(math.radians(a))
        p0 = nock + d * start
        p1 = nock + d * (start + length)
        verts += studies.plate(mb, [p0, p1, p1 + out * width - d * sweep * 0.6, p0 + out * width - d * sweep],
                               thickness, mat)
    return verts


# ----------------------------------------------------------------- shields

def regular(n, radius, center=(0.0, 0.0), phase=0.0, squash=1.0):
    """A regular polygon outline (x, z); with phase 0 a vertex is on top."""
    return [(center[0] + radius * squash * math.sin(phase + i * math.tau / n),
             center[1] + radius * math.cos(phase + i * math.tau / n)) for i in range(n)]


def mirrored(half):
    """A symmetric outline from its right half (x >= 0), top first; points
    on the axis (x = 0) are not repeated."""
    left = [(-x, z) for x, z in reversed(half) if x > 1e-9]
    return list(half) + left


def inset(outline, width):
    """The outline moved inward by `width` (mitered corners)."""
    n = len(outline)
    area = sum(outline[i][0] * outline[(i + 1) % n][1] - outline[(i + 1) % n][0] * outline[i][1] for i in range(n))
    sign = 1.0 if area > 0 else -1.0
    out = []
    for i in range(n):
        p0, p1, p2 = (Vector(outline[(i + k) % n]) for k in (-1, 0, 1))
        e1, e2 = (p1 - p0).normalized(), (p2 - p1).normalized()
        n1 = Vector((-e1.y, e1.x)) * sign
        n2 = Vector((-e2.y, e2.x)) * sign
        m = (n1 + n2) / max(0.35, 1.0 + n1.dot(n2))
        out.append((p1.x + m.x * width, p1.y + m.y * width))
    return out


def inside_polygon(x, z, poly):
    hit = False
    for i in range(len(poly)):
        (x0, z0), (x1, z1) = poly[i], poly[(i + 1) % len(poly)]
        if (z0 > z) != (z1 > z) and x < x0 + (z - z0) * (x1 - x0) / (z1 - z0):
            hit = not hit
    return hit


class Shield:
    """A shield made flat in the XZ plane (the face looks to -Y, at y = 0)
    and then bent: body() makes the plate with its raised rim and painted
    face, emblem() adds flat raised pieces, finish() folds everything along
    the fold planes and moves every vertex by bend(x, z). After finish(),
    at() gives points on the bent face for rivets, bosses and spikes."""

    def __init__(self, mb, outline, bend=None):
        self.mb = mb
        self.outline = [(float(x), float(z)) for x, z in outline]
        self.bend = bend or (lambda x, z: 0.0)
        mb.bm.verts.index_update()
        self.start = len(mb.bm.verts)
        self.back = 0.0

    def _loop(self, pts, y):
        return [self.mb.bm.verts.new((x, y, z)) for x, z in pts]

    def _verts(self):
        self.mb.bm.verts.ensure_lookup_table()
        return self.mb.bm.verts[self.start:]

    def body(self, rim_w, rim_h, back, rim_mat, back_mat, paint, bevel=0.0, inner_mat=None,
             rim_paint=None, rings=(), fan=True, center=None, splits=()):
        """rim_w, rim_h: the rim's width and its height over the face;
        back: the plate's thickness behind the face; bevel: how far the rim's
        front edge is set in from the outline (a sloped outer side).
        paint(x, z) names the material of a face of the shield's face;
        rim_paint(i) of the rim's segment i. The face is a fan around
        `center` through `rings` (scales of the inner outline), or one
        polygon if fan is false; `splits` are lines (point, normal) in (x, z)
        that cut the face where colors must change."""
        bm, mb = self.mb.bm, self.mb
        n = len(self.outline)
        inner = inset(self.outline, rim_w)
        self.inner = inner
        self.back = back
        a = self._loop(self.outline, back)
        b = self._loop(inset(self.outline, bevel) if bevel else self.outline, -rim_h)
        c = self._loop(inner, -rim_h)
        d = self._loop(inner, 0.0)
        f = bm.faces.new(list(reversed(a)))
        f.material_index = mb._material_index(back_mat)
        for i in range(n):
            j = (i + 1) % n
            mat = mb._material_index(rim_paint(i) if rim_paint else rim_mat)
            for lo, hi, m in ((a, b, mat), (b, c, mat), (c, d, mb._material_index(inner_mat) if inner_mat else mat)):
                f = bm.faces.new((lo[i], lo[j], hi[j], hi[i]))
                f.material_index = m
        if center is None:
            center = (sum(p[0] for p in inner) / n, sum(p[1] for p in inner) / n)
        loops = [d]
        for s in rings:
            loops.append(self._loop([(center[0] + (x - center[0]) * s, center[1] + (z - center[1]) * s)
                                     for x, z in inner], 0.0))
        for l0, l1 in zip(loops, loops[1:]):
            for i in range(n):
                j = (i + 1) % n
                bm.faces.new((l0[i], l0[j], l1[j], l1[i]))
        if fan:
            mid = bm.verts.new((center[0], 0.0, center[1]))
            for i in range(n):
                bm.faces.new((loops[-1][i], loops[-1][(i + 1) % n], mid))
        else:
            bm.faces.new(loops[-1])
        for point, normal in splits:
            faces = self._face_faces()
            geom = list({v for f in faces for v in f.verts}) + list({e for f in faces for e in f.edges}) + faces
            bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(point[0], 0.0, point[1]),
                                   plane_no=(normal[0], 0.0, normal[1]))
        for f in self._face_faces():
            c0 = f.calc_center_median()
            f.material_index = mb._material_index(paint(c0.x, c0.z))
        for f in {f for v in self._verts() for f in v.link_faces}:
            f.smooth = False

    def _face_faces(self):
        faces = {f for v in self._verts() for f in v.link_faces}
        out = []
        for f in faces:
            if all(abs(v.co.y) < 1e-7 for v in f.verts):
                c = f.calc_center_median()
                if inside_polygon(c.x, c.z, self.inner):
                    out.append(f)
        return out

    def emblem(self, points, mat, height=0.012, sink=0.003, lift=0.0):
        """A flat raised piece on the face from a polygon of (x, z) points
        (it may be concave); it is folded and bent with the shield."""
        bm = self.mb.bm
        area = sum(points[i][0] * points[(i + 1) % len(points)][1] - points[(i + 1) % len(points)][0] * points[i][1]
                   for i in range(len(points)))
        pts = list(points) if area < 0 else list(reversed(points))
        front = self._loop(pts, -height - lift)
        back = self._loop(pts, sink - lift)
        bm.faces.new(front)
        bm.faces.new(list(reversed(back)))
        for i in range(len(pts)):
            j = (i + 1) % len(pts)
            bm.faces.new((back[i], back[j], front[j], front[i]))
        return self.mb._finish(front + back, mat, None)

    def strip(self, centers, width, mat, **kw):
        """A band of constant width along a line of (x, z) points."""
        pts = [Vector(p) for p in centers]
        left, right = [], []
        for i, p in enumerate(pts):
            t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
            side = Vector((-t.y, t.x)) * (width * 0.5)
            left.append(tuple(p + side))
            right.append(tuple(p - side))
        return self.emblem(left + list(reversed(right)), mat, **kw)

    def finish(self, folds=()):
        """Cuts all the pieces along the fold lines (point, normal) in
        (x, z), so they can crease there, and bends them."""
        bm = self.mb.bm
        for point, normal in folds:
            verts = list(self._verts())
            faces = list({f for v in verts for f in v.link_faces})
            geom = verts + list({e for f in faces for e in f.edges}) + faces
            bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(point[0], 0.0, point[1]),
                                   plane_no=(normal[0], 0.0, normal[1]))
        for v in self._verts():
            v.co.y += self.bend(v.co.x, v.co.z)
        bm.normal_update()

    def at(self, x, z, y=0.0):
        """The point of the bent face at (x, z), moved y (negative: forward)."""
        return Vector((x, self.bend(x, z) + y, z))

    def stud(self, x, z, radius, height, mat, y=0.0, sides=4, phase=0.0):
        """A small pyramid (a rivet) pointing forward."""
        return lathe(self.mb, self.at(x, z, y + 0.002), (0, -1, 0), [(radius, 0.0), (0.0, height)], sides, mat,
                     phase=phase)

    def boss(self, x, z, rings, mat, y=0.0, sides=8, phase=0.0):
        """A faceted dome pointing forward: rings of (radius, height)."""
        return lathe(self.mb, self.at(x, z, y + 0.002), (0, -1, 0), rings, sides, mat, phase=phase)

    def grip(self):
        """The back center, where an arm holds the shield."""
        xs = [p[0] for p in self.outline]
        zs = [p[1] for p in self.outline]
        x, z = (min(xs) + max(xs)) * 0.5, (min(zs) + max(zs)) * 0.5
        return (x, self.bend(x, z) + self.back, z)
