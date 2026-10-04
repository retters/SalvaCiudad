"""Shared pieces of the `beasts` proposal family: great beasts and bosses,
sea creatures and more pets and working animals.

Everything here is made of rigid faceted pieces, each bound whole to one
bone of a kit.Mech (the technique of creatures/wyvern.py): the pieces and
pose converters come from the `creatures` family (_parts.py), imported
read-only; this module adds

- Beast: a four-legged body of any size (legs posed by inverse kinematics,
  one or several necks and heads, a tail, optional wings and a jet of fire)
  with the clips idle, walk, run, eat, attack, breath, fly and die; several
  of them can share one skeleton (a pack of hounds): pack();
- a small library of heads, wings, manes, horns and antlers.

Front is -Y, the ground is Z = 0, meters.
"""

import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CREATURES = os.path.join(os.path.dirname(HERE), "creatures")
if CREATURES not in sys.path:
    sys.path.append(CREATURES)

import _parts as P  # noqa: E402  (creatures/_parts.py)
from mathutils import Quaternion, Vector  # noqa: E402
from _parts import X, Y, Z, Pose, hull, rock, seg, spike, ball, plate, bar, box, pulse, smooth  # noqa: E402,F401

FAMILY = "beasts"
P.FAMILY = FAMILY          # Whatever the borrowed builders save goes to this family's folder.
FPS = P.FPS
SIDES = P.SIDES
LEGS = (("FL", 1.0, "F"), ("FR", -1.0, "F"), ("HL", 1.0, "H"), ("HR", -1.0, "H"))
WALK = {"HL": 0.0, "FL": 0.25, "HR": 0.5, "FR": 0.75}
TROT = {"FL": 0.0, "HR": 0.0, "FR": 0.5, "HL": 0.5}
FWD = Vector((0, -1, 0))

shades, palette, mix = P.shades, P.palette, P._mix


def lump(mb, center, radii, mat, bone, seed=1, count=16, jitter=0.07, tones=True):
    """A faceted lump with some facets a tone lighter or darker (the
    material needs its "_light" and "_shade" tones: shades())."""
    verts = rock(mb, center, radii, mat, bone, count=count, seed=seed, jitter=jitter)
    if tones:
        rnd = random.Random(seed)
        faces = sorted({f for v in verts for f in v.link_faces}, key=lambda f: tuple(f.calc_center_median()))
        for f in faces:
            r = rnd.random()
            if r < 0.22:
                f.material_index = mb._material_index(mat + "_light")
            elif r < 0.44:
                f.material_index = mb._material_index(mat + "_shade")
    return verts


def chain(mb, name, pts, radii, mats, sides=7, over=0.25, joints=True, tag=""):
    """Overlapping tapered segments along the points, one bone each."""
    for i, (a, b) in enumerate(zip(pts, pts[1:])):
        d = (b - a).normalized()
        bone = f"{name}.{i + 1}{tag}"
        seg(mb, a - d * radii[i] * over, b, radii[i], radii[i + 1], mats[i % len(mats)], bone, sides=sides)
        if joints:
            ball(mb, a, radii[i] * 0.97, mats[i % len(mats)], bone, segments=sides, rings=4)


def chain_bones(name, pts, parent, tag=""):
    out = []
    for i, (a, b) in enumerate(zip(pts, pts[1:])):
        out.append((f"{name}.{i + 1}{tag}", tuple(a), tuple(b), parent))
        parent = f"{name}.{i + 1}{tag}"
    return out, parent


def up_of(a, b):
    """A unit vector across the segment a-b, as near straight up as it can."""
    d = (b - a).normalized()
    up = Vector((0, 0, 1)) - d * d.z
    return up.normalized() if up.length > 0.15 else Vector((0, 1, 0))


def crest(mb, name, pts, radii, mat, height, first=0, last=None, per=1, width=0.5, lean=0.4, tag=""):
    """Spines along the top of a chain."""
    last = len(pts) - 1 if last is None else last
    for i in range(first, last):
        a, b = pts[i], pts[i + 1]
        up, d = up_of(a, b), (b - a).normalized()
        for j in range(per):
            u = (j + 0.5) / per
            c = a.lerp(b, u)
            r = radii[i] + (radii[i + 1] - radii[i]) * u
            h = height * (r / radii[first]) ** 0.5
            spike(mb, c + up * r * 0.8, c + up * (r + h) + d * h * -lean, h * width * 0.5, mat, f"{name}.{i + 1}{tag}")


def mane(mb, name, pts, radii, mat, height, thick=0.04, first=0, last=None, back=0.3, tag=""):
    """A mane of upright plates along the top of a chain."""
    last = len(pts) - 1 if last is None else last
    for i in range(first, last):
        a, b = pts[i], pts[i + 1]
        up, d = up_of(a, b), (b - a).normalized()
        base_a, base_b = a + up * radii[i] * 0.8, b + up * radii[i + 1] * 0.8
        plate(mb, [base_a, base_b, base_b + up * height - d * height * back,
                   base_a + up * height * 0.85 - d * height * back], thick, mat, f"{name}.{i + 1}{tag}")


def horn(mb, base, pts, r, mat, bone, sides=5):
    """A curved horn through the points, tapering to a tip."""
    all_pts = [Vector(base)] + [Vector(p) for p in pts]
    n = len(all_pts) - 1
    for i, (a, b) in enumerate(zip(all_pts, all_pts[1:])):
        seg(mb, a, b, r * (1 - i / n), r * (1 - (i + 1) / n), mat, bone, sides=sides)


def antler(mb, base, s, sx, mat, bone, points=4, spread=1.0):
    """A stag's antler: a main beam curving up and back with tines."""
    beam = [Vector(base)]
    for i in range(1, points + 2):
        u = i / (points + 1)
        beam.append(Vector(base) + Vector((sx * (0.18 * u + 0.22 * u * u) * spread, 0.3 * u - 0.25 * u * u, 0.75 * u)) * s)
    for i, (a, b) in enumerate(zip(beam, beam[1:])):
        seg(mb, a, b, 0.035 * s * (1 - 0.14 * i), 0.035 * s * (1 - 0.14 * (i + 1)), mat, bone, sides=5)
        if 0 < i <= points:
            tine = a + Vector((sx * 0.06 * spread, -0.3 + 0.03 * i, 0.2 + 0.03 * i)) * s * (1.0 - 0.1 * i)
            seg(mb, a, tine, 0.026 * s, 0.006 * s, mat, bone, sides=4)
    spike(mb, beam[-2], beam[-1] + Vector((0, 0.04, 0.1)) * s, 0.02 * s, mat, bone)


# --------------------------------------------------------------------- heads

def head_muzzle(mb, at, s, bone, jaw=None, skull=(0.13, 0.16, 0.13), mz=(0.34, 0.07, 0.11, 0.05), ears="up",
                ear=1.0, mat="fur", mat2="fur_shade", nose="nose", eye="eye", ear_mat=None, teeth=None,
                eye_r=0.022, tones=True):
    """A head with a muzzle (horse, wolf, lion, goat, camel, pig...) at the
    head joint `at`, looking toward -Y. `skull` are the radii of the brain
    case and `mz` the muzzle's (length, half width at the tip, height at the
    tip, drop of the tip). With `jaw`, the lower third of the muzzle is a
    separate piece on that bone. Returns hp(x, y, z): a point from the
    skull's center in head units."""
    rx, ry, rz = skull
    c = at + Vector((0, -ry * 0.75, rz * 0.15)) * s

    def hp(x, y, z):
        return c + Vector((x, y, z)) * s
    if tones:
        lump(mb, c, (rx * s, ry * s, rz * s), mat, bone, seed=5, count=16, jitter=0.04)
    else:
        rock(mb, c, (rx * s, ry * s, rz * s), mat, bone, count=16, seed=5, jitter=0.04)
    ln, mw, mh, drop = mz
    y0, y1 = -ry * 0.45, -ry * 0.45 - ln
    top0, bot0 = rz * 0.62, -rz * 0.85
    top1, bot1 = -drop + mh * 0.5, -drop - mh * 0.5
    split = 0.38 if jaw else 0.0
    m0, m1 = bot0 + (top0 - bot0) * split, bot1 + (top1 - bot1) * split
    hull(mb, [hp(sx * rx * 0.8, y0, z) for sx in (-1, 1) for z in (top0, m0)]
         + [hp(sx * mw, y1, z) for sx in (-1, 1) for z in (top1, m1)]
         + [hp(sx * mw * 0.7, y1 - mh * 0.25, (top1 + m1) * 0.5) for sx in (-1, 1)], mat, bone)
    if jaw:
        hull(mb, [hp(sx * rx * 0.72, y0 + ry * 0.2, z) for sx in (-1, 1) for z in (m0 - 0.004, bot0)]
             + [hp(sx * mw * 0.85, y1 + ln * 0.06, z) for sx in (-1, 1) for z in (m1 - 0.004, bot1)], mat2, jaw)
    ball(mb, hp(0, y1 - mh * 0.18, top1 - mh * 0.12), mw * 0.6 * s, nose, bone, segments=6, rings=4, scale=(1, 0.7, 0.7))
    for sx in (-1, 1):
        ball(mb, hp(sx * rx * 0.86, -ry * 0.5, rz * 0.3), eye_r * s, eye, bone, segments=6, rings=4)
        em = ear_mat or mat2
        if ears == "up":         # Pointed, upright.
            plate(mb, [hp(sx * rx * 0.25, ry * 0.15, rz * 0.8), hp(sx * rx * 0.95, ry * 0.25, rz * 0.5),
                       hp(sx * rx * 0.8, ry * 0.1, rz * 0.8 + 0.17 * ear)], 0.02 * s, em, bone)
        elif ears == "long":     # A hare's, a donkey's.
            plate(mb, [hp(sx * rx * 0.2, ry * 0.3, rz * 0.8), hp(sx * rx * 0.75, ry * 0.4, rz * 0.6),
                       hp(sx * rx * 0.9, ry * 0.7, rz * 0.8 + 0.3 * ear), hp(sx * rx * 0.4, ry * 0.75, rz * 0.8 + 0.34 * ear)],
                  0.02 * s, em, bone)
        elif ears == "round":
            ball(mb, hp(sx * rx * 0.75, ry * 0.2, rz * 0.85), 0.05 * ear * s, em, bone, segments=6, rings=4,
                 scale=(1, 0.45, 1))
        elif ears == "side":     # Cattle, goats, pigs: out and a little down.
            plate(mb, [hp(sx * rx * 0.8, ry * 0.2, rz * 0.55), hp(sx * rx * 0.8, ry * 0.5, rz * 0.3),
                       hp(sx * (rx + 0.16 * ear), ry * 0.5, rz * 0.2)], 0.02 * s, em, bone)
        elif ears == "flop":
            plate(mb, [hp(sx * rx * 0.75, ry * 0.0, rz * 0.6), hp(sx * rx * 0.85, ry * 0.5, rz * 0.5),
                       hp(sx * (rx + 0.05), ry * 0.3, rz * 0.5 - 0.2 * ear)], 0.025 * s, em, bone)
        if teeth:
            for i in range(2):
                y = y1 + ln * (0.1 + 0.25 * i)
                spike(mb, hp(sx * mw * 0.85, y, m1 + 0.01), hp(sx * mw * 0.85, y, m1 - 0.05 * (1.3 - 0.5 * i)), 0.012 * s,
                      teeth, bone)
    return hp


def head_dragon(mb, at, s, bone, jaw, horns=2, mat="scale", belly="belly", frill=False):
    """A dragon's head about 0.6 * s long: a wedge skull, a hinged jaw with
    teeth, eyes under brows and horns swept back."""
    def hp(x, y, z):
        return at + Vector((x, y, z)) * s
    hull(mb, [hp(-0.17, 0.1, -0.08), hp(0.17, 0.1, -0.08), hp(-0.16, 0.1, 0.15), hp(0.16, 0.1, 0.15),
              hp(-0.15, -0.2, 0.13), hp(0.15, -0.2, 0.13), hp(-0.085, -0.6, 0.02), hp(0.085, -0.6, 0.02),
              hp(-0.1, -0.58, -0.09), hp(0.1, -0.58, -0.09), hp(-0.16, -0.15, -0.08), hp(0.16, -0.15, -0.08),
              hp(0, -0.34, 0.12)], mat, bone)
    hull(mb, [hp(-0.15, 0.06, -0.1), hp(0.15, 0.06, -0.1), hp(-0.15, 0.06, -0.2), hp(0.15, 0.06, -0.2),
              hp(-0.085, -0.55, -0.105), hp(0.085, -0.55, -0.105), hp(-0.07, -0.52, -0.17), hp(0.07, -0.52, -0.17)],
         belly, jaw)
    hull(mb, [hp(-0.11, 0.0, -0.098), hp(0.11, 0.0, -0.098), hp(-0.06, -0.5, -0.098), hp(0.06, -0.5, -0.098),
              hp(0, -0.25, -0.092)], "mouth", jaw)
    for sx in (-1, 1):
        ball(mb, hp(sx * 0.14, -0.14, 0.085), 0.04 * s, "eye", bone, segments=6, rings=4)
        hull(mb, [hp(sx * 0.1, -0.24, 0.12), hp(sx * 0.17, -0.2, 0.1), hp(sx * 0.17, -0.02, 0.15), hp(sx * 0.1, -0.04, 0.19),
                  hp(sx * 0.15, -0.12, 0.17)], mat + "_dark", bone)                       # Brow ridge.
        spike(mb, hp(sx * 0.1, 0.06, 0.12), hp(sx * 0.24, 0.52, 0.36), 0.06 * s, "horn", bone, sides=5)
        if horns > 1:
            spike(mb, hp(sx * 0.15, 0.06, 0.0), hp(sx * 0.32, 0.34, 0.0), 0.045 * s, "horn", bone, sides=4)
        if horns > 2:
            spike(mb, hp(sx * 0.13, 0.04, -0.14), hp(sx * 0.24, 0.24, -0.2), 0.035 * s, "horn", jaw, sides=4)
        spike(mb, hp(sx * 0.05, -0.52, 0.03), hp(sx * 0.055, -0.5, 0.1), 0.022 * s, "horn", bone, sides=4)   # Nostril horn.
        for i in range(6):
            y = -0.14 - i * 0.08
            x = sx * (0.14 - 0.011 * i)
            spike(mb, hp(x, y, -0.08), hp(x, y - 0.01, -0.16 - 0.02 * (i % 2)), 0.02 * s, "tooth", bone, sides=4)
        for i in range(4):
            y = -0.18 - i * 0.09
            x = sx * (0.12 - 0.012 * i)
            spike(mb, hp(x, y, -0.105), hp(x, y - 0.01, -0.04), 0.016 * s, "tooth", jaw, sides=4)
        if frill:
            plate(mb, [hp(sx * 0.16, 0.05, 0.1), hp(sx * 0.16, 0.08, -0.12), hp(sx * 0.36, 0.3, -0.1),
                       hp(sx * 0.4, 0.34, 0.14)], 0.02 * s, "membrane", bone)
    return hp


def head_beak(mb, at, s, bone, jaw, mat="feather", beak="beak", hook=1.0, brow=True):
    """A raptor's head: a round skull, a hooked beak and stern brows."""
    c = at + Vector((0, -0.12, 0.02)) * s

    def hp(x, y, z):
        return c + Vector((x, y, z)) * s
    lump(mb, c, (0.13 * s, 0.16 * s, 0.13 * s), mat, bone, seed=4, count=16, jitter=0.04)
    hull(mb, [hp(-0.065, -0.12, 0.05), hp(0.065, -0.12, 0.05), hp(-0.06, -0.12, -0.03), hp(0.06, -0.12, -0.03),
              hp(-0.03, -0.3, 0.02), hp(0.03, -0.3, 0.02), hp(0, -0.36, -0.03 - 0.07 * hook), hp(0, -0.27, -0.035),
              hp(0, -0.2, 0.065)], beak, bone)
    hull(mb, [hp(-0.05, -0.1, -0.035), hp(0.05, -0.1, -0.035), hp(-0.045, -0.1, -0.075), hp(0.045, -0.1, -0.075),
              hp(0, -0.27, -0.05), hp(0, -0.25, -0.07)], beak, jaw)
    for sx in (-1, 1):
        ball(mb, hp(sx * 0.105, -0.07, 0.035), 0.026 * s, "eye", bone, segments=6, rings=4)
        if brow:
            hull(mb, [hp(sx * 0.07, -0.14, 0.07), hp(sx * 0.135, -0.1, 0.06), hp(sx * 0.14, 0.02, 0.075),
                      hp(sx * 0.08, 0.0, 0.11)], mat + "_shade", bone)
    return hp


# --------------------------------------------------------------------- wings

def wing_membrane(mb, sx, sh, el, tip, root, mat="membrane", arm="scale", dark="scale_dark", claw="horn", r=0.1,
                  chord=1.0, thick=0.03, tag=""):
    """A bat wing: an arm from the shoulder to the elbow, three fingers and
    the skin between them. Bones wing.1 and wing.2 of that side."""
    side = "L" if sx > 0 else "R"
    b1, b2 = f"wing.1.{side}{tag}", f"wing.2.{side}{tag}"
    span = tip - el
    back = Vector((0, chord, -0.12 * chord))
    f_mid = el + span * 0.72 + back * 0.75
    f_back = el + span * 0.28 + back * 1.0
    inner = sh.lerp(el, 0.55) + back * 0.95
    plate(mb, [sh, el, f_back, inner, root], thick, mat, b1)
    plate(mb, [el, tip, f_mid], thick, mat, b2)
    plate(mb, [el, f_mid, f_back], thick, mat, b2)
    seg(mb, sh, el, r, r * 0.7, arm, b1)
    rock(mb, sh, (r * 1.7, r * 1.7, r * 1.5), arm, b1, seed=7, count=10)
    for end in (tip, f_mid, f_back):
        seg(mb, el, end, r * 0.5, r * 0.16, dark, b2, sides=4)
    spike(mb, el, el + Vector((sx * 0.05, -0.3, 0.1)) * (r / 0.1), r * 0.4, claw, b2, sides=4)


def wing_feather(mb, sx, sh, el, tip, chord=1.0, mat="feather", tip_mat="feather_dark", arm="feather_shade", thick=0.03,
                 inner_n=5, outer_n=7, tag=""):
    """A bird's wing: coverts along the arm and long flight feathers, the
    outer ones fanned. Bones wing.1 and wing.2 of that side."""
    side = "L" if sx > 0 else "R"
    b1, b2 = f"wing.1.{side}{tag}", f"wing.2.{side}{tag}"
    back = Vector((0, 1, -0.08))
    seg(mb, sh, el, 0.09 * chord, 0.07 * chord, arm, b1, sides=5)
    seg(mb, el, el.lerp(tip, 0.6), 0.07 * chord, 0.03 * chord, arm, b2, sides=5)
    for i in range(inner_n):
        a, b = sh.lerp(el, i / inner_n), sh.lerp(el, (i + 1) / inner_n)
        ln = chord * (0.75 + 0.25 * i / inner_n)
        plate(mb, [a, b, b + back * ln, a + back * ln * 0.96], thick, mat if i % 2 else arm, b1)
        plate(mb, [a + back * ln * 0.9, b + back * ln * 0.9, b.lerp(a, 0.5) + back * ln * 1.25], thick, tip_mat, b1)
    out = (tip - el).normalized()
    for i in range(outer_n):
        u0, u1 = i / outer_n, (i + 1) / outer_n
        a, b = el.lerp(tip, u0 * 0.8), el.lerp(tip, u1 * 0.8)
        d = (back * (1 - u1 * 0.75) + out * (u1 * 1.1)).normalized()
        ln = chord * (1.05 + 0.25 * math.sin(math.pi * u1))
        plate(mb, [a, b, b + d * ln, a + d * ln * 0.92], thick, mat if i % 2 else arm, b2)
        plate(mb, [a + d * ln * 0.85, b + d * ln * 0.9, b + d * ln * 1.28], thick, tip_mat, b2)


# --------------------------------------------------------------------- beast

class Beast:
    """A four-legged body of rigid pieces. `L` is the distance from the
    shoulders to the hips, `zs` the height of the spine, `w` half the
    distance between left and right feet, `hl` the height of the shoulder
    and hip joints. `fb` and `hb` say how far the front and hind middle
    joints sit behind (+) or ahead (-) of the leg, as a fraction of the
    leg's height. `origin` (x, y) places it away from the model's center
    and `tag` is added to its bones' names (several beasts in one model)."""

    def __init__(self, L, zs, w, hl, fb=0.2, hb=-0.2, ankle=None, hw=None, hind_hl=None, toe=None, origin=(0, 0),
                 tag="", two_legs=None):
        self.L, self.zs, self.w, self.hl = L, zs, w, hl
        self.o = Vector((origin[0], origin[1], origin[2] if len(origin) > 2 else 0.0))
        self.tag = tag
        self.ankle_z = ankle if ankle is not None else 0.1 * hl
        self.toe = toe if toe is not None else 0.16 * hl
        self.hw = hw if hw is not None else w
        self.points = {}
        # A bird: two legs under the body at y = `two_legs`.
        self.LEGS = LEGS if two_legs is None else (("L", 1.0, "F"), ("R", -1.0, "F"))
        self.walk_ph = WALK if two_legs is None else {"L": 0.0, "R": 0.5}
        self.trot_ph = TROT if two_legs is None else {"L": 0.0, "R": 0.5}
        for leg, sx, end in self.LEGS:
            y = two_legs if two_legs is not None else (-L / 2 if end == "F" else L / 2)
            x = (w if end == "F" else self.hw) * sx
            top = hl if end == "F" else (hind_hl or hl)
            bend = (fb if end == "F" else hb) * (top - self.ankle_z)
            self.points[leg] = tuple(self.o + Vector(p) for p in (
                (x, y, top), (x, y + bend, (top + self.ankle_z) * 0.5), (x, y, self.ankle_z), (x, y - self.toe, 0.0)))
        self.necks = []        # (prefix, points)
        self.tail_pts = None
        self.wing = None
        self.bones = []        # Extra bones (name, head, tail, parent).
        self.fire_chunks = []
        self.out = []          # The clips: (name, seconds, function, loops, speed).
        self.m = None

    def n(self, bone):
        return bone + self.tag

    def at(self, *p):
        """A point of this beast (local coordinates) in the model."""
        return self.o + (Vector(p[0]) if len(p) == 1 else Vector(p))

    # ------------------------------------------------------------ geometry

    def trunk(self, mb, mat, chest, belly, hips, belly_mat=None, drop=0.0, seed=1):
        """Three lumps (chest, belly, hips), each given by its radii; the
        optional `belly_mat` paints a plate under the body."""
        L, z, body = self.L, self.zs - drop, self.n("body")
        lump(mb, self.at(0, -L * 0.36, z - chest[2] * 0.25), chest, mat, body, seed=seed, count=22)
        lump(mb, self.at(0, 0.0, z - belly[2] * 0.3), belly, mat, body, seed=seed + 1, count=18)
        lump(mb, self.at(0, L * 0.38, z - hips[2] * 0.2), hips, mat, body, seed=seed + 2, count=20)
        if belly_mat:
            zb = z - chest[2] * 1.2
            hull(mb, [self.at(p) for p in
                      [(sx * chest[0] * 0.55, -L * 0.36 - chest[1] * 0.75, zb + chest[2] * 0.55) for sx in (-1, 1)]
                      + [(sx * chest[0] * 0.6, -L * 0.3, zb) for sx in (-1, 1)]
                      + [(sx * hips[0] * 0.55, L * 0.45, z - hips[2] * 1.12) for sx in (-1, 1)]
                      + [(0, 0, z - belly[2] * 1.3), (0, -L * 0.3, zb - chest[2] * 0.06)]], belly_mat, body)

    def legs(self, mb, r_up, r_low, mat, mat_low=None, foot="paw", foot_mat=None, claw="horn", foot_r=None, hind=1.0,
             shoulder=1.5, front_claw=None):
        mat_low = mat_low or mat
        foot_mat = foot_mat or mat_low
        for leg, sx, end in self.LEGS:
            j, k, a, toe = self.points[leg]
            f = 1.0 if end == "F" else hind
            ru, rl = r_up * f, r_low * f
            up, low, bone = self.n(f"leg_up.{leg}"), self.n(f"leg_low.{leg}"), self.n(f"foot.{leg}")
            rock(mb, j + Vector((-sx * ru * 0.2, 0, -ru * 0.3)), (ru * shoulder, ru * shoulder * 1.2, ru * shoulder * 1.3),
                 mat, up, seed=11 + len(leg) + int(sx), count=10)
            seg(mb, j, k, ru, rl * 1.1, mat, up)
            ball(mb, k, rl * 1.15, mat_low, low)
            seg(mb, k, a, rl * 1.05, rl * 0.8, mat_low, low)
            fr = foot_r or rl * 1.25
            g = self.o.z                                         # The ground this beast stands on (a perch).
            x, y, az = a.x, a.y, a.z - g
            fl = self.toe
            kind = front_claw if (front_claw and end == "F") else foot
            if kind == "hoof":
                seg(mb, (x, y, g + az + rl * 0.3), (x, y - fl * 0.25, g + az * 0.45), rl * 0.8, fr * 0.85, mat_low, bone)
                mb.cylinder((x, y - fl * 0.25, g + az * 0.5), (x, y - fl * 0.25, g), fr * 0.85, fr, foot_mat,
                            weights={bone: 1.0}, segments=7)
            elif kind == "pad":      # An elephant's: a round column with toenails.
                mb.cylinder((x, y, g + az + rl * 0.3), (x, y, g), rl * 0.95, fr, foot_mat, weights={bone: 1.0}, segments=8)
                for i in (-1, 0, 1):
                    ang = math.radians(90 + 32 * i)
                    ball(mb, (x + math.cos(ang) * fr * 0.9, y - math.sin(ang) * fr * 0.9, g + fr * 0.24), fr * 0.24, claw,
                         bone, segments=5, rings=3)
            else:
                hull(mb, [(x - fr, y + fr * 0.9, g), (x + fr, y + fr * 0.9, g), (x - fr * 1.25, y - fl * 0.75, g),
                          (x + fr * 1.25, y - fl * 0.75, g), (x - fr * 0.75, y + fr * 0.8, g + az * 1.5),
                          (x + fr * 0.75, y + fr * 0.8, g + az * 1.5), (x - fr * 0.9, y - fl * 0.55, g + az * 0.7),
                          (x + fr * 0.9, y - fl * 0.55, g + az * 0.7)], foot_mat if kind != "talon" else claw, bone)
                if kind in ("claw", "talon"):
                    for dx in (-1, 0, 1):
                        spike(mb, (x + dx * fr * 0.8, y - fl * 0.6, g + az * 0.45), (x + dx * fr * 1.2, y - fl * 1.25, g),
                              fr * 0.34, claw if kind == "claw" else "claw", bone, sides=4)
                    spike(mb, (x, y + fr * 0.8, g + az * 0.5), (x, y + fr * 1.7, g), fr * 0.3,
                          claw if kind == "claw" else "claw", bone, sides=4)
                else:
                    for dx in (-1, 0, 1):
                        ball(mb, (x + dx * fr * 0.75, y - fl * 0.75, g + az * 0.5), fr * 0.42, foot_mat, bone, segments=5,
                             rings=3, scale=(1, 1.2, 1.0))

    def neck(self, mb, pts, radii, mats, prefix="", sides=7):
        """A neck along the points; the head joint is its last point.
        Bones <prefix>neck.N, <prefix>head and <prefix>jaw."""
        pts = [self.at(p) for p in pts]
        chain(mb, prefix + "neck", pts, radii, mats, sides=sides, tag=self.tag)
        self.necks.append((prefix, pts))
        return pts[-1]

    def tail(self, mb, pts, radii, mats, sides=6):
        pts = [self.at(p) for p in pts]
        chain(mb, "tail", pts, radii, mats, sides=sides, tag=self.tag)
        self.tail_pts = pts
        return pts

    def wings(self, sh, el, tip, fold=(40.0, 60.0, 0.0), flap=(28.0, 20.0, -10.0)):
        """Declares the wings' bones (the left side's shoulder, elbow and
        tip); the geometry is wing_membrane() or wing_feather(). `fold` is
        the folded pose on the ground: (inner panel raised, outer panel
        folded down, both swept back) in degrees; `flap` the beat in the
        air: (inner swing, outer swing, inner mean)."""
        self.wing = (Vector(sh), Vector(el), Vector(tip), fold, flap)

    def fire(self, mb, hide, n=6, r0=0.2, r1=0.6, mats=("fire_c", "fire_b", "fire_a")):
        """A jet of fire: lumps hidden inside the chest at `hide`, thrown out
        of the mouth by fire_pose()."""
        d = 0.0
        for i in range(n):
            r = r0 + (r1 - r0) * i / max(1, n - 1)
            c = self.at(hide)
            bone = self.n(f"fire.{i + 1}")
            rock(mb, c, (r * 0.5, r * 0.9, r * 0.5), mats[min(len(mats) - 1, i * len(mats) // n)], bone, count=9, seed=40 + i,
                 jitter=0.3)
            self.bones.append((bone, tuple(c), tuple(c + FWD * 0.3), self.n("body")))
            d += r * 1.3
            self.fire_chunks.append((c, r, d))

    # ---------------------------------------------------------------- bones

    def bone_list(self):
        L, zs, n = self.L, self.zs, self.n
        bones = [(n("body"), tuple(self.at(0, L / 2, zs)), tuple(self.at(0, -L / 2, zs)), None)]
        for prefix, pts in self.necks:
            made, last = chain_bones(prefix + "neck", pts, n("body"), tag=self.tag)
            bones += made
            h = pts[-1]
            d = (pts[-1] - pts[-2]).length
            bones += [(n(prefix + "head"), tuple(h), tuple(h + FWD * max(d, 0.1)), last),
                      (n(prefix + "jaw"), tuple(h + Vector((0, 0.02, -0.1)) * d), tuple(h + Vector((0, -1.0, -0.2)) * d),
                       n(prefix + "head"))]
        if self.tail_pts:
            bones += chain_bones("tail", self.tail_pts, n("body"), tag=self.tag)[0]
        for leg, sx, end in self.LEGS:
            j, k, a, toe = self.points[leg]
            bones += [(n(f"leg_up.{leg}"), tuple(j), tuple(k), n("body")),
                      (n(f"leg_low.{leg}"), tuple(k), tuple(a), n(f"leg_up.{leg}")),
                      (n(f"foot.{leg}"), tuple(a), tuple(toe), n(f"leg_low.{leg}"))]
        if self.wing:
            sh, el, tip = self.wing[:3]
            for side, sx in SIDES:
                def m(p, sx=sx):
                    return tuple(self.at(p.x * sx, p.y, p.z))
                bones += [(n(f"wing.1.{side}"), m(sh), m(el), n("body")),
                          (n(f"wing.2.{side}"), m(el), m(tip), n(f"wing.1.{side}"))]
        return bones + self.bones

    def mech(self):
        self.m = P.kit.Mech(self.bone_list())
        return self.m

    # ---------------------------------------------------------------- poses

    def stand(self, pose, targets=None, toes=None):
        for leg, sx, end in self.LEGS:
            j, k, a, toe = self.points[leg]
            bend = (k - (j + a) * 0.5).y
            pole = Vector((sx * 0.05, bend, 0.0)) if abs(bend) > 1e-4 else Vector((0, -1, 0))
            pose.limb(self.n(f"leg_up.{leg}"), self.n(f"leg_low.{leg}"), (targets or {}).get(leg, a), pole)
            pose.set_world(self.n(f"foot.{leg}"), Quaternion(X, math.radians((toes or {}).get(leg, 0.0))))

    def tuck(self, pose, amount=1.0):
        """Legs trailing and folded under the body (flying)."""
        for leg, sx, end in self.LEGS:
            f = 1.0 if end == "F" else -1.0
            j, k, a, toe = self.points[leg]
            back = 1.0 if (k.y - j.y) >= 0 else -1.0     # Which way the middle joint bends.
            pose.turn(self.n(f"leg_up.{leg}"), X, (35.0 + f * 5.0) * amount)
            pose.turn(self.n(f"leg_low.{leg}"), X, -back * 55.0 * amount)
            pose.turn(self.n(f"foot.{leg}"), X, 25.0 * amount)

    def neck_pose(self, pose, bend=0.0, side=0.0, head=0.0, jaw=0.0, only=None, twist=0.0):
        for prefix, pts in self.necks:
            if only is not None and prefix != only:
                continue
            for i in range(len(pts) - 1):
                pose.turn(self.n(f"{prefix}neck.{i + 1}"), X, bend)
                pose.turn(self.n(f"{prefix}neck.{i + 1}"), Z, side)
            pose.turn(self.n(prefix + "head"), X, head)
            if twist:
                pose.turn(self.n(prefix + "head"), Z, twist)
            pose.turn(self.n(prefix + "jaw"), X, jaw)

    def tail_pose(self, pose, fn, up=0.0):
        if self.tail_pts:
            for i in range(len(self.tail_pts) - 1):
                pose.turn(self.n(f"tail.{i + 1}"), Z, fn(i))
                if up:
                    pose.turn(self.n(f"tail.{i + 1}"), X, up)

    def wing_pose(self, pose, raise_, fold, sweep=0.0):
        if self.wing:
            for side, sx in SIDES:
                pose.turn(self.n(f"wing.1.{side}"), Y, -sx * raise_)
                pose.turn(self.n(f"wing.1.{side}"), Z, sx * sweep)
                pose.turn(self.n(f"wing.2.{side}"), Y, sx * fold)
                pose.turn(self.n(f"wing.2.{side}"), Z, sx * sweep * 0.6)

    def folded(self, pose, more=0.0, open_=0.0):
        """The wings folded on the ground. A fold ("flank", roll, sweep,
        droop) lays a feathered wing against the flank: rolled so the
        feathers hang down, swept back along the body, the outer panel
        drooping toward the tail."""
        if not self.wing:
            return
        fold = self.wing[3]
        if fold[0] == "flank":
            c = 1 - open_
            for side, sx in SIDES:
                pose.turn(self.n(f"wing.1.{side}"), X, -fold[1] * c)
                pose.turn(self.n(f"wing.1.{side}"), Z, sx * fold[2] * c)
                pose.turn(self.n(f"wing.2.{side}"), Z, sx * fold[3] * c)
            return
        r, f, s = fold
        self.wing_pose(pose, r + more, f * (1 - open_), s * (1 - open_))

    def fire_pose(self, pose, moves, amount, t, head="head", spread=0.1):
        """Throws the fire lumps out of the mouth of `head`: `amount` from
        0 (hidden in the chest) to 1 (the whole jet)."""
        if amount <= 0.0 or not self.fire_chunks:
            return
        m = self.m
        hb, body = m.by_name[self.n(head)], m.by_name[self.n("body")]
        hq, bq = pose.world(self.n(head)), pose.world(self.n("body"))
        tip, bh = pose.tail(self.n(head)), pose.head(self.n("body"))
        fwd = (hq @ (hb.tail - hb.head)).normalized()
        aim = FWD.rotation_difference(fwd)
        count = len(self.fire_chunks)
        for i, (rest, r, d) in enumerate(self.fire_chunks):
            if amount * count <= i:
                continue
            wob = Vector((math.sin(t * 40 + i * 2.1), 0.0, math.cos(t * 34 + i * 1.3))) * r * spread
            target = tip + fwd * (d - r * 0.6) + aim @ wob
            natural = bh + bq @ (rest - body.head)
            moves[self.n(f"fire.{i + 1}")] = tuple(bq.inverted() @ (target - natural))
            pose.q[self.n(f"fire.{i + 1}")] = bq.inverted() @ aim @ Quaternion(FWD, t * 12.0 + i)

    # --------------------------------------------------------------- strides

    def max_stride(self, crouch, bob=0.0, side=0.0):
        best = None
        for leg, sx, end in self.LEGS:
            j, k, a, toe = self.points[leg]
            reach = ((k - j).length + (a - k).length) * 0.975
            height = j.z - a.z - crouch + abs(bob)
            room = reach * reach - height * height - side * side
            half = math.sqrt(max(0.0, room)) - abs(a.y - j.y)
            best = half if best is None else min(best, half)
        return max(0.0, 2 * best * 0.94)

    def gait(self, frames, duty, lift, crouch, phases=None, stride=None, bob=None, yaw=1.5, nod=2.0, wag=6.0, lean=0.0,
             sway=0.0, toe=18.0):
        """A walk or run clip; returns (pose function, speed)."""
        phases = phases or self.walk_ph
        bob = self.hl * 0.012 if bob is None else bob
        side = self.L * math.sin(math.radians(yaw)) + sway
        limit = self.max_stride(crouch, bob, side)
        stride = limit if stride is None else min(stride, limit)
        speed = stride * FPS / (duty * frames)
        body = self.n("body")

        def fn(t):
            p = 2 * math.pi * t
            pose = Pose(self.m, (sway * math.sin(p), 0, -crouch + bob * math.cos(2 * p)))
            pose.turn(body, Z, yaw * math.sin(p))
            if lean:
                pose.turn(body, X, lean)
            targets, toes = {}, {}
            for leg, sx, end in self.LEGS:
                dy, dz, u = P.step(t, phases[leg], duty, stride, lift)
                a = self.points[leg][2]
                targets[leg] = Vector((a.x, a.y + dy, a.z + dz))
                toes[leg] = min(toe, 40.0 * lift / max(self.toe, 1e-6)) * math.sin(math.pi * u) ** 2 if u else 0.0
            self.stand(pose, targets, toes)
            self.neck_pose(pose, nod * math.cos(2 * p) - lean * 0.5, -yaw * 0.6 * math.sin(p), head=-nod * math.cos(2 * p))
            self.tail_pose(pose, lambda i: -wag * math.sin(p - (i + 1) * 0.6))
            if self.wing:
                self.folded(pose, 3.0 * math.cos(2 * p))
            return pose
        return fn, speed

    # ------------------------------------------------------------- the clips

    def add(self, name, seconds, fn, loops=True, speed=None):
        if name in self.skip:
            return
        self.out.append((name, seconds, fn, loops, speed))
        if self.register:
            self.m.clip(name, seconds, fn, loops=loops, speed=speed)

    def clips(self, walk=None, run=None, attack="bite", idle_s=4.0, attack_s=1.4, die_s=2.0, fly=None, lunge=None,
              extra_idle=None, extra_walk=None, breath=None, die_side=1.0, wide=None, eat=None, jaw=32.0,
              register=True, idle_look=4.0, skip=()):
        """Adds the usual clips to the skeleton. `walk` and `run` are the
        arguments of gait(); `attack` is "bite", "gore" (head down, horns
        first) or None; `fly` a dict(height, seconds, speed, pitch);
        `breath` a dict(seconds) for a fire-breathing attack named "breath";
        `eat` a dict(bend, head) to graze; `extra_idle(pose, t)` and
        `extra_walk(pose, t)` add to those poses."""
        self.register, self.skip = register, tuple(skip)
        if self.m is None:
            self.mech()
        m, hl, body = self.m, self.hl, self.n("body")
        wide = self.w * 1.6 if wide is None else wide
        walk = dict(dict(frames=30, duty=0.66, lift=hl * 0.1, crouch=hl * 0.05), **(walk or {}))
        lunge = self.max_stride(hl * 0.07) * 0.22 if lunge is None else lunge

        def idle(t):
            p = 2 * math.pi * t
            b = math.sin(2 * p)
            pose = Pose(m, (0, 0, -hl * 0.012 * (1 + b)))
            pose.turn(body, X, 0.6 * b)
            self.stand(pose)
            for i, (prefix, pts) in enumerate(self.necks):
                q = p + i * 2.1
                self.neck_pose(pose, 1.5 * math.sin(2 * q), idle_look * math.sin(q), head=3.0 * math.sin(q + 1.0),
                               jaw=jaw * 0.25 * pulse((t + i * 0.23) % 1.0, 0.55, 0.62, 0.68, 0.78), only=prefix)
            self.tail_pose(pose, lambda i: 7.0 * math.sin(p - i * 0.7))
            if self.wing:
                self.folded(pose, 2.5 * b)
            if extra_idle:
                extra_idle(pose, t)
            return P.from_pose(pose)

        def wrap(fn, extra):
            def out(t):
                pose = fn(t)
                if extra:
                    extra(pose, t)
                return P.from_pose(pose)
            return out

        self.add("idle", idle_s, idle)
        walk_fn, walk_speed = self.gait(**walk)
        self.add("walk", walk["frames"] / FPS, wrap(walk_fn, extra_walk), speed=walk_speed)
        if run:
            run = dict(dict(frames=14, duty=0.42, lift=hl * 0.16, crouch=hl * 0.08, phases=self.trot_ph, nod=4.0, lean=3.0),
                       **run)
            run_fn, run_speed = self.gait(**run)
            self.add("run", run["frames"] / FPS, wrap(run_fn, extra_walk), speed=run_speed)

        if eat:
            def eat_fn(t):
                down = pulse(t, 0.0, 0.2, 0.8, 1.0)
                chew = math.sin(2 * math.pi * 6 * t) * down
                pose = Pose(m, (0, 0, -hl * 0.02 * down))
                pose.turn(body, X, eat.get("body", 2.0) * down)
                self.stand(pose)
                self.neck_pose(pose, eat.get("bend", 25.0) * down, head=eat.get("head", 15.0) * down + 2.0 * chew,
                               jaw=4.0 + 4.0 * chew)
                self.tail_pose(pose, lambda i: 8.0 * math.sin(4 * math.pi * t - i))
                if self.wing:
                    self.folded(pose)
                if extra_idle:
                    extra_idle(pose, t)
                return P.from_pose(pose)
            self.add("eat", eat.get("seconds", 3.0), eat_fn)

        def bite(t):
            wind = pulse(t, 0.0, 0.32, 0.38, 0.47)
            hit = pulse(t, 0.38, 0.47, 0.56, 0.95)
            pose = Pose(m, (0, lunge * (0.35 * wind - 1.0 * hit), -hl * (0.03 + 0.05 * hit + 0.02 * wind)))
            pose.turn(body, X, -3.0 * wind + 4.0 * hit)
            self.stand(pose)
            for i, (prefix, pts) in enumerate(self.necks):
                late = 0.0 if i == 0 else math.sin(i * 2.4)
                if attack == "gore":
                    self.neck_pose(pose, -6.0 * wind + 14.0 * hit, 0.0, head=10.0 * wind + 22.0 * hit, only=prefix)
                else:
                    self.neck_pose(pose, -11.0 * wind + 9.0 * hit, 7.0 * late * (wind - hit), head=12.0 * wind - 10.0 * hit,
                                   jaw=jaw * max(wind * 0.6, hit), only=prefix)
            self.tail_pose(pose, lambda i: 4.0 * wind - 6.0 * hit, up=2.0 * hit)
            if self.wing:
                self.folded(pose, 22.0 * wind - 8.0 * hit, open_=0.55 * wind)
            if extra_idle:
                extra_idle(pose, t)
            return P.from_pose(pose)

        if attack:
            self.add("attack", attack_s, bite)

        if breath:
            def breathe(t):
                wind = pulse(t, 0.0, 0.2, 0.24, 0.32)
                out = pulse(t, 0.26, 0.34, 0.8, 0.95)
                p = 2 * math.pi * t
                pose = Pose(m, (0, lunge * (0.3 * wind - 0.5 * out), -hl * (0.03 + 0.06 * out)))
                pose.turn(body, X, -4.0 * wind + 3.0 * out)
                self.stand(pose)
                sweep = 5.0 * math.sin(3 * p) * out
                which = breath.get("neck")
                self.neck_pose(pose, -12.0 * wind + 7.0 * out, sweep, head=14.0 * wind - 2.0 * out,
                               jaw=38.0 * max(wind * 0.4, out), only=which)
                self.tail_pose(pose, lambda i: 5.0 * math.sin(2 * p - i) * out, up=3.0 * out)
                if self.wing:
                    self.folded(pose, 26.0 * wind + 14.0 * out, open_=0.7 * max(wind, out))
                moves = {}
                self.fire_pose(pose, moves, smooth((t - 0.3) / 0.12) * (1.0 - smooth((t - 0.8) / 0.1)), t,
                               head=(which or "") + "head")
                if extra_idle:
                    extra_idle(pose, t)
                return P.from_pose(pose, moves)
            self.add("breath", breath.get("seconds", 2.6), breathe)

        if fly:
            height, pitch = fly.get("height", self.zs * 0.5), fly.get("pitch", 8.0)
            amp, lag, bias = self.wing[4]

            def fly_fn(t):
                p = 2 * math.pi * t
                pose = Pose(m, (0, 0, height - height * 0.08 * math.sin(p + 1.2)))
                pose.turn(body, X, pitch + 2.5 * math.sin(p))
                self.neck_pose(pose, fly.get("neck", 8.0), head=fly.get("head", -20.0))
                self.tail_pose(pose, lambda i: 3.0 * math.sin(p - i), up=fly.get("tail", 4.0))
                self.tuck(pose, fly.get("tuck", 1.0))
                for side, sx in SIDES:
                    pose.turn(self.n(f"wing.1.{side}"), Y, -sx * (bias + amp * math.sin(p)))
                    pose.turn(self.n(f"wing.2.{side}"), Y, -sx * (lag * math.sin(p - 0.9) - 4.0))
                if extra_idle:
                    extra_idle(pose, t)
                return P.from_pose(pose)
            self.add("fly", fly.get("seconds", 1.2), fly_fn, speed=fly.get("speed", 9.0))

        def die(t):
            stagger = pulse(t, 0.0, 0.2, 0.25, 0.4)
            a = smooth((t - 0.2) / 0.6)
            drop = self.zs + self.o.z - wide * 0.5
            pose = Pose(m, (die_side * wide * 0.3 * a, 0, -drop * a * a))
            pose.turn(body, Y, die_side * (4.0 * stagger + 84.0 * a))
            for i, (prefix, pts) in enumerate(self.necks):
                self.neck_pose(pose, 5.0 * a, -die_side * 6.0 * a, head=10.0 * a, jaw=20.0 * a, only=prefix)
            self.tail_pose(pose, lambda i: 5.0 * a * die_side)
            for leg, sx, end in self.LEGS:
                j, k, a_, toe = self.points[leg]
                back = 1.0 if (k.y - j.y) >= 0 else -1.0
                low = sx * die_side > 0                 # The legs that end underneath.
                pose.turn(self.n(f"leg_up.{leg}"), X, back * (18.0 if low else 8.0) * a)
                pose.turn(self.n(f"leg_low.{leg}"), X, -back * (30.0 if low else 14.0) * a)
                pose.turn(self.n(f"leg_up.{leg}"), Y, -sx * (16.0 if low else -6.0) * a)
            if self.wing and self.wing[3][0] == "flank":
                self.folded(pose)
            elif self.wing:
                r, f, s = self.wing[3]
                for side, sx in SIDES:
                    low = sx * die_side > 0
                    pose.turn(self.n(f"wing.1.{side}"), Y, -sx * (r * (1 - a) + (70.0 if low else -30.0) * a))
                    pose.turn(self.n(f"wing.2.{side}"), Y, sx * f * (1 - 0.6 * a))
                    pose.turn(self.n(f"wing.1.{side}"), Z, sx * s)
            if extra_idle:
                extra_idle(pose, 0.0)
            return P.from_pose(pose)
        self.add("die", die_s, die, loops=False)
        return m


def pack(beasts, extra_bones=(), phases=None, **kw):
    """Several beasts in one skeleton, each with its own clips out of step.
    Returns the Mech; `kw` are the arguments of Beast.clips()."""
    bones = []
    for b in beasts:
        bones += b.bone_list()
    m = P.kit.Mech(bones + list(extra_bones))
    phases = phases or [0.37 * i for i in range(len(beasts))]
    for b in beasts:
        b.m = m
        b.clips(register=False, **kw)
    for i, (name, seconds, fn, loops, speed) in enumerate(beasts[0].out):
        def combined(t, i=i, loops=loops, name=name):
            turns, moves = {}, {}
            for j, b in enumerate(beasts):
                # Walking in step keeps every foot on the ground at the same speed.
                tt = (t + phases[j]) % 1.0 if loops else min(1.0, t * (1.0 + 0.12 * j))
                tr, mv = b.out[i][2](tt)
                mv = dict(mv)
                mv[b.n("body")] = mv.pop("root")
                turns.update(tr)
                moves.update(mv)
            return turns, moves
        m.clip(name, seconds, combined, loops=loops, speed=speed)
    return m


def with_extra(m, base, extra):
    """Wraps a clip function of (turns, moves): adds the turns that
    `extra(pose, t)` works out on an empty Pose (bones the clip leaves alone
    or turns further)."""
    def fn(t):
        posed = base(t)
        turns, moves = posed if isinstance(posed, tuple) else (posed, {})
        turns = dict(turns)
        pose = Pose(m)
        extra(pose, t)
        for bone, quat in pose.q.items():
            turns[bone] = list(turns.get(bone, [])) + P.aa(quat)
        return turns, moves
    return fn


def extend(m, name, extra):
    """Replaces the clip `name` of a Mech by the same one with extra turns."""
    m._clips = [c if c[0] != name else (c[0], c[1], c[2], with_extra(m, c[3], extra), c[4]) for c in m._clips]


def save(mb, name, colors, mech, k=1.0):
    return P.save(mb, name, colors, mech, k)


def builder(fn, *args, **kw):
    return lambda: fn(*args, **kw)
