"""Cow (Holstein): white with black patches whose borders are cut into the
surface, a black head with a white blaze, a pink muzzle and udder, small
horns, black ears, dark hooves and a thin tail with a black tuft."""

import math

from mathutils import Vector

import common
import rigs
import studies

LEG_X = 0.2
FRONT_Y, HIND_Y = -0.5, 0.68
HOOF_TOP = 0.09
# The pink muzzle: the part of the face in front of this plane.
MUZZLE_P, MUZZLE_N = Vector((0, -1.18, 1.0)), Vector((0, -1, -0.25)).normalized()
BLAZE = 0.055   # Half width of the white stripe down the face.
HEAD_Y = -0.86  # In front of this the head's own colors apply.
HEAD_BLACK_Z = 1.08  # The head is black above this, white below.
UDDER_Z = 0.7
UDDER = ((0, 0.42, UDDER_Z - 0.03), (0.14, 0.15, 0.1))

# Black patches: (side, x limit, convex polygon in (y, z)). A patch covers
# the surface on that side (side * x > x limit) whose (y, z) is inside the
# polygon; its borders are cut so they stay straight and crisp. Polygon
# edges off the body (above the back, behind the rump, in front of the
# head's border) cut nothing, so they cost no triangles.
PATCHES = [
    (-1, -0.06, [(-0.74, 1.6), (-0.36, 1.6), (-0.2, 1.08), (-0.34, 0.8), (-0.68, 0.94)]),
    (-1, 0.08, [(0.3, 1.6), (1.1, 1.6), (1.1, 0.95), (0.64, 0.84), (0.38, 1.04)]),
    (-1, 0.14, [(-0.1, 0.86), (0.1, 0.98), (0.2, 0.75), (0.1, 0.5), (-0.1, 0.5)]),
    (1, -0.04, [(-0.32, 1.6), (0.36, 1.6), (0.46, 0.9), (-0.08, 0.72), (-0.4, 1.02)]),
    (1, 0.1, [(-0.95, 1.6), (-0.66, 1.6), (-0.58, 1.02), (-0.95, 0.94)]),
    (1, 0.1, [(0.62, 1.22), (1.1, 1.22), (1.1, 0.62), (0.66, 0.62)]),
]


def edge_side(p, a, b):
    return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])


def in_polygon(p, poly):
    signs = [edge_side(p, a, b) for a, b in zip(poly, poly[1:] + poly[:1])]
    return all(s >= 0 for s in signs) or all(s <= 0 for s in signs)


def near_segment(p, a, b, margin):
    a, b, p = Vector(a), Vector(b), Vector(p)
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / ab.dot(ab)))
    return (p - (a + ab * t)).length < margin


def in_patch(c, patch):
    side, xlim, poly = patch
    return side * c.x > xlim and in_polygon((c.y, c.z), poly)


def patch_cuts():
    cuts = []
    for side, xlim, poly in PATCHES:
        for a, b in zip(poly, poly[1:] + poly[:1]):
            normal = Vector((0, b[1] - a[1], -(b[0] - a[0]))).normalized()
            cuts.append(((0, a[0], a[1]), normal,
                         lambda c, n, a=a, b=b, side=side, xlim=xlim:
                         side * c.x > xlim - 0.1 and c.y > HEAD_Y and near_segment((c.y, c.z), a, b, 0.1)))
        cuts.append(((side * xlim, 0, 0), (1, 0, 0),
                     lambda c, n, poly=poly: c.y > HEAD_Y and any(
                         in_polygon((c.y + dy, c.z + dz), poly) for dy in (-0.07, 0.07) for dz in (-0.07, 0.07))))
    return cuts


def on_surface(spec, origin, direction, sink=0.0):
    """The point where a ray from inside the spec's shape leaves it, moved
    `sink` back inside (details that must touch the skin: eyes)."""
    o, d = Vector(origin), Vector(direction).normalized()
    t = 0.0
    while studies.sdf(spec, o + d * t) < 0.0 and t < 5.0:
        t += 0.002
    return o + d * (t - sink)


def mark_surface(mb):
    """Marks the vertices of the welded surface (call when details() starts)."""
    layer = mb.bm.verts.layers.int.new("surface")
    for v in mb.bm.verts:
        v[layer] = 1
    return layer


def surface_first(mb, layer):
    """Puts the welded surface's vertices before the detail pieces again
    (call when details() ends). rigs.bind takes the first mb.detail_from
    vertices as the surface, but new vertices fill the slots of those the
    cuts removed, so pieces and surface end up mixed and the whole surface
    is bound a second time as if it were one piece. No vertex may be held
    in a variable across the sort: it moves the vertices in memory."""
    bm = mb.bm
    bm.verts.index_update()
    count = len(bm.verts)
    bm.verts.sort(key=lambda v: v.index + (0 if v[layer] else count))
    bm.verts.layers.int.remove(layer)
    bm.verts.index_update()


TAIL = [(0, 0.9, 1.3), (0, 0.97, 1.1), (0, 0.99, 0.85), (0, 0.99, 0.62)]


class CowRig(rigs.Quadruped):
    """The quadruped, with the udder kept on the body (it hangs between
    the hind legs, inside their reach) and a head that goes lower to graze."""

    def surface_weights(self, p):
        if p.z < UDDER_Z + 0.04 and studies.inside(p, UDDER[0], [r * 1.3 for r in UDDER[1]]):
            return [("body", 1.0)]
        return super().surface_weights(p)

    def piece_bone(self, center, piece):
        if center.y > 0.85:  # Tail links and the tuft.
            tail = [b for b in self.bones if b.name.startswith("tail.")]
            return min(tail, key=lambda b: rigs.segment_distance(center, b.head, b.tail)).name
        if center.y > 0.0:
            return "body"  # Teats.
        if len(piece) == 6:  # The ear flaps (the only six-vertex pieces).
            return "ear.L" if center.x > 0 else "ear.R"
        return "head"  # Eyes, nostrils and horns.

    def eat_pose(self, t):
        # As the template's, but the short neck has to go much further down.
        down = rigs.smooth(t / 0.2) * (1 - rigs.smooth((t - 0.8) / 0.2))
        root = (math.sin(2 * math.pi * 6 * t) * rigs.smooth((t - 0.2) / 0.05)
                * (1 - rigs.smooth((t - 0.75) / 0.05)))
        pitch = math.radians(4.0) * down
        dz = -0.02 * down
        rot = self.planted({}, pitch, dz)
        rot["body"] = [(rigs.X, math.degrees(pitch))]
        rot["chest"] = [(rigs.X, 6.0 * down)]
        rot["neck"] = [(rigs.X, 48.0 * down)]
        rot["head"] = [(rigs.X, 15.0 * down + 5.0 * root)]
        rot["ear.L"] = [(rigs.X, 10.0 * down)]
        rot["ear.R"] = [(rigs.X, 10.0 * down)]
        self.tail_rot(rot, 25.0 * math.sin(2 * math.pi * 4 * t) * down)
        return rot, Vector((0, 0, dz)), {}


class Cow(studies.Spec):
    name = "cow"
    budget = 800
    max_tris = 2000
    remesh_voxel = 0.016
    tone_material = "cow"
    colors = {
        "cow": common.rgb(0xF1EEE8),
        "cow_light": common.rgb(0xFBFAF6),
        "cow_shade": common.rgb(0xDEDAD2),
        "black": common.rgb(0x1F1D20),
        "pink": common.rgb(0xEE9AA6),
        "horn": common.rgb(0xE6D8B8),
    }
    ellipsoids = [
        ((0, 0.05, 1.0), (0.33, 0.66, 0.36)),     # Barrel.
        ((0, -0.48, 1.03), (0.31, 0.3, 0.36)),    # Chest.
        ((0, 0.6, 1.08), (0.31, 0.32, 0.32)),     # Rump.
        ((0, -0.97, 1.28), (0.16, 0.17, 0.17)),   # Skull.
        ((0, -1.19, 1.0), (0.135, 0.095, 0.105)),  # Muzzle.
        UDDER,
    ]
    capsules = [
        ((0, -0.6, 1.1), (0, -0.88, 1.22), 0.26, 0.17),    # Neck.
        ((0, -0.62, 0.9), (0, -0.8, 1.02), 0.18, 0.12),    # Dewlap.
        ((0, -0.99, 1.26), (0, -1.16, 1.03), 0.13, 0.11),  # Face.
    ]
    for _x in (-LEG_X, LEG_X):
        capsules += [
            ((_x, FRONT_Y, 0.88), (_x, FRONT_Y, 0.4), 0.105, 0.07),
            ((_x, FRONT_Y, 0.4), (_x, FRONT_Y - 0.01, 0.1), 0.065, 0.056),
            ((_x, FRONT_Y - 0.02, 0.02), (_x, FRONT_Y - 0.02, 0.09), 0.07, 0.064),
            ((_x * 1.05, HIND_Y - 0.1, 1.02), (_x, HIND_Y + 0.05, 0.45), 0.16, 0.07),
            ((_x, HIND_Y + 0.05, 0.45), (_x, HIND_Y, 0.1), 0.065, 0.056),
            ((_x, HIND_Y - 0.01, 0.02), (_x, HIND_Y - 0.01, 0.09), 0.07, 0.064),
        ]
    del _x
    cuts = [
        ((0, 0, HOOF_TOP), (0, 0, 1), lambda c, n: c.z < 0.2),
        (MUZZLE_P, MUZZLE_N, lambda c, n: c.y < -1.0),
        ((0, 0, UDDER_Z), (0, 0, 1), lambda c, n: 0.22 < c.y < 0.62 and abs(c.x) < 0.17),
        ((BLAZE, 0, 0), (1, 0, 0), lambda c, n: c.y < -0.95),
        ((-BLAZE, 0, 0), (1, 0, 0), lambda c, n: c.y < -0.95),
        ((0, HEAD_Y, 0), (0, 1, 0), lambda c, n: c.z > 1.0 and abs(c.y - HEAD_Y) < 0.12),
        ((0, 0, HEAD_BLACK_Z), (0, 0, 1), lambda c, n: c.y < HEAD_Y),
    ] + patch_cuts()

    rig = CowRig(
        body=((0, 0.9, 1.05), (0, 0.0, 1.03)),
        chest=((0, 0.0, 1.03), (0, -0.55, 1.05)),
        neck=((0, -0.55, 1.05), (0, -0.88, 1.22)),
        head=((0, -0.88, 1.22), (0, -1.22, 1.0)),
        ears=((0.11, -0.92, 1.3), (0.34, -0.95, 1.28)),
        tail=TAIL,
        legs={
            "F": ((LEG_X, FRONT_Y, 1.0), (LEG_X, FRONT_Y - 0.02, 0.42), (LEG_X, FRONT_Y - 0.02, HOOF_TOP),
                  (LEG_X, FRONT_Y - 0.08, 0.0)),
            "H": ((LEG_X, HIND_Y - 0.04, 1.0), (LEG_X, HIND_Y + 0.05, 0.45), (LEG_X, HIND_Y - 0.01, HOOF_TOP),
                  (LEG_X, HIND_Y - 0.07, 0.0)),
        },
        leg_exit=(0.62, 0.84),
        leg_reach=0.21,
        walk=rigs.Gait(speed=1.0, frames=26, duty=0.65, lift=0.07, crouch=0.065, bob=0.006,
                       phases=rigs.WALK_PHASES, nod=3.0, wag=12.0),
        run=rigs.Gait(speed=2.8, frames=16, duty=0.42, lift=0.13, crouch=0.08, bob=0.01,
                      phases=rigs.TROT_PHASES, nod=4.0, wag=20.0),
        lie_height=0.36,
        blend=0.08,
    )

    def paint(self, c, n):
        if c.z < HOOF_TOP:
            return "black"
        if (c - MUZZLE_P).dot(MUZZLE_N) > 0.0:
            return "pink"
        if c.z < UDDER_Z and studies.inside(c, UDDER[0], [r * 1.25 for r in UDDER[1]]):
            return "pink"
        if c.y < HEAD_Y:
            if abs(c.x) < BLAZE and n.y < -0.2:
                return "cow"  # The blaze down the face.
            return "black" if c.z > HEAD_BLACK_Z else "cow"
        if any(in_patch(c, p) for p in PATCHES):
            return "black"
        return "cow"

    def details(self, mb):
        surface = mark_surface(mb)
        for s in (-1, 1):
            eye = on_surface(self, (s * 0.05, -1.0, 1.3), (s, -0.45, 0.1), 0.01)
            mb.sphere(eye, 0.026, "black", segments=6, rings=4)
            nostril = on_surface(self, (s * 0.05, -1.19, 1.0), (s * 0.3, -1, 0.1), 0.006)
            mb.sphere(nostril, 0.02, "black", segments=5, rings=3, scale=(0.8, 0.5, 1.0))
            # Ears stick out sideways below the horns.
            studies.flap(mb, (s * 0.11, -0.94, 1.36), (s * 0.12, -0.9, 1.25), (s * 0.34, -0.95, 1.28),
                         0.03, "black")
            # Small horns curving out and up.
            mb.cylinder((s * 0.08, -0.93, 1.4), (s * 0.18, -0.95, 1.45), 0.035, 0.028, "horn", segments=5)
            mb.cylinder((s * 0.18, -0.95, 1.45), (s * 0.22, -0.98, 1.56), 0.028, 0.0, "horn", segments=5)
            # Teats.
            for y in (0.36, 0.48):
                mb.cylinder((s * 0.06, y, UDDER_Z - 0.08), (s * 0.06, y, UDDER_Z - 0.17), 0.022, 0.016,
                            "pink", segments=5)
        # A thin tail hanging from the rump, with a black tuft.
        for a, b in zip(TAIL, TAIL[1:]):
            mb.cylinder(a, b, 0.028, 0.024, "cow", segments=5)
        mb.cylinder((0, 0.99, 0.66), (0, 1.0, 0.45), 0.05, 0.015, "black", segments=5)
        surface_first(mb, surface)


SPECS = [Cow()]
