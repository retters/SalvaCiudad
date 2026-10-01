"""Traces the tree reference pictures into the data the generator builds from.

    python art/blender/lowpoly_trees/_trace.py [debug folder] [tree names]

A development tool (system Python with PIL; Blender is not needed): it is
run by hand when the reference pictures change, and writes _traced.py next
to itself. The models are built from _traced.py alone.

The three pictures in the repository root show the same 16 trees in a 4 x 4
grid: "Arboles 1.png" in bloom, "Arboles 2.png" in autumn and "Arboles 3.png"
without leaves. For each tree:

  * the bare picture gives the branch structure: the bark pixels are
    thinned to a one-pixel skeleton, the skeleton becomes a tree of
    polylines rooted at the trunk, and the distance to the background gives
    the thickness along every branch;
  * the bloom picture gives the canopy: the foliage pixels are covered
    with ellipses ("blobs", the clumps of leaves) and their outline is kept
    as a width profile, from which the generator derives the depth;
  * the autumn picture gives the colors of the canopy in autumn, blob by
    blob and in a grid of small cells.

Everything is in meters, X to the right and Z up, from the foot of the
trunk. With a debug folder, also writes one overlay image per tree.
"""

import heapq
import math
import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
PICTURES = {"bloom": "Arboles 1.png", "autumn": "Arboles 2.png", "bare": "Arboles 3.png"}
# Rows of the grid in every picture (top, bottom) and the column borders.
ROWS = {
    "bloom": [(5, 255), (275, 497), (520, 740), (765, 985)],
    "autumn": [(5, 255), (275, 497), (520, 740), (765, 985)],
    "bare": [(5, 248), (270, 490), (510, 732), (752, 980)],
}
COLUMNS = [0, 362, 765, 1108, 1536]
NAMES = [
    ["cherry_1", "cherry_2", "cherry_weeping", "cherry_3"],
    ["jacaranda_1", "jacaranda_2", "jacaranda_3", "jacaranda_4"],
    ["elm_1", "elm_2", "elm_3", "elm_4"],
    ["guayacan_1", "guayacan_2", "guayacan_3", "guayacan_4"],
]
PX_PER_M = 32.0     # Scale of the pictures: the trees come out 6 to 7 m tall.
S = 3               # The skeleton is traced on the picture enlarged S times.
ROOT_Z = 0.7        # The skeleton starts here: below, grass and stones hide the trunk.
MIN_TWIG = 0.1      # Shorter side twigs are skeleton noise.
TOLERANCE = 0.022   # Polyline simplification.
BLOB_MAX = 0.85     # Largest and smallest blob radius.
BLOB_MIN = 0.24
AUTUMN_CELL = 0.4   # Size of the cells the autumn colors are read in.
BLOB_WIDE = 2.2     # A blob may be this many times wider than tall.


# ------------------------------------------------------------------ colors

def is_bark(r, g, b):
    return r - b > 22 and r >= g - 4 and g >= b - 6 and not (g > 140 and b > 108)


def is_strict_bark(r, g, b):
    return r - b > 30 and r > g + 12 and g > b and g < 125 and r < 185


def is_foliage(r, g, b):
    """Leaves or blossom, lit or in the shade: any color that is neither
    the grey background nor brown."""
    if max(r, g, b) - min(r, g, b) <= 26:
        return False
    return not (r > g + 8 and g > b + 4 and r < 185 and g < 125)


# ------------------------------------------------------------------- masks

def cell(state, row, col, scale):
    im = Image.open(os.path.join(ROOT, PICTURES[state])).convert("RGB")
    y0, y1 = ROWS[state][row]
    box = (COLUMNS[col], y0, COLUMNS[col + 1], y1)
    im = im.crop(box)
    if scale != 1:
        im = im.resize((im.width * scale, im.height * scale), Image.BICUBIC)
    return im


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


def foot(im):
    """(x, y) of the foot of the trunk in a picture: the lowest row where
    the dark bark is as wide as a trunk, and the middle of that run."""
    w, h = im.size
    px = im.load()
    scale = w / (COLUMNS[1] - COLUMNS[0])  # Roughly: the cells differ a little.
    scale = max(1, round(scale))
    need = 0.3 * PX_PER_M * scale

    def widest(y):
        best, start, gap = (0, 0), None, 0
        for x in range(w):
            if is_strict_bark(*px[x, y]):
                if start is None:
                    start = x
                gap = 0
                if x - start > best[0]:
                    best = (x - start, (x + start) // 2)
            elif start is not None:
                gap += 1
                if gap > 2 * scale:
                    start = None
        return best

    for y in range(h - 1, h // 2, -1):
        if widest(y)[0] >= need:
            return widest(y - 4 * scale)[1], y
    raise ValueError("no trunk found")


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
    """Zhang-Suen thinning, in place: leaves a one-pixel-wide skeleton."""
    h, w = len(grid), len(grid[0])
    for y in (0, h - 1):
        for x in range(w):
            grid[y][x] = 0
    for y in range(h):
        grid[y][0] = grid[y][w - 1] = 0
    pixels = [(x, y) for y in range(h) for x in range(w) if grid[y][x]]
    changed = True
    while changed:
        changed = False
        for step in (0, 1):
            remove = []
            for x, y in pixels:
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
                pixels = [(x, y) for x, y in pixels if grid[y][x]]
    return pixels


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

    def rec(a, b):
        ax, az = points[a][0], points[a][1]
        bx, bz = points[b][0], points[b][1]
        dx, dz = bx - ax, bz - az
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
            rec(a, at)
            rec(at, b)

    for a, b in zip(anchors, anchors[1:]):
        rec(a, b)
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


def trace_branches(name, row, col, debug):
    im = cell("bare", row, col, S)
    w, h = im.size
    k = S * PX_PER_M  # Pixels per meter.
    fx, fy = foot(im)
    bark = mask_of(im, is_bark)
    # Below the cut the grass and the stones hide the trunk: the trunk goes
    # on straight down from its width at the cut, so that the skeleton
    # crosses the cut along its center line.
    cut = int(fy - (ROOT_Z - 0.12) * k)
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
    bark += [bytearray(column) for _ in range(int(1.2 * k))]
    dist = distance(bark)
    grid = dilate(bark)
    top = int(fy - ROOT_Z * k)
    pixels = {p for p in thin(grid) if p[1] <= top}
    # The root: the thickest place of the skeleton at that height.
    root = max((p for p in pixels if p[1] >= top - 3 and abs(p[0] - fx) < 0.9 * k),
               key=lambda p: (dist[p[1]][p[0]], p))
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

    def walk(start, first, parent_index):
        """One branch: from `start` (a pixel of the parent, or the root)
        through `first` along the longest way to a tip."""
        chain = [start] if start is not None else []
        forks = []
        p = first
        while True:
            chain.append(p)
            kids = sorted(children[p], key=lambda c: -mass[c])  # The branch goes on the larger way.
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
            a, b = max(0, i - 3), min(n, i + 4)
            if i == 0 or i == n - 1:
                a, b = i, i + 1
            x = sum(q[0] for q in chain[a:b]) / (b - a)
            y = sum(q[1] for q in chain[a:b]) / (b - a)
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
        branches.append(None)
        kept = simplify(pts, [i for i, _ in forks], TOLERANCE)
        where = {i: j for j, i in enumerate(kept)}
        branches[index] = [parent_index[0], parent_index[1], [pts[i] for i in kept]]
        for i, c in forks:
            walk(chain[i], c, (index, where[i]))

    sys.setrecursionlimit(100000)
    walk(None, root, (-1, 0))
    # A branch is never thicker than where it leaves its parent.
    for b in branches:
        limit = branches[b[0]][2][b[1]][2] if b[0] >= 0 else 1e9
        b[2] = [(round(x, 3), round(z, 3), round(min(r, limit), 3)) for x, z, r in b[2]]
    xs = [p[0] for b in branches for p in b[2]]
    zs = [p[1] for b in branches for p in b[2]]
    profile = outline(bark[:cut], fx, fy, k)
    if debug:
        draw = ImageDraw.Draw(im)
        for b in branches:
            pts = [(fx + x * k, fy - z * k) for x, z, r in b[2]]
            draw.line(pts, fill=(255, 255, 0) if b[0] < 0 else (0, 255, 255), width=1)
            draw.ellipse((pts[-1][0] - 2, pts[-1][1] - 2, pts[-1][0] + 2, pts[-1][1] + 2), outline=(255, 0, 0))
        im.save(os.path.join(debug, name + "_trace.png"))
    print(f"TRACE {name}: {len(branches)} branches, {sum(len(b[2]) for b in branches)} points, "
          f"x {min(xs):.2f} .. {max(xs):.2f}, top {max(zs):.2f}")
    return branches, profile


def outline(grid, fx, fy, k, step=0.25):
    """Width profile of a mask: (z, leftmost x, rightmost x) every `step`."""
    h, w = len(grid), len(grid[0])
    bands = {}
    for y in range(h):
        row = grid[y]
        a = row.find(1)
        if a < 0:
            continue
        b = row.rfind(1)
        i = int(((fy - y) / k) / step)
        lo, hi = bands.get(i, (1e9, -1e9))
        bands[i] = (min(lo, (a - fx) / k), max(hi, (b - fx) / k))
    return [(round((i + 0.5) * step, 3), round(lo, 2), round(hi, 2)) for i, (lo, hi) in sorted(bands.items())]


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


def trace_canopy(name, row, col, debug):
    scale = 2
    im = cell("bloom", row, col, scale)
    w, h = im.size
    k = scale * PX_PER_M
    fx, fy = foot(im)
    grid = mask_of(im, is_foliage)
    # Drop the fallen petals, the grass and the stones: small pieces, or
    # pieces that stay near the ground.
    for comp in components(grid):
        top = (fy - min(y for _, y in comp)) / k
        if len(comp) < 0.3 * k * k or top < 1.5:
            for x, y in comp:
                grid[y][x] = 0
    grid = fill(grid, 3)
    profile = outline(grid, fx, fy, k)
    dist = distance(grid)
    autumn = cell("autumn", row, col, scale)
    ax, ay = fx, fy  # The pictures share the layout; fallen leaves hide the autumn foot.
    apx = autumn.load()
    # Greedy cover: the largest circle that fits, widened to an ellipse
    # while it stays inside the foliage (the flat layers of some trees),
    # then the next one in what is left, until only the fringe remains.
    todo = {(x, y) for y in range(h) for x in range(w) if grid[y][x]}
    total = len(todo)
    blobs = []
    rmax, rmin = BLOB_MAX * k, BLOB_MIN * k

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
        while a < r * BLOB_WIDE and a < BLOB_MAX * 1.6 * k and filled(x, y, a * 1.2, r) > 0.93:
            a *= 1.2
        r *= 1.12
        a *= 1.12
        # Color of the same place in the autumn picture.
        acc, count = [0, 0, 0], 0
        for dy in range(-int(r), int(r) + 1, 2):
            for dx in range(-int(a), int(a) + 1, 2):
                if (dx / a) ** 2 + (dy / r) ** 2 > 1.0:
                    continue
                qx, qy = x - fx + ax + dx, y - fy + ay + dy
                if 0 <= qx < w and 0 <= qy < autumn.height:
                    c = apx[qx, qy]
                    if is_foliage(*c):
                        acc = [acc[i] + c[i] for i in range(3)]
                        count += 1
        color = tuple(int(v / count) for v in acc) if count >= 8 else None
        blobs.append([round((x - fx) / k, 2), round((fy - y) / k, 2), round(a / k, 2), round(r / k, 2),
                      (color[0] << 16) | (color[1] << 8) | color[2] if color else None])
        todo = {p for p in todo if ((p[0] - x) / (a * 1.16)) ** 2 + ((p[1] - y) / (r * 1.16)) ** 2 > 1.0}
    # The autumn colors, cell by cell: in each cell the most common color
    # (not the average, which would be a mix that no leaf has).
    cells = []
    size = int(AUTUMN_CELL * k)
    for y0 in range(0, h, size):
        for x0 in range(0, w, size):
            bins = {}
            for y in range(y0, min(h, y0 + size), 2):
                for x in range(x0, min(w, x0 + size), 2):
                    qx, qy = x - fx + ax, y - fy + ay
                    if grid[y][x] and 0 <= qx < w and 0 <= qy < autumn.height:
                        c = apx[qx, qy]
                        if is_foliage(*c):
                            bins.setdefault((c[0] >> 5, c[1] >> 5, c[2] >> 5), []).append(c)
            if sum(len(v) for v in bins.values()) < 6:
                continue
            best = max(bins.values(), key=len)
            color = [sum(c[i] for c in best) // len(best) for i in range(3)]
            cells.append((round((x0 + size / 2 - fx) / k, 2), round((fy - y0 - size / 2) / k, 2),
                          (color[0] << 16) | (color[1] << 8) | color[2]))
    for b in blobs:  # Where the autumn tree has no leaves: as the nearest blob that has.
        if b[4] is None:
            near = min((o for o in blobs if o[4] is not None),
                       key=lambda o: (o[0] - b[0]) ** 2 + (o[1] - b[1]) ** 2, default=None)
            b[4] = near[4] if near else 0x808080
    blobs = [tuple(b) for b in blobs]
    if debug:
        draw = ImageDraw.Draw(im)
        for x, z, a, r, color in blobs:
            cx, cy = fx + x * k, fy - z * k
            draw.ellipse((cx - a * k, cy - r * k, cx + a * k, cy + r * k), outline=(0, 0, 0))
            draw.ellipse((cx - 5, cy - 5, cx + 5, cy + 5), fill=(color >> 16, (color >> 8) & 255, color & 255),
                         outline=(0, 0, 0))
        px = im.load()
        for y in range(1, h - 1):
            for x in range(1, w - 1):
                if grid[y][x] and not (grid[y][x - 1] and grid[y][x + 1] and grid[y - 1][x] and grid[y + 1][x]):
                    px[x, y] = (255, 255, 255)
        draw.line((fx - 10, fy, fx + 10, fy), fill=(255, 0, 0))
        im.save(os.path.join(debug, name + "_canopy.png"))
    print(f"TRACE {name}: {len(blobs)} blobs, {total / k / k:.1f} m2 of foliage")
    return blobs, profile, cells


# ------------------------------------------------------------------ output

def write(trees):
    lines = ['"""Branch structure and canopy of every tree, traced from the reference',
             'pictures by _trace.py. Generated: do not edit by hand.',
             '',
             'TREES[name] = {',
             '    "branches": [(parent branch, parent vertex, [(x, z, radius), ...]), ...],',
             '    "blobs": [(x, z, radius along x, radius along z, autumn color), ...],',
             '    "outline": [(z, leftmost x, rightmost x), ...],   # Of the canopy and the branches.',
             '    "autumn": [(x, z, color), ...],   # Color of the autumn canopy, cell by cell.',
             '}',
             'Meters, X right and Z up from the foot of the trunk. The first branch is',
             'the trunk; the others start at a vertex of their parent."""',
             '',
             'TREES = {']
    for name, (branches, blobs, profile, cells) in trees.items():
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
        text = ", ".join(f"({x:g}, {z:g}, 0x{c:06X})" for x, z, c in cells)
        lines.append(f'        "autumn": [{text}],')
        lines.append('    },')
    lines.append('}')
    with open(os.path.join(HERE, "_traced.py"), "w", encoding="utf-8", newline="\n") as f:
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
        import _traced
        for name, t in _traced.TREES.items():
            trees[name] = (t["branches"], t["blobs"], t["outline"], t["autumn"])
    for row in range(4):
        for col in range(4):
            name = NAMES[row][col]
            if only and name not in only:
                continue
            branches, bare_profile = trace_branches(name, row, col, debug)
            blobs, bloom_profile, cells = trace_canopy(name, row, col, debug)
            trees[name] = (branches, blobs, merge(bare_profile, bloom_profile), cells)
    write({name: trees[name] for r in NAMES for name in r if name in trees})


if __name__ == "__main__":
    main()
