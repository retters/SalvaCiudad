"""Shark: blue-grey back and white belly with a crisp border, a pointed
snout, an open mouth with a dark inside and white triangular teeth, and
flat dorsal, pectoral and tail fins."""

import math

from mathutils import Vector

import common
import rigs_swim
import studies

BODY_Z = 0.42
# Belly border: a plane through BELLY_P, the belly below it.
BELLY_P, BELLY_N = Vector((0, 0, 0.38)), Vector((0, -0.08, 1)).normalized()
# The open mouth: a wedge between two planes through the jaw hinge (on X).
HINGE = Vector((0, -0.85, 0.29))
UPPER = Vector((0, -1.4, 0.4))   # A point of the upper lip plane in front.
LOWER = Vector((0, -1.3, 0.04))    # A point of the lower lip plane in front.
MOUTH_FRONT = -1.36               # Nothing of the mouth in front of this.
EYE = (0.2, -1.12, 0.52)
TOOTH_STEP, TOOTH_W, TOOTH_H = 0.075, 0.028, 0.075


def lip_normal(front, up):
    """The normal of a lip plane through the hinge and `front`, facing
    `up` (+1: away from the mouth, above the upper lip)."""
    d = front - HINGE
    n = Vector((0, -d.z, d.y)).normalized()
    return n if n.z * up > 0 else -n


UPPER_N = lip_normal(UPPER, 1)
LOWER_N = lip_normal(LOWER, -1)


def near_mouth(c, n):
    return c.y < HINGE.y + 0.05 and abs(c.x) < 0.3 and c.z < 0.45


def in_mouth(c):
    return (c.y < HINGE.y and c.y > MOUTH_FRONT and (c - HINGE).dot(UPPER_N) < 0
            and (c - HINGE).dot(LOWER_N) < 0)


class Shark(studies.Spec):
    name = "shark"
    colors = {
        "blue": common.rgb(0x4D7FB8),
        "blue_light": common.rgb(0x5E91C8),
        "blue_shade": common.rgb(0x416FA3),
        "belly": common.rgb(0xF1F3F5),
        "mouth": common.rgb(0x5A1F2A),
        "tooth": common.rgb(0xFFFFFF),
        "eye": common.rgb(0x101216),
    }
    ellipsoids = [
        ((0.0, -0.25, BODY_Z), (0.36, 0.9, 0.42)),    # Chest and belly.
        ((0.0, -0.95, 0.38), (0.27, 0.5, 0.3)),       # Head.
        ((0.0, -1.3, 0.42), (0.14, 0.3, 0.14)),       # Snout.
    ]
    capsules = [
        ((0.0, 0.4, 0.45), (0.0, 1.05, 0.5), 0.3, 0.14),  # Back half.
        ((0.0, 1.05, 0.5), (0.0, 1.4, 0.53), 0.14, 0.07),  # Tail stalk.
    ]
    cuts = [(BELLY_P, BELLY_N, lambda c, n: True),
            (HINGE, UPPER_N, near_mouth),
            (HINGE, LOWER_N, near_mouth)]
    budget = 650
    max_tris = 1500
    tone_material = "blue"
    rig = rigs_swim.Fish(
        spine=[(0, -1.6, 0.42), (0, -0.8, 0.42), (0, -0.35, 0.43), (0, 0.15, 0.44), (0, 0.55, 0.46),
               (0, 0.9, 0.49), (0, 1.2, 0.51), (0, 1.47, 0.53)],
        fins={
            "fin.L": ((0.27, -0.42, 0.29), (0.85, 0.12, 0.04), "body"),
            "fin.R": ((-0.27, -0.42, 0.29), (-0.85, 0.12, 0.04), "body"),
            "dorsal": ((0, -0.1, 0.78), (0, 0.25, 1.3), "spine.1"),
            "lobe.U": ((0, 1.4, 0.56), (0, 1.88, 1.18), "spine.5"),
            "lobe.L": ((0, 1.4, 0.5), (0, 1.77, 0.12), "spine.5"),
        },
        jaw=(HINGE, (0, -1.3, 0.07), UPPER_N, LOWER_N),
    )

    def paint(self, c, n):
        if in_mouth(c):
            return "mouth"
        if (c - BELLY_P).dot(BELLY_N) < 0:
            return "belly"
        return "blue"

    def details(self, mb):
        open_mouth(mb)
        teeth(mb)
        for s in (-1, 1):
            mb.sphere((s * EYE[0], EYE[1], EYE[2]), 0.042, "eye", segments=6, rings=4)
            # Pectoral fins: swept back and down.
            studies.plate(mb, [(s * 0.25, -0.6, 0.28), (s * 0.3, -0.25, 0.3), (s * 0.85, 0.12, 0.04)],
                          0.04, "blue")
            # Small pelvic fins.
            studies.plate(mb, [(s * 0.12, 0.55, 0.22), (s * 0.15, 0.75, 0.27), (s * 0.35, 0.85, 0.08)],
                          0.03, "blue")
        # Dorsal fin: tall and swept back.
        studies.plate(mb, [(0, -0.35, 0.78), (0, 0.15, 0.8), (0, 0.28, 1.35)], 0.05, "blue")
        # Tail fin: a big upper lobe and a smaller lower one.
        studies.plate(mb, [(0, 1.3, 0.5), (0, 1.5, 0.66), (0, 1.9, 1.2), (0, 1.8, 1.14), (0, 1.62, 0.5)],
                      0.05, "blue")
        studies.plate(mb, [(0, 1.32, 0.52), (0, 1.62, 0.5), (0, 1.8, 0.12), (0, 1.7, 0.1), (0, 1.45, 0.38)],
                      0.05, "blue")
        # Second dorsal fin, small.
        studies.flap(mb, (0, 0.95, 0.7), (0, 1.1, 0.67), (0, 1.15, 0.84), 0.03, "blue")


def open_mouth(mb):
    """Sinks the mouth faces into the head, toward the jaw hinge, so the
    mouth reads as an opening and not as paint."""
    index = mb.materials.index("mouth")
    verts = {v for f in mb.bm.faces if f.material_index == index for v in f.verts}
    border = {v for v in verts if any(f.material_index != index for f in v.link_faces)}
    for v in verts - border:
        v.co = Vector((v.co.x * 0.65, v.co.y + 0.16, v.co.z))
    mb.bm.normal_update()


def teeth(mb):
    """Small white triangles along both lips, evenly spaced along each lip
    and pointing into the mouth."""
    index = mb.materials.index("mouth")
    border = [v for v in {v for f in mb.bm.faces if f.material_index == index for v in f.verts}
              if any(f.material_index != index for f in v.link_faces)]
    for lip, sign in ((UPPER_N, -1), (LOWER_N, 1)):
        edge = [v.co.copy() for v in border if abs((v.co - HINGE).dot(lip)) < 0.03 and v.co.y < HINGE.y - 0.1]
        # Around the mouth from one corner to the other.
        edge.sort(key=lambda p: math.atan2(p.x, HINGE.y - p.y))
        for p, tangent in resample(edge, TOOTH_STEP):
            side = tangent * TOOTH_W
            tip = p + Vector((0, -0.25 * sign, sign)).normalized() * TOOTH_H
            studies.flap(mb, p - side, p + side, tip, 0.02, "tooth")


def resample(points, step):
    """Points every `step` along a polyline, with the direction there."""
    out = []
    dist = step * 0.5
    for a, b in zip(points, points[1:]):
        seg = (b - a).length
        while seg > 1e-6 and dist < seg:
            out.append((a.lerp(b, dist / seg), (b - a).normalized()))
            dist += step
        dist -= seg
    return out


SPECS = [Shark()]
