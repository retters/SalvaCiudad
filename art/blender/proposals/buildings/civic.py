"""Civic and noble buildings: wizard tower, lighthouse, church with a bell
tower, town hall with a clock tower, manor house, library, bank, market
hall and guard house."""

import math
import random

import parts as P
import castles
from parts import game, TAU

ROOF = ("roof", "roof_dark")


def storey(mb, rnd, kind, cx, cy, z0, w, d, h, plinth=0.6, cross=False):
    """One floor of a building in the given wall type."""
    if kind == "stone":
        P.stone_block(mb, cx, cy, z0, w, d, h, rnd, plinth=plinth, density=0.28)
    elif kind == "brick":
        P.stone_block(mb, cx, cy, z0, w, d, h, rnd, wall="brick", dark="brick_dark", light="trim", plinth=plinth,
                      density=0.3)
    elif kind == "log":
        P.log_block(mb, cx, cy, z0, w, d, h)
    else:
        if plinth:
            mb.box((cx, cy, z0 + plinth / 2), (w + 0.16, d + 0.16, plinth), "stone")
        P.framed_block(mb, cx, cy, z0 + plinth, w, d, h - plinth, infill="plaster", cross=cross)


def round_window(mb, x, y, r, a, z, w=0.55, h=0.8, glass="window", frame="trim"):
    c, s = math.cos(a), math.sin(a)
    mb.box((x + (r - 0.03) * c, y + (r - 0.03) * s, z), (0.22, w + 0.24, h + 0.22), frame, rotation_z=a)
    mb.box((x + (r + 0.02) * c, y + (r + 0.02) * s, z), (0.22, w, h), glass, rotation_z=a)


def railing_ring(mb, x, y, z, r, n=12, h=0.9, post="iron", rail="iron"):
    for i in range(n):
        a, a2 = TAU * i / n, TAU * (i + 1) / n
        c, s = math.cos(a), math.sin(a)
        mb.box((x + r * c, y + r * s, z + h / 2), (0.07, 0.07, h), post, rotation_z=a)
        for zz in (z + h * 0.55, z + h):
            P.beam(mb, (x + r * c, y + r * s, zz), (x + r * math.cos(a2), y + r * math.sin(a2), zz), 0.05, rail)


# --- Wizard tower ------------------------------------------------------------------------


def wizard_tower(mb, rig, seed=12):
    rnd = random.Random(seed)
    x, y, r, h, taper = 0.0, 0.6, 1.8, 12.0, 0.6

    def r_at(z):
        return (r + taper * (1 - z / h)) * math.cos(math.pi / 14)

    P.round_tower(mb, x, y, r, h, rnd, taper=taper, slits=0)
    for a, z in ((-1.2, 3.2), (0.4, 5.6), (2.2, 6.8), (-2.2, 8.6), (-0.6, 9.8), (1.4, 10.4)):
        round_window(mb, x, y, r_at(z), a, z, glass="glow")
    with mb.placed((x, y - r_at(1.0) - 0.03, 0)):
        P.arched_door(mb, 0, 0.1, w=1.0, h=2.0)
    # The study at the top, wider than the shaft.
    R = 2.7
    mb.cylinder((x, y, h - 1.4), (x, y, h), r, R, "wall_dark", segments=14)
    mb.cylinder((x, y, h), (x, y, h + 3.0), R, R, "wall", segments=14)
    mb.cylinder((x, y, h + 2.9), (x, y, h + 3.1), R + 0.12, R + 0.12, "wall_light", segments=14)
    for i in range(7):
        a = TAU * i / 7 - 1.3
        c, s = math.cos(a), math.sin(a)
        rr = R * math.cos(math.pi / 14)
        mb.box((x + (rr - 0.03) * c, y + (rr - 0.03) * s, h + 1.5), (0.22, 0.9, 1.8), "trim", rotation_z=a)
        mb.box((x + (rr + 0.02) * c, y + (rr + 0.02) * s, h + 1.5), (0.22, 0.6, 1.5), "magic" if i % 3 == 0 else "glow",
               rotation_z=a)
    tip = P.cone_roof(mb, x, y, h + 3.1, R, 7.0, ("purple", "purple_dark"), rows=7, eave=0.6, power=1.5, finial=None)
    mb.cylinder((x, y, tip - 0.4), (x + 0.5, y, tip + 0.5), 0.18, 0.02, "purple_dark", segments=6)  # The bent tip.
    # A turret growing out of the side.
    a = 2.5
    tx, ty = x + (r + 0.75) * math.cos(a), y + (r + 0.75) * math.sin(a)
    mb.cylinder((tx, ty, 5.4), (tx, ty, 6.8), 0.2, 0.9, "wall_dark", segments=10)
    mb.cylinder((tx, ty, 6.8), (tx, ty, 9.6), 0.9, 0.9, "wall", segments=10)
    round_window(mb, tx, ty, 0.87, a, 8.3, w=0.4, h=0.7, glass="magic")
    P.cone_roof(mb, tx, ty, 9.6, 0.9, 2.8, ("purple", "purple_dark"), rows=4, eave=0.3, power=1.4, seg=10)
    # A stair winding up around the foot to a high door.
    n = 20
    for i in range(n):
        t = (i + 0.5) / n
        aa = -0.9 + 3.6 * t
        z = 0.15 + 4.6 * t
        rr = r + taper * (1 - z / h) + 0.55
        mb.box((x + rr * math.cos(aa), y + rr * math.sin(aa), z), (1.1, 0.62, 0.14), "plank", rotation_z=aa)
        if i % 3 == 1:
            px, py = x + (rr + 0.45) * math.cos(aa), y + (rr + 0.45) * math.sin(aa)
            mb.box((px, py, z / 2), (0.12, 0.12, z), "timber", rotation_z=aa)
            mb.box((px, py, z + 0.5), (0.08, 0.08, 1.0), "timber", rotation_z=aa)
    aa = -0.9 + 3.6
    rr = r + taper * (1 - 4.8 / h)
    mb.box((x + (rr + 0.5) * math.cos(aa + 0.12), y + (rr + 0.5) * math.sin(aa + 0.12), 4.75), (1.2, 1.0, 0.14), "plank",
           rotation_z=aa)
    mb.box((x + rr * 0.97 * math.cos(aa + 0.12), y + rr * 0.97 * math.sin(aa + 0.12), 5.75), (0.24, 0.85, 1.8), "door",
           rotation_z=aa)
    # A balcony with a telescope at the study.
    by = y - R
    mb.box((x, by - 0.5, h + 0.2), (2.0, 1.2, 0.14), "plank")
    for sx in (-1, 1):
        P.beam(mb, (x + sx * 0.8, by + 0.3, h - 0.8), (x + sx * 0.8, by - 1.0, h + 0.15), 0.1, "timber")
        mb.box((x + sx * 0.95, by - 1.05, h + 0.75), (0.08, 0.08, 1.0), "timber")
    mb.box((x, by - 1.05, h + 1.2), (2.0, 0.08, 0.08), "timber")
    mb.cylinder((x + 0.3, by - 0.7, h + 1.0), (x + 0.3, by - 0.7, h + 0.3), 0.04, 0.04, "iron", segments=5)
    mb.cylinder((x + 0.3, by - 0.3, h + 0.9), (x + 0.3, by - 1.5, h + 1.6), 0.09, 0.13, "brass", segments=8)
    # The crystal floating over the roof, with three shards around it.
    cz = tip + 1.9
    with mb.bone("crystal"):
        mb.cylinder((x, y, cz), (x, y, cz + 0.9), 0.42, 0.0, "crystal", segments=6)
        mb.cylinder((x, y, cz), (x, y, cz - 0.9), 0.42, 0.0, "crystal", segments=6)
        for i in range(3):
            a = TAU * i / 3
            sx, sy = x + 1.0 * math.cos(a), y + 1.0 * math.sin(a)
            mb.cylinder((sx, sy, cz), (sx, sy, cz + 0.35), 0.14, 0.0, "magic", segments=5)
            mb.cylinder((sx, sy, cz), (sx, sy, cz - 0.35), 0.14, 0.0, "magic", segments=5)
    rig.bone("crystal", (x, y, cz), (x, y, cz + 1), None)
    rig.add("float", 4.0, lambda t: ({"crystal": [(P.kit.Z, 360 * t)]},
                                     {"crystal": (0, 0, 0.3 * math.sin(TAU * t))}))
    # The yard: a cauldron, a herb bed, mushrooms.
    mb.sphere((x + 2.6, y - 3.0, 0.45), 0.5, "charcoal", segments=8, rings=5, scale=(1, 1, 0.85))
    mb.cylinder((x + 2.6, y - 3.0, 0.72), (x + 2.6, y - 3.0, 0.78), 0.4, 0.4, "magic", segments=8)
    for i in range(3):
        a = TAU * i / 3
        P.beam(mb, (x + 2.6 + 0.6 * math.cos(a), y - 3.0 + 0.6 * math.sin(a), 0), (x + 2.6, y - 3.0, 1.5), 0.05, "iron")
    for i, (mx, my) in enumerate(((-2.6, -2.6), (-3.0, -2.0), (-2.2, -3.1))):
        mb.cylinder((mx, my, 0), (mx, my, 0.3 + 0.1 * i), 0.07, 0.06, "bone", segments=5)
        mb.cylinder((mx, my, 0.3 + 0.1 * i), (mx, my, 0.5 + 0.1 * i), 0.24, 0.03, "band", segments=7)
    game.garden_patch(mb, -2.4, 2.8)
    game.garden_patch(mb, -1.4, 3.2)


# --- Lighthouse --------------------------------------------------------------------------


def lighthouse(mb, rig, striped=True, seed=14):
    rnd = random.Random(seed)
    x, y, r, h, taper = 0.7, 0.9, 1.6, 13.0, 1.0

    def rr(z):
        return r + taper * (1 - z / h)

    mb.cylinder((x, y, 0), (x, y, 0.9), 3.3, 3.0, "rock", segments=12)
    P.rocks(mb, rnd, x, y, 3.6, n=14, size=0.9)
    mb.cylinder((x, y, 0.9), (x, y, h), rr(0.9), r, "wall", segments=14)
    if striped:
        for z0, z1 in ((3.2, 5.6), (8.0, 10.4)):
            mb.cylinder((x, y, z0), (x, y, z1), rr(z0) + 0.02, rr(z1) + 0.02, "band", segments=14)
    else:
        for _ in range(40):
            a, z = rnd.uniform(0, TAU), rnd.uniform(1.5, h - 0.8)
            q = rr(z) * math.cos(math.pi / 14)
            mb.box((x + q * math.cos(a), y + q * math.sin(a), z), (0.16, rnd.uniform(0.35, 0.6), 0.28),
                   rnd.choice(("wall_dark", "wall_light")), rotation_z=a)
    for a, z in ((-math.pi / 2, 4.4), (-math.pi / 2, 9.2), (0.6, 6.8), (2.6, 6.8), (math.pi / 2, 11.2), (-2.0, 11.4)):
        round_window(mb, x, y, rr(z) * math.cos(math.pi / 14), a, z, w=0.45, h=0.8)
    with mb.placed((x, y - rr(1.5) * math.cos(math.pi / 14) - 0.03, 0)):
        P.arched_door(mb, 0, 0.9, w=1.0, h=2.0)
        P.stairs(mb, 0, -1.3, 0.3, 0.9, 1.4, 1.2, mat="rock_dark")
    # The gallery and the lantern.
    mb.cylinder((x, y, h - 0.6), (x, y, h), r, r + 0.9, "wall_dark", segments=14)
    mb.cylinder((x, y, h), (x, y, h + 0.14), r + 0.95, r + 0.95, "iron", segments=14)
    railing_ring(mb, x, y, h + 0.14, r + 0.85, n=14)
    mb.cylinder((x, y, h + 0.14), (x, y, h + 0.7), 1.25, 1.25, "wall", segments=10)
    for i in range(10):
        a = TAU * i / 10
        mb.box((x + 1.2 * math.cos(a), y + 1.2 * math.sin(a), h + 1.6), (0.09, 0.09, 1.9), "iron", rotation_z=a)
    mb.cylinder((x, y, h + 2.5), (x, y, h + 2.7), 1.4, 1.4, "iron", segments=10)
    P.dome(mb, x, y, h + 2.7, 1.3, 1.2, ("copper", "copper_dark"), rows=3, seg=10, finial="brass")
    mb.cylinder((x, y, h + 0.7), (x, y, h + 1.2), 0.3, 0.3, "iron", segments=8)
    mb.cylinder((x, y, h + 1.2), (x, y, h + 2.1), 0.42, 0.42, "glow", segments=8)
    with mb.bone("lamp"):
        for s in (-1, 1):
            mb.box((x + s * 0.7, y, h + 1.65), (0.5, 0.75, 0.95), "glow")
            mb.box((x + s * 0.97, y, h + 1.65), (0.06, 0.95, 1.15), "brass")
        mb.box((x, y, h + 1.1), (2.0, 0.2, 0.08), "iron")
    rig.bone("lamp", (x, y, h + 1.1), (x, y, h + 2.1), None)
    rig.add("turn", 6.0, lambda t: {"lamp": [(P.kit.Z, 360 * t)]})
    # The keeper's cottage.
    with mb.placed((-1.7, -1.9, 0)):
        mb.box((0, 0, 0.45), (3.9, 3.3, 0.9), "rock_dark")
        storey(mb, rnd, "stone", 0, 0, 0.9, 3.6, 3.0, 2.3, plinth=0)
        P.gable_roof(mb, 0, 0, 3.6, 3.0, 3.2, 1.5, ("tile_red", "tile_red_dark"), rows=4, overhang=0.3, gable="wall")
        with P.face(mb, 0, 0, 3.6, 3.0, "front"):
            P.plank_door(mb, -0.8, 0.9, w=0.9, h=1.6)
            P.window(mb, 0.8, 2.1, w=0.6, h=0.6)
            P.stairs(mb, -0.8, -0.9, 0, 0.9, 1.1, 0.9, mat="rock")
        with P.face(mb, 0, 0, 3.6, 3.0, "left"):
            P.window(mb, 0, 2.1, w=0.6, h=0.6)
        P.chimney(mb, -1.1, 0.5, 3.2, 5.2, w=0.55)


# --- Church ------------------------------------------------------------------------------


def church(mb, rig, seed=16, spire=6.5):
    rnd = random.Random(seed)
    with mb.placed((0, -2.0, 0)):
        with mb.placed((0, 2.6, 0), math.pi / 2):
            castles.hall(mb, rnd, 10.0, 6.0, 5.4, 4.0, door_end="left", chimney=False, dormers=False, windows=4)
        # The apse.
        ay = 7.6
        mb.cylinder((0, ay, 0), (0, ay, 5.0), 2.5, 2.5, "wall", segments=12)
        mb.cylinder((0, ay, 0), (0, ay, 0.6), 2.7, 2.65, "wall_dark", segments=12)
        P.cone_roof(mb, 0, ay, 5.0, 2.5, 3.0, ROOF, rows=4, eave=0.35, power=1.0, finial=None)
        for a in (0.5, math.pi / 2, math.pi - 0.5):
            round_window(mb, 0, ay, 2.5 * math.cos(math.pi / 12), a, 3.0, w=0.6, h=1.8)
        # The bell tower at the front.
        ty, tw, th = -4.0, 3.6, 9.5
        P.stone_block(mb, 0, ty, 0, tw, tw, th, rnd, band=(th * 0.5,))
        with P.face(mb, 0, ty, tw, tw, "front"):
            P.arched_door(mb, 0, 0.05, w=1.6, h=2.8)
            P.arched_window(mb, 0, 4.4, w=0.8, h=1.8)
            mb.box((0, -0.6, 0.08), (2.4, 1.2, 0.16), "wall_dark")
        for side in ("left", "right"):
            with P.face(mb, 0, ty, tw, tw, side):
                P.arrow_slit(mb, 0, 3.0)
                P.arched_window(mb, 0, 6.2, w=0.6, h=1.3)
        mb.box((0, ty, th + 0.07), (tw + 0.3, tw + 0.3, 0.14), "wall_light")
        for side in P.SIDES:
            with P.face(mb, 0, ty, tw, tw, side):
                with mb.placed((0, 0.3, 0)):
                    P.arch_wall(mb, tw, 0.6, 2.7, 1.7, 2.1, z0=th + 0.14)
                P.arch_trim(mb, 0, 0, th + 0.14, 1.7, 2.1, t=0.18, depth=0.08)
        mb.box((0, ty, th + 2.92), (tw + 0.3, tw + 0.3, 0.16), "wall_light")
        tip = P.pyramid_roof(mb, 0, ty, th + 3.0, tw, tw, spire, ROOF, rows=6, overhang=0.3)
        mb.box((0, ty, tip + 0.5), (0.1, 0.1, 1.2), "gold")
        mb.box((0, ty, tip + 0.75), (0.6, 0.1, 0.1), "gold")
        # The bell, which swings.
        mb.box((0, ty, th + 2.5), (tw - 0.4, 0.2, 0.2), "timber")
        with mb.bone("bell"):
            mb.box((0, ty, th + 2.3), (1.0, 0.22, 0.24), "timber")
            mb.cylinder((0, ty, th + 1.2), (0, ty, th + 1.9), 0.62, 0.38, "bell", segments=10)
            mb.cylinder((0, ty, th + 1.9), (0, ty, th + 2.2), 0.38, 0.2, "bell", segments=10)
            mb.cylinder((0, ty, th + 1.5), (0, ty, th + 0.95), 0.05, 0.1, "iron", segments=5)
        head = mb.world((0, ty, th + 2.4))
        rig.bone("bell", head, head + P.Vector((0, 0, -1)), None)
        rig.add("ring", 2.0, lambda t: {"bell": [(P.kit.X, 26 * math.sin(TAU * t))]})
        # The churchyard.
        for i, (gx, gy) in enumerate(((-4.2, -3.6), (-4.0, -2.2), (-4.4, -0.8), (4.2, -3.2), (4.3, -1.8))):
            if i % 2:
                mb.box((gx, gy, 0.4), (0.5, 0.12, 0.8), "wall_dark")
                mb.cylinder((gx, gy - 0.06, 0.8), (gx, gy + 0.06, 0.8), 0.25, 0.25, "wall_dark", segments=8)
            else:
                mb.box((gx, gy, 0.5), (0.12, 0.12, 1.0), "wall_light")
                mb.box((gx, gy, 0.72), (0.5, 0.12, 0.12), "wall_light")


# --- Town hall ---------------------------------------------------------------------------


def clock(mb, rig, x, y, z, r=0.85, animated=True):
    """A clock face on the plane y, facing -Y; its long hand turns."""
    mb.cylinder((x, y + 0.02, z), (x, y - 0.1, z), r + 0.12, r + 0.12, "gold", segments=14)
    mb.cylinder((x, y, z), (x, y - 0.14, z), r, r, "white", segments=14)
    for i in range(12):
        a = TAU * i / 12
        mb.box((x + r * 0.82 * math.sin(a), y - 0.15, z + r * 0.82 * math.cos(a)), (0.07, 0.03, 0.07), "charcoal")
    mb.box((x + r * 0.22, y - 0.17, z + r * 0.12), (r * 0.5, 0.03, 0.09), "charcoal")  # The short hand.
    name = rig.name("hand") if animated else None
    if animated:
        with mb.bone(name):
            mb.box((x, y - 0.2, z + r * 0.36), (0.07, 0.03, r * 0.78), "charcoal")
            mb.cylinder((x, y - 0.15, z), (x, y - 0.23, z), 0.08, 0.08, "gold", segments=6)
        head = mb.world((x, y - 0.2, z))
        axis = mb.world_dir((0, 1, 0))
        rig.bone(name, head, head + P.Vector((0, 0, 0.5)), None)
        rig.add("tick", 12.0, lambda t: {name: [(axis, 360 * t)]})
    else:
        mb.box((x, y - 0.2, z + r * 0.36), (0.07, 0.03, r * 0.78), "charcoal")


def town_hall(mb, rig, upper="timber", seed=18):
    rnd = random.Random(seed)
    cx, cy, w, d, h1, h2 = 0.0, 1.0, 10.4, 6.0, 3.4, 3.2
    # Ground floor behind an arcade of four arches.
    storey(mb, rnd, "stone", cx, cy + 0.9, 0, w, d - 1.8, h1)
    n = 4
    for i in range(n):
        ax = cx - w / 2 + (i + 0.5) * w / n
        with mb.placed((ax, cy - d / 2 + 0.3, 0)):
            P.arch_wall(mb, w / n, 0.6, h1, w / n - 0.9, 2.8, mat="wall", inner="wall_dark")
            P.arch_trim(mb, 0, -0.3, 0, w / n - 0.9, 2.8, t=0.2, depth=0.08)
    mb.box((cx, cy - d / 2 + 1.0, 0.05), (w, 2.0, 0.1), "paving")
    with P.face(mb, cx, cy + 0.9, w, d - 1.8, "front") as L:
        for x in (-L * 0.36, L * 0.36):
            P.plank_door(mb, x, 0.1, w=1.0, h=1.8)
        for x in (-L * 0.14, L * 0.14):
            P.window(mb, x, 1.9, w=0.8, h=0.9, shutter=None, lit=True)
    # Upper floor and roof.
    z1 = h1 + 0.2
    W, D = w + 0.5, d + 0.5
    mb.box((cx, cy, h1 + 0.1), (W + 0.1, D + 0.1, 0.2), "timber" if upper == "timber" else "wall_light")
    storey(mb, rnd, upper, cx, cy, z1, W, D, h2, plinth=0, cross=True)
    for side in ("front", "back"):
        with P.face(mb, cx, cy, W, D, side) as L:
            for i in range(5):
                x = -L / 2 + (i + 0.5) * L / 5
                if side == "front" and i == 2:
                    continue
                P.arched_window(mb, x, z1 + 0.7, w=0.8, h=1.8)
    for side in ("left", "right"):
        with P.face(mb, cx, cy, W, D, side) as L:
            for x in (-L * 0.25, L * 0.25):
                P.arched_window(mb, x, z1 + 0.7, w=0.8, h=1.8)
    zr = z1 + h2
    P.pyramid_roof(mb, cx, cy, zr, W, D, 3.4, ROOF, rows=6, overhang=0.45, ridge=W - D)
    for x in (cx - 3.4, cx + 3.4):
        P.dormer(mb, x, cy - D / 2 + 0.8, zr + 0.8, w=1.0, h=0.8, depth=1.2, mats=ROOF, walls="plaster")
    P.chimney(mb, cx - 3.6, cy + 1.2, zr + 1.0, zr + 4.4, w=0.7, pots=2)
    P.chimney(mb, cx + 3.6, cy + 1.2, zr + 1.0, zr + 4.4, w=0.7, pots=2)
    # The clock tower, standing forward of the front.
    tw, th = 3.0, 13.0
    ty = cy - d / 2 - 0.2
    P.stone_block(mb, cx, ty, 0, tw, tw, th, rnd, band=(h1 + 0.1, zr + 0.2))
    with P.face(mb, cx, ty, tw, tw, "front"):
        P.arched_door(mb, 0, 0.05, w=1.5, h=2.7)
        P.wall_banner(mb, 0, 8.4, w=0.9, h=2.6)
        mb.box((0, -0.5, 4.3), (2.4, 1.0, 0.14), "wall_light")  # A balcony for proclamations.
        for sx in (-1, 0, 1):
            mb.box((sx * 1.1, -0.95, 4.85), (0.12, 0.12, 1.0), "wall_light")
        mb.box((0, -0.95, 5.3), (2.4, 0.14, 0.12), "wall_light")
        P.arched_door(mb, 0, 4.37, w=0.9, h=1.9)
        clock(mb, rig, 0, 0, 11.2)
    for side in ("left", "right"):
        with P.face(mb, cx, ty, tw, tw, side):
            clock(mb, rig, 0, 0, 11.2, animated=False)
    P.battlements(mb, cx, ty, th, tw, tw, merlon=0.45, gap=0.4, low=0.35, high=0.45, out=0.2)
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.box((cx + sx * 0.9, ty + sy * 0.9, th + 1.0), (0.3, 0.3, 2.0), "wall")
    mb.cylinder((cx, ty, th + 0.5), (cx, ty, th + 1.2), 0.5, 0.3, "bell", segments=8)
    mb.box((cx, ty, th + 1.4), (2.0, 0.14, 0.14), "timber")
    mb.box((cx, ty, th + 2.05), (2.4, 2.4, 0.14), "wall_light")
    tip = P.pyramid_roof(mb, cx, ty, th + 2.1, 2.2, 2.2, 3.4, ROOF, rows=4, overhang=0.3)
    P.flag(mb, rig, cx, ty, tip - 0.2, pole=2.0, length=1.4, pennant=False, height=0.8)
    # The square in front: steps, a notice board, benches.
    with mb.placed((cx, ty - tw / 2 - 0.9, 0)):
        mb.box((0, 0.3, 0.08), (2.6, 1.4, 0.16), "wall_dark")
    for sx in (-1, 1):
        mb.box((cx + sx * 3.6, cy - d / 2 - 1.3, 0.42), (1.6, 0.4, 0.08), "wood")
        for dx in (-0.6, 0.6):
            mb.box((cx + sx * 3.6 + dx, cy - d / 2 - 1.3, 0.2), (0.1, 0.36, 0.4), "wall_dark")


# --- Manor house -------------------------------------------------------------------------


def manor(mb, rig, ground="brick", upper="timber", seed=20):
    rnd = random.Random(seed)
    h1, h2, rise = 3.2, 2.9, 3.0
    z1 = h1 + 0.2
    # The main range, its ridge along X.
    mw, md, my = 8.4, 5.0, 1.6
    storey(mb, rnd, ground, 0, my, 0, mw, md, h1)
    mb.box((0, my, h1 + 0.1), (mw + 0.5, md + 0.5, 0.2), "timber")
    storey(mb, rnd, upper, 0, my, z1, mw + 0.4, md + 0.4, h2, plinth=0, cross=True)
    top = P.gable_roof(mb, 0, my, mw + 0.4, md + 0.4, z1 + h2, rise, ROOF, rows=7, overhang=0.4, gable=None, barge=None,
                       end_overhang=0.0)
    # Two cross wings with their gables toward the front.
    ww, wd, wy = 4.2, 8.0, 0.2
    for sx in (-1, 1):
        wx = sx * (mw / 2 + ww / 2 - 0.3)
        storey(mb, rnd, ground, wx, wy, 0, ww, wd, h1)
        mb.box((wx, wy, h1 + 0.1), (ww + 0.5, wd + 0.5, 0.2), "timber")
        storey(mb, rnd, upper, wx, wy, z1, ww + 0.4, wd + 0.4, h2, plinth=0, cross=True)
        with mb.placed((wx, wy, 0), math.pi / 2):
            P.gable_roof(mb, 0, 0, wd + 0.4, ww + 0.4, z1 + h2, rise * 0.95, ROOF, rows=6, overhang=0.4,
                         gable="plaster" if upper == "timber" else "wall", end_overhang=0.35)
        with P.face(mb, wx, wy, ww, wd, "front"):
            P.arched_window(mb, 0, 1.0, w=1.2, h=1.9)
        with P.face(mb, wx, wy, ww + 0.4, wd + 0.4, "front"):
            P.window(mb, 0, z1 + h2 * 0.55, w=1.0, h=1.0, flowers=True)
            P.window(mb, 0, z1 + h2 + 1.0, w=0.5, h=0.6, shutter=None)
        with P.face(mb, wx, wy, ww + 0.4, wd + 0.4, "right" if sx > 0 else "left") as L:
            for x in (-L * 0.28, L * 0.28):
                P.window(mb, x, z1 + h2 * 0.55, w=0.7, h=0.9)
        with P.face(mb, wx, wy, ww, wd, "right" if sx > 0 else "left") as L:
            for x in (-L * 0.28, L * 0.28):
                P.arched_window(mb, x, 1.1, w=0.7, h=1.5)
        P.chimney(mb, wx + sx * 1.0, wy + 2.4, z1 + h2 + 0.6, top + 1.3, w=0.75, mat="brick", cap="trim", pots=2)
    # The front of the main range: the door under a porch, windows, dormers.
    with P.face(mb, 0, my, mw, md, "front"):
        P.arched_door(mb, 0, 0.3, w=1.4, h=2.4)
        for x in (-2.6, 2.6):
            P.arched_window(mb, x, 1.0, w=0.8, h=1.7)
        P.stairs(mb, 0, -1.9, 0, 0.3, 2.6, 0.6)
        mb.box((0, -1.0, 0.15), (3.0, 1.6, 0.3), "wall_light")
        for sx in (-1, 1):
            mb.cylinder((sx * 1.1, -1.5, 0.3), (sx * 1.1, -1.5, 2.9), 0.16, 0.14, "trim", segments=8)
            mb.box((sx * 1.1, -1.5, 0.4), (0.44, 0.44, 0.2), "trim")
        mb.box((0, -0.9, 3.0), (2.9, 1.9, 0.2), "trim")
        P.prism_xz(mb, [(-1.5, 3.1), (1.5, 3.1), (0, 3.9)], -1.85, -1.65, "trim")
    with P.face(mb, 0, my, mw + 0.4, md + 0.4, "front"):
        for x in (-2.6, 0, 2.6):
            P.window(mb, x, z1 + h2 * 0.55, w=0.8, h=1.0)
    with P.face(mb, 0, my, mw + 0.4, md + 0.4, "back"):
        for x in (-2.8, -0.9, 0.9, 2.8):
            P.window(mb, x, z1 + h2 * 0.55, w=0.8, h=1.0)
    for x in (-1.8, 1.8):
        P.dormer(mb, x, my - md / 2 + 0.6, z1 + h2 + 0.7, w=1.0, h=0.8, depth=1.2, mats=ROOF, walls="plaster")
    P.chimney(mb, 0, my + 1.2, z1 + h2 + 1.2, top + 1.3, w=0.9, mat="brick", cap="trim", pots=3)
    # The forecourt: a low wall with gate piers, hedges and a little fountain.
    fy = -4.6
    for sx in (-1, 1):
        mb.box((sx * 4.2, fy, 0.45), (5.2, 0.35, 0.9), "wall")
        mb.box((sx * 4.2, fy, 0.94), (5.3, 0.45, 0.1), "wall_light")
        mb.box((sx * 1.4, fy, 0.8), (0.6, 0.6, 1.6), "wall")
        mb.box((sx * 1.4, fy, 1.66), (0.75, 0.75, 0.14), "wall_light")
        mb.sphere((sx * 1.4, fy, 1.9), 0.2, "wall_light", segments=6, rings=4)
        mb.box((sx * 1.6, -2.8, 0.35), (0.7, 2.4, 0.7), "hedge")
    mb.cylinder((0, -2.6, 0), (0, -2.6, 0.45), 0.9, 0.9, "wall", segments=10)
    mb.cylinder((0, -2.6, 0.42), (0, -2.6, 0.47), 0.72, 0.72, "water", segments=10)
    mb.cylinder((0, -2.6, 0.4), (0, -2.6, 1.1), 0.12, 0.1, "wall_light", segments=6)
    mb.cylinder((0, -2.6, 1.1), (0, -2.6, 1.2), 0.3, 0.36, "wall_light", segments=8)


def make(name, fn, colors, **kw):
    def build():
        mb = P.begin()
        rig = P.Rig()
        fn(mb, rig, **kw)
        P.finish(mb, name, colors, rig)
    return build


SLATE = dict(roof=0x5A6470, roof_dark=0x46505A)
RED = dict(roof=0xB0503A, roof_dark=0x8E3E2A)
WHITE = dict(wall=0xECE6D6, wall_dark=0xD0C8B4, wall_light=0xF6F2E6)

MODELS = {
    "bld_wizard_tower": make("bld_wizard_tower", wizard_tower, P.BASE),
    "bld_wizard_tower_dark": make("bld_wizard_tower_dark", wizard_tower,
                                  P.palette(wall=0x4C4854, wall_dark=0x36333C, wall_light=0x625E6C, trim=0x2A2830,
                                            purple=0x2C3A34, purple_dark=0x1E2A26, glow=0x7AE86A, magic=0x4AD06A,
                                            crystal=0x9AF07A)),
    "bld_lighthouse_striped": make("bld_lighthouse_striped", lighthouse, P.palette(**WHITE)),
    "bld_lighthouse_stone": make("bld_lighthouse_stone", lighthouse, P.BASE, striped=False),
    "bld_church_stone": make("bld_church_stone", church, P.palette(**SLATE)),
    "bld_church_blue": make("bld_church_blue", church, P.STONE_BLUE),
    "bld_town_hall_timber_blue": make("bld_town_hall_timber_blue", town_hall, P.BASE),
    "bld_manor_timber_blue": make("bld_manor_timber_blue", manor, P.BASE, ground="stone", upper="timber"),
    "bld_wizard_tower_blue": make("bld_wizard_tower_blue", wizard_tower, P.palette(purple=0x3F5F9E, purple_dark=0x324B80)),
    "bld_church_sandstone": make("bld_church_sandstone", church, P.SANDSTONE_RED),
    "bld_church_brick": make("bld_church_brick", church, P.BRICK_SLATE),
    "bld_town_hall_timber": make("bld_town_hall_timber", town_hall, P.palette(**RED)),
    "bld_town_hall_stone": make("bld_town_hall_stone", town_hall, P.palette(**SLATE), upper="stone"),
    "bld_town_hall_brick": make("bld_town_hall_brick", town_hall, P.palette(**SLATE), upper="brick"),
    "bld_manor_brick": make("bld_manor_brick", manor, P.palette(**SLATE)),
    "bld_manor_stone": make("bld_manor_stone", manor, P.palette(**RED), ground="stone", upper="stone"),
    "bld_manor_timber": make("bld_manor_timber", manor, P.palette(**RED), ground="stone", upper="timber"),
}
