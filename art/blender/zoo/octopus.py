"""Octopus: red-orange, a big upright mantle, big eyes and eight tentacles
that lie on the ground and curl up and outward at their tips; the inner
side of the curls is lighter, as the suckers."""

import math

from mathutils import Vector

import common
import rigs_swim
import studies

MANTLE = ((0.0, 0.06, 0.78), (0.3, 0.33, 0.4))
BODY = ((0.0, 0.0, 0.34), (0.27, 0.27, 0.22))
EYE = (0.13, -0.235, 0.47)
EYE_R = 0.07
ARMS = 8


def arm_path(angle, curl=1.0):
    """Points and radii of one tentacle: out and down from the body onto
    the ground, then curled up and back over itself."""
    d = Vector((math.sin(angle), -math.cos(angle), 0.0))
    side = Vector((d.y, -d.x, 0.0))
    pts = [(0.17, 0.26), (0.3, 0.13), (0.45, 0.065), (0.6, 0.05)]
    out = [(d * r + Vector((0, 0, z)), rad) for (r, z), rad in zip(pts, (0.095, 0.075, 0.06, 0.05))]
    # The curl: a spiral in the vertical plane of the tentacle, shrinking.
    cr, cz, radius = 0.64, 0.17, 0.13
    steps = 7
    for i in range(1, steps + 1):
        t = i / steps
        a = -math.pi / 2 + t * math.pi * 1.5 * curl
        rr = radius * (1.0 - 0.45 * t)
        p = d * (cr + math.cos(a) * rr) + Vector((0, 0, cz + math.sin(a) * rr)) + side * (0.04 * t)
        out.append((p, 0.046 - 0.022 * t))
    return out


ARM_PATHS = [arm_path((i + 0.5) * math.tau / ARMS, 1.0 if i % 2 else 0.8) for i in range(ARMS)]
ARM_JOINTS = (0, 1, 2, 3, 5, 7, 10)  # The points of a path where its bones meet.


def arm_capsules():
    caps = []
    for path in ARM_PATHS:
        for (a, ra), (b, rb) in zip(path, path[1:]):
            caps.append((tuple(a), tuple(b), ra, rb))
    return caps


class Octopus(studies.Spec):
    name = "octopus"
    colors = {
        "red": common.rgb(0xE8452C),
        "red_light": common.rgb(0xF25A3C),
        "red_shade": common.rgb(0xD03A24),
        "sucker": common.rgb(0xF59A6E),
        "eye_white": common.rgb(0xFFE7C2),
        "eye": common.rgb(0x151012),
    }
    ellipsoids = [MANTLE, BODY]
    capsules = arm_capsules()
    budget = 1000
    max_tris = 1500
    tone_material = "red"
    rig = rigs_swim.Tentacled(
        body=((0, 0, 0.26), (0, 0, 0.5)),
        mantle=((0, 0.03, 0.5), (0, 0.06, 1.15)),
        mantle_fade=(0.56, 0.72),
        core=((0, 0, 0.3), (0, 0.06, 0.85), 0.25),
        arms=[[path[i] for i in ARM_JOINTS] for path in ARM_PATHS],
    )

    def paint(self, c, n):
        r = math.hypot(c.x, c.y)
        if r > 0.5 and c.z > 0.08:
            # Inside of the curl: faces looking back toward the body.
            radial = Vector((c.x, c.y, 0)).normalized()
            if n.dot(radial) < -0.3 or n.z < -0.5:
                return "sucker"
        return "red"

    def details(self, mb):
        for s in (-1, 1):
            center = Vector((s * EYE[0], EYE[1], EYE[2]))
            mb.sphere(center, EYE_R, "eye_white", segments=8, rings=6)
            mb.sphere(center + Vector((s * 0.005, -0.045, 0.0)), EYE_R * 0.55, "eye", segments=6, rings=4,
                      scale=(1.0, 0.6, 1.0))


SPECS = [Octopus()]
