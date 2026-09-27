#include "game/village_view.h"

#include <algorithm>
#include <cmath>
#include <numbers>

#include "core/log.h"
#include "game/camera.h"

namespace sc {

namespace {

float to_float(sim::Fixed f) {
    return static_cast<float>(f.raw()) / 65536.0f;
}

// Villagers walk 0.2 m per tick (sim/game.cpp), ten ticks a second at x1.
constexpr float kWalkMetersPerSecond = 2.0f;

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
    def_models_.assign(content.buildings.size(), Model{});
    std::size_t missing = 0;
    for (std::size_t i = 0; i < content.buildings.size(); ++i) {
        const sim::BuildingDef& d = content.buildings[i];
        const std::filesystem::path file = mods::mod_file(pack.dir(d.mod), d.model);
        if (file.empty()) {
            ++missing;
            continue;
        }
        const std::string key = file.generic_string();
        auto it = files_.find(key);
        if (it == files_.end()) {
            Model m;
            const auto data = load_model_file(file);
            render::ModelId id = 0;
            if (data.has_value() && renderer.add_model(*data, id)) {
                m.id = id;
                m.height = std::max(0.1f, data->bounds_max.y - data->bounds_min.y);
                m.width = std::max(0.1f, data->bounds_max.x - data->bounds_min.x);
                m.depth = std::max(0.1f, data->bounds_max.z - data->bounds_min.z);
                used_.push_back(id);
            }
            it = files_.emplace(key, m).first;
        }
        def_models_[i] = it->second;
        missing += it->second.id == kNoModel ? 1 : 0;
    }
    if (missing > 0) {
        log::warn("village: {} building model(s) missing; those buildings will not be drawn", missing);
    }
}

void VillageView::set_bodies(const std::vector<TestCrowd::BodyKind>* bodies, std::uint32_t palette_count) {
    bodies_ = bodies;
    palette_count_ = std::max(1u, palette_count);
}

void VillageView::begin(render::SceneRenderer& renderer, MapScene& scene, sim::Game& game) {
    shown_ = true;
    looks_.clear();
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
    ghost_.reset();
    shown_ = false;
}

void VillageView::set_ghost(std::optional<Ghost> ghost) {
    if (ghost != ghost_) {
        ghost_ = ghost;
        ghost_changed_ = true;
    }
}

void VillageView::update(render::SceneRenderer& renderer, MapScene& scene, sim::Game& game, float alpha, float dt,
                         int speed) {
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
    if (game.take_buildings_changed() || ghost_changed_) {
        rebuild_buildings(renderer, game);
        ghost_changed_ = false;
    }
    update_characters(renderer, game, alpha, dt, speed);
}

render::Instance VillageView::building_instance(const sim::Game& game, sim::DefIndex def, std::int32_t x,
                                                std::int32_t z, std::int32_t w, std::int32_t d, std::uint8_t rotation,
                                                float progress) const {
    const sim::BuildingDef& bd = game.content().buildings[def];
    const Model& m = def_models_[def];
    render::Instance inst;
    // Sit on the lowest corner so no corner floats on a slope.
    std::int32_t low = 65535;
    for (const std::int32_t vz : {z, z + d}) {
        for (const std::int32_t vx : {x, x + w}) {
            low = std::min<std::int32_t>(low, game.map().height_cm(vx, vz));
        }
    }
    inst.scale = std::min(static_cast<float>(bd.width) / m.width, static_cast<float>(bd.depth) / m.depth) * 0.95f;
    inst.position = {static_cast<float>(x) + static_cast<float>(w) * 0.5f, static_cast<float>(low) * 0.01f - 0.1f,
                     static_cast<float>(z) + static_cast<float>(d) * 0.5f};
    // Models face +Z; rotation 0 puts the door on the -Z side.
    inst.yaw = std::numbers::pi_v<float> - static_cast<float>(rotation) * std::numbers::pi_v<float> * 0.5f;
    if (progress < 1.0f) {
        // Rises out of the ground as it is built; unfinished wood color.
        const float shown = 0.08f + 0.92f * std::clamp(progress, 0.0f, 1.0f);
        inst.position.y -= (1.0f - shown) * m.height * inst.scale;
        inst.tint = {0.85f, 0.72f, 0.55f};
    }
    return inst;
}

void VillageView::rebuild_buildings(render::SceneRenderer& renderer, const sim::Game& game) {
    std::map<render::ModelId, std::vector<render::Instance>> lists;
    for (const render::ModelId id : used_) {
        lists[id];
    }
    const sim::Content& content = game.content();
    for (const sim::Building& b : game.buildings().data()) {
        if (b.def >= def_models_.size() || def_models_[b.def].id == kNoModel) {
            continue;
        }
        const sim::BuildingDef& d = content.buildings[b.def];
        float progress = 1.0f;
        if (b.state == sim::BuildingState::Construction) {
            progress = d.build_work > 0 ? static_cast<float>(b.work_done) / static_cast<float>(d.build_work) : 1.0f;
        }
        lists[def_models_[b.def].id].push_back(
            building_instance(game, b.def, b.x, b.z, b.width, b.depth, b.rotation, progress));
    }
    if (ghost_ && ghost_->def < def_models_.size() && def_models_[ghost_->def].id != kNoModel) {
        std::int32_t w = 0, d = 0;
        sim::Game::footprint(content.buildings[ghost_->def], ghost_->rotation, w, d);
        render::Instance g = building_instance(game, ghost_->def, ghost_->x, ghost_->z, w, d, ghost_->rotation, 1.0f);
        g.tint = ghost_->allowed ? math::Vec3{0.55f, 1.6f, 0.6f} : math::Vec3{1.8f, 0.45f, 0.4f};
        lists[def_models_[ghost_->def].id].push_back(g);
    }
    for (auto& [id, list] : lists) {
        renderer.set_instances(id, list);
    }
}

math::Vec3 VillageView::villager_position(const sim::Game& game, const sim::Villager& v, float alpha) const {
    const float x = to_float(v.previous.x) + (to_float(v.position.x) - to_float(v.previous.x)) * alpha;
    const float z = to_float(v.previous.z) + (to_float(v.position.z) - to_float(v.previous.z)) * alpha;
    return {x, map_surface_height(game.map(), x, z), z};
}

math::Vec3 VillageView::building_top(const sim::Game& game, const sim::Building& b) const {
    const math::Vec3 base{static_cast<float>(b.x) + static_cast<float>(b.width) * 0.5f, 0.0f,
                          static_cast<float>(b.z) + static_cast<float>(b.depth) * 0.5f};
    float h = 5.0f;
    if (b.def < def_models_.size() && def_models_[b.def].id != kNoModel) {
        const sim::BuildingDef& d = game.content().buildings[b.def];
        const Model& m = def_models_[b.def];
        h = m.height * std::min(static_cast<float>(d.width) / m.width, static_cast<float>(d.depth) / m.depth) * 0.95f;
    }
    return {base.x, map_surface_height(game.map(), base.x, base.z) + h + 1.0f, base.z};
}

void VillageView::update_characters(render::SceneRenderer& renderer, const sim::Game& game, float alpha, float dt,
                                    int speed) {
    characters_.clear();
    if (bodies_ == nullptr || bodies_->empty()) {
        renderer.set_characters({});
        return;
    }
    const auto& store = game.villagers();
    for (std::size_t k = 0; k < store.size(); ++k) {
        const sim::EntityId id = store.entities()[k];
        const sim::Villager& v = store.data()[k];
        if (id.index >= looks_.size()) {
            looks_.resize(static_cast<std::size_t>(id.index) + 1);
        }
        Look& look = looks_[id.index];
        const bool moving = v.position != v.previous;
        if (look.generation != id.generation) {
            look = Look{};
            look.generation = id.generation;
            look.yaw = static_cast<float>(v.appearance % 628u) / 100.0f;
            look.time = static_cast<float>((v.appearance >> 10) % 1000u) / 1000.0f;
        }
        if (moving) {
            const float want = std::atan2(to_float(v.position.x - v.previous.x), to_float(v.position.z - v.previous.z));
            look.yaw += wrap_angle(want - look.yaw) * std::min(1.0f, dt * 8.0f);
        }
        const float rate = moving ? kWalkMetersPerSecond * static_cast<float>(speed) / TestCrowd::kWalkReferenceSpeed
                                  : 1.0f;
        look.time += dt * rate;

        // The body by sex, a palette and accessories from the appearance bits.
        const bool female = v.sex == sim::Sex::Female;
        const TestCrowd::BodyKind* kind = &bodies_->front();
        for (const TestCrowd::BodyKind& b : *bodies_) {
            if (b.female == female) {
                kind = &b;
            }
        }
        render::CharacterInstance c;
        c.body = kind->id;
        c.clip = moving ? kind->walk : kind->idle;
        c.time = look.time;
        c.position = villager_position(game, v, alpha);
        c.yaw = look.yaw;
        const std::int32_t age = game.age_years(v);
        c.scale = age < sim::village::kAdultAgeYears
                      ? 0.55f + 0.4f * static_cast<float>(age) / static_cast<float>(sim::village::kAdultAgeYears)
                      : 0.94f + static_cast<float>((v.appearance >> 3) % 12u) / 100.0f;
        c.palette = v.appearance % palette_count_;
        std::uint32_t mask = 0;
        const std::uint32_t bits = v.appearance >> 16;
        const std::uint32_t hat = bits % 3u;
        if (hat > 0 && hat <= kind->hats.size()) {
            mask |= 1u << kind->hats[hat - 1];
        }
        if (kind->beard != ~0u && age >= sim::village::kAdultAgeYears && (bits >> 2) % 3u == 0) {
            mask |= 1u << kind->beard;
        }
        if (kind->apron != ~0u && (bits >> 4) % 4u == 0) {
            mask |= 1u << kind->apron;
        }
        c.accessories = mask;
        characters_.push_back(c);
    }
    renderer.set_characters(characters_);
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
        const RayHit hit = ray_to_vertical_segment(origin, dir, p, kHeight);
        if (hit.distance <= kRadius && hit.t < best_t) {
            best_t = hit.t;
            best = store.entities()[k];
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
