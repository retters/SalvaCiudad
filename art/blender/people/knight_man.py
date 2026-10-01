"""Knight (man): dark hair, plate armor (steel pauldrons with a tan rim, a
light breastplate with a center ridge, gauntlets, greaves and sabatons)
over a dark under-suit, a blue cowl draped to a point on the chest, a belt,
a long blue tabard with a gold border in front and a blue cape behind."""

from mathutils import Vector

import common
import studies
from lizardfolk import Folk, belt, buckle, collar, hip_ring, hull, recolor, sheet, skirt, sym, sym_y
from rigs import Bone


class KnightMan(Folk):
    name = "knight_man"
    height = 1.8
    shoulder = 0.2      # Measured on the picture: his arms hang wider than the shared body's.
    build = 1.08
    budget = 1000
    colors = {
        "skin": common.rgb(0xF6AC7C),
        "hair": common.rgb(0x4A302C),
        "steel": common.rgb(0x77789A),
        "steel_light": common.rgb(0xB4B0C8),
        "steel_shade": common.rgb(0x54566F),
        "plate": common.rgb(0xE6DCDE),
        "blue": common.rgb(0x2A66C4),
        "blue_dark": common.rgb(0x163F9A),
        "gold": common.rgb(0xC69666),
        "dark": common.rgb(0x25232E),
        "leather": common.rgb(0x5A3626),
        "eye": common.rgb(0x1A1414),
    }
    BELT = 1.135
    HEM = 0.54
    HANG = 0.46     # The tabard's point, below the hip joints.
    CAPE = 1.17     # The cape's length.

    def extra_bones(self):
        return [Bone("cape", self.V(0, 0.125, 1.47), self.V(0, 0.16, 1.0), parent="chest")]

    def __init__(self):
        super().__init__()
        k = self.k
        for side in (".L", ".R"):
            hand = self.parts["hand" + side]
            self.cuts.append(((0, 0, hand[1][2] - 0.01 * k), (0, 0, 1), self.near("hand" + side)))

    def customize(self, parts):
        self.small_head(parts)
        parts["chest"] = self.ellipsoid((0, 0.0, 1.33), (0.172, 0.118, 0.18))
        for side, x in ((".L", 1), (".R", -1)):   # Fists.
            h = self.joints()["hand"]
            parts["hand" + side] = self.ellipsoid((h[0] * x, h[1], h[2] + 0.02), (0.04, 0.05, 0.052))

    def paint(self, c, n):
        k, zone = self.k, self.zone(c)
        if zone in ("head", "jaw", "neck"):
            return "skin"
        if zone.startswith("hand"):
            return "dark" if c.z > self.parts[zone][1][2] - 0.01 * k else "skin"
        if zone.startswith(("shin", "foot")):
            return "steel_shade"
        return "dark"

    def details(self, mb):
        k, V, rig = self.k, self.V, self.rig
        self.begin(mb)
        self.head(mb)
        self.face(mb)
        self.hair(mb)
        self.tag(mb, "chest")
        # The cowl: wrapped around the neck, draped in two folds to a point
        # on the chest.
        collar(mb, (0.0, 0.0), 1.455 * k, 1.57 * k, (0.165 * k, 0.14 * k), (0.112 * k, 0.112 * k), "blue",
               drop=0.03 * k, lean=0.016 * k)
        studies.plate(mb, [V(-0.15, -0.09, 1.485), V(0.15, -0.09, 1.485), V(0.0, -0.172, 1.27)], 0.03 * k, "blue_dark")
        studies.plate(mb, [V(-0.12, -0.115, 1.53), V(0.12, -0.115, 1.53), V(0.0, -0.178, 1.37)], 0.03 * k, "blue")
        # Breastplate: an angular shell with a ridge down the middle.
        self.tag(mb, rig.torso)
        verts = hull(mb, [V(*p) for p in sym([
            (0.11, -0.1, 1.43), (0.0, -0.13, 1.44), (0.175, -0.03, 1.37), (0.0, -0.165, 1.31), (0.15, -0.085, 1.2),
            (0.0, -0.145, 1.165), (0.135, -0.075, 1.165), (0.12, 0.1, 1.42), (0.17, 0.04, 1.37), (0.14, 0.09, 1.185),
            (0.0, 0.125, 1.32), (0.0, 0.112, 1.175)])], "plate")
        recolor(mb, verts, lambda c, n: "steel_light" if abs(n.x) > 0.8 or n.z < -0.6 else None)
        for s in (-1, 1):
            # Pauldrons: sloping plates with a ridge and a tan rim.
            side = "L" if s > 0 else "R"
            sh = self.J("shoulder", s) + Vector((s * 0.005, 0.0, 0.02)) * k
            # A leather strap from the pauldron to the belt.
            self.tag(mb, rig.torso)
            studies.plate(mb, [V(s * 0.138, -0.092, 1.42), V(s * 0.164, -0.07, 1.42), V(s * 0.16, -0.078, 1.22),
                               V(s * 0.14, -0.092, 1.22)], 0.02 * k, "leather")
            self.tag(mb, rig.shoulder(side))
            hull(mb, [sh + Vector((s * x, y, z)) * k * 1.1 for x, y, z in sym_y([
                (-0.085, 0.07, 0.085), (-0.015, 0.125, 0.085), (-0.02, 0.0, 0.125), (0.075, 0.13, 0.03),
                (0.085, 0.0, 0.09), (0.15, 0.108, -0.075), (0.172, 0.0, -0.04), (0.0, 0.14, -0.015)])], "steel_light")
            hull(mb, [sh + Vector((s * x, y, z)) * k * 1.1 for x, y, z in sym_y([
                (0.06, 0.142, -0.02), (0.155, 0.122, -0.085), (0.187, 0.0, -0.055), (0.145, 0.108, -0.112),
                (0.17, 0.0, -0.1), (0.05, 0.132, -0.055)])], "gold")
            # Gauntlets: a faceted sleeve, a flared cuff at the elbow and a
            # ring at the wrist.
            self.tag(mb, "lower_arm." + side)
            a, b = self.J("elbow", s), self.J("wrist", s)
            mb.cylinder(a.lerp(b, 0.02), a.lerp(b, 1.0), 0.066 * k, 0.05 * k, "steel", segments=6)
            mb.cylinder(a.lerp(b, -0.08), a.lerp(b, 0.34), 0.088 * k, 0.07 * k, "steel_light", segments=6)
            mb.cylinder(a.lerp(b, 0.84), a.lerp(b, 1.02), 0.055 * k, 0.062 * k, "steel_light", segments=6)
        # Leg armor.
        self.greaves(mb, "steel")
        self.knee_guard(mb, "steel_light", size=1.15)
        self.sabatons(mb, "steel")
        # Belt.
        self.tag(mb, "hips")
        at = belt(mb, self, self.BELT * k, 0.07 * k, "leather", pad=0.014 * k)
        buckle(mb, at, "steel_light", size=0.075 * k)
        buckle(mb, at, "leather", size=0.036 * k, depth=0.018 * k)
        self.tag(mb, rig.drape)
        # Tabard: a blue skirt hanging straight from the belt, open at the
        # front, where a blue strip with a gold border ends in a point.
        angles = (15, 52, 92, 135, 180, 225, 268, 308, 345)
        top = [at(a, dz=-0.02 * k) for a in angles]
        hips = hip_ring(self, angles, 0.95 * k, 0.022 * k)
        low = []
        for i, p in enumerate(hips):
            fold = 1.3 + (0.06 if i % 2 else 0.0)
            low.append(Vector((p.x * fold, p.y * fold * 1.05, (self.HEM + (0.012 if i % 2 else 0.0)) * k)))
        skirt(mb, [top, hips, low], "blue", inner="blue_dark", thickness=0.012 * k)
        y0, y1 = at(0).y - 0.004, low[0].y - 0.012 * k

        def strip_points(w, z_low, z_tip, dy):
            return [(-w, y0 + dy, top[0].z), (w, y0 + dy, top[0].z), (w, y1 + dy, z_low), (0, y1 + dy, z_tip),
                    (-w, y1 + dy, z_low)]
        studies.plate(mb, strip_points(0.08 * k, 0.58 * k, 0.475 * k, 0.0), 0.012 * k, "gold")
        studies.plate(mb, strip_points(0.06 * k, 0.6 * k, 0.52 * k, -0.008 * k), 0.012 * k, "blue")
        self.tag(mb, rig.cape)
        # Cape: flat folded panels from the shoulders to the calves, with a
        # jagged hem.
        rows = []
        for z, half, y in ((1.47, 0.17, 0.125), (1.1, 0.27, 0.15), (0.7, 0.34, 0.18), (0.3, 0.39, 0.2)):
            row = []
            for i in range(7):
                x = (i / 3.0 - 1.0) * half
                fold = 0.06 if i % 2 else 0.0
                jag = (0.08 if i % 2 else 0.0) if z < 0.5 else 0.0
                wrap = -0.05 * abs(i / 3.0 - 1.0) ** 2   # The sides come forward around the arms.
                row.append(V(x, y + fold * (1.5 - z) + wrap, z + jag))
            rows.append(row)
        sheet(mb, rows, 0.014 * k, "blue_dark")
        self.fingers(mb, "skin")
        self.tone(mb, ["steel"], 0.4)
        self.done(mb)

    def hair(self, mb):
        """Short dark hair, full on top and swept up at the front."""
        self.hair_hull(mb, "hair", [
            (0.072, -0.097, 0.062), (0.0, -0.108, 0.072),           # Hairline.
            (0.03, -0.116, 0.118), (0.072, -0.08, 0.112),           # The quiff.
            (0.0, -0.03, 0.17), (0.045, 0.03, 0.152), (0.088, 0.02, 0.105),
            (0.103, -0.035, 0.035), (0.102, 0.05, -0.01),           # Over the ears.
            (0.0, 0.1, 0.13), (0.0, 0.138, 0.06), (0.07, 0.122, -0.04), (0.0, 0.122, -0.08)])
        self.shards(mb, "hair", [
            ((0.03, -0.08, 0.125), (0.085, -0.14, 0.165), 0.16),
            ((-0.03, -0.085, 0.125), (0.0, -0.155, 0.158), 0.16),
            ((0.0, 0.11, 0.0), (0.0, 0.145, -0.07), 0.1)])


SPECS = [KnightMan()]
