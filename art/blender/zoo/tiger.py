"""Tiger: orange with black stripes cut into the surface, white muzzle,
cheeks, chest, belly and paws."""

import math

from mathutils import Vector

import common
import rigs
import studies

X = 0.19  # Half the distance between left and right legs.
TAIL = [(0, 0.8, 0.86), (0, 1.05, 0.72), (0.05, 1.3, 0.52), (0.12, 1.55, 0.42), (0.2, 1.75, 0.45),
        (0.26, 1.9, 0.56)]
TAIL_R = [0.075, 0.065, 0.06, 0.055, 0.05, 0.045]
KNEE, HOCK = 0.44, 0.3  # Heights of the front and hind leg joints.
PAW_TOP = 0.115  # Where the white paws start: below it they stay rigid.
GALLOP_PHASES = {"HL": 0.0, "HR": 0.1, "FL": 0.5, "FR": 0.6}


class Beast(rigs.Quadruped):
    """The quadruped template for long-legged animals with a tail welded
    into the surface (shared by the lion, wolf and deer specs):

    - the surface near the tail's axis follows the tail bones (the template
      only moves tails made of separate pieces);
    - a tail of many bones swings as far as the template's three;
    - eat lowers the head by the spec's own angles, down to the ground;
    - die tips over the right feet instead of sinking the legs into the
      ground while it rolls, and ends with the head lifted off the ground
      by `die_lift` degrees and rolled back by `die_untwist` degrees (for
      manes and antlers wider than the body).
    """

    tail_reach = None            # Surface this near the tail's axis follows the tail (m); None: rigid.
    eat = (5.0, 0.0, 20.0, 25.0)  # Degrees down at the lowest point: body, chest, neck, head.
    eat_drop = 0.02              # How much the body goes down while eating (m).
    die_lift = 0.0
    die_untwist = 0.0

    def tail_bones(self):
        return [b for b in self.bones if b.name.startswith("tail.")]

    def surface_weights(self, p):
        base = super().surface_weights(p)
        if self.tail_reach is None:
            return base
        tails = self.tail_bones()
        dists = [(rigs.segment_distance(p, b.head, b.tail), b.name) for b in tails]
        d0 = min(d for d, _ in dists)
        r = self.tail_reach
        # Fades in away from the tail's root, so the rump stays with the body.
        k = (max(0.0, min(1.0, (r - d0) / (r * 0.3)))
             * max(0.0, min(1.0, ((p - tails[0].head).length - r * 0.5) / r)))
        if k <= 0.0:
            return base
        tail = [(n, max(0.0, 1.0 - (d - d0) / self.blend) ** 2) for d, n in dists]
        sb, st = sum(w for _, w in base), sum(w for _, w in tail)
        return [(n, w / sb * (1 - k)) for n, w in base] + [(n, w / st * k) for n, w in tail]

    def tail_rot(self, rot, side_deg, up_deg=0.0):
        k = 3.0 / len(self.tail_bones())
        super().tail_rot(rot, side_deg * k, up_deg * k)

    def piece_bone(self, center, piece):
        if center.y > self.tail_bones()[0].head.y:
            return self.tail_bones()[-1].name  # A tuft.
        if len(piece) == 6:  # A flap.
            return "ear.L" if center.x > 0 else "ear.R"
        return "head"  # Eyes, nose, antlers.

    def eat_pose(self, t):
        rot, offset, extra = super().eat_pose(t)
        down = rigs.smooth(t / 0.2) * (1 - rigs.smooth((t - 0.8) / 0.2))
        pitch, chest, neck, head = (a * down for a in self.eat)
        dz = -self.eat_drop * down
        root = rot["head"][0][1] - 25.0 * down  # The template's rooting about.
        rot = self.planted(rot, math.radians(pitch), dz)
        rot["body"] = [(rigs.X, pitch)]
        rot["chest"] = [(rigs.X, chest)]
        rot["neck"] = [(rigs.X, neck)]
        rot["head"] = [(rigs.X, head + root)]
        return rot, Vector((0, 0, dz)), extra

    def die_pose(self, t):
        rot, offset, extra = super().die_pose(t)
        sag = rigs.smooth(t / 0.35)
        roll = rigs.smooth((t - 0.3) / 0.45)
        # High enough for the right legs to pass under the body as it rolls.
        a = math.radians(90.0) * roll
        pivot = self.by_name["body"].head
        offset.z = max(offset.z, -0.08 * sag * (1 - roll) + pivot.z * (math.cos(a) - 1) + self.lie_height * math.sin(a))
        rot["chest"] = [(rigs.Z, self.die_lift * roll)]
        rot["neck"] = rot["neck"] + [(rigs.Z, self.die_lift * roll), (rigs.Y, self.die_untwist * 0.5 * roll)]
        rot["head"] = rot["head"] + [(rigs.Y, self.die_untwist * 0.5 * roll)]
        return rot, offset, extra


def legs_capsules():
    caps = []
    for s in (-1, 1):
        x = s * X
        caps += [
            ((x * 0.95, -0.47, 0.8), (x, -0.47, 0.44), 0.12, 0.09),     # Front upper leg.
            ((x, -0.47, 0.44), (x, -0.52, 0.1), 0.085, 0.07),           # Front lower leg.
            ((x, -0.5, 0.05), (x, -0.64, 0.05), 0.068, 0.062),          # Front paw.
            ((x * 0.95, 0.55, 0.62), (x, 0.7, 0.3), 0.11, 0.075),       # Hind leg to the hock.
            ((x, 0.7, 0.3), (x, 0.62, 0.1), 0.07, 0.065),               # Hind lower leg.
            ((x, 0.64, 0.05), (x, 0.5, 0.05), 0.065, 0.06),             # Hind paw.
        ]
    return caps


def tail_capsules():
    return [(a, b, ra, rb) for a, b, ra, rb in zip(TAIL, TAIL[1:], TAIL_R, TAIL_R[1:])]


def on_leg(c):
    """Whether c is on the outer side of one of the four legs."""
    return X - 0.02 < abs(c.x) < X + 0.14 and (-0.66 < c.y < -0.36 or 0.45 < c.y < 0.8)


def bands():
    # Every band costs two cuts through the surface, and each cut splits
    # every face it crosses: the stripes are few, wide and short so the
    # model stays under its triangle limit.
    out = []
    for i in range(7):  # Body stripes, of uneven length down the flanks.
        n = Vector((0.25 * math.sin(i * 2.1), 1.0, 0.3 * math.cos(i * 1.3))).normalized()
        zmin = 0.66 + 0.07 * (i % 3)
        out.append((Vector((0, -0.52 + i * 0.2, 0.8)), n, 0.042 + 0.01 * (i % 2),
                    lambda c, nn, zmin=zmin: -0.7 < c.y < 0.86 and c.z > zmin))
    # Leg rings, on the outer side. Their upper edges are where the rig cuts
    # the legs anyway (the hock and the front knee), to save triangles.
    for z in (HOCK, KNEE):
        out.append((Vector((0, 0, z - 0.028)), Vector((0, 0, 1)), 0.028,
                    lambda c, nn: 0.12 < c.z < 0.58 and on_leg(c)))
    out.append((Vector((0, -0.7, 0.9)), Vector((0, 1, 0.7)).normalized(), 0.03,  # Neck.
                lambda c, nn: -0.9 < c.y < -0.55 and c.z > 0.9))
    for x, hw in ((0.0, 0.014), (0.06, 0.01), (-0.06, 0.01)):  # Forehead.
        out.append((Vector((x, 0, 0)), Vector((1, 0, 0)), hw,
                    lambda c, nn: -1.07 < c.y < -0.86 and c.z > 1.1))
    out.append((Vector((0, -0.95, 1.02)), Vector((0, 0.4, 1)).normalized(), 0.014,  # Cheeks.
                lambda c, nn: -1.05 < c.y < -0.85 and abs(c.x) > 0.15))
    # Tail rings, every 0.26 m along the tail.
    pts = [Vector(p) for p in TAIL]
    dist = 0.16
    for a, b in zip(pts, pts[1:]):
        seg = (b - a).length
        while dist < seg:
            out.append((a.lerp(b, dist / seg), (b - a).normalized(), 0.035,
                        lambda c, nn: c.y > 0.86))
            dist += 0.26
        dist -= seg
    return out


class TigerRig(Beast):
    tail_reach = 0.11
    eat = (8.0, 8.0, 30.0, 20.0)
    eat_drop = 0.04


class Tiger(studies.Spec):
    name = "tiger"
    max_tris = 2000
    budget = 494
    colors = {
        "orange": common.rgb(0xF0922A),
        "orange_light": common.rgb(0xF6A844),
        "orange_shade": common.rgb(0xDD801C),
        "white": common.rgb(0xF4EEE4),
        "black": common.rgb(0x1E1A18),
        "nose": common.rgb(0xD9868A),
        "eye": common.rgb(0x151012),
    }
    ellipsoids = [
        ((0, -0.35, 0.8), (0.26, 0.42, 0.3)),     # Chest.
        ((0, 0.0, 0.75), (0.25, 0.4, 0.25)),      # Belly.
        ((0, 0.38, 0.78), (0.24, 0.44, 0.26)),    # Hips.
        ((X * 0.9, 0.5, 0.66), (0.12, 0.23, 0.25)),   # Thighs.
        ((-X * 0.9, 0.5, 0.66), (0.12, 0.23, 0.25)),
        ((0, -0.95, 1.04), (0.21, 0.19, 0.19)),   # Head.
        ((0, -0.98, 0.97), (0.25, 0.14, 0.13)),   # Cheek ruff.
        ((0, -1.12, 0.95), (0.12, 0.11, 0.09)),   # Muzzle.
    ]
    capsules = [((0, -0.6, 0.88), (0, -0.85, 1.0), 0.2, 0.17)] + legs_capsules() + tail_capsules()
    loft = [
        (0.82, 0.8, 0.1, 0.1), (0.75, 0.8, 0.2, 0.2), (0.55, 0.78, 0.25, 0.26), (0.25, 0.76, 0.26, 0.26),
        (-0.05, 0.76, 0.26, 0.27), (-0.35, 0.8, 0.27, 0.3), (-0.58, 0.86, 0.22, 0.25),
        (-0.78, 0.98, 0.19, 0.19), (-0.9, 1.04, 0.22, 0.2), (-1.02, 1.03, 0.2, 0.17),
        (-1.1, 0.97, 0.13, 0.11), (-1.21, 0.96, 0.1, 0.08), (-1.235, 0.97, 0.05, 0.04),
    ]
    loft_capsules = legs_capsules() + tail_capsules()
    box = {
        "body": ((0, 0.02, 0.78), (0.26, 0.74, 0.28)),
        "legs": [path for s in (-1, 1) for path in (
            [((s * X, -0.47, 0.44), 0.1), ((s * X, -0.52, 0.12), 0.075), ((s * X, -0.6, 0.05), 0.07)],
            [((s * X, 0.62, 0.42), 0.1), ((s * X, 0.7, 0.26), 0.075), ((s * X, 0.6, 0.05), 0.07)],
        )],
        "head": [((0, -0.8, 0.95), 0.25), ((0, -0.95, 1.02), 0.24), ((0, -1.1, 0.97), 0.14),
                 ((0, -1.22, 0.96), 0.09)],
        "tail": [((0, 0.95, 0.76), 0.07), ((0.05, 1.25, 0.52), 0.06), ((0.14, 1.55, 0.42), 0.055),
                 ((0.24, 1.88, 0.53), 0.045)],
    }
    tone_material = "orange"
    voxel = 0.05
    rig = TigerRig(
        body=((0, 0.78, 0.8), (0, -0.05, 0.77)),
        chest=((0, -0.05, 0.77), (0, -0.58, 0.86)),
        neck=((0, -0.58, 0.86), (0, -0.85, 1.0)),
        head=((0, -0.85, 1.0), (0, -1.24, 0.97)),
        ears=((0.13, -0.89, 1.16), (0.18, -0.9, 1.27)),
        tail=TAIL,
        legs={
            "F": ((X, -0.47, 0.8), (X, -0.47, KNEE), (X, -0.52, PAW_TOP), (X, -0.7, 0.0)),
            "H": ((X, 0.58, 0.62), (X, 0.7, HOCK), (X, 0.62, PAW_TOP), (X, 0.44, 0.0)),
        },
        leg_exit=(KNEE, 0.56),
        leg_reach=0.24,
        walk=rigs.Gait(speed=1.1, frames=18, duty=0.62, lift=0.08, crouch=0.06, bob=0.01,
                       phases=rigs.WALK_PHASES, wag=10.0),
        run=rigs.Gait(speed=5.0, frames=11, duty=0.3, lift=0.15, crouch=0.11, bob=0.02,
                      phases=GALLOP_PHASES, nod=4.0, wag=6.0),
        lie_height=0.3,
        blend=0.06,
    )

    def __init__(self):
        self.bands = bands()
        joints = {
            "belly": ((0, 0.0, 0.76), (0.26, 0.26)),
            "chest": ((0, -0.35, 0.8), (0.26, 0.29)),
            "neck": ((0, -0.66, 0.9), (0.2, 0.22)),
            "head": ((0, -0.95, 1.03), (0.21, 0.19)),
            "muzzle": ((0, -1.13, 0.96), (0.12, 0.09)),
            "nose": ((0, -1.22, 0.97), (0.07, 0.05)),
            "hips": ((0, 0.4, 0.78), (0.24, 0.25)),
            "rump": ((0, 0.72, 0.82), (0.15, 0.17)),
        }
        edges = [("belly", "chest"), ("chest", "neck"), ("neck", "head"), ("head", "muzzle"),
                 ("muzzle", "nose"), ("belly", "hips"), ("hips", "rump")]
        prev = "rump"
        for i, (p, r) in enumerate(zip(TAIL[1:], TAIL_R[1:])):
            joints[f"tail{i}"] = (p, (r, r))
            edges.append((prev, f"tail{i}"))
            prev = f"tail{i}"
        for s, side in ((-1, "r"), (1, "l")):
            x = s * X
            chain = [("chest", None),
                     (f"fs{side}", ((x, -0.45, 0.58), (0.11, 0.12))),
                     (f"fe{side}", ((x, -0.48, 0.38), (0.085, 0.085))),
                     (f"fw{side}", ((x, -0.52, 0.1), (0.07, 0.07))),
                     (f"fp{side}", ((x, -0.62, 0.06), (0.065, 0.055)))]
            chain2 = [("hips", None),
                      (f"hk{side}", ((x, 0.52, 0.5), (0.12, 0.14))),
                      (f"hh{side}", ((x, 0.68, 0.28), (0.075, 0.075))),
                      (f"ha{side}", ((x, 0.62, 0.1), (0.068, 0.068))),
                      (f"hp{side}", ((x, 0.53, 0.06), (0.063, 0.055)))]
            for ch in (chain, chain2):
                for (a, _), (b, data) in zip(ch, ch[1:]):
                    joints[b] = data
                    edges.append((a, b))
        self.skeleton = (joints, edges)

    def paint(self, c, n):
        if c.y > 1.8:
            return "black"  # Tail tip.
        if c.z < 0.115 and c.y < 0.86:
            return "white"  # Paws.
        if c.y < -1.08 and c.z < 1.02:
            return "white"  # Muzzle.
        for s in (-1, 1):
            if (c - Vector((s * 0.085, -1.1, 1.13))).length < 0.05:
                return "white"  # Above the eyes.
        if c.y < -0.86 and abs(c.x) > 0.12 and c.z < 0.99:
            return "white"  # Cheeks.
        if -0.95 < c.y < -0.55 and c.z < 0.9 and abs(c.x) < 0.17 and n.z < 0.3:
            return "white"  # Throat and chest.
        if -0.6 < c.y < 0.8 and c.z < 0.62 and n.z < -0.1 and abs(c.x) < 0.2:
            return "white"  # Belly.
        if studies.in_band(self, c, n):
            return "black"
        return "orange"

    def details(self, mb):
        for s in (-1, 1):
            mb.sphere((s * 0.085, -1.105, 1.085), 0.024, "eye", segments=6, rings=4)
            base_a, base_b, tip = (s * 0.08, -0.9, 1.19), (s * 0.19, -0.88, 1.12), (s * 0.18, -0.9, 1.27)
            studies.flap(mb, base_a, base_b, tip, 0.03, "black")
            inner = [Vector(p) + Vector((0, -0.02, 0)) for p in (base_a, base_b, tip)]
            mid = sum(inner, Vector()) / 3
            studies.flap(mb, *[mid + (p - mid) * 0.65 for p in inner], 0.02, "white")
        mb.sphere((0, -1.225, 0.985), 0.045, "nose", segments=6, rings=4, scale=(1.0, 0.5, 0.6))


SPECS = [Tiger()]
