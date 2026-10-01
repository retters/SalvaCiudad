"""Mannequins: the shared body in plain clothes, male and female. The
example to copy for a character: paint by zone and height, cuts for crisp
borders, and a few details."""

from mathutils import Vector

import common
import studies
from _human import Human


class Mannequin(Human):
    name = "mannequin"
    colors = {
        "skin": common.rgb(0xE8B48C),
        "skin_light": common.rgb(0xF0C29C),
        "skin_shade": common.rgb(0xD9A27A),
        "tunic": common.rgb(0x3A62C4),
        "trousers": common.rgb(0x3B3A48),
        "boot": common.rgb(0x6B4226),
        "hair": common.rgb(0x5A3420),
        "eye": common.rgb(0x1A1414),
    }
    tone_material = "skin"

    def __init__(self):
        super().__init__()
        z = self.z
        legs = lambda c, n: c.z < z["hip"]  # noqa: E731
        arms = lambda c, n: abs(c.x) > self.shoulder * self.k * 0.9  # noqa: E731
        self.cuts = [
            ((0, 0, z["knee"] - 0.08 * self.k), (0, 0, 1), legs),       # Boot tops.
            ((0, 0, z["hip"] - 0.03 * self.k), (0, 0, 1), lambda c, n: abs(c.x) < 0.3 * self.k),  # Tunic hem.
            ((0, 0, z["chest"] - 0.02 * self.k), (0, 0, 1), arms),      # Sleeve ends.
            ((0, 0, z["neck"] + 0.01 * self.k), (0, 0, 1), lambda c, n: abs(c.x) < 0.12 * self.k),  # Collar.
        ]

    def paint(self, c, n):
        z, zone = self.z, self.zone(c)
        if zone.startswith(("foot", "shin")) and c.z < z["knee"] - 0.08 * self.k:
            return "boot"
        if zone.startswith(("thigh", "shin", "foot")):
            return "trousers" if c.z < z["hip"] - 0.03 * self.k else "tunic"
        if zone in ("head", "jaw", "neck"):
            return "skin" if c.z > z["neck"] + 0.01 * self.k else "tunic"
        if zone.startswith(("forearm", "hand")):
            return "skin"
        if zone.startswith(("upper_arm", "shoulder")):
            return "tunic" if c.z > z["chest"] - 0.02 * self.k else "skin"
        return "tunic" if c.z > z["hip"] - 0.03 * self.k else "trousers"

    def details(self, mb):
        self.eyes(mb)
        # Hair: a cap of shards over the top and back of the head.
        head = Vector(self.parts["head"][1])
        r = self.parts["head"][2]
        mb.sphere((head.x, head.y + 0.02 * self.k, head.z + 0.035 * self.k), 1.0, "hair", segments=8, rings=5,
                  scale=(r[0] * 1.08, r[1] * 1.05, r[2] * 0.85))


class MannequinFemale(Mannequin):
    name = "mannequin_female"
    female = True
    height = 1.7
    shoulder = 0.155
    hip = 0.09
    build = 0.9


SPECS = [Mannequin(), MannequinFemale()]
