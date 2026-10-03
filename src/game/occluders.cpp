#include "game/occluders.h"

#include <algorithm>
#include <cmath>

namespace sc {

namespace {

float to_float(sim::Fixed f) {
    return static_cast<float>(f.raw()) / 65536.0f;
}

}  // namespace

namespace occlusion {

bool segment_hits_box(math::Vec3 a, math::Vec3 b, math::Vec3 lo, math::Vec3 hi) {
    // Slabs: the part of the segment inside each pair of planes.
    float t0 = 0.0f;
    float t1 = 1.0f;
    const float from[3] = {a.x, a.y, a.z};
    const float to[3] = {b.x, b.y, b.z};
    const float low[3] = {lo.x, lo.y, lo.z};
    const float high[3] = {hi.x, hi.y, hi.z};
    for (int axis = 0; axis < 3; ++axis) {
        const float d = to[axis] - from[axis];
        if (std::abs(d) < 1e-6f) {
            if (from[axis] < low[axis] || from[axis] > high[axis]) {
                return false;
            }
            continue;
        }
        float near_t = (low[axis] - from[axis]) / d;
        float far_t = (high[axis] - from[axis]) / d;
        if (near_t > far_t) {
            std::swap(near_t, far_t);
        }
        t0 = std::max(t0, near_t);
        t1 = std::min(t1, far_t);
        if (t0 > t1) {
            return false;
        }
    }
    return true;
}

bool in_crown(math::Vec3 p, float x, float z, float radius, float bottom, float top) {
    const float dx = p.x - x;
    const float dz = p.z - z;
    return p.y >= bottom && p.y <= top && dx * dx + dz * dz <= radius * radius;
}

Crown crown_of(float height, float ground) {
    Crown c;
    c.radius = std::max(1.0f, height * 0.3f);
    c.bottom = ground + height * 0.25f;
    c.top = ground + height;
    return c;
}

float step_level(float level, bool wanted, float dt, float full, float seconds) {
    const float step = seconds > 0.0f ? dt / seconds * full : full;
    return wanted ? std::min(full, level + step) : std::max(0.0f, level - step);
}

}  // namespace occlusion

void Occluders::clear() {
    entries_.clear();
    grid_map_ = nullptr;
    grid_features_ = 0;
    grid_side_ = 0;
    grid_start_.clear();
    grid_items_.clear();
    scene_rebuilds_ = 0;
}

std::size_t Occluders::buildings() const {
    return static_cast<std::size_t>(
        std::count_if(entries_.begin(), entries_.end(), [](const Entry& e) { return !e.tree && e.applied > 0; }));
}

std::size_t Occluders::trees() const {
    return static_cast<std::size_t>(
        std::count_if(entries_.begin(), entries_.end(), [](const Entry& e) { return e.tree && e.applied > 0; }));
}

void Occluders::build_grid(const sim::MapData& map) {
    grid_map_ = &map;
    grid_features_ = map.features.size();
    grid_side_ = std::max(1, (map.size + kCell - 1) / kCell);
    const auto cells = static_cast<std::size_t>(grid_side_) * static_cast<std::size_t>(grid_side_);
    const auto cell_of = [&](const sim::MapFeature& f) {
        const std::int32_t cx = std::clamp(f.x.floor_int() / kCell, 0, grid_side_ - 1);
        const std::int32_t cz = std::clamp(f.z.floor_int() / kCell, 0, grid_side_ - 1);
        return static_cast<std::size_t>(cz) * static_cast<std::size_t>(grid_side_) + static_cast<std::size_t>(cx);
    };
    // Counting sort: how many trees per cell, then each in its place.
    grid_start_.assign(cells + 1, 0);
    for (const sim::MapFeature& f : map.features) {
        if (f.type == sim::FeatureType::Tree) {
            ++grid_start_[cell_of(f) + 1];
        }
    }
    for (std::size_t c = 0; c < cells; ++c) {
        grid_start_[c + 1] += grid_start_[c];
    }
    grid_items_.assign(grid_start_[cells], 0);
    std::vector<std::uint32_t> next(grid_start_.begin(), grid_start_.end() - 1);
    for (std::size_t i = 0; i < map.features.size(); ++i) {
        if (map.features[i].type == sim::FeatureType::Tree) {
            grid_items_[next[cell_of(map.features[i])]++] = static_cast<std::uint32_t>(i);
        }
    }
}

Occluders::Entry& Occluders::entry(bool tree, std::uint32_t feature, sim::EntityId building) {
    for (Entry& e : entries_) {
        if (e.tree == tree && (tree ? e.feature == feature : e.building == building)) {
            return e;
        }
    }
    Entry e;
    e.tree = tree;
    e.feature = feature;
    e.building = building;
    entries_.push_back(e);
    return entries_.back();
}

void Occluders::update(render::SceneRenderer& renderer, const sim::Game& game, VillageView& view, MapScene& scene,
                       math::Vec3 eye, std::optional<math::Vec3> anchor, float dt) {
    const sim::MapData& map = game.map();
    if (grid_map_ != &map || grid_features_ != map.features.size()) {
        entries_.clear();
        build_grid(map);
    }
    for (Entry& e : entries_) {
        e.wanted = false;
    }
    // The line of sight stops short of the anchor, so what stands right
    // behind the one being followed stays as it is.
    math::Vec3 end = eye;
    if (anchor) {
        const math::Vec3 to = *anchor - eye;
        const float length = math::length(to);
        end = length > 1.0f ? eye + to * ((length - 0.75f) / length) : eye;
    }

    // Buildings: their box, from the ground up.
    const auto& store = game.buildings();
    for (std::size_t k = 0; k < store.size(); ++k) {
        const sim::Building& b = store.data()[k];
        const float top = view.building_roof(game, b);
        if (top <= 0.0f) {
            continue;  // Not drawn.
        }
        const float ground = map_surface_height(map, static_cast<float>(b.x) + static_cast<float>(b.width) * 0.5f,
                                                static_cast<float>(b.z) + static_cast<float>(b.depth) * 0.5f);
        const math::Vec3 lo{static_cast<float>(b.x), ground - 2.0f, static_cast<float>(b.z)};
        const math::Vec3 hi{static_cast<float>(b.x + b.width), top, static_cast<float>(b.z + b.depth)};
        if (occlusion::segment_hits_box(eye, end, lo, hi)) {
            entry(false, 0, store.entities()[k]).wanted = true;
        }
    }

    // Trees: the crowns the line of sight goes through, sampled every half
    // meter; around each sample, the trees of its cell and its neighbors.
    const float length = math::length(end - eye);
    const int samples = static_cast<int>(std::min(160.0f, length / 0.5f)) + 1;
    std::int32_t last_cx = -1000, last_cz = -1000;
    std::vector<std::uint32_t> near;
    for (int i = 0; i < samples; ++i) {
        const math::Vec3 p = samples > 1 ? eye + (end - eye) * (static_cast<float>(i) / static_cast<float>(samples - 1)) : eye;
        const auto cx = static_cast<std::int32_t>(std::floor(p.x)) / kCell;
        const auto cz = static_cast<std::int32_t>(std::floor(p.z)) / kCell;
        if (cx != last_cx || cz != last_cz) {
            last_cx = cx;
            last_cz = cz;
            near.clear();
            for (std::int32_t nz = cz - 1; nz <= cz + 1; ++nz) {
                for (std::int32_t nx = cx - 1; nx <= cx + 1; ++nx) {
                    if (nx < 0 || nz < 0 || nx >= grid_side_ || nz >= grid_side_) {
                        continue;
                    }
                    const std::size_t cell = static_cast<std::size_t>(nz) * static_cast<std::size_t>(grid_side_) +
                                             static_cast<std::size_t>(nx);
                    near.insert(near.end(), grid_items_.begin() + grid_start_[cell], grid_items_.begin() + grid_start_[cell + 1]);
                }
            }
        }
        for (const std::uint32_t f : near) {
            if (f < game.nodes().size() && game.nodes()[f].amount <= 0) {
                continue;  // Felled.
            }
            const sim::MapFeature& tree = map.features[f];
            const float x = to_float(tree.x);
            const float z = to_float(tree.z);
            const float height = static_cast<float>(sim::MapData::tree_height_cm(tree)) / 100.0f;
            const float reach = occlusion::crown_of(height, 0.0f).radius;
            if ((p.x - x) * (p.x - x) + (p.z - z) * (p.z - z) > reach * reach) {
                continue;
            }
            const occlusion::Crown crown = occlusion::crown_of(height, map_surface_height(map, x, z));
            if (occlusion::in_crown(p, x, z, crown.radius, crown.bottom, crown.top)) {
                entry(true, f, {}).wanted = true;
            }
        }
    }

    // The transitions, and what changed since the last frame.
    const bool rebuilt = scene.rebuilds() != scene_rebuilds_;
    scene_rebuilds_ = scene.rebuilds();
    bool buildings_changed = false;
    for (Entry& e : entries_) {
        e.level = occlusion::step_level(e.level, e.wanted, dt, static_cast<float>(kFade), kFadeSeconds);
        const auto level = static_cast<std::uint8_t>(std::lround(e.level));
        if (e.tree) {
            // A rebuild of the map's features (a new season) drew the tree whole again.
            if (level != e.applied || (rebuilt && level > 0)) {
                scene.set_feature_fade(renderer, map, game.content(), e.feature, level);
            }
        } else if (level != e.applied) {
            buildings_changed = true;
        }
        e.applied = level;
    }
    if (buildings_changed) {
        std::vector<VillageView::Fade> fades;
        for (const Entry& e : entries_) {
            if (!e.tree && e.applied > 0) {
                fades.push_back({e.building, e.applied});
            }
        }
        view.set_faded_buildings(std::move(fades));
    }
    std::erase_if(entries_, [](const Entry& e) { return !e.wanted && e.level <= 0.0f && e.applied == 0; });
}

}  // namespace sc
