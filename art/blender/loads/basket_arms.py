"""Load: a round woven basket with a handle, full of food, held in the
arms.

Placement (see _load_kit): the basket lies wholly in front of the plane
Y = 0 (toward -Y, in front of the character) and stands on Z = 0. `grip` =
(0, 0, 0.14) is the point that touches the middle of the character's
chest; the bottom of the basket rests on the hands.
Size: 0.42 wide (X), 0.40 deep (Y), 0.34 high (Z, the handle included; the
basket's rim is at 0.17).
"""

import math

import studies
import _load_kit as kit

CENTER = (0.0, -0.21, 0.0)


class BasketArms(studies.Spec):
    name = "basket_arms"
    colors = kit.colors("wicker", "carrot", "tomato", "leaf", "bread")
    max_tris = 320
    grip = (0.0, 0.0, kit.ARMS_GRIP_Z)

    def details(self, mb):
        kit.lathe(mb, CENTER, [(0.12, 0.0, "wicker_dark"), (0.15, 0.03, "wicker"), (0.18, 0.09, "wicker_dark"),
                               (0.192, 0.14, "wicker"), (0.205, 0.14, "wicker_dark"), (0.205, 0.17, "wicker_dark"),
                               (0.18, 0.17, "wicker_dark"), (0.18, 0.145, "leaf_dark")], 8, squash=0.95)
        # The handle: an arch from side to side over the food.
        arch = [(0.195 * math.cos(a), CENTER[1], 0.155 + 0.17 * math.sin(a))
                for a in [math.pi * i / 6 for i in range(7)]]
        kit.strap(mb, arch, (0, 1, 0), 0.035, 0.014, "wicker_dark", closed=False)
        kit.bread(mb, (-0.13, -0.27, 0.17), (0.07, -0.3, 0.2), 0.048)
        kit.carrot(mb, (0.13, -0.15, 0.21), (-0.01, -0.2, 0.17))
        kit.tomato(mb, (-0.09, -0.15, 0.185), 0.047, 1)
        kit.tomato(mb, (0.0, -0.11, 0.18), 0.045, 2)
        kit.tomato(mb, (0.1, -0.27, 0.185), 0.047, 3)
        kit.greens(mb, (0.05, -0.12, 0.16), 0.13, 0.06)


SPECS = [BasketArms()]
