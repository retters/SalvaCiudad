// The villagers' bodies and the people placed with the developer tools.
#pragma once

#include <cstdint>
#include <filesystem>
#include <functional>
#include <optional>
#include <span>
#include <string>
#include <vector>

#include "render/model.h"
#include "render/scene_renderer.h"

namespace sc {

// The villagers' palettes: outfits x skin tones x hair colors.
[[nodiscard]] std::vector<render::Palette> make_villager_palettes();

// The villagers' bodies (one per race and sex, with their clips and
// accessories), and the people the developer tools place on the map, who
// wander around where they were put.
class Walkers {
public:
    // Loads the bodies and accessories from the core mod's folder. Bodies
    // of each race in `bodies` (see sim::race_body_file); missing races are
    // skipped.
    bool load(render::SceneRenderer& renderer, const std::filesystem::path& core_dir,
              const std::vector<std::string>& bodies = {"human"});
    // Removes everyone.
    void clear();
    // The ground they walk on (flat at 0 if empty).
    void set_ground(std::function<float(float, float)> ground);
    // Moves everyone and hands the result, after `others`, to the renderer.
    void update(render::SceneRenderer& renderer, float dt, std::span<const render::CharacterInstance> others = {});

    [[nodiscard]] bool loaded() const { return loaded_; }
    [[nodiscard]] std::size_t size() const { return villagers_.size(); }

    // The villager nearest to the ray origin whose body the ray touches.
    [[nodiscard]] std::optional<std::size_t> pick(math::Vec3 origin, math::Vec3 dir) const;
    [[nodiscard]] math::Vec3 position(std::size_t i) const { return villagers_[i].look.position; }

    // For the developer tools.
    struct VillagerInfo {
        bool female = false;
        std::uint32_t palette = 0;
        bool walking = false;
        float speed = 0.0f;
        float scale = 1.0f;
        float yaw = 0.0f;
        math::Vec3 target;
        math::Vec3 home;
        bool hat = false;
        bool beard = false;
        bool apron = false;
    };
    [[nodiscard]] VillagerInfo info(std::size_t i) const;
    // Adds a villager that wanders around `at`; `female` picks the body
    // (random when empty). Returns its index.
    std::size_t add_villager(math::Vec3 at, std::optional<bool> female);
    void remove_villager(std::size_t i);
    [[nodiscard]] float scale(std::size_t i) const { return villagers_[i].look.scale; }
    // A villager not drawn (the one seen through in first person).
    void set_hidden(std::optional<std::size_t> i) { hidden_ = i; }

    // Walking speed at which the walk clip plays at its authored rate.
    static constexpr float kWalkReferenceSpeed = 1.45f;

    // A loaded body with its clips and accessories; the village's
    // villagers use the same ones.
    struct BodyKind {
        bool female = false;
        std::string body = "human";  // The race's body files (phase 19).
        render::SkinnedId id = 0;
        std::uint32_t idle = 0;
        std::uint32_t walk = 0;
        std::vector<std::uint32_t> hats;  // Accessory bits.
        std::uint32_t beard = ~0u;
        std::uint32_t apron = ~0u;
    };
    [[nodiscard]] const std::vector<BodyKind>& bodies() const { return kinds_; }

private:
    struct Villager {
        render::CharacterInstance look;
        std::size_t kind = 0;
        math::Vec3 target;
        math::Vec3 home;       // Wanders around this point.
        float roam = 10.0f;    // ... this far.
        float speed = 1.4f;
        float rest_time = 0.0f;  // Seconds left standing still.
    };

    std::uint32_t next_random();
    math::Vec3 random_point(math::Vec3 center, float radius);
    Villager make_villager(std::size_t kind, math::Vec3 home, float roam);

    bool loaded_ = false;
    std::vector<BodyKind> kinds_;
    std::vector<Villager> villagers_;
    std::vector<render::CharacterInstance> instances_;
    std::uint32_t random_state_ = 1;
    std::function<float(float, float)> ground_;
    std::optional<std::size_t> hidden_;
};

}  // namespace sc
