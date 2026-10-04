"""Mythic four-legged beasts on the Beast body (_bq.py):

- horse kind: unicorn (a glowing horn), nightmare (a black unicorn with a
  mane of fire), pegasus (feathered wings, with a fly clip) and pony (small,
  plain or saddled);
- lion kind: griffin (an eagle's head, wings and talons), manticore (bat
  wings and a scorpion's tail) and chimera (a lion's and a goat's head, a
  snake for a tail, fire breath);
- cerberus: a three-headed black hound 2.3 m tall;
- hydra with three or five heads on long necks;
- forest spirit: a great white stag with glowing antlers.
Clips: idle, walk, run (the fast ones), eat (the grazers), attack, breath
(the chimera), fly (the winged) and die.
"""

import math

from mathutils import Vector

import _bq as B
from _bq import hull, spike, seg, ball, plate, lump, rock

# ---------------------------------------------------------------- horse kind


def horse_colors(coat, hair, glow=0xFFE9A8, eye=0x151012, **more):
    return {**B.shades("coat", coat), **B.shades("feather", more.pop("feather", 0xF4F1EA)),
            **B.palette(hair=hair, hoof=0x2A2624, eye=eye, nose=B.mix(coat, 0x000000, 0.45), glow=glow,
                        feather_dark=more.pop("feather_dark", 0xB8C4D2), leather=0x7A4A2E, leather_dark=0x4E3020,
                        cloth=more.pop("cloth", 0xA83A2E), iron=0x8A8F96, sack=0xD8C8A0, **more)}


def horse(name, cols, k=1.0, horn=False, wings=False, pony=False, gear=None, flame=False):
    mb = B.P.kit.begin()
    hl = 0.82 if pony else 1.12
    dz = hl - 1.12
    fat = 1.15 if pony else 1.0
    q = B.Beast(L=1.0 if pony else 1.15, zs=1.42 + dz, w=0.19 * fat, hl=hl, fb=-0.1, hb=0.16, ankle=0.11, toe=0.1)
    q.trunk(mb, "coat", (0.29 * fat, 0.42, 0.36), (0.28 * fat, 0.5, 0.33 * fat), (0.29 * fat, 0.42, 0.35))
    q.legs(mb, 0.1 * fat, 0.05 * fat, "coat", "coat_shade", foot="hoof", foot_mat="hoof", foot_r=0.065 * fat, hind=1.1)
    y0 = -q.L / 2
    if pony:
        neck = [(0, y0 + 0.05, 1.5 + dz), (0, y0 - 0.2, 1.78 + dz), (0, y0 - 0.36, 1.98 + dz)]
    else:
        neck = [(0, y0 + 0.03, 1.5), (0, y0 - 0.24, 1.86), (0, y0 - 0.44, 2.16)]
    radii = [0.25 * fat, 0.18 * fat, 0.13 * fat]
    h = q.neck(mb, neck, radii, ("coat",))
    s = 1.12 if pony else 1.0
    hp = B.head_muzzle(mb, h, s, "head", "jaw", skull=(0.1, 0.13, 0.11), mz=(0.36, 0.055, 0.1, 0.2), ears="up", ear=0.8,
                       mat="coat", mat2="coat_shade")
    mane_mat = "glow" if flame else "hair"
    B.mane(mb, "neck", q.necks[0][1], radii, mane_mat, 0.2 if not flame else 0.3, thick=0.06)
    plate(mb, [hp(-0.03, 0.05, 0.1), hp(0.03, 0.05, 0.1), hp(0.0, -0.17, 0.0)], 0.05, mane_mat, "head")     # Forelock.
    top = 1.42 + dz
    tail = q.tail(mb, [(0, q.L / 2 + 0.05, top + 0.02), (0, q.L / 2 + 0.27, top - 0.1), (0, q.L / 2 + 0.36, top - 0.5),
                       (0, q.L / 2 + 0.34, top - 0.95)], [0.06, 0.1, 0.09, 0.03], (mane_mat,))
    if flame:
        for i, (a, b) in enumerate(zip(q.necks[0][1], q.necks[0][1][1:])):
            spike(mb, b + Vector((0, 0.12, 0.1)), b + Vector((0, 0.3, 0.5)), 0.08, "fire", f"neck.{i + 1}")
        for leg, sx, end in B.LEGS:
            a = q.points[leg][2]
            for j in range(3):
                ang = j * 2.1
                spike(mb, a + Vector((math.cos(ang) * 0.05, math.sin(ang) * 0.05, 0.02)),
                      a + Vector((math.cos(ang) * 0.09, math.sin(ang) * 0.09 + 0.05, 0.24)), 0.035, "fire", f"leg_low.{leg}")
    if horn:
        B.horn(mb, hp(0, -0.1, 0.09), [hp(0, -0.2, 0.3), hp(0, -0.3, 0.52), hp(0, -0.38, 0.7)], 0.035, "glow", "head", sides=6)
    if wings:
        sh, el, tip = Vector((0.2, y0 + 0.2, 1.62)), Vector((0.95, y0 + 0.25, 2.05)), Vector((2.7, y0 + 0.5, 1.95))
        q.wings(sh, el, tip, fold=("flank", 66.0, 70.0, -6.0), flap=(30.0, 22.0, -8.0))
        for sx in (1, -1):
            B.wing_feather(mb, sx, Vector((sh.x * sx, sh.y, sh.z)), Vector((el.x * sx, el.y, el.z)),
                           Vector((tip.x * sx, tip.y, tip.z)), chord=0.85)
    if gear:
        w = 0.3 * fat
        hull(mb, [(sx * x, y, top + z) for sx in (-1, 1) for x, z in ((w * 1.02, -0.2), (w * 0.9, 0.0), (0.1, 0.07))
                  for y in (-0.25, 0.3)], "cloth", "body")
        if gear == "saddle":
            hull(mb, [(sx * 0.17, y, top + z) for sx in (-1, 1) for y, z in ((-0.2, 0.08), (-0.24, 0.2), (0.2, 0.08),
                                                                            (0.27, 0.22), (0.0, 0.1))], "leather", "body")
            for sx in (-1, 1):
                bar_a = Vector((sx * w * 1.05, -0.02, top - 0.05))
                seg(mb, bar_a, bar_a + Vector((0, 0, -0.42)), 0.012, 0.012, "leather_dark", "body", sides=4)
                mb.cylinder(bar_a + Vector((-0.04 * sx, 0, -0.47)), bar_a + Vector((0.04 * sx, 0, -0.47)), 0.05, 0.05, "iron",
                            weights={"body": 1.0}, segments=6)
        else:
            for sx in (-1, 1):
                rock(mb, (sx * (w + 0.12), 0.03, top - 0.12), (0.13, 0.26, 0.2), "sack", "body", count=12, seed=3 + sx)
            rock(mb, (0, 0.03, top + 0.16), (0.2, 0.24, 0.1), "sack", "body", count=12, seed=8)
    q.mech()
    q.clips(walk=dict(frames=24, duty=0.64, lift=0.12, crouch=0.05, nod=3.0, wag=5.0),
            run=dict(frames=13, duty=0.4, lift=0.2, crouch=0.09), attack="gore" if horn else "bite", jaw=10.0,
            eat=dict(bend=30.0 if not pony else 34.0, head=-8.0),
            fly=dict(height=1.2, seconds=0.9, speed=10.0, pitch=4.0, neck=6.0, head=-10.0, tuck=0.8) if wings else None,
            wide=0.6)
    B.save(mb, name, cols, q.m, k)


# ----------------------------------------------------------------- lion kind

def lion_colors(fur, mane, **more):
    return {**B.shades("fur", fur), **B.shades("mane", mane), **B.shades("feather", more.pop("feather", 0xE9E2D0)),
            **B.palette(eye=more.pop("eye", 0xF2C83A), nose=0x2A2020, tooth=0xF2EAD0, horn=0x2E2A28, claw=0x2A2624,
                        beak=0xE8A82A, feather_dark=more.pop("feather_dark", 0x6A4A2E), membrane=0x7A2A22, mouth=0x6A1A20,
                        fire_a=0xE8501E, fire_b=0xFF9A2A, fire_c=0xFFE27A, **more)}


NECK_L = [(0, -0.6, 1.2), (0, -0.82, 1.42), (0, -1.0, 1.56)]
NECK_LR = [0.31, 0.26, 0.21]


def lion_base(mb, front_claw=None, claw="claw"):
    q = B.Beast(L=1.3, zs=1.12, w=0.24, hl=0.9, fb=0.18, hb=-0.22, ankle=0.1, toe=0.2)
    q.trunk(mb, "fur", (0.34, 0.5, 0.4), (0.27, 0.5, 0.31), (0.3, 0.42, 0.36))
    q.legs(mb, 0.14, 0.085, "fur", "fur_shade", foot="paw", foot_r=0.11, hind=1.05, front_claw=front_claw, claw=claw)
    return q


def lion_head(mb, h, s=1.0, bone="head", jaw="jaw", maned=True, mat="fur"):
    hp = B.head_muzzle(mb, h, s, bone, jaw, skull=(0.17, 0.19, 0.17), mz=(0.2, 0.085, 0.15, 0.03), ears="round",
                       ear=1.2, mat=mat, mat2=mat + "_shade", teeth="tooth", eye_r=0.026)
    if maned:
        for i in range(11):                                     # A ruff of spikes around the face.
            ang = math.radians(-50 + i * 28)
            d = Vector((math.cos(ang), 0.0, math.sin(ang)))
            spike(mb, hp(d.x * 0.14, 0.02, d.z * 0.14), hp(d.x * 0.36, 0.22, d.z * 0.36 + 0.02), 0.09 * s, "mane", bone, sides=5)
    return hp


def lion_tail(q, mb, mat="fur", tuft="mane"):
    pts = q.tail(mb, [(0, 0.66, 1.1), (0, 0.95, 1.0), (0, 1.2, 0.8), (0, 1.38, 0.62), (0, 1.5, 0.6)],
                 [0.06, 0.05, 0.045, 0.04, 0.035], (mat,))
    rock(mb, pts[-1] + Vector((0, 0.07, 0.0)), (0.08, 0.13, 0.08), tuft, "tail.4", count=10, seed=3)


def griffin(name, cols, k=1.5):
    mb = B.P.kit.begin()
    q = lion_base(mb, front_claw="talon", claw="beak")
    lump(mb, (0, -0.52, 1.08), (0.36, 0.42, 0.44), "feather", "body", seed=9, count=18)        # A feathered breast.
    h = q.neck(mb, NECK_L, [0.3, 0.24, 0.19], ("feather", "feather_shade"))
    hp = B.head_beak(mb, h, 1.7, "head", "jaw", hook=1.2)
    for sx in (-1, 1):                                          # Ear tufts.
        spike(mb, hp(sx * 0.08, 0.06, 0.09), hp(sx * 0.14, 0.2, 0.26), 0.05, "feather_dark", "head")
    B.crest(mb, "neck", q.necks[0][1], [0.3, 0.24, 0.19], "feather_dark", 0.14, per=2, width=0.9)
    lion_tail(q, mb)
    sh, el, tip = Vector((0.26, -0.4, 1.3)), Vector((1.05, -0.35, 1.7)), Vector((2.5, -0.15, 1.6))
    q.wings(sh, el, tip, fold=("flank", 66.0, 70.0, -6.0), flap=(30.0, 22.0, -8.0))
    for sx in (1, -1):
        B.wing_feather(mb, sx, Vector((sh.x * sx, sh.y, sh.z)), Vector((el.x * sx, el.y, el.z)),
                       Vector((tip.x * sx, tip.y, tip.z)), chord=0.8)
    q.mech()
    q.clips(walk=dict(frames=26, duty=0.66, lift=0.1, crouch=0.06), run=dict(frames=12), jaw=24.0,
            fly=dict(height=1.0, seconds=0.9, speed=11.0, pitch=5.0, neck=6.0, head=-12.0), wide=0.7)
    B.save(mb, name, cols, q.m, k)


def manticore(name, cols, k=1.45):
    mb = B.P.kit.begin()
    q = lion_base(mb)
    h = q.neck(mb, NECK_L, NECK_LR, ("fur",))
    hp = lion_head(mb, h, 1.05)
    hull(mb, [hp(-0.05, -0.2, -0.16), hp(0.05, -0.2, -0.16), hp(0, -0.24, -0.34), hp(0, -0.12, -0.2)], "mane", "jaw")  # Beard.
    for sx in (-1, 1):
        spike(mb, hp(sx * 0.1, 0.0, 0.14), hp(sx * 0.2, 0.1, 0.36), 0.035, "horn", "head")
    tail = [(0, 0.66, 1.15), (0, 1.1, 1.3), (0, 1.5, 1.7), (0, 1.62, 2.25), (0, 1.38, 2.72), (0, 0.95, 2.9)]
    radii = [0.11, 0.12, 0.125, 0.12, 0.11, 0.1]
    pts = q.tail(mb, tail, radii, ("chitin", "chitin_dark"), sides=6)
    rock(mb, pts[-1] + Vector((0, -0.08, 0.0)), (0.15, 0.2, 0.15), "chitin", "tail.5", count=10, seed=4)
    B.horn(mb, pts[-1] + Vector((0, -0.2, 0.0)), [pts[-1] + Vector((0, -0.42, -0.06)), pts[-1] + Vector((0, -0.56, -0.26))],
           0.07, "horn", "tail.5")
    sh, el, tip = Vector((0.26, -0.35, 1.3)), Vector((1.0, -0.3, 1.75)), Vector((2.4, -0.1, 1.6))
    q.wings(sh, el, tip, fold=(34.0, 80.0, 18.0), flap=(28.0, 20.0, -10.0))
    for sx in (1, -1):
        B.wing_membrane(mb, sx, Vector((sh.x * sx, sh.y, sh.z)), Vector((el.x * sx, el.y, el.z)),
                        Vector((tip.x * sx, tip.y, tip.z)), Vector((0.18 * sx, 0.45, 1.2)), arm="fur", dark="fur_shade",
                        claw="horn", r=0.08, chord=1.1)
    q.mech()

    def sting(pose, t):
        # The tail strikes over the head with every bite.
        hit = B.pulse(t, 0.4, 0.5, 0.58, 0.9)
        for i in range(5):
            pose.turn(f"tail.{i + 1}", B.X, -9.0 * hit)
    q.clips(walk=dict(frames=26, duty=0.66, lift=0.1, crouch=0.06), run=dict(frames=12), jaw=30.0,
            fly=dict(height=1.0, seconds=0.9, speed=9.0, pitch=5.0, neck=6.0, head=-12.0, tail=0.0), wide=0.7)
    m = q.m
    base = dict((c[0], c) for c in m.clips())["attack"][3]
    m._clips = [c if c[0] != "attack" else (c[0], c[1], c[2], with_extra(q, base, sting), c[4]) for c in m._clips]
    B.save(mb, name, cols, q.m, k)


def with_extra(q, base, extra):
    """Wraps a clip of (turns, moves) adding turns worked out on a Pose."""
    def fn(t):
        turns, moves = base(t)
        pose = B.Pose(q.m)
        extra(pose, t)
        for bone, quat in pose.q.items():
            turns[bone] = turns.get(bone, []) + B.P.aa(quat)
        return turns, moves
    return fn


def chimera(name, cols, k=1.45):
    mb = B.P.kit.begin()
    q = lion_base(mb)
    h = q.neck(mb, NECK_L, NECK_LR, ("fur",))
    lion_head(mb, h, 1.05)
    # The goat's neck and head rise from the back.
    gneck = [(0.08, -0.1, 1.3), (0.12, -0.25, 1.62), (0.14, -0.42, 1.9)]
    gh = q.neck(mb, gneck, [0.17, 0.13, 0.1], ("goat",), prefix="goat_")
    ghp = B.head_muzzle(mb, gh, 0.9, "goat_head", "goat_jaw", skull=(0.1, 0.13, 0.11), mz=(0.24, 0.05, 0.09, 0.1),
                        ears="side", mat="goat", mat2="goat_shade", eye="goat_eye")
    for sx in (-1, 1):
        B.horn(mb, ghp(sx * 0.05, 0.02, 0.09), [ghp(sx * 0.09, 0.14, 0.3), ghp(sx * 0.14, 0.32, 0.4), ghp(sx * 0.2, 0.46, 0.36)],
               0.04, "horn", "goat_head")
    spike(mb, ghp(0, -0.3, -0.16), ghp(0, -0.26, -0.36), 0.035, "goat_shade", "goat_jaw")       # Beard.
    # The tail is a snake.
    tail = [(0, 0.66, 1.1), (0, 1.05, 1.15), (0, 1.4, 1.35), (0, 1.62, 1.7), (0, 1.6, 2.1), (0, 1.36, 2.36)]
    pts = q.tail(mb, tail, [0.1, 0.095, 0.09, 0.085, 0.08, 0.075], ("snake", "snake_dark"))
    t = pts[-1]
    hull(mb, [t + Vector(o) for o in ((-0.09, 0.05, 0.05), (0.09, 0.05, 0.05), (-0.09, 0.05, -0.05), (0.09, 0.05, -0.05),
                                      (-0.06, -0.26, 0.02), (0.06, -0.26, 0.02), (-0.05, -0.25, -0.05), (0.05, -0.25, -0.05),
                                      (0, -0.12, 0.08))], "snake", "tail.5")
    for sx in (-1, 1):
        ball(mb, t + Vector((sx * 0.075, -0.1, 0.045)), 0.022, "goat_eye", "tail.5", segments=5, rings=3)
        spike(mb, t + Vector((sx * 0.035, -0.24, -0.04)), t + Vector((sx * 0.035, -0.25, -0.12)), 0.012, "tooth", "tail.5")
    q.fire(mb, (0, -0.45, 1.0), n=5, r0=0.12, r1=0.3)
    q.mech()
    q.clips(walk=dict(frames=26, duty=0.66, lift=0.1, crouch=0.06), run=dict(frames=12), jaw=30.0,
            breath=dict(seconds=2.4), wide=0.7)
    B.save(mb, name, cols, q.m, k)


# ------------------------------------------------------------------ cerberus

def wolf_head(mb, h, s, bone, jaw, mat="fur", ears="up", eye="eye"):
    return B.head_muzzle(mb, h, s, bone, jaw, skull=(0.115, 0.14, 0.11), mz=(0.24, 0.045, 0.085, 0.03), ears=ears, ear=1.0,
                         mat=mat, mat2=mat + "_shade", teeth="tooth", eye=eye)


def cerberus(name, cols, k=2.7):
    mb = B.P.kit.begin()
    q = B.Beast(L=0.76, zs=0.74, w=0.15, hl=0.58, fb=0.16, hb=-0.2, ankle=0.07, toe=0.11)
    q.trunk(mb, "fur", (0.24, 0.32, 0.24), (0.16, 0.3, 0.17), (0.17, 0.24, 0.19))
    q.legs(mb, 0.085, 0.05, "fur", "fur_shade", foot="claw", foot_r=0.06, claw="tooth")
    for prefix, x in (("", 0.0), ("l_", 0.2), ("r_", -0.2)):
        up = 0.06 if not prefix else 0.0
        pts = [(x * 0.4, -0.36, 0.8), (x * 0.9, -0.54, 0.95 + up), (x * 1.25, -0.68, 1.03 + up)]
        h = q.neck(mb, pts, [0.14, 0.115, 0.1], ("fur",), prefix=prefix)
        wolf_head(mb, h, 1.0, prefix + "head", prefix + "jaw")
        a = q.necks[-1][1][1]
        mb.cylinder(a + Vector((0, 0.03, -0.02)), a + Vector((0, -0.03, 0.02)), 0.135, 0.135, "iron",
                    weights={prefix + "neck.2": 1.0}, segments=8)                         # A spiked collar.
        for j in range(5):
            ang = math.radians(-30 + j * 60)
            d = Vector((math.cos(ang), 0, math.sin(ang)))
            spike(mb, a + d * 0.12, a + d * 0.2, 0.02, "tooth", prefix + "neck.2")
    for i in range(6):                                          # Hackles down the back.
        y = -0.3 + i * 0.1
        spike(mb, (0, y, 0.86 - 0.01 * i), (0, y + 0.06, 0.98 - 0.015 * i), 0.035, "fur_shade", "body")
    pts = q.tail(mb, [(0, 0.4, 0.76), (0, 0.6, 0.7), (0, 0.78, 0.58), (0, 0.9, 0.5)], [0.045, 0.05, 0.04, 0.02], ("fur",))
    hull(mb, [pts[-1] + Vector(o) for o in ((0.05, 0, 0), (-0.05, 0, 0), (0, 0.14, 0.02), (0, 0.02, 0.04), (0, 0.02, -0.04))],
         "fire_b", "tail.3")                                    # An ember at the tail's tip.
    q.mech()
    q.clips(walk=dict(frames=22, duty=0.64, lift=0.07, crouch=0.04), run=dict(frames=11), jaw=34.0, attack_s=1.1, wide=0.4)
    B.save(mb, name, cols, q.m, k)


# --------------------------------------------------------------------- hydra

def hydra(name, cols, heads=5, k=1.0):
    mb = B.P.kit.begin()
    q = B.Beast(L=2.4, zs=1.9, w=0.85, hl=1.4, fb=0.26, hb=-0.26, ankle=0.24, toe=0.55)
    q.trunk(mb, "scale", (1.15, 1.35, 0.95), (1.05, 1.3, 0.85), (0.95, 1.2, 0.85), belly_mat="belly")
    q.legs(mb, 0.36, 0.25, "scale", "scale_dark", foot="claw", foot_r=0.3, claw="tooth")
    xs = {5: (0.0, 0.42, -0.42, 0.84, -0.84), 3: (0.0, 0.55, -0.55)}[heads]
    radii = [0.36, 0.3, 0.25, 0.21, 0.18]
    for i, x in enumerate(xs):
        prefix = "" if i == 0 else "abcdef"[i] + "_"
        rise = 0.9 - 0.42 * abs(x) / 0.42 * 0.5
        fwd = 0.3 if i == 0 else 0.0
        pts = [(x * 0.9, -1.25, 2.0), (x * 1.5, -1.8 - fwd * 0.3, 2.75 + rise * 0.3), (x * 2.0, -2.3 - fwd * 0.6, 3.5 + rise * 0.6),
               (x * 2.3, -2.9 - fwd, 4.05 + rise * 0.85), (x * 2.45, -3.6 - fwd, 4.3 + rise)]
        h = q.neck(mb, pts, radii, ("scale", "scale_dark"), prefix=prefix)
        B.head_dragon(mb, h, 1.35, prefix + "head", prefix + "jaw", horns=1, frill=True)
        B.crest(mb, prefix + "neck", q.necks[-1][1], radii, "horn", 0.22, per=1)
    tail = q.tail(mb, [(0, 1.5, 1.8), (0, 2.4, 1.5), (0, 3.3, 1.1), (0, 4.1, 0.75), (0, 4.8, 0.5), (0, 5.4, 0.36)],
                  [0.62, 0.5, 0.38, 0.27, 0.17, 0.08], ("scale_dark", "scale"))
    B.crest(mb, "tail", tail, [0.62, 0.5, 0.38, 0.27, 0.17, 0.08], "horn", 0.3, per=2)
    for i in range(5):
        y = -0.9 + i * 0.5
        spike(mb, (0, y, 2.35), (0, y + 0.2, 2.85 - 0.04 * i), 0.14, "horn", "body")
    q.mech()
    q.clips(walk=dict(frames=40, duty=0.7, lift=0.22, crouch=0.1, yaw=1.2), attack_s=1.8, die_s=2.6, wide=2.0, idle_look=7.0)
    B.save(mb, name, cols, q.m, k)


def hydra_colors(scale, dark, belly):
    return {**B.shades("scale", scale), **B.palette(scale_dark=dark, belly=belly, membrane=0xC8A03A, horn=0xE6D8B8,
                                                    tooth=0xF2EAD0, eye=0xFFD23A, mouth=0x6A1A20)}


# ------------------------------------------------------------- forest spirit

def stag(name, cols, k=1.5, spirit=True):
    mb = B.P.kit.begin()
    q = B.Beast(L=1.0, zs=1.18, w=0.14, hl=0.95, fb=-0.1, hb=0.17, ankle=0.09, toe=0.08)
    q.trunk(mb, "coat", (0.23, 0.36, 0.3), (0.2, 0.42, 0.25), (0.22, 0.34, 0.27))
    q.legs(mb, 0.075, 0.035, "coat", "coat_shade", foot="hoof", foot_mat="hoof", foot_r=0.045, hind=1.1)
    radii = [0.2, 0.13, 0.1]
    h = q.neck(mb, [(0, -0.46, 1.24), (0, -0.6, 1.6), (0, -0.68, 1.9)], radii, ("coat",))
    hp = B.head_muzzle(mb, h, 0.95, "head", "jaw", skull=(0.09, 0.12, 0.1), mz=(0.26, 0.04, 0.075, 0.1), ears="side", ear=0.8,
                       mat="coat", mat2="coat_shade")
    for sx in (-1, 1):
        B.antler(mb, hp(sx * 0.05, 0.04, 0.09), 1.0, sx, "glow", "head", points=4, spread=1.5)
    lump(mb, (0, -0.52, 1.02), (0.2, 0.2, 0.3), "ruff", "body", seed=6, count=12, tones=False)   # A pale ruff on the chest.
    q.tail(mb, [(0, 0.52, 1.2), (0, 0.62, 1.16), (0, 0.7, 1.08)], [0.05, 0.05, 0.02], ("ruff",))
    if spirit:
        for i in range(7):                                      # Glowing spots along the back, leaves on the rump.
            ang = i * 2.4
            ball(mb, (0.16 * math.cos(ang), -0.3 + i * 0.11, 1.33 + 0.03 * math.sin(ang * 2)), 0.03, "glow", "body",
                 segments=5, rings=3)
        for leg, sx, end in B.LEGS:
            a = q.points[leg][2]
            mb.cylinder(a + Vector((0, 0, 0.1)), a + Vector((0, 0, 0.14)), 0.05, 0.05, "glow", weights={f"leg_low.{leg}": 1.0},
                        segments=6)
    q.mech()
    q.clips(walk=dict(frames=24, duty=0.64, lift=0.1, crouch=0.045, nod=3.0), run=dict(frames=12, lift=0.18),
            attack="gore", jaw=8.0, eat=dict(bend=40.0, head=-25.0), wide=0.5)
    B.save(mb, name, cols, q.m, k)


def stag_colors(coat, glow, ruff):
    return {**B.shades("coat", coat), **B.palette(hoof=0x3A3430, eye=0x101418, nose=0x2A2624, glow=glow, ruff=ruff)}


WHITE = horse_colors(0xF2EEE6, 0xE6D8F0)
MODELS = {
    "mythic_unicorn": B.builder(horse, "mythic_unicorn", WHITE, k=1.1, horn=True),
    "mythic_nightmare": B.builder(horse, "mythic_nightmare", horse_colors(0x2A2630, 0x1A181E, glow=0xFF8A2A, eye=0xFF3A1A,
                                                                         fire=0xFFD24A), k=1.15, horn=True, flame=True),
    "mythic_pegasus": B.builder(horse, "mythic_pegasus", WHITE, k=1.1, wings=True),
    "mythic_pegasus_black": B.builder(horse, "mythic_pegasus_black",
                                      horse_colors(0x34303A, 0x1E1C22, feather=0x4A4654, feather_dark=0x222028), k=1.1,
                                      wings=True),
    "animal_pony": B.builder(horse, "animal_pony", horse_colors(0x9A6A42, 0x3A2A20), k=0.95, pony=True),
    "animal_pony_saddled": B.builder(horse, "animal_pony_saddled", horse_colors(0xD8C8A8, 0xF2EEE6), k=0.95, pony=True,
                                     gear="saddle"),
    "animal_pony_pack": B.builder(horse, "animal_pony_pack", horse_colors(0x4A4038, 0x1E1A18, cloth=0x3A5A8A), k=0.95,
                                  pony=True, gear="pack"),
    "mythic_griffin": B.builder(griffin, "mythic_griffin", lion_colors(0xC89A52, 0x8A5A2E)),
    "mythic_griffin_snow": B.builder(griffin, "mythic_griffin_snow",
                                     lion_colors(0xE4E0D8, 0xB8B4AE, feather=0xF6F4F0, feather_dark=0x4A4A52)),
    "monster_manticore": B.builder(manticore, "monster_manticore",
                                   lion_colors(0xB8562E, 0x5A2418, chitin=0x3A2A2E, chitin_dark=0x241A1E, eye=0xE8E04A)),
    "monster_chimera": B.builder(chimera, "monster_chimera",
                                 lion_colors(0xC89A52, 0x7A4A26, goat=0xD8D2C6, goat_shade=0xA8A296, goat_light=0xECE8E0,
                                             goat_eye=0xE8C83A, snake=0x4E7A3A, snake_dark=0x35582A)),
    "boss_cerberus": B.builder(cerberus, "boss_cerberus",
                               {**B.shades("fur", 0x2E2A30), **B.palette(eye=0xFF3A1A, nose=0x121014, tooth=0xF2EAD0,
                                                                         iron=0x6A6E76, fire_b=0xFF8A2A)}),
    "boss_hydra": B.builder(hydra, "boss_hydra", hydra_colors(0x3E7A6A, 0x2A5850, 0xD8C87A)),
    "boss_hydra_three": B.builder(hydra, "boss_hydra_three", hydra_colors(0x6A7A3A, 0x4A5828, 0xE0D08A), heads=3, k=0.75),
    "spirit_stag": B.builder(stag, "spirit_stag", stag_colors(0xECEFE8, 0x7AFFC8, 0xFFFFFF)),
    "spirit_stag_autumn": B.builder(stag, "spirit_stag_autumn", stag_colors(0x9A6A42, 0xFFC84A, 0xECE2CC)),
}
