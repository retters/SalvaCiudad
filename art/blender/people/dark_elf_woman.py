"""Dark elf woman: purple skin, long white hair and pointed ears, a dark
top with a high collar and a bare midriff, a purple cape behind, a leather
belt on the hips, long dark gloves and dark thigh-high boots with pointed
cuffs and heels."""

from mathutils import Vector

import common
from dark_elf_man import Elf, sheet, solid


class DarkElfWoman(Elf):
    name = "dark_elf_woman"
    height = 1.78
    female = True
    # Measured on the reference: narrow shoulders and waist, slender limbs.
    shoulder = 0.13
    build = 0.8
    waist_width = 0.086
    heel = 0.06
    hair_back = ((0, 0.08, 1.45), (0.105, 0.055, 0.26))
    lock = (0.068, -0.115, 1.38)
    lock_mid = -0.1
    ear = (0.09, 0.05)
    chains = (("cape", "chest", ((0, 0.14, 1.47), (0, 0.2, 1.05), (0, 0.24, 0.7), (0, 0.26, 0.39)), True),)
    palette = {"top": "bottom", "cloak": "top"}   # Materials the game recolors (rigs.palette_name).
    colors = {
        "skin": common.rgb(0xBA8ADC),
        "skin_light": common.rgb(0xC796E6),
        "skin_shade": common.rgb(0xA677CA),
        "hair": common.rgb(0xDCD2E6),
        "top": common.rgb(0x362B4C),
        "boot": common.rgb(0x46375F),
        "cloak": common.rgb(0x443068),
        "dark": common.rgb(0x1F1634),      # The inside of the cape, the eyes.
        "leather": common.rgb(0x76524A),
        "silver": common.rgb(0xB9ADC8),
        "iris": common.rgb(0x8A4FD0),
    }
    tone_material = "skin"
    tones = 0.4
    budget = 1150

    TOP = 1.265      # The lower edge of the top.
    COLLAR = 1.5     # Where the collar starts.
    CLEAVAGE = 1.37  # The lowest point of the neckline.
    BELT = 1.14
    LEGGING = 0.8    # The upper edge of the leggings (their cuffs rise above it).

    def __init__(self):
        super().__init__()
        k = self.k
        self.cuts = [
            (self.V(0, 0, self.TOP), (0, 0, 1), lambda c, n: abs(c.x) < 0.13 * k),
            (self.V(0, 0, self.COLLAR), (0, 0, 1), lambda c, n: abs(c.x) < 0.1 * k and c.z > 1.4 * k),
            (self.V(0, 0, self.LEGGING), (0, 0, 1), lambda c, n: 0.7 * k < c.z < 0.9 * k),
        ]
        for s in (-1, 1):
            self.cuts.append((self.V(s * 0.01, 0, self.CLEAVAGE), Vector((s, 0, -0.3)).normalized(),
                              lambda c, n, s=s: c.y < 0 and c.x * s > 0 and 1.33 * k < c.z < 1.52 * k))
            self.cuts.append((self.V(s * 0.06, 0, 0), (1, 0, 0),
                              lambda c, n, s=s: c.x * s > 0 and 0.84 * k < c.z < 1.14 * k))

    def paint(self, c, n):
        u = self.u(c)
        zone = self.zone(c)
        part = zone.split(".")[0]
        if self.is_hair(zone):
            return "hair"
        if part in ("head", "jaw"):
            return "skin"
        if part == "neck":
            return "skin" if u.z > 1.565 else "top"
        if part in ("forearm", "hand"):
            return "top"
        if part in ("shoulder", "upper_arm"):
            return "top" if u.x > 0 else "skin"   # Only her left arm has a sleeve.
        if part in ("chest", "bust", "waist"):
            if u.z < self.TOP:
                return "skin"
            if u.z > self.COLLAR:
                return "top"
            if u.y < 0 and u.z > self.CLEAVAGE and abs(u.x) < 0.01 + (u.z - self.CLEAVAGE) * 0.3:
                return "skin"   # The neckline.
            return "top"
        if part == "hips":
            return "top" if u.z < self.BELT and (abs(u.x) < 0.06 or u.y > 0.03) else "skin"
        if part == "thigh":
            if u.z < self.LEGGING:
                return "boot"
            return "top" if abs(u.x) < 0.06 and u.z > 0.86 else "skin"
        return "boot"

    def details(self, mb):
        k = self.k
        self.begin(mb)
        self.head_details(mb, eye="dark", brow="dark")
        # The cape: from the shoulders down to the calves.
        xs = (1.0, 0.6, 0.0, -0.6, -1.0)
        ys = (0.0, 0.7, 1.0, 0.7, 0.0)
        cape = []
        for z, w, d, jag in ((1.47, 0.15, 0.09, 0), (1.05, 0.21, 0.15, 0), (0.7, 0.255, 0.19, 0), (0.47, 0.275, 0.21, 1)):
            cape.append([self.V(x * w, 0.05 + y * d + (0.02 if i % 2 else 0.0) * (1.47 - z),
                                z - (0.08 if jag and i % 2 == 0 else 0.0)) for i, (x, y) in enumerate(zip(xs, ys))])
        sheet(mb, cape, 0.014 * k, "cloak", back="dark")
        self.mark(mb, self.rig.chain_weights("cape"))
        # The collar of the cape over the shoulders.
        for s in (-1, 1):
            solid(mb, [self.V(s * 0.05, 0.02, 1.535), self.V(s * 0.16, 0.0, 1.5), self.V(s * 0.165, 0.08, 1.45),
                       self.V(s * 0.04, 0.11, 1.48), self.V(s * 0.15, -0.03, 1.47), self.V(s * 0.06, -0.02, 1.51)],
                  "cloak")
        # The gem at the throat.
        g = self.front(0, 1.475, 0.004)
        solid(mb, [g + Vector(d) * k for d in ((0, 0, 0.024), (0, 0, -0.032), (0.018, 0, 0), (-0.018, 0, 0),
                                               (0, -0.012, 0), (0, 0.01, 0))], "silver")
        # The pointed lower edge of the top.
        for s in (-1, 1):
            a = self.front(s * 0.015, self.TOP + 0.01, 0.0)
            b = self.front(s * 0.085, self.TOP + 0.01, 0.0)
            t = self.front(s * 0.045, self.TOP - 0.045, 0.004)
            solid(mb, [a, b, t, a + Vector((0, 0.03, 0)), b + Vector((0, 0.03, 0))], "top")
        self.mark(mb, "chest")   # The collar, the gem and the edge of the top.
        # Belts on the hips, with a buckle.
        self.ring(mb, self.BELT, 0.045, 0.012, "leather", tilt=-0.08)
        self.ring(mb, self.BELT - 0.03, 0.028, 0.018, "leather", tilt=0.22, count=10)
        b = self.front(0.0, self.BELT, 0.02)
        mb.box(b, (0.055 * k, 0.014 * k, 0.052 * k), "silver")
        mb.box(b - Vector((0, 0.006 * k, 0)), (0.028 * k, 0.014 * k, 0.026 * k), "leather")
        self.mark(mb, "spine")
        # The loincloth: a pointed panel at the front.
        top = [self.front(x, self.BELT - 0.02, 0.008) for x in (-0.062, 0.0, 0.062)]
        low = [self.front(-0.022, 0.9, 0.01), self.front(0.0, 0.8, 0.03), self.front(0.022, 0.9, 0.01)]
        sheet(mb, [top, low], 0.012 * k, "top")
        self.mark(mb, "hips")
        for side, s in ((".L", 1), (".R", -1)):
            # Glove cuffs flaring toward the elbow, with a point.
            self.cuff(mb, "forearm" + side, 0.34, 0.06, 0.004, "top", flare=0.016)
            _, a, b2, ra, rb = self.parts["forearm" + side]
            a, b2 = Vector(a), Vector(b2)
            out = Vector((s, 0.25, 0)).normalized()
            solid(mb, [a.lerp(b2, 0.25) + out * ra, a.lerp(b2, 0.02) + out * (ra + 0.016 * k) + Vector((0, 0.025 * k, 0)),
                       a.lerp(b2, 0.02) + out * (ra + 0.016 * k) - Vector((0, 0.025 * k, 0)),
                       a.lerp(b2, -0.12) + out * (ra + 0.022 * k), a.lerp(b2, 0.1)], "top")
            self.mark(mb, "lower_arm" + side)
            # Legging cuffs: a flare with a point up the outside of the thigh.
            self.cuff(mb, "thigh" + side, 0.36, 0.25, 0.004, "boot", flare=0.014, segments=7)
            _, a, b2, ra, rb = self.parts["thigh" + side]
            a, b2 = Vector(a), Vector(b2)
            out = Vector((s, -0.35, 0)).normalized()
            r = ra + (rb - ra) * 0.27
            solid(mb, [a.lerp(b2, 0.34) + out * r, a.lerp(b2, 0.25) + out * (r + 0.018 * k) + Vector((0, 0.04 * k, 0)),
                       a.lerp(b2, 0.25) + out * (r + 0.018 * k) - Vector((s * 0.02 * k, 0.04 * k, 0)),
                       a.lerp(b2, 0.07) + out * (r + 0.03 * k), a.lerp(b2, 0.25)], "boot")
            self.mark(mb, "thigh" + side)
            self.knee_guard(mb, s, "boot", 0.95)
            self.mark(mb, "shin" + side)
        self.heels(mb, "boot", width=0.03)
        self.mark(mb, "foot.?")


SPECS = [DarkElfWoman()]
