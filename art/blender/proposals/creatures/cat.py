"""Cats: gray (the color of the cat-folk in the owner's reference), tabby,
black and white. A round head with a short muzzle, pointed ears and a long
tail held up. Clips: idle, walk, run, eat, die, attack (a paw swipe), sit
and sleep."""

import math

import _parts as P
import quad


def plain(main="fur", light="light", chest=True):
    def coat(u, n):
        if u.y < -0.8 and u.z < 0.86:
            return light                      # Muzzle.
        if chest and u.y < -0.38 and u.z < 0.72 and abs(u.x) < 0.12 and n.y < 0.2 and n.z < 0.4:
            return light
        if chest and u.z < quad.SOCK * 0.6 and 0.25 < abs(u.y) < 0.6:
            return light                      # Paws.
        return main
    return coat


def tabby(u, n):
    base = plain()(u, n)
    if base != "fur":
        return base
    if u.y > 0.6:                              # Tail rings.
        return "stripe" if math.floor(u.z * 8 + u.y * 3) % 2 == 0 else "fur"
    if u.z > 0.66 and -0.45 < u.y < 0.5 and math.floor((u.y + 2.0) * 8.5) % 2 == 0:
        return "stripe"
    if u.y < -0.62 and u.z > 0.93 and abs(u.x) < 0.035:
        return "stripe"                        # Forehead.
    return "fur"


def cat(name, fur, light, eye=0x1A1A14, stripe=None, nose=0xD9868A, coat=None, chest=True, **shape):
    colors = {**P.shades("fur", fur), **P.palette(light=light, eye=eye, nose=nose, pink=0xE7A7A2)}
    if stripe is not None:
        colors.update(P.palette(stripe=stripe))
    params = dict(k=0.34, leg=0.9, head=1.3, snout=0.3, snout_r=0.9, neck=0.9, ruff=0.72, ears="up", ear_size=0.75,
                  tail=quad.TAIL_CAT, attack="swipe", eye=0.018, inner_ear="pink", sit_tail=0.0, lie_tail=0.0,
                  max_tris=1500, budget=750)
    params.update(shape)
    return quad.Quad(name, colors, coat or plain(chest=chest), **params)


def spotted(u, n):
    base = plain()(u, n)
    if base != "fur":
        return base
    if u.y > 0.56:
        return "stripe"                        # The black tip of the stub tail.
    if u.z > 0.3 and (math.sin(u.y * 23.0) * math.sin(u.z * 29.0 + u.x * 17.0)) > 0.55:
        return "stripe"
    return "fur"


def tufts(spec, mb):
    """Black tufts on the ear tips and a ruff of cheek fur."""
    for s in (-1, 1):
        a, b, tip = spec.ear_points(s)
        quad.tag(mb.cylinder(tip, tip + (tip - (a + b) * 0.5).normalized() * 0.07 * spec.k, 0.012 * spec.k, 0.0,
                             "stripe", segments=4), "ear.L" if s > 0 else "ear.R")
        quad.tag(mb.cylinder(spec.H(s * 0.1, -0.05, -0.05), spec.H(s * 0.16, -0.03, -0.11), 0.035 * spec.k, 0.0, "light",
                             segments=4), "head")


def build(*args, **kw):
    return lambda: P.kit.build_zoo_spec(cat(*args, **kw), P.FAMILY)


MODELS = {
    "pet_cat": build("pet_cat", 0x8E9299, 0xE9E6E0, eye=0x2A3A1A),
    "pet_cat_tabby": build("pet_cat_tabby", 0xD98A3A, 0xF6EBDD, stripe=0xA85E22, coat=tabby),
    "pet_cat_black": build("pet_cat_black", 0x2C2C31, 0x2C2C31, eye=0xD8C83A, nose=0x1A1A1C, chest=False),
    "pet_cat_white": build("pet_cat_white", 0xF2EFE8, 0xFBF9F4, eye=0x3F86C8),
    "pet_kitten": build("pet_kitten", 0xD98A3A, 0xF6EBDD, stripe=0xA85E22, coat=tabby, k=0.2, head=1.55, leg=0.8,
                        ear_size=0.7, budget=600),
    "animal_lynx": build("animal_lynx", 0xC29A62, 0xF2E8D6, stripe=0x3A2A20, coat=spotted, k=0.62, leg=1.08, head=1.2,
                         ruff=0.9, snout=0.4, ear_size=1.0, tail=quad.TAIL_STUB, extra=tufts, budget=800),
    "animal_wildcat": build("animal_wildcat", 0x8A7A5E, 0xD8CCB0, stripe=0x4A3E2E, coat=tabby, k=0.42, head=1.25,
                            ruff=0.85),
}
