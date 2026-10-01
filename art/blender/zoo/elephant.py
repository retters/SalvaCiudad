"""Elephant: blue-grey with lighter and darker facets, pillar legs, big flat
ears, a trunk of tapering capsules hanging almost to the ground, white
tusks and a thin tail with a dark tuft."""

import math

from mathutils import Vector

import common
import rigs
import studies

LEG_X = 0.5
FRONT_Y, HIND_Y = -0.62, 0.95
# The trunk, from the face down to the slightly curled tip.
TRUNK = [(0, -1.78, 2.2), (0, -1.97, 1.78), (0, -2.05, 1.3), (0, -2.03, 0.85), (0, -1.97, 0.5),
         (0, -2.03, 0.28), (0, -2.14, 0.24)]
TRUNK_R = [0.27, 0.21, 0.165, 0.135, 0.115, 0.1, 0.095]
TAIL = [(0, 1.52, 2.25), (0, 1.62, 1.9), (0, 1.66, 1.5)]
FOOT_TOP = 0.25
TRUNK_BONES = [f"trunk.{i + 1}" for i in range(len(TRUNK) - 1)]
# Turns of the trunk bones (degrees about X, each relative to the one above)
# when it is curled up with its tip at the mouth, and when it reaches out
# for food on the ground.
TRUNK_CURL = [-12.0, -6.0, 58.0, 98.0, 70.0, 35.0]
TRUNK_REACH = [-7.0, -8.0, -3.0, 6.0, 10.0, 12.0]


def on_surface(spec, origin, direction, sink=0.0):
    """The point where a ray from inside the spec's shape leaves it, moved
    `sink` back inside (details that must touch the skin: eyes)."""
    o, d = Vector(origin), Vector(direction).normalized()
    t = 0.0
    while studies.sdf(spec, o + d * t) < 0.0 and t < 5.0:
        t += 0.004
    return o + d * (t - sink)


def mark_surface(mb):
    """Marks the vertices of the welded surface (call when details() starts)."""
    layer = mb.bm.verts.layers.int.new("surface")
    for v in mb.bm.verts:
        v[layer] = 1
    return layer


def surface_first(mb, layer):
    """Puts the welded surface's vertices before the detail pieces again
    (call when details() ends). rigs.bind takes the first mb.detail_from
    vertices as the surface, but new vertices fill the slots of those the
    cuts removed, so pieces and surface end up mixed and the whole surface
    is bound a second time as if it were one piece. No vertex may be held
    in a variable across the sort: it moves the vertices in memory."""
    bm = mb.bm
    bm.verts.index_update()
    count = len(bm.verts)
    bm.verts.sort(key=lambda v: v.index + (0 if v[layer] else count))
    bm.verts.layers.int.remove(layer)
    bm.verts.index_update()


class ElephantRig(rigs.Quadruped):
    """The quadruped plus a trunk: a chain of bones under the head that the
    welded surface follows, swaying in idle and walk and bringing food to
    the mouth in eat. The big ears flap slowly."""

    def __init__(self, **kw):
        bones, parent = [], "head"
        for name, a, b in zip(TRUNK_BONES, TRUNK, TRUNK[1:]):
            bones.append(rigs.Bone(name, a, b, parent=parent, surface=True))
            parent = name
        super().__init__(extra_bones=bones, **kw)

    def cuts(self):
        """Also a ring at every joint of the trunk, so it can curl."""
        out = super().cuts()
        pts = [Vector(p) for p in TRUNK]
        for a, b, c in zip(pts, pts[1:], pts[2:]):
            out.append((b, (c - a).normalized(), lambda p, n, b=b: p.y < -1.7 and (p - b).length < 0.45))
        return out

    def surface_weights(self, p):
        if p.y > -1.6:
            return super().surface_weights(p)
        # The face and the trunk: by distance to the head and trunk bones
        # (the template would give the low tip of the trunk to a foot).
        cands = [(rigs.segment_distance(p, b.head, b.tail), b.name) for b in self.bones
                 if b.name == "head" or b.name.startswith("trunk.")]
        d0 = min(d for d, _ in cands)
        return [(n, max(0.0, 1.0 - (d - d0) / self.blend) ** 2) for d, n in cands]

    def piece_bone(self, center, piece):
        if center.y > 1.3:  # Tail links and the tuft.
            tail = [b for b in self.bones if b.name.startswith("tail.")]
            return min(tail, key=lambda b: rigs.segment_distance(center, b.head, b.tail)).name
        if abs(center.x) > 0.65:
            return "ear.L" if center.x > 0 else "ear.R"
        return "head"  # Eyes and tusks.

    def eat_pose(self, t):
        # An elephant eats with its trunk (pose_extra): the head only dips.
        down = rigs.smooth(t / 0.2) * (1 - rigs.smooth((t - 0.8) / 0.2))
        rot = self.planted({}, 0.0, 0.0)
        rot["neck"] = [(rigs.X, 3.0 * down)]
        rot["head"] = [(rigs.X, 5.0 * down)]
        self.tail_rot(rot, 20.0 * math.sin(2 * math.pi * 3 * t) * down)
        return rot, Vector((0, 0, 0)), {}

    def pose_extra(self, clip, t, rot):
        p = 2 * math.pi * t
        # Ears: hinged on a vertical axis; a positive turn folds the left
        # ear back against the neck, a negative one fans it out.
        if clip == "die":
            flap = 18.0 * rigs.smooth((t - 0.3) / 0.45)
        elif clip in ("walk", "run"):
            flap = -4.0 - 6.0 * math.sin(p + 0.8)
        else:
            flap = -4.0 - 11.0 * math.sin(2 * p)
        rot["ear.L"] = [(rigs.Z, flap)]
        rot["ear.R"] = [(rigs.Z, -flap)]
        for i, name in enumerate(TRUNK_BONES):
            if clip == "eat":
                # Twice per loop: reach out, curl the tip around the food,
                # lift it to the mouth, and let the trunk down again.
                u = (t * 2) % 1.0
                reach = rigs.smooth(u / 0.15) * (1 - rigs.smooth((u - 0.2) / 0.15))
                lead = (len(TRUNK_BONES) - 1 - i) * 0.035  # The tip curls first.
                curl = rigs.smooth((u - 0.2 + lead) / 0.3) * (1 - rigs.smooth((u - 0.68 - lead * 0.5) / 0.25))
                rot[name] = [(rigs.X, TRUNK_REACH[i] * reach + TRUNK_CURL[i] * curl)]
            elif clip == "die":
                rot[name] = [(rigs.X, 6.0 * rigs.smooth(t / 0.35))]
            elif clip in ("walk", "run"):
                rot[name] = [(rigs.Y, 2.5 * math.sin(p - 0.5 * i)), (rigs.X, 2.0 * math.cos(2 * p - 0.4 * i))]
            else:
                rot[name] = [(rigs.Y, 3.0 * math.sin(p - 0.5 * i)), (rigs.X, 2.0 * math.sin(2 * p - 0.4 * i))]


class Elephant(studies.Spec):
    name = "elephant"
    budget = 1100
    max_tris = 2000
    tone_material = "elephant"
    colors = {
        "elephant": common.rgb(0x6F809E),
        "elephant_light": common.rgb(0x8090AC),
        "elephant_shade": common.rgb(0x5E6D8A),
        "ear": common.rgb(0x7888A5),
        "tusk": common.rgb(0xF3EDE0),
        "eye": common.rgb(0x151012),
    }
    ellipsoids = [
        ((0, 0.2, 1.95), (0.8, 1.2, 0.9)),        # Body.
        ((0, -0.45, 2.12), (0.78, 0.62, 0.88)),   # Shoulders.
        ((0, 0.95, 1.9), (0.72, 0.6, 0.82)),      # Rump.
        ((0, -1.3, 2.42), (0.6, 0.52, 0.64)),     # Head.
        ((0, -1.62, 2.26), (0.44, 0.3, 0.48)),    # Face.
        ((0, -1.78, 1.95), (0.2, 0.12, 0.12)),    # Mouth.
    ]
    capsules = [(a, b, ra, rb) for a, b, ra, rb in zip(TRUNK, TRUNK[1:], TRUNK_R, TRUNK_R[1:])]
    for _x in (-LEG_X, LEG_X):
        capsules += [
            ((_x, FRONT_Y, 1.65), (_x, FRONT_Y, 0.3), 0.33, 0.28),
            ((_x, FRONT_Y - 0.02, 0.0), (_x, FRONT_Y - 0.02, 0.25), 0.31, 0.3),
            ((_x * 0.95, HIND_Y, 1.7), (_x, HIND_Y + 0.03, 0.3), 0.36, 0.28),
            ((_x, HIND_Y + 0.02, 0.0), (_x, HIND_Y + 0.02, 0.25), 0.31, 0.3),
        ]
    del _x
    # Hips high inside the body: the legs swing from the shoulder and the
    # pelvis. Knees a little off the straight line so they bend the right way.
    rig = ElephantRig(
        body=((0, 1.4, 2.0), (0, 0.2, 2.0)),
        chest=((0, 0.2, 2.0), (0, -0.75, 2.15)),
        neck=((0, -0.75, 2.15), (0, -1.1, 2.3)),
        head=((0, -1.1, 2.3), (0, -1.75, 2.25)),
        ears=((0.55, -1.12, 2.45), (1.05, -0.72, 2.4)),
        tail=TAIL + [(0, 1.68, 1.3)],
        legs={
            "F": ((LEG_X, FRONT_Y, 2.1), (LEG_X, FRONT_Y - 0.03, 0.95), (LEG_X, FRONT_Y, FOOT_TOP),
                  (LEG_X, FRONT_Y - 0.25, 0.0)),
            "H": ((LEG_X, HIND_Y, 2.1), (LEG_X, HIND_Y + 0.05, 0.95), (LEG_X, HIND_Y, FOOT_TOP),
                  (LEG_X, HIND_Y - 0.25, 0.0)),
        },
        leg_exit=(1.1, 1.5),
        leg_reach=0.45,
        # Elephants never trot: the run is a faster walk with the same
        # footfall order and no flight phase (duty above one half).
        # Short quick steps: the knees give by a quarter of the stride,
        # and an elephant's legs should stay close to straight.
        walk=rigs.Gait(speed=1.3, frames=24, duty=0.66, lift=0.17, crouch=0.05, bob=0.01,
                       phases=rigs.WALK_PHASES, nod=2.0, wag=10.0),
        run=rigs.Gait(speed=2.2, frames=18, duty=0.55, lift=0.2, crouch=0.06, bob=0.015,
                      phases=rigs.WALK_PHASES, nod=3.0, wag=14.0),
        lie_height=0.85,
        blend=0.15,
        idle_frames=120,
        eat_frames=150,
        die_frames=60,
    )

    def paint(self, c, n):
        return "elephant"

    def details(self, mb):
        surface = mark_surface(mb)
        for s in (-1, 1):
            eye = on_surface(self, (s * 0.2, -1.5, 2.5), (s, -0.55, 0.05), 0.02)
            mb.sphere(eye, 0.05, "eye", segments=6, rings=4)
            # A big ear fanned back from the side of the head, folded once
            # so its two halves catch the light differently.
            top, mid, bottom = (s * 0.5, -1.18, 2.88), (s * 0.58, -1.12, 2.45), (s * 0.55, -1.1, 1.98)
            back = (s * 1.1, -0.7, 2.35)
            studies.plate(mb, [top, (s * 0.8, -0.94, 3.02), (s * 1.03, -0.76, 2.78), back, mid], 0.06, "ear")
            studies.plate(mb, [mid, back, (s * 1.02, -0.75, 1.9), (s * 0.8, -0.92, 1.55), bottom], 0.06,
                          "elephant_shade")
            # A tusk curving forward and up from the mouth.
            pts = [Vector((s * 0.2, -1.8, 2.0)), Vector((s * 0.25, -2.08, 1.78)),
                   Vector((s * 0.26, -2.38, 1.78)), Vector((s * 0.22, -2.56, 1.95))]
            radii = [0.075, 0.062, 0.045, 0.0]
            for (a, b), (ra, rb) in zip(zip(pts, pts[1:]), zip(radii, radii[1:])):
                mb.cylinder(a, b, ra, rb, "tusk", segments=6)
        for a, b in zip(TAIL, TAIL[1:]):
            mb.cylinder(a, b, 0.05, 0.04, "elephant", segments=5)
        studies.plate(mb, [(0, 1.64, 1.56), (0.0, 1.7, 1.5), (0, 1.72, 1.32), (0, 1.63, 1.36)], 0.06, "eye")
        surface_first(mb, surface)


SPECS = [Elephant()]
