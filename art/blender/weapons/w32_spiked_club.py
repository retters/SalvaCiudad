"""Weapon 32: spiked club. A brown wooden club that widens to a heavy
faceted head studded with steel spikes, a stub on top, red cord wraps under
the head and on the grip, and a steel stud on the pommel."""

import math

import studies
import _parts_c as parts

BODY = [((0.0, 0.0, 0.036), 0.036), ((0.0, 0.0, 0.085), 0.028), ((0.003, 0.0, 0.38), 0.031),
        ((0.0, 0.0, 0.52), 0.05), ((0.0, 0.0, 0.62), 0.07), ((0.0, 0.0, 0.75), 0.076),
        ((0.0, 0.0, 0.782), 0.046), ((0.0, 0.0, 0.79), 0.02)]
SPIKE_ROWS = [(0.56, 5, 0.3), (0.625, 5, 1.0), (0.69, 5, 0.2), (0.755, 5, 0.85)]  # Height, count, first angle.
WRAPS = [(0.37, 0.5, 0.011), (0.075, 0.205, 0.006)]   # The cord wraps: from, to, how far out.
STUB = [(0.795, 0.027), (0.85, 0.025), (0.876, 0.011)]   # The stub on top: (height, radius).


class SpikedClub(studies.Spec):
    name = "w32_spiked_club"
    colors = {
        **parts.shades("wood", 0x93543A, 0xAE6C48, 0x673728),
        **parts.shades("steel", 0xD6D2D6, shade=0x8E8C96),
        **parts.shades("red", 0xCE251D, shade=0x8E1F1A),
    }
    capsules = parts.chain(BODY)
    ellipsoids = []
    budget = 190
    max_tris = 600
    grip = (0.0, 0.0, 0.26)

    def paint(self, c, n):
        return "wood"

    def details(self, mb):
        parts.begin(mb, self)
        parts.retone(mb, "wood", 0.5)
        axis = parts.along(BODY)
        for z, count, first in SPIKE_ROWS:
            c, r = axis(z)
            for k in range(count):
                a = first + k * math.tau / count
                d = (math.cos(a), math.sin(a))
                parts.spike(mb, (c.x + d[0] * r * 0.8, c.y + d[1] * r * 0.8, z),
                            (c.x + d[0] * (r + 0.042), c.y + d[1] * (r + 0.042), z + 0.006), 0.028, "steel",
                            ref=(0, 0, 1), phase=math.pi / 4)
        for k, (z0, z1, lift) in enumerate(WRAPS):
            parts.wrap(mb, (0, 0, z0), (0, 0, z1), (axis(z0)[1] + lift, axis(z1)[1] + lift), 3, "red",
                       bulge=0.005, seed=k + 2)
        parts.loft(mb, [(0, 0, z) for z, _ in STUB], [r for _, r in STUB], 6, "wood", tones=0.5, seed=9)
        parts.spike(mb, (0.0, -0.028, 0.036), (0.0, -0.05, 0.034), 0.014, "steel", ref=(0, 0, 1))


SPECS = [SpikedClub()]
