"""Purple recurve bow (reference 15): angular purple limbs with two indigo
sections, a tan wrapped grip, a gold band under the top tip and a thin
string. The belly points to -X."""

import studies
from _parts_b import picture, shades, tone, tube

# Measured on the reference crop (pixels); the string is the vertical.
P = picture({
    "tip_top": (292, 40), "band_top": (258, 72), "bend_top": (200, 106), "indigo1_a": (152, 168),
    "indigo1_b": (128, 246), "horn_top": (74, 302), "grip_a": (80, 346), "grip_b": (68, 440),
    "horn_bottom": (42, 486), "indigo2_a": (72, 546), "indigo2_b": (84, 616), "bend_bottom": (116, 690),
    "band_bottom": (158, 730), "tip_bottom": (178, 756), "string_top": (262, 80), "string_bottom": (164, 718),
}, bottom=(164, 718), top=(262, 80), length=1.16, shift=(0.018, 0.002))

LIMB = (0.034, 0.044)    # Half sizes across (Y) and along the bow's plane; x 1.41 for a square tube.


class PurpleBow(studies.Spec):
    name = "w15_purple_bow"
    colors = {**shades("purple", 0x8A3399, 0.2), "indigo": shades("i", 0x473078)["i"],
              "tan": shades("t", 0xCFA06A)["t"], "gold": shades("g", 0xE3A33A)["g"],
              "string": shades("s", 0xD8D4D7)["s"]}
    max_tris = 600
    grip = tuple((P["grip_a"] + P["grip_b"]) * 0.5)

    def details(self, mb):
        def r(k):
            return (LIMB[0] * k, LIMB[1] * k)

        limb = tube(mb, [
            (P["tip_top"], (0.008, 0.004), "purple"), (P["band_top"], r(0.62), "purple"),
            (P["bend_top"], r(0.85), "purple"), (P["indigo1_a"], r(0.95), "indigo"),
            (P["indigo1_b"], r(1.0), "purple"), (P["horn_top"], r(1.25), "purple"), (P["grip_a"], r(1.0), "tan"),
            (P["grip_a"], r(1.12), "tan"), (P["grip_b"], r(1.12), "tan"), (P["grip_b"], r(1.0), "purple"),
            (P["horn_bottom"], r(1.25), "purple"), (P["indigo2_a"], r(1.0), "indigo"),
            (P["indigo2_b"], r(0.95), "purple"), (P["bend_bottom"], r(0.85), "purple"),
            (P["band_bottom"], r(0.62), "purple"), (P["tip_bottom"], (0.008, 0.004), "purple"),
        ])
        tone(mb, limb, "purple", seed=2, share=0.6)
        d = (P["bend_top"] - P["band_top"]).normalized()
        tube(mb, [(P["band_top"] - d * 0.012, r(0.78), "gold"), (P["band_top"] + d * 0.025, r(0.82), "gold")])
        mb.cylinder(P["string_bottom"], P["string_top"], 0.004, 0.004, "string", segments=3)


SPECS = [PurpleBow()]
