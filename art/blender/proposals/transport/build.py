"""Transport proposals: wagons and carts with their draft animals, siege
engines on wheels, a mine cart and a balloon. See ../LEEME.md.

    blender --background --factory-startup --python art/blender/proposals/transport/build.py -- [ids]

Everything faces -Y: the animal in front, the vehicle behind it. Animals
are made of rigid parts (kit.Mech): a `roll` clip walks them while the
wheels turn at the speed saved in the model, and `idle` lets them rest.
"""

import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import _animals  # noqa: E402
import _kit as kit  # noqa: E402
import _shapes  # noqa: E402
import common  # noqa: E402
from _animals import draft_animal  # noqa: E402
from _shapes import TAU, barrel, beam, crate, lantern, log, mark, moved, rock, rope, sack, solid, wheel  # noqa: E402

FAMILY = "transport"
C = common.rgb
COLORS = {
    **_shapes.COLORS,
    **_animals.COLORS,
    "coat_brown": C(0x7A4E2E), "coat_dark": C(0x3E2C22), "coat_grey": C(0x9A968E), "coat_cream": C(0xD8C8A8),
    "coat_ox": C(0x8A5A3A), "coat_ox_white": C(0xD8D0C0),
    "mane_dark": C(0x2A2018), "mane_light": C(0xD8C8A0), "hoof": C(0x2E2A28), "muzzle": C(0x4A342A),
    "eye": C(0x101010), "horn": C(0xE0D8C0),
    "canvas": C(0xE4D8B8), "canvas_shade": C(0xD0C29C), "canvas_trim": C(0xB8A880),
    "cloth_blue": C(0x2F4E8C), "cloth_blue_shade": C(0x29447A), "cloth_blue_trim": C(0x24396A),
    "cloth_red": C(0xA83A34), "cloth_red_shade": C(0x94322E), "cloth_red_trim": C(0x7E2A26),
    "shadow": C(0x2A2622), "coach": C(0x6A2A2A), "coach_dark": C(0x2E1A1A), "coach_trim": C(0xC9A441),
    "vardo": C(0x3F7A4A), "vardo_trim": C(0xE0B040), "vardo_roof": C(0xA83A34), "vardo_door": C(0x8A3A34),
    "hide": C(0x9A7050), "hide_shade": C(0x86603F), "ore": C(0x4A4E58), "ore_glint": C(0xC08A4A),
    "balloon_a": C(0xC0392B), "balloon_b": C(0xF0E0C0), "wicker": C(0xB08A4A), "wicker_dark": C(0x8A6A34),
    "flame": C(0xF08A24), "flame_core": C(0xFFF0B0), "water": C(0x4A7FA0), "bow": C(0x8A6038),
    "soil": C(0x6A4A30), "flowers": C(0xC86A8A),
}

def axle(mb, name, y, r, half, bed_z=None):
    """Two wheels and their axle at height r; returns the bone and its radius."""
    w = {name: 1.0}
    mb.cylinder((-half, y, r), (half, y, r), 0.045, 0.045, "iron", w, segments=6)
    wheel(mb, (-half, y, r), r, name)
    wheel(mb, (half, y, r), r, name)
    if bed_z is not None and bed_z > r + 0.1:
        mb.box((0, y, (r + bed_z) / 2 + 0.03), (half * 1.5, 0.16, bed_z - r - 0.04), "plank_dark")
    return (name, (0, y, r), (0.5, y, r), None), r


def finish(mb, name, animals=(), axles=(), speed=None, clips=(), move_clip="roll", extra_bones=(), idle_extra=None,
           roll_extra=None):
    """Saves a vehicle: `idle` if it has animals, a moving clip if it has
    animals or wheels (with its speed saved), and its own `clips`
    (name, seconds, pose, loops)."""
    bones = [b for a in animals for b in a["bones"]] + [b for b, _r in axles] + list(extra_bones)
    mech = kit.Mech(bones)
    cycles = 2
    cycle = animals[0]["cycle"] if animals else 1.0
    seconds = cycles * cycle
    speed = speed or (animals[0]["speed"] if animals else 1.2)
    turns_per_axle = {}
    if axles:
        big = max(r for _b, r in axles)
        _deg, speed = _shapes.wheel_turn(speed, seconds, big)
        step = 360.0 / _shapes.SPOKES
        for bone, r in axles:
            turns_per_axle[bone[0]] = max(1, round(speed * seconds / (TAU * r) * 360.0 / step)) * step
    if animals:
        def idle(t):
            turns, moves = {}, {}
            for a in animals:
                tt, mm = a["idle"](t)
                turns.update(tt)
                moves.update(mm)
            if idle_extra:
                tt, mm = idle_extra(t)
                turns.update(tt)
                moves.update(mm)
            return turns, moves
        mech.clip("idle", 4.0, idle)
    if animals or axles:
        def roll(t):
            turns, moves = {}, {}
            for i, a in enumerate(animals):
                swing = math.degrees(math.asin(min(0.5, speed * a["cycle"] / (4 * a["hip"]))))
                tt, mm = a["gait"]((t * cycles + 0.13 * i) % 1.0, swing)
                turns.update(tt)
                moves.update(mm)
            for bone, degrees in turns_per_axle.items():
                turns[bone] = [(kit.X, degrees * t)]
            if roll_extra:
                tt, mm = roll_extra(t)
                turns.update(tt)
                moves.update(mm)
            return turns, moves
        mech.clip(move_clip, seconds, roll, speed=round(speed, 3))
    for clip, secs, pose, loops in clips:
        mech.clip(clip, secs, pose, loops=loops)
    kit.save(mb, FAMILY, name, COLORS, mech=mech)


def shafts(mb, y0, y1, half=0.42, z0=0.98, z1=1.05):
    for sx in (-1, 1):
        beam(mb, (sx * half, y0, z0), (sx * half, y1, z1), 0.045, "pole")


def arch(half, base, rise, n=6, scale=1.0, cz=None):
    """Points (x, z) of an arch, right to left."""
    cz = base if cz is None else cz
    pts = []
    for k in range(n + 1):
        a = math.pi * k / n
        pts.append((half * math.cos(a) * scale, cz + (base - cz) * scale + rise * math.sin(a) * scale))
    return pts


def arched_cover(mb, y0, y1, half, base, rise, mats, trim, strips=5, ends="shadow"):
    """A cloth cover on hoops along Y, with dark openings at both ends."""
    pts = arch(half, base, rise)
    for i in range(strips):
        a, b = y0 + (y1 - y0) * i / strips, y0 + (y1 - y0) * (i + 1) / strips
        solid(mb, [(x, a, z) for x, z in pts], (0, b - a, 0), mats[i % len(mats)])
    for i in range(strips + 1):
        yy = y0 + (y1 - y0) * i / strips
        solid(mb, [(x * 1.035, yy - 0.03, base + (z - base) * 1.035) for x, z in pts], (0, 0.06, 0), trim)
    if ends:
        inner = [(x * 0.84, base + 0.02 + (z - base) * 0.84) for x, z in pts]
        solid(mb, [(x, y0 - 0.035, z) for x, z in inner], (0, 0.012, 0), ends)
        solid(mb, [(x, y1 + 0.023, z) for x, z in inner], (0, 0.012, 0), ends)


# --- Wagons ------------------------------------------------------------------------------------


def wagon_bed(mb, y0=-1.1, y1=2.2, half=0.75, z=1.0, side=0.55):
    cy, length = (y0 + y1) / 2, y1 - y0
    mb.box((0, cy, z), (half * 2, length, 0.12), "plank_dark")
    for sx in (-1, 1):
        mb.box((sx * half, cy, z + 0.06 + side / 2), (0.07, length, side), "plank")
        mb.box((sx * (half + 0.04), cy, z + 0.06 + side * 0.5), (0.02, length, 0.05), "plank_dark")
        mb.box((sx * half, cy, z + 0.08 + side), (0.1, length + 0.06, 0.05), "plank_dark")
        for k in range(5):
            mb.box((sx * (half + 0.045), y0 + length * (k + 0.5) / 5, z + 0.06 + side / 2), (0.05, 0.08, side + 0.08), "plank_dark")
    mb.box((0, y0 + 0.03, z + 0.06 + side / 2), (half * 2, 0.07, side), "plank")
    mb.box((0, y1 - 0.03, z + 0.06 + side * 0.36), (half * 2, 0.07, side * 0.72), "plank")


def driver_seat(mb, y=-0.95, z=1.72, w=1.4):
    mb.box((0, y, z), (w, 0.42, 0.07), "plank")
    mb.box((0, y + 0.2, z + 0.22), (w, 0.06, 0.4), "plank")
    for sx in (-1, 1):
        mb.box((sx * (w / 2 - 0.05), y, z - 0.18), (0.07, 0.36, 0.3), "plank_dark")
    mb.box((0, y - 0.35, z - 0.5), (w - 0.1, 0.38, 0.06), "plank_dark")


def merchant_wagon(name, cover="canvas", coat="coat_brown", mane="mane_dark", open_=False):
    def build():
        mb = kit.begin()
        wagon_bed(mb)
        driver_seat(mb)
        a1 = axle(mb, "axle_rear", 1.55, 0.62, 0.93, 0.94)
        a2 = axle(mb, "axle_front", -0.45, 0.5, 0.93, 0.94)
        if open_:
            crate(mb, -0.3, 1.75, 1.06, 0.7)
            crate(mb, 0.38, 1.1, 1.06, 0.55)
            crate(mb, -0.3, 1.75, 1.83, 0.45)
            barrel(mb, -0.35, 0.95, 1.06)
            barrel(mb, 0.36, 1.8, 1.06, 0.75, 0.27)
            sack(mb, 0.35, 0.3, 1.06, 0.26)
            sack(mb, -0.3, 0.2, 1.06, 0.3)
            sack(mb, 0.0, -0.3, 1.06, 0.24)
            rope(mb, (-0.78, 0.6, 1.66), (0.78, 1.4, 1.66), 0.018)
            rope(mb, (-0.78, 1.4, 1.66), (0.78, 0.6, 1.66), 0.018)
        else:
            arched_cover(mb, -0.55, 2.2, 0.8, 1.58, 1.05, (cover, cover + "_shade"), cover + "_trim")
            crate(mb, 0.25, 2.5, 0.95, 0.5)
            mb.box((0, 2.45, 0.92), (1.3, 0.6, 0.06), "plank_dark")
            barrel(mb, -0.35, 2.45, 0.95, 0.6, 0.22)
        beam(mb, (0.72, -1.1, 1.6), (0.72, -1.25, 2.35), 0.03, "iron")
        beam(mb, (0.72, -1.25, 2.35), (0.72, -1.5, 2.35), 0.025, "iron")
        lantern(mb, 0.72, -1.5, 2.02)
        shafts(mb, -1.1, -3.4)
        horse = draft_animal(mb, -2.8, "h_", "horse", coat, mane)
        finish(mb, name, [horse], [a1, a2])
    return build


def ox_cart(name, cargo, coat="coat_ox"):
    def build():
        mb = kit.begin()
        mb.box((0, 0.8, 1.12), (1.7, 2.7, 0.12), "plank_dark")
        for k in range(5):
            mb.box((-0.68 + 0.34 * k, 0.8, 1.19), (0.3, 2.66, 0.03), "plank" if k % 2 else "plank_light")
        for sx in (-1, 1):
            for yy in (-0.4, 0.8, 2.0):
                mb.box((sx * 0.82, yy, 1.52), (0.08, 0.08, 0.72), "pole_dark")
            mb.box((sx * 0.82, 0.8, 1.82), (0.07, 2.6, 0.07), "pole")
            mb.box((sx * 0.82, 0.8, 1.48), (0.05, 2.6, 0.06), "pole")
        mb.box((0, -0.5, 1.5), (1.7, 0.07, 0.6), "plank")
        a1 = axle(mb, "axle", 0.9, 0.72, 1.02, 1.06)
        beam(mb, (0, -0.5, 1.05), (0, -3.25, 1.3), 0.07, "pole")
        beam(mb, (-0.55, -3.2, 1.66), (0.55, -3.2, 1.66), 0.07, "pole_dark")
        for sx in (-0.3, 0.3):
            beam(mb, (sx, -3.2, 1.66), (sx * 1.2, -3.2, 1.1), 0.03, "pole_dark")
        rnd = random.Random(4)
        z = 1.21
        if cargo == "logs":
            for i, (xx, zz) in enumerate(((-0.5, 0.17), (-0.16, 0.17), (0.18, 0.17), (0.52, 0.17), (-0.33, 0.47), (0.02, 0.47),
                                          (0.36, 0.47), (-0.15, 0.76), (0.2, 0.76))):
                log(mb, (xx, -0.4 + rnd.uniform(-0.08, 0.05), z + zz), (xx, 2.1 + rnd.uniform(-0.05, 0.25), z + zz), 0.17)
            rope(mb, (-0.8, 0.2, 1.3), (0, 0.2, 2.2), 0.02)
            rope(mb, (0.8, 0.2, 1.3), (0, 0.2, 2.2), 0.02)
        elif cargo == "stone":
            for xx, yy, zz, rr in ((-0.4, 0.0, 0.2, 0.36), (0.35, 0.1, 0.2, 0.38), (-0.35, 0.85, 0.22, 0.4), (0.4, 0.95, 0.2, 0.36),
                                   (-0.3, 1.7, 0.2, 0.36), (0.35, 1.75, 0.2, 0.38), (0.0, 0.45, 0.62, 0.36), (0.05, 1.3, 0.64, 0.38),
                                   (0.0, 0.9, 0.98, 0.3)):
                rock(mb, xx, yy, z + zz, rr, rnd)
        elif cargo == "hay":
            for xx, yy, zz, rr, mat in ((0, 0.2, 0.5, 0.85, "hay"), (0, 1.3, 0.55, 0.9, "hay_dark"), (0, 0.75, 1.05, 0.75, "hay"),
                                        (-0.3, 1.9, 0.4, 0.6, "hay"), (0.3, -0.2, 0.35, 0.55, "hay_dark")):
                mb.sphere((xx, yy, z + zz), rr, mat, segments=7, rings=5, scale=(1.0, 1.0, 0.75))
            beam(mb, (0.5, 0.6, 2.0), (0.75, 0.9, 3.0), 0.025, "pole")
        elif cargo == "barrels":
            for xx, yy in ((-0.4, -0.05), (0.4, -0.05), (-0.4, 0.7), (0.4, 0.7), (-0.4, 1.45), (0.4, 1.45)):
                barrel(mb, xx, yy, z, 0.9, 0.33)
            barrel(mb, 0.0, 0.33, z + 0.9, 0.8, 0.3)
        ox = draft_animal(mb, -2.45, "o_", "ox", coat, "mane_dark")
        finish(mb, name, [ox], [a1])
    return build


def carriage():
    mb = kit.begin()
    mb.box((0, 0.25, 0.98), (1.2, 2.9, 0.12), "coach_dark")
    a1 = axle(mb, "axle_rear", 1.3, 0.62, 0.9, 0.95)
    a2 = axle(mb, "axle_front", -0.9, 0.5, 0.9, 0.95)
    mb.box((0, 0.3, 1.2), (1.3, 1.7, 0.35), "coach_dark")
    mb.box((0, 0.3, 1.95), (1.48, 2.0, 1.2), "coach")
    for sx in (-1, 1):
        mb.box((sx * 0.745, 0.3, 2.05), (0.02, 0.62, 0.52), "window")
        mb.box((sx * 0.75, 0.3, 2.34), (0.03, 0.74, 0.06), "coach_trim")
        mb.box((sx * 0.75, 0.3, 1.76), (0.03, 0.74, 0.06), "coach_trim")
        for yy in (-0.07, 0.67):
            mb.box((sx * 0.75, yy, 1.9), (0.03, 0.05, 0.95), "coach_trim")
        mb.box((sx * 0.75, 0.3, 1.4), (0.03, 0.05, 0.06), "coach_trim")   # Door handle.
        for yy in (-0.45, 1.05):
            mb.box((sx * 0.745, yy, 2.08), (0.02, 0.34, 0.44), "window")
        mb.box((sx * 0.78, 0.3, 1.02), (0.3, 0.5, 0.05), "coach_dark")   # Step.
        lantern(mb, sx * 0.86, -0.72, 2.1)
    mb.box((0, 0.3, 2.6), (1.62, 2.16, 0.1), "coach_dark")
    mb.box((0, 0.3, 2.68), (1.3, 1.8, 0.08), "coach")
    for sx in (-1, 1):
        beam(mb, (sx * 0.72, -0.6, 2.86), (sx * 0.72, 1.2, 2.86), 0.02, "coach_trim")
    beam(mb, (-0.72, 1.2, 2.86), (0.72, 1.2, 2.86), 0.02, "coach_trim")
    crate(mb, -0.25, 0.75, 2.72, 0.6, 0.4)
    crate(mb, 0.35, 0.1, 2.72, 0.45, 0.35)
    mb.cylinder((-0.5, -0.1, 2.9), (0.1, -0.35, 2.9), 0.16, 0.16, "leather", segments=8)
    mb.box((0, 1.52, 1.35), (1.2, 0.5, 0.6), "plank_dark")
    mb.box((0, 1.52, 1.68), (1.26, 0.56, 0.06), "leather")
    driver_seat(mb, -1.05, 1.9, 1.3)
    beam(mb, (0, -1.3, 0.95), (0, -3.75, 1.05), 0.055, "pole")
    beam(mb, (-0.95, -1.9, 1.0), (0.95, -1.9, 1.0), 0.045, "pole_dark")
    h1 = draft_animal(mb, -2.95, "h1_", "horse", "coat_dark", "mane_dark", x=-0.5)
    h2 = draft_animal(mb, -2.95, "h2_", "horse", "coat_grey", "mane_light", x=0.5)
    finish(mb, "wagon_carriage", [h1, h2], [a1, a2], speed=1.5)


def vardo():
    """A traveling merchant's house on wheels."""
    mb = kit.begin()
    mb.box((0, 0.5, 1.0), (1.7, 3.3, 0.14), "plank_dark")
    a1 = axle(mb, "axle_rear", 1.5, 0.6, 0.98, 0.93)
    a2 = axle(mb, "axle_front", -0.5, 0.48, 0.98, 0.93)
    mb.box((0, 0.6, 1.87), (1.6, 2.9, 1.6), "vardo")
    for zz in (1.12, 2.62):
        mb.box((0, 0.6, zz), (1.66, 2.96, 0.1), "vardo_trim")
    for sx in (-1, 1):
        for yy in (-0.85, 2.05):
            mb.box((sx * 0.8, yy, 1.87), (0.08, 0.08, 1.6), "vardo_trim")
        mb.box((sx * 0.805, 0.6, 1.95), (0.02, 0.6, 0.55), "window")
        for yy in (0.2, 1.0):
            mb.box((sx * 0.82, yy, 1.95), (0.03, 0.18, 0.6), "vardo_roof")
        mb.box((sx * 0.86, 0.6, 1.6), (0.14, 0.7, 0.1), "plank")
        for k in range(4):
            mb.sphere((sx * 0.88, 0.33 + 0.18 * k, 1.7), 0.06, "flowers", segments=5, rings=3)
        for k, yy in enumerate((1.45, 1.7)):   # Pots and pans hanging on the side.
            mb.cylinder((sx * 0.84, yy, 1.5 - 0.1 * k), (sx * 0.9, yy, 1.5 - 0.1 * k), 0.1, 0.1, "iron", segments=7)
    pts = arch(1.0, 2.66, 0.5, n=6)
    for i in range(6):
        a, b = -1.2 + 3.55 * i / 6, -1.2 + 3.55 * (i + 1) / 6
        solid(mb, [(xx, a, zz) for xx, zz in pts], (0, b - a, 0), "vardo_roof" if i % 2 == 0 else "cloth_red_shade")
    mb.cylinder((0.5, 1.3, 2.95), (0.5, 1.3, 3.5), 0.08, 0.08, "iron", segments=6)
    mb.cylinder((0.5, 1.3, 3.5), (0.5, 1.3, 3.6), 0.14, 0.02, "iron", segments=6)
    mb.box((0, 2.06, 1.75), (0.7, 0.04, 1.35), "vardo_door")           # The door, at the back.
    mb.box((0, 2.08, 2.0), (0.4, 0.03, 0.35), "window")
    mb.box((0.25, 2.09, 1.65), (0.05, 0.04, 0.05), "vardo_trim")
    for k in range(3):
        mb.box((0, 2.3 + 0.25 * k, 0.86 - 0.28 * k), (0.8, 0.26, 0.06), "plank")
    for sx in (-1, 1):
        beam(mb, (sx * 0.4, 2.2, 0.95), (sx * 0.4, 2.95, 0.12), 0.03, "plank_dark")
    mb.box((0, -1.0, 1.2), (1.5, 0.55, 0.07), "plank")                  # The driver's porch.
    mb.box((0, -0.9, 1.55), (1.3, 0.35, 0.07), "plank")
    mb.box((0, -0.87, 2.0), (0.6, 0.04, 0.5), "window")
    lantern(mb, 0.6, -1.15, 2.2)
    beam(mb, (0.6, -0.9, 2.5), (0.6, -1.15, 2.5), 0.02, "iron")
    shafts(mb, -1.25, -3.45, 0.42, 1.0, 1.05)
    horse = draft_animal(mb, -2.85, "h_", "horse", "coat_cream", "mane_light")
    finish(mb, "wagon_vardo", [horse], [a1, a2], speed=1.1)


def water_cart():
    mb = kit.begin()
    a1 = axle(mb, "axle", 0.8, 0.65, 0.88)
    for sx in (-1, 1):
        beam(mb, (sx * 0.5, -0.5, 0.86), (sx * 0.5, 2.0, 0.86), 0.06, "plank_dark")
        beam(mb, (sx * 0.5, 1.9, 0.8), (sx * 0.5, 2.0, 0.0), 0.04, "plank_dark")
    for yy in (-0.2, 0.8, 1.8):
        mb.box((0, yy, 0.98), (1.1, 0.14, 0.18), "plank_dark")
    mb.cylinder((0, -0.45, 1.6), (0, 0.75, 1.6), 0.56, 0.64, "plank", segments=12)
    mb.cylinder((0, 0.75, 1.6), (0, 1.95, 1.6), 0.64, 0.56, "plank", segments=12)
    for yy, rr in ((-0.3, 0.6), (0.4, 0.66), (1.1, 0.66), (1.8, 0.6)):
        mb.cylinder((0, yy - 0.03, 1.6), (0, yy + 0.03, 1.6), rr, rr, "iron", segments=12)
    mb.cylinder((0, 0.75, 2.2), (0, 0.75, 2.34), 0.12, 0.1, "plank_dark", segments=7)
    mb.cylinder((0, 1.95, 1.2), (0, 2.12, 1.2), 0.04, 0.04, "iron", segments=6)
    mb.box((0, 2.1, 1.14), (0.05, 0.06, 0.14), "iron")
    for sx in (-0.35, 0.35):   # Buckets on the back.
        mb.cylinder((sx, 2.1, 0.55), (sx, 2.1, 0.85), 0.11, 0.15, "plank_light", segments=8)
        mb.cylinder((sx, 2.1, 0.82), (sx, 2.1, 0.86), 0.13, 0.13, "water", segments=8)
        rope(mb, (sx, 2.1, 0.85), (sx, 2.0, 1.0))
    shafts(mb, -0.5, -3.0, 0.42, 0.86, 1.05)
    horse = draft_animal(mb, -2.4, "h_", "horse", "coat_grey", "mane_dark")
    finish(mb, "cart_water", [horse], [a1], speed=1.6)


def sled():
    mb = kit.begin()
    for sx in (-1, 1):
        beam(mb, (sx * 0.62, -1.35, 0.5), (sx * 0.62, -0.85, 0.07), 0.06, "plank_dark")
        beam(mb, (sx * 0.62, -0.85, 0.07), (sx * 0.62, 1.7, 0.07), 0.06, "plank_dark")
        mb.box((sx * 0.62, 0.42, 0.02), (0.05, 2.5, 0.03), "iron")
        for yy in (-0.5, 0.5, 1.5):
            mb.box((sx * 0.62, yy, 0.3), (0.08, 0.08, 0.42), "plank_dark")
    mb.box((0, 0.5, 0.55), (1.4, 2.3, 0.08), "plank")
    for sx in (-1, 1):
        mb.box((sx * 0.66, 0.5, 0.78), (0.06, 2.3, 0.38), "plank")
    rnd = random.Random(2)
    for row in range(3):   # Firewood across the sled.
        for k in range(8 - row):
            log(mb, (-0.6, -0.45 + 0.28 * k + 0.14 * row + rnd.uniform(-0.02, 0.02), 0.72 + 0.24 * row),
                (0.6, -0.45 + 0.28 * k + 0.14 * row + rnd.uniform(-0.02, 0.02), 0.72 + 0.24 * row), 0.12)
    rope(mb, (-0.68, 0.3, 0.6), (0, 0.3, 1.5), 0.02)
    rope(mb, (0.68, 0.3, 0.6), (0, 0.3, 1.5), 0.02)
    shafts(mb, -1.3, -3.2, 0.45, 0.5, 1.05)
    horse = draft_animal(mb, -2.6, "h_", "horse", "coat_brown", "mane_light")
    finish(mb, "sled_horse", [horse], [], move_clip="slide")


def wheelbarrow(name, cargo):
    def build():
        mb = kit.begin()
        w = {"axle": 1.0}
        wheel(mb, (0, -0.8, 0.28), 0.28, "axle", width=0.07)
        mb.cylinder((-0.14, -0.8, 0.28), (0.14, -0.8, 0.28), 0.025, 0.025, "iron", w, segments=6)
        for sx in (-1, 1):
            beam(mb, (sx * 0.12, -0.8, 0.28), (sx * 0.38, 1.25, 0.78), 0.035, "pole")
            beam(mb, (sx * 0.3, 0.45, 0.6), (sx * 0.33, 0.5, 0.0), 0.03, "pole_dark")
        solid(mb, [(-0.32, -0.45, 0.48), (0.32, -0.45, 0.48), (0.42, 0.6, 0.62), (-0.42, 0.6, 0.62)], (0, 0, 0.05), "plank_dark")
        for sx in (-1, 1):
            solid(mb, [(sx * 0.32, -0.45, 0.5), (sx * 0.42, 0.6, 0.64), (sx * 0.5, 0.6, 0.98), (sx * 0.4, -0.52, 0.86)],
                  (sx * 0.04, 0, 0), "plank")
        solid(mb, [(-0.32, -0.45, 0.5), (0.32, -0.45, 0.5), (0.4, -0.52, 0.86), (-0.4, -0.52, 0.86)], (0, -0.04, 0), "plank")
        solid(mb, [(-0.42, 0.6, 0.64), (0.42, 0.6, 0.64), (0.5, 0.6, 0.98), (-0.5, 0.6, 0.98)], (0, 0.04, 0), "plank")
        rnd = random.Random(6)
        if cargo == "stone":
            for xx, yy, zz, rr in ((-0.15, -0.15, 0.72, 0.2), (0.15, 0.2, 0.76, 0.22), (-0.1, 0.35, 0.82, 0.18), (0.1, -0.25, 0.8, 0.17),
                                   (0.0, 0.05, 0.98, 0.18)):
                rock(mb, xx, yy, zz, rr, rnd)
        else:
            mb.sphere((0, 0.05, 0.8), 0.4, "soil", segments=7, rings=4, scale=(0.9, 1.25, 0.55))
            beam(mb, (0.1, 0.2, 0.85), (0.3, 0.7, 1.5), 0.02, "pole")
            mb.box((0.08, 0.15, 0.82), (0.16, 0.03, 0.22), "steel")
        finish(mb, name, [], [(("axle", (0, -0.8, 0.28), (0.5, -0.8, 0.28), None), 0.28)], speed=1.2)
    return build


def plough():
    mb = kit.begin()
    beam(mb, (0, 0.2, 0.75), (0, -3.25, 1.3), 0.06, "pole")
    beam(mb, (-0.55, -3.2, 1.66), (0.55, -3.2, 1.66), 0.07, "pole_dark")
    for sx in (-0.3, 0.3):
        beam(mb, (sx, -3.2, 1.66), (sx * 1.2, -3.2, 1.1), 0.03, "pole_dark")
    beam(mb, (0, 0.2, 0.75), (0, 0.75, 0.12), 0.07, "plank_dark")
    solid(mb, [(0.0, 0.0, 0.5), (0.0, 0.85, 0.02), (0.0, 0.25, 0.02)], (0.05, 0, 0), "steel")       # Coulter and share.
    solid(mb, [(0.03, 0.2, 0.45), (0.3, 0.75, 0.3), (0.05, 0.9, 0.02), (0.03, 0.3, 0.02)], (0.03, 0.02, 0), "iron")
    for sx in (-1, 1):
        beam(mb, (0, 0.6, 0.3), (sx * 0.3, 1.6, 1.05), 0.03, "pole")
        mb.cylinder((sx * 0.3, 1.55, 1.03), (sx * 0.32, 1.78, 1.1), 0.035, 0.035, "leather", segments=6)
    beam(mb, (-0.24, 1.3, 0.83), (0.24, 1.3, 0.83), 0.025, "pole_dark")
    w = {"axle": 1.0}
    wheel(mb, (0.12, -0.6, 0.22), 0.22, "axle", width=0.05)
    mb.cylinder((0.0, -0.6, 0.22), (0.2, -0.6, 0.22), 0.02, 0.02, "iron", w, segments=6)
    beam(mb, (0.03, -0.6, 0.22), (0.0, -0.75, 0.9), 0.03, "plank_dark")
    for k in range(6):   # The furrow it leaves behind.
        mb.sphere((0.18, 1.1 + 0.32 * k, 0.03), 0.16, "soil", segments=5, rings=3, scale=(1.0, 1.4, 0.5))
    ox = draft_animal(mb, -2.45, "o_", "ox", "coat_ox_white", "mane_dark")
    finish(mb, "tool_plough_ox", [ox], [(("axle", (0, -0.6, 0.22), (0.5, -0.6, 0.22), None), 0.22)], speed=0.8, move_clip="pull")


# --- Siege engines ----------------------------------------------------------------------------


def ram():
    mb = kit.begin()
    a1 = axle(mb, "axle_rear", 1.5, 0.45, 1.2)
    a2 = axle(mb, "axle_front", -1.5, 0.45, 1.2)
    for sx in (-1, 1):
        beam(mb, (sx * 0.95, -2.3, 0.62), (sx * 0.95, 2.3, 0.62), 0.11, "plank_dark")
        for sy in (-1.9, 1.9):
            beam(mb, (sx * 0.95, sy, 0.6), (sx * 0.85, sy, 2.6), 0.09, "pole")
        beam(mb, (sx * 0.85, -2.2, 2.6), (sx * 0.85, 2.2, 2.6), 0.08, "pole_dark")
        beam(mb, (sx * 0.95, -1.9, 0.7), (sx * 0.87, 0.0, 2.55), 0.05, "pole_dark")
        beam(mb, (sx * 0.95, 1.9, 0.7), (sx * 0.87, 0.0, 2.55), 0.05, "pole_dark")
    for sy in (-2.3, 2.3):
        beam(mb, (-1.05, sy, 0.62), (1.05, sy, 0.62), 0.1, "plank_dark")
    for sy in (-1.1, 1.1):
        beam(mb, (-0.9, sy, 2.62), (0.9, sy, 2.62), 0.08, "pole_dark")
    beam(mb, (0, -2.4, 3.45), (0, 2.4, 3.45), 0.07, "pole_dark")
    for sx in (-1, 1):   # A roof of hides against arrows and fire.
        normal = (sx * 0.85, 0, 1.25)
        length = math.hypot(*normal)
        normal = (normal[0] / length * 0.05, 0, normal[2] / length * 0.05)
        for k in range(4):
            y0, y1 = -2.35 + 4.7 * k / 4, -2.35 + 4.7 * (k + 1) / 4
            solid(mb, [(sx * 1.25, y0, 2.45), (sx * 1.25, y1, 2.45), (0, y1, 3.48), (0, y0, 3.48)], normal,
                  "hide" if (k + (sx > 0)) % 2 else "hide_shade")
    w = {"ram": 1.0}
    log(mb, (0, -3.2, 1.3), (0, 2.6, 1.3), 0.24, w)
    mb.cylinder((0, -3.75, 1.3), (0, -3.2, 1.3), 0.12, 0.3, "iron", w, segments=8)
    for yy in (-2.9, -2.2, 1.9):
        mb.cylinder((0, yy - 0.06, 1.3), (0, yy + 0.06, 1.3), 0.27, 0.27, "iron", w, segments=8)
    bones = [("ram", (0, 0, 1.3), (0, -0.5, 1.3), None)]
    hang = 1.25
    for name, yy in (("rope_front", -1.1), ("rope_back", 1.1)):
        for sx in (-0.2, 0.2):
            rope(mb, (sx, yy, 2.58), (sx * 0.9, yy, 1.5), 0.025, {name: 1.0})
        bones.append((name, (0, yy, 2.58), (0, yy, 1.5), None))

    def swing(t):
        phi = 26.0 * math.sin(TAU * t) * (1.0 if math.sin(TAU * t) > 0 else 1.5)   # Back, then a longer strike forward.
        rad = math.radians(phi)
        return ({"rope_front": [(kit.X, phi)], "rope_back": [(kit.X, phi)]},
                {"ram": (0, hang * math.sin(rad), hang * (1 - math.cos(rad)))})

    finish(mb, "siege_ram", [], [a1, a2], speed=0.6, clips=[("ram", 1.8, swing, True)], extra_bones=bones)


def catapult():
    mb = kit.begin()
    a1 = axle(mb, "axle_rear", 1.3, 0.45, 1.0)
    a2 = axle(mb, "axle_front", -1.3, 0.45, 1.0)
    for sx in (-1, 1):
        beam(mb, (sx * 0.7, -1.9, 0.62), (sx * 0.7, 1.9, 0.62), 0.12, "plank_dark")
        beam(mb, (sx * 0.7, -0.3, 0.6), (sx * 0.62, -0.3, 2.6), 0.1, "pole")
        beam(mb, (sx * 0.7, -1.7, 0.7), (sx * 0.63, -0.3, 2.3), 0.06, "pole_dark")
        beam(mb, (sx * 0.7, 1.2, 0.7), (sx * 0.63, -0.3, 2.3), 0.06, "pole_dark")
    for sy in (-1.9, 0.2, 1.9):
        beam(mb, (-0.8, sy, 0.62), (0.8, sy, 0.62), 0.1, "plank_dark")
    mb.cylinder((-0.72, -0.3, 2.55), (0.72, -0.3, 2.55), 0.16, 0.16, "leather", segments=8)
    mb.cylinder((-0.6, 0.2, 0.78), (0.6, 0.2, 0.78), 0.2, 0.2, "rope", segments=8)
    pivot = (0.0, 0.2, 0.78)
    w = {"arm": 1.0}
    beam(mb, pivot, (0, 2.5, 1.08), 0.09, "pole", w)
    mb.cylinder((0, 2.5, 1.02), (0, 2.5, 1.2), 0.22, 0.3, "plank_dark", w, segments=8)
    shot0 = (0.0, 2.5, 1.32)
    rnd = random.Random(1)
    rock(mb, shot0[0], shot0[1], shot0[2], 0.22, rnd, "stone", {"shot": 1.0})
    mb.cylinder((-0.95, 1.6, 0.9), (0.95, 1.6, 0.9), 0.08, 0.08, "plank", segments=7)   # The winch.
    for sx in (-1, 1):
        beam(mb, (sx * 0.7, 1.6, 0.6), (sx * 0.7, 1.6, 1.0), 0.07, "plank_dark")
        beam(mb, (sx * 0.95, 1.6, 0.6), (sx * 0.95, 1.6, 1.2), 0.025, "pole")
    for xx, yy in ((1.4, 0.4), (1.6, 0.9), (1.35, 1.0), (1.5, 0.65)):
        rock(mb, xx, yy, 0.16 if xx != 1.5 else 0.42, 0.2, rnd, "stone")

    top, release, fire = 95.0, 50.0, 0.08

    def arm_angle(t):
        if t < fire:
            return top * (t / fire) ** 2
        if t < 0.35:
            return top - 4.0 * math.sin((t - fire) / (0.35 - fire) * math.pi * 3) * (1 - (t - fire) / (0.35 - fire))
        if t < 0.9:
            return top * (1 - kit.smooth((t - 0.35) / 0.55))
        return 0.0

    def on_arm(deg):
        rad = math.radians(deg)
        dy, dz = shot0[1] - pivot[1], shot0[2] - pivot[2]
        return pivot[1] + dy * math.cos(rad) - dz * math.sin(rad), pivot[2] + dy * math.sin(rad) + dz * math.cos(rad)

    t_release = fire * math.sqrt(release / top)
    y_rel, z_rel = on_arm(release)

    def shoot(t):
        deg = arm_angle(t)
        if t <= t_release:
            y, z = on_arm(deg)
        elif t < 0.45:
            s = (t - t_release) / (0.45 - t_release)
            y, z = y_rel - 15.0 * s, max(0.2, z_rel + 9.5 * s - 12.3 * s * s)
        elif t < 0.9:
            y, z = y_rel - 15.0, 0.2     # It lies where it fell until the arm is wound back.
        else:
            y, z = shot0[1], shot0[2]
        return {"arm": [(kit.X, deg)]}, {"shot": (0, y - shot0[1], z - shot0[2])}

    bones = [("arm", pivot, (0, 1.2, 0.95), None), ("shot", shot0, (shot0[0], shot0[1], shot0[2] + 0.3), None)]
    finish(mb, "siege_catapult", [], [a1, a2], speed=0.6, clips=[("fire", 4.0, shoot, True)], extra_bones=bones)


def ballista():
    mb = kit.begin()
    a1 = axle(mb, "axle", 0.2, 0.5, 0.85)
    beam(mb, (0, 0.2, 0.5), (0, 0.2, 1.1), 0.1, "plank_dark")
    beam(mb, (0, -1.7, 1.32), (0, 1.5, 1.12), 0.1, "plank")
    beam(mb, (0, 0.6, 1.0), (0, 2.3, 0.05), 0.07, "plank_dark")
    for sx in (-1, 1):
        beam(mb, (sx * 0.3, 0.5, 1.0), (sx * 0.6, 2.0, 0.05), 0.05, "plank_dark")
        beam(mb, (sx * 0.22, -1.45, 1.32), (sx * 1.45, -0.95, 1.36), 0.07, "bow")
        mb.box((sx * 0.22, -1.45, 1.32), (0.2, 0.3, 0.5), "plank_dark")
        mb.cylinder((sx * 0.22, -1.45, 1.02), (sx * 0.22, -1.45, 1.62), 0.09, 0.09, "rope", segments=7)
        rope(mb, (sx * 1.45, -0.95, 1.36), (0, 0.7, 1.26), 0.015, {"string": 1.0})
    mb.box((0, -1.45, 1.6), (0.7, 0.2, 0.08), "iron")
    w = {"bolt": 1.0}
    mb.cylinder((0, -1.5, 1.4), (0, 0.7, 1.3), 0.03, 0.03, "pole", w, segments=6)
    mb.cylinder((0, -1.85, 1.415), (0, -1.5, 1.4), 0.0, 0.07, "steel", w, segments=4)
    for sx in (-1, 1):
        solid(mb, [(0, 0.35, 1.31), (0, 0.7, 1.3), (sx * 0.1, 0.7, 1.36)], (0, 0, 0.012), "cloth_red", w)
    mb.cylinder((-0.4, 1.3, 1.2), (0.4, 1.3, 1.2), 0.07, 0.07, "plank_dark", segments=7)
    for sx in (-1, 1):
        beam(mb, (sx * 0.4, 1.3, 1.2), (sx * 0.4, 1.5, 1.5), 0.02, "iron")
    for k in range(4):   # Spare bolts.
        beam(mb, (0.9 + 0.08 * k, 0.6, 0.05), (0.9 + 0.08 * k, 2.4, 0.05), 0.025, "pole")

    def shoot(t):
        if t < 0.1:
            fly, pull = 0.0, 0.0
        elif t < 0.3:
            s = (t - 0.1) / 0.2
            fly, pull = -18.0 * s, -1.25 * min(1.0, s * 6)
        elif t < 0.85:
            fly, pull = -18.0, -1.25 * (1 - kit.smooth((t - 0.45) / 0.4)) if t > 0.45 else -1.25
        else:
            fly, pull = 0.0, 0.0
        return {}, {"bolt": (0, fly, -(fly / 18.0) ** 2), "string": (0, pull, 0)}

    bones = [("bolt", (0, 0.7, 1.3), (0, -0.5, 1.36), None), ("string", (0, 0.7, 1.26), (0, 0.2, 1.26), None)]
    finish(mb, "siege_ballista", [], [a1], speed=0.8, clips=[("fire", 3.0, shoot, True)], extra_bones=bones)


def siege_tower():
    mb = kit.begin()
    a1 = axle(mb, "axle_rear", 1.15, 0.5, 1.72)
    a2 = axle(mb, "axle_front", -1.15, 0.5, 1.72)
    floors = (0.62, 3.0, 5.4)
    top = 7.6

    def corner(sx, sy, z):
        k = 1.5 - 0.35 * (z - 0.5) / (top - 0.5)
        return (sx * k, sy * k, z)

    for sx in (-1, 1):
        for sy in (-1, 1):
            beam(mb, corner(sx, sy, 0.5), corner(sx, sy, top), 0.12, "pole")
    for z in floors + (top,):
        k = 1.5 - 0.35 * (z - 0.5) / (top - 0.5)
        mb.box((0, 0, z), (2 * k + 0.2, 2 * k + 0.2, 0.12), "plank_dark")
        for i in range(6):
            mb.box((-k + k * 2 * (i + 0.5) / 6, 0, z + 0.07), (k * 2 / 6 - 0.03, 2 * k, 0.03), "plank" if i % 2 else "plank_light")
    for a, b in zip(floors, floors[1:] + (top,)):
        for sx in (-1, 1):   # Braced sides.
            beam(mb, corner(sx, -1, a + 0.1), corner(sx, 1, b - 0.1), 0.05, "pole_dark")
            beam(mb, corner(sx, 1, a + 0.1), corner(sx, -1, b - 0.1), 0.05, "pole_dark")
        beam(mb, corner(-1, 1, a + 0.1), corner(1, 1, b - 0.1), 0.05, "pole_dark")
    for i, (a, b) in enumerate(zip((0.5,) + floors[1:], floors[1:] + (top,))):   # Hides on the front.
        hi = b if i < 2 else 5.4
        if hi > a:
            for sx in (-1, 0):
                p0, p1 = corner(-1, -1, a), corner(1, -1, a)
                q0, q1 = corner(-1, -1, hi), corner(1, -1, hi)
                mid_low = ((p0[0] + p1[0]) / 2, p0[1], a)
                mid_high = ((q0[0] + q1[0]) / 2, q0[1], hi)
                ring = [p0, mid_low, mid_high, q0] if sx < 0 else [mid_low, p1, q1, mid_high]
                solid(mb, ring, (0, -0.05, 0), "hide" if (i + sx) % 2 else "hide_shade")
    k = 1.5 - 0.35
    for sx in (-1, 1):   # Parapet on top.
        mb.box((sx * (k + 0.05), 0, top + 0.5), (0.08, 2 * k + 0.2, 0.9), "plank")
        for m in range(3):
            mb.box((sx * (k + 0.05), -k + 0.4 + m * (k - 0.4), top + 1.15), (0.08, 0.45, 0.4), "plank_dark")
    mb.box((0, k + 0.05, top + 0.5), (2 * k + 0.2, 0.08, 0.9), "plank")
    for sx in (-1, 1):
        mb.box((sx * (k - 0.15), -k - 0.05, top + 0.5), (0.5, 0.08, 0.9), "plank")
    hinge_y = -(1.5 - 0.35 * (5.4 - 0.5) / (top - 0.5)) - 0.1
    w = {"bridge": 1.0}
    mb.box((0, hinge_y, 5.4 + 1.1), (1.7, 0.1, 2.2), "plank", w)
    for zz in (5.7, 6.5, 7.3):
        mb.box((0, hinge_y - 0.06, zz), (1.74, 0.04, 0.1), "iron", w)
    for sx in (-1, 1):
        rope(mb, (sx * 0.8, hinge_y, 7.5), (sx * 0.9, hinge_y + 0.5, top + 0.2), 0.02)
    for sy in (0.2, 0.75):   # A ladder inside, floor to floor.
        beam(mb, (0.6, sy, 0.6), (0.6, sy + 0.0, top), 0.04, "pole")
    for i in range(18):
        beam(mb, (0.6, 0.2, 0.9 + 0.37 * i), (0.6, 0.75, 0.9 + 0.37 * i), 0.025, "pole_dark")
    beam(mb, (0, 0, top), (0, 0, top + 2.2), 0.04, "pole")
    solid(mb, [(0, 0, top + 2.15), (0, 0.9, top + 1.95), (0, 0, top + 1.6)], (0.02, 0, 0), "cloth_red")

    def drop(t):
        s = kit.smooth(min(1.0, t / 0.7))
        bounce = 6.0 * math.sin((t - 0.7) / 0.3 * math.pi) * (1 - (t - 0.7) / 0.3) if t > 0.7 else 0.0
        return {"bridge": [(kit.X, 90.0 * s - bounce)]}, {}

    bones = [("bridge", (0, hinge_y, 5.4), (0, hinge_y, 6.4), None)]
    finish(mb, "siege_tower", [], [a1, a2], speed=0.4, clips=[("drop", 1.6, drop, False)], extra_bones=bones)


# --- Others ------------------------------------------------------------------------------------


def mine_cart():
    mb = kit.begin()
    rnd = random.Random(9)
    for k in range(10):
        mb.box((0, -2.7 + 0.6 * k, 0.05), (1.3, 0.2, 0.1), "plank_dark")
    for sx in (-1, 1):
        mb.box((sx * 0.4, 0, 0.14), (0.07, 6.0, 0.09), "iron")
    for sx in (-1, 1):   # A buffer stop at the far end.
        beam(mb, (sx * 0.4, 2.85, 0.1), (sx * 0.4, 2.6, 0.75), 0.06, "plank_dark")
    mb.box((0, 2.62, 0.7), (1.0, 0.12, 0.16), "plank")
    w = {"cart": 1.0}
    mb.box((0, 0, 0.46), (0.75, 1.25, 0.1), "plank_dark", w)
    solid(mb, [(-0.4, -0.62, 0.5), (0.4, -0.62, 0.5), (0.5, -0.72, 1.1), (-0.5, -0.72, 1.1)], (0, 0.05, 0), "plank", w)
    solid(mb, [(-0.4, 0.62, 0.5), (0.4, 0.62, 0.5), (0.5, 0.72, 1.1), (-0.5, 0.72, 1.1)], (0, -0.05, 0), "plank", w)
    for sx in (-1, 1):
        solid(mb, [(sx * 0.4, -0.62, 0.5), (sx * 0.4, 0.62, 0.5), (sx * 0.5, 0.72, 1.1), (sx * 0.5, -0.72, 1.1)], (-sx * 0.05, 0, 0),
              "plank", w)
        for yy in (-0.66, 0.66):
            beam(mb, (sx * 0.41, yy * 0.95, 0.5), (sx * 0.51, yy * 1.09, 1.12), 0.035, "iron", w)
    mb.box((0, 0, 1.11), (1.06, 1.5, 0.05), "iron", w)
    mb.box((0, 0, 0.9), (0.9, 1.3, 0.3), "ore", w)
    for xx, yy, rr, mat in ((-0.2, -0.3, 0.22, "ore"), (0.2, -0.1, 0.2, "ore_glint"), (-0.1, 0.25, 0.24, "ore"), (0.22, 0.4, 0.18, "ore"),
                            (0.0, 0.0, 0.2, "ore_glint"), (-0.25, 0.5, 0.15, "ore_glint")):
        rock(mb, xx, yy, 1.12 + rr * 0.3, rr, rnd, mat, w)
    r = 0.2
    bones = [("cart", (0, 0, 0.5), (0, -0.5, 0.5), None)]
    for name, yy in (("mwheel_f", -0.42), ("mwheel_b", 0.42)):
        for sx in (-1, 1):
            mb.cylinder((sx * 0.36, yy, r + 0.18), (sx * 0.44, yy, r + 0.18), r, r, "iron", {name: 1.0}, segments=8)
            mb.box((sx * 0.45, yy, r + 0.18), (0.02, 0.3, 0.06), "steel", {name: 1.0})
            mb.box((sx * 0.45, yy, r + 0.18), (0.02, 0.06, 0.3), "steel", {name: 1.0})
        mb.cylinder((-0.4, yy, r + 0.18), (0.4, yy, r + 0.18), 0.03, 0.03, "iron", {name: 1.0}, segments=6)
        bones.append((name, (0, yy, r + 0.18), (0.4, yy, r + 0.18), "cart"))

    def roll(t):
        y = 1.6 * math.sin(TAU * t)
        turn = [(kit.X, math.degrees(-y / r))]
        return {"mwheel_f": turn, "mwheel_b": turn}, {"cart": (0, y, 0)}

    finish(mb, "cart_mine", [], [], clips=[("roll", 5.0, roll, True)], extra_bones=bones)


def lathe(mb, profile, sectors, mats, weights):
    """A surface of revolution around Z through (radius, z) points, closed
    at both ends, with the materials alternating by sector."""
    bm = mb.bm
    rings = [[bm.verts.new((r * math.cos(TAU * i / sectors), r * math.sin(TAU * i / sectors), z)) for i in range(sectors)]
             for r, z in profile]
    faces = []
    for j in range(len(profile) - 1):
        for i in range(sectors):
            k = (i + 1) % sectors
            faces.append((bm.faces.new((rings[j][i], rings[j][k], rings[j + 1][k], rings[j + 1][i])), i))
    faces.append((bm.faces.new(list(reversed(rings[0]))), 0))
    faces.append((bm.faces.new(rings[-1]), 0))
    verts = [v for ring in rings for v in ring]
    mb._finish(verts, mats[0], weights)
    for face, i in faces:
        face.material_index = mb._material_index(mats[i % len(mats)])


def balloon():
    """A fantasy way to travel: a hot air balloon with a wicker basket."""
    mb = kit.begin()
    w = {"balloon": 1.0}
    lathe(mb, [(0.75, 3.2), (1.3, 3.8), (2.3, 4.9), (3.05, 6.2), (3.3, 7.5), (2.85, 8.7), (1.75, 9.6), (0.5, 10.0)], 12,
          ("balloon_a", "balloon_b"), w)
    mb.cylinder((0, 0, 3.12), (0, 0, 3.24), 0.8, 0.8, "rope", w, segments=12)
    mb.box((0, 0, 0.75), (1.3, 1.3, 0.95), "wicker", w)
    for zz in (0.32, 0.75, 1.2):
        mb.box((0, 0, zz), (1.36, 1.36, 0.08), "wicker_dark", w)
    mb.box((0, 0, 1.25), (1.42, 1.42, 0.07), "leather", w)
    for sx in (-1, 1):
        for sy in (-1, 1):
            rope(mb, (sx * 0.65, sy * 0.65, 1.25), (sx * 0.55, sy * 0.55, 3.15), 0.02, w)
            beam(mb, (sx * 0.65, sy * 0.65, 1.25), (sx * 0.3, sy * 0.3, 2.35), 0.025, "iron", w)
        sack(mb, sx * 0.78, 0.2, 0.55, 0.16, w)
        sack(mb, 0.2, sx * 0.78, 0.5, 0.16, w)
    mb.cylinder((0, 0, 2.3), (0, 0, 2.55), 0.3, 0.22, "iron", w, segments=8)
    mb.cylinder((0, 0, 2.55), (0, 0, 3.3), 0.2, 0.0, "flame", w, segments=5)
    mb.cylinder((0, 0, 2.55), (0, 0, 3.0), 0.1, 0.0, "flame_core", w, segments=5)
    mb.box((0, 0, 0.14), (1.2, 1.2, 0.28), "wicker_dark", w)
    mb.box((1.9, 0.4, 0.15), (0.12, 0.12, 0.3), "pole_dark")           # The mooring stake stays on the ground.
    mb.cylinder((1.9, 0.4, 0.05), (1.9, 0.4, 0.12), 0.3, 0.3, "rope", segments=8)
    bones = [("balloon", (0, 0, 0.3), (0, 0, 3.0), None)]

    def floating(t):
        return ({"balloon": [(kit.X, 2.5 * math.sin(TAU * t)), (kit.Y, 2.0 * math.sin(TAU * t + 1.3)), (kit.Z, 12.0 * math.sin(TAU * t))]},
                {"balloon": (0.15 * math.sin(TAU * t), 0, 1.6 + 0.3 * math.sin(TAU * 2 * t))})

    finish(mb, "balloon_airship", [], [], clips=[("float", 8.0, floating, True)], extra_bones=bones)


# --- People --------------------------------------------------------------------------------------


def riding_horse(name, coat, mane, cloth):
    """A saddled horse, for a rider the game would seat on it."""
    def build():
        mb = kit.begin()
        horse = draft_animal(mb, 0.0, "h_", "horse", coat, mane, harness=False)
        w = {"h_body": 1.0}
        solid(mb, [(-0.38, -0.3, 1.62), (0.38, -0.3, 1.62), (0.4, 0.35, 1.6), (-0.4, 0.35, 1.6)], (0, 0, 0.04), cloth, w)       # The blanket.
        for sx in (-1, 1):
            solid(mb, [(sx * 0.38, -0.3, 1.62), (sx * 0.38, 0.35, 1.62), (sx * 0.42, 0.3, 1.2), (sx * 0.42, -0.25, 1.2)], (sx * 0.03, 0, 0), cloth, w)
            beam(mb, (sx * 0.4, -0.05, 1.5), (sx * 0.42, -0.02, 0.95), 0.015, "leather", w)                                   # Stirrups.
            mb.box((sx * 0.42, -0.02, 0.9), (0.05, 0.14, 0.06), "iron", w)
        mb.box((0, 0.02, 1.7), (0.4, 0.5, 0.1), "leather", w)                                                                  # The saddle.
        mb.box((0, -0.2, 1.8), (0.26, 0.08, 0.14), "leather", w)
        mb.box((0, 0.28, 1.78), (0.36, 0.08, 0.12), "leather", w)
        mb.cylinder((0, 0.45, 1.66), (0, 0.75, 1.62), 0.12, 0.1, "sack", w, segments=7)                                         # A bedroll behind it.
        wh = {"h_head": 1.0}
        for sx in (-1, 1):
            beam(mb, (sx * 0.1, -1.38, 1.8), (sx * 0.16, -1.05, 2.0), 0.012, "leather", wh)
        rope(mb, (0.1, -1.38, 1.8), (0.2, -0.25, 1.84), 0.012, {"h_neck": 1.0})                                                 # Reins to the saddle.
        rope(mb, (-0.1, -1.38, 1.8), (-0.2, -0.25, 1.84), 0.012, {"h_neck": 1.0})
        finish(mb, name, [horse], [], speed=1.3, move_clip="walk")
    return build


def passenger_wagon():
    """An open wagon with three benches, for moving people."""
    mb = kit.begin()
    wagon_bed(mb, -1.1, 2.6, 0.8, 1.0, 0.4)
    a1 = axle(mb, "axle_rear", 1.9, 0.62, 0.98, 0.94)
    a2 = axle(mb, "axle_front", -0.4, 0.5, 0.98, 0.94)
    driver_seat(mb, -0.95, 1.72, 1.5)
    for y in (0.3, 1.2, 2.1):
        mb.box((0, y, 1.5), (1.5, 0.38, 0.06), "plank_light")
        mb.box((0, y + 0.18, 1.72), (1.5, 0.05, 0.36), "plank")
        for sx in (-0.6, 0.6):
            mb.box((sx, y, 1.28), (0.07, 0.3, 0.42), "plank_dark")
    for sx in (-1, 1):                                                                 # A canopy on four posts.
        for y in (-0.7, 2.5):
            mb.cylinder((sx * 0.78, y, 1.4), (sx * 0.78, y, 2.75), 0.035, 0.03, "pole", segments=6)
    for k in range(4):
        y0, y1 = -0.9 + 0.9 * k, -0.9 + 0.9 * (k + 1)
        solid(mb, [(-0.95, y0, 2.7), (0.95, y0, 2.7), (0.95, y1, 2.7), (-0.95, y1, 2.7)], (0, 0, 0.05), "cloth_red" if k % 2 else "canvas")
        for sx in (-1, 1):
            solid(mb, [(sx * 0.95, y0, 2.7), (sx * 0.95, y1, 2.7), (sx * 0.95, (y0 + y1) / 2, 2.45)], (sx * 0.02, 0, 0), "coach_trim")
    for k in range(2):                                                                 # Steps at the back.
        mb.box((0, 2.8 + 0.25 * k, 0.75 - 0.3 * k), (0.8, 0.25, 0.05), "plank_dark")
    crate(mb, 0.4, 2.35, 1.06, 0.4)
    beam(mb, (0, -1.1, 0.95), (0, -3.6, 1.05), 0.055, "pole")
    beam(mb, (-0.95, -1.75, 1.0), (0.95, -1.75, 1.0), 0.045, "pole_dark")
    h1 = draft_animal(mb, -2.85, "h1_", "horse", "coat_brown", "mane_dark", x=-0.5)
    h2 = draft_animal(mb, -2.85, "h2_", "horse", "coat_cream", "mane_light", x=0.5)
    finish(mb, "wagon_passenger", [h1, h2], [a1, a2], speed=1.4)


def sedan_chair():
    """A covered chair on two poles, carried by two bearers."""
    mb = kit.begin()
    for sx in (-1, 1):
        beam(mb, (sx * 0.42, -1.9, 0.85), (sx * 0.42, 1.9, 0.85), 0.04, "pole")
        for sy in (-1.85, 1.85):
            mb.cylinder((sx * 0.42, sy, 0.84), (sx * 0.42, sy + (0.08 if sy > 0 else -0.08), 0.84), 0.055, 0.055, "leather", segments=6)
        for sy in (-0.45, 0.45):                                                       # Legs it rests on when set down.
            mb.cylinder((sx * 0.38, sy, 0), (sx * 0.38, sy, 0.5), 0.035, 0.03, "pole_dark", segments=5)
    mb.box((0, 0, 0.5), (0.85, 1.0, 0.08), "coach_dark")
    for sx in (-1, 1):
        mb.box((sx * 0.42, 0.3, 1.2), (0.04, 0.4, 1.35), "coach")
        mb.box((sx * 0.42, -0.25, 0.85), (0.04, 0.5, 0.65), "coach")
        mb.box((sx * 0.43, -0.25, 1.5), (0.02, 0.4, 0.5), "window")
        for sy in (-0.5, 0.0, 0.5):
            mb.box((sx * 0.42, sy, 1.2), (0.06, 0.05, 1.4), "coach_trim")
    mb.box((0, 0.5, 1.2), (0.85, 0.04, 1.35), "coach")
    mb.box((0, 0.2, 0.9), (0.7, 0.4, 0.08), "cloth_red")                                 # The seat.
    mb.box((0, 0.42, 1.25), (0.7, 0.06, 0.6), "cloth_red")
    solid(mb, [(-0.5, -0.6, 1.9), (0.5, -0.6, 1.9), (0.5, 0.6, 1.9), (-0.5, 0.6, 1.9)], (0, 0, 0.06), "coach_dark")
    for i in range(4):
        a0, a1 = TAU * (i + 0.5) / 4, TAU * (i + 1.5) / 4
        solid(mb, [(math.cos(a0) * 0.72, math.sin(a0) * 0.85, 1.96), (math.cos(a1) * 0.72, math.sin(a1) * 0.85, 1.96), (0, 0, 2.3)], (0, 0, 0.04),
              "coach" if i % 2 else "coach_dark")
    mb.sphere((0, 0, 2.36), 0.07, "coach_trim", segments=6, rings=4)
    for sx in (-1, 1):                                                                 # Curtains at the front.
        solid(mb, [(sx * 0.4, -0.5, 1.85), (sx * 0.15, -0.5, 1.85), (sx * 0.3, -0.5, 0.9), (sx * 0.4, -0.5, 0.9)], (0, -0.02, 0), "cloth_blue")
    kit.save(mb, FAMILY, "litter_sedan_chair", COLORS)


def chariot():
    """A light war chariot with two horses."""
    mb = kit.begin()
    a1 = axle(mb, "axle", 0.5, 0.55, 0.85)
    mb.box((0, 0.35, 0.68), (1.2, 1.1, 0.07), "plank_dark")
    for i in range(7):                                                                 # A curved front of wicker and hide.
        a0, a1b = math.pi + math.pi * i / 7, math.pi + math.pi * (i + 1) / 7
        solid(mb, [(math.cos(a0) * 0.6, 0.2 + math.sin(a0) * 0.75, 0.7), (math.cos(a1b) * 0.6, 0.2 + math.sin(a1b) * 0.75, 0.7),
                   (math.cos(a1b) * 0.62, 0.2 + math.sin(a1b) * 0.78, 1.55), (math.cos(a0) * 0.62, 0.2 + math.sin(a0) * 0.78, 1.55)],
              (math.cos((a0 + a1b) / 2) * 0.03, math.sin((a0 + a1b) / 2) * 0.03, 0), "cloth_red" if i % 2 else "hide")
    for sx in (-1, 1):
        beam(mb, (sx * 0.6, 0.2, 1.55), (sx * 0.6, 0.85, 1.1), 0.03, "coach_trim")
    mb.cylinder((0.45, 0.6, 0.72), (0.5, 0.75, 2.3), 0.02, 0.02, "pole", segments=5)        # Javelins at hand.
    mb.cylinder((0.5, 0.75, 2.3), (0.51, 0.78, 2.55), 0.04, 0.0, "steel", segments=4)
    mb.cylinder((0.35, 0.65, 0.72), (0.38, 0.8, 2.2), 0.02, 0.02, "pole", segments=5)
    mb.cylinder((-0.5, 0.2, 1.0), (-0.52, 0.16, 1.02), 0.3, 0.3, "cloth_blue", segments=9)  # A shield on the side.
    beam(mb, (0, -0.4, 0.7), (0, -2.9, 1.25), 0.05, "pole")
    beam(mb, (-0.95, -2.6, 1.62), (0.95, -2.6, 1.62), 0.045, "pole_dark")
    h1 = draft_animal(mb, -2.1, "h1_", "horse", "coat_dark", "mane_dark", x=-0.5)
    h2 = draft_animal(mb, -2.1, "h2_", "horse", "coat_grey", "mane_light", x=0.5)
    finish(mb, "chariot_war", [h1, h2], [a1], speed=2.4)


MODELS = {
    "wagon_merchant": merchant_wagon("wagon_merchant", "canvas"),
    "wagon_merchant_blue": merchant_wagon("wagon_merchant_blue", "cloth_blue", "coat_grey", "mane_light"),
    "wagon_merchant_red": merchant_wagon("wagon_merchant_red", "cloth_red", "coat_dark"),
    "wagon_merchant_open": merchant_wagon("wagon_merchant_open", coat="coat_cream", mane="mane_light", open_=True),
    "cart_ox_logs": ox_cart("cart_ox_logs", "logs"),
    "cart_ox_stone": ox_cart("cart_ox_stone", "stone", "coat_ox_white"),
    "cart_ox_hay": ox_cart("cart_ox_hay", "hay"),
    "cart_ox_barrels": ox_cart("cart_ox_barrels", "barrels", "coat_ox_white"),
    "cart_ox_empty": ox_cart("cart_ox_empty", "empty"),
    "wagon_carriage": carriage,
    "wagon_vardo": vardo,
    "cart_water": water_cart,
    "sled_horse": sled,
    "cart_wheelbarrow_stone": wheelbarrow("cart_wheelbarrow_stone", "stone"),
    "cart_wheelbarrow_soil": wheelbarrow("cart_wheelbarrow_soil", "soil"),
    "tool_plough_ox": plough,
    "siege_ram": ram,
    "siege_catapult": catapult,
    "siege_ballista": ballista,
    "siege_tower": siege_tower,
    "cart_mine": mine_cart,
    "balloon_airship": balloon,
    "mount_horse": riding_horse("mount_horse", "coat_brown", "mane_dark", "cloth_blue"),
    "mount_horse_grey": riding_horse("mount_horse_grey", "coat_grey", "mane_light", "cloth_red"),
    "mount_horse_black": riding_horse("mount_horse_black", "coat_dark", "mane_dark", "canvas"),
    "wagon_passenger": passenger_wagon,
    "litter_sedan_chair": sedan_chair,
    "chariot_war": chariot,
}

kit.run(MODELS, FAMILY)
