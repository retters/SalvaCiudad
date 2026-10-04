"""A ninth batch of the `bridges` family: a war galley, a market boat and
the remains of an old pier."""

import math

from parts import B, barrel, crate, jit, lantern, lerp, planks_y, rope, sack, save
from boats import (Hull, finish, floating, flutter, furled_sail, mast, merge, oar, pennant, rowing, rudder, sail,
                   waving)
from docks import DZ, fish, pile

MODELS = {}


def model(name, fn, **kw):
    MODELS[name] = lambda: fn(name, **kw)


def galley(name, sail_mats=("cloth_blue", "canvas"), trim="paint_blue", furled=False):
    """A long war galley with a ram, a fighting deck aft and twelve oars a side."""
    root = B()
    b = root.bone("hull")
    bones = []
    h = Hull(22.0, 4.4, 0.8, 1.2, tm=0.52, bow_p=0.7, stern_w=0.35, stern_p=0.6, sheer_bow=0.7, sheer_stern=1.2,
             bow_rise=0.7, stern_rise=0.6, n=18, flat=0.55, thick=0.1)
    h.build(b, strakes=(trim, "wood", "wood_dark"), inner="wood")
    dz = 0.7
    h.deck(b, dz, 0.05, 0.98, mat="plank", alt="plank_b", steps=26)
    b.box((0, 0, dz + 0.22), (0.9, 13.0, 0.08), "plank_b")          # The gangway between the rowers.
    for s in (-1, 1):
        b.box((s * 0.45, 0, dz + 0.1), (0.08, 13.0, 0.26), "timber")
    # The ram at the waterline, an eye on each bow and a raised fighting deck aft.
    y0 = h.y(0.0)
    b.cyl((0, y0 + 1.0, 0.1), (0, y0 - 2.0, 0.0), 0.34, "wood_dark", r2=0.12, seg=7)
    b.cyl((0, y0 - 1.2, 0.05), (0, y0 - 2.5, -0.02), 0.2, "iron", r2=0.02, seg=6)
    for s in (-1, 1):
        t = 0.07
        b.cyl((s * (h.w(t) + 0.03), h.y(t), h.top(t) - 0.45), (s * (h.w(t) + 0.08), h.y(t), h.top(t) - 0.45), 0.24,
              "cloth_white", seg=8)
        ey, ez = h.y(t) - 0.04, h.top(t) - 0.45
        b.cyl((s * (h.w(t) + 0.07), ey, ez), (s * (h.w(t) + 0.11), ey, ez), 0.11, "charcoal", seg=6)
    ya, yb = h.y(0.8), h.y(1.0) + 0.2
    zc = h.top(0.95) + 0.1
    wc = h.w(0.85) + 0.1
    b.box((0, (ya + yb) / 2, zc), (2 * wc, yb - ya, 0.12), "plank_b")
    b.box((0, ya + 0.06, (dz + zc) / 2), (2 * h.half_at(0.8, dz + 0.3) + 0.1, 0.12, zc - dz), "wood")
    for s in (-1, 1):
        for k in range(4):
            b.box((s * (wc - 0.07), lerp(ya + 0.2, yb - 0.2, k / 3), zc + 0.5), (0.16, 0.5, 0.9),
                  trim if k % 2 else "wood")
        b.beam((s * 0.9, ya - 1.1, dz), (s * 0.9, ya, zc), 0.45, 0.06, "wood")
    b.box((0, yb - 0.05, zc + 0.5), (2 * wc, 0.14, 0.9), "wood")
    lantern(b, 0, yb + 0.05, zc + 1.9)
    b.box((0, yb + 0.05, zc + 1.4), (0.06, 0.06, 0.6), "iron")
    rudder(b, h, size=1.0)
    # Oars: twelve a side, each on its bone; shields between them.
    oars = []
    count = 12
    for i in range(count):
        t = 0.2 + i * 0.52 / (count - 1)
        for s in (-1, 1):
            bone = "oar_%s%d" % ("l" if s < 0 else "r", i)
            oar(b, bones, bone, (s * h.w(t), h.y(t), h.top(t) - 0.15), s, out=3.2, inboard=0.9, drop=1.1)
            oars.append((bone, s))
            if i % 2 == 0:
                ts = t + 0.02
                sy, sz = h.y(ts), h.top(ts) + 0.1
                b.cyl((s * (h.w(ts) + 0.05), sy, sz), (s * (h.w(ts) + 0.11), sy, sz), 0.36, sail_mats[(i // 2) % 2],
                      seg=9)
        if i % 3 == 0:
            b.box((0, h.y(t), dz + 0.5), (2 * h.half_at(t, dz + 0.5), 0.14, 0.1), "timber")
    ym = h.y(0.42)
    mast(b, ym, dz, 9.0, r=0.16, yard=7.6, yard_z=dz + 8.0)
    if furled:
        furled_sail(b, 7.0, ym - 0.24, dz + 7.85, sail_mats[0])
    else:
        sail(b, bones, "sail", 7.0, ym - 0.24, dz + 7.9, dz + 2.6, sail_mats, bulge=1.1, strips=10)
    for s in (-1, 1):
        for dy in (-0.8, 0.8):
            rope(b, [(0, ym, dz + 8.4), (s * h.w(0.45), ym + dy, h.top(0.45))], r=0.022)
    rope(b, [(0, ym, dz + 8.8), (0, y0 - 0.2, h.top(0) + 0.2)], r=0.022)
    rope(b, [(0, ym, dz + 8.8), (0, yb, zc + 1.0)], r=0.022)
    pennant(b, bones, ym, dz + 9.1, mat=sail_mats[0], size=1.6)
    finish(root, name, bones, [("bob", 4.0, merge(floating(1.8, 0.8, 0.04), waving(3, 12)), None),
                               ("sail", 4.0, merge(floating(2.5, 1.0, 0.06), flutter("sail", amp=2.0), waving()), 3.0),
                               ("row", 2.4, merge(floating(1.0, 0.6, 0.03), rowing(oars, sweep=18, lift=5),
                                                  waving(2, 10)), 2.8)])


def market_boat(name, cloths=("cloth_red", "cloth_blue")):
    """A merchant's barge that sells from the water: two stalls under awnings."""
    root = B()
    b = root.bone("hull")
    h = Hull(10.0, 3.4, 0.45, 0.6, tm=0.5, bow_p=0.32, stern_w=0.78, stern_p=0.4, sheer_bow=0.25, sheer_stern=0.12,
             bow_rise=0.6, stern_rise=0.3, n=12, flat=0.88, thick=0.09)
    h.build(b, strakes=("paint_yellow", "wood", "tar"), inner="wood")
    dz = 0.25
    h.deck(b, dz, 0.05, 0.97, mat="plank", alt="plank_b", steps=20)
    for k, yc in enumerate((h.y(0.34), h.y(0.66))):
        for sx in (-1, 1):
            for sy in (-1, 1):
                b.box((sx * 1.25, yc + sy * 0.95, dz + 1.1), (0.09, 0.09, 2.2), "timber")
        ring = [(-1.5, yc - 1.1, dz + 2.3), (1.5, yc - 1.1, dz + 2.3), (1.7, yc + 1.1, dz + 2.0),
                (-1.7, yc + 1.1, dz + 2.0)]
        b.solid(ring, [(x, y, z + 0.05) for x, y, z in ring], cloths[k % 2])
        for s in (-1, 1):   # A counter along each side, facing the people on the quay.
            b.box((s * 1.0, yc, dz + 0.8), (0.5, 1.8, 0.08), "wood")
            b.box((s * 0.8, yc, dz + 0.4), (0.06, 1.7, 0.8), "wood_light")
            for j in range(3):
                item = (yc - 0.6 + j * 0.6)
                if (j + k) % 3 == 0:
                    b.cyl((s * 1.0, item, dz + 0.84), (s * 1.0, item, dz + 1.1), 0.16, "clay", r2=0.1, seg=7)
                elif (j + k) % 3 == 1:
                    b.box((s * 1.0, item, dz + 0.94), (0.34, 0.4, 0.2), cloths[(j + k) % 2])
                else:
                    b.sphere((s * 1.0, item, dz + 0.95), 0.14, "bread", seg=6, rings=4, scale=(1, 1.3, 0.7))
        for j in range(3):
            fish(b, -0.5 + j * 0.5, yc + 0.9, dz + 2.0, s=0.3, mat=("fish", "hide", "sack")[j])
        lantern(b, 0, yc - 1.05, dz + 2.25)
    crate(b, -0.5, h.y(0.14), z=dz, s=0.6)
    barrel(b, 0.4, h.y(0.15), z=dz)
    sack(b, 0.0, h.y(0.5), z=dz)
    sack(b, 0.3, h.y(0.52), z=dz)
    b.box((0, h.y(0.9), dz + 0.3), (0.9, 0.5, 0.6), "wood_dark")        # The merchant's strongbox.
    b.box((0, h.y(0.9), dz + 0.62), (0.94, 0.54, 0.06), "gold")
    b.cyl((0.2, h.y(0.84), dz + 1.2), (0, h.y(1.0) + 2.4, -0.3), 0.045, "wood", seg=6)
    b.beam((0, h.y(1.0) + 1.8, 0.0), (0, h.y(1.0) + 2.5, -0.36), 0.04, 0.3, "wood_light")
    finish(root, name, [], [("bob", 4.0, floating(1.6, 0.8, 0.03), None)])


def ruined_pier(name):
    """What is left of an old pier: leaning piles, a few boards, moss and a sunken boat."""
    b = B()
    spots = [(-0.8, 2.6, 0.2), (0.8, 2.6, 0.25), (-0.8, 0.8, 0.1), (0.8, 0.9, -0.5), (-0.9, -1.0, 0.3),
             (0.8, -1.1, 0.0), (-0.8, -2.9, -0.6), (0.9, -3.0, 0.35)]
    for k, (x, y, top) in enumerate(spots):
        head = (x + jit(k, 0.25, 2), y + jit(k, 0.2, 3), top)
        b.cyl((x + jit(k, 0.2), y, -3.0), head, 0.12, "wood_dark", r2=0.09, seg=6)
        if k % 3 == 0:
            b.box((x + jit(k, 0.25, 2), y + jit(k, 0.2, 3), top + 0.02), (0.22, 0.22, 0.06), "moss")
    planks_y(b, 1.6, 3.4, 2.0, z=DZ - 0.02, mats=("plank_b", "wood_dark"), step=0.32, ragged=0.15)
    for k in range(5):   # Boards that still hang on, askew, and some fallen in the water.
        y = 1.2 - k * 0.9
        if k % 2 == 0:
            b.box((jit(k, 0.3), y, DZ - 0.1 - 0.04 * k), (1.7 + jit(k, 0.3, 2), 0.3, 0.06), "wood_dark",
                  rz=jit(k, 0.25, 4))
        else:
            b.beam((-0.9, y, DZ - 0.3), (0.6, y + 0.3, -0.9), 0.3, 0.06, "tar")
    b.box((-0.8, 1.7, DZ - 0.3), (0.14, 3.6, 0.14), "wood_dark")
    b.beam((0.8, 2.6, DZ - 0.3), (0.85, 0.2, -0.6), 0.14, 0.14, "wood_dark")
    for k in range(4):
        b.box((jit(k, 0.8, 5), 2.0 + jit(k, 0.9, 6), DZ + 0.0), (0.4, 0.3, 0.03), "moss", rz=jit(k, 1.0, 7))
    pile(b, 1.15, 3.2, DZ + 0.7, r=0.12, mat="wood_dark")
    for k in range(2):
        b.cyl((1.15, 3.2, DZ + 0.3 + k * 0.07), (1.15, 3.2, DZ + 0.36 + k * 0.07), 0.16, "rope", seg=7)
    # A boat gone down beside it: only the bow and one side show.
    h = Hull(3.8, 1.4, 0.28, 0.38, stern_w=0.55, sheer_bow=0.2, sheer_stern=0.08, stern_rise=0.3, n=9, thick=0.06)
    hb = b.at(dx=2.2, dy=-0.6, dz=-0.75).turn("X", 12).turn("Y", 20)
    h.build(hb, strakes=("wood_dark", "tar", "tar"), inner="wood_dark", rail="tar")
    for t in (0.36, 0.64):
        h.thwart(hb, t, mat="wood_dark")
    for k in range(6):   # Reeds have taken the shore end.
        a = k * 1.1
        rx, ry = math.cos(a) * 1.6, 3.6 + math.sin(a) * 0.5
        b.cyl((rx, ry, -0.3), (rx + jit(k, 0.1), ry, 1.0 + jit(k, 0.3, 2)), 0.03, "leaves", r2=0.01, seg=4)
    save(b, name)


model("boat_galley", galley)
model("boat_galley_red", galley, sail_mats=("cloth_red", "canvas"), trim="paint_red")
model("boat_galley_furled", galley, furled=True)
model("boat_market", market_boat)
model("dock_ruined_pier", ruined_pier)
