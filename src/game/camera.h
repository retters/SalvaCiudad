// Player camera with three modes (switched with a key):
// - Aerial: the strategy view in the style of Farthest Frontier. It looks at
//   a point on the ground and tilts from low (close) to steep (far) as it
//   zooms.
// - Third person: an orbit around a point at eye height, free in yaw and
//   pitch, like World of Warcraft. It rises instead of going under the
//   ground.
// - First person: look around with the mouse and walk on the ground.
// It can follow a moving point (a selected character). Presentation only,
// never simulation.
#pragma once

#include <cstdint>
#include <functional>
#include <optional>

#include "math/vec.h"

namespace sc {

enum class CameraMode : std::uint8_t { Aerial, ThirdPerson, FirstPerson, Count };

[[nodiscard]] CameraMode next_camera_mode(CameraMode mode);

struct CameraInput {
    float move_forward = 0.0f;    // -1..1, from keys or screen edge.
    float move_right = 0.0f;      // -1..1
    float rotate = 0.0f;          // -1..1 from keys (positive turns right).
    float drag_rotate_px = 0.0f;  // Horizontal mouse drag this frame, pixels.
    float drag_pitch_px = 0.0f;   // Vertical mouse drag this frame (third person).
    float look_dx = 0.0f;         // Relative mouse motion (first person).
    float look_dy = 0.0f;
    float zoom_steps = 0.0f;      // Wheel notches this frame (positive zooms in).
};

struct CameraSpeeds {
    float pan = 1.0f;  // Multipliers from the settings.
    float rotate = 1.0f;
    float zoom = 1.0f;
};

class Camera {
public:
    // Aerial.
    static constexpr float kMinDistance = 8.0f;
    static constexpr float kMaxDistance = 260.0f;
    static constexpr float kCloseTilt = 28.0f;  // Degrees above the horizon.
    static constexpr float kFarTilt = 68.0f;
    // Third person.
    static constexpr float kOrbitMinDistance = 2.0f;
    static constexpr float kOrbitMaxDistance = 60.0f;
    static constexpr float kOrbitMaxPitch = 85.0f;
    // Looking up: past the angle the ground allows the eye stays on the
    // ground and the view goes on turning up, to the sky (phase 61).
    static constexpr float kOrbitMinPitch = -60.0f;
    static constexpr float kPivotHeight = 1.5f;      // Eye height of the orbit point.
    static constexpr float kOrbitDefaultDistance = 10.0f;
    static constexpr float kOrbitDefaultPitch = 25.0f;
    static constexpr float kGroundClearance = 0.4f;
    // First person.
    static constexpr float kEyeHeight = 1.65f;
    static constexpr float kMaxLookPitch = 85.0f;

    static constexpr float kFovY = 45.0f;

    // Advances the camera by `dt` seconds of real time.
    void update(const CameraInput& input, const CameraSpeeds& speeds, float dt);

    // Switches mode, keeping the point being looked at.
    void set_mode(CameraMode mode);
    [[nodiscard]] CameraMode mode() const { return mode_; }

    // While set, the camera keeps its focus on this ground point (a
    // character's feet); `height` is the character's size factor.
    void set_follow(std::optional<math::Vec3> feet, float height = 1.0f);
    [[nodiscard]] bool following() const { return follow_.has_value(); }

    // Height of the ground at (x, z); flat at 0 until the map exists.
    void set_ground(std::function<float(float, float)> ground);

    // Keeps the focus inside a rectangle on the ground (x, z).
    void set_bounds(float min_x, float min_z, float max_x, float max_z);
    void set_target(math::Vec3 target);
    void set_yaw(float radians);
    void set_distance(float meters);
    // Raises the zoom-out limit (debug stress view); 0 restores the default.
    void set_max_distance_override(float meters);
    // Jumps to the goal state without smoothing.
    void snap();
    // Puts the camera exactly as it was (a map report, phase 38): mode,
    // point looked at, turn, tilt and distance, without smoothing.
    void restore(CameraMode mode, math::Vec3 target, float yaw, float pitch, float distance);

    [[nodiscard]] math::Vec3 eye() const;
    [[nodiscard]] math::Vec3 target() const { return target_; }
    [[nodiscard]] float yaw() const { return yaw_; }
    [[nodiscard]] float pitch() const { return pitch_; }
    // Third person: the elevation of the eye over the point it orbits; over
    // pitch() when the ground keeps the eye from going lower.
    [[nodiscard]] float eye_pitch() const { return eye_pitch_; }
    [[nodiscard]] float distance() const { return distance_; }
    // Aerial tilt above the horizon for the current distance, in radians.
    [[nodiscard]] float tilt() const;
    [[nodiscard]] static float tilt_for_distance(float distance);

    [[nodiscard]] math::Mat4 view() const;
    [[nodiscard]] math::Mat4 projection(float aspect, float far_z) const;
    [[nodiscard]] float near_z() const;
    // Direction the camera looks at.
    [[nodiscard]] math::Vec3 forward() const;

    // Ground directions (y = 0) for the current yaw.
    [[nodiscard]] math::Vec3 forward_on_ground() const;
    [[nodiscard]] math::Vec3 right_on_ground() const;

private:
    [[nodiscard]] float ground(float x, float z) const;
    [[nodiscard]] float focus_height() const;
    [[nodiscard]] math::Vec3 orbit_eye(float pitch, float distance) const;
    void keep_above_ground();

    CameraMode mode_ = CameraMode::Aerial;
    // Current (smoothed) and goal state. In first person, target_ is the
    // point under the viewer's feet.
    math::Vec3 target_{0, 0, 0};
    math::Vec3 goal_target_{0, 0, 0};
    float yaw_ = 0.0f;
    float goal_yaw_ = 0.0f;
    // Third person: how far down the view looks (the orbit's elevation,
    // while the ground lets the eye be there). First person: look up (+) or
    // down (-).
    float pitch_ = 0.5f;
    // Third person: the elevation the eye really is at: `pitch_`, or more
    // where the ground is in the way.
    float eye_pitch_ = 0.5f;
    float goal_pitch_ = 0.5f;
    float distance_ = 60.0f;
    float goal_distance_ = 60.0f;
    float min_x_ = -1e6f, min_z_ = -1e6f, max_x_ = 1e6f, max_z_ = 1e6f;
    float max_distance_ = kMaxDistance;
    std::optional<math::Vec3> follow_;
    float follow_height_ = 1.0f;
    std::function<float(float, float)> ground_;
};

// Distance between a ray and a vertical segment [base.y, base.y + height]
// at (base.x, base.z), and the ray parameter of the closest point. Used to
// pick characters with the mouse.
struct RayHit {
    float distance = 0.0f;
    float t = 0.0f;
};
[[nodiscard]] RayHit ray_to_vertical_segment(math::Vec3 origin, math::Vec3 dir, math::Vec3 base, float height);

}  // namespace sc
