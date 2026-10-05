// Phase 91: what dresses the ground. Tall grass, ferns, reeds, wild
// flowers, petals, scree, driftwood, snowdrifts: small models the view puts
// around the camera by a fixed rule of each place (its biome, ground, slope,
// water nearby and the time of year, and a number taken from where it is).
// Nothing here is in the simulation, its hashes or the saved games: every
// machine draws the same because the rule only reads the map.
#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <optional>
#include <string_view>
#include <unordered_map>
#include <unordered_set>
#include <vector>

#include "math/vec.h"
#include "mods/mod_library.h"
#include "render/scene_renderer.h"
#include "sim/game.h"

namespace sc::cover {

enum class Kind : std::uint8_t {
    GrassTall,
    GrassDry,
    Clover,
    Fern,
    Reeds,
    FlowersRed,
    FlowersYellow,
    FlowersBlue,
    FlowersWhite,
    FlowersMixed,
    Sunflowers,
    PetalsPink,
    PetalsPurple,
    AlpineFlowers,
    Scree,
    Crag,
    Driftwood,
    Shells,
    TidePool,
    SnowDrift,
    IceFloe,
    Snowman,
    Count
};
inline constexpr std::size_t kKinds = static_cast<std::size_t>(Kind::Count);

// Its model, a file of the core mod.
[[nodiscard]] std::string_view model_file(Kind kind);
// A plant: it sways with the wind, and snow on the ground hides it.
[[nodiscard]] bool plant(Kind kind);

// What the time of year does to the ground.
struct When {
    sim::Season season = sim::Season::Spring;
    bool snow = false;    // The ground is white: the plants are under it.
    bool frozen = false;  // It freezes: ice floats on the water.
    bool operator==(const When&) const = default;
};
[[nodiscard]] When when(const sim::Game& game);

// The ground is looked at in squares of this many meters: one adornment at
// most in each.
inline constexpr std::int32_t kSquare = 4;

struct Item {
    Kind kind = Kind::GrassTall;
    float x = 0.0f;  // Where it stands, in meters.
    float z = 0.0f;
    float yaw = 0.0f;
    float scale = 1.0f;
};
// The adornment of the square (sx, sz) of the map, if it has one. The same
// for the same map, content and time of year, on every machine. Never on
// water (but for ice floes), never outside the map.
[[nodiscard]] std::optional<Item> item_at(const sim::MapData& map, const sim::Content& content, const When& when,
                                          std::int32_t sx, std::int32_t sz);

// How far from where the camera looks the ground is dressed, by the
// "ground detail" setting (0: not at all), and whether plants sway.
[[nodiscard]] float reach(int detail);
[[nodiscard]] bool sways(int detail);

// Snow against a wall: where the drift of a building stands, if it has one
// (about half of them do, on one of their sides, by where they are).
// (x, z, w, d): the building's footprint in cells.
[[nodiscard]] std::optional<Item> drift_by(std::int32_t x, std::int32_t z, std::int32_t w, std::int32_t d);
// A snowman beside a plaza's decoration: one in three has it.
[[nodiscard]] std::optional<Item> snowman_by(std::int32_t x, std::int32_t z, std::int32_t w, std::int32_t d);

// Puts the adornments in the scene, around where the camera looks.
class GroundCover {
public:
    void load(render::SceneRenderer& renderer, const mods::BuildResult& pack);
    // A new map: nothing drawn, nothing remembered.
    void reset(render::SceneRenderer& renderer);
    // Buildings, sites or fields changed: the ground under them is bare.
    void buildings_changed() { ++blocked_version_; }
    // `focus`: where the camera looks. `detail`: the setting, 0 to 3.
    void update(render::SceneRenderer& renderer, const sim::Game& game, math::Vec3 focus, int detail);
    // How many adornments are in the scene now.
    [[nodiscard]] std::size_t shown() const { return shown_; }

private:
    static constexpr render::ModelId kNoModel = ~0u;
    static constexpr std::int32_t kChunk = 32;  // Meters; a multiple of kSquare.

    struct Chunk {
        std::vector<Item> items;
    };
    void block(const sim::Game& game);
    [[nodiscard]] const Chunk& chunk(const sim::Game& game, std::int32_t cx, std::int32_t cz);

    std::array<render::ModelId, kKinds> models_{};
    bool loaded_ = false;
    std::unordered_map<std::uint64_t, Chunk> chunks_;   // By chunk, for the `when_` and the blocked squares of now.
    std::unordered_set<std::uint64_t> blocked_;         // Squares under buildings and fields.
    std::uint64_t blocked_version_ = 1;
    std::uint64_t blocked_built_ = 0;
    When when_;
    const void* map_ = nullptr;      // The map the chunks are of.
    int detail_ = -1;
    std::int32_t focus_cx_ = 0;      // The chunk the camera looked at when the scene was last filled.
    std::int32_t focus_cz_ = 0;
    bool filled_ = false;
    std::size_t shown_ = 0;
    std::array<std::vector<render::Instance>, kKinds> lists_;
};

}  // namespace sc::cover
