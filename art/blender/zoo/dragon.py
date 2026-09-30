"""Dragon: red, standing on four legs, with an orange-yellow belly, a long
S-curved neck and a long tail ending in a spade, golden horns and spikes
along the back, and big bat wings raised: membrane panels stretched
between finger bones."""

import random

from mathutils import Vector

import common
import studies

X_LEG = 0.55
FRONT_LEG = [((X_LEG * 0.9, -0.95, 1.55), (X_LEG * 1.05, -0.72, 0.85), 0.32, 0.21),
             ((X_LEG * 1.05, -0.72, 0.85), (X_LEG * 1.05, -1.05, 0.17), 0.2, 0.16),
             ((X_LEG * 1.05, -1.03, 0.14), (X_LEG * 1.05, -1.38, 0.12), 0.18, 0.13)]
HIND_LEG = [((X_LEG, 0.65, 1.1), (X_LEG * 1.05, 1.05, 0.55), 0.32, 0.19),
            ((X_LEG * 1.05, 1.05, 0.55), (X_LEG * 1.05, 0.9, 0.17), 0.17, 0.16),
            ((X_LEG * 1.05, 0.92, 0.14), (X_LEG * 1.05, 0.56, 0.12), 0.18, 0.13)]
THIGH = ((X_LEG * 0.9, 0.55, 1.3), (0.32, 0.6, 0.62))
NECK = [(0.0, -1.4, 2.05), (0.0, -1.95, 2.65), (0.0, -2.15, 3.15), (0.0, -2.3, 3.38)]
NECK_R = [0.45, 0.33, 0.27, 0.26]
TAIL = [(0.0, 1.2, 1.7), (0.0, 2.1, 1.3), (0.15, 2.9, 0.85), (0.55, 3.5, 0.55), (1.05, 3.85, 0.4)]
TAIL_R = [0.42, 0.3, 0.2, 0.13, 0.08]
HEAD_Z = 3.42
HEAD = ((0.0, -2.42, HEAD_Z), (0.31, 0.42, 0.3))
SNOUT = ((0.0, -2.6, HEAD_Z - 0.06), (0.0, -3.1, HEAD_Z - 0.16), 0.23, 0.15)
JAW = ((0.0, -2.45, HEAD_Z - 0.22), (0.0, -2.95, HEAD_Z - 0.3), 0.17, 0.1)
EYE = (0.25, -2.66, HEAD_Z + 0.08)
# Wing, right side: shoulder, elbow, wrist, the finger tips (front to
# back) and where the membrane meets the back.
SHOULDER, ELBOW, WRIST = Vector((0.42, -0.75, 2.3)), Vector((1.25, -0.55, 3.35)), Vector((1.7, -0.15, 4.25))
FINGERS = [Vector(p) for p in ((2.6, 0.35, 4.45), (2.55, 1.25, 3.7), (2.15, 1.95, 2.8), (1.45, 2.1, 2.1))]
BACK = Vector((0.36, 1.0, 2.15))
SPINE = [(0.0, -2.2, HEAD_Z - 0.1), (0.0, -1.95, 2.65), (0.0, -1.4, 2.05), (0.0, -0.9, 1.9), (0.0, 0.4, 1.7),
         (0.0, 1.2, 1.7), (0.0, 2.1, 1.3), (0.15, 2.9, 0.85), (0.55, 3.5, 0.55)]


def tone_faces(mb, mat, share, seed=11):
    """Facet tones for a second material (finish() only tones one): turns a
    share of its faces into <mat>_light and <mat>_shade."""
    if mat not in mb.materials:
        return
    rnd = random.Random(seed)
    main = mb.materials.index(mat)
    light, shade = mb._material_index(mat + "_light"), mb._material_index(mat + "_shade")
    for f in mb.bm.faces:
        if f.material_index == main:
            r = rnd.random()
            if r < share * 0.5:
                f.material_index = light
            elif r < share:
                f.material_index = shade


def near_capsule(c, caps, margin):
    """Whether point c is within `margin` of any of the capsules."""
    for a, b, ra, rb in caps:
        a, b = Vector(a), Vector(b)
        ba = b - a
        h = max(0.0, min(1.0, (c - a).dot(ba) / ba.dot(ba)))
        if (c - a - ba * h).length < ra + (rb - ra) * h + margin:
            return True
    return False


def mirror(p, s):
    return Vector((s * p[0], p[1], p[2]))


def legs():
    return [(mirror(a, s), mirror(b, s), ra, rb) for s in (-1, 1) for a, b, ra, rb in FRONT_LEG + HIND_LEG]


def surface(spec, inside, direction):
    """Marches from a point inside the body along direction to the surface."""
    p, d = Vector(inside), Vector(direction).normalized()
    for _ in range(200):
        if studies.sdf(spec, p) > 0.0:
            return p
        p = p + d * 0.01
    return p


class Dragon(studies.Spec):
    name = "dragon"
    colors = {
        "red": common.rgb(0xD23A2A),
        "red_light": common.rgb(0xE04A34),
        "red_shade": common.rgb(0xB82E24),
        "belly": common.rgb(0xF6A623),
        "belly_light": common.rgb(0xFBC040),
        "belly_shade": common.rgb(0xEB8F1C),
        "membrane": common.rgb(0xF08A2A),
        "membrane_dark": common.rgb(0xE0602A),
        "horn": common.rgb(0xF2C230),
        "eye": common.rgb(0xFFE24A),
        "nostril": common.rgb(0x3A1410),
    }
    ellipsoids = [
        ((0.0, -0.9, 1.8), (0.68, 0.95, 0.68)),   # Chest.
        ((0.0, 0.35, 1.65), (0.62, 1.0, 0.62)),   # Belly and hips.
        THIGH, ((-THIGH[0][0], THIGH[0][1], THIGH[0][2]), THIGH[1]),
        HEAD,
    ]
    budget = 1400
    max_tris = 3000
    tone_material = "red"

    def __init__(self):
        self.capsules = (legs() + [SNOUT, JAW]
                         + [(a, b, ra, rb) for a, b, ra, rb in zip(NECK, NECK[1:], NECK_R, NECK_R[1:])]
                         + [(a, b, ra, rb) for a, b, ra, rb in zip(TAIL, TAIL[1:], TAIL_R, TAIL_R[1:])])
        self.legs = legs()

    def paint(self, c, n):
        if near_capsule(c, self.legs, 0.03):
            return "red"
        if n.z < -0.3 and abs(c.x) < 0.5:
            return "belly"  # Underside of the body, the tail and the jaw.
        if c.y < -1.25 and n.y < -0.35 and abs(c.x) < 0.25 and 1.7 < c.z < HEAD_Z - 0.25:
            return "belly"  # Front of the neck.
        return "red"

    def details(self, mb):
        tone_faces(mb, "belly", 0.3)
        for s in (-1, 1):
            self.wing(mb, s)
            mb.sphere(mirror(EYE, s), 0.05, "eye", segments=6, rings=4)
            mb.sphere(mirror((0.08, -3.22, HEAD_Z - 0.12), s), 0.03, "nostril", segments=6, rings=3)
            # Horns: two swept-back golden cones, bent once, and a small one on the cheek.
            base, bend, tip = (mirror((0.17, -2.3, HEAD_Z + 0.2), s), mirror((0.26, -2.0, HEAD_Z + 0.53), s),
                               mirror((0.3, -1.6, HEAD_Z + 0.68), s))
            mb.cylinder(base, bend, 0.1, 0.06, "horn", segments=6)
            mb.cylinder(bend, tip, 0.06, 0.004, "horn", segments=6)
            mb.cylinder(mirror((0.26, -2.35, HEAD_Z - 0.1), s), mirror((0.45, -2.05, HEAD_Z - 0.02), s),
                        0.06, 0.004, "horn", segments=5)
            # Claws: three golden cones on each foot.
            for leg in (FRONT_LEG, HIND_LEG):
                b = Vector(leg[2][1])
                for dx in (-0.1, 0.0, 0.1):
                    root = mirror(b, s) + Vector((dx, 0.02, -0.04))
                    mb.cylinder(root, root + Vector((dx * 0.4, -0.16, -0.06)), 0.045, 0.004, "horn", segments=5)
        self.spikes(mb)
        # Spade-shaped fin at the tail tip.
        t = Vector(TAIL[-1])
        d = (t - Vector(TAIL[-2])).normalized()
        side = d.cross(Vector((0, 0, 1))).cross(d).normalized()  # Upright, seen from the side.
        studies.plate(mb, [t - d * 0.1, t + side * 0.3 + d * 0.12, t + d * 0.6, t - side * 0.3 + d * 0.12],
                      0.06, "red")

    def wing(self, mb, s):
        sh, el, wr = mirror(SHOULDER, s), mirror(ELBOW, s), mirror(WRIST, s)
        tips = [mirror(f, s) for f in FINGERS]
        back = mirror(BACK, s)
        # Arm and finger bones.
        mb.cylinder(sh, el, 0.16, 0.12, "red", segments=6)
        mb.sphere(el, 0.12, "red", segments=6, rings=4)
        mb.cylinder(el, wr, 0.12, 0.08, "red", segments=6)
        mb.sphere(wr, 0.09, "red", segments=6, rings=4)
        mb.cylinder(wr, wr + (wr - el).normalized() * 0.25, 0.06, 0.004, "horn", segments=5)  # Thumb claw.
        for f in tips:
            mb.cylinder(wr, f, 0.06, 0.02, "red", segments=5)
        # Membrane: from the wrist, one pair of triangles per gap between
        # fingers, dipping toward the wrist between the tips (scalloped edge).
        ends = tips + [back]
        for i, (f0, f1) in enumerate(zip(ends, ends[1:])):
            mid = f0.lerp(f1, 0.5)
            dip = mid.lerp(wr, 0.18)
            mat = "membrane" if i % 2 == 0 else "membrane_dark"
            studies.plate(mb, [wr, f0, dip], 0.03, mat)
            studies.plate(mb, [wr, dip, f1], 0.03, mat)
        # Between the arm and the body.
        studies.plate(mb, [el, wr, back], 0.03, "membrane_dark")
        studies.plate(mb, [sh, el, back], 0.03, "membrane_dark")

    def spikes(self, mb):
        """Golden triangular spikes along the back, from the head to the tail."""
        pts = [Vector(p) for p in SPINE]
        for i, (a, b) in enumerate(zip(pts, pts[1:])):
            seg = (b - a).length
            count = max(1, int(seg / 0.32))
            for k in range(count):
                c = a.lerp(b, (k + 0.5) / count)
                tangent = (b - a).normalized()
                up = Vector((0, 0, 1)) - tangent * tangent.z
                up.normalize()
                top = surface(self, c, up) - up * 0.04
                size = 0.2 * (1.0 - 0.55 * max(0.0, c.y - 1.2) / 2.4)
                studies.flap(mb, top - tangent * size * 0.55, top + tangent * size * 0.55,
                             top + up * size * 1.1 + tangent * size * 0.5, 0.05, "horn")


SPECS = [Dragon()]
