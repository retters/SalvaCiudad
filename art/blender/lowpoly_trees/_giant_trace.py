"""Traces the giant-tree reference pictures into the data _giant.py builds from.

    python art/blender/lowpoly_trees/_giant_trace.py [debug folder] [tree names]

A development tool (system Python with PIL; Blender is not needed), run by
hand when the reference pictures change; it writes _giant_traced.py next to
itself. The models are built from _giant_traced.py alone.

"Arboles 7.png" (in art/reference/) shows the eight giants with leaves and "Arboles 8.png" the
same eight without. Only the giants whose crown is a spread of branches are
traced (baobab, cherry, mangrove, ginkgo); the others are defined by hand
in their own modules. For each traced tree, as _trace.py does for the
ordinary trees:

  * the bare picture gives the branch structure: the bark pixels above the
    foot of the crown are thinned to a one-pixel skeleton, the skeleton
    becomes a tree of polylines rooted at the trunk, and the distance to the
    background gives the thickness along every branch;
  * the picture with leaves gives the canopy: the foliage pixels are covered
    with ellipses (the clumps) and their outline is kept as a width
    profile, from which the generator derives the depth.

Everything is in meters, X to the right and Z up, from the foot of the
trunk. With a debug folder, also writes two overlay images per tree.

The thinning, the skeleton walk and the ellipse cover are those of
_trace.py, copied here so that this file does not change when that one
does; the thinning only looks at the pixels of the border, which is what
makes the huge trunks affordable.
"""

import heapq
import math
import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
# The user's reference pictures (phase 49: before, in the repository root).
REFERENCE = os.path.abspath(os.path.join(HERE, "..", "..", "reference"))
PICTURES = {"bloom": "Arboles 7.png", "bare": "Arboles 8.png"}
S = 2  # The pictures are traced enlarged S times.


def green(r, g, b):
    return g > r + 4 and g > b + 6


def pink(r, g, b):
    return r > g + 30 and b > g + 8


def yellow(r, g, b):
    return r > 170 and g - b > 85


# box: the tree's cell in each picture; foot: the foot of the trunk in the
# picture (x, y); top: the highest row of the tree; height: meters between
# the two. root_z: the skeleton starts at this height (below, the trunk and
# its roots are modeled by hand in the tree's module). blob: smallest and
# largest radius of a clump, and how many times wider than tall it may be.
TREES = {
    "giant_baobab": {
        "bare": {"box": (0, 0, 430, 478), "foot": (192, 463), "top": 38},
        "bloom": {"box": (0, 0, 434, 490), "foot": (188, 475), "top": 45},
        "height": 26.0, "root_z": 6.0, "foliage": green, "blob": (0.6, 2.4, 3.0),
    },
    "giant_cherry": {
        "bare": {"box": (705, 0, 1142, 478), "foot": (917, 463), "top": 57},
        "bloom": {"box": (700, 0, 1112, 490), "foot": (907, 473), "top": 64},
        "height": 25.0, "root_z": 5.0, "foliage": pink, "blob": (0.8, 2.3, 1.25),
    },
    "giant_mangrove": {
        "bare": {"box": (1142, 0, 1536, 478), "foot": (1334, 466), "top": 34},
        "bloom": {"box": (1112, 0, 1536, 490), "foot": (1332, 478), "top": 41},
        "height": 25.0, "root_z": 13.0, "foliage": green, "blob": (0.9, 2.5, 1.5),
    },
    "giant_ginkgo": {
        "bare": {"box": (725, 522, 1125, 955), "foot": (940, 944), "top": 524},
        "bloom": {"box": (730, 522, 1118, 960), "foot": (945, 945), "top": 530},
        "height": 30.0, "root_z": 2.0, "foliage": yellow, "blob": (0.7, 2.6, 2.0),
    },
}

# Lengths below are for a tree of ordinary size, as in _trace.py, times UNIT.
UNIT = 4.0
MIN_TWIG = 0.1 * UNIT     # Shorter side twigs are skeleton noise.
TOLERANCE = 0.022 * UNIT  # Polyline simplification.


def is_bark(r, g, b):
    """Any brown, lit or in the shade: the background is blue-grey."""
    return r - b > 6


# ------------------------------------------------------------------- masks

def cell(name, state):
    """The tree's cell enlarged, the foot in it and the pixels per meter."""
    t = TREES[name]
    c = t[state]
    im = Image.open(os.path.join(REFERENCE, PICTURES[state])).convert("RGB").crop(c["box"])
    im = im.resize((im.width * S, im.height * S), Image.BICUBIC)
    fx, fy = (c["foot"][0] - c["box"][0]) * S, (c["foot"][1] - c["box"][1]) * S
    k = (c["foot"][1] - c["top"]) * S / t["height"]
    return im, fx, fy, k


def mask_of(im, test):
    w, h = im.size
    data = im.tobytes()
    grid = [bytearray(w) for _ in range(h)]
    for y in range(h):
        row = grid[y]
        o = y * w * 3
        for x in range(w):
            if test(data[o], data[o + 1], data[o + 2]):
                row[x] = 1
            o += 3
    return grid


def distance(grid):
    """Chamfer (3-4) distance to the background, in pixels."""
    h, w = len(grid), len(grid[0])
    big = 10 ** 6
    d = [[big if v else 0 for v in row] for row in grid]
    for y in range(h):
        row = d[y]
        up = d[y - 1] if y else None
        for x in range(w):
            v = row[x]
            if not v:
                continue
            if x:
                v = min(v, row[x - 1] + 3)
            else:
                v = 3
            if up is not None:
                v = min(v, up[x] + 3)
                if x:
                    v = min(v, up[x - 1] + 4)
                if x < w - 1:
                    v = min(v, up[x + 1] + 4)
            else:
                v = 3
            row[x] = v
    for y in range(h - 1, -1, -1):
        row = d[y]
        dn = d[y + 1] if y < h - 1 else None
        for x in range(w - 1, -1, -1):
            v = row[x]
            if not v:
                continue
            if x < w - 1:
                v = min(v, row[x + 1] + 3)
            else:
                v = min(v, 3)
            if dn is not None:
                v = min(v, dn[x] + 3)
                if x:
                    v = min(v, dn[x - 1] + 4)
                if x < w - 1:
                    v = min(v, dn[x + 1] + 4)
            else:
                v = min(v, 3)
            row[x] = v
    return [[v / 3.0 for v in row] for row in d]


def dilate(grid):
    h, w = len(grid), len(grid[0])
    out = [bytearray(row) for row in grid]
    for y in range(h):
        for x in range(w):
            if grid[y][x]:
                continue
            if ((x and grid[y][x - 1]) or (x < w - 1 and grid[y][x + 1])
                    or (y and grid[y - 1][x]) or (y < h - 1 and grid[y + 1][x])):
                out[y][x] = 1
    return out


def thin(grid):
    """Zhang-Suen thinning, in place: leaves a one-pixel-wide skeleton.
    Only the pixels next to the background can go in a pass, so only those
    are looked at."""
    h, w = len(grid), len(grid[0])
    for y in (0, h - 1):
        for x in range(w):
            grid[y][x] = 0
    for y in range(h):
        grid[y][0] = grid[y][w - 1] = 0
    around = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]
    active = {(x, y) for y in range(1, h - 1) for x in range(1, w - 1)
              if grid[y][x] and not all(grid[y + dy][x + dx] for dx, dy in around)}
    changed = True
    while changed:
        changed = False
        for step in (0, 1):
            remove = []
            for x, y in active:
                up, mid, dn = grid[y - 1], grid[y], grid[y + 1]
                p2, p3, p4, p5 = up[x], up[x + 1], mid[x + 1], dn[x + 1]
                p6, p7, p8, p9 = dn[x], dn[x - 1], mid[x - 1], up[x - 1]
                n = p2 + p3 + p4 + p5 + p6 + p7 + p8 + p9
                if n < 2 or n > 6:
                    continue
                seq = (p2, p3, p4, p5, p6, p7, p8, p9, p2)
                if sum(1 for i in range(8) if not seq[i] and seq[i + 1]) != 1:
                    continue
                if step == 0:
                    if p2 * p4 * p6 or p4 * p6 * p8:
                        continue
                else:
                    if p2 * p4 * p8 or p2 * p6 * p8:
                        continue
                remove.append((x, y))
            if remove:
                changed = True
                for x, y in remove:
                    grid[y][x] = 0
                for x, y in remove:
                    active.discard((x, y))
                    for dx, dy in around:
                        if grid[y + dy][x + dx]:
                            active.add((x + dx, y + dy))
    return [(x, y) for y in range(h) for x in range(w) if grid[y][x]]


# ---------------------------------------------------------------- skeleton

NEIGHBORS = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
             (1, 1, 1.4142), (1, -1, 1.4142), (-1, 1, 1.4142), (-1, -1, 1.4142)]


def simplify(points, keep, tolerance):
    """Douglas-Peucker on (x, z, ...) points; indices in `keep` stay."""
    n = len(points)
    stay = [False] * n
    stay[0] = stay[-1] = True
    for i in keep:
        stay[i] = True
    anchors = [i for i in range(n) if stay[i]]
    stack = list(zip(anchors, anchors[1:]))
    while stack:
        a, b = stack.pop()
        ax, az = points[a][0], points[a][1]
        dx, dz = points[b][0] - ax, points[b][1] - az
        length = math.hypot(dx, dz) or 1e-9
        worst, at = 0.0, None
        for i in range(a + 1, b):
            px, pz = points[i][0] - ax, points[i][1] - az
            t = max(0.0, min(1.0, (px * dx + pz * dz) / (length * length)))
            d = math.hypot(px - dx * t, pz - dz * t)
            if d > worst:
                worst, at = d, i
        if at is not None and worst > tolerance:
            stay[at] = True
            stack += [(a, at), (at, b)]
    return [i for i in range(n) if stay[i]]


def thinning(values):
    """The never-growing sequence closest to `values` (least absolute
    difference): a branch thins toward its tip, whatever it crosses in the
    picture (which reads thicker) or wherever the picture lost it (thinner)."""
    blocks = []  # [values, median]
    for v in values:
        blocks.append([[v], v])
        while len(blocks) > 1 and blocks[-2][1] < blocks[-1][1]:
            last = blocks.pop()
            blocks[-1][0] += last[0]
            ordered = sorted(blocks[-1][0])
            blocks[-1][1] = ordered[len(ordered) // 2]
    return [m for vals, m in blocks for _ in vals]


def trace_branches(name, debug):
    t = TREES[name]
    im, fx, fy, k = cell(name, "bare")
    w, h = im.size
    bark = mask_of(im, is_bark)
    # Below the cut the trunk is not traced: it goes on straight down from
    # its width at the cut, so that the skeleton crosses the cut along its
    # center line.
    cut = int(fy - (t["root_z"] - 0.12 * UNIT) * k)
    runs, start = [], None
    for x in range(w + 1):
        on = x < w and bark[cut][x]
        if on and start is None:
            start = x
        elif not on and start is not None:
            runs.append((x - start, start, x))
            start = None
    _, a, b = max(runs)
    column = bytearray(w)
    column[a:b] = bytes([1]) * (b - a)
    for y in range(cut + 1, h):
        bark[y] = bytearray(column)
    bark += [bytearray(column) for _ in range(b - a)]
    dist = distance(bark)
    grid = dilate(bark)
    top = int(fy - t["root_z"] * k)
    pixels = {p for p in thin(grid) if p[1] <= top}
    # The root: the thickest place of the skeleton at that height.
    root = max((p for p in pixels if p[1] >= top - 3 and a <= p[0] < b), key=lambda p: (dist[p[1]][p[0]], p))
    # Cheapest paths from the root, cheaper along the thick branches, so a
    # twig that crosses a branch in the picture hangs from that branch: a
    # spanning tree of the skeleton.
    best = {root: 0.0}
    parent = {root: None}
    heap = [(0.0, root)]
    while heap:
        d, p = heapq.heappop(heap)
        if d > best[p]:
            continue
        for dx, dy, c in NEIGHBORS:
            q = (p[0] + dx, p[1] + dy)
            if q not in pixels:
                continue
            e = d + c / (1.0 + dist[q[1]][q[0]])
            if e < best.get(q, 1e18):
                best[q] = e
                parent[q] = p
                heapq.heappush(heap, (e, q))
    children = {p: [] for p in parent}
    for p, q in parent.items():
        if q is not None:
            children[q].append(p)
    order = sorted(parent, key=lambda p: -best[p])
    reach, mass = {}, {}
    for p in order:  # Tips first.
        reach[p] = max([reach[c] + math.hypot(c[0] - p[0], c[1] - p[1]) for c in children[p]], default=0.0)
        mass[p] = 1 + sum(mass[c] for c in children[p])
    radius = {p: max(dist[p[1]][p[0]], 1.0) / k for p in parent}

    branches = []  # [parent index, parent vertex, [(x, z, r)]]
    todo = [(None, root, (-1, 0))]
    while todo:
        # One branch: from `start` (a pixel of the parent, or the root)
        # through `first` along the larger way to a tip.
        start, first, parent_index = todo.pop()
        chain = [start] if start is not None else []
        forks = []
        p = first
        while True:
            chain.append(p)
            kids = sorted(children[p], key=lambda c: (-mass[c], c))
            if not kids:
                break
            for c in kids[1:]:
                length = (reach[c] + 1.0) / k
                if length >= max(MIN_TWIG, 1.6 * radius[p]):
                    forks.append((len(chain) - 1, c))
            p = kids[0]
        # Smooth the pixel staircase and the thickness.
        n = len(chain)
        pts = []
        for i in range(n):
            lo, hi = max(0, i - 3), min(n, i + 4)
            if i == 0 or i == n - 1:
                lo, hi = i, i + 1
            x = sum(q[0] for q in chain[lo:hi]) / (hi - lo)
            y = sum(q[1] for q in chain[lo:hi]) / (hi - lo)
            pts.append(((x - fx) / k, (fy - y) / k, radius[chain[i]]))
        if start is not None:
            # The first pixels are inside the parent: the branch's own
            # thickness is the one just outside it.
            away = 1.3 * radius[start] * k + 2
            j = next((i for i, q in enumerate(chain) if math.hypot(q[0] - start[0], q[1] - start[1]) > away),
                     n - 1)
            pts = [(x, z, pts[j][2]) if i < j else (x, z, r) for i, (x, z, r) in enumerate(pts)]
        pts = [(x, z, r) for (x, z, _), r in zip(pts, thinning([r for _, _, r in pts]))]
        index = len(branches)
        kept = simplify(pts, [i for i, _ in forks], TOLERANCE)
        where = {i: j for j, i in enumerate(kept)}
        branches.append([parent_index[0], parent_index[1], [pts[i] for i in kept]])
        # Children are numbered after their parent, in a fixed order.
        todo += [(chain[i], c, (index, where[i])) for i, c in reversed(forks)]
    # A branch is never thicker than where it leaves its parent.
    for b in branches:
        limit = branches[b[0]][2][b[1]][2] if b[0] >= 0 else 1e9
        b[2] = [(round(x, 2), round(z, 2), round(min(r, limit), 3)) for x, z, r in b[2]]
    xs = [p[0] for b in branches for p in b[2]]
    zs = [p[1] for b in branches for p in b[2]]
    profile = outline(bark[:cut], fx, fy, k)
    if debug:
        draw = ImageDraw.Draw(im)
        for b in branches:
            pts = [(fx + x * k, fy - z * k) for x, z, r in b[2]]
            draw.line(pts, fill=(255, 255, 0) if b[0] < 0 else (0, 255, 255), width=1)
            draw.ellipse((pts[-1][0] - 2, pts[-1][1] - 2, pts[-1][0] + 2, pts[-1][1] + 2), outline=(255, 0, 0))
        grid_lines(draw, im, fx, fy, k)
        im.save(os.path.join(debug, name + "_trace.png"))
    print(f"TRACE {name}: {len(branches)} branches, {sum(len(b[2]) for b in branches)} points, "
          f"x {min(xs):.2f} .. {max(xs):.2f}, top {max(zs):.2f}")
    return branches, profile


def grid_lines(draw, im, fx, fy, k, step=5.0):
    """A grid every `step` meters on a debug picture."""
    w, h = im.size
    i = 0
    while fy - i * step * k > 0:
        y = fy - i * step * k
        draw.line((0, y, w, y), fill=(255, 255, 255) if i == 0 else (200, 200, 200))
        draw.text((2, y - 11), f"{i * step:g}", fill=(255, 255, 255))
        i += 1
    i = -int(fx / (step * k))
    while fx + i * step * k < w:
        x = fx + i * step * k
        draw.line((x, 0, x, h), fill=(255, 255, 255) if i == 0 else (200, 200, 200))
        draw.text((x + 2, 2), f"{i * step:g}", fill=(255, 255, 255))
        i += 1


def outline(grid, fx, fy, k, step=0.25 * UNIT):
    """Width profile of a mask: (z, leftmost x, rightmost x) every `step`."""
    bands = {}
    for y in range(len(grid)):
        row = grid[y]
        a = row.find(1)
        if a < 0:
            continue
        b = row.rfind(1)
        i = int(((fy - y) / k) / step)
        lo, hi = bands.get(i, (1e9, -1e9))
        bands[i] = (min(lo, (a - fx) / k), max(hi, (b - fx) / k))
    return [(round((i + 0.5) * step, 2), round(lo, 2), round(hi, 2)) for i, (lo, hi) in sorted(bands.items())]


# ------------------------------------------------------------------ canopy

def components(grid):
    h, w = len(grid), len(grid[0])
    seen = [bytearray(w) for _ in range(h)]
    out = []
    for y in range(h):
        for x in range(w):
            if grid[y][x] and not seen[y][x]:
                comp = [(x, y)]
                seen[y][x] = 1
                i = 0
                while i < len(comp):
                    cx, cy = comp[i]
                    i += 1
                    for dx, dy, _ in NEIGHBORS:
                        nx, ny = cx + dx, cy + dy
                        if 0 <= nx < w and 0 <= ny < h and grid[ny][nx] and not seen[ny][nx]:
                            seen[ny][nx] = 1
                            comp.append((nx, ny))
                out.append(comp)
    return out


def fill(grid, grow):
    """Closes the gaps up to 2 x `grow` pixels wide and fills the holes: what
    the background cannot reach from the picture's border."""
    h, w = len(grid), len(grid[0])
    big = grid
    for _ in range(grow):
        big = dilate(big)
    outside = [bytearray(w) for _ in range(h)]
    stack = [(x, y) for x in range(w) for y in (0, h - 1)] + [(x, y) for y in range(h) for x in (0, w - 1)]
    while stack:
        x, y = stack.pop()
        if x < 0 or y < 0 or x >= w or y >= h or outside[y][x] or big[y][x]:
            continue
        outside[y][x] = 1
        stack += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    for _ in range(grow):
        outside = dilate(outside)
    return [bytearray(0 if o else 1 for o in row) for row in outside]


def trace_canopy(name, debug):
    t = TREES[name]
    im, fx, fy, k = cell(name, "bloom")
    w, h = im.size
    px = im.load()
    grid = mask_of(im, t["foliage"])
    # Drop the grass, the flowers and the fallen petals: small pieces, or
    # pieces that stay near the ground.
    for comp in components(grid):
        top = (fy - min(y for _, y in comp)) / k
        if len(comp) < 0.3 * k * k or top < 0.2 * t["height"]:
            for x, y in comp:
                grid[y][x] = 0
    grid = fill(grid, 2)
    profile = outline(grid, fx, fy, k)
    dist = distance(grid)
    # Greedy cover: the largest circle that fits, widened to an ellipse
    # while it stays inside the foliage (the flat pads of some trees), then
    # the next one in what is left, until only the fringe remains.
    todo = {(x, y) for y in range(h) for x in range(w) if grid[y][x]}
    total = len(todo)
    blobs = []
    blob_min, blob_max, blob_wide = t["blob"]
    rmax, rmin = blob_max * k, blob_min * k

    def filled(x, y, a, r):
        hit = count = 0
        for dy in range(-int(r), int(r) + 1, 2):
            for dx in range(-int(a), int(a) + 1, 2):
                if (dx / a) ** 2 + (dy / r) ** 2 > 1.0:
                    continue
                count += 1
                qx, qy = x + dx, y + dy
                if 0 <= qx < w and 0 <= qy < h and grid[qy][qx]:
                    hit += 1
        return hit / max(1, count)

    while todo:
        x, y = max(todo, key=lambda p: (min(dist[p[1]][p[0]], rmax), -p[1], p[0]))
        r = min(dist[y][x], rmax)
        if r < rmin:
            break
        a = r
        while a < r * blob_wide and a < blob_max * 1.6 * k and filled(x, y, a * 1.2, r) > 0.93:
            a *= 1.2
        r *= 1.12
        a *= 1.12
        # Its color in the picture, for the tone of its leaves.
        acc, count = [0, 0, 0], 0
        for dy in range(-int(r), int(r) + 1, 2):
            for dx in range(-int(a), int(a) + 1, 2):
                qx, qy = x + dx, y + dy
                if (dx / a) ** 2 + (dy / r) ** 2 <= 1.0 and 0 <= qx < w and 0 <= qy < h:
                    c = px[qx, qy]
                    if t["foliage"](*c):
                        acc = [acc[i] + c[i] for i in range(3)]
                        count += 1
        color = [int(v / max(1, count)) for v in acc]
        blobs.append((round((x - fx) / k, 2), round((fy - y) / k, 2), round(a / k, 2), round(r / k, 2),
                      (color[0] << 16) | (color[1] << 8) | color[2]))
        todo = {p for p in todo if ((p[0] - x) / (a * 1.16)) ** 2 + ((p[1] - y) / (r * 1.16)) ** 2 > 1.0}
    if debug:
        draw = ImageDraw.Draw(im)
        for x, z, a, r, color in blobs:
            cx, cy = fx + x * k, fy - z * k
            draw.ellipse((cx - a * k, cy - r * k, cx + a * k, cy + r * k), outline=(0, 0, 0))
        for y in range(1, h - 1):
            for x in range(1, w - 1):
                if grid[y][x] and not (grid[y][x - 1] and grid[y][x + 1] and grid[y - 1][x] and grid[y + 1][x]):
                    px[x, y] = (255, 255, 255)
        grid_lines(draw, im, fx, fy, k)
        im.save(os.path.join(debug, name + "_canopy.png"))
    print(f"TRACE {name}: {len(blobs)} blobs, {total / k / k:.1f} m2 of foliage")
    return blobs, profile


# ------------------------------------------------------------------ output

def write(trees):
    lines = ['"""Branch structure and canopy of the traced giant trees, read from the',
             'reference pictures by _giant_trace.py. Generated: do not edit by hand.',
             '',
             'TREES[name] = {',
             '    "branches": [(parent branch, parent vertex, [(x, z, radius), ...]), ...],',
             '    "blobs": [(x, z, radius along x, radius along z, color in the picture), ...],',
             '    "outline": [(z, leftmost x, rightmost x), ...],   # Of the canopy and the branches.',
             '}',
             'Meters, X right and Z up from the foot of the trunk. The first branch is',
             'the trunk; the others start at a vertex of their parent."""',
             '',
             'TREES = {']
    for name, (branches, blobs, profile) in trees.items():
        lines.append(f'    "{name}": {{')
        lines.append('        "branches": [')
        for parent, vertex, pts in branches:
            text = ", ".join(f"({x:g}, {z:g}, {r:g})" for x, z, r in pts)
            lines.append(f'            ({parent}, {vertex}, [{text}]),')
        lines.append('        ],')
        lines.append('        "blobs": [')
        for x, z, a, r, color in blobs:
            lines.append(f'            ({x:g}, {z:g}, {a:g}, {r:g}, 0x{color:06X}),')
        lines.append('        ],')
        text = ", ".join(f"({z:g}, {a:g}, {b:g})" for z, a, b in profile)
        lines.append(f'        "outline": [{text}],')
        lines.append('    },')
    lines.append('}')
    with open(os.path.join(HERE, "_giant_traced.py"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")


def merge(a, b):
    """The wider of two width profiles at every height."""
    bands = {}
    for z, lo, hi in a + b:
        old = bands.get(z, (1e9, -1e9))
        bands[z] = (min(old[0], lo), max(old[1], hi))
    return [(z, lo, hi) for z, (lo, hi) in sorted(bands.items())]


def main():
    debug = sys.argv[1] if len(sys.argv) > 1 else None
    only = set(sys.argv[2:])
    if debug:
        os.makedirs(debug, exist_ok=True)
    trees = {}
    if only:  # Keep the other trees as they are.
        sys.path.insert(0, HERE)
        import _giant_traced
        for name, t in _giant_traced.TREES.items():
            trees[name] = (t["branches"], t["blobs"], t["outline"])
    for name in TREES:
        if only and name not in only:
            continue
        branches, bare_profile = trace_branches(name, debug)
        blobs, bloom_profile = trace_canopy(name, debug)
        trees[name] = (branches, blobs, merge(bare_profile, bloom_profile))
    write({name: trees[name] for name in TREES if name in trees})


if __name__ == "__main__":
    main()
