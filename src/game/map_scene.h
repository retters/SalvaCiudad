// Shows a generated map: turns the simulation's map data into ground
// colors, terrain and model instances for the renderer. Presentation only;
// nothing here feeds back into the simulation.
#pragma once

#include <array>
#include <cstddef>
#include <filesystem>
#include <vector>

#include "render/scene_renderer.h"
#include "sim/map.h"

namespace sc {

// Everything the renderer needs for a map, built off the main thread.
struct MapVisuals {
    render::TerrainData terrain;
    std::array<std::vector<render::Instance>, static_cast<std::size_t>(sim::FeatureType::Count)> features;
    [[nodiscard]] std::size_t feature_count() const;
};

// Largest ground color texture, texels per side; bigger maps share texels.
inline constexpr std::int32_t kMaxGroundColorSize = 2048;

[[nodiscard]] MapVisuals build_map_visuals(const sim::MapData& map);

// Ground color of a cell, sRGB (presentation only).
struct Rgb8 {
    std::uint8_t r = 0, g = 0, b = 0;
};
[[nodiscard]] Rgb8 ground_color(sim::Terrain terrain, std::uint8_t fertility, std::uint32_t cell_hash);

// Height in meters at a point, for the camera: the ground, or the water
// surface where there is water. Outside the map it takes the nearest edge.
[[nodiscard]] float map_surface_height(const sim::MapData& map, float x, float z);

class MapScene {
public:
    // Loads the feature models from data/models/props. Models that fail are
    // skipped (and logged); returns false only if none loaded.
    bool load_models(render::SceneRenderer& renderer, const std::filesystem::path& props_dir);

    // Puts a map in the renderer, or takes it out.
    bool show(render::SceneRenderer& renderer, const MapVisuals& visuals);
    void hide(render::SceneRenderer& renderer);
    // A ring of houses around `center` (a start position), to see the map
    // next to buildings until real towns exist. Cleared by hide().
    void show_sample_village(render::SceneRenderer& renderer, const sim::MapData& map, math::Vec3 center);

    [[nodiscard]] bool shown() const { return shown_; }

private:
    static constexpr std::uint32_t kNoModel = ~0u;
    std::array<render::ModelId, static_cast<std::size_t>(sim::FeatureType::Count)> models_{};
    render::ModelId house_ = kNoModel;
    bool models_loaded_ = false;
    bool shown_ = false;
};

}  // namespace sc
