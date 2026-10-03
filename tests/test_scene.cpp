#include <doctest.h>

#include "render/scene_renderer.h"

using namespace sc;

TEST_SUITE("scene") {
    TEST_CASE("cascade splits grow and end at the shadow distance") {
        float splits[3];
        render::compute_cascade_splits(0.5f, 400.0f, 3, splits);
        CHECK(splits[0] > 0.5f);
        CHECK(splits[0] < splits[1]);
        CHECK(splits[1] < splits[2]);
        CHECK(splits[2] == doctest::Approx(400.0f));
        render::compute_cascade_splits(0.5f, 120.0f, 1, splits);
        CHECK(splits[0] == doctest::Approx(120.0f));
    }

    TEST_CASE("quality levels map to renderer values") {
        CHECK(render::shadow_cascades_for_level(0) == 0);
        CHECK(render::shadow_cascades_for_level(3) == 3);
        CHECK(render::msaa_samples_for_level(0) == 1);
        CHECK(render::msaa_samples_for_level(2) == 4);
        CHECK(render::draw_distance_for_level(0) < render::draw_distance_for_level(3));
        CHECK(render::shadow_map_size_for_level(9) == render::shadow_map_size_for_level(3));
    }
}
