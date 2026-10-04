"""Shared pieces of the `walls` proposal family: a transformable pen over
common.MeshBuilder (so one piece builder can be placed at any grid offset
and turned by 90 degrees), the palette, and small props (brazier, rubble,
scaffold, ladder, door leaves).
"""

import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import _kit as kit  # noqa: E402
import buildings  # noqa: E402
import common  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

FAMILY = "walls"

COLORS = dict(buildings.COLORS)
COLORS.update({
    "stone_light": common.rgb(0xB4AEA4),
    "stone_deep": common.rgb(0x5E5A55),
    "stone_black": common.rgb(0x46444A),
    "brick_dark": common.rgb(0x7E4030),
    "brick_light": common.rgb(0xB8684A),
    "adobe": common.rgb(0xC89A6A),
    "adobe_dark": common.rgb(0xA87C52),
    "adobe_light": common.rgb(0xD8B080),
    "iron_dark": common.rgb(0x2E3136),
    "steel": common.rgb(0x6A7078),
    "rust": common.rgb(0x7A4A32),
    "rope": common.rgb(0xB89A62),
    "moss": common.rgb(0x6A7A48),
    "leaves_dark": common.rgb(0x38602A),
    "leaves_light": common.rgb(0x6A9A40),
    "ember": common.rgb(0xD8501E),
    "flame_core": common.rgb(0xFFE07A),
    "dark": common.rgb(0x1E2024),
    "grass": common.rgb(0x6E8E48),
    "mud": common.rgb(0x54402C),
    "wattle": common.rgb(0x9A7A4A),
    "wattle_dark": common.rgb(0x7A5E38),
    "paint_white": common.rgb(0xE4E0D2),
    # Walls of the fantasy races.
    "granite": common.rgb(0x6E6A72),
    "granite_dark": common.rgb(0x4A4750),
    "granite_light": common.rgb(0x8A8690),
    "marble": common.rgb(0xDAD8CE),
    "marble_dark": common.rgb(0xB0B4A8),
    "obsidian": common.rgb(0x3E3550),
    "obsidian_dark": common.rgb(0x2A2338),
    "obsidian_light": common.rgb(0x574A70),
    "silver": common.rgb(0xB8C0CC),
    "violet": common.rgb(0x7A4AA0),
    "sand": common.rgb(0xD0B080),
    "sand_dark": common.rgb(0xAE8C5C),
    "sand_light": common.rgb(0xE2CC9C),
    "bone": common.rgb(0xDCD4BC),
    "blood": common.rgb(0x8A2A22),
    "bamboo": common.rgb(0xA8B060),
    "bamboo_dark": common.rgb(0x7E8A44),
    "leather": common.rgb(0x7A5236),
    "lacquer": common.rgb(0xA8322A),
    "tile_blue": common.rgb(0x2F6E9A),
    "tile_blue_dark": common.rgb(0x245578),
})

# Rotation (degrees about Z) that takes local +X to a direction (an arm),
# and local -Y to a direction (a closed side of a junction).
ARM_ROT = {"E": 0.0, "N": 90.0, "W": 180.0, "S": 270.0}
SIDE_ROT = {"S": 0.0, "E": 90.0, "N": 180.0, "W": 270.0}


class Pen:
    """A MeshBuilder seen through a transform. With `static`, bone weights
    are dropped (assembled demo models have no skeleton)."""

    def __init__(self, mb, m=None, static=False):
        self.mb = mb
        self.m = Matrix.Identity(4) if m is None else m
        self.static = static

    def at(self, x=0.0, y=0.0, rot=0.0, z=0.0):
        m = self.m @ Matrix.Translation((x, y, z)) @ Matrix.Rotation(math.radians(rot), 4, "Z")
        return Pen(self.mb, m, self.static)

    def _w(self, w):
        return None if self.static else w

    def _tx(self, verts):
        for v in verts:
            v.co = self.m @ v.co
        return verts

    def box(self, c, s, mat, w=None, rz=0.0):
        return self._tx(self.mb.box(c, s, mat, self._w(w), math.radians(rz)))

    def cyl(self, a, b, r1, r2, mat, w=None, seg=8):
        return self._tx(self.mb.cylinder(a, b, r1, r2, mat, self._w(w), segments=seg))

    def sphere(self, c, r, mat, w=None, seg=6, rings=4, scale=(1, 1, 1)):
        return self._tx(self.mb.sphere(c, r, mat, self._w(w), segments=seg, rings=rings, scale=scale))

    def prism(self, pts, z0, z1, mat, w=None):
        return self._tx(self.mb.prism(pts, z0, z1, mat, self._w(w)))

    def xprism(self, pts, x0, x1, mat, w=None):
        """A convex polygon of (y, z) points extruded along X."""
        verts = self.mb.prism(pts, x0, x1, mat, self._w(w))
        for v in verts:
            v.co = Vector((v.co.z, v.co.x, v.co.y))
        return self._tx(verts)

    def yprism(self, pts, y0, y1, mat, w=None):
        """A convex polygon of (x, z) points extruded along Y."""
        verts = self.mb.prism(pts, y0, y1, mat, self._w(w))
        for v in verts:
            v.co = Vector((v.co.x, v.co.z, v.co.y))
        return self._tx(verts)

    def taper(self, c, s0, s1, z0, z1, mat, w=None):
        """A box from z0 to z1 whose rectangle goes from s0 (w, d) at the
        bottom to s1 at the top: battered walls, hipped roofs, pyramids."""
        cx, cy = c
        a, b = s0[0] / 2, s0[1] / 2
        verts = self.mb.prism([(cx - a, cy - b), (cx + a, cy - b), (cx + a, cy + b), (cx - a, cy + b)],
                              z0, z1, mat, self._w(w))
        for v in verts[4:]:
            v.co.x = cx + (v.co.x - cx) * (s1[0] / s0[0])
            v.co.y = cy + (v.co.y - cy) * (s1[1] / s0[1])
        return self._tx(verts)

    def beam(self, a, b, size, mat, w=None):
        """A square-section beam between two points (any direction)."""
        a, b = Vector(a), Vector(b)
        axis = b - a
        rot = Vector((0, 0, 1)).rotation_difference(axis.normalized()).to_matrix().to_4x4()
        m = Matrix.Translation((a + b) * 0.5) @ rot @ Matrix.Diagonal((size, size, axis.length, 1.0))
        import bmesh
        r = bmesh.ops.create_cube(self.mb.bm, size=1.0, matrix=m)
        return self._tx(self.mb._finish(r["verts"], mat, self._w(w)))

    def world(self, pt):
        return tuple(self.m @ Vector(pt))


def rng(*key):
    return random.Random("/".join(str(k) for k in key))


# --- Props ---------------------------------------------------------------------------------


def brazier(p, x, y, z, pole=1.0, bone="flame"):
    """An iron fire basket on a pole; its flame follows `bone`. Returns the
    flame's base (for the bone)."""
    p.cyl((x, y, z), (x, y, z + pole), 0.035, 0.035, "iron", seg=6)
    zb = z + pole
    p.cyl((x, y, zb), (x, y, zb + 0.22), 0.09, 0.2, "iron", seg=8)
    p.cyl((x, y, zb + 0.2), (x, y, zb + 0.26), 0.22, 0.22, "iron_dark", seg=8)
    p.cyl((x, y, zb + 0.24), (x, y, zb + 0.31), 0.17, 0.14, "ember", seg=8)
    w = {bone: 1.0}
    p.cyl((x, y, zb + 0.29), (x, y, zb + 0.68), 0.13, 0.0, "torch_flame", w, seg=6)
    p.cyl((x + 0.05, y + 0.03, zb + 0.29), (x + 0.08, y + 0.03, zb + 0.5), 0.07, 0.0, "flame_core", w, seg=5)
    p.cyl((x - 0.06, y - 0.04, zb + 0.29), (x - 0.09, y - 0.05, zb + 0.46), 0.06, 0.0, "ember", w, seg=5)
    return (x, y, zb + 0.29)


def flame_bones(points):
    """Names and Mech bones of the flames at `points` (flame, flame2...)."""
    names = ["flame"] + ["flame%d" % i for i in range(2, len(points) + 1)]
    return names, [(n, pt, (pt[0], pt[1], pt[2] + 0.3), None) for n, pt in zip(names, points)]


def flame_mech(points, extra=()):
    """A Mech with one flame bone per point and the `flicker` clip."""
    names, bones = flame_bones(points)
    return add_flicker(kit.Mech(bones + list(extra)), names)


def add_flicker(mech, names):
    def pose(t):
        turns, moves = {}, {}
        for i, n in enumerate(names):
            ph = 2 * math.pi * (t + i * 0.37)
            turns[n] = [(kit.Z, 360.0 * t), (kit.X, 9.0 * math.sin(2 * ph)), (kit.Y, 7.0 * math.sin(3 * ph))]
            moves[n] = (0.0, 0.0, 0.025 * math.sin(4 * ph))
        return turns, moves

    mech.clip("flicker", 1.2, pose)
    return mech


def rubble(p, x0, x1, y_half, mats, seed, n=10, size=0.3):
    """Loose blocks scattered at the foot of a wall, on both sides."""
    r = rng("rubble", seed)
    for i in range(n):
        s = size * r.uniform(0.5, 1.0)
        side = -1 if i % 2 else 1
        p.box((r.uniform(x0, x1), side * (y_half + r.uniform(0.05, 0.5)), s * 0.35),
              (s * r.uniform(0.9, 1.5), s, s * 0.7), r.choice(mats), rz=r.uniform(0, 90))


def ladder(p, foot, top, width=0.45, mat="wood"):
    foot, top = Vector(foot), Vector(top)
    axis = (top - foot)
    side = axis.cross(Vector((0, 0, 1)))
    side = side.normalized() * (width / 2) if side.length > 1e-6 else Vector((width / 2, 0, 0))
    for s in (-1, 1):
        p.beam(foot + side * s, top + side * s, 0.06, mat)
    n = max(2, int(axis.length / 0.32))
    for i in range(1, n):
        c = foot + axis * (i / n)
        p.beam(c - side, c + side, 0.045, mat)


def scaffold(p, x0, x1, y_face, height, side=-1):
    """Builders' scaffold along a wall face at y = y_face: poles, ledgers,
    a plank platform at `height`, a diagonal brace and a ladder."""
    y1 = y_face + side * 0.14
    y2 = y_face + side * 0.84
    for x in (x0 + 0.1, (x0 + x1) / 2, x1 - 0.1):
        for y in (y1, y2):
            p.cyl((x, y, 0), (x, y, height + 1.15), 0.05, 0.045, "timber", seg=6)
        p.box((x, (y1 + y2) / 2, height - 0.06), (0.07, abs(y2 - y1) + 0.2, 0.07), "timber")
        if height > 2.4:
            p.box((x, (y1 + y2) / 2, height * 0.5), (0.07, abs(y2 - y1) + 0.2, 0.07), "timber")
    for y in (y1, y2):
        p.box(((x0 + x1) / 2, y, height + 0.95), (x1 - x0, 0.06, 0.06), "wood")
    for i in range(3):
        y = y1 + (y2 - y1) * (0.2 + 0.3 * i)
        p.box(((x0 + x1) / 2, y, height + 0.02), (x1 - x0 + 0.1, 0.2, 0.05), "wood_light" if i % 2 else "wood")
    p.beam((x0 + 0.1, y2, 0.1), ((x0 + x1) / 2, y2, height - 0.1), 0.05, "timber")
    ladder(p, (x1 - 0.45, y2 + side * 0.45, 0.0), (x1 - 0.45, y2 + side * 0.03, height + 0.5))


def door_leaf(p, hinge_x, y, width, height, direction, bone, style="plank", z0=0.05):
    """A door leaf hinged at x = hinge_x, extending `width` toward
    `direction` (+1 or -1 along X). Styles: plank (iron-bound planks),
    iron (plated), bars (five-bar field gate), picket."""
    w = {bone: 1.0}
    xc = hinge_x + direction * width / 2
    zc = z0 + height / 2
    if style in ("plank", "iron"):
        n = max(2, round(width / 0.24))
        for i in range(n):
            bx = hinge_x + direction * (i + 0.5) * width / n
            mat = ("wood" if i % 2 else "door") if style == "plank" else ("iron" if i % 2 else "steel")
            p.box((bx, y, zc), (width / n - 0.015, 0.1, height), mat, w)
        for k, z in enumerate((z0 + height * 0.15, z0 + height * 0.5, z0 + height * 0.85)):
            p.box((xc, y, z), (width, 0.15, 0.11), "iron_dark" if style == "iron" else "iron", w)
            for j in range(4):
                sx = hinge_x + direction * (j + 0.5) * width / 4
                p.box((sx, y, z), (0.07, 0.2, 0.07), "steel" if style == "plank" else "rust", w)
        p.box((hinge_x + direction * width * 0.5, y, z0 + height * 0.675), (width * 0.92, 0.13, 0.07), "timber", w)
        p.cyl((hinge_x + direction * (width - 0.18), y - 0.11, z0 + height * 0.42),
              (hinge_x + direction * (width - 0.18), y - 0.07, z0 + height * 0.42), 0.09, 0.09, "iron_dark", w, seg=8)
    elif style == "bars":
        for z in [z0 + 0.12 + i * (height - 0.2) / 4 for i in range(5)]:
            p.box((xc, y, z), (width, 0.05, 0.08), "wood", w)
        for bx in (hinge_x + direction * 0.05, hinge_x + direction * (width - 0.05)):
            p.box((bx, y, zc), (0.09, 0.08, height), "timber", w)
        p.beam((hinge_x + direction * 0.08, y, z0 + 0.1), (hinge_x + direction * (width - 0.08), y, z0 + height - 0.1),
               0.06, "timber", w)
    elif style == "picket":
        n = max(3, round(width / 0.16))
        for i in range(n):
            bx = hinge_x + direction * (i + 0.5) * width / n
            hh = height * (0.86 + 0.14 * math.sin(math.pi * (i + 0.5) / n))
            p.box((bx, y, z0 + hh / 2), (0.1, 0.035, hh), "paint_white", w)
            p.taper((bx, y), (0.1, 0.035), (0.01, 0.035), z0 + hh, z0 + hh + 0.08, "paint_white", w)
        for z in (z0 + 0.2, z0 + height * 0.7):
            p.box((xc, y + 0.03, z), (width, 0.04, 0.07), "wood_light", w)
    elif style == "ironbars":
        n = max(3, round(width / 0.14))
        for i in range(n):
            bx = hinge_x + direction * (i + 0.5) * width / n
            p.cyl((bx, y, z0), (bx, y, z0 + height), 0.018, 0.018, "iron", w, seg=5)
            p.cyl((bx, y, z0 + height), (bx, y, z0 + height + 0.14), 0.035, 0.0, "iron_dark", w, seg=4)
        for z in (z0 + 0.12, z0 + height - 0.1):
            p.box((xc, y, z), (width, 0.035, 0.05), "iron_dark", w)
    for z in (z0 + height * 0.18, z0 + height * 0.82):  # Hinges.
        p.cyl((hinge_x, y, z - 0.09), (hinge_x, y, z + 0.09), 0.05, 0.05, "iron_dark", w, seg=6)


def door_mech(hinges, angle=100.0, extra=(), seconds=1.6):
    """`hinges` is a list of (bone, (x, y), sign): sign +1 turns the leaf
    counter-clockwise seen from above when it opens."""
    bones = [(name, (x, y, 0.0), (x, y, 1.0), None) for name, (x, y), _ in hinges]
    mech = kit.Mech(bones + list(extra))

    def opened(t):
        return {name: [(kit.Z, sign * angle * kit.smooth(t))] for name, _, sign in hinges}

    mech.clip("open", seconds, opened, loops=False)
    mech.clip("close", seconds, lambda t: opened(1.0 - t), loops=False)
    return mech


def pyramid_roof(p, c, w, d, z, rise, mats=("roof", "roof_dark"), tiers=3, over=0.25):
    """A hipped roof in overlapping tiers of alternating tile colors."""
    for i in range(tiers):
        t0, t1 = i / tiers, (i + 1) / tiers
        s0 = (1 - t0)
        s1 = max(0.02, 1 - t1 - 0.02)
        lip = 0.07 if i else 0.0
        p.taper(c, ((w + 2 * over) * s0 + lip, (d + 2 * over) * s0 + lip), ((w + 2 * over) * s1, (d + 2 * over) * s1),
                z + rise * t0 - (0.04 if i else 0.0), z + rise * t1, mats[i % len(mats)])
    p.cyl((c[0], c[1], z + rise - 0.05), (c[0], c[1], z + rise + 0.35), 0.05, 0.01, "iron", seg=5)


def cone_roof(p, c, r, z, rise, mats=("roof", "roof_dark"), tiers=3, seg=12):
    for i in range(tiers):
        t0, t1 = i / tiers, (i + 1) / tiers
        r0 = r * (1 - t0) + (0.06 if i else 0.0)
        r1 = max(0.0, r * (1 - t1) - 0.03)
        p.cyl((c[0], c[1], z + rise * t0 - (0.04 if i else 0.0)), (c[0], c[1], z + rise * t1), r0, r1,
              mats[i % len(mats)], seg=seg)
    p.cyl((c[0], c[1], z + rise - 0.05), (c[0], c[1], z + rise + 0.4), 0.05, 0.01, "iron", seg=5)


def flag(p, x, y, z, height=1.6, mat="cloth_red", bone=None):
    """A pole with a pennant; with `bone`, the cloth is weighted to it."""
    p.cyl((x, y, z), (x, y, z + height), 0.035, 0.03, "timber", seg=6)
    w = {bone: 1.0} if bone else None
    p.yprism([(x + 0.03, z + height - 0.5), (x + 0.9, z + height - 0.28), (x + 0.03, z + height - 0.04)],
             y - 0.015, y + 0.015, mat, w)
