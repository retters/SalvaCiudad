"""Shared pieces for the weapons 28 to 42 (staffs, clubs, daggers, bow,
spear, great sword): faceted solids built directly, for the hard thin
shapes that the remesh would round off.

    loft()    a tube of rings along a path (shafts, crystals, spikes, vines)
    shell()   a flat blade from a grid of outline points with a thickness
    ico()     a faceted ball (orbs, gems)
    ring()    a faceted torus (ring pommels)
    ribbon()  a flat band along a path (wraps around a staff)

Materials: a piece with `tones` uses <material>, <material>_light and
<material>_shade, but only the ones the spec defines in its colors (see
begin() and shades()), so each weapon decides which materials get facet
tones and stays within its material limit.
"""

import math
import random

import bmesh
from mathutils import Vector

import common

# Where the light comes from in the reference picture: facets that look
# this way get the light tone, the ones that look away the shade tone.
LIGHT = Vector((-0.5, -0.62, 0.6)).normalized()


def shades(name, hex_color, light=None, shade=None):
    """Colors of a material and its facet tones, from sRGB values: {name,
    name_light, name_shade}. A tone that is not given does not exist; its
    facets keep the plain material."""
    colors = {name: common.rgb(hex_color)}
    if light is not None:
        colors[name + "_light"] = common.rgb(light)
    if shade is not None:
        colors[name + "_shade"] = common.rgb(shade)
    return colors


def begin(mb, spec):
    """Call first in details(): from here on the pieces only use the tones
    that the spec has colors for."""
    mb.palette = set(spec.colors)


def toned(mb, mat, suffix):
    """mat + suffix if the spec has that tone, else mat."""
    palette = getattr(mb, "palette", None)
    return mat + suffix if palette is None or mat + suffix in palette else mat


def retone(mb, mat, share, seed=7):
    """Gives a share of the faces painted `mat` its light and shade tones
    at random (half each): the facet tones of the welded surface."""
    rnd = random.Random(seed)
    main = mb._material_index(mat)
    for f in mb.bm.faces:
        if f.material_index != main:
            continue
        r = rnd.random()
        if r < share * 0.5:
            f.material_index = mb._material_index(toned(mb, mat, "_light"))
        elif r < share:
            f.material_index = mb._material_index(toned(mb, mat, "_shade"))


def face(mb, verts, mat, tones=None, outward=None, rnd=None):
    """A flat face of the builder; skips repeated vertices and faces that
    collapse. tones: None (plain), "light" (tone from where the facet
    looks, needs `outward`, a point-out direction) or a share 0..1 of
    random light and shade facets (needs rnd)."""
    uniq = []
    for v in verts:
        if v not in uniq:
            uniq.append(v)
    if len(uniq) < 3:
        return None
    try:
        f = mb.bm.faces.new(uniq)
    except ValueError:  # The face already exists.
        return None
    name = mat
    if tones == "light":
        f.normal_update()
        n = f.normal.copy()
        if outward is not None and n.dot(outward) < 0.0:
            n = -n
        d = n.dot(LIGHT)
        if d > 0.45:
            name = toned(mb, mat, "_light")
        elif d < -0.05:
            name = toned(mb, mat, "_shade")
    elif tones:
        r = rnd.random()
        if r < tones * 0.5:
            name = toned(mb, mat, "_light")
        elif r < tones:
            name = toned(mb, mat, "_shade")
    f.material_index = mb._material_index(name)
    f.smooth = False
    return f


def loft(mb, pts, radii, sides, mat, phase=0.0, twist=0.0, tones=None, seed=1, ref=(0, -1, 0), cap=True):
    """A tube of `sides`-sided rings through the points. A radius is a
    number or (across, along ref) for a flattened ring; a radius 0 makes
    that ring a single point (a cone tip). Two points at the same place
    with different radii make a step (a collar's lip). mat is one name or
    one name per segment. The first vertex of a ring looks toward `ref`
    turned by phase (+ twist per ring)."""
    pts = [Vector(p) for p in pts]
    n = len(pts)
    rnd = random.Random(seed)
    segs = [pts[i + 1] - pts[i] for i in range(n - 1)]

    def direction(i, step):
        while 0 <= i < n - 1:
            if segs[i].length > 1e-7:
                return segs[i].normalized()
            i += step
        return Vector()

    u = Vector(ref).normalized()
    rings = []
    tangents = []
    for i in range(n):
        t = direction(i - 1, -1) + direction(i, 1)
        if t.length < 1e-7:
            t = direction(i, 1) if direction(i, 1).length > 0 else direction(i - 1, -1)
        t = t.normalized()
        tangents.append(t)
        u = u - t * u.dot(t)
        if u.length < 1e-6:
            u = t.orthogonal()
        u = u.normalized()
        v = t.cross(u)
        r = radii[i]
        rx, ry = r if isinstance(r, (tuple, list)) else (r, r)
        if rx == 0 and ry == 0:
            rings.append([mb.bm.verts.new(pts[i])])
            continue
        ring = []
        for k in range(sides):
            a = phase + twist * i + k * math.tau / sides
            ring.append(mb.bm.verts.new(pts[i] + u * (math.cos(a) * ry) + v * (math.sin(a) * rx)))
        rings.append(ring)
    for i in range(n - 1):
        r0, r1 = rings[i], rings[i + 1]
        if len(r0) == 1 and len(r1) == 1:
            continue
        name = mat[i] if isinstance(mat, (list, tuple)) else mat
        axis = (pts[i] + pts[i + 1]) * 0.5
        for k in range(sides):
            quad = [r0[k % len(r0)], r0[(k + 1) % len(r0)], r1[(k + 1) % len(r1)], r1[k % len(r1)]]
            center = sum((q.co for q in quad), Vector()) / 4
            out = center - axis
            if segs[i].length < 1e-7:  # A step: it looks back along the path if the tube widens there.
                widens = (r1[0].co - pts[i]).length > (r0[0].co - pts[i]).length
                out = -tangents[i] if widens else tangents[i]
            face(mb, quad, name, tones, out, rnd)
    if cap:
        if len(rings[0]) > 1:
            face(mb, list(reversed(rings[0])), mat[0] if isinstance(mat, (list, tuple)) else mat, tones,
                 -tangents[0], rnd)
        if len(rings[-1]) > 1:
            face(mb, rings[-1], mat[-1] if isinstance(mat, (list, tuple)) else mat, tones, tangents[-1], rnd)
    return [v for ring in rings for v in ring]


def spike(mb, base, tip, radius, mat, sides=4, tones="light", phase=0.0, ref=(0, -1, 0)):
    """A pointed pyramid from base to tip."""
    b, t = Vector(base), Vector(tip)
    if abs((t - b).normalized().dot(Vector(ref).normalized())) > 0.9:
        ref = (1, 0, 0) if abs((t - b).normalized().x) < 0.9 else (0, 0, 1)
    return loft(mb, [b, t], [radius, 0.0], sides, mat, phase=phase, tones=tones, ref=ref)


def shell(mb, grid, thick, mats, at=(0, 0, 0)):
    """A flat piece (a blade) in the XZ plane. grid[i][j] = (x, z): row i
    along the blade, column j across it. thick[j] (or thick[i][j]) is half
    the thickness at that column: 0 makes a sharp edge. mats[j] paints the
    strip between columns j and j + 1 (a name, or a list with one name per
    row step). A row whose points all coincide is a sharp tip."""
    rows, cols = len(grid), len(grid[0])
    cache = {}
    at = Vector(at)

    def vert(x, y, z):
        key = (round(x, 5), round(y, 5), round(z, 5))
        if key not in cache:
            cache[key] = mb.bm.verts.new(Vector((x, y, z)) + at)
        return cache[key]

    def half(i, j):
        if all((Vector(p) - Vector(grid[i][0])).length < 1e-7 for p in grid[i]):
            return 0.0
        return thick[i][j] if isinstance(thick[0], (tuple, list)) else thick[j]

    front = [[vert(grid[i][j][0], -half(i, j), grid[i][j][1]) for j in range(cols)] for i in range(rows)]
    back = [[vert(grid[i][j][0], half(i, j), grid[i][j][1]) for j in range(cols)] for i in range(rows)]

    def name(i, j):
        m = mats[j]
        return m[min(i, len(m) - 1)] if isinstance(m, (tuple, list)) else m

    for i in range(rows - 1):
        for j in range(cols - 1):
            face(mb, [front[i][j], front[i][j + 1], front[i + 1][j + 1], front[i + 1][j]], name(i, j))
            face(mb, [back[i][j], back[i + 1][j], back[i + 1][j + 1], back[i][j + 1]], name(i, j))
        for j in (0, cols - 1):
            face(mb, [front[i][j], front[i + 1][j], back[i + 1][j], back[i][j]], name(i, min(j, cols - 2)))
    for j in range(cols - 1):
        for i in (0, rows - 1):
            face(mb, [front[i][j], front[i][j + 1], back[i][j + 1], back[i][j]], name(min(i, rows - 2), j))
    return list(cache.values())


def ico(mb, center, radius, mat, subdiv=1, scale=(1, 1, 1), tones="light", seed=1, jitter=0.0, tilt=0.0):
    """A faceted ball from an icosphere (20 triangles, 80 with subdiv 2)."""
    rnd = random.Random(seed)
    center = Vector(center)
    tmp = bmesh.new()
    bmesh.ops.create_icosphere(tmp, subdivisions=subdiv, radius=1.0)
    ct, st = math.cos(tilt), math.sin(tilt)
    mapping = {}
    for v in tmp.verts:
        p = v.co * (1.0 + rnd.uniform(-jitter, jitter))
        p = Vector((p.x * ct - p.z * st, p.y, p.x * st + p.z * ct))
        mapping[v] = mb.bm.verts.new(center + Vector((p.x * radius * scale[0], p.y * radius * scale[1],
                                                      p.z * radius * scale[2])))
    for f in tmp.faces:
        verts = [mapping[v] for v in f.verts]
        out = sum((v.co for v in verts), Vector()) / len(verts) - center
        face(mb, verts, mat, tones, out, rnd)
    tmp.free()
    return list(mapping.values())


def ring(mb, center, big, small, mat, count=6, sides=4, depth=None, tones="light", phase=0.0):
    """A faceted torus standing in the XZ plane (its hole looks along Y):
    `count` segments around, a `sides`-sided section of radius `small`
    (`depth` along Y if it differs)."""
    center = Vector(center)
    depth = small if depth is None else depth
    loops = []
    for i in range(count):
        a = phase + i * math.tau / count
        d = Vector((math.cos(a), 0.0, math.sin(a)))
        loop = []
        for k in range(sides):
            b = k * math.tau / sides
            loop.append(mb.bm.verts.new(center + d * (big + math.cos(b) * small) + Vector((0, math.sin(b) * depth, 0))))
        loops.append((center + d * big, loop))
    for i in range(count):
        (c0, l0), (c1, l1) = loops[i], loops[(i + 1) % count]
        for k in range(sides):
            quad = [l0[k], l0[(k + 1) % sides], l1[(k + 1) % sides], l1[k]]
            out = sum((q.co for q in quad), Vector()) / 4 - (c0 + c1) * 0.5
            face(mb, quad, mat, tones, out)
    return [v for _, loop in loops for v in loop]


def ribbon(mb, pts, normals, width, thick, mat, tones=None, seed=1, sink=0.004):
    """A flat band through the points, lying on a surface whose outward
    directions at the points are `normals` (a wrap around a staff)."""
    rnd = random.Random(seed)
    pts = [Vector(p) for p in pts]
    loops = []
    for i, (p, n) in enumerate(zip(pts, normals)):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        n = Vector(n).normalized()
        w = t.cross(n).normalized() * (width * 0.5)
        loops.append([mb.bm.verts.new(p + w - n * sink), mb.bm.verts.new(p + w + n * thick),
                      mb.bm.verts.new(p - w + n * thick), mb.bm.verts.new(p - w - n * sink)])
    for i in range(len(loops) - 1):
        l0, l1 = loops[i], loops[i + 1]
        mid = (pts[i] + pts[i + 1]) * 0.5
        for k in range(4):
            quad = [l0[k], l0[(k + 1) % 4], l1[(k + 1) % 4], l1[k]]
            face(mb, quad, mat, tones, sum((q.co for q in quad), Vector()) / 4 - mid, rnd)
    face(mb, list(reversed(loops[0])), mat)
    face(mb, loops[-1], mat)
    return [v for loop in loops for v in loop]


def chain(nodes):
    """Capsules through (point, radius) nodes: a gnarled staff or a prong."""
    return [(a, b, ra, rb) for (a, ra), (b, rb) in zip(nodes, nodes[1:])]


def along(nodes):
    """axis(z) -> (center, radius) of a staff given as (point, radius)
    nodes ordered from the bottom up."""
    def axis(z):
        for (a, ra), (b, rb) in zip(nodes, nodes[1:]):
            if z <= b[2] or (b, rb) == nodes[-1]:
                k = max(0.0, min(1.0, (z - a[2]) / (b[2] - a[2])))
                return Vector(a).lerp(Vector(b), k), ra + (rb - ra) * k
        return Vector(nodes[-1][0]), nodes[-1][1]
    return axis


def helix(axis, z0, z1, turns, steps, phase=0.0, gap=0.0, clear=False):
    """(points, outward directions) of a helix around a staff; axis(z)
    gives the staff's center and radius (see along()). With clear, the
    points are far enough out for the straight pieces between them not to
    cut into the staff (a vine); without, they sit on its surface (a
    ribbon, which has its own thickness)."""
    per_turn = max(3.0, steps / max(abs(turns), 1e-6))
    grow = 1.0 / math.cos(math.pi / per_turn) if clear else 1.0
    pts, normals = [], []
    for i in range(steps + 1):
        t = i / steps
        z = z0 + (z1 - z0) * t
        a = phase + turns * math.tau * t
        c, r = axis(z)
        d = Vector((math.cos(a), math.sin(a), 0.0))
        pts.append(Vector((c.x, c.y, z)) + d * (r * grow + gap))
        normals.append(d)
    return pts, normals


def stack(mb, sections, sides, at=(0, 0), phase=0.0, twist=0.0, tones=None, seed=1):
    """An upright shaft made of sections (z0, z1, r0, r1, material), bottom
    first, as one closed solid: a section wider than the one before makes a
    lip (collars, wraps, pommels). A radius 0 at either end makes a point."""
    pts, radii, mats = [], [], []
    for k, (z0, z1, r0, r1, mat) in enumerate(sections):
        if k:
            mats.append(mat if r0 >= radii[-1] else sections[k - 1][4])
        pts += [(at[0], at[1], z0), (at[0], at[1], z1)]
        radii += [r0, r1]
        mats.append(mat)
    return loft(mb, pts, radii, sides, mats, phase=phase, twist=twist, tones=tones, seed=seed)


def wrap(mb, a, b, radius, bands, mat, sides=6, bulge=0.004, twist=0.35, tones=0.5, seed=1, phase=0.0):
    """A cord or ribbon wound around a shaft from a to b: a sleeve of
    `bands` turns, each one bulging and turned a little against the next
    so the facets run diagonally. radius is a number, or (at a, at b)."""
    a, b = Vector(a), Vector(b)
    ra, rb = radius if isinstance(radius, (tuple, list)) else (radius, radius)
    pts, radii = [], []
    for i in range(bands * 2 + 1):
        k = i / (bands * 2)
        pts.append(a.lerp(b, k))
        radii.append(ra + (rb - ra) * k + (bulge if i % 2 else 0.0))
    return loft(mb, pts, radii, sides, mat, phase=phase, twist=twist, tones=tones, seed=seed)


def leaf(mb, base, tip, width, mat, thick=0.006, fold=0.25, across=(0, 0, 1)):
    """A small pointed leaf from base to tip: two facets folded along the
    midrib (one light, one plain) over a shallow keel. The leaf is wide at
    right angles to `across`: by default it lies flat."""
    base, tip = Vector(base), Vector(tip)
    d = tip - base
    side = d.cross(Vector(across))
    if side.length < 1e-6:
        side = Vector((1, 0, 0))
    side = side.normalized() * (width * 0.5)
    up = side.cross(d).normalized()
    mid = base + d * 0.42
    b, t = mb.bm.verts.new(base), mb.bm.verts.new(tip)
    left = mb.bm.verts.new(mid + side + up * (width * fold))
    right = mb.bm.verts.new(mid - side + up * (width * fold))
    keel = mb.bm.verts.new(mid - up * thick)
    face(mb, [b, t, left], toned(mb, mat, "_light"))
    face(mb, [b, right, t], mat)
    for x, y in ((b, left), (left, t), (t, right), (right, b)):
        face(mb, [x, y, keel], toned(mb, mat, "_shade"))
    return [b, t, left, right, keel]
