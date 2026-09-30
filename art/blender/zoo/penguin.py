"""Penguin: a standing king penguin. Dark navy back and head, white belly,
an orange-yellow patch on the upper chest and behind the eyes, a long dark
beak with an orange stripe, flippers hanging at the sides and dark feet."""

import random

import common
import studies

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
        mb.cylinder((0, -0.11, 0.835), (0, -0.265, 0.795), 0.028, 0.004, "beak", segments=6)
        mb.cylinder((0, -0.105, 0.822), (0, -0.235, 0.79), 0.024, 0.003, "orange", segments=5)
        for s in (-1, 1):
            mb.sphere((s * EYE[0], EYE[1], EYE[2]), 0.014, "eye", segments=6, rings=4)
            # Flipper hanging down along the side, a little out from the body.
            studies.plate(mb, [(s * 0.145, -0.02, 0.64), (s * 0.165, 0.07, 0.6), (s * 0.215, 0.1, 0.36),
                               (s * 0.235, 0.07, 0.22), (s * 0.21, 0.0, 0.36)], 0.02, "navy")
            # Foot: a flat dark paddle with three toes.
            studies.plate(mb, [(s * 0.04, -0.02, 0.0), (s * 0.13, -0.02, 0.0), (s * 0.15, -0.13, 0.0),
                               (s * 0.09, -0.17, 0.0), (s * 0.03, -0.12, 0.0)], 0.04, "foot")
        # A short stiff tail at the back, touching the ground.
        studies.plate(mb, [(-0.06, 0.15, 0.1), (0.06, 0.15, 0.1), (0.03, 0.22, 0.0), (-0.03, 0.22, 0.0)],
                      0.025, "navy")


SPECS = [Penguin()]
