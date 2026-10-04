// What makes the village's work visible (phase 67), as plain rules the view
// follows: the stage a building site shows, how full a pile looks and how an
// arrow flies. View only: nothing here changes the simulation.
#pragma once

#include <cstddef>
#include <cstdint>
#include <optional>
#include <span>
#include <vector>

#include "math/vec.h"

namespace sc::props {

// A site shows its foundations, then its frame with scaffolding, then the
// building itself: the stage (0 or 1) for a progress of 0 to 1.
inline constexpr float kFrameFrom = 0.35f;
[[nodiscard]] constexpr int site_stage(float progress) {
    return progress < kFrameFrom ? 0 : 1;
}

// How a pile of `amount` looks next to what would be a full one: 0 (no
// pile), 1 (a few pieces), 2 (half a pile) or 3 (full).
[[nodiscard]] constexpr int pile_level(std::int32_t amount, std::int32_t full) {
    if (amount <= 0) {
        return 0;
    }
    if (full <= 0 || amount * 3 >= full * 2) {
        return 3;
    }
    return amount * 3 >= full ? 2 : 1;
}

// Phase 89: a building shows a pile for each resource it holds, at most
// this many: those it has the most of.
inline constexpr std::size_t kMaxPiles = 6;
// The resources that get a pile, given the amount of each by its index:
// the `most` largest amounts over zero (of two alike, the lower index), in
// the order of their indices, so a pile keeps its place while amounts change.
[[nodiscard]] std::vector<std::size_t> choose_piles(std::span<const std::int32_t> amounts, std::size_t most = kMaxPiles);
// Where pile number `slot` (from 0) stands by a building, in meters from
// its center: `along` the wall of the door (to the door's right) and `out`
// from the center toward the front. The first piles line the front wall
// from its right corner, leaving the door free; the next ones follow the
// right wall toward the back. Nothing when there is no room left.
// `half_along` and `half_out` are half the building's footprint.
struct PileSpot {
    float along = 0.0f;
    float out = 0.0f;
};
[[nodiscard]] std::optional<PileSpot> pile_spot(std::size_t slot, float half_along, float half_out);

// An arrow from `from` to `to`: where it is and where it points (about the
// vertical) after `t` of its flight (0 to 1). It flies in a low arc.
struct ArrowPose {
    math::Vec3 position;
    float yaw = 0.0f;
};
[[nodiscard]] ArrowPose arrow_pose(math::Vec3 from, math::Vec3 to, float t);
// Seconds an arrow takes: 30 m a second, never under a fifth of a second.
[[nodiscard]] float arrow_seconds(math::Vec3 from, math::Vec3 to);

}  // namespace sc::props
