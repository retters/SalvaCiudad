"""Pineapple: a yellow-orange body covered in diamond scales and a green
crown of spiky folded leaves.

The body is not remeshed: it is a staggered lattice of rings whose every
diamond is raised into a low pyramid, the regular pattern of a pineapple's
scales that a remeshed surface cannot follow. Only the green collar under
the crown goes through the usual remesh."""

import math

from mathutils import Vector

import common
import studies

BODY_Z = (0.0, 0.232)   # Bottom and top of the scaled body.
BODY_R = 0.09           # Widest radius.
BODY_MID = 0.108        # Height of the widest ring.
COLUMNS = 10            # Scales around the body.
ROWS = 9                # Rings of the lattice (scales are centered on rows 1..ROWS-2).
BUMP = 0.011            # How far a scale's center stands out.
COLLAR = ((0.0, 0.0, 0.238), (0.05, 0.05, 0.024))
# Crown tiers: (count, base radius, base height, leaf length, tilt from vertical in degrees).
CROWN = [(8, 0.044, 0.238, 0.06, 74), (7, 0.036, 0.245, 0.085, 56), (6, 0.024, 0.252, 0.095, 34), (4, 0.01, 0.258, 0.1, 12)]


def radius_at(z):
    t = (z - BODY_MID) / ((BODY_Z[1] - BODY_MID) if z > BODY_MID else (BODY_MID - BODY_Z[0]))
    return BODY_R * math.sqrt(max(0.0, 1.0 - (t * 0.93) ** 2)) * (0.97 if z > BODY_MID else 1.0)


def ring_z(row):
    return BODY_Z[0] + 0.006 + (BODY_Z[1] - 0.006 - BODY_Z[0]) * row / (ROWS - 1)


class Pineapple(studies.Spec):
    name = "pineapple"
    colors = {
        "pine": common.rgb(0xF6B81E),
        "pine_light": common.rgb(0xFFD24A),
        "pine_shade": common.rgb(0xE08E14),
        "pine_base": common.rgb(0xC87412),
        "leaf": common.rgb(0x46B03A),
        "leaf_light": common.rgb(0x62C84A),
        "leaf_shade": common.rgb(0x2F8C2C),
    }
    ellipsoids = [COLLAR]
    capsules = []
    budget = 70
    max_tris = 1000
    tone_material = "leaf"
    tones = 0.3

    def paint(self, c, n):
        return "leaf"

    def details(self, mb):
        self.body(mb)
        self.crown(mb)

    def body(self, mb):
        bm = mb.bm
        step = math.tau / COLUMNS
        rings = []
        for row in range(ROWS):
            z = ring_z(row)
            r = radius_at(z)
            off = 0.5 * (row % 2)
            rings.append([bm.verts.new((r * math.cos((i + off) * step), r * math.sin((i + off) * step), z))
                          for i in range(COLUMNS)])
        mats = {k: mb._material_index(k) for k in ("pine", "pine_light", "pine_shade", "pine_base")}

        def face(verts, mat):
            f = bm.faces.new(verts)
            f.material_index = mats[mat]
            f.smooth = False

        # A scale centered on row r between its vertices i and i+1: bottom
        # and top from rows r-1 and r+1, raised in the middle.
        for row in range(1, ROWS - 1):
            shift = row % 2  # Rows above and below are offset by half a step.
            for i in range(COLUMNS):
                left, right = rings[row][i], rings[row][(i + 1) % COLUMNS]
                bottom = rings[row - 1][(i + shift) % COLUMNS]
                top = rings[row + 1][(i + shift) % COLUMNS]
                mid = (left.co + right.co + bottom.co + top.co) / 4
                out = Vector((mid.x, mid.y, 0.0)).normalized()
                out = (out + Vector((0, 0, (mid.z - BODY_MID) / 0.25))).normalized()
                apex = bm.verts.new(mid + out * BUMP)
                low = "pine_base" if row == 1 else "pine_shade"
                face((bottom, right, apex), low)
                face((right, top, apex), "pine")
                face((top, left, apex), "pine_light" if (i + row) % 3 == 0 else "pine")
                face((left, bottom, apex), low)
        # Half scales along the first and last rings, and the flat ends.
        for row, other, mat in ((0, 1, "pine_base"), (ROWS - 1, ROWS - 2, "pine_shade")):
            for i in range(COLUMNS):
                face((rings[row][i], rings[row][(i + 1) % COLUMNS], rings[other][i]), mat)
        for row, z in ((0, BODY_Z[0]), (ROWS - 1, ring_z(ROWS - 1) + 0.004)):
            c = bm.verts.new((0, 0, z))
            for i in range(COLUMNS):
                face((rings[row][i], rings[row][(i + 1) % COLUMNS], c), "pine_base" if row == 0 else "pine")

    def crown(self, mb):
        for tier, (count, base_r, base_z, length, tilt) in enumerate(CROWN):
            for i in range(count):
                a = (i + 0.5 * tier) * math.tau / count + tier * 0.4
                d = Vector((math.cos(a), math.sin(a), 0.0))
                t = math.radians(tilt + 6 * ((i * 7 + tier) % 3 - 1))
                axis = d * math.sin(t) + Vector((0, 0, math.cos(t)))
                base = Vector((0, 0, base_z)) + d * base_r
                self.leaf(mb, base, axis, d, length * (0.9 + 0.1 * ((i + tier) % 3)), 0.038 - tier * 0.005,
                          ("leaf", "leaf_light", "leaf_shade")[(i + tier) % 3])

    def leaf(self, mb, base, axis, out, length, width, mat):
        """A spiky leaf folded along its middle: two thin triangles sharing
        the midrib, the fold toward the outside."""
        side = axis.cross(out).normalized()
        fold = axis.cross(side).normalized()
        if fold.dot(out) < 0:
            fold = -fold
        tip = base + axis * length
        rib = base + fold * (width * 0.35)
        for s in (-1, 1):
            studies.flap(mb, rib, base + side * (s * width * 0.5), tip, 0.003, mat)


SPECS = [Pineapple()]
