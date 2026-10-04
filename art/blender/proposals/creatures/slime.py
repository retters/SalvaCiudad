"""Slime: a wobbling dome of jelly, 1 m wide, with two eyes, a shine and a
few things it swallowed floating on its skin. It has no hard parts: the
dome's vertices blend between a bone at the top, four around the sides and
the root at the base, and the clips squash and stretch it by moving those
bones (no scaling). Clips: idle (wobbles), walk (bounces), attack (lunges
forward) and die (flattens into a puddle). Variants: green, blue (ice) and
red (fire), and a small one."""

import math

from mathutils import Vector

import _parts as P
from _parts import ball, box, seg

SIDES = {"side.F": Vector((0, -1, 0)), "side.B": Vector((0, 1, 0)), "side.L": Vector((1, 0, 0)),
         "side.R": Vector((-1, 0, 0))}


def colors(base, eye=0x1A1A22):
    return {**P.shades("jelly", base, light=0.22, dark=0.18), **P.palette(eye=eye, shine=0xFFFFFF, bone=0xE6DCC2,
                                                                        iron=0x8A8F96)}


def weights_at(p, k):
    """Blend of top, side and root bones for a point of a slime of size k."""
    h = 0.58 * k
    z = max(0.0, min(1.0, p.z / h))
    top = z ** 1.5
    side = (1.0 - top) * math.sin(math.pi * min(1.0, z * 1.15 + 0.12)) * 0.9
    out = {"top": top}
    flat = Vector((p.x, p.y, 0.0))
    if flat.length > 1e-5:
        flat.normalize()
        lobes = {n: max(0.0, flat.dot(d)) ** 2 for n, d in SIDES.items()}
        total = sum(lobes.values())
        for n, w in lobes.items():
            if w > 0:
                out[n] = side * w / total
    out["root"] = max(0.0, 1.0 - sum(out.values()))
    return {n: w for n, w in out.items() if w > 1e-4}


def body(mb, k, crown=False):
    R, h, n = 0.5 * k, 0.58 * k, 10
    profile = [(0.9, 0.0), (1.0, 0.08), (0.97, 0.2), (0.86, 0.34), (0.66, 0.46), (0.36, 0.55)]   # (radius, height).
    rings = []
    for i, (r, z) in enumerate(profile):
        ring = []
        for j in range(n):
            a = math.tau * (j + 0.5 * (i % 2)) / n
            wob = 1.0 + 0.04 * math.sin(3 * a + i)
            ring.append(mb.bm.verts.new((math.cos(a) * r * R * wob, math.sin(a) * r * R * wob, z * k)))
        rings.append(ring)
    top = mb.bm.verts.new((0, 0, h))
    faces = [mb.bm.faces.new(list(reversed(rings[0])))]
    for i, (r0, r1) in enumerate(zip(rings, rings[1:])):
        for j in range(n):
            jj = (j + 1) % n
            if i % 2 == 0:
                faces.append(mb.bm.faces.new((r0[j], r0[jj], r1[j])))
                faces.append(mb.bm.faces.new((r0[jj], r1[jj], r1[j])))
            else:
                faces.append(mb.bm.faces.new((r0[j], r0[jj], r1[jj])))
                faces.append(mb.bm.faces.new((r0[j], r1[jj], r1[j])))
    for j in range(n):
        faces.append(mb.bm.faces.new((rings[-1][j], rings[-1][(j + 1) % n], top)))
    verts = [v for ring in rings for v in ring] + [top]
    mb._finish(verts, "jelly", None)
    import random
    rnd = random.Random(4)
    for f in faces[1:]:
        r = rnd.random()
        f.material_index = mb._material_index("jelly_light" if r < 0.3 else "jelly_shade" if r < 0.55 else "jelly")
    for v in verts:
        P.weigh(mb, [v], weights_at(v.co, k))

    def stuck(new_verts):
        """Binds a small piece to the jelly where it sits."""
        c = sum((v.co for v in new_verts), Vector()) / len(new_verts)
        P.weigh(mb, new_verts, weights_at(c, k))

    if crown:                                                # The king's crown, sunk into the top.
        import math as _m
        stuck(mb.cylinder((0, 0, 0.5 * k), (0, 0, 0.6 * k), 0.17 * k, 0.18 * k, "gold", segments=8))
        for i in range(6):
            a = i * _m.tau / 6
            p = Vector((_m.cos(a) * 0.16 * k, _m.sin(a) * 0.16 * k, 0.6 * k))
            stuck(P.spike(mb, p, p + Vector((_m.cos(a) * 0.03 * k, _m.sin(a) * 0.03 * k, 0.12 * k)), 0.04 * k, "gold"))
    for s in (-1, 1):
        stuck(ball(mb, (s * 0.15 * k, -0.4 * k, 0.3 * k), 0.07 * k, "shine", segments=8, rings=5, scale=(1, 0.5, 1.2)))
        stuck(ball(mb, (s * 0.15 * k, -0.435 * k, 0.29 * k), 0.038 * k, "eye", segments=6, rings=4,
                   scale=(1, 0.5, 1.2)))
    stuck(box(mb, (-0.2 * k, -0.22 * k, 0.47 * k), (0.12 * k, 0.03 * k, 0.05 * k), "shine", rotation_z=0.6))   # Shine.
    stuck(box(mb, (-0.29 * k, -0.14 * k, 0.4 * k), (0.05 * k, 0.03 * k, 0.04 * k), "shine", rotation_z=0.9))
    # Swallowed things poking out: a bone and a sword hilt.
    stuck(seg(mb, (0.26 * k, 0.1 * k, 0.36 * k), (0.42 * k, 0.2 * k, 0.5 * k), 0.022 * k, 0.022 * k, "bone", sides=5))
    stuck(ball(mb, (0.43 * k, 0.21 * k, 0.51 * k), 0.035 * k, "bone"))
    stuck(seg(mb, (-0.1 * k, 0.25 * k, 0.42 * k), (-0.16 * k, 0.4 * k, 0.6 * k), 0.018 * k, 0.018 * k, "iron", sides=4))
    stuck(box(mb, (-0.12 * k, 0.3 * k, 0.48 * k), (0.12 * k, 0.03 * k, 0.03 * k), "iron", rotation_z=0.4))


def mech(k):
    bones = [("top", (0, 0, 0.3 * k), (0, 0, 0.58 * k), None)]
    for name, d in SIDES.items():
        bones.append((name, tuple(d * 0.2 * k + Vector((0, 0, 0.2 * k))), tuple(d * 0.5 * k + Vector((0, 0, 0.2 * k))),
                      None))
    m = P.kit.Mech(bones)

    def shape(squash, lean=(0.0, 0.0), front=0.0, lift=0.0, wobble=0.0):
        """squash > 0 flattens and widens; < 0 stretches up. `lean` moves
        the top (x, y); `front` pushes the front side out."""
        moves = {"top": (lean[0] * k, lean[1] * k, -0.5 * squash * k), "root": (0, 0, lift * k)}
        for name, d in SIDES.items():
            out = 0.36 * squash + wobble * (1 if name in ("side.L", "side.R") else -1)
            v = d * out * k
            if name == "side.F":
                v += Vector((0, -front * k, 0))
            if name == "side.B":
                v += Vector((0, -front * 0.4 * k, 0))
            moves[name] = tuple(v)
        return {}, moves

    def idle(t):
        p = 2 * math.pi * t
        return shape(0.1 * math.sin(2 * p), lean=(0.03 * math.sin(p), 0.02 * math.cos(p)),
                     wobble=0.03 * math.sin(2 * p + 1.0))

    def walk(t):
        squat = P.pulse(t, 0.0, 0.14, 0.18, 0.3)
        u = max(0.0, min(1.0, (t - 0.22) / 0.5))
        air = math.sin(math.pi * u)
        land = P.pulse(t, 0.7, 0.78, 0.8, 1.0)
        return shape(0.5 * squat - 0.4 * air + 0.55 * land, lean=(0, -0.08 * air + 0.04 * squat),
                     lift=0.42 * air)

    def attack(t):
        back = P.pulse(t, 0.0, 0.3, 0.34, 0.44)
        lunge = P.pulse(t, 0.34, 0.44, 0.5, 0.9)
        return shape(0.45 * back - 0.15 * lunge, lean=(0, 0.14 * back - 0.5 * lunge), front=0.38 * lunge - 0.08 * back)

    def die(t):
        a = P.smooth(t / 0.8)
        jig = math.sin(30 * t) * (1 - a) * 0.05
        return shape(0.9 * a + jig, wobble=jig)

    m.clip("idle", 2.0, idle)
    m.clip("walk", 0.8, walk)
    m.clip("attack", 1.0, attack)
    m.clip("die", 1.4, die, loops=False)
    return m


def build(name, base, k=1.0, eye=0x1A1A22, crown=False):
    def make():
        mb = P.kit.begin()
        body(mb, k, crown)
        P.kit.save(mb, P.FAMILY, name, dict(colors(base, eye), **P.palette(gold=0xE8C23A)), mech=mech(k))
    return make


MODELS = {
    "monster_slime": build("monster_slime", 0x6CC24A),
    "monster_slime_ice": build("monster_slime_ice", 0x6FB8E8),
    "monster_slime_fire": build("monster_slime_fire", 0xE8662A, eye=0x3A1408),
    "monster_slime_king": build("monster_slime_king", 0x9A5AD8, k=2.2, crown=True),
    "monster_slime_small": build("monster_slime_small", 0x9AD84A, k=0.5),
}
