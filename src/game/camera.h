// Strategy camera in the style of Farthest Frontier: it looks at a point on
// the ground, orbits around it, and tilts from low (close) to steep (far)
// as it zooms. Movement is smoothed. Presentation only, never simulation.
#pragma once

#include "math/vec.h"

namespace sc {

struct CameraInput {
    float move_forward = 0.0f;  // -1..1, from keys or screen edge.
    float move_right = 0.0f;    // -1..1
    float rotate = 0.0f;        // -1..1 from keys (positive turns right).
    float drag_rotate_px = 0.0f;  // Horizontal mouse drag this frame, pixels.
    float zoom_steps = 0.0f;      // Wheel notches this frame (positive zooms in).
};

struct CameraSpeeds {
    float pan = 1.0f;     // Multipliers from the settings.
    float rotate = 1.0f;
    float zoom = 1.0f;
};

class Camera {
public:
    static constexpr float kMinDistance = 8.0f;
    static constexpr float kMaxDistance = 260.0f;
    static constexpr float kCloseTilt = 28.0f;  // Degrees above the horizon.
    static constexpr float kFarTilt = 68.0f;
    static constexpr float kFovY = 45.0f;

    // Advances the camera by `dt` seconds of real time.
    void update(const CameraInput& input, const CameraSpeeds& speeds, float dt);

    // Keeps the target inside a rectangle on the ground (x, z).
    void set_bounds(float min_x, float min_z, float max_x, float max_z);
    void set_target(math::Vec3 target);
    void set_yaw(float radians);
    void set_distance(float meters);
    // Raises the zoom-out limit (debug stress view); 0 restores the default.
    void set_max_distance_override(float meters);
    // Jumps to the goal state without smoothing.
    void snap();

    [[nodiscard]] math::Vec3 eye() const;
    [[nodiscard]] math::Vec3 target() const { return target_; }
    [[nodiscard]] float yaw() const { return yaw_; }
    [[nodiscard]] float distance() const { return distance_; }
    // Tilt above the horizon for the current distance, in radians.
    [[nodiscard]] float tilt() const;
    [[nodiscard]] static float tilt_for_distance(float distance);

    [[nodiscard]] math::Mat4 view() const;
    [[nodiscard]] math::Mat4 projection(float aspect, float far_z) const;
    [[nodiscard]] float near_z() const;

    // Ground directions (y = 0) for the current yaw.
    [[nodiscard]] math::Vec3 forward_on_ground() const;
    [[nodiscard]] math::Vec3 right_on_ground() const;

private:
    // Current (smoothed) and goal state.
    math::Vec3 target_{0, 0, 0};
    math::Vec3 goal_target_{0, 0, 0};
    float yaw_ = 0.0f;
    float goal_yaw_ = 0.0f;
    float distance_ = 60.0f;
    float goal_distance_ = 60.0f;
    float min_x_ = -1e6f, min_z_ = -1e6f, max_x_ = 1e6f, max_z_ = 1e6f;
    float max_distance_ = kMaxDistance;
};

}  // namespace sc
