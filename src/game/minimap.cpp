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

void apply_fog(std::vector<std::uint8_t>& rgba, std::int32_t map_size, const FogView& fog) {
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
                px[0] = 14;
                px[1] = 15;
                px[2] = 20;
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

std::array<float, 2> north_on_screen(float yaw) {
    // The camera's right is (cos, sin) and its forward (sin, -cos) on the
    // ground (x, z); north is (0, -1). Up the screen is forward.
    return {-std::sin(yaw), -std::cos(yaw)};
}

}  // namespace sc::minimap
