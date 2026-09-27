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
