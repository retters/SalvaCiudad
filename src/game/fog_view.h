// What this machine's player sees through the fog of war (phases 32 and
// 33). The game keeps what each side explored; this works out what is in
// sight right now, from the same people and buildings, once a tick, and
// keeps the texels the renderer shows (decision D-3201). Presentation
// only: it never changes the game.
#pragma once

#include <cstdint>
#include <vector>

#include "sim/game.h"
#include "sim/vision.h"

namespace sc {

// Phase 34: the fog's ceiling over `map`, in cells of FogView::kCeilingCell
// meters, `side` per side: the ground smoothed over about 100 m, plus
// FogView::kCeilingAbove. What stands higher shows through the fog.
// Centimeters, row by row.
[[nodiscard]] std::vector<std::uint16_t> fog_ceiling(const sim::MapData& map, std::int32_t side);

class FogView {
public:
    // Texels of the fog texture: unexplored, explored but out of sight
    // (dynamic fog), in sight.
    static constexpr std::uint8_t kHidden = 0;
    static constexpr std::uint8_t kExplored = 128;
    static constexpr std::uint8_t kInSight = 255;
    // The texture goes to the GPU in square tiles of this many texels.
    static constexpr std::int32_t kTile = 64;
    // Phase 34: the ceiling's cells (meters), how high it stands over the
    // smoothed ground (centimeters) and the band over it where the fog
    // thins out (meters).
    static constexpr std::int32_t kCeilingCell = 16;
    static constexpr std::int32_t kCeilingAbove = 1400;
    static constexpr float kCeilingBand = 4.0f;

    // Follows `game` for the vision group `group`.
    void begin(const sim::Game& game, std::uint8_t group);
    // Works out what is in sight if the game moved on since the last call.
    void update(const sim::Game& game);

    // The fog shown: None when the game has none or when the developer
    // tools reveal everything.
    [[nodiscard]] sim::FogMode mode() const { return revealed_ || watch_all_ ? sim::FogMode::None : mode_; }
    // Phase 79: a spectator looking at everything sees no fog either.
    [[nodiscard]] bool watch_all() const { return watch_all_; }
    void set_watch_all(bool all);
    [[nodiscard]] sim::FogMode game_mode() const { return game_mode_; }
    [[nodiscard]] bool revealed() const { return revealed_; }
    void set_revealed(bool revealed);
    [[nodiscard]] std::uint8_t group() const { return group_; }

    // At a point (meters): in sight now; explored (ever seen, or in sight).
    [[nodiscard]] bool in_sight(float x, float z) const;
    [[nodiscard]] bool explored(float x, float z) const;
    // Whether what moves there and is not the player's shows: everywhere
    // without fog, where explored with static fog, in sight with dynamic.
    [[nodiscard]] bool shows(float x, float z) const;
    // The same for anything under a rectangle of cells (a building): some
    // part of it counts.
    [[nodiscard]] bool rect_in_sight(std::int32_t x, std::int32_t z, std::int32_t w, std::int32_t d) const;
    [[nodiscard]] bool rect_shows(std::int32_t x, std::int32_t z, std::int32_t w, std::int32_t d) const;
    // Whether nothing under the rectangle was ever explored or is in sight.
    [[nodiscard]] bool rect_unexplored(std::int32_t x, std::int32_t z, std::int32_t w, std::int32_t d) const;

    // Phase 34: the ceiling (see fog_ceiling()), and its height at a point
    // in meters.
    [[nodiscard]] const std::vector<std::uint16_t>& ceiling() const { return ceiling_; }
    [[nodiscard]] std::int32_t ceiling_side() const { return ceiling_side_; }
    [[nodiscard]] float ceiling_at(float x, float z) const;

    // The texels (side x side, row by row) and the tiles that changed since
    // the last call, as texel rectangles.
    struct Rect {
        std::int32_t x = 0, z = 0, w = 0, d = 0;
    };
    [[nodiscard]] std::int32_t side() const { return side_; }
    [[nodiscard]] const std::vector<std::uint8_t>& texels() const { return texels_; }
    [[nodiscard]] std::vector<Rect> take_dirty();
    // Counts every change of the texels (for the minimap), and every begin().
    [[nodiscard]] std::uint32_t revision() const { return revision_; }
    [[nodiscard]] std::uint32_t generation() const { return generation_; }

private:
    // How it is drawn: the revealed fog (phase 60) is the dynamic one with
    // every cell explored. `game_mode_` is the game's own.
    sim::FogMode mode_ = sim::FogMode::None;
    sim::FogMode game_mode_ = sim::FogMode::None;
    bool revealed_ = false;
    bool watch_all_ = false;
    std::uint8_t group_ = 0;
    std::int32_t side_ = 0;
    std::uint64_t tick_ = ~0ull;
    std::uint32_t explored_count_ = 0;
    sim::FogGrid visible_;
    sim::FogGrid previous_;           // Last tick's sight.
    sim::FogGrid explored_;           // The game's, when last copied.
    std::int32_t rows_[2] = {0, -1};  // Rows stamped now (first, last).
    std::int32_t last_rows_[2] = {0, -1};
    std::vector<std::uint8_t> texels_;
    std::int32_t tiles_ = 0;          // Per side.
    std::vector<std::uint8_t> dirty_; // By tile.
    bool any_dirty_ = false;
    std::vector<Rect> pending_;       // Tiles rebuilt, not yet taken.
    std::vector<std::uint16_t> ceiling_;
    std::int32_t ceiling_side_ = 0;
    std::uint32_t revision_ = 0;
    std::uint32_t generation_ = 0;

    [[nodiscard]] bool cell_in_sight(std::int32_t cx, std::int32_t cz) const { return visible_.get(cx, cz); }
    [[nodiscard]] bool cell_explored(std::int32_t cx, std::int32_t cz) const {
        return explored_.get(cx, cz) || visible_.get(cx, cz);
    }
    void stamp(std::int32_t x, std::int32_t z, std::int32_t radius);
    void mark_word(std::size_t word, std::uint64_t changed);
    void mark_all();
    void refresh_tiles();
};

}  // namespace sc
