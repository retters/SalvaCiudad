"""Sea turtle: a domed green shell split into darker and lighter plates,
a yellow-green rim, a yellow-green head and big flat flippers, the front
pair long and swept back."""

import common
import studies

SHELL = ((0.0, 0.04, 0.1), (0.4, 0.5, 0.27))
RIM_Z = 0.13          # Below this the shell is the light rim.
PLATE_X = 0.13        # Border between the middle row of plates and the side plates.
PLATE_Y = (-0.2, 0.04, 0.27)  # Borders between the middle plates along the shell.
SIDE_Y = (-0.3, -0.08, 0.16, 0.38)  # Borders between the side plates, staggered.
SIDE_Z = 0.2          # Below this, down to the rim, a ring of dark edge plates.
HEAD = ((0.0, -0.58, 0.19), (0.11, 0.16, 0.1))
EYE = (0.08, -0.64, 0.22)


def on_shell(c, n):
    return c.y > -0.47 and c.z > RIM_Z - 0.05


class Turtle(studies.Spec):
    name = "turtle"
    colors = {
        "shell": common.rgb(0x35995E),
        "shell_light": common.rgb(0x40AA69),
        "shell_shade": common.rgb(0x2E8A53),
        "plate": common.rgb(0x1C5E3E),
        "rim": common.rgb(0xB5D63A),
        "skin": common.rgb(0x9CCB3B),
        "eye": common.rgb(0x151012),
    }
    ellipsoids = [
        SHELL,
        ((0.0, 0.02, 0.07), (0.36, 0.44, 0.07)),  # Belly plate, flat under the rim.
        HEAD,
        ((0.0, -0.7, 0.16), (0.075, 0.08, 0.065)),  # Beak.
    ]
    capsules = [((0.0, -0.34, 0.12), (0.0, -0.5, 0.17), 0.085, 0.09)]  # Neck.
    cuts = [((0, 0, RIM_Z), (0, 0, 1), on_shell),
            ((0, 0, SIDE_Z), (0, 0, 1), lambda c, n: on_shell(c, n) and abs(c.x) > PLATE_X - 0.03)]
    cuts += [((s * PLATE_X, 0, 0), (1, 0, 0), lambda c, n: on_shell(c, n) and c.z > RIM_Z) for s in (-1, 1)]
    cuts += [((0, y, 0), (0, 1, 0), lambda c, n: on_shell(c, n) and abs(c.x) < PLATE_X + 0.03 and c.z > RIM_Z)
             for y in PLATE_Y]
    cuts += [((0, y, 0), (0, 1, 0), lambda c, n: on_shell(c, n) and abs(c.x) > PLATE_X - 0.03 and c.z > SIDE_Z)
             for y in SIDE_Y]
    budget = 650
    max_tris = 1500
    tone_material = "shell"

    def paint(self, c, n):
        if c.y < -0.4 and not (c.z > RIM_Z and c.y > -0.47):
            return "skin"  # Neck and head.
        if c.z < RIM_Z:
            return "rim"
        if abs(c.x) < PLATE_X:
            return "plate" if sum(1 for y in PLATE_Y if c.y > y) % 2 == 0 else "shell"
        if c.z < SIDE_Z:
            return "plate"
        return "plate" if sum(1 for y in SIDE_Y if c.y > y) % 2 == 1 else "shell"

    def details(self, mb):
        for s in (-1, 1):
            mb.sphere((s * EYE[0], EYE[1], EYE[2]), 0.022, "eye", segments=6, rings=4)
            # Front flipper: long, swept back, in two plates for a slight bend.
            studies.plate(mb, [(s * 0.26, -0.34, 0.11), (s * 0.46, -0.4, 0.09), (s * 0.6, -0.34, 0.07),
                               (s * 0.58, -0.16, 0.06), (s * 0.3, -0.1, 0.1)], 0.04, "skin")
            studies.plate(mb, [(s * 0.6, -0.34, 0.07), (s * 0.76, -0.24, 0.04), (s * 0.86, -0.02, 0.02),
                               (s * 0.72, -0.04, 0.03), (s * 0.58, -0.16, 0.06)], 0.035, "skin")
            # Hind flipper: short and rounded.
            studies.plate(mb, [(s * 0.2, 0.42, 0.07), (s * 0.34, 0.48, 0.05), (s * 0.38, 0.6, 0.03),
                               (s * 0.27, 0.64, 0.03), (s * 0.15, 0.52, 0.06)], 0.03, "skin")
        # A short pointed tail.
        mb.cylinder((0, 0.5, 0.08), (0, 0.64, 0.05), 0.04, 0.0, "skin", segments=5)


SPECS = [Turtle()]
