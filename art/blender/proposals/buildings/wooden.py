"""Wooden castles: a motte and bailey and a frontier log fort."""

import math
import random

import _kit as kit
import castles
import parts as P
from parts import game

SHINGLE = ("shingle", "shingle_dark")
THATCH = ("thatch", "thatch_dark")


def palisade(mb, rnd, pts, h=2.8, r=0.17, inside=1, rail=True):
    """Pointed stakes along a polyline; `inside` is +1 if the inner side is
    to the left of the way the points run, -1 if to the right."""
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        L = math.hypot(x1 - x0, y1 - y0)
        n = max(1, int(L / (r * 1.9)))
        for i in range(n):
            t = (i + 0.5) / n
            x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            hh = h + rnd.uniform(-0.15, 0.15)
            mb.cylinder((x, y, 0), (x, y, hh), r, r * 0.95, "log", segments=6)
            mb.cylinder((x, y, hh), (x, y, hh + 0.4), r * 0.95, 0.0, "log_end", segments=6)
        if rail:
            nx, ny = -(y1 - y0) / L * inside, (x1 - x0) / L * inside
            for z in (h * 0.3, h * 0.72):
                P.beam(mb, (x0 + nx * (r + 0.05), y0 + ny * (r + 0.05), z),
                       (x1 + nx * (r + 0.05), y1 + ny * (r + 0.05), z), 0.1, "timber")


def gate_leaves(mb, rig, w, h, y, prefix="gate"):
    """Two plank leaves that close an opening w wide; clips `open`/`close`."""
    names = []
    for s in (-1, 1):
        name = rig.name(prefix + ("_l" if s < 0 else "_r"))
        with mb.bone(name):
            mb.box((s * w / 4, y, h / 2 + 0.05), (w / 2 - 0.04, 0.12, h), "plank")
            for i in range(1, 4):
                mb.box((s * w / 2 * i / 4, y - 0.065, h / 2 + 0.05), (0.04, 0.02, h), "plank_dark")
            for z in (h * 0.2, h * 0.8):
                mb.box((s * w / 4, y - 0.08, z), (w / 2 - 0.04, 0.04, 0.12), "iron")
            P.beam(mb, (s * (w / 2 - 0.1), y - 0.08, h * 0.22), (s * 0.1, y - 0.08, h * 0.78), 0.08, "timber")
        head = mb.world((s * w / 2, y, 0))
        rig.bone(name, head, head + kit.Vector((0, 0, 1)), None)
        names.append((name, -s))
    rig.add("open", 2.5, lambda t: {n: [(kit.Z, -sg * 100 * kit.smooth(t))] for n, sg in names}, loops=False)
    rig.add("close", 2.5, lambda t: {n: [(kit.Z, -sg * 100 * (1 - kit.smooth(t)))] for n, sg in names},
            loops=False)


def gate_tower(mb, rig, w=3.2, h=3.3, roof=SHINGLE, flag=True):
    """A timber gate with a roofed fighting platform over it (local frame,
    front toward -Y)."""
    px = w / 2 + 0.25
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.box((sx * px, sy * 1.0, 3.0), (0.4, 0.4, 6.0), "log")
        P.beam(mb, (sx * px, -1.0, 1.2), (sx * px, 1.0, 3.2), 0.14, "timber")
    for sy in (-1, 1):
        mb.box((0, sy * 1.0, h + 0.15), (w + 1.2, 0.3, 0.3), "timber")
    mb.box((0, 0, h + 0.4), (w + 1.6, 3.0, 0.16), "plank")
    for side in P.SIDES:
        with P.face(mb, 0, 0, w + 1.6, 3.0, side) as L:
            mb.box((0, 0.05, h + 0.95), (L, 0.1, 0.9), "plank")
            n = int(L / 0.45)
            for i in range(n + 1):
                mb.box((-L / 2 + i * L / n, -0.01, h + 0.95), (0.05, 0.05, 0.9), "plank_dark")
            mb.box((0, 0.03, h + 1.42), (L + 0.1, 0.16, 0.08), "timber")
    P.gable_roof(mb, 0, 0, w + 1.2, 2.6, 6.0, 1.3, roof, rows=4, overhang=0.5, gable=None, barge="timber")
    gate_leaves(mb, rig, w, h - 0.1, -1.0)
    # A ladder up to the platform at the back.
    for sx in (-0.25, 0.25):
        P.beam(mb, (px - 0.9 + sx, 2.3, 0), (px - 0.9 + sx, 1.45, h + 0.4), 0.07, "timber")
    for i in range(8):
        t = (i + 0.5) / 8
        mb.box((px - 0.9, 2.3 - 0.85 * t, (h + 0.4) * t), (0.6, 0.05, 0.05), "wood")
    if flag:
        P.flag(mb, rig, 0, 0, 7.2, pole=2.0, length=1.3)


def blockhouse(mb, rig, w=3.4, h1=3.0, h2=2.3, roof_h=2.3, door="back", flag=False, roof=SHINGLE):
    """A log tower with a jettied plank storey and loopholes (local frame)."""
    P.log_block(mb, 0, 0, 0, w, w, h1)
    mb.box((0, 0, h1 + 0.08), (w + 1.0, w + 1.0, 0.16), "timber")
    for sx in (-1, 1):
        for sy in (-1, 1):
            P.beam(mb, (sx * w / 2, sy * w / 2, h1 - 0.8), (sx * (w / 2 + 0.42), sy * (w / 2 + 0.42), h1 + 0.05), 0.12,
                   "timber")
    W = w + 0.9
    P.plank_block(mb, 0, 0, h1 + 0.16, W, W, h2)
    for side in P.SIDES:
        with P.face(mb, 0, 0, W, W, side):
            for x in (-W * 0.25, W * 0.25):
                mb.box((x, -0.03, h1 + 0.16 + h2 * 0.55), (0.18, 0.1, 0.7), "window")
    with P.face(mb, 0, 0, w + 0.34, w + 0.34, door):
        P.plank_door(mb, 0, 0.0, w=0.95, h=1.7)
    tip = P.pyramid_roof(mb, 0, 0, h1 + 0.16 + h2, W, W, roof_h, roof, rows=4, overhang=0.35,
                         finial=None if flag else "timber")
    if flag:
        P.flag(mb, rig, 0, 0, tip - 0.3, pole=2.0, length=1.3)


def log_house(mb, w, d, h, rise, roof=THATCH, chimney=True, storeys=1):
    """A log house, its ridge along local X, door toward -Y."""
    mb.box((0, 0, 0.15), (w + 0.5, d + 0.5, 0.3), "stone")
    P.log_block(mb, 0, 0, 0.3, w, d, h - 0.3)
    P.gable_roof(mb, 0, 0, w, d, h, rise, roof, rows=5, overhang=0.5, gable="plank", barge="timber")
    with P.face(mb, 0, 0, w + 0.34, d + 0.34, "front") as L:
        P.plank_door(mb, 0, 0.3, w=1.0, h=1.7)
        for x in (-L * 0.32, L * 0.32):
            P.window(mb, x, 1.6, w=0.6, h=0.6, shutter="shutter")
            if storeys > 1:
                P.window(mb, x, 3.9, w=0.6, h=0.6, shutter="shutter")
    with P.face(mb, 0, 0, w + 0.34, d + 0.34, "back") as L:
        for x in (-L * 0.3, L * 0.3):
            P.window(mb, x, 1.6, w=0.6, h=0.6, shutter="shutter")
    if chimney:
        mb.box((w / 2 + 0.45, 0, h / 2), (0.9, 1.4, h), "stone")
        P.chimney(mb, w / 2 + 0.45, 0, h, h + rise + 0.9, w=0.8, mat="stone", cap="stone_dark")


def stable_shed(mb, w=4.0, d=3.0, roof=THATCH):
    """An open shed on posts with hay and a trough (local frame, open to -Y)."""
    for sx in (-1, 0, 1):
        mb.box((sx * w / 2, -d / 2, 1.1), (0.16, 0.16, 2.2), "timber")
        mb.box((sx * w / 2, d / 2, 1.4), (0.16, 0.16, 2.8), "timber")
    mb.box((0, d / 2, 1.2), (w, 0.08, 2.2), "plank")
    game.sloped_slab(mb, -w / 2 - 0.3, w / 2 + 0.3, -d / 2 - 0.4, d / 2 + 0.3, 2.15, 2.95, 0.14, roof[0])
    game.sloped_slab(mb, -w / 2 - 0.3, w / 2 + 0.3, -d / 2 - 0.4, -d / 2 + 0.5, 2.2, 2.44, 0.14, roof[1])
    P.hay_bale(mb, -w / 4, d / 4)
    P.hay_bale(mb, -w / 4, d / 4 - 0.7)
    mb.box((w / 4, 0, 0.35), (1.4, 0.5, 0.3), "wood")
    mb.box((w / 4, 0, 0.47), (1.25, 0.36, 0.08), "hay")
    for sx in (-1, 1):
        mb.box((w / 4 + sx * 0.55, 0, 0.12), (0.1, 0.4, 0.24), "timber")


def motte_and_bailey(mb, rig, seed=3, keep="wood"):
    rnd = random.Random(seed)
    mx, my, R0, R1, MH = 0.0, 4.6, 7.2, 4.5, 4.6
    mb.cylinder((mx, my, 0), (mx, my, MH), R0, R1, "grass", segments=18)
    mb.cylinder((mx, my, 0), (mx, my, 0.5), R0 + 0.15, R0 - 0.2, "earth", segments=18)
    mb.cylinder((mx, my, MH - 0.02), (mx, my, MH + 0.05), R1 - 0.05, R1 - 0.2, "earth", segments=18)
    for _ in range(26):
        a = rnd.uniform(0, P.TAU)
        t = rnd.uniform(0.15, 0.85)
        rr = R0 + (R1 - R0) * t - 0.1
        mb.sphere((mx + rr * math.cos(a), my + rr * math.sin(a), MH * t), rnd.uniform(0.4, 0.8),
                  rnd.choice(("grass_dark", "grass_dark", "rock")), segments=6, rings=4, scale=(1, 1, 0.45))
    # The keep on the mound.
    if keep == "stone":   # A later stage: a stone shell keep replaces the timber tower.
        with mb.placed((mx, my + 0.2, MH)):
            castles.tower(mb, rig, rnd, 0, 0, 2.7, 6.5, top="crown", flag=True, slits=4)
            with mb.placed((0, -2.7 * math.cos(math.pi / 14) - 0.02, 0)):
                P.arched_door(mb, 0, 0.1, w=1.0, h=2.0)
    else:
        with mb.placed((mx, my + 0.4, MH)):
            blockhouse(mb, rig, w=4.0, h1=4.6, h2=2.6, roof_h=3.2, door="front", flag=True)
    # A ring of stakes around the top, open toward the stair.
    ring = []
    for i in range(25):
        a = -math.pi / 2 + 0.3 + (P.TAU - 0.6) * i / 24
        ring.append((mx + (R1 - 0.35) * math.cos(a), my + (R1 - 0.35) * math.sin(a)))
    with mb.placed((0, 0, MH)):
        palisade(mb, rnd, ring, h=1.7, r=0.13, rail=False)
    # The stair up the mound.
    y0, y1 = my - R0 - 0.4, my - R1 + 0.3
    with mb.placed((mx, y0, 0)):
        P.stairs(mb, 0, 0, 0, MH + 0.05, 1.5, y1 - y0, mat="plank", step=0.3, solid=False)
        for sx in (-1, 1):
            P.beam(mb, (sx * 0.75, 0, 0.0), (sx * 0.75, y1 - y0, MH), 0.14, "timber")
            P.beam(mb, (sx * 0.8, 0, 1.0), (sx * 0.8, y1 - y0, MH + 1.0), 0.08, "timber")
            for i in range(5):
                t = i / 4
                yy = (y1 - y0) * t
                mb.box((sx * 0.8, yy, MH * t * 0.5 + (MH * t + 1.0) * 0.5 - 0.0), (0.1, 0.1, 1.0 + MH * t * 0.0 + 0.0),
                       "timber")
    # The bailey: a palisade from one flank of the mound to the other.
    gx = 1.85
    right = [(6.3, 1.2), (10.6, 0.2), (11.4, -8.6), (8.6, -11.3), (gx, -11.3)]
    left = [(-gx, -11.3), (-8.6, -11.3), (-11.4, -8.6), (-10.6, 0.2), (-6.3, 1.2)]
    palisade(mb, rnd, right, inside=-1)
    palisade(mb, rnd, left, inside=-1)
    with mb.placed((0, -11.3, 0)):
        gate_tower(mb, rig)
    mb.box((0, -6.4, 0.02), (2.2, 8.4, 0.04), "earth")
    with mb.placed((-6.6, -5.0, 0), math.pi / 2):
        log_house(mb, 6.0, 4.4, 2.9, 2.4)
    with mb.placed((7.0, -5.6, 0), -math.pi / 2):
        stable_shed(mb, 4.4, 3.0)
    P.well(mb, 4.2, -0.6, roof=SHINGLE)
    for x, y in ((-3.4, -9.6), (-2.8, -9.9), (-3.2, -9.0)):
        game.barrel(mb, x, y, h=0.8, r=0.3)
    game.log_pile(mb, -5.0, 0.2, length=1.8)
    game.crate(mb, 3.2, -9.8, s=0.6)
    game.crate(mb, 3.9, -9.6, s=0.5)
    game.fence(mb, 4.6, -8.6, 9.6, -8.6, posts=5)


def log_fort(mb, rig, seed=9):
    rnd = random.Random(seed)
    C = 7.5
    gx = 1.85
    palisade(mb, rnd, [(gx, -C), (C, -C)], inside=1)
    palisade(mb, rnd, [(C, -C), (C, C)], inside=1)
    palisade(mb, rnd, [(C, C), (-C, C)], inside=1)
    palisade(mb, rnd, [(-C, C), (-C, -C)], inside=1)
    palisade(mb, rnd, [(-C, -C), (-gx, -C)], inside=1)
    for i, (sx, sy) in enumerate(((-1, -1), (1, -1), (1, 1), (-1, 1))):
        with mb.placed((sx * C, sy * C, 0)):
            blockhouse(mb, rig, w=3.2, door="back" if sy < 0 else "front", flag=(i == 2))
    with mb.placed((0, -C, 0)):
        gate_tower(mb, rig)
    with mb.placed((0, 2.6, 0)):
        log_house(mb, 7.0, 5.0, 5.0, 2.6, roof=SHINGLE, storeys=2)
    with mb.placed((-5.2, -3.0, 0), math.pi / 2):
        stable_shed(mb, 4.0, 2.6, roof=SHINGLE)
    mb.box((0, -3.4, 0.02), (2.2, 7.0, 0.04), "earth")
    game.log_pile(mb, 4.8, -4.6, length=2.0)
    for x, y in ((3.6, -2.2), (4.2, -2.0), (5.2, 0.0)):
        game.barrel(mb, x, y, h=0.8, r=0.3)
    for x in (2.6, 4.0):
        mb.box((x, -5.9, 0.8), (0.1, 0.1, 1.6), "timber")
        mb.box((x, -5.9, 1.25), (0.7, 0.09, 0.09), "timber")
        mb.sphere((x, -5.9, 1.62), 0.2, "hay", segments=6, rings=4)


def stockade(mb, rig, seed=15):
    with mb.placed((1.15, -0.3, 0)):   # Centered on its lot: the blockhouse hangs off one corner.
        stockade_parts(mb, rig, seed)


def stockade_parts(mb, rig, seed):
    """The smallest wooden stronghold: one blockhouse on a corner of a small
    palisade, a gate tower and a cabin. The wooden counterpart of the tower
    house, and the first step toward the log fort."""
    rnd = random.Random(seed)
    C, gx = 4.6, 1.85
    palisade(mb, rnd, [(gx, -C), (C, -C)], inside=1)
    palisade(mb, rnd, [(C, -C), (C, C)], inside=1)
    palisade(mb, rnd, [(C, C), (-C, C)], inside=1)
    palisade(mb, rnd, [(-C, C), (-C, -C)], inside=1)
    palisade(mb, rnd, [(-C, -C), (-gx, -C)], inside=1)
    with mb.placed((-C, C, 0)):
        blockhouse(mb, rig, w=3.2, door="front", flag=True)
    with mb.placed((0, -C, 0)):
        gate_tower(mb, rig, flag=False)
    with mb.placed((1.4, 1.9, 0)):
        log_house(mb, 4.6, 3.4, 2.7, 2.0, roof=SHINGLE)
    mb.box((0, -2.2, 0.02), (2.2, 3.6, 0.04), "earth")
    game.log_pile(mb, -2.6, -2.6, length=1.6, rows=3)
    for x, y in ((3.2, -2.6), (3.7, -2.3)):
        game.barrel(mb, x, y, h=0.8, r=0.3)
    game.crate(mb, 3.3, -3.4, s=0.55)
    mb.box((-2.6, -0.6, 0.8), (0.1, 0.1, 1.6), "timber")
    mb.box((-2.6, -0.6, 1.25), (0.7, 0.09, 0.09), "timber")
    mb.sphere((-2.6, -0.6, 1.62), 0.2, "hay", segments=6, rings=4)


def make(name, fn, colors, **kw):
    def build():
        mb = P.begin()
        rig = P.Rig()
        fn(mb, rig, **kw)
        P.finish(mb, name, colors, rig)
    return build


MODELS = {
    "castle_motte_bailey": make("castle_motte_bailey", motte_and_bailey, P.BASE),
    "castle_motte_bailey_stone_keep": make("castle_motte_bailey_stone_keep", motte_and_bailey, P.BASE, keep="stone"),
    "castle_motte_bailey_shingles": make("castle_motte_bailey_shingles", motte_and_bailey,
                                         P.palette(thatch=0x7A5A3C, thatch_dark=0x614530, banner=0xA8403A)),
    "castle_stockade": make("castle_stockade", stockade, P.palette(banner=0x3E7A46, banner2=0xE8E4D8)),
    "castle_stockade_thatch": make("castle_stockade_thatch", stockade,
                                   P.palette(shingle=0xC9A55A, shingle_dark=0xA8863F, banner=0xA8403A)),
    "castle_log_fort_thatch": make("castle_log_fort_thatch", log_fort,
                                   P.palette(shingle=0xC9A55A, shingle_dark=0xA8863F, banner=0xA8403A, banner2=0xE8E4D8)),
    "castle_log_fort": make("castle_log_fort", log_fort, P.palette(banner=0x3E7A46, banner2=0xE8E4D8)),
}
