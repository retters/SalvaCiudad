#include <doctest.h>

#include "game/camera.h"

using namespace sc;

TEST_SUITE("camera") {
    TEST_CASE("the camera tilts down as it zooms out") {
        const float close = Camera::tilt_for_distance(Camera::kMinDistance);
        const float mid = Camera::tilt_for_distance(100.0f);
        const float far = Camera::tilt_for_distance(Camera::kMaxDistance);
        CHECK(close == doctest::Approx(math::radians(Camera::kCloseTilt)));
        CHECK(far == doctest::Approx(math::radians(Camera::kFarTilt)));
        CHECK(close < mid);
        CHECK(mid < far);
    }

    TEST_CASE("ground directions follow the yaw") {
        Camera cam;
        cam.snap();
        CHECK(cam.forward_on_ground().z == doctest::Approx(-1.0f));
        CHECK(cam.right_on_ground().x == doctest::Approx(1.0f));
        cam.set_yaw(math::kPi / 2);
        cam.snap();
        CHECK(cam.forward_on_ground().x == doctest::Approx(1.0f));
        CHECK(math::dot(cam.forward_on_ground(), cam.right_on_ground()) == doctest::Approx(0.0f).epsilon(1e-6));
    }

    TEST_CASE("moving forward goes where the camera looks, and stays in bounds") {
        Camera cam;
        cam.set_bounds(-100, -100, 100, 100);
        cam.set_yaw(math::kPi / 2);  // Looking along +x.
        cam.snap();
        CameraInput in;
        in.move_forward = 1.0f;
        for (int i = 0; i < 30; ++i) {
            cam.update(in, {}, 1.0f / 60.0f);
        }
        CHECK(cam.target().x > 10.0f);
        CHECK(std::abs(cam.target().z) < 0.01f);
        for (int i = 0; i < 600; ++i) {
            cam.update(in, {}, 1.0f / 60.0f);
        }
        CHECK(cam.target().x <= 100.0f);
        CHECK(cam.target().x > 95.0f);
    }

    TEST_CASE("zoom is clamped and the eye stays above the target") {
        Camera cam;
        CameraInput in;
        in.zoom_steps = 100.0f;
        cam.update(in, {}, 0.016f);
        for (int i = 0; i < 200; ++i) {
            cam.update({}, {}, 0.016f);
        }
        CHECK(cam.distance() == doctest::Approx(Camera::kMinDistance).epsilon(0.01));
        in.zoom_steps = -100.0f;
        cam.update(in, {}, 0.016f);
        for (int i = 0; i < 200; ++i) {
            cam.update({}, {}, 0.016f);
        }
        CHECK(cam.distance() == doctest::Approx(Camera::kMaxDistance).epsilon(0.01));
        CHECK(cam.eye().y > cam.target().y);
        CHECK(math::length(cam.eye() - cam.target()) == doctest::Approx(cam.distance()).epsilon(0.001));
    }

    TEST_CASE("smoothing does not depend on the frame rate") {
        Camera a;
        Camera b;
        a.set_target({10, 0, 0});
        b.set_target({10, 0, 0});
        a.update({}, {}, 0.1f);
        for (int i = 0; i < 10; ++i) {
            b.update({}, {}, 0.01f);
        }
        CHECK(a.target().x == doctest::Approx(b.target().x).epsilon(0.001));
    }
}

TEST_SUITE("camera") {
    TEST_CASE("modes cycle aerial, third person, first person") {
        CHECK(next_camera_mode(CameraMode::Aerial) == CameraMode::ThirdPerson);
        CHECK(next_camera_mode(CameraMode::ThirdPerson) == CameraMode::FirstPerson);
        CHECK(next_camera_mode(CameraMode::FirstPerson) == CameraMode::Aerial);
    }

    TEST_CASE("third person never looks from under the ground") {
        Camera cam;
        cam.set_mode(CameraMode::ThirdPerson);
        cam.set_distance(20.0f);
        cam.snap();
        CameraInput in;
        in.drag_pitch_px = -5000.0f;  // Try hard to swing below the ground.
        for (int i = 0; i < 120; ++i) {
            cam.update(in, {}, 1.0f / 60.0f);
            CHECK(cam.eye().y >= Camera::kGroundClearance - 1e-3f);
            in.drag_pitch_px = -50.0f;
        }
        // It still reaches low angles when there is room (pivot at eye height).
        CHECK(cam.pitch() < math::radians(10.0f));
    }

    TEST_CASE("third person keeps the pivot at eye height over bumpy ground") {
        Camera cam;
        cam.set_ground([](float x, float) { return x * 0.1f; });
        cam.set_mode(CameraMode::ThirdPerson);
        cam.set_target({10.0f, 0.0f, 0.0f});
        cam.snap();
        for (int i = 0; i < 200; ++i) {
            cam.update({}, {}, 1.0f / 60.0f);
        }
        CHECK(cam.target().y == doctest::Approx(1.0f + Camera::kPivotHeight).epsilon(0.01));
        CHECK(cam.eye().y >= 1.0f);
    }

    TEST_CASE("first person walks where it looks and clamps the look up and down") {
        Camera cam;
        cam.set_mode(CameraMode::FirstPerson);
        cam.snap();
        CameraInput look;
        look.look_dx = 1.0f / 0.0025f * (math::kPi / 2);  // A quarter turn right.
        cam.update(look, {}, 0.016f);
        CHECK(cam.yaw() == doctest::Approx(math::kPi / 2).epsilon(0.001));
        CameraInput walk;
        walk.move_forward = 1.0f;
        for (int i = 0; i < 60; ++i) {
            cam.update(walk, {}, 1.0f / 60.0f);
        }
        CHECK(cam.target().x > 2.0f);        // Walked along +x.
        CHECK(std::abs(cam.target().z) < 0.01f);
        CHECK(cam.eye().y == doctest::Approx(Camera::kEyeHeight).epsilon(0.01));
        CameraInput up;
        up.look_dy = -100000.0f;
        cam.update(up, {}, 0.016f);
        CHECK(cam.pitch() == doctest::Approx(math::radians(Camera::kMaxLookPitch)));
        CHECK(cam.forward().y > 0.99f);
    }

    TEST_CASE("following overrides moving the focus until it stops") {
        Camera cam;
        cam.set_follow(math::Vec3{30.0f, 0.0f, -12.0f});
        for (int i = 0; i < 200; ++i) {
            cam.update({}, {}, 1.0f / 60.0f);
        }
        CHECK(cam.target().x == doctest::Approx(30.0f).epsilon(0.01));
        CHECK(cam.target().z == doctest::Approx(-12.0f).epsilon(0.01));
        CHECK(cam.following());
        cam.set_follow(std::nullopt);
        CHECK_FALSE(cam.following());
    }

    TEST_CASE("switching modes keeps the focus point") {
        Camera cam;
        cam.set_target({5.0f, 0.0f, 7.0f});
        cam.snap();
        cam.set_mode(CameraMode::ThirdPerson);
        for (int i = 0; i < 200; ++i) {
            cam.update({}, {}, 1.0f / 60.0f);
        }
        CHECK(cam.target().x == doctest::Approx(5.0f).epsilon(0.01));
        cam.set_mode(CameraMode::Aerial);
        for (int i = 0; i < 200; ++i) {
            cam.update({}, {}, 1.0f / 60.0f);
        }
        CHECK(cam.distance() >= Camera::kMinDistance);
        CHECK(cam.target().y == doctest::Approx(0.0f).epsilon(0.01));
    }

    TEST_CASE("rays pick a standing character") {
        // Looking straight at a 1.8 m figure 10 m away.
        const RayHit hit = ray_to_vertical_segment({0, 1, 10}, {0, 0, -1}, {0, 0, 0}, 1.8f);
        CHECK(hit.distance == doctest::Approx(0.0f));
        CHECK(hit.t == doctest::Approx(10.0f));
        // Passing over its head.
        const RayHit over = ray_to_vertical_segment({0, 3, 10}, {0, 0, -1}, {0, 0, 0}, 1.8f);
        CHECK(over.distance == doctest::Approx(1.2f));
        // From above, as the aerial camera looks.
        const RayHit down = ray_to_vertical_segment({0.2f, 50, 0}, {0, -1, 0}, {0, 0, 0}, 1.8f);
        CHECK(down.distance == doctest::Approx(0.2f));
    }
}
