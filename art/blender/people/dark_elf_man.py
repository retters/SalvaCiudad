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
import rigs
import rigs_human
import studies
from _human import Human
from _people_kit import arc, ribbon
from _people_kit import hull as solid
from rigs import Bone, Pose, smooth


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


# --------------------------------------------------------------------- rig

class ClothRig(rigs_human.Humanoid):
    """The shared skeleton plus what long clothes need:
    - chains of cloth bones (a cape, the back of a coat, a hanging panel)
      that hang by gravity in every clip, lean out of the way of the legs
      and lie on the ground when the character sits;
    - weights for skirts that follow the legs (leg_weights, coat_weights);
    - the bone or the weights of each detail piece, as the character
      marked them while building (Figure.mark);
    - soft weights for welded parts (Figure.soft_parts: long hair).

    chains: (name, parent bone, points from top to bottom of a 1.8 m body,
    hangs behind the body: True, or in front of it: False). The bones are
    called <name>.1, <name>.2...
    """

    def __init__(self, spec, chains=(), part_bones=None, extra_bones=()):
        bones = []
        self.chains = []
        for name, parent, points, back in chains:
            names = []
            pts = [Vector(spec.P(*p)) for p in points]
            for i, (a, b) in enumerate(zip(pts, pts[1:])):
                bones.append(Bone(f"{name}.{i + 1}", a, b, parent=names[-1] if names else parent))
                names.append(f"{name}.{i + 1}")
            self.chains.append((name, names, parent, back))
        super().__init__(spec, extra_bones=bones + list(extra_bones), part_bones=part_bones)

    # ------------------------------------------------------------ binding

    def bind(self, mb):
        """As Rig.bind, but telling the welded surface from the details by
        the vertices themselves (Figure.begin) and not by their order: a
        vertex added by a detail may take the place of one deleted while
        the surface was cut, and then the order is not that of creation."""
        surface = self.spec.surface

        def put(v, weights):
            weights = sorted(((w, n) for n, w in weights if w > 0.0), reverse=True)[:4]
            total = sum(w for w, _ in weights)
            for w, n in weights:
                v[mb.deform][mb._group_index(n)] = w / total

        seen = set()
        for v in mb.bm.verts:
            if v in surface:
                put(v, self.surface_weights(v.co))
            elif v not in seen:
                piece, stack = [], [v]
                seen.add(v)
                while stack:
                    u = stack.pop()
                    piece.append(u)
                    for e in u.link_edges:
                        w = e.other_vert(u)
                        if w not in seen:
                            seen.add(w)
                            stack.append(w)
                center = sum((u.co for u in piece), Vector()) / len(piece)
                soft = self.piece_weights(center, piece)
                bone = self.piece_bone(center, piece) if soft is None else None
                for u in piece:
                    put(u, [(bone, 1.0)] if soft is None else soft(u.co))

    def role(self, piece):
        return self.spec.roles.get(piece[0])

    def piece_bone(self, center, piece):
        """The bone the character marked for the piece ("shin.?" takes the
        side the piece is on); unmarked pieces follow the bone of the body
        part they sit on."""
        role = self.role(piece)
        if isinstance(role, str):
            return role.replace("?", "L" if center.x > 0 else "R")
        return self.nearest_bone(center)

    def piece_weights(self, center, piece):
        role = self.role(piece)
        return role if callable(role) else None

    def surface_weights(self, p):
        best, name = 1e9, None
        for part_name, part in self.spec.parts.items():
            d = self.part_distance(p, part)
            if d < best:
                best, name = d, part_name
        soft = self.spec.soft_parts.get(name)
        return getattr(self.spec, soft)(p) if soft else super().surface_weights(p)

    def leg_weights(self, p):
        """A skirt around the legs: the hips at the belt, then the thigh
        of its side (both in the middle), then partly the shin."""
        k = self.k
        left = max(0.0, min(1.0, 0.5 + p.x / (0.16 * k)))
        down = smooth((0.98 * k - p.z) / (0.3 * k))
        low = max(0.0, min(0.65, (self.by_name["shin.L"].head.z - p.z) / (0.35 * k)))
        out = [("hips", 1.0 - down)]
        for side, share in (("L", left), ("R", 1.0 - left)):
            out += [(f"thigh.{side}", down * share * (1.0 - low)), (f"shin.{side}", down * share * low)]
        return out

    def chain_weights(self, name):
        """point -> weights along a chain of cloth bones: its parent above
        the chain, then each bone, blending around the joints."""
        names, parent = next((n, p) for c, n, p, _ in self.chains if c == name)
        bones = [self.by_name[n] for n in names]
        k = self.k

        def weights(p):
            below = [1.0 - smooth((p.z - (bones[0].head.z - 0.12 * k)) / (0.12 * k))]
            below += [smooth((b.head.z + 0.07 * k - p.z) / (0.14 * k)) for b in bones[1:]] + [0.0]
            return [(parent, 1.0 - below[0])] + [(b.name, max(0.0, below[i] - below[i + 1]))
                                                 for i, b in enumerate(bones)]
        return weights

    def coat_weights(self, name):
        """point -> weights of a long coat or skirt: its back follows the
        chain `name`, its front and sides follow the legs."""
        chain = self.chain_weights(name)

        def weights(p):
            back = smooth(p.y / (abs(p.x) + abs(p.y) + 1e-6) / 0.55)
            out = {}
            for bone, w in [(n, w * (1.0 - back)) for n, w in self.leg_weights(p)] + \
                    [(n, w * back) for n, w in chain(p)]:
                out[bone] = out.get(bone, 0.0) + w
            return sorted(out.items())
        return weights

    # -------------------------------------------------------------- poses

    def obstacles(self, pose):
        """What cloth must hang clear of: the trunk and the legs, as
        (start, end, radius)."""
        k = self.k
        segs = [(pose.head("hips"), pose.tail("spine"), 0.105 * k)]
        for side in ("L", "R"):
            hip, knee, ankle = pose.head(f"thigh.{side}"), pose.head(f"shin.{side}"), pose.tail(f"shin.{side}")
            segs += [(hip, knee, 0.095 * k), (knee, ankle, 0.075 * k), (ankle, pose.tail(f"foot.{side}"), 0.06 * k)]
        return segs

    def hang(self, pose, names, parent, back, segs):
        """Poses a chain of cloth bones: each hangs as at rest, leans away
        from the body (backward or forward, as the body is turned) as far
        as it must to clear the legs, and lies along the ground rather than
        sinking into it."""
        k = self.k
        sign = 1.0 if back else -1.0
        out = pose.world(parent) @ Vector((0.0, sign, 0.0))
        out = Vector((out.x, out.y, 0.0)).normalized()

        def flat(p):
            """The point in the upright plane the cloth swings in."""
            return Vector((0.0, p.dot(out), p.z))

        for name in names:
            bone = self.by_name[name]
            rest = bone.tail - bone.head
            head = pose.head(name)
            first = math.degrees(math.atan2(sign * rest.y, -rest.z))
            for step in range(160):
                a = math.radians(min(150.0, first + step))
                d = out * math.sin(a) + Vector((0.0, 0.0, -math.cos(a)))
                clear = True
                for t in (0.5, 1.0):
                    q = head + d * (rest.length * t)
                    if q.z < 0.02 * k:
                        clear = False
                    for s, e, r in segs:
                        if rigs.segment_distance(flat(q), flat(s), flat(e)) < r + 0.025 * k:
                            clear = False
                if clear:
                    break
            pose.aim(name, d)

    def clips(self):
        out = []
        for name, frames, loops, fn, speed in super().clips():
            def posed(t, fn=fn, name=name):
                q, offset, extra = fn(t)
                pose = Pose(self, offset)
                pose.q = q
                self.spec.pose_fix(self, name, t, pose)
                segs = self.obstacles(pose)
                for _, names, parent, back in self.chains:
                    self.hang(pose, names, parent, back, segs)
                self.spec.pose_after(self, name, t, pose)
                return pose.q, pose.offset, extra
            out.append((name, frames, loops, posed, speed))
        return out


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
    # The skeleton (see ClothRig): chains of cloth bones, the bones of the
    # welded parts the character added, and the welded parts with weights
    # of their own {part: name of the method point -> weights}.
    chains = ()
    part_bones = {}
    soft_parts = {}

    def make_rig(self):
        self.roles = {}
        self.surface = set()
        return ClothRig(self, chains=self.chains, part_bones=self.part_bones, extra_bones=self.extra_bones())

    def extra_bones(self):
        return ()

    def pose_fix(self, rig, clip, t, pose):
        """Hook: change a clip's pose for this character, before its cloth hangs."""

    def pose_after(self, rig, clip, t, pose):
        """Hook: pose the character's own bones, after its cloth hangs."""

    def begin(self, mb):
        """Starts the details: from here on mark() says what they follow."""
        self.roles = {}
        self.surface = set(mb.bm.verts)
        self.marked = set(self.surface)

    def mark(self, mb, role):
        """The detail pieces added since the last mark follow `role`: a
        bone ("shin.?": the one of the side the piece is on) or a function
        point -> [(bone, weight)] for a piece that bends. Unmarked pieces
        follow the bone of the body part they sit on. (By vertex and not by
        index: a new vertex may take the place of a deleted one.)"""
        for v in mb.bm.verts:
            if v not in self.marked:
                self.marked.add(v)
                self.roles[v] = role

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
        tris, seen = [], set()   # In the order of the mesh, so every build is the same.
        for v in mask:
            for f in v.link_faces:
                if f not in seen:
                    seen.add(f)
                    tris.append([u.co.copy() for u in f.verts])

        def on(x, z, off=0.0025):
            """The point of the mask's front at head offsets (x, z)."""
            origin = H(x, -0.5, z)
            hits = [geometry.intersect_ray_tri(a, b, c, Vector((0, 1, 0)), origin, True) for a, b, c in tris]
            hits = [round(h.y, 5) for h in hits if h is not None]
            y = min(hits) if hits else H(x, -0.1, z).y
            return Vector((origin.x, y - off * self.k, origin.z))

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
    part_bones = {"hair_cap": "head", "hair_side.L": "head", "hair_side.R": "head"}
    soft_parts = {"hair_back": "hair_weights"}

    def hair_weights(self, p):
        """The hair down the back: with the head at the top, then lying on
        the back (chest, then spine), so it does not cut into the shoulders
        when the head turns."""
        z = self.z
        head = smooth((p.z - (z["neck"] - 0.1 * self.k)) / (0.14 * self.k))
        low = smooth((z["chest"] - p.z) / (0.15 * self.k))
        return [("head", head), ("chest", (1.0 - head) * (1.0 - low)), ("spine", (1.0 - head) * low)]

    def head_details(self, mb, **face):
        """Face, ears and hair, each following its bone."""
        self.face(mb, **face)
        self.ears(mb)
        self.hair(mb)

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
        self.mark(mb, "head")
        if not self.hair_ends:
            return
        (cx, cy, cz), (rx, ry, rz) = self.hair_back
        for x, w, drop in ((-0.62, 0.3, 0.07), (0.0, 0.34, 0.12), (0.62, 0.3, 0.07)):
            z0 = cz - rz * 0.72
            solid(mb, [self.V(cx + (x - w) * rx, cy, z0), self.V(cx + (x + w) * rx, cy, z0),
                       self.V(cx + x * rx, cy - ry * 0.7, z0), self.V(cx + x * rx, cy + ry * 0.75, z0),
                       self.V(cx + x * rx, cy + ry * 0.2, cz - rz - drop)], mat)
        self.mark(mb, self.hair_weights)

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
    chains = (("cape", "chest", ((0, 0.17, 1.36), (0, 0.2, 1.0), (0, 0.23, 0.62), (0, 0.25, 0.3)), True),)
    part_bones = dict(Elf.part_bones, cowl="chest", cowl_back="chest")
    lock = (0.072, -0.13, 1.385)
    lock_mid = -0.135
    ear = (0.1, 0.09)
    palette = {"cloak": "top", "tunic": "bottom"}   # Materials the game recolors (rigs.palette_name).
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

    def mantle_weights(self, p):
        """The mantle lies on the chest; over each arm it lifts with it."""
        k = self.k
        arm = 0.75 * smooth((abs(p.x) - 0.13 * k) / (0.1 * k)) * smooth((1.5 * k - p.z) / (0.12 * k))
        return [("chest", 1.0 - arm), ("upper_arm.L" if p.x > 0 else "upper_arm.R", arm)]

    def details(self, mb):
        k = self.k
        self.begin(mb)
        self.head_details(mb, eye="dark", brow="dark")
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
        self.mark(mb, self.mantle_weights)
        # The cape: from under the mantle down to the calves.
        xs = (1.0, 0.72, 0.36, 0.0, -0.36, -0.72, -1.0)
        ys = (0.0, 0.62, 0.8, 1.0, 0.8, 0.62, 0.0)
        cape = []
        for z, w, d, jag in ((1.36, 0.235, 0.14, 0), (1.0, 0.27, 0.17, 0), (0.62, 0.3, 0.2, 0), (0.37, 0.315, 0.22, 1)):
            cape.append([self.V(x * w, 0.03 + y * d + (0.022 if i % 2 else 0.0) * (1.4 - z),
                                z - (0.07 if jag and i % 2 == 0 else 0.0)) for i, (x, y) in enumerate(zip(xs, ys))])
        sheet(mb, cape, 0.014 * k, "cloak", back="dark")
        self.mark(mb, self.rig.chain_weights("cape"))
        # The skirt of the tunic, open at the front.
        skirt = self.skirt_rows([(1.08, 0.15, 0.108, 0.0), (0.86, 0.178, 0.128, 0.0), (0.6, 0.195, 0.145, 0.0)],
                                arc(-80, 260, 9), jag=0.025)
        sheet(mb, skirt, 0.012 * k, "tunic", back="dark", trim="tunic_trim", hem=0.028 * k, sides=0.028 * k)
        self.mark(mb, self.rig.leg_weights)
        # Belt and buckle, and a second strap sagging over his right hip.
        self.ring(mb, 1.115, 0.06, 0.014, "leather")
        self.ring(mb, 1.06, 0.034, 0.02, "leather", tilt=0.25, count=10)
        b = self.front(0.012, 1.115, 0.024)
        mb.box(b, (0.068 * k, 0.014 * k, 0.066 * k), "silver")
        mb.box(b - Vector((0, 0.006 * k, 0)), (0.036 * k, 0.014 * k, 0.034 * k), "leather")
        self.mark(mb, "spine")
        # The clasp where the strap meets the mantle.
        mb.box(self.V(0.035, -0.118, self.CLASP - 0.012), (0.055 * k, 0.02 * k, 0.036 * k), "silver",
               rotation_z=math.radians(-12))
        self.mark(mb, "chest")
        # Bracers, knee guards and heels.
        for side in (".L", ".R"):
            self.cuff(mb, "forearm" + side, 0.25, 0.92, 0.009, "leather")
        self.mark(mb, "lower_arm.?")
        for s in (-1, 1):
            self.knee_guard(mb, s, "leather", 1.05)
        self.mark(mb, "shin.?")
        self.heels(mb, "boot")
        self.mark(mb, "foot.?")


SPECS = [DarkElfMan()]
