"""Sea and river creatures, all of rigid pieces on a chain of bones from
the nose to the tail (seg.N), so a wave runs down the body:

- shark (4.5 m): swims with a sideways wave; attack opens the jaws;
- whale (14 m): swims with an up-and-down wave; swim_breach leaps out;
- dolphin (2.7 m): the same, with swim_jump;
- sea serpent (20 m): a raised neck and humps; idle, swim, attack, die;
- giant crab (3.4 m wide): eight legs posed by inverse kinematics and two
  claws that snap; idle, walk, attack, die;
- giant sea turtle (3 m): flippers that row; idle, swim, die;
- fish school: twelve fish, each on its bone; swim and swim_scatter.
The models rest on Z = 0 and the game lifts them into the water (as
rigs_swim.py says); the clips named swim* and die may go below Z = 0.
"""

import math

from mathutils import Quaternion, Vector

import _bq as B
from _bq import hull, spike, seg, ball, plate, lump, rock, Pose, X, Y, Z, pulse, smooth

TAU = 2 * math.pi


def ring(c, w, h, half=None, n=8):
    out = []
    for i in range(n + 1 if half else n):
        a = TAU * i / n
        if half == "up" and i > n // 2:
            continue
        if half == "down" and i < n // 2:
            continue
        out.append(Vector(c) + Vector((w * math.cos(a), 0.0, h * math.sin(a))))
    return out


def tube(mb, pts, sizes, mat, belly=None, name="seg"):
    """A body of faceted sections along the points, each on its bone; with
    `belly`, the lower half is of that material."""
    for i, (a, b) in enumerate(zip(pts, pts[1:])):
        bone = f"{name}.{i + 1}"
        if belly:
            hull(mb, ring(a, *sizes[i], half="up") + ring(b, *sizes[i + 1], half="up"), mat, bone)
            hull(mb, ring(a, *sizes[i], half="down") + ring(b, *sizes[i + 1], half="down"), belly, bone)
        else:
            hull(mb, ring(a, *sizes[i]) + ring(b, *sizes[i + 1]), mat, bone)


def wave(n, axis, amp, t, k=1, lag=0.7, first=0.12, power=1.2):
    """The turns of a swimming wave along seg.1..seg.n."""
    p = TAU * k * t
    turns = {"seg.1": [(axis, -amp * first * n * 0.3 * math.sin(p))]}
    for i in range(1, n):
        turns[f"seg.{i + 1}"] = [(axis, amp * (i / (n - 1)) ** power * math.sin(p - i * lag))]
    return turns


def merge(turns, more):
    for bone, t in more.items():
        turns[bone] = list(turns.get(bone, [])) + list(t)
    return turns


# --------------------------------------------------------------------- shark

def shark(name, cols, k=1.0):
    mb = B.P.kit.begin()
    zc = 0.55
    ys = (-2.2, -1.75, -1.0, -0.1, 0.8, 1.5, 1.95)
    sizes = [(0.03, 0.03), (0.24, 0.24), (0.38, 0.42), (0.37, 0.43), (0.24, 0.29), (0.11, 0.14), (0.05, 0.07)]
    pts = [Vector((0, y, zc + (0.04 if i == 0 else 0.0))) for i, y in enumerate(ys)]
    tube(mb, pts, sizes, "skin", belly="belly")
    n = len(pts) - 1
    plate(mb, [(0, -0.75, zc + 0.38), (0, 0.05, zc + 0.4), (0, 0.22, zc + 1.0), (0, 0.0, zc + 0.95)], 0.06, "skin_dark", "seg.3")
    plate(mb, [(0, 1.0, zc + 0.24), (0, 1.3, zc + 0.2), (0, 1.36, zc + 0.42)], 0.04, "skin_dark", "seg.5")
    for sx in (-1, 1):                                          # Pectoral fins, eyes, gills.
        plate(mb, [(sx * 0.3, -1.0, zc - 0.18), (sx * 0.32, -0.55, zc - 0.2), (sx * 1.05, -0.3, zc - 0.42),
                   (sx * 1.0, -0.5, zc - 0.42)], 0.05, "skin_dark", "seg.2")
        plate(mb, [(sx * 0.2, 0.75, zc - 0.2), (sx * 0.2, 1.0, zc - 0.2), (sx * 0.45, 1.1, zc - 0.34)], 0.035, "skin_dark", "seg.4")
        ball(mb, (sx * 0.2, -1.78, zc + 0.1), 0.035, "eye", "seg.1", segments=5, rings=3)
        for i in range(3):
            y = -1.3 + i * 0.11
            plate(mb, [(sx * 0.36, y, zc + 0.14), (sx * 0.365, y + 0.03, zc + 0.14), (sx * 0.37, y + 0.02, zc - 0.12)], 0.02,
                  "skin_dark", "seg.2")
    t = pts[-1]
    plate(mb, [t + Vector((0, -0.25, 0)), t + Vector((0, 0.35, 1.0)), t + Vector((0, 0.5, 0.95)), t + Vector((0, 0.1, 0.0))], 0.05,
          "skin_dark", f"seg.{n}")
    plate(mb, [t + Vector((0, -0.2, 0)), t + Vector((0, 0.1, 0.0)), t + Vector((0, 0.38, -0.5)), t + Vector((0, 0.25, -0.5))], 0.05,
          "skin_dark", f"seg.{n}")
    # The jaw under the snout, with teeth above and below.
    hull(mb, [(-0.2, -1.72, zc - 0.22), (0.2, -1.72, zc - 0.22), (-0.26, -1.25, zc - 0.36), (0.26, -1.25, zc - 0.36),
              (-0.2, -1.7, zc - 0.3), (0.2, -1.7, zc - 0.3), (0, -1.86, zc - 0.24)], "belly", "jaw")
    hull(mb, [(-0.17, -1.7, zc - 0.215), (0.17, -1.7, zc - 0.215), (-0.2, -1.3, zc - 0.3), (0.2, -1.3, zc - 0.3),
              (0, -1.5, zc - 0.2)], "mouth", "jaw")
    for i in range(7):
        x = (i - 3) * 0.055
        spike(mb, (x, -1.82 + abs(x) * 0.6, zc - 0.16), (x, -1.83 + abs(x) * 0.6, zc - 0.25), 0.022, "tooth", "seg.1", sides=3)
        spike(mb, (x * 0.9, -1.78 + abs(x) * 0.6, zc - 0.23), (x * 0.9, -1.8 + abs(x) * 0.6, zc - 0.15), 0.018, "tooth", "jaw",
              sides=3)
    bones = B.chain_bones("seg", pts, None)[0] + [("jaw", (0, -1.25, zc - 0.3), (0, -1.85, zc - 0.25), "seg.1")]
    m = B.P.kit.Mech(bones)
    m.clip("idle", 4.0, lambda t: merge(wave(n, Z, 5.0, t), {"jaw": [(X, 4.0 + 3.0 * math.sin(TAU * t))]}))
    m.clip("swim", 1.4, lambda t: wave(n, Z, 15.0, t), speed=3.0)

    def attack(t):
        hit = pulse(t, 0.25, 0.4, 0.5, 0.85)
        turns = wave(n, Z, 10.0 + 8.0 * hit, t, k=2)
        turns["jaw"] = [(X, 4.0 + 34.0 * pulse(t, 0.15, 0.36, 0.42, 0.52))]
        return turns, {"root": (0, -0.5 * hit, 0.12 * hit)}
    m.clip("attack", 1.2, attack)

    def die(t):
        a = smooth((t - 0.1) / 0.7)
        turns = wave(n, Z, 12.0 * (1 - a), t, k=3)
        turns["seg.1"] = turns["seg.1"] + [(Y, 172.0 * a)]
        turns["jaw"] = [(X, 18.0 * a)]
        return turns, {"root": (0, 0, 0.5 * a)}
    m.clip("die", 2.2, die, loops=False)
    B.save(mb, name, cols, m, k)


# --------------------------------------------------------- whale and dolphin

def cetacean(name, cols, length, girth, zc, beak=0.0, k=1.0, leap="swim_breach", height=None, seconds=3.4, grooves=True,
             dorsal=0.5):
    mb = B.P.kit.begin()
    L = length
    fr = (-0.5, -0.42, -0.25, -0.05, 0.16, 0.32, 0.43, 0.5)
    prof = [(0.08, 0.1), (0.62, 0.6), (0.98, 0.92), (1.0, 1.0), (0.7, 0.74), (0.34, 0.4), (0.14, 0.2), (0.07, 0.07)]
    pts = [Vector((0, L * f, zc)) for f in fr]
    sizes = [(girth * w, girth * h) for w, h in prof]
    tube(mb, pts, sizes, "skin", belly="belly")
    n = len(pts) - 1
    g = girth
    if beak:                                                    # A dolphin's beak.
        hull(mb, [(sx * g * 0.22, pts[0].y + g * 0.3, zc + dz) for sx in (-1, 1) for dz in (-g * 0.22, g * 0.05)]
             + [(sx * g * 0.1, pts[0].y - beak, zc + dz) for sx in (-1, 1) for dz in (-g * 0.2, -g * 0.05)], "skin", "seg.1")
    else:                                                       # A whale's mouth line and throat grooves.
        for sx in (-1, 1):
            plate(mb, [(sx * g * 0.5, pts[1].y - g * 0.2, zc - g * 0.1), (sx * g * 0.86, pts[2].y, zc - g * 0.25),
                       (sx * g * 0.84, pts[2].y, zc - g * 0.33), (sx * g * 0.48, pts[1].y - g * 0.2, zc - g * 0.17)], g * 0.06,
                  "skin_dark", "seg.1")
        if grooves:
            for i in range(5):
                x = (i - 2) * g * 0.2
                seg(mb, (x, pts[1].y, zc - g * 0.6 * 0.97), (x * 1.3, pts[2].y, zc - g * 0.93), g * 0.025, g * 0.025, "skin_dark",
                    "seg.2", sides=3)
        spike(mb, (0, pts[2].y - g * 0.3, zc + g * 0.86), (0, pts[2].y - g * 0.3, zc + g * 0.98), g * 0.08, "skin_dark", "seg.2")
    for sx in (-1, 1):
        ball(mb, (sx * g * 0.6, pts[1].y + g * 0.1, zc - g * 0.02), g * 0.045, "eye", "seg.1", segments=5, rings=3)
        a = Vector((sx * g * 0.8, pts[2].y + g * 0.15, zc - g * 0.45))
        side = "L" if sx > 0 else "R"
        plate(mb, [a, a + Vector((0, g * 0.55, 0)), a + Vector((sx * g * 1.3, g * 1.25, -g * 0.3)),
                   a + Vector((sx * g * 1.5, g * 1.0, -g * 0.3))], g * 0.07, "skin_dark", f"fin.{side}")
    y = pts[3].y + (pts[4].y - pts[3].y) * dorsal
    plate(mb, [(0, y - g * 0.5, zc + g * 0.85), (0, y + g * 0.25, zc + g * 0.75), (0, y + g * 0.42, zc + g * 0.85 + g * 0.6 * (1.5 if beak else 0.6)),
               (0, y + g * 0.2, zc + g * 0.85 + g * 0.55 * (1.5 if beak else 0.6))], g * 0.07, "skin_dark", "seg.4")
    t = pts[-1]
    fluke = g * (1.5 if beak else 1.25)
    for sx in (-1, 1):                                          # Flukes, flat.
        plate(mb, [t + Vector((0, -fluke * 0.3, 0)), t + Vector((sx * fluke, fluke * 0.35, 0)),
                   t + Vector((sx * fluke * 0.85, fluke * 0.6, 0)), t + Vector((0, fluke * 0.25, 0))], g * 0.08, "skin_dark",
              f"seg.{n}")
    bones = B.chain_bones("seg", pts, None)[0]
    for side, sx in B.SIDES:
        a = Vector((sx * g * 0.8, pts[2].y + g * 0.15, zc - g * 0.45))
        bones.append((f"fin.{side}", tuple(a), tuple(a + Vector((sx * g * 1.4, g * 1.1, -g * 0.3))), "seg.2"))
    m = B.P.kit.Mech(bones)

    def fins(t, a):
        return {f"fin.{side}": [(Y, sx * a * math.sin(TAU * t))] for side, sx in B.SIDES}
    m.clip("idle", 5.0, lambda t: merge(wave(n, Z, 2.0, t), fins(t, 6.0)))
    m.clip("swim", 2.4 if not beak else 0.9, lambda t: merge(wave(n, X, 9.0, t, lag=0.6), fins(t, 8.0)),
           speed=3.0 if not beak else 6.0)
    height = height or L * 0.5

    def breach(t):
        u = max(0.0, min(1.0, (t - 0.08) / 0.72))
        up = math.sin(math.pi * u)
        pitch = -62.0 * math.cos(math.pi * u) * smooth(u * 5) * smooth((1 - u) * 5)
        turns = wave(n, X, 5.0 + 6.0 * (1 - up), t, k=3, lag=0.6)
        turns["seg.1"] = turns["seg.1"] + [(X, pitch)]
        merge(turns, {f"fin.{side}": [(Y, sx * 28.0 * up)] for side, sx in B.SIDES})
        return turns, {"root": (0, 0, height * up)}
    m.clip(leap, seconds, breach)

    def die(t):
        a = smooth((t - 0.1) / 0.75)
        turns = wave(n, X, 6.0 * (1 - a), t, k=2)
        turns["seg.1"] = turns["seg.1"] + [(Y, 165.0 * a)]
        return turns, {"root": (0, 0, girth * 0.6 * a)}
    m.clip("die", 3.0, die, loops=False)
    B.save(mb, name, cols, m, k)


# --------------------------------------------------------------- sea serpent

def serpent(name, cols, k=1.0):
    mb = B.P.kit.begin()
    r0 = 0.55
    back = []                                                   # From the neck's base to the tail: three humps.
    count = 12
    for i in range(count + 1):
        u = i / count
        r = r0 * (1.0 - 0.8 * u ** 1.5)
        hump = max(0.0, math.sin(u * 3.2 * math.pi)) * 2.3 * (1 - 0.5 * u)
        back.append((Vector((0, 1.25 * i, r + 0.06 + hump)), r))
    neck = [Vector((0, 0, r0 + 0.06)), Vector((0, -0.7, r0 + 1.0)), Vector((0, -1.1, r0 + 2.1)), Vector((0, -1.5, r0 + 3.1)),
            Vector((0, -2.2, r0 + 3.8))]
    neck_r = [r0, 0.5, 0.44, 0.38, 0.33]
    B.chain(mb, "neck", neck, neck_r, ("scale", "scale_dark"), sides=8)
    bpts, brad = [p for p, r in back], [r for p, r in back]
    B.chain(mb, "seg", bpts, brad, ("scale_dark", "scale"), sides=8)
    B.crest(mb, "neck", neck, neck_r, "fin", 0.5, per=2, width=0.8)
    B.crest(mb, "seg", bpts, brad, "fin", 0.5, per=2, width=0.8, last=count - 1)
    h = neck[-1]
    B.head_dragon(mb, h, 2.0, "head", "jaw", horns=1, frill=True)
    t = bpts[-1]
    plate(mb, [t + Vector((0, -0.4, 0.0)), t + Vector((0, 0.5, 0.75)), t + Vector((0, 1.1, 0.0)), t + Vector((0, 0.5, 0.0))], 0.06,
          "fin", f"seg.{count}")
    bones = B.chain_bones("seg", bpts, None)[0]
    made, last = B.chain_bones("neck", neck, "seg.1")
    bones += made + [("head", tuple(h), tuple(h + Vector((0, -1.1, 0))), last),
                     ("jaw", tuple(h + Vector((0, 0.02, -0.2))), tuple(h + Vector((0, -1.1, -0.3))), "head")]
    m = B.P.kit.Mech(bones)

    def neck_turns(bend, side, head=0.0, jaw=0.0):
        out = {f"neck.{i + 1}": [(X, bend), (Z, side)] for i in range(4)}
        out["head"] = [(X, head)]
        out["jaw"] = [(X, jaw)]
        return out

    def body(t, amp, kk=1):
        p = TAU * kk * t
        return {f"seg.{i + 1}": [(Z, amp * math.sin(p - i * 0.9))] for i in range(1, count)}

    def idle(t):
        p = TAU * t
        return merge(body(t, 2.5), neck_turns(1.5 * math.sin(2 * p), 5.0 * math.sin(p), 3.0 * math.sin(p + 1),
                                              8.0 * pulse(t, 0.55, 0.62, 0.68, 0.78)))
    m.clip("idle", 5.0, idle)
    m.clip("swim", 2.0, lambda t: merge(body(t, 9.0), neck_turns(2.0 * math.sin(2 * TAU * t), -3.0 * math.sin(TAU * t))),
           speed=4.0)

    def attack(t):
        wind = pulse(t, 0.0, 0.32, 0.38, 0.47)
        hit = pulse(t, 0.38, 0.47, 0.56, 0.95)
        return merge(body(t, 3.0), neck_turns(-9.0 * wind + 14.0 * hit, 0.0, 14.0 * wind - 4.0 * hit, 36.0 * max(wind * 0.6, hit)))
    m.clip("attack", 1.8, attack)

    def die(t):
        a = smooth((t - 0.15) / 0.7)
        turns = merge(body(t, 6.0 * (1 - a), 2), neck_turns(21.0 * a, 4.0 * a, 10.0 * a, 22.0 * a))
        return turns, {"root": (0, 0, -0.9 * a)}
    m.clip("die", 2.8, die, loops=False)
    B.save(mb, name, cols, m, k)


# ---------------------------------------------------------------------- crab

def crab(name, cols, k=1.0):
    mb = B.P.kit.begin()
    zb = 0.75
    lump(mb, (0, 0, zb), (1.15, 0.8, 0.38), "shell", "body", seed=3, count=26)
    hull(mb, [(sx * 0.95, y, zb - 0.22) for sx in (-1, 1) for y in (-0.6, 0.6)] + [(0, -0.7, zb - 0.3), (0, 0.65, zb - 0.3),
                                                                                 (0, 0, zb - 0.42)], "belly", "body")
    for i in range(7):                                          # Spines along the shell's front edge.
        x = (i - 3) * 0.3
        spike(mb, (x, -0.66 + abs(x) * 0.22, zb + 0.05), (x * 1.08, -0.9 + abs(x) * 0.22, zb + 0.12), 0.06, "shell_dark", "body")
    bones = [("body", (0, 0.6, zb), (0, -0.6, zb), None)]
    for side, sx in B.SIDES:
        e = Vector((sx * 0.22, -0.68, zb + 0.15))                # Eyes on stalks.
        seg(mb, e, e + Vector((sx * 0.05, -0.1, 0.3)), 0.035, 0.03, "shell_dark", f"eye.{side}", sides=5)
        ball(mb, e + Vector((sx * 0.05, -0.1, 0.34)), 0.07, "eye", f"eye.{side}", segments=6, rings=4)
        bones.append((f"eye.{side}", tuple(e), tuple(e + Vector((sx * 0.05, -0.1, 0.34))), "body"))
        # The claw: an arm, a fat hand and a finger that snaps.
        a, b, c = Vector((sx * 0.8, -0.5, zb - 0.05)), Vector((sx * 1.35, -1.1, zb + 0.15)), Vector((sx * 0.95, -1.75, zb + 0.1))
        seg(mb, a, b, 0.17, 0.15, "shell", f"claw.1.{side}")
        ball(mb, b, 0.19, "shell_dark", f"claw.2.{side}")
        lump(mb, b.lerp(c, 0.55), (0.3, 0.42, 0.24), "shell", f"claw.2.{side}", seed=9 + int(sx), count=14)
        tip = c + Vector((-sx * 0.25, -0.62, 0.0))
        hull(mb, [c + Vector((sx * 0.1, 0.0, -0.16)), c + Vector((-sx * 0.2, 0.0, -0.16)), c + Vector((sx * 0.1, 0, -0.02)),
                  c + Vector((-sx * 0.2, 0, -0.02)), tip + Vector((0, 0, -0.1))], "claw", f"claw.2.{side}")
        hull(mb, [c + Vector((sx * 0.1, 0.0, 0.2)), c + Vector((-sx * 0.2, 0.0, 0.2)), c + Vector((sx * 0.1, 0, 0.03)),
                  c + Vector((-sx * 0.2, 0, 0.03)), tip + Vector((0, 0, 0.06))], "claw", f"pincer.{side}")
        bones += [(f"claw.1.{side}", tuple(a), tuple(b), "body"), (f"claw.2.{side}", tuple(b), tuple(c), f"claw.1.{side}"),
                  (f"pincer.{side}", tuple(c + Vector((0, 0.05, 0.08))), tuple(tip + Vector((0, 0, 0.06))), f"claw.2.{side}")]
    legs = {}
    for side, sx in B.SIDES:
        for i in range(4):
            y = -0.3 + i * 0.3
            hip = Vector((sx * 0.9, y, zb - 0.1))
            knee = Vector((sx * 1.55, y * 1.5, zb + 0.5))
            ankle = Vector((sx * 2.0, y * 1.9 + 0.05, 0.1))
            toe = ankle + Vector((sx * 0.05, 0, -0.1))
            leg = f"{side}{i + 1}"
            seg(mb, hip, knee, 0.12, 0.09, "shell", f"leg_up.{leg}")
            ball(mb, knee, 0.11, "shell_dark", f"leg_low.{leg}")
            seg(mb, knee, ankle, 0.09, 0.05, "shell_dark", f"leg_low.{leg}")
            spike(mb, ankle + Vector((0, 0, 0.05)), toe, 0.05, "claw", f"foot.{leg}", sides=4)
            bones += [(f"leg_up.{leg}", tuple(hip), tuple(knee), "body"), (f"leg_low.{leg}", tuple(knee), tuple(ankle), f"leg_up.{leg}"),
                      (f"foot.{leg}", tuple(ankle), tuple(toe), f"leg_low.{leg}")]
            legs[leg] = (ankle, ((i % 2) * 0.5 + (0.0 if sx > 0 else 0.5)) % 1.0)
    m = B.P.kit.Mech(bones)
    frames, duty, stride, lift = 20, 0.6, 0.55, 0.22
    speed = stride * B.FPS / (duty * frames)

    def stand(pose, t=None):
        for leg, (ankle, phase) in legs.items():
            target = ankle
            if t is not None:
                dy, dz, u = B.P.step(t, phase, duty, stride, lift)
                target = ankle + Vector((0, dy, dz))
            pose.limb(f"leg_up.{leg}", f"leg_low.{leg}", target, Vector((0, 0, 1)))
            pose.set_world(f"foot.{leg}", Quaternion())

    def claws(pose, raise_=0.0, snap=0.0, wave_=0.0):
        for side, sx in B.SIDES:
            pose.turn(f"claw.1.{side}", X, -raise_)
            pose.turn(f"claw.1.{side}", Z, sx * wave_)
            pose.turn(f"pincer.{side}", X, -8.0 - 26.0 * snap)
            pose.turn(f"eye.{side}", Z, 12.0 * math.sin(wave_ * 0.5))

    def idle(t):
        p = TAU * t
        pose = Pose(m, (0, 0, 0.03 * math.sin(2 * p)))
        pose.turn("body", Y, 1.5 * math.sin(p))
        stand(pose)
        claws(pose, 6.0 + 4.0 * math.sin(2 * p), pulse(t, 0.5, 0.56, 0.6, 0.66) + pulse(t, 0.7, 0.76, 0.8, 0.86), 6.0 * math.sin(p))
        return B.P.from_pose(pose)

    def walk(t):
        p = TAU * t
        pose = Pose(m, (0, 0, 0.03 * math.cos(2 * p)))
        pose.turn("body", Y, 2.0 * math.sin(p))
        stand(pose, t)
        claws(pose, 10.0 + 3.0 * math.cos(2 * p), 0.0, 4.0 * math.sin(p))
        return B.P.from_pose(pose)

    def attack(t):
        wind = pulse(t, 0.0, 0.3, 0.36, 0.46)
        hit = pulse(t, 0.36, 0.46, 0.56, 0.95)
        pose = Pose(m, (0, 0.1 * wind - 0.22 * hit, 0.08 * wind - 0.05 * hit))
        pose.turn("body", X, -5.0 * wind + 5.0 * hit)
        stand(pose)
        claws(pose, 38.0 * wind - 6.0 * hit, wind * (1 - hit), -10.0 * wind + 14.0 * hit)
        return B.P.from_pose(pose)

    def die(t):
        a = smooth((t - 0.15) / 0.6)
        pose = Pose(m, (0, 0, -(zb - 0.45) * a))
        pose.turn("body", Y, 6.0 * a)
        stand(pose)
        claws(pose, -14.0 * a, 0.5 * a, 0.0)
        return B.P.from_pose(pose)
    m.clip("idle", 3.0, idle)
    m.clip("walk", frames / B.FPS, walk, speed=speed)
    m.clip("attack", 1.3, attack)
    m.clip("die", 1.8, die, loops=False)
    B.save(mb, name, cols, m, k)


# -------------------------------------------------------------------- turtle

def turtle(name, cols, k=1.0):
    mb = B.P.kit.begin()
    zc = 0.5
    lump(mb, (0, 0.1, zc + 0.05), (1.0, 1.3, 0.48), "shell", "body", seed=4, count=30)
    hull(mb, [(sx * 0.85, y, zc - 0.15) for sx in (-1, 1) for y in (-0.9, 1.1)] + [(0, -1.1, zc - 0.2), (0, 1.3, zc - 0.2),
                                                                                 (0, 0.1, zc - 0.38)], "belly", "body")
    for i, (x, y) in enumerate(((0, -0.5), (0, 0.15), (0, 0.8), (0.5, -0.2), (-0.5, -0.2), (0.5, 0.5), (-0.5, 0.5))):
        zt = zc + 0.05 + 0.48 * math.sqrt(max(0.05, 1 - (x / 1.0) ** 2 - ((y - 0.1) / 1.3) ** 2))
        hull(mb, [(x + dx * 0.24, y + dy * 0.28, zt - 0.03) for dx, dy in ((1, 0), (0.5, 0.9), (-0.5, 0.9), (-1, 0), (-0.5, -0.9),
                                                                         (0.5, -0.9))] + [(x, y, zt + 0.07)], "shell_dark", "body")
    neck = [Vector((0, -1.0, zc)), Vector((0, -1.5, zc + 0.12))]
    seg(mb, neck[0], neck[1], 0.26, 0.2, "skin", "neck")
    h = neck[1]
    hull(mb, [h + Vector(o) for o in ((-0.2, 0.1, -0.14), (0.2, 0.1, -0.14), (-0.2, 0.1, 0.16), (0.2, 0.1, 0.16), (-0.16, -0.3, 0.14),
                                      (0.16, -0.3, 0.14), (-0.1, -0.52, -0.02), (0.1, -0.52, -0.02), (0, -0.56, -0.08),
                                      (-0.14, -0.3, -0.15), (0.14, -0.3, -0.15))], "skin", "head")
    for sx in (-1, 1):
        ball(mb, h + Vector((sx * 0.17, -0.2, 0.06)), 0.045, "eye", "head", segments=5, rings=3)
    bones = [("body", (0, 1.2, zc), (0, -1.0, zc), None), ("neck", tuple(neck[0]), tuple(neck[1]), "body"),
             ("head", tuple(h), tuple(h + Vector((0, -0.55, 0))), "neck")]
    for side, sx in B.SIDES:
        a = Vector((sx * 0.8, -0.7, zc - 0.08))                  # Front flippers: long blades.
        plate(mb, [a + Vector((0, -0.2, 0)), a + Vector((0, 0.3, 0)), a + Vector((sx * 1.5, 0.75, -0.2)),
                   a + Vector((sx * 1.75, 0.45, -0.22)), a + Vector((sx * 1.0, -0.1, -0.1))], 0.09, "skin", f"flipper.F{side}")
        bones.append((f"flipper.F{side}", tuple(a), tuple(a + Vector((sx * 1.7, 0.5, -0.2))), "body"))
        b = Vector((sx * 0.7, 1.05, zc - 0.1))                   # Hind flippers: short paddles.
        plate(mb, [b + Vector((0, -0.15, 0)), b + Vector((0, 0.2, 0)), b + Vector((sx * 0.5, 0.75, -0.12)),
                   b + Vector((sx * 0.75, 0.5, -0.12))], 0.08, "skin", f"flipper.H{side}")
        bones.append((f"flipper.H{side}", tuple(b), tuple(b + Vector((sx * 0.7, 0.6, -0.12))), "body"))
    spike(mb, (0, 1.35, zc - 0.05), (0, 1.7, zc - 0.1), 0.09, "skin", "body")
    m = B.P.kit.Mech(bones)

    def flip(t, front, hind, lift=0.0):
        p = TAU * t
        out = {}
        for side, sx in B.SIDES:
            out[f"flipper.F{side}"] = [(Y, -sx * (lift + front * math.sin(p))), (Z, sx * front * 0.5 * math.cos(p))]
            out[f"flipper.H{side}"] = [(Y, -sx * (lift * 0.5 + hind * math.sin(p + 1.0)))]
        return out
    m.clip("idle", 5.0, lambda t: merge(flip(t, 0.0, 0.0, 3.0 + 3.0 * math.sin(TAU * t)),
                                        {"neck": [(Z, 10.0 * math.sin(TAU * t))], "head": [(X, 4.0 * math.sin(2 * TAU * t))]}))
    m.clip("swim", 2.0, lambda t: (merge(flip(t, 30.0, 10.0, 6.0), {"body": [(X, 2.5 * math.sin(TAU * t + 0.6))],
                                                                      "neck": [(X, -3.0 * math.sin(TAU * t + 0.6))]}),
                                   {"root": (0, 0, 0.5 + 0.08 * math.sin(TAU * t))}), speed=1.6)

    def die(t):
        a = smooth((t - 0.1) / 0.7)
        turns = flip(t, 0.0, 0.0, -10.0 * a)
        turns["neck"] = [(X, 14.0 * a)]
        turns["body"] = [(Y, 170.0 * a)]
        return turns, {"root": (0, 0, 0.6 * a)}
    m.clip("die", 2.4, die, loops=False)
    B.save(mb, name, cols, m, k)


# --------------------------------------------------------------- fish school

def school(name, cols, count=12, size=0.4, k=1.0):
    import random
    rnd = random.Random(7)
    mb = B.P.kit.begin()
    bones, fish = [], []
    for i in range(count):
        c = Vector((rnd.uniform(-0.9, 0.9), rnd.uniform(-1.4, 1.4), rnd.uniform(0.25, 0.95)))
        s = size * rnd.uniform(0.8, 1.15)
        bone = f"fish.{i + 1}"
        hull(mb, [c + Vector(o) * s for o in ((0, -0.5, 0.0), (0.07, -0.2, 0.13), (-0.07, -0.2, 0.13), (0.07, -0.2, -0.08),
                                              (-0.07, -0.2, -0.08), (0.05, 0.15, 0.1), (-0.05, 0.15, 0.1), (0, 0.38, 0.0),
                                              (0.05, 0.15, -0.1), (-0.05, 0.15, -0.1))], "fish" if i % 3 else "fish_dark", bone)
        hull(mb, [c + Vector(o) * s for o in ((0.065, -0.18, -0.085), (-0.065, -0.18, -0.085), (0, -0.44, -0.03),
                                              (0, 0.3, -0.03), (0, -0.05, -0.14))], "belly", bone)
        plate(mb, [c + Vector((0, 0.34, 0.0)) * s, c + Vector((0, 0.6, 0.17)) * s, c + Vector((0, 0.5, 0.0)) * s,
                   c + Vector((0, 0.6, -0.17)) * s], 0.02 * s, "fin", bone)
        plate(mb, [c + Vector((0, -0.2, 0.12)) * s, c + Vector((0, 0.1, 0.1)) * s, c + Vector((0, 0.08, 0.22)) * s], 0.02 * s,
              "fin", bone)
        for sx in (-1, 1):
            ball(mb, c + Vector((sx * 0.06, -0.3, 0.05)) * s, 0.022 * s, "eye", bone, segments=4, rings=3)
        bones.append((bone, tuple(c), tuple(c + Vector((0, -0.4 * s, 0))), None))
        fish.append((c, rnd.uniform(0, TAU), rnd.uniform(0, TAU), rnd.choice((3, 4, 5)), rnd.uniform(0.6, 1.0)))
    m = B.P.kit.Mech(bones)

    def swim(t):
        p = TAU * t
        turns, moves = {}, {}
        for i, (c, f1, f2, beats, a) in enumerate(fish):
            bone = f"fish.{i + 1}"
            turns[bone] = [(Z, 14.0 * math.sin(beats * p + f1)), (Z, 6.0 * math.cos(p + f2) * a)]
            moves[bone] = (0.12 * a * math.sin(p + f2), 0.18 * a * math.sin(p + f1), 0.06 * a * math.sin(2 * p + f1))
        return turns, moves

    def scatter(t):
        p = TAU * t
        out = pulse(t, 0.05, 0.2, 0.45, 0.95)
        turns, moves = {}, {}
        for i, (c, f1, f2, beats, a) in enumerate(fish):
            bone = f"fish.{i + 1}"
            away = Vector((c.x, c.y, 0)).normalized() if abs(c.x) + abs(c.y) > 0.05 else Vector((1, 0, 0))
            yaw = math.degrees(math.atan2(away.x, -away.y)) * pulse(t, 0.05, 0.15, 0.3, 0.5)
            turns[bone] = [(Z, 16.0 * math.sin(2 * beats * p + f1)), (Z, yaw)]
            moves[bone] = (away.x * 1.6 * out * a, away.y * 1.6 * out * a, 0.1 * out * math.sin(f1))
        return turns, moves
    m.clip("swim", 3.0, swim, speed=1.0)
    m.clip("swim_scatter", 2.4, scatter)
    B.save(mb, name, cols, m, k)


def sea_colors(skin, dark, belly, **more):
    return B.palette(skin=skin, skin_dark=dark, belly=belly, eye=0x101014, tooth=0xF4F0E4, mouth=0x8A2A30, **more)


MODELS = {
    "sea_shark": B.builder(shark, "sea_shark", sea_colors(0x6A7A8A, 0x4E5C6A, 0xE8ECEE)),
    "sea_whale": B.builder(cetacean, "sea_whale", sea_colors(0x3E5A78, 0x2C4460, 0xD8E2E8), 14.0, 1.7, 1.95),
    "sea_dolphin": B.builder(cetacean, "sea_dolphin", sea_colors(0x7A8EA4, 0x5A6C82, 0xE4EAEE), 2.5, 0.3, 0.42, beak=0.32,
                             leap="swim_jump", height=1.9, seconds=1.6, dorsal=0.2),
    "sea_serpent": B.builder(serpent, "sea_serpent",
                             {**B.shades("scale", 0x2E7A8A), **B.palette(scale_dark=0x1E5868, belly=0xC8E0C8, fin=0xE8A03A,
                                                                         membrane=0xE8A03A, horn=0xE6D8B8, tooth=0xF2EAD0,
                                                                         eye=0xFFD23A, mouth=0x6A1A20)}),
    "sea_giant_crab": B.builder(crab, "sea_giant_crab",
                                {**B.shades("shell", 0xC8502E), **B.palette(shell_dark=0x8A3220, belly=0xE8C8A0, claw=0xF2E0C0,
                                                                            eye=0x141014)}),
    "sea_giant_turtle": B.builder(turtle, "sea_giant_turtle",
                                  {**B.shades("shell", 0x5A7A4A), **B.palette(shell_dark=0x3E5A36, belly=0xD8CC9A, skin=0x7A9A6A,
                                                                              eye=0x141014)}),
    "sea_fish_school": B.builder(school, "sea_fish_school",
                                 B.palette(fish=0x8AA4B8, fish_dark=0x5E7A90, belly=0xE8EEF0, fin=0x6A8498, eye=0x101014)),
    "sea_fish_school_gold": B.builder(school, "sea_fish_school_gold",
                                      B.palette(fish=0xE8862A, fish_dark=0xC85A1E, belly=0xF6E0B0, fin=0xF2B04A, eye=0x101014),
                                      count=8, size=0.55),
}
