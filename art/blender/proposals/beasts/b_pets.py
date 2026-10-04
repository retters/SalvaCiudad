"""Pets and working animals on the Beast body (_bq.py):

- rabbit: long ears, big hind legs, a white tail (brown and white);
- camel: one hump, a long neck; plain, with a pack (bags and jars) or with
  a riding saddle;
- truffle pig: a fat pig with a harness; its eat clip is rooting the ground;
- ram: a woolly body and curled horns; attack is a butt with the head down;
- pack of hounds: three hunting dogs in one model, each on its own bones,
  moving out of step.
Clips: idle, walk, run, eat (not the hounds), attack and die.
"""

import math

from mathutils import Vector

import _bq as B
from _bq import hull, spike, seg, ball, plate, lump, rock


def rabbit(name, fur, belly, k=1.0):
    mb = B.P.kit.begin()
    q = B.Beast(L=0.2, zs=0.155, w=0.045, hl=0.08, fb=0.25, hb=-0.35, ankle=0.02, toe=0.05, hw=0.07)
    q.trunk(mb, "fur", (0.07, 0.1, 0.08), (0.085, 0.12, 0.095), (0.1, 0.115, 0.115))
    q.legs(mb, 0.026, 0.016, "fur", "fur_shade", foot="paw", foot_r=0.02, hind=1.7, shoulder=0.8)
    h = q.neck(mb, [(0, -0.1, 0.165), (0, -0.15, 0.225)], [0.06, 0.05], ("fur",))
    hp = B.head_muzzle(mb, h, 1.0, "head", "jaw", skull=(0.05, 0.06, 0.05), mz=(0.045, 0.02, 0.035, 0.012), ears="long",
                       ear=0.36, mat="fur", mat2="fur_shade", ear_mat="fur", eye_r=0.009)
    for sx in (-1, 1):                                          # The pink inside of the ears.
        plate(mb, [hp(sx * 0.03, 0.022, 0.07), hp(sx * 0.04, 0.03, 0.14), hp(sx * 0.02, 0.035, 0.14)], 0.005, "ear", "head")
    ball(mb, (0, 0.21, 0.17), 0.035, "belly", "body", segments=6, rings=4)                         # The tail.
    lump(mb, (0, -0.1, 0.1), (0.05, 0.06, 0.045), "belly", "body", seed=7, count=10, tones=False)
    q.mech()
    q.clips(walk=dict(frames=10, duty=0.6, lift=0.025, crouch=0.006, nod=4.0), run=dict(frames=8, lift=0.04, crouch=0.01),
            jaw=6.0,
            eat=dict(bend=30.0, head=20.0, body=8.0, seconds=2.0), wide=0.12, idle_look=10.0, attack_s=0.8)
    cols = {**B.shades("fur", fur), **B.palette(belly=belly, eye=0x151012, nose=0xD88A8A, ear=0xE8A8A8)}
    B.save(mb, name, cols, q.m, k)


def camel(name, coat, gear=None, k=1.0):
    mb = B.P.kit.begin()
    q = B.Beast(L=1.45, zs=1.7, w=0.2, hl=1.42, fb=-0.09, hb=0.15, ankle=0.12, toe=0.13)
    q.trunk(mb, "coat", (0.32, 0.5, 0.42), (0.34, 0.6, 0.4), (0.3, 0.45, 0.38))
    lump(mb, (0, 0.08, 2.02), (0.26, 0.42, 0.36), "coat", "body", seed=8, count=16)                 # The hump.
    q.legs(mb, 0.11, 0.055, "coat", "coat_shade", foot="paw", foot_r=0.09, hind=1.05, shoulder=1.6)
    radii = [0.24, 0.17, 0.14, 0.125]
    h = q.neck(mb, [(0, -0.72, 1.62), (0, -1.12, 1.66), (0, -1.38, 2.08), (0, -1.46, 2.52)], radii, ("coat",))
    hp = B.head_muzzle(mb, h, 1.1, "head", "jaw", skull=(0.095, 0.13, 0.1), mz=(0.3, 0.06, 0.12, 0.1), ears="up", ear=0.3,
                       mat="coat", mat2="coat_shade")
    lump(mb, hp(0, 0.03, 0.09), (0.07, 0.08, 0.05), "hair", "head", seed=5, count=10, tones=False)
    lump(mb, q.necks[0][1][0] + Vector((0, -0.05, -0.2)), (0.14, 0.14, 0.2), "hair", "neck.1", seed=6, count=10, tones=False)
    pts = q.tail(mb, [(0, 0.74, 1.7), (0, 0.84, 1.5), (0, 0.86, 1.2)], [0.04, 0.035, 0.03], ("coat",))
    spike(mb, pts[-1], pts[-1] + Vector((0, 0.01, -0.22)), 0.05, "hair", "tail.2")
    if gear:
        top = 1.72
        hull(mb, [(sx * x, y, z) for sx in (-1, 1) for x, z in ((0.36, top - 0.22), (0.3, top + 0.2), (0.12, top + 0.62))
                  for y in (-0.42, 0.56)], "cloth", "body")                                       # Blanket over the hump.
        if gear == "pack":
            for sx in (-1, 1):
                rock(mb, (sx * 0.5, -0.1, top + 0.05), (0.16, 0.3, 0.24), "sack", "body", count=12, seed=3 + sx)
                mb.cylinder((sx * 0.5, 0.42, top - 0.2), (sx * 0.5, 0.42, top + 0.18), 0.13, 0.1, "clay",
                            weights={"body": 1.0}, segments=7)
                mb.cylinder((sx * 0.5, 0.42, top + 0.18), (sx * 0.5, 0.42, top + 0.26), 0.05, 0.07, "clay",
                            weights={"body": 1.0}, segments=7)
            rock(mb, (0, 0.08, top + 0.7), (0.24, 0.34, 0.12), "sack", "body", count=12, seed=9)
        else:
            for y in (-0.3, 0.46):                              # A wooden saddle frame with a horn at each end.
                for sx in (-1, 1):
                    B.bar(mb, (sx * 0.26, y, top + 0.3), (0, y, top + 0.92), 0.05, 0.05, "wood", "body", side=(0, 1, 0))
                ball(mb, (0, y, top + 0.95), 0.06, "wood", "body", segments=6, rings=4)
            hull(mb, [(sx * 0.22, y, top + z) for sx in (-1, 1) for y, z in ((-0.26, 0.42), (0.42, 0.42), (0.08, 0.7))],
                 "leather", "body")
            for i in range(5):                                  # Tassels.
                spike(mb, (0.37, -0.36 + i * 0.2, top - 0.2), (0.38, -0.36 + i * 0.2, top - 0.36), 0.03, "tassel", "body")
                spike(mb, (-0.37, -0.36 + i * 0.2, top - 0.2), (-0.38, -0.36 + i * 0.2, top - 0.36), 0.03, "tassel", "body")
    q.mech()
    q.clips(walk=dict(frames=30, duty=0.66, lift=0.14, crouch=0.06, nod=3.0, wag=4.0), run=dict(frames=16, lift=0.24),
            jaw=10.0, eat=dict(bend=27.0, head=-20.0), wide=0.7)
    cols = {**B.shades("coat", coat), **B.palette(hair=B.mix(coat, 0x000000, 0.3), eye=0x151012, nose=B.mix(coat, 0x000000, 0.45),
                                                  cloth=0xA83A2E, sack=0xD8C8A0, clay=0xB5694A, wood=0x7A5636, leather=0x5E3F36,
                                                  tassel=0xE8C03A)}
    B.save(mb, name, cols, q.m, k)


def pig(name, skin, k=1.0):
    mb = B.P.kit.begin()
    q = B.Beast(L=0.6, zs=0.5, w=0.13, hl=0.32, fb=-0.12, hb=0.16, ankle=0.04, toe=0.05)
    q.trunk(mb, "skin", (0.2, 0.27, 0.21), (0.23, 0.32, 0.23), (0.21, 0.26, 0.21))
    q.legs(mb, 0.06, 0.032, "skin", "skin_shade", foot="hoof", foot_mat="hoof", foot_r=0.035)
    h = q.neck(mb, [(0, -0.3, 0.48), (0, -0.44, 0.47)], [0.17, 0.15], ("skin",))
    hp = B.head_muzzle(mb, h, 1.0, "head", "jaw", skull=(0.12, 0.13, 0.12), mz=(0.15, 0.06, 0.1, 0.04), ears="flop",
                       ear=0.7, mat="skin", mat2="skin_shade", nose="snout", eye_r=0.014)
    mb.cylinder(hp(0, -0.2, -0.04), hp(0, -0.235, -0.045), 0.055, 0.06, "snout", weights={"head": 1.0}, segments=8)
    for sx in (-1, 1):
        ball(mb, hp(sx * 0.02, -0.24, -0.04), 0.012, "hoof", "head", segments=4, rings=3)
    pts = [Vector((0, 0.36, 0.56)), Vector((0.03, 0.42, 0.62)), Vector((-0.02, 0.44, 0.68)), Vector((0.02, 0.41, 0.72))]
    q.tail_pts = pts
    B.chain(mb, "tail", pts, [0.018, 0.016, 0.014, 0.01], ("skin_shade",), sides=4)
    # The truffle hunter's harness: a strap around the chest, a ring and a bit of rope.
    mb.cylinder((0, -0.2, 0.46), (0, -0.14, 0.46), 0.225, 0.225, "leather", weights={"body": 1.0}, segments=10)
    ball(mb, (0, -0.17, 0.7), 0.03, "iron", "body", segments=5, rings=3)
    seg(mb, (0, -0.17, 0.7), (0.1, 0.1, 0.74), 0.012, 0.012, "rope", "body", sides=4)
    seg(mb, (0.1, 0.1, 0.74), (0.2, 0.3, 0.68), 0.012, 0.012, "rope", "body", sides=4)
    q.mech()

    def tail(pose, t):
        for i in range(3):
            pose.turn(f"tail.{i + 1}", B.Z, 8.0 * math.sin(4 * math.pi * t + i))
    q.clips(walk=dict(frames=18, duty=0.64, lift=0.04, crouch=0.02, nod=3.0, wag=0.0), run=dict(frames=10, lift=0.06),
            jaw=8.0, eat=dict(bend=10.0, head=22.0, body=7.0, seconds=3.0), wide=0.4, extra_idle=tail, extra_walk=tail)
    cols = {**B.shades("skin", skin), **B.palette(hoof=0x3A2E2A, eye=0x151012, snout=B.mix(skin, 0xC85A6A, 0.5),
                                                  leather=0x5E3F36, iron=0x8A8F96, rope=0xC8B078)}
    B.save(mb, name, cols, q.m, k)


def ram(name, wool, face, k=1.0):
    mb = B.P.kit.begin()
    q = B.Beast(L=0.72, zs=0.74, w=0.13, hl=0.5, fb=-0.1, hb=0.16, ankle=0.05, toe=0.06)
    q.trunk(mb, "wool", (0.25, 0.32, 0.27), (0.26, 0.36, 0.27), (0.25, 0.3, 0.27))
    q.legs(mb, 0.055, 0.028, "face", "face", foot="hoof", foot_mat="hoof", foot_r=0.035, shoulder=1.2)
    h = q.neck(mb, [(0, -0.36, 0.8), (0, -0.5, 0.98)], [0.17, 0.13], ("wool",))
    hp = B.head_muzzle(mb, h, 1.0, "head", "jaw", skull=(0.09, 0.11, 0.09), mz=(0.17, 0.045, 0.085, 0.07), ears="side",
                       ear=0.5, mat="face", mat2="face_shade")
    lump(mb, hp(0, 0.03, 0.06), (0.085, 0.08, 0.06), "wool", "head", seed=5, count=10, tones=False)
    for sx in (-1, 1):                                          # Curled horns: one turn and a quarter.
        c = hp(sx * 0.1, 0.02, -0.01)
        pts = []
        for i in range(1, 9):
            u = i / 8.0
            a = math.radians(110 - 440 * u)
            r = 0.11 - 0.03 * u
            pts.append(c + Vector((sx * (0.02 + 0.09 * u), -r * math.cos(a) * -1.0, r * math.sin(a))))
        B.horn(mb, hp(sx * 0.06, 0.0, 0.08), pts, 0.045, "horn", "head", sides=5)
    rock(mb, (0, 0.4, 0.78), (0.05, 0.07, 0.05), "wool", "body", count=8, seed=4)
    q.mech()
    q.clips(walk=dict(frames=20, duty=0.64, lift=0.06, crouch=0.025, nod=3.0), run=dict(frames=11, lift=0.1), attack="gore",
            jaw=6.0, eat=dict(bend=40.0, head=-5.0, body=3.0), wide=0.45, attack_s=1.0)
    cols = {**B.shades("wool", wool), **B.shades("face", face), **B.palette(hoof=0x2A2624, eye=0xD8B84A, nose=0x2A2020,
                                                                          horn=0xC8B48A)}
    B.save(mb, name, cols, q.m, k)


def hound(mb, origin, tag, coat):
    q = B.Beast(L=0.6, zs=0.6, w=0.09, hl=0.46, fb=0.16, hb=-0.2, ankle=0.045, toe=0.075, origin=origin, tag=tag)
    q.trunk(mb, coat, (0.15, 0.25, 0.2), (0.11, 0.24, 0.13), (0.12, 0.2, 0.15))
    q.legs(mb, 0.05, 0.027, coat, coat + "_shade", foot="paw", foot_r=0.032)
    h = q.neck(mb, [(0, -0.28, 0.66), (0, -0.44, 0.84)], [0.11, 0.085], (coat,))
    hp = B.head_muzzle(mb, h, 0.9, q.n("head"), q.n("jaw"), skull=(0.085, 0.11, 0.085), mz=(0.2, 0.04, 0.075, 0.03),
                       ears="flop", ear=0.8, mat=coat, mat2=coat + "_shade", ear_mat="ear", eye_r=0.014)
    a = q.necks[0][1][0].lerp(q.necks[0][1][1], 0.55)
    mb.cylinder(a + Vector((0, 0.02, -0.02)), a + Vector((0, -0.02, 0.02)), 0.105, 0.105, "collar",
                weights={q.n("neck.1"): 1.0}, segments=8)
    q.tail(mb, [(0, 0.32, 0.62), (0, 0.46, 0.68), (0, 0.56, 0.8), (0, 0.6, 0.92)], [0.03, 0.026, 0.02, 0.012], (coat,))
    return q


def hounds(name, k=1.0):
    mb = B.P.kit.begin()
    pack = [hound(mb, (0.0, -0.35), ".a", "tan"), hound(mb, (0.55, 0.35), ".b", "white"), hound(mb, (-0.5, 0.5), ".c", "brown")]
    m = B.pack(pack, phases=[0.0, 0.5, 0.25], walk=dict(frames=16, duty=0.62, lift=0.05, crouch=0.03, nod=3.0, wag=14.0),
               run=dict(frames=10, lift=0.09), jaw=30.0, wide=0.3, attack_s=0.9, idle_look=9.0)
    cols = {**B.shades("tan", 0xC89A5A), **B.shades("white", 0xE8E2D4), **B.shades("brown", 0x7A4E30),
            **B.palette(ear=0x5A3A26, eye=0x151012, nose=0x1E1A1A, tooth=0xF2EAD0, collar=0xA83A2E)}
    B.save(mb, name, cols, m, k)


MODELS = {
    "pet_rabbit": B.builder(rabbit, "pet_rabbit", 0x9A7A5A, 0xECE4D6),
    "pet_rabbit_white": B.builder(rabbit, "pet_rabbit_white", 0xECE8E0, 0xFFFFFF),
    "animal_camel": B.builder(camel, "animal_camel", 0xC8A26A),
    "animal_camel_pack": B.builder(camel, "animal_camel_pack", 0xC8A26A, gear="pack"),
    "animal_camel_saddled": B.builder(camel, "animal_camel_saddled", 0xD8C8A0, gear="saddle"),
    "animal_truffle_pig": B.builder(pig, "animal_truffle_pig", 0xE0A8A0),
    "animal_ram": B.builder(ram, "animal_ram", 0xE8E2D4, 0x4A3E36),
    "animal_ram_black": B.builder(ram, "animal_ram_black", 0x3A3632, 0x1E1C1A),
    "animal_hounds_pack": B.builder(hounds, "animal_hounds_pack"),
}
