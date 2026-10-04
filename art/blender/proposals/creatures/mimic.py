"""Mimic: a treasure chest that is a monster. Closed it is a plain chest of
planks with iron straps; open it shows teeth on both rims, a red mouth, two
yellow eyes and a long tongue. Clips: idle (closed; now and then the lid
lifts a crack), open (the bite: it gapes, lunges and snaps shut), walk (it
hops) and die (falls open, tongue out). Variants: oak with iron, dark wood
with gold."""

import math

from mathutils import Vector

import _parts as P
from _parts import X, Y, Pose, hull, bar, box, spike, ball

W, D, H = 1.0, 0.62, 0.42           # Width, depth and height of the box without the lid.
ARCH = [(-0.31, 0.42), (-0.31, 0.5), (-0.2, 0.62), (0.0, 0.67), (0.2, 0.62), (0.31, 0.5), (0.31, 0.42)]

OAK = P.palette(wood=0x8A6038, wood_dark=0x6B4628, iron=0x44484E, lock=0xD9B24A, mouth=0x8A2A30, tooth=0xF2EAD6,
                tongue=0xE0707E, eye=0xF4D23A, pupil=0x1A1210)
DARK = P.palette(wood=0x4A3428, wood_dark=0x35241C, iron=0xC9A23A, lock=0xE8E2D0, mouth=0x5A1F4A, tooth=0xF2EAD6,
                 tongue=0xB86AD0, eye=0x7CFFB0, pupil=0x101A12)


def arch(mb, x0, x1, mat, grow=1.0):
    pts = [(x, y * (1 + (grow - 1) * 0.5), H + (z - H) * grow) for x in (x0, x1) for y, z in ARCH]
    return hull(mb, pts, mat, "lid")


def body(mb):
    box(mb, (0, -0.29, 0.21), (W, 0.04, H), "wood", "body")
    box(mb, (0, 0.29, 0.21), (W, 0.04, H), "wood", "body")
    for s in (-1, 1):
        box(mb, (s * 0.48, 0, 0.21), (0.04, 0.54, H), "wood", "body")
        box(mb, (s * 0.495, s * 0, 0.21), (0.02, 0.5, 0.06), "wood_dark", "body")
        for y in (-0.3, 0.3):
            box(mb, (s * 0.49, y, 0.215), (0.07, 0.07, H + 0.01), "iron", "body")
        box(mb, (s * 0.3, -0.315, 0.21), (0.08, 0.02, H), "iron", "body")
        box(mb, (s * 0.3, 0.315, 0.21), (0.08, 0.02, H), "iron", "body")
    box(mb, (0, 0, 0.03), (W, D, 0.06), "wood_dark", "body")
    box(mb, (0, 0, 0.07), (0.92, 0.54, 0.02), "mouth", "body")
    box(mb, (0, -0.322, 0.34), (0.14, 0.03, 0.14), "lock", "body")
    box(mb, (0, -0.34, 0.33), (0.03, 0.01, 0.05), "pupil", "body")                # Keyhole.
    # Plank lines on the front and the back.
    for z in (0.15, 0.28):
        box(mb, (0, -0.312, z), (0.5, 0.008, 0.012), "wood_dark", "body")
        box(mb, (0, 0.312, z), (0.5, 0.008, 0.012), "wood_dark", "body")
    # Lid.
    arch(mb, -0.5, 0.5, "wood")
    for x in (-0.3, 0.3):
        arch(mb, x - 0.04, x + 0.04, "iron", grow=1.07)
    for x in (-0.5, 0.5):
        arch(mb, x - 0.012, x + 0.012, "iron", grow=1.05)
    box(mb, (0, 0, 0.412), (0.9, 0.52, 0.02), "mouth", "lid")
    box(mb, (0, -0.322, 0.455), (0.1, 0.03, 0.09), "lock", "lid")
    # Teeth: the lower ones stand on the rim (inside the lid when closed),
    # the upper ones hang from the lid (inside the box when closed).
    for i in range(6):
        x = -0.4 + i * 0.16
        spike(mb, (x, -0.272, 0.415), (x, -0.27, 0.5), 0.03, "tooth", "body")
        spike(mb, (x + 0.08, -0.225, 0.42), (x + 0.08, -0.23, 0.3), 0.03, "tooth", "lid") if i < 5 else None
    for s in (-1, 1):
        for y in (-0.14, 0.04):
            spike(mb, (s * 0.462, y, 0.415), (s * 0.46, y, 0.49), 0.028, "tooth", "body")
            spike(mb, (s * 0.415, y + 0.09, 0.42), (s * 0.42, y + 0.09, 0.32), 0.028, "tooth", "lid")
        ball(mb, (s * 0.17, 0.2, 0.3), 0.06, "eye", "body", segments=8, rings=5)
        ball(mb, (s * 0.17, 0.15, 0.3), 0.025, "pupil", "body", scale=(0.6, 1, 1.6))
    # Tongue, curled on the floor of the box.
    bar(mb, (0, 0.2, 0.12), (0, -0.05, 0.13), 0.2, 0.05, "tongue", "tongue.1")
    bar(mb, (0, -0.05, 0.13), (0, -0.25, 0.14), 0.2, 0.05, "tongue", "tongue.2", taper=0.55)


def mech():
    m = P.kit.Mech([
        ("body", (0, 0, 0), (0, 0, 0.4), None),
        ("lid", (0, 0.31, 0.42), (0, -0.31, 0.42), "body"),
        ("tongue.1", (0, 0.2, 0.12), (0, -0.05, 0.13), "body"),
        ("tongue.2", (0, -0.05, 0.13), (0, -0.25, 0.14), "tongue.1"),
    ])

    def tilt(deg, lift=0.0, side=0.0):
        """Body turns keeping its base on the ground."""
        dz = 0.33 * abs(math.sin(math.radians(deg))) + 0.5 * abs(math.sin(math.radians(side))) + lift
        return [(X, deg), (Y, side)], dz

    def idle(t):
        peek = P.pulse(t, 0.5, 0.56, 0.72, 0.78)
        shiver = math.sin(60 * t) * P.pulse(t, 0.2, 0.22, 0.26, 0.3)
        turn, dz = tilt(0.6 * shiver)
        return ({"body": turn, "lid": [(X, -9.0 * peek)]}, {"root": (0, 0, dz)})

    def bite(t):
        gape = P.pulse(t, 0.0, 0.3, 0.48, 0.56)      # Opens wide, leaning back.
        lunge = P.pulse(t, 0.36, 0.5, 0.58, 0.95)    # Throws itself forward.
        tongue = P.pulse(t, 0.15, 0.34, 0.44, 0.54)
        turn, dz = tilt(-12.0 * gape * (1 - lunge) + 14.0 * lunge, lift=0.12 * math.sin(math.pi * lunge))
        return ({"body": turn, "lid": [(X, -75.0 * gape)],
                 "tongue.1": [(X, -38.0 * tongue)], "tongue.2": [(X, 22.0 * tongue * math.sin(12 * t))]},
                {"root": (0, 0.06 * gape - 0.3 * lunge, dz), "tongue.1": (0, -0.12 * tongue, 0.2 * tongue)})

    def hop(t):
        squat = P.pulse(t, 0.0, 0.12, 0.16, 0.24)
        u = max(0.0, min(1.0, (t - 0.2) / 0.55))
        air = math.sin(math.pi * u)
        land = P.pulse(t, 0.74, 0.8, 0.84, 1.0)
        turn, dz = tilt(-7.0 * squat + 10.0 * air * (0.5 - u) * 2 + 4.0 * land, lift=0.3 * air)
        return ({"body": turn, "lid": [(X, -20.0 * air - 6.0 * land)]}, {"root": (0, 0, dz)})

    def die(t):
        a = P.smooth(t / 0.35)
        b = P.smooth((t - 0.3) / 0.5)
        bounce = math.sin(math.pi * min(1.0, t / 0.3)) * 0.1
        turn, dz = tilt(0.0, lift=bounce, side=9.0 * b)
        return ({"body": turn, "lid": [(X, -118.0 * a + 8.0 * math.sin(math.pi * b) * (1 - b))],
                 "tongue.1": [(X, -30.0 * b)], "tongue.2": [(X, 75.0 * b)]},
                {"root": (0, 0, dz), "tongue.1": (0, -0.2 * b, 0.27 * b)})

    m.clip("idle", 4.0, idle)
    m.clip("open", 1.2, bite)
    m.clip("walk", 0.7, hop)
    m.clip("die", 1.2, die, loops=False)
    return m


def build(name, colors, k=1.0):
    def make():
        mb = P.kit.begin()
        body(mb)
        P.save(mb, name, colors, mech(), k)
    return make


MODELS = {"monster_mimic": build("monster_mimic", OAK), "monster_mimic_dark": build("monster_mimic_dark", DARK),
          "monster_mimic_small": build("monster_mimic_small", OAK, k=0.55)}
