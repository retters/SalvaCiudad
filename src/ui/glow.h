// Soft glows for display text such as the logo. Copies of the text drawn at
// offsets leave visible rings and ghost letters, so the glow is instead an
// alpha mask blurred on the CPU (three box blurs, a close match of a Gaussian)
// and composed into one RGBA image that the renderer draws at 1:1.
#pragma once

#include <cstdint>
#include <vector>

#include "ui/draw_list.h"

namespace sc::ui {

// Coverage in [0, 1], row by row. Pixels outside count as 0.
struct AlphaMask {
    int w = 0;
    int h = 0;
    std::vector<float> a;

    void resize(int width, int height);
    [[nodiscard]] float at(int x, int y) const { return a[static_cast<std::size_t>(y) * static_cast<std::size_t>(w) + static_cast<std::size_t>(x)]; }
    float& at(int x, int y) { return a[static_cast<std::size_t>(y) * static_cast<std::size_t>(w) + static_cast<std::size_t>(x)]; }
    // Takes the larger coverage, as overlapping glyphs do.
    void stamp_max(int x, int y, float coverage);
};

// Blurs in place with a Gaussian of `sigma` pixels (no-op below 0.3).
void gaussian_blur(AlphaMask& mask, float sigma);

// Premultiplied RGBA in floats, composed with "over" and turned into straight
// 8-bit RGBA at the end, with a little noise so faint tails do not band.
class GlowCanvas {
public:
    GlowCanvas(int width, int height);

    [[nodiscard]] int width() const { return w_; }
    [[nodiscard]] int height() const { return h_; }

    // Lays `color` over the canvas with opacity `mask * opacity` (same size as the canvas).
    void over(const AlphaMask& mask, Color color, float opacity);
    // A horizontal line one or more pixels thick whose opacity follows sin(pi t) along it.
    void faded_line(int x, int y, int length, int thickness, Color color);

    [[nodiscard]] std::vector<std::uint8_t> to_rgba8() const;

private:
    int w_;
    int h_;
    std::vector<float> px_;  // r, g, b, a premultiplied.
};

}  // namespace sc::ui
