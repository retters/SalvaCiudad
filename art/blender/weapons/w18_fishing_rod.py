"""Fishing rod (reference 18): a thick wooden handle with steel bands, a
bent rod with four line guides, a blue reel on a gold mount, and the line
hanging from the tip with a red-and-white float and a steel hook."""

from mathutils import Vector

import studies
from _parts_b import lathe, picture, shades, tone, tube

# Measured on the reference crop (pixels); the hanging line is the vertical.
P = picture({
    "butt": (78, 778), "handle_top": (146, 566), "band1": (152, 548), "band2_a": (160, 520), "band2_b": (165, 502),
    "seat_a": (172, 480), "seat_b": (178, 462), "wrap_b": (186, 438), "g1": (224, 346), "g2": (300, 232),
    "g3": (398, 130), "g4": (498, 58), "tip": (520, 42),
    "l0": (212, 452), "l1": (244, 362), "l1m": (290, 312), "l2": (320, 248), "l2m": (372, 200), "l3": (410, 144),
    "l3m": (462, 106), "l4": (512, 68), "float": (522, 330), "hook_top": (523, 470), "hook_a": (521, 522),
    "hook_b": (531, 550), "hook_c": (548, 544), "hook_d": (551, 520), "reel": (246, 556), "mount": (196, 484),
    "knob": (304, 520),
}, bottom=(522, 500), top=(522, 60), length=1.17, shift=(0.02, 0.014))


class FishingRod(studies.Spec):
    name = "w18_fishing_rod"
    colors = {"wood": shades("w", 0x98552E)["w"], "wood_shade": shades("w", 0x98552E, 0.2)["w_shade"],
              "steel": shades("s", 0x667080)["s"], "blue": shades("b", 0x4A8DB4)["b"],
              "gold": shades("g", 0xE0A62E)["g"], "white": shades("w", 0xECE6DA)["w"],
              "red": shades("r", 0xCC2F28)["r"]}
    max_tris = 600
    grip = tuple((P["butt"] + P["handle_top"]) * 0.5)

    def details(self, mb):
        handle, band, rod = 0.068, 0.054, 0.036
        pole = tube(mb, [
            (P["butt"], handle * 0.92, "wood"), (P["handle_top"], handle, "steel"),
            (P["handle_top"], band, "steel"), (P["band1"], band, "wood"), (P["band1"], band * 0.86, "wood"),
            (P["band2_a"], band * 0.86, "steel"), (P["band2_a"], band, "steel"), (P["band2_b"], band, "wood"),
            (P["band2_b"], band * 0.84, "wood_shade"), (P["seat_b"], band * 0.84, "gold"),
            (P["seat_b"], band * 0.95, "gold"), (P["wrap_b"], band * 0.9, "wood"), (P["wrap_b"], rod, "wood"),
            (P["g1"], rod * 0.9, "wood"), (P["g2"], rod * 0.78, "wood"), (P["g3"], rod * 0.64, "wood"),
            (P["g4"], rod * 0.5, "gold"), (P["tip"], rod * 0.4, "gold"),
        ])
        tone(mb, pole, "wood", seed=3, share=0.4, tones=("_shade",))
        # The line guides, on the line's side of the rod.
        for g, l in (("g1", "l1"), ("g2", "l2"), ("g3", "l3"), ("g4", "l4")):
            d = (P[l] - P[g]).normalized()
            mb.cylinder(P[g] - d * 0.025, P[l] + d * 0.012, 0.022, 0.016, "steel", segments=4)
        # The reel: a blue drum facing the viewer on a gold mount, with a crank knob.
        c = P["reel"]
        lathe(mb, c + Vector((0, 0.045, 0)), (0, -1, 0), [(0.1, 0.0), (0.125, 0.02), (0.125, 0.075), (0.1, 0.092)],
              8, "blue")
        lathe(mb, c + Vector((0, -0.04, 0)), (0, -1, 0), [(0.085, 0.0), (0.08, 0.012), (0.03, 0.02), (0.0, 0.04)],
              8, "steel")
        tube(mb, [(P["mount"] + Vector((-0.02, 0, 0.02)), 0.032, "gold"),
                  (c + Vector((-0.05, 0, 0.09)), 0.03, "gold")])
        mb.cylinder(c + Vector((0.09, -0.02, 0.03)), P["knob"] + Vector((0.01, -0.03, 0)), 0.014, 0.02, "steel",
                    segments=4)
        # The line: from the reel through the guides, sagging between them, and down to the hook.
        f = P["float"]
        path = [P[k] for k in ("l0", "l1", "l1m", "l2", "l2m", "l3", "l3m", "l4")] + [f + Vector((0, 0, 0.1))]
        tube(mb, [(p, 0.005, "white") for p in path], sides=3)
        mb.cylinder(f - Vector((0, 0, 0.1)), P["hook_top"], 0.005, 0.005, "white", segments=3)
        tube(mb, [
            (f + Vector((0, 0, 0.125)), 0.014, "red"), (f + Vector((0, 0, 0.09)), 0.02, "white"),
            (f + Vector((0, 0, 0.06)), 0.066, "white"), (f + Vector((0, 0, 0.022)), 0.085, "red"),
            (f + Vector((0, 0, -0.022)), 0.085, "white"), (f + Vector((0, 0, -0.06)), 0.066, "white"),
            (f + Vector((0, 0, -0.09)), 0.02, "steel"), (f + Vector((0, 0, -0.12)), 0.014, "steel"),
        ], sides=6, up=(1, 0, 0))
        tube(mb, [(P["hook_top"], 0.011, "steel"), (P["hook_a"], 0.011, "steel"), (P["hook_b"], 0.012, "steel"),
                  (P["hook_c"], 0.011, "steel"), (P["hook_d"], 0.004, "steel")], sides=4)


SPECS = [FishingRod()]
