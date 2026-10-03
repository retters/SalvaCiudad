#include "game/village_view.h"

#include "game/multiplayer_screens.h"

#include <algorithm>
#include <cmath>
#include <numbers>

#include "core/log.h"
#include "game/animal_motion.h"
#include "game/builtin_models.h"
#include "game/model_file.h"
#include "game/camera.h"
#include "game/variants.h"
#include "game/village_props.h"

namespace sc {

namespace {

float to_float(sim::Fixed f) {
    return static_cast<float>(f.raw()) / 65536.0f;
}

// Villagers walk 0.2 m per tick (sim/game.cpp), ten ticks a second at x1.

// A slab of soil, 2 x 2 m, white so the instance tint colors it.
render::ModelData make_tile_model() {
    render::ModelData m;
    const float h = 0.25f;
    const float s = 1.0f;
    // Top and four sides (counter-clockwise seen from outside).
    const auto quad = [&](math::Vec3 a, math::Vec3 b, math::Vec3 c, math::Vec3 d, math::Vec3 n) {
        const auto base = static_cast<std::uint32_t>(m.vertices.size());
        for (const math::Vec3& p : {a, b, c, d}) {
            m.vertices.push_back({p.x, p.y, p.z, n.x, n.y, n.z, 0.0f, 0.0f});
        }
        for (const std::uint32_t i : {0u, 1u, 2u, 0u, 2u, 3u}) {
            m.indices.push_back(base + i);
        }
    };
    quad({-s, h, -s}, {-s, h, s}, {s, h, s}, {s, h, -s}, {0, 1, 0});
    quad({-s, 0, s}, {s, 0, s}, {s, h, s}, {-s, h, s}, {0, 0, 1});
    quad({s, 0, -s}, {-s, 0, -s}, {-s, h, -s}, {s, h, -s}, {0, 0, -1});
    quad({s, 0, s}, {s, 0, -s}, {s, h, -s}, {s, h, s}, {1, 0, 0});
    quad({-s, 0, -s}, {-s, 0, s}, {-s, h, s}, {-s, h, -s}, {-1, 0, 0});
    m.materials.push_back({});
    m.primitives.push_back({0, static_cast<std::uint32_t>(m.indices.size()), 0});
    m.bounds_min = {-s, 0, -s};
    m.bounds_max = {s, h, s};
    m.radius = 1.5f;
    return m;
}

// Four small low-poly plants on a 2 x 2 m patch, 0.7 m high at scale 1.
render::ModelData make_plant_model() {
    render::ModelData m;
    const float kSpots[4][2] = {{-0.5f, -0.5f}, {0.5f, -0.4f}, {-0.45f, 0.5f}, {0.5f, 0.45f}};
    for (const auto& spot : kSpots) {
        const math::Vec3 top{spot[0], 0.7f, spot[1]};
        const float r = 0.28f;
        const math::Vec3 base[4] = {{spot[0] - r, 0.2f, spot[1]}, {spot[0], 0.2f, spot[1] + r},
                                    {spot[0] + r, 0.2f, spot[1]}, {spot[0], 0.2f, spot[1] - r}};
        for (int k = 0; k < 4; ++k) {
            const math::Vec3 a = base[k];
            const math::Vec3 b = base[(k + 1) % 4];
            const math::Vec3 n = math::normalize(math::cross(b - a, top - a));
            const auto i = static_cast<std::uint32_t>(m.vertices.size());
            for (const math::Vec3& p : {a, b, top}) {
                m.vertices.push_back({p.x, p.y, p.z, n.x, n.y, n.z, 0.0f, 0.0f});
            }
            m.indices.insert(m.indices.end(), {i, i + 1, i + 2});
        }
    }
    m.materials.push_back({});
    m.primitives.push_back({0, static_cast<std::uint32_t>(m.indices.size()), 0});
    m.bounds_min = {-1, 0, -1};
    m.bounds_max = {1, 0.7f, 1};
    m.radius = 1.5f;
    return m;
}

// A four-legged animal 1.6 m long, facing +Z, white so the tint colors it.
render::ModelData make_animal_model() {
    render::ModelData m;
    const auto box = [&](math::Vec3 lo, math::Vec3 hi) {
        const math::Vec3 c[8] = {{lo.x, lo.y, lo.z}, {hi.x, lo.y, lo.z}, {hi.x, hi.y, lo.z}, {lo.x, hi.y, lo.z},
                                 {lo.x, lo.y, hi.z}, {hi.x, lo.y, hi.z}, {hi.x, hi.y, hi.z}, {lo.x, hi.y, hi.z}};
        const int faces[6][4] = {{0, 3, 2, 1}, {4, 5, 6, 7}, {0, 4, 7, 3}, {1, 2, 6, 5}, {3, 7, 6, 2}, {0, 1, 5, 4}};
        const math::Vec3 normals[6] = {{0, 0, -1}, {0, 0, 1}, {-1, 0, 0}, {1, 0, 0}, {0, 1, 0}, {0, -1, 0}};
        for (int f = 0; f < 6; ++f) {
            const auto base = static_cast<std::uint32_t>(m.vertices.size());
            for (int k = 0; k < 4; ++k) {
                const math::Vec3& p = c[faces[f][k]];
                m.vertices.push_back({p.x, p.y, p.z, normals[f].x, normals[f].y, normals[f].z, 0.0f, 0.0f});
            }
            for (const std::uint32_t i : {0u, 1u, 2u, 0u, 2u, 3u}) {
                m.indices.push_back(base + i);
            }
        }
    };
    box({-0.25f, 0.55f, -0.7f}, {0.25f, 1.0f, 0.55f});    // Body.
    box({-0.15f, 0.8f, 0.5f}, {0.15f, 1.15f, 0.95f});     // Head.
    for (const float x : {-0.2f, 0.12f}) {
        for (const float z : {-0.6f, 0.38f}) {
            box({x, 0.0f, z}, {x + 0.08f, 0.6f, z + 0.1f});  // Legs.
        }
    }
    m.materials.push_back({});
    m.primitives.push_back({0, static_cast<std::uint32_t>(m.indices.size()), 0});
    m.bounds_min = {-0.25f, 0.0f, -0.7f};
    m.bounds_max = {0.25f, 1.15f, 0.95f};
    m.radius = 1.2f;
    return m;
}

// A thin colored square for the map layers, 2 x 2 m.
render::ModelData make_overlay_model() {
    render::ModelData m;
    const float s = 1.0f;
    const float h = 0.04f;
    for (const math::Vec3& p : {math::Vec3{-s, h, -s}, math::Vec3{-s, h, s}, math::Vec3{s, h, s}, math::Vec3{s, h, -s}}) {
        m.vertices.push_back({p.x, p.y, p.z, 0.0f, 1.0f, 0.0f, 0.0f, 0.0f});
    }
    m.indices = {0, 1, 2, 0, 2, 3};
    m.materials.push_back({});
    m.primitives.push_back({0, 6, 0});
    m.bounds_min = {-s, 0, -s};
    m.bounds_max = {s, h, s};
    m.radius = 1.5f;
    return m;
}

// A puff for smoke and flames: a low-poly ball, white for the tint.
render::ModelData make_puff_model() {
    render::ModelData m;
    constexpr int kRings = 4;
    constexpr int kSegments = 6;
    constexpr float kPi = std::numbers::pi_v<float>;
    for (int r = 0; r <= kRings; ++r) {
        const float phi = kPi * static_cast<float>(r) / kRings;
        for (int s = 0; s <= kSegments; ++s) {
            const float theta = 2.0f * kPi * static_cast<float>(s) / kSegments;
            const math::Vec3 n{std::sin(phi) * std::cos(theta), std::cos(phi), std::sin(phi) * std::sin(theta)};
            m.vertices.push_back({n.x * 0.5f, n.y * 0.5f + 0.5f, n.z * 0.5f, n.x, n.y, n.z, 0.0f, 0.0f});
        }
    }
    for (int r = 0; r < kRings; ++r) {
        for (int s = 0; s < kSegments; ++s) {
            const auto a = static_cast<std::uint32_t>(r * (kSegments + 1) + s);
            const auto b = a + kSegments + 1;
            m.indices.insert(m.indices.end(), {a, a + 1, b, a + 1, b + 1, b});
        }
    }
    m.materials.push_back({});
    m.primitives.push_back({0, static_cast<std::uint32_t>(m.indices.size()), 0});
    m.bounds_min = {-0.5f, 0.0f, -0.5f};
    m.bounds_max = {0.5f, 1.0f, 0.5f};
    m.radius = 0.8f;
    return m;
}

// Red (0) through yellow to green (1).
math::Vec3 ramp(float v) {
    v = std::clamp(v, 0.0f, 1.0f);
    return v < 0.5f ? math::Vec3{1.0f, v * 2.0f, 0.1f} : math::Vec3{2.0f - v * 2.0f, 1.0f, 0.1f};
}

float wrap_angle(float a) {
    while (a > std::numbers::pi_v<float>) {
        a -= 2.0f * std::numbers::pi_v<float>;
    }
    while (a < -std::numbers::pi_v<float>) {
        a += 2.0f * std::numbers::pi_v<float>;
    }
    return a;
}

}  // namespace

void VillageView::load(render::SceneRenderer& renderer, const mods::BuildResult& pack) {
    const sim::Content& content = pack.content;
    // The animals (phase 18), animated (phase 47).
    creature_looks_.clear();
    corpses_.clear();
    for (std::size_t k = 0; k < std::size(builtin_models::kAnimals) && k < species_.size(); ++k) {
        if (species_[k].loaded) {
            continue;
        }
        const std::filesystem::path file = mods::mod_file(pack.dir("core"), builtin_models::kAnimals[k]);
        const auto data = file.empty() ? std::nullopt : load_model_file(file);
        Species sp;
        if (!data.has_value() || !renderer.add_skinned_model(*data, sp.body)) {
            continue;  // Drawn with the fallback body.
        }
        const auto clip = [&](std::string_view name, std::uint32_t& index, float& length, float* speed) {
            const int i = renderer.clip_index(sp.body, name);
            if (i < 0) {
                return false;
            }
            index = static_cast<std::uint32_t>(i);
            length = std::max(0.05f, renderer.clip_duration(sp.body, index));
            for (const render::ModelClip& c : data->clips) {
                if (speed != nullptr && c.name == name && c.speed > 0.0f) {
                    *speed = c.speed;
                }
            }
            return true;
        };
        animal_motion::Clips& c = sp.clips;
        sp.loaded = clip("idle", c.idle, c.idle_length, nullptr) && clip("walk", c.walk, c.walk_length, &c.walk_speed) &&
                    clip("run", c.run, c.run_length, &c.run_speed) && clip("eat", c.eat, c.eat_length, nullptr) &&
                    clip("die", sp.die, sp.die_length, nullptr);
        if (!sp.loaded) {
            log::warn("village: animal model without its clips: {}", file.generic_string());
            continue;
        }
        species_[k] = sp;
    }
    const std::vector<render::BuildingPalette> palettes = make_building_palettes();
    renderer.set_building_palettes(palettes);
    palette_count_buildings_ = static_cast<std::uint32_t>(palettes.size());
    def_looks_.assign(content.buildings.size(), DefLook{});
    std::size_t missing = 0;
    const auto load_list = [&](const std::string& mod, const std::vector<std::string>& files) {
        std::vector<Model> out;
        for (const std::string& rel : files) {
            const std::filesystem::path file = mods::mod_file(pack.dir(mod), rel);
            const Model m = file.empty() ? Model{} : load_building_file(renderer, file);
            if (m.id == kNoModel) {
                ++missing;
            } else {
                out.push_back(m);
            }
        }
        return out;
    };
    for (std::size_t i = 0; i < content.buildings.size(); ++i) {
        const sim::BuildingDef& d = content.buildings[i];
        def_looks_[i].base = load_list(d.mod, d.models);
        for (const sim::LevelDef& level : d.levels) {
            def_looks_[i].levels.push_back(load_list(level.models_mod, level.models));
        }
    }
    if (missing > 0) {
        log::warn("village: {} building model(s) missing; those buildings will not be drawn", missing);
    }
    // Phase 67: the stages of a site, by footprint; the piles; the cart; the arrow.
    const std::filesystem::path core = pack.dir("core");
    const auto core_model = [&](const std::string& rel) {
        const std::filesystem::path file = mods::mod_file(core, rel);
        std::error_code ec;
        return !file.empty() && std::filesystem::is_regular_file(file, ec) ? load_building_file(renderer, file) : Model{};
    };
    for (const sim::BuildingDef& d : content.buildings) {
        const std::pair<std::int32_t, std::int32_t> size{d.width, d.depth};
        if (sites_.contains(size)) {
            continue;
        }
        const std::string base = std::string(builtin_models::kSitePrefix) + std::to_string(d.width) + "x" + std::to_string(d.depth);
        sites_[size] = {core_model(base + "_1.glb"), core_model(base + "_2.glb")};
    }
    const auto prop = [&](std::string_view rel) {
        const Model m = core_model(std::string(rel));
        if (m.id != kNoModel && !is_prop(m.id)) {
            prop_models_.push_back(m.id);
        }
        return m;
    };
    for (std::size_t kind = 0; kind < piles_.size(); ++kind) {
        for (std::size_t level = 0; level < 3; ++level) {
            piles_[kind][level] = prop(builtin_models::kPiles[kind][level]);
        }
    }
    cart_ = prop(builtin_models::kCart);
    arrow_ = prop(builtin_models::kArrow);
    if (tile_model_ == kNoModel) {
        render::ModelId id = 0;
        if (renderer.add_model(make_tile_model(), id)) {
            tile_model_ = id;
            used_.push_back(id);
        }
        if (renderer.add_model(make_plant_model(), id)) {
            renderer.set_model_class(id, render::ModelClass::SmallVegetation);
            plant_model_ = id;
            used_.push_back(id);
        }
        if (renderer.add_model(make_animal_model(), id)) {
            animal_model_ = id;
            used_.push_back(id);
        }
        if (renderer.add_model(make_tile_model(), id)) {
            mark_model_ = id;
            used_.push_back(id);
        }
        if (renderer.add_model(make_overlay_model(), id)) {
            overlay_model_ = id;
            used_.push_back(id);
        }
        if (renderer.add_model(make_puff_model(), id)) {
            puff_model_ = id;
            used_.push_back(id);
        }
    }
}

bool VillageView::is_prop(render::ModelId id) const {
    return std::find(prop_models_.begin(), prop_models_.end(), id) != prop_models_.end();
}

void VillageView::begin(render::SceneRenderer& renderer, MapScene& scene, sim::Game& game) {
    shown_ = true;
    arrows_.clear();
    piles_timer_ = 0.0f;
    looks_.clear();
    creature_looks_.clear();
    corpses_.clear();
    ghost_.reset();
    // The map shows every feature as generated; felled trees and picked
    // bushes of a loaded game are updated here.
    const sim::Content& content = game.content();
    for (std::size_t i = 0; i < game.nodes().size(); ++i) {
        const sim::Node& n = game.nodes()[i];
        if (n.amount <= 0) {
            const bool regrows = n.regrow_tick != 0;
            scene.set_feature_look(renderer, game.map(), content, i,
                                   regrows ? MapScene::FeatureLook::Empty : MapScene::FeatureLook::Gone);
        }
    }
    (void)game.take_changed_nodes();
    (void)game.take_buildings_changed();
    rebuild_buildings(renderer, game);
}

void VillageView::end(render::SceneRenderer& renderer) {
    for (const render::ModelId id : used_) {
        renderer.set_instances(id, {});
    }
    renderer.set_characters({});
    looks_.clear();
    creature_looks_.clear();
    faded_.clear();
    corpses_.clear();
    ghost_.reset();
    shown_ = false;
}

void VillageView::set_field_ghost(std::optional<FieldGhost> ghost) {
    if (ghost != field_ghost_) {
        field_ghost_ = ghost;
        ghost_changed_ = true;
    }
}

void VillageView::rebuild_fields(render::SceneRenderer& renderer, const sim::Game& game) {
    if (tile_model_ == kNoModel) {
        return;
    }
    std::vector<render::Instance> tiles;
    std::vector<render::Instance> plants;
    const auto patch = [&](std::int32_t x, std::int32_t z, std::int32_t w, std::int32_t d, math::Vec3 soil,
                           float plant_scale, math::Vec3 plant) {
        for (std::int32_t cz = z; cz + 1 < z + d + 1; cz += 2) {
            for (std::int32_t cx = x; cx + 1 < x + w + 1; cx += 2) {
                const float px = static_cast<float>(cx) + 1.0f;
                const float pz = static_cast<float>(cz) + 1.0f;
                const float y = map_surface_height(game.map(), px, pz) - 0.15f;
                render::Instance t;
                t.position = {px, y, pz};
                t.tint = soil;
                tiles.push_back(t);
                if (plant_scale > 0.0f && plant_model_ != kNoModel) {
                    render::Instance p = t;
                    p.position.y = y + 0.05f;
                    p.scale = plant_scale;
                    p.yaw = static_cast<float>((cx * 7 + cz * 13) % 6);
                    p.tint = plant;
                    plants.push_back(p);
                }
            }
        }
    };
    const sim::Content& content = game.content();
    for (const sim::Building& b : game.buildings().data()) {
        for (const sim::Field& f : b.fields) {
            if (fog_ != nullptr && fog_->mode() != sim::FogMode::None && game.town_group(b.owner) != fog_->group() &&
                !fog_->rect_shows(f.x, f.z, f.w, f.d)) {
                continue;
            }
            math::Vec3 soil{0.16f, 0.09f, 0.05f};  // Linear colors.
            float scale = 0.0f;
            math::Vec3 plant{0.1f, 0.32f, 0.06f};
            const bool fallow = f.plan[f.slot] == sim::kNoDef;
            const std::string_view crop = f.crop < content.crops.size() ? std::string_view(content.crops[f.crop].id) : "";
            // Ripe colors: golden wheat, orange vegetables, green beans.
            math::Vec3 ripe{0.75f, 0.52f, 0.12f};
            if (crop == "core:vegetables") {
                ripe = {0.6f, 0.22f, 0.05f};
            } else if (crop == "core:beans") {
                ripe = {0.12f, 0.42f, 0.08f};
            }
            switch (f.state) {
                case sim::FieldState::Waiting:
                    soil = f.work > 0 ? math::Vec3{0.11f, 0.06f, 0.035f} : soil;
                    break;
                case sim::FieldState::Growing: {
                    const float g = static_cast<float>(f.growth) / 1000.0f;
                    scale = 0.35f + 0.85f * g;
                    plant = plant * (1.0f - g * 0.5f) + ripe * (g * 0.5f);
                    break;
                }
                case sim::FieldState::Ripe:
                    scale = 1.2f;
                    plant = ripe;
                    break;
                case sim::FieldState::Done:
                    if (fallow) {
                        soil = {0.12f, 0.26f, 0.06f};  // Resting under grass.
                    } else {
                        scale = 0.12f;  // Stubble.
                        plant = {0.5f, 0.38f, 0.14f};
                    }
                    break;
                case sim::FieldState::Count: break;
            }
            patch(f.x, f.z, f.w, f.d, soil, scale, plant);
        }
    }
    if (field_ghost_) {
        const math::Vec3 tint = field_ghost_->allowed ? math::Vec3{0.2f, 0.9f, 0.25f} : math::Vec3{0.9f, 0.15f, 0.1f};
        patch(field_ghost_->x, field_ghost_->z, field_ghost_->w, field_ghost_->d, tint, 0.0f, {});
    }
    renderer.set_instances(tile_model_, tiles);
    if (plant_model_ != kNoModel) {
        renderer.set_instances(plant_model_, plants);
    }
}

void VillageView::set_ghost(std::optional<Ghost> ghost) {
    if (ghost != ghost_) {
        ghost_ = ghost;
        ghost_changed_ = true;
    }
}

void VillageView::update(render::SceneRenderer& renderer, MapScene& scene, sim::Game& game, float alpha, float dt,
                         float speed) {
    if (!shown_) {
        return;
    }
    for (const std::uint32_t i : game.take_changed_nodes()) {
        const sim::Node& n = game.nodes()[i];
        MapScene::FeatureLook look = MapScene::FeatureLook::Normal;
        if (n.amount <= 0) {
            look = n.regrow_tick != 0 ? MapScene::FeatureLook::Empty : MapScene::FeatureLook::Gone;
        }
        scene.set_feature_look(renderer, game.map(), game.content(), i, look);
    }
    // Buildings of others come and go with the fog.
    const std::uint64_t shown = shown_signature(game);
    if (game.take_buildings_changed() || ghost_changed_ || shown != shown_buildings_) {
        shown_buildings_ = shown;
        rebuild_buildings(renderer, game);
        ghost_changed_ = false;
    }
    update_characters(renderer, game, alpha, dt, speed);
    update_props(renderer, game, alpha, dt, speed);
    update_creatures(renderer, game, alpha, dt, speed);
    update_overlay(renderer, game, dt);
    update_particles(renderer, game, dt, speed);
}

bool VillageView::building_shown(const sim::Game& game, const sim::Building& b) const {
    return fog_ == nullptr || fog_->mode() == sim::FogMode::None || game.town_group(b.owner) == fog_->group() ||
           fog_->rect_shows(b.x, b.z, b.width, b.depth);
}

bool VillageView::mover_shown(const sim::Game& game, bool owned, std::uint8_t town, float x, float z) const {
    if (fog_ == nullptr || fog_->mode() == sim::FogMode::None) {
        return true;
    }
    return (owned && game.town_group(town) == fog_->group()) || fog_->shows(x, z);
}

bool VillageView::building_silhouette(const sim::Game& game, const sim::Building& b) const {
    if (fog_ == nullptr || fog_->mode() == sim::FogMode::None || game.town_group(b.owner) == fog_->group() ||
        !fog_->rect_unexplored(b.x, b.z, b.width, b.depth)) {
        return false;
    }
    if (game.content().buildings[b.def].landmark) {
        return true;
    }
    const math::Vec3 top = building_top(game, b);
    return top.y - 1.0f > fog_->ceiling_at(top.x, top.z);
}

std::uint64_t VillageView::shown_signature(const sim::Game& game) const {
    if (fog_ == nullptr || fog_->mode() == sim::FogMode::None) {
        return 0;
    }
    std::uint64_t h = 0xcbf29ce484222325ull ^ game.vision().ghost_revision();
    const auto& store = game.buildings();
    for (std::size_t k = 0; k < store.size(); ++k) {
        const sim::Building& b = store.data()[k];
        if (game.town_group(b.owner) != fog_->group() &&
            (fog_->rect_shows(b.x, b.z, b.width, b.depth) || building_silhouette(game, b))) {
            h = (h ^ (store.entities()[k].index + 1ull)) * 0x100000001b3ull;
        }
    }
    return h;
}

float VillageView::random01() {
    particle_seed_ ^= particle_seed_ << 13;
    particle_seed_ ^= particle_seed_ >> 17;
    particle_seed_ ^= particle_seed_ << 5;
    return static_cast<float>(particle_seed_ & 0xFFFFu) / 65535.0f;
}

void VillageView::update_particles(render::SceneRenderer& renderer, const sim::Game& game, float dt, float speed) {
    if (puff_model_ == kNoModel) {
        return;
    }
    constexpr std::size_t kMaxParticles = 4000;
    const float step = dt * std::max(speed, 0.0f);
    // New puffs a few times a second, near the view only.
    emit_timer_ -= step;
    if (emit_timer_ <= 0.0f && speed > 0) {
        emit_timer_ = 0.12f;
        const sim::Content& content = game.content();
        const bool cold = game.temperature() < sim::village::kColdBelow;
        for (const sim::Building& b : game.buildings().data()) {
            const float cx = static_cast<float>(b.x) + static_cast<float>(b.width) * 0.5f;
            const float cz = static_cast<float>(b.z) + static_cast<float>(b.depth) * 0.5f;
            if (std::abs(cx - view_x_) > 180.0f || std::abs(cz - view_z_) > 180.0f || particles_.size() >= kMaxParticles ||
                !building_shown(game, b)) {
                continue;
            }
            const sim::BuildingDef& d = content.buildings[b.def];
            const math::Vec3 top = building_top(game, b);
            if (b.fire > 0) {
                // Flames low on the building, dark smoke above.
                const float strength = static_cast<float>(b.fire) / 100.0f;
                const int flames = 2 + static_cast<int>(strength * 4.0f);
                for (int k = 0; k < flames; ++k) {
                    Particle p;
                    p.position = {static_cast<float>(b.x) + random01() * static_cast<float>(b.width),
                                  top.y - 2.5f + random01() * 1.5f,
                                  static_cast<float>(b.z) + random01() * static_cast<float>(b.depth)};
                    p.velocity = {(random01() - 0.5f) * 0.4f, 1.6f + random01(), (random01() - 0.5f) * 0.4f};
                    p.life = 0.6f + random01() * 0.4f;
                    p.size0 = 0.9f + strength;
                    p.size1 = 0.2f;
                    p.color0 = {2.4f, 1.4f, 0.3f};
                    p.color1 = {1.8f, 0.3f, 0.05f};
                    particles_.push_back(p);
                }
                Particle smoke;
                smoke.position = {cx + (random01() - 0.5f) * 2.0f, top.y, cz + (random01() - 0.5f) * 2.0f};
                smoke.velocity = {0.6f + random01() * 0.3f, 1.4f, 0.2f};
                smoke.life = 4.0f;
                smoke.size0 = 1.2f;
                smoke.size1 = 4.0f;
                smoke.color0 = {0.18f, 0.16f, 0.15f};
                smoke.color1 = {0.35f, 0.34f, 0.34f};
                particles_.push_back(smoke);
                continue;
            }
            // Chimneys: homes with a fire in the cold, and workshops at work
            // with a recipe that burns fuel.
            bool smokes = false;
            if (b.state == sim::BuildingState::Complete) {
                if (d.kind == sim::BuildingKind::House || d.kind == sim::BuildingKind::TownCenter) {
                    smokes = cold && b.heated && (!b.residents.empty() || d.kind == sim::BuildingKind::TownCenter);
                } else if (!b.workers.empty()) {
                    for (const sim::DefIndex r : d.recipes) {
                        for (const sim::ResourceAmount& in : content.recipes[r].inputs) {
                            smokes = smokes || content.resources[in.resource].category == sim::ResourceCategory::Fuel;
                        }
                    }
                }
            }
            if (!smokes || random01() > 0.45f) {
                continue;
            }
            Particle p;
            p.position = {cx + static_cast<float>(b.width) * 0.2f, top.y - 0.6f, cz + static_cast<float>(b.depth) * 0.1f};
            p.velocity = {0.35f + random01() * 0.2f, 0.9f + random01() * 0.3f, 0.1f};
            p.life = 3.5f + random01();
            p.size0 = 0.35f;
            p.size1 = 1.8f;
            p.color0 = {0.62f, 0.62f, 0.64f};
            p.color1 = {0.86f, 0.87f, 0.9f};
            particles_.push_back(p);
        }
    }
    // Move, grow and fade (by shrinking at the end).
    puffs_.clear();
    std::size_t kept = 0;
    for (std::size_t i = 0; i < particles_.size(); ++i) {
        Particle p = particles_[i];
        p.age += step;
        if (p.age >= p.life) {
            continue;
        }
        p.position = p.position + p.velocity * step;
        p.velocity.y *= 1.0f - 0.15f * step;
        const float t = p.age / p.life;
        float size = p.size0 + (p.size1 - p.size0) * t;
        if (t > 0.75f) {
            size *= 1.0f - (t - 0.75f) * 3.2f;
        }
        render::Instance inst;
        inst.position = p.position;
        inst.scale = std::max(0.01f, size);
        inst.yaw = p.age;
        inst.tint = p.color0 + (p.color1 - p.color0) * t;
        puffs_.push_back(inst);
        particles_[kept++] = p;
    }
    particles_.resize(kept);
    renderer.set_instances(puff_model_, puffs_);
}


void VillageView::update_overlay(render::SceneRenderer& renderer, const sim::Game& game, float dt) {
    if (overlay_model_ == kNoModel) {
        return;
    }
    overlay_timer_ -= dt;
    if (overlay_timer_ > 0.0f) {
        return;
    }
    overlay_timer_ = 0.5f;  // Twice a second is enough.
    overlay_tiles_.clear();
    const sim::MapData& map = game.map();
    const sim::Content& content = game.content();
    const auto tile = [&](float x, float z, float size, math::Vec3 color) {
        if (fog_ != nullptr && !fog_->explored(x, z)) {
            return;  // Nothing to tell about what was never seen.
        }
        render::Instance t;
        t.position = {x, map_surface_height(map, x, z) + 0.05f, z};
        t.scale = size * 0.5f * 0.9f;
        t.tint = color;
        overlay_tiles_.push_back(t);
    };
    constexpr float kCell = 4.0f;
    constexpr int kReach = 25;  // Cells each way: 100 m around the view.
    const int cx0 = static_cast<int>(std::floor(view_x_ / kCell));
    const int cz0 = static_cast<int>(std::floor(view_z_ / kCell));
    const int cells = map.size / static_cast<int>(kCell);
    const auto each_cell = [&](auto&& fn) {
        for (int cz = std::max(0, cz0 - kReach); cz <= std::min(cells - 1, cz0 + kReach); ++cz) {
            for (int cx = std::max(0, cx0 - kReach); cx <= std::min(cells - 1, cx0 + kReach); ++cx) {
                const float x = (static_cast<float>(cx) + 0.5f) * kCell;
                const float z = (static_cast<float>(cz) + 0.5f) * kCell;
                if (!map.water_at(static_cast<int>(x), static_cast<int>(z))) {
                    fn(x, z);
                }
            }
        }
    };
    // Which need a coverage layer shows.
    int need = -1;
    switch (overlay_) {
        case 3: need = static_cast<int>(sim::Need::Water); break;
        case 4: need = static_cast<int>(sim::Need::Market); break;
        case 5: need = static_cast<int>(sim::Need::Religion); break;
        case 6: need = static_cast<int>(sim::Need::Healer); break;
        default: break;
    }
    switch (overlay_) {
        case 1:  // Fertility.
            each_cell([&](float x, float z) {
                const auto i = static_cast<std::size_t>(static_cast<int>(z)) * static_cast<std::size_t>(map.size) +
                               static_cast<std::size_t>(static_cast<int>(x));
                tile(x, z, kCell, ramp(static_cast<float>(map.fertility[i]) / 255.0f));
            });
            break;
        case 2:  // Beauty, in 8 m cells: it costs more to work out.
            each_cell([&](float x, float z) {
                if (static_cast<int>(x / kCell) % 2 != 0 || static_cast<int>(z / kCell) % 2 != 0) {
                    return;
                }
                const sim::FixedVec2 at{sim::Fixed::from_int(static_cast<int>(x) + 2),
                                        sim::Fixed::from_int(static_cast<int>(z) + 2)};
                const float v = static_cast<float>(game.desirability_at(at) + 10) / 30.0f;
                tile(x + 2.0f, z + 2.0f, kCell * 2.0f, ramp(v));
            });
            break;
        case 3:
        case 4:
        case 5:
        case 6: {
            // Covered cells, in green.
            struct Reach {
                float x;
                float z;
                float r2;
            };
            std::vector<Reach> reach;
            for (const sim::Building& b : game.buildings().data()) {
                const sim::BuildingDef& d = content.buildings[b.def];
                const bool gives = d.service == need || (need == static_cast<int>(sim::Need::Healer) &&
                                                         d.service == static_cast<int>(sim::Need::Doctor));
                if (b.owner == town_ && b.state == sim::BuildingState::Complete && d.service_radius > 0 && gives) {
                    const auto r = static_cast<float>(d.service_radius);
                    reach.push_back({static_cast<float>(b.x) + static_cast<float>(b.width) * 0.5f,
                                     static_cast<float>(b.z) + static_cast<float>(b.depth) * 0.5f, r * r});
                }
            }
            each_cell([&](float x, float z) {
                for (const Reach& r : reach) {
                    if ((x - r.x) * (x - r.x) + (z - r.z) * (z - r.z) <= r.r2) {
                        tile(x, z, kCell, {0.2f, 1.2f, 0.4f});
                        return;
                    }
                }
            });
            break;
        }
        case 7: {  // Fire risk: wooden buildings, and whether a well is near.
            std::vector<std::pair<float, float>> wells;
            for (const sim::Building& b : game.buildings().data()) {
                if (b.owner == town_ && content.buildings[b.def].service == static_cast<int>(sim::Need::Water)) {
                    wells.emplace_back(static_cast<float>(b.x) + static_cast<float>(b.width) * 0.5f,
                                       static_cast<float>(b.z) + static_cast<float>(b.depth) * 0.5f);
                }
            }
            for (const sim::Building& b : game.buildings().data()) {
                const sim::BuildingDef& d = content.buildings[b.def];
                if (b.owner != town_ || d.fireproof) {
                    continue;
                }
                const float bx = static_cast<float>(b.x) + static_cast<float>(b.width) * 0.5f;
                const float bz = static_cast<float>(b.z) + static_cast<float>(b.depth) * 0.5f;
                bool well = false;
                for (const auto& [wx, wz] : wells) {
                    well = well || (wx - bx) * (wx - bx) + (wz - bz) * (wz - bz) <= 50.0f * 50.0f;
                }
                const math::Vec3 color = well ? math::Vec3{1.2f, 1.0f, 0.1f} : math::Vec3{1.4f, 0.15f, 0.1f};
                for (int z = b.z - 1; z < b.z + b.depth + 1; z += 2) {
                    for (int x = b.x - 1; x < b.x + b.width + 1; x += 2) {
                        tile(static_cast<float>(x) + 1.0f, static_cast<float>(z) + 1.0f, 2.0f, color);
                    }
                }
            }
            break;
        }
        case 8:  // Routes: where the villagers are going.
            for (const sim::Villager& v : game.villagers().data()) {
                if (v.owner != town_) {
                    continue;
                }
                for (std::size_t k = v.path_index; k < v.path.size() && overlay_tiles_.size() < 4000; ++k) {
                    tile(to_float(v.path[k].x), to_float(v.path[k].z), 1.0f, {1.4f, 1.2f, 0.2f});
                }
            }
            break;
        default: break;
    }
    renderer.set_instances(overlay_model_, overlay_tiles_);
}


void VillageView::update_creatures(render::SceneRenderer& renderer, const sim::Game& game, float alpha, float dt,
                                   float speed) {
    animals_.clear();
    marks_.clear();
    static constexpr math::Vec3 kColors[] = {
        {0.55f, 0.36f, 0.2f},   // Deer.
        {0.25f, 0.18f, 0.14f},  // Boar.
        {0.45f, 0.45f, 0.48f},  // Wolf.
        {0.3f, 0.2f, 0.12f},    // Bear.
    };
    static constexpr float kScales[] = {1.0f, 0.75f, 0.8f, 1.5f};
    // A new game, a loaded save or a jump back: nobody died, start over.
    if (&game != creatures_game_ || game.tick() < creatures_tick_) {
        creature_looks_.clear();
        corpses_.clear();
    }
    creatures_game_ = &game;
    creatures_tick_ = game.tick();
    ++frame_;
    const float game_dt = dt * std::max(speed, 0.0f);
    // Breathing and grazing at the game's pace, but never faster than real
    // time, so a fast game does not make them twitch.
    const float rest_dt = dt * std::clamp(speed, 0.0f, 1.0f);
    const auto& store = game.creatures();
    for (std::size_t k = 0; k < store.size(); ++k) {
        const sim::EntityId id = store.entities()[k];
        const sim::Creature& a = store.data()[k];
        const float x = to_float(a.previous.x) + (to_float(a.position.x) - to_float(a.previous.x)) * alpha;
        const float z = to_float(a.previous.z) + (to_float(a.position.z) - to_float(a.previous.z)) * alpha;
        const math::Vec3 at{x, map_surface_height(game.map(), x, z), z};
        if (id.index >= creature_looks_.size()) {
            creature_looks_.resize(static_cast<std::size_t>(id.index) + 1);
        }
        CreatureLook& look = creature_looks_[id.index];
        if (look.generation != id.generation) {
            add_corpse(look);  // The slot's last animal died this tick.
            look = CreatureLook{};
            look.generation = id.generation;
            look.yaw = static_cast<float>(id.index % 628u) / 100.0f;
            look.motion.time = static_cast<float>(id.index % 97u) / 97.0f;
        }
        look.kind = a.kind;
        look.present = frame_;
        const bool moving = a.position != a.previous;
        if (moving) {
            const float want = std::atan2(to_float(a.position.x - a.previous.x), to_float(a.position.z - a.previous.z));
            look.yaw += wrap_angle(want - look.yaw) * std::min(1.0f, dt * 8.0f);
        }
        if (a.state == sim::CreatureState::Travel) {
            continue;  // Away on the world map.
        }
        if (!mover_shown(game, a.kind == sim::CreatureKind::Soldier, a.town, x, z)) {
            continue;  // Under the fog of war.
        }
        look.seen = frame_;
        look.position = at;
        if (a.kind == sim::CreatureKind::Raider || a.kind == sim::CreatureKind::Soldier) {
            // A villager with a mark under it: red for raiders, the town's
            // color for soldiers. They hurry after an enemy and swing at
            // what they attack.
            if (cast_ != nullptr && cast_->loaded()) {
                const std::uint32_t bits = id.index * 2654435761u + id.generation;
                const people::Body& body = cast_->any_body(bits);
                const float meters = math::length(math::Vec3{to_float(a.position.x - a.previous.x), 0.0f,
                                                             to_float(a.position.z - a.previous.z)}) *
                                     static_cast<float>(sim::kTicksPerSecond);
                const people::Act act = moving ? (a.state == sim::CreatureState::Chase ? people::Act::Run : people::Act::Walk)
                                        : a.state == sim::CreatureState::Bash ? people::Act::Chop
                                                                              : people::Act::Idle;
                people::advance(body, look.person, act, meters, game_dt, rest_dt);
                render::CharacterInstance c;
                people::pose(body, look.person, c);
                c.position = at;
                c.yaw = look.yaw;
                c.scale = 1.05f;
                c.palette = people::Cast::palette(body, bits);
                characters_.push_back(c);
            }
            render::Instance mark;
            mark.position = {at.x, at.y + 0.02f, at.z};
            mark.scale = 0.4f;
            mark.tint = {1.6f, 0.15f, 0.1f};
            if (a.kind == sim::CreatureKind::Soldier) {
                const ui::Color color = player_color(a.town);
                mark.tint = {static_cast<float>(color.r) / 160.0f, static_cast<float>(color.g) / 160.0f,
                             static_cast<float>(color.b) / 160.0f};
                mark.scale = 0.45f;
            }
            marks_.push_back(mark);
            continue;
        }
        const auto kind = static_cast<std::size_t>(a.kind) % std::size(kColors);
        if (kind >= species_.size() || !species_[kind].loaded) {
            render::Instance inst;
            inst.position = at;
            look.motion.time += dt * (moving ? 2.0f * std::max(speed, 1.0f) : 1.0f);
            if (moving) {
                inst.position.y += 0.06f * std::abs(std::sin(look.motion.time * 6.0f));  // A trot.
            }
            inst.yaw = look.yaw;
            inst.scale = kScales[kind];
            inst.tint = kColors[kind];
            animals_.push_back(inst);
            continue;
        }
        // Meters per second of game time, from the last tick's step.
        const float step_x = to_float(a.position.x - a.previous.x);
        const float step_z = to_float(a.position.z - a.previous.z);
        const float v = std::sqrt(step_x * step_x + step_z * step_z) * static_cast<float>(sim::kTicksPerSecond);
        animal_motion::advance(species_[kind].clips, look.motion, v, game_dt, rest_dt, id.index);
        render::CharacterInstance c;
        c.body = species_[kind].body;
        c.clip = look.motion.clip;
        c.time = look.motion.time;
        c.position = at;
        c.yaw = look.yaw;
        characters_.push_back(c);
    }
    // Animals shown last frame and gone now died (animals only leave the
    // game by dying).
    for (CreatureLook& look : creature_looks_) {
        if (look.generation != ~0u && look.present + 1 == frame_) {
            add_corpse(look);
            look = CreatureLook{};
        }
    }
    update_corpses(game, game_dt);
    if (animal_model_ != kNoModel) {
        renderer.set_instances(animal_model_, animals_);
    }
    if (mark_model_ != kNoModel) {
        renderer.set_instances(mark_model_, marks_);
    }
    renderer.set_characters(characters_);
}

void VillageView::add_corpse(const CreatureLook& look) {
    const auto kind = static_cast<std::size_t>(look.kind);
    if (look.generation == ~0u || look.seen + 1 != frame_ || kind >= species_.size() || !species_[kind].loaded) {
        return;  // Not an animal, or not in view when it died.
    }
    corpses_.push_back(Corpse{kind, look.position, look.yaw, 0.0f});
}

void VillageView::update_corpses(const sim::Game& game, float game_dt) {
    static constexpr float kLie = 8.0f;   // Seconds lying still after the clip.
    static constexpr float kSink = 3.0f;  // Seconds to sink into the ground.
    static constexpr float kDepth = 0.8f;
    std::erase_if(corpses_, [&](Corpse& c) {
        c.time += game_dt;
        return c.time > species_[c.species].die_length + kLie + kSink;
    });
    for (const Corpse& c : corpses_) {
        if (!mover_shown(game, false, 0, c.position.x, c.position.z)) {
            continue;
        }
        const Species& sp = species_[c.species];
        const float sink = std::clamp((c.time - sp.die_length - kLie) / kSink, 0.0f, 1.0f);
        render::CharacterInstance ch;
        ch.body = sp.body;
        ch.clip = sp.die;
        ch.time = std::min(c.time, sp.die_length * 0.999f);  // Holds the last pose.
        ch.position = {c.position.x, c.position.y - kDepth * sink, c.position.z};
        ch.yaw = c.yaw;
        characters_.push_back(ch);
    }
}

VillageView::Model VillageView::load_building_file(render::SceneRenderer& renderer, const std::filesystem::path& file) {
    const std::string key = file.generic_string();
    auto it = files_.find(key);
    if (it == files_.end()) {
        Model m;
        const auto data = load_model_file(file);
        render::ModelId id = 0;
        if (data.has_value() && renderer.add_model(*data, id)) {
            m.id = id;
            m.height = std::max(0.1f, data->bounds_max.y);  // Over the floor; foundations go below.
            m.width = std::max(0.1f, data->bounds_max.x - data->bounds_min.x);
            m.depth = std::max(0.1f, data->bounds_max.z - data->bounds_min.z);
            used_.push_back(id);
        }
        it = files_.emplace(key, m).first;
    }
    return it->second;
}

const VillageView::Model* VillageView::model_for(sim::DefIndex def, std::uint8_t level, std::uint32_t key) const {
    if (def >= def_looks_.size()) {
        return nullptr;
    }
    const DefLook& look = def_looks_[def];
    // The highest level reached that has a look of its own.
    const std::vector<Model>* list = &look.base;
    for (std::size_t l = 0; l < look.levels.size() && l < level; ++l) {
        if (!look.levels[l].empty()) {
            list = &look.levels[l];
        }
    }
    return list->empty() ? nullptr : &(*list)[pick_variant(key, list->size())];
}

render::Instance VillageView::building_instance(const sim::Game& game, sim::DefIndex def, const Model& m,
                                                std::int32_t x, std::int32_t z, std::int32_t w, std::int32_t d,
                                                std::uint8_t rotation, float progress) const {
    const sim::BuildingDef& bd = game.content().buildings[def];
    render::Instance inst;
    // Roof, wall and shutter colors by its place (materials named var_*).
    inst.palette = pick_building_palette(place_key(x, z), palette_count_buildings_);
    inst.scale = std::min(static_cast<float>(bd.width) / m.width, static_cast<float>(bd.depth) / m.depth) * 0.95f;
    inst.position = {static_cast<float>(x) + static_cast<float>(w) * 0.5f, floor_y(game, def, x, z, w, d, rotation),
                     static_cast<float>(z) + static_cast<float>(d) * 0.5f};
    // Models face +Z; rotation 0 puts the door on the -Z side.
    inst.yaw = std::numbers::pi_v<float> - static_cast<float>(rotation) * std::numbers::pi_v<float> * 0.5f;
    inst.landmark = bd.landmark;  // Phase 34.
    if (progress < 1.0f) {
        // Rises out of the ground as it is built; unfinished wood color.
        const float shown = 0.08f + 0.92f * std::clamp(progress, 0.0f, 1.0f);
        inst.position.y -= (1.0f - shown) * m.height * inst.scale;
        inst.tint = {0.85f, 0.72f, 0.55f};
    }
    return inst;
}

float VillageView::floor_y(const sim::Game& game, sim::DefIndex def, std::int32_t x, std::int32_t z, std::int32_t w,
                           std::int32_t d, std::uint8_t rotation) const {
    if (!sim::follows_ground(game.content().buildings[def])) {
        return static_cast<float>(game.floor_cm(x, z, w, d, rotation)) * 0.01f;
    }
    // On the lowest corner, a little sunk, so no corner floats on a slope.
    std::int32_t low = 65535;
    for (const std::int32_t vz : {z, z + d}) {
        for (const std::int32_t vx : {x, x + w}) {
            low = std::min<std::int32_t>(low, game.map().height_cm(vx, vz));
        }
    }
    return static_cast<float>(low) * 0.01f - 0.1f;
}

void VillageView::rebuild_buildings(render::SceneRenderer& renderer, const sim::Game& game) {
    std::map<render::ModelId, std::vector<render::Instance>> lists;
    for (const render::ModelId id : used_) {
        if (id != tile_model_ && id != plant_model_ && id != animal_model_ && id != mark_model_ && id != overlay_model_ &&
            id != puff_model_ && !is_prop(id)) {
            lists[id];
        }
    }
    // A site shows its foundations, then its frame, then the building.
    const auto stage = [&](sim::DefIndex def, float progress) -> const Model* {
        if (progress >= 1.0f || def >= game.content().buildings.size()) {
            return nullptr;
        }
        const sim::BuildingDef& bd = game.content().buildings[def];
        const auto it = sites_.find({bd.width, bd.depth});
        if (it == sites_.end()) {
            return nullptr;
        }
        const Model& m = it->second[static_cast<std::size_t>(props::site_stage(progress))];
        return m.id != kNoModel ? &m : nullptr;
    };
    const sim::Content& content = game.content();
    for (std::size_t k = 0; k < game.buildings().size(); ++k) {
        const sim::Building& b = game.buildings().data()[k];
        const Model* m = model_for(b.def, b.level, place_key(b.x, b.z));
        if (m == nullptr || (!building_shown(game, b) && !building_silhouette(game, b))) {
            continue;
        }
        const sim::BuildingDef& d = content.buildings[b.def];
        float progress = 1.0f;
        if (b.state == sim::BuildingState::Construction) {
            progress = d.build_work > 0 ? static_cast<float>(b.work_done) / static_cast<float>(d.build_work) : 1.0f;
        }
        const Model* site = b.state == sim::BuildingState::Construction ? stage(b.def, progress) : nullptr;
        if (site != nullptr) {
            m = site;
        }
        render::Instance inst =
            building_instance(game, b.def, *m, b.x, b.z, b.width, b.depth, b.rotation, site != nullptr ? 1.0f : progress);
        if (site != nullptr) {
            inst.palette = 0;  // A site has no colors of its own yet.
        }
        if (b.fire > 0 || b.burned > 0) {
            // Glowing while it burns, charred after.
            const float char_level = 1.0f - 0.7f * static_cast<float>(b.burned) / 1000.0f;
            inst.tint = b.fire > 0 ? math::Vec3{1.9f * char_level, 0.6f * char_level, 0.3f * char_level}
                                   : math::Vec3{char_level, char_level, char_level};
        }
        // In the camera's way (phase 61): see-through.
        for (const Fade& fade : faded_) {
            if (fade.building == game.buildings().entities()[k]) {
                inst.fade = std::min(fade.level, render::kMaxFade);
            }
        }
        lists[m->id].push_back(inst);
    }
    // Dynamic fog (phase 33): others' buildings out of sight, as last seen.
    if (fog_ != nullptr && fog_->mode() == sim::FogMode::Dynamic) {
        for (const sim::BuildingGhost& h : game.vision().ghosts(fog_->group())) {
            const sim::Building* real = game.buildings().get(h.id);
            if ((real != nullptr && building_shown(game, *real)) || h.def >= content.buildings.size()) {
                continue;  // The real one is in sight.
            }
            const Model* m = model_for(h.def, h.level, place_key(h.x, h.z));
            if (m == nullptr) {
                continue;
            }
            std::int32_t w = 0, d = 0;
            sim::Game::footprint(content.buildings[h.def], h.rotation, w, d);
            const float seen = static_cast<float>(h.progress) / 1000.0f;
            const Model* site = stage(h.def, seen);
            if (site != nullptr) {
                m = site;
            }
            render::Instance inst = building_instance(game, h.def, *m, h.x, h.z, w, d, h.rotation, site != nullptr ? 1.0f : seen);
            if (site != nullptr) {
                inst.palette = 0;
            }
            if (h.burning || h.burned > 0) {
                const float char_level = 1.0f - 0.7f * static_cast<float>(h.burned) / 1000.0f;
                inst.tint = h.burning ? math::Vec3{1.9f * char_level, 0.6f * char_level, 0.3f * char_level}
                                      : math::Vec3{char_level, char_level, char_level};
            }
            lists[m->id].push_back(inst);
        }
    }
    // The ghost shows the variant the building will have there.
    if (const Model* m = ghost_ ? model_for(ghost_->def, 0, place_key(ghost_->x, ghost_->z)) : nullptr) {
        std::int32_t w = 0, d = 0;
        sim::Game::footprint(content.buildings[ghost_->def], ghost_->rotation, w, d);
        render::Instance g =
            building_instance(game, ghost_->def, *m, ghost_->x, ghost_->z, w, d, ghost_->rotation, 1.0f);
        g.tint = ghost_->allowed ? math::Vec3{0.55f, 1.6f, 0.6f} : math::Vec3{1.8f, 0.45f, 0.4f};
        g.palette = 0;  // Its own colors under the green or red.
        lists[m->id].push_back(g);
    }
    for (auto& [id, list] : lists) {
        if (id != tile_model_ && id != plant_model_ && id != animal_model_ && id != mark_model_ && id != overlay_model_ &&
            id != puff_model_ && !is_prop(id)) {
            renderer.set_instances(id, list);
        }
    }
    rebuild_fields(renderer, game);
    rebuild_piles(renderer, game);
}

void VillageView::shoot(math::Vec3 from, math::Vec3 to) {
    if (arrow_.id != kNoModel && arrows_.size() < 256) {
        arrows_.push_back({from, to, 0.0f, props::arrow_seconds(from, to)});
    }
}

// The piles: at a site, what was brought so far; beside a storage, what it
// holds. One pile per kind of load, along the door's side.
void VillageView::rebuild_piles(render::SceneRenderer& renderer, const sim::Game& game) {
    const sim::Content& content = game.content();
    constexpr std::size_t kKinds = static_cast<std::size_t>(sim::LoadKind::Count);
    std::array<std::array<std::vector<render::Instance>, 3>, kKinds> lists;
    const auto& store = game.buildings();
    for (std::size_t k = 0; k < store.size(); ++k) {
        const sim::Building& b = store.data()[k];
        const sim::BuildingDef& d = content.buildings[b.def];
        const bool site = b.state == sim::BuildingState::Construction;
        if ((!site && (d.storage <= 0 || d.kind == sim::BuildingKind::House)) || sim::follows_ground(d) ||
            !building_shown(game, b)) {
            continue;
        }
        // How much of each kind, and what a full pile of it would be.
        std::array<std::int32_t, kKinds> amount{};
        std::array<std::int32_t, kKinds> full{};
        for (const sim::Stock& st : site ? b.delivered : b.stock) {
            if (st.resource < content.resources.size()) {
                amount[static_cast<std::size_t>(content.resources[st.resource].load)] += st.amount;
            }
        }
        if (site) {
            for (const sim::ResourceAmount& c : d.cost) {
                if (c.resource < content.resources.size()) {
                    full[static_cast<std::size_t>(content.resources[c.resource].load)] += c.amount;
                }
            }
        } else {
            full.fill(std::max(1, d.storage / 3));  // A third of the storage in one kind is a full pile.
        }
        // Along the door's side, a meter out, from its left corner.
        const float yaw = std::numbers::pi_v<float> - static_cast<float>(b.rotation) * std::numbers::pi_v<float> * 0.5f;
        // The door looks along -Z unturned; `out` points away from it, `along` to its right.
        static constexpr float kOut[4][2] = {{0, -1}, {1, 0}, {0, 1}, {-1, 0}};
        static constexpr float kAlong[4][2] = {{1, 0}, {0, 1}, {-1, 0}, {0, -1}};
        const std::size_t r = b.rotation & 3u;
        const float cx = static_cast<float>(b.x) + static_cast<float>(b.width) * 0.5f;
        const float cz = static_cast<float>(b.z) + static_cast<float>(b.depth) * 0.5f;
        const float half_out = static_cast<float>(r % 2 == 0 ? b.depth : b.width) * 0.5f;
        const float half_along = static_cast<float>(r % 2 == 0 ? b.width : b.depth) * 0.5f;
        int placed = 0;
        for (std::size_t kind = 0; kind < kKinds; ++kind) {
            const int level = props::pile_level(amount[kind], full[kind]);
            if (level == 0 || piles_[kind][static_cast<std::size_t>(level - 1)].id == kNoModel) {
                continue;
            }
            // Sites pile up on the left of the door, storages on the right.
            const float side = (site ? -1.0f : 1.0f) * (half_along - 0.8f - 1.7f * static_cast<float>(placed));
            if (std::abs(side) > half_along + 0.1f && placed > 0) {
                break;  // No more room along this side.
            }
            render::Instance inst;
            inst.position.x = cx + kOut[r][0] * (half_out + 1.0f) + kAlong[r][0] * side;
            inst.position.z = cz + kOut[r][1] * (half_out + 1.0f) + kAlong[r][1] * side;
            inst.position.y = map_surface_height(game.map(), inst.position.x, inst.position.z);
            inst.yaw = yaw + static_cast<float>(placed) * 0.6f;
            lists[kind][static_cast<std::size_t>(level - 1)].push_back(inst);
            ++placed;
        }
    }
    for (std::size_t kind = 0; kind < kKinds; ++kind) {
        for (std::size_t level = 0; level < 3; ++level) {
            if (piles_[kind][level].id != kNoModel) {
                renderer.set_instances(piles_[kind][level].id, lists[kind][level]);
            }
        }
    }
}

// The merchant and the cart at the trading post, the arrows in the air and
// the piles, which follow what is stored a few times a second.
void VillageView::update_props(render::SceneRenderer& renderer, const sim::Game& game, float alpha, float dt,
                               float speed) {
    const float game_dt = dt * std::max(speed, 0.0f);
    const float before = props_time_;
    props_time_ += game_dt;
    piles_timer_ -= dt;
    if (piles_timer_ <= 0.0f) {
        piles_timer_ = 0.5f;
        rebuild_piles(renderer, game);
    }
    const sim::Content& content = game.content();
    // Whether something that repeats every `ticks` came around this frame;
    // `shift` keeps each shooter on its own beat.
    const auto beat = [&](std::int32_t ticks, std::uint32_t shift) {
        const float period = static_cast<float>(std::max(1, ticks)) / static_cast<float>(sim::kTicksPerSecond);
        const float phase = static_cast<float>(shift % 97u) / 97.0f * period;
        return std::floor((props_time_ + phase) / period) != std::floor((before + phase) / period);
    };
    // The nearest enemy of a town within `range` meters of a point.
    const auto enemy_near = [&](math::Vec3 from, float range) -> std::optional<math::Vec3> {
        std::optional<math::Vec3> best;
        float best_d = range * range;
        for (const sim::Creature& c : game.creatures().data()) {
            if (c.kind != sim::CreatureKind::Raider && c.kind != sim::CreatureKind::Wolf && c.kind != sim::CreatureKind::Bear) {
                continue;
            }
            const math::Vec3 p = creature_position(game, c, alpha);
            const float d2 = (p.x - from.x) * (p.x - from.x) + (p.z - from.z) * (p.z - from.z);
            if (d2 < best_d && mover_shown(game, false, 0, p.x, p.z)) {
                best_d = d2;
                best = p + math::Vec3{0.0f, 1.0f, 0.0f};
            }
        }
        return best;
    };
    std::vector<render::Instance> carts;
    const auto& store = game.buildings();
    for (std::size_t k = 0; k < store.size(); ++k) {
        const sim::Building& b = store.data()[k];
        const sim::BuildingDef& d = content.buildings[b.def];
        if (b.state != sim::BuildingState::Complete || !building_shown(game, b)) {
            continue;
        }
        const math::Vec3 top = building_top(game, b);
        // Towers shoot at what comes near.
        if (d.attack_range > 0 && !d.trap && beat(d.attack_every, static_cast<std::uint32_t>(k) * 31u)) {
            if (const auto enemy = enemy_near(top, static_cast<float>(d.attack_range))) {
                shoot(top - math::Vec3{0.0f, 2.0f, 0.0f}, *enemy);
            }
        }
        // The merchant waits beside the trading post with the cart.
        if (d.trade && b.owner < game.player_count() && game.merchant_here(b.owner)) {
            const math::Vec3 door{to_float(game.door(b).x), 0.0f, to_float(game.door(b).z)};
            const math::Vec3 away = math::normalize(math::Vec3{door.x - top.x, 0.0f, door.z - top.z});
            const math::Vec3 beside{-away.z, 0.0f, away.x};
            render::Instance cart;
            cart.position = door + away * 1.6f + beside * 2.2f;
            cart.position.y = map_surface_height(game.map(), cart.position.x, cart.position.z);
            cart.yaw = std::atan2(-away.x, -away.z);  // Its shafts toward the post.
            if (cart_.id != kNoModel) {
                carts.push_back(cart);
            }
            if (cast_ != nullptr && cast_->loaded()) {
                const people::Body& body = cast_->any_body(static_cast<std::uint32_t>(k) * 7919u + 3u);
                people::Motion standing;
                standing.act = people::Act::Idle;
                standing.time = std::fmod(props_time_, body.length[static_cast<std::size_t>(people::Act::Idle)]);
                render::CharacterInstance c;
                people::pose(body, standing, c);
                c.position = door + away * 1.2f + beside * 0.6f;
                c.position.y = map_surface_height(game.map(), c.position.x, c.position.z);
                c.yaw = std::atan2(-away.x, -away.z);
                c.palette = people::Cast::palette(body, static_cast<std::uint32_t>(k) * 2654435761u + 11u);
                characters_.push_back(c);
            }
        }
    }
    if (cart_.id != kNoModel) {
        renderer.set_instances(cart_.id, carts);
    }
    // Archers shoot at whoever they are after.
    const auto& creatures = game.creatures();
    for (std::size_t k = 0; k < creatures.size(); ++k) {
        const sim::Creature& a = creatures.data()[k];
        if (a.kind != sim::CreatureKind::Soldier || a.unit >= content.units.size() || content.units[a.unit].range <= 4 ||
            a.state == sim::CreatureState::Travel) {
            continue;
        }
        const sim::Creature* target = a.target_kind == sim::TargetKind::Creature ? creatures.get(a.target) : nullptr;
        if (target == nullptr || !beat(content.units[a.unit].attack_every, creatures.entities()[k].index * 53u)) {
            continue;
        }
        const math::Vec3 from = creature_position(game, a, alpha);
        const math::Vec3 to = creature_position(game, *target, alpha);
        const float reach = static_cast<float>(content.units[a.unit].range) + 1.0f;
        if ((to.x - from.x) * (to.x - from.x) + (to.z - from.z) * (to.z - from.z) <= reach * reach &&
            mover_shown(game, true, a.town, from.x, from.z)) {
            shoot(from + math::Vec3{0.0f, 1.4f, 0.0f}, to + math::Vec3{0.0f, 1.0f, 0.0f});
        }
    }
    // The arrows in the air.
    const bool had = !arrow_instances_.empty();
    arrow_instances_.clear();
    for (Arrow& arrow : arrows_) {
        arrow.age += game_dt;
        const props::ArrowPose pose = props::arrow_pose(arrow.from, arrow.to, arrow.age / arrow.seconds);
        render::Instance inst;
        inst.position = pose.position;
        inst.yaw = pose.yaw;
        arrow_instances_.push_back(inst);
    }
    std::erase_if(arrows_, [](const Arrow& arrow) { return arrow.age >= arrow.seconds; });
    if (arrow_.id != kNoModel && (had || !arrow_instances_.empty())) {
        renderer.set_instances(arrow_.id, arrow_instances_);
    }
}

math::Vec3 VillageView::villager_position(const sim::Game& game, const sim::Villager& v, float alpha) const {
    const float x = to_float(v.previous.x) + (to_float(v.position.x) - to_float(v.previous.x)) * alpha;
    const float z = to_float(v.previous.z) + (to_float(v.position.z) - to_float(v.previous.z)) * alpha;
    return {x, map_surface_height(game.map(), x, z), z};
}

float VillageView::building_roof(const sim::Game& game, const sim::Building& b) const {
    const Model* m = model_for(b.def, b.level, place_key(b.x, b.z));
    if (m == nullptr || !building_shown(game, b)) {
        return 0.0f;
    }
    const sim::BuildingDef& d = game.content().buildings[b.def];
    float progress = 1.0f;
    if (b.state == sim::BuildingState::Construction && d.build_work > 0) {
        progress = static_cast<float>(b.work_done) / static_cast<float>(d.build_work);
    }
    // The same instance it is drawn with: sunk while it is being built.
    const render::Instance inst = building_instance(game, b.def, *m, b.x, b.z, b.width, b.depth, b.rotation, progress);
    return inst.position.y + m->height * inst.scale;
}

math::Vec3 VillageView::building_top(const sim::Game& game, const sim::Building& b) const {
    const math::Vec3 base{static_cast<float>(b.x) + static_cast<float>(b.width) * 0.5f, 0.0f,
                          static_cast<float>(b.z) + static_cast<float>(b.depth) * 0.5f};
    float h = 5.0f;
    if (const Model* m = model_for(b.def, b.level, place_key(b.x, b.z)); m != nullptr) {
        const sim::BuildingDef& d = game.content().buildings[b.def];
        h = m->height * std::min(static_cast<float>(d.width) / m->width, static_cast<float>(d.depth) / m->depth) *
            0.95f;
    }
    return {base.x, floor_y(game, b.def, b.x, b.z, b.width, b.depth, b.rotation) + h + 1.0f, base.z};
}

void VillageView::update_characters(render::SceneRenderer& renderer, const sim::Game& game, float alpha, float dt,
                                    float speed) {
    characters_.clear();
    if (cast_ == nullptr || !cast_->loaded()) {
        renderer.set_characters({});
        return;
    }
    const float game_dt = dt * std::max(speed, 0.0f);
    // Work and rest at the game's pace, but never faster than real time.
    const float rest_dt = dt * std::clamp(speed, 0.0f, 1.0f);
    const auto& store = game.villagers();
    for (std::size_t k = 0; k < store.size(); ++k) {
        const sim::EntityId id = store.entities()[k];
        const sim::Villager& v = store.data()[k];
        if (id.index >= looks_.size()) {
            looks_.resize(static_cast<std::size_t>(id.index) + 1);
        }
        Look& look = looks_[id.index];
        const bool moving = v.position != v.previous;
        if (!mover_shown(game, true, v.owner, to_float(v.position.x), to_float(v.position.z))) {
            continue;  // Under the fog of war.
        }
        if (id == hidden_villager_) {
            continue;  // The first-person camera looks from its eyes.
        }
        if (look.generation != id.generation) {
            look = Look{};
            look.generation = id.generation;
            look.yaw = static_cast<float>(v.appearance % 628u) / 100.0f;
            look.motion.time = static_cast<float>((v.appearance >> 10) % 1000u) / 1000.0f;
        }
        if (moving) {
            const float want = std::atan2(to_float(v.position.x - v.previous.x), to_float(v.position.z - v.previous.z));
            look.yaw += wrap_angle(want - look.yaw) * std::min(1.0f, dt * 8.0f);
        }
        // The character by race and sex, and what it does by its task; the
        // stride follows the ground it really covers.
        const people::Body& body = cast_->body(v.race, v.sex == sim::Sex::Female, v.appearance);
        const std::int32_t age = game.age_years(v);
        const float scale = people::scale_of(age, v.appearance);
        const float meters = math::length(math::Vec3{to_float(v.position.x - v.previous.x), 0.0f,
                                                     to_float(v.position.z - v.previous.z)}) *
                             static_cast<float>(sim::kTicksPerSecond);
        // A smaller body takes shorter steps.
        const people::Load load = people::load_of(game.content(), v);
        const float before = look.motion.act == people::Act::Shoot ? look.motion.time : -1.0f;
        people::advance(body, look.motion, people::act_of(game, v, moving), meters / scale, game_dt, rest_dt, load);
        render::CharacterInstance c;
        people::pose(body, look.motion, c, load);
        c.position = villager_position(game, v, alpha);
        if (look.motion.act == people::Act::Shoot && before >= 0.0f && look.motion.time < before) {
            // The shot came around: an arrow flies where it aims, into the grass.
            const math::Vec3 ahead{std::sin(look.yaw), 0.0f, std::cos(look.yaw)};
            math::Vec3 to = c.position + ahead * 24.0f;
            to.y = map_surface_height(game.map(), to.x, to.z) + 0.1f;
            shoot(c.position + math::Vec3{0.0f, 1.4f * scale, 0.0f} + ahead * 0.5f, to);
        }
        c.yaw = look.yaw;
        c.scale = scale;
        c.palette = people::Cast::palette(body, v.appearance);
        characters_.push_back(c);
    }
    // The ghost of the camera's anchor walks when the anchor moves; it is
    // the camera's, so it goes by real time whatever the game's speed.
    if (anchor_ghost_) {
        const people::Body& body = cast_->body(0, false, 0);
        const bool moving = anchor_ghost_->speed > 0.3f;
        people::advance(body, anchor_motion_, moving ? people::Act::Walk : people::Act::Idle, anchor_ghost_->speed, dt, dt);
        render::CharacterInstance c;
        people::pose(body, anchor_motion_, c);
        c.accessories = 0;
        c.position = anchor_ghost_->feet;
        c.yaw = anchor_ghost_->yaw;
        c.palette = cast_->ghost_palette();
        c.fade = 2;
        characters_.push_back(c);
    }
    renderer.set_characters(characters_);
}

std::optional<VillageView::Standing> VillageView::standing(const sim::Game& game, sim::EntityId villager, float alpha) const {
    const sim::Villager* v = game.villagers().get(villager);
    if (v == nullptr || !mover_shown(game, true, v->owner, to_float(v->position.x), to_float(v->position.z))) {
        return std::nullopt;
    }
    Standing out;
    out.feet = villager_position(game, *v, alpha);
    if (cast_ != nullptr && cast_->loaded()) {
        const people::Body& body = cast_->body(v->race, v->sex == sim::Sex::Female, v->appearance);
        out.height = body.height / 1.8f * people::scale_of(game.age_years(*v), v->appearance);
    }
    return out;
}

std::optional<sim::EntityId> VillageView::pick_villager(const sim::Game& game, math::Vec3 origin, math::Vec3 dir,
                                                        float alpha) const {
    constexpr float kHeight = 1.8f;
    constexpr float kRadius = 0.5f;
    std::optional<sim::EntityId> best;
    float best_t = 1e30f;
    const auto& store = game.villagers();
    for (std::size_t k = 0; k < store.size(); ++k) {
        const math::Vec3 p = villager_position(game, store.data()[k], alpha);
        if (!mover_shown(game, true, store.data()[k].owner, p.x, p.z)) {
            continue;
        }
        const RayHit hit = ray_to_vertical_segment(origin, dir, p, kHeight);
        if (hit.distance <= kRadius && hit.t < best_t) {
            best_t = hit.t;
            best = store.entities()[k];
        }
    }
    return best;
}

math::Vec3 VillageView::creature_position(const sim::Game& game, const sim::Creature& c, float alpha) const {
    const float x = to_float(c.previous.x) + (to_float(c.position.x) - to_float(c.previous.x)) * alpha;
    const float z = to_float(c.previous.z) + (to_float(c.position.z) - to_float(c.previous.z)) * alpha;
    return {x, map_surface_height(game.map(), x, z), z};
}

std::optional<sim::EntityId> VillageView::pick_creature(const sim::Game& game, math::Vec3 origin, math::Vec3 dir,
                                                        float alpha) const {
    std::optional<sim::EntityId> best;
    float best_t = 1e30f;
    const auto& store = game.creatures();
    for (std::size_t k = 0; k < store.size(); ++k) {
        const sim::Creature& c = store.data()[k];
        if (c.state == sim::CreatureState::Travel) {
            continue;  // Away on the world map.
        }
        const math::Vec3 p = creature_position(game, c, alpha);
        if (!mover_shown(game, c.kind == sim::CreatureKind::Soldier, c.town, p.x, p.z)) {
            continue;
        }
        // People stand; animals are low and long.
        const bool person = c.kind == sim::CreatureKind::Raider || c.kind == sim::CreatureKind::Soldier;
        const bool big = c.kind == sim::CreatureKind::Bear;
        const RayHit hit = ray_to_vertical_segment(origin, dir, p, person ? 1.8f : big ? 1.4f : 1.0f);
        if (hit.distance <= (person ? 0.5f : big ? 1.1f : 0.8f) && hit.t < best_t) {
            best_t = hit.t;
            best = store.entities()[k];
        }
    }
    return best;
}

bool VillageView::feature_shown(const sim::Game& game, std::uint32_t feature) const {
    if (feature >= game.map().features.size() || feature >= game.nodes().size()) {
        return false;
    }
    const sim::Node& n = game.nodes()[feature];
    if (n.amount <= 0 && n.regrow_tick == 0) {
        return false;  // Felled or dug out.
    }
    const sim::MapFeature& f = game.map().features[feature];
    return fog_ == nullptr || fog_->mode() == sim::FogMode::None || fog_->explored(to_float(f.x), to_float(f.z));
}

math::Vec3 VillageView::feature_top(const sim::Game& game, std::uint32_t feature) const {
    if (feature >= game.map().features.size()) {
        return {};
    }
    const sim::MapFeature& f = game.map().features[feature];
    const float x = to_float(f.x);
    const float z = to_float(f.z);
    const float height = f.type == sim::FeatureType::Tree
                             ? static_cast<float>(sim::MapData::tree_height_cm(f)) / 100.0f
                             : 1.0f;
    return {x, map_surface_height(game.map(), x, z) + height + 1.0f, z};
}

std::optional<std::uint32_t> VillageView::pick_feature(const sim::Game& game, math::Vec3 origin, math::Vec3 dir) const {
    const sim::MapData& map = game.map();
    // Only those near where the ray meets the ground: the tallest tree
    // leans no farther than this over it.
    const std::optional<math::Vec3> ground = ground_hit(map, origin, dir);
    if (!ground) {
        return std::nullopt;
    }
    constexpr float kReach = 80.0f;
    std::optional<std::uint32_t> best;
    float best_t = 1e30f;
    for (std::size_t i = 0; i < map.features.size(); ++i) {
        const sim::MapFeature& f = map.features[i];
        const float x = to_float(f.x);
        const float z = to_float(f.z);
        if (std::abs(x - ground->x) > kReach || std::abs(z - ground->z) > kReach ||
            !feature_shown(game, static_cast<std::uint32_t>(i))) {
            continue;
        }
        const bool tree = f.type == sim::FeatureType::Tree;
        const float height = tree ? static_cast<float>(sim::MapData::tree_height_cm(f)) / 100.0f : 0.8f;
        const float ground_y = map_surface_height(map, x, z);
        RayHit hit = ray_to_vertical_segment(origin, dir, {x, ground_y, z}, height);
        bool on = hit.distance <= 0.8f;
        if (tree && !on) {
            // Not on the trunk: on the crown, a third of the height wide,
            // over the lower third of the tree.
            hit = ray_to_vertical_segment(origin, dir, {x, ground_y + height * 0.35f, z}, height * 0.5f);
            on = hit.distance <= std::max(1.0f, height * 0.3f);
        }
        if (on && hit.t < best_t) {
            best_t = hit.t;
            best = static_cast<std::uint32_t>(i);
        }
    }
    return best;
}

std::optional<sim::EntityId> VillageView::pick_building(const sim::Game& game, math::Vec3 origin,
                                                        math::Vec3 dir) const {
    std::optional<sim::EntityId> best;
    float best_t = 1e30f;
    const auto& store = game.buildings();
    for (std::size_t k = 0; k < store.size(); ++k) {
        const sim::Building& b = store.data()[k];
        if (!building_shown(game, b)) {
            continue;
        }
        const math::Vec3 top = building_top(game, b);
        const float lo[3] = {static_cast<float>(b.x), top.y - 12.0f, static_cast<float>(b.z)};
        const float hi[3] = {static_cast<float>(b.x + b.width), top.y, static_cast<float>(b.z + b.depth)};
        const float o[3] = {origin.x, origin.y, origin.z};
        const float dv[3] = {dir.x, dir.y, dir.z};
        float t0 = 0.0f;
        float t1 = 1e30f;
        bool hit = true;
        for (int a = 0; a < 3 && hit; ++a) {
            if (std::abs(dv[a]) < 1e-8f) {
                hit = o[a] >= lo[a] && o[a] <= hi[a];
                continue;
            }
            float ta = (lo[a] - o[a]) / dv[a];
            float tb = (hi[a] - o[a]) / dv[a];
            if (ta > tb) {
                std::swap(ta, tb);
            }
            t0 = std::max(t0, ta);
            t1 = std::min(t1, tb);
            hit = t0 <= t1;
        }
        if (hit && t0 < best_t) {
            best_t = t0;
            best = store.entities()[k];
        }
    }
    return best;
}

}  // namespace sc
