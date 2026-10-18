// The minimap (phase 24): the whole map seen from above as a small image,
// north up, and where north is on the screen for the compass.
#pragma once

#include <array>
#include <cstdint>
#include <vector>

#include "game/fog_view.h"
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

// Covers `rgba` (from render()) with the fog of war: black where nothing
// was explored and dim where it is out of sight (dynamic fog).
// `silhouette` (phase 74, while the town is not founded): what was not
// explored shows land and water in two dark tones, nothing else.
void apply_fog(std::vector<std::uint8_t>& rgba, std::int32_t map_size, const FogView& fog, bool silhouette = false);

// Phase 121: what the HUD draws over the image (the roads, the buildings,
// the sites and what the camera sees), now into the image itself, in its
// texels (a map meter is kImageSize / map size texels). Colors are RGBA
// with straight alpha; they are blended over what is there.
struct Rgba {
    std::uint8_t r = 0;
    std::uint8_t g = 0;
    std::uint8_t b = 0;
    std::uint8_t a = 255;
};
void fill(std::vector<std::uint8_t>& rgba, float x, float y, float w, float h, Rgba color);
// A line `thickness` texels wide.
void line(std::vector<std::uint8_t>& rgba, float x0, float y0, float x1, float y1, float thickness, Rgba color);

// Where north lies on the screen for a camera turned `yaw` radians (0
// looks north; turning right is positive): a unit vector, x to the right
// and y down the screen.
[[nodiscard]] std::array<float, 2> north_on_screen(float yaw);

}  // namespace sc::minimap
