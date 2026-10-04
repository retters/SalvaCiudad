"""A sixth batch of the `bridges` family: a harbor tavern on piles, a rope
walk, a sea wall, crab pots, stockfish racks and a net yard."""

import math

import bmesh

from parts import (B, BRICK, STONE, WOOD, barrel, blocks, chain, crate, jit, lantern, lerp, log, net, parapet,
                   planks_x, planks_y, rail, rock, roof_y, rope, sag, save)
from bridges import trestle_bent
from boats import Hull
from docks import DZ, WATER, bollard, fish, ladder, mooring_post, wood_deck
import _kit as kit
import buildings

MODELS = {}


def model(name, fn, **kw):
    MODELS[name] = lambda: fn(name, **kw)


def harbor_tavern(name, roof=("roof", "roof_dark")):
    b = B()
    z = 0.6
    wood_deck(b, -4.5, 4.5, -4, 3, z=z)
    for k in range(3):   # Steps from the shore.
        b.box((0, 3.0 + 0.2 + k * 0.4, (z - k * 0.2) / 2), (2.0, 0.4, z - k * 0.2), "stone" if k % 2 else "stone_dark")
    before = len(b.mb.bm.verts)
    buildings.cottage(b.mb, 0.0, 0.6, 6.4, 4.2, 3.0, roof=roof, walls="plaster_warm", gable="plaster_warm",
                      chimney=True)
    b.mb.bm.verts.ensure_lookup_table()
    bmesh.ops.translate(b.mb.bm, verts=b.mb.bm.verts[before:], vec=(0, 0, z - 0.05))
    # A terrace over the water: tables made of barrels, benches, lanterns on a line and a sign.
    yt = -1.5 - 1.25
    rail(b, [(-4.4, -3.9, z), (-2.2, -3.9, z), (0.0, -3.9, z), (2.2, -3.9, z), (4.4, -3.9, z)], h=0.9)
    for s in (-1, 1):
        rail(b, [(s * 4.4, -3.9, z), (s * 4.4, -1.6, z)], h=0.9)
        barrel(b, s * 2.4, yt, z=z, h=0.8, r=0.36)
        b.cyl((s * 2.4, yt, z + 0.8), (s * 2.4, yt, z + 0.86), 0.6, "wood_light", seg=9)
        b.cyl((s * 2.55, yt + 0.1, z + 0.86), (s * 2.55, yt + 0.1, z + 1.02), 0.07, "clay", seg=6)
        for dy in (-0.9, 0.9):
            b.box((s * 2.4, yt + dy, z + 0.42), (1.1, 0.26, 0.06), "wood")
            for dx in (-0.45, 0.45):
                b.box((s * 2.4 + dx, yt + dy, z + 0.2), (0.07, 0.22, 0.4), "timber")
        b.box((s * 4.3, -3.8, z + 1.5), (0.1, 0.1, 3.0), "timber")
    rope(b, sag((-4.3, -3.8, z + 2.9), (4.3, -3.8, z + 2.9), 0.5, 10), r=0.015)
    for k in range(5):
        t = (k + 0.5) / 5
        lantern(b, lerp(-4.3, 4.3, t), -3.8, z + 2.9 - 0.5 * 4 * t * (1 - t), s=0.18,
                glow=("lantern", "paint_red", "lantern", "paint_green", "lantern")[k])
    b.box((1.9, -1.62, z + 2.3), (0.06, 0.06, 0.06), "iron")
    b.box((1.9, -2.0, z + 2.45), (0.06, 0.8, 0.06), "iron")
    b.box((1.9, -2.1, z + 2.05), (0.05, 0.6, 0.6), "wood_dark")
    b.sphere((1.94, -2.1, z + 2.05), 0.16, "gold", seg=6, rings=4, scale=(0.2, 1, 1))
    b.sphere((1.86, -2.1, z + 2.05), 0.16, "gold", seg=6, rings=4, scale=(0.2, 1, 1))
    barrel(b, -3.8, 1.6, z=z)
    barrel(b, -3.9, 0.8, z=z, mat="wood_dark")
    crate(b, 3.8, 1.5, z=z, s=0.6)
    for x in (-4.62, 4.62):
        mooring_post(b, x, -3.6, z=z)
    ladder(b, -3.0, -4.0, z + 0.3, -1.3)
    h = Hull(3.8, 1.4, 0.28, 0.38, stern_w=0.55, sheer_bow=0.2, sheer_stern=0.08, stern_rise=0.3, n=9, thick=0.06)
    hb = b.at(dx=-2.9, dy=-5.4, dz=WATER, rz=85)
    h.build(hb, strakes=("paint_red", "wood_light", "wood"))
    h.deck(hb, 0.04, 0.08, 0.995, mat="plank_b")
    for t in (0.36, 0.64):
        h.thwart(hb, t)
    save(b, name)


def rope_walk(name):
    """A long shed where rope is twisted: a wheel at one end, a sledge at the other."""
    b = B()
    length, width = 14.0, 3.0
    b.box((0, 0, 0.03), (width + 0.4, length + 0.4, 0.06), "road")
    wall_h = 2.3
    for k in range(6):
        y = -length / 2 + 0.2 + k * (length - 0.4) / 5
        for s in (-1, 1):
            b.box((s * width / 2, y, wall_h / 2), (0.14, 0.14, wall_h), "timber")
        b.box((0, y, wall_h - 0.07), (width, 0.12, 0.14), "timber")
    for s in (-1, 1):
        b.box((s * width / 2, 0, wall_h - 0.07), (0.14, length, 0.14), "timber")
    roof_y(b, 0, 0, width, length, wall_h, 0.9, 0.3, ["shingle", "shingle_dark"], rows=4)
    # The spinning wheel with its four hooks, at the shore end (+Y).
    wy = length / 2 - 1.0
    for s in (-1, 1):
        b.beam((s * 0.6, wy + 0.3, 0.0), (0, wy + 0.3, 1.3), 0.09, 0.09, "timber")
    b.box((0, wy, 1.0), (1.0, 0.1, 0.9), "wood")
    wheel = b.bone("wheel")
    r = 0.75

    def rim(a, sign=1):
        return (sign * r * math.cos(a), wy + 0.3, 1.2 + sign * r * math.sin(a))

    for i in range(10):
        wheel.beam(rim(2 * math.pi * i / 10), rim(2 * math.pi * (i + 1) / 10), 0.07, 0.07, "wood_light")
    for i in range(4):
        wheel.beam(rim(math.pi * i / 4), rim(math.pi * i / 4, -1), 0.05, 0.05, "timber")
    wheel.cyl((0, wy + 0.2, 1.2), (0, wy + 0.5, 1.2), 0.08, "iron", seg=6)
    wheel.beam((0, wy + 0.5, 1.2), (0.3, wy + 0.5, 1.2), 0.04, 0.04, "iron")
    wheel.cyl((0.3, wy + 0.45, 1.2), (0.3, wy + 0.75, 1.2), 0.03, "wood", seg=5)
    # Strands from the hooks to the sledge, resting on trestles; the finished rope in coils.
    sy = -length / 2 + 1.6
    for k, x in enumerate((-0.3, -0.1, 0.1, 0.3)):
        b.cyl((x, wy - 0.06, 1.0 + 0.1 * (k % 2)), (x, wy - 0.2, 1.0 + 0.1 * (k % 2)), 0.02, "iron", seg=4)
        rope(b, sag((x, wy - 0.2, 1.0 + 0.1 * (k % 2)), (x * 0.3, sy, 0.75), 0.12, 8), r=0.022)
    for y in (-2.5, 1.5):
        for s in (-1, 1):
            b.beam((s * 0.5, y, 0.0), (s * 0.15, y, 0.85), 0.06, 0.06, "timber")
        b.box((0, y, 0.85), (0.9, 0.08, 0.08), "wood")
    for s in (-1, 1):
        b.box((s * 0.35, sy - 0.4, 0.1), (0.1, 1.3, 0.14), "timber")
    b.box((0, sy - 0.4, 0.2), (0.9, 1.0, 0.08), "plank")
    b.box((0, sy - 0.1, 0.5), (0.5, 0.12, 0.6), "wood")
    b.box((0, sy - 0.7, 0.4), (0.6, 0.5, 0.36), "stone_dark")
    for x, y in ((-1.0, -5.5), (1.0, -5.9), (-1.0, 4.2)):
        for k in range(4):
            b.cyl((x, y, 0.06 + k * 0.09), (x, y, 0.14 + k * 0.09), 0.34 - 0.02 * k, "rope", seg=9)
    for k in range(3):   # Bundles of flax waiting to be spun.
        b.cyl((1.0, 3.0 + k * 0.45, 0.18), (1.0 + 0.9, 3.0 + k * 0.45, 0.18), 0.17, "hay", seg=6)
    mech = kit.Mech([("wheel", (0, wy + 0.3, 1.2), (0, wy + 0.3, 1.6), None)])
    mech.clip("turn", 2.0, lambda t: {"wheel": [(kit.Y, 360 * t)]})
    save(b, name, mech=mech)


def seawall(name, pal=STONE, stairs=False, length=4.0):
    """A stretch of sea wall along X: the land is at +Y and the sea at -Y."""
    b = B()
    half = length / 2
    top = 1.2
    b.xz([(-half, -3.0), (half, -3.0), (half, top), (-half, top)], -0.6, 0.6, pal["body"])
    b.yz([(-0.6, -3.0), (-1.3, -3.0), (-0.6, 0.6)], -half, half, pal["body"])     # A battered face toward the sea.
    b.box((0, -0.85, -2.75), (length, 1.3, 0.5), pal["trim"])
    blocks(b, -half + 0.3, half - 0.3, -0.62, -0.4, top - 0.2, pal, face=-1, count=5, seed=2)
    planks_y(b, -0.6, 0.6, length, z=top + 0.12, mats=pal["deck"], step=0.6, thick=0.14, gap=0.03, ragged=0.0)
    for xa, xb in (((-half, -0.7), (0.7, half)) if stairs else ((-half, half),)):
        parapet(b, xa, xb, -0.45, lambda x: top + 0.12, pal, h=0.8, t=0.3)
    # An earth bank behind the wall, so the walk on top is reached from the land.
    b.yz([(0.6, 0.0), (2.0, 0.0), (0.6, top)], -half, half, "soil")
    if stairs:
        for k in range(6):   # Steps down to the water through a gap in the parapet.
            zk = top - k * 0.3
            b.box((0, -0.75 - k * 0.32, (zk - 3.0) / 2), (1.3, 0.32, zk + 3.0), pal["cap"] if k % 2 else pal["body"])
        b.cyl((0.9, -0.66, 0.2), (0.9, -0.72, 0.2), 0.14, "iron", seg=8)
        bollard(b, -1.4, 0.2, z=top + 0.12)
    else:
        for x in (-half + 0.5, half - 0.5):
            b.cyl((x, -0.66, 0.1), (x, -0.72, 0.1), 0.14, "iron", seg=8)
        b.box((0, 0.2, top + 0.45), (0.08, 0.08, 0.7), "iron")
        lantern(b, 0, 0.2, top + 1.25)
    for k in range(5):   # Loose rocks at the foot break the waves.
        rock(b, -half + 0.4 + k * (length - 0.8) / 4, -1.7 + jit(k, 0.2), 0.6, -3.0, -0.6 + jit(k, 0.3, 2), seed=k,
             mat="stone_dark" if k % 2 else "stone")
    save(b, name)


def crab_pots(name):
    b = B()
    wood_deck(b, -1.5, 1.5, -1.5, 1.5)
    spots = [(-0.8, -0.6, 0), (0.0, -0.7, 0), (0.8, -0.6, 0), (-0.4, -0.65, 1), (0.4, -0.65, 1), (0.0, -0.65, 2),
             (-0.7, 0.7, 0), (0.1, 0.8, 0)]
    for k, (x, y, lvl) in enumerate(spots):
        z = DZ + lvl * 0.46
        b.box((x, y, z + 0.03), (0.7, 0.55, 0.04), "wood")
        for i in range(3):   # Hoops and a net skin make each pot.
            xi = x - 0.3 + i * 0.3
            for a in range(6):
                a0, a1 = math.pi * a / 6, math.pi * (a + 1) / 6
                b.beam((xi, y + 0.26 * math.cos(a0), z + 0.05 + 0.38 * math.sin(a0)),
                       (xi, y + 0.26 * math.cos(a1), z + 0.05 + 0.38 * math.sin(a1)), 0.03, 0.03, "timber")
        for a in range(5):
            ang = math.pi * (a + 0.5) / 5
            b.cyl((x - 0.32, y + 0.26 * math.cos(ang), z + 0.05 + 0.38 * math.sin(ang)),
                  (x + 0.32, y + 0.26 * math.cos(ang), z + 0.05 + 0.38 * math.sin(ang)), 0.012, "net", seg=4)
    # Floats on a line, a coil of rope, a basket of crabs and a mooring post.
    for k in range(5):
        b.sphere((1.1, -0.9 + k * 0.35, DZ + 0.12), 0.13, ("paint_red", "paint_yellow")[k % 2], seg=6, rings=4)
    for k in range(3):
        b.cyl((-1.0, 0.0, DZ + 0.02 + k * 0.07), (-1.0, 0.0, DZ + 0.08 + k * 0.07), 0.26, "rope", seg=8)
    b.cyl((0.9, 0.7, DZ), (0.9, 0.7, DZ + 0.3), 0.26, "thatch_dark", r2=0.32, seg=8)
    for k in range(4):
        b.sphere((0.9 + jit(k, 0.12), 0.7 + jit(k, 0.12, 2), DZ + 0.33), 0.09, "paint_red", seg=5, rings=3,
                 scale=(1.3, 1, 0.5))
    mooring_post(b, 1.62, -1.38)
    save(b, name)


def stockfish_racks(name):
    b = B()
    for row, y in enumerate((-1.6, 0.0, 1.6)):
        for x in (-2.8, 0.0, 2.8):
            for s in (-1, 1):
                b.beam((x, y + s * 0.55, 0.0), (x, y, 2.6), 0.08, 0.08, "timber")
        for dz, wide in ((2.55, 0.0), (1.9, 0.18), (1.25, 0.34)):
            for s in ((0,) if wide == 0 else (-1, 1)):
                yy = y + s * wide
                b.cyl((-3.0, yy, dz), (3.0, yy, dz), 0.035, "wood_light", seg=5)
                for k in range(9):
                    fish(b, -2.7 + k * 0.675, yy, dz, s=0.46 + jit(k + row, 0.06, dz),
                         mat="fish" if (k + row) % 3 else "sack")
    b.box((0, 0, 0.02), (6.6, 4.6, 0.04), "road")
    barrel(b, 3.4, 1.8)
    barrel(b, 3.5, 1.0, mat="wood_dark")
    crate(b, -3.5, -1.7, s=0.6)
    b.cyl((-3.4, 1.6, 0.0), (-3.6, 0.4, 2.2), 0.03, "wood_light", seg=5)
    b.beam((-3.6, 0.4, 2.2), (-3.55, 0.25, 2.3), 0.3, 0.03, "iron")
    save(b, name)


def net_yard(name):
    b = B()
    b.box((0, 0, 0.02), (7.0, 5.0, 0.04), "road")
    # Nets hung between tall poles, with floats along the top and weights at the foot.
    for y, x0, x1 in ((1.6, -3.0, 0.4), (0.2, -0.6, 3.0), (-1.4, -3.0, 0.0)):
        for x in (x0, x1):
            b.cyl((x, y, -0.4), (x, y, 2.9), 0.07, "timber", r2=0.05, seg=6)
        b.cyl((x0 - 0.2, y, 2.75), (x1 + 0.2, y, 2.75), 0.035, "wood_light", seg=5)
        net(b, (x0 + 0.1, y, 2.7), (x1 - 0.1, y, 2.7), (x0 + 0.2, y - 0.25, 0.15), (x1 - 0.2, y - 0.25, 0.15), n=9)
        n = round((x1 - x0) / 0.45)
        for k in range(n):
            x = lerp(x0 + 0.2, x1 - 0.2, k / max(1, n - 1))
            b.sphere((x, y, 2.66), 0.07, "wood_light" if k % 2 else "paint_red", seg=5, rings=3)
            b.box((x, y - 0.25, 0.12), (0.1, 0.08, 0.08), "stone_dark")
    # A bench with a net being mended, a tub of tar and a heap of nets.
    b.box((1.8, -1.6, 0.42), (1.6, 0.4, 0.07), "wood")
    for x in (1.2, 2.4):
        b.box((x, -1.6, 0.2), (0.08, 0.35, 0.4), "timber")
    for k in range(4):
        b.sphere((1.9 + jit(k, 0.3), -1.9 + jit(k, 0.15, 2), 0.12 + 0.07 * k), 0.36 - 0.05 * k, "net", seg=6, rings=4,
                 scale=(1.3, 1, 0.45))
    b.cyl((2.9, 1.8, 0.0), (2.9, 1.8, 0.5), 0.36, "iron", r2=0.42, seg=8)
    b.cyl((2.9, 1.8, 0.48), (2.9, 1.8, 0.5), 0.38, "tar", seg=8)
    for k in range(3):
        rock(b, 2.9 + math.cos(k * 2.1) * 0.5, 1.8 + math.sin(k * 2.1) * 0.5, 0.2, 0.0, 0.22, seed=k, mat="stone_dark")
    barrel(b, -3.0, -2.0)
    save(b, name)


# --- States of the wooden bridge and of a boat ----------------------------------------


def trestle_site(name, length=10.0, width=3.0):
    """The plank bridge half built: all the bents driven, the deck laid from
    one bank, and a pile driver at work."""
    b = B()
    half = length / 2
    zd = 0.3
    xs = [-half + (i + 1) * length / 4 for i in range(3)]
    for i, x in enumerate(xs):
        trestle_bent(b, x, width, zd - 0.45, WOOD)
    for y in (-width / 2 + 0.3, 0.0, width / 2 - 0.3):
        b.box((-half / 2 + 0.6, y, zd - 0.17), (half + 0.9, 0.16, 0.2), "timber")
    b.box((1.2, width / 2 - 0.3, zd - 0.17), (2.6, 0.16, 0.2), "timber")
    planks_x(b, -half + 0.5, -0.8, width, z=zd)
    for k in range(3):   # Loose boards waiting on the deck.
        b.box((-1.6 + k * 0.05, -0.4 + k * 0.35, zd + 0.04 + k * 0.07), (2.2, 0.3, 0.06),
              "plank" if k % 2 else "plank_b", rz=0.05 * k)
    log(b, (-half + 0.45, -width / 2 - 0.1, -0.02), (-half + 0.45, width / 2 + 0.1, -0.02), 0.2, seg=7)
    log(b, (half - 0.45, -width / 2 - 0.1, -0.02), (half - 0.45, width / 2 + 0.1, -0.02), 0.2, seg=7)
    # The pile driver: a tripod over the far bent with a stone ram on a rope.
    px, py = xs[2], 0.0
    top = (px, py, 4.6)
    for a in (0.5, 2.6, 4.7):
        b.cyl((px + math.cos(a) * 1.3, py + math.sin(a) * 1.3, zd - 0.4), top, 0.07, "timber", seg=6)
    b.cyl((px - 0.15, py, 4.45), (px + 0.15, py, 4.45), 0.14, "wood_light", seg=8)
    b.cyl((px, py, -3.0), (px, py, 1.4), 0.12, "wood", seg=7)        # The pile being driven.
    ram = b.bone("ram")
    ram.box((px, py, 2.0), (0.5, 0.5, 0.7), "stone_dark")
    ram.box((px, py, 2.0), (0.56, 0.1, 0.76), "iron")
    rope(ram, [(px, py, 2.35), (px, py, 4.4)], r=0.025)
    rope(b, [(px, py + 0.1, 4.45), (px - 2.4, py + 0.5, zd + 0.9)], r=0.025)
    for k in range(5):   # Timber stacked on the bank.
        b.box((half + 0.2, -0.6 + k * 0.3, 0.1 + (k % 2) * 0.16), (0.3, 0.26, 0.16), "timber", rz=0.0)
    mech = kit.Mech([("ram", (px, py, 2.0), (px, py, 2.4), None)])

    def drive(t):
        lift = (t / 0.8) if t < 0.8 else (1 - (t - 0.8) / 0.2) ** 2
        return {}, {"ram": (0.0, 0.0, -0.25 + 1.3 * lift)}

    mech.clip("drive", 2.5, drive)
    save(b, name, mech=mech)


def trestle_burnt(name, length=10.0, width=3.0):
    """The plank bridge after a fire: the middle fallen in, the rest charred."""
    b = B()
    half = length / 2
    zd = 0.3
    burnt = {"body": "charcoal", "trim": "tar", "cap": "wood_dark", "deck": ("charcoal", "tar")}
    for i, x in enumerate((-2.5, 0.0, 2.5)):
        if i == 1:   # Only the stumps of the middle bent are left.
            for s in (-1, 1):
                stump = (x + 0.1 * s, s * 1.35, -0.3 - 0.4 * (s > 0))
                b.cyl((x, s * 1.6, -3.0), stump, 0.12, "charcoal", r2=0.06, seg=7)
        else:
            trestle_bent(b, x, width, zd - 0.45, burnt)
    for e in (-1, 1):
        for y in (-width / 2 + 0.3, 0.0, width / 2 - 0.3):
            far = e * (1.6 + 0.5 * abs(y))
            b.beam((e * (half - 0.15), y, zd - 0.17), (far, y, zd - 0.17 - 0.25 * abs(y)), 0.16, 0.2,
                   "timber" if abs(far) > 2.3 else "tar")
        n = 9
        for k in range(n):
            x = e * (half - 0.5 - k * 0.3)
            mat = ("plank", "plank_b")[k % 2] if k < 4 else ("tar", "charcoal", "wood_dark")[k % 3]
            if k in (6, 8):
                continue
            b.box((x, jit(k, 0.06, e), zd - 0.035 - 0.012 * max(0, k - 4)),
                  (0.28, width + jit(k, 0.05, e + 2), 0.07), mat)
        log(b, (e * (half - 0.45), -width / 2 - 0.1, -0.02), (e * (half - 0.45), width / 2 + 0.1, -0.02), 0.2, seg=7)
        yr = e * (width / 2 - 0.08)
        b.box((e * (half - 0.6), yr, zd + 0.5), (0.1, 0.1, 1.0), "timber")
        b.box((e * (half - 2.2), yr, zd + 0.4), (0.1, 0.1, 0.8), "charcoal")
        b.beam((e * (half - 0.6), yr, zd + 0.94), (e * (half - 2.2), yr, zd + 0.7), 0.08, 0.08, "tar")
    for k in range(5):   # Charred boards hanging and fallen into the water.
        x = jit(k, 1.4, 3)
        b.beam((x, jit(k, 1.0, 4), -0.2), (x + jit(k, 0.5, 5), jit(k, 1.0, 6), -1.6), 0.26, 0.06,
               "charcoal" if k % 2 else "tar")
    for k in range(4):   # Embers.
        b.box((jit(k, 2.2, 7), jit(k, 1.0, 8), zd - 0.02), (0.12, 0.1, 0.05), "torch_flame")
    save(b, name)


def sunk_boat(name):
    """A merchant ship gone down in shallow water: the stern castle, the
    mast and the bow rail still show above the surface (Z = 0)."""
    root = B()
    h = Hull(12.0, 4.2, 1.1, 1.5, tm=0.5, bow_p=0.7, stern_w=0.5, stern_p=0.6, sheer_bow=0.9, sheer_stern=0.7,
             bow_rise=0.75, stern_rise=0.5, n=14, thick=0.1)
    hb = root.at(dz=-1.55).turn("Y", 16).turn("X", 7)
    h.build(hb, strakes=("tar", "wood_dark", "wood_dark"), inner="wood_dark", rail="tar")
    h.deck(hb, 1.0, 0.06, 0.98, mat="plank_b", alt="wood_dark", steps=18)
    ya, yb = h.y(0.72), h.y(1.0) + 0.25
    wc = h.w(0.8) + 0.12
    zc = h.top(1.0) + 0.2
    hb.box((0, (ya + yb) / 2, zc), (2 * wc, yb - ya, 0.12), "plank_b")
    hb.box((0, ya + 0.06, (1.0 + zc) / 2), (2 * h.half_at(0.72, 1.3) + 0.1, 0.12, zc - 1.0), "wood_dark")
    for s in (-1, 1):
        for k in range(3):
            hb.box((s * (wc - 0.07), lerp(ya + 0.1, yb - 0.1, k / 2), zc + 0.45), (0.1, 0.1, 0.8), "timber")
        hb.box((s * (wc - 0.07), (ya + yb) / 2, zc + 0.82), (0.1, yb - ya, 0.1), "tar")
    ym = h.y(0.46)
    hb.cyl((0, ym, 1.0), (0, ym, 9.5), 0.16, "timber", r2=0.1, seg=7)
    hb.cyl((-2.6, ym - 0.2, 8.6), (2.9, ym - 0.2, 8.2), 0.055, "wood", seg=6)
    hb.solid([(-2.3, ym - 0.24, 8.5), (0.4, ym - 0.24, 8.35), (-0.8, ym - 0.3, 6.6), (-2.0, ym - 0.3, 7.2)],
             [(-2.3, ym - 0.2, 8.5), (0.4, ym - 0.2, 8.35), (-0.8, ym - 0.26, 6.6), (-2.0, ym - 0.26, 7.2)],
             "canvas_shade")
    hb.cyl((0, ym, 8.2), (0, ym, 8.65), 0.34, "wood", r2=0.42, seg=8)
    # Things that float away: on bones, so they bob.
    bones = []
    spots = [(3.6, -2.0, "barrel"), (-3.2, 2.6, "plank"), (2.4, 3.8, "crate"), (-2.2, -4.6, "plank")]
    for k, (x, y, what) in enumerate(spots):
        name_k = "drift%d" % k
        bones.append((name_k, (x, y, 0.0), (x, y, 0.4), None))
        d = root.bone(name_k)
        if what == "barrel":
            d.cyl((x - 0.45, y, 0.05), (x + 0.45, y, 0.05), 0.3, "wood", seg=9)
            for dx in (-0.25, 0.25):
                d.cyl((x + dx - 0.03, y, 0.05), (x + dx + 0.03, y, 0.05), 0.32, "iron", seg=9)
        elif what == "crate":
            d.box((x, y, 0.05), (0.6, 0.6, 0.5), "wood_light", rz=0.4)
            d.box((x, y, 0.05), (0.64, 0.1, 0.54), "wood", rz=0.4)
        else:
            d.box((x, y, 0.02), (1.8, 0.3, 0.06), "plank_b", rz=0.7 * k)
            d.box((x + 0.3, y + 0.35, 0.02), (1.3, 0.28, 0.06), "plank", rz=0.7 * k + 0.2)
    mech = kit.Mech(bones)

    def bob(t):
        turns, moves = {}, {}
        for k in range(len(spots)):
            ph = 2 * math.pi * t + k * 1.7
            turns["drift%d" % k] = [(kit.X, 5 * math.sin(ph)), (kit.Y, 4 * math.sin(ph + 1.0))]
            moves["drift%d" % k] = (0.0, 0.0, 0.04 * math.sin(ph))
        return turns, moves

    mech.clip("bob", 3.0, bob)
    save(root, name, mech=mech)


def chain_bridge(name, pal=STONE, length=20.0, width=3.4, span=14.0):
    """A suspension bridge for carts: two masonry towers, iron chains and a
    stiff plank deck, with no support in the water between the towers."""
    b = B()
    half = length / 2
    zd = 0.5
    tower = span / 2
    high = 6.2
    yc = width / 2 + 0.35

    def deck(x):
        return zd * min(1.0, (half - abs(x)) / 2.0)

    for e in (-1, 1):
        for s in (-1, 1):
            q = 0.5
            cx, cy = e * tower, s * yc
            b.xy([(cx - q, cy - q), (cx + q, cy - q), (cx + q, cy + q), (cx - q, cy + q)], -3.0, zd + high, pal["body"],
                 shrink=0.8)
            b.box((cx, cy, zd + high + 0.08), (0.95, 0.95, 0.16), pal["trim"])
            b.box((cx, cy, 0.3), (1.2, 1.2, 0.6), pal["trim"])
            b.cyl((cx - 0.3, cy, zd + high + 0.3), (cx + 0.3, cy, zd + high + 0.3), 0.16, "iron", seg=8)
        b.box((e * tower, 0, zd + high - 0.5), (0.7, 2 * yc, 0.6), pal["body"])
        b.box((e * tower, 0, zd + high - 0.85), (0.74, 2 * yc - 0.6, 0.12), pal["cap"])
        lantern(b, e * tower, 0, zd + high - 0.95)
        # Anchor blocks on each bank, and the ramp up to the deck.
        for s in (-1, 1):
            b.box((e * (half - 0.4), s * yc, 0.1), (1.0, 0.8, 1.4), pal["body"])
            b.box((e * (half - 0.4), s * yc, 0.85), (1.1, 0.9, 0.14), pal["trim"])
            chain(b, (e * (half - 0.4), s * yc, 0.9), (e * tower, s * yc, zd + high + 0.3), link=0.36)
    n = 40
    for i in range(n):   # Deck: stringers, cross beams and boards.
        xa, xb = -half + length * i / n, -half + length * (i + 1) / n
        for y in (-width / 2 + 0.2, 0.0, width / 2 - 0.2):
            b.beam((xa, y, deck(xa) - 0.2), (xb, y, deck(xb) - 0.2), 0.16, 0.24, "timber")
    planks_x(b, -half, half, width, zf=deck, step=0.3)
    for s in (-1, 1):
        pts = []
        m = 14
        for i in range(m + 1):   # The main chain, and an iron rod down to the deck at every point.
            x = -tower + span * i / m
            u = i / m
            z = zd + high + 0.3 - 4.9 * 4 * u * (1 - u)
            pts.append((x, s * yc, z))
            if 0 < i < m:
                b.cyl((x, s * yc, z), (x, s * (width / 2 + 0.06), zd - 0.2), 0.025, "iron", seg=5)
                b.box((x, s * (width / 2 + 0.02), zd - 0.33), (0.16, 0.5, 0.14), "timber")
        for p, q in zip(pts, pts[1:]):
            chain(b, p, q, link=0.36)
        rail(b, [(x, s * (width / 2 - 0.06), deck(x)) for x in (-half + 0.3, -tower + 0.7)], h=0.9, mid=True)
        rail(b, [(x, s * (width / 2 - 0.06), deck(x)) for x in (tower - 0.7, half - 0.3)], h=0.9, mid=True)
        rail(b, [(-tower + 0.7 + k * (span - 1.4) / 7, s * (width / 2 - 0.06), zd) for k in range(8)], h=0.9,
             mat="iron", rail_mat="timber", post=0.06)
    save(b, name)


model("bridge_chain", chain_bridge)
model("bridge_chain_brick", chain_bridge, pal=BRICK)
model("bridge_plank_trestle_site", trestle_site)
model("bridge_plank_trestle_burnt", trestle_burnt)
model("boat_wreck_sunk", sunk_boat)
model("dock_harbor_tavern", harbor_tavern)
model("dock_harbor_tavern_slate", harbor_tavern, roof=("slate", "slate_dark"))
model("dock_rope_walk", rope_walk)
model("dock_seawall", seawall)
model("dock_seawall_stairs", seawall, stairs=True)
model("dock_seawall_brick", seawall, pal=BRICK)
model("dock_crab_pots", crab_pots)
model("dock_stockfish_racks", stockfish_racks)
model("dock_net_yard", net_yard)
