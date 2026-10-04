"""A four-legged organic body for the proposals, with the zoo technique
(studies.Spec welded by remesh, rigs.Beast skeleton). One generator covers
dogs, cats, rats, foxes, dire wolves, goats and donkeys: every measure is
given for a wolf-sized "unit" animal (about 1.9 m from nose to tail tip)
and then scaled by `k`, with options for leg length, bulk, head, snout,
ears, tail and feet (paws or hooves).

The skeleton adds clips to the template's idle, walk, run, eat and die:
attack (a bite lunge or a paw swipe), sit, sleep (lying on the belly) and
howl. All of them loop and start from a pose near idle.
"""

import math

from mathutils import Vector

import _parts as P
import rigs
import studies
from rigs import LEGS, X, smooth

LEG_X = 0.13       # Half the distance between left and right legs.
HEAD_C = Vector((0, -0.69, 0.87))
PAW_TOP = 0.085
SOCK = 0.2
BODY_Z = 0.6       # Below this height the unit animal is leg.

TAIL_DOWN = ([(0, 0.5, 0.66), (0, 0.7, 0.56), (0, 0.84, 0.4), (0, 0.9, 0.26)], [0.05, 0.08, 0.075, 0.045])
TAIL_UP = ([(0, 0.5, 0.66), (0, 0.64, 0.8), (0, 0.64, 0.96), (0, 0.54, 1.06)], [0.05, 0.05, 0.045, 0.035])
TAIL_CAT = ([(0, 0.5, 0.66), (0, 0.7, 0.7), (0, 0.84, 0.86), (0, 0.86, 1.06), (0, 0.78, 1.22)],
            [0.05, 0.045, 0.042, 0.04, 0.036])
TAIL_BRUSH = ([(0, 0.5, 0.66), (0, 0.72, 0.6), (0, 0.94, 0.5), (0, 1.12, 0.42)], [0.05, 0.1, 0.11, 0.05])
TAIL_STUB = ([(0, 0.5, 0.68), (0, 0.58, 0.76), (0, 0.62, 0.84)], [0.045, 0.04, 0.03])

TAGS = {}   # Detail vertex -> bone, filled by details() and read by the rig.


def tag(verts, bone):
    for v in verts:
        TAGS[v] = bone
    return verts


class PetRig(rigs.Beast):
    """rigs.Beast with the family's extra clips."""

    k = 1.0
    extra = ("attack", "sit", "sleep")
    attack = "bite"       # Or "swipe": a front paw strikes.
    sit_angle = 25.0
    sit_tail = 27.0       # Degrees the tail lifts so it lies on the ground.
    lie_tail = 22.0
    belly_z = 0.3         # Lowest point of the trunk at rest (m).
    low = 1.0             # Short legs: how much less the head may go down.

    def piece_bone(self, center, piece):
        return TAGS.get(piece[0]) or super().piece_bone(center, piece)

    def fk_leg(self, leg, phi1, phi2, pitch=0.0, foot=0.0):
        """Poses a leg by the angles of its two bones in the side plane
        (degrees from straight down, positive toward the back)."""
        hip, knee, ankle, toe = self.leg_points[leg]
        r1 = math.degrees(math.atan2((knee - hip).y, -(knee - hip).z))
        r2 = math.degrees(math.atan2((ankle - knee).y, -(ankle - knee).z))
        d1, d2 = phi1 - r1, phi2 - r2
        return {f"leg_upper.{leg}": [(X, d1 - pitch)], f"leg_lower.{leg}": [(X, d2 - d1)],
                f"foot.{leg}": [(X, foot - d2)]}

    def feet(self, rot, pitch, dz, dy=0.0, shift=None, lift=None):
        """Inverse kinematics for every leg with the body moved by (dy, dz)
        and pitched: the feet stay where they stand, plus `shift` {leg or
        "F"/"H": (y, z)}."""
        pivot = self.by_name["body"].head
        for leg in LEGS:
            ankle = self.leg_points[leg][2].copy()
            ankle.y -= dy
            s = (shift or {}).get(leg) or (shift or {}).get(leg[0])
            if s:
                ankle.y += s[0]
                ankle.z += s[1]
            rot.update(self.leg_pose(leg, ankle, pitch, dz, pivot, (lift or {}).get(leg, 0.0)))
        return rot

    def attack_pose(self, t):
        k = self.k
        wind = P.pulse(t, 0.0, 0.28, 0.3, 0.42)
        lunge = P.pulse(t, 0.3, 0.42, 0.5, 0.9)
        dy = (0.05 * wind - 0.15 * lunge) * k
        low = self.low
        dz = -(0.05 * wind + 0.03 * lunge) * k * low
        pitch = math.radians(-4.0 * wind + 6.0 * lunge * low)
        shift, lift = {}, {}
        if self.attack == "swipe":
            # The right front paw rises, strikes forward and down.
            up = P.pulse(t, 0.1, 0.34, 0.36, 0.5)
            hit = P.pulse(t, 0.34, 0.48, 0.5, 0.85)
            shift["FR"] = ((-0.1 * up - 0.24 * hit) * k, (0.3 * up + 0.1 * hit) * k)
            lift["FR"] = math.radians(-50.0 * up + 20.0 * hit)
            dy *= 0.5
        rot = self.feet({}, pitch, dz, dy, shift, lift)
        rot["body"] = [(X, math.degrees(pitch))]
        rot["neck"] = [(X, -12.0 * wind + 10.0 * lunge * low)]
        rot["head"] = [(X, -18.0 * wind + 22.0 * lunge * low)]
        for side in ("L", "R"):
            rot[f"ear.{side}"] = [(X, -20.0 * max(wind, lunge))]
        self.tail_rot(rot, 0.0, 8.0 * lunge - 6.0 * wind)
        return rot, Vector((0, dy, dz)), {}

    def sit_pose(self, t):
        k = self.k
        p = 2 * math.pi * t
        breath = math.sin(2 * p)
        a = math.radians(-self.sit_angle)
        pivot = self.by_name["body"].head
        rel = self.leg_points["FL"][0] - pivot
        dz = rel.z - (rel.y * math.sin(a) + rel.z * math.cos(a)) - 0.004 * k * (1 + breath)
        rot = self.feet({}, a, dz, 0.0, {"F": (0.09 * k, 0.0)})
        for leg in ("HL", "HR"):       # The hocks rest on the ground, the paws forward.
            hip, knee, ankle, toe = self.leg_points[leg]
            rel = hip - pivot
            h = pivot.z + rel.y * math.sin(a) + rel.z * math.cos(a) + dz
            l1 = math.hypot(knee.y - hip.y, knee.z - hip.z)
            fold = math.degrees(math.acos(max(-1.0, min(1.0, (h - 0.125 * k) / l1))))
            rot.update(self.fk_leg(leg, fold, -82.0, -self.sit_angle))
        rot["body"] = [(X, -self.sit_angle)]
        rot["chest"] = [(X, 3.0 + 1.5 * breath)]
        rot["neck"] = [(X, self.sit_angle * 0.4), (rigs.Z, 6.0 * math.sin(p))]
        rot["head"] = [(X, self.sit_angle * 0.5), (rigs.Z, 9.0 * math.sin(p))]
        rot["ear.L"] = [(X, 12.0 * P.pulse(t, 0.55, 0.6, 0.62, 0.68))]
        self.tail_rot(rot, 16.0 * math.sin(2 * p), self.sit_tail)
        return rot, Vector((0, 0, dz)), {}

    def sleep_pose(self, t):
        k = self.k
        breath = math.sin(2 * math.pi * 2 * t)
        dz = -(self.belly_z - 0.045 * k) + 0.004 * k * breath
        rot = {}
        for leg in LEGS:
            hip, knee, ankle, toe = self.leg_points[leg]
            h = hip.z + dz
            l1 = math.hypot(knee.y - hip.y, knee.z - hip.z)
            fold = math.degrees(math.acos(max(-1.0, min(1.0, (h - 0.11 * k) / l1))))
            if leg[0] == "F":
                rot.update(self.fk_leg(leg, fold, -86.0))     # Elbow back, forearm forward.
            else:
                rot.update(self.fk_leg(leg, -fold, 84.0))     # Knee forward, shank back.
        rot["chest"] = [(X, 8.0 + 1.5 * breath)]
        rot["neck"] = [(X, 34.0)]
        rot["head"] = [(X, -22.0 + 1.0 * breath)]
        for side in ("L", "R"):
            rot[f"ear.{side}"] = [(X, -10.0)]
        self.tail_rot(rot, 30.0, self.lie_tail)
        return rot, Vector((0, 0, dz)), {}

    def howl_pose(self, t):
        k = self.k
        up = P.pulse(t, 0.0, 0.25, 0.8, 1.0)
        shake = math.sin(2 * math.pi * 5 * t) * P.pulse(t, 0.25, 0.3, 0.75, 0.8)
        pitch = math.radians(-5.0 * up)
        dz = -0.02 * k * up
        rot = self.feet({}, pitch, dz)
        rot["body"] = [(X, math.degrees(pitch))]
        rot["chest"] = [(X, -6.0 * up)]
        rot["neck"] = [(X, -30.0 * up)]
        rot["head"] = [(X, -32.0 * up + 2.0 * shake)]
        for side in ("L", "R"):
            rot[f"ear.{side}"] = [(X, -25.0 * up)]
        self.tail_rot(rot, 4.0 * shake, -6.0 * up)
        return rot, Vector((0, 0, dz)), {}

    def clips(self):
        out = super().clips()
        table = {"attack": (24, self.attack_pose), "sit": (90, self.sit_pose), "sleep": (120, self.sleep_pose),
                 "howl": (90, self.howl_pose)}
        for name in self.extra:
            out.append((name, table[name][0], True, table[name][1], None))
        return out


class Quad(studies.Spec):
    """See the module's text. `paint` is a function (u, n) -> material with
    `u` the face's center in unit coordinates; `extra` a function (spec, mb)
    for more details (a collar, spikes, a saddle), which tags its pieces to
    bones with quad.tag()."""

    def __init__(self, name, colors, paint, k=1.0, bulk=1.0, leg=1.0, head=1.0, snout=1.0, snout_r=1.0,
                 neck=1.0, ruff=1.0, ears="up", ear_size=1.0, tail=TAIL_DOWN, tail_detail=None, hooves=False,
                 leg_r=1.0, tone="fur", extra=None, clips=("attack", "sit", "sleep"), attack="bite",
                 speed=1.0, trot=False, max_tris=1500, budget=800, eye=0.017, inner_ear="dark",
                 sit_tail=27.0, lie_tail=22.0, belly=1.0, eat=(8.0, 8.0, 30.0, 20.0), snout_end=1.0):
        self.name = name
        self.colors = colors
        self.k, self.leg_f, self.bulk, self.head_f = k, leg, bulk, head
        self.paint_fn, self.extra, self.ears, self.ear_size = paint, extra, ears, ear_size
        self.hooves, self.eye_r, self.inner_ear = hooves, eye, inner_ear
        self.tone_material = tone
        self.max_tris, self.budget = max_tris, budget
        self.tail_pts, self.tail_r = tail
        self.tail_detail = tail_detail   # Material of a thin tail built from pieces, or None.
        M, R = self.M, self.R
        lx = LEG_X * bulk
        self.lx = lx
        self.head_c = HEAD_C.copy()
        self.snout_a = HEAD_C + Vector((0, -0.09 * head, -0.03 * head))
        self.snout_b = self.snout_a + Vector((0, -0.16 * snout, -0.04 * snout))
        self.snout_rb = 0.052 * snout_r * snout_end   # A blunt muzzle: snout_end > 1.
        self.ellipsoids = [
            (M((0, -0.26, 0.61)), R((0.19 * bulk, 0.32, 0.24))),      # Chest.
            (M((0, 0.02, 0.61)), R((0.16 * bulk, 0.3, 0.17 * belly))),   # Belly.
            (M((0, 0.3, 0.61)), R((0.16 * bulk, 0.27, 0.19))),        # Hips.
            (M((0, -0.5, 0.72)), R((0.18 * ruff * neck, 0.16, 0.22 * ruff))),   # Neck ruff.
            (M(HEAD_C), R((0.14 * head, 0.14 * head, 0.13 * head))),
        ]
        for s in (-1, 1):
            self.ellipsoids.append((M((s * lx * 0.8, 0.36, 0.52)), R((0.08 * leg_r, 0.15, 0.17))))   # Thighs.
        self.capsules = [
            (M((0, -0.42, 0.66)), M((0, -0.62, 0.82)), 0.15 * neck * k, 0.13 * neck * k),
            (M(self.snout_a), M(self.snout_b), 0.08 * snout_r * head * k, self.snout_rb * k),
        ]
        for s in (-1, 1):
            x = s * lx
            r = leg_r * k
            self.capsules += [
                (M((x * 0.9, -0.33, 0.62)), M((x, -0.35, 0.3)), 0.075 * r, 0.055 * r),
                (M((x, -0.35, 0.3)), M((x, -0.37, 0.06)), 0.048 * r, 0.042 * r),
                (M((x * 0.9, 0.36, 0.52)), M((x, 0.48, 0.24)), 0.08 * r, 0.05 * r),
                (M((x, 0.48, 0.24)), M((x, 0.44, 0.06)), 0.045 * r, 0.042 * r),
            ]
            if hooves:
                self.capsules += [
                    (M((x, -0.37, 0.07)), (x * k, -0.375 * k, 0.03 * k), 0.046 * r, 0.052 * r),
                    (M((x, 0.44, 0.07)), (x * k, 0.435 * k, 0.03 * k), 0.046 * r, 0.052 * r),
                ]
            else:
                paw = M((0, 0, 0.04))[2]
                self.capsules += [
                    ((x * k, -0.36 * k, paw), (x * k, -0.44 * k, paw), 0.045 * r, 0.04 * r),
                    ((x * k, 0.45 * k, paw), (x * k, 0.37 * k, paw), 0.044 * r, 0.04 * r),
                ]
        if tail_detail is None:
            pts = [M(p) for p in self.tail_pts]
            self.capsules += [(a, b, ra * k, rb * k) for a, b, ra, rb in
                              zip(pts, pts[1:], self.tail_r, self.tail_r[1:])]
        sock = M((0, 0, SOCK))[2]
        self.cuts = [((0, 0, sock), (0, 0, 1), lambda c, n: c.z < sock + 0.1 * k and abs(c.y) > 0.25 * k)]
        paw_top = M((0, 0, PAW_TOP))[2]
        if hooves:
            self.cuts.append(((0, 0, paw_top), (0, 0, 1), lambda c, n: c.z < 0.2 * k))

        ear_a, ear_b, ear_tip = self.ear_points(1)
        f = min(1.0, leg) * speed
        rig = PetRig(
            body=(M((0, 0.56, 0.63)), M((0, -0.02, 0.61))),
            chest=(M((0, -0.02, 0.61)), M((0, -0.42, 0.66))),
            neck=(M((0, -0.42, 0.66)), M((0, -0.62, 0.82))),
            head=(M((0, -0.62, 0.82)), M(self.snout_b + Vector((0, -0.04, 0)))),
            ears=(tuple((ear_a + ear_b) * 0.5), tuple(ear_tip)),
            tail=[M((0, 0.57, 0.63))] + [M(p) for p in self.tail_pts[1:]],
            legs={
                "F": (M((lx, -0.34, 0.62)), M((lx, -0.35, 0.3)), M((lx, -0.37, PAW_TOP)),
                      (lx * k, -0.5 * k, 0.0)),
                "H": (M((lx, 0.4, 0.52)), M((lx, 0.48, 0.24)), M((lx, 0.44, PAW_TOP)),
                      (lx * k, 0.33 * k, 0.0)),
            },
            leg_exit=(M((0, 0, 0.33))[2], M((0, 0, 0.42))[2]),
            leg_reach=0.2 * k * max(1.0, leg_r * 0.9),
            walk=rigs.Gait(speed=1.0 * k * f, frames=16, duty=0.62, lift=0.06 * k, crouch=0.06 * k * min(1.0, leg),
                           bob=0.01 * k, phases=rigs.WALK_PHASES, wag=10.0),
            run=(rigs.Gait(speed=2.4 * k * f, frames=12, duty=0.42, lift=0.1 * k, crouch=0.08 * k * min(1.0, leg),
                           bob=0.015 * k, phases=rigs.TROT_PHASES, nod=5.0, wag=8.0) if trot else
                 rigs.Gait(speed=4.5 * k * f, frames=10, duty=0.3, lift=0.12 * k, crouch=0.1 * k * min(1.0, leg),
                           bob=0.015 * k, phases=rigs.GALLOP_PHASES, nod=4.0, wag=6.0)),
            lie_height=0.2 * k,
            blend=0.05 * k,
        )
        rig.k = k
        rig.extra = tuple(clips)
        rig.attack = attack
        rig.tail_reach = None if tail_detail else 0.12 * k
        rig.low = min(1.0, leg) ** 2.2
        rig.eat = tuple(e * rig.low for e in eat)
        rig.eat_drop = 0.03 * k
        rig.sit_tail, rig.lie_tail = sit_tail, lie_tail
        rig.belly_z = min(M((0, 0, 0.61 - 0.24))[2], M((0, 0, 0.61 - 0.17 * belly))[2])
        self.rig = rig

    # ------------------------------------------------------------ mapping

    def zmap(self, z):
        f = self.leg_f
        return z * f if z < BODY_Z else z + BODY_Z * (f - 1.0)

    def M(self, p):
        """A unit point in the model: legs lengthened, then scaled."""
        return (p[0] * self.k, p[1] * self.k, self.zmap(p[2]) * self.k)

    def R(self, r):
        return tuple(x * self.k for x in r)

    def U(self, c):
        """The unit point of a model point (the inverse of M)."""
        f = self.leg_f
        z = c.z / self.k
        z = z / f if z < BODY_Z * f else z - BODY_Z * (f - 1.0)
        return Vector((c.x / self.k, c.y / self.k, z))

    def V(self, p):
        return Vector(self.M(p))

    def H(self, x, y, z):
        """A point given from the head's center, in head sizes."""
        return self.V(self.head_c + Vector((x, y, z)) * self.head_f)

    def ear_points(self, s):
        e = self.ear_size
        if self.ears == "flop":
            a, b = Vector((0.07, 0.0, 0.11)), Vector((0.128, 0.03, 0.06))
            tip = Vector((0.15 + 0.03 * e, -0.02, 0.06 - 0.16 * e))
        elif self.ears == "long":      # A donkey's: tall, leaning out.
            a, b = Vector((0.04, 0.02, 0.11)), Vector((0.11, 0.04, 0.08))
            tip = Vector((0.13, 0.06, 0.1 + 0.26 * e))
        elif self.ears == "side":      # Cattle and goats: sticking out sideways.
            a, b = Vector((0.09, 0.03, 0.09)), Vector((0.1, 0.05, 0.02))
            tip = Vector((0.1 + 0.2 * e, 0.07, 0.03))
        elif self.ears == "round":
            a, b = Vector((0.03, 0.02, 0.1)), Vector((0.12, 0.04, 0.05))
            tip = Vector((0.11, 0.03, 0.09 + 0.1 * e))
        else:
            a, b = Vector((0.035, 0.0, 0.10)), Vector((0.12, 0.03, 0.06))
            tip = Vector((0.1, -0.01, 0.08 + 0.15 * e))
        return tuple(self.H(s * p.x, p.y, p.z) for p in (a, b, tip))

    def paint(self, c, n):
        return self.paint_fn(self.U(c), n)

    def details(self, mb):
        TAGS.clear()
        k, hk = self.k, self.k * self.head_f
        for s in (-1, 1):
            tag(mb.sphere(self.H(s * 0.062, -0.12, 0.04), self.eye_r * hk, "eye", segments=6, rings=4), "head")
            a, b, tip = self.ear_points(s)
            studies.flap(mb, a, b, tip, 0.025 * hk, self.tone_material if "ear" not in self.colors else "ear")
            if self.ears in ("up", "long", "round"):
                inner = [p + Vector((0, -0.016 * hk, 0)) for p in (a, b, tip)]
                mid = sum(inner, Vector()) / 3
                studies.flap(mb, *[mid + (p - mid) * 0.6 for p in inner], 0.015 * hk, self.inner_ear)
        tip = self.V(self.snout_b)
        r = self.snout_rb * k
        tag(mb.sphere((tip.x, tip.y - r * 0.85, tip.z + r * 0.3), r * 0.62, "nose", segments=6, rings=4,
                      scale=(1.0, 0.7, 0.7)), "head")
        if self.tail_detail:
            pts = [self.V(p) for p in self.tail_pts]
            for i, (a, b) in enumerate(zip(pts, pts[1:])):
                tag(mb.cylinder(a, b, self.tail_r[i] * k, self.tail_r[i + 1] * k, self.tail_detail, segments=5),
                    f"tail.{i + 1}")
        if self.extra:
            self.extra(self, mb)


# ------------------------------------------------------- paint functions

def wolf_coat(main="fur", light="light", dark="dark", saddle=True, tail_tip=None, socks=True, muzzle=True,
              belly=True):
    """The wolf's pattern in unit coordinates, each part optional."""
    def paint(u, n):
        if tail_tip and u.y > 0.75 and (u.y > 0.98 or u.z < 0.34 or u.z > 0.98):
            return tail_tip
        if socks and u.z < SOCK and 0.25 < abs(u.y) < 0.6:
            return socks if isinstance(socks, str) else light
        if muzzle and u.y < -0.83 and u.z < 0.84:
            return muzzle if isinstance(muzzle, str) else light
        if belly and u.y < -0.38 and u.z < 0.74 and abs(u.x) < 0.13 and n.y < 0.2 and n.z < 0.4:
            return light   # Throat and chest.
        if belly and -0.4 < u.y < 0.5 and u.z < 0.5 and n.z < -0.1 and abs(u.x) < 0.11:
            return light
        if saddle and u.z > 0.74 and -0.38 < u.y < 0.5 and n.z > 0.45:
            return saddle if isinstance(saddle, str) else dark
        return main
    return paint


def hoof_coat(inner):
    """Wraps a paint function: hooves below the fetlock."""
    def paint(u, n):
        if u.z < PAW_TOP:
            return "hoof"
        return inner(u, n)
    return paint
