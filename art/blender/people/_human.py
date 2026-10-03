"""The shared body of the low-poly characters: one anatomy for every
character, so they share proportions now and a skeleton later.

A character subclasses Human, sets a few proportions, and overrides:
- customize(parts): add, replace or remove welded body parts (a tail, a
  muzzle, a robe's skirt, digitigrade feet);
- paint(c, n): the material of each face, usually by zone(c) (which body
  part the point belongs to) and by height (self.z["waist"]...);
- cuts / bands: where color borders must be crisp (a sleeve's end, a boot's
  top, a belt);
- details(mb): hair, ears, belts, pouches, pauldrons, capes, weapons.

Stance: standing on Z = 0, facing -Y, arms a little away from the body
(the pose of the reference pictures). `.L` is the character's left (+X).
All measures are for a 1.8 m body and scale with `height`.
"""

from mathutils import Vector

import studies

# Heights of the landmarks of a 1.8 m body.
LANDMARKS = {
    "sole": 0.0, "ankle": 0.09, "knee": 0.5, "crotch": 0.86, "hip": 0.95, "waist": 1.1, "chest": 1.32,
    "shoulder": 1.46, "neck": 1.52, "chin": 1.59, "eyes": 1.7, "top": 1.8,
}


class Human(studies.Spec):
    height = 1.8        # Meters, to the top of the head (hair and hats excluded).
    female = False
    shoulder = 0.18     # Half width at the shoulder joints (of a 1.8 m body).
    hip = 0.095         # Half distance between the legs.
    build = 1.0         # Thickness of limbs and trunk: 0.85 slender, 1.3 brawny.
    # Measured on the reference pictures: the head is about a tenth of the
    # height and the chest a fifth, with the arms hanging close to the body.
    head_size = 0.9
    max_tris = 3000
    budget = 1300
    rigged = True       # Gets the shared skeleton and clips (rigs_human.Humanoid).
    far_tris = 500      # Triangles of its far version, "<name>_far.glb" (rigs.animate).

    def __init__(self):
        self.k = self.height / 1.8
        self.z = {name: z * self.k for name, z in LANDMARKS.items()}
        # The face follows the head's size.
        self.z["eyes"] = (1.8 - 0.112 * self.head_size) * self.k
        self.z["chin"] = (1.8 - 0.235 * self.head_size) * self.k
        self.parts = self.body_parts()
        self.customize(self.parts)
        self.ellipsoids = [(p[1], p[2]) for p in self.parts.values() if p[0] == "ellipsoid"]
        self.capsules = [(p[1], p[2], p[3], p[4]) for p in self.parts.values() if p[0] == "capsule"]
        if self.rigged:
            self.rig = self.make_rig()

    def make_rig(self):
        """Hook: the character's skeleton. Override to add bones (a tail,
        a cape) or to say which bone the character's own parts follow."""
        import rigs_human
        return rigs_human.Humanoid(self)

    # ----------------------------------------------------------- building

    def P(self, x, y, z):
        """A point of the 1.8 m body, scaled to this character."""
        return (x * self.k, y * self.k, z * self.k)

    def ellipsoid(self, center, radii):
        return ("ellipsoid", self.P(*center), tuple(r * self.k for r in radii))

    def capsule(self, a, b, ra, rb):
        return ("capsule", self.P(*a), self.P(*b), ra * self.k, rb * self.k)

    def joints(self):
        """Where the limbs bend, for a 1.8 m body (left side; mirror X)."""
        s, h = self.shoulder, self.hip
        return {
            "shoulder": (s, 0.0, 1.45), "elbow": (s + 0.05, 0.01, 1.17), "wrist": (s + 0.08, -0.02, 0.93),
            "hand": (s + 0.09, -0.03, 0.83),
            "hip": (h, 0.0, 0.92), "knee": (h + 0.012, -0.01, 0.5), "ankle": (h + 0.02, 0.01, 0.1),
            "toe": (h + 0.03, -0.17, 0.05),
        }

    def body_parts(self):
        """The welded parts, by name. Limbs end in ".L" and ".R"."""
        b, f = self.build, self.female
        s = self.shoulder
        j = self.joints()
        hs = self.head_size
        parts = {
            # The top of the head stays at 1.8 m whatever its size.
            "head": self.ellipsoid((0, -0.01, 1.8 - 0.118 * hs), (0.09 * hs, 0.105 * hs, 0.118 * hs)),
            "jaw": self.ellipsoid((0, -0.035, 1.8 - 0.178 * hs), (0.072 * hs, 0.075 * hs, 0.06 * hs)),
            "neck": self.capsule((0, 0.005, 1.49), (0, -0.005, 1.8 - 0.2 * hs), 0.05 * b, 0.046 * b),
            "chest": self.ellipsoid((0, 0.0, 1.33), (s * (0.95 if f else 1.0), 0.115 * b, 0.18)),
            "waist": self.ellipsoid((0, 0.0, 1.13), ((0.12 if f else 0.145) * b, 0.098 * b, 0.15)),
            "hips": self.ellipsoid((0, 0.005, 0.96), ((0.17 if f else 0.16) * b, 0.115 * b, 0.13)),
        }
        if f:
            for side, x in ((".L", 1), (".R", -1)):
                parts["bust" + side] = self.ellipsoid((x * 0.065, -0.085, 1.33), (0.06, 0.055, 0.057))
        for side, x in ((".L", 1), (".R", -1)):
            def m(p, x=x):
                return (p[0] * x, p[1], p[2])
            parts["shoulder" + side] = self.ellipsoid(m(j["shoulder"]), (0.06 * b, 0.06 * b, 0.062 * b))
            parts["upper_arm" + side] = self.capsule(m(j["shoulder"]), m(j["elbow"]), 0.056 * b, 0.048 * b)
            parts["forearm" + side] = self.capsule(m(j["elbow"]), m(j["wrist"]), 0.048 * b, 0.04 * b)
            parts["hand" + side] = self.ellipsoid(m(j["hand"]), (0.034 * b, 0.048 * b, 0.075))
            parts["thigh" + side] = self.capsule(m(j["hip"]), m(j["knee"]), (0.095 if f else 0.092) * b, 0.066 * b)
            parts["shin" + side] = self.capsule(m(j["knee"]), m(j["ankle"]), 0.066 * b, 0.048 * b)
            parts["foot" + side] = self.capsule(m((j["ankle"][0], 0.035, 0.055)), m(j["toe"]), 0.055 * b, 0.047 * b)
        return parts

    def customize(self, parts):
        """Hook: change the welded parts (same tuples as body_parts)."""

    # ----------------------------------------------------------- painting

    def zone(self, c):
        """The name of the body part nearest to point c ("chest",
        "forearm.L"...), to paint clothes by region."""
        best, name = 1e9, None
        for part_name, p in self.parts.items():
            if p[0] == "ellipsoid":
                center, r = p[1], p[2]
                q = Vector(((c.x - center[0]) / r[0], (c.y - center[1]) / r[1], (c.z - center[2]) / r[2]))
                d = (q.length - 1.0) * min(r)
            else:
                a, b = Vector(p[1]), Vector(p[2])
                ab = b - a
                t = max(0.0, min(1.0, (Vector(c) - a).dot(ab) / max(ab.dot(ab), 1e-12)))
                d = (Vector(c) - (a + ab * t)).length - (p[3] + (p[4] - p[3]) * t)
            if d < best:
                best, name = d, part_name
        return name

    # ------------------------------------------------------------ details

    def eyes(self, mb, mat="eye", spread=0.036, forward=None, radius=0.013):
        """Two small dark eyes on the face. `forward` is how far in front of
        the head's center they sit (default: on the head's surface)."""
        center = Vector(self.parts["head"][1])
        radii = self.parts["head"][2]
        x = spread * self.k
        z = self.z["eyes"]
        if forward is None:
            inside = 1.0 - (x / radii[0]) ** 2 - ((z - center.z) / radii[2]) ** 2
            forward = radii[1] * max(0.0, inside) ** 0.5
        for s in (-1, 1):
            mb.sphere((s * x, center.y - forward, z), radius * self.k, mat, segments=6, rings=4,
                      scale=(1.0, 0.5, 1.0))
