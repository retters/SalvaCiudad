"""The wall types and their modular pieces.

Every wall type is a class with the same interface, so one set of piece
builders (straight, corner, tee, cross, end, ...) serves all of them:

    run(p, x0, x1, base=0, floor=None)   a stretch of wall along local X,
                                         centered on y = 0, from x0 to x1
    node(p, arms, base=0)                the core of a junction; `arms` is
                                         the set of sides ("E", "N", ...)
                                         where a wall arrives
    body(p, x0, x1, z0, z1)              the plain mass, without its top
    half                                 half the size of the node (arms
                                         start there)

The module is 2 m: a piece fills a 2 x 2 m cell and shows the same
cross-section at the middle of each cell edge it reaches.
"""

import math

from wallkit import ARM_ROT, SIDE_ROT, brazier, flame_mech, rng, rubble, scaffold

MERLON = 0.5  # Length of a merlon and of a crenel: the pattern repeats every 1 m.


def merlons(x0, x1, phase=0.5):
    """(lo, hi) spans of the merlons that fall inside [x0, x1]."""
    out = []
    k = math.floor(x0 - phase) - 1
    while k + phase - MERLON / 2 < x1:
        lo = max(x0, k + phase - MERLON / 2)
        hi = min(x1, k + phase + MERLON / 2)
        if hi - lo > 0.08:
            out.append((lo, hi))
        k += 1
    return out


class WallType:
    key = ""
    walk = None        # Height of the walkway, or None.
    h = 2.0            # Height of the wall proper (walkway or top).
    top = 2.0          # Highest point (for doors, torches, scaffolds).
    t = 0.6            # Thickness.
    half = 0.3
    rubble_mats = ("stone",)
    roof = ("roof", "roof_dark")
    stair_wood = False
    frame_mat = "timber"
    door_style = "plank"

    def arm(self, p, d, base=0.0):
        self.run(p.at(rot=ARM_ROT[d]), self.half, 1.0, base=base)

    def torch_at(self):
        """(y, z of the foot, pole length) of the wall-top brazier."""
        return (0.0, self.h, 0.7)


# --- Masonry with or without a walkway -------------------------------------------------------


class Masonry(WallType):
    def __init__(self, key, mat, dark, trim, light, walk, t, parapet=True, course=0.7, walkmat="stone_dark",
                 bands=(), spikes=False, rubble_mats=None, band_mat="iron"):
        self.key, self.mat, self.dark, self.trim, self.light = key, mat, dark, trim, light
        self.t, self.half, self.course, self.walkmat = t, t / 2, course, walkmat
        self.parapet_on, self.bands, self.spikes, self.band_mat = parapet, bands, spikes, band_mat
        self.h = walk
        self.walk = walk if parapet else None
        self.top = walk + 1.1 if parapet else walk + 0.12
        self.pw = 0.3
        self.rubble_mats = rubble_mats or (mat, dark, light)
        self.frame_mat = trim

    def block(self, p, x0, x1, y0, y1, z0, z1, base=0.0, proud_x=False):
        xc, yc, L, D = (x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0
        p.box((xc, yc, (z0 + z1) / 2), (L, D, z1 - z0), self.mat)
        gx = 0.03 if proud_x else 0.0
        z = base + 0.4
        row = 0
        r = rng(self.key, round(x0, 2), round(y0, 2), base)
        while z < z1 - 0.15:   # Courses: a dark joint and one or two proud blocks per row.
            if z > max(z0, base + 0.4) + 0.1:
                p.box((xc, yc, z), (L + gx, D + 0.03, 0.05), self.dark)
            zt = min(z + self.course, z1)
            if z >= z0 - 0.01 and zt - z > 0.2 and L > 0.9 and (self.course > 0.4 or row % 2 == 0):
                for j in range(1 if L < 1.6 else 2):
                    w = r.uniform(0.4, 0.7)
                    x = r.uniform(x0 + w / 2 + 0.05, x1 - w / 2 - 0.05)
                    p.box((x, yc, (z + zt) / 2 + 0.02), (w, D + 0.05, zt - z - 0.1),
                          self.light if (row + j) % 3 else self.dark)
            z += self.course
            row += 1
        for zb in self.bands:
            if z0 + 0.1 < base + zb < z1 - 0.1:
                p.box((xc, yc, base + zb), (L + gx, D + 0.07, 0.14), self.band_mat)
                n = max(1, round(L / 0.5))
                for i in range(n):
                    p.box((x0 + (i + 0.5) * L / n, yc, base + zb), (0.08, D + 0.13, 0.08), "steel")

    def run(self, p, x0, x1, base=0.0, floor=None, foot=True, sides=(-1, 1), phase=0.5):
        L, xc = x1 - x0, (x0 + x1) / 2
        z0 = base if floor is None else floor
        top = base + self.h
        if floor is None and foot:
            p.box((xc, 0, base + 0.2), (L, self.t + 0.16, 0.4), self.dark)
        self.block(p, x0, x1, -self.half, self.half, z0, top, base)
        if self.parapet_on:
            p.box((xc, 0, top - 0.11), (L, self.t + 0.2, 0.22), self.dark)
            p.box((xc, 0, top + 0.01), (L, self.t - 0.3, 0.05), self.walkmat)
            for s in sides:
                self.parapet(p, x0, x1, s, base, phase)
        else:
            p.box((xc, 0, top + 0.06), (L, self.t + 0.12, 0.12), self.trim)

    def parapet(self, p, x0, x1, s, base=0.0, phase=0.5, solid=False):
        y = s * (self.half + 0.1 - self.pw / 2)
        top = base + self.h
        L, xc = x1 - x0, (x0 + x1) / 2
        p.box((xc, y, top + 0.3), (L, self.pw, 0.6), self.mat)
        spans = [(x0, x0 + 0.45), (x1 - 0.45, x1)] if solid else merlons(x0, x1, phase)
        for lo, hi in spans:
            p.box(((lo + hi) / 2, y, top + 0.85), (hi - lo, self.pw, 0.5), self.mat)
            p.box(((lo + hi) / 2, y, top + 1.13), (hi - lo + 0.06, self.pw + 0.08, 0.07), self.trim)
            if self.spikes and hi - lo > 0.3:
                for dx in (-0.12, 0.12):
                    p.cyl(((lo + hi) / 2 + dx, y, top + 1.15), ((lo + hi) / 2 + dx, y, top + 1.5), 0.04, 0.0,
                          "iron_dark", seg=4)

    def node(self, p, arms, base=0.0):
        hf, top = self.half, base + self.h
        if not self.parapet_on:   # A pilaster a little wider and taller than the wall.
            g = hf + 0.08
            p.box((0, 0, base + 0.22), (2 * g + 0.12, 2 * g + 0.12, 0.44), self.dark)
            self.block(p, -g, g, -g, g, base, top + 0.14, base, proud_x=True)
            p.box((0, 0, top + 0.2), (2 * g + 0.14, 2 * g + 0.14, 0.12), self.trim)
            p.taper((0, 0), (2 * g + 0.02, 2 * g + 0.02), (0.2, 0.2), top + 0.26, top + 0.5, self.trim)
            return
        p.box((0, 0, base + 0.2), (self.t + 0.16, self.t + 0.16, 0.4), self.dark)
        self.block(p, -hf, hf, -hf, hf, base, top, base, proud_x=True)
        p.box((0, 0, top - 0.11), (self.t + 0.2, self.t + 0.2, 0.22), self.dark)
        p.box((0, 0, top + 0.01), (self.t - 0.3, self.t - 0.3, 0.05), self.walkmat)
        for d in "ESWN":
            if d in arms:   # The walkway flags reach the arm.
                q = p.at(rot=ARM_ROT[d])
                q.box((hf - 0.1, 0, top + 0.01), (0.3, self.t - 0.3, 0.05), self.walkmat)
            else:
                self.parapet(p.at(rot=SIDE_ROT[d]), -hf - 0.1, hf + 0.1, -1, base, solid=True)

    def body(self, p, x0, x1, z0, z1):
        if z0 <= 0.01:
            p.box(((x0 + x1) / 2, 0, 0.2), (x1 - x0, self.t + 0.16, 0.4), self.dark)
        self.block(p, x0, x1, -self.half, self.half, z0, z1, 0.0)

    def torch_at(self):
        if self.parapet_on:
            return (-(self.half + 0.1 - self.pw / 2), self.h + 0.6, 0.9)
        return (0.0, self.h + 0.12, 0.7)


class PlankRampart(Masonry):
    """Two skins of sawn planks on posts, a plank walkway between two
    plank parapets."""

    def __init__(self, key="plank", walk=2.6, t=1.2):
        Masonry.__init__(self, key, "wood", "timber", "timber", "wood_light", walk, t, walkmat="wood_light",
                         rubble_mats=("wood", "wood_light", "timber"))
        self.pw = 0.12
        self.stair_wood = True

    def block(self, p, x0, x1, y0, y1, z0, z1, base=0.0, proud_x=False):
        xc, yc, L, D = (x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0
        row, z = 0, z0
        while z < z1 - 0.01:
            zt = min(z + 0.26, z1)
            g = 0.0 if row % 2 else 0.03
            p.box((xc, yc, (z + zt) / 2), (L + (g if proud_x else 0.0), D + g, zt - z),
                  "wood" if row % 2 else "wood_light")
            z = zt
            row += 1

    def run(self, p, x0, x1, base=0.0, floor=None, foot=True, sides=(-1, 1), phase=0.5):
        L, xc = x1 - x0, (x0 + x1) / 2
        z0 = base if floor is None else floor
        top = base + self.h
        self.block(p, x0, x1, -self.half, self.half, z0, top, base)
        p.box((xc, 0, top + 0.03), (L, self.t + 0.1, 0.07), "wood_light")
        for lo, hi in merlons(x0, x1, phase):   # Posts and joist ends, one per merlon.
            c = (lo + hi) / 2
            if hi - lo < 0.3:
                continue
            for s in (-1, 1):
                p.box((c, s * (self.half + 0.03), (z0 + top) / 2), (0.16, 0.14, top - z0), "timber")
            p.box((c, 0, top - 0.14), (0.14, self.t + 0.34, 0.14), "timber")
        for s in sides:
            self.parapet(p, x0, x1, s, base, phase)

    def parapet(self, p, x0, x1, s, base=0.0, phase=0.5, solid=False):
        y = s * (self.half + 0.03)
        top = base + self.h + 0.06
        L, xc = x1 - x0, (x0 + x1) / 2
        p.box((xc, y, top + 0.16), (L, self.pw, 0.3), "wood")
        p.box((xc, y, top + 0.45), (L, self.pw - 0.02, 0.28), "wood_light")
        spans = [(x0, x1)] if solid else merlons(x0, x1, phase)
        for lo, hi in spans:
            p.box(((lo + hi) / 2, y, top + 0.82), (hi - lo, self.pw, 0.46), "wood")
            if not solid and hi - lo > 0.3:
                p.box(((lo + hi) / 2, y + s * 0.02, top + 0.55), (0.16, self.pw + 0.06, 1.1), "timber")
        if solid:
            for x in (x0 + 0.08, x1 - 0.08):
                p.box((x, y, top + 0.55), (0.18, self.pw + 0.08, 1.14), "timber")

    def node(self, p, arms, base=0.0):
        hf, top = self.half, base + self.h
        self.block(p, -hf, hf, -hf, hf, base, top, base, proud_x=True)
        p.box((0, 0, top + 0.03), (self.t + 0.1, self.t + 0.1, 0.07), "wood_light")
        for sx in (-1, 1):
            for sy in (-1, 1):
                p.box((sx * (hf + 0.02), sy * (hf + 0.02), base + (self.h + 1.2) / 2), (0.2, 0.2, self.h + 1.2),
                      "timber")
        for d in "ESWN":
            if d not in arms:
                self.parapet(p.at(rot=SIDE_ROT[d]), -hf - 0.05, hf + 0.05, -1, base, solid=True)

    def body(self, p, x0, x1, z0, z1):
        self.block(p, x0, x1, -self.half, self.half, z0, z1, 0.0)
        for lo, hi in merlons(x0, x1):
            if hi - lo > 0.3:
                for s in (-1, 1):
                    p.box(((lo + hi) / 2, s * (self.half + 0.03), (z0 + z1) / 2 + 0.2), (0.16, 0.14, z1 - z0 + 0.4),
                          "timber")

    def torch_at(self):
        return (-(self.half + 0.03), self.h + 0.66, 0.9)


class Stockade(PlankRampart):
    """A double palisade: two rows of logs with rammed earth between
    them and a plank walkway on top; the logs rise above it, tall and
    short in turn, as a parapet on both sides."""

    def __init__(self):
        PlankRampart.__init__(self, "stockade", walk=2.2, t=1.4)
        self.rubble_mats = ("log", "log_end", "soil")

    def _rows(self, p, x0, x1, z0, top, sides, flat=False):
        L = x1 - x0
        n = max(1, round(L / 0.4))
        step = L / n
        r = step / 2
        for s in (-1, 1):
            y = s * (self.half - 0.2)
            for i in range(n):
                x = x0 + (i + 0.5) * step
                if flat:
                    zt = top - 0.12 * ((i * 3 + (s > 0)) % 3)
                elif s in sides:
                    zt = top + (1.5 if int(math.floor(x / 0.4 + 100.01)) % 3 else 0.95)
                else:
                    zt = top + 0.06
                p.cyl((x, y, z0), (x, y, zt), r, r * 0.94, "log", seg=7)
                if s in sides and not flat:
                    p.cyl((x, y, zt), (x, y, zt + 0.36), r * 0.94, 0.0, "log_end", seg=7)
                else:
                    p.cyl((x, y, zt), (x, y, zt + 0.03), r * 0.8, r * 0.8, "log_end", seg=7)
        return r

    def run(self, p, x0, x1, base=0.0, floor=None, foot=True, sides=(-1, 1), phase=0.5):
        L, xc = x1 - x0, (x0 + x1) / 2
        z0 = base if floor is None else floor
        top = base + self.h
        p.box((xc, 0, (z0 + top) / 2), (L, self.t - 0.5, top - z0), "soil")
        p.box((xc, 0, top + 0.03), (L, self.t - 0.4, 0.08), "wood_light")
        r = self._rows(p, x0, x1, z0, top, sides)
        for s in sides:
            yo = s * (self.half - 0.2 + r * 0.92)
            p.box((xc, yo, top + 0.6), (L, 0.08, 0.09), "rope")
            if base + 1.0 > z0 + 0.1:
                p.box((xc, yo, base + 1.0), (L, 0.08, 0.12), "timber")

    def node(self, p, arms, base=0.0):
        hf, top = self.half, base + self.h
        p.box((0, 0, base + self.h / 2), (self.t - 0.5, self.t - 0.5, self.h), "soil")
        p.box((0, 0, top + 0.03), (self.t - 0.3, self.t - 0.3, 0.08), "wood_light")
        for sx in (-1, 1):
            for sy in (-1, 1):
                x, y = sx * (hf - 0.2), sy * (hf - 0.2)
                p.cyl((x, y, base), (x, y, top + 1.75), 0.25, 0.22, "log", seg=8)
                p.cyl((x, y, top + 1.75), (x, y, top + 2.2), 0.22, 0.0, "log_end", seg=8)
                p.cyl((x, y, top + 0.55), (x, y, top + 0.67), 0.26, 0.26, "rope", seg=8)
        for d in "ESWN":
            q = p.at(rot=SIDE_ROT[d])
            closed = d not in arms
            for x in (-0.19, 0.19):
                zt = top + 1.2 if closed else top + 0.06
                q.cyl((x, -(hf - 0.2), base), (x, -(hf - 0.2), zt), 0.19, 0.18, "log", seg=7)
                if closed:
                    q.cyl((x, -(hf - 0.2), zt), (x, -(hf - 0.2), zt + 0.34), 0.18, 0.0, "log_end", seg=7)

    def parapet(self, p, x0, x1, s, base=0.0, phase=0.5, solid=False):
        pass

    def body(self, p, x0, x1, z0, z1):
        p.box(((x0 + x1) / 2, 0, (z0 + z1) / 2 - 0.1), (x1 - x0, self.t - 0.5, max(0.05, z1 - z0 - 0.2)), "soil")
        self._rows(p, x0, x1, z0, z1, (), flat=True)

    def torch_at(self):
        return (0.0, self.h + 0.06, 1.8)


# --- Log palisade ----------------------------------------------------------------------------


class Palisade(WallType):
    key = "palisade"
    h, top, t, half = 3.0, 3.0, 0.42, 0.2
    rubble_mats = ("log", "log_end", "timber")
    frame_mat = "timber"

    log, tip, hvar = "log", "log_end", 0.14

    def _logs(self, p, x0, x1, z0, base, pointed=True, hmax=None):
        n = max(1, round((x1 - x0) / 0.4))
        step = (x1 - x0) / n
        r = step / 2
        for i in range(n):
            x = x0 + (i + 0.5) * step
            hh = 2.6 + self.hvar * ((int(round((x + 9) * 5)) * 7) % 3 - 1)
            if hmax is not None:
                hh = min(hh, hmax * (0.75 + 0.25 * ((i * 5) % 3) / 2))
            zt = base + hh
            p.cyl((x, 0, z0), (x, 0, zt), r, r * 0.94, self.log, seg=7)
            if pointed:
                p.cyl((x, 0, zt), (x, 0, zt + 0.42), r * 0.94, 0.0, self.tip, seg=7)
            else:
                p.cyl((x, 0, zt), (x, 0, zt + 0.03), r * 0.8, r * 0.8, self.tip, seg=7)
        return r

    def run(self, p, x0, x1, base=0.0, floor=None, **_):
        z0 = base if floor is None else floor
        r = self._logs(p, x0, x1, z0, base)
        xc, L = (x0 + x1) / 2, x1 - x0
        for z, mat, hh in ((base + 0.95, "timber", 0.12), (base + 2.1, "rope", 0.09), (base + 2.22, "rope", 0.06)):
            if z > z0 + 0.1:
                for s in (-1, 1):
                    p.box((xc, s * r * 0.92, z), (L, 0.08, hh), mat)

    def node(self, p, arms, base=0.0):
        p.cyl((0, 0, base), (0, 0, base + 3.1), 0.27, 0.25, self.log, seg=8)
        p.cyl((0, 0, base + 3.1), (0, 0, base + 3.6), 0.25, 0.0, self.tip, seg=8)
        for z in (base + 0.95, base + 2.15):
            p.cyl((0, 0, z - 0.07), (0, 0, z + 0.07), 0.29, 0.29, "rope" if z > base + 1.5 else "iron", seg=8)

    def body(self, p, x0, x1, z0, z1):
        self._logs(p, x0, x1, z0, 0.0, pointed=False, hmax=z1)

    def torch_at(self):
        return (-0.26, 1.6, 2.1)


class OrcPalisade(Palisade):
    """The orcs' palisade: dark, uneven logs with bone-white tips, scrap
    iron plates, outward spikes and a stripe of war paint."""
    key = "orc"
    log, tip, hvar = "timber", "bone", 0.4
    rubble_mats = ("timber", "bone", "rust")

    def run(self, p, x0, x1, base=0.0, floor=None, **_):
        z0 = base if floor is None else floor
        r = self._logs(p, x0, x1, z0, base)
        xc, L = (x0 + x1) / 2, x1 - x0
        rr = rng("orc", round(x0, 2), round(x1, 2), base)
        for s in (-1, 1):
            if base + 1.7 > z0 + 0.2:
                p.box((xc, s * r * 0.93, base + 1.7), (L, 0.07, 0.26), "blood")
            if base + 0.9 > z0 + 0.1:
                p.box((xc, s * r * 0.95, base + 0.9), (L, 0.08, 0.12), "iron_dark")
        n = max(1, round(L / 0.4))
        for i in range(n):
            x = x0 + (i + 0.5) * L / n
            if base + 2.2 > z0 + 0.2:
                for s in (-1, 1):   # Spikes pointing out, on both faces.
                    p.cyl((x, s * r * 0.8, base + 2.2), (x, s * (r + 0.42), base + 2.38), 0.05, 0.0, "iron_dark",
                          seg=5)
            if i % 2 == 0 and L > 0.7 and base + 1.3 > z0 + 0.3:
                p.box((x + rr.uniform(-0.1, 0.1), 0, base + rr.uniform(0.4, 1.3)),
                      (rr.uniform(0.3, 0.45), 2 * r + 0.07, rr.uniform(0.25, 0.4)), rr.choice(("rust", "iron")),
                      rz=0)

    def node(self, p, arms, base=0.0):
        p.cyl((0, 0, base), (0, 0, base + 3.3), 0.29, 0.24, "timber", seg=8)
        for z in (base + 0.9, base + 2.3):
            p.cyl((0, 0, z - 0.08), (0, 0, z + 0.08), 0.31, 0.3, "iron_dark", seg=8)
        p.cyl((0, 0, base + 3.3), (0, 0, base + 3.75), 0.06, 0.03, "iron_dark", seg=5)
        # A horned skull on the post.
        p.sphere((0, 0, base + 3.55), 0.2, "bone", seg=8, rings=5, scale=(1.0, 1.0, 1.1))
        p.box((0, 0, base + 3.36), (0.2, 0.22, 0.14), "bone")
        for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            p.box((d[0] * 0.17 + d[1] * 0.07, d[1] * 0.17 + d[0] * 0.07, base + 3.58), (0.07, 0.07, 0.08), "dark")
            p.box((d[0] * 0.17 - d[1] * 0.07, d[1] * 0.17 - d[0] * 0.07, base + 3.58), (0.07, 0.07, 0.08), "dark")
        for s in (-1, 1):
            p.cyl((s * 0.15, s * 0.15, base + 3.66), (s * 0.42, s * 0.42, base + 3.95), 0.06, 0.0, "bone", seg=5)
            p.cyl((s * 0.15, -s * 0.15, base + 3.66), (s * 0.42, -s * 0.42, base + 3.95), 0.06, 0.0, "bone", seg=5)


class ReedWall(WallType):
    """The frogfolk's wall: two rows of thick canes lashed together, on a
    bank of mud."""
    key = "reed"
    h, top, t, half = 2.4, 2.6, 0.5, 0.18
    rubble_mats = ("bamboo", "bamboo_dark", "mud")
    door_style = "bars"
    frame_mat = "bamboo_dark"

    def run(self, p, x0, x1, base=0.0, floor=None, h=None, **_):
        z0 = base if floor is None else floor
        hh = h or self.h
        L, xc = x1 - x0, (x0 + x1) / 2
        if floor is None:
            p.xprism([(-0.4, base), (0.4, base), (0.24, base + 0.3), (-0.24, base + 0.3)], x0, x1, "mud")
        n = max(1, round(L / 0.14))
        for i in range(n):
            x = x0 + (i + 0.5) * L / n
            y = 0.07 if i % 2 else -0.07
            top = base + hh - 0.25 * (((i * 7) % 5) / 4.0)
            p.cyl((x, y, max(z0, base + 0.1)), (x, y, top), 0.062, 0.05, "bamboo" if (i * 3) % 4 else "bamboo_dark",
                  seg=6)
            p.cyl((x, y, top), (x, y, top + 0.04), 0.03, 0.03, "dark", seg=5)
        for z in (base + 0.75, base + 1.75):
            if z > z0 + 0.1 and z < base + hh - 0.3:
                p.box((xc, 0, z), (L, 0.3, 0.07), "rope")
                p.box((xc, 0, z + 0.1), (L, 0.26, 0.05), "bamboo_dark")

    def node(self, p, arms, base=0.0):
        p.cyl((0, 0, base), (0, 0, base + 0.34), 0.42, 0.3, "mud", seg=8)
        for k in range(3):
            a = 2 * math.pi * k / 3
            x, y = 0.11 * math.cos(a), 0.11 * math.sin(a)
            p.cyl((x, y, base + 0.1), (x, y, base + 2.7 + 0.15 * k), 0.1, 0.085, "bamboo", seg=7)
            p.cyl((x, y, base + 2.7 + 0.15 * k), (x, y, base + 2.74 + 0.15 * k), 0.06, 0.06, "dark", seg=6)
        for z in (0.8, 1.8, 2.5):
            p.cyl((0, 0, base + z - 0.05), (0, 0, base + z + 0.05), 0.24, 0.24, "rope", seg=8)

    def body(self, p, x0, x1, z0, z1):
        self.run(p, x0, x1, base=0.0, floor=z0 if z0 > 0.01 else None, h=z1)

    def torch_at(self):
        return (-0.3, 0.3, 2.6)


# --- Low fieldstone wall ---------------------------------------------------------------------


class Fieldstone(WallType):
    key = "fieldstone"
    h, top, t, half = 1.2, 1.3, 0.7, 0.4
    rubble_mats = ("stone", "stone_dark", "stone_light")
    door_style = "bars"
    frame_mat = "stone_dark"

    def run(self, p, x0, x1, base=0.0, floor=None, h=None, cap=True, **_):
        z0 = base if floor is None else floor
        top = base + (h or self.h)
        L, xc = x1 - x0, (x0 + x1) / 2
        p.box((xc, 0, (z0 + top) / 2), (L, self.t - 0.1, top - z0), "stone_deep")
        r = rng("field", round(x0, 2), round(x1, 2), base, h)
        rows = max(1, round((top - z0) / 0.3))
        rh = (top - z0) / rows
        for row in range(rows):
            x = x0
            while x < x1 - 0.02:
                w = min(r.uniform(0.28, 0.5), x1 - x)
                if x1 - (x + w) < 0.15:
                    w = x1 - x
                mat = r.choice(("stone", "stone", "stone_light", "stone_dark", "moss" if row == 0 else "stone"))
                p.box((x + w / 2, 0, z0 + (row + 0.5) * rh), (w - 0.03, self.t + r.uniform(-0.04, 0.06), rh - 0.03),
                      mat)
                x += w
        if cap:
            x = x0
            while x < x1 - 0.02:
                w = min(r.uniform(0.3, 0.45), x1 - x)
                if x1 - (x + w) < 0.15:
                    w = x1 - x
                hh = r.uniform(0.1, 0.18)
                p.box((x + w / 2, 0, top + hh / 2), (w - 0.02, self.t + 0.1, hh), r.choice(("stone", "stone_light")))
                x += w

    def node(self, p, arms, base=0.0):
        p.box((0, 0, base + 0.7), (0.8, 0.8, 1.4), "stone_deep")
        r = rng("fieldnode")
        for row in range(4):
            for sx in (-1, 1):
                p.box((sx * 0.21 + r.uniform(-0.03, 0.03), 0, base + 0.175 + row * 0.35),
                      (0.42, 0.86 + r.uniform(-0.03, 0.03), 0.31), r.choice(("stone", "stone_light", "stone_dark")))
                p.box((0, sx * 0.21, base + 0.175 + row * 0.35), (0.86, 0.4, 0.3),
                      r.choice(("stone", "stone_light", "stone_dark")))
        p.box((0, 0, base + 1.47), (0.96, 0.96, 0.14), "stone_light")
        p.taper((0, 0), (0.8, 0.8), (0.3, 0.3), base + 1.54, base + 1.72, "stone")

    def body(self, p, x0, x1, z0, z1):
        self.run(p, x0, x1, base=0.0, floor=z0, h=z1, cap=False)

    def torch_at(self):
        return (0.0, self.h + 0.14, 1.0)


# --- Adobe (clay) wall -----------------------------------------------------------------------


class Adobe(WallType):
    key = "adobe"
    h, top, t, half = 2.4, 2.66, 0.8, 0.45
    rubble_mats = ("adobe", "adobe_dark", "clay")
    frame_mat = "timber"

    def _mass(self, p, x0, x1, z0, z1, base):
        t0 = self.t - 0.16 * max(0.0, (z0 - base)) / self.h
        t1 = self.t - 0.16 * max(0.0, (z1 - base)) / self.h
        p.xprism([(-t0 / 2, z0), (t0 / 2, z0), (t1 / 2, z1), (-t1 / 2, z1)], x0, x1, "adobe")

    def run(self, p, x0, x1, base=0.0, floor=None, **_):
        z0 = base if floor is None else floor
        top = base + self.h
        L, xc = x1 - x0, (x0 + x1) / 2
        if floor is None:
            p.box((xc, 0, base + 0.15), (L, self.t + 0.12, 0.3), "stone_dark")
        self._mass(p, x0, x1, z0, top, base)
        tw = self.t - 0.16
        # A coping of clay tiles in two slopes.
        p.xprism([(-tw / 2 - 0.14, top), (tw / 2 + 0.14, top), (tw / 2 + 0.14, top + 0.05), (0, top + 0.26),
                  (-tw / 2 - 0.14, top + 0.05)], x0, x1, "roof")
        p.box((xc, 0, top + 0.25), (L, 0.12, 0.08), "roof_dark")
        r = rng("adobe", round(x0, 2), round(x1, 2), base)
        k = math.floor(x0)
        while k + 0.5 < x1:   # Beam ends through the wall.
            c = k + 0.5
            if c - 0.07 >= x0 and c + 0.07 <= x1 and base + 1.95 > z0 + 0.2:
                p.cyl((c, -self.t / 2 - 0.1, base + 1.95), (c, self.t / 2 + 0.1, base + 1.95), 0.07, 0.07, "timber",
                      seg=6)
            k += 1
        if L > 0.7:   # Patches where the render fell and the adobe bricks show.
            for i in range(int(L * 1.5)):
                x = r.uniform(x0 + 0.25, x1 - 0.25)
                z = r.uniform(z0 + 0.45, top - 0.9)
                tt = self.t - 0.16 * (z - base) / self.h
                p.box((x, 0, z), (r.uniform(0.25, 0.4), tt + 0.02, r.uniform(0.18, 0.3)),
                      r.choice(("adobe_dark", "adobe_light")))

    def node(self, p, arms, base=0.0):
        g = self.half
        p.box((0, 0, base + 0.17), (2 * g + 0.12, 2 * g + 0.12, 0.34), "stone_dark")
        p.taper((0, 0), (2 * g, 2 * g), (2 * g - 0.14, 2 * g - 0.14), base, base + self.h + 0.25, "adobe")
        p.box((0, 0, base + self.h + 0.29), (2 * g + 0.1, 2 * g + 0.1, 0.08), "roof_dark")
        p.taper((0, 0), (2 * g + 0.04, 2 * g + 0.04), (0.12, 0.12), base + self.h + 0.33, base + self.h + 0.66, "roof")

    def body(self, p, x0, x1, z0, z1):
        if z0 <= 0.01:
            p.box(((x0 + x1) / 2, 0, 0.15), (x1 - x0, self.t + 0.12, 0.3), "stone_dark")
        self._mass(p, x0, x1, z0, z1, 0.0)
        r = rng("adobebody", round(x0, 2), z1)
        n = max(1, round((x1 - x0) / 0.42))
        for i in range(n):   # A course of loose adobe bricks on top.
            w = (x1 - x0) / n
            p.box((x0 + (i + 0.5) * w, 0, z1 + 0.06), (w - 0.04, self.t - 0.25, 0.12),
                  r.choice(("adobe_dark", "adobe_light")))

    def torch_at(self):
        return (-(self.t / 2 + 0.02), 1.3, 2.0)


# --- Living hedge ----------------------------------------------------------------------------


class Hedge(WallType):
    key = "hedge"
    h, top, t, half = 1.8, 1.95, 0.9, 0.5
    rubble_mats = ("leaves_dark", "wood", "leaves")
    door_style = "picket"
    frame_mat = "wood"
    lift = 0.22   # The leaves start this far above the ground, on bare stems.

    def run(self, p, x0, x1, base=0.0, floor=None, h=None, flowers=True, **_):
        z0 = (base if floor is None else floor)
        top = base + (h or self.h)
        L, xc = x1 - x0, (x0 + x1) / 2
        lo = z0 + (self.lift if floor is None else 0.0)
        p.box((xc, 0, (lo + top - 0.12) / 2), (L, self.t - 0.3, top - 0.12 - lo), "leaves_dark")
        r = rng("hedge", round(x0, 2), round(x1, 2), base, h, floor)
        if floor is None and self.lift > 0.1:
            k = math.floor(x0)
            while k + 0.5 < x1:
                c = k + 0.5
                if x0 <= c - 0.1 and c + 0.1 <= x1:
                    p.cyl((c, 0, base), (c + 0.05, 0.03, base + 0.5), 0.07, 0.05, "wood", seg=5)
                    p.cyl((c + 0.18, 0.1, base), (c + 0.12, 0.06, base + 0.45), 0.04, 0.03, "timber", seg=5)
                k += 1
        m = min(0.22, L / 2 - 0.02)
        n = max(2, int(L * (top - lo) * 8.5))
        for i in range(n):
            x = r.uniform(x0 + m, x1 - m)
            rad = min(r.uniform(0.2, 0.3), max(0.12, m + 0.02))
            where = i % 5
            if where < 2:   # Top.
                c = (x, r.uniform(-0.18, 0.18), top - rad * 0.9)
            else:           # Faces.
                c = (x, (1 if i % 2 else -1) * (self.t / 2 - rad * 0.8), r.uniform(lo + rad * 0.6, top - rad * 1.1))
            p.sphere(c, rad, r.choice(("leaves", "leaves", "leaves_light", "leaves_dark")), seg=6, rings=4,
                     scale=(1.25, 1.0, 0.9))
        if flowers and L > 0.8:
            for i in range(int(L * 2.5)):
                s = 1 if i % 2 else -1
                p.box((r.uniform(x0 + 0.2, x1 - 0.2), s * (self.t / 2 + 0.03), r.uniform(lo + 0.3, top - 0.3)),
                      (0.08, 0.08, 0.08), r.choice(("flowers", "berries", "flowers_y")), rz=r.uniform(0, 45))

    def node(self, p, arms, base=0.0):
        p.cyl((0, 0, base), (0, 0, base + 0.5), 0.1, 0.07, "wood", seg=6)
        p.box((0, 0, base + 1.0), (0.75, 0.75, 1.55), "leaves_dark")
        r = rng("hedgenode", len(arms))
        for i in range(12):
            a = i * math.pi / 6
            p.sphere((0.42 * math.cos(a), 0.42 * math.sin(a), base + 0.5 + (i % 3) * 0.55 + r.uniform(0, 0.1)), 0.3,
                     r.choice(("leaves", "leaves_light", "leaves")), seg=6, rings=4)
        p.sphere((0, 0, base + 1.95), 0.42, "leaves_light", seg=6, rings=4)
        p.sphere((0, 0, base + 2.35), 0.25, "leaves", seg=6, rings=4)

    def body(self, p, x0, x1, z0, z1):
        self.run(p, x0, x1, base=0.0, floor=z0 if z0 > 0.01 else None, h=z1, flowers=False)

    def torch_at(self):
        return (-(self.t / 2 + 0.12), 0.0, 2.2)


# --- The wall types of the family ------------------------------------------------------------

WALLS = {
    "palisade": Palisade(),
    "plank": PlankRampart(),
    "fieldstone": Fieldstone(),
    "stone": Masonry("stone", "stone", "stone_dark", "stone_light", "stone_light", 4.0, 1.4, course=0.6),
    "brick": Masonry("brick", "brick", "brick_dark", "stone_light", "brick_light", 3.0, 1.2, course=0.3),
    "adobe": Adobe(),
    "iron": Masonry("iron", "stone_deep", "stone_black", "iron", "stone_dark", 5.0, 1.6, course=0.8,
                    bands=(1.4, 3.0, 4.55), spikes=True, walkmat="stone_black",
                    rubble_mats=("stone_deep", "stone_black", "iron")),
    "hedge": Hedge(),
    # Further types, built with the same generators.
    "whitewash": Masonry("whitewash", "plaster", "stone_dark", "roof", "plaster_warm", 2.6, 0.8, parapet=False,
                         course=0.9, rubble_mats=("plaster", "stone", "brick")),
    "cobble": Masonry("cobble", "stone_dark", "stone_deep", "stone", "stone", 2.4, 0.9, parapet=False, course=0.45),
    # Walls of the fantasy races.
    "dwarf": Masonry("dwarf", "granite", "granite_dark", "bell", "granite_light", 4.0, 1.6, course=0.8,
                     bands=(2.4,), band_mat="bell", walkmat="granite_dark"),
    "elf": Masonry("elf", "marble", "marble_dark", "leaves", "paint_white", 3.6, 1.0, course=0.9,
                   bands=(3.05,), band_mat="gold", walkmat="marble_dark"),
    "darkelf": Masonry("darkelf", "obsidian", "obsidian_dark", "silver", "obsidian_light", 4.4, 1.2, course=0.55,
                       spikes=True, walkmat="obsidian_dark"),
    "sandstone": Masonry("sandstone", "sand", "sand_dark", "sand_light", "sand_light", 3.6, 1.4, course=0.6,
                         walkmat="sand_dark"),
    "foxfolk": Masonry("foxfolk", "plaster", "timber", "lacquer", "plaster_warm", 3.2, 1.0, course=0.8,
                       walkmat="wood"),
    "catfolk": Masonry("catfolk", "adobe_light", "adobe_dark", "tile_blue", "adobe", 3.4, 1.2, course=0.7,
                       bands=(2.75,), band_mat="tile_blue", walkmat="adobe_dark"),
    "orc": OrcPalisade(),
    "reed": ReedWall(),
    "stockade": Stockade(),
}
WALLS["iron"].roof = ("slate", "slate_dark")
WALLS["dwarf"].roof = ("slate", "slate_dark")
WALLS["elf"].roof = ("leaves", "leaves_dark")
WALLS["darkelf"].roof = ("violet", "obsidian_dark")
WALLS["foxfolk"].roof = ("slate", "slate_dark")
WALLS["catfolk"].roof = ("tile_blue", "tile_blue_dark")


# --- Pieces ----------------------------------------------------------------------------------


def straight(p, W):
    W.run(p, -1.0, 1.0)


def half(p, W):
    W.run(p, -0.5, 0.5, phase=0.0)


def junction(p, W, arms):
    W.node(p, set(arms))
    for d in arms:
        W.arm(p, d)


def corner(p, W):
    junction(p, W, "EN")


def tee(p, W):
    junction(p, W, "EWN")


def cross(p, W):
    junction(p, W, "EWNS")


def end(p, W):
    junction(p, W, "W")


def pillar(p, W):
    junction(p, W, "")


def slit(p, W):
    """Straight with an arrow slit (tall walls) or a shuttered window."""
    W.run(p, -1.0, 1.0)
    y = W.t / 2 + 0.02
    if isinstance(W, Palisade):   # A shooting hatch framed in timber.
        for s in (-1, 1):
            p.box((0, s * 0.2, 1.75), (0.62, 0.1, 0.72), "timber")
            p.box((0, s * 0.235, 1.75), (0.4, 0.06, 0.5), "dark")
            p.box((0, s * 0.27, 2.14), (0.56, 0.05, 0.1), "iron")
        p.box((0, -0.3, 1.52), (0.44, 0.05, 0.5), "wood", rz=0)
        return
    zc = min(1.9, W.h * 0.6)
    tall = W.h >= 2.9
    for s in (-1, 1):
        if tall:   # A cross-shaped loophole in a dressed stone frame.
            p.box((0, s * y, zc), (0.46, 0.12, 1.3), W.frame_mat)
            p.box((0, s * (y + 0.035), zc), (0.1, 0.07, 1.05), "dark")
            p.box((0, s * (y + 0.035), zc + 0.12), (0.3, 0.07, 0.1), "dark")
            p.box((0, s * y, zc - 0.7), (0.6, 0.16, 0.1), W.frame_mat)
        else:      # A small window with shutters.
            p.box((0, s * y, zc), (0.66, 0.1, 0.66), W.frame_mat)
            p.box((0, s * (y + 0.03), zc), (0.5, 0.07, 0.5), "dark")
            for dx in (-0.42, 0.42):
                p.box((dx, s * (y + 0.03), zc), (0.24, 0.05, 0.56), "shutter")
            p.box((0, s * (y + 0.05), zc), (0.04, 0.05, 0.5), "iron")


def breach(p, W):
    """A stretch knocked down by raiders: ragged stumps and rubble."""
    W.run(p, -1.0, -0.6, foot=True) if isinstance(W, Masonry) else W.run(p, -1.0, -0.6)
    W.run(p, 0.62, 1.0)
    hb = W.h
    W.body(p, -0.6, -0.25, 0.0, hb * 0.62)
    W.body(p, -0.25, 0.25, 0.0, hb * 0.22)
    W.body(p, 0.25, 0.62, 0.0, hb * 0.42)
    rubble(p, -0.7, 0.7, W.t / 2, W.rubble_mats, W.key, n=14, size=min(0.4, 0.2 + W.h * 0.05))
    if isinstance(W, Palisade):
        p.cyl((-0.5, -0.5, 0.18), (0.75, -0.95, 0.18), 0.18, 0.17, "log", seg=7)
        p.cyl((0.1, 0.45, 0.16), (0.9, 0.8, 0.5), 0.17, 0.0, "log_end", seg=7)


def building(p, W):
    """Under construction: the wall half raised inside a scaffold."""
    hb = max(0.6, W.h * 0.55)
    W.body(p, -1.0, 1.0, 0.0, hb)
    if W.h >= 2.0:
        scaffold(p, -1.0, 1.0, -W.t / 2, hb, side=-1)
    else:   # Low walls: a string line on stakes and a pile of material.
        for x in (-0.9, 0.9):
            p.cyl((x, -W.t / 2 - 0.25, 0), (x, -W.t / 2 - 0.25, W.h + 0.25), 0.03, 0.02, "timber", seg=5)
        p.box((0, -W.t / 2 - 0.25, W.h + 0.15), (1.8, 0.015, 0.015), "rope")
    r = rng("pile", W.key)
    for i in range(7):   # Material waiting at the foot.
        p.box((r.uniform(-0.7, 0.2), W.t / 2 + r.uniform(0.2, 0.55), 0.1 + 0.16 * (i % 3)),
              (0.36, 0.26, 0.16), r.choice(W.rubble_mats), rz=r.uniform(-12, 12))
    if isinstance(W, Hedge):
        for x in (-0.6, 0.0, 0.6):
            p.cyl((x, 0.3, 0), (x, 0.3, 1.5), 0.03, 0.025, "timber", seg=5)


def step(p, W):
    """A 1 m rise for sloped ground: the right half stands 1 m higher."""
    W.run(p, -1.0, 0.0)
    W.body(p, 0.0, 1.0, 0.0, 1.0)
    if isinstance(W, Masonry):
        W.run(p, 0.0, 1.0, base=1.0, foot=False)
    else:
        W.run(p, 0.0, 1.0, base=1.0)
    if W.walk is not None:   # Five steps on the walkway.
        wide = W.t - 0.34
        for i in range(5):
            p.box((-0.9 + i * 0.2, 0, W.h + (i + 1) * 0.1), (0.2, wide, (i + 1) * 0.2),
                  "wood_light" if W.stair_wood else W.walkmat)


def stairs_length(W):
    return 2 * math.ceil(W.h / 2 - 0.01)


def stairs(p, W):
    """Stairs up to the walkway on the inner (+Y) side. The piece is
    stairs_length(W) long and 1 m deeper than the wall."""
    Ls = stairs_length(W)
    W.run(p, -Ls / 2, Ls / 2 - 1.0)
    W.run(p, Ls / 2 - 1.0, Ls / 2, sides=(-1,))
    n = round(W.h / 0.25)
    rise = W.h / n
    xs = Ls / 2 - n * 0.25
    y0 = W.t / 2 + (0.1 if not W.stair_wood else 0.09)
    yc = y0 + 0.45
    if W.stair_wood:
        for i in range(n):
            p.box((xs + (i + 0.5) * 0.25, yc, (i + 1) * rise - 0.03), (0.28, 0.9, 0.06),
                  "wood_light" if i % 2 else "wood")
        for y in (y0 + 0.04, y0 + 0.86):
            p.yprism([(xs, 0.0), (xs + 0.3, 0.0), (Ls / 2, W.h - 0.3), (Ls / 2, W.h - 0.06), (xs, rise - 0.06)],
                     y - 0.04, y + 0.04, "timber")
        for i in range(2, n, 3):
            x = xs + (i + 0.5) * 0.25
            p.box((x, y0 + 0.86, (i + 1) * rise / 2 + 0.5), (0.1, 0.1, (i + 1) * rise + 1.0), "timber")
        p.beam((xs, y0 + 0.86, rise + 0.95), (Ls / 2, y0 + 0.86, W.h + 0.95), 0.07, "wood")
    else:
        for i in range(n):
            top = (i + 1) * rise
            p.box((xs + (i + 0.5) * 0.25, yc, top / 2), (0.25, 0.9, top), W.mat if i % 2 else W.light)
        p.yprism([(xs, 0.0), (Ls / 2, 0.0), (Ls / 2, W.h + 0.35), (Ls / 2 - 0.25, W.h + 0.35), (xs, rise + 0.35)],
                 y0 + 0.9, y0 + 1.0, W.dark)


def torch(p, W):
    """Straight with a brazier on the wall top. Returns its Mech."""
    W.run(p, -1.0, 1.0)
    y, z, pole = W.torch_at()
    if W.walk is None and abs(y) > 0.01:   # A pole strapped to the face.
        for zb in (z + 0.25, z + pole * 0.55):
            p.box((0, y, zb), (0.14, 0.12, 0.07), "iron")
    if isinstance(W, Hedge):
        p.box((0, y, pole * 0.5), (0.12, 0.12, pole), "timber")
        z, pole = pole, 0.3
    pt = brazier(p, 0.0, y, z, pole)
    if p.static:
        return None
    return flame_mech([pt])


def stile(p, W):
    """Low walls: stone steps over the wall, so villagers cross and
    livestock does not."""
    W.run(p, -1.0, 1.0)
    for s in (-1, 1):
        for i in range(3):
            z = 0.3 * (i + 1)
            p.box((0, s * (W.t / 2 + 0.75 - i * 0.28), z - 0.05), (0.7, 0.32, 0.1), "stone_light")
            p.box((0, s * (W.t / 2 + 0.75 - i * 0.28), (z - 0.1) / 2), (0.5, 0.2, max(0.02, z - 0.1)), "stone_dark")
    p.box((0, 0, W.h + 0.18), (0.72, W.t + 0.1, 0.1), "stone_light")
    for x in (-0.42, 0.42):
        p.cyl((x, 0, W.h), (x, 0, W.h + 1.0), 0.04, 0.035, "timber", seg=6)


def arch(p, W):
    """Hedge: an arch cut through for villagers to walk under."""
    W.run(p, -1.0, -0.55)
    W.run(p, 0.55, 1.0)
    W.run(p, -0.55, 0.55, floor=1.9, h=2.5)
    W.run(p, -1.0, -0.55, floor=W.h - 0.1, h=2.4)
    W.run(p, 0.55, 1.0, floor=W.h - 0.1, h=2.4)
    for x in (-0.55, 0.55):
        for y in (-0.3, 0.3):
            p.cyl((x, y, 0), (x, y, 1.95), 0.04, 0.035, "timber", seg=5)
    for y in (-0.3, 0.3):
        p.box((0, y, 1.95), (1.2, 0.05, 0.05), "timber")


def buttress(p, W):
    """Straight with a sloped buttress on both faces."""
    W.run(p, -1.0, 1.0)
    hb = W.h * 0.8
    for s in (-1, 1):
        y0 = s * W.t / 2
        pts = [(y0, 0.0), (y0 + s * 0.7, 0.0), (y0 + s * 0.7, 0.4), (y0 + s * 0.12, hb), (y0, hb)]
        if s < 0:
            pts = pts[::-1]
        p.xprism(pts, -0.3, 0.3, W.mat)
        p.box((0, y0 + s * 0.36, 0.2), (0.7, 0.72, 0.4), W.dark)


def drain(p, W):
    """Straight with a barred culvert at the foot (a stream or a moat
    passes under the wall)."""
    W.run(p, -1.0, -0.5)
    W.run(p, 0.5, 1.0)
    W.run(p, -0.5, 0.5, floor=0.75)
    p.box((0, 0, 0.82), (1.3, W.t + 0.12, 0.2), W.frame_mat)
    for x in (-0.3, -0.1, 0.1, 0.3):
        for s in (-1, 1):
            p.cyl((x, s * (W.t / 2 - 0.1), 0), (x, s * (W.t / 2 - 0.1), 0.75), 0.03, 0.03, "iron_dark", seg=5)
    p.box((0, 0, 0.04), (1.0, W.t + 1.0, 0.08), "water")


def banner(p, W):
    """Straight with the town's banner hanging on the outer face."""
    W.run(p, -1.0, 1.0)
    y = -(W.t / 2 + (0.14 if W.walk else 0.06))
    zt = W.h + (0.45 if W.walk else -0.15)
    p.box((0, y, zt), (1.0, 0.06, 0.06), "timber")
    p.box((0, y - 0.01, zt - 0.85), (0.8, 0.03, 1.6), "cloth_red")
    for x in (-0.4, 0.0):   # A swallow tail.
        p.yprism([(x, zt - 1.64), (x + 0.4, zt - 1.64), (x + 0.2, zt - 2.0)], y - 0.025, y + 0.005, "cloth_red")
    p.box((0, y - 0.03, zt - 0.8), (0.34, 0.02, 0.34), "gold", rz=0)


def diagonal(p, W):
    """A stretch at 45 degrees, from one corner of the cell to the opposite
    one (2.83 m), for walls drawn diagonally."""
    W.run(p.at(rot=45.0), -1.4142, 1.4142, phase=0.0)


def roofed(p, W):
    """Walls with a walkway: a straight whose walkway is covered by a
    gabled roof on posts."""
    W.run(p, -1.0, 1.0)
    top = W.h + 1.1
    yo = W.half + 0.1 - W.pw / 2 if not W.stair_wood else W.half + 0.03
    for x in (-0.5, 0.5):
        for s in (-1, 1):
            p.box((x, s * yo, top + 0.55), (0.12, 0.12, 1.1), "timber")
        p.box((x, 0, top + 1.1), (0.12, 2 * yo + 0.3, 0.12), "timber")
        p.beam((x, -yo, top + 1.1), (x, 0, top + 1.1 + yo * 0.75), 0.09, "timber")
        p.beam((x, yo, top + 1.1), (x, 0, top + 1.1 + yo * 0.75), 0.09, "timber")
    for s in (-1, 1):
        p.box((0, s * yo, top + 1.1), (2.0, 0.12, 0.12), "timber")
    w = yo + 0.45
    rise = w * 0.75
    mats = ("thatch", "thatch_dark") if W.stair_wood else W.roof
    p.xprism([(-w, top + 1.16), (w, top + 1.16), (0, top + 1.16 + rise)], -1.0, 1.0, mats[0])
    p.xprism([(-w * 0.55, top + 1.2 + rise * 0.45), (w * 0.55, top + 1.2 + rise * 0.45), (0, top + 1.2 + rise)],
             -1.0, 1.0, mats[1])
    p.box((0, 0, top + 1.2 + rise), (2.0, 0.14, 0.1), mats[1])


PIECES = {
    "diagonal": diagonal, "roofed": roofed,
    "straight": straight, "half": half, "corner": corner, "tee": tee, "cross": cross, "end": end,
    "pillar": pillar, "slit": slit, "breach": breach, "building": building, "step": step, "stairs": stairs,
    "torch": torch, "stile": stile, "arch": arch, "buttress": buttress, "drain": drain, "banner": banner,
}
