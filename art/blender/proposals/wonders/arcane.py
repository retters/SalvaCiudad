"""Wonders of knowledge and magic: the great observatory with its orrery, the
portal ring, the mage academy whose tower floats in pieces and the dragon-bone
monument. Each is built in three stages (see parts.py).
"""

import math
import random

import parts as P
from parts import SLATE, TAU, kit

NIGHT = ("night", "slate_dark")
BLUE_FIRE = ("crystal_blue", "glow_blue")


def _crystal(w, x, y, z, s, mat="crystal_blue", mat2="glow_blue", seg=5):
    w.cyl((x, y, z), (x, y, z + 1.4 * s), 0.0, 0.5 * s, mat, seg)
    w.cyl((x, y, z + 1.4 * s), (x, y, z + 2.2 * s), 0.5 * s, 0.0, mat2, seg)


def observatory(stage):
    """A turning copper dome with a telescope, a stair tower and an orrery. Footprint 24 x 24 m, 22 m high."""
    def build():
        w = P.W()
        rnd = random.Random(51)
        s = P.staged(w, stage, 2.6, 7.5, (0.4, 2.0), salt=13.0)
        fin = stage == 3
        F = 1.5
        P.yard(w, stage, rnd, 24, 24, piles=[(-10.6, -10.8, 0.8), (10.6, -10.8, 0.8)], timbers=[(10.9, 10.4, 0)], outline=(23.6, 23.6))
        w.cyl((0, 0, 0), (0, 0, F), 11.8, 11.4, "stone_dark", 8, spin=22.5)
        P.steps(w, 0, -10.5, 5.0, 6, 0.25, 0.25, "stone_light")
        P.drum(s, 0, 1.5, 6.0, F, 12.0, "stone", 12)
        for i in range(6):
            a = TAU * (i + 0.5) / 6
            s.box((math.cos(a) * 6.2, 1.5 + math.sin(a) * 6.2, F + 4.5), (1.0, 1.4, 9.0), "stone_dark", rz=math.degrees(a))
        P.drum(s, 7.0, 6.0, 2.0, F, 16.0, "stone_light", 8)
        if stage == 1:
            P.crane(w.at(0, 1.5, F, 0), 6.0, 3.0)
            P.lodge(w.at(0, 0, F), -6.5, -6.0, 30)
        if stage == 2:
            P.scaffold_ring(w, 0, 1.5, 6.5, 4, n=8, z=F, a0=math.pi * 0.62, a1=math.pi * 2.25)
            P.crane(w.at(0, 1.5, F, 0), 11.0, 3.0)
        if not fin:
            P.finish(w, P.model_id("wonder_observatory", stage))
            return

        w.cyl((0, 1.5, 12.0), (0, 1.5, 12.6), 6.6, 6.6, "stone_light", 12, spin=15)
        d = w.bone("dome")
        P.dome(d, 0, 1.5, 12.6, 6.2, "copper", "copper_dark", 12, 5)
        pts = [(0, 1.5 - math.cos(a) * 6.0, 12.6 + math.sin(a) * 6.0) for a in [math.radians(8 + 20 * k) for k in range(6)]]
        for p0, p1 in zip(pts, pts[1:]):
            d.cyl(p0, p1, 1.1, 1.1, "glass_dark", 4, spin=45)
        d.cyl((0, 0.5, 14.6), (0, -4.2, 19.6), 0.6, 0.75, "bronze", 8)
        d.cyl((0, -4.2, 19.6), (0, -4.5, 19.92), 0.85, 0.85, "gold", 8)
        d.cyl((0, -4.5, 19.92), (0, -4.56, 19.98), 0.6, 0.6, "glass_blue", 8)
        d.cyl((0, -1.3, 16.5), (0, -1.6, 16.8), 0.8, 0.8, "gold_dark", 8)
        P.door(w.at(0, 1.5 - 5.82, F), 2.2, 3.6, "door", "stone_light")
        for i in (1, 2, 4, 5, 7, 8, 10, 11):
            a = TAU * i / 12 - math.pi / 2
            P.window(w.at(math.cos(a) * 5.82, 1.5 + math.sin(a) * 5.82, 6.0, math.degrees(a) + 90), 1.1, 3.0, "glass_blue", "stone_light")
        w.cyl((7.0, 6.0, 16.0), (7.0, 6.0, 16.5), 2.6, 2.6, "stone", 8)
        for i in range(8):
            a = TAU * i / 8
            w.box((7.0 + math.cos(a) * 2.4, 6.0 + math.sin(a) * 2.4, 17.0), (0.3, 0.3, 1.0), "stone_light")
        w.cyl((7.0, 6.0, 16.5), (7.0, 6.0, 18.4), 1.4, 1.4, "stone_light", 8)
        P.cone_roof(w, 7.0, 6.0, 1.9, 18.4, 3.4, SLATE, 8, 2)
        P.finial(w, 7.0, 6.0, 21.6, 0.7)
        for z in (5.0, 9.0, 13.0):
            P.window(w.at(7.0 + 1.9, 6.0, z, 90), 0.7, 1.6, "window", "stone")
        # The orrery on the terrace.
        ox, oy = 0.0, -7.2
        w.cyl((ox, oy, F), (ox, oy, F + 0.08), 3.6, 3.6, "night", 16)
        for i in range(14):
            a = rnd.uniform(0, TAU)
            r = rnd.uniform(0.9, 3.3)
            w.box((ox + math.cos(a) * r, oy + math.sin(a) * r, F + 0.1), (0.16, 0.16, 0.04), "star", rz=45)
        w.cyl((ox, oy, F), (ox, oy, F + 2.4), 0.5, 0.3, "bronze_dark", 8)
        w.sphere((ox, oy, F + 3.6), 0.85, "gold", 10, 7)
        w.cyl((ox, oy, F + 2.4), (ox, oy, F + 3.0), 0.12, 0.12, "bronze_dark", 6)
        for plane in (0, 1):
            for i in range(14):
                a0, a1 = TAU * i / 14, TAU * (i + 1) / 14
                if plane == 0:
                    p0, p1 = (ox + math.cos(a0) * 1.5, oy, F + 3.6 + math.sin(a0) * 1.5), (ox + math.cos(a1) * 1.5, oy, F + 3.6 + math.sin(a1) * 1.5)
                else:
                    p0, p1 = (ox + math.cos(a0) * 1.65, oy + math.sin(a0) * 1.65 * 0.5, F + 3.6 + math.sin(a0) * 1.4), (ox + math.cos(a1) * 1.65, oy + math.sin(a1) * 1.65 * 0.5, F + 3.6 + math.sin(a1) * 1.4)
                w.cyl(p0, p1, 0.06, 0.06, "gold_dark", 4)
        bones = [("dome", (0, 1.5, 12.6), (0, 1.5, 13.6), None)]
        for k, (r, size, mat) in enumerate(((2.0, 0.3, "crystal_blue"), (2.7, 0.42, "jade"), (3.3, 0.34, "lacquer"))):
            o = w.bone("orb%d" % k)
            a = 2.1 * k
            z = F + 2.5 + 0.18 * k
            x, y = ox + math.cos(a) * r, oy + math.sin(a) * r
            o.cyl((ox, oy, z), (x, y, z), 0.05, 0.05, "bronze", 4)
            o.cyl((x, y, z), (x, y, F + 3.6 - size), 0.04, 0.04, "bronze", 4)
            o.sphere((x, y, F + 3.6), size, mat, 8, 5)
            bones.append(("orb%d" % k, (ox, oy, z), (ox, oy, z + 1), None))
        for i in range(8):
            a = TAU * (i + 0.5) / 8
            if abs(a - TAU * 0.75) < 0.5:
                continue
            x, y = math.cos(a) * 10.6, math.sin(a) * 10.6
            w.cyl((x, y, F), (x, y, F + 2.4), 0.12, 0.1, "iron", 6)
            P.lamp(w, x, y, F + 2.4, 1.6)

        def idle(t):
            return {"dome": [(kit.Z, 360.0 * t)], "orb0": [(kit.Z, 360.0 * 4 * t)], "orb1": [(kit.Z, 360.0 * 2 * t)], "orb2": [(kit.Z, 360.0 * t)]}, {}

        P.finish(w, "wonder_observatory", bones, [("idle", 24.0, idle)])
    return build


def portal(stage):
    """A standing ring of rune stones with a turning vortex. Footprint 18 x 12 m, 16 m high."""
    def build():
        w = P.W()
        rnd = random.Random(52)
        s = P.staged(w, stage, 1.6, 8.0, (0.0, 0.0), salt=14.0)
        fin = stage == 3
        P.yard(w, stage, rnd, 18, 12, piles=[(-8.0, -5.2, 0.7), (8.0, 5.2, 0.7)], outline=(17.6, 11.6))
        w.box((0, 0, 0.3), (16, 10, 0.6), "stone_dark")
        w.box((0, 0, 0.9), (13, 7, 0.6), "stone")
        P.steps(w, 0, -5.0, 6.0, 2, 0.3, 0.5, "stone_light")
        P.steps(w, 0, -3.5, 5.0, 2, 0.3, 0.5, "stone_light", z0=0.6)
        w.box((0, 0, 1.8), (4.4, 2.6, 1.2), "stone_light")
        P.steps(w, 0, -1.3, 3.4, 4, 0.3, 0.3, "stone", z0=1.2)
        C, R0, R1, N = 7.8, 5.2, 7.0, 20
        for i in range(N):
            a0, a1 = TAU * i / N - math.pi / 2, TAU * (i + 1) / N - math.pi / 2
            ring = [(math.cos(a0) * R0, -0.9, C + math.sin(a0) * R0), (math.cos(a0) * R1, -0.9, C + math.sin(a0) * R1),
                    (math.cos(a1) * R1, -0.9, C + math.sin(a1) * R1), (math.cos(a1) * R0, -0.9, C + math.sin(a1) * R0)]
            s.solid(ring, (0, 1.8, 0), "granite" if i % 2 else "stone_light")
        for cx in (-1, 1):
            for cy in (-1, 1):
                s.frustum(cx * 7.2, cy * 4.2, 1.3, 1.3, 0.6, 0.8, 0.8, 6.6, "granite")
        if stage == 1:
            P.lodge(w.at(0, 0, 1.2), -3.8, 0.6, 90)
        if stage == 2:
            P.scaffold(w, (-7.6, -1.0), (7.6, -1.0), 4, 1.2, depth=1.2)
            P.scaffold(w, (7.6, 1.0), (-7.6, 1.0), 4, 1.2, depth=1.2)
            P.crane(w.at(0, 0.3, 2.4, 0), 9.0, 1.6, load="granite")
            for k in range(7):                                                 # The timber centering the stones will rest on.
                a = math.pi * (k + 0.5) / 7
                w.cyl((0, 0, 2.4), (math.cos(a) * 5.0, 0, C + math.sin(a) * 5.0), 0.1, 0.1, "pole", 4)
        if not fin:
            P.finish(w, P.model_id("wonder_portal", stage))
            return

        for i in range(N):
            a = TAU * (i + 0.5) / N - math.pi / 2
            for y in (-0.95, 0.95):
                w.box((math.cos(a) * 6.1, y, C + math.sin(a) * 6.1), (0.5, 0.14, 0.9 if i % 2 else 0.6), "glow_blue" if i % 3 else "crystal_blue")
        w.box((0, 0, C + 7.4), (1.8, 2.3, 1.5), "stone_light")
        w.cyl((0, -1.2, C + 7.4), (0, -1.3, C + 7.4), 0.5, 0.5, "crystal_blue", 6)
        w.cyl((0, -0.12, C), (0, 0.12, C), 5.3, 5.3, "night", 24)
        v = w.bone("vortex")
        for y in (-0.2, 0.2):
            v.sphere((0, y, C), 1.1, "glow_blue", 10, 5, (1.0, 0.2, 1.0))
            for arm in range(3):
                for k in range(8):
                    a = TAU * arm / 3 + 0.42 * k
                    r = 1.0 + 0.52 * k
                    v.sphere((math.cos(a) * r, y, C + math.sin(a) * r), 0.62 - 0.05 * k, "crystal_blue" if k % 2 else "glow_blue", 6, 4, (1.0, 0.25, 1.0))
            for k in range(9):
                a = 2.4 * k + 0.5
                r = 2.0 + 0.33 * k
                v.box((math.cos(a) * r, y * 1.1, C + math.sin(a) * r), (0.14, 0.06, 0.14), "star")
        bob = w.bone("bob")
        for cx in (-1, 1):
            for cy in (-1, 1):
                w.box((cx * 7.2, cy * 4.2, 6.7), (1.1, 1.1, 0.25), "stone_light")
                _crystal(bob, cx * 7.2, cy * 4.2, 7.4, 0.9)
        for sx in (-1, 1):
            P.brazier(w, sx * 4.0, -5.4, 0.0, 1.4, "granite_dark", mats=BLUE_FIRE)

        def idle(t):
            moves = P.flame_moves(t, 0.1, 6)
            moves["bob"] = (0, 0, 0.3 * math.sin(TAU * t))
            return {"vortex": [(kit.Y, 360.0 * t)]}, moves

        P.finish(w, "wonder_portal", [("vortex", (0, -0.2, C), (0, 0.8, C), None), ("bob", (0, 0, 7.4), (0, 0, 8.4), None)], [("idle", 6.0, idle)])
    return build


def mage_academy(stage):
    """A hall of eight sides under a tower whose upper floors float apart. Footprint 22 x 22 m, 50 m high."""
    def build():
        w = P.W()
        rnd = random.Random(53)
        s = P.staged(w, stage, 2.4, 10.5, (0.4, 2.5), salt=15.0)
        fin = stage == 3
        P.yard(w, stage, rnd, 22, 22, piles=[(-9.8, -9.9, 0.8), (9.8, -9.9, 0.8)], outline=(21.6, 21.6))
        w.cyl((0, 0, 0), (0, 0, 1.0), 10.8, 10.4, "stone_dark", 8, spin=22.5)
        P.steps(w, 0, -9.6, 5.0, 4, 0.25, 0.3, "stone_light")
        P.drum(s, 0, 0, 7.5, 1.0, 9.0, "stone", 8)
        turrets = [(cx * 5.7, cy * 5.7) for cx in (-1, 1) for cy in (-1, 1)]
        for x, y in turrets:
            P.drum(s, x, y, 1.8, 1.0, 13.0, "stone_light", 8)
        P.drum(s, 0, 0, 3.8, 9.0, 24.0, "stone", 8, r2=3.4)
        if stage == 1:
            P.crane(w.at(0, 0, 1.0, 0), 6.0, 3.0)
        if stage == 2:
            P.scaffold_ring(w, 0, 0, 7.9, 3, n=6, z=1.0, a0=-math.pi * 0.25 + 0.3, a1=math.pi * 1.25 - 0.3, depth=1.2)
            P.crane(w.at(0, 0, 1.0, 0), 13.0, 3.0)
        if not fin:
            P.finish(w, P.model_id("wonder_mage_academy", stage))
            return

        P.cone_roof(w, 0, 0, 8.0, 9.0, 3.2, NIGHT, 8, 3)
        for x, y in turrets:
            w.cyl((x, y, 13.0), (x, y, 13.4), 2.2, 2.2, "stone", 8)
            P.cone_roof(w, x, y, 2.2, 13.4, 5.0, NIGHT, 8, 2)
            P.finial(w, x, y, 18.2, 0.6)
            a = math.atan2(y, x)
            P.window(w.at(x + math.cos(a) * 1.7, y + math.sin(a) * 1.7, 9.0, math.degrees(a) + 90), 0.7, 2.0, "glow_blue", "stone")
        P.door(w.at(0, -6.93, 1.0), 2.4, 4.0, "door", "stone_light")
        for sx in (-1, 1):
            P.banner(w.at(sx * 2.6, -6.95, 8.4), 1.2, 5.0, "cloth_purple")
            P.window(w.at(sx * 6.93, 0, 3.0, 90 * sx), 1.6, 3.4, "glow_blue", "stone_light")
        P.window(w.at(0, 6.93, 3.0, 180), 1.6, 3.4, "glow_blue", "stone_light")
        for i in range(6):
            a = TAU * i / 8 * 3
            z = 11.5 + 2.0 * i
            P.window(w.at(math.cos(a) * 3.4, math.sin(a) * 3.4, z, math.degrees(a) + 90), 0.8, 1.8, "glow_blue", "stone_light")
        for i in range(8):                                                     # The broken crown of the tower.
            a = TAU * (i + 0.5) / 8
            w.frustum(math.cos(a) * 2.9, math.sin(a) * 2.9, 1.5, 1.2, 23.6, 0.2, 0.2, 24.4 + rnd.uniform(0.3, 1.8), "stone_dark", rz=math.degrees(a))
        core = w.bone("core")
        core.sphere((0, 0, 26.6), 1.2, "glow_blue", 8, 6)
        runes = w.bone("runes")
        for i in range(8):
            a = TAU * i / 8
            runes.box((math.cos(a) * 3.6, math.sin(a) * 3.6, 26.6), (0.14, 1.0, 1.4), "crystal_blue", rz=math.degrees(a))
        f1 = w.bone("float1")
        f1.cyl((0, 0, 27.4), (0, 0, 29.2), 0.8, 3.4, "stone_dark", 8)
        f1.cyl((0, 0, 29.2), (0, 0, 35.5), 3.4, 3.2, "stone", 8)
        f1.cyl((0, 0, 32.0), (0, 0, 32.4), 4.3, 4.3, "stone_light", 8)
        f1.cyl((0, 0, 35.5), (0, 0, 36.0), 3.7, 3.7, "stone_light", 8)
        for i in range(4):
            a = TAU * i / 4 + 0.4
            P.window(f1.at(math.cos(a) * 3.2, math.sin(a) * 3.2, 32.6, math.degrees(a) + 90), 0.9, 2.0, "glow_blue", "stone_light")
        f2 = w.bone("float2")
        f2.cyl((0, 0, 37.6), (0, 0, 39.0), 0.6, 2.8, "stone_dark", 8)
        f2.cyl((0, 0, 39.0), (0, 0, 43.0), 2.8, 2.8, "stone_light", 8)
        f2.cyl((0, 0, 43.0), (0, 0, 43.5), 3.6, 3.6, "stone", 8)
        P.cone_roof(f2, 0, 0, 3.8, 43.5, 6.5, NIGHT, 8, 3)
        P.finial(f2, 0, 0, 49.6, 1.0)
        for i in range(4):
            a = TAU * i / 4
            P.window(f2.at(math.cos(a) * 2.6, math.sin(a) * 2.6, 40.0, math.degrees(a) + 90), 0.9, 1.8, "glow_blue", "stone")
        rocks = w.bone("rocks")
        for i in range(5):
            a = TAU * i / 5 + 0.3
            x, y, z = math.cos(a) * 7.6, math.sin(a) * 7.6, 21.0 + 3.2 * i
            rocks.cyl((x, y, z - 1.6), (x, y, z), 0.2, 1.3, "stone_dark", 6)
            rocks.cyl((x, y, z), (x, y, z + 0.3), 1.3, 1.2, "grass", 6)
            if i % 2:
                _crystal(rocks, x, y, z + 0.3, 0.7)
            else:
                P.tree(rocks, x, y, z + 0.3, 0.7, rnd)

        def idle(t):
            turns = {"float2": [(kit.Z, 360.0 * t)], "rocks": [(kit.Z, 360.0 * t)], "runes": [(kit.Z, -720.0 * t)]}
            moves = {"float1": (0, 0, 0.45 * math.sin(TAU * 2 * t)), "float2": (0, 0, 0.6 * math.sin(TAU * 2 * t + 1.2)),
                     "core": (0, 0, 0.3 * math.sin(TAU * 4 * t)), "rocks": (0, 0, 0.5 * math.sin(TAU * 3 * t))}
            return turns, moves

        bones = [("core", (0, 0, 26), (0, 0, 27), None), ("runes", (0, 0, 26), (0, 0, 27), None), ("float1", (0, 0, 29), (0, 0, 30), None),
                 ("float2", (0, 0, 39), (0, 0, 40), None), ("rocks", (0, 0, 21), (0, 0, 22), None)]
        P.finish(w, "wonder_mage_academy", bones, [("idle", 12.0, idle)])
    return build


# -------------------------------------------------------------- dragon bones


def _spine(u):
    return (-9.0 + 22.0 * u, 0.0, 5.2 + 2.4 * math.sin(math.pi * (u * 0.95 + 0.12)) - 3.4 * max(0.0, u - 0.62) ** 1.2 * 3.2)


def _skull(g):
    """A dragon's skull at the local origin, its snout toward -Y."""
    g.sphere((0, 0.6, 1.5), 1.5, "bone", 9, 6, (1.0, 1.3, 0.85))
    g.frustum(0, -1.6, 2.4, 3.2, 0.9, 1.3, 2.6, 2.1, "bone", oy=-0.5)
    g.frustum(0, -2.2, 1.9, 4.0, 0.0, 1.5, 3.6, 0.5, "bone_dark", oy=0.3)
    for sx in (-1, 1):
        g.sphere((sx * 0.8, -0.3, 1.9), 0.5, "cave", 6, 4, (0.7, 1.0, 0.9))
        g.cyl((sx * 0.9, 1.4, 2.2), (sx * 1.7, 3.4, 3.4), 0.45, 0.28, "bone_dark", 6)
        g.cyl((sx * 1.7, 3.4, 3.4), (sx * 1.5, 4.8, 5.0), 0.28, 0.0, "bone_dark", 6)
        for k in range(5):
            g.cyl((sx * (0.95 - 0.09 * k), -0.8 - 0.62 * k, 0.95), (sx * (0.95 - 0.09 * k), -0.85 - 0.62 * k, 0.35), 0.16, 0.0, "bone", 4)
            g.cyl((sx * (0.7 - 0.05 * k), -1.0 - 0.6 * k, 0.45), (sx * (0.7 - 0.05 * k), -1.0 - 0.6 * k, 0.95), 0.13, 0.0, "bone", 4)
        g.sphere((sx * 0.35, -3.3, 1.7), 0.2, "cave", 5, 3)


def _dragon(w, rnd, rib_sides=(-1, 1), wings=True, legs=True):
    n = 26
    for i in range(n):
        u = i / (n - 1)
        x, y, z = _spine(u)
        r = 0.62 - 0.4 * u
        w.sphere((x, y, z), r, "bone" if i % 2 else "bone_dark", 6, 4, (0.8, 1.0, 1.0))
        if u < 0.7:
            w.cyl((x, y, z + r * 0.6), (x + 0.3, y, z + r + 0.9 - 0.6 * u), 0.2, 0.0, "bone", 4)
        if i % 5 == 2 and u < 0.8:
            w.cyl((x, y, 1.1), (x, y, z - r * 0.6), 0.14, 0.12, "bronze_dark", 6)
            w.cyl((x, y, 1.1), (x, y, 1.3), 0.4, 0.3, "bronze_dark", 6)
    for i in range(9):                                                         # The ribs.
        u = 0.14 + 0.05 * i
        x, y, z = _spine(u)
        rr = 3.3 - 0.22 * abs(i - 3.5)
        for sy in rib_sides:
            pts = []
            for k in range(6):
                th = math.radians(8 + 29 * k)
                pts.append((x + 0.5 * math.sin(th), sy * rr * math.sin(th), z - rr * 0.95 * (1 - math.cos(th)) * (z - 1.15) / (rr * 1.75)))
            for k, (p0, p1) in enumerate(zip(pts, pts[1:])):
                w.cyl(p0, p1, 0.22 - 0.03 * k, 0.19 - 0.03 * k, "bone", 5)
    if legs:
        for u, reach in ((0.16, 1.0), (0.56, 1.15)):
            x, y, z = _spine(u)
            for sy in (-1, 1):
                knee = (x + 1.2, sy * 4.4 * reach, z - 1.2)
                foot = (x - 0.4, sy * 4.9 * reach, 1.15)
                w.cyl((x, sy * 1.0, z - 0.3), knee, 0.34, 0.24, "bone", 6)
                w.cyl(knee, foot, 0.24, 0.18, "bone_dark", 6)
                for k in (-1, 0, 1):
                    w.cyl(foot, (foot[0] - 1.1, foot[1] + k * 0.5, 1.2), 0.14, 0.0, "bone", 4)
    if wings:
        x, y, z = _spine(0.2)
        for sy in (-1, 1):
            elbow = (x + 0.5, sy * 3.6, z + 5.0)
            wrist = (x + 3.2, sy * 6.2, z + 7.6)
            w.cyl((x, sy * 0.8, z + 0.3), elbow, 0.36, 0.26, "bone", 6)
            w.cyl(elbow, wrist, 0.26, 0.2, "bone_dark", 6)
            for k, (dx, dy, dz) in enumerate(((5.5, -1.2, -1.0), (7.6, -0.4, -3.6), (7.0, 0.4, -6.2), (4.6, 0.6, -7.6))):
                w.cyl(wrist, (wrist[0] + dx, sy * (6.2 + dy), wrist[2] + dz), 0.16, 0.04, "bone", 5)
            w.cyl(wrist, (wrist[0] - 0.8, sy * 6.6, wrist[2] + 1.4), 0.16, 0.0, "bone_dark", 4)


def dragon_bones(stage):
    """The skeleton of a great dragon raised on bronze props, wings open. Footprint 34 x 16 m, 15 m high."""
    def build():
        w = P.W()
        rnd = random.Random(54)
        fin = stage == 3
        P.yard(w, stage, rnd, 34, 16, piles=[(13.5, -6.6, 0.8)], timbers=[(-12, 6.8, 0)], lodges=[(11, 5.0, 180)] if stage == 1 else [], outline=(33.6, 15.6))
        w.box((1, 0, 0.4), (28, 11, 0.8), "stone_dark")
        w.box((1, 0, 0.95), (27, 10, 0.3), "stone")
        P.steps(w, 1, -5.5, 6.0, 4, 0.27, 0.3, "stone_light")
        if stage == 1:
            _skull(w.at(-9, -1.0, 1.1, 20))
            for i in range(14):                                                # The bones as the carts brought them.
                x, y = rnd.uniform(-3, 10), rnd.uniform(-3.5, 3.5)
                a = rnd.uniform(0, TAU)
                w.cyl((x, y, 1.3 + 0.25 * (i % 3)), (x + math.cos(a) * 3.0, y + math.sin(a) * 3.0, 1.4 + 0.25 * (i % 3)), 0.24, 0.16, "bone" if i % 2 else "bone_dark", 5)
            for i in range(6):
                w.sphere((11 + 0.9 * (i % 3), -2.5 + 1.0 * (i // 3), 1.6), 0.55, "bone_dark", 6, 4, (0.8, 1, 1))
            P.finish(w, "wonder_dragon_bones_stage1")
            return
        if stage == 2:
            _dragon(w, rnd, rib_sides=(1,), wings=False, legs=False)
            _skull(w.at(-12.4, -5.6, 0.0, 60))
            P.scaffold(w, (-10, -5.3), (12, -5.3), 3, 1.1, depth=1.2)
            P.crane(w.at(2, -7.2, 0, 180), 9.0, 3.2, load="bone")
            for i in range(5):
                w.cyl((-6 + 2.0 * i, 6.0, 1.3), (-5 + 2.0 * i, 7.6, 0.3), 0.2, 0.14, "bone", 5)
            P.finish(w, "wonder_dragon_bones_stage2")
            return

        _dragon(w, rnd)
        x0, _, z0 = _spine(0.0)                                                # The neck comes down to the skull.
        neck = [(x0, 0, z0), (-10.4, -0.8, 6.6), (-11.6, -2.0, 6.0), (-12.3, -3.2, 5.0)]
        for i, (p0, p1) in enumerate(zip(neck, neck[1:])):
            w.cyl(p0, p1, 0.55, 0.5, "bone" if i % 2 else "bone_dark", 6)
            w.sphere(p1, 0.62, "bone", 6, 4)
        w.box((-12.6, -4.4, 1.6), (3.0, 3.6, 3.2), "stone")
        w.box((-12.6, -4.4, 3.3), (3.4, 4.0, 0.3), "stone_light")
        _skull(w.at(-12.6, -4.2, 3.45, 25))
        g = w.at(-12.4, -3.4, 5.0)
        g.turn("X", -20).box((0, 0, 1.6), (0.3, 0.1, 3.4), "steel")             # The sword that killed it.
        g.turn("X", -20).box((0, 0, 3.4), (1.2, 0.2, 0.2), "gold")
        g.turn("X", -20).cyl((0, 0, 3.5), (0, 0, 4.3), 0.1, 0.1, "leather", 5)
        w.box((1, -5.2, 1.5), (4.0, 0.3, 1.0), "stone_light")
        w.box((1, -5.4, 1.5), (3.4, 0.12, 0.7), "bronze")
        for x in (-11.5, 13.5):
            for y in (-4.4, 4.4):
                if x < 0 and y < 0:
                    continue
                P.brazier(w, x, y, 1.1, 1.5, "bronze_dark")
        P.finish(w, "wonder_dragon_bones", [], [("idle", 4.0, lambda t: ({}, P.flame_moves(t, 0.1, 6)))])
    return build


MODELS = {}
for _base, _fn in (("wonder_observatory", observatory), ("wonder_portal", portal), ("wonder_mage_academy", mage_academy), ("wonder_dragon_bones", dragon_bones)):
    for _stage in (1, 2, 3):
        MODELS[P.model_id(_base, _stage)] = _fn(_stage)
