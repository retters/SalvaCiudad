"""Cross shield (reference 22): a tall red heater shield with clipped top
corners, a steel border and a raised white cross with flared ends."""

import studies
from _parts_b import Shield, mirrored, shades, tone

OUTLINE = mirrored([(0.0, 0.86), (0.2, 0.84), (0.255, 0.79), (0.26, 0.48), (0.2, 0.24), (0.1, 0.07), (0.0, 0.0)])
FOLD = [((0.0, 0.0), (1.0, 0.0))]
POST = [(0.0, 0.75), (0.038, 0.718), (0.021, 0.685), (0.021, 0.27), (0.03, 0.245), (0.0, 0.19), (-0.03, 0.245),
        (-0.021, 0.27), (-0.021, 0.685), (-0.038, 0.718)]
BAR = [(-0.155, 0.585), (-0.128, 0.622), (-0.098, 0.606), (0.098, 0.606), (0.128, 0.622), (0.155, 0.585),
       (0.128, 0.548), (0.098, 0.564), (-0.098, 0.564), (-0.128, 0.548)]


class CrossShield(studies.Spec):
    name = "w22_cross_shield"
    colors = {**shades("steel", 0x9A9BB0, 0.3), **shades("red", 0xC2222A, 0.07), "white": shades("w", 0xE2E0E6)["w"]}
    max_tris = 600
    grip = (0.0, 0.03, 0.45)

    def details(self, mb):
        sh = Shield(mb, OUTLINE, bend=lambda x, z: 0.12 * abs(x))
        sh.body(0.042, 0.02, 0.03, "steel", "steel_shade", lambda x, z: "red", bevel=0.014, center=(0.0, 0.5),
                rim_paint=lambda i: ("steel", "steel_light", "steel", "steel_shade")[i % 4])
        tone(mb, sh._verts(), "red", seed=11, share=0.6)
        sh.emblem(POST, "white", height=0.016)
        sh.emblem(BAR, "white", height=0.016)
        sh.finish(FOLD)


SPECS = [CrossShield()]
