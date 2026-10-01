"""Knight (woman): red hair in a big high ponytail, pointed steel pauldrons,
a silver breastplate and armored skirt plates with blue trim, a blue
collar, bracers, dark leggings, steel greaves and heeled boots, leather
straps and a belt with pouches."""

import math

from mathutils import Vector

import common
import studies
from rigs import Bone, X, Z, smooth
from lizardfolk import (Folk, along, belt, buckle, hip_ring, hull, panel, pouch, recolor, skirt, spike, strip, sym_y,
                        tube)


class KnightWoman(Folk):
    name = "knight_woman"
    female = True
    height = 1.7
    shoulder = 0.142
    hip = 0.085
    build = 0.75
    head_size = 0.84
    jaw = 0.88
    budget = 1050
    colors = {
        "skin": common.rgb(0xFDB687),
        "hair": common.rgb(0xBC4332),
        "steel": common.rgb(0x8D8AA4),
        "steel_light": common.rgb(0xBDB6C6),
        "steel_shade": common.rgb(0x6C6C84),
        "plate": common.rgb(0xDDD0D2),
        "blue": common.rgb(0x35569E),
        "dark": common.rgb(0x353248),
        "leather": common.rgb(0x7A4B34),
        "leather_dark": common.rgb(0x4E3126),
        "eye": common.rgb(0x1A1414),
    }
    BELT = 1.165
    HEM = 0.83
    HANG = 0.2
    PONYTAIL = [(0.0, 0.08, 0.07), (0.0, 0.17, 0.135), (-0.01, 0.26, 0.13), (-0.02, 0.33, 0.04),
                (-0.03, 0.34, -0.09), (-0.035, 0.315, -0.22), (-0.04, 0.28, -0.35)]

    def extra_bones(self):
        return [Bone("ponytail", self.hp(*self.PONYTAIL[1]), self.hp(*self.PONYTAIL[-1]), parent="head")]

    def ponytail_weights(self, p):
        """The ponytail follows the head at its root and its own bone beyond."""
        bone = self.rig.by_name["ponytail"]
        f = smooth((p - bone.head).dot((bone.tail - bone.head).normalized()) / (0.12 * self.k) + 0.5)
        return [("head", 1.0 - f), ("ponytail", f)]

    def animate(self, clip, t, pose):
        """The ponytail lags behind the head's bobbing."""
        p = 2 * math.pi * t
        swing = {"walk": 5.0, "run": 9.0}.get(clip, 1.5)
        pose.turn("ponytail", X, swing * math.sin(2 * p + 0.8))
        pose.turn("ponytail", Z, swing * 0.6 * math.sin(p))

    def __init__(self):
        super().__init__()
        k = self.k
        torso = lambda c, n: abs(c.x) < 0.2 * k and self.BELT * k < c.z < 1.5 * k  # noqa: E731
        for x in (-0.045, 0.045):            # The breastplate's blue sides.
            self.cuts.append(((x * k, 0, 0), (1, 0, 0), lambda c, n: torso(c, n) and c.z < 1.3 * k and c.y < 0))
        self.level_cut(1.43, torso)          # The breastplate's top.
        self.level_cut(1.575, lambda c, n: abs(c.x) < 0.1 * k)   # Collar.
        for side in (".L", ".R"):
            self.limb_cut("upper_arm" + side, 0.3)
            self.limb_cut("forearm" + side, 0.12)
            hand = self.parts["hand" + side]
            self.cuts.append(((0, 0, hand[1][2] - 0.01 * k), (0, 0, 1), self.near("hand" + side)))

    def customize(self, parts):
        E, C = self.ellipsoid, self.capsule
        self.small_head(parts)
        # A narrow waist over wide hips, as in the picture.
        parts["chest"] = E((0, 0.0, 1.345), (0.108, 0.095, 0.16))
        parts["waist"] = E((0, 0.0, 1.2), (0.071, 0.068, 0.13))
        parts["hips"] = E((0, 0.005, 1.02), (0.128, 0.098, 0.15))
        for side, x in ((".L", 1), (".R", -1)):
            j = {n: (p[0] * x, p[1], p[2]) for n, p in self.joints().items()}
            parts["bust" + side] = E((x * 0.058, -0.075, 1.36), (0.056, 0.05, 0.053))
            parts["upper_arm" + side] = C(j["shoulder"], j["elbow"], 0.034, 0.029)
            parts["forearm" + side] = C(j["elbow"], j["wrist"], 0.036, 0.029)     # Bracer.
            parts["thigh" + side] = C(j["hip"], j["knee"], 0.064, 0.045)
            parts["shin" + side] = C(j["knee"], j["ankle"], 0.043, 0.03)
            parts["hand" + side] = E((j["hand"][0], j["hand"][1], j["hand"][2] + 0.02), (0.026, 0.036, 0.048))

    def paint(self, c, n):
        k, zone = self.k, self.zone(c)
        if zone in ("head", "jaw"):
            return "skin"
        if zone == "neck":
            return "skin" if c.z > 1.575 * k else "blue"
        if zone.startswith("shoulder"):
            return "blue"
        if zone.startswith("upper_arm"):
            return "blue" if along(self.parts[zone], c) < 0.3 else "skin"
        if zone.startswith("forearm"):
            return "skin" if along(self.parts[zone], c) < 0.12 else "plate"
        if zone.startswith("hand"):
            return "dark" if c.z > self.parts[zone][1][2] - 0.01 * k else "skin"
        if zone.startswith("thigh"):
            return "dark"
        if zone.startswith(("shin", "foot")):
            return "steel_shade"
        if c.z < self.BELT * k:
            return "blue"
        if c.z > 1.43 * k:
            return "skin" if c.y < 0.02 * k else "blue"
        if zone.startswith("bust") or (abs(c.x) < 0.045 * k and c.y < 0):
            return "plate"
        return "blue"

    def details(self, mb):
        k, V, rig = self.k, self.V, self.rig
        self.begin(mb)
        self.head(mb)
        self.face(mb, brow="leather_dark", stern=0.006, nose=0.85)
        self.hair(mb)
        # A steel gem on the collar.
        self.tag(mb, "chest")
        spike(mb, V(0, -0.052, 1.56), V(0, -0.062, 1.485), 0.045 * k, "steel_light", thickness=0.02 * k,
              across=(1, 0, 0))
        for s in (-1, 1):
            # Pauldrons: angular plates with a tall point by the neck.
            side = "L" if s > 0 else "R"
            self.tag(mb, rig.shoulder(side))
            sh = self.J("shoulder", s)
            verts = hull(mb, [sh + Vector((s * x, y, z)) * k for x, y, z in sym_y([
                (-0.045, 0.05, 0.05), (-0.02, 0.0, 0.135), (0.03, 0.085, 0.035), (0.095, 0.07, -0.04),
                (0.115, 0.0, 0.02), (0.105, 0.0, -0.085), (0.02, 0.075, -0.03)])], "plate")
            recolor(mb, verts, lambda c, n: "steel_light" if n.z < -0.1 else None)
            # Bracers: a faceted sleeve under a flared blue cuff.
            self.tag(mb, "lower_arm." + side)
            a, b = self.J("elbow", s), self.J("wrist", s)
            mb.cylinder(a.lerp(b, 0.14), a.lerp(b, 1.0), 0.044 * k, 0.034 * k, "plate", segments=6)
            mb.cylinder(a.lerp(b, 0.0), a.lerp(b, 0.22), 0.05 * k, 0.04 * k, "blue", segments=6)
        # Leg armor: greaves with a light front, knee plates, heeled boots.
        self.greaves(mb, "steel", front="plate", size=0.7)
        self.knee_guard(mb, "plate", size=1.25)
        self.sabatons(mb, "steel", size=0.72, heel=0.04)
        # Leather straps over the shoulders, front and back.
        self.tag(mb, rig.torso)
        for s in (-1, 1):
            strip(mb, [V(s * 0.07, -0.06, 1.47), V(s * 0.072, -0.128, 1.375), V(s * 0.07, -0.075, 1.19)],
                  [(0, -1, 0.5), (0, -1, 0), (0, -1, -0.3)], 0.028 * k, 0.014 * k, "leather")
            strip(mb, [V(s * 0.07, 0.07, 1.47), V(s * 0.07, 0.1, 1.36), V(s * 0.07, 0.078, 1.19)],
                  [(0, 1, 0.4), (0, 1, 0), (0, 1, -0.2)], 0.028 * k, 0.014 * k, "leather")
        # Belt with a buckle and two pouches.
        self.tag(mb, "hips")
        at = belt(mb, self, self.BELT * k, 0.05 * k, "leather_dark", pad=0.012 * k)
        buckle(mb, at, "steel_light", size=0.058 * k)
        buckle(mb, at, "leather_dark", size=0.027 * k, depth=0.018 * k)
        pouch(mb, at, -62, (0.075 * k, 0.04 * k, 0.085 * k), "leather", drop=0.01 * k, flap="leather_dark")
        pouch(mb, at, 70, (0.06 * k, 0.035 * k, 0.065 * k), "leather", drop=0.01 * k, flap="leather_dark")
        # A short blue skirt under pointed plates.
        self.tag(mb, rig.drape)
        angles = tuple(range(0, 360, 40))
        top = [at(a, dz=-0.015 * k) for a in angles]
        hips = hip_ring(self, angles, 1.02 * k, 0.014 * k)
        low = [Vector((p.x * 1.14, p.y * 1.16, self.HEM * k)) for p in hips]
        skirt(mb, [top, hips, low], "blue", inner="dark", thickness=0.012 * k, closed=True)
        y0, y1 = top[0].y - 0.012 * k, low[0].y - 0.014 * k
        zt = top[0].z
        studies.plate(mb, [(-0.05 * k, y0, zt), (0.05 * k, y0, zt), (0.062 * k, y1, 0.9 * k),
                           (0.0, y1 - 0.008 * k, 0.745 * k), (-0.062 * k, y1, 0.9 * k)], 0.014 * k, "plate")
        for a, mat, drop, point in ((-50, "steel_light", 0.18, 0.08), (50, "steel_light", 0.18, 0.08),
                                    (-105, "plate", 0.2, 0.07), (105, "plate", 0.2, 0.07),
                                    (-152, "steel_light", 0.19, 0.07), (152, "steel_light", 0.19, 0.07),
                                    (180, "plate", 0.2, 0.09)):
            panel(mb, at, a, 0.095 * k, drop * k, mat, point=point * k, flare=0.045 * k, dz=-0.02 * k,
                  lift=0.004 * k, taper=1.05)
        self.fingers(mb, "skin")
        self.tone(mb, ["steel"], 0.4)
        self.done(mb)

    def hair(self, mb):
        """Red hair combed back into a big high ponytail, with a fringe
        swept to one side and locks framing the face."""
        u = self.head_size * self.k
        self.hair_hull(mb, "hair", [
            (0.0, -0.109, 0.066), (0.072, -0.1, 0.055), (0.035, -0.12, 0.125),       # Hairline and fringe.
            (0.0, -0.02, 0.16), (0.09, 0.0, 0.122),
            (0.104, -0.04, 0.03), (0.104, 0.04, -0.03),                              # Sides.
            (0.0, 0.135, 0.06), (0.066, 0.122, -0.03), (0.0, 0.12, -0.05)])
        self.shards(mb, "hair", [
            ((0.075, -0.085, 0.05), (0.096, -0.078, -0.11), 0.06),
            ((-0.075, -0.085, 0.05), (-0.092, -0.08, -0.09), 0.06),
            ((0.03, -0.1, 0.1), (-0.075, -0.118, 0.025), 0.09),
            ((0.0, -0.1, 0.1), (0.08, -0.115, 0.03), 0.08)])
        with self.bound(mb, self.ponytail_weights):
            tube(mb, [self.hp(*p) for p in self.PONYTAIL],
                 [r * u for r in (0.06, 0.09, 0.108, 0.112, 0.098, 0.066, 0.0)], "hair", sides=5)


SPECS = [KnightWoman()]
