"""Tree species in four sizes (phase 6b, docs/ARBOLES.md).

Every tree comes from one parametric builder: a species gives its trunk,
crown shape, colors, flowers and fruit; the size gives the height and the
proportions (young trees are slimmer, with fewer and smaller clumps). The
output is tree_<species>_<size>.glb, built at the size's model height.
"""

import math
import os
import random
import zlib

import common
from common import MeshBuilder

# Model height in meters per size; matches SizeInfo::model_cm in flora.cpp.
SIZES = (("small", 4.5), ("medium", 9.5), ("large", 18.0), ("huge", 33.0))


def lumpy(verts, amount, seed):
    """Deterministic lumps on a clump: push vertices by a fixed pattern."""
    ordered = sorted(verts, key=lambda v: (round(v.co.z, 4), round(v.co.x, 4), round(v.co.y, 4)))
    cx = sum(v.co.x for v in verts) / len(verts)
    cy = sum(v.co.y for v in verts) / len(verts)
    cz = sum(v.co.z for v in verts) / len(verts)
    for i, v in enumerate(ordered):
        k = 1.0 + amount * math.sin(i * 2.3 + seed) + amount * 0.5 * math.cos(i * 5.1 + seed)
        v.co.x = cx + (v.co.x - cx) * k
        v.co.y = cy + (v.co.y - cy) * k
        v.co.z = cz + (v.co.z - cz) * (1.0 + (k - 1.0) * 0.5)


class Species:
    """How a species looks. Fractions are of the tree's height."""

    def __init__(self, sid, sizes, shape, bark, leaves, leaves_dark, *, crown_start=0.35, crown_width=0.6,
                 trunk=0.035, flowers=None, flower_share=0.0, fruit=None, bark_top=None, extra=None):
        self.id = sid
        self.sizes = sizes            # Allowed size indices.
        self.shape = shape            # round, oval, cone, umbrella, tall, vase, weeping, spire
        self.bark = bark
        self.bark_top = bark_top      # Upper trunk color (pines), or None.
        self.leaves = leaves
        self.leaves_dark = leaves_dark
        self.crown_start = crown_start
        self.crown_width = crown_width
        self.trunk = trunk            # Trunk radius at the base.
        self.flowers = flowers        # List of colors, or None.
        self.flower_share = flower_share
        self.fruit = fruit            # Fruit color, or None.
        self.extra = extra or {}


def hexrgb(h):
    return common.rgb(h)


S, M, L, H = 0, 1, 2, 3

SPECIES = [
    Species("oak", (S, M, L), "round", 0x5C3F28, 0x4E7A34, 0x3D6629, crown_start=0.3, crown_width=0.85, trunk=0.045),
    Species("pine", (S, M, L, H), "cone", 0x6B4530, 0x3F6B35, 0x2F5429, crown_start=0.3, crown_width=0.42,
            trunk=0.03, bark_top=0xA8653A, extra={"high_crown_big": True}),
    Species("toog", (M, L, H), "tall", 0xB8B0A2, 0x4F7A3A, 0x3E6630, crown_start=0.68, crown_width=0.32,
            trunk=0.03),
    Species("eucalyptus", (S, M, L, H), "tall", 0xCBC2AE, 0x7A9A7A, 0x5F8264, crown_start=0.45, crown_width=0.45,
            trunk=0.03, extra={"sparse": True}),
    Species("sequoia", (S, M, L, H), "spire", 0x8B4A2B, 0x3E6A3A, 0x2E5530, crown_start=0.25, crown_width=0.34,
            trunk=0.06, extra={"roots": True}),
    Species("mountain_ash", (L, H), "tall", 0xDDD7CA, 0x6A8C5E, 0x557A4C, crown_start=0.72, crown_width=0.28,
            trunk=0.026, extra={"sparse": True}),
    Species("cherry", (S, M), "umbrella", 0x5A2E2A, 0x5A8A3E, 0x4A7A34, crown_start=0.38, crown_width=1.0,
            trunk=0.05, flowers=[0xF2B8C8, 0xE89AB2], flower_share=0.8),
    Species("jacaranda", (S, M, L), "umbrella", 0x6B5A48, 0x6A9A4A, 0x578A3E, crown_start=0.45, crown_width=0.95,
            trunk=0.035, flowers=[0x8E6CC8, 0x7A58B8], flower_share=0.75),
    Species("tulip_tree", (S, M, L), "round", 0x7A6E60, 0x3F7A34, 0x336A2C, crown_start=0.35, crown_width=0.7,
            trunk=0.035, flowers=[0xE8552A, 0xD8401E], flower_share=0.3),
    Species("silk_floss", (S, M, L), "round", 0x6F8A4E, 0x5E8A44, 0x4C7838, crown_start=0.5, crown_width=0.75,
            trunk=0.05, flowers=[0xE67AB0, 0xD4609A], flower_share=0.55, extra={"bottle": True}),
    Species("magnolia", (S, M, L), "oval", 0x6E665C, 0x2F5A2E, 0x264C26, crown_start=0.18, crown_width=0.62,
            trunk=0.035, flowers=[0xF4EFE2], flower_share=0.0, extra={"blossoms": True}),
    Species("flamboyant", (S, M), "umbrella", 0x7A6A58, 0x5E9A3E, 0x4E8A34, crown_start=0.5, crown_width=1.45,
            trunk=0.04, flowers=[0xD9431F, 0xE86A2A], flower_share=0.65, extra={"flat": True}),
    Species("bottlebrush", (S,), "weeping", 0x5E4A3A, 0x5A7A4A, 0x4A6A3E, crown_start=0.3, crown_width=0.75,
            trunk=0.035, flowers=[0xC8202E], extra={"brushes": True}),
    Species("stone_pine", (S, M, L), "umbrella", 0x7A4E36, 0x4A7038, 0x3A5E2E, crown_start=0.62, crown_width=0.85,
            trunk=0.035, extra={"flat": True}),
    Species("elm", (S, M, L), "vase", 0x4E3B2C, 0x557F37, 0x436A2C, crown_start=0.3, crown_width=0.75,
            trunk=0.04),
    Species("lemon", (S,), "round", 0x5E4430, 0x3F7A34, 0x2F6A2E, crown_start=0.25, crown_width=0.8, trunk=0.04,
            fruit=0xF2D43A),
    Species("apple", (S, M), "round", 0x5E4430, 0x4E8A38, 0x3E7A2E, crown_start=0.35, crown_width=0.95,
            trunk=0.045, fruit=0xC8302E),
    Species("orange", (S,), "round", 0x5E4430, 0x2F6A2E, 0x285E28, crown_start=0.22, crown_width=0.85,
            trunk=0.04, fruit=0xF28A1E),
    Species("pear", (S, M), "oval", 0x5E4430, 0x5A8A3A, 0x4A7A30, crown_start=0.3, crown_width=0.6, trunk=0.04,
            fruit=0xC8C84A),
    Species("peach", (S,), "umbrella", 0x6A4636, 0x5E8A3E, 0x4E7A34, crown_start=0.35, crown_width=1.0,
            trunk=0.04, fruit=0xF2A06A, extra={"flat": True}),
    Species("avocado", (S, M), "round", 0x5A4636, 0x2E5A28, 0x264E22, crown_start=0.25, crown_width=0.9,
            trunk=0.045, fruit=0x3A4A1E),
]


def species_by_id(sid):
    for s in SPECIES:
        if s.id == sid:
            return s
    raise KeyError(sid)


class Tree:
    """Builds one tree into a MeshBuilder."""

    def __init__(self, sp, size, height, rng):
        self.sp = sp
        self.size = size
        self.h = height
        self.rng = rng
        self.mb = MeshBuilder()
        # Young trees are slimmer and narrower; old ones spread out.
        self.slim = (0.7, 0.85, 1.0, 1.15)[size]
        self.spread = (0.8, 0.92, 1.0, 1.08)[size]
        self.detail = (0.6, 0.8, 1.0, 1.25)[size]
        self.clump_index = 0

    # --- Parts ------------------------------------------------------------

    def trunk(self, top, radius, mat="bark", segments=8):
        mb = self.mb
        if self.sp.extra.get("bottle"):
            # Palo borracho: a swollen, bottle-shaped trunk with spines.
            belly = top * 0.35
            mb.cylinder((0, 0, 0), (0, 0, belly), radius * 1.3, radius * 1.9, mat, segments=segments)
            mb.cylinder((0, 0, belly), (0, 0, top), radius * 1.9, radius * 0.5, mat, segments=segments)
            for i in range(int(10 * self.detail)):
                a = i * 2.399963
                z = belly * (0.4 + 0.9 * ((i * 7) % 10) / 10.0)
                r = radius * (1.6 if z < belly else 1.2)
                base = (math.cos(a) * r, math.sin(a) * r, z)
                tip = (math.cos(a) * (r + radius * 0.35), math.sin(a) * (r + radius * 0.35), z + radius * 0.1)
                mb.cylinder(base, tip, radius * 0.08, 0.0, "spines", segments=4)
            return
        if self.sp.bark_top is not None:
            # Pines: dark and furrowed below, orange and smooth above.
            mid = top * 0.45
            mb.cylinder((0, 0, 0), (0, 0, mid), radius, radius * 0.75, mat, segments=segments)
            mb.cylinder((0, 0, mid), (0, 0, top), radius * 0.75, radius * 0.25, "bark_top", segments=segments)
        else:
            mb.cylinder((0, 0, 0), (0, 0, top), radius, radius * 0.35, mat, segments=segments)
        if self.sp.extra.get("roots") or self.size >= H:
            # Buttress roots flaring at the base.
            for i in range(5):
                a = i * 2 * math.pi / 5 + 0.3
                mb.cylinder((math.cos(a) * radius * 0.6, math.sin(a) * radius * 0.6, radius * 0.9),
                            (math.cos(a) * radius * 1.7, math.sin(a) * radius * 1.7, 0.0),
                            radius * 0.4, radius * 0.15, mat, segments=5)

    def branch(self, a, b, radius):
        self.mb.cylinder(a, b, radius, radius * 0.45, "bark", segments=5)

    def clump(self, center, radius, squash=0.85, allow_flowers=True):
        """A lumpy ball of leaves; some are flowers when the species blooms."""
        sp = self.sp
        i = self.clump_index
        self.clump_index += 1
        mat = "leaves" if i % 2 == 0 else "leaves_dark"
        if allow_flowers and sp.flowers and sp.flower_share > 0.0 and self.rng.random() < sp.flower_share:
            mat = "flowers_%d" % (i % len(sp.flowers))
        segs = 8 if radius < 2.5 else 10
        verts = self.mb.sphere(center, radius, mat, segments=segs, rings=6, scale=(1.0, 1.0, squash))
        lumpy(verts, 0.09, i * 1.7)
        return center, radius

    def decorate(self, clumps):
        """Fruit, blossoms and bottlebrush flowers on the outside of the crown."""
        sp, mb, rng = self.sp, self.mb, self.rng
        if sp.fruit is not None:
            # A little larger than life, so the fruit reads from afar.
            count = int(24 * self.detail)
            size = max(0.1, self.h * 0.03)
            for k in range(count):
                c, r = clumps[k % len(clumps)]
                a = rng.random() * 2 * math.pi
                e = (rng.random() - 0.6) * 1.2
                p = (c[0] + math.cos(a) * math.cos(e) * r * 0.92, c[1] + math.sin(a) * math.cos(e) * r * 0.92,
                     c[2] + math.sin(e) * r * 0.8)
                mb.sphere(p, size, "fruit", segments=5, rings=4)
        if sp.extra.get("blossoms"):
            count = int(22 * self.detail)
            size = max(0.1, self.h * 0.025)
            for k in range(count):
                c, r = clumps[k % len(clumps)]
                a = rng.random() * 2 * math.pi
                e = rng.random() * 1.0 - 0.2
                p = (c[0] + math.cos(a) * math.cos(e) * r * 0.95, c[1] + math.sin(a) * math.cos(e) * r * 0.95,
                     c[2] + math.sin(e) * r * 0.85)
                mb.sphere(p, size, "flowers_0", segments=6, rings=3, scale=(1.0, 1.0, 0.6))
        if sp.extra.get("brushes"):
            count = int(26 * self.detail)
            for k in range(count):
                c, r = clumps[k % len(clumps)]
                a = rng.random() * 2 * math.pi
                p = (c[0] + math.cos(a) * r * 0.85, c[1] + math.sin(a) * r * 0.85, c[2] - r * 0.3 * rng.random())
                mb.cylinder(p, (p[0], p[1], p[2] - self.h * 0.07), self.h * 0.018, self.h * 0.012, "flowers_0",
                            segments=5)

    # --- Crown shapes -----------------------------------------------------

    def build(self):
        sp, h, rng = self.sp, self.h, self.rng
        width = h * sp.crown_width * self.spread
        radius = h * sp.trunk * self.slim
        start = h * sp.crown_start
        shape = sp.shape
        if shape == "cone" and self.size >= L and sp.extra.get("high_crown_big"):
            start = h * 0.5   # Old pines lose their lower branches.
        clumps = []

        if shape in ("cone", "spire"):
            self.trunk(h * 0.97, radius)
            tiers = int(4 + 4 * self.detail) if shape == "cone" else int(6 + 5 * self.detail)
            for t in range(tiers):
                f0 = t / tiers
                z0 = start + (h - start) * f0 * 0.93
                z1 = z0 + (h - start) / tiers * (2.2 if shape == "cone" else 1.8)
                z1 = min(z1, h)
                r = width * 0.5 * (1.0 - f0 * 0.85)
                if shape == "spire":
                    # Sequoia: rounded, lumpy tiers that stay wide longer.
                    r = width * 0.5 * (1.0 - f0 ** 1.4 * 0.8)
                    verts = self.mb.sphere((0, 0, (z0 + z1) * 0.5), r, "leaves" if t % 2 == 0 else "leaves_dark",
                                           segments=9, rings=6, scale=(1.0, 1.0, (z1 - z0) / (2 * r) * 1.3))
                    lumpy(verts, 0.12, t * 1.3)
                else:
                    mat = "leaves" if t % 2 == 0 else "leaves_dark"
                    verts = self.mb.cylinder((0, 0, z0), (0, 0, z1), r, 0.0, mat, segments=9)
                    angle = t * 0.37
                    c, s = math.cos(angle), math.sin(angle)
                    for v in verts:
                        x, y = v.co.x, v.co.y
                        v.co.x, v.co.y = x * c - y * s, x * s + y * c
                clumps.append(((0, 0, (z0 + z1) * 0.5), r))

        elif shape == "tall":
            # A long straight trunk and a sparse, irregular crown on top.
            self.trunk(h * 0.9, radius)
            n = int(5 + 6 * self.detail)
            sparse = sp.extra.get("sparse", False)
            for k in range(n):
                a = k * 2.399963 + rng.random() * 0.5
                f = k / max(1, n - 1)
                z = start + (h * 0.92 - start) * f
                out = width * 0.5 * (0.55 + 0.45 * rng.random()) * (1.0 - 0.5 * f)
                p = (math.cos(a) * out, math.sin(a) * out, z)
                self.branch((0, 0, z - h * 0.05), p, radius * 0.35)
                r = width * (0.22 if sparse else 0.28) * (0.8 + 0.4 * rng.random())
                clumps.append(self.clump(p, r, squash=0.7))
            clumps.append(self.clump((0, 0, h * 0.94), width * 0.25, squash=0.8))

        elif shape == "umbrella":
            flat = sp.extra.get("flat", False)
            top = h * (0.82 if flat else 0.78)
            self.trunk(start + (top - start) * 0.25, radius)
            n = int(5 + 5 * self.detail)
            for k in range(n):
                a = k * 2 * math.pi / n + rng.random() * 0.4
                out = width * 0.5 * (0.55 + 0.35 * rng.random())
                p = (math.cos(a) * out, math.sin(a) * out, top - h * 0.06 * rng.random())
                self.branch((0, 0, start), p, radius * 0.5)
                r = width * (0.2 if flat else 0.25) * (0.85 + 0.3 * rng.random())
                clumps.append(self.clump(p, r, squash=0.45 if flat else 0.6))
            clumps.append(self.clump((0, 0, top + h * 0.03), width * 0.28, squash=0.45 if flat else 0.6))

        elif shape == "vase":
            # Elm: branches rise and fan out; the crown is widest at the top.
            self.trunk(start + h * 0.1, radius)
            n = int(4 + 4 * self.detail)
            for k in range(n):
                a = k * 2 * math.pi / n + rng.random() * 0.4
                out = width * 0.5 * (0.6 + 0.3 * rng.random())
                z = h * (0.7 + 0.12 * rng.random())
                p = (math.cos(a) * out, math.sin(a) * out, z)
                self.branch((0, 0, start + h * 0.05), p, radius * 0.45)
                clumps.append(self.clump(p, width * 0.26 * (0.85 + 0.3 * rng.random()), squash=0.75))
            clumps.append(self.clump((0, 0, h * 0.86), width * 0.3, squash=0.7))

        elif shape == "weeping":
            # Bottlebrush: a short trunk, a low crown with drooping clumps.
            self.trunk(start + h * 0.2, radius)
            n = int(6 + 4 * self.detail)
            cz = start + (h - start) * 0.55
            for k in range(n):
                a = k * 2.399963
                out = width * 0.5 * (0.5 + 0.4 * rng.random())
                z = cz + (rng.random() - 0.6) * (h - start) * 0.6
                p = (math.cos(a) * out, math.sin(a) * out, z)
                self.branch((0, 0, cz - h * 0.1), p, radius * 0.4)
                clumps.append(self.clump(p, width * 0.24, squash=1.1))
            clumps.append(self.clump((0, 0, h * 0.88), width * 0.3))

        else:
            # round and oval: overlapping clumps on an ellipsoid shell.
            oval = shape == "oval"
            crown_h = h - start
            cz = start + crown_h * 0.5
            rx = width * 0.5
            rz = crown_h * 0.5
            self.trunk(cz, radius)
            n = int(6 + 7 * self.detail)
            for k in range(n):
                a = k * 2.399963 + rng.random() * 0.3
                e = (rng.random() * 1.6 - 0.6)  # Elevation, mostly above the middle.
                sx = math.cos(e) * rx * 0.62
                p = (math.cos(a) * sx, math.sin(a) * sx, cz + math.sin(e) * rz * 0.62)
                if k < int(3 + 2 * self.detail):
                    self.branch((0, 0, start + crown_h * 0.1), p, radius * 0.45)
                r = min(rx, rz) * (0.5 if not oval else 0.45) * (0.85 + 0.3 * rng.random())
                clumps.append(self.clump(p, r, squash=1.15 if oval else 0.85))
            clumps.append(self.clump((0, 0, h - rz * 0.45), min(rx, rz) * 0.5, squash=1.1 if oval else 0.9))

        self.decorate(clumps)

    def colors(self):
        sp = self.sp
        c = {
            "bark": hexrgb(sp.bark),
            "leaves": hexrgb(sp.leaves),
            "leaves_dark": hexrgb(sp.leaves_dark),
            "spines": hexrgb(0x4E6A3A),
        }
        if sp.bark_top is not None:
            c["bark_top"] = hexrgb(sp.bark_top)
        for i, f in enumerate(sp.flowers or []):
            c["flowers_%d" % i] = hexrgb(f)
        if sp.fruit is not None:
            c["fruit"] = hexrgb(sp.fruit)
        return c


def make_tree(folder, sp, size):
    name, height = SIZES[size]
    common.reset_scene()
    # The same seed every time, so the file is the same every time.
    rng = random.Random(zlib.crc32(("%s/%s" % (sp.id, name)).encode("utf-8")))
    tree = Tree(sp, size, height, rng)
    tree.build()
    obj = tree.mb.to_object("tree_%s_%s" % (sp.id, name), tree.colors())
    common.export_glb(os.path.join(folder, "tree_%s_%s.glb" % (sp.id, name)), [obj])


def make_all(folder, only=None):
    os.makedirs(folder, exist_ok=True)
    for sp in SPECIES:
        if only and sp.id not in only:
            continue
        for size in sp.sizes:
            make_tree(folder, sp, size)
