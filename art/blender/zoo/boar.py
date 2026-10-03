"""Wild boar: dark brown-grey, built like the pig but wilder: a high
bristly back, a wedge head with a long flat snout, small upright ears,
curved tusks and a thin tail with a dark tuft."""

from mathutils import Vector

import common
import rigs
import studies

X = 0.15  # Half the distance between left and right legs.
LEG_Y, LEG_TOP, LEG_R = (-0.3, 0.42), 0.5, 0.068
HOOF_TOP = 0.07
SNOUT_A, SNOUT_B, SNOUT_R = (0.0, -0.84, 0.54), (0.0, -1.06, 0.45), 0.085
EYE = (0.11, -0.8, 0.7)
TAIL = [(0, 0.6, 0.68), (0, 0.66, 0.58), (0, 0.68, 0.48), (0, 0.69, 0.4)]
MANE = 0.78  # Above this the back is dark and bristly.


class BoarRig(rigs.Quadruped):
    """The pig's template; the long snout needs the head lowered less."""

    def eat_pose(self, t):
        rot, offset, extra = super().eat_pose(t)
        for bone in ("neck", "head"):
            rot[bone] = [(axis, deg * 0.5) for axis, deg in rot[bone]]
        return rot, offset, extra


class Boar(studies.Spec):
    name = "boar"
    colors = {
        "boar": common.rgb(0x5E4A3A),
        "boar_light": common.rgb(0x6A5444),
        "boar_shade": common.rgb(0x523F31),
        "bristle": common.rgb(0x33271F),
        "snout": common.rgb(0x4A3A34),
        "nostril": common.rgb(0x1E1614),
        "tusk": common.rgb(0xE6DCC4),
        "hoof": common.rgb(0x2A2220),
        "eye": common.rgb(0x151012),
    }
    ellipsoids = [
        ((0, 0.12, 0.62), (0.27, 0.5, 0.27)),     # Body and rump.
        ((0, -0.3, 0.68), (0.29, 0.34, 0.31)),    # High shoulders.
        ((0, -0.66, 0.62), (0.19, 0.24, 0.21)),   # Head.
    ]
    capsules = ([(SNOUT_A, SNOUT_B, SNOUT_R * 1.15, SNOUT_R)]
                + [((s * X, y, 0.0), (s * X, y, LEG_TOP + 0.08), LEG_R * 0.85, LEG_R * 1.25)
                   for s in (-1, 1) for y in LEG_Y]
                + [(TAIL[0], TAIL[1], 0.03, 0.02)])
    caps = [(SNOUT_A, (0, -0.93, -0.37), SNOUT_R * 1.5, 0.03, "snout")]
    cuts = [((0, 0, HOOF_TOP), (0, 0, 1), lambda c, n: c.z < 0.2)]
    budget = 650
    max_tris = 1500
    tone_material = "boar"
    rig = BoarRig(
        body=((0, 0.55, 0.62), (0, -0.05, 0.63)),
        chest=((0, -0.05, 0.63), (0, -0.42, 0.66)),
        neck=((0, -0.42, 0.66), (0, -0.58, 0.66)),
        head=((0, -0.58, 0.66), (0, -1.08, 0.46)),
        ears=((0.11, -0.6, 0.8), (0.15, -0.58, 0.95)),
        tail=TAIL,
        legs={
            "F": ((X, LEG_Y[0], 0.56), (X, LEG_Y[0], 0.3), (X, LEG_Y[0], HOOF_TOP), (X, LEG_Y[0] - 0.05, 0.0)),
            "H": ((X, LEG_Y[1], 0.56), (X, LEG_Y[1], 0.3), (X, LEG_Y[1], HOOF_TOP), (X, LEG_Y[1] - 0.05, 0.0)),
        },
        leg_exit=(0.3, 0.4),
        walk=rigs.Gait(speed=0.9, frames=16, duty=0.62, lift=0.06, crouch=0.02, bob=0.008,
                       phases=rigs.WALK_PHASES),
        run=rigs.Gait(speed=2.6, frames=12, duty=0.42, lift=0.1, crouch=0.05, bob=0.015,
                      phases=rigs.TROT_PHASES, nod=5.0, wag=25.0),
        lie_height=0.3,
        blend=0.04,
    )

    def paint(self, c, n):
        if c.z < HOOF_TOP:
            return "hoof"
        if c.z > MANE and -0.6 < c.y < 0.45 and abs(c.x) < 0.14 and n.z > 0.3:
            return "bristle"  # The ridge along the back.
        if c.y > 0.62 and c.z < 0.5:
            return "bristle"  # The tail tuft.
        return "boar"

    def details(self, mb):
        tip = mb.cap_centers[0]
        for s in (-1, 1):
            mb.sphere((s * EYE[0], EYE[1], EYE[2]), 0.022, "eye", segments=6, rings=4)
            mb.sphere((s * 0.03, tip.y - 0.002, tip.z), 0.018, "nostril",
                      segments=6, rings=3, scale=(0.8, 0.4, 1.2))
            # Small upright ears.
            studies.flap(mb, (s * 0.06, -0.62, 0.8), (s * 0.15, -0.58, 0.77), (s * 0.15, -0.6, 0.95),
                         0.025, "boar")
            # Tusks: two short cones curving up and back from the snout's sides.
            pts = [Vector((s * 0.085, -0.95, 0.46)), Vector((s * 0.115, -0.94, 0.52)),
                   Vector((s * 0.12, -0.9, 0.57))]
            for (p, q), (ra, rb) in zip(zip(pts, pts[1:]), ((0.018, 0.012), (0.012, 0.004))):
                mb.cylinder(p, q, ra, rb, "tusk", segments=5)
        # The tuft at the tail's end.
        for p, q in zip(TAIL[1:], TAIL[2:]):
            mb.cylinder(p, q, 0.025, 0.035, "bristle", segments=5)


SPECS = [Boar()]
