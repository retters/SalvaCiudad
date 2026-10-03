"""Dwarf (man): short and broad, with a big head set low on the shoulders,
a red beard down to the chest with two braids, bushy brows, a russet
tunic with a short skirt, a wide belt with a big buckle, bracers, dark
trousers and heavy boots.

There is no reference picture for the dwarves (phase 57): they are the
adventurers' body with other proportions. dwarf_woman imports Dwarf.
"""

import random

from mathutils import Vector

import common
import studies
from adventurer_man import SIDES, Adventurer, Surface, buckle, chunk, hair_cap, mirror, spike, strap


class Dwarf(Adventurer):
    """What the two dwarves share: the proportions, the loose trousers and
    the heavy boots, the belt and the face."""

    head_size = 1.42
    hip = 0.125
    BELT = 1.02      # Heights on the 1.8 m body.
    HEM = 0.55       # The tunic's hem, at the knees: the legs look short.
    BOOT = 0.44      # The rim of the boot cuffs.

    def head_at(self, x, y, z):
        """A point by the head: its center plus the offsets in head radii."""
        head = Vector(self.parts["head"][1])
        r = self.parts["head"][2]
        return head + Vector((x * r[0], y * r[1], z * r[2]))

    def legs(self, parts, inside):
        j, b = self.joints(), self.build
        for side, x in SIDES:
            parts["thigh" + side] = self.capsule(mirror(j["hip"], x), mirror(j["knee"], x), 0.094 * b, 0.076 * b)
        self.boots(parts, inside, top=self.BOOT, cuff=0.088, cuff_height=0.1, toe=0.16, shaft=0.058, foot=1.15,
                   knee=0.074)

    def belt(self, mb, surf, size=0.13):
        """The wide belt and its buckle."""
        k = self.k
        self.mark(mb, self.trunk)
        strap(mb, surf, (0, 0, self.BELT * k), (0, 0, 1), 0.11 * k, "leather", thick=0.014, segments=14)
        front = surf.onto((0, 0, self.BELT * k), (0, 1, 0))
        self.mark(mb, "hips")
        buckle(mb, front + Vector((0, -0.02, 0)) * k, size * k, "gold", "leather_dark")

    def brows(self, mb, surf, mat):
        """Bushy brows over the eyes."""
        u = self.k * self.head_size
        head = Vector(self.parts["head"][1])
        for s in (-1, 1):
            p = surf.onto((s * 0.04 * u, head.y, self.z["eyes"] + 0.03 * u), (0, 1, 0))
            chunk(mb, [p + Vector(q) * u for q in ((-s * 0.034, -0.014, -0.012), (-s * 0.034, -0.016, 0.012),
                                                   (s * 0.04, -0.006, 0.0), (s * 0.04, -0.004, 0.02),
                                                   (-s * 0.03, 0.02, 0.0), (s * 0.03, 0.02, 0.012))], mat)


class DwarfMan(Dwarf):
    name = "dwarf_man"
    height = 1.3
    shoulder = 0.265
    build = 1.5
    palette = {"tunic": "top", "trousers": "bottom"}   # Materials the game recolors (rigs.palette_name).
    colors = {
        "skin": common.rgb(0xE8A57C),
        "tunic": common.rgb(0x8E3B2C),
        "tunic_light": common.rgb(0xA4483A),
        "tunic_shade": common.rgb(0x6A2A20),
        "trousers": common.rgb(0x443C3A),
        "leather": common.rgb(0x7A4A2C),
        "leather_dark": common.rgb(0x4E2E1E),
        "hair": common.rgb(0xC8642A),
        "hair_dark": common.rgb(0x9A4A1E),
        "gold": common.rgb(0xE9A63E),
        "metal": common.rgb(0x9A9AA2),
        "eye": common.rgb(0x1A1414),
    }
    tone_material = "tunic"
    tones = 0.2

    def customize(self, parts):
        self.angular_jaw(parts)
        self.sleeves(parts, "tunic_shade", length=0.75, r0=0.068, r1=0.082)
        self.skirt(parts, self.BELT + 0.04, self.HEM, (0.235, 0.17), (0.3, 0.215), "trousers")
        self.bracers(parts, "skin", r=0.054, top=0.35)
        self.legs(parts, "trousers")

    def paint(self, c, n):
        k = self.k
        zone = self.painted_zone(c)
        if zone.startswith(("sleeve", "shoulder", "chest", "waist", "hips", "skirt")):
            return "tunic"
        if zone.startswith("bracer"):
            return "leather_dark"
        if zone.startswith(("cuff", "fold", "foot")):
            return "leather"
        if zone.startswith("shin"):
            return "leather" if c.z < self.BOOT * k else "trousers"
        if zone.startswith("thigh"):
            return "trousers" if c.z < self.HEM * k else "tunic"
        return "skin"

    def hair(self, mb):
        """Short swept-back hair, thick at the sides."""
        k = self.k
        at = self.head_at
        r = self.parts["head"][2]

        def keep(d):
            return d.z > (0.25 - 0.3 * d.y if d.y < 0 else max(-0.7, 0.1 - 1.3 * d.y))
        hair_cap(mb, at(0, 0.04, 0.03), r, "hair", keep, scale=(1.16, 1.16, 1.22), count=70)
        rnd = random.Random(5)
        tufts = [
            ((0.0, -0.55, 1.02), (0.8, 0.45, 0.3)),
            ((0.7, 0.1, 0.95), (0.5, 0.8, 0.4)),
            ((-0.7, 0.1, 0.95), (0.5, 0.8, 0.4)),
            ((0.0, 0.95, 0.3), (0.9, 0.42, 0.7)),
            ((0.98, 0.3, 0.2), (0.36, 0.6, 0.6)),
            ((-0.98, 0.3, 0.2), (0.36, 0.6, 0.6)),
        ]
        for i, (c, h) in enumerate(tufts):
            pts = studies.ellipsoid_points(at(*c), (h[0] * r[0], h[1] * r[1], h[2] * r[2]), 9, rnd)
            chunk(mb, pts, "hair_dark" if i % 2 else "hair")
        for a, b, rad in (((0.5, 0.9, 0.5), (0.75, 1.3, 0.2), 0.05), ((-0.5, 0.9, 0.5), (-0.75, 1.3, 0.2), 0.05),
                          ((0.0, 1.05, 0.0), (0.0, 1.4, -0.4), 0.055)):
            spike(mb, at(*a), at(*b), rad * k, "hair_dark")

    def beard(self, mb):
        """A full beard from the cheeks down to the chest, a moustache and
        two braids with gold rings."""
        k = self.k
        at = self.head_at
        r = self.parts["head"][2]
        rnd = random.Random(9)
        lumps = [
            ((0.0, -0.95, -0.55), (0.8, 0.4, 0.42), "hair"),          # Under the nose and over the chin.
            ((0.72, -0.5, -0.45), (0.42, 0.55, 0.5), "hair_dark"),    # The cheeks.
            ((-0.72, -0.5, -0.45), (0.42, 0.55, 0.5), "hair_dark"),
            ((0.0, -0.95, -1.15), (0.78, 0.42, 0.6), "hair"),         # Down the chest.
            ((0.0, -0.95, -1.75), (0.5, 0.3, 0.5), "hair_dark"),
        ]
        for c, h, mat in lumps:
            pts = studies.ellipsoid_points(at(*c), (h[0] * r[0], h[1] * r[1], h[2] * r[2]), 10, rnd)
            chunk(mb, pts, mat)
        for s in (-1, 1):  # The moustache and the braids.
            spike(mb, at(s * 0.1, -1.2, -0.42), at(s * 0.75, -1.15, -0.72), 0.035 * k, "hair")
            top, low = at(s * 0.45, -1.1, -1.25), at(s * 0.5, -1.15, -2.3)
            mb.cylinder(top, low, 0.03 * k, 0.022 * k, "hair", segments=5)
            mb.cylinder(low, low + Vector((0, 0, -0.03 * k)), 0.027 * k, 0.027 * k, "gold", segments=5)
            spike(mb, low + Vector((0, 0, -0.03 * k)), low + Vector((0, 0, -0.1 * k)), 0.022 * k, "hair_dark")

    def details(self, mb):
        self.flatten(mb)
        surf = Surface(mb)
        self.mark(mb, "head")
        self.face(mb, surf, "hair_dark", "skin")
        self.brows(mb, surf, "hair")
        self.hair(mb)
        self.beard(mb)
        self.mark(mb, None)
        self.thumbs(mb, "skin", size=1.1)
        self.belt(mb, surf)


SPECS = [DwarfMan()]
