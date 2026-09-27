// The minimap (phase 24): the whole map seen from above as a small image,
// north up, and where north is on the screen for the compass.
#pragma once

#include <array>
#include <cstdint>
#include <vector>

#include "sim/map.h"

namespace sc::minimap {

// Texels per side of the minimap image, whatever the map's size.
inline constexpr int kImageSize = 256;
// The image's id in the interface renderer.
inline constexpr std::uint32_t kImageId = 1;

// The map from above, north (-z) up and east (+x) right: ground colors,
// darker forests, shading from the relief, and water darker where deep.
// RGBA, kImageSize x kImageSize.
[[nodiscard]] std::vector<std::uint8_t> render(const sim::MapData& map);

// Where north lies on the screen for a camera turned `yaw` radians (0
// looks north; turning right is positive): a unit vector, x to the right
// and y down the screen.
[[nodiscard]] std::array<float, 2> north_on_screen(float yaw);

}  // namespace sc::minimap
