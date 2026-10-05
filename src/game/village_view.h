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

#include "game/ambient_fauna.h"
#include "game/ground_cover.h"
#include "game/animal_motion.h"
#include "game/fog_view.h"
#include "game/map_scene.h"
#include "game/people.h"
#include "game/walkers.h"
#include "mods/mod_library.h"
#include "render/scene_renderer.h"
#include "sim/game.h"

namespace sc {

class VillageView {
public:
    // Loads one model per building definition (shared by path).
    void load(render::SceneRenderer& renderer, const mods::BuildResult& pack);
    // The characters, loaded by the app (game/walkers.h).
    void set_cast(const people::Cast* cast) { cast_ = cast; }

    // Shows a game that just started or was loaded.
    void begin(render::SceneRenderer& renderer, MapScene& scene, sim::Game& game);
    void end(render::SceneRenderer& renderer);

    // Per frame. `alpha` is how far into the next tick the clock is, to
    // draw villagers between their last two positions; `speed` is the
    // game speed (0 when paused).
    void update(render::SceneRenderer& renderer, MapScene& scene, sim::Game& game, float alpha, float dt, float speed);
    // The villagers drawn by the last update().
    [[nodiscard]] std::span<const render::CharacterInstance> characters() const { return characters_; }

    // Phase 61. Where a villager's feet are now and how tall it is drawn
    // (1: a body of 1.8 m), for the camera that follows it; nothing if it
    // is gone or under the fog.
    struct Standing {
        math::Vec3 feet;
        float height = 1.0f;
    };
    [[nodiscard]] std::optional<Standing> standing(const sim::Game& game, sim::EntityId villager, float alpha) const;
    // A villager not drawn: the one the first-person camera looks from.
    void set_hidden_villager(sim::EntityId id) { hidden_villager_ = id; }
    // The ghost of the camera's anchor: a pale see-through villager where
    // the third-person camera turns around when it follows nobody. `speed`
    // is how fast the anchor moves, in meters per second of real time.
    struct AnchorGhost {
        math::Vec3 feet;
        float yaw = 0.0f;
        float speed = 0.0f;
    };
    void set_anchor_ghost(std::optional<AnchorGhost> ghost) { anchor_ghost_ = ghost; }
    // The buildings drawn see-through, and how much (quarters, up to
    // render::kMaxFade): those in the camera's way.
    struct Fade {
        sim::EntityId building;
        std::uint8_t level = 0;
    };
    void set_faded_buildings(std::vector<Fade> fades) {
        faded_ = std::move(fades);
        ghost_changed_ = true;
    }
    // How high a building reaches as it is drawn now (y of its top); 0 if
    // it is not drawn.
    [[nodiscard]] float building_roof(const sim::Game& game, const sim::Building& b) const;

    struct Ghost {
        sim::DefIndex def = sim::kNoDef;
        std::int32_t x = 0;
        std::int32_t z = 0;
        std::uint8_t rotation = 0;
        bool allowed = false;
        bool operator==(const Ghost&) const = default;
    };
    void set_ghost(std::optional<Ghost> ghost);
    // Phase 93: the modules of a line being traced, each allowed or not.
    void set_trace(std::vector<Ghost> modules);
    // Phase 17: a map layer (GameHud's list; 0 = none) for a town, drawn
    // around (x, z), where the camera looks.
    void set_overlay(int layer) {
        overlay_ = layer;
        overlay_timer_ = 0.0f;
    }
    // Phase 92: somebody died at (x, z): carrion birds gather there a while.
    void note_death(const sim::Game& game, float x, float z) { fauna_.note_death(game, x, z); }
    [[nodiscard]] std::size_t ambient_animals() const { return fauna_.shown(); }
    // Phase 91: the "ground detail" setting, 0 (nothing dresses the ground) to 3.
    void set_ground_detail(int detail) { ground_detail_ = detail; }
    // Phase 97: how much it rains or snows on screen now, 0 to 1 (it eases
    // in and out), for the light and the sound; `false`: nothing falls
    // (a report shows a moment of a game, not its weather).
    [[nodiscard]] float wet() const { return wet_; }
    [[nodiscard]] bool snow_falling() const { return flakes_falling_; }
    void set_weather_shown(bool shown) { weather_shown_ = shown; }
    // How far the camera is from what it looks at, in meters: the rain is
    // drawn thicker from far, or it would not be seen.
    void set_view_distance(float meters) { view_distance_ = meters; }
    [[nodiscard]] std::size_t ground_cover_shown() const { return cover_.shown(); }
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
    // Phase 32: what the local player sees; null shows everything. What is
    // not theirs shows only where the fog lets it.
    void set_fog(const FogView* fog) {
        if (fog != fog_) {
            fog_ = fog;
            ghost_changed_ = true;
        }
    }
    // Whether a building, or something that moves at (x, z) and belongs to
    // `town` (or to nobody), is shown to the local player.
    [[nodiscard]] bool building_shown(const sim::Game& game, const sim::Building& b) const;
    [[nodiscard]] bool mover_shown(const sim::Game& game, bool owned, std::uint8_t town, float x, float z) const;
    // Phase 34: a building of others nobody explored around that still
    // shows, as a silhouette, because it stands over the fog's ceiling or
    // is a landmark. Never selectable.
    [[nodiscard]] bool building_silhouette(const sim::Game& game, const sim::Building& b) const;

    [[nodiscard]] std::optional<sim::EntityId> pick_villager(const sim::Game& game, math::Vec3 origin, math::Vec3 dir,
                                                             float alpha) const;
    [[nodiscard]] std::optional<sim::EntityId> pick_building(const sim::Game& game, math::Vec3 origin,
                                                             math::Vec3 dir) const;
    // Phase 63: an animal, soldier or raider in view, and a natural feature
    // (its index in the map's list) on explored ground.
    [[nodiscard]] std::optional<sim::EntityId> pick_creature(const sim::Game& game, math::Vec3 origin, math::Vec3 dir,
                                                             float alpha) const;
    [[nodiscard]] std::optional<std::uint32_t> pick_feature(const sim::Game& game, math::Vec3 origin,
                                                            math::Vec3 dir) const;
    // Where a creature is drawn (feet), and the top of a feature, for markers.
    [[nodiscard]] math::Vec3 creature_position(const sim::Game& game, const sim::Creature& c, float alpha) const;
    [[nodiscard]] math::Vec3 feature_top(const sim::Game& game, std::uint32_t feature) const;
    [[nodiscard]] bool feature_shown(const sim::Game& game, std::uint32_t feature) const;
    // Where a villager is drawn (feet), for markers and the camera.
    [[nodiscard]] math::Vec3 villager_position(const sim::Game& game, const sim::Villager& v, float alpha) const;
    // The lights of the night (phase 69), added to `out`: the buildings
    // that give light and, when `torches`, the torch of each person drawn
    // by the last update() (villagers, soldiers, raiders, the merchant) who
    // is out of their reach. Animals carry none.
    void lights(const sim::Game& game, bool torches, std::vector<render::PointLight>& out) const;
    // Top of a building, for its marker.
    [[nodiscard]] math::Vec3 building_top(const sim::Game& game, const sim::Building& b) const;

private:
    static constexpr render::ModelId kNoModel = ~0u;
    struct Model {
        render::ModelId id = kNoModel;
        // Meters over its floor (the model's origin): what lies under it
        // is foundations (phase 65).
        float height = 1.0f;
        float width = 1.0f;  // Model size along x and z, meters.
        float depth = 1.0f;
    };
    std::map<std::string, Model> files_;
    // The looks of each building definition (phase 31): variants of its own
    // look and of each level that has one. Missing files are left out.
    struct DefLook {
        std::vector<Model> base;
        std::vector<std::vector<Model>> levels;  // Level n + 1; empty: the one below.
    };
    std::vector<DefLook> def_looks_;  // By building definition.
    std::uint32_t palette_count_buildings_ = 0;
    // The model a building shows at `level`, for its place `key`; null if
    // its definition has none.
    [[nodiscard]] const Model* model_for(sim::DefIndex def, std::uint8_t level, std::uint32_t key) const;
    Model load_building_file(render::SceneRenderer& renderer, const std::filesystem::path& file);
    std::vector<render::ModelId> used_;

    struct Look {
        std::uint32_t generation = ~0u;
        float yaw = 0.0f;
        people::Motion motion;
    };
    std::vector<Look> looks_;  // By villager entity index.
    std::vector<render::CharacterInstance> characters_;
    std::vector<math::Vec3> torches_;  // Where each person of characters_ stands; see lights().
    const people::Cast* cast_ = nullptr;
    sim::EntityId hidden_villager_;
    std::optional<AnchorGhost> anchor_ghost_;
    std::vector<Fade> faded_;
    people::Motion anchor_motion_;

    std::optional<Ghost> ghost_;
    std::vector<Ghost> trace_;
    // Phase 93: the pieces of each building that goes in lines, by definition
    // (kNoModel: it has none, and shows its own model).
    std::map<sim::DefIndex, std::array<Model, sim::kLinePieces>> line_pieces_;
    std::optional<FieldGhost> field_ghost_;
    // Phase 91: what dresses the ground around where the camera looks.
    cover::GroundCover cover_;
    int ground_detail_ = 2;
    // Phase 92: the animals that only give the map life, by the same setting.
    fauna::AmbientFauna fauna_;
    // No place in a list of models (a pile's, a crop's).
    static constexpr std::size_t kNoPile = ~std::size_t{0};
    // Meters a crop that sways bends at one meter of height.
    static constexpr float kCropSway = 0.07f;
    // Fields: a soil slab and a plant per 2 m, made in code.
    render::ModelId tile_model_ = kNoModel;
    render::ModelId plant_model_ = kNoModel;
    // Phase 90: each crop's own plots, one per stage, as places in
    // `crop_ids_` (kNoPile: the plain plant above); `crop_ids_` holds every
    // such model once and `crop_lists_` its instances while fields are rebuilt.
    std::vector<std::array<std::size_t, sim::kCropStages>> crop_models_;
    std::vector<render::ModelId> crop_ids_;
    std::vector<std::vector<render::Instance>> crop_lists_;
    // Animals: one low-poly body for all kinds (phase 18 brings real ones),
    // and a red mark under raiders.
    render::ModelId animal_model_ = kNoModel;  // The fallback body for animals without a model.
    // Deer, boar, wolf and bear (models/animals in core), animated (phase
    // 47): the body, its clips and the speeds the clips were made for.
    struct Species {
        bool loaded = false;
        render::SkinnedId body = 0;
        animal_motion::Clips clips;
        std::uint32_t die = 0;
        float die_length = 1.0f;
    };
    std::array<Species, 4> species_{};
    // What each creature is showing, by creature entity index.
    struct CreatureLook {
        std::uint32_t generation = ~0u;
        float yaw = 0.0f;
        animal_motion::State motion;  // Unanimated animals: only its time.
        people::Motion person;        // Raiders and soldiers.
        sim::CreatureKind kind = sim::CreatureKind::Deer;
        math::Vec3 position;
        std::uint32_t seen = 0;      // Frame it was last shown.
        std::uint32_t present = 0;   // Frame it was last in the game.
    };
    std::vector<CreatureLook> creature_looks_;
    // Animals that died in view: they play their die clip where they fell,
    // lie still a while and sink into the ground.
    struct Corpse {
        std::size_t species = 0;
        math::Vec3 position;
        float yaw = 0.0f;
        float time = 0.0f;
    };
    std::vector<Corpse> corpses_;
    std::uint32_t frame_ = 0;
    const sim::Game* creatures_game_ = nullptr;
    std::uint64_t creatures_tick_ = 0;
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
        float drag = 0.15f;  // How fast it stops rising (smoke: slowly, to climb high).
    };
    render::ModelId puff_model_ = kNoModel;
    std::vector<Particle> particles_;
    std::vector<render::Instance> puffs_;
    std::uint32_t particle_seed_ = 12345u;
    float emit_timer_ = 0.0f;
    [[nodiscard]] float random01();
    void update_particles(render::SceneRenderer& renderer, const sim::Game& game, float dt, float speed);
    // Phase 97: rain, or snow when it freezes: streaks (or flakes) falling
    // in a box around where the view looks. `wet_` eases in and out.
    render::ModelId streak_model_ = kNoModel;
    std::vector<math::Vec3> drops_;  // Where each is, from the middle of the box.
    std::vector<render::Instance> streaks_;
    std::vector<render::Instance> flakes_;
    float wet_ = 0.0f;
    bool flakes_falling_ = false;
    bool weather_shown_ = true;
    float view_distance_ = 60.0f;
    void update_weather(render::SceneRenderer& renderer, const sim::Game& game, float dt, float speed);
    void update_overlay(render::SceneRenderer& renderer, const sim::Game& game, float dt);
    std::vector<render::Instance> animals_;
    std::vector<render::Instance> marks_;
    void update_creatures(render::SceneRenderer& renderer, const sim::Game& game, float alpha, float dt, float speed);
    void add_corpse(const CreatureLook& look);
    void update_corpses(const sim::Game& game, float game_dt);
    void rebuild_fields(render::SceneRenderer& renderer, const sim::Game& game);
    const FogView* fog_ = nullptr;
    std::uint64_t shown_buildings_ = 0;  // Which buildings of others show (a hash).
    [[nodiscard]] std::uint64_t shown_signature(const sim::Game& game) const;
    bool ghost_changed_ = false;
    bool shown_ = false;

    void rebuild_buildings(render::SceneRenderer& renderer, const sim::Game& game);
    // Phase 65: the height a building's model stands at. Its floor, level
    // with the ground at its door; walls and the like, on the lowest ground
    // under them.
    [[nodiscard]] float floor_y(const sim::Game& game, sim::DefIndex def, std::int32_t x, std::int32_t z, std::int32_t w,
                                std::int32_t d, std::uint8_t rotation) const;
    [[nodiscard]] render::Instance building_instance(const sim::Game& game, sim::DefIndex def, const Model& m,
                                                     std::int32_t x,
                                                     std::int32_t z, std::int32_t w, std::int32_t d,
                                                     std::uint8_t rotation, float progress) const;
    void update_characters(render::SceneRenderer& renderer, const sim::Game& game, float alpha, float dt, float speed);

    // Phase 67: what makes the work visible. The stages of a building site
    // by its footprint (missing: the building rises out of the ground as
    // before); the piles of goods beside sites and storages, by the kind
    // of load and how full; the merchant's cart at the trading post; and
    // the arrows of hunters, archers and towers.
    std::map<std::pair<std::int32_t, std::int32_t>, std::array<Model, 2>> sites_;
    std::array<std::array<Model, 3>, static_cast<std::size_t>(sim::LoadKind::Count)> piles_{};
    // Phase 89: a pile per resource. Each resource's three sizes as places
    // in `pile_ids_` (kNoPile: nothing to draw): its own models, or those
    // of its kind of load. `pile_ids_` holds every pile model once, and
    // `pile_lists_` the instances of each while the piles are rebuilt.
    std::vector<std::array<std::size_t, 3>> resource_piles_;
    std::vector<render::ModelId> pile_ids_;
    std::vector<std::vector<render::Instance>> pile_lists_;
    std::vector<std::int32_t> pile_amounts_;  // Per resource, of the building at hand.
    std::vector<std::int32_t> pile_full_;
    Model cart_;
    Model arrow_;
    std::vector<render::ModelId> prop_models_;  // Piles, cart and arrow: set apart from the buildings.
    [[nodiscard]] bool is_prop(render::ModelId id) const;
    float piles_timer_ = 0.0f;
    void rebuild_piles(render::SceneRenderer& renderer, const sim::Game& game);
    struct Arrow {
        math::Vec3 from;
        math::Vec3 to;
        float age = 0.0f;
        float seconds = 1.0f;
    };
    std::vector<Arrow> arrows_;
    std::vector<render::Instance> arrow_instances_;
    float props_time_ = 0.0f;  // Game seconds, for what repeats.
    void shoot(math::Vec3 from, math::Vec3 to);
    void update_props(render::SceneRenderer& renderer, const sim::Game& game, float alpha, float dt, float speed);
};

}  // namespace sc
