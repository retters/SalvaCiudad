"""Siege engines that go against the walls (for raiders, or for the
player's soldiers against raider camps): battering ram, siege tower and
scaling ladder. They give the wall pieces something to defend against."""

import math

import _kit as kit
from registry import reg
from wallkit import ladder


def wheel(p, x, y, r, w=None, axis=1):
    """A plank wheel on the X axis (thickness toward +X * axis)."""
    p.cyl((x, y, r), (x + axis * 0.14, y, r), r, r, "wood", w, seg=10)
    p.cyl((x + axis * 0.14, y, r), (x + axis * 0.18, y, r), r * 0.28, r * 0.28, "iron", w, seg=6)
    p.box((x + axis * 0.07, y, r), (0.16, r * 1.9, 0.08), "timber", w)
    p.box((x + axis * 0.07, y, r), (0.16, 0.08, r * 1.9), "timber", w)


def ram(p):
    """A covered battering ram 2 x 4.5 m: a log with an iron head slung on
    ropes under a roof of planks and hides, on four wheels. Front at -Y."""
    for s in (-1, 1):
        p.box((s * 0.85, 0, 0.62), (0.18, 4.2, 0.2), "timber")
        for y in (-1.4, 1.4):
            wheel(p, s * 0.95, y, 0.42, axis=s)
            p.box((s * 0.85, y, 1.5), (0.16, 0.16, 1.7), "timber")
        p.box((s * 0.85, 0, 2.3), (0.16, 3.2, 0.16), "timber")
        p.beam((s * 0.85, -1.4, 0.75), (s * 0.85, -0.5, 2.25), 0.1, "timber")
        p.beam((s * 0.85, 1.4, 0.75), (s * 0.85, 0.5, 2.25), 0.1, "timber")
    for y in (-1.4, 1.4):
        p.cyl((-0.9, y, 0.42), (0.9, y, 0.42), 0.06, 0.06, "iron_dark", seg=5)
        p.box((0, y, 2.3), (1.86, 0.16, 0.16), "timber")
        p.box((0, y, 0.62), (1.86, 0.16, 0.18), "timber")
    # The roof: two slopes of planks under hides.
    for s in (-1, 1):
        pts = [(s * 1.25, 2.2), (0.0, 3.05), (0.0, 3.13), (s * 1.25, 2.28)]
        p.yprism(pts if s > 0 else pts[::-1], -1.9, 1.9, "wood")
        for k, y in enumerate((-1.25, 0.0, 1.25)):
            hp = [(s * 1.28, 2.24), (s * 0.1, 3.08), (s * 0.1, 3.13), (s * 1.28, 2.29)]
            p.yprism(hp if s > 0 else hp[::-1], y - 0.55, y + 0.55, "hide" if (k + (s > 0)) % 2 else "leather")
    p.box((0, 0, 3.12), (0.16, 3.9, 0.12), "timber")
    # The ram itself, on its ropes.
    w = {"ram": 1.0}
    p.cyl((0, 1.9, 1.25), (0, -2.1, 1.25), 0.2, 0.2, "log", w, seg=8)
    p.cyl((0, 1.9, 1.25), (0, 1.93, 1.25), 0.17, 0.17, "log_end", w, seg=8)
    p.cyl((0, -2.1, 1.25), (0, -2.55, 1.25), 0.27, 0.2, "iron", w, seg=8)
    p.cyl((0, -2.55, 1.25), (0, -2.75, 1.25), 0.2, 0.08, "iron_dark", w, seg=8)
    for y in (-1.3, 0.2, 1.4):
        p.cyl((0, y - 0.06, 1.25), (0, y + 0.06, 1.25), 0.23, 0.23, "iron", w, seg=8)
    for y in (-1.0, 1.0):
        p.beam((0, y, 1.45), (0, y, 2.26), 0.045, "rope")
    if p.static:
        return None
    mech = kit.Mech([("ram", (0, 0, 2.26), (0, 0, 1.25), None)])

    def swing(t):
        # Pulled back slowly, then driven forward into the gate.
        k = -math.sin(math.pi * t / 0.6) * 0.6 if t < 0.6 else math.sin(math.pi * (t - 0.6) / 0.4) * 0.75
        return {}, {"ram": (0.0, -k, 0.12 * abs(k))}

    mech.clip("ram", 1.8, swing)
    return mech


def siege_tower(p):
    """A siege tower 3 x 3 m and 7 m tall on four wheels: three floors,
    a front covered in hides and a boarding ramp that drops (`drop`).
    Front at -Y."""
    H = 6.2
    for sx in (-1, 1):
        for sy in (-1, 1):
            p.beam((sx * 1.4, sy * 1.4, 0.5), (sx * 1.15, sy * 1.15, H + 1.2), 0.2, "timber")
        for y in (-1.0, 1.0):
            wheel(p, sx * 1.5, y, 0.5, axis=sx)
        p.box((sx * 1.4, 0, 0.6), (0.22, 3.1, 0.24), "timber")
    for y in (-1.0, 1.0):
        p.cyl((-1.5, y, 0.5), (1.5, y, 0.5), 0.07, 0.07, "iron_dark", seg=5)
    for sy in (-1, 1):
        p.box((0, sy * 1.4, 0.6), (3.0, 0.22, 0.24), "timber")
    for z in (0.75, 2.6, 4.4, H):   # Floors.
        k = 1.4 - 0.25 * (z - 0.5) / (H + 0.7)
        for i in range(6):
            p.box((-k + (i + 0.5) * 2 * k / 6, 0, z), (2 * k / 6 - 0.02, 2 * k, 0.08),
                  "wood_light" if i % 2 else "wood")
    # Cladding: hides on the front, planks on the sides, open at the back.
    for i in range(10):
        z0 = 0.8 + i * 0.52
        k = 1.4 - 0.25 * (z0 + 0.26 - 0.5) / (H + 0.7)
        p.box((0, -k - 0.06, z0 + 0.26), (2 * k + 0.1, 0.07, 0.5), "hide" if i % 2 else "leather")
        for sx in (-1, 1):
            p.box((sx * (k + 0.06), 0, z0 + 0.26), (0.07, 2 * k - 0.1, 0.5), "wood" if i % 2 else "wood_light")
    kt = 1.15
    for sx in (-1, 1):
        p.box((sx * kt, 0, H + 0.6), (0.08, 2 * kt, 0.9), "wood")
        p.box((sx * kt, 0, H + 1.12), (0.1, 2 * kt + 0.1, 0.1), "timber")
    p.box((0, kt, H + 1.12), (2 * kt, 0.1, 0.1), "timber")
    for z0, z1, y0 in ((0.75, 2.6, 0.6), (2.6, 4.4, -0.2), (4.4, H, 0.6)):
        ladder(p, (0.5, y0 + 0.5, z0), (0.5, y0, z1 + 0.3), width=0.4)
    for sx in (-1, 1):   # Shafts to push it.
        p.box((sx * 1.0, 2.1, 0.75), (0.12, 1.6, 0.12), "timber")
    p.box((0, 2.8, 0.75), (2.2, 0.12, 0.12), "timber")
    # The boarding ramp: raised in the rest pose, it drops forward.
    w = {"ramp": 1.0}
    for i in range(5):
        p.box((-0.9 + (i + 0.5) * 0.36, -kt - 0.1, H + 1.05), (0.34, 0.08, 2.0), "wood" if i % 2 else "wood_light", w)
    for z in (H + 0.3, H + 1.1, H + 1.9):
        p.box((0, -kt - 0.16, z), (1.86, 0.06, 0.1), "iron", w)
    for sx in (-1, 1):
        p.cyl((sx * 0.8, -kt - 0.2, H + 2.0), (sx * 0.8, -kt - 0.42, H + 2.12), 0.05, 0.0, "iron_dark", w, seg=4)
        p.beam((sx * 0.95, -kt - 0.1, H + 1.9), (sx * 1.1, kt * 0.2, H + 1.15), 0.03, "rope")
    p.cyl((0, 0.3, H + 1.2), (0, 0.3, H + 3.0), 0.04, 0.03, "timber", seg=5)
    p.yprism([(0.03, H + 2.4), (0.9, H + 2.62), (0.03, H + 2.95)], 0.285, 0.315, "blood")
    if p.static:
        return None
    mech = kit.Mech([("ramp", (0, -kt - 0.1, H + 0.05), (0, -kt - 0.1, H + 1.05), None)])

    def drop(t):
        k = kit.smooth(min(1.0, t / 0.25)) if t < 0.75 else 1.0 - kit.smooth((t - 0.75) / 0.25)
        bounce = 6.0 * math.sin(math.pi * min(1.0, max(0.0, (t - 0.25) / 0.12))) if t < 0.37 else 0.0
        return {"ramp": [(kit.X, 96.0 * k - bounce)]}

    mech.clip("drop", 4.0, drop)
    return mech


def scaling_ladder(p, height=4.0):
    """A scaling ladder with iron hooks, built leaning: its foot at
    y = -1.6 and its top at y = 0, above a wall walk `height` m up. `raise`
    swings it from flat on the ground, over the vertical, onto the wall."""
    top = height + 1.1
    reach = 1.6
    w = {"ladder": 1.0}
    for sx in (-1, 1):
        p.beam((sx * 0.3, -reach, 0.0), (sx * 0.3, 0.0, top), 0.08, "timber", w)
        p.cyl((sx * 0.3, 0.0, top), (sx * 0.3, 0.3, top + 0.1), 0.035, 0.03, "iron", w, seg=5)
        p.cyl((sx * 0.3, 0.3, top + 0.1), (sx * 0.3, 0.38, top - 0.2), 0.03, 0.0, "iron_dark", w, seg=5)
        p.cyl((sx * 0.3, -reach, 0.0), (sx * 0.3, -reach - 0.03, -0.0), 0.05, 0.05, "iron_dark", w, seg=5)
    n = int(top / 0.33)
    for i in range(1, n):
        k = i / n
        p.beam((-0.3, -reach * (1 - k), top * k), (0.3, -reach * (1 - k), top * k), 0.05, "wood", w)
    if p.static:
        return None
    mech = kit.Mech([("ladder", (0, -reach, 0.0), (0, 0.0, top), None)])
    lean = math.degrees(math.atan2(top, reach))   # Angle of the ladder from the ground.

    def lift(t):
        k = kit.smooth(t)
        return {"ladder": [(kit.X, (176.0 - lean) * (1.0 - k))]}

    mech.clip("raise", 2.0, lift, loops=False)
    return mech


reg("defense_siege_ram", "defense_siege_ram", "Ariete cubierto", ram, material="troncos, hierro y cuero",
    anim={"ram": "El ariete toma impulso y golpea"})
reg("defense_siege_tower", "defense_siege_tower", "Torre de asedio", siege_tower, material="troncos y cuero",
    anim={"drop": "La pasarela cae sobre el muro y vuelve a subir"})
for h, nombre in ((3.0, "Para muro de 3 m"), (4.0, "Para muralla de 4 m"), (5.0, "Para muralla de 5 m")):
    reg("defense_siege_ladder", "defense_siege_ladder_%d" % h, nombre, (lambda p, h=h: scaling_ladder(p, h)),
        material="troncos y hierro", anim={"raise": "La escala se levanta del suelo hasta apoyarse en el muro"})
