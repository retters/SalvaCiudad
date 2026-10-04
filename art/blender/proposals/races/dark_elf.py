"""Dark elves: shards of obsidian that end in needles, violet light in every
crack, thorns, webs and mushrooms that glow."""

import math

import rparts as p
from rparts import TAU

APO = math.cos(math.pi / 6)   # A six-sided shard's flat face is this far from its axis.
TURN = math.pi / 6            # bmesh puts a corner of an even-sided cone at the front; this turns a face there.


def shard_tower(mb, x, y, r, wall, tip, seg=6, lean=(0.0, 0.0), band="obsidian_light"):
    """A faceted shard: a flared foot, a wall that narrows, a needle."""
    c, s = math.cos(-TURN), math.sin(-TURN)
    lx, ly = lean[0] * c - lean[1] * s, lean[0] * s + lean[1] * c
    with mb.placed((x, y, 0), TURN):                                            # Turned so that a flat side looks to the front.
        mb.cylinder((0, 0, 0), (0, 0, 0.5), r * 1.3, r * 1.08, "obsidian_dark", segments=seg)
        mb.cylinder((0, 0, 0.5), (0, 0, wall), r * 1.05, r * 0.88, "obsidian", segments=seg)
        mb.cylinder((0, 0, wall - 0.12), (0, 0, wall + 0.1), r * 0.98, r * 0.98, band, segments=seg)
        mb.cylinder((0, 0, wall + 0.1), (lx * 0.35, ly * 0.35, wall + tip * 0.45), r * 0.92, r * 0.5, "obsidian_dark", segments=seg)
        mb.cylinder((lx * 0.35, ly * 0.35, wall + tip * 0.45), (lx, ly, wall + tip), r * 0.5, 0.0, "obsidian", segments=seg)
    return wall + tip


def hexcyl(mb, x, y, z0, z1, r0, r1, mat):
    """A six-sided band with a flat side to the front."""
    with mb.placed((x, y, 0), TURN):
        mb.cylinder((0, 0, z0), (0, 0, z1), r0, r1, mat, segments=6)


def on_shard(mb, x, y, r, k=0, z=0.0, at=0.95):
    """The face frame on side k of a six-sided shard (0 is the front)."""
    a = -math.pi / 2 + k * TAU / 6
    return mb.placed((x + math.cos(a) * r * APO * at, y + math.sin(a) * r * APO * at, z), a + math.pi / 2)


def thorns(mb, rnd, x, y, r, z0, z1, n, size=0.9):
    for _ in range(n):
        a = rnd.uniform(0, TAU)
        z = rnd.uniform(z0, z1)
        c, s = math.cos(a), math.sin(a)
        mb.cylinder((x + c * r * 0.7, y + s * r * 0.7, z), (x + c * (r + size * 0.7), y + s * (r + size * 0.7), z + size), 0.16 * size, 0.0, "obsidian_light", segments=4)


def splinters(mb, rnd, x0, x1, y0, y1, n, size=1.0):
    """Small shards that break out of the ground."""
    for _ in range(n):
        h = size * rnd.uniform(0.5, 1.3)
        p.crystal(mb, rnd.uniform(x0, x1), rnd.uniform(y0, y1), 0, 0.16 * size, h, rnd.choice(("obsidian", "obsidian_dark", "obsidian_light")), (rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3)))


def shrooms(mb, rnd, x0, x1, y0, y1, n, size=0.5):
    for _ in range(n):
        s = size * rnd.uniform(0.6, 1.3)
        p.mushroom(mb, rnd.uniform(x0, x1), rnd.uniform(y0, y1), 0, s, s * 0.45, rnd.choice(("cap", "violet_dark")), "stalk", None, 6, "violet")


def bridge(mb, a, b, w=0.5):
    """A thin walk between two shards, with a rail of needles."""
    p.beam(mb, a, b, w, "obsidian_light")
    n = 4
    for k in range(n + 1):
        u = k / n
        x, y, z = a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u, a[2] + (b[2] - a[2]) * u
        mb.cylinder((x, y, z + 0.1), (x, y, z + 0.75), 0.05, 0.0, "obsidian_dark", segments=4)


def floaters(mb, rig, x, y, z, r, n=4, size=0.5, name="shards"):
    name = rig.name(name)
    with mb.bone(name):
        for k in range(n):
            a = TAU * k / n
            p.shard(mb, x + math.cos(a) * r, y + math.sin(a) * r, z + 0.3 * (k % 2), size * 0.22, size, "violet")
    p.bob(mb, rig, name, (x, y, z), 0.15, 8.0, "float")


def house(level):
    def build():
        mb = p.begin()
        rig = p.Rig()
        rnd = p.random.Random(70 + level)
        if level == 1:
            top = shard_tower(mb, 0, 0.2, 1.7, 2.6, 3.4, lean=(0.3, 0.1))
            with on_shard(mb, 0, 0.2, 1.7 * 1.05):
                p.pointed_door(mb, 0, 0, 0.9, 1.9)
            with on_shard(mb, 0, 0.2, 1.7, 1, 0, 0.98):
                p.slit(mb, 0, 1.5, 0.14, 0.8)
            thorns(mb, rnd, 0, 0.2, 1.5, 1.6, 2.6, 3, 0.7)
            splinters(mb, rnd, -1.9, -1.2, -1.6, 0.5, 3, 0.8)
            shrooms(mb, rnd, 1.1, 1.9, -1.8, -1.2, 3, 0.45)
            p.arc(mb, [(-1.5, -1.6, 0), (-1.5, -1.6, 1.6), (-1.3, -1.6, 2.1), (-1.0, -1.6, 2.2)], 0.05, "obsidian_light", 0.6)
            p.hang_lantern(mb, rig, -1.0, -1.6, 2.2, 0.15, "shard", "violet", size=0.8)
        elif level == 2:
            shard_tower(mb, -0.7, 0.4, 2.0, 3.2, 4.6, lean=(-0.3, 0.2))
            shard_tower(mb, 1.7, 0.7, 1.15, 2.2, 3.0, lean=(0.4, 0.0))
            with on_shard(mb, -0.7, 0.4, 2.0 * 1.05):
                p.pointed_door(mb, 0, 0, 1.0, 2.1)
            for k in (1, 5):
                with on_shard(mb, -0.7, 0.4, 2.0, k, 0, 0.96):
                    p.slit(mb, 0, 1.8, 0.16, 1.1)
            with on_shard(mb, 1.7, 0.7, 1.15, 0, 0, 0.98):
                p.slit(mb, 0, 1.3, 0.14, 0.9)
            hexcyl(mb, -0.7, 0.4, 3.25, 3.4, 2.5, 2.6, "obsidian_light")      # A collar to stand on.
            for k in range(6):
                a = TAU * k / 6
                mb.cylinder((-0.7 + math.cos(a) * 2.5, 0.4 + math.sin(a) * 2.5, 3.4), (-0.7 + math.cos(a) * 2.6, 0.4 + math.sin(a) * 2.6, 4.2), 0.07, 0.0, "obsidian_dark", segments=4)
            thorns(mb, rnd, -0.7, 0.4, 1.7, 4.0, 5.5, 4, 0.8)
            splinters(mb, rnd, -2.8, -2.0, -1.8, 0.5, 4, 0.9)
            shrooms(mb, rnd, 0.8, 2.6, -2.2, -1.4, 5, 0.5)
            floaters(mb, rig, -1.0, 0.6, 8.6, 0.5, 3, 0.5)
        else:
            top = shard_tower(mb, -0.4, 0.6, 2.2, 4.2, 6.0, lean=(0.2, 0.3))
            shard_tower(mb, -2.9, -0.4, 1.2, 2.6, 3.6, lean=(-0.5, 0.0))
            shard_tower(mb, 2.5, 0.2, 1.4, 3.4, 4.4, lean=(0.5, 0.1))
            shard_tower(mb, 1.2, 2.0, 1.0, 5.0, 3.6, lean=(0.2, 0.4))
            with on_shard(mb, -0.4, 0.6, 2.2 * 1.05):
                p.pointed_door(mb, 0, 0.3, 1.2, 2.4)
                p.stairs(mb, 0, -0.9, 0, 0.3, 1.8, 0.9, "obsidian_dark", 0.15)
            for k in (1, 5):
                with on_shard(mb, -0.4, 0.6, 2.2, k, 0, 0.95):
                    p.slit(mb, -0.3, 2.2, 0.16, 1.3)
                    p.slit(mb, 0.3, 2.9, 0.16, 1.0)
            with on_shard(mb, -2.9, -0.4, 1.2, 0, 0, 0.98):
                p.slit(mb, 0, 1.5, 0.14, 1.0)
            with on_shard(mb, 2.5, 0.2, 1.4, 0, 0, 0.97):
                p.slit(mb, 0, 1.4, 0.14, 1.0)
                p.slit(mb, 0, 2.7, 0.14, 0.6)
            hexcyl(mb, -0.4, 0.6, 4.3, 4.45, 2.7, 2.85, "obsidian_light")     # The balcony ring.
            for k in range(12):
                a = TAU * k / 12
                mb.cylinder((-0.4 + math.cos(a) * 2.7, 0.6 + math.sin(a) * 2.7, 4.45), (-0.4 + math.cos(a) * 2.8, 0.6 + math.sin(a) * 2.8, 5.3), 0.07, 0.0, "obsidian_dark", segments=4)
            bridge(mb, (-2.9, -0.4, 2.7), (-1.6, 0.2, 3.3))
            bridge(mb, (2.5, 0.2, 3.5), (1.2, 0.5, 3.9))
            with on_shard(mb, -0.4, 0.6, 2.2, 0, 4.45, 0.82):
                p.pointed_door(mb, 0, 0, 0.7, 1.5)
            thorns(mb, rnd, -0.4, 0.6, 1.8, 5.0, 7.0, 5, 0.9)
            thorns(mb, rnd, 2.5, 0.2, 1.1, 3.6, 4.6, 3, 0.7)
            for sx in (-1, 1):
                p.flag(mb, rig, -0.4 + sx * 2.6, 0.6 - 1.2, 4.45, 2.4, 1.2, 0.5, "violet_dark", "violet", pole_mat="obsidian_light", knob="violet")
            splinters(mb, rnd, -3.8, 3.6, -2.6, -1.9, 5, 0.9)
            shrooms(mb, rnd, 0.8, 3.4, -2.6, -1.6, 5, 0.55)
            floaters(mb, rig, -0.2, 0.9, top + 0.6, 0.7, 4, 0.6)
        p.finish(mb, "race_dark_elf_house_%d" % level, rig)
    return build


def center():
    """The obsidian court: a great needle in a ring of six, 13 x 13 m."""
    mb = p.begin()
    rig = p.Rig()
    rnd = p.random.Random(77)
    cy = 0.5
    mb.cylinder((0, cy, 0), (0, cy, 0.25), 6.2, 6.0, "obsidian_dark", segments=12)
    mb.cylinder((0, cy, 0.25), (0, cy, 0.4), 5.4, 5.3, "obsidian", segments=12)
    p.ring(mb, 0, cy, 0.42, 4.6, 0.12, "violet", 12)
    top = shard_tower(mb, 0, cy, 2.8, 7.0, 9.5, lean=(0.0, 0.3))
    with on_shard(mb, 0, cy, 2.8 * 1.05, 0, 0.4):
        p.pointed_door(mb, 0, 0.4, 1.8, 3.6)
        p.stairs(mb, 0, -1.2, 0, 0.4, 2.6, 1.2, "obsidian_light", 0.14)
    for k in range(1, 6):
        with on_shard(mb, 0, cy, 2.8, k, 0, 0.93):
            p.slit(mb, -0.5, 3.0, 0.2, 2.0)
            p.slit(mb, 0.5, 4.6, 0.2, 1.6)
            p.slit(mb, 0.0, 1.6, 0.16, 0.9)
    hexcyl(mb, 0, cy, 7.1, 7.3, 3.3, 3.5, "obsidian_light")
    for k in range(12):
        a = TAU * k / 12
        mb.cylinder((math.cos(a) * 3.3, cy + math.sin(a) * 3.3, 7.3), (math.cos(a) * 3.45, cy + math.sin(a) * 3.45, 8.3), 0.09, 0.0, "obsidian_dark", segments=4)
    thorns(mb, rnd, 0, cy, 2.2, 8.5, 12.0, 7, 1.3)
    for k in range(6):                                                          # The ring of lesser needles and their bridges.
        a = TAU * k / 6
        x, y = math.cos(a) * 4.9, cy + math.sin(a) * 4.9
        hw = 3.2 + 1.3 * (k % 3)
        shard_tower(mb, x, y, 1.0, hw, 3.2 + 0.5 * (k % 2), lean=(math.cos(a) * 0.5, math.sin(a) * 0.5))
        bridge(mb, (x * 0.85, cy + (y - cy) * 0.85, hw - 0.4), (x * 0.45, cy + (y - cy) * 0.45, hw + 0.4), 0.4)
        with on_shard(mb, x, y, 1.0, 0, 0, 0.98):
            p.slit(mb, 0, 1.7, 0.2, 1.3, "violet")
            p.slit(mb, 0, hw - 0.7, 0.3, 0.3, "violet")
        if k in (4, 5):                                                         # The two at the front carry the banners.
            p.flag(mb, rig, x, y - 1.3, 0.4, 4.2, 1.6, 0.7, "violet_dark", "violet", pole_mat="obsidian_light", knob="violet")
    with mb.bone("heart"):                                                      # The heart crystal over the tip.
        p.shard(mb, 0, cy + 0.3, top + 1.6, 0.6, 2.0, "violet")
        p.ring(mb, 0, cy + 0.3, top + 1.6, 1.1, 0.07, "obsidian_light", 10)
    p.bob(mb, rig, "heart", (0, cy + 0.3, top + 1.6), 0.2, 8.0, "float")
    floaters(mb, rig, 0, cy + 0.3, top + 1.2, 1.9, 5, 0.7)
    for sx in (-1, 1):                                                          # Pools of violet light by the stair.
        mb.cylinder((sx * 2.6, cy - 4.4, 0.25), (sx * 2.6, cy - 4.4, 0.5), 0.9, 0.8, "obsidian_light", segments=8)
        mb.cylinder((sx * 2.6, cy - 4.4, 0.4), (sx * 2.6, cy - 4.4, 0.52), 0.65, 0.65, "violet", segments=8)
    shrooms(mb, rnd, -5.5, 5.5, -5.6, -4.9, 8, 0.6)
    splinters(mb, rnd, -6.0, 6.0, 4.6, 6.0, 8, 1.2)
    p.finish(mb, "race_dark_elf_center", rig)


def workshop():
    """The cap workshop: benches and a cauldron under a giant mushroom."""
    mb = p.begin()
    rig = p.Rig()
    rnd = p.random.Random(78)
    mb.cylinder((0, 0.3, 0), (0, 0.3, 0.2), 2.9, 2.8, "obsidian_dark", segments=10)
    mb.cylinder((0, 0.5, 0.2), (0.2, 0.7, 4.2), 0.9, 0.6, "stalk", segments=8)   # The stalk, with a door in it.
    mb.cylinder((0.12, 0.62, 2.7), (0.14, 0.64, 2.9), 0.95, 0.75, "stalk_dark", segments=8)
    with mb.placed((0, -0.3, 0.2), 0):
        p.pointed_door(mb, 0, 0, 0.7, 1.6, "stalk_dark", "violet")
    p.lathe(mb, 0.2, 0.7, 4.0, [(3.3, 0), (3.0, 0.5), (2.2, 1.0), (1.1, 1.4), (0.0, 1.55)], ("cap", "cap_light", "cap", "cap_light"), 10)
    mb.cylinder((0.2, 0.7, 3.6), (0.2, 0.7, 4.0), 2.4, 3.3, "cap_light", segments=10)
    for k in range(10):                                                         # Gills that glow.
        a = TAU * k / 10
        p.beam(mb, (0.2 + math.cos(a) * 0.7, 0.7 + math.sin(a) * 0.7, 3.62), (0.2 + math.cos(a) * 2.6, 0.7 + math.sin(a) * 2.6, 3.84), 0.07, "violet")
    for k in range(6):
        a = TAU * k / 6 + 0.4
        mb.sphere((0.2 + math.cos(a) * 1.9, 0.7 + math.sin(a) * 1.9, 4.95), 0.34, "cap_spot", segments=6, rings=4, scale=(1, 1, 0.4))
    mb.box((-1.7, -0.9, 0.95), (1.4, 0.7, 0.08), "obsidian_light")              # The bench of vials.
    for sx in (-0.55, 0.55):
        mb.box((-1.7 + sx, -0.9, 0.57), (0.1, 0.6, 0.75), "obsidian")
    for k in range(4):
        mb.sphere((-2.2 + 0.33 * k, -0.9, 1.08), 0.09, ("violet", "e_blue", "cap_spot", "violet_dark")[k], segments=6, rings=4)
        mb.cylinder((-2.2 + 0.33 * k, -0.9, 1.13), (-2.2 + 0.33 * k, -0.9, 1.26), 0.03, 0.035, "web", segments=5)
    mb.sphere((1.7, -1.0, 0.65), 0.55, "o_iron", segments=8, rings=6, scale=(1, 1, 0.85))    # The cauldron.
    mb.cylinder((1.7, -1.0, 0.82), (1.7, -1.0, 0.95), 0.52, 0.56, "o_iron", segments=8)
    mb.cylinder((1.7, -1.0, 0.9), (1.7, -1.0, 0.97), 0.48, 0.48, "violet", segments=8)
    with mb.bone("bubbles"):
        for k in range(4):
            mb.sphere((1.7 + 0.2 * math.cos(k * 1.7), -1.0 + 0.2 * math.sin(k * 1.7), 1.0 + 0.04 * (k % 2)), 0.08 + 0.02 * (k % 2), "cap_spot", segments=5, rings=3)
    p.bob(mb, rig, "bubbles", (1.7, -1.0, 1.0), 0.04, 3.0, "brew")
    for k in range(3):
        a = TAU * k / 3 + 0.3
        p.beam(mb, (1.7 + math.cos(a) * 0.5, -1.0 + math.sin(a) * 0.5, 0.2), (1.7 + math.cos(a) * 0.3, -1.0 + math.sin(a) * 0.3, 0.5), 0.07, "o_iron")
    for sx in (-1, 1):                                                          # A web frame where silk is drawn.
        p.beam(mb, (2.0 + sx * 0.6, 1.6, 0.2), (2.0 + sx * 0.5, 1.6, 2.2), 0.08, "obsidian_light")
    p.beam(mb, (1.5, 1.6, 2.2), (2.5, 1.6, 2.2), 0.08, "obsidian_light")
    for k in range(5):
        p.beam(mb, (1.5 + 0.25 * k, 1.6, 0.4), (2.5 - 0.25 * k, 1.6, 2.15), 0.02, "web")
    mb.box((2.0, 1.6, 1.3), (0.9, 0.03, 1.5), "web")
    for a in (0.6, 2.3, 3.9):
        p.hang_lantern(mb, rig, 0.2 + math.cos(a) * 2.9, 0.7 + math.sin(a) * 2.9, 3.7, 0.3, "shard", "violet", size=0.7)
    shrooms(mb, rnd, -2.8, -1.4, 0.8, 2.4, 4, 0.8)
    shrooms(mb, rnd, 0.6, 2.6, -2.6, -2.0, 3, 0.4)
    p.finish(mb, "race_dark_elf_workshop", rig)


def storehouse():
    """The claw vault: a six-sided strongroom under four ribs of obsidian."""
    mb = p.begin()
    rig = p.Rig()
    rnd = p.random.Random(79)
    r, h = 2.3, 2.4
    cy = 0.4
    hexcyl(mb, 0, cy, 0, 0.4, r * 1.2, r * 1.06, "obsidian_dark")
    hexcyl(mb, 0, cy, 0.4, h, r * 1.04, r * 0.94, "obsidian")
    hexcyl(mb, 0, cy, h, h + 0.2, r * 1.02, r * 1.02, "obsidian_light")
    hexcyl(mb, 0, cy, h + 0.2, h + 1.3, r * 0.98, r * 0.3, "obsidian_dark")
    p.crystal(mb, 0, cy, h + 1.2, 0.3, 1.2, "violet")
    for k in range(4):                                                          # The claws.
        a = TAU * k / 4 + TAU / 8
        c, s = math.cos(a), math.sin(a)
        p.arc(mb, [(c * 3.0, cy + s * 3.0, 0), (c * 3.1, cy + s * 3.1, 2.0), (c * 2.5, cy + s * 2.5, 3.6), (c * 1.4, cy + s * 1.4, 4.6), (c * 0.7, cy + s * 0.7, 4.7)], 0.24, "obsidian_light", 0.2)
        name = rig.name("cocoon")
        with mb.bone(name):                                                     # Stores wrapped in silk hang from them.
            mb.cylinder((c * 2.75, cy + s * 2.75, 3.2), (c * 2.75, cy + s * 2.75, 2.7), 0.015, 0.015, "web", segments=4)
            mb.sphere((c * 2.75, cy + s * 2.75, 2.35), 0.3, "web", segments=6, rings=5, scale=(1, 1, 1.5))
        p.sway(mb, rig, name, (c * 2.75, cy + s * 2.75, 3.2), 6.0, 4.0, "sway", (-s, c, 0), (c * 2.75, cy + s * 2.75, 2.3))
    with on_shard(mb, 0, cy, r * 1.0):
        p.pointed_door(mb, 0, 0, 1.3, 2.0, "obsidian_light", "o_iron")
        mb.cylinder((0, -0.14, 1.0), (0, -0.22, 1.0), 0.2, 0.2, "violet", segments=6)
    for k in (1, 5):
        with on_shard(mb, 0, cy, r, k, 0, 0.97):
            p.slit(mb, 0, 1.5, 0.5, 0.14)
    for x, y in ((1.7, -2.3), (2.3, -1.8), (-1.9, -2.3)):
        mb.box((x, y, 0.3), (0.6, 0.6, 0.6), "obsidian_light")
        mb.box((x, y, 0.62), (0.66, 0.66, 0.06), "violet_dark")
    mb.sphere((-2.5, -1.7, 0.3), 0.36, "web", segments=6, rings=5, scale=(1, 1, 0.8))
    shrooms(mb, rnd, -3.0, -2.2, -0.8, 1.2, 3, 0.5)
    splinters(mb, rnd, 2.2, 3.0, 0.2, 2.0, 3, 0.8)
    p.finish(mb, "race_dark_elf_storehouse", rig)


def mushroom_cave():
    """The mushroom farm: beds of glowing caps before a cave mouth, 8 x 8 m."""
    mb = p.begin()
    rig = p.Rig()
    rnd = p.random.Random(75)
    for x, y, r, zs, mat in ((-1.7, 2.3, 2.5, 1.2, "obsidian"), (1.7, 2.4, 2.7, 1.3, "obsidian_dark"), (0, 2.8, 2.5, 1.7, "obsidian")):
        mb.sphere((x, y, 0), r, mat, segments=7, rings=5, scale=(1, 0.75, zs))
    p.tbox(mb, 0, 1.0, 0, 3.3, 3.8, 1.5, 2.2, 1.3, "obsidian_dark")               # The mouth.
    with mb.placed((0, 0.3, 0), 0):
        p.pointed_door(mb, 0, 0, 2.2, 2.6, "obsidian_light", "dark")
        mb.box((0, -0.17, 0.2), (1.9, 0.06, 0.4), "violet_dark")
        mb.box((0, -0.19, 0.1), (1.3, 0.06, 0.2), "violet")
    for sx in (-1, 1):
        p.crystal(mb, sx * 1.9, 0.5, 0, 0.3, 3.4, "obsidian_light", (sx * 0.12, 0.0), 6)
        p.crystal(mb, sx * 2.3, 0.3, 0, 0.2, 2.0, "obsidian", (sx * 0.25, -0.1), 6)
    p.mushroom(mb, -3.0, 0.9, 0, 3.4, 1.4, "cap", "stalk", "cap_spot", 9, "violet")
    p.mushroom(mb, 3.1, 1.2, 0, 2.6, 1.1, "violet_dark", "stalk", "cap_spot", 9, "cap_light")
    sizes = (1.0, 0.65, 0.36)
    for row, y in enumerate((-0.9, -2.0, -3.1)):                                # Three beds: grown, growing, just sown.
        mb.box((0, y, 0.11), (6.4, 0.8, 0.22), "soil")
        for sy in (-1, 1):
            mb.box((0, y + sy * 0.44, 0.14), (6.6, 0.1, 0.28), "obsidian_light")
        for k in range(8):
            x = -2.8 + 0.8 * k + rnd.uniform(-0.1, 0.1)
            s = sizes[row] * rnd.uniform(0.8, 1.2)
            p.mushroom(mb, x, y + rnd.uniform(-0.12, 0.12), 0.2, s, s * 0.42, ("cap", "violet_dark", "cap_light")[(k + row) % 3], "stalk", "cap_spot" if row == 0 else None, 7, "violet")
    mb.cylinder((3.5, -2.0, 0), (3.5, -2.0, 0.45), 0.34, 0.42, "sisal", segments=8)   # A basket of the day's picking.
    for k in range(5):
        mb.sphere((3.5 + 0.16 * math.cos(k * 1.3), -2.0 + 0.16 * math.sin(k * 1.3), 0.5), 0.15, "cap" if k % 2 else "cap_light", segments=6, rings=3, scale=(1, 1, 0.6))
    with mb.bone("spores"):                                                     # Spores drift over the beds.
        for k in range(9):
            mb.sphere((rnd.uniform(-2.8, 2.8), rnd.uniform(-3.2, -0.6), rnd.uniform(1.3, 2.4)), 0.05, "cap_spot", segments=4, rings=3)
    rig.bone("spores", (0, -2.0, 1.8), (0, -2.0, 2.3), None)
    rig.add("float", 8.0, lambda t: ({"spores": [(p.kit.Z, 8.0 * math.sin(TAU * t))]}, {"spores": (0.15 * math.sin(TAU * t), 0, 0.2 * math.sin(TAU * 2 * t))}))
    for sx in (-1, 1):
        p.arc(mb, [(sx * 3.6, -3.4, 0), (sx * 3.6, -3.4, 1.7), (sx * 3.4, -3.4, 2.2), (sx * 3.1, -3.4, 2.3)], 0.05, "obsidian_light", 0.6)
        p.hang_lantern(mb, rig, sx * 3.1, -3.4, 2.3, 0.15, "shard", "violet", size=0.8)
    splinters(mb, rnd, -3.9, 3.9, 3.4, 3.9, 6, 1.0)
    p.finish(mb, "race_dark_elf_mushroom_cave", rig)


def tower():
    """A watch needle: a thin shard with a ring to stand on and an eye of crystal."""
    mb = p.begin()
    rig = p.Rig()
    rnd = p.random.Random(76)
    top = shard_tower(mb, 0, 0, 1.3, 7.5, 4.5, lean=(0.0, 0.2))
    with on_shard(mb, 0, 0, 1.3 * 1.05):
        p.pointed_door(mb, 0, 0, 0.9, 2.0)
    for k, z in ((0, 3.4), (1, 4.6), (5, 4.6), (0, 5.8)):
        with on_shard(mb, 0, 0, 1.3, k, 0, 0.93 - 0.02 * z / 3):
            p.slit(mb, 0, z, 0.16, 0.8)
    hexcyl(mb, 0, 0, 7.6, 7.75, 1.9, 2.1, "obsidian_light")
    for k in range(12):
        a = TAU * k / 12
        mb.cylinder((math.cos(a) * 1.95, math.sin(a) * 1.95, 7.75), (math.cos(a) * 2.05, math.sin(a) * 2.05, 8.6), 0.07, 0.0, "obsidian_dark", segments=4)
    thorns(mb, rnd, 0, 0, 0.9, 8.4, 10.0, 4, 0.8)
    with mb.bone("eye"):                                                        # The eye turns and sees in the dark.
        p.shard(mb, 0, 0.2, top + 1.0, 0.3, 1.0, "violet")
        p.ring(mb, 0, 0.2, top + 1.0, 0.6, 0.05, "obsidian_light", 8)
    p.bob(mb, rig, "eye", (0, 0.2, top + 1.0), 0.1, 6.0, "float")
    p.flag(mb, rig, 1.6, -1.0, 7.75, 2.2, 1.1, 0.5, "violet_dark", "violet", pole_mat="obsidian_light", knob="violet")
    splinters(mb, rnd, -1.9, -1.2, -1.5, 1.0, 3, 0.8)
    shrooms(mb, rnd, 1.0, 1.9, -1.8, -1.2, 3, 0.4)
    p.finish(mb, "race_dark_elf_tower", rig)


def shrine():
    """The weaver's altar: a slab under an arch of two shards strung with web, 4 x 4 m."""
    mb = p.begin()
    rig = p.Rig()
    rnd = p.random.Random(72)
    hexcyl(mb, 0, 0, 0, 0.25, 2.0, 1.9, "obsidian_dark")
    p.ring(mb, 0, 0, 0.27, 1.5, 0.08, "violet", 6)
    for sx in (-1, 1):                                                          # Two shards lean together.
        p.crystal(mb, sx * 1.3, 0.6, 0.2, 0.34, 4.2, "obsidian", (-sx * 0.27, 0.0), 6)
        p.crystal(mb, sx * 1.7, 0.9, 0.2, 0.22, 2.2, "obsidian_light", (sx * 0.1, 0.1), 5)
    for k in range(5):                                                          # The web between them.
        z = 1.5 + 0.5 * k
        w = 1.25 - 0.27 * (z - 0.2) / 4.2 * 4.2 / 1.0 * 0.23
        p.beam(mb, (-w, 0.6, z), (w, 0.6, z - 0.12 if k % 2 else z + 0.1), 0.02, "web")
    for x in (-0.5, 0, 0.5):
        p.beam(mb, (x, 0.6, 1.4), (x * 0.3, 0.6, 3.7), 0.02, "web")
    mb.box((0, 0.0, 0.6), (1.5, 0.8, 0.7), "obsidian")                           # The altar slab.
    mb.box((0, 0.0, 1.0), (1.8, 1.0, 0.12), "obsidian_light")
    mb.box((0, -0.42, 0.6), (0.9, 0.04, 0.1), "violet")
    for sx in (-1, 1):
        mb.cylinder((sx * 0.7, 0, 1.06), (sx * 0.7, 0, 1.3), 0.04, 0.035, "stalk", segments=5)
        mb.cylinder((sx * 0.7, 0, 1.3), (sx * 0.7, 0, 1.42), 0.03, 0.0, "violet", segments=4)
    mb.cylinder((0, 0, 1.06), (0, 0, 1.14), 0.24, 0.3, "o_iron", segments=8)
    with mb.bone("gem"):
        p.shard(mb, 0, 0.0, 1.9, 0.22, 0.7, "violet")
        for k in range(3):
            a = TAU * k / 3
            p.shard(mb, math.cos(a) * 0.5, math.sin(a) * 0.5, 1.9, 0.06, 0.24, "cap_spot")
    p.bob(mb, rig, "gem", (0, 0, 1.9), 0.1, 6.0, "float")
    shrooms(mb, rnd, -1.7, -1.0, -1.6, -1.0, 3, 0.4)
    shrooms(mb, rnd, 1.0, 1.7, -1.6, -1.0, 3, 0.4)
    p.finish(mb, "race_dark_elf_shrine", rig)


def market_stall():
    """A stall under a mushroom cap, 3 x 3 m."""
    mb = p.begin()
    rig = p.Rig()
    mb.cylinder((0, 0.2, 0), (0.1, 0.3, 2.5), 0.34, 0.24, "stalk", segments=8)
    p.lathe(mb, 0.1, 0.3, 2.4, [(1.7, 0), (1.5, 0.3), (1.0, 0.6), (0.4, 0.82), (0.0, 0.9)], ("cap", "cap_light", "cap", "cap_light"), 9)
    mb.cylinder((0.1, 0.3, 2.2), (0.1, 0.3, 2.4), 1.2, 1.7, "violet", segments=9)
    for k in range(4):
        a = TAU * k / 4 + 0.5
        mb.sphere((0.1 + math.cos(a) * 1.0, 0.3 + math.sin(a) * 1.0, 2.88), 0.18, "cap_spot", segments=5, rings=3, scale=(1, 1, 0.4))
    mb.box((0, -0.7, 0.45), (2.2, 0.5, 0.9), "obsidian")                         # The counter.
    mb.box((0, -0.7, 0.93), (2.4, 0.62, 0.08), "obsidian_light")
    mb.box((0, -0.96, 0.5), (1.2, 0.03, 0.08), "violet")
    for k in range(4):
        mb.sphere((-0.9 + 0.3 * k, -0.7, 1.06), 0.09, ("violet", "e_blue", "cap_spot", "violet_dark")[k], segments=6, rings=4)
        mb.cylinder((-0.9 + 0.3 * k, -0.7, 1.12), (-0.9 + 0.3 * k, -0.7, 1.24), 0.03, 0.035, "web", segments=5)
    for k in range(3):                                                          # Bolts of silk.
        mb.cylinder((0.3, -0.85 + 0.15 * k, 1.05), (1.0, -0.85 + 0.15 * k, 1.05), 0.08, 0.08, "web" if k % 2 else "cap_light", segments=6)
    p.mushroom(mb, 1.2, 0.9, 0, 0.7, 0.3, "violet_dark", "stalk", None, 6, "violet")
    p.mushroom(mb, -1.1, 0.8, 0, 0.5, 0.22, "cap", "stalk", None, 6, "violet")
    for a in (-2.2, -0.9):
        p.hang_lantern(mb, rig, 0.1 + math.cos(a) * 1.5, 0.3 + math.sin(a) * 1.5, 2.3, 0.25, "shard", "violet", size=0.7)
    p.finish(mb, "race_dark_elf_market_stall", rig)


def well():
    """A well of black glass whose water glows, under three claws."""
    mb = p.begin()
    rig = p.Rig()
    hexcyl(mb, 0, 0, 0, 0.2, 1.5, 1.4, "obsidian_dark")
    hexcyl(mb, 0, 0, 0.2, 0.95, 1.05, 0.95, "obsidian")
    hexcyl(mb, 0, 0, 0.9, 1.02, 1.05, 1.05, "obsidian_light")
    hexcyl(mb, 0, 0, 0.9, 1.04, 0.72, 0.72, "violet")
    for k in range(3):
        a = TAU * k / 3 + math.pi / 2
        c, s = math.cos(a), math.sin(a)
        p.arc(mb, [(c * 1.0, s * 1.0, 0.9), (c * 1.15, s * 1.15, 2.0), (c * 0.7, s * 0.7, 2.9), (c * 0.15, s * 0.15, 3.1)], 0.14, "obsidian_light", 0.3)
    with mb.bone("pail"):
        mb.cylinder((0, 0, 3.05), (0, 0, 2.0), 0.012, 0.012, "obsidian_light", segments=4)
        mb.cylinder((0, 0, 1.6), (0, 0, 2.0), 0.13, 0.18, "o_iron", segments=6)
        mb.cylinder((0, 0, 1.96), (0, 0, 2.01), 0.15, 0.15, "violet", segments=6)
    p.sway(mb, rig, "pail", (0, 0, 3.05), 5.0, 3.0, "sway", (1, 0, 0), (0, 0, 1.8))
    p.mushroom(mb, 1.2, -0.9, 0, 0.5, 0.22, "cap", "stalk", None, 6, "violet")
    p.mushroom(mb, -1.25, -0.7, 0, 0.36, 0.16, "violet_dark", "stalk", None, 6, "violet")
    p.finish(mb, "race_dark_elf_well", rig)


def great_crystal():
    """A crystal that lights the street, with shards that circle it."""
    mb = p.begin()
    rig = p.Rig()
    rnd = p.random.Random(73)
    hexcyl(mb, 0, 0, 0, 0.3, 1.2, 1.0, "obsidian_dark")
    hexcyl(mb, 0, 0, 0.3, 0.5, 0.8, 0.75, "obsidian")
    p.crystal(mb, 0, 0, 0.45, 0.36, 3.0, "violet", (0.05, 0.03), 6)
    for k in range(5):
        a = TAU * k / 5 + 0.4
        p.crystal(mb, math.cos(a) * 0.42, math.sin(a) * 0.42, 0.45, rnd.uniform(0.13, 0.2), rnd.uniform(0.8, 1.7), ("violet_dark", "violet", "cap_light")[k % 3], (math.cos(a) * 0.35, math.sin(a) * 0.35), 5)
    splinters(mb, rnd, -1.0, 1.0, -1.0, 1.0, 5, 0.5)
    floaters(mb, rig, 0, 0, 2.6, 0.9, 4, 0.45, "orbit")
    p.finish(mb, "race_dark_elf_great_crystal", rig)


MODELS = {
    "race_dark_elf_shrine": shrine, "race_dark_elf_market_stall": market_stall, "race_dark_elf_well": well, "race_dark_elf_great_crystal": great_crystal,
    "race_dark_elf_mushroom_cave": mushroom_cave, "race_dark_elf_tower": tower,
    "race_dark_elf_house_1": house(1), "race_dark_elf_house_2": house(2), "race_dark_elf_house_3": house(3),
    "race_dark_elf_center": center, "race_dark_elf_workshop": workshop, "race_dark_elf_storehouse": storehouse,
}
