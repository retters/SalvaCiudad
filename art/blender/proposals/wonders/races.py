"""Wonders of the peoples: the lizard-folk ziggurat, the elven world tree,
the dwarven mountain gate, the dark-elf obsidian spire, the cat-folk sun
temple, the fox-folk great shrine, the frog-folk lily palace and the orc war
arena. Each is built in three stages (see parts.py).
"""

import math
import random

import parts as P
from parts import TAU, kit


def _stages(base, fn):
    return {P.model_id(base, stage): fn(stage) for stage in (1, 2, 3)}


# ------------------------------------------------------------------ ziggurat


def ziggurat(stage):
    """Five tiers, four stairways and a shrine of the sun. Footprint 40 x 40 m, 33 m high."""
    def build():
        w = P.W()
        rnd = random.Random(31)
        s = P.staged(w, stage, 2.0, 11.0, (0.0, 0.0), salt=1.0)
        fin = stage == 3
        P.yard(w, stage, rnd, 40, 40, piles=[(-18.9, -18.9, 0.9), (18.9, -18.9, 0.9), (18.9, 18.9, 0.9), (-18.9, 18.9, 0.9)], outline=(39.6, 39.6))
        sides = (36, 30, 24, 18, 13)
        for i, a in enumerate(sides):
            z = 4.5 * i
            s.frustum(0, 0, a, a, z, a - 1.6, a - 1.6, z + 4.5, "sand" if i % 2 == 0 else "sand_dark")
            s.box((0, 0, z + 4.0), (a - 1.42, a - 1.42, 0.3), "turquoise")
            s.box((0, 0, z + 4.35), (a - 1.3, a - 1.3, 0.3), "sand_light")
        for rz in (0, 90, 180, 270):
            wide = 6.0 if rz == 0 else 3.6
            P.steps(s.at(0, 0, 0, rz), 0, -6.5, wide, 45, 0.5, 0.3, "sand_light", mat2="sand")
        if stage == 1:
            P.crane(w.at(6, 6, 2.0, 30), 6.5, 3.5)
            P.lodge(w.at(0, 0, 2.0), -8, 6, 0)
            P.stone_pile(w.at(0, 0, 2.0), -6, -8, rnd, 4, 3, 2, ("sand", "sand_light"))
        if stage == 2:
            P.crane(w.at(5, 5, 11.0, 40), 8.0, 4.0, load="sand_light")
            P.lodge(w.at(0, 0, 11.0), -5, 4, 0)
            P.scaffold_box(w, 0, 0, 24.2, 24.2, 1, z=9.0, sides="rbl")
            for x, y in ((-13, -13), (13, 13)):
                P.stone_pile(w.at(0, 0, 9.0), x, y, rnd, 2, 2, 2, ("sand", "sand_light"))
            w.solid([(18, -19.6, 0), (18, 3, 4.5), (18, 14, 4.5), (18, 14, 0)], (1.8, 0, 0), "soil_dark")   # The ramp the blocks go up.
        if not fin:
            P.finish(w, P.model_id("wonder_ziggurat", stage))
            return

        for sx in (-1, 1):                                                     # The balustrades end in serpent heads.
            w.solid([(sx * 3.0, -20, 0.0), (sx * 3.0, -6.5, 22.5), (sx * 3.0, -6.5, 23.4), (sx * 3.0, -20, 1.1)], (sx * 0.9, 0, 0), "sand_dark")
            g = w.at(sx * 3.45, -19.6, 0)
            g.box((0, 0.2, 0.9), (1.5, 1.8, 1.8), "jade")
            g.frustum(0, -1.2, 1.3, 1.4, 0.5, 0.9, 0.8, 1.5, "jade", oy=-0.3)
            for ex in (-1, 1):
                g.sphere((ex * 0.55, -0.5, 1.5), 0.22, "gold", 6, 4)
                g.cyl((ex * 0.3, -1.9, 0.5), (ex * 0.3, -1.95, 0.05), 0.12, 0.0, "bone", 4)
            P.brazier(w, sx * 6.5, -19.2, 0, 2.0, "bronze_dark")
            P.banner(w.at(sx * 7.5, -(30 - 1.6) / 2 - 0.1, 8.7), 2.2, 3.6, "cloth_red" if sx < 0 else "cloth_green")
            P.banner(w.at(sx * 6.5, -(24 - 1.6) / 2 - 0.1, 13.2), 2.0, 3.4, "cloth_green" if sx < 0 else "cloth_red")
        top = 22.5
        w.box((0, 0.6, top + 0.4), (9.4, 8.2, 0.8), "sand_light")
        P.steps(w, 0, -3.5, 4.0, 3, 0.27, 0.4, "sand", z0=top)
        w.box((0, 1.4, top + 3.0), (7.6, 5.4, 4.4), "sand")
        w.box((0, -1.35, top + 2.5), (2.2, 0.2, 3.4), "cave")
        for x in (-3.3, -1.7, 1.7, 3.3):
            P.column(w, x, -2.4, top + 0.8, 4.2, 0.36, "jade", "gold")
        w.box((0, 0.6, top + 5.3), (9.0, 7.6, 0.6), "sand_light")
        w.box((0, 0.6, top + 5.75), (9.2, 7.8, 0.3), "turquoise")
        w.frustum(0, 1.4, 7.0, 3.4, top + 5.9, 5.0, 1.6, top + 10.0, "sand_dark")   # The roof comb.
        w.cyl((0, 0.5, top + 8.2), (0, -0.5, top + 8.2), 1.7, 1.7, "gold", 16)
        for i in range(12):
            a = TAU * i / 12
            w.cyl((math.cos(a) * 1.7, -0.35, top + 8.2 + math.sin(a) * 1.7), (math.cos(a) * 2.5, -0.35, top + 8.2 + math.sin(a) * 2.5), 0.22, 0.0, "gold_light", 4)
        for cx in (-1, 1):
            for cy in (-1, 1):
                P.brazier(w, cx * 5.0, cy * 5.0, top, 1.6, "bronze_dark")
        for i in (1, 2, 3):
            for cx in (-1, 1):
                for cy in (-1, 1):
                    k = sides[i] / 2 + 0.9
                    w.box((cx * k, cy * k, 4.5 * i + 0.6), (1.2, 1.2, 1.2), "sand_dark")
                    w.frustum(cx * k, cy * k, 1.0, 1.0, 4.5 * i + 1.2, 0.0, 0.0, 4.5 * i + 2.4, "jade")
        P.finish(w, "wonder_ziggurat", [], [("idle", 4.0, lambda t: ({}, P.flame_moves(t, 0.14, 6)))])
    return build


# ---------------------------------------------------------------- world tree


def _trunk_r(z):
    pts = [(0, 5.0), (6, 4.0), (13, 3.4), (20, 2.9), (26, 2.3)]
    for (z0, r0), (z1, r1) in zip(pts, pts[1:]):
        if z <= z1:
            return r0 + (r1 - r0) * (z - z0) / (z1 - z0)
    return 2.3


def _tree(w, rnd, lights=None):
    for i in range(9):
        a = TAU * i / 9 + rnd.uniform(-0.2, 0.2)
        length = rnd.uniform(7.5, 11.0)
        w.cyl((math.cos(a) * 2.6, math.sin(a) * 2.6, 3.8), (math.cos(a) * length, math.sin(a) * length, -0.4), 1.6, 0.5, "trunk" if i % 2 else "trunk_dark", 6)
    pts = [(0, 0, -0.2, 5.0), (0.3, 0.2, 6, 4.0), (-0.2, 0.5, 13, 3.4), (0.4, -0.2, 20, 2.9), (0, 0, 26, 2.3)]
    for (x0, y0, z0, r0), (x1, y1, z1, r1) in zip(pts, pts[1:]):
        w.cyl((x0, y0, z0), (x1, y1, z1), r0, r1, "trunk", 9)
    for i in range(7):                                                         # Ridges of bark.
        a = TAU * i / 7 + 0.3
        w.cyl((math.cos(a) * 4.5, math.sin(a) * 4.5, 0), (math.cos(a + 0.5) * 2.4, math.sin(a + 0.5) * 2.4, 24), 0.7, 0.4, "trunk_dark" if i % 2 else "trunk_light", 5)
    tips = []
    for i in range(8):
        a = TAU * i / 8 + rnd.uniform(-0.15, 0.15)
        z0 = rnd.uniform(18.0, 25.0)
        reach, z1 = rnd.uniform(8.5, 12.0), rnd.uniform(27.0, 33.0)
        mid = (math.cos(a) * reach * 0.55, math.sin(a) * reach * 0.55, (z0 + z1) / 2 + 1.5)
        tip = (math.cos(a) * reach, math.sin(a) * reach, z1)
        w.cyl((math.cos(a) * 1.5, math.sin(a) * 1.5, z0), mid, 1.5, 1.0, "trunk", 6)
        w.cyl(mid, tip, 1.0, 0.5, "trunk_dark", 6)
        tips.append(tip)
    w.cyl((0, 0, 25.5), (0.5, 0.3, 33), 2.3, 1.2, "trunk", 7)
    leaves = ("leaf", "leaf_dark", "leaf_light")
    for i, (x, y, z) in enumerate(tips):
        w.sphere((x, y, z + 1.5), rnd.uniform(4.6, 5.8), leaves[i % 3], 8, 5, (1.0, 1.0, 0.72))
        w.sphere((x * 0.6 + rnd.uniform(-1, 1), y * 0.6 + rnd.uniform(-1, 1), z + 4.5), rnd.uniform(4.0, 5.0), leaves[(i + 1) % 3], 8, 5, (1.0, 1.0, 0.72))
        for k in range(2):                                                     # Hanging vines.
            vx, vy = x + rnd.uniform(-2.5, 2.5), y + rnd.uniform(-2.5, 2.5)
            w.cyl((vx, vy, z - 1.0), (vx, vy, z - rnd.uniform(5.0, 9.0)), 0.09, 0.03, "leaf_light", 4)
        if lights:
            lz = z - rnd.uniform(3.5, 6.5)
            w.bone(lights[i % 2]).sphere((x * 0.85, y * 0.85, lz), 0.38, "glow_blue" if i % 2 else "lantern", 6, 4)
    w.sphere((0.5, 0.3, 37.5), 6.6, "leaf_light", 9, 6, (1.0, 1.0, 0.78))
    w.sphere((-1.5, 2.0, 34.0), 6.0, "leaf", 9, 6, (1.0, 1.0, 0.72))
    w.sphere((2.5, -2.0, 33.5), 5.6, "leaf_dark", 9, 6, (1.0, 1.0, 0.72))


def _deck(w, z, inner, outer, n=12, posts=True, part=1.0):
    count = max(1, round(n * part))
    for i in range(count):
        a0, a1 = TAU * i / n, TAU * (i + 1) / n
        w.solid([(math.cos(a0) * inner, math.sin(a0) * inner, z), (math.cos(a0) * outer, math.sin(a0) * outer, z),
                 (math.cos(a1) * outer, math.sin(a1) * outer, z), (math.cos(a1) * inner, math.sin(a1) * inner, z)], (0, 0, 0.3), "plank" if i % 2 else "plank_light")
        w.cyl((math.cos(a0) * inner, math.sin(a0) * inner, z - 2.2), (math.cos(a0) * (outer - 0.3), math.sin(a0) * (outer - 0.3), z), 0.16, 0.14, "trunk_dark", 5)
        if posts:
            w.cyl((math.cos(a0) * (outer - 0.15), math.sin(a0) * (outer - 0.15), z + 0.3), (math.cos(a0) * (outer - 0.15), math.sin(a0) * (outer - 0.15), z + 1.4), 0.08, 0.07, "marble", 5)
            w.cyl((math.cos(a0) * (outer - 0.15), math.sin(a0) * (outer - 0.15), z + 1.3), (math.cos(a1) * (outer - 0.15), math.sin(a1) * (outer - 0.15), z + 1.3), 0.06, 0.06, "marble", 4)


def world_tree(stage):
    """A giant tree sung into growing, with decks, a stair and lights. Footprint 34 x 34 m, 44 m high."""
    def build():
        w = P.W()
        rnd = random.Random(32)
        fin = stage == 3
        w.cyl((0, 0, 0), (0, 0, 0.1), 16.8, 16.8, "grass", 16)
        w.cyl((0, 0, 0.1), (0, 0, 0.16), 11.0, 11.0, "grass_dark", 14)
        for i in range(8):                                                     # The ring of singing stones.
            a = TAU * (i + 0.5) / 8
            g = w.at(math.cos(a) * 14.6, math.sin(a) * 14.6, 0, math.degrees(a) + 90)
            g.frustum(0, 0, 1.4, 0.8, 0, 0.9, 0.5, 3.2 + 0.5 * (i % 2), "stone_light")
            g.box((0, -0.42, 2.0), (0.4, 0.06, 0.9), "glow_blue")
        if stage == 1:
            _tree(w.scaled(0.34), rnd)
            P.stakes(w, 14, 14)
            P.timber_pile(w, -8, -7.5, 20)
            P.lodge(w, 8, -7, 0)
            for i in range(6):
                a = TAU * i / 6
                w.cyl((math.cos(a) * 4.2, math.sin(a) * 4.2, 0), (math.cos(a) * 1.2, math.sin(a) * 1.2, 5.5), 0.1, 0.08, "pole", 5)   # Props for the young tree.
            P.finish(w, "wonder_world_tree_stage1")
            return
        if stage == 2:
            k = 0.66
            _tree(w.scaled(k), rnd)
            _deck(w, 8.0, _trunk_r(8 / k) * k, _trunk_r(8 / k) * k + 3.0, part=0.6, posts=False)
            P.scaffold_ring(w, 0, 0, 4.6, 3, n=8)
            P.timber_pile(w, -9, -8, 20)
            P.timber_pile(w, 10, 6, 100)
            P.lodge(w, 9, -8, 0)
            P.crane(w.at(-8, 5, 0, -60), 9.0, 4.0, load="plank")
            P.finish(w, "wonder_world_tree_stage2")
            return

        _tree(w, rnd, lights=("lights_a", "lights_b"))
        for z, extra in ((12.0, 3.4), (19.0, 2.8)):
            _deck(w, z, _trunk_r(z) - 0.2, _trunk_r(z) + extra)
        n = 54                                                                 # The stair that winds up the trunk.
        for i in range(n):
            u = i / n
            z = 0.3 + 11.7 * u
            a = -math.pi / 2 + 0.5 + TAU * 1.4 * u
            r = _trunk_r(z) + 0.9
            w.box((math.cos(a) * r, math.sin(a) * r, z), (2.0, 1.0, 0.22), "plank_light" if i % 2 else "plank", rz=math.degrees(a))
            if i % 3 == 0:
                w.cyl((math.cos(a) * (r + 0.9), math.sin(a) * (r + 0.9), z), (math.cos(a) * (r + 0.9), math.sin(a) * (r + 0.9), z + 1.2), 0.06, 0.05, "marble", 4)
        P.door(w.at(0, -4.75, 0.1), 2.4, 3.8, "door", "marble")
        for sx in (-1, 1):
            P.column(w, sx * 2.4, -6.2, 0.1, 5.0, 0.3, "marble", "gold")
            P.lamp(w, sx * 2.4, -6.2, 5.1, 2.0, "gold", "glow_blue")
        w.solid([(-2.9, -6.2, 5.0), (2.9, -6.2, 5.0), (0, -6.2, 6.6)], (0, 0.5, 0), "marble")
        for i in range(3):                                                     # Pavilions on the first deck.
            a = TAU * i / 3 + 0.9
            r = _trunk_r(12) + 2.0
            x, y = math.cos(a) * r, math.sin(a) * r
            for cx in (-1, 1):
                for cy in (-1, 1):
                    w.cyl((x + cx * 0.8, y + cy * 0.8, 12.3), (x + cx * 0.8, y + cy * 0.8, 14.6), 0.09, 0.08, "marble", 5)
            P.dome(w, x, y, 14.6, 1.5, "leaf_gold", "gold", 8, 3, 1.1)
            P.lamp(w, x, y, 13.4, 1.4, "gold", "lantern")
        for i in range(10):
            a = TAU * i / 10
            z = 12.3 if i % 2 else 19.3
            r = _trunk_r(z) + (3.2 if i % 2 else 2.6)
            P.lamp(w, math.cos(a) * r, math.sin(a) * r, z + 1.1, 1.3, "gold", "lantern" if i % 3 else "glow_blue")

        def idle(t):
            b = 0.35 * math.sin(TAU * t)
            return {}, {"lights_a": (0, 0, b), "lights_b": (0, 0, -b)}

        P.finish(w, "wonder_world_tree", [("lights_a", (0, 0, 22), (0, 0, 23), None), ("lights_b", (0, 0, 22), (0, 0, 23), None)], [("idle", 6.0, idle)])
    return build


# ---------------------------------------------------------------- dwarf gate


def dwarf_gate(stage):
    """A gate carved in a cliff between two stone dwarves of 15 m. Footprint 40 x 20 m, 31 m high."""
    def build():
        w = P.W()
        rnd = random.Random(33)
        fin = stage == 3
        P.yard(w, stage, rnd, 40, 20, piles=[(-15, -7.5, 1.0), (15, -7.5, 1.0)], timbers=[(-15, -4.5, 0)], lodges=[(13, -4.5, 0)], outline=(30, 7, 0, -6))
        w.frustum(0, 4, 40, 12, 0, 33, 8, 24, "granite")                       # The cliff.
        for sx in (-1, 1):
            w.frustum(sx * 15.5, -1.0, 9, 8, 0, 5, 4, 15, "granite_dark", ox=sx * 1.0, oy=1.5)
        for i in range(9):
            x = -15.5 + 3.9 * i + rnd.uniform(-0.8, 0.8)
            h = rnd.uniform(3.0, 7.5)
            w.frustum(x, 4.5 + rnd.uniform(-1, 1), rnd.uniform(4.5, 7.0), rnd.uniform(4.5, 7.0), 22.5, rnd.uniform(0.5, 2.0), rnd.uniform(0.5, 2.0), 24 + h,
                      rnd.choice(("granite", "granite_dark", "granite_light")), ox=rnd.uniform(-1, 1), oy=rnd.uniform(-1, 1))
        for i in range(10):
            P._shapes.rock(w.mb, rnd.uniform(-19, 19) if i % 2 else rnd.choice((-1, 1)) * rnd.uniform(11, 19), rnd.uniform(-5.5, -2.5), 0.3, rnd.uniform(0.8, 1.6), rnd, "granite_dark")
        for i in range(10):                                                    # Crags and ledges that break up the face.
            sx = -1 if i % 2 else 1
            x = sx * rnd.uniform(14.0, 18.0)
            w.frustum(x, -1.6 + rnd.uniform(-0.8, 0.6), rnd.uniform(3.0, 4.0), rnd.uniform(2.5, 4.0), 0, rnd.uniform(1.2, 2.6), rnd.uniform(1.0, 2.0), rnd.uniform(7.0, 21.0),
                      rnd.choice(("granite", "granite_dark", "granite_light")), ox=rnd.uniform(-0.8, 0.8), oy=rnd.uniform(0.8, 1.8))
        for z in (6.5, 12.5, 18.5):
            w.box((0, 4, z), (40.3 - 7 * z / 24, 12.3 - 4 * z / 24, 0.45), "granite_dark")
        for i in range(4):
            x = -13.5 + 9.0 * i + rnd.uniform(-1, 1)
            w.sphere((x, 4.5, 27.5 + rnd.uniform(0, 2.5)), rnd.uniform(1.6, 2.4), "marble", 7, 4, (1.3, 1.2, 0.45))   # Snow on the heights.
        if stage == 1:
            w.box((0, -2.05, 9.0), (18, 0.3, 18), "granite_light")              # The face dressed smooth, the gate drawn on it.
            w.box((0, -2.25, 7.0), (8, 0.2, 14), "granite_dark")
            P.scaffold(w, (-9.5, -2.4), (9.5, -2.4), 7)
            P.crane(w.at(-4, -6.5, 0, 180), 7.0, 3.0, load="granite_light")
            for x in (-6, 0, 7):
                P.heap(w, x, -7.5, 1.6, "granite_dark")
            P.finish(w, "wonder_dwarf_gate_stage1")
            return

        w.box((0, -4.0, 0.9), (28, 5.0, 1.8), "granite_dark")                   # The terrace and its stairs.
        P.steps(w, 0, -6.5, 12, 6, 0.3, 0.5, "granite_light", mat2="granite")
        w.box((0, -2.1, 11.5), (22, 0.5, 21), "granite_light")
        w.box((0, -2.4, 9.0), (9.0, 0.5, 15.0), "cave")
        for sx in (-1, 1):
            w.box((sx * 9, -4.2, 2.8), (5.2, 4.0, 2.0), "granite")
        if stage == 2:
            for sx in (-1, 1):                                                 # The statues, still blocks.
                w.box((sx * 9, -4.2, 7.3), (4.6, 3.4, 7.0), "granite_light")
                w.box((sx * 9, -4.2, 12.3), (3.4, 2.8, 3.0), "granite")
                P.scaffold_box(w, sx * 9, -4.2, 5.4, 4.2, 5, z=1.8, sides="fl" if sx < 0 else "fr")
            P.scaffold(w, (-4.6, -2.8), (4.6, -2.8), 7, 1.8)
            P.crane(w.at(0, -7.0, 0, 180), 9.0, 3.0, load="granite_light")
            P.finish(w, "wonder_dwarf_gate_stage2")
            return

        bones = []
        for sx in (-1, 1):
            g = w.at(sx * 9, -4.2, 3.8)
            hands = P.statue(g, 15.0, "granite_light", ("front", "front"), "granite", stocky=1.35, beard=True, detail=True, cape="granite")
            hx, hy, hz = 0.0, hands["hand_r"][1], hands["hand_r"][2]
            g.cyl((hx, hy, 0.6), (hx, hy, hz + 0.8), 0.28, 0.28, "granite", 6)   # A war hammer, head down.
            g.box((hx, hy, 1.0), (3.4, 1.5, 1.8), "granite")
            g.box((hx, hy, 1.0), (3.5, 1.0, 0.5), "gold")
            g.cyl((0, 0, 14.2), (0, 0, 15.7), 1.3, 0.4, "gold_dark", 8)          # The helmet and its horns.
            g.cyl((0, 0, 14.0), (0, 0, 14.4), 1.36, 1.36, "gold", 8)
            for hs in (-1, 1):
                g.cyl((hs * 1.1, 0, 14.6), (hs * 2.1, 0, 15.2), 0.4, 0.28, "bone", 6)
                g.cyl((hs * 2.1, 0, 15.2), (hs * 2.3, 0, 16.6), 0.28, 0.0, "bone", 6)
            g.cyl((0, -1.4, 13.2), (0, -1.9, 9.6), 1.0, 0.2, "granite", 6)       # A beard to the belt.
            w.cyl((sx * 5.6, -2.5, 1.8), (sx * 5.6, -2.5, 21.0), 0.9, 0.8, "granite", 6)
            w.cyl((sx * 5.6, -2.5, 19.6), (sx * 5.6, -2.5, 20.4), 1.1, 1.1, "gold", 6)
            w.cyl((sx * 5.6, -2.5, 2.2), (sx * 5.6, -2.5, 3.0), 1.1, 1.1, "gold", 6)
            w.box((sx * 7.6, -8.6, 1.0), (2.0, 2.0, 2.0), "granite")
            P.brazier(w, sx * 7.6, -8.6, 2.0, 2.0, "bronze_dark")
            name = "door_l" if sx < 0 else "door_r"
            d = w.bone(name)
            d.box((sx * 2.1, -2.55, 8.8), (4.1, 0.4, 14.0), "bronze")
            for z in (4.0, 8.8, 13.6):
                d.box((sx * 2.1, -2.8, z), (4.1, 0.14, 0.7), "gold_dark")
            d.box((sx * 0.5, -2.85, 8.0), (0.4, 0.2, 1.6), "gold")
            bones.append((name, (sx * 4.2, -2.55, 1.8), (sx * 4.2, -2.55, 15.8), None))
        w.box((0, -2.5, 16.6), (11.5, 0.9, 1.6), "granite")                     # The lintel and its runes.
        for i in range(9):
            w.box((-4.4 + 1.1 * i, -3.0, 16.6), (0.5, 0.12, 0.9 if i % 2 else 0.6), "gold")
        w.solid([(-7, -2.4, 21.0), (7, -2.4, 21.0), (0, -2.4, 25.0)], (0, -0.6, 0), "granite_light")
        w.box((0, -3.1, 22.2), (2.4, 0.3, 1.0), "gold")                         # The hammer and anvil of the clans.
        w.box((0, -3.1, 23.2), (0.4, 0.3, 1.4), "gold")
        w.box((0, -2.45, 21.0), (15, 0.8, 0.7), "granite")

        def swing(opening):
            def pose(t):
                a = 78.0 * (kit.smooth(t) if opening else 1 - kit.smooth(t))
                return {"door_l": [(kit.Z, -a)], "door_r": [(kit.Z, a)]}, {}
            return pose

        P.finish(w, "wonder_dwarf_gate", bones, [("idle", 4.0, lambda t: ({}, P.flame_moves(t, 0.16, 6))),
                                                 ("open", 4.0, swing(True), False), ("close", 4.0, swing(False), False)])
    return build


# ------------------------------------------------------------ obsidian spire


def _crystal(w, x, y, z, s, mat="crystal", mat2="crystal_glow", seg=5):
    w.cyl((x, y, z), (x, y, z + 1.4 * s), 0.0, 0.5 * s, mat, seg)
    w.cyl((x, y, z + 1.4 * s), (x, y, z + 2.2 * s), 0.5 * s, 0.0, mat2, seg)


def obsidian_spire(stage):
    """A twisted needle of black glass with crystals that float around it. Footprint 20 x 20 m, 58 m high."""
    def build():
        w = P.W()
        rnd = random.Random(34)
        s = P.staged(w, stage, 3.2, 21.0, (0.0, 0.0), salt=2.0)
        fin = stage == 3
        P.yard(w, stage, rnd, 20, 20, piles=[(-8.4, -8.6, 0.8), (8.4, -8.6, 0.8)], outline=(19.6, 19.6))
        w.cyl((0, 0, 0), (0, 0, 1.0), 9.6, 9.2, "obsidian_light", 8, spin=22.5)
        w.cyl((0, 0, 1.0), (0, 0, 2.0), 7.2, 6.8, "obsidian", 8, spin=22.5)
        P.steps(w, 0, -6.2, 4.0, 8, 0.25, 0.4, "obsidian_edge")
        sizes = [8.0, 7.4, 6.8, 6.2, 5.6, 5.0, 4.4, 3.8, 3.2, 2.7, 2.2]
        for i in range(10):
            z = 2.0 + 4.2 * i
            s.frustum(0, 0, sizes[i], sizes[i], z, sizes[i + 1] + 0.3, sizes[i + 1] + 0.3, z + 4.2, "obsidian" if i % 2 == 0 else "obsidian_light", rz=11 * i)
            s.box((0, 0, z + 4.1), (sizes[i + 1] + 0.7, sizes[i + 1] + 0.7, 0.25), "obsidian_edge", rz=11 * i + 5)
        for cx in (-1, 1):
            for cy in (-1, 1):
                s.frustum(cx * 6.0, cy * 6.0, 2.4, 2.4, 1.0, 0.0, 0.0, 17.0, "obsidian_light", rz=45)
        if stage == 2:
            top = s.cap(0, 0)
            P.scaffold_box(w, 0, 0, 8.4, 8.4, 6, z=2.0)
            P.crane(w.at(0, 0, top, 25), 8.0, 4.0, load="obsidian_light")
        if stage == 1:
            P.crane(w.at(0, 0, 3.2, 25), 6.0, 3.5, load="obsidian_light")
        if not fin:
            P.finish(w, P.model_id("wonder_obsidian_spire", stage))
            return

        w.cyl((0, 0, 44.0), (0, 0, 52.0), 1.6, 0.0, "obsidian", 4, spin=20)
        for i in range(10):                                                    # Glowing seams.
            z = 2.0 + 4.2 * i
            for rz in (0, 90, 180, 270):
                f = w.at(0, 0, 0, rz + 11 * i)
                half = (sizes[i] + sizes[i + 1] + 0.3) / 4
                f.box((0, -half - 0.02, z + 2.1), (0.3 if i % 2 else 0.5, 0.14, 2.6), "crystal_glow" if i % 2 else "crystal")
        P.door(w.at(0, -4.0, 2.0), 2.0, 3.6, "crystal", "obsidian_edge")
        for i in (2, 5, 8):                                                    # Crowns of thorns around the needle.
            z = 2.0 + 4.2 * i
            r = sizes[i] * 0.78
            w.cyl((0, 0, z - 0.3), (0, 0, z + 0.2), r + 0.5, r + 0.9, "obsidian_edge", 8, spin=11 * i)
            for k in range(8):
                a = TAU * k / 8 + math.radians(11 * i)
                w.cyl((math.cos(a) * (r + 0.6), math.sin(a) * (r + 0.6), z + 0.1), (math.cos(a) * (r + 2.0), math.sin(a) * (r + 2.0), z + 2.6), 0.36, 0.0, "obsidian_light", 4)
                w.sphere((math.cos(a) * (r + 0.75), math.sin(a) * (r + 0.75), z + 0.35), 0.22, "crystal_glow", 5, 3)
        for rz in (90, 180, 270):
            f = w.at(0, 0, 0, rz)
            f.frustum(0, -8.0, 1.6, 1.6, 1.0, 0.0, 0.0, 9.5, "obsidian", rz=45)
            f.solid([(-0.2, -7.6, 1.0), (-0.2, -4.2, 1.0), (-0.2, -3.6, 9.0), (-0.2, -7.4, 4.0)], (0.4, 0, 0), "obsidian_light")
            f.box((0, -7.9, 4.4), (0.5, 0.3, 1.6), "crystal_glow")
        core = w.bone("core")
        _crystal(core, 0, 0, 53.0, 2.2, seg=6)
        orbit = w.bone("orbit")
        for i in range(6):
            a = TAU * i / 6
            _crystal(orbit, math.cos(a) * 5.8, math.sin(a) * 5.8, 37.5 + 1.5 * (i % 2), 1.5)
        orbit2 = w.bone("orbit2")
        for i in range(8):
            a = TAU * i / 8 + 0.6
            orbit2.box((math.cos(a) * 7.6, math.sin(a) * 7.6, 24.0 + 2.2 * (i % 3)), (1.0, 0.6, 2.6), "obsidian_edge", rz=math.degrees(a) + 30)
            orbit2.box((math.cos(a) * 7.6, math.sin(a) * 7.6, 24.0 + 2.2 * (i % 3)), (0.6, 0.7, 1.4), "crystal_glow", rz=math.degrees(a) + 30)
        bob = w.bone("bob")
        for cx in (-1, 1):
            for cy in (-1, 1):
                _crystal(bob, cx * 6.0, cy * 6.0, 17.8, 1.0)
                w.cyl((cx * 5.4, cy * 5.4, 9.0), (cx * 2.6, cy * 2.6, 12.5), 0.3, 0.3, "obsidian_edge", 4)
        for sx in (-1, 1):
            P.brazier(w, sx * 3.2, -7.6, 1.0, 1.5, "obsidian_edge", mats=("flame_violet", "flame_violet_core"))

        def idle(t):
            moves = P.flame_moves(t, 0.12, 8)
            moves["bob"] = (0, 0, 0.4 * math.sin(TAU * 2 * t))
            moves["core"] = (0, 0, 0.5 * math.sin(TAU * t))
            return {"orbit": [(kit.Z, 360.0 * t)], "orbit2": [(kit.Z, -360.0 * t)], "core": [(kit.Z, -720.0 * t)]}, moves

        bones = [("core", (0, 0, 53), (0, 0, 55), None), ("orbit", (0, 0, 38), (0, 0, 39), None), ("orbit2", (0, 0, 26), (0, 0, 27), None), ("bob", (0, 0, 17), (0, 0, 18), None)]
        P.finish(w, "wonder_obsidian_spire", bones, [("idle", 12.0, idle)])
    return build


# ---------------------------------------------------------------- sun temple


def _cat(w, h, mat, trim="gold"):
    """A seated cat of height h at the local origin, facing -Y."""
    u = h
    w.frustum(0, 0.08 * u, 0.36 * u, 0.5 * u, 0, 0.26 * u, 0.26 * u, 0.55 * u, mat, oy=-0.1 * u)
    for sx in (-1, 1):
        w.cyl((sx * 0.1 * u, -0.2 * u, 0), (sx * 0.09 * u, -0.14 * u, 0.5 * u), 0.055 * u, 0.06 * u, mat, 6)
        w.box((sx * 0.1 * u, -0.26 * u, 0.03 * u), (0.1 * u, 0.14 * u, 0.06 * u), mat)
        w.cyl((sx * 0.1 * u, -0.06 * u, 0.86 * u), (sx * 0.13 * u, -0.05 * u, 1.0 * u), 0.06 * u, 0.0, mat, 4)
    w.cyl((0, -0.06 * u, 0.5 * u), (0, -0.08 * u, 0.66 * u), 0.12 * u, 0.1 * u, mat, 7)
    w.cyl((0, -0.07 * u, 0.56 * u), (0, -0.075 * u, 0.62 * u), 0.125 * u, 0.12 * u, trim, 7)
    w.sphere((0, -0.1 * u, 0.76 * u), 0.15 * u, mat, 8, 6, (1.0, 0.95, 0.9))
    w.box((0, -0.24 * u, 0.73 * u), (0.1 * u, 0.06 * u, 0.07 * u), mat)
    w.cyl((0.12 * u, 0.3 * u, 0.04 * u), (-0.22 * u, -0.1 * u, 0.05 * u), 0.04 * u, 0.03 * u, mat, 5)


def sun_temple(stage):
    """A pylon gate, a court of columns and a turning sun of gold. Footprint 30 x 40 m, 24 m high."""
    def build():
        w = P.W()
        rnd = random.Random(35)
        s = P.staged(w, stage, 1.6, 6.5, (0.4, 2.5), salt=3.0)
        fin = stage == 3
        P.yard(w, stage, rnd, 30, 40, piles=[(-12, -18, 1.0), (12, -18, 1.0)], timbers=[(11, -13, 90)], lodges=[(6, -1, 90)] if stage == 1 else [],
               cranes=[(-2, 0, 180, 11.0), (0, 10, 0, 11.0, 2)], outline=(29.6, 39.6))
        if fin:
            w.box((0, 0, 0.08), (30, 40, 0.16), "sand_light")
        w.box((0, 4.5, 0.2), (26, 30, 0.4), "sand_dark")
        for sx in (-1, 1):
            s.frustum(sx * 7.5, -8, 11.0, 5.0, 0.4, 9.6, 3.4, 16.0, "sand")      # The pylon.
            s.frustum(sx * 5, -17, 1.7, 1.7, 0.9, 1.0, 1.0, 15.0, "sand_light")  # An obelisk.
            w.box((sx * 5, -17, 0.45), (2.6, 2.6, 0.9), "sand_dark")
            P.wall(s, (sx * 12.5, -5.5), (sx * 12.5, 6), 0.4, 7.0, 1.0, "sand")
            for i in range(5):
                P.column(s, sx * 9.6, -4.0 + 2.2 * i, 0.4, 6.0, 0.5, "sand_light", "turquoise")
            w.box((sx * 5, -12.5, 0.6), (2.4, 4.2, 1.2), "sand_dark")
        s.box((0, -8, 12.2), (4.2, 3.4, 3.0), "sand")
        P.block(s, 0, 10, 24, 8, 0.4, 11.0, "sand")
        P.block(s, 0, 16.5, 12, 5, 0.4, 8.0, "sand_dark")
        for x in (-7.5, -2.5, 2.5, 7.5):
            P.column(s, x, 5.2, 0.4, 9.0, 0.7, "sand_light", "turquoise")
        if stage == 2:
            P.scaffold(w, (-13.2, -10.7), (13.2, -10.7), 5)
            P.scaffold(w, (12.2, 6), (12.2, 14), 4, 0.4)
            P.scaffold(w, (-12.2, 14), (-12.2, 6), 4, 0.4)
        if stage == P.RUIN:
            w.box((0, 0, 0.05), (30, 40, 0.1), "sand")
            P.rubble(w, rnd, 28, 38, 50, ("sand", "sand_dark", "sand_light"), moss=False)
            w.at(5, -15, 0).turn("X", 80).frustum(0, 0, 1.2, 1.2, 0, 0.8, 0.8, 7.0, "sand_light")   # The top of an obelisk, fallen.
        if not fin:
            P.finish(w, P.model_id("wonder_sun_temple", stage))
            return

        bones, flags = [], []
        for sx in (-1, 1):
            w.box((sx * 7.5, -8, 16.2), (10.2, 4.0, 0.5), "sand_light")
            w.box((sx * 7.5, -8, 16.6), (10.6, 4.4, 0.4), "turquoise")
            w.box((sx * 7.5, -10.25, 13.6), (8.4, 0.2, 0.8), "turquoise")
            w.box((sx * 7.5, -10.4, 11.9), (8.0, 0.2, 0.5), "gold")
            w.frustum(sx * 5, -17, 1.0, 1.0, 15.0, 0.0, 0.0, 17.0, "gold")
            _cat(w.at(sx * 5, -12.3, 1.2), 4.4, "sand_light")
            for k, x in enumerate((4.2, 9.6)):
                name = "flag%d%d" % (sx > 0, k)
                bones += P.flag(w, name, sx * x, -11.0, 0.0, 19.5 if k == 0 else 17.5, "cloth_red" if k == 0 else "cloth_white", 1.3, "pole", "gold")
                flags.append(name)
            w.box((sx * 12.5, 0.25, 7.2), (1.3, 11.8, 0.4), "sand_light")
            w.box((sx * 9.6, 0.4, 6.6), (1.6, 9.8, 0.5), "sand")
            for i in range(4):
                P.window(w.at(sx * 12.02, 7.5 + 1.7 * i, 6.5, 90 * sx), 0.8, 2.2, "turquoise", "sand_light", pointed=False)
        w.box((0, -9.6, 5.0), (3.6, 0.3, 9.2), "cave")
        w.box((0, -8, 10.3), (5.2, 3.6, 0.8), "sand_light")
        w.cyl((0, -9.5, 13.2), (0, -10.0, 13.2), 1.5, 1.5, "gold", 14)
        w.box((0, 5.2, 9.7), (18, 1.8, 0.6), "sand_light")
        w.box((0, 10, 11.2), (24.6, 8.6, 0.5), "sand_light")
        w.box((0, 10, 11.6), (25, 9, 0.35), "turquoise")
        w.box((0, 5.9, 4.0), (3.0, 0.3, 7.0), "cave")
        w.box((0, 16.5, 8.2), (12.6, 5.6, 0.5), "sand_light")
        w.frustum(0, 10, 4.0, 4.0, 11.8, 2.4, 2.4, 16.5, "sand_light")           # The mast of the sun.
        sun = w.bone("sun")
        sun.cyl((0, 9.65, 19.6), (0, 10.35, 19.6), 3.0, 3.0, "gold", 20)
        sun.cyl((0, 9.5, 19.6), (0, 10.5, 19.6), 1.9, 1.9, "gold_light", 16)
        for i in range(12):
            a = TAU * i / 12
            sun.cyl((math.cos(a) * 3.0, 10, 19.6 + math.sin(a) * 3.0), (math.cos(a) * (4.4 if i % 2 == 0 else 3.8), 10, 19.6 + math.sin(a) * (4.4 if i % 2 == 0 else 3.8)), 0.42, 0.0, "gold_light" if i % 2 else "gold", 4)
        bones.append(("sun", (0, 10, 19.6), (0, 11, 19.6), None))
        for sx in (-1, 1):
            P.brazier(w, sx * 2.6, -11.2, 0.0, 1.6, "bronze")
            P.brazier(w, sx * 3.0, 10, 11.8, 1.3, "bronze")

        def idle(t):
            turns = P.flag_turns(flags, t, 4)
            turns["sun"] = [(kit.Y, 360.0 * t)]
            return turns, P.flame_moves(t, 0.12, 12)

        P.finish(w, "wonder_sun_temple", bones, [("idle", 12.0, idle)])
    return build


# ---------------------------------------------------------------- fox shrine


def _torii(w, span=5.6, h=5.2):
    for sx in (-1, 1):
        w.cyl((sx * span / 2, 0, 0), (sx * span / 2, 0, h), 0.3, 0.26, "lacquer", 8)
        w.cyl((sx * span / 2, 0, 0), (sx * span / 2, 0, 0.5), 0.4, 0.36, "obsidian", 8)
        w.box((sx * (span / 2 + 1.0), 0, h + 0.62), (0.7, 0.62, 0.3), "obsidian", rz=0)
    w.box((0, 0, h + 0.3), (span + 2.2, 0.6, 0.5), "obsidian")
    w.box((0, 0, h - 0.1), (span + 1.8, 0.5, 0.35), "lacquer")
    w.box((0, 0, h - 1.2), (span + 0.9, 0.36, 0.4), "lacquer_dark")
    w.box((0, -0.05, h - 0.62), (0.7, 0.3, 0.8), "gold")


def _fox(w, h, mat="marble", bib="cloth_red"):
    """A seated fox of height h at the local origin, facing -Y."""
    u = h
    w.frustum(0, 0.08 * u, 0.3 * u, 0.44 * u, 0, 0.22 * u, 0.22 * u, 0.56 * u, mat, oy=-0.1 * u)
    for sx in (-1, 1):
        w.cyl((sx * 0.085 * u, -0.17 * u, 0), (sx * 0.075 * u, -0.12 * u, 0.5 * u), 0.045 * u, 0.05 * u, mat, 6)
        w.cyl((sx * 0.085 * u, -0.03 * u, 0.82 * u), (sx * 0.11 * u, -0.02 * u, 1.0 * u), 0.055 * u, 0.0, mat, 4)
    w.sphere((0, -0.08 * u, 0.72 * u), 0.13 * u, mat, 8, 6, (1.0, 1.0, 0.9))
    w.cyl((0, -0.16 * u, 0.7 * u), (0, -0.34 * u, 0.66 * u), 0.075 * u, 0.02 * u, mat, 6)
    w.box((0, -0.14 * u, 0.5 * u), (0.2 * u, 0.04 * u, 0.16 * u), bib)
    w.cyl((0.1 * u, 0.26 * u, 0.1 * u), (0.16 * u, 0.4 * u, 0.5 * u), 0.09 * u, 0.13 * u, mat, 6)
    w.cyl((0.16 * u, 0.4 * u, 0.5 * u), (0.1 * u, 0.36 * u, 0.9 * u), 0.13 * u, 0.0, mat, 6)


def fox_shrine(stage):
    """A stair under seven red gates, a hall and a pagoda of five roofs on a hill. Footprint 24 x 44 m, 29 m high."""
    def build():
        w = P.W()
        rnd = random.Random(36)
        s = P.staged(w, stage, 2.0, 11.5, (0.0, 2.0), salt=4.0)
        fin = stage == 3
        T = 6.0
        P.yard(w, stage, rnd, 24, 44, piles=[(-8, -19.5, 0.9), (8, -19.5, 0.9)], timbers=[(8, -15, 90)], outline=(23.6, 43.6))
        if fin:
            w.box((0, 0, 0.06), (24, 44, 0.12), "grass")
        w.frustum(0, 9, 24, 26, 0, 22.6, 24.6, T, "stone")                     # The hill, walled in stone.
        w.box((0, 9, T + 0.05), (22.2, 24.2, 0.1), "paving" if stage > 1 else "soil")
        for sx in (-1, 1):
            w.solid([(sx * 2.6, -20.5, 0), (sx * 2.6, -4, T), (sx * 2.6, -4, 0)], (sx * 9.2, 0, 0), "grass_dark")
            w.solid([(sx * 2.6, -20.5, 0.1), (sx * 2.6, -4, T + 0.1), (sx * 2.6, -4, 0)], (sx * 0.5, 0, 0), "stone_light")
        P.steps(s, 0, -4, 5.2, 30, 0.2, 0.55, "stone_light", mat2="stone")

        def step_z(y):
            return max(0.0, min(T, (y + 20.5) / 0.55 * 0.2))

        gates = [-19.6 + 2.5 * i for i in range(7)]
        P.block(s, 0, 14.5, 11, 7, T + 1.0, T + 5.2, "plaster")
        s.box((0, 14.5, T + 0.5), (12.6, 8.6, 1.0), "stone_dark")
        for i in range(5):
            a = 4.2 - 0.45 * i
            P.block(s, 7, 2.5, a, a, T + 0.8 + 3.6 * i, T + 3.4 + 3.6 * i, "lacquer" if i % 2 == 0 else "plaster")
        s.box((7, 2.5, T + 0.4), (5.6, 5.6, 0.8), "stone_dark")
        if stage == 1:
            P.crane(w.at(-5, 10, T, 180), 6.5, 3.0)
            P.lodge(w.at(0, 0, T), 5, 16, 180)
            P.stakes(w.at(0, 0, T), 11, 7, 0, 14.5)
        if stage == 2:
            for y in gates[:3]:
                _torii(w.at(0, y, step_z(y)))
            P.scaffold_box(w, 7, 2.5, 4.4, 4.4, 4, z=T)
            P.scaffold_box(w, 0, 14.5, 11.2, 7.2, 2, z=T, sides="frl")
            P.crane(w.at(-5.5, 4, T, 200), 9.0, 3.5, load="plank")
            P.timber_pile(w.at(0, 0, T), -6, 20, 0)
        if not fin:
            P.finish(w, P.model_id("wonder_fox_shrine", stage))
            return

        for i, y in enumerate(gates):
            _torii(w.at(0, y, step_z(y)))
            if i % 2 == 0:
                for sx in (-1, 1):
                    z = step_z(y + 1.2) * 1.0
                    w.cyl((sx * 3.6, y + 1.2, z - 0.5), (sx * 3.6, y + 1.2, z + 1.6), 0.22, 0.18, "stone_light", 6)
                    P.lamp(w, sx * 3.6, y + 1.2, z + 1.6, 1.8, "stone", "lantern")
        for sx in (-1, 1):
            w.box((sx * 3.8, -2.6, T + 0.5), (1.4, 1.8, 1.0), "stone_light")
            _fox(w.at(sx * 3.8, -2.5, T + 1.0), 2.6)
        # The hall.
        for x in (-5.5, -1.9, 1.9, 5.5):
            w.cyl((x, 10.8, T + 1.0), (x, 10.8, T + 5.2), 0.24, 0.22, "lacquer", 6)
        for sx in (-1, 1):
            for y in (11.0, 18.0):
                w.box((sx * 5.5, y, T + 3.1), (0.4, 0.4, 4.2), "lacquer")
        w.box((0, 10.95, T + 2.6), (3.0, 0.2, 3.2), "door_dark")
        w.box((0, 10.8, T + 4.6), (11.6, 0.3, 0.3), "lacquer_dark")
        P.steps(w, 0, 10.2, 5.0, 4, 0.25, 0.35, "stone_light", z0=T)
        w.frustum(0, 14.5, 16.0, 12.0, T + 4.9, 15.0, 11.0, T + 5.3, "obsidian")
        w.frustum(0, 14.5, 15.0, 11.0, T + 5.3, 7.0, 0.0, T + 9.4, "slate_dark")
        w.box((0, 14.5, T + 9.4), (8.0, 0.5, 0.5), "obsidian")
        for sx in (-1, 1):
            w.cyl((sx * 4.0, 14.5, T + 9.5), (sx * 4.4, 14.5, T + 10.6), 0.3, 0.0, "gold", 5)
            for cy in (-1, 1):
                w.cyl((sx * 7.4, 14.5 + cy * 5.4, T + 5.0), (sx * 8.4, 14.5 + cy * 6.2, T + 5.9), 0.3, 0.1, "obsidian", 4)
        w.cyl((-4.5, 10.6, T + 4.2), (4.5, 10.6, T + 4.2), 0.2, 0.2, "rope", 6)   # The sacred rope.
        for x in (-3, -1, 1, 3):
            w.box((x, 10.6, T + 3.7), (0.3, 0.06, 0.7), "cloth_white")
        w.box((0, 9.4, T + 0.5), (1.6, 0.9, 1.0), "plank_dark")
        lant = w.bone("lanterns")
        for x in (-6.5, -3.3, 3.3, 6.5):
            w.cyl((x, 9.4, T + 5.0), (x, 9.4, T + 4.3), 0.02, 0.02, "rope", 4)
            lant.sphere((x, 9.4, T + 3.9), 0.42, "lacquer", 8, 5, (1.0, 1.0, 1.2))
            lant.cyl((x, 9.4, T + 3.25), (x, 9.4, T + 3.5), 0.2, 0.3, "lantern", 6)
        # The pagoda.
        for i in range(5):
            a = 4.2 - 0.45 * i
            z = T + 3.4 + 3.6 * i
            w.frustum(7, 2.5, a + 3.6, a + 3.6, z - 0.2, a + 3.0, a + 3.0, z + 0.1, "obsidian")
            w.frustum(7, 2.5, a + 3.0, a + 3.0, z + 0.1, a - 0.6, a - 0.6, z + 1.1, "slate_dark")
            for cx in (-1, 1):
                for cy in (-1, 1):
                    w.cyl((7 + cx * (a / 2 + 1.5), 2.5 + cy * (a / 2 + 1.5), z - 0.1), (7 + cx * (a / 2 + 2.1), 2.5 + cy * (a / 2 + 2.1), z + 0.5), 0.18, 0.05, "gold", 4)
                w.box((7 + cx * (a / 2 + 0.03), 2.5, z - 1.5), (0.08, 0.8, 1.2), "window")
                w.box((7, 2.5 + cx * (a / 2 + 0.03), z - 1.5), (0.8, 0.08, 1.2), "window")
        zt = T + 3.4 + 3.6 * 4 + 1.1
        w.cyl((7, 2.5, zt), (7, 2.5, zt + 4.6), 0.14, 0.06, "gold", 6)
        for k in range(5):
            w.cyl((7, 2.5, zt + 0.8 + 0.6 * k), (7, 2.5, zt + 0.95 + 0.6 * k), 0.6 - 0.08 * k, 0.6 - 0.08 * k, "gold_dark", 8)
        # A sacred cherry tree.
        w.cyl((-7, 3, T), (-6.6, 3.2, T + 3.6), 0.5, 0.3, "trunk_dark", 6)
        w.cyl((-7, 3, T + 1.2), (-7, 3, T + 1.5), 0.56, 0.56, "rope", 6)
        for dx, dy, dz, r in ((0, 0, 4.6, 2.4), (1.4, 0.8, 3.8, 1.7), (-1.5, -0.6, 3.9, 1.8), (0.2, -1.4, 5.4, 1.6)):
            w.sphere((-6.6 + dx, 3.2 + dy, T + dz), r, "petal" if dz > 4 else "petal_light", 7, 5, (1, 1, 0.75))

        def idle(t):
            return {}, {"lanterns": (0.08 * math.sin(TAU * t), 0, 0.03 * math.sin(TAU * 2 * t))}

        P.finish(w, "wonder_fox_shrine", [("lanterns", (0, 9.4, T + 5.0), (0, 9.4, T + 3.5), None)], [("idle", 4.0, idle)])
    return build


# --------------------------------------------------------------- lily palace


def _pad(w, x, y, r, z=0.16, rz=0.0):
    g = w.at(x, y, 0, rz)
    g.cyl((0, 0, z), (0, 0, z + 0.3), r * 0.96, r, "lily", 14)
    g.cyl((0, 0, z + 0.3), (0, 0, z + 0.36), r * 0.86, r * 0.86, "lily_light", 14)
    g.solid([(0, 0, z + 0.05), (r * 1.02, -r * 0.16, z + 0.05), (r * 1.02, r * 0.16, z + 0.05)], (0, 0, 0.36), "water_deep")
    for i in range(7):
        a = TAU * (i + 1) / 8
        g.cyl((0, 0, z + 0.37), (math.cos(a) * r * 0.84, math.sin(a) * r * 0.84, z + 0.37), 0.06 * r ** 0.5, 0.03, "lily_dark", 4)


def _bud(w, x, y, z, r, mats=("petal", "petal_light")):
    prof = [(0.0, 1.0), (0.25, 1.16), (0.6, 1.1), (1.0, 0.86), (1.4, 0.5), (1.75, 0.0)]
    for i, ((z0, r0), (z1, r1)) in enumerate(zip(prof, prof[1:])):
        w.cyl((x, y, z + z0 * r), (x, y, z + z1 * r), r0 * r, r1 * r, mats[i % 2], 10)


def _frog(w, s, mat="gold"):
    w.sphere((0, 0, 0.5 * s), 0.6 * s, mat, 8, 5, (1.0, 1.15, 0.8))
    w.sphere((0, -0.45 * s, 0.75 * s), 0.42 * s, mat, 8, 5, (1.1, 1.0, 0.75))
    for sx in (-1, 1):
        w.sphere((sx * 0.26 * s, -0.5 * s, 1.08 * s), 0.16 * s, mat, 6, 4)
        w.sphere((sx * 0.6 * s, 0.25 * s, 0.25 * s), 0.34 * s, mat, 6, 4, (0.8, 1.3, 0.75))
        w.cyl((sx * 0.4 * s, -0.5 * s, 0.4 * s), (sx * 0.5 * s, -0.8 * s, 0.0), 0.12 * s, 0.1 * s, mat, 5)


def lily_palace(stage):
    """A palace like a lotus bud on a giant lily pad, in its own pond. Footprint 36 x 36 m, 21 m high."""
    def build():
        w = P.W()
        rnd = random.Random(37)
        s = P.staged(w, stage, 1.6, 8.5, (0.0, 0.0), salt=5.0)
        fin = stage == 3
        w.cyl((0, 0, 0), (0, 0, 0.1), 17.9, 17.9, "grass_dark" if fin else "soil", 18)
        w.cyl((0, 0, 0.1), (0, 0, 0.16), 16.6, 16.6, "water", 18)
        w.cyl((0, 0, 0.16), (0, 0, 0.18), 12.0, 12.0, "water_deep", 16)
        _pad(w, 0, 1.0, 9.2, rz=95)
        pads = [(TAU * (i + 0.5) / 5 + 0.2, 12.4) for i in range(5)]
        for i in range(8):                                                     # The bridge from the shore.
            y = -17.6 + 1.25 * i
            w.box((0, y, 0.55 + 0.5 * math.sin(math.pi * (i + 0.5) / 8)), (3.0, 1.3, 0.2), "plank" if i % 2 else "plank_light")
        for sx in (-1, 1):
            for i in range(5):
                y = -17.2 + 2.3 * i
                w.cyl((sx * 1.5, y, -0.2), (sx * 1.5, y, 1.9 + 0.5 * math.sin(math.pi * (i + 0.2) / 4.4)), 0.11, 0.09, "reed_dark", 5)
        Z = 0.52
        P.drum(s, 0, 1.0, 5.0, Z, 5.2, "plaster", 12)
        for i in range(12):
            a = TAU * (i + 0.5) / 12
            x, y = math.cos(a) * 6.3, 1.0 + math.sin(a) * 6.3
            s.cyl((x, y, Z), (x, y, 5.2), 0.34, 0.3, "reed", 6)
            for k in range(3):
                s.cyl((x, y, Z + 1.0 + 1.4 * k), (x, y, Z + 1.2 + 1.4 * k), 0.38, 0.38, "reed_dark", 6)
        prof = [(5.2, 6.6), (6.4, 6.9), (8.6, 6.2), (11.0, 4.9), (13.4, 3.0), (15.4, 0.0)]
        for i, ((z0, r0), (z1, r1)) in enumerate(zip(prof, prof[1:])):
            s.cyl((0, 1.0, z0), (0, 1.0, z1), r0, r1, "petal" if i % 2 == 0 else "petal_light", 12)
        if stage == 1:
            P.timber_pile(w.at(0, 0, Z), -4.5, -3.5, 30)
            P.lodge(w.at(0, 0, Z), 5.0, -2.5, -30)
            for i in range(10):
                a = TAU * i / 10
                w.cyl((math.cos(a) * 8.6, 1.0 + math.sin(a) * 8.6, 0.2), (math.cos(a) * 8.6, 1.0 + math.sin(a) * 8.6, 2.2), 0.08, 0.06, "pole", 5)
        if stage == 2:
            P.scaffold_ring(w, 0, 1.0, 7.0, 3, n=8, z=Z, a0=-math.pi / 2 + 0.5, a1=-math.pi / 2 + TAU - 0.5)
            P.timber_pile(w.at(0, 0, Z), -5.5, -4.6, 30)
            _pad(w, math.cos(pads[0][0]) * pads[0][1], math.sin(pads[0][0]) * pads[0][1], 3.6, rz=20)
            _pad(w, math.cos(pads[2][0]) * pads[2][1], math.sin(pads[2][0]) * pads[2][1], 3.6, rz=150)
        if not fin:
            P.finish(w, P.model_id("wonder_lily_palace", stage))
            return

        for i in range(8):                                                     # The petals open around the bud.
            f = w.at(0, 1.0, 0, 360.0 * i / 8)
            f.frustum(0, -6.2, 4.4, 0.6, 4.6, 0.0, 0.0, 12.2, "petal_dark", oy=-3.0)
            g = w.at(0, 1.0, 0, 360.0 * (i + 0.5) / 8)
            g.frustum(0, -6.0, 3.6, 0.5, 6.2, 0.0, 0.0, 14.0, "petal", oy=-1.2)
        w.cyl((0, 1.0, 15.2), (0, 1.0, 16.4), 0.5, 0.7, "gold", 8)
        for i in range(8):
            a = TAU * i / 8
            w.cyl((math.cos(a) * 0.5, 1.0 + math.sin(a) * 0.5, 16.2), (math.cos(a) * 1.3, 1.0 + math.sin(a) * 1.3, 17.6), 0.1, 0.05, "gold_light", 4)
            w.sphere((math.cos(a) * 1.3, 1.0 + math.sin(a) * 1.3, 17.7), 0.2, "gold_light", 5, 3)
        jet = w.bone("jet")
        jet.cyl((0, 1.0, 16.4), (0, 1.0, 19.6), 0.3, 0.1, "water_light", 6)
        jet.sphere((0, 1.0, 19.7), 0.5, "water_light", 6, 4, (1.3, 1.3, 0.6))
        P.door(w.at(0, -4.0, Z), 2.6, 3.6, "door", "gold", pointed=False)
        for i in range(12):
            if i in (8, 9):
                continue
            a = TAU * (i + 0.5) / 12 + TAU / 24
            P.window(w.at(math.cos(a) * 5.0, 1.0 + math.sin(a) * 5.0, 1.8, math.degrees(a) + 90), 1.0, 2.0, "glass_green" if i % 2 else "glass_yellow", "gold", pointed=False)
        la, lb = w.bone("lights_a"), w.bone("lights_b")
        for i, (a, d) in enumerate(pads):
            x, y = math.cos(a) * d, math.sin(a) * d
            _pad(w, x, y, 3.6, rz=math.degrees(a) + 140)
            for k in range(4):
                b = TAU * k / 4 + 0.4
                w.cyl((x + math.cos(b) * 1.3, y + math.sin(b) * 1.3, 0.5), (x + math.cos(b) * 1.3, y + math.sin(b) * 1.3, 2.9), 0.14, 0.12, "reed", 5)
            _bud(w, x, y, 2.9, 1.7, ("petal_light", "petal") if i % 2 else ("petal", "petal_dark"))
            w.cyl((x, y, 2.9 + 1.7 * 1.75), (x, y, 2.9 + 1.7 * 1.75 + 0.6), 0.1, 0.0, "gold", 5)
            (la if i % 2 else lb).sphere((x * 0.72, y * 0.72 + 0.3, 2.6 + 0.4 * (i % 3)), 0.28, "glow_blue" if i % 2 else "lantern", 6, 4)
            (lb if i % 2 else la).sphere((x * 1.1, y * 1.1, 3.4), 0.22, "lantern", 6, 4)
            for k in range(3):                                                 # A reed walk between the pads.
                u = (k + 1) / 4
                w.box((x * (1 - 0.42 * u), 1.0 * 0 + y * (1 - 0.42 * u) + 0.4 * u, 0.5), (1.5, 1.5, 0.14), "reed", rz=math.degrees(a))
        for i in range(14):                                                    # Cattails on the bank.
            a = TAU * i / 14 + rnd.uniform(-0.1, 0.1)
            if abs(a - TAU * 0.75) < 0.35:
                continue
            for k in range(4):
                x, y = math.cos(a) * 16.4 + rnd.uniform(-0.9, 0.9), math.sin(a) * 16.4 + rnd.uniform(-0.9, 0.9)
                h = rnd.uniform(2.2, 3.6)
                w.cyl((x, y, 0.1), (x, y, h), 0.06, 0.04, "reed_dark", 4)
                w.cyl((x, y, h - 0.7), (x, y, h - 0.1), 0.13, 0.13, "trunk_dark", 5)
        for sx in (-1, 1):
            w.cyl((sx * 2.6, -8.4, 0.5), (sx * 2.6, -8.4, 1.3), 0.9, 0.8, "stone_light", 8)
            _frog(w.at(sx * 2.6, -8.4, 1.3), 1.4)

        def idle(t):
            b = 0.3 * math.sin(TAU * t)
            return {}, {"jet": (0, 0, 0.25 * math.sin(TAU * 4 * t)), "lights_a": (0, 0, b), "lights_b": (0, 0, -b)}

        bones = [("jet", (0, 1, 16.4), (0, 1, 19.6), None), ("lights_a", (0, 0, 2), (0, 0, 3), None), ("lights_b", (0, 0, 2), (0, 0, 3), None)]
        P.finish(w, "wonder_lily_palace", bones, [("idle", 4.0, idle)])
    return build


# ----------------------------------------------------------------- war arena


def war_arena(stage):
    """An oval pit of stone and logs under the skull of a great beast. Footprint 36 x 30 m, 17 m high."""
    def build():
        w = P.W()
        rnd = random.Random(38)
        s = P.staged(w, stage, 1.4, 4.0, (0.4, 1.8), salt=6.0, cell=2.0)
        fin = stage == 3
        P.yard(w, stage, rnd, 36, 30, lodges=[(4, 3, 200)] if stage == 1 else [], cranes=[(-3, 0, 100, 9.0)], piles=[(3, -4, 1.0)], timbers=[(0, 5, 10)])
        A, B, N = 17.0, 14.0, 28
        if fin:
            w.box((0, 0, 0.05), (36, 30, 0.1), "soil")
            w.prism([(math.cos(TAU * i / 20) * (A - 5.6), math.sin(TAU * i / 20) * (B - 5.6)) for i in range(20)], 0.1, 0.25, "sandbox")
        for i in range(N):
            a = TAU * (i + 0.5) / N
            if abs(a - TAU * 0.75) < 0.2:
                continue                                                       # The gate.
            x, y = math.cos(a) * A, math.sin(a) * B
            nx, ny = math.cos(a) * B, math.sin(a) * A                           # The outward normal of the oval.
            deg = math.degrees(math.atan2(ny, nx))
            length = TAU * math.hypot(A * math.sin(a), B * math.cos(a)) / N * 1.12
            g = s.at(x, y, 0, deg)
            throne = abs(a - TAU * 0.25) < 0.4
            g.box((-0.7, 0, 3.6 + (1.0 if throne else 0)), (1.4, length, 7.2 + (2.0 if throne else 0)), "stone_dark" if i % 2 else "granite")
            g.box((-2.0, 0, 2.5), (1.3, length * 0.94, 5.0), "stone")
            g.box((-3.3, 0, 1.8), (1.3, length * 0.9, 3.6), "stone_light")
            g.box((-4.6, 0, 1.1), (1.3, length * 0.86, 2.2), "stone")
            if fin:
                f = w.at(x, y, 0, deg)
                top = 7.2 + (2.0 if throne else 0)
                for k in (-1, 1):
                    f.cyl((-0.6, k * length * 0.25, top - 0.4), (1.1, k * length * 0.25, top + 2.0), 0.2, 0.0, "pole_dark", 5)
                    f.cyl((0.1, k * length * 0.3, 0), (0.1, k * length * 0.3, top - 0.6), 0.26, 0.22, "bark", 6)
                f.box((0.12, 0, top * 0.55), (0.2, length, 0.5), "iron")
        if stage == 2:
            P.scaffold(w, (-9.5, -15.2), (-3.5, -15.9), 3)
            P.scaffold(w, (3.5, -15.9), (9.5, -15.2), 3)
        if not fin:
            P.finish(w, P.model_id("wonder_war_arena", stage))
            return

        bones, flags = [], []
        for sx in (-1, 1):                                                     # The gate under the skull.
            w.cyl((sx * 3.4, -13.9, 0), (sx * 3.4, -13.9, 9.5), 1.2, 1.0, "pole_dark", 8)
            for z in (2.0, 5.0, 8.0):
                w.cyl((sx * 3.4, -13.9, z), (sx * 3.4, -13.9, z + 0.4), 1.25, 1.25, "iron", 8)
            P.brazier(w, sx * 5.6, -15.2, 0, 2.0, "iron")
        w.cyl((-5.0, -13.9, 9.2), (5.0, -13.9, 9.2), 0.8, 0.8, "bark", 7)
        g = w.at(0, -14.2, 10.0)
        g.sphere((0, 0.8, 2.4), 2.6, "bone", 9, 6, (1.15, 1.25, 0.95))
        g.frustum(0, -1.6, 3.4, 3.0, 0.3, 2.0, 2.2, 2.6, "bone", oy=-0.8)
        g.box((0, -3.3, 0.5), (2.2, 1.2, 1.0), "bone_dark")
        for sx in (-1, 1):
            g.sphere((sx * 1.2, -1.25, 2.7), 0.75, "cave", 7, 5, (1.0, 0.6, 1.0))
            g.cyl((sx * 2.4, 0.8, 3.2), (sx * 5.0, 0.2, 4.0), 0.75, 0.55, "bone_dark", 6)
            g.cyl((sx * 5.0, 0.2, 4.0), (sx * 6.6, -1.2, 6.6), 0.55, 0.0, "bone_dark", 6)
            g.cyl((sx * 1.3, -3.4, 0.4), (sx * 1.9, -4.6, 2.6), 0.4, 0.0, "bone", 5)
            for k in range(3):
                g.cyl((sx * (0.3 + 0.55 * k), -3.6, 0.1), (sx * (0.3 + 0.55 * k), -3.7, -0.9), 0.22, 0.0, "bone", 4)
        # The warlord's seat over the far side.
        w.box((0, 11.2, 4.6), (9.0, 4.0, 9.2), "granite")
        w.box((0, 9.6, 9.5), (7.0, 3.6, 0.6), "stone_dark")
        w.box((0, 10.6, 10.6), (2.6, 2.2, 1.6), "iron")
        w.box((0, 11.5, 12.6), (2.8, 0.5, 4.2), "iron")
        for sx in (-1, 1):
            w.box((sx * 1.5, 10.5, 11.6), (0.5, 2.2, 0.6), "bone_dark")
            for k in range(3):
                w.cyl((sx * (0.5 + 0.5 * k), 11.6, 14.4), (sx * (1.0 + 0.9 * k), 11.8, 16.2 - 0.5 * k), 0.16, 0.0, "bone", 4)
            w.cyl((sx * 3.0, 9.0, 9.8), (sx * 3.0, 9.0, 11.2), 0.8, 0.9, "hide", 8)
            w.cyl((sx * 3.0, 9.0, 11.2), (sx * 3.0, 9.0, 11.3), 0.92, 0.92, "bone", 8)
            P.brazier(w, sx * 4.0, 11.6, 9.2, 1.6, "iron")
        w.sphere((0, 11.4, 15.0), 0.8, "bone", 7, 5, (1.0, 1.0, 1.1))
        for i, (x, y) in enumerate(((-12.5, -9.0), (12.5, -9.0), (-12.5, 9.0), (12.5, 9.0))):
            name = "flag%d" % i
            bones += P.flag(w, name, x, y, 6.5, 8.0, "war_red", 1.6, "pole_dark", "bone")
            flags.append(name)
        w.cyl((0, 0, 0.2), (0, 0, 4.5), 0.35, 0.28, "pole_dark", 6)            # The post in the pit.
        for k in range(4):
            a = TAU * k / 4
            w.cyl((0, 0, 3.6), (math.cos(a) * 1.6, math.sin(a) * 1.6, 0.3), 0.05, 0.05, "iron", 4)

        def idle(t):
            return P.flag_turns(flags, t, 2), P.flame_moves(t, 0.15, 6)

        P.finish(w, "wonder_war_arena", bones, [("idle", 4.0, idle)])
    return build


MODELS = {}
for _base, _fn in (("wonder_ziggurat", ziggurat), ("wonder_world_tree", world_tree), ("wonder_dwarf_gate", dwarf_gate), ("wonder_obsidian_spire", obsidian_spire),
                   ("wonder_sun_temple", sun_temple), ("wonder_fox_shrine", fox_shrine), ("wonder_lily_palace", lily_palace), ("wonder_war_arena", war_arena)):
    MODELS.update(_stages(_base, _fn))
MODELS["wonder_sun_temple_ruin"] = sun_temple(P.RUIN)
