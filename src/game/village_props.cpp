#include "game/village_props.h"

#include <algorithm>
#include <cmath>

namespace sc::props {

std::vector<std::size_t> choose_piles(std::span<const std::int32_t> amounts, std::size_t most) {
    std::vector<std::size_t> chosen;
    for (std::size_t i = 0; i < amounts.size(); ++i) {
        if (amounts[i] > 0) {
            chosen.push_back(i);
        }
    }
    if (chosen.size() > most) {
        std::stable_sort(chosen.begin(), chosen.end(), [&](std::size_t a, std::size_t b) { return amounts[a] > amounts[b]; });
        chosen.resize(most);
        std::sort(chosen.begin(), chosen.end());
    }
    return chosen;
}

std::optional<PileSpot> pile_spot(std::size_t slot, float half_along, float half_out) {
    constexpr float kStep = 1.7f;    // Between two piles.
    constexpr float kCorner = 0.8f;  // From a corner to the first pile's middle.
    constexpr float kDoor = 1.0f;    // Kept free on each side of the door's middle.
    constexpr float kWall = 1.0f;    // From a wall to a pile's middle.
    // Along the front wall, from the right corner toward the door.
    for (float along = half_along - kCorner; along >= kDoor; along -= kStep) {
        if (slot == 0) {
            return PileSpot{along, half_out + kWall};
        }
        --slot;
    }
    // Along the right wall, from the front corner toward the back.
    for (float out = half_out - kCorner; out >= -half_out; out -= kStep) {
        if (slot == 0) {
            return PileSpot{half_along + kWall, out};
        }
        --slot;
    }
    return std::nullopt;
}

ArrowPose arrow_pose(math::Vec3 from, math::Vec3 to, float t) {
    const float u = std::clamp(t, 0.0f, 1.0f);
    const math::Vec3 d = to - from;
    ArrowPose pose;
    pose.position = from + d * u;
    // A low arc: a twelfth of the way up at the middle.
    pose.position.y += math::length(math::Vec3{d.x, 0.0f, d.z}) / 12.0f * 4.0f * u * (1.0f - u);
    pose.yaw = std::atan2(d.x, d.z);
    return pose;
}

float arrow_seconds(math::Vec3 from, math::Vec3 to) {
    return std::max(0.2f, math::length(to - from) / 30.0f);
}

}  // namespace sc::props
