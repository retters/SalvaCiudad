"""Lizard-folk: stepped platforms of sandstone with painted bands, doorways
that narrow upward, roof combs, sun discs, jade, feathers and steep palm
roofs; a warm flat stone to bask on next to every door."""

import math

import rparts as p
from rparts import TAU, face, tbox

PALM = ("palm", "palm_dark", "palm", "palm_green")
PAINT = ("l_red", "l_blue", "l_yellow", "jade")


def step(mb, cx, cy, z0, w, d, h, slope=0.25, band=True):
    """One body of a platform: a sloping foot and a framed panel above."""
    hs = h * 0.5
    tbox(mb, cx, cy, z0, z0 + hs, w, d, w - 2 * slope, d - 2 * slope, "l_stone")
    mb.box((cx, cy, z0 + hs + (h - hs) / 2), (w - 2 * slope + 0.16, d - 2 * slope + 0.16, h - hs), "l_stone_light")
    if band:
        mb.box((cx, cy, z0 + hs + (h - hs) / 2), (w - 2 * slope + 0.2, d - 2 * slope + 0.2, (h - hs) * 0.4), "l_stone_dark")
    return z0 + h


def stair(mb, x, y, z0, z1, w, run, rail=True):
    """Steps that climb toward +Y between two sloping stone rails."""
    p.stairs(mb, x, y, z0, z1, w, run, "l_stone_dark", 0.2)
    if rail:
        for s in (-1, 1):
            xx = x + s * (w / 2 + 0.2)
            p.prism_yz(mb, [(y - 0.1, z0), (y + run, z0), (y + run, z1 + 0.25), (y + run - 0.3, z1 + 0.25), (y - 0.1, z0 + 0.3)], xx - 0.2, xx + 0.2, "l_stone_light")


def fret(mb, L, z, mats=PAINT, size=0.36):
    """A painted band of step-frets along a face."""
    n = max(2, int(L / (size * 1.5)))
    for i in range(n):
        x = -L / 2 + L * (i + 0.5) / n
        mat = mats[i % len(mats)]
        mb.box((x, -0.03, z), (size, 0.06, size), mat)
        mb.box((x + size * 0.3, -0.05, z + size * 0.18), (size * 0.4, 0.06, size * 0.36), "l_stone_light")


def comb(mb, cx, cy, z, w, h=1.4, d=0.4, n=None):
    """A roof comb: a pierced crest of stone with jade and feathers."""
    n = n or max(3, int(w / 0.8))
    mb.box((cx, cy, z + 0.15), (w, d, 0.3), "l_stone")
    for i in range(n):
        x = cx - w / 2 + w * (i + 0.5) / n
        hh = h * (1.0 - 0.35 * abs(i - (n - 1) / 2) / max(1, (n - 1) / 2))
        mb.box((x, cy, z + 0.3 + hh / 2), (w / n * 0.62, d * 0.8, hh), "l_stone_light")
        mb.box((x, cy - d * 0.42, z + 0.3 + hh * 0.6), (w / n * 0.3, 0.06, w / n * 0.3), PAINT[i % 4])
        p.feathers(mb, x, cy, z + 0.3 + hh, 0.4, (PAINT[i % 4], PAINT[(i + 1) % 4], PAINT[(i + 2) % 4]))
    mb.box((cx, cy, z + 0.3 + h * 0.5), (w, d * 0.5, 0.14), "l_stone_dark")


def serpent(mb, x, y, z, s=1.0, rot=0.0):
    """A feathered serpent's head that looks toward -Y."""
    with mb.placed((x, y, z), rot):
        mb.box((0, 0.1 * s, 0.35 * s), (0.6 * s, 0.9 * s, 0.5 * s), "l_stone_light")
        mb.box((0, -0.5 * s, 0.42 * s), (0.5 * s, 0.5 * s, 0.26 * s), "l_stone_light")
        mb.box((0, -0.45 * s, 0.16 * s), (0.44 * s, 0.4 * s, 0.14 * s), "l_stone")
        mb.box((0, -0.5 * s, 0.26 * s), (0.36 * s, 0.42 * s, 0.07 * s), "l_red")
        for sx in (-1, 1):
            mb.box((sx * 0.3 * s, -0.25 * s, 0.5 * s), (0.06, 0.16 * s, 0.14 * s), "jade")
            mb.cylinder((sx * 0.16 * s, -0.7 * s, 0.24 * s), (sx * 0.16 * s, -0.72 * s, 0.1 * s), 0.035 * s, 0.0, "white", segments=4)
        for k in range(5):
            a = math.pi * (0.1 + 0.8 * k / 4)
            mb.cylinder((math.cos(a) * 0.3 * s, 0.3 * s, 0.4 * s + math.sin(a) * 0.2 * s), (math.cos(a) * 0.75 * s, 0.45 * s, 0.4 * s + math.sin(a) * 0.65 * s), 0.11 * s, 0.0, ("jade", "l_red", "l_yellow", "l_red", "jade")[k], segments=4)


def palm_roof(mb, cx, cy, z, w, d, rise, axis="y", over=0.4):
    """A steep roof of palm in bands; its gable looks to the front."""
    if axis == "y":
        with mb.placed((cx, cy, 0), math.pi / 2):
            return palm_roof(mb, 0, 0, z, d, w, rise, "x", over)
    top = p.gable(mb, cx, cy, z, w, d, rise, PALM, rows=4, over=over, end_over=0.35, fill="cane", thick=0.12, ridge_mat="palm_dark")
    for s in (-1, 1):
        for side in (-1, 1):
            p.beam(mb, (cx + s * (w / 2 + 0.35), cy + side * (d / 2 + over), z - over * rise / (d / 2) - 0.05), (cx + s * (w / 2 + 0.35), cy - side * 0.25, top + 0.45), 0.1, "pole")
    return top


def cane_walls(mb, cx, cy, z0, w, d, h):
    mb.box((cx, cy, z0 + h / 2), (w, d, h), "cane")
    for side in p.SIDES:
        with face(mb, cx, cy, w, d, side, z0) as L:
            n = max(2, round(L / 0.45))
            for i in range(n + 1):
                mb.cylinder((-L / 2 + L * i / n, -0.02, 0), (-L / 2 + L * i / n, -0.02, h), 0.04, 0.04, "linen", segments=4)
            mb.box((0, -0.02, h * 0.55), (L, 0.07, 0.07), "pole")


def bask_rock(mb, x, y, z=0.0, s=1.0, rot=0.3):
    with mb.placed((x, y, z), rot):
        tbox(mb, 0, 0, 0, 0.3 * s, 1.5 * s, 1.0 * s, 1.3 * s, 0.8 * s, "f_stone")
        mb.box((0, 0, 0.3 * s + 0.015), (1.1 * s, 0.6 * s, 0.03), "warm")


def standard(mb, x, y, h=2.6, z=0.0, mats=PAINT):
    """A pole with a painted collar and a crest of feathers."""
    mb.cylinder((x, y, z), (x, y, z + h), 0.08, 0.06, "pole_dark", segments=6)
    mb.cylinder((x, y, z + h * 0.72), (x, y, z + h * 0.86), 0.14, 0.14, "jade", segments=6)
    mb.cylinder((x, y, z + h * 0.86), (x, y, z + h * 0.92), 0.16, 0.16, "gold", segments=6)
    p.feathers(mb, x, y, z + h, 0.7, mats)


def palm_tree(mb, x, y, h=4.0, lean=0.6):
    pts = [(x, y, 0), (x + lean * 0.3, y, h * 0.4), (x + lean * 0.75, y, h * 0.75), (x + lean, y, h)]
    p.arc(mb, pts, 0.16, "pole", 0.6)
    for k in range(6):
        a = TAU * k / 6 + 0.3
        tip = (x + lean + math.cos(a) * 1.5, y + math.sin(a) * 1.5, h - 0.5)
        mid = (x + lean + math.cos(a) * 0.8, y + math.sin(a) * 0.8, h + 0.25)
        mb.cylinder((x + lean, y, h), mid, 0.07, 0.22, "palm_green", segments=4)
        mb.cylinder(mid, tip, 0.22, 0.0, "palm_green", segments=4)


def jar(mb, x, y, z=0.0, s=1.0, mat="clay"):
    p.lathe(mb, x, y, z, [(0.14 * s, 0), (0.3 * s, 0.25 * s), (0.26 * s, 0.5 * s), (0.14 * s, 0.62 * s), (0.18 * s, 0.7 * s)], (mat, "clay_dark", mat, "l_stone_light"), 7)


def house(level):
    def build():
        mb = p.begin()
        rig = p.Rig()
        if level == 1:
            z = step(mb, 0, 0.2, 0, 3.8, 3.4, 0.4, 0.15, False)
            stair(mb, -0.4, -1.75, 0, z, 1.0, 0.4, False)
            cane_walls(mb, -0.4, 0.5, z, 2.4, 2.2, 1.5)
            with face(mb, -0.4, 0.5, 2.4, 2.2, "front", z):
                p.trap_door(mb, 0, 0, 0.8, 1.25, "pole", "dark", "pole")
                for k in range(3):
                    mb.box((-0.25 + 0.25 * k, -0.2, 1.05), (0.2, 0.03, 0.3), PAINT[k])
            palm_roof(mb, -0.4, 0.5, z + 1.5, 2.4, 2.2, 2.3)
            bask_rock(mb, 1.25, -0.8, z, 0.7)
            standard(mb, 1.5, 0.9, 2.2, z)
        elif level == 2:
            z = step(mb, 0, 0.3, 0, 5.6, 4.4, 0.7, 0.25)
            stair(mb, -0.8, -2.5, 0, z, 1.3, 0.7)
            w, d, h = 3.4, 2.8, 1.9
            cx, cy = -0.8, 0.6
            tbox(mb, cx, cy, z, z + h, w, d, w - 0.3, d - 0.3, "l_stone")
            mb.box((cx, cy, z + h - 0.12), (w - 0.1, d - 0.1, 0.24), "l_stone_light")
            with face(mb, cx, cy, w, d, "front", z) as L:
                p.trap_door(mb, 0, 0, 0.95, 1.4)
                fret(mb, L - 0.5, h - 0.14)
                p.sun_disc(mb, 0, -0.2, 2.35, 0.24)
            palm_roof(mb, cx, cy, z + h, w - 0.3, d - 0.3, 2.6)
            bask_rock(mb, 1.8, -0.6, z, 0.9)
            jar(mb, 1.6, 1.1, z, 1.0)
            jar(mb, 2.1, 0.7, z, 0.8, "l_stone_dark")
            standard(mb, -2.45, -1.55, 2.6, z)
            standard(mb, 0.85, -1.55, 2.6, z, ("jade", "l_yellow", "l_red"))
        else:
            z = step(mb, 0, 0.3, 0, 7.6, 5.4, 0.7, 0.25)
            z = step(mb, 0, 0.5, z, 6.4, 4.4, 0.6, 0.2)
            stair(mb, -0.9, -2.75, 0, z, 1.6, 1.3)
            for sx in (-1, 1):
                serpent(mb, -0.9 + sx * 1.3, -2.9, 0, 0.7)
            w, d, h = 4.2, 3.0, 2.3
            cx, cy = -0.9, 0.8
            tbox(mb, cx, cy, z, z + h * 0.45, w, d, w - 0.3, d - 0.3, "l_stone")                # Slope and panel.
            mb.box((cx, cy, z + h * 0.725), (w - 0.14, d - 0.14, h * 0.55), "l_stone_light")
            mb.box((cx, cy, z + h + 0.1), (w + 0.2, d + 0.2, 0.22), "l_stone")
            with face(mb, cx, cy, w - 0.14, d - 0.14, "front", z) as L:
                p.trap_door(mb, 0, 0, 1.1, 1.6)
                fret(mb, L - 0.3, h - 0.25)
                for sx in (-1, 1):
                    mb.box((sx * 1.4, -0.04, 1.0), (0.5, 0.06, 0.7), "l_red")
                    mb.box((sx * 1.4, -0.06, 1.0), (0.24, 0.06, 0.36), "jade")
            comb(mb, cx, cy + 0.3, z + h + 0.2, 3.0, 1.3)
            p.sun_disc(mb, cx, cy - d / 2 - 0.1, z + h + 0.75, 0.32)
            wx = 2.2                                                            # A cane wing under palm, for the cool of the night.
            cane_walls(mb, wx, 0.9, z, 1.9, 2.4, 1.6)
            with face(mb, wx, 0.9, 1.9, 2.4, "front", z):
                p.trap_door(mb, 0, 0, 0.7, 1.2, "pole", "dark", "pole")
            palm_roof(mb, wx, 0.9, z + 1.6, 1.9, 2.4, 2.0)
            bask_rock(mb, 2.1, -1.1, z, 0.9, 0.2)
            for sx in (-1, 1):
                p.brazier(mb, rig, cx + sx * 1.6, -1.25, z, 0.9, "gold", "l_stone_dark")
            standard(mb, -3.3, -1.9, 3.0, 0.7)
            standard(mb, 3.3, -1.9, 3.0, 0.7, ("jade", "l_yellow", "l_red"))
            jar(mb, -2.9, 1.9, z, 1.1)
            jar(mb, -2.9, 1.2, z, 0.8, "l_stone_dark")
        p.finish(mb, "race_lizard_house_%d" % level, rig)
    return build


def center():
    """The palace of the sun: a long hall and two shrines on a stepped
    court, 14 x 12 m."""
    mb = p.begin()
    rig = p.Rig()
    cy = 0.6
    z = step(mb, 0, cy, 0, 13.6, 10.6, 0.9, 0.35)
    z = step(mb, 0, cy + 0.4, z, 12.0, 9.0, 0.8, 0.3)
    stair(mb, 0, cy - 5.3 - 0.2, 0, z, 3.6, 1.9)
    for sx in (-1, 1):
        serpent(mb, sx * 2.5, cy - 5.6, 0, 1.1)
    hw, hd, hh = 8.4, 3.4, 2.9                                                  # The long hall.
    hy = cy + 2.2
    tbox(mb, 0, hy, z, z + hh * 0.4, hw, hd, hw - 0.4, hd - 0.4, "l_stone")
    mb.box((0, hy, z + hh * 0.7), (hw - 0.2, hd - 0.2, hh * 0.6), "l_stone_light")
    mb.box((0, hy, z + hh + 0.14), (hw + 0.3, hd + 0.3, 0.3), "l_stone")
    mb.box((0, hy, z + hh + 0.4), (hw - 0.4, hd - 0.4, 0.3), "l_stone_light")
    with face(mb, 0, hy, hw - 0.2, hd - 0.2, "front", z) as L:
        for k in range(5):
            p.trap_door(mb, -3.0 + 1.5 * k, 0, 0.95, 1.9, "l_stone", "dark", "jade" if k == 2 else "l_stone_dark")
        fret(mb, L - 0.4, hh - 0.3, PAINT, 0.42)
    comb(mb, 0, hy + 0.4, z + hh + 0.5, 5.0, 2.0, 0.5)
    with mb.bone("sun"):                                                        # The great disc turns in front of the comb.
        p.sun_disc(mb, 0, hy - 0.1, z + hh + 1.9, 0.75, "gold", 10, "l_red")
    p.spin(mb, rig, "sun", (0, hy - 0.1, z + hh + 1.9), (0, 1, 0), 12.0, "turn", (0, hy - 0.6, z + hh + 1.9))
    for sx in (-1, 1):                                                          # Two shrines on their own steps.
        tx, ty = sx * 4.4, cy - 1.6
        zt = step(mb, tx, ty, z, 3.2, 3.2, 1.1, 0.3)
        with mb.placed((tx, ty - 1.6 - 0.9, 0), 0):
            p.stairs(mb, 0, 0, z, zt, 1.2, 1.0, "l_stone_dark", 0.2)
        tbox(mb, tx, ty, zt, zt + 1.9, 2.3, 2.3, 2.0, 2.0, "l_stone_light")
        with face(mb, tx, ty, 2.3, 2.3, "front", zt) as L:
            p.trap_door(mb, 0, 0, 0.8, 1.35)
        mb.box((tx, ty, zt + 2.0), (2.5, 2.5, 0.24), "l_stone")
        p.hip_roof(mb, tx, ty, zt + 2.1, 2.3, 2.3, 2.6, PALM, rows=4, over=0.35, power=0.75)
        p.feathers(mb, tx, ty, zt + 4.6, 0.8)
        p.brazier(mb, rig, tx - sx * 1.25, ty - 1.1, zt, 0.8, "gold", "l_stone_dark")
        with mb.placed((sx * 5.4, cy - 3.6, z), 0):
            mb.cylinder((0, 0, 0), (0, 0, 4.0), 0.07, 0.06, "pole_dark", segments=5)
            p.hang_banner(mb, rig, -sx * 0.5, 0, 3.9, 0.8, 2.4, "l_red", "gold", "pole_dark", 3)
        palm_tree(mb, sx * 6.2, cy + 3.9, 4.6 + 0.6 * sx, sx * 0.8)
        bask_rock(mb, sx * 1.9, cy - 2.6, z, 1.1, 0.4 * sx)
        p.brazier(mb, rig, sx * 2.4, cy - 4.2, z, 1.1, "gold", "l_stone_dark")
    mb.box((0, cy - 1.4, z + 0.2), (1.3, 1.0, 0.4), "l_stone_dark")               # The jade seat in the court.
    mb.box((0, cy - 1.3, z + 0.55), (1.0, 0.7, 0.3), "jade")
    mb.box((0, cy - 0.95, z + 1.1), (1.0, 0.2, 1.1), "jade_dark")
    p.feathers(mb, 0, cy - 0.95, z + 1.6, 0.8)
    p.finish(mb, "race_lizard_center", rig)


def workshop():
    """The jade carvers' shade: four pillars, palm, and a polishing wheel."""
    mb = p.begin()
    rig = p.Rig()
    z = step(mb, 0, 0.2, 0, 5.4, 4.2, 0.5, 0.2)
    stair(mb, 0, -2.3, 0, z, 1.4, 0.5, False)
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * 2.0, 0.3 + sy * 1.4
            tbox(mb, x, y, z, z + 2.3, 0.5, 0.5, 0.4, 0.4, "l_stone_light")
            mb.box((x, y, z + 1.6), (0.5, 0.5, 0.3), PAINT[(sx + 1) + (sy + 1) // 2])
            mb.box((x, y, z + 2.36), (0.6, 0.6, 0.14), "l_stone")
    p.hip_roof(mb, 0, 0.3, z + 2.4, 4.4, 3.2, 2.2, PALM, rows=4, over=0.5, ridge=2.0, power=0.85)
    mb.box((-1.0, 0.9, z + 0.4), (1.8, 0.8, 0.8), "l_stone")                     # The bench with rough and cut jade.
    mb.box((-1.0, 0.9, z + 0.84), (2.0, 0.95, 0.1), "l_stone_light")
    for k, (dx, s, mat) in enumerate(((-0.6, 0.34, "jade_dark"), (-0.1, 0.24, "jade"), (0.35, 0.18, "jade"), (0.65, 0.12, "l_stone_light"))):
        mb.box((-1.0 + dx, 0.9, z + 0.9 + s / 2), (s, s * 0.9, s), mat, rotation_z=0.3 * k)
    for sy in (-1, 1):                                                          # The wheel, turned by a cord.
        p.beam(mb, (1.3, 0.2 + sy * 0.3, z), (1.3, 0.2 + sy * 0.3, z + 1.0), 0.1, "pole_dark")
    with mb.bone("wheel"):
        mb.cylinder((1.3, 0.05, z + 0.95), (1.3, 0.35, z + 0.95), 0.5, 0.5, "f_stone", segments=10)
        mb.cylinder((1.3, -0.15, z + 0.95), (1.3, 0.55, z + 0.95), 0.05, 0.05, "pole", segments=5)
        mb.box((1.3, 0.2, z + 1.3), (0.1, 0.32, 0.1), "jade")
    p.spin(mb, rig, "wheel", (1.3, 0.2, z + 0.95), (0, 1, 0), 2.4, "turn", (1.3, 0.6, z + 0.95))
    for k in range(5):                                                          # Blades of black glass set out to dry.
        mb.cylinder((0.3 + 0.2 * k, -1.2, z + 0.02), (0.36 + 0.2 * k, -0.7, z + 0.05), 0.07, 0.0, "obsidian", segments=3)
    jar(mb, -2.0, -1.0, z, 1.0)
    jar(mb, 2.1, 1.5, z, 0.9, "l_stone_dark")
    bask_rock(mb, 3.3, -1.4, 0, 0.8)
    standard(mb, -3.1, -1.6, 2.6)
    p.finish(mb, "race_lizard_workshop", rig)


def storehouse():
    """Two clay granaries shaped like jars under caps of palm."""
    mb = p.begin()
    rig = p.Rig()
    z = step(mb, 0, 0.2, 0, 5.6, 4.2, 0.5, 0.2)
    stair(mb, 1.6, -2.3, 0, z, 1.2, 0.5, False)
    for x, y, s in ((-1.0, 0.5, 1.0), (1.7, 0.9, 0.7)):
        mb.cylinder((x, y, z), (x, y, z + 0.35 * s), 1.0 * s, 0.95 * s, "l_stone_dark", segments=9)
        p.lathe(mb, x, y, z + 0.35 * s, [(0.8 * s, 0), (1.45 * s, 0.9 * s), (1.5 * s, 1.5 * s), (1.2 * s, 2.3 * s), (0.9 * s, 2.7 * s)], ("clay", "clay", "clay_dark", "clay"), 9)
        mb.cylinder((x, y, z + 1.55 * s), (x, y, z + 1.75 * s), 1.52 * s, 1.5 * s, PAINT[0] if s == 1.0 else PAINT[1], segments=9)
        p.cone_roof(mb, x, y, z + 3.0 * s, 0.9 * s, 1.5 * s, PALM, 4, 9, 0.5 * s, 0.9)
        mb.cylinder((x, y, z + 4.45 * s), (x, y, z + 4.75 * s), 0.1 * s, 0.14 * s, "palm_dark", segments=5)
        with mb.placed((x, y - 1.36 * s, z + 2.0 * s), 0):
            mb.box((0, 0, 0), (0.6 * s, 0.14, 0.6 * s), "pole_dark")
            mb.box((0, -0.06, 0), (0.44 * s, 0.1, 0.44 * s), "pole")
    for k in range(8):                                                          # A ladder to the big one's hatch.
        mb.box((-1.0, -1.7 + 0.05 * k, z + 0.2 + 0.24 * k), (0.6, 0.05, 0.05), "pole")
    for sx in (-1, 1):
        p.beam(mb, (-1.0 + sx * 0.3, -1.75, z), (-1.0 + sx * 0.3, -1.3, z + 2.2), 0.07, "pole_dark")
    for k, (x, y) in enumerate(((0.6, -1.3), (1.2, -1.0), (2.3, -0.9))):         # Baskets of maize.
        mb.cylinder((x, y, z), (x, y, z + 0.3), 0.24, 0.3, "sisal", segments=7)
        for i in range(5):
            mb.cylinder((x + 0.1 * math.cos(i * 1.3), y + 0.1 * math.sin(i * 1.3), z + 0.28), (x + 0.16 * math.cos(i * 1.3), y + 0.16 * math.sin(i * 1.3), z + 0.5), 0.06, 0.03, "l_yellow", segments=5)
    jar(mb, -2.4, -1.4, z, 1.1)
    standard(mb, 2.5, -1.7, 2.4, z)
    p.finish(mb, "race_lizard_storehouse", rig)


def egg(mb, x, y, z, s=1.0, mat="egg"):
    mb.sphere((x, y, z + 0.17 * s), 0.14 * s, mat, segments=6, rings=5, scale=(1, 1, 1.3))


def hatchery():
    """The hatchery: clutches on warm stones around a fire, half under palm,
    with a mirror that throws the sun on them: 8 x 6 m."""
    mb = p.begin()
    rig = p.Rig()
    rnd = p.random.Random(95)
    z = step(mb, 0, 0.2, 0, 7.6, 5.6, 0.5, 0.2)
    stair(mb, 0, -3.0, 0, z, 1.6, 0.5)
    for sx in (-1, 1):
        serpent(mb, sx * 1.3, -3.2, 0, 0.6)
    mb.box((0, 0.3, z + 0.06), (5.6, 3.6, 0.12), "sack")                          # The bed of sand in its kerb.
    for sx in (-1, 1):
        mb.box((sx * 2.9, 0.3, z + 0.17), (0.3, 4.2, 0.34), "l_stone_light")
        mb.box((0 if sx > 0 else 0, 0.3 + sx * 1.95, z + 0.17), (5.6, 0.3, 0.34), "l_stone_light")
    mb.box((0, -1.65, z + 0.2), (1.2, 0.34, 0.4), "sack")                         # A gap in the kerb to walk in.
    spots = ((-1.8, -0.5), (-1.9, 1.1), (1.8, -0.5), (1.9, 1.1), (0, 1.4))
    for k, (x, y) in enumerate(spots):                                          # Warm stones with their clutches.
        with mb.placed((x, y, z + 0.1), 0.5 * k):
            tbox(mb, 0, 0, 0, 0.26, 1.3, 1.0, 1.1, 0.8, "f_stone")
            mb.box((0, 0, 0.275), (0.95, 0.65, 0.03), "warm")
        for i in range(4 + k % 2):
            a = TAU * i / (4 + k % 2) + k
            egg(mb, x + math.cos(a) * 0.26, y + math.sin(a) * 0.22, z + 0.36, rnd.uniform(0.85, 1.1), "egg" if (i + k) % 3 else "l_stone_light")
    hx, hy = 1.8, -0.5                                                          # One of them is hatching.
    with mb.bone("hatch"):
        mb.cylinder((hx + 0.55, hy - 0.5, z + 0.12), (hx + 0.55, hy - 0.5, z + 0.3), 0.1, 0.15, "egg", segments=6)
        mb.sphere((hx + 0.55, hy - 0.5, z + 0.37), 0.1, "jade", segments=6, rings=4)
        for sx in (-1, 1):
            mb.box((hx + 0.55 + sx * 0.05, hy - 0.59, z + 0.4), (0.03, 0.02, 0.03), "l_yellow")
    p.sway(mb, rig, "hatch", (hx + 0.55, hy - 0.5, z + 0.12), 12.0, 1.2, "hatch", (0, 1, 0), (hx + 0.55, hy - 0.5, z + 0.5))
    mb.cylinder((0, 0.2, z + 0.1), (0, 0.2, z + 0.4), 0.7, 0.6, "l_stone_dark", segments=8)      # The fire that warms the sand.
    mb.cylinder((0, 0.2, z + 0.36), (0, 0.2, z + 0.42), 0.5, 0.5, "ember", segments=8)
    p.flame(mb, rig, 0, 0.2, z + 0.4, 0.45)
    for sx in (-1, 1):                                                          # Palm shade over the back half.
        for y, hh in ((0.6, 2.3), (2.4, 2.9)):
            mb.cylinder((sx * 3.2, y, z), (sx * 3.2, y, z + hh), 0.1, 0.09, "pole", segments=6)
    for r in range(3):
        y0, y1 = 0.3 + 0.8 * r, 0.3 + 0.8 * (r + 1) + 0.06
        z0, z1 = z + 2.25 + 0.24 * r, z + 2.25 + 0.24 * (r + 1) + 0.02
        p.solid(mb, [(-3.6, y0, z0), (3.6, y0, z0), (3.6, y1, z1), (-3.6, y1, z1)], (0, 0, 0.12), PALM[r])
    mx, my = -3.2, -1.9                                                         # The sun mirror on its post.
    mb.cylinder((mx, my, z), (mx, my, z + 2.4), 0.09, 0.07, "pole_dark", segments=6)
    with mb.bone("mirror"):
        with mb.placed((mx, my, z + 2.7), -0.7):
            p.sun_disc(mb, 0, 0, 0, 0.45, "gold", 8, "white")
    p.sway(mb, rig, "mirror", (mx, my, z + 2.4), 25.0, 8.0, "turn", (0, 0, 1), (mx, my, z + 3.0))
    standard(mb, 3.3, -2.0, 2.8, z)
    jar(mb, 2.6, -2.1, z, 0.9)
    bask_rock(mb, -1.7, -2.1, z, 0.8, 0.1)
    palm_tree(mb, 3.2, 2.5, 4.2, 0.5)
    p.finish(mb, "race_lizard_hatchery", rig)


def tower():
    """A stepped pylon with a guard room and a signal mirror."""
    mb = p.begin()
    rig = p.Rig()
    z = 0.0
    for k, (w, h) in enumerate(((4.0, 1.5), (3.2, 1.5), (2.6, 1.4))):
        z = step(mb, 0, 0, z, w, w, h, 0.22)
    with face(mb, 0, 0, 4.0 - 0.28, 4.0 - 0.28, "front", 0) as L:
        p.trap_door(mb, 0, 0, 0.9, 1.2)
    for k, (w, zz) in enumerate(((3.2, 1.5), (2.6, 3.0))):
        with face(mb, 0, 0, w - 0.3, w - 0.3, "front", zz) as L:
            fret(mb, L - 0.4, 1.12, PAINT, 0.3)
    tbox(mb, 0, 0, z, z + 1.8, 1.7, 1.7, 1.5, 1.5, "l_stone_light")                # The guard room.
    with face(mb, 0, 0, 1.7, 1.7, "front", z):
        p.trap_door(mb, 0, 0.0, 0.6, 1.2)
    for side in ("left", "right"):
        with face(mb, 0, 0, 1.6, 1.6, side, z):
            mb.box((0, 0.02, 1.0), (0.5, 0.2, 0.5), "dark")
    mb.box((0, 0, z + 1.9), (2.1, 2.1, 0.26), "l_stone")
    comb(mb, 0, 0.5, z + 2.0, 1.8, 1.0, 0.36, 3)
    with mb.bone("mirror"):                                                     # The mirror flashes to the next town.
        p.sun_disc(mb, 0, -0.3, z + 2.9, 0.5, "gold", 8, "white")
    mb.cylinder((0, -0.3, z + 2.0), (0, -0.3, z + 2.5), 0.07, 0.06, "pole_dark", segments=5)
    p.sway(mb, rig, "mirror", (0, -0.3, z + 2.4), 30.0, 6.0, "turn", (0, 0, 1), (0, -0.3, z + 3.0))
    for sx in (-1, 1):
        p.brazier(mb, rig, sx * 1.3, -2.4, 0, 1.0, "gold", "l_stone_dark")
        standard(mb, sx * 2.2, -2.0, 2.8, 0.0)
    p.finish(mb, "race_lizard_tower", rig)


MODELS = {
    "race_lizard_hatchery": hatchery, "race_lizard_tower": tower,
    "race_lizard_house_1": house(1), "race_lizard_house_2": house(2), "race_lizard_house_3": house(3),
    "race_lizard_center": center, "race_lizard_workshop": workshop, "race_lizard_storehouse": storehouse,
}
