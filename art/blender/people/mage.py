"""Mage: light-brown tousled hair, a long green robe open at the front with
wide sleeves and a dark cowl wrapped around the neck, a dark inner robe, a
belt with pouches, a brown sash hanging in front, dark boots, and a tall
wooden staff topped with a big blue crystal in the left hand."""

import math

from mathutils import Quaternion, Vector

import common
import studies
from lizardfolk import Folk, along, belt, buckle, collar, follows, hip_ring, hull, pouch, skirt, spike, tube
from rigs import Bone, X


class Mage(Folk):
    name = "mage"
    height = 1.75
    shoulder = 0.17
    build = 0.95
    head_size = 0.87
    budget = 1100
    # The left forearm is raised to hold the staff, as in the picture (the
    # shoulder and elbow stay where the shared body puts them, and the
    # forearm keeps its length: it only turns at the elbow). False: both
    # arms hang as in the shared body and the staff stands in the lowered hand.
    raised_arm = True
    colors = {
        "skin": common.rgb(0xFBB888),
        "hair": common.rgb(0xB06A30),
        "robe": common.rgb(0x5E8A4C),
        "robe_light": common.rgb(0x6C9A56),
        "robe_shade": common.rgb(0x4F7644),
        "dark": common.rgb(0x3B4447),
        "leather": common.rgb(0x70432B),
        "sash": common.rgb(0x4C3533),
        "trim": common.rgb(0x9A7350),
        "crystal": common.rgb(0x55C8FD),
        "crystal_dark": common.rgb(0x1A7FE0),
        "eye": common.rgb(0x1A1414),
    }
    BELT = 1.117
    HANG = 0.57     # The robe's hem, below the hip joints.

    def part_bones(self):
        out = {}
        for side in ("L", "R"):
            out["sleeve." + side] = "upper_arm." + side
            out["cuff." + side] = "lower_arm." + side
        return out

    def extra_bones(self):
        wrist = Vector(self.P(*self.arm()[1]))
        return [Bone("staff", wrist, wrist + Vector((0, 0, 0.3)), parent="hand.L")]

    def animate(self, clip, t, pose):
        """The staff stays upright on the ground: standing, walking and
        running, the left arm keeps its raised forearm instead of
        swinging; in the other clips the staff only leans when the hand
        comes too low for it."""
        rig = self.rig
        wrist, shoulder = rig.by_name["hand.L"].head, rig.by_name["upper_arm.L"].head
        if self.raised_arm and clip in ("idle", "walk", "run"):
            target = pose.head("upper_arm.L") + (wrist - shoulder)
            target.z = wrist.z
            pose.limb("upper_arm.L", "lower_arm.L", target, Vector((0.2, 0.6, -1.0)))
            pose.set_world("hand.L", Quaternion())
        # The staff's foot is a little ahead of the wrist; tipping it
        # farther forward lifts it.
        ahead = abs(self.arm()[2][1] * self.k - 0.012 * self.k - wrist.y)
        reach, rest = math.hypot(ahead, wrist.z), math.atan2(ahead, wrist.z)
        height = pose.head("staff").z
        lo, hi = rest, math.pi / 2      # The staff's angle from the vertical, found by halving.
        for _ in range(24):
            mid = (lo + hi) / 2
            if height - reach * math.cos(mid) - 0.03 * math.sin(mid - rest) < 0.0:
                lo = mid
            else:
                hi = mid
        pose.set_world("staff", Quaternion(X, rest - (hi if height < wrist.z else rest)))

    def __init__(self):
        super().__init__()
        k = self.k
        for side in (".L", ".R"):
            self.hem("sleeve" + side, "robe_shade")
            self.hem("cuff" + side, "dark")
            self.limb_cut("cuff" + side, 0.72)
        # The robe's opening on the chest: a strip of the inner robe.
        for s in (-1, 1):
            self.cuts.append(((s * 0.03 * k, 0, self.BELT * k), (1, 0, -s * 0.06),
                              lambda c, n: c.y < 0 and abs(c.x) < 0.16 * k and 1.0 * k < c.z < 1.5 * k))

    def arm(self):
        """Elbow, wrist and hand of the left arm (raised or not), of a 1.8 m body."""
        j = self.joints()
        elbow, wrist, hand = Vector(j["elbow"]), Vector(j["wrist"]), Vector(j["hand"])
        if self.raised_arm:
            d = Vector((0.3, -0.92, -0.2)).normalized()
            wrist = elbow + d * (wrist - elbow).length
            hand = wrist + d * 0.08
        return elbow, wrist, hand

    def customize(self, parts):
        E, C = self.ellipsoid, self.capsule
        self.small_head(parts)
        parts["waist"] = E((0, 0.0, 1.13), (0.165, 0.115, 0.15))    # The robe is full at the waist.
        for side, x in ((".L", 1), (".R", -1)):
            j = {n: Vector((p[0] * x, p[1], p[2])) for n, p in self.joints().items()}
            elbow, wrist = j["elbow"], j["wrist"]
            if x > 0:
                elbow, wrist, hand = self.arm()
                parts["forearm" + side] = C(elbow, wrist, 0.046, 0.04)
                parts["hand" + side] = E(hand, (0.045, 0.047, 0.052) if self.raised_arm else (0.032, 0.046, 0.072))
            # Wide sleeves: a short one over the upper arm, a long one to the wrist.
            parts["sleeve" + side] = C(j["shoulder"], j["shoulder"].lerp(j["elbow"], 0.86), 0.07, 0.092)
            parts["cuff" + side] = C(elbow, elbow.lerp(wrist, 0.8), 0.06, 0.088)
            if x < 0:
                h = j["hand"]
                parts["hand" + side] = E((h.x, h.y, h.z + 0.015), (0.03, 0.044, 0.056))

    def paint(self, c, n):
        k, zone = self.k, self.zone(c)
        if zone in ("head", "jaw", "neck") or zone.startswith("hand"):
            return "skin"
        if zone.startswith("cuff"):
            return "trim" if along(self.parts[zone], c) > 0.72 else "robe"
        if zone.startswith("sleeve"):
            return "robe"
        if zone.startswith("forearm"):
            return "dark"
        if zone.startswith(("shin", "foot")):
            return "sash"
        if zone.startswith("thigh") or c.z < self.BELT * k:
            return "dark"
        if c.y < 0 and abs(c.x) < 0.03 * k + (c.z - self.BELT * k) * 0.06:
            return "sash"
        return "robe"

    def details(self, mb):
        k, V = self.k, self.V
        self.begin(mb)
        self.flatten_hems(mb)
        self.head(mb)
        self.face(mb)
        self.hair(mb)
        self.tag(mb, "chest")
        # The cowl: wrapped around the neck, sagging at the front, with a
        # fold on the chest and the hood's lump at the back.
        collar(mb, (0.0, 0.005 * k), 1.44 * k, 1.565 * k, (0.18 * k, 0.155 * k), (0.128 * k, 0.122 * k), "dark",
               drop=0.045 * k, lean=0.02 * k)
        studies.plate(mb, [V(-0.12, -0.11, 1.47), V(0.12, -0.11, 1.47), V(0.01, -0.145, 1.375)], 0.035 * k, "dark")
        hull(mb, [V(*p) for p in ((-0.1, 0.1, 1.54), (0.1, 0.1, 1.54), (0.0, 0.175, 1.5), (-0.08, 0.12, 1.4),
                                  (0.08, 0.12, 1.4), (0.0, 0.15, 1.36), (0.0, 0.1, 1.58))], "dark")
        # Belt, buckle and pouches.
        self.tag(mb, "hips")
        at = belt(mb, self, self.BELT * k, 0.058 * k, "leather", pad=0.013 * k)
        buckle(mb, at, "trim", size=0.065 * k)
        buckle(mb, at, "leather", size=0.032 * k, depth=0.018 * k)
        pouch(mb, at, -58, (0.09 * k, 0.045 * k, 0.11 * k), "leather", drop=0.005 * k, flap="sash")
        pouch(mb, at, 62, (0.065 * k, 0.038 * k, 0.07 * k), "leather", drop=0.005 * k, flap="sash")
        self.tag(mb, self.rig.drape)
        # The robe's skirt: straight cloth from the belt to an uneven hem,
        # open at the front over the dark inner robe.
        angles = (13, 50, 90, 135, 180, 225, 270, 310, 347)
        hems = (0.4, 0.365, 0.385, 0.355, 0.375, 0.35, 0.385, 0.37, 0.415)
        top = [at(a, dz=-0.02 * k) for a in angles]
        hips = hip_ring(self, angles, 0.95 * k, 0.024 * k)
        low = [Vector((p.x * 1.55, p.y * 1.5, z * k)) for p, z in zip(hips, hems)]
        verts = skirt(mb, [top, hips, low], "robe", inner="dark", thickness=0.012 * k)
        self.robe_verts = verts
        y0, y1 = at(0).y - 0.004, low[0].y
        zt = top[0].z
        studies.plate(mb, [(-0.05 * k, y0 + 0.012 * k, zt), (0.05 * k, y0 + 0.012 * k, zt),
                           (0.085 * k, y1 + 0.03 * k, 0.43 * k), (-0.085 * k, y1 + 0.03 * k, 0.43 * k)], 0.012 * k,
                      "dark")
        # Sash: a long brown strip with a lighter border and a pointed end.

        def strip_points(w, z_low, z_tip, dy):
            return [(-w, y0 + dy, zt), (w, y0 + dy, zt), (w, y1 + dy, z_low), (0, y1 + dy, z_tip),
                    (-w, y1 + dy, z_low)]
        studies.plate(mb, strip_points(0.064 * k, 0.53 * k, 0.44 * k, 0.0), 0.012 * k, "trim")
        studies.plate(mb, strip_points(0.044 * k, 0.555 * k, 0.49 * k, -0.008 * k), 0.012 * k, "sash")
        # Boots: a fold at the ankle and a heel.
        for s in (-1, 1):
            knee, ankle = self.J("knee", s), self.J("ankle", s)
            self.tag(mb, "shin.L" if s > 0 else "shin.R")
            tube(mb, [knee.lerp(ankle, t) + Vector((0.004 * (i % 2), 0, 0)) for i, t in
                      enumerate((0.3, 0.55, 0.72, 0.86, 1.0))],
                 [r * k for r in (0.066, 0.06, 0.068, 0.058, 0.064)], "sash", sides=6)
            self.tag(mb, "foot.L" if s > 0 else "foot.R")
            mb.box(ankle + Vector((0, 0.045 * k, -ankle.z + 0.02 * k)), (0.075 * k, 0.07 * k, 0.04 * k), "sash")
        self.staff(mb)
        self.fingers(mb, "skin", sides=(-1,) if self.raised_arm else (-1, 1))
        self.tone(mb, ["robe"], 0.3)
        self.done(mb)

    def hair(self, mb):
        """Tousled light-brown hair: a full mass with locks in every direction."""
        self.hair_hull(mb, "hair", [
            (0.0, -0.11, 0.062), (0.075, -0.102, 0.05), (0.045, -0.118, 0.15),
            (0.0, -0.03, 0.18), (0.1, 0.0, 0.135),
            (0.115, -0.035, 0.03), (0.112, 0.05, -0.03),
            (0.0, 0.145, 0.07), (0.075, 0.128, -0.04), (0.0, 0.128, -0.08)])
        self.shards(mb, "hair", [
            ((0.03, -0.1, 0.1), (0.08, -0.135, 0.015), 0.1),
            ((-0.03, -0.1, 0.1), (-0.075, -0.13, 0.03), 0.1),
            ((0.05, -0.04, 0.145), (0.115, -0.08, 0.2), 0.12),
            ((-0.05, -0.02, 0.145), (-0.105, -0.02, 0.21), 0.12),
            ((0.0, 0.05, 0.15), (0.03, 0.11, 0.205), 0.12),
            ((0.09, 0.0, 0.08), (0.15, 0.01, 0.1), 0.11),
            ((-0.09, 0.0, 0.08), (-0.15, 0.0, 0.07), 0.11),
            ((0.0, 0.12, 0.02), (0.0, 0.17, -0.06), 0.12),
            ((0.065, 0.1, 0.0), (0.115, 0.14, -0.05), 0.1),
            ((-0.065, 0.1, 0.0), (-0.115, 0.135, -0.06), 0.1)])

    @follows("staff")
    def staff(self, mb):
        """A tall wooden staff in the left hand, with prongs holding a crystal."""
        k = self.k
        hand = Vector(self.P(*self.arm()[2]))
        x, y = hand.x + 0.005, hand.y - (0.012 if self.raised_arm else 0.045) * k
        knots = [(0.0, 0.019), (0.5, 0.025), (1.0, 0.023), (1.27, 0.031), (1.37, 0.023), (1.47, 0.042)]
        for i, ((z0, r0), (z1, r1)) in enumerate(zip(knots, knots[1:])):
            lean = 0.006 * (i % 2)
            mb.cylinder((x + lean, y, z0), (x + 0.006 - lean, y, z1), r0, r1, "leather", segments=5)
        for i in range(4):   # Prongs around the crystal.
            a = math.radians(45 + 90 * i)
            d = Vector((math.cos(a), math.sin(a), 0.0))
            spike(mb, Vector((x, y, 1.45)) + d * 0.03, Vector((x, y, 1.58)) + d * 0.095, 0.065, "leather",
                  thickness=0.035)
        if self.raised_arm:  # Fingers around the staff.
            with self.bound(mb, "hand.L"):
                mb.cylinder((x, y, hand.z - 0.042 * k), (x, y, hand.z + 0.042 * k), 0.036 * k, 0.036 * k, "skin",
                            segments=6)
        mb.cylinder((x, y, 1.5), (x, y, 1.61), 0.0, 0.095, "crystal_dark", segments=5)
        mb.cylinder((x, y, 1.61), (x, y, 1.78), 0.095, 0.0, "crystal", segments=5)


SPECS = [Mage()]
