// Renderer test scene for phase 3: a ground plane with forests, villages and
// rocks made of the test models, used to check performance and the camera
// until the procedural map exists (phase 6). Also the main menu backdrop.
#pragma once

#include <cstdint>
#include <filesystem>
#include <optional>
#include <vector>

#include "render/model.h"
#include "render/scene_renderer.h"

namespace sc {

struct TestSceneLayout {
    std::vector<render::Instance> trees;
    std::vector<render::Instance> houses;
    std::vector<render::Instance> rocks;
    [[nodiscard]] std::size_t total() const { return trees.size() + houses.size() + rocks.size(); }
};

inline constexpr float kTestSceneHalfSize = 1000.0f;  // Meters from the center to each edge.

// Places `count` objects, always the same for the same seed.
[[nodiscard]] TestSceneLayout make_test_scene_layout(std::size_t count, std::uint32_t seed);

// A flat ground model with a tiling grass texture.
[[nodiscard]] render::ModelData make_ground_model(float half_size);

class TestScene {
public:
    // Loads the models from data/models/test and fills the renderer.
    // Models that fail to load are skipped (and logged).
    bool load(render::SceneRenderer& renderer, const std::filesystem::path& models_dir, std::size_t count);

    [[nodiscard]] bool loaded() const { return loaded_; }
    [[nodiscard]] std::size_t instance_count() const { return instances_; }

private:
    bool loaded_ = false;
    std::size_t instances_ = 0;
};

}  // namespace sc
