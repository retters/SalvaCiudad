"""Round wooden shield (reference 19): vertical planks, a faceted steel
rim with eight rivets and a steel boss."""

import math

import studies
from _parts_b import Shield, regular, shades, tone

R = 0.375
CZ = R * math.cos(math.pi / 16)      # The center: the lowest corners stand on Z = 0.
GROOVES = (-0.212, -0.106, 0.0, 0.106, 0.212)   # Plank borders (x).
PLANKS = ("wood_shade", "wood", "wood_light", "wood", "wood_light", "wood_shade")


def paint(x, z):
    for g in GROOVES:
        if abs(x - g) < 0.004:
            return "groove"
    return PLANKS[sum(x > g for g in GROOVES)]


class RoundWoodShield(studies.Spec):
    name = "w19_round_wood_shield"
    colors = {**shades("wood", 0x8D4F2E, 0.1), **shades("steel", 0x7F7B8E, 0.22),
              "groove": shades("g", 0x3F241B)["g"]}
    max_tris = 600
    grip = (0.0, 0.03, CZ)

    def details(self, mb):
        sh = Shield(mb, regular(16, R, (0.0, CZ), math.pi / 16))
        splits = [((g + s * 0.004, 0.0), (1.0, 0.0)) for g in GROOVES for s in (-1, 1)]
        sh.body(0.066, 0.024, 0.03, "steel", "wood_shade", paint, bevel=0.022, fan=False, splits=splits,
                rim_paint=lambda i: ("steel", "steel_shade", "steel", "steel_light")[i % 4])
        sh.finish()
        tone(mb, sh.boss(0.0, CZ, [(0.1, 0.0), (0.095, 0.014), (0.06, 0.05), (0.0, 0.064)], "steel",
                         phase=math.pi / 8), "steel", seed=4, share=0.6)
        for k in range(8):
            a = k * math.tau / 8
            sh.stud(0.33 * math.sin(a), CZ + 0.33 * math.cos(a), 0.024, 0.03, "steel_light", y=-0.024,
                    phase=math.pi / 4)


SPECS = [RoundWoodShield()]
