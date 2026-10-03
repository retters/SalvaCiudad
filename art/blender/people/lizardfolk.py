"""Lizardfolk: a green lizard person with a crest of teal spikes, a snout,
a yellow chest and belly, a red scarf, a grey pauldron on the right
shoulder, a leather harness, bracers, a belt with a tan loincloth over dark
trousers, grey knee guards, leg wraps, clawed feet and a long ridged tail.

This module also holds the helpers shared by the characters of the same
reference picture (orc, knight_man, knight_woman and mage import them from
here): faceted hulls and shells, spikes, straps laid on the body's surface,
belts, cloth (skirts, collars, capes), the angular head with its face, and
the skeleton that makes armor and cloth follow the right bones (FolkRig).
"""

import contextlib
import functools
import math
import random

import bmesh
from mathutils import Matrix, Quaternion, Vector

import common
import rigs_human
import studies
from _human import Human
from _people_kit import along, hull, part_distance, strip, sym, sym_y, tone_faces
from rigs import Bone, Pose, X, Z, smooth

# ------------------------------------------------------------ shared helpers


def blob(mb, center, radii, mat, count=12, seed=1, keep=None, rotate=None):
    """A faceted lump: the hull of points scattered on an ellipsoid. `keep`
    filters the points (a cap of hair: only those above the hairline);
    `rotate` is (axis, degrees), turning the lump around its center."""
    center = Vector(center)
    pts = studies.ellipsoid_points((0.0, 0.0, 0.0), radii, count, random.Random(seed))
    if rotate is not None:
        m = Matrix.Rotation(math.radians(rotate[1]), 3, Vector(rotate[0]).normalized())
        pts = [m @ p for p in pts]
    pts = [p + center for p in pts]
    if keep is not None:
        pts = [p for p in pts if keep(p)]
    return hull(mb, pts, mat)


def spike(mb, root, tip, width, mat, thickness=None, across=None):
    """A pyramid from a rhombus at `root` to `tip`: `width` along `across`
    (default: horizontal) and `thickness` the other way (default: width)."""
    root, tip = Vector(root), Vector(tip)
    d = (tip - root).normalized()
    u = Vector(across) if across is not None else d.cross(Vector((0, 0, 1)))
    u = u - d * u.dot(d)
    if u.length < 1e-6:
        u = d.orthogonal()
    u.normalize()
    v = d.cross(u)
    w, t = width * 0.5, (thickness if thickness is not None else width) * 0.5
    base = [mb.bm.verts.new(root + o) for o in (u * w, v * t, -u * w, -v * t)]
    top = mb.bm.verts.new(tip)
    mb.bm.faces.new(list(reversed(base)))
    for i in range(4):
        mb.bm.faces.new((base[i], base[(i + 1) % 4], top))
    return mb._finish(base + [top], mat, None)


def tube(mb, path, radii, mat, sides=5, flat=1.0):
    """A faceted tube along `path` with a radius at each point (a ponytail,
    a braid, a horn); an end closes to a point when its radius is 0.
    `flat` squeezes it across the path."""
    pts = [Vector(p) for p in path]
    rings = []
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        u = t.cross(Vector((1, 0, 0)))
        u = u.normalized() if u.length > 1e-6 else Vector((0, 1, 0))
        v = t.cross(u).normalized()
        if radii[i] <= 0.0:
            rings.append([mb.bm.verts.new(p)])
            continue
        turn = 0.5 * (i % 2)   # Alternate rings are turned half a side, for irregular facets.
        rings.append([mb.bm.verts.new(p + (u * math.cos(a) + v * math.sin(a) * flat) * radii[i])
                      for a in [(j + turn) * math.tau / sides for j in range(sides)]])
    for r0, r1 in zip(rings, rings[1:]):
        for j in range(sides):
            a0, a1 = r0[j % len(r0)], r0[(j + 1) % len(r0)]
            b0, b1 = r1[j % len(r1)], r1[(j + 1) % len(r1)]
            if len(r0) > 1 and len(r1) > 1:
                mb.bm.faces.new((a0, a1, b1))
                mb.bm.faces.new((a0, b1, b0))
            elif len(r0) > 1:
                mb.bm.faces.new((a0, a1, b0))
            elif len(r1) > 1:
                mb.bm.faces.new((a0, b1, b0))
    for ring in (rings[0], rings[-1]):
        if len(ring) > 2:
            mb.bm.faces.new(ring)
    return mb._finish([v for ring in rings for v in ring], mat, None)


def surface(spec, origin, direction, step=0.004, reach=1.5):
    """From a point inside the welded body, the point where the ray along
    `direction` leaves it."""
    p, d = Vector(origin), Vector(direction).normalized() * step
    for _ in range(int(reach / step)):
        if studies.sdf(spec, p) > 0.0:
            break
        p = p + d
    return p


def land(spec, origin, direction, step=0.004, reach=2.0):
    """From a point outside the welded body, the point where the ray along
    `direction` hits it; None if it misses."""
    p, d = Vector(origin), Vector(direction).normalized() * step
    for _ in range(int(reach / step)):
        if studies.sdf(spec, p) < 0.0:
            return p
        p = p + d
    return None


def normal_at(spec, p, e=0.012):
    """The outward direction of the welded body's surface near p."""
    n = Vector([studies.sdf(spec, p + o) - studies.sdf(spec, p - o)
                for o in (Vector((e, 0, 0)), Vector((0, e, 0)), Vector((0, 0, e)))])
    return n.normalized() if n.length > 1e-9 else Vector((0, -1, 0))


def strap(mb, spec, path, width, mat, front=True, lift=0.004, thickness=0.02, step=0.06):
    """A strap lying on the body: `path` is a line of (x, z) points as seen
    from the front (or from the back), projected onto the surface."""
    y = -1.0 if front else 1.0
    samples = []
    for (x0, z0), (x1, z1) in zip(path, path[1:]):
        count = max(1, round(math.hypot(x1 - x0, z1 - z0) / step))
        samples += [(x0 + (x1 - x0) * i / count, z0 + (z1 - z0) * i / count) for i in range(count)]
    samples.append(path[-1])
    pts, normals = [], []
    for x, z in samples:
        p = land(spec, (x, y, z), (0, -y, 0))
        if p is None:
            continue
        n = normal_at(spec, p)
        # Flatten the normal toward the viewer, so the strap does not twist
        # where the surface turns away (under an arm).
        n = (n + Vector((0, y, 0)) * 0.6).normalized()
        pts.append(p + n * lift)
        normals.append(n)
    if len(pts) > 1:
        strip(mb, pts, normals, width, thickness, mat)


def belt(mb, spec, z, height, mat, pad=0.012, segments=10, flare=0.0):
    """A belt around the trunk at height z, following its outline. Returns
    at(angle in degrees, 0 = front, 90 = the character's left): the point
    on the belt's outside there. `flare` widens the lower edge."""
    origin = Vector((0.0, 0.0, z))

    def at(angle, extra=0.0, dz=0.0):
        a = math.radians(angle)
        d = Vector((math.sin(a), -math.cos(a), 0.0))
        return surface(spec, origin, d) + d * (pad + extra) + Vector((0, 0, dz))

    angles = [(i + 0.5) * 360.0 / segments for i in range(segments)]
    low = [mb.bm.verts.new(at(a, flare, -height * 0.5)) for a in angles]
    top = [mb.bm.verts.new(at(a, 0.0, height * 0.5)) for a in angles]
    mb.bm.faces.new(low)
    mb.bm.faces.new(list(reversed(top)))
    for i in range(segments):
        j = (i + 1) % segments
        mb.bm.faces.new((low[i], low[j], top[j], top[i]))
    mb._finish(low + top, mat, None)
    return at


def buckle(mb, at, mat, size=0.06, angle=0.0, depth=0.016):
    """A square buckle on a belt (`at` as returned by belt())."""
    p = at(angle)
    mb.box((p.x, p.y, p.z), (size, depth * 2, size), mat, rotation_z=math.radians(angle))


def pouch(mb, at, angle, size, mat, drop=0.02, flap=None):
    """A box hanging from a belt at `angle`; `flap` is the lid's material."""
    p = at(angle)
    a = math.radians(angle)
    out = Vector((math.sin(a), -math.cos(a), 0.0))
    c = p + out * (size[1] * 0.35) - Vector((0, 0, drop + size[2] * 0.5))
    mb.box(c, size, mat, rotation_z=a)
    if flap:
        lid = (size[0] * 1.08, size[1] * 1.12, size[2] * 0.42)
        mb.box(c + Vector((0, 0, size[2] * 0.33)), lid, flap, rotation_z=a)


def panel(mb, at, angle, width, drop, mat, point=0.0, flare=0.03, thickness=0.014, taper=1.0, dz=0.0, lift=0.0):
    """A cloth or plate panel hanging from a belt (`at` as returned by
    belt()) at `angle`: `width` wide, `drop` long down to its corners and
    `point` more to its tip; `flare` is how far the low edge swings out."""
    a = math.radians(angle)
    out = Vector((math.sin(a), -math.cos(a), 0.0))
    side = Vector((math.cos(a), math.sin(a), 0.0)) * (width * 0.5)
    top = at(angle, extra=lift, dz=dz)
    low = top + out * flare - Vector((0, 0, drop))
    pts = [top - side, top + side, low + side * taper]
    if point:
        pts.append(low + out * (flare * point / drop) - Vector((0, 0, point)))
    pts.append(low - side * taper)
    return studies.plate(mb, pts, thickness, mat)


def sheet(mb, rows, thickness, mat, back=(0, 1, 0)):
    """A thin cloth through a grid of points (rows of equal length), with
    folds wherever the points say; `back` is the side it is thickened to."""
    off = Vector(back).normalized() * thickness
    front = [[mb.bm.verts.new(Vector(p)) for p in row] for row in rows]
    rear = [[mb.bm.verts.new(Vector(p) + off) for p in row] for row in rows]
    nr, nc = len(rows), len(rows[0])
    for r in range(nr - 1):
        for c in range(nc - 1):
            mb.bm.faces.new((front[r][c], front[r][c + 1], front[r + 1][c + 1], front[r + 1][c]))
            mb.bm.faces.new((rear[r][c], rear[r + 1][c], rear[r + 1][c + 1], rear[r][c + 1]))
        for c in (0, nc - 1):
            mb.bm.faces.new((front[r][c], front[r + 1][c], rear[r + 1][c], rear[r][c]))
    for c in range(nc - 1):
        for r in (0, nr - 1):
            mb.bm.faces.new((front[r][c], rear[r][c], rear[r][c + 1], front[r][c + 1]))
    return mb._finish([v for row in front + rear for v in row], mat, None)


def hip_ring(spec, angles, z, pad, parts=("hips", "waist", "thigh.L", "thigh.R")):
    """Points around the trunk and thighs at height z, `pad` outside them,
    at the angles (degrees, 0 = front, 90 = the character's left): where a
    skirt must pass to clear the hips. Arms and sleeves do not count."""
    solids = [spec.parts[n] for n in parts]
    ring = []
    for a in angles:
        r = math.radians(a)
        d = Vector((math.sin(r), -math.cos(r), 0.0))
        p = Vector((0.0, 0.0, z))
        for _ in range(300):
            if min(part_distance(s, p) for s in solids) > 0.0:
                break
            p = p + d * 0.004
        ring.append(p + d * pad)
    return ring


def shell(mb, rings, mat, sides=6):
    """A hard angular shell (a greave, a boot, a cuirass): the hull of
    horizontal rings (center, half width, front depth, back depth). With
    6 sides every ring has a point at the front: a ridge down the middle."""
    pts = []
    for c, rx, front, back in rings:
        c = Vector(c)
        for i in range(sides):
            a = i * math.tau / sides
            ry = front if math.cos(a) > 0 else back
            pts.append(c + Vector((math.sin(a) * rx, -math.cos(a) * ry, 0.0)))
    return hull(mb, pts, mat)


def recolor(mb, verts, pick):
    """Repaints the faces of a piece: pick(center, normal) -> material or None."""
    mb.bm.normal_update()
    for f in {f for v in verts for f in v.link_faces}:
        mat = pick(f.calc_center_median(), f.normal)
        if mat:
            f.material_index = mb._material_index(mat)


def skirt(mb, rows, mat, inner=None, thickness=0.012, closed=False):
    """Cloth hanging around the body with straight edges: `rows` (top to
    bottom) of points going around it. Open (a robe open at the front)
    unless `closed`. The inside can have another material."""
    def inward(p):
        d = Vector((-p.x, -p.y, 0.0))
        return d.normalized() * thickness if d.length > 1e-6 else Vector()
    outer = [[mb.bm.verts.new(Vector(p)) for p in row] for row in rows]
    inn = [[mb.bm.verts.new(Vector(p) + inward(Vector(p))) for p in row] for row in rows]
    nr, nc = len(rows), len(rows[0])
    inner_faces = []
    for r in range(nr - 1):
        for c in range(nc if closed else nc - 1):
            d = (c + 1) % nc
            mb.bm.faces.new((outer[r][c], outer[r][d], outer[r + 1][d], outer[r + 1][c]))
            inner_faces.append(mb.bm.faces.new((inn[r][c], inn[r + 1][c], inn[r + 1][d], inn[r][d])))
        if not closed:
            for c in (0, nc - 1):
                mb.bm.faces.new((outer[r][c], outer[r + 1][c], inn[r + 1][c], inn[r][c]))
    for c in range(nc if closed else nc - 1):
        d = (c + 1) % nc
        for r in (0, nr - 1):
            mb.bm.faces.new((outer[r][c], inn[r][c], inn[r][d], outer[r][d]))
    verts = mb._finish([v for row in outer + inn for v in row], mat, None)
    if inner:
        index = mb._material_index(inner)
        for f in inner_faces:
            f.material_index = index
    return verts


def collar(mb, center, z0, z1, r0, r1, mat, segments=8, drop=0.0, lean=0.0):
    """A wrapped cloth around the neck (a cowl, a scarf): a faceted ring
    from the wide low edge (radii r0 at z0) to the narrow top (r1 at z1).
    `drop` lowers the front of the low edge; `lean` moves the top back."""
    low, top = [], []
    for i in range(segments):
        a = (i + 0.5) * math.tau / segments
        s, c = math.sin(a), -math.cos(a)
        front = max(0.0, -c)
        low.append(mb.bm.verts.new((center[0] + s * r0[0], center[1] + c * r0[1], z0 - drop * front)))
        top.append(mb.bm.verts.new((center[0] + s * r1[0], center[1] + lean + c * r1[1], z1)))
    mb.bm.faces.new(low)
    mb.bm.faces.new(list(reversed(top)))
    for i in range(segments):
        j = (i + 1) % segments
        mb.bm.faces.new((low[i], low[j], top[j], top[i]))
    return mb._finish(low + top, mat, None)


class FolkRig(rigs_human.Humanoid):
    """The shared skeleton plus what these characters' clothes need:
    - two bones for what hangs from the belt, in front and behind
      ("skirt.F", "skirt.B"); they follow the leg that is farthest forward
      or back, and lie on the ground when the character sits;
    - detail pieces bound to the bones the character names (Folk.tag);
    - the character's own bones and poses (Folk.extra_bones, Folk.animate).
    """

    def __init__(self, spec, extra_bones=(), part_bones=None):
        k = spec.k
        hip = spec.joints()["hip"][2] * k
        hang = [Bone("skirt.F", (0, -0.02 * k, hip), (0, -0.02 * k, hip - 0.4 * k), parent="hips"),
                Bone("skirt.B", (0, 0.02 * k, hip), (0, 0.02 * k, hip - 0.4 * k), parent="hips")]
        super().__init__(spec, hang + list(extra_bones), part_bones)
        self.rest_swing = [self.thigh_angle(Pose(self), side) for side, _ in rigs_human.SIDES]

    # ------------------------------------------------------------ binding

    def target(self, piece):
        """What the character said this detail piece follows (Folk.tag)."""
        return self.spec.owner.get(piece[0])

    def piece_bone(self, center, piece):
        target = self.target(piece)
        if isinstance(target, str):
            return target
        return min(self.bones[:17], key=lambda b: rigs_human.rigs.segment_distance(center, b.head, b.tail)).name

    def piece_weights(self, center, piece):
        target = self.target(piece)
        return None if target is None or isinstance(target, str) else target

    def drape(self, p):
        """Weights of what hangs from the belt (skirts, panels, tabards,
        loincloths): the hips at the belt, and lower down the front or
        back bone, or the thigh on its side."""
        k = self.k
        top = (self.spec.BELT - 0.02) * k
        full = min(top - 0.1 * k, self.by_name["skirt.F"].head.z)
        f = smooth((top - p.z) / (top - full))
        if f <= 0.0:
            return [("hips", 1.0)]
        d = Vector((p.x, p.y, 0.0))
        d = d.normalized() if d.length > 1e-6 else Vector((0, -1, 0))
        return [("hips", 1.0 - f), ("skirt.F", f * max(0.0, -d.y) ** 2), ("skirt.B", f * max(0.0, d.y) ** 2),
                ("thigh.L", f * max(0.0, d.x) ** 2), ("thigh.R", f * max(0.0, -d.x) ** 2)]

    def torso(self, p):
        """Weights of what lies on the trunk (straps, a cuirass): hips,
        spine and chest by height."""
        z, b = self.spec.z, 0.05 * self.k
        a = smooth((p.z - (z["waist"] - b)) / (2 * b))
        c = smooth((p.z - (z["chest"] - b)) / (2 * b))
        return [("hips", 1.0 - a), ("spine", a * (1.0 - c)), ("chest", a * c)]

    def shoulder(self, side):
        """Weights of a pauldron: mostly the chest, so it does not cut
        into the neck when the arm rises, and partly the arm."""
        return lambda p: [("chest", 0.6), (f"upper_arm.{side}", 0.4)]

    def cape(self, p):
        """Weights of a cape: the chest at the shoulders, its bone below."""
        f = smooth((self.by_name["cape"].head.z - p.z) / (0.22 * self.k))
        return [("chest", 1.0 - f), ("cape", f)]

    # -------------------------------------------------------------- poses

    def thigh_angle(self, pose, side):
        """How far forward the thigh points, in radians, seen from the hips."""
        d = pose.world("hips").inverted() @ (pose.tail(f"thigh.{side}") - pose.head(f"thigh.{side}"))
        return math.atan2(-d.y, -d.z)

    @staticmethod
    def clear(height, length):
        """The angle from the vertical at which something `length` long,
        hanging from `height`, stays above the ground."""
        return 0.0 if length <= height else math.acos(max(0.0, height) / length)

    def cloth(self, pose):
        """Poses the cloth bones for the pose of the body."""
        spec, k = self.spec, self.k
        swing = [self.thigh_angle(pose, side) - rest for (side, _), rest in zip(rigs_human.SIDES, self.rest_swing)]
        forward, back = max(0.0, max(swing)), max(0.0, -min(swing))
        down = pose.world("hips") @ Vector((0, 0, -1))
        pitch = math.atan2(down.y, -down.z)     # How far back the hips tip what hangs from them.
        lie = self.clear(pose.head("skirt.F").z - 0.03 * k, spec.HANG * k)
        pose.q["skirt.F"] = Quaternion(X, -max(forward, lie) - pitch)
        pose.q["skirt.B"] = Quaternion(X, max(back, lie) - pitch)
        if "cape" in self.by_name:
            ahead = pose.world("chest") @ Vector((0, -1, 0))
            yaw = math.atan2(ahead.x, -ahead.y)
            lie = self.clear(pose.head("cape").z - 0.03 * k, spec.CAPE * k)
            pose.set_world("cape", Quaternion(Z, yaw) @ Quaternion(X, max(back * 0.8, lie)))

    def clips(self):
        def adjusted(name, fn):
            def pose_fn(t):
                q, offset, more = fn(t)
                pose = Pose(self, offset)
                pose.q = q
                self.spec.animate(name, t, pose)
                self.cloth(pose)
                return pose.q, pose.offset, more
            return pose_fn
        return [(name, frames, loops, adjusted(name, fn), speed) for name, frames, loops, fn, speed in super().clips()]


def follows(target):
    """Decorator for the Folk methods that add detail pieces: the pieces
    follow `target` (see Folk.tag), and afterwards the tag is what it was."""
    def decorate(method):
        @functools.wraps(method)
        def wrapped(self, mb, *args, **kwargs):
            with self.bound(mb, target):
                return method(self, mb, *args, **kwargs)
        return wrapped
    return decorate


# The angular head of the humans, for a head of size 1 and relative to the
# head's center (x is mirrored): flat planes for the forehead, the cheeks,
# the jaw and the chin.
HEAD_POINTS = [
    (0.0, -0.01, 0.118), (0.052, -0.04, 0.1), (0.052, 0.05, 0.1), (0.0, 0.085, 0.085),   # Crown.
    (0.062, -0.088, 0.055), (0.0, -0.1, 0.06),                                          # Forehead.
    (0.088, -0.02, 0.03), (0.086, 0.05, 0.015),                                         # Temples.
    (0.0, 0.112, 0.01), (0.058, 0.095, -0.035), (0.0, 0.09, -0.07),                     # Back.
    (0.072, -0.09, 0.012),                                                              # Brow corners.
]
JAW_POINTS = [
    (0.082, -0.055, -0.035),    # Cheekbones.
    (0.07, 0.005, -0.085),      # Jaw corners.
    (0.045, -0.096, -0.07),     # Sides of the mouth.
    (0.03, -0.092, -0.117), (0.0, -0.098, -0.113),   # Chin.
    (0.04, -0.01, -0.112),      # Under the jaw.
]


class Folk(Human):
    """The shared body plus what these characters need: an angular head
    with a face, hair, joints as vectors, cuts across a limb, flat hems and
    plate armor for the legs."""

    jaw = 1.0   # Width of the jaw and chin (a woman's is narrower).
    BELT = 1.1  # Height of the belt (of a 1.8 m body).
    HANG = 0.4  # How far below the hip joints the longest cloth of the belt hangs.

    def __init__(self):
        self.cuts = []
        self.hems = []  # (part name, material of the flat end).
        self.owner = {}  # Detail vertex -> what it follows; see tag().
        self.tones = 0.0  # Facet tones are added at the end of details (tone()).
        super().__init__()

    # ----------------------------------------------------------- skeleton

    def make_rig(self):
        return FolkRig(self, self.extra_bones(), self.part_bones())

    def extra_bones(self):
        """Hook: the character's own bones (a tail, a cape), parents first."""
        return []

    def part_bones(self):
        """Hook: {welded part the character added: the bone it follows}."""
        return {}

    def animate(self, clip, t, pose):
        """Hook: pose the character's own bones, or change the clip's pose
        (a rigs.Pose), at time t (0 to 1) of the clip."""

    def begin(self, mb):
        """Call first in details(): starts the list of what follows what.
        The skeleton tells the detail pieces from the welded surface by
        the order of the vertices (rigs.Rig.bind: those after
        mb.detail_from), but the cuts made before deleted vertices and new
        ones would take their places; a packed copy puts them in order."""
        packed = mb.bm.copy()
        mb.bm.free()
        mb.bm = packed
        mb.deform = packed.verts.layers.deform.verify()
        mb.detail_from = len(packed.verts)
        self.owner = {}                 # Detail vertex -> what it follows.
        self.known = set(packed.verts)
        self.following = None

    def tag(self, mb, target):
        """The detail pieces added from here on follow `target`: a bone's
        name, a function point -> [(bone, weight)] for pieces that bend
        (self.rig.drape, .torso, .cape, .shoulder(side)), or None for the
        nearest bone. (The vertices are looked up one by one, not by
        their order: some primitives delete helper vertices, and the next
        piece's vertices take their places.)"""
        for v in mb.bm.verts:
            if v not in self.known:
                self.known.add(v)
                self.owner[v] = self.following
        self.following = target

    @contextlib.contextmanager
    def bound(self, mb, target):
        """`with self.bound(mb, target):` tags the pieces added inside."""
        before = self.following
        self.tag(mb, target)
        yield
        self.tag(mb, before)

    def done(self, mb):
        """Call last in details(): closes the last tag and numbers the
        vertices (the skeleton tells the pieces apart by their numbers)."""
        self.tag(mb, None)
        mb.bm.verts.index_update()

    def V(self, x, y, z):
        """A point of the 1.8 m body, scaled, as a Vector."""
        return Vector(self.P(x, y, z))

    def J(self, name, side=1):
        """A joint (see Human.joints) of the left (1) or right (-1) side."""
        j = self.joints()[name]
        return self.V(j[0] * side, j[1], j[2])

    def near(self, name, tol=0.03):
        """A region for cuts: within `tol` of the welded part."""
        part = self.parts[name]
        return lambda c, n: part_distance(part, c) < tol

    def limb_cut(self, name, t, tol=0.03):
        """Adds a cut across the capsule part `name` at `t` along it."""
        part = self.parts[name]
        a, b = Vector(part[1]), Vector(part[2])
        self.cuts.append((a.lerp(b, t), (b - a).normalized(), self.near(name, tol)))

    def level_cut(self, z, region=None):
        """Adds a horizontal cut at height z (of the 1.8 m body)."""
        self.cuts.append(((0, 0, z * self.k), (0, 0, 1), region or (lambda c, n: True)))

    def hem(self, name, mat, tol=0.02):
        """Makes the far end of the capsule part `name` flat and open-looking
        (a sleeve's hem) instead of round: the surface is cut there and what
        lies beyond is pressed onto the cut, painted `mat`. Call in
        __init__; flatten_hems() does the pressing in details()."""
        part = self.parts[name]
        a, b = Vector(part[1]), Vector(part[2])
        self.cuts.append((b, (b - a).normalized(), self.near(name, tol)))
        self.hems.append((name, mat, tol))

    def flatten_hems(self, mb):
        for name, mat, tol in self.hems:
            part = self.parts[name]
            a, b = Vector(part[1]), Vector(part[2])
            axis = (b - a).normalized()
            moved = set()
            for v in mb.bm.verts:
                d = (v.co - b).dot(axis)
                if d > -1e-5 and part_distance(part, v.co) < tol:
                    v.co -= axis * d
                    moved.add(v)
            index = mb._material_index(mat)
            for f in mb.bm.faces:
                if all(v in moved for v in f.verts):
                    f.material_index = index
        mb.bm.normal_update()

    def tone(self, mb, mats, share=0.35):
        """Lighter and darker facets for the materials (welded and details)."""
        for i, mat in enumerate(mats):
            tone_faces(mb, mat, share, seed=11 + i)

    # --------------------------------------------------------------- head

    def small_head(self, parts):
        """Shrinks the welded head so the angular head (head()) covers it."""
        hs = self.head_size
        parts["head"] = self.ellipsoid((0, -0.005, 1.8 - 0.118 * hs), (0.068 * hs, 0.085 * hs, 0.095 * hs))
        parts["jaw"] = self.ellipsoid((0, -0.03, 1.8 - 0.168 * hs), (0.048 * hs, 0.055 * hs, 0.045 * hs))

    def hp(self, x, y, z):
        """A point given relative to the head's center, for a head of size 1."""
        u = self.head_size * self.k
        return Vector((x * u, -0.01 * self.k + y * u, (1.8 - 0.118 * self.head_size) * self.k + z * u))

    @follows("head")
    def head(self, mb, skin="skin", points=None, jaw_points=None):
        """The angular head: a hull with planes for the forehead, the
        cheeks, the jaw and the chin."""
        jaw = [(x * self.jaw, y, z) for x, y, z in (jaw_points or JAW_POINTS)]
        return hull(mb, [self.hp(*p) for p in sym((points or HEAD_POINTS) + jaw)], skin)

    @follows("head")
    def face(self, mb, skin="skin", brow="hair", eye="eye", ears=True, stern=0.01, nose=1.0, forward=0.0):
        """Eyes, dark eyebrows, a nose wedge and ears, on the angular head
        (`forward`: how much farther forward this head's face is)."""
        hp, u = self.hp, self.head_size * self.k
        for s in (-1, 1):
            mb.sphere(hp(s * 0.034, -0.095 - forward, 0.004), 0.0125 * u, eye, segments=6, rings=4,
                      scale=(1.25, 0.45, 0.75))
            if brow:
                a, b = hp(s * 0.011, -0.1015, 0.03 - stern), hp(s * 0.066, -0.094, 0.032)
                up = Vector((0, 0, 0.015 * u))
                studies.plate(mb, [a, b, b + up, a + up], 0.012 * u, brow)
            if ears:
                hull(mb, [hp(s * x, y, z) for x, y, z in ((0.084, 0.0, 0.012), (0.084, 0.035, 0.0),
                                                          (0.102, 0.032, 0.014),
                                                          (0.098, 0.022, -0.03), (0.084, 0.01, -0.04))], skin)
        if nose:
            hull(mb, [hp(0, -0.099, 0.014), hp(0.016 * nose, -0.097, -0.036), hp(-0.016 * nose, -0.097, -0.036),
                      hp(0, -0.1 - 0.03 * nose, -0.03), hp(0, -0.098, -0.045)], skin)

    @follows("head")
    def hair_hull(self, mb, mat, points):
        """A mass of hair with flat planes: the hull of points given like
        hp() (x is mirrored)."""
        return hull(mb, [self.hp(*p) for p in sym(points)], mat)

    @follows("head")
    def shards(self, mb, mat, shards):
        """Locks of hair: (root, tip, width), points given like hp()."""
        u = self.head_size * self.k
        for root, tip, width in shards:
            spike(mb, self.hp(*root), self.hp(*tip), width * u, mat, thickness=width * 0.6 * u)

    # ------------------------------------------------------- hands, armor

    @follows(None)
    def fingers(self, mb, mat, sides=(-1, 1)):
        """A thumb on each mitt hand, so it reads as a fist."""
        k = self.k
        for s in sides:
            self.tag(mb, "hand.L" if s > 0 else "hand.R")
            h = Vector(self.parts["hand.L" if s > 0 else "hand.R"][1])
            mb.cylinder(h + Vector((-s * 0.016 * k, -0.032 * k, 0.03 * k)),
                        h + Vector((-s * 0.026 * k, -0.055 * k, -0.03 * k)), 0.016 * k, 0.011 * k, mat, segments=4)

    @follows(None)
    def knee_guard(self, mb, mat, size=1.0):
        """An angular plate over each knee: a ridge down the middle, pointed
        above and below."""
        k = self.k * size
        for s, side in ((1, ".L"), (-1, ".R")):
            self.tag(mb, "shin" + side)
            c = self.J("knee", s)
            r = self.parts["thigh" + side][4] * size   # The leg's radius at the knee.
            hull(mb, [c + Vector(p) for p in sym([
                (0, -r - 0.012 * k, 0.1 * k), (r + 0.01 * k, -0.25 * r, 0.03 * k), (0, -r - 0.042 * k, 0.012 * k),
                (0, -r - 0.012 * k, -0.095 * k), (r * 0.9, 0.45 * r, 0.0), (r * 0.8, -0.5 * r, -0.06 * k)])], mat)

    @follows(None)
    def greaves(self, mb, mat, front=None, size=1.0):
        """Hard shin plates: wide under the knee, a calf behind, narrow at
        the ankle, with a ridge down the front (optionally another color)."""
        k = self.k
        for s in (-1, 1):
            self.tag(mb, "shin.L" if s > 0 else "shin.R")
            knee, ankle = self.J("knee", s), self.J("ankle", s)
            rings = []
            for t, rx, fr, bk in ((0.14, 0.068, 0.082, 0.066), (0.42, 0.064, 0.07, 0.084), (0.93, 0.045, 0.058, 0.048)):
                rings.append((knee.lerp(ankle, t), rx * k * size, fr * k * size, bk * k * size))
            verts = shell(mb, rings, mat)
            if front:
                recolor(mb, verts, lambda c, n: front if n.y < -0.55 else None)

    @follows(None)
    def sabatons(self, mb, mat, size=1.0, heel=0.028):
        """Armored shoes: a wedge over the toes with a ridge, and a heel
        (`heel`: how high the arch is)."""
        k = self.k
        heel = heel / size
        for s in (-1, 1):
            self.tag(mb, "foot.L" if s > 0 else "foot.R")
            a = self.J("ankle", s)
            a.z = 0.0

            def p(x, y, z):
                return a + Vector((s * 0.008 * (-y / 0.2) + x, y, z)) * (k * size)
            hull(mb, [p(0, -0.225, 0.0), p(0, -0.21, 0.04), p(0.055, -0.13, 0.0), p(-0.055, -0.13, 0.0),
                      p(0.05, -0.12, 0.068), p(-0.05, -0.12, 0.068), p(0, -0.13, 0.085), p(0, -0.04, 0.125),
                      p(0.052, -0.03, heel), p(-0.052, -0.03, heel), p(0.052, -0.02, 0.105), p(-0.052, -0.02, 0.105)],
                 mat)
            hull(mb, [p(0.046, -0.03, heel), p(-0.046, -0.03, heel), p(0.042, 0.01, 0.0), p(-0.042, 0.01, 0.0),
                      p(0.04, 0.085, 0.0), p(-0.04, 0.085, 0.0), p(0.048, 0.09, 0.11), p(-0.048, 0.09, 0.11),
                      p(0.05, -0.03, 0.12), p(-0.05, -0.03, 0.12)], mat)


# ---------------------------------------------------------------- lizardfolk


class Lizardfolk(Folk):
    name = "lizardfolk"
    height = 1.75
    shoulder = 0.22
    build = 1.0
    budget = 1150
    palette = {"crest": "hair", "scarf": "top", "trousers": "bottom"}   # Materials the game recolors (rigs.palette_name).
    colors = {
        "skin": common.rgb(0x6FA63A),
        "skin_light": common.rgb(0x9DC748),
        "skin_shade": common.rgb(0x578C36),
        "crest": common.rgb(0x2F5753),
        "belly": common.rgb(0xF0D08A),
        "scarf": common.rgb(0xB3383C),
        "steel": common.rgb(0xB4A3A1),
        "leather": common.rgb(0x74482F),
        "leather_dark": common.rgb(0x4E342B),
        "trousers": common.rgb(0x47404D),
        "eye": common.rgb(0x1A1414),
    }
    BELT = 1.09
    HANG = 0.32
    TAIL = [(0.0, 0.07, 0.95), (0.0, 0.23, 0.72), (-0.03, 0.34, 0.44), (-0.10, 0.42, 0.21), (-0.22, 0.48, 0.075),
            (-0.37, 0.45, 0.035)]
    TAIL_R = [0.1, 0.095, 0.08, 0.06, 0.036, 0.014]

    def part_bones(self):
        out = {"snout": "head"}
        for side in ("L", "R"):
            out["brow." + side] = "head"
            out["clavicle." + side] = "chest"
            for i in range(3):
                out[f"toe{i}.{side}"] = "foot." + side
        for i in range(len(self.TAIL) - 1):
            out[f"tail{i}"] = f"tail.{i + 1}"
        return out

    def extra_bones(self):
        pts = [self.V(*p) for p in self.TAIL]
        return [Bone(f"tail.{i + 1}", a, b, parent=f"tail.{i}" if i else "hips")
                for i, (a, b) in enumerate(zip(pts, pts[1:]))]

    def animate(self, clip, t, pose):
        """The tail sways, stays off the ground when the body sinks, and
        lies flat behind when sitting."""
        p = 2 * math.pi * t
        count = len(self.TAIL) - 1
        if clip in ("walk", "run", "carry_walk"):     # The long toes stay level: tipped down they would dig into the ground.
            for side in ("L", "R"):
                pose.set_world("foot." + side, Quaternion())
        if clip == "fish_sit":
            for i in range(count):
                pose.aim(f"tail.{i + 1}", Vector((-0.12 * i + 0.05 * math.sin(p) * i, 1.0, 0.0)))
            return
        amp = {"idle": 4.0, "walk": 8.0, "carry_walk": 8.0, "run": 11.0}.get(clip, 2.5)
        for i in range(count):
            pose.turn(f"tail.{i + 1}", Z, amp * math.sin((2 if clip == "idle" else 1) * p - 0.7 * i))
        rest = self.rig.by_name[f"tail.{count}"].tail.z
        for _ in range(4):
            tip, root = pose.tail(f"tail.{count}"), pose.head("tail.1")
            if tip.z >= rest - 1e-4:
                break
            pose.turn("tail.1", X, math.degrees((rest - tip.z) / max(0.1, math.hypot(tip.x - root.x, tip.y - root.y))))

    def __init__(self):
        super().__init__()
        k = self.k
        legs = lambda c, n: c.z < self.z["hip"]  # noqa: E731
        self.level_cut(0.64, legs)   # Trouser cuffs.
        self.level_cut(0.52, legs)
        self.level_cut(0.13, legs)   # Leg wraps end at the ankle.
        for side in (".L", ".R"):
            self.limb_cut("forearm" + side, 0.1)
            self.limb_cut("forearm" + side, 0.97)
        for x in (-0.085, 0.085):    # The yellow belly's edges.
            self.cuts.append(((x * k, 0, 0), (1, 0, 0),
                              lambda c, n: 1.0 * k < c.z < 1.46 * k and c.y < 0.0 and abs(c.x) < 0.2 * k))

    def customize(self, parts):
        E, C = self.ellipsoid, self.capsule
        # A reptile's head: a long skull, a snout and a lower jaw.
        parts["head"] = E((0, 0.0, 1.705), (0.094, 0.135, 0.092))
        parts["snout"] = C((0, -0.08, 1.7), (0, -0.295, 1.668), 0.08, 0.05)
        parts["jaw"] = C((0, -0.04, 1.638), (0, -0.275, 1.618), 0.064, 0.036)
        parts["neck"] = C((0, 0.012, 1.47), (0, 0.02, 1.64), 0.07, 0.064)
        parts["chest"] = E((0, 0.0, 1.33), (0.138, 0.112, 0.18))
        parts["waist"] = E((0, 0.0, 1.13), (0.118, 0.095, 0.15))
        for side, x in ((".L", 1), (".R", -1)):
            parts["brow" + side] = E((x * 0.052, -0.075, 1.768), (0.036, 0.075, 0.028))
            j = {n: (p[0] * x, p[1], p[2]) for n, p in self.joints().items()}
            parts["clavicle" + side] = C((x * 0.05, 0.0, 1.44), j["shoulder"], 0.056, 0.056)   # Square shoulders.
            parts["upper_arm" + side] = C(j["shoulder"], j["elbow"], 0.052, 0.046)
            parts["forearm" + side] = C(j["elbow"], j["wrist"], 0.06, 0.05)     # Bracer.
            parts["shin" + side] = C(j["knee"], j["ankle"], 0.058, 0.042)
            parts["hand" + side] = E((j["hand"][0], j["hand"][1], j["hand"][2] + 0.015), (0.034, 0.048, 0.056))
            parts["thigh" + side] = C(j["hip"], j["knee"], 0.11, 0.086)         # Baggy trousers.
            # A big three-toed foot.
            ax = j["ankle"][0]
            parts["foot" + side] = C((ax, 0.03, 0.062), (ax + x * 0.01, -0.13, 0.052), 0.058, 0.056)
            for i, dx in enumerate((-0.052, 0.0, 0.052)):
                parts[f"toe{i}{side}"] = C((ax + x * 0.01 + dx * 0.5, -0.12, 0.048),
                                           (ax + x * 0.01 + dx * 1.5, -0.25 + abs(dx) * 0.5, 0.03), 0.034, 0.023)
        for i in range(len(self.TAIL) - 1):
            parts[f"tail{i}"] = C(self.TAIL[i], self.TAIL[i + 1], self.TAIL_R[i], self.TAIL_R[i + 1])

    def paint(self, c, n):
        k, zone = self.k, self.zone(c)
        if zone == "jaw":
            return "belly"
        if zone in ("head", "snout", "neck") or zone.startswith("brow"):
            if zone == "neck" and n.y < -0.35:
                return "belly"
            return "skin_shade" if n.z > 0.45 else "skin"
        if zone.startswith("tail"):
            return "skin_light" if n.z < -0.25 else "skin_shade" if n.z > 0.55 else "skin"
        if zone.startswith("forearm"):
            return "leather" if 0.1 < along(self.parts[zone], c) < 0.97 else "skin"
        if zone.startswith(("hand", "upper_arm", "shoulder", "clavicle", "foot", "toe")):
            return "skin"
        if zone.startswith("shin"):
            return "leather_dark" if c.z > 0.13 * k else "skin"
        if zone.startswith("thigh") or c.z < self.BELT * k:
            if c.z > 0.64 * k:
                return "trousers"
            return "leather" if c.z > 0.52 * k else "leather_dark"
        if c.y < 0.0 and abs(c.x) < 0.085 * k:
            return "belly"
        return "skin"

    def details(self, mb):
        k, V = self.k, self.V
        self.begin(mb)
        self.tag(mb, "head")
        # Eyes on the sides of the skull, under the brow ridges.
        for s in (-1, 1):
            p = surface(self, V(0, -0.085, 1.725), (s, -0.25, 0)) - Vector((s * 0.005, 0, 0))
            mb.sphere(p, 0.018 * k, "belly", segments=6, rings=4, scale=(0.5, 1.0, 0.75))
            mb.sphere(p + Vector((s * 0.007 * k, -0.002, 0)), 0.0095 * k, "eye", segments=5, rings=3,
                      scale=(0.5, 0.6, 1.0))
            mb.sphere(V(s * 0.022, -0.34, 1.685), 0.007 * k, "eye", segments=5, rings=3)   # Nostrils.
        self.crest(mb)
        self.tail_ridge(mb)
        # Scarf: wrapped around the neck, with two folds pointing down the chest.
        self.tag(mb, "chest")
        collar(mb, (0.0, 0.0), 1.45 * k, 1.6 * k, (0.15 * k, 0.135 * k), (0.085 * k, 0.09 * k), "scarf", drop=0.03 * k)
        studies.plate(mb, [V(-0.145, -0.085, 1.5), V(0.145, -0.085, 1.5), V(0.03, -0.14, 1.3)], 0.03 * k, "scarf")
        studies.plate(mb, [V(-0.12, -0.115, 1.535), V(0.115, -0.115, 1.535), V(-0.01, -0.15, 1.4)], 0.03 * k, "scarf")
        spike(mb, V(-0.05, 0.12, 1.5), V(-0.09, 0.15, 1.3), 0.09 * k, "scarf", thickness=0.03 * k, across=(1, 0, 0))
        # Harness: two crossing straps, front and back.
        self.tag(mb, self.rig.torso)
        for front in (True, False):
            strap(mb, self, [(-0.14 * k, 1.4 * k), (0.115 * k, 1.14 * k)], 0.04 * k, "leather", front=front)
            strap(mb, self, [(-0.135 * k, 1.2 * k), (0.125 * k, 1.37 * k)], 0.034 * k, "leather", front=front)
        self.tag(mb, self.rig.shoulder("R"))
        # The pauldron on the right shoulder: a boulder of plates with blunt
        # points, over a dark rim.
        c = self.J("shoulder", -1) + Vector((-0.045, 0.0, 0.0)) * k
        blob(mb, c, (0.125 * k, 0.125 * k, 0.105 * k), "steel", count=14, seed=4, rotate=((0, 1, 0), 20))
        blob(mb, c + Vector((-0.02, 0.0, -0.075)) * k, (0.1 * k, 0.105 * k, 0.05 * k), "leather_dark", count=9, seed=6,
             rotate=((0, 1, 0), 25))
        for d in ((-0.7, -0.4, 0.6), (-0.4, 0.5, 0.75), (-1.0, 0.1, 0.0), (0.2, -0.3, 0.95)):
            d = Vector(d).normalized()
            spike(mb, c + d * (0.07 * k), c + d * (0.135 * k), 0.13 * k, "steel")
        # Belt, buckle, a sheath on the left hip and leather flaps at the hips.
        self.tag(mb, "hips")
        at = belt(mb, self, self.BELT * k, 0.062 * k, "leather_dark", pad=0.012 * k, flare=0.005 * k)
        buckle(mb, at, "steel", size=0.062 * k, angle=8)
        buckle(mb, at, "leather_dark", size=0.03 * k, angle=8, depth=0.018 * k)
        self.tag(mb, self.rig.drape)
        pouch(mb, at, 62, (0.042 * k, 0.036 * k, 0.2 * k), "leather", drop=0.0)
        for a in (-80, -42, 100, 140, -140):
            panel(mb, at, a, 0.13 * k, 0.15 * k, "leather", point=0.07 * k, flare=0.03 * k, dz=-0.02 * k, taper=0.8)
        # Loincloth: a long tan cloth with a split end, front and back.
        for y, zt in ((-1, 0.5), (1, 0.62)):
            top = at(0 if y < 0 else 180, dz=-0.02 * k)
            yy = top.y + y * 0.004
            low = yy + y * 0.03 * k
            w = 0.062 * k
            studies.plate(mb, [(-w, yy, top.z), (w, yy, top.z), (w * 0.9, low, 0.7 * k), (0.03 * k, low, zt * k),
                               (-0.005 * k, low, 0.64 * k)], 0.014 * k, "belly")
            studies.plate(mb, [(-w, yy, top.z), (-0.005 * k, low, 0.64 * k), (-0.035 * k, low, (zt + 0.06) * k),
                               (-w * 0.9, low, 0.7 * k)], 0.014 * k, "belly")
        self.knee_guard(mb, "steel", size=1.05)
        # Bracer rims.
        for side in (".L", ".R"):
            self.tag(mb, "lower_arm" + side)
            part = self.parts["forearm" + side]
            a, b = Vector(part[1]), Vector(part[2])
            for t0, t1, r in ((0.08, 0.24, 0.074), (0.5, 0.62, 0.066)):
                mb.cylinder(a.lerp(b, t0), a.lerp(b, t1), r * k, (r - 0.004) * k, "leather_dark", segments=6)
        # Claws on the toes and the fingers.
        for s, side in ((1, ".L"), (-1, ".R")):
            self.tag(mb, "foot" + side)
            for i in range(3):
                part = self.parts[f"toe{i}{side}"]
                a, b = Vector(part[1]), Vector(part[2])
                d = (b - a).normalized()
                spike(mb, b + d * 0.008 + Vector((0, 0, 0.004)), b + d * (0.062 * k) - Vector((0, 0, 0.024 * k)),
                      0.038 * k, "crest")
            self.tag(mb, "hand" + side)
            h = Vector(self.parts["hand" + side][1])
            for dy in (-0.028, 0.0, 0.028):
                spike(mb, h + Vector((0, dy * k, -0.06 * k)), h + Vector((-s * 0.01 * k, dy * k, -0.1 * k)),
                      0.02 * k, "crest")
        self.fingers(mb, "skin")
        self.tone(mb, ["skin"], 0.3)
        self.done(mb)

    @follows("head")
    def crest(self, mb):
        """Swept-back blades over the skull and down the neck, in three rows."""
        k = self.k
        center = Vector(self.parts["head"][1])
        back = Vector((0.0, 0.93, 0.37))
        for x, scale in ((0.0, 1.0), (-0.8, 0.85), (0.8, 0.85)):
            for i, phi in enumerate((55, 80, 105, 130, 158, 186)):
                a = math.radians(phi)
                d = Vector((x * (0.9 if phi > 60 else 0.6), -math.cos(a), max(-0.25, math.sin(a))))
                root = surface(self, center, d) - d.normalized() * (0.03 * k)
                size = (0.09, 0.12, 0.145, 0.155, 0.14, 0.115)[i] * scale * k
                tip = root + (back + d.normalized() * 0.45 + Vector((x * 0.3, 0, 0))).normalized() * size * 1.3
                spike(mb, root, tip, size * 0.95, "crest", thickness=size * 0.42,
                      across=Vector((x * 0.6, back.z, -back.y)))
        # Two more blades on the back of the neck.
        self.tag(mb, "neck")
        for z, size in ((1.6, 0.1), (1.54, 0.075)):
            root = surface(self, self.V(0, 0.02, z), (0, 1, 0)) - Vector((0, 0.015 * k, 0))
            spike(mb, root, root + Vector((0, 0.8, 0.3)) * size * k, size * 0.6 * k, "crest",
                  thickness=size * 0.3 * k, across=(0, 0.3, -0.8))

    @follows(None)
    def tail_ridge(self, mb):
        """Triangular plates along the top of the tail."""
        k = self.k
        pts = [self.V(*p) for p in self.TAIL]
        for i, (a, b) in enumerate(zip(pts, pts[1:])):
            tangent = (b - a).normalized()
            up = (Vector((0, 0, 1)) - tangent * tangent.z).normalized()
            count = 2 if i < 4 else 1
            self.tag(mb, f"tail.{i + 1}")
            for j in range(count):
                c = a.lerp(b, (j + 0.5) / count)
                top = surface(self, c, up) - up * (0.012 * k)
                size = (0.075 - 0.011 * i) * k
                studies.flap(mb, top - tangent * size * 0.6, top + tangent * size * 0.6,
                             top + up * size + tangent * size * 0.75, 0.022 * k, "crest")


SPECS = [Lizardfolk()]
