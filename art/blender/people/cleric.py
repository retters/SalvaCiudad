"""Cleric: a broad figure in a white hood with a gold helmet in its dark
opening, big layered gold-trimmed pauldrons, a white long coat with gold
borders, a red tabard with gold trim and two white star emblems, a brown
belt with a pouch, brown gloves and boots with gold trim, and a wooden
staff topped with a gold spiked mace head held in his left hand."""

import math

from mathutils import Vector

import common
import studies
from dark_elf_man import Figure, arc, sheet, solid


class Cleric(Figure):
    name = "cleric"
    height = 1.9
    # Measured on the reference: broad, in thick clothes.
    shoulder = 0.2
    hip = 0.105
    build = 1.15
    heel = 0.03
    raised_arm = True   # The left forearm bent forward to hold the staff (False: the arm hangs).
    colors = {
        "white": common.rgb(0xE6D6C8),
        "white_light": common.rgb(0xF1E3D5),
        "white_shade": common.rgb(0xD3C2B6),
        "inner": common.rgb(0xA8968C),     # The inside of the coat.
        "gold": common.rgb(0xE2A654),
        "red": common.rgb(0xB03338),
        "brown": common.rgb(0x6C4A3C),
        "dark": common.rgb(0x48332F),
        "shadow": common.rgb(0x241817),    # The opening of the hood.
    }
    tone_material = "white"
    tones = 0.45
    budget = 1100

    BOOT = 0.47
    MACE = 1.5    # Height of the center of the mace head.

    def __init__(self):
        super().__init__()
        k = self.k
        self.cuts = [(self.V(0, 0, self.BOOT), (0, 0, 1), lambda c, n: c.z < 0.6 * k)]

    def customize(self, parts):
        super().customize(parts)
        b = self.build
        j = self.joints()
        parts["cowl"] = self.ellipsoid((0, 0.01, 1.5), (0.165, 0.145, 0.07))
        for side, s in ((".L", 1), (".R", -1)):   # Wide sleeves on the upper arms.
            mid = [(a + c) * 0.5 for a, c in zip(j["shoulder"], j["elbow"])]
            parts["sleeve" + side] = self.ellipsoid((s * mid[0], mid[1], mid[2]), (0.076, 0.078, 0.14))
        e = Vector(j["elbow"])
        self.grip = Vector(j["hand"]) + Vector((0.0, -0.045, 0.0))
        if self.raised_arm:
            # The forearm turns forward at the elbow; the fist closes on the staff.
            d = Vector((0.1, -1.0, 0.04)).normalized()
            length = (Vector(j["wrist"]) - e).length
            parts["forearm.L"] = self.capsule(e, e + d * length, 0.048 * b, 0.042 * b)
            self.grip = e + d * (length + 0.055)
            parts["hand.L"] = self.ellipsoid(self.grip, (0.048, 0.055, 0.05))

    def paint(self, c, n):
        u = self.u(c)
        part = self.zone(c).split(".")[0]
        if part in ("head", "jaw", "neck"):
            return "shadow"
        if part in ("forearm", "hand"):
            return "brown"
        if part == "thigh":
            return "dark"
        if part in ("shin", "foot"):
            return "brown" if u.z < self.BOOT else "dark"
        return "white"

    # ------------------------------------------------------------ details

    def hood(self, mb):
        """The hood: an arched tunnel from the rim around the face to the
        back of the head, pointed at the top, its rim gold and its inside
        dark."""
        k = self.k
        profile = ((0.7, 0.0), (1.0, 0.32), (0.95, 0.62), (0.58, 0.9), (0.0, 1.0))  # (x, height) fractions.
        rows = []
        for y, w, low, top in ((-0.15, 0.095, 1.5, 1.83), (-0.07, 0.142, 1.48, 1.86), (0.05, 0.15, 1.47, 1.85),
                               (0.14, 0.12, 1.47, 1.77), (0.185, 0.06, 1.46, 1.62), (0.175, 0.012, 1.45, 1.5)):
            half = [(w * x, low + (top - low) * h) for x, h in profile]
            pts = [(-x, z) for x, z in half] + [(x, z) for x, z in reversed(half[:-1])]
            rows.append([self.V(x, y + (0.03 if x == 0 else 0.0), z) for x, z in pts])
        sheet(mb, rows, 0.016 * k, "white", back="shadow", trim="gold", top=0.03 * k, flip=True)

    def helmet(self, mb):
        """The gold helmet inside the hood: a brow, a ridge down to the
        nose guard and two cheek plates around a dark T-shaped slit."""
        H = self.H
        for s in (-1, 1):
            solid(mb, [H(s * 0.02, -0.122, -0.24), H(s * 0.02, -0.128, -0.14), H(s * 0.094, -0.07, -0.14),
                       H(s * 0.086, -0.07, -0.225), H(s * 0.02, -0.09, -0.24), H(s * 0.09, -0.03, -0.18)], "gold")
        solid(mb, [H(-0.096, -0.07, -0.1), H(0.096, -0.07, -0.1), H(0, -0.13, -0.105), H(-0.09, -0.06, -0.005),
                   H(0.09, -0.06, -0.005), H(0, -0.136, 0.01), H(0, -0.04, 0.02)], "gold")
        solid(mb, [H(-0.014, -0.128, -0.09), H(0.014, -0.128, -0.09), H(0, -0.158, -0.1), H(0, -0.15, 0.025),
                   H(0, -0.14, -0.19), H(0, -0.1, -0.15), H(-0.01, -0.125, 0.0), H(0.01, -0.125, 0.0)], "gold")

    def yoke(self, mb):
        """The collar of the hood on the chest: white with a gold edge that
        dips to a point at the front."""
        k = self.k
        angles = arc(-90, 270, 13)
        dip = [0.085 * max(0.0, -math.sin(a)) ** 3 for a in angles]
        rows = [[self.V(0.12 * math.cos(a), 0.01 + 0.105 * math.sin(a), 1.52) for a in angles],
                [self.V(0.185 * math.cos(a), 0.01 + (0.15 if math.sin(a) < 0 else 0.16) * math.sin(a), 1.465 - d)
                 for a, d in zip(angles, dip)]]
        sheet(mb, rows, 0.014 * k, "white", back="inner", trim="gold", hem=0.03 * k)

    def pauldrons(self, mb):
        """Two layers over each shoulder: a big gold plate standing over
        it, and a white plate with a gold edge down the upper arm."""
        k = self.k
        s0 = self.shoulder
        for s in (-1, 1):
            solid(mb, [self.V(s * (s0 - 0.085), 0.0, 1.6), self.V(s * (s0 - 0.095), -0.125, 1.52),
                       self.V(s * (s0 - 0.095), 0.13, 1.52), self.V(s * (s0 + 0.01), 0.0, 1.64),
                       self.V(s * (s0 + 0.09), -0.135, 1.5), self.V(s * (s0 + 0.11), 0.0, 1.55),
                       self.V(s * (s0 + 0.09), 0.14, 1.5), self.V(s * (s0 + 0.0), -0.155, 1.5),
                       self.V(s * (s0 + 0.0), 0.16, 1.5), self.V(s * (s0 + 0.085), 0.0, 1.45)], "gold")
            for top, low, r0, r1, point in ((1.52, 1.33, 0.1, 0.128, 0.05),):
                rows = []
                for z, r in ((top, r0), (low, r1)):
                    cx = s0 + 0.05 * (1.45 - z) / 0.28
                    rows.append([self.V(s * (cx + r * math.cos(a)), r * 1.1 * math.sin(a), z)
                                 for a in arc(-115, 115, 5)])
                rows[1][2].z -= point * k   # The edge comes to a point at the outside.
                rows[1][2].x += s * 0.02 * k
                sheet(mb, rows, 0.02 * k, "white", back="inner", trim="gold", hem=0.035 * k, flip=s < 0)

    def emblem(self, mb, z, y):
        """A white four-pointed star with a gold center, on the tabard."""
        k = self.k
        c = Vector((0, y - 0.006 * k, z * k))
        for w, up, down in ((0.014, 0.075, 0.1), (0.05, 0.013, 0.013)):
            studies.plate(mb, [c + Vector((0, 0, up * k)), c + Vector((-w * k, 0, 0)), c + Vector((0, 0, -down * k)),
                               c + Vector((w * k, 0, 0))], 0.006 * k, "white")
        studies.plate(mb, [c + Vector((x * k, -0.004 * k, zz * k)) for x, zz in ((0, 0.02), (-0.02, 0), (0, -0.02),
                                                                             (0.02, 0))], 0.006 * k, "gold")

    def staff(self, mb):
        """The staff stands through his left fist; the mace head on top."""
        k = self.k
        g = self.grip
        top = self.V(g.x + 0.02, g.y, self.MACE)
        mb.cylinder(self.V(g.x - 0.07, g.y + 0.01, 0.0), top, 0.02 * k, 0.018 * k, "brown", segments=6)
        neck = top - self.V(0.006, 0, 0.1)
        mb.cylinder(neck - self.V(0.004, 0, 0.07), neck, 0.028 * k, 0.036 * k, "gold", segments=6)
        mb.sphere(top, 0.062 * k, "gold", segments=6, rings=4, scale=(1, 1, 1.2))
        spikes = [(Vector((0, 0, 1)), 0.2, 0.04)]
        for i in range(4):
            a = math.radians(45 + 90 * i)
            spikes.append((Vector((math.cos(a), math.sin(a), 0.0)), 0.085, 0.034))
            a += math.radians(45)
            spikes.append((Vector((math.cos(a), math.sin(a), 0.9)).normalized(), 0.085, 0.034))
            spikes.append((Vector((math.cos(a), math.sin(a), -0.9)).normalized(), 0.07, 0.03))
        for d, length, r in spikes:
            mb.cylinder(top + d * 0.04 * k, top + d * (0.05 + length) * k, r * k, 0.0, "gold", segments=4)

    def details(self, mb):
        k = self.k
        self.hood(mb)
        self.helmet(mb)
        self.yoke(mb)
        self.pauldrons(mb)
        # The tabard: red with a gold border, down to a point.
        xs = (-0.09, 0.0, 0.09)
        tabard = [[self.front(x, z, 0.02) for x in xs] for z in (1.4, 1.3, 1.2, 1.1, 0.97)]
        y = tabard[-1][1].y
        tabard.append([Vector((x * k, y - 0.01 * k, 0.6 * k)) for x in xs])
        tabard.append([Vector((x * k, y - 0.012 * k, z * k)) for x, z in zip(xs, (0.48, 0.39, 0.48))])
        sheet(mb, tabard, 0.012 * k, "red", back="inner", trim="gold", hem=0.04 * k, sides=0.032 * k)
        self.emblem(mb, 1.3, self.front(0, 1.3, 0.026).y)
        self.emblem(mb, 0.84, y - 0.014 * k)
        # The belt and its pouch on his right hip.
        self.ring(mb, 1.11, 0.058, 0.028, "brown")
        p = self.around(1.05, [math.radians(222)], 0.045)[0]
        mb.box(p, (0.08 * k, 0.065 * k, 0.12 * k), "brown", rotation_z=math.radians(40))
        mb.box(p + Vector((-0.01 * k, -0.01 * k, 0.035 * k)), (0.085 * k, 0.07 * k, 0.05 * k), "dark",
               rotation_z=math.radians(40))
        # The skirt of the coat, open at the front, and its longer back layer.
        angles = arc(0, 1, 9)
        coat = self.skirt_rows([(1.1, 0.18, 0.135, 0.0, -80, 260), (0.96, 0.225, 0.17, 0.0, -73, 253),
                                (0.64, 0.295, 0.23, 0.02, -61, 241), (0.36, 0.335, 0.265, 0.03, -53, 233)], angles)
        sheet(mb, coat, 0.014 * k, "white", back="inner", trim="gold", hem=0.055 * k, sides=0.03 * k)
        back = self.skirt_rows([(0.6, 0.265, 0.2, 0.02), (0.21, 0.295, 0.235, 0.03)], arc(-10, 190, 6), jag=0.04)
        sheet(mb, back, 0.012 * k, "inner", trim="gold", hem=0.04 * k)
        for side, s in ((".L", 1), (".R", -1)):
            # Bracers: gold ends around a brown band.
            self.cuff(mb, "forearm" + side, 0.14, 0.34, 0.013, "gold")
            self.cuff(mb, "forearm" + side, 0.34, 0.72, 0.007, "brown")
            self.cuff(mb, "forearm" + side, 0.72, 0.9, 0.011, "gold")
            # Gold bands at the knee, with a point, and around the ankle.
            self.cuff(mb, "shin" + side, 0.0, 0.12, 0.011, "gold")
            self.knee_guard(mb, s, "gold", 0.75)
            self.cuff(mb, "shin" + side, 0.74, 0.87, 0.013, "gold")
        self.heels(mb, "brown", width=0.07)
        self.staff(mb)


SPECS = [Cleric()]
