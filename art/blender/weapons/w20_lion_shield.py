"""Lion shield (reference 20): a blue heater shield creased down the
middle, with a thick gold border and a gold rampant lion made of flat
raised pieces."""

import studies
from _parts_b import Shield, mirrored, shades

OUTLINE = mirrored([(0.0, 0.86), (0.3, 0.815), (0.31, 0.5), (0.25, 0.27), (0.13, 0.09), (0.0, 0.0)])
FOLD = [((0.0, 0.0), (1.0, 0.0))]

# The lion, facing left: (material, extra lift, polygon of (x, z)).
LION = [
    ("gold_light", 0.0, [(-0.02, 0.735), (0.03, 0.752), (0.05, 0.725), (0.095, 0.722), (0.095, 0.685), (0.13, 0.655),
                         (0.11, 0.625), (0.126, 0.585), (0.09, 0.565), (0.03, 0.6), (0.015, 0.66)]),   # Mane.
    ("gold", 0.0, [(-0.035, 0.6), (0.03, 0.62), (0.085, 0.585), (0.1, 0.5), (0.085, 0.41), (0.03, 0.385),
                   (0.0, 0.43), (-0.02, 0.52)]),                                       # Torso.
    ("gold", 0.005, [(-0.105, 0.665), (-0.075, 0.7), (-0.03, 0.722), (0.015, 0.71), (0.03, 0.655), (-0.005, 0.62),
                     (-0.05, 0.628), (-0.06, 0.648), (-0.1, 0.645)]),                  # Head.
    ("gold", 0.005, [(-0.088, 0.628), (-0.045, 0.618), (-0.05, 0.6)]),                 # Jaw.
    ("gold", 0.0, [(-0.125, 0.622), (-0.17, 0.632), (-0.18, 0.662), (-0.152, 0.68), (-0.12, 0.66)]),   # Paws.
    ("gold", 0.0, [(-0.115, 0.5), (-0.16, 0.5), (-0.175, 0.53), (-0.15, 0.552), (-0.115, 0.54)]),
    ("gold", 0.0, [(-0.09, 0.355), (-0.14, 0.33), (-0.155, 0.35), (-0.135, 0.378), (-0.1, 0.38)]),
    ("gold", 0.0, [(0.06, 0.295), (0.045, 0.252), (-0.03, 0.245), (-0.04, 0.268), (0.005, 0.285)]),
    ("gold_light", 0.0, [(0.16, 0.69), (0.198, 0.72), (0.188, 0.765), (0.152, 0.735)]),    # Tail tuft.
]
# Legs and tail: (material, width, line of (x, z)).
LIMBS = [
    ("gold", 0.032, [(-0.005, 0.585), (-0.085, 0.6), (-0.135, 0.645)]),
    ("gold", 0.032, [(0.0, 0.515), (-0.075, 0.5), (-0.13, 0.522)]),
    ("gold", 0.038, [(0.03, 0.405), (-0.05, 0.38), (-0.11, 0.355)]),
    ("gold", 0.04, [(0.07, 0.42), (0.078, 0.34), (0.045, 0.275)]),
    ("gold", 0.018, [(0.085, 0.43), (0.135, 0.44), (0.168, 0.5), (0.152, 0.58), (0.158, 0.65), (0.176, 0.705)]),
]


def paint(x, z):
    return "blue_light" if x < 0.0 else "blue"


class LionShield(studies.Spec):
    name = "w20_lion_shield"
    colors = {**shades("gold", 0xF2AE35, 0.3), **shades("blue", 0x2A4AA6, 0.22)}
    max_tris = 600
    grip = (0.0, 0.03, 0.45)

    def details(self, mb):
        sh = Shield(mb, OUTLINE, bend=lambda x, z: 0.13 * abs(x))
        sh.body(0.058, 0.022, 0.03, "gold", "blue_shade", paint, bevel=0.014, fan=False, splits=FOLD,
                rim_paint=lambda i: ("gold", "gold_light", "gold_shade", "gold")[i % 4])
        for mat, lift, pts in LION:
            sh.emblem(pts, mat, lift=lift)
        for mat, width, line in LIMBS:
            sh.strip(line, width, mat)
        sh.finish(FOLD)


SPECS = [LionShield()]
