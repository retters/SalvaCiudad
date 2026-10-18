"""Writes the grain of the Frosted style (data/ui/styles/frosted/grain.png): the
mockups' SVG fractal noise (gray, alpha up to about 9 %) approximated with
three octaves of smoothed random noise. Fixed seed: the same file every time.

    python tools/ui/ruido.py [output.png]
"""
import random
import sys
from pathlib import Path

from PIL import Image, ImageFilter

SIZE = 160
OUT = Path(__file__).resolve().parents[2] / "data" / "ui" / "styles" / "frosted" / "grain.png"


def octave(rng, cell):
    small = Image.new("L", (SIZE // cell, SIZE // cell))
    small.frombytes(bytes(rng.randrange(256) for _ in range(small.width * small.height)))
    return small.resize((SIZE, SIZE), Image.BICUBIC)


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else OUT
    rng = random.Random(118)
    layers = [octave(rng, c) for c in (1, 2, 4)]
    data = []
    for a, b, c in zip(*(l.tobytes() for l in layers)):
        v = (a * 4 + b * 2 + c) / 7.0
        data.append((128, 128, 128, round(v / 255.0 * 0.18 * 255)))
    img = Image.new("RGBA", (SIZE, SIZE))
    img.putdata(data)
    img = img.filter(ImageFilter.SMOOTH)
    img.save(out, optimize=True)
    print(out)


if __name__ == "__main__":
    main()
