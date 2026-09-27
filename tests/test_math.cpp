#include <doctest.h>

#include "math/vec.h"

using namespace sc::math;

namespace {

bool near(float a, float b, float eps = 1e-4f) {
    return std::abs(a - b) <= eps;
}

bool near(Vec3 a, Vec3 b, float eps = 1e-4f) {
    return near(a.x, b.x, eps) && near(a.y, b.y, eps) && near(a.z, b.z, eps);
}

}  // namespace

TEST_SUITE("math") {
    TEST_CASE("reversed-Z perspective maps near to 1 and far to 0") {
        const Mat4 p = perspective_reverse_z(radians(60.0f), 16.0f / 9.0f, 0.5f, 1000.0f);
        CHECK(near(p.transform_point({0, 0, -0.5f}).z, 1.0f));
        CHECK(near(p.transform_point({0, 0, -1000.0f}).z, 0.0f));
        const float mid = p.transform_point({0, 0, -10.0f}).z;
        CHECK(mid > 0.0f);
        CHECK(mid < 1.0f);
    }

    TEST_CASE("reversed-Z orthographic") {
        const Mat4 o = orthographic_reverse_z(-10, 10, -5, 5, 1, 101);
        CHECK(near(o.transform_point({0, 0, -1}).z, 1.0f));
        CHECK(near(o.transform_point({0, 0, -101}).z, 0.0f));
        CHECK(near(o.transform_point({10, 5, -50}), Vec3{1, 1, o.transform_point({10, 5, -50}).z}));
    }

    TEST_CASE("look_at puts the target straight ahead") {
        const Mat4 v = look_at({10, 20, 30}, {0, 0, 0}, {0, 1, 0});
        const Vec3 t = v.transform_point({0, 0, 0});
        CHECK(near(t.x, 0.0f));
        CHECK(near(t.y, 0.0f));
        CHECK(t.z < 0.0f);
        CHECK(near(t.z, -length({10, 20, 30}), 1e-3f));
    }

    TEST_CASE("inverse undoes a transform") {
        const Mat4 m = translation({3, -2, 5}) * rotation_y(0.7f) * scaling({2, 2, 2});
        const Mat4 i = inverse(m);
        const Vec3 p{1.5f, -4.0f, 2.0f};
        CHECK(near(i.transform_point(m.transform_point(p)), p));
        const Mat4 proj = perspective_reverse_z(1.0f, 1.5f, 0.1f, 500.0f);
        CHECK(near(inverse(proj).transform_point(proj.transform_point({1, 2, -7})), Vec3{1, 2, -7}, 1e-3f));
    }

    TEST_CASE("rotations") {
        CHECK(near(rotation_y(kPi / 2).transform_point({1, 0, 0}), Vec3{0, 0, -1}));
        // A quarter turn around Y as a quaternion.
        const float h = std::sqrt(0.5f);
        CHECK(near(rotation_quat(0, h, 0, h).transform_point({1, 0, 0}), Vec3{0, 0, -1}));
    }

    TEST_CASE("frustum culling of spheres") {
        const Mat4 vp = perspective_reverse_z(radians(60.0f), 1.0f, 0.5f, 100.0f) * look_at({0, 0, 0}, {0, 0, -1}, {0, 1, 0});
        const Frustum f = Frustum::from_matrix(vp);
        CHECK(f.sphere_visible({0, 0, -10}, 1.0f));
        CHECK_FALSE(f.sphere_visible({0, 0, 10}, 1.0f));        // Behind.
        CHECK_FALSE(f.sphere_visible({0, 0, -200}, 1.0f));      // Beyond far.
        CHECK_FALSE(f.sphere_visible({50, 0, -10}, 1.0f));      // Far to the side.
        CHECK(f.sphere_visible({0, 0, -101}, 2.0f));            // Touches the far plane.
        CHECK(f.sphere_visible({6.5f, 0, -10}, 1.0f));          // Straddles the side plane.
    }
}
