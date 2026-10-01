"""Catfolk: a grey-blue cat person with pink inner ears, yellow-green eyes,
a white muzzle and whiskers; a blue cowl and tabard over a dark shirt, a
chest strap with a pouch, a belt with pouches, bracers, dark hands with
white fingertips, a long tail and tall boots open at the toes."""

from mathutils import Vector

import common
import rigs
import studies
from adventurer_man import SIDES, Adventurer, Surface, buckle, chunk, pouch, spike, strap

TAIL = [((0, 0.09, 1.0), 0.05), ((-0.08, 0.21, 0.9), 0.05), ((-0.18, 0.33, 0.68), 0.048),
        ((-0.24, 0.38, 0.47), 0.046), ((-0.23, 0.35, 0.3), 0.04)]


class Catfolk(Adventurer):
    name = "catfolk"
    height = 1.67
    shoulder = 0.165
    build = 0.9
    colors = {
        "fur": common.rgb(0x666D90),
        "white": common.rgb(0xF0E2DA),
        "dark": common.rgb(0x383750),
        "blue": common.rgb(0x3F68D6),
        "blue_light": common.rgb(0x5580EA),
        "blue_shade": common.rgb(0x2B4BA8),
        "leather": common.rgb(0x7E4332),
        "leather_dark": common.rgb(0x55302A),
        "yellow": common.rgb(0xE8D23E),
        "pink": common.rgb(0xE08C92),
        "eye": common.rgb(0x1A1414),
    }
    tone_material = "blue"
    tones = 0.2
    TABARD = 0.095   # Half width of the tabard on the chest (1.8 m body).
    BELT = 1.105
    BOOT = 0.455
    FINGERS = 0.8

    def __init__(self):
        super().__init__()
        k = self.k
        torso = self.in_zone(("chest", "waist", "hips"))
        self.cuts = self.cuts + [
            ((0, 0, self.FINGERS * k), (0, 0, 1), self.in_zone("hand")),
            ((self.TABARD * k, 0, 0), (1, 0, 0), torso),
            ((-self.TABARD * k, 0, 0), (1, 0, 0), torso),
            ((0, 0, self.BELT * k), (0, 0, 1), torso),
            ((0, 0, 1.68 * k), (0, 0.5, 1), self.in_zone("muzzle")),
            ((0, 0, 0.125 * k), (0, 0, 1), lambda c, n: c.z < 0.3 * k and c.y < 0.2 * k),
        ]

    def extra_bones(self):
        ears = [rigs.Bone("ear" + side, self.P(s * 0.08, 0.0, 1.76), self.P(s * 0.125, 0.0, 1.94), parent="head")
                for side, s in SIDES]
        return self.chain_bones("tail", [p for p, _ in TAIL], "hips") + ears

    def customize(self, parts):
        del parts["jaw"]
        parts["head"] = self.ellipsoid((0, -0.005, 1.695), (0.145, 0.13, 0.108))
        parts["muzzle"] = self.ellipsoid((0, -0.115, 1.645), (0.064, 0.052, 0.048))
        parts["neck"] = self.capsule((0, 0.005, 1.49), (0, -0.005, 1.62), 0.045, 0.045)
        for side, x in SIDES:
            parts["cheek" + side] = self.ellipsoid((x * 0.092, -0.04, 1.64), (0.062, 0.066, 0.048))
        self.cowl(parts, "blue_shade", top=1.54, bottom=1.445, r_top=(0.15, 0.112), r_bottom=(0.178, 0.138), rim=1.54,
                  tilt=0.5, back=0.045, drape=((0, -0.115, 1.42), (0.09, 0.035, 0.07)))
        self.sleeves(parts, "dark", length=0.78, r0=0.06, r1=0.066)
        self.bracers(parts, "white", r=0.05, top=0.4)
        self.boots(parts, "dark", top=self.BOOT, cuff=0.086, cuff_height=0.09, shaft=0.046, toe=0.13, foot=1.05)
        for i, ((a, ra), (c, rc)) in enumerate(zip(TAIL, TAIL[1:])):
            parts[f"tail{i}"] = self.capsule(a, c, ra, rc)

    def paint(self, c, n):
        k = self.k
        z = c.z / k
        zone = self.painted_zone(c)
        if zone == "muzzle":
            return "white" if z + 0.5 * c.y / k < 1.68 else "fur"
        if zone == "neck":
            return "white" if c.y < 0.02 * k else "fur"
        if zone.startswith("cowl"):
            return "blue"
        if zone.startswith(("chest", "waist", "hips")):
            return "blue" if abs(c.x) < self.TABARD * k and z > self.BELT else "dark"
        if zone.startswith(("sleeve", "shoulder", "thigh")):
            return "dark"
        if zone.startswith(("upper_arm", "forearm")):
            return "white"
        if zone.startswith("hand"):
            return "dark" if z > self.FINGERS else "white"
        if zone.startswith(("bracer", "cuff")):
            return "leather"
        if zone.startswith(("shin", "fold")):
            if z < 0.125:
                return "fur"
            return "leather" if z < self.BOOT else "dark"
        return "fur"  # Head, cheeks, feet and tail.

    def head_details(self, mb, surf):
        k = self.k

        def P(x, y, z):
            return Vector(self.P(x, y, z))
        for s in (-1, 1):
            # Ears: a faceted cone of fur, pink inside.
            self.mark(mb, "ear.L" if s > 0 else "ear.R")
            chunk(mb, [P(s * 0.03, -0.02, 1.78), P(s * 0.135, -0.01, 1.73), P(s * 0.08, 0.06, 1.755),
                       P(s * 0.125, 0.0, 1.94)], "fur")
            studies.flap(mb, P(s * 0.052, -0.03, 1.788), P(s * 0.12, -0.022, 1.754), P(s * 0.116, -0.012, 1.9),
                         0.012 * k, "pink")
            # Eyes: big yellow almonds with a dark slit, under a brow.
            self.mark(mb, "head")
            p = surf.onto(P(s * 0.064, 0, 1.71), (0, 1, 0))
            chunk(mb, [p + Vector(q) * k for q in ((s * 0.036, 0.008, 0.012), (-s * 0.032, 0, -0.01), (0, 0, 0.022),
                                                   (0, 0, -0.018), (0, -0.01, 0.002), (0, 0.02, 0))], "yellow")
            chunk(mb, [p + Vector(q) * k for q in ((-s * 0.004, -0.004, 0.02), (-s * 0.004, -0.004, -0.016),
                                                   (0.009 - s * 0.004, -0.004, 0.002), (-0.009 - s * 0.004, -0.004, 0.002),
                                                   (-s * 0.004, -0.016, 0.002))], "eye")
            chunk(mb, [p + Vector(q) * k for q in ((-s * 0.04, -0.014, 0.016), (-s * 0.04, -0.012, 0.03),
                                                   (s * 0.04, 0.002, 0.03), (s * 0.04, 0.004, 0.04),
                                                   (-s * 0.04, 0.02, 0.024), (s * 0.04, 0.024, 0.034))], "fur")
            # Whiskers.
            root = surf.out(P(0, -0.115, 1.642), (s, -0.25, 0))
            for dz in (0.03, 0.0, -0.03):
                tip = root + Vector((s * 0.1, -0.02, dz)) * k
                studies.flap(mb, root + Vector((0, 0, 0.005 * k)), root - Vector((0, 0, 0.005 * k)), tip, 0.006 * k,
                             "white")
            # Cheek tufts.
            spike(mb, P(s * 0.115, -0.02, 1.645), P(s * 0.19, 0.03, 1.595), 0.04 * k, "fur")
        nose = surf.onto(P(0, 0, 1.67), (0, 1, 0))
        chunk(mb, [nose + Vector(q) * k for q in ((0.016, 0.005, 0.007), (-0.016, 0.005, 0.007), (0, -0.01, 0.004),
                                                  (0, 0.004, -0.012))], "pink")

    def details(self, mb):
        k = self.k
        self.flatten(mb)
        surf = Surface(mb)

        def P(x, y, z):
            return Vector(self.P(x, y, z))
        self.head_details(mb, surf)
        self.mark(mb, None)
        self.thumbs(mb, "white", size=0.9)
        self.toes(mb, "white", length=0.035)
        self.mark(mb, "chest")
        # A leather pauldron on the right shoulder: angular plates.
        sh = Vector(self.parts["shoulder.R"][1])
        chunk(mb, [sh + Vector(q) * k for q in ((0.04, -0.06, 0.066), (0.04, 0.06, 0.066), (-0.04, -0.075, 0.062),
                                                (-0.04, 0.075, 0.062), (-0.088, -0.06, -0.01), (-0.088, 0.06, -0.01),
                                                (-0.08, 0.0, -0.075), (-0.02, -0.08, -0.02), (-0.02, 0.08, -0.02))],
              "leather")

        def under_cowl(p):
            return self.zone(p).startswith("cowl")
        # The chest strap from the left shoulder to the right hip, with a
        # buckle and a pouch on it.
        self.mark(mb, self.trunk)
        strap(mb, surf, P(0, 0, 1.27), (-0.74, 0, 0.68), 0.045 * k, "leather", thick=0.01, skip=under_cowl)
        p = surf.onto(P(0.07, 0, 1.345), (0, 1, 0))
        self.mark(mb, "chest")
        mb.box(p + Vector((0, -0.014 * k, 0)), (0.06 * k, 0.02 * k, 0.045 * k), "yellow")
        p = surf.onto(P(-0.055, 0, 1.22), (0, 1, 0))
        self.mark(mb, "spine")
        pouch(mb, p + Vector((0, -0.03 * k, 0)), (0.1 * k, 0.05 * k, 0.085 * k), (-0.2, -1), "leather", "leather_dark")
        # The belt, a second one slanting, the buckle and the hip pouches.
        self.mark(mb, self.trunk)
        strap(mb, surf, P(0, 0, self.BELT), (0, 0, 1), 0.06 * k, "leather", thick=0.012)
        strap(mb, surf, P(0, 0, self.BELT - 0.06), (0.3, 0, 1), 0.04 * k, "leather", thick=0.01)
        front = surf.onto(P(0.02, 0, self.BELT), (0, 1, 0))
        self.mark(mb, "hips")
        buckle(mb, front + Vector((0, -0.018, 0)) * k, 0.08 * k, "yellow", "leather_dark")
        for z, size, out, clasp in ((1.01, (0.16, 0.08, 0.18), (-1, -0.7), "yellow"),
                                    (1.05, (0.075, 0.045, 0.09), (1, -0.25), None)):
            o = Vector((out[0], out[1], 0)).normalized()
            p = surf.out(P(0, 0, z), o)
            pouch(mb, p + o * size[1] * 0.4 * k, tuple(v * k for v in size), o, "leather", "leather_dark", clasp)
        # The tabard below the belt: two pointed panels in front, one behind.
        y = front.y - 0.01 * k
        top = (self.BELT - 0.02) * k
        self.mark(mb, self.drape(self.BELT, 0.67))
        for x0, x1, low in ((-0.16, -0.01, 0.67), (0.03, 0.115, 0.7)):
            tip = (x0 + x1) * 0.5 + (0.025 if x0 > 0 else -0.01)
            studies.plate(mb, [(x0 * k, y, top), (x1 * k, y, top),
                               (x1 * k, y - 0.03 * k, (low + 0.1) * k), (tip * k, y - 0.03 * k, low * k),
                               (x0 * k, y - 0.03 * k, (low + 0.06) * k)], 0.016 * k, "blue")
        back = surf.onto(P(0.07, 0, self.BELT), (0, -1, 0)).y + 0.01 * k
        studies.plate(mb, [(-0.11 * k, back, top), (0.11 * k, back, top),
                           (0.12 * k, back + 0.012 * k, 0.78 * k), (0, back + 0.014 * k, 0.7 * k),
                           (-0.12 * k, back + 0.012 * k, 0.78 * k)], 0.016 * k, "blue_shade")
        # Thigh straps.
        for side, s in SIDES:
            thigh = Vector(self.parts["thigh" + side][1]).lerp(Vector(self.parts["thigh" + side][2]), 0.7)
            self.mark(mb, "thigh" + side)
            strap(mb, surf, thigh, (0, 0, 1), 0.04 * k, "leather", thick=0.009, segments=8)


SPECS = [Catfolk()]
