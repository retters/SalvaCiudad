// The hierarchical map generator (phases 39 to 43): it decides from the
// general to the particular, and each level only refines what the one
// before allowed.
//   Level 0, the world: size, seed, sea and islands.
//   Level 1, regions: the map is split into irregular regions, each with a
//            single role (plain, hills, mountains, plateau or basin).
//   Level 2, structures: only those of the region's role inside it.
//   Level 3, water; level 4, soil and life; level 5, fine detail.
// This module shapes the ground (levels 0 to 2); the water, soil and life
// stages are shared with the classic generator (worldgen.cpp).
// Deterministic and integer-only, like the rest of the simulation.
#pragma once

#include <array>
#include <cstdint>
#include <functional>
#include <vector>

#include "sim/map.h"

namespace sc::sim::hier {

// Changes whenever the same settings would give a different map.
inline constexpr std::uint16_t kVersion = 1;

// The shaped ground, for the shared stages.
struct Ground {
    std::vector<std::int32_t> h;  // (n + 1)^2 vertex heights, millimeters.
    std::int32_t sea_mm = 0;      // Sea surface; 0 without a sea.
    // Regions first (landform i is region i), then structures.
    std::vector<Landform> landforms;
    // Per kOwnerBlock square: landform index + 1 of its region and of its
    // structure (0 = none).
    std::vector<std::uint16_t> region_owner;
    std::vector<std::uint16_t> structure_owner;
    // Vertices where a river must start (x, z).
    std::vector<std::array<std::int32_t, 2>> river_sources;
};

// Called with the progress (0..100); returning false cancels.
using Progress = std::function<bool(int percent)>;

// Shapes a map of `n` cells per side. False if cancelled.
[[nodiscard]] bool shape(const MapSettings& s, std::int32_t n, const Progress& progress, Ground& out);

// Tuning shared with the tests: meters between region centers.
[[nodiscard]] std::int32_t region_spacing(std::int32_t n);

}  // namespace sc::sim::hier
