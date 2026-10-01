"""Sun shield (reference 27): a small round shield of dark brown planks
with a faceted gold rim, eight gold rivets and a raised gold sun."""

import math

from mathutils import Vector

import studies
from _parts_b import Shield, regular, shades, tone

R = 0.325
CZ = R * math.cos(math.pi / 16)      # The center: the lowest corners stand on Z = 0.
GROOVES = (-0.165, -0.055, 0.055, 0.165)     # Plank borders (x).
PLANKS = ("wood_shade", "wood", "wood_light", "wood", "wood_shade")


def paint(x, z):
    for g in GROOVES:
        if abs(x - g) < 0.004:
            return "groove"
    return PLANKS[sum(x > g for g in GROOVES)]


def ray(mb, sh, center, angle, r0, r1, half, height, mats):
    """A ray of the sun: a low ridge from the disk to its point."""
    out = Vector((math.sin(angle), 0.0, math.cos(angle)))
    side = Vector((out.z, 0.0, -out.x))
    c = Vector((center[0], 0.0, center[1]))
    left, right, tip = c + out * r0 - side * half, c + out * r0 + side * half, c + out * r1
    ridge = c + out * r0 + Vector((0.0, -height, 0.0))
    v = [mb.bm.verts.new(sh.at(p.x, p.z, p.y - 0.001)) for p in (left, right, tip, ridge)]
    for a, b, d, mat in ((0, 3, 2, mats[0]), (3, 1, 2, mats[1]), (0, 1, 3, mats[0]), (1, 0, 2, mats[0])):
        mb.bm.faces.new((v[a], v[b], v[d])).material_index = mb._material_index(mat)
    return v


class SunShield(studies.Spec):
    name = "w27_sun_shield"
    colors = {**shades("gold", 0xE5A62E, 0.3), **shades("wood", 0x673E27, 0.14), "groove": shades("g", 0x3A2014)["g"]}
    max_tris = 600
    grip = (0.0, 0.03, CZ)

    def details(self, mb):
        sh = Shield(mb, regular(16, R, (0.0, CZ), math.pi / 16))
        splits = [((g + s * 0.004, 0.0), (1.0, 0.0)) for g in GROOVES for s in (-1, 1)]
        sh.body(0.052, 0.022, 0.03, "gold", "wood_shade", paint, bevel=0.018, fan=False, splits=splits,
                rim_paint=lambda i: ("gold", "gold_shade", "gold", "gold_light")[i % 4])
        sh.finish()
        for k in range(8):
            a = k * math.tau / 8
            sh.stud(0.298 * math.sin(a), CZ + 0.298 * math.cos(a), 0.016, 0.018, "gold_light", y=-0.022,
                    phase=math.pi / 4)
            ray(mb, sh, (0.0, CZ), a, 0.085, 0.19 if k % 2 == 0 else 0.172, 0.032, 0.026,
                ("gold_light", "gold") if k < 4 else ("gold", "gold_shade"))
        tone(mb, sh.boss(0.0, CZ, [(0.1, 0.0), (0.075, 0.036), (0.0, 0.054)], "gold", phase=math.pi / 8),
             "gold", seed=2, share=0.6)


SPECS = [SunShield()]
