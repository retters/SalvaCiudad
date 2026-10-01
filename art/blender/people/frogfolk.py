"""Frogfolk: a bright blue frog person with a wide head, big yellow eyes
and a pale green throat; long thin limbs with long fingers and toes, a tan
shawl over a blue top, a belt with a pouch and a tan loincloth."""

from mathutils import Vector

import common
import studies
from adventurer_man import SIDES, Adventurer, Surface, buckle, chunk, lerp, mirror, pouch, spike, strap


class Frogfolk(Adventurer):
    name = "frogfolk"
    height = 1.6
    shoulder = 0.15
    hip = 0.09
    build = 0.82
    colors = {
        "blue": common.rgb(0x2AB4F4),
        "blue_light": common.rgb(0x48C6FA),
        "blue_shade": common.rgb(0x1F9CE0),
        "top": common.rgb(0x2C66B6),
        "throat": common.rgb(0xDCDDAA),
        "tan": common.rgb(0xEFC89C),
        "leather": common.rgb(0x7E4633),
        "leather_dark": common.rgb(0x5A3330),
        "metal": common.rgb(0xA98F7C),
        "yellow": common.rgb(0xF2C820),
        "eye": common.rgb(0x1A1414),
    }
    tone_material = "blue"
    BELT = 1.095
    KNEE = 0.42   # The dark blue of the legs ends below the knees.
    MOUTH = 1.655

    def __init__(self):
        super().__init__()
        k = self.k
        self.cuts = self.cuts + [
            ((0, 0, self.KNEE * k), (0, 0, 1), self.in_zone(("shin", "knee"))),
            ((0, 0, self.MOUTH * k), (0, 0, 1), lambda c, n: c.z > 1.55 * k and c.y < 0.02 * k),
        ]

    def customize(self, parts):
        j = self.joints()
        del parts["jaw"]
        parts["head"] = self.ellipsoid((0, -0.01, 1.68), (0.18, 0.165, 0.1))
        parts["snout"] = self.ellipsoid((0, -0.14, 1.668), (0.125, 0.105, 0.062))
        parts["throat"] = self.ellipsoid((0, -0.055, 1.618), (0.148, 0.14, 0.06))
        parts["neck"] = self.capsule((0, 0.005, 1.47), (0, -0.01, 1.62), 0.042, 0.048)
        for side, x in SIDES:
            parts["eye" + side] = self.ellipsoid((x * 0.112, -0.05, 1.756), (0.068, 0.072, 0.06))
            parts["knee" + side] = self.ellipsoid(mirror(j["knee"], x), (0.068, 0.072, 0.074))
            parts["upper_arm" + side] = self.capsule(mirror(j["shoulder"], x), mirror(j["elbow"], x), 0.052, 0.046)
            parts["forearm" + side] = self.capsule(mirror(j["elbow"], x), mirror(j["wrist"], x), 0.046, 0.04)
            parts["thigh" + side] = self.capsule(mirror(j["hip"], x), mirror(j["knee"], x), 0.1, 0.06)
            parts["shin" + side] = self.capsule(mirror(j["knee"], x), mirror(j["ankle"], x), 0.058, 0.04)
            parts["hand" + side] = self.ellipsoid(mirror(j["hand"], x), (0.03, 0.045, 0.055))
            ankle = j["ankle"]
            parts["foot" + side] = self.capsule(mirror((ankle[0], 0.03, 0.045), x),
                                                mirror((ankle[0] + 0.01, -0.08, 0.04), x), 0.042, 0.048)
        # The shawl: a cone of cloth over the shoulders, open like a hood.
        self.cowl(parts, "leather_dark", top=1.555, bottom=1.39, r_top=(0.165, 0.125), r_bottom=(0.235, 0.155), rim=1.555,
                  tilt=0.55, back=0.06, drape=((0, -0.11, 1.36), (0.1, 0.035, 0.085)), name="shawl")

    def paint(self, c, n):
        k = self.k
        z = c.z / k
        zone = self.painted_zone(c)
        if zone.startswith("shawl"):
            return "tan"
        if zone in ("head", "snout", "throat"):
            return "throat" if z < self.MOUTH and c.y < 0.02 * k else "blue"
        if zone == "neck":
            return "throat" if c.y < 0.0 else "blue"
        if zone.startswith(("chest", "waist", "hips", "thigh")):
            return "top"
        if zone.startswith(("shin", "knee")):
            return "top" if z > self.KNEE else "blue"
        return "blue"

    def details(self, mb):
        k = self.k
        self.flatten(mb)
        surf = Surface(mb)

        def P(x, y, z):
            return Vector(self.P(x, y, z))
        j = self.joints()
        for s in (-1, 1):
            # Eyes: a yellow disk looking out and forward, with a slit pupil.
            c = P(s * 0.112, -0.05, 1.756)
            d = Vector((s * 0.72, -0.66, 0.2)).normalized()
            p = surf.out(c, d)
            mb.cylinder(p - d * 0.02 * k, p + d * 0.008 * k, 0.054 * k, 0.048 * k, "yellow", segments=7)
            side = d.cross(Vector((0, 0, 1))).normalized()
            up = side.cross(d)
            q = p + d * 0.009 * k
            chunk(mb, [q + up * 0.04 * k, q - up * 0.04 * k, q + side * 0.013 * k, q - side * 0.013 * k,
                       q + d * 0.006 * k, q - d * 0.01 * k], "eye")
            # Nostrils.
            mb.box(P(s * 0.032, -0.238, 1.692), (0.012 * k, 0.012 * k, 0.008 * k), "blue_shade")
            # Long fingers and a thumb.
            hand = Vector(self.parts["hand.L"][1])
            hand.x *= s
            for dy, length in ((-0.03, 0.095), (-0.004, 0.11), (0.022, 0.095)):
                a = hand + Vector((0, dy, -0.025)) * k
                spike(mb, a, a + Vector((s * 0.01, dy * 0.5 - 0.01, -length)) * k, 0.015 * k, "blue")
            spike(mb, hand + Vector((-s * 0.008, -0.03, 0.0)) * k, hand + Vector((-s * 0.03, -0.07, -0.055)) * k,
                  0.015 * k, "blue")
            # A yellow fin along the forearm, down to the wrist.
            a = Vector(self.P(*mirror(lerp(j["elbow"], j["wrist"], 0.35), s)))
            b = Vector(self.P(*mirror(lerp(j["elbow"], j["wrist"], 1.1), s)))
            out = Vector((s * 0.03, 0.045, 0)) * k
            studies.flap(mb, a + out * 0.6, b + out * 0.5, a.lerp(b, 0.6) + out * 1.6, 0.012 * k, "yellow")
            # Long toes.
            foot = Vector(self.parts["foot.L"][2])
            foot.x *= s
            for dx, length in ((-0.075, 0.13), (-0.025, 0.17), (0.03, 0.17), (0.085, 0.12)):
                a = Vector((foot.x + dx * 0.25 * k, foot.y + 0.02 * k, 0.03 * k))
                tip = Vector((foot.x + dx * 1.25 * k, foot.y - length * k, 0.004))
                mid = a.lerp(tip, 0.55) + Vector((0, 0, 0.012 * k))
                mb.cylinder(a, mid, 0.027 * k, 0.021 * k, "blue", segments=4)
                spike(mb, mid, tip, 0.021 * k, "blue_light")
        # The shawl's end hangs in front, on his left.
        p = surf.onto(P(0.05, 0, 1.3), (0, 1, 0)) + Vector((0, -0.012 * k, 0))
        studies.plate(mb, [p + Vector(q) * k for q in ((-0.06, 0, 0.03), (0.05, 0, 0.055), (0.07, 0.012, -0.07),
                                                       (0.04, 0.02, -0.17), (-0.01, 0.012, -0.09))], 0.018 * k, "tan")
        # Belt, buckle, a big pouch on the right hip and the loincloth.
        strap(mb, surf, P(0, 0, self.BELT), (0, 0, 1), 0.06 * k, "leather", thick=0.012, segments=12)
        strap(mb, surf, P(0, 0, self.BELT - 0.05), (0.3, 0, 1), 0.035 * k, "leather", thick=0.01, segments=12)
        front = surf.onto(P(0.015, 0, self.BELT), (0, 1, 0))
        buckle(mb, front + Vector((0, -0.018, 0)) * k, 0.085 * k, "metal", "leather_dark")
        o = Vector((-1, -0.55, 0)).normalized()
        p = surf.out(P(0, 0, 0.99), o)
        pouch(mb, p + o * 0.035 * k, (0.16 * k, 0.075 * k, 0.18 * k), o, "leather_dark", "leather", "yellow")
        y = front.y - 0.01 * k
        top = (self.BELT - 0.02) * k
        studies.plate(mb, [(-0.045 * k, y, top), (0.045 * k, y, top), (0.05 * k, y - 0.02 * k, 0.8 * k),
                           (0.02 * k, y - 0.025 * k, 0.675 * k), (-0.04 * k, y - 0.02 * k, 0.76 * k)],
                      0.016 * k, "tan")
        studies.plate(mb, [(-0.105 * k, y + 0.02 * k, top), (-0.04 * k, y + 0.012 * k, top),
                           (-0.045 * k, y + 0.0 * k, 0.74 * k), (-0.085 * k, y + 0.0 * k, 0.62 * k),
                           (-0.115 * k, y + 0.01 * k, 0.74 * k)], 0.014 * k, "tan")
        back = surf.onto(P(0, 0, self.BELT - 0.02), (0, -1, 0)).y + 0.012 * k
        studies.plate(mb, [(-0.075 * k, back, top), (0.075 * k, back, top), (0.08 * k, back + 0.02 * k, 0.78 * k),
                           (0, back + 0.025 * k, 0.66 * k), (-0.08 * k, back + 0.02 * k, 0.78 * k)],
                      0.016 * k, "tan")


SPECS = [Frogfolk()]
