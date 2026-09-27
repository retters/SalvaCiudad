#include "game/map_scene.h"

#include <algorithm>
#include <cmath>
#include <numbers>

#include "core/log.h"
#include "game/test_scene.h"

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

std::size_t tree_slot(std::size_t species, sim::TreeSize size) {
    return species * sim::kTreeSizes + static_cast<std::size_t>(size);
}

std::size_t tree_slot_count(const sim::Content& content) {
    return content.flora.species.size() * sim::kTreeSizes;
}

std::size_t visual_slot_count(const sim::Content& content) {
    return tree_slot_count(content) + static_cast<std::size_t>(sim::FeatureType::Count);
}

std::size_t visual_slot(const sim::Content& content, const sim::MapFeature& f) {
    if (f.type == sim::FeatureType::Tree) {
        return tree_slot(f.species, static_cast<sim::TreeSize>(f.size));
    }
    return tree_slot_count(content) + static_cast<std::size_t>(f.type);
}

std::string tree_model_file(const sim::SpeciesDef& species, sim::TreeSize size) {
    return species.model + "_" + sim::size_info(size).id + ".glb";
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
                                                  : to_float(f.scale);
    // Slightly different shades so forests do not look copied.
    const std::uint32_t h = hash2(static_cast<std::uint32_t>(f.x.raw()), static_cast<std::uint32_t>(f.z.raw()));
    const float shade = 0.9f + static_cast<float>(h & 0xFFu) / 255.0f * 0.2f;
    inst.tint = {shade, shade, shade};
    // The season's colors.
    const bool tree = f.type == sim::FeatureType::Tree;
    const bool evergreen = tree && content != nullptr && f.species < content->flora.species.size() &&
                           content->flora.species[f.species].evergreen;
    if (!evergreen) {
        if (season == sim::Season::Spring && tree) {
            inst.tint = inst.tint * 1.0f + math::Vec3{0.02f, 0.08f, -0.02f};
        } else if (season == sim::Season::Autumn) {
            // Each tree turns its own way: gold, orange or red.
            static constexpr math::Vec3 kAutumn[3] = {{1.45f, 1.15f, 0.4f}, {1.5f, 0.9f, 0.35f}, {1.35f, 0.6f, 0.35f}};
            const math::Vec3 c = tree ? kAutumn[(h >> 8) % 3] : math::Vec3{1.2f, 0.95f, 0.6f};
            inst.tint = {inst.tint.x * c.x, inst.tint.y * c.y, inst.tint.z * c.z};
        } else if (season == sim::Season::Winter) {
            inst.tint = {inst.tint.x * 0.85f, inst.tint.y * 0.72f, inst.tint.z * 0.55f};
        }
    }
    if (snowy) {
        inst.tint = inst.tint * 0.6f + math::Vec3{0.5f, 0.52f, 0.56f};
    }
    return inst;
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
    // March in steps of a meter, then narrow down the crossing.
    float prev = 0.0f;
    for (float t = 1.0f; t <= max_distance; t += 1.0f) {
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
                                                                  const sim::Content& content, sim::Season season,
                                                                  bool snowy) {
    std::vector<std::vector<render::Instance>> features(visual_slot_count(content));
    // One instance per natural feature, standing on the ground.
    for (const sim::MapFeature& f : map.features) {
        const std::size_t slot = visual_slot(content, f);
        if (slot < features.size()) {
            features[slot].push_back(feature_instance(map, f, &content, season, snowy));
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
    render::add_backdrop(t.facets, n, map.heights, static_cast<std::uint32_t>(map.settings.seed));
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
        for (std::size_t z = 0; z < sim::kTreeSizes; ++z) {
            const auto size = static_cast<sim::TreeSize>(z);
            if (!content.flora.species_has_size(s, size)) {
                continue;
            }
            const std::filesystem::path file = mods::mod_file(pack.dir(sp.mod), tree_model_file(sp, size));
            Slot& slot = slots_[tree_slot(s, size)];
            slot = file.empty() ? Slot{} : load_file(renderer, file, render::ModelClass::Normal);
            missing += slot.model == kNoModel ? 1 : 0;
            any = any || slot.model != kNoModel;
        }
    }
    for (const sim::FeatureDef& f : content.features) {
        if (f.kind == sim::FeatureKind::Tree || f.model.empty()) {
            continue;
        }
        const sim::FeatureType type = f.kind;
        const std::filesystem::path file = mods::mod_file(pack.dir(f.mod), f.model);
        Slot& slot = slots_[tree_slots_ + static_cast<std::size_t>(type)];
        slot = file.empty() ? Slot{} : load_file(renderer, file, feature_class(type));
        missing += slot.model == kNoModel ? 1 : 0;
        any = any || slot.model != kNoModel;
    }
    if (missing > 0) {
        log::warn("map: {} model(s) missing; those objects will not be drawn", missing);
    }
    const std::filesystem::path core = pack.dir(mods::kCoreModId) / "models" / "props";
    house_ = load_file(renderer, core / "house_small.glb", render::ModelClass::Normal).model;
    cloud_ = load_file(renderer, core / "cloud.glb", render::ModelClass::Sky).model;
    models_loaded_ = any;
    return any;
}

bool MapScene::show(render::SceneRenderer& renderer, const MapVisuals& visuals) {
    hide(renderer);
    looks_.clear();
    season_ = sim::Season::Summer;
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
    apply_features(renderer, build_feature_instances(map, content));
}

void MapScene::apply_features(render::SceneRenderer& renderer,
                              const std::vector<std::vector<render::Instance>>& features) {
    feature_refs_.clear();
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
                        inst.scale /= slots_[i].height;
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
        const std::size_t slot = visual_slot(content, map.features[k]);
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
    const std::size_t slot = visual_slot(content, f);
    if (ref.model == kNoModel || slot >= slots_.size()) {
        return;
    }
    if (looks_.size() != map.features.size()) {
        looks_.assign(map.features.size(), FeatureLook::Normal);
    }
    looks_[feature] = look;
    render::Instance inst = feature_instance(map, f, &content, season_, snowy_);
    if (slot < tree_slots_) {
        inst.scale /= slots_[slot].height;
    }
    if (look == FeatureLook::Gone) {
        inst.scale = 0.0f;
    } else if (look == FeatureLook::Empty) {
        // A picked bush: smaller and duller until it grows back.
        inst.scale *= 0.8f;
        inst.tint = inst.tint * 0.55f;
    }
    renderer.update_instance(ref.model, ref.index, inst);
}

void MapScene::set_season(render::SceneRenderer& renderer, const sim::MapData& map, const sim::Content& content,
                          sim::Season season, bool snowy) {
    if (season == season_ && snowy == snowy_) {
        return;
    }
    season_ = season;
    snowy_ = snowy;
    // Every instance again, then the felled and the picked as they were.
    const std::vector<FeatureLook> looks = looks_;
    apply_features(renderer, build_feature_instances(map, content, season, snowy));
    for (std::size_t i = 0; i < looks.size() && i < map.features.size(); ++i) {
        if (looks[i] != FeatureLook::Normal) {
            set_feature_look(renderer, map, content, i, looks[i]);
        }
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

// Low-poly clouds high over the map and the mountains around it; they do
// not move and cast no shadow (decision D-628).
void MapScene::show_clouds(render::SceneRenderer& renderer, const sim::MapData& map) {
    if (cloud_ == kNoModel) {
        return;
    }
    const float side = static_cast<float>(map.size);
    const float reach = side + 3000.0f;
    // About one cloud every 600 x 600 m.
    const auto count = static_cast<std::size_t>(reach * reach / 360000.0f) + 4;
    std::vector<render::Instance> clouds;
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
        clouds.push_back(c);
    }
    renderer.set_instances(cloud_, clouds);
}

void MapScene::hide(render::SceneRenderer& renderer) {
    houses_.clear();
    if (cloud_ != kNoModel) {
        renderer.set_instances(cloud_, {});
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
