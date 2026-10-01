"""Shared pieces for the weapons 1 to 12 (w01_... to w12_...): faceted
blades, turned parts (grips, collars, pommels), gems and bevelled plates.

Every piece is a closed solid built straight into the MeshBuilder with
clean flat faces; nothing here goes through the remesh. The weapon's wide
side lies on the XZ plane (seen from the front, -Y), so most pieces are
given as (x, z) outlines plus a half thickness along Y.

`mat` is a material name or, where it says so, a function that picks the
name for each face, so big faces can get lighter and darker variants.
`place` maps a piece's local (x, y, z) to the model (see placer()).
"""

import math

from mathutils import Vector


def pixels(scale, x0, y0):
    """Maps a point measured on the reference picture (pixels, y down) to
    (x, z) in meters: x0 is the pixel column of X = 0 and y0 the pixel row
    of Z = 0."""
    def to_xz(px, py):
        return ((px - x0) * scale, (y0 - py) * scale)
    return to_xz


def placer(origin=(0.0, 0.0, 0.0), angle=0.0, mirror=False):
    """Local (x, y, z) -> model: mirrored in X if asked, turned `angle`
    degrees about Y (counter-clockwise seen from the front) and moved to
    origin."""
    c, s = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    k = -1.0 if mirror else 1.0

    def place(p):
        x, y, z = p[0] * k, p[1], p[2]
        return Vector((origin[0] + x * c - z * s, origin[1] + y, origin[2] + x * s + z * c))
    return place


class Solid:
    """One piece: its vertices are merged by position, so rows that meet at
    a point (a tip, a sharp edge) make triangles instead of empty faces."""

    def __init__(self, mb, place=None):
        self.mb = mb
        self.place = place
        self.verts = {}

    def vert(self, p):
        key = (round(p[0], 5), round(p[1], 5), round(p[2], 5))
        if key not in self.verts:
            self.verts[key] = self.mb.bm.verts.new(self.place(p) if self.place else p)
        return self.verts[key]

    def face(self, points, mat):
        verts = []
        for p in points:
            v = self.vert(p)
            if v not in verts:
                verts.append(v)
        if len(verts) < 3 or self.mb.bm.faces.get(verts) is not None:
            return None
        f = self.mb.bm.faces.new(verts)
        f.material_index = self.mb._material_index(mat)
        f.smooth = False
        return f


def ridged(mb, rows, mat, place=None):
    """A blade-like solid, the same on the front and the back. Each row is
    a cross-section: points (x, z, h) across the blade, h being the half
    thickness there (0 on a sharp edge). Rows are joined in order; a row
    whose points are all the same is a tip. mat: name or f(row, column)."""
    s = Solid(mb, place)
    pick = mat if callable(mat) else (lambda i, j: mat)
    n = len(rows[0])
    front = [[(x, -h, z) for x, z, h in row] for row in rows]
    back = [[(x, h, z) for x, z, h in row] for row in rows]
    for i in range(len(rows) - 1):
        for j in range(n - 1):
            for side in (front, back):
                s.face([side[i][j], side[i][j + 1], side[i + 1][j + 1], side[i + 1][j]], pick(i, j))
        for j, k in ((0, 0), (n - 1, n - 2)):  # Blunt edges.
            s.face([front[i][j], back[i][j], back[i + 1][j], front[i + 1][j]], pick(i, k))
    for i, k in ((0, 0), (len(rows) - 1, len(rows) - 2)):
        s.face(front[i] + back[i][::-1], pick(k, 0))
    return s


def blade(mb, half_width, z0, z1, z_tip, half, mats, ridge=0.0, place=None):
    """A straight double-edged blade from z0 up to the tip: it starts to
    taper at z1. half: half thickness at the middle. ridge: half width of a
    flat middle band (0: one ridge line). mats: (left, right, tip left, tip
    right[, middle]) materials."""
    w, r = half_width, ridge
    if r:
        rows = [[(-w, z, 0.0), (-r, z, half), (r, z, half), (w, z, 0.0)] for z in (z0, z1)]
        rows.append([(0.0, z_tip, 0.0)] * 4)
        table = [[mats[0], mats[4], mats[1]], [mats[2], mats[4], mats[3]]]
    else:
        rows = [[(-w, z, 0.0), (0.0, z, half), (w, z, 0.0)] for z in (z0, z1)]
        rows.append([(0.0, z_tip, 0.0)] * 3)
        table = [[mats[0], mats[1]], [mats[2], mats[3]]]
    return ridged(mb, rows, lambda i, j: table[i][j], place)


def polygon(sides, phase=0.0, scale=(1.0, 1.0)):
    """A regular cross-section for lathe() and tube(); phase in degrees."""
    return [(math.cos(math.radians(phase) + i * math.tau / sides) * scale[0],
             math.sin(math.radians(phase) + i * math.tau / sides) * scale[1]) for i in range(sides)]


def chamfered(cut=0.6, scale=(1.0, 1.0)):
    """A square cross-section with its corners cut (a hammer head)."""
    pts = [(1, cut), (cut, 1), (-cut, 1), (-1, cut), (-1, -cut), (-cut, -1), (cut, -1), (1, -cut)]
    return [(a * scale[0], b * scale[1]) for a, b in pts]


def _frame(axis):
    axis = Vector(axis).normalized()
    u = Vector((0.0, 1.0, 0.0)).cross(axis)
    u = u.normalized() if u.length > 1e-6 else Vector((1.0, 0.0, 0.0))
    return axis, u, axis.cross(u)


def _bridge(s, rings, radii, mat):
    pick = mat if callable(mat) else ((lambda i, k: mat[i]) if isinstance(mat, (list, tuple))
                                      else (lambda i, k: mat))
    n = len(rings[0])
    for i in range(len(rings) - 1):
        for k in range(n):
            j = (k + 1) % n
            s.face([rings[i][k], rings[i][j], rings[i + 1][j], rings[i + 1][k]], pick(i, k))
    if radii[0] > 0.0:
        s.face(rings[0], pick(0, 0))
    if radii[-1] > 0.0:
        s.face(rings[-1], pick(len(rings) - 2, 0))
    return s


def lathe(mb, profile, mat, sides=6, origin=(0.0, 0.0, 0.0), axis=(0.0, 0.0, 1.0), phase=0.0,
          scale=(1.0, 1.0), section=None, place=None):
    """A turned piece (grip, collar, pommel, cone, block): a cross-section
    swept along a straight axis. profile: (distance along the axis, radius)
    in order; radius 0 at an end makes a point. For the Z axis the section
    is (x, y); for the X axis, (-z, y). mat: name, one name per segment, or
    f(segment, side)."""
    axis, u, v = _frame(axis)
    section = section or polygon(sides, phase, scale)
    origin = Vector(origin)
    rings = [[tuple(origin + axis * t + (u * a + v * b) * r) for a, b in section] for t, r in profile]
    return _bridge(Solid(mb, place), rings, [r for _, r in profile], mat)


def tube(mb, path, radii, mat, sides=6, phase=0.0, scale=(1.0, 1.0), section=None, place=None):
    """Like lathe(), along a bent path of points (a curved grip, an arm):
    each cross-section is set square to the path there."""
    pts = [Vector(p) for p in path]
    section = section or polygon(sides, phase, scale)
    rings = []
    for i, p in enumerate(pts):
        tangent = pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]
        _, u, v = _frame(tangent)
        rings.append([tuple(p + (u * a + v * b) * radii[i]) for a, b in section])
    return _bridge(Solid(mb, place), rings, radii, mat)


def wrapped(mb, z0, z1, radius, bands, mat, sides=6, squeeze=0.84, x=0.0, phase=0.0, place=None):
    """A wrapped grip from z0 to z1: `bands` rings of wrap, pinched between
    them. mat as in lathe()."""
    n = bands * 2
    profile = [(z0 + (z1 - z0) * i / n, radius * (squeeze if i % 2 == 0 else 1.0)) for i in range(n + 1)]
    return lathe(mb, profile, mat, sides=sides, origin=(x, 0.0, 0.0), phase=phase, place=place)


def gem(mb, center, half_w, half_h, depth, mats, base=0.0, place=None):
    """A cut gem set in a plate: a diamond outline on the XZ plane with a
    point toward the front and one toward the back. base: half thickness of
    the plate under it (the gem's outline lies on both faces). mats: a name
    or the four facet names (upper left, upper right, lower left, lower
    right)."""
    if isinstance(mats, str):
        mats = (mats,) * 4
    cx, cy, cz = center
    for sign in (-1.0, 1.0):
        y = cy + sign * base
        top, bottom = (cx, y, cz + half_h), (cx, y, cz - half_h)
        left, right = (cx - half_w, y, cz), (cx + half_w, y, cz)
        apex = (cx, y + sign * depth, cz)
        s = Solid(mb, place)
        s.face([top, left, apex], mats[0])
        s.face([top, right, apex], mats[1])
        s.face([bottom, left, apex], mats[2])
        s.face([bottom, right, apex], mats[3])
        if base > 0.0:
            s.face([top, right, bottom, left], mats[3])
        else:  # One solid: the back half shares the outline.
            apex = (cx, y + depth, cz)
            s.face([top, left, apex], mats[0])
            s.face([top, right, apex], mats[1])
            s.face([bottom, left, apex], mats[2])
            s.face([bottom, right, apex], mats[3])
            break


def bevel_plate(mb, points, half, inset, mat, bevel_mat=None, edge=0.0, y=0.0, place=None):
    """A flat convex piece on the XZ plane with bevelled borders: `points`
    (x, z) is its outline, where it is `edge` thick each side (0: sharp);
    the flat face, `inset` inside the outline, is `half` thick each side.
    bevel_mat: name or f(border index); defaults to mat."""
    pts = [Vector((x, z)) for x, z in points]
    area = sum(pts[i].x * pts[(i + 1) % len(pts)].y - pts[(i + 1) % len(pts)].x * pts[i].y
               for i in range(len(pts)))
    if area < 0.0:
        pts.reverse()
    n = len(pts)
    inner = []
    for i in range(n):
        d0 = (pts[i] - pts[i - 1]).normalized()
        d1 = (pts[(i + 1) % n] - pts[i]).normalized()
        n0, n1 = Vector((-d0.y, d0.x)), Vector((-d1.y, d1.x))  # Inward normals.
        inner.append(pts[i] + (n0 + n1) * (inset / (1.0 + n0.dot(n1))))
    pick = bevel_mat if callable(bevel_mat) else (lambda i: bevel_mat or mat)
    s = Solid(mb, place)
    for sign in (-1.0, 1.0):
        face = [(p.x, y + sign * half, p.y) for p in inner]
        rim = [(p.x, y + sign * edge, p.y) for p in pts]
        s.face(face, mat)
        for i in range(n):
            j = (i + 1) % n
            s.face([rim[i], rim[j], face[j], face[i]], pick(i))
    if edge > 0.0:
        for i in range(n):
            j = (i + 1) % n
            s.face([(pts[i].x, y - edge, pts[i].y), (pts[j].x, y - edge, pts[j].y),
                    (pts[j].x, y + edge, pts[j].y), (pts[i].x, y + edge, pts[i].y)], pick(i))
    return s


def spike(mb, base, tip, radius, mat, sides=4, phase=0.0):
    """A pointed spike from base to tip. mat: name or f(segment, side)."""
    base, tip = Vector(base), Vector(tip)
    return lathe(mb, [(0.0, radius), ((tip - base).length, 0.0)], mat, sides=sides, origin=base,
                 axis=tip - base, phase=phase)


def cross_guard(mb, stations, mats, y_edge=0.5):
    """Both arms of a sword's cross-guard, mirrored in X. stations, from the
    middle outward: (x, z of the arm's middle line, half height, half
    thickness); a last station with half height 0 is a point. mats: (lower
    facets, upper facets)."""
    rows = [[(x, zc - hh, ht * y_edge), (x, zc, ht), (x, zc + hh, ht * y_edge)] for x, zc, hh, ht in stations]
    for mirror in (False, True):
        ridged(mb, rows, lambda i, j: mats[j], placer(mirror=mirror))


def kite(mb, top, z_wide, bottom, half_width, half, inset, mat, bevel_mat=None, edge=None):
    """The guard's middle plate: a kite outline from z = bottom to z = top,
    widest at z_wide."""
    pts = [(0.0, top), (half_width, z_wide), (0.0, bottom), (-half_width, z_wide)]
    return bevel_plate(mb, pts, half, inset, mat, bevel_mat, half * 0.45 if edge is None else edge)
