"""Small flying things, all rigid, with one looping clip that fills a
patch of air (the model is the whole patch: place it and play):

- butterfly (0.25 m of wingspan, bigger than life so it shows): fly, a
  wandering loop of flutters, and idle, perched with the wings opening and
  closing. Orange, blue and white;
- dragonfly: fly (hovers, darts sideways and comes back) and idle (perched,
  wings flat). Blue and red;
- firefly swarm: nine points of light each on its own looping path inside
  a 1.6 m ball; idle;
- bat swarm: seven small bats circling a 1.2 m ring, each flapping; fly,
  attack (the ring tightens and dives) and die (they drop).
"""

import math

from mathutils import Quaternion, Vector

import _parts as P
from _parts import X, Y, Z, hull, seg, spike, ball, plate

# ---------------------------------------------------------------- butterfly

BF_H = 0.6


def butterfly(name, wing, edge, spot):
    colors = P.palette(body=0x2A2420, wing=wing, edge=edge, spot=spot)

    def make():
        mb = P.kit.begin()
        seg(mb, (0, 0.06, BF_H), (0, -0.05, BF_H), 0.008, 0.012, "body", "body", sides=5)
        ball(mb, (0, -0.06, BF_H + 0.003), 0.013, "body", "body")
        for s in (-1, 1):
            seg(mb, (s * 0.005, -0.07, BF_H + 0.01), (s * 0.03, -0.12, BF_H + 0.04), 0.002, 0.002, "body", "body", sides=3)
            side = "L" if s > 0 else "R"
            up = [(0.006, -0.03, 0), (0.07, -0.085, 0), (0.125, -0.06, 0), (0.115, 0.0, 0), (0.006, 0.015, 0)]
            low = [(0.006, 0.01, 0), (0.1, 0.01, 0), (0.09, 0.075, 0), (0.04, 0.095, 0), (0.006, 0.05, 0)]
            for pts, mat in ((up, "wing"), (low, "edge")):
                plate(mb, [(s * x, y, BF_H + 0.004) for x, y, z in pts], 0.004, mat, f"wing.{side}")
            for x, y in ((0.085, -0.045), (0.07, 0.04)):
                plate(mb, [(s * (x + dx), y + dy, BF_H + 0.0075) for dx, dy in ((-0.015, 0), (0, -0.015), (0.015, 0),
                                                                              (0, 0.015))], 0.002, "spot", f"wing.{side}")
        m = P.kit.Mech([("body", (0, 0.06, BF_H), (0, -0.06, BF_H), None), ("wing.L", (0.004, 0, BF_H), (0.12, 0, BF_H), "body"),
                        ("wing.R", (-0.004, 0, BF_H), (-0.12, 0, BF_H), "body")])

        def wings(turns, angle):
            turns["wing.L"] = [(Y, -angle)]
            turns["wing.R"] = [(Y, angle)]

        def fly(t):
            p = 2 * math.pi * t
            beat = math.sin(8 * p)
            x, y = 0.35 * math.sin(p), 0.25 * math.sin(2 * p)             # A figure of eight.
            heading = math.degrees(math.atan2(0.35 * math.cos(p), -0.5 * math.cos(2 * p)))
            turns = {"body": [(X, -18.0), (Z, heading * 0.5)]}
            wings(turns, 30.0 + 50.0 * beat)
            return turns, {"root": (x, y, 0.12 * math.sin(3 * p) - 0.04 * beat)}

        def idle(t):
            p = 2 * math.pi * t
            turns = {"body": [(X, -8.0)]}
            wings(turns, 45.0 + 38.0 * math.sin(p) + 5.0 * math.sin(4 * p))
            return turns, {"root": (0, 0, -BF_H + 0.03)}

        m.clip("fly", 3.0, fly)
        m.clip("idle", 2.5, idle)
        P.kit.save(mb, P.FAMILY, name, colors, mech=m)
    return make


# ---------------------------------------------------------------- dragonfly

DF_H = 0.7


def dragonfly(name, body_color, eye):
    colors = P.palette(body=body_color, dark=0x1E2A30, wing=0xDCEEF4, eye=eye)

    def make():
        mb = P.kit.begin()
        seg(mb, (0, -0.03, DF_H), (0, 0.03, DF_H), 0.016, 0.012, "body", "body", sides=5)
        for i in range(5):                                          # The long segmented tail.
            seg(mb, (0, 0.03 + i * 0.035, DF_H), (0, 0.062 + i * 0.035, DF_H), 0.008, 0.007, "body" if i % 2 else "dark",
                "body", sides=4)
        ball(mb, (0, -0.045, DF_H), 0.015, "dark", "body")
        for s in (-1, 1):
            ball(mb, (s * 0.012, -0.052, DF_H + 0.005), 0.011, "eye", "body")
            side = "L" if s > 0 else "R"
            for n, y, length in (("1", -0.02, 0.15), ("2", 0.012, 0.13)):
                plate(mb, [(s * 0.008, y - 0.008, DF_H + 0.012), (s * length * 0.6, y - 0.02, DF_H + 0.012),
                           (s * length, y - 0.005, DF_H + 0.012), (s * length * 0.9, y + 0.014, DF_H + 0.012),
                           (s * 0.008, y + 0.008, DF_H + 0.012)], 0.003, "wing", f"wing.{n}.{side}")
        bones = [("body", (0, 0.05, DF_H), (0, -0.05, DF_H), None)]
        for side, s in P.SIDES:
            for n, y in (("1", -0.02), ("2", 0.012)):
                bones.append((f"wing.{n}.{side}", (s * 0.008, y, DF_H + 0.012), (s * 0.15, y, DF_H + 0.012), "body"))
        m = P.kit.Mech(bones)

        def wings(turns, a, b):
            for side, s in P.SIDES:
                turns[f"wing.1.{side}"] = [(Y, -s * a)]
                turns[f"wing.2.{side}"] = [(Y, -s * b)]

        def fly(t):
            p = 2 * math.pi * t
            dart = P.smooth((t - 0.3) / 0.06) - P.smooth((t - 0.62) / 0.06)   # Jumps aside, hovers, jumps back.
            turns = {"body": [(X, 6.0 + 3.0 * math.sin(3 * p)), (Z, -25.0 * dart)]}
            wings(turns, 22.0 * math.sin(30 * p), 22.0 * math.sin(30 * p + 2.0))
            return turns, {"root": (0.45 * dart, -0.15 * dart, 0.03 * math.sin(4 * p) + 0.1 * dart)}

        def idle(t):
            p = 2 * math.pi * t
            turns = {"body": [(X, -10.0)]}
            twitch = P.pulse(t, 0.5, 0.52, 0.56, 0.6)
            wings(turns, -6.0 + 14.0 * twitch, -10.0 + 10.0 * twitch)
            return turns, {"root": (0, 0, -DF_H + 0.035)}

        m.clip("fly", 2.0, fly)
        m.clip("idle", 3.0, idle)
        P.kit.save(mb, P.FAMILY, name, colors, mech=m)
    return make


# ----------------------------------------------------------- firefly swarm

def fireflies(name, glow, body=0x2A2A1E, size=1.0, seconds=6.0, spread=1.0):
    colors = P.palette(glow=glow, body=body)
    n = 9

    def make():
        mb = P.kit.begin()
        homes = []
        for i in range(n):
            a = i * 2.4
            home = Vector((0.55 * spread * math.cos(a) * (0.5 + 0.5 * ((i * 7) % 5) / 4), 0.55 * spread * math.sin(a),
                           0.5 + 0.11 * i * spread))
            homes.append(home)
            ball(mb, home, 0.022 * size, "glow", f"fly.{i + 1}", segments=6, rings=4, scale=(1, 1.4, 1))
            ball(mb, home + Vector((0, 0.03 * size, 0.004)), 0.016 * size, "body", f"fly.{i + 1}", segments=5, rings=3)
        m = P.kit.Mech([(f"fly.{i + 1}", tuple(homes[i]), tuple(homes[i] + Vector((0, -0.04, 0))), None)
                        for i in range(n)])

        def idle(t):
            p = 2 * math.pi * t
            moves = {}
            for i in range(n):
                a, b, c = 1 + i % 3, 1 + (i + 1) % 2, 1 + (i + 2) % 3
                ph = i * 1.3
                moves[f"fly.{i + 1}"] = (0.22 * spread * math.sin(a * p + ph), 0.22 * spread * math.cos(b * p + ph * 0.7),
                                         0.16 * spread * math.sin(c * p + ph * 1.9))
            return {}, moves

        m.clip("idle", seconds, idle)
        P.kit.save(mb, P.FAMILY, name, colors, mech=m)
    return make


# ---------------------------------------------------------------- bat swarm

def bat_swarm(name, fur, membrane):
    colors = P.palette(fur=fur, membrane=membrane, eye=0xE0342A)
    n, height = 7, 1.6
    fwd, out = Vector((0, -1, 0)), Vector((1, 0, 0))

    def path(i, t, radius=1.0):
        """Where bat i is and where it heads: a figure of eight of its own
        size, tilt and phase. The heading never turns more than 165 degrees
        from the rest direction, so no turn wraps around."""
        th = math.tau * t + i * math.tau / n
        size = (0.75 + 0.1 * (i % 4)) * radius
        yaw = math.radians(-30.0 + 10.0 * i)
        x, y = size * math.sin(th), size * 0.5 * math.sin(2 * th)
        vx, vy = math.cos(th), math.cos(2 * th)
        h = math.degrees(math.atan2(vy, vx))
        if h > 90.0:
            h -= 360.0
        c, s = math.cos(yaw), math.sin(yaw)
        pos = Vector((x * c - y * s, x * s + y * c, height + 0.2 * (i % 3) + 0.15 * math.sin(2 * th + i)))
        return pos, math.radians(h + 90.0) + yaw

    def make():
        mb = P.kit.begin()
        bones = []
        for i in range(n):
            c, _ = path(i, 0.0)
            b = f"bat.{i + 1}"
            hull(mb, [c + fwd * 0.07, c - fwd * 0.07 + out * 0.03, c - fwd * 0.07 - out * 0.03, c + Vector((0, 0, 0.035)),
                      c - Vector((0, 0, 0.03))], "fur", b)
            ball(mb, c + fwd * 0.08 + Vector((0, 0, 0.012)), 0.028, "fur", b)
            for s in (-1, 1):
                spike(mb, c + fwd * 0.085 + out * s * 0.015 + Vector((0, 0, 0.03)),
                      c + fwd * 0.09 + out * s * 0.03 + Vector((0, 0, 0.075)), 0.012, "fur", b, sides=3)
                ball(mb, c + fwd * 0.103 + out * s * 0.012 + Vector((0, 0, 0.02)), 0.006, "eye", b, segments=4, rings=3)
                side = "L" if s > 0 else "R"
                w = out * s
                plate(mb, [c + fwd * 0.04 + w * 0.02, c + fwd * 0.05 + w * 0.13, c + w * 0.2 - fwd * 0.01,
                           c - fwd * 0.07 + w * 0.12, c - fwd * 0.06 + w * 0.02], 0.006, "membrane", f"{b}.wing.{side}")
            bones.append((b, tuple(c), tuple(c + fwd * 0.07), None))
            for side, s in P.SIDES:
                bones.append((f"{b}.wing.{side}", tuple(c + out * s * 0.02), tuple(c + out * s * 0.2), b))
        m = P.kit.Mech(bones)

        def swarm(t, radius=1.0, drop=0.0, flap=1.0, fall=0.0):
            turn, place = {}, {}
            for i in range(n):
                pos, heading = path(i, t, radius)
                pos.z -= drop
                q = Quaternion(Z, heading)
                bank = Quaternion(fwd, math.radians(18.0 * math.sin(math.tau * t * 2 + i)))
                if fall:
                    pos.z = 0.04 + (pos.z - 0.04) * (1 - fall) ** 2
                    bank = Quaternion(fwd, math.radians(170.0 * fall))
                turn[f"bat.{i + 1}"] = q @ bank
                place[f"bat.{i + 1}"] = pos
            turns, moves = P.world_pose(m, turn, place)
            for i in range(n):
                beat = math.sin(math.tau * t * (9 + i % 3) + i) * flap
                for side, s in P.SIDES:
                    turns[f"bat.{i + 1}.wing.{side}"] = [(tuple(fwd), s * (10.0 + 50.0 * beat))]
            return turns, moves

        def attack(t):
            d = P.pulse(t, 0.15, 0.45, 0.55, 0.85)
            return swarm(t, radius=1.0 - 0.6 * d, drop=0.7 * d)

        def die(t):
            f = P.smooth(t / 0.8)
            return swarm(t * 0.3, flap=1.0 - f, fall=f)

        m.clip("fly", 3.0, swarm)
        m.clip("attack", 3.0, attack)
        m.clip("die", 1.2, die, loops=False)
        P.kit.save(mb, P.FAMILY, name, colors, mech=m)
    return make


MODELS = {
    "animal_butterfly": butterfly("animal_butterfly", 0xF08A1E, 0x2A1E14, 0xFFFFFF),
    "animal_butterfly_blue": butterfly("animal_butterfly_blue", 0x3F86E8, 0x1A2A5A, 0xBFE0FF),
    "animal_butterfly_white": butterfly("animal_butterfly_white", 0xF6F2E8, 0xE8E0C8, 0x3A3A3A),
    "animal_dragonfly": dragonfly("animal_dragonfly", 0x2E8AC8, 0x7ADCB0),
    "animal_dragonfly_red": dragonfly("animal_dragonfly_red", 0xC8402E, 0xF2D23A),
    "animal_fireflies": fireflies("animal_fireflies", 0xE8FF6A),
    "animal_fireflies_blue": fireflies("animal_fireflies_blue", 0x8CF0FF),
    "animal_bees": fireflies("animal_bees", 0xF2C230, body=0x2A2018, size=1.3, seconds=3.0, spread=0.6),
    "enemy_bat_swarm": bat_swarm("enemy_bat_swarm", 0x3A2E36, 0x5A3A44),
}
