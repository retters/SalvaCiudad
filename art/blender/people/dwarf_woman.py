"""Dwarf (woman): short and sturdy, with a big head, two thick blonde
braids over the shoulders tied with gold rings, a green dress down to the
shins with a lighter hem, a wide belt with a buckle, bracers and heavy
boots. There is no reference picture (phase 57): see dwarf_man.
"""

import random

from mathutils import Vector

import common
import studies
from adventurer_man import Surface, chunk, hair_cap, spike
from dwarf_man import Dwarf


class DwarfWoman(Dwarf):
    name = "dwarf_woman"
    height = 1.24
    female = True
    shoulder = 0.22
    build = 1.38
    head_size = 1.38
    palette = {"dress": "top", "trousers": "bottom"}   # Materials the game recolors (rigs.palette_name).
    colors = {
        "skin": common.rgb(0xEDAE86),
        "dress": common.rgb(0x3F7A4A),
        "dress_light": common.rgb(0x4C8C58),
        "dress_shade": common.rgb(0x2E5C38),
        "trousers": common.rgb(0x4A4038),
        "leather": common.rgb(0x7A4A2C),
        "leather_dark": common.rgb(0x4E2E1E),
        "hair": common.rgb(0xE0B050),
        "hair_dark": common.rgb(0xB8863A),
        "gold": common.rgb(0xE9A63E),
        "eye": common.rgb(0x1A1414),
    }
    tone_material = "dress"
    tones = 0.2
    HEM = 0.36
    BOOT = 0.3

    def customize(self, parts):
        self.angular_jaw(parts)
        self.sleeves(parts, "dress_shade", length=0.9, r0=0.064, r1=0.076)
        self.skirt(parts, self.BELT + 0.04, self.HEM, (0.225, 0.165), (0.33, 0.235), "trousers")
        self.bracers(parts, "skin", r=0.05, top=0.4)
        self.legs(parts, "trousers")

    def paint(self, c, n):
        k = self.k
        zone = self.painted_zone(c)
        if zone.startswith("skirt"):
            return "dress_shade" if c.z < (self.HEM + 0.07) * k else "dress"
        if zone.startswith(("sleeve", "shoulder", "chest", "bust", "waist", "hips")):
            return "dress"
        if zone.startswith("bracer"):
            return "leather_dark"
        if zone.startswith(("cuff", "fold", "foot")):
            return "leather"
        if zone.startswith(("shin", "thigh")):
            return "leather" if c.z < self.BOOT * k else "trousers"
        return "skin"

    def hair(self, mb):
        """Hair parted in the middle and two thick braids to the chest."""
        k = self.k
        at = self.head_at
        r = self.parts["head"][2]

        def keep(d):
            return d.z > (0.2 - 0.45 * d.y if d.y < 0 else max(-0.75, 0.1 - 1.5 * d.y))
        hair_cap(mb, at(0, 0.03, 0.03), r, "hair", keep, scale=(1.15, 1.15, 1.2), count=80, seed=3)
        rnd = random.Random(7)
        for s in (-1, 1):
            # A lock framing the face, down to the jaw.
            chunk(mb, [at(s * 0.05, -0.98, 0.9), at(s * 0.75, -0.84, 0.78), at(s * 1.12, -0.35, 0.25),
                       at(s * 1.12, -0.42, -0.5), at(s * 1.0, -0.7, 0.15), at(s * 0.55, -1.0, 0.68),
                       at(s * 1.0, -0.1, 0.55)], "hair")
            # The braid: lumps down the front of the shoulder, then a ring and a tip.
            path = [(s * 1.05, -0.45, -0.75), (s * 1.0, -0.7, -1.2), (s * 0.95, -0.85, -1.65), (s * 0.92, -0.9, -2.1)]
            for i, c in enumerate(path):
                size = 0.3 - 0.03 * i
                pts = studies.ellipsoid_points(at(*c), (size * r[0], size * r[1], 0.3 * r[2]), 8, rnd)
                chunk(mb, pts, "hair_dark" if i % 2 else "hair")
            low = at(s * 0.92, -0.9, -2.35)
            mb.cylinder(low + Vector((0, 0, 0.03 * k)), low, 0.028 * k, 0.028 * k, "gold", segments=5)
            spike(mb, low, low + Vector((0, 0, -0.09 * k)), 0.024 * k, "hair")

    def details(self, mb):
        self.flatten(mb)
        surf = Surface(mb)
        self.mark(mb, "head")
        self.face(mb, surf, "hair_dark", "skin")
        self.hair(mb)
        self.mark(mb, None)
        self.thumbs(mb, "skin")
        self.belt(mb, surf, size=0.1)


SPECS = [DwarfWoman()]
