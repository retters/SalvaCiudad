"""Birds on the Beast body with two legs (_bq.py), all rigid feathers:

- phoenix: a bird of fire with a 6 m wingspan, a crest and long tail plumes;
- giant eagle (a roc): 10 m of wingspan, big enough to carry off a cow;
- parrot on a perch: a pet that talks;
- peacock: its train opens in a fan (the display clip).
Clips: idle, walk, eat (a peck), attack, fly and die; display (peacock) and
talk (parrot, which has no walk: it lives on its perch).
"""

import math

from mathutils import Vector

import _bq as B
from _bq import hull, spike, seg, ball, plate, lump, rock, Pose, X, Y, Z

CZ = 0.3          # Height of the body's center in the unit bird.


def bird(mb, body=(0.11, 0.2, 0.12), neck=((0, -0.14, 0.36), (0, -0.2, 0.47)), neck_r=(0.07, 0.055), head=0.5, hook=1.0,
         wing=((0.09, -0.07, 0.38), (0.3, -0.05, 0.42), (0.78, 0.02, 0.4)), chord=0.24, fold=("flank", 56.0, 74.0, -8.0),
         flap=(34.0, 24.0, -6.0), origin=(0, 0, 0), leg_r=0.014, tail=0.2, tail_n=5, tail_mat="feather_dark", wings=True,
         breast=None):
    q = B.Beast(L=0.3, zs=CZ + 0.04, w=0.055, hl=0.22, fb=0.25, ankle=0.03, toe=0.085, two_legs=0.03, origin=origin)
    lump(mb, q.at(0, 0.0, CZ), body, "feather", "body", seed=3, count=20)
    if breast:
        lump(mb, q.at(0, -body[1] * 0.45, CZ - body[2] * 0.2), (body[0] * 0.85, body[1] * 0.6, body[2] * 0.85), breast, "body",
             seed=5, count=12, tones=False)
    q.legs(mb, leg_r * 2.2, leg_r, "feather", "leg", foot="claw", foot_mat="leg", claw="claw", foot_r=leg_r * 1.8, shoulder=1.6)
    h = q.neck(mb, neck, list(neck_r), ("feather",))
    hp = B.head_beak(mb, h, head, "head", "jaw", hook=hook)
    # Tail: a fan of feathers on one bone.
    a = q.at(0, body[1] * 0.8, CZ + 0.02)
    q.tail_pts = [a, a + Vector((0, tail, -0.04))]
    for i in range(tail_n):
        ang = math.radians((i - (tail_n - 1) / 2) * (60.0 / max(1, tail_n - 1)))
        d = Vector((math.sin(ang), math.cos(ang), -0.18))
        side = Vector((math.cos(ang), -math.sin(ang), 0)) * 0.035
        plate(mb, [a - side, a + side, a + d * tail + side * 1.3, a + d * tail * 1.08, a + d * tail - side * 1.3], 0.012,
              tail_mat if i % 2 == 0 else "feather_shade", "tail.1")
    if wings:
        sh, el, tip = (Vector(p) for p in wing)
        q.wings(sh, el, tip, fold=fold, flap=flap)
        for sx in (1, -1):
            B.wing_feather(mb, sx, q.at(sh.x * sx, sh.y, sh.z), q.at(el.x * sx, el.y, el.z), q.at(tip.x * sx, tip.y, tip.z),
                           chord=chord, thick=0.012, inner_n=4, outer_n=6)
    return q, hp


def bird_colors(feather, dark, beak=0xE8A82A, leg=0xD8A040, eye=0xF2D23A, **more):
    return {**B.shades("feather", feather), **B.palette(feather_dark=dark, beak=beak, leg=leg, claw=0x2A2624, eye=eye, **more)}


WALK = dict(frames=14, duty=0.62, lift=0.035, crouch=0.012, nod=6.0, yaw=3.0, wag=3.0)


def eagle(name, cols, k=6.5):
    mb = B.P.kit.begin()
    q, hp = bird(mb, body=(0.12, 0.21, 0.13), head=0.56, hook=1.3, breast="breast", leg_r=0.017, chord=0.27,
                 neck_r=(0.085, 0.07))
    lump(mb, hp(0, 0.02, 0.0), (0.085, 0.1, 0.085), "head_white", "head", seed=8, count=12, tones=False)
    q.mech()
    q.clips(walk=WALK, jaw=26.0, eat=dict(bend=38.0, head=30.0, body=14.0),
            fly=dict(height=0.5, seconds=1.3, speed=14.0 / k, pitch=4.0, neck=4.0, head=-6.0), wide=0.2, attack_s=1.0)
    B.save(mb, name, cols, q.m, k)


def phoenix(name, cols, k=4.0):
    mb = B.P.kit.begin()
    q, hp = bird(mb, body=(0.1, 0.2, 0.11), neck=((0, -0.14, 0.36), (0, -0.2, 0.47), (0, -0.23, 0.58)),
                 neck_r=(0.06, 0.045, 0.04), head=0.42, hook=0.8, tail=0.3, tail_n=5, tail_mat="fire_b", breast="fire_b",
                 chord=0.26)
    for i in range(3):                                          # A crest of flames.
        spike(mb, hp(0, 0.02 + 0.04 * i, 0.1), hp(0, 0.16 + 0.06 * i, 0.3 - 0.03 * i), 0.03, "fire_c", "head")
    base = q.tail_pts[0]
    for j, x in enumerate((-0.07, 0.0, 0.07)):                  # Three long plumes with an eye of fire at the end.
        pts = [base + Vector((x * 0.5, 0.0, 0)), base + Vector((x * 1.5, 0.3, -0.03)), base + Vector((x * 2.6, 0.62, -0.1)),
               base + Vector((x * 3.4, 0.92, -0.2))]
        for i, (a, b) in enumerate(zip(pts, pts[1:])):
            side = Vector((0.03 + 0.012 * i, 0, 0))
            plate(mb, [a - side, a + side, b + side * 1.3, b - side * 1.3], 0.012, ("fire_a", "fire_b", "fire_c")[i],
                  f"plume{j}.{i + 1}")
        ball(mb, pts[-1], 0.06, "fire_c", f"plume{j}.3", segments=6, rings=4, scale=(1, 1.3, 0.4))
        q.bones += B.chain_bones(f"plume{j}", pts, "tail.1")[0]
    for side, sx in B.SIDES:                                    # Flames along the wings' leading edge.
        sh, el, tip = q.wing[0], q.wing[1], q.wing[2]
        for i in range(4):
            p = el.lerp(tip, i / 4.0)
            spike(mb, Vector((p.x * sx, p.y, p.z + 0.01)), Vector((p.x * sx, p.y + 0.1, p.z + 0.14)), 0.03, "fire_c",
                  f"wing.2.{side}")
    q.mech()

    def plumes(pose, t):
        p = 2 * math.pi * t
        for j in range(3):
            for i in range(3):
                pose.turn(f"plume{j}.{i + 1}", Z, 7.0 * math.sin(p - i * 0.9 + j))
                pose.turn(f"plume{j}.{i + 1}", X, 3.0 + 3.0 * math.sin(2 * p - i * 0.7 + j))
    q.clips(walk=WALK, jaw=22.0, extra_idle=plumes, extra_walk=plumes,
            fly=dict(height=0.6, seconds=1.1, speed=12.0 / k, pitch=4.0, neck=3.0, head=-6.0), wide=0.2)
    B.save(mb, name, cols, q.m, k)


def parrot(name, cols, k=0.8):
    mb = B.P.kit.begin()
    z0 = 1.3 / k
    q, hp = bird(mb, body=(0.1, 0.17, 0.12), head=0.6, hook=1.7, tail=0.34, tail_n=3, tail_mat="tail", breast="breast",
                 origin=(0, 0, z0), neck_r=(0.075, 0.07), chord=0.2,
                 wing=((0.085, -0.06, 0.38), (0.26, -0.04, 0.42), (0.62, 0.02, 0.4)))
    # The perch: a T of wood on a round foot, a feeding cup at one end.
    mb.cylinder((0, 0.02, 0.0), (0, 0.02, 0.05), 0.3, 0.24, "wood_dark", segments=10)
    mb.cylinder((0, 0.02, 0.05), (0, 0.02, z0 - 0.04), 0.035, 0.03, "wood", segments=7)
    mb.cylinder((-0.42, 0.0, z0 - 0.026), (0.42, 0.0, z0 - 0.026), 0.026, 0.026, "wood", segments=7)
    mb.cylinder((0.36, 0.0, z0 - 0.01), (0.36, 0.0, z0 + 0.07), 0.05, 0.065, "iron", segments=8)
    mb.cylinder((0.36, 0.0, z0 + 0.05), (0.36, 0.0, z0 + 0.075), 0.055, 0.055, "seed", segments=8)
    m = B.pack([q], walk=WALK, jaw=30.0, eat=dict(bend=30.0, head=26.0, body=10.0), skip=("walk",),
               fly=dict(height=0.5, seconds=0.5, speed=6.0 / k, pitch=6.0, neck=3.0, head=-6.0), wide=0.2)

    def talk(t):
        p = 2 * math.pi * t
        pose = Pose(m)
        q.stand(pose)
        q.folded(pose)
        beat = abs(math.sin(4 * p))
        q.neck_pose(pose, -8.0 + 10.0 * math.sin(2 * p), 14.0 * math.sin(p), head=-6.0 * beat, jaw=34.0 * beat)
        pose.turn("tail.1", X, 6.0 * math.sin(2 * p))
        return B.P.from_pose(pose)
    m.clip("talk", 2.0, talk)
    B.save(mb, name, cols, m, k)


def peacock(name, cols, k=2.3):
    mb = B.P.kit.begin()
    q, hp = bird(mb, body=(0.1, 0.19, 0.11), neck=((0, -0.14, 0.36), (0, -0.2, 0.48), (0, -0.22, 0.6)),
                 neck_r=(0.055, 0.04, 0.034), head=0.34, hook=0.4, tail=0.12, tail_n=3, wings=False)
    for i in range(5):                                          # The crest: a little fan of pins.
        x = (i - 2) * 0.012
        seg(mb, hp(x, 0.0, 0.035), hp(x * 2.2, 0.03, 0.085), 0.002, 0.002, "eye_spot", "head", sides=3)
        ball(mb, hp(x * 2.2, 0.03, 0.09), 0.006, "eye_spot", "head", segments=4, rings=3)
    for sx in (-1, 1):                                          # Folded wings, brown.
        lump(mb, q.at(sx * 0.09, 0.03, CZ + 0.02), (0.035, 0.15, 0.075), "wing", "body", seed=6 + sx, count=10, tones=False)
    # The train: nine long feathers, each on its bone, trailing behind.
    base = q.at(0, 0.14, CZ + 0.05)
    n = 9
    for i in range(n):
        u = (i - (n - 1) / 2) / ((n - 1) / 2)                   # -1..1 across the fan.
        ln = 0.62 - 0.1 * abs(u)
        d = Vector((u * 0.16, 1.0, -0.3)).normalized()
        tip = base + d * ln
        side = Vector((1, 0, 0)) * 0.022
        bone = f"train.{i + 1}"
        plate(mb, [base - side, base + side, tip + side * 1.2, tip - side * 1.2], 0.008, "train", bone)
        up = Vector((0, 0.05, 0.012))
        mb.cylinder(tip - d * 0.06 + up * 0.0, tip - d * 0.06 + Vector((0, 0, 0.012)), 0.05, 0.05, "eye_ring",
                    weights={bone: 1.0}, segments=7)
        mb.cylinder(tip - d * 0.06, tip - d * 0.06 + Vector((0, 0, 0.018)), 0.026, 0.026, "eye_spot", weights={bone: 1.0},
                    segments=6)
        q.bones.append((bone, tuple(base), tuple(tip), "body"))
    q.mech()

    def train(amount):
        def fn(pose, t):
            p = 2 * math.pi * t
            for i in range(n):
                u = (i - (n - 1) / 2) / ((n - 1) / 2)
                bone = f"train.{i + 1}"
                pose.turn(bone, Z, 2.0 * math.sin(p + i))
                a = amount(t)
                if a:
                    shimmer = 2.5 * math.sin(10 * p + i) * a
                    pose.turn(bone, Z, 9.0 * u * a)             # Undo the rest fan before raising.
                    pose.turn(bone, X, (100.0 + shimmer) * a)
                    pose.turn(bone, Y, 78.0 * u * a)
        return fn
    still = train(lambda t: 0.0)
    q.clips(walk=dict(WALK, frames=18), jaw=14.0, eat=dict(bend=30.0, head=26.0, body=12.0), extra_idle=still,
            extra_walk=still, wide=0.2)
    show = train(lambda t: B.pulse(t, 0.05, 0.3, 0.8, 0.97))

    def display(t):
        p = 2 * math.pi * t
        pose = Pose(q.m, (0, 0, -0.003))
        q.stand(pose)
        q.neck_pose(pose, -4.0 * B.pulse(t, 0.05, 0.3, 0.8, 0.97), 6.0 * math.sin(p), head=4.0)
        pose.turn("body", Z, 5.0 * math.sin(p) * B.pulse(t, 0.2, 0.3, 0.8, 0.9))
        show(pose, t)
        return B.P.from_pose(pose)
    q.m.clip("display", 5.0, display)
    B.save(mb, name, cols, q.m, k)


MODELS = {
    "mythic_phoenix": B.builder(phoenix, "mythic_phoenix",
                                bird_colors(0xE8501E, 0x9A2A1A, beak=0xFFD24A, leg=0xFFB03A, eye=0xFFFFFF, fire_a=0xE8501E,
                                            fire_b=0xFF9A2A, fire_c=0xFFE27A)),
    "boss_giant_eagle": B.builder(eagle, "boss_giant_eagle",
                                  bird_colors(0x6A4A32, 0x3A2A20, breast=0x8A6A4A, head_white=0xF2EEE6)),
    "pet_parrot_perch": B.builder(parrot, "pet_parrot_perch",
                                  bird_colors(0xD8342A, 0x2A52B8, beak=0x2A2624, leg=0x6A6A6A, eye=0xF6F2E8, breast=0xF2C83A,
                                              tail=0x2A52B8, wood=0x8A6038, wood_dark=0x5A3E28, iron=0x8A8F96, seed=0xD8C070)),
    "pet_parrot_perch_green": B.builder(parrot, "pet_parrot_perch_green",
                                        bird_colors(0x4EA83A, 0x2A6A8A, beak=0xE8A82A, leg=0x6A6A6A, eye=0xF6F2E8,
                                                    breast=0xF2D83A, tail=0xD8342A, wood=0x8A6038, wood_dark=0x5A3E28,
                                                    iron=0x8A8F96, seed=0xD8C070)),
    "animal_peacock": B.builder(peacock, "animal_peacock",
                                bird_colors(0x1E5AC8, 0x3A7A4A, beak=0xD8D0C0, leg=0x8A8070, eye=0x101010, wing=0x8A6A4A,
                                            train=0x2E8A5A, eye_ring=0xD8B83A, eye_spot=0x2A3AC8)),
}
