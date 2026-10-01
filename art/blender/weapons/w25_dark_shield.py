"""Dark shield (reference 25): an angular dark grey shield with a thick
stone-like rim, a purple glow on the rim's inner edge and gable, two
shoulder spikes and a long grey crystal in the middle."""

from mathutils import Vector

import studies
from _parts_b import Shield, mirrored, shades, spike, tone

OUTLINE = mirrored([(0.0, 0.9), (0.19, 0.79), (0.25, 0.74), (0.25, 0.3), (0.2, 0.19), (0.0, 0.0)])
FOLD = [((0.0, 0.0), (1.0, 0.0))]
GLOW = [(0.198, 0.67), (0.238, 0.6), (0.215, 0.53), (0.188, 0.6)]      # A purple patch on the rim's side.
# The crystal: top, bottom, left, right and the raised middle (x, z, forward).
CRYSTAL = {"top": (0.0, 0.615, 0.0), "bottom": (0.0, 0.19, 0.0), "left": (-0.095, 0.475, 0.0),
           "right": (0.095, 0.475, 0.0), "mid": (0.0, 0.475, 0.1)}
SHARD = {"top": (0.0, 0.835, 0.0), "bottom": (0.0, 0.6, 0.0), "left": (-0.055, 0.7, 0.0),
         "right": (0.055, 0.7, 0.0), "mid": (0.0, 0.7, 0.05)}      # A smaller one above it.


class DarkShield(studies.Spec):
    name = "w25_dark_shield"
    colors = {**shades("stone", 0x6A6A84, 0.32), "purple": shades("p", 0x7C56B0)["p"],
              "dark": shades("d", 0x3A3248)["d"], "dark_light": shades("d", 0x4A4460)["d"]}
    max_tris = 600
    grip = (0.0, 0.03, 0.47)

    def details(self, mb):
        n = len(OUTLINE)
        sh = Shield(mb, OUTLINE, bend=lambda x, z: 0.1 * abs(x))
        sh.body(0.065, 0.03, 0.035, "stone", "stone_shade", lambda x, z: "dark", bevel=0.022, inner_mat="purple",
                center=(0.0, 0.5),
                rim_paint=lambda i: "purple" if i in (0, n - 1) else ("stone", "stone_shade", "stone_light")[i % 3])
        tone(mb, sh._verts(), "dark", seed=8, share=0.4, tones=("_light",))
        for s in (-1, 1):
            sh.emblem([(x * s, z) for x, z in GLOW], "purple", height=0.006, lift=0.03)
        sh.finish(FOLD)
        for crystal in (CRYSTAL, SHARD):
            v = {k: mb.bm.verts.new(sh.at(x, z, -0.004 - f)) for k, (x, z, f) in crystal.items()}
            for names, mat in ((("top", "left", "mid"), "stone_light"), (("top", "mid", "right"), "stone"),
                               (("left", "bottom", "mid"), "stone"), (("mid", "bottom", "right"), "stone_shade"),
                               (("top", "right", "bottom", "left"), "stone_shade")):
                mb.bm.faces.new([v[k] for k in names]).material_index = mb._material_index(mat)
        for s in (-1, 1):
            base = sh.at(0.212 * s, 0.762, -0.02)
            tip = base + Vector((0.8 * s, -0.3, 0.5)).normalized() * 0.135
            spike(mb, base - (tip - base) * 0.15, tip, 0.08, "stone_light")


SPECS = [DarkShield()]
