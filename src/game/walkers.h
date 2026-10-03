// The people of the game as the renderer has them (the cast), and the ones
// the developer tools place on the map, who wander around where they were
// put.
#pragma once

#include <cstdint>
#include <filesystem>
#include <functional>
#include <optional>
#include <span>
#include <string>
#include <vector>

#include "game/people.h"
#include "render/model.h"
#include "render/scene_renderer.h"

namespace sc {

class Walkers {
public:
    // Loads every race's characters from the core mod's folder.
    bool load(render::SceneRenderer& renderer, const std::filesystem::path& core_dir, const sim::Content& content);
    // Removes everyone.
    void clear();
    // The ground they walk on (flat at 0 if empty).
    void set_ground(std::function<float(float, float)> ground);
    // Moves everyone and hands the result, after `others`, to the renderer.
    void update(render::SceneRenderer& renderer, float dt, std::span<const render::CharacterInstance> others = {});

    [[nodiscard]] bool loaded() const { return cast_.loaded(); }
    [[nodiscard]] std::size_t size() const { return villagers_.size(); }
    // The characters; the village's villagers use the same ones.
    [[nodiscard]] const people::Cast& cast() const { return cast_; }

    // The villager nearest to the ray origin whose body the ray touches.
    [[nodiscard]] std::optional<std::size_t> pick(math::Vec3 origin, math::Vec3 dir) const;
    [[nodiscard]] math::Vec3 position(std::size_t i) const { return villagers_[i].look.position; }

    // For the developer tools.
    struct VillagerInfo {
        std::string model;  // The character's file name.
        std::uint32_t palette = 0;
        bool walking = false;
        float speed = 0.0f;
        float scale = 1.0f;
        float yaw = 0.0f;
        math::Vec3 target;
        math::Vec3 home;
    };
    [[nodiscard]] VillagerInfo info(std::size_t i) const;
    // Adds a villager that wanders around `at`; `female` picks among the
    // characters of that sex (any when empty). Returns its index.
    std::size_t add_villager(math::Vec3 at, std::optional<bool> female);
    void remove_villager(std::size_t i);
    [[nodiscard]] float scale(std::size_t i) const { return villagers_[i].look.scale; }
    // Its height in meters, as drawn.
    [[nodiscard]] float height(std::size_t i) const;

private:
    struct Villager {
        render::CharacterInstance look;
        const people::Body* body = nullptr;
        people::Motion motion;
        math::Vec3 target;
        math::Vec3 home;       // Wanders around this point.
        float roam = 10.0f;    // ... this far.
        float speed = 1.4f;
        float rest_time = 0.0f;  // Seconds left standing still.
    };

    std::uint32_t next_random();
    math::Vec3 random_point(math::Vec3 center, float radius);

    people::Cast cast_;
    std::vector<Villager> villagers_;
    std::vector<render::CharacterInstance> instances_;
    std::uint32_t random_state_ = 1;
    std::function<float(float, float)> ground_;
};

}  // namespace sc
