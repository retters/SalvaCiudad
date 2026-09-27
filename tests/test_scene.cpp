#include <doctest.h>

#include "game/test_scene.h"
#include "render/scene_renderer.h"

using namespace sc;

TEST_SUITE("scene") {
    TEST_CASE("the test layout is reproducible and inside the area") {
        const TestSceneLayout a = make_test_scene_layout(50'000, 2026);
        const TestSceneLayout b = make_test_scene_layout(50'000, 2026);
        CHECK(a.total() == 50'000);
        REQUIRE(a.trees.size() == b.trees.size());
        for (std::size_t i = 0; i < a.trees.size(); i += 997) {
            CHECK(a.trees[i].position == b.trees[i].position);
        }
        for (const auto* list : {&a.trees, &a.houses, &a.rocks}) {
            for (const render::Instance& inst : *list) {
                CHECK(std::abs(inst.position.x) <= kTestSceneHalfSize);
                CHECK(std::abs(inst.position.z) <= kTestSceneHalfSize);
                CHECK(inst.scale > 0.0f);
            }
        }
        const TestSceneLayout c = make_test_scene_layout(50'000, 7);
        CHECK_FALSE(c.trees[0].position == a.trees[0].position);
    }

    TEST_CASE("the ground faces up and its indices are valid") {
        const render::ModelData g = make_ground_model(100.0f);
        REQUIRE(g.indices.size() % 3 == 0);
        for (std::size_t i = 0; i < g.indices.size(); i += 3) {
            const auto& a = g.vertices[g.indices[i]];
            const auto& b = g.vertices[g.indices[i + 1]];
            const auto& c = g.vertices[g.indices[i + 2]];
            const math::Vec3 n = math::cross({b.px - a.px, b.py - a.py, b.pz - a.pz}, {c.px - a.px, c.py - a.py, c.pz - a.pz});
            CHECK(n.y > 0.0f);
        }
        CHECK(g.textures.size() == 1);
        CHECK(g.textures[0].rgba.size() == 64u * 64u * 4u);
    }

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
