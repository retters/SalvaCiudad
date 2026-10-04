"""Frog-folk: round huts of reeds under mossy domes, on decks that stand on
stilts in their own pond, with plank walks, lily pads, cattails and gourd
lanterns."""

import math

import rparts as p
from rparts import TAU

SEG = 9          # Odd, so a flat side of every hut looks to the front.
FACE = TAU / SEG
DOME = ("reed", "moss", "reed", "reed_dark")


def on_hut(mb, x, y, r, j=0, z=0.0):
    """The face frame on side j of a hut (0 is the front, positive to the right)."""
    a = -math.pi / 2 + j * FACE
    rr = r * math.cos(math.pi / SEG) * 1.0
    return mb.placed((x + math.cos(a) * rr, y + math.sin(a) * rr, z), a + math.pi / 2)


def hut(mb, x, y, z, r, wall, dome_h, door=True, windows=(-2, 2), knot=True):
    mb.cylinder((x, y, z), (x, y, z + wall), r, r, "reed", segments=SEG)
    mb.cylinder((x, y, z), (x, y, z + 0.2), r + 0.05, r + 0.05, "reed_dark", segments=SEG)
    for k in range(SEG):                                                        # Poles at the corners, tied with a band.
        a = math.pi / 2 - FACE * k
        mb.cylinder((x + math.cos(a) * r, y + math.sin(a) * r, z), (x + math.cos(a) * r, y + math.sin(a) * r, z + wall), 0.06, 0.06, "moss_dark", segments=5)
    mb.cylinder((x, y, z + wall * 0.62), (x, y, z + wall * 0.7), r + 0.03, r + 0.03, "moss", segments=SEG)
    if dome_h > 0:
        p.dome(mb, x, y, z + wall, r, dome_h, DOME, 4, SEG, 0.32)
    if knot:
        mb.cylinder((x, y, z + wall + dome_h - 0.05), (x, y, z + wall + dome_h + 0.4), 0.12, 0.2, "reed_dark", segments=6)
        mb.cylinder((x, y, z + wall + dome_h + 0.08), (x, y, z + wall + dome_h + 0.16), 0.17, 0.17, "moss", segments=6)
    if door:
        with on_hut(mb, x, y, r, 0, z):
            p.round_door(mb, 0, 0.08, min(0.7, wall * 0.5), "moss", "dark", None)
    for j in windows:
        with on_hut(mb, x, y, r, j, z):
            p.win(mb, 0, wall * 0.62, 0.36, 0.4, "moss_dark", "frog_glow", False)
    return z + wall + dome_h


def deck(mb, x, y, z, r, stilts=6, seg=10):
    mb.cylinder((x, y, z - 0.16), (x, y, z), r, r, "deck", segments=seg)
    mb.cylinder((x, y, z - 0.22), (x, y, z - 0.1), r + 0.06, r + 0.06, "deck_dark", segments=seg)
    for k in range(stilts):
        a = TAU * k / stilts + 0.35
        mb.cylinder((x + math.cos(a) * r * 0.86, y + math.sin(a) * r * 0.86, 0), (x + math.cos(a) * r * 0.82, y + math.sin(a) * r * 0.82, z - 0.1), 0.09, 0.08, "deck_dark", segments=6)


def walk(mb, a, b, w=0.9, posts=True, rail=False):
    """A walk of planks from a to b (a ramp if their heights differ)."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy)
    rot = math.atan2(dy, dx)
    nx, ny = -dy / length, dx / length
    for s in (-1, 1):
        p.beam(mb, (a[0] + nx * s * w * 0.4, a[1] + ny * s * w * 0.4, a[2] - 0.1), (b[0] + nx * s * w * 0.4, b[1] + ny * s * w * 0.4, b[2] - 0.1), 0.09, "deck_dark")
    n = max(2, round(length / 0.3))
    for i in range(n):
        u = (i + 0.5) / n
        mb.box((a[0] + dx * u, a[1] + dy * u, a[2] + (b[2] - a[2]) * u - 0.02), (length / n * 0.86, w, 0.05), "deck", rotation_z=rot)
    if posts:
        for u in (0.0, 0.5, 1.0) if length > 2.2 else (0.0, 1.0):
            zz = a[2] + (b[2] - a[2]) * u
            if zz > 0.3:
                for s in (-1, 1):
                    mb.cylinder((a[0] + dx * u + nx * s * w * 0.45, a[1] + dy * u + ny * s * w * 0.45, 0), (a[0] + dx * u + nx * s * w * 0.45, a[1] + dy * u + ny * s * w * 0.45, zz + (0.7 if rail else 0.0)), 0.05, 0.05, "deck_dark", segments=5)


def reeds(mb, rig, rnd, x, y, n=4, spread=0.4, z=0.1):
    """A clump of cattails that rocks in the wind (clip `sway`)."""
    name = rig.name("reeds")
    with mb.bone(name):
        for _ in range(n):
            p.cattail(mb, x + rnd.uniform(-spread, spread), y + rnd.uniform(-spread, spread), z, rnd.uniform(1.2, 2.0), rnd.uniform(-0.15, 0.15))
    p.sway(mb, rig, name, (x, y, z), 5.0, 4.0, "sway", (0, 1, 0), (x, y, z + 1.0))


def lilies(mb, rnd, cx, cy, rx, ry, n, keep_out=()):
    made = 0
    for _ in range(n * 6):
        a, u = rnd.uniform(0, TAU), rnd.uniform(0.35, 0.82)
        x, y = cx + math.cos(a) * rx * u, cy + math.sin(a) * ry * u
        if any(math.hypot(x - kx, y - ky) < kr for kx, ky, kr in keep_out):
            continue
        p.lily(mb, x, y, 0.13, rnd.uniform(0.22, 0.4), made % 3 == 0, rnd.uniform(0, TAU))
        made += 1
        if made >= n:
            break


def lamp(mb, rig, x, y, h=2.2, z=0.0, side=1):
    """A bent reed with a gourd of fireflies."""
    p.arc(mb, [(x, y, z), (x, y, z + h * 0.6), (x + side * 0.2, y, z + h * 0.92), (x + side * 0.5, y, z + h)], 0.05, "moss_dark", 0.6)
    p.hang_lantern(mb, rig, x + side * 0.5, y, z + h, 0.12, "gourd", "frog_glow", "moss_dark")


def pot(mb, x, y, z, s=1.0, mat="mud"):
    p.lathe(mb, x, y, z, [(0.16 * s, 0), (0.32 * s, 0.25 * s), (0.28 * s, 0.5 * s), (0.16 * s, 0.6 * s)], (mat, "clay", mat), 7)
    mb.cylinder((x, y, z + 0.6 * s), (x, y, z + 0.66 * s), 0.19 * s, 0.19 * s, "moss", segments=7)


def totem(mb, x, y, h=3.0, z=0.0):
    """A post carved with frogs sitting on one another."""
    mb.cylinder((x, y, z), (x, y, z + h), 0.2, 0.17, "deck_dark", segments=7)
    n = max(2, int(h / 0.9))
    for k in range(n):
        zz = z + 0.5 + (h - 0.6) * k / n
        mb.sphere((x, y - 0.05, zz), 0.34, "moss" if k % 2 else "lily", segments=7, rings=5, scale=(1.2, 1.0, 0.75))
        for sx in (-1, 1):
            mb.sphere((x + sx * 0.2, y - 0.22, zz + 0.2), 0.11, "frog_glow", segments=5, rings=4)
            mb.box((x + sx * 0.2, y - 0.32, zz + 0.2), (0.05, 0.03, 0.09), "dark")
        mb.box((x, y - 0.36, zz - 0.02), (0.4, 0.04, 0.04), "dark")


def house(level):
    def build():
        mb = p.begin()
        rig = p.Rig()
        rnd = p.random.Random(110 + level)
        if level == 1:
            p.pond(mb, 0, 0, 1.95, 1.85)
            deck(mb, 0, 0.2, 0.75, 1.45, 5)
            hut(mb, 0, 0.3, 0.75, 1.1, 1.15, 1.0, True, (2,))
            walk(mb, (0, -1.85, 0.12), (0, -1.1, 0.75), 0.8, False)
            lilies(mb, rnd, 0, 0, 1.9, 1.8, 3, ((0, -1.4, 0.6),))
            reeds(mb, rig, rnd, -1.5, -0.6, 3, 0.2)
            lamp(mb, rig, 1.2, -0.9, 1.5, 0.75, -1)
        elif level == 2:
            p.pond(mb, 0, 0, 2.9, 2.4)
            deck(mb, -0.5, 0.3, 0.85, 2.0, 6)
            hut(mb, -0.5, 0.5, 0.85, 1.55, 1.3, 1.3, True, (-2, 2))
            deck(mb, 1.9, -0.7, 0.6, 0.95, 4, 8)                                # A lower deck to fish from.
            walk(mb, (0.9, -0.5, 0.85), (1.6, -0.7, 0.6), 0.7, False)
            walk(mb, (-0.5, -2.4, 0.12), (-0.5, -1.55, 0.85), 0.9, False)
            p.beam(mb, (2.2, -0.9, 0.6), (2.75, -1.7, 1.7), 0.04, "moss_dark")    # A rod left propped, its line in the water.
            mb.cylinder((2.75, -1.7, 1.7), (2.75, -1.75, 0.14), 0.006, 0.006, "net", segments=3)
            pot(mb, 1.7, -0.3, 0.6, 0.8)
            lilies(mb, rnd, 0, 0, 2.8, 2.3, 5, ((-0.5, -2.0, 0.7), (1.9, -0.7, 1.0)))
            reeds(mb, rig, rnd, -2.4, -0.6, 4, 0.25)
            reeds(mb, rig, rnd, 2.3, 1.1, 3, 0.25)
            lamp(mb, rig, -1.9, -1.0, 1.7, 0.85)
        else:
            p.pond(mb, 0, 0, 3.9, 2.9)
            deck(mb, -0.9, 0.4, 0.95, 2.4, 7)
            hut(mb, -0.9, 0.6, 0.95, 1.95, 1.5, 0.0, True, (-2, -1, 1, 2), False)
            zz = 0.95 + 1.5                                                     # The dome is cut flat for an upper room.
            p.lathe(mb, -0.9, 0.6, zz, [(2.3, 0), (2.05, 0.5), (1.5, 0.9)], ("reed", "moss"), SEG)
            mb.cylinder((-0.9, 0.6, zz + 0.86), (-0.9, 0.6, zz + 0.96), 1.6, 1.6, "deck", segments=SEG)
            hut(mb, -0.9, 0.6, zz + 0.96, 1.05, 0.9, 0.95, False, (-2, 0, 2))
            deck(mb, 2.4, -0.3, 0.7, 1.35, 5)
            hut(mb, 2.4, -0.2, 0.7, 1.05, 1.1, 0.95, True, (2,))
            walk(mb, (1.3, 0.0, 0.95), (1.5, -0.2, 0.7), 0.8, False)
            walk(mb, (-0.9, -2.9, 0.12), (-0.9, -1.9, 0.95), 1.0, False)
            pot(mb, 0.4, -1.3, 0.95, 0.9)
            pot(mb, -2.6, -0.6, 0.95, 0.7, "clay")
            lilies(mb, rnd, 0, 0, 3.8, 2.8, 7, ((-0.9, -2.4, 0.8), (2.4, -0.3, 1.3)))
            reeds(mb, rig, rnd, -3.3, -0.4, 4, 0.3)
            reeds(mb, rig, rnd, 3.4, 0.9, 4, 0.3)
            reeds(mb, rig, rnd, 0.9, -2.3, 3, 0.25)
            lamp(mb, rig, -2.5, -1.4, 1.8, 0.95)
            lamp(mb, rig, 0.6, -1.7, 1.8, 0.95, -1)
        p.finish(mb, "race_frog_house_%d" % level, rig)
    return build


def center():
    """The great lodge: a moss dome with a lantern room, four huts around it
    and a ring of walks, in a pond of 12 x 12 m."""
    mb = p.begin()
    rig = p.Rig()
    rnd = p.random.Random(117)
    p.pond(mb, 0, 0, 5.9, 5.8, 14)
    cy = 0.5
    deck(mb, 0, cy, 1.1, 3.7, 9, 12)
    hut(mb, 0, cy, 1.1, 3.1, 2.0, 0.0, False, (-3, -2, -1, 1, 2, 3), False)
    with on_hut(mb, 0, cy, 3.1, 0, 1.1):
        p.round_door(mb, 0, 0.08, 0.95, "moss", "dark", None)
        for sx in (-1, 1):
            p.arc(mb, [(sx * 1.25, -0.3, 0), (sx * 1.2, -0.35, 1.5), (sx * 0.7, -0.4, 2.35), (0, -0.4, 2.6)], 0.09, "moss_dark", 0.6)
    z = 3.1
    p.lathe(mb, 0, cy, z, [(3.5, 0), (3.25, 0.8), (2.6, 1.6), (1.7, 2.2)], ("reed", "moss", "reed"), SEG)
    mb.cylinder((0, cy, z + 2.15), (0, cy, z + 2.3), 1.85, 1.85, "deck", segments=SEG)
    top = hut(mb, 0, cy, z + 2.3, 1.3, 1.0, 1.2, False, tuple(range(-4, 5)))        # The lantern room.
    with mb.bone("glow"):
        mb.sphere((0, cy, top + 1.0), 0.42, "frog_glow", segments=8, rings=6)
        p.ring(mb, 0, cy, top + 1.0, 0.62, 0.05, "moss_dark", 9)
    p.bob(mb, rig, "glow", (0, cy, top + 1.0), 0.1, 6.0, "float")
    for k in range(4):                                                          # The four huts and the ring of walks.
        a = TAU * k / 4 + TAU / 8
        x, y = math.cos(a) * 4.5, cy + math.sin(a) * 4.3
        deck(mb, x, y, 0.8, 1.5, 5)
        with mb.placed((x, y, 0), a + math.pi / 2 + math.pi):
            hut(mb, 0, 0, 0.8, 1.15, 1.15, 1.05, True, (-2, 2))
        walk(mb, (math.cos(a) * 3.3, cy + math.sin(a) * 3.3, 1.1), (math.cos(a) * 3.5, cy + math.sin(a) * 3.4, 0.8), 0.9, False)
    for sx in (-1, 1):
        walk(mb, (sx * 2.2, cy - 3.9, 0.8), (sx * 0.9, cy - 4.3, 0.8), 0.8)
    walk(mb, (0, -5.9, 0.12), (0, -4.6, 0.8), 1.6, False)
    walk(mb, (0, -4.6, 0.8), (0, -3.6, 0.8), 1.6)
    walk(mb, (0, -3.6, 0.8), (0, -3.0, 1.1), 1.6, False)
    for sx in (-1, 1):
        totem(mb, sx * 1.2, -4.9, 2.8, 0.75)
        lamp(mb, rig, sx * 1.75, cy - 3.4, 2.2, 1.1, -sx)
        reeds(mb, rig, rnd, sx * 5.0, 0.4, 5, 0.3)
        reeds(mb, rig, rnd, sx * 2.6, -5.0, 4, 0.3)
        reeds(mb, rig, rnd, sx * 1.4, 5.3, 4, 0.3)
        for k in range(3):
            a = -math.pi / 2 + sx * (0.45 + 0.6 * k)
            p.hang_lantern(mb, rig, math.cos(a) * 3.65, cy + math.sin(a) * 3.65, z + 0.02, 0.15, "gourd", "frog_glow", "moss_dark", 1.1)
    lilies(mb, rnd, 0, 0, 5.7, 5.6, 12, ((0, cy, 3.9), (0, -5.0, 1.4), (3.2, 3.5, 1.7), (-3.2, 3.5, 1.7), (3.2, -2.6, 1.7), (-3.2, -2.6, 1.7)))
    p.finish(mb, "race_frog_center", rig)


def workshop():
    """The net-makers' deck: nets drying, traps, and a boat at its post."""
    mb = p.begin()
    rig = p.Rig()
    rnd = p.random.Random(118)
    p.pond(mb, 0, 0, 2.95, 2.9)
    z = 0.8
    mb.box((0, 0.6, z - 0.08), (4.4, 2.8, 0.16), "deck")
    mb.box((0, 0.6, z - 0.2), (4.5, 2.9, 0.1), "deck_dark")
    for sx in (-1, 0, 1):
        for sy in (-1, 1):
            mb.cylinder((sx * 2.0, 0.6 + sy * 1.2, 0), (sx * 2.0, 0.6 + sy * 1.2, z + (2.4 if sy > 0 else 1.9)), 0.09, 0.08, "deck_dark", segments=6)
    for r in range(4):                                                          # A lean-to of reed mats, mossy at the back.
        y0, y1 = 2.2 - 0.9 * r, 2.2 - 0.9 * (r + 1) - 0.05
        z0, z1 = z + 2.5 - 0.15 * r, z + 2.5 - 0.15 * (r + 1) - 0.02
        p.solid(mb, [(-2.4, y0, z0), (2.4, y0, z0), (2.4, y1, z1), (-2.4, y1, z1)], (0, 0, 0.1), ("moss", "reed", "reed_dark", "reed")[r])
    hut(mb, -1.1, 1.1, z, 0.95, 1.1, 0.0, True, (2,), False)                      # The store of twine, flat-topped under the mat.
    mb.cylinder((-1.1, 1.1, z + 1.1), (-1.1, 1.1, z + 1.25), 1.1, 0.9, "reed_dark", segments=SEG)
    for k in range(2):                                                          # Nets hung to dry.
        name = rig.name("net")
        x = 0.5 + 1.1 * k
        with mb.bone(name):
            for i in range(5):
                mb.cylinder((x - 0.4 + 0.2 * i, -0.6, z + 1.85), (x - 0.4 + 0.2 * i, -0.6, z + 0.5), 0.012, 0.012, "net", segments=3)
            for i in range(5):
                mb.cylinder((x - 0.42, -0.6, z + 0.6 + 0.28 * i), (x + 0.42, -0.6, z + 0.6 + 0.28 * i), 0.012, 0.012, "net", segments=3)
            for i in range(3):
                mb.sphere((x - 0.3 + 0.3 * i, -0.6, z + 0.46), 0.05, "cattail", segments=4, rings=3)
        p.sway(mb, rig, name, (x, -0.6, z + 1.85), 5.0, 3.5, "sway", (1, 0, 0), (x, -0.6, z + 0.6))
    p.beam(mb, (-2.0, -0.6, z + 1.88), (2.0, -0.6, z + 1.88), 0.06, "deck_dark")
    for k in range(2):                                                          # Fish traps woven of reed.
        x = 0.3 + 0.9 * k
        mb.cylinder((x, 1.2, z + 0.25), (x + 0.7, 1.2, z + 0.25), 0.25, 0.1, "reed", segments=7)
        mb.cylinder((x - 0.02, 1.2, z + 0.25), (x + 0.04, 1.2, z + 0.25), 0.26, 0.26, "reed_dark", segments=7)
    pot(mb, 1.8, 1.5, z, 0.9)
    walk(mb, (-1.6, -2.85, 0.12), (-1.6, -0.8, z), 0.9, False)
    with mb.bone("boat"):                                                       # A reed boat tied to the corner post.
        for s in (-1, 1):
            p.arc(mb, [(2.5, -2.1, 0.3), (2.6 + s * 0.3, -1.4, 0.16), (2.6 + s * 0.3, -0.6, 0.16), (2.5, 0.1, 0.36)], 0.16, "reed", 0.8)
        p.arc(mb, [(2.5, -2.15, 0.34), (2.6, -1.4, 0.12), (2.6, -0.6, 0.12), (2.5, 0.15, 0.4)], 0.17, "reed_dark", 0.8)
        mb.box((2.6, -1.0, 0.27), (0.5, 0.2, 0.05), "deck")
        p.beam(mb, (2.4, -1.6, 0.3), (2.9, -0.3, 0.42), 0.04, "deck_dark")
    rig.bone("boat", (2.6, -1.0, 0.15), (2.6, -0.2, 0.15), None)
    rig.add("float", 4.0, lambda t: ({"boat": [(p.kit.Y, 4.0 * math.sin(TAU * t)), (p.kit.X, 2.0 * math.sin(TAU * 2 * t))]}, {"boat": (0, 0, 0.03 * math.sin(TAU * t))}))
    lilies(mb, rnd, 0, 0, 2.9, 2.8, 4, ((0, 0.6, 2.6), (2.6, -1.0, 1.3), (-1.6, -2.2, 0.8)))
    reeds(mb, rig, rnd, -2.5, -1.0, 4, 0.25)
    reeds(mb, rig, rnd, 2.2, 2.3, 3, 0.2)
    lamp(mb, rig, -2.0, -0.6, 1.7, z, -1)
    p.finish(mb, "race_frog_workshop", rig)


def storehouse():
    """The pot store: sealed jars under a dome with no walls, and cool
    baskets that float tied to the stilts."""
    mb = p.begin()
    rig = p.Rig()
    rnd = p.random.Random(119)
    p.pond(mb, 0, 0, 2.9, 2.8)
    z = 0.9
    deck(mb, 0, 0.3, z, 2.2, 7)
    for k in range(7):
        a = TAU * k / 7 + math.pi / 2 + TAU / 14
        mb.cylinder((math.cos(a) * 1.9, 0.3 + math.sin(a) * 1.9, z), (math.cos(a) * 1.9, 0.3 + math.sin(a) * 1.9, z + 1.9), 0.09, 0.08, "moss_dark", segments=6)
    mb.cylinder((0, 0.3, z + 1.85), (0, 0.3, z + 2.0), 2.1, 2.1, "reed_dark", segments=SEG)
    p.dome(mb, 0, 0.3, z + 2.0, 2.0, 1.6, DOME, 4, SEG, 0.35)
    mb.cylinder((0, 0.3, z + 3.55), (0, 0.3, z + 4.0), 0.13, 0.22, "reed_dark", segments=6)
    for k, (x, y, s, mat) in enumerate(((-0.8, 0.6, 1.5, "mud"), (0.5, 0.9, 1.3, "clay"), (0.2, -0.3, 1.1, "mud"), (-0.9, -0.5, 0.9, "clay"), (1.1, 0.0, 0.9, "mud"))):
        pot(mb, x, y, z, s, mat)
    for k in range(4):                                                          # Gourds hang from the eave.
        a = -math.pi / 2 + (k - 1.5) * 0.7
        p.hang_lantern(mb, rig, math.cos(a) * 2.0, 0.3 + math.sin(a) * 2.0, z + 1.85, 0.2, "gourd", "reed" if k % 2 else "frog_glow", "moss_dark", 1.2)
    walk(mb, (0, -2.8, 0.12), (0, -1.7, z), 0.9, False)
    for k, (x, y) in enumerate(((2.3, -0.6), (-2.3, 0.2), (1.6, 1.9))):         # Baskets kept cool in the water.
        name = rig.name("basket")
        with mb.bone(name):
            mb.cylinder((x, y, 0.08), (x, y, 0.42), 0.26, 0.3, "reed", segments=7)
            mb.cylinder((x, y, 0.4), (x, y, 0.46), 0.32, 0.32, "moss", segments=7)
        rig.bone(name, (x, y, 0.13), (x, y, 0.6), None)
        ph = k * 0.3
        rig.add("float", 4.0, lambda t, n=name, ph=ph: ({n: [(p.kit.X, 5.0 * math.sin(TAU * (t + ph)))]}, {n: (0, 0, 0.04 * math.sin(TAU * (t + ph)))}))
        mb.cylinder((x, y, 0.4), (x * 0.7, 0.3 + (y - 0.3) * 0.7, z - 0.1), 0.01, 0.01, "net", segments=3)
    lilies(mb, rnd, 0, 0, 2.85, 2.75, 4, ((0, 0.3, 1.2), (0, -2.2, 0.8), (2.3, -0.6, 0.6), (-2.3, 0.2, 0.6), (1.6, 1.9, 0.6)))
    reeds(mb, rig, rnd, -2.2, -1.5, 4, 0.25)
    reeds(mb, rig, rnd, 2.3, 0.9, 3, 0.2)
    p.finish(mb, "race_frog_storehouse", rig)


def big_pad(mb, x, y, r, rot=0.0, z=0.13):
    """A lily pad big enough to stand on."""
    n = 10
    pts = [(x + math.cos(rot + TAU * i / n) * r, y + math.sin(rot + TAU * i / n) * r) for i in range(n - 1)]
    mb.prism([(x, y)] + pts, z, z + 0.1, "lily")
    inner = [(x + math.cos(rot + TAU * i / n) * r * 0.86, y + math.sin(rot + TAU * i / n) * r * 0.86) for i in range(n - 1)]
    mb.prism([(x, y)] + inner, z + 0.06, z + 0.13, "lily_dark")


def leaf_shade(mb, x, y, z, h=1.9, r=0.9, lean=0.3):
    """A leaf on its stalk for a sunshade."""
    p.arc(mb, [(x, y, z), (x + lean * 0.3, y, z + h * 0.6), (x + lean, y, z + h)], 0.05, "moss_dark", 0.7)
    mb.cylinder((x + lean, y, z + h - 0.02), (x + lean + 0.1, y, z + h + 0.14), r, r * 0.25, "lily", segments=9)
    mb.cylinder((x + lean, y, z + h - 0.06), (x + lean, y, z + h - 0.01), r * 1.02, r * 1.02, "lily_dark", segments=9)


def goods(mb, x, y, z, kind):
    if kind == 0:                                                               # Sealed pots.
        pot(mb, x - 0.3, y, z, 0.9)
        pot(mb, x + 0.3, y + 0.1, z, 0.7, "clay")
        pot(mb, x, y - 0.35, z, 0.6)
    elif kind == 1:                                                             # Baskets of fish.
        for dx in (-0.3, 0.3):
            mb.cylinder((x + dx, y, z), (x + dx, y, z + 0.28), 0.22, 0.28, "reed", segments=7)
            for i in range(4):
                mb.sphere((x + dx + 0.1 * math.cos(i * 1.6), y + 0.1 * math.sin(i * 1.6), z + 0.3), 0.13, "fish", segments=5, rings=3, scale=(1, 0.4, 0.5))
    elif kind == 2:                                                             # A heap of gourds.
        for i, (dx, dy, dz) in enumerate(((-0.25, 0, 0), (0.25, 0.05, 0), (0, 0.3, 0), (0, -0.25, 0), (0, 0.05, 0.3))):
            mb.sphere((x + dx, y + dy, z + 0.2 + dz), 0.22, ("reed", "frog_glow", "clay")[i % 3], segments=6, rings=4, scale=(1, 1, 1.1))
    elif kind == 3:                                                             # Rolled mats.
        for i in range(3):
            mb.cylinder((x - 0.5, y - 0.25 + 0.25 * i, z + 0.13), (x + 0.5, y - 0.25 + 0.25 * i, z + 0.13), 0.13, 0.13, "reed" if i % 2 else "reed_dark", segments=7)
        mb.cylinder((x - 0.5, y - 0.1, z + 0.36), (x + 0.5, y - 0.1, z + 0.36), 0.13, 0.13, "moss", segments=7)
    elif kind == 4:                                                             # Flowers and herbs.
        for i in range(6):
            a = TAU * i / 6
            mb.cylinder((x + math.cos(a) * 0.3, y + math.sin(a) * 0.3, z), (x + math.cos(a) * 0.3, y + math.sin(a) * 0.3, z + 0.16), 0.06, 0.16, "lily_flower" if i % 2 else "flower_w", segments=6)
        mb.sphere((x, y, z + 0.15), 0.22, "moss", segments=5, rings=3)
    else:                                                                       # Flies and grubs in jars of light.
        for dx in (-0.3, 0.05, 0.4):
            mb.cylinder((x + dx, y, z), (x + dx, y, z + 0.36), 0.14, 0.14, "frog_glow", segments=7)
            mb.cylinder((x + dx, y, z + 0.36), (x + dx, y, z + 0.42), 0.16, 0.16, "deck_dark", segments=7)


def lily_market():
    """The lily-pad market: stalls that float on giant pads along a walk of
    planks, in a pond of 10 x 8 m."""
    mb = p.begin()
    rig = p.Rig()
    rnd = p.random.Random(115)
    p.pond(mb, 0, 0, 5.0, 4.0, 14)
    z = 0.5
    walk(mb, (0, -4.0, 0.12), (0, -3.0, z), 1.3, False)
    walk(mb, (0, -3.0, z), (0, 2.9, z), 1.3)
    pads = ((-2.3, -1.8, 1.15), (2.3, -1.8, 1.2), (-2.9, 0.5, 1.3), (2.9, 0.5, 1.25), (-1.9, 2.5, 1.1), (1.9, 2.5, 1.15))
    for k, (x, y, r) in enumerate(pads):
        sx = 1 if x > 0 else -1
        mb.box((sx * (0.65 + (abs(x) - r - 0.5) / 2), y, z - 0.03), (abs(x) - r - 0.4, 0.5, 0.05), "deck")     # A plank from the walk.
        name = "pad_%d" % k
        with mb.bone(name):
            big_pad(mb, x, y, r, math.pi if sx > 0 else 0.0, 0.13)
            goods(mb, x + sx * 0.15, y, 0.26, k)
            leaf_shade(mb, x + sx * (r - 0.25), y + 0.3, 0.26, 1.7 + 0.2 * (k % 2), 0.85, -sx * 0.4)
            if k % 2 == 0:
                mb.cylinder((x - sx * 0.2, y - r * 0.6, 0.26), (x - sx * 0.2, y - r * 0.6, 0.42), 0.05, 0.14, "lily_flower", segments=6)
        rig.bone(name, (x, y, 0.13), (x, y, 0.6), None)
        ph = k * 0.17
        rig.add("float", 5.0, lambda t, n=name, ph=ph: ({n: [(p.kit.X, 1.5 * math.sin(TAU * (t + ph))), (p.kit.Y, 1.2 * math.sin(TAU * (2 * t + ph)))]}, {n: (0, 0, 0.025 * math.sin(TAU * (t + ph)))}))
    deck(mb, 0, 3.3, z, 1.1, 5, 9)                                              # The weigh-house at the end of the walk.
    hut(mb, 0, 3.4, z, 0.85, 1.0, 0.8, True, ())
    for sx in (-1, 1):
        lamp(mb, rig, sx * 0.75, -2.9, 2.0, z, -sx)
        lamp(mb, rig, sx * 0.75, 0.2, 2.0, z, -sx)
        reeds(mb, rig, rnd, sx * 4.3, -1.0, 4, 0.3)
        reeds(mb, rig, rnd, sx * 3.4, 2.9, 3, 0.25)
    totem(mb, -1.2, -4.2, 2.2)
    with mb.bone("boat"):                                                       # A customer's boat.
        for s in (-1, 1):
            p.arc(mb, [(3.8, 0.9, 0.3), (3.95 + s * 0.28, 1.4, 0.16), (3.85 + s * 0.28, 2.0, 0.16), (3.55, 2.5, 0.34)], 0.15, "reed", 0.8)
        p.arc(mb, [(3.8, 0.88, 0.33), (3.95, 1.4, 0.12), (3.85, 2.0, 0.12), (3.54, 2.52, 0.37)], 0.16, "reed_dark", 0.8)
    rig.bone("boat", (3.9, 1.7, 0.15), (3.8, 2.3, 0.15), None)
    rig.add("float", 5.0, lambda t: ({"boat": [(p.kit.Y, 3.0 * math.sin(TAU * t))]}, {"boat": (0, 0, 0.03 * math.sin(TAU * (t + 0.3)))}))
    lilies(mb, rnd, 0, 0, 4.9, 3.9, 8, tuple((x, y, r + 0.4) for x, y, r in pads) + ((0, 0, 1.0), (0, -2.0, 1.0), (0, 2.0, 1.4), (3.8, 1.7, 1.1)))
    p.finish(mb, "race_frog_lily_market", rig)


def tower():
    """A lookout on long stilts over the water, under a reed dome."""
    mb = p.begin()
    rig = p.Rig()
    rnd = p.random.Random(116)
    p.pond(mb, 0, 0, 1.95, 1.95)
    zf = 5.2
    for k in range(4):
        a = TAU * k / 4 + TAU / 8
        c, s = math.cos(a), math.sin(a)
        mb.cylinder((c * 1.5, s * 1.5, 0), (c * 1.0, s * 1.0, zf - 0.1), 0.11, 0.09, "deck_dark", segments=6)
        b = TAU * (k + 1) / 4 + TAU / 8
        for z0, z1 in ((0.5, 2.3), (2.3, 4.2)):                                 # Lashed braces.
            k0, k1 = 1.5 - 0.5 * z0 / zf, 1.5 - 0.5 * z1 / zf
            p.beam(mb, (c * k0, s * k0, z0), (math.cos(b) * k1, math.sin(b) * k1, z1), 0.07, "moss_dark")
    deck(mb, 0, 0, zf, 1.6, 0, 9)
    p.ring(mb, 0, 0, zf + 0.8, 1.5, 0.06, "moss_dark", 9)
    for k in range(9):
        a = math.pi / 2 - FACE * k
        p.beam(mb, (math.cos(a) * 1.5, math.sin(a) * 1.5, zf), (math.cos(a) * 1.5, math.sin(a) * 1.5, zf + 0.8), 0.05, "moss_dark")
    for k in range(5):                                                          # A dome on poles: open all round.
        a = TAU * k / 5 + math.pi / 2
        mb.cylinder((math.cos(a) * 1.1, math.sin(a) * 1.1, zf), (math.cos(a) * 1.1, math.sin(a) * 1.1, zf + 1.9), 0.06, 0.06, "moss_dark", segments=5)
    mb.cylinder((0, 0, zf + 1.85), (0, 0, zf + 1.98), 1.3, 1.3, "reed_dark", segments=SEG)
    p.dome(mb, 0, 0, zf + 1.98, 1.2, 1.1, DOME, 4, SEG, 0.3)
    mb.cylinder((0, 0, zf + 3.0), (0, 0, zf + 3.45), 0.1, 0.18, "reed_dark", segments=6)
    with mb.bone("horn"):                                                       # A shell horn to give the alarm.
        mb.cylinder((0.0, -0.9, zf + 1.1), (0.0, -1.5, zf + 1.3), 0.06, 0.24, "egg", segments=7)
        mb.cylinder((0.0, -0.9, zf + 1.1), (0.0, -0.9, zf + 1.85), 0.012, 0.012, "net", segments=3)
    p.sway(mb, rig, "horn", (0, -0.9, zf + 1.85), 8.0, 3.0, "sway", (1, 0, 0), (0, -0.9, zf + 1.1))
    for k in range(17):                                                         # The ladder up from the plank.
        mb.box((0, -1.72 - 0.015 * (16 - k), 0.35 + 0.29 * k), (0.5, 0.05, 0.05), "deck")
    for sx in (-1, 1):
        p.beam(mb, (sx * 0.26, -2.0, 0.1), (sx * 0.26, -1.7, zf + 0.3), 0.06, "deck_dark")
    walk(mb, (0, -1.95, 0.12), (0, -1.6, 0.3), 0.8, False)
    for a in (0.4, 2.6):
        p.hang_lantern(mb, rig, math.cos(a) * 1.3, math.sin(a) * 1.3, zf + 1.85, 0.2, "gourd", "frog_glow", "moss_dark")
    lilies(mb, rnd, 0, 0, 1.9, 1.9, 3, ((0, -1.6, 0.6),))
    reeds(mb, rig, rnd, -1.5, -0.7, 4, 0.2)
    reeds(mb, rig, rnd, 1.4, 0.9, 3, 0.2)
    p.finish(mb, "race_frog_tower", rig)


MODELS = {
    "race_frog_lily_market": lily_market, "race_frog_tower": tower,
    "race_frog_house_1": house(1), "race_frog_house_2": house(2), "race_frog_house_3": house(3),
    "race_frog_center": center, "race_frog_workshop": workshop, "race_frog_storehouse": storehouse,
}
