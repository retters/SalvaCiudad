"""Dogs: a brown village mutt with a red collar and three breeds made with
the same generator (a shepherd, a mastiff and a small terrier). Clips:
idle, walk, run, eat, die, attack (bite), sit and sleep."""

from mathutils import Vector

import _parts as P
import quad

EYE_NOSE = P.palette(eye=0x151012, nose=0x1E1C1E)


def collar(mat, t=0.55, radius=0.158, bell=None):
    def add(spec, mb):
        a, b = Vector((0, -0.42, 0.66)), Vector((0, -0.62, 0.82))
        at = a.lerp(b, t)
        axis = (b - a).normalized()
        k = spec.k
        quad.tag(mb.cylinder(spec.V(at - axis * 0.028), spec.V(at + axis * 0.028), radius * k, radius * 0.97 * k,
                             mat, segments=8), "neck")
        if bell:
            low = at + Vector((0, -0.1, -0.13))
            quad.tag(mb.sphere(spec.V(low), 0.03 * k, bell, segments=6, rings=4), "neck")
    return add


def mutt():
    colors = {**P.shades("fur", 0xB07A45), **P.palette(light=0xF0E6D2, dark=0x6E4A2A, collar=0xB8312A,
                                                        brass=0xD9B24A), **EYE_NOSE}
    return quad.Quad("pet_dog", colors, quad.wolf_coat(saddle=False, tail_tip="light"), k=0.6, snout=0.85,
                     snout_r=1.1, ruff=0.7, ears="flop", tail=quad.TAIL_UP, sit_tail=0.0, lie_tail=0.0,
                     extra=collar("collar", bell="brass"))


def shepherd():
    colors = {**P.shades("fur", 0xC8964E), **P.palette(light=0xE8D2A8, dark=0x2E2A28, collar=0x5E3F36),
              **EYE_NOSE}
    return quad.Quad("pet_dog_shepherd", colors, quad.wolf_coat(muzzle="dark", tail_tip="dark"), k=0.68,
                     ruff=0.8, ears="up", ear_size=1.1, extra=collar("collar"))


def mastiff():
    colors = {**P.shades("fur", 0xC9A56B), **P.palette(light=0xE2CDA0, dark=0x3A2E28, collar=0x3A2E28,
                                                        iron=0xA9ACB2), **EYE_NOSE}

    def spiked(spec, mb):
        collar("collar", radius=0.2)(spec, mb)
        a, b = Vector((0, -0.42, 0.66)), Vector((0, -0.62, 0.82))
        at, axis = a.lerp(b, 0.55), (b - a).normalized()
        for i in range(7):
            out = Vector((1, 0, 0)).cross(axis)
            import math
            ang = (i - 3) * math.radians(38)
            d = (out * math.cos(ang) + Vector((1, 0, 0)) * math.sin(ang)).normalized()
            base = at + d * 0.195
            quad.tag(mb.cylinder(spec.V(base), spec.V(base + d * 0.06), 0.018 * spec.k, 0.0, "iron", segments=4),
                     "neck")

    return quad.Quad("pet_dog_mastiff", colors, quad.wolf_coat(saddle=False, muzzle="dark", socks=False),
                     k=0.8, bulk=1.3, head=1.25, snout=0.6, snout_r=1.4, neck=1.2, ruff=0.85, ears="flop",
                     ear_size=0.8, leg_r=1.25, speed=0.85, extra=spiked, max_tris=1800)


def terrier():
    colors = {**P.shades("fur", 0xEDE8DC), **P.palette(light=0xF6F2EA, dark=0x8A5A30, collar=0x2F6FA8),
              **EYE_NOSE}

    def coat(u, n):
        if u.y < -0.6 and u.z > 0.86 and abs(u.x) > 0.03:
            return "dark"   # Patches over the eyes and ears.
        if u.z > 0.7 and 0.0 < u.y < 0.45 and n.z > 0.3:
            return "dark"   # A saddle patch.
        return "fur"

    return quad.Quad("pet_dog_terrier", colors, coat, k=0.42, leg=0.8, head=1.2, snout=0.8, snout_r=1.15,
                     ruff=0.75, ears="flop", ear_size=0.6, tail=quad.TAIL_STUB, sit_tail=0.0, lie_tail=0.0,
                     extra=collar("collar"), eye=0.02)


def puppy():
    colors = {**P.shades("fur", 0xC8964E), **P.palette(light=0xF0E6D2, dark=0x6E4A2A, collar=0x2F6FA8), **EYE_NOSE}
    return quad.Quad("pet_puppy", colors, quad.wolf_coat(saddle=False, tail_tip="light"), k=0.33, leg=0.82, head=1.4,
                     snout=0.6, snout_r=1.2, ruff=0.75, ears="flop", ear_size=0.8, tail=quad.TAIL_STUB, sit_tail=0.0,
                     lie_tail=0.0, extra=collar("collar"), eye=0.022, budget=650)


def build(make):
    return lambda: P.kit.build_zoo_spec(make(), P.FAMILY)


MODELS = {"pet_dog": build(mutt), "pet_dog_shepherd": build(shepherd), "pet_dog_mastiff": build(mastiff),
          "pet_dog_terrier": build(terrier), "pet_puppy": build(puppy)}
