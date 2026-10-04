"""Orcs: raw logs, patched hides, tusks and bone, sharpened stakes, red and
black banners, a fire in front of everything."""

import math

import rparts as p
from rparts import TAU, solid

HIDES = ("hide", "hide_dark", "hide", "hide_light")


def log_walls(mb, cx, cy, z0, w, d, h, r=0.19, door=None):
    """Stacked raw logs that cross at the corners. `door` = (side, width)
    leaves a dark doorway on that wall."""
    mb.box((cx, cy, z0 + h / 2), (w - 0.15, d - 0.15, h), "pole_dark")
    n = max(1, round(h / (2 * r * 0.9)))
    step = h / n
    for i in range(n):
        z = z0 + (i + 0.5) * step
        for y in (cy - d / 2, cy + d / 2):
            p.log(mb, (cx - w / 2 - 0.35, y, z), (cx + w / 2 + 0.35, y, z), r)
        zz = min(z + step / 2, z0 + h - r * 0.6)
        for x in (cx - w / 2, cx + w / 2):
            p.log(mb, (x, cy - d / 2 - 0.35, zz), (x, cy + d / 2 + 0.35, zz), r)


def doorway(mb, x=0.0, w=1.1, h=1.7, flap=True):
    """A dark doorway with a hide flap pulled aside (face frame)."""
    mb.box((x, -0.16, h / 2), (w, 0.12, h), "o_black")
    for s in (-1, 1):
        p.log(mb, (x + s * (w / 2 + 0.12), -0.22, 0), (x + s * (w / 2 + 0.12), -0.22, h + 0.2), 0.13)
    p.log(mb, (x - w / 2 - 0.4, -0.22, h + 0.25), (x + w / 2 + 0.4, -0.22, h + 0.25), 0.14)
    if flap:
        solid(mb, [(x - w / 2, -0.26, h), (x - w / 2 + w * 0.45, -0.26, h), (x - w / 2 + w * 0.15, -0.3, 0.3), (x - w / 2, -0.3, 0.1)], (0, -0.04, 0), "hide_light")


def hide_roof(mb, cx, cy, z, w, d, rise, axis="x", rnd=None, over=0.4, patches=5, smoke_hole=False):
    """A steep roof of patched hides over a ridge log that sticks out, with
    crossed tusks at both ends."""
    if axis == "y":
        with mb.placed((cx, cy, 0), math.pi / 2):
            return hide_roof(mb, 0, 0, z, d, w, rise, "x", rnd, over, patches, smoke_hole)
    top = p.gable(mb, cx, cy, z, w, d, rise, HIDES, rows=4, over=over, end_over=0.25, fill="hide_dark", thick=0.08, ridge_mat="hide_dark")
    p.log(mb, (cx - w / 2 - 0.9, cy, top + 0.12), (cx + w / 2 + 0.9, cy, top + 0.12), 0.16)
    slope = rise / (d / 2)
    for k in range(patches):                                                    # Patches sewn on.
        side = -1 if k % 2 else 1
        t = rnd.uniform(0.2, 0.75)
        x = cx + rnd.uniform(-w / 2 + 0.5, w / 2 - 0.5)
        y = cy + side * (d / 2) * (1 - t)
        zz = z + rise * t
        s = rnd.uniform(0.35, 0.6)
        solid(mb, [(x - s, y + side * s * 0.4, zz - s * 0.4 * slope + 0.1), (x + s, y + side * s * 0.4, zz - s * 0.4 * slope + 0.1),
                   (x + s * 0.8, y - side * s * 0.4, zz + s * 0.4 * slope + 0.1), (x - s * 0.9, y - side * s * 0.4, zz + s * 0.4 * slope + 0.1)], (0, 0, 0.05), "hide_light" if k % 3 else "hide_dark")
    for s in (-1, 1):                                                           # Rafters cross above the ridge, with tusks.
        x = cx + s * (w / 2 + 0.2)
        for side in (-1, 1):
            p.beam(mb, (x, cy + side * (d / 2 + over), z - 0.3), (x, cy - side * 0.7, top + 0.75), 0.13, "pole_dark")
            p.tusk(mb, x + s * 0.12, cy + side * 0.55, top + 0.1, 0.9, 0.0, side * 0.5, 0.11)
    return top


def stakes(mb, rnd, x0, y0, x1, y1, n, out=(0, -1), h=1.3):
    """A row of sharpened stakes that lean outward."""
    for k in range(n):
        u = (k + 0.5) / n
        x, y = x0 + (x1 - x0) * u, y0 + (y1 - y0) * u
        hh = h * rnd.uniform(0.8, 1.2)
        lean = rnd.uniform(0.35, 0.6)
        mb.cylinder((x, y, 0), (x + out[0] * lean * hh, y + out[1] * lean * hh, hh * 0.75), 0.09, 0.07, "bark", segments=5)
        mb.cylinder((x + out[0] * lean * hh, y + out[1] * lean * hh, hh * 0.75), (x + out[0] * lean * hh * 1.3, y + out[1] * lean * hh * 1.3, hh), 0.07, 0.0, "log_end", segments=5)


def palisade(mb, rnd, x0, y0, x1, y1, h=2.4, r=0.17):
    n = max(1, round(math.hypot(x1 - x0, y1 - y0) / (r * 2)))
    for k in range(n + 1):
        u = k / n
        x, y = x0 + (x1 - x0) * u, y0 + (y1 - y0) * u
        hh = h * rnd.uniform(0.88, 1.1)
        mb.cylinder((x, y, 0), (x, y, hh), r, r * 0.92, "bark", segments=6)
        mb.cylinder((x, y, hh), (x, y, hh + 0.4), r * 0.92, 0.0, "log_end", segments=6)
    p.beam(mb, (x0, y0, h * 0.6), (x1, y1, h * 0.6), 0.1, "pole_dark")


def shield(mb, x, z, r=0.36, mat="o_red"):
    """A round shield hung on a face (face frame)."""
    mb.cylinder((x, -0.2, z), (x, -0.28, z), r, r, mat, segments=8)
    mb.cylinder((x, -0.28, z), (x, -0.34, z), r * 0.35, r * 0.2, "o_iron", segments=6)


def skull_pole(mb, x, y, h=2.6, horns=True):
    mb.cylinder((x, y, 0), (x, y, h), 0.07, 0.05, "pole_dark", segments=5)
    p.skull(mb, x, y, h + 0.12, 0.3, horns)


def bonfire(mb, rig, rnd, x, y, s=1.0):
    for k in range(7):
        a = TAU * k / 7
        p.rock(mb, x + math.cos(a) * 0.62 * s, y + math.sin(a) * 0.62 * s, 0.06, 0.16 * s, rnd, "o_stone" if k % 2 else "o_stone_dark")
    for k in range(4):
        a = TAU * k / 4 + 0.4
        p.log(mb, (x + math.cos(a) * 0.55 * s, y + math.sin(a) * 0.55 * s, 0.08), (x - math.cos(a) * 0.1 * s, y - math.sin(a) * 0.1 * s, 0.5 * s), 0.08 * s)
    p.flame(mb, rig, x, y, 0.1, 0.5 * s)


def drum(mb, x, y, r=0.6, h=0.9):
    mb.cylinder((x, y, 0.15), (x, y, 0.15 + h), r * 0.85, r, "hide_dark", segments=10)
    mb.cylinder((x, y, 0.13 + h), (x, y, 0.19 + h), r * 1.03, r * 1.03, "hide_light", segments=10)
    mb.cylinder((x, y, 0.3), (x, y, 0.4), r * 0.92, r * 0.92, "o_red", segments=10)
    for k in range(3):
        a = TAU * k / 3
        mb.cylinder((x + math.cos(a) * r * 0.9, y + math.sin(a) * r * 0.9, 0), (x + math.cos(a) * r * 0.8, y + math.sin(a) * r * 0.8, 0.3), 0.05, 0.05, "bone", segments=4)


def axe(mb, x, y, z, lean=0.0):
    """A crude axe standing on its handle."""
    p.beam(mb, (x, y, z), (x + lean, y, z + 1.4), 0.07, "pole_dark")
    mb.box((x + lean + 0.16, y, z + 1.2), (0.36, 0.05, 0.4), "o_iron")


def house(level):
    def build():
        mb = p.begin()
        rig = p.Rig()
        rnd = p.random.Random(80 + level)
        if level == 1:                                                          # A tent of hides over three pairs of poles.
            with mb.placed((0, 0.3, 0), math.pi / 2):
                top = p.gable(mb, 0, 0, 0.0, 3.2, 3.0, 2.7, HIDES, rows=4, over=0.0, end_over=0.0, fill=None, thick=0.08, ridge_mat="hide_dark")
                for x in (-1.6, 0, 1.6):
                    for side in (-1, 1):
                        p.beam(mb, (x, side * 1.6, 0), (x, -side * 0.45, 3.5), 0.12, "pole_dark")
                p.log(mb, (-2.1, 0, 2.82), (2.1, 0, 2.82), 0.12)
                p.prism_yz(mb, [(-1.45, 0), (1.45, 0), (0, 2.6)], 1.45, 1.55, "hide_dark")
                p.prism_yz(mb, [(-1.45, 0), (1.45, 0), (0, 2.6)], -1.55, -1.45, "hide_dark")
            mb.box((0, -1.27, 0.75), (0.9, 0.1, 1.5), "o_black")
            solid(mb, [(-0.45, -1.34, 1.5), (0.0, -1.34, 1.5), (-0.3, -1.38, 0.2), (-0.45, -1.38, 0.1)], (0, -0.04, 0), "hide_light")
            p.skull(mb, 0, -1.5, 2.2, 0.3)
            for side in (-1, 1):
                p.tusk(mb, side * 0.75, -1.5, 0, 1.7, -side * 0.35, 0.0, 0.11)
            stakes(mb, rnd, -1.9, 1.2, -1.9, -0.8, 3, (-1, 0), 1.0)
            bonfire(mb, rig, rnd, 1.4, -1.4, 0.55)
        elif level == 2:
            w, d, h = 3.8, 4.6, 1.3
            log_walls(mb, 0, 0.2, 0, w, d, h)
            hide_roof(mb, 0, 0.2, h, w, d, 2.5, "y", rnd)
            with p.face(mb, 0, 0.2, w, d, "front"):
                doorway(mb, 0, 1.0, 1.5)
                p.skull(mb, 0, -0.3, 2.35, 0.34)
                shield(mb, -1.25, 0.8, 0.34, "o_red")
                shield(mb, 1.25, 0.8, 0.34, "o_black")
            stakes(mb, rnd, -2.6, 1.8, -2.6, -1.4, 4, (-1, 0))
            stakes(mb, rnd, 2.6, 1.8, 2.6, -1.4, 4, (1, 0))
            skull_pole(mb, 2.2, -2.2, 2.4)
            bonfire(mb, rig, rnd, -1.7, -2.1, 0.6)
        else:
            w, d, h = 6.6, 4.2, 1.8
            cy = 0.4
            mb.box((0, cy, 0.2), (w + 0.5, d + 0.5, 0.4), "o_stone")
            for k in range(14):
                a = TAU * k / 14
                p.rock(mb, math.cos(a) * (w / 2 + 0.3), cy + math.sin(a) * (d / 2 + 0.3), 0.15, 0.3, rnd, "o_stone_dark")
            log_walls(mb, 0, cy, 0.4, w, d, h)
            top = hide_roof(mb, 0, cy, h + 0.4, w, d, 2.9, "x", rnd, patches=8)
            with p.face(mb, 0, cy, w, d, "front", 0.4):
                doorway(mb, 0, 1.3, 1.7)
                for sx in (-1, 1):
                    shield(mb, sx * 2.0, 1.0, 0.4, "o_red" if sx < 0 else "o_black")
                    shield(mb, sx * 2.9, 1.0, 0.34, "o_black" if sx < 0 else "o_red")
            for sx in (-1, 1):                                                  # A porch of two great tusks under a horned skull.
                p.tusk(mb, sx * 1.5, cy - d / 2 - 0.7, 0, 3.6, -sx * 1.1, 0.2, 0.24, n=6)
            p.skull(mb, 0, cy - d / 2 - 0.55, 3.75, 0.6)
            mb.box((0, cy - d / 2 - 0.5, 0.2), (2.0, 1.0, 0.4), "o_stone_dark")
            p.smoke(mb, rig, 1.4, cy, top + 0.3, 0.4)
            for sx in (-1, 1):
                p.flag(mb, rig, sx * (w / 2 + 0.9), cy - d / 2 - 0.3, 0, 4.4, 1.5, 0.8, "o_red", "o_black", knob="bone")
            stakes(mb, rnd, -3.9, cy + 2.2, -3.9, cy - 1.2, 5, (-1, 0))
            stakes(mb, rnd, 3.9, cy + 2.2, 3.9, cy - 1.2, 5, (1, 0))
            for k in range(3):
                axe(mb, 2.3 + 0.3 * k, cy - d / 2 - 0.45, 0.4, 0.1)
            bonfire(mb, rig, rnd, -2.6, -2.5, 0.7)
            drum(mb, 2.9, -2.5, 0.45, 0.7)
        p.finish(mb, "race_orc_house_%d" % level, rig)
    return build


def center():
    """The warlord's hall: a longhouse under a ribcage of tusks, 14 x 12 m."""
    mb = p.begin()
    rig = p.Rig()
    rnd = p.random.Random(87)
    w, d, h = 10.0, 5.6, 2.4
    cy = 1.2
    mb.box((0, cy, 0.3), (w + 0.8, d + 0.8, 0.6), "o_stone")
    for k in range(22):
        a = TAU * k / 22
        p.rock(mb, math.cos(a) * (w / 2 + 0.5), cy + math.sin(a) * (d / 2 + 0.5), 0.2, 0.42, rnd, "o_stone_dark")
    log_walls(mb, 0, cy, 0.6, w, d, h, 0.22)
    top = hide_roof(mb, 0, cy, h + 0.6, w, d, 4.0, "x", rnd, over=0.5, patches=14)
    for k in range(5):                                                          # The ribs over the roof.
        x = -4.0 + 2.0 * k
        for side in (-1, 1):
            pts = []
            for i in range(7):
                u = i / 6
                pts.append((x, cy + side * (d / 2 + 1.1) * (1 - u * u * 0.95), 0.2 + (top + 0.9) * math.sin(u * math.pi / 2)))
            for i in range(6):
                mb.cylinder(pts[i], pts[i + 1], 0.26 * (1 - i / 6.5), 0.26 * (1 - (i + 1) / 6.5), "tusk", segments=6)
    with p.face(mb, 0, cy, w, d, "front", 0.6):
        doorway(mb, 0, 2.0, 2.1, False)
        for sx in (-1, 1):
            for k in range(3):
                shield(mb, sx * (1.9 + 1.0 * k), 1.2, 0.4, ("o_red", "o_black", "o_red")[k])
    p.stairs(mb, 0, cy - d / 2 - 2.2, 0, 0.6, 3.0, 1.8, "o_stone_dark", 0.2)
    for sx in (-1, 1):                                                          # The gate of tusks and the great skull.
        p.tusk(mb, sx * 2.3, cy - d / 2 - 1.2, 0, 5.4, -sx * 1.7, 0.3, 0.36, n=7)
        p.tusk(mb, sx * 3.3, cy - d / 2 - 0.8, 0, 3.4, -sx * 0.9, 0.2, 0.24, n=6)
    p.skull(mb, 0, cy - d / 2 - 0.9, 5.7, 1.0)
    p.smoke(mb, rig, -2.0, cy, top + 0.4, 0.5)
    p.smoke(mb, rig, 2.4, cy, top + 0.4, 0.45)
    for sx in (-1, 1):                                                          # Palisade wings, banners, drums, fires.
        palisade(mb, rnd, sx * 5.4, cy - 1.0, sx * 6.8, cy - 3.8, 2.6)
        stakes(mb, rnd, sx * 5.6, cy - 1.6, sx * 6.9, cy - 4.2, 5, (sx * 0.4, -0.9), 1.4)
        p.flag(mb, rig, sx * 6.8, cy - 4.1, 0, 6.2, 2.0, 1.1, "o_red", "o_black", knob="bone")
        p.flag(mb, rig, sx * 5.2, cy + 2.2, 0.6, 6.4, 1.8, 0.9, "o_red", "o_black", knob="bone")
        drum(mb, sx * 3.9, cy - d / 2 - 2.6, 0.7, 1.0)
        skull_pole(mb, sx * 1.9, cy - d / 2 - 3.6, 2.6)
    bonfire(mb, rig, rnd, 0, cy - d / 2 - 4.2, 1.2)
    for k in range(4):
        axe(mb, -4.6 + 0.35 * k, cy - d / 2 - 0.5, 0.6, 0.1)
    p.finish(mb, "race_orc_center", rig)


def workshop():
    """The scrap forge: a lean-to, a stone hearth and a grindstone."""
    mb = p.begin()
    rig = p.Rig()
    rnd = p.random.Random(88)
    for sx in (-2.3, 0, 2.3):
        p.log(mb, (sx, 1.6, 0), (sx, 1.6, 2.0), 0.15)
        p.log(mb, (sx, -1.3, 0), (sx, -1.3, 3.0), 0.15)
        p.beam(mb, (sx, 1.9, 1.85), (sx, -1.7, 3.1), 0.12, "pole_dark")
    for r in range(4):                                                          # Hides laced over the rafters.
        y0, y1 = 2.0 - 0.95 * r, 2.0 - 0.95 * (r + 1) - 0.06
        z0, z1 = 1.95 + 0.33 * r, 1.95 + 0.33 * (r + 1) + 0.02
        solid(mb, [(-2.7, y0, z0), (2.7, y0, z0), (2.7, y1, z1), (-2.7, y1, z1)], (0, 0, 0.07), HIDES[r])
    palisade(mb, rnd, -2.5, 1.75, 2.5, 1.75, 1.7, 0.16)
    mb.box((-1.3, 0.7, 0.5), (1.5, 1.2, 1.0), "o_stone")                          # The hearth.
    mb.box((-1.3, 0.7, 1.04), (1.2, 0.9, 0.1), "ember")
    for k in range(8):
        a = TAU * k / 8
        p.rock(mb, -1.3 + math.cos(a) * 0.7, 0.7 + math.sin(a) * 0.55, 0.95, 0.2, rnd, "o_stone_dark")
    p.flame(mb, rig, -1.3, 0.7, 1.05, 0.4)
    mb.sphere((0.3, -0.2, 0.3), 0.5, "o_stone_dark", segments=6, rings=4, scale=(1.2, 0.9, 0.9))    # A boulder for an anvil.
    mb.box((0.3, -0.2, 0.62), (0.7, 0.4, 0.14), "o_iron")
    mb.box((0.35, -0.2, 0.72), (0.9, 0.08, 0.04), "ember")
    for sx in (-1, 1):                                                          # The grindstone.
        p.beam(mb, (1.9 + sx * 0.22, -0.9, 0), (1.9 + sx * 0.22, -0.4, 0.8), 0.1, "pole_dark")
        p.beam(mb, (1.9 + sx * 0.22, 0.1, 0), (1.9 + sx * 0.22, -0.4, 0.8), 0.1, "pole_dark")
    with mb.bone("stone"):
        mb.cylinder((1.78, -0.4, 0.8), (2.02, -0.4, 0.8), 0.5, 0.5, "o_stone", segments=10)
        mb.cylinder((1.6, -0.4, 0.8), (2.2, -0.4, 0.8), 0.05, 0.05, "o_iron", segments=5)
        mb.box((2.25, -0.4, 0.68), (0.06, 0.06, 0.3), "o_iron")
    p.spin(mb, rig, "stone", (1.9, -0.4, 0.8), (1, 0, 0), 2.0, "turn", (2.2, -0.4, 0.8))
    p.beam(mb, (-2.3, -1.45, 1.5), (0, -1.45, 1.5), 0.08, "pole_dark")           # The rack of what was made.
    for k in range(4):
        axe(mb, -2.0 + 0.5 * k, -1.5, 0.15, 0.0)
    for k in range(6):
        mb.box((2.2 + rnd.uniform(-0.3, 0.3), 0.9 + rnd.uniform(-0.3, 0.3), 0.08 + 0.07 * k), (rnd.uniform(0.3, 0.7), rnd.uniform(0.1, 0.3), 0.07), "o_iron", rotation_z=rnd.uniform(0, 3))
    skull_pole(mb, 2.7, -1.9, 2.2, False)
    p.finish(mb, "race_orc_workshop", rig)


def storehouse():
    """The meat loft: a platform on stilts, out of reach of the wolves."""
    mb = p.begin()
    rig = p.Rig()
    rnd = p.random.Random(89)
    w, d, zf = 4.6, 3.6, 1.5
    for sx in (-1, 1):
        for sy in (-1, 1):
            p.log(mb, (sx * w / 2, sy * d / 2, 0), (sx * w / 2, sy * d / 2, zf + 2.0), 0.17)
            p.beam(mb, (sx * w / 2, sy * d / 2, 0.4), (sx * (w / 2 - 1.0), sy * d / 2, zf - 0.1), 0.1, "pole_dark")
    for k in range(10):
        y = -d / 2 + d * (k + 0.5) / 10
        p.log(mb, (-w / 2 - 0.3, y, zf), (w / 2 + 0.3, y, zf), 0.17)
    hide_roof(mb, 0, 0, zf + 2.0, w, d, 1.6, "x", rnd, patches=4)
    p.log(mb, (-w / 2, -d / 2, zf + 1.9), (w / 2, -d / 2, zf + 1.9), 0.12)
    for k in range(4):                                                          # Carcasses and hams swing from the beam.
        name = rig.name("meat")
        x = -1.5 + 1.0 * k
        with mb.bone(name):
            mb.cylinder((x, -d / 2, zf + 1.8), (x, -d / 2, zf + 1.45), 0.015, 0.015, "rope", segments=4)
            mb.sphere((x, -d / 2, zf + 1.05), 0.3, "meat", segments=6, rings=5, scale=(0.8, 0.6, 1.5))
            mb.cylinder((x, -d / 2, zf + 0.62), (x, -d / 2, zf + 0.42), 0.05, 0.08, "bone", segments=5)
        p.sway(mb, rig, name, (x, -d / 2, zf + 1.8), 7.0, 3.2, "sway", (1, 0, 0), (x, -d / 2, zf + 1.0))
    p.barrel(mb, -1.5, 0.6, zf + 0.17, 0.8, 0.3)
    p.barrel(mb, -0.8, 0.9, zf + 0.17, 0.8, 0.3)
    p.sack(mb, 0.4, 0.8, zf + 0.17, 0.3)
    p.sack(mb, 1.1, 0.5, zf + 0.17, 0.28)
    p.crate(mb, 1.6, 1.0, zf + 0.17, 0.6)
    for k in range(7):                                                          # A ladder.
        mb.box((1.6, -d / 2 - 0.25 - 0.12 * (6 - k), 0.2 + 0.2 * k), (0.6, 0.06, 0.05), "pole")
    for sx in (-1, 1):
        p.beam(mb, (1.6 + sx * 0.3, -d / 2 - 1.1, 0), (1.6 + sx * 0.3, -d / 2 - 0.2, zf + 0.2), 0.07, "pole_dark")
    for k in range(5):                                                          # Bones thrown under it.
        mb.cylinder((rnd.uniform(-1.5, 0.8), rnd.uniform(-1, 1), 0.05), (rnd.uniform(-1.5, 0.8), rnd.uniform(-1, 1), 0.05), 0.04, 0.04, "bone", segments=4)
    p.skull(mb, -0.3, -0.4, 0.14, 0.26, True)
    stakes(mb, rnd, -2.9, 1.6, -2.9, -1.6, 4, (-1, 0), 1.1)
    stakes(mb, rnd, 2.9, 1.6, 2.9, -1.0, 3, (1, 0), 1.1)
    p.finish(mb, "race_orc_storehouse", rig)


def fighting_pit():
    """The fighting pit: a ring of stakes, a gate of tusks and the benches
    of those who watch, 10 x 10 m."""
    mb = p.begin()
    rig = p.Rig()
    rnd = p.random.Random(85)
    R = 3.4
    mb.cylinder((0, 0, 0), (0, 0, 0.1), R + 0.3, R + 0.3, "o_mud", segments=16)
    mb.cylinder((0, 0, 0.05), (0, 0, 0.14), R - 0.1, R - 0.1, "sack", segments=16)   # Sand.
    n = 58
    for k in range(n):                                                          # The ring, open at the front for the gate.
        a = TAU * k / n
        if abs(math.cos(a)) < 0.28 and math.sin(a) < 0:
            continue
        hh = 1.5 * rnd.uniform(0.85, 1.15)
        x, y = math.cos(a) * R, math.sin(a) * R
        mb.cylinder((x, y, 0), (x, y, hh), 0.17, 0.15, "bark", segments=6)
        mb.cylinder((x, y, hh), (x, y, hh + 0.36), 0.15, 0.0, "log_end", segments=6)
    for sx in (-1, 1):
        p.tusk(mb, sx * 1.15, -R, 0, 3.4, -sx * 0.9, 0.0, 0.24, n=6)
        p.brazier(mb, rig, sx * 2.0, -R - 0.7, 0, 1.2, "o_iron", "pole_dark")
        skull_pole(mb, sx * 2.9, -R - 0.2, 2.4)
    p.skull(mb, 0, -R - 0.1, 3.55, 0.6)
    p.log(mb, (0, 0, 0), (0, 0, 2.2), 0.2)                                        # The post in the middle, with its chain.
    p.ring(mb, 0, 0, 1.6, 0.26, 0.06, "o_iron", 8)
    for k in range(5):
        p.beam(mb, (0.26 + 0.2 * k, 0, 1.6 - 0.3 * k), (0.46 + 0.2 * k, 0, 1.3 - 0.3 * k), 0.05 if k % 2 else 0.07, "o_iron")
    axe(mb, -1.4, 0.9, 0.1, 0.25)
    mb.cylinder((1.3, -1.2, 0.12), (1.3, -1.2, 0.2), 0.4, 0.4, "o_red", segments=8)  # A shield left on the sand.
    mb.cylinder((1.3, -1.2, 0.2), (1.3, -1.2, 0.26), 0.14, 0.08, "o_iron", segments=6)
    for tier, (rr, zz) in enumerate(((R + 0.9, 0.9), (R + 1.6, 1.5))):          # Two tiers of log benches round the back.
        m = 7
        for i in range(m):
            a0 = math.radians(15 + 150 * i / m)
            a1 = math.radians(15 + 150 * (i + 1) / m)
            p.log(mb, (math.cos(a0) * rr, math.sin(a0) * rr, zz), (math.cos(a1) * rr, math.sin(a1) * rr, zz), 0.2)
            mb.cylinder((math.cos(a0) * rr, math.sin(a0) * rr, 0), (math.cos(a0) * rr, math.sin(a0) * rr, zz - 0.15), 0.12, 0.12, "pole_dark", segments=5)
        a1 = math.radians(165)
        mb.cylinder((math.cos(a1) * rr, math.sin(a1) * rr, 0), (math.cos(a1) * rr, math.sin(a1) * rr, zz - 0.15), 0.12, 0.12, "pole_dark", segments=5)
    for a in (35, 145):                                                         # The chief's banners.
        x, y = math.cos(math.radians(a)) * (R + 1.9), math.sin(math.radians(a)) * (R + 1.9)
        p.flag(mb, rig, x, y, 0, 5.0, 1.7, 0.9, "o_red", "o_black", knob="bone")
    for a in (200, 340):
        x, y = math.cos(math.radians(a)) * (R + 1.0), math.sin(math.radians(a)) * (R + 1.0)
        p.flag(mb, rig, x, y, 0, 3.8, 1.3, 0.7, "o_red", "o_black", knob="bone")
    drum(mb, -3.6, -3.4, 0.6, 0.9)
    for k in range(3):
        axe(mb, 3.3 + 0.3 * k, -3.6, 0, 0.1)
    p.beam(mb, (3.1, -3.65, 1.0), (4.2, -3.65, 1.0), 0.08, "pole_dark")
    p.finish(mb, "race_orc_fighting_pit", rig)


def tower():
    """A lookout of lashed logs with a hide roof and the alarm drum."""
    mb = p.begin()
    rig = p.Rig()
    rnd = p.random.Random(86)
    zf = 5.0
    for sx in (-1, 1):
        for sy in (-1, 1):
            p.log(mb, (sx * 1.5, sy * 1.5, 0), (sx * 1.1, sy * 1.1, zf + 2.0), 0.17)
    for z in (1.6, 3.4):                                                        # Cross braces on every side.
        k = 1.5 - 0.4 * z / (zf + 2.0)
        for a, b in (((-k, -k), (k, -k)), ((k, -k), (k, k)), ((k, k), (-k, k)), ((-k, k), (-k, -k))):
            p.beam(mb, (a[0], a[1], z - 1.3), (b[0], b[1], z + 0.3), 0.1, "pole_dark")
            p.beam(mb, (a[0], a[1], z + 0.3), (b[0], b[1], z + 0.3), 0.1, "pole_dark")
    for k in range(9):
        y = -1.4 + 2.8 * (k + 0.5) / 9
        p.log(mb, (-1.6, y, zf), (1.6, y, zf), 0.16)
    for sx in (-1, 1):                                                          # A rail with shields.
        p.beam(mb, (sx * 1.5, -1.5, zf + 0.9), (sx * 1.5, 1.5, zf + 0.9), 0.1, "pole_dark")
        p.beam(mb, (-1.5, sx * 1.5, zf + 0.9), (1.5, sx * 1.5, zf + 0.9), 0.1, "pole_dark")
    with mb.placed((0, -1.5, zf), 0):
        shield(mb, -0.7, 0.55, 0.36, "o_red")
        shield(mb, 0.7, 0.55, 0.36, "o_black")
    hide_roof(mb, 0, 0, zf + 2.0, 2.4, 2.4, 1.4, "x", rnd, over=0.5, patches=3)
    with mb.placed((0.4, 0.3, zf + 0.16), 0):
        drum(mb, 0, 0, 0.45, 0.6)
    for k in range(16):                                                         # The ladder.
        mb.box((0, -1.75 - 0.03 * (15 - k), 0.25 + 0.31 * k), (0.6, 0.06, 0.05), "pole")
    for sx in (-1, 1):
        p.beam(mb, (sx * 0.3, -2.25, 0), (sx * 0.3, -1.7, zf + 0.3), 0.07, "pole_dark")
    p.flag(mb, rig, -1.1, 1.1, zf + 2.6, 2.6, 1.5, 0.8, "o_red", "o_black", knob="bone")
    p.skull(mb, 0, -1.25, zf + 2.1, 0.34)
    stakes(mb, rnd, -2.1, 1.6, -2.1, -1.6, 4, (-1, 0), 1.1)
    stakes(mb, rnd, 2.1, 1.6, 2.1, -1.6, 4, (1, 0), 1.1)
    p.finish(mb, "race_orc_tower", rig)


MODELS = {
    "race_orc_fighting_pit": fighting_pit, "race_orc_tower": tower,
    "race_orc_house_1": house(1), "race_orc_house_2": house(2), "race_orc_house_3": house(3),
    "race_orc_center": center, "race_orc_workshop": workshop, "race_orc_storehouse": storehouse,
}
