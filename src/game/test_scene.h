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

// The palettes used by the test crowd: outfits x skin tones x hair colors.
[[nodiscard]] std::vector<render::Palette> make_villager_palettes();

// Villagers wandering around the center of the test scene, to check the
// animated character path (phase 4 acceptance: 2000 on screen).
class TestCrowd {
public:
    // Loads the bodies and accessories from data/models/characters.
    bool load(render::SceneRenderer& renderer, const std::filesystem::path& characters_dir);
    void spawn(std::size_t count, std::uint32_t seed, float radius);
    // Moves everyone and hands the result to the renderer.
    void update(render::SceneRenderer& renderer, float dt);

    [[nodiscard]] bool loaded() const { return loaded_; }
    [[nodiscard]] std::size_t size() const { return villagers_.size(); }

    // The villager nearest to the ray origin whose body the ray touches.
    [[nodiscard]] std::optional<std::size_t> pick(math::Vec3 origin, math::Vec3 dir) const;
    [[nodiscard]] math::Vec3 position(std::size_t i) const { return villagers_[i].look.position; }
    [[nodiscard]] float scale(std::size_t i) const { return villagers_[i].look.scale; }
    // A villager not drawn (the one seen through in first person).
    void set_hidden(std::optional<std::size_t> i) { hidden_ = i; }

    // Walking speed at which the walk clip plays at its authored rate.
    static constexpr float kWalkReferenceSpeed = 1.45f;

private:
    struct BodyKind {
        render::SkinnedId id = 0;
        std::uint32_t idle = 0;
        std::uint32_t walk = 0;
        std::vector<std::uint32_t> hats;  // Accessory bits.
        std::uint32_t beard = ~0u;
        std::uint32_t apron = ~0u;
    };
    struct Villager {
        render::CharacterInstance look;
        std::size_t kind = 0;
        math::Vec3 target;
        float speed = 1.4f;
        float rest_time = 0.0f;  // Seconds left standing still.
    };

    std::uint32_t next_random();
    math::Vec3 random_point();

    bool loaded_ = false;
    std::vector<BodyKind> kinds_;
    std::vector<Villager> villagers_;
    std::vector<render::CharacterInstance> instances_;
    std::uint32_t random_state_ = 1;
    float radius_ = 60.0f;
    std::optional<std::size_t> hidden_;
};

class TestScene {
public:
    // Loads the props from data/models/props and fills the renderer.
    // Models that fail to load are skipped (and logged).
    bool load(render::SceneRenderer& renderer, const std::filesystem::path& models_dir, std::size_t count);

    [[nodiscard]] bool loaded() const { return loaded_; }
    [[nodiscard]] std::size_t instance_count() const { return instances_; }

    // Takes the scene out of the renderer (while a map is shown) or puts it
    // back.
    void set_visible(render::SceneRenderer& renderer, bool visible);

private:
    struct Placed {
        render::ModelId model = 0;
        std::vector<render::Instance> instances;
    };
    bool loaded_ = false;
    bool visible_ = true;
    std::size_t instances_ = 0;
    std::vector<Placed> placed_;
};

// Reads and validates one .glb from disk (models only come from the game's
// data folder, decision D-302).
[[nodiscard]] std::optional<render::ModelData> load_model_file(const std::filesystem::path& file);

}  // namespace sc
