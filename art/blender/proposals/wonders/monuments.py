"""Monuments: single prestige pieces of 3 to 15 m, cheaper than a wonder,
each in the materials that make sense (stone, white marble, bronze, gold).
"""

import math
import random

import parts as P
from parts import TAU, kit

PALS = {
    "stone": dict(body="stone", trim="stone_dark", light="stone_light", fig="stone_light", fig2="stone", accent="bronze"),
    "marble": dict(body="marble", trim="marble_shade", light="marble", fig="marble", fig2="marble_shade", accent="gold"),
    "bronze": dict(body="stone", trim="stone_dark", light="stone_light", fig="bronze", fig2="bronze_dark", accent="gold"),
    "gold": dict(body="marble", trim="marble_shade", light="marble", fig="gold", fig2="gold_dark", accent="gold_light"),
    "obsidian": dict(body="obsidian", trim="obsidian_light", light="obsidian_edge", fig="obsidian_light", fig2="obsidian", accent="crystal_glow"),
}


def victory_column(name, key):
    """A column with a spiral band and a winged victory. Footprint 4 x 4 m, 15 m high."""
    def build():
        p = PALS[key]
        w = P.W()
        w.box((0, 0, 0.2), (4, 4, 0.4), p["trim"])
        w.box((0, 0, 0.6), (3.2, 3.2, 0.4), p["body"])
        w.box((0, 0, 1.0), (2.5, 2.5, 0.4), p["trim"])
        w.box((0, 0, 2.3), (2.0, 2.0, 2.2), p["body"])
        w.box((0, 0, 3.5), (2.4, 2.4, 0.3), p["light"])
        for rz in (0, 90, 180, 270):
            f = w.at(0, 0, 0, rz)
            f.box((0, -1.02, 2.3), (1.3, 0.08, 1.3), p["accent"])
            f.cyl((1.75, -1.75, 0.4), (1.75, -1.75, 1.3), 0.12, 0.1, p["trim"], 6)
            f.sphere((1.75, -1.75, 1.4), 0.16, p["accent"], 6, 4)
            f.cyl((-1.75, -1.75, 1.1), (1.75, -1.75, 1.1), 0.04, 0.04, "iron", 4)
        w.cyl((0, 0, 3.65), (0, 0, 4.0), 0.95, 0.8, p["light"], 10)
        w.cyl((0, 0, 4.0), (0, 0, 11.0), 0.72, 0.6, p["body"], 10)
        for i in range(44):
            u = i / 44
            a = TAU * 3.5 * u
            r = 0.74 - 0.12 * u
            w.box((math.cos(a) * r, math.sin(a) * r, 4.3 + 6.4 * u), (0.14, 0.52, 0.34), p["accent"] if i % 2 else p["trim"], rz=math.degrees(a))
        w.cyl((0, 0, 11.0), (0, 0, 11.5), 0.6, 1.0, p["light"], 10)
        w.box((0, 0, 11.65), (2.0, 2.0, 0.3), p["light"])
        w.sphere((0, 0, 12.1), 0.5, p["accent"], 8, 5, (1, 1, 0.7))
        g = w.at(0, 0, 12.3)
        hands = P.statue(g, 2.8, p["fig"], ("up", "side"), p["fig2"], robe=True)
        for s in (-1, 1):
            g.solid([(s * 0.2, 0.28, 1.6), (s * 2.0, 0.6, 3.2), (s * 1.6, 0.6, 1.5), (s * 0.5, 0.28, 0.9)], (0, 0.12, 0), p["fig2"])
            g.solid([(s * 0.3, 0.3, 1.9), (s * 1.5, 0.5, 2.9), (s * 0.9, 0.45, 1.6)], (0, -0.1, 0), p["fig"])
        hx, hy, hz = hands["hand_r"]
        for i in range(8):
            a0, a1 = TAU * i / 8, TAU * (i + 1) / 8
            g.cyl((hx + math.cos(a0) * 0.33, hy, hz + 0.35 + math.sin(a0) * 0.33), (hx + math.cos(a1) * 0.33, hy, hz + 0.35 + math.sin(a1) * 0.33), 0.07, 0.07, p["accent"], 4)
        P.finish(w, name)
    return build


def equestrian(name, key):
    """A rider with a raised sword on a tall pedestal. Footprint 4 x 6 m, 9 m high."""
    def build():
        p = PALS[key]
        w = P.W()
        w.box((0, 0, 0.2), (4, 6, 0.4), p["trim"])
        w.box((0, 0, 0.55), (3.4, 5.4, 0.3), p["body"])
        w.box((0, 0, 0.85), (2.8, 5.0, 0.3), p["light"])
        w.box((0, 0, 2.1), (2.4, 4.6, 2.4), p["body"])
        w.box((0, 0, 3.4), (2.8, 5.0, 0.3), p["light"])
        w.box((0, -2.32, 2.1), (1.5, 0.08, 1.2), p["accent"])
        w.box((0, 2.32, 2.1), (1.5, 0.08, 1.2), p["accent"])
        for sx in (-1, 1):
            w.box((sx * 1.22, 0, 2.1), (0.08, 3.4, 1.2), p["fig2"])
            for k in range(3):
                w.box((sx * 1.27, -1.1 + 1.1 * k, 2.1), (0.06, 0.6, 0.8), p["accent"] if k == 1 else p["fig"])
        g = w.at(0, 0.3, 3.55)
        P.horse(g, 3.4, p["fig"], p["fig2"])
        r, hands, u = P.rider(g, 3.4, p["fig"], p["fig2"], arms=("up", "fwd"), crown=key != "stone", cape=p["fig2"])
        P.sword(r, hands["hand_r"], u, p["accent"] if key in ("stone", "marble") else "steel", up=True, hilt=p["accent"])
        g.cyl((0, -2.2, 3.1), hands["hand_l"][0:1] + (hands["hand_l"][1] + 0.0, hands["hand_l"][2] + 0.8 * 3.4 - 0.5 * u), 0.03, 0.03, p["fig2"], 4)
        P.finish(w, name)
    return build


def obelisk(name, key):
    """A needle of one stone with a gilded tip and four guardians. Footprint 5 x 5 m, 13 m high."""
    def build():
        p = PALS[key]
        w = P.W()
        w.box((0, 0, 0.15), (5, 5, 0.3), p["trim"])
        w.box((0, 0, 0.45), (4.0, 4.0, 0.3), p["body"])
        w.box((0, 0, 0.75), (3.0, 3.0, 0.3), p["trim"])
        w.box((0, 0, 1.7), (2.2, 2.2, 1.6), p["body"])
        w.box((0, 0, 2.6), (2.5, 2.5, 0.2), p["light"])
        w.frustum(0, 0, 1.5, 1.5, 2.7, 0.95, 0.95, 11.2, p["body"])
        w.frustum(0, 0, 0.95, 0.95, 11.2, 0.0, 0.0, 12.7, "gold" if key != "obsidian" else "crystal")
        for rz in (0, 90, 180, 270):
            f = w.at(0, 0, 0, rz)
            f.box((0, -1.12, 1.7), (1.4, 0.08, 1.0), p["accent"])
            for k in range(6):
                z = 3.6 + 1.25 * k
                half = (1.5 - 0.55 * (z - 2.7) / 8.5) / 2
                f.box((0, -half - 0.01, z), (half * 1.1, 0.06, 0.5 if k % 2 else 0.28), p["accent"])
            g = f.at(1.95, -1.95, 0.6, -45)                                    # A guardian at each corner.
            g.box((0, 0.1, 0.35), (0.7, 1.2, 0.7), p["fig"])
            g.sphere((0, -0.5, 0.95), 0.36, p["fig"], 7, 5)
            g.box((0, -0.85, 0.2), (0.6, 0.6, 0.2), p["fig"])
            for s in (-1, 1):
                g.cyl((s * 0.2, -0.45, 1.2), (s * 0.26, -0.42, 1.5), 0.1, 0.0, p["fig2"], 4)
        P.finish(w, name)
    return build


def memorial(name, key):
    """A curved wall of shields, a sword set in a block and two flames. Footprint 8 x 5 m, 3.6 m high."""
    def build():
        p = PALS[key]
        w = P.W()
        w.box((0, 0, 0.15), (8, 5, 0.3), p["trim"])
        w.box((0, 0.4, 0.4), (7.2, 3.6, 0.2), p["body"])
        for i in range(-2, 3):
            h = 2.2 + 0.45 * (2 - abs(i))
            f = w.at(i * 1.45, 1.9 - 0.16 * i * i, 0.5, -i * 9)
            f.box((0, 0, h / 2), (1.5, 0.5, h), p["body"])
            f.box((0, 0, h + 0.1), (1.66, 0.66, 0.2), p["light"])
            f.cyl((0, -0.25, h - 0.75), (0, -0.33, h - 0.75), 0.45, 0.45, p["accent"], 10)
            f.cyl((0, -0.33, h - 0.75), (0, -0.42, h - 0.75), 0.14, 0.05, p["fig2"], 6)
            f.box((0, -0.27, (h - 1.4) / 2 + 0.1), (1.0, 0.06, h - 1.6), p["trim"])
            for k in range(int((h - 1.6) / 0.25)):
                f.box((0, -0.31, 0.3 + 0.25 * k), (0.7 if k % 2 else 0.55, 0.04, 0.08), p["light"])
        g = w.at(0, -0.6, 0.5)
        g.box((0, 0, 0.4), (1.3, 1.3, 0.8), p["body"])
        g.box((0, 0, 0.85), (1.5, 1.5, 0.12), p["light"])
        P.sword(g.at(0, 0, 0.9), (0, 0, 1.5), 4.2, "steel", hilt=p["accent"])
        g.sphere((0, 0, 2.95), 0.3, "steel", 7, 4, (1, 1.1, 0.9))
        for sx in (-1, 1):
            P.brazier(w, sx * 3.0, -1.4, 0.3, 0.8, "bronze_dark")
            for k in range(8):                                                 # A wreath.
                a = TAU * k / 8
                w.sphere((sx * 1.3 + math.cos(a) * 0.3, -0.75, 0.9 + math.sin(a) * 0.3), 0.13, "leaf_dark" if k % 2 else "leaf", 5, 3)
            w.sphere((sx * 1.3, -0.8, 0.62), 0.09, "cloth_red", 5, 3)
        P.finish(w, name, [], [("idle", 4.0, lambda t: ({}, P.flame_moves(t, 0.06, 6)))])
    return build


def founder_stone():
    """The boulder where the first settlers camped, with a plaque, the first axe and a flag. Footprint 5 x 5 m."""
    w = P.W()
    rnd = random.Random(61)
    w.cyl((0, 0, 0), (0, 0, 0.1), 2.45, 2.45, "grass", 12)
    w.sphere((0, 0.3, 0.9), 1.5, "stone", 8, 5, (1.2, 1.0, 0.9))
    w.sphere((0.9, 0.8, 0.6), 0.9, "stone_dark", 7, 4, (1.1, 1.0, 0.8))
    w.sphere((-0.8, 0.9, 0.5), 0.7, "stone_light", 7, 4)
    w.sphere((-0.2, 0.5, 2.0), 0.5, "moss", 6, 3, (1.6, 1.3, 0.4))
    w.box((0, -1.05, 1.0), (1.2, 0.12, 0.8), "bronze_dark")
    w.box((0, -1.12, 1.0), (1.0, 0.06, 0.6), "bronze")
    for k in range(3):
        w.box((0, -1.16, 1.18 - 0.18 * k), (0.7 - 0.1 * k, 0.03, 0.06), "gold")
    P._shapes.stump(w.mb, 1.55, -1.0, 0.5, 0.3)
    w.cyl((1.55, -1.0, 0.5), (1.2, -1.35, 1.3), 0.035, 0.03, "pole", 5)         # The first axe, left in the first stump.
    w.box((1.52, -1.03, 0.6), (0.3, 0.06, 0.2), "steel", rz=45)
    for i in range(9):
        a = TAU * i / 9 + 0.2
        P._shapes.rock(w.mb, math.cos(a) * 2.1, math.sin(a) * 2.1, 0.12, rnd.uniform(0.2, 0.32), rnd)
    for i in range(12):
        a = rnd.uniform(0, TAU)
        r = rnd.uniform(1.5, 2.0)
        w.cyl((math.cos(a) * r, math.sin(a) * r, 0.1), (math.cos(a) * r, math.sin(a) * r, 0.4), 0.02, 0.02, "leaf", 4)
        w.sphere((math.cos(a) * r, math.sin(a) * r, 0.44), 0.09, rnd.choice(("petal", "leaf_gold", "cloth_white")), 5, 3)
    bones = P.flag(w, "flag", -1.5, -0.6, 0.0, 4.4, "cloth_red", 0.9)
    P.finish(w, "monument_founder_stone", bones, [("idle", 4.0, lambda t: (P.flag_turns(["flag"], t), {}))])


def fountain(name, key):
    """A basin of eight sides with four peoples back to back under a bowl. Footprint 8 x 8 m, 6 m high."""
    def build():
        p = PALS[key]
        w = P.W()
        w.cyl((0, 0, 0), (0, 0, 0.3), 4.0, 3.9, p["trim"], 8, spin=22.5)
        w.cyl((0, 0, 0.3), (0, 0, 0.75), 3.7, 3.7, p["body"], 8, spin=22.5)
        w.cyl((0, 0, 0.75), (0, 0, 0.82), 3.4, 3.4, "water", 8, spin=22.5)
        for i in range(8):
            a0, a1 = TAU * (i + 0.5) / 8, TAU * (i + 1.5) / 8
            P.wall(w, (math.cos(a0) * 3.62, math.sin(a0) * 3.62), (math.cos(a1) * 3.62, math.sin(a1) * 3.62), 0.3, 1.05, 0.4, p["light"])
            w.sphere((math.cos(a0) * 3.62, math.sin(a0) * 3.62, 1.15), 0.22, p["accent"], 6, 4)
        w.cyl((0, 0, 0.3), (0, 0, 1.7), 1.5, 1.3, p["body"], 8)
        w.cyl((0, 0, 1.7), (0, 0, 1.9), 1.5, 1.5, p["light"], 8)
        figures = (dict(h=2.1, arms=("front", "front")), dict(h=1.7, arms=("front", "front"), stocky=1.5, beard=True),
                   dict(h=2.25, arms=("down", "fwd"), robe=True, ears=p["fig"]), dict(h=2.0, arms=("down", "hip"), ears=p["fig2"]))
        for i, spec in enumerate(figures):
            g = w.at(0, 0, 1.9, 90 * i).at(0, -0.85, 0)
            spec = dict(spec)
            h = spec.pop("h")
            hands = P.statue(g, h, p["fig"], mat2=p["fig2"], **spec)
            if i == 0:
                P.sword(g, (0, hands["hand_r"][1], hands["hand_r"][2]), h, p["fig2"], hilt=p["accent"])
            elif i == 1:
                g.cyl((0, hands["hand_r"][1], 0.2), (0, hands["hand_r"][1], hands["hand_r"][2] + 0.1), 0.05, 0.05, p["fig2"], 5)
                g.box((0, hands["hand_r"][1], 0.2), (0.6, 0.3, 0.3), p["fig2"])
            elif i == 2:
                g.cyl((hands["hand_l"][0], hands["hand_l"][1], 0), (hands["hand_l"][0], hands["hand_l"][1], h * 1.1), 0.035, 0.03, p["fig2"], 5)
                g.sphere((hands["hand_l"][0], hands["hand_l"][1], h * 1.12), 0.1, p["accent"], 5, 3)
            else:
                P.spear(g, hands["hand_r"], h, p["fig2"], p["accent"])
        w.cyl((0, 0, 1.9), (0, 0, 4.4), 0.42, 0.34, p["body"], 8)
        w.cyl((0, 0, 4.4), (0, 0, 4.85), 0.45, 1.25, p["light"], 10)
        w.cyl((0, 0, 4.8), (0, 0, 4.88), 1.1, 1.1, "water", 10)
        jet = w.bone("jet")
        jet.cyl((0, 0, 4.85), (0, 0, 6.0), 0.14, 0.05, "water_light", 6)
        jet.sphere((0, 0, 6.0), 0.24, "water_light", 6, 4, (1.3, 1.3, 0.6))
        fall = w.bone("fall")
        for i in range(4):
            a = TAU * (i + 0.5) / 4
            w.cyl((math.cos(a) * 1.2, math.sin(a) * 1.2, 4.6), (math.cos(a) * 1.75, math.sin(a) * 1.75, 4.5), 0.12, 0.09, p["accent"], 6)
            fall.cyl((math.cos(a) * 1.75, math.sin(a) * 1.75, 4.5), (math.cos(a) * 1.95, math.sin(a) * 1.95, 0.8), 0.045, 0.07, "water_light", 5)
            fall.sphere((math.cos(a) * 1.95, math.sin(a) * 1.95, 0.86), 0.26, "water_light", 6, 3, (1, 1, 0.3))

        def idle(t):
            return {}, {"jet": (0, 0, 0.14 * math.sin(TAU * 4 * t)), "fall": (0, 0, 0.05 * math.sin(TAU * 8 * t))}

        P.finish(w, name, [("jet", (0, 0, 4.85), (0, 0, 6.0), None), ("fall", (0, 0, 4.8), (0, 0, 0.8), None)], [("idle", 4.0, idle)])
    return build


def eternal_flame(name, key):
    """A bowl of fire on three leaning pillars over a round dais. Footprint 5 x 5 m, 5.5 m high."""
    def build():
        p = PALS[key]
        w = P.W()
        w.cyl((0, 0, 0), (0, 0, 0.3), 2.45, 2.4, p["trim"], 12)
        w.cyl((0, 0, 0.3), (0, 0, 0.6), 1.95, 1.9, p["body"], 12)
        for i in range(12):
            a = TAU * i / 12
            w.box((math.cos(a) * 2.15, math.sin(a) * 2.15, 0.36), (0.14, 0.5, 0.12), p["accent"], rz=math.degrees(a))
        for i in range(3):
            a = TAU * i / 3 + math.pi / 2
            b, t = (math.cos(a) * 1.5, math.sin(a) * 1.5, 0.6), (math.cos(a) * 0.75, math.sin(a) * 0.75, 3.2)
            w.cyl(b, t, 0.26, 0.18, p["body"], 6)
            w.cyl((b[0], b[1], 0.6), (b[0], b[1], 0.85), 0.4, 0.34, p["light"], 6)
            for u in (0.3, 0.62):
                q = [b[k] + (t[k] - b[k]) * u for k in range(3)]
                w.sphere(q, 0.27, p["accent"], 6, 4, (1, 1, 0.5))
        bowl = "bronze" if key == "stone" else ("gold" if key == "gold" else "bronze_light")
        w.cyl((0, 0, 3.0), (0, 0, 3.2), 0.5, 0.6, bowl, 10)
        w.cyl((0, 0, 3.2), (0, 0, 3.8), 0.6, 1.3, bowl, 10)
        w.cyl((0, 0, 3.74), (0, 0, 3.82), 1.2, 1.2, "coal", 10)
        P.flame(w, 0, 0, 3.8, 1.5)
        P.finish(w, name, [], [("idle", 4.0, lambda t: ({}, P.flame_moves(t, 0.12, 6)))])
    return build


MODELS = {"monument_founder_stone": founder_stone}
for _base, _fn, _keys in (("monument_victory_column", victory_column, ("stone", "marble", "bronze", "gold")),
                          ("monument_equestrian", equestrian, ("stone", "marble", "bronze", "gold")),
                          ("monument_obelisk", obelisk, ("stone", "marble", "obsidian")),
                          ("monument_memorial", memorial, ("stone", "marble")),
                          ("monument_fountain", fountain, ("stone", "marble", "bronze")),
                          ("monument_eternal_flame", eternal_flame, ("stone", "marble", "gold"))):
    for _key in _keys:
        _name = "%s_%s" % (_base, _key)
        MODELS[_name] = _fn(_name, _key)
