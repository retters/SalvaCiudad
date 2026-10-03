"""Adventurer (man): brown swept-up hair, a blue hooded short-sleeve tunic
with a long skirt and a gold clasp, crossed leather chest straps, a wide
belt with a buckle, bracers, fingerless gloves, dark trousers, tall boots
with folded cuffs and a sword on the back.

This module also holds the helpers shared by the characters of the first
reference sheet (adventurer_woman, catfolk, foxfolk, frogfolk import them):
- Adventurer: Human plus welded clothing parts with straight edges (cowl,
  skirt, sleeves, bracers, cuffed boots) and an angular human face;
- Surface: ray casts onto the welded surface, to lay details on it;
- strap / buckle / pouch / chunk / tube / hair_cap: detail pieces.
"""

import math
import random

import bmesh
from mathutils import Quaternion, Vector
from mathutils.bvhtree import BVHTree

import common
import rigs
import rigs_human
import studies
from _human import Human
from _people_kit import hull as chunk
from _people_kit import lerp, mirror

TAU = math.tau
SIDES = ((".L", 1), (".R", -1))


# ------------------------------------------------------------ detail pieces

def tube(mb, stations, mat, sides=5):
    """A faceted tube through the stations (center, radius); each ring is
    turned half a step from the one before, so the wall is made of
    triangles. A radius of 0 at an end closes it in a point."""
    rings = []
    count = len(stations)
    for i, (c, r) in enumerate(stations):
        c = Vector(c)
        axis = (Vector(stations[min(i + 1, count - 1)][0]) - Vector(stations[max(i - 1, 0)][0])).normalized()
        ref = Vector((1, 0, 0)) if abs(axis.x) < 0.9 else Vector((0, 1, 0))
        u = axis.cross(ref).normalized()
        v = axis.cross(u)
        if r <= 0.0:
            rings.append([mb.bm.verts.new(c)])
            continue
        phase = (i % 2) * math.pi / sides
        rings.append([mb.bm.verts.new(c + (u * math.cos(phase + k * TAU / sides)
                                           + v * math.sin(phase + k * TAU / sides)) * r) for k in range(sides)])
    for i, (r0, r1) in enumerate(zip(rings, rings[1:])):
        if len(r0) == 1 and len(r1) == 1:
            continue
        for k in range(sides):
            n = (k + 1) % sides
            if len(r0) == 1:
                mb.bm.faces.new((r0[0], r1[k], r1[n]))
            elif len(r1) == 1:
                mb.bm.faces.new((r0[k], r0[n], r1[0]))
            elif i % 2 == 0:  # r1 is half a step ahead of r0.
                mb.bm.faces.new((r0[k], r0[n], r1[k]))
                mb.bm.faces.new((r0[n], r1[n], r1[k]))
            else:
                mb.bm.faces.new((r0[k], r0[n], r1[n]))
                mb.bm.faces.new((r0[k], r1[n], r1[k]))
    for ring in (rings[0], rings[-1]):
        if len(ring) > 1:
            mb.bm.faces.new(ring)
    return mb._finish([v for ring in rings for v in ring], mat, None)


def spike(mb, base, tip, radius, mat, sides=4):
    """A faceted cone (a hair shard, a claw, a finger)."""
    return mb.cylinder(base, tip, radius, 0.0, mat, segments=sides)


def hair_cap(mb, center, radii, mat, keep, scale=(1.12, 1.12, 1.2), count=60, seed=1):
    """A faceted cap of hair over the head ellipsoid: the convex hull of
    points on a slightly larger ellipsoid, in the directions keep(d)
    accepts (d is a unit vector from the head's center)."""
    rnd = random.Random(seed)
    center = Vector(center)
    pts = []
    for p in studies.ellipsoid_points((0, 0, 0), (1, 1, 1), count, rnd):
        if keep(p.normalized()):
            pts.append(center + Vector((p.x * radii[0] * scale[0], p.y * radii[1] * scale[1],
                                        p.z * radii[2] * scale[2])))
    return chunk(mb, pts, mat)


class Surface:
    """The welded surface as it is after decimating, to lay details on it."""

    def __init__(self, mb):
        mb.bm.faces.ensure_lookup_table()
        self.tree = BVHTree.FromBMesh(mb.bm)

    def out(self, origin, direction, reach=1.5):
        """Where a ray from a point inside the body leaves it (or None)."""
        return self.tree.ray_cast(Vector(origin), Vector(direction).normalized(), reach)[0]

    def onto(self, point, direction, back=0.6):
        """The first surface point met coming from outside along
        `direction` toward `point` (or None)."""
        d = Vector(direction).normalized()
        return self.tree.ray_cast(Vector(point) - d * back, d, back * 2.0)[0]


def strap(mb, surf, center, normal, width, mat, thick=0.012, sink=0.025, segments=16, skip=None):
    """A band around the body (belt, chest strap, thigh strap): follows the
    surface where the plane (center, normal) cuts it. `center` must be
    inside the body. skip(point) leaves gaps (under a cowl, behind a
    tabard). Returns the outer points of the stations (None where skipped)."""
    center, n = Vector(center), Vector(normal).normalized()
    u = n.orthogonal().normalized()
    v = n.cross(u)
    frames = []
    for i in range(segments):
        a = TAU * i / segments
        d = u * math.cos(a) + v * math.sin(a)
        p = surf.out(center, d)
        frames.append(None if p is None or (skip is not None and skip(p)) else (p, d))
    half = n * (width * 0.5)
    rings = []
    for i, frame in enumerate(frames):
        alone = frames[i - 1] is None and frames[(i + 1) % segments] is None
        if frame is None or alone:
            rings.append(None)
            continue
        p, d = frame
        rings.append([mb.bm.verts.new(q) for q in (p + d * thick + half, p + d * thick - half,
                                                   p - d * sink - half, p - d * sink + half)])
    verts = []
    for i, ring in enumerate(rings):
        if ring is None:
            continue
        verts += ring
        nxt = rings[(i + 1) % segments]
        if nxt is None:
            mb.bm.faces.new(ring)
        else:
            for k in range(4):
                m = (k + 1) % 4
                mb.bm.faces.new((ring[k], ring[m], nxt[m], nxt[k]))
        if rings[i - 1] is None:
            mb.bm.faces.new(list(reversed(ring)))
    mb._finish(verts, mat, None)
    return [None if f is None else f[0] + f[1] * thick for f in frames]


def buckle(mb, pos, size, frame_mat, inner_mat, depth=0.022):
    """A square belt buckle facing -Y: a frame with the belt showing inside."""
    pos = Vector(pos)
    mb.box(pos, (size, depth, size * 0.9), frame_mat)
    mb.box(pos - Vector((0, depth * 0.35, 0)), (size * 0.55, depth, size * 0.48), inner_mat)
    mb.box(pos - Vector((size * 0.1, depth * 0.45, 0)), (size * 0.5, depth, size * 0.14), frame_mat)


def pouch(mb, center, size, out, mat, flap_mat, clasp_mat=None):
    """A belt pouch: a box (width, depth, height) whose front looks toward
    `out` (a horizontal direction), with a flap and an optional clasp."""
    center = Vector(center)
    out = Vector((out[0], out[1], 0.0)).normalized()
    rot = math.atan2(out.x, -out.y)
    mb.box(center, size, mat, rotation_z=rot)
    mb.box(center + Vector((0, 0, size[2] * 0.3)) + out * (size[1] * 0.06),
           (size[0] * 1.08, size[1] * 1.08, size[2] * 0.45), flap_mat, rotation_z=rot)
    if clasp_mat is not None:
        k = size[0] * 0.2
        mb.box(center + Vector((0, 0, size[2] * 0.06)) + out * (size[1] * 0.6), (k, k, k * 1.3), clasp_mat,
               rotation_z=rot + math.pi / 4)


# ----------------------------------------------------------------- skeleton

# The bone each welded garment or head part follows (limbs get their side).
GARMENT_BONES = {
    "cowl": "chest", "scarf": "chest", "shawl": "chest", "sleeve": "upper_arm", "bracer": "lower_arm",
    "cuff": "shin", "fold": "shin", "gather": "shin", "knee": "thigh", "jaw": "head", "muzzle": "head",
    "cheek": "head", "snout": "head", "throat": "head", "eye": "head", "skirt": "hips", "tail": "hips",
}


class AdventurerRig(rigs_human.Humanoid):
    """The shared skeleton plus what these characters need:
    - a welded skirt follows the hips at the belt and each thigh lower down;
    - a welded tail follows its own chain of bones ("tail.1"...);
    - the detail pieces follow the bone the character marked for them while
      making them (Adventurer.mark), whole or with weights per vertex;
    - tails, ponytails and ears move in every clip (pose_extra)."""

    def chain(self, prefix):
        return [b for b in self.bones if b.name.startswith(prefix + ".")]

    def chain_weights(self, p, prefix, root):
        """Weights along a chain of bones (a tail, a ponytail): the nearest
        bone, blending with its neighbors near its ends and with `root`
        where the chain starts."""
        bones = self.chain(prefix)
        i = min(range(len(bones)), key=lambda j: rigs.segment_distance(p, bones[j].head, bones[j].tail))
        b = bones[i]
        ab = b.tail - b.head
        t = max(0.0, min(1.0, (Vector(p) - b.head).dot(ab) / ab.dot(ab)))
        before = bones[i - 1].name if i > 0 else root
        weights = [(b.name, 1.0), (before, max(0.0, 0.35 - t))]
        if i + 1 < len(bones):
            weights.append((bones[i + 1].name, max(0.0, t - 0.65)))
        return weights

    def part_distance(self, p, part):
        """As Humanoid's, but with a capsule's radius where the point is
        (not its largest one): a flared sleeve or bracer does not claim the
        trunk beside it."""
        if part[0] == "ellipsoid":
            return super().part_distance(p, part)
        a, b = Vector(part[1]), Vector(part[2])
        ab = b - a
        t = max(0.0, min(1.0, (Vector(p) - a).dot(ab) / max(ab.dot(ab), 1e-12)))
        return (Vector(p) - (a + ab * t)).length - (part[3] + (part[4] - part[3]) * t)

    def nearest_part(self, p):
        return min(self.spec.parts, key=lambda name: self.part_distance(p, self.spec.parts[name]))

    def surface_weights(self, p):
        part = self.nearest_part(p)
        if part.startswith("skirt"):
            return self.spec.drape(*self.spec.skirt_span)(p)
        if part.startswith("tail"):
            return self.chain_weights(p, "tail", "hips")
        return super().surface_weights(p)

    def bind(self, mb):
        """As Rig.bind, but it tells the welded surface from the detail
        pieces by the vertices themselves, not by their place in the mesh:
        a mesh reuses the room of deleted vertices, so new detail vertices
        can come before `detail_from` (and then got both kinds of weights)."""
        spec = self.spec
        spec.claim(mb)

        def put(v, weights):
            v[mb.deform].clear()
            weights = sorted(((w, n) for n, w in weights if w > 0.0), reverse=True)[:4]
            total = sum(w for w, _ in weights)
            for w, n in weights:
                v[mb.deform][mb._group_index(n)] = w / total

        done = set()
        for v in mb.bm.verts:
            if v in spec.surface_verts:
                put(v, self.surface_weights(v.co))
                continue
            if v in done:
                continue
            piece, stack = [], [v]
            done.add(v)
            while stack:
                u = stack.pop()
                piece.append(u)
                for e in u.link_edges:
                    w = e.other_vert(u)
                    if w not in done:
                        done.add(w)
                        stack.append(w)
            bone = spec.owners.get(v)
            if callable(bone):
                for u in piece:
                    put(u, bone(u.co))
                continue
            if bone is None:
                center = sum((u.co for u in piece), Vector()) / len(piece)
                bone = self.piece_bone(center, piece)
            for u in piece:
                put(u, [(bone, 1.0)])

    def pose_extra(self, clip, t, rot):
        p = TAU * t
        moving = {"walk": 1.0, "run": 1.6}.get(clip, 0.0)
        tail = self.chain("tail")
        for i, bone in enumerate(tail):
            if clip == "fish_sit":
                continue
            if moving:
                side, up = 7.0 * moving * math.sin(p - 0.5 * i), 3.0 * moving * math.cos(2 * p - 0.4 * i)
            elif clip == "idle":
                side, up = 9.0 * math.sin(p - 0.6 * i), 2.0 * math.sin(2 * p - 0.5 * i)
            else:
                side, up = 4.0 * math.sin(p - 0.6 * i), 0.0
            rot[bone.name] = [(rigs.Z, side), (rigs.X, up)]
        if tail and clip == "fish_sit":
            # Sitting, the tail lies on the ground behind.
            lying = (tail[-1].tail - tail[0].head).normalized().rotation_difference(
                Vector((-0.45, 1.0, 0.1)).normalized())
            hips = rot.get("hips", Quaternion())
            hips = hips if isinstance(hips, Quaternion) else Quaternion()
            rot[tail[0].name] = hips.inverted() @ Quaternion(rigs.Z, math.radians(3.0 * math.sin(p))) @ lying
        for i, bone in enumerate(self.chain("ponytail")):
            # The ponytail lags behind the head's bobbing.
            swing = 7.0 * moving * math.cos(2 * p - 0.9 - 0.5 * i) if moving else 1.5 * math.sin(3 * p - 0.6 * i)
            sway = 4.0 * moving * math.sin(p - 0.6 - 0.5 * i) if moving else 2.0 * math.sin(p - 0.6 * i)
            rot[bone.name] = [(rigs.X, swing), (rigs.Z, sway)]
        for bone in self.chain("ear"):
            sx = 1.0 if bone.name.endswith("L") else -1.0
            if moving:
                turn = 5.0 * moving * math.cos(2 * p + 0.6)
            else:  # A flick of one ear, then of the other.
                at = 0.3 if sx > 0 else 0.7
                turn = 14.0 * math.sin(math.pi * max(0.0, min(1.0, (t - at) / 0.08)))
            rot[bone.name] = [(rigs.X, turn)]


# -------------------------------------------------------------- shared body

class Adventurer(Human):
    """Human plus the welded clothing parts these characters share. All
    measures are for the 1.8 m body, as in Human.

    Cloth gets its straight edges from flat(): a welded part is made longer
    than the garment, cut by a plane where the garment ends, and what is
    beyond the plane is flattened onto it (a hem, a sleeve's opening, the
    rim of a cowl or a boot's cuff), painted as the dark inside."""

    remesh_voxel = 0.007
    budget = 1300
    # Parts that flatten() never deforms, even next to a flattened garment.
    PROTECTED = ("head", "jaw", "muzzle", "cheek", "snout", "throat", "eye")

    def __init__(self):
        self.flats = []
        super().__init__()
        self.cuts = [(p, n, self.in_zone(prefixes)) for p, n, prefixes, _ in self.flats]

    # ----------------------------------------------------------- skeleton

    skirt_span = (1.04, 0.66)  # Heights where a welded skirt starts and ends (1.8 m body).

    def extra_bones(self):
        """Hook: the character's own bones (tail, ears, ponytail)."""
        return []

    def make_rig(self):
        bones = {}
        for name in self.parts:
            for garment, bone in GARMENT_BONES.items():
                if name.startswith(garment):
                    side = ".L" if ".L" in name else ".R" if ".R" in name else ""
                    bones[name] = bone + (side if bone in ("upper_arm", "lower_arm", "shin", "thigh") else "")
        return AdventurerRig(self, extra_bones=self.extra_bones(), part_bones=bones)

    def chain_bones(self, prefix, points, parent):
        """Bones "<prefix>.1"... through the points (of the 1.8 m body)."""
        out = []
        for i, (a, b) in enumerate(zip(points, points[1:])):
            out.append(rigs.Bone(f"{prefix}.{i + 1}", self.P(*a), self.P(*b), parent=parent))
            parent = f"{prefix}.{i + 1}"
        return out

    def mark(self, mb, bone):
        """The detail pieces made from here on follow `bone`: a bone's name,
        a function point -> [(bone, weight)] for pieces that bend, or None
        for the nearest bone."""
        self.claim(mb)
        self.marked = bone

    def claim(self, mb):
        """Notes the bone of the detail vertices made since the last mark."""
        for v in mb.bm.verts:
            if v not in self.known_verts:
                self.known_verts.add(v)
                self.owners[v] = self.marked

    def trunk(self, p):
        """Weights of a point on the trunk (belts, straps): hips, spine or
        chest by height, blending across the joints."""
        blend = 0.05 * self.k
        waist, chest = self.z["waist"], self.z["chest"]
        up1 = max(0.0, min(1.0, (p.z - waist) / (2 * blend) + 0.5))
        up2 = max(0.0, min(1.0, (p.z - chest) / (2 * blend) + 0.5))
        return [("hips", 1.0 - up1), ("spine", up1 * (1.0 - up2)), ("chest", up2)]

    def trunk_bone(self, z):
        return "hips" if z < self.z["waist"] else "spine" if z < self.z["chest"] else "chest"

    def drape(self, top, bottom, share=0.85):
        """Weights for cloth hanging from the belt over the legs (a skirt,
        a tabard, a loincloth) between the heights `top` and `bottom` of the
        1.8 m body: the hips at the top, more and more of the thigh on its
        side lower down, so the legs do not pierce it."""
        def weights(p):
            t = max(0.0, min(1.0, (top * self.k - p.z) / ((top - bottom) * self.k))) * share
            left = max(0.0, min(1.0, 0.5 + p.x / (0.1 * self.k)))
            return [("hips", 1.0 - t), ("thigh.L", t * left), ("thigh.R", t * (1.0 - left))]
        return weights

    # ------------------------------------------------------------ building

    def in_zone(self, prefixes):
        return lambda c, n=None: self.zone(c).startswith(prefixes)

    def flat(self, point, normal, prefixes, mat):
        """The parts whose names start with `prefixes` end at the plane
        (point, normal): flat, with a crisp edge, painted `mat`."""
        self.flats.append((Vector(self.P(*point)), Vector(normal).normalized(), tuple(prefixes), mat))

    def distance(self, c, prefixes):
        """Distance from point c to the surface of the parts whose names
        start with `prefixes` (negative inside)."""
        best = 1e9
        for name, p in self.parts.items():
            if not name.startswith(prefixes):
                continue
            if p[0] == "ellipsoid":
                center, r = p[1], p[2]
                q = Vector(((c.x - center[0]) / r[0], (c.y - center[1]) / r[1], (c.z - center[2]) / r[2]))
                d = (q.length - 1.0) * min(r)
            else:
                a, b = Vector(p[1]), Vector(p[2])
                ab = b - a
                t = max(0.0, min(1.0, (Vector(c) - a).dot(ab) / max(ab.dot(ab), 1e-12)))
                d = (Vector(c) - (a + ab * t)).length - (p[3] + (p[4] - p[3]) * t)
            best = min(best, d)
        return best

    # What shows where a garment ends: the limb that comes out of it.
    UNDER = {"sleeve": "upper_arm", "bracer": "forearm", "cuff": "shin", "gather": "shin", "skirt": "thigh"}

    def painted_zone(self, c):
        """zone(c) for paint(): past the plane where a garment ends, the
        zone of the limb under it, so the color border is the straight rim."""
        zone = self.zone(c)
        for p, n, prefixes, _ in self.flats:
            if zone.startswith(prefixes) and (c - p).dot(n) > 0:
                for garment, under in self.UNDER.items():
                    if zone.startswith(garment):
                        return under + (".L" if ".L" in zone else ".R" if ".R" in zone else "")
        return zone

    def flatten(self, mb, near=0.014):
        """Applies the flat() planes; call it first in details(). Beyond a
        plane it moves the garment and what touches it (the limb coming out
        of it, up to `near` from the garment), so the end is one flat face."""
        bm = mb.bm
        for p, n, prefixes, mat in self.flats:
            moved = set()
            for v in bm.verts:
                d = (v.co - p).dot(n)
                if d < 1e-4:
                    continue  # Behind the plane or on its edge.
                zone = self.zone(v.co)
                if zone.startswith(prefixes) or (not zone.startswith(self.PROTECTED)
                                                 and self.distance(v.co, prefixes) < near):
                    v.co -= n * d
                    moved.add(v)
            index = mb._material_index(mat)  # The flat end shows the inside.
            for f in bm.faces:
                if all(v in moved for v in f.verts):
                    f.material_index = index
        bmesh.ops.dissolve_degenerate(bm, dist=1e-5, edges=list(bm.edges))
        bm.normal_update()
        bm.verts.index_update()
        mb.detail_from = len(bm.verts)
        # From here on, new vertices are detail pieces (see mark()).
        self.surface_verts = set(bm.verts)
        self.known_verts = set(self.surface_verts)
        self.owners = {}
        self.marked = None

    def stack(self, parts, name, z0, z1, r0, r1, y0=0.0, y1=0.0, flat=0.03):
        """A cone of cloth: thin flat ellipsoids piled from height z0 (half
        sizes r0 = (x, y)) to z1 (r1), close enough to weld into straight
        walls."""
        steps = max(2, int(abs(z0 - z1) / (flat * 0.8)) + 2)
        for i in range(steps):
            t = i / (steps - 1)
            parts[f"{name}{i}"] = self.ellipsoid((0, y0 + (y1 - y0) * t, z0 + (z1 - z0) * t),
                                                 (r0[0] + (r1[0] - r0[0]) * t, r0[1] + (r1[1] - r0[1]) * t, flat))

    def skirt(self, parts, top, hem, r_top, r_hem, inside, name="skirt", y=0.0):
        """A flared skirt with a straight hem at height `hem`."""
        t = (top - hem + 0.05) / (top - hem)
        low = (r_top[0] + (r_hem[0] - r_top[0]) * t, r_top[1] + (r_hem[1] - r_top[1]) * t)
        self.stack(parts, name, top, hem - 0.05, r_top, low, y0=y, y1=y)
        self.flat((0, 0, hem), (0, 0, -1), (name,), inside)

    def cowl(self, parts, inside, top=1.6, bottom=1.45, r_top=(0.105, 0.1), r_bottom=(0.175, 0.135), rim=1.55,
             tilt=0.5, y=0.01, drape=None, name="cowl", back=0.04):
        """A cowl or scarf: a cone of cloth on the shoulders, open at the
        top (a slanted rim, lower in front, dark inside). `drape` is the
        (center, radii) of the fold hanging on the chest. The top leans
        `back`, clear of the chin: it must stay a voxel away from the head,
        or the two weld together."""
        self.stack(parts, name, top, bottom, r_top, r_bottom, y0=y + back, y1=y - 0.015)
        self.flat((0, y, rim), (0, -tilt, 1), (name,), inside)
        if drape is not None:
            parts[name + "_drape"] = self.ellipsoid(*drape)

    def ended(self, parts, name, a, b, ra, rb, r_limb, inside, reach=0.03):
        """A tube of cloth or leather from a to b that ends at b in a
        straight rim: past b it narrows at once to the limb inside it
        (radius r_limb), and that part is flattened onto the rim."""
        a, b = Vector(a), Vector(b)
        way = (b - a).normalized()
        parts[name] = self.capsule(tuple(a), tuple(b), ra, rb)
        # Thinner than the limb at its far end, so the limb's surface is
        # the limb's zone right after the taper.
        parts[name + "_end"] = self.capsule(tuple(b), tuple(b + way * reach), rb, r_limb - 0.008)
        self.flat(tuple(b), way, (name,), inside)

    def sleeves(self, parts, inside, length=0.6, r0=0.066, r1=0.078):
        """Flared sleeves down to `length` of the upper arm, with a straight
        opening."""
        j, b = self.joints(), self.build
        for side, x in SIDES:
            sh, el = Vector(mirror(j["shoulder"], x)), Vector(mirror(j["elbow"], x))
            self.ended(parts, "sleeve" + side, sh, sh.lerp(el, length), r0 * b, r1 * b, 0.054 * b, inside)

    def bracers(self, parts, inside, r=0.052, top=0.3, flare=1.15):
        """Bracers from `top` of the forearm to the wrist, wider at the
        top, where they end in a straight rim."""
        j, b = self.joints(), self.build
        for side, x in SIDES:
            el, wr = Vector(mirror(j["elbow"], x)), Vector(mirror(j["wrist"], x))
            self.ended(parts, "bracer" + side, wr, el.lerp(wr, top), r * 0.86 * b, r * flare * b, 0.048 * b, inside)

    def shin_point(self, z, x=1):
        j = self.joints()
        t = (j["knee"][2] - z) / (j["knee"][2] - j["ankle"][2])
        return mirror(lerp(j["knee"], j["ankle"], t), x)

    def boots(self, parts, inside, top=0.42, cuff=0.084, cuff_height=0.08, toe=0.15, shaft=0.052, foot=1.0,
              knee=0.066):
        """Slim boots: a shaft, a flared cuff with a straight rim at height
        `top`, a fold at the ankle and a pointed toe. cuff=0 leaves it out."""
        j, b = self.joints(), self.build
        for side, x in SIDES:
            parts["shin" + side] = self.capsule(mirror(j["knee"], x), mirror(j["ankle"], x), knee * b, shaft * b)
            if cuff:
                self.ended(parts, "cuff" + side, self.shin_point(top - cuff_height, x), self.shin_point(top, x),
                           (cuff - 0.02) * b, cuff * b, 0.064 * b, inside)
            ankle = j["ankle"]
            parts["fold" + side] = self.ellipsoid(mirror((ankle[0], ankle[1] - 0.012, ankle[2] + 0.06), x),
                                                  (0.064 * b, 0.074 * b, 0.034))
            parts["foot" + side] = self.capsule(mirror((ankle[0], 0.03, 0.054), x),
                                                mirror((ankle[0] + 0.012, -toe, 0.036), x),
                                                0.054 * b * foot, 0.032 * b * foot)

    def angular_jaw(self, parts):
        """A human jaw with planes: two jaw lines meeting at the chin."""
        hs = self.head_size

        def at(x, y, down):
            return (x * hs, y * hs, 1.8 - down * hs)
        parts["jaw"] = self.ellipsoid(at(0, -0.03, 0.168), (0.06 * hs, 0.068 * hs, 0.05 * hs))
        for side, x in SIDES:
            parts["jawline" + side] = self.capsule(at(x * 0.066, 0.005, 0.162), at(x * 0.016, -0.084, 0.212),
                                                   0.03 * hs, 0.023 * hs)

    def face(self, mb, surf, brow_mat, skin_mat, eye_mat="eye"):
        """Almond eyes, slanted dark brows, a nose wedge and ears."""
        u = self.k * self.head_size
        head = Vector(self.parts["head"][1])
        r = self.parts["head"][2]
        z = self.z["eyes"]
        for s in (-1, 1):
            p = surf.onto((s * 0.037 * u, head.y, z), (0, 1, 0))
            chunk(mb, [p + Vector(q) * u for q in ((s * 0.02, 0.004, 0.002), (-s * 0.016, 0, -0.003), (0, 0, 0.011),
                                                   (0, 0, -0.01), (0, -0.007, 0), (0, 0.02, 0))], eye_mat)
            chunk(mb, [p + Vector(q) * u for q in ((-s * 0.03, -0.012, 0.016), (-s * 0.03, -0.012, 0.03),
                                                   (s * 0.03, -0.002, 0.026), (s * 0.03, -0.002, 0.037),
                                                   (-s * 0.03, 0.02, 0.022), (s * 0.03, 0.02, 0.03))], brow_mat)
            mb.box((s * r[0] * 0.99, head.y + 0.02 * u, z - 0.025 * u), (0.028 * u, 0.035 * u, 0.06 * u), skin_mat)
        p = surf.onto((0, head.y, z - 0.03 * u), (0, 1, 0))
        chunk(mb, [p + Vector(q) * u for q in ((0, 0.012, 0.034), (0, -0.026, -0.012), (-0.015, 0.01, -0.02),
                                               (0.015, 0.01, -0.02), (0, 0.01, -0.024))], skin_mat)

    def toes(self, mb, mat, count=4, spread=0.031, length=0.05):
        """Chunky toes at the front of each foot (paws showing out of a boot)."""
        k = self.k
        for side, _ in SIDES:
            toe = Vector(self.parts["foot" + side][2])
            mid = (count - 1) * 0.5
            for i in range(count):
                x = toe.x + (i - mid) * spread * k
                y = toe.y - (0.02 - abs(i - mid) * 0.01) * k
                w = spread * 0.46 * k
                chunk(mb, [(x - w, y, 0.0), (x + w, y, 0.0), (x, y + 0.02 * k, 0.058 * k),
                           (x - w * 0.85, y - length * k, 0.0), (x + w * 0.85, y - length * k, 0.0),
                           (x, y - length * 0.8 * k, 0.036 * k)], mat)

    def thumbs(self, mb, mat, size=1.0):
        for s in (-1, 1):
            hand = Vector(self.parts["hand.L"][1])
            hand.x *= s
            a = hand + Vector((-s * 0.012, -0.03, 0.02)) * self.k
            tip = hand + Vector((-s * 0.026, -0.066 * size, -0.045 * size)) * self.k
            mb.cylinder(a, tip, 0.018 * self.k * size, 0.011 * self.k * size, mat, segments=4)


# ---------------------------------------------------------------- character

class AdventurerMan(Adventurer):
    name = "adventurer_man"
    height = 1.8
    head_size = 1.0
    shoulder = 0.198
    build = 1.1
    palette = {"tunic": "top", "trousers": "bottom"}   # Materials the game recolors (rigs.palette_name).
    colors = {
        "skin": common.rgb(0xF0B284),
        "tunic": common.rgb(0x3559C0),
        "tunic_light": common.rgb(0x4169D2),
        "tunic_shade": common.rgb(0x25408F),
        "trousers": common.rgb(0x4B4450),
        "leather": common.rgb(0x80432F),
        "leather_dark": common.rgb(0x553027),
        "hair": common.rgb(0x6A3B2A),
        "hair_dark": common.rgb(0x4C2A1E),
        "gold": common.rgb(0xE9A63E),
        "metal": common.rgb(0xA98468),
        "eye": common.rgb(0x1A1414),
    }
    tone_material = "tunic"
    tones = 0.2
    BELT = 1.02      # Heights on the 1.8 m body.
    HEM = 0.66       # The tunic's hem.
    BOOT = 0.42      # The rim of the boot cuffs.
    FINGERS = 0.8    # Below this the gloves leave the fingers bare.

    def __init__(self):
        super().__init__()
        k = self.k
        self.cuts = self.cuts + [
            ((0, 0, self.FINGERS * k), (0, 0, 1), self.in_zone("hand")),
        ]

    def customize(self, parts):
        self.angular_jaw(parts)
        hs = self.head_size
        parts["head"] = self.ellipsoid((0, -0.01, 1.8 - 0.118 * hs), (0.1 * hs, 0.105 * hs, 0.118 * hs))
        self.cowl(parts, "trousers", top=1.545, bottom=1.44, r_top=(0.145, 0.11), r_bottom=(0.19, 0.145), rim=1.545,
                  tilt=0.5, back=0.05, drape=((0, -0.125, 1.425), (0.09, 0.035, 0.07)))
        j, b = self.joints(), self.build
        for side, x in SIDES:  # Loose trousers.
            parts["thigh" + side] = self.capsule(mirror(j["hip"], x), mirror(j["knee"], x), 0.098 * b, 0.076 * b)
        self.sleeves(parts, "tunic_shade", length=0.8, r0=0.066, r1=0.082)
        self.skirt(parts, self.BELT + 0.04, self.HEM, (0.175, 0.13), (0.245, 0.168), "trousers")
        self.bracers(parts, "skin", r=0.052, top=0.4)
        self.boots(parts, "trousers", top=self.BOOT, cuff_height=0.09, knee=0.074)

    def paint(self, c, n):
        k = self.k
        zone = self.painted_zone(c)
        if zone.startswith("cowl"):
            return "tunic_shade"
        if zone.startswith(("sleeve", "shoulder", "chest", "waist", "hips", "skirt")):
            return "tunic"
        if zone.startswith("bracer"):
            return "leather_dark"
        if zone.startswith("hand"):
            return "leather_dark" if c.z > self.FINGERS * k else "skin"
        if zone.startswith(("cuff", "fold", "foot")):
            return "leather"
        if zone.startswith("shin"):
            return "leather" if c.z < self.BOOT * k else "trousers"
        if zone.startswith("thigh"):
            return "trousers" if c.z < self.HEM * k else "tunic"
        return "skin"

    def hair(self, mb):
        """A wide tousled mass with a fringe swept to his left."""
        k = self.k
        head = Vector(self.parts["head"][1])
        r = self.parts["head"][2]

        def at(x, y, z):
            return head + Vector((x * r[0], y * r[1], z * r[2]))

        def keep(d):
            return d.z > (0.1 - 0.45 * d.y if d.y < 0 else max(-0.6, 0.1 - 1.2 * d.y))
        hair_cap(mb, at(0, 0.03, 0.04), r, "hair", keep, scale=(1.2, 1.18, 1.3), count=70)
        rnd = random.Random(11)
        tufts = [
            ((0.2, -0.72, 0.98), (0.95, 0.5, 0.36)),     # The fringe over the forehead.
            ((0.62, -0.25, 1.12), (0.72, 0.75, 0.42)),
            ((-0.6, -0.2, 1.08), (0.7, 0.75, 0.4)),
            ((0.0, 0.5, 1.12), (0.98, 0.7, 0.45)),
            ((0.0, 1.0, 0.35), (0.95, 0.42, 0.7)),       # The back of the head.
            ((-0.95, 0.35, 0.4), (0.4, 0.6, 0.5)),
            ((0.95, 0.35, 0.4), (0.4, 0.6, 0.5)),
        ]
        for i, (c, h) in enumerate(tufts):
            pts = studies.ellipsoid_points(at(*c), (h[0] * r[0], h[1] * r[1], h[2] * r[2]), 9, rnd)
            chunk(mb, pts, "hair_dark" if i % 2 else "hair")
        shards = [
            ((0.45, -0.9, 0.95), (0.95, -1.3, 0.75), 0.05),      # Fringe tips.
            ((-0.1, -0.95, 0.95), (-0.35, -1.3, 0.62), 0.045),
            ((-0.6, -0.8, 0.9), (-0.95, -1.05, 0.6), 0.04),
            ((0.75, -0.3, 1.25), (1.3, -0.4, 1.5), 0.055),
            ((0.2, -0.2, 1.35), (0.5, -0.4, 1.75), 0.055),
            ((-0.5, -0.1, 1.3), (-0.95, -0.1, 1.6), 0.05),
            ((0.3, 0.6, 1.3), (0.6, 0.85, 1.65), 0.055),
            ((-0.4, 0.75, 1.15), (-0.7, 1.15, 1.4), 0.05),
            ((0.0, 1.15, 0.2), (0.0, 1.45, -0.35), 0.05),
            ((-1.0, -0.05, 0.3), (-1.08, -0.3, -0.35), 0.03),    # Sideburns.
            ((1.0, -0.05, 0.3), (1.08, -0.3, -0.35), 0.03),
        ]
        for i, (a, b, rad) in enumerate(shards):
            spike(mb, at(*a), at(*b), rad * k, "hair_dark" if i % 3 == 0 else "hair")

    def details(self, mb):
        k = self.k
        self.flatten(mb)
        surf = Surface(mb)
        self.mark(mb, "head")
        self.face(mb, surf, "hair_dark", "skin")
        self.hair(mb)
        self.mark(mb, None)
        self.thumbs(mb, "skin")

        def under_cowl(p):
            return self.zone(p).startswith("cowl")
        # Crossed chest straps, the wide belt and its buckle.
        self.mark(mb, self.trunk)
        for s in (-1, 1):
            strap(mb, surf, (0, 0, 1.22 * k), (s * 0.7, 0, 0.71), 0.046 * k, "leather", thick=0.01, skip=under_cowl)
        strap(mb, surf, (0, 0, self.BELT * k), (0, 0, 1), 0.095 * k, "leather", thick=0.014, segments=14)
        front = surf.onto((0.015 * k, 0, self.BELT * k), (0, 1, 0))
        self.mark(mb, "hips")
        buckle(mb, front + Vector((0, -0.02, 0)) * k, 0.105 * k, "metal", "leather_dark")
        # The belt's end hangs over the skirt, with a lighter tip.
        self.mark(mb, self.drape(self.BELT, self.HEM))
        top = surf.onto((0.085 * k, 0, (self.BELT - 0.04) * k), (0, 1, 0)) + Vector((0, -0.016, 0))
        low = surf.onto((0.105 * k, 0, (self.HEM + 0.1) * k), (0, 1, 0)) + Vector((0, -0.012, 0))
        w = Vector((0.03 * k, 0, 0))
        studies.plate(mb, [top - w, top + w, low + w, low - w], 0.012, "leather")
        tip = low + Vector((0, -0.004, -0.085 * k))
        studies.plate(mb, [low - w, low + w, tip + w, tip + Vector((0, 0, 0.035 * k)), tip - w], 0.012, "gold")
        # The gold clasp of the cowl, on his left.
        self.mark(mb, "chest")
        p = surf.onto((0.115 * k, 0, 1.4 * k), (0, 1, 0)) + Vector((0, -0.01 * k, 0))
        chunk(mb, [p + Vector(q) * k for q in ((0.012, 0, 0.05), (-0.012, 0, -0.05), (0.038, 0, -0.008), (-0.038, 0, 0.008),
                                               (0, -0.02, 0), (0, 0.02, 0))], "gold")
        # The sword on the back: the hilt shows over the right shoulder.
        a = Vector((-0.1, 0.16, 1.36)) * k
        d = Vector((-0.55, 0.05, 0.83)).normalized()
        mb.cylinder(a + d * 0.06 * k, a + d * 0.3 * k, 0.026 * k, 0.023 * k, "leather_dark", segments=5)
        tube(mb, [(a + d * 0.29 * k, 0.0), (a + d * 0.335 * k, 0.045 * k), (a + d * 0.385 * k, 0.0)], "gold", sides=4)
        side = d.cross(Vector((0, 1, 0))).normalized()
        g = a + d * 0.05 * k
        studies.plate(mb, [g - side * 0.11 * k, g - side * 0.07 * k + d * 0.035 * k, g + side * 0.07 * k + d * 0.035 * k,
                           g + side * 0.11 * k, g + side * 0.05 * k - d * 0.035 * k, g - side * 0.05 * k - d * 0.035 * k],
                      0.03 * k, "metal")
        e = a - d * 0.62 * k  # The scabbard, down to the left hip.
        w2 = side * 0.04 * k
        studies.plate(mb, [g - w2, g + w2, e + w2 * 0.7, e - d * 0.05 * k, e - w2 * 0.7], 0.03 * k, "leather_dark")


SPECS = [AdventurerMan()]
