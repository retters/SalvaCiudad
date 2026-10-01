"""Long bow (reference 13): an angular wooden bow with two green wraps, a
chunky green grip, gold tips and a thin string. The belly points to -X."""

import studies
from _parts_b import picture, shades, tone, tube

# Measured on the reference crop (pixels); the string is the vertical.
P = picture({
    "tip_top": (352, 52), "band_top": (322, 82), "bend_top": (235, 128), "wrap1_a": (172, 222),
    "wrap1_b": (156, 312), "grip_a": (114, 360), "grip_mid": (80, 405), "grip_b": (114, 452),
    "wrap2_a": (150, 498), "wrap2_b": (162, 588), "bend_bottom": (186, 640), "band_bottom": (265, 695),
    "tip_bottom": (300, 735), "string_top": (326, 92), "string_bottom": (272, 692),
}, bottom=(272, 692), top=(326, 92), length=1.41, shift=(0.03, 0.002))

LIMB = (0.038, 0.048)     # Half sizes across (Y) and along the bow's plane; x 1.41 for a square tube.
WRAP = (0.048, 0.062)


class LongBow(studies.Spec):
    name = "w13_long_bow"
    colors = {**shades("wood", 0x8A512D, 0.16), **shades("green", 0x7B9B38, 0.2), "gold": shades("g", 0xE3B23C)["g"],
              "string": shades("s", 0xDED9BE)["s"]}
    max_tris = 600
    grip = tuple(P["grip_mid"])

    def details(self, mb):
        def r(k, size=LIMB):
            return (size[0] * k, size[1] * k)

        limb = tube(mb, [
            (P["band_top"], r(0.72), "wood"), (P["bend_top"], r(0.9), "wood"), (P["wrap1_a"], r(1.0), "green"),
            (P["wrap1_a"], WRAP, "green"), (P["wrap1_b"], WRAP, "green"), (P["wrap1_b"], r(1.0), "wood"),
            (P["grip_a"], r(1.0), "green"), (P["grip_a"], r(1.1, WRAP), "green"),
            (P["grip_mid"], r(1.45, WRAP), "green"), (P["grip_b"], r(1.1, WRAP), "green"),
            (P["grip_b"], r(1.0), "wood"), (P["wrap2_a"], r(1.0), "green"), (P["wrap2_a"], WRAP, "green"),
            (P["wrap2_b"], WRAP, "green"), (P["wrap2_b"], r(1.0), "wood"), (P["bend_bottom"], r(0.95), "wood"),
            (P["band_bottom"], r(0.72), "wood"),
        ])
        tone(mb, limb, "wood", seed=3, share=0.6)
        tone(mb, limb, "green", seed=5, share=0.45, tones=("_shade",))
        for band, tip, inner in (("band_top", "tip_top", "bend_top"), ("band_bottom", "tip_bottom", "bend_bottom")):
            d = (P[tip] - P[band]).normalized()
            back = (P[inner] - P[band]).normalized()
            tube(mb, [(P[band] + back * 0.03, r(0.95), "gold"), (P[band] + d * 0.012, r(0.95), "gold"),
                      (P[band] + d * 0.012, r(0.6), "gold"), (P[tip], (0.008, 0.004), "gold")])
        mb.cylinder(P["string_bottom"], P["string_top"], 0.004, 0.004, "string", segments=3)


SPECS = [LongBow()]
