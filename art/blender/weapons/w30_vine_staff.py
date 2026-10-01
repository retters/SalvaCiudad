"""Weapon 30: vine staff. A thick brown staff with a knobby foot and a
two-pronged fork that holds a green crystal; a green vine with leaves winds
around it, and moss grows on the foot and the fork."""

from mathutils import Vector

import studies
import _parts_c as parts

SHAFT = [((0.0, 0.0, 0.06), 0.04), ((0.012, 0.0, 0.3), 0.04), ((-0.012, 0.004, 0.65), 0.046),
         ((0.012, 0.0, 1.0), 0.05), ((-0.004, 0.0, 1.25), 0.05), ((0.0, 0.0, 1.42), 0.052)]
LEFT = [((-0.02, 0.0, 1.4), 0.042), ((-0.105, 0.0, 1.47), 0.04), ((-0.135, 0.0, 1.56), 0.036),
        ((-0.135, 0.0, 1.62), 0.034)]
RIGHT = [((0.02, 0.0, 1.4), 0.042), ((0.11, 0.0, 1.48), 0.04), ((0.14, 0.0, 1.62), 0.036),
         ((0.15, 0.0, 1.76), 0.032)]
VINE = (0.5, 1.43, 2.45, 20, 2.0)  # z0, z1, turns, steps, phase.


class VineStaff(studies.Spec):
    name = "w30_vine_staff"
    colors = {
        **parts.shades("wood", 0x86482A, shade=0x5C301C),
        **parts.shades("vine", 0x5F9A2E, light=0x8CC84A),     # The vine, its leaves and the moss.
        **parts.shades("crystal", 0x2FC457, 0x7BE694, 0x1B8C3C),
    }
    capsules = parts.chain(SHAFT) + parts.chain(LEFT) + parts.chain(RIGHT)
    ellipsoids = [((0.0, 0.0, 0.07), (0.062, 0.056, 0.07)),    # The knobby foot.
                  ((0.02, -0.01, 0.8), (0.05, 0.048, 0.06)),
                  ((0.0, 0.0, 1.41), (0.07, 0.058, 0.055))]
    remesh_voxel = 0.009
    budget = 250
    max_tris = 600
    grip = (0.0, 0.0, 0.95)

    def paint(self, c, n):
        # Moss on the upper faces of the foot and on the prong tips.
        if c.z < 0.13 and n.z > 0.25 and c.x > -0.02:
            return "vine"
        if c.z > 1.58 and c.x < 0 and n.z > 0.3:
            return "vine"
        if c.z > 1.72 and n.z > 0.3:
            return "vine"
        return "wood"

    def details(self, mb):
        parts.begin(mb, self)
        parts.retone(mb, "wood", 0.5)
        # The crystal: a six-sided prism with a pointed top, standing in the fork.
        parts.loft(mb, [(0, 0, 1.45), (0, 0, 1.54), (0.004, 0, 1.66), (0.01, 0, 1.78)],
                   [0.03, 0.068, 0.072, 0.0], 6, "crystal", phase=0.3, tones="light")
        axis = parts.along(SHAFT)
        z0, z1, turns, steps, phase = VINE
        pts, normals = parts.helix(axis, z0, z1, turns, steps, phase=phase, gap=0.006, clear=True)
        radii = [0.007] + [0.016] * (len(pts) - 2) + [0.013]
        parts.loft(mb, pts, radii, 4, "vine", tones=0.6, seed=6, ref=(0, 0, 1))
        for k, up in ((3, 0.03), (7, 0.045), (10, 0.02), (14, 0.05), (18, 0.035)):
            p, d = pts[k], normals[k]
            parts.leaf(mb, p + d * 0.008, p + d * 0.09 + Vector((0, 0, up)), 0.05, "vine", across=(d.y, -d.x, 0.6))


SPECS = [VineStaff()]
