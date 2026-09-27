// Shows a village game: buildings (rising while they are built), the
// natural features the villagers harvest, the villagers themselves and the
// ghost of a building being placed. Presentation only; it reads the game
// and never changes its state (it only takes the "what changed" lists).
#pragma once

#include <cstdint>
#include <filesystem>
#include <map>
#include <optional>
#include <string>
#include <vector>

#include "game/map_scene.h"
#include "game/test_scene.h"
#include "mods/mod_library.h"
#include "render/scene_renderer.h"
#include "sim/game.h"

namespace sc {

class VillageView {
public:
    // Loads one model per building definition (shared by path).
    void load(render::SceneRenderer& renderer, const mods::BuildResult& pack);
    // The villagers' bodies, from the test crowd that already loaded them.
    void set_bodies(const std::vector<TestCrowd::BodyKind>* bodies, std::uint32_t palette_count);

    // Shows a game that just started or was loaded.
    void begin(render::SceneRenderer& renderer, MapScene& scene, sim::Game& game);
    void end(render::SceneRenderer& renderer);

    // Per frame. `alpha` is how far into the next tick the clock is, to
    // draw villagers between their last two positions; `speed` is the
    // game speed (0 when paused).
    void update(render::SceneRenderer& renderer, MapScene& scene, sim::Game& game, float alpha, float dt, int speed);

    struct Ghost {
        sim::DefIndex def = sim::kNoDef;
        std::int32_t x = 0;
        std::int32_t z = 0;
        std::uint8_t rotation = 0;
        bool allowed = false;
        bool operator==(const Ghost&) const = default;
    };
    void set_ghost(std::optional<Ghost> ghost);
    // Winter brings caps; summer, straw hats.
    void set_season(sim::Season season) { season_ = season; }

    [[nodiscard]] std::optional<sim::EntityId> pick_villager(const sim::Game& game, math::Vec3 origin, math::Vec3 dir,
                                                             float alpha) const;
    [[nodiscard]] std::optional<sim::EntityId> pick_building(const sim::Game& game, math::Vec3 origin,
                                                             math::Vec3 dir) const;
    // Where a villager is drawn (feet), for markers and the camera.
    [[nodiscard]] math::Vec3 villager_position(const sim::Game& game, const sim::Villager& v, float alpha) const;
    // Top of a building, for its marker.
    [[nodiscard]] math::Vec3 building_top(const sim::Game& game, const sim::Building& b) const;

private:
    static constexpr render::ModelId kNoModel = ~0u;
    struct Model {
        render::ModelId id = kNoModel;
        float height = 1.0f;
        float width = 1.0f;  // Model size along x and z, meters.
        float depth = 1.0f;
    };
    std::map<std::string, Model> files_;
    std::vector<Model> def_models_;  // By building definition.
    std::vector<render::ModelId> used_;

    struct Look {
        std::uint32_t generation = ~0u;
        float yaw = 0.0f;
        float time = 0.0f;
    };
    std::vector<Look> looks_;  // By villager entity index.
    std::vector<render::CharacterInstance> characters_;
    const std::vector<TestCrowd::BodyKind>* bodies_ = nullptr;
    std::uint32_t palette_count_ = 1;

    std::optional<Ghost> ghost_;
    sim::Season season_ = sim::Season::Summer;
    bool ghost_changed_ = false;
    bool shown_ = false;

    void rebuild_buildings(render::SceneRenderer& renderer, const sim::Game& game);
    [[nodiscard]] render::Instance building_instance(const sim::Game& game, sim::DefIndex def, std::int32_t x,
                                                     std::int32_t z, std::int32_t w, std::int32_t d,
                                                     std::uint8_t rotation, float progress) const;
    void update_characters(render::SceneRenderer& renderer, const sim::Game& game, float alpha, float dt, int speed);
};

}  // namespace sc
