"""Docks and other works at the water's edge. A dock runs along Y: the shore
is at +Y and the water end at -Y. Z = 0 is the ground of the shore, the deck
is 0.3 m above it and the water is expected about 0.4 m below; piles and
walls go down to Z = -3."""

import math

from parts import (B, BRICK, ROOFS, STONE, WOOD, barrel, blocks, crate, flame, jit, lantern, lerp, log, net,
                   planks_x, planks_y, plate, rail, rock, roof_y, rope, sack, sag, save)
from boats import Hull
import _kit as kit

MODELS = {}
DZ = 0.3
DEEP = -3.0
WATER = -0.4


def model(name, fn, **kw):
    MODELS[name] = lambda: fn(name, **kw)


def pile(b, x, y, top, deep=DEEP, r=0.11, mat="timber"):
    b.cyl((x, y, deep), (x, y, top), r, mat, r2=r * 0.88, seg=7)


def mooring_post(b, x, y, z=DZ, h=0.9, deep=DEEP):
    pile(b, x, y, z + h, deep=deep, r=0.13)
    b.cyl((x, y, z + h), (x, y, z + h + 0.06), 0.15, "wood_light", seg=7)
    for k in range(3):
        b.cyl((x, y, z + h * 0.45 + k * 0.07), (x, y, z + h * 0.45 + k * 0.07 + 0.06), 0.17, "rope", seg=7)


def ladder(b, x, y, top, bottom, face=-1, mat="timber"):
    """A ladder on a face that looks toward -Y (face = -1) or +Y."""
    for s in (-1, 1):
        b.box((x + s * 0.22, y + face * 0.06, (top + bottom) / 2), (0.06, 0.06, top - bottom), mat)
    n = round((top - bottom) / 0.3)
    for k in range(n):
        b.box((x, y + face * 0.06, bottom + 0.15 + k * 0.3), (0.44, 0.05, 0.05), "wood")


def wood_deck(b, x0, x1, y0, y1, z=DZ, pal=WOOD, deep=DEEP, brace=True):
    """A plank platform on piles over the rectangle."""
    w, d = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    planks_y(b, y0, y1, w, z=z, xc=cx, mats=pal["deck"])
    xs = [x0 + 0.2, x1 - 0.2] if w <= 3.5 else [x0 + 0.2, cx, x1 - 0.2]
    for x in xs:
        b.box((x, cy, z - 0.15), (0.14, d, 0.16), pal["trim"])
    rows = max(2, round(d / 2.2) + 1)
    for r in range(rows):
        y = y0 + 0.3 + r * (d - 0.6) / (rows - 1)
        b.box((cx, y, z - 0.31), (w + 0.1, 0.16, 0.16), pal["trim"])
        for x in xs:
            pile(b, x, y, z - 0.22, deep=deep, mat=pal["body"])
        if brace:
            b.beam((xs[0], y + 0.1, -1.4), (xs[-1], y + 0.1, z - 0.4), 0.06, 0.12, pal["trim"])


def stone_quay(b, x0, x1, y0, y1, z=DZ, pal=STONE, deep=DEEP, faces=(-1,)):
    w, d = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    b.box((cx, cy, (z - 0.12 + deep) / 2), (w - 0.1, d - 0.1, z - 0.12 - deep), pal["body"])
    planks_y(b, y0, y1, w, z=z, xc=cx, mats=pal["deck"], step=0.5, thick=0.14, gap=0.03, ragged=0.0)
    b.box((cx, cy, deep + 0.3), (w + 0.2, d + 0.2, 0.6), pal["trim"])
    for s in (-1, 1):
        for k in range(max(2, round(d * 1.2))):
            yk = lerp(y0 + 0.3, y1 - 0.3, 0.5 + jit(k, 0.48, s + w))
            zk = lerp(deep + 0.8, z - 0.5, 0.5 + jit(k, 0.45, s + 3))
            b.box((cx + s * (w / 2 - 0.04), yk, zk), (0.08, 0.5, 0.24), pal["trim"])
    for face in faces:
        y = y0 if face < 0 else y1
        blocks(b, x0 + 0.2, x1 - 0.2, y + face * -0.05, deep + 0.8, z - 0.5, pal, face=face, count=max(2, round(w)),
               seed=face + d)


def bollard(b, x, y, z=DZ):
    b.cyl((x, y, z), (x, y, z + 0.5), 0.14, "iron", r2=0.11, seg=7)
    b.cyl((x, y, z + 0.5), (x, y, z + 0.58), 0.19, "iron", seg=7)


# --- Modular pier --------------------------------------------------------------------


def pier_piece(b, kind, piece):
    pal = {"wood": WOOD, "brick": BRICK}.get(kind, STONE)
    deck = wood_deck if kind == "wood" else stone_quay
    if piece == "straight":
        deck(b, -1, 1, -2, 2, pal=pal)
    elif piece == "corner":
        deck(b, -1, 1, -1, 1, pal=pal)
        if kind == "wood":
            mooring_post(b, 1.12, -1.12)
        else:
            bollard(b, 0.7, -0.7)
    elif piece == "end":
        deck(b, -1, 1, -1, 1, pal=pal)
        if kind == "wood":
            for x in (-1.12, 1.12):
                mooring_post(b, x, -0.88)
            ladder(b, 0, -1.0, DZ + 0.4, -1.4)
            b.box((0.7, 0.6, DZ + 1.0), (0.1, 0.1, 2.0), "timber")
            b.box((0.7, 0.35, DZ + 1.9), (0.07, 0.6, 0.07), "timber")
            lantern(b, 0.7, 0.15, DZ + 1.86)
        else:
            for x in (-0.65, 0.65):
                bollard(b, x, -0.65)
            for k in range(4):   # Steps down to the water on the end face.
                b.box((0, -1.0 - 0.15 - k * 0.3, (DZ - 0.25 * (k + 1) + DEEP) / 2),
                      (1.2, 0.3, DZ - 0.25 * (k + 1) - DEEP), pal["cap"] if k % 2 else pal["body"])
            for x in (-0.8, 0.8):
                b.cyl((x, -1.03, -0.1), (x, -1.09, -0.1), 0.12, "iron", seg=8)
    elif piece == "ramp":
        # From the shore (y = +1, Z = 0) up to the deck.
        if kind == "wood":
            for k in range(4):
                ya, yb = 1 - k * 0.5, 1 - (k + 1) * 0.5
                b.beam((0, ya, DZ * k / 4 - 0.035), (0, yb, DZ * (k + 1) / 4 - 0.035), 2.0, 0.07, pal["deck"][k % 2])
            log(b, (-1.1, 0.9, -0.05), (1.1, 0.9, -0.05), 0.15, seg=7)
            for x in (-0.8, 0.8):
                b.box((x, 0, DZ / 2 - 0.2), (0.14, 2.0, 0.16), pal["trim"])
        else:
            for k in range(3):
                b.box((0, 1 - 0.33 - k * 0.67 + 0.0, (DZ * (k + 1) / 3 - 1.0) / 2), (2.0, 0.67, DZ * (k + 1) / 3 + 1.0),
                      pal["cap"] if k % 2 else pal["body"])


def pier_demo(name, kind):
    b = B()
    pier_piece(b.at(dy=6), kind, "ramp")
    pier_piece(b.at(dy=3), kind, "straight")
    pier_piece(b.at(dy=-1), kind, "straight")
    pier_piece(b.at(dy=-4), kind, "corner")
    pier_piece(b.at(dx=-3, dy=-4, rz=-90), kind, "straight")
    pier_piece(b.at(dx=-6, dy=-4, rz=-90), kind, "end")
    save(b, name)


def pier_model(name, kind, piece):
    b = B()
    pier_piece(b, kind, piece)
    save(b, name)


# --- Fishing dock --------------------------------------------------------------------


def fish(b, x, y, z, s=0.3, mat="fish"):
    """A fish hanging by the tail from z."""
    b.cyl((x, y, z - 0.06), (x, y, z - 0.06 - s * 0.55), 0.02, mat, r2=s * 0.2, seg=5)
    b.cyl((x, y, z - 0.06 - s * 0.55), (x, y, z - 0.06 - s), s * 0.2, mat, r2=0.02, seg=5)
    b.box((x, y, z - 0.04), (0.02, s * 0.3, 0.07), mat)


def fishing_dock(name, boat=True):
    b = B()
    wood_deck(b, -3, 3, 0, 4)
    wood_deck(b, -1, 1, -4, 0)
    b.box((0, 4.12, DZ / 2 - 0.05), (2.4, 0.3, DZ - 0.1), "stone")     # Step up from the shore.
    # Net rack: two posts and a pole, with a net hung to dry.
    for x in (-2.7, -0.3):
        b.box((x, 3.4, DZ + 1.1), (0.1, 0.1, 2.2), "timber")
        b.beam((x, 3.4, DZ + 0.02), (x, 2.8, DZ + 0.9), 0.07, 0.07, "wood")
    b.cyl((-2.9, 3.4, DZ + 2.15), (-0.1, 3.4, DZ + 2.15), 0.045, "wood_light", seg=6)
    net(b, (-2.6, 3.38, DZ + 2.12), (-0.4, 3.38, DZ + 2.12), (-2.5, 3.0, DZ + 0.3), (-0.5, 3.0, DZ + 0.3), n=8)
    for k in range(5):
        b.sphere((-2.5 + k * 0.5, 3.0, DZ + 0.3), 0.06, "paint_red" if k % 2 else "wood_light", seg=5, rings=3)
    # Fish drying rack.
    for x in (0.9, 2.7):
        for s in (-1, 1):
            b.beam((x, 3.2 + s * 0.45, DZ), (x, 3.2, DZ + 1.7), 0.07, 0.07, "timber")
    for dz in (1.65, 1.15):
        wide = 0.0 if dz > 1.5 else 0.14
        for s in ((0,) if dz > 1.5 else (-1, 1)):
            y = 3.2 + s * wide
            b.cyl((0.75, y, DZ + dz), (2.85, y, DZ + dz), 0.03, "wood_light", seg=5)
            for k in range(6):
                fish(b, 1.0 + k * 0.32, y, DZ + dz, s=0.3 + jit(k, 0.05, dz))
    # Barrels, crates, a basket of fish and rods.
    barrel(b, 2.5, 0.6, z=DZ)
    barrel(b, 1.85, 0.5, z=DZ)
    barrel(b, 2.3, 1.2, z=DZ, mat="wood_dark")
    crate(b, -2.5, 0.6, z=DZ, s=0.65)
    crate(b, -2.45, 1.35, z=DZ, s=0.55, rz=0.25)
    b.cyl((-1.7, 0.7, DZ), (-1.7, 0.7, DZ + 0.3), 0.26, "thatch_dark", r2=0.33, seg=8)
    for k in range(5):
        b.box((-1.7 + jit(k, 0.12), 0.7 + jit(k, 0.12, 2), DZ + 0.32), (0.1, 0.3, 0.06), "fish", rz=k * 0.7)
    for k in range(2):
        b.cyl((0.3 + k * 0.2, 3.45, DZ), (0.2 + k * 0.5, 3.1, DZ + 2.9), 0.02, "wood_light", seg=4)
    b.box((1.9, 1.9, DZ + 0.22), (1.3, 0.35, 0.06), "wood")     # A bench to gut the catch.
    for x in (1.4, 2.4):
        b.box((x, 1.9, DZ + 0.1), (0.08, 0.3, 0.2), "timber")
    # The finger pier: mooring posts, a ladder and a lantern.
    for x in (-1.12, 1.12):
        mooring_post(b, x, -3.85)
        mooring_post(b, x, -1.0)
    ladder(b, 0, -4.0, DZ + 0.4, -1.4)
    b.box((-0.85, -0.2, DZ + 1.1), (0.1, 0.1, 2.2), "timber")
    b.box((-0.6, -0.2, DZ + 2.1), (0.6, 0.07, 0.07), "timber")
    lantern(b, -0.4, -0.2, DZ + 2.06)
    if boat:
        h = Hull(3.8, 1.4, 0.28, 0.38, stern_w=0.55, sheer_bow=0.2, sheer_stern=0.08, stern_rise=0.3, n=9,
                 thick=0.06)
        hb = b.at(dx=1.95, dy=-2.4, dz=WATER, rz=6)
        h.build(hb)
        h.deck(hb, 0.04, 0.08, 0.995, mat="plank_b")
        for t in (0.36, 0.64):
            h.thwart(hb, t)
        rope(b, sag((1.12, -3.85, DZ + 0.6), (1.85, -4.2, WATER + 0.55), 0.2, 5), r=0.02)
    save(b, name)


# --- Treadwheel crane ----------------------------------------------------------------


def crane(name, pal=STONE):
    b = B()
    stone_quay(b, -2.5, 2.5, -2.5, 2.5, pal=pal, faces=(-1, 1))
    for x in (-2.0, 2.0):
        b.cyl((x, -2.0, DZ), (x, -2.0, DZ + 0.5), 0.14, "iron", r2=0.11, seg=7)
        b.cyl((x, -2.0, DZ + 0.5), (x, -2.0, DZ + 0.58), 0.19, "iron", seg=7)
    # A turntable: everything above it turns with the mast.
    b.cyl((0, 0.4, DZ), (0, 0.4, DZ + 0.2), 1.9, "timber", seg=12)
    m = b.bone("mast")
    cy = 0.4
    m.cyl((0, cy, DZ + 0.2), (0, cy, DZ + 0.32), 1.75, "wood", seg=12)
    m.box((0, cy - 0.9, DZ + 2.7), (0.3, 0.3, 4.8), "timber")
    py = cy - 0.9          # The king post.
    for s in (-1, 1):
        m.beam((s * 1.3, cy, DZ + 0.35), (0, py, DZ + 3.0), 0.14, 0.14, "wood")
        m.beam((s * 0.95, cy + 1.2, DZ + 0.35), (s * 0.95, cy + 0.6, DZ + 3.1), 0.14, 0.14, "timber")
        m.beam((s * 0.95, cy - 0.1, DZ + 0.35), (s * 0.95, cy + 0.6, DZ + 3.1), 0.14, 0.14, "timber")
        m.box((s * 0.95, cy + 0.55, DZ + 0.4), (0.16, 1.6, 0.14), "timber")
    m.beam((0, py, DZ + 4.6), (0, cy + 0.6, DZ + 3.1), 0.14, 0.14, "wood")
    m.cyl((-1.1, cy + 0.6, DZ + 1.75), (1.1, cy + 0.6, DZ + 1.75), 0.09, "iron", seg=7)   # The axle.
    wheel = b.bone("wheel")
    ax, az = cy + 0.6, DZ + 1.75
    r = 1.3
    n = 12
    for sx in (-0.42, 0.42):
        for i in range(n):
            a0, a1 = 2 * math.pi * i / n, 2 * math.pi * (i + 1) / n
            wheel.beam((sx, ax + r * math.cos(a0), az + r * math.sin(a0)),
                       (sx, ax + r * math.cos(a1), az + r * math.sin(a1)), 0.1, 0.12, "wood")
        for i in range(4):
            a0 = math.pi * i / 4
            wheel.beam((sx, ax + r * math.cos(a0), az + r * math.sin(a0)),
                       (sx, ax - r * math.cos(a0), az - r * math.sin(a0)), 0.06, 0.08, "timber")
    for i in range(n):   # The treads the walkers step on.
        a0, a1 = 2 * math.pi * (i + 0.08) / n, 2 * math.pi * (i + 0.92) / n
        ya, za = ax + (r - 0.07) * math.cos(a0), az + (r - 0.07) * math.sin(a0)
        yb, zb = ax + (r - 0.07) * math.cos(a1), az + (r - 0.07) * math.sin(a1)
        plate(wheel, (-0.42, ya, za), (0.42, ya, za), (0.42, yb, zb), (-0.42, yb, zb), 0.04,
              "plank" if i % 2 else "plank_b")
    wheel.cyl((-0.3, ax, az), (0.3, ax, az), 0.2, "wood_light", seg=8)
    # The jib: a rigid triangle hinged on the post, with the load hanging from its tip.
    hinge = (0, py - 0.15, DZ + 2.7)
    tip = (0, py - 3.3, DZ + 4.2)
    jib = b.bone("jib")
    jib.beam(hinge, tip, 0.18, 0.2, "timber")
    jib.beam((0, py - 0.15, DZ + 4.3), tip, 0.1, 0.1, "wood")
    jib.beam((0, py - 1.6, DZ + 3.42), (0, py - 1.4, DZ + 4.27), 0.08, 0.08, "wood")
    jib.cyl((-0.14, tip[1], tip[2]), (0.14, tip[1], tip[2]), 0.16, "wood_light", seg=8)
    load = b.bone("load")
    lx, ly = 0.0, tip[1]
    hook_z = tip[2] - 2.3
    rope(load, [(lx, ly, tip[2] - 0.1), (lx, ly, hook_z)], r=0.03)
    load.box((lx, ly, hook_z - 0.08), (0.12, 0.12, 0.16), "iron")
    for s in (-1, 1):
        for e in (-1, 1):
            rope(load, [(lx, ly, hook_z - 0.1), (lx + s * 0.4, ly + e * 0.4, hook_z - 0.55)], r=0.02)
    load.box((lx, ly, hook_z - 0.95), (0.85, 0.85, 0.8), "wood_light")
    load.box((lx, ly, hook_z - 0.95), (0.9, 0.14, 0.86), "wood")
    load.box((lx, ly, hook_z - 0.95), (0.14, 0.9, 0.86), "wood")
    # Goods waiting on the quay.
    crate(b, -1.9, 1.9, z=DZ, s=0.7)
    barrel(b, 1.9, 1.9, z=DZ)
    barrel(b, 1.95, 1.2, z=DZ)
    sack(b, -1.9, 1.1, z=DZ)
    mech = kit.Mech([("mast", (0, cy, DZ), (0, cy, DZ + 0.5), None),
                     ("wheel", (0, ax, az), (0, ax, az + 0.4), "mast"),
                     ("jib", hinge, (hinge[0], hinge[1], hinge[2] + 0.4), "mast"),
                     ("load", (lx, ly, tip[2]), (lx, ly, tip[2] + 0.4), "mast")])
    ry, rz = tip[1] - hinge[1], tip[2] - hinge[2]

    def lift(t):
        up = 0.5 - 0.5 * math.cos(2 * math.pi * t)                  # 0 .. 1 .. 0
        slew = 55 * (0.5 - 0.5 * math.cos(2 * math.pi * (t - 0.12)))
        a = math.radians(22 * up)
        ny = ry * math.cos(a) + rz * math.sin(a)
        nz = -ry * math.sin(a) + rz * math.cos(a)
        return ({"mast": [(kit.Z, slew)], "jib": [(kit.X, -22 * up)], "wheel": [(kit.X, 540 * up)]},
                {"load": (0.0, ny - ry, nz - rz)})

    mech.clip("lift", 6.0, lift)
    save(b, name, mech=mech)


# --- Ferry landing -------------------------------------------------------------------


def ferry_landing(name):
    b = B()

    def zf(y):
        return lerp(0.25, -0.55, (2.5 - y) / 5.0)

    n = 16
    for i in range(n):   # The ramp of boards that runs down into the water.
        ya, yb = 2.5 - 5.0 * i / n, 2.5 - 5.0 * (i + 1) / n
        b.solid([(-2, ya, zf(ya) - 0.07), (2, ya, zf(ya) - 0.07), (2, ya, zf(ya)), (-2, ya, zf(ya))],
                [(-2, yb + 0.02, zf(yb) - 0.07), (2, yb + 0.02, zf(yb) - 0.07), (2, yb + 0.02, zf(yb)),
                 (-2, yb + 0.02, zf(yb))], "plank" if i % 2 else "plank_b")
    for x in (-1.8, 0.0, 1.8):
        b.beam((x, 2.5, zf(2.5) - 0.17), (x, -2.5, zf(-2.5) - 0.17), 0.16, 0.2, "timber")
    for y in (-2.2, -0.4, 1.4):
        for x in (-1.9, 1.9):
            pile(b, x, y, zf(y) - 0.2, deep=-2.5)
        b.box((0, y, zf(y) - 0.35), (4.2, 0.16, 0.16), "timber")
    b.box((0, 2.75, 0.02), (4.4, 0.5, 0.2), "stone")
    # Two tall posts carry the guide rope of the ferry; a capstan tightens it.
    for x in (-2.25, 2.25):
        pile(b, x, -2.2, 2.6, deep=-2.5, r=0.14)
        b.cyl((x, -2.2, 2.6), (x, -2.2, 2.7), 0.17, "wood_light", seg=7)
        b.beam((x, -1.2, 0.0), (x, -2.2, 1.5), 0.1, 0.1, "wood")
    b.box((1.9, -2.2, 2.3), (0.9, 0.12, 0.12), "timber")
    b.cyl((1.45, -2.32, 2.3), (1.45, -2.08, 2.3), 0.16, "wood_light", seg=8)
    rope(b, [(1.45, 2.0, 0.75), (1.45, -2.2, 2.42), (1.45, -5.5, 2.2)], r=0.035)
    b.cyl((1.45, 2.0, 0.0), (1.45, 2.0, 0.9), 0.22, "wood", seg=8)
    b.cyl((1.45, 2.0, 0.9), (1.45, 2.0, 1.0), 0.26, "timber", seg=8)
    for k in range(4):
        a = k * math.pi / 2 + 0.4
        b.cyl((1.45, 2.0, 0.78), (1.45 + math.cos(a) * 0.75, 2.0 + math.sin(a) * 0.75, 0.8), 0.03, "wood_light",
              seg=5)
    for k in range(4):
        b.cyl((1.45, 2.0, 0.3 + k * 0.08), (1.45, 2.0, 0.37 + k * 0.08), 0.25, "rope", seg=8)
    # A bell to call the ferryman, a sign and waiting cargo.
    b.box((-2.2, 1.9, 1.2), (0.12, 0.12, 2.4), "timber")
    b.box((-1.85, 1.9, 2.3), (0.8, 0.08, 0.08), "timber")
    b.cyl((-1.6, 1.9, 2.0), (-1.6, 1.9, 2.25), 0.16, "bell", r2=0.07, seg=8)
    b.cyl((-1.6, 1.9, 1.92), (-1.6, 1.9, 2.0), 0.04, "iron", seg=5)
    b.box((-2.2, 1.82, 1.6), (0.7, 0.05, 0.4), "wood_light")
    b.box((-2.2, 1.79, 1.6), (0.5, 0.02, 0.08), "paint_blue")
    crate(b, -1.2, 2.9, z=0.12, s=0.6)
    sack(b, -0.5, 2.9, z=0.12)
    lantern(b, 2.25, -2.0, 2.2)
    save(b, name)


# --- Boathouse -----------------------------------------------------------------------


def boathouse(name, roof="shingle", boat=True):
    b = B()
    w, d = 6.0, 8.0
    # Two walkways on piles with a slip of water between them, open toward -Y.
    for s in (-1, 1):
        xa, xb = sorted((s * 1.7, s * 3.0))
        wood_deck(b, xa, xb, -4, 3, brace=False)
    wood_deck(b, -3, 3, 3, 4, brace=False)
    wall_h = DZ + 2.6
    for s in (-1, 1):
        x = s * (w / 2 - 0.08)
        for k in range(5):
            y = -4 + 0.1 + k * (d - 0.2) / 4
            b.box((x, y, DZ + 1.3), (0.18, 0.18, 2.6), "timber")
        b.box((x, 0, wall_h - 0.09), (0.18, d, 0.18), "timber")
        for k in range(9):
            b.box((x + s * 0.02, 0, DZ + 0.16 + k * 0.27), (0.06, d - 0.2, 0.25), "wood" if k % 2 else "wood_light")
        for y in (-2.0, 1.0):
            b.box((x + s * 0.04, y, DZ + 1.6), (0.06, 0.8, 0.6), "window")
            b.box((x + s * 0.05, y, DZ + 1.6), (0.05, 0.9, 0.08), "timber")
    for x in (-w / 2 + 0.08, w / 2 - 0.08):
        b.box((x, 4 - 0.1, DZ + 1.3), (0.18, 0.18, 2.6), "timber")
    for k in range(9):   # Back wall with the door to the shore.
        for s in (-1, 1):
            b.box((s * 1.75, 3.94, DZ + 0.16 + k * 0.27), (2.3, 0.06, 0.25), "wood" if k % 2 else "wood_light")
    b.box((0, 3.94, DZ + 2.15), (1.2, 0.06, 0.9), "wood")
    b.box((0, 3.97, DZ + 0.85), (1.0, 0.06, 1.7), "door")
    b.box((0, 4.0, DZ + 0.85), (1.16, 0.05, 1.8), "timber")
    b.box((0, 4.3, DZ / 2), (1.6, 0.6, DZ), "stone")
    b.box((0, -3.92, wall_h - 0.09), (w, 0.18, 0.18), "timber")
    for s in (-1, 1):
        b.beam((s * (w / 2 - 0.2), -3.92, wall_h - 0.9), (s * (w / 2 - 1.1), -3.92, wall_h - 0.15), 0.12, 0.12,
               "timber")
    for y in (-1.5, 1.0):
        b.box((0, y, wall_h - 0.09), (w, 0.14, 0.14), "timber")
    roof_y(b, 0, 0, w, d, wall_h, 1.9, 0.4, list(ROOFS[roof]), rows=6, gables=(-1, 1))
    b.box((0, -4.02, wall_h + 0.75), (0.5, 0.06, 0.5), "window")
    lantern(b, 0, -4.2, wall_h - 0.2)
    # Gear inside: oars on the wall, a barrel, a coil of rope and a winch beam.
    barrel(b, 2.4, 2.2, z=DZ)
    crate(b, -2.4, 2.4, z=DZ, s=0.6)
    for k in range(3):
        b.cyl((-2.45, 0.8, DZ + 0.02 + k * 0.07), (-2.45, 0.8, DZ + 0.08 + k * 0.07), 0.28, "rope", seg=8)
    for k in range(2):
        b.cyl((2.75, -1.0 + k * 0.3, DZ + 0.1), (2.82, -1.0 + k * 0.3, DZ + 2.4), 0.03, "wood_light", seg=5)
    if boat:
        h = Hull(4.6, 1.6, 0.3, 0.42, stern_w=0.5, sheer_bow=0.25, sheer_stern=0.1, stern_rise=0.3, n=10, thick=0.06)
        hb = b.at(dy=-0.6, dz=WATER)
        h.build(hb, strakes=("paint_blue", "wood_light", "wood"))
        h.deck(hb, 0.04, 0.08, 0.995, mat="plank_b")
        for t in (0.36, 0.64):
            h.thwart(hb, t)
    save(b, name)


# --- Lighthouse and beacon -----------------------------------------------------------


def flicker(extra=None):
    def pose(t):
        turns = {"flame": [(kit.Z, 360 * t), (kit.X, 6 * math.sin(4 * math.pi * t))]}
        if extra:
            turns.update(extra(t))
        return turns, {"flame": (0.0, 0.0, 0.05 * math.sin(6 * math.pi * t))}
    return pose


def lighthouse(name, bands=("stone", "stone_light"), base="stone_dark", cap="roof"):
    b = B()
    for k in range(9):   # Rocks of the point it stands on.
        a = k * 0.7
        rock(b, math.cos(a) * (2.9 + jit(k, 0.4)), math.sin(a) * (2.9 + jit(k, 0.4, 2)), 0.9 + jit(k, 0.3, 3), -1.5,
             0.3 + abs(jit(k, 0.5, 4)), seed=k, mat="stone_dark" if k % 2 else "stone")
    levels = [(0.0, 2.6), (2.5, 2.25), (5.0, 2.0), (7.5, 1.8), (10.0, 1.6), (11.0, 1.55)]
    for k, ((z0, r0), (z1, r1)) in enumerate(zip(levels, levels[1:])):
        b.cyl((0, 0, z0), (0, 0, z1), r0, base if k == 0 else bands[k % 2], r2=r1, seg=8)
        b.cyl((0, 0, z1 - 0.1), (0, 0, z1 + 0.1), r1 + 0.08, base, seg=8)
    b.cyl((0, 0, -1.5), (0, 0, 0.0), 2.75, base, r2=2.6, seg=8)
    # Door toward -Y with steps, and windows up the stair.
    b.box((0, -2.5, 1.0), (1.3, 0.5, 2.0), base)
    b.box((0, -2.74, 0.9), (0.95, 0.08, 1.7), "door")
    b.xz([(-0.7, 2.0), (0.7, 2.0), (0, 2.5)], -2.78, -2.2, cap)
    for k in range(3):
        b.box((0, -3.0 - k * 0.3, 0.1 - k * 0.1), (1.5, 0.3, 0.2), "stone_light")
    for k, (z, a) in enumerate(((4.0, -1.57), (6.2, 0.4), (8.4, 2.4), (9.6, -1.57))):
        r = lerp(2.25, 1.6, (z - 2.5) / 7.5) + 0.02
        b.box((math.cos(a) * r, math.sin(a) * r, z), (0.4, 0.4, 0.8), "window", rz=a)
    # Gallery, lantern room and its roof.
    gz = 11.0
    b.cyl((0, 0, gz), (0, 0, gz + 0.25), 2.35, base, seg=8)
    for k in range(8):
        a = 2 * math.pi * (k + 0.5) / 8
        b.beam((math.cos(a) * 1.5, math.sin(a) * 1.5, gz - 0.7), (math.cos(a) * 2.2, math.sin(a) * 2.2, gz), 0.2, 0.2,
               base)
        p = (math.cos(a) * 2.2, math.sin(a) * 2.2, gz + 0.25)
        a2 = 2 * math.pi * (k + 1.5) / 8
        q = (math.cos(a2) * 2.2, math.sin(a2) * 2.2, gz + 0.25)
        b.box((p[0], p[1], p[2] + 0.45), (0.08, 0.08, 0.9), "iron")
        b.beam((p[0], p[1], p[2] + 0.88), (q[0], q[1], q[2] + 0.88), 0.06, 0.06, "iron")
        b.beam((p[0], p[1], p[2] + 0.45), (q[0], q[1], q[2] + 0.45), 0.04, 0.04, "iron")
    lz = gz + 0.25
    b.cyl((0, 0, lz), (0, 0, lz + 0.6), 1.25, bands[0], seg=8)
    for k in range(8):
        a = 2 * math.pi * (k + 0.5) / 8
        b.box((math.cos(a) * 1.15, math.sin(a) * 1.15, lz + 1.5), (0.1, 0.1, 1.9), "iron", rz=a)
    b.cyl((0, 0, lz + 2.4), (0, 0, lz + 2.55), 1.5, "iron", seg=8)
    b.cyl((0, 0, lz + 2.55), (0, 0, lz + 3.9), 1.45, cap, r2=0.12, seg=8)
    b.sphere((0, 0, lz + 4.0), 0.18, "gold", seg=6, rings=4)
    b.cyl((0, 0, lz + 4.0), (0, 0, lz + 4.6), 0.03, "iron", seg=4)
    # The fire in its brazier, and a mirror that turns around it.
    b.cyl((0, 0, lz + 0.6), (0, 0, lz + 1.0), 0.2, "iron", seg=6)
    b.cyl((0, 0, lz + 1.0), (0, 0, lz + 1.25), 0.35, "iron", r2=0.55, seg=8)
    f = b.bone("flame")
    flame(f, 0, 0, lz + 1.2, s=1.1)
    mir = b.bone("mirror")
    for k in (-1, 0, 1):
        a = math.pi / 2 + k * 0.5
        mir.box((math.cos(a) * 0.85, math.sin(a) * 0.85, lz + 1.6), (0.46, 0.05, 0.9), "gold", rz=a + math.pi / 2)
    mir.box((0, 0.42, lz + 1.08), (0.08, 0.85, 0.06), "iron")
    mech = kit.Mech([("flame", (0, 0, lz + 1.2), (0, 0, lz + 1.6), None),
                     ("mirror", (0, 0, lz + 1.0), (0, 0, lz + 1.4), None)])
    mech.clip("flicker", 1.5, flicker())
    mech.clip("turn", 6.0, lambda t: ({"mirror": [(kit.Z, 360 * t)],
                                       "flame": [(kit.Z, 360 * 4 * t), (kit.X, 6 * math.sin(16 * math.pi * t))]},
                                      {}))
    save(b, name, mech=mech)


def beacon(name, pal=WOOD):
    b = B()
    top = 6.0
    legs = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            legs.append(((sx * 1.4, sy * 1.4, -0.3), (sx * 0.95, sy * 0.95, top)))
            b.cyl(legs[-1][0], legs[-1][1], 0.13, pal["body"], r2=0.1, seg=7)
            b.box((sx * 1.42, sy * 1.42, 0.1), (0.5, 0.5, 0.3), "stone")

    def at(sx, sy, z):
        f = z / top
        return (sx * lerp(1.4, 0.95, f), sy * lerp(1.4, 0.95, f), z)

    for z0, z1 in ((0.4, 2.8), (2.8, 5.4)):
        for sx, sy, tx, ty in ((-1, -1, 1, -1), (1, -1, 1, 1), (1, 1, -1, 1), (-1, 1, -1, -1)):
            b.beam(at(sx, sy, z0), at(tx, ty, z1), 0.07, 0.12, pal["trim"])
            b.beam(at(tx, ty, z0), at(sx, sy, z1), 0.07, 0.12, pal["trim"])
            b.beam(at(sx, sy, z1), at(tx, ty, z1), 0.1, 0.12, pal["trim"])
    planks_x(b, -1.5, 1.5, 3.0, z=top + 0.12, mats=pal["deck"])
    b.box((0, 0, top), (3.0, 0.14, 0.14), pal["trim"])
    for s in (-1, 1):
        b.box((0, s * 1.2, top), (3.0, 0.14, 0.14), pal["trim"])
        rail(b, [(-1.42, s * 1.42, top + 0.12), (0, s * 1.42, top + 0.12), (1.42, s * 1.42, top + 0.12)], h=0.9,
             mat=pal["trim"], rail_mat=pal["body"])
        rail(b, [(s * 1.42, -1.42, top + 0.12), (s * 1.42, 1.42, top + 0.12)], h=0.9, mat=pal["trim"],
             rail_mat=pal["body"])
    # Ladder up the -Y face.
    for s in (-1, 1):
        b.beam((s * 0.25, -1.75, 0.0), (s * 0.25, -1.5, top + 0.9), 0.06, 0.06, pal["trim"])
    for k in range(18):
        z = 0.3 + k * 0.34
        b.box((0, -1.75 + 0.25 * z / (top + 0.9), z), (0.5, 0.05, 0.05), pal["body"])
    # Iron fire basket on a stone hearth.
    b.box((0, 0, top + 0.27), (1.1, 1.1, 0.3), "stone")
    b.cyl((0, 0, top + 0.42), (0, 0, top + 0.9), 0.08, "iron", seg=6)
    b.cyl((0, 0, top + 0.9), (0, 0, top + 1.3), 0.4, "iron", r2=0.62, seg=8)
    for k in range(4):
        a = k * 0.8
        b.cyl((math.cos(a) * 0.45, math.sin(a) * 0.45, top + 1.3), (-math.cos(a) * 0.45, -math.sin(a) * 0.45,
                                                                   top + 1.42), 0.08, "charcoal", seg=5)
    f = b.bone("flame")
    flame(f, 0, 0, top + 1.3, s=1.3)
    flame(f, 0.25, 0.1, top + 1.3, s=0.7)
    flame(f, -0.2, -0.15, top + 1.3, s=0.8)
    mech = kit.Mech([("flame", (0, 0, top + 1.3), (0, 0, top + 1.7), None)])
    mech.clip("flicker", 1.5, flicker())
    save(b, name, mech=mech)


for _kind, _prefix in (("wood", "dock_pier"), ("stone", "dock_quay"), ("brick", "dock_quay_brick")):
    for _piece in ("straight", "corner", "end", "ramp"):
        model("%s_%s" % (_prefix, _piece), pier_model, kind=_kind, piece=_piece)
    model("%s_demo" % _prefix, pier_demo, kind=_kind)
model("dock_fishing", fishing_dock)
model("dock_crane", crane)
model("dock_crane_brick", crane, pal=BRICK)
model("dock_ferry_landing", ferry_landing)
model("dock_boathouse", boathouse, roof="shingle")
model("dock_boathouse_thatch", boathouse, roof="thatch")
model("dock_boathouse_tile", boathouse, roof="tile")
model("dock_lighthouse", lighthouse)
model("dock_lighthouse_white", lighthouse, bands=("plaster", "cloth_red"), base="stone", cap="slate")
model("dock_lighthouse_brick", lighthouse, bands=("brick", "brick_light"), base="stone_dark", cap="slate")
model("dock_beacon", beacon)
