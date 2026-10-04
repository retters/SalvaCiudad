"""Elementals: a floating body of loose lumps with two arms and a head
of flames or shards, each lump on its own bone so they drift apart and
flicker. Fire (orange flames over an ember core), frost (ice shards) and
earth-and-crystal. Clips: idle (the lumps bob out of step), walk (glides),
attack (both arms thrust forward and the body flares) and die (it goes out:
the pieces sink into the ground)."""

import math

from mathutils import Vector

import _parts as P
from _parts import rock, spike, ball, box

FIRE = P.palette(core=0x3A1E14, a=0xE8501E, b=0xFF9A2A, c=0xFFE27A, eye=0xFFFFFF)
FROST = P.palette(core=0x2E4A6A, a=0x6FB8E8, b=0xA8DCF4, c=0xECFAFF, eye=0x1E3A5A)
CRYSTAL = P.palette(core=0x5A4A3A, a=0x7A6A52, b=0xB06AD8, c=0xE0B0FF, eye=0xFFE27A)

# Lumps: (bone, center, radii, material, spikes up).
LUMPS = [
    ("base", (0, 0, 0.45), (0.3, 0.3, 0.22), "a", 0),
    ("belly", (0, 0, 0.85), (0.36, 0.32, 0.3), "core", 0),
    ("chest", (0, 0, 1.35), (0.44, 0.34, 0.32), "a", 2),
    ("head", (0, -0.03, 1.85), (0.22, 0.22, 0.22), "b", 4),
    ("shoulder.L", (0.55, 0, 1.5), (0.2, 0.2, 0.18), "b", 2), ("shoulder.R", (-0.55, 0, 1.5), (0.2, 0.2, 0.18), "b", 2),
    ("arm.L", (0.72, -0.05, 1.1), (0.15, 0.16, 0.24), "a", 0), ("arm.R", (-0.72, -0.05, 1.1), (0.15, 0.16, 0.24), "a", 0),
    ("fist.L", (0.76, -0.14, 0.7), (0.17, 0.18, 0.18), "c", 0), ("fist.R", (-0.76, -0.14, 0.7), (0.17, 0.18, 0.18), "c", 0),
    ("spark.1", (0.3, 0.3, 2.1), (0.08, 0.08, 0.1), "c", 1), ("spark.2", (-0.35, 0.2, 0.3), (0.09, 0.09, 0.1), "c", 1),
    ("spark.3", (0.1, 0.4, 1.0), (0.07, 0.07, 0.09), "b", 1),
]


def body(mb):
    for i, (bone, c, r, mat, n) in enumerate(LUMPS):
        rock(mb, c, r, mat, bone, count=12, seed=i + 1, jitter=0.16)
        for j in range(n):                                    # Flames or shards rising from the lump.
            a = j * 2.4 + i
            base = Vector(c) + Vector((math.cos(a) * r[0] * 0.5, math.sin(a) * r[1] * 0.5, r[2] * 0.5))
            spike(mb, base, base + Vector((math.cos(a) * 0.08, math.sin(a) * 0.08, 0.28 + 0.08 * (j % 2))), r[0] * 0.4,
                  "c" if j % 2 else "b", bone, sides=4)
    for s in (-1, 1):
        box(mb, (s * 0.08, -0.23, 1.88), (0.06, 0.04, 0.035), "eye", "head", rotation_z=0.0)
    box(mb, (0, -0.33, 1.38), (0.2, 0.04, 0.2), "c", "chest", rotation_z=0.785)                # A heart of light.


def mech():
    bones = []
    for bone, c, r, mat, n in LUMPS:
        parent = None
        if bone.startswith("arm"):
            parent = "shoulder" + bone[3:]
        elif bone.startswith("fist"):
            parent = "arm" + bone[4:]
        bones.append((bone, (c[0], c[1], c[2] + r[2] * 0.6), (c[0], c[1], c[2] - r[2] * 0.6), parent))
    m = P.kit.Mech(bones)
    order = [b for b, *_ in LUMPS]

    def drift(t, amount=1.0, lean=0.0):
        """Every lump bobs with its own phase."""
        p = 2 * math.pi * t
        turns, moves = {}, {}
        for i, bone in enumerate(order):
            if bone.startswith(("arm", "fist")):
                continue
            ph = i * 1.7
            spark = bone.startswith("spark")
            k = (3.0 if spark else 1.0) * amount
            z = Vector(LUMPS[i][1]).z
            moves[bone] = (0.02 * k * math.sin(p + ph), 0.02 * k * math.cos(p + ph * 1.3) - lean * z * 0.2,
                           0.03 * k * math.sin(2 * p + ph))
            turns[bone] = [(P.Z, (18.0 if spark else 5.0) * math.sin(p + ph) * amount), (P.X, lean * 40.0)]
        return turns, moves

    def idle(t):
        turns, moves = drift(t)
        p = 2 * math.pi * t
        for side, s in P.SIDES:
            turns[f"arm.{side}"] = [(P.X, 5.0 * math.sin(p + s)), (P.Y, 4.0 * math.sin(2 * p) * s)]
        return turns, moves

    def glide(t):
        turns, moves = drift(t, 1.0, lean=0.35)
        p = 2 * math.pi * t
        for side, s in P.SIDES:
            turns[f"arm.{side}"] = [(P.X, 20.0 + 8.0 * math.sin(p + s))]
        return turns, moves

    def attack(t):
        w = P.pulse(t, 0.0, 0.3, 0.36, 0.46)
        s = P.pulse(t, 0.36, 0.46, 0.56, 0.95)
        turns, moves = drift(t, 1.0 + 2.0 * s, lean=-0.15 * w + 0.4 * s)
        for side, sx in P.SIDES:
            turns[f"shoulder.{side}"] = turns.get(f"shoulder.{side}", []) + [(P.X, 30.0 * w - 95.0 * s)]
            turns[f"arm.{side}"] = [(P.Y, (25.0 * w - 14.0 * s) * sx)]
            moves[f"fist.{side}"] = (0, 0, -0.3 * s)             # The fists shoot out along the arms.
        return turns, moves

    def die(t):
        a = P.smooth(t / 0.9)
        flick = math.sin(40 * t) * (1 - a)
        turns, moves = drift(t, 1.0 - a)
        for i, bone in enumerate(order):
            if bone.startswith(("arm", "fist")):
                continue
            delay = P.smooth((t - 0.08 * (i % 5)) / 0.75)
            x, y, z = moves[bone]
            top = Vector(LUMPS[i][1]).z + LUMPS[i][2][2] + 0.5
            moves[bone] = (x + 0.05 * flick, y, z - top * delay ** 1.5)
        return turns, moves

    m.clip("idle", 2.4, idle)
    m.clip("walk", 1.6, glide)
    m.clip("attack", 1.1, attack)
    m.clip("die", 1.6, die, loops=False)
    return m


def build(name, colors):
    def make():
        mb = P.kit.begin()
        body(mb)
        P.kit.save(mb, P.FAMILY, name, colors, mech=mech())
    return make


MODELS = {"monster_elemental_fire": build("monster_elemental_fire", FIRE),
          "monster_elemental_frost": build("monster_elemental_frost", FROST),
          "monster_elemental_crystal": build("monster_elemental_crystal", CRYSTAL)}
