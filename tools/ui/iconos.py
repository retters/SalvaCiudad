"""The interface's icon atlases (phase 119, D-11706).

The icons are the mockups' own set (docs/propuestas/interfaz/kit/iconos.js),
kept in data/ui/icons/icons.json: SVG path data on a 24 x 24 grid, drawn
with round strokes (s), an optional tone layer (f) and always-filled dots
(k). This tool draws them white, with alpha, in three modes:

    stroke   strokes and dots
    duotone  strokes and dots over the tone layer at 20 % alpha
    solid    strokes and dots over the tone layer fully filled

each at 1x (24 px) and 2x (48 px), into data/ui/icons/<mode>@<n>x.png, with
the RmlUi sprite sheet of each in <mode>@<n>x.rcss (sprites "icon-<name>").
The style tints them with image-color. Only PIL: the paths are flattened to
lines and drawn 8 times larger, then reduced (box filter), so the result is
the same file every time.

    python tools/ui/iconos.py             build the atlases
    python tools/ui/iconos.py comprobar   build into a temporary folder and
                                          compare with the committed files
    python tools/ui/iconos.py importar    icons.json from the mockups' iconos.js
"""
import json
import math
import re
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
ICONS = ROOT / "data" / "ui" / "icons"
SOURCE = ICONS / "icons.json"
MOCKUP = ROOT / "docs" / "propuestas" / "interfaz" / "kit" / "iconos.js"

GRID = 24
STROKE = 1.8      # Grid units, as the mockups' default --icon-stroke.
TONE = 0.20       # Alpha of the tone layer in duotone.
SUPER = 8         # Supersampling.
COLUMNS = 12
MODES = ("stroke", "duotone", "solid")
SCALES = (1, 2)
MAX_ICONS = 512


# --- SVG path data --------------------------------------------------------

TOKEN = re.compile(r"[MmLlHhVvCcSsQqTtAaZz]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")


def parse(d):
    """Path data to a list of subpaths, each a list of (x, y) points and a
    closed flag. Curves and arcs are flattened."""
    if len(d) > 20000:
        raise ValueError("path too long")
    # Arc flags may be glued to what follows ("a2 2 0 011 1"): flag() splits them.
    tokens = TOKEN.findall(d)
    out = []
    pts = []
    closed = False
    x = y = 0.0
    sx = sy = 0.0
    last_ctrl = None
    cmd = None
    i = 0

    def num():
        nonlocal i
        if i >= len(tokens) or tokens[i].isalpha():
            raise ValueError("number expected")
        v = float(tokens[i])
        i += 1
        return v

    def flag():
        nonlocal i
        t = tokens[i]
        if t.isalpha():
            raise ValueError("flag expected")
        if t[0] in "01" and len(t) > 1 and t[1] in "01.":
            # "011" or "01.5": the first digit is the flag, keep the rest.
            tokens[i] = t[1:]
            return float(t[0])
        i += 1
        return float(t)

    def finish():
        nonlocal pts, closed
        if len(pts) > 1:
            out.append((pts, closed))
        pts = []
        closed = False

    def cubic(p0, p1, p2, p3):
        n = 16
        for k in range(1, n + 1):
            t = k / n
            a = (1 - t) ** 3
            b = 3 * (1 - t) ** 2 * t
            c = 3 * (1 - t) * t * t
            e = t ** 3
            pts.append((a * p0[0] + b * p1[0] + c * p2[0] + e * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + e * p3[1]))

    def arc(x0, y0, rx, ry, phi, large, sweep, x1, y1):
        # SVG arc, endpoint to center form (SVG 1.1, appendix F.6).
        if rx == 0 or ry == 0 or (x0 == x1 and y0 == y1):
            pts.append((x1, y1))
            return
        rx, ry = abs(rx), abs(ry)
        cp, sp = math.cos(math.radians(phi)), math.sin(math.radians(phi))
        dx, dy = (x0 - x1) / 2, (y0 - y1) / 2
        x1p, y1p = cp * dx + sp * dy, -sp * dx + cp * dy
        lam = (x1p * x1p) / (rx * rx) + (y1p * y1p) / (ry * ry)
        if lam > 1:
            s = math.sqrt(lam)
            rx, ry = rx * s, ry * s
        num_ = rx * rx * ry * ry - rx * rx * y1p * y1p - ry * ry * x1p * x1p
        den = rx * rx * y1p * y1p + ry * ry * x1p * x1p
        coef = math.sqrt(max(0.0, num_ / den)) if den else 0.0
        if large == sweep:
            coef = -coef
        cxp, cyp = coef * rx * y1p / ry, -coef * ry * x1p / rx
        cx = cp * cxp - sp * cyp + (x0 + x1) / 2
        cy = sp * cxp + cp * cyp + (y0 + y1) / 2

        def angle(ux, uy, vx, vy):
            a = math.atan2(ux * vy - uy * vx, ux * vx + uy * vy)
            return a

        t1 = angle(1, 0, (x1p - cxp) / rx, (y1p - cyp) / ry)
        dt = angle((x1p - cxp) / rx, (y1p - cyp) / ry, (-x1p - cxp) / rx, (-y1p - cyp) / ry)
        if not sweep and dt > 0:
            dt -= 2 * math.pi
        elif sweep and dt < 0:
            dt += 2 * math.pi
        n = max(4, int(abs(dt) / (math.pi / 24)) + 1)
        for k in range(1, n + 1):
            t = t1 + dt * k / n
            px, py = rx * math.cos(t), ry * math.sin(t)
            pts.append((cp * px - sp * py + cx, sp * px + cp * py + cy))

    while i < len(tokens):
        t = tokens[i]
        if t.isalpha():
            cmd = t
            i += 1
        elif cmd is None:
            raise ValueError("path must start with a command")
        rel = cmd.islower()
        c = cmd.upper()
        ox, oy = (x, y) if rel else (0.0, 0.0)
        if c == "M":
            finish()
            x, y = num() + ox, num() + oy
            sx, sy = x, y
            pts = [(x, y)]
            cmd = "l" if rel else "L"  # Following pairs are lines.
            last_ctrl = None
        elif c == "L":
            x, y = num() + ox, num() + oy
            pts.append((x, y))
            last_ctrl = None
        elif c == "H":
            x = num() + ox
            pts.append((x, y))
            last_ctrl = None
        elif c == "V":
            y = num() + oy
            pts.append((x, y))
            last_ctrl = None
        elif c == "C":
            p1 = (num() + ox, num() + oy)
            p2 = (num() + ox, num() + oy)
            p3 = (num() + ox, num() + oy)
            cubic((x, y), p1, p2, p3)
            last_ctrl = p2
            x, y = p3
        elif c == "S":
            p1 = (2 * x - last_ctrl[0], 2 * y - last_ctrl[1]) if last_ctrl else (x, y)
            p2 = (num() + ox, num() + oy)
            p3 = (num() + ox, num() + oy)
            cubic((x, y), p1, p2, p3)
            last_ctrl = p2
            x, y = p3
        elif c == "A":
            rx, ry, phi = num(), num(), num()
            large, sweep = flag(), flag()
            x1, y1 = num() + ox, num() + oy
            arc(x, y, rx, ry, phi, large, sweep, x1, y1)
            x, y = x1, y1
            last_ctrl = None
        elif c == "Z":
            if pts:
                pts.append((sx, sy))
                closed = True
            x, y = sx, sy
            finish()
            pts = [(x, y)]
            last_ctrl = None
            cmd = None
        else:
            raise ValueError(f"unsupported command {cmd}")
    finish()
    return out


# --- Drawing --------------------------------------------------------------

def fill_mask(size, subpaths):
    scale = size * SUPER / GRID
    img = Image.new("L", (size * SUPER, size * SUPER), 0)
    d = ImageDraw.Draw(img)
    for pts, _closed in subpaths:
        if len(pts) >= 3:
            d.polygon([(px * scale, py * scale) for px, py in pts], fill=255)
    return img


def stroke_mask(size, subpaths, width):
    scale = size * SUPER / GRID
    r = width * scale / 2
    img = Image.new("L", (size * SUPER, size * SUPER), 0)
    d = ImageDraw.Draw(img)
    for pts, _closed in subpaths:
        p = [(px * scale, py * scale) for px, py in pts]
        for (ax, ay), (bx, by) in zip(p, p[1:]):
            dx, dy = bx - ax, by - ay
            n = math.hypot(dx, dy)
            if n > 0:
                nx, ny = -dy / n * r, dx / n * r
                d.polygon([(ax + nx, ay + ny), (bx + nx, by + ny), (bx - nx, by - ny), (ax - nx, ay - ny)], fill=255)
        for cx, cy in p:  # Round joins and caps.
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=255)
    return img


def icon_image(icon, size, mode):
    """The icon, white with alpha, `size` pixels square."""
    big = size * SUPER
    lines = Image.new("L", (big, big), 0)
    if icon.get("s"):
        lines = stroke_mask(size, parse(icon["s"]), STROKE)
    if icon.get("k"):
        lines = ImageChops.lighter(lines, fill_mask(size, parse(icon["k"])))
    tone = Image.new("L", (big, big), 0)
    if icon.get("f") and mode != "stroke":
        tone = fill_mask(size, parse(icon["f"]))
    lines = lines.reduce(SUPER)
    tone = tone.reduce(SUPER)
    level = TONE if mode == "duotone" else 1.0
    alpha = Image.new("L", (size, size), 0)
    a_px = alpha.load()
    l_px = lines.load()
    t_px = tone.load()
    for yy in range(size):
        for xx in range(size):
            s = l_px[xx, yy] / 255.0
            f = t_px[xx, yy] / 255.0 * level
            a_px[xx, yy] = round((1.0 - (1.0 - s) * (1.0 - f)) * 255)
    out = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    out.putalpha(alpha)
    return out


# --- Atlas ----------------------------------------------------------------

def load_icons():
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    icons = data.get("icons")
    if not isinstance(icons, dict) or not icons or len(icons) > MAX_ICONS:
        raise SystemExit("icons.json: 'icons' must be an object with 1 to 512 icons")
    for name, icon in icons.items():
        if not re.fullmatch(r"[a-z][a-z0-9-]{0,39}", name):
            raise SystemExit(f"icons.json: bad icon name '{name}'")
        if not isinstance(icon, dict) or not set(icon) <= {"s", "f", "k"} or not icon:
            raise SystemExit(f"icons.json: '{name}' needs s, f or k path data only")
        for key, d in icon.items():
            if not isinstance(d, str):
                raise SystemExit(f"icons.json: '{name}.{key}' is not a string")
            try:
                parse(d)
            except (ValueError, IndexError, TypeError) as e:
                raise SystemExit(f"icons.json: '{name}.{key}': {e}")
    return dict(sorted(icons.items()))


def build(out_dir):
    icons = load_icons()
    names = list(icons)
    rows = (len(names) + COLUMNS - 1) // COLUMNS
    written = []
    for mode in MODES:
        for scale in SCALES:
            size = GRID * scale
            gap = 2 * scale
            cell = size + gap
            atlas = Image.new("RGBA", (COLUMNS * cell + gap, rows * cell + gap), (255, 255, 255, 0))
            lines = [
                f"/* Generated by tools/ui/iconos.py from icons.json: {mode} icons at {scale}x. */",
                "",
                "@spritesheet icons",
                "{",
                f"\tsrc: /icons/{mode}@{scale}x.png;",
                f"\tresolution: {scale}x;",
            ]
            for n, name in enumerate(names):
                x = gap + (n % COLUMNS) * cell
                y = gap + (n // COLUMNS) * cell
                atlas.paste(icon_image(icons[name], size, mode), (x, y))
                lines.append(f"\ticon-{name}: {x}px {y}px {size}px {size}px;")
            lines.append("}")
            png = out_dir / f"{mode}@{scale}x.png"
            atlas.save(png, optimize=False, compress_level=9)
            rcss = out_dir / f"{mode}@{scale}x.rcss"
            rcss.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
            written += [png.name, rcss.name]
    return written


def import_mockups():
    text = MOCKUP.read_text(encoding="utf-8")
    body = text[text.index("window.ICONOS = {") : text.index("};")]
    icons = {}
    for m in re.finditer(r"^\s+([a-z][a-z0-9_]*): \{(.*)\},?\s*$", body, re.M):
        name = m.group(1).replace("_", "-")
        icons[name] = {k: v for k, v in re.findall(r"([sfk]): '([^']*)'", m.group(2))}
    data = {
        "about": "The interface's own icons (from the mockups' kit/iconos.js): SVG path data on a 24 x 24 grid; "
                 "s = round strokes, f = tone layer, k = filled dots. tools/ui/iconos.py draws the atlases.",
        "icons": dict(sorted(icons.items())),
    }
    SOURCE.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"{SOURCE}: {len(icons)} icons")


def main():
    what = sys.argv[1] if len(sys.argv) > 1 else "build"
    if what == "importar":
        import_mockups()
    elif what == "comprobar":
        with tempfile.TemporaryDirectory() as tmp:
            names = build(Path(tmp))
            bad = [n for n in names if (Path(tmp) / n).read_bytes() != (ICONS / n).read_bytes()]
        if bad:
            raise SystemExit("different from the committed files: " + ", ".join(bad))
        print(f"the same: {len(names)} files")
    elif what == "build":
        names = build(ICONS)
        print(f"{ICONS}: {len(names)} files")
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
