#include "game/camera.h"

#include <algorithm>
#include <cmath>

namespace sc {

namespace {

constexpr float kPanSpeedPerMeter = 1.1f;   // Ground meters per second per meter of distance.
constexpr float kRotateSpeed = 1.6f;        // Radians per second with the keys.
constexpr float kDragRotatePerPixel = 0.005f;
constexpr float kZoomStep = 0.15f;          // Fraction of the distance per wheel notch.
constexpr float kSmoothing = 12.0f;         // Higher is snappier.

// Exponential approach that behaves the same at any frame rate.
float approach(float current, float goal, float dt) {
    return goal + (current - goal) * std::exp(-kSmoothing * dt);
}

}  // namespace

float Camera::tilt_for_distance(float distance) {
    const float t = std::clamp((distance - kMinDistance) / (kMaxDistance - kMinDistance), 0.0f, 1.0f);
    // Tilts quickly near the ground, slowly when far.
    const float eased = 1.0f - (1.0f - t) * (1.0f - t);
    return math::radians(math::lerp(kCloseTilt, kFarTilt, eased));
}

float Camera::tilt() const {
    return tilt_for_distance(distance_);
}

math::Vec3 Camera::forward_on_ground() const {
    return {std::sin(yaw_), 0.0f, -std::cos(yaw_)};
}

math::Vec3 Camera::right_on_ground() const {
    return {std::cos(yaw_), 0.0f, std::sin(yaw_)};
}

void Camera::update(const CameraInput& input, const CameraSpeeds& speeds, float dt) {
    dt = std::clamp(dt, 0.0f, 0.1f);
    goal_yaw_ += (input.rotate * kRotateSpeed * dt + input.drag_rotate_px * kDragRotatePerPixel) * speeds.rotate;

    if (input.zoom_steps != 0.0f) {
        const float factor = std::pow(1.0f - kZoomStep * std::clamp(speeds.zoom, 0.25f, 4.0f), input.zoom_steps);
        goal_distance_ = std::clamp(goal_distance_ * factor, kMinDistance, max_distance_);
    }

    // Pan relative to where the camera looks, faster when zoomed out.
    const float cy = std::cos(goal_yaw_);
    const float sy = std::sin(goal_yaw_);
    const math::Vec3 fwd{sy, 0.0f, -cy};
    const math::Vec3 right{cy, 0.0f, sy};
    const float speed = kPanSpeedPerMeter * goal_distance_ * speeds.pan * dt;
    goal_target_ += (fwd * input.move_forward + right * input.move_right) * speed;
    goal_target_.x = std::clamp(goal_target_.x, min_x_, max_x_);
    goal_target_.z = std::clamp(goal_target_.z, min_z_, max_z_);

    target_ = {approach(target_.x, goal_target_.x, dt), approach(target_.y, goal_target_.y, dt),
               approach(target_.z, goal_target_.z, dt)};
    yaw_ = approach(yaw_, goal_yaw_, dt);
    distance_ = approach(distance_, goal_distance_, dt);
}

void Camera::set_bounds(float min_x, float min_z, float max_x, float max_z) {
    min_x_ = min_x;
    min_z_ = min_z;
    max_x_ = max_x;
    max_z_ = max_z;
}

void Camera::set_target(math::Vec3 target) {
    goal_target_ = target;
}

void Camera::set_yaw(float radians) {
    goal_yaw_ = radians;
}

void Camera::set_distance(float meters) {
    goal_distance_ = std::clamp(meters, kMinDistance, max_distance_);
}

void Camera::set_max_distance_override(float meters) {
    max_distance_ = meters > kMaxDistance ? meters : kMaxDistance;
    goal_distance_ = std::min(goal_distance_, max_distance_);
}

void Camera::snap() {
    target_ = goal_target_;
    yaw_ = goal_yaw_;
    distance_ = goal_distance_;
}

math::Vec3 Camera::eye() const {
    const float t = tilt();
    const math::Vec3 back = -forward_on_ground();
    return target_ + back * (distance_ * std::cos(t)) + math::Vec3{0.0f, distance_ * std::sin(t), 0.0f};
}

math::Mat4 Camera::view() const {
    return math::look_at(eye(), target_, {0.0f, 1.0f, 0.0f});
}

float Camera::near_z() const {
    return std::max(0.25f, distance_ * 0.02f);
}

math::Mat4 Camera::projection(float aspect, float far_z) const {
    return math::perspective_reverse_z(math::radians(kFovY), aspect, near_z(), far_z);
}

}  // namespace sc
