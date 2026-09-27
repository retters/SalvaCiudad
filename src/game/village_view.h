// Shows a village game: buildings (rising while they are built), the
// natural features the villagers harvest, the villagers themselves and the
// ghost of a building being placed. Presentation only; it reads the game
// and never changes its state (it only takes the "what changed" lists).
#pragma once

#include <array>
#include <cstdint>
#include <filesystem>
#include <map>
#include <optional>
#include <span>
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
    // The villagers drawn by the last update().
    [[nodiscard]] std::span<const render::CharacterInstance> characters() const { return characters_; }

    struct Ghost {
        sim::DefIndex def = sim::kNoDef;
        std::int32_t x = 0;
        std::int32_t z = 0;
        std::uint8_t rotation = 0;
        bool allowed = false;
        bool operator==(const Ghost&) const = default;
    };
    void set_ghost(std::optional<Ghost> ghost);
    // Phase 17: a map layer (GameHud's list; 0 = none) for a town, drawn
    // around (x, z), where the camera looks.
    void set_overlay(int layer) {
        overlay_ = layer;
        overlay_timer_ = 0.0f;
    }
    void set_view(float x, float z, std::uint8_t town) {
        view_x_ = x;
        view_z_ = z;
        town_ = town;
    }
    // A field being marked out (x, z, w, d in cells), green if it fits.
    struct FieldGhost {
        std::int32_t x = 0, z = 0, w = 0, d = 0;
        bool allowed = false;
        bool operator==(const FieldGhost&) const = default;
    };
    void set_field_ghost(std::optional<FieldGhost> ghost);
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
    std::optional<FieldGhost> field_ghost_;
    // Fields: a soil slab and a plant per 2 m, made in code.
    render::ModelId tile_model_ = kNoModel;
    render::ModelId plant_model_ = kNoModel;
    // Animals: one low-poly body for all kinds (phase 18 brings real ones),
    // and a red mark under raiders.
    render::ModelId animal_model_ = kNoModel;  // The fallback body for animals without a model.
    // Deer, boar, wolf and bear (models/animals in core), if found.
    std::array<render::ModelId, 4> species_models_{kNoModel, kNoModel, kNoModel, kNoModel};
    std::array<std::vector<render::Instance>, 4> species_;
    render::ModelId mark_model_ = kNoModel;
    render::ModelId overlay_model_ = kNoModel;
    int overlay_ = 0;
    float overlay_timer_ = 0.0f;
    float view_x_ = 0.0f;
    float view_z_ = 0.0f;
    std::uint8_t town_ = 0;
    std::vector<render::Instance> overlay_tiles_;
    // Particles (phase 18): chimney smoke and fires, made of small puffs.
    struct Particle {
        math::Vec3 position;
        math::Vec3 velocity;
        float age = 0.0f;
        float life = 1.0f;
        float size0 = 0.3f;
        float size1 = 1.0f;
        math::Vec3 color0;
        math::Vec3 color1;
    };
    render::ModelId puff_model_ = kNoModel;
    std::vector<Particle> particles_;
    std::vector<render::Instance> puffs_;
    std::uint32_t particle_seed_ = 12345u;
    float emit_timer_ = 0.0f;
    [[nodiscard]] float random01();
    void update_particles(render::SceneRenderer& renderer, const sim::Game& game, float dt, int speed);
    void update_overlay(render::SceneRenderer& renderer, const sim::Game& game, float dt);
    std::vector<render::Instance> animals_;
    std::vector<render::Instance> marks_;
    void update_creatures(render::SceneRenderer& renderer, const sim::Game& game, float alpha, float dt, int speed);
    void rebuild_fields(render::SceneRenderer& renderer, const sim::Game& game);
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
