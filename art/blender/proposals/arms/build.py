"""Arms proposals: the weapon, the shield and the helmet of each of the nine
races. Hand-held: the grip at the origin, the blade up, shields face -Y.
See ../LEEME.md.

    blender --background --factory-startup --python art/blender/proposals/arms/build.py -- [ids]
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import _kit as kit  # noqa: E402
import _shapes  # noqa: E402
import common  # noqa: E402
from _shapes import TAU, beam, rope, solid  # noqa: E402

FAMILY = "arms"
C = common.rgb
COLORS = {
    **_shapes.COLORS,
    "steel_dark": C(0x6E767E), "bronze": C(0x9A7A3A), "obsidian": C(0x2A2630), "obsidian_light": C(0x4A4458), "glow_violet": C(0xB98CFF), "glow_gold": C(0xFFD66A),
    "bone": C(0xE0D8C0), "bone_dark": C(0xB8AE94), "jade": C(0x3EA878), "white": C(0xECE8DC), "cloth_blue": C(0x2E5A9A), "cloth_orange": C(0xD8892E),
    "cloth_red": C(0xC0392B), "cloth_green": C(0x3E7A4A), "lacquer": C(0xA82A24), "lacquer_dark": C(0x2A2224), "shell": C(0x4E8A5A), "shell_dark": C(0x356A44),
    "reed": C(0xB8A860), "hide": C(0x9A7050), "feather_red": C(0xC84A3A), "feather_green": C(0x3EA858), "feather_blue": C(0x3A7AC8), "cave": C(0x14110F),
    "rust": C(0x6A4A3A),
}


def save(mb, name, grip=(0, 0, 0)):
    kit.save(mb, FAMILY, name, COLORS, extras={"grip": [float(v) for v in grip]})


def flat(mb, pts, thick, mat, y=0.0):
    """A flat shape drawn in the XZ plane, `thick` deep around y."""
    solid(mb, [(px, y - thick / 2, pz) for px, pz in pts], (0, thick, 0), mat)


def strip(mb, pts, widths, thick, mat):
    """A blade that follows a line: quads between consecutive points, each as wide as said."""
    def sides(i):
        x, z = pts[i]
        a, b = pts[max(0, i - 1)], pts[min(len(pts) - 1, i + 1)]
        dx, dz = b[0] - a[0], b[1] - a[1]
        n = math.hypot(dx, dz) or 1.0
        nx, nz = -dz / n, dx / n
        return (x + nx * widths[i] / 2, z + nz * widths[i] / 2), (x - nx * widths[i] / 2, z - nz * widths[i] / 2)
    for i in range(len(pts) - 1):
        l0, r0 = sides(i)
        l1, r1 = sides(i + 1)
        flat(mb, [l0, r0, r1, l1], thick, mat)


def grip(mb, z0, z1, mat="leather", r=0.018, pommel="steel"):
    mb.cylinder((0, 0, z0), (0, 0, z1), r, r, mat, segments=6)
    mb.sphere((0, 0, z0 - 0.01), r * 1.5, pommel, segments=6, rings=4)


def ring(mb, z, r, n, size, mat, y_scale=1.0):
    for k in range(n):
        a = TAU * k / n
        mb.box((math.cos(a) * r, math.sin(a) * r * y_scale, z), size, mat, rotation_z=a)


def strap(mb, z, y=0.05):
    for dz in (0.1, -0.1):
        beam(mb, (-0.1, y, z + dz), (0.1, y, z + dz), 0.012, "leather")


def dome(mb, mat, r=0.125, z=0.1, scale=(1, 1.1, 1.0)):
    mb.sphere((0, 0, z), r, mat, segments=8, rings=5, scale=scale)


# --- Weapons ------------------------------------------------------------------------------------

def human_sword():
    mb = kit.begin()
    grip(mb, 0.0, 0.14, "leather", 0.018, "gold")
    mb.box((0, 0, 0.155), (0.22, 0.035, 0.03), "gold")
    flat(mb, [(-0.032, 0.17), (0.032, 0.17), (0.028, 0.86), (0, 0.96), (-0.028, 0.86)], 0.012, "steel")
    flat(mb, [(-0.008, 0.18), (0.008, 0.18), (0.006, 0.7), (-0.006, 0.7)], 0.018, "steel_dark")
    save(mb, "arms_human_sword", (0, 0, 0.07))


def catfolk_khopesh():
    mb = kit.begin()
    grip(mb, 0.0, 0.15, "cloth_orange", 0.018, "gold")
    mb.cylinder((0, 0, 0.15), (0, 0, 0.18), 0.04, 0.04, "gold", segments=8)
    pts = [(0, 0.18), (0, 0.42)] + [(0.2 - math.cos(a) * 0.2, 0.42 + math.sin(a) * 0.3) for a in (0.4, 0.9, 1.4, 1.9, 2.4)]
    strip(mb, pts, [0.05, 0.05, 0.06, 0.07, 0.07, 0.06, 0.01], 0.012, "bronze")
    strip(mb, pts[1:6], [0.014] * 5, 0.018, "gold")
    save(mb, "arms_catfolk_khopesh", (0, 0, 0.08))


def dwarf_axe():
    mb = kit.begin()
    mb.cylinder((0, 0, 0), (0, 0, 0.8), 0.022, 0.02, "pole_dark", segments=6)
    for z in (0.04, 0.2, 0.36):
        mb.cylinder((0, 0, z), (0, 0, z + 0.03), 0.026, 0.026, "bronze", segments=6)
    mb.box((0, 0, 0.7), (0.07, 0.05, 0.16), "iron")
    flat(mb, [(0.03, 0.76), (0.2, 0.84), (0.26, 0.62), (0.22, 0.4), (0.12, 0.48), (0.03, 0.64)], 0.02, "steel")       # A bearded blade.
    flat(mb, [(0.2, 0.84), (0.26, 0.62), (0.22, 0.4), (0.25, 0.62)], 0.006, "white")
    flat(mb, [(-0.03, 0.74), (-0.14, 0.7), (-0.03, 0.66)], 0.02, "steel_dark")
    for k in range(3):
        mb.box((0.1 + 0.035 * k, 0, 0.68 - 0.03 * k), (0.012, 0.026, 0.05), "glow_gold")
    mb.cylinder((0, 0, 0.8), (0, 0, 0.86), 0.03, 0.0, "bronze", segments=6)
    save(mb, "arms_dwarf_axe", (0, 0, 0.12))


def elf_blade():
    mb = kit.begin()
    grip(mb, 0.0, 0.16, "white", 0.016, "gold")
    for sx in (-1, 1):
        beam(mb, (0, 0, 0.165), (sx * 0.09, 0, 0.21), 0.012, "gold")
    flat(mb, [(0, 0.17), (0.04, 0.34), (0.055, 0.6), (0.03, 0.88), (0, 1.02), (-0.03, 0.88), (-0.055, 0.6), (-0.04, 0.34)], 0.01, "steel")
    flat(mb, [(0, 0.22), (0.01, 0.6), (0, 0.94), (-0.01, 0.6)], 0.016, "jade")
    save(mb, "arms_elf_blade", (0, 0, 0.08))


def dark_elf_blade():
    mb = kit.begin()
    grip(mb, 0.0, 0.15, "obsidian", 0.017, "glow_violet")
    flat(mb, [(-0.1, 0.16), (0.1, 0.16), (0.06, 0.2), (-0.06, 0.2)], 0.03, "steel_dark")
    flat(mb, [(-0.025, 0.2), (0.03, 0.2), (0.03, 0.82), (0, 0.95), (-0.025, 0.8)], 0.012, "obsidian")
    for k in range(6):                                                           # Teeth along one edge.
        z = 0.26 + 0.09 * k
        flat(mb, [(0.03, z), (0.075, z + 0.02), (0.03, z + 0.07)], 0.01, "obsidian_light")
    flat(mb, [(-0.005, 0.24), (0.006, 0.24), (0.004, 0.76), (-0.004, 0.76)], 0.018, "glow_violet")
    save(mb, "arms_dark_elf_blade", (0, 0, 0.08))


def foxfolk_katana():
    mb = kit.begin()
    mb.cylinder((0, 0, 0), (0, 0, 0.26), 0.018, 0.017, "lacquer", segments=6)
    for k in range(6):
        mb.cylinder((0, 0, 0.02 + 0.04 * k), (0, 0, 0.035 + 0.04 * k), 0.021, 0.021, "white", segments=6)
    mb.cylinder((0, 0, 0.26), (0, 0, 0.275), 0.045, 0.045, "gold", segments=8)
    pts = [(0.0 + 0.06 * (k / 8) ** 2, 0.28 + 0.085 * k) for k in range(9)]
    strip(mb, pts, [0.034, 0.034, 0.033, 0.032, 0.031, 0.03, 0.028, 0.022, 0.004], 0.009, "steel")
    mb.sphere((0, 0, -0.01), 0.022, "gold", segments=6, rings=4)
    solid(mb, [(0, -0.004, -0.02), (0.03, -0.004, -0.14), (-0.02, -0.004, -0.12)], (0, 0.008, 0), "cloth_red")
    save(mb, "arms_foxfolk_katana", (0, 0, 0.12))


def frogfolk_harpoon():
    mb = kit.begin()
    mb.cylinder((0, 0, 0), (0, 0, 1.5), 0.016, 0.014, "reed", segments=6)
    for z in (0.3, 0.75, 1.2):
        mb.cylinder((0, 0, z), (0, 0, z + 0.02), 0.02, 0.02, "pole_dark", segments=6)
    flat(mb, [(-0.022, 1.48), (0.022, 1.48), (0.016, 1.72), (0, 1.84), (-0.016, 1.72)], 0.014, "bone")
    for k, sx in enumerate((1, -1, 1)):                                           # Barbs.
        z = 1.56 + 0.07 * k
        flat(mb, [(sx * 0.016, z + 0.06), (sx * 0.06, z), (sx * 0.016, z + 0.02)], 0.012, "bone_dark")
    for k in range(4):
        mb.cylinder((0, 0, 1.4 + 0.02 * k), (0, 0, 1.415 + 0.02 * k), 0.022, 0.022, "rope", segments=6)
    for k in range(8):                                                           # The line, coiled at the butt.
        a0, a1 = TAU * k / 8, TAU * (k + 1) / 8
        rope(mb, (math.cos(a0) * 0.06, math.sin(a0) * 0.06, 0.1 + 0.004 * k), (math.cos(a1) * 0.06, math.sin(a1) * 0.06, 0.104 + 0.004 * k), 0.008)
    rope(mb, (0.06, 0, 0.13), (0.02, 0, 1.4), 0.006)
    save(mb, "arms_frogfolk_harpoon", (0, 0, 0.7))


def lizardfolk_macuahuitl():
    mb = kit.begin()
    grip(mb, 0.0, 0.2, "hide", 0.02, "jade")
    flat(mb, [(-0.03, 0.2), (0.03, 0.2), (0.055, 0.34), (0.055, 0.86), (0.03, 0.92), (-0.03, 0.92), (-0.055, 0.86), (-0.055, 0.34)], 0.026, "plank")
    for k in range(6):                                                           # Obsidian teeth along both edges.
        z = 0.36 + 0.085 * k
        for sx in (-1, 1):
            flat(mb, [(sx * 0.05, z), (sx * 0.095, z + 0.035), (sx * 0.05, z + 0.07)], 0.012, "obsidian")
    flat(mb, [(-0.02, 0.4), (0.02, 0.4), (0.02, 0.8), (-0.02, 0.8)], 0.03, "jade")
    for k, mat in enumerate(("feather_red", "feather_green", "feather_blue")):
        solid(mb, [(0, -0.004, -0.02), (-0.06 + 0.05 * k, -0.004, -0.2), (-0.02 + 0.05 * k, -0.004, -0.2)], (0, 0.008, 0), mat)
    save(mb, "arms_lizardfolk_macuahuitl", (0, 0, 0.1))


def orc_cleaver():
    mb = kit.begin()
    mb.cylinder((0, 0, 0), (0, 0, 0.24), 0.024, 0.022, "bone", segments=6)
    for k in range(4):
        mb.cylinder((0, 0, 0.03 + 0.05 * k), (0, 0, 0.05 + 0.05 * k), 0.028, 0.028, "hide", segments=6)
    flat(mb, [(-0.05, 0.24), (0.04, 0.24), (0.12, 0.36), (0.16, 0.7), (0.1, 0.86), (-0.02, 0.8), (-0.06, 0.5)], 0.02, "iron")
    flat(mb, [(0.12, 0.36), (0.16, 0.7), (0.1, 0.86), (0.13, 0.7)], 0.006, "steel")
    flat(mb, [(0.04, 0.5), (0.09, 0.5), (0.09, 0.56), (0.04, 0.56)], 0.03, "cave")                 # A hole to hang it by.
    for k in range(3):
        z = 0.42 + 0.13 * k
        flat(mb, [(-0.055, z), (-0.12, z + 0.04), (-0.05, z + 0.08)], 0.016, "rust")
    save(mb, "arms_orc_cleaver", (0, 0, 0.12))


# --- Shields ------------------------------------------------------------------------------------

def human_shield():
    mb = kit.begin()
    flat(mb, [(-0.3, 0.9), (0.3, 0.9), (0.3, 0.5), (0.18, 0.18), (0, 0.0), (-0.18, 0.18), (-0.3, 0.5)], 0.035, "cloth_blue", 0.018)
    flat(mb, [(-0.32, 0.93), (0.32, 0.93), (0.32, 0.87), (-0.32, 0.87)], 0.045, "steel", 0.018)
    flat(mb, [(-0.09, 0.3), (0.09, 0.3), (0.09, 0.62), (-0.09, 0.62)], 0.012, "gold", -0.004)       # A tower.
    for x in (-0.09, -0.02, 0.05):
        flat(mb, [(x, 0.62), (x + 0.04, 0.62), (x + 0.04, 0.7), (x, 0.7)], 0.012, "gold", -0.004)
    strap(mb, 0.55)
    save(mb, "arms_human_shield", (0, 0.05, 0.55))


def catfolk_shield():
    mb = kit.begin()
    mb.cylinder((0, 0, 0.36), (0, 0.035, 0.36), 0.36, 0.36, "cloth_orange", segments=14)
    mb.cylinder((0, -0.008, 0.36), (0, 0, 0.36), 0.375, 0.375, "bronze", segments=14)
    mb.cylinder((0, -0.014, 0.36), (0, -0.006, 0.36), 0.33, 0.33, "cloth_orange", segments=14)
    mb.sphere((0, -0.02, 0.36), 0.1, "gold", segments=8, rings=5, scale=(1, 0.5, 1))
    for k in range(10):
        a = TAU * k / 10
        flat(mb, [(math.cos(a - 0.14) * 0.14, 0.36 + math.sin(a - 0.14) * 0.14), (math.cos(a + 0.14) * 0.14, 0.36 + math.sin(a + 0.14) * 0.14),
                  (math.cos(a) * 0.3, 0.36 + math.sin(a) * 0.3)], 0.01, "gold", -0.016)
    strap(mb, 0.36)
    save(mb, "arms_catfolk_shield", (0, 0.05, 0.36))


def dwarf_shield():
    mb = kit.begin()
    flat(mb, [(-0.3, 0.0), (0.3, 0.0), (0.34, 0.1), (0.34, 0.6), (0.3, 0.7), (-0.3, 0.7), (-0.34, 0.6), (-0.34, 0.1)], 0.045, "steel_dark", 0.022)
    flat(mb, [(-0.26, 0.06), (0.26, 0.06), (0.26, 0.64), (-0.26, 0.64)], 0.012, "iron", -0.004)
    for sx in (-1, 1):
        for z in (0.08, 0.62):
            mb.sphere((sx * 0.28, -0.01, z), 0.03, "bronze", segments=5, rings=3)
    mb.box((0, -0.012, 0.35), (0.6, 0.016, 0.07), "bronze")
    mb.box((0, -0.012, 0.35), (0.07, 0.016, 0.6), "bronze")
    mb.sphere((0, -0.03, 0.35), 0.07, "bronze", segments=7, rings=4, scale=(1, 0.6, 1))
    for sx in (-1, 1):
        for sz in (-1, 1):
            mb.box((sx * 0.15, -0.012, 0.35 + sz * 0.16), (0.03, 0.012, 0.1), "glow_gold")
    strap(mb, 0.35)
    save(mb, "arms_dwarf_shield", (0, 0.06, 0.35))


def elf_shield():
    mb = kit.begin()
    shape = [(0, 0.0), (0.2, 0.25), (0.28, 0.6), (0.2, 0.86), (0, 0.98), (-0.2, 0.86), (-0.28, 0.6), (-0.2, 0.25)]
    flat(mb, shape, 0.03, "white", 0.015)
    flat(mb, [(x * 1.06, 0.5 + (z - 0.5) * 1.05) for x, z in shape], 0.012, "gold", 0.02)
    flat(mb, [(-0.012, 0.08), (0.012, 0.08), (0.012, 0.9), (-0.012, 0.9)], 0.012, "cloth_green", -0.004)
    for k in range(4):
        z = 0.25 + 0.15 * k
        for sx in (-1, 1):
            flat(mb, [(0, z), (sx * (0.2 - 0.02 * k), z + 0.14), (sx * (0.2 - 0.02 * k), z + 0.165), (0, z + 0.03)], 0.012, "cloth_green", -0.004)
    strap(mb, 0.55)
    save(mb, "arms_elf_shield", (0, 0.05, 0.55))


def dark_elf_shield():
    mb = kit.begin()
    for k in range(11):                                                          # A disc with a bite out of it, to strike past.
        a0, a1 = math.radians(40 + 280 * k / 11), math.radians(40 + 280 * (k + 1) / 11)
        flat(mb, [(0, 0.38), (math.cos(a0) * 0.38, 0.38 + math.sin(a0) * 0.38), (math.cos(a1) * 0.38, 0.38 + math.sin(a1) * 0.38)], 0.03, "obsidian" if k % 2 else "obsidian_light", 0.015)
        flat(mb, [(math.cos(a0) * 0.36, 0.38 + math.sin(a0) * 0.36), (math.cos(a0) * 0.4, 0.38 + math.sin(a0) * 0.4), (math.cos(a1) * 0.4, 0.38 + math.sin(a1) * 0.4),
                  (math.cos(a1) * 0.36, 0.38 + math.sin(a1) * 0.36)], 0.04, "steel_dark", 0.015)
    for a in (40, 320):
        r = math.radians(a)
        flat(mb, [(math.cos(r) * 0.3, 0.38 + math.sin(r) * 0.3), (math.cos(r) * 0.52, 0.38 + math.sin(r) * 0.52), (math.cos(r + 0.2) * 0.38, 0.38 + math.sin(r + 0.2) * 0.38)]
             if a == 40 else [(math.cos(r) * 0.3, 0.38 + math.sin(r) * 0.3), (math.cos(r) * 0.52, 0.38 + math.sin(r) * 0.52), (math.cos(r - 0.2) * 0.38, 0.38 + math.sin(r - 0.2) * 0.38)],
             0.02, "steel_dark", 0.01)
    mb.sphere((-0.08, -0.01, 0.38), 0.06, "glow_violet", segments=6, rings=4, scale=(1, 0.5, 1.3))
    strap(mb, 0.38)
    save(mb, "arms_dark_elf_shield", (0, 0.05, 0.38))


def foxfolk_shield():
    mb = kit.begin()
    flat(mb, [(-0.28, 0.0), (0.28, 0.0), (0.28, 0.9), (0.16, 1.02), (-0.16, 1.02), (-0.28, 0.9)], 0.03, "lacquer", 0.015)
    for z in (0.06, 0.86):
        mb.box((0, 0.0, z), (0.6, 0.04, 0.05), "lacquer_dark")
    flat(mb, [(0, 0.24), (0.12, 0.4), (0.09, 0.56), (-0.09, 0.56), (-0.12, 0.4)], 0.012, "white", -0.004)          # A white flame.
    flat(mb, [(-0.09, 0.56), (0.09, 0.56), (0.03, 0.78)], 0.012, "white", -0.004)
    flat(mb, [(-0.12, 0.4), (-0.09, 0.56), (-0.18, 0.64)], 0.012, "white", -0.004)
    beam(mb, (0, 0.04, 0.0), (0, 0.3, -0.02), 0.02, "pole")                       # The prop it stands on.
    strap(mb, 0.55)
    save(mb, "arms_foxfolk_shield", (0, 0.05, 0.55))


def frogfolk_shield():
    mb = kit.begin()
    mb.sphere((0, 0.02, 0.36), 0.36, "shell", segments=10, rings=6, scale=(1, 0.3, 1.1))
    mb.cylinder((0, 0.02, 0.36), (0, 0.05, 0.36), 0.37, 0.37, "shell_dark", segments=10)
    for k in range(6):
        a = TAU * k / 6 + 0.5
        mb.sphere((math.cos(a) * 0.2, -0.07, 0.36 + math.sin(a) * 0.22), 0.09, "shell_dark", segments=6, rings=3, scale=(1, 0.3, 1))
    mb.sphere((0, -0.1, 0.36), 0.1, "shell_dark", segments=6, rings=3, scale=(1, 0.3, 1))
    strap(mb, 0.36, 0.07)
    save(mb, "arms_frogfolk_shield", (0, 0.07, 0.36))


def lizardfolk_shield():
    mb = kit.begin()
    mb.cylinder((0, 0, 0.5), (0, 0.03, 0.5), 0.34, 0.34, "hide", segments=12)
    mb.cylinder((0, -0.008, 0.5), (0, 0, 0.5), 0.35, 0.35, "jade", segments=12)
    mb.cylinder((0, -0.014, 0.5), (0, -0.006, 0.5), 0.3, 0.3, "hide", segments=12)
    mb.cylinder((0, -0.022, 0.5), (0, -0.012, 0.5), 0.13, 0.13, "gold", segments=8)
    for k in range(4):                                                           # A stepped cross round the sun.
        a = TAU * k / 4
        mb.box((math.cos(a) * 0.21, -0.016, 0.5 + math.sin(a) * 0.21), (0.08 if k % 2 else 0.12, 0.012, 0.12 if k % 2 else 0.08), "jade")
    for k in range(7):                                                           # Feathers hang from the rim.
        x = -0.24 + 0.08 * k
        z = 0.5 - math.sqrt(max(0.0, 0.34 ** 2 - x ** 2))
        flat(mb, [(x - 0.03, z + 0.02), (x + 0.03, z + 0.02), (x, z - 0.26 + 0.05 * abs(k - 3))], 0.008, ("feather_red", "feather_green", "feather_blue")[k % 3], 0.01)
    strap(mb, 0.5)
    save(mb, "arms_lizardfolk_shield", (0, 0.05, 0.5))


def orc_shield():
    mb = kit.begin()
    for k, (x, z0, z1) in enumerate(((-0.24, 0.06, 0.7), (-0.08, 0.0, 0.82), (0.08, 0.04, 0.78), (0.24, 0.1, 0.66))):       # Rough planks of uneven length.
        mb.box((x, 0.015, (z0 + z1) / 2), (0.155, 0.035, z1 - z0), "plank_dark" if k % 2 else "pole")
    for z in (0.22, 0.56):
        mb.box((0, -0.008, z), (0.66, 0.016, 0.05), "iron")
        for x in (-0.26, -0.09, 0.09, 0.26):
            mb.cylinder((x, -0.016, z), (x, -0.11, z), 0.022, 0.0, "rust", segments=5)
    mb.sphere((0, -0.05, 0.4), 0.1, "bone", segments=7, rings=5)                  # A skull nailed in the middle.
    mb.box((0, -0.11, 0.33), (0.1, 0.06, 0.06), "bone")
    for sx in (-1, 1):
        mb.box((sx * 0.04, -0.135, 0.42), (0.035, 0.02, 0.035), "cave")
    strap(mb, 0.4)
    save(mb, "arms_orc_shield", (0, 0.05, 0.4))


# --- Helmets ------------------------------------------------------------------------------------

def human_helmet():
    mb = kit.begin()
    dome(mb, "steel")
    mb.cylinder((0, 0, 0.05), (0, 0, 0.085), 0.128, 0.128, "steel_dark", segments=8)
    mb.box((0, -0.135, 0.0), (0.03, 0.014, 0.16), "steel_dark")
    mb.cylinder((0, 0, 0.21), (0, 0, 0.26), 0.03, 0.0, "steel", segments=6)
    for sx in (-1, 1):
        solid(mb, [(sx * 0.12, -0.02, 0.06), (sx * 0.12, 0.09, 0.06), (sx * 0.11, 0.06, -0.08), (sx * 0.11, -0.01, -0.06)], (sx * 0.012, 0, 0), "leather")
    save(mb, "arms_human_helmet")


def catfolk_helmet():
    mb = kit.begin()
    dome(mb, "bronze")
    mb.cylinder((0, 0, 0.2), (0, 0, 0.34), 0.03, 0.0, "gold", segments=6)
    for k in range(3):                                                           # A turban wound round it.
        mb.cylinder((0, 0, 0.035 + 0.035 * k), (0, 0, 0.07 + 0.035 * k), 0.14 - 0.006 * k, 0.136 - 0.006 * k, "cloth_orange" if k % 2 == 0 else "white", segments=8)
    for sx in (-1, 1):                                                           # Covers for the ears.
        mb.cylinder((sx * 0.085, 0.01, 0.17), (sx * 0.11, 0.01, 0.3), 0.045, 0.0, "bronze", segments=4)
    mb.sphere((0, -0.14, 0.09), 0.025, "gold", segments=5, rings=3)
    solid(mb, [(-0.1, 0.1, 0.04), (0.1, 0.1, 0.04), (0.08, 0.14, -0.14), (-0.08, 0.14, -0.14)], (0, 0.012, 0), "cloth_orange")
    save(mb, "arms_catfolk_helmet")


def dwarf_helmet():
    mb = kit.begin()
    mb.cylinder((0, 0, -0.04), (0, 0, 0.14), 0.135, 0.13, "steel_dark", segments=8)
    mb.cylinder((0, 0, 0.14), (0, 0, 0.22), 0.13, 0.06, "steel_dark", segments=8)
    mb.box((0, 0, 0.2), (0.03, 0.26, 0.06), "bronze")                            # A crest ridge.
    mb.box((0, -0.135, 0.02), (0.035, 0.016, 0.2), "bronze")
    mb.box((0, -0.136, 0.07), (0.18, 0.012, 0.03), "cave")
    mb.cylinder((0, 0, 0.1), (0, 0, 0.13), 0.14, 0.14, "bronze", segments=8)
    for sx in (-1, 1):
        mb.cylinder((sx * 0.13, 0, 0.13), (sx * 0.24, 0, 0.2), 0.035, 0.025, "bone", segments=6)
        mb.cylinder((sx * 0.24, 0, 0.2), (sx * 0.27, 0, 0.32), 0.025, 0.0, "bone", segments=6)
        mb.box((sx * 0.1, -0.1, -0.02), (0.06, 0.02, 0.1), "steel")
    for k in range(3):
        mb.box((-0.04 + 0.04 * k, -0.142, 0.16), (0.012, 0.01, 0.04), "glow_gold")
    save(mb, "arms_dwarf_helmet")


def elf_helmet():
    mb = kit.begin()
    mb.cylinder((0, 0, 0.07), (0, 0, 0.1), 0.127, 0.127, "gold", segments=10)       # A circlet, not a helm.
    dome(mb, "white", 0.118, 0.11, (1, 1.1, 0.9))
    mb.sphere((0, -0.13, 0.1), 0.025, "jade", segments=5, rings=3)
    flat(mb, [(-0.02, 0.1), (0.02, 0.1), (0, 0.2)], 0.01, "gold", -0.13)
    for sx in (-1, 1):                                                           # Wings swept back.
        for k in range(3):
            solid(mb, [(sx * 0.128, -0.02 + 0.02 * k, 0.08 + 0.02 * k), (sx * 0.128, 0.04 + 0.02 * k, 0.08 + 0.02 * k), (sx * 0.15, 0.2 + 0.05 * k, 0.2 + 0.07 * k)],
                  (sx * 0.008, 0, 0), "white" if k % 2 else "gold")
    save(mb, "arms_elf_helmet")


def dark_elf_helmet():
    mb = kit.begin()
    dome(mb, "obsidian")
    mb.box((0, -0.12, 0.02), (0.2, 0.02, 0.2), "obsidian_light")                  # A blank face plate.
    mb.box((0, -0.132, 0.07), (0.16, 0.008, 0.016), "glow_violet")
    flat(mb, [(-0.1, -0.08), (0.1, -0.08), (0, -0.2)], 0.02, "obsidian_light", -0.12)
    for k, (y, h) in enumerate(((-0.08, 0.2), (0.0, 0.26), (0.08, 0.18))):
        mb.cylinder((0, y, 0.2), (0, y + 0.03, 0.2 + h), 0.025, 0.0, "steel_dark", segments=4)
    for sx in (-1, 1):
        mb.cylinder((sx * 0.11, 0, 0.12), (sx * 0.2, 0.06, 0.26), 0.03, 0.0, "steel_dark", segments=4)
    save(mb, "arms_dark_elf_helmet")


def foxfolk_helmet():
    mb = kit.begin()
    dome(mb, "lacquer")
    mb.cylinder((0, 0, 0.21), (0, 0, 0.24), 0.03, 0.03, "gold", segments=6)
    for k in range(3):                                                           # The neck guard, in three flaring plates.
        r = 0.14 + 0.03 * k
        for i in range(5):
            a0, a1 = math.radians(20 + 28 * i), math.radians(20 + 28 * (i + 1))
            solid(mb, [(math.cos(a0) * r, math.sin(a0) * r, 0.06 - 0.045 * k), (math.cos(a1) * r, math.sin(a1) * r, 0.06 - 0.045 * k),
                       (math.cos(a1) * (r + 0.03), math.sin(a1) * (r + 0.03), 0.02 - 0.045 * k), (math.cos(a0) * (r + 0.03), math.sin(a0) * (r + 0.03), 0.02 - 0.045 * k)],
                  (0, 0, 0.012), "lacquer" if k % 2 == 0 else "lacquer_dark")
    mb.cylinder((0, 0, 0.055), (0, 0, 0.08), 0.132, 0.132, "lacquer_dark", segments=8)
    for sx in (-1, 1):                                                           # A crescent crest and room for the ears.
        flat(mb, [(sx * 0.01, 0.12), (sx * 0.12, 0.3), (sx * 0.16, 0.36), (sx * 0.1, 0.24), (sx * 0.01, 0.16)], 0.01, "gold", -0.125)
        mb.cylinder((sx * 0.08, 0.02, 0.18), (sx * 0.1, 0.02, 0.3), 0.04, 0.0, "lacquer", segments=4)
    save(mb, "arms_foxfolk_helmet")


def frogfolk_helmet():
    mb = kit.begin()
    mb.sphere((0, 0, 0.1), 0.14, "shell", segments=8, rings=5, scale=(1.15, 1.2, 0.8))
    for k in range(5):
        a = TAU * k / 5
        mb.sphere((math.cos(a) * 0.08, math.sin(a) * 0.09, 0.19), 0.04, "shell_dark", segments=5, rings=3, scale=(1, 1, 0.4))
    mb.sphere((0, 0, 0.215), 0.045, "shell_dark", segments=5, rings=3, scale=(1, 1, 0.5))
    for sx in (-1, 1):                                                           # Holes for the eyes, which sit on top.
        mb.sphere((sx * 0.08, -0.09, 0.17), 0.035, "cave", segments=5, rings=3)
        beam(mb, (sx * 0.13, 0, 0.06), (sx * 0.08, -0.04, -0.08), 0.01, "reed")
    for k in range(3):
        mb.cylinder((0, 0.1 + 0.02 * k, 0.16), (0, 0.2 + 0.04 * k, 0.32 - 0.04 * k), 0.012, 0.004, "reed", segments=4)
    save(mb, "arms_frogfolk_helmet")


def lizardfolk_helmet():
    mb = kit.begin()
    dome(mb, "bone", 0.13)
    mb.box((0, -0.15, 0.04), (0.14, 0.14, 0.07), "bone")                          # The snout of the beast it was.
    mb.box((0, -0.16, -0.01), (0.12, 0.1, 0.02), "bone_dark")
    for k in range(4):
        for sx in (-1, 1):
            mb.cylinder((sx * 0.055, -0.2 + 0.035 * k, 0.005), (sx * 0.055, -0.2 + 0.035 * k, -0.04), 0.012, 0.0, "white", segments=4)
    for sx in (-1, 1):
        mb.sphere((sx * 0.07, -0.1, 0.12), 0.03, "cave", segments=5, rings=3)
        mb.sphere((sx * 0.07, -0.105, 0.12), 0.014, "jade", segments=4, rings=3)
    for k in range(7):                                                           # A fan of feathers behind.
        a = math.radians(-60 + 20 * k)
        solid(mb, [(-0.02 + math.sin(a) * 0.05, 0.1, 0.16), (0.02 + math.sin(a) * 0.05, 0.1, 0.16), (math.sin(a) * 0.3, 0.2, 0.16 + math.cos(a) * 0.32)], (0, 0.008, 0),
              ("feather_red", "feather_green", "feather_blue")[k % 3])
    mb.cylinder((0, 0, 0.055), (0, 0, 0.08), 0.134, 0.134, "gold", segments=8)
    save(mb, "arms_lizardfolk_helmet")


def orc_helmet():
    mb = kit.begin()
    dome(mb, "iron", 0.135)
    mb.cylinder((0, 0, 0.21), (0, 0.02, 0.38), 0.04, 0.0, "rust", segments=5)
    mb.box((0, -0.135, 0.02), (0.04, 0.02, 0.18), "rust")
    for sx in (-1, 1):
        mb.box((sx * 0.1, -0.09, -0.03), (0.07, 0.03, 0.12), "iron")              # Jaw guards with tusks.
        mb.cylinder((sx * 0.1, -0.11, -0.08), (sx * 0.13, -0.2, 0.06), 0.022, 0.0, "bone", segments=5)
        mb.cylinder((sx * 0.13, 0, 0.14), (sx * 0.26, 0.02, 0.1), 0.04, 0.03, "bone_dark", segments=5)
        mb.cylinder((sx * 0.26, 0.02, 0.1), (sx * 0.3, 0.0, 0.26), 0.03, 0.0, "bone", segments=5)
    ring(mb, 0.07, 0.137, 8, (0.02, 0.03, 0.03), "rust", 1.1)
    solid(mb, [(-0.1, 0.11, 0.04), (0.1, 0.11, 0.04), (0.12, 0.16, -0.12), (-0.12, 0.16, -0.12)], (0, 0.014, 0), "hide")
    save(mb, "arms_orc_helmet")


MODELS = {
    "arms_human_sword": human_sword, "arms_catfolk_khopesh": catfolk_khopesh, "arms_dwarf_axe": dwarf_axe, "arms_elf_blade": elf_blade,
    "arms_dark_elf_blade": dark_elf_blade, "arms_foxfolk_katana": foxfolk_katana, "arms_frogfolk_harpoon": frogfolk_harpoon,
    "arms_lizardfolk_macuahuitl": lizardfolk_macuahuitl, "arms_orc_cleaver": orc_cleaver,
    "arms_human_shield": human_shield, "arms_catfolk_shield": catfolk_shield, "arms_dwarf_shield": dwarf_shield, "arms_elf_shield": elf_shield,
    "arms_dark_elf_shield": dark_elf_shield, "arms_foxfolk_shield": foxfolk_shield, "arms_frogfolk_shield": frogfolk_shield,
    "arms_lizardfolk_shield": lizardfolk_shield, "arms_orc_shield": orc_shield,
    "arms_human_helmet": human_helmet, "arms_catfolk_helmet": catfolk_helmet, "arms_dwarf_helmet": dwarf_helmet, "arms_elf_helmet": elf_helmet,
    "arms_dark_elf_helmet": dark_elf_helmet, "arms_foxfolk_helmet": foxfolk_helmet, "arms_frogfolk_helmet": frogfolk_helmet,
    "arms_lizardfolk_helmet": lizardfolk_helmet, "arms_orc_helmet": orc_helmet,
}

kit.run(MODELS, FAMILY)
