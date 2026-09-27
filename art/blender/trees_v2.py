"""Prototype of organic trees (second style, not wired into the build yet).

A tree is grown as a skeleton of branches (trunk, limbs, twigs) that the
Skin modifier turns into one continuous mesh, so the joints are smooth;
leaves are small individual cards in clusters at the twig tips, around an
irregular inner volume that keeps the crown from looking hollow. No
spheres or cylinders show.
"""

import math
import os
import random
import zlib

import bmesh
import bpy
from mathutils import Matrix, Vector

import common

SIZES = (("small", 4.5), ("medium", 9.5), ("large", 18.0), ("huge", 33.0))


class Params:
    def __init__(self, **kw):
        # Defaults: a broadleaf tree.
        self.trunk_top = 0.45        # Where the trunk ends and limbs take over (fraction of height).
        self.trunk_radius = 0.035    # Fraction of height.
        self.limbs = 6               # Level 1 branches.
        self.limb_start = 0.3        # Along the trunk (fraction of height).
        self.limb_angle = 50.0       # From vertical, degrees.
        self.limb_length = 0.42      # Fraction of height.
        self.limb_rise = 0.25        # Upward pull as they grow.
        self.branches = 4            # Level 2 per limb.
        self.branch_angle = 45.0
        self.branch_length = 0.45    # Fraction of the parent's length.
        self.twigs = 3               # Level 3 per branch.
        self.twig_length = 0.4
        self.leader = True           # The trunk keeps going to the top.
        self.whorls = False          # Conifer: limbs in rings, shorter toward the top.
        self.droop = 0.0             # Downward pull at the ends (conifers, weeping).
        self.card_size = 0.14        # Leaf card side, fraction of height.
        self.leaf_shape = (1.0, 0.45)  # Length, width of the painted leaves.
        self.needles = False
        self.flatten = 1.0           # Vertical squash of clusters (umbrella crowns).
        self.bark = 0x5C3F28
        self.leaf_colors = (0x4E7A34, 0x5E8A3C, 0x3F6B2E)
        self.inner = 0x2F5424
        self.flowers = ()
        self.flower_share = 0.0
        self.__dict__.update(kw)


SPECIES = {
    "oak": Params(),
    "pine": Params(whorls=True, trunk_top=1.0, limb_start=0.28, limbs=22, limb_angle=82.0, limb_length=0.2,
                   limb_rise=0.0, droop=0.25, branches=3, branch_angle=40.0, branch_length=0.35, twigs=0,
                   needles=True, card_size=0.17, leaf_shape=(1.0, 0.16),
                   trunk_radius=0.028, bark=0x7A4A2E,
                   leaf_colors=(0x3F6B35, 0x2F5A2C, 0x4A7A3A), inner=0x264A24),
    "jacaranda": Params(leader=False, trunk_top=0.35, limb_start=0.3, limbs=4, limb_angle=38.0, limb_length=0.55,
                        limb_rise=0.35, branches=5, branch_angle=65.0, branch_length=0.5, twigs=3,
                        flatten=0.55, card_size=0.15, leaf_shape=(1.0, 0.3), bark=0x6B5A48,
                        leaf_colors=(0x6A9A4A, 0x5E8A3E, 0x78A854), inner=0x4A6E36,
                        flowers=(0x8E6CC8, 0x7A58B8, 0x9E80D8), flower_share=0.7),
}


class Tree:
    def __init__(self, p, height, detail, rng):
        self.p = p
        self.h = height
        self.detail = detail   # 1 for the closest level of detail, less for farther ones.
        self.rng = rng
        self.verts = []        # Skeleton points.
        self.radii = []
        self.edges = []
        self.tips = []         # (position, direction) of leafy ends.

    # --- Skeleton ------------------------------------------------------------

    def add(self, co, radius, parent):
        self.verts.append(Vector(co))
        self.radii.append(radius)
        index = len(self.verts) - 1
        if parent is not None:
            self.edges.append((parent, index))
        return index

    def jitter(self, amount):
        r = self.rng
        return Vector((r.uniform(-1, 1), r.uniform(-1, 1), r.uniform(-1, 1))) * amount

    def grow(self, start, parent, direction, length, radius, level, steps):
        """Grows a branch in `steps` segments; returns the list of its nodes."""
        p = self.p
        nodes = [(parent, Vector(start), radius)]
        pos = Vector(start)
        d = direction.normalized()
        seg = length / steps
        for s in range(1, steps + 1):
            t = s / steps
            bend = Vector((0, 0, p.limb_rise if level == 1 else p.limb_rise * 0.5))
            if p.droop:
                bend.z -= p.droop * t * (1 if level >= 1 else 0)
            d = (d + bend * 0.35 + self.jitter(0.18)).normalized()
            pos = pos + d * seg
            r = radius * (1.0 - 0.75 * t)
            idx = self.add(pos, max(r, self.h * 0.002), nodes[-1][0])
            nodes.append((idx, Vector(pos), r))
        return nodes, d

    def children(self, nodes, direction, length, radius, level, count, angle, ratio, start_frac=0.35):
        """Side branches along a branch, turned around it like leaves on a stem."""
        results = []
        if count <= 0:
            return results
        axis = direction.normalized()
        # Any vector perpendicular to the axis, to turn around.
        side = axis.cross(Vector((0, 0, 1)))
        if side.length < 1e-3:
            side = Vector((1, 0, 0))
        side.normalize()
        for i in range(count):
            f = start_frac + (1.0 - start_frac) * (i + 0.5) / count
            k = min(len(nodes) - 1, max(1, int(round(f * (len(nodes) - 1)))))
            node, pos, r = nodes[k]
            turn = Matrix.Rotation(i * 2.39996 + self.rng.uniform(-0.3, 0.3), 3, axis)
            out = turn @ side
            tilt = math.radians(angle + self.rng.uniform(-8, 8))
            d = (axis * math.cos(tilt) + out * math.sin(tilt)).normalized()
            l = length * ratio * (1.15 - 0.5 * f) * self.rng.uniform(0.8, 1.15)
            results.append((node, pos, d, l, r * 0.7))
        return results

    def build_skeleton(self):
        p, h = self.p, self.h
        base_r = h * p.trunk_radius
        steps = 8
        trunk_len = h * (0.97 if p.leader else p.trunk_top)
        trunk, trunk_dir = self.grow((0, 0, 0), None, Vector((0, 0, 1)) + self.jitter(0.04), trunk_len, base_r, 0,
                                     steps)
        self.add_root_flare(base_r)
        limbs = []
        if p.whorls:
            # Conifer: rings of limbs, longest low down.
            rings = max(3, int(p.limbs / 3 * self.detail))
            for ring in range(rings):
                f = p.limb_start + (0.95 - p.limb_start) * ring / rings
                k = min(len(trunk) - 1, int(round(f * (len(trunk) - 1))))
                node, pos, r = trunk[k]
                per_ring = 4 if self.detail > 0.6 else 3
                for j in range(per_ring):
                    a = j * 2 * math.pi / per_ring + ring * 0.9
                    tilt = math.radians(p.limb_angle + self.rng.uniform(-6, 6))
                    d = Vector((math.cos(a) * math.sin(tilt), math.sin(a) * math.sin(tilt), math.cos(tilt)))
                    l = h * p.limb_length * (1.0 - (f - p.limb_start) / (1.0 - p.limb_start)) * 1.4 + h * 0.04
                    limbs.append((node, pos, d, l, r * 0.45))
        else:
            count = max(3, int(round(p.limbs * (0.7 + 0.3 * self.detail))))
            top = trunk if p.leader else trunk
            limbs = self.children(top, trunk_dir, h * p.limb_length / 0.8, base_r, 1, count, p.limb_angle, 0.8,
                                  start_frac=p.limb_start / max(0.01, (0.97 if p.leader else p.trunk_top)))
            if not p.leader:
                # The trunk splits into the limbs at its top.
                last = trunk[-1]
                limbs = [(last[0], last[1], d, l, base_r * 0.6) for (_, _, d, l, _) in limbs]
        for (node, pos, d, l, r) in limbs:
            lsteps = 5 if self.detail > 0.6 else 3
            nodes, ldir = self.grow(pos, node, d, l, r, 1, lsteps)
            branches = self.children(nodes, ldir, l, r, 2, int(round(p.branches * self.detail)), p.branch_angle,
                                     p.branch_length)
            if not branches:
                self.tips.append((nodes[-1][1], ldir))
                if p.needles:
                    for k in range(2, len(nodes), 2):
                        self.tips.append((nodes[k][1], ldir))
                continue
            self.tips.append((nodes[-1][1], ldir))
            for (bnode, bpos, bd, bl, br) in branches:
                bnodes, bdir = self.grow(bpos, bnode, bd, bl, br, 2, 3)
                twigs = self.children(bnodes, bdir, bl, br, 3, int(round(p.twigs * self.detail)), 40.0,
                                      p.twig_length)
                self.tips.append((bnodes[-1][1], bdir))
                if p.needles:
                    self.tips.append((bnodes[len(bnodes) // 2][1], bdir))
                for (tnode, tpos, td, tl, tr) in twigs:
                    tnodes, tdir = self.grow(tpos, tnode, td, tl, tr, 3, 2)
                    self.tips.append((tnodes[-1][1], tdir))

    def add_root_flare(self, base_r):
        for i in range(5):
            a = i * 2 * math.pi / 5 + 0.4
            tip = Vector((math.cos(a) * base_r * 1.5, math.sin(a) * base_r * 1.5, -base_r * 0.6))
            self.add(tip, base_r * 0.3, 0)

    def skeleton_object(self, name):
        mesh = bpy.data.meshes.new(name + "_skel")
        mesh.from_pydata([tuple(v) for v in self.verts], self.edges, [])
        obj = bpy.data.objects.new(name + "_skel", mesh)
        bpy.context.scene.collection.objects.link(obj)
        skin = obj.modifiers.new("skin", "SKIN")
        skin.branch_smoothing = 0.6
        data = mesh.skin_vertices[0].data
        for i, r in enumerate(self.radii):
            data[i].radius = (r, r)
        data[0].use_root = True
        depsgraph = bpy.context.evaluated_depsgraph_get()
        solid = bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph))
        bpy.data.objects.remove(obj)
        result = bpy.data.objects.new(name + "_wood", solid)
        bpy.context.scene.collection.objects.link(result)
        # Down to the budget of this level of detail.
        triangles = sum(len(poly.vertices) - 2 for poly in solid.polygons)
        # Small trees are seen smaller: fewer triangles for the same look.
        scale = min(1.0, 0.45 + self.h / 40.0)
        budget = int((2200 if self.detail > 0.8 else (700 if self.detail > 0.4 else 160)) * scale)
        if triangles > budget:
            dec = result.modifiers.new("budget", "DECIMATE")
            dec.ratio = budget / triangles
            depsgraph = bpy.context.evaluated_depsgraph_get()
            reduced = bpy.data.meshes.new_from_object(result.evaluated_get(depsgraph))
            result.modifiers.clear()
            result.data = reduced
        result.data.materials.append(common.material("bark", common.rgb(self.p.bark)))
        for poly in result.data.polygons:
            poly.use_smooth = False
        return result

    # --- Foliage ---------------------------------------------------------------

    def foliage(self, mb, uv):
        """Crossed leaf cards at every leafy end; each card is a picture of a
        spray of leaves, cut out by its transparency in the game."""
        p, h, rng = self.p, self.h, self.rng
        # Fewer, bigger cards for farther levels of detail keep the same crown.
        per_tip = 3 if self.detail > 0.8 else (2 if self.detail > 0.4 else 1)
        size = h * p.card_size * (1.0 if self.detail > 0.8 else (1.25 if self.detail > 0.4 else 1.7))
        for (tip, direction) in self.tips:
            bloom = bool(p.flowers) and rng.random() < p.flower_share
            for k in range(per_tip):
                mat = "card_flower" if bloom and k != 1 else "card_leaf"
                self.card(mb, uv, tip, direction, size * rng.uniform(0.8, 1.2), k, per_tip, mat)

    def card(self, mb, uv, tip, direction, size, k, count, mat):
        """A quad whose bottom edge sits at the branch end and grows outward."""
        rng = self.rng
        d = direction.normalized()
        if self.p.needles:
            # Needle sprays lie along the branch, drooping a little.
            d = (d + Vector((0, 0, -0.15))).normalized()
        else:
            d = (d + Vector((0, 0, 0.25)) + self.jitter(0.35)).normalized()
        up = Vector((0, 0, 1)) if abs(d.z) < 0.95 else Vector((1, 0, 0))
        side = d.cross(up).normalized()
        # Cards around the same end are turned apart so they cross.
        turn = Matrix.Rotation(math.pi * k / count + rng.uniform(-0.3, 0.3), 3, d)
        side = turn @ side
        half = side * size * 0.5
        base = tip - d * size * 0.25
        top = base + d * size
        corners = (base - half, base + half, top + half, top - half)
        uvs = ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))
        bm = mb.bm
        vs = [bm.verts.new(c) for c in corners]
        face = bm.faces.new(vs)
        face.material_index = mb._material_index(mat)
        face.smooth = False
        for loop, t in zip(face.loops, uvs):
            loop[uv].uv = t

    def colors(self):
        return {"card_leaf": (1.0, 1.0, 1.0), "card_flower": (1.0, 1.0, 1.0)}


# --- Leaf spray textures -----------------------------------------------------

TEX = 128


def srgb(hex_color):
    return ((hex_color >> 16) & 255) / 255.0, ((hex_color >> 8) & 255) / 255.0, (hex_color & 255) / 255.0


def spray_image(name, p, rng, flower=False):
    """Paints a spray of leaves (or needles, or blossoms) on a stem, from the
    bottom center upward, on a transparent background. Colors are sRGB."""
    w = h = TEX
    rgba = [0.0] * (w * h * 4)
    covered = [False] * (w * h)
    colors = [srgb(c) for c in (p.flowers if flower else p.leaf_colors)]

    def plot(x, y, color):
        if 0 <= x < w and 0 <= y < h:
            i = y * w + x
            rgba[i * 4:i * 4 + 4] = [color[0], color[1], color[2], 1.0]
            covered[i] = True

    def ellipse(cx, cy, length, width, angle, color, shade_rib=True):
        ca, sa = math.cos(angle), math.sin(angle)
        reach = int(length) + 2
        for y in range(int(cy) - reach, int(cy) + reach + 1):
            for x in range(int(cx) - reach, int(cx) + reach + 1):
                dx, dy = x - cx, y - cy
                u = dx * ca + dy * sa        # Along the leaf.
                v = -dx * sa + dy * ca       # Across.
                t = u / length
                if abs(t) > 1.0:
                    continue
                # A pointed leaf: narrower toward both ends.
                half = width * (1.0 - t * t) ** 0.7
                if abs(v) > half:
                    continue
                k = 0.85 + 0.25 * (v / max(half, 0.01))  # Lit on one side.
                if shade_rib and abs(v) < 0.6:
                    k *= 0.8                             # Midrib.
                plot(x, y, tuple(min(1.0, c * k) for c in color))

    stem = srgb(0x5A4A30)
    top = h * 0.95
    for y in range(int(top)):
        x = int(w / 2 + math.sin(y / h * 2.2) * w * 0.04)
        for dx in (-1, 0):
            plot(x + dx, y, stem)
    if p.needles:
        # Needle bundles: fans of thin strokes along the stem.
        rows = 60
        for i in range(rows):
            y0 = h * (0.05 + 0.9 * i / rows)
            x0 = w / 2 + math.sin(y0 / h * 2.2) * w * 0.04
            for side in (-1, 1):
                for fan in range(2):
                    color = colors[(i + fan) % len(colors)]
                    a = side * (0.7 + 0.35 * fan + rng.uniform(-0.15, 0.15))
                    length = w * (0.34 - 0.18 * i / rows) * rng.uniform(0.85, 1.1)
                    for step in range(int(length)):
                        x = int(x0 + math.sin(a) * step)
                        y = int(y0 + math.cos(a) * step * 0.55)
                        plot(x, y, color)
                        plot(x + 1, y, color)
    else:
        shape_w = p.leaf_shape[1]
        n = 9 if not flower else 14
        for i in range(n):
            f = (i + 1) / (n + 1)
            y0 = h * (0.1 + 0.8 * f)
            x0 = w / 2 + math.sin(y0 / h * 2.2) * w * 0.04
            side = -1 if i % 2 == 0 else 1
            color = colors[rng.randrange(len(colors))]
            color = tuple(c * rng.uniform(0.9, 1.1) for c in color)
            if flower:
                # A round blossom cluster: a few petal blobs.
                r = w * rng.uniform(0.07, 0.11)
                cx = x0 + side * w * rng.uniform(0.05, 0.25)
                for b in range(5):
                    a = b * 1.2566
                    ellipse(cx + math.cos(a) * r * 0.6, y0 + math.sin(a) * r * 0.6, r * 0.7, r * 0.5, a, color,
                            shade_rib=False)
            else:
                length = w * 0.2 * (1.2 - 0.5 * f) * rng.uniform(0.85, 1.15)
                angle = math.pi / 2 - side * (0.9 + rng.uniform(-0.2, 0.25))
                cx = x0 + math.cos(angle) * length * 0.9
                cy = y0 + math.sin(angle) * length * 0.9
                ellipse(cx, cy, length, length * shape_w, angle, color)
        if not flower:
            ellipse(w / 2, top - w * 0.1, w * 0.12, w * 0.12 * p.leaf_shape[1], math.pi / 2, colors[0])
    # Transparent pixels take the average leaf color, so mipmaps do not
    # darken the edges.
    total = [0.0, 0.0, 0.0]
    count = 0
    for i in range(w * h):
        if covered[i]:
            for c in range(3):
                total[c] += rgba[i * 4 + c]
            count += 1
    avg = [t / max(1, count) for t in total]
    for i in range(w * h):
        if not covered[i]:
            rgba[i * 4:i * 4 + 3] = avg
    img = bpy.data.images.new(name, w, h, alpha=True)
    img.pixels.foreach_set(rgba)
    img.file_format = "PNG"
    img.pack()
    return img


def card_material(name, img):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = img
    tex.interpolation = "Linear"
    mat.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    mat.node_tree.links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
    bsdf.inputs["Roughness"].default_value = 0.9
    return mat


def make(folder, sid, size_index, detail=1.0, suffix=""):
    name, height = SIZES[size_index]
    common.reset_scene()
    rng = random.Random(zlib.crc32(("%s/%s" % (sid, name)).encode("utf-8")))
    p = SPECIES[sid]
    tree = Tree(p, height, detail, rng)
    tree.build_skeleton()
    wood = tree.skeleton_object("tree")
    mb = common.MeshBuilder()
    uv = mb.bm.loops.layers.uv.verify()
    tree.foliage(mb, uv)
    names = list(mb.materials)
    leaves = mb.to_object("leaves", tree.colors())
    # The textures have their own random stream, so every size and level of
    # detail of a species shares the same pictures.
    trng = random.Random(zlib.crc32(("%s/texture" % sid).encode("utf-8")))
    for i, mat_name in enumerate(names):
        img = spray_image("%s_%s" % (sid, mat_name), p, trng, flower=(mat_name == "card_flower"))
        placeholder = leaves.data.materials[i]
        leaves.data.materials[i] = None
        bpy.data.materials.remove(placeholder)
        leaves.data.materials[i] = card_material(mat_name, img)
    common.select_only([wood, leaves])
    bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    obj.name = "tree_%s_%s" % (sid, name)
    path = os.path.join(folder, "tree_%s_%s%s.glb" % (sid, name, suffix))
    common.export_glb(path, [obj], images=True)
    return path
