"""More of the family, built on the same pieces: wooden gatehouses, war
machines (ballista, catapult), beacons, a pit trap and three more fences."""

import math

import _kit as kit
import fences
import gates
import towers
from registry import reg
from wallkit import (SIDE_ROT, add_flicker, brazier, flame_bones, flame_mech, ladder, pyramid_roof, rng)
from walltypes import WALLS, Hedge, Masonry, WallType


# --- Wooden gatehouse ------------------------------------------------------------------------


def wood_gatehouse(p, log="log", tip="log_end", roof=("thatch", "thatch_dark"), skulls=False):
    """A gate 4 m wide under a timber guard room: 4 x 4 m, four log posts,
    a plank room with a parapet at 3.7 m and a hipped roof."""
    for sx in (-1, 1):
        for sy in (-1, 1):
            p.cyl((sx * 1.72, sy * 1.5, 0), (sx * 1.72, sy * 1.5, 6.3), 0.27, 0.22, log, seg=8)
            p.cyl((sx * 1.72, sy * 1.5, 0), (sx * 1.72, sy * 1.5, 0.3), 0.36, 0.3, "stone_dark", seg=8)
            for z in (1.0, 3.0):
                p.cyl((sx * 1.72, sy * 1.5, z - 0.07), (sx * 1.72, sy * 1.5, z + 0.07), 0.29, 0.28, "iron", seg=8)
        for i in range(12):   # Plank sides of the passage.
            p.box((sx * 1.72, 0, 0.2 + (i + 0.5) * 0.28), (0.09 if i % 2 else 0.12, 2.6, 0.27),
                  "wood" if i % 2 else "wood_light")
        for sy in (-1, 1):
            p.beam((sx * 1.5, sy * 1.5, 2.7), (sx * 0.8, sy * 1.5, 3.4), 0.14, "timber")
    for sy in (-1, 1):
        p.cyl((-2.1, sy * 1.5, 3.45), (2.1, sy * 1.5, 3.45), 0.17, 0.17, log, seg=7)
        for sx in (-1, 1):
            p.cyl((sx * 2.1, sy * 1.5, 3.45), (sx * 2.12, sy * 1.5, 3.45), 0.14, 0.14, tip, seg=7)
    for y in (-1.5, -0.5, 0.5, 1.5):
        p.box((0, y, 3.66), (4.5, 0.14, 0.14), "timber")
    for i in range(12):
        p.box((-2.2 + (i + 0.5) * 4.4 / 12, 0, 3.77), (4.4 / 12 - 0.02, 3.9, 0.08), "wood_light" if i % 2 else "wood")
    for d, length, hd in (("S", 4.4, 1.95), ("N", 4.4, 1.95), ("E", 3.9, 2.2), ("W", 3.9, 2.2)):
        q = p.at(rot=SIDE_ROT[d])
        q.box((0, -hd + 0.04, 4.0), (length, 0.08, 0.34), "wood")
        q.box((0, -hd + 0.04, 4.34), (length, 0.07, 0.32), "wood_light")
        n = int(length)
        for k in range(n):
            q.box((-length / 2 + (k + 0.5) * length / n, -hd + 0.04, 4.72), (0.5, 0.08, 0.44), "wood")
    pyramid_roof(p, (0, 0), 3.7, 3.3, 6.3, 1.6, roof, over=0.5)
    for s in (-1, 1):
        p.box((0, s * 1.5, 6.24), (3.7, 0.16, 0.16), "timber")
        p.box((s * 1.72, 0, 6.24), (0.16, 3.2, 0.16), "timber")
    ladder(p, (1.2, 2.6, 0.0), (1.2, 2.0, 4.1))
    if skulls:
        for x in (-1.0, 0.0, 1.0):
            p.sphere((x, -1.72, 3.5), 0.16, "bone", seg=7, rings=5)
            p.box((x, -1.74, 3.38), (0.16, 0.14, 0.1), "bone")
            for s in (-1, 1):
                p.box((x + s * 0.06, -1.87, 3.52), (0.05, 0.04, 0.06), "dark")
        p.box((0, -1.68, 3.05), (2.6, 0.05, 0.3), "blood")
    hinges = gates.leaves(p, 1.42, 3.2, "plank", y=-1.5)
    pts = [brazier(p, s * 2.15, -1.9, 0.0, 2.0, bone) for s, bone in ((-1, "flame"), (1, "flame2"))]
    if p.static:
        return None
    names, bones = flame_bones(pts)
    return add_flicker(gates.door_mech(hinges, extra=bones), names)


# --- War machines ----------------------------------------------------------------------------


def field_ballista(p):
    """A ballista on a wheeled carriage, for the ground or a bastion."""
    for s in (-1, 1):
        p.box((s * 0.55, 0.1, 0.42), (0.14, 2.2, 0.16), "timber")
        for y in (-0.6, 0.8):
            p.cyl((s * 0.68, y, 0.3), (s * 0.8, y, 0.3), 0.3, 0.3, "wood", seg=10)
            p.cyl((s * 0.8, y, 0.3), (s * 0.83, y, 0.3), 0.08, 0.08, "iron", seg=6)
    for y in (-0.6, 0.8):
        p.cyl((-0.7, y, 0.3), (0.7, y, 0.3), 0.05, 0.05, "iron_dark", seg=5)
        p.box((0, y, 0.45), (1.2, 0.14, 0.12), "timber")
    p.box((0, 0.1, 0.52), (1.0, 1.2, 0.06), "wood_light")
    bones = towers.ballista(p, 0.55)
    if p.static:
        return None
    return towers.ballista_clips(kit.Mech(bones))


def catapult(p):
    """A torsion catapult (onager) on four wheels. The arm rests loaded,
    toward +Y; `fire` throws the stone toward -Y, `reload` winds it back."""
    for s in (-1, 1):
        p.box((s * 0.7, 0, 0.55), (0.2, 3.2, 0.24), "timber")
        for y in (-1.15, 1.15):
            p.cyl((s * 0.82, y, 0.38), (s * 0.98, y, 0.38), 0.38, 0.38, "wood", seg=10)
            p.cyl((s * 0.98, y, 0.38), (s * 1.02, y, 0.38), 0.1, 0.1, "iron", seg=6)
        p.box((s * 0.7, -0.5, 1.45), (0.18, 0.2, 1.7), "timber")          # Uprights.
        p.beam((s * 0.7, -1.4, 0.65), (s * 0.7, -0.55, 2.1), 0.14, "timber")
        p.beam((s * 0.7, 0.5, 0.65), (s * 0.7, -0.45, 1.9), 0.12, "timber")
    for y in (-1.5, 1.5):
        p.box((0, y, 0.55), (1.6, 0.2, 0.22), "timber")
    for y in (-1.15, 1.15):
        p.cyl((-0.85, y, 0.38), (0.85, y, 0.38), 0.06, 0.06, "iron_dark", seg=5)
    p.box((0, -0.5, 2.25), (1.7, 0.26, 0.26), "timber")                   # The stop beam, padded.
    p.box((0, -0.36, 2.25), (0.9, 0.12, 0.34), "hide")
    p.cyl((-0.62, 0.0, 0.72), (0.62, 0.0, 0.72), 0.2, 0.2, "rope", seg=8)  # The torsion skein.
    for s in (-1, 1):
        p.cyl((s * 0.62, 0.0, 0.72), (s * 0.84, 0.0, 0.72), 0.26, 0.26, "iron", seg=8)
    p.cyl((-0.8, 1.35, 0.8), (0.8, 1.35, 0.8), 0.09, 0.09, "wood", seg=7)  # The windlass.
    for s in (-1, 1):
        p.beam((s * 0.8, 1.35, 0.8), (s * 0.8, 1.6, 1.15), 0.05, "iron_dark")
    w = {"arm": 1.0}
    pivot = (0.0, 0.0, 0.72)
    p.beam(pivot, (0.0, 2.1, 1.05), 0.16, "wood", w)
    p.cyl((0, 2.1, 0.98), (0, 2.1, 1.14), 0.3, 0.34, "iron_dark", w, seg=8)          # The cup.
    p.cyl((0, 2.1, 1.12), (0, 2.1, 1.15), 0.28, 0.28, "wood_light", w, seg=8)
    p.sphere((0, 2.1, 1.3), 0.22, "stone", {"stone": 1.0}, seg=7, rings=5)
    for i, (x, y) in enumerate(((1.4, 1.0), (1.75, 1.15), (1.5, 1.4), (1.6, 1.18))):   # Spare stones.
        p.sphere((x, y, 0.2 + (0.34 if i == 3 else 0.0)), 0.21, "stone" if i % 2 else "stone_dark", seg=7, rings=5)
    if p.static:
        return None
    mech = kit.Mech([("arm", pivot, (0.0, 1.0, 0.88), None), ("stone", (0, 2.1, 1.3), (0, 2.1, 1.6), None)])
    up = 95.0   # Degrees about X from the loaded pose to the stop beam.

    def arm_angle(t):
        return up * kit.smooth(min(1.0, t / 0.18))

    def stone_at(t):
        a = math.radians(arm_angle(min(t, 0.16)))
        ry, rz = 2.1, 1.3 - 0.72   # The stone, seen from the pivot.
        y = ry * math.cos(a) - rz * math.sin(a)
        z = 0.72 + ry * math.sin(a) + rz * math.cos(a)
        if t > 0.16:   # Released: it flies on.
            k = (t - 0.16) / 0.84
            y -= 9.0 * k
            z += 4.0 * k - 6.6 * k * k
        return (0.0, y - 2.1, max(z, 0.2) - 1.3)

    def reload(t):
        # A new stone waits on the ground by the pile and is lifted into the cup at the end.
        k = kit.smooth(max(0.0, (t - 0.8) / 0.2))
        wait = (1.1, -0.6, -1.08)
        stone = (wait[0] * (1 - k), wait[1] * (1 - k), wait[2] * (1 - k) + 0.5 * math.sin(math.pi * k))
        return {"arm": [(kit.X, up * (1.0 - kit.smooth(min(1.0, t / 0.8))))]}, {"stone": stone}

    mech.clip("fire", 1.6, lambda t: ({"arm": [(kit.X, arm_angle(t))]}, {"stone": stone_at(t)}), loops=False)
    mech.clip("reload", 3.0, reload, loops=False)
    return mech


def beacon(p, W):
    """A slender signal tower 3 x 3 m and 10 m tall with a great fire
    basket on top: lit, it calls the militia from far away."""
    H = 10.0
    p.taper((0, 0), (3.0, 3.0), (2.5, 2.5), 0.0, 1.2, W.dark)
    p.taper((0, 0), (2.5, 2.5), (2.0, 2.0), 1.2, H, W.mat)
    z = 1.8
    while z < H - 0.4:
        s = 2.5 - 0.5 * (z - 1.2) / (H - 1.2)
        p.box((0, 0, z), (s + 0.03, s + 0.03, 0.05), W.dark)
        z += 0.9
    p.box((0, 0, H - 0.1), (2.6, 2.6, 0.24), W.dark)
    towers.ring_parapet(p, W, 1.2, H)
    for d in "SEW":
        q = p.at(rot=SIDE_ROT[d])
        for zz in (3.5, 6.6):
            q.box((0, -1.2 + 0.25 * (zz - 1.2) / (H - 1.2) - 0.02, zz), (0.4, 0.1, 1.2), W.trim)
            q.box((0, -1.2 + 0.25 * (zz - 1.2) / (H - 1.2) - 0.05, zz), (0.1, 0.08, 0.95), "dark")
    q = p.at(rot=180)
    q.box((0, -1.27, 1.0), (1.2, 0.14, 2.0), W.trim)
    q.box((0, -1.31, 0.95), (0.9, 0.1, 1.8), "door")
    # The fire basket: an iron cage on a stone hearth.
    p.box((0, 0, H + 0.25), (1.3, 1.3, 0.5), W.dark)
    for k in range(8):
        a = 2 * math.pi * k / 8
        p.beam((0.5 * math.cos(a), 0.5 * math.sin(a), H + 0.5), (0.72 * math.cos(a), 0.72 * math.sin(a), H + 1.4),
               0.05, "iron_dark")
    for zz, r in ((H + 0.95, 0.63), (H + 1.4, 0.74)):
        p.cyl((0, 0, zz - 0.03), (0, 0, zz + 0.03), r, r, "iron", seg=8)
    for k in range(5):
        a = 2 * math.pi * k / 5
        p.cyl((0.25 * math.cos(a), 0.25 * math.sin(a), H + 0.5), (-0.2 * math.cos(a), -0.2 * math.sin(a), H + 1.0),
              0.08, 0.07, "log", seg=5)
    p.cyl((0, 0, H + 0.5), (0, 0, H + 0.75), 0.5, 0.45, "ember", seg=8)
    pts = []
    for i, (x, y, s) in enumerate(((0.0, 0.0, 1.0), (0.25, 0.12, 0.6), (-0.22, -0.18, 0.7), (-0.05, 0.28, 0.5))):
        bone = "flame" if i == 0 else "flame%d" % (i + 1)
        w = {bone: 1.0}
        p.cyl((x, y, H + 0.7), (x, y, H + 0.7 + 1.5 * s), 0.34 * s, 0.0, "torch_flame", w, seg=6)
        p.cyl((x + 0.05, y, H + 0.7), (x + 0.08, y, H + 0.7 + 0.9 * s), 0.17 * s, 0.0, "flame_core", w, seg=5)
        pts.append((x, y, H + 0.7))
    if p.static:
        return None
    return flame_mech(pts)


def beacon_wood(p):
    """A signal fire on a tall timber tripod, with a ladder."""
    H = 6.0
    feet = [(1.3 * math.cos(a), 1.3 * math.sin(a)) for a in (math.pi / 2, math.pi * 7 / 6, math.pi * 11 / 6)]
    for x, y in feet:
        p.cyl((x, y, 0), (x * 0.25, y * 0.25, H), 0.13, 0.1, "log", seg=7)
    for z in (2.0, 4.0):
        k = 1 - 0.75 * z / H
        for i in range(3):
            a, b = feet[i], feet[(i + 1) % 3]
            p.beam((a[0] * k, a[1] * k, z), (b[0] * k, b[1] * k, z), 0.08, "timber")
    p.cyl((0, 0, H - 0.1), (0, 0, H + 0.05), 0.75, 0.75, "wood", seg=8)
    p.cyl((0, 0, H + 0.05), (0, 0, H + 0.2), 0.6, 0.6, "stone_dark", seg=8)
    ladder(p, (0.0, -1.6, 0.0), (0.0, -0.75, H))
    for k in range(5):
        a = 2 * math.pi * k / 5
        p.cyl((0.3 * math.cos(a), 0.3 * math.sin(a), H + 0.2), (-0.2 * math.cos(a), -0.2 * math.sin(a), H + 0.8),
              0.08, 0.07, "log", seg=5)
    p.cyl((0, 0, H + 0.2), (0, 0, H + 0.4), 0.45, 0.4, "ember", seg=8)
    pts = []
    for i, (x, y, s) in enumerate(((0.0, 0.0, 1.0), (0.22, 0.1, 0.6), (-0.2, -0.15, 0.7))):
        bone = "flame" if i == 0 else "flame%d" % (i + 1)
        w = {bone: 1.0}
        p.cyl((x, y, H + 0.4), (x, y, H + 0.4 + 1.3 * s), 0.3 * s, 0.0, "torch_flame", w, seg=6)
        p.cyl((x + 0.05, y, H + 0.4), (x + 0.07, y, H + 0.4 + 0.8 * s), 0.15 * s, 0.0, "flame_core", w, seg=5)
        pts.append((x, y, H + 0.4))
    if p.static:
        return None
    return flame_mech(pts)


def pit_trap(p):
    """A covered pit 2 x 2 m with stakes, shown as a block of ground 1.2 m
    deep: the lid of branches drops on its hinge (`spring`)."""
    G = 1.2
    q = p.at(z=G)
    for d in range(4):   # The four walls of the pit.
        s = q.at(rot=d * 90)
        s.box((0, -0.9, -G / 2), (2.0, 0.2, G), "soil")
    q.box((0, 0, -G + 0.05), (1.6, 1.6, 0.1), "mud")
    q.box((0, -0.9, 0.0), (2.0, 0.2, 0.04), "grass")
    q.box((0, 0.9, 0.0), (2.0, 0.2, 0.04), "grass")
    r = rng("pit")
    for i in range(4):
        for j in range(4):
            x, y = -0.6 + i * 0.4 + r.uniform(-0.05, 0.05), -0.6 + j * 0.4 + r.uniform(-0.05, 0.05)
            q.cyl((x, y, -G + 0.1), (x, y, -G + 0.75), 0.05, 0.04, "log", seg=5)
            q.cyl((x, y, -G + 0.75), (x, y, -G + 0.95), 0.04, 0.0, "log_end", seg=5)
    w = {"lid": 1.0}
    for i in range(6):   # The lid: branches under a layer of straw and leaves.
        q.cyl((-0.8, -0.7 + i * 0.28, 0.02), (0.8, -0.7 + i * 0.28 + r.uniform(-0.05, 0.05), 0.02), 0.03, 0.025,
              "timber", w, seg=5)
    for i in range(7):
        q.box((r.uniform(-0.45, 0.45), r.uniform(-0.5, 0.5), 0.06), (r.uniform(0.5, 0.8), 0.3, 0.03),
              r.choice(("hay", "leaves", "grass", "thatch_dark")), w, rz=r.uniform(0, 180))
    if p.static:
        return None
    mech = kit.Mech([("lid", (-0.8, 0.0, G), (0.2, 0.0, G), None)])

    def spring(t):
        k = kit.smooth(min(1.0, t / 0.25)) if t < 0.7 else 1.0 - kit.smooth((t - 0.7) / 0.3)
        return {"lid": [(kit.Y, 82.0 * k)]}

    mech.clip("spring", 3.0, spring)
    return mech


# --- More fences -----------------------------------------------------------------------------


class BrickFence(Masonry):
    leaf = "ironbars"
    post = 0.34   # Half the width of its pilaster, for the gate.

    def __init__(self):
        Masonry.__init__(self, "lowbrick", "brick", "brick_dark", "stone_light", "brick_light", 0.9, 0.36,
                         parapet=False, course=0.3)


class RopeFence(WallType):
    key, h, top, t, half = "rope", 0.95, 1.1, 0.12, 0.07
    leaf = "bars"

    def run(self, p, x0, x1, base=0.0, **_):
        n = 4
        for z in (0.45, 0.85):
            for i in range(n):   # A sagging rope, in short straight stretches.
                a = x0 + (x1 - x0) * i / n
                b = x0 + (x1 - x0) * (i + 1) / n
                sag = lambda x: 0.1 * math.sin(math.pi * max(0.0, min(1.0, (abs(x) - self.half) / (1.0 - self.half))))
                p.beam((a, 0, base + z - sag(a)), (b, 0, base + z - sag(b)), 0.035, "rope")

    def node(self, p, arms, base=0.0):
        p.cyl((0, 0, base), (0, 0, base + 1.05), 0.07, 0.06, "timber", seg=6)
        p.cyl((0, 0, base + 1.05), (0, 0, base + 1.12), 0.08, 0.05, "wood_light", seg=6)
        for z in (0.45, 0.85):
            p.cyl((0, 0, base + z - 0.04), (0, 0, base + z + 0.04), 0.085, 0.085, "rope", seg=6)


class BoxHedge(Hedge):
    key, h, top, t, half = "boxhedge", 0.9, 1.0, 0.6, 0.3
    leaf = "picket"
    lift = 0.02

    def node(self, p, arms, base=0.0):
        p.box((0, 0, base + 0.5), (0.62, 0.62, 0.9), "leaves_dark")
        p.sphere((0, 0, base + 1.1), 0.36, "leaves", seg=7, rings=5)
        p.sphere((0, 0, base + 1.5), 0.2, "leaves_light", seg=6, rings=4)


MORE_FENCES = {"brick": BrickFence(), "rope": RopeFence(), "boxhedge": BoxHedge()}
MORE_NAMES = {"brick": "ladrillo y piedra", "rope": "troncos y lino", "boxhedge": "seto vivo"}

for key, F in MORE_FENCES.items():
    group = "fence_" + key
    mat = MORE_NAMES[key]
    reg(group, "fence_%s_demo_pen" % key, "Corral de demostración (8 × 6 m)",
        (lambda p, F=F: fences.pen_demo(p, F)), material=mat,
        nota="Montado con las piezas del grupo: rectos, cuatro esquinas y una cancela.")
    for kind, nombre, arms in (("straight", "Recto (2 m)", "EW"), ("corner", "Esquina", "EN"),
                               ("tee", "Unión en T", "EWN"), ("cross", "Cruce", "EWNS"), ("end", "Remate", "W")):
        reg(group, "fence_%s_%s" % (key, kind), nombre, (lambda p, F=F, arms=arms: fences.junction(p, F, arms)),
            material=mat)
    reg(group, "fence_%s_step" % key, "Escalón de 1 m (pendiente)", (lambda p, F=F: fences.fence_step(p, F)),
        material=mat)
    reg(group, "fence_%s_gate" % key, "Cancela", (lambda p, F=F: fences.fence_gate(p, F)), material=mat,
        anim=fences.GATE_ANIM)

# --- Registration ----------------------------------------------------------------------------

GH = {"open": "Las dos hojas se abren hacia dentro", "close": "Las dos hojas se cierran",
      "flicker": "Las llamas de los braseros se mueven"}
reg("gate_wood_gatehouse", "gate_palisade_gatehouse", "De troncos, con techo de paja", lambda p: wood_gatehouse(p),
    material="troncos y paja", anim=GH)
reg("gate_wood_gatehouse", "gate_plank_gatehouse", "De troncos, con tejado de tejas",
    lambda p: wood_gatehouse(p, roof=("roof", "roof_dark")), material="troncos y tejas", anim=GH)
reg("gate_wood_gatehouse", "gate_orc_gatehouse", "Orca, con calaveras",
    lambda p: wood_gatehouse(p, log="timber", tip="bone", roof=("hide", "timber"), skulls=True),
    material="troncos y cuero", anim=GH)

reg("defense_ballista", "defense_ballista", "Balista de campaña", field_ballista, material="troncos y hierro",
    anim={"aim": "La balista gira buscando blanco", "fire": "Dispara el virote y recarga"})
reg("defense_catapult", "defense_catapult", "Catapulta de torsión", catapult, material="troncos, hierro y cuero",
    anim={"fire": "El brazo salta y lanza la piedra", "reload": "El torno baja el brazo otra vez"})
for key, nombre, material in (("stone", "Sillería", "piedra"), ("brick", "Ladrillo", "ladrillo y piedra"),
                              ("darkelf", "De elfos oscuros", "piedra y hierro")):
    reg("tower_beacon", "tower_%s_beacon" % key, nombre, (lambda p, W=WALLS[key]: beacon(p, W)), material=material,
        anim={"flicker": "La hoguera de señales arde"})
reg("tower_beacon", "tower_wood_beacon", "Trípode de troncos", beacon_wood, material="troncos",
    anim={"flicker": "La hoguera de señales arde"})
reg("defense_pit", "defense_pit_trap", "Foso trampa con estacas", pit_trap, material="troncos",
    anim={"spring": "La tapa cede, queda abierta y vuelve a su sitio"},
    nota="El modelo incluye el bloque de terreno de 1,2 m de hondo: el nivel del suelo está en Z = 1,2 m.")
