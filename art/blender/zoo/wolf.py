"""Wolf: blue-grey with a light belly, throat, cheeks, muzzle and lower
legs, tall pointy ears and a bushy tail with a dark tip."""

from mathutils import Vector

import common
import studies

X = 0.13  # Half the distance between left and right legs.
HEAD = ((0, -0.69, 0.87), (0.14, 0.14, 0.13))
SNOUT_A, SNOUT_B = (0, -0.78, 0.84), (0, -0.94, 0.8)
SOCK = 0.2  # Below this the legs are light.
TAIL = [(0, 0.5, 0.66), (0, 0.7, 0.56), (0, 0.84, 0.4), (0, 0.9, 0.26)]
TAIL_R = [0.05, 0.08, 0.075, 0.045]


def legs_capsules():
    caps = []
    for s in (-1, 1):
        x = s * X
        caps += [
            ((x * 0.9, -0.33, 0.62), (x, -0.35, 0.3), 0.075, 0.055),    # Front upper leg.
            ((x, -0.35, 0.3), (x, -0.37, 0.06), 0.048, 0.042),          # Front lower leg.
            ((x, -0.36, 0.04), (x, -0.44, 0.04), 0.045, 0.04),          # Front paw.
            ((x * 0.9, 0.36, 0.52), (x, 0.48, 0.24), 0.08, 0.05),       # Hind leg to the hock.
            ((x, 0.48, 0.24), (x, 0.44, 0.06), 0.045, 0.042),           # Hind lower leg.
            ((x, 0.45, 0.04), (x, 0.37, 0.04), 0.044, 0.04),            # Hind paw.
        ]
    return caps


class Wolf(studies.Spec):
    name = "wolf"
    max_tris = 1500
    budget = 800
    colors = {
        "grey": common.rgb(0x8A93A2),
        "grey_light": common.rgb(0x99A2B0),
        "grey_shade": common.rgb(0x7A8292),
        "dark": common.rgb(0x565D6A),
        "light": common.rgb(0xE8E6E1),
        "nose": common.rgb(0x1E1C1E),
        "eye": common.rgb(0x151012),
    }
    ellipsoids = [
        ((0, -0.26, 0.61), (0.19, 0.32, 0.24)),    # Chest.
        ((0, 0.02, 0.61), (0.16, 0.3, 0.17)),      # Belly.
        ((0, 0.3, 0.61), (0.16, 0.27, 0.19)),      # Hips.
        ((X * 0.8, 0.36, 0.52), (0.08, 0.15, 0.17)),   # Thighs.
        ((-X * 0.8, 0.36, 0.52), (0.08, 0.15, 0.17)),
        ((0, -0.5, 0.72), (0.18, 0.16, 0.22)),      # Neck ruff.
        HEAD,
    ]
    capsules = ([((0, -0.42, 0.66), (0, -0.62, 0.82), 0.15, 0.13), (SNOUT_A, SNOUT_B, 0.08, 0.052)]
                + legs_capsules()
                + [(a, b, ra, rb) for a, b, ra, rb in zip(TAIL, TAIL[1:], TAIL_R, TAIL_R[1:])])
    cuts = [((0, 0, SOCK), (0, 0, 1), lambda c, n: c.z < SOCK + 0.1 and abs(c.y) > 0.25)]
    tone_material = "grey"

    def paint(self, c, n):
        if c.y > 0.75 and c.z < 0.34:
            return "dark"  # Tail tip.
        if c.z < SOCK and abs(c.y) > 0.25 and c.y < 0.6:
            return "light"  # Lower legs.
        if c.y < -0.8 and c.z < 0.83:
            return "light"  # Muzzle and jaw.
        if c.y < -0.62 and abs(c.x) > 0.07 and c.z < 0.86:
            return "light"  # Cheeks.
        if c.y < -0.38 and c.z < 0.74 and abs(c.x) < 0.13 and n.y < 0.2 and n.z < 0.4:
            return "light"  # Throat and chest.
        if -0.4 < c.y < 0.5 and c.z < 0.5 and n.z < -0.1 and abs(c.x) < 0.11:
            return "light"  # Belly.
        if c.z > 0.76 and -0.35 < c.y < 0.45 and n.z > 0.5:
            return "dark"  # Saddle along the back.
        return "grey"

    def details(self, mb):
        for s in (-1, 1):
            mb.sphere((s * 0.062, -0.81, 0.91), 0.017, "eye", segments=6, rings=4)
            a, b, tip = (Vector((s * 0.035, -0.69, 0.97)), Vector((s * 0.12, -0.66, 0.93)),
                         Vector((s * 0.1, -0.7, 1.1)))
            studies.flap(mb, a, b, tip, 0.025, "grey")
            inner = [p + Vector((0, -0.016, 0)) for p in (a, b, tip)]
            mid = sum(inner, Vector()) / 3
            studies.flap(mb, *[mid + (p - mid) * 0.6 for p in inner], 0.015, "dark")
        mb.sphere((0, -0.99, 0.815), 0.032, "nose", segments=6, rings=4, scale=(1.0, 0.7, 0.7))


SPECS = [Wolf()]
