"""The largest works of a rich town: the royal palace and its gardens, the
grand bazaar, the plaza of the great sundial and the great dam. Each is built
in three stages (see parts.py).
"""

import math
import random

import parts as P
from parts import SLATE, TAU, TILE, kit

CLOTHS = ("cloth_red", "cloth_blue", "cloth_gold", "cloth_green", "cloth_white", "cloth_purple")


def royal_palace(stage):
    """A palace of two wings and four towers behind a formal garden. Footprint 48 x 40 m, 24 m high."""
    def build():
        w = P.W()
        rnd = random.Random(71)
        s = P.staged(w, stage, 2.2, 7.5, (0.4, 2.5), salt=21.0)
        fin = stage == 3
        F = 0.8
        P.yard(w, stage, rnd, 48, 40, piles=[(-20, -17.5, 1.0), (20, -17.5, 1.0), (8, -9, 1.0)], timbers=[(12, -16, 0), (-12, -14, 20)], lodges=[(-7, -12, 0)],
               cranes=[(0, -8, 180, 13.0), (-17, -9, 180, 11.0, 2), (17, -9, 180, 11.0, 2)], outline=(47.6, 39.6))
        if fin:
            w.box((0, 0, 0.05), (48, 40, 0.1), "grass")
        w.box((0, 8, F / 2), (46, 22, F), "stone_light")
        P.steps(w, 0, -3.0, 9.0, 4, 0.2, 0.4, "stone")
        P.block(s, 0, 9, 24, 10, F, 13, "plaster")
        P.block(s, 0, 3.2, 9, 2.6, F, 15, "plaster")
        towers = [(sx * 22, y) for sx in (-1, 1) for y in (-3, 13)]
        for sx in (-1, 1):
            P.block(s, sx * 17, 5, 10, 16, F, 11, "plaster")
            for x, y in ((sx * 12.2, -3), (sx * 12.2, 4), (sx * 21.8, 4)):
                s.box((x, y, 6.0), (0.9, 0.9, 10.4), "stone_light")
        for x, y in towers:
            P.drum(s, x, y, 2.4, F, 16, "stone_light", 8)
        if stage == 2:
            P.scaffold(w, (12, -3.2), (19.4, -3.2), 3, F)
            P.scaffold(w, (-19.4, -3.2), (-12, -3.2), 3, F)
            P.scaffold(w, (-11.5, 3.8), (-5, 3.8), 3, F)
            P.scaffold(w, (5, 3.8), (11.5, 3.8), 3, F)
        if not fin:
            P.finish(w, P.model_id("wonder_royal_palace", stage))
            return

        bones, flags = [], []
        # Roofs and cornices.
        w.box((0, 9, 13.15), (24.8, 10.8, 0.4), "stone_light")
        w.frustum(0, 9, 24.6, 10.6, 13.3, 19.0, 4.0, 16.8, "slate")
        w.box((0, 9, 16.9), (19.2, 4.2, 0.25), "slate_dark")
        for sx in (-1, 1):
            w.box((sx * 17, 5, 11.15), (10.8, 16.8, 0.4), "stone_light")
            w.frustum(sx * 17, 5, 10.6, 16.6, 11.3, 3.0, 9.0, 14.4, "slate")
            w.box((sx * 17, 5, 14.5), (3.2, 9.2, 0.25), "slate_dark")
            for k in range(3):                                                 # Chimneys.
                w.box((sx * (9 + 4 * k), 12.5, 15.2), (0.9, 0.9, 3.4), "brick")
                w.box((sx * (9 + 4 * k), 12.5, 17.0), (1.1, 1.1, 0.3), "stone_light")
        for i, (x, y) in enumerate(towers):
            w.cyl((x, y, 16.0), (x, y, 16.5), 2.9, 2.9, "stone_light", 8, spin=22.5)
            P.cone_roof(w, x, y, 2.8, 16.5, 6.0, ("night", "slate"), 8, 3)
            bones += P.flag(w, "flag%d" % i, x, y, 22.3, 3.6, "cloth_blue" if i % 2 else "cloth_red", 1.1)
            flags.append("flag%d" % i)
            a = math.atan2(y - 5, x)
            for z in (5.0, 10.5):
                P.window(w.at(x + math.cos(a) * 2.3, y + math.sin(a) * 2.3, z, math.degrees(a) + 90), 0.9, 2.0, "window", "stone")
        # The central pavilion: a portico, a balcony, a pediment and a dome.
        w.box((0, 3.2, 15.2), (9.6, 3.2, 0.4), "stone_light")
        w.solid([(-4.6, 1.9, 15.4), (4.6, 1.9, 15.4), (0, 1.9, 17.6)], (0, 2.6, 0), "plaster")
        w.cyl((0, 1.85, 16.1), (0, 1.75, 16.1), 0.6, 0.6, "gold", 10)
        w.box((0, 5.5, 17.2), (7.0, 6.0, 1.6), "plaster")
        w.box((0, 5.5, 18.1), (7.6, 6.6, 0.3), "stone_light")
        P.dome(w, 0, 5.5, 18.2, 3.4, "copper", "copper_dark", 10, 5, 1.15)
        w.cyl((0, 5.5, 22.0), (0, 5.5, 23.0), 0.6, 0.6, "plaster", 8)
        P.finial(w, 0, 5.5, 23.0, 0.9)
        P.door(w.at(0, 1.9, F), 2.6, 4.2, "door", "stone_light", pointed=False)
        for x in (-3.4, -1.9, 1.9, 3.4):
            P.column(w, x, 0.9, F, 6.0, 0.3, "marble", "stone_light")
        w.box((0, 1.2, 7.0), (8.0, 1.8, 0.4), "stone_light")
        for k in range(9):
            w.box((-3.8 + 0.95 * k, 0.4, 7.7), (0.2, 0.2, 1.0), "marble")
        w.box((0, 0.4, 8.25), (8.0, 0.25, 0.15), "marble")
        P.window(w.at(0, 1.88, 7.4), 2.2, 3.6, "window", "stone_light", pointed=False)
        for z in (2.6, 7.6):
            for x in (-10.4, -8.0, -5.8, 5.8, 8.0, 10.4):
                P.window(w.at(x, 3.98, z), 1.2, 2.6, "window", "stone_light", pointed=False)
            for x in (-3.0, 3.0):
                if z > 5:
                    P.window(w.at(x, 1.88, z), 1.1, 2.6, "window", "stone_light", pointed=False)
        for sx in (-1, 1):
            for z in (2.4, 6.8):
                for x in (14.4, 17.0, 19.6):
                    P.window(w.at(sx * x, -3.02, z), 1.2, 2.4, "window", "stone_light", pointed=False)
                for y in (-0.5, 2.2):
                    P.window(w.at(sx * 11.98, y, z, -90 * sx), 1.2, 2.4, "window", "stone_light", pointed=False)
                for y in (0.5, 3.5, 6.5, 9.5):
                    P.window(w.at(sx * 22.02, y, z, 90 * sx), 1.2, 2.4, "window", "stone_light", pointed=False)
        # The garden.
        w.box((0, -11.5, 0.12), (4.0, 17.0, 0.06), "paving")
        w.box((0, -11.5, 0.12), (42.0, 3.0, 0.06), "paving")
        for cx in (-1, 1):
            for cy in (-1, 1):
                x, y = cx * 10.5, -11.5 + cy * 4.6
                for k, (dx, dy, sx_, sy_) in enumerate(((0, 2.0, 13, 0.7), (0, -2.0, 13, 0.7), (6.15, 0, 0.7, 4.7), (-6.15, 0, 0.7, 4.7))):
                    w.box((x + dx, y + dy, 0.45), (sx_, sy_, 0.7), "leaf_dark")
                w.box((x, y, 0.22), (11.6, 3.3, 0.24), rnd.choice(("petal", "leaf_gold", "cloth_red", "petal_light")))
                w.box((x, y, 0.28), (6.0, 1.6, 0.24), "leaf_light")
                P.cypress(w, x, y, 0.1, 1.1)
        w.cyl((0, -11.5, 0.1), (0, -11.5, 0.7), 2.6, 2.7, "stone_light", 12)
        w.cyl((0, -11.5, 0.6), (0, -11.5, 0.76), 2.3, 2.3, "water", 12)
        w.cyl((0, -11.5, 0.6), (0, -11.5, 1.8), 0.4, 0.3, "marble", 8)
        w.cyl((0, -11.5, 1.8), (0, -11.5, 2.1), 0.3, 0.9, "marble", 8)
        jet = w.bone("jet")
        jet.cyl((0, -11.5, 2.1), (0, -11.5, 3.6), 0.14, 0.05, "water_light", 6)
        jet.sphere((0, -11.5, 3.6), 0.3, "water_light", 6, 4, (1.3, 1.3, 0.6))
        bones.append(("jet", (0, -11.5, 2.1), (0, -11.5, 3.6), None))
        for sx in (-1, 1):
            w.box((sx * 3.4, -5.0, 0.7), (1.2, 1.2, 1.2), "stone_light")
            P.statue(w.at(sx * 3.4, -5.0, 1.3), 2.6, "marble", ("down", "hip"), "marble_shade", robe=sx > 0)
            for k in range(6):
                P.cypress(w, sx * 22.6, -18.5 + 2.6 * k, 0.1, 1.5)
            w.box((sx * 2.6, -19.4, 1.6), (1.0, 1.0, 3.2), "stone_light")           # The gate and the railings.
            P.lamp(w, sx * 2.6, -19.4, 3.2, 2.0, "iron")
            for k in range(8):
                x = sx * (4.9 + 2.5 * k)
                w.box((x, -19.4, 1.0), (0.5, 0.5, 2.0), "stone_light")
                w.sphere((x, -19.4, 2.2), 0.3, "gold", 6, 4)
            for z in (0.6, 1.5):
                w.box((sx * 13.0, -19.4, z), (20.8, 0.1, 0.1), "iron")
            for k in range(40):
                w.cyl((sx * (3.3 + 0.5 * k), -19.4, 0.1), (sx * (3.3 + 0.5 * k), -19.4, 1.8), 0.035, 0.035, "iron", 4)

        def idle(t):
            return P.flag_turns(flags, t), {"jet": (0, 0, 0.18 * math.sin(TAU * 4 * t))}

        P.finish(w, "wonder_royal_palace", bones, [("idle", 4.0, idle)])
    return build


def bazaar(stage):
    """A covered market: two vaulted streets that cross under a dome, four gates and a ring of stalls. Footprint 36 x 28 m, 17 m high."""
    def build():
        w = P.W()
        rnd = random.Random(72)
        s = P.staged(w, stage, 1.6, 4.5, (0.4, 1.8), salt=22.0)
        fin = stage == 3
        P.yard(w, stage, rnd, 36, 28, piles=[(-6, -5, 1.0), (6, 5, 1.0)], timbers=[(7, -5, 0)], lodges=[(-7, 5, 0)], cranes=[(0, 0, 0, 10.0)], outline=(35.6, 27.6))
        P.block(s, 0, 0, 32, 24, 0, 6.0, "sand")
        P.block(s, 0, 0, 30, 6.4, 6.0, 8.0, "sand_light")
        P.block(s, 0, 0, 6.4, 22, 6.0, 8.0, "sand_light")
        for rz, d in ((0, 12.0), (180, 12.0), (90, 16.0), (270, 16.0)):
            g = s.at(0, 0, 0, rz)
            P.block(g, 0, -d - 0.4, 8.0, 2.8, 0, 10.0, "sand_light")
            for sx in (-1, 1):
                g.cyl((sx * 4.6, -d - 0.6, 0), (sx * 4.6, -d - 0.6, 12.5), 0.9, 0.75, "sand", 8)
        if stage == 2:
            P.scaffold(w, (-16.2, -12.2), (-4.2, -12.2), 2)
            P.scaffold(w, (4.2, -12.2), (16.2, -12.2), 2)
        if not fin:
            P.finish(w, P.model_id("wonder_bazaar", stage))
            return

        bones, flags = [], []
        w.box((0, 0, 0.05), (36, 28, 0.1), "paving")
        w.box((0, 0, 6.15), (32.6, 24.6, 0.3), "sand_light")
        P.battlements(w, 0, 0, 32.2, 24.2, 6.3, "sand", 0.6, 0.6)
        P.vault(w, 0, 0, 30, 3.2, 8.0, TILE)
        P.vault(w.at(0, 0, 0, 90), 0, 0, 22, 3.2, 8.0, TILE)
        w.cyl((0, 0, 8.0), (0, 0, 11.0), 5.2, 5.2, "sand_light", 8, spin=22.5)
        w.cyl((0, 0, 11.0), (0, 0, 11.4), 5.6, 5.6, "turquoise", 8, spin=22.5)
        for i in range(8):
            a = TAU * i / 8
            P.window(w.at(math.cos(a) * 4.8, math.sin(a) * 4.8, 9.0, math.degrees(a) + 90), 1.0, 1.4, "glass_yellow", "sand", pointed=False)
        P.dome(w, 0, 0, 11.4, 5.2, "turquoise", "jade", 12, 5, 1.0)
        P.finial(w, 0, 0, 16.5, 1.0)
        for cx in (-1, 1):
            for cy in (-1, 1):
                w.cyl((cx * 10, cy * 7.5, 6.3), (cx * 10, cy * 7.5, 7.3), 2.3, 2.3, "sand_light", 8)
                P.dome(w, cx * 10, cy * 7.5, 7.3, 2.2, "turquoise", None, 8, 3, 1.0)
                P.finial(w, cx * 10, cy * 7.5, 9.4, 0.5)
        k = 0
        for rz, d, half in ((0, 12.0, 16.0), (180, 12.0, 16.0), (90, 16.0, 12.0), (270, 16.0, 12.0)):
            g = w.at(0, 0, 0, rz)
            g.box((0, -d - 0.4, 10.2), (8.6, 3.2, 0.4), "turquoise")           # The gate.
            g.box((0, -d - 1.82, 4.6), (5.4, 0.1, 8.4), "turquoise")
            P.arch_panel(g.at(0, -d - 1.85, 0.1), 4.0, 5.2)
            g.box((0, -d - 1.9, 9.0), (4.6, 0.1, 0.5), "gold")
            for sx in (-1, 1):
                g.cyl((sx * 4.6, -d - 0.6, 12.5), (sx * 4.6, -d - 0.6, 13.0), 1.1, 1.1, "sand_light", 8)
                P.dome(g, sx * 4.6, -d - 0.6, 13.0, 0.9, "turquoise", None, 8, 3, 1.3)
                P.finial(g, sx * 4.6, -d - 0.6, 14.1, 0.45)
                n = int((half - 5.6) / 2.6)
                for i in range(n):                                             # The stalls under their awnings.
                    x = sx * (6.2 + 2.6 * i)
                    P.arch_panel(g.at(x, -d - 0.02, 0.1), 1.8, 2.6)
                    mat = CLOTHS[k % len(CLOTHS)]
                    k += 1
                    g.solid([(x - 1.25, -d, 4.3), (x + 1.25, -d, 4.3), (x + 1.25, -d - 1.9, 3.3), (x - 1.25, -d - 1.9, 3.3)], (0, 0, 0.1), mat)
                    for ex in (-1.15, 1.15):
                        g.cyl((x + ex, -d - 1.8, 0.1), (x + ex, -d - 1.8, 3.3), 0.05, 0.05, "pole", 5)
                    g.box((x, -d - 1.0, 0.5), (2.0, 0.9, 0.8), "plank")
                    for j in range(3):
                        kind = rnd.randrange(3)
                        if kind == 0:
                            g.box((x - 0.6 + 0.6 * j, -d - 1.0, 1.1), (0.4, 0.4, 0.4), rnd.choice(("plank_light", "tile", "sack")))
                        elif kind == 1:
                            g.sphere((x - 0.6 + 0.6 * j, -d - 1.0, 1.1), 0.24, rnd.choice(("leaf_gold", "cloth_red", "leaf", "petal")), 6, 4)
                        else:
                            g.cyl((x - 0.6 + 0.6 * j, -d - 1.0, 0.9), (x - 0.6 + 0.6 * j, -d - 1.0, 1.4), 0.16, 0.22, rnd.choice(("tile", "bronze", "sand_dark")), 6)
        for i, sx in enumerate((-1, 1)):
            bones += P.flag(w, "flag%d" % i, sx * 4.6, -12.6, 14.6, 3.4, "cloth_gold" if i else "cloth_red", 1.0)
            flags.append("flag%d" % i)
        P.finish(w, "wonder_bazaar", bones, [("idle", 4.0, lambda t: (P.flag_turns(flags, t), {}))])
    return build


def sundial_plaza(stage):
    """A round plaza whose marble gnomon of 10 m casts the hour on twelve stones. Footprint 24 x 24 m, 10 m high."""
    def build():
        w = P.W()
        rnd = random.Random(73)
        fin = stage == 3
        P.yard(w, stage, rnd, 24, 24, piles=[(-9.6, -9.8, 0.8), (9.6, -9.8, 0.8)], lodges=[(8.5, 8.8, 180)] if stage == 1 else [], outline=(23.6, 23.6))
        if fin:
            w.box((0, 0, 0.05), (24, 24, 0.1), "grass")
        w.cyl((0, 0, 0), (0, 0, 0.3), 11.8, 11.8, "paving_dark", 24)
        n = 24 if stage > 1 else 9
        for i in range(n):
            a0, a1 = TAU * i / 24 - math.pi / 2, TAU * (i + 1) / 24 - math.pi / 2
            w.solid([(0, 0, 0.3), (math.cos(a0) * 10.8, math.sin(a0) * 10.8, 0.3), (math.cos(a1) * 10.8, math.sin(a1) * 10.8, 0.3)], (0, 0, 0.12), "paving" if i % 2 else "sand_light")
        if stage == 1:
            P.stone_pile(w, 3, 3, rnd, 4, 3, 2, ("paving", "sand_light"))
            P.finish(w, "wonder_sundial_stage1")
            return
        w.box((0, 0, 0.6), (2.0, 11.0, 0.5), "stone")
        if stage == 2:
            w.solid([(-0.5, -5, 0.85), (-0.5, 4.5, 0.85), (-0.5, 4.5, 4.6), (-0.5, -1.2, 4.6)], (1.0, 0, 0), "marble")
            P.scaffold(w, (-1.2, 5.2), (-1.2, -5.2), 3, 0.42, depth=1.2)
            P.scaffold(w, (1.2, -5.2), (1.2, 5.2), 3, 0.42, depth=1.2)
            P.crane(w.at(5.5, 3, 0.42, 90), 10.0, 4.0, load="marble")
            P.stone_pile(w.at(0, 0, 0.42), -6, -3, rnd, 3, 2, 2, ("marble", "marble_shade"))
            P.finish(w, "wonder_sundial_stage2")
            return

        w.solid([(-0.5, -5, 0.85), (-0.5, 4.5, 0.85), (-0.5, 4.5, 10.0)], (1.0, 0, 0), "marble")   # The gnomon.
        w.solid([(-0.62, -5.1, 0.85), (-0.62, 4.5, 10.15), (-0.62, 4.5, 9.4), (-0.62, -4.3, 0.85)], (1.24, 0, 0), "bronze")
        w.box((0, 4.75, 5.4), (1.3, 0.5, 9.2), "marble_shade")
        w.cyl((-0.56, 2.4, 4.6), (0.56, 2.4, 4.6), 1.5, 1.5, "gold", 14)
        w.cyl((-0.6, 2.4, 4.6), (0.6, 2.4, 4.6), 1.1, 1.1, "night", 14)
        P.finial(w, 0, 4.6, 10.0, 0.8)
        for i in range(24):
            a0, a1 = TAU * i / 24, TAU * (i + 1) / 24
            w.cyl((math.cos(a0) * 6.2, math.sin(a0) * 6.2, 0.46), (math.cos(a1) * 6.2, math.sin(a1) * 6.2, 0.46), 0.12, 0.12, "gold_dark", 4)
        for i in range(12):                                                    # The hour stones.
            a = TAU * i / 12 - math.pi / 2 + TAU / 24
            g = w.at(math.cos(a) * 9.7, math.sin(a) * 9.7, 0.42, math.degrees(a) + 90)
            g.frustum(0, 0, 1.1, 0.7, 0, 0.9, 0.5, 1.9, "stone_light")
            for k in range(i % 4 + 1):
                g.box((-0.3 + 0.2 * k, -0.33, 1.3), (0.08, 0.06, 0.6), "gold")
            if i % 3 == 0:
                g.sphere((0, 0, 2.15), 0.3, "gold", 6, 4)
        sh = w.bone("shadow")
        sh.solid([(0, 0.2, 0.47), (-0.9, 9.0, 0.47), (0.9, 9.0, 0.47)], (0, 0, 0.03), "glass_dark")
        for cx in (-1, 1):
            for cy in (-1, 1):
                w.box((cx * 10.6, cy * 10.6, 0.4), (2.2, 2.2, 0.6), "stone")
                P.tree(w, cx * 10.6, cy * 10.6, 0.6, 1.3, rnd)
                w.box((cx * 6.2, cy * 6.2, 0.7), (1.8, 0.6, 0.12), "plank", rz=45 * cx * cy)
                for e in (-0.7, 0.7):
                    w.box((cx * 6.2 + e * 0.7, cy * 6.2 + e * 0.7 * cx * cy, 0.55), (0.14, 0.5, 0.3), "stone_dark", rz=45 * cx * cy)

        def day(t):
            return {"shadow": [(kit.Z, 80.0 - 160.0 * t)]}, {}

        P.finish(w, "wonder_sundial", [("shadow", (0, 0, 0.47), (0, 1, 0.47), None)], [("day", 12.0, day, False)])
    return build


def dam(stage):
    """A stone dam with three sluices, two gatehouses and a mill wheel. Footprint 40 x 16 m, 17 m high."""
    def build():
        w = P.W()
        rnd = random.Random(74)
        s = P.staged(w, stage, 2.0, 6.5, (0.0, 1.5), salt=23.0, cell=4.0)
        fin = stage == 3
        P.yard(w, stage, rnd, 40, 16, piles=[(-15, -6, 1.0), (15, -6, 1.0)], timbers=[(0, -6.5, 0)], lodges=[(-7, -5.5, 0)] if stage == 1 else [], cranes=[(8, -5.0, 180, 10.0, 2)], outline=(39.6, 15.6))
        for i in range(10):                                                    # The body, cut in blocks so it rises unevenly.
            s.frustum(-18 + 4 * i, 2.5, 4.02, 9, 0, 4.02, 4, 12, "stone" if i % 2 else "stone_light", oy=2.5)
            if i % 2 == 0:
                s.frustum(-18 + 4 * i, -1.2, 1.4, 4.0, 0, 1.4, 1.0, 10.5, "stone_dark", oy=3.7)
        xs = (-8.0, 0.0, 8.0)
        if stage < 3:
            for i in range(14):                                                # The cofferdam that holds the river back.
                x = -19.5 + 3.0 * i
                w.cyl((x, 7.4, 0), (x, 7.4, 3.6), 0.2, 0.18, "bark", 6)
                w.box((x + 1.5, 7.5, 1.6), (3.0, 0.14, 3.0), "plank" if i % 2 else "plank_dark")
            w.box((0, 6.6, 1.2), (40, 1.2, 2.4), "soil_dark")
        if stage == 2:
            P.scaffold(w, (-12, -2.2), (12, -2.2), 3)
        if not fin:
            P.finish(w, P.model_id("wonder_dam", stage))
            return

        bones = [("water", (0, -3, 0.5), (0, -3, 1.5), None)]
        w.box((0, 7.5, 5.4), (40, 1.0, 10.8), "water_deep")                     # The reservoir behind.
        w.box((0, 7.5, 10.85), (40, 1.0, 0.1), "water")
        w.box((0, 5.0, 12.15), (40, 4.4, 0.3), "stone_light")
        for y in (3.0, 7.0):
            for k in range(20):
                w.box((-19 + 2.0 * k, y, 12.7), (1.0, 0.4, 0.8), "stone")
        water = w.bone("water")
        w.box((0, -5.2, 0.25), (34, 4.6, 0.5), "water")                          # The stilling pool and the river going on.
        w.box((0, -7.75, 0.2), (8, 0.5, 0.4), "water")
        for sx in (-1, 1):
            w.box((sx * 17.2, -5.2, 0.4), (0.6, 5.0, 0.8), "stone_dark")
            w.box((sx * 10.6, -7.6, 0.4), (13.6, 0.6, 0.8), "stone_dark")
        for i, x in enumerate(xs):
            w.box((x, -1.4, 4.2), (4.4, 2.6, 6.0), "stone_dark")                # A sluice.
            w.box((x, -1.4, 7.35), (4.8, 3.0, 0.3), "stone_light")
            P.arch_panel(w.at(x, -2.72, 2.2), 2.4, 2.2)
            water.box((x, -3.1, 1.9), (2.0, 0.9, 2.9), "water_light")
            water.sphere((x, -3.6, 0.5), 1.4, "water_light", 8, 4, (1.2, 1.0, 0.35))
            for sx in (-1, 1):
                w.box((x + sx * 1.5, 3.2, 14.2), (0.3, 0.3, 4.2), "pole_dark")
            w.box((x, 3.2, 16.2), (3.6, 0.4, 0.3), "pole_dark")
            w.cyl((x - 0.8, 3.2, 15.6), (x + 0.8, 3.2, 15.6), 0.25, 0.25, "plank_dark", 8)
            name = "gate%d" % i
            gt = w.bone(name)
            gt.box((x, 3.2, 12.6), (2.7, 0.2, 2.6), "plank_dark")
            for z in (11.8, 12.6, 13.4):
                gt.box((x, 3.08, z), (2.7, 0.06, 0.2), "iron")
            gt.cyl((x, 3.2, 13.9), (x, 3.2, 15.4), 0.03, 0.03, "rope", 4)
            bones.append((name, (x, 3.2, 12.6), (x, 3.2, 13.6), None))
        for sx in (-1, 1):                                                     # The gatehouses.
            w.box((sx * 17.6, 5.0, 14.3), (4.0, 4.0, 4.0), "stone")
            P.tent_roof(w, sx * 17.6, 5.0, 4.0, 4.0, 16.3, 2.6, SLATE, 0.3, 2)
            P.window(w.at(sx * 17.6, 3.0, 13.4), 0.8, 1.6, "window", "stone_light")
            P.door(w.at(sx * 15.6, 5.0, 12.3, -90 * sx), 1.0, 1.8, "door", "stone_light", pointed=False)
        w.box((15.0, -5.2, 2.6), (5.0, 4.0, 4.4), "brick")                       # The mill the dam drives.
        P.roof(w, 15.0, -5.2, 5.0, 4.0, 4.8, 1.8, TILE, 0.3, 3, gable="brick")
        P.door(w.at(15.0, -7.2, 0.8), 1.0, 1.8, "door", "stone_light", pointed=False)
        w.box((15.0, -5.2, 0.6), (5.4, 4.4, 0.6), "stone_dark")
        P._shapes.wheel(w.mb, (12.0, -5.0, 2.7), 2.3, "wheel", 0.5, "plank_dark", "plank")
        for i in range(12):
            a = TAU * i / 12
            w.bone("wheel").box((12.0, -5.0 + math.cos(a) * 2.2, 2.7 + math.sin(a) * 2.2), (0.9, 0.5, 0.08), "plank_light")
        bones.append(("wheel", (12.0, -5.0, 2.7), (13.0, -5.0, 2.7), None))
        w.solid([(11.5, -1.0, 6.4), (12.5, -1.0, 6.4), (12.5, -4.4, 5.2), (11.5, -4.4, 5.2)], (0, 0, 0.14), "plank_dark")   # The flume.
        water.box((12.0, -4.5, 3.9), (0.6, 0.3, 2.6), "water_light")
        for y in (-1.4, -3.6):
            w.cyl((12.0, y, 0.4), (12.0, y, 6.4 + (y + 1.0) * 0.35), 0.1, 0.1, "pole", 5)

        def idle(t):
            return {"wheel": [(kit.X, 360.0 * t)]}, {"water": (0, 0, 0.07 * math.sin(TAU * 8 * t))}

        def lift(up):
            def pose(t):
                k = kit.smooth(t) if up else 1 - kit.smooth(t)
                return {}, {"gate%d" % i: (0, 0, 1.6 * k) for i in range(3)}
            return pose

        P.finish(w, "wonder_dam", bones, [("idle", 8.0, idle), ("open", 3.0, lift(True), False), ("close", 3.0, lift(False), False)])
    return build


MODELS = {}
for _base, _fn in (("wonder_royal_palace", royal_palace), ("wonder_bazaar", bazaar), ("wonder_sundial", sundial_plaza), ("wonder_dam", dam)):
    for _stage in (1, 2, 3):
        MODELS[P.model_id(_base, _stage)] = _fn(_stage)
