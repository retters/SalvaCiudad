"""Cat-folk: stacked cubes of warm stucco with roof terraces to lie in the
sun, striped awnings, green onion domes, cushions and climbing posts."""

import math

import rparts as p
from rparts import TAU, face

DOME = ("c_dome", "c_dome_dark")
STRIPES = (("aw_red", "aw_white"), ("aw_yellow", "aw_green"), ("aw_blue", "aw_white"), ("aw_yellow", "aw_red"))


def cube(mb, cx, cy, z0, w, d, h, parapet=0.45, vigas=True):
    """A stucco block with a terrace on top behind a low parapet with
    stepped corners, and beam ends that poke out under it."""
    mb.box((cx, cy, z0 + h / 2), (w, d, h), "stucco")
    mb.box((cx, cy, z0 + 0.2), (w + 0.12, d + 0.12, 0.4), "stucco_dark")
    mb.box((cx, cy, z0 + h - 0.02), (w - 0.3, d - 0.3, 0.06), "terracotta")
    if parapet:
        for sx in (-1, 1):
            mb.box((cx + sx * (w / 2 - 0.09), cy, z0 + h + parapet / 2), (0.18, d, parapet), "stucco_light")
            mb.box((cx, cy + sx * (d / 2 - 0.09), z0 + h + parapet / 2), (w, 0.18, parapet), "stucco_light")
            for sy in (-1, 1):
                mb.box((cx + sx * (w / 2 - 0.2), cy + sy * (d / 2 - 0.2), z0 + h + parapet + 0.12), (0.44, 0.44, 0.24), "stucco_light")
                mb.box((cx + sx * (w / 2 - 0.2), cy + sy * (d / 2 - 0.2), z0 + h + parapet + 0.32), (0.24, 0.24, 0.18), "stucco")
    if vigas:
        n = max(2, round(w / 0.9))
        for i in range(n):
            x = cx - w / 2 + w * (i + 0.5) / n
            mb.cylinder((x, cy - d / 2 - 0.28, z0 + h - 0.35), (x, cy + d / 2 + 0.28, z0 + h - 0.35), 0.075, 0.075, "c_timber", segments=5)
    return z0 + h


def door(mb, x=0.0, z=0.0, w=0.95, h=1.75):
    p.arch_door(mb, x, z, w, h, "stucco_light", "c_timber", None)
    mb.sphere((x + w * 0.28, -0.13, z + h * 0.45), 0.05, "gold", segments=5, rings=3)
    mb.box((x, -0.32, z + 0.06), (w + 0.5, 0.6, 0.12), "stucco_dark")


def cushion(mb, x, y, z, mat="aw_red", r=0.3):
    mb.sphere((x, y, z + r * 0.35), r, mat, segments=7, rings=4, scale=(1, 1, 0.38))


def pot(mb, x, y, z=0.0, s=1.0, plant=True):
    p.lathe(mb, x, y, z, [(0.14 * s, 0), (0.26 * s, 0.2 * s), (0.2 * s, 0.42 * s), (0.24 * s, 0.5 * s)], ("terracotta", "terracotta_dark", "terracotta"), 7)
    if plant:
        mb.sphere((x, y, z + 0.62 * s), 0.24 * s, "leaf", segments=5, rings=3)


def climb_post(mb, x, y, h=3.2, steps=3, z=0.0):
    """A post wrapped in sisal with round perches and a cushion on top."""
    mb.cylinder((x, y, z), (x, y, z + h), 0.12, 0.11, "sisal", segments=7)
    mb.cylinder((x, y, z), (x, y, z + 0.12), 0.4, 0.36, "c_timber", segments=8)
    for k in range(steps):
        a = TAU * k / steps + 0.6
        zz = z + h * (k + 1) / (steps + 0.5)
        px, py = x + math.cos(a) * 0.42, y + math.sin(a) * 0.42
        mb.cylinder((px, py, zz), (px, py, zz + 0.08), 0.36, 0.36, "c_timber", segments=8)
        p.beam(mb, (x, y, zz - 0.35), (px + math.cos(a) * 0.2, py + math.sin(a) * 0.2, zz), 0.06, "c_timber")
    mb.cylinder((x, y, z + h), (x, y, z + h + 0.08), 0.46, 0.46, "c_timber", segments=8)
    cushion(mb, x, y, z + h + 0.08, "aw_blue", 0.34)


def ladder(mb, x, y, z0, z1, rot=0.0, w=0.5):
    """A ladder that leans back toward local +Y."""
    with mb.placed((x, y, 0), rot):
        run = (z1 - z0) * 0.25
        for s in (-1, 1):
            p.beam(mb, (s * w / 2, -run, z0), (s * w / 2, 0, z1 + 0.3), 0.07, "c_timber")
        n = max(2, round((z1 - z0) / 0.32))
        for k in range(n):
            u = (k + 0.7) / n
            mb.box((0, -run * (1 - u), z0 + (z1 - z0) * u), (w, 0.05, 0.05), "c_timber")


def fish_rack(mb, x, y, w=1.6, rot=0.0, z=0.0):
    with mb.placed((x, y, z), rot):
        for s in (-1, 1):
            p.beam(mb, (s * w / 2, 0, 0), (s * w / 2, 0, 1.5), 0.07, "c_timber")
        p.beam(mb, (-w / 2 - 0.1, 0, 1.45), (w / 2 + 0.1, 0, 1.45), 0.05, "c_timber")
        n = max(2, round(w / 0.28))
        for k in range(n):
            fx = -w / 2 + w * (k + 0.5) / n
            mb.sphere((fx, 0, 1.15), 0.2, "fish", segments=5, rings=4, scale=(0.3, 0.16, 1.0))
            p.prism_xz(mb, [(fx - 0.09, 0.86), (fx + 0.09, 0.86), (fx, 0.98)], -0.02, 0.02, "fish")


def turret(mb, x, y, z0, r, h, windows=3, seg=9):
    """A round turret with an onion dome; returns the dome's base height."""
    mb.cylinder((x, y, z0), (x, y, z0 + h), r, r, "stucco", segments=seg)
    mb.cylinder((x, y, z0 + h - 0.12), (x, y, z0 + h + 0.1), r + 0.14, r + 0.14, "stucco_light", segments=seg)
    for k in range(windows):
        a = -math.pi / 2 + TAU * k / windows
        with mb.placed((x + math.cos(a) * r * 0.94, y + math.sin(a) * r * 0.94, z0), a + math.pi / 2):
            p.arch_door(mb, 0, h * 0.45, 0.4, 0.9, "stucco_light", "window", None, 0.1)
    p.onion(mb, x, y, z0 + h + 0.1, r * 0.95, DOME, seg + 1)
    return z0 + h + 0.1


def pergola(mb, cx, cy, z, w, d, h=1.9, mats=STRIPES[1]):
    """Four poles and a striped cloth over a terrace."""
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.cylinder((cx + sx * w / 2, cy + sy * d / 2, z), (cx + sx * w / 2, cy + sy * d / 2, z + h + (0.3 if sy > 0 else 0)), 0.05, 0.05, "c_timber", segments=5)
    n = max(2, round(w / 0.45))
    for i in range(n):
        x0, x1 = cx - w / 2 - 0.15 + (w + 0.3) * i / n, cx - w / 2 - 0.15 + (w + 0.3) * (i + 1) / n
        p.solid(mb, [(x0, cy - d / 2 - 0.2, z + h), (x1, cy - d / 2 - 0.2, z + h), (x1, cy + d / 2 + 0.2, z + h + 0.3), (x0, cy + d / 2 + 0.2, z + h + 0.3)], (0, 0, 0.04), mats[i % 2])


def house(level):
    def build():
        mb = p.begin()
        rig = p.Rig()
        if level == 1:
            w, d, h = 3.4, 3.0, 2.4
            cube(mb, 0, 0.3, 0, w, d, h)
            with face(mb, 0, 0.3, w, d, "front"):
                door(mb, -0.6)
                p.round_win(mb, 0.95, 1.5, 0.3, "c_timber", "window")
                p.awning(mb, -0.6, 2.25, 1.6, 0.9, 0.4, STRIPES[0])
            ladder(mb, 1.95, 0.6, 0, h + 0.45, -math.pi / 2)
            cushion(mb, 0.5, 0.5, h, "aw_red", 0.36)
            cushion(mb, -0.6, 0.9, h, "aw_yellow", 0.3)
            pot(mb, -1.5, -1.5)
            pot(mb, 1.2, -1.45, 0, 0.8)
            fish_rack(mb, -0.5, 1.1, 1.2, 0.0, h)
        elif level == 2:
            w, d, h = 5.2, 4.0, 2.6
            cy = 0.3
            cube(mb, 0, cy, 0, w, d, h)
            cube(mb, 1.2, cy + 0.6, h, 2.6, 2.6, 2.2, 0.35)
            with face(mb, 0, cy, w, d, "front"):
                door(mb, -1.2)
                p.round_win(mb, 0.4, 1.5, 0.32, "c_timber", "window")
                p.round_win(mb, 1.7, 1.5, 0.32, "c_timber", "window")
                p.awning(mb, -1.2, 2.4, 1.8, 1.0, 0.45, STRIPES[0])
            with face(mb, 1.2, cy + 0.6, 2.6, 2.6, "front", h):
                p.arch_door(mb, 0, 0, 0.7, 1.5, "stucco_light", "dark", None)
                p.awning(mb, 0, 2.0, 1.6, 0.8, 0.35, STRIPES[1])
            turret(mb, 1.2, cy + 0.6, h + 2.2, 0.75, 0.9, 2)
            pergola(mb, -1.5, cy - 0.3, h, 1.7, 2.0, 1.8, STRIPES[2])
            cushion(mb, -1.6, cy - 0.5, h, "aw_red", 0.4)
            cushion(mb, -1.2, cy + 0.3, h, "aw_yellow", 0.32)
            ladder(mb, -2.85, cy + 0.6, 0, h + 0.45, math.pi / 2)
            climb_post(mb, 2.3, -2.0, 2.4, 2)
            pot(mb, -2.3, -2.0)
            pot(mb, -0.2, -1.95, 0, 0.8)
            p.hang_lantern(mb, rig, 0.25, cy - d / 2 - 0.25, 2.2, 0.15, "cage", "window", "c_timber")
            p.beam(mb, (0.25, cy - d / 2, 2.2), (0.25, cy - d / 2 - 0.3, 2.2), 0.05, "c_timber")
        else:
            w, d, h = 7.2, 4.8, 2.8
            cy = 0.4
            cube(mb, 0, cy, 0, w, d, h)
            cube(mb, -1.2, cy + 0.6, h, 4.4, 3.4, 2.4, 0.4)
            with face(mb, 0, cy, w, d, "front"):
                for k in range(3):                                              # A loggia of three arches.
                    p.arch_door(mb, -2.3 + 1.5 * k, 0, 1.1, 2.1, "stucco_light", "dark", None, 0.14)
                door(mb, -2.3)
                p.round_win(mb, 1.9, 1.6, 0.36, "c_timber", "window")
                p.round_win(mb, 2.9, 1.6, 0.36, "c_timber", "window")
                p.awning(mb, 2.4, 2.6, 2.0, 1.1, 0.5, STRIPES[0], "c_timber")
            with face(mb, 0, cy, w, d, "right"):
                p.round_win(mb, 0, 1.6, 0.36, "c_timber", "window")
                p.awning(mb, 0, 2.5, 1.8, 0.9, 0.4, STRIPES[3])
            with face(mb, -1.2, cy + 0.6, 4.4, 3.4, "front", h):
                p.arch_door(mb, -1.0, 0, 0.8, 1.6, "stucco_light", "c_timber", None)
                p.round_win(mb, 0.6, 1.3, 0.3, "c_timber", "window")
                p.awning(mb, -1.0, 2.15, 1.8, 0.9, 0.4, STRIPES[1])
            turret(mb, 0.1, cy + 1.3, h + 2.4, 1.0, 1.5, 3)
            pergola(mb, 2.4, cy + 0.2, h, 1.8, 2.4, 1.9, STRIPES[2])
            cushion(mb, 2.2, cy, h, "aw_red", 0.42)
            cushion(mb, 2.8, cy + 0.8, h, "aw_yellow", 0.34)
            cushion(mb, -2.6, cy + 0.4, h + 2.4, "aw_blue", 0.36)
            fish_rack(mb, -1.9, cy + 1.7, 1.4, 0.0, h + 2.4)
            climb_post(mb, 3.2, -2.3, 3.2, 3)
            ladder(mb, 0.7, cy - 1.15, h, h + 2.4 + 0.4, 0.0)
            pot(mb, -3.3, -2.3, 0, 1.1)
            pot(mb, 0.3, -2.3, 0, 0.9)
            pot(mb, 0.9, cy - 1.9, h, 0.8)
            for x in (-0.8, 1.2):
                p.beam(mb, (x, cy - d / 2, 2.45), (x, cy - d / 2 - 0.35, 2.45), 0.05, "c_timber")
                p.hang_lantern(mb, rig, x, cy - d / 2 - 0.3, 2.45, 0.15, "cage", "window", "c_timber")
        p.finish(mb, "race_cat_house_%d" % level, rig)
    return build


def center():
    """The sun palace: a great onion dome between four turrets, 12 x 12 m."""
    mb = p.begin()
    rig = p.Rig()
    w, d, h = 10.0, 8.0, 3.4
    cy = 0.8
    mb.box((0, cy - 0.3, 0.25), (w + 1.2, d + 1.8, 0.5), "stucco_dark")
    cube(mb, 0, cy, 0.5, w, d, h, 0.5)
    with face(mb, 0, cy, w, d, "front", 0.5):
        for k in range(5):                                                      # The arcade.
            p.arch_door(mb, -3.2 + 1.6 * k, 0, 1.15, 2.4, "stucco_light", "c_timber" if k == 2 else "dark", None, 0.16)
        p.sun_disc(mb, 0, -0.2, 3.0, 0.36, "gold", 8, "aw_red")
        for sx in (-1, 1):
            p.awning(mb, sx * 3.2, 3.0, 2.4, 1.2, 0.5, STRIPES[0] if sx < 0 else STRIPES[3], "c_timber")
    for side in ("left", "right"):
        with face(mb, 0, cy, w, d, side, 0.5):
            for x in (-2.4, 0, 2.4):
                p.round_win(mb, x, 1.9, 0.4, "c_timber", "window")
            p.awning(mb, 0, 3.0, 2.6, 1.0, 0.45, STRIPES[1])
    p.stairs(mb, 0, cy - d / 2 - 1.9, 0, 0.5, 4.0, 1.0, "stucco_dark", 0.17)
    z = h + 0.5
    cube(mb, 0, cy + 0.4, z, 6.0, 5.0, 2.2, 0.4)                                 # The upper hall and the drum of the dome.
    with face(mb, 0, cy + 0.4, 6.0, 5.0, "front", z):
        for x in (-2.0, 0, 2.0):
            p.arch_door(mb, x, 0.3, 0.7, 1.4, "stucco_light", "window", None, 0.1)
    mb.cylinder((0, cy + 0.4, z + 2.2), (0, cy + 0.4, z + 3.8), 2.4, 2.4, "stucco", segments=12)
    mb.cylinder((0, cy + 0.4, z + 3.7), (0, cy + 0.4, z + 3.95), 2.6, 2.6, "stucco_light", segments=12)
    for k in range(12):
        a = TAU * (k + 0.5) / 12
        with mb.placed((math.cos(a) * 2.32, cy + 0.4 + math.sin(a) * 2.32, z + 2.2), a + math.pi / 2):
            p.arch_door(mb, 0, 0.3, 0.45, 0.95, "stucco_light", "window", None, 0.1)
    top = p.onion(mb, 0, cy + 0.4, z + 3.95, 2.4, DOME, 12, None)
    mb.cylinder((0, cy + 0.4, top - 0.4), (0, cy + 0.4, top + 1.2), 0.08, 0.0, "gold", segments=6)
    with mb.bone("sun"):                                                        # A gold sun turns on the tip.
        p.sun_disc(mb, 0, cy + 0.4, top + 0.6, 0.4, "gold", 8, "gold")
    p.spin(mb, rig, "sun", (0, cy + 0.4, top + 0.6), (0, 0, 1), 10.0, "turn")
    for sx in (-1, 1):
        for sy in (-1, 1):                                                      # Corner turrets.
            tx, ty = sx * (w / 2 - 0.1), cy + sy * (d / 2 - 0.1)
            mb.cylinder((tx, ty, 0), (tx, ty, 5.4), 1.15, 1.05, "stucco", segments=9)
            mb.cylinder((tx, ty, 0), (tx, ty, 0.6), 1.3, 1.2, "stucco_dark", segments=9)
            turret(mb, tx, ty, 5.4, 1.05, 1.6, 3)
            if sy < 0:
                p.flag(mb, rig, tx, ty, 5.4 + 1.7 + 1.0 * 2.7, 1.6, 1.1, 0.5, "aw_red", "aw_yellow", pole_mat="c_timber")
    for sx in (-1, 1):
        pergola(mb, sx * 3.9, cy - 2.0, z, 1.6, 2.2, 1.9, STRIPES[2] if sx < 0 else STRIPES[1])
        cushion(mb, sx * 3.9, cy - 2.2, z, "aw_red", 0.44)
        cushion(mb, sx * 3.6, cy - 1.4, z, "aw_yellow", 0.34)
        climb_post(mb, sx * 2.6, cy - d / 2 - 2.3, 3.4, 3)
        pot(mb, sx * 4.3, cy - d / 2 - 0.8, 0.5, 1.2)
        p.beam(mb, (sx * 0.8, cy - d / 2, 3.4), (sx * 0.8, cy - d / 2 - 0.4, 3.4), 0.05, "c_timber")
        p.hang_lantern(mb, rig, sx * 0.8, cy - d / 2 - 0.35, 3.4, 0.2, "cage", "window", "c_timber", 1.2)
    mb.cylinder((0, cy - d / 2 - 3.6, 0), (0, cy - d / 2 - 3.6, 0.45), 1.3, 1.2, "stucco_light", segments=10)     # The fish fountain.
    mb.cylinder((0, cy - d / 2 - 3.6, 0.35), (0, cy - d / 2 - 3.6, 0.47), 1.05, 1.05, "water", segments=10)
    mb.cylinder((0, cy - d / 2 - 3.6, 0.4), (0, cy - d / 2 - 3.6, 1.2), 0.16, 0.12, "stucco", segments=6)
    mb.sphere((0, cy - d / 2 - 3.6, 1.45), 0.36, "gold", segments=6, rings=5, scale=(1.5, 0.5, 1.0))
    p.prism_xz(mb, [(0.45, 1.45), (0.85, 1.75), (0.85, 1.15)], cy - d / 2 - 3.65, cy - d / 2 - 3.55, "gold")
    p.finish(mb, "race_cat_center", rig)


def workshop():
    """The spinners' and fish-driers' house: wool, wheel and racks in the shade."""
    mb = p.begin()
    rig = p.Rig()
    w, d, h = 4.6, 3.0, 2.5
    cy = 1.0
    cube(mb, 0, cy, 0, w, d, h)
    with face(mb, 0, cy, w, d, "front"):
        p.arch_door(mb, 1.2, 0, 1.3, 2.0, "stucco_light", "dark", None, 0.14)
        p.round_win(mb, -1.2, 1.5, 0.36, "c_timber", "window")
        p.awning(mb, 0, 2.4, 4.4, 2.0, 0.6, STRIPES[1], "c_timber")
    for k, (x, y, r, mat) in enumerate(((-1.7, -0.9, 0.34, "aw_red"), (-1.1, -1.2, 0.28, "aw_blue"), (-1.45, -1.45, 0.24, "aw_yellow"), (-1.35, -1.0, 0.22, "aw_white"))):
        mb.sphere((x, y, r + (0.42 if k == 3 else 0)), r, mat, segments=7, rings=5)                 # Balls of yarn.
    mb.box((0.4, -0.9, 0.3), (1.1, 0.4, 0.08), "c_timber")                       # The spinning wheel.
    for sx in (-0.4, 0.4):
        mb.box((0.4 + sx, -0.9, 0.15), (0.08, 0.36, 0.3), "c_timber")
    for sy in (-1, 1):
        p.beam(mb, (0.75, -0.9 + sy * 0.12, 0.3), (0.75, -0.9 + sy * 0.12, 1.0), 0.06, "c_timber")
    with mb.bone("wheel"):
        p.ring(mb, 0.75, -0.9, 1.0, 0.5, 0.06, "c_timber", 12, "y")
        for k in range(6):
            a = TAU * k / 6
            p.beam(mb, (0.75, -0.9, 1.0), (0.75 + math.cos(a) * 0.5, -0.9, 1.0 + math.sin(a) * 0.5), 0.035, "c_timber")
    p.spin(mb, rig, "wheel", (0.75, -0.9, 1.0), (0, 1, 0), 3.0, "turn", (0.75, -0.6, 1.0))
    mb.cylinder((0.0, -0.9, 0.34), (0.0, -0.9, 0.7), 0.03, 0.03, "c_timber", segments=4)
    mb.sphere((0.0, -0.9, 0.75), 0.1, "aw_white", segments=5, rings=4)
    fish_rack(mb, 2.9, -0.2, 1.8, math.pi / 2)
    fish_rack(mb, 0.4, 1.2, 1.6, 0.0, h)
    mb.cylinder((-2.9, -0.4, 0), (-2.9, -0.4, 0.5), 0.34, 0.4, "terracotta", segments=8)     # A tub of the day's catch.
    for k in range(4):
        mb.sphere((-2.9 + 0.12 * math.cos(k * 1.6), -0.4 + 0.12 * math.sin(k * 1.6), 0.52), 0.16, "fish", segments=5, rings=3, scale=(1, 0.4, 0.5))
    cushion(mb, -1.2, cy, h, "aw_red", 0.36)
    climb_post(mb, -2.9, -1.9, 2.2, 2)
    p.finish(mb, "race_cat_workshop", rig)


def storehouse():
    """The granary: a domed jar of stucco on staddle stones, out of reach of mice."""
    mb = p.begin()
    rig = p.Rig()
    r, z0, h = 2.0, 1.0, 2.6
    for k in range(6):                                                          # Staddle stones: a mouse cannot climb past the cap.
        a = TAU * k / 6 + 0.3
        x, y = math.cos(a) * 1.6, 0.3 + math.sin(a) * 1.6
        mb.cylinder((x, y, 0), (x, y, 0.75), 0.22, 0.14, "stucco_dark", segments=6)
        mb.cylinder((x, y, 0.75), (x, y, 0.9), 0.42, 0.3, "stucco_dark", segments=8)
    mb.cylinder((0, 0.3, 0.3), (0, 0.3, 0.8), 0.3, 0.3, "stucco_dark", segments=6)
    mb.cylinder((0, 0.3, 0.88), (0, 0.3, z0), r + 0.2, r + 0.2, "c_timber", segments=9)
    p.lathe(mb, 0, 0.3, z0, [(r, 0), (r + 0.15, h * 0.5), (r - 0.1, h)], ("stucco", "stucco"), 9)
    mb.cylinder((0, 0.3, z0 + h - 0.1), (0, 0.3, z0 + h + 0.12), r + 0.05, r + 0.05, "stucco_light", segments=9)
    p.dome(mb, 0, 0.3, z0 + h + 0.12, r - 0.1, 1.5, DOME, 4, 9)
    mb.cylinder((0, 0.3, z0 + h + 1.55), (0, 0.3, z0 + h + 1.8), 0.3, 0.36, "stucco_light", segments=8)
    zc = z0 + h + 1.8                                                           # A golden cat keeps watch on top.
    mb.sphere((0, 0.3, zc + 0.3), 0.32, "gold", segments=7, rings=5, scale=(0.9, 0.8, 1.1))
    mb.sphere((0, 0.2, zc + 0.78), 0.22, "gold", segments=7, rings=5)
    for sx in (-1, 1):
        mb.cylinder((sx * 0.12, 0.2, zc + 0.92), (sx * 0.15, 0.2, zc + 1.12), 0.07, 0.0, "gold", segments=4)
    with mb.bone("paw"):
        mb.cylinder((0.24, 0.1, zc + 0.6), (0.3, 0.02, zc + 0.95), 0.06, 0.07, "gold", segments=5)
    p.sway(mb, rig, "paw", (0.24, 0.1, zc + 0.6), 14.0, 1.6, "wave", (1, 0, 0), (0.3, 0.02, zc + 0.95))
    with mb.placed((0, 0.3 - r * 0.97, z0), 0):
        p.arch_door(mb, 0, 0.5, 0.8, 1.2, "stucco_light", "c_timber", None)
        mb.box((0, -0.35, 0.45), (1.2, 0.7, 0.1), "c_timber")
    ladder(mb, 0, 0.3 - r - 0.75, 0, z0 + 0.4, 0.0, 0.6)
    for k in range(5):
        a = -1.2 + 0.6 * k
        mb.box((math.cos(a) * (r + 0.1), 0.3 + math.sin(a) * (r + 0.1) * 0 - r * 0 + math.sin(a) * (r + 0.1), z0 + h * 0.75), (0.14, 0.14, 0.3), "dark", rotation_z=a)
    pot(mb, 2.3, -1.9, 0, 1.4, False)
    pot(mb, 2.8, -1.2, 0, 1.1, False)
    pot(mb, -2.4, -1.8, 0, 1.3, False)
    p.sack(mb, -2.7, -1.0, 0, 0.26)
    p.finish(mb, "race_cat_storehouse", rig)


def parasol(mb, x, y, z, r=1.1, h=2.0, mats=STRIPES[0], tilt=0.0):
    """A striped sunshade on a pole."""
    mb.cylinder((x, y, z), (x + tilt, y, z + h), 0.04, 0.04, "c_timber", segments=5)
    n = 8
    for i in range(n):
        a0, a1 = TAU * i / n, TAU * (i + 1) / n
        p.solid(mb, [(x + tilt, y, z + h + 0.05), (x + tilt + math.cos(a0) * r, y + math.sin(a0) * r, z + h - 0.38), (x + tilt + math.cos(a1) * r, y + math.sin(a1) * r, z + h - 0.38)], (0, 0, 0.04), mats[i % 2])
    mb.sphere((x + tilt, y, z + h + 0.12), 0.07, "gold", segments=5, rings=3)


def low_table(mb, x, y, z, fish=True):
    mb.cylinder((x, y, z + 0.22), (x, y, z + 0.28), 0.42, 0.42, "c_timber", segments=8)
    mb.cylinder((x, y, z), (x, y, z + 0.22), 0.1, 0.14, "c_timber", segments=6)
    if fish:
        mb.cylinder((x, y, z + 0.28), (x, y, z + 0.31), 0.24, 0.26, "stucco_light", segments=8)
        mb.sphere((x, y, z + 0.34), 0.16, "fish", segments=5, rings=3, scale=(1.2, 0.4, 0.3))


def sun_terrace():
    """The sun terrace: three steps of warm stone with cushions, sunshades
    and a fountain, 8 x 6 m."""
    mb = p.begin()
    rig = p.Rig()
    levels = ((0, 0.0, 7.6, 5.6, 0.6), (-0.6, 0.9, 5.2, 3.6, 1.4), (-1.6, 1.5, 2.8, 2.2, 2.2))
    for k, (cx, cy, w, d, top) in enumerate(levels):
        mb.box((cx, cy, top / 2), (w, d, top), "stucco")
        mb.box((cx, cy, top - 0.03), (w + 0.12, d + 0.12, 0.1), "stucco_light")
        mb.box((cx, cy, top + 0.02), (w - 0.3, d - 0.3, 0.04), "terracotta")
        mb.box((cx, cy, 0.15), (w + 0.1, d + 0.1, 0.3), "stucco_dark")
    p.stairs(mb, 1.5, -3.3, 0, 0.6, 1.6, 0.5, "stucco_dark", 0.2)
    p.stairs(mb, 0.4, -1.4, 0.6, 1.4, 1.2, 0.5, "stucco_dark", 0.2)
    p.stairs(mb, -1.6, -0.05, 1.4, 2.2, 1.0, 0.45, "stucco_dark", 0.2)
    with face(mb, 0, 0, 7.6, 5.6, "front"):
        for x in (-2.6, -1.2):
            p.arch_door(mb, x, 0, 0.8, 0.5, "stucco_light", "dark", None, 0.1)   # Cool niches to sleep in at noon.
    colors = ("aw_red", "aw_yellow", "aw_blue", "aw_green", "aw_white")
    spots = ((2.9, -1.9, 0.6), (3.1, 0.2, 0.6), (2.6, 1.9, 0.6), (-3.2, -2.1, 0.6), (-2.0, -2.2, 0.6), (0.3, -2.3, 0.6), (1.4, 0.2, 1.4), (1.3, 1.8, 1.4), (-2.6, -0.4, 1.4), (-0.4, 2.1, 1.4), (-1.9, 1.9, 2.2), (-1.2, 1.2, 2.2))
    for k, (x, y, z) in enumerate(spots):
        cushion(mb, x, y, z + 0.04, colors[k % 5], 0.34 + 0.06 * (k % 3))
    mb.box((2.9, -0.8, 0.63), (1.5, 2.8, 0.03), "aw_red")                         # Rugs.
    mb.box((2.9, -0.8, 0.64), (1.1, 2.4, 0.03), "aw_yellow")
    mb.box((1.3, 1.0, 1.43), (1.2, 2.2, 0.03), "aw_blue")
    low_table(mb, 2.2, -0.9, 0.6)
    low_table(mb, 0.6, 1.0, 1.4, False)
    p.lathe(mb, 0.6, 1.0, 1.68, [(0.1, 0), (0.16, 0.1), (0.08, 0.22)], ("terracotta",), 6)
    parasol(mb, 3.2, -1.0, 0.6, 1.3, 2.1, STRIPES[0], 0.15)
    parasol(mb, 1.6, 1.0, 1.4, 1.2, 2.0, STRIPES[1], -0.1)
    with mb.bone("shade"):                                                      # The top sunshade turns to follow the sun.
        parasol(mb, -1.6, 1.6, 2.2, 1.25, 2.1, STRIPES[2], 0.0)
    p.spin(mb, rig, "shade", (-1.6, 1.6, 2.2), (0, 0, 1), 16.0, "turn")
    fx, fy = -2.4, -1.8                                                         # A fountain: the fish spits the water.
    mb.cylinder((fx, fy, 0.6), (fx, fy, 0.95), 0.75, 0.7, "stucco_light", segments=9)
    mb.cylinder((fx, fy, 0.85), (fx, fy, 0.97), 0.58, 0.58, "water", segments=9)
    mb.cylinder((fx, fy, 0.9), (fx, fy, 1.45), 0.1, 0.07, "stucco", segments=6)
    mb.sphere((fx, fy, 1.6), 0.22, "gold", segments=6, rings=4, scale=(1.5, 0.5, 1.0))
    with mb.bone("jet"):
        p.arc(mb, [(fx + 0.3, fy, 1.6), (fx + 0.45, fy, 1.5), (fx + 0.52, fy, 1.0)], 0.04, "water", 0.6)
    rig.bone("jet", (fx + 0.3, fy, 1.6), (fx + 0.5, fy, 1.2), None)
    rig.add("turn", 16.0, lambda t: ({}, {"jet": (0.03 * math.sin(TAU * 8 * t), 0, 0)}))
    climb_post(mb, 3.3, 2.2, 2.6, 3, 0.6)
    climb_post(mb, 0.9, -0.6, 2.0, 2, 1.4)
    pot(mb, -3.3, 2.3, 0.6, 1.3)
    pot(mb, 0.2, -2.4, 0.0 + 0.6, 0.9)
    pot(mb, 1.6, 2.4, 1.4, 1.0)
    pot(mb, -2.8, 0.7, 2.2, 0.8)
    for k, (x, y, r, mat) in enumerate(((0.9, -2.0, 0.26, "aw_red"), (1.3, -2.3, 0.2, "aw_green"))):
        mb.sphere((x, y, 0.6 + r), r, mat, segments=7, rings=5)                   # Yarn to play with.
    p.finish(mb, "race_cat_sun_terrace", rig)


def tower():
    """A slender lookout with a balcony under an onion dome."""
    mb = p.begin()
    rig = p.Rig()
    mb.box((0, 0, 0.3), (2.6, 2.6, 0.6), "stucco_dark")
    mb.cylinder((0, 0, 0.6), (0, 0, 7.0), 1.05, 0.9, "stucco", segments=9)
    for z in (2.6, 4.6):
        mb.cylinder((0, 0, z), (0, 0, z + 0.16), 1.06, 1.04, "stucco_light", segments=9)
    with mb.placed((0, -1.0, 0.6), 0):
        door(mb, 0, 0, 0.85, 1.7)
        p.round_win(mb, 0, 3.0, 0.26, "c_timber", "window")
        p.round_win(mb, 0, 5.0, 0.26, "c_timber", "window")
    mb.cylinder((0, 0, 6.8), (0, 0, 7.0), 1.0, 1.7, "stucco_light", segments=9)   # The balcony.
    mb.cylinder((0, 0, 7.0), (0, 0, 7.08), 1.7, 1.7, "terracotta", segments=9)
    p.ring(mb, 0, 0, 7.75, 1.62, 0.07, "c_timber", 9)
    for k in range(9):
        a = math.pi / 2 - TAU * k / 9
        p.beam(mb, (math.cos(a) * 1.62, math.sin(a) * 1.62, 7.08), (math.cos(a) * 1.62, math.sin(a) * 1.62, 7.75), 0.06, "c_timber")
    turret(mb, 0, 0, 7.08, 0.85, 1.9, 4)
    with mb.placed((0, -1.62, 7.08), 0):
        p.awning(mb, 0, 1.6, 1.5, 0.7, 0.3, STRIPES[0])
    cushion(mb, 1.2, -0.4, 7.1, "aw_red", 0.3)
    cushion(mb, -1.1, 0.6, 7.1, "aw_blue", 0.3)
    p.flag(mb, rig, 0, 0, 7.08 + 2.0 + 0.85 * 2.5, 1.5, 1.0, 0.45, "aw_red", "aw_yellow", pole_mat="c_timber")
    for a in (-0.6, math.pi + 0.6):
        p.hang_lantern(mb, rig, math.cos(a) * 1.6, math.sin(a) * 1.6 - 0.0, 7.0, 0.2, "cage", "window", "c_timber")
    climb_post(mb, 1.9, -1.6, 2.6, 3)
    pot(mb, -1.6, -1.6, 0, 1.0)
    p.finish(mb, "race_cat_tower", rig)


MODELS = {
    "race_cat_sun_terrace": sun_terrace, "race_cat_tower": tower,
    "race_cat_house_1": house(1), "race_cat_house_2": house(2), "race_cat_house_3": house(3),
    "race_cat_center": center, "race_cat_workshop": workshop, "race_cat_storehouse": storehouse,
}
