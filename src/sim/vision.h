// Fog of war (phases 32 to 34): what each side has explored, on a grid of
// 4 m cells. The simulation keeps only what was explored (it decides where
// a building may go and it is saved); what is in sight right now is worked
// out by the view, with the same helpers (decision D-3201).
#pragma once

#include <array>
#include <bit>
#include <cstdint>
#include <span>
#include <vector>

#include "sim/entity.h"
#include "sim/fixed.h"
#include "sim/serialize.h"

namespace sc::sim {

// Meters per side of a fog cell.
inline constexpr std::int32_t kFogCell = 4;
// Farthest anything sees, meters (the definitions are checked against it).
inline constexpr std::int32_t kMaxSight = 200;
// Vision groups: one per town, or one for all the allies (shared vision).
inline constexpr std::size_t kVisionGroups = 12;

// Fog cells per side of a map of `map_size` cells.
[[nodiscard]] constexpr std::int32_t fog_side(std::int32_t map_size) {
    return map_size <= 0 ? 0 : (map_size + kFogCell - 1) / kFogCell;
}

// One bit per fog cell.
class FogGrid {
public:
    void reset(std::int32_t side);
    [[nodiscard]] std::int32_t side() const { return side_; }
    [[nodiscard]] bool empty() const { return side_ == 0; }
    [[nodiscard]] bool get(std::int32_t cx, std::int32_t cz) const {
        if (cx < 0 || cz < 0 || cx >= side_ || cz >= side_) {
            return false;
        }
        const std::size_t i = static_cast<std::size_t>(cz) * static_cast<std::size_t>(side_) + static_cast<std::size_t>(cx);
        return ((words_[i >> 6] >> (i & 63u)) & 1u) != 0;
    }
    void clear_all();
    // Sets cells cx0..cx1 (inclusive) of row cz. `on_new` is called with
    // the index of each cell that was clear.
    template <typename Fn>
    void set_span(std::int32_t cz, std::int32_t cx0, std::int32_t cx1, Fn&& on_new);
    void set_span(std::int32_t cz, std::int32_t cx0, std::int32_t cx1) {
        set_span(cz, cx0, cx1, [](std::size_t) {});
    }
    [[nodiscard]] const std::vector<std::uint64_t>& words() const { return words_; }
    [[nodiscard]] std::vector<std::uint64_t>& words() { return words_; }

    bool operator==(const FogGrid&) const = default;

private:
    std::int32_t side_ = 0;
    std::vector<std::uint64_t> words_;
};

// Calls `fn(cz, cx0, cx1)` for each row of the fog cells whose centers lie
// within `radius` meters of (x, z), in meters; clipped to the grid.
template <typename Fn>
void for_each_disc_row(std::int32_t side, std::int32_t x, std::int32_t z, std::int32_t radius, Fn&& fn);

// A mixed number for a fog cell index: the explored cells' sum of these is
// a cheap check that two machines explored the same cells.
[[nodiscard]] std::uint64_t fog_cell_mix(std::size_t index);

// A building of another side as a vision group last saw it (phase 33,
// dynamic fog): out of sight it is drawn like this, even if it changed or
// is gone, until the group sees the place again.
struct BuildingGhost {
    EntityId id;
    std::uint16_t def = 0;
    std::uint8_t owner = 0;
    std::uint8_t rotation = 0;
    std::uint8_t level = 0;
    bool burning = false;
    std::int32_t x = 0;           // Corner cell, as the building's.
    std::int32_t z = 0;
    std::int16_t progress = 1000; // Built, per mille (1000: complete).
    std::int16_t burned = 0;      // Fire damage, 0..1000.
    bool operator==(const BuildingGhost&) const = default;
};

// The part of the vision that goes in the state hash, read back from a
// save before the cells (see Vision::read_summary).
struct VisionSummary {
    std::uint16_t groups = 0;
    std::array<std::uint32_t, 12> counts{};
    std::array<std::uint64_t, 12> sums{};
    std::array<std::vector<BuildingGhost>, 12> ghosts;
};

// What each vision group has explored, with a count and a checksum kept up
// to date as cells are revealed; with dynamic fog, also what each group
// sees at the last update and its ghosts of others' buildings.
class Vision {
public:
    // No fog: nothing is kept.
    void clear();
    // A grid per group whose bit is set in `groups`, all unexplored.
    void reset(std::int32_t map_size, std::uint16_t groups);
    [[nodiscard]] bool active() const { return side_ > 0; }
    [[nodiscard]] std::int32_t side() const { return side_; }
    [[nodiscard]] std::uint16_t groups() const { return groups_; }
    [[nodiscard]] bool used(std::uint8_t group) const { return group < kVisionGroups && ((groups_ >> group) & 1u) != 0; }
    [[nodiscard]] const FogGrid& explored(std::uint8_t group) const { return explored_[group % kVisionGroups]; }
    // Whether the fog cell holding (x, z) meters is explored.
    [[nodiscard]] bool explored_at(std::uint8_t group, std::int32_t x, std::int32_t z) const;
    // Whether every fog cell under the cells x..x+w-1, z..z+d-1 is explored.
    [[nodiscard]] bool explored_rect(std::uint8_t group, std::int32_t x, std::int32_t z, std::int32_t w,
                                     std::int32_t d) const;
    // Explores what can be seen from (x, z) meters, `radius` meters around;
    // with `sight`, marks it as in sight too (after begin_sight()).
    void reveal(std::uint8_t group, std::int32_t x, std::int32_t z, std::int32_t radius, bool sight = false);

    // Phase 33. Forgets what was in sight, before revealing again.
    void begin_sight();
    // Whether some fog cell under the cells x..x+w-1, z..z+d-1 was in sight
    // at the last update.
    [[nodiscard]] bool sees(std::uint8_t group, std::int32_t x, std::int32_t z, std::int32_t w, std::int32_t d) const;
    // Remembers a building as seen now (replaces what was remembered of it).
    void remember(std::uint8_t group, const BuildingGhost& ghost);
    // Forgets a building (its place was seen and it is gone).
    void forget(std::uint8_t group, EntityId id);
    // A group's ghosts, by entity index.
    [[nodiscard]] const std::vector<BuildingGhost>& ghosts(std::uint8_t group) const { return ghosts_[group % kVisionGroups]; }
    // Counts every change of any ghost (derived; for the view).
    [[nodiscard]] std::uint32_t ghost_revision() const { return ghost_revision_; }
    [[nodiscard]] std::uint32_t count(std::uint8_t group) const { return count_[group % kVisionGroups]; }
    [[nodiscard]] std::uint64_t sum(std::uint8_t group) const { return sum_[group % kVisionGroups]; }

    // The count and checksum of each group, and its ghosts (for the state
    // hash; saves carry it too).
    void write_summary(BinaryWriter& w) const;
    // Reads what write_summary() wrote. Ghosts must name a building
    // definition below `buildings`, an owner below `players` and a corner
    // inside a map of `map_size` cells.
    [[nodiscard]] static bool read_summary(BinaryReader& r, std::size_t buildings, std::uint8_t players,
                                           std::int32_t map_size, VisionSummary& out);
    // The explored cells (for saves and network snapshots).
    void write(BinaryWriter& w) const;
    // Reads what write() wrote, for a map of `map_size` cells; with
    // `expect_active` false there must be no grids. The counts must match
    // `summary`, whose ghosts it takes. On failure `out` is unchanged.
    [[nodiscard]] static bool read(BinaryReader& r, std::int32_t map_size, bool expect_active,
                                   const VisionSummary& summary, Vision& out);

    // Compares what is kept (not what was in sight, which follows from it).
    [[nodiscard]] bool operator==(const Vision& o) const {
        return side_ == o.side_ && groups_ == o.groups_ && explored_ == o.explored_ && count_ == o.count_ &&
               sum_ == o.sum_ && ghosts_ == o.ghosts_;
    }

private:
    std::int32_t side_ = 0;
    std::uint16_t groups_ = 0;
    std::array<FogGrid, kVisionGroups> explored_;
    std::array<std::uint32_t, kVisionGroups> count_{};
    std::array<std::uint64_t, kVisionGroups> sum_{};
    std::array<std::vector<BuildingGhost>, kVisionGroups> ghosts_;
    // Derived, never saved.
    std::array<FogGrid, kVisionGroups> sight_;
    std::uint32_t ghost_revision_ = 0;
};

// --- Templates -------------------------------------------------------------------

template <typename Fn>
void FogGrid::set_span(std::int32_t cz, std::int32_t cx0, std::int32_t cx1, Fn&& on_new) {
    if (cz < 0 || cz >= side_ || cx1 < cx0) {
        return;
    }
    cx0 = cx0 < 0 ? 0 : cx0;
    cx1 = cx1 >= side_ ? side_ - 1 : cx1;
    std::size_t first = static_cast<std::size_t>(cz) * static_cast<std::size_t>(side_) + static_cast<std::size_t>(cx0);
    const std::size_t last = static_cast<std::size_t>(cz) * static_cast<std::size_t>(side_) + static_cast<std::size_t>(cx1);
    while (first <= last) {
        const std::size_t word = first >> 6;
        const std::size_t bit0 = first & 63u;
        const std::size_t bit1 = (word == (last >> 6)) ? (last & 63u) : 63u;
        const std::uint64_t mask = (bit1 == 63u ? ~0ull : ((1ull << (bit1 + 1)) - 1)) & ~((1ull << bit0) - 1);
        std::uint64_t fresh = mask & ~words_[word];
        words_[word] |= mask;
        while (fresh != 0) {
            const auto b = static_cast<std::size_t>(std::countr_zero(fresh));
            on_new((word << 6) | b);
            fresh &= fresh - 1;
        }
        first = (word + 1) << 6;
    }
}

template <typename Fn>
void for_each_disc_row(std::int32_t side, std::int32_t x, std::int32_t z, std::int32_t radius, Fn&& fn) {
    if (side <= 0 || radius < 0) {
        return;
    }
    const auto floor_div = [](std::int32_t a, std::int32_t b) { return a >= 0 ? a / b : -((-a + b - 1) / b); };
    const std::int64_t r2 = static_cast<std::int64_t>(radius) * radius;
    // Cell centers are at 4c + 2 meters.
    std::int32_t cz0 = floor_div(z - radius - 2 + kFogCell - 1, kFogCell);
    std::int32_t cz1 = floor_div(z + radius - 2, kFogCell);
    cz0 = cz0 < 0 ? 0 : cz0;
    cz1 = cz1 >= side ? side - 1 : cz1;
    for (std::int32_t cz = cz0; cz <= cz1; ++cz) {
        const std::int64_t dz = static_cast<std::int64_t>(cz) * kFogCell + 2 - z;
        const std::int64_t rest = r2 - dz * dz;
        if (rest < 0) {
            continue;
        }
        const auto half = static_cast<std::int32_t>(isqrt(static_cast<std::uint64_t>(rest)));
        std::int32_t cx0 = floor_div(x - half - 2 + kFogCell - 1, kFogCell);
        std::int32_t cx1 = floor_div(x + half - 2, kFogCell);
        cx0 = cx0 < 0 ? 0 : cx0;
        cx1 = cx1 >= side ? side - 1 : cx1;
        if (cx0 <= cx1) {
            fn(cz, cx0, cx1);
        }
    }
}

}  // namespace sc::sim
