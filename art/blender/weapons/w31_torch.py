"""Weapon 31: torch. A wooden handle that narrows to a foot with two pale
claws, a leather binding at the middle, a tan band and a dark flared cup,
and a faceted orange flame with a yellow heart and a redder top tongue."""

import common
import studies
import _parts_c as parts


class Torch(studies.Spec):
    name = "w31_torch"
    colors = {
        **parts.shades("wood", 0x8A4C2C, shade=0x5C3220),    # The shade is also the leather binding.
        "cup": common.rgb(0x5E4C48),
        "band": common.rgb(0xC4A888),                           # The tan band and the claws.
        "flame": common.rgb(0xFA8218),
        "ember": common.rgb(0xF0662C),
        "heart": common.rgb(0xFAD63A),
    }
    max_tris = 600
    grip = (0.0, 0.0, 0.17)

    def details(self, mb):
        parts.begin(mb, self)
        # The handle, slightly crooked, thinner toward the foot.
        parts.loft(mb, [(0.0, 0, 0.03), (0.003, 0, 0.12), (-0.003, 0, 0.26), (0.0, 0, 0.385)],
                   [0.009, 0.015, 0.018, 0.021], 6, "wood", tones=0.5, seed=4, twist=0.25)
        for s in (-1, 1):
            parts.loft(mb, [(s * 0.006, 0, 0.055), (s * 0.012, 0, 0.03), (s * 0.014, 0, 0.0)],
                       [0.006, 0.008, 0.0], 4, "band")
        # The leather binding and its knot.
        parts.wrap(mb, (-0.003, 0, 0.245), (-0.002, 0, 0.3), 0.024, 2, "wood_shade", bulge=0.003, tones=None)
        parts.loft(mb, [(-0.016, -0.022, 0.262), (0.012, -0.024, 0.282)], [0.008, 0.008], 4, "wood_shade",
                   ref=(0, 0, 1))
        # The tan band and the flared cup.
        parts.stack(mb, [(0.375, 0.405, 0.027, 0.028, "band"), (0.405, 0.44, 0.03, 0.04, "cup"),
                         (0.44, 0.458, 0.052, 0.052, "cup")], 7)
        # The flame: a leaning body, side tongues and a yellow heart that shows through front and back.
        parts.loft(mb, [(0.0, 0, 0.452), (-0.004, 0, 0.495), (0.0, 0, 0.535), (0.014, 0, 0.572),
                        (0.038, 0, 0.612), (0.03, 0, 0.648)],
                   [(0.03, 0.03), (0.06, 0.046), (0.05, 0.04), (0.034, 0.03), (0.02, 0.018), 0.0], 6,
                   ["flame", "flame", "flame", "ember", "ember"], tones="light", phase=0.2, twist=0.3)
        parts.spike(mb, (-0.035, 0.0, 0.5), (-0.076, 0.0, 0.578), 0.026, "ember")
        parts.spike(mb, (0.04, 0.004, 0.5), (0.074, 0.0, 0.572), 0.024, "flame")
        parts.spike(mb, (-0.014, 0.008, 0.55), (-0.032, 0.0, 0.618), 0.024, "ember")
        parts.loft(mb, [(0.0, 0, 0.455), (0.0, 0, 0.492), (0.004, 0, 0.53), (0.008, 0, 0.565)],
                   [(0.022, 0.03), (0.046, 0.057), (0.03, 0.046), 0.0], 5, "heart", tones="light", phase=0.628)

SPECS = [Torch()]
