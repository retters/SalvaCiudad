"""Sheep: a lumpy cream fleece (many overlapping wool puffs welded by the
remesh), a dark grey face, ears and legs, and a woolly tuft on the head."""

import math

from mathutils import Vector

import common
import rigs
import studies

BODY = ((0.0, 0.05, 0.56), (0.32, 0.46, 0.28))
HEAD = ((0.0, -0.56, 0.74), (0.135, 0.16, 0.145))
MUZZLE = ((0.0, -0.68, 0.68), (0.095, 0.1, 0.095))
TUFT = ((0.0, -0.49, 0.85), (0.145, 0.12, 0.1))
LEG_X, LEG_Y = 0.15, (-0.28, 0.33)
WOOL_LOW = 0.44  # Below this the legs are bare.
EYE = (0.095, -0.655, 0.78)


def wool_puffs():
    """Puffs spread over the fleece with a golden-angle spiral, so the
    silhouette is bumpy all around."""
    (cx, cy, cz), (rx, ry, rz) = BODY
    puffs = []
    count = 34
    golden = math.pi * (3 - math.sqrt(5))
    for i in range(count):
        t = 1 - 2 * (i + 0.5) / count      # -1 .. 1 along the body (Y).
        s = math.sqrt(1 - t * t)
        a = i * golden
        x, z = s * math.cos(a), s * math.sin(a)
        if z < -0.55:
            continue  # The belly stays smooth.
        r = 0.1 + 0.025 * ((i * 7) % 3)
        p = (cx + x * rx * 0.88, cy + t * ry * 0.88, cz + z * rz * 0.85)
        puffs.append((p, (r, r * 1.05, r * 0.9)))
    return puffs


class SheepRig(rigs.Quadruped):
    """A quadruped that grazes: the head goes all the way down to the grass."""

    def eat_pose(self, t):
        down = rigs.smooth(t / 0.2) * (1 - rigs.smooth((t - 0.8) / 0.2))
        # Small tugs at the grass while the head is down.
        tug = (math.sin(2 * math.pi * 6 * t) * rigs.smooth((t - 0.2) / 0.05)
               * (1 - rigs.smooth((t - 0.75) / 0.05)))
        pitch = math.radians(5.0) * down
        dz = -0.005 * down
        rot = self.planted({}, pitch, dz)
        rot["body"] = [(rigs.X, math.degrees(pitch))]
        rot["chest"] = [(rigs.X, 20.0 * down)]
        rot["neck"] = [(rigs.X, 42.0 * down + 2.0 * tug)]
        rot["head"] = [(rigs.X, -6.0 * down + 5.0 * tug)]
        rot["ear.L"] = [(rigs.Y, 12.0 * down)]
        rot["ear.R"] = [(rigs.Y, -12.0 * down)]
        self.tail_rot(rot, 20.0 * math.sin(2 * math.pi * 4 * t) * down)
        return rot, Vector((0, 0, dz)), {}


class Sheep(studies.Spec):
    name = "sheep"
    colors = {
        "wool": common.rgb(0xF1E9D6),
        "wool_light": common.rgb(0xFAF5E8),
        "wool_shade": common.rgb(0xE2D8C0),
        "face": common.rgb(0x35322F),
        "leg": common.rgb(0x2A2826),
        "eye": common.rgb(0x0E0C0B),
        "nose": common.rgb(0x1A1817),
    }
    budget = 800
    max_tris = 1500
    tone_material = "wool"
    tones = 0.35
    rig = SheepRig(
        body=((0, 0.42, 0.6), (0, -0.05, 0.6)),
        chest=((0, -0.05, 0.6), (0, -0.3, 0.67)),
        neck=((0, -0.3, 0.67), (0, -0.5, 0.76)),
        head=((0, -0.5, 0.76), (0, -0.77, 0.68)),
        ears=((0.1, -0.53, 0.78), (0.27, -0.56, 0.73)),
        tail=[(0, 0.46, 0.68), (0, 0.5, 0.67), (0, 0.54, 0.65), (0, 0.58, 0.62)],
        legs={
            "F": ((LEG_X, LEG_Y[0], 0.5), (LEG_X, LEG_Y[0], 0.27), (LEG_X, LEG_Y[0], 0.05),
                  (LEG_X, LEG_Y[0] - 0.04, 0.0)),
            "H": ((LEG_X, LEG_Y[1], 0.5), (LEG_X, LEG_Y[1], 0.27), (LEG_X, LEG_Y[1], 0.05),
                  (LEG_X, LEG_Y[1] - 0.04, 0.0)),
        },
        # The wool is welded surface: the legs only pull on the bare legs.
        leg_exit=(0.36, WOOL_LOW),
        leg_reach=0.1,
        walk=rigs.Gait(speed=0.6, frames=20, duty=0.64, lift=0.05, crouch=0.015, bob=0.006,
                       phases=rigs.WALK_PHASES),
        run=rigs.Gait(speed=2.0, frames=14, duty=0.42, lift=0.09, crouch=0.04, bob=0.015,
                      phases=rigs.TROT_PHASES, nod=4.0, wag=10.0),
        lie_height=0.36,
        blend=0.05,
    )

    def __init__(self):
        self.ellipsoids = [BODY, HEAD, MUZZLE, TUFT,
                           ((0.0, 0.5, 0.66), (0.1, 0.08, 0.1))] + wool_puffs()  # Last: tail.
        self.capsules = [((0.0, -0.3, 0.68), (0.0, -0.5, 0.76), 0.13, 0.1)]  # Neck.
        for s in (-1, 1):
            for y in LEG_Y:
                self.capsules.append(((s * LEG_X, y, 0.02), (s * LEG_X, y, 0.5), 0.05, 0.06))
        self.cuts = [((0, 0, WOOL_LOW), (0, 0, 1), lambda c, n: c.z < 0.5 and any(
                         math.hypot(abs(c.x) - LEG_X, c.y - y) < 0.09 for y in LEG_Y)),
                     ((0, -0.49, 0.75), Vector((0, 1, 0.35)).normalized(),
                      lambda c, n: c.y < -0.38 and c.z > 0.55)]

    def paint(self, c, n):
        if c.z < WOOL_LOW and any(math.hypot(abs(c.x) - LEG_X, c.y - y) < 0.075 for y in LEG_Y):
            return "leg"
        # Face: in front of the plane just behind the head, below the tuft.
        behind = (c - Vector((0, -0.49, 0.75))).dot(Vector((0, 1, 0.35)).normalized())
        if behind < 0 and c.y < -0.42 and (c.z > 0.64 or c.y < -0.6):
            if not studies.inside(c, TUFT[0], (0.12, 0.1, 0.075)) or c.y < -0.53:
                return "face"
        return "wool"

    def details(self, mb):
        for s in (-1, 1):
            mb.sphere((s * EYE[0], EYE[1], EYE[2]), 0.018, "eye", segments=6, rings=4)
            mb.sphere((s * 0.028, -0.755, 0.69), 0.012, "nose", segments=5, rings=3, scale=(1.0, 0.5, 0.8))
            # Ears stick out sideways and a little down.
            studies.plate(mb, [(s * 0.1, -0.5, 0.8), (s * 0.23, -0.53, 0.76), (s * 0.27, -0.56, 0.73),
                               (s * 0.21, -0.57, 0.72), (s * 0.1, -0.56, 0.75)], 0.025, "face")


SPECS = [Sheep()]
