"""Deer: slim brown stag with a light belly, throat and rump, dark hooves,
big side ears and branching antlers made of thin cylinders."""

import common
import rigs
import studies
from tiger import GALLOP_PHASES, Beast

X = 0.11  # Half the distance between left and right legs.
HEAD = ((0, -0.66, 1.48), (0.085, 0.12, 0.09))
HOOF_TOP = 0.07


def legs_capsules():
    caps = []
    for s in (-1, 1):
        x = s * X
        caps += [
            ((x * 0.9, -0.36, 0.9), (x, -0.38, 0.56), 0.075, 0.044),     # Front upper leg.
            ((x, -0.38, 0.56), (x, -0.4, 0.02), 0.037, 0.032),           # Front lower leg.
            ((x * 0.9, 0.34, 0.92), (x, 0.46, 0.52), 0.095, 0.042),      # Hind leg to the hock.
            ((x, 0.46, 0.52), (x, 0.4, 0.02), 0.037, 0.032),             # Hind lower leg.
        ]
    return caps


def antler(s):
    """Segments (a, b, radius a, radius b) of one antler: a beam curving up
    and back with tines pointing forward and up."""
    beam = [(s * 0.045, -0.62, 1.55), (s * 0.13, -0.6, 1.68), (s * 0.2, -0.56, 1.8), (s * 0.25, -0.5, 1.92),
            (s * 0.27, -0.44, 2.02)]
    radii = [0.022, 0.019, 0.016, 0.013, 0.01]
    segs = [(a, b, ra, rb) for a, b, ra, rb in zip(beam, beam[1:], radii, radii[1:])]
    tines = [(1, (s * 0.1, -0.73, 1.76)), (2, (s * 0.15, -0.66, 1.93)), (3, (s * 0.2, -0.56, 2.03)),
             (3, (s * 0.36, -0.46, 2.0))]
    for i, tip in tines:
        segs.append((beam[i], tip, radii[i] * 0.85, 0.007))
    return segs


class DeerRig(Beast):
    tail_reach = 0.07
    eat = (8.0, 16.0, 97.0, -55.0)   # The long neck swings all the way down to graze.
    eat_drop = 0.05
    die_lift = 4.0                   # The head ends propped on the lower antler,
    die_untwist = 46.0               # not with it sunk in the ground.


class Deer(studies.Spec):
    name = "deer"
    max_tris = 1500
    budget = 730
    remesh_voxel = 0.012  # Fine enough for the slim legs.
    colors = {
        "brown": common.rgb(0xB06A34),
        "brown_light": common.rgb(0xBF7A42),
        "brown_shade": common.rgb(0x9C5B2A),
        "cream": common.rgb(0xEBD7B4),
        "hoof": common.rgb(0x3A2A22),
        "antler": common.rgb(0x6E4B2C),
        "nose": common.rgb(0x1E1A18),
        "eye": common.rgb(0x151012),
    }
    ellipsoids = [
        ((0, -0.27, 0.94), (0.17, 0.31, 0.22)),    # Chest.
        ((0, 0.02, 0.93), (0.16, 0.3, 0.2)),      # Belly.
        ((0, 0.3, 0.96), (0.16, 0.27, 0.2)),      # Hips.
        HEAD,
    ]
    capsules = ([((0, -0.42, 1.0), (0, -0.62, 1.42), 0.13, 0.075),     # Neck.
                 ((0, -0.72, 1.47), (0, -0.87, 1.41), 0.068, 0.042),    # Snout.
                 ((0, 0.52, 1.07), (0, 0.6, 1.0), 0.05, 0.035)]         # Tail.
                + legs_capsules())
    cuts = [((0, 0, HOOF_TOP), (0, 0, 1), lambda c, n: c.z < 0.2)]
    tone_material = "brown"
    rig = DeerRig(
        body=((0, 0.5, 0.98), (0, 0.0, 0.95)),
        chest=((0, 0.0, 0.95), (0, -0.42, 1.0)),
        neck=((0, -0.42, 1.0), (0, -0.62, 1.42)),
        head=((0, -0.62, 1.42), (0, -0.9, 1.42)),
        ears=((0.06, -0.59, 1.53), (0.2, -0.6, 1.61)),
        tail=[(0, 0.52, 1.07), (0, 0.56, 1.035), (0, 0.6, 1.0)],
        legs={
            "F": ((X, -0.37, 0.9), (X, -0.38, 0.56), (X, -0.4, HOOF_TOP), (X, -0.44, 0.0)),
            "H": ((X, 0.38, 0.92), (X, 0.46, 0.52), (X, 0.406, HOOF_TOP), (X, 0.37, 0.0)),
        },
        leg_exit=(0.62, 0.74),
        leg_reach=0.2,
        walk=rigs.Gait(speed=1.2, frames=18, duty=0.62, lift=0.1, crouch=0.06, bob=0.01,
                       phases=rigs.WALK_PHASES, wag=8.0),
        run=rigs.Gait(speed=6.0, frames=10, duty=0.28, lift=0.2, crouch=0.1, bob=0.02,
                      phases=GALLOP_PHASES, nod=4.0, wag=6.0),
        lie_height=0.2,
        blend=0.05,
    )

    def paint(self, c, n):
        if c.z < HOOF_TOP:
            return "hoof"
        if c.y > 0.5 and n.y > 0.2 and c.z > 0.8:
            return "cream"  # Rump and tail.
        if -0.4 < c.y < 0.45 and c.z < 0.82 and n.z < -0.2 and abs(c.x) < 0.13:
            return "cream"  # Belly.
        if -0.75 < c.y < -0.5 and 1.22 < c.z < 1.43 and abs(c.x) < 0.06 and n.y < 0.0 and n.z < 0.3:
            return "cream"  # Throat.
        if c.y < -0.8 and c.z < 1.42:
            return "cream"  # Chin.
        return "brown"

    def details(self, mb):
        for s in (-1, 1):
            mb.sphere((s * 0.068, -0.72, 1.51), 0.017, "eye", segments=6, rings=4)
            studies.flap(mb, (s * 0.05, -0.61, 1.55), (s * 0.07, -0.57, 1.5), (s * 0.21, -0.6, 1.61),
                         0.02, "brown")
            studies.flap(mb, (s * 0.07, -0.615, 1.545), (s * 0.08, -0.59, 1.52), (s * 0.18, -0.607, 1.595),
                         0.012, "cream")
            for a, b, ra, rb in antler(s):
                mb.cylinder(a, b, ra, rb, "antler", segments=4)
        mb.sphere((0, -0.885, 1.425), 0.028, "nose", segments=6, rings=4, scale=(1.0, 0.7, 0.8))


SPECS = [Deer()]
