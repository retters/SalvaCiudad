"""Arrow (reference 17): a wooden shaft with a chunky steel head and red
fletching. It stands head up; the swept ends of the vanes rest on Z = 0."""

import studies
from _parts_b import fletching, lathe, shades, tone


class Arrow(studies.Spec):
    name = "w17_arrow"
    colors = {**shades("steel", 0x8F8790, 0.3), "wood": shades("w", 0xA5623F)["w"],
              "red": shades("r", 0xF03434)["r"], "red_shade": shades("r", 0xB02A26)["r"]}
    max_tris = 600
    grip = (0.0, 0.0, 0.4)

    def details(self, mb):
        mb.cylinder((0, 0, 0.03), (0, 0, 0.67), 0.008, 0.007, "wood", segments=5)
        head = lathe(mb, (0, 0, 0.655), (0, 0, 1), [(0.011, 0.0), (0.036, 0.035), (0.0, 0.145)], 4, "steel")
        tone(mb, head, "steel", seed=3, share=0.7)
        # Three vanes: one toward the viewer (seen edge on, darker) and two to the sides.
        fletching(mb, (0, 0, 0.03), (0, 0, 1), 0.125, 0.062, 0.05, (210, 330), "red")
        fletching(mb, (0, 0, 0.03), (0, 0, 1), 0.125, 0.062, 0.05, (90,), "red_shade")


SPECS = [Arrow()]
