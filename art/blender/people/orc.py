"""Orc: big, muscular and green, much broader than a human. A small
topknot, tusks and a heavy brow; a bare chest with crossed leather straps,
a fur pauldron with pale bone spikes on the right shoulder, big bracers, a
belt with a skull buckle, a ragged leather kilt and big wrinkled boots."""

import math

from mathutils import Quaternion, Vector

import common
from lizardfolk import HEAD_POINTS, Folk, along, belt, blob, follows, hull, panel, spike, strap, surface, sym, tube


class Orc(Folk):
    name = "orc"
    height = 2.05
    shoulder = 0.26
    hip = 0.12
    build = 1.4
    head_size = 1.0
    budget = 1150
    colors = {
        "skin": common.rgb(0x8FAE38),
        "skin_light": common.rgb(0xB2C845),
        "skin_shade": common.rgb(0x73902D),
        "hair": common.rgb(0x4A302B),
        "leather": common.rgb(0x85543C),
        "leather_dark": common.rgb(0x5E3F36),
        "boot": common.rgb(0x6B4534),
        "bone": common.rgb(0xE6CFB2),
        "yellow": common.rgb(0xE8C83A),
        "eye": common.rgb(0x1A1414),
    }
    BELT = 1.08
    HANG = 0.36     # The kilt's front panel, below the hip joints.

    def part_bones(self):
        out = {}
        for side in ("L", "R"):
            out["pec." + side] = out["trap." + side] = "chest"
        return out

    def animate(self, clip, t, pose):
        if clip in ("walk", "run", "carry_walk"):     # The big boots stay level: tipped down their toes would dig in.
            for side in ("L", "R"):
                pose.set_world("foot." + side, Quaternion())

    def __init__(self):
        super().__init__()
        self.level_cut(0.78, lambda c, n: c.z < self.z["hip"])   # Under the kilt.
        for side in (".L", ".R"):
            self.limb_cut("forearm" + side, 0.06)
            self.limb_cut("forearm" + side, 0.96)

    def customize(self, parts):
        E, C = self.ellipsoid, self.capsule
        self.small_head(parts)
        parts["neck"] = C((0, 0.012, 1.47), (0, 0.0, 1.6), 0.095, 0.085)
        parts["chest"] = E((0, -0.005, 1.33), (0.25, 0.165, 0.2))
        parts["waist"] = E((0, 0.0, 1.13), (0.235, 0.14, 0.16))
        for side, x in ((".L", 1), (".R", -1)):
            j = {n: (p[0] * x, p[1], p[2]) for n, p in self.joints().items()}
            parts["pec" + side] = E((x * 0.11, -0.108, 1.365), (0.115, 0.07, 0.085))
            parts["trap" + side] = C((x * 0.06, 0.015, 1.52), (x * 0.21, 0.005, 1.47), 0.065, 0.075)
            parts["shoulder" + side] = E(j["shoulder"], (0.11, 0.105, 0.108))
            parts["upper_arm" + side] = C(j["shoulder"], j["elbow"], 0.084, 0.07)
            parts["forearm" + side] = C(j["elbow"], j["wrist"], 0.09, 0.076)       # Bracer.
            parts["hand" + side] = E((j["hand"][0], j["hand"][1], j["hand"][2] + 0.01), (0.056, 0.07, 0.08))
            parts["thigh" + side] = C(j["hip"], j["knee"], 0.105, 0.078)

    def paint(self, c, n):
        k, zone = self.k, self.zone(c)
        if zone.startswith(("shin", "foot")):
            return "boot"
        if zone.startswith("forearm"):
            return "leather" if 0.06 < along(self.parts[zone], c) < 0.96 else "skin"
        if zone.startswith("thigh"):
            return "leather_dark" if c.z > 0.78 * k else "skin"
        if zone in ("hips", "waist") and c.z < self.BELT * k:
            return "leather_dark"
        return "skin"

    def details(self, mb):
        k, V, rig = self.k, self.V, self.rig
        self.begin(mb)
        self.orc_head(mb)
        # Crossed straps, with a patch where they cross.
        self.tag(mb, rig.torso)
        for front in (True, False):
            strap(mb, self, [(-0.17 * k, 1.5 * k), (0.19 * k, 1.12 * k)], 0.075 * k, "leather_dark", front=front)
            strap(mb, self, [(0.17 * k, 1.5 * k), (-0.15 * k, 1.2 * k)], 0.06 * k, "leather", front=front)
        cross = surface(self, V(-0.01, 0, 1.33), (0, -1, 0))
        mb.box(cross + Vector((0, -0.012 * k, 0)), (0.09 * k, 0.03 * k, 0.09 * k), "leather", rotation_z=0.0)
        self.pauldron(mb)
        # Bracers: layered rims.
        for side in (".L", ".R"):
            self.tag(mb, "lower_arm" + side)
            part = self.parts["forearm" + side]
            a, b = Vector(part[1]), Vector(part[2])
            for t0, t1, r in ((0.04, 0.3, 0.113), (0.36, 0.6, 0.103), (0.66, 0.9, 0.093)):
                mb.cylinder(a.lerp(b, t0), a.lerp(b, t1), r * k, (r - 0.014) * k,
                            "leather" if t0 != 0.36 else "leather_dark", segments=6)
        # Belt with a skull.
        self.tag(mb, "hips")
        at = belt(mb, self, self.BELT * k, 0.11 * k, "leather", pad=0.018 * k, segments=10)
        self.skull(mb, at(0) + Vector((0, 0.012 * k, -0.02 * k)), k)
        # Kilt: ragged leather panels of uneven length, the front one longest.
        self.tag(mb, rig.drape)
        for a, width, drop, point, mat in (
                (0, 0.2, 0.35, 0.1, "leather"), (38, 0.18, 0.2, 0.08, "leather_dark"),
                (-38, 0.18, 0.23, 0.06, "leather_dark"), (76, 0.2, 0.25, 0.07, "leather"),
                (-76, 0.2, 0.21, 0.09, "leather"), (114, 0.2, 0.2, 0.08, "leather_dark"),
                (-114, 0.2, 0.24, 0.06, "leather_dark"), (150, 0.2, 0.24, 0.07, "leather"),
                (-150, 0.2, 0.2, 0.09, "leather"), (180, 0.2, 0.27, 0.08, "leather_dark")):
            panel(mb, at, a, width * k, drop * k, mat, point=point * k, flare=0.028 * k, thickness=0.02 * k,
                  dz=-0.04 * k, taper=0.9 if a else 0.8, lift=0.004 * k if a == 0 else 0.0)
        # Boots: wrinkled leather with folds, and a big foot.
        for s in (-1, 1):
            knee, ankle = self.J("knee", s), self.J("ankle", s)
            self.tag(mb, "shin.L" if s > 0 else "shin.R")
            ts = (-0.08, 0.1, 0.22, 0.42, 0.55, 0.74, 0.86, 0.98)
            radii = (0.108, 0.113, 0.1, 0.107, 0.095, 0.101, 0.092, 0.098)
            path = [knee.lerp(ankle, t) + Vector(((0.01, -0.008)[i % 2] * k, (0.006, -0.01)[i % 2] * k, 0))
                    for i, t in enumerate(ts)]
            tube(mb, path, [r * k for r in radii], "boot", sides=6)
            self.tag(mb, "foot.L" if s > 0 else "foot.R")
            a = Vector((ankle.x, ankle.y, 0.0))
            hull(mb, [a + Vector((s * 0.01 * (-y / 0.2) + x, y, z)) * k for x, y, z in sym([
                (0.0, -0.27, 0.0), (0.0, -0.255, 0.07), (0.088, -0.16, 0.0), (0.08, -0.15, 0.105),
                (0.0, -0.16, 0.13), (0.0, -0.05, 0.17), (0.085, 0.11, 0.0), (0.08, 0.11, 0.13), (0.09, -0.02, 0.15)])],
                 "boot")
        self.fingers(mb, "skin")
        self.tone(mb, ["skin"], 0.3)
        self.done(mb)

    @follows("head")
    def orc_head(self, mb):
        """A heavy head: a brow ridge, a wide jaw with an underbite and tusks,
        a broad nose, yellow eyes, pointed ears, and a topknot."""
        hp, u = self.hp, self.head_size * self.k
        self.head(mb, points=HEAD_POINTS + [(0.078, -0.108, 0.022), (0.0, -0.114, 0.026)], jaw_points=[
            (0.09, -0.055, -0.03), (0.088, 0.0, -0.09), (0.06, -0.106, -0.068), (0.048, -0.104, -0.12),
            (0.0, -0.112, -0.117), (0.05, -0.01, -0.115)])
        self.face(mb, brow=None, eye="yellow", ears=False, nose=1.5, forward=0.013)
        for s in (-1, 1):
            # Heavy brows shading the eyes.
            hull(mb, [hp(s * x, y, z) for x, y, z in ((0.008, -0.108, 0.016), (0.08, -0.1, 0.03), (0.08, -0.1, 0.05),
                                                      (0.008, -0.108, 0.04), (0.045, -0.125, 0.03))], "hair")
            spike(mb, hp(s * 0.084, 0.01, -0.015), hp(s * 0.128, 0.065, 0.035), 0.055 * u, "skin",
                  thickness=0.025 * u, across=(0, 0.3, 1))
            spike(mb, hp(s * 0.05, -0.1, -0.082), hp(s * 0.056, -0.122, -0.022), 0.032 * u, "bone")
        # Hair: a strip over the skull and a topknot.
        self.hair_hull(mb, "hair", [(0.04, -0.03, 0.118), (0.0, -0.04, 0.128), (0.045, 0.085, 0.09),
                                    (0.04, 0.115, -0.03), (0.0, 0.132, 0.0), (0.0, 0.03, 0.14), (0.0, 0.1, -0.075)])
        knot = hp(0.0, 0.04, 0.155)
        blob(mb, knot, (0.055 * u, 0.065 * u, 0.048 * u), "hair", count=12, seed=8)
        for d in ((0, 0.95, 0.3), (0.5, 0.6, 0.5), (-0.5, 0.7, 0.4), (0, 0.5, 0.9)):
            d = Vector(d).normalized()
            spike(mb, knot + d * (0.025 * u), knot + d * (0.08 * u), 0.06 * u, "hair")

    @follows(None)
    def pauldron(self, mb):
        """Fur over the right shoulder, ragged below, with stubby bone spikes."""
        k = self.k
        self.tag(mb, self.rig.shoulder("R"))
        c = self.J("shoulder", -1) + Vector((0.035, 0.0, 0.055)) * k
        r = Vector((0.185, 0.17, 0.115)) * k
        blob(mb, c, r, "leather", count=16, seed=4, rotate=((0, 1, 0), 22))
        # Tufts hanging around the lower edge.
        for i, a in enumerate(range(-150, 151, 30)):
            ang = math.radians(a)
            out = Vector((-math.cos(ang) * 0.85, math.sin(ang), 0.0))
            p = c + Vector((out.x * r.x * 0.9, out.y * r.y * 0.9, -0.035 * k + out.x * 0.07 * k))
            spike(mb, p, p + Vector((out.x * 0.02, out.y * 0.015, -0.1 - 0.03 * (i % 2))) * k, 0.11 * k,
                  "leather_dark" if i % 2 else "leather", thickness=0.04 * k, across=Vector((-out.y, out.x, 0.0)))
        for d, size in (((-0.3, -0.5, 0.8), 1.0), ((0.3, -0.35, 0.9), 1.1), ((-0.8, -0.3, 0.5), 0.9),
                        ((-0.4, 0.5, 0.8), 1.0), ((0.25, 0.45, 0.85), 0.9), ((-0.9, 0.35, 0.3), 0.8),
                        ((-0.1, -0.95, 0.3), 0.85), ((0.55, -0.75, 0.4), 0.8)):
            d = Vector(d).normalized()
            p = c + Vector((d.x * r.x, d.y * r.y, d.z * r.z)) * 0.8
            spike(mb, p, p + d * (0.085 * size * k), 0.11 * size * k, "bone")

    def skull(self, mb, p, k):
        """The belt buckle: a skull with dark sockets."""
        def q(x, y, z):
            return p + Vector((x, y, z)) * k
        hull(mb, [q(*o) for o in sym([(0.0, 0.0, 0.1), (0.05, 0.0, 0.085), (0.074, 0.0, 0.035), (0.066, 0.0, -0.02),
                                      (0.03, -0.05, 0.075), (0.058, -0.045, 0.02), (0.0, -0.06, 0.045),
                                      (0.04, -0.045, -0.025)])], "bone")
        hull(mb, [q(*o) for o in sym([(0.042, 0.0, -0.02), (0.03, 0.0, -0.09), (0.036, -0.04, -0.025),
                                      (0.026, -0.034, -0.09)])], "bone")
        for s in (-1, 1):
            hull(mb, [q(s * x, y, z) for x, y, z in ((0.012, -0.056, 0.028), (0.05, -0.05, 0.036),
                                                     (0.052, -0.05, 0.008),
                                                     (0.03, -0.052, -0.008), (0.012, -0.056, 0.004),
                                                     (0.03, -0.03, 0.015))], "eye")
        spike(mb, q(0, -0.05, -0.03), q(0, -0.05, 0.0), 0.022 * k, "eye", thickness=0.012 * k, across=(1, 0, 0))


SPECS = [Orc()]
