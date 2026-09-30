"""Rabbit: white, sitting upright on its haunches, with long upright ears
(pink on the inside), a pink nose and a round tail."""

from mathutils import Matrix, Vector

import common
import studies

HEAD = ((0.0, -0.1, 0.27), (0.068, 0.078, 0.064))
MUZZLE = ((0.0, -0.162, 0.25), (0.042, 0.036, 0.036))
EYE = (0.047, -0.143, 0.285)
EARS_X = 0.03


def ear(s, lean):
    """Outline of an ear, base on the head top, tip up and a bit back."""
    x0 = s * EARS_X
    pivot = Vector((x0, -0.08, 0.3))
    turn = Matrix.Rotation(s * 0.35, 3, "Z")  # Opened outward a little.
    return [pivot + turn @ (Vector(p) - pivot) for p in (
        (x0 - s * 0.018, -0.1, 0.315), (x0 + s * 0.028, -0.095, 0.315), (x0 + s * (0.035 + lean), -0.06, 0.4),
        (x0 + s * (0.022 + lean * 1.5), -0.04, 0.47), (x0 + s * lean * 1.5, -0.035, 0.48),
        (x0 - s * (0.012 - lean), -0.055, 0.4))]


class Rabbit(studies.Spec):
    name = "rabbit"
    colors = {
        "fur": common.rgb(0xF2F0EE),
        "fur_light": common.rgb(0xFBFAF9),
        "fur_shade": common.rgb(0xDEDBD8),
        "pink": common.rgb(0xF0A3B4),
        "eye": common.rgb(0x151012),
    }
    ellipsoids = [
        ((0.0, 0.03, 0.105), (0.1, 0.12, 0.1)),        # Haunches.
        ((0.0, -0.04, 0.17), (0.078, 0.08, 0.1)),      # Chest.
        ((0.06, 0.04, 0.085), (0.045, 0.1, 0.075)),    # Thighs.
        ((-0.06, 0.04, 0.085), (0.045, 0.1, 0.075)),
        HEAD, MUZZLE,
        ((0.0, -0.13, 0.225), (0.03, 0.03, 0.022)),    # Chin.
        ((0.0, 0.145, 0.08), (0.035, 0.03, 0.035)),    # Tail.
    ]
    capsules = [((0.0, -0.05, 0.2), (0.0, -0.09, 0.26), 0.055, 0.05)] + [  # Neck.
        cap for s in (-1, 1) for cap in (
            ((s * 0.075, 0.06, 0.028), (s * 0.07, -0.07, 0.02), 0.03, 0.022),      # Hind feet.
            ((s * 0.035, -0.08, 0.14), (s * 0.035, -0.105, 0.02), 0.02, 0.018),   # Front legs.
            ((s * 0.035, -0.105, 0.015), (s * 0.035, -0.13, 0.015), 0.018, 0.016),  # Front paws.
        )]
    budget = 420
    max_tris = 800
    tone_material = "fur"
    tones = 0.3

    def paint(self, c, n):
        return "fur"

    def details(self, mb):
        for s in (-1, 1):
            mb.sphere((s * EYE[0], EYE[1], EYE[2]), 0.012, "eye", segments=6, rings=4)
            outer = ear(s, 0.012)
            studies.plate(mb, outer, 0.012, "fur")
            # The pink inside, a smaller copy just in front of the ear.
            mid = sum(outer, Vector()) / len(outer)
            inner = [mid + (p - mid) * 0.7 + Vector((0, -0.007, 0)) for p in outer]
            studies.plate(mb, inner, 0.006, "pink")
        mb.sphere((0.0, -0.197, 0.262), 0.012, "pink", segments=6, rings=3, scale=(1.2, 0.6, 0.8))


SPECS = [Rabbit()]
