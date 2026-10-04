"""Stone castles: one generator for three sizes (tower house, small castle,
great castle), in any stone palette."""

import math
import random

import parts as P
from parts import game

STYLE = {"roof_k": 1.0, "spikes": False}
ROOF = ("roof", "roof_dark")


def tower(mb, rig, rnd, x, y, r, h, top="cone", roof_h=None, flag=False, z0=0.0, slits=3, plinth=True,
          banner="banner"):
    """A round tower with a pointed roof. `top`: "cone" (the roof sits on
    the shaft), "crown" (battlements and a narrower roofed drum) or "open"
    (battlements only). Returns the height of its tip."""
    P.round_tower(mb, x, y, r, h, rnd, z0=z0, slits=slits, plinth=plinth)
    z = z0 + h
    k = STYLE["roof_k"]
    tip = z
    if top == "cone":
        mb.cylinder((x, y, z - 0.5), (x, y, z), r, r + 0.3, "wall", segments=14)
        mb.cylinder((x, y, z), (x, y, z + 0.14), r + 0.34, r + 0.34, "wall_light", segments=14)
        tip = P.cone_roof(mb, x, y, z + 0.14, r + 0.3, (roof_h or 2.3 * r + 1.0) * k, ROOF,
                          finial=None if flag else "gold")
    elif top == "crown":
        P.round_battlements(mb, x, y, z, r)
        rr = r * 0.68
        mb.cylinder((x, y, z), (x, y, z + 1.7), rr, rr, "wall", segments=12)
        for i in range(4):
            a = P.TAU * i / 4 + 0.4
            P.arrow_slit_round(mb, x, y, rr, a, z + 1.0, h=0.7)
        tip = P.cone_roof(mb, x, y, z + 1.7, rr, (roof_h or 2.6 * rr + 1.2) * k, ROOF, eave=0.4,
                          finial=None if flag else "gold")
    else:
        P.round_battlements(mb, x, y, z, r)
        tip = z + 1.1
    if STYLE["spikes"]:
        for i in range(6):
            a = P.TAU * i / 6
            c, s = math.cos(a), math.sin(a)
            mb.cylinder((x + r * c, y + r * s, z - 0.4), (x + (r + 0.9) * c, y + (r + 0.9) * s, z + 1.5), 0.14, 0.0,
                        "trim", segments=4)
    if flag:
        P.flag(mb, rig, x, y, tip - 0.3, pole=2.2, length=1.5 + r * 0.2, mat=banner)
    return tip


def square_tower(mb, rig, rnd, x, y, w, h, top="crown", roof_h=3.2, flag=False):
    P.stone_block(mb, x, y, 0, w, w, h, rnd, band=(h * 0.55,))
    for side in P.SIDES:
        with P.face(mb, x, y, w, w, side):
            P.arrow_slit(mb, 0, h * 0.42)
            P.arrow_slit(mb, 0, h * 0.78, h=0.8)
    P.battlements(mb, x, y, h, w, w)
    tip = h + 1.1
    if top == "crown":
        iw = w - 1.5
        mb.box((x, y, h + 0.8), (iw, iw, 1.6), "wall")
        for side in P.SIDES:
            with P.face(mb, x, y, iw, iw, side):
                P.arched_window(mb, 0, h + 0.45, w=0.5, h=0.9, sill=False)
        tip = P.pyramid_roof(mb, x, y, h + 1.6, iw, iw, roof_h * STYLE["roof_k"], ROOF, overhang=0.4,
                             finial=None if flag else "gold")
    if flag:
        P.flag(mb, rig, x, y, tip - 0.3, pole=2.2)
    return tip


def curtain(mb, rnd, p0, p1, h=6.0, thick=1.5, slits=True):
    """A stretch of curtain wall with a walk and battlements on its outer
    side: the right-hand side going from p0 to p1."""
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    L = math.hypot(dx, dy)
    with mb.placed(((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2, 0), math.atan2(dy, dx)):
        mb.box((0, 0, h / 2), (L, thick, h), "wall")
        mb.box((0, 0, 0.4), (L, thick + 0.4, 0.8), "wall_dark")
        mb.box((0, -thick / 2 - 0.06, h - 0.2), (L, 0.3, 0.3), "wall_dark")
        mb.box((0, 0, h + 0.02), (L, thick, 0.06), "paving")
        with mb.placed((0, -thick / 2 - 0.2, 0)):
            P.crenels(mb, L, h, "wall")
        mb.box((0, thick / 2 - 0.1, h + 0.2), (L, 0.2, 0.4), "wall_dark")
        with mb.placed((0, -thick / 2, 0)):
            P.scatter_face(mb, rnd, L - 1, 1.0, h - 0.5)
            if slits:
                n = int(L / 4)
                for i in range(n):
                    P.arrow_slit(mb, -L / 2 + (i + 0.5) * L / n, h * 0.55, h=0.9)
        with mb.placed((0, thick / 2, 0), math.pi):
            P.scatter_face(mb, rnd, L - 1, 1.0, h - 0.5)
        if STYLE["spikes"]:   # Iron spikes leaning out over the battlements.
            n = max(2, int(L / 1.1))
            for i in range(n):
                x = -L / 2 + (i + 0.5) * L / n
                mb.cylinder((x, -thick / 2 - 0.1, h + 0.9), (x, -thick / 2 - 0.55, h + 1.9), 0.09, 0.0, "trim", segments=4)


def gatehouse(mb, rig, rnd, w=6.0, d=4.6, h=8.5, open_w=2.8, open_h=3.7, flank_r=1.9, flank_h=11.0,
              flank=True, flags=True):
    """A gate with an arched passage, a portcullis and (maybe) two flanking
    towers. Local frame: centered, front toward -Y."""
    P.arch_wall(mb, w, d, h, open_w, open_h)
    for s in (-1, 1):
        mb.box((s * (w / 2 + open_w / 2) / 2, 0, 0.4), ((w - open_w) / 2 + 0.3, d + 0.3, 0.8), "wall_dark")
    mb.box((0, 0, 0.03), (open_w, d + 2.0, 0.06), "paving")
    P.arch_trim(mb, 0, -d / 2, 0, open_w, open_h)
    with mb.placed((0, d / 2, 0), math.pi):
        P.arch_trim(mb, 0, 0, 0, open_w, open_h)
    P.portcullis(mb, rig, 0, -d / 2 + 0.7, 0, open_w + 0.1, open_h)
    # The doors, open against the walls of the passage.
    for s in (-1, 1):
        mb.box((s * (open_w / 2 - 0.08), d / 2 - 1.0, open_h * 0.42), (0.12, 1.3, open_h * 0.84), "door")
        for z in (0.7, open_h * 0.6):
            mb.box((s * (open_w / 2 - 0.16), d / 2 - 1.0, z), (0.04, 1.3, 0.1), "iron")
    with mb.placed((0, -d / 2, 0)):
        P.arched_window(mb, 0, open_h + 1.3, w=0.7, h=1.4)
        for s in (-1, 1):
            P.wall_banner(mb, s * (open_w / 2 + 0.75), open_h + 3.0, w=0.8, h=2.6)
        P.scatter_face(mb, rnd, w - 1, open_h + 0.5, h - 0.6)
        mb.box((0, -0.05, open_h + 0.75), (w, 0.14, 0.14), "wall_light")
    P.battlements(mb, 0, 0, h, w, d)
    if STYLE["spikes"]:   # A horned skull over the gate.
        zs = open_h + 2.9
        mb.sphere((0, -d / 2 - 0.25, zs), 0.6, "wall_light", segments=7, rings=5, scale=(1, 0.8, 1.05))
        mb.box((0, -d / 2 - 0.45, zs - 0.55), (0.6, 0.4, 0.45), "wall_light")
        for s in (-1, 1):
            mb.box((s * 0.24, -d / 2 - 0.68, zs + 0.02), (0.2, 0.16, 0.2), "window")
            mb.cylinder((s * 0.45, -d / 2 - 0.2, zs + 0.3), (s * 1.35, -d / 2 - 0.5, zs + 1.25), 0.2, 0.0, "trim", segments=5)
        for k in range(4):
            mb.box((-0.21 + k * 0.14, -d / 2 - 0.66, zs - 0.72), (0.08, 0.06, 0.16), "trim")
    # A roofed chamber over the gate, for the winch.
    mb.box((0, 0.2, h + 0.9), (w - 1.6, d - 1.6, 1.8), "wall")
    for side in ("front", "back"):
        with P.face(mb, 0, 0.2, w - 1.6, d - 1.6, side):
            P.arched_window(mb, 0, h + 0.5, w=0.5, h=0.9, sill=False)
    P.pyramid_roof(mb, 0, 0.2, h + 1.8, w - 1.6, d - 1.6, 2.6 * STYLE["roof_k"], ROOF, overhang=0.4,
                   ridge=max(0.0, w - d) * 0.8, finial="gold")
    if flank:
        for s in (-1, 1):
            tower(mb, rig, rnd, s * (w / 2 + flank_r * 0.55), -d / 2 + flank_r - 0.6, flank_r, flank_h, top="cone",
                  flag=flags)


def hall(mb, rnd, w, d, h, rise, door_end="left", chimney=True, buttress=True, windows=None, roof=ROOF,
         dormers=True):
    """A stone hall with a steep roof, its ridge along local X; the great
    door and a round window are on one gable end."""
    P.stone_block(mb, 0, 0, 0, w, d, h, rnd)
    top = P.gable_roof(mb, 0, 0, w, d, h, rise * STYLE["roof_k"], roof, rows=7, overhang=0.45, gable="wall",
                       barge="wall_light")
    n = windows or max(2, int(w / 2.6))
    for side in ("front", "back"):
        with P.face(mb, 0, 0, w, d, side) as L:
            for i in range(n):
                x = -L / 2 + (i + 0.5) * L / n
                P.arched_window(mb, x, h * 0.3, w=0.8, h=h * 0.5)
            if buttress:
                for i in range(n + 1):
                    x = -L / 2 + i * L / n
                    x = max(-L / 2 + 0.35, min(L / 2 - 0.35, x))
                    mb.box((x, -0.3, h * 0.4), (0.6, 0.7, h * 0.8), "wall")
                    P.prism_yz(mb, [(-0.65, h * 0.8), (0.05, h * 0.8), (0.05, h * 0.98)], x - 0.3, x + 0.3,
                               "wall_light")
    with P.face(mb, 0, 0, w, d, door_end):
        P.arched_door(mb, 0, 0.05, w=1.7, h=2.8)
        mb.cylinder((0, 0.05, h + rise * 0.22), (0, -0.1, h + rise * 0.22), 0.8, 0.8, "trim", segments=12)
        mb.cylinder((0, 0.0, h + rise * 0.22), (0, -0.14, h + rise * 0.22), 0.6, 0.6, "window", segments=12)
        mb.box((0, -0.15, h + rise * 0.22), (1.2, 0.04, 0.06), "trim")
        mb.box((0, -0.15, h + rise * 0.22), (0.06, 0.04, 1.2), "trim")
    if dormers:
        for i in range(max(1, n - 1)):
            x = -w / 2 + (i + 1) * w / n
            P.dormer(mb, x, -d / 2 + d * 0.16, h + rise * 0.18, w=0.9, h=0.8, depth=1.3, mats=roof)
    if chimney:
        P.chimney(mb, w * 0.3, d * 0.2, h, top + 0.9, w=0.8, pots=2)
    return top


def keep(mb, rig, rnd, cx, cy, w, d, h, turrets=4, turret_r=1.1, central=None, flag=True, stairs=True):
    """The great tower: a tall block with battlements, a roof inside them,
    corner turrets and maybe a taller round tower rising from its roof."""
    P.stone_block(mb, cx, cy, 0, w, d, h, rnd, band=(h * 0.36, h * 0.7))
    levels = [h * 0.2, h * 0.45, h * 0.78]
    for side in P.SIDES:
        with P.face(mb, cx, cy, w, d, side) as L:
            n = max(2, int(L / 2.6))
            for li, z in enumerate(levels):
                for i in range(n):
                    x = -L / 2 + (i + 0.5) * L / n
                    if side == "front" and li == 0 and abs(x) < 1.6:
                        continue
                    if li == 0:
                        P.arrow_slit(mb, x, z + 0.6)
                    else:
                        P.arched_window(mb, x, z, w=0.7, h=1.5 if li == 1 else 1.2)
    with P.face(mb, cx, cy, w, d, "front"):
        P.arched_door(mb, 0, 1.2, w=1.6, h=2.7)
        P.wall_banner(mb, -2.2, h * 0.72, w=0.9, h=3.0)
        P.wall_banner(mb, 2.2, h * 0.72, w=0.9, h=3.0)
    if stairs:
        with mb.placed((cx, cy - d / 2 - 2.6, 0)):
            P.stairs(mb, 0, 0, 0, 1.2, 2.4, 1.8)
            mb.box((0, 2.2, 0.6), (2.8, 0.9, 1.2), "wall_dark")
            for s in (-1, 1):
                mb.box((s * 1.3, 1.3, 0.9), (0.25, 2.7, 1.8), "wall")
                mb.box((s * 1.3, 0.0, 1.9), (0.4, 0.4, 0.3), "wall_light")
    P.battlements(mb, cx, cy, h, w, d)
    k = STYLE["roof_k"]
    mb.box((cx, cy, h + 0.5), (w - 1.8, d - 1.8, 1.0), "wall")
    P.pyramid_roof(mb, cx, cy, h + 1.0, w - 1.8, d - 1.8, min(w, d) * 0.42 * k, ROOF, rows=5, overhang=0.35,
                   ridge=max(0.0, w - d))
    corners = [(-1, -1), (1, -1), (1, 1), (-1, 1)][:turrets]
    for sx, sy in corners:
        tx, ty = cx + sx * (w / 2 + 0.15), cy + sy * (d / 2 + 0.15)
        zb = h - 3.4
        mb.cylinder((tx, ty, zb - 1.3), (tx, ty, zb), 0.25, turret_r, "wall_dark", segments=12)
        tower(mb, rig, rnd, tx, ty, turret_r, 6.4, top="cone", z0=zb, slits=2, plinth=False,
              roof_h=turret_r * 3.2)
    tip = h + 4
    if central:
        ox, oy, r, extra = central
        tip = tower(mb, rig, rnd, cx + ox, cy + oy, r, extra, top="crown", z0=h + 0.2, flag=flag, slits=4,
                    plinth=False, roof_h=r * 2.9)
    return tip


def courtyard_props(mb, rnd, spots):
    for kind, x, y in spots:
        if kind == "barrel":
            game.barrel(mb, x, y, h=0.8, r=0.3)
        elif kind == "crate":
            game.crate(mb, x, y, s=0.6)
        elif kind == "hay":
            P.hay_bale(mb, x, y)
        elif kind == "dummy":
            mb.box((x, y, 0.8), (0.1, 0.1, 1.6), "timber")
            mb.box((x, y, 1.25), (0.7, 0.09, 0.09), "timber")
            mb.sphere((x, y, 1.62), 0.2, "hay", segments=6, rings=4)
            mb.box((x, y, 1.05), (0.34, 0.2, 0.5), "hay")
        elif kind == "well":
            P.well(mb, x, y)


def paving(mb, rnd, w, d, cx=0.0, cy=0.0, n=40):
    mb.box((cx, cy, 0.03), (w, d, 0.06), "paving")
    for _ in range(n):
        mb.box((cx + rnd.uniform(-w / 2 + 0.6, w / 2 - 0.6), cy + rnd.uniform(-d / 2 + 0.6, d / 2 - 0.6), 0.065),
               (rnd.uniform(0.5, 1.0), rnd.uniform(0.4, 0.8), 0.03), "paving_light")


def timber_house(mb, rnd, w, d, h, rise, roof=("shingle", "shingle_dark"), door=True):
    """A plain timber-framed service building, its ridge along local X."""
    mb.box((0, 0, 0.25), (w + 0.1, d + 0.1, 0.5), "wall_dark")
    P.framed_block(mb, 0, 0, 0.5, w, d, h - 0.5)
    P.gable_roof(mb, 0, 0, w, d, h, rise, roof, rows=5, overhang=0.35, gable="plaster")
    with P.face(mb, 0, 0, w, d, "front") as L:
        if door:
            P.plank_door(mb, 0, 0.0, w=1.0, h=1.7)
        for x in (-L * 0.3, L * 0.3):
            P.window(mb, x, h * 0.6, w=0.6, h=0.6)


# --- The three sizes ---------------------------------------------------------------------


def great_castle(mb, rig, seed=7):
    rnd = random.Random(seed)
    X, YF, YB = 15.4, -13.4, 13.4
    H, T = 6.5, 1.6
    paving(mb, rnd, 2 * X, YB - YF, 0, 0, n=90)
    gw = 6.0
    curtain(mb, rnd, (-X, YF), (-gw / 2, YF), H, T)
    curtain(mb, rnd, (gw / 2, YF), (X, YF), H, T)
    curtain(mb, rnd, (X, YF), (X, YB), H, T)
    curtain(mb, rnd, (X, YB), (-X, YB), H, T)
    curtain(mb, rnd, (-X, YB), (-X, YF), H, T)
    tower(mb, rig, rnd, -X, YF, 2.4, 11.0, top="crown", flag=True)
    tower(mb, rig, rnd, X, YF, 2.4, 11.0, top="crown", flag=True)
    tower(mb, rig, rnd, -X, YB, 2.4, 13.5, top="cone", flag=False)
    tower(mb, rig, rnd, X, YB, 2.4, 12.5, top="cone", flag=True)
    square_tower(mb, rig, rnd, -X, 0.5, 4.0, 9.5, top="crown")
    square_tower(mb, rig, rnd, X, -1.0, 4.0, 9.5, top="crown")
    tower(mb, rig, rnd, -6.5, YB, 2.0, 11.0, top="cone")
    with mb.placed((0, YF, 0)):
        gatehouse(mb, rig, rnd, w=gw, d=4.6, h=8.5)
    # The keep with its great round tower.
    keep(mb, rig, rnd, 4.5, 6.0, 10.0, 9.0, 13.0, central=(1.6, 1.2, 2.4, 8.0))
    # The great hall, its ridge along Y and its door toward the courtyard.
    with mb.placed((-8.6, 5.5, 0), math.pi / 2):
        hall(mb, rnd, 12.0, 7.0, 6.0, 4.6, door_end="left")
    # A gallery from the hall to the keep.
    with mb.placed((-2.8, 6.0, 0)):
        mb.box((0, 0, 2.3), (4.6, 3.0, 4.6), "wall")
        P.gable_roof(mb, 0, 0, 4.6, 3.0, 4.6, 1.8 * STYLE["roof_k"], ROOF, rows=4, overhang=0.3, gable=None,
                     barge=None, end_overhang=0.0)
        with P.face(mb, 0, 0, 4.6, 3.0, "front"):
            for x in (-1.0, 1.0):
                P.arched_window(mb, x, 1.6, w=0.7, h=1.6)
    # The chapel, by the east wall.
    with mb.placed((10.2, -6.0, 0), math.pi / 2):
        hall(mb, rnd, 8.0, 4.6, 4.4, 3.2, door_end="left", chimney=False, dormers=False)
    mb.box((10.2, -9.2, 8.2), (1.3, 1.3, 2.0), "wall")
    P.pyramid_roof(mb, 10.2, -9.2, 9.2, 1.3, 1.3, 2.6 * STYLE["roof_k"], ROOF, rows=3, overhang=0.25, finial="gold")
    mb.box((10.2, -9.87, 8.5), (0.5, 0.06, 0.8), "window")
    # Barracks and stable against the west wall.
    with mb.placed((-11.0, -6.6, 0), math.pi / 2):
        timber_house(mb, rnd, 8.0, 5.0, 3.2, 2.2)
    # The stair up to the wall walk.
    with mb.placed((4.2, YF + T / 2 + 0.7, 0), -math.pi / 2):
        P.stairs(mb, 0, 0, 0, H, 1.3, 7.0)
    courtyard_props(mb, rnd, [
        ("well", -2.0, -5.5), ("barrel", -7.6, -3.2), ("barrel", -7.0, -3.4), ("barrel", -7.4, -2.6),
        ("crate", 6.6, -2.0), ("crate", 7.3, -2.2), ("hay", -7.6, -9.4), ("hay", -7.6, -8.6),
        ("dummy", -4.5, -9.0), ("dummy", -3.0, -9.6), ("crate", 12.8, 1.6), ("barrel", 13.2, 2.6),
    ])


def small_castle(mb, rig, seed=11):
    rnd = random.Random(seed)
    X, YF, YB = 8.3, -8.0, 8.3
    H, T = 5.0, 1.3
    paving(mb, rnd, 2 * X, YB - YF, 0, (YF + YB) / 2, n=30)
    gw = 4.8
    curtain(mb, rnd, (-X, YF), (-gw / 2, YF), H, T)
    curtain(mb, rnd, (gw / 2, YF), (X, YF), H, T)
    curtain(mb, rnd, (X, YF), (X, YB), H, T)
    curtain(mb, rnd, (X, YB), (-X, YB), H, T)
    curtain(mb, rnd, (-X, YB), (-X, YF), H, T)
    tower(mb, rig, rnd, -X, YF, 1.55, 8.5, top="cone", flag=True)
    tower(mb, rig, rnd, X, YF, 1.55, 8.5, top="cone", flag=True)
    tower(mb, rig, rnd, -X, YB, 1.55, 9.5, top="crown")
    tower(mb, rig, rnd, X, YB, 1.55, 9.5, top="cone")
    with mb.placed((0, YF, 0)):
        gatehouse(mb, rig, rnd, w=gw, d=3.6, h=6.8, open_w=2.4, open_h=3.2, flank=False)
    keep(mb, rig, rnd, 2.2, 3.6, 7.0, 6.0, 10.0, turrets=2, turret_r=0.9, central=(1.4, 1.0, 1.6, 5.5))
    with mb.placed((-4.8, 3.2, 0), math.pi / 2):
        timber_house(mb, rnd, 6.0, 4.0, 3.0, 2.0)
    with mb.placed((3.4, YF + T / 2 + 0.6, 0), -math.pi / 2):
        P.stairs(mb, 0, 0, 0, H, 1.1, 4.0)
    courtyard_props(mb, rnd, [("well", -3.6, -3.4), ("barrel", -6.6, -1.0), ("barrel", -6.0, -1.2),
                              ("crate", 6.6, -1.4), ("hay", -6.4, -5.6), ("dummy", 0.5, -3.0)])


def tower_house(mb, rig, seed=5):
    rnd = random.Random(seed)
    cx, cy, w, d, h = -0.5, 0.9, 5.4, 5.2, 10.0
    P.stone_block(mb, cx, cy, 0, w, d, h, rnd, band=(h * 0.4, h * 0.72))
    for side in P.SIDES:
        with P.face(mb, cx, cy, w, d, side) as L:
            for x in (-L * 0.25, L * 0.25):
                P.arrow_slit(mb, x, 2.0)
                P.arched_window(mb, x, 4.6, w=0.7, h=1.4)
                P.arched_window(mb, x, 7.4, w=0.6, h=1.2)
    with P.face(mb, cx, cy, w, d, "front"):
        P.arched_door(mb, 0, 0.05, w=1.2, h=2.2)
        P.wall_banner(mb, 0, 7.0, w=0.8, h=2.6)
    P.battlements(mb, cx, cy, h, w, d)
    mb.box((cx, cy, h + 0.6), (w - 1.6, d - 1.6, 1.2), "plaster")
    for side in P.SIDES:
        with P.face(mb, cx, cy, w - 1.6, d - 1.6, side) as L:
            P.timber_face(mb, L, h, h + 1.2, spacing=1.0, braces=False, rail=False)
    P.pyramid_roof(mb, cx, cy, h + 1.2, w - 1.6, d - 1.6, 3.0 * STYLE["roof_k"], ROOF, rows=4, overhang=0.4,
                   finial="gold")
    # The stair turret at the front right corner, taller than the house.
    tower(mb, rig, rnd, 2.3, -1.5, 1.3, 12.5, top="cone", flag=True)
    # A bartizan on the opposite corner.
    tx, ty = cx - w / 2 - 0.1, cy + d / 2 + 0.1
    mb.cylinder((tx, ty, 6.0), (tx, ty, 7.2), 0.2, 0.85, "wall_dark", segments=12)
    tower(mb, rig, rnd, tx, ty, 0.85, 5.0, top="cone", z0=7.2, slits=2, plinth=False)
    # A low yard wall with a gate arch in front.
    mb.box((-2.6, -3.5, 0.9), (2.4, 0.5, 1.8), "wall")
    mb.box((-2.6, -3.5, 1.86), (2.5, 0.6, 0.14), "wall_light")
    mb.box((-3.6, -2.4, 0.9), (0.5, 2.2, 1.8), "wall")
    game.barrel(mb, -2.9, -2.4, h=0.8, r=0.3)
    game.crate(mb, -2.2, -2.7, s=0.55)
    P.chimney(mb, cx - 1.4, cy + 1.0, h + 1.2, h + 4.6, w=0.6)


def pine(mb, x, y, h=4.0, r=1.1):
    mb.cylinder((x, y, 0), (x, y, h * 0.3), 0.16, 0.12, "log", segments=6)
    for i in range(3):
        z = h * (0.2 + 0.25 * i)
        mb.cylinder((x, y, z), (x, y, z + h * 0.36), r * (1 - 0.25 * i), 0.0, "grass_dark" if i % 2 else "leaves", segments=7)


def crag_castle(mb, rig, seed=13, great=False):
    """A castle on top of a crag, with a ramp on arches up to its gate: the
    castle on the cliff of the reference picture. The small castle, or the
    great one."""
    rnd = random.Random(seed)
    if great:
        H, RX, RY, n, e, x0, stones = 8.0, 21.5, 19.8, 24, 0.35, -26.0, 64
    else:
        H, RX, RY, n, e, x0, stones = 6.0, 12.4, 12.4, 18, 0.6, -15.0, 34

    def rim(a, k=1.0):
        c, s = math.cos(a), math.sin(a)
        return (k * RX * math.copysign(abs(c) ** e, c), k * RY * math.copysign(abs(s) ** e, s))

    crag = mb.prism([rim(P.TAU * i / n) for i in range(n)], 0.0, H, "rock")
    for v in crag:
        if v.co.z < 1.0:
            v.co.x *= 1.1
            v.co.y *= 1.1
    mb.prism([rim(P.TAU * i / n, 0.985) for i in range(n)], H, H + 0.06, "grass")
    for i in range(stones):
        x, y = rim(rnd.uniform(0, P.TAU), rnd.uniform(0.98, 1.06))
        if y < -RY + 1.5 and x0 < x < 3:
            continue  # The ramp runs here.
        r = rnd.uniform(1.4, 2.6) * (1.25 if great else 1.0)
        mb.sphere((x, y, rnd.uniform(0.3, H - r * 0.9)), r, rnd.choice(("rock", "rock_dark", "rock_dark")), segments=6, rings=4,
                  scale=(1, 1, rnd.uniform(1.0, 1.5)))
    for i in range(8 if not great else 16):
        x, y = rim(rnd.uniform(0, P.TAU), 0.93)
        mb.sphere((x, y, H), rnd.uniform(0.5, 0.9), "grass_dark", segments=6, rings=4, scale=(1, 1, 0.35))
    # The ramp along the front of the crag, on arches, up to the gate.
    x1, y0, y1 = -1.6, -RY - 2.7, -RY + 0.3
    P.prism_xz(mb, [(x0, 0.0), (x1, 0.0), (x1, H)], y0, y1, "wall")
    mb.box(((x1 + 2.2) / 2, (y0 + y1) / 2, H / 2), (2.2 - x1, y1 - y0, H), "wall")
    mb.box(((x1 + 2.2) / 2, (y0 + y1) / 2, H + 0.03), (2.2 - x1, y1 - y0, 0.06), "paving")
    slope = H / (x1 - x0)
    P.prism_xz(mb, [(x0, 0.0), (x1, H), (x1, H + 0.06), (x0, 0.06)], y0 + 0.3, y1, "paving")
    P.prism_xz(mb, [(x0, 0.0), (x1, H), (x1, H + 0.9), (x0, 0.9)], y0, y0 + 0.35, "wall_dark")
    mb.box(((x1 + 2.2) / 2, y0 + 0.17, H + 0.45), (2.2 - x1, 0.35, 0.9), "wall_dark")
    mb.box((2.2 - 0.17, (y0 + y1) / 2 - 0.4, H + 0.45), (0.35, y1 - y0 - 0.8, 0.9), "wall_dark")
    arches = 5 if not great else 8
    for i in range(1, arches):  # Blind arches under the ramp.
        ax = x0 + (x1 - x0) * (i + 0.35) / arches
        top = (ax - x0) * slope - 0.9
        if top > 1.4:
            w = 1.7
            mb.box((ax, y0 - 0.02, (top - w / 2) / 2), (w, 0.1, top - w / 2), "wall_dark")
            mb.cylinder((ax, y0 + 0.03, top - w / 2), (ax, y0 - 0.07, top - w / 2), w / 2, w / 2, "wall_dark", segments=10)
    merlons = 6 if not great else 11
    for i in range(merlons):
        mx = x0 + (x1 - x0) * (i + 0.5) / merlons
        mb.box((mx, y0 + 0.17, (mx - x0) * slope + 1.15), (0.7, 0.35, 0.5), "wall")
    k = RX / 12.4
    for x, y in ((-14.6, -9.0), (13.8, -6.0), (14.2, 4.5), (-13.6, 8.5), (5.5, -15.2), (9.0, -14.6)):
        pine(mb, x * k, y * RY / 12.4, h=rnd.uniform(3.5, 5.0) * (1.3 if great else 1.0))
    with mb.placed((0, 0, H)):
        (great_castle if great else small_castle)(mb, rig, seed if not great else 7)


def great_crag_castle(mb, rig):
    crag_castle(mb, rig, great=True)


def moat_castle(mb, rig, seed=11):
    """The small castle on an island in a moat, with a drawbridge that can
    be raised (clips `raise` and `lower`)."""
    rnd = random.Random(seed + 100)
    hin, hout, cy, top = 11.4, 14.4, 0.15, 0.18
    mb.box((0, cy, 0.05), (2 * hout, 2 * hout, 0.1), "water")
    mb.box((0, cy, top / 2), (2 * hin - 0.4, 2 * hin - 0.4, top), "grass")
    for side in P.SIDES:
        with P.face(mb, 0, cy, 2 * hin, 2 * hin, side) as L:
            mb.box((0, 0.2, 0.17), (L, 0.4, 0.34), "wall_dark")
            P.scatter_face(mb, rnd, L - 1, 0.02, 0.36, density=0.5, size=(0.6, 0.14))
        with P.face(mb, 0, cy, 2 * hout + 1.2, 2 * hout + 1.2, side) as L:
            mb.box((0, 0.3, 0.2), (L, 0.6, 0.4), "wall_dark")
            mb.box((0, 0.3, 0.42), (L, 0.7, 0.06), "wall_light")
    for _ in range(12):   # Lily pads and reeds in the water.
        side = rnd.choice((-1, 1))
        a = rnd.uniform(-hout + 1, hout - 1)
        b = side * rnd.uniform(hin + 0.6, hout - 0.6)
        x, y = (a, cy + b) if rnd.random() < 0.5 else (b, cy + a)
        if abs(x) < 2.5 and y < 0:
            continue
        mb.cylinder((x, y, 0.1), (x, y, 0.13), rnd.uniform(0.25, 0.45), 0.3, "leaves", segments=7)
    # The causeway from the gate to the edge of the island and the bridgehead on the far bank.
    y_in, y_out = cy - hin + 0.2, cy - hout - 0.1
    mb.box((0, (-9.6 + y_in) / 2, 0.2), (3.2, -9.6 - y_in + 0.4, 0.4), "wall")
    mb.box((0, y_out - 0.5, 0.2), (3.6, 1.6, 0.4), "wall")
    for s in (-1, 1):
        mb.box((s * 1.7, y_out - 0.2, 0.7), (0.5, 0.5, 1.4), "wall")
        mb.box((s * 1.7, y_out - 0.2, 1.45), (0.62, 0.62, 0.12), "wall_light")
        mb.box((s * 1.5, y_in + 0.1, 0.6), (0.4, 0.4, 0.8), "wall")
    with mb.bone("bridge"):
        L = y_in - y_out + 0.3
        yc = y_in - L / 2
        mb.box((0, yc, 0.36), (2.8, L, 0.12), "plank")
        for i in range(int(L / 0.45)):
            mb.box((0, y_in - 0.2 - i * 0.45, 0.425), (2.8, 0.04, 0.02), "plank_dark")
        for s in (-1, 1):
            mb.box((s * 1.4, yc, 0.4), (0.16, L, 0.24), "timber")
            mb.box((s * 1.4, y_in - L + 0.2, 0.75), (0.1, 0.1, 0.6), "iron")
            mb.box((s * 1.4, y_in - L / 2, 0.75), (0.1, 0.1, 0.6), "iron")
            mb.box((s * 1.4, y_in - L * 0.75 + 0.1, 1.02), (0.06, L / 2, 0.06), "iron")
    rig.bone("bridge", (0, y_in, 0.36), (0, y_in - 1.0, 0.36), None)
    rig.add("raise", 3.0, lambda t: {"bridge": [(P.kit.X, -78 * P.kit.smooth(t))]}, loops=False)
    rig.add("lower", 3.0, lambda t: {"bridge": [(P.kit.X, -78 * (1 - P.kit.smooth(t)))]}, loops=False)
    with mb.placed((0, 0, top)):
        small_castle(mb, rig, seed)


BUILDERS = {"great": great_castle, "small": small_castle, "tower": tower_house, "crag": crag_castle, "moat": moat_castle,
            "great_crag": great_crag_castle}


def make(name, colors, size, spiky=False):
    def build():
        STYLE["roof_k"] = 1.45 if spiky else 1.0
        STYLE["spikes"] = spiky
        mb = P.begin()
        rig = P.Rig()
        BUILDERS[size](mb, rig)
        P.finish(mb, name, colors, rig)
        STYLE["roof_k"], STYLE["spikes"] = 1.0, False
    return build


MODELS = {}
for _size, _key in (("great", "castle_great"), ("small", "castle_small"), ("tower", "castle_tower_house"),
                    ("crag", "castle_crag"), ("moat", "castle_moat"), ("great_crag", "castle_great_crag")):
    for _mat, _colors, _spiky in (("stone", P.STONE_BLUE, False), ("sandstone", P.SANDSTONE_RED, False),
                                  ("brick", P.BRICK_SLATE, False), ("dark", P.DARK_EVIL, True)):
        _name = "%s_%s" % (_key, _mat)
        MODELS[_name] = make(_name, _colors, _size, _spiky)
