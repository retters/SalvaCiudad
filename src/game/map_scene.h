// Shows a generated map: turns the simulation's map data into ground
// colors, terrain and model instances for the renderer. Presentation only;
// nothing here feeds back into the simulation.
#pragma once

#include <algorithm>
#include <array>
#include <cstddef>
#include <filesystem>
#include <string>
#include <vector>

#include <map>
#include <optional>

#include "mods/mod_library.h"
#include "render/scene_renderer.h"
#include "sim/climate.h"
#include "sim/content.h"
#include "sim/map.h"

namespace sc {

// The point of the year the trees are shown at (phase 51): the season and
// how far its change has gone, from 0 (no tree has changed yet) to
// kTurnSteps (all have). Each tree changes at its own step.
inline constexpr int kTurnSteps = 8;
// The change takes this much of the season, in thousandths.
inline constexpr std::uint32_t kTurnProgress = 200;
struct TreeCalendar {
    sim::Season season = sim::Season::Summer;
    int turn = kTurnSteps;
    bool operator==(const TreeCalendar&) const = default;
};
// From a season and its progress (0..999, sim::Calendar).
[[nodiscard]] TreeCalendar tree_calendar(sim::Season season, std::uint32_t season_progress);
// The step at which a tree changes, from its place: 0 changes first.
[[nodiscard]] int tree_turn(const sim::MapFeature& f);
// The state a tree shows: the season's, or still the one before if its
// turn has not come.
[[nodiscard]] sim::TreeState tree_state(const sim::MapFeature& f, TreeCalendar when);

// The look (render::Instance::look) a tree takes in a state: the state's
// number, or 0 (Bloom's) for a species without models for it.
[[nodiscard]] std::uint8_t tree_look(const sim::Content& content, const sim::MapFeature& f, TreeCalendar when);

// Instances are grouped by "visual slot". Each tree species has
// kSpeciesSlots: one per size, or, for a species with models by state
// (phase 51), one per variant: a tree stays in its slot all year and the
// state only changes its look (phase 52). Then one per variant of every
// other feature type.
inline constexpr std::size_t kSpeciesSlots = sim::kMaxModelVariants;
[[nodiscard]] std::size_t tree_slot(std::size_t species, sim::TreeSize size);
[[nodiscard]] std::size_t tree_variant_slot(std::size_t species, std::size_t variant);
[[nodiscard]] std::size_t tree_slot_count(const sim::Content& content);
[[nodiscard]] std::size_t visual_slot_count(const sim::Content& content);
[[nodiscard]] std::size_t visual_slot(const sim::Content& content, const sim::MapFeature& f);

// A tree with models by state is its model scaled to the tree's height,
// but never under half the model's height or over one and a half.
inline constexpr float kMinTreeScale = 0.5f;
inline constexpr float kMaxTreeScale = 1.5f;
// The slot of a variant of a natural feature other than trees (phase 31).
[[nodiscard]] std::size_t feature_slot(const sim::Content& content, sim::FeatureType type, std::size_t variant);

// Everything the renderer needs for a map, built off the main thread. For
// trees, an instance's scale is the tree's height in meters; MapScene turns
// it into the model's scale.
struct MapVisuals {
    render::TerrainData terrain;
    std::vector<std::vector<render::Instance>> features;
    [[nodiscard]] std::size_t feature_count() const;
};

// Path of a tree model inside its mod, for example
// "models/props/tree_oak_large.glb"; for a species with models by state,
// the first of the state.
[[nodiscard]] std::string tree_model_file(const sim::SpeciesDef& species, sim::TreeSize size,
                                          sim::TreeState state = sim::TreeState::Bloom);

// Largest ground color texture, texels per side; bigger maps share texels.
inline constexpr std::int32_t kMaxGroundColorSize = 2048;

[[nodiscard]] MapVisuals build_map_visuals(const sim::MapData& map, const sim::Content& content);
// Only the feature instances, by visual slot.
[[nodiscard]] std::vector<std::vector<render::Instance>> build_feature_instances(
    const sim::MapData& map, const sim::Content& content, TreeCalendar when = {}, bool snowy = false);
// One feature's instance (for trees, scale is the height in meters; the
// look is left at 0, see tree_look), colored for the season: snow whitens everything; bushes, and trees
// without models by state, turn in autumn and fade in winter unless they
// are evergreen (trees with models by state change model instead).
[[nodiscard]] render::Instance feature_instance(const sim::MapData& map, const sim::MapFeature& f,
                                                const sim::Content* content = nullptr,
                                                sim::Season season = sim::Season::Summer, bool snowy = false);

// The color a tree or bush takes in a season: `shade` is its own
// brightness (0.9 to 1.1) and `pick` chooses its autumn color.
[[nodiscard]] math::Vec3 season_tint(float shade, bool tree, bool evergreen, std::uint32_t pick, sim::Season season,
                                     bool snowy);

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
    // The clouds drift with the wind (phase 18); `dt` in seconds.
    void update_sky(render::SceneRenderer& renderer, float dt);

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
    // Colors the trees and bushes for the season; felled trees and picked
    // bushes stay as they are.
    void set_season(render::SceneRenderer& renderer, const sim::MapData& map, const sim::Content& content,
                    TreeCalendar when, bool snowy);

private:
    static constexpr std::uint32_t kNoModel = ~0u;
    struct Slot {
        render::ModelId model = kNoModel;
        float height = 1.0f;  // Model height in meters (trees).
        bool limited = false;  // A tree by state: its scale stays within limits.
        // The model's scale for a tree `meters` high.
        [[nodiscard]] float tree_scale(float meters) const {
            const float s = meters / height;
            return limited && s > 0.0f ? std::clamp(s, kMinTreeScale, kMaxTreeScale) : s;
        }
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
    std::vector<FeatureLook> looks_;  // By feature, as last set.
    TreeCalendar when_;
    bool snowy_ = false;
    std::vector<std::size_t> slot_counts_;  // Features per visual slot, as last shown.
    void build_feature_refs(const sim::MapData& map, const sim::Content& content);
    std::vector<render::Instance> houses_;

    void apply_features(render::SceneRenderer& renderer, const std::vector<std::vector<render::Instance>>& features);
    render::ModelId house_ = kNoModel;
    std::vector<render::ModelId> cloud_models_;         // The cloud shapes (phase 31).
    std::vector<std::vector<render::Instance>> clouds_;  // By shape.
    float cloud_min_ = 0.0f;  // The x range the clouds wrap around.
    float cloud_max_ = 0.0f;
    void show_clouds(render::SceneRenderer& renderer, const sim::MapData& map);
    bool models_loaded_ = false;
    bool shown_ = false;
};

}  // namespace sc
