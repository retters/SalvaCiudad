"""Tower shield (reference 26): a tall wooden shield creased down the
middle, with steel bands on top, middle and bottom, riveted corner plates
and a diamond stud with a long blade on the crease."""

import math

from mathutils import Vector

import studies
from _parts_b import Shield, mirrored, shades, spike

W, TOP, PEAK = 0.27, 1.15, 1.2
OUTLINE = mirrored([(0.0, PEAK), (W, TOP), (W, 0.07), (0.0, 0.0)])
FOLD = [((0.0, 0.0), (1.0, 0.0))]
GROOVES = (-0.18, -0.09, 0.09, 0.18)
BORDERS = (-0.18, -0.09, 0.0, 0.09, 0.18)
PLANKS = ("wood", "wood_light", "wood", "wood_shade", "wood", "wood_shade")


def paint(x, z):
    for g in GROOVES:
        if abs(x - g) < 0.004:
            return "groove"
    return PLANKS[sum(x > b for b in BORDERS)]


def edge(x):
    """The height of the top edge at x."""
    return PEAK - abs(x) * (PEAK - TOP) / W


def rect(x0, x1, z0, z1):
    return [(x0, z0), (x1, z0), (x1, z1), (x0, z1)]


class TowerShield(studies.Spec):
    name = "w26_tower_shield"
    colors = {**shades("wood", 0x8D5235, 0.14), **shades("steel", 0x77737F, 0.2), "groove": shades("g", 0x2B1F20)["g"]}
    max_tris = 600
    grip = (0.0, 0.03, 0.62)

    def details(self, mb):
        sh = Shield(mb, OUTLINE, bend=lambda x, z: 0.34 * abs(x))
        splits = [((g + s * 0.004, 0.0), (1.0, 0.0)) for g in GROOVES for s in (-1, 1)] + FOLD
        sh.body(0.014, 0.004, 0.03, "wood_shade", "wood_shade", paint, fan=False, splits=splits)
        # Bands: along the top edge, across the upper third and near the bottom.
        sh.emblem([(-W, TOP), (0.0, PEAK), (W, TOP), (W, TOP - 0.085), (0.0, PEAK - 0.085), (-W, TOP - 0.085)],
                  "steel_shade")
        sh.emblem(rect(-W, W, 0.84, 0.92), "steel_shade")
        sh.emblem(rect(-W, W, 0.13, 0.21), "steel_shade")
        sh.emblem([(-0.075, 0.21), (0.075, 0.21), (0.075, 0.09), (0.0, 0.0), (-0.075, 0.09)], "steel", lift=0.008)
        sh.emblem([(-0.075, edge(0.075)), (0.0, PEAK), (0.075, edge(0.075)), (0.075, 1.05), (0.0, 1.015),
                   (-0.075, 1.05)], "steel", lift=0.008)
        sh.emblem([(-0.042, 0.86), (0.042, 0.86), (0.024, 0.5), (0.0, 0.36), (-0.024, 0.5)], "steel_light",
                  height=0.016, lift=0.008)
        rivets = [(0.0, 1.105), (0.0, 0.125)]
        for s in (-1, 1):
            x0, x1 = sorted((0.165 * s, W * s))
            sh.emblem([(x0, 1.03), (x1, 1.03), (x1, edge(x1)), (x0, edge(x0))], "steel", lift=0.008)
            sh.emblem(rect(x0, x1, 0.815, 0.945), "steel", lift=0.008)
            sh.emblem(rect(x0, x1, 0.105, 0.235), "steel", lift=0.008)
            rivets += [(0.218 * s, 1.09), (0.218 * s, 0.88), (0.218 * s, 0.17)]
        sh.finish(FOLD)
        for x, z in rivets:
            sh.stud(x, z, 0.03, 0.03, "steel_light", y=-0.02, phase=math.pi / 4 if x else 0.0)
        c = sh.at(0.0, 0.88, -0.02)
        spike(mb, c, c + Vector((0.0, -0.075, 0.0)), 0.088, "steel_light")


SPECS = [TowerShield()]
