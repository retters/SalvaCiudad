"""Giant cherry: a thick gnarled grey-brown trunk on big roots under a huge
dense canopy of pink blossom in rounded masses; bare, a wide spreading
crown of branches. About 25 m tall and 26 m wide.

The branches and the masses of blossom are traced from the pictures; the
foot and the roots are made here."""

import _giant


class Cherry(_giant.Giant):
    traced = "giant_cherry"

    def shape(self):
        seed = self.o["seed"]
        self.roots(8, [(1.5, 4.2, 1.35), (3.0, 1.9, 1.15), (4.7, 0.7, 0.85), (6.6, -0.3, 0.45)], seed + 5,
                   wobble=0.2, center=(0.1, 0.0))
        self.knobs(30, 1.5, 9.5, (0.7, 1.2), seed + 7, out=0.4)


SPECS = _giant.variants(
    Cherry, "giant_cherry", _giant.bark_tones(0xAC8166, 0x644538), _giant.tones(0xF8A2BD, 0xC05281, 0x902D4D),
    seed=4203, foot=[(0.1, -0.4, 3.0), (0.1, 2.6, 2.8)], skip=[(-1.2, 5.2, 1.0)], back_from=7.0,
    twig_scale=1.2, budget=1500, ring=(5.6, 7.4), stones=16, tufts=14, flowers=12)
