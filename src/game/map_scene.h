// Shows a generated map: turns the simulation's map data into ground
// colors, terrain and model instances for the renderer. Presentation only;
// nothing here feeds back into the simulation.
#pragma once

#include <array>
#include <cstddef>
#include <filesystem>
#include <string>
#include <vector>

#include "render/scene_renderer.h"
#include "sim/map.h"

namespace sc {

// Instances are grouped by "visual slot": one per tree species and size,
// then one per other feature type.
inline constexpr std::size_t kTreeSlots = sim::kSpeciesCount * sim::kTreeSizes;
inline constexpr std::size_t kVisualSlots = kTreeSlots + static_cast<std::size_t>(sim::FeatureType::Count);
[[nodiscard]] std::size_t visual_slot(const sim::MapFeature& f);
[[nodiscard]] std::size_t tree_slot(sim::Species species, sim::TreeSize size);

// Everything the renderer needs for a map, built off the main thread. For
// trees, an instance's scale is the tree's height in meters; MapScene turns
// it into the model's scale.
struct MapVisuals {
    render::TerrainData terrain;
    std::vector<std::vector<render::Instance>> features = std::vector<std::vector<render::Instance>>(kVisualSlots);
    [[nodiscard]] std::size_t feature_count() const;
};

// File name of a tree model, for example "tree_oak_large.glb".
[[nodiscard]] std::string tree_model_file(sim::Species species, sim::TreeSize size);

// Largest ground color texture, texels per side; bigger maps share texels.
inline constexpr std::int32_t kMaxGroundColorSize = 2048;

[[nodiscard]] MapVisuals build_map_visuals(const sim::MapData& map);
// Only the feature instances, by visual slot.
[[nodiscard]] std::vector<std::vector<render::Instance>> build_feature_instances(const sim::MapData& map);

// Ground color of a cell, sRGB (presentation only).
struct Rgb8 {
    std::uint8_t r = 0, g = 0, b = 0;
};
[[nodiscard]] Rgb8 ground_color(sim::Terrain terrain, std::uint8_t fertility, std::uint32_t cell_hash);
// How much decorative grass grows on a cell, 0..255.
[[nodiscard]] std::uint8_t grass_density(sim::Terrain terrain, std::uint8_t fertility, sim::Biome biome);

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

    // Developer tools: redraw the features after the map's list changed,
    // and edit the houses.
    void refresh_features(render::SceneRenderer& renderer, const sim::MapData& map);
    [[nodiscard]] const std::vector<render::Instance>& houses() const { return houses_; }
    void add_house(render::SceneRenderer& renderer, const render::Instance& house);
    void remove_house(render::SceneRenderer& renderer, std::size_t index);

    [[nodiscard]] bool shown() const { return shown_; }

private:
    static constexpr std::uint32_t kNoModel = ~0u;
    struct Slot {
        render::ModelId model = kNoModel;
        float height = 1.0f;  // Model height in meters (trees).
    };
    std::vector<Slot> slots_ = std::vector<Slot>(kVisualSlots);
    std::vector<render::ModelId> used_models_;
    std::vector<render::Instance> scratch_;
    std::vector<render::Instance> houses_;

    void apply_features(render::SceneRenderer& renderer, const std::vector<std::vector<render::Instance>>& features);
    render::ModelId house_ = kNoModel;
    bool models_loaded_ = false;
    bool shown_ = false;
};

}  // namespace sc
