"""Last additions: ruins left by fire and war, a cemetery with a crypt and a
free-standing bell tower."""

import math
import random

import parts as P
from extra import bell_tower
from parts import game, TAU


def burnt_house(mb, rig, seed=140):
    rnd = random.Random(seed)
    w, d = 4.8, 3.6
    mb.cylinder((0, 0.3, 0), (0, 0.3, 0.03), 3.6, 3.6, "charcoal", segments=12)
    mb.box((0, 0.3, 0.2), (w + 0.2, d + 0.2, 0.4), "stone")
    mb.box((0, 0.3, 0.38), (w - 0.3, d - 0.3, 0.08), "charcoal")
    # Charred posts of uneven height and what is left of two walls.
    for sx in (-1, 0, 1):
        for sy in (-1, 1):
            hh = rnd.uniform(0.8, 2.6)
            x, y = sx * w / 2, 0.3 + sy * d / 2
            mb.box((x, y, 0.4 + hh / 2), (0.16, 0.16, hh), "charcoal")
            mb.cylinder((x, y, 0.4 + hh), (x + rnd.uniform(-0.05, 0.05), y, 0.4 + hh + 0.3), 0.09, 0.0, "charcoal", segments=4)
    P.prism_xz(mb, [(-w / 2, 0.4), (-0.6, 0.4), (-0.9, 1.3), (-1.6, 1.1), (-w / 2, 2.3)], 0.3 + d / 2 - 0.08, 0.3 + d / 2 + 0.08, "white_dark")
    P.prism_yz(mb, [(0.3 - d / 2, 0.4), (0.3 + d / 2, 0.4), (0.3 + d / 2, 2.2), (0.6, 1.4), (0.3 - d / 2, 1.9)], w / 2 - 0.08, w / 2 + 0.08,
               "white_dark")
    mb.box((w / 2, 0.3, 0.5), (0.2, d, 0.14), "charcoal")
    mb.box((-1.4, 0.3 + d / 2, 0.5), (2.0, 0.2, 0.14), "charcoal")
    # Fallen roof beams, rubble and ash, and embers still glowing.
    for i in range(7):
        a = rnd.uniform(0, TAU)
        x, y = rnd.uniform(-1.6, 1.6), 0.3 + rnd.uniform(-1.2, 1.2)
        L = rnd.uniform(1.4, 2.8)
        P.beam(mb, (x - L / 2 * math.cos(a), y - L / 2 * math.sin(a), 0.45), (x + L / 2 * math.cos(a), y + L / 2 * math.sin(a), rnd.uniform(0.5, 1.8)),
               0.12, "charcoal")
    for i in range(10):
        x, y = rnd.uniform(-2.2, 2.2), 0.3 + rnd.uniform(-1.6, 1.6)
        mb.sphere((x, y, 0.45), rnd.uniform(0.2, 0.45), rnd.choice(("wall_dark", "stone_dark", "charcoal")), segments=5, rings=3, scale=(1, 1, 0.5))
    for x, y in ((-0.6, 0.2), (0.9, 0.8), (0.2, -0.5)):
        mb.box((x, y, 0.5), (0.3, 0.2, 0.08), "ember")
    # The chimney stands alone, blackened at the top.
    mb.box((1.3, 1.5, 1.9), (0.8, 0.8, 3.8), "stone")
    mb.box((1.3, 1.5, 3.9), (0.84, 0.84, 0.8), "charcoal")
    mb.box((1.3, 1.0, 0.9), (0.9, 0.3, 1.0), "stone_dark")
    mb.box((1.3, 0.86, 0.75), (0.5, 0.06, 0.6), "charcoal")
    # A singed door frame, a fallen shutter, a bucket.
    for s in (-0.5, 0.5):
        mb.box((-1.2 + s, 0.3 - d / 2, 1.2), (0.14, 0.14, 1.6), "timber")
    mb.box((-1.2, 0.3 - d / 2, 2.05), (1.2, 0.16, 0.16), "charcoal")
    mb.box((1.0, -2.2, 0.06), (0.4, 0.7, 0.05), "shutter", rotation_z=0.4)
    mb.cylinder((-2.6, -1.8, 0), (-2.6, -1.8, 0.3), 0.14, 0.18, "wood", segments=7)


def ruined_tower(mb, rig, seed=142):
    rnd = random.Random(seed)
    x, y, r = 0.0, 0.3, 2.3
    P.round_tower(mb, x, y, r, 4.0, rnd, slits=2, bands=False, density=0.3)
    # A broken crown: the wall stands higher on one side.
    n = 18
    for i in range(n):
        a = TAU * i / n
        hh = max(0.2, 3.6 * (0.5 + 0.5 * math.cos(a - 2.2)) ** 1.5 + rnd.uniform(-0.3, 0.5))
        mb.box((x + (r - 0.3) * math.cos(a), y + (r - 0.3) * math.sin(a), 4.0 + hh / 2), (0.6, 2 * r * math.tan(math.pi / n) + 0.05, hh),
               "wall" if i % 3 else "wall_dark", rotation_z=a)
    mb.cylinder((x, y, 3.9), (x, y, 4.0), r - 0.5, r - 0.5, "wall_dark", segments=12)
    q = r * math.cos(math.pi / 14)
    with mb.placed((x, y - q - 0.02, 0)):
        P.arch_trim(mb, 0, 0, 0, 1.2, 2.2, t=0.22, depth=0.12)
        mb.box((0, 0.0, 0.8), (1.2, 0.12, 1.6), "charcoal")
        mb.cylinder((0, 0.06, 1.6), (0, -0.06, 1.6), 0.6, 0.6, "charcoal", segments=10)
    # Fallen blocks, ivy and a sapling growing inside.
    for _ in range(16):
        a = rnd.uniform(-0.5, 2.0)
        rr = rnd.uniform(r + 0.4, r + 2.6)
        s = rnd.uniform(0.35, 0.8)
        mb.box((x + rr * math.cos(a), y + rr * math.sin(a), s * 0.3), (s * 1.3, s, s * 0.6), rnd.choice(("wall", "wall_dark", "wall_light")),
               rotation_z=rnd.uniform(0, 3))
    for _ in range(14):
        a = rnd.uniform(1.5, 4.5)
        z = rnd.uniform(0.5, 5.5)
        mb.sphere((x + (q + 0.05) * math.cos(a), y + (q + 0.05) * math.sin(a), z), rnd.uniform(0.3, 0.6), rnd.choice(("leaves", "moss", "leaf_dark")),
                  segments=5, rings=3, scale=(1, 1, 0.9))
    mb.cylinder((x + 0.4, y + 0.2, 4.0), (x + 0.6, y + 0.3, 6.2), 0.1, 0.06, "bark", segments=5)
    mb.sphere((x + 0.6, y + 0.3, 6.8), 1.0, "leaf", segments=6, rings=4, scale=(1, 1, 0.8))
    mb.box((x - 2.9, y - 2.0, 0.5), (0.1, 0.1, 1.0), "timber")
    mb.box((x - 2.9, y - 2.05, 0.9), (0.7, 0.05, 0.3), "wood_light")


def cemetery(mb, rig, seed=144):
    rnd = random.Random(seed)
    W, D = 9.0, 8.0
    mb.box((0, 0, 0.03), (W, D, 0.06), "grass_dark")
    # The wall and the lychgate.
    for x, y, w, d in ((0, D / 2, W, 0.4), (-W / 2, 0, 0.4, D), (W / 2, 0, 0.4, D), (-2.9, -D / 2, 3.2, 0.4), (2.9, -D / 2, 3.2, 0.4)):
        mb.box((x, y, 0.5), (w, d, 1.0), "wall")
        mb.box((x, y, 1.04), (w + 0.1, d + 0.1, 0.1), "wall_light")
    for s in (-1, 1):
        mb.box((s * 1.1, -D / 2, 1.2), (0.22, 0.22, 2.4), "timber")
        P.beam(mb, (s * 1.1, -D / 2, 1.7), (s * 0.5, -D / 2, 2.3), 0.09, "timber")
    P.gable_roof(mb, 0, -D / 2, 2.6, 1.4, 2.4, 0.9, ("shingle", "shingle_dark"), rows=3, overhang=0.25, gable=None, barge="timber")
    mb.box((0, -D / 2, 0.03), (2.0, 1.6, 0.07), "paving")
    mb.box((0, -1.6, 0.04), (1.4, 4.4, 0.06), "paving")
    # The crypt: a little stone temple with an iron door.
    cx, cy = 0.0, 2.2
    P.stone_block(mb, cx, cy, 0, 3.2, 2.6, 2.4, rnd, density=0.2)
    mb.box((cx, cy, 2.5), (3.6, 3.0, 0.2), "wall_light")
    P.prism_xz(mb, [(cx - 1.8, 2.6), (cx + 1.8, 2.6), (cx, 3.5)], cy - 1.5, cy + 1.5, "wall")
    P.prism_xz(mb, [(cx - 1.95, 2.55), (cx, 3.6), (cx, 3.75), (cx - 1.95, 2.7)], cy - 1.6, cy + 1.6, "wall_dark")
    P.prism_xz(mb, [(cx + 1.95, 2.55), (cx + 1.95, 2.7), (cx, 3.75), (cx, 3.6)], cy - 1.6, cy + 1.6, "wall_dark")
    with P.face(mb, cx, cy, 3.2, 2.6, "front"):
        P.arched_door(mb, 0, 0.05, w=1.0, h=1.9, door="iron", iron="wall_dark")
        for s in (-1, 1):
            mb.cylinder((s * 1.1, -0.3, 0), (s * 1.1, -0.3, 2.4), 0.18, 0.15, "wall_light", segments=8)
        mb.box((0, -0.25, 3.0), (0.1, 0.08, 0.6), "gold")
        mb.box((0, -0.25, 3.1), (0.4, 0.08, 0.1), "gold")
    # Graves in rows: headstones, crosses and slabs.
    k = 0
    for x in (-3.4, -2.2, 2.2, 3.4):
        for y in (-2.6, -1.2, 0.2, 1.6, 3.0):
            k += 1
            if rnd.random() < 0.15:
                continue
            kind = k % 3
            if kind == 0:
                mb.box((x, y + 0.3, 0.4), (0.5, 0.12, 0.8), "wall_dark")
                mb.cylinder((x, y + 0.24, 0.8), (x, y + 0.36, 0.8), 0.25, 0.25, "wall_dark", segments=8)
            elif kind == 1:
                mb.box((x, y + 0.3, 0.5), (0.12, 0.12, 1.0), "wall_light")
                mb.box((x, y + 0.3, 0.72), (0.5, 0.12, 0.12), "wall_light")
            else:
                mb.box((x, y, 0.12), (0.6, 1.1, 0.14), "wall")
            if k % 4 == 0:
                mb.sphere((x + 0.2, y - 0.1, 0.14), 0.1, rnd.choice(("flowers", "flowers_y", "cloth_white")), segments=5, rings=3)
    # A yew, a fresh grave with a spade, a lantern.
    mb.cylinder((3.2, -3.0, 0), (3.2, -3.0, 0.8), 0.16, 0.12, "bark_dark", segments=6)
    mb.cylinder((3.2, -3.0, 0.6), (3.2, -3.0, 4.2), 1.0, 0.0, "leaf_dark", segments=8)
    mb.sphere((-3.0, -3.2, 0.05), 0.6, "earth", segments=6, rings=4, scale=(0.7, 1.4, 0.4))
    P.beam(mb, (-2.4, -3.4, 0), (-2.3, -3.2, 1.2), 0.03, "wood")
    mb.box((-2.42, -3.44, 0.12), (0.2, 0.04, 0.26), "iron")
    mb.box((1.4, -3.3, 0.8), (0.08, 0.08, 1.6), "timber")
    mb.box((1.4, -3.5, 1.5), (0.06, 0.4, 0.06), "timber")
    mb.box((1.4, -3.66, 1.25), (0.18, 0.18, 0.26), "glow")


def campanile(mb, rig, seed=146):
    rnd = random.Random(seed)
    mb.box((0, 0, 0.1), (6.0, 6.0, 0.2), "paving")
    for i in range(10):
        mb.box((rnd.uniform(-2.6, 2.6), rnd.uniform(-2.6, 2.6), 0.205), (rnd.uniform(0.5, 0.9), rnd.uniform(0.4, 0.7), 0.02), "paving_light")
    with mb.placed((0, 0.4, 0.2)):
        bell_tower(mb, rig, rnd, 0, 0, 3.2, 12.0, 6.0)
        with P.face(mb, 0, 0, 3.2, 3.2, "front"):
            mb.cylinder((0, 0.02, 9.6), (0, -0.1, 9.6), 0.8, 0.8, "gold", segments=14)
            mb.cylinder((0, 0.0, 9.6), (0, -0.14, 9.6), 0.68, 0.68, "white", segments=14)
            mb.box((0, -0.16, 9.85), (0.06, 0.03, 0.5), "charcoal")
            mb.box((0.15, -0.16, 9.6), (0.34, 0.03, 0.06), "charcoal")
    for s in (-1, 1):
        mb.box((s * 2.3, -1.9, 0.6), (1.4, 0.4, 0.08), "wall_light")
        for dx in (-0.5, 0.5):
            mb.box((s * 2.3 + dx, -1.9, 0.4), (0.12, 0.34, 0.4), "wall_dark")


def guild_hall(mb, rig, seed=148):
    """A brick hall with crow-stepped gables toward the street."""
    from civic import storey
    rnd = random.Random(seed)
    cx, cy, w, d, h = 0.0, 0.6, 7.6, 6.4, 6.6
    storey(mb, rnd, "brick", cx, cy, 0, w, d, h)
    mb.box((cx, cy, 3.3), (w + 0.14, d + 0.14, 0.16), "trim")
    rise = 4.2
    with mb.placed((cx, cy, 0), math.pi / 2):
        P.gable_roof(mb, 0, 0, d - 0.5, w, h, rise, ("roof", "roof_dark"), rows=7, overhang=0.3, gable="brick", end_overhang=0.0, barge=None)
    # The stepped gables, front and back, standing above the roof.
    steps = 6
    for sy in (-1, 1):
        y = cy + sy * (d / 2 - 0.2)
        for i in range(steps):
            ww = (w + 0.4) * (1 - i / steps)
            z0 = h + i * (rise + 0.8) / steps
            mb.box((cx, y, z0 + 0.45), (ww, 0.44, 0.9), "brick")
            for s in (-1, 1):
                mb.box((cx + s * (ww / 2 - 0.3), y, z0 + 0.94), (0.7, 0.54, 0.1), "trim")
        mb.box((cx, y, h + rise + 1.3), (0.5, 0.5, 0.9), "brick")
        mb.cylinder((cx, y, h + rise + 1.75), (cx, y, h + rise + 2.5), 0.3, 0.0, "trim", segments=4)
    with P.face(mb, cx, cy, w, d, "front") as L:
        P.arched_door(mb, 0, 0.1, w=1.7, h=2.9)
        for x in (-2.6, 2.6):
            P.arched_window(mb, x, 1.0, w=0.9, h=1.9)
        for x in (-2.6, 0, 2.6):
            P.arched_window(mb, x, 4.0, w=0.9, h=2.0)
        for x in (-1.0, 1.0):
            P.arched_window(mb, x, h + 0.9, w=0.6, h=1.4, sill=False)
        mb.cylinder((0, 0.02, h + 3.2), (0, -0.14, h + 3.2), 0.5, 0.5, "gold", segments=10)
        mb.box((0, -0.6, h + rise - 0.2), (0.16, 1.4, 0.16), "timber")
        mb.box((0, -1.2, h + rise - 0.9), (0.03, 0.03, 1.3), "rope")
        # The shields of the trades over the door.
        for i, c in enumerate(("banner", "band", "cloth_green", "banner2", "purple")):
            x = -1.6 + i * 0.8
            P.prism_xz(mb, [(x - 0.25, 3.55), (x + 0.25, 3.55), (x + 0.25, 3.25), (x, 3.0), (x - 0.25, 3.25)][::-1], -0.14, -0.06, c)
    game.crate(mb, cx, cy - d / 2 - 1.2, s=0.5, z=h + rise - 2.0)
    for side in ("left", "right"):
        with P.face(mb, cx, cy, w, d, side) as L:
            for x in (-L * 0.28, L * 0.28):
                P.arched_window(mb, x, 1.0, w=0.8, h=1.8)
                P.arched_window(mb, x, 4.0, w=0.8, h=1.9)
    P.chimney(mb, cx - 2.6, cy + 0.8, h + 1.0, h + rise + 1.4, w=0.7, mat="brick", cap="trim", pots=2)
    P.chimney(mb, cx + 2.6, cy + 0.8, h + 1.0, h + rise + 1.4, w=0.7, mat="brick", cap="trim", pots=2)
    # Steps, lanterns and a notice board.
    mb.box((cx, cy - d / 2 - 0.6, 0.08), (3.0, 1.2, 0.16), "trim")
    for s in (-1, 1):
        mb.box((cx + s * 1.9, cy - d / 2 - 1.0, 1.1), (0.12, 0.12, 2.2), "iron")
        mb.box((cx + s * 1.9, cy - d / 2 - 1.0, 2.35), (0.26, 0.26, 0.34), "glow")
    mb.box((cx + 3.2, cy - d / 2 - 0.8, 0.9), (0.1, 0.1, 1.8), "timber")
    mb.box((cx + 3.2, cy - d / 2 - 0.86, 1.4), (1.0, 0.06, 0.8), "wood_light")
    mb.box((cx + 3.2, cy - d / 2 - 0.9, 1.4), (0.7, 0.02, 0.5), "white")
    P.flag(mb, rig, cx, cy - d / 2 + 0.2, h + rise + 2.3, pole=1.8, length=1.3, pennant=False, height=0.7)


def make(name, fn, colors=None, **kw):
    def build():
        mb = P.begin()
        rig = P.Rig()
        fn(mb, rig, **kw)
        P.finish(mb, name, colors or P.BASE, rig)
    return build


MODELS = {
    "bld_ruin_burnt_house": make("bld_ruin_burnt_house", burnt_house),
    "bld_ruin_tower": make("bld_ruin_tower", ruined_tower),
    "bld_cemetery": make("bld_cemetery", cemetery),
    "bld_bell_tower_stone": make("bld_bell_tower_stone", campanile, P.palette(roof=0x5A6470, roof_dark=0x46505A)),
    "bld_bell_tower_brick": make("bld_bell_tower_brick", campanile, P.BRICK_SLATE),
    "bld_bell_tower_blue": make("bld_bell_tower_blue", campanile, P.STONE_BLUE),
    "bld_guild_hall_blue": make("bld_guild_hall_blue", guild_hall, P.BASE),
    "bld_guild_hall_brick": make("bld_guild_hall_brick", guild_hall, P.palette(roof=0x5A6470, roof_dark=0x46505A)),
    "bld_guild_hall_red": make("bld_guild_hall_red", guild_hall, P.palette(roof=0xB0503A, roof_dark=0x8E3E2A, brick=0xC9B48A, brick_dark=0xA8946C)),
}
