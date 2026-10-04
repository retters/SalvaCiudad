"""Shared pieces of the `wonders` proposal family: wonders built in stages
and smaller monuments. See ../LEEME.md.

Conventions of the family (on top of docs/ARTE.md):
- A wonder is one generator called with stage 1 (foundations and work yard),
  2 (half built, scaffolds and cranes, no roofs) or 3 (finished). The ids are
  <id>_stage1, <id>_stage2 and <id>.
- Masonry goes through a *capped* builder: in stages 1 and 2 whatever rises
  above an uneven height is cut or left out, so the same code draws the
  unfinished walls. Roofs, glass, statues and whatever moves are only built
  when finished.
- The three stages share the footprint: the work yard stays inside it.
- What moves all the time (flags, flames, lights, floating pieces) goes in
  one looping clip `idle`; other clips are named for what they do (`ring`,
  `turn`, `open`).
"""

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import bmesh  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import _kit as kit  # noqa: E402
import _shapes  # noqa: E402
import common  # noqa: E402

FAMILY = "wonders"
TAU = 2 * math.pi
C = common.rgb

COLORS = dict(_shapes.COLORS)
COLORS.update({
    "marble": C(0xE9E6DC), "marble_shade": C(0xC6C8CC), "marble_dark": C(0xA4A8B0),
    "sand": C(0xD2B480), "sand_dark": C(0xB08E5A), "sand_light": C(0xE6D0A0),
    "granite": C(0x6E6C70), "granite_dark": C(0x4E4C52), "granite_light": C(0x8C8A8E),
    "obsidian": C(0x24202C), "obsidian_light": C(0x3C3448), "obsidian_edge": C(0x5A4A78),
    "crystal": C(0xA060E0), "crystal_glow": C(0xE0B0FF), "crystal_blue": C(0x60C8F0), "glow_blue": C(0xC8F4FF),
    "bronze": C(0x9A6E36), "bronze_dark": C(0x6E4C26), "bronze_light": C(0xC08E48), "verdigris": C(0x5EA08A),
    "gold": C(0xD8AC3C), "gold_dark": C(0xA87E28), "gold_light": C(0xF2D470),
    "slate": C(0x4A5666), "slate_dark": C(0x384250), "slate_light": C(0x5E6C7E),
    "tile": C(0xA8502E), "tile_dark": C(0x863C22), "copper": C(0x4E9A84), "copper_dark": C(0x3A7C6A),
    "glass_red": C(0xC83A3A), "glass_blue": C(0x3A6CD0), "glass_green": C(0x3CA860), "glass_yellow": C(0xF0C040),
    "glass_violet": C(0x8A4AC8), "glass_dark": C(0x26303C), "window": C(0xF6D070),
    "flame": C(0xF08A20), "flame_core": C(0xFFE070), "flame_violet": C(0xB060F0), "flame_violet_core": C(0xF0C8FF),
    "flame_green": C(0x60E080), "flame_green_core": C(0xD8FFD0), "coal": C(0x2A2422),
    "water": C(0x4A8FC0), "water_light": C(0x9AD0F0), "water_deep": C(0x2E6A9A),
    "soil": C(0x7A5A3C), "soil_dark": C(0x5E4530), "grass": C(0x6A9440), "grass_dark": C(0x527A34), "paving": C(0xB0A898), "paving_dark": C(0x948C7E),
    "leaf": C(0x4E8A3A), "leaf_dark": C(0x386A2C), "leaf_light": C(0x7AB04A), "leaf_gold": C(0xD0C050),
    "trunk": C(0x6A4E34), "trunk_dark": C(0x4E3826), "trunk_light": C(0x8A6A46),
    "cloth_red": C(0xB8302C), "cloth_blue": C(0x2E4E9A), "cloth_white": C(0xECE6D6), "cloth_green": C(0x3A7A44),
    "cloth_purple": C(0x6A3A8A), "cloth_gold": C(0xD8A830), "cloth_black": C(0x2A2630),
    "bone": C(0xE4DCC4), "bone_dark": C(0xB8AE90), "cave": C(0x14110F), "door": C(0x5A3A22), "door_dark": C(0x402A18),
    "lacquer": C(0xC0342A), "lacquer_dark": C(0x8E241E), "plaster": C(0xE8E0CC), "brick": C(0xA0553A), "brick_dark": C(0x84422C),
    "lily": C(0x5AA04A), "lily_dark": C(0x3E7E3A), "lily_light": C(0x86C060), "petal": C(0xF0A0C0), "petal_light": C(0xFBE0EA), "petal_dark": C(0xD0689A),
    "jade": C(0x3AA088), "turquoise": C(0x30B0B8), "sandbox": C(0xD8C48E), "beam": C(0xFFF2B0), "lantern": C(0xFFC860),
    "rust": C(0x8A4A2E), "hide": C(0x9A7A52), "war_red": C(0x9A2018), "night": C(0x1E2A4A), "star": C(0xF4F0D0),
    "lime": C(0xE8E4D8), "moss": C(0x5E8A3A), "reed": C(0xA8A050), "reed_dark": C(0x7E7A38),
})

GLASS = ("glass_blue", "glass_red", "glass_yellow", "glass_green", "glass_violet")
SLATE = ("slate", "slate_dark")
TILE = ("tile", "tile_dark")
COPPER = ("copper", "copper_dark")


def jit(i, j=0, salt=0.0):
    """A repeatable pseudo-random number in [0, 1) for a pair of indices."""
    v = math.sin(i * 12.9898 + j * 78.233 + salt * 37.719) * 43758.5453
    return v - math.floor(v)


def cap_fn(base, amp, cell=3.0, salt=0.0, course=0.5):
    """An uneven height over the map: how far the masons have got."""
    def cap(x, y):
        z = base + amp * (jit(math.floor(x / cell), math.floor(y / cell), salt) * 2 - 1)
        return max(course, round(z / course) * course)
    return cap


class W:
    """A MeshBuilder with default bone weights, a placement and an optional
    height cap (a function of world x, y) that cuts the masonry of an
    unfinished stage. The cap assumes a placement that only moves and turns
    around Z."""

    def __init__(self, mb=None, weights=None, m=None, cap=None):
        self.mb = mb if mb is not None else kit.begin()
        self.w = weights
        self.m = m if m is not None else Matrix.Identity(4)
        self.cap = cap

    def bone(self, name):
        return W(self.mb, {name: 1.0}, self.m, self.cap)

    def at(self, dx=0.0, dy=0.0, dz=0.0, rz=0.0):
        m = self.m @ Matrix.Translation((dx, dy, dz)) @ Matrix.Rotation(math.radians(rz), 4, "Z")
        return W(self.mb, self.w, m, self.cap)

    def turn(self, axis, deg):
        return W(self.mb, self.w, self.m @ Matrix.Rotation(math.radians(deg), 4, axis), self.cap)

    def scaled(self, k):
        return W(self.mb, self.w, self.m @ Matrix.Scale(k, 4), self.cap)

    def capped(self, cap):
        return W(self.mb, self.w, self.m, cap)

    def free(self):
        return W(self.mb, self.w, self.m, None)

    def p(self, pt):
        q = self.m @ Vector(pt)
        return (q.x, q.y, q.z)

    def _top(self, x, y):
        if self.cap is None:
            return None
        q = self.m @ Vector((x, y, 0.0))
        return self.cap(q.x, q.y) - self.m[2][3]

    def box(self, c, s, mat, rz=0.0):
        cx, cy, cz = c
        sx, sy, sz = s
        top = self._top(cx, cy)
        if top is not None:
            z0 = cz - sz / 2
            if z0 >= top - 0.05:
                return []
            if cz + sz / 2 > top:
                sz = top - z0
                cz = z0 + sz / 2
        m = (self.m @ Matrix.Translation((cx, cy, cz)) @ Matrix.Rotation(math.radians(rz), 4, "Z")
             @ Matrix.Diagonal((sx, sy, sz, 1.0)))
        r = bmesh.ops.create_cube(self.mb.bm, size=1.0, matrix=m)
        return self.mb._finish(r["verts"], mat, self.w)

    def cyl(self, a, b, r1, r2, mat, seg=8, spin=0.0):
        a, b = Vector(a), Vector(b)
        top = self._top(a.x, a.y)
        if top is not None:
            if abs(a.x - b.x) < 1e-6 and abs(a.y - b.y) < 1e-6 and b.z > a.z:
                if a.z >= top - 0.05:
                    return []
                if b.z > top:
                    t = (top - a.z) / (b.z - a.z)
                    r2 = r1 + (r2 - r1) * t
                    b = Vector((a.x, a.y, top))
            elif max(a.z, b.z) > top:
                return []
        axis = b - a
        rot = Vector((0, 0, 1)).rotation_difference(axis.normalized()).to_matrix().to_4x4()
        m = self.m @ Matrix.Translation((a + b) * 0.5) @ rot @ Matrix.Rotation(math.radians(spin), 4, "Z")
        r = bmesh.ops.create_cone(self.mb.bm, cap_ends=True, cap_tris=False, segments=seg,
                                  radius1=r1, radius2=max(r2, 0.0), depth=axis.length, matrix=m)
        return self.mb._finish(r["verts"], mat, self.w)

    def sphere(self, c, r, mat, seg=10, rings=7, scale=(1, 1, 1)):
        top = self._top(c[0], c[1])
        if top is not None and c[2] + r * scale[2] > top:
            return []
        m = self.m @ Matrix.Translation(Vector(c)) @ Matrix.Diagonal((*scale, 1.0))
        r_ = bmesh.ops.create_uvsphere(self.mb.bm, u_segments=seg, v_segments=rings, radius=r, matrix=m)
        return self.mb._finish(r_["verts"], mat, self.w)

    def solid(self, ring, offset, mat):
        """A flat polygon (3D points) given a thickness along `offset`."""
        top = self._top(ring[0][0], ring[0][1])
        if top is not None and max(p[2] for p in ring) + max(0.0, offset[2]) > top:
            return []
        off = self.m.to_3x3() @ Vector(offset)
        return _shapes.solid(self.mb, [self.m @ Vector(p) for p in ring], off, mat, self.w)

    def prism(self, points, z0, z1, mat):
        """A convex polygon [(x, y)...] extruded from z0 to z1."""
        top = self._top(points[0][0], points[0][1])
        if top is not None:
            if z0 >= top - 0.05:
                return []
            z1 = min(z1, top)
        return _shapes.solid(self.mb, [self.m @ Vector((x, y, z0)) for x, y in points], self.m.to_3x3() @ Vector((0, 0, z1 - z0)), mat, self.w)

    def frustum(self, cx, cy, sx, sy, z0, sx2, sy2, z1, mat, ox=0.0, oy=0.0, rz=0.0):
        """A rectangle sx x sy at z0 joined to a rectangle sx2 x sy2 at z1
        (moved ox, oy). A side of 0 at the top makes a ridge; both, a point."""
        top = self._top(cx, cy)
        if top is not None:
            if z0 >= top - 0.05:
                return []
            if z1 > top:
                t = (top - z0) / (z1 - z0)
                sx2, sy2 = sx + (sx2 - sx) * t, sy + (sy2 - sy) * t
                ox, oy, z1 = ox * t, oy * t, top
        m = self.m @ Matrix.Translation((cx, cy, 0.0)) @ Matrix.Rotation(math.radians(rz), 4, "Z")
        bm = self.mb.bm

        def v(x, y, z):
            return bm.verts.new(m @ Vector((x, y, z)))

        a = [v(-sx / 2, -sy / 2, z0), v(sx / 2, -sy / 2, z0), v(sx / 2, sy / 2, z0), v(-sx / 2, sy / 2, z0)]
        bm.faces.new(list(reversed(a)))
        ex, ey = sx2 > 1e-6, sy2 > 1e-6
        if ex and ey:
            b = [v(ox - sx2 / 2, oy - sy2 / 2, z1), v(ox + sx2 / 2, oy - sy2 / 2, z1), v(ox + sx2 / 2, oy + sy2 / 2, z1), v(ox - sx2 / 2, oy + sy2 / 2, z1)]
            bm.faces.new(b)
            for i in range(4):
                j = (i + 1) % 4
                bm.faces.new((a[i], a[j], b[j], b[i]))
        elif ex:
            b = [v(ox - sx2 / 2, oy, z1), v(ox + sx2 / 2, oy, z1)]
            bm.faces.new((a[0], a[1], b[1], b[0]))
            bm.faces.new((a[1], a[2], b[1]))
            bm.faces.new((a[2], a[3], b[0], b[1]))
            bm.faces.new((a[3], a[0], b[0]))
        elif ey:
            b = [v(ox, oy - sy2 / 2, z1), v(ox, oy + sy2 / 2, z1)]
            bm.faces.new((a[0], a[1], b[0]))
            bm.faces.new((a[1], a[2], b[1], b[0]))
            bm.faces.new((a[2], a[3], b[1]))
            bm.faces.new((a[3], a[0], b[0], b[1]))
        else:
            b = [v(ox, oy, z1)]
            for i in range(4):
                bm.faces.new((a[i], a[(i + 1) % 4], b[0]))
        return self.mb._finish(a + b, mat, self.w)


def staged(w, stage, low, mid, amp=None, salt=0.0, cell=3.0):
    """The builder for the masonry: capped in stages 1 and 2."""
    if stage == 3:
        return w
    if stage == 1:
        return w.capped(cap_fn(low, (amp or (0.5, 0))[0], cell, salt))
    if stage == RUIN:
        return w.capped(cap_fn(mid * 0.95, mid * 0.6, cell * 1.4, salt + 9.0))
    return w.capped(cap_fn(mid, (amp or (0, mid * 0.3))[1], cell, salt + 5.0))


RUIN = 4   # A fourth "stage": what is left after the town falls.


def model_id(base, stage):
    return base + {1: "_stage1", 2: "_stage2", RUIN: "_ruin"}.get(stage, "")


def rubble(w, rnd, sx, sy, n=40, mats=("stone", "stone_dark", "stone_light"), cx=0.0, cy=0.0, z=0.0, moss=True):
    """Fallen blocks, heaps and moss over a ruin's footprint."""
    w = w.free()
    for _ in range(n):
        x, y = cx + rnd.uniform(-0.48, 0.48) * sx, cy + rnd.uniform(-0.48, 0.48) * sy
        s = rnd.uniform(0.5, 1.5)
        w.box((x, y, z + s * 0.3), (s * 1.4, s, s * 0.7), rnd.choice(mats), rz=rnd.uniform(0, 180))
    for _ in range(n // 5):
        x, y = cx + rnd.uniform(-0.45, 0.45) * sx, cy + rnd.uniform(-0.45, 0.45) * sy
        w.sphere((x, y, z), rnd.uniform(1.2, 2.6), rnd.choice(mats), 7, 4, (1.0, 0.8, 0.45))
        if moss:
            w.sphere((x + 0.5, y, z + 0.2), rnd.uniform(0.9, 1.8), "moss", 6, 3, (1.0, 0.9, 0.35))
    if moss:
        for _ in range(n // 6):
            x, y = cx + rnd.uniform(-0.45, 0.45) * sx, cy + rnd.uniform(-0.45, 0.45) * sy
            tree(w, x, y, z, rnd.uniform(0.6, 1.1), rnd)


def vault(w, cx, cy, length, r, z, mats=TILE, n=6, thick=0.3):
    """A barrel vault along X (turn the builder for Y): its springing at z."""
    for i in range(n):
        a0, a1 = math.pi * i / n, math.pi * (i + 1) / n
        am = (a0 + a1) / 2
        w.solid([(cx - length / 2, cy + math.cos(a0) * r, z + math.sin(a0) * r), (cx + length / 2, cy + math.cos(a0) * r, z + math.sin(a0) * r),
                 (cx + length / 2, cy + math.cos(a1) * r, z + math.sin(a1) * r), (cx - length / 2, cy + math.cos(a1) * r, z + math.sin(a1) * r)],
                (0, -math.cos(am) * thick, -math.sin(am) * thick), mats[i % len(mats)])
    for s in (-1, 1):
        w.cyl((cx + s * (length / 2 - 0.15), cy, z), (cx + s * length / 2, cy, z), r - thick * 0.5, r - thick * 0.5, "sand", 12)


# ----------------------------------------------------------------- masonry


def wall(w, a, b, z0, z1, t, mat, seg=2.5, mat2=None):
    """A wall between two points (x, y). Capped, it is cut piece by piece."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy)
    n = max(1, round(length / seg)) if (w.cap is not None or mat2) else 1
    ang = math.degrees(math.atan2(dy, dx))
    for k in range(n):
        u = (k + 0.5) / n
        w.box((a[0] + dx * u, a[1] + dy * u, (z0 + z1) / 2), (length / n + 0.002, t, z1 - z0), mat if (mat2 is None or k % 2 == 0) else mat2, rz=ang)


def block(w, cx, cy, sx, sy, z0, z1, mat, t=0.9):
    """A building volume: solid when finished, four walls while it rises."""
    if w.cap is None:
        w.box((cx, cy, (z0 + z1) / 2), (sx, sy, z1 - z0), mat)
        return
    x0, x1, y0, y1 = cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2
    h = t / 2
    wall(w, (x0, y0 + h), (x1, y0 + h), z0, z1, t, mat)
    wall(w, (x0, y1 - h), (x1, y1 - h), z0, z1, t, mat)
    wall(w, (x0 + h, y0), (x0 + h, y1), z0, z1, t, mat)
    wall(w, (x1 - h, y0), (x1 - h, y1), z0, z1, t, mat)


def drum(w, cx, cy, r, z0, z1, mat, seg=12, t=0.9, r2=None):
    """A round volume: solid when finished, a ring of wall pieces while it rises."""
    r2 = r if r2 is None else r2
    if w.cap is None:
        w.cyl((cx, cy, z0), (cx, cy, z1), r, r2, mat, seg, spin=180.0 / seg)
        return
    for i in range(seg):
        a0, a1 = TAU * i / seg, TAU * (i + 1) / seg
        k = math.cos(math.pi / seg)
        wall(w, (cx + math.cos(a0) * r, cy + math.sin(a0) * r), (cx + math.cos(a1) * r, cy + math.sin(a1) * r), z0, z1, t, mat, seg=99)
        del k


def battlements(w, cx, cy, sx, sy, z, mat, size=0.8, h=0.9):
    for x0, y0, x1, y1 in ((-sx / 2, -sy / 2, sx / 2, -sy / 2), (sx / 2, -sy / 2, sx / 2, sy / 2), (sx / 2, sy / 2, -sx / 2, sy / 2), (-sx / 2, sy / 2, -sx / 2, -sy / 2)):
        n = max(2, round(math.hypot(x1 - x0, y1 - y0) / (size * 2)))
        for k in range(n + 1):
            u = k / n
            w.box((cx + x0 + (x1 - x0) * u, cy + y0 + (y1 - y0) * u, z + h / 2), (size, size, h), mat)


def column(w, x, y, z0, h, r, mat, mat2=None, seg=8):
    mat2 = mat2 or mat
    w.box((x, y, z0 + r * 0.25), (r * 2.8, r * 2.8, r * 0.5), mat2)
    w.cyl((x, y, z0 + r * 0.5), (x, y, z0 + h - r * 0.6), r, r * 0.85, mat, seg)
    w.cyl((x, y, z0 + h - r * 0.6), (x, y, z0 + h - r * 0.25), r * 0.9, r * 1.3, mat2, seg)
    w.box((x, y, z0 + h - r * 0.125), (r * 2.8, r * 2.8, r * 0.25), mat2)


def steps(w, cx, y_top, width, n, rise, run, mat, z0=0.0, mat2=None):
    """Stairs that climb toward +Y; the landing begins at y_top."""
    for i in range(n):
        y0 = y_top - (n - i) * run
        w.box((cx, (y0 + y_top) / 2, z0 + (i + 0.5) * rise), (width, y_top - y0, rise), mat if (mat2 is None or i % 2 == 0) else mat2)


def window(w, wd, h, glass, frame="stone_light", pointed=True, depth=0.14):
    """A pane on a wall face: local origin at the middle of the sill, facing -Y."""
    w.box((0, -depth / 2, h / 2), (wd, depth, h), glass)
    if pointed:
        w.solid([(-wd / 2, 0, h), (wd / 2, 0, h), (0, 0, h + wd * 0.8)], (0, -depth, 0), glass)
    else:
        w.cyl((0, 0, h), (0, -depth * 0.95, h), wd / 2, wd / 2, glass, 10)
    w.box((0, -depth / 2 - 0.03, -0.1), (wd + 0.4, depth + 0.12, 0.2), frame)
    for sx in (-1, 1):
        w.box((sx * (wd / 2 + 0.08), -depth / 2 - 0.02, h / 2), (0.16, depth + 0.06, h), frame)
    if wd > 1.0:
        w.box((0, -depth / 2 - 0.02, h / 2), (0.1, depth + 0.05, h), frame)


def door(w, wd, h, mat="door", frame="stone_light", pointed=True, depth=0.2):
    """A doorway on a wall face, facing -Y, its threshold at the local origin."""
    w.box((0, -depth / 2, h / 2), (wd, depth, h), mat)
    if pointed:
        w.solid([(-wd / 2, 0, h), (wd / 2, 0, h), (0, 0, h + wd * 0.6)], (0, -depth, 0), mat)
        w.solid([(-wd / 2 - 0.3, 0, h), (-wd / 2, 0, h), (0, 0, h + wd * 0.6), (0, 0, h + wd * 0.6 + 0.4)], (0, -depth - 0.1, 0), frame)
        w.solid([(wd / 2 + 0.3, 0, h), (wd / 2, 0, h), (0, 0, h + wd * 0.6), (0, 0, h + wd * 0.6 + 0.4)], (0, -depth - 0.1, 0), frame)
    else:
        w.cyl((0, 0, h), (0, -depth * 0.95, h), wd / 2, wd / 2, mat, 10)
    for sx in (-1, 1):
        w.box((sx * (wd / 2 + 0.15), -depth / 2 - 0.05, h / 2), (0.3, depth + 0.1, h), frame)
    w.box((0, -depth - 0.02, h / 2), (0.08, 0.05, h), "door_dark")
    for sx in (-1, 1):
        w.box((sx * wd * 0.12, -depth - 0.04, h * 0.45), (0.1, 0.08, 0.3), "gold")


def arch(w, cx, r, z_spring, z_top, y0, y1, mat, n=8, ring=None):
    """The wall over a round opening that runs along Y: from the arc up to
    z_top, between y0 and y1. `ring` draws the voussoirs in another material."""
    for i in range(n):
        a0, a1 = math.pi * i / n, math.pi * (i + 1) / n
        p0 = (cx + math.cos(a0) * r, z_spring + math.sin(a0) * r)
        p1 = (cx + math.cos(a1) * r, z_spring + math.sin(a1) * r)
        w.solid([(p0[0], y0, p0[1]), (p1[0], y0, p1[1]), (p1[0], y0, z_top), (p0[0], y0, z_top)], (0, y1 - y0, 0), mat)
        if ring:
            k = (r + 0.4) / r
            q0 = (cx + math.cos(a0) * r * k, z_spring + math.sin(a0) * r * k)
            q1 = (cx + math.cos(a1) * r * k, z_spring + math.sin(a1) * r * k)
            w.solid([(p0[0], y0 - 0.12, p0[1]), (p1[0], y0 - 0.12, p1[1]), (q1[0], y0 - 0.12, q1[1]), (q0[0], y0 - 0.12, q0[1])], (0, y1 - y0 + 0.24, 0), ring)


def arch_panel(w, wd, h, mat="cave", depth=0.1):
    """A dark arched opening painted on a wall face (facing -Y, sill at the local origin)."""
    w.box((0, -depth / 2, h / 2), (wd, depth, h), mat)
    w.cyl((0, 0, h), (0, -depth * 0.95, h), wd / 2, wd / 2, mat, 10)


def tree(w, x, y, z, s, rnd, leaves=("leaf", "leaf_dark", "leaf_light"), trunk="trunk"):
    """A small round tree of height about 3 * s."""
    w.cyl((x, y, z), (x, y, z + 1.6 * s), 0.16 * s, 0.11 * s, trunk, 5)
    w.sphere((x, y, z + 2.2 * s), 0.95 * s, rnd.choice(leaves), 6, 4, (1.0, 1.0, 0.85))
    w.sphere((x + 0.4 * s, y + 0.2 * s, z + 1.8 * s), 0.6 * s, rnd.choice(leaves), 6, 4)


def cypress(w, x, y, z, s, mat="leaf_dark"):
    w.cyl((x, y, z), (x, y, z + 0.5 * s), 0.1 * s, 0.1 * s, "trunk", 5)
    w.cyl((x, y, z + 0.4 * s), (x, y, z + 1.4 * s), 0.34 * s, 0.42 * s, mat, 6)
    w.cyl((x, y, z + 1.4 * s), (x, y, z + 3.4 * s), 0.42 * s, 0.0, mat, 6)


def rose(w, r, mats=GLASS, frame="stone_light", n=12):
    """A rose window facing -Y, centered on the local origin."""
    w.cyl((0, 0.1, 0), (0, -0.2, 0), r * 1.14, r * 1.14, frame, 20)
    for i in range(n):
        a0, a1 = TAU * i / n, TAU * (i + 1) / n
        ring = [(math.cos(a0) * r * 0.28, -0.2, math.sin(a0) * r * 0.28), (math.cos(a0) * r, -0.2, math.sin(a0) * r),
                (math.cos(a1) * r, -0.2, math.sin(a1) * r), (math.cos(a1) * r * 0.28, -0.2, math.sin(a1) * r * 0.28)]
        w.solid(ring, (0, -0.07, 0), mats[i % len(mats)])
        w.cyl((math.cos(a0) * r * 0.25, -0.3, math.sin(a0) * r * 0.25), (math.cos(a0) * r * 1.02, -0.3, math.sin(a0) * r * 1.02), r * 0.035, r * 0.035, frame, 4)
    w.cyl((0, -0.2, 0), (0, -0.36, 0), r * 0.3, r * 0.3, frame, 10)
    w.cyl((0, -0.36, 0), (0, -0.4, 0), r * 0.2, r * 0.2, "gold", 10)


def dome(w, cx, cy, z, r, mat, mat2=None, seg=12, rings=5, k=1.0):
    """A faceted dome of height r * k."""
    for i in range(rings):
        a0, a1 = (math.pi / 2) * i / rings, (math.pi / 2) * (i + 1) / rings
        r1 = r * math.cos(a1)
        w.cyl((cx, cy, z + math.sin(a0) * r * k), (cx, cy, z + math.sin(a1) * r * k), r * math.cos(a0), 0.0 if r1 < 1e-6 else r1,
              mat if (mat2 is None or i % 2 == 0) else mat2, seg, spin=180.0 / seg)


def finial(w, x, y, z, s=1.0, mat="gold"):
    w.cyl((x, y, z), (x, y, z + 1.2 * s), 0.09 * s, 0.05 * s, mat, 6)
    w.sphere((x, y, z + 0.5 * s), 0.28 * s, mat, 8, 5)
    w.cyl((x, y, z + 1.2 * s), (x, y, z + 2.0 * s), 0.13 * s, 0.0, mat, 6)


def roof(w, cx, cy, sx, sy, z, rise, mats=SLATE, over=0.4, rows=4, thick=0.25, gable=None):
    """A gable roof with its ridge along X (turn the builder for Y)."""
    half = sy / 2 + over
    slope = rise / (sy / 2)
    for side in (-1, 1):
        for r in range(rows):
            u0, u1 = r / rows, min(1.0, (r + 1) / rows + 0.04)
            y0, y1 = half * (1 - u0), half * (1 - u1)
            za, zb = z + rise - slope * y0, z + rise - slope * y1
            w.solid([(cx - sx / 2 - over, cy + side * y0, za), (cx + sx / 2 + over, cy + side * y0, za),
                     (cx + sx / 2 + over, cy + side * y1, zb), (cx - sx / 2 - over, cy + side * y1, zb)], (0, 0, thick), mats[r % len(mats)])
    w.box((cx, cy, z + rise + thick * 0.8), (sx + 2 * over + 0.1, thick * 1.8, thick * 1.2), mats[-1])
    if gable:
        for s in (-1, 1):
            w.solid([(cx + s * sx / 2, cy - sy / 2, z), (cx + s * sx / 2, cy + sy / 2, z), (cx + s * sx / 2, cy, z + rise)], (-s * 0.6, 0, 0), gable)


def tent_roof(w, cx, cy, sx, sy, z, rise, mats=SLATE, over=0.3, rows=3):
    """A pyramid roof in bands."""
    for r in range(rows):
        u0, u1 = r / rows, (r + 1) / rows
        w.frustum(cx, cy, (sx + 2 * over) * (1 - u0), (sy + 2 * over) * (1 - u0), z + rise * u0,
                  (sx + 2 * over) * (1 - u1), (sy + 2 * over) * (1 - u1), z + rise * u1, mats[r % len(mats)])


def cone_roof(w, cx, cy, r, z, rise, mats=SLATE, seg=8, rows=3):
    for i in range(rows):
        u0, u1 = i / rows, (i + 1) / rows
        w.cyl((cx, cy, z + rise * u0), (cx, cy, z + rise * u1), r * (1 - u0), r * (1 - u1), mats[i % len(mats)], seg, spin=180.0 / seg)


# ------------------------------------------------------------------ figures


ARMS = {
    "down": ((0.25, 0.0, 0.61), (0.25, -0.03, 0.46)),
    "up": ((0.31, 0.0, 0.9), (0.34, -0.02, 1.07)),
    "fwd": ((0.25, -0.12, 0.7), (0.26, -0.3, 0.74)),
    "front": ((0.23, -0.07, 0.62), (0.06, -0.17, 0.6)),
    "side": ((0.36, 0.0, 0.76), (0.52, 0.0, 0.78)),
    "hip": ((0.33, 0.02, 0.64), (0.2, -0.05, 0.54)),
}


def statue(w, h, mat, arms=("down", "down"), mat2=None, upto=1.0, spread=0.06, robe=False, stocky=1.0,
           crown=False, cape=None, beard=False, legs=True, ears=None, detail=False):
    """A figure of height h at the local origin, facing -Y. `arms` is the
    pose of the arm at +X and at -X. Returns where its hands and head are
    (local coordinates). `upto` builds only that fraction of the height."""
    u, k = h, stocky
    m2 = mat2 or mat
    hip = 0.09 * k
    if legs:
        for s in (-1, 1):
            w.box((s * spread * u, -0.035 * u, 0.02 * u), (0.1 * u * k, 0.19 * u, 0.04 * u), m2)
        if robe:
            zt = min(0.54, upto)
            w.cyl((0, 0, 0.03 * u), (0, 0, zt * u), 0.2 * u * k, (0.2 - 0.07 * zt / 0.54) * u * k, mat, 8)
        else:
            zt = min(0.52, upto)
            f = (zt - 0.03) / 0.49
            for s in (-1, 1):
                x0, x1 = s * spread * u, s * hip * u
                w.cyl((x0, 0, 0.03 * u), (x0 + (x1 - x0) * f, 0, zt * u), 0.06 * u * k, (0.06 + 0.03 * f) * u * k, mat, 7)
                if detail:                                                     # Greaves and knee guards.
                    def leg(t):
                        return (x0 + (x1 - x0) * t, 0, (0.03 + 0.49 * t) * u)
                    if f > 0.4:
                        w.cyl(leg(0.04), leg(0.4), 0.072 * u * k, 0.082 * u * k, m2, 7)
                    if f > 0.56:
                        w.cyl(leg(0.42), leg(0.54), 0.09 * u * k, 0.094 * u * k, mat, 7)
                        w.sphere((leg(0.48)[0], -0.085 * u * k, leg(0.48)[2]), 0.04 * u, "gold", 6, 4)
    out = {"head": (0, 0, 0.92 * u)}
    for side, s in ((0, 1), (1, -1)):
        elbow, hand = ARMS[arms[side]]
        out["hand_r" if s > 0 else "hand_l"] = (s * hand[0] * u * (k if arms[side] in ("down", "up", "side") else 1.0), hand[1] * u, hand[2] * u)
    if upto < 0.6:
        return out
    w.frustum(0, 0, 0.36 * u * k, 0.2 * u, 0.44 * u, 0.3 * u * k, 0.17 * u, 0.58 * u, m2)        # The skirt of the tunic.
    if upto < 0.85:
        return out
    w.frustum(0, 0, 0.29 * u * k, 0.16 * u, 0.56 * u, 0.4 * u * k, 0.2 * u, 0.8 * u, mat)
    w.box((0, 0, 0.575 * u), (0.31 * u * k, 0.18 * u, 0.035 * u), m2)
    w.cyl((0, 0, 0.79 * u), (0, 0, 0.86 * u), 0.05 * u, 0.045 * u, mat, 6)
    w.sphere((0, 0, 0.915 * u), 0.075 * u, mat, 8, 6, (1.0, 1.05, 1.15))
    w.sphere((0, 0.012 * u, 0.94 * u), 0.078 * u, m2, 8, 5, (1.04, 1.05, 0.85))                   # Hair or helmet.
    w.box((0, -0.078 * u, 0.905 * u), (0.022 * u, 0.03 * u, 0.04 * u), mat)                      # A nose, to tell the front.
    if beard:
        w.cyl((0, -0.06 * u, 0.88 * u), (0, -0.1 * u, 0.66 * u), 0.07 * u, 0.0, m2, 6)
    if ears:
        for s in (-1, 1):
            w.cyl((s * 0.05 * u, 0, 0.97 * u), (s * 0.075 * u, 0, 1.07 * u), 0.03 * u, 0.0, ears, 4)
    if crown:
        w.cyl((0, 0, 0.985 * u), (0, 0, 1.01 * u), 0.07 * u, 0.075 * u, "gold", 8)
        for i in range(6):
            a = TAU * i / 6
            w.cyl((math.cos(a) * 0.07 * u, math.sin(a) * 0.07 * u, 1.0 * u), (math.cos(a) * 0.09 * u, math.sin(a) * 0.09 * u, 1.07 * u), 0.014 * u, 0.0, "gold", 4)
    for side, s in ((0, 1), (1, -1)):
        elbow, hand = ARMS[arms[side]]
        kk = k if arms[side] in ("down", "up", "side") else 1.0
        sh = (s * 0.2 * u * k, 0, 0.765 * u)
        e = (s * elbow[0] * u * kk, elbow[1] * u, elbow[2] * u)
        hd = (s * hand[0] * u * kk, hand[1] * u, hand[2] * u)
        w.sphere(sh, 0.068 * u, mat, 6, 4)
        w.cyl(sh, e, 0.05 * u, 0.042 * u, mat, 6)
        w.cyl(e, hd, 0.042 * u, 0.034 * u, mat, 6)
        w.sphere(hd, 0.042 * u, mat, 6, 4)
    if cape:
        w.frustum(0, 0.115 * u, 0.44 * u * k, 0.035 * u, 0.1 * u, 0.36 * u * k, 0.035 * u, 0.8 * u, cape)
    if detail:                                                                 # A breastplate, pauldrons, bracers and a face.
        for s in (-1, 1):
            w.box((s * 0.085 * u * k, -0.092 * u, 0.725 * u), (0.15 * u * k, 0.03 * u, 0.085 * u), m2)
            w.box((s * 0.07 * u * k, -0.088 * u, 0.635 * u), (0.11 * u * k, 0.02 * u, 0.05 * u), m2)
            w.sphere((s * 0.215 * u * k, 0, 0.795 * u), 0.09 * u, m2, 8, 4, (1.15, 1.25, 0.62))
            w.box((s * 0.03 * u, -0.07 * u, 0.925 * u), (0.022 * u, 0.02 * u, 0.012 * u), m2)
            elbow, hand = ARMS[arms[0 if s > 0 else 1]]
            kk = k if arms[0 if s > 0 else 1] in ("down", "up", "side") else 1.0
            e = Vector((s * elbow[0] * u * kk, elbow[1] * u, elbow[2] * u))
            hd = Vector((s * hand[0] * u * kk, hand[1] * u, hand[2] * u))
            w.cyl(e + (hd - e) * 0.35, e + (hd - e) * 0.85, 0.05 * u, 0.045 * u, "gold", 6)
        w.box((0, -0.105 * u, 0.575 * u), (0.1 * u, 0.02 * u, 0.06 * u), "gold")
        for i in range(5):
            w.box(((i - 2) * 0.062 * u * k, -0.1 * u, 0.5 * u), (0.05 * u * k, 0.016 * u, 0.1 * u), mat if i % 2 else m2)
        w.box((0, -0.068 * u, 0.878 * u), (0.04 * u, 0.012 * u, 0.008 * u), m2)
    return out


def sword(w, hand, u, mat="steel", up=False, hilt="gold"):
    """A sword held at `hand`: point down to the ground, or raised."""
    x, y, z = hand
    if up:
        w.box((x, y, z + 0.2 * u), (0.03 * u, 0.012 * u, 0.4 * u), mat)
        w.cyl((x, y, z + 0.4 * u), (x, y, z + 0.46 * u), 0.021 * u, 0.0, mat, 4)
        w.box((x, y, z + 0.01 * u), (0.11 * u, 0.025 * u, 0.02 * u), hilt)
    else:
        w.box((x, y, z / 2 + 0.01 * u), (0.035 * u, 0.012 * u, z - 0.02 * u), mat)
        w.box((x, y, z + 0.0 * u), (0.13 * u, 0.028 * u, 0.022 * u), hilt)
        w.cyl((x, y, z), (x, y, z + 0.07 * u), 0.014 * u, 0.014 * u, hilt, 5)
        w.sphere((x, y, z + 0.08 * u), 0.022 * u, hilt, 5, 3)


def spear(w, hand, u, mat="pole_dark", tip="steel"):
    x, y, z = hand
    w.cyl((x, y, 0), (x, y, 1.12 * u), 0.014 * u, 0.012 * u, mat, 5)
    w.cyl((x, y, 1.12 * u), (x, y, 1.26 * u), 0.03 * u, 0.0, tip, 4)


def shield(w, hand, u, mat="bronze", boss="gold", r=0.15):
    x, y, z = hand
    w.cyl((x, y - 0.03 * u, z + 0.05 * u), (x, y - 0.06 * u, z + 0.05 * u), r * u, r * u, mat, 10)
    w.cyl((x, y - 0.06 * u, z + 0.05 * u), (x, y - 0.085 * u, z + 0.05 * u), r * 0.35 * u, r * 0.1 * u, boss, 8)


def torch(w, hand, u, mat="bronze", s=1.0):
    """A torch bowl over a raised hand; returns where its flame goes."""
    x, y, z = hand
    w.cyl((x, y, z - 0.03 * u), (x, y, z + 0.1 * u), 0.018 * u, 0.022 * u, mat, 6)
    w.cyl((x, y, z + 0.1 * u), (x, y, z + 0.16 * u), 0.025 * u, 0.06 * u * s, mat, 8)
    return (x, y, z + 0.16 * u)


def horse(w, L, mat, mat2=None, rear=False):
    """A horse of body length L at the local origin, facing -Y."""
    m2 = mat2 or mat
    w.cyl((0, 0.36 * L, 0.63 * L), (0, -0.36 * L, 0.65 * L), 0.17 * L, 0.185 * L, mat, 8)
    w.sphere((0, 0.36 * L, 0.63 * L), 0.175 * L, mat, 8, 5)
    w.sphere((0, -0.36 * L, 0.66 * L), 0.19 * L, mat, 8, 5)
    for sx in (-1, 1):
        w.cyl((sx * 0.1 * L, 0.36 * L, 0.56 * L), (sx * 0.11 * L, 0.42 * L, 0.3 * L), 0.065 * L, 0.04 * L, mat, 6)
        w.cyl((sx * 0.11 * L, 0.42 * L, 0.3 * L), (sx * 0.11 * L, 0.4 * L, 0.0), 0.04 * L, 0.034 * L, mat, 6)
    w.cyl((0.1 * L, -0.36 * L, 0.56 * L), (0.1 * L, -0.36 * L, 0.0), 0.055 * L, 0.034 * L, mat, 6)
    w.cyl((-0.1 * L, -0.38 * L, 0.56 * L), (-0.1 * L, -0.56 * L, 0.4 * L), 0.055 * L, 0.04 * L, mat, 6)     # A raised foreleg.
    w.cyl((-0.1 * L, -0.56 * L, 0.4 * L), (-0.1 * L, -0.5 * L, 0.2 * L), 0.04 * L, 0.032 * L, mat, 6)
    w.cyl((0, -0.4 * L, 0.72 * L), (0, -0.6 * L, 1.02 * L), 0.13 * L, 0.08 * L, mat, 7)
    w.cyl((0, -0.57 * L, 1.04 * L), (0, -0.82 * L, 0.9 * L), 0.085 * L, 0.05 * L, mat, 7)
    for sx in (-1, 1):
        w.cyl((sx * 0.045 * L, -0.57 * L, 1.09 * L), (sx * 0.06 * L, -0.56 * L, 1.17 * L), 0.022 * L, 0.0, mat, 4)
    w.solid([(0, -0.38 * L, 0.84 * L), (0, -0.58 * L, 1.12 * L), (0, -0.5 * L, 1.14 * L), (0, -0.3 * L, 0.88 * L)], (0.03 * L, 0, 0), m2)   # The mane.
    w.cyl((0, 0.5 * L, 0.7 * L), (0, 0.66 * L, 0.3 * L), 0.055 * L, 0.02 * L, m2, 6)


def rider(w, L, mat, mat2=None, arms=("up", "down"), crown=False, cape=None):
    """A rider on the horse of horse(w, L...); returns the hands."""
    u = L * 0.95
    r = w.at(0, 0.02 * L, 0.8 * L - 0.5 * u)
    hands = statue(r, u, mat, arms, mat2, legs=False, crown=crown, cape=cape)
    for s in (-1, 1):
        r.cyl((s * 0.09 * u, 0, 0.5 * u), (s * 0.22 * u, -0.1 * u, 0.3 * u), 0.07 * u, 0.055 * u, mat, 6)
        r.cyl((s * 0.22 * u, -0.1 * u, 0.3 * u), (s * 0.22 * u, -0.06 * u, 0.08 * u), 0.055 * u, 0.04 * u, mat, 6)
        r.box((s * 0.22 * u, -0.1 * u, 0.06 * u), (0.08 * u, 0.17 * u, 0.045 * u), mat2 or mat)
    return r, hands, u


# -------------------------------------------------------------- what moves


def flag(w, name, x, y, z0, h, mat, size=1.0, pole="pole_dark", tip="gold"):
    """A pole with a flag of two bones flying toward +X. Returns its bones."""
    w.cyl((x, y, z0), (x, y, z0 + h), 0.07 * size, 0.05 * size, pole, 6)
    w.sphere((x, y, z0 + h + 0.08 * size), 0.13 * size, tip, 6, 4)
    fw, fh = 2.2 * size, 1.3 * size
    zt = z0 + h - 0.1 * size
    t = 0.03 * size
    w.bone(name).box((x + fw * 0.25, y, zt - fh / 2), (fw * 0.5, 2 * t, fh), mat)
    w.bone(name + "_tip").solid([(x + fw * 0.5, y - t, zt), (x + fw, y - t, zt - fh * 0.12), (x + fw * 0.8, y - t, zt - fh * 0.5),
                                 (x + fw, y - t, zt - fh * 0.88), (x + fw * 0.5, y - t, zt - fh)], (0, 2 * t, 0), mat)
    p0, p1, p2 = w.p((x, y, zt - fh / 2)), w.p((x + fw * 0.5, y, zt - fh / 2)), w.p((x + fw, y, zt - fh / 2))
    return [(name, p0, p1, None), (name + "_tip", p1, p2, name)]


def flag_turns(names, t, cycles=2):
    turns = {}
    for i, n in enumerate(names):
        ph = i * 1.3
        turns[n] = [(kit.Z, 14.0 * math.sin(TAU * cycles * t + ph))]
        turns[n + "_tip"] = [(kit.Z, 24.0 * math.sin(TAU * cycles * t + ph - 1.1))]
    return turns


def banner(w, wd, h, mat, trim="gold"):
    """A hanging banner on a wall face, facing -Y, its top at the local origin."""
    w.box((0, -0.06, 0.04), (wd + 0.3, 0.1, 0.1), "pole_dark")
    w.box((0, -0.06, -h * 0.4), (wd, 0.06, h * 0.8), mat)
    w.solid([(-wd / 2, -0.09, -h * 0.8), (wd / 2, -0.09, -h * 0.8), (0, -0.09, -h)], (0, 0.06, 0), mat)
    w.box((0, -0.1, -h * 0.35), (wd * 0.4, 0.04, wd * 0.4), trim, rz=0)


FLAME_BONES = [("flame_a", (0, 0, 0), (0, 0, 1), None), ("flame_b", (0, 0, 0), (0, 0, 1), None)]


def flame(w, x, y, z, s=1.0, mats=("flame", "flame_core")):
    """Tongues of fire that bob with the shared bones flame_a and flame_b."""
    a, b = w.bone("flame_a"), w.bone("flame_b")
    a.cyl((x, y, z - 0.05 * s), (x, y, z + 0.3 * s), 0.2 * s, 0.3 * s, mats[0], 6)
    a.cyl((x, y, z + 0.3 * s), (x, y, z + 1.15 * s), 0.3 * s, 0.0, mats[0], 6)
    b.cyl((x + 0.17 * s, y - 0.12 * s, z), (x + 0.2 * s, y - 0.14 * s, z + 0.7 * s), 0.17 * s, 0.0, mats[1], 5)
    b.cyl((x - 0.2 * s, y + 0.05 * s, z), (x - 0.24 * s, y + 0.05 * s, z + 0.55 * s), 0.15 * s, 0.0, mats[1], 5)
    b.cyl((x + 0.02 * s, y - 0.24 * s, z), (x + 0.02 * s, y - 0.27 * s, z + 0.45 * s), 0.13 * s, 0.0, mats[1], 5)


def flame_moves(t, amp=0.1, cycles=6):
    return {"flame_a": (0, 0, amp * math.sin(TAU * cycles * t)), "flame_b": (amp * 0.3 * math.sin(TAU * cycles * t + 0.7), 0, -amp * math.sin(TAU * cycles * t + 0.5))}


def brazier(w, x, y, z, s=1.0, mat="iron", fire=True, mats=("flame", "flame_core")):
    w.cyl((x, y, z), (x, y, z + 0.12 * s), 0.34 * s, 0.22 * s, mat, 6)
    w.cyl((x, y, z + 0.1 * s), (x, y, z + 0.9 * s), 0.1 * s, 0.08 * s, mat, 6)
    w.cyl((x, y, z + 0.9 * s), (x, y, z + 1.2 * s), 0.2 * s, 0.46 * s, mat, 8)
    w.cyl((x, y, z + 1.17 * s), (x, y, z + 1.22 * s), 0.4 * s, 0.4 * s, "coal", 8)
    if fire:
        flame(w, x, y, z + 1.22 * s, s * 0.85, mats)


def lamp(w, x, y, z, s=1.0, mat="iron", glow="lantern"):
    w.box((x, y, z + 0.03 * s), (0.22 * s, 0.22 * s, 0.06 * s), mat)
    w.box((x, y, z + 0.2 * s), (0.16 * s, 0.16 * s, 0.28 * s), glow)
    w.frustum(x, y, 0.26 * s, 0.26 * s, z + 0.34 * s, 0.0, 0.0, z + 0.5 * s, mat)


# ------------------------------------------------------------ the work yard


def ladder(w, a, b, half=0.22):
    dx, dy = b[0] - a[0], b[1] - a[1]
    flat = math.hypot(dx, dy)
    nx, ny = (1.0, 0.0) if flat < 1e-6 else (-dy / flat, dx / flat)
    for s in (-1, 1):
        w.cyl((a[0] + nx * half * s, a[1] + ny * half * s, a[2]), (b[0] + nx * half * s, b[1] + ny * half * s, b[2]), 0.04, 0.04, "pole", 4)
    n = max(2, int(math.dist(a, b) / 0.4))
    for k in range(n):
        u = (k + 0.5) / n
        p = [a[i] + (b[i] - a[i]) * u for i in range(3)]
        w.cyl((p[0] - nx * half, p[1] - ny * half, p[2]), (p[0] + nx * half, p[1] + ny * half, p[2]), 0.026, 0.026, "pole_dark", 4)


def scaffold_run(w, length, levels, step=2.3, depth=1.4, seed=0):
    """Pole scaffold along local +X from 0 to `length`; the wall is at +Y."""
    w = w.free()
    n = max(1, round(length / 2.7))
    top = levels * step
    for i in range(n + 1):
        x = length * i / n
        for y in (-0.15, -depth):
            w.cyl((x, y, 0), (x, y, top + 1.15), 0.07, 0.055, "pole", 5)
    for lv in range(1, levels + 1):
        z = lv * step
        for y in (-0.15, -depth):
            w.cyl((-0.2, y, z - 0.12), (length + 0.2, y, z - 0.12), 0.05, 0.05, "pole_dark", 4)
        for i in range(n + 1):
            w.cyl((length * i / n, -depth - 0.15, z - 0.05), (length * i / n, 0.3, z - 0.05), 0.045, 0.045, "pole_dark", 4)
        for i in range(n):
            if jit(i, lv, seed) < 0.1:
                continue
            w.box((length * (i + 0.5) / n, -depth / 2 - 0.08, z + 0.03), (length / n - 0.04, depth - 0.2, 0.07), "plank" if (i + lv) % 2 else "plank_light")
        w.cyl((-0.1, -depth, z + 1.0), (length + 0.1, -depth, z + 1.0), 0.035, 0.035, "pole", 4)
    for lv in range(levels):
        for i in range(n):
            if (i + lv) % 2 == 0:
                w.cyl((length * i / n, -depth - 0.07, lv * step + 0.1), (length * (i + 1) / n, -depth - 0.07, (lv + 1) * step - 0.15), 0.04, 0.04, "pole_dark", 4)
        i = (lv * 2 + 1) % n
        ladder(w, (length * (i + 0.25) / n, -depth * 0.55, lv * step + 0.05), (length * (i + 0.75) / n, -depth * 0.55, (lv + 1) * step + 0.6))


def scaffold(w, a, b, levels, z=0.0, **kw):
    """Scaffold along the face a -> b of a wall, standing to the right of
    that direction (walk the outline counter-clockwise to stay outside)."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    scaffold_run(w.at(a[0], a[1], z, math.degrees(math.atan2(dy, dx))), math.hypot(dx, dy), levels, **kw)


def scaffold_box(w, cx, cy, sx, sy, levels, z=0.0, sides="fbrl", **kw):
    x0, x1, y0, y1 = cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2
    if "f" in sides:
        scaffold(w, (x0, y0), (x1, y0), levels, z, **kw)
    if "r" in sides:
        scaffold(w, (x1, y0), (x1, y1), levels, z, **kw)
    if "b" in sides:
        scaffold(w, (x1, y1), (x0, y1), levels, z, **kw)
    if "l" in sides:
        scaffold(w, (x0, y1), (x0, y0), levels, z, **kw)


def scaffold_ring(w, cx, cy, r, levels, n=8, z=0.0, a0=0.0, a1=TAU, **kw):
    for i in range(n):
        u0, u1 = a0 + (a1 - a0) * i / n, a0 + (a1 - a0) * (i + 1) / n
        scaffold(w, (cx + math.cos(u0) * r, cy + math.sin(u0) * r), (cx + math.cos(u1) * r, cy + math.sin(u1) * r), levels, z, **kw)


def crane(w, h=9.0, reach=4.0, load_z=None, load="stone_light"):
    """A treadwheel crane at the local origin, its jib toward -Y."""
    w = w.free()
    for sx in (-1.4, 1.4):
        w.box((sx, 1.0, 0.12), (0.25, 5.6, 0.24), "pole_dark")
    for y in (-1.6, 0.2, 3.6):
        w.box((0, y, 0.3), (3.1, 0.25, 0.2), "pole_dark")
    w.box((0, 0, h * 0.5 + 0.2), (0.36, 0.36, h), "pole")
    for sx in (-1.4, 1.4):
        w.cyl((sx, 0, 0.3), (0, 0, h * 0.6), 0.1, 0.1, "pole_dark", 4)
    w.cyl((0, 3.6, 0.3), (0, 0.1, h * 0.7), 0.1, 0.1, "pole_dark", 4)
    foot, tip = Vector((0, 0.8, h * 0.85)), Vector((0, -reach, h + 2.0))
    w.cyl(foot, tip, 0.15, 0.11, "pole", 4)
    w.cyl((0, -0.1, h * 0.6), foot + (tip - foot) * 0.68, 0.09, 0.09, "pole_dark", 4)
    w.box((0, 0, h + 0.25), (0.46, 0.46, 0.16), "iron")
    for x in (-0.55, 0.55):                                   # The wheel men walk in.
        for i in range(12):
            a0, a1 = TAU * i / 12, TAU * (i + 1) / 12
            w.cyl((x, 2.0 + math.cos(a0) * 1.5, 1.9 + math.sin(a0) * 1.5), (x, 2.0 + math.cos(a1) * 1.5, 1.9 + math.sin(a1) * 1.5), 0.08, 0.08, "plank_dark", 4)
        for i in range(3):
            a = TAU * i / 6
            w.cyl((x, 2.0 + math.cos(a) * 1.5, 1.9 + math.sin(a) * 1.5), (x, 2.0 - math.cos(a) * 1.5, 1.9 - math.sin(a) * 1.5), 0.05, 0.05, "plank", 4)
        w.box((x * 1.75, 2.0, 1.0), (0.2, 0.26, 2.0), "pole")
    for i in range(12):
        a = TAU * (i + 0.5) / 12
        w.box((0, 2.0 + math.cos(a) * 1.5, 1.9 + math.sin(a) * 1.5), (1.1, 0.5, 0.06), "plank_light" if i % 2 else "plank")
    w.cyl((-1.05, 2.0, 1.9), (1.05, 2.0, 1.9), 0.1, 0.1, "pole_dark", 6)
    w.cyl((0, 2.0, 2.1), (0, 0.7, h * 0.9), 0.025, 0.025, "rope", 4)
    w.cyl((0, 0.7, h * 0.9), tip, 0.025, 0.025, "rope", 4)
    lz = h * 0.45 if load_z is None else load_z
    mid = (h + 1.9 + lz + 1.0) / 2                           # The rope seems to shorten: its lower half rides up with the load.
    w.cyl((0, -reach, h + 1.9), (0, -reach, mid), 0.027, 0.027, "rope", 4)
    wl = w.bone("load")
    wl.cyl((0, -reach, mid), (0, -reach, lz + 1.0), 0.025, 0.025, "rope", 4)
    wl.box((0, -reach, lz + 0.35), (1.2, 0.8, 0.7), load)
    for sx in (-1, 1):
        wl.cyl((sx * 0.6, -reach, lz + 0.7), (0, -reach, lz + 1.0), 0.02, 0.02, "rope", 4)
        wl.box((sx * 0.6, -reach, lz + 0.35), (0.04, 0.84, 0.74), "rope")


LOAD_TRAVEL = 2.0   # Meters every crane's load rises in the clip `work`.


def work_moves(t):
    return {"load": (0, 0, LOAD_TRAVEL * (0.5 - 0.5 * math.cos(TAU * t)))}


def stone_pile(w, x, y, rnd, cols=3, rows=2, layers=2, mats=("stone", "stone_light"), size=1.0, rz=0.0):
    w = w.free().at(x, y, 0, rz)
    for layer in range(layers):
        for i in range(cols):
            for j in range(rows):
                if layer == layers - 1 and rnd.random() < 0.35:
                    continue
                w.box(((i - (cols - 1) / 2) * 0.95 * size, (j - (rows - 1) / 2) * 0.65 * size, (0.25 + 0.5 * layer) * size),
                      (0.9 * size, 0.6 * size, 0.48 * size), rnd.choice(mats))


def timber_pile(w, x, y, rz=0.0, n=4, length=5.0):
    w = w.free().at(x, y, 0, rz)
    for layer in range(2):
        for i in range(n - layer):
            yy = (i - (n - layer - 1) / 2) * 0.36
            w.cyl((-length / 2, yy, 0.17 + 0.3 * layer), (length / 2, yy, 0.17 + 0.3 * layer), 0.17, 0.16, "bark", 6)
            w.cyl((length / 2, yy, 0.17 + 0.3 * layer), (length / 2 + 0.02, yy, 0.17 + 0.3 * layer), 0.14, 0.14, "log_end", 6)
            w.cyl((-length / 2 - 0.02, yy, 0.17 + 0.3 * layer), (-length / 2, yy, 0.17 + 0.3 * layer), 0.14, 0.14, "log_end", 6)


def lodge(w, x, y, rz=0.0):
    """The masons' lodge: an open shed with a bench and a block being cut."""
    w = w.free().at(x, y, 0, rz)
    for sx in (-1.8, 1.8):
        w.cyl((sx, -1.2, 0), (sx, -1.2, 2.3), 0.09, 0.08, "pole", 6)
        w.cyl((sx, 1.2, 0), (sx, 1.2, 3.0), 0.09, 0.08, "pole", 6)
    w.solid([(-2.2, -1.6, 2.2), (2.2, -1.6, 2.2), (2.2, 1.5, 3.05), (-2.2, 1.5, 3.05)], (0, 0, 0.12), "plank_dark")
    w.box((0, 1.2, 1.4), (3.6, 0.08, 2.6), "plank")
    w.box((0, 0.4, 0.75), (2.4, 0.8, 0.1), "plank_light")
    for sx in (-1.0, 1.0):
        w.box((sx, 0.4, 0.35), (0.12, 0.7, 0.7), "pole_dark")
    w.box((0.3, 0.4, 1.0), (0.9, 0.55, 0.4), "stone_light")
    w.box((-0.7, 0.4, 0.86), (0.3, 0.1, 0.1), "iron")


def stakes(w, sx, sy, cx=0.0, cy=0.0, gap=4.0):
    """Survey stakes and lines around a rectangle."""
    w = w.free()
    pts = []
    for x0, y0, x1, y1 in ((-sx / 2, -sy / 2, sx / 2, -sy / 2), (sx / 2, -sy / 2, sx / 2, sy / 2), (sx / 2, sy / 2, -sx / 2, sy / 2), (-sx / 2, sy / 2, -sx / 2, -sy / 2)):
        n = max(1, round(math.hypot(x1 - x0, y1 - y0) / gap))
        for k in range(n):
            pts.append((cx + x0 + (x1 - x0) * k / n, cy + y0 + (y1 - y0) * k / n))
    for i, (x, y) in enumerate(pts):
        w.cyl((x, y, 0), (x, y, 0.75), 0.05, 0.04, "pole", 5)
        w.box((x, y, 0.7), (0.12, 0.12, 0.1), "cloth_red")
        nx, ny = pts[(i + 1) % len(pts)]
        w.cyl((x, y, 0.6), (nx, ny, 0.6), 0.015, 0.015, "rope", 4)


def dirt(w, sx, sy, cx=0.0, cy=0.0, mat="soil", rnd=None):
    w = w.free()
    w.box((cx, cy, 0.04), (sx, sy, 0.08), mat)
    if rnd:
        for _ in range(max(3, int(sx * sy / 120))):
            x, y = cx + rnd.uniform(-0.42, 0.42) * sx, cy + rnd.uniform(-0.42, 0.42) * sy
            w.box((x, y, 0.09), (rnd.uniform(1.5, 4.0), rnd.uniform(1.5, 4.0), 0.03), "soil_dark", rz=rnd.uniform(0, 90))


def heap(w, x, y, r, mat="soil_dark"):
    w.free().sphere((x, y, 0.0), r, mat, 8, 5, (1.0, 0.85, 0.5))


def yard(w, stage, rnd, sx, sy, piles=(), timbers=(), lodges=(), cranes=(), heaps=(), cx=0.0, cy=0.0, outline=None, z=0.0):
    """The work yard of stages 1 and 2: trodden earth, stacked stone and
    timber, the lodge and the cranes. `outline` (sx, sy, cx, cy) gets survey
    stakes in stage 1. `z` raises all but the earth (a yard on a platform)."""
    if stage >= 3:
        return
    dirt(w, sx, sy, cx, cy, rnd=rnd)
    w = w.at(0, 0, z)
    for item in piles:
        stone_pile(w, item[0], item[1], rnd, 3, 2, 2 if stage == 1 else 3, size=item[2] if len(item) > 2 else 1.0, rz=item[3] if len(item) > 3 else 0.0)
    for item in timbers:
        timber_pile(w, item[0], item[1], item[2] if len(item) > 2 else 0.0)
    for item in lodges:
        lodge(w, item[0], item[1], item[2] if len(item) > 2 else 0.0)
    for item in cranes:
        if stage == 1 and len(item) > 4 and item[4] == 2:
            continue
        crane(w.at(item[0], item[1], item[5] if len(item) > 5 else 0.0, item[2]), item[3] if stage == 2 else min(item[3], 7.0))
    for item in heaps:
        heap(w, item[0], item[1], item[2])
    if stage == 1 and outline:
        stakes(w, *outline)


def finish(w, name, bones=None, clips=()):
    """Saves the model. `clips` is a list of (name, seconds, pose[, loops]).
    The shared flame bones are added when the model has flames."""
    bones = list(bones or [])
    clips = list(clips)
    known = {b[0] for b in bones}
    for b in FLAME_BONES:
        if b[0] in w.mb.groups and b[0] not in known:
            bones.append(b)
    if "load" in w.mb.groups and "load" not in known:          # A crane at work, in the stages.
        bones.append(("load", (0, 0, 0), (0, 0, 1), None))
        idle = next((c for c in clips if c[0] == "idle"), None)
        if idle is None:
            clips.append(("work", 8.0, lambda t: ({}, work_moves(t))))
        else:
            clips.remove(idle)
            clips.append(("work", 8.0, lambda t, pose=idle[2]: (pose((t * 2) % 1.0)[0], {**pose((t * 2) % 1.0)[1], **work_moves(t)})))
    mech = None
    if bones:
        mech = kit.Mech(bones)
        for clip in clips:
            mech.clip(clip[0], clip[1], clip[2], loops=clip[3] if len(clip) > 3 else True)
    kit.save(w.mb, FAMILY, name, COLORS, mech=mech)
