"""Dwarves: squat battered ashlar, slab roofs with turf, bronze and gold
bands, fire behind every window, and the rock they are built against."""

import math

import rparts as p
from rparts import TAU, face, tbox

WALL, DARK, LIGHT = "d_wall", "d_dark", "d_light"


def block(mb, cx, cy, z0, w, d, h, batter=0.22, mat=WALL):
    """A block whose sides and back lean in; the front stays plumb."""
    tbox(mb, cx, cy, z0, z0 + h, w, d, w - 2 * batter, d - batter, mat, top=(0, -batter / 2))
    tbox(mb, cx, cy, z0, z0 + 0.4, w + 0.24, d + 0.24, w + 0.1, d + 0.1, DARK)
    mb.box((cx, cy - batter / 2, z0 + h - 0.08), (w - 2 * batter + 0.12, d - batter + 0.12, 0.16), LIGHT)


def frieze(mb, L, z, mat="gold", step=0.5):
    """A band of geometric teeth along a face."""
    mb.box((0, -0.03, z), (L, 0.06, 0.07), mat)
    n = max(2, int(L / step))
    for i in range(n + 1):
        mb.box((-L / 2 + L * i / n, -0.03, z - 0.09 if i % 2 else z + 0.09), (0.07, 0.06, 0.16), mat)


def runes(mb, x, z0, z1, mat="gold", n=3):
    for k in range(n):
        z = z0 + (z1 - z0) * (k + 0.5) / n
        mb.box((x, -0.03, z), (0.22 if k % 2 else 0.06, 0.05, 0.06 if k % 2 else 0.22), mat)
        mb.box((x + (0.08 if k % 2 else 0), -0.03, z + 0.07), (0.06, 0.05, 0.12), mat)


def buttress(mb, x, y, z0, h, w=0.7, out=0.7, sx=1):
    """A leaning pier at a corner; it leans toward the wall along X."""
    tbox(mb, x, y, z0, z0 + h, w, out, w * 0.45, out * 0.8, DARK, top=(-sx * w * 0.27, 0))


def slab_roof(mb, cx, cy, z, w, d, h, turf=True, rnd=None, metal=None):
    """Low hipped slabs with a flat top; maybe turf, maybe a bronze cap."""
    p.hip_roof(mb, cx, cy, z, w, d, h, ("d_roof_dark", "d_roof"), rows=2, over=0.3, ridge=w * 0.45, power=0.8)
    top_w, top_d = w * 0.45, d * 0.22
    if metal:
        mb.box((cx, cy, z + h + 0.06), (top_w + 0.5, top_d + 0.5, 0.14), metal)
        mb.box((cx, cy, z + h + 0.2), (top_w, 0.2, 0.2), "gold")
    elif turf:
        mb.box((cx, cy, z + h + 0.05), (top_w + 0.4, top_d + 0.5, 0.14), "grass")
        mb.box((cx - w * 0.25, cy - d * 0.25, z + h * 0.5 + 0.06), (0.5, 0.4, 0.12), "grass_dark")


def chimney(mb, rig, x, y, z0, z1, w=0.6, smoke=True):
    mb.box((x, y, (z0 + z1) / 2), (w, w, z1 - z0), DARK)
    mb.box((x, y, z1 + 0.06), (w + 0.2, w + 0.2, 0.14), WALL)
    mb.box((x, y, z1 + 0.14), (w - 0.14, w - 0.14, 0.04), "ember")
    if smoke and rig:
        p.smoke(mb, rig, x, y, z1 + 0.2, w * 0.45)


def bench(mb, x, y, w=1.4):
    mb.box((x, y, 0.42), (w, 0.4, 0.1), LIGHT)
    for s in (-1, 1):
        mb.box((x + s * (w / 2 - 0.15), y, 0.19), (0.16, 0.34, 0.38), DARK)


def boulders(mb, rnd, x0, x1, y0, y1, n, size=1.0, mats=("d_rock", "d_rock_dark")):
    for _ in range(n):
        s = size * rnd.uniform(0.6, 1.2)
        mb.sphere((rnd.uniform(x0, x1), rnd.uniform(y0, y1), s * 0.3), s, rnd.choice(mats), segments=6, rings=4, scale=(1, rnd.uniform(0.7, 1.0), rnd.uniform(0.6, 0.9)))


def anvil(mb, x, y, z=0.0):
    mb.box((x, y, z + 0.22), (0.5, 0.4, 0.44), DARK)
    mb.box((x, y, z + 0.53), (0.3, 0.22, 0.18), "iron")
    mb.box((x, y, z + 0.68), (0.62, 0.26, 0.12), "iron")
    mb.cylinder((x + 0.31, y, z + 0.68), (x + 0.56, y, z + 0.7), 0.07, 0.0, "iron", segments=5)


def ingots(mb, x, y, z, mat="gold", rows=3):
    for r in range(rows):
        for k in range(rows - r):
            mb.box((x + (k - (rows - r - 1) / 2) * 0.3, y, z + 0.07 + r * 0.13), (0.26, 0.5, 0.12), mat)


def house(level):
    def build():
        mb = p.begin()
        rig = p.Rig()
        rnd = p.random.Random(40 + level)
        w, d, h = ((3.6, 3.2, 1.9), (5.4, 4.2, 2.3), (7.4, 5.2, 2.6))[level - 1]
        cy = 0.2
        block(mb, 0, cy, 0, w, d, h)
        with face(mb, 0, cy, w, d, "front") as L:
            p.arch_door(mb, 0, 0, 0.95 + 0.15 * level, 1.5 + 0.2 * level, LIGHT, "d_door", "gold" if level > 1 else "iron")
            if level == 1:
                p.win(mb, 1.05, 1.1, 0.5, 0.5, LIGHT, "fire_win")
                mb.box((0, -0.03, h - 0.3), (L - 0.8, 0.06, 0.08), "bronze")
            else:
                for sx in (-1, 1):
                    for k in range(level - 1):
                        p.win(mb, sx * (1.5 + 1.15 * k), 1.25, 0.55, 0.6, LIGHT, "fire_win")
                frieze(mb, L - 0.8, h - 0.42, "gold")
            if level == 3:
                for sx in (-1, 1):                                               # Pillars with bronze caps flank the door.
                    mb.box((sx * 0.95, -0.25, 1.2), (0.42, 0.42, 2.4), DARK)
                    mb.box((sx * 0.95, -0.25, 2.45), (0.56, 0.56, 0.14), "bronze")
                    runes(mb, sx * 0.95, 0.5, 2.1, "gold", 3)
                    mb.box((sx * 0.95, -0.25, 0.12), (0.6, 0.6, 0.24), LIGHT)
                mb.box((0, -0.3, 2.62), (2.7, 0.6, 0.22), LIGHT)
                mb.box((0, -0.3, 2.78), (2.3, 0.5, 0.12), "bronze")
        if level >= 2:
            for sx in (-1, 1):
                for sy in (-1, 1):
                    buttress(mb, sx * (w / 2 + 0.08), cy + sy * (d / 2 - 0.45), 0, h * 0.85, 0.75, 0.75, sx)
            for side in ("left", "right"):
                with face(mb, 0, cy, w, d, side):
                    p.win(mb, 0, 1.25, 0.5, 0.55, LIGHT, "fire_win")
        z = h
        if level == 3:                                                          # An upper hall set back, under bronze.
            mb.box((0, cy, z + 0.1), (w - 0.3, d - 0.3, 0.2), "d_roof_dark")
            uw, ud, uh = 4.2, 3.2, 1.7
            block(mb, 0, cy + 0.4, z + 0.2, uw, ud, uh, 0.16)
            with face(mb, 0, cy + 0.4, uw, ud, "front", z + 0.2) as L:
                for sx in (-1, 0, 1):
                    p.win(mb, sx * 1.15, 0.9, 0.5, 0.7, LIGHT, "fire_win")
                frieze(mb, L - 0.6, uh - 0.3, "gold", 0.4)
            slab_roof(mb, 0, cy + 0.32, z + 0.2 + uh, uw - 0.3, ud - 0.2, 0.7, metal="bronze")
            for sx in (-1, 1):
                p.brazier(mb, rig, sx * (w / 2 - 0.7), cy - d / 2 + 0.6, z + 0.2, 0.8)
            chimney(mb, rig, 1.4, cy + 1.2, z + uh, z + uh + 1.9, 0.6)
            chimney(mb, None, -2.9, cy + 1.6, z, z + 1.5, 0.5)
            with face(mb, 0, cy + 0.4, uw, ud, "left", z + 0.2):
                p.hang_banner(mb, rig, 0, -0.14, 1.5, 0.6, 1.1, "d_banner", "gold", "bronze")
            with face(mb, 0, cy + 0.4, uw, ud, "right", z + 0.2):
                p.hang_banner(mb, rig, 0, -0.14, 1.5, 0.6, 1.1, "d_banner", "gold", "bronze")
        else:
            slab_roof(mb, 0, cy - 0.1, z, w - 0.44, d - 0.22, 0.55 + 0.15 * level, rnd=rnd)
            chimney(mb, rig if level == 2 else None, w / 2 - 1.0, cy + d / 2 - 0.9, z, z + 1.5 + 0.2 * level, 0.5 + 0.06 * level)
        boulders(mb, rnd, -w / 2, w / 2, cy + d / 2 - 0.1, cy + d / 2 + 0.2, 2 + level, 0.5 + 0.12 * level)
        if level >= 2:
            p.barrel(mb, w / 2 - 0.5, cy - d / 2 - 0.45, 0, 0.8, 0.28)
            bench(mb, -w / 2 + 1.3, cy - d / 2 - 0.5, 1.3)
        if level == 3:
            anvil(mb, w / 2 - 1.5, cy - d / 2 - 0.5)
            p.barrel(mb, w / 2 - 0.3, cy - d / 2 - 0.25, 0, 0.8, 0.28)
        p.finish(mb, "race_dwarf_house_%d" % level, rig)
    return build


def statue(mb, x, y, z, s=1.0, weapon="hammer"):
    """A stone dwarf standing guard, looking toward -Y."""
    mb.box((x, y, z + 0.2 * s), (1.3 * s, 1.0 * s, 0.4 * s), DARK)
    for sx in (-1, 1):
        mb.box((x + sx * 0.28 * s, y, z + 0.75 * s), (0.42 * s, 0.5 * s, 0.7 * s), WALL)
        mb.box((x + sx * 0.62 * s, y, z + 1.7 * s), (0.34 * s, 0.44 * s, 1.0 * s), WALL)
        mb.sphere((x + sx * 0.62 * s, y, z + 2.25 * s), 0.3 * s, "bronze", segments=6, rings=4)
    mb.box((x, y, z + 1.7 * s), (1.0 * s, 0.7 * s, 1.3 * s), WALL)
    mb.box((x, y - 0.36 * s, z + 1.35 * s), (1.02 * s, 0.06, 0.16 * s), "gold")
    mb.box((x, y, z + 2.65 * s), (0.6 * s, 0.6 * s, 0.6 * s), LIGHT)
    p.prism_xz(mb, [(x - 0.32 * s, z + 2.55 * s), (x, z + 1.55 * s), (x + 0.32 * s, z + 2.55 * s)], y - 0.44 * s, y - 0.28 * s, LIGHT)   # The beard.
    mb.cylinder((x, y, z + 2.9 * s), (x, y, z + 3.3 * s), 0.38 * s, 0.12 * s, "bronze", segments=8)
    mb.box((x, y - 0.28 * s, z + 2.92 * s), (0.66 * s, 0.1, 0.1 * s), "gold")
    mb.box((x, y - 0.62 * s, z + 1.25 * s), (0.14 * s, 0.14 * s, 1.9 * s), "d_door")                 # Both hands rest on the weapon.
    if weapon == "hammer":
        mb.box((x, y - 0.62 * s, z + 2.2 * s), (0.75 * s, 0.4 * s, 0.4 * s), "bronze")
    else:
        for sx in (-1, 1):
            p.prism_xz(mb, [(x, z + 1.95 * s), (x + sx * 0.5 * s, z + 1.75 * s), (x + sx * 0.5 * s, z + 2.55 * s), (x, z + 2.3 * s)][::sx], y - 0.67 * s, y - 0.57 * s, "bronze")


def center():
    """The hall under the mountain: 14 x 12 m."""
    mb = p.begin()
    rig = p.Rig()
    rnd = p.random.Random(47)
    for x, y, r, zs in ((-3.5, 3.4, 3.4, 1.9), (2.5, 3.8, 3.8, 2.1), (0, 2.6, 3.2, 2.6), (-5.6, 2.2, 2.2, 1.6), (5.6, 2.6, 2.2, 1.8)):   # The crag behind.
        mb.sphere((x, y, 0), r, "d_rock" if x < 1 else "d_rock_dark", segments=7, rings=5, scale=(1, 0.75, zs))
    mb.box((0, 3.4, 8.3), (1.6, 1.2, 0.3), "grass")
    w, d, h = 10.0, 5.0, 4.4
    cy = -1.0
    block(mb, 0, cy, 0, w, d, h, 0.3)
    block(mb, 0, cy + 0.5, h, 6.4, 3.6, 2.4, 0.22)
    slab_roof(mb, 0, cy + 0.4, h + 2.4, 6.0, 3.3, 0.9, metal="bronze")
    mb.box((0, cy - 0.2, h + 0.08), (w - 0.5, d - 0.4, 0.16), "d_roof_dark")
    with face(mb, 0, cy, w, d, "front") as L:
        p.arch_door(mb, 0, 0.6, 2.4, 3.3, LIGHT, "d_door", "gold", 0.3)
        mb.box((0, -0.42, 2.9), (0.7, 0.1, 0.7), "gold")                        # The clan's mark on the keystone.
        mb.box((0, -0.46, 2.9), (0.36, 0.1, 0.36), "d_banner")
        frieze(mb, L - 0.9, h - 0.5, "gold", 0.55)
        mb.box((0, -0.03, h - 0.95), (L - 0.9, 0.06, 0.07), "bronze")
        for sx in (-1, 1):
            for k in range(2):
                p.win(mb, sx * (2.5 + 1.3 * k), 2.0, 0.6, 1.0, LIGHT, "fire_win")
            runes(mb, sx * 1.75, 1.0, 3.2, "gold", 4)
        p.stairs(mb, 0, -1.9, 0, 0.6, 3.6, 1.9, DARK, 0.2)
        mb.box((0, -0.3, 0.3), (4.4, 0.6, 0.6), DARK)
    with face(mb, 0, cy + 0.5, 6.4, 3.6, "front", h) as L:
        for sx in (-2, -1, 0, 1, 2):
            p.win(mb, sx * 1.05, 1.1, 0.5, 0.9, LIGHT, "fire_win")
        frieze(mb, L - 0.7, 2.0, "gold", 0.45)
    for sx in (-1, 1):                                                          # The gate towers and their fires.
        tx = sx * 5.6
        block(mb, tx, cy - 1.2, 0, 2.6, 2.6, 6.4, 0.2)
        mb.box((tx, cy - 1.3, 6.5), (2.7, 2.7, 0.24), DARK)
        for a in range(4):
            cx_, cy_ = (1.1 * (1 if a % 2 else -1)), (1.1 * (1 if a < 2 else -1))
            mb.box((tx + cx_, cy - 1.3 + cy_, 6.9), (0.5, 0.5, 0.6), WALL)
        p.brazier(mb, rig, tx, cy - 1.3, 6.6, 1.5)
        with face(mb, tx, cy - 1.2, 2.6, 2.6, "front") as L:
            p.win(mb, 0, 4.6, 0.4, 0.9, LIGHT, "fire_win", cross=False)
            frieze(mb, L - 0.6, 5.7, "gold", 0.4)
            p.hang_banner(mb, rig, 0, -0.14, 3.8, 0.9, 2.2, "d_banner", "gold", "bronze")
        statue(mb, sx * 2.9, cy - d / 2 - 0.9, 0, 1.15, "hammer" if sx < 0 else "axe")
    chimney(mb, rig, -2.2, 2.4, 6.0, 9.0, 0.9)
    chimney(mb, rig, 3.0, 3.2, 6.5, 9.4, 0.8)
    for sx in (-1, 1):                                                          # A gallery mouth with its rails and cart.
        pass
    mb.box((4.2, cy - d / 2 - 0.3, 0.05), (0.1, 1.8, 0.1), "iron")
    mb.box((4.8, cy - d / 2 - 0.3, 0.05), (0.1, 1.8, 0.1), "iron")
    mb.box((4.5, cy - d / 2 - 0.7, 0.42), (0.8, 1.0, 0.5), "plank_dark")
    for k in range(4):
        mb.sphere((4.5 + rnd.uniform(-0.2, 0.2), cy - d / 2 - 0.7 + rnd.uniform(-0.3, 0.3), 0.72), 0.17, "gold", segments=5, rings=3)
    for sx in (-1, 1):
        mb.cylinder((4.5 + sx * 0.36, cy - d / 2 - 0.7, 0.16), (4.5 + sx * 0.44, cy - d / 2 - 0.7, 0.16), 0.14, 0.14, "iron", segments=8)
    with face(mb, 0, cy, w, d, "front"):
        p.arch_door(mb, 4.5, 0, 0.9, 1.4, DARK, "dark", None)
    boulders(mb, rnd, -6.6, 6.6, 4.4, 5.6, 8, 1.0)
    p.finish(mb, "race_dwarf_center", rig)


def workshop():
    """The forge: an open arch on the fire, a trip hammer and the stack."""
    mb = p.begin()
    rig = p.Rig()
    rnd = p.random.Random(48)
    w, d, h = 5.2, 3.6, 2.6
    cy = 0.9
    block(mb, 0, cy, 0, w, d, h)
    slab_roof(mb, 0, cy - 0.1, h, w - 0.44, d - 0.22, 0.7, turf=False)
    with face(mb, 0, cy, w, d, "front") as L:
        p.arch_door(mb, -0.6, 0, 2.2, 2.1, LIGHT, "dark", None, 0.14)
        mb.box((-0.6, -0.12, 0.45), (1.5, 0.1, 0.5), "ember")                    # The hearth seen through the arch.
        mb.box((-0.6, -0.14, 0.4), (1.0, 0.1, 0.3), "flame")
        p.win(mb, 1.75, 1.3, 0.55, 0.6, LIGHT, "fire_win")
        frieze(mb, L - 0.8, h - 0.4, "bronze")
    for sx in (-1, 1):
        buttress(mb, sx * (w / 2 + 0.08), cy - d / 2 + 0.5, 0, h * 0.85, 0.75, 0.75, sx)
    chimney(mb, rig, 1.2, cy + 0.6, h, h + 3.0, 1.0)
    mb.box((1.2, cy + 0.6, h + 1.4), (1.14, 1.14, 0.14), "bronze")
    anvil(mb, 0.4, -1.5)
    mb.box((-1.9, -1.4, 1.0), (0.3, 0.3, 2.0), DARK)                              # The trip hammer on its post.
    mb.cylinder((-1.9, -1.62, 1.8), (-1.9, -1.18, 1.8), 0.1, 0.1, "bronze", segments=6)
    with mb.bone("hammer"):
        p.beam(mb, (-2.7, -1.4, 1.8), (0.25, -1.4, 1.8), 0.14, "wood")
        mb.box((0.3, -1.4, 1.62), (0.4, 0.4, 0.55), "iron")
        mb.box((-2.7, -1.4, 1.8), (0.3, 0.3, 0.3), "d_dark")
    rig.bone("hammer", (-1.9, -1.4, 1.8), (-0.9, -1.4, 1.8), None)

    def strike(t):
        lift = p.kit.smooth(min(1.0, t / 0.6)) - p.kit.smooth(min(1.0, max(0.0, (t - 0.6) / 0.12)))
        return {"hammer": [(p.kit.Y, -22.0 * lift - 6.0)]}

    rig.add("strike", 1.6, strike)
    mb.box((2.2, -1.6, 0.3), (1.2, 0.6, 0.6), DARK)                               # The quench trough.
    mb.box((2.2, -1.6, 0.56), (1.0, 0.4, 0.06), "water")
    ingots(mb, -0.9, -2.2, 0, "iron", 3)
    ingots(mb, 2.3, -0.5, 0, "bronze", 2)
    for k in range(3):
        p.beam(mb, (1.3 + 0.14 * k, cy - d / 2 - 0.06, 0), (1.3 + 0.14 * k, cy - d / 2 - 0.02, 1.2), 0.05, "iron")
    boulders(mb, rnd, -2.6, 2.6, cy + d / 2 - 0.1, cy + d / 2 + 0.1, 4, 0.7)
    p.finish(mb, "race_dwarf_workshop", rig)


def storehouse():
    """The vault: a barrel of stone and a round bronze door."""
    mb = p.begin()
    rig = p.Rig()
    rnd = p.random.Random(49)
    w, d, h = 5.0, 4.6, 1.7
    cy = 0.5
    block(mb, 0, cy, 0, w, d, h, 0.18)
    for k in range(5):                                                           # The vault in stone ribs.
        y = cy - d / 2 + 0.25 + (d - 0.6) * k / 4
        mb.cylinder((0, y - 0.48, h - 0.1), (0, y + 0.48, h - 0.1), 2.25 if k % 2 == 0 else 2.12, 2.25 if k % 2 == 0 else 2.12, WALL if k % 2 else "d_roof_dark", segments=14)
    mb.box((0, cy - 0.1, h + 2.1), (0.5, d - 0.2, 0.2), "bronze")
    with face(mb, 0, cy, w, d, "front") as L:
        mb.cylinder((0, 0.1, 1.35), (0, -0.2, 1.35), 1.35, 1.35, DARK, segments=14)
        mb.cylinder((0, -0.1, 1.35), (0, -0.24, 1.35), 1.1, 1.1, "dark", segments=14)
        with mb.bone("door"):
            mb.cylinder((0, -0.22, 1.35), (0, -0.38, 1.35), 1.12, 1.12, "bronze", segments=14)
            p.ring(mb, 0, -0.4, 1.35, 0.8, 0.1, "gold", 12, "y")
            for k in range(4):
                a = TAU * k / 4 + TAU / 8
                p.beam(mb, (0, -0.42, 1.35), (math.cos(a) * 0.55, -0.42, 1.35 + math.sin(a) * 0.55), 0.09, "gold")
            mb.cylinder((0, -0.38, 1.35), (0, -0.5, 1.35), 0.2, 0.2, "gold", segments=8)
        p.hinge(mb, rig, "door", (-1.25, -0.25, 1.35), (0, 0, 1), -105.0, 3.0)
        mb.box((-1.3, -0.25, 1.35), (0.2, 0.3, 1.6), DARK)
        for sx in (-1, 1):
            runes(mb, sx * 2.0, 0.5, 1.5, "gold", 3)
    for sx in (-1, 1):
        for sy in (-1, 1):
            buttress(mb, sx * (w / 2 + 0.1), cy + sy * (d / 2 - 0.5), 0, 1.9, 0.75, 0.8, sx)
    ingots(mb, 1.9, -2.3, 0, "gold", 3)
    p.crate(mb, -1.9, -2.3, 0, 0.6)
    p.crate(mb, -2.4, -1.7, 0, 0.5)
    p.barrel(mb, 2.5, -1.7, 0, 0.8, 0.28)
    boulders(mb, rnd, -2.5, 2.5, cy + d / 2, cy + d / 2 + 0.1, 3, 0.7)
    p.finish(mb, "race_dwarf_storehouse", rig)


def keg(mb, x, y, z, r=0.36, length=0.9):
    """A barrel lying on its side along X."""
    mb.cylinder((x - length / 2, y, z), (x, y, z), r * 0.86, r, "plank", segments=9)
    mb.cylinder((x, y, z), (x + length / 2, y, z), r, r * 0.86, "plank", segments=9)
    for k in (-0.3, 0.3):
        mb.cylinder((x + k * length - 0.03, y, z), (x + k * length + 0.03, y, z), r * 0.99, r * 0.99, "iron", segments=9)
    mb.cylinder((x - length / 2 - 0.05, y, z - r * 0.4), (x - length / 2, y, z - r * 0.4), 0.04, 0.04, "bronze", segments=5)


def brewery():
    """The brew-forge: a hall and a great copper over the same fire, 8 x 6 m."""
    mb = p.begin()
    rig = p.Rig()
    rnd = p.random.Random(50)
    w, d, h = 5.0, 4.2, 2.6
    cx, cy = -1.3, 0.6
    block(mb, cx, cy, 0, w, d, h)
    slab_roof(mb, cx, cy - 0.1, h, w - 0.44, d - 0.22, 0.8)
    with face(mb, cx, cy, w, d, "front") as L:
        p.arch_door(mb, -1.0, 0, 1.2, 1.9, LIGHT, "d_door", "gold")
        p.win(mb, 1.2, 1.3, 0.6, 0.6, LIGHT, "fire_win")
        frieze(mb, L - 0.8, h - 0.42, "gold")
        mb.box((0.25, -0.5, 2.15), (0.08, 1.0, 0.08), "iron")                    # The sign of the tankard.
        with mb.bone("sign"):
            mb.box((0.25, -0.72, 1.7), (0.08, 0.62, 0.62), "d_door")
            for s in (-1, 1):
                mb.box((0.25 + s * 0.05, -0.72, 1.7), (0.03, 0.26, 0.34), "gold")
                mb.box((0.25 + s * 0.05, -0.54, 1.7), (0.03, 0.08, 0.2), "gold")
                mb.box((0.25 + s * 0.05, -0.72, 1.9), (0.03, 0.3, 0.07), "white")
        p.sway(mb, rig, "sign", (0.25, -0.72, 2.1), 9.0, 2.4, "swing", (0, 1, 0), (0.25, -0.72, 1.5))
    for sx in (-1, 1):
        buttress(mb, cx + sx * (w / 2 + 0.08), cy - d / 2 + 0.5, 0, h * 0.85, 0.75, 0.75, sx)
    chimney(mb, rig, cx - 1.4, cy + 1.0, h, h + 2.4, 0.7)
    kx, ky = 2.5, 0.5                                                           # The copper on its firebox.
    mb.cylinder((kx, ky, 0), (kx, ky, 0.9), 1.4, 1.3, DARK, segments=10)
    mb.cylinder((kx, ky, 0.86), (kx, ky, 0.98), 1.42, 1.42, LIGHT, segments=10)
    mb.box((kx, ky - 1.3, 0.45), (0.8, 0.3, 0.6), "dark")
    mb.box((kx, ky - 1.42, 0.38), (0.6, 0.1, 0.36), "ember")
    mb.box((kx, ky - 1.44, 0.32), (0.4, 0.1, 0.2), "flame")
    p.lathe(mb, kx, ky, 0.95, [(1.15, 0), (1.35, 0.6), (1.2, 1.3), (0.6, 1.9), (0.32, 2.3), (0.32, 2.8)], ("copper", "bronze", "copper", "copper", "bronze"), 10)
    mb.cylinder((kx, ky, 0.95 + 0.55), (kx, ky, 0.95 + 0.67), 1.37, 1.37, "gold", segments=10)
    p.arc(mb, [(kx, ky, 3.7), (kx - 0.3, ky, 4.15), (kx - 0.9, ky + 0.1, 4.1), (kx - 1.5, ky + 0.2, 3.3), (kx - 1.7, ky + 0.2, 2.9)], 0.15, "copper", 0.8)
    p.smoke(mb, rig, kx + 0.7, ky - 0.3, 3.0, 0.28, "white")
    mb.cylinder((kx + 0.7, ky - 0.3, 2.5), (kx + 0.7, ky - 0.3, 3.0), 0.08, 0.08, "bronze", segments=5)
    for x, z in ((-3.3, 0.36), (-2.5, 0.36), (-2.9, 0.98)):                       # Kegs, and a bench to try them.
        keg(mb, x, -2.35, z)
    bench(mb, 0.4, -2.5, 1.5)
    for k in range(3):
        mb.cylinder((0.0 + 0.4 * k, -2.5, 0.47), (0.0 + 0.4 * k, -2.5, 0.65), 0.07, 0.08, "bronze", segments=6)
    p.barrel(mb, 1.5, -1.9, 0, 0.85, 0.3)
    p.sack(mb, -1.5, -2.2, 0, 0.26)
    p.sack(mb, -1.1, -1.95, 0, 0.22)
    boulders(mb, rnd, -3.8, 3.6, cy + d / 2, cy + d / 2 + 0.2, 6, 0.8)
    p.finish(mb, "race_dwarf_brewery", rig)


def tower():
    """A squat watchtower: battered stone, a fire on top under bronze."""
    mb = p.begin()
    rig = p.Rig()
    block(mb, 0, 0, 0, 3.4, 3.4, 5.0, 0.35)
    mb.box((0, -0.17, 5.1), (3.3, 3.3, 0.24), DARK)
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.box((sx * 1.35, -0.17 + sy * 1.35, 5.75), (0.5, 0.5, 1.1), WALL)
            mb.box((sx * 1.35, -0.17 + sy * 1.35, 6.34), (0.6, 0.6, 0.12), "bronze")
        mb.box((sx * 1.45, -0.17, 5.45), (0.3, 2.2, 0.5), WALL)
        mb.box((0, -0.17 + sx * 1.45, 5.45), (2.2, 0.3, 0.5), WALL)
    p.hip_roof(mb, 0, -0.17, 6.4, 3.0, 3.0, 1.1, ("bronze", "d_roof_dark"), rows=2, over=0.25, ridge=0.8)
    mb.box((0, -0.17, 7.6), (0.9, 0.2, 0.2), "gold")
    p.brazier(mb, rig, 0, -0.17, 5.2, 1.3)
    with face(mb, 0, 0, 3.4, 3.4, "front") as L:
        p.arch_door(mb, 0, 0, 0.95, 1.6, LIGHT, "d_door", "gold")
        p.win(mb, 0, 3.0, 0.4, 0.9, LIGHT, "fire_win", cross=False)
        frieze(mb, L - 1.0, 4.4, "gold", 0.4)
        runes(mb, -1.0, 0.6, 2.0, "gold", 3)
        runes(mb, 1.0, 0.6, 2.0, "gold", 3)
    for side in ("left", "right"):
        with face(mb, 0, 0, 3.4, 3.4, side):
            p.hang_banner(mb, rig, 0, 0.1, 4.0, 0.7, 1.8, "d_banner", "gold", "bronze")
    p.finish(mb, "race_dwarf_tower", rig)


def shrine():
    """The ancestors' anvil: a stele with a stone face over a bronze anvil, 4 x 4 m."""
    mb = p.begin()
    rig = p.Rig()
    mb.box((0, 0, 0.12), (3.8, 3.6, 0.24), DARK)
    mb.box((0, 0.2, 0.34), (3.0, 2.8, 0.2), WALL)
    tbox(mb, 0, 1.1, 0.44, 3.6, 1.7, 0.7, 1.3, 0.55, WALL)                        # The stele.
    mb.box((0, 1.1, 3.65), (1.5, 0.7, 0.16), "bronze")
    with mb.placed((0, 0.74, 0.44), 0):
        mb.box((0, 0.0, 2.3), (0.7, 0.12, 0.7), LIGHT)                           # The ancestor's face: helm, brow and beard.
        p.prism_xz(mb, [(-0.36, 2.1), (0, 1.2), (0.36, 2.1)], -0.1, 0.02, LIGHT)
        mb.box((0, -0.05, 2.75), (0.8, 0.16, 0.26), "bronze")
        mb.box((0, -0.08, 2.5), (0.76, 0.1, 0.08), DARK)
        for sx in (-1, 1):
            mb.box((sx * 0.17, -0.07, 2.36), (0.14, 0.06, 0.08), "fire_win")
            runes(mb, sx * 0.5, 0.2, 1.6, "gold", 4)
        frieze(mb, 1.3, 3.0, "gold", 0.3)
    mb.box((0, -0.2, 0.74), (1.1, 0.8, 0.6), DARK)                               # The anvil of bronze on its block.
    mb.box((0, -0.2, 1.14), (0.4, 0.3, 0.2), "bronze")
    mb.box((0, -0.2, 1.32), (0.9, 0.36, 0.16), "bronze")
    mb.cylinder((0.45, -0.2, 1.32), (0.8, -0.2, 1.35), 0.1, 0.0, "bronze", segments=5)
    mb.box((-0.1, -0.2, 1.46), (0.34, 0.2, 0.14), "gold")
    for sx in (-1, 1):
        p.brazier(mb, rig, sx * 1.4, -1.2, 0.24, 1.0)
        ingots(mb, sx * 1.1, 0.0, 0.44, "gold", 2)
    p.finish(mb, "race_dwarf_shrine", rig)


def market_stall():
    """A stone counter under a slab on four stub pillars, 3 x 2 m."""
    mb = p.begin()
    rig = p.Rig()
    for sx in (-1, 1):
        for sy in (-1, 1):
            tbox(mb, sx * 1.25, sy * 0.75, 0, 2.0, 0.44, 0.44, 0.34, 0.34, WALL)
            mb.box((sx * 1.25, sy * 0.75, 2.04), (0.5, 0.5, 0.1), "bronze")
    p.hip_roof(mb, 0, 0, 2.1, 2.9, 1.9, 0.5, ("d_roof_dark", "d_roof"), rows=2, over=0.3, ridge=1.6, power=0.8)
    mb.box((0, 0, 2.66), (1.9, 0.5, 0.12), "grass")
    mb.box((0, -0.6, 0.45), (2.1, 0.5, 0.9), DARK)
    mb.box((0, -0.6, 0.93), (2.3, 0.62, 0.1), LIGHT)
    with mb.placed((0, -0.85, 0), 0):
        frieze(mb, 1.8, 0.6, "gold", 0.36)
    ingots(mb, -0.7, -0.6, 0.98, "iron", 2)
    ingots(mb, 0.0, -0.6, 0.98, "gold", 2)
    for k in range(3):                                                          # Hammers and picks laid out.
        mb.box((0.55 + 0.2 * k, -0.6, 1.0), (0.05, 0.45, 0.05), "d_door")
        mb.box((0.55 + 0.2 * k, -0.8, 1.02), (0.16, 0.1, 0.09), "iron")
    keg(mb, 0.0, 0.5, 0.36)
    p.barrel(mb, -1.0, 0.45, 0, 0.8, 0.28)
    mb.box((0, -1.05, 2.0), (0.06, 0.4, 0.06), "iron")
    with mb.bone("sign"):
        mb.box((0, -1.2, 1.7), (0.6, 0.06, 0.4), "d_door")
        mb.box((0, -1.24, 1.7), (0.3, 0.03, 0.12), "gold")
        mb.box((0, -1.24, 1.7), (0.1, 0.03, 0.26), "gold")
    p.sway(mb, rig, "sign", (0, -1.2, 1.95), 8.0, 2.4, "swing", (1, 0, 0), (0, -1.2, 1.6))
    p.finish(mb, "race_dwarf_market_stall", rig)


def well():
    """A well of stone with a bronze winch."""
    mb = p.begin()
    rig = p.Rig()
    mb.box((0, 0, 0.1), (2.6, 2.6, 0.2), DARK)
    tbox(mb, 0, 0, 0.2, 1.0, 1.9, 1.9, 1.7, 1.7, WALL)
    mb.box((0, 0, 1.02), (1.9, 1.9, 0.12), LIGHT)
    mb.box((0, 0, 1.06), (1.2, 1.2, 0.1), "dark")
    mb.box((0, 0, 0.98), (1.2, 1.2, 0.06), "water")
    with mb.placed((0, -0.95, 0.2), 0):
        frieze(mb, 1.3, 0.45, "gold", 0.3)
    for sx in (-1, 1):
        tbox(mb, sx * 0.8, 0, 1.08, 2.5, 0.34, 0.5, 0.26, 0.4, DARK)
    mb.box((0, 0, 2.6), (2.3, 0.9, 0.18), "d_roof")
    mb.box((0, 0, 2.74), (1.5, 0.5, 0.12), "bronze")
    with mb.bone("winch"):
        mb.cylinder((-0.7, 0, 2.0), (0.7, 0, 2.0), 0.12, 0.12, "bronze", segments=8)
        mb.cylinder((0.7, 0, 2.0), (1.15, 0, 2.0), 0.04, 0.04, "iron", segments=5)
        mb.box((1.15, 0, 1.85), (0.06, 0.06, 0.34), "iron")
        mb.cylinder((1.15, 0, 1.7), (1.4, 0, 1.7), 0.045, 0.045, "d_door", segments=5)
    p.spin(mb, rig, "winch", (0, 0, 2.0), (1, 0, 0), 4.0, "turn", (0.5, 0, 2.0))
    mb.cylinder((0, -0.12, 2.0), (0, -0.12, 1.45), 0.015, 0.015, "rope", segments=4)
    mb.cylinder((0, -0.12, 1.15), (0, -0.12, 1.45), 0.14, 0.17, "d_door", segments=8)
    p.finish(mb, "race_dwarf_well", rig)


def monument():
    """A stone warrior of the clan between two banners."""
    mb = p.begin()
    rig = p.Rig()
    mb.box((0, 0, 0.15), (3.0, 2.4, 0.3), DARK)
    tbox(mb, 0, 0.1, 0.3, 1.3, 2.0, 1.6, 1.7, 1.3, WALL)
    mb.box((0, 0.1, 1.36), (1.9, 1.5, 0.12), LIGHT)
    with mb.placed((0, -0.68, 0.3), 0):
        frieze(mb, 1.5, 0.75, "gold", 0.3)
        runes(mb, 0, 0.1, 0.55, "gold", 2)
    statue(mb, 0, 0.3, 1.4, 1.0, "axe")
    for sx in (-1, 1):
        mb.cylinder((sx * 1.3, -0.9, 0.3), (sx * 1.3, -0.9, 3.6), 0.07, 0.06, "bronze", segments=6)
        mb.sphere((sx * 1.3, -0.9, 3.66), 0.1, "gold", segments=6, rings=4)
        with mb.placed((sx * 1.3, -0.9, 0), 0):
            p.hang_banner(mb, rig, sx * 0.0, -0.08, 3.4, 0.6, 1.8, "d_banner", "gold", "bronze")
    p.finish(mb, "race_dwarf_monument", rig)


MODELS = {
    "race_dwarf_shrine": shrine, "race_dwarf_market_stall": market_stall, "race_dwarf_well": well, "race_dwarf_monument": monument,
    "race_dwarf_brewery": brewery, "race_dwarf_tower": tower,
    "race_dwarf_house_1": house(1), "race_dwarf_house_2": house(2), "race_dwarf_house_3": house(3),
    "race_dwarf_center": center, "race_dwarf_workshop": workshop, "race_dwarf_storehouse": storehouse,
}
