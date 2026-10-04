"""Shared parts of the elaborate buildings: a builder that can place parts
anywhere, palettes, towers, roofs, battlements, timber framing, windows,
doors, flags and the collector of the moving parts.

Everything is built in local coordinates (meters, Z up, front toward -Y)
and moved into place with `mb.placed(origin, rot_z)`.
"""

import math
import os
import random
import sys
from contextlib import contextmanager

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import _kit as kit  # noqa: E402
import common  # noqa: E402
import buildings as game  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

FAMILY = "buildings"
TAU = 2 * math.pi


# --- Builder -----------------------------------------------------------------------------


class Builder(common.MeshBuilder):
    """A MeshBuilder whose new parts can be captured, moved as a group and
    bound to a bone by default."""

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
        """Everything built inside is turned rot_z about Z and moved to
        origin, or moved by `matrix` if given."""
        m = matrix if matrix is not None else (
            Matrix.Translation(Vector(origin)) @ Matrix.Rotation(rot_z, 4, "Z"))
        got = []
        self._captures.append(got)
        self._stack.append(m)
        try:
            yield
        finally:
            self._captures.pop()
            self._stack.pop()
            for v in got:
                v.co = m @ v.co

    @contextmanager
    def bone(self, name):
        """Everything built inside follows the bone `name`."""
        old = self._weights
        self._weights = {name: 1.0}
        try:
            yield
        finally:
            self._weights = old

    def world(self, p):
        """A local point of the current placement, in model coordinates."""
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
    """Collects the bones and the clips of the moving parts of a model."""

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
        names = [b[0] for b in self.bones]
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
        assert len(set(names)) == len(names), "repeated bone names"
        return mech


def finish(mb, name, colors, rig=None):
    for v in mb.bm.verts:   # Nothing below the ground: boulders, piles and mounds are cut flat at Z = 0.
        if v.co.z < 0.0:
            v.co.z = 0.0
    kit.save(mb, FAMILY, name, colors, mech=rig.mech() if rig else None)


# --- Palettes ----------------------------------------------------------------------------

BASE = dict(game.COLORS)
BASE.update({
    "wall": common.rgb(0xA9A59C), "wall_dark": common.rgb(0x87837A), "wall_light": common.rgb(0xC6C2B8),
    "trim": common.rgb(0xD2CEC2),
    "roof": common.rgb(0x3F5F9E), "roof_dark": common.rgb(0x324B80),
    "banner": common.rgb(0x2F4FA6), "banner2": common.rgb(0xE2C24A),
    "glow": common.rgb(0xF2C860),
    "earth": common.rgb(0x74603F), "earth_dark": common.rgb(0x5C4A30),
    "grass": common.rgb(0x6F9A45), "grass_dark": common.rgb(0x5A8238),
    "rock": common.rgb(0x8A857C), "rock_dark": common.rgb(0x6C6860),
    "water_dark": common.rgb(0x3A6A8C), "foam": common.rgb(0xDCE8EE),
    "plank": common.rgb(0x9A7044), "plank_dark": common.rgb(0x7C5834),
    "rope": common.rgb(0xB89A62), "canvas": common.rgb(0xE4D8B8), "canvas_dark": common.rgb(0xC8B890),
    "moss": common.rgb(0x5E7A40), "crystal": common.rgb(0x7FD6E8), "magic": common.rgb(0x9A6AE0),
    "brass": common.rgb(0xC09A40), "bone": common.rgb(0xE0D8C0), "fur": common.rgb(0x6A5038),
    "tile_red": common.rgb(0xB0503A), "tile_red_dark": common.rgb(0x8E3E2A),
    "shingle": common.rgb(0x7A5A3C), "shingle_dark": common.rgb(0x614530),
    "paving": common.rgb(0x8E887C), "paving_light": common.rgb(0xA29C90),
    "brick_dark": common.rgb(0x844432), "brick_light": common.rgb(0xBE7252),
    "sand": common.rgb(0xD8C08A), "sand_dark": common.rgb(0xC0A872),
    "teal": common.rgb(0x4A7A6C), "teal_dark": common.rgb(0x3A6256),
    "stripe_a": common.rgb(0xB8362E), "stripe_b": common.rgb(0xEFE6D0),
    "bark": common.rgb(0x6A4A2E), "bark_dark": common.rgb(0x523822),
    "leaf": common.rgb(0x4E8A3A), "leaf_dark": common.rgb(0x3C7030), "leaf_light": common.rgb(0x74A848),
    "tusk": common.rgb(0xE6DCC0), "blood": common.rgb(0x8E1C1C), "hide_dark": common.rgb(0x74523A),
    "copper": common.rgb(0x5E9A84), "copper_dark": common.rgb(0x4A7E6C),
    "band": common.rgb(0xB03A30), "white": common.rgb(0xECE8DC), "white_dark": common.rgb(0xD2CCBC),
    "hedge": common.rgb(0x3F6A30), "glass": common.rgb(0x9CC4D8), "purple": common.rgb(0x5B3F8C),
    "purple_dark": common.rgb(0x46306E), "lava": common.rgb(0xF07A28), "ember": common.rgb(0xE84A20),
})


def palette(**roles):
    colors = dict(BASE)
    for key, value in roles.items():
        colors[key] = common.rgb(value) if isinstance(value, int) else colors[value]
    return colors


# Wall and roof colors of the stone buildings.
STONE_BLUE = palette()
SANDSTONE_RED = palette(wall=0xD4BC8C, wall_dark=0xB69C6E, wall_light=0xE6D4AA, trim=0xF0E4C4,
                        roof=0xB4523A, roof_dark=0x8E3E2A, banner=0xB03A30, banner2=0xF0E0B0)
BRICK_SLATE = palette(wall=0xA65A3E, wall_dark=0x844432, wall_light=0xBE7252, trim=0xCFC8B8,
                      roof=0x5A6470, roof_dark=0x46505A, banner=0x3E7A46, banner2=0xE8E4D8)
DARK_EVIL = palette(paving=0x3A3840, paving_light=0x4A4852, wall=0x4C4854, wall_dark=0x36333C, wall_light=0x625E6C, trim=0x2A2830,
                    roof=0x2C2834, roof_dark=0x6A2028, banner=0x8E1C24, banner2=0x1A181C,
                    window=0xE8502A, glow=0xF07030, gold=0x8A8690, door=0x2A2426)
WOOD = palette(wall=0x7A5232, wall_dark=0x5E3E26, wall_light=0x94683E, trim=0xB08A5A,
               roof=0x7A5A3C, roof_dark=0x614530, banner=0xA8403A, banner2=0xE8E4D8)

ROOFS = {
    "tiles": {"roof": 0xB0503A, "roof_dark": 0x8E3E2A},
    "thatch": {"roof": 0xC9A55A, "roof_dark": 0xA8863F},
    "shingles": {"roof": 0x7A5A3C, "roof_dark": 0x614530},
    "slate": {"roof": 0x5A6470, "roof_dark": 0x46505A},
    "blue": {"roof": 0x3F5F9E, "roof_dark": 0x324B80},
}


# --- Basic shapes ------------------------------------------------------------------------


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
    """A square beam from a to b."""
    return mb.cylinder(a, b, t * 0.7, t * 0.7, mat, segments=4)


FACE_TURN = {"front": 0.0, "right": math.pi / 2, "back": math.pi, "left": -math.pi / 2}


@contextmanager
def face(mb, cx, cy, w, d, side):
    """Places what is built inside on one wall of a w x d block: local X runs
    along the wall, the wall plane is y = 0 and outward is -Y. Yields the
    wall's length."""
    origin, length = {
        "front": ((cx, cy - d / 2, 0), w), "right": ((cx + w / 2, cy, 0), d),
        "back": ((cx, cy + d / 2, 0), w), "left": ((cx - w / 2, cy, 0), d),
    }[side]
    with mb.placed(origin, FACE_TURN[side]):
        yield length


SIDES = ("front", "right", "back", "left")


# --- Roofs -------------------------------------------------------------------------------


def cone_roof(mb, x, y, z, r, h, mats=("roof", "roof_dark"), rows=5, seg=12, eave=0.35, power=1.2,
              finial="gold"):
    """A pointed round roof in rings of tiles, a little concave like a
    witch's hat, with a finial. Returns the tip height."""
    r0 = r + eave
    for i in range(rows):
        t0, t1 = i / rows, (i + 1) / rows
        ra = r0 * (1 - t0) ** power + (0.07 if i else 0.0)
        rb = r0 * (1 - t1) ** power
        mb.cylinder((x, y, z + h * t0), (x, y, z + h * t1), ra, rb, mats[i % len(mats)], segments=seg)
    if finial:
        mb.cylinder((x, y, z + h - 0.25), (x, y, z + h + 0.45), 0.05, 0.0, finial, segments=5)
        mb.sphere((x, y, z + h + 0.02), 0.11, finial, segments=6, rings=4)
    return z + h


def pyramid_roof(mb, cx, cy, z, w, d, h, mats=("roof", "roof_dark"), rows=4, overhang=0.3, ridge=0.0,
                 finial=None):
    """A hipped roof over a w x d block in rows of tiles; `ridge` is the
    length of the ridge along X (0 = a pyramid)."""
    hw, hd = w / 2 + overhang, d / 2 + overhang
    for i in range(rows):
        t0, t1 = i / rows, (i + 1) / rows
        lift = 0.06 if i else 0.0
        ax, ay = hw * (1 - t0) + ridge / 2 * t0 + lift, hd * (1 - t0) + lift
        bx, by = hw * (1 - t1) + ridge / 2 * t1, max(hd * (1 - t1), 0.001)
        bx = max(bx, 0.001)
        z0, z1 = z + h * t0, z + h * t1
        verts = mb.prism([(cx - ax, cy - ay), (cx + ax, cy - ay), (cx + ax, cy + ay), (cx - ax, cy + ay)],
                         z0, z1, mats[i % len(mats)])
        for v in verts:
            if v.co.z > (z0 + z1) / 2:
                v.co.x = cx + math.copysign(bx, v.co.x - cx)
                v.co.y = cy + math.copysign(by, v.co.y - cy)
    if finial:
        mb.cylinder((cx, cy, z + h - 0.2), (cx, cy, z + h + 0.5), 0.05, 0.0, finial, segments=5)
        mb.sphere((cx, cy, z + h + 0.05), 0.11, finial, segments=6, rings=4)
    return z + h


def gable_roof(mb, cx, cy, w, d, z, rise, mats=("roof", "roof_dark"), rows=6, overhang=0.4, gable="wall",
               thick=0.1, barge="timber", end_overhang=None):
    """A two-slope roof with its ridge along X over a w x d block whose walls
    end at z. Rows of tiles overlap like a saw. Returns the ridge height."""
    eo = overhang if end_overhang is None else end_overhang
    half = d / 2 + overhang
    z_eave = z - overhang * rise / (d / 2)
    top = z + rise

    def zz(t):
        return z_eave + (top - z_eave) * t

    for side in (-1, 1):
        for r in range(rows):
            t0, t1 = r / rows, min(1.0, (r + 1) / rows + 0.02)
            game.sloped_slab(mb, cx - w / 2 - eo, cx + w / 2 + eo, cy + side * half * (1 - t0),
                             cy + side * half * (1 - t1), zz(t0) + (0.07 if r else 0.0), zz(t1), thick,
                             mats[r % len(mats)])
    if gable:
        for x in (cx - w / 2, cx + w / 2):
            s = 1 if x > cx else -1
            prism_yz(mb, [(cy - d / 2, z - 0.02), (cy + d / 2, z - 0.02), (cy, top)], x - 0.12 * (s > 0), x + 0.12 * (s < 0),
                     gable)
    if barge:
        for x in (cx - w / 2 - eo, cx + w / 2 + eo):
            for side in (-1, 1):
                prism_yz(mb, [(cy + side * half, z_eave - 0.1), (cy + side * half, z_eave + 0.12),
                              (cy, top + 0.12), (cy, top - 0.1)][::side], x - 0.05, x + 0.05, barge)
    mb.box((cx, cy, top + 0.08), (w + 2 * eo + 0.06, 0.24, 0.14), mats[-1])
    return top


def dome(mb, x, y, z, r, h, mats=("roof", "roof_dark"), rows=4, seg=12, finial=None, eave=0.2):
    """A rounded cap in rings (the cap of a windmill, an onion roof)."""
    for i in range(rows):
        a0, a1 = math.pi / 2 * i / rows, math.pi / 2 * (i + 1) / rows
        ra = (r + eave) * math.cos(a0) + (0.05 if i else 0.0)
        rb = (r + eave) * math.cos(a1) if i < rows - 1 else 0.0
        mb.cylinder((x, y, z + h * math.sin(a0)), (x, y, z + h * math.sin(a1)), ra, rb, mats[i % len(mats)],
                    segments=seg)
    if finial:
        mb.cylinder((x, y, z + h - 0.1), (x, y, z + h + 0.5), 0.05, 0.0, finial, segments=5)
        mb.sphere((x, y, z + h + 0.05), 0.11, finial, segments=6, rings=4)
    return z + h


def turn_x(origin, angle):
    """A matrix that turns `angle` about the X axis through `origin`."""
    o = Vector(origin)
    return Matrix.Translation(o) @ Matrix.Rotation(angle, 4, "X") @ Matrix.Translation(-o)


def turn_y(origin, angle):
    o = Vector(origin)
    return Matrix.Translation(o) @ Matrix.Rotation(angle, 4, "Y") @ Matrix.Translation(-o)


def dormer(mb, x, y, z, w=1.0, h=0.9, depth=1.2, mats=("roof", "roof_dark"), walls="wall", glass="window"):
    """A small gabled window standing on a roof slope, facing -Y, with its
    sill at (x, y, z); it runs back `depth` into the roof."""
    mb.box((x, y + depth / 2, z + h / 2), (w, depth, h), walls)
    mb.box((x, y - 0.03, z + h * 0.5), (w * 0.6, 0.06, h * 0.6), glass)
    with mb.placed((x, y + depth / 2, 0), math.pi / 2):
        gable_roof(mb, 0, 0, depth, w, z + h, w * 0.45, mats, rows=2, overhang=0.12, gable=walls, barge=None,
                   thick=0.06)


def chimney(mb, x, y, z0, z1, w=0.7, mat="wall", cap="wall_dark", pots=1):
    mb.box((x, y, (z0 + z1) / 2), (w, w, z1 - z0), mat)
    mb.box((x, y, z1 - 0.3), (w + 0.12, w + 0.12, 0.12), cap)
    mb.box((x, y, z1 + 0.05), (w + 0.16, w + 0.16, 0.12), cap)
    for i in range(pots):
        px = x + (i - (pots - 1) / 2) * 0.3
        mb.cylinder((px, y, z1 + 0.1), (px, y, z1 + 0.4), 0.11, 0.09, "clay", segments=6)


# --- Stone work --------------------------------------------------------------------------


def scatter_face(mb, rnd, L, z0, z1, mats=("wall_dark", "wall_light"), density=0.22, size=(0.55, 0.28)):
    """Stones that stand a little proud of a wall face (local face frame)."""
    n = int(L * (z1 - z0) * density)
    for _ in range(n):
        w = size[0] * rnd.uniform(0.7, 1.3)
        h = size[1] * rnd.uniform(0.8, 1.2)
        x = rnd.uniform(-L / 2 + w / 2 + 0.1, L / 2 - w / 2 - 0.1) if L > w + 0.3 else 0
        z = rnd.uniform(z0 + h, z1 - h)
        mb.box((x, 0, z), (w, 0.07, h), rnd.choice(mats))


def stone_block(mb, cx, cy, z0, w, d, h, rnd, wall="wall", dark="wall_dark", light="wall_light", quoins=True,
                plinth=0.6, density=0.22, band=None):
    """A masonry block with a plinth, corner stones and loose proud stones."""
    mb.box((cx, cy, z0 + h / 2), (w, d, h), wall)
    if plinth:
        mb.box((cx, cy, z0 + plinth / 2), (w + 0.3, d + 0.3, plinth), dark)
        mb.box((cx, cy, z0 + plinth + 0.05), (w + 0.16, d + 0.16, 0.1), light)
    if quoins:
        n = int(h / 0.45)
        for sx in (-1, 1):
            for sy in (-1, 1):
                for k in range(n):
                    a, b = (0.55, 0.3) if k % 2 else (0.3, 0.55)
                    z = z0 + (k + 0.5) * h / n
                    if z < z0 + plinth + 0.2:
                        continue
                    mb.box((cx + sx * (w / 2 - a / 2 + 0.035), cy + sy * (d / 2 - b / 2 + 0.035), z),
                           (a, b, h / n * 0.9), light)
    for side in SIDES:
        with face(mb, cx, cy, w, d, side) as L:
            scatter_face(mb, rnd, L - 1.0, z0 + plinth + 0.2, z0 + h - 0.2, (dark, light), density)
    for z in band or ():
        mb.box((cx, cy, z), (w + 0.14, d + 0.14, 0.14), light)


def battlements(mb, cx, cy, z, w, d, mat="wall", dark="wall_dark", merlon=0.6, gap=0.5, low=0.5, high=0.65,
                thick=0.3, out=0.25, sides=SIDES, floor=True):
    """A crenellated parapet around the top of a w x d block, corbelled out."""
    W, D = w + 2 * out, d + 2 * out
    if out > 0:
        mb.box((cx, cy, z - 0.2), (W, D, 0.25), dark)
        mb.box((cx, cy, z - 0.42), (w + out, d + out, 0.2), mat)
    if floor:
        mb.box((cx, cy, z - 0.04), (W, D, 0.08), dark)
    for side in sides:
        with face(mb, cx, cy, W, D, side) as L:
            crenels(mb, L, z, mat, merlon, gap, low, high, thick)


def crenels(mb, L, z, mat="wall", merlon=0.6, gap=0.5, low=0.5, high=0.65, thick=0.3, cap=None):
    """A parapet along local X centered on 0, just inside the y = 0 plane."""
    mb.box((0, thick / 2, z + low / 2), (L, thick, low), mat)
    n = max(2, int((L + gap) / (merlon + gap)))
    step = (L - merlon) / (n - 1)
    for i in range(n):
        x = -L / 2 + merlon / 2 + i * step
        mb.box((x, thick / 2, z + low + high / 2), (merlon, thick, high), mat)
        if cap:
            mb.box((x, thick / 2, z + low + high + 0.04), (merlon + 0.08, thick + 0.08, 0.08), cap)


def round_battlements(mb, x, y, z, r, mat="wall", dark="wall_dark", low=0.5, high=0.65, thick=0.3, out=0.3,
                      count=None, seg=14):
    """A corbelled crenellated ring on top of a round tower of radius r."""
    R = r + out
    mb.cylinder((x, y, z - 0.55), (x, y, z - 0.1), r, R, mat, segments=seg)
    mb.cylinder((x, y, z - 0.1), (x, y, z), R, R, dark, segments=seg)
    n = count or max(8, 2 * int(TAU * R / 2.0 / 0.62))
    n += n % 2
    width = 2 * (R - thick / 2) * math.tan(math.pi / n) + 0.06
    for i in range(n):
        a = TAU * i / n
        hh = low + high if i % 2 == 0 else low
        mb.box((x + (R - thick / 2) * math.cos(a), y + (R - thick / 2) * math.sin(a), z + hh / 2),
               (thick, width, hh), mat, rotation_z=a)
    for i in range(0, n, 2):  # Corbels under the merlons.
        a = TAU * i / n
        mb.box((x + (R - 0.12) * math.cos(a), y + (R - 0.12) * math.sin(a), z - 0.35), (0.3, 0.3, 0.3), dark,
               rotation_z=a)


def round_tower(mb, x, y, r, h, rnd, wall="wall", dark="wall_dark", light="wall_light", seg=14, z0=0.0,
                plinth=True, slits=3, bands=True, density=0.2, taper=0.0):
    """The shaft of a round tower from z0 to z0 + h."""
    mb.cylinder((x, y, z0), (x, y, z0 + h), r + taper, r, wall, segments=seg)
    if plinth:
        mb.cylinder((x, y, z0), (x, y, z0 + 0.9), r + taper + 0.3, r + taper + 0.08, dark, segments=seg)
    if bands:
        for z in (z0 + h * 0.45, z0 + h * 0.8):
            mb.cylinder((x, y, z - 0.07), (x, y, z + 0.07), r + 0.06, r + 0.06, light, segments=seg)
    n = int(TAU * r * h * density)
    for _ in range(n):
        a = rnd.uniform(0, TAU)
        z = z0 + rnd.uniform(1.0 if plinth else 0.3, h - 0.5)
        w = rnd.uniform(0.35, 0.6)
        rr = (r + taper * (1 - (z - z0) / h)) * math.cos(math.pi / seg) + 0.01
        mb.box((x + rr * math.cos(a), y + rr * math.sin(a), z), (0.16, w, rnd.uniform(0.22, 0.32)),
               rnd.choice((dark, light)), rotation_z=a)
    for i in range(slits):
        a = -math.pi / 2 + (i - (slits - 1) / 2) * (TAU / max(slits, 3)) + 0.0
        z = z0 + h * (0.35 + 0.22 * (i % 3))
        arrow_slit_round(mb, x, y, r, a, z)


def arrow_slit_round(mb, x, y, r, a, z, h=1.0, frame="trim", dark="window"):
    c, s = math.cos(a), math.sin(a)
    mb.box((x + (r - 0.04) * c, y + (r - 0.04) * s, z), (0.2, 0.42, h + 0.2), frame, rotation_z=a)
    mb.box((x + (r + 0.0) * c, y + (r + 0.0) * s, z), (0.2, 0.16, h), dark, rotation_z=a)


def arrow_slit(mb, x, z, h=1.0, frame="trim", dark="window"):
    """On a wall face (local face frame)."""
    mb.box((x, -0.02, z), (0.42, 0.1, h + 0.2), frame)
    mb.box((x, -0.05, z), (0.16, 0.1, h), dark)


def arch_wall(mb, w, d, h, open_w, open_h, mat="wall", inner="wall_dark", seg=5, z0=0.0):
    """A wall w wide, d thick and h high (centered, local frame) with an
    arched passage through it along Y."""
    side = (w - open_w) / 2
    for s in (-1, 1):
        mb.box((s * (open_w / 2 + side / 2), 0, z0 + h / 2), (side, d, h), mat)
    R = open_w / 2
    spring = open_h - R
    mb.box((0, 0, z0 + (open_h + h) / 2), (open_w, d, h - open_h), mat)
    for s in (-1, 1):
        for k in range(seg):
            a0 = math.pi / 2 * k / seg
            a1 = math.pi / 2 * (k + 1) / seg
            x0, zq0 = s * R * math.cos(a0), z0 + spring + R * math.sin(a0)
            x1, zq1 = s * R * math.cos(a1), z0 + spring + R * math.sin(a1)
            prism_xz(mb, [(x0, zq0), (x1, zq1), (x1, z0 + open_h), (x0, z0 + open_h)], -d / 2, d / 2, inner)


def arch_trim(mb, x, y, z0, open_w, open_h, mat="trim", t=0.25, depth=0.12, seg=5):
    """Voussoirs around an arched opening on the plane y, facing -Y."""
    R = open_w / 2
    spring = open_h - R
    for s in (-1, 1):
        mb.box((x + s * (R + t / 2), y - depth / 2 + 0.02, z0 + spring / 2), (t, depth, spring), mat)
        for k in range(seg):
            a0 = math.pi / 2 * k / seg
            a1 = math.pi / 2 * (k + 1) / seg
            pts = [(x + s * R * math.cos(a0), z0 + spring + R * math.sin(a0)),
                   (x + s * (R + t) * math.cos(a0), z0 + spring + (R + t) * math.sin(a0)),
                   (x + s * (R + t) * math.cos(a1), z0 + spring + (R + t) * math.sin(a1)),
                   (x + s * R * math.cos(a1), z0 + spring + R * math.sin(a1))]
            prism_xz(mb, pts, y - depth + 0.02, y + 0.02, mat)
    mb.box((x, y - depth / 2, z0 + open_h + t / 2), (t * 0.9, depth + 0.06, t + 0.14), mat)  # Keystone.


# --- Windows and doors (on a wall face: plane y = 0, outward -Y) -----------------------


def arched_window(mb, x, z, w=0.7, h=1.5, frame="trim", glass="window", bars=True, sill=True):
    """An arched window with its sill at height z."""
    hr = h - w / 2
    mb.box((x, -0.03, z + hr / 2), (w + 0.22, 0.12, hr), frame)
    mb.cylinder((x, 0.03, z + hr), (x, -0.09, z + hr), w / 2 + 0.11, w / 2 + 0.11, frame, segments=10)
    mb.box((x, -0.07, z + hr / 2 + 0.03), (w, 0.1, hr - 0.06), glass)
    mb.cylinder((x, 0.0, z + hr), (x, -0.12, z + hr), w / 2, w / 2, glass, segments=10)
    if bars:
        mb.box((x, -0.12, z + h / 2), (0.05, 0.04, h - 0.05), frame)
        mb.box((x, -0.12, z + hr), (w, 0.04, 0.05), frame)
    if sill:
        mb.box((x, -0.1, z - 0.06), (w + 0.36, 0.24, 0.12), frame)


def arched_door(mb, x, z, w=1.2, h=2.2, frame="trim", door="door", iron="iron"):
    hr = h - w / 2
    mb.box((x, -0.03, z + hr / 2), (w + 0.3, 0.14, hr), frame)
    mb.cylinder((x, 0.04, z + hr), (x, -0.1, z + hr), w / 2 + 0.15, w / 2 + 0.15, frame, segments=10)
    mb.box((x, -0.08, z + hr / 2), (w, 0.1, hr), door)
    mb.cylinder((x, 0.0, z + hr), (x, -0.13, z + hr), w / 2, w / 2, door, segments=10)
    for zz in (z + hr * 0.25, z + hr * 0.8):
        mb.box((x, -0.14, zz), (w, 0.03, 0.09), iron)
    mb.box((x, -0.14, z + h / 2), (0.04, 0.03, h - 0.1), iron)
    mb.sphere((x + w * 0.2, -0.16, z + hr * 0.5), 0.06, iron, segments=5, rings=3)


def window(mb, x, z, w=0.7, h=0.8, frame="timber", glass="window", shutter="shutter", flowers=False, lit=False):
    """A square window with a cross, shutters and maybe a flower box; z is
    the height of its center."""
    mb.box((x, -0.02, z), (w + 0.18, 0.12, h + 0.18), frame)
    mb.box((x, -0.05, z), (w, 0.1, h), "glow" if lit else glass)
    mb.box((x, -0.09, z), (0.05, 0.04, h), frame)
    mb.box((x, -0.09, z), (w, 0.04, 0.05), frame)
    if shutter:
        for s in (-1, 1):
            mb.box((x + s * (w / 2 + 0.22), -0.05, z), (0.3, 0.06, h + 0.1), shutter)
            mb.box((x + s * (w / 2 + 0.22), -0.09, z), (0.3, 0.03, 0.06), frame)
    if flowers:
        mb.box((x, -0.18, z - h / 2 - 0.12), (w + 0.2, 0.24, 0.18), "wood")
        for i in range(3):
            mb.sphere((x + (i - 1) * w * 0.33, -0.2, z - h / 2 + 0.02), 0.13,
                      ("flowers", "leaves", "flowers_y")[i], segments=5, rings=3)


def plank_door(mb, x, z, w=0.95, h=1.6, frame="timber", door="door", iron="iron", double=False):
    mb.box((x, -0.02, z + h / 2 + 0.05), (w + 0.2, 0.12, h + 0.1), frame)
    mb.box((x, -0.06, z + h / 2), (w, 0.1, h), door)
    for zz in (z + h * 0.22, z + h * 0.78):
        mb.box((x, -0.115, zz), (w, 0.03, 0.08), iron)
    if double:
        mb.box((x, -0.115, z + h / 2), (0.05, 0.03, h), frame)
    else:
        mb.sphere((x + w * 0.32, -0.13, z + h * 0.5), 0.05, iron, segments=5, rings=3)


# --- Timber framing ----------------------------------------------------------------------


def timber_face(mb, L, z0, z1, t=0.14, spacing=1.3, braces=True, rail=True, cross=False, mat="timber"):
    """Posts, plates, a rail and braces on a wall face (local face frame)."""
    n = max(1, round(L / spacing))
    xs = [-L / 2 + L * i / n for i in range(n + 1)]
    for x in xs:
        mb.box((x, 0, (z0 + z1) / 2), (t, t, z1 - z0), mat)
    for z in (z0 + t / 2, z1 - t / 2):
        mb.box((0, 0, z), (L + t, t * 1.1, t), mat)
    zm = (z0 + z1) / 2
    if rail:
        mb.box((0, 0, zm), (L, t * 0.8, t * 0.8), mat)
    if braces and n >= 2:
        for xa, xb in ((xs[0], xs[1]), (xs[-1], xs[-2])):
            za, zb = (z0 + t, zm) if rail else (z0 + t, z1 - t)
            pts = [(xb - t / 2, za), (xb + t / 2, za), (xa + t / 2, zb), (xa - t / 2, zb)]
            if xa > xb:
                pts = pts[::-1]
            prism_xz(mb, pts, -t * 0.4, t * 0.4, mat)
    if cross and rail:
        for i in range(1, n - 1):
            xa, xb = xs[i], xs[i + 1]
            for p, q in (((xa, zm), (xb, z1 - t)), ((xb, zm), (xa, z1 - t))):
                pts = [(p[0] - t * 0.35, p[1]), (p[0] + t * 0.35, p[1]), (q[0] + t * 0.35, q[1]),
                       (q[0] - t * 0.35, q[1])]
                if q[0] < p[0]:
                    pts = pts[::-1]
                prism_xz(mb, pts, -t * 0.35, t * 0.35, mat)


def framed_block(mb, cx, cy, z0, w, d, h, infill="plaster", mat="timber", spacing=1.3, cross=False, t=0.14):
    """A plastered storey with its timber frame on the four faces."""
    mb.box((cx, cy, z0 + h / 2), (w, d, h), infill)
    for side in SIDES:
        with face(mb, cx, cy, w, d, side) as L:
            timber_face(mb, L, z0, z0 + h, t=t, spacing=spacing, cross=cross, mat=mat)


def log_block(mb, cx, cy, z0, w, d, h, log="log", end="log_end", r=0.17, fill="timber"):
    """Walls of stacked logs whose ends cross at the corners."""
    mb.box((cx, cy, z0 + h / 2), (w - 0.1, d - 0.1, h), fill)
    n = max(1, int(h / (2 * r * 0.92)))
    step = h / n
    for i in range(n):
        z = z0 + (i + 0.5) * step
        for y in (cy - d / 2, cy + d / 2):
            mb.cylinder((cx - w / 2 - 0.3, y, z), (cx + w / 2 + 0.3, y, z), r, r, log, segments=6)
            for s in (-1, 1):
                mb.cylinder((cx + s * (w / 2 + 0.29), y, z), (cx + s * (w / 2 + 0.32), y, z), r * 0.75, r * 0.75,
                            end, segments=6)
        zz = z + step / 2 if i < n - 1 else z - step / 2
        for x in (cx - w / 2, cx + w / 2):
            mb.cylinder((x, cy - d / 2 - 0.3, zz), (x, cy + d / 2 + 0.3, zz), r, r, log, segments=6)
            for s in (-1, 1):
                mb.cylinder((x, cy + s * (d / 2 + 0.29), zz), (x, cy + s * (d / 2 + 0.32), zz), r * 0.75,
                            r * 0.75, end, segments=6)


def plank_block(mb, cx, cy, z0, w, d, h, mat="plank", dark="plank_dark", post="timber", step=0.5):
    """Walls of vertical boards with posts at the corners."""
    mb.box((cx, cy, z0 + h / 2), (w, d, h), mat)
    for side in SIDES:
        with face(mb, cx, cy, w, d, side) as L:
            n = int(L / step)
            for i in range(1, n):
                mb.box((-L / 2 + i * L / n, 0, z0 + h / 2), (0.05, 0.05, h), dark)
            for x in (-L / 2, L / 2):
                mb.box((x, 0, z0 + h / 2), (0.16, 0.16, h), post)
            for z in (z0 + 0.08, z0 + h - 0.08):
                mb.box((0, 0, z), (L, 0.12, 0.14), post)


# --- Flags, signs and other moving parts -------------------------------------------------


def flag(mb, rig, x, y, z, pole=2.2, length=1.5, height=0.7, mat="banner", stripe="banner2", segs=3,
         pennant=True, speed=1.0):
    """A pole with a cloth of rigid segments that waves (clip `wave`). The
    cloth flies toward local +X."""
    mb.cylinder((x, y, z), (x, y, z + pole), 0.05, 0.035, "timber", segments=6)
    mb.sphere((x, y, z + pole + 0.05), 0.08, "gold", segments=6, rings=4)
    base = rig.name("flag")
    zc = z + pole - height / 2 - 0.08
    step = length / segs
    names = []
    parent = None
    for k in range(segs):
        name = "%s_%d" % (base, k)
        x0, x1 = x + 0.04 + k * step, x + 0.04 + (k + 1) * step
        h0 = height * (1 - k / segs * 0.85) if pennant else height
        h1 = height * (1 - (k + 1) / segs * 0.85) if pennant else height
        with mb.bone(name):
            prism_xz(mb, [(x0, zc - h0 / 2), (x1 + 0.01, zc - h1 / 2), (x1 + 0.01, zc + h1 / 2), (x0, zc + h0 / 2)],
                     y - 0.02, y + 0.02, mat)
            if stripe:
                prism_xz(mb, [(x0, zc - h0 * 0.14), (x1 + 0.01, zc - h1 * 0.14), (x1 + 0.01, zc + h1 * 0.14),
                              (x0, zc + h0 * 0.14)], y - 0.028, y + 0.028, stripe)
        head = mb.world((x0, y, zc))
        tail = mb.world((x1, y, zc))
        rig.bone(name, head, tail, parent)
        parent = name
        names.append(name)
    phase = (len(rig.bones) * 0.37) % 1.0
    cycles = 2

    def pose(t):
        out = {}
        for k, name in enumerate(names):
            amp = 9 + 7 * k
            out[name] = [(kit.Z, amp * math.sin(TAU * (cycles * t + phase) - k * 1.1))]
        return out

    rig.add("wave", 2.4 / speed, pose)
    return names


def wall_banner(mb, x, z, w=0.9, h=2.2, mat="banner", stripe="banner2"):
    """A long banner hanging flat on a wall face (local face frame); z is
    its top."""
    mb.box((x, -0.1, z + 0.04), (w + 0.3, 0.07, 0.07), "timber")
    prism_xz(mb, [(x - w / 2, z - h + 0.35), (x, z - h), (x + w / 2, z - h + 0.35), (x + w / 2, z), (x - w / 2, z)],
             -0.12, -0.08, mat)
    if stripe:
        prism_xz(mb, [(x - w * 0.2, z - h * 0.55), (x, z - h * 0.55 - w * 0.25), (x + w * 0.2, z - h * 0.55),
                      (x, z - h * 0.55 + w * 0.25)], -0.14, -0.07, stripe)


def portcullis(mb, rig, x, y, z0, w, h, mat="iron", name="portcullis"):
    """An iron grille that closes a gate w x h; clips `open` and `close`
    (it rises into the wall above)."""
    name = rig.name(name)
    with mb.bone(name):
        n = max(3, int(w / 0.36))
        for i in range(n + 1):
            bx = x - w / 2 + w * i / n
            mb.box((bx, y, z0 + h / 2 + 0.1), (0.08, 0.08, h - 0.2), mat)
            mb.cylinder((bx, y, z0 + 0.22), (bx, y, z0), 0.06, 0.0, mat, segments=4)
        m = max(2, int(h / 0.55))
        for j in range(1, m + 1):
            mb.box((x, y, z0 + h * j / m - 0.1), (w, 0.06, 0.08), mat)
    head = mb.world((x, y, z0))
    rig.bone(name, head, head + Vector((0, 0, 1)), None)
    rig.add("open", 3.0, lambda t: ({}, {name: (0, 0, (h - 0.25) * kit.smooth(t))}), loops=False)
    rig.add("close", 2.0, lambda t: ({}, {name: (0, 0, (h - 0.25) * (1 - kit.smooth(t)))}), loops=False)
    return name


def hanging_sign(mb, rig, x, y, z, arm=1.1, board=(0.9, 0.7), emblem="gold", board_mat="wood_light"):
    """A bracket sticking out along local +X from (x, y, z) with a board
    hanging under it that swings (clip `swing`)."""
    mb.box((x + arm / 2, y, z), (arm, 0.08, 0.08), "iron")
    beam(mb, (x, y, z - 0.5), (x + arm * 0.6, y, z - 0.03), 0.05, "iron")
    name = rig.name("sign")
    bx = x + arm - board[0] / 2 - 0.05
    with mb.bone(name):
        for s in (-1, 1):
            mb.box((bx + s * board[0] * 0.35, y, z - 0.12), (0.03, 0.03, 0.2), "iron")
        mb.box((bx, y, z - 0.2 - board[1] / 2), (board[0], 0.06, board[1]), board_mat)
        mb.box((bx, y, z - 0.2 - board[1] / 2), (board[0] + 0.08, 0.04, board[1] + 0.08), "timber")
        mb.cylinder((bx, y - 0.05, z - 0.2 - board[1] / 2), (bx, y + 0.05, z - 0.2 - board[1] / 2),
                    board[1] * 0.3, board[1] * 0.3, emblem, segments=8)
    head = mb.world((bx, y, z - 0.03))
    tail = mb.world((bx, y, z - 0.6))
    axis = mb.world_dir((1, 0, 0))
    rig.bone(name, head, tail, None)
    rig.add("swing", 2.4, lambda t: {name: [(axis, 13 * math.sin(TAU * t))]})
    return name


# --- Props -------------------------------------------------------------------------------


def stairs(mb, x, y, z0, z1, w, run, mat="wall_dark", step=0.25, solid=True):
    """Steps climbing toward local +Y from (x, y) at z0 up to z1."""
    n = max(1, round((z1 - z0) / step))
    for i in range(n):
        top = z0 + (i + 1) * (z1 - z0) / n
        yy = y + (i + 0.5) * run / n
        if solid:
            mb.box((x, yy, (z0 + top) / 2), (w, run / n + 0.02, top - z0), mat)
        else:
            mb.box((x, yy, top - 0.05), (w, run / n + 0.06, 0.1), mat)


def table(mb, x, y, w=1.4, d=0.8, benches=True):
    mb.box((x, y, 0.74), (w, d, 0.07), "wood")
    for sx in (-1, 1):
        mb.box((x + sx * (w / 2 - 0.15), y, 0.36), (0.09, d * 0.7, 0.72), "timber")
    if benches:
        for sy in (-1, 1):
            mb.box((x, y + sy * (d / 2 + 0.3), 0.42), (w, 0.28, 0.06), "wood")
            for sx in (-1, 1):
                mb.box((x + sx * (w / 2 - 0.2), y + sy * (d / 2 + 0.3), 0.2), (0.07, 0.24, 0.4), "timber")
    mb.cylinder((x - 0.2, y, 0.78), (x - 0.2, y, 0.94), 0.07, 0.07, "wood_light", segments=6)
    mb.cylinder((x + 0.3, y + 0.1, 0.78), (x + 0.3, y + 0.1, 0.94), 0.07, 0.07, "wood_light", segments=6)


def well(mb, x, y, roof=("roof", "roof_dark")):
    mb.cylinder((x, y, 0), (x, y, 0.85), 0.85, 0.8, "wall", segments=10)
    mb.cylinder((x, y, 0.8), (x, y, 0.87), 0.9, 0.9, "wall_light", segments=10)
    mb.cylinder((x, y, 0.86), (x, y, 0.88), 0.62, 0.62, "water", segments=10)
    for s in (-1, 1):
        mb.box((x + s * 0.8, y, 1.45), (0.12, 0.12, 1.3), "timber")
    mb.cylinder((x - 0.85, y, 1.75), (x + 0.85, y, 1.75), 0.07, 0.07, "wood", segments=6)
    gable_roof(mb, x, y, 1.7, 1.3, 2.1, 0.6, roof, rows=2, overhang=0.15, gable=None, barge=None, thick=0.07)


def hay_bale(mb, x, y, z=0.0, r=0.35, w=0.6):
    mb.cylinder((x - w / 2, y, z + r), (x + w / 2, y, z + r), r, r, "hay", segments=8)


def rocks(mb, rnd, x, y, r, n=6, mats=("rock", "rock_dark"), size=0.5):
    for _ in range(n):
        a, rr = rnd.uniform(0, TAU), rnd.uniform(0, r)
        s = size * rnd.uniform(0.5, 1.2)
        mb.sphere((x + rr * math.cos(a), y + rr * math.sin(a), s * 0.25), s, rnd.choice(mats), segments=6, rings=4,
                  scale=(1, rnd.uniform(0.7, 1.0), 0.6))
