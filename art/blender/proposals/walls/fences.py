"""Low fences on the same 2 m module and the same connection rule as the
walls: a post at the middle of each cell and arms toward the neighbors."""

from registry import reg
from wallkit import door_leaf, door_mech
from walltypes import Fieldstone, WallType, junction


class RailFence(WallType):
    key, h, top, t, half = "rail", 1.1, 1.25, 0.14, 0.07
    leaf = "bars"

    def run(self, p, x0, x1, base=0.0, **_):
        for i, z in enumerate((0.32, 0.64, 0.96)):
            p.cyl((x0, 0, base + z), (x1, 0, base + z), 0.05, 0.042, "wood" if i % 2 else "wood_light", seg=6)

    def node(self, p, arms, base=0.0):
        p.box((0, 0, base + 0.6), (0.15, 0.15, 1.2), "timber")
        p.taper((0, 0), (0.15, 0.15), (0.04, 0.04), base + 1.2, base + 1.3, "timber")


class PicketFence(WallType):
    key, h, top, t, half = "picket", 1.0, 1.2, 0.12, 0.07
    leaf = "picket"

    def run(self, p, x0, x1, base=0.0, **_):
        L, xc = x1 - x0, (x0 + x1) / 2
        for z in (0.28, 0.78):   # Rails through the pickets, so both faces look the same.
            p.box((xc, 0.0, base + z), (L, 0.08, 0.07), "wood_light")
        n = max(1, round(L / 0.155))
        for i in range(n):
            x = x0 + (i + 0.5) * L / n
            p.box((x, 0.0, base + 0.5), (0.1, 0.04, 0.9), "paint_white")
            p.taper((x, 0.0), (0.1, 0.04), (0.01, 0.04), base + 0.95, base + 1.06, "paint_white")

    def node(self, p, arms, base=0.0):
        p.box((0, 0, base + 0.58), (0.13, 0.13, 1.16), "paint_white")
        p.box((0, 0, base + 1.18), (0.18, 0.18, 0.05), "wood_light")
        p.taper((0, 0), (0.14, 0.14), (0.02, 0.02), base + 1.2, base + 1.32, "paint_white")


class WattleFence(WallType):
    key, h, top, t, half = "wattle", 1.05, 1.2, 0.14, 0.05
    leaf = "bars"

    def run(self, p, x0, x1, base=0.0, **_):
        L = x1 - x0
        n = max(1, round(L / 0.32))
        xs = [x0 + i * L / n for i in range(n + 1)]
        for x in xs[1:-1] if n > 1 else []:
            p.cyl((x, 0, base), (x, 0, base + 1.15), 0.035, 0.028, "timber", seg=5)
        for row in range(8):
            z = base + 0.1 + row * 0.115
            for i in range(n):
                s = 1 if (row + i) % 2 else -1
                p.box(((xs[i] + xs[i + 1]) / 2, s * 0.035, z), (xs[i + 1] - xs[i] + 0.05, 0.045, 0.1),
                      "wattle" if row % 2 else "wattle_dark")

    def node(self, p, arms, base=0.0):
        p.cyl((0, 0, base), (0, 0, base + 1.3), 0.06, 0.045, "timber", seg=6)


class StoneFence(WallType):
    key, h, top, t, half = "stone", 0.75, 0.95, 0.5, 0.3
    leaf = "bars"

    def __init__(self):
        self.fs = Fieldstone()
        self.fs.t = 0.5

    def run(self, p, x0, x1, base=0.0, **_):
        self.fs.run(p, x0, x1, base=base, h=0.75)

    def node(self, p, arms, base=0.0):
        p.box((0, 0, base + 0.48), (0.6, 0.6, 0.96), "stone_dark")
        p.box((0, 0, base + 0.3), (0.64, 0.64, 0.25), "stone")
        p.box((0, 0, base + 0.7), (0.64, 0.64, 0.22), "stone_light")
        p.box((0, 0, base + 1.0), (0.72, 0.72, 0.1), "stone_light")


class IronFence(WallType):
    key, h, top, t, half = "iron", 1.5, 1.7, 0.3, 0.22
    leaf = "ironbars"

    def run(self, p, x0, x1, base=0.0, **_):
        L, xc = x1 - x0, (x0 + x1) / 2
        p.box((xc, 0, base + 0.15), (L, 0.3, 0.3), "stone")
        p.box((xc, 0, base + 0.32), (L, 0.36, 0.06), "stone_light")
        for z in (0.5, 1.32):
            p.box((xc, 0, base + z), (L, 0.04, 0.05), "iron_dark")
        n = max(1, round(L / 0.15))
        for i in range(n):
            x = x0 + (i + 0.5) * L / n
            tall = 1.5 if i % 2 else 1.42
            p.cyl((x, 0, base + 0.34), (x, 0, base + tall), 0.018, 0.018, "iron", seg=5)
            p.cyl((x, 0, base + tall), (x, 0, base + tall + 0.14), 0.035, 0.0, "iron_dark", seg=4)

    def node(self, p, arms, base=0.0):
        p.box((0, 0, base + 0.8), (0.44, 0.44, 1.6), "stone")
        p.box((0, 0, base + 0.2), (0.5, 0.5, 0.4), "stone_dark")
        p.box((0, 0, base + 1.63), (0.54, 0.54, 0.1), "stone_light")
        p.sphere((0, 0, base + 1.82), 0.15, "stone_light", seg=8, rings=5)


FENCES = {"rail": RailFence(), "picket": PicketFence(), "wattle": WattleFence(), "stone": StoneFence(),
          "iron": IronFence()}


def fence_gate(p, F):
    """A 2 m piece: two posts and a leaf that swings inward."""
    for s in (-1, 1):
        F.node(p.at(x=s * 0.88), set())
    post = getattr(F, "post", F.half)
    hinge = -0.88 + post + 0.02
    door_leaf(p, hinge, 0.0, 2 * (0.88 - post) - 0.06, F.h, +1, "door", F.leaf, z0=0.08)
    if p.static:
        return None
    return door_mech([("door", (hinge, 0.0), +1)], angle=100.0, seconds=1.2)


def fence_step(p, F):
    """A 1 m rise for sloped ground."""
    F.node(p.at(x=-1.0), set())
    F.run(p, -1.0, 0.0)
    F.node(p, set())
    F.node(p, set(), base=1.0)
    F.run(p, 0.0, 1.0, base=1.0)


def pen_demo(p, F):
    """A paddock 8 x 6 m made of the fence's own pieces."""
    from wallkit import Pen
    q = Pen(p.mb, p.m, True)
    junction(q.at(x=-3, y=-2), F, "EN")
    junction(q.at(x=3, y=-2), F, "WN")
    junction(q.at(x=-3, y=2), F, "ES")
    junction(q.at(x=3, y=2), F, "WS")
    for x in (-1, 1):
        junction(q.at(x=x, y=2), F, "EW")
    junction(q.at(x=-1, y=-2), F, "EW")
    fence_gate(q.at(x=1, y=-2), F)
    for sx in (-1, 1):
        junction(q.at(x=sx * 3, y=0), F, "NS")
    # A trough and a heap of hay inside, to give the scale.
    q.box((1.4, 1.0, 0.25), (1.6, 0.5, 0.3), "wood")
    q.box((1.4, 1.0, 0.37), (1.4, 0.34, 0.08), "water")
    for x in (0.7, 2.1):
        q.box((x, 1.0, 0.12), (0.1, 0.56, 0.24), "timber")
    q.sphere((-1.6, 0.8, 0.35), 0.55, "hay", seg=8, rings=5, scale=(1.2, 1.0, 0.75))
    return None


NAMES = {"rail": ("Cerca de palos", "troncos"), "picket": ("Valla de estacas pintadas", "troncos"),
         "wattle": ("Cerca de zarzo", "leña"), "stone": ("Murete de piedra seca", "piedra"),
         "iron": ("Verja de hierro", "hierro y piedra")}
GATE_ANIM = {"open": "La cancela se abre hacia dentro", "close": "La cancela se cierra"}

for key, F in FENCES.items():
    group = "fence_" + key
    mat = NAMES[key][1]
    reg(group, "fence_%s_demo_pen" % key, "Corral de demostración (8 × 6 m)", (lambda p, F=F: pen_demo(p, F)),
        material=mat, nota="Montado con las piezas del grupo: rectos, cuatro esquinas y una cancela.")
    reg(group, "fence_%s_straight" % key, "Recto (2 m)", (lambda p, F=F: junction(p, F, "EW")), material=mat)
    reg(group, "fence_%s_corner" % key, "Esquina", (lambda p, F=F: junction(p, F, "EN")), material=mat)
    reg(group, "fence_%s_tee" % key, "Unión en T", (lambda p, F=F: junction(p, F, "EWN")), material=mat)
    reg(group, "fence_%s_cross" % key, "Cruce", (lambda p, F=F: junction(p, F, "EWNS")), material=mat)
    reg(group, "fence_%s_end" % key, "Remate", (lambda p, F=F: junction(p, F, "W")), material=mat)
    reg(group, "fence_%s_step" % key, "Escalón de 1 m (pendiente)", (lambda p, F=F: fence_step(p, F)), material=mat)
    reg(group, "fence_%s_gate" % key, "Cancela", (lambda p, F=F: fence_gate(p, F)), material=mat, anim=GATE_ANIM)
