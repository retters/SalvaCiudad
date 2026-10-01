"""High elf man: tan skin, long blond hair and long pointed ears, a red
long coat with gold trim, big pointed gold-edged shoulder pieces, a gold
belt with a diamond buckle, long hanging panels with gold borders, dark
trousers and red boots with gold trim.

HighElf holds what he shares with the high elf woman: the colors, the
collar, the shoulder pieces and the gold-trimmed boots."""

import math

from mathutils import Vector

import common
import studies
from dark_elf_man import Elf, arc, sheet, solid


class HighElf(Elf):
    colors = {
        "skin": common.rgb(0xF4B588),
        "hair": common.rgb(0xEBBE6C),
        "red": common.rgb(0xC22B33),
        "red_light": common.rgb(0xD63A3C),
        "red_shade": common.rgb(0xA8202B),
        "inner": common.rgb(0x6E1019),     # The inside of the coat and of the skirts.
        "gold": common.rgb(0xF0A850),
        "dark": common.rgb(0x2B1D27),      # Trousers, and the outline of the eyes.
        "iris": common.rgb(0x1E9A72),
    }
    tone_material = "red"
    tones = 0.45
    BOOT = 0.4

    def collar(self, mb, height=0.08, gap=34):
        """A standing collar, open at the front, with a gold edge."""
        k = self.k
        angles = arc(-90 + gap, 270 - gap, 7)
        rows = [[self.V(r * math.cos(a), 0.0 + r * 1.05 * math.sin(a), z) for a in angles]
                for z, r in ((1.5 + height, 0.08), (1.5, 0.064))]
        sheet(mb, rows, 0.012 * k, "red", back="inner", trim="gold", top=0.02 * k)

    def shoulder_pieces(self, mb, reach=0.29, low=1.35, lift=0.0, inner=0.03, corner=None):
        """Stiff pointed pieces from the collar out over the shoulders,
        their outer edges gold: a point beyond each shoulder, a point on
        the chest and a point on the back (or, with `corner` = (x, y, z),
        free corners in front of and behind the shoulder)."""
        k = self.k
        s0 = self.shoulder
        for s in (-1, 1):
            neck = [self.V(s * 0.045, -0.062, 1.5), self.V(s * 0.058, 0.0, 1.548), self.V(s * 0.045, 0.07, 1.5)]
            rows = [
                # The inner row needs as many points as the outer one.
                [neck[0], neck[0].lerp(neck[1], 0.6), neck[1], neck[1].lerp(neck[2], 0.4), neck[2]],
                [self.V(s * corner[0], -corner[1], corner[2]) if corner else self.front(s * inner, low, 0.02),
                 self.V(s * (s0 + 0.045), -0.085, 1.505 + lift),
                 self.V(s * reach, 0.0, 1.52 + lift), self.V(s * (s0 + 0.045), 0.09, 1.505 + lift),
                 self.V(s * corner[0], corner[1], corner[2]) if corner
                 else self.behind(s * (inner + 0.005), low + 0.03, 0.02)],
            ]
            sheet(mb, rows, 0.02 * k, "red", back="inner", trim="gold", hem=0.03 * k, flip=s < 0)

    def boot_trim(self, mb):
        """A gold edge around the top of each boot, rising to a point."""
        k = self.k
        for side, s in ((".L", 1), (".R", -1)):
            _, a, b, ra, rb = self.parts["shin" + side]
            t = (a[2] - self.BOOT * k) / (a[2] - b[2])
            self.cuff(mb, "shin" + side, t - 0.04, t + 0.04, 0.007, "gold")
            r = ra + (rb - ra) * t
            p = Vector(a).lerp(Vector(b), t) + Vector((0, -r - 0.005 * k, 0))
            solid(mb, [p + Vector(d) * k for d in ((-0.04, 0.015, 0.0), (0.04, 0.015, 0.0), (0, -0.01, 0.0),
                                                   (0, -0.002, 0.07), (0, 0.02, 0.01))], "gold")


class HighElfMan(HighElf):
    name = "high_elf_man"
    height = 1.9
    # Measured on the reference.
    shoulder = 0.17
    build = 0.92
    waist_width = 0.118
    heel = 0.03
    hair_out = 0.014
    hair_back = ((0, 0.085, 1.48), (0.14, 0.06, 0.25))
    lock = (0.09, -0.135, 1.36)
    lock_mid = -0.12
    ear = (0.085, 0.07)
    budget = 1150
    BELT = 1.175

    def __init__(self):
        super().__init__()
        k = self.k
        self.bands = [
            # The gold line down the chest.
            (self.V(0, 0, 0), Vector((1, 0, 0)), 0.013 * k,
             lambda c, n: c.y < -0.02 * k and 1.15 * k < c.z < 1.5 * k),
        ]
        for s in (-1, 1):   # A gold V under the collar.
            self.bands.append((self.V(0, 0, 1.41), Vector((s * 0.085, 0, -0.05)).normalized(), 0.008 * k,
                               lambda c, n, s=s: c.y < -0.02 * k and c.x * s > -0.004 and 1.4 * k < c.z < 1.52 * k
                               and abs(c.x) < 0.07 * k))
        self.cuts = [(self.V(0, 0, self.BOOT), (0, 0, 1), lambda c, n: c.z < 0.5 * k)]

    def paint(self, c, n):
        u = self.u(c)
        zone = self.zone(c)
        part = zone.split(".")[0]
        if self.is_hair(zone):
            return "hair"
        if part in ("head", "jaw", "neck", "hand"):
            return "skin"
        if part in ("thigh", "shin", "foot"):
            return "red" if u.z < self.BOOT else "dark"
        if part in ("chest", "waist") and studies.in_band(self, c, n):
            return "gold"
        return "red"

    def details(self, mb):
        k = self.k
        self.face(mb, eye="dark", brow="gold")
        self.ears(mb)
        self.hair(mb)
        self.collar(mb)
        self.shoulder_pieces(mb)
        # Gold bands on the sleeves.
        for side in (".L", ".R"):
            self.cuff(mb, "forearm" + side, 0.34, 0.48, 0.007, "gold")
            self.cuff(mb, "forearm" + side, 0.84, 1.0, 0.007, "gold")
        # The belt and its diamond buckle; a smaller diamond on the chest.
        self.ring(mb, self.BELT, 0.045, 0.012, "gold")
        for z, w, h, off in ((self.BELT - 0.005, 0.042, 0.068, 0.026), (1.27, 0.024, 0.042, 0.01)):
            p = self.front(0, z, off)
            solid(mb, [p + Vector(d) * k for d in ((0, 0, h), (0, 0, -h), (w, 0, 0), (-w, 0, 0), (0, -0.02, 0),
                                                   (0, 0.02, 0))], "gold")
        # The skirt of the coat: long tails behind, and a shorter layer
        # over them; both open at the front and edged with gold.
        angles = arc(0, 1, 9)
        tails = self.skirt_rows([(1.155, 0.138, 0.102, 0.0, -75, 255), (0.97, 0.185, 0.138, 0.0, -68, 248),
                                 (0.6, 0.24, 0.185, 0.02, -65, 245), (0.15, 0.275, 0.22, 0.04, -63, 243)],
                                angles, jag=0.07)
        sheet(mb, tails, 0.012 * k, "red", back="inner", trim="gold", hem=0.032 * k, sides=0.03 * k)
        over = self.skirt_rows([(1.165, 0.15, 0.114, 0.0, -86, 266), (0.98, 0.2, 0.152, 0.0, -78, 258),
                                (0.72, 0.248, 0.19, 0.01, -70, 250), (0.47, 0.28, 0.22, 0.02, -65, 245)],
                               angles, jag=0.07)
        sheet(mb, over, 0.012 * k, "red", back="inner", trim="gold", hem=0.032 * k, sides=0.03 * k)
        # The narrow panel hanging from the buckle.
        y = self.front(0, 1.0, 0.03).y
        panel = [[self.front(x, 1.14, 0.03) for x in (-0.045, 0.0, 0.045)],
                 [Vector((x * k, y, 0.76 * k)) for x in (-0.05, 0.0, 0.05)],
                 [Vector((x * k, y, z * k)) for x, z in ((-0.05, 0.72), (0.0, 0.65), (0.05, 0.72))]]
        sheet(mb, panel, 0.012 * k, "red", back="inner", trim="gold", hem=0.028 * k, sides=0.02 * k)
        self.boot_trim(mb)
        self.heels(mb, "red")


SPECS = [HighElfMan()]
