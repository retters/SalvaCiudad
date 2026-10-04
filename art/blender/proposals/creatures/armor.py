"""Animated armor: an empty suit of plate that walks. Loose plates with
gaps at the joints (nothing inside but a glow in the helm and the chest), a
great helm with a plume, a longsword and a kite shield. It shares the
skeleton warrior's skeleton and clips: idle, walk, attack and die (the
plates fall apart). Variants: steel, black with a red glow, and rusted."""

import math

from mathutils import Vector

import _parts as P
import skeleton
from _parts import hull, bar, rock, seg, spike, ball, box

PTS = skeleton.PTS
STEEL = P.palette(steel=0xA9ACB2, steel_dark=0x6E7278, steel_light=0xC8CBD0, trim=0xD9B24A, plume=0xB8312A,
                  void=0x101014, glow=0x7CD8FF, leather=0x5E3F36)
BLACK = P.palette(steel=0x3A3C44, steel_dark=0x24262C, steel_light=0x54565E, trim=0x8A1E1E, plume=0x1A1A1E,
                  void=0x08080A, glow=0xFF4A2A, leather=0x2A2020)
RUST = P.palette(steel=0x8A6A52, steel_dark=0x5E4636, steel_light=0xA8846A, trim=0x4A6A4A, plume=0x4A5A3A,
                 void=0x0E120E, glow=0x8CFFB8, leather=0x3A2E28)


def body(mb):
    # Great helm: a faceted bucket with a slit and a plume.
    hull(mb, [(x, y, z) for x, y, z in ((-0.11, -0.12, 1.55), (0.11, -0.12, 1.55), (-0.11, 0.12, 1.55), (0.11, 0.12, 1.55),
                                        (-0.12, -0.13, 1.72), (0.12, -0.13, 1.72), (-0.12, 0.13, 1.72), (0.12, 0.13, 1.72),
                                        (-0.07, -0.08, 1.8), (0.07, -0.08, 1.8), (-0.07, 0.08, 1.8), (0.07, 0.08, 1.8),
                                        (0, -0.16, 1.63))], "steel", "head")
    box(mb, (0, -0.128, 1.67), (0.19, 0.03, 0.022), "void", "head")
    for s in (-1, 1):
        ball(mb, (s * 0.045, -0.135, 1.67), 0.012, "glow", "head", segments=5, rings=3)
    bar(mb, (0, -0.145, 1.75), (0, -0.15, 1.56), 0.02, 0.02, "trim", "head")
    for i in range(4):
        spike(mb, (0, 0.02 + 0.03 * i, 1.79), (0, 0.1 + 0.07 * i, 1.98 - 0.05 * i), 0.035, "plume", "head")
    # Cuirass, a glow at the empty neck, and the fauld of plates.
    hull(mb, [(-0.19, -0.13, 1.45), (0.19, -0.13, 1.45), (-0.19, 0.11, 1.45), (0.19, 0.11, 1.45), (-0.15, -0.12, 1.12),
              (0.15, -0.12, 1.12), (-0.15, 0.1, 1.12), (0.15, 0.1, 1.12), (0, -0.18, 1.32), (0, 0.14, 1.34)],
         "steel", "chest")
    bar(mb, (0, -0.172, 1.42), (0, -0.165, 1.16), 0.03, 0.02, "trim", "chest")
    ball(mb, (0, 0, 1.5), 0.06, "glow", "chest")
    mb.cylinder((0, 0, 1.47), (0, 0, 1.53), 0.09, 0.08, "steel_dark", weights={"chest": 1.0}, segments=8)   # Gorget.
    for i in range(6):
        a = i * math.tau / 6 + 0.52
        c, s_ = math.cos(a), math.sin(a)
        bar(mb, (c * 0.15, s_ * 0.11, 1.1), (c * 0.19, s_ * 0.14, 0.86), 0.13, 0.025, "steel_dark" if i % 2 else "steel",
            "hips", side=(-s_, c, 0), taper=1.1)
    mb.cylinder((0, 0, 1.06), (0, 0, 1.12), 0.17, 0.17, "leather", weights={"hips": 1.0}, segments=8)
    for side, s in P.SIDES:
        def m(name):
            p = PTS[name]
            return Vector((p[0] * s, p[1], p[2]))
        rock(mb, m("shoulder") + Vector((s * 0.02, 0, 0.03)), (0.1, 0.1, 0.075), "steel_light", f"upper_arm.{side}",
             count=12, seed=5)
        seg(mb, m("shoulder").lerp(m("elbow"), 0.25), m("shoulder").lerp(m("elbow"), 0.88), 0.055, 0.048, "steel",
            f"upper_arm.{side}")
        seg(mb, m("elbow").lerp(m("wrist"), 0.12), m("wrist"), 0.052, 0.045, "steel_dark", f"lower_arm.{side}")
        ball(mb, m("elbow"), 0.05, "steel_light", f"lower_arm.{side}")
        hull(mb, [m("wrist") + Vector(o) for o in ((-0.04, -0.03, 0.02), (0.04, -0.03, 0.02), (-0.04, 0.03, 0.02),
                                                    (0.04, 0.03, 0.02), (-0.035, -0.04, -0.12), (0.035, -0.04, -0.12),
                                                    (-0.03, 0.02, -0.12), (0.03, 0.02, -0.12))], "steel", f"hand.{side}")
        seg(mb, m("hip").lerp(m("knee"), 0.12), m("hip").lerp(m("knee"), 0.86), 0.075, 0.06, "steel", f"thigh.{side}")
        hull(mb, [m("knee") + Vector(o) for o in ((-0.06, -0.08, 0.05), (0.06, -0.08, 0.05), (-0.06, -0.08, -0.05),
                                                   (0.06, -0.08, -0.05), (0, -0.11, 0.0), (-0.05, 0.0, 0.04),
                                                   (0.05, 0.0, 0.04))], "steel_light", f"shin.{side}")       # Knee cop.
        seg(mb, m("knee").lerp(m("ankle"), 0.14), m("ankle"), 0.06, 0.048, "steel_dark", f"shin.{side}")
        x = PTS["ankle"][0] * s
        hull(mb, [(x - 0.05, 0.07, 0.0), (x + 0.05, 0.07, 0.0), (x - 0.055, -0.14, 0.0), (x + 0.055, -0.14, 0.0),
                  (x - 0.045, 0.06, 0.1), (x + 0.045, 0.06, 0.1), (x - 0.04, -0.1, 0.06), (x + 0.04, -0.1, 0.06),
                  (x, -0.2, 0.01)], "steel", f"foot.{side}")
    # Longsword in the right hand.
    h = Vector((-0.255, -0.03, 0.82))
    bar(mb, h + Vector((0, 0.09, 0)), h + Vector((0, -0.07, 0)), 0.03, 0.03, "leather", "hand.R")
    ball(mb, h + Vector((0, 0.105, 0)), 0.028, "trim", "hand.R")
    bar(mb, h + Vector((0, -0.08, -0.12)), h + Vector((0, -0.08, 0.12)), 0.035, 0.03, "trim", "hand.R")
    bar(mb, h + Vector((0, -0.09, 0)), h + Vector((0, -0.85, 0.03)), 0.014, 0.075, "steel_light", "hand.R", taper=0.7)
    hull(mb, [h + Vector(o) for o in ((0.006, -0.85, 0.056), (-0.006, -0.85, 0.056), (0.006, -0.85, 0.004),
                                      (-0.006, -0.85, 0.004), (0, -0.96, 0.034))], "steel_light", "hand.R")
    # Kite shield on the left forearm, facing out.
    c = Vector((0.31, -0.01, 1.02))
    outline = [(0.0, 0.3), (0.2, 0.26), (0.22, 0.05), (0.12, -0.25), (0.0, -0.42), (-0.12, -0.25), (-0.22, 0.05), (-0.2, 0.26)]
    hull(mb, [c + Vector((dx, y, z)) for y, z in outline for dx in (0.0, 0.03)] + [c + Vector((0.055, 0, 0.0))], "steel",
         "lower_arm.L")
    bar(mb, c + Vector((0.05, 0, 0.26)), c + Vector((0.048, 0, -0.36)), 0.02, 0.05, "trim", "lower_arm.L", side=(1, 0, 0))
    bar(mb, c + Vector((0.05, -0.18, 0.1)), c + Vector((0.05, 0.18, 0.1)), 0.02, 0.05, "trim", "lower_arm.L", side=(1, 0, 0))


def build(name, colors):
    def make():
        mb = P.kit.begin()
        body(mb)
        P.kit.save(mb, P.FAMILY, name, colors, mech=skeleton.mech(P.piece_info(mb)))
    return make


MODELS = {"enemy_armor": build("enemy_armor", STEEL), "enemy_armor_black": build("enemy_armor_black", BLACK),
          "enemy_armor_rust": build("enemy_armor_rust", RUST)}
