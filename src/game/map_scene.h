// Shows a generated map: turns the simulation's map data into ground
// colors, terrain and model instances for the renderer. Presentation only;
// nothing here feeds back into the simulation.
#pragma once

#include <array>
#include <cstddef>
#include <filesystem>
#include <string>
#include <vector>

#include <map>
#include <optional>

#include "mods/mod_library.h"
#include "render/scene_renderer.h"
#include "sim/content.h"
#include "sim/map.h"

namespace sc {

// Instances are grouped by "visual slot": one per tree species and size,
// then one per other feature type.
[[nodiscard]] std::size_t tree_slot(std::size_t species, sim::TreeSize size);
[[nodiscard]] std::size_t tree_slot_count(const sim::Content& content);
[[nodiscard]] std::size_t visual_slot_count(const sim::Content& content);
[[nodiscard]] std::size_t visual_slot(const sim::Content& content, const sim::MapFeature& f);

// Everything the renderer needs for a map, built off the main thread. For
// trees, an instance's scale is the tree's height in meters; MapScene turns
// it into the model's scale.
struct MapVisuals {
    render::TerrainData terrain;
    std::vector<std::vector<render::Instance>> features;
    [[nodiscard]] std::size_t feature_count() const;
};

// Path of a tree model inside its mod, for example
// "models/props/tree_oak_large.glb".
[[nodiscard]] std::string tree_model_file(const sim::SpeciesDef& species, sim::TreeSize size);

// Largest ground color texture, texels per side; bigger maps share texels.
inline constexpr std::int32_t kMaxGroundColorSize = 2048;

[[nodiscard]] MapVisuals build_map_visuals(const sim::MapData& map, const sim::Content& content);
// Only the feature instances, by visual slot.
[[nodiscard]] std::vector<std::vector<render::Instance>> build_feature_instances(const sim::MapData& map,
                                                                                 const sim::Content& content);
// One feature's instance (for trees, scale is the height in meters).
[[nodiscard]] render::Instance feature_instance(const sim::MapData& map, const sim::MapFeature& f);

// Ground color of a cell, sRGB (presentation only).
struct Rgb8 {
    std::uint8_t r = 0, g = 0, b = 0;
};
[[nodiscard]] Rgb8 ground_color(sim::Terrain terrain, std::uint8_t fertility, std::uint32_t cell_hash);
// How much decorative grass grows on a cell, 0..255.
// `biome_grass` is the biome's amount of grass (0..255).
[[nodiscard]] std::uint8_t grass_density(sim::Terrain terrain, std::uint8_t fertility, std::uint8_t biome_grass);

// Height in meters at a point, for the camera: the ground, or the water
// surface where there is water. Outside the map it takes the nearest edge.
[[nodiscard]] float map_surface_height(const sim::MapData& map, float x, float z);

// Where a ray from the camera meets the map's surface, if it does within
// `max_distance` meters.
[[nodiscard]] std::optional<math::Vec3> ground_hit(const sim::MapData& map, math::Vec3 origin, math::Vec3 dir,
                                                   float max_distance = 4000.0f);

class MapScene {
public:
    // Loads the models of the content's trees and features from their mods.
    // Files already loaded are reused, so switching mods only loads new
    // ones. Missing models are skipped (and logged); returns false only if
    // none loaded.
    bool load_models(render::SceneRenderer& renderer, const mods::BuildResult& pack);

    // Puts a map in the renderer, or takes it out.
    bool show(render::SceneRenderer& renderer, const MapVisuals& visuals);
    void hide(render::SceneRenderer& renderer);
    // A ring of houses around `center` (a start position), to see the map
    // next to buildings until real towns exist. Cleared by hide().
    void show_sample_village(render::SceneRenderer& renderer, const sim::MapData& map, math::Vec3 center);

    // The clouds over a shown map.
    void show_sky(render::SceneRenderer& renderer, const sim::MapData& map);

    // Developer tools: redraw the features after the map's list changed,
    // and edit the houses.
    void refresh_features(render::SceneRenderer& renderer, const sim::MapData& map, const sim::Content& content);
    [[nodiscard]] const std::vector<render::Instance>& houses() const { return houses_; }
    void add_house(render::SceneRenderer& renderer, const render::Instance& house);
    void remove_house(render::SceneRenderer& renderer, std::size_t index);

    [[nodiscard]] bool shown() const { return shown_; }

    // How a natural feature looks during a game.
    enum class FeatureLook : std::uint8_t { Normal, Empty, Gone };
    // Changes one feature (by its index in the map's list) without
    // rebuilding the others: a felled tree, a picked bush.
    void set_feature_look(render::SceneRenderer& renderer, const sim::MapData& map, const sim::Content& content,
                          std::size_t feature, FeatureLook look);
    // Takes out the sample village (a real game has its own town).
    void hide_sample_village(render::SceneRenderer& renderer);

private:
    static constexpr std::uint32_t kNoModel = ~0u;
    struct Slot {
        render::ModelId model = kNoModel;
        float height = 1.0f;  // Model height in meters (trees).
    };
    std::vector<Slot> slots_;
    std::size_t tree_slots_ = 0;
    std::vector<render::ModelId> used_models_;
    std::map<std::string, Slot> files_;  // Loaded model files by path.
    Slot load_file(render::SceneRenderer& renderer, const std::filesystem::path& file, render::ModelClass model_class);
    std::vector<render::Instance> scratch_;
    // Where each map feature went: its model and its index in that model's
    // instance list. Built on first use after the features were shown.
    struct FeatureRef {
        render::ModelId model = kNoModel;
        std::uint32_t index = 0;
    };
    std::vector<FeatureRef> feature_refs_;
    std::vector<std::size_t> slot_counts_;  // Features per visual slot, as last shown.
    void build_feature_refs(const sim::MapData& map, const sim::Content& content);
    std::vector<render::Instance> houses_;

    void apply_features(render::SceneRenderer& renderer, const std::vector<std::vector<render::Instance>>& features);
    render::ModelId house_ = kNoModel;
    render::ModelId cloud_ = kNoModel;
    void show_clouds(render::SceneRenderer& renderer, const sim::MapData& map);
    bool models_loaded_ = false;
    bool shown_ = false;
};

}  // namespace sc
