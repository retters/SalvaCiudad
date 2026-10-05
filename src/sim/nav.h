// Walking on the map: a grid of 2 m cells marking water, steep ground and
// buildings, and an A* search over it (section 7.8). Deterministic: ties
// are broken by cell index, never by memory order.
#pragma once

#include <algorithm>
#include <array>
#include <cstdint>
#include <functional>
#include <utility>
#include <vector>

#include "sim/fixed.h"
#include "sim/map.h"

namespace sc::sim {

class NavGrid {
public:
    static constexpr std::int32_t kCell = 2;                // Meters per nav cell.
    static constexpr std::int32_t kDefaultMaxNodes = 150000;  // Search budget per path.

    void build(const MapData& map);

    [[nodiscard]] std::int32_t side() const { return side_; }
    [[nodiscard]] bool walkable(std::int32_t cx, std::int32_t cz) const;
    // Marks the nav cells under a rectangle of map meters (buildings).
    void set_building(std::int32_t x0, std::int32_t z0, std::int32_t x1, std::int32_t z1, bool blocked);

    [[nodiscard]] std::int32_t cell_of(Fixed meters) const;
    [[nodiscard]] FixedVec2 center(std::int32_t cx, std::int32_t cz) const;

    // A path from `from` to `to` as waypoints (the last is `to` itself, or
    // the closest walkable point to it). False if no path was found within
    // the budget.
    bool find_path(FixedVec2 from, FixedVec2 to, std::vector<FixedVec2>& out, std::int32_t max_nodes = kDefaultMaxNodes);
    // Phase 66: the same over the cells `allow` accepts only (an explorer
    // keeps to explored ground).
    bool find_path_within(FixedVec2 from, FixedVec2 to, std::vector<FixedVec2>& out,
                          const std::function<bool(std::int32_t, std::int32_t)>& allow,
                          std::int32_t max_nodes = kDefaultMaxNodes);
    // Raiders: a path over the ground that may cross buildings and gates
    // (they break them), which cost a lot more than open ground.
    bool find_path_through(FixedVec2 from, FixedVec2 to, std::vector<FixedVec2>& out,
                           std::int32_t max_nodes = kDefaultMaxNodes);
    // Cell size in meters.
    static constexpr std::int32_t kCellMeters = 2;
    // Gates: walkable for villagers, an obstacle for raiders.
    void set_gate(std::int32_t x0, std::int32_t z0, std::int32_t x1, std::int32_t z1, bool on);
    // Whether a cell (2 m) has a building or a gate in the way of raiders.
    [[nodiscard]] bool obstacle(std::int32_t cx, std::int32_t cz) const;
    // Open ground (no water or cliff), whatever is built on it.
    [[nodiscard]] bool ground(std::int32_t cx, std::int32_t cz) const;
    // Phase 95: roads. Each kind (1 to `percents.size()`) is walked at its
    // percent of the usual speed, and a path costs that much less over it.
    void set_road_kinds(const std::vector<std::int32_t>& percents);
    // The road on a cell: a kind, or 0 for none.
    void set_road(std::int32_t cx, std::int32_t cz, std::uint8_t kind);
    [[nodiscard]] std::uint8_t road(std::int32_t cx, std::int32_t cz) const {
        return road_.empty() || cx < 0 || cz < 0 || cx >= side_ || cz >= side_ ? std::uint8_t{0} : road_[index(cx, cz)];
    }
    // How fast one walks on a cell, percent (100 off the roads).
    [[nodiscard]] std::int32_t road_percent(std::int32_t cx, std::int32_t cz) const { return road_percent_[road(cx, cz)]; }
    // Phase 94: walls, hedges, fences and their gates. The wild animals do
    // not cross these cells (they walk over every other building's).
    void set_barrier(std::int32_t x0, std::int32_t z0, std::int32_t x1, std::int32_t z1, bool on);
    [[nodiscard]] bool barrier(std::int32_t cx, std::int32_t cz) const;

    // Straight-line guess of the walking distance, in meters.
    [[nodiscard]] static std::int32_t distance_estimate(FixedVec2 a, FixedVec2 b);

    [[nodiscard]] std::uint64_t searches() const { return searches_; }
    // Changes whenever buildings block or free cells.
    [[nodiscard]] std::uint32_t version() const { return version_; }

    // Walking cost from `from` to every cell within `max_cost` (10 per
    // straight 2 m step on flat ground), in a square window around it.
    struct Area {
        std::int32_t x0 = 0;  // Window corner and side, in cells.
        std::int32_t z0 = 0;
        std::int32_t side = 0;
        std::vector<std::uint16_t> cost;  // 0xFFFF = out of reach.
        std::uint32_t version = 0;
        [[nodiscard]] std::uint16_t at(std::int32_t cx, std::int32_t cz) const {
            const std::int32_t lx = cx - x0;
            const std::int32_t lz = cz - z0;
            if (lx < 0 || lz < 0 || lx >= side || lz >= side) {
                return 0xFFFF;
            }
            return cost[static_cast<std::size_t>(lz * side + lx)];
        }
    };
    [[nodiscard]] Area flood(FixedVec2 from, std::uint16_t max_cost) const;
    // Whether two points are in the same walkable area (after snapping each
    // to the nearest walkable cell).
    [[nodiscard]] bool connected(FixedVec2 a, FixedVec2 b) const;
    // Whether two points are on the same land, whatever is built on it:
    // false across the sea or a lake (islands, phase 22).
    [[nodiscard]] bool same_land(FixedVec2 a, FixedVec2 b) const;

private:
    [[nodiscard]] std::size_t index(std::int32_t cx, std::int32_t cz) const {
        return static_cast<std::size_t>(cz) * static_cast<std::size_t>(side_) + static_cast<std::size_t>(cx);
    }
    bool search(FixedVec2 from, FixedVec2 to, std::vector<FixedVec2>& out, std::int32_t max_nodes, bool through,
                const std::function<bool(std::int32_t, std::int32_t)>* allow = nullptr);
    // Nearest walkable cell to (cx, cz) within a few cells; false if none.
    bool nearest_walkable(std::int32_t& cx, std::int32_t& cz) const;
    // Connected areas, labeled inside blocks of 64 x 64 cells and joined
    // across the blocks' edges, so a change relabels only its blocks (a
    // colossal map has 67 million cells). Derived, rebuilt lazily.
    struct Areas {
        static constexpr std::int32_t kBlock = 64;
        std::int32_t side = 0;             // Cells per side.
        std::int32_t blocks = 0;           // Blocks per side.
        std::vector<std::uint16_t> local;  // Per cell: 0 = closed, else its area inside the block.
        std::vector<std::uint16_t> count;  // Per block: areas inside it.
        std::vector<std::uint32_t> base;   // Per block: its first area among all.
        std::vector<std::uint8_t> dirty;   // Per block.
        bool any_dirty = false;
        // Per block: the pairs of areas that touch across its right and
        // its bottom edge (this block's area, the neighbor's).
        using Pairs = std::vector<std::pair<std::uint16_t, std::uint16_t>>;
        std::vector<Pairs> right;
        std::vector<Pairs> down;
        std::vector<std::uint32_t> root;   // Per area among all: the area it joins.
        std::vector<std::uint16_t> stack;

        void reset(std::int32_t cells_per_side);
        void mark(std::int32_t cx0, std::int32_t cz0, std::int32_t cx1, std::int32_t cz1);
        template <class Open>
        void update(const Open& open);
        // 0 for a closed cell; equal for cells in the same area.
        [[nodiscard]] std::uint32_t at(std::int32_t cx, std::int32_t cz) const;
    };
    void update_regions() const;
    // Nearest open ground to (cx, cz) within a few cells; false if none.
    bool nearest_ground(std::int32_t& cx, std::int32_t& cz) const;
    mutable Areas walk_areas_;   // Walkable cells.
    mutable Areas land_areas_;   // Ground, ignoring buildings (built on first use).

    std::int32_t side_ = 0;
    std::vector<std::uint8_t> terrain_cost_;  // 0 = blocked, else cost of a straight step (10 = normal).
    std::vector<std::uint8_t> building_;      // Cells under buildings.
    // Low half: the gates over the cell (walkable, but raiders break them).
    // High half: the walls, fences and gates over it (closed to the wild
    // animals). Two counts in a byte: a colossal map has 67 million cells.
    std::vector<std::uint8_t> gate_;

    // Roads: the kind on each cell (empty until the first road is laid: a
    // colossal map has 67 million cells), how many cells there are of each
    // kind, and each kind's speed and what it does to the cost of a step.
    std::vector<std::uint8_t> road_;
    std::array<std::uint32_t, 16> road_cells_{};
    std::array<std::int32_t, 16> road_percent_{100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100};
    // The least a straight step may cost, with the roads there are now (10 without any).
    std::uint32_t least_step_ = 10;
    // The cost of a step onto a cell: its ground's, less on a road.
    [[nodiscard]] std::uint32_t step_cost(std::size_t i) const {
        const std::uint32_t ground = terrain_cost_[i];
        if (road_.empty() || road_[i] == 0) {
            return ground;
        }
        const auto percent = static_cast<std::uint32_t>(road_percent_[road_[i]]);
        return std::max<std::uint32_t>(1, (ground * 100 + percent / 2) / percent);
    }

    // Search scratch, reused between searches (stamped instead of cleared).
    std::vector<std::uint32_t> stamp_;
    std::vector<std::uint32_t> g_;
    std::vector<std::uint32_t> parent_;
    std::vector<std::uint8_t> closed_;
    std::uint32_t current_stamp_ = 0;
    std::uint64_t searches_ = 0;
    std::uint32_t version_ = 1;
};

}  // namespace sc::sim
