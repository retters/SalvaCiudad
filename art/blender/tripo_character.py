"""Turns a character sculpted by Tripo (a mesh without skeleton, texture or
colors) into a low-poly animated character. Used by tripo_build.py.

1. The mesh is turned to face -Y, stood on Z = 0 and scaled to a height.
2. Its joints are found by shape: horizontal slices of the mesh fall into
   separate pieces where the arms and the legs are apart from the trunk,
   which gives the armpits, the crotch and the limbs' axes.
3. It is reduced by edge collapse to the character triangle limit and shaded
   flat (the look of the other low-poly models).
4. Its colors come from the picture the model was generated from: the view
   of the model whose silhouette matches the picture best is found, each
   face takes the color the picture has where the face is seen, and the
   faces the picture does not show take the color of their mirror image or
   of the nearest colored face. The colors are grouped into a few
   materials.
5. It gets the characters' skeleton and clips (rigs_human.Humanoid).
"""

import math

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

import common
import rigs
import rigs_human

SLICES = 72          # Horizontal slices the shape is analyzed with.
SILHOUETTE = 180     # Height in pixels of the silhouettes compared.
MAX_COLORS = 12      # Materials: each one is a draw call.


# ------------------------------------------------------------------ shape

def vertices(mesh):
    out = np.empty(len(mesh.data.vertices) * 3, dtype=np.float64)
    mesh.data.vertices.foreach_get("co", out)
    return out.reshape(-1, 3)


def orient(mesh, height, front=None):
    """Bakes the object's transform into the mesh so it faces -Y, stands on
    Z = 0 over the origin and is `height` tall."""
    mesh.data.transform(mesh.matrix_world)
    mesh.parent = None
    mesh.matrix_world = Matrix.Identity(4)
    v = vertices(mesh)
    lo, hi = v.min(axis=0), v.max(axis=0)
    h = hi[2] - lo[2]
    if front is None:
        # Arms make a character wider than deep; its toes point forward.
        side = 0 if hi[0] - lo[0] > hi[1] - lo[1] else 1
        axis = 1 - side
        feet = v[v[:, 2] < lo[2] + 0.04 * h][:, axis].mean()
        shins = v[(v[:, 2] > lo[2] + 0.1 * h) & (v[:, 2] < lo[2] + 0.2 * h)][:, axis].mean()
        forward = np.zeros(2)
        forward[axis] = 1.0 if feet > shins else -1.0
    else:
        forward = {"+x": (1, 0), "-x": (-1, 0), "+y": (0, 1), "-y": (0, -1)}[front]
    turn = Matrix.Rotation(-math.pi / 2 - math.atan2(forward[1], forward[0]), 4, "Z")   # Brings `forward` onto -Y.
    trunk = v[(v[:, 2] > lo[2] + 0.45 * h) & (v[:, 2] < lo[2] + 0.6 * h)].mean(axis=0)
    scale = height / h
    mesh.data.transform(Matrix.Scale(scale, 4) @ turn @ Matrix.Translation((-trunk[0], -trunk[1], -lo[2])))


class Piece:
    """A connected piece of a horizontal slice of the mesh."""

    def __init__(self, points):
        p = np.array(points)
        self.center = Vector(p.mean(axis=0))
        self.lo, self.hi = p.min(axis=0), p.max(axis=0)
        self.count = len(points)

    @property
    def radius(self):
        return 0.25 * ((self.hi[0] - self.lo[0]) + (self.hi[1] - self.lo[1]))

    def spans_middle(self, margin):
        return self.lo[0] < -margin and self.hi[0] > margin


def slices(mesh, height):
    """For each slice height, the pieces the mesh is cut into there."""
    bm = bmesh.new()
    bm.from_mesh(mesh.data)
    step = height / SLICES
    buckets = [[] for _ in range(SLICES)]
    for f in bm.faces:
        zs = [v.co.z for v in f.verts]
        for i in range(max(1, int(min(zs) / step) + 1), min(SLICES, int(max(zs) / step) + 1)):
            buckets[i].append(f)
    out = {}
    for i, faces in enumerate(buckets):
        if not faces:
            continue
        parent = {}

        def find(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a

        for f in faces:
            ids = [v.index for v in f.verts]
            for a in ids:
                parent.setdefault(a, a)
            for a in ids[1:]:
                parent[find(a)] = find(ids[0])
        groups = {}
        cos = {v.index: v.co for f in faces for v in f.verts}
        for a in sorted(parent):
            groups.setdefault(find(a), []).append(tuple(cos[a]))
        out[i * step] = sorted((Piece(g) for g in groups.values() if len(g) >= 6), key=lambda p: -p.count)
    bm.free()
    return out


def chain_of(cut, side, start_z, pick, step, direction, height):
    """Follows a limb through the slices from `start_z`, up (direction 1)
    or down (-1): at each slice, the piece on that side nearest to the one
    before. Stops where the limb joins the trunk or ends."""
    chain = []
    z = start_z
    last = None
    while 0.0 < z < height:
        key = min(cut, key=lambda k: abs(k - z)) if cut else None
        pieces = [p for p in cut.get(key, []) if p.center.x * side > 0 and not p.spans_middle(0.015 * height)]
        if last is None:
            pieces = [p for p in pieces if pick(p)]
            found = max(pieces, key=lambda p: p.count, default=None)
        else:
            near = [p for p in pieces if (p.center.to_2d() - last.center.to_2d()).length < 0.07 * height]
            found = max(near, key=lambda p: p.count, default=None)
        if found is None:
            if last is not None:
                break
        else:
            chain.append((key, found))
            last = found
        z += direction * step
    return chain


def at(chain, z):
    """The piece of a limb's chain nearest to height z."""
    return min(chain, key=lambda item: abs(item[0] - z))[1]


class FittedBody:
    """The body found in a mesh, in the form rigs_human.Humanoid takes: the
    landmarks, the joints and the body parts of people._human.Human."""

    def __init__(self, mesh, height):
        self.k = height / 1.8
        self.height = height
        h = height
        cut = slices(mesh, h)
        step = h / SLICES
        trunk = {z: next((p for p in pieces if p.spans_middle(0.015 * h)), None) for z, pieces in cut.items()}
        self.parts = {}
        self.sides = {}
        self.part_bones = {}   # Parts beyond the body's own: which bone each follows.
        problems = []
        limbs = {}
        for name, side in (("L", 1.0), ("R", -1.0)):
            leg = chain_of(cut, side, 0.06 * h, lambda p: True, step, 1, h)
            if len(leg) < SLICES // 5:
                problems.append("legs")
                continue
            in_leg = {id(p) for _, p in leg}
            # The arm: the piece farthest out that is not the leg, followed
            # down from the highest slice where it is apart from the trunk.
            tops = [(z, p) for z, pieces in cut.items() for p in pieces
                    if 0.45 * h < z < 0.9 * h and p.center.x * side > 0.09 * h and id(p) not in in_leg
                    and not p.spans_middle(0.015 * h)]
            if not tops:
                problems.append("arms")
                continue
            top_z = max(z for z, _ in tops)
            best = None
            for z0 in sorted({z for z, _ in tops if z > top_z - 0.2 * h}, reverse=True):
                arm = chain_of(cut, side, z0, lambda p: p.center.x * side > 0.09 * h and id(p) not in in_leg,
                               step, -1, h)
                if best is None or len(arm) > len(best):
                    best = arm
            arm = best
            if len(arm) < SLICES // 8:
                problems.append("arms")
                continue
            limbs[name] = (side, leg, arm)
        self.problem = ", ".join(sorted(set(problems)))
        if self.problem:
            return
        # An arm that reaches much lower than the other holds something (a
        # dagger hanging from the hand): the hand ends where the other does.
        lowest = {name: arm[-1][0] for name, (_, _, arm) in limbs.items()}
        for name, (side, leg, arm) in limbs.items():
            crotch = leg[-1][0]
            armpit, tips = arm[0][0], arm[-1][0]
            other = lowest["R" if name == "L" else "L"]
            if other - tips > 0.04 * h:
                held = [p for z, p in arm if z < other]
                self.parts["held." + name] = ("capsule", tuple(at(arm, other).center), tuple(arm[-1][1].center),
                                              max(p.radius for p in held), max(p.radius for p in held))
                self.part_bones["held." + name] = "hand." + name
                tips = other
            top = arm[0][1]
            shoulder = Vector((top.center.x - side * 0.005 * h, top.center.y, armpit + 0.03 * h))
            wrist_z = tips + 0.1 * h
            wrist = at(arm, wrist_z).center.copy()
            hand = at(arm, tips + 0.045 * h).center.copy()
            elbow = at(arm, (shoulder.z + wrist_z) / 2).center.copy()
            hip_piece = leg[-1][1]
            hip = Vector((hip_piece.center.x, hip_piece.center.y, crotch + 0.05 * h))
            ankle = at(leg, 0.06 * h).center.copy()
            line = (ankle - hip).normalized()
            between = [p.center for z, p in leg if ankle.z + 0.12 * h < z < hip.z - 0.12 * h]
            knee = max(between, key=lambda c: ((c - hip) - line * (c - hip).dot(line)).length,
                       default=hip.lerp(ankle, 0.5)).copy()
            r_arm = (top.radius, at(arm, elbow.z).radius, at(arm, wrist.z).radius)
            r_leg = (hip_piece.radius, at(leg, knee.z).radius, at(leg, ankle.z).radius)
            self.sides[name] = {"shoulder": shoulder, "elbow": elbow, "wrist": wrist, "hand": hand, "hip": hip,
                                "knee": knee, "ankle": ankle}
            s = "." + name
            self.parts["shoulder" + s] = ("ellipsoid", tuple(shoulder), (r_arm[0] * 1.15,) * 3)
            self.parts["upper_arm" + s] = ("capsule", tuple(shoulder), tuple(elbow), r_arm[0], r_arm[1])
            self.parts["forearm" + s] = ("capsule", tuple(elbow), tuple(wrist), r_arm[1], r_arm[2])
            tip = at(arm, tips + 0.02 * h)
            self.parts["hand" + s] = ("ellipsoid", tuple(hand),
                                      (max(r_arm[2], tip.radius) * 1.3, max(r_arm[2], tip.radius) * 1.5, 0.06 * h))
            self.parts["thigh" + s] = ("capsule", tuple(hip), tuple(knee), r_leg[0], r_leg[1])
            self.parts["shin" + s] = ("capsule", tuple(knee), tuple(ankle), r_leg[1], r_leg[2])
            self.parts["foot" + s] = ("capsule", (ankle.x, ankle.y + 0.02 * h, 0.03 * h),
                                      (ankle.x, ankle.y - 0.1 * h, 0.03 * h), 0.03 * h, 0.03 * h)
        left, right = self.sides["L"], self.sides["R"]
        hip_z = (left["hip"].z + right["hip"].z) / 2
        shoulder_z = (left["shoulder"].z + right["shoulder"].z) / 2
        half = min(abs(left["shoulder"].x), abs(right["shoulder"].x))
        # The neck: where the trunk is narrowest above the shoulders.
        necks = [(p.hi[0] - p.lo[0], z) for z, p in trunk.items()
                 if p is not None and shoulder_z + 0.02 * h < z < min(h - 0.1 * h, shoulder_z + 0.14 * h)]
        neck_z = min(necks)[1] if necks else shoulder_z + 0.06 * h
        self.z = {"sole": 0.0, "ankle": 0.06 * h, "knee": (left["knee"].z + right["knee"].z) / 2, "crotch": hip_z - 0.05 * h,
                  "hip": hip_z, "waist": hip_z + 0.33 * (shoulder_z - hip_z), "chest": hip_z + 0.72 * (shoulder_z - hip_z),
                  "shoulder": shoulder_z, "neck": max(shoulder_z + 0.02 * h, neck_z - 0.02 * h),
                  "chin": neck_z + 0.01 * h, "eyes": (neck_z + h) / 2, "top": h}
        arm_r = self.parts["upper_arm.L"][3]

        def trunk_part(z, dz):
            p = trunk.get(min(trunk, key=lambda k: abs(k - z)))
            rx = min(half - arm_r * 0.5, (p.hi[0] - p.lo[0]) / 2) if p is not None else half * 0.8
            ry = (p.hi[1] - p.lo[1]) / 2 if p is not None else half * 0.6
            return ("ellipsoid", (0.0, 0.0, z), (max(rx, 0.03 * h), max(min(ry, half), 0.03 * h), dz))

        self.parts["hips"] = trunk_part(hip_z + 0.02 * h, 0.09 * h)
        self.parts["waist"] = trunk_part(self.z["waist"], 0.09 * h)
        self.parts["chest"] = trunk_part(self.z["chest"] + 0.03 * h, 0.1 * h)
        self.parts["neck"] = ("capsule", (0, 0, self.z["neck"] - 0.02 * h), (0, 0, self.z["chin"]), 0.04 * h, 0.04 * h)
        head = trunk.get(min(trunk, key=lambda k: abs(k - self.z["eyes"])))
        self.parts["head"] = ("ellipsoid", (0.0, head.center.y if head else 0.0, self.z["eyes"]),
                              ((head.hi[0] - head.lo[0]) / 2 if head else 0.08 * h,
                               (head.hi[1] - head.lo[1]) / 2 if head else 0.08 * h, (h - self.z["chin"]) / 2))

    def P(self, x, y, z):
        return (x * self.k, y * self.k, z * self.k)

    def joints(self):
        """The left side's joints for a 1.8 m body, as Human.joints()."""
        s = self.sides["L"]
        out = {name: tuple(c / self.k for c in s[name]) for name in s}
        ankle = s["ankle"]
        out["toe"] = (ankle.x / self.k, (ankle.y - 0.1 * self.height) / self.k, 0.03 * self.height / self.k)
        return out


class TripoHumanoid(rigs_human.Humanoid):
    """Cloth that hangs away from a limb (a shawl over the shoulders, a
    loincloth in front of the thighs) stays with the trunk: only what is on
    the limb's own surface follows the limb."""

    LIMBS = ("upper_arm", "lower_arm", "thigh", "shin")   # Hands and feet keep their fingers and toes.

    def surface_weights(self, p):
        best, bone = 1e9, None
        for name, part in self.spec.parts.items():
            d = self.part_distance(p, part)
            if d < best:
                best, bone = d, self.bone_of_part(name)
        loose = self.spec.height * 0.03
        if bone.startswith(self.LIMBS) and best > loose and p.z > self.spec.z["ankle"] * 2:
            z = self.spec.z
            trunk = "hips" if p.z < z["waist"] else "spine" if p.z < z["chest"] else "chest" if p.z < z["neck"] else "head"
            k = min(1.0, (best - loose) / loose)
            return [(n, w * (1 - k)) for n, w in super().surface_weights(p)] + [(trunk, k)]
        return super().surface_weights(p)


def cut_bridges(mesh, bone_of):
    """A sculpted figure is one fused surface: where a hand rests on the
    hip or a cloth tip touches a leg, faces join parts that move apart, and
    they would stretch into long strips. Those faces are removed and the
    holes they leave are closed on each side. `bone_of` gives each vertex's
    main bone. Returns how many faces were removed."""
    def group(bone):
        base, _, side = bone.partition(".")
        kind = {"lower_arm": "arm", "hand": "arm", "upper_arm": "sho", "thigh": "thi", "shin": "leg", "foot": "leg",
                "hips": "low", "spine": "low"}.get(base, "top")
        return kind, side

    APART = ({"arm", "thi"}, {"arm", "leg"}, {"arm", "low"}, {"sho", "thi"}, {"sho", "leg"}, {"sho", "low"},
             {"leg", "low"})

    def apart(a, b):
        if {a[0], b[0]} in APART:
            return True
        # A limb and the one on the other side (the thighs do meet, at the crotch).
        return a[1] != b[1] and "top" not in (a[0], b[0]) and {a[0], b[0]} != {"thi"} and a[0] != "low" != b[0]             and {a[0], b[0]} != {"sho"}

    bm = bmesh.new()
    bm.from_mesh(mesh.data)
    bm.verts.ensure_lookup_table()
    groups = [group(bone_of[v.index]) for v in bm.verts]
    bridges = [f for f in bm.faces
               if any(apart(groups[a.index], groups[b.index]) for a in f.verts for b in f.verts)]
    if bridges:
        near = {f: f.material_index for f in bridges}
        bmesh.ops.delete(bm, geom=bridges, context="FACES")
        before = set(bm.faces)
        bmesh.ops.holes_fill(bm, edges=[e for e in bm.edges if e.is_boundary], sides=0)
        for f in set(bm.faces) - before:
            # A patch takes the material of a face it touches.
            around = [g.material_index for e in f.edges for g in e.link_faces if g is not f and g in before]
            f.material_index = max(sorted(set(around)), key=around.count) if around else 0
            f.smooth = False
        bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
        bmesh.ops.recalc_face_normals(bm, faces=list(set(bm.faces) - before))
        bm.to_mesh(mesh.data)
    bm.free()
    return len(bridges)


# ----------------------------------------------------------------- colors

def reduce(mesh, triangles):
    """Collapses edges down to `triangles` and shades the faces flat."""
    current = sum(len(p.vertices) - 2 for p in mesh.data.polygons)
    if current > triangles:
        mod = mesh.modifiers.new("dec", "DECIMATE")
        mod.decimate_type = "COLLAPSE"
        mod.ratio = triangles / current
        tri = mesh.modifiers.new("tri", "TRIANGULATE")
        tri.quad_method = "BEAUTY"
        dg = bpy.context.evaluated_depsgraph_get()
        reduced = bpy.data.meshes.new_from_object(mesh.evaluated_get(dg))
        mesh.modifiers.clear()
        old = mesh.data
        mesh.data = reduced
        bpy.data.meshes.remove(old)
    for poly in mesh.data.polygons:
        poly.use_smooth = False


def load_picture(path, crop):
    """The picture's pixels as sRGB in 0..1, top row first, cropped."""
    image = bpy.data.images.load(path)
    image.colorspace_settings.name = "Non-Color"   # The file's own values, not converted.
    w, h = image.size
    pixels = np.array(image.pixels[:], dtype=np.float32).reshape(h, w, 4)[::-1, :, :3]
    bpy.data.images.remove(image)
    if crop:
        x0, y0, x1, y1 = crop
        pixels = pixels[max(0, y0):min(h, y1), max(0, x0):min(w, x1)]
    return np.ascontiguousarray(pixels)


def figure_mask(pixels):
    """Where the picture shows the figure: what differs from the background,
    whose color is taken from the picture's border."""
    border = np.concatenate([pixels[0], pixels[-1], pixels[:, 0], pixels[:, -1]])
    background = np.median(border, axis=0)
    return np.abs(pixels - background).max(axis=2) > 0.1


def bounds(mask):
    rows = np.where(mask.sum(axis=1) > max(2, mask.shape[1] * 0.01))[0]
    cols = np.where(mask.sum(axis=0) > max(2, mask.shape[0] * 0.01))[0]
    return cols[0], rows[0], cols[-1] + 1, rows[-1] + 1


def view_axes(yaw, pitch):
    """Screen right, screen up and the direction toward the camera, for a
    camera in front of the model turned by yaw and raised by pitch."""
    right = Vector((math.cos(yaw), math.sin(yaw), 0.0))
    toward = Vector((math.sin(yaw) * math.cos(pitch), -math.cos(yaw) * math.cos(pitch), math.sin(pitch)))
    up = toward.cross(right).normalized()
    return right, up, toward


def grid(mask, box):
    """A mask resampled to SILHOUETTE rows, its bounds' height filling them
    and its bounds centered across."""
    x0, y0, x1, y1 = box
    scale = (y1 - y0) / SILHOUETTE
    rows = np.clip((np.arange(SILHOUETTE) * scale + y0).astype(int), 0, mask.shape[0] - 1)
    cols = (np.arange(SILHOUETTE) - SILHOUETTE / 2) * scale + (x0 + x1) / 2
    inside = (cols >= 0) & (cols < mask.shape[1])
    out = np.zeros((SILHOUETTE, SILHOUETTE), dtype=bool)
    out[:, inside] = mask[rows][:, np.clip(cols.astype(int), 0, mask.shape[1] - 1)[inside]]
    return out


def silhouette(points, right, up):
    """The model's silhouette in the same frame as grid(): points splatted
    and grown by a pixel."""
    sx, sy = points @ np.array(right), points @ np.array(up)
    scale = SILHOUETTE / (sy.max() - sy.min())
    col = ((sx - (sx.max() + sx.min()) / 2) * scale + SILHOUETTE / 2).astype(int)
    row = ((sy.max() - sy) * scale).astype(int)
    ok = (col >= 1) & (col < SILHOUETTE - 1) & (row >= 0) & (row < SILHOUETTE)
    out = np.zeros((SILHOUETTE, SILHOUETTE), dtype=bool)
    for dc in (-1, 0, 1):
        out[np.clip(row[ok], 0, SILHOUETTE - 1), col[ok] + dc] = True
    return out


def best_view(points, mask):
    """The yaw and pitch from which the model looks most like the picture."""
    target = grid(mask, bounds(mask))
    best = (-1.0, 0.0, 0.0)
    for pitch_deg in (0, 6, 12):
        for yaw_deg in range(-80, 81, 4):
            right, up, _ = view_axes(math.radians(yaw_deg), math.radians(pitch_deg))
            shape = silhouette(points, right, up)
            score = (shape & target).sum() / max(1, (shape | target).sum())
            if score > best[0]:
                best = (score, math.radians(yaw_deg), math.radians(pitch_deg))
    return best


def paint(mesh, name, picture_path, crop, dense_points):
    """Gives each face a material with the picture's color for it."""
    pixels = load_picture(picture_path, crop)
    mask = figure_mask(pixels)
    score, yaw, pitch = best_view(dense_points, mask)
    right, up, toward = view_axes(yaw, pitch)
    x0, y0, x1, y1 = bounds(mask)
    sx, sy = dense_points @ np.array(right), dense_points @ np.array(up)
    scale = (y1 - y0) / (sy.max() - sy.min())
    cx, top = (sx.max() + sx.min()) / 2, sy.max()

    bm = bmesh.new()
    bm.from_mesh(mesh.data)
    bm.faces.ensure_lookup_table()
    bm.normal_update()
    tree = BVHTree.FromBMesh(bm)
    span = max(dense_points.max(axis=0) - dense_points.min(axis=0))
    def sample(point):
        """The picture's color where `point` is drawn, or None off the figure."""
        col = int((point.dot(right) - cx) * scale + (x0 + x1) / 2)
        row = int((top - point.dot(up)) * scale + y0)
        r0, r1, c0, c1 = max(0, row - 2), min(mask.shape[0], row + 3), max(0, col - 2), min(mask.shape[1], col + 3)
        if r0 >= r1 or c0 >= c1:
            return None
        window, inside = pixels[r0:r1, c0:c1].reshape(-1, 3), mask[r0:r1, c0:c1].reshape(-1)
        if inside.sum() * 2 < inside.size:
            return None   # At the figure's edge: the background would bleed in.
        return np.median(window[inside], axis=0)

    def shown(point, normal):
        """Whether the picture shows the surface at `point`."""
        return normal.dot(toward) > 0.12 and tree.ray_cast(point + toward * span * 0.004, toward)[0] is None

    # Each face takes, in this order: its own color in the picture if the
    # picture shows it; the color of its mirror image across the body if the
    # picture shows that; the color of what the picture has in front of it
    # (a back takes its front's color); the same for its mirror image.
    centers = [f.calc_center_median() for f in bm.faces]
    colors = [None] * len(bm.faces)
    direct = 0
    for f in bm.faces:
        c, n = centers[f.index], f.normal
        mirror, mirror_n = Vector((-c.x, c.y, c.z)), Vector((-n.x, n.y, n.z))
        color = sample(c) if shown(c, n) else None
        if color is not None:
            direct += 1
        elif shown(mirror, mirror_n):
            color = sample(mirror)
        if color is None:
            color = sample(c)
        if color is None:
            color = sample(mirror)
        colors[f.index] = color
    seen = [i for i, c in enumerate(colors) if c is not None]
    if not seen:
        bm.free()
        return score, 0.0
    kd = KDTree(len(seen))
    for i in seen:
        kd.insert(centers[i], i)
    kd.balance()
    filled = [c if c is not None else colors[kd.find(centers[i])[1]] for i, c in enumerate(colors)]
    data = np.array(filled, dtype=np.float64)

    # A few materials: k-means. It starts from the average color and then,
    # one by one, from the color farthest from those already chosen, so a
    # color on few faces (the eyes) keeps a material of its own.
    k = min(MAX_COLORS, len(data))
    means = [data.mean(axis=0)]
    while len(means) < k:
        far = ((data[:, None, :] - np.array(means)[None, :, :]) ** 2).sum(axis=2).min(axis=1)
        means.append(data[int(np.argmax(far))])
    means = np.array(means)
    for _ in range(24):
        which = np.argmin(((data[:, None, :] - means[None, :, :]) ** 2).sum(axis=2), axis=1)
        for m in range(k):
            if (which == m).any():
                means[m] = data[which == m].mean(axis=0)
    which = np.argmin(((data[:, None, :] - means[None, :, :]) ** 2).sum(axis=2), axis=1)
    # A lone face of one color among faces of another is noise from the
    # picture not matching the model exactly: it takes its neighbors' color.
    for _ in range(2):
        changed = which.copy()
        for f in bm.faces:
            around = [int(which[g.index]) for e in f.edges for g in e.link_faces if g is not f]
            if around and int(which[f.index]) not in around:
                changed[f.index] = max(sorted(set(around)), key=around.count)
        which = changed
    used = [m for m in range(k) if (which == m).any()]
    slot = {m: i for i, m in enumerate(used)}
    mesh.data.materials.clear()
    for i, m in enumerate(used):
        srgb = tuple(int(round(max(0.0, min(1.0, float(c))) * 255)) for c in means[m])
        mesh.data.materials.append(common.material(f"{name}_c{i:02d}", common.rgb((srgb[0] << 16) | (srgb[1] << 8) | srgb[2])))
    for f in bm.faces:
        f.material_index = slot[int(which[f.index])]
    bm.to_mesh(mesh.data)
    bm.free()
    print(f"TRIPO {name}: the picture is seen from {math.degrees(yaw):+.0f} degrees to the side and "
          f"{math.degrees(pitch):.0f} above")
    return score, direct / len(colors)


# ------------------------------------------------------------------- main

def build(mesh, name, path, height, triangles, picture=None, crop=None, front=None):
    """Returns a message when the mesh cannot be made a character."""
    orient(mesh, height, front)
    body = FittedBody(mesh, height)
    if body.problem:
        return f"cannot find the {body.problem} (is it a standing character with its arms apart from the body?)"
    dense = vertices(mesh)
    reduce(mesh, triangles)
    mesh.name = mesh.data.name = name
    if picture:
        score, seen = paint(mesh, name, picture, crop, dense)
        print(f"TRIPO {name}: colors from the picture, silhouette match {score:.2f}, {seen:.0%} of the faces seen in it")
    else:
        mesh.data.materials.clear()
        mesh.data.materials.append(common.material(name + "_c00", common.rgb(0x9A9AA0)))
    rig = TripoHumanoid(body, part_bones=body.part_bones)
    mesh.vertex_groups.clear()
    all_weights = [sorted(((w, n) for n, w in rig.surface_weights(v.co) if w > 0.0), reverse=True)[:4]
                   for v in mesh.data.vertices]
    cut = cut_bridges(mesh, [w[0][1] for w in all_weights])
    if cut:
        print(f"TRIPO {name}: {cut} faces that joined parts that move apart were cut")
    groups = {}
    for v in mesh.data.vertices:
        weights = all_weights[v.index]
        norm = sum(w for w, _ in weights)
        for w, bone in weights:
            if bone not in groups:
                groups[bone] = mesh.vertex_groups.new(name=bone)
            groups[bone].add([v.index], w / norm, "REPLACE")
    rigs.animate(rig, mesh, name, path)
    tris = sum(len(p.vertices) - 2 for p in mesh.data.polygons)
    print(f"TRIPO {name}: character, {tris} triangles, {len(mesh.data.materials)} materials, {len(rig.bones)} bones, "
          f"{height:.2f} m tall, walk {rig.walk['speed']:.2f} m/s, run {rig.run['speed']:.2f} m/s -> {path}")
    return None
