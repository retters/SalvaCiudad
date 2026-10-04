"""Towers that plug into the walls: 4 x 4 m, centered on a wall node, with
doors to the wall walk on their sides at the height of the wall's walkway.
Square and round, masonry (stone, brick, iron-bound) and wood, open or
roofed; a corner bastion, a keep and a ballista tower."""

import math

import _kit as kit
from registry import reg
from wallkit import SIDE_ROT, add_flicker, brazier, cone_roof, flag, flame_bones, ladder, pyramid_roof, rng
from walltypes import WALLS

FLICKER = {"flicker": "La llama del brasero se mueve"}


def ring_parapet(p, W, hs, H, phase=0.0):
    """Crenellated parapets around a square platform of half-size hs."""
    base = H - W.h
    for d in "ESWN":
        q = p.at(rot=SIDE_ROT[d]).at(y=-(hs + 0.05 - W.half))
        W.parapet(q, -hs - 0.15, hs + 0.15, -1, base, phase)


def slit_on(p, W, d, off, z, hs, tall=1.1):
    q = p.at(rot=SIDE_ROT[d])
    q.box((off, -hs - 0.01, z), (0.42, 0.1, tall + 0.2), W.trim)
    q.box((off, -hs - 0.04, z), (0.1, 0.08, tall), "dark")
    q.box((off, -hs - 0.04, z + 0.1), (0.28, 0.08, 0.1), "dark")


def door_on(p, W, d, z, hs, w=0.95, h=1.8, wood=True):
    q = p.at(rot=SIDE_ROT[d])
    q.box((0, -hs - 0.01, z + (h + 0.12) / 2), (w + 0.3, 0.12, h + 0.12), W.trim)
    q.box((0, -hs - 0.05, z + h / 2), (w, 0.08, h), "door" if wood else "dark")
    if wood:
        for zz in (z + h * 0.25, z + h * 0.75):
            q.box((0, -hs - 0.08, zz), (w, 0.05, 0.08), "iron")


def square_shell(p, W, size, H, walk_sides="EW"):
    hs = size / 2
    p.taper((0, 0), (size + 0.6, size + 0.6), (size + 0.08, size + 0.08), 0.0, 0.9, W.dark)
    W.block(p, -hs, hs, -hs, hs, 0.0, H, 0.0, proud_x=True)
    r = rng("quoin", W.key, size)
    z = 1.0
    i = 0
    while z < H - 0.6:   # Quoins at the four corners.
        for sx in (-1, 1):
            for sy in (-1, 1):
                long_x = (i + (sx > 0) + (sy > 0)) % 2
                p.box((sx * (hs - 0.2 + 0.03), sy * (hs - 0.2 + 0.03), z + 0.2),
                      (0.62 if long_x else 0.4, 0.4 if long_x else 0.62, 0.4), W.trim)
        z += 0.62
        i += 1
    p.box((0, 0, H - 0.13), (size + 0.5, size + 0.5, 0.26), W.dark)
    for d in "ESWN":   # Corbels under the platform.
        q = p.at(rot=SIDE_ROT[d])
        n = int(size / 0.6)
        for k in range(n):
            q.box((-hs + (k + 0.5) * size / n, -hs - 0.1, H - 0.4), (0.2, 0.3, 0.3), W.trim)
    p.box((0, 0, H + 0.01), (size, size, 0.05), W.walkmat)
    ring_parapet(p, W, hs + 0.1, H)
    for d in "SEW":
        slit_on(p, W, d, 0.0 if d == "S" else 0.9, H - 1.7, hs)
    slit_on(p, W, "S", 0.0, 2.2, hs)
    door_on(p, W, "N", 0.0, hs)
    for d in walk_sides:
        door_on(p, W, d, W.h, hs, wood=False)
    return hs


def roof_on_posts(p, hs, H, rise=1.7, mats=("roof", "roof_dark"), post=2.1):
    for sx in (-1, 1):
        for sy in (-1, 1):
            p.box((sx * (hs - 0.1), sy * (hs - 0.1), H + post / 2), (0.16, 0.16, post), "timber")
            p.beam((sx * (hs - 0.1), sy * (hs - 0.1), H + post - 0.5), (sx * (hs - 0.6), sy * (hs - 0.1), H + post),
                   0.09, "timber")
    for s in (-1, 1):
        p.box((0, s * (hs - 0.1), H + post), (2 * hs + 0.1, 0.14, 0.14), "timber")
        p.box((s * (hs - 0.1), 0, H + post), (0.14, 2 * hs + 0.1, 0.14), "timber")
    pyramid_roof(p, (0, 0), 2 * hs, 2 * hs, H + post + 0.05, rise, mats, over=0.45)


def top_fire(p, H, x=0.0, y=0.0):
    p.box((x, y, H + 0.2), (0.5, 0.5, 0.35), "stone_dark")
    return brazier(p, x, y, H + 0.37, 0.5)


def tower_square(p, W, roof=False, size=3.6, walk_sides="EW"):
    H = W.h + 3.0
    hs = square_shell(p, W, size, H, walk_sides)
    if roof:
        roof_on_posts(p, hs, H, mats=W.roof)
        return None
    flag(p, hs - 0.5, hs - 0.5, H, 2.4)
    pt = top_fire(p, H)
    if p.static:
        return None
    names, bones = flame_bones([pt])
    return add_flicker(kit.Mech(bones), names)


def tower_round(p, W, roof=False, r=1.85, walk_sides="EW"):
    H = W.h + 3.0
    seg = 14
    p.cyl((0, 0, 0), (0, 0, 0.9), r + 0.32, r + 0.05, W.dark, seg=seg)
    p.cyl((0, 0, 0), (0, 0, H), r, r, W.mat, seg=seg)
    rr = rng("round", W.key)
    z, row = 0.9, 0
    while z < H - 0.3:
        p.cyl((0, 0, z), (0, 0, z + 0.05), r + 0.02, r + 0.02, W.dark, seg=seg)
        zt = min(z + W.course, H - 0.25)
        if zt - z > 0.2 and (W.course > 0.4 or row % 2 == 0):
            for j in range(3):
                a = rr.uniform(0, 2 * math.pi)
                p.box(((r - 0.05) * math.cos(a), (r - 0.05) * math.sin(a), (z + zt) / 2 + 0.02),
                      (0.2, rr.uniform(0.4, 0.6), zt - z - 0.1), W.light if (row + j) % 3 else W.dark,
                      rz=math.degrees(a))
        z += W.course
        row += 1
    for zb in W.bands:
        p.cyl((0, 0, zb - 0.07), (0, 0, zb + 0.07), r + 0.04, r + 0.04, W.band_mat, seg=seg)
    p.cyl((0, 0, H - 0.5), (0, 0, H - 0.24), r + 0.02, r + 0.3, W.dark, seg=seg)
    p.cyl((0, 0, H - 0.24), (0, 0, H), r + 0.3, r + 0.3, W.dark, seg=seg)
    p.cyl((0, 0, H), (0, 0, H + 0.04), r + 0.02, r + 0.02, W.walkmat, seg=seg)
    n = 12
    rp = r + 0.14
    wseg = 2 * (rp + 0.15) * math.tan(math.pi / n) + 0.02
    for k in range(n):   # The parapet: a ring of flat panels, a merlon on every other one.
        a = 2 * math.pi * (k + 0.5) / n
        q = p.at(rot=math.degrees(a) + 90.0)
        q.box((0, -rp, H + 0.3), (wseg, 0.3, 0.6), W.mat)
        if k % 2 == 0:
            q.box((0, -rp, H + 0.85), (wseg * 0.8, 0.3, 0.5), W.mat)
            q.box((0, -rp, H + 1.13), (wseg * 0.8 + 0.06, 0.38, 0.07), W.trim)
            if W.spikes:
                q.cyl((0, -rp, H + 1.15), (0, -rp, H + 1.5), 0.04, 0.0, "iron_dark", seg=4)
    for a_deg, z in ((0, H - 1.7), (0, 2.2), (120, H - 1.9), (240, H - 1.9), (60, 3.4), (300, 3.4)):
        q = p.at(rot=a_deg)   # Front is -Y.
        q.box((0, -r + 0.02, z), (0.42, 0.14, 1.3), W.trim)
        q.box((0, -r - 0.02, z), (0.1, 0.1, 1.05), "dark")
    q = p.at(rot=180)
    q.box((0, -r + 0.02, 0.96), (1.25, 0.16, 1.92), W.trim)
    q.box((0, -r - 0.03, 0.9), (0.95, 0.1, 1.8), "door")
    for d in walk_sides:   # Doors to the wall walk.
        q = p.at(rot=SIDE_ROT[d])
        q.box((0, -r + 0.03, W.h + 0.96), (1.25, 0.16, 1.92), W.trim)
        q.box((0, -r - 0.02, W.h + 0.9), (0.9, 0.1, 1.8), "dark")
    if roof:
        for k in range(6):
            a = 2 * math.pi * k / 6
            p.box(((r - 0.1) * math.cos(a), (r - 0.1) * math.sin(a), H + 1.05), (0.14, 0.14, 2.1), "timber",
                  rz=math.degrees(a))
        p.cyl((0, 0, H + 2.05), (0, 0, H + 2.2), r + 0.2, r + 0.2, "timber", seg=seg)
        cone_roof(p, (0, 0), r + 0.6, H + 2.2, 2.4, mats=W.roof, seg=seg)
        return None
    flag(p, 0.9, 0.9, H, 2.4)
    pt = top_fire(p, H)
    if p.static:
        return None
    names, bones = flame_bones([pt])
    return add_flicker(kit.Mech(bones), names)


# --- Wood ------------------------------------------------------------------------------------


def tower_wood_square(p, roof=False):
    """A timber tower: splayed log posts, a plank room below, a platform
    with a plank parapet at 5 m."""
    H = 5.0
    for sx in (-1, 1):
        for sy in (-1, 1):
            p.cyl((sx * 1.7, sy * 1.7, 0), (sx * 1.45, sy * 1.45, H), 0.2, 0.16, "log", seg=7)
            p.cyl((sx * 1.7, sy * 1.7, 0), (sx * 1.7, sy * 1.7, 0.25), 0.3, 0.26, "stone_dark", seg=7)
    for d in "ESWN":
        q = p.at(rot=SIDE_ROT[d])
        # Plank cladding of the room, cross braces above it.
        for i in range(9):
            wd = 3.2 - 0.03 * i
            q.box((0, -1.6 + 0.012 * i, 0.3 + (i + 0.5) * 0.28), (wd, 0.07, 0.26), "wood" if i % 2 else "wood_light")
        q.box((0, -1.56, 2.9), (3.25, 0.12, 0.14), "timber")
        q.beam((-1.5, -1.52, 3.0), (1.45, -1.48, 4.8), 0.1, "timber")
        q.beam((1.5, -1.52, 3.0), (-1.45, -1.48, 4.8), 0.1, "timber")
        q.box((0, -1.5, H - 0.12), (3.3, 0.14, 0.16), "timber")
        if d != "N":
            q.box((0, -1.64, 1.9), (0.5, 0.06, 0.6), "timber")
            q.box((0, -1.67, 1.9), (0.3, 0.05, 0.42), "dark")
    p.at(rot=180).box((0, -1.66, 1.1), (1.0, 0.07, 1.7), "door")
    p.at(rot=180).box((0, -1.64, 1.15), (1.2, 0.06, 1.9), "timber")
    for i in range(10):   # The platform's deck, overhanging on joists.
        p.box((-1.8 + (i + 0.5) * 0.36, 0, H + 0.04), (0.34, 3.6, 0.08), "wood_light" if i % 2 else "wood")
    for y in (-1.2, 0.0, 1.2):
        p.box((0, y, H - 0.07), (4.0, 0.14, 0.14), "timber")
    for d in "ESWN":
        q = p.at(rot=SIDE_ROT[d])
        q.box((0, -1.76, H + 0.4), (3.6, 0.08, 0.3), "wood")
        q.box((0, -1.76, H + 0.72), (3.6, 0.07, 0.3), "wood_light")
        for k in range(4):
            q.box((-1.35 + k * 0.9, -1.76, H + 1.08), (0.5, 0.08, 0.42), "wood")
        for x in (-1.76, 1.76):
            q.box((x, -1.76, H + 0.7), (0.14, 0.14, 1.4), "timber")
    ladder(p, (0.7, 2.5, 0.0), (0.7, 1.84, H + 0.3))
    if roof:
        roof_on_posts(p, 1.8, H + 0.1, rise=1.6, mats=("thatch", "thatch_dark"), post=2.2)
        return None
    pt = brazier(p, 1.3, 1.3, H + 0.08, 1.2)
    flag(p, -1.4, 1.4, H + 0.08, 2.6, "cloth_blue")
    if p.static:
        return None
    names, bones = flame_bones([pt])
    return add_flicker(kit.Mech(bones), names)


def tower_wood_round(p, roof=False, log="log", tip="log_end", roof_mats=("thatch", "thatch_dark"), orc=False):
    """A drum of upright logs, bound with rope, with a platform inside.
    With `orc`: iron bands, spikes all around and a stripe of war paint."""
    H = 4.6
    n, r = 16, 1.75
    for k in range(n):
        a = 2 * math.pi * k / n
        x, y = r * math.cos(a), r * math.sin(a)
        hh = H + 1.0 + (0.5 if k % 2 == 0 else 0.0)
        z0 = 2.0 if k == 4 else 0.0   # The log over the doorway, on +Y.
        p.cyl((x, y, z0), (x, y, hh), 0.36, 0.33, log, seg=7)
        p.cyl((x, y, hh), (x, y, hh + 0.45), 0.33, 0.0, tip, seg=7)
        if orc:
            p.cyl(((r + 0.3) * math.cos(a), (r + 0.3) * math.sin(a), H - 0.4),
                  ((r + 0.95) * math.cos(a), (r + 0.95) * math.sin(a), H - 0.1), 0.07, 0.0, "iron_dark", seg=5)
    for z in (1.0, 3.2, H + 0.6):
        p.cyl((0, 0, z - 0.06), (0, 0, z + 0.06), r + 0.34, r + 0.34,
              "iron_dark" if orc else "rope" if z > 1.5 else "iron", seg=n)
    if orc:
        p.cyl((0, 0, 2.3), (0, 0, 2.6), r + 0.33, r + 0.33, "blood", seg=n)
    p.cyl((0, 0, 0.0), (0, 0, H), r - 0.1, r - 0.1, "dark", seg=n)
    p.cyl((0, 0, H), (0, 0, H + 0.08), r - 0.05, r - 0.05, "wood_light", seg=n)
    p.at(rot=180).box((0, -r - 0.2, 1.0), (0.85, 0.3, 2.0), "timber")
    p.at(rot=180).box((0, -r - 0.33, 0.95), (0.65, 0.1, 1.8), "door")
    if roof:
        p.cyl((0, 0, H + 0.08), (0, 0, H + 2.4), 0.12, 0.1, "timber", seg=6)
        for k in range(8):
            a = 2 * math.pi * k / 8
            p.beam((0, 0, H + 2.4), ((r + 0.5) * math.cos(a), (r + 0.5) * math.sin(a), H + 1.75), 0.08, "timber")
        cone_roof(p, (0, 0), r + 0.75, H + 1.75, 2.2, mats=roof_mats, seg=n)
        return None
    pt = brazier(p, 0.0, 0.0, H + 0.08, 1.5)
    if p.static:
        return None
    names, bones = flame_bones([pt])
    return add_flicker(kit.Mech(bones), names)


# --- Bastion, keep, ballista -----------------------------------------------------------------


def tower_bastion(p, W):
    """A low, wide corner bastion: a battered octagon 6 m across, level
    with the wall walk, with wide embrasures."""
    H = W.h + 0.4
    seg, r = 8, 3.0
    q0 = p.at(rot=22.5)
    q0.cyl((0, 0, 0), (0, 0, 1.6), r + 0.25, r - 0.2, W.dark, seg=seg)
    q0.cyl((0, 0, 1.6), (0, 0, H), r - 0.2, r - 0.35, W.mat, seg=seg)
    z = 2.2
    while z < H - 0.3:
        rz = r - 0.2 - 0.15 * (z - 1.6) / (H - 1.6)
        q0.cyl((0, 0, z), (0, 0, z + 0.05), rz + 0.02, rz + 0.02, W.dark, seg=seg)
        z += max(W.course, 0.6)
    q0.cyl((0, 0, H - 0.25), (0, 0, H), r - 0.1, r - 0.1, W.dark, seg=seg)
    q0.cyl((0, 0, H), (0, 0, H + 0.05), r - 0.4, r - 0.4, W.walkmat, seg=seg)
    rin = (r - 0.1) * math.cos(math.pi / seg) - 0.17
    side = 2 * (r - 0.1) * math.sin(math.pi / seg)
    for k in range(seg):
        q = p.at(rot=k * 45.0)
        q.box((0, -rin, H + 0.3), (side, 0.34, 0.6), W.mat)
        for s in (-1, 1):
            q.box((s * (side / 2 - 0.3), -rin, H + 0.9), (0.6, 0.34, 0.6), W.mat)
            q.box((s * (side / 2 - 0.3), -rin, H + 1.23), (0.66, 0.42, 0.07), W.trim)
        if k in (1, 3, 5, 7):
            q.box((0, -rin + 0.25, 0.9), (0.44, 0.3, 1.3), W.trim)
    for zb in W.bands[:1]:
        q0.cyl((0, 0, 2.0), (0, 0, 2.14), r - 0.2, r - 0.22, W.band_mat, seg=seg)
    # Stones for the defenders and a brazier.
    for i, (x, y) in enumerate(((1.2, 0.9), (1.5, 0.6), (1.3, 0.5), (1.35, 0.75))):
        p.sphere((x, y, H + 0.2 + (0.22 if i == 3 else 0)), 0.17, "stone", seg=6, rings=4)
    flag(p, -1.3, 1.3, H, 2.6)
    pt = top_fire(p, H)
    if p.static:
        return None
    names, bones = flame_bones([pt])
    return add_flicker(kit.Mech(bones), names)


def tower_keep(p, W):
    """A keep 6 x 6 m and 11 m to its platform, with corner turrets, an
    upper hall under a hipped roof and a waving banner."""
    H = 11.0
    size = 5.6
    hs = size / 2
    p.taper((0, 0), (size + 0.9, size + 0.9), (size + 0.08, size + 0.08), 0.0, 1.4, W.dark)
    W.block(p, -hs, hs, -hs, hs, 0.0, H, 0.0, proud_x=True)
    p.box((0, 0, H - 0.13), (size + 0.5, size + 0.5, 0.26), W.dark)
    p.box((0, 0, 5.4), (size + 0.16, size + 0.16, 0.2), W.trim)
    p.box((0, 0, H + 0.01), (size, size, 0.05), W.walkmat)
    ring_parapet(p, W, hs + 0.1, H)
    for d in "ESWN":
        for off in (-1.4, 1.4):
            slit_on(p, W, d, off, 3.4, hs)
            slit_on(p, W, d, off, 9.0, hs)
        q = p.at(rot=SIDE_ROT[d])   # An arched window per side, at the hall.
        q.box((0, -hs - 0.01, 7.1), (1.0, 0.12, 1.7), W.trim)
        q.box((0, -hs - 0.05, 7.0), (0.7, 0.08, 1.3), "dark")
        q.box((0, -hs - 0.08, 7.0), (0.05, 0.05, 1.3), W.trim)
        q.box((0, -hs - 0.08, 7.2), (0.7, 0.05, 0.05), W.trim)
        q.box((0, -hs - 0.12, 6.2), (1.2, 0.3, 0.12), W.trim)
    # Corner turrets hanging from the top.
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * hs, sy * hs
            p.cyl((x, y, H - 2.6), (x, y, H - 1.7), 0.15, 0.75, W.dark, seg=8)
            p.cyl((x, y, H - 1.7), (x, y, H + 1.7), 0.75, 0.75, W.mat, seg=8)
            p.cyl((x, y, H + 0.2), (x, y, H + 0.3), 0.78, 0.78, W.dark, seg=8)
            p.box((x + sx * 0.53, y + sy * 0.53, H + 0.9), (0.12, 0.12, 0.6), "dark", rz=45)
            cone_roof(p, (x, y), 0.95, H + 1.7, 1.5, mats=W.roof, tiers=2, seg=8)
    # The upper hall and its roof.
    us = 3.4
    W.block(p, -us / 2, us / 2, -us / 2, us / 2, H, H + 2.4, H - 0.4, proud_x=True)
    for d in "ESWN":
        q = p.at(rot=SIDE_ROT[d])
        q.box((0, -us / 2 - 0.02, H + 1.3), (0.6, 0.1, 0.9), W.trim)
        q.box((0, -us / 2 - 0.05, H + 1.3), (0.36, 0.08, 0.66), "dark")
    p.box((0, 0, H + 2.45), (us + 0.3, us + 0.3, 0.14), W.dark)
    pyramid_roof(p, (0, 0), us, us, H + 2.5, 2.4, mats=W.roof, over=0.35, tiers=4)
    # Door on the front, up a flight of steps.
    for i in range(6):
        p.box((0, -hs - 0.75 - (5 - i) * 0.3, (i + 1) * 0.125), (1.9, 0.32, (i + 1) * 0.25), W.light)
    p.box((0, -hs - 0.45, 0.75), (1.9, 0.9, 1.5), W.mat)
    p.box((0, -hs - 0.02, 2.55), (1.7, 0.16, 2.3), W.trim)
    p.box((0, -hs - 0.08, 2.5), (1.3, 0.1, 2.0), "door")
    for z in (1.9, 2.5, 3.1):
        p.box((0, -hs - 0.13, z), (1.3, 0.05, 0.1), "iron")
    p.box((0, -hs - 0.1, 4.6), (0.9, 0.06, 1.2), "cloth_red")
    p.box((0, -hs - 0.14, 4.7), (0.4, 0.04, 0.4), "gold")
    # The banner on the roof.
    zf = H + 4.9
    p.cyl((0, 0, zf - 0.3), (0, 0, zf + 2.2), 0.05, 0.04, "timber", seg=6)
    p.yprism([(0.04, zf + 1.2), (1.5, zf + 1.5), (1.5, zf + 1.9), (0.04, zf + 2.15)], -0.02, 0.02, "cloth_red",
             {"flag": 1.0})
    p.yprism([(1.5, zf + 1.5), (2.3, zf + 1.72), (1.5, zf + 1.9)], -0.02, 0.02, "gold", {"flag_tip": 1.0})
    if p.static:
        return None
    mech = kit.Mech([("flag", (0, 0, zf + 1.7), (1.5, 0, zf + 1.7), None),
                     ("flag_tip", (1.5, 0, zf + 1.7), (2.3, 0, zf + 1.7), "flag")])
    mech.clip("wave", 2.4, lambda t: {
        "flag": [(kit.Z, 16 * math.sin(2 * math.pi * t))],
        "flag_tip": [(kit.Z, 26 * math.sin(2 * math.pi * t - 1.0))],
    })
    return mech


def ballista(p, z, bone="ballista", scale=1.0):
    """A ballista on a turntable at height z, aiming at -Y. Everything is
    weighted to `bone`, the bolt to "bolt"."""
    w = {bone: 1.0}
    p.cyl((0, 0, z), (0, 0, z + 0.18), 0.7, 0.7, "timber", seg=10)
    p.cyl((0, 0, z + 0.18), (0, 0, z + 0.3), 0.55, 0.55, "wood", w, seg=10)
    for s in (-1, 1):
        p.beam((s * 0.35, 0.5, z + 0.3), (s * 0.12, 0.1, z + 1.05), 0.1, "timber", w)
        p.beam((s * 0.35, -0.5, z + 0.3), (s * 0.12, -0.1, z + 1.05), 0.1, "timber", w)
    p.beam((0, 1.1, z + 0.95), (0, -1.3, z + 1.25), 0.18, "wood", w)            # The stock.
    p.box((0, -1.05, z + 1.26), (1.0, 0.3, 0.42), "timber", w)                  # The spring frame.
    for s in (-1, 1):
        p.cyl((s * 0.38, -1.05, z + 0.98), (s * 0.38, -1.05, z + 1.54), 0.09, 0.09, "rope", w, seg=6)
        p.beam((s * 0.38, -1.05, z + 1.26), (s * 1.35, -0.55, z + 1.3), 0.08, "wood_light", w)   # The arms.
        p.beam((s * 1.35, -0.55, z + 1.3), (0, 0.75, z + 1.08), 0.025, "rope", w)                # The string.
        p.box((s * 0.5, -1.05, z + 1.26), (0.06, 0.34, 0.46), "iron", w)
    p.cyl((-0.3, 0.95, z + 1.02), (0.3, 0.95, z + 1.02), 0.08, 0.08, "iron", w, seg=6)           # The winch.
    for s in (-1, 1):
        p.beam((s * 0.3, 0.95, z + 0.8), (s * 0.3, 0.95, z + 1.24), 0.04, "iron_dark", w)
    wb = {"bolt": 1.0}
    p.cyl((0, 0.7, z + 1.14), (0, -1.5, z + 1.42), 0.03, 0.03, "wood_light", wb, seg=5)
    p.cyl((0, -1.5, z + 1.42), (0, -1.8, z + 1.458), 0.06, 0.0, "iron", wb, seg=4)
    for s in (-1, 1):
        p.box((s * 0.05, 0.6, z + 1.155), (0.1, 0.25, 0.01), "cloth_red", wb)
    return [(bone, (0, 0, z + 0.2), (0, 0, z + 1.2), None), ("bolt", (0, 0.7, z + 1.14), (0, -0.3, z + 1.27), bone)]


def ballista_clips(mech):
    mech.clip("aim", 5.0, lambda t: {"ballista": [(kit.Z, 55.0 * math.sin(2 * math.pi * t))]})

    def fire(t):
        d = 0.0 if t < 0.1 else min(1.0, (t - 0.1) / 0.5)
        back = 1.0 if t < 0.7 else 1.0 - (t - 0.7) / 0.3
        k = d * back if t < 0.7 else back
        return {}, {"bolt": (0.0, -9.0 * k, 1.1 * k * (1.0 - 0.4 * k))}

    mech.clip("fire", 1.6, fire)
    return mech


def tower_ballista(p, W, walk_sides="EW"):
    H = W.h + 2.0
    square_shell(p, W, 3.6, H, walk_sides)
    for sx in (-1, 1):   # A timber stand, so the ballista clears the merlons.
        for sy in (-1, 1):
            p.box((sx * 0.75, sy * 0.75, H + 0.3), (0.16, 0.16, 0.6), "timber")
    p.box((0, 0, H + 0.62), (1.9, 1.9, 0.1), "wood")
    bones = ballista(p, H + 0.67)
    for i, (x, y) in enumerate(((1.3, 1.2), (1.3, 0.9), (1.3, 0.6))):   # Spare bolts.
        p.cyl((x, y - 0.1, H + 0.1), (x + 0.05, y + 0.1, H + 1.3), 0.03, 0.03, "wood_light", seg=5)
    p.box((1.3, 0.9, H + 0.3), (0.3, 0.9, 0.5), "wood")
    if p.static:
        return None
    return ballista_clips(kit.Mech(bones))


def tower_wood_ballista(p):
    tower_wood_square(static_pen(p))
    bones = ballista(p, 5.1)
    if p.static:
        return None
    return ballista_clips(kit.Mech(bones))


def static_pen(p):
    """The same pen without bone weights."""
    from wallkit import Pen
    return Pen(p.mb, p.m, True)


# --- Registration ----------------------------------------------------------------------------

MASONRY = (("stone", "Sillería", "piedra"), ("brick", "Ladrillo", "ladrillo y piedra"),
           ("iron", "Reforzada con hierro", "piedra y hierro"), ("dwarf", "Enana", "piedra y oro"),
           ("elf", "Élfica", "piedra"), ("darkelf", "De elfos oscuros", "piedra y hierro"),
           ("sandstone", "Arenisca", "piedra"), ("foxfolk", "De la gente zorro", "piedra, troncos y tejas"),
           ("catfolk", "De la gente gato", "arcilla y tejas"))
for key, nombre, material in MASONRY:
    W_ = WALLS[key]
    reg("tower_square", "tower_%s_square" % key, nombre + ", abierta", (lambda p, W=W_: tower_square(p, W)),
        material=material, anim=FLICKER)
    reg("tower_square", "tower_%s_square_roof" % key, nombre + ", con tejado",
        (lambda p, W=W_: tower_square(p, W, roof=True)), material=material + " y tejas")
    reg("tower_round", "tower_%s_round" % key, nombre + ", abierta", (lambda p, W=W_: tower_round(p, W)),
        material=material, anim=FLICKER)
    reg("tower_round", "tower_%s_round_roof" % key, nombre + ", con tejado",
        (lambda p, W=W_: tower_round(p, W, roof=True)), material=material + " y tejas")
    reg("tower_bastion", "tower_%s_bastion" % key, nombre, (lambda p, W=W_: tower_bastion(p, W)), material=material,
        anim=FLICKER)
    reg("tower_keep", "tower_%s_keep" % key, nombre, (lambda p, W=W_: tower_keep(p, W)), material=material,
        anim={"wave": "El estandarte ondea"})
    reg("tower_ballista", "tower_%s_ballista" % key, nombre, (lambda p, W=W_: tower_ballista(p, W)),
        material=material, anim={"aim": "La balista gira buscando blanco", "fire": "Dispara el virote y recarga"})

reg("tower_wood", "tower_wood_square", "Cuadrada, abierta", lambda p: tower_wood_square(p), material="troncos",
    anim=FLICKER)
reg("tower_wood", "tower_wood_square_roof", "Cuadrada, con techo de paja", lambda p: tower_wood_square(p, roof=True),
    material="troncos y paja")
reg("tower_wood", "tower_wood_round", "Redonda, abierta", lambda p: tower_wood_round(p), material="troncos",
    anim=FLICKER)
reg("tower_wood", "tower_wood_round_roof", "Redonda, con techo de paja", lambda p: tower_wood_round(p, roof=True),
    material="troncos y paja")
ORC = dict(log="timber", tip="bone", roof_mats=("hide", "timber"), orc=True)
reg("tower_wood", "tower_orc_round", "Orca, abierta", lambda p: tower_wood_round(p, **ORC),
    material="troncos y hierro", anim=FLICKER)
reg("tower_wood", "tower_orc_round_roof", "Orca, con techo de pieles", lambda p: tower_wood_round(p, roof=True, **ORC),
    material="troncos, hierro y cuero")
reg("tower_ballista", "tower_wood_ballista", "De madera", tower_wood_ballista, material="troncos",
    anim={"aim": "La balista gira buscando blanco", "fire": "Dispara el virote y recarga"})
