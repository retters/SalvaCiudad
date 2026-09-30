"""Horse: chestnut brown with lighter and darker facets, a dark mane and tail
made of flat shards, dark hooves. Equine is also the base of the unicorn
(unicorn.py), which reshapes it with a few proportion factors."""

import math

from mathutils import Vector

import common
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

    def paint(self, c, n):
        return self.hoof if c.z < self.hoof_top else self.body

    # ---------------------------------------------------------- details
    def shard(self, mb, points, i, head=False, thickness=0.03):
        studies.plate(mb, [self.P(p, head) for p in points], self.R(thickness),
                      self.manes[i % len(self.manes)])

    def mane(self, mb):
        crest = [Vector(p) for p in CREST]
        up = Vector((0, 0.85, 0.53))  # Out of the crest, up and back.
        thick = self.R(0.03)
        for i, (a, b) in enumerate(zip(crest, crest[1:])):
            head = i == 0
            a2, b2 = a + up * 0.03, b + up * 0.03
            mid = (a + b) * 0.5
            # A low jagged ridge along the top...
            self.shard(mb, [a2 - (a2 - b2) * 0.1, b2 + (a2 - b2) * 0.05,
                            mid + up * self.ridge + Vector((0, 0.06, 0))], i, head)
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
                studies.plate(mb, [rows[0][0], rows[0][1], rows[1][1], rows[1][0]], thick, mat)
                tip = (rows[2][0] + rows[2][1]) * 0.5 + Vector((0, 0.02, -1)) * self.R(0.05)
                studies.plate(mb, [rows[1][0], rows[1][1], rows[2][1], tip, rows[2][0]], thick, mat)
        # Forelock over the forehead.
        self.shard(mb, [(0, -0.87, 2.0), (0.03, -0.93, 1.99), (0.0, -1.0, 1.87), (-0.03, -0.93, 1.99)], 1, True)

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
            self.shard(mb, pts, i, thickness=0.035)

    def details(self, mb):
        for s in (-1, 1):
            eye = on_surface(self, self.P((0, -1.0, 1.8), True), (s, -0.35, 0.15), self.R(0.012 * self.eye, True))
            mb.sphere(eye, self.R(0.026 * self.eye, True), "eye", segments=6, rings=4)
            nostril = on_surface(self, self.P((0, -1.25, 1.52), True), (s * 0.45, -1, 0.15), self.R(0.008, True))
            mb.sphere(nostril, self.R(0.018, True), "eye", segments=5, rings=3, scale=(0.7, 0.5, 1.0))
            studies.flap(mb, self.P((s * 0.035, -0.88, 1.97), True), self.P((s * 0.1, -0.83, 1.94), True),
                         self.P((s * 0.085, -0.86, 2.13), True), self.R(0.03, True), self.body)
        self.mane(mb)
        self.tail(mb)


SPECS = [Equine()]
