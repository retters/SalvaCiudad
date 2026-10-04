"""More ideas of the `bridges` family: bridges of the fantasy races, fortified
and inhabited bridges, a shipyard, a fish weir, a breakwater, a washing
place, a toll gate, a wreck and boats of the other races."""

import math

from parts import (B, BRICK, ROOFS, TARRED, barrel, crate, flame, jit, lantern, lerp, log, net, planks_x, planks_y,
                   rail, rock, roof_y, rope, sag, save, smoothstep)
from bridges import plank_trestle, stone_bridge
from boats import Hull, finish, floating, flutter, merchant, merge, oar, pennant, rowing, sail, waving
from docks import DZ, pile, wood_deck
import _kit as kit

MODELS = {}


def model(name, fn, **kw):
    MODELS[name] = lambda: fn(name, **kw)


# --- Fortified bridge ----------------------------------------------------------------


def gate_tower(b, top, length, width, pal):
    """A gate tower over the middle pier, with a portcullis."""
    z = top(0.0)
    tw, td, th = 3.0, width + 0.8, 7.0
    pw = 2.6
    side = (td - pw) / 2
    for s in (-1, 1):
        b.box((0, s * (pw / 2 + side / 2), z + th / 2 - 0.3), (tw, side, th + 0.6), pal["body"])
    b.box((0, 0, z + 3.3 + (th - 3.3) / 2), (tw, pw, th - 3.3), pal["body"])
    for e in (-1, 1):
        x = e * (tw / 2 + 0.03)
        for k in range(5):
            b.box((x, lerp(-pw / 2 + 0.26, pw / 2 - 0.26, k / 4), z + 3.5), (0.1, 0.5, 0.42), pal["ring"][k % 2])
        for s in (-1, 1):
            for k in range(4):
                b.box((x, s * (pw / 2 + 0.2), z + 0.4 + k * 0.8), (0.1, 0.42, 0.38), pal["ring"][k % 2])
            b.box((x, s * 1.0, z + 5.6), (0.08, 0.16, 0.9), "window")
        b.box((x + e * 0.03, 0, z + 4.75), (0.05, 0.9, 1.5), "cloth_red")
        b.box((x + e * 0.05, 0, z + 4.9), (0.05, 0.4, 0.4), "gold")
    for s in (-1, 1):
        b.box((0, s * (td / 2 + 0.03), z + 4.5), (0.16, 0.08, 0.9), "window")
    b.box((0, 0, z + th + 0.1), (tw + 0.3, td + 0.3, 0.2), pal["trim"])
    for s in (-1, 1):
        for x in (-1.25, 0.0, 1.25):
            b.box((x, s * (td / 2), z + th + 0.55), (0.6, 0.35, 0.7), pal["body"])
        for k in range(5):
            b.box((s * (tw / 2), lerp(-td / 2 + 0.3, td / 2 - 0.3, k / 4), z + th + 0.55), (0.35, 0.6, 0.7),
                  pal["body"])
    q, r = tw / 2 - 0.4, td / 2 - 0.4
    b.xy([(-q, -r), (q, -r), (q, r), (-q, r)], z + th + 0.2, z + th + 2.4, "slate", shrink=0.04)
    b.cyl((0, 0, z + th + 2.3), (0, 0, z + th + 3.3), 0.03, "iron", seg=4)
    b.solid([(0, 0, z + th + 2.8), (0, 0, z + th + 3.25), (0, 0.7, z + th + 3.0)],
            [(0.03, 0, z + th + 2.8), (0.03, 0, z + th + 3.25), (0.03, 0.7, z + th + 3.0)], "cloth_red")
    g = b.bone("gate")
    x = -tw / 2 + 0.35
    for k in range(7):
        y = lerp(-pw / 2 + 0.12, pw / 2 - 0.12, k / 6)
        g.box((x, y, z + 1.7), (0.07, 0.07, 3.2), "iron")
        g.cyl((x, y, z + 0.1), (x, y, z - 0.08), 0.045, "iron", r2=0.005, seg=4)
    for k in range(4):
        g.box((x, 0, z + 0.55 + k * 0.85), (0.06, pw - 0.1, 0.08), "iron")
    mech = kit.Mech([("gate", (x, 0, z), (x, 0, z + 0.5), None)])
    mech.clip("open", 2.5, lambda t: ({}, {"gate": (0.0, 0.0, 3.0 * smoothstep(t))}), loops=False)
    mech.clip("close", 1.5, lambda t: ({}, {"gate": (0.0, 0.0, 3.0 * (1 - smoothstep(t)))}), loops=False)
    return mech


# --- Dwarven and orc bridges ---------------------------------------------------------

DWARF = {"body": "stone_dark", "trim": "slate_dark", "cap": "stone", "ring": ("stone", "slate"), "road": "slate",
         "deck": ("stone", "stone_dark")}


def dwarf_extra(b, top, length, width, pal):
    bones = []
    k = 0
    for e in (-1, 1):
        for s in (-1, 1):
            x, y = e * (length / 2 - 0.6), s * (width / 2 + 0.25)
            q = 0.5
            b.xy([(x - q, y - q), (x + q, y - q), (x + q, y + q), (x - q, y + q)], -0.6, 3.2, pal["body"],
                 shrink=0.72)
            b.box((x, y, 0.5), (1.08, 1.08, 0.16), "iron")
            b.box((x, y, 2.5), (0.86, 0.86, 0.14), "iron")
            b.box((x, y, 3.25), (0.95, 0.95, 0.14), pal["cap"])
            for dz, wide in ((1.9, 0.3), (1.6, 0.12), (1.3, 0.3)):   # A rune on the outer face.
                b.box((x, y + s * 0.44, dz), (wide, 0.06, 0.08), "gold")
            b.box((x, y + s * 0.44, 1.6), (0.08, 0.06, 0.6), "gold")
            b.cyl((x, y, 3.3), (x, y, 3.55), 0.3, "iron", r2=0.48, seg=8)
            name = "flame%d" % k
            bones.append((name, (x, y, 3.5), (x, y, 3.9), None))
            flame(b.bone(name), x, y, 3.5, s=0.8)
            k += 1
    for s in (-1, 1):   # A shield with crossed hammers over the crown of the arch.
        y = s * (width / 2 + 0.1)
        b.cyl((0, y - 0.04, top(0) - 0.25), (0, y + 0.04, top(0) - 0.25), 0.5, "iron", seg=8)
        b.box((0, y + s * 0.05, top(0) - 0.25), (0.6, 0.05, 0.1), "gold", rz=0.0)
        b.box((0, y + s * 0.05, top(0) - 0.25), (0.1, 0.05, 0.6), "gold")
    mech = kit.Mech(bones)

    def pose(t):
        turns, moves = {}, {}
        for i in range(4):
            turns["flame%d" % i] = [(kit.Z, 360 * t + i * 90), (kit.X, 6 * math.sin(4 * math.pi * t + i))]
            moves["flame%d" % i] = (0.0, 0.0, 0.04 * math.sin(6 * math.pi * t + i))
        return turns, moves

    mech.clip("flicker", 1.5, pose)
    return mech


def skull(b, x, y, z, s=0.22):
    b.sphere((x, y, z), s, "bark", seg=6, rings=4, scale=(1.0, 1.15, 0.95))
    b.box((x, y - s * 0.9, z - s * 0.55), (s * 0.9, s * 0.7, s * 0.5), "bark")
    for e in (-1, 1):
        b.box((x + e * s * 0.4, y - s * 1.0, z + s * 0.05), (s * 0.3, s * 0.2, s * 0.3), "charcoal")
        b.cyl((x + e * s * 0.7, y, z + s * 0.4), (x + e * s * 1.8, y - s * 0.2, z + s * 1.3), s * 0.25, "bark",
              r2=0.01, seg=5)


def orc_extra(b, length, width, zd, pal):
    half = length / 2
    n = round(length / 0.6)
    for s in (-1, 1):
        for i in range(n):   # Sharpened stakes that lean out over the water.
            x = -half + 0.6 + i * (length - 1.2) / (n - 1)
            tip = (x + jit(i, 0.08), s * (width / 2 + 0.55), zd + 0.9 + jit(i, 0.2, s))
            b.cyl((x, s * (width / 2 - 0.1), zd - 0.2), tip, 0.07, "wood_dark", r2=0.01, seg=5)
        b.beam((-half + 0.5, s * (width / 2 + 0.12), zd + 0.25), (half - 0.5, s * (width / 2 + 0.12), zd + 0.25), 0.08,
               0.08, "tar")
        for e in (-1, 1):   # A totem pole with a horned skull and a ragged banner at each corner.
            x, y = e * (half - 0.3), s * (width / 2 + 0.3)
            b.cyl((x, y, -0.5), (x + e * 0.1, y, 3.2), 0.14, "wood_dark", r2=0.1, seg=6)
            skull(b, x + e * 0.1, y, 3.4, 0.24)
            b.box((x + e * 0.1, y - s * 0.0, 2.6), (0.7, 0.06, 0.06), "tar")
            b.solid([(x - 0.2, y, 2.58), (x + 0.4, y, 2.58), (x + 0.3, y, 1.6), (x + 0.0, y, 1.9), (x - 0.15, y, 1.5)],
                    [(x - 0.2, y + 0.03, 2.58), (x + 0.4, y + 0.03, 2.58), (x + 0.3, y + 0.03, 1.6),
                     (x + 0.0, y + 0.03, 1.9), (x - 0.15, y + 0.03, 1.5)], "cloth_red")
            for k in range(3):
                b.cyl((x, y, 0.8 + k * 0.5), (x, y, 0.88 + k * 0.5), 0.17, "hide", seg=6)
    return None


# --- Clapper and moon bridges --------------------------------------------------------


def clapper(name, length=8.0, width=2.0):
    b = B()
    n = 4
    xs = [-length / 2 + 0.4 + k * (length - 0.8) / n for k in range(n + 1)]
    for k, x in enumerate(xs):
        rock(b, x, 0, 0.85, -2.2, -0.9, seed=k, mat="stone_dark", sides=7, shrink=0.9, squash=1.5)
        rock(b, x + jit(k, 0.08), 0, 0.72, -0.9, -0.2, seed=k + 9, mat="stone", sides=6, shrink=0.9, squash=1.5)
        rock(b, x + jit(k, 0.08, 4), 0, 0.62, -0.2, 0.22, seed=k + 5, mat="stone_dark", sides=6, shrink=0.92,
             squash=1.6)
    for k in range(n):
        xa, xb = xs[k] - 0.3, xs[k + 1] + 0.3
        pts = [(xa + jit(k, 0.1, 1), -width / 2 + jit(k, 0.1, 2)), (xb + jit(k, 0.1, 3), -width / 2 + jit(k, 0.12, 4)),
               (xb + jit(k, 0.1, 5), width / 2 + jit(k, 0.1, 6)), (xa + jit(k, 0.1, 7), width / 2 + jit(k, 0.12, 8))]
        z = 0.22 + 0.05 * (k % 2)
        b.xy(pts, z, z + 0.26, "stone" if k % 2 else "stone_light", shrink=0.96)
        b.box((lerp(xa, xb, 0.5 + jit(k, 0.3)), jit(k, 0.5, 9), z + 0.265), (0.5, 0.4, 0.02), "moss", rz=jit(k, 1.0))
    save(b, name)


def moon(name, length=8.0, width=2.4, paint="paint_red"):
    b = B()
    half = length / 2
    hump = 1.5

    def top(x):
        return hump * (1 - (x / half) ** 2)

    planks_x(b, -half, half, width, zf=top, step=0.25)
    n = 16
    for y in (-width / 2 + 0.2, 0.0, width / 2 - 0.2):
        for i in range(n):
            xa, xb = -half + length * i / n, -half + length * (i + 1) / n
            b.beam((xa, y, top(xa) - 0.2), (xb, y, top(xb) - 0.2), 0.16, 0.24, paint)
    for x in (-half * 0.5, half * 0.5):
        for s in (-1, 1):
            b.cyl((x, s * (width / 2 - 0.2), -2.5), (x, s * (width / 2 - 0.2), top(x) - 0.3), 0.12, "timber", seg=7)
        b.box((x, 0, top(x) - 0.42), (0.2, width + 0.1, 0.2), "timber")
        b.box((x, 0, -0.5), (0.12, width - 0.3, 0.14), "timber")
    for s in (-1, 1):
        y = s * (width / 2 - 0.1)
        xs = [-half + 0.15 + i * (length - 0.3) / 8 for i in range(9)]
        rail(b, [(x, y, top(x)) for x in xs], h=0.9, post=0.11, mat=paint, rail_mat=paint, top=0.1, cap="gold")
        for xa, xb in zip(xs, xs[1:]):
            b.beam((xa, y, top(xa) + 0.25), (xb, y, top(xb) + 0.25), 0.05, 0.06, paint)
        for e in (-1, 1):
            x = e * (half + 0.05)
            b.box((x, y, 0.65), (0.2, 0.2, 1.5), paint)
            b.box((x, y, 1.42), (0.3, 0.3, 0.08), "gold")
            b.sphere((x, y, 1.6), 0.15, "gold", seg=6, rings=4, scale=(1, 1, 1.3))
            b.box((x, y, 0.08), (0.5, 0.5, 0.3), "stone")
    save(b, name)


# --- Inhabited bridge ----------------------------------------------------------------


def shops(b, top, length, width, pal):
    roofs = (("roof", "roof_dark"), ("slate", "slate_dark"), ("shingle", "shingle_dark"))
    walls = ("plaster", "plaster_warm")
    spots = [(-5.6, 1), (0.0, 1), (5.6, 1), (-2.8, -1), (2.8, -1)]
    for k, (x, s) in enumerate(spots):
        sx, sy, sh = 2.6, 2.0, 2.3
        yc = s * (width / 2 + 0.2)
        zf = max(top(x - sx / 2), top(x + sx / 2)) + 0.12
        b.box((x, yc, zf - 0.4), (sx + 0.1, sy + 0.1, 0.8), "timber")
        for dx in (-1.0, 1.0):   # Struts down to the wall of the bridge.
            b.beam((x + dx, s * (width / 2 + 0.02), zf - 1.7), (x + dx, s * (width / 2 + 1.1), zf - 0.7), 0.14, 0.14,
                   "timber")
        b.box((x, yc, zf + sh / 2), (sx, sy, sh), walls[k % 2])
        for dx in (-1, 1):
            for dy in (-1, 1):
                b.box((x + dx * sx / 2, yc + dy * sy / 2, zf + sh / 2), (0.14, 0.14, sh), "timber")
        for dy in (-1, 1):
            b.box((x, yc + dy * sy / 2, zf + sh - 0.07), (sx, 0.14, 0.14), "timber")
            b.box((x, yc + dy * sy / 2, zf + 1.0), (sx, 0.1, 0.1), "timber")
        yin, yout = yc - s * sy / 2, yc + s * sy / 2
        b.box((x - 0.7, yin - s * 0.04, zf + 0.85), (0.8, 0.06, 1.6), "door")
        b.box((x + 0.55, yin - s * 0.04, zf + 1.4), (0.9, 0.06, 0.7), "window")
        b.box((x + 0.55, yin - s * 0.2, zf + 0.98), (1.0, 0.36, 0.06), "wood")
        b.solid([(x + 0.0, yin - s * 0.02, zf + 2.05), (x + 1.1, yin - s * 0.02, zf + 2.05),
                 (x + 1.1, yin - s * 0.7, zf + 1.8), (x + 0.0, yin - s * 0.7, zf + 1.8)],
                [(x + 0.0, yin - s * 0.02, zf + 2.1), (x + 1.1, yin - s * 0.02, zf + 2.1),
                 (x + 1.1, yin - s * 0.7, zf + 1.85), (x + 0.0, yin - s * 0.7, zf + 1.85)],
                ("cloth_red", "cloth_blue", "cloth_green")[k % 3])
        b.box((x, yout + s * 0.04, zf + 1.3), (0.7, 0.06, 0.6), "window")
        for dx in (-1, 1):
            b.box((x + dx * 0.5, yout + s * 0.05, zf + 1.3), (0.24, 0.05, 0.56), "shutter")
        zw = zf + sh
        mats = roofs[k % 3]
        for side in (-1, 1):
            ye, zr = yc + side * (sy / 2 + 0.25), zw + 0.95
            ring = [(x - sx / 2 - 0.2, ye, zw - 0.1), (x + sx / 2 + 0.2, ye, zw - 0.1), (x + sx / 2 + 0.2, yc, zr),
                    (x - sx / 2 - 0.2, yc, zr)]
            b.solid(ring, [(px, py, pz + 0.1) for px, py, pz in ring], mats[0 if side > 0 else 1])
        b.box((x, yc, zw + 1.03), (sx + 0.4, 0.2, 0.1), mats[1])
        for dx in (-1, 1):
            xg = x + dx * sx / 2
            b.yz([(yc - sy / 2, zw), (yc + sy / 2, zw), (yc, zw + 0.85)], xg - 0.05, xg + 0.05, walls[k % 2])
        if k % 2 == 0:
            b.box((x + 0.8, yc + s * 0.4, zw + 0.8), (0.4, 0.4, 1.2), "stone")
    for e in (-1, 1):
        lantern(b, e * 8.0, 0.0, top(e * 8.0) + 3.0)
        for s in (-1, 1):
            b.box((e * 8.0, s * (width / 2 - 0.3), top(e * 8.0) + 1.5), (0.14, 0.14, 3.0), "timber")
        b.box((e * 8.0, 0, top(e * 8.0) + 3.0), (0.14, width - 0.5, 0.14), "timber")
    return None


# --- Works on the shore --------------------------------------------------------------


def shipyard(name):
    b = B()

    def zs(y):
        return lerp(0.12, -0.95, (6.5 - y) / 14.0)

    for x in (-0.9, 0.9):   # The slipway that runs down into the water.
        b.beam((x, 6.5, zs(6.5)), (x, -7.5, zs(-7.5)), 0.24, 0.24, "timber")
    for k in range(11):
        y = 6.0 - k * 1.3
        log(b, (-1.7, y, zs(y) - 0.2), (1.7, y, zs(y) - 0.2), 0.14, seg=6)
    h = Hull(9.0, 3.0, 0.8, 0.9, stern_w=0.45, sheer_bow=0.5, sheer_stern=0.3, n=12, thick=0.09)
    hb = b.at(dy=1.0, dz=1.35)
    h.build(hb, stations=(6, 12), strakes=("wood_light", "wood", "wood"), inner="wood_light")
    h.ribs(hb, [i / 12 for i in range(1, 6)])
    for i in range(6):
        ta, tb = i / 12, (i + 1) / 12
        hb.beam((0, h.y(ta), h.bot(ta) - 0.02), (0, h.y(tb), h.bot(tb) - 0.02), 0.12, 0.14, "timber")
        for s in (-1, 1):
            hb.beam((s * h.w(ta), h.y(ta), h.top(ta)), (s * h.w(tb), h.y(tb), h.top(tb)), 0.07, 0.09, "wood_light")
            hb.beam((s * h.w(ta) * 0.9, h.y(ta), lerp(h.bot(ta), h.top(ta), 0.45)),
                    (s * h.w(tb) * 0.9, h.y(tb), lerp(h.bot(tb), h.top(tb), 0.45)), 0.05, 0.07, "wood")
    hb.beam((0, h.y(0) - 0.02, h.bot(0) - 0.05), (0, h.y(0) - 0.1, h.top(0) + 0.3), 0.12, 0.16, "timber")
    for y in (-2.2, -0.2, 1.8, 3.8):   # Stocks under the keel and shores against the sides.
        b.box((0, y, 0.27), (0.6, 0.4, 0.5), "timber")
        b.box((0, y, 0.05), (1.2, 0.3, 0.14), "wood")
        for s in (-1, 1):
            b.beam((s * 2.5, y, 0.0), (s * 1.25, y, 1.5), 0.1, 0.1, "wood")
    # Scaffold along one side, with a ladder.
    for y in (-2.5, 0.5, 3.5):
        for x in (2.0, 3.0):
            b.box((x, y, 1.3), (0.1, 0.1, 2.6), "timber")
        b.box((2.5, y, 1.85), (1.1, 0.08, 0.1), "timber")
    planks_y(b, -2.7, 3.7, 0.9, z=2.0, xc=2.5, step=0.8, thick=0.06)
    b.box((2.02, 0.5, 2.5), (0.06, 6.2, 0.06), "wood")
    for s in (-1, 1):
        b.beam((3.4, 3.9 + s * 0.2, 0.0), (2.9, 3.9 + s * 0.2, 2.0), 0.05, 0.06, "timber")
    for k in range(6):
        b.box((3.4 - 0.5 * (0.15 + k * 0.3) / 2.0 * 2.0 * 0.5, 3.9, 0.15 + k * 0.3), (0.05, 0.44, 0.05), "wood")
    # A pile of planks, a sawhorse with a beam, a tar barrel and tools.
    for k in range(5):
        b.box((-3.2, 2.5, 0.06 + k * 0.1), (0.9 - 0.05 * (k % 2), 3.2, 0.09), "plank" if k % 2 else "plank_b")
    for y in (-1.2, 0.2):
        for s in (-1, 1):
            b.beam((-3.2 + s * 0.35, y, 0.0), (-3.2, y, 0.8), 0.07, 0.07, "timber")
    b.box((-3.2, -0.5, 0.86), (0.2, 2.6, 0.2), "wood_light")
    barrel(b, -3.0, -2.6, mat="tar")
    crate(b, -2.2, 4.8, s=0.6)
    log(b, (-3.6, 5.2, 0.2), (-2.0, 5.8, 0.2), 0.2, seg=7)
    b.cyl((2.6, 5.4, 0.0), (2.6, 5.4, 0.5), 0.4, "iron", r2=0.45, seg=8)
    b.cyl((2.6, 5.4, 0.5), (2.6, 5.4, 0.52), 0.4, "tar", seg=8)
    save(b, name)


def fish_weir(name):
    b = B()
    for s in (-1, 1):   # Two fences of stakes and wattle that close toward the trap.
        pts = [(lerp(s * 4.0, s * 0.55, i / 15), lerp(2.5, -3.2, i / 15)) for i in range(16)]
        for i, (x, y) in enumerate(pts):
            b.cyl((x, y, -1.9), (x + jit(i, 0.05, s), y, 0.5 + jit(i, 0.12, s + 2)), 0.055, "wood", r2=0.035, seg=5)
        for z in (-0.3, -0.05, 0.2, 0.4):
            for i in range(15):
                (xa, ya), (xb, yb) = pts[i], pts[i + 1]
                off = 0.05 if (i + round(z * 10)) % 2 else -0.05
                b.beam((xa, ya, z + off * 0.3), (xb, yb, z - off * 0.3), 0.04, 0.09, "thatch_dark" if i % 2 else "hay")
    # The trap at the point of the V: a cage of stakes with a net lid.
    for x in (-0.6, 0.6):
        for y in (-3.3, -4.5):
            b.cyl((x, y, -1.9), (x, y, 0.3), 0.06, "timber", seg=5)
    for x in (-0.6, 0.6):
        net(b, (x, -3.3, 0.2), (x, -4.5, 0.2), (x, -3.3, -0.9), (x, -4.5, -0.9), n=4)
    net(b, (-0.6, -4.5, 0.2), (0.6, -4.5, 0.2), (-0.6, -4.5, -0.9), (0.6, -4.5, -0.9), n=4)
    for k in range(4):
        b.box((jit(k, 0.3), -3.9 + jit(k, 0.3, 2), -0.42), (0.1, 0.34, 0.07), "fish", rz=k * 0.9)
    # A landing on the shore with baskets and a hand net.
    wood_deck(b, -1.2, 1.2, 3.0, 5.0, brace=False)
    b.cyl((0.6, 4.2, DZ), (0.6, 4.2, DZ + 0.3), 0.26, "thatch_dark", r2=0.33, seg=8)
    for k in range(4):
        b.box((0.6 + jit(k, 0.1), 4.2 + jit(k, 0.1, 2), DZ + 0.32), (0.1, 0.3, 0.06), "fish", rz=k * 0.7)
    b.cyl((-0.7, 3.4, DZ), (-0.4, 4.6, DZ + 1.9), 0.025, "wood_light", seg=5)
    b.cyl((-0.4, 4.6, DZ + 1.9), (-0.38, 4.68, DZ + 2.0), 0.22, "net", seg=7)
    save(b, name)


def breakwater(name, length=12.0):
    b = B()
    for k in range(46):
        t = k / 45
        y = length / 2 - length * t + jit(k, 0.3, 5)
        x = jit(k, 1.35, 1)
        high = 0.75 * (1 - abs(x) / 1.6) + abs(jit(k, 0.25, 3))
        rock(b, x, y, 0.85 + jit(k, 0.25, 2), -2.6, 0.1 + high, seed=k,
             mat=("stone", "stone_dark", "stone_light")[k % 3], sides=6 + k % 2, shrink=0.72)
    for k in range(12):   # A path of flat slabs along the crest.
        y = length / 2 - 0.6 - k * (length - 1.6) / 11
        b.box((jit(k, 0.12), y, 0.92), (1.0, 0.85, 0.12), "stone_light" if k % 2 else "road", rz=jit(k, 0.12, 2))
    ye = -length / 2 + 0.6
    b.cyl((0, ye, 0.6), (0, ye, 1.3), 0.5, "stone", r2=0.4, seg=8)
    b.cyl((0, ye, 1.3), (0, ye, 3.4), 0.1, "timber", r2=0.08, seg=7)
    b.box((0, ye - 0.3, 3.3), (0.07, 0.7, 0.07), "timber")
    lantern(b, 0, ye - 0.55, 3.26, s=0.3)
    for s in (-1, 1):
        b.cyl((s * 0.9, ye + 2.0, 0.6), (s * 0.9, ye + 2.0, 1.25), 0.13, "iron", r2=0.1, seg=7)
        b.cyl((s * 0.9, ye + 2.0, 1.25), (s * 0.9, ye + 2.0, 1.33), 0.18, "iron", seg=7)
    save(b, name)


def washing(name, roof="thatch"):
    b = B()
    wood_deck(b, -2, 2, -1.5, 1.5, brace=False)
    # A low step by the water with slanted washing stones.
    planks_y(b, -2.3, -1.5, 3.6, z=-0.15, step=0.27)
    for x in (-1.7, 1.7):
        pile(b, x, -2.2, -0.2)
    for k in range(3):
        x = -1.2 + k * 1.2
        b.beam((x, -2.1, -0.12), (x, -2.75, -0.5), 0.6, 0.07, "stone_light")
    wall_h = DZ + 2.2
    for x in (-1.85, 1.85):
        for y in (-1.35, 1.35):
            b.box((x, y, DZ + 1.1), (0.14, 0.14, 2.2), "timber")
        b.box((x, 0, wall_h - 0.07), (0.14, 2.9, 0.14), "timber")
    for y in (-1.35, 1.35):
        b.box((0, y, wall_h - 0.07), (3.8, 0.14, 0.14), "timber")
    roof_y(b, 0, 0, 3.9, 2.9, wall_h, 1.1, 0.3, list(ROOFS[roof]), rows=4)
    # Tubs, a basket of linen, a bench and a line of washing.
    for x, y in ((-1.2, 0.3), (0.2, -0.6)):
        b.cyl((x, y, DZ), (x, y, DZ + 0.35), 0.36, "wood", r2=0.42, seg=9)
        b.cyl((x, y, DZ + 0.3), (x, y, DZ + 0.32), 0.38, "water", seg=9)
        b.cyl((x, y, DZ + 0.12), (x, y, DZ + 0.17), 0.415, "iron", seg=9)
    b.cyl((1.3, 0.2, DZ), (1.3, 0.2, DZ + 0.28), 0.26, "thatch_dark", r2=0.32, seg=8)
    b.sphere((1.3, 0.2, DZ + 0.3), 0.25, "cloth_white", seg=6, rings=4, scale=(1, 1, 0.5))
    b.box((0.9, 1.0, DZ + 0.4), (1.4, 0.3, 0.06), "wood")
    for x in (0.35, 1.45):
        b.box((x, 1.0, DZ + 0.2), (0.08, 0.26, 0.4), "timber")
    for x in (-2.6, 2.6):
        b.cyl((x, 2.3, -0.2), (x, 2.3, 1.9), 0.06, "timber", seg=6)
    rope(b, sag((-2.6, 2.3, 1.8), (2.6, 2.3, 1.8), 0.15, 8), r=0.015)
    for k, mat in enumerate(("cloth_white", "cloth_blue", "cloth_white", "cloth_red", "cloth_green", "cloth_white")):
        x = -2.0 + k * 0.8
        b.box((x, 2.3, 1.36 + 0.1 * (k % 2)), (0.55, 0.03, 0.7 - 0.2 * (k % 2)), mat)
    save(b, name)


def toll_gate(name):
    b = B()
    # The booth beside the road (the road runs along X through the gate).
    cy = 3.8
    b.box((0, cy, 0.15), (2.3, 2.3, 0.3), "stone")
    b.box((0, cy, 1.35), (2.0, 2.0, 2.1), "plaster")
    for x in (-1, 1):
        for y in (-1, 1):
            b.box((x, cy + y, 1.35), (0.14, 0.14, 2.1), "timber")
    for y in (-1, 1):
        b.box((0, cy + y, 2.33), (2.0, 0.14, 0.14), "timber")
    b.box((0, cy - 1.03, 1.55), (1.0, 0.06, 0.7), "window")
    b.box((0, cy - 1.2, 1.16), (1.2, 0.4, 0.07), "wood")
    b.box((1.03, cy, 1.15), (0.06, 0.8, 1.6), "door")
    roof_y(b, 0, cy, 2.0, 2.0, 2.4, 1.0, 0.3, ["roof", "roof_dark"], rows=4, gables=(-1, 1), gable_mat="plaster")
    b.box((-0.6, cy - 1.25, 2.1), (0.06, 0.5, 0.06), "iron")
    b.cyl((-0.6, cy - 1.47, 1.75), (-0.6, cy - 1.53, 1.75), 0.2, "gold", seg=8)
    # A strongbox and a lantern.
    b.box((0.75, cy - 1.5, 0.22), (0.6, 0.4, 0.34), "wood_dark")
    b.box((0.75, cy - 1.5, 0.42), (0.64, 0.44, 0.06), "iron")
    b.box((0.75, cy - 1.71, 0.3), (0.1, 0.03, 0.12), "gold")
    # The barrier: a counterweighted pole across a 3 m road.
    px, py, pz = 0.0, 1.6, 1.05
    for dx in (-0.14, 0.14):
        b.box((px + dx, py, 0.6), (0.1, 0.16, 1.2), "timber")
    b.cyl((px - 0.2, py, pz), (px + 0.2, py, pz), 0.04, "iron", seg=6)
    for dx in (-0.14, 0.14):
        b.box((px + dx, -1.7, 0.5), (0.08, 0.12, 1.0), "timber")
    b.box((px, -1.7, 0.1), (0.4, 0.3, 0.2), "stone")
    bar = b.bone("bar")
    for k in range(6):
        ya, yb = py - 0.1 - k * 0.6, py - 0.1 - (k + 1) * 0.6
        bar.box((px, (ya + yb) / 2, pz), (0.09, 0.6, 0.09), "paint_red" if k % 2 else "cloth_white")
    bar.box((px, py + 0.3, pz), (0.09, 0.9, 0.09), "timber")
    bar.box((px, py + 0.7, pz - 0.05), (0.3, 0.34, 0.34), "stone_dark")
    mech = kit.Mech([("bar", (px, py, pz), (px, py, pz + 0.4), None)])
    mech.clip("open", 1.5, lambda t: {"bar": [(kit.X, -78 * smoothstep(t))]}, loops=False)
    mech.clip("close", 1.5, lambda t: {"bar": [(kit.X, -78 * (1 - smoothstep(t)))]}, loops=False)
    save(b, name, mech=mech)


def wreck(name):
    b = B()
    for k in range(7):
        a = k * 0.95
        rock(b, math.cos(a) * 3.2 + jit(k, 0.5), math.sin(a) * 5.0, 0.6 + abs(jit(k, 0.3, 2)), -0.5,
             0.25 + abs(jit(k, 0.3, 3)), seed=k, mat="stone_dark" if k % 2 else "stone")
    h = Hull(11.0, 3.8, 1.0, 1.3, tm=0.5, bow_p=0.7, stern_w=0.5, stern_p=0.6, sheer_bow=0.8, sheer_stern=0.6,
             bow_rise=0.75, stern_rise=0.5, n=12, thick=0.1)
    hb = b.at(dz=0.25).turn("Y", 24).turn("X", -5)
    h.build(hb, stations=(6, 12), strakes=("wood_dark", "wood", "tar"), inner="wood_dark", rail="tar")
    h.ribs(hb, [i / 12 for i in range(1, 6)], mat="wood_dark", w=0.12)
    for i in range(6):
        ta, tb = i / 12, (i + 1) / 12
        hb.beam((0, h.y(ta), h.bot(ta) - 0.02), (0, h.y(tb), h.bot(tb) - 0.02), 0.14, 0.16, "tar")
        if i > 1:
            hb.beam((h.w(ta), h.y(ta), h.top(ta)), (h.w(tb), h.y(tb), h.top(tb)), 0.08, 0.1, "wood_dark")
    hb.beam((0, h.y(0) - 0.02, h.bot(0) - 0.05), (0, h.y(0) - 0.1, h.top(0) + 0.3), 0.14, 0.18, "tar")
    h.deck(hb, 0.6, 0.55, 0.97, mat="plank_b", alt="wood_dark")
    # The stump of the mast, the fallen top with a rag of sail, and a chest in the hold.
    hb.cyl((0, h.y(0.46), 0.0), (0.1, h.y(0.46), 3.2), 0.16, "timber", r2=0.14, seg=7)
    b.cyl((1.2, -1.0, 1.4), (5.4, -3.2, 0.1), 0.13, "timber", r2=0.09, seg=7)
    b.solid([(2.4, -1.6, 1.05), (4.6, -2.75, 0.4), (3.6, -1.0, 0.05)],
            [(2.4, -1.6, 1.09), (4.6, -2.75, 0.44), (3.6, -1.0, 0.09)], "canvas_shade")
    hb.box((0.3, h.y(0.72), 0.82), (0.7, 0.45, 0.4), "wood")
    hb.box((0.3, h.y(0.72), 1.05), (0.74, 0.49, 0.08), "gold")
    for k in range(5):
        hb.box((jit(k, 0.8), h.y(0.6 + k * 0.07), 0.63), (0.5, 0.4, 0.04), "moss", rz=jit(k, 1.0, 2))
    barrel(b, -2.6, -2.2, mat="wood_dark")
    crate(b, -2.9, 0.8, s=0.55, rz=0.5)
    save(b, name)


# --- Boats of the other races --------------------------------------------------------


def swan_boat(name):
    root = B()
    b = root.bone("hull")
    bones = []
    h = Hull(6.0, 1.9, 0.32, 0.5, tm=0.5, bow_p=0.7, stern_p=0.6, sheer_bow=0.3, sheer_stern=0.55, bow_rise=0.8,
             stern_rise=0.7, n=12, thick=0.06)
    h.build(b, strakes=("marble", "marble", "marble_shade"), inner="marble_shade", rail="gold", posts=False)
    h.deck(b, 0.03, 0.05, 0.97, mat="plank", alt="wood_light")
    for t in (0.42, 0.66):
        h.thwart(b, t, drop=0.18)
        z = h.top(t) - 0.14
        b.box((0, h.y(t), z), (1.0, 0.24, 0.07), "cloth_blue")
    # Neck and head of the swan at the bow.
    y0, z0 = h.y(0.0), h.top(0.0)
    pts = [(0, y0 + 0.25, z0 - 0.2), (0, y0 - 0.15, z0 + 0.4), (0, y0 - 0.3, z0 + 1.0), (0, y0 - 0.15, z0 + 1.6),
           (0, y0 + 0.1, z0 + 2.05), (0, y0 - 0.05, z0 + 2.4)]
    for k, (p, q) in enumerate(zip(pts, pts[1:])):
        b.cyl(p, q, 0.2 - 0.02 * k, "marble", r2=0.18 - 0.02 * k, seg=7)
    hy, hz = y0 - 0.2, z0 + 2.45
    b.sphere((0, hy, hz), 0.2, "marble", seg=7, rings=5, scale=(0.9, 1.4, 0.95))
    b.cyl((0, hy - 0.22, hz - 0.02), (0, hy - 0.6, hz - 0.12), 0.09, "gold", r2=0.02, seg=6)
    for e in (-1, 1):
        b.sphere((e * 0.14, hy - 0.1, hz + 0.05), 0.04, "charcoal", seg=5, rings=3)
    # Wings: three feathers rising along each side, on a bone that flutters.
    for s, bone in ((-1, "wing_l"), (1, "wing_r")):
        t0 = 0.45
        bones.append((bone, (s * h.w(t0), h.y(t0), h.top(t0)), (s * h.w(t0), h.y(t0), h.top(t0) + 0.3), "hull"))
        w = b.bone(bone)
        for k in range(3):
            ta, tb = 0.3 + k * 0.14, 0.62 + k * 0.14
            pa = (s * (h.w(ta) + 0.03), h.y(ta), h.top(ta) - 0.05)
            pb = (s * (h.w(min(tb, 0.95)) + 0.2 + k * 0.12), h.y(tb) + 0.2, h.top(0.5) + 0.75 + k * 0.28)
            pc = (s * (h.w(min(ta + 0.2, 0.95)) + 0.03), h.y(ta + 0.2), h.top(ta) - 0.05)
            w.solid([pa, pb, pc], [(px + s * 0.05, py, pz) for px, py, pz in (pa, pb, pc)],
                    "marble" if k % 2 == 0 else "marble_shade")
    # A lantern of crystal on a curved post at the stern.
    y1, z1 = h.y(1.0), h.top(1.0)
    post = [(0, y1 - 0.1, z1 - 0.1), (0, y1 + 0.15, z1 + 0.7), (0, y1 + 0.05, z1 + 1.3), (0, y1 - 0.3, z1 + 1.55)]
    for p, q in zip(post, post[1:]):
        b.cyl(p, q, 0.05, "gold", seg=6)
    lantern(b, 0, y1 - 0.3, z1 + 1.5, glow="crystal_glow", frame="gold", s=0.2)
    wings = lambda t: ({"wing_l": [(kit.Y, 5 * math.sin(4 * math.pi * t))],
                        "wing_r": [(kit.Y, -5 * math.sin(4 * math.pi * t))]}, {})
    finish(root, name, bones, [("bob", 3.0, floating(3.0, 1.2, 0.03), None),
                               ("sail", 4.0, merge(floating(2.0, 1.0, 0.03), wings), 2.0)])


def orc_raft(name):
    root = B()
    b = root.bone("hull")
    bones = []
    n = 9
    for i in range(n):
        x = -2.2 + i * 4.4 / (n - 1)
        ya, yb = -3.4 + abs(x) * 0.35 + jit(i, 0.15), 3.3 + jit(i, 0.2, 2)
        log(b, (x, ya, 0.03), (x, yb, 0.03), 0.25, bark="wood_dark", seg=7)
        b.cyl((x, ya, 0.03), (x, ya - 0.7, 0.1), 0.24, "wood_dark", r2=0.02, seg=7)
        b.cyl((x, ya - 0.45, 0.075), (x, ya - 0.75, 0.105), 0.09, "iron", r2=0.01, seg=6)
    for y in (-2.2, 0.2, 2.6):
        log(b, (-2.6, y, 0.4), (2.6, y, 0.4), 0.16, bark="tar", seg=6)
    # A wall of hide shields at the front.
    for x in (-1.9, 0.0, 1.9):
        b.box((x, -2.3, 1.1), (0.14, 0.14, 1.5), "tar")
    b.box((0, -2.3, 1.7), (4.2, 0.1, 0.12), "tar")
    for k in range(4):
        x = -1.5 + k * 1.0
        b.cyl((x, -2.4, 1.15), (x, -2.48, 1.15), 0.5, "hide", seg=8)
        b.cyl((x, -2.47, 1.15), (x, -2.55, 1.15), 0.13, "iron", seg=6)
        b.cyl((x, -2.5, 1.15), (x, -2.85, 1.15), 0.05, "iron", r2=0.005, seg=5)
    # A crooked mast with a ragged sail, a skull pole and a war drum.
    ym = 0.3
    b.cyl((0, ym, 0.2), (0.15, ym, 5.2), 0.14, "wood_dark", r2=0.09, seg=7)
    b.cyl((-2.1, ym - 0.18, 4.6), (2.1, ym - 0.18, 4.75), 0.07, "tar", seg=6)
    sail(b, bones, "sail", 3.9, ym - 0.22, 4.6, 1.7, ("roof_dark", "cloth_red", "roof_dark", "charcoal"), bulge=0.5,
         strips=7, top_scale=0.95)
    skull(b, 0.15, ym, 5.4, 0.26)
    b.cyl((1.5, 2.2, 0.55), (1.5, 2.2, 1.25), 0.5, "wood_dark", r2=0.55, seg=9)
    b.cyl((1.5, 2.2, 1.25), (1.5, 2.2, 1.29), 0.56, "hide", seg=9)
    b.cyl((-1.6, 2.6, 0.5), (-1.6, 2.6, 2.6), 0.07, "tar", seg=5)
    skull(b, -1.6, 2.6, 2.75, 0.18)
    oars = []
    for s in (-1, 1):
        bone = "oar_%s" % ("l" if s < 0 else "r")
        b.box((s * 2.3, 1.2, 0.8), (0.14, 0.14, 0.7), "tar")
        oar(b, bones, bone, (s * 2.35, 1.2, 1.15), s, out=2.6, inboard=0.8, drop=1.2, blade="wood_dark")
        oars.append((bone, s))
    finish(root, name, bones, [("bob", 3.0, floating(2.5, 1.5, 0.04), None),
                               ("sail", 4.0, merge(floating(3.0, 1.5, 0.05), flutter("sail", amp=3.0)), 1.8),
                               ("row", 2.4, merge(floating(1.5, 1.0, 0.03), rowing(oars, sweep=20, lift=6)), 1.4)])


def dwarf_paddle(name):
    root = B()
    b = root.bone("hull")
    bones = []
    h = Hull(9.0, 3.2, 0.6, 0.8, tm=0.45, bow_p=0.5, stern_w=0.7, stern_p=0.5, sheer_bow=0.35, sheer_stern=0.15,
             bow_rise=0.6, stern_rise=0.35, n=12, flat=0.8, thick=0.1)
    h.build(b, strakes=("iron", "wood_dark", "wood_dark"), inner="wood", rail="iron")
    dz = 0.3
    h.deck(b, dz, 0.06, 0.97, mat="plank", alt="plank_b", steps=18)
    # An iron ram at the waterline and a gilded anvil for a figurehead.
    b.cyl((0, h.y(0) + 0.5, 0.05), (0, h.y(0) - 1.1, -0.05), 0.3, "iron", r2=0.03, seg=6)
    b.box((0, h.y(0.04), h.top(0) + 0.25), (0.5, 0.3, 0.14), "gold")
    b.box((0, h.y(0.04), h.top(0) + 0.1), (0.24, 0.2, 0.2), "gold")
    # The engine house: a treadwheel inside turns the two paddle wheels.
    yw = h.y(0.55)
    b.box((0, yw, dz + 0.9), (2.0, 2.6, 1.8), "wood")
    for x in (-1, 1):
        for y in (-1.3, 1.3):
            b.box((x, yw + y, dz + 0.9), (0.16, 0.16, 1.8), "iron")
        b.cyl((x * 1.01, yw - 0.6, dz + 1.2), (x * 1.06, yw - 0.6, dz + 1.2), 0.25, "gold", seg=8)
        b.cyl((x * 1.03, yw - 0.6, dz + 1.2), (x * 1.08, yw - 0.6, dz + 1.2), 0.17, "window", seg=8)
    b.box((0, yw, dz + 1.87), (2.3, 2.9, 0.14), "iron")
    b.box((0, yw - 1.32, dz + 0.8), (0.8, 0.06, 1.5), "door")
    b.cyl((0.5, yw + 0.8, dz + 1.9), (0.5, yw + 0.8, dz + 3.1), 0.18, "iron", seg=7)
    b.cyl((0.5, yw + 0.8, dz + 3.1), (0.5, yw + 0.8, dz + 3.25), 0.25, "iron", seg=7)
    az = 0.75
    r = 1.35
    w = b.bone("wheels")
    bones.append(("wheels", (0, yw, az), (0, yw, az + 0.4), "hull"))
    w.cyl((-2.55, yw, az), (2.55, yw, az), 0.08, "iron", seg=6)
    n = 8
    for s in (-1, 1):
        xc = s * (h.w(0.55) + 0.55)
        for sx in (-0.3, 0.3):
            for i in range(n):
                a0, a1 = 2 * math.pi * i / n, 2 * math.pi * (i + 1) / n
                w.beam((xc + sx, yw + r * 0.8 * math.cos(a0), az + r * 0.8 * math.sin(a0)),
                       (xc + sx, yw + r * 0.8 * math.cos(a1), az + r * 0.8 * math.sin(a1)), 0.06, 0.1, "iron")
        for i in range(n):
            a0 = 2 * math.pi * i / n
            w.beam((xc, yw + 0.15 * math.cos(a0), az + 0.15 * math.sin(a0)),
                   (xc, yw + r * math.cos(a0), az + r * math.sin(a0)), 0.66, 0.06, "wood" if i % 2 else "wood_light")
        w.cyl((xc - 0.34, yw, az), (xc + 0.34, yw, az), 0.2, "iron", seg=8)
        # A guard over the top half of the wheel.
        for i in range(5):
            a0, a1 = math.pi * i / 5, math.pi * (i + 1) / 5
            b.beam((xc + 0.42, yw + (r + 0.12) * math.cos(a0), az + (r + 0.12) * math.sin(a0)),
                   (xc + 0.42, yw + (r + 0.12) * math.cos(a1), az + (r + 0.12) * math.sin(a1)), 0.08, 0.16,
                   "paint_red" if i % 2 else "gold")
        b.box((xc + 0.42, yw, az), (0.08, 2 * r + 0.24, 0.12), "iron")
    # Ore crates at the bow, a steering wheel aft and lanterns.
    for i, (x, y) in enumerate(((-0.6, h.y(0.2)), (0.3, h.y(0.22)), (-0.2, h.y(0.3)))):
        crate(b, x, y, z=dz, s=0.62, mat="wood_dark", edge="iron")
        b.box((x, y, dz + 0.66), (0.5, 0.5, 0.1), "stone_dark" if i % 2 else "iron")
    b.box((0, h.y(0.9), dz + 0.5), (0.14, 0.14, 1.0), "iron")
    b.cyl((0, h.y(0.9) - 0.1, dz + 1.0), (0, h.y(0.9) - 0.16, dz + 1.0), 0.32, "wood", seg=8)
    for s in (-1, 1):
        b.box((s * (h.w(0.92) - 0.1), h.y(0.95), dz + 0.7), (0.06, 0.06, 1.4), "iron")
        lantern(b, s * (h.w(0.92) - 0.1), h.y(0.95), dz + 1.7)
    pennant(b, bones, yw + 0.8, dz + 3.2, mat="gold", size=0.9)
    turn = lambda t: ({"wheels": [(kit.X, 360 * t)]}, {})
    finish(root, name, bones, [("bob", 4.0, merge(floating(1.5, 0.8, 0.03), waving(3, 10)), None),
                               ("paddle", 2.0, merge(floating(1.0, 0.6, 0.02), turn, waving(2, 10)), 2.0)])


model("bridge_fortified", stone_bridge, arches=2, span=6.0, pier_w=2.0, abut=2.5, hump=1.3, extra=gate_tower)
model("bridge_dwarven", stone_bridge, span=7.0, abut=2.5, hump=1.3, n=3, ring=0.42, pal=DWARF, extra=dwarf_extra)
model("bridge_orc", plank_trestle, pal=TARRED, rails=False, extra=orc_extra)
model("bridge_clapper", clapper)
model("bridge_moon", moon)
model("bridge_moon_green", moon, paint="paint_green")
model("bridge_inhabited", stone_bridge, arches=3, span=4.5, abut=1.75, width=6.0, hump=1.0, extra=shops)
model("bridge_inhabited_brick", stone_bridge, arches=3, span=4.5, abut=1.75, width=6.0, hump=1.0, pal=BRICK,
      extra=shops)
model("dock_shipyard", shipyard)
model("dock_fish_weir", fish_weir)
model("dock_breakwater", breakwater)
model("dock_washing", washing)
model("dock_washing_tile", washing, roof="tile")
model("bridge_toll_gate", toll_gate)
model("boat_wreck", wreck)
model("boat_merchant_furled", merchant, furled=True)
model("boat_war_cog", merchant, sail_mats=("roof_dark", "charcoal"), trim="charcoal", flag="cloth_red", war=True)
model("boat_swan", swan_boat)
model("boat_orc_raft", orc_raft)
model("boat_dwarf_paddle", dwarf_paddle)
