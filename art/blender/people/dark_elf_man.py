"""Dark elf man: purple skin, long white hair and long pointed ears, a big
purple cloak (a cowl around the neck, a mantle over the shoulders and a
cape down to the calves), a dark tunic with a diagonal leather strap and a
silver clasp, a wide belt with a buckle, leather bracers, dark trousers and
dark boots with knee guards.

This module also holds what the characters of the third reference sheet
share (the other dark elf, the high elves and the cleric import it):
- sheet(): a thin curved panel from a grid of points, with an optional trim
  border of another material (capes, coat skirts, tabards, hoods);
- ribbon(), solid(): curved strips and convex pieces of any material;
- Figure: the shared body plus helpers to place details on its surface
  (front(), ring(), cuff(), skirt_rows()), the planes of the face (face()),
  heeled boots (heel, heels()) and proportions measured on the reference;
- Elf: a Figure with long straight hair in one mass and long pointed ears.
"""

import math

import bmesh
from mathutils import Vector, geometry

import common
import studies
from _human import Human


# ------------------------------------------------------------------ pieces

def sheet(mb, rows, thickness, mat, back=None, trim=None, hem=0.0, sides=0.0, top=0.0, flip=False):
    """A thin curved panel through a grid of points (rows of the same
    length). With the rows going down and the columns counter-clockwise
    seen from above, `mat` is the side looking outward and `back` the side
    looking inward (`flip` swaps them). With `trim`, a border of that
    material runs along the last row (`hem` wide), the first row (`top`)
    and the first and last columns (`sides`: a width or (first, last))."""
    rows = [[Vector(p) for p in r] for r in rows]

    def toward(a, b, d):
        v = b - a
        return a + v * min(0.5, d / max(v.length, 1e-9))

    first, last = sides if isinstance(sides, tuple) else (sides, sides)
    if not trim:
        hem = top = first = last = 0.0
    if top:
        rows.insert(1, [toward(a, b, top) for a, b in zip(rows[0], rows[1])])
    if hem:
        rows.insert(len(rows) - 1, [toward(a, b, hem) for a, b in zip(rows[-1], rows[-2])])
    if first:
        rows = [[r[0], toward(r[0], r[1], first)] + r[1:] for r in rows]
    if last:
        rows = [r[:-1] + [toward(r[-1], r[-2], last), r[-1]] for r in rows]
    nr, nc = len(rows), len(rows[0])

    def normal(i, j):
        du = rows[i][min(j + 1, nc - 1)] - rows[i][max(j - 1, 0)]
        dv = rows[min(i + 1, nr - 1)][j] - rows[max(i - 1, 0)][j]
        n = dv.cross(du)
        return n.normalized() if n.length > 1e-12 else Vector()

    half = thickness * 0.5
    outer = [[mb.bm.verts.new(rows[i][j] + normal(i, j) * half) for j in range(nc)] for i in range(nr)]
    inner = [[mb.bm.verts.new(rows[i][j] - normal(i, j) * half) for j in range(nc)] for i in range(nr)]
    back = back or mat
    if flip:
        mat, back = back, mat

    def is_trim(i, j):
        return bool((top and i == 0) or (hem and i == nr - 2) or (first and j == 0) or (last and j == nc - 2))

    def face(verts, name):
        f = mb.bm.faces.new(verts)
        f.material_index = mb._material_index(name)
        f.smooth = False

    for i in range(nr - 1):
        for j in range(nc - 1):
            t = is_trim(i, j)
            face((outer[i][j], outer[i + 1][j], outer[i + 1][j + 1], outer[i][j + 1]), trim if t else mat)
            face((inner[i][j], inner[i][j + 1], inner[i + 1][j + 1], inner[i + 1][j]), trim if t else back)
    for i in range(nr - 1):
        for j, cell in ((0, 0), (nc - 1, nc - 2)):
            face((outer[i][j], inner[i][j], inner[i + 1][j], outer[i + 1][j]), trim if is_trim(i, cell) else mat)
    for j in range(nc - 1):
        for i, cell in ((0, 0), (nr - 1, nr - 2)):
            face((outer[i][j], outer[i][j + 1], inner[i][j + 1], inner[i][j]), trim if is_trim(cell, j) else mat)


def ribbon(mb, centers, widths, side_axis, thickness, mat):
    """A thin curved strip along `centers`: at every point it is
    `widths[i]` wide, across the line and away from side_axis (the
    direction its flat faces look to). As the rooster's feathers."""
    side_axis = Vector(side_axis).normalized()
    pts = [Vector(c) for c in centers]
    off = side_axis * (thickness * 0.5)
    rows = []
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        across = t.cross(side_axis).normalized() * (widths[i] * 0.5)
        rows.append([mb.bm.verts.new(p + a + o) for a in (-across, across) for o in (off, -off)])
    faces = []
    for r0, r1 in zip(rows, rows[1:]):
        faces += [(r0[0], r0[2], r1[2], r1[0]), (r0[3], r0[1], r1[1], r1[3]),
                  (r0[1], r0[0], r1[0], r1[1]), (r0[2], r0[3], r1[3], r1[2])]
    faces.append((rows[0][0], rows[0][1], rows[0][3], rows[0][2]))
    faces.append((rows[-1][2], rows[-1][3], rows[-1][1], rows[-1][0]))
    for f in faces:
        mb.bm.faces.new(f)
    return mb._finish([v for r in rows for v in r], mat, None)


def solid(mb, points, mat):
    """A convex faceted piece (studies.hull) of the given material."""
    tmp = bmesh.new()
    verts = [tmp.verts.new(Vector(p)) for p in points]
    res = bmesh.ops.convex_hull(tmp, input=verts)
    bmesh.ops.delete(tmp, geom=[v for v in res["geom_interior"] if isinstance(v, bmesh.types.BMVert)],
                     context="VERTS")
    mapping = {v: mb.bm.verts.new(v.co) for v in tmp.verts}
    for f in tmp.faces:
        mb.bm.faces.new([mapping[v] for v in f.verts])
    tmp.free()
    return mb._finish(list(mapping.values()), mat, None)


def arc(a0, a1, count):
    """`count` angles in radians from a0 to a1 degrees (0 = +X, -90 = the
    front, 90 = the back; growing counter-clockwise seen from above)."""
    return [math.radians(a0 + (a1 - a0) * i / (count - 1)) for i in range(count)]


# ------------------------------------------------------------------ figure

class Figure(Human):
    """The shared body plus helpers to place details on it. Coordinates
    given to the helpers are those of the 1.8 m body (as in _human.py);
    they return real points."""

    def V(self, x, y, z):
        return Vector(self.P(x, y, z))

    def u(self, c):
        """A real point in the coordinates of the 1.8 m body."""
        return Vector(c) / self.k

    def out(self, start, direction, off=0.0):
        """Where the ray from `start` (a real point inside the welded
        parts) leaves them, plus `off`."""
        start, d = Vector(start), Vector(direction).normalized()
        t = 0.0
        while t < 1.0 and studies.sdf(self, start + d * t) < 0.0:
            t += 0.004
        return start + d * (t + off)

    def front(self, x, z, off=0.012, y=0.0):
        """The point of the body's front at (x, z), `off` outside it."""
        return self.out(self.V(x, y, z), (0, -1, 0), off * self.k)

    def behind(self, x, z, off=0.012, y=0.0):
        return self.out(self.V(x, y, z), (0, 1, 0), off * self.k)

    def around(self, z, angles, off=0.012, y=0.0, tilt=0.0):
        """Points around the trunk at height z (`tilt`: rise per meter
        toward +X), `off` outside the surface."""
        pts = []
        for a in angles:
            d = Vector((math.cos(a), math.sin(a), 0.0))
            p = self.out(self.V(0, y, z), d, off * self.k)
            p.z += tilt * p.x
            pts.append(p)
        return pts

    def ring(self, mb, z, height, off, mat, count=12, tilt=0.0, y=0.0):
        """A belt around the trunk: `height` tall, standing `off` out."""
        angles = [math.radians(-90 + 360 * i / count) for i in range(count)]
        outer = self.around(z, angles, off, y, tilt)
        inner = self.around(z, angles, -0.02, y, tilt)
        dz = Vector((0, 0, height * self.k * 0.5))
        rows = [[p + dz for p in inner], [p + dz for p in outer], [p - dz for p in outer], [p - dz for p in inner]]
        verts = [[mb.bm.verts.new(p) for p in r] for r in rows]
        for r0, r1 in zip(verts, verts[1:]):
            for i in range(count):
                j = (i + 1) % count
                mb.bm.faces.new((r0[i], r1[i], r1[j], r0[j]))
        return mb._finish([v for r in verts for v in r], mat, None)

    def cuff(self, mb, part, t0, t1, off, mat, segments=6, flare=0.0):
        """A sleeve around a limb (a capsule part) from t0 to t1 along it,
        `off` thicker than the limb (`flare`: more at t1)."""
        _, a, b, ra, rb = self.parts[part]
        a, b = Vector(a), Vector(b)
        mb.cylinder(a.lerp(b, t0), a.lerp(b, t1), ra + (rb - ra) * t0 + off * self.k,
                    ra + (rb - ra) * t1 + (off + flare) * self.k, mat, segments=segments)

    def skirt_rows(self, levels, angles, jag=0.0):
        """Rows for sheet(): one per level (z, rx, ry, y) around the legs,
        the columns at `angles`; a level may end with its own first and
        last angle in degrees (front edges that open downward). `jag`
        lowers every other point of the last row (a ragged hem)."""
        rows = []
        for z, rx, ry, y, *span in levels:
            row = arc(span[0], span[1], len(angles)) if span else angles
            rows.append([self.V(rx * math.cos(a), y + ry * math.sin(a), z) for a in row])
        for i, p in enumerate(rows[-1]):
            if i % 2 == 1:
                p.z -= jag * self.k
        return rows

    # Proportions measured on the reference and not covered by Human.
    face_width = 1.0    # Narrower heads: 0.9.
    heel = 0.0          # Height of the boots' heels (of a 1.8 m body).
    waist_width = None  # Half width of the waist, to override the body's.

    def customize(self, parts):
        hs, w, b = self.head_size, self.face_width, self.build
        parts["head"] = self.ellipsoid((0, -0.01, 1.8 - 0.118 * hs), (0.09 * hs * w, 0.105 * hs, 0.118 * hs))
        parts["jaw"] = self.ellipsoid((0, -0.035, 1.8 - 0.178 * hs), (0.07 * hs * w, 0.075 * hs, 0.06 * hs))
        if self.waist_width:
            parts["waist"] = self.ellipsoid((0, 0.0, 1.13), (self.waist_width, 0.098 * b, 0.15))
        if self.heel:
            # The heel lifts the back of the foot; the ankle joint stays.
            j = self.joints()
            for side, s in ((".L", 1), (".R", -1)):
                parts["foot" + side] = self.capsule((s * j["ankle"][0], 0.03, 0.05 + 0.6 * self.heel),
                                                    (s * j["toe"][0], j["toe"][1], 0.04), 0.048 * b, 0.04 * b)

    def heels(self, mb, mat, width=0.05):
        """The heels of the boots (see `heel`)."""
        x, h, w = self.joints()["ankle"][0], self.heel, width * 0.5
        for s in (-1, 1):
            solid(mb, [self.V(s * x + dx * w * k, y, z) for dx in (-1, 1)
                       for y, z, k in ((0.035, 0.0, 1.0), (0.08, 0.0, 1.0), (0.02, h + 0.03, 1.2), (0.09, h + 0.03, 1.2))],
                  mat)

    def H(self, x, y, z):
        """A point of the head: offsets from the middle of its top, for a
        head of size 1 (they follow head_size and face_width)."""
        hs = self.head_size
        return self.V(x * hs * self.face_width, -0.01 + y * hs, 1.8 + z * hs)

    def face(self, mb, skin="skin", eye="eye", iris="iris", brow="eye"):
        """The planes of the face over the welded head: an angular mask
        (forehead, cheekbones, jaw, pointed chin), a nose wedge, almond
        eyes with a colored iris and slanted eyebrows."""
        H = self.H
        pts = [H(0, -0.106, -0.04), H(0, -0.111, -0.1), H(0, -0.117, -0.195), H(0, -0.108, -0.25)]
        for s in (-1, 1):
            pts += [H(s * 0.045, -0.097, -0.045), H(s * 0.064, -0.092, -0.098), H(s * 0.07, -0.074, -0.145),
                    H(s * 0.055, -0.05, -0.208), H(s * 0.07, -0.03, -0.09), H(s * 0.058, -0.01, -0.2),
                    H(s * 0.016, -0.106, -0.246)]
        mask = solid(mb, pts, skin)
        tris = [[v.co.copy() for v in f.verts] for f in {f for v in mask for f in v.link_faces}]

        def on(x, z, off=0.0025):
            """The point of the mask's front at head offsets (x, z)."""
            origin = H(x, -0.5, z)
            for a, b, c in tris:
                hit = geometry.intersect_ray_tri(a, b, c, Vector((0, 1, 0)), origin, True)
                if hit is not None and hit.y < H(0, -0.03, 0).y:
                    return hit - Vector((0, off * self.k, 0))
            return H(x, -0.1, z)

        # The nose: a wedge from between the brows down to its tip.
        solid(mb, [H(0, -0.113, -0.098), H(0, -0.146, -0.158), H(-0.017, -0.11, -0.166), H(0.017, -0.11, -0.166),
                   H(0, -0.108, -0.172), H(-0.009, -0.108, -0.105), H(0.009, -0.108, -0.105)], skin)
        ez = -0.119
        for s in (-1, 1):
            x = s * 0.035
            studies.plate(mb, [on(x - s * 0.016, ez - 0.003), on(x - s * 0.002, ez + 0.008), on(x + s * 0.019, ez + 0.006),
                               on(x + s * 0.004, ez - 0.007)], 0.003 * self.k, eye)
            studies.plate(mb, [on(x + s * d, ez + e, 0.005) for d, e in ((-0.005, 0.0), (0.001, 0.0065), (0.008, 0.001),
                                                                          (0.002, -0.0055))], 0.003 * self.k, iris)
            studies.plate(mb, [on(x - s * 0.024, ez + 0.013, 0.004), on(x - s * 0.022, ez + 0.022, 0.004),
                               on(x + s * 0.024, ez + 0.033, 0.004), on(x + s * 0.027, ez + 0.026, 0.004)],
                          0.004 * self.k, brow)

    def knee_guard(self, mb, side, mat, size=1.0):
        """A pointed plate over the front of a knee (side: 1 left, -1 right)."""
        j = self.joints()["knee"]
        x, y, z = side * j[0], j[1] - 0.07 * self.build, j[2]
        s = size
        solid(mb, [self.V(x, y - 0.02 * s, z + 0.1 * s), self.V(x - 0.06 * s, y + 0.02, z + 0.02 * s),
                   self.V(x + 0.06 * s, y + 0.02, z + 0.02 * s), self.V(x, y - 0.045 * s, z + 0.01 * s),
                   self.V(x - 0.045 * s, y + 0.02, z - 0.06 * s), self.V(x + 0.045 * s, y + 0.02, z - 0.06 * s),
                   self.V(x, y - 0.015 * s, z - 0.085 * s), self.V(x - 0.05 * s, y + 0.07, z),
                   self.V(x + 0.05 * s, y + 0.07, z)], mat)


class Elf(Figure):
    """A tall slender figure with long straight hair in one mass (a cap,
    curtains at both sides of the face and the hair down the back, plus
    a few faceted locks) and long pointed ears."""
    face_width = 0.9
    hair_back = ((0, 0.085, 1.45), (0.12, 0.06, 0.27))  # The hair down the back (center, radii).
    lock = (0.075, -0.12, 1.38)   # Where the front locks end (x, y, z).
    lock_mid = -0.1               # How far forward the locks pass the neck (y).
    ear = (0.1, 0.05)             # How far the ears reach out of the head, and up.
    hair_out = 0.0                # Extra width of the hair at both sides.
    hair_ends = True              # Pointed ends under the hair down the back.

    def customize(self, parts):
        super().customize(parts)
        hs = self.head_size
        rx = 0.09 * hs * self.face_width
        parts["hair_cap"] = self.ellipsoid((0, 0.018, 1.8 - 0.1 * hs), (rx + 0.018 + self.hair_out, 0.116 * hs, 0.124 * hs))
        parts["hair_back"] = self.ellipsoid(*self.hair_back)
        for side, s in ((".L", 1), (".R", -1)):   # The curtains framing the face.
            parts["hair_side" + side] = self.ellipsoid((s * (rx + 0.014 + self.hair_out), -0.01, 1.8 - 0.165 * hs),
                                                       (0.034, 0.064 * hs, 0.135 * hs))

    def is_hair(self, zone):
        return zone.startswith("hair")

    def hair(self, mb, mat="hair"):
        """The faceted parts of the hair: the two halves of the fringe
        from the center parting down to the temples, the front locks that
        continue the curtains to a point on the chest, and the pointed ends
        at the back."""
        H = self.H
        hs = self.head_size
        rx = 0.09 * hs * self.face_width + self.hair_out
        zt = 1.8 - 0.27 * hs
        lx, ly, lz = self.lock
        for s in (-1, 1):
            solid(mb, [H(0, -0.1, 0.012), H(0, 0.0, 0.03), H(s * 0.1, 0.0, -0.02), H(s * 0.096, -0.068, -0.115),
                       H(s * 0.07, -0.103, -0.085), H(s * 0.03, -0.11, -0.03), H(s * 0.1, -0.03, -0.14)], mat)
            solid(mb, [self.V(s * (rx - 0.012), -0.055, zt), self.V(s * (rx + 0.042), -0.045, zt),
                       self.V(s * (rx + 0.042), 0.02, zt), self.V(s * (rx - 0.005), 0.02, zt),
                       self.V(s * (lx - 0.022), self.lock_mid, (zt + lz) * 0.5 + 0.02),
                       self.V(s * (lx + 0.03), self.lock_mid + 0.01, (zt + lz) * 0.5 + 0.02),
                       self.V(s * lx, ly, lz)], mat)
        if not self.hair_ends:
            return
        (cx, cy, cz), (rx, ry, rz) = self.hair_back
        for x, w, drop in ((-0.62, 0.3, 0.07), (0.0, 0.34, 0.12), (0.62, 0.3, 0.07)):
            z0 = cz - rz * 0.72
            solid(mb, [self.V(cx + (x - w) * rx, cy, z0), self.V(cx + (x + w) * rx, cy, z0),
                       self.V(cx + x * rx, cy - ry * 0.7, z0), self.V(cx + x * rx, cy + ry * 0.75, z0),
                       self.V(cx + x * rx, cy + ry * 0.2, cz - rz - drop)], mat)

    def ears(self, mb, mat="skin"):
        H = self.H
        out, up = self.ear
        hs, w = self.head_size, self.face_width
        for s in (-1, 1):
            solid(mb, [H(s * 0.08, 0.0, -0.15), H(s * 0.08, 0.01, -0.095), H(s * 0.085, -0.04, -0.12),
                       H(s * 0.08, 0.04, -0.12),
                       H(s * (0.105 + out / hs / w), 0.07, -0.112 + up / hs)], mat)


# ------------------------------------------------------------ dark elf man

class DarkElfMan(Elf):
    name = "dark_elf_man"
    height = 1.9
    build = 0.9
    heel = 0.03
    hair_ends = False   # His hair goes into the cowl.
    hair_back = ((0, 0.075, 1.52), (0.115, 0.06, 0.15))
    lock = (0.072, -0.13, 1.385)
    lock_mid = -0.135
    ear = (0.1, 0.09)
    colors = {
        "skin": common.rgb(0xB587D8),
        "hair": common.rgb(0xDCD2E2),
        "cloak": common.rgb(0x4E3672),
        "cloak_light": common.rgb(0x5C4384),
        "cloak_shade": common.rgb(0x402C62),
        "dark": common.rgb(0x2A1D40),      # The inside of the cloak, the trousers, the eyes.
        "tunic": common.rgb(0x3B3145),
        "tunic_trim": common.rgb(0x5E5070),
        "leather": common.rgb(0x7C5145),
        "silver": common.rgb(0xCFC6CC),
        "boot": common.rgb(0x553D4E),
        "iris": common.rgb(0xE0962E),
    }
    tone_material = "cloak"
    tones = 0.5
    budget = 1150

    CLASP = 1.4      # Height where the mantle closes on the chest.
    EDGE = 1.25      # Height of the edge of the mantle over the arms.
    BOOT = 0.47

    def __init__(self):
        super().__init__()
        k = self.k
        strap = Vector((0.30, 0, -0.26)).normalized()
        self.bands = [
            (self.V(-0.03, 0, 1.27), strap, 0.022 * k,
             lambda c, n: abs(c.x) < 0.17 * k and 1.05 * k < c.z < 1.46 * k),
        ]
        self.cuts = [
            (self.V(0, 0, self.BOOT), (0, 0, 1), lambda c, n: c.z < 0.6 * k),
        ]

    def customize(self, parts):
        super().customize(parts)
        parts["cowl"] = self.ellipsoid((0, 0.02, 1.5), (0.165, 0.14, 0.078))
        parts["cowl_back"] = self.ellipsoid((0, 0.1, 1.47), (0.13, 0.085, 0.1))   # The hood, fallen back.

    def paint(self, c, n):
        u = self.u(c)
        zone = self.zone(c)
        part = zone.split(".")[0]
        if self.is_hair(zone):
            return "hair"
        if part in ("head", "jaw", "neck", "hand"):
            return "skin"
        if part.startswith("cowl") or part == "shoulder":
            return "cloak"
        if part in ("upper_arm", "forearm"):
            return "skin" if u.x < 0 else "tunic"   # His right arm is bare.
        if part in ("chest", "waist", "hips"):
            return "leather" if studies.in_band(self, c, n) else "tunic"
        if part == "thigh":
            return "dark"
        return "boot" if u.z < self.BOOT else "dark"

    def details(self, mb):
        k = self.k
        self.face(mb, eye="dark", brow="dark")
        self.ears(mb)
        self.hair(mb)
        # The mantle: from the cowl out over the shoulders in folded planes,
        # its edge hanging over the arms and rising to the clasp in front.
        angles = arc(-87, 267, 15)
        rows = [[], [], [], []]
        for i, a in enumerate(angles):
            c, s = math.cos(a), math.sin(a)
            fold = 1.0 if i % 2 else 0.0
            ry = 0.125 if s < 0 else 0.165
            low = self.EDGE if s > 0 else self.CLASP - (self.CLASP - self.EDGE) * min(1.0, abs(c) / 0.55)
            rows[0].append(self.V(0.125 * c, 0.02 + 0.105 * s, 1.535))
            rows[1].append(self.V(0.2 * c, 0.02 + (ry - 0.025) * s, max(1.495 + 0.02 * abs(c), low + 0.06)))
            rows[2].append(self.V((0.25 + 0.01 * fold) * c, 0.02 + (ry - 0.006) * s,
                                  max(1.41 + 0.045 * abs(c), low + 0.03)))
            rows[3].append(self.V((0.262 + 0.02 * fold) * c, 0.02 + (ry + 0.012 * fold) * s, low - 0.03 * fold))
        sheet(mb, rows, 0.016 * k, "cloak", back="dark")
        # The cape: from under the mantle down to the calves.
        xs = (1.0, 0.72, 0.36, 0.0, -0.36, -0.72, -1.0)
        ys = (0.0, 0.62, 0.8, 1.0, 0.8, 0.62, 0.0)
        cape = []
        for z, w, d, jag in ((1.36, 0.235, 0.14, 0), (1.0, 0.27, 0.17, 0), (0.62, 0.3, 0.2, 0), (0.37, 0.315, 0.22, 1)):
            cape.append([self.V(x * w, 0.03 + y * d + (0.022 if i % 2 else 0.0) * (1.4 - z),
                                z - (0.07 if jag and i % 2 == 0 else 0.0)) for i, (x, y) in enumerate(zip(xs, ys))])
        sheet(mb, cape, 0.014 * k, "cloak", back="dark")
        # The skirt of the tunic, open at the front.
        skirt = self.skirt_rows([(1.08, 0.15, 0.108, 0.0), (0.86, 0.178, 0.128, 0.0), (0.6, 0.195, 0.145, 0.0)],
                                arc(-80, 260, 9), jag=0.025)
        sheet(mb, skirt, 0.012 * k, "tunic", back="dark", trim="tunic_trim", hem=0.028 * k, sides=0.028 * k)
        # Belt and buckle, and a second strap sagging over his right hip.
        self.ring(mb, 1.115, 0.06, 0.014, "leather")
        self.ring(mb, 1.06, 0.034, 0.02, "leather", tilt=0.25, count=10)
        b = self.front(0.012, 1.115, 0.024)
        mb.box(b, (0.068 * k, 0.014 * k, 0.066 * k), "silver")
        mb.box(b - Vector((0, 0.006 * k, 0)), (0.036 * k, 0.014 * k, 0.034 * k), "leather")
        # The clasp where the strap meets the mantle.
        mb.box(self.V(0.035, -0.118, self.CLASP - 0.012), (0.055 * k, 0.02 * k, 0.036 * k), "silver",
               rotation_z=math.radians(-12))
        # Bracers, knee guards and heels.
        for side in (".L", ".R"):
            self.cuff(mb, "forearm" + side, 0.25, 0.92, 0.009, "leather")
        for s in (-1, 1):
            self.knee_guard(mb, s, "leather", 1.05)
        self.heels(mb, "boot")


SPECS = [DarkElfMan()]
