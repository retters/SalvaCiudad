"""Weapon 9: a morning star. A dark faceted iron ball with twelve spikes on
a steel neck, a brown shaft between two steel collars and a dark butt."""

import math
import random

import bmesh
from mathutils import Matrix, Vector

import common
import studies

import _parts_a as parts

BALL = (0.0, 0.0, 0.735)
RADIUS = 0.128
SPIKE = 0.052  # How far a spike sticks out of the ball.


class MorningStar(studies.Spec):
    name = "w09_morning_star"
    colors = {
        "iron": common.rgb(0x4A4656),
        "iron_light": common.rgb(0x645C6C),
        "iron_dark": common.rgb(0x2A2630),
        "steel": common.rgb(0x857C8C),
        "wood": common.rgb(0x8A4420),
        "wood_dark": common.rgb(0x5E3018),
    }
    max_tris = 500
    grip = (0.0, 0.0, 0.3)

    def details(self, mb):
        parts.lathe(mb, [(0.0, 0.0), (0.03, 0.036), (0.08, 0.043)], ["iron_dark", "iron"], sides=6)
        parts.lathe(mb, [(0.08, 0.03), (0.115, 0.03)], ["wood_dark"], sides=6)
        parts.lathe(mb, [(0.112, 0.047), (0.172, 0.047)], ["steel"], sides=6)
        parts.wrapped(mb, 0.17, 0.44, 0.03, 3, lambda i, k: ("wood", "wood_dark")[(i // 2) % 2])
        parts.lathe(mb, [(0.438, 0.047), (0.505, 0.047)], ["steel"], sides=6)
        parts.lathe(mb, [(0.503, 0.036), (0.585, 0.036), (0.635, 0.05)], ["iron", "iron_dark"], sides=6)
        # The ball: an icosphere turned so a face (not a corner) looks up
        # and down, with a spike on each of its twelve corners.
        turn = Matrix.Rotation(math.radians(37.377), 4, "X")
        ball = bmesh.ops.create_icosphere(mb.bm, subdivisions=2, radius=RADIUS,
                                          matrix=Matrix.Translation(Vector(BALL)) @ turn)
        verts = mb._finish(ball["verts"], "iron", None)
        # Lighter facets looking up, darker ones looking down, a few at random.
        rnd = random.Random(9)
        mb.bm.normal_update()
        for f in sorted({f for v in verts for f in v.link_faces}, key=lambda f: f.calc_center_median()[:]):
            lift = f.normal.z + rnd.uniform(-0.35, 0.35)
            f.material_index = mb._material_index("iron_light" if lift > 0.45 else "iron_dark" if lift < -0.45
                                                  else "iron")
        center = Vector(BALL)
        for v in [v for v in verts if len(v.link_edges) == 5]:
            out = (v.co - center).normalized()
            parts.spike(mb, center + out * (RADIUS * 0.88), center + out * (RADIUS + SPIKE), 0.035,
                        lambda i, k: ("steel", "steel", "iron_dark", "iron")[k], sides=4)


SPECS = [MorningStar()]
