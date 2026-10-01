"""Spiked shield (reference 21): a sharply creased shield, red on the left
half and dark grey on the right, with a dark steel rim carrying six big
spikes, a steel spine down the crease and a central spike."""

from mathutils import Vector

import studies
from _parts_b import Shield, mirrored, shades, spike, tone

OUTLINE = mirrored([(0.0, 0.84), (0.16, 0.83), (0.29, 0.71), (0.32, 0.5), (0.26, 0.28), (0.13, 0.1), (0.0, 0.0)])
FOLD = [((0.0, 0.0), (1.0, 0.0))]
CENTER = (0.0, 0.47)
# Rim spikes of the right side (mirrored to the left): (x, z, direction).
SPIKES = [(0.225, 0.775, (0.6, -0.75, 0.62)), (0.312, 0.53, (1.0, -0.75, 0.08)), (0.2, 0.19, (0.72, -0.75, -0.5))]


class SpikedShield(studies.Spec):
    name = "w21_spiked_shield"
    colors = {**shades("steel", 0x6C6A84, 0.42), **shades("red", 0xC6242C, 0.08), "dark": shades("d", 0x5A5164)["d"]}
    max_tris = 600
    grip = (0.0, 0.03, 0.45)

    def details(self, mb):
        sh = Shield(mb, OUTLINE, bend=lambda x, z: 0.22 * abs(x))
        sh.body(0.045, 0.022, 0.03, "steel", "steel_shade", lambda x, z: "red" if x < 0.0 else "dark", bevel=0.014,
                center=CENTER, rim_paint=lambda i: ("steel", "steel_shade")[i % 2])
        tone(mb, sh._verts(), "red", seed=2, share=0.7)
        sh.strip([(0.0, 0.8), (0.0, 0.05)], 0.032, "steel", height=0.01)
        sh.emblem([(0.0, 0.47), (0.042, 0.41), (0.0, 0.07), (-0.042, 0.41)], "steel_light", height=0.012, lift=0.008)
        sh.finish(FOLD)
        c = sh.at(CENTER[0], CENTER[1], -0.015)
        spike(mb, c, c + Vector((0.0, -0.15, 0.0)), 0.075, "steel_light")
        for x, z, d in SPIKES:
            for s in (-1, 1):
                base = sh.at(x * s, z, -0.012)
                tip = base + Vector((d[0] * s, d[1], d[2])).normalized() * 0.135
                spike(mb, base - (tip - base) * 0.12, tip, 0.08, "steel_light")
        for s in (-1, 1):
            sh.stud(0.075 * s, 0.092, 0.012, 0.012, "steel_light", y=-0.022)
            sh.stud(0.16 * s, 0.17, 0.012, 0.012, "steel_light", y=-0.022)


SPECS = [SpikedShield()]
