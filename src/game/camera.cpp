#include "game/camera.h"

#include <algorithm>
#include <cmath>
#include <utility>

namespace sc {

namespace {

constexpr float kPanSpeedPerMeter = 1.1f;   // Aerial: ground meters per second per meter of distance.
constexpr float kRotateSpeed = 1.6f;        // Radians per second with the keys.
constexpr float kDragRotatePerPixel = 0.005f;
constexpr float kLookPerPixel = 0.0025f;    // First person mouse look.
constexpr float kZoomStep = 0.15f;          // Fraction of the distance per wheel notch.
constexpr float kSmoothing = 12.0f;         // Higher is snappier.
constexpr float kFollowSmoothing = 8.0f;
constexpr float kWalkSpeed = 5.5f;          // First person, meters per second.

// Exponential approach that behaves the same at any frame rate.
float approach(float current, float goal, float dt, float rate = kSmoothing) {
    return goal + (current - goal) * std::exp(-rate * dt);
}

}  // namespace

CameraMode next_camera_mode(CameraMode mode) {
    return static_cast<CameraMode>((static_cast<int>(mode) + 1) % static_cast<int>(CameraMode::Count));
}

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

float Camera::ground(float x, float z) const {
    return ground_ ? ground_(x, z) : 0.0f;
}

// Height of the point the camera orbits or stands on.
float Camera::focus_height() const {
    switch (mode_) {
        case CameraMode::Aerial: return 0.0f;
        case CameraMode::ThirdPerson: return kPivotHeight * follow_height_;
        case CameraMode::FirstPerson: return kEyeHeight * follow_height_;
        case CameraMode::Count: break;
    }
    return 0.0f;
}

void Camera::set_ground(std::function<float(float, float)> ground) {
    ground_ = std::move(ground);
}

void Camera::set_follow(std::optional<math::Vec3> feet, float height) {
    follow_ = feet;
    follow_height_ = feet ? height : 1.0f;
}

void Camera::set_mode(CameraMode mode) {
    if (mode == mode_ || mode == CameraMode::Count) {
        return;
    }
    const CameraMode old = mode_;
    mode_ = mode;
    switch (mode) {
        case CameraMode::Aerial:
            goal_distance_ = std::clamp(goal_distance_, kMinDistance, max_distance_);
            break;
        case CameraMode::ThirdPerson:
            // Glide in from the current view to a close, over-the-shoulder
            // orbit; the smoothing makes the switch continuous.
            if (old == CameraMode::Aerial) {
                pitch_ = tilt();
            }
            goal_pitch_ = math::radians(kOrbitDefaultPitch);
            goal_distance_ = kOrbitDefaultDistance;
            break;
        case CameraMode::FirstPerson:
            goal_pitch_ = pitch_ = math::radians(-8.0f);
            break;
        case CameraMode::Count:
            break;
    }
}

void Camera::update(const CameraInput& input, const CameraSpeeds& speeds, float dt) {
    dt = std::clamp(dt, 0.0f, 0.1f);
    const float max_pitch = math::radians(kOrbitMaxPitch);

    // Turning: keys and horizontal drag in every mode; mouse look in first person.
    goal_yaw_ += (input.rotate * kRotateSpeed * dt + input.drag_rotate_px * kDragRotatePerPixel) * speeds.rotate;
    if (mode_ == CameraMode::FirstPerson) {
        goal_yaw_ += input.look_dx * kLookPerPixel * speeds.rotate;
        goal_pitch_ -= input.look_dy * kLookPerPixel * speeds.rotate;
        goal_pitch_ = std::clamp(goal_pitch_, -math::radians(kMaxLookPitch), math::radians(kMaxLookPitch));
    } else if (mode_ == CameraMode::ThirdPerson) {
        // Dragging down raises the camera, as in most orbit cameras.
        goal_pitch_ += input.drag_pitch_px * kDragRotatePerPixel * speeds.rotate;
        goal_pitch_ = std::clamp(goal_pitch_, math::radians(kOrbitMinPitch), max_pitch);
    }

    if (input.zoom_steps != 0.0f && mode_ != CameraMode::FirstPerson) {
        const float factor = std::pow(1.0f - kZoomStep * std::clamp(speeds.zoom, 0.25f, 4.0f), input.zoom_steps);
        const float lo = mode_ == CameraMode::Aerial ? kMinDistance : kOrbitMinDistance;
        const float hi = mode_ == CameraMode::Aerial ? max_distance_ : kOrbitMaxDistance;
        goal_distance_ = std::clamp(goal_distance_ * factor, lo, hi);
    }

    // Moving, relative to where the camera looks.
    const float cy = std::cos(goal_yaw_);
    const float sy = std::sin(goal_yaw_);
    const math::Vec3 fwd{sy, 0.0f, -cy};
    const math::Vec3 right{cy, 0.0f, sy};
    float speed = 0.0f;
    switch (mode_) {
        case CameraMode::Aerial: speed = kPanSpeedPerMeter * goal_distance_; break;
        case CameraMode::ThirdPerson: speed = 6.0f + goal_distance_ * 0.35f; break;
        case CameraMode::FirstPerson: speed = kWalkSpeed; break;
        case CameraMode::Count: break;
    }
    goal_target_ += (fwd * input.move_forward + right * input.move_right) * (speed * speeds.pan * dt);
    if (follow_) {
        goal_target_ = *follow_;
    }
    goal_target_.x = std::clamp(goal_target_.x, min_x_, max_x_);
    goal_target_.z = std::clamp(goal_target_.z, min_z_, max_z_);
    goal_target_.y = ground(goal_target_.x, goal_target_.z) + focus_height();

    const float follow_rate = follow_ ? kFollowSmoothing : kSmoothing;
    target_ = {approach(target_.x, goal_target_.x, dt, follow_rate), approach(target_.y, goal_target_.y, dt, follow_rate),
               approach(target_.z, goal_target_.z, dt, follow_rate)};
    if (mode_ == CameraMode::FirstPerson) {
        // Mouse look must feel direct: no smoothing on rotation.
        yaw_ = goal_yaw_;
        pitch_ = goal_pitch_;
    } else {
        yaw_ = approach(yaw_, goal_yaw_, dt);
        pitch_ = approach(pitch_, goal_pitch_, dt);
    }
    distance_ = approach(distance_, goal_distance_, dt);
    keep_above_ground();
}

math::Vec3 Camera::orbit_eye(float pitch, float distance) const {
    const math::Vec3 back = -forward_on_ground();
    return target_ + back * (distance * std::cos(pitch)) + math::Vec3{0.0f, distance * std::sin(pitch), 0.0f};
}

// Third person: if the eye would go under the ground, raise the orbit so
// the view pans up instead.
void Camera::keep_above_ground() {
    if (mode_ != CameraMode::ThirdPerson || distance_ <= 0.0f) {
        return;
    }
    const math::Vec3 e = orbit_eye(pitch_, distance_);
    const float floor_y = std::max(ground(e.x, e.z), ground(target_.x, target_.z)) + kGroundClearance;
    const float need = (floor_y - target_.y) / distance_;
    if (need > -1.0f) {
        const float min_pitch = std::asin(std::clamp(need, -1.0f, 1.0f));
        if (pitch_ < min_pitch) {
            pitch_ = min_pitch;
            goal_pitch_ = std::max(goal_pitch_, min_pitch);
        }
    }
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
    const float lo = mode_ == CameraMode::Aerial ? kMinDistance : kOrbitMinDistance;
    const float hi = mode_ == CameraMode::Aerial ? max_distance_ : kOrbitMaxDistance;
    goal_distance_ = std::clamp(meters, lo, hi);
}

void Camera::set_max_distance_override(float meters) {
    max_distance_ = meters > kMaxDistance ? meters : kMaxDistance;
    goal_distance_ = std::min(goal_distance_, max_distance_);
}

void Camera::snap() {
    target_ = goal_target_;
    yaw_ = goal_yaw_;
    pitch_ = goal_pitch_;
    distance_ = goal_distance_;
}

void Camera::restore(CameraMode mode, math::Vec3 target, float yaw, float pitch, float distance) {
    set_mode(mode);
    follow_.reset();
    goal_target_ = target;
    goal_yaw_ = yaw;
    goal_pitch_ = pitch;
    // The same limits as zooming by hand.
    set_distance(distance);
    snap();
}

math::Vec3 Camera::forward() const {
    switch (mode_) {
        case CameraMode::FirstPerson: {
            const float c = std::cos(pitch_);
            return {std::sin(yaw_) * c, std::sin(pitch_), -std::cos(yaw_) * c};
        }
        case CameraMode::Aerial:
        case CameraMode::ThirdPerson:
        case CameraMode::Count:
            break;
    }
    return math::normalize(target_ - eye());
}

math::Vec3 Camera::eye() const {
    switch (mode_) {
        case CameraMode::Aerial: return orbit_eye(tilt(), distance_);
        case CameraMode::ThirdPerson: return orbit_eye(pitch_, distance_);
        case CameraMode::FirstPerson: return target_;
        case CameraMode::Count: break;
    }
    return target_;
}

math::Mat4 Camera::view() const {
    const math::Vec3 e = eye();
    if (mode_ == CameraMode::FirstPerson) {
        return math::look_at(e, e + forward(), {0.0f, 1.0f, 0.0f});
    }
    return math::look_at(e, target_, {0.0f, 1.0f, 0.0f});
}

float Camera::near_z() const {
    switch (mode_) {
        case CameraMode::Aerial: return std::max(0.25f, distance_ * 0.02f);
        case CameraMode::ThirdPerson: return std::max(0.1f, distance_ * 0.01f);
        case CameraMode::FirstPerson: return 0.05f;
        case CameraMode::Count: break;
    }
    return 0.1f;
}

math::Mat4 Camera::projection(float aspect, float far_z) const {
    return math::perspective_reverse_z(math::radians(kFovY), aspect, near_z(), far_z);
}

RayHit ray_to_vertical_segment(math::Vec3 origin, math::Vec3 dir, math::Vec3 base, float height) {
    // Closest points between the ray origin + t * dir and the segment
    // base + s * (0, 1, 0), s in [0, height].
    const math::Vec3 d = math::normalize(dir);
    const math::Vec3 w = origin - base;
    const float b = d.y;  // dot(d, up)
    const float denom = 1.0f - b * b;
    float t = 0.0f;
    float s = 0.0f;
    if (denom > 1e-6f) {
        t = (b * w.y - math::dot(d, w)) / denom;
        s = w.y + b * t;
    } else {
        // Looking straight up or down: any point of the ray will do.
        t = 0.0f;
        s = w.y;
    }
    s = std::clamp(s, 0.0f, height);
    // Recompute t for the clamped segment point.
    const math::Vec3 on_segment = base + math::Vec3{0.0f, s, 0.0f};
    t = std::max(0.0f, math::dot(on_segment - origin, d));
    const math::Vec3 on_ray = origin + d * t;
    return {math::length(on_ray - on_segment), t};
}

}  // namespace sc
