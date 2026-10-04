"""Farmyard birds with the zoo technique and the rigs_bird skeleton: hen
(brown and white), chick, duck (mallard and white) and goose (white and
gray). One generator: the rooster's measures as the "unit" bird, scaled,
with options for the neck, the legs, the bill, the feet and the tail.
Clips: idle, walk, run, eat, die and fly (a flutter), plus sit (brooding,
for the hen and the duck) and attack (a lunge with the neck stretched and
the wings out, for the goose)."""

import math

from mathutils import Vector

import _parts as P
import rigs_bird
import studies
from rigs import Bone, Pose, X, Z

LEG_X = 0.045
LEG_TOP = 0.2            # Below this height the unit bird is leg.
TAIL_BASE = (0.0, 0.15, 0.35)
WING = [(0.055, -0.04, 0.34), (0.055, 0.03, 0.365), (0.055, 0.15, 0.33), (0.055, 0.14, 0.27), (0.055, 0.02, 0.235)]


class FowlRig(rigs_bird.Bird):
    k = 1.0
    extra = ()
    sit_drop = 0.05

    def sit_pose(self, t):
        breath = math.sin(2 * math.pi * 2 * t)
        pose = Pose(self, (0, 0, -self.sit_drop + 0.002 * self.k * breath))
        pose.turn("body", X, 3.0 + breath)
        self.stand(pose, both=True)
        self.turn_neck(pose, Z, 22.0 * math.sin(2 * math.pi * t), 0.6)
        if self.tail:
            pose.turn(self.tail[0], X, 6.0 + 2.0 * breath)
        return pose.q, pose.offset, {}

    def attack_pose(self, t):
        k = self.k
        w = P.pulse(t, 0.0, 0.3, 0.34, 0.44)
        s = P.pulse(t, 0.34, 0.44, 0.5, 0.9)
        pose = Pose(self, (0, (0.02 * w - 0.05 * s) * k, -0.015 * k * s))
        pose.turn("body", X, -10.0 * w + 20.0 * s)
        self.stand(pose, both=True)
        for name in self.neck:
            pose.turn(name, X, (-20.0 * w + 34.0 * s) / len(self.neck))
        pose.turn("head", X, 6.0 * w - 30.0 * s)
        self.wings_out(pose, 45.0 * max(w, s), 12.0 * math.sin(50 * t) * s)
        if self.tail:
            pose.turn(self.tail[0], X, 12.0 * s)
        return pose.q, pose.offset, {}

    def clips(self):
        out = super().clips()
        table = {"sit": (120, self.sit_pose), "attack": (24, self.attack_pose)}
        for name in self.extra:
            out.append((name, table[name][0], True, table[name][1], None))
        return out


class Fowl(studies.Spec):
    tones = 0.35

    def __init__(self, name, colors, paint, k=1.0, ly=1.0, lf=1.0, neck_up=0.0, neck_fwd=0.0, neck_r=1.0, head=1.0,
                 bill="beak", webbed=False, comb=False, tail="fan", wing_mat="main", clips=(), budget=268,
                 max_tris=1000, flight=None, bulk=1.0):
        self.name, self.colors, self.paint_fn = name, colors, paint
        self.k, self.ly, self.lf, self.head_f = k, ly, lf, head
        self.bill, self.webbed, self.comb, self.tail_kind, self.wing_mat = bill, webbed, comb, tail, wing_mat
        self.budget, self.max_tris = budget, max_tris
        self.tone_material = "main"
        M = self.M
        self.head_c = Vector((0.0, -0.115 - neck_fwd, 0.47 + neck_up))
        neck_top = Vector((0.0, -0.1 - neck_fwd, 0.45 + neck_up))
        hr = tuple(r * head * k for r in (0.048, 0.058, 0.052))
        self.ellipsoids = [
            (M((0, -0.05, 0.28)), (0.11 * bulk * k, 0.12 * ly * k, 0.125 * k)),      # Breast.
            (M((0, 0.07, 0.3)), (0.1 * bulk * k, 0.13 * ly * k, 0.105 * k)),         # Back.
            (M(self.head_c), hr),
            (M((LEG_X, 0.02, 0.2)), (0.045 * k, 0.065 * k, 0.065 * k)),              # Thighs.
            (M((-LEG_X, 0.02, 0.2)), (0.045 * k, 0.065 * k, 0.065 * k)),
            (M((0, 0.17, 0.35)), (0.05 * k, 0.06 * ly * k, 0.06 * k)),               # Tail root.
        ]
        self.capsules = [(M((0, -0.06, 0.33)), M(neck_top), 0.078 * neck_r * k, 0.052 * neck_r * k)]
        base = Vector((0, -0.07, 0.33))
        steps = 3 if neck_up > 0.08 else 2
        neck = [M(base.lerp(neck_top, i / steps) + Vector((0, 0.02 * math.sin(math.pi * i / steps) * (steps - 2), 0)))
                for i in range(steps + 1)]
        self.beak_tip = self.head_c + Vector((0, -0.1 * head, -0.012 * head))
        extra_bones, dangles = [], {}
        if comb:
            hc = self.head_c
            extra_bones = [Bone("comb", M(hc + Vector((0, 0, 0.035))), M(hc + Vector((0, 0, 0.08))), parent="head"),
                           Bone("wattle", M(hc + Vector((0, -0.045, -0.02))), M(hc + Vector((0, -0.045, -0.06))),
                                parent="head")]
            dangles = {"comb": (rigs_bird.X, 12.0), "wattle": (rigs_bird.X, 20.0)}
        air = dict(name="fly", frames=12, beats=2, pitch=-22.0, lift=0.15 * k, amp=55.0, mid=10.0, tuck=35.0,
                   speed=2.5, bob=0.015 * k)
        air.update(flight or {})
        rig = FowlRig(
            body=(M((0, 0.1, 0.29)), M((0, -0.07, 0.33))),
            neck=neck,
            head=(M(neck_top), M(self.head_c + Vector((0, -0.055 * head, 0)))),
            beak_tip=M(self.beak_tip),
            tail=[M(TAIL_BASE), M((0, 0.27, 0.43))],
            legs=(M((LEG_X, 0.02, 0.25)), M((LEG_X, 0.02, 0.17)), M((LEG_X, 0.0, 0.012)), M((LEG_X, -0.06, 0.006))),
            leg_exit=(M((0, 0, 0.17))[2], M((0, 0, 0.23))[2]), leg_reach=0.07 * k, blend=0.04 * k,
            wings=[M((0.055, -0.03, 0.34)), M((0.055, 0.15, 0.3))], wing_sides=[(0, 0, -1)], wing_twitch=0.0,
            walk=rigs_bird.Step(frames=20, duty=0.62, crouch=0.02 * k * lf, lift=0.05 * k * lf, bob=0.004 * k,
                                head_bob=14.0 if not webbed else 6.0, tail=5.0, waddle=7.0 if webbed else 0.0),
            run=rigs_bird.Step(frames=10, duty=0.4, crouch=0.035 * k * lf, lift=0.07 * k * lf, bob=0.008 * k,
                               head_bob=8.0 if not webbed else 3.0, lean=12.0, tail=8.0,
                               waddle=9.0 if webbed else 0.0, wings=0.0 if not webbed else 12.0),
            eat=dict(pitch=(40.0 if neck_up < 0.08 else 20.0) * lf ** 2, crouch=0.035 * k * lf ** 3, head=75.0, height=0.025 * k),
            air=air, lie_height=0.09 * k, dangles=dangles, extra_bones=extra_bones,
        )
        rig.k = k
        rig.extra = tuple(clips)
        rig.sit_drop = (self.zmap(0.2) - 0.065) * k - 0.004 * k
        self.rig = rig
        breast = Vector((0, -1, -0.35)).normalized()
        self.cuts = [(M((0, -0.03, 0.3)), breast, lambda c, n: c.z < M((0, 0, 0.38))[2])]

    def zmap(self, z):
        return z * self.lf if z < LEG_TOP else z - LEG_TOP * (1.0 - self.lf)

    def M(self, p):
        return (p[0] * self.k, p[1] * self.ly * self.k, self.zmap(p[2]) * self.k)

    def V(self, p):
        return Vector(self.M(p))

    def U(self, c):
        z = c.z / self.k
        z = z / self.lf if z < LEG_TOP * self.lf else z + LEG_TOP * (1.0 - self.lf)
        return Vector((c.x / self.k, c.y / (self.ly * self.k), z))

    def H(self, x, y, z):
        return self.V(self.head_c + Vector((x, y, z)) * self.head_f)

    def paint(self, c, n):
        return self.paint_fn(self.U(c), n)

    def details(self, mb):
        k, tag, V, H = self.k, rigs_bird.tag, self.V, self.H
        for s in (-1, 1):
            side = "L" if s > 0 else "R"
            tag(mb, mb.sphere(H(s * 0.036, -0.03, 0.012), 0.01 * k * self.head_f, "eye", segments=5, rings=3), "head")
            tag(mb, studies.plate(mb, [V((s * x, y, z)) for x, y, z in WING], 0.01 * k, self.wing_mat),
                f"wing.{side}")
            x = s * LEG_X
            tag(mb, mb.cylinder(V((x, 0.02, 0.17)), V((x, 0.0, 0.015)), 0.015 * k, 0.012 * k, "leg", segments=5),
                f"leg_lower.{side}")
            ankle = V((x, 0.0, 0.01))
            if self.webbed:
                tag(mb, studies.plate(mb, [ankle + Vector((0, 0.01, 0)) * k, ankle + Vector((-0.04, -0.075, -0.004)) * k,
                                           ankle + Vector((0.0, -0.085, -0.004)) * k,
                                           ankle + Vector((0.04, -0.075, -0.004)) * k], 0.008 * k, "leg"),
                    f"foot.{side}")
            else:
                for dx, dy in ((-0.028, -0.05), (0.0, -0.06), (0.028, -0.05), (0.0, 0.035)):
                    tag(mb, mb.cylinder(ankle, ankle + Vector((dx, dy, -0.004)) * k, 0.009 * k, 0.005 * k, "leg",
                                        segments=3), f"foot.{side}")
        if self.bill == "beak":
            tag(mb, mb.cylinder(H(0, -0.045, -0.002), H(0, -0.1, -0.012), 0.018 * k * self.head_f, 0.0, "bill",
                                segments=5), "head")
        else:   # A flat bill, wider at the tip.
            pts = [H(sx * w, y, z) for sx in (-1, 1) for w, y, z in ((0.018, -0.04, 0.008), (0.018, -0.04, -0.016),
                                                                    (0.024, -0.12, -0.012), (0.024, -0.12, -0.026))]
            tag(mb, P.hull(mb, pts + [H(0, -0.13, -0.018)], "bill"), "head")
        if self.comb:
            for y, h in ((-0.03, 0.022), (0.0, 0.03), (0.028, 0.02)):
                tag(mb, studies.plate(mb, [H(0, y - 0.016, 0.04), H(0, y + 0.016, 0.042), H(0, y + 0.008, 0.045 + h),
                                           H(0, y - 0.01, 0.045 + h)], 0.012 * k, "comb"), "comb")
            tag(mb, studies.plate(mb, [H(0, -0.035, -0.02), H(0, -0.06, -0.024), H(0, -0.055, -0.055),
                                       H(0, -0.038, -0.05)], 0.014 * k, "comb"), "wattle")
        base = Vector(TAIL_BASE)
        if self.tail_kind == "fan":
            for a, x in ((38, 0.0), (58, 0.03), (58, -0.03)):
                d = Vector((x * 2.5, math.cos(math.radians(a)), math.sin(math.radians(a))))
                tip = base + d * 0.19
                wide = Vector((0.0, -d.z, d.y)) * 0.045
                tag(mb, studies.plate(mb, [V(base + Vector((x, 0.0, -0.02))), V(base + d * 0.1 - wide),
                                           V(tip), V(base + d * 0.1 + wide)], 0.012 * k, "tail"), "tail")
        else:
            tag(mb, P.hull(mb, [V(p) for p in ((-0.05, 0.17, 0.35), (0.05, 0.17, 0.35), (0, 0.17, 0.39),
                                               (0, 0.15 + 0.13 / self.ly, 0.41), (0, 0.18, 0.31))], "tail"), "tail")


# ----------------------------------------------------------------- models

def hen_coat(u, n):
    if u.z < 0.19 and u.y > -0.08:
        return "light"
    if (u - Vector((0, -0.03, 0.3))).dot(Vector((0, -1, -0.35)).normalized()) > 0 and u.z < 0.38:
        return "light"                                           # Breast.
    return "main"


def hen(name, main, light):
    colors = {**P.shades("main", main), **P.palette(light=light, tail=_darker(main), comb=0xD8302A, bill=0xF4BE2A,
                                                    leg=0xE8B030, eye=0x151012)}
    return Fowl(name, colors, hen_coat, k=0.9, comb=True, tail="fan", clips=("sit",), bulk=1.1)


def chick(name):
    colors = {**P.shades("main", 0xF6D860), **P.palette(light=0xFBE88A, tail=0xF0C840, bill=0xF09A2A, leg=0xF09A2A,
                                                        eye=0x151012)}
    return Fowl(name, colors, hen_coat, k=0.36, head=1.45, tail="point", budget=180, max_tris=600, bulk=1.15)


def mallard(u, n):
    if u.y < -0.085 and u.z > 0.41:
        return "head"
    if 0.375 < u.z <= 0.41 and u.y < -0.04:
        return "ring"
    if (u - Vector((0, -0.03, 0.3))).dot(Vector((0, -1, -0.35)).normalized()) > 0 and u.z < 0.375:
        return "breast"
    if u.y > 0.15:
        return "dark"
    if abs(u.x) > 0.06 and 0.26 < u.z < 0.33 and 0.02 < u.y < 0.14:
        return "wing"
    return "main"


def plain(u, n):
    return "main"


def duck(name, mallard_colors=True):
    if mallard_colors:
        colors = {**P.shades("main", 0xB9B2A6), **P.palette(head=0x1F6A4A, ring=0xF4F0E8, breast=0x7A4A32,
                                                            dark=0x2E2A28, wing=0x3A62B8, tail=0x2E2A28, bill=0xE8C030,
                                                            leg=0xF08A2A, eye=0x151012)}
        coat = mallard
    else:
        colors = {**P.shades("main", 0xF4F1EA), **P.palette(tail=0xF4F1EA, bill=0xF0A02A, leg=0xF08A2A, eye=0x151012)}
        coat = plain
    return Fowl(name, colors, coat, k=1.0, ly=1.25, lf=0.62, neck_up=0.02, neck_fwd=0.03, bill="flat", webbed=True,
                tail="point", clips=("sit",),
                flight=dict(frames=10, beats=1, pitch=-8.0, amp=50.0, mid=8.0, tuck=60.0, speed=6.0))


def goose(name, main, bill=0xF08A2A, neck=None):
    colors = {**P.shades("main", main), **P.palette(tail=main, bill=bill, leg=0xF08A2A, eye=0x151012,
                                                    neck=neck if neck is not None else main)}

    def coat(u, n):
        if neck is not None and u.z > 0.4 and u.y < -0.04:
            return "neck"
        return "main"

    return Fowl(name, colors, coat, k=1.55, ly=1.3, lf=0.8, neck_up=0.17, neck_fwd=0.05, neck_r=0.72, head=0.85,
                bill="flat", webbed=True, tail="point", clips=("attack",), max_tris=1200, budget=330,
                flight=dict(frames=12, beats=1, pitch=-6.0, amp=48.0, mid=8.0, tuck=60.0, speed=7.0))


FLIGHT = dict(frames=10, beats=1, pitch=-8.0, amp=55.0, mid=8.0, tuck=60.0, speed=7.0)


def crow(name, k=0.6):
    colors = {**P.shades("main", 0x24242C, light=0.1), **P.palette(tail=0x16161C, bill=0x2E2E34, leg=0x2E2E34,
                                                                  eye=0xC8CCD8)}
    return Fowl(name, colors, plain, k=k, head=1.05, tail="point", flight=FLIGHT, budget=240, max_tris=800)


def vulture(name):
    colors = {**P.shades("main", 0x4A3A30), **P.palette(tail=0x2E2420, bill=0xD8C8A0, leg=0xC8B8A0, eye=0x151012,
                                                        skin=0xD88A80, ruff=0xF0ECE0)}

    def coat(u, n):
        if u.z > 0.445:
            return "skin"                                   # The bare head and neck.
        if 0.37 < u.z <= 0.445 and u.y < 0.02:
            return "ruff"
        return "main"

    return Fowl(name, colors, coat, k=1.45, ly=1.15, neck_up=0.12, neck_fwd=0.05, neck_r=0.62, head=0.9, tail="point",
                clips=("attack",), max_tris=1200, budget=320,
                flight=dict(frames=30, beats=1, pitch=-4.0, amp=20.0, mid=10.0, tuck=60.0, speed=8.0))


def songbird(name, main, breast):
    colors = {**P.shades("main", main), **P.palette(light=breast, tail=_darker(main), bill=0x3A3028, leg=0x6A5A4A,
                                                    eye=0x151012)}
    return Fowl(name, colors, hen_coat, k=0.3, head=1.25, tail="point", budget=180, max_tris=600, flight=FLIGHT,
                bulk=1.1)


def raptor(name, main, breast, k=0.75):
    """A falcon or hawk for the hunter: barred breast, dark cap, hooked beak."""
    colors = {**P.shades("main", main), **P.palette(light=breast, tail=_darker(main), bill=0xE8C030, leg=0xE8C030,
                                                    eye=0x151012, cap=_darker(main))}

    def coat(u, n):
        base = hen_coat(u, n)
        if u.z > 0.455 and u.y > -0.15:
            return "cap"
        if base == "light" and math.floor(u.z * 40) % 2 == 0:
            return "main"                                    # Bars across the breast.
        return base

    return Fowl(name, colors, coat, k=k, neck_r=1.05, head=1.05, tail="point", clips=("attack",), flight=FLIGHT,
                budget=260, max_tris=900)


def dove(name, main, light):
    colors = {**P.shades("main", main), **P.palette(light=light, tail=_darker(main), bill=0xD88A80, leg=0xD86A6A,
                                                    eye=0x151012)}
    return Fowl(name, colors, hen_coat, k=0.5, head=0.95, tail="fan", flight=FLIGHT, budget=220, max_tris=800, bulk=1.1)


def owl(name, main, light):
    colors = {**P.shades("main", main), **P.palette(light=light, tail=_darker(main), bill=0xD8B84A, leg=0xC8B090,
                                                    eye=0xF2C230, disc=light)}

    def coat(u, n):
        if u.z > 0.42 and u.y < -0.12 and n.y < -0.3:
            return "disc"                                    # The pale face.
        return hen_coat(u, n)

    return Fowl(name, colors, coat, k=0.8, ly=0.85, head=1.7, neck_r=1.25, tail="point", flight=dict(FLIGHT, frames=16),
                budget=260, max_tris=900, bulk=1.15)


def seagull(name):
    colors = {**P.shades("main", 0xF4F2EC), **P.palette(wing=0x9AA2AC, tail=0x2A2A2E, bill=0xF0C02A, leg=0xF0A02A,
                                                        eye=0x151012)}

    def coat(u, n):
        if u.z > 0.3 and u.y > -0.02 and n.z > 0.2:
            return "wing"                                    # A gray back.
        return "main"

    return Fowl(name, colors, coat, k=0.62, ly=1.2, webbed=True, tail="point", wing_mat="wing", flight=FLIGHT,
                budget=240, max_tris=800)


def swan(name, main, bill):
    colors = {**P.shades("main", main), **P.palette(tail=main, bill=bill, leg=0x2A2A2E, eye=0x151012)}
    return Fowl(name, colors, plain, k=1.9, ly=1.35, lf=0.7, neck_up=0.26, neck_fwd=0.02, neck_r=0.62, head=0.8,
                bill="flat", webbed=True, tail="point", clips=("attack", "sit"), max_tris=1300, budget=340,
                flight=dict(frames=14, beats=1, pitch=-6.0, amp=46.0, mid=8.0, tuck=60.0, speed=7.0))


def _darker(c):
    return P._mix(c, 0x000000, 0.35)


def build(make, *args, **kw):
    return lambda: P.kit.build_zoo_spec(make(*args, **kw), P.FAMILY)


MODELS = {
    "animal_hen": build(hen, "animal_hen", 0xB5713A, 0xD8A468),
    "animal_hen_white": build(hen, "animal_hen_white", 0xF2EEE4, 0xFBF9F4),
    "animal_chick": build(chick, "animal_chick"),
    "animal_duck": build(duck, "animal_duck"),
    "animal_duck_white": build(duck, "animal_duck_white", mallard_colors=False),
    "animal_goose": build(goose, "animal_goose", 0xF4F1EA),
    "animal_goose_gray": build(goose, "animal_goose_gray", 0xA8A096, bill=0x2A2624, neck=0x3A3632),
    "pet_falcon": build(raptor, "pet_falcon", 0x6A5A4E, 0xF0E6D2),
    "pet_hawk": build(raptor, "pet_hawk", 0x8A5A32, 0xF2DCC0, k=0.9),
    "animal_dove": build(dove, "animal_dove", 0xF2EFE8, 0xFFFFFF),
    "animal_pigeon": build(dove, "animal_pigeon", 0x8A929E, 0xB8A0B8),
    "animal_owl": build(owl, "animal_owl", 0x8A6A4A, 0xE8DCC0),
    "animal_owl_snowy": build(owl, "animal_owl_snowy", 0xECEAE4, 0xFFFFFF),
    "animal_seagull": build(seagull, "animal_seagull"),
    "animal_swan": build(swan, "animal_swan", 0xF6F4EE, 0xF08A2A),
    "animal_swan_black": build(swan, "animal_swan_black", 0x26262C, 0xD8302A),
    "animal_crow": build(crow, "animal_crow"),
    "animal_raven": build(crow, "animal_raven", k=0.85),
    "animal_vulture": build(vulture, "animal_vulture"),
    "animal_sparrow": build(songbird, "animal_sparrow", 0x8A6A4A, 0xD8C8A8),
    "animal_robin": build(songbird, "animal_robin", 0x6A5A4A, 0xE8662A),
    "animal_bluebird": build(songbird, "animal_bluebird", 0x3F86C8, 0xF0E8D8),
}
