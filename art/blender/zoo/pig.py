"""Pig: the reference animal for the zoo specs (the one chosen in the
technique studies, version 06). Pink with lighter and darker facets, a flat
snout cut into the surface, dark hooves, drooping ears and a curly tail."""

import math

import common
import rigs
import studies

BODY = ((0.0, 0.08, 0.47), (0.28, 0.45, 0.27))
HEAD = ((0.0, -0.40, 0.54), (0.21, 0.19, 0.2))
SNOUT_A, SNOUT_B, SNOUT_R = (0.0, -0.54, 0.49), (0.0, -0.68, 0.47), 0.095
LEG_X, LEG_Y, LEG_TOP, LEG_R = (-0.14, 0.14), (-0.2, 0.34), 0.36, 0.065
HOOF_TOP = 0.06
EYE = (0.1, -0.555, 0.6)


def tail_points():
    """A small curl: points along a helix behind the rump."""
    pts = []
    for i in range(10):
        t = i / 9.0
        ang = t * math.pi * 2.6
        pts.append((0.045 * math.sin(ang), 0.47 + 0.08 * t + 0.03 * (1 - math.cos(ang)) * 0.5,
                    0.53 + 0.045 * math.cos(ang) - 0.02 * t))
    return pts


TAIL = tail_points()


class Pig(studies.Spec):
    name = "pig"
    colors = {
        "pig": common.rgb(0xF2A0AC),
        "pig_light": common.rgb(0xF7B4BE),
        "pig_shade": common.rgb(0xE38E9B),
        "snout": common.rgb(0xE07F8E),
        "nostril": common.rgb(0x8A3A48),
        "hoof": common.rgb(0x9A5A62),
        "eye": common.rgb(0x151012),
    }
    ellipsoids = [BODY, HEAD]
    capsules = [(SNOUT_A, SNOUT_B, SNOUT_R, SNOUT_R)] + [
        ((x, y, 0.0), (x, y, LEG_TOP + 0.08), LEG_R * 0.9, LEG_R * 1.15) for x in LEG_X for y in LEG_Y]
    caps = [(SNOUT_A, (0, -1, 0), SNOUT_R * 1.5, 0.035, "snout")]
    cuts = [((0, 0, HOOF_TOP), (0, 0, 1), lambda c, n: c.z < 0.2)]
    budget = 600
    max_tris = 1500
    tone_material = "pig"
    rig = rigs.Quadruped(
        body=((0, 0.36, 0.47), (0, -0.08, 0.48)),
        chest=((0, -0.08, 0.48), (0, -0.26, 0.5)),
        neck=((0, -0.26, 0.5), (0, -0.38, 0.54)),
        head=((0, -0.38, 0.54), (0, -0.7, 0.48)),
        ears=((0.1, -0.4, 0.69), (0.19, -0.53, 0.84)),
        tail=[TAIL[0], TAIL[3], TAIL[6], TAIL[9]],
        legs={
            "F": ((0.14, -0.2, 0.44), (0.14, -0.2, 0.24), (0.14, -0.2, HOOF_TOP), (0.14, -0.24, 0.0)),
            "H": ((0.14, 0.34, 0.44), (0.14, 0.34, 0.24), (0.14, 0.34, HOOF_TOP), (0.14, 0.3, 0.0)),
        },
        leg_exit=(0.2, 0.26),
        walk=rigs.Gait(speed=0.7, frames=16, duty=0.62, lift=0.05, crouch=0.02, bob=0.008,
                       phases=rigs.WALK_PHASES),
        run=rigs.Gait(speed=1.6, frames=14, duty=0.42, lift=0.08, crouch=0.05, bob=0.015,
                      phases=rigs.TROT_PHASES, nod=5.0, wag=25.0),
        lie_height=0.28,
        blend=0.04,
    )

    def paint(self, c, n):
        return "hoof" if c.z < HOOF_TOP else "pig"

    def details(self, mb):
        tip = mb.cap_centers[0]
        for s in (-1, 1):
            mb.sphere((s * EYE[0], EYE[1], EYE[2]), 0.024, "eye", segments=6, rings=4)
            mb.sphere((s * 0.035, tip.y - 0.002, SNOUT_B[2] + 0.005), 0.02, "nostril",
                      segments=6, rings=3, scale=(0.8, 0.4, 1.2))
            studies.flap(mb, (s * 0.05, -0.41, 0.71), (s * 0.18, -0.35, 0.65), (s * 0.19, -0.53, 0.84),
                         0.03, "pig")
        for p, q in zip(TAIL, TAIL[1:]):
            mb.cylinder(p, q, 0.018, 0.016, "pig", segments=5)


SPECS = [Pig()]
