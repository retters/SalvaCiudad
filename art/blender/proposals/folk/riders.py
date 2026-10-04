"""Riders on mounts, and the mounts alone with their saddles: one model
holds the mount and its rider, with the clips idle, walk and gallop (and
attack for the armed ones).

Unlike the people on foot (welded bodies on the game's humanoid skeleton),
these are made of faceted rigid pieces, each bound whole to one bone of a
kit.Mech: a mount's four (or two) legs swing from the hip and bend at the
knee, its neck, head and tail move, and the rider sits in the saddle with
bones of its own ("r_hips", "r_chest", "r_head", "r_arm_R_u"...), so a
later version can swap the rider for one of the game's characters.
"""

import math
import random

from mathutils import Vector

import _folk as F
import studies
from _folk import kit
from lizardfolk import HEAD_POINTS, JAW_POINTS, sym

TAU = math.tau
X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)


# ------------------------------------------------------------------ pieces

def W(bone):
    return {bone: 1.0}


def bind(mb, verts, bone):
    g = mb._group_index(bone)
    for v in verts:
        v[mb.deform][g] = 1.0
    return verts


def hull(mb, points, mat, bone):
    return bind(mb, F.hull(mb, [Vector(p) for p in points], mat), bone)


def lump(mb, center, radii, mat, bone, seed=1, count=14, tones=True):
    """A faceted lump with lighter and darker facets."""
    rnd = random.Random(seed)
    verts = hull(mb, studies.ellipsoid_points(center, radii, count, rnd), mat, bone)
    if tones:
        faces = []      # In the order they were made: a set's order changes from run to run.
        for v in verts:
            faces += [f for f in v.link_faces if f not in faces]
        for f in faces:
            r = rnd.random()
            if r < 0.2:
                f.material_index = mb._material_index(mat + "_light")
            elif r < 0.4:
                f.material_index = mb._material_index(mat + "_shade")
    return verts


def seg(mb, a, b, ra, rb, mat, bone, sides=6):
    return mb.cylinder(a, b, ra, rb, mat, weights=W(bone), segments=sides)


def cone(mb, a, b, r, mat, bone, sides=4):
    return mb.cylinder(a, b, r, 0.0, mat, weights=W(bone), segments=sides)


def slab(mb, lo, hi, mat, bone):
    return hull(mb, [(x, y, z) for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])], mat, bone)


def plate(mb, points, thickness, mat, bone):
    return bind(mb, studies.plate(mb, points, thickness, mat), bone)


def snout(mb, a, b, ha, hb, mat, bone, mid=None):
    """A head as a faceted wedge from a (half sizes ha = (x, z)) to b (hb)."""
    a, b = Vector(a), Vector(b)
    d = (b - a).normalized()
    up = Vector((0.0, d.z, -d.y)).normalized()
    if up.z < 0:
        up = -up
    side = Vector((1, 0, 0))
    pts = []
    rings = [(a, ha), (b, hb)] + ([(a.lerp(b, 0.5), mid)] if mid else [])
    for c, h in rings:
        pts += [c + side * (sx * h[0]) + up * (h[1] * 0.35) for sx in (-1, 1)]
        pts += [c + side * (sx * h[0] * 0.6) + up * h[1] for sx in (-1, 1)]
        pts += [c + side * (sx * h[0] * 0.7) - up * h[1] for sx in (-1, 1)]
    return hull(mb, pts, mat, bone), d, up


# ------------------------------------------------------------------ mounts

LEGS4 = (("FL", 1, "f"), ("FR", -1, "f"), ("HL", 1, "h"), ("HR", -1, "h"))
WALK4 = {"FL": 0.0, "HR": 0.06, "FR": 0.5, "HL": 0.56}
GALLOP4 = {"HL": 0.0, "HR": 0.12, "FL": 0.5, "FR": 0.62}

MOUNTS = dict(
    horse=dict(z=1.27, w=0.3, rz=0.33, fy=-0.56, hy=0.58, lx=0.19, hip=1.06, knee=0.56, ur=0.1, lr=0.058,
               neck=((0, -0.68, 1.42), (0, -1.06, 1.96)), nr=(0.21, 0.13), head=0.52, hr=(0.115, 0.13), drop=0.62,
               muzzle=(0.062, 0.07), tail=((0, 0.84, 1.42), (0, 1.02, 1.15), (0, 1.06, 0.62)), tr=(0.06, 0.1, 0.03),
               seat=(0, 0.02, 1.63), foot="hoof", cycle=1.0, swing=18.0, bend=40.0, gcycle=0.5, gswing=34.0),
    mule=dict(z=1.12, w=0.29, rz=0.31, fy=-0.5, hy=0.52, lx=0.18, hip=0.93, knee=0.48, ur=0.09, lr=0.055,
              neck=((0, -0.62, 1.25), (0, -0.98, 1.62)), nr=(0.2, 0.13), head=0.5, hr=(0.115, 0.13), drop=0.5,
              muzzle=(0.07, 0.075), tail=((0, 0.76, 1.24), (0, 0.9, 0.95), (0, 0.92, 0.62)), tr=(0.03, 0.035, 0.05),
              seat=(0, 0.02, 1.46), foot="hoof", cycle=1.05, swing=17.0, bend=38.0, gcycle=0.56, gswing=28.0),
    wolf=dict(z=1.02, w=0.27, rz=0.27, fy=-0.5, hy=0.56, lx=0.18, hip=0.86, knee=0.45, ur=0.095, lr=0.05,
              neck=((0, -0.6, 1.12), (0, -0.92, 1.3)), nr=(0.24, 0.18), head=0.5, hr=(0.16, 0.14), drop=0.25,
              muzzle=(0.065, 0.06), tail=((0, 0.8, 1.1), (0, 1.15, 0.98), (0, 1.45, 0.8)), tr=(0.09, 0.13, 0.03),
              seat=(0, 0.0, 1.32), foot="paw", cycle=0.8, swing=22.0, bend=50.0, gcycle=0.42, gswing=38.0),
    ram=dict(z=0.86, w=0.3, rz=0.29, fy=-0.4, hy=0.44, lx=0.17, hip=0.66, knee=0.34, ur=0.085, lr=0.045,
             neck=((0, -0.5, 0.98), (0, -0.72, 1.2)), nr=(0.2, 0.15), head=0.36, hr=(0.13, 0.12), drop=0.7,
             muzzle=(0.06, 0.065), tail=((0, 0.66, 0.98), (0, 0.74, 0.86), (0, 0.76, 0.76)), tr=(0.05, 0.05, 0.02),
             seat=(0, 0.02, 1.18), foot="hoof", cycle=0.8, swing=20.0, bend=42.0, gcycle=0.44, gswing=34.0),
    boar=dict(z=0.82, w=0.34, rz=0.32, fy=-0.42, hy=0.46, lx=0.19, hip=0.6, knee=0.32, ur=0.1, lr=0.05,
              neck=((0, -0.5, 0.88), (0, -0.72, 0.9)), nr=(0.3, 0.24), head=0.5, hr=(0.2, 0.19), drop=0.35,
              muzzle=(0.075, 0.07), tail=((0, 0.64, 0.96), (0, 0.82, 0.94), (0, 0.88, 0.8)), tr=(0.03, 0.022, 0.03),
              seat=(0, 0.04, 1.17), foot="hoof", cycle=0.75, swing=20.0, bend=40.0, gcycle=0.42, gswing=32.0),
    elk=dict(z=1.36, w=0.27, rz=0.31, fy=-0.54, hy=0.56, lx=0.17, hip=1.14, knee=0.6, ur=0.085, lr=0.045,
             neck=((0, -0.64, 1.5), (0, -0.94, 2.06)), nr=(0.19, 0.12), head=0.46, hr=(0.1, 0.11), drop=0.45,
             muzzle=(0.055, 0.06), tail=((0, 0.8, 1.5), (0, 0.88, 1.42), (0, 0.9, 1.34)), tr=(0.05, 0.05, 0.02),
             seat=(0, 0.02, 1.7), foot="hoof", cycle=0.95, swing=18.0, bend=42.0, gcycle=0.48, gswing=34.0),
    cat=dict(z=0.98, w=0.24, rz=0.25, fy=-0.5, hy=0.56, lx=0.17, hip=0.82, knee=0.42, ur=0.1, lr=0.055,
             neck=((0, -0.6, 1.06), (0, -0.86, 1.2)), nr=(0.2, 0.17), head=0.34, hr=(0.17, 0.15), drop=0.2,
             muzzle=(0.09, 0.075), tail=((0, 0.8, 1.02), (0, 1.25, 0.8), (0, 1.6, 0.95)), tr=(0.055, 0.05, 0.04),
             seat=(0, 0.0, 1.26), foot="paw", cycle=0.85, swing=22.0, bend=50.0, gcycle=0.4, gswing=40.0),
    lizard=dict(z=0.62, w=0.3, rz=0.2, fy=-0.6, hy=0.6, lx=0.26, hip=0.56, knee=0.44, ur=0.085, lr=0.06,
                neck=((0, -0.78, 0.66), (0, -1.1, 0.74)), nr=(0.2, 0.16), head=0.6, hr=(0.17, 0.11), drop=0.1,
                muzzle=(0.1, 0.05), tail=((0, 0.9, 0.62), (0, 1.6, 0.4), (0, 2.4, 0.1)), tr=(0.18, 0.11, 0.02),
                seat=(0, 0.0, 0.86), foot="claw", cycle=0.9, swing=24.0, bend=14.0, gcycle=0.5, gswing=34.0,
                sprawl=0.3),
)


def quadruped(mb, m, coat="coat", belly=None):
    """The body, legs, neck, head and tail of a four-legged mount. Returns
    its bones and the head's frame (base, forward, up) for the trimmings."""
    z, w, rz, fy, hy = m["z"], m["w"], m["rz"], m["fy"], m["hy"]
    sprawl = m.get("sprawl", 0.0)
    bones = [("body", (0, 0, z), (0, -0.4, z), None)]
    lump(mb, (0, fy * 0.82, z + 0.02), (w, abs(fy) * 0.72, rz * 1.06), coat, "body", 1, 18)
    lump(mb, (0, 0.02, z - 0.01), (w * 0.96, (hy - fy) * 0.42, rz * 0.96), belly or coat, "body", 2, 16)
    lump(mb, (0, hy * 0.82, z + 0.02), (w * 1.04, hy * 0.72, rz * 1.05), coat, "body", 3, 18)
    n0, n1 = Vector(m["neck"][0]), Vector(m["neck"][1])
    seg(mb, n0 + (n0 - n1) * 0.25, n1, m["nr"][0], m["nr"][1], coat, "neck", sides=7)
    bones.append(("neck", tuple(n0), tuple(n1), "body"))
    d = Vector((0, -1, -m["drop"])).normalized()
    a = n1 + Vector((0, 0.04, 0.02))
    tip = a + d * m["head"]
    hr = m["hr"]
    _, d, up = snout(mb, a, tip, hr, m["muzzle"], coat, "head", mid=(hr[0] * 0.8, hr[1] * 0.8))
    for sx in (-1, 1):
        p = a + d * (m["head"] * 0.32) + Vector((sx * hr[0] * 0.78, 0, 0)) + up * (hr[1] * 0.45)
        mb.sphere(p, hr[0] * 0.16, "eye", weights=W("head"), segments=5, rings=3)
    bones.append(("head", tuple(n1), tuple(tip), "neck"))
    t = [Vector(p) for p in m["tail"]]
    tr = m["tr"]
    seg(mb, t[0], t[1], tr[0], tr[1], m.get("tail_mat", coat), "tail", sides=6)
    seg(mb, t[1], t[2], tr[1], tr[2], m.get("tail_mat", coat), "tail", sides=6)
    bones.append(("tail", tuple(t[0]), tuple(t[2]), "body"))
    k = m["hip"] / 1.06      # The feet's size follows the leg's length.
    for name, sx, end in LEGS4:
        y = fy if end == "f" else hy
        x = sx * m["lx"]
        hip = Vector((x, y, m["hip"]))
        knee = Vector((x + sx * sprawl, y + (-0.02 if end == "f" else 0.07) * k, m["knee"]))
        ankle = Vector((x + sx * sprawl * 1.25, y + (0.0 if end == "f" else 0.02), 0.1 * k))
        upper, lower = f"leg_{name}_u", f"leg_{name}_l"
        lump(mb, hip + Vector((0, 0, 0.06 * k)), (m["ur"] * 1.5, m["ur"] * 1.9, m["ur"] * 2.2), coat, upper,
             10 + len(bones), 10)
        seg(mb, hip, knee, m["ur"] * 1.1, m["ur"] * 0.72, coat, upper)
        seg(mb, knee, ankle, m["lr"] * 1.15, m["lr"] * 0.9, m.get("leg_mat", coat), lower)
        mb.sphere(knee, m["ur"] * 0.74, coat, weights=W(lower), segments=6, rings=4)
        f, r = m["foot"], m["lr"]
        if f == "hoof":
            mb.cylinder(ankle, (ankle.x, ankle.y - 0.02 * k, 0.0), r * 1.1, r * 1.45, "hoof", weights=W(lower),
                        segments=6)
        else:
            hull(mb, [(ankle.x - r * 1.5, ankle.y + r * 1.2, 0.0), (ankle.x + r * 1.5, ankle.y + r * 1.2, 0.0),
                      (ankle.x - r * 1.7, ankle.y - r * 2.6, 0.0), (ankle.x + r * 1.7, ankle.y - r * 2.6, 0.0),
                      (ankle.x - r, ankle.y + r, 0.13 * k), (ankle.x + r, ankle.y + r, 0.13 * k),
                      (ankle.x, ankle.y - r * 2.0, 0.08 * k)], m.get("leg_mat", coat), lower)
            if f == "claw":
                for dx in (-1, 0, 1):
                    cone(mb, (ankle.x + dx * r, ankle.y - r * 2.4, 0.03), (ankle.x + dx * r * 1.3, ankle.y - r * 4.0, 0.0),
                         r * 0.4, "horn", lower)
        bones.append((upper, tuple(hip), tuple(knee), "body"))
        bones.append((lower, tuple(knee), (ankle.x, ankle.y, 0.0), upper))
    return bones, (a, d, up, tip)


def ears(mb, frame, m, mat, length=0.2, spread=0.6, back=0.0):
    a, d, up, tip = frame
    for sx in (-1, 1):
        base = a + Vector((sx * m["hr"][0] * spread, 0, 0)) + up * m["hr"][1] * 0.8 - d * 0.02
        cone(mb, base, base + up * length + Vector((sx * length * 0.3, 0, 0)) - d * back, m["hr"][0] * 0.3, mat, "head")


def mane(mb, m, mat, height=0.2):
    n0, n1 = Vector(m["neck"][0]), Vector(m["neck"][1])
    d = (n1 - n0).normalized()
    out = Vector((0, -d.z, d.y))
    if out.y < 0:
        out = -out
    for i in range(5):
        c = n0.lerp(n1, 0.1 + 0.2 * i) + out * (m["nr"][0] + (m["nr"][1] - m["nr"][0]) * i / 4 + height * 0.3)
        hull(mb, [c + d * 0.1 + out * height * 0.5, c - d * 0.1 + out * height * 0.5, c + d * 0.12 - out * height * 0.5,
                  c - d * 0.12 - out * height * 0.5, c + Vector((0.035, 0, 0)), c - Vector((0.035, 0, 0))], mat, "neck")


def saddle(mb, m, blanket="accent", bags=False, pack=False):
    s = Vector(m["seat"])
    w = m["w"]
    hull(mb, [(sx * (w + 0.03), s.y + y, s.z - dz) for sx in (-1, 1) for y, dz in ((-0.3, 0.3), (0.34, 0.3))]
         + [(sx * w * 0.6, s.y + y, s.z - 0.035) for sx in (-1, 1) for y in (-0.3, 0.34)], blanket, "body")
    hull(mb, [(sx * 0.17, s.y - 0.2, s.z - 0.03) for sx in (-1, 1)] + [(sx * 0.19, s.y + 0.22, s.z - 0.03) for sx in (-1, 1)]
         + [(sx * 0.1, s.y - 0.24, s.z + 0.07) for sx in (-1, 1)] + [(sx * 0.14, s.y + 0.27, s.z + 0.09) for sx in (-1, 1)]
         + [(sx * 0.12, s.y, s.z + 0.005) for sx in (-1, 1)] + [(sx * (w + 0.04), s.y, s.z - 0.2) for sx in (-1, 1)],
         "leather", "body")
    for sx in (-1, 1):   # Girth and stirrups.
        seg(mb, (sx * (w + 0.035), s.y - 0.02, s.z - 0.2), (sx * (w + 0.05), s.y - 0.06, s.z - 0.56), 0.012, 0.012,
            "leather_dark", "body", sides=4)
        slab(mb, (sx * (w + 0.05) - 0.05, s.y - 0.12, s.z - 0.6), (sx * (w + 0.05) + 0.05, s.y - 0.0, s.z - 0.56),
             "metal", "body")
    if bags or pack:
        for sx in (-1, 1):
            c = Vector((sx * (w + 0.1), s.y + 0.4, s.z - 0.26))
            mb.box(c, (0.16, 0.3, 0.26), "leather", weights=W("body"))
            mb.box(c + Vector((0, 0, 0.1)), (0.18, 0.32, 0.08), "leather_dark", weights=W("body"))
    if pack:
        lump(mb, (0, s.y + 0.45, s.z + 0.1), (0.3, 0.24, 0.2), "sack", "body", 31, 16)
        mb.cylinder((-0.34, s.y + 0.44, s.z + 0.32), (0.34, s.y + 0.44, s.z + 0.32), 0.09, 0.09, "accent",
                    weights=W("body"), segments=7)
        mb.box((0, s.y + 0.78, s.z - 0.02), (0.44, 0.3, 0.26), "wood", weights=W("body"))


def bridle(mb, frame, m, mat="leather_dark"):
    a, d, up, tip = frame
    for t, grow in ((0.45, 1.06), (0.8, 1.08)):
        c = a + d * (m["head"] * t)
        hx = (m["hr"][0] + (m["muzzle"][0] - m["hr"][0]) * t) * grow
        hz = (m["hr"][1] + (m["muzzle"][1] - m["hr"][1]) * t) * grow
        hull(mb, [c + Vector((sx * hx, 0, 0)) + up * (sz * hz) + d * (sd * 0.018) for sx in (-1, 1) for sz in (-1, 1)
                  for sd in (-1, 1)], mat, "head")


def trim_horse(mb, m, frame, mane_mat="mane"):
    ears(mb, frame, m, "coat", 0.16, 0.6)
    mane(mb, m, mane_mat, 0.2)
    a, d, up, tip = frame
    lump(mb, a + up * m["hr"][1] * 0.9 + d * 0.08, (0.05, 0.12, 0.07), mane_mat, "head", 5, 8, tones=False)
    lump(mb, tip + d * 0.0, (m["muzzle"][0] * 1.05, 0.06, m["muzzle"][1] * 1.05), "muzzle", "head", 6, 10, tones=False)


def trim_barding(mb, m, frame):
    """A war horse's cloth caparison and its steel face plate."""
    a, d, up, tip = frame
    z, w, rz, fy, hy = m["z"], m["w"], m["rz"], m["fy"], m["hy"]
    # The cloth drapes over the forehand and the croup as two tents that
    # hug the back and flare toward the hem, with a gold border below.
    for y0, y1 in ((fy * 1.5, -0.27), (0.31, hy * 1.5)):
        low, hem = z - rz * 1.45, z - rz * 1.7
        hull(mb, [(sx * x, y, zz) for sx in (-1, 1) for y in (y0, y1)
                  for x, zz in ((w * 0.5, z + rz * 1.1), (w * 0.98, z + rz * 0.5), (w + 0.05, low))], "accent", "body")
        hull(mb, [(sx * x, y, zz) for sx in (-1, 1) for y in (y0 - 0.01, y1 + 0.01)
                  for x, zz in ((w + 0.06, low + 0.01), (w + 0.065, hem))], "gold", "body")
    hull(mb, [a + up * (m["hr"][1] * 1.08) + Vector((sx * m["hr"][0] * 0.8, 0, 0)) for sx in (-1, 1)]
         + [tip + up * (m["muzzle"][1] * 1.15) + Vector((sx * m["muzzle"][0] * 0.9, 0, 0)) - d * 0.08 for sx in (-1, 1)]
         + [a.lerp(tip, 0.5) + up * (m["hr"][1] * 1.2)], "metal", "head")
    cone(mb, a.lerp(tip, 0.3) + up * m["hr"][1] * 1.1, a.lerp(tip, 0.3) + up * (m["hr"][1] * 1.1 + 0.16), 0.03, "gold",
         "head")


def trim_mule(mb, m, frame):
    ears(mb, frame, m, "coat", 0.32, 0.6)
    mane(mb, m, "mane", 0.1)
    a, d, up, tip = frame
    lump(mb, tip, (m["muzzle"][0] * 1.08, 0.07, m["muzzle"][1] * 1.08), "muzzle", "head", 6, 10, tones=False)
    lump(mb, Vector(m["tail"][2]), (0.05, 0.05, 0.12), "mane", "tail", 7, 8, tones=False)


def trim_wolf(mb, m, frame):
    ears(mb, frame, m, "coat", 0.2, 0.7, back=0.05)
    a, d, up, tip = frame
    cone(mb, tip + up * 0.02, tip + d * 0.06 + up * 0.03, 0.045, "eye", "head")
    for sx in (-1, 1):
        cone(mb, tip - d * 0.06 + Vector((sx * 0.04, 0, 0)) - up * 0.04, tip - d * 0.05 + Vector((sx * 0.045, 0, 0)) - up * 0.14,
             0.02, "horn", "head")
        lump(mb, a + Vector((sx * 0.17, 0.06, -0.05)), (0.08, 0.12, 0.13), "mane", "head", 20 + sx, 8, tones=False)
    n0, n1 = Vector(m["neck"][0]), Vector(m["neck"][1])
    lump(mb, n0.lerp(n1, 0.3) + Vector((0, 0.08, 0.12)), (0.25, 0.3, 0.22), "mane", "neck", 22, 14)


def trim_ram(mb, m, frame, wool="mane"):
    a, d, up, tip = frame
    for sx in (-1, 1):
        base = a + Vector((sx * 0.08, 0, 0)) + up * 0.1
        pts = [base, base + Vector((sx * 0.14, 0.1, 0.08)), base + Vector((sx * 0.22, 0.12, -0.08)),
               base + Vector((sx * 0.2, -0.04, -0.2)), base + Vector((sx * 0.13, -0.14, -0.12))]
        F.tube(mb, pts, [0.06, 0.055, 0.045, 0.03, 0.0], "horn", sides=5)
    bind(mb, [v for v in mb.bm.verts if not v[mb.deform]], "head")
    ears(mb, frame, m, "coat", 0.1, 1.0)
    z, w, rz = m["z"], m["w"], m["rz"]
    for i, (px, py, pz) in enumerate(((0.16, -0.3, 0.2), (-0.16, -0.3, 0.2), (0.2, 0.3, 0.18), (-0.2, 0.3, 0.18),
                                      (0.0, 0.62, 0.1), (0.25, 0.0, -0.05), (-0.25, 0.0, -0.05))):
        lump(mb, (px, py, z + pz), (0.2, 0.22, 0.18), wool, "body", 40 + i, 10)
    n0 = Vector(m["neck"][0])
    lump(mb, n0 + Vector((0, 0.05, 0.02)), (0.25, 0.22, 0.25), wool, "neck", 48, 12)


def trim_boar(mb, m, frame):
    a, d, up, tip = frame
    ears(mb, frame, m, "coat", 0.12, 0.8)
    mb.cylinder(tip - d * 0.02, tip + d * 0.03, m["muzzle"][0] * 1.1, m["muzzle"][0] * 1.0, "muzzle", weights=W("head"),
                segments=6)
    for sx in (-1, 1):
        cone(mb, tip - d * 0.1 + Vector((sx * 0.07, 0, 0)) - up * 0.03,
             tip - d * 0.04 + Vector((sx * 0.13, 0, 0)) + up * 0.14, 0.03, "horn", "head")
    z, hy, fy = m["z"], m["hy"], m["fy"]
    for i in range(6):   # A ridge of bristles along the back.
        y = fy * 1.1 + (hy - fy) * 1.2 * i / 5
        cone(mb, (0, y, z + m["rz"] * 0.95), (0, y + 0.08, z + m["rz"] + 0.16), 0.07, "mane",
             "body" if i > 0 else "neck")


def trim_elk(mb, m, frame):
    a, d, up, tip = frame
    ears(mb, frame, m, "coat", 0.14, 1.1)
    for sx in (-1, 1):
        base = a + Vector((sx * 0.05, 0, 0)) + up * 0.1
        beam = [base, base + Vector((sx * 0.16, 0.12, 0.3)), base + Vector((sx * 0.36, 0.1, 0.52)),
                base + Vector((sx * 0.44, -0.04, 0.78))]
        F.tube(mb, beam, [0.03, 0.028, 0.022, 0.0], "horn", sides=4)
        for at, tine in ((beam[1], (sx * 0.02, -0.2, 0.12)), (beam[2], (sx * 0.1, -0.2, 0.16)),
                         (beam[2], (sx * 0.16, 0.14, 0.18)), (beam[1], (sx * 0.14, 0.0, 0.2))):
            mb.cylinder(at, at + Vector(tine), 0.022, 0.0, "horn", segments=4)
    bind(mb, [v for v in mb.bm.verts if not v[mb.deform]], "head")
    n0, n1 = Vector(m["neck"][0]), Vector(m["neck"][1])
    lump(mb, n0.lerp(n1, 0.35) + Vector((0, -0.1, -0.12)), (0.16, 0.2, 0.26), "mane", "neck", 50, 12)
    lump(mb, tip, (m["muzzle"][0] * 1.05, 0.05, m["muzzle"][1] * 1.05), "muzzle", "head", 6, 10, tones=False)


def trim_cat(mb, m, frame, fangs=True):
    a, d, up, tip = frame
    ears(mb, frame, m, "coat", 0.12, 0.75)
    lump(mb, tip - d * 0.03 - up * 0.02, (m["muzzle"][0] * 1.15, 0.07, m["muzzle"][1] * 0.95), "belly", "head", 6, 10,
         tones=False)
    cone(mb, tip + up * 0.03, tip + d * 0.035 + up * 0.03, 0.035, "muzzle", "head")
    if fangs:
        for sx in (-1, 1):
            cone(mb, tip - d * 0.03 + Vector((sx * 0.05, 0, 0)) - up * 0.05,
                 tip - d * 0.01 + Vector((sx * 0.055, 0, 0)) - up * 0.22, 0.022, "horn", "head")


def trim_lizard(mb, m, frame):
    a, d, up, tip = frame
    z, hy, fy = m["z"], m["hy"], m["fy"]
    for i in range(9):   # Spikes along the back and the tail.
        y = fy * 1.5 + (hy * 1.6 - fy * 1.5) * i / 8
        cone(mb, (0, y, z + m["rz"] * 0.9), (0, y + 0.07, z + m["rz"] + 0.2 - 0.012 * i), 0.08, "mane",
             "neck" if i == 0 else "body")
    t = [Vector(p) for p in m["tail"]]
    for i in range(5):
        p = t[0].lerp(t[2], 0.12 + 0.15 * i)
        cone(mb, p + Vector((0, 0, 0.1 - 0.015 * i)), p + Vector((0, 0.06, 0.26 - 0.035 * i)), 0.06, "mane", "tail")
    for sx in (-1, 1):
        cone(mb, a + Vector((sx * 0.1, 0, 0)) + up * 0.08, a + Vector((sx * 0.17, 0.14, 0)) + up * 0.2, 0.05, "horn",
             "head")
    slab(mb, tuple(tip - Vector((0.08, 0, 0.012)) - d * 0.3), tuple(tip + Vector((0.08, 0, -0.03))), "eye", "head")


TRIMS = dict(horse=trim_horse, mule=trim_mule, wolf=trim_wolf, ram=trim_ram, boar=trim_boar, elk=trim_elk,
             cat=trim_cat, lizard=trim_lizard)


# --------------------------------------------------------- the two-legged ones

BIRD = dict(z=1.28, seat=(0, 0.08, 1.62), w=0.3, hip=1.1, knee=0.62, cycle=0.7, swing=26.0, bend=46.0, gcycle=0.4,
            gswing=40.0)
TOAD = dict(z=0.62, seat=(0, 0.12, 1.12), w=0.5, cycle=0.9, gcycle=0.7, sit="forward")


def bird(mb, m):
    """A giant running bird: a round body, a long neck, a big beak, small
    wings, a fan of tail feathers and two long legs."""
    z = m["z"]
    bones = [("body", (0, 0, z), (0, -0.4, z), None)]
    lump(mb, (0, 0.0, z), (0.36, 0.56, 0.4), "coat", "body", 1, 22)
    lump(mb, (0, -0.3, z - 0.02), (0.3, 0.3, 0.36), "belly", "body", 2, 14)
    n0, n1, n2 = Vector((0, -0.42, z + 0.2)), Vector((0, -0.62, z + 0.62)), Vector((0, -0.66, z + 1.0))
    seg(mb, n0, n1, 0.17, 0.11, "coat", "neck", sides=6)
    seg(mb, n1, n2, 0.11, 0.09, "coat", "neck", sides=6)
    lump(mb, n0 + Vector((0, 0.02, 0.02)), (0.22, 0.2, 0.22), "mane", "neck", 3, 12)
    bones.append(("neck", tuple(n0), tuple(n2), "body"))
    head = n2 + Vector((0, -0.05, 0.08))
    lump(mb, head, (0.15, 0.19, 0.15), "coat", "head", 4, 14)
    hull(mb, [head + Vector(p) for p in ((0.08, -0.12, 0.05), (-0.08, -0.12, 0.05), (0.07, -0.12, -0.09),
                                         (-0.07, -0.12, -0.09), (0.0, -0.46, -0.08), (0.0, -0.3, 0.06),
                                         (0.0, -0.36, -0.14))], "beak", "head")
    for sx in (-1, 1):
        mb.sphere(head + Vector((sx * 0.12, -0.08, 0.04)), 0.032, "eye", weights=W("head"), segments=5, rings=3)
    for i, (dx, dz) in enumerate(((-0.06, 0.2), (0.0, 0.28), (0.06, 0.2))):   # A crest.
        cone(mb, head + Vector((dx, 0.04, 0.1)), head + Vector((dx * 2, 0.2, 0.12 + dz)), 0.06, "accent", "head")
    bones.append(("head", tuple(n2), tuple(head + Vector((0, -0.4, -0.06))), "neck"))
    for i, (dx, dz) in enumerate(((-0.24, 0.2), (-0.12, 0.34), (0.0, 0.4), (0.12, 0.34), (0.24, 0.2))):
        plate(mb, [(dx * 0.4 - 0.05, 0.46, z + 0.1), (dx * 0.4 + 0.05, 0.46, z + 0.1), (dx + 0.07, 0.95, z + dz + 0.06),
                   (dx, 1.05, z + dz + 0.1), (dx - 0.07, 0.95, z + dz + 0.06)], 0.03, "mane" if i % 2 else "accent",
              "tail")
    bones.append(("tail", (0, 0.46, z + 0.1), (0, 1.0, z + 0.4), "body"))
    for name, sx in (("L", 1), ("R", -1)):
        wing = f"wing_{name}"
        plate(mb, [(sx * 0.36, -0.3, z + 0.2), (sx * 0.4, 0.2, z + 0.26), (sx * 0.4, 0.62, z + 0.02),
                   (sx * 0.38, 0.3, z - 0.18), (sx * 0.36, -0.2, z - 0.12)], 0.05, "mane", wing)
        bones.append((wing, (sx * 0.34, -0.28, z + 0.2), (sx * 0.4, 0.5, z), "body"))
        x = sx * 0.2
        hip, knee, ankle = Vector((x, 0.06, m["hip"])), Vector((x, -0.1, m["knee"])), Vector((x, 0.04, 0.1))
        upper, lower = f"leg_{name}_u", f"leg_{name}_l"
        lump(mb, hip + Vector((0, -0.02, -0.08)), (0.15, 0.2, 0.3), "coat", upper, 8 + sx, 12)
        seg(mb, hip, knee, 0.1, 0.06, "coat", upper)
        seg(mb, knee, ankle, 0.05, 0.04, "beak", lower)
        mb.sphere(knee, 0.062, "beak", weights=W(lower), segments=6, rings=4)
        for a in (-0.5, 0.0, 0.5):
            cone(mb, ankle, (x + math.sin(a) * 0.26, ankle.y - math.cos(a) * 0.3, 0.0), 0.045, "beak", lower)
        cone(mb, ankle, (x, ankle.y + 0.14, 0.0), 0.04, "beak", lower)
        bones.append((upper, tuple(hip), tuple(knee), "body"))
        bones.append((lower, tuple(knee), (x, 0.04, 0.0), upper))
    return bones


def toad(mb, m):
    """A giant toad: a squat warty body, a wide mouth, bulging eyes, small
    front legs and big folded hind legs."""
    z = m["z"]
    bones = [("body", (0, 0.3, z), (0, -0.3, z), None)]
    lump(mb, (0, 0.1, z), (0.56, 0.72, 0.46), "coat", "body", 1, 26)
    lump(mb, (0, -0.2, z - 0.12), (0.5, 0.56, 0.38), "belly", "body", 2, 18)
    head = Vector((0, -0.62, z + 0.12))
    hull(mb, [head + Vector(p) for p in sym([(0.4, 0.2, 0.0), (0.34, -0.2, 0.02), (0.14, -0.42, 0.04),
                                             (0.3, 0.1, 0.2), (0.16, -0.26, 0.2), (0.0, -0.44, 0.1),
                                             (0.0, 0.1, 0.26)])], "coat", "head")
    hull(mb, [head + Vector(p) for p in sym([(0.38, 0.18, -0.02), (0.32, -0.2, -0.01), (0.13, -0.4, 0.0),
                                             (0.3, 0.1, -0.22), (0.14, -0.3, -0.16), (0.0, -0.42, 0.0),
                                             (0.0, 0.0, -0.26)])], "belly", "head")
    for sx in (-1, 1):
        lump(mb, head + Vector((sx * 0.22, -0.04, 0.24)), (0.12, 0.13, 0.12), "coat", "head", 5 + sx, 10)
        mb.sphere(head + Vector((sx * 0.25, -0.1, 0.27)), 0.07, "iris", weights=W("head"), segments=6, rings=4)
        mb.sphere(head + Vector((sx * 0.27, -0.15, 0.28)), 0.035, "eye", weights=W("head"), segments=5, rings=3)
    bones.append(("head", (0, -0.4, z + 0.05), (0, -1.0, z + 0.1), "body"))
    rnd = random.Random(4)
    for i in range(12):   # Warts.
        a, b = rnd.uniform(-1.2, 1.2), rnd.uniform(0.2, 1.2)
        p = Vector((math.sin(a) * math.cos(b) * 0.54, 0.15 + rnd.uniform(-0.4, 0.5), z + math.sin(b) * 0.44))
        mb.sphere(p, rnd.uniform(0.04, 0.07), "mane", weights=W("body"), segments=5, rings=3)
    for name, sx in (("FL", 1), ("FR", -1)):
        upper, lower = f"leg_{name}_u", f"leg_{name}_l"
        hip, knee, foot = Vector((sx * 0.42, -0.42, z - 0.12)), Vector((sx * 0.58, -0.5, 0.3)), Vector((sx * 0.5, -0.66, 0.05))
        seg(mb, hip, knee, 0.13, 0.09, "coat", upper)
        seg(mb, knee, foot, 0.085, 0.06, "coat", lower)
        for a in (-0.5, 0.0, 0.5):
            cone(mb, foot, (foot.x + math.sin(a) * 0.2 + sx * 0.05, foot.y - math.cos(a) * 0.22, 0.0), 0.05, "belly",
                 lower)
        bones += [(upper, tuple(hip), tuple(knee), "body"), (lower, tuple(knee), tuple(foot), upper)]
    for name, sx in (("HL", 1), ("HR", -1)):
        upper, lower = f"leg_{name}_u", f"leg_{name}_l"
        hip, knee, foot = Vector((sx * 0.44, 0.52, z - 0.1)), Vector((sx * 0.74, 0.1, 0.42)), Vector((sx * 0.66, 0.62, 0.07))
        lump(mb, hip.lerp(knee, 0.5), (0.2, 0.36, 0.24), "coat", upper, 9 + sx, 14)
        seg(mb, knee, foot, 0.12, 0.08, "coat", lower)
        hull(mb, [(foot.x - 0.1, foot.y + 0.1, 0.0), (foot.x + 0.1, foot.y + 0.1, 0.0), (foot.x - 0.2, foot.y - 0.5, 0.0),
                  (foot.x + 0.2, foot.y - 0.5, 0.0), (foot.x, foot.y, 0.12), (foot.x, foot.y - 0.4, 0.05)], "belly", lower)
        bones += [(upper, tuple(hip), tuple(knee), "body"), (lower, tuple(knee), tuple(foot), upper)]
    return bones


# ------------------------------------------------------------------ riders

RACES = dict(
    human=dict(s=1.0, b=1.0), elf=dict(s=1.0, b=0.9), dwarf=dict(s=0.76, b=1.35), orc=dict(s=1.14, b=1.35),
    catfolk=dict(s=0.93, b=0.9), foxfolk=dict(s=0.92, b=0.9), frogfolk=dict(s=0.88, b=1.0),
    lizardfolk=dict(s=0.97, b=1.0),
)


def rider_head(mb, c, s, race, o):
    bone = "r_head"

    def P(x, y, z):
        return c + Vector((x, y, z)) * s

    if race in ("human", "elf", "dwarf", "orc"):
        wide = 1.18 if race == "orc" else 1.1 if race == "dwarf" else 1.0
        hull(mb, [P(x * wide, y, z) for x, y, z in sym(HEAD_POINTS + JAW_POINTS)], "skin", bone)
        for sx in (-1, 1):
            mb.sphere(P(sx * 0.036 * wide, -0.097, 0.004), 0.014 * s, "eye", weights=W(bone), segments=5, rings=3,
                      scale=(1.2, 0.5, 0.8))
            if race == "elf":
                cone(mb, P(sx * 0.085, 0.01, -0.01), P(sx * 0.16, 0.08, 0.1), 0.03 * s, "skin", bone)
            if race == "orc":
                cone(mb, P(sx * 0.05, -0.1, -0.085), P(sx * 0.058, -0.125, -0.02), 0.016 * s, "horn", bone)
        hull(mb, [P(0, -0.1, 0.014), P(0.016, -0.097, -0.036), P(-0.016, -0.097, -0.036), P(0, -0.13, -0.03)], "skin", bone)
        cap = o.get("helmet") or "hair"
        dome = [(0.0, -0.11, 0.07), (0.078, -0.1, 0.058), (0.108, -0.035, 0.045), (0.108, 0.05, 0.012),
                (0.075, 0.128, -0.06), (0.0, 0.145, -0.06), (0.0, -0.035, 0.158), (0.064, 0.02, 0.142),
                (0.0, 0.088, 0.14), (0.088, -0.04, 0.11)]
        hull(mb, [P(x * wide, y, z) for x, y, z in sym(dome)], cap, bone)
        if o.get("helmet"):
            if o.get("plume"):
                F.tube(mb, [P(0, -0.06, 0.16), P(0, 0.0, 0.26), P(0, 0.13, 0.25), P(0, 0.24, 0.1), P(0, 0.27, -0.05)],
                       [0.02 * s, 0.045 * s, 0.055 * s, 0.045 * s, 0.0], o["plume"], sides=5, flat=0.5)
            hull(mb, [P(x, y, z) for x, y, z in sym([(0.1, -0.07, 0.05), (0.106, 0.03, 0.03), (0.092, -0.085, -0.09),
                                                     (0.1, 0.0, -0.1)])][:8:2], cap, bone)
            hull(mb, [P(x, y, z) for x, y, z in sym([(0.1, -0.07, 0.05), (0.106, 0.03, 0.03), (0.092, -0.085, -0.09),
                                                     (0.1, 0.0, -0.1)])][1:8:2], cap, bone)
            slab(mb, tuple(P(-0.014, -0.125, -0.04)), tuple(P(0.014, -0.112, 0.07)), cap, bone)
        if race == "dwarf":
            hull(mb, [P(x, y, z) for x, y, z in sym([(0.085, -0.08, -0.05), (0.0, -0.118, -0.055), (0.09, -0.05, -0.16),
                                                     (0.05, -0.09, -0.3), (0.0, -0.11, -0.36), (0.085, -0.01, -0.08)])],
                 "hair", bone)
            for sx in (-1, 1):
                cone(mb, P(sx * 0.1, 0.0, 0.1), P(sx * 0.22, 0.0, 0.24), 0.035 * s, "horn", bone)
        if race == "elf" or o.get("long_hair"):
            hull(mb, [P(x, y, z) for x, y, z in sym([(0.1, 0.03, 0.03), (0.108, 0.06, -0.1), (0.1, 0.1, -0.26),
                                                     (0.0, 0.145, -0.3), (0.0, 0.15, 0.0), (0.07, 0.135, 0.05)])],
                 "hair", bone)
        if race == "orc":
            lump(mb, P(0, 0.04, 0.17), (0.05 * s, 0.06 * s, 0.05 * s), "hair", bone, 3, 8, tones=False)
        if o.get("beard") and race == "human":
            hull(mb, [P(x, y, z) for x, y, z in sym([(0.062, -0.086, -0.056), (0.0, -0.113, -0.06), (0.07, -0.06, -0.12),
                                                     (0.0, -0.1, -0.21), (0.075, -0.02, -0.07)])], "hair", bone)
    elif race in ("catfolk", "foxfolk"):
        lump(mb, P(0, 0, 0.0), (0.14 * s, 0.13 * s, 0.115 * s), "skin", bone, 3, 16)
        long = 0.2 if race == "foxfolk" else 0.09
        hull(mb, [P(x, y, z) for x, y, z in sym([(0.06, -0.1, -0.005), (0.06, -0.1, -0.075), (0.03, -0.1 - long, -0.035),
                                                 (0.03, -0.1 - long, -0.07), (0.0, -0.1, 0.01)])], "pale", bone)
        cone(mb, P(0, -0.1 - long, -0.035), P(0, -0.125 - long, -0.035), 0.03 * s, "eye", bone)
        tall = 0.2 if race == "foxfolk" else 0.15
        for sx in (-1, 1):
            hull(mb, [P(sx * 0.03, -0.02, 0.09), P(sx * 0.135, -0.01, 0.045), P(sx * 0.08, 0.06, 0.07),
                      P(sx * 0.125, 0.0, 0.07 + tall)], "skin", bone)
            mb.sphere(P(sx * 0.062, -0.118, 0.03), 0.022 * s, "iris", weights=W(bone), segments=5, rings=3,
                      scale=(1.2, 0.5, 0.9))
            cone(mb, P(sx * 0.115, -0.03, -0.04), P(sx * 0.2, 0.02, -0.09), 0.04 * s, "skin" if race == "catfolk" else "pale",
                 bone)
    elif race == "frogfolk":
        hull(mb, [P(x, y, z) for x, y, z in sym([(0.17, 0.0, 0.0), (0.15, -0.1, 0.0), (0.07, -0.19, 0.0), (0.12, 0.08, 0.06),
                                                 (0.08, -0.08, 0.09), (0.0, -0.2, 0.03), (0.0, 0.12, 0.05)])], "skin", bone)
        hull(mb, [P(x, y, z) for x, y, z in sym([(0.165, 0.0, -0.01), (0.145, -0.1, -0.01), (0.065, -0.185, -0.01),
                                                 (0.11, 0.06, -0.1), (0.07, -0.1, -0.09), (0.0, -0.19, -0.01),
                                                 (0.0, 0.1, -0.1)])], "pale", bone)
        for sx in (-1, 1):
            lump(mb, P(sx * 0.095, -0.03, 0.1), (0.06 * s, 0.06 * s, 0.06 * s), "skin", bone, 5 + sx, 10, tones=False)
            mb.sphere(P(sx * 0.105, -0.07, 0.11), 0.03 * s, "iris", weights=W(bone), segments=5, rings=3)
            mb.sphere(P(sx * 0.11, -0.092, 0.112), 0.014 * s, "eye", weights=W(bone), segments=4, rings=3)
    else:   # Lizardfolk.
        lump(mb, P(0, 0.0, 0.0), (0.105 * s, 0.13 * s, 0.11 * s), "skin", bone, 3, 14)
        hull(mb, [P(x, y, z) for x, y, z in sym([(0.08, -0.08, 0.03), (0.075, -0.08, -0.07), (0.045, -0.3, -0.01),
                                                 (0.04, -0.3, -0.07), (0.0, -0.1, 0.06), (0.0, -0.31, 0.0)])], "skin", bone)
        hull(mb, [P(x, y, z) for x, y, z in sym([(0.07, -0.06, -0.07), (0.04, -0.29, -0.07), (0.05, -0.06, -0.11),
                                                 (0.0, -0.28, -0.085)])], "pale", bone)
        for sx in (-1, 1):
            mb.sphere(P(sx * 0.075, -0.1, 0.035), 0.02 * s, "iris", weights=W(bone), segments=5, rings=3)
        for i in range(5):
            cone(mb, P(0, -0.04 + 0.045 * i, 0.1 - 0.012 * i), P(0, 0.02 + 0.06 * i, 0.22 - 0.03 * i), 0.05 * s, "hair",
                 bone)


def rider(mb, m, race="human", **o):
    """A rider in the saddle of mount m. Options: helmet (material), plume,
    armor (material of a breastplate), cape (material), weapon (lance,
    sword, spear, axe, bow, staff, banner, horn), shield (material), beard,
    long_hair, tail. Returns the rider's bones."""
    r = RACES[race]
    s, b = r["s"], r["b"]
    S = Vector(m["seat"])
    w = m["w"]

    def P(x, y, z):
        return S + Vector((x * b, y, z)) * s

    bones = [("r_hips", tuple(S), tuple(P(0, 0, 0.22)), "body"),
             ("r_chest", tuple(P(0, 0, 0.22)), tuple(P(0, 0, 0.6)), "r_hips"),
             ("r_head", tuple(P(0, 0, 0.62)), tuple(P(0, 0, 0.9)), "r_chest")]
    lump(mb, P(0, 0.0, 0.11), (0.17 * s * b, 0.14 * s * b, 0.14 * s), "bottom", "r_hips", 61, 12)
    lump(mb, P(0, -0.01, 0.42), (0.2 * s * b, 0.135 * s * b, 0.21 * s), "top", "r_chest", 62, 18)
    seg(mb, P(0, 0, 0.56), P(0, -0.01, 0.68), 0.055 * s * b, 0.05 * s * b, "skin", "r_chest")
    slab(mb, tuple(P(-0.165, -0.135 * b, 0.19)), tuple(P(0.165, 0.135 * b, 0.25)), "leather", "r_hips")
    if o.get("armor"):
        hull(mb, [P(x, y, z) for x, y, z in sym([(0.12, -0.12 * b, 0.6), (0.0, -0.15 * b, 0.6), (0.19, -0.03, 0.54),
                                                 (0.0, -0.185 * b, 0.47), (0.16, -0.1 * b, 0.32), (0.0, -0.16 * b, 0.28),
                                                 (0.13, 0.12 * b, 0.6), (0.18, 0.05, 0.54), (0.15, 0.11 * b, 0.3),
                                                 (0.0, 0.145 * b, 0.46)])], o["armor"], "r_chest")
        for sx in (-1, 1):
            hull(mb, [P(sx * x, y, z) for x, y, z in ((0.14, 0.08, 0.66), (0.14, -0.08, 0.66), (0.21, 0.0, 0.7),
                                                      (0.28, 0.1, 0.56), (0.28, -0.1, 0.56), (0.31, 0.0, 0.52))],
                 o["armor"] + "_shade", "r_chest")
    if o.get("tabard"):
        plate(mb, [P(-0.1, -0.2 * b, 0.56), P(0.1, -0.2 * b, 0.56), P(0.12, -0.17 * b, 0.22), P(-0.12, -0.17 * b, 0.22)],
              0.02 * s, o["tabard"], "r_chest")
    rider_head(mb, P(0, -0.02, 0.775) if race != "dwarf" else P(0, -0.02, 0.8), s * (1.25 if race == "dwarf" else 1.0),
               race, o)
    forward = m.get("sit") == "forward"     # On a mount too wide to straddle: the legs lie forward on its back.
    straddle = 0.24 * s if forward else max(w + 0.07, 0.2 * s)
    for name, sx in (("L", 1), ("R", -1)):
        knee = Vector((sx * straddle, S.y - 0.3 * s, S.z - (0.0 if forward else 0.1) * s))
        foot = Vector((sx * (straddle + 0.03), S.y - (0.62 if forward else 0.2) * s, S.z - (0.1 if forward else 0.56) * s))
        seg(mb, P(sx * 0.1, 0.0, 0.09), knee, 0.092 * s * b, 0.07 * s * b, "bottom", "r_hips")
        seg(mb, knee, foot, 0.068 * s * b, 0.052 * s * b, "boots", "r_hips")
        mb.sphere(knee, 0.072 * s * b, "bottom", weights=W("r_hips"), segments=6, rings=4)
        hull(mb, [foot + Vector(p) * s for p in ((-0.05, 0.07, -0.07), (0.05, 0.07, -0.07), (-0.05, -0.17, -0.07),
                                                 (0.05, -0.17, -0.07), (-0.045, 0.06, 0.03), (0.045, 0.06, 0.03),
                                                 (0.0, -0.15, -0.01))], "boots", "r_hips")
        shoulder, elbow = P(sx * 0.215, 0.0, 0.55), P(sx * 0.27, -0.03, 0.29)
        hand = P(sx * 0.2, -0.3, 0.27)
        upper, lower = f"r_arm_{name}_u", f"r_arm_{name}_l"
        lump(mb, shoulder, (0.075 * s * b, 0.075 * s * b, 0.075 * s), "top", upper, 70 + sx, 8, tones=False)
        seg(mb, shoulder, elbow, 0.06 * s * b, 0.05 * s * b, "top", upper)
        seg(mb, elbow, hand, 0.05 * s * b, 0.042 * s * b, o.get("sleeve", "top"), lower)
        lump(mb, hand, (0.045 * s * b, 0.055 * s * b, 0.05 * s), o.get("glove", "skin"), lower, 72 + sx, 8, tones=False)
        bones += [(upper, tuple(shoulder), tuple(elbow), "r_chest"), (lower, tuple(elbow), tuple(hand), upper)]
        if sx == -1 and o.get("weapon"):
            weapon(mb, o["weapon"], hand, s, lower)
        if sx == 1 and o.get("shield"):
            c = elbow.lerp(hand, 0.5) + Vector((0.09 * s, 0, 0.04 * s))
            pts = []
            for y, z in ((-0.2, 0.28), (0.2, 0.28), (-0.21, 0.04), (0.21, 0.04), (0.0, -0.38), (0.0, 0.32)):
                pts += [c + Vector((0.0, y, z)) * s, c + Vector((0.04, y * 0.94, z * 0.94)) * s]
            hull(mb, pts + [c + Vector((0.075, 0, 0.04)) * s], o["shield"], lower)
            mb.box(c + Vector((0.06, 0, 0.06)) * s, (0.03 * s, 0.07 * s, 0.36 * s), "gold", weights=W(lower))
            mb.box(c + Vector((0.06, 0, 0.12)) * s, (0.03 * s, 0.28 * s, 0.07 * s), "gold", weights=W(lower))
        if sx == 1 and o.get("weapon") == "bow":
            pts = [(0.0, -0.66), (-0.06, -0.44), (-0.12, -0.2), (-0.14, 0.0), (-0.12, 0.2), (-0.06, 0.44), (0.0, 0.66)]
            F.tube(mb, [hand + Vector((0, y, z + 0.05)) * s for y, z in pts], [0.01 * s, 0.014 * s, 0.017 * s, 0.02 * s,
                                                                             0.017 * s, 0.014 * s, 0.01 * s], "wood", sides=4)
            bind(mb, [v for v in mb.bm.verts if not v[mb.deform]], lower)
            seg(mb, hand + Vector((0, 0, -0.61)) * s, hand + Vector((0, 0, 0.71)) * s, 0.004, 0.004, "pale", lower, sides=3)
    if o.get("cape"):
        rows = []
        for z, half, y in ((0.6, 0.18, 0.13), (0.36, 0.25, 0.2), (0.1, 0.31, 0.3), (-0.14, 0.35, 0.42)):
            rows.append([P((i / 2.0 - 1.0) * half, y * b + (0.04 if i % 2 else 0.0), z) for i in range(5)])
        bind(mb, F.sheet(mb, rows, 0.018 * s, o["cape"]), "r_cape")
        bones.append(("r_cape", tuple(P(0, 0.13, 0.6)), tuple(P(0, 0.42, -0.14)), "r_chest"))
    if o.get("tail"):
        pts = [P(0, 0.12, 0.08), P(0.06, 0.3, 0.12), P(0.12, 0.46, 0.3), P(0.1, 0.52, 0.5)]
        fat = 2.2 if race == "foxfolk" else 1.6 if race == "lizardfolk" else 1.0
        F.tube(mb, pts, [0.05 * s * fat, 0.055 * s * fat, 0.045 * s * fat, 0.0], "skin", sides=5)
        bind(mb, [v for v in mb.bm.verts if not v[mb.deform]], "r_tail")
        if race == "foxfolk":
            cone(mb, pts[2].lerp(pts[3], 0.3), pts[3] + Vector((0, 0.02, 0.06)), 0.1 * s, "pale", "r_tail", sides=5)
        bones.append(("r_tail", tuple(pts[0]), tuple(pts[3]), "r_hips"))
    if o.get("quiver"):
        a, e = P(-0.12, 0.17 * b, 0.25), P(0.12, 0.18 * b, 0.68)
        seg(mb, a, e, 0.05 * s, 0.06 * s, "leather", "r_chest")
        for dx in (-0.02, 0.02):
            cone(mb, e + Vector((dx, 0, 0.06)), e + Vector((dx * 2, 0.02, 0.2)), 0.035 * s, "pale", "r_chest")
    if o.get("satchel"):
        mb.box(P(-0.2, 0.08, 0.16), (0.1 * s, 0.26 * s, 0.22 * s), "leather", weights=W("r_hips"))
        plate(mb, [P(0.12, -0.15 * b, 0.6), P(0.16, -0.15 * b, 0.58), P(-0.14, -0.16 * b, 0.24), P(-0.18, -0.16 * b, 0.26)],
              0.016 * s, "leather", "r_chest")
    return bones


def weapon(mb, kind, hand, s, bone):
    def P(x, y, z):
        return hand + Vector((x, y, z)) * s
    if kind in ("lance", "spear", "banner", "staff"):
        top = {"lance": 2.3, "spear": 1.5, "banner": 2.0, "staff": 1.2}[kind]
        seg(mb, P(0, 0, -0.7), P(0, 0, top), 0.022 * s, 0.018 * s, "wood", bone, sides=5)
        if kind == "staff":
            mb.cylinder(P(0, 0, top), P(0, 0, top + 0.1), 0.0, 0.07 * s, "glow", weights=W(bone), segments=5)
            mb.cylinder(P(0, 0, top + 0.1), P(0, 0, top + 0.3), 0.07 * s, 0.0, "glow", weights=W(bone), segments=5)
        else:
            hull(mb, [P(0.045, 0, top + 0.05), P(-0.045, 0, top + 0.05), P(0, 0.014, top), P(0, -0.014, top),
                      P(0, 0, top + 0.32)], "metal", bone)
        if kind in ("lance", "banner"):
            long = 0.36 if kind == "lance" else 0.6
            plate(mb, [P(0, 0.02, top - 0.04), P(0, 0.02, top - 0.04 - long * 0.7), P(0, 0.02 + long * 0.75, top - long * 0.5),
                       P(0, 0.02 + long, top - 0.1)], 0.016, "accent", bone)
        if kind == "lance":
            mb.cylinder(P(0, 0, 0.06), P(0, 0, 0.2), 0.09 * s, 0.02 * s, "metal", weights=W(bone), segments=6)
    elif kind == "sword":
        seg(mb, P(0, 0, -0.07), P(0, 0, 0.08), 0.018 * s, 0.018 * s, "leather", bone, sides=5)
        slab(mb, tuple(P(-0.1, -0.018, 0.08)), tuple(P(0.1, 0.018, 0.11)), "gold", bone)
        hull(mb, [P(0.035, 0, 0.11), P(-0.035, 0, 0.11), P(0.03, 0, 0.82), P(-0.03, 0, 0.82), P(0, 0, 0.94),
                  P(0, 0.01, 0.11), P(0, -0.01, 0.11), P(0, 0.008, 0.82), P(0, -0.008, 0.82)], "metal", bone)
    elif kind == "axe":
        seg(mb, P(0, 0, -0.3), P(0, 0, 0.8), 0.024 * s, 0.022 * s, "wood", bone, sides=5)
        for sy in (-1, 1):
            hull(mb, [P(0.014, sy * 0.02, 0.56), P(-0.014, sy * 0.02, 0.56), P(0.014, sy * 0.02, 0.76),
                      P(-0.014, sy * 0.02, 0.76), P(0, sy * 0.24, 0.46), P(0, sy * 0.24, 0.86)], "metal", bone)
    elif kind == "horn":
        F.tube(mb, [P(0, -0.02, 0.0), P(0, -0.06, 0.12), P(0, -0.16, 0.22), P(0, -0.3, 0.27)],
               [0.014 * s, 0.022 * s, 0.035 * s, 0.06 * s], "horn", sides=6)
        bind(mb, [v for v in mb.bm.verts if not v[mb.deform]], bone)


# ------------------------------------------------------------------- clips

def colors(**hexes):
    base = dict(coat=0x7A4E2E, belly=0xD8C8A8, mane=0x2A2018, muzzle=0x4A342A, hoof=0x2E2A28, eye=0x101010,
                horn=0xE6DCC8, leather=0x70432B, leather_dark=0x4E2E1E, metal=0x9A9EAE, gold=0xE2B13C, accent=0xB8382E,
                wood=0x8A6038, sack=0xD8CCA8, beak=0xE0A030, iris=0xF2D23A, pale=0xF0E6D8, glow=0x6AE0FF,
                skin=0xF0B284, hair=0x4A302C, top=0x6A6A72, bottom=0x3E3A44, boots=0x4A3020)
    base.update(hexes)
    return F.shaded(base)


def finish(mb, name, m, bones, palette, kind="quad", armed=False):
    """Adds the clips and saves. kind: quad, bird or toad."""
    mech = kit.Mech(bones)
    names = {b[0] for b in bones}
    has = names.__contains__
    sprawl = m.get("sprawl", 0.0)

    def rider_pose(turns, g, lean, bounce, cape):
        if not has("r_hips"):
            return
        turns["r_hips"] = [(X, lean * 0.4)]
        turns["r_chest"] = [(X, lean * 0.6 + bounce * math.sin(2 * TAU * g + 0.8))]
        turns["r_head"] = [(X, -lean * 0.7 - bounce * 0.5 * math.sin(2 * TAU * g + 0.8))]
        for side in ("L", "R"):
            turns[f"r_arm_{side}_u"] = [(X, -lean * 0.5 + bounce * math.sin(2 * TAU * g))]
        if has("r_cape"):
            turns["r_cape"] = [(X, cape + cape * 0.25 * math.sin(2 * TAU * g))]
        if has("r_tail"):
            turns["r_tail"] = [(Z, 10.0 * math.sin(TAU * g))]

    def legs(turns, g, swing, bend, phases):
        for leg, phase in phases.items():
            th = TAU * (g + phase)
            upper, lower = f"leg_{leg}_u", f"leg_{leg}_l"
            if sprawl:
                sx = 1.0 if leg.endswith("L") else -1.0
                turns[upper] = [(Z, sx * swing * math.sin(th)), (Y, -sx * bend * max(0.0, -math.cos(th)))]
            else:
                turns[upper] = [(X, swing * math.sin(th))]
                turns[lower] = [(X, bend * max(0.0, -math.cos(th)))]

    def quad_gait(swing, bend, phases, bob, pitch, lean, cape):
        def pose(g):
            turns, moves = {}, {}
            legs(turns, g, swing, bend, phases)
            moves["body"] = (0, 0, bob * math.sin(2 * TAU * g) - bob)
            turns["body"] = [(X, pitch * math.sin(TAU * g + 0.6))] + \
                ([(Z, 6.0 * math.sin(TAU * g))] if sprawl else [])
            turns["neck"] = [(X, 5.0 * math.sin(2 * TAU * g) - pitch * 0.5 * math.sin(TAU * g + 0.6) + pitch * 1.5)]
            turns["head"] = [(X, -3.0 * math.sin(2 * TAU * g))]
            turns["tail"] = [(Z, (16.0 if sprawl else 9.0) * math.sin(TAU * g + 1.0)), (X, pitch * 4.0)]
            for wing in ("wing_L", "wing_R"):
                if has(wing):
                    sx = 1.0 if wing.endswith("L") else -1.0
                    turns[wing] = [(Y, -sx * (pitch * 4.0 + pitch * 3.0 * math.sin(2 * TAU * g)))]
            rider_pose(turns, g, lean, 2.0 + pitch, cape)
            return turns, moves
        return pose

    def idle(t):
        turns = {"neck": [(X, 4.0 * math.sin(TAU * t))], "head": [(X, 5.0 * math.sin(TAU * t + 1.0)),
                                                                   (Z, 6.0 * math.sin(TAU * t * 2))],
                 "tail": [(Z, 18.0 * math.sin(TAU * 2 * t)), (X, 4.0 * math.sin(TAU * t))]}
        moves = {"body": (0, 0, 0.008 * math.sin(TAU * 2 * t))}
        if has("r_hips"):
            turns["r_chest"] = [(X, 1.5 * math.sin(TAU * 2 * t))]
            turns["r_head"] = [(Z, 14.0 * math.sin(TAU * t)), (X, -1.5 * math.sin(TAU * 2 * t))]
            if has("r_cape"):
                turns["r_cape"] = [(X, 3.0 * math.sin(TAU * t))]
            if has("r_tail"):
                turns["r_tail"] = [(Z, 14.0 * math.sin(TAU * t))]
        if kind == "toad":   # The throat swells.
            moves["head"] = (0, 0, 0.012 * math.sin(TAU * 3 * t))
        return turns, moves

    def hop(height, reach):
        def pose(g):
            air = F.pulse(g, 0.15, 0.35, 0.55, 0.8)
            crouch = F.pulse(g, 0.0, 0.12, 0.14, 0.3) + F.pulse(g, 0.72, 0.85, 0.9, 1.0)
            turns = {"body": [(X, -16.0 * F.pulse(g, 0.1, 0.3, 0.35, 0.6) + 10.0 * F.pulse(g, 0.55, 0.75, 0.8, 0.95))]}
            moves = {"body": (0, 0, height * air - 0.06 * crouch)}
            for side in ("L", "R"):
                turns[f"leg_H{side}_u"] = [(X, 50.0 * air)]
                turns[f"leg_H{side}_l"] = [(X, 40.0 * air)]
                turns[f"leg_F{side}_u"] = [(X, -reach * air + 10.0 * crouch)]
            rider_pose(turns, g, 8.0 + 14.0 * air, 3.0, 20.0 * air)
            return turns, moves
        return pose

    def attack(t):
        turns, moves = idle(0.0)
        w = F.pulse(t, 0.0, 0.35, 0.45, 0.6)
        hit = F.pulse(t, 0.45, 0.6, 0.65, 1.0)
        turns["r_chest"] = [(Z, -18.0 * w + 22.0 * hit), (X, 12.0 * hit)]
        turns["r_arm_R_u"] = [(X, -120.0 * w - 40.0 * hit)]
        turns["r_arm_R_l"] = [(X, -30.0 * w + 50.0 * hit)]
        turns["neck"] = [(X, 8.0 * hit)]
        return turns, moves

    mech.clip("idle", 3.0, idle)
    if kind == "toad":
        mech.clip("walk", m["cycle"], hop(0.22, 30.0), speed=0.9 / m["cycle"])
        mech.clip("gallop", m["gcycle"], hop(0.75, 55.0), speed=2.8 / m["gcycle"])
    else:
        walk = {"L": 0.0, "R": 0.5} if kind == "bird" else WALK4
        gallop = {"L": 0.0, "R": 0.5} if kind == "bird" else GALLOP4
        leg = m["hip"] * (0.55 if sprawl else 1.0)
        mech.clip("walk", m["cycle"], quad_gait(m["swing"], m["bend"], walk, 0.02, 0.0, 2.0, 4.0),
                  speed=4 * leg * math.sin(math.radians(m["swing"])) / m["cycle"])
        mech.clip("gallop", m["gcycle"], quad_gait(m["gswing"], m["bend"] * 1.5, gallop, 0.06, 5.0, 16.0, 38.0),
                  speed=5.5 * leg * math.sin(math.radians(m["gswing"])) / m["gcycle"])
    if armed:
        mech.clip("attack", 1.0, attack)
    kit.save(mb, F.FAMILY, name, palette, mech=mech)


def mounted(name, mount, palette, race=None, trims=(), saddle_opts=None, **rider_opts):
    """A function that builds a mount (see MOUNTS, "bird" or "toad") with
    its trimmings and saddle and, with `race`, its rider."""
    def make():
        mb = kit.begin()
        if mount == "bird":
            m, kind = BIRD, "bird"
            bones = bird(mb, m)
        elif mount == "toad":
            m, kind = TOAD, "toad"
            bones = toad(mb, m)
        else:
            m, kind = MOUNTS[mount], "quad"
            bones, frame = quadruped(mb, m, belly="belly" if mount in ("lizard", "cat", "wolf") else None)
            TRIMS[mount](mb, m, frame)
            for trim in trims:
                trim(mb, m, frame)
            bridle(mb, frame, m)
        saddle(mb, m, **(saddle_opts or {}))
        if race:
            bones += rider(mb, m, race, **rider_opts)
        finish(mb, name, m, bones, colors(**palette), kind, armed=bool(race and rider_opts.get("weapon")
                                                                     and rider_opts["weapon"] not in ("bow", "horn", "banner", "staff")))
    return make


# ------------------------------------------------------------------ models

WAR_HORSE = dict(coat=0x3E3A3A, mane=0x1E1A1A, accent=0x2E5AA8)
HORSE = dict(coat=0x8A5A32, mane=0x2A2018, accent=0x3E7A4A)
MULE = dict(coat=0x8A8478, mane=0x3A3632, muzzle=0xD8D0C0, accent=0x8A2E6A)
WOLF = dict(coat=0x6A6A72, belly=0xB8B4AC, mane=0x4A4A52, accent=0x7A2A2A, leather=0x4A3A32)
RAM = dict(coat=0x5A4A3E, mane=0xE8E0D0, horn=0xC8B890, accent=0x2E5AA8)
BOAR = dict(coat=0x5A4636, mane=0x2E2420, muzzle=0xC89A8A, accent=0x8A2E2A)
ELK = dict(coat=0xA87A4A, mane=0xE0D0B0, muzzle=0x3A2A22, accent=0x3E8A5A, horn=0xE8DCC0)
CAT = dict(coat=0x3A3A4A, belly=0x8A8A9A, muzzle=0xD08A8A, accent=0x3F68D6, iris=0xE8D23E)
SABRE = dict(coat=0xC8964A, belly=0xF0E0C0, muzzle=0x5A3A2A, accent=0x3F68D6)
LIZARD = dict(coat=0x5A8A3A, belly=0xE8D08A, mane=0x2F5753, accent=0xB3383C, horn=0xE8DCC0, iris=0xF2D23A)
BIRDC = dict(coat=0xE8C23A, belly=0xF4E8B0, mane=0xC8802A, accent=0xD8482E, beak=0xE08A2A)
TOADC = dict(coat=0x6A8A3A, belly=0xE0D8A0, mane=0x4E6A2A, accent=0x2C66B6, iris=0xF2A020)

MODELS = {
    # --- The mounts alone, saddled.
    "folk_mount_war_horse": mounted("folk_mount_war_horse", "horse", WAR_HORSE, trims=(trim_barding,)),
    "folk_mount_horse": mounted("folk_mount_horse", "horse", HORSE, saddle_opts=dict(bags=True)),
    "folk_mount_horse_white": mounted("folk_mount_horse_white", "horse",
                                      dict(coat=0xE8E4DC, mane=0xC8C0B0, muzzle=0xD8A8A0, accent=0xB8382E)),
    "folk_mount_mule": mounted("folk_mount_mule", "mule", MULE, saddle_opts=dict(pack=True)),
    "folk_mount_dire_wolf": mounted("folk_mount_dire_wolf", "wolf", WOLF),
    "folk_mount_ram": mounted("folk_mount_ram", "ram", RAM),
    "folk_mount_boar": mounted("folk_mount_boar", "boar", BOAR),
    "folk_mount_elk": mounted("folk_mount_elk", "elk", ELK),
    "folk_mount_great_cat": mounted("folk_mount_great_cat", "cat", CAT),
    "folk_mount_sabre_cat": mounted("folk_mount_sabre_cat", "cat", SABRE),
    "folk_mount_giant_lizard": mounted("folk_mount_giant_lizard", "lizard", LIZARD),
    "folk_mount_giant_bird": mounted("folk_mount_giant_bird", "bird", BIRDC),
    "folk_mount_giant_toad": mounted("folk_mount_giant_toad", "toad", TOADC),
    # --- Riders.
    "folk_rider_knight": mounted(
        "folk_rider_knight", "horse", dict(WAR_HORSE, top=0x8A8E9E, bottom=0x5A5E6E, boots=0x5A5E6E, steel=0xB4B8C8),
        race="human", trims=(trim_barding,), helmet="steel", plume="accent", armor="steel", cape="accent",
        weapon="lance", shield="accent", glove="steel", sleeve="steel"),
    "folk_rider_knight_red": mounted(
        "folk_rider_knight_red", "horse",
        dict(coat=0xE8E4DC, mane=0xC8C0B0, muzzle=0xD8A8A0, accent=0xB8382E, top=0x8A8E9E, bottom=0x5A5E6E,
             boots=0x5A5E6E, steel=0xB4B8C8),
        race="human", trims=(trim_barding,), helmet="steel", plume="accent", armor="steel", cape="accent",
        weapon="sword", shield="accent", glove="steel", sleeve="steel"),
    "folk_rider_messenger": mounted(
        "folk_rider_messenger", "horse", dict(HORSE, top=0x3E7A4A, bottom=0x5A4632, hair=0xA84A22, cape=0x2E5A3A),
        race="human", saddle_opts=dict(bags=True), cape="cape", weapon="horn", satchel=True, long_hair=True),
    "folk_rider_standard": mounted(
        "folk_rider_standard", "horse", dict(HORSE, coat=0x5A3A22, accent=0x2E5AA8, top=0x2E5AA8, bottom=0x3E3A44,
                                              steel=0x9A9EAE),
        race="human", helmet="steel", armor="steel", weapon="banner", beard=True),
    "folk_rider_merchant": mounted(
        "folk_rider_merchant", "mule", dict(MULE, top=0x7A3A8A, bottom=0x4A2A6A, hair=0x2A2220, hat=0x4A2A6A),
        race="human", saddle_opts=dict(pack=True), helmet="hat", plume="gold", beard=True, weapon="staff",
        satchel=True),
    "folk_rider_orc_wolf": mounted(
        "folk_rider_orc_wolf", "wolf", dict(WOLF, skin=0x8FAE38, hair=0x2A2220, top=0x8FAE38, bottom=0x5E3F36,
                                            boots=0x6B4534, steel=0x5A5A66),
        race="orc", weapon="axe", armor="leather", sleeve="skin"),
    "folk_rider_dwarf_ram": mounted(
        "folk_rider_dwarf_ram", "ram", dict(RAM, skin=0xE8A57C, hair=0xC8642A, top=0x2E5AA8, bottom=0x443C3A,
                                            steel=0x9A9AA2),
        race="dwarf", helmet="steel", armor="steel", weapon="axe", tabard=None),
    "folk_rider_dwarf_boar": mounted(
        "folk_rider_dwarf_boar", "boar", dict(BOAR, skin=0xE8A57C, hair=0x4A302C, top=0x8E3B2C, bottom=0x443C3A,
                                              steel=0x9A9AA2),
        race="dwarf", helmet="steel", weapon="spear", shield="accent"),
    "folk_rider_elf_elk": mounted(
        "folk_rider_elf_elk", "elk", dict(ELK, skin=0xF4B588, hair=0xEBBE6C, top=0x3E8A5A, bottom=0x2B1D27,
                                          cape=0x2E6A44),
        race="elf", weapon="bow", cape="cape", quiver=True),
    "folk_rider_dark_elf_cat": mounted(
        "folk_rider_dark_elf_cat", "cat", dict(CAT, skin=0xB587D8, hair=0xDCD2E2, top=0x4E3672, bottom=0x2A1D40,
                                               cape=0x3B3145, accent=0x4E3672),
        race="elf", weapon="spear", cape="cape"),
    "folk_rider_lizardfolk_lizard": mounted(
        "folk_rider_lizardfolk_lizard", "lizard", dict(LIZARD, skin=0x6FA63A, pale=0xF0D08A, hair=0x2F5753,
                                                       top=0xB3383C, bottom=0x47404D, boots=0x6FA63A),
        race="lizardfolk", weapon="spear", shield="accent", tail=True, sleeve="skin"),
    "folk_rider_frogfolk_toad": mounted(
        "folk_rider_frogfolk_toad", "toad", dict(TOADC, skin=0x2AB4F4, pale=0xDCDDAA, top=0x2C66B6, bottom=0xEFC89C,
                                                 boots=0x2AB4F4),
        race="frogfolk", weapon="spear", sleeve="skin"),
    "folk_rider_catfolk_cat": mounted(
        "folk_rider_catfolk_cat", "cat", dict(SABRE, skin=0x666D90, pale=0xF0E2DA, top=0x3F68D6, bottom=0x383750,
                                              boots=0x7E4332),
        race="catfolk", weapon="sword", shield="accent", tail=True),
    "folk_rider_foxfolk_bird": mounted(
        "folk_rider_foxfolk_bird", "bird", dict(BIRDC, skin=0xEE8C42, pale=0xF6DDBE, top=0x4F8B88, bottom=0x66764E,
                                                boots=0x7C4432, iris=0x2A2222, cape=0x33696C),
        race="foxfolk", weapon="lance", tail=True, cape="cape"),
}
