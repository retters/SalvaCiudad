"""Brown bear: heavy and round, with a shoulder hump, thick legs, wide
plantigrade paws, a short lighter muzzle, round ears and a stub tail."""

from mathutils import Vector

import common
import rigs
import studies

X = 0.25  # Half the distance between left and right legs.
PAW_TOP = 0.12  # Where the dark paws start: below it they stay rigid.
HEAD = ((0, -0.95, 0.94), (0.21, 0.2, 0.2))
MUZZLE_A, MUZZLE_B = (0, -1.06, 0.88), (0, -1.25, 0.84)
TAIL = [(0, 0.82, 0.86), (0, 0.89, 0.82), (0, 0.93, 0.77)]


def legs_capsules():
    caps = []
    for s in (-1, 1):
        x = s * X
        caps += [
            ((x * 0.9, -0.45, 0.82), (x, -0.47, 0.42), 0.16, 0.12),     # Front upper leg.
            ((x, -0.47, 0.42), (x, -0.48, 0.1), 0.115, 0.1),            # Front lower leg.
            ((x, -0.46, 0.06), (x, -0.64, 0.05), 0.1, 0.09),            # Front paw.
            ((x * 0.9, 0.5, 0.76), (x, 0.6, 0.4), 0.17, 0.12),          # Hind leg to the hock.
            ((x, 0.6, 0.4), (x, 0.55, 0.1), 0.115, 0.1),                # Hind lower leg.
            ((x, 0.56, 0.06), (x, 0.36, 0.05), 0.1, 0.09),              # Hind paw.
        ]
    return caps


class BearRig(rigs.Beast):
    eat = (6.0, 6.0, 25.0, 15.0)
    eat_drop = 0.05


class Bear(studies.Spec):
    name = "bear"
    max_tris = 1500
    budget = 900
    colors = {
        "bear": common.rgb(0x6B4A32),
        "bear_light": common.rgb(0x7A563C),
        "bear_shade": common.rgb(0x5C3E2A),
        "bear_dark": common.rgb(0x3E2A1E),
        "muzzle": common.rgb(0xA88460),
        "nose": common.rgb(0x1A1412),
        "eye": common.rgb(0x151012),
    }
    ellipsoids = [
        ((0, -0.35, 0.86), (0.36, 0.45, 0.38)),    # Chest and shoulders.
        ((0, -0.4, 1.06), (0.25, 0.3, 0.18)),      # The hump.
        ((0, 0.1, 0.83), (0.34, 0.45, 0.34)),      # Belly.
        ((0, 0.5, 0.84), (0.33, 0.36, 0.33)),      # Hips.
        HEAD,
    ]
    capsules = ([((0, -0.6, 0.92), (0, -0.85, 0.95), 0.25, 0.2), (MUZZLE_A, MUZZLE_B, 0.11, 0.08)]
                + legs_capsules()
                + [(TAIL[0], TAIL[1], 0.06, 0.045)])
    cuts = [((0, 0, PAW_TOP), (0, 0, 1), lambda c, n: c.z < PAW_TOP + 0.1)]
    tone_material = "bear"
    rig = BearRig(
        body=((0, 0.78, 0.86), (0, 0.05, 0.83)),
        chest=((0, 0.05, 0.83), (0, -0.55, 0.92)),
        neck=((0, -0.55, 0.92), (0, -0.85, 0.95)),
        head=((0, -0.85, 0.95), (0, -1.27, 0.85)),
        ears=((0.13, -0.9, 1.1), (0.15, -0.9, 1.2)),
        tail=TAIL,
        legs={
            "F": ((X, -0.45, 0.82), (X, -0.47, 0.42), (X, -0.47, PAW_TOP), (X, -0.66, 0.0)),
            "H": ((X, 0.5, 0.76), (X, 0.6, 0.4), (X, 0.55, PAW_TOP), (X, 0.34, 0.0)),
        },
        leg_exit=(0.45, 0.58),
        leg_reach=0.26,
        walk=rigs.Gait(speed=1.0, frames=20, duty=0.65, lift=0.08, crouch=0.04, bob=0.012,
                       phases=rigs.WALK_PHASES, wag=4.0),
        run=rigs.Gait(speed=3.5, frames=12, duty=0.35, lift=0.14, crouch=0.08, bob=0.02,
                      phases=rigs.GALLOP_PHASES, nod=4.0, wag=4.0),
        lie_height=0.36,
        blend=0.06,
    )

    def paint(self, c, n):
        if c.z < PAW_TOP:
            return "bear_dark"
        if c.y < -1.07 and c.z < 0.95:
            return "muzzle"
        return "bear"

    def details(self, mb):
        for s in (-1, 1):
            mb.sphere((s * 0.09, -1.1, 1.0), 0.02, "eye", segments=6, rings=4)
            # Round ears: a short flap with a darker inside.
            a, b, tip = (Vector((s * 0.07, -0.9, 1.1)), Vector((s * 0.23, -0.88, 1.05)),
                         Vector((s * 0.16, -0.9, 1.24)))
            studies.flap(mb, a, b, tip, 0.04, "bear")
            inner = [p + Vector((0, -0.02, 0)) for p in (a, b, tip)]
            mid = sum(inner, Vector()) / 3
            studies.flap(mb, *[mid + (p - mid) * 0.55 for p in inner], 0.02, "bear_dark")
        mb.sphere((0, -1.315, 0.87), 0.045, "nose", segments=6, rings=4, scale=(1.1, 0.7, 0.8))


SPECS = [Bear()]
