"""Crossbow (reference 14): a chunky wooden stock standing on its butt, a
curved wooden prod held by steel blocks, steel tip caps, a steel stirrup on
top, a drawn string and a trigger guard behind. The rail looks to -Y."""

import math

import studies
from _parts_b import shades, tone, tube

PROD = [(-0.39, 0.53), (-0.33, 0.6), (-0.2, 0.672), (-0.06, 0.705), (0.06, 0.705), (0.2, 0.672), (0.33, 0.6),
        (0.39, 0.53)]
NUT = (0.0, -0.05, 0.4)     # Where the drawn string crosses the rail.


class Crossbow(studies.Spec):
    name = "w14_crossbow"
    colors = {**shades("wood", 0xB0663A, 0.14), **shades("steel", 0x6E6C7A, 0.3),
              "rail": shades("r", 0xD9482A)["r"], "string": shades("s", 0x6E544C)["s"]}
    max_tris = 600
    grip = (0.0, 0.0, 0.2)

    def details(self, mb):
        stock = tube(mb, [
            ((0.012, 0.012, 0.0), (0.04, 0.05), "wood"), ((0.012, 0.012, 0.035), (0.062, 0.088), "wood"),
            ((0.0, 0.01, 0.17), (0.06, 0.08), "wood"), ((0.0, 0.0, 0.31), (0.045, 0.052), "wood"),
            ((0.0, 0.0, 0.62), (0.042, 0.048), "wood"), ((0.0, 0.0, 0.76), (0.04, 0.044), "wood"),
            ((0.0, 0.0, 0.78), (0.03, 0.034), "wood"),
        ], sides=6)
        tone(mb, stock, "wood", seed=6, share=0.55)
        # The rail groove and a steel side plate.
        mb.box((0.0, -0.036, 0.57), (0.014, 0.012, 0.36), "rail")
        mb.box((-0.04, 0.0, 0.52), (0.012, 0.03, 0.2), "steel_shade")
        tube(mb, [((x, 0.0, z), (0.03 - 0.008 * abs(x) / 0.39, 0.044 - 0.016 * abs(x) / 0.39), "wood_light")
                  for x, z in PROD])
        for s in (-1, 1):
            mb.box((0.078 * s, 0.0, 0.7), (0.06, 0.07, 0.085), "steel")
            mb.box((0.392 * s, 0.0, 0.535), (0.045, 0.05, 0.05), "steel")
            mb.cylinder((0.385 * s, -0.012, 0.525), NUT, 0.009, 0.009, "string", segments=4)
        # The stirrup: a hexagonal steel ring on the front end.
        ring = [(0.056 * math.sin(i * math.tau / 6), 0.0, 0.806 + 0.052 * math.cos(i * math.tau / 6))
                for i in range(7)]
        hoop = tube(mb, [(p, (0.03, 0.022), "steel") for p in ring[3:] + ring[1:4]], sides=4)
        tone(mb, hoop, "steel", seed=5, share=0.5, tones=("_shade",))
        # The trigger guard, under the stock.
        tube(mb, [((0, 0.03, 0.34), 0.011, "steel_shade"), ((0, 0.085, 0.325), 0.011, "steel_shade"),
                  ((0, 0.085, 0.25), 0.011, "steel_shade"), ((0, 0.03, 0.235), 0.011, "steel_shade")],
             sides=4, up=(1, 0, 0))


SPECS = [Crossbow()]
