"""Sound effects of SalvaCiudad, synthesized (phase 18).

    python art/audio/make_sounds.py data/mods/core/sounds

Pure Python (no libraries): noise, tones and envelopes with a fixed seed,
so running it twice writes the same files. 22 050 Hz, mono, 16-bit WAV.
The game mixes them with SDL (src/audio).
"""

import math
import os
import random
import struct
import sys
import wave

RATE = 22050


def write(folder, name, samples):
    peak = max(1e-6, max(abs(s) for s in samples))
    scale = 0.85 / peak
    data = b"".join(struct.pack("<h", int(max(-1.0, min(1.0, s * scale)) * 32767)) for s in samples)
    with wave.open(os.path.join(folder, name + ".wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(data)


def env(t, attack, decay):
    """A quick rise and an exponential fall."""
    if t < attack:
        return t / attack
    return math.exp(-(t - attack) / decay)


def lowpass(samples, k):
    out = []
    y = 0.0
    for s in samples:
        y += k * (s - y)
        out.append(y)
    return out


def noise(rng, n):
    return [rng.uniform(-1.0, 1.0) for _ in range(n)]


def chop(rng):
    """An axe biting wood: a dull thump and a crack."""
    n = int(RATE * 0.35)
    body = lowpass(noise(rng, n), 0.18)
    out = []
    for i in range(n):
        t = i / RATE
        thump = math.sin(2 * math.pi * 110 * t) * env(t, 0.002, 0.05)
        out.append(body[i] * env(t, 0.001, 0.06) + 0.8 * thump)
    return out


def hammer(rng):
    """A hammer on wood, twice."""
    out = []
    for hit in range(2):
        n = int(RATE * 0.28)
        body = lowpass(noise(rng, n), 0.35)
        for i in range(n):
            t = i / RATE
            ring = math.sin(2 * math.pi * 620 * t) * 0.35 + math.sin(2 * math.pi * 240 * t) * 0.5
            out.append((body[i] * 0.6 + ring) * env(t, 0.001, 0.04))
    return out


def bell(rng):
    """A town bell: inharmonic partials that ring on."""
    n = int(RATE * 2.4)
    partials = ((1.0, 1.0), (2.0, 0.6), (2.4, 0.4), (3.0, 0.25), (4.2, 0.2), (5.4, 0.12))
    base = 330.0
    out = []
    for i in range(n):
        t = i / RATE
        s = sum(a * math.sin(2 * math.pi * base * f * t) * math.exp(-t * (0.9 + f * 0.5)) for f, a in partials)
        out.append(s * min(1.0, t / 0.003))
    return out


def fire(rng):
    """Crackling fire, a loop of two seconds."""
    n = int(RATE * 2.0)
    roar = lowpass(noise(rng, n), 0.05)
    out = [r * 0.6 for r in roar]
    for _ in range(40):
        at = rng.randrange(0, n - 400)
        length = rng.randrange(40, 300)
        for i in range(length):
            out[at + i] += rng.uniform(-1, 1) * math.exp(-i / (length * 0.25)) * 0.9
    # Fade the ends into each other so it loops.
    fade = int(RATE * 0.05)
    for i in range(fade):
        k = i / fade
        out[i] = out[i] * k + out[n - fade + i] * (1 - k)
    return out[: n - fade]


def click(rng):
    """The interface: a short wooden tick."""
    n = int(RATE * 0.06)
    return [math.sin(2 * math.pi * 1400 * i / RATE) * env(i / RATE, 0.0005, 0.008)
            + rng.uniform(-0.2, 0.2) * env(i / RATE, 0.0005, 0.003) for i in range(n)]


def notify(rng):
    """A notification: two soft notes going up."""
    out = []
    for f in (660.0, 880.0):
        n = int(RATE * 0.16)
        for i in range(n):
            t = i / RATE
            out.append((math.sin(2 * math.pi * f * t) + 0.3 * math.sin(4 * math.pi * f * t)) * env(t, 0.005, 0.07))
    return out


def coins(rng):
    """Coins: bright metallic ticks."""
    n = int(RATE * 0.5)
    out = [0.0] * n
    for k in range(5):
        at = int(RATE * (0.02 + k * 0.07 + rng.uniform(0, 0.02)))
        f = rng.uniform(2800, 3600)
        for i in range(n - at):
            t = i / RATE
            out[at + i] += (math.sin(2 * math.pi * f * t) + 0.5 * math.sin(2 * math.pi * f * 1.5 * t)) * \
                math.exp(-t / 0.04) * 0.5
    return out


def sword(rng):
    """Steel on steel."""
    n = int(RATE * 0.6)
    body = noise(rng, n)
    return [(body[i] * 0.4 * env(i / RATE, 0.001, 0.02)
             + (math.sin(2 * math.pi * 1900 * i / RATE) + 0.6 * math.sin(2 * math.pi * 2750 * i / RATE))
             * env(i / RATE, 0.001, 0.18) * 0.5) for i in range(n)]


def birds(rng):
    """Birds in the trees, a loop of eight seconds."""
    n = int(RATE * 8.0)
    out = lowpass(noise(rng, n), 0.01)
    out = [s * 0.08 for s in out]  # A little wind in the leaves.
    for _ in range(18):
        at = rng.randrange(0, n - RATE)
        f0 = rng.uniform(2200, 3800)
        notes = rng.randrange(2, 6)
        for k in range(notes):
            length = int(RATE * rng.uniform(0.05, 0.12))
            start = at + k * int(length * 1.4)
            if start + length >= n:
                break
            glide = rng.uniform(-900, 900)
            phase = 0.0
            for i in range(length):
                t = i / length
                phase += 2 * math.pi * (f0 + glide * t) / RATE
                out[start + i] += math.sin(phase) * math.sin(math.pi * t) * 0.35
    return out


def wind(rng):
    """Winter wind, a loop of six seconds."""
    n = int(RATE * 6.0)
    base = lowpass(noise(rng, n), 0.02)
    out = []
    for i in range(n):
        t = i / n
        gust = 0.6 + 0.4 * math.sin(2 * math.pi * t) * math.sin(2 * math.pi * 3 * t + 1.0)
        out.append(base[i] * gust)
    return out


def rain(rng):
    """Steady rain, a loop of six seconds: a hiss, and drops on leaves and roofs (phase 97)."""
    n = int(RATE * 6.0)
    # The hiss: noise with its lows taken out, so it does not rumble.
    white = noise(rng, n)
    low = lowpass(white, 0.08)
    hiss = lowpass([w - l for w, l in zip(white, low)], 0.55)
    out = [h * 0.5 for h in hiss]
    # Some three hundred drops a second, each a tick of a few milliseconds.
    for _ in range(1800):
        start = rng.randrange(n)
        length = rng.randrange(40, 160)
        loud = rng.uniform(0.15, 0.6)
        tone = rng.uniform(900.0, 3200.0)
        for i in range(length):
            t = i / RATE
            out[(start + i) % n] += math.sin(2 * math.pi * tone * t) * math.exp(-t * 900.0) * loud
    # The ends meet: the last tenth of a second fades into the first.
    blend = int(RATE * 0.1)
    for i in range(blend):
        k = i / blend
        out[i] = out[i] * k + out[n - blend + i] * (1 - k)
    return out[:n - blend]


def main():
    folder = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "data/mods/core/sounds")
    os.makedirs(folder, exist_ok=True)
    for name, make in (("chop", chop), ("hammer", hammer), ("bell", bell), ("fire", fire), ("click", click),
                       ("notify", notify), ("coins", coins), ("sword", sword), ("birds", birds), ("wind", wind),
                       ("rain", rain)):
        write(folder, name, make(random.Random(name)))
    print("SalvaCiudad sounds written to", folder)


main()
