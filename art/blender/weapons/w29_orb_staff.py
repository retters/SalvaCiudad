"""Weapon 29: orb staff. A dark purple-grey staff ending in a claw of four
blunt prongs over a shallow cup that hold a big faceted purple orb; a purple ribbon
around the middle, a purple band and a faceted pommel at the bottom."""

import math

import common
import studies
import _parts_c as parts

SHAFT = [((0.01, 0.0, 0.1), 0.031), ((-0.008, 0.0, 0.42), 0.036), ((0.01, 0.004, 0.8), 0.041),
         ((-0.006, 0.0, 1.15), 0.045), ((0.0, 0.0, 1.4), 0.05)]
HUB_Z = 1.42
ORB = ((0.0, 0.0, 1.635), 0.135)


def prong(angle, reach, height, thick):
    """One claw: out under the orb, up beside it and in over it, blunt."""
    c, s = math.cos(angle), math.sin(angle)
    path = [(0.03, HUB_Z, thick), (reach * 0.82, HUB_Z + 0.05, thick), (reach, HUB_Z + 0.15, thick * 0.95),
            (reach * 0.97, HUB_Z + height * 0.75, thick * 0.9), (reach * 0.8, HUB_Z + height, thick * 0.8)]
    return parts.chain([((c * r, s * r, z), t) for r, z, t in path])


class OrbStaff(studies.Spec):
    name = "w29_orb_staff"
    colors = {
        **parts.shades("dark", 0x4E4462, shade=0x33294A),
        **parts.shades("orb", 0x8440DC, 0xAE7CEE, 0x5E1EB0),
        "ribbon": common.rgb(0x8E4FD6),
        "glint": common.rgb(0xE9D6F2),
    }
    capsules = (parts.chain(SHAFT) + prong(0.0, 0.168, 0.31, 0.046) + prong(math.pi, 0.168, 0.31, 0.046)
                + prong(-math.pi / 2, 0.135, 0.17, 0.03) + prong(math.pi / 2, 0.135, 0.17, 0.03))
    ellipsoids = [((0.0, 0.0, 1.38), (0.058, 0.055, 0.05)),   # The knot under the claw.
                  ((0.0, 0.0, 1.47), (0.115, 0.115, 0.045))]   # The cup under the orb.
    remesh_voxel = 0.009
    budget = 280
    max_tris = 600
    grip = (0.0, 0.0, 0.9)

    def paint(self, c, n):
        return "dark"

    def details(self, mb):
        parts.begin(mb, self)
        parts.retone(mb, "dark", 0.5)
        parts.ico(mb, ORB[0], ORB[1], "orb", subdiv=2, tilt=0.3)
        # A pale glint facet near the top of the orb, as in the picture.
        parts.spike(mb, (0.035, -0.095, 1.7), (0.045, -0.125, 1.725), 0.03, "glint", sides=3, tones=None)
        axis = parts.along(SHAFT)
        pts, normals = parts.helix(axis, 0.66, 1.06, 1.2, 12, phase=2.2)
        parts.ribbon(mb, pts, normals, 0.065, 0.009, "ribbon", sink=0.014)
        # The bottom: a purple band over a faceted pommel.
        parts.wrap(mb, (0.008, 0, 0.15), (0.006, 0, 0.23), 0.04, 2, "ribbon", seed=2)
        parts.loft(mb, [(0.008, 0, 0.0), (0.008, 0, 0.06), (0.008, 0, 0.13), (0.008, 0, 0.16)],
                   [0.0, 0.05, 0.036, 0.03], 5, "dark", tones="light", phase=0.3)
        parts.spike(mb, (0.008, -0.03, 0.07), (0.008, -0.058, 0.07), 0.016, "glint", sides=4, tones=None,
                    ref=(0, 0, 1))


SPECS = [OrbStaff()]
