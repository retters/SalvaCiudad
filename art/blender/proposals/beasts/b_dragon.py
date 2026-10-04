"""The great dragon: a four-legged boss 15 m long with a 16 m wingspan, a
long neck with a crest, a horned head with a hinged jaw full of teeth, bat
wings with three fingers, clawed feet and a tail ending in a spade. Clips:
idle (wings half folded, the head sways), walk, fly, attack (a bite),
breath (it rears and throws a jet of fire that sweeps from side to side)
and die (it rolls on its side). Variants by color (red, green, black,
white) and a young dragon at 40 % of the size."""

from mathutils import Vector

import _bq as B
from _bq import hull, spike

NECK = [(0, -1.9, 3.0), (0, -2.75, 3.75), (0, -3.5, 4.45), (0, -4.2, 4.95), (0, -4.9, 5.2)]
NECK_R = [0.66, 0.54, 0.45, 0.39, 0.34]
TAIL = [(0, 1.9, 2.6), (0, 3.0, 2.3), (0, 4.1, 1.9), (0, 5.2, 1.5), (0, 6.2, 1.15), (0, 7.1, 0.92), (0, 7.9, 0.8),
        (0, 8.6, 0.75)]
TAIL_R = [0.72, 0.6, 0.48, 0.38, 0.29, 0.21, 0.14, 0.08]
SH, EL, TIP = Vector((0.85, -1.0, 3.45)), Vector((3.2, -0.8, 4.6)), Vector((8.0, 0.0, 4.1))


def colors(scale, dark, belly, membrane, horn=0xE6D8B8, eye=0xFFD23A, fire=(0xE8501E, 0xFF9A2A, 0xFFE27A)):
    return {**B.shades("scale", scale), **B.palette(scale_dark=dark, belly=belly, membrane=membrane, horn=horn,
                                                    tooth=0xF2EAD0, eye=eye, mouth=0x6A1A20, fire_a=fire[0],
                                                    fire_b=fire[1], fire_c=fire[2])}


RED = colors(0xA83226, 0x74201C, 0xE8B86A, 0x6A2420)
GREEN = colors(0x4E7A3A, 0x35582A, 0xD8C87A, 0x8A5A32, fire=(0x4EA02A, 0x9ADE3A, 0xE8FF8A))
BLACK = colors(0x34303C, 0x201E26, 0x6A5A7A, 0x5A3A7A, horn=0xC8C2D0, eye=0xC86AFF, fire=(0x7A3AC8, 0xB06AFF, 0xF0D0FF))
WHITE = colors(0xDCE6EE, 0xA8BCCC, 0xF6FAFC, 0x8AB4D8, horn=0x6A8AA8, eye=0x3AA0FF, fire=(0x6FB8E8, 0xA8DCF4, 0xFFFFFF))


def dragon(name, cols, k=1.0):
    mb = B.P.kit.begin()
    q = B.Beast(L=3.2, zs=2.75, w=0.9, hl=2.2, fb=0.24, hb=-0.24, ankle=0.32, toe=0.75)
    q.trunk(mb, "scale", (1.05, 1.5, 1.1), (0.95, 1.4, 0.95), (0.95, 1.35, 1.0), belly_mat="belly")
    q.legs(mb, 0.42, 0.27, "scale", "scale_dark", foot="claw", foot_r=0.34, hind=1.12)
    h = q.neck(mb, NECK, NECK_R, ("scale", "scale_dark"), sides=8)
    B.head_dragon(mb, h, 2.2, "head", "jaw", horns=3, frill=True)
    neck = [Vector(p) for p in NECK]
    B.crest(mb, "neck", neck, NECK_R, "horn", 0.5, per=2)
    tail = q.tail(mb, TAIL, TAIL_R, ("scale_dark", "scale"))
    B.crest(mb, "tail", tail, TAIL_R, "horn", 0.5, last=6, per=2)
    for i in range(7):                                         # Spines down the back.
        y = -1.5 + i * 0.5
        spike(mb, (0, y, 3.5 - 0.02 * i * i), (0, y + 0.25, 4.2 - 0.03 * i * i), 0.16, "horn", "body")
    t = tail[-1]
    hull(mb, [t + Vector(o) for o in ((0, -0.2, 0.06), (0, -0.2, -0.06), (0.55, 0.35, 0), (-0.55, 0.35, 0), (0, 1.1, 0.0),
                                      (0, 0.3, 0.1), (0, 0.3, -0.1))], "horn", f"tail.{len(TAIL) - 1}")
    q.wings(SH, EL, TIP, fold=(30.0, 78.0, 22.0), flap=(26.0, 20.0, -12.0))
    for sx in (1, -1):
        def m(p, sx=sx):
            return Vector((p[0] * sx, p[1], p[2]))
        B.wing_membrane(mb, sx, m(SH), m(EL), m(TIP), m((0.5, 1.5, 3.0)), r=0.24, chord=3.6, thick=0.06)
    q.fire(mb, (0, -0.9, 2.45), n=7, r0=0.35, r1=0.95)
    q.mech()
    q.clips(walk=dict(frames=44, duty=0.68, lift=0.35, crouch=0.14, yaw=1.5, wag=5.0, nod=1.5),
            attack_s=1.6, die_s=2.6, breath=dict(seconds=3.0),
            fly=dict(height=2.2, seconds=1.6, speed=11.0, pitch=7.0, neck=7.0, head=-24.0, tail=3.0), wide=2.0)
    B.save(mb, name, cols, q.m, k)


MODELS = {
    "boss_dragon": B.builder(dragon, "boss_dragon", RED),
    "boss_dragon_green": B.builder(dragon, "boss_dragon_green", GREEN),
    "boss_dragon_black": B.builder(dragon, "boss_dragon_black", BLACK),
    "boss_dragon_white": B.builder(dragon, "boss_dragon_white", WHITE),
    "boss_dragon_young": B.builder(dragon, "boss_dragon_young", GREEN, k=0.4),
}
