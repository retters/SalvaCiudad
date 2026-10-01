"""Bald eagle, perched upright: a dark brown body with its wings folded
along the sides, a white head and tail, a big yellow hooked beak and
yellow legs with dark talons."""

import bmesh
from mathutils import Vector

import common
import rigs_bird
import studies
from rigs_bird import tag

HEAD = ((0.0, -0.07, 0.725), (0.092, 0.115, 0.09))
EYE = (0.07, -0.13, 0.755)
NECK_PLANE = (Vector((0, 0, 0.64)), Vector((0, -0.35, 1)).normalized())
LEG_X = 0.07


def hull(mb, points, mat):
    """A convex solid around the points (a beak, a talon)."""
    tmp = bmesh.new()
    verts = [tmp.verts.new(p) for p in points]
    res = bmesh.ops.convex_hull(tmp, input=verts)
    bmesh.ops.delete(tmp, geom=[v for v in res["geom_interior"] if isinstance(v, bmesh.types.BMVert)],
                     context="VERTS")
    mapping = {v: mb.bm.verts.new(v.co) for v in tmp.verts}
    for f in tmp.faces:
        mb.bm.faces.new([mapping[v] for v in f.verts])
    tmp.free()
    return mb._finish(list(mapping.values()), mat, None)


def mirror(points, s):
    return [(s * x, y, z) for x, y, z in points]


# Folded wing (right side, x > 0), outline from the shoulder down to the tip.
WING = [(0.12, -0.09, 0.55), (0.13, 0.0, 0.61), (0.16, 0.1, 0.54), (0.12, 0.27, 0.14),
        (0.09, 0.22, 0.12), (0.14, -0.05, 0.36)]
# The long flight feathers at the lower end, a darker layer on the wing.
PRIMARIES = [(0.14, 0.05, 0.36), (0.16, 0.11, 0.42), (0.125, 0.28, 0.1), (0.1, 0.24, 0.1),
             (0.13, 0.03, 0.3)]
TAIL = [(-0.05, 0.12, 0.3), (0.05, 0.12, 0.3), (0.11, 0.4, 0.05), (0.0, 0.45, 0.025), (-0.11, 0.4, 0.05)]
# The wing unfolds like a real one: the upper arm from the shoulder back to
# the elbow, the forearm forward to the wrist, and the hand (the visible
# plate) from the wrist down to the tip. Two hidden plates under the visible
# one are the inner wing's feathers; they only show when the wing opens,
# and reach past the elbow so the open wing has no gaps.
ELBOW = tuple(a + (b - a) * 0.4 for a, b in zip(WING[2], WING[3]))
SHOULDER, WRIST, WING_TIP = (0.13, 0.03, 0.57), (0.125, -0.07, 0.53), (0.105, 0.245, 0.13)
# (outline, how far under the visible plate, bone, material).
HIDDEN = [(WING, 0.03, "wing", "brown"),                                             # On the upper arm.
          ([WING[0], ELBOW, WING[3], WING[4], WING[5]], 0.045, "wing.2", "brown")]   # On the forearm.


class Eagle(studies.Spec):
    name = "eagle"
    colors = {
        "brown": common.rgb(0x5A3A24),
        "brown_light": common.rgb(0x6C4830),
        "brown_shade": common.rgb(0x4A2E1C),
        "dark": common.rgb(0x3A2517),
        "white": common.rgb(0xF4F2EE),
        "yellow": common.rgb(0xF2B928),
        "eye": common.rgb(0x151012),
    }
    ellipsoids = [
        ((0.0, 0.03, 0.42), (0.145, 0.14, 0.24)),    # Body.
        ((0.0, -0.04, 0.48), (0.13, 0.11, 0.16)),    # Chest.
        ((0.0, 0.0, 0.58), (0.12, 0.11, 0.08)),      # Shoulders.
        HEAD,
        ((0.0, -0.15, 0.7), (0.05, 0.05, 0.045)),    # Face, under the beak.
        ((LEG_X, -0.02, 0.2), (0.06, 0.07, 0.1)),    # Feathered thighs.
        ((-LEG_X, -0.02, 0.2), (0.06, 0.07, 0.1)),
    ]
    capsules = [((0.0, -0.02, 0.58), (0.0, -0.06, 0.7), 0.085, 0.075)]  # Neck.
    cuts = [(NECK_PLANE[0], NECK_PLANE[1], lambda c, n: 0.52 < c.z < 0.75)]
    budget = 380
    max_tris = 1000  # Raised for the hidden inner wings and the rings cut at the thighs.
    tone_material = "brown"
    tones = 0.35
    rig = rigs_bird.Bird(
        body=((0, 0.03, 0.28), (0, -0.01, 0.58)),
        neck=[(0, -0.01, 0.58), (0, -0.04, 0.65), (0, -0.06, 0.7)],
        head=((0, -0.06, 0.7), (0, -0.15, 0.73)),
        beak_tip=(0, -0.25, 0.67),
        tail=[(0, 0.12, 0.3), (0, 0.45, 0.03)],
        legs=((LEG_X, -0.02, 0.26), (LEG_X, -0.03, 0.14), (LEG_X, -0.04, 0.02), (LEG_X, -0.12, 0.012)),
        leg_exit=(0.17, 0.24), leg_reach=0.09, blend=0.05,
        wings=[SHOULDER, ELBOW, WRIST, WING_TIP],
        wing_sides=[(0, -0.8, -0.6), (0, -0.5, -0.85), (0, 0.8, 0.6)], wing_twitch=6.0,
        # On the ground an eagle is clumsy: it waddles, and to go faster it hops.
        walk=rigs_bird.Step(frames=18, duty=0.6, crouch=0.03, lift=0.05, bob=0.005, head_bob=5.0, waddle=7.0,
                            sway=0.02, tail_up=12.0),
        run=rigs_bird.Step(frames=12, duty=0.45, crouch=0.04, lift=0.03, lean=12.0, wings=14.0,
                           phases=(0.0, 0.0), hop=0.07, toe=15.0, tail_up=6.0),
        eat=dict(pitch=62.0, crouch=0.04, head=75.0, height=0.03, pecks=3),
        air=dict(name="fly", frames=20, beats=1, pitch=72.0, lift=0.3, amp=30.0, mid=8.0, lag=0.5, tuck=8.0,
                 sweep=(-0.3, 0.0, 0.3),
                 foot=35.0, tail=-35.0, head=8.0, speed=9.0, bob=0.03),
        lie_height=0.14, look=35.0,
    )

    def paint(self, c, n):
        p, no = NECK_PLANE
        return "white" if (c - p).dot(no) > 0 else "brown"

    def details(self, mb):
        for s in (-1, 1):
            side = "L" if s > 0 else "R"
            tag(mb, mb.sphere((s * EYE[0], EYE[1], EYE[2]), 0.015, "eye", segments=6, rings=4), "head")
            tag(mb, studies.plate(mb, mirror(WING, s), 0.035, "brown"), f"wing.3.{side}")
            tag(mb, studies.plate(mb, [(x + s * 0.012, y, z) for x, y, z in mirror(PRIMARIES, s)], 0.02, "dark"),
                f"wing.3.{side}")
            for outline, depth, bone, mat in HIDDEN:
                mid = sum((Vector(p) for p in outline), Vector()) / len(outline)
                pts = [mid + (Vector(p) - mid) * 0.92 - Vector((depth, 0, 0)) for p in outline]
                tag(mb, studies.plate(mb, mirror(pts, s), 0.012, mat), f"{bone}.{side}")
            # Leg, three toes forward and one back, each with a dark talon.
            x = s * LEG_X
            tag(mb, mb.cylinder((x, -0.03, 0.14), (x, -0.04, 0.02), 0.018, 0.015, "yellow", segments=5),
                f"leg_lower.{side}")
            for dx, dy in ((-0.035, -0.07), (0.0, -0.08), (0.035, -0.07), (0.0, 0.04)):
                tip = Vector((x + dx, -0.04 + dy, 0.012))
                tag(mb, mb.cylinder((x, -0.04, 0.015), tip, 0.011, 0.008, "yellow", segments=4), f"foot.{side}")
                d = (tip - Vector((x, -0.04, 0.015))).normalized()
                tag(mb, mb.cylinder(tip, tip + d * 0.02 - Vector((0, 0, 0.01)), 0.007, 0.0, "dark", segments=3),
                    f"foot.{side}")
        tag(mb, studies.plate(mb, TAIL, 0.03, "white"), "tail")
        # Beak: a big hooked hull out of the face.
        tag(mb, hull(mb, [
            (-0.032, -0.14, 0.74), (0.032, -0.14, 0.74), (-0.036, -0.145, 0.69), (0.036, -0.145, 0.69),
            (0.0, -0.155, 0.755), (-0.02, -0.225, 0.73), (0.02, -0.225, 0.73), (0.0, -0.255, 0.71),
            (0.0, -0.25, 0.67), (-0.016, -0.21, 0.69), (0.016, -0.21, 0.69)], "yellow"), "head")


SPECS = [Eagle()]
