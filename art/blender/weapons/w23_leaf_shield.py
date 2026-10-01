"""Leaf shield (reference 23): a wide heater shield with a wooden border, a
dark green field and a light green tree emblem with leaves in the corners."""

import studies
from _parts_b import Shield, mirrored, shades, tone

OUTLINE = mirrored([(0.0, 0.84), (0.33, 0.8), (0.335, 0.47), (0.26, 0.22), (0.11, 0.055), (0.0, 0.0)])
FOLD = [((0.0, 0.0), (1.0, 0.0))]
CROWN = mirrored([(0.0, 0.765), (0.035, 0.7), (0.08, 0.705), (0.072, 0.65), (0.12, 0.62), (0.09, 0.565), (0.122, 0.51),
                  (0.07, 0.48), (0.045, 0.43)])
CROWN_TOP = [(0.0, 0.765), (-0.035, 0.7), (-0.072, 0.62), (-0.035, 0.52), (0.0, 0.56)]     # A lit facet.
TRUNK = [(-0.024, 0.46), (0.024, 0.46), (0.03, 0.25), (0.075, 0.18), (0.0, 0.115), (-0.075, 0.18), (-0.03, 0.25)]
LEAVES = [[(0.03, 0.37), (0.1, 0.43), (0.085, 0.335)],                                 # A twig on the trunk.
          [(0.272, 0.742), (0.17, 0.705), (0.15, 0.62), (0.255, 0.6)],                    # Upper corner leaf.
          [(0.215, 0.36), (0.13, 0.37), (0.11, 0.27), (0.175, 0.2)]]                 # Lower leaf.


class LeafShield(studies.Spec):
    name = "w23_leaf_shield"
    colors = {"wood": shades("w", 0xAA6238)["w"], "wood_shade": shades("w", 0xAA6238, 0.18)["w_shade"],
              "field": shades("f", 0x1F6549)["f"], "field_light": shades("f", 0x2F7D5E)["f"],
              **shades("leaf", 0x8DB552, 0.18)}
    max_tris = 600
    grip = (0.0, 0.03, 0.45)

    def details(self, mb):
        sh = Shield(mb, OUTLINE, bend=lambda x, z: 0.1 * abs(x))
        sh.body(0.05, 0.022, 0.03, "wood", "wood_shade", lambda x, z: "field", bevel=0.012, center=(0.0, 0.5),
                rim_paint=lambda i: ("wood", "wood_shade")[i % 2])
        tone(mb, sh._verts(), "field", seed=3, share=0.45, tones=("_light",))
        sh.emblem(CROWN, "leaf")
        sh.emblem(CROWN_TOP, "leaf_light", lift=0.006)
        sh.emblem(TRUNK, "leaf")
        for pts in LEAVES:
            sh.emblem(pts, "leaf", height=0.008)
            sh.emblem([(-x, z) for x, z in pts], "leaf_shade", height=0.008)
        sh.finish(FOLD)


SPECS = [LeafShield()]
