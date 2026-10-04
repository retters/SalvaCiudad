"""Shared pieces of the `bridges` proposal family: bridges, docks and boats.

Conventions of the family (on top of docs/ARTE.md):
- Bridges run along X (the side elevation, with the arches, faces -Y). Z = 0
  is the ground of the two banks; piers and piles go below 0 into the water.
- Docks run along Y: the shore is at +Y and the water end at -Y.
- Boats float with the waterline at Z = 0 and the bow toward -Y.
"""

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import bmesh  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import _kit as kit  # noqa: E402
import buildings  # noqa: E402
import common  # noqa: E402

FAMILY = "bridges"

COLORS = dict(buildings.COLORS)
COLORS.update({
    "wood_dark": common.rgb(0x5E4026),
    "plank": common.rgb(0x9C7446),
    "plank_b": common.rgb(0x86603A),
    "tar": common.rgb(0x3E3028),
    "rope": common.rgb(0xB89A62),
    "stone_light": common.rgb(0xB8B1A6),
    "stone_moss": common.rgb(0x7E8A62),
    "brick_dark": common.rgb(0x84422E),
    "brick_light": common.rgb(0xB86A4C),
    "road": common.rgb(0x8E7E66),
    "canvas": common.rgb(0xE6DEC6),
    "canvas_shade": common.rgb(0xCFC4A6),
    "net": common.rgb(0x6E6A52),
    "root": common.rgb(0x6A4E34),
    "root_light": common.rgb(0x8A6A42),
    "moss": common.rgb(0x5E8A3C),
    "marble": common.rgb(0xE8E8E2),
    "marble_shade": common.rgb(0xC2C8CE),
    "crystal": common.rgb(0x6FD0E0),
    "crystal_deep": common.rgb(0x3A8FC0),
    "crystal_glow": common.rgb(0xC8F4FF),
    "lantern": common.rgb(0xFFD070),
    "flame_core": common.rgb(0xFFE08A),
    "shingle": common.rgb(0x7A5A3C),
    "shingle_dark": common.rgb(0x64482E),
    "sack": common.rgb(0xC2A878),
    "bark": common.rgb(0xD8D0BC),
    "paint_red": common.rgb(0xA83A30),
    "paint_blue": common.rgb(0x2F5488),
    "paint_green": common.rgb(0x3F6E46),
    "paint_yellow": common.rgb(0xD0A030),
})

# Palettes of the parametrized generators.
WOOD = {"body": "wood", "trim": "timber", "cap": "wood_light", "deck": ("plank", "plank_b"),
        "ring": ("wood_light", "wood"), "road": "plank"}
TARRED = {"body": "wood_dark", "trim": "tar", "cap": "wood", "deck": ("plank_b", "wood_dark"),
          "ring": ("wood", "wood_dark"), "road": "plank_b"}
STONE = {"body": "stone", "trim": "stone_dark", "cap": "stone_light", "ring": ("stone_light", "stone_dark"),
         "road": "road", "deck": ("stone_light", "stone")}
BRICK = {"body": "brick", "trim": "brick_dark", "cap": "stone_light", "ring": ("brick_light", "brick_dark"),
         "road": "road", "deck": ("brick_light", "brick")}
MOSSY = {"body": "stone_dark", "trim": "stone", "cap": "stone_moss", "ring": ("stone", "stone_dark"),
         "road": "road", "deck": ("stone", "stone_dark")}
MARBLE = {"body": "marble", "trim": "marble_shade", "cap": "gold", "ring": ("marble", "marble_shade"),
          "road": "marble_shade", "glow": "crystal_glow", "deck": ("marble", "marble_shade")}
CRYSTAL = {"body": "crystal", "trim": "crystal_deep", "cap": "crystal_glow", "ring": ("crystal", "crystal_deep"),
           "road": "crystal_deep", "glow": "crystal_glow", "deck": ("crystal", "crystal_deep")}
ROOFS = {"thatch": ("thatch", "thatch_dark"), "shingle": ("shingle", "shingle_dark"), "tile": ("roof", "roof_dark")}


def jit(i, amp=1.0, salt=0.0):
    """A repeatable pseudo-random number in [-amp, amp] for the index i."""
    v = math.sin(i * 12.9898 + salt * 78.233) * 43758.5453
    return ((v - math.floor(v)) * 2.0 - 1.0) * amp


def smoothstep(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def _frame(direction):
    x = direction.normalized()
    if abs(x.z) < 0.999:
        y = Vector((0, 0, 1)).cross(x).normalized()
    else:
        y = Vector((0, 1, 0))
    z = x.cross(y)
    m = Matrix.Identity(4)
    for col, axis in enumerate((x, y, z)):
        for row in range(3):
            m[row][col] = axis[row]
    return m


class B:
    """A MeshBuilder with default bone weights and a rigid placement, so the
    same piece builder serves a static model, a moving part and a piece of an
    assembled demo."""

    def __init__(self, mb=None, weights=None, m=None):
        self.mb = mb if mb is not None else kit.begin()
        self.w = weights
        self.m = m if m is not None else Matrix.Identity(4)

    def bone(self, name):
        return B(self.mb, {name: 1.0}, self.m)

    def at(self, dx=0.0, dy=0.0, dz=0.0, rz=0.0):
        """The same builder moved by (dx, dy, dz) and turned rz degrees."""
        m = self.m @ Matrix.Translation((dx, dy, dz)) @ Matrix.Rotation(math.radians(rz), 4, "Z")
        return B(self.mb, self.w, m)

    def turn(self, axis, deg):
        """The same builder turned around one of its own axes ("X", "Y", "Z")."""
        return B(self.mb, self.w, self.m @ Matrix.Rotation(math.radians(deg), 4, axis))

    def _p(self, p):
        return self.m @ Vector(p)

    def _cube(self, m, mat):
        r = bmesh.ops.create_cube(self.mb.bm, size=1.0, matrix=self.m @ m)
        return self.mb._finish(r["verts"], mat, self.w)

    def box(self, c, s, mat, rz=0.0):
        return self._cube(Matrix.Translation(Vector(c)) @ Matrix.Rotation(rz, 4, "Z")
                          @ Matrix.Diagonal((s[0], s[1], s[2], 1.0)), mat)

    def beam(self, a, b, w, h, mat):
        """A box from a to b; w is its horizontal thickness and h the other."""
        a, b = Vector(a), Vector(b)
        d = b - a
        if d.length < 1e-6:
            return []
        return self._cube(Matrix.Translation((a + b) * 0.5) @ _frame(d)
                          @ Matrix.Diagonal((d.length, w, h, 1.0)), mat)

    def cyl(self, a, b, r, mat, r2=None, seg=8):
        if (Vector(a) - Vector(b)).length < 1e-6:
            return []
        return self.mb.cylinder(self._p(a), self._p(b), r, r if r2 is None else r2, mat,
                                weights=self.w, segments=seg)

    def sphere(self, c, r, mat, seg=7, rings=5, scale=(1, 1, 1)):
        return self.mb.sphere(self._p(c), r, mat, weights=self.w, segments=seg, rings=rings, scale=scale)

    def face(self, pts, mat):
        bm = self.mb.bm
        vs = [bm.verts.new(self._p(p)) for p in pts]
        f = bm.faces.new(vs)
        f.material_index = self.mb._material_index(mat)
        f.smooth = False
        for v in vs:
            for bone, w in (self.w or {}).items():
                v[self.mb.deform][self.mb._group_index(bone)] = w
        return vs

    def solid(self, ring_a, ring_b, mat):
        """A closed solid between two rings with the same number of points."""
        bm = self.mb.bm
        a = [bm.verts.new(self._p(p)) for p in ring_a]
        c = [bm.verts.new(self._p(p)) for p in ring_b]
        bm.faces.new(list(reversed(a)))
        bm.faces.new(c)
        n = len(a)
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], c[j], c[i]))
        return self.mb._finish(a + c, mat, self.w)

    def mesh(self, pts, faces):
        """A connected mesh: `faces` is a list of (indexes into pts, material)."""
        bm = self.mb.bm
        vs = [bm.verts.new(self._p(p)) for p in pts]
        for v in vs:
            for bone, w in (self.w or {}).items():
                v[self.mb.deform][self.mb._group_index(bone)] = w
        for idx, mat in faces:
            try:
                f = bm.faces.new([vs[i] for i in idx])
            except ValueError:
                continue
            f.material_index = self.mb._material_index(mat)
            f.smooth = False
        return vs

    def xz(self, pts, y0, y1, mat):
        """Extrudes a convex polygon of (x, z) points along Y."""
        return self.solid([(x, y0, z) for x, z in pts], [(x, y1, z) for x, z in pts], mat)

    def yz(self, pts, x0, x1, mat):
        """Extrudes a convex polygon of (y, z) points along X."""
        return self.solid([(x0, y, z) for y, z in pts], [(x1, y, z) for y, z in pts], mat)

    def xy(self, pts, z0, z1, mat, shrink=1.0):
        """Extrudes a convex polygon of (x, y) points along Z; `shrink`
        scales the top ring around its center (a taper)."""
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        top = [(cx + (x - cx) * shrink, cy + (y - cy) * shrink, z1) for x, y in pts]
        return self.solid([(x, y, z0) for x, y in pts], top, mat)


# --- Small pieces --------------------------------------------------------------------


def planks_x(b, x0, x1, width, z=0.0, mats=("plank", "plank_b"), step=0.3, thick=0.07, zf=None, yc=0.0,
             gap=0.02, ragged=0.04):
    """Deck boards laid across the way (each one along Y), from x0 to x1.
    `z` (or zf(x)) is the top of the deck."""
    n = max(1, round((x1 - x0) / step))
    s = (x1 - x0) / n
    for i in range(n):
        xa, xb = x0 + i * s + gap / 2, x0 + (i + 1) * s - gap / 2
        wide = width + jit(i, ragged, x0)
        if zf:
            b.beam((xa, yc, zf(xa) - thick / 2), (xb, yc, zf(xb) - thick / 2), wide, thick, mats[i % len(mats)])
        else:
            b.box(((xa + xb) / 2, yc, z - thick / 2), (xb - xa, wide, thick), mats[i % len(mats)])


def planks_y(b, y0, y1, width, z=0.0, mats=("plank", "plank_b"), step=0.3, thick=0.07, xc=0.0, gap=0.02,
             ragged=0.04):
    """Deck boards laid along X, from y0 to y1 (a dock that runs along Y)."""
    n = max(1, round((y1 - y0) / step))
    s = (y1 - y0) / n
    for i in range(n):
        ya, yb = y0 + i * s + gap / 2, y0 + (i + 1) * s - gap / 2
        b.box((xc, (ya + yb) / 2, z - thick / 2), (width + jit(i, ragged, y0), yb - ya, thick), mats[i % len(mats)])


def rail(b, pts, h=1.0, post=0.1, mat="timber", rail_mat="wood", mid=True, top=0.08, cap=None):
    """A handrail: a post on every point and rails between them."""
    for p in pts:
        b.box((p[0], p[1], p[2] + h / 2), (post, post, h), mat)
        if cap:
            b.box((p[0], p[1], p[2] + h + 0.04), (post + 0.06, post + 0.06, 0.08), cap)
    for p, q in zip(pts, pts[1:]):
        b.beam((p[0], p[1], p[2] + h - 0.06), (q[0], q[1], q[2] + h - 0.06), top, top, rail_mat)
        if mid:
            b.beam((p[0], p[1], p[2] + h * 0.5), (q[0], q[1], q[2] + h * 0.5), 0.05, 0.06, rail_mat)


def plate(b, p0, p1, p2, p3, thick, mat):
    """A flat board through four corners given in order, `thick` thick."""
    ring = [Vector(p) for p in (p0, p1, p2, p3)]
    normal = (ring[1] - ring[0]).cross(ring[3] - ring[0]).normalized() * (thick / 2)
    return b.solid([tuple(p - normal) for p in ring], [tuple(p + normal) for p in ring], mat)


def line(a, b_, n):
    return [tuple(lerp(a[k], b_[k], i / n) for k in range(3)) for i in range(n + 1)]


def sag(a, b_, drop, n=8):
    """Points of a hanging rope from a to b that drops `drop` in the middle."""
    return [(lerp(a[0], b_[0], t), lerp(a[1], b_[1], t), lerp(a[2], b_[2], t) - drop * 4 * t * (1 - t))
            for t in (i / n for i in range(n + 1))]


def rope(b, pts, r=0.025, mat="rope", seg=5):
    for p, q in zip(pts, pts[1:]):
        b.cyl(p, q, r, mat, seg=seg)


def chain(b, a, c, mat="iron", link=0.16):
    """A chain of alternating flat links from a to c."""
    a, c = Vector(a), Vector(c)
    n = max(1, round((c - a).length / link))
    for i in range(n):
        p, q = a.lerp(c, i / n), a.lerp(c, (i + 1) / n)
        if i % 2:
            b.beam(p, q, 0.08, 0.03, mat)
        else:
            b.beam(p, q, 0.03, 0.08, mat)


def rock(b, cx, cy, r, z0, z1, seed=0, mat="stone", sides=7, shrink=0.7, squash=1.0):
    pts = []
    for i in range(sides):
        a = 2 * math.pi * i / sides + jit(i, 0.2, seed)
        rr = r * (1 + jit(i, 0.22, seed + 3))
        pts.append((cx + rr * math.cos(a), cy + rr * squash * math.sin(a)))
    b.xy(pts, z0, z1, mat, shrink=shrink)


def log(b, a, c, r, bark="log", end="log_end", seg=8, r2=None):
    """A trunk with pale cut ends."""
    a, c = Vector(a), Vector(c)
    d = (c - a).normalized()
    b.cyl(a, c, r, bark, r2=r2, seg=seg)
    b.cyl(a - d * 0.012, a + d * 0.01, r * 0.82, end, seg=seg)
    r_end = r if r2 is None else r2
    b.cyl(c - d * 0.01, c + d * 0.012, r_end * 0.82, end, seg=seg)


def barrel_y(b, cx, cy, cz, length=1.2, r=0.38, mat="wood", hoop="iron"):
    """A barrel lying along Y."""
    b.cyl((cx, cy - length / 2, cz), (cx, cy, cz), r * 0.84, mat, r2=r, seg=10)
    b.cyl((cx, cy, cz), (cx, cy + length / 2, cz), r, mat, r2=r * 0.84, seg=10)
    for y in (cy - length * 0.3, cy + length * 0.3):
        b.cyl((cx, y - 0.03, cz), (cx, y + 0.03, cz), r * 0.96, hoop, seg=10)


def barrel(b, cx, cy, z=0.0, h=0.8, r=0.3, mat="wood", hoop="iron"):
    b.cyl((cx, cy, z), (cx, cy, z + h / 2), r * 0.85, mat, r2=r, seg=9)
    b.cyl((cx, cy, z + h / 2), (cx, cy, z + h), r, mat, r2=r * 0.85, seg=9)
    for zz in (z + h * 0.2, z + h * 0.8):
        b.cyl((cx, cy, zz - 0.025), (cx, cy, zz + 0.025), r * 0.96, hoop, seg=9)


def crate(b, cx, cy, z=0.0, s=0.6, mat="wood_light", edge="wood", rz=0.0):
    b.box((cx, cy, z + s / 2), (s, s, s), mat, rz=rz)
    b.box((cx, cy, z + s / 2), (s + 0.03, s * 0.16, s + 0.03), edge, rz=rz)
    b.box((cx, cy, z + s / 2), (s * 0.16, s + 0.03, s + 0.03), edge, rz=rz)


def sack(b, cx, cy, z=0.0, r=0.28, mat="sack"):
    b.sphere((cx, cy, z + r * 0.75), r, mat, seg=7, rings=4, scale=(1.0, 0.8, 0.8))
    b.cyl((cx, cy, z + r * 1.3), (cx, cy, z + r * 1.55), r * 0.2, mat, r2=r * 0.3, seg=5)


def lantern(b, x, y, z, glow="lantern", frame="iron", s=0.22):
    """A lantern hanging with its top at z."""
    b.box((x, y, z - 0.03), (s + 0.06, s + 0.06, 0.05), frame)
    b.box((x, y, z - 0.05 - s / 2), (s, s, s), glow)
    b.box((x, y, z - 0.08 - s), (s + 0.06, s + 0.06, 0.05), frame)
    for sx in (-1, 1):
        for sy in (-1, 1):
            b.box((x + sx * s / 2, y + sy * s / 2, z - 0.05 - s / 2), (0.03, 0.03, s), frame)


def flame(b, x, y, z, s=0.5, outer="torch_flame", core="flame_core"):
    """A faceted flame of two cones, standing at z."""
    b.cyl((x, y, z), (x, y, z + s * 0.35), s * 0.22, outer, r2=s * 0.36, seg=6)
    b.cyl((x, y, z + s * 0.35), (x, y, z + s), s * 0.36, outer, r2=0.01, seg=6)
    b.cyl((x, y, z + s * 0.1), (x, y, z + s * 0.6), s * 0.2, core, r2=0.01, seg=5)
    for k in range(3):   # Smaller tongues that lean out around the main one.
        a = k * 2.1 + 0.4
        dx, dy = math.cos(a) * s * 0.3, math.sin(a) * s * 0.3
        b.cyl((x + dx * 0.6, y + dy * 0.6, z), (x + dx, y + dy, z + s * 0.28), s * 0.12, outer, r2=s * 0.17, seg=5)
        b.cyl((x + dx, y + dy, z + s * 0.28), (x + dx * 1.5, y + dy * 1.5, z + s * (0.6 + 0.08 * k)), s * 0.17,
              outer if k else core, r2=0.01, seg=5)


def net(b, a, c, d, e, mat="net", n=5, r=0.012):
    """A net as a grid of cords between the corners a, c (top) and d, e (bottom)."""
    a, c, d, e = Vector(a), Vector(c), Vector(d), Vector(e)
    for i in range(n + 1):
        t = i / n
        b.cyl(a.lerp(c, t), d.lerp(e, t), r, mat, seg=4)
        b.cyl(a.lerp(d, t), c.lerp(e, t), r, mat, seg=4)


# --- Masonry -------------------------------------------------------------------------


def arch(b, xc, half, rise, zs, top, y0, y1, pal, n=9, ring=0.28, proud=0.06, keep=None):
    """A masonry arch along X, centered at xc: an elliptical opening of
    half-span `half` and height `rise` springing from zs, filled above up to
    top(x). It spans xc -/+ (half + ring). `keep` limits the stones built to
    those indexes (a ruin)."""
    def pt(i, extra):
        a = math.pi * i / n
        return (xc - (half + extra) * math.cos(a), zs + (rise + extra) * math.sin(a))

    for i in range(n):
        if keep is not None and i not in keep:
            continue
        ia, ib = pt(i, 0.0), pt(i + 1, 0.0)
        oa, ob = pt(i, ring), pt(i + 1, ring)
        key = n % 2 == 1 and i == n // 2
        extra = 0.05 if key else 0.0
        b.xz([ia, ib, ob, oa], y0 - proud - extra, y1 + proud + extra,
             pal["cap"] if key else pal["ring"][i % 2])
        b.xz([oa, ob, (ob[0], top(ob[0])), (oa[0], top(oa[0]))], y0, y1, pal["body"])


def pier(b, x, wx, y0, y1, z0, z1, pal, cut=True, footing=True):
    """A pier under a bridge that runs along X, with pointed cutwaters on
    both faces (up and down the river)."""
    yc = (y0 + y1) / 2
    b.box((x, yc, (z0 + z1) / 2), (wx, y1 - y0, z1 - z0), pal["body"])
    if cut:
        nose = wx * 0.85
        for s, y in ((-1, y0), (1, y1)):
            tri = [(x - wx / 2, y), (x + wx / 2, y), (x, y + s * nose)]
            b.solid([(px, py, z0) for px, py in tri], [(px, py, z1 - 0.35) for px, py in tri], pal["body"])
            b.solid([(px, py, z1 - 0.35) for px, py in tri], [(x, y, z1 + 0.25)] * 3, pal["cap"])
    if footing:
        b.box((x, yc, z0 + 0.25), (wx + 0.3, y1 - y0 + (2.0 * wx if cut else 0.3), 0.5), pal["trim"])


def parapet(b, x0, x1, y, top, pal, h=0.9, t=0.3, step=1.0):
    """A low wall along X on top of a bridge whose road is at top(x)."""
    n = max(1, round((x1 - x0) / step))
    s = (x1 - x0) / n
    for i in range(n):
        xa, xb = x0 + i * s, x0 + (i + 1) * s
        za, zb = top(xa), top(xb)
        b.xz([(xa, za - 0.1), (xb, zb - 0.1), (xb, zb + h), (xa, za + h)], y - t / 2, y + t / 2, pal["body"])
        b.xz([(xa, za + h), (xb, zb + h), (xb, zb + h + 0.1), (xa, za + h + 0.1)], y - t / 2 - 0.05,
             y + t / 2 + 0.05, pal["cap"] if i % 2 == 0 else pal["trim"])


def road(b, x0, x1, y0, y1, top, mat, step=1.0, thick=0.05):
    n = max(1, round((x1 - x0) / step))
    s = (x1 - x0) / n
    for i in range(n):
        xa, xb = x0 + i * s, x0 + (i + 1) * s
        b.xz([(xa, top(xa)), (xb, top(xb)), (xb, top(xb) + thick), (xa, top(xa) + thick)], y0, y1, mat)


def pilaster(b, x, y, z, pal, s=0.5, h=1.25):
    b.box((x, y, z + h / 2 - 0.1), (s, s, h + 0.2), pal["body"])
    b.box((x, y, z + h + 0.05), (s + 0.12, s + 0.12, 0.1), pal["trim"])
    q = s / 2 + 0.02
    b.solid([(x - q, y - q, z + h + 0.1), (x + q, y - q, z + h + 0.1), (x + q, y + q, z + h + 0.1),
             (x - q, y + q, z + h + 0.1)], [(x, y, z + h + 0.38)] * 4, pal["cap"])


def blocks(b, x0, x1, y, z0, z1, pal, face=-1, count=6, seed=0):
    """A few stones standing proud of a wall face at y, to read as masonry."""
    for i in range(count):
        x = lerp(x0, x1, 0.5 + jit(i, 0.42, seed))
        z = lerp(z0, z1, 0.5 + jit(i, 0.42, seed + 5))
        b.box((x, y + face * 0.02, z), (0.45 + jit(i, 0.12, seed + 9), 0.08, 0.22), pal["trim"])


def roof_y(b, cx, cy, w, d, wall_h, rise, overhang, mats, rows=5, gables=(), gable_mat="wood_light"):
    """A two-slope roof whose ridge runs along Y, over a w x d block.
    `gables` lists the ends (-1 for -Y, 1 for +Y) closed with a gable."""
    ridge = wall_h + rise
    ya, yb = cy - d / 2 - overhang, cy + d / 2 + overhang
    for side in (-1, 1):
        for r in range(rows):
            t0 = r / rows
            t1 = min(1.0, (r + 1) / rows + 0.05)
            xo = cx + side * (w / 2 + overhang) * (1 - t0)
            xi = cx + side * (w / 2 + overhang) * (1 - t1)
            zo = wall_h - 0.12 + (rise + 0.12) * t0
            zi = wall_h - 0.12 + (rise + 0.12) * t1
            ring = [(xo, zo), (xi, zi), (xi, zi + 0.09), (xo, zo + 0.09)]
            b.solid([(x, ya, z) for x, z in ring], [(x, yb, z) for x, z in ring], mats[r % len(mats)])
    b.box((cx, cy, ridge + 0.04), (0.22, d + 2 * overhang, 0.12), mats[-1])
    for end in gables:
        y = cy + end * d / 2
        b.xz([(cx - w / 2, wall_h), (cx + w / 2, wall_h), (cx, ridge - 0.05)], y - 0.05, y + 0.05, gable_mat)
    return ridge


def roof_x(b, cx, cy, w, d, wall_h, rise, overhang, mats, rows=5, gables=(), gable_mat="wood_light", ends=0.0):
    """A two-slope roof whose ridge runs along X, over a w (along X) x d
    block. `ends` is how far it overhangs the two gable ends."""
    ridge = wall_h + rise
    xa, xb = cx - w / 2 - ends, cx + w / 2 + ends
    for side in (-1, 1):
        for r in range(rows):
            t0 = r / rows
            t1 = min(1.0, (r + 1) / rows + 0.05)
            yo = cy + side * (d / 2 + overhang) * (1 - t0)
            yi = cy + side * (d / 2 + overhang) * (1 - t1)
            zo = wall_h - 0.12 + (rise + 0.12) * t0
            zi = wall_h - 0.12 + (rise + 0.12) * t1
            ring = [(yo, zo), (yi, zi), (yi, zi + 0.09), (yo, zo + 0.09)]
            b.solid([(xa, y, z) for y, z in ring], [(xb, y, z) for y, z in ring], mats[r % len(mats)])
    b.box((cx, cy, ridge + 0.04), (w + 2 * ends, 0.22, 0.12), mats[-1])
    for end in gables:
        x = cx + end * w / 2
        b.yz([(cy - d / 2, wall_h), (cy + d / 2, wall_h), (cy, ridge - 0.05)], x - 0.05, x + 0.05, gable_mat)
    return ridge


def save(b, name, mech=None, extras=None):
    lift = float(os.environ.get("BRIDGES_LIFT", "0") or 0)
    if lift:
        # Review aid only: a static copy raised above the preview's ground, in
        # preview/_lift, to look at what goes below Z = 0.
        bmesh.ops.translate(b.mb.bm, verts=b.mb.bm.verts, vec=(0, 0, lift))
        return kit.save(b.mb, FAMILY + "/preview/_lift", name, COLORS)
    return kit.save(b.mb, FAMILY, name, COLORS, mech=mech, extras=extras)
