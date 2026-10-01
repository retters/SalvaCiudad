"""Weapon 28: crystal staff. A gnarled brown staff whose top forks into
wooden prongs that hold a big blue crystal; a gold binding under the fork,
a blue ribbon and a thin gold strand wound around the shaft."""

import math

import common
import studies
import _parts_c as parts

# The shaft, from the bottom up: slightly crooked and knotty.
SHAFT = [((0.014, 0.0, 0.02), 0.03), ((-0.01, 0.004, 0.3), 0.039), ((0.014, -0.004, 0.62), 0.037),
         ((-0.014, 0.0, 0.95), 0.042), ((0.004, 0.0, 1.2), 0.04), ((0.0, 0.0, 1.34), 0.046)]
FORK_Z = 1.34
CRYSTAL_Z = (1.37, 1.57, 1.63, 1.84)  # Bottom point, belt bottom, belt top, tip.
CRYSTAL_R = 0.135


def prong(angle, reach, height, thick):
    """One prong of the fork: out, up and back in toward the crystal."""
    c, s = math.cos(angle), math.sin(angle)
    path = [(0.03, FORK_Z, thick), (reach * 0.8, FORK_Z + height * 0.42, thick * 0.92),
            (reach, FORK_Z + height * 0.8, thick * 0.75), (reach * 0.8, FORK_Z + height, thick * 0.5)]
    return parts.chain([((c * r, s * r, z), t) for r, z, t in path])


class CrystalStaff(studies.Spec):
    name = "w28_crystal_staff"
    colors = {
        **parts.shades("wood", 0x8A4721, shade=0x5E2D17),
        **parts.shades("crystal", 0x12A6F4, 0x58CBFF, 0x0B72CB),
        "ribbon": common.rgb(0x1276D0),
        "cord": common.rgb(0xDDB236),     # The gold binding and the thin strand.
    }
    capsules = (parts.chain(SHAFT) + prong(0.0, 0.135, 0.25, 0.03) + prong(math.pi, 0.135, 0.25, 0.03)
                + prong(-math.pi / 2, 0.085, 0.11, 0.026) + prong(math.pi / 2, 0.085, 0.11, 0.026))
    ellipsoids = [((0.0, 0.0, 1.345), (0.055, 0.05, 0.045)),      # The knot under the fork.
                  ((-0.02, -0.012, 0.47), (0.04, 0.036, 0.05)),   # Knots on the shaft.
                  ((0.016, 0.01, 0.84), (0.042, 0.038, 0.05))]
    remesh_voxel = 0.009
    budget = 190
    max_tris = 600
    grip = (0.0, 0.0, 0.95)

    def paint(self, c, n):
        return "wood"

    def details(self, mb):
        parts.begin(mb, self)
        parts.retone(mb, "wood", 0.5)
        z0, z1, z2, z3 = CRYSTAL_Z
        # The crystal: a six-sided bipyramid with a short belt, slightly turned.
        parts.loft(mb, [(0, 0, z0), (0, 0, z1), (0, 0, z2), (0, 0, z3)], [0.0, CRYSTAL_R, CRYSTAL_R * 0.94, 0.0],
                   6, "crystal", phase=0.35, twist=0.0, tones="light")
        # The gold binding under the fork.
        parts.loft(mb, [(0, 0, 1.235), (0, 0, 1.262), (0, 0, 1.29)], [0.05, 0.058, 0.051], 7, "cord")
        axis = parts.along(SHAFT)
        pts, normals = parts.helix(axis, 0.5, 1.22, 2.25, 18, phase=1.0)
        parts.ribbon(mb, pts, normals, 0.05, 0.011, "ribbon")
        pts, normals = parts.helix(axis, 0.6, 1.12, -1.25, 10, phase=2.4)
        parts.ribbon(mb, pts, normals, 0.04, 0.012, "ribbon")
        pts, normals = parts.helix(axis, 0.14, 0.8, 1.5, 11, phase=4.0)
        parts.ribbon(mb, pts, normals, 0.014, 0.012, "cord", sink=0.006)

SPECS = [CrystalStaff()]
