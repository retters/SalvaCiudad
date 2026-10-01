"""Round blue shield (reference 24): a domed round shield with alternating
blue and white sectors (six in the reference), a steel rim with small
rivets and a steel boss."""

import math

import studies
from _parts_b import Shield, regular, shades, tone

R = 0.375
N = 18
PHASE = math.radians(-6.0)      # The sector borders are turned a little, as in the reference.
CZ = R * math.cos(PHASE)        # The center: the lowest corner stands on Z = 0.


def paint(x, z):
    a = (math.atan2(x, z - CZ) - PHASE) % math.tau
    sector = int(a / (math.tau / 6))
    step = int(a / (math.tau / N))
    inner = math.hypot(x, z - CZ) < 0.17
    if sector % 2 == 0:
        return "blue_light" if (step + inner) % 3 == 0 else "blue"
    return "white_shade" if (step + inner) % 3 == 1 else "white"


class RoundBlueShield(studies.Spec):
    name = "w24_round_blue_shield"
    colors = {**shades("steel", 0x77768F, 0.18), "blue": shades("b", 0x2247A0)["b"],
              "blue_light": shades("b", 0x3A5DB6)["b"], "white": shades("w", 0xC4C0CC)["w"],
              "white_shade": shades("w", 0xA9A5B6)["w"]}
    max_tris = 600
    grip = (0.0, 0.085, CZ)

    def details(self, mb):
        sh = Shield(mb, regular(N, R, (0.0, CZ), PHASE), bend=lambda x, z: 0.055 * (x * x + (z - CZ) ** 2) / (R * R))
        sh.body(0.045, 0.02, 0.03, "steel", "steel_shade", paint, bevel=0.018, rings=(0.55,),
                rim_paint=lambda i: ("steel", "steel_shade", "steel")[i % 3])
        sh.finish()
        tone(mb, sh.boss(0.0, CZ, [(0.092, 0.0), (0.088, 0.016), (0.055, 0.046), (0.0, 0.058)], "steel",
                         phase=math.pi / 8), "steel", seed=9, share=0.7)
        for k in range(6):
            a = PHASE + (k + 0.5) * math.tau / 6
            sh.stud(0.345 * math.sin(a), CZ + 0.345 * math.cos(a), 0.012, 0.012, "steel_light", y=-0.02)


SPECS = [RoundBlueShield()]
