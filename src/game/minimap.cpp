#include "game/minimap.h"

#include <algorithm>
#include <cmath>

#include "game/map_scene.h"

namespace sc::minimap {

namespace {

// Cells sampled per texel side: enough to see small lakes on a colossal
// map without reading all of its 268 million cells.
constexpr int kSamples = 4;

}  // namespace

std::vector<std::uint8_t> render(const sim::MapData& map) {
    std::vector<std::uint8_t> out(static_cast<std::size_t>(kImageSize) * kImageSize * 4, 0);
    const std::int32_t n = map.size;
    if (n <= 0 || map.terrain.size() != static_cast<std::size_t>(n) * static_cast<std::size_t>(n)) {
        return out;
    }
    const double cells_per_texel = static_cast<double>(n) / kImageSize;
    // Relief shading: the slope toward the light, from the north-west.
    const auto step = std::max<std::int32_t>(1, static_cast<std::int32_t>(cells_per_texel));
    for (int ty = 0; ty < kImageSize; ++ty) {
        for (int tx = 0; tx < kImageSize; ++tx) {
            float r = 0.0f;
            float g = 0.0f;
            float b = 0.0f;
            for (int sy = 0; sy < kSamples; ++sy) {
                for (int sx = 0; sx < kSamples; ++sx) {
                    const auto cx = std::min<std::int32_t>(
                        n - 1, static_cast<std::int32_t>((tx + (sx + 0.5) / kSamples) * cells_per_texel));
                    const auto cz = std::min<std::int32_t>(
                        n - 1, static_cast<std::int32_t>((ty + (sy + 0.5) / kSamples) * cells_per_texel));
                    const std::size_t cell = static_cast<std::size_t>(cz) * static_cast<std::size_t>(n) +
                                             static_cast<std::size_t>(cx);
                    const auto terrain = static_cast<sim::Terrain>(map.terrain[cell]);
                    float cr = 0.0f;
                    float cg = 0.0f;
                    float cb = 0.0f;
                    const float ground = static_cast<float>(map.height_cm(cx, cz));
                    if (map.water[cell] != 0) {
                        // Light blue in the shallows, deep blue far down.
                        const float depth = std::clamp((static_cast<float>(map.water[cell]) - ground) / 400.0f, 0.0f, 1.0f);
                        cr = 110.0f + (38.0f - 110.0f) * depth;
                        cg = 178.0f + (92.0f - 178.0f) * depth;
                        cb = 205.0f + (152.0f - 205.0f) * depth;
                    } else {
                        const Rgb8 c = ground_color(terrain, map.fertility[cell], 0x80u);
                        const float shade = terrain == sim::Terrain::ForestFloor ? 0.78f : 1.0f;
                        const float west = static_cast<float>(map.height_cm(cx - step, cz));
                        const float north = static_cast<float>(map.height_cm(cx, cz - step));
                        // 1 m higher than the neighbors toward the light over a
                        // texel: a little brighter.
                        const float light = std::clamp(1.0f + ((ground - west) + (ground - north)) /
                                                                  static_cast<float>(step) * 0.004f,
                                                       0.7f, 1.3f);
                        cr = c.r * shade * light;
                        cg = c.g * shade * light;
                        cb = c.b * shade * light;
                    }
                    r += cr;
                    g += cg;
                    b += cb;
                }
            }
            constexpr float kCount = kSamples * kSamples;
            std::uint8_t* px = &out[(static_cast<std::size_t>(ty) * kImageSize + static_cast<std::size_t>(tx)) * 4];
            px[0] = static_cast<std::uint8_t>(std::clamp(r / kCount, 0.0f, 255.0f));
            px[1] = static_cast<std::uint8_t>(std::clamp(g / kCount, 0.0f, 255.0f));
            px[2] = static_cast<std::uint8_t>(std::clamp(b / kCount, 0.0f, 255.0f));
            px[3] = 255;
        }
    }
    return out;
}

void apply_fog(std::vector<std::uint8_t>& rgba, std::int32_t map_size, const FogView& fog, bool silhouette) {
    if (fog.mode() == sim::FogMode::None || map_size <= 0 ||
        rgba.size() != static_cast<std::size_t>(kImageSize) * kImageSize * 4) {
        return;
    }
    const float meters = static_cast<float>(map_size) / kImageSize;
    for (int ty = 0; ty < kImageSize; ++ty) {
        for (int tx = 0; tx < kImageSize; ++tx) {
            const float x = (static_cast<float>(tx) + 0.5f) * meters;
            const float z = (static_cast<float>(ty) + 0.5f) * meters;
            std::uint8_t* px = &rgba[(static_cast<std::size_t>(ty) * kImageSize + static_cast<std::size_t>(tx)) * 4];
            if (!fog.explored(x, z)) {
                // Water is the only thing drawn bluer than green.
                const bool water = silhouette && px[2] > px[1];
                const bool land = silhouette && !water;
                px[0] = land ? 46 : water ? 22 : 14;
                px[1] = land ? 48 : water ? 30 : 15;
                px[2] = land ? 50 : water ? 46 : 20;
            } else if (fog.mode() == sim::FogMode::Dynamic && !fog.in_sight(x, z)) {
                // Dim and grey, as on the ground.
                const int luma = (px[0] * 54 + px[1] * 183 + px[2] * 19) >> 8;
                px[0] = static_cast<std::uint8_t>((px[0] + luma * 3) / 4 * 11 / 20);
                px[1] = static_cast<std::uint8_t>((px[1] + luma * 3) / 4 * 11 / 20);
                px[2] = static_cast<std::uint8_t>((px[2] + luma * 3) / 4 * 12 / 20);
            }
        }
    }
}

void fill(std::vector<std::uint8_t>& rgba, float x, float y, float w, float h, Rgba color) {
    if (rgba.size() != static_cast<std::size_t>(kImageSize) * kImageSize * 4 || color.a == 0) {
        return;
    }
    const int x0 = std::clamp(static_cast<int>(std::floor(x)), 0, kImageSize);
    const int y0 = std::clamp(static_cast<int>(std::floor(y)), 0, kImageSize);
    const int x1 = std::clamp(static_cast<int>(std::ceil(x + w)), x0, kImageSize);
    const int y1 = std::clamp(static_cast<int>(std::ceil(y + h)), y0, kImageSize);
    const int a = color.a;
    for (int ty = y0; ty < y1; ++ty) {
        for (int tx = x0; tx < x1; ++tx) {
            std::uint8_t* p = &rgba[(static_cast<std::size_t>(ty) * kImageSize + static_cast<std::size_t>(tx)) * 4];
            p[0] = static_cast<std::uint8_t>((color.r * a + p[0] * (255 - a)) / 255);
            p[1] = static_cast<std::uint8_t>((color.g * a + p[1] * (255 - a)) / 255);
            p[2] = static_cast<std::uint8_t>((color.b * a + p[2] * (255 - a)) / 255);
            p[3] = 255;
        }
    }
}

void line(std::vector<std::uint8_t>& rgba, float x0, float y0, float x1, float y1, float thickness, Rgba color) {
    // Squares stamped along it, half a texel apart.
    const float length = std::hypot(x1 - x0, y1 - y0);
    const int steps = std::clamp(static_cast<int>(length * 2.0f) + 1, 1, kImageSize * 8);
    const float half = thickness * 0.5f;
    std::vector<std::uint8_t> mask(static_cast<std::size_t>(kImageSize) * kImageSize, 0);
    int min_x = kImageSize, min_y = kImageSize, max_x = 0, max_y = 0;
    for (int i = 0; i <= steps; ++i) {
        const float t = static_cast<float>(i) / static_cast<float>(steps);
        const float cx = x0 + (x1 - x0) * t;
        const float cy = y0 + (y1 - y0) * t;
        const int ax = std::clamp(static_cast<int>(std::floor(cx - half + 0.5f)), 0, kImageSize);
        const int ay = std::clamp(static_cast<int>(std::floor(cy - half + 0.5f)), 0, kImageSize);
        const int bx = std::clamp(static_cast<int>(std::floor(cx + half + 0.5f)), ax, kImageSize);
        const int by = std::clamp(static_cast<int>(std::floor(cy + half + 0.5f)), ay, kImageSize);
        for (int ty = ay; ty < std::max(by, ay + 1) && ty < kImageSize; ++ty) {
            for (int tx = ax; tx < std::max(bx, ax + 1) && tx < kImageSize; ++tx) {
                mask[static_cast<std::size_t>(ty) * kImageSize + static_cast<std::size_t>(tx)] = 1;
                min_x = std::min(min_x, tx);
                min_y = std::min(min_y, ty);
                max_x = std::max(max_x, tx);
                max_y = std::max(max_y, ty);
            }
        }
    }
    // Each texel once, so the color does not pile up where squares overlap.
    for (int ty = min_y; ty <= max_y && ty < kImageSize; ++ty) {
        for (int tx = min_x; tx <= max_x && tx < kImageSize; ++tx) {
            if (mask[static_cast<std::size_t>(ty) * kImageSize + static_cast<std::size_t>(tx)] != 0) {
                fill(rgba, static_cast<float>(tx), static_cast<float>(ty), 1.0f, 1.0f, color);
            }
        }
    }
}

std::array<float, 2> north_on_screen(float yaw) {
    // The camera's right is (cos, sin) and its forward (sin, -cos) on the
    // ground (x, z); north is (0, -1). Up the screen is forward.
    return {-std::sin(yaw), -std::cos(yaw)};
}

}  // namespace sc::minimap
