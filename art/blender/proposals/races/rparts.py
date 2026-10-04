"""Shared parts of the race architecture sets: a builder that places groups
of pieces, the palette of every race, roofs, openings and the moving parts
(flags, hanging lanterns, flames, smoke).

Everything is in meters, Z up, front toward -Y. A piece "on a face" is built
in the face frame: the wall plane is y = 0 and outward is -Y.
"""

import math
import os
import random  # noqa: F401  (the race modules take it from here)
import sys
from contextlib import contextmanager

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import _kit as kit  # noqa: E402
import _shapes  # noqa: E402
import common  # noqa: E402
from _shapes import barrel, crate, log, rock, sack, solid  # noqa: E402,F401
from mathutils import Matrix, Vector  # noqa: E402

FAMILY = "races"
TAU = 2 * math.pi
C = common.rgb


class Builder(common.MeshBuilder):
    """A MeshBuilder whose new parts can be moved as a group and bound to a
    bone by default."""

    def __init__(self):
        super().__init__()
        self._captures = []
        self._stack = []
        self._weights = None

    def _finish(self, geom, mat, weights):
        verts = super()._finish(geom, mat, weights if weights is not None else self._weights)
        for got in self._captures:
            got.extend(verts)
        return verts

    @contextmanager
    def placed(self, origin=(0, 0, 0), rot_z=0.0, matrix=None):
        m = matrix if matrix is not None else (Matrix.Translation(Vector(origin)) @ Matrix.Rotation(rot_z, 4, "Z"))
        got = []
        self._captures.append(got)
        self._stack.append(m)
        try:
            yield
        finally:
            self._captures.pop()
            self._stack.pop()
            for v in set(got):
                v.co = m @ v.co

    @contextmanager
    def bone(self, name):
        old = self._weights
        self._weights = {name: 1.0}
        try:
            yield
        finally:
            self._weights = old

    def world(self, p):
        p = Vector(p)
        for m in reversed(self._stack):
            p = m @ p
        return p

    def world_dir(self, d):
        d = Vector(d)
        for m in reversed(self._stack):
            d = m.to_3x3() @ d
        return d


def begin():
    common.reset_scene()
    return Builder()


class Rig:
    """Collects the bones and clips of the moving parts of a model."""

    def __init__(self):
        self.bones = []
        self.clips = {}
        self._count = {}

    def name(self, base):
        n = self._count.get(base, 0)
        self._count[base] = n + 1
        return base if n == 0 else "%s%d" % (base, n + 1)

    def bone(self, name, head, tail, parent=None):
        self.bones.append((name, tuple(head), tuple(tail), parent))
        return name

    def add(self, clip, seconds, pose, loops=True):
        c = self.clips.setdefault(clip, {"seconds": seconds, "loops": loops, "poses": []})
        c["seconds"] = max(c["seconds"], seconds)
        c["poses"].append(pose)

    def mech(self):
        if not self.bones:
            return None
        mech = kit.Mech(self.bones)
        for clip, c in self.clips.items():
            def pose(t, poses=c["poses"]):
                turns, moves = {}, {}
                for fn in poses:
                    got = fn(t)
                    tr, mv = got if isinstance(got, tuple) else (got, {})
                    turns.update(tr)
                    moves.update(mv)
                return turns, moves
            mech.clip(clip, c["seconds"], pose, loops=c["loops"])
        return mech


def finish(mb, name, rig=None):
    for v in mb.bm.verts:   # Nothing below the ground.
        if v.co.z < 0.0:
            v.co.z = 0.0
    kit.save(mb, FAMILY, name, COLORS, mech=rig.mech() if rig else None)


COLORS = {
    **_shapes.COLORS,
    "dark": C(0x1E1A1C), "window": C(0xF6D070), "fire_win": C(0xF28A30), "ember": C(0xE8502A), "flame": C(0xF2A23A), "smoke": C(0xC8C4C0),
    "water": C(0x4A8FC0), "water_dark": C(0x3A6A9C), "soil": C(0x5A4430), "grass": C(0x6FA83C), "grass_dark": C(0x5A8A34),
    "leaf": C(0x4E9A3C), "leaf_light": C(0x7AB850), "leaf_dark": C(0x3A7A30), "bone": C(0xDCD4BC), "tusk": C(0xECE2C8),
    "bronze": C(0xB08040), "copper": C(0xB8703A), "wood": C(0x8A6038), "wood_dark": C(0x5E3E26), "wood_light": C(0xB48A58),
    "clay": C(0xB8683E), "clay_dark": C(0x8E4E2E), "linen": C(0xE6DCC0), "white": C(0xF0ECE0),
    # Dwarves: grey ashlar, slab roofs, turf, bronze and gold.
    "d_wall": C(0x8E8A84), "d_dark": C(0x66625E), "d_light": C(0xAAA69E), "d_roof": C(0x9E9A92), "d_roof_dark": C(0x7C7872), "d_door": C(0x7A5230),
    "d_rock": C(0x6E6862), "d_rock_dark": C(0x56524E), "d_banner": C(0x8A2A22),
    # Elves: white stone, pale living wood, verdigris leaf roofs.
    "e_white": C(0xECE8DC), "e_white_dark": C(0xCEC8B8), "e_wood": C(0xB48E5C), "e_bark": C(0x7A5636), "e_roof": C(0x3E8E7A), "e_roof_dark": C(0x2E7062),
    "e_roof_light": C(0x5AAA92), "e_door": C(0x2A6E60), "moon": C(0xE2EEFF), "e_blue": C(0x7AC8F0), "flower": C(0xF0A0C0), "flower_w": C(0xF8F4E8),
    # Dark elves: obsidian, violet light, mushrooms.
    "obsidian": C(0x383442), "obsidian_dark": C(0x24202A), "obsidian_light": C(0x524C66), "violet": C(0xC84AF4), "violet_dark": C(0x7A3AA8),
    "cap": C(0x6A46A0), "cap_light": C(0x9470CC), "cap_spot": C(0xDCCCF4), "stalk": C(0xCCC4D6), "stalk_dark": C(0xA8A0B6), "web": C(0xDCDCE8),
    # Orcs: hides, raw logs, bone, red and black.
    "hide": C(0x9A6A44), "hide_dark": C(0x7A5034), "hide_light": C(0xB4845A), "o_red": C(0xB02A1E), "o_black": C(0x2A2426), "o_iron": C(0x4E4C50),
    "o_stone": C(0x76706A), "o_stone_dark": C(0x5C5852), "meat": C(0xA84A3A), "o_mud": C(0x6A5440),
    # Cat-folk: warm stucco, dark timber, green domes, striped awnings.
    "stucco": C(0xEED6A4), "stucco_dark": C(0xD6B47C), "stucco_light": C(0xF8E8C6), "c_timber": C(0x6A4028), "c_dome": C(0x2E8A6E), "c_dome_dark": C(0x246E58),
    "aw_red": C(0xC8382E), "aw_white": C(0xF2EADA), "aw_yellow": C(0xE8C030), "aw_green": C(0x3E9A5A), "aw_blue": C(0x3A5AB8), "terracotta": C(0xC06A3E),
    "terracotta_dark": C(0x9A5230), "fish": C(0xA8B8C4), "sisal": C(0xD2B478),
    # Fox-folk: red posts, white plaster, dark curved tiles, paper lanterns.
    "f_red": C(0xC4302A), "f_red_dark": C(0x8E2420), "f_plaster": C(0xF2ECDC), "f_plaster_dark": C(0xD8D0BC), "f_tile": C(0x3E4A5C), "f_tile_light": C(0x57667E),
    "paper": C(0xFFE6A8), "f_wood": C(0x6A4630), "f_wood_dark": C(0x4A3020), "f_stone": C(0x9C968C), "f_stone_dark": C(0x7A746C), "tea": C(0x6A9A4A),
    "noren": C(0x2E4A8A),
    # Lizard-folk: stepped sandstone, jade, painted bands, feathers, palm.
    "l_stone": C(0xD8C08A), "l_stone_dark": C(0xB89C68), "l_stone_light": C(0xEAD8A8), "jade": C(0x3EA88A), "jade_dark": C(0x2A7E68), "l_red": C(0xC83A2E),
    "l_blue": C(0x2E8AB8), "l_yellow": C(0xE8B830), "palm": C(0xD8B458), "palm_dark": C(0xB8943E), "palm_green": C(0x3E9A4A), "cane": C(0xD6B868),
    "egg": C(0xF0E8D0), "warm": C(0xE8763A),
    # Frog-folk: reeds, moss, water, lily pads.
    "reed": C(0xD8B048), "reed_dark": C(0xB89038), "moss": C(0x5E9A3E), "moss_dark": C(0x4A7E32), "pond": C(0x3E7EB8), "pond_dark": C(0x2E64A0), "lily": C(0x58B04A),
    "lily_dark": C(0x449038), "lily_flower": C(0xF08AB0), "mud": C(0x7A6444), "deck": C(0x9A6A3E), "deck_dark": C(0x7A5230), "cattail": C(0x6A4226),
    "frog_glow": C(0xF8E468), "net": C(0xC8B890),
}


# --- Shapes ------------------------------------------------------------------------------


def prism_xz(mb, pts, y0, y1, mat):
    """A convex polygon given in (x, z), extruded along Y."""
    verts = mb.prism(pts, y0, y1, mat)
    for v in verts:
        v.co = Vector((v.co.x, v.co.z, v.co.y))
    return verts


def prism_yz(mb, pts, x0, x1, mat):
    """A convex polygon given in (y, z), extruded along X."""
    verts = mb.prism(pts, x0, x1, mat)
    for v in verts:
        v.co = Vector((v.co.z, v.co.x, v.co.y))
    return verts


def beam(mb, a, b, t, mat):
    """A square beam from a to b, `t` thick."""
    return mb.cylinder(a, b, t * 0.7, t * 0.7, mat, segments=4)


def tbox(mb, cx, cy, z0, z1, w0, d0, w1, d1, mat, top=(0.0, 0.0)):
    """A box that tapers from w0 x d0 at z0 to w1 x d1 at z1 (battered
    walls, pyramid steps); `top` shifts the upper face."""
    verts = mb.prism([(-w0 / 2, -d0 / 2), (w0 / 2, -d0 / 2), (w0 / 2, d0 / 2), (-w0 / 2, d0 / 2)], z0, z1, mat)
    for v in verts:
        if v.co.z > (z0 + z1) / 2:
            v.co.x *= w1 / w0
            v.co.y *= d1 / d0
            v.co.x += top[0]
            v.co.y += top[1]
        v.co.x += cx
        v.co.y += cy
    return verts


def lathe(mb, x, y, z, profile, mats, seg=10):
    """A turned shape: `profile` is a list of (radius, height) from bottom to
    top; each band takes the next material."""
    for i, ((r0, z0), (r1, z1)) in enumerate(zip(profile, profile[1:])):
        mb.cylinder((x, y, z + z0), (x, y, z + z1), r0, r1, mats[i % len(mats)], segments=seg)


def ring(mb, x, y, z, r, t, mat, seg=12, axis="z"):
    """A ring of square section: around Z, or standing in the XZ plane ("y")."""
    for i in range(seg):
        a0, a1 = TAU * i / seg, TAU * (i + 1) / seg
        if axis == "z":
            beam(mb, (x + math.cos(a0) * r, y + math.sin(a0) * r, z), (x + math.cos(a1) * r, y + math.sin(a1) * r, z), t, mat)
        else:
            beam(mb, (x + math.cos(a0) * r, y, z + math.sin(a0) * r), (x + math.cos(a1) * r, y, z + math.sin(a1) * r), t, mat)


def arc(mb, pts, t, mat, taper=1.0):
    """A bent pole through the points; `taper` is the thickness left at the end."""
    n = len(pts) - 1
    for i in range(n):
        r0 = t * (1 - (1 - taper) * i / n)
        r1 = t * (1 - (1 - taper) * (i + 1) / n)
        mb.cylinder(pts[i], pts[i + 1], r0, r1, mat, segments=6)


def tusk(mb, x, y, z, h, lean_x, lean_y=0.0, r=0.16, mat="tusk", n=5):
    """A curved horn that rises from (x, y, z) and bends by lean at its tip."""
    pts = []
    for i in range(n + 1):
        u = i / n
        pts.append((x + lean_x * u * u, y + lean_y * u * u, z + h * math.sin(u * math.pi / 2)))
    for i in range(n):
        mb.cylinder(pts[i], pts[i + 1], r * (1 - i / n), r * (1 - (i + 1) / n) if i < n - 1 else 0.0, mat, segments=6)


FACE_TURN = {"front": 0.0, "right": math.pi / 2, "back": math.pi, "left": -math.pi / 2}
SIDES = ("front", "right", "back", "left")


@contextmanager
def face(mb, cx, cy, w, d, side, z=0.0):
    """Places what is built inside on one wall of a w x d block; yields the
    wall's length."""
    origin, length = {
        "front": ((cx, cy - d / 2, z), w), "right": ((cx + w / 2, cy, z), d),
        "back": ((cx, cy + d / 2, z), w), "left": ((cx - w / 2, cy, z), d),
    }[side]
    with mb.placed(origin, FACE_TURN[side]):
        yield length


# --- Roofs -------------------------------------------------------------------------------


def hip_roof(mb, cx, cy, z, w, d, h, mats, rows=4, over=0.3, ridge=0.0, power=1.0, lip=0.06):
    """A hipped roof in rows over a w x d block. `power` above 1 sweeps the
    slopes like a pagoda (flat at the eaves, steep at the top); below 1 it
    swells like a bell. `ridge` is the length of the ridge along X."""
    hw, hd = w / 2 + over, d / 2 + over

    def ext(t):
        k = (1 - t) ** power
        return ridge / 2 + (hw - ridge / 2) * k, max(hd * k, 0.002)

    for i in range(rows):
        t0, t1 = i / rows, (i + 1) / rows
        (ax, ay), (bx, by) = ext(t0), ext(t1)
        l = lip if i else 0.0
        tbox(mb, cx, cy, z + h * t0, z + h * t1, 2 * (ax + l), 2 * (ay + l), 2 * max(bx, 0.002), 2 * by, mats[i % len(mats)])
    return z + h


def eave_tips(mb, cx, cy, z, w, d, mat, over=0.3, size=0.5):
    """Upturned corner tips for a swept roof."""
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = cx + sx * (w / 2 + over), cy + sy * (d / 2 + over)
            mb.cylinder((x - sx * size * 0.5, y - sy * size * 0.5, z + 0.03), (x + sx * size * 0.35, y + sy * size * 0.35, z + size * 0.55), 0.09, 0.0, mat, segments=4)


def gable_profile(z, d, rise, over, power=1.0):
    """The height of a gable roof's underside at a distance y from its
    ridge: it passes through the top of the walls (z at y = d / 2) whatever
    the sag, so a swept roof ends up with a higher ridge."""
    half = d / 2 + over
    drop = over * rise / (d / 2)
    lift = z - ((z - drop) + (rise + drop) * (over / half) ** power)

    def zr(y):
        return (z - drop) + (rise + drop) * (max(0.0, 1 - abs(y) / half) ** power) + lift

    return zr


def gable(mb, cx, cy, z, w, d, rise, mats, rows=5, over=0.35, end_over=0.3, axis="x", fill=None, thick=0.1, power=1.0, ridge_mat=None):
    """A two-slope roof whose ridge runs along X (or Y) over a w x d block
    whose walls end at z. `power` above 1 gives the sagging, swept slopes of
    the fox-folk tiles. Returns the ridge height."""
    if axis == "y":
        with mb.placed((cx, cy, 0), math.pi / 2):
            return gable(mb, 0, 0, z, d, w, rise, mats, rows, over, end_over, "x", fill, thick, power, ridge_mat)
    half = d / 2 + over
    zr = gable_profile(z, d, rise, over, power)
    top = zr(0.0)

    def yz(t):
        return half * (1 - t), zr(half * (1 - t))

    for side in (-1, 1):
        for r in range(rows):
            t0, t1 = r / rows, min(1.0, (r + 1) / rows + 0.03)
            (y0, z0), (y1, z1) = yz(t0), yz(t1)
            z0 += 0.05 if r else 0.0
            pts = [(cx - w / 2 - end_over, cy + side * y0, z0), (cx + w / 2 + end_over, cy + side * y0, z0),
                   (cx + w / 2 + end_over, cy + side * y1, z1), (cx - w / 2 - end_over, cy + side * y1, z1)]
            solid(mb, pts if side < 0 else pts[::-1], (0, 0, thick), mats[r % len(mats)])
    if fill:
        n = max(rows, 4)
        for sx in (-1, 1):
            x = cx + sx * (w / 2 - 0.08)
            for side in (-1, 1):
                for r in range(n):
                    t0, t1 = r / n, (r + 1) / n
                    ya, yb = d / 2 * (1 - t0), d / 2 * (1 - t1)
                    za, zb = zr(ya) + 0.02, zr(yb) + 0.02
                    pts = [(cy + side * ya, z - 0.03), (cy + side * yb, z - 0.03), (cy + side * yb, zb), (cy + side * ya, za)]
                    prism_yz(mb, pts if side < 0 else pts[::-1], x - 0.06, x + 0.06, fill)
    mb.box((cx, cy, top + thick * 0.8), (w + 2 * end_over + 0.08, 0.26, 0.16), ridge_mat or mats[-1])
    return top


def cone_roof(mb, x, y, z, r, h, mats, rows=5, seg=12, eave=0.3, power=1.2):
    r0 = r + eave
    for i in range(rows):
        t0, t1 = i / rows, (i + 1) / rows
        ra = r0 * (1 - t0) ** power + (0.06 if i else 0.0)
        rb = r0 * (1 - t1) ** power
        mb.cylinder((x, y, z + h * t0), (x, y, z + h * t1), ra, rb, mats[i % len(mats)], segments=seg)
    return z + h


def dome(mb, x, y, z, r, h, mats, rows=4, seg=12, eave=0.15):
    for i in range(rows):
        a0, a1 = math.pi / 2 * i / rows, math.pi / 2 * (i + 1) / rows
        ra = (r + eave) * math.cos(a0) + (0.04 if i else 0.0)
        rb = (r + eave) * math.cos(a1) if i < rows - 1 else 0.0
        mb.cylinder((x, y, z + h * math.sin(a0)), (x, y, z + h * math.sin(a1)), ra, rb, mats[i % len(mats)], segments=seg)
    return z + h


def onion(mb, x, y, z, r, mats, seg=10, finial="gold"):
    """An onion dome of radius r on a drum top at z; about 2.6 r high."""
    prof = [(r * 0.8, 0), (r * 1.12, r * 0.45), (r * 1.2, r * 0.85), (r * 0.95, r * 1.3), (r * 0.5, r * 1.75), (r * 0.16, r * 2.2), (0.0, r * 2.6)]
    lathe(mb, x, y, z, prof, mats, seg)
    if finial:
        mb.cylinder((x, y, z + r * 2.45), (x, y, z + r * 3.0), 0.04, 0.0, finial, segments=5)
        mb.sphere((x, y, z + r * 2.65), 0.09, finial, segments=6, rings=4)
    return z + r * 2.6


# --- Openings (face frame) ---------------------------------------------------------------


def arch_door(mb, x, z, w=1.0, h=1.7, frame="d_light", door="d_door", metal="gold", depth=0.12):
    hr = h - w / 2
    mb.box((x, -depth / 2 + 0.03, z + hr / 2), (w + 0.3, depth, hr), frame)
    mb.cylinder((x, 0.03, z + hr), (x, -depth + 0.03, z + hr), w / 2 + 0.15, w / 2 + 0.15, frame, segments=10)
    mb.box((x, -depth + 0.0, z + hr / 2), (w, 0.08, hr), door)
    mb.cylinder((x, 0.0, z + hr), (x, -depth - 0.04, z + hr), w / 2, w / 2, door, segments=10)
    if metal:
        for zz in (z + hr * 0.3, z + hr * 0.85):
            mb.box((x, -depth - 0.05, zz), (w, 0.03, 0.08), metal)
        mb.box((x, -depth - 0.05, z + h / 2), (0.04, 0.03, h - 0.1), metal)


def round_door(mb, x, z, r=0.8, frame="f_wood", door="f_red", metal="gold"):
    """A round door whose lowest point is at z."""
    mb.cylinder((x, 0.04, z + r), (x, -0.1, z + r), r + 0.14, r + 0.14, frame, segments=12)
    mb.cylinder((x, 0.0, z + r), (x, -0.15, z + r), r, r, door, segments=12)
    if metal:
        mb.sphere((x, -0.17, z + r), 0.07, metal, segments=6, rings=4)
        mb.box((x, -0.16, z + r), (r * 1.6, 0.02, 0.05), frame)


def pointed_door(mb, x, z, w=1.0, h=2.0, frame="obsidian_light", door="violet"):
    """An ogival opening full of light."""
    prism_xz(mb, [(x - w / 2 - 0.14, z), (x + w / 2 + 0.14, z), (x + w / 2 + 0.14, z + h * 0.62), (x, z + h + 0.2), (x - w / 2 - 0.14, z + h * 0.62)], -0.1, 0.03, frame)
    prism_xz(mb, [(x - w / 2, z), (x + w / 2, z), (x + w / 2, z + h * 0.6), (x, z + h), (x - w / 2, z + h * 0.6)], -0.15, 0.0, door)


def trap_door(mb, x, z, w=1.1, h=1.8, frame="l_stone_light", door="dark", lintel="jade"):
    """A doorway that narrows upward, with a heavy lintel."""
    prism_xz(mb, [(x - w / 2 - 0.2, z), (x + w / 2 + 0.2, z), (x + w * 0.36 + 0.2, z + h + 0.1), (x - w * 0.36 - 0.2, z + h + 0.1)], -0.1, 0.03, frame)
    prism_xz(mb, [(x - w / 2, z), (x + w / 2, z), (x + w * 0.36, z + h), (x - w * 0.36, z + h)], -0.14, 0.0, door)
    mb.box((x, -0.08, z + h + 0.2), (w + 0.7, 0.2, 0.26), lintel)


def win(mb, x, z, w=0.6, h=0.7, frame="d_light", glass="window", cross=True, sill=False):
    """A square window centered at height z."""
    mb.box((x, -0.02, z), (w + 0.18, 0.12, h + 0.18), frame)
    mb.box((x, -0.05, z), (w, 0.1, h), glass)
    if cross:
        mb.box((x, -0.09, z), (0.05, 0.04, h), frame)
        mb.box((x, -0.09, z), (w, 0.04, 0.05), frame)
    if sill:
        mb.box((x, -0.1, z - h / 2 - 0.1), (w + 0.3, 0.22, 0.08), frame)


def round_win(mb, x, z, r=0.32, frame="f_wood", glass="window", cross=True):
    mb.cylinder((x, 0.04, z), (x, -0.08, z), r + 0.09, r + 0.09, frame, segments=10)
    mb.cylinder((x, 0.0, z), (x, -0.11, z), r, r, glass, segments=10)
    if cross:
        mb.box((x, -0.115, z), (0.04, 0.03, r * 2), frame)
        mb.box((x, -0.115, z), (r * 2, 0.03, 0.04), frame)


def slit(mb, x, z, w=0.14, h=0.9, glass="violet", frame=None):
    if frame:
        mb.box((x, -0.01, z), (w + 0.16, 0.08, h + 0.16), frame)
    mb.box((x, -0.03, z), (w, 0.1, h), glass)


def awning(mb, x, z, w=1.6, out=1.0, drop=0.45, mats=("aw_red", "aw_white"), posts=None):
    """A striped cloth that leans out of a face from height z; `posts` is
    the material of two poles that hold its outer edge, or None."""
    n = max(2, round(w / 0.4))
    for i in range(n):
        x0, x1 = x - w / 2 + w * i / n, x - w / 2 + w * (i + 1) / n
        solid(mb, [(x0, 0.0, z), (x1, 0.0, z), (x1, -out, z - drop), (x0, -out, z - drop)], (0, 0, 0.04), mats[i % len(mats)])
        mb.box(((x0 + x1) / 2, -out - 0.01, z - drop - 0.07), (x1 - x0, 0.03, 0.16), mats[i % len(mats)])
    if posts:
        for s in (-1, 1):
            mb.cylinder((x + s * (w / 2 - 0.05), -out + 0.05, 0), (x + s * (w / 2 - 0.05), -out + 0.05, z - drop), 0.04, 0.04, posts, segments=5)


# --- Moving parts ------------------------------------------------------------------------


def flag(mb, rig, x, y, z, pole=2.2, length=1.3, height=0.7, mat="o_red", stripe=None, segs=3, pennant=True, pole_mat="pole_dark", knob="gold"):
    """A pole with a cloth of rigid segments that waves (clip `wave`); the
    cloth flies toward local +X."""
    mb.cylinder((x, y, z), (x, y, z + pole), 0.05, 0.035, pole_mat, segments=6)
    if knob:
        mb.sphere((x, y, z + pole + 0.05), 0.08, knob, segments=6, rings=4)
    base = rig.name("flag")
    zc = z + pole - height / 2 - 0.08
    step = length / segs
    names, parent = [], None
    for k in range(segs):
        name = "%s_%d" % (base, k)
        x0, x1 = x + 0.04 + k * step, x + 0.04 + (k + 1) * step
        h0 = height * (1 - k / segs * 0.85) if pennant else height
        h1 = height * (1 - (k + 1) / segs * 0.85) if pennant else height
        with mb.bone(name):
            prism_xz(mb, [(x0, zc - h0 / 2), (x1 + 0.01, zc - h1 / 2), (x1 + 0.01, zc + h1 / 2), (x0, zc + h0 / 2)], y - 0.02, y + 0.02, mat)
            if stripe:
                prism_xz(mb, [(x0, zc - h0 * 0.14), (x1 + 0.01, zc - h1 * 0.14), (x1 + 0.01, zc + h1 * 0.14), (x0, zc + h0 * 0.14)], y - 0.03, y + 0.03, stripe)
        rig.bone(name, mb.world((x0, y, zc)), mb.world((x1, y, zc)), parent)
        parent = name
        names.append(name)
    phase = (len(rig.bones) * 0.37) % 1.0

    def pose(t):
        return {name: [(kit.Z, (9 + 7 * k) * math.sin(TAU * (2 * t + phase) - k * 1.1))] for k, name in enumerate(names)}

    rig.add("wave", 2.4, pose)


def hang_banner(mb, rig, x, y, z, w=0.8, h=1.8, mat="d_banner", emblem="gold", bar="pole_dark", segs=2):
    """A long cloth hanging from a bar at height z, facing -Y, that sways in
    the wind (clip `wave`)."""
    mb.box((x, y, z + 0.04), (w + 0.3, 0.07, 0.07), bar)
    base = rig.name("banner")
    axis = mb.world_dir((1, 0, 0))
    names, parent = [], None
    step = h / segs
    for k in range(segs):
        name = "%s_%d" % (base, k)
        z1, z0 = z - k * step, z - (k + 1) * step
        with mb.bone(name):
            if k == segs - 1:
                prism_xz(mb, [(x - w / 2, z0 + w * 0.35), (x, z0), (x + w / 2, z0 + w * 0.35), (x + w / 2, z1), (x - w / 2, z1)], y - 0.02, y + 0.02, mat)
            else:
                mb.box((x, y, (z0 + z1) / 2), (w, 0.04, step), mat)
            if emblem and k == 0:
                prism_xz(mb, [(x - w * 0.22, z1 - step * 0.5), (x, z1 - step * 0.5 - w * 0.26), (x + w * 0.22, z1 - step * 0.5), (x, z1 - step * 0.5 + w * 0.26)], y - 0.035, y + 0.035, emblem)
        rig.bone(name, mb.world((x, y, z1)), mb.world((x, y, z0)), parent)
        parent = name
        names.append(name)
    phase = (len(rig.bones) * 0.29) % 1.0

    def pose(t):
        return {name: [(axis, (5 + 5 * k) * math.sin(TAU * (t + phase) - k * 0.9))] for k, name in enumerate(names)}

    rig.add("wave", 3.0, pose)


def hang_lantern(mb, rig, x, y, z, drop=0.35, kind="paper", glow="paper", cap="f_red", size=1.0):
    """A lantern hanging from (x, y, z) that swings (clip `sway`). Kinds:
    paper (round, fox-folk), cage (square), drop (elven), gourd (frog-folk),
    shard (dark-elf crystal)."""
    name = rig.name("lantern")
    s = size
    with mb.bone(name):
        mb.cylinder((x, y, z), (x, y, z - drop), 0.012, 0.012, "rope" if kind != "shard" else "obsidian_light", segments=4)
        zb = z - drop
        if kind == "paper":
            mb.cylinder((x, y, zb), (x, y, zb - 0.05 * s), 0.07 * s, 0.07 * s, cap, segments=8)
            lathe(mb, x, y, zb - 0.4 * s, [(0.08 * s, 0), (0.16 * s, 0.1 * s), (0.16 * s, 0.25 * s), (0.08 * s, 0.35 * s)], (glow,), 8)
            mb.cylinder((x, y, zb - 0.4 * s), (x, y, zb - 0.45 * s), 0.07 * s, 0.07 * s, cap, segments=8)
        elif kind == "cage":
            mb.box((x, y, zb - 0.03 * s), (0.2 * s, 0.2 * s, 0.05 * s), cap)
            mb.box((x, y, zb - 0.17 * s), (0.15 * s, 0.15 * s, 0.24 * s), glow)
            mb.box((x, y, zb - 0.31 * s), (0.2 * s, 0.2 * s, 0.05 * s), cap)
        elif kind == "drop":
            mb.cylinder((x, y, zb), (x, y, zb - 0.14 * s), 0.02, 0.1 * s, cap, segments=6)
            mb.cylinder((x, y, zb - 0.14 * s), (x, y, zb - 0.42 * s), 0.1 * s, 0.0, glow, segments=6)
        elif kind == "gourd":
            mb.sphere((x, y, zb - 0.14 * s), 0.15 * s, glow, segments=7, rings=5, scale=(1, 1, 1.15))
            mb.cylinder((x, y, zb + 0.02), (x, y, zb - 0.04 * s), 0.05 * s, 0.07 * s, cap, segments=6)
        else:
            mb.cylinder((x, y, zb), (x, y, zb - 0.18 * s), 0.0, 0.09 * s, glow, segments=5)
            mb.cylinder((x, y, zb - 0.18 * s), (x, y, zb - 0.5 * s), 0.09 * s, 0.0, glow, segments=5)
    rig.bone(name, mb.world((x, y, z)), mb.world((x, y, z - drop - 0.3)), None)
    phase = (len(rig.bones) * 0.41) % 1.0
    ax, ay = mb.world_dir((1, 0, 0)), mb.world_dir((0, 1, 0))
    rig.add("sway", 3.0, lambda t: {name: [(ax, 9 * math.sin(TAU * (t + phase))), (ay, 5 * math.sin(TAU * (2 * t + phase)))]})


def flame(mb, rig, x, y, z, s=0.3, mats=("ember", "flame")):
    """A fire that flickers (clip `burn`)."""
    name = rig.name("flame")
    with mb.bone(name):
        mb.cylinder((x, y, z), (x, y, z + s * 1.6), s * 0.55, 0.0, mats[0], segments=5)
        mb.cylinder((x + s * 0.1, y, z + s * 0.1), (x - s * 0.1, y + s * 0.1, z + s * 1.1), s * 0.3, 0.0, mats[1], segments=4)
    rig.bone(name, mb.world((x, y, z)), mb.world((x, y, z + s)), None)
    phase = (len(rig.bones) * 0.23) % 1.0
    rig.add("burn", 1.6, lambda t: ({name: [(kit.Z, 360.0 * t), (kit.X, 7 * math.sin(TAU * (3 * t + phase)))]}, {name: (0, 0, s * 0.12 * math.sin(TAU * (2 * t + phase)))}))


def smoke(mb, rig, x, y, z, s=0.3, mat="smoke", n=3):
    """Puffs over a chimney that drift (clip `smoke`)."""
    name = rig.name("smoke")
    with mb.bone(name):
        for k in range(n):
            mb.sphere((x + s * 0.3 * k, y + s * 0.15 * (k % 2), z + s * (0.6 + 1.1 * k)), s * (0.6 + 0.25 * k), mat, segments=6, rings=4)
    rig.bone(name, mb.world((x, y, z)), mb.world((x, y, z + 1.0)), None)
    phase = (len(rig.bones) * 0.31) % 1.0
    rig.add("smoke", 4.0, lambda t: ({name: [(kit.Z, 20 * math.sin(TAU * (t + phase)))]}, {name: (s * 0.3 * math.sin(TAU * (t + phase)), 0, s * 0.5 * math.sin(TAU * (2 * t + phase)))}))


def brazier(mb, rig, x, y, z, s=1.0, mat="bronze", leg="d_dark"):
    """A bowl of fire on a short foot, with its flame."""
    mb.cylinder((x, y, z), (x, y, z + 0.5 * s), 0.1 * s, 0.07 * s, leg, segments=6)
    mb.cylinder((x, y, z + 0.5 * s), (x, y, z + 0.72 * s), 0.12 * s, 0.32 * s, mat, segments=8)
    mb.cylinder((x, y, z + 0.68 * s), (x, y, z + 0.74 * s), 0.28 * s, 0.28 * s, "ember", segments=8)
    flame(mb, rig, x, y, z + 0.72 * s, 0.26 * s)


def spin(mb, rig, name, head, axis, seconds=8.0, clip="turn", tail=None):
    """Declares a bone that turns once around `axis` per loop; build its
    parts inside `with mb.bone(name)`."""
    h = mb.world(head)
    rig.bone(name, h, mb.world(tail) if tail else h + Vector((0, 0, 0.5)), None)
    ax = mb.world_dir(axis)
    rig.add(clip, seconds, lambda t: {name: [(ax, 360.0 * t)]})


def hinge(mb, rig, name, head, axis, degrees, seconds=2.0, clip="open", tail=None):
    """A bone that swings open and stays (clips `open` and `close`)."""
    h = mb.world(head)
    rig.bone(name, h, mb.world(tail) if tail else h + Vector((0, 0, 0.5)), None)
    ax = mb.world_dir(axis)
    rig.add(clip, seconds, lambda t: {name: [(ax, degrees * kit.smooth(t))]}, loops=False)
    rig.add("close", seconds, lambda t: {name: [(ax, degrees * (1 - kit.smooth(t)))]}, loops=False)


def bob(mb, rig, name, head, dz=0.1, seconds=6.0, clip="float", turn=360.0, tail=None):
    """A bone that floats up and down while it turns."""
    h = mb.world(head)
    rig.bone(name, h, mb.world(tail) if tail else h + Vector((0, 0, 0.5)), None)
    rig.add(clip, seconds, lambda t: ({name: [(kit.Z, turn * t)]}, {name: (0, 0, dz * math.sin(TAU * 2 * t))}))


def sway(mb, rig, name, head, degrees=6.0, seconds=4.0, clip="sway", axis=(1, 0, 0), tail=None):
    """A bone that rocks around `axis` (reeds, hanging things)."""
    h = mb.world(head)
    rig.bone(name, h, mb.world(tail) if tail else h + Vector((0, 0, 0.5)), None)
    ax = mb.world_dir(axis)
    phase = (len(rig.bones) * 0.37) % 1.0
    rig.add(clip, seconds, lambda t: {name: [(ax, degrees * math.sin(TAU * (t + phase)))]})


# --- Props -------------------------------------------------------------------------------


def stairs(mb, x, y, z0, z1, w, run, mat, step=0.22):
    """Solid steps climbing toward local +Y from (x, y) at z0 up to z1."""
    n = max(1, round((z1 - z0) / step))
    for i in range(n):
        top = z0 + (i + 1) * (z1 - z0) / n
        mb.box((x, y + (i + 0.5) * run / n, (z0 + top) / 2), (w, run / n + 0.02, top - z0), mat)


def tree(mb, x, y, h=3.0, r=1.0, bark="e_bark", leaves=("leaf", "leaf_light", "leaf_dark"), rnd=None):
    mb.cylinder((x, y, 0), (x, y, h * 0.7), r * 0.16, r * 0.1, bark, segments=6)
    blobs = ((0, 0, h * 0.85, r), (r * 0.5, r * 0.2, h * 0.72, r * 0.7), (-r * 0.5, -r * 0.15, h * 0.75, r * 0.72), (0.1, -r * 0.4, h, r * 0.62))
    for k, (dx, dy, z, rr) in enumerate(blobs):
        mb.sphere((x + dx, y + dy, z), rr, leaves[k % len(leaves)], segments=7, rings=5)


def mushroom(mb, x, y, z, h, r, cap="cap", stalk="stalk", spots="cap_spot", seg=8, under="cap_light"):
    """A mushroom h tall with a cap of radius r."""
    mb.cylinder((x, y, z), (x, y, z + h * 0.72), r * 0.26, r * 0.18, stalk, segments=6)
    mb.cylinder((x, y, z + h * 0.6), (x, y, z + h * 0.72), r * 0.9, r, under, segments=seg)
    lathe(mb, x, y, z + h * 0.72, [(r, 0), (r * 0.8, h * 0.14), (r * 0.42, h * 0.25), (0.0, h * 0.3)], (cap,), seg)
    if spots and r > 0.25:
        for k in range(4):
            a = TAU * k / 4 + 0.6
            mb.sphere((x + math.cos(a) * r * 0.55, y + math.sin(a) * r * 0.55, z + h * 0.72 + h * 0.19), r * 0.13, spots, segments=5, rings=3, scale=(1, 1, 0.5))


def crystal(mb, x, y, z, r, h, mat, lean=(0.0, 0.0), seg=5):
    mx, my = x + lean[0] * h * 0.7, y + lean[1] * h * 0.7
    mb.cylinder((x, y, z), (mx, my, z + h * 0.7), r * 0.8, r, mat, segments=seg)
    mb.cylinder((mx, my, z + h * 0.7), (x + lean[0] * h, y + lean[1] * h, z + h), r, 0.0, mat, segments=seg)


def shard(mb, x, y, z, r, h, mat):
    mb.cylinder((x, y, z - h / 2), (x, y, z), 0.0, r, mat, segments=5)
    mb.cylinder((x, y, z), (x, y, z + h / 2), r, 0.0, mat, segments=5)


def skull(mb, x, y, z, s=0.3, horns=True, mat="bone"):
    """A skull that looks toward -Y."""
    mb.box((x, y, z), (s, s * 0.9, s * 0.8), mat)
    mb.box((x, y - s * 0.1, z - s * 0.5), (s * 0.6, s * 0.6, s * 0.35), mat)
    for sx in (-1, 1):
        mb.box((x + sx * s * 0.22, y - s * 0.46, z + s * 0.02), (s * 0.2, 0.03, s * 0.2), "o_black")
        if horns:
            mb.cylinder((x + sx * s * 0.45, y, z + s * 0.25), (x + sx * s * 1.3, y, z + s * 0.9), s * 0.16, 0.0, mat, segments=5)


def pond(mb, cx, cy, rx, ry, seg=12, rim="mud", water="pond", z=0.0):
    """A pool: a rim of mud and the water just inside it."""
    for r0, r1, z0, z1, mat in ((1.0, 0.96, z, z + 0.1, rim), (0.9, 0.9, z + 0.06, z + 0.13, water)):
        for v in mb.cylinder((0, 0, z0), (0, 0, z1), r0, r1, mat, segments=seg):
            v.co.x = cx + v.co.x * rx
            v.co.y = cy + v.co.y * ry


def lily(mb, x, y, z, r=0.3, flower=False, rot=0.0):
    n = 8
    pts = [(x + math.cos(rot + TAU * i / n) * r, y + math.sin(rot + TAU * i / n) * r) for i in range(n - 1)]
    mb.prism([(x, y)] + pts, z, z + 0.03, "lily" if not flower else "lily_dark")
    if flower:
        mb.cylinder((x, y, z + 0.03), (x, y, z + 0.16), 0.05, 0.13, "lily_flower", segments=6)


def cattail(mb, x, y, z, h=1.6, lean=0.0):
    mb.cylinder((x, y, z), (x + lean, y, z + h), 0.02, 0.015, "moss_dark", segments=4)
    mb.cylinder((x + lean * 0.8, y, z + h * 0.78), (x + lean, y, z + h * 0.96), 0.045, 0.045, "cattail", segments=5)
    mb.cylinder((x + 0.06, y, z), (x + 0.2 + lean, y + 0.05, z + h * 0.7), 0.03, 0.0, "moss", segments=3)


def feathers(mb, x, y, z, s=0.6, mats=("l_red", "l_yellow", "jade", "l_blue")):
    """A fan of feathers standing in the XZ plane."""
    n = len(mats) + 1
    for k in range(n):
        a = math.pi * (0.25 + 0.5 * k / (n - 1))
        mb.cylinder((x, y, z), (x + math.cos(a) * s, y, z + math.sin(a) * s), 0.05 * s + 0.03, 0.0, mats[k % len(mats)], segments=4)


def sun_disc(mb, x, y, z, r, mat="gold", rays=8, face_mat="l_red"):
    """A disc standing in the XZ plane centered at (x, y, z), facing -Y."""
    mb.cylinder((x, y + 0.05, z), (x, y - 0.05, z), r, r, mat, segments=12)
    mb.cylinder((x, y, z), (x, y - 0.09, z), r * 0.55, r * 0.55, face_mat, segments=8)
    mb.cylinder((x, y, z), (x, y - 0.12, z), r * 0.25, r * 0.25, mat, segments=6)
    for k in range(rays):
        a = TAU * k / rays
        mb.cylinder((x + math.cos(a) * r * 0.95, y, z + math.sin(a) * r * 0.95), (x + math.cos(a) * r * 1.45, y, z + math.sin(a) * r * 1.45), r * 0.16, 0.0, mat, segments=4)
