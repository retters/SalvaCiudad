"""Unicorn: the horse (horse.py) as a smaller, cuter pony: shorter legs and
body, a bigger head and eyes. White with lavender facets, a purple and pink
mane and tail, a golden spiral horn."""

from mathutils import Vector

import common
import studies
from horse import Equine, twisted_cone


class Unicorn(Equine):
    name = "unicorn"
    colors = {
        "unicorn": common.rgb(0xF3F0F8),
        "unicorn_light": common.rgb(0xFFFFFF),
        "unicorn_shade": common.rgb(0xDCD4EC),
        "mane_purple": common.rgb(0x9A62D8),
        "mane_pink": common.rgb(0xE68AD2),
        "horn": common.rgb(0xF0BE3C),
        "hoof": common.rgb(0xB4AAC6),
        "eye": common.rgb(0x151012),
    }
    tone_material = "unicorn"
    body = "unicorn"
    manes = ("mane_purple", "mane_pink")
    k = 0.95
    leg = 0.75
    length = 0.9
    head = 1.25
    eye = 1.35
    ridge = 0.08
    snout = 0.68
    leg_r = 1.35
    girth = 1.15
    mane_hang = 0.1
    tail_size = 1.2

    def details(self, mb):
        super().details(mb)
        base = self.P((0, -0.93, 1.98), True)
        tip = base + Vector((0, -0.45, 1.0)).normalized() * self.R(0.34, True)
        twisted_cone(mb, base - Vector((0, -0.45, 1.0)).normalized() * self.R(0.03, True), tip,
                     self.R(0.045, True), 5, 5, 0.45, "horn")


SPECS = [Unicorn()]
