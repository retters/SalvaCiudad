"""More pieces built on the wall types: a wall climbing a slope (demo of
the 1 m step), water gates, a turret piece and old ruined walls."""

import math

import _kit as kit
import gates
import towers
import wall_models
from registry import reg
from wallkit import Pen, brazier, cone_roof, flame_mech, pyramid_roof, rng, rubble
from walltypes import PIECES, WALLS, Masonry, stairs_length

# --- Twin-tower gate -------------------------------------------------------------------------


def twin_gate(p, W):
    """A gate 8 x 4 m between two slim round towers with conical roofs:
    a portcullis in front and two leaves behind it. `open` raises the
    portcullis and then swings the leaves in; `close` does the opposite."""
    q = Pen(p.mb, p.m, True)
    for s in (-1, 1):
        towers.tower_round(q.at(x=s * 2.7), W, roof=True, r=1.3, walk_sides="EW")
    over = max(W.h, 3.6)
    door_h = min(over - 0.8, 3.4)
    t = W.t
    W.run(p, -1.5, 1.5, base=over - W.h, floor=door_h + 0.25)
    p.box((0, 0, door_h + 0.2), (3.0, t + 0.16, 0.3), W.trim)
    for s in (-1, 1):
        p.box((s * 1.36, 0, door_h / 2), (0.14, t + 0.14, door_h), W.trim)
        for f in (-1, 1):
            p.box((s * 1.12, f * (t / 2 - 0.1), door_h - 0.15), (0.36, 0.3, 0.36), W.trim)
    p.box((0, -(t / 2 + 0.1), door_h + 0.26), (0.44, 0.1, 0.52), W.light)
    p.box((0, -(t / 2 + 0.14), over - 0.5), (0.8, 0.05, 0.8), "cloth_red")
    p.box((0, -(t / 2 + 0.18), over - 0.5), (0.36, 0.04, 0.36), "gold")
    w = {"portcullis": 1.0}
    yp = -(t / 2 - 0.25)
    for i in range(9):
        x = -1.2 + i * 0.3
        p.box((x, yp, door_h / 2 + 0.1), (0.07, 0.07, door_h), "iron", w)
        p.cyl((x, yp, 0.14), (x, yp, 0.0), 0.05, 0.0, "iron_dark", w, seg=4)
    z = 0.45
    while z < door_h:
        p.box((0, yp, z), (2.56, 0.09, 0.07), "iron_dark", w)
        z += 0.55
    hinges = gates.leaves(p, 1.28, door_h - 0.05, "iron" if W.spikes else "plank", y=0.25)
    pts = [brazier(p, s * 1.5, -(t / 2 + 0.75), 0.0, 1.9, bone) for s, bone in ((-1, "flame"), (1, "flame2"))]
    if p.static:
        return None
    bones = [(name, (x, y, 0.0), (x, y, 1.0), None) for name, (x, y), _ in hinges]
    mech = flame_mech(pts, extra=bones + [("portcullis", (0, yp, 0.0), (0, yp, 1.0), None)])
    rise = door_h - 0.3

    def opened(t_):
        up = kit.smooth(min(1.0, t_ / 0.55))
        swing = kit.smooth(max(0.0, (t_ - 0.45) / 0.55))
        return ({name: [(kit.Z, sign * 100.0 * swing)] for name, _, sign in hinges},
                {"portcullis": (0.0, 0.0, rise * up)})

    mech.clip("open", 3.5, opened, loops=False)
    mech.clip("close", 3.5, lambda t_: opened(1.0 - t_), loops=False)
    return mech


TWIN = {"open": "Sube el rastrillo y después se abren las hojas", "close": "Se cierran las hojas y baja el rastrillo",
        "flicker": "Las llamas de los braseros se mueven"}
for _key, _nombre, _mat in (("stone", "Sillería", "piedra"), ("brick", "Ladrillo", "ladrillo y piedra"),
                            ("iron", "Reforzada con hierro", "piedra y hierro"), ("sandstone", "Arenisca", "piedra"),
                            ("dwarf", "Enana", "piedra y oro"), ("elf", "Élfica", "piedra"),
                            ("darkelf", "De elfos oscuros", "piedra y hierro"),
                            ("foxfolk", "De la gente zorro", "piedra, troncos y tejas"),
                            ("catfolk", "De la gente gato", "arcilla y tejas")):
    reg("gate_twin", "gate_%s_twin" % _key, _nombre, (lambda p, W=WALLS[_key]: twin_gate(p, W)), material=_mat,
        anim=TWIN)

# --- A wall on a slope -----------------------------------------------------------------------


def slope_demo(p, key):
    """Nine cells climbing 3 m: flat stretches and 1 m steps in turn, on
    a wedge of ground, to show how the step piece follows the terrain."""
    W = WALLS[key]
    q = Pen(p.mb, p.m, True)
    cells = [(-8, "end", 0, 180), (-6, "straight", 0, 0), (-4, "step", 0, 0), (-2, "straight", 1, 0),
             (0, "step", 1, 0), (2, "torch", 2, 0), (4, "step", 2, 0), (6, "straight", 3, 0), (8, "end", 3, 0)]
    wide = 2.2
    for x, kind, b, rot in cells:
        PIECES[kind](q.at(x=x, rot=rot, z=b), W)
        if kind == "step":
            q.yprism([(x - 1, 0.0), (x + 1, 0.0), (x + 1, b + 1.0), (x - 1, b)], -wide, wide, "soil")
            q.yprism([(x - 1, b), (x + 1, b + 1.0), (x + 1, b + 1.05), (x - 1, b + 0.05)], -wide, wide, "grass")
        else:
            if b > 0:
                q.box((x, 0, b / 2), (2.0, 2 * wide, b), "soil")
            q.box((x, 0, b + 0.02), (2.0, 2 * wide, 0.05), "grass")
    return None


for _key, _txt in (("stone", "muralla"), ("palisade", "empalizada"), ("fieldstone", "muro bajo"),
                   ("plank", "muro de tablas"), ("brick", "muralla")):
    reg("wall_" + _key, "wall_%s_demo_slope" % _key, "Demostración en ladera (18 m, sube 3 m)",
        (lambda p, key=_key: slope_demo(p, key)), material=wall_models.MATERIAL[_key],
        nota="Montada con 2 remates, 3 rectos, 3 escalones de 1 m y 1 pieza con brasero sobre una cuña de "
             "terreno: así seguiría la %s una pendiente." % _txt)


# --- Water gate ------------------------------------------------------------------------------


def water_gate(p, W):
    """A 4 m stretch of wall over a channel 3 m wide: an arch closed by an
    iron grate that lifts (`open` / `close`), so boats and the stream
    pass under the wall walk."""
    for s in (-1, 1):
        W.run(p.at(rot=0 if s > 0 else 180), 1.5, 2.0)
    arch = 2.3
    W.run(p, -1.5, 1.5, floor=arch + 0.3)
    t = W.t
    for s in (-1, 1):
        p.box((s * 1.56, 0, arch / 2), (0.14, t + 0.14, arch), W.trim)
        for f in (-1, 1):
            p.box((s * 1.3, f * (t / 2 - 0.1), arch - 0.05), (0.42, 0.3, 0.5), W.trim)
            p.box((s * 1.0, f * (t / 2 - 0.1), arch + 0.12), (0.26, 0.3, 0.26), W.trim)
            p.taper((s * 1.78, f * (t / 2 + 0.2)), (0.5, 0.5), (0.36, 0.2), 0.0, 1.6, W.dark)   # Cutwaters.
    p.box((0, 0, arch + 0.3), (3.3, t + 0.16, 0.3), W.trim)
    p.box((0, -(t / 2 + 0.1), arch + 0.36), (0.44, 0.1, 0.5), W.light)
    p.box((0, 0, 0.03), (3.0, t + 3.0, 0.06), "water")
    w = {"grate": 1.0}
    for i in range(10):
        x = -1.35 + i * 0.3
        p.box((x, 0, 1.2), (0.07, 0.07, 2.2), "iron", w)
    for z in (0.35, 0.95, 1.55, 2.15):
        p.box((0, 0, z), (2.9, 0.09, 0.07), "iron_dark", w)
    y = -(t / 2 + 0.36)
    pts = [brazier(p, s * 1.78, y, 1.6, 0.9, bone) for s, bone in ((-1, "flame"), (1, "flame2"))]
    if p.static:
        return None
    mech = flame_mech(pts, extra=[("grate", (0, 0, 0.0), (0, 0, 1.0), None)])
    rise = min(2.0, W.h - arch + 0.9)

    def opened(t_):
        return {}, {"grate": (0, 0, rise * kit.smooth(t_))}

    mech.clip("open", 3.0, opened, loops=False)
    mech.clip("close", 3.0, lambda t_: opened(1.0 - t_), loops=False)
    return mech


WATER = {"open": "La reja sube y deja pasar barcas", "close": "La reja baja",
         "flicker": "Las llamas de los braseros se mueven"}
for _key, _nombre, _mat in (("stone", "Sillería", "piedra"), ("brick", "Ladrillo", "ladrillo y piedra"),
                            ("iron", "Reforzada con hierro", "piedra y hierro"), ("sandstone", "Arenisca", "piedra"),
                            ("dwarf", "Enana", "piedra y oro")):
    reg("gate_water", "gate_%s_water" % _key, _nombre, (lambda p, W=WALLS[_key]: water_gate(p, W)), material=_mat,
        anim=WATER)


# --- Turret piece ----------------------------------------------------------------------------


def turret(p, W):
    """A straight whose outer parapet swells into a small round turret
    with a conical roof: a sheltered post for one sentry."""
    W.run(p, -1.0, 1.0)
    top = W.h
    yc = -(W.half + 0.45)
    r = 0.85
    p.cyl((0, yc, top - 1.5), (0, yc, top - 0.3), 0.2, r + 0.05, W.dark, seg=10)   # The corbelled foot.
    p.cyl((0, yc, top - 0.3), (0, yc, top + 2.3), r, r, W.mat, seg=10)
    p.cyl((0, yc, top - 0.05), (0, yc, top + 0.05), r + 0.04, r + 0.04, W.dark, seg=10)
    p.cyl((0, yc, top + 2.2), (0, yc, top + 2.36), r + 0.1, r + 0.1, W.trim, seg=10)
    for a in (-90, -35, -145):   # Slits looking out and along the wall.
        ar = math.radians(a)
        p.box((0 + (r - 0.02) * math.cos(ar), yc + (r - 0.02) * math.sin(ar), top + 1.3), (0.12, 0.34, 0.9), W.trim,
              rz=a)
        p.box((0 + (r + 0.02) * math.cos(ar), yc + (r + 0.02) * math.sin(ar), top + 1.3), (0.1, 0.1, 0.7), "dark",
              rz=a)
    p.box((0, yc + r - 0.05, top + 0.95), (0.7, 0.2, 1.8), "dark")   # The doorway from the walk.
    cone_roof(p, (0, yc), r + 0.3, top + 2.36, 1.5, mats=W.roof, tiers=2, seg=10)


for _key in ("stone", "brick", "iron", "sandstone", "dwarf", "elf", "darkelf", "foxfolk", "catfolk"):
    reg("wall_" + _key, "wall_%s_turret" % _key, "Con garita", (lambda p, W=WALLS[_key]: turret(p, W)),
        material=wall_models.MATERIAL[_key])


# --- Ruins -----------------------------------------------------------------------------------

RUIN = Masonry("ruin", "stone", "stone_dark", "stone_light", "moss", 3.2, 1.2, course=0.6,
               rubble_mats=("stone", "stone_dark", "moss"))


def ivy(p, x0, x1, y, z0, z1, seed, n=7):
    r = rng("ivy", seed)
    for i in range(n):
        p.sphere((r.uniform(x0, x1), y + r.uniform(-0.05, 0.05), r.uniform(z0, z1)), r.uniform(0.18, 0.32),
                 r.choice(("leaves", "leaves_dark", "moss")), seg=6, rings=4, scale=(1.2, 0.6, 1.0))


def ruin_straight(p):
    """An old wall, its top broken down in ragged steps and overgrown."""
    W = RUIN
    for x0, x1, h in ((-1.0, -0.45, 2.9), (-0.45, 0.1, 2.2), (0.1, 0.55, 2.55), (0.55, 1.0, 1.5)):
        W.body(p, x0, x1, 0.0, h)
    rubble(p, -0.9, 0.9, W.t / 2, W.rubble_mats, "ruin_s", n=10, size=0.35)
    ivy(p, -0.9, 0.9, -W.t / 2 - 0.05, 0.3, 2.2, "s1")
    ivy(p, -0.2, 0.9, W.t / 2 + 0.05, 0.2, 1.4, "s2", n=4)


def ruin_corner(p):
    W = RUIN
    W.body(p, -0.6, 0.6, 0.0, 3.3)
    for q, hs in ((p, (2.6, 1.7)), (p.at(rot=90), (2.1, 1.0))):
        q_ = q
        W.body(q_, 0.6, 0.85, 0.0, hs[0])
        W.body(q_, 0.85, 1.0, 0.0, hs[1])
    rubble(p, -0.2, 1.0, W.t / 2, W.rubble_mats, "ruin_c", n=10, size=0.35)
    ivy(p, -0.6, 0.6, -W.t / 2 - 0.05, 0.4, 2.8, "c1")
    ivy(p.at(rot=90), -0.4, 0.8, W.t / 2 + 0.05, 0.3, 1.8, "c2", n=5)


def ruin_arch(p):
    """A gateway 4 m wide whose arch still stands; the doors are gone."""
    W = RUIN
    for s, h in ((-1, 3.6), (1, 3.1)):
        W.body(p, min(s * 1.3, s * 2.0), max(s * 1.3, s * 2.0), 0.0, h)
        p.box((s * 1.36, 0, 1.3), (0.16, W.t + 0.12, 2.6), "stone_light")
        for f in (-1, 1):
            p.box((s * 1.1, f * (W.t / 2 - 0.1), 2.5), (0.4, 0.3, 0.4), "stone_light")
    p.box((-0.1, 0, 2.95), (2.9, W.t + 0.1, 0.5), "stone")
    p.box((-0.6, 0, 3.4), (1.6, W.t, 0.5), "stone_dark")
    p.box((0, -W.t / 2 - 0.06, 2.95), (0.4, 0.1, 0.56), "stone_light")
    p.box((-1.36, 0.0, 1.9), (0.1, 0.12, 0.3), "rust")   # What is left of a hinge.
    rubble(p, -1.0, 1.9, W.t / 2, W.rubble_mats, "ruin_a", n=12, size=0.4)
    ivy(p, -1.9, -1.0, -W.t / 2 - 0.05, 0.4, 3.2, "a1")
    ivy(p, -1.5, 0.6, -W.t / 2 - 0.05, 2.9, 3.6, "a2", n=5)
    ivy(p, 1.2, 1.9, W.t / 2 + 0.05, 0.3, 2.4, "a3", n=5)


def ruin_tower(p):
    """The stump of a round tower, split open, with a tree growing in it."""
    r = 1.8
    seg = 12
    heights = (4.6, 4.2, 3.4, 2.2, 1.2, 0.7, 1.6, 2.6, 3.8, 4.4, 4.9, 4.8)
    for k in range(seg):
        a0 = 2 * math.pi * k / seg
        a1 = 2 * math.pi * (k + 1) / seg
        pts = [(r * math.cos(a0), r * math.sin(a0)), (r * math.cos(a1), r * math.sin(a1)),
               ((r - 0.5) * math.cos(a1), (r - 0.5) * math.sin(a1)),
               ((r - 0.5) * math.cos(a0), (r - 0.5) * math.sin(a0))]
        p.prism(pts, 0.0, heights[k], "stone" if k % 3 else "stone_light")
        am = (a0 + a1) / 2
        for z in (0.9, 1.7, 2.5, 3.3, 4.1):
            if z < heights[k] - 0.2:
                p.box(((r + 0.005) * math.cos(am), (r + 0.005) * math.sin(am), z), (0.06, 0.98, 0.06), "stone_dark",
                      rz=math.degrees(am))
    p.cyl((0, 0, 0), (0, 0, 0.3), r + 0.3, r + 0.1, "stone_dark", seg=seg)
    rubble(p, -1.6, 1.6, 1.9, ("stone", "stone_dark", "moss"), "ruin_t", n=12, size=0.45)
    p.cyl((0.1, 0.0, 0.2), (0.3, 0.1, 3.2), 0.2, 0.12, "timber", seg=6)
    p.cyl((0.3, 0.1, 3.2), (0.9, 0.3, 4.6), 0.1, 0.05, "timber", seg=5)
    p.cyl((0.3, 0.1, 3.0), (-0.5, -0.2, 4.4), 0.1, 0.05, "timber", seg=5)
    for c, rad in (((0.9, 0.3, 4.9), 0.9), ((-0.5, -0.2, 4.8), 0.8), ((0.2, 0.3, 5.6), 0.85), ((0.3, -0.6, 4.4), 0.6)):
        p.sphere(c, rad, "leaves" if rad > 0.8 else "leaves_light", seg=7, rings=5)
    ivy(p.at(rot=200), -0.8, 0.8, -r - 0.05, 0.4, 3.4, "t1", n=9)


reg("wall_ruin", "wall_ruin_straight", "Tramo de muro", ruin_straight, material="piedra")
reg("wall_ruin", "wall_ruin_corner", "Esquina", ruin_corner, material="piedra")
reg("wall_ruin", "wall_ruin_arch", "Arco de puerta (4 m)", ruin_arch, material="piedra")
reg("wall_ruin", "wall_ruin_tower", "Torre desmochada", ruin_tower, material="piedra")


# --- Kit sheet -------------------------------------------------------------------------------


def kit_sheet(p, key):
    """Every piece of one wall type laid out in rows, with its gate and
    its postern, to see the whole kit at once."""
    W = WALLS[key]
    q = Pen(p.mb, p.m, True)
    items = []
    for kind in wall_models.SETS[key]:
        width = stairs_length(W) if kind == "stairs" else 3.0 if kind == "diagonal" else 2.0
        items.append((width, lambda pen, kind=kind: PIECES[kind](pen, W)))
    items.append((4.0, gates.gate_for(key)))
    if key != "hedge":
        items.append((2.0, lambda pen: gates.postern(pen, W)))
    rows, row, used = [], [], 0.0
    for width, fn in items:
        if row and used + width > 24.0:
            rows.append((row, used))
            row, used = [], 0.0
        row.append((width, fn))
        used += width + 1.6
    rows.append((row, used))
    for i, (row, used) in enumerate(rows):
        x = -(used - 1.6) / 2
        y = (i - (len(rows) - 1) / 2) * 5.5
        for width, fn in row:
            fn(q.at(x=x + width / 2, y=y))
            x += width + 1.6
    return None


for _key in wall_models.SETS:
    reg("wall_" + _key, "wall_%s_demo_kit" % _key, "Muestrario de piezas", (lambda p, key=_key: kit_sheet(p, key)),
        material=wall_models.MATERIAL[_key],
        nota="Todas las piezas del tipo en filas, en el orden de la lista, seguidas de su puerta y su poterna.")


# --- Bell tower ------------------------------------------------------------------------------


def bell_tower(p, W):
    """A slim alarm tower 3 x 3 m: a shaft of 8 m, an open belfry with a
    great bell that swings (`ring`) and a hipped roof."""
    H, hs = 8.0, 1.3
    p.taper((0, 0), (3.0, 3.0), (2.66, 2.66), 0.0, 1.0, W.dark)
    W.block(p, -hs, hs, -hs, hs, 0.0, H, 0.0, proud_x=True)
    p.box((0, 0, H + 0.1), (2.9, 2.9, 0.22), W.trim)
    p.box((0, 0, 4.2), (2.7, 2.7, 0.14), W.trim)
    for d in "SEW":
        towers.slit_on(p, W, d, 0.0, 2.8, hs)
        towers.slit_on(p, W, d, 0.0, 6.2, hs)
    towers.door_on(p, W, "N", 0.0, hs)
    top = H + 0.2
    for sx in (-1, 1):
        for sy in (-1, 1):
            p.box((sx * 1.05, sy * 1.05, top + 1.25), (0.5, 0.5, 2.5), W.mat)
            p.box((sx * 1.05, sy * 1.05, top + 2.3), (0.58, 0.58, 0.14), W.trim)
    for d in "ESWN":
        q = p.at(rot=towers.SIDE_ROT[d])
        q.box((0, -1.05, top + 2.72), (2.6, 0.5, 0.5), W.mat)
        q.box((0, -1.32, top + 2.5), (0.34, 0.08, 0.44), W.trim)
        q.box((0, -1.2, top + 0.3), (1.6, 0.12, 0.6), W.mat)
        q.box((0, -1.2, top + 0.63), (1.7, 0.2, 0.08), W.trim)
    p.box((0, 0, top + 3.02), (2.9, 2.9, 0.14), W.dark)
    pyramid_roof(p, (0, 0), 2.6, 2.6, top + 3.08, 2.3, W.roof, over=0.3)
    zb = top + 2.35
    p.box((0, 0, zb + 0.06), (2.1, 0.16, 0.16), "timber")
    w = {"bell": 1.0}
    p.box((0, 0, zb - 0.08), (0.7, 0.2, 0.2), "timber", w)
    p.cyl((0, 0, zb - 0.18), (0, 0, zb - 0.5), 0.2, 0.3, "bell", w, seg=10)
    p.cyl((0, 0, zb - 0.5), (0, 0, zb - 1.0), 0.3, 0.52, "bell", w, seg=10)
    p.cyl((0, 0, zb - 1.0), (0, 0, zb - 1.08), 0.56, 0.56, "bell", w, seg=10)
    wc = {"clapper": 1.0}
    p.cyl((0, 0, zb - 0.4), (0, 0, zb - 1.05), 0.03, 0.03, "iron_dark", wc, seg=5)
    p.sphere((0, 0, zb - 1.1), 0.1, "iron_dark", wc, seg=6, rings=4)
    p.cyl((0.9, 0, zb), (0.9, 0.05, top + 0.2), 0.015, 0.015, "rope", seg=4)
    if p.static:
        return None
    mech = kit.Mech([("bell", (0, 0, zb), (0, 0, zb - 0.5), None),
                     ("clapper", (0, 0, zb - 0.4), (0, 0, zb - 1.0), "bell")])
    mech.clip("ring", 1.6, lambda t_: {
        "bell": [(kit.X, 30.0 * math.sin(2 * math.pi * t_))],
        "clapper": [(kit.X, -22.0 * math.sin(2 * math.pi * t_ + 0.7))],
    })
    return mech


for _key, _nombre, _mat in (("stone", "Sillería", "piedra"), ("brick", "Ladrillo", "ladrillo y piedra"),
                            ("sandstone", "Arenisca", "piedra"), ("elf", "Élfica", "piedra"),
                            ("dwarf", "Enana", "piedra y oro")):
    reg("tower_bell", "tower_%s_bell" % _key, _nombre, (lambda p, W=WALLS[_key]: bell_tower(p, W)),
        material=_mat + " y bronce", anim={"ring": "La campana voltea y repica"})
