"""Domestic and work animals made with the quad generator, all hoofed:

- donkey with a pack saddle (blanket, wooden frame, two baskets and a sack
  on top), a plain donkey and a bigger brown mule with the same pack;
- ox with long horns, a nose ring and a wooden yoke (red-brown and black);
- goat with horns and a beard (white, brown and black-and-white).
Clips: idle, walk, run (a trot), eat and die; the goat also has attack (a
butt with the head down)."""

from mathutils import Vector

import _parts as P
import quad

THIN_TAIL = ([(0, 0.5, 0.68), (0, 0.6, 0.6), (0, 0.64, 0.46), (0, 0.65, 0.32)], [0.03, 0.026, 0.022, 0.02])


def tuft(spec, mb, mat="dark"):
    a = Vector(spec.tail_pts[-1])
    quad.tag(mb.cylinder(spec.V(a), spec.V(a + Vector((0, 0.01, -0.16))), 0.045 * spec.k, 0.012 * spec.k, mat,
                         segments=5), f"tail.{len(spec.tail_pts) - 1}")


def mane(spec, mb, mat="dark"):
    """A short upright mane from the poll to the withers."""
    a, b = Vector((0, -0.6, 0.97)), Vector((0, -0.36, 0.86))
    for i in range(5):
        p = a.lerp(b, i / 4)
        quad.tag(P.studies.plate(mb, [spec.V(p + Vector((0, -0.04, -0.03))), spec.V(p + Vector((0, 0.04, -0.03))),
                                      spec.V(p + Vector((0, 0.03, 0.07))), spec.V(p + Vector((0, -0.03, 0.08)))],
                                 0.03 * spec.k, mat), "neck" if i < 3 else "chest")


def pack(spec, mb):
    """A pack saddle: blanket, crossed wooden frame, a basket on each side
    and a sack tied on top."""
    b = spec.bulk
    V = spec.V

    def piece(points, mat):
        return quad.tag(P.hull(mb, [V(p) for p in points], mat), "body")

    piece([(s * x * b, y, z) for s in (-1, 1) for x, z in ((0.2, 0.66), (0.17, 0.8), (0.06, 0.85))
           for y in (-0.2, 0.32)], "cloth")
    for y in (-0.12, 0.24):                                      # The frame: an X at each end.
        for s in (-1, 1):
            quad.tag(P.bar(mb, V((s * 0.13 * b, y, 0.82)), V((-s * 0.05 * b, y, 0.97)), 0.03 * spec.k,
                           0.03 * spec.k, "wood", side=(0, 1, 0)), "body")
    quad.tag(P.bar(mb, V((0, -0.14, 0.9)), V((0, 0.26, 0.9)), 0.03 * spec.k, 0.03 * spec.k, "wood"), "body")
    for s in (-1, 1):
        x0, x1 = s * 0.2 * b, s * 0.36 * b
        piece([(x, y, z) for x in (x0, x1) for y in (-0.14, 0.26) for z in (0.5, 0.8)]
              + [(x1 + s * 0.02, 0.06, 0.65)], "basket")
        piece([(x, y, 0.8 + dz) for x in (x0 - s * 0.01, x1 + s * 0.01) for y in (-0.15, 0.27)
               for dz in (0.0, 0.025)], "wood")                  # Rim.
        quad.tag(P.rock(mb, V((s * 0.28 * b, 0.06, 0.84)), tuple(r * spec.k for r in (0.07, 0.16, 0.06)), "sack",
                        count=10, seed=3 + s), "body")           # What it carries.
    quad.tag(P.rock(mb, V((0, 0.06, 1.0)), tuple(r * spec.k for r in (0.13, 0.2, 0.09)), "sack", count=14, seed=6),
             "body")
    quad.tag(P.bar(mb, V((-0.14 * b, 0.06, 0.93)), V((0.14 * b, 0.06, 0.93)), 0.02 * spec.k, 0.2 * spec.k, "rope",
                   side=(0, 0, 1)), "body")
    # Girth under the belly.
    quad.tag(mb.cylinder(V((0, 0.02, 0.62)), V((0, 0.08, 0.62)), 0.215 * b * spec.k, 0.215 * b * spec.k, "rope",
                         segments=8), "body")


def donkey(name, fur, light, dark, k=1.15, packed=True):
    colors = {**P.shades("fur", fur), **P.palette(light=light, dark=dark, hoof=0x2A2624, eye=0x151012, nose=0x3A3432,
                                                  cloth=0xA83A2E, wood=0x8A6038, basket=0xC9A45E, sack=0xD8C8A0,
                                                  rope=0x6B4628)}

    def coat(u, n):
        if u.y < -0.86 and u.z < 0.86:
            return "light"                                       # The pale muzzle.
        if -0.4 < u.y < 0.5 and u.z < 0.52 and n.z < -0.1 and abs(u.x) < 0.14:
            return "light"
        if abs(u.x) < 0.035 and u.z > 0.72 and -0.3 < u.y < 0.5 and n.z > 0.5:
            return "dark"                                        # The stripe along the back.
        return "fur"

    def extra(spec, mb):
        mane(spec, mb)
        tuft(spec, mb)
        if packed:
            pack(spec, mb)

    return quad.Quad(name, colors, quad.hoof_coat(coat), k=k, leg=1.22, bulk=1.2, belly=1.25, head=1.15, snout=1.3,
                     snout_r=1.4, neck=1.0, ruff=0.62, ears="long", ear_size=1.0, tail=THIN_TAIL, tail_detail="fur",
                     hooves=True, leg_r=0.95, clips=(), trot=True, speed=1.1, extra=extra, max_tris=2600,
                     budget=850, eye=0.02, eat=(6.0, 8.0, 42.0, 20.0), snout_end=1.5)


def ox(name, fur, light, dark):
    colors = {**P.shades("fur", fur), **P.palette(light=light, dark=dark, hoof=0x2A2624, eye=0x151012, nose=0x3A3432,
                                                  horn=0xE6D8B8, wood=0x8A6038, iron=0x8A8F96, rope=0x6B4628)}

    def coat(u, n):
        if u.y < -0.84 and u.z < 0.86:
            return "light"
        return "fur"

    def extra(spec, mb):
        k = spec.k
        tuft(spec, mb)
        for s in (-1, 1):                                        # Horns: out, then forward and up.
            a, b, c = spec.H(s * 0.09, 0.02, 0.1), spec.H(s * 0.3, 0.0, 0.16), spec.H(s * 0.36, -0.1, 0.34)
            quad.tag(mb.cylinder(a, b, 0.04 * k, 0.03 * k, "horn", segments=5), "head")
            quad.tag(mb.cylinder(b, c, 0.03 * k, 0.0, "horn", segments=5), "head")
        tip = Vector(spec.snout_b)
        quad.tag(mb.cylinder(spec.V(tip + Vector((0, -0.03, -0.03))), spec.V(tip + Vector((0, -0.035, -0.03))),
                             0.035 * k, 0.035 * k, "iron", segments=6), "head")       # Nose ring.
        # The yoke: a beam over the neck with a bow under it.
        b = spec.bulk
        beam = [(x, y, z) for x in (-0.3, 0.3) for y in (-0.44, -0.36) for z in (0.9, 0.97)]
        quad.tag(P.hull(mb, [spec.V((p[0] * b, p[1], p[2])) for p in beam] + [spec.V((0, -0.4, 1.02))], "wood"),
                 "chest")
        for s in (-1, 1):
            quad.tag(P.bar(mb, spec.V((s * 0.17 * b, -0.4, 0.93)), spec.V((s * 0.15 * b, -0.42, 0.5)), 0.03 * k,
                           0.03 * k, "wood"), "chest")
            quad.tag(mb.cylinder(spec.V((s * 0.3 * b, -0.4, 0.93)), spec.V((s * 0.3 * b, -0.3, 0.9)), 0.03 * k,
                                 0.03 * k, "iron", segments=6), "chest")              # Rings for the traces.
        quad.tag(P.bar(mb, spec.V((-0.15 * b, -0.42, 0.5)), spec.V((0.15 * b, -0.42, 0.5)), 0.03 * k, 0.03 * k,
                       "wood"), "chest")

    return quad.Quad(name, colors, quad.hoof_coat(coat), k=1.5, leg=1.0, bulk=1.6, belly=1.55, head=1.15, snout=0.95,
                     snout_r=1.75, neck=1.45, ruff=1.2, ears="side", ear_size=1.0, tail=THIN_TAIL, tail_detail="fur",
                     hooves=True, leg_r=1.5, clips=(), trot=True, speed=0.8, extra=extra, max_tris=2600, budget=900,
                     eye=0.018, eat=(5.0, 6.0, 30.0, 12.0), snout_end=1.2)


def goat(name, fur, light, dark, patch=False):
    colors = {**P.shades("fur", fur), **P.palette(light=light, dark=dark, hoof=0x2A2624, eye=0xD8B84A,
                                                  nose=0x3A3432, horn=0x8A7A62)}

    def coat(u, n):
        if u.y < -0.86 and u.z < 0.84:
            return "light"
        if patch and (u.y < -0.3 or (u.y > 0.3 and u.z > 0.5)):
            return "dark"
        return "fur"

    def extra(spec, mb):
        k = spec.k
        for s in (-1, 1):                                        # Horns swept back.
            a, b, c = spec.H(s * 0.06, 0.0, 0.11), spec.H(s * 0.09, 0.1, 0.27), spec.H(s * 0.13, 0.26, 0.3)
            quad.tag(mb.cylinder(a, b, 0.035 * k, 0.026 * k, "horn", segments=5), "head")
            quad.tag(mb.cylinder(b, c, 0.026 * k, 0.0, "horn", segments=5), "head")
        tip = Vector(spec.snout_b)
        quad.tag(mb.cylinder(spec.V(tip + Vector((0, 0.05, -0.06))), spec.V(tip + Vector((0, 0.07, -0.2))),
                             0.03 * k, 0.0, "light", segments=4), "head")              # Beard.

    return quad.Quad(name, colors, quad.hoof_coat(coat), k=0.66, leg=1.05, bulk=1.1, belly=1.3, head=0.95, snout=0.9,
                     snout_r=1.05, neck=0.85, ruff=0.6, ears="side", ear_size=0.7, tail=quad.TAIL_STUB, hooves=True,
                     leg_r=0.85, clips=("attack",), trot=True, extra=extra, sit_tail=0.0, lie_tail=0.0, eye=0.02,
                     eat=(8.0, 8.0, 36.0, 20.0), snout_end=1.2)


def build(make, *args, **kw):
    return lambda: P.kit.build_zoo_spec(make(*args, **kw), P.FAMILY)


MODELS = {
    "animal_donkey_pack": build(donkey, "animal_donkey_pack", 0x8A8580, 0xE8E2D6, 0x4A4440),
    "animal_donkey": build(donkey, "animal_donkey", 0x8A8580, 0xE8E2D6, 0x4A4440, packed=False),
    "animal_mule_pack": build(donkey, "animal_mule_pack", 0x6A4A36, 0xD8C4A4, 0x2E2420, k=1.32),
    "animal_ox": build(ox, "animal_ox", 0x9A6240, 0xE2CDB0, 0x5A3A28),
    "animal_ox_black": build(ox, "animal_ox_black", 0x34302E, 0x8A8078, 0x1E1C1C),
    "animal_goat": build(goat, "animal_goat", 0xEDE6D8, 0xF8F4EC, 0x6A4A36),
    "animal_goat_brown": build(goat, "animal_goat_brown", 0x8A6240, 0xE2CDB0, 0x4A3628),
    "animal_goat_pied": build(goat, "animal_goat_pied", 0xEDE6D8, 0xF8F4EC, 0x2E2A28, patch=True),
}
