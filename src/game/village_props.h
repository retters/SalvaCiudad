// What makes the village's work visible (phase 67), as plain rules the view
// follows: the stage a building site shows, how full a pile looks and how an
// arrow flies. View only: nothing here changes the simulation.
#pragma once

#include <cstdint>

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
