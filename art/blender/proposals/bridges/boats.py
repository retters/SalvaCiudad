"""Boats of the `bridges` family. Every boat floats with its waterline at
Z = 0 (part of the hull is below 0) and its bow toward -Y."""

import math

from parts import B, barrel, chain, crate, jit, lantern, lerp, log, planks_y, rope, sack, sag, save
import _kit as kit

MODELS = {}


def model(name, fn, **kw):
    MODELS[name] = lambda: fn(name, **kw)


class Hull:
    """A lofted hull: stations from the bow (t = 0, y = -length / 2) to the
    stern (t = 1), each a section of gunwale, bilge, chine and keel, with an
    inner skin so the planking has thickness."""

    def __init__(self, length, beam, depth, freeboard, tm=0.55, bow_p=0.8, stern_w=0.0, stern_p=0.7,
                 sheer_bow=0.3, sheer_stern=0.15, bow_rise=0.8, stern_rise=0.4, n=12, flat=0.5, thick=0.07):
        self.length, self.beam, self.depth, self.freeboard = length, beam, depth, freeboard
        self.tm, self.bow_p, self.stern_w, self.stern_p = tm, bow_p, stern_w, stern_p
        self.sheer_bow, self.sheer_stern = sheer_bow, sheer_stern
        self.bow_rise, self.stern_rise = bow_rise, stern_rise
        self.n, self.flat, self.thick = n, flat, thick

    def y(self, t):
        return -self.length / 2 + self.length * t

    def w(self, t):
        """Half-beam at the gunwale."""
        if t <= self.tm:
            f = math.sin(math.pi / 2 * t / self.tm) ** self.bow_p
        else:
            u = (t - self.tm) / (1 - self.tm)
            f = self.stern_w + (1 - self.stern_w) * max(0.0, math.cos(math.pi / 2 * u)) ** self.stern_p
        return max(0.03, self.beam / 2 * f)

    def top(self, t):
        if t <= self.tm:
            return self.freeboard + self.sheer_bow * (1 - t / self.tm) ** 2
        return self.freeboard + self.sheer_stern * ((t - self.tm) / (1 - self.tm)) ** 2

    def bot(self, t):
        if t <= self.tm:
            k = (1 - t / self.tm) ** 3 * self.bow_rise
        else:
            k = ((t - self.tm) / (1 - self.tm)) ** 3 * self.stern_rise
        return lerp(-self.depth, self.top(t) - 0.05, k)

    def section(self, t):
        w, zt, zb = self.w(t), self.top(t), self.bot(t)
        return [(w, zt), (w * 0.9, lerp(zb, zt, 0.45)), (w * self.flat, lerp(zb, zt, 0.08)), (0.0, zb)]

    def half_at(self, t, z):
        """Inner half-width of the hull at height z."""
        sec = self.section(t)
        if z >= sec[0][1]:
            return max(0.0, sec[0][0] - self.thick)
        for (xa, za), (xb, zb) in zip(sec, sec[1:]):
            if zb <= z <= za and za > zb:
                return max(0.0, lerp(xb, xa, (z - zb) / (za - zb)) - self.thick)
        return 0.0

    def ribs(self, b, ts, mat="timber", w=0.09):
        """Bare frames at the stations ts: a hull being built, or a wreck."""
        for t in ts:
            y = self.y(t)
            sec = self.section(t)
            prof = [(-x, z) for x, z in sec] + [(x, z) for x, z in reversed(sec[:-1])]
            for (xa, za), (xb, zb) in zip(prof, prof[1:]):
                b.beam((xa, y, za), (xb, y, zb), w, w, mat)

    def build(self, b, strakes=("wood", "wood_light", "wood"), inner="wood_light", rail="timber", posts=True,
              keel=True, stations=None):
        n, th = self.n, self.thick
        i0, i1 = stations or (0, n)
        pts, faces = [], []
        for i in range(i0, i1 + 1):
            t = i / n
            y = self.y(t)
            sec = self.section(t)
            zt = sec[0][1]
            prof = [(-x, z) for x, z in sec] + [(x, z) for x, z in reversed(sec[:-1])]
            pts += [(x, y, z) for x, z in prof]
            for k, (x, z) in enumerate(prof):
                xi = math.copysign(max(0.0, abs(x) - th), x) if x else 0.0
                pts.append((xi, y, zt if k in (0, 6) else min(zt, z + th)))

        def o(i, k):
            return (i - i0) * 14 + k

        def q(i, k):
            return (i - i0) * 14 + 7 + k

        for i in range(i0, i1):
            for k in range(6):
                faces.append(((o(i, k), o(i, k + 1), o(i + 1, k + 1), o(i + 1, k)), strakes[min(k, 5 - k)]))
                faces.append(((q(i, k), q(i + 1, k), q(i + 1, k + 1), q(i, k + 1)), inner))
            faces.append(((o(i, 0), o(i + 1, 0), q(i + 1, 0), q(i, 0)), rail))
            faces.append(((o(i, 6), q(i, 6), q(i + 1, 6), o(i + 1, 6)), rail))
        for i in (i0, i1):
            for k in range(6):
                faces.append(((o(i, k), o(i, k + 1), q(i, k + 1), q(i, k)), strakes[min(k, 5 - k)]))
        b.mesh(pts, faces)
        for i in range(i0, i1):   # Gunwale rails and the keel.
            ta, tb = i / n, (i + 1) / n
            for s in (-1, 1):
                b.beam((s * self.w(ta), self.y(ta), self.top(ta)), (s * self.w(tb), self.y(tb), self.top(tb)),
                       th + 0.05, 0.07, rail)
            if keel:
                b.beam((0, self.y(ta), self.bot(ta) - 0.02), (0, self.y(tb), self.bot(tb) - 0.02), 0.1, 0.12, rail)
        if posts:
            y0, y1 = self.y(0), self.y(1)
            if i0 == 0:
                b.beam((0, y0 - 0.02, self.bot(0) - 0.05), (0, y0 - 0.1, self.top(0) + 0.22), 0.11, 0.14, rail)
            if self.stern_w < 0.1 and i1 == n:
                b.beam((0, y1 + 0.02, self.bot(1) - 0.05), (0, y1 + 0.1, self.top(1) + 0.22), 0.11, 0.14, rail)

    def deck(self, b, z, t0, t1, mat="plank", thick=0.05, steps=None, alt=None):
        steps = steps or max(2, round((t1 - t0) * self.n))
        for i in range(steps):
            ta, tb = lerp(t0, t1, i / steps), lerp(t0, t1, (i + 1) / steps)
            if z < self.bot(ta) or z < self.bot(tb):
                continue   # The bottom has risen above this deck: nothing to cover.
            wa, wb = self.half_at(ta, z) + 0.01, self.half_at(tb, z) + 0.01
            ya, yb = self.y(ta), self.y(tb)
            ring = [(-wa, ya), (wa, ya), (wb, yb), (-wb, yb)]
            b.solid([(x, y, z - thick) for x, y in ring], [(x, y, z) for x, y in ring],
                    alt if alt and i % 2 else mat)

    def thwart(self, b, t, drop=0.2, mat="wood", wide=0.26):
        z = self.top(t) - drop
        b.box((0, self.y(t), z), (2 * self.half_at(t, z) + 0.04, wide, 0.05), mat)


# --- Rigging and motion --------------------------------------------------------------


def sail(b, bones, prefix, width, y, z_top, z_bot, mats, bulge=0.5, bands=3, strips=6, top_scale=1.0,
         parent="hull"):
    """A sail of rigid bands hinged one under the other, so it can flutter.
    It bulges toward the bow."""
    def point(u, v):
        x = lerp(-width / 2, width / 2, u) * lerp(top_scale, 1.0, v)
        return (x, y - bulge * (1 - (2 * u - 1) ** 2) * (0.25 + 0.75 * math.sin(math.pi * v * 0.8)),
                lerp(z_top, z_bot, v))

    for j in range(bands):
        name = "%s%d" % (prefix, j)
        v0, v1 = j / bands, (j + 1) / bands
        zh = lerp(z_top, z_bot, v0)
        bones.append((name, (0, y, zh), (0, y, zh + 0.3), parent if j == 0 else "%s%d" % (prefix, j - 1)))
        band = b.bone(name)
        for i in range(strips):
            u0, u1 = i / strips, (i + 1) / strips
            ring = [point(u0, v1), point(u1, v1), point(u1, v0), point(u0, v0)]
            band.solid(ring, [(px, py + 0.04, pz) for px, py, pz in ring], mats[i % len(mats)])


def mast(b, y, z0, height, r=0.09, yard=None, yard_z=None):
    b.cyl((0, y, z0), (0, y, z0 + height), r, "timber", r2=r * 0.65, seg=7)
    b.cyl((0, y, z0 + height), (0, y, z0 + height + 0.12), r * 0.9, "wood_light", r2=0.02, seg=7)
    if yard:
        b.cyl((-yard / 2, y - r - 0.04, yard_z), (yard / 2, y - r - 0.04, yard_z), 0.055, "wood", seg=6)
        b.cyl((0, y - r - 0.1, yard_z - 0.07), (0, y + 0.02, yard_z + 0.07), 0.07, "rope", seg=6)


def pennant(b, bones, y, z, mat="cloth_red", size=0.9, parent="hull"):
    bones.append(("flag", (0, y, z), (0, y, z + 0.3), parent))
    f = b.bone("flag")
    f.solid([(0, y, z), (0, y, z + 0.35), (0, y + size, z + 0.2)],
            [(0.025, y, z), (0.025, y, z + 0.35), (0.025, y + size, z + 0.2)], mat)


def floating(roll=3.0, pitch=1.2, heave=0.04):
    def pose(t):
        a = 2 * math.pi * t
        return ({"hull": [(kit.Y, roll * math.sin(a)), (kit.X, pitch * math.sin(a + 1.2))]},
                {"hull": (0.0, 0.0, heave * math.sin(a + 0.5))})
    return pose


def flutter(prefix, bands=3, amp=3.0, cycles=2):
    def pose(t):
        return {"%s%d" % (prefix, j): [(kit.X, amp * (0.6 + 0.5 * j) * math.sin(2 * math.pi * cycles * t - j * 0.9))]
                for j in range(bands)}, {}
    return pose


def waving(cycles=3, amp=18.0):
    return lambda t: ({"flag": [(kit.Z, amp * math.sin(2 * math.pi * cycles * t))]}, {})


def rowing(oars, sweep=24.0, lift=7.0, cycles=1):
    """`oars` is a list of (bone, side), side -1 for port (x < 0)."""
    def pose(t):
        a = 2 * math.pi * cycles * t
        turns = {}
        for bone, side in oars:
            up = lift * (1 - math.cos(a))
            turns[bone] = [(kit.Y, -side * up), (kit.Z, side * sweep * math.sin(a))]
        return turns, {}
    return pose


def merge(*poses):
    def pose(t):
        turns, moves = {}, {}
        for p in poses:
            a, m = p(t)
            turns.update(a)
            moves.update(m)
        return turns, moves
    return pose


def oar(b, bones, name, pivot, side, out=1.7, inboard=0.55, drop=0.55, parent="hull", blade="wood_light"):
    px, py, pz = pivot
    bones.append((name, pivot, (px, py, pz + 0.3), parent))
    o = b.bone(name)
    tip = (px + side * out, py, pz - drop)
    o.cyl((px - side * inboard, py, pz + drop * inboard / out), tip, 0.03, "wood", seg=5)
    mid = (px + side * (out - 0.55), py, pz - drop * (out - 0.55) / out)
    o.beam(mid, (tip[0] + side * 0.05, py, tip[2] - 0.02), 0.03, 0.17, blade)
    b.box((px, py, pz), (0.1, 0.07, 0.1), "iron")


def finish(b, name, bones, clips):
    mech = kit.Mech([("hull", (0, 0, 0), (0, 0, 0.5), None)] + bones)
    for clip, seconds, pose, speed in clips:
        mech.clip(clip, seconds, pose, speed=speed)
    save(b, name, mech=mech)


def rudder(b, h, mat="wood_dark", size=0.5):
    y = h.y(1) + 0.08
    b.box((0, y + size * 0.35, (h.bot(1) + h.top(1)) / 2 - 0.1), (0.06, size * 0.7, h.top(1) - h.bot(1) + 0.2), mat)
    b.beam((0, y + 0.1, h.top(1) + 0.15), (0, y - 0.9, h.top(1) + 0.3), 0.05, 0.06, "timber")


# --- Boats ---------------------------------------------------------------------------


def rowboat(name, strakes=("wood", "wood_light", "wood"), rail="timber", beached=False):
    # Beached: hauled out on the shore, lying on its bilge, with the oars inside. Z = 0 is the ground.
    root = B().at(dz=0.3).turn("Y", 16) if beached else B()
    b = root if beached else root.bone("hull")
    bones = []
    h = Hull(4.2, 1.5, 0.28, 0.4, stern_w=0.55, sheer_bow=0.22, sheer_stern=0.08, stern_rise=0.3, n=10,
             thick=0.06)
    h.build(b, strakes=strakes, rail=rail)
    # The floor boards stay above the waterline, so the water never shows inside the hull.
    h.deck(b, 0.04, 0.08, 0.995, mat="plank", alt="plank_b")
    for t in (0.36, 0.62):
        h.thwart(b, t)
    h.thwart(b, 0.93, drop=0.16, wide=0.4)
    h.thwart(b, 0.1, drop=0.14, wide=0.35)
    b.cyl((0, h.y(0.03), h.top(0.03)), (0, h.y(0.03), h.top(0.03) + 0.1), 0.05, "iron", seg=6)
    if beached:
        for s in (-1, 1):
            b.cyl((s * 0.25, h.y(0.2), 0.3), (s * 0.3, h.y(0.85), 0.25), 0.03, "wood", seg=5)
            b.box((s * 0.3, h.y(0.82), 0.25), (0.16, 0.5, 0.03), "wood_light")
        flat = B(root.mb)   # The mooring line and its stake lie on the ground, not tilted.
        rope(flat, sag((0.1, h.y(0.03), 0.75), (1.4, h.y(0.0) - 1.6, 0.35), 0.25, 5), r=0.02)
        flat.cyl((1.4, h.y(0.0) - 1.6, -0.3), (1.45, h.y(0.0) - 1.65, 0.45), 0.05, "timber", seg=5)
        flat.cyl((-1.3, h.y(0.6), 0.0), (-0.75, h.y(0.6), 0.5), 0.05, "wood", seg=5)
        save(root, name)
        return
    for s, bone in ((-1, "oar_l"), (1, "oar_r")):
        oar(b, bones, bone, (s * h.w(0.5), h.y(0.5), h.top(0.5) + 0.06), s)
    rope(b, sag((0, h.y(0.03), h.top(0.03) + 0.05), (0.2, h.y(0.16), 0.06), 0.05, 4), r=0.02)
    oars = [("oar_l", -1), ("oar_r", 1)]
    finish(root, name, bones, [("bob", 3.0, floating(4.0, 1.5, 0.04), None),
                               ("row", 2.0, merge(floating(1.5, 1.0, 0.02), rowing(oars)), 1.4)])


def furled_sail(b, width, y, z, mat):
    """A sail gathered and tied on its yard, for a boat at its mooring."""
    b.cyl((-width / 2, y, z), (width / 2, y, z), 0.035 * width + 0.03, mat, seg=7)
    n = max(3, round(width / 0.8))
    for k in range(n):
        x = -width / 2 + (k + 0.5) * width / n
        b.cyl((x - 0.04, y, z), (x + 0.04, y, z), 0.035 * width + 0.055, "rope", seg=7)


def fishing_boat(name, sail_mats=("canvas", "canvas_shade"), strakes=("wood_dark", "wood", "wood"), furled=False):
    root = B()
    b = root.bone("hull")
    bones = []
    h = Hull(6.6, 2.3, 0.5, 0.62, stern_w=0.45, sheer_bow=0.4, sheer_stern=0.18, n=12)
    h.build(b, strakes=strakes)
    h.deck(b, 0.05, 0.12, 0.995, mat="plank", alt="plank_b")
    h.deck(b, h.top(0.12) - 0.12, 0.02, 0.22, mat="wood")      # Foredeck.
    h.thwart(b, 0.42, drop=0.12, wide=0.3)
    h.thwart(b, 0.9, drop=0.14, wide=0.5)
    ym = h.y(0.42)
    mast(b, ym, 0.0, 4.6, r=0.08, yard=3.0, yard_z=4.1)
    if furled:
        furled_sail(b, 2.6, ym - 0.14, 3.98, sail_mats[0])
    else:
        sail(b, bones, "sail", 2.8, ym - 0.13, 4.05, 1.45, sail_mats, bulge=0.4, top_scale=0.75)
    rope(b, [(0, ym, 4.5), (0, h.y(0.0) - 0.05, h.top(0) + 0.2)], r=0.018)
    for s in (-1, 1):
        rope(b, [(0, ym, 4.4), (s * h.w(0.55), h.y(0.55), h.top(0.55))], r=0.018)
    rudder(b, h)
    # Nets, a fish basket and floats.
    for k in range(4):
        b.sphere((jit(k, 0.3, 1), h.y(0.72) + jit(k, 0.35, 2), 0.2 + 0.08 * k), 0.34 - 0.04 * k, "net", seg=6,
                 rings=4, scale=(1.2, 1.0, 0.5))
    for k in range(3):
        b.sphere((0.35 - 0.3 * k, h.y(0.78), 0.42), 0.07, "paint_red", seg=5, rings=3)
    barrel(b, -0.55, h.y(0.28), z=0.05, h=0.55, r=0.24)
    b.cyl((0.5, h.y(0.3), 0.05), (0.5, h.y(0.3), 0.35), 0.24, "thatch_dark", r2=0.3, seg=8)
    for k in range(4):
        b.box((0.5 + jit(k, 0.1), h.y(0.3) + jit(k, 0.1, 3), 0.37), (0.1, 0.3, 0.06), "fish", rz=k * 0.8)
    pennant(b, bones, ym, 4.5, mat="cloth_blue", size=0.6)
    finish(root, name, bones, [("bob", 3.0, merge(floating(3.5, 1.5, 0.04), waving(2, 10)), None),
                               ("sail", 4.0, merge(floating(4.0, 1.5, 0.05), flutter("sail", amp=2.5), waving()),
                                2.0)])


def raft_ferry(name, cargo=True, cart=False):
    root = B()
    b = root.bone("hull")
    bones = []
    wide, long_ = 4.0, 5.0
    n = 11
    for i in range(n):
        x = -wide / 2 + 0.18 + i * (wide - 0.36) / (n - 1)
        log(b, (x, -long_ / 2 + jit(i, 0.12), 0.02), (x, long_ / 2 + jit(i, 0.12, 2), 0.02), 0.18, seg=7)
    for y in (-1.9, 0.0, 1.9):
        b.box((0, y, 0.24), (wide + 0.1, 0.16, 0.12), "timber")
        for x in (-1.7, -0.6, 0.6, 1.7):
            b.cyl((x, y, 0.2), (x, y, 0.32), 0.1, "rope", seg=6)
    planks_y(b, -1.85, 1.85, wide - 0.5, z=0.37, step=0.32)
    deck = 0.37
    for s in (-1, 1):
        x = s * (wide / 2 - 0.2)
        for y in (-1.8, 0.0, 1.8):
            b.box((x, y, deck + 0.5), (0.1, 0.1, 1.0), "timber")
        b.box((x, 0, deck + 0.95), (0.08, 3.7, 0.08), "wood")
        b.box((x, 0, deck + 0.5), (0.05, 3.7, 0.06), "wood")
    # The guide rope runs along the crossing, through two rollers on the upstream side.
    xr = wide / 2 - 0.2
    for k, y in enumerate((-1.8, 1.8)):
        b.box((xr, y, deck + 1.25), (0.14, 0.14, 0.5), "timber")
        name_k = "roller%d" % k
        bones.append((name_k, (xr + 0.16, y, deck + 1.4), (xr + 0.16, y, deck + 1.7), "hull"))
        r = b.bone(name_k)
        r.cyl((xr + 0.08, y, deck + 1.4), (xr + 0.24, y, deck + 1.4), 0.14, "wood_light", seg=8)
        r.box((xr + 0.16, y, deck + 1.4), (0.18, 0.05, 0.3), "iron")
    rope(root, sag((xr + 0.16, -4.2, 1.95), (xr + 0.16, 4.2, 1.95), -0.0, 6), r=0.035)
    b.cyl((-1.2, -1.5, deck), (-1.6, 1.9, deck + 1.9), 0.035, "wood_light", seg=5)   # The ferryman's pole.
    if cart:   # A loaded cart on board: what the ferry is for.
        b.box((0.1, 0.2, deck + 0.75), (1.3, 2.2, 0.12), "wood")
        for s in (-1, 1):
            b.box((0.1 + s * 0.62, 0.2, deck + 1.0), (0.07, 2.2, 0.45), "wood_light")
            b.cyl((0.1 + s * 0.78, 0.4, deck + 0.55), (0.1 + s * 0.88, 0.4, deck + 0.55), 0.55, "timber", seg=10)
            b.cyl((0.1 + s * 0.76, 0.4, deck + 0.55), (0.1 + s * 0.9, 0.4, deck + 0.55), 0.12, "iron", seg=6)
            b.beam((0.1 + s * 0.45, -0.9, deck + 0.75), (0.1 + s * 0.4, -2.3, deck + 0.3), 0.07, 0.07, "timber")
        b.box((0.1, 1.28, deck + 1.0), (1.3, 0.07, 0.45), "wood_light")
        b.cyl((0.1 - 0.7, 0.4, deck + 0.55), (0.1 + 0.7, 0.4, deck + 0.55), 0.05, "iron", seg=5)
        sack(b, -0.2, 0.7, z=deck + 0.81)
        sack(b, 0.35, 0.5, z=deck + 0.81)
        barrel(b, 0.1, -0.3, z=deck + 0.81, h=0.6, r=0.26)
    elif cargo:
        crate(b, -0.6, 0.9, z=deck, s=0.7)
        crate(b, 0.15, 1.05, z=deck, s=0.55, rz=0.3)
        barrel(b, -0.9, -0.2, z=deck)
        sack(b, 0.5, 0.2, z=deck)
        sack(b, 0.75, 0.55, z=deck)
    rollers = lambda t: ({"roller0": [(kit.X, 360 * 2 * t)], "roller1": [(kit.X, 360 * 2 * t)]}, {})
    finish(root, name, bones, [("bob", 3.0, floating(2.0, 1.5, 0.03), None),
                               ("cross", 3.0, merge(floating(2.0, 1.5, 0.03), rollers), 1.2)])


def merchant(name, sail_mats=("canvas", "canvas", "cloth_red"), trim="paint_red", flag="cloth_red", war=False,
             furled=False):
    root = B()
    b = root.bone("hull")
    bones = []
    h = Hull(12.0, 4.2, 1.1, 1.5, tm=0.5, bow_p=0.7, stern_w=0.5, stern_p=0.6, sheer_bow=0.9, sheer_stern=0.7,
             bow_rise=0.75, stern_rise=0.5, n=14, thick=0.1)
    h.build(b, strakes=(trim, "wood", "wood_dark"), inner="wood")
    dz = 1.0
    h.deck(b, dz, 0.06, 0.98, mat="plank", alt="plank_b", steps=22)
    # Aftercastle: a raised deck with a rail, a cabin wall below and a lantern.
    ya, yb = h.y(0.72), h.y(1.0) + 0.25
    wc = h.w(0.8) + 0.12
    zc = h.top(1.0) + 0.2
    b.box((0, (ya + yb) / 2, zc), (2 * wc, yb - ya, 0.12), "plank_b")
    b.box((0, ya + 0.06, (dz + zc) / 2), (2 * h.half_at(0.72, dz + 0.3) + 0.1, 0.12, zc - dz), "wood")
    b.box((0.0, ya - 0.01, dz + 0.55), (0.6, 0.06, 1.1), "door")
    for s in (-1, 1):
        b.box((s * 1.1, ya - 0.01, dz + 0.75), (0.4, 0.05, 0.35), "window")
        for k in range(4):
            yk = lerp(ya + 0.1, yb - 0.1, k / 3)
            b.box((s * (wc - 0.07), yk, zc + 0.45), (0.1, 0.1, 0.8), "timber")
        b.box((s * (wc - 0.07), (ya + yb) / 2, zc + 0.82), (0.1, yb - ya, 0.1), trim)
        b.box((s * (wc - 0.07), (ya + yb) / 2, zc + 0.42), (0.06, yb - ya, 0.3), "wood")
        b.beam((s * 0.9, ya - 1.0, dz), (s * 0.9, ya, zc), 0.5, 0.06, "wood")     # Steps up.
    b.box((0, yb - 0.05, zc + 0.82), (2 * wc, 0.1, 0.1), trim)
    b.box((0, yb - 0.05, zc + 0.42), (2 * wc - 0.2, 0.06, 0.7), "wood")
    b.box((0, ya + 0.05, zc + 0.82), (2 * wc, 0.1, 0.1), trim)
    b.box((0, yb + 0.02, zc + 1.2), (0.06, 0.06, 0.7), "iron")
    lantern(b, 0, yb + 0.02, zc + 1.8)
    # Forecastle: a small triangular deck over the bow.
    yf0, yf1 = h.y(0.0) - 0.15, h.y(0.2)
    zf = h.top(0.05) + 0.15
    wf = h.w(0.2) + 0.1
    tri = [(0, yf0), (wf, yf1), (-wf, yf1)]
    b.xy(tri, zf, zf + 0.12, "plank_b")
    for s in (-1, 1):
        b.beam((0, yf0, zf + 0.75), (s * wf, yf1, zf + 0.75), 0.1, 0.1, trim)
        b.beam((0, yf0, zf + 0.4), (s * wf, yf1, zf + 0.4), 0.06, 0.4, "wood")
        b.box((s * wf, yf1, zf + 0.4), (0.1, 0.1, 0.8), "timber")
    b.box((0, yf1, zf + 0.75), (2 * wf, 0.1, 0.1), trim)
    b.beam((0, yf0, zf + 0.5), (0, yf0 - 2.2, zf + 1.5), 0.1, 0.1, "timber")     # Bowsprit.
    # Mast, yard, sail, shrouds and a crow's nest.
    ym = h.y(0.46)
    top = dz + 9.0
    mast(b, ym, dz, 9.0, r=0.16, yard=6.2, yard_z=top - 1.3)
    b.cyl((0, ym, top - 0.9), (0, ym, top - 0.45), 0.34, "wood", r2=0.42, seg=8)
    if furled:   # The sail gathered on the yard, for a ship at anchor.
        b.cyl((-2.9, ym - 0.26, top - 1.52), (2.9, ym - 0.26, top - 1.52), 0.2, sail_mats[0], seg=7)
        for k in range(7):
            x = -2.7 + k * 0.9
            b.cyl((x - 0.04, ym - 0.26, top - 1.52), (x + 0.04, ym - 0.26, top - 1.52), 0.225, "rope", seg=7)
    else:
        sail(b, bones, "sail", 5.8, ym - 0.24, top - 1.4, dz + 2.0, sail_mats, bulge=0.9, strips=9)
    if war:   # Battlements on the castles, shields on the rail and a ballista at the bow.
        for s in (-1, 1):
            for k in range(4):
                b.box((s * (wc - 0.07), lerp(ya + 0.3, yb - 0.3, k / 3), zc + 1.0), (0.16, 0.42, 0.3), trim)
            for k in range(5):
                t = 0.3 + k * 0.08
                b.cyl((s * (h.w(t) + 0.04), h.y(t), h.top(t) - 0.3), (s * (h.w(t) + 0.1), h.y(t), h.top(t) - 0.3),
                      0.36, sail_mats[k % 2], seg=9)
                b.cyl((s * (h.w(t) + 0.09), h.y(t), h.top(t) - 0.3), (s * (h.w(t) + 0.15), h.y(t), h.top(t) - 0.3),
                      0.1, "iron", seg=6)
        for k in range(3):
            b.box((lerp(-wc + 0.3, wc - 0.3, k / 2), yb - 0.05, zc + 1.0), (0.42, 0.16, 0.3), trim)
        by = (yf0 + yf1) / 2 + 0.5
        b.box((0, by, zf + 0.4), (0.3, 0.3, 0.6), "timber")
        b.beam((0, by + 0.7, zf + 0.75), (0, by - 0.9, zf + 0.95), 0.14, 0.12, "wood")
        for s in (-1, 1):
            b.beam((0, by - 0.7, zf + 0.92), (s * 0.9, by - 0.35, zf + 0.9), 0.07, 0.07, "wood_light")
            rope(b, [(s * 0.9, by - 0.35, zf + 0.9), (0, by + 0.5, zf + 0.8)], r=0.015)
        b.cyl((0, by + 0.5, zf + 0.9), (0, by - 1.3, zf + 1.1), 0.025, "iron", seg=5)
    for s in (-1, 1):
        for dy in (-0.7, 0.0, 0.7):
            rope(b, [(s * 0.2, ym, top - 1.0), (s * h.w(0.5), ym + 0.5 + dy, h.top(0.5))], r=0.022)
        for k in range(5):
            f = 0.15 + k * 0.14
            xa = lerp(s * h.w(0.5), s * 0.2, f)
            b.beam((xa, ym + 0.5 - 0.7 * (1 - f), lerp(h.top(0.5), top - 1.0, f)),
                   (xa, ym + 0.5 + 0.7 * (1 - f), lerp(h.top(0.5), top - 1.0, f)), 0.03, 0.03, "rope")
    rope(b, [(0, ym, top - 0.3), (0, yf0 - 2.1, zf + 1.48)], r=0.022)
    rope(b, [(0, ym, top - 0.3), (0, yb, zc + 0.9)], r=0.022)
    pennant(b, bones, ym, top + 0.1, mat=flag, size=1.4)
    rudder(b, h, size=0.9)
    # Cargo around the hatch, and an anchor at the bow.
    b.box((0, h.y(0.3), dz + 0.08), (1.6, 1.4, 0.16), "timber")
    b.box((0, h.y(0.3), dz + 0.17), (1.4, 1.2, 0.04), "wood_dark")
    crate(b, -1.1, h.y(0.6), z=dz, s=0.7)
    crate(b, -1.15, h.y(0.6) + 0.75, z=dz, s=0.6, rz=0.2)
    barrel(b, 1.1, h.y(0.6), z=dz)
    barrel(b, 1.2, h.y(0.6) + 0.7, z=dz)
    sack(b, 0.9, h.y(0.36), z=dz)
    chain(b, (h.w(0.12) + 0.05, h.y(0.12), h.top(0.12)), (h.w(0.12) + 0.08, h.y(0.12), 0.6))
    b.box((h.w(0.12) + 0.1, h.y(0.12), 0.35), (0.07, 0.07, 0.6), "iron")
    b.box((h.w(0.12) + 0.1, h.y(0.12), 0.1), (0.07, 0.6, 0.08), "iron")
    finish(root, name, bones, [("bob", 4.0, merge(floating(2.0, 1.0, 0.05), waving(3, 12)), None),
                               ("sail", 4.0, merge(floating(3.5, 1.2, 0.07), flutter("sail", amp=2.2), waving()),
                                2.5)])


def barge(name, cargo="mixed"):
    root = B()
    b = root.bone("hull")
    bones = []
    h = Hull(10.0, 3.2, 0.4, 0.55, tm=0.5, bow_p=0.3, stern_w=0.75, stern_p=0.4, sheer_bow=0.25, sheer_stern=0.1,
             bow_rise=0.6, stern_rise=0.3, n=12, flat=0.88, thick=0.09)
    h.build(b, strakes=("wood_dark", "wood", "tar"), inner="wood")
    dz = 0.1
    h.deck(b, dz, 0.05, 0.97, mat="plank", alt="plank_b", steps=20)
    # A small shelter at the stern and the long steering oar.
    ys = h.y(0.86)
    for s in (-1, 1):
        for dy in (-0.6, 0.6):
            b.box((s * 0.9, ys + dy, dz + 0.8), (0.1, 0.1, 1.6), "timber")
    for k in range(4):
        b.beam((-1.15, ys - 0.8 + k * 0.4, dz + 1.75 - 0.0), (1.15, ys - 0.8 + k * 0.4, dz + 1.75), 0.45, 0.06,
               "thatch" if k % 2 else "thatch_dark")
    bones.append(("sweep", (0, h.y(1.0), h.top(1.0) + 0.15), (0, h.y(1.0), h.top(1.0) + 0.45), "hull"))
    sw = b.bone("sweep")
    sw.cyl((0.2, h.y(0.82), dz + 1.2), (0, h.y(1.0) + 2.6, -0.35), 0.045, "wood", seg=6)
    sw.beam((0, h.y(1.0) + 1.9, 0.0), (0, h.y(1.0) + 2.7, -0.4), 0.04, 0.3, "wood_light")
    b.box((0, h.y(1.0), h.top(1.0) + 0.08), (0.2, 0.16, 0.2), "timber")
    for s in (-1, 1):   # Mooring bitts.
        for t in (0.1, 0.9):
            b.cyl((s * (h.w(t) - 0.2), h.y(t), dz), (s * (h.w(t) - 0.2), h.y(t), dz + 0.45), 0.07, "timber", seg=6)
    if cargo == "mixed":
        for i in range(3):
            for j in range(2):
                crate(b, -0.75 + j * 0.8, h.y(0.2) + i * 0.8, z=dz, s=0.72)
        crate(b, -0.35, h.y(0.2) + 0.4, z=dz + 0.72, s=0.66, rz=0.2)
        for i in range(3):
            for j in range(2):
                barrel(b, -0.4 + j * 0.75, h.y(0.48) + i * 0.7, z=dz)
        for i in range(6):
            sack(b, -0.6 + (i % 3) * 0.6, h.y(0.7) + (i // 3) * 0.55, z=dz)
        sack(b, 0.0, h.y(0.7) + 0.25, z=dz + 0.36)
    elif cargo == "logs":
        for r in range(3):
            for i in range(5 - r):
                x = (i - (4 - r) / 2) * 0.46
                log(b, (x, h.y(0.14), dz + 0.22 + r * 0.4), (x, h.y(0.74), dz + 0.22 + r * 0.4), 0.22, seg=7)
        for y in (h.y(0.25), h.y(0.62)):
            for s in (-1, 1):
                b.box((s * 1.2, y, dz + 0.6), (0.1, 0.1, 1.2), "timber")
    elif cargo == "stone":
        for i in range(4):
            for j in range(3):
                for k in range(2 if (i + j) % 2 else 1):
                    b.box((-0.8 + j * 0.8, h.y(0.27) + i * 1.25, dz + 0.25 + k * 0.5), (0.7, 1.1, 0.48),
                          "stone" if (i + j + k) % 2 else "stone_light", rz=jit(i * 3 + j, 0.05))
    sweep = lambda t: ({"sweep": [(kit.Z, 10 * math.sin(2 * math.pi * t))]}, {})
    finish(root, name, bones, [("bob", 4.0, merge(floating(1.5, 0.8, 0.03), sweep), None)])


def canoe(name, kind="dugout"):
    root = B()
    b = root.bone("hull")
    bones = []
    if kind == "dugout":
        h = Hull(4.8, 0.85, 0.22, 0.26, tm=0.5, bow_p=0.55, stern_p=0.55, sheer_bow=0.12, sheer_stern=0.1,
                 bow_rise=0.5, stern_rise=0.5, n=10, flat=0.7, thick=0.09)
        h.build(b, strakes=("log", "log", "log"), inner="log_end", rail="log_end", posts=False, keel=False)
    else:
        h = Hull(5.0, 0.95, 0.18, 0.3, tm=0.5, bow_p=0.75, stern_p=0.75, sheer_bow=0.32, sheer_stern=0.32,
                 bow_rise=0.9, stern_rise=0.9, n=12, flat=0.6, thick=0.04)
        h.build(b, strakes=("bark", "bark", "bark"), inner="wood_light", rail="timber", keel=False, posts=False)
        for t in (0.0, 1.0):   # Slim, raised ends.
            b.box((0, h.y(t), h.top(t) + 0.05), (0.07, 0.1, 0.3), "timber")
        for t in (0.2, 0.32, 0.44, 0.56, 0.68, 0.8):   # Ribs.
            z = h.top(t) - 0.03
            b.box((0, h.y(t), z), (2 * h.w(t), 0.05, 0.04), "timber")
        for s in (-1, 1):
            for t in (0.12, 0.88):
                b.box((s * (h.w(t) + 0.005), h.y(t), h.top(t) - 0.12), (0.02, 0.5, 0.12), "paint_red")
    h.deck(b, 0.03, 0.05, 0.95, mat="log_end" if kind == "dugout" else "wood_light")
    for t in (0.3, 0.72):
        h.thwart(b, t, drop=0.08, wide=0.2)
    bones.append(("paddle", (0.35, h.y(0.68), h.top(0.68) + 0.25), (0.35, h.y(0.68), h.top(0.68) + 0.55), "hull"))
    p = b.bone("paddle")
    p.cyl((0.25, h.y(0.66), h.top(0.6) + 0.75), (0.55, h.y(0.7), -0.25), 0.025, "wood", seg=5)
    p.beam((0.5, h.y(0.695), -0.02), (0.57, h.y(0.705), -0.42), 0.16, 0.03, "wood_light")
    sack(b, 0.0, h.y(0.5), z=0.03, r=0.2)
    stroke = lambda t: ({"paddle": [(kit.X, 22 * math.sin(2 * math.pi * t)),
                                    (kit.Y, 6 * (1 - math.cos(2 * math.pi * t)))]}, {})
    finish(root, name, bones, [("bob", 3.0, floating(4.5, 1.5, 0.03), None),
                               ("row", 1.6, merge(floating(2.5, 1.0, 0.02), stroke), 1.8)])


def longship(name, sail_mats=("cloth_red", "canvas"), shields=("paint_red", "paint_yellow", "paint_blue"),
             furled=False, beached=False):
    # Beached: run up on the shore and heeled over, oars shipped, with a gangplank. Z = 0 is the ground.
    root = B().at(dz=0.62).turn("Y", 13) if beached else B()
    b = root if beached else root.bone("hull")
    bones = []
    h = Hull(16.0, 3.4, 0.6, 0.8, tm=0.5, bow_p=0.65, stern_p=0.65, sheer_bow=1.3, sheer_stern=1.1,
             bow_rise=0.85, stern_rise=0.85, n=16, flat=0.55, thick=0.08)
    h.build(b, strakes=("wood_dark", "wood", "wood_dark"), inner="wood", posts=False)
    h.deck(b, 0.05, 0.1, 0.9, mat="plank", alt="plank_b", steps=20)
    # Curled stem with a dragon head, and a curled tail.
    for end, s in ((0.0, -1), (1.0, 1)):
        y0, z0 = h.y(end), h.top(end)
        pts = [(0, y0 - s * 0.1, h.bot(end) - 0.05), (0, y0 + s * 0.02, z0), (0, y0 + s * 0.25, z0 + 0.7),
               (0, y0 + s * 0.3, z0 + 1.3), (0, y0 + s * 0.12, z0 + 1.8)]
        for p, q in zip(pts, pts[1:]):
            b.beam(p, q, 0.16, 0.22, "timber")
        if s < 0:
            hy, hz = y0 - 0.3, z0 + 2.0
            b.box((0, hy, hz), (0.28, 0.75, 0.3), "timber")
            b.box((0, hy - 0.32, hz - 0.2), (0.22, 0.4, 0.08), "timber")
            b.box((0, hy - 0.3, hz - 0.1), (0.16, 0.3, 0.06), "paint_red")
            for e in (-1, 1):
                b.box((e * 0.145, hy - 0.1, hz + 0.05), (0.02, 0.1, 0.08), "gold")
                b.cyl((e * 0.1, hy + 0.25, hz + 0.1), (e * 0.22, hy + 0.55, hz + 0.45), 0.05, "wood_light", r2=0.01,
                      seg=5)
            for k in range(3):
                b.box((0, y0 + 0.02 - k * 0.0, z0 + 0.5 + k * 0.4), (0.06, 0.34, 0.14), "gold")
        else:
            b.beam(pts[-1], (0, y0 - 0.25, z0 + 2.05), 0.14, 0.18, "timber")
            b.beam((0, y0 - 0.25, z0 + 2.05), (0, y0 - 0.45, z0 + 1.8), 0.12, 0.14, "timber")
    # Thwarts, oars and shields.
    oars = []
    count = 8
    for i in range(count):
        t = 0.22 + i * 0.56 / (count - 1)
        h.thwart(b, t, drop=0.3, wide=0.24)
        for s in (-1, 1):
            bone = "oar_%s%d" % ("l" if s < 0 else "r", i)
            if not beached:
                oar(b, bones, bone, (s * h.w(t), h.y(t), h.top(t) - 0.12), s, out=2.6, inboard=0.7, drop=0.75)
                oars.append((bone, s))
            ts = t + 0.035
            b.cyl((s * (h.w(ts) + 0.05), h.y(ts), h.top(ts) - 0.05), (s * (h.w(ts) + 0.11), h.y(ts), h.top(ts) - 0.05),
                  0.34, shields[i % len(shields)], seg=9)
            b.cyl((s * (h.w(ts) + 0.1), h.y(ts), h.top(ts) - 0.05), (s * (h.w(ts) + 0.17), h.y(ts), h.top(ts) - 0.05),
                  0.09, "iron", seg=6)
    ym = h.y(0.48)
    mast(b, ym, 0.0, 8.0, r=0.14, yard=7.0, yard_z=7.2)
    if furled or beached:
        furled_sail(b, 6.4, ym - 0.21, 7.05, sail_mats[0])
    else:
        sail(b, bones, "sail", 6.6, ym - 0.2, 7.1, 2.3, sail_mats, bulge=1.0, strips=10)
    rope(b, [(0, ym, 7.9), (0, h.y(0) + 0.3, h.top(0) + 1.3)], r=0.022)
    rope(b, [(0, ym, 7.9), (0, h.y(1) - 0.3, h.top(1) + 1.3)], r=0.022)
    for s in (-1, 1):
        rope(b, [(0, ym, 7.6), (s * h.w(0.55), h.y(0.55), h.top(0.55))], r=0.022)
        rope(b, [(s * 3.3, ym - 0.2, 2.35), (s * h.w(0.75), h.y(0.75), h.top(0.75))], r=0.018)
    pennant(b, bones, ym, 8.1, mat=sail_mats[0], size=1.2)
    # Steering oar on the starboard quarter.
    b.cyl((h.w(0.9) + 0.1, h.y(0.9), h.top(0.9) + 0.4), (h.w(0.9) + 0.15, h.y(0.92), -0.9), 0.04, "wood", seg=6)
    b.beam((h.w(0.9) + 0.14, h.y(0.915), 0.1), (h.w(0.9) + 0.16, h.y(0.925), -1.0), 0.3, 0.04, "wood_light")
    b.beam((h.w(0.9) + 0.1, h.y(0.9), h.top(0.9) + 0.35), (0.6, h.y(0.9), h.top(0.9) + 0.4), 0.05, 0.05, "wood")
    if beached:
        flat = B(root.mb)   # The gangplank and the anchor lie on the ground, not heeled with the hull.
        yg = h.y(0.3)
        flat.beam((3.7, yg, 0.03), (1.9, yg, 1.02), 0.6, 0.07, "plank_b")
        for k in range(4):
            flat.box((3.4 - k * 0.42, yg, 0.2 + k * 0.235), (0.06, 0.6, 0.04), "timber")
        rope(flat, sag((0.3, h.y(0.02), 1.6), (2.2, h.y(0.0) - 3.0, 0.3), 0.5, 6), r=0.03)
        flat.box((2.2, h.y(0.0) - 3.0, 0.2), (0.1, 0.1, 0.7), "iron")
        flat.box((2.2, h.y(0.0) - 3.0, 0.05), (0.7, 0.1, 0.1), "iron")
        save(root, name)
        return
    finish(root, name, bones, [("bob", 4.0, merge(floating(2.0, 1.0, 0.04), waving(3, 12)), None),
                               ("sail", 4.0, merge(floating(3.0, 1.2, 0.06), flutter("sail", amp=2.2), waving()),
                                3.0),
                               ("row", 2.4, merge(floating(1.2, 0.8, 0.03), rowing(oars, sweep=20, lift=6),
                                                  waving(2, 10)), 2.2)])


model("boat_rowboat", rowboat)
model("boat_rowboat_painted", rowboat, strakes=("paint_blue", "canvas", "wood"), rail="wood_dark")
model("boat_fishing", fishing_boat)
model("boat_fishing_red", fishing_boat, sail_mats=("cloth_red", "roof_dark"), strakes=("paint_green", "wood", "wood"))
model("boat_raft_ferry", raft_ferry)
model("boat_merchant", merchant)
model("boat_merchant_blue", merchant, sail_mats=("cloth_blue", "canvas"), trim="paint_blue", flag="gold")
model("boat_merchant_white", merchant, sail_mats=("canvas", "canvas_shade"), trim="wood_light", flag="cloth_blue")
model("boat_barge", barge)
model("boat_barge_logs", barge, cargo="logs")
model("boat_barge_stone", barge, cargo="stone")
model("boat_barge_empty", barge, cargo="none")
model("boat_raft_ferry_empty", raft_ferry, cargo=False)
model("boat_raft_ferry_cart", raft_ferry, cart=True)
model("boat_canoe", canoe)
model("boat_canoe_bark", canoe, kind="bark")
model("boat_longship", longship)
model("boat_longship_blue", longship, sail_mats=("cloth_blue", "canvas"),
      shields=("paint_blue", "canvas", "paint_green"))
model("boat_longship_furled", longship, furled=True)
model("boat_longship_beached", longship, beached=True)
model("boat_rowboat_beached", rowboat, beached=True)
model("boat_fishing_furled", fishing_boat, furled=True)
