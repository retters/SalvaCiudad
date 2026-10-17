// Developer tools (Ctrl+F3): an inspector for the object under the cursor
// or selected, a tab to create objects and an explorer to find them. Built
// with Dear ImGui like the statistics window, never shown to players in
// normal play (decision D-622).
#pragma once

#include <cstddef>
#include <cstdint>
#include <optional>
#include <string>
#include <vector>

#include "game/terrain_names.h"
#include "math/vec.h"
#include "sim/content.h"
#include "sim/map.h"

namespace sc {

class Camera;
class GameSession;
class MapScene;
class Walkers;
namespace rml {
class RmlUi;
}
namespace render {
class SceneRenderer;
}

// What the tools can see and change this frame.
struct DevContext {
    sim::MapData* map = nullptr;  // Null when no map is shown.
    const sim::Content* content = nullptr;
    MapScene* scene = nullptr;
    render::SceneRenderer* renderer = nullptr;
    Walkers* crowd = nullptr;
    Camera* camera = nullptr;
    GameSession* session = nullptr;  // The village game, if any.
    bool ray_valid = false;  // The pointer is over the world, not a window.
    math::Vec3 ray_origin;
    math::Vec3 ray_dir;      // Normalized.
    bool clicked = false;    // A left click (not a drag) on the world.
    rml::RmlUi* rml = nullptr;  // The RmlUi interface (phase 117), in menus too.
};

struct DevObject {
    enum class Kind : std::uint8_t { None, Feature, House, Villager };
    Kind kind = Kind::None;
    std::size_t index = 0;
    bool operator==(const DevObject&) const = default;
};

class DevTools {
public:
    void toggle() { visible_ = !visible_; }
    [[nodiscard]] bool visible() const { return visible_; }

    // Picking and placing; call every frame before draw().
    void update(DevContext& ctx);
    // The ImGui window; call inside the ImGui frame.
    void draw(DevContext& ctx);

    // Where to draw markers (the top of the object), if any.
    [[nodiscard]] std::optional<math::Vec3> selected_marker(const DevContext& ctx) const;
    [[nodiscard]] std::optional<math::Vec3> hovered_marker(const DevContext& ctx) const;

    // Forget everything that points into the current map.
    void reset();

private:
    enum class Tab : std::uint8_t { Inspector, Create, Explorer, Village, Interface };
    enum class CreateKind : std::uint8_t { Tree, BerryBush, Herbs, Stone, IronOre, House, Person, Count };
    enum class Filter : std::uint8_t { All, Trees, Plants, Rocks, Houses, People, Count };

    [[nodiscard]] bool valid(const DevContext& ctx, DevObject o) const;
    [[nodiscard]] math::Vec3 position(const DevContext& ctx, DevObject o) const;
    [[nodiscard]] float height(const DevContext& ctx, DevObject o) const;
    [[nodiscard]] std::string name(const DevContext& ctx, DevObject o) const;
    [[nodiscard]] bool passes(const DevContext& ctx, DevObject o) const;

    void pick(DevContext& ctx);
    [[nodiscard]] std::optional<float> ground_hit(const DevContext& ctx) const;
    void build_index(const sim::MapData& map);
    void place(DevContext& ctx, math::Vec3 at);
    void remove(DevContext& ctx, DevObject o);
    void go_to(DevContext& ctx, DevObject o);

    void inspector_tab(DevContext& ctx);
    void terrain_info(const DevContext& ctx, math::Vec3 at);
    TerrainNames terrain_names_;
    void create_tab(DevContext& ctx);
    void explorer_tab(DevContext& ctx);
    void village_tab(DevContext& ctx);
    void interface_tab(DevContext& ctx);
    int grant_amount_ = 100;
    void rebuild_list(const DevContext& ctx);

    bool visible_ = false;
    DevObject selected_;
    DevObject hovered_;
    std::optional<math::Vec3> hovered_ground_;  // Ground under the cursor.
    std::optional<Tab> switch_to_;
    Tab active_tab_ = Tab::Inspector;  // The tab shown last frame.

    // Features by 16 m cell, for picking.
    const sim::MapData* indexed_map_ = nullptr;
    std::size_t indexed_count_ = 0;
    std::int32_t index_side_ = 0;
    std::vector<std::vector<std::uint32_t>> index_;

    // Create tab.
    CreateKind create_kind_ = CreateKind::Tree;
    int species_ = 0;
    int size_ = 1;
    float height_m_ = 9.5f;
    float house_yaw_deg_ = 0.0f;
    int person_body_ = 0;  // 0 random, 1 man, 2 woman.
    int person_count_ = 1;
    bool place_on_click_ = false;
    std::string last_message_;

    // Explorer tab.
    Filter filter_ = Filter::All;
    char search_[64] = {};
    std::string applied_search_;
    Filter applied_filter_ = Filter::Count;
    bool sort_by_distance_ = false;
    bool list_dirty_ = true;
    std::vector<DevObject> list_;
};

// Lowercase without accents (á → a, Ñ → n...), for searching.
[[nodiscard]] std::string fold_for_search(std::string_view text);

}  // namespace sc
