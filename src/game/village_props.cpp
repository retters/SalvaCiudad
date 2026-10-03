#include "game/village_props.h"

#include <algorithm>
#include <cmath>

namespace sc::props {

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
