"""Adventurer (woman): auburn hair in a high ponytail, a red scarf, a dark
red crop top under a leather harness, belts with pouches on the hips and a
thigh strap, bracers, fingerless gloves, dark leggings and tall boots."""

from mathutils import Vector

import common
from adventurer_man import SIDES, Adventurer, Surface, buckle, chunk, hair_cap, mirror, pouch, spike, strap, tube


class AdventurerWoman(Adventurer):
    name = "adventurer_woman"
    female = True
    height = 1.72
    head_size = 1.0
    shoulder = 0.152
    build = 0.9
    colors = {
        "skin": common.rgb(0xEFA878),
        "skin_light": common.rgb(0xF8BC8C),
        "skin_shade": common.rgb(0xE29868),
        "scarf": common.rgb(0xD23A40),
        "top": common.rgb(0x842838),
        "leggings": common.rgb(0x433E52),
        "leather": common.rgb(0x8A4A33),
        "leather_dark": common.rgb(0x55302A),
        "hair": common.rgb(0x86402A),
        "gold": common.rgb(0xE9A63E),
        "metal": common.rgb(0x9A8474),
        "eye": common.rgb(0x1A1414),
    }
    tone_material = "skin"
    tones = 0.2
    TOP = (1.22, 1.26)   # The crop top: hem and top of its dark band (1.8 m body).
    BELT = 1.065
    BOOT = 0.41
    FINGERS = 0.8

    def __init__(self):
        super().__init__()
        k = self.k
        torso = self.in_zone(("chest", "bust", "waist", "hips"))
        self.cuts = self.cuts + [
            ((0, 0, self.FINGERS * k), (0, 0, 1), self.in_zone("hand")),
            ((0, 0, self.TOP[0] * k), (0, 0, 1), torso),
            ((0, 0, self.TOP[1] * k), (0, 0, 1), torso),
            ((0, 0, (self.BELT - 0.02) * k), (0, 0, 1), torso),
            # The neckline, a V in front.
            ((0, 0, 1.345 * k), (0.9, 0, -1), lambda c, n: torso(c) and c.y < 0 and c.x > 0),
            ((0, 0, 1.345 * k), (-0.9, 0, -1), lambda c, n: torso(c) and c.y < 0 and c.x < 0),
        ]

    PONYTAIL = [(0, 0.085, 1.765), (0, 0.2, 1.72), (0, 0.225, 1.47)]

    def extra_bones(self):
        return self.chain_bones("ponytail", self.PONYTAIL, "head")

    def customize(self, parts):
        j, b = self.joints(), self.build
        self.angular_jaw(parts)
        self.cowl(parts, "top", top=1.545, bottom=1.465, r_top=(0.12, 0.095), r_bottom=(0.148, 0.118), rim=1.545,
                  tilt=0.5, back=0.05, drape=((0, -0.1, 1.455), (0.07, 0.03, 0.045)), name="scarf")
        parts["hips"] = self.ellipsoid((0, 0.005, 0.96), (0.18, 0.115, 0.13))
        for side, x in SIDES:
            parts["thigh" + side] = self.capsule(mirror(j["hip"], x), mirror(j["knee"], x), 0.09, 0.056)
        self.bracers(parts, "skin", r=0.045, top=0.22, flare=1.1)
        self.boots(parts, "leggings", top=self.BOOT, cuff=0.088, cuff_height=0.09, shaft=0.05, toe=0.145, knee=0.062)

    def paint(self, c, n):
        k = self.k
        z = c.z / k
        zone = self.painted_zone(c)
        if zone.startswith("scarf"):
            return "scarf"
        if zone.startswith(("chest", "bust", "waist", "hips")):
            if z < self.BELT - 0.02:
                return "leggings"
            if z < self.TOP[0]:
                return "skin"
            if z < self.TOP[1]:
                return "leather_dark"
            if c.y < 0 and z > 1.345 + 0.9 * abs(c.x) / k:
                return "skin"
            return "top"
        if zone.startswith("bracer"):
            return "leather"
        if zone.startswith("hand"):
            return "leather_dark" if z > self.FINGERS else "skin"
        if zone.startswith(("cuff", "fold", "foot")):
            return "leather"
        if zone.startswith("shin"):
            return "leather" if z < self.BOOT else "leggings"
        if zone.startswith("thigh"):
            return "leggings"
        return "skin"

    def hair(self, mb):
        k = self.k
        head = Vector(self.parts["head"][1])
        r = self.parts["head"][2]

        def at(x, y, z):
            return head + Vector((x * r[0], y * r[1], z * r[2]))

        def keep(d):
            return d.z > (0.15 - 0.5 * d.y if d.y < 0 else max(-0.6, 0.15 - 1.5 * d.y))
        hair_cap(mb, at(0, 0.02, 0.03), r, "hair", keep, scale=(1.16, 1.15, 1.18), count=80, seed=4)
        # Locks framing the face, from a parting down to the jaw.
        for s in (-1, 1):
            chunk(mb, [at(s * 0.05, -0.98, 0.92), at(s * 0.75, -0.82, 0.8), at(s * 1.14, -0.35, 0.25),
                       at(s * 1.14, -0.4, -0.55), at(s * 1.02, -0.68, 0.15), at(s * 0.55, -1.0, 0.7),
                       at(s * 1.02, -0.1, 0.55)], "hair")
            spike(mb, at(s * 1.1, -0.3, -0.25), at(s * 1.1, -0.5, -1.2), 0.028 * k, "hair")
        # The ponytail: up from the crown, then back and down to the shoulders.
        tie = at(0, 0.85, 0.68)
        mb.cylinder(tie - Vector((0, 0.015, 0.01)) * k, tie + Vector((0, 0.03, 0.02)) * k, 0.04 * k, 0.04 * k,
                    "leather_dark", segments=6)
        self.mark(mb, lambda p: self.rig.chain_weights(p, "ponytail", "head"))
        tube(mb, [(tie + Vector(p) * k, rad * k) for p, rad in (
            ((0, 0.015, 0.01), 0.04), ((0, 0.06, 0.04), 0.07), ((0, 0.125, 0.02), 0.088), ((0, 0.165, -0.07), 0.085),
            ((0, 0.175, -0.17), 0.068), ((0, 0.165, -0.26), 0.045), ((0, 0.145, -0.33), 0.0))], "hair", sides=6)

    def details(self, mb):
        k = self.k
        self.flatten(mb)
        surf = Surface(mb)
        self.mark(mb, "head")
        self.face(mb, surf, "hair", "skin")
        self.hair(mb)
        self.mark(mb, None)
        self.thumbs(mb, "skin", size=0.9)

        def under_scarf(p):
            return self.zone(p).startswith("scarf")
        # The harness crossing over the top, with gold studs.
        self.mark(mb, self.trunk)
        for s in (-1, 1):
            strap(mb, surf, (0, 0, 1.3 * k), (s * 0.78, 0, 0.62), 0.034 * k, "leather", thick=0.008,
                  skip=under_scarf)
        self.mark(mb, "chest")
        for x, z in ((0.0, 1.3), (-0.065, 1.385)):
            p = surf.onto((x * k, 0, z * k), (0, 1, 0))
            chunk(mb, [p + Vector(q) * k for q in ((0, 0, 0.03), (0, 0, -0.03), (0.02, 0, 0), (-0.02, 0, 0),
                                                   (0, -0.02, 0), (0, 0.02, 0))], "gold")
        # Two belts: one level, one slanting down to her right.
        self.mark(mb, "hips")
        strap(mb, surf, (0, 0, self.BELT * k), (0, 0, 1), 0.06 * k, "leather", thick=0.012)
        strap(mb, surf, (0, 0, (self.BELT - 0.08) * k), (0.42, 0, 1), 0.045 * k, "leather", thick=0.01)
        front = surf.onto((0.02 * k, 0, self.BELT * k), (0, 1, 0))
        buckle(mb, front + Vector((0, -0.018, 0)) * k, 0.085 * k, "metal", "leather_dark")
        # Pouches: a big one on the right hip, one below it on a thigh
        # strap, a small one on the left hip.
        thigh = Vector(self.parts["thigh.R"][1]).lerp(Vector(self.parts["thigh.R"][2]), 0.32)
        self.mark(mb, "thigh.R")
        strap(mb, surf, thigh, (0.08, 0, 1), 0.045 * k, "leather", thick=0.01, segments=10)
        for z, size, out, clasp in ((0.98, (0.15, 0.075, 0.17), (-1, -0.5), "gold"),
                                    (thigh.z / k + 0.03, (0.1, 0.05, 0.1), (-1, -0.4), None),
                                    (1.0, (0.08, 0.045, 0.09), (1, -0.3), None)):
            o = Vector((out[0], out[1], 0)).normalized()
            p = surf.out((0, 0, z * k), o)
            self.mark(mb, "hips" if z > 0.9 else "thigh.R")
            pouch(mb, p + o * size[1] * 0.4 * k, tuple(v * k for v in size), o, "leather", "leather_dark", clasp)


SPECS = [AdventurerWoman()]
