"""Animals made of rigid parts for the proposal families: the horse and the
ox that pull the vehicles of `transport`, and the cow and the sheep of
`farm`. Each part follows one bone (kit.Mech), so a walk, a rest and a
grazing pose cost nothing to build. They are stand-ins: the game's own
animals come from art/blender/zoo.
"""

import math

import _kit as kit
import common
from _shapes import TAU, beam

C = common.rgb
COLORS = {
    "coat_brown": C(0x7A4E2E), "coat_dark": C(0x3E2C22), "coat_grey": C(0x9A968E), "coat_cream": C(0xD8C8A8),
    "coat_ox": C(0x8A5A3A), "coat_ox_white": C(0xD8D0C0), "coat_cow": C(0xECE6DA), "cow_patch": C(0x3A2C24),
    "udder": C(0xE8A8A0), "wool": C(0xF0ECE0), "wool_dark": C(0x4A4038), "sheep_face": C(0x3A3230),
    "mane_dark": C(0x2A2018), "mane_light": C(0xD8C8A0), "hoof": C(0x2E2A28), "muzzle": C(0x4A342A),
    "eye": C(0x101010), "horn": C(0xE0D8C0),
}

ANIMALS = {
    "horse": dict(z=1.28, r=0.36, long=2.25, hip=1.08, knee=0.56, leg_x=0.2, leg_y=0.56, upper=0.105, lower=0.065,
                  neck=((0, -0.62, 1.42), (0, -1.02, 1.98)), neck_r=(0.23, 0.15),
                  head=((0, -0.98, 2.02), (0, -1.46, 1.74)), head_r=(0.17, 0.095),
                  tail=((0, 0.8, 1.42), (0, 1.0, 0.7)), tail_r=(0.09, 0.04), cycle=1.0, speed=1.3, bend=38),
    "ox": dict(z=1.12, r=0.46, long=2.0, hip=0.92, knee=0.48, leg_x=0.26, leg_y=0.6, upper=0.13, lower=0.085,
               neck=((0, -0.7, 1.25), (0, -1.12, 1.4)), neck_r=(0.32, 0.25),
               head=((0, -1.06, 1.42), (0, -1.52, 1.2)), head_r=(0.23, 0.15),
               tail=((0, 0.9, 1.3), (0, 0.98, 0.55)), tail_r=(0.035, 0.03), cycle=1.3, speed=0.9, bend=30),
    "sheep": dict(z=0.56, r=0.25, long=1.45, hip=0.42, knee=0.22, leg_x=0.13, leg_y=0.25, upper=0.055, lower=0.035,
                  neck=((0, -0.3, 0.64), (0, -0.47, 0.82)), neck_r=(0.13, 0.1),
                  head=((0, -0.45, 0.84), (0, -0.7, 0.74)), head_r=(0.1, 0.065),
                  tail=((0, 0.36, 0.62), (0, 0.42, 0.46)), tail_r=(0.05, 0.03), cycle=0.8, speed=0.7, bend=30),
}
ANIMALS["cow"] = dict(ANIMALS["ox"])
LEGS = (("FL", 1, -1, 0.0), ("FR", -1, -1, 0.5), ("HL", 1, 1, 0.5), ("HR", -1, 1, 0.0))   # Name, side, end, phase.


def draft_animal(mb, y, prefix, kind="horse", coat="coat_brown", mane="mane_dark", x=0.0, harness=True, turn=0.0):
    """A horse, an ox, a cow or a sheep of rigid parts centered at (x, y),
    facing -Y (turned `turn` degrees around Z). Returns its bones and its
    poses: gait(g, swing), idle(t) and graze(t)."""
    p = ANIMALS[kind]
    body, neck, head, tail = (prefix + n for n in ("body", "neck", "head", "tail"))
    rad = math.radians(turn)
    cos, sin = math.cos(rad), math.sin(rad)
    skin = "sheep_face" if kind == "sheep" else coat
    small = p["hip"] if p["hip"] < 0.9 else 1.0   # The horse and the ox keep their measures.

    def at(point):
        return (x + point[0] * cos - point[1] * sin, y + point[0] * sin + point[1] * cos, point[2])

    wb, wn, wh, wt = {body: 1.0}, {neck: 1.0}, {head: 1.0}, {tail: 1.0}
    if turn == 0.0:
        mb.sphere(at((0, 0, p["z"])), p["r"], coat, wb, segments=8, rings=6, scale=(1.0, p["long"], 1.05))
    else:   # A turned body is built from balls, which do not mind the turn.
        for k in range(5):
            mb.sphere(at((0, p["r"] * p["long"] * (k - 2) * 0.36, p["z"])), p["r"] * 1.02, coat, wb, segments=8, rings=5, scale=(1.0, 1.0, 1.05))
    mb.sphere(at((0, -p["leg_y"], p["z"] + 0.03)), p["r"] * 1.02, coat, wb, segments=8, rings=5, scale=(1.0, 1.0, 1.12))
    mb.sphere(at((0, p["leg_y"], p["z"] + 0.04)), p["r"] * 1.05, coat, wb, segments=8, rings=5, scale=(1.0, 1.0, 1.08))
    if kind == "sheep":
        for k, (px, py, pz) in enumerate(((0.12, -0.2, 0.2), (-0.12, 0.0, 0.22), (0.1, 0.2, 0.2), (0, -0.05, 0.26), (-0.1, -0.24, 0.16), (0.02, 0.28, 0.14))):
            mb.sphere(at((px, py, p["z"] + pz)), 0.14, coat, wb, segments=6, rings=4)
    if kind == "cow":
        for px, py, pz, r in ((0.3, -0.25, 0.25, 0.26), (-0.32, 0.3, 0.2, 0.3), (0.28, 0.55, 0.3, 0.22), (-0.2, -0.6, 0.32, 0.2)):
            mb.sphere(at((px, py, p["z"] + pz * 0.6)), r, "cow_patch", wb, segments=6, rings=4, scale=(0.75, 1.0, 0.75))
        mb.sphere(at((0, 0.42, p["z"] - 0.42)), 0.17, "udder", wb, segments=6, rings=4)
    mb.cylinder(at(p["neck"][0]), at(p["neck"][1]), p["neck_r"][0], p["neck_r"][1], coat, wn, segments=7)
    mb.cylinder(at(p["head"][0]), at(p["head"][1]), p["head_r"][0], p["head_r"][1], skin, wh, segments=6)
    h0, h1 = p["head"]
    tip = (h1[0], h1[1] - 0.02, h1[2] - 0.01)
    mb.sphere(at(tip), p["head_r"][1] * 1.05, "muzzle", wh, segments=6, rings=4)
    for side in (-1, 1):
        mb.box(at((side * p["head_r"][0] * 0.82, h0[1] - 0.14 * (0.6 if kind == "sheep" else 1.0), h0[2] - 0.05 * (0.6 if kind == "sheep" else 1.0))),
               (0.03, 0.06, 0.05) if kind != "sheep" else (0.02, 0.03, 0.03), "eye", wh, rotation_z=rad)
        ear = (side * p["head_r"][0] * 0.6, h0[1] + 0.02, h0[2] + p["head_r"][0] * 0.7)
        if kind == "horse":
            mb.cylinder(at(ear), at((ear[0] * 1.3, ear[1] + 0.02, ear[2] + 0.2)), 0.05, 0.0, coat, wh, segments=4)
        elif kind == "sheep":
            mb.cylinder(at((ear[0] * 1.4, ear[1] + 0.03, ear[2] - 0.06)), at((ear[0] * 2.6, ear[1] + 0.05, ear[2] - 0.1)), 0.035, 0.012, skin, wh, segments=4)
        else:
            mb.cylinder(at((ear[0] * 1.6, ear[1] + 0.06, ear[2] - 0.12)), at((ear[0] * 2.6, ear[1] + 0.08, ear[2] - 0.16)),
                        0.06, 0.02, coat, wh, segments=4)
            horn = 0.45 if kind == "ox" else 0.3
            mb.cylinder(at(ear), at((side * horn, ear[1] - 0.1, ear[2] + (0.3 if kind == "ox" else 0.16))), 0.055 if kind == "ox" else 0.04, 0.0, "horn", wh, segments=5)
    n0, n1 = p["neck"]
    if kind == "horse":
        for k in range(5):   # The mane, along the top of the neck.
            u = k / 4
            mb.box(at((0, n0[1] + (n1[1] - n0[1]) * u + 0.14, n0[2] + (n1[2] - n0[2]) * u + 0.17)), (0.07, 0.16, 0.22), mane, wn, rotation_z=rad)
        mb.box(at((0, h0[1] - 0.08, h0[2] + 0.16)), (0.08, 0.2, 0.1), mane, wh, rotation_z=rad)
    if kind == "sheep":
        mb.sphere(at((0, h0[1] + 0.03, h0[2] + 0.07)), 0.1, coat, wh, segments=6, rings=4)
    t0, t1 = p["tail"]
    mb.cylinder(at(t0), at(t1), p["tail_r"][0], p["tail_r"][1], mane if kind == "horse" else coat, wt, segments=5)
    if kind in ("ox", "cow"):
        mb.sphere(at(t1), 0.07, mane, wt, segments=5, rings=3, scale=(1, 1, 1.6))
    bones = [(body, at((0, 0.3, p["z"])), at((0, -0.3, p["z"])), None),
             (neck, at(n0), at(n1), body), (head, at(h0), at(h1), neck), (tail, at(t0), at(t1), body)]
    for name, side, end, _phase in LEGS:
        lx, ly = side * p["leg_x"], end * p["leg_y"]
        up, low = prefix + "leg_" + name + "_u", prefix + "leg_" + name + "_l"
        mb.cylinder(at((lx, ly, p["hip"] + 0.12 * small)), at((lx, ly, p["knee"])), p["upper"], p["upper"] * 0.7, skin if kind == "sheep" else coat, {up: 1.0}, segments=6)
        mb.cylinder(at((lx, ly, p["knee"] + 0.03)), at((lx, ly, 0.09 * small)), p["lower"] * 1.05, p["lower"] * 0.85, skin, {low: 1.0}, segments=6)
        mb.cylinder(at((lx, ly, 0.09 * small)), at((lx, ly, 0.0)), p["lower"] * 1.15, p["lower"] * 1.3, "hoof", {low: 1.0}, segments=6)
        bones.append((up, at((lx, ly, p["hip"])), at((lx, ly, p["knee"])), body))
        bones.append((low, at((lx, ly, p["knee"])), at((lx, ly, 0.0)), up))
    if harness:   # A collar and a girth.
        for yy, rr in ((-p["leg_y"] - 0.02, p["r"] * 1.2), (0.05, p["r"] * 1.12)):
            for i in range(8):
                a0, a1 = TAU * i / 8, TAU * (i + 1) / 8
                beam(mb, at((math.cos(a0) * rr, yy, p["z"] + 0.04 + math.sin(a0) * rr * 1.08)),
                     at((math.cos(a1) * rr, yy, p["z"] + 0.04 + math.sin(a1) * rr * 1.08)), 0.035, "leather", wb)
    # The axis the legs swing around and the one the tail wags around, turned with the animal.
    side_axis, long_axis = (cos, sin, 0.0), (-sin, cos, 0.0)

    def gait(g, swing):
        turns, moves = {}, {}
        for name, _side, _end, phase in LEGS:
            th = TAU * (g + phase)
            turns[prefix + "leg_" + name + "_u"] = [(side_axis, swing * math.sin(th))]
            turns[prefix + "leg_" + name + "_l"] = [(side_axis, p["bend"] * max(0.0, -math.cos(th)))]
        moves[body] = (0, 0, 0.025 * math.sin(2 * TAU * g))
        turns[neck] = [(side_axis, 4.0 * math.sin(2 * TAU * g))]
        turns[tail] = [(long_axis, 9.0 * math.sin(TAU * g))]
        return turns, moves

    def idle(t):
        return {neck: [(side_axis, 5.0 * math.sin(TAU * t))], head: [(side_axis, 6.0 * math.sin(TAU * t + 1.0))],
                tail: [(long_axis, 20.0 * math.sin(TAU * 2 * t)), (side_axis, 6.0 * math.sin(TAU * t))]}, {}

    def graze(t, phase=0.0):
        down = 0.5 + 0.5 * math.sin(TAU * t + phase)          # Head down to the grass, and up to look around.
        reach = {"horse": 62.0, "ox": 38.0, "cow": 38.0, "sheep": 50.0}[kind]
        return {neck: [(side_axis, -reach * (0.35 + 0.65 * down))], head: [(side_axis, -18.0 * down + 5.0 * math.sin(TAU * 6 * t + phase))],
                tail: [(long_axis, 18.0 * math.sin(TAU * 3 * t + phase))]}, {}

    return {"bones": bones, "gait": gait, "idle": idle, "graze": graze, "hip": p["hip"], "cycle": p["cycle"], "speed": p["speed"]}
