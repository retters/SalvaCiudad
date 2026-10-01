"""Horse: chestnut brown with lighter and darker facets, a dark mane and tail
made of flat shards, dark hooves. Equine is also the base of the unicorn
(unicorn.py), which reshapes it with a few proportion factors."""

import math

from mathutils import Vector

import common
import rigs
import studies

# Design coordinates: a horse 1.6 m at the withers. Equine.P() maps them to
# the real model (scale, leg length, body length, head size).
BELLY_Z = 0.92      # Below this height only the legs are, which leg scales.
POLL = Vector((0.0, -0.86, 1.95))  # Top of the head, the head scales about it.
FACE = Vector((0.0, -0.38, -0.36)).normalized()  # From the poll down the face.
LEG_X = 0.15
FRONT_Y, HIND_Y = -0.52, 0.62
HOOF_TOP = 0.1
# Crest of the neck, from the poll to the withers, where the mane grows.
CREST = [(0, -0.84, 2.0), (0, -0.76, 1.9), (0, -0.68, 1.8), (0, -0.6, 1.71), (0, -0.52, 1.64),
         (0, -0.43, 1.59)]
TAIL_ROOT = (0, 0.84, 1.44)
HIP_Z = 1.2  # Where the legs swing from, inside the body.
MANE_BONES = ("chest", "neck", "head")
TAIL_BONES = ("tail.1", "tail.2", "tail.3")


def on_surface(spec, origin, direction, sink=0.0):
    """The point where a ray from inside the spec's shape leaves it, moved
    `sink` back inside (details that must touch the skin: eyes)."""
    o, d = Vector(origin), Vector(direction).normalized()
    t = 0.0
    while studies.sdf(spec, o + d * t) < 0.0 and t < 5.0:
        t += 0.002
    return o + d * (t - sink)


def twisted_cone(mb, base, tip, radius, sides, rings, twist, mat):
    """A cone whose rings turn a little each step: a faceted spiral horn."""
    base, tip = Vector(base), Vector(tip)
    axis = (tip - base).normalized()
    u = axis.orthogonal().normalized()
    v = axis.cross(u)
    layers = []
    for i in range(rings):
        t = i / rings
        c = base.lerp(tip, t)
        r = radius * (1.0 - t)
        layers.append([mb.bm.verts.new(c + (u * math.cos(a) + v * math.sin(a)) * r)
                       for a in [twist * i + k * math.tau / sides for k in range(sides)]])
    apex = mb.bm.verts.new(tip)
    mb.bm.faces.new(list(reversed(layers[0])))
    for l0, l1 in zip(layers, layers[1:]):
        for k in range(sides):
            j = (k + 1) % sides
            mb.bm.faces.new((l0[k], l0[j], l1[k]))
            mb.bm.faces.new((l0[j], l1[j], l1[k]))
    for k in range(sides):
        mb.bm.faces.new((layers[-1][k], layers[-1][(k + 1) % sides], apex))
    return mb._finish([v for layer in layers for v in layer] + [apex], mat, None)


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


class EquineRig(rigs.Quadruped):
    """The quadruped for a horse: the spec tags its detail pieces with the
    bone they follow (the mane and tail plates bend along several bones),
    and the long neck goes all the way down to graze."""

    # Grazing: turns of (body, chest, neck, head) per degree of the neck's
    # own turn. The forehand comes down too (neck and head together are
    # shorter than the legs), and the head turns back up so the face stays
    # toward the grass, ahead of the hooves.
    GRAZE = (0.05, 0.16, 1.0, -0.45)

    def __init__(self, soft_blend, graze, **kw):
        super().__init__(**kw)
        self.soft_blend = soft_blend  # Width of the weight transition in the mane and tail (m).
        self.graze = graze            # Height the tip of the head bone goes down to in eat (m).
        self.tags = []                # (center of a detail piece, bone name or tuple of bone names).
        self.neck_down = self.solve_graze()

    def tag(self, verts, bones):
        """Says which bone a detail piece follows: one name, or several
        for a piece that bends between them."""
        self.tags.append((sum((v.co for v in verts), Vector()) / len(verts), bones))

    def tagged(self, center):
        near = min(self.tags, key=lambda t: (t[0] - center).length, default=None)
        return near[1] if near is not None and (near[0] - center).length < 1e-3 else None

    def piece_bone(self, center, piece):
        bones = self.tagged(center)
        return bones if isinstance(bones, str) else super().piece_bone(center, piece)

    def piece_weights(self, center, piece):
        bones = self.tagged(center)
        if bones is None or isinstance(bones, str):
            return None

        def weights(p):
            cands = [(rigs.segment_distance(p, self.by_name[n].head, self.by_name[n].tail), n) for n in bones]
            d0 = min(d for d, _ in cands)
            return [(n, max(0.0, 1.0 - (d - d0) / self.soft_blend) ** 2) for d, n in cands]
        return weights

    def graze_tip(self, neck):
        pose = rigs.Pose(self)
        for bone, share in zip(("body", "chest", "neck", "head"), self.GRAZE):
            pose.turn(bone, rigs.X, neck * share)
        return pose.tail("head").z

    def solve_graze(self):
        """The neck turn that brings the tip of the head to the graze height."""
        lo, hi = 0.0, 130.0
        for _ in range(30):
            mid = (lo + hi) * 0.5
            lo, hi = (mid, hi) if self.graze_tip(mid) > self.graze else (lo, mid)
        return lo

    def eat_pose(self, t):
        down = rigs.smooth(t / 0.25) * (1 - rigs.smooth((t - 0.75) / 0.25))
        root = (math.sin(2 * math.pi * 6 * t) * rigs.smooth((t - 0.25) / 0.05)
                * (1 - rigs.smooth((t - 0.7) / 0.05)))
        a = self.neck_down * down
        rot = self.planted({}, math.radians(a * self.GRAZE[0]), 0.0)
        rot["body"] = [(rigs.X, a * self.GRAZE[0])]
        rot["chest"] = [(rigs.X, a * self.GRAZE[1])]
        rot["neck"] = [(rigs.X, a * self.GRAZE[2])]
        rot["head"] = [(rigs.X, a * self.GRAZE[3] + 4.0 * root)]
        rot["ear.L"] = [(rigs.X, 10.0 * down)]
        rot["ear.R"] = [(rigs.X, 10.0 * down)]
        self.tail_rot(rot, 25.0 * math.sin(2 * math.pi * 4 * t) * down)
        return rot, Vector((0, 0, 0)), {}


def crouch_for(legs, speed, frames, duty):
    """How much the body must come down for every foot to reach both ends
    of its stride (a planted foot that cannot reach would slide)."""
    half = speed * duty * frames / rigs.FPS / 2
    need = 0.0
    for hip, knee, ankle, toe in legs.values():
        reach = (knee - hip).length + (ankle - knee).length - 0.003
        need = max(need, (hip.z - ankle.z) - math.sqrt(reach * reach - (abs(ankle.y - hip.y) + half) ** 2))
    return need


class Equine(studies.Spec):
    name = "horse"
    budget = 800
    max_tris = 2000
    remesh_voxel = 0.016
    tone_material = "horse"
    colors = {
        "horse": common.rgb(0x98482A),
        "horse_light": common.rgb(0xAC5634),
        "horse_shade": common.rgb(0x803C22),
        "mane": common.rgb(0x3A2018),
        "hoof": common.rgb(0x2E2622),
        "eye": common.rgb(0x151012),
    }
    body = "horse"         # Main material.
    manes = ("mane",)      # Mane and tail shard materials, used in turn.
    hoof = "hoof"
    k = 1.0                # Overall scale.
    leg = 1.0              # Leg length factor.
    length = 1.0           # Body length factor.
    head = 1.0             # Head size factor.
    eye = 1.0              # Eye size factor.
    ridge = 0.045          # Height of the mane's ridge spikes (design meters).
    snout = 1.0            # Length factor of the face in front of the eyes.
    girth = 1.0            # Width factor of the body.
    mane_hang = 0.0        # How far the mane hangs below its skin line.
    tail_size = 1.0        # Tail size factor.
    leg_r = 1.0            # Leg thickness factor.
    # Gaits: (speed m/s, frames per cycle, share of the cycle a foot is planted).
    walk = (1.6, 22, 0.62)
    trot = (4.2, 16, 0.36)

    # ----------------------------------------------------------- mapping
    def P(self, p, head=False):
        p = Vector(p)
        if head:
            q = (p - POLL) * self.head
            along = q.dot(FACE)
            if along > 0.2 * self.head:
                q -= FACE * (along - 0.2 * self.head) * (1.0 - self.snout)
            p = POLL + q
        z = p.z * self.leg if p.z < BELLY_Z else BELLY_Z * self.leg + (p.z - BELLY_Z)
        return Vector((p.x, p.y * self.length, z)) * self.k

    def R(self, r, head=False):
        return r * self.k * (self.head if head else 1.0)

    def ell(self, c, r, head=False):
        s = self.k * (self.head if head else 1.0)
        return (tuple(self.P(c, head)), (r[0] * s * (1.0 if head else self.girth),
                                         r[1] * s * (1.0 if head else self.length), r[2] * s))

    def cap(self, a, b, ra, rb, head=False):
        return (tuple(self.P(a, head)), tuple(self.P(b, head)), self.R(ra, head), self.R(rb, head))

    # ------------------------------------------------------------ shape
    def __init__(self):
        e, h = self.ell, True
        neck = (1.0 + self.girth) * 0.5
        self.ellipsoids = [
            e((0, 0.02, 1.22), (0.3, 0.55, 0.3)),        # Barrel.
            e((0, -0.5, 1.26), (0.28, 0.27, 0.31)),      # Chest.
            e((0, 0.52, 1.27), (0.26, 0.3, 0.29)),       # Hindquarters.
            e((0, -0.42, 1.45), (0.13, 0.2, 0.15)),      # Withers.
            e((0, -0.97, 1.77), (0.1, 0.13, 0.13), h),   # Cheek.
            e((0, -1.27, 1.52), (0.085, 0.1, 0.085), h),  # Muzzle.
        ]
        c = self.cap
        self.capsules = [
            c((0, -0.58, 1.38), (0, -0.82, 1.8), 0.2 * neck, 0.13 * neck),     # Neck.
            c((0, -0.66, 1.22), (0, -0.88, 1.66), 0.16 * neck, 0.11 * neck),   # Throat.
            c((0, -0.88, 1.9), (0, -1.26, 1.54), 0.115, 0.085, h),  # Skull to nose.
            c(TAIL_ROOT, (0, 0.9, 1.36), 0.075, 0.06),             # Dock of the tail.
        ]

        def lc(a, b, ra, rb):
            return c(a, b, ra * self.leg_r, rb * self.leg_r)

        for s in (-1, 1):
            x = s * LEG_X
            self.capsules += [
                lc((x, FRONT_Y, 1.08), (x, FRONT_Y - 0.01, 0.56), 0.105, 0.058),   # Forearm.
                lc((x, FRONT_Y - 0.01, 0.56), (x, FRONT_Y - 0.02, 0.16), 0.05, 0.043),  # Cannon.
                lc((x, FRONT_Y - 0.02, 0.16), (x, FRONT_Y - 0.05, 0.08), 0.045, 0.05),  # Pastern.
                lc((x, FRONT_Y - 0.05, 0.02), (x, FRONT_Y - 0.05, 0.09), 0.062, 0.055),  # Hoof.
                lc((x * 1.05, HIND_Y - 0.1, 1.18), (x, HIND_Y + 0.1, 0.6), 0.155, 0.062),  # Gaskin.
                lc((x, HIND_Y + 0.1, 0.6), (x, HIND_Y, 0.16), 0.05, 0.043),           # Cannon.
                lc((x, HIND_Y, 0.16), (x, HIND_Y - 0.03, 0.08), 0.045, 0.05),           # Pastern.
                lc((x, HIND_Y - 0.03, 0.02), (x, HIND_Y - 0.03, 0.09), 0.062, 0.055),   # Hoof.
            ]
        hoof_top = self.P((0, 0, HOOF_TOP)).z
        self.hoof_top = hoof_top
        self.cuts = [((0, 0, hoof_top), (0, 0, 1), lambda c, n: c.z < hoof_top + 0.1)]
        self.rig = self.make_rig()

    def make_rig(self):
        P, k = self.P, self.k
        # Knees a little off the straight line from hip to hoof, so each
        # bends its own way (the knee forward, the hock back).
        legs = {
            "F": (P((LEG_X, FRONT_Y, HIP_Z)), P((LEG_X, FRONT_Y - 0.04, 0.56)),
                  P((LEG_X, FRONT_Y - 0.04, HOOF_TOP)), P((LEG_X, FRONT_Y - 0.11, 0.0))),
            "H": (P((LEG_X, HIND_Y + 0.02, HIP_Z)), P((LEG_X, HIND_Y + 0.1, 0.6)),
                  P((LEG_X, HIND_Y - 0.02, HOOF_TOP)), P((LEG_X, HIND_Y - 0.09, 0.0))),
        }

        def gait(speed, frames, duty, lift, bob, phases, **kw):
            return rigs.Gait(speed=speed, frames=frames, duty=duty, lift=lift * k,
                             crouch=crouch_for(legs, speed, frames, duty) + bob * k + 0.004, bob=bob * k,
                             phases=phases, **kw)

        root = Vector(TAIL_ROOT)
        z = self.tail_size
        neck_end = P((0, -0.84, 1.84), True)
        return EquineRig(
            soft_blend=0.12 * k,
            graze=self.R(0.2, True),
            body=(P((0, 0.8, 1.3)), P((0, -0.05, 1.28))),
            chest=(P((0, -0.05, 1.28)), P((0, -0.52, 1.36))),
            neck=(P((0, -0.52, 1.36)), neck_end),
            head=(neck_end, P((0, -1.3, 1.5), True)),
            ears=(P((0.07, -0.86, 1.95), True), P((0.085, -0.86, 2.13), True)),
            tail=[P(root), P(root + Vector((0, 0.1, -0.1))), P(root + Vector((0, 0.22, -0.4)) * z),
                  P(root + Vector((0, 0.2, -0.76)) * z)],
            legs=legs,
            leg_exit=(P((0, 0, 0.9)).z, P((0, 0, 1.1)).z),
            leg_reach=0.22 * k * (1.0 + self.leg_r) * 0.5,
            walk=gait(*self.walk, lift=0.1, bob=0.008, phases=rigs.WALK_PHASES, nod=4.0, wag=10.0),
            run=gait(*self.trot, lift=0.22, bob=0.02, phases=rigs.TROT_PHASES, nod=3.0, wag=14.0),
            lie_height=0.31 * k * self.girth,
            blend=0.08 * k,
        )

    def paint(self, c, n):
        return self.hoof if c.z < self.hoof_top else self.body

    # ---------------------------------------------------------- details
    def shard(self, mb, points, i, head=False, thickness=0.03):
        return studies.plate(mb, [self.P(p, head) for p in points], self.R(thickness),
                             self.manes[i % len(self.manes)])

    def mane(self, mb):
        crest = [Vector(p) for p in CREST]
        up = Vector((0, 0.85, 0.53))  # Out of the crest, up and back.
        thick = self.R(0.03)
        tag = self.rig.tag
        for i, (a, b) in enumerate(zip(crest, crest[1:])):
            head = i == 0
            a2, b2 = a + up * 0.03, b + up * 0.03
            mid = (a + b) * 0.5
            # A low jagged ridge along the top...
            tag(self.shard(mb, [a2 - (a2 - b2) * 0.1, b2 + (a2 - b2) * 0.05,
                                mid + up * self.ridge + Vector((0, 0.06, 0))], i, head), MANE_BONES)
            # ...and a curtain hanging down both sides of the neck, just
            # off the skin, ending in a jagged lower edge.
            for s in (-1, 1):
                # Rings of skin points around the neck, from the crest
                # down the side, each a bit off the skin.
                rows = []
                for angle in (0.0, 0.8, 1.45):
                    row = []
                    for p in (a, b):
                        inner = self.P(p - up * 0.1, head)
                        ray = Vector((s * math.sin(angle), up.y * math.cos(angle) * self.length,
                                      up.z * math.cos(angle)))
                        row.append(on_surface(self, inner, ray) + ray.normalized() * self.R(0.02))
                    rows.append(row)
                hang = Vector((s * 0.02, 0.0, -1.0)) * self.R(self.mane_hang + 0.02 * (i % 2))
                rows[-1] = [p + hang for p in rows[-1]]
                mat = self.manes[(i + (1 if s > 0 else 0)) % len(self.manes)]
                tag(studies.plate(mb, [rows[0][0], rows[0][1], rows[1][1], rows[1][0]], thick, mat), MANE_BONES)
                tip = (rows[2][0] + rows[2][1]) * 0.5 + Vector((0, 0.02, -1)) * self.R(0.05)
                tag(studies.plate(mb, [rows[1][0], rows[1][1], rows[2][1], tip, rows[2][0]], thick, mat),
                    MANE_BONES)
        # Forelock over the forehead.
        tag(self.shard(mb, [(0, -0.87, 2.0), (0.03, -0.93, 1.99), (0.0, -1.0, 1.87), (-0.03, -0.93, 1.99)],
                       1, True), "head")

    def tail(self, mb):
        root = Vector(TAIL_ROOT)
        z = self.tail_size
        for i, (dx, back, low, spread) in enumerate(((0.0, 0.2, 0.62, 0.05), (-0.06, 0.14, 0.74, 0.06),
                                                     (0.06, 0.15, 0.72, 0.06), (0.0, 0.1, 0.82, 0.04),
                                                     (-0.03, 0.24, 0.5, 0.05))):
            pts = [root + Vector((dx * 0.3, -0.02, 0.04)), root + Vector((dx * 0.5, 0.1, -0.02)),
                   root + Vector((dx + spread * (1 if dx >= 0 else -1), back + 0.1, -low * 0.55)) * z,
                   root + Vector((dx * 1.4, back, -low)) * z,
                   root + Vector((dx - spread * 0.4, back - 0.08, -low * 0.6)) * z]
            self.rig.tag(self.shard(mb, pts, i, thickness=0.035), TAIL_BONES)

    def details(self, mb):
        surface = mark_surface(mb)
        self.pieces(mb)
        surface_first(mb, surface)

    def pieces(self, mb):
        self.rig.tags = []  # A rebuild with a lower budget makes the pieces again.
        tag = self.rig.tag
        for s in (-1, 1):
            eye = on_surface(self, self.P((0, -1.0, 1.8), True), (s, -0.35, 0.15), self.R(0.012 * self.eye, True))
            tag(mb.sphere(eye, self.R(0.026 * self.eye, True), "eye", segments=6, rings=4), "head")
            nostril = on_surface(self, self.P((0, -1.25, 1.52), True), (s * 0.45, -1, 0.15), self.R(0.008, True))
            tag(mb.sphere(nostril, self.R(0.018, True), "eye", segments=5, rings=3, scale=(0.7, 0.5, 1.0)), "head")
            tag(studies.flap(mb, self.P((s * 0.035, -0.88, 1.97), True), self.P((s * 0.1, -0.83, 1.94), True),
                             self.P((s * 0.085, -0.86, 2.13), True), self.R(0.03, True), self.body),
                "ear.L" if s > 0 else "ear.R")
        self.mane(mb)
        self.tail(mb)


SPECS = [Equine()]
