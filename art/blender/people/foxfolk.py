"""Foxfolk: an orange fox person with white cheeks and muzzle, a black
nose and big ears, pink inside; a teal cowl over a green and teal tunic, a
chest strap, a belt, bracers, olive trousers gathered over short leather
wraps, cream paws and a bushy tail with a cream tip."""

from mathutils import Vector

import common
import rigs
import studies
from adventurer_man import SIDES, Adventurer, Surface, buckle, chunk, mirror, pouch, spike, strap

TAIL = [((0, 0.09, 0.98), 0.045), ((-0.07, 0.2, 0.82), 0.07), ((-0.14, 0.3, 0.66), 0.105),
        ((-0.2, 0.35, 0.62), 0.095), ((-0.245, 0.37, 0.72), 0.055), ((-0.26, 0.375, 0.82), 0.02)]


class Foxfolk(Adventurer):
    name = "foxfolk"
    height = 1.67
    shoulder = 0.185
    build = 1.06
    tones = 0.0
    colors = {
        "fur": common.rgb(0xEE8C42),
        "cream": common.rgb(0xF6DDBE),
        "pink": common.rgb(0xD0705E),
        "eye": common.rgb(0x2A2222),
        "teal": common.rgb(0x4F8B88),
        "teal_dark": common.rgb(0x33696C),
        "green": common.rgb(0x66764E),
        "olive": common.rgb(0x4B4B3F),
        "tan": common.rgb(0x9A7650),
        "leather": common.rgb(0x7C4432),
        "leather_dark": common.rgb(0x55302A),
        "gold": common.rgb(0xF0B048),
    }
    PANEL = 0.085    # Half width of the teal panel of the tunic (1.8 m body).
    BELT = 1.025
    HEM = 0.81       # The tunic's hem.
    CUFF = 0.45      # The top of the trousers' gathered ends.
    WRAP = 0.37      # The top of the leather wraps.
    FINGERS = 0.8

    def __init__(self):
        super().__init__()
        k = self.k
        torso = self.in_zone(("chest", "waist", "hips", "skirt"))
        t = self.tail_tip()
        legs = self.in_zone(("shin", "gather", "thigh"))
        self.cuts = self.cuts + [
            ((0, 0, self.FINGERS * k), (0, 0, 1), self.in_zone("hand")),
            ((self.PANEL * k, 0, 0), (1, 0, 0), torso),
            ((-self.PANEL * k, 0, 0), (1, 0, 0), torso),
            ((0, 0, (self.HEM + 0.07) * k), (0, 0, 1), self.in_zone("skirt")),
            ((0, 0, self.WRAP * k), (0, 0, 1), legs),
            ((0, 0, self.CUFF * k), (0, 0, 1), legs),
            ((0, -0.055 * k, 0), (0, 1, 0), self.in_zone("foot")),
            (t[0], t[1], self.in_zone("tail")),
            ((0, 0, 1.69 * k), (0, 0, 1), lambda c, n: self.zone(c) in ("muzzle", "head") and c.y < -0.03 * k),
            ((0, 0, 1.15 * k), (0, 0, 1), self.in_zone(("upper_arm", "forearm"))),
        ]

    def tail_tip(self):
        """The plane beyond which the tail is cream: (point, direction)."""
        a, b = Vector(self.P(*TAIL[2][0])), Vector(self.P(*TAIL[3][0]))
        return a.lerp(b, 0.5), (b - a + Vector((0, 0, -0.05))).normalized()

    skirt_span = (1.045, 0.81)

    def extra_bones(self):
        ears = [rigs.Bone("ear" + side, self.P(s * 0.08, 0.02, 1.765), self.P(s * 0.122, 0.02, 1.935), parent="head")
                for side, s in SIDES]
        return self.chain_bones("tail", [p for p, _ in TAIL], "hips") + ears

    def customize(self, parts):
        j, b = self.joints(), self.build
        del parts["jaw"]
        parts["head"] = self.ellipsoid((0, 0.01, 1.695), (0.146, 0.146, 0.108))
        parts["muzzle"] = self.capsule((0, -0.09, 1.668), (0, -0.265, 1.655), 0.07, 0.038)
        parts["neck"] = self.capsule((0, 0.005, 1.49), (0, 0.0, 1.62), 0.052, 0.052)
        for side, x in SIDES:
            parts["cheek" + side] = self.ellipsoid((x * 0.094, -0.02, 1.64), (0.072, 0.082, 0.054))
            parts["thigh" + side] = self.capsule(mirror(j["hip"], x), mirror(j["knee"], x), 0.098 * b, 0.082 * b)
        self.cowl(parts, "olive", back=0.045, top=1.54, bottom=1.445, r_top=(0.155, 0.115), r_bottom=(0.188, 0.142), rim=1.54,
                  tilt=0.6, drape=((0, -0.12, 1.425), (0.095, 0.035, 0.075)))
        self.sleeves(parts, "olive", length=0.74, r0=0.068, r1=0.084)
        self.skirt(parts, self.BELT + 0.04, self.HEM, (0.17, 0.128), (0.205, 0.15), "olive")
        self.bracers(parts, "fur", r=0.055, top=0.42, flare=1.1)
        self.boots(parts, "olive", top=self.CUFF, cuff=0, shaft=0.042, toe=0.13, foot=1.1, knee=0.074)
        for side, x in SIDES:  # Baggy trousers gathered below the knee.
            self.ended(parts, "gather" + side, self.shin_point(self.CUFF + 0.04, x), self.shin_point(self.WRAP, x),
                       0.078 * b, 0.068 * b, 0.05 * b, "leather_dark", reach=0.02)
        for i, ((a, ra), (c, rc)) in enumerate(zip(TAIL, TAIL[1:])):
            parts[f"tail{i}"] = self.capsule(a, c, ra, rc)

    def paint(self, c, n):
        k = self.k
        z = c.z / k
        zone = self.painted_zone(c)
        if zone.startswith("tail"):
            p, d = self.tail_tip()
            return "cream" if (c - p).dot(d) > 0 else "fur"
        if zone.startswith("cheek"):
            return "cream"
        if zone in ("muzzle", "head"):
            return "cream" if z < 1.69 and c.y < -0.03 * k else "fur"
        if zone == "neck":
            return "cream" if c.y < 0.02 * k else "fur"
        if zone.startswith("cowl"):
            return "teal_dark"
        if zone.startswith(("chest", "waist", "hips", "skirt")) or (zone.startswith("thigh") and z > self.HEM):
            if abs(c.x) < self.PANEL * k and z > self.BELT:
                return "teal"
            return "tan" if z < self.HEM + 0.07 else "green"
        if zone.startswith(("sleeve", "shoulder")):
            return "green"
        if zone.startswith(("upper_arm", "forearm")):
            return "cream" if z > 1.15 else "fur"
        if zone.startswith("bracer"):
            return "leather_dark"
        if zone.startswith("hand"):
            return "leather_dark" if z > self.FINGERS else "fur"
        if zone.startswith("foot"):
            return "cream" if c.y < -0.055 * k else "leather"
        if zone.startswith("fold"):
            return "leather"
        if zone.startswith(("gather", "shin")):
            if z > self.CUFF:
                return "olive"
            return "tan" if z > self.WRAP else "leather"
        if zone.startswith("thigh"):
            return "olive"
        return "fur"

    def head_details(self, mb, surf):
        k = self.k

        def P(x, y, z):
            return Vector(self.P(x, y, z))
        for s in (-1, 1):
            # Ears: big faceted cones, pink inside.
            self.mark(mb, "ear.L" if s > 0 else "ear.R")
            chunk(mb, [P(s * 0.03, 0.0, 1.785), P(s * 0.136, 0.01, 1.735), P(s * 0.08, 0.08, 1.755),
                       P(s * 0.122, 0.02, 1.935)], "fur")
            studies.flap(mb, P(s * 0.05, -0.012, 1.792), P(s * 0.12, -0.004, 1.76), P(s * 0.114, 0.006, 1.895),
                         0.012 * k, "pink")
            # Dark eyes under slanted brows.
            self.mark(mb, "head")
            p = surf.onto(P(s * 0.07, 0, 1.72), (0, 1, 0))
            chunk(mb, [p + Vector(q) * k for q in ((s * 0.03, 0.006, 0.01), (-s * 0.026, 0, -0.007), (0, 0, 0.018),
                                                   (0, 0, -0.014), (0, -0.01, 0.0), (0, 0.02, 0))], "eye")
            chunk(mb, [p + Vector(q) * k for q in ((-s * 0.036, -0.014, 0.014), (-s * 0.036, -0.012, 0.028),
                                                   (s * 0.038, 0.002, 0.028), (s * 0.038, 0.004, 0.038),
                                                   (-s * 0.036, 0.02, 0.022), (s * 0.038, 0.024, 0.032))], "fur")
            # Cheek ruffs.
            spike(mb, P(s * 0.125, 0.0, 1.64), P(s * 0.195, 0.05, 1.59), 0.044 * k, "cream")
        tip = Vector(self.parts["muzzle"][2])
        nose = tip + Vector((0, -0.026, 0.018)) * k
        chunk(mb, [nose + Vector(q) * k for q in ((0.02, 0.012, 0.01), (-0.02, 0.012, 0.01), (0, -0.014, 0.005),
                                                  (0, 0.012, -0.018), (0, 0.02, 0.014))], "eye")

    def details(self, mb):
        k = self.k
        self.flatten(mb)
        surf = Surface(mb)

        def P(x, y, z):
            return Vector(self.P(x, y, z))
        self.head_details(mb, surf)
        self.mark(mb, None)
        self.thumbs(mb, "fur")
        self.toes(mb, "cream", spread=0.034, length=0.035)

        def under_cowl(p):
            return self.zone(p).startswith("cowl")
        # The chest strap from the left shoulder to the right hip, with a
        # gold clasp, the belt, its buckle and a slanting second belt.
        self.mark(mb, self.trunk)
        strap(mb, surf, P(0, 0, 1.24), (-0.74, 0, 0.68), 0.05 * k, "leather", thick=0.01, skip=under_cowl)
        self.mark(mb, "chest")
        p = surf.onto(P(0.105, 0, 1.385), (0, 1, 0)) + Vector((0, -0.01 * k, 0))
        chunk(mb, [p + Vector(q) * k for q in ((0.01, 0, 0.045), (-0.01, 0, -0.045), (0.034, 0, -0.007),
                                               (-0.034, 0, 0.007), (0, -0.02, 0), (0, 0.02, 0))], "gold")
        self.mark(mb, "hips")
        strap(mb, surf, P(0, 0, self.BELT), (0, 0, 1), 0.075 * k, "leather", thick=0.013, segments=14)
        strap(mb, surf, P(0, 0, self.BELT - 0.065), (-0.3, 0, 1), 0.04 * k, "leather", thick=0.01, segments=14)
        front = surf.onto(P(0.02, 0, self.BELT), (0, 1, 0))
        buckle(mb, front + Vector((0, -0.02, 0)) * k, 0.095 * k, "tan", "leather_dark")
        o = Vector((1, -0.35, 0)).normalized()
        p = surf.out(P(0, 0, 0.96), o)
        pouch(mb, p + o * 0.02 * k, (0.085 * k, 0.045 * k, 0.1 * k), o, "leather", "leather_dark")
        # The teal panel hanging in front, below the belt.
        y = front.y - 0.012 * k
        self.mark(mb, self.drape(self.BELT, 0.72))
        studies.plate(mb, [(-0.075 * k, y, self.BELT * k), (0.075 * k, y, self.BELT * k),
                           (0.085 * k, y - 0.03 * k, 0.8 * k), (0.03 * k, y - 0.03 * k, 0.72 * k),
                           (-0.08 * k, y - 0.03 * k, 0.78 * k)], 0.016 * k, "teal")


SPECS = [Foxfolk()]
