#include "ui/glow.h"

#include <algorithm>
#include <array>
#include <cmath>

namespace sc::ui {

namespace {

// Widths of three box blurs whose sum matches a Gaussian of `sigma`
// (Kutskir, "Fastest Gaussian blur"). All odd, so each box is centered.
std::array<int, 3> box_widths(float sigma) {
    constexpr int n = 3;
    const float ideal = std::sqrt(12.0f * sigma * sigma / n + 1.0f);
    int lower = static_cast<int>(std::floor(ideal));
    if (lower % 2 == 0) {
        --lower;
    }
    const int upper = lower + 2;
    const float m_ideal =
        (12.0f * sigma * sigma - static_cast<float>(n * lower * lower + 4 * n * lower + 3 * n)) /
        static_cast<float>(-4 * lower - 4);
    const int m = static_cast<int>(std::lround(m_ideal));
    std::array<int, 3> widths{};
    for (int i = 0; i < n; ++i) {
        widths[static_cast<std::size_t>(i)] = i < m ? lower : upper;
    }
    return widths;
}

// One box blur of `count` samples `stride` apart, reading zeros past both ends.
void box_line(float* data, int count, int stride, int radius, std::vector<double>& prefix) {
    prefix.assign(static_cast<std::size_t>(count) + 1, 0.0);
    for (int i = 0; i < count; ++i) {
        prefix[static_cast<std::size_t>(i) + 1] = prefix[static_cast<std::size_t>(i)] + data[i * stride];
    }
    const double inv = 1.0 / static_cast<double>(2 * radius + 1);
    for (int i = 0; i < count; ++i) {
        const int lo = std::max(0, i - radius);
        const int hi = std::min(count, i + radius + 1);
        data[i * stride] =
            static_cast<float>((prefix[static_cast<std::size_t>(hi)] - prefix[static_cast<std::size_t>(lo)]) * inv);
    }
}

// Cheap integer hash for the dithering noise: fixed, so the image is the same every time.
float noise(int x, int y) {
    std::uint32_t h = static_cast<std::uint32_t>(x) * 0x8DA6B343u ^ static_cast<std::uint32_t>(y) * 0xD8163841u;
    h ^= h >> 13;
    h *= 0x85EBCA6Bu;
    h ^= h >> 16;
    return static_cast<float>(h & 0xFFFFu) / 65535.0f - 0.5f;
}

std::uint8_t to_byte(float v) {
    return static_cast<std::uint8_t>(std::clamp(std::lround(v), 0L, 255L));
}

}  // namespace

void AlphaMask::resize(int width, int height) {
    w = std::max(0, width);
    h = std::max(0, height);
    a.assign(static_cast<std::size_t>(w) * static_cast<std::size_t>(h), 0.0f);
}

void AlphaMask::stamp_max(int x, int y, float coverage) {
    if (x < 0 || y < 0 || x >= w || y >= h) {
        return;
    }
    float& p = at(x, y);
    p = std::max(p, coverage);
}

void gaussian_blur(AlphaMask& mask, float sigma) {
    if (sigma < 0.3f || mask.w == 0 || mask.h == 0) {
        return;
    }
    std::vector<double> prefix;
    for (const int width : box_widths(sigma)) {
        const int radius = (width - 1) / 2;
        if (radius < 1) {
            continue;
        }
        for (int y = 0; y < mask.h; ++y) {
            box_line(&mask.at(0, y), mask.w, 1, radius, prefix);
        }
        for (int x = 0; x < mask.w; ++x) {
            box_line(&mask.at(x, 0), mask.h, mask.w, radius, prefix);
        }
    }
}

GlowCanvas::GlowCanvas(int width, int height)
    : w_(std::max(0, width)), h_(std::max(0, height)), px_(static_cast<std::size_t>(w_) * static_cast<std::size_t>(h_) * 4, 0.0f) {}

void GlowCanvas::over(const AlphaMask& mask, Color color, float opacity) {
    if (mask.w != w_ || mask.h != h_) {
        return;
    }
    const float r = static_cast<float>(color.r) / 255.0f;
    const float g = static_cast<float>(color.g) / 255.0f;
    const float b = static_cast<float>(color.b) / 255.0f;
    const float base = opacity * static_cast<float>(color.a) / 255.0f;
    for (std::size_t i = 0; i < mask.a.size(); ++i) {
        const float a = std::clamp(mask.a[i] * base, 0.0f, 1.0f);
        float* p = &px_[i * 4];
        const float keep = 1.0f - a;
        p[0] = r * a + p[0] * keep;
        p[1] = g * a + p[1] * keep;
        p[2] = b * a + p[2] * keep;
        p[3] = a + p[3] * keep;
    }
}

void GlowCanvas::faded_line(int x, int y, int length, int thickness, Color color) {
    if (length < 1 || thickness < 1) {
        return;
    }
    AlphaMask line;
    line.resize(w_, h_);
    for (int i = 0; i < length; ++i) {
        const float t = (static_cast<float>(i) + 0.5f) / static_cast<float>(length);
        const float fade = std::sin(t * 3.14159265f);
        for (int k = 0; k < thickness; ++k) {
            line.stamp_max(x + i, y + k, fade);
        }
    }
    over(line, color, 1.0f);
}

std::vector<std::uint8_t> GlowCanvas::to_rgba8() const {
    std::vector<std::uint8_t> out(static_cast<std::size_t>(w_) * static_cast<std::size_t>(h_) * 4, 0);
    for (int y = 0; y < h_; ++y) {
        for (int x = 0; x < w_; ++x) {
            const std::size_t i = (static_cast<std::size_t>(y) * static_cast<std::size_t>(w_) + static_cast<std::size_t>(x)) * 4;
            const float a = px_[i + 3];
            const float inv = a > 1e-5f ? 1.0f / a : 0.0f;
            for (int c = 0; c < 3; ++c) {
                out[i + static_cast<std::size_t>(c)] = to_byte(std::min(1.0f, px_[i + static_cast<std::size_t>(c)] * inv) * 255.0f);
            }
            out[i + 3] = a > 0.0f ? to_byte(a * 255.0f + noise(x, y)) : 0;
        }
    }
    return out;
}

}  // namespace sc::ui
