"""High elf woman: long blond hair and pointed ears, a red dress with gold
trim (a bodice with a gold neckline, pointed shoulder pieces, a long skirt
slit at the front with a gold-bordered panel), red bracers and red
high-heeled boots over the knee with gold trim."""

import math

from mathutils import Vector

import common  # noqa: F401  (the colors come from HighElf)
import studies
from dark_elf_man import arc, sheet, solid
from high_elf_man import HighElf


class HighElfWoman(HighElf):
    name = "high_elf_woman"
    height = 1.78
    female = True
    # Measured on the reference: narrow shoulders, a very narrow waist.
    shoulder = 0.13
    build = 0.78
    waist_width = 0.076
    heel = 0.09
    hair_out = 0.006
    hair_back = ((0, 0.08, 1.42), (0.125, 0.055, 0.32))
    lock = (0.07, -0.118, 1.39)
    lock_mid = -0.1
    ear = (0.075, 0.1)
    budget = 1150
    BOOT = 0.46

    NECK = 1.37      # The lowest point of the neckline (the middle of the chest).
    RISE = 0.75      # How fast it rises toward the arms.
    BELT = 1.165
    BOOT_TOP = 0.62  # The boots end over the knee.

    def __init__(self):
        super().__init__()
        k = self.k
        chest = lambda c, n: c.y < 0.0 and 1.3 * k < c.z < 1.52 * k  # noqa: E731
        self.bands = [
            # The gold line down the bodice.
            (self.V(0, 0, 0), Vector((1, 0, 0)), 0.009 * k, lambda c, n: c.y < -0.02 * k and 1.14 * k < c.z < 1.38 * k),
        ]
        for s in (-1, 1):   # The gold edge of the neckline.
            self.bands.append((self.V(0, 0, self.NECK - 0.012), Vector((-s * self.RISE, 0, 1)).normalized(), 0.012 * k,
                               lambda c, n, s=s: chest(c, n) and c.x * s > -0.005))
        self.cuts = [(self.V(0, 0, self.BOOT_TOP), (0, 0, 1), lambda c, n: 0.5 * k < c.z < 0.75 * k)]

    def paint(self, c, n):
        u = self.u(c)
        zone = self.zone(c)
        part = zone.split(".")[0]
        if self.is_hair(zone):
            return "hair"
        if part in ("head", "jaw", "neck", "hand", "shoulder", "upper_arm"):
            return "skin"
        if part in ("thigh", "shin", "foot"):
            return "red" if u.z < self.BOOT_TOP else "skin"
        if part in ("chest", "bust", "waist"):
            edge = self.NECK + self.RISE * abs(u.x) if u.y < 0.0 else 1.42
            if u.z > edge:
                return "skin"
            if studies.in_band(self, c, n):
                return "gold"
        return "red"

    def details(self, mb):
        k = self.k
        self.face(mb, eye="dark", brow="gold")
        self.ears(mb)
        self.hair(mb)
        self.collar(mb, height=0.055, gap=48)
        self.shoulder_pieces(mb, reach=0.215, lift=-0.035, corner=(0.13, 0.1, 1.4))
        # Bracers: red with gold ends, wider toward the elbow.
        for side in (".L", ".R"):
            self.cuff(mb, "forearm" + side, 0.92, 0.1, 0.003, "red", flare=0.007)
            self.cuff(mb, "forearm" + side, 0.95, 0.85, 0.006, "gold")
            self.cuff(mb, "forearm" + side, 0.16, 0.04, 0.011, "gold", flare=0.005)
        # The belt: a gold band with a point down the front; two diamonds
        # on the bodice.
        self.ring(mb, self.BELT, 0.03, 0.01, "gold")
        p = self.front(0, self.BELT - 0.005, 0.018)
        solid(mb, [p + Vector(d) * k for d in ((0, 0, 0.024), (0, 0, -0.085), (0.05, 0.03, 0.018), (-0.05, 0.03, 0.018),
                                               (0, -0.014, 0), (0, 0.02, 0))], "gold")
        for z, w, h in ((1.285, 0.026, 0.05), (1.19, 0.018, 0.03)):
            p = self.front(0, z, 0.005)
            solid(mb, [p + Vector(d) * k for d in ((0, 0, h), (0, 0, -h), (w, 0, 0), (-w, 0, 0), (0, -0.011, 0),
                                                   (0, 0.02, 0))], "gold")
            solid(mb, [p + Vector(d) * k for d in ((0, 0, h * 0.55), (0, 0, -h * 0.55), (w * 0.5, 0, 0), (-w * 0.5, 0, 0),
                                                   (0, -0.016, 0), (0, 0.02, 0))], "red")
        # The skirt: long, longer behind, slit at the front over her right leg.
        angles = arc(0, 1, 11)
        skirt = self.skirt_rows([(1.145, 0.098, 0.088, 0.0, -100, 252), (0.96, 0.165, 0.13, 0.0, -98, 247),
                                 (0.62, 0.215, 0.175, 0.02, -95, 236), (0.36, 0.25, 0.21, 0.04, -93, 230)],
                                angles, jag=0.05)
        for p, a in zip(skirt[-1], arc(-93, 230, 11)):
            p.z -= 0.14 * k * max(0.0, math.sin(a)) ** 2
        sheet(mb, skirt, 0.012 * k, "red", back="inner", trim="gold", hem=0.03 * k, sides=0.03 * k)
        # The panel down the front, over the skirt.
        panel = [[self.V(x, y, z) for x in (-w, 0.0, w)] for w, y, z in ((0.042, -0.112, 1.13), (0.052, -0.156, 0.96),
                                                                       (0.056, -0.172, 0.67))]
        panel.append([self.V(-0.056, -0.176, 0.64), self.V(0.0, -0.182, 0.575), self.V(0.056, -0.176, 0.64)])
        sheet(mb, panel, 0.012 * k, "red", back="inner", trim="gold", hem=0.028 * k, sides=0.02 * k)
        # Boots: pointed knee pieces, gold edges, gold toes and heels.
        self.boot_trim(mb)
        for side, s in ((".L", 1), (".R", -1)):
            self.knee_guard(mb, s, "red", 0.95)
            _, a, b, ra, rb = self.parts["foot" + side]
            b = Vector(b)
            solid(mb, [b + Vector(d) * k for d in ((-0.036, 0.0, -0.036), (0.036, 0.0, -0.036), (0, 0.0, 0.04),
                                                   (0, -0.065, -0.034), (0, 0.03, 0.0))], "gold")
        self.heels(mb, "gold", width=0.024)


SPECS = [HighElfWoman()]
