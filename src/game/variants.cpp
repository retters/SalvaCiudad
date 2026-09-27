#include "game/variants.h"

#include <cmath>

namespace sc {

namespace {

std::uint32_t mix(std::uint32_t h) {
    h ^= h >> 16;
    h *= 0x7FEB352Du;
    h ^= h >> 15;
    h *= 0x846CA68Bu;
    h ^= h >> 16;
    return h;
}

// sRGB 0xRRGGBB to linear, as the shaders light in linear space.
math::Vec3 linear_rgb(std::uint32_t hex) {
    const auto lin = [](std::uint32_t c) {
        const float v = static_cast<float>(c) / 255.0f;
        return v <= 0.04045f ? v / 12.92f : std::pow((v + 0.055f) / 1.055f, 2.4f);
    };
    return {lin((hex >> 16) & 255u), lin((hex >> 8) & 255u), lin(hex & 255u)};
}

}  // namespace

std::uint32_t place_key(std::int32_t x, std::int32_t z) {
    return mix(static_cast<std::uint32_t>(x) * 0x9E3779B1u ^ mix(static_cast<std::uint32_t>(z) + 0x632BE5ABu));
}

std::size_t pick_variant(std::uint32_t key, std::size_t count) {
    return count <= 1 ? 0 : mix(key ^ 0xA511E9B3u) % count;
}

std::vector<render::BuildingPalette> make_building_palettes() {
    // Roof and its darker rows: red tiles, thatch, slate, shingles, old tiles.
    constexpr std::uint32_t kRoofs[][2] = {
        {0x9A4A2E, 0x7E3A24}, {0xC9A55A, 0xA8863F}, {0x5A6470, 0x46505A}, {0x7A5A3E, 0x5E432C}, {0x8A3F32, 0x6E3026},
    };
    // Walls: plaster, warm, ochre, rose, lime white, grey.
    constexpr std::uint32_t kWalls[] = {0xE6DCC4, 0xE8CFA6, 0xD9B77A, 0xE3C3B5, 0xF0ECE2, 0xD5D2CB};
    // Shutters: green, blue, red, brown, teal.
    constexpr std::uint32_t kShutters[] = {0x4F6B4A, 0x3F5E8C, 0x8A3A30, 0x6B4A2E, 0x3E6E6A};
    std::vector<render::BuildingPalette> out;
    for (const auto& roof : kRoofs) {
        for (const std::uint32_t wall : kWalls) {
            for (const std::uint32_t shutter : kShutters) {
                render::BuildingPalette p;
                p.colors[0] = linear_rgb(roof[0]);
                p.colors[1] = linear_rgb(roof[1]);
                p.colors[2] = linear_rgb(wall);
                p.colors[3] = linear_rgb(shutter);
                out.push_back(p);
            }
        }
    }
    return out;
}

std::uint32_t pick_building_palette(std::uint32_t key, std::size_t count) {
    return count == 0 ? 0u : static_cast<std::uint32_t>(mix(key ^ 0x3C6EF372u) % count) + 1u;
}

}  // namespace sc
