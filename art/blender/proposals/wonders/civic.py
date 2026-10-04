"""Wonders of any town: the cathedral, the great clock tower, the lighthouse
of the world and the colossus. Each is built in three stages (see parts.py).
"""

import math
import random

import parts as P
from parts import GLASS, SLATE, TAU, kit


def cathedral(stage):
    """Twin spires, a rose window, flying buttresses. Footprint 28 x 46 m."""
    def build():
        w = P.W()
        rnd = random.Random(21)
        s = P.staged(w, stage, 2.4, 10.0, (0.6, 3.5), salt=1.0)
        fin = stage == 3
        F = 0.6
        P.yard(w, stage, rnd, 28, 46, piles=[(-10.5, -21.4), (10.5, -21.4), (10.5, 17.5, 1.0, 90)], timbers=[(-10.5, 17.5, 90)],
               lodges=[(0, -3, 0)], cranes=[(0, 7, 180, 14.0), (0, -10, 0, 12.0, 2)], outline=(27.6, 45.6), z=F)
        w.box((0, 0, F / 2), (27, 44.8, F), "stone_dark")
        P.steps(w, 0, -22.4, 16, 3, 0.2, 0.2, "stone_light")

        P.block(s, 0, 0.75, 10, 28.5, F, 17, "stone")
        P.block(s, 0, -16.75, 10, 6.5, F, 17, "stone")
        for sx in (-1, 1):
            P.block(s, sx * 7, -5.25, 4, 16.5, F, 8.5, "stone")
            P.block(s, sx * 8.5, 7, 7, 8, F, 17, "stone")
            P.block(s, sx * 8.5, -17, 7, 7, F, 27, "stone")
            for y in (-13, -9, -5, -1):
                s.box((sx * 9.7, y, F + 5.2), (1.4, 1.0, 10.4), "stone_dark")
            for cx in (-1, 1):
                for cy in (-1, 1):
                    s.box((sx * 8.5 + cx * 3.5, -17 + cy * 3.5, F + 12), (1.1, 1.1, 24), "stone_dark")
        P.drum(s, 0, 15, 5, F, 17, "stone", 10)
        chapels = [(math.cos(math.radians(a)) * 6.3, 15 + math.sin(math.radians(a)) * 6.3) for a in (15, 90, 165)]
        for x, y in chapels:
            P.drum(s, x, y, 2.2, F, 7, "stone", 8)

        if stage == 2:
            P.scaffold(w, (-12.5, -20.6), (12.5, -20.6), 6, F)
            P.scaffold(w, (-10.6, 3), (-10.6, -13.5), 4, F)
            P.scaffold(w, (10.6, -13.5), (10.6, 3), 4, F)
            P.scaffold(w, (12.1, 3), (12.1, 11), 5, F)
            P.scaffold(w, (-12.1, 11), (-12.1, 3), 5, F)
        if stage == P.RUIN:
            w.box((0, 0, 0.05), (28, 46, 0.1), "grass_dark")
            P.rubble(w, rnd, 27, 45, 90)
            P.rubble(w, rnd, 9, 26, 20, z=F, moss=False)
            for sx in (-1, 1):                                                 # Empty windows, ivy, and one pane that still holds.
                for i, y in enumerate((-11, -7, -3, 1)):
                    P.window(s.at(sx * 9.02, y, 3.0, 90 * sx), 1.5, 3.4, GLASS[i] if (i == 1 and sx > 0) else "glass_dark")
                    s.box((sx * 10.45, y - 2, F + 2.0 + i * 0.8), (0.14, 1.0, 4.0 + i * 1.6), "moss")
                for i, y in enumerate((-11, -7, -3, 1, 13)):
                    P.window(s.at(sx * 5.02, y, 11.2, 90 * sx), 1.6, 3.6, "glass_dark")
                P.window(s.at(sx * 8.5, -20.5, 9.5), 1.8, 4.5, "glass_dark")
                P.door(s.at(sx * 8.5, -20.5, F), 2.0, 3.4, "glass_dark")
                s.box((sx * 6.5, -20.56, F + 3.5), (2.2, 0.14, 7.0), "moss")
                s.box((sx * 12.06, -16, F + 2.5), (0.14, 3.0, 5.0), "moss")
            P.door(s.at(0, -20.0, F), 3.2, 5.0, "glass_dark")
            w.at(0.5, -11, F + 1.5).turn("X", -86).cyl((0, 0, 0), (0, 0, 10.0), 2.2, 0.0, "slate", 4, spin=45)   # A fallen spire.
        if not fin:
            P.finish(w, P.model_id("wonder_cathedral", stage))
            return

        bones = []
        w.box((0, 0.75, 17.1), (10.5, 29, 0.3), "stone_light")
        for sx in (-1, 1):
            x, y = sx * 8.5, -17
            for z in (17.2, 27.2):
                w.box((x, y, z), (7.6, 7.6, 0.4), "stone_light")
            for cx in (-1, 1):                                               # The open belfry.
                for cy in (-1, 1):
                    w.box((x + cx * 2.8, y + cy * 2.8, 30.3), (1.4, 1.4, 5.8), "stone")
                    w.cyl((x + cx * 3.3, y + cy * 3.3, 33.6), (x + cx * 3.3, y + cy * 3.3, 37.2), 0.55, 0.0, "stone_light", 4, spin=45)
                w.box((x, y + cx * 2.8, 32.5), (4.2, 1.3, 1.4), "stone")
                w.box((x + cx * 2.8, y, 32.5), (1.3, 4.2, 1.4), "stone")
            w.box((x, y, 33.4), (7.4, 7.4, 0.5), "stone_light")
            w.box((x, y, 31.9), (5.0, 0.3, 0.3), "pole_dark")
            P.tent_roof(w, x, y, 6.6, 6.6, 33.6, 13.5, SLATE, 0.2, 6)
            P.finial(w, x, y, 46.9, 1.4)
            name = "bell_l" if sx < 0 else "bell_r"
            b = w.bone(name)
            b.cyl((x, y, 31.8), (x, y, 30.9), 0.45, 0.9, "bronze", 10)
            b.cyl((x, y, 30.9), (x, y, 29.7), 0.9, 1.35, "bronze", 10)
            b.sphere((x, y, 29.5), 0.25, "iron", 6, 4)
            bones.append((name, (x, y, 31.9), (x, y, 29.7), None))
            P.door(w.at(x, -20.5, F), 2.0, 3.4)
            P.window(w.at(x, -20.5, 9.5), 1.8, 4.5, GLASS[0 if sx < 0 else 1])
            P.window(w.at(x, -20.5, 19.5), 1.6, 4.5, "glass_dark")
            P.window(w.at(sx * 12, -17, 19.5, 90 * sx), 1.6, 4.5, "glass_dark")
            P.window(w.at(sx * 12, -17, 9.5, 90 * sx), 1.8, 4.5, GLASS[2])
            for i, y in enumerate((-11, -7, -3, 1)):                       # Aisle windows, buttresses and their flying arches.
                P.window(w.at(sx * 9.02, y, 3.0, 90 * sx), 1.5, 3.4, GLASS[(i + (sx > 0)) % 5])
            for i, y in enumerate((-11, -7, -3, 1, 13)):
                P.window(w.at(sx * 5.02, y, 11.2, 90 * sx), 1.6, 3.6, GLASS[(i + 2 + (sx > 0)) % 5])
            for y in (-13, -9, -5, -1):
                w.cyl((sx * 9.7, y, 11.0), (sx * 9.7, y, 13.8), 0.7, 0.0, "stone_light", 4, spin=45)
                w.cyl((sx * 9.5, y, 10.4), (sx * 5.2, y, 14.8), 0.34, 0.34, "stone_light", 4, spin=45)
            w.solid([(sx * 5, -13.5, 11.0), (sx * 9.4, -13.5, 8.3), (sx * 9.4, 3, 8.3), (sx * 5, 3, 11.0)], (0, 0, 0.3), "slate_dark")
            P.rose(w.at(sx * 12.02, 7, 11.5, 90 * sx), 2.3)
            P.door(w.at(sx * 12.02, 7, F, 90 * sx), 1.8, 3.2)
        P.rose(w.at(0, -20.0, 12.3), 3.2)
        w.solid([(-5, -20, 17), (5, -20, 17), (0, -20, 22.5)], (0, 1.0, 0), "stone")
        P.finial(w, 0, -19.5, 22.4, 1.0)
        P.door(w.at(0, -20.0, F), 3.2, 5.0)
        w.solid([(-2.6, -20.0, 7.7), (2.6, -20.0, 7.7), (0, -20.0, 9.6)], (0, -0.5, 0), "stone_light")
        for i in range(6):                                                    # The gallery over the doors.
            x = (-4.2, -3.1, -2.0, 2.0, 3.1, 4.2)[i]
            P.statue(w.at(x, -20.35, 6.2), 1.7, "marble", robe=True, mat2="marble_shade")
            w.box((x, -20.35, 6.0), (0.8, 0.8, 0.4), "stone_light")
        for i, a in enumerate((18, 54, 90, 126, 162)):
            x, y = math.cos(math.radians(a)) * 5.05, 15 + math.sin(math.radians(a)) * 5.05
            P.window(w.at(x, y, 9.0, a + 90), 1.5, 5.0, GLASS[i % 5])
        P.roof(w.at(0, -2.5, 0, 90), 0, 0, 35, 10, 17, 5.5, SLATE, 0.4, 5)
        P.roof(w, 0, 7, 24, 8, 17, 5.5, SLATE, 0.4, 4, gable="stone")
        P.cone_roof(w, 0, 15, 5.5, 17, 5.5, SLATE, 10, 3)
        for x, y in chapels:
            P.cone_roof(w, x, y, 2.5, 7, 3.0, SLATE, 8, 2)
        w.cyl((0, 7, 21.5), (0, 7, 25.0), 1.4, 1.1, "slate_dark", 8)          # The fleche over the crossing.
        w.cyl((0, 7, 25.0), (0, 7, 36.0), 1.3, 0.0, "slate", 8)
        P.finial(w, 0, 7, 35.8, 1.0)

        def ring(t):
            a = 20.0 * math.sin(TAU * 2 * t)
            return {"bell_l": [(kit.Y, a)], "bell_r": [(kit.Y, -a)]}, {}

        P.finish(w, "wonder_cathedral", bones, [("ring", 4.0, ring)])
    return build


def clock_tower(stage):
    """Four clock faces, a bell and a slate spire. Footprint 14 x 14 m, 49 m high."""
    def build():
        w = P.W()
        rnd = random.Random(22)
        s = P.staged(w, stage, 2.6, 17.0, (0.5, 3.0), salt=2.0, cell=2.2)
        fin = stage == 3
        P.yard(w, stage, rnd, 14, 14, piles=[(-5.6, -6.3, 0.8), (5.6, -6.3, 0.8)], outline=(13.6, 13.6))
        w.box((0, 0, 0.5), (11, 11, 1.0), "stone_dark")
        P.steps(w, 0, -5.5, 6, 4, 0.25, 0.35, "stone_light")
        P.block(s, 0, 0, 8.4, 8.4, 1.0, 11, "stone")
        for cx in (-1, 1):
            for cy in (-1, 1):
                s.box((cx * 4.2, cy * 4.2, 5.5), (1.5, 1.5, 9.0), "stone_dark")
                s.box((cx * 4.2, cy * 4.2, 10.4), (1.1, 1.1, 1.0), "stone_dark")
                s.box((cx * 3.3, cy * 3.3, 18.0), (0.8, 0.8, 14.0), "stone_light")
        P.block(s, 0, 0, 6.6, 6.6, 11, 25, "stone")
        P.block(s, 0, 0, 7.6, 7.6, 25, 32, "stone_light")
        if stage == 2:
            P.scaffold_box(w, 0, 0, 8.6, 8.6, 7)
            w.box((0, 0, 11.3), (6.4, 6.4, 0.3), "plank")
            P.crane(w.at(0, 0, 11.45, 20), 8.0, 4.4, load_z=1.0)
        if stage == 1:
            P.crane(w.at(0, 0.3, 1.0, 0), 6.0, 3.0)
        if not fin:
            P.finish(w, P.model_id("wonder_clock_tower", stage))
            return

        bones, hands = [], []
        w.box((0, 0, 11.2), (9.2, 9.2, 0.5), "stone_light")
        P.door(w.at(0, -4.2, 1.0), 2.6, 4.2)
        for z in (25.0, 32.2):
            w.box((0, 0, z), (8.3, 8.3, 0.5), "stone")
        for i, rz in enumerate((0, 90, 180, 270)):
            f = w.at(0, 0, 0, rz)
            P.window(f.at(0, -3.3, 13.5), 1.0, 3.0, "glass_dark")
            P.window(f.at(0, -3.3, 19.5), 1.0, 3.0, "glass_dark")
            if i:
                P.window(f.at(0, -4.2, 4.0), 1.6, 3.6, GLASS[i])
            c = f.at(0, -3.8, 28.6)                                            # A clock face.
            c.cyl((0, 0.1, 0), (0, -0.2, 0), 3.0, 3.0, "gold_dark", 24)
            c.cyl((0, -0.2, 0), (0, -0.28, 0), 2.7, 2.7, "plaster", 24)
            for k in range(12):
                a = TAU * k / 12
                r0 = 1.95 if k % 3 == 0 else 2.2
                c.cyl((math.cos(a) * r0, -0.3, math.sin(a) * r0), (math.cos(a) * 2.55, -0.3, math.sin(a) * 2.55), 0.1, 0.1, "obsidian", 4)
            c.bone("hour%d" % i).cyl((0.2, -0.36, -0.12), (-1.3, -0.36, 0.78), 0.2, 0.08, "obsidian", 4)
            c.bone("min%d" % i).cyl((0, -0.44, -0.3), (0, -0.44, 2.3), 0.15, 0.05, "obsidian", 4)
            c.cyl((0, -0.28, 0), (0, -0.52, 0), 0.25, 0.2, "gold", 8)
            axis = tuple(c.m.to_3x3() @ P.Vector((0, 1, 0)))
            for kind in ("hour", "min"):
                bones.append(("%s%d" % (kind, i), c.p((0, -0.4, 0)), c.p((0, -0.9, 0)), None))
            hands.append((i, axis))
        for cx in (-1, 1):                                                     # The belfry.
            for cy in (-1, 1):
                w.box((cx * 3.0, cy * 3.0, 35.3), (1.4, 1.4, 5.6), "stone")
                w.cyl((cx * 3.6, cy * 3.6, 38.6), (cx * 3.6, cy * 3.6, 42.0), 0.6, 0.0, "stone_light", 4, spin=45)
            w.box((0, cx * 3.0, 37.4), (4.6, 1.3, 1.4), "stone")
            w.box((cx * 3.0, 0, 37.4), (1.3, 4.6, 1.4), "stone")
        w.box((0, 0, 38.35), (8.2, 8.2, 0.5), "stone_light")
        w.box((0, 0, 36.8), (5.4, 0.3, 0.3), "pole_dark")
        b = w.bone("bell")
        b.cyl((0, 0, 36.7), (0, 0, 35.7), 0.5, 1.0, "bronze", 10)
        b.cyl((0, 0, 35.7), (0, 0, 34.2), 1.0, 1.6, "bronze", 10)
        b.sphere((0, 0, 34.0), 0.3, "iron", 6, 4)
        bones.append(("bell", (0, 0, 36.8), (0, 0, 34.2), None))
        P.tent_roof(w, 0, 0, 7.2, 7.2, 38.6, 9.0, SLATE, 0.2, 5)
        P.finial(w, 0, 0, 47.4, 1.5)
        flags = []
        for i, cx in enumerate((-1, 1)):
            bones += P.flag(w, "flag%d" % i, cx * 5.0, -5.0, 1.0, 7.0, "cloth_blue" if i else "cloth_red", 1.0)
            flags.append("flag%d" % i)

        def turn(t):
            turns = {}
            for i, axis in hands:
                turns["hour%d" % i] = [(axis, 360.0 * t)]
                turns["min%d" % i] = [(axis, 360.0 * 12 * t)]
            return turns, {}

        P.finish(w, "wonder_clock_tower", bones, [
            ("idle", 4.0, lambda t: (P.flag_turns(flags, t), {})),
            ("turn", 36.0, turn),
            ("ring", 4.0, lambda t: ({"bell": [(kit.Y, 18.0 * math.sin(TAU * 2 * t))]}, {})),
        ])
    return build


def lighthouse(stage):
    """Three tiers of white stone, a fire and a turning mirror. Footprint 22 x 22 m, 59 m high."""
    def build():
        w = P.W()
        rnd = random.Random(23)
        s = P.staged(w, stage, 4.5, 14.0, (0.0, 2.5), salt=3.0)
        fin = stage == 3
        P.yard(w, stage, rnd, 22, 22, piles=[(-7.5, -9.9), (7.5, -9.9)], timbers=[(9.8, 2, 90)], heaps=[(-9.6, 4, 1.2)], outline=(21.6, 21.6))
        w.frustum(0, 0, 17, 17, 0, 16, 16, 3, "stone_dark")
        w.box((0, 0, 3.05), (15.4, 15.4, 0.1), "paving")
        P.steps(w, 0, -8.0, 5, 10, 0.3, 0.3, "stone_light")
        for sx in (-1, 1):
            w.box((sx * 2.8, -9.5, 1.6), (0.6, 3.0, 3.2), "stone")
        s.frustum(0, 0, 13, 13, 3, 10.5, 10.5, 23, "marble")
        for cx in (-1, 1):
            for cy in (-1, 1):
                s.frustum(cx * 6.2, cy * 6.2, 1.4, 1.4, 3, 1.4, 1.4, 23, "marble_shade", ox=-cx * 1.25, oy=-cy * 1.25)
        P.drum(s, 0, 0, 4.0, 23.5, 38, "marble", 8, r2=3.4)
        P.drum(s, 0, 0, 2.4, 38.5, 46, "marble", 12, r2=2.1)
        if stage == 2:
            top = s.cap(0, 0)
            P.scaffold_box(w, 0, 0, 13.2, 13.2, 5, z=3.0)
            P.crane(w.at(0, 0, top, 30), 8.0, 4.5, load_z=1.0)
            P.lodge(w.at(0, 0, top), -3.0, 2.5, 90)
        if stage == 1:
            P.lodge(w.at(0, 0, 3.0), 0, 2.5, 0)
            P.crane(w.at(0, -2.0, 3.0, 0), 6.0, 3.0)
        if not fin:
            P.finish(w, P.model_id("wonder_lighthouse", stage))
            return

        P.door(w.at(0, -6.5, 3.0), 2.4, 4.0, pointed=False, frame="marble_shade")
        for rz in (0, 90, 180, 270):
            f = w.at(0, 0, 0, rz)
            for z in (9.0, 13.5, 18.0):
                half = 6.5 - (z - 3.0) / 20.0 * 1.25
                for x in (-2.6, 0.0, 2.6):
                    if rz == 0 and z == 9.0 and x == 0.0:
                        continue
                    P.window(f.at(x, -half + 0.05, z), 0.8, 1.7, "glass_dark", "marble_shade", pointed=False)
            P.window(f.at(0, -3.45, 28.0), 0.9, 2.2, "glass_dark", "marble_shade", pointed=False)
            P.window(f.at(0, -3.3, 33.0), 0.9, 2.2, "glass_dark", "marble_shade", pointed=False)
        w.box((0, 0, 23.25), (12.0, 12.0, 0.5), "marble_shade")                # The first terrace.
        P.battlements(w, 0, 0, 11.4, 11.4, 23.5, "marble", 0.6, 0.8)
        for i, (cx, cy) in enumerate(((-1, -1), (1, -1), (1, 1), (-1, 1))):
            g = w.at(cx * 4.7, cy * 4.7, 23.5, (135, 225, 315, 45)[i] - 180 + (0 if cy < 0 else 0))
            g.box((0, 0, 0.5), (1.4, 1.4, 1.0), "marble_shade")
            hands = P.statue(g.at(0, 0, 1.0), 3.6, "bronze", ("down", "up"), "bronze_dark")
            g.at(0, 0, 1.0).cyl(hands["hand_l"], (hands["hand_l"][0] - 0.3, hands["hand_l"][1], hands["hand_l"][2] + 1.0), 0.12, 0.3, "gold", 6)
        w.cyl((0, 0, 38.0), (0, 0, 38.5), 4.6, 4.6, "marble_shade", 8, spin=22.5)
        for i in range(8):
            a = TAU * (i + 0.5) / 8
            w.box((math.cos(a) * 4.3, math.sin(a) * 4.3, 39.0), (0.4, 0.4, 1.0), "marble")
        w.cyl((0, 0, 46.0), (0, 0, 46.5), 3.1, 3.1, "marble_shade", 12)        # The lantern.
        for i in range(8):
            a = TAU * i / 8
            P.column(w, math.cos(a) * 2.6, math.sin(a) * 2.6, 46.5, 4.6, 0.22, "marble", "gold")
        w.cyl((0, 0, 51.1), (0, 0, 51.5), 3.2, 3.2, "marble_shade", 12)
        P.cone_roof(w, 0, 0, 3.1, 51.5, 3.6, P.COPPER, 12, 3)
        w.cyl((0, 0, 55.0), (0, 0, 55.6), 0.5, 0.6, "marble", 8)
        hands = P.statue(w.at(0, 0, 55.6), 3.4, "gold", ("up", "down"), "gold_dark", robe=True)
        P.spear(w.at(0, 0, 55.6), hands["hand_l"], 3.4, "gold_dark", "gold_light")
        w.cyl((0, 0, 46.5), (0, 0, 47.5), 0.5, 1.2, "iron", 8)
        w.cyl((0, 0, 47.45), (0, 0, 47.55), 1.1, 1.1, "coal", 8)
        P.flame(w, 0, 0, 47.5, 2.0)
        b = w.bone("light")
        b.box((0, 1.7, 48.6), (2.6, 0.14, 2.6), "gold_light")
        b.box((0, 1.8, 48.6), (2.9, 0.1, 2.9), "bronze")
        b.cyl((0, -2.9, 48.6), (0, -10.5, 48.6), 0.35, 1.3, "beam", 8)
        P.banner(w.at(0, -5.6, 21.5), 2.4, 6.0, "cloth_blue")

        def idle(t):
            return {"light": [(kit.Z, 360.0 * t)]}, P.flame_moves(t, 0.2, 8)

        P.finish(w, "wonder_lighthouse", [("light", (0, 0, 48.0), (0, 0, 49.0), None)], [("idle", 8.0, idle)])
    return build


def colossus(stage, mat="bronze", mat2="bronze_dark", suffix=""):
    """A founder of 30 m astride a gate or a harbor mouth. Footprint 26 x 12 m, 39 m high."""
    def build():
        w = P.W()
        rnd = random.Random(24)
        s = P.staged(w, stage, 2.0, 30.0, (0.5, 0.0), salt=4.0)
        fin = stage == 3
        P.yard(w, stage, rnd, 26, 12, piles=[(0, 4.2, 1.0)], timbers=[(0, -4.6, 0)], lodges=[(0, 0.5, 0)] if stage == 1 else [],
               cranes=[(0, 0.5, 0, 13.0, 2)], outline=(25.6, 11.6))
        for sx in (-1, 1):
            w.box((sx * 7, 0, 0.4), (8.4, 8.4, 0.8), "stone_dark")
            s.box((sx * 7, 0, 1.15), (7.6, 7.6, 0.7), "stone_dark")
            P.block(s, sx * 7, 0, 6.6, 6.6, 1.5, 5.0, "stone")
            if stage >= 2:
                w.box((sx * 7, 0, 5.3), (7.2, 7.2, 0.6), "stone_light")
                for rz in (0, 180):
                    f = w.at(sx * 7, 0, 0, rz)
                    f.box((0, -3.35, 3.2), (3.6, 0.12, 2.2), mat)
                    f.box((0, -3.4, 3.2), (3.0, 0.1, 1.6), mat2)
                for cx in (-1, 1):
                    for cy in (-1, 1):
                        w.box((sx * 7 + cx * 3.2, cy * 3.2, 3.2), (0.7, 0.7, 3.6), "stone_light")
        if stage == 1:
            for i in range(4):                                                 # Bronze plates waiting on the ground.
                w.box((-1.5 + i * 1.0, -1.8, 0.2 + 0.08 * i), (2.2, 1.4, 0.12), mat if i % 2 else mat2, rz=8 * i)
        g = w.at(0, 0, 5.6)
        if stage == 2:
            P.statue(g, 30.0, mat, ("up", "down"), mat2, upto=0.52, spread=7 / 30, detail=True)
            for sx in (-1, 1):
                P.scaffold_box(w, sx * 7, 0, 8.6, 8.6, 9)
                for i in range(3):
                    w.box((sx * 2.2, -3.6 + i * 0.5, 0.2 + 0.1 * i), (2.2, 1.4, 0.12), mat if i % 2 else mat2, rz=10 * i)
        if not fin:
            P.finish(w, P.model_id("wonder_colossus", stage))
            return
        hands = P.statue(g, 30.0, mat, ("up", "down"), mat2, spread=7 / 30, crown=True, cape=mat2, detail=True)
        tip = P.torch(g, hands["hand_r"], 30.0, "gold", 1.4)
        P.flame(g, tip[0], tip[1], tip[2], 3.2)
        P.sword(g, hands["hand_l"], 30.0, "steel" if mat == "bronze" else mat2)
        g.cyl((0, -3.0, 20.3), (0, -3.5, 20.3), 1.6, 1.3, "gold", 8)           # The clasp of the belt.
        for sx in (-1, 1):
            P.brazier(w, sx * 7, -4.9, 0.8, 1.5)
        P.finish(w, "wonder_colossus" + suffix, [], [("idle", 4.0, lambda t: ({}, P.flame_moves(t, 0.3, 6)))])
    return build


MODELS = {}
for _base, _fn in (("wonder_cathedral", cathedral), ("wonder_clock_tower", clock_tower), ("wonder_lighthouse", lighthouse), ("wonder_colossus", colossus)):
    for _stage in (1, 2, 3):
        MODELS[P.model_id(_base, _stage)] = _fn(_stage)
MODELS["wonder_cathedral_ruin"] = cathedral(P.RUIN)
MODELS["wonder_colossus_gold"] = colossus(3, "gold", "gold_dark", "_gold")
MODELS["wonder_colossus_marble"] = colossus(3, "marble", "marble_shade", "_marble")
