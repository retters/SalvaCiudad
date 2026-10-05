"""Extras made once the family's list was complete:

- mammoth: a shaggy pack beast 3.6 m tall with curved tusks and a trunk of
  five bones that sways; plain or loaded with crates;
- spirit fox: a white fox with nine tails tipped with light, each tail on
  its own bones (a red one tipped with fire is the variant);
- will-o'-the-wisp: a floating flame with four sparks that orbit it.
"""

import math

from mathutils import Vector

import _bq as B
from _bq import hull, spike, seg, ball, plate, lump, rock, X, Y, Z

TAU = 2 * math.pi


def mammoth(name, gear=None, k=1.0):
    mb = B.P.kit.begin()
    q = B.Beast(L=2.0, zs=2.85, w=0.55, hl=2.0, fb=-0.07, hb=0.1, ankle=0.3, toe=0.15)
    q.trunk(mb, "fur", (0.95, 1.1, 1.15), (0.9, 1.2, 1.0), (0.8, 0.95, 0.92))
    lump(mb, (0, -0.75, 3.35), (0.6, 0.6, 0.5), "fur", "body", seed=12, count=14)                   # The hump of the withers.
    q.legs(mb, 0.36, 0.3, "fur", "fur_shade", foot="pad", foot_mat="skin", claw="tusk", foot_r=0.34, shoulder=1.3)
    h = q.neck(mb, [(0, -1.25, 2.85), (0, -1.75, 3.1)], [0.78, 0.64], ("fur",))

    def hp(x, y, z):
        return h + Vector((x, y, z))
    lump(mb, hp(0, -0.4, 0.1), (0.56, 0.62, 0.7), "fur", "head", seed=5, count=18)
    lump(mb, hp(0, -0.3, 0.7), (0.4, 0.42, 0.34), "fur", "head", seed=6, count=12)                 # The domed crown.
    for sx in (-1, 1):
        ball(mb, hp(sx * 0.47, -0.72, 0.12), 0.06, "eye", "head", segments=5, rings=3)
        plate(mb, [hp(sx * 0.5, -0.2, 0.4), hp(sx * 0.52, -0.1, -0.2), hp(sx * 0.95, 0.15, -0.1), hp(sx * 0.9, 0.1, 0.4)], 0.07,
              "fur_shade", "head")                                                                 # Small ears.
        B.horn(mb, hp(sx * 0.3, -0.75, -0.4), [hp(sx * 0.5, -1.2, -1.15), hp(sx * 0.52, -1.9, -1.4), hp(sx * 0.35, -2.5, -1.05),
                                               hp(sx * 0.12, -2.75, -0.45)], 0.15, "tusk", "head", sides=6)
        for i in range(6):                                      # A skirt of long hair along the flanks.
            y = -0.9 + i * 0.36
            plate(mb, [(sx * 0.93, y - 0.2, 2.0), (sx * 0.93, y + 0.2, 2.0), (sx * 0.86, y + 0.05, 1.2 + 0.12 * (i % 2))], 0.1,
                  "fur_shade", "body")
    trunk = [hp(0, -0.9, -0.25), hp(0, -1.12, -0.8), hp(0, -1.2, -1.3), hp(0, -1.18, -1.75), hp(0, -1.06, -2.1),
             hp(0, -0.88, -2.3)]
    B.chain(mb, "trunk", trunk, [0.27, 0.22, 0.18, 0.14, 0.11, 0.09], ("fur_shade", "fur"), sides=7)
    q.bones += B.chain_bones("trunk", trunk, "head")[0]
    q.tail(mb, [(0, 1.42, 2.7), (0, 1.56, 2.3), (0, 1.58, 1.9)], [0.09, 0.07, 0.1], ("fur_shade",))
    if gear:
        top = 3.35
        hull(mb, [(sx * x, y, z) for sx in (-1, 1) for x, z in ((1.0, 2.3), (0.9, 3.2), (0.3, top + 0.35))
                  for y in (-0.5, 1.0)], "cloth", "body")
        for sx in (-1, 1):
            B.box(mb, (sx * 1.2, 0.25, 2.75), (0.5, 0.9, 0.6), "wood", "body")
            B.box(mb, (sx * 1.2, 0.25, 3.12), (0.44, 0.5, 0.16), "wood_dark", "body")
            seg(mb, (sx * 1.0, -0.1, 3.05), (sx * 0.3, -0.1, top + 0.4), 0.03, 0.03, "rope", "body", sides=4)
            seg(mb, (sx * 1.0, 0.6, 3.05), (sx * 0.3, 0.6, top + 0.4), 0.03, 0.03, "rope", "body", sides=4)
        rock(mb, (0, 0.25, top + 0.55), (0.55, 0.7, 0.28), "sack", "body", count=14, seed=5)
    q.mech()

    def sway(pose, t):
        p = TAU * t
        for i in range(5):
            pose.turn(f"trunk.{i + 1}", Z, 5.0 * math.sin(p - i * 0.8))
            pose.turn(f"trunk.{i + 1}", X, -5.0 - 2.0 * math.sin(2 * p - i * 0.6))      # Only curls forward and up.
    # (The run, a heavy trot, is for the game: every animal of its fauna has one.)
    q.clips(walk=dict(frames=40, duty=0.7, lift=0.2, crouch=0.08, nod=1.5, wag=4.0, yaw=1.0), run=dict(frames=26, lift=0.3),
            attack="gore", attack_s=1.8,
            die_s=2.6, wide=1.8, extra_idle=sway, extra_walk=sway, eat=dict(bend=4.0, head=6.0, body=1.0), idle_look=3.0)

    def curl(pose, t):
        # The trunk curls up out of the way when the head goes down to gore.
        hit = max(B.pulse(t, 0.0, 0.32, 0.38, 0.47) * 0.5, B.pulse(t, 0.38, 0.47, 0.56, 0.95))
        for i in range(5):
            pose.turn(f"trunk.{i + 1}", X, -28.0 * hit)
    B.extend(q.m, "attack", curl)
    cols = {**B.shades("fur", 0x6A4A36), **B.palette(skin=0x5A4A42, tusk=0xEFE6CC, eye=0x151012, cloth=0x3A5A8A, wood=0x8A6038,
                                                     wood_dark=0x5A3E28, rope=0xC8B078, sack=0xD8C8A0)}
    B.save(mb, name, cols, q.m, k)


def spirit_fox(name, fur, tip, k=1.6):
    mb = B.P.kit.begin()
    q = B.Beast(L=0.55, zs=0.5, w=0.07, hl=0.38, fb=0.16, hb=-0.2, ankle=0.04, toe=0.06)
    q.trunk(mb, "fur", (0.12, 0.2, 0.15), (0.095, 0.2, 0.11), (0.105, 0.17, 0.13))
    q.legs(mb, 0.042, 0.022, "fur", "sock", foot="paw", foot_r=0.027)
    h = q.neck(mb, [(0, -0.25, 0.55), (0, -0.38, 0.7)], [0.09, 0.07], ("fur",))
    hp = B.head_muzzle(mb, h, 0.85, "head", "jaw", skull=(0.09, 0.11, 0.085), mz=(0.17, 0.028, 0.055, 0.03), ears="up", ear=1.3,
                       mat="fur", mat2="fur_shade", ear_mat="sock", eye="glow", eye_r=0.016)
    lump(mb, (0, -0.3, 0.46), (0.09, 0.1, 0.12), "ruff", "body", seed=6, count=10, tones=False)
    ball(mb, hp(0, -0.06, 0.1), 0.02, "glow", "head", segments=5, rings=3)                         # A mark on the brow.
    base = Vector((0, 0.27, 0.52))
    tails = 9
    for j in range(tails):
        a = math.radians((j - (tails - 1) / 2) * 15.0)
        d = Vector((math.sin(a) * 1.1, math.cos(a) * 0.75, 0.62 - 0.2 * abs(math.sin(a)))).normalized()
        pts = [base, base + d * 0.2 + Vector((0, 0, -0.02)), base + d * 0.42, base + d * 0.6]
        name_ = "tail" if j == (tails - 1) // 2 else f"tail{j}"
        B.chain(mb, name_, pts, [0.03, 0.065, 0.06, 0.012], ("fur", "fur", "glow"), sides=6)
        if name_ == "tail":
            q.tail_pts = pts
        else:
            q.bones += B.chain_bones(name_, pts, "body")[0]
    q.mech()

    def fan(pose, t):
        p = TAU * t
        for j in range(tails):
            if j == (tails - 1) // 2:
                continue
            for i in range(3):
                pose.turn(f"tail{j}.{i + 1}", Z, 6.0 * math.sin(p - i * 0.8 + j * 0.7))
                pose.turn(f"tail{j}.{i + 1}", X, 3.0 + 3.0 * math.sin(2 * p - i * 0.6 + j))
    q.clips(walk=dict(frames=16, duty=0.62, lift=0.05, crouch=0.025, nod=3.0, wag=8.0), run=dict(frames=10, lift=0.08),
            jaw=26.0, wide=0.25, attack_s=0.9, extra_idle=fan, extra_walk=fan, idle_look=8.0)
    cols = {**B.shades("fur", fur), **B.palette(sock=B.mix(fur, 0x000000, 0.55), ruff=B.mix(fur, 0xFFFFFF, 0.6), glow=tip,
                                                nose=0x1E1A1A, eye=0x151012)}
    B.save(mb, name, cols, q.m, k)


def wisp(name, core, mid, spark):
    mb = B.P.kit.begin()
    c = Vector((0, 0, 1.1))
    rock(mb, c, (0.16, 0.16, 0.2), "core", "flame", count=12, seed=3, jitter=0.15)
    for i in range(5):
        a = i * 1.3
        spike(mb, c + Vector((math.cos(a) * 0.08, math.sin(a) * 0.08, 0.1)),
              c + Vector((math.cos(a) * 0.12, math.sin(a) * 0.12, 0.42 + 0.08 * (i % 2))), 0.07, "mid", "flame", sides=4)
    for i in range(6):                                          # A ring of shards that turns the other way.
        a = i * TAU / 6
        d = Vector((math.cos(a), math.sin(a), 0.0))
        spike(mb, c + d * 0.2 + Vector((0, 0, -0.05)), c + d * 0.34 + Vector((0, 0, 0.05)), 0.035, "halo", "halo", sides=3)
    spike(mb, c + Vector((0, 0, -0.15)), c + Vector((0, 0.1, -0.6)), 0.1, "mid", "flame", sides=5)       # A wisp of a tail.
    bones = [("flame", tuple(c), tuple(c + Vector((0, 0, 0.3))), None), ("halo", tuple(c), tuple(c + Vector((0, 0, 0.3))), "flame")]
    sparks = []
    for i in range(4):
        a = i * TAU / 4
        p = c + Vector((math.cos(a) * 0.45, math.sin(a) * 0.45, 0.15 * math.sin(a * 2 + 1)))
        rock(mb, p, (0.05, 0.05, 0.07), "spark", f"spark.{i + 1}", count=8, seed=10 + i, jitter=0.2)
        bones.append((f"spark.{i + 1}", tuple(p), tuple(p + Vector((0, 0, 0.1))), "flame"))
        sparks.append((p - c, a))
    m = B.P.kit.Mech(bones)

    def pose(t, lean=0.0, fade=0.0):
        p = TAU * t
        turns = {"flame": [(Z, 20.0 * math.sin(p)), (X, lean)], "halo": [(Z, -360.0 * t)]}
        moves = {"root": (0.05 * math.sin(p), 0.0, 0.08 * math.sin(2 * p) - 1.0 * fade)}
        for i, (rest, a) in enumerate(sparks):
            ang = a + p
            now = Vector((math.cos(ang) * 0.45 * (1 - fade), math.sin(ang) * 0.45 * (1 - fade),
                          0.15 * math.sin(ang * 2 + 1) - 0.3 * fade))
            moves[f"spark.{i + 1}"] = tuple(now - rest)
        return turns, moves
    m.clip("idle", 3.0, lambda t: pose(t))
    m.clip("fly", 2.0, lambda t: pose(t, lean=-14.0), speed=1.5)
    m.clip("die", 1.6, lambda t: pose(t * 0.5, fade=B.smooth(t)), loops=False)
    B.save(mb, name, B.palette(core=core, mid=mid, halo=mid, spark=spark), m)


MODELS = {
    "animal_mammoth": B.builder(mammoth, "animal_mammoth"),
    "animal_mammoth_pack": B.builder(mammoth, "animal_mammoth_pack", gear="pack"),
    "spirit_fox_nine_tails": B.builder(spirit_fox, "spirit_fox_nine_tails", 0xECEFF2, 0x7AD8FF),
    "spirit_fox_fire": B.builder(spirit_fox, "spirit_fox_fire", 0xD8642A, 0xFFE27A),
    "spirit_wisp": B.builder(wisp, "spirit_wisp", 0xE8FFF6, 0x6AE8C8, 0xC8FFE8),
    "spirit_wisp_ember": B.builder(wisp, "spirit_wisp_ember", 0xFFF2C0, 0xFF9A2A, 0xFFD24A),
}
