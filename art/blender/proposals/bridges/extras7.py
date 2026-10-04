"""An eighth batch of the `bridges` family: a narrow stone footbridge,
mooring dolphins and two more fantasy bridges (of bones and of mushrooms)."""

import math

from parts import B, BRICK, jit, lantern, lerp, log, planks_x, planks_y, rock, rope, sag, save
from bridges import stone_bridge
from docks import pile
from extras import skull

MODELS = {}


def model(name, fn, **kw):
    MODELS[name] = lambda: fn(name, **kw)


def dolphins(name):
    """Two clusters of piles to moor a big ship away from the shore."""
    b = B()
    for cx in (-4.0, 4.0):
        for k in range(5):
            a = 2 * math.pi * k / 5 + cx
            lean = 0.55 if k else 0.0
            foot = (cx + math.cos(a) * lean, math.sin(a) * lean, -3.0)
            head = (cx + math.cos(a) * lean * 0.25, math.sin(a) * lean * 0.25, 2.2 + (0.3 if k == 0 else jit(k, 0.1)))
            b.cyl(foot, head, 0.15, "timber", r2=0.12, seg=7)
        for z in (1.2, 1.9):
            b.cyl((cx, 0, z - 0.06), (cx, 0, z + 0.06), 0.34, "iron", seg=8)
        for k in range(3):
            b.cyl((cx, 0, 0.3 + k * 0.09), (cx, 0, 0.38 + k * 0.09), 0.36, "rope", seg=8)
        b.cyl((cx, 0, 2.5), (cx, 0, 2.58), 0.17, "wood_light", seg=7)
    lantern(b, -4.0, 0, 3.0)
    b.box((-4.0, 0, 2.75), (0.05, 0.05, 0.4), "iron")
    rope(b, sag((-4.0, 0.3, 0.5), (4.0, 0.3, 0.5), 0.9, 10), r=0.03)
    for k in range(3):   # Floats on the line between them.
        t = (k + 1) / 4
        b.sphere((lerp(-4.0, 4.0, t), 0.3, 0.5 - 0.9 * 4 * t * (1 - t) + 0.05), 0.16,
                 "paint_red" if k % 2 else "wood_light", seg=6, rings=4)
    pile(b, 0.0, 2.6, 0.9, r=0.1)
    b.solid([(0, 2.6, 0.9), (0, 2.6, 0.55), (0.5, 2.6, 0.72)], [(0, 2.63, 0.9), (0, 2.63, 0.55), (0.5, 2.63, 0.72)],
            "cloth_red")
    save(b, name)


def bone_bridge(name, length=9.0):
    """The spine and ribs of some giant beast, laid across a river."""
    b = B()
    half = length / 2

    def top(x):
        return 0.55 * 0.5 * (1 + math.cos(2 * math.pi * max(-half, min(half, x)) / length))

    n = 14
    for i in range(n):   # Vertebrae: a flat top to walk on, a spur on each side and a keel below.
        xa, xb = -half + length * i / n, -half + length * (i + 1) / n
        xm = (xa + xb) / 2
        z = top(xm)
        b.beam((xa + 0.03, 0, top(xa)), (xb - 0.03, 0, top(xb)), 1.5, 0.28, "bark" if i % 2 else "canvas_shade")
        b.box((xm, 0, z - 0.4), (0.3, 0.5, 0.5), "canvas_shade")
        for s in (-1, 1):
            b.cyl((xm, s * 0.7, z), (xm, s * 1.05, z + 0.12), 0.12, "bark", r2=0.05, seg=5)
    for i in range(1, n, 2):   # Ribs curve out and up: they serve as a handrail.
        xm = -half + length * (i + 0.5) / n
        z = top(xm)
        for s in (-1, 1):
            pts = [(xm, s * 0.8, z - 0.05), (xm, s * 1.35, z + 0.45), (xm, s * 1.45, z + 1.1), (xm, s * 1.15, z + 1.7)]
            for k, (p, q) in enumerate(zip(pts, pts[1:])):
                b.cyl(p, q, 0.09 - 0.02 * k, "bark", r2=0.07 - 0.02 * k, seg=6)
    for s in (-1, 1):
        pts = [(-half + length * (i + 0.5) / n, s * 1.42, top(-half + length * (i + 0.5) / n) + 1.05)
               for i in range(1, n, 2)]
        for p, q in zip(pts, pts[1:]):
            rope(b, sag(p, q, 0.12, 4), r=0.02)
    # The skull at one end, tail bones at the other, and three legs of bone standing in the water.
    skull(b, -half - 0.9, 0, 0.75, 0.85)
    for k in range(4):
        x = half + 0.25 + k * 0.42
        b.box((x, jit(k, 0.06), 0.14 - 0.02 * k), (0.36 - 0.05 * k, 0.7 - 0.12 * k, 0.26 - 0.04 * k), "bark")
    for x in (-2.2, 0.0, 2.2):
        for s in (-1, 1):
            b.cyl((x, s * 0.55, top(x) - 0.3), (x + 0.2 * s, s * 0.9, -3.0), 0.16, "canvas_shade", r2=0.1, seg=6)
            b.sphere((x, s * 0.55, top(x) - 0.3), 0.2, "bark", seg=6, rings=4)
    for k in range(3):
        rock(b, -half + 0.2 + k * 0.1, (k - 1) * 1.5, 0.5, -0.4, 0.2, seed=k, mat="stone_dark")
    save(b, name)


def mushroom_bridge(name, cap=("paint_red", "cloth_red"), spots="cloth_white", glow=False):
    """Giant mushrooms as stepping platforms across a stream of the enchanted forest."""
    b = B()
    spots_at = [(-3.4, 0.2, 0.45, 1.25), (-1.6, -0.35, 0.8, 1.15), (0.1, 0.3, 1.0, 1.3), (1.9, -0.25, 0.75, 1.1),
                (3.5, 0.15, 0.4, 1.2)]
    for k, (x, y, hgt, r) in enumerate(spots_at):
        b.cyl((x + 0.15, y, -2.5), (x, y, hgt - 0.1), 0.42, "bark", r2=0.26, seg=8)
        b.cyl((x, y, hgt - 0.38), (x, y, hgt - 0.3), 0.45, "canvas_shade", r2=0.3, seg=8)       # The ring on the stem.
        b.cyl((x, y, hgt - 0.14), (x, y, hgt), r * 0.86, "canvas", r2=r, seg=10)                # Gills.
        b.cyl((x, y, hgt), (x, y, hgt + 0.2), r, cap[k % 2], r2=r * 0.72, seg=10)
        b.cyl((x, y, hgt + 0.2), (x, y, hgt + 0.3), r * 0.72, cap[k % 2], r2=r * 0.3, seg=10)
        for j in range(5):
            a = j * 1.26 + k
            rr = r * (0.82 if j % 2 else 0.5)
            zz = hgt + (0.11 if j % 2 else 0.25)
            sx, sy = x + math.cos(a) * rr, y + math.sin(a) * rr
            b.cyl((sx, sy, zz), (sx, sy, zz + 0.05), 0.13, spots, seg=6)
        if glow:
            for j in range(3):
                a = j * 2.1 + k
                b.sphere((x + math.cos(a) * r * 1.05, y + math.sin(a) * r * 1.05, hgt - 0.25 - 0.1 * j), 0.07,
                         "crystal_glow", seg=5, rings=3)
    # Small mushrooms as steps on the banks, and a few growing from the stems.
    for e in (-1, 1):
        x = e * 4.6
        b.cyl((x, 0.1, -0.2), (x, 0.1, 0.12), 0.16, "bark", seg=6)
        b.cyl((x, 0.1, 0.12), (x, 0.1, 0.24), 0.55, cap[0], r2=0.25, seg=8)
        rock(b, e * 5.1, -0.4, 0.4, -0.3, 0.12, seed=e + 4, mat="stone_moss")
    for k, (x, y, z) in enumerate(((-2.6, 0.9, 0.1), (0.9, -1.2, 0.2), (2.7, 0.9, 0.05))):
        b.cyl((x, y, -1.0), (x, y, z + 0.3), 0.07, "bark", seg=5)
        b.cyl((x, y, z + 0.3), (x, y, z + 0.42), 0.3, cap[(k + 1) % 2], r2=0.1, seg=7)
    save(b, name)


def crib(b, cx, cy, sx, sy, z0, z1, fill="stone_dark"):
    """A box of stacked logs, notched at the corners and filled with rocks."""
    layers = max(2, round((z1 - z0) / 0.3))
    for k in range(layers):
        z = z0 + 0.15 + k * (z1 - z0 - 0.3) / max(1, layers - 1)
        for s in (-1, 1):
            if k % 2 == 0:
                y = cy + s * (sy / 2 - 0.1)
                log(b, (cx - sx / 2 - 0.25, y, z), (cx + sx / 2 + 0.25, y, z), 0.15, seg=7)
            else:
                x = cx + s * (sx / 2 - 0.1)
                log(b, (x, cy - sy / 2 - 0.25, z), (x, cy + sy / 2 + 0.25, z), 0.15, seg=7)
    b.box((cx, cy, (z0 + z1) / 2 - 0.1), (sx - 0.35, sy - 0.35, z1 - z0 - 0.2), fill)
    for k in range(4):
        rock(b, cx + jit(k, sx * 0.3, cx), cy + jit(k, sy * 0.3, cy + 1), 0.3, z1 - 0.4, z1 - 0.12 + jit(k, 0.05),
             seed=k, mat="stone" if k % 2 else "stone_dark")


def crib_bridge(name, length=10.0, width=3.0):
    """Log cribs full of rocks for piers, trunks for beams: a strong bridge with no mason."""
    b = B()
    half = length / 2
    zd = 0.45
    for x in (-half + 0.9, 0.0, half - 0.9):
        crib(b, x, 0, 1.5, width + 0.4, -2.2 if x == 0 else -1.2, zd - 0.42)
    for y in (-width / 2 + 0.3, -0.45, 0.45, width / 2 - 0.3):
        log(b, (-half + 0.1, y, zd - 0.27), (half - 0.1, y, zd - 0.27), 0.17, seg=7)
    planks_x(b, -half + 0.2, half - 0.2, width, z=zd)
    for e in (-1, 1):
        b.beam((e * (half + 0.7), 0, 0.0), (e * (half - 0.2), 0, zd - 0.03), width - 0.3, 0.07, "plank_b")
        for s in (-1, 1):
            y = s * (width / 2 - 0.15)
            log(b, (e * 0.3, y, zd + 0.14), (e * (half - 0.3), y, zd + 0.14), 0.13, seg=7)
    save(b, name)


def crib_pier(name, length=6.0, width=3.0):
    """An early dock: two log cribs full of rocks with a plank deck. Shore at +Y."""
    b = B()
    zd = 0.3
    for y in (length / 2 - 1.3, -length / 2 + 1.3):
        crib(b, 0, y, width, 2.4, -2.0, zd - 0.09)
    planks_y(b, -length / 2, length / 2, width - 0.1, z=zd)
    for s in (-1, 1):
        pile(b, s * (width / 2 + 0.15), -length / 2 + 0.3, zd + 0.9, r=0.13)
        for k in range(3):
            b.cyl((s * (width / 2 + 0.15), -length / 2 + 0.3, zd + 0.35 + k * 0.07),
                  (s * (width / 2 + 0.15), -length / 2 + 0.3, zd + 0.41 + k * 0.07), 0.17, "rope", seg=7)
    b.beam((0, length / 2 + 0.6, 0.0), (0, length / 2, zd - 0.03), width - 0.4, 0.07, "plank_b")
    save(b, name)


model("bridge_crib", crib_bridge)
model("dock_crib_pier", crib_pier)
model("bridge_stone_foot", stone_bridge, span=5.0, abut=1.5, width=2.0, hump=1.6, zs=-0.5, n=7)
model("bridge_stone_foot_brick", stone_bridge, span=5.0, abut=1.5, width=2.0, hump=1.6, zs=-0.5, n=7, pal=BRICK)
model("bridge_stone_multi_level_brick", stone_bridge, arches=4, span=4.5, abut=4.5, hump=2.4, level=True, pal=BRICK)
model("dock_dolphins", dolphins)
model("bridge_bone", bone_bridge)
model("bridge_mushroom", mushroom_bridge)
model("bridge_mushroom_glow", mushroom_bridge, cap=("crystal_deep", "paint_blue"), spots="crystal_glow", glow=True)
