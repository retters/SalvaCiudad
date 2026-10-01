"""Penguin: a standing king penguin. Dark navy back and head, white belly,
an orange-yellow patch on the upper chest and behind the eyes, a long dark
beak with an orange stripe, flippers hanging at the sides and dark feet."""

import random

import common
import rigs_bird
import studies
from rigs_bird import tag

BODY = ((0.0, 0.02, 0.36), (0.2, 0.19, 0.34))
CHEST = ((0.0, -0.01, 0.58), (0.16, 0.15, 0.2))
HEAD = ((0.0, -0.03, 0.83), (0.105, 0.12, 0.11))
NECK_A, NECK_B = (0.0, 0.0, 0.64), (0.0, -0.02, 0.79)
BELLY_Y = -0.06      # In front of this plane the body is white (below the patch).
PATCH_Z = (0.56, 0.61, 0.73)  # Pale yellow, then orange chest patch up to the top.
EYE = (0.062, -0.117, 0.86)
EAR = (0.075, -0.0, 0.83)  # Center of the orange patch behind the eyes.


def tone_faces(mb, mat, share, seed=11):
    """Facet tones for a second material (finish() only tones one): turns a
    share of its faces into <mat>_light and <mat>_shade."""
    if mat not in mb.materials:
        return
    rnd = random.Random(seed)
    main = mb.materials.index(mat)
    light, shade = mb._material_index(mat + "_light"), mb._material_index(mat + "_shade")
    for f in mb.bm.faces:
        if f.material_index == main:
            r = rnd.random()
            if r < share * 0.5:
                f.material_index = light
            elif r < share:
                f.material_index = shade


class Penguin(studies.Spec):
    name = "penguin"
    colors = {
        "navy": common.rgb(0x2C3A5C),
        "navy_light": common.rgb(0x3A4A70),
        "navy_shade": common.rgb(0x222D4A),
        "white": common.rgb(0xF2F2EE),
        "white_light": common.rgb(0xFAFAF7),
        "white_shade": common.rgb(0xE2E3E0),
        "orange": common.rgb(0xF7A21B),
        "yellow": common.rgb(0xFBD46A),
        "beak": common.rgb(0x1C1C22),
        "foot": common.rgb(0x26262C),
        "eye": common.rgb(0x0C0C10),
    }
    ellipsoids = [BODY, CHEST, HEAD]
    capsules = [(NECK_A, NECK_B, 0.12, 0.085)]
    cuts = [
        ((0, BELLY_Y, 0), (0, 1, 0), lambda c, n: c.z < PATCH_Z[2] + 0.02),
        ((0, 0, PATCH_Z[0]), (0, 0, 1), lambda c, n: c.y < BELLY_Y + 0.02),
        ((0, 0, PATCH_Z[1]), (0, 0, 1), lambda c, n: c.y < BELLY_Y + 0.02),
        ((0, 0, PATCH_Z[2]), (0, 0, 1), lambda c, n: c.y < BELLY_Y + 0.02),
    ]
    budget = 420
    max_tris = 1000
    tone_material = "navy"
    rig = rigs_bird.Bird(
        body=((0, 0.02, 0.15), (0, 0.0, 0.64)),
        neck=[(0, 0.0, 0.64), (0, -0.02, 0.77)],
        head=((0, -0.02, 0.77), (0, -0.1, 0.84)),
        beak_tip=(0, -0.265, 0.795),
        tail=[(0, 0.15, 0.1), (0, 0.22, 0.02)],
        # The legs are hidden in the body: only the feet show.
        legs=((0.085, 0.0, 0.15), (0.085, 0.04, 0.09), (0.085, -0.03, 0.02), (0.09, -0.15, 0.01)),
        wings=[(0.15, 0.02, 0.63), (0.23, 0.08, 0.22)], wing_sides=[(0, 1, 0)], wing_twitch=6.0,
        blend=0.07,
        # A waddle: short steps, the body rocking over each foot, the flippers out a little.
        walk=rigs_bird.Step(frames=16, duty=0.6, crouch=0.0, lift=0.025, waddle=8.0, sway=0.02, wings=14.0,
                            tail=3.0, toe=10.0),
        run=rigs_bird.Step(frames=9, duty=0.55, crouch=0.0, lift=0.03, waddle=11.0, sway=0.022, wings=28.0,
                           lean=6.0, tail=4.0, toe=10.0),
        eat=dict(pitch=20.0, crouch=0.0, head=55.0, curl=25.0, pecks=3),   # Just dips its head.
        air=dict(name="swim", frames=20, beats=1, pitch=86.0, lift=0.15, amp=38.0, mid=0.0, tuck=0.0,
                 foot=80.0, head=18.0, speed=2.0, bob=0.02),
        lie_height=0.19, look=28.0, die_droop=25.0,
    )

    def paint(self, c, n):
        if c.y < BELLY_Y and c.z < PATCH_Z[2]:
            return "white" if c.z < PATCH_Z[0] else "yellow" if c.z < PATCH_Z[1] else "orange"
        if c.z > 0.76 and abs(c.x) > 0.05:
            if ((abs(c.x) - EAR[0]) ** 2 + (c.y - EAR[1]) ** 2 * 0.6 + (c.z - EAR[2]) ** 2) < 0.035 ** 2:
                return "orange"
        return "navy"

    def details(self, mb):
        tone_faces(mb, "white", 0.25)
        # Beak: a long dark cone with a thinner orange lower half.
        tag(mb, mb.cylinder((0, -0.11, 0.835), (0, -0.265, 0.795), 0.028, 0.004, "beak", segments=6), "head")
        tag(mb, mb.cylinder((0, -0.105, 0.822), (0, -0.235, 0.79), 0.024, 0.003, "orange", segments=5), "head")
        for s in (-1, 1):
            side = "L" if s > 0 else "R"
            tag(mb, mb.sphere((s * EYE[0], EYE[1], EYE[2]), 0.014, "eye", segments=6, rings=4), "head")
            # Flipper hanging down along the side, a little out from the body.
            tag(mb, studies.plate(mb, [(s * 0.145, -0.02, 0.64), (s * 0.165, 0.07, 0.6), (s * 0.215, 0.1, 0.36),
                                       (s * 0.235, 0.07, 0.22), (s * 0.21, 0.0, 0.36)], 0.02, "navy"),
                f"wing.{side}")
            # Foot: a flat dark paddle with three toes, lying on the ground
            # (its top where it always was; the lower half used to be buried).
            tag(mb, studies.plate(mb, [(s * 0.04, -0.02, 0.01), (s * 0.13, -0.02, 0.01), (s * 0.15, -0.13, 0.01),
                                       (s * 0.09, -0.17, 0.01), (s * 0.03, -0.12, 0.01)], 0.02, "foot"),
                f"foot.{side}")
        # A short stiff tail at the back, touching the ground.
        tag(mb, studies.plate(mb, [(-0.06, 0.15, 0.1), (0.06, 0.15, 0.1), (0.03, 0.22, 0.014),
                                   (-0.03, 0.22, 0.014)], 0.025, "navy"), "tail")


SPECS = [Penguin()]
