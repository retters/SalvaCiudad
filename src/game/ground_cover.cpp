#include "game/ground_cover.h"

#include <algorithm>
#include <cmath>
#include <numbers>

#include "game/map_scene.h"
#include "game/model_file.h"

namespace sc::cover {

namespace {

constexpr std::string_view kFiles[kKinds] = {
    "models/props/cover_grass_tall.glb",     "models/props/cover_grass_dry.glb",
    "models/props/cover_clover.glb",         "models/props/cover_fern.glb",
    "models/props/cover_reeds.glb",          "models/props/cover_flowers_red.glb",
    "models/props/cover_flowers_yellow.glb", "models/props/cover_flowers_blue.glb",
    "models/props/cover_flowers_white.glb",  "models/props/cover_flowers_mixed.glb",
    "models/props/cover_sunflowers.glb",     "models/props/cover_petals_pink.glb",
    "models/props/cover_petals_purple.glb",  "models/props/cover_alpine_flowers.glb",
    "models/props/cover_scree.glb",          "models/props/cover_crag.glb",
    "models/props/cover_driftwood.glb",      "models/props/cover_shells.glb",
    "models/props/cover_tide_pool.glb",      "models/props/cover_snow_drift.glb",
    "models/props/cover_ice_floe.glb",       "models/props/cover_snowman.glb",
};

// Meters a plant bends at one meter of height.
constexpr float kSway = 0.05f;

// A number from a place: the same wherever and whenever it is asked.
std::uint32_t mix(std::int32_t x, std::int32_t z, std::uint32_t salt) {
    std::uint32_t h = static_cast<std::uint32_t>(x) * 0x9E3779B1u ^ static_cast<std::uint32_t>(z) * 0x85EBCA77u ^
                      (salt + 1u) * 0xC2B2AE3Du;
    h ^= h >> 15;
    h *= 0x2C1B3C6Du;
    h ^= h >> 12;
    h *= 0x297A2D39u;
    h ^= h >> 15;
    return h;
}

float unit(std::uint32_t h, std::uint32_t shift) {
    return static_cast<float>((h >> shift) & 0xFFu) / 255.0f;
}

bool inside(const sim::MapData& map, std::int32_t cx, std::int32_t cz) {
    return cx >= 0 && cz >= 0 && cx < map.size && cz < map.size;
}

bool water(const sim::MapData& map, std::int32_t cx, std::int32_t cz) {
    return inside(map, cx, cz) && map.water_at(cx, cz);
}

// Whether a cell of water is the sea: its surface is at its region's sea level.
bool sea(const sim::MapData& map, std::int32_t cx, std::int32_t cz) {
    if (!water(map, cx, cz)) {
        return false;
    }
    const std::size_t cell = static_cast<std::size_t>(cz) * static_cast<std::size_t>(map.size) + static_cast<std::size_t>(cx);
    const auto region = static_cast<std::size_t>(map.region_at(cx, cz));
    return region < map.sea_levels.size() && map.sea_levels[region] != 0 && map.water[cell] == map.sea_levels[region];
}

// How much the ground rises across a square, in centimeters.
std::int32_t rise_cm(const sim::MapData& map, std::int32_t sx, std::int32_t sz) {
    std::int32_t low = 0x7FFFFFFF;
    std::int32_t high = 0;
    for (std::int32_t dz = 0; dz <= kSquare; dz += 2) {
        for (std::int32_t dx = 0; dx <= kSquare; dx += 2) {
            const std::int32_t vx = std::clamp(sx * kSquare + dx, 0, map.size);
            const std::int32_t vz = std::clamp(sz * kSquare + dz, 0, map.size);
            const std::int32_t h = map.height_cm(vx, vz);
            low = std::min(low, h);
            high = std::max(high, h);
        }
    }
    return high - low;
}

bool has(std::uint8_t cover, sim::BiomeCover bit) {
    return (cover & (1u << static_cast<unsigned>(bit))) != 0;
}

std::uint64_t key(std::int32_t x, std::int32_t z) {
    return (static_cast<std::uint64_t>(static_cast<std::uint32_t>(x)) << 32) | static_cast<std::uint32_t>(z);
}

}  // namespace

std::string_view model_file(Kind kind) {
    return kind < Kind::Count ? kFiles[static_cast<std::size_t>(kind)] : std::string_view{};
}

bool plant(Kind kind) {
    return kind <= Kind::AlpineFlowers;
}

When when(const sim::Game& game) {
    When w;
    w.season = game.calendar().season;
    w.snow = game.snow() >= 30;
    w.frozen = game.frozen();
    return w;
}

float reach(int detail) {
    constexpr float kReach[] = {0.0f, 64.0f, 96.0f, 160.0f};
    return kReach[std::clamp(detail, 0, 3)];
}

bool sways(int detail) {
    return detail >= 2;
}

std::optional<Item> item_at(const sim::MapData& map, const sim::Content& content, const When& when, std::int32_t sx,
                            std::int32_t sz) {
    const std::uint32_t h = mix(sx, sz, 0);
    // Somewhere inside the square, half a meter in from its edges.
    Item item;
    item.x = static_cast<float>(sx * kSquare) + 0.5f + unit(h, 0) * static_cast<float>(kSquare - 1);
    item.z = static_cast<float>(sz * kSquare) + 0.5f + unit(h, 8) * static_cast<float>(kSquare - 1);
    const auto cx = static_cast<std::int32_t>(std::floor(item.x));
    const auto cz = static_cast<std::int32_t>(std::floor(item.z));
    if (!inside(map, cx, cz)) {
        return std::nullopt;
    }
    const std::uint32_t more = mix(sx, sz, 1);
    const std::uint32_t roll = more % 1000u;        // Per thousand.
    const std::uint32_t pick = (more >> 12) & 63u;  // Which of several alike.
    item.yaw = unit(more, 20) * 2.0f * std::numbers::pi_v<float>;
    item.scale = 0.85f + 0.3f * unit(h, 16);
    const auto take = [&](Kind kind) {
        item.kind = kind;
        return std::optional<Item>(item);
    };

    if (map.water_at(cx, cz)) {
        // Ice floes, away from the shore, while it freezes.
        const bool open = water(map, cx - 2, cz) && water(map, cx + 2, cz) && water(map, cx, cz - 2) && water(map, cx, cz + 2);
        return when.frozen && open && roll < 30 ? take(Kind::IceFloe) : std::nullopt;
    }
    const sim::Terrain terrain = map.terrain_at(cx, cz);
    const std::uint8_t b = map.biome_at(cx, cz);
    const std::uint8_t biome = b < content.flora.biomes.size() ? content.flora.biomes[b].cover : std::uint8_t{0};

    // The shore: what the sea leaves on the sand, reeds by fresh water.
    bool by_sea = false;
    bool by_fresh = false;
    for (std::int32_t d = 2; d <= 6; d += 2) {
        for (const auto& [dx, dz] : {std::pair{d, 0}, std::pair{-d, 0}, std::pair{0, d}, std::pair{0, -d}}) {
            if (water(map, cx + dx, cz + dz)) {
                (sea(map, cx + dx, cz + dz) ? by_sea : by_fresh) = true;
            }
        }
    }
    if (by_sea && terrain == sim::Terrain::Sand) {
        return roll < 40 ? take(Kind::Driftwood) : roll < 100 ? take(Kind::Shells) : roll < 112 ? take(Kind::TidePool) : std::nullopt;
    }
    const bool at_the_edge = water(map, cx + 2, cz) || water(map, cx - 2, cz) || water(map, cx, cz + 2) || water(map, cx, cz - 2);
    if (by_fresh && !by_sea && at_the_edge && terrain != sim::Terrain::Rock && roll < 400) {
        return take(Kind::Reeds);
    }
    // Rock: crags where the ground is too steep to walk, scree on bare rock.
    if (has(biome, sim::BiomeCover::Crag) && rise_cm(map, sx, sz) >= 300 && roll < 70) {
        item.scale = 0.8f + 0.4f * unit(h, 16);
        return take(Kind::Crag);
    }
    if (has(biome, sim::BiomeCover::Scree) && terrain == sim::Terrain::Rock && roll < 90) {
        return take(Kind::Scree);
    }
    if (when.snow) {
        return std::nullopt;  // The plants are under the snow.
    }
    const bool spring = when.season == sim::Season::Spring;
    const bool summer = when.season == sim::Season::Summer;
    if (terrain == sim::Terrain::ForestFloor) {
        if (has(biome, sim::BiomeCover::Petals) && spring && roll < 300) {
            return take((pick & 1u) != 0 ? Kind::PetalsPink : Kind::PetalsPurple);
        }
        if (has(biome, sim::BiomeCover::Ferns) && roll >= 300 && roll < 440) {
            return take(Kind::Fern);
        }
        return std::nullopt;
    }
    if (terrain != sim::Terrain::Meadow && terrain != sim::Terrain::Grass) {
        return std::nullopt;
    }
    // Wild flowers come up in spring and go in autumn; sunflowers are summer's.
    const std::int32_t flowers = sim::wildflowers(map, content, cx, cz);
    if ((spring || summer) && roll < static_cast<std::uint32_t>(flowers) * 5u) {
        if (has(biome, sim::BiomeCover::Alpine)) {
            return take(Kind::AlpineFlowers);
        }
        if (summer && pick % 6u == 0) {
            return take(Kind::Sunflowers);
        }
        constexpr Kind kColors[] = {Kind::FlowersRed, Kind::FlowersYellow, Kind::FlowersBlue, Kind::FlowersWhite, Kind::FlowersMixed};
        return take(kColors[pick % 5u]);
    }
    if (roll >= 500 && roll < 590) {
        // Tall grass, dry after the spring where summers are dry, and everywhere from autumn on.
        const bool dry = (has(biome, sim::BiomeCover::DryGrass) && !spring) || when.season == sim::Season::Autumn ||
                         when.season == sim::Season::Winter;
        return take(dry ? Kind::GrassDry : Kind::GrassTall);
    }
    if (has(biome, sim::BiomeCover::Clover) && (spring || summer) && roll >= 590 && roll < 630) {
        return take(Kind::Clover);
    }
    return std::nullopt;
}

std::optional<Item> drift_by(std::int32_t x, std::int32_t z, std::int32_t w, std::int32_t d) {
    const std::uint32_t h = mix(x, z, 2);
    if ((h & 1u) != 0) {
        return std::nullopt;
    }
    // Against the middle part of one of its four walls, half a meter out.
    const std::uint32_t side = (h >> 1) & 3u;
    const float t = 0.25f + 0.5f * unit(h, 8);
    Item item;
    item.kind = Kind::SnowDrift;
    const auto fx = static_cast<float>(x), fz = static_cast<float>(z), fw = static_cast<float>(w), fd = static_cast<float>(d);
    switch (side) {
        case 0: item.x = fx + fw * t; item.z = fz - 0.5f; break;
        case 1: item.x = fx + fw * t; item.z = fz + fd + 0.5f; break;
        case 2: item.x = fx - 0.5f; item.z = fz + fd * t; break;
        default: item.x = fx + fw + 0.5f; item.z = fz + fd * t; break;
    }
    item.yaw = static_cast<float>(side < 2 ? 0 : 1) * std::numbers::pi_v<float> * 0.5f;
    item.scale = 0.8f + 0.4f * unit(h, 16);
    return item;
}

std::optional<Item> snowman_by(std::int32_t x, std::int32_t z, std::int32_t w, std::int32_t d) {
    const std::uint32_t h = mix(x, z, 3);
    if (h % 3u != 0) {
        return std::nullopt;
    }
    Item item;
    item.kind = Kind::Snowman;
    // Off one of its corners, a good step away.
    item.x = (h & 4u) != 0 ? static_cast<float>(x) - 1.2f : static_cast<float>(x + w) + 1.2f;
    item.z = (h & 8u) != 0 ? static_cast<float>(z) - 1.2f : static_cast<float>(z + d) + 1.2f;
    item.yaw = unit(h, 8) * 2.0f * std::numbers::pi_v<float>;
    item.scale = 0.9f + 0.2f * unit(h, 16);
    return item;
}

void GroundCover::load(render::SceneRenderer& renderer, const mods::BuildResult& pack) {
    if (loaded_) {
        return;
    }
    models_.fill(kNoModel);
    for (std::size_t k = 0; k < kKinds; ++k) {
        const std::filesystem::path file = mods::mod_file(pack.dir("core"), kFiles[k]);
        const auto data = file.empty() ? std::nullopt : load_model_file(file);
        render::ModelId id = 0;
        if (!data.has_value() || !renderer.add_model(*data, id)) {
            continue;  // Not drawn.
        }
        models_[k] = id;
        if (plant(static_cast<Kind>(k))) {
            renderer.set_model_class(id, render::ModelClass::SmallVegetation);
        }
    }
    loaded_ = true;
}

void GroundCover::reset(render::SceneRenderer& renderer) {
    chunks_.clear();
    blocked_.clear();
    map_ = nullptr;
    filled_ = false;
    shown_ = 0;
    ++blocked_version_;
    for (std::size_t k = 0; k < kKinds; ++k) {
        lists_[k].clear();
        if (loaded_ && models_[k] != kNoModel) {
            renderer.set_instances(models_[k], lists_[k]);
        }
    }
}

void GroundCover::block(const sim::Game& game) {
    blocked_.clear();
    // A square is bare if any of it lies under the place, with a meter around.
    const auto take = [&](std::int32_t x, std::int32_t z, std::int32_t w, std::int32_t d) {
        const std::int32_t x0 = (x - 1) >= 0 ? (x - 1) / kSquare : -1;
        const std::int32_t z0 = (z - 1) >= 0 ? (z - 1) / kSquare : -1;
        for (std::int32_t sz = z0; sz <= (z + d) / kSquare; ++sz) {
            for (std::int32_t sx = x0; sx <= (x + w) / kSquare; ++sx) {
                blocked_.insert(key(sx, sz));
            }
        }
    };
    for (const sim::Building& b : game.buildings().data()) {
        take(b.x, b.z, b.width, b.depth);
        for (const sim::Field& f : b.fields) {
            take(f.x, f.z, f.w, f.d);
        }
    }
    // Phase 95: nor on a road.
    const auto side = static_cast<std::uint32_t>(std::max(1, game.road_side()));
    for (const auto& [cell, kind] : game.roads()) {
        take(static_cast<std::int32_t>(cell % side) * sim::kRoadModule, static_cast<std::int32_t>(cell / side) * sim::kRoadModule,
             sim::kRoadModule, sim::kRoadModule);
    }
}

const GroundCover::Chunk& GroundCover::chunk(const sim::Game& game, std::int32_t cx, std::int32_t cz) {
    const auto [it, added] = chunks_.try_emplace(key(cx, cz));
    if (added) {
        constexpr std::int32_t kSide = kChunk / kSquare;
        for (std::int32_t sz = cz * kSide; sz < (cz + 1) * kSide; ++sz) {
            for (std::int32_t sx = cx * kSide; sx < (cx + 1) * kSide; ++sx) {
                if (blocked_.contains(key(sx, sz))) {
                    continue;
                }
                if (const std::optional<Item> item = item_at(game.map(), game.content(), when_, sx, sz)) {
                    it->second.items.push_back(*item);
                }
            }
        }
    }
    return it->second;
}

void GroundCover::update(render::SceneRenderer& renderer, const sim::Game& game, math::Vec3 focus, int detail) {
    if (!loaded_) {
        return;
    }
    detail = std::clamp(detail, 0, 3);
    const sim::MapData& map = game.map();
    const When now = when(game);
    if (map_ != &map || !(now == when_) || blocked_built_ != blocked_version_) {
        chunks_.clear();
        when_ = now;
        map_ = &map;
        block(game);
        blocked_built_ = blocked_version_;
        filled_ = false;
    }
    if (detail != detail_) {
        detail_ = detail;
        for (std::size_t k = 0; k < kKinds; ++k) {
            if (models_[k] != kNoModel && plant(static_cast<Kind>(k))) {
                renderer.set_model_sway(models_[k], sways(detail) ? kSway : 0.0f);
            }
        }
        filled_ = false;
    }
    const auto fcx = static_cast<std::int32_t>(std::floor(focus.x / static_cast<float>(kChunk)));
    const auto fcz = static_cast<std::int32_t>(std::floor(focus.z / static_cast<float>(kChunk)));
    if (filled_ && fcx == focus_cx_ && fcz == focus_cz_) {
        return;
    }
    focus_cx_ = fcx;
    focus_cz_ = fcz;
    filled_ = true;
    for (std::vector<render::Instance>& list : lists_) {
        list.clear();
    }
    shown_ = 0;
    const auto put = [&](const Item& item) {
        const auto k = static_cast<std::size_t>(item.kind);
        if (models_[k] == kNoModel) {
            return;
        }
        render::Instance inst;
        inst.position = {item.x, map_surface_height(map, item.x, item.z), item.z};
        inst.yaw = item.yaw;
        inst.scale = item.scale;
        lists_[k].push_back(inst);
        ++shown_;
    };
    const float far = reach(detail);
    if (far > 0.0f) {
        const auto span = static_cast<std::int32_t>(std::ceil(far / static_cast<float>(kChunk)));
        const std::int32_t last = (map.size - 1) / kChunk;
        for (std::int32_t cz = std::max(0, fcz - span); cz <= std::min(last, fcz + span); ++cz) {
            for (std::int32_t cx = std::max(0, fcx - span); cx <= std::min(last, fcx + span); ++cx) {
                if ((cx - fcx) * (cx - fcx) + (cz - fcz) * (cz - fcz) > span * span) {
                    continue;
                }
                for (const Item& item : chunk(game, cx, cz).items) {
                    put(item);
                }
            }
        }
        // Winter in town: snow blown against the walls, and the children's snowmen.
        if (now.snow) {
            const sim::Content& content = game.content();
            const float limit = far + static_cast<float>(kChunk);
            std::array<int, sim::kMaxPlayers> children{};  // -1 none, 1 some, 0 not looked at yet.
            for (const sim::Building& b : game.buildings().data()) {
                const float dx = static_cast<float>(b.x) - focus.x;
                const float dz = static_cast<float>(b.z) - focus.z;
                if (b.state != sim::BuildingState::Complete || dx * dx + dz * dz > limit * limit) {
                    continue;
                }
                const sim::BuildingDef& d = content.buildings[b.def];
                if (d.cart) {
                    continue;
                }
                if (const std::optional<Item> drift = drift_by(b.x, b.z, b.width, b.depth)) {
                    put(*drift);
                }
                if (d.kind != sim::BuildingKind::Decoration || d.category != sim::kPlazaCategory || b.owner >= sim::kMaxPlayers) {
                    continue;
                }
                if (children[b.owner] == 0) {
                    children[b.owner] = game.population(b.owner) > game.population(b.owner, true) ? 1 : -1;
                }
                if (children[b.owner] > 0) {
                    if (const std::optional<Item> snowman = snowman_by(b.x, b.z, b.width, b.depth)) {
                        put(*snowman);
                    }
                }
            }
        }
    }
    for (std::size_t k = 0; k < kKinds; ++k) {
        if (models_[k] != kNoModel) {
            renderer.set_instances(models_[k], lists_[k]);
        }
    }
}

}  // namespace sc::cover
