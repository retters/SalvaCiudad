"""Weapon 11: a trident. Three light blue crystal prongs, the side ones on
dark blue arms with gold bands, a pointed gold fitting, a blue wrap, a
brown shaft and a gold butt."""

import common
import studies

import _parts_a as parts

P = parts.pixels(0.001975, 215, 1000)  # 4x crop of item 11.


def rows(points, halves):
    return [[(*P(*p), h) for p, h in zip(row, hs)] for row, hs in zip(points, halves)]


class Trident(studies.Spec):
    name = "w11_trident"
    colors = {
        "crystal": common.rgb(0x3E9EDC),
        "crystal_light": common.rgb(0x8EDCF6),
        "blue": common.rgb(0x1C55A0),
        "gold": common.rgb(0xF2B424),
        "gold_shade": common.rgb(0xB8781A),
        "wood": common.rgb(0x70401F),
    }
    max_tris = 500
    grip = (0.0, 0.0, 0.6)

    def details(self, mb):
        parts.lathe(mb, [(0.0, 0.0), (0.05, 0.06), (0.11, 0.073), (0.168, 0.052)],
                    ["gold_shade", "gold_shade", "gold"], sides=6)
        parts.lathe(mb, [(0.16, 0.046), (0.735, 0.046)], ["wood"], sides=6)
        parts.wrapped(mb, 0.73, 0.992, 0.06, 4, lambda i, k: "blue" if i in (0, 7) else "crystal")
        # The gold fitting: a collar that widens into a four-sided point.
        parts.lathe(mb, [(0.985, 0.062), (1.07, 0.07), (1.108, 0.092), (1.3, 0.0)],
                    lambda i, k: "gold" if k in (1, 2) or i == 0 else "gold_shade", sides=4)

        def crystal(i, j):
            return ("crystal", "crystal_light")[j]
        # Middle prong: base, waist, widest, tip.
        parts.ridged(mb, rows([[(193, 392), (215, 392), (237, 392)], [(191, 305), (215, 305), (239, 305)],
                               [(171, 192), (215, 188), (263, 192)], [(215, 38)] * 3],
                              [(0.012, 0.022, 0.012), (0.014, 0.036, 0.014), (0.0, 0.05, 0.0), (0.0,) * 3]), crystal)
        for mirror in (False, True):
            place = parts.placer(mirror=mirror)
            path = [(x, 0.0, z) for x, z in (P(205, 452), P(160, 444), P(126, 422), P(110, 390))]
            parts.tube(mb, path, [0.04, 0.04, 0.038, 0.036], "blue", sides=6, place=place)
            bx, bz = P(114, 394)
            parts.lathe(mb, [(-0.012, 0.05), (0.04, 0.045)], ["gold"], sides=6, origin=(bx, 0.0, bz),
                        axis=(-0.45, 0.0, 0.89), place=place)
            parts.ridged(mb, rows([[(84, 372), (102, 378), (122, 368)], [(55, 298), (92, 298), (127, 292)],
                                   [(112, 165)] * 3],
                                  [(0.012, 0.032, 0.012), (0.0, 0.042, 0.0), (0.0,) * 3]), crystal, place)


SPECS = [Trident()]
