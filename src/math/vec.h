// Float vectors and matrices for the presentation side (render, camera).
// Never used by the simulation, which is fixed-point (section 7.3).
//
// Conventions: right-handed world, Y up, meters. Matrices are column-major
// (m[column][row]) and multiply column vectors: p' = M * p. Clip space
// follows the SDL GPU API: depth in [0, 1], with reversed Z (near = 1,
// far = 0) for precision on large maps.
#pragma once

#include <cmath>

namespace sc::math {

inline constexpr float kPi = 3.14159265358979323846f;

[[nodiscard]] constexpr float radians(float degrees) { return degrees * kPi / 180.0f; }

struct Vec2 {
    float x = 0, y = 0;
};

struct Vec3 {
    float x = 0, y = 0, z = 0;

    constexpr Vec3 operator+(Vec3 o) const { return {x + o.x, y + o.y, z + o.z}; }
    constexpr Vec3 operator-(Vec3 o) const { return {x - o.x, y - o.y, z - o.z}; }
    constexpr Vec3 operator*(float s) const { return {x * s, y * s, z * s}; }
    constexpr Vec3 operator-() const { return {-x, -y, -z}; }
    constexpr Vec3& operator+=(Vec3 o) { x += o.x; y += o.y; z += o.z; return *this; }
    constexpr bool operator==(const Vec3&) const = default;
};

struct Vec4 {
    float x = 0, y = 0, z = 0, w = 0;
};

[[nodiscard]] constexpr float dot(Vec3 a, Vec3 b) { return a.x * b.x + a.y * b.y + a.z * b.z; }
[[nodiscard]] constexpr Vec3 cross(Vec3 a, Vec3 b) {
    return {a.y * b.z - a.z * b.y, a.z * b.x - a.x * b.z, a.x * b.y - a.y * b.x};
}
[[nodiscard]] inline float length(Vec3 v) { return std::sqrt(dot(v, v)); }
[[nodiscard]] inline Vec3 normalize(Vec3 v) {
    const float len = length(v);
    return len > 0.0f ? v * (1.0f / len) : Vec3{0, 0, 0};
}
[[nodiscard]] constexpr Vec3 lerp(Vec3 a, Vec3 b, float t) { return a + (b - a) * t; }
[[nodiscard]] constexpr float lerp(float a, float b, float t) { return a + (b - a) * t; }

struct Mat4 {
    float m[4][4] = {};  // m[column][row]

    [[nodiscard]] static constexpr Mat4 identity() {
        Mat4 r;
        r.m[0][0] = r.m[1][1] = r.m[2][2] = r.m[3][3] = 1.0f;
        return r;
    }
    [[nodiscard]] Mat4 operator*(const Mat4& o) const;
    [[nodiscard]] Vec4 operator*(Vec4 v) const;
    [[nodiscard]] Vec3 transform_point(Vec3 p) const;   // Divides by w.
    [[nodiscard]] Vec3 transform_vector(Vec3 v) const;  // Ignores translation.
};

[[nodiscard]] Mat4 translation(Vec3 t);
[[nodiscard]] Mat4 scaling(Vec3 s);
[[nodiscard]] Mat4 rotation_y(float radians);
// Rotation from a unit quaternion (x, y, z, w), as glTF stores it.
[[nodiscard]] Mat4 rotation_quat(float x, float y, float z, float w);
[[nodiscard]] Mat4 look_at(Vec3 eye, Vec3 target, Vec3 up);
// Perspective with reversed depth: near maps to 1, far to 0.
[[nodiscard]] Mat4 perspective_reverse_z(float fov_y, float aspect, float near_z, float far_z);
// Orthographic with reversed depth, for shadow maps.
[[nodiscard]] Mat4 orthographic_reverse_z(float left, float right, float bottom, float top, float near_z, float far_z);
[[nodiscard]] Mat4 inverse(const Mat4& m);

// Six planes (a, b, c, d) with normals pointing inward: a point is inside
// when a*x + b*y + c*z + d >= 0 for all of them.
struct Frustum {
    Vec4 planes[6];

    [[nodiscard]] static Frustum from_matrix(const Mat4& view_proj);
    [[nodiscard]] bool sphere_visible(Vec3 center, float radius) const;
};

}  // namespace sc::math
