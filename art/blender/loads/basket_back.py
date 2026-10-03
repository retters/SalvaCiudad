"""Load: a woven basket backpack with vegetables and bread showing, held
by a leather belt.

Placement (see _load_kit): the basket lies wholly behind the plane Y = 0
(toward +Y, behind the character) and stands on Z = 0. `grip` =
(0, 0, 0.25) is the point that touches the middle of the character's back.
Size: 0.46 wide (X), 0.40 deep (Y), 0.62 high (Z, the food included; the
basket's rim is at 0.44).
"""

import math

import studies
import _load_kit as kit

CENTER = (0.0, 0.2, 0.0)
SQUASH = 0.85


class BasketBack(studies.Spec):
    name = "basket_back"
    colors = kit.colors("wicker", "leather", "carrot", "tomato", "leaf", "bread")
    max_tris = 320
    grip = (0.0, 0.0, 0.25)

    def details(self, mb):
        kit.lathe(mb, CENTER, [(0.13, 0.0, "wicker_dark"), (0.15, 0.03, "wicker"), (0.175, 0.15, "wicker_dark"),
                               (0.195, 0.27, "wicker"), (0.21, 0.4, "wicker_dark"), (0.228, 0.4, "wicker_dark"),
                               (0.228, 0.44, "wicker_dark"), (0.2, 0.44, "wicker_dark"), (0.2, 0.41, "leaf_dark")],
                  8, squash=SQUASH)
        kit.strap(mb, kit.ring((0.0, 0.2, 0.25), 0.197, 0.197 * SQUASH, 8, math.pi / 8), (0, 0, 1), 0.045, 0.012,
                  "leather")
        # The food on top.
        kit.bread(mb, (-0.15, 0.27, 0.43), (0.06, 0.3, 0.5), 0.05)
        kit.carrot(mb, (0.1, 0.12, 0.52), (0.07, 0.17, 0.36))
        kit.tomato(mb, (-0.09, 0.12, 0.45), 0.05, 1)
        kit.tomato(mb, (0.0, 0.17, 0.46), 0.05, 2)
        kit.tomato(mb, (0.11, 0.3, 0.45), 0.045, 3)
        kit.greens(mb, (-0.07, 0.2, 0.43), 0.19, 0.08)


SPECS = [BasketBack()]
