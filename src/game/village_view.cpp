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
        if (id != tile_model_ && id != plant_model_) {
            lists[id];
        }
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
        if (id != tile_model_ && id != plant_model_) {
            renderer.set_instances(id, list);
        }
    }
    rebuild_fields(renderer, game);
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
        std::uint32_t hat = bits % 3u;
        // The season decides the hat: a cap for everybody in winter, a straw
        // hat in summer for those who wear one.
        if (season_ == sim::Season::Winter && kind->hats.size() >= 2) {
            hat = 2;
        } else if (season_ == sim::Season::Summer && hat == 2) {
            hat = 1;
        }
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
