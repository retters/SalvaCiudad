"""More wonders of any town: the triumphal arch, the great library, the
founder's mausoleum, the coliseum, the hanging gardens and the great bell.
Each is built in three stages (see parts.py).
"""

import math
import random

import parts as P
from parts import GLASS, SLATE, TAU, kit

def jit_moss(i, k):
    """Whether a bay of a ruin has ivy on it."""
    return P.jit(i, k, 3.0) < 0.3


MARBLE = ("marble", "marble_shade", "stone_light")
SAND = ("sand", "sand_dark", "sand_light")


def triumphal_arch(stage, pal=MARBLE, suffix=""):
    """Three passages, eight columns and a chariot of four horses. Footprint 22 x 9 m, 26 m high."""
    def build():
        body, shade, light = pal
        w = P.W()
        rnd = random.Random(41)
        s = P.staged(w, stage, 1.9, 9.0, (0.4, 2.5), salt=7.0, cell=2.0)
        fin = stage == 3
        P.yard(w, stage, rnd, 22, 9, piles=[(-6.5, 0.0, 0.8, 90), (6.5, 0.0, 0.8, 90)], outline=(21.6, 8.6), z=0.4)
        w.box((0, 0, 0.2), (22, 9, 0.4), shade)
        for sx in (-1, 1):
            P.block(s, sx * 9, 0, 2, 6, 0.4, 15, body)
            P.block(s, sx * 4, 0, 2, 6, 0.4, 15, body)
            P.arch(s, sx * 6.5, 1.5, 6.0, 15, -3, 3, body, 8, ring=shade)
        P.arch(s, 0, 3.0, 8.0, 15, -3, 3, body, 10, ring=shade)
        if stage == 2:
            P.scaffold(w, (-10.5, -3.1), (10.5, -3.1), 5, 0.4, depth=1.2)
            P.scaffold(w, (10.5, 3.1), (-10.5, 3.1), 5, 0.4, depth=1.2)
            P.crane(w.at(0, 0.6, 0.4, 0), 12.0, 2.4, load=body)
            for sx in (-1, 1):                                                 # Timber centering under the side arches.
                for y in (-2.5, 2.5):
                    for k in (-1, 1):
                        w.cyl((sx * 6.5 + k * 1.3, y, 0.4), (sx * 6.5 + k * 1.3, y, 6.0), 0.1, 0.1, "pole", 5)
                    w.cyl((sx * 6.5 - 1.4, y, 6.0), (sx * 6.5 + 1.4, y, 6.0), 0.1, 0.1, "pole_dark", 4)
        if not fin:
            P.finish(w, P.model_id("wonder_triumphal_arch", stage))
            return

        bones = []
        w.box((0, 0, 15.6), (20.6, 6.6, 1.2), shade)
        w.box((0, 0, 17.85), (20, 5.6, 3.3), body)
        w.box((0, 0, 19.75), (20.8, 6.4, 0.5), shade)
        for face, rz in ((-1, 0), (1, 180)):
            f = w.at(0, 0, 0, rz)
            for x in (-9, -4, 4, 9):
                f.box((x, -3.7, 1.6), (1.5, 1.5, 2.4), shade)
                P.column(f, x, -3.7, 2.8, 10.2, 0.5, body, light)
                f.box((x, -3.6, 14.6), (1.6, 1.8, 3.2), body)
                f.box((x, -3.7, 16.3), (1.8, 1.8, 0.3), shade)
                P.statue(f.at(x, -3.7, 16.45), 2.8, "bronze", ("down", "hip"), "bronze_dark", cape="bronze_dark")
            f.box((0, -2.86, 17.9), (9.0, 0.14, 2.1), "bronze_dark")
            for k in range(3):
                f.box((0, -2.95, 18.5 - 0.6 * k), (7.6 - 1.2 * k, 0.08, 0.22), "gold")
            f.box((0, -3.2, 11.3), (1.0, 0.5, 1.4), "gold")
            for sx in (-1, 1):
                f.box((sx * 6.5, -3.06, 11.3), (2.6, 0.16, 3.2), "bronze_dark")
                f.box((sx * 6.5, -3.12, 11.3), (2.0, 0.12, 2.6), "bronze")
                f.cyl((sx * 6.5, -3.0, 8.6), (sx * 6.5, -3.2, 8.6), 0.5, 0.5, "gold", 10)
        w.box((0, 0.2, 20.2), (9.0, 5.4, 0.4), shade)                           # The chariot of four horses.
        for x in (-2.85, -0.95, 0.95, 2.85):
            P.horse(w.at(x, -0.9, 20.4), 2.9, "bronze", "bronze_dark")
            w.cyl((x, 0.2, 22.3), (0, 1.6, 21.6), 0.04, 0.04, "gold", 4)
        w.box((0, 1.9, 21.4), (2.6, 1.5, 1.2), "bronze_dark")
        w.box((0, 1.3, 21.9), (2.6, 0.2, 1.6), "bronze")
        for sx in (-1, 1):
            w.cyl((sx * 1.4, 1.9, 21.3), (sx * 1.6, 1.9, 21.3), 0.9, 0.9, "bronze", 10)
            w.cyl((sx * 1.6, 1.9, 21.3), (sx * 1.7, 1.9, 21.3), 0.25, 0.25, "gold", 6)
        g = w.at(0, 2.1, 21.6)
        hands = P.statue(g, 3.4, "gold", ("up", "fwd"), "gold_dark", cape="gold_dark", crown=True)
        hx, hy, hz = hands["hand_r"]
        for i in range(8):
            a0, a1 = TAU * i / 8, TAU * (i + 1) / 8
            g.cyl((hx + math.cos(a0) * 0.4, hy, hz + 0.4 + math.sin(a0) * 0.4), (hx + math.cos(a1) * 0.4, hy, hz + 0.4 + math.sin(a1) * 0.4), 0.08, 0.08, "gold_light", 4)
        flags = []
        for i, x in enumerate((-9.7, 9.7)):
            bones += P.flag(w, "flag%d" % i, x, 0, 20.0, 5.5, "cloth_red", 1.2)
            flags.append("flag%d" % i)
        P.finish(w, "wonder_triumphal_arch" + suffix, bones, [("idle", 4.0, lambda t: (P.flag_turns(flags, t), {}))])
    return build


def library(stage):
    """A rotunda under a copper dome, a portico of six columns and two wings. Footprint 32 x 26 m, 29 m high."""
    def build():
        w = P.W()
        rnd = random.Random(42)
        s = P.staged(w, stage, 2.6, 7.0, (0.4, 2.2), salt=8.0)
        fin = stage == 3
        F = 1.2
        P.yard(w, stage, rnd, 32, 26, piles=[(-12, -9.5, 0.9), (12, -9.5, 0.9)], timbers=[(11, 10.3, 0)], lodges=[(-10.5, 1.5, 90)] if stage == 1 else [],
               cranes=[(0, 1.5, 0, 12.0)], outline=(31.6, 25.6), z=F)
        w.box((0, 0.25, F / 2), (31, 23.5, F), "stone_dark")
        P.steps(w, 0, -11.5, 16, 5, 0.24, 0.3, "stone_light")
        P.drum(s, 0, 1.5, 7.5, F, 13, "brick", 12)
        P.block(s, 0, -6.5, 13, 4, F, 11.2, "brick")
        for sx in (-1, 1):
            P.block(s, sx * 10.5, 1.5, 8, 14, F, 10, "brick")
            for cy in (-1, 1):
                s.box((sx * 14.4, 1.5 + cy * 6.9, 5.6), (1.0, 1.0, 8.8), "stone_light")
                s.box((sx * 6.6, 1.5 + cy * 6.9, 5.6), (1.0, 1.0, 8.8), "stone_light")
        for i in range(6):
            P.column(s, -6.25 + 2.5 * i, -9.6, F, 9.0, 0.55, "marble", "stone_light")
        if stage == 2:
            P.scaffold(w, (-14.6, -5.6), (-6.4, -5.6), 3, F)
            P.scaffold(w, (6.4, -5.6), (14.6, -5.6), 3, F)
            P.scaffold_ring(w, 0, 1.5, 7.9, 4, n=5, z=F, a0=0.35, a1=math.pi - 0.35)
        if not fin:
            P.finish(w, P.model_id("wonder_library", stage))
            return

        bones, flags = [], []
        w.box((0, -9.0, 10.7), (15.4, 3.6, 1.0), "stone_light")                 # The portico.
        w.solid([(-7.9, -10.8, 11.2), (7.9, -10.8, 11.2), (0, -10.8, 14.4)], (0, 3.6, 0), "stone_light")
        w.solid([(-6.2, -10.9, 11.5), (6.2, -10.9, 11.5), (0, -10.9, 13.9)], (0, 0.2, 0), "marble_shade")
        w.box((-0.55, -11.0, 12.3), (0.9, 0.12, 0.7), "gold")                   # An open book.
        w.box((0.55, -11.0, 12.3), (0.9, 0.12, 0.7), "gold")
        P.roof(w.at(0, -6.4, 0, 90), 0, 0, 5.4, 13.6, 11.2, 3.0, SLATE, 0.2, 3)
        P.door(w.at(0, -8.5, F), 3.0, 5.0, "door", "stone_light", pointed=False)
        w.cyl((0, 1.5, 13.0), (0, 1.5, 13.5), 8.0, 8.0, "stone_light", 12, spin=15)
        w.cyl((0, 1.5, 13.5), (0, 1.5, 17.0), 6.5, 6.5, "plaster", 12, spin=15)
        w.cyl((0, 1.5, 17.0), (0, 1.5, 17.5), 7.0, 7.0, "stone_light", 12, spin=15)
        for i in range(12):
            a = TAU * i / 12
            x, y = math.cos(a) * 6.3, 1.5 + math.sin(a) * 6.3
            P.window(w.at(x, y, 14.2, math.degrees(a) + 90), 1.3, 1.9, GLASS[i % 5], "stone_light", pointed=False)
        P.dome(w, 0, 1.5, 17.5, 6.6, "copper", "copper_dark", 12, 6)
        for i in range(12):                                                    # The ribs of the dome.
            a = TAU * (i + 0.5) / 12
            for k in range(5):
                a0, a1 = (math.pi / 2) * k / 5.4, (math.pi / 2) * (k + 1) / 5.4
                w.cyl((math.cos(a) * math.cos(a0) * 6.55, 1.5 + math.sin(a) * math.cos(a0) * 6.55, 17.5 + math.sin(a0) * 6.65),
                      (math.cos(a) * math.cos(a1) * 6.55, 1.5 + math.sin(a) * math.cos(a1) * 6.55, 17.5 + math.sin(a1) * 6.65), 0.16, 0.14, "gold_dark", 4)
        w.cyl((0, 1.5, 23.6), (0, 1.5, 26.0), 1.3, 1.3, "plaster", 8)
        for i in range(8):
            a = TAU * i / 8
            w.box((math.cos(a) * 1.25, 1.5 + math.sin(a) * 1.25, 24.8), (0.14, 0.5, 1.6), "window", rz=math.degrees(a))
        P.dome(w, 0, 1.5, 26.0, 1.6, "copper", None, 8, 3)
        P.finial(w, 0, 1.5, 27.4, 1.0)
        for sx in (-1, 1):
            x = sx * 10.5
            w.box((x, 1.5, 10.2), (8.6, 14.6, 0.5), "stone_light")
            w.frustum(x, 1.5, 8.8, 14.8, 10.4, 0.0, 8.0, 13.4, "slate")
            w.box((x, 1.5, 13.4), (0.4, 8.2, 0.3), "slate_dark")
            for k in (-1, 1):
                P.window(w.at(x + k * 1.9, -5.52, 2.6), 1.5, 2.6, GLASS[1 + k], "stone_light", pointed=False)
                P.window(w.at(x + k * 1.9, -5.52, 6.6), 1.5, 2.2, "glass_dark", "stone_light", pointed=False)
            for k in range(4):
                y = -3.4 + 3.3 * k
                P.window(w.at(sx * 14.52, y, 2.6, 90 * sx), 1.5, 2.6, GLASS[k % 5], "stone_light", pointed=False)
                P.window(w.at(sx * 14.52, y, 6.6, 90 * sx), 1.5, 2.2, "glass_dark", "stone_light", pointed=False)
            w.box((sx * 9.2, -11.0, F + 0.7), (1.6, 1.6, 1.4), "stone_light")
            g = w.at(sx * 9.2, -11.0, F + 1.4)
            hands = P.statue(g, 3.2, "marble", ("front", "front"), "marble_shade", robe=True)
            g.box((0, hands["hand_r"][1] - 0.1, hands["hand_r"][2] + 0.1), (0.9, 0.2, 0.6), "gold_dark")
            bones += P.flag(w, "flag%d" % (sx > 0), sx * 14.0, -5.0, 10.4, 6.0, "cloth_blue", 1.2)
            flags.append("flag%d" % (sx > 0))
        P.finish(w, "wonder_library", bones, [("idle", 4.0, lambda t: (P.flag_turns(flags, t), {}))])
    return build


def mausoleum(stage):
    """A tomb on a stepped podium, ringed by columns, under a stepped pyramid. Footprint 22 x 26 m, 24 m high."""
    def build():
        w = P.W()
        rnd = random.Random(43)
        s = P.staged(w, stage, 1.4, 6.5, (0.0, 1.6), salt=9.0)
        fin = stage == 3
        P.yard(w, stage, rnd, 22, 26, piles=[(-9.6, -11.6, 0.8), (9.6, -11.6, 0.8)], outline=(21.6, 25.6))
        for i, (a, b) in enumerate(((20, 24), (18.6, 22.6), (17.2, 21.2))):
            s.box((0, 0.5, 0.5 + i), (a, b, 1.0), "marble_shade" if i % 2 == 0 else "marble")
        P.steps(s, 0, -10.1, 6.0, 12, 0.25, 0.2, "stone_light")
        P.block(s, 0, 0.5, 11, 14, 3.0, 10.0, "marble")
        xs = [-7.0 + 2.8 * i for i in range(6)]
        ys = [-8.6 + 2.6 * i for i in range(8)]
        cols = [(x, ys[0]) for x in xs] + [(x, ys[-1]) for x in xs] + [(xs[0], y) for y in ys[1:-1]] + [(xs[-1], y) for y in ys[1:-1]]
        for x, y in cols:
            P.column(s, x, y, 3.0, 7.0, 0.45, "marble", "marble_shade")
        if stage == 1:
            P.crane(w.at(0, 0.5, 1.4, 0), 6.0, 3.0, load="marble")
            P.lodge(w.at(0, 0, 1.4), -4, 5, 90)
        if stage == 2:
            P.scaffold_box(w, 0, 0.5, 11.2, 14.2, 3, z=3.0, sides="rbl", depth=1.2)
            P.crane(w.at(0, 0.5, 3.0, 0), 11.0, 3.0, load="marble")
        if not fin:
            P.finish(w, P.model_id("wonder_mausoleum", stage))
            return

        w.box((0, 0.5, 10.5), (15.4, 19.6, 1.0), "marble_shade")
        w.box((0, 0.5, 11.15), (16.0, 20.2, 0.3), "marble")
        for i in range(7):                                                     # The stepped pyramid.
            k = i / 7
            w.box((0, 0.5, 11.7 + 0.8 * i), (15.0 - 11.0 * k, 19.0 - 14.0 * k, 0.8), "marble" if i % 2 else "marble_shade")
        w.box((0, 0.5, 17.7), (3.6, 4.6, 0.8), "marble")
        w.box((0, 0.5, 18.4), (2.4, 3.2, 0.7), "bronze_dark")
        g = w.at(0, 0.5, 18.75)
        hands = P.statue(g, 4.6, "bronze", ("front", "front"), "bronze_dark", cape="bronze_dark", crown=True, detail=True)
        P.sword(g, (0, hands["hand_r"][1], hands["hand_r"][2]), 4.6, "gold_light")
        P.door(w.at(0, -6.5, 3.0), 2.6, 4.6, "bronze", "marble_shade", pointed=False)
        for sx in (-1, 1):
            P.brazier(w, sx * 4.4, -10.4, 3.0, 1.5, "bronze_dark")
            w.box((sx * 4.4, -12.6, 0.6), (1.6, 1.6, 1.2), "marble_shade")
            P._shapes.lantern(w.mb, sx * 2.2, -7.2, 6.4)
            for cy in (-1, 1):
                w.cyl((sx * 9.0, 0.5 + cy * 11.0, 1.0), (sx * 9.0, 0.5 + cy * 11.0, 2.2), 0.4, 0.7, "bronze", 8)
                w.cyl((sx * 9.0, 0.5 + cy * 11.0, 2.2), (sx * 9.0, 0.5 + cy * 11.0, 2.5), 0.7, 0.3, "bronze_dark", 8)
                P.cypress(w, sx * 10.2, 0.5 + cy * 7.0, 0, 1.6)
            g2 = w.at(sx * 4.4, -12.6, 1.2)
            hands2 = P.statue(g2, 2.6, "marble", ("down", "down"), "marble_shade", robe=True)
            del hands2
        P.finish(w, "wonder_mausoleum", [], [("idle", 4.0, lambda t: ({}, P.flame_moves(t, 0.1, 6)))])
    return build


def coliseum(stage):
    """An oval of three arcaded stories and an attic around a pit of sand. Footprint 44 x 36 m, 22 m high."""
    def build():
        w = P.W()
        rnd = random.Random(44)
        s = P.staged(w, stage, 1.6, 7.0, (0.4, 3.0), salt=10.0, cell=2.5)
        fin = stage == 3
        A, B, N = 21.0, 17.0, 36
        P.yard(w, stage, rnd, 44, 36, lodges=[(4, 3, 200)] if stage == 1 else [], cranes=[(-5, 0, 100, 12.0), (6, -1, -80, 12.0, 2)], piles=[(3, -5, 1.0), (-2, 6, 1.0)], timbers=[(0, -2, 10)])
        if fin:
            w.box((0, 0, 0.05), (44, 36, 0.1), "paving")
            w.prism([(math.cos(TAU * i / 24) * (A - 9.6), math.sin(TAU * i / 24) * (B - 9.6)) for i in range(24)], 0.1, 0.3, "sandbox")
        bones, flags = [], []
        for i in range(N):
            a = TAU * (i + 0.5) / N
            x, y = math.cos(a) * A, math.sin(a) * B
            deg = math.degrees(math.atan2(math.sin(a) * A, math.cos(a) * B))
            length = TAU * math.hypot(A * math.sin(a), B * math.cos(a)) / N * 1.1
            g = s.at(x, y, 0, deg)
            gate = min(abs(a - TAU * 0.75), abs(a - TAU * 0.25), abs(a - TAU * 0.5), abs(a - TAU)) < 0.1 or a < 0.1
            for k in range(3):
                g.box((-1.0, 0, 2.5 + 5 * k), (2.0, length, 5.0), "sand" if (i + k) % 2 else "sand_light")
                g.box((0.05, length * 0.46, 2.5 + 5 * k), (0.5, length * 0.14, 5.0), "marble")
                g.box((0.1, 0, 4.85 + 5 * k), (0.5, length, 0.3), "marble_shade")
            g.box((-0.9, 0, 16.8), (1.8, length, 3.6), "sand_dark")
            g.box((0.1, 0, 18.6), (0.6, length, 0.4), "marble_shade")
            for k in range(7):                                                 # The seats step down to the pit.
                g.box((-2.6 - 1.1 * k, 0, (13.2 - 1.7 * k) / 2), (1.15, length * (1 - 0.035 * (k + 2)), 13.2 - 1.7 * k), "stone_light" if k % 2 else "stone")
            if fin or stage == P.RUIN:
                f = (w if fin else s).at(x, y, 0, deg)
                for k in range(3):
                    wd = length * 0.56
                    if gate and k == 0:
                        P.arch_panel(f.at(0.03, 0, 0.1, 90), length * 0.7, 3.4)
                    else:
                        P.arch_panel(f.at(0.03, 0, 5 * k + 0.5, 90), wd, 2.7)
                        if fin and k > 0 and i % 3 == 0:
                            P.statue(f.at(0.2, 0, 5 * k + 0.5, 90), 2.2, "marble", ("down", "hip"), robe=True)
                    if not fin and jit_moss(i, k):
                        f.box((0.3, length * 0.2, 5 * k + 1.5), (0.14, length * 0.5, 3.0), "moss")
                f.box((0.06, 0, 16.9), (0.14, length * 0.3, 1.6), "glass_dark")
                if fin and i % 3 == 1:
                    f.cyl((0.3, 0, 15.5), (0.3, 0, 21.5), 0.1, 0.08, "pole_dark", 5)
                    f.box((0.3, 0, 21.3), (0.2, 0.2, 0.3), "gold")
        if stage == 2:
            P.scaffold(w, (-9, -18.4), (9, -18.4), 4)
            P.scaffold(w, (9, 18.4), (-9, 18.4), 4)
            P.scaffold(w, (22.4, -7), (22.4, 7), 4)
            P.scaffold(w, (-22.4, 7), (-22.4, -7), 4)
        if stage == P.RUIN:
            w.box((0, 0, 0.05), (44, 36, 0.1), "grass_dark")
            w.prism([(math.cos(TAU * i / 24) * (A - 9.6), math.sin(TAU * i / 24) * (B - 9.6)) for i in range(24)], 0.1, 0.3, "grass")
            P.rubble(w, rnd, 42, 34, 70, ("sand", "sand_dark", "stone_light"))
        if not fin:
            P.finish(w, P.model_id("wonder_coliseum", stage))
            return

        w.box((0, 7.6, 5.4), (7.0, 2.4, 0.5), "marble")                         # The box of honor.
        for sx in (-1, 1):
            P.column(w, sx * 3.0, 6.8, 5.6, 4.0, 0.25, "marble", "gold")
        w.solid([(-3.6, 6.4, 9.6), (3.6, 6.4, 9.6), (3.6, 8.8, 10.4), (-3.6, 8.8, 10.4)], (0, 0, 0.2), "cloth_purple")
        w.box((0, 7.9, 6.4), (1.4, 1.0, 1.6), "gold_dark")
        for i, (x, y) in enumerate(((-15.4, -12.4), (15.4, -12.4), (-15.4, 12.4), (15.4, 12.4))):
            name = "flag%d" % i
            bones += P.flag(w, name, x, y, 18.0, 7.0, "cloth_red" if i % 2 else "cloth_gold", 1.7)
            flags.append(name)
        for sx in (-1, 1):
            P.brazier(w, sx * 3.0, -18.8, 0.1, 2.0, "bronze_dark")
            w.box((sx * 6.4, 0, 0.5), (0.4, 3.0, 0.5), "plank_dark")           # Gates of the beasts.
        for k in range(4):
            a = TAU * k / 4 + 0.4
            w.box((math.cos(a) * 6.0, math.sin(a) * 4.0, 0.42), (2.2, 1.4, 0.06), "soil_dark", rz=40 * k)

        def idle(t):
            return P.flag_turns(flags, t), P.flame_moves(t, 0.15, 6)

        P.finish(w, "wonder_coliseum", bones, [("idle", 4.0, idle)])
    return build


def hanging_gardens(stage):
    """Four terraces of trees and vines with water falling from one to the next. Footprint 32 x 32 m, 26 m high."""
    def build():
        w = P.W()
        rnd = random.Random(45)
        s = P.staged(w, stage, 1.6, 8.0, (0.0, 2.0), salt=11.0)
        fin = stage == 3
        P.yard(w, stage, rnd, 32, 32, piles=[(-14.6, -14.6, 0.8), (14.6, -14.6, 0.8), (14.6, 14.6, 0.8)], timbers=[(-14.8, 8, 90)], outline=(31.6, 31.6))
        sides = (28, 22, 16, 10)
        H = 5.0
        for i, a in enumerate(sides):
            z = H * i
            if i == 0:
                P.block(s, 0, 0, a, a, z, z + H, "sand")
            else:
                P.block(s, 0, 0, a, a, z, z + H, "sand" if i % 2 == 0 else "sand_light")
            s.box((0, 0, z + H - 0.2), (a + 0.6, a + 0.6, 0.4), "sand_dark")
        if stage == 1:
            P.crane(w.at(0, 0, 0, 0), 6.5, 3.0, load="sand_light")
            P.lodge(w, 6, 5, 180)
        if stage == 2:
            P.scaffold(w, (-14.2, -14.2), (14.2, -14.2), 3)
            P.scaffold(w, (14.2, -14.2), (14.2, 14.2), 3)
            P.crane(w.at(0, 0, 0, 30), 13.0, 4.0, load="sand_light")
            P.crane(w.at(-7, 6, 0, 200), 10.0, 3.0, load="sand_light")
        if not fin:
            P.finish(w, P.model_id("wonder_hanging_gardens", stage))
            return

        water = w.bone("water")
        for i, a in enumerate(sides):
            z = H * i
            top = z + H
            inner = sides[i + 1] if i + 1 < len(sides) else 0
            w.box((0, 0, top + 0.1), (a - 0.6, a - 0.6, 0.25), "grass" if i % 2 == 0 else "grass_dark")
            for rz in (0, 90, 180, 270):
                f = w.at(0, 0, 0, rz)
                n = int(a // 3.4)
                for k in range(n):                                             # The arcade of each terrace.
                    x = (k - (n - 1) / 2) * (a / n)
                    if rz == 0 and abs(x) < 1.6:
                        continue
                    P.arch_panel(f.at(x, -a / 2 - 0.02, z + 0.5), a / n * 0.55, 2.4)
                    f.box((x + a / n / 2, -a / 2 - 0.15, z + 2.3), (0.5, 0.3, 4.6), "sand_light")
                for k in range(int(a // 2.2)):                                 # Vines over the edge.
                    x = rnd.uniform(-a / 2 + 0.8, a / 2 - 0.8)
                    if rz == 0 and abs(x) < 1.8:
                        continue
                    drop = rnd.uniform(1.0, 3.2)
                    f.box((x, -a / 2 - 0.42, top + 0.1 - drop / 2), (rnd.uniform(0.5, 1.1), 0.18, drop), rnd.choice(("leaf", "leaf_dark", "leaf_light")))
                band = (a - inner) / 2
                if band > 1.5:
                    y = -(inner / 2 + band / 2)
                    for k in range(max(2, int(a // 4.5))):
                        x = (k + 0.5) / max(2, int(a // 4.5)) * (a - 2.5) - (a - 2.5) / 2
                        if rz == 0 and abs(x) < 2.6:
                            continue
                        kind = (k + i + rz // 90) % 3
                        if kind == 0:
                            P.tree(f, x, y, top + 0.2, rnd.uniform(1.0, 1.4), rnd)
                        elif kind == 1:
                            P.cypress(f, x, y, top + 0.2, rnd.uniform(0.9, 1.3))
                        else:
                            f.sphere((x, y, top + 0.6), 0.8, rnd.choice(("leaf", "petal", "leaf_gold")), 6, 4, (1.2, 1.0, 0.7))
            # The water: a channel on the terrace, then a fall down its front.
            y_face = -a / 2 - 0.3
            water.box((0, -(a / 2 + (inner / 2 if inner else 2.0)) / 2, top + 0.24), (2.0, a / 2 - (inner / 2 if inner else 2.0), 0.1), "water")
            water.box((0, y_face, z + H / 2 + 0.15), (1.8, 0.2, H + 0.2), "water_light")
            w.box((0, y_face - 0.05, top + 0.3), (2.6, 0.5, 0.3), "sand_dark")
            P.steps(w.at((a / 2 - 2.2) * (1 if i % 2 == 0 else -1), 0, 0), 0, -a / 2, 2.4, 10, 0.5, 0.2, "sand_light", z0=z)
        w.cyl((0, -15.2, 0.0), (0, -15.2, 0.6), 1.7, 1.9, "sand_dark", 10)        # The basin at the foot.
        w.cyl((0, -15.2, 0.5), (0, -15.2, 0.66), 1.5, 1.5, "water", 10)
        top = H * 4
        for cx in (-1, 1):                                                     # The pavilion on top.
            for cy in (-1, 1):
                P.column(w, cx * 2.6, cy * 2.6, top + 0.2, 4.0, 0.3, "marble", "gold")
        w.box((0, 0, top + 4.4), (6.6, 6.6, 0.4), "sand_light")
        P.dome(w, 0, 0, top + 4.6, 2.8, "gold", "gold_dark", 10, 4, 1.0)
        P.finial(w, 0, 0, top + 7.3, 0.8)
        w.cyl((0, 0, top + 0.2), (0, 0, top + 0.6), 1.5, 1.6, "marble", 10)
        water.cyl((0, 0, top + 0.6), (0, 0, top + 2.4), 0.2, 0.06, "water_light", 6)
        w.cyl((0, 0, top + 0.5), (0, 0, top + 0.66), 1.4, 1.4, "water", 10)

        def idle(t):
            return {}, {"water": (0, 0, 0.06 * math.sin(TAU * 4 * t))}

        P.finish(w, "wonder_hanging_gardens", [("water", (0, 0, 10), (0, 0, 11), None)], [("idle", 4.0, idle)])
    return build


def great_bell(stage):
    """A bronze bell of 5 m under a double roof, struck by a hanging log. Footprint 14 x 14 m, 16 m high."""
    def build():
        w = P.W()
        rnd = random.Random(46)
        s = P.staged(w, stage, 1.6, 4.5, (0.0, 0.0), salt=12.0)
        fin = stage == 3
        P.yard(w, stage, rnd, 14, 14, piles=[(-5.8, -6.2, 0.7), (5.8, 6.2, 0.7)], timbers=[(5.6, -6.2, 0)], outline=(13.6, 13.6))
        s.frustum(0, 0, 12, 12, 0, 11, 11, 1.6, "stone")
        s.box((0, 0, 1.7), (10.6, 10.6, 0.2), "stone_light")
        for rz in (0, 90, 180, 270):
            P.steps(s.at(0, 0, 0, rz), 0, -5.6, 4.0, 6, 0.27, 0.2, "stone_light")
        posts = [(cx * 3.6, cy * 3.6) for cx in (-1, 1) for cy in (-1, 1)]
        if stage >= 2:
            for x, y in posts:
                w.cyl((x, y, 1.8), (x, y, 9.0 if fin else 7.5), 0.42, 0.38, "lacquer", 8)
                w.cyl((x, y, 1.8), (x, y, 2.4), 0.6, 0.55, "stone_dark", 8)
        if stage == 2:
            P.scaffold_box(w, 0, 0, 8.0, 8.0, 2, z=1.8, depth=1.2)
            w.cyl((0, 0, 1.8), (0, 0, 3.2), 2.6, 2.3, "soil_dark", 10)          # The casting pit and its mould.
            w.cyl((0, 0, 3.2), (0, 0, 4.4), 1.9, 1.5, "tile_dark", 10)
            w.cyl((2.6, 2.0, 1.8), (2.6, 2.0, 3.6), 0.8, 0.6, "brick", 8)
            P.flame(w, 2.6, 2.0, 3.6, 0.8)
            P.finish(w, "wonder_great_bell_stage2", [], [("idle", 4.0, lambda t: ({}, P.flame_moves(t, 0.06, 6)))])
            return
        if stage == 1:
            P.lodge(w.at(0, 0, 1.6), 0, 1.5, 0)
            P.finish(w, "wonder_great_bell_stage1")
            return

        for sx in (-1, 1):
            w.box((sx * 3.6, 0, 8.6), (0.5, 8.6, 0.6), "lacquer_dark")
            w.box((0, sx * 3.6, 8.6), (8.6, 0.5, 0.6), "lacquer_dark")
            w.box((0, sx * 3.6, 4.4), (7.2, 0.3, 0.4), "lacquer_dark")
        w.frustum(0, 0, 13.0, 13.0, 8.9, 12.0, 12.0, 9.3, "obsidian")            # The lower roof, with upturned corners.
        w.frustum(0, 0, 12.0, 12.0, 9.3, 5.0, 5.0, 11.6, "slate_dark")
        w.box((0, 0, 12.2), (4.6, 4.6, 1.4), "plaster")
        for cx in (-1, 1):
            for cy in (-1, 1):
                w.cyl((cx * 6.0, cy * 6.0, 9.0), (cx * 7.0, cy * 7.0, 10.2), 0.3, 0.08, "obsidian", 4)
                w.box((cx * 2.2, cy * 2.2, 12.2), (0.4, 0.4, 1.4), "lacquer")
                w.cyl((cx * 3.6, cy * 3.6, 12.9), (cx * 4.3, cy * 4.3, 13.8), 0.22, 0.06, "obsidian", 4)
        w.frustum(0, 0, 7.6, 7.6, 12.8, 7.0, 7.0, 13.1, "obsidian")
        w.frustum(0, 0, 7.0, 7.0, 13.1, 0.0, 0.0, 15.4, "slate_dark")
        P.finial(w, 0, 0, 15.2, 0.9)
        w.box((0, 0, 8.3), (0.5, 7.4, 0.5), "pole_dark")
        bell = w.bone("bell")
        bell.cyl((0, 0, 8.2), (0, 0, 7.6), 0.3, 0.5, "bronze_dark", 8)
        bell.cyl((0, 0, 7.6), (0, 0, 6.8), 1.3, 2.0, "bronze", 12)
        bell.cyl((0, 0, 6.8), (0, 0, 3.6), 2.0, 2.3, "bronze", 12)
        bell.cyl((0, 0, 3.6), (0, 0, 3.1), 2.3, 2.5, "bronze_light", 12)
        for z in (4.2, 5.6, 6.6):
            bell.cyl((0, 0, z), (0, 0, z + 0.2), 2.33 - (z - 3.6) * 0.09, 2.31 - (z - 3.6) * 0.09, "bronze_dark", 12)
        bell.cyl((2.2, 0, 4.4), (2.42, 0, 4.4), 0.5, 0.5, "gold", 8)
        st = w.bone("striker")
        st.cyl((3.4, 0, 4.4), (6.4, 0, 4.4), 0.32, 0.32, "bark", 8)
        st.cyl((3.3, 0, 4.4), (3.4, 0, 4.4), 0.3, 0.3, "log_end", 8)
        for x in (4.0, 5.8):
            st.cyl((x, 0, 4.7), (x, 0, 8.6), 0.03, 0.03, "rope", 4)
        w.box((4.9, 0, 8.6), (3.0, 0.3, 0.3), "pole_dark")
        st.cyl((6.4, 0, 4.4), (6.7, 0, 3.4), 0.03, 0.03, "rope", 4)

        def ring(t):
            hit = max(0.0, math.sin(TAU * t))                                   # The log swings in and falls back.
            back = max(0.0, -math.sin(TAU * t))
            sway = 3.0 * math.sin(TAU * 2 * t) * (1.0 if t > 0.25 else t * 4)
            return {"bell": [(kit.Y, sway * (1 - t))]}, {"striker": (-0.75 * hit + 0.6 * back, 0, 0.12 * (hit + back))}

        P.finish(w, "wonder_great_bell", [("bell", (0, 0, 8.2), (0, 0, 3.2), None), ("striker", (3.4, 0, 4.4), (7.2, 0, 4.4), None)], [("ring", 4.0, ring)])
    return build


MODELS = {}
for _base, _fn in (("wonder_triumphal_arch", triumphal_arch), ("wonder_library", library), ("wonder_mausoleum", mausoleum), ("wonder_coliseum", coliseum),
                   ("wonder_hanging_gardens", hanging_gardens), ("wonder_great_bell", great_bell)):
    for _stage in (1, 2, 3):
        MODELS[P.model_id(_base, _stage)] = _fn(_stage)
MODELS["wonder_triumphal_arch_sand"] = triumphal_arch(3, SAND, "_sand")
MODELS["wonder_coliseum_ruin"] = coliseum(P.RUIN)
