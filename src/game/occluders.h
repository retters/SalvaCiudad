// What is in the camera's way (phase 61): the building or tree the eye is
// inside of and, in third person, those between the eye and the point it
// turns around. They are drawn see-through while they are in the way, with
// a short transition. View only.
#pragma once

#include <cstdint>
#include <optional>
#include <vector>

#include "game/map_scene.h"
#include "game/village_view.h"
#include "math/vec.h"
#include "render/scene_renderer.h"
#include "sim/game.h"

namespace sc {

namespace occlusion {

// Whether the segment a..b crosses the box (lo, hi).
[[nodiscard]] bool segment_hits_box(math::Vec3 a, math::Vec3 b, math::Vec3 lo, math::Vec3 hi);
// Whether point p is inside a tree's crown: a cylinder of `radius` around
// the trunk at (x, z), from `bottom` to `top`.
[[nodiscard]] bool in_crown(math::Vec3 p, float x, float z, float radius, float bottom, float top);
// The crown of a tree `height` meters tall standing on `ground`: its
// radius and where it starts.
struct Crown {
    float radius = 1.0f;
    float bottom = 0.0f;
    float top = 0.0f;
};
[[nodiscard]] Crown crown_of(float height, float ground);
// A transition's level after `dt` seconds: toward `full` while it is in the
// way and back to 0 after, taking `seconds` for the whole change.
[[nodiscard]] float step_level(float level, bool wanted, float dt, float full, float seconds);

}  // namespace occlusion

class Occluders {
public:
    // How see-through something in the way gets, in quarters, and how
    // long the change takes.
    static constexpr std::uint8_t kFade = 3;
    static constexpr float kFadeSeconds = 0.2f;

    // Forgets everything (another map or game).
    void clear();
    // Finds what is in the way of `eye` (and, in third person, between it
    // and `anchor`), moves the transitions on by `dt` seconds and applies
    // them: to the trees right away, and to the buildings through `view`.
    void update(render::SceneRenderer& renderer, const sim::Game& game, VillageView& view, MapScene& scene, math::Vec3 eye,
                std::optional<math::Vec3> anchor, float dt);

    // For tests: how many buildings and trees are faded now.
    [[nodiscard]] std::size_t buildings() const;
    [[nodiscard]] std::size_t trees() const;

private:
    struct Entry {
        bool tree = false;
        std::uint32_t feature = 0;  // Trees.
        sim::EntityId building;     // Buildings.
        float level = 0.0f;         // 0..kFade, moving toward its goal.
        bool wanted = false;
        std::uint8_t applied = 0;
    };
    void build_grid(const sim::MapData& map);
    Entry& entry(bool tree, std::uint32_t feature, sim::EntityId building);

    std::vector<Entry> entries_;
    // The trees by cells of kCell meters, to look around a point.
    static constexpr std::int32_t kCell = 16;
    const sim::MapData* grid_map_ = nullptr;
    std::size_t grid_features_ = 0;
    std::int32_t grid_side_ = 0;
    std::vector<std::uint32_t> grid_start_;  // Per cell, into grid_items_.
    std::vector<std::uint32_t> grid_items_;
    std::uint32_t scene_rebuilds_ = 0;
};

}  // namespace sc
