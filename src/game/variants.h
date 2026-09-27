// Which of a thing's looks the view shows (phase 31). Presentation only:
// the choice comes from a stable number of the thing, such as its place on
// the map, so every computer and every loaded game shows the same, and it
// never enters the simulation.
#pragma once

#include <cstddef>
#include <cstdint>
#include <vector>

#include "render/scene_renderer.h"

namespace sc {

// A number for a place on the map (cells or fixed-point raw values).
[[nodiscard]] std::uint32_t place_key(std::int32_t x, std::int32_t z);

// One of `count` variants (0 when there are none or one).
[[nodiscard]] std::size_t pick_variant(std::uint32_t key, std::size_t count);

// The building palettes: every roof with every wall and shutter color.
[[nodiscard]] std::vector<render::BuildingPalette> make_building_palettes();

// The building palette for `key`, as Instance::palette (1..count; 0 if none).
[[nodiscard]] std::uint32_t pick_building_palette(std::uint32_t key, std::size_t count);

}  // namespace sc
