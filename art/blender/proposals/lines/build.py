"""Line kits proposals: rails, canals and streets cut in the same six pieces
as the walls (pillar, end, straight, corner, tee, cross) on a 2 m module,
so the same neighbour rule lays them out. See ../LEEME.md.

At rest: the end reaches west (-X); the straight joins east and west; the
corner, east and north (+Y); the tee, all but south; the cross, all four.

    blender --background --factory-startup --python art/blender/proposals/lines/build.py -- [ids]
"""

import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import _kit as kit  # noqa: E402
import _shapes  # noqa: E402
import common  # noqa: E402
from _shapes import TAU, beam, mark, moved  # noqa: E402

FAMILY = "lines"
C = common.rgb
COLORS = {
    **_shapes.COLORS,
    "gravel": C(0x8A8478), "gravel_dark": C(0x6E6A60), "rust": C(0x7A4A3A), "bronze": C(0x9A7A3A), "glow_gold": C(0xFFD66A), "dwarf_stone": C(0x5E5A5E),
    "dwarf_dark": C(0x444046), "water": C(0x4A8FC0), "water_light": C(0x7AB8E0), "soil": C(0x6A4A30), "soil_dark": C(0x4A3422), "grass": C(0x6A9440),
    "grass_light": C(0x86B050), "cobble": C(0x8A8680), "cobble_dark": C(0x6E6A64), "cobble_light": C(0xA6A29A), "dirt": C(0x9A7A52), "dirt_dark": C(0x7A5E3E),
    "mud": C(0x5A4632),
}
E, N, W, S = 0, 1, 2, 3
PIECES = {"pillar": (), "end": (W,), "straight": (E, W), "corner": (E, N), "tee": (E, N, W), "cross": (E, N, W, S)}


def turned(mb, direction, draw):
    """Draws along +X and turns it to face `direction`."""
    start = mark(mb)
    draw()
    moved(mb, start, (0, 0, 0), 90.0 * direction)


def rails(kind):
    """A tramway for mine carts: where lines meet there is a turnplate."""
    sleeper, rail, bed = {"wood": ("pole_dark", "plank_light", None), "iron": ("pole_dark", "iron", "gravel"), "dwarf": ("dwarf_dark", "bronze", "dwarf_stone")}[kind]

    def build(mb, arms, piece):
        plate = piece in ("pillar", "corner", "tee", "cross")
        start = 0.55 if plate else 0.0

        def arm():
            if bed:
                mb.box(((start + 1.0) / 2, 0, 0.03), (1.0 - start, 1.3, 0.06), bed)
            for x in (0.25, 0.75):
                if x > start:
                    mb.box((x, 0, 0.09 if bed else 0.04), (0.16, 1.05, 0.08), sleeper)
            for sy in (-0.3, 0.3):
                mb.box(((start + 1.0) / 2, sy, 0.16 if bed else 0.11), (1.0 - start, 0.07, 0.07), rail)
                if kind == "dwarf":
                    mb.box((0.8, sy * 1.5, 0.14), (0.08, 0.05, 0.03), "glow_gold")
        for d in arms:
            turned(mb, d, arm)
        if plate:
            z = 0.06 if bed else 0.0
            mb.cylinder((0, 0, 0), (0, 0, z + 0.1), 0.62, 0.62, bed or "plank_dark", segments=12)
            mb.cylinder((0, 0, z + 0.1), (0, 0, z + 0.13), 0.55, 0.55, "iron" if kind != "wood" else "plank", segments=12)
            mb.cylinder((0, 0, z + 0.13), (0, 0, z + 0.16), 0.08, 0.08, rail, segments=6)
            for sy in (-0.3, 0.3):                                               # The plate carries its own length of rail.
                mb.box((0, sy, z + 0.16), (0.9, 0.07, 0.06), rail)
        if piece == "end":                                                       # A buffer stop.
            for sy in (-0.3, 0.3):
                mb.box((0.12, sy, 0.4), (0.12, 0.12, 0.7), sleeper)
                beam(mb, (0.12, sy, 0.6), (0.6, sy, 0.1), 0.045, sleeper)
            mb.box((0.06, 0, 0.6), (0.14, 0.9, 0.16), "plank" if kind == "wood" else rail)
    return build


def canal(kind):
    """A channel 1 m wide between two banks."""
    wall, cap, floor, high = {"stone": ("stone", "stone_light", "stone_dark", 0.34), "dirt": ("soil", "grass", "soil_dark", 0.22)}[kind]
    thick = 0.2 if kind == "stone" else 0.34

    def build(mb, arms, piece):
        reach = 0.5 + thick
        mb.box((0, 0, 0.04), (2 * reach, 2 * reach, 0.08), floor)
        mb.box((0, 0, 0.14), (1.0, 1.0, 0.12), "water")
        for sx in (-1, 1):
            for sy in (-1, 1):
                mb.box((sx * (0.5 + thick / 2), sy * (0.5 + thick / 2), high / 2), (thick, thick, high), wall)
                mb.box((sx * (0.5 + thick / 2), sy * (0.5 + thick / 2), high + 0.02), (thick + 0.04, thick + 0.04, 0.05), cap)

        def side():                                                              # A closed side: the bank runs across.
            mb.box((0.5 + thick / 2, 0, high / 2), (thick, 1.0, high), wall)
            mb.box((0.5 + thick / 2, 0, high + 0.02), (thick + 0.04, 1.0, 0.05), cap)

        def arm():
            mb.box(((reach + 1.0) / 2, 0, 0.04), (1.0 - reach, 2 * reach, 0.08), floor)
            mb.box((0.75, 0, 0.14), (0.5, 1.0, 0.12), "water")
            for sy in (-1, 1):
                mb.box(((reach + 1.0) / 2, sy * (0.5 + thick / 2), high / 2), (1.0 - reach, thick, high), wall)
                mb.box(((reach + 1.0) / 2, sy * (0.5 + thick / 2), high + 0.02), (1.0 - reach, thick + 0.04, 0.05), cap)
        for d in (E, N, W, S):
            turned(mb, d, arm if d in arms else side)
        if piece == "pillar":                                                    # A basin on its own: something to drink from.
            mb.cylinder((0, 0, 0.2), (0, 0, 0.22), 0.3, 0.3, "water_light", segments=8)
    return build


def road(kind):
    half = {"cobble": 0.8, "plank": 0.65, "dirt": 0.75}[kind]

    def surface(mb, x0, x1, y0, y1, rnd, across):
        """The paving over a rectangle; `across` says which way the boards or ruts run."""
        if kind == "cobble":
            mb.box(((x0 + x1) / 2, (y0 + y1) / 2, 0.03), (x1 - x0, y1 - y0, 0.06), "cobble_dark")
            nx, ny = max(1, round((x1 - x0) / 0.26)), max(1, round((y1 - y0) / 0.26))
            for i in range(nx):
                for j in range(ny):
                    mb.box((x0 + (x1 - x0) * (i + 0.5) / nx, y0 + (y1 - y0) * (j + 0.5) / ny, 0.07 + rnd.uniform(0, 0.015)),
                           ((x1 - x0) / nx - 0.04, (y1 - y0) / ny - 0.04, 0.05), rnd.choice(("cobble", "cobble", "cobble_light")))
        elif kind == "plank":
            if across:
                n = max(1, round((x1 - x0) / 0.25))
                for i in range(n):
                    mb.box((x0 + (x1 - x0) * (i + 0.5) / n, (y0 + y1) / 2, 0.3), ((x1 - x0) / n - 0.02, y1 - y0, 0.05), "plank" if i % 2 else "plank_light")
            else:
                n = max(1, round((y1 - y0) / 0.25))
                for j in range(n):
                    mb.box(((x0 + x1) / 2, y0 + (y1 - y0) * (j + 0.5) / n, 0.3), (x1 - x0, (y1 - y0) / n - 0.02, 0.05), "plank" if j % 2 else "plank_light")
        else:
            mb.box(((x0 + x1) / 2, (y0 + y1) / 2, 0.02), (x1 - x0, y1 - y0, 0.04), "dirt")

    def build(mb, arms, piece):
        rnd = random.Random(len(piece) * 7 + len(kind))
        if kind == "plank":
            mb.box((0, 0, 0.02), (2 * half + 0.5, 2 * half + 0.5, 0.04), "mud")
            for sx in (-1, 1):
                for sy in (-1, 1):
                    mb.cylinder((sx * (half - 0.08), sy * (half - 0.08), 0), (sx * (half - 0.08), sy * (half - 0.08), 0.7 if piece != "cross" else 0.3), 0.06, 0.05, "pole_dark", segments=6)
            for sy in (-1, 1):
                mb.box((0, sy * (half - 0.15), 0.22), (2 * half, 0.1, 0.1), "pole")
        surface(mb, -half, half, -half, half, rnd, False)

        def arm():
            surface(mb, half, 1.0, -half, half, rnd, True)
            if kind == "plank":
                mb.box(((half + 1.0) / 2, 0, 0.02), (1.0 - half, 2 * half + 0.5, 0.04), "mud")
                for sy in (-1, 1):
                    mb.box(((half + 1.0) / 2, sy * (half - 0.15), 0.22), (1.0 - half, 0.1, 0.1), "pole")
            if kind == "dirt":                                                   # Cart ruts.
                for sy in (-0.35, 0.35):
                    mb.box((0.5, sy, 0.045), (1.0, 0.12, 0.012), "dirt_dark")

        def side():
            if kind == "cobble":                                                 # A kerb.
                mb.box((half + 0.06, 0, 0.08), (0.12, 2 * half + 0.24, 0.16), "stone_light")
            elif kind == "plank":                                                # A rope between the corner posts.
                beam(mb, (half - 0.08, -half + 0.08, 0.62), (half - 0.08, half - 0.08, 0.62), 0.014, "rope")
            else:                                                                # Grass creeping in.
                for k in range(5):
                    y = -half + 2 * half * (k + 0.5) / 5
                    mb.cylinder((half + rnd.uniform(-0.05, 0.1), y, 0), (half + rnd.uniform(0.0, 0.15), y + rnd.uniform(-0.05, 0.05), rnd.uniform(0.15, 0.3)), 0.09, 0.0,
                                "grass" if k % 2 else "grass_light", segments=4)
        for d in (E, N, W, S):
            turned(mb, d, arm if d in arms else side)
        if piece == "pillar" and kind == "cobble":                               # A small paved place with its lamp post base.
            mb.cylinder((0, 0, 0.1), (0, 0, 0.5), 0.14, 0.1, "stone_light", segments=6)
    return build


def sluice():
    """A straight length of stone canal with a gate that shuts it."""
    mb = kit.begin()
    canal("stone")(mb, PIECES["straight"], "straight")
    for sy in (-1, 1):
        mb.box((0, sy * 0.62, 0.9), (0.2, 0.2, 1.3), "pole")
    mb.box((0, 0, 1.6), (0.24, 1.6, 0.16), "pole_dark")
    w = {"gate": 1.0}
    mb.box((0, 0, 0.5), (0.08, 1.04, 0.75), "plank", w)
    for z in (0.3, 0.7):
        mb.box((0, 0, z), (0.1, 1.06, 0.06), "iron", w)
    mb.box((0, 0, 1.1), (0.06, 0.06, 0.9), "iron", w)
    wc = {"wheel": 1.0}
    for k in range(6):
        a = TAU * k / 6
        beam(mb, (0.16, 0, 1.6), (0.16, math.cos(a) * 0.3, 1.6 + math.sin(a) * 0.3), 0.02, "iron", wc)

    def move(opening):
        def pose(t):
            s = kit.smooth(t) if opening else 1 - kit.smooth(t)
            return {"wheel": [(kit.X, 360.0 * s)]}, {"gate": (0, 0, 0.5 * s)}
        return pose

    mech = kit.Mech([("gate", (0, 0, 0.9), (0, 0, 0.1), None), ("wheel", (0.16, 0, 1.6), (0.5, 0, 1.6), None)])
    mech.clip("open", 2.5, move(True), loops=False).clip("close", 2.5, move(False), loops=False)
    kit.save(mb, FAMILY, "canal_stone_sluice", COLORS, mech=mech)


KITS = {
    "rail_wood": rails("wood"), "rail_iron": rails("iron"), "rail_dwarf": rails("dwarf"),
    "canal_stone": canal("stone"), "canal_dirt": canal("dirt"),
    "street_cobble": road("cobble"), "street_plank": road("plank"), "street_dirt": road("dirt"),
}


def piece_builder(prefix, piece):
    def build():
        mb = kit.begin()
        KITS[prefix](mb, PIECES[piece], piece)
        kit.save(mb, FAMILY, "%s_%s" % (prefix, piece), COLORS)
    return build


MODELS = {"%s_%s" % (prefix, piece): piece_builder(prefix, piece) for prefix in KITS for piece in PIECES}
MODELS["canal_stone_sluice"] = sluice

kit.run(MODELS, FAMILY)
