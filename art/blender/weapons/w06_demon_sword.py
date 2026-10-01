"""Weapon 6: a demon sword. A jagged black blade with a red glowing edge
and core, barbs along its back, a spiky dark guard with a red gem, a red
wrapped grip and a dark pommel."""

import common
import studies

import _parts_a as parts

S = 0.001084


def P(px, py):
    """A point of the reference picture (4x crop of item 6), straightened:
    the sword leans there, here it stands upright."""
    return ((px - 195 - (1020 - py) * 0.0964) * S, (1050 - py) * S)


# The blade from the tip down: (red edge, where the red ends, ridge, back).
BLADE = [
    ((292, 32), (292, 32), (292, 32), (292, 32)),
    ((200, 132), (252, 133), (264, 134), (301, 108)),
    ((178, 215), (230, 210), (252, 205), (318, 206)),
    ((150, 300), (203, 300), (228, 300), (270, 300)),
    ((104, 400), (165, 395), (216, 390), (255, 400)),
    ((62, 468), (150, 458), (215, 455), (290, 464)),
    ((120, 528), (152, 520), (208, 510), (240, 506)),
    ((118, 608), (165, 600), (202, 600), (235, 600)),
    ((150, 642), (172, 645), (204, 650), (250, 660)),
    ((132, 692), (172, 690), (208, 690), (280, 692)),
    ((156, 724), (176, 725), (210, 722), (245, 722)),
    ((152, 778), (178, 778), (212, 778), (240, 778)),
]
EDGE = ["red_light", "red", "maroon", "maroon", "red", "red_light", "red", "red_light", "red", "red_light", "red"]
CORE = ["red_light", "red", "red", "red", "red_light", "red", "black", "black", "black", "black", "black"]


class DemonSword(studies.Spec):
    name = "w06_demon_sword"
    colors = {
        "black": common.rgb(0x44364A),
        "black_light": common.rgb(0x6A5566),
        "red": common.rgb(0xF02328),
        "red_light": common.rgb(0xFF4A44),
        "maroon": common.rgb(0x5A2030),
    }
    max_tris = 500
    grip = (0.0, 0.0, 0.16)

    def details(self, mb):
        def xz(p, h):
            return (*P(*p), h)

        rows = [[xz(a, 0.0), xz(b, 0.013), xz(c, 0.017), xz(d, 0.0)] for a, b, c, d in BLADE]

        def blade_mat(i, j):
            return (EDGE[i], CORE[i], ("black", "black_light")[i % 2])[j]
        parts.ridged(mb, rows, blade_mat)

        # Guard: a dark middle plate with a red gem, a long spike and a claw
        # to one side, a hooked block to the other.
        parts.bevel_plate(mb, [P(215, 738), P(258, 790), P(215, 848), P(172, 790)], 0.024, 0.014, "black",
                          "black_light", edge=0.012)
        gx, gz = P(215, 792)
        parts.gem(mb, (gx, 0.0, gz), 0.024, 0.036, 0.018, ("red_light", "red", "red", "maroon"), base=0.024)
        parts.ridged(mb, [[xz((240, 758), 0.008), xz((248, 790), 0.02), xz((252, 818), 0.008)],
                          [xz((385, 715), 0.0)] * 3], lambda i, j: ("black_light", "black")[j])
        parts.ridged(mb, [[xz((238, 802), 0.008), xz((255, 812), 0.017), xz((258, 832), 0.008)],
                          [xz((303, 850), 0.0)] * 3], lambda i, j: ("black_light", "black")[j])
        parts.ridged(mb, [[xz((192, 766), 0.01), xz((190, 795), 0.021), xz((190, 824), 0.01)],
                          [xz((132, 752), 0.01), xz((120, 800), 0.024), xz((152, 846), 0.01)],
                          [xz((90, 812), 0.006), xz((102, 846), 0.018), xz((142, 860), 0.006)],
                          [xz((124, 902), 0.0)] * 3], lambda i, j: ("black_light", "black")[j])
        parts.wrapped(mb, 0.076, 0.24, 0.029, 5, "red")
        parts.lathe(mb, [(0.0, 0.0), (0.038, 0.047), (0.07, 0.042), (0.09, 0.028)],
                    ["black", "black", "black_light"], sides=6)
        parts.gem(mb, (0.0, 0.0, 0.052), 0.015, 0.02, 0.01, "red", base=0.038)


SPECS = [DemonSword()]
