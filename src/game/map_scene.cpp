#include "game/map_scene.h"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <numbers>

#include "core/log.h"
#include "game/builtin_models.h"
#include "game/variants.h"
#include "game/model_file.h"

namespace sc {

namespace {

float to_float(sim::Fixed f) {
    return static_cast<float>(f.raw()) / 65536.0f;
}

std::uint32_t hash2(std::uint32_t x, std::uint32_t z) {
    std::uint32_t h = (x * 0x8DA6B343u) ^ (z * 0xD8163841u);
    h ^= h >> 13;
    h *= 0x5BD1E995u;
    h ^= h >> 15;
    return h;
}

render::ModelClass feature_class(sim::FeatureType t) {
    return t == sim::FeatureType::BerryBush || t == sim::FeatureType::Herbs ? render::ModelClass::SmallVegetation
                                                                               : render::ModelClass::Normal;
}

}  // namespace

std::size_t tree_variant_slot(std::size_t species, std::size_t variant) {
    return species * kSpeciesSlots + variant;
}

std::size_t tree_slot_count(const sim::Content& content) {
    return content.flora.species.size() * kSpeciesSlots;
}

TreeCalendar tree_calendar(sim::Season season, std::uint32_t season_progress) {
    const std::uint32_t step = season_progress * static_cast<std::uint32_t>(kTurnSteps) / kTurnProgress;
    return {season, static_cast<int>(std::min<std::uint32_t>(step, static_cast<std::uint32_t>(kTurnSteps)))};
}

namespace {

sim::TreeState state_of(sim::Season season) {
    switch (season) {
        case sim::Season::Autumn: return sim::TreeState::Autumn;
        case sim::Season::Winter: return sim::TreeState::Bare;
        default: return sim::TreeState::Bloom;
    }
}

sim::Season season_before(sim::Season season) {
    const auto count = static_cast<std::uint32_t>(sim::Season::Count);
    return static_cast<sim::Season>((static_cast<std::uint32_t>(season) + count - 1) % count);
}

}  // namespace

int tree_turn(const sim::MapFeature& f) {
    const std::uint32_t h = hash2(static_cast<std::uint32_t>(f.z.raw()) ^ 0x51ED270Bu, static_cast<std::uint32_t>(f.x.raw()));
    return static_cast<int>((h >> 11) % static_cast<std::uint32_t>(kTurnSteps));
}

sim::TreeState tree_state(const sim::MapFeature& f, TreeCalendar when) {
    return state_of(when.turn > tree_turn(f) ? when.season : season_before(when.season));
}

std::size_t visual_slot_count(const sim::Content& content) {
    return tree_slot_count(content) + static_cast<std::size_t>(sim::FeatureType::Count) * sim::kMaxModelVariants;
}

std::size_t feature_slot(const sim::Content& content, sim::FeatureType type, std::size_t variant) {
    return tree_slot_count(content) + static_cast<std::size_t>(type) * sim::kMaxModelVariants + variant;
}

std::uint8_t tree_look(const sim::Content& content, const sim::MapFeature& f, TreeCalendar when) {
    if (f.type != sim::FeatureType::Tree || f.species >= content.flora.species.size()) {
        return 0;
    }
    const auto state = static_cast<std::size_t>(tree_state(f, when));
    return content.flora.species[f.species].state_models[state].empty() ? std::uint8_t{0} : static_cast<std::uint8_t>(state);
}

std::uint8_t feature_look(const sim::Content& content, const sim::MapFeature& f, TreeCalendar when) {
    // A stone deposit's sizes are the looks of one model (phase 83).
    if (f.type == sim::FeatureType::StoneDeposit) {
        return std::min<std::uint8_t>(f.size, sim::kDepositSizes - 1);
    }
    if (f.type == sim::FeatureType::Tree) {
        return tree_look(content, f, when);
    }
    // Phase 99: what gives by seasons, if it has the models for it: in
    // flower in spring (look 2), green out of its seasons (look 1), and
    // with its fruit, itself.
    const sim::FeatureDef* def = content.feature(f.type);
    if (def == nullptr || def->seasons == 0) {
        return 0;
    }
    if (when.season == sim::Season::Spring && !def->model_flower.empty()) {
        return kFlowerLook;
    }
    const bool in_season = ((def->seasons >> static_cast<unsigned>(when.season)) & 1u) != 0;
    return !in_season && !def->model_green.empty() ? kGreenLook : std::uint8_t{0};
}

std::size_t visual_slot(const sim::Content& content, const sim::MapFeature& f, const sim::MapData* map) {
    if (f.type == sim::FeatureType::Tree) {
        // One of the variants, by the place; the state is its look.
        const std::size_t variants =
            f.species < content.flora.species.size() ? content.flora.species[f.species].state_models[0].size() : 1;
        return tree_variant_slot(
            f.species, pick_variant(place_key(static_cast<std::int32_t>(f.x.raw()), static_cast<std::int32_t>(f.z.raw())),
                                    std::clamp<std::size_t>(variants, 1, sim::kMaxModelVariants)));
    }
    // Phase 102: the stone of the biome the feature stands in (gray without a map).
    const auto rock = [&]() -> std::size_t {
        if (map == nullptr) {
            return 0;
        }
        const std::size_t biome = map->biome_at(f.x.floor_int(), f.z.floor_int());
        return biome < content.flora.biomes.size() ? content.flora.biomes[biome].rock : 0;
    };
    if (f.type == sim::FeatureType::StoneDeposit) {
        // Its files are its sizes, not variants. After them it may list its
        // small size in mossy and in sandstone: a small one is the outcrop of
        // its biome (phase 102); worn down from a larger one, too.
        const sim::FeatureDef* def = content.feature(f.type);
        const std::size_t kind = f.size == 0 ? rock() : 0;
        const std::size_t file = sim::kDepositSizes + kind - 1;
        return feature_slot(content, f.type,
                            kind != 0 && def != nullptr && file < def->models.size() && file < sim::kMaxModelVariants ? file : 0);
    }
    if (sim::is_deposit(f.type)) {
        return feature_slot(content, f.type, 0);  // One file.
    }
    if (const sim::FeatureDef* def = content.feature(f.type); def != nullptr && def->rock_of_biome) {
        // Its files are the stones of the biomes: gray, mossy, sandstone.
        const std::size_t kind = rock();
        return feature_slot(content, f.type, kind < def->models.size() && kind < sim::kMaxModelVariants ? kind : 0);
    }
    if (f.type == sim::FeatureType::BerryBush) {
        // Its files are the bushes of the biomes: berries, blueberries, brambles (phase 99).
        const sim::FeatureDef* bush = content.feature(f.type);
        const std::size_t files = bush != nullptr ? bush->models.size() : 1;
        std::size_t kind = 0;
        if (map != nullptr) {
            const std::size_t biome = map->biome_at(f.x.floor_int(), f.z.floor_int());
            kind = biome < content.flora.biomes.size() ? content.flora.biomes[biome].bush : 0;
        }
        return feature_slot(content, f.type, kind < files && kind < sim::kMaxModelVariants ? kind : 0);
    }
    // Each other kind has room for its variants; the place picks one.
    const sim::FeatureDef* def = content.feature(f.type);
    const std::size_t variants = def != nullptr ? def->models.size() : 1;
    return feature_slot(content, f.type,
                        pick_variant(place_key(static_cast<std::int32_t>(f.x.raw()), static_cast<std::int32_t>(f.z.raw())),
                                     std::min(variants, sim::kMaxModelVariants)));
}

std::string tree_model_file(const sim::SpeciesDef& species, sim::TreeState state) {
    const std::vector<std::string>& files = species.state_models[static_cast<std::size_t>(state)];
    const std::vector<std::string>& bloom = species.state_models[0];
    return !files.empty() ? files.front() : !bloom.empty() ? bloom.front() : std::string();
}

std::size_t MapVisuals::feature_count() const {
    std::size_t n = 0;
    for (const auto& list : features) {
        n += list.size();
    }
    return n;
}

Rgb8 ground_color(sim::Terrain terrain, std::uint8_t fertility, std::uint32_t cell_hash) {
    float r = 0.0f;
    float g = 0.0f;
    float b = 0.0f;
    bool grows = false;  // Plant cover that dries out on poor soil.
    switch (terrain) {
        // Bright, saturated low-poly colors (decision D-627).
        case sim::Terrain::Grass: r = 96; g = 168; b = 58; grows = true; break;
        case sim::Terrain::Meadow: r = 122; g = 180; b = 66; grows = true; break;
        case sim::Terrain::ForestFloor: r = 70; g = 128; b = 50; grows = true; break;
        case sim::Terrain::Sand: r = 226; g = 206; b = 150; break;
        case sim::Terrain::Rock: r = 138; g = 104; b = 82; break;
        case sim::Terrain::Clay: r = 164; g = 118; b = 84; break;
        // Wet sand: the bed shows through shallow water.
        case sim::Terrain::Water: r = 196; g = 186; b = 138; break;
        case sim::Terrain::Count: break;
    }
    if (grows) {
        // Poor soil looks drier and yellower.
        const float dry = (1.0f - static_cast<float>(fertility) / 255.0f) * 0.55f;
        r += (196.0f - r) * dry;
        g += (190.0f - g) * dry;
        b += (96.0f - b) * dry;
    }
    // A little variation per cell so large areas are not flat.
    const float jitter = 0.96f + static_cast<float>(cell_hash & 0xFFu) / 255.0f * 0.08f;
    const auto channel = [&](float v) { return static_cast<std::uint8_t>(std::clamp(v * jitter, 0.0f, 255.0f)); };
    return {channel(r), channel(g), channel(b)};
}

std::uint8_t grass_density(sim::Terrain terrain, std::uint8_t fertility, std::uint8_t biome_grass) {
    int base = 0;
    switch (terrain) {
        case sim::Terrain::Grass: base = 255; break;
        case sim::Terrain::Meadow: base = 235; break;
        case sim::Terrain::ForestFloor: base = 110; break;  // Shade keeps it thin.
        case sim::Terrain::Clay: base = 40; break;
        default: base = 0; break;
    }
    // Poor soil grows less; the biome sets the overall amount.
    const int soil = 110 + fertility * 145 / 255;
    return static_cast<std::uint8_t>(base * soil / 255 * biome_grass / 255);
}

float map_surface_height(const sim::MapData& map, float x, float z) {
    if (map.size <= 0) {
        return 0.0f;
    }
    const float max = static_cast<float>(map.size);
    x = std::clamp(x, 0.0f, max);
    z = std::clamp(z, 0.0f, max);
    const int ix = std::min(static_cast<int>(x), map.size - 1);
    const int iz = std::min(static_cast<int>(z), map.size - 1);
    const float tx = x - static_cast<float>(ix);
    const float tz = z - static_cast<float>(iz);
    const auto h = [&](int vx, int vz) { return static_cast<float>(map.height_cm(vx, vz)) * 0.01f; };
    const float ground = (h(ix, iz) * (1 - tx) + h(ix + 1, iz) * tx) * (1 - tz) +
                         (h(ix, iz + 1) * (1 - tx) + h(ix + 1, iz + 1) * tx) * tz;
    const std::uint16_t water = map.water[static_cast<std::size_t>(iz) * static_cast<std::size_t>(map.size) +
                                          static_cast<std::size_t>(ix)];
    return std::max(ground, static_cast<float>(water) * 0.01f);
}

render::Instance feature_instance(const sim::MapData& map, const sim::MapFeature& f, const sim::Content* content,
                                  sim::Season season, bool snowy) {
    const float x = to_float(f.x);
    const float z = to_float(f.z);
    render::Instance inst;
    inst.position = {x, to_float(map.height_at(f.x, f.z)), z};
    inst.yaw = static_cast<float>(f.rotation) / 65536.0f * 2.0f * std::numbers::pi_v<float>;
    inst.scale = f.type == sim::FeatureType::Tree ? static_cast<float>(sim::MapData::tree_height_cm(f)) / 100.0f
                 : f.type == sim::FeatureType::StoneDeposit ? 1.0f  // Its models are to size.
                 : sim::is_deposit(f.type)                  // The other deposits (phase 101): one model, as large as their ground.
                     ? static_cast<float>(sim::deposit_half_side(f.size)) / static_cast<float>(sim::deposit_half_side(0))
                     : to_float(f.scale);
    // Slightly different shades so forests do not look copied.
    const std::uint32_t h = hash2(static_cast<std::uint32_t>(f.x.raw()), static_cast<std::uint32_t>(f.z.raw()));
    const float shade = 0.9f + static_cast<float>(h & 0xFFu) / 255.0f * 0.2f;
    const bool tree = f.type == sim::FeatureType::Tree;
    inst.tint = season_tint(shade, tree, season, snowy);
    // Phase 34: landmarks show through the fog of war.
    if (content != nullptr) {
        if (tree) {
            inst.landmark = f.species < content->flora.species.size() && content->flora.species[f.species].landmark;
        } else if (const sim::FeatureDef* fd = content->feature(f.type)) {
            // Of the stone deposits, only the large ones.
            inst.landmark = fd->landmark && (!sim::is_deposit(f.type) || f.size + 1 >= sim::kDepositSizes);
        }
    }
    return inst;
}

math::Vec3 season_tint(float shade, bool tree, sim::Season season, bool snowy) {
    math::Vec3 tint{shade, shade, shade};
    // A tree changes model with the season (phase 51); a bush, color.
    if (!tree) {
        if (season == sim::Season::Autumn) {
            tint = {tint.x * 1.2f, tint.y * 0.95f, tint.z * 0.6f};
        } else if (season == sim::Season::Winter) {
            tint = {tint.x * 0.85f, tint.y * 0.72f, tint.z * 0.55f};
        }
    }
    if (snowy) {
        tint = tint * 0.6f + math::Vec3{0.5f, 0.52f, 0.56f};
    }
    return tint;
}

std::optional<math::Vec3> ground_hit(const sim::MapData& map, math::Vec3 origin, math::Vec3 dir, float max_distance) {
    if (map.size <= 0) {
        return std::nullopt;
    }
    dir = math::normalize(dir);
    const float size = static_cast<float>(map.size);
    const auto above = [&](float t) {
        const math::Vec3 p = origin + dir * t;
        return p.y > map_surface_height(map, p.x, p.z);
    };
    // Nothing is higher than the highest height a map can hold: from far
    // above, the march starts there.
    constexpr float kHighest = 65535.0f / 100.0f;
    float start = 0.0f;
    if (origin.y > kHighest && dir.y < 0.0f) {
        start = (origin.y - kHighest) / -dir.y;
    }
    // March in steps of a meter, longer far away (a meter per 500 m
    // marched), then narrow down the crossing.
    float prev = start;
    for (float t = start + 1.0f; t <= max_distance; t += std::max(1.0f, (t - start) / 500.0f)) {
        const math::Vec3 p = origin + dir * t;
        if (p.x < -50.0f || p.z < -50.0f || p.x > size + 50.0f || p.z > size + 50.0f) {
            if (dir.y >= 0.0f) {
                return std::nullopt;
            }
        }
        if (!above(t)) {
            float lo = prev;
            float hi = t;
            for (int i = 0; i < 16; ++i) {
                const float mid = (lo + hi) * 0.5f;
                (above(mid) ? lo : hi) = mid;
            }
            const math::Vec3 hit = origin + dir * hi;
            if (hit.x < 0.0f || hit.z < 0.0f || hit.x > size || hit.z > size) {
                return std::nullopt;
            }
            return hit;
        }
        prev = t;
    }
    return std::nullopt;
}

std::vector<std::vector<render::Instance>> build_feature_instances(const sim::MapData& map,
                                                                  const sim::Content& content, TreeCalendar when,
                                                                  bool snowy) {
    std::vector<std::vector<render::Instance>> features(visual_slot_count(content));
    // One instance per natural feature, standing on the ground.
    for (const sim::MapFeature& f : map.features) {
        const std::size_t slot = visual_slot(content, f, &map);
        if (slot < features.size()) {
            features[slot].push_back(feature_instance(map, f, &content, when.season, snowy));
            features[slot].back().look = feature_look(content, f, when);
        }
    }
    return features;
}

MapVisuals build_map_visuals(const sim::MapData& map, const sim::Content& content) {
    MapVisuals v;
    render::TerrainData& t = v.terrain;
    const std::int32_t n = map.size;
    t.cells = n;
    t.heights = map.heights;
    t.water = map.water;

    // Every cell's color, for the facets and the color texture.
    std::vector<std::uint32_t> cell_colors(static_cast<std::size_t>(n) * static_cast<std::size_t>(n));
    for (std::int32_t cz = 0; cz < n; ++cz) {
        for (std::int32_t cx = 0; cx < n; ++cx) {
            const std::size_t cell = static_cast<std::size_t>(cz) * static_cast<std::size_t>(n) + static_cast<std::size_t>(cx);
            const Rgb8 c = ground_color(static_cast<sim::Terrain>(map.terrain[cell]), map.fertility[cell],
                                        hash2(static_cast<std::uint32_t>(cx), static_cast<std::uint32_t>(cz)));
            cell_colors[cell] = 0xFF000000u | (static_cast<std::uint32_t>(c.b) << 16) |
                                (static_cast<std::uint32_t>(c.g) << 8) | c.r;
        }
    }

    // Ground colors, averaged down when the map is bigger than the texture.
    t.color_size = std::min(n, kMaxGroundColorSize);
    const std::int32_t shrink = n / t.color_size;
    const auto texels = static_cast<std::size_t>(t.color_size);
    t.colors.resize(texels * texels * 4);
    for (std::int32_t ty = 0; ty < t.color_size; ++ty) {
        for (std::int32_t tx = 0; tx < t.color_size; ++tx) {
            std::uint32_t sum[4] = {0, 0, 0, 0};
            for (std::int32_t dz = 0; dz < shrink; ++dz) {
                for (std::int32_t dx = 0; dx < shrink; ++dx) {
                    const std::int32_t cx = tx * shrink + dx;
                    const std::int32_t cz = ty * shrink + dz;
                    const std::size_t cell = static_cast<std::size_t>(cz) * static_cast<std::size_t>(n) +
                                             static_cast<std::size_t>(cx);
                    const std::uint32_t c = cell_colors[cell];
                    sum[0] += c & 0xFFu;
                    sum[1] += (c >> 8) & 0xFFu;
                    sum[2] += (c >> 16) & 0xFFu;
                    const std::uint8_t b = map.biome.empty() ? 0 : map.biome[cell];
                    const std::uint8_t grass = b < content.flora.biomes.size() ? content.flora.biomes[b].grass : 180;
                    sum[3] += grass_density(static_cast<sim::Terrain>(map.terrain[cell]), map.fertility[cell], grass);
                }
            }
            const auto count = static_cast<std::uint32_t>(shrink * shrink);
            std::uint8_t* px = &t.colors[(static_cast<std::size_t>(ty) * texels + static_cast<std::size_t>(tx)) * 4];
            px[0] = static_cast<std::uint8_t>(sum[0] / count);
            px[1] = static_cast<std::uint8_t>(sum[1] / count);
            px[2] = static_cast<std::uint8_t>(sum[2] / count);
            px[3] = static_cast<std::uint8_t>(sum[3] / count);
        }
    }

    // The faceted ground, with small facets where the kind of ground changes.
    std::vector<std::uint8_t> classes(map.terrain.size());
    for (std::size_t i = 0; i < classes.size(); ++i) {
        render::GroundClass c = render::GroundClass::Soft;
        switch (static_cast<sim::Terrain>(map.terrain[i])) {
            case sim::Terrain::Sand: c = render::GroundClass::Sand; break;
            case sim::Terrain::Water: c = render::GroundClass::Water; break;
            case sim::Terrain::Rock: c = render::GroundClass::Rock; break;
            default: break;
        }
        classes[i] = static_cast<std::uint8_t>(c);
    }
    t.facets = render::build_facet_meshes(n, map.heights, classes, cell_colors,
                                          static_cast<std::uint32_t>(map.settings.seed));
    // Where the map's edge is sea, the sea goes on past it.
    render::add_backdrop(t.facets, n, map.heights, static_cast<std::uint32_t>(map.settings.seed), &map.water);
    v.features = build_feature_instances(map, content);
    return v;
}

MapScene::Slot MapScene::load_file(render::SceneRenderer& renderer, const std::filesystem::path& file,
                                   render::ModelClass model_class) {
    const std::string key = file.generic_string();
    if (const auto it = files_.find(key); it != files_.end()) {
        return it->second;
    }
    Slot slot;
    const auto model = load_model_file(file);
    render::ModelId id = 0;
    if (model.has_value() && renderer.add_model(*model, id)) {
        renderer.set_model_class(id, model_class);
        slot.model = id;
        slot.height = std::max(0.1f, model->bounds_max.y - model->bounds_min.y);
        used_models_.push_back(id);
    }
    files_[key] = slot;
    return slot;
}

bool MapScene::load_models(render::SceneRenderer& renderer, const mods::BuildResult& pack) {
    const sim::Content& content = pack.content;
    tree_slots_ = tree_slot_count(content);
    slots_.assign(visual_slot_count(content), Slot{});
    std::size_t missing = 0;
    bool any = false;
    for (std::size_t s = 0; s < content.flora.species.size(); ++s) {
        const sim::SpeciesDef& sp = content.flora.species[s];
        // Each variant is a model with the other states
        // as its looks (the variant of the same number, going around), and
        // every file may have a far version.
        const auto state_model = [&](std::size_t st, std::size_t v) {
            const std::vector<std::string>& files = sp.state_models[st];
            if (files.empty()) {
                return kNoModel;
            }
            const std::size_t i = v % files.size();
            const std::filesystem::path file = mods::mod_file(pack.dir(sp.mod), files[i]);
            const render::ModelId id = file.empty() ? kNoModel : load_file(renderer, file, render::ModelClass::Normal).model;
            missing += id == kNoModel ? 1 : 0;
            if (id != kNoModel && i < sp.state_far[st].size() && !sp.state_far[st][i].empty()) {
                const std::filesystem::path far_file = mods::mod_file(pack.dir(sp.mod), sp.state_far[st][i]);
                const render::ModelId far_id =
                    far_file.empty() ? kNoModel : load_file(renderer, far_file, render::ModelClass::Normal).model;
                missing += far_id == kNoModel ? 1 : 0;
                renderer.set_far_model(id, far_id == kNoModel ? render::kNoFarModel : far_id);
            }
            return id;
        };
        for (std::size_t v = 0; v < sp.state_models[0].size() && v < sim::kMaxModelVariants; ++v) {
            Slot& slot = slots_[tree_variant_slot(s, v)];
            const std::filesystem::path file = mods::mod_file(pack.dir(sp.mod), sp.state_models[0][v]);
            slot = Slot{};
            if (state_model(0, v) != kNoModel) {
                slot = load_file(renderer, file, render::ModelClass::Normal);
                // Looks 1 and 2: autumn and bare (the model itself without them).
                const render::ModelId looks[2] = {state_model(1, v), state_model(2, v)};
                renderer.set_model_looks(slot.model, looks);
            }
            any = any || slot.model != kNoModel;
        }
    }
    for (const sim::FeatureDef& f : content.features) {
        if (f.kind == sim::FeatureKind::Tree) {
            continue;
        }
        for (std::size_t v = 0; v < f.models.size() && v < sim::kMaxModelVariants; ++v) {
            const std::filesystem::path file = mods::mod_file(pack.dir(f.mod), f.models[v]);
            Slot& slot = slots_[feature_slot(content, f.kind, v)];
            slot = file.empty() ? Slot{} : load_file(renderer, file, feature_class(f.kind));
            missing += slot.model == kNoModel ? 1 : 0;
            any = any || slot.model != kNoModel;
        }
        if (!f.model_green.empty() || !f.model_flower.empty()) {
            // Phase 99: without its fruit and in flower, as looks 1 and 2 of
            // each of its models (but the bramble, which is always the same).
            const auto extra = [&](const std::string& rel) {
                const std::filesystem::path file = rel.empty() ? std::filesystem::path{} : mods::mod_file(pack.dir(f.mod), rel);
                const render::ModelId id = file.empty() ? kNoModel : load_file(renderer, file, feature_class(f.kind)).model;
                missing += !rel.empty() && id == kNoModel ? 1 : 0;
                return id;
            };
            const render::ModelId looks[2] = {extra(f.model_green), extra(f.model_flower)};
            for (std::size_t v = 0; v < f.models.size() && v < sim::kMaxModelVariants; ++v) {
                const render::ModelId model = slots_[feature_slot(content, f.kind, v)].model;
                const bool bramble = f.kind == sim::FeatureKind::BerryBush && v == static_cast<std::size_t>(sim::BushKind::Thorn);
                if (model != kNoModel && !bramble) {
                    renderer.set_model_looks(model, looks);
                }
            }
        }
        if (f.kind == sim::FeatureKind::StoneDeposit && f.models.size() >= sim::kDepositSizes) {
            // The small one is the model; the medium and the large, its looks 1 and 2.
            // (And the same for the small ones of other stone, phase 102.)
            const render::ModelId looks[2] = {slots_[feature_slot(content, f.kind, 1)].model,
                                              slots_[feature_slot(content, f.kind, 2)].model};
            for (std::size_t v = 0; v < f.models.size() && v < sim::kMaxModelVariants; ++v) {
                const render::ModelId small = slots_[feature_slot(content, f.kind, v)].model;
                if ((v == 0 || v >= sim::kDepositSizes) && small != kNoModel) {
                    renderer.set_model_looks(small, looks);
                }
            }
        }
    }
    if (missing > 0) {
        log::warn("map: {} model(s) missing; those objects will not be drawn", missing);
    }
    const std::filesystem::path core = pack.dir(mods::kCoreModId);
    house_ = load_file(renderer, core / builtin_models::kSampleHouse, render::ModelClass::Normal).model;
    cloud_models_.clear();
    for (const std::string_view cloud : builtin_models::kClouds) {
        const render::ModelId id = load_file(renderer, core / cloud, render::ModelClass::Sky).model;
        if (id != kNoModel) {
            cloud_models_.push_back(id);
        }
    }
    models_loaded_ = any;
    return any;
}

bool MapScene::show(render::SceneRenderer& renderer, const MapVisuals& visuals) {
    hide(renderer);
    looks_.clear();
    when_ = TreeCalendar{};
    snowy_ = false;
    if (!renderer.set_terrain(visuals.terrain)) {
        return false;
    }
    apply_features(renderer, visuals.features);
    shown_ = true;
    return true;
}

void MapScene::show_sky(render::SceneRenderer& renderer, const sim::MapData& map) {
    show_clouds(renderer, map);
}

void MapScene::refresh_features(render::SceneRenderer& renderer, const sim::MapData& map,
                                const sim::Content& content) {
    apply_features(renderer, build_feature_instances(map, content, when_, snowy_));
}

void MapScene::apply_features(render::SceneRenderer& renderer,
                              const std::vector<std::vector<render::Instance>>& features) {
    feature_refs_.clear();
    fades_.clear();
    ++rebuilds_;
    slot_counts_.assign(features.size(), 0);
    for (std::size_t i = 0; i < features.size(); ++i) {
        slot_counts_[i] = features[i].size();
    }
    if (models_loaded_) {
        // Slots that share a model (stand-ins) go into one list.
        for (const render::ModelId model : used_models_) {
            scratch_.clear();
            for (std::size_t i = 0; i < slots_.size() && i < features.size(); ++i) {
                if (slots_[i].model != model) {
                    continue;
                }
                const bool tree = i < tree_slots_;
                for (render::Instance inst : features[i]) {
                    if (tree) {
                        inst.scale = slots_[i].tree_scale(inst.scale);
                    }
                    scratch_.push_back(inst);
                }
            }
            renderer.set_instances(model, scratch_);
        }
        scratch_.clear();
        scratch_.shrink_to_fit();
    }
}

void MapScene::build_feature_refs(const sim::MapData& map, const sim::Content& content) {
    feature_refs_.assign(map.features.size(), FeatureRef{});
    // The same order as apply_features: per model, its slots in order.
    std::vector<std::uint32_t> base(slots_.size(), 0);
    for (const render::ModelId model : used_models_) {
        std::uint32_t offset = 0;
        for (std::size_t i = 0; i < slots_.size() && i < slot_counts_.size(); ++i) {
            if (slots_[i].model == model) {
                base[i] = offset;
                offset += static_cast<std::uint32_t>(slot_counts_[i]);
            }
        }
    }
    std::vector<std::uint32_t> next(slots_.size(), 0);
    for (std::size_t k = 0; k < map.features.size(); ++k) {
        const std::size_t slot = visual_slot(content, map.features[k], &map);
        if (slot >= slots_.size()) {
            continue;
        }
        feature_refs_[k] = {slots_[slot].model, base[slot] + next[slot]++};
    }
}

void MapScene::set_feature_look(render::SceneRenderer& renderer, const sim::MapData& map, const sim::Content& content,
                                std::size_t feature, FeatureLook look) {
    if (!models_loaded_ || feature >= map.features.size()) {
        return;
    }
    if (feature_refs_.size() != map.features.size()) {
        build_feature_refs(map, content);
    }
    const FeatureRef ref = feature_refs_[feature];
    const sim::MapFeature& f = map.features[feature];
    const std::size_t slot = visual_slot(content, f, &map);
    if (ref.model == kNoModel || slot >= slots_.size()) {
        return;
    }
    if (looks_.size() != map.features.size()) {
        looks_.assign(map.features.size(), FeatureLook::Normal);
    }
    looks_[feature] = look;
    render::Instance inst = feature_instance(map, f, &content, when_.season, snowy_);
    inst.look = feature_look(content, f, when_);
    if (slot < tree_slots_) {
        inst.scale = slots_[slot].tree_scale(inst.scale);
    }
    if (look == FeatureLook::Gone) {
        inst.scale = 0.0f;
    } else if (look == FeatureLook::Empty && f.type == sim::FeatureType::Tree) {
        inst.scale *= 0.3f;  // A sprout (phase 86): its tree, small.
    } else if (const sim::FeatureDef* def = look == FeatureLook::Empty ? content.feature(f.type) : nullptr;
               def != nullptr && def->seasons != 0 && !def->model_green.empty()) {
        inst.look = kGreenLook;  // Picked clean in its season (phase 99): the bush without its fruit.
    } else if (look == FeatureLook::Empty) {
        // A picked bush: smaller and duller until it grows back.
        inst.scale *= 0.8f;
        inst.tint = inst.tint * 0.55f;
    }
    if (const auto fade = fades_.find(feature); fade != fades_.end()) {
        inst.fade = fade->second;
    }
    renderer.update_instance(ref.model, ref.index, inst);
}

void MapScene::set_feature_fade(render::SceneRenderer& renderer, const sim::MapData& map, const sim::Content& content,
                                std::size_t feature, std::uint8_t level) {
    if (feature >= map.features.size()) {
        return;
    }
    if (level == 0) {
        fades_.erase(feature);
    } else {
        fades_[feature] = std::min(level, render::kMaxFade);
    }
    set_feature_look(renderer, map, content, feature,
                     feature < looks_.size() ? looks_[feature] : FeatureLook::Normal);
}

void MapScene::set_season(render::SceneRenderer& renderer, const sim::MapData& map, const sim::Content& content,
                          TreeCalendar when, bool snowy) {
    if (when == when_ && snowy == snowy_) {
        return;
    }
    if (when.season == when_.season && snowy == snowy_ && models_loaded_) {
        // Only the turn moved on: the trees whose turn came change their
        // look, and nothing is rebuilt (phase 52).
        const auto t0 = std::chrono::steady_clock::now();
        if (feature_refs_.size() != map.features.size()) {
            build_feature_refs(map, content);
        }
        for (std::size_t k = 0; k < map.features.size(); ++k) {
            const sim::MapFeature& f = map.features[k];
            if (f.type != sim::FeatureType::Tree) {
                continue;
            }
            // Only the trees whose own step lies between the two turns.
            const int own = tree_turn(f);
            if ((when.turn > own) != (when_.turn > own) && feature_refs_[k].model != kNoModel) {
                renderer.set_instance_look(feature_refs_[k].model, feature_refs_[k].index, tree_look(content, f, when));
            }
        }
        when_ = when;
        const double ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - t0).count();
        if (ms >= 5.0) {
            log::info("map: trees turned (step {}) in {:.0f} ms", when.turn, ms);
        }
        return;
    }
    when_ = when;
    snowy_ = snowy;
    const auto t0 = std::chrono::steady_clock::now();
    // Every instance again, then the felled and the picked as they were.
    const std::vector<FeatureLook> looks = looks_;
    apply_features(renderer, build_feature_instances(map, content, when, snowy));
    for (std::size_t i = 0; i < looks.size() && i < map.features.size(); ++i) {
        if (looks[i] != FeatureLook::Normal) {
            set_feature_look(renderer, map, content, i, looks[i]);
        }
    }
    // On the largest maps this is felt; the log says how much.
    const double ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - t0).count();
    if (ms >= 20.0) {
        log::info("map: {} features shown for the season in {:.0f} ms", map.features.size(), ms);
    }
}

void MapScene::hide_sample_village(render::SceneRenderer& renderer) {
    houses_.clear();
    if (house_ != kNoModel) {
        renderer.set_instances(house_, {});
    }
}

void MapScene::show_sample_village(render::SceneRenderer& renderer, const sim::MapData& map, math::Vec3 center) {
    if (house_ == kNoModel) {
        return;
    }
    constexpr int kHouses = 6;
    constexpr float kRing = 18.0f;    // Meters from the center.
    constexpr float kHalfSize = 3.0f;  // About half the house's footprint.
    std::vector<render::Instance>& houses = houses_;
    houses.clear();
    for (int i = 0; i < kHouses; ++i) {
        const float a = static_cast<float>(i) / kHouses * 2.0f * std::numbers::pi_v<float> + 0.3f;
        const float x = center.x + std::cos(a) * kRing;
        const float z = center.z + std::sin(a) * kRing;
        if (map.water_at(static_cast<std::int32_t>(x), static_cast<std::int32_t>(z))) {
            continue;
        }
        // Sit on the lowest corner so no corner floats on a slope.
        float y = map_surface_height(map, x, z);
        for (const float dx : {-kHalfSize, kHalfSize}) {
            for (const float dz : {-kHalfSize, kHalfSize}) {
                y = std::min(y, map_surface_height(map, x + dx, z + dz));
            }
        }
        render::Instance h;
        h.position = {x, y - 0.1f, z};
        h.yaw = std::atan2(center.x - x, center.z - z);  // Front (+Z) toward the square.
        houses.push_back(h);
    }
    renderer.set_instances(house_, houses);
}

void MapScene::add_house(render::SceneRenderer& renderer, const render::Instance& house) {
    if (house_ == kNoModel) {
        return;
    }
    houses_.push_back(house);
    renderer.set_instances(house_, houses_);
}

void MapScene::remove_house(render::SceneRenderer& renderer, std::size_t index) {
    if (house_ == kNoModel || index >= houses_.size()) {
        return;
    }
    houses_.erase(houses_.begin() + static_cast<std::ptrdiff_t>(index));
    renderer.set_instances(house_, houses_);
}

// Low-poly clouds high over the map and the mountains around it; they cast
// no shadow (decision D-628) and drift with the wind (phase 18).
void MapScene::show_clouds(render::SceneRenderer& renderer, const sim::MapData& map) {
    if (cloud_models_.empty()) {
        return;
    }
    const float side = static_cast<float>(map.size);
    const float reach = side + 3000.0f;
    // About one cloud every 600 x 600 m.
    const auto count = static_cast<std::size_t>(reach * reach / 360000.0f) + 4;
    clouds_.assign(cloud_models_.size(), {});
    cloud_min_ = -1500.0f;
    cloud_max_ = -1500.0f + reach;
    std::uint32_t h = static_cast<std::uint32_t>(map.settings.seed) * 2654435761u + 12345u;
    const auto next = [&h] {
        h ^= h << 13;
        h ^= h >> 17;
        h ^= h << 5;
        return static_cast<float>(h & 0xFFFFu) / 65535.0f;
    };
    for (std::size_t i = 0; i < count; ++i) {
        render::Instance c;
        c.position = {-1500.0f + next() * reach, 240.0f + next() * 120.0f, -1500.0f + next() * reach};
        c.yaw = next() * 6.2831853f;
        c.scale = 7.0f + next() * 9.0f;
        // Each cloud one of the shapes, the same for the same map.
        clouds_[pick_variant(h, clouds_.size())].push_back(c);
    }
    for (std::size_t v = 0; v < cloud_models_.size(); ++v) {
        renderer.set_instances(cloud_models_[v], clouds_[v]);
    }
}

void MapScene::update_sky(render::SceneRenderer& renderer, float dt) {
    if (cloud_models_.empty() || clouds_.size() != cloud_models_.size()) {
        return;
    }
    constexpr float kWind = 5.0f;  // Meters per second, west to east.
    const float span = cloud_max_ - cloud_min_;
    for (std::size_t v = 0; v < clouds_.size(); ++v) {
        for (render::Instance& c : clouds_[v]) {
            c.position.x += kWind * dt * (0.8f + 0.1f * c.scale / 8.0f);
            if (c.position.x > cloud_max_) {
                c.position.x -= span;
            }
        }
        renderer.set_instances(cloud_models_[v], clouds_[v]);
    }
}

void MapScene::hide(render::SceneRenderer& renderer) {
    houses_.clear();
    for (const render::ModelId id : cloud_models_) {
        renderer.set_instances(id, {});
    }
    if (house_ != kNoModel) {
        renderer.set_instances(house_, {});
    }
    for (const render::ModelId id : used_models_) {
        renderer.set_instances(id, {});
    }
    renderer.clear_terrain();
    shown_ = false;
}

}  // namespace sc
