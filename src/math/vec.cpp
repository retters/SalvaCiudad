#include "math/vec.h"

namespace sc::math {

Mat4 Mat4::operator*(const Mat4& o) const {
    Mat4 r;
    for (int c = 0; c < 4; ++c) {
        for (int row = 0; row < 4; ++row) {
            float sum = 0.0f;
            for (int k = 0; k < 4; ++k) {
                sum += m[k][row] * o.m[c][k];
            }
            r.m[c][row] = sum;
        }
    }
    return r;
}

Vec4 Mat4::operator*(Vec4 v) const {
    return {m[0][0] * v.x + m[1][0] * v.y + m[2][0] * v.z + m[3][0] * v.w,
            m[0][1] * v.x + m[1][1] * v.y + m[2][1] * v.z + m[3][1] * v.w,
            m[0][2] * v.x + m[1][2] * v.y + m[2][2] * v.z + m[3][2] * v.w,
            m[0][3] * v.x + m[1][3] * v.y + m[2][3] * v.z + m[3][3] * v.w};
}

Vec3 Mat4::transform_point(Vec3 p) const {
    const Vec4 r = (*this) * Vec4{p.x, p.y, p.z, 1.0f};
    const float inv_w = r.w != 0.0f ? 1.0f / r.w : 1.0f;
    return {r.x * inv_w, r.y * inv_w, r.z * inv_w};
}

Vec3 Mat4::transform_vector(Vec3 v) const {
    const Vec4 r = (*this) * Vec4{v.x, v.y, v.z, 0.0f};
    return {r.x, r.y, r.z};
}

Mat4 translation(Vec3 t) {
    Mat4 r = Mat4::identity();
    r.m[3][0] = t.x;
    r.m[3][1] = t.y;
    r.m[3][2] = t.z;
    return r;
}

Mat4 scaling(Vec3 s) {
    Mat4 r;
    r.m[0][0] = s.x;
    r.m[1][1] = s.y;
    r.m[2][2] = s.z;
    r.m[3][3] = 1.0f;
    return r;
}

Mat4 rotation_y(float a) {
    Mat4 r = Mat4::identity();
    const float c = std::cos(a);
    const float s = std::sin(a);
    r.m[0][0] = c;
    r.m[0][2] = -s;
    r.m[2][0] = s;
    r.m[2][2] = c;
    return r;
}

Mat4 rotation_quat(float x, float y, float z, float w) {
    Mat4 r = Mat4::identity();
    r.m[0][0] = 1 - 2 * (y * y + z * z);
    r.m[0][1] = 2 * (x * y + z * w);
    r.m[0][2] = 2 * (x * z - y * w);
    r.m[1][0] = 2 * (x * y - z * w);
    r.m[1][1] = 1 - 2 * (x * x + z * z);
    r.m[1][2] = 2 * (y * z + x * w);
    r.m[2][0] = 2 * (x * z + y * w);
    r.m[2][1] = 2 * (y * z - x * w);
    r.m[2][2] = 1 - 2 * (x * x + y * y);
    return r;
}

Mat4 look_at(Vec3 eye, Vec3 target, Vec3 up) {
    const Vec3 f = normalize(target - eye);
    const Vec3 s = normalize(cross(f, up));
    const Vec3 u = cross(s, f);
    Mat4 r = Mat4::identity();
    r.m[0][0] = s.x;
    r.m[1][0] = s.y;
    r.m[2][0] = s.z;
    r.m[0][1] = u.x;
    r.m[1][1] = u.y;
    r.m[2][1] = u.z;
    r.m[0][2] = -f.x;
    r.m[1][2] = -f.y;
    r.m[2][2] = -f.z;
    r.m[3][0] = -dot(s, eye);
    r.m[3][1] = -dot(u, eye);
    r.m[3][2] = dot(f, eye);
    return r;
}

Mat4 perspective_reverse_z(float fov_y, float aspect, float near_z, float far_z) {
    const float f = 1.0f / std::tan(fov_y * 0.5f);
    Mat4 r;
    r.m[0][0] = f / aspect;
    r.m[1][1] = f;
    // View-space z is negative in front of the camera. depth = A + B / -z,
    // with depth(near) = 1 and depth(far) = 0.
    r.m[2][2] = near_z / (far_z - near_z);
    r.m[2][3] = -1.0f;
    r.m[3][2] = far_z * near_z / (far_z - near_z);
    return r;
}

Mat4 orthographic_reverse_z(float left, float right, float bottom, float top, float near_z, float far_z) {
    Mat4 r = Mat4::identity();
    r.m[0][0] = 2.0f / (right - left);
    r.m[1][1] = 2.0f / (top - bottom);
    r.m[3][0] = -(right + left) / (right - left);
    r.m[3][1] = -(top + bottom) / (top - bottom);
    // z_view = -near -> 1, z_view = -far -> 0.
    r.m[2][2] = 1.0f / (far_z - near_z);
    r.m[3][2] = far_z / (far_z - near_z);
    return r;
}

Mat4 inverse(const Mat4& mat) {
    // Cofactor expansion on the flattened column-major array.
    const float* m = &mat.m[0][0];
    float inv[16];
    inv[0] = m[5] * m[10] * m[15] - m[5] * m[11] * m[14] - m[9] * m[6] * m[15] + m[9] * m[7] * m[14] +
             m[13] * m[6] * m[11] - m[13] * m[7] * m[10];
    inv[4] = -m[4] * m[10] * m[15] + m[4] * m[11] * m[14] + m[8] * m[6] * m[15] - m[8] * m[7] * m[14] -
             m[12] * m[6] * m[11] + m[12] * m[7] * m[10];
    inv[8] = m[4] * m[9] * m[15] - m[4] * m[11] * m[13] - m[8] * m[5] * m[15] + m[8] * m[7] * m[13] +
             m[12] * m[5] * m[11] - m[12] * m[7] * m[9];
    inv[12] = -m[4] * m[9] * m[14] + m[4] * m[10] * m[13] + m[8] * m[5] * m[14] - m[8] * m[6] * m[13] -
              m[12] * m[5] * m[10] + m[12] * m[6] * m[9];
    inv[1] = -m[1] * m[10] * m[15] + m[1] * m[11] * m[14] + m[9] * m[2] * m[15] - m[9] * m[3] * m[14] -
             m[13] * m[2] * m[11] + m[13] * m[3] * m[10];
    inv[5] = m[0] * m[10] * m[15] - m[0] * m[11] * m[14] - m[8] * m[2] * m[15] + m[8] * m[3] * m[14] +
             m[12] * m[2] * m[11] - m[12] * m[3] * m[10];
    inv[9] = -m[0] * m[9] * m[15] + m[0] * m[11] * m[13] + m[8] * m[1] * m[15] - m[8] * m[3] * m[13] -
             m[12] * m[1] * m[11] + m[12] * m[3] * m[9];
    inv[13] = m[0] * m[9] * m[14] - m[0] * m[10] * m[13] - m[8] * m[1] * m[14] + m[8] * m[2] * m[13] +
              m[12] * m[1] * m[10] - m[12] * m[2] * m[9];
    inv[2] = m[1] * m[6] * m[15] - m[1] * m[7] * m[14] - m[5] * m[2] * m[15] + m[5] * m[3] * m[14] +
             m[13] * m[2] * m[7] - m[13] * m[3] * m[6];
    inv[6] = -m[0] * m[6] * m[15] + m[0] * m[7] * m[14] + m[4] * m[2] * m[15] - m[4] * m[3] * m[14] -
             m[12] * m[2] * m[7] + m[12] * m[3] * m[6];
    inv[10] = m[0] * m[5] * m[15] - m[0] * m[7] * m[13] - m[4] * m[1] * m[15] + m[4] * m[3] * m[13] +
              m[12] * m[1] * m[7] - m[12] * m[3] * m[5];
    inv[14] = -m[0] * m[5] * m[14] + m[0] * m[6] * m[13] + m[4] * m[1] * m[14] - m[4] * m[2] * m[13] -
              m[12] * m[1] * m[6] + m[12] * m[2] * m[5];
    inv[3] = -m[1] * m[6] * m[11] + m[1] * m[7] * m[10] + m[5] * m[2] * m[11] - m[5] * m[3] * m[10] -
             m[9] * m[2] * m[7] + m[9] * m[3] * m[6];
    inv[7] = m[0] * m[6] * m[11] - m[0] * m[7] * m[10] - m[4] * m[2] * m[11] + m[4] * m[3] * m[10] +
             m[8] * m[2] * m[7] - m[8] * m[3] * m[6];
    inv[11] = -m[0] * m[5] * m[11] + m[0] * m[7] * m[9] + m[4] * m[1] * m[11] - m[4] * m[3] * m[9] -
              m[8] * m[1] * m[7] + m[8] * m[3] * m[5];
    inv[15] = m[0] * m[5] * m[10] - m[0] * m[6] * m[9] - m[4] * m[1] * m[10] + m[4] * m[2] * m[9] +
              m[8] * m[1] * m[6] - m[8] * m[2] * m[5];
    float det = m[0] * inv[0] + m[1] * inv[4] + m[2] * inv[8] + m[3] * inv[12];
    Mat4 r;
    if (det == 0.0f) {
        return r;
    }
    det = 1.0f / det;
    float* out = &r.m[0][0];
    for (int i = 0; i < 16; ++i) {
        out[i] = inv[i] * det;
    }
    return r;
}

Frustum Frustum::from_matrix(const Mat4& vp) {
    // Rows of the matrix (row-vector view of column-major storage).
    const auto row = [&](int r) { return Vec4{vp.m[0][r], vp.m[1][r], vp.m[2][r], vp.m[3][r]}; };
    const Vec4 r0 = row(0), r1 = row(1), r2 = row(2), r3 = row(3);
    const auto add = [](Vec4 a, Vec4 b) { return Vec4{a.x + b.x, a.y + b.y, a.z + b.z, a.w + b.w}; };
    const auto sub = [](Vec4 a, Vec4 b) { return Vec4{a.x - b.x, a.y - b.y, a.z - b.z, a.w - b.w}; };
    Frustum f;
    f.planes[0] = add(r3, r0);  // Left:   x >= -w
    f.planes[1] = sub(r3, r0);  // Right:  x <= w
    f.planes[2] = add(r3, r1);  // Bottom: y >= -w
    f.planes[3] = sub(r3, r1);  // Top:    y <= w
    f.planes[4] = r2;           // Far (reversed Z): z >= 0
    f.planes[5] = sub(r3, r2);  // Near (reversed Z): z <= w
    for (Vec4& p : f.planes) {
        const float len = std::sqrt(p.x * p.x + p.y * p.y + p.z * p.z);
        if (len > 0.0f) {
            p = {p.x / len, p.y / len, p.z / len, p.w / len};
        }
    }
    return f;
}

bool Frustum::sphere_visible(Vec3 c, float radius) const {
    for (const Vec4& p : planes) {
        if (p.x * c.x + p.y * c.y + p.z * c.z + p.w < -radius) {
            return false;
        }
    }
    return true;
}

}  // namespace sc::math
