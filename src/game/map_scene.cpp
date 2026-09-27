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

struct FeatureLook {
    const char* file;
    render::ModelClass model_class;
};

// Model per non-tree feature type, in FeatureType order after Tree.
constexpr FeatureLook kFeatureLooks[] = {
    {"rock.glb", render::ModelClass::Normal},
    {"ore_rock.glb", render::ModelClass::Normal},
    {"berry_bush.glb", render::ModelClass::SmallVegetation},
    {"herb.glb", render::ModelClass::SmallVegetation},
};
static_assert(std::size(kFeatureLooks) + 1 == static_cast<std::size_t>(sim::FeatureType::Count));

// Stand-ins while a species has no model of its own: cone-shaped conifers
// use the old pine, everything else the old oak.
const char* fallback_tree_file(sim::Species species) {
    switch (species) {
        case sim::Species::Pine:
        case sim::Species::Sequoia: return "tree_pine.glb";
        default: return "tree_oak.glb";
    }
}

}  // namespace

std::size_t tree_slot(sim::Species species, sim::TreeSize size) {
    return static_cast<std::size_t>(species) * sim::kTreeSizes + static_cast<std::size_t>(size);
}

std::size_t visual_slot(const sim::MapFeature& f) {
    if (f.type == sim::FeatureType::Tree) {
        return tree_slot(static_cast<sim::Species>(f.species), static_cast<sim::TreeSize>(f.size));
    }
    return kTreeSlots + static_cast<std::size_t>(f.type);
}

std::string tree_model_file(sim::Species species, sim::TreeSize size) {
    return std::string("tree_") + sim::species_info(species).id + "_" + sim::size_info(size).id + ".glb";
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

std::uint8_t grass_density(sim::Terrain terrain, std::uint8_t fertility, sim::Biome biome) {
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
    return static_cast<std::uint8_t>(base * soil / 255 * sim::biome_info(biome).grass / 255);
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

std::vector<std::vector<render::Instance>> build_feature_instances(const sim::MapData& map) {
    MapVisuals v;
    // One instance per natural feature, standing on the ground.
    for (const sim::MapFeature& f : map.features) {
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
        v.features[visual_slot(f)].push_back(inst);
    }
    return std::move(v.features);
}

MapVisuals build_map_visuals(const sim::MapData& map) {
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
                    sum[3] += grass_density(static_cast<sim::Terrain>(map.terrain[cell]), map.fertility[cell],
                                            map.biome.empty() ? sim::Biome::Temperate
                                                              : static_cast<sim::Biome>(map.biome[cell]));
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
    v.features = build_feature_instances(map);
    return v;
}

bool MapScene::load_models(render::SceneRenderer& renderer, const std::filesystem::path& props_dir) {
    // Each file is uploaded once, even if several slots use it.
    struct Loaded {
        std::string file;
        Slot slot;
    };
    std::vector<Loaded> loaded;
    const auto load = [&](const std::string& file, render::ModelClass model_class, Slot& out) {
        for (const Loaded& l : loaded) {
            if (l.file == file) {
                out = l.slot;
                return out.model != kNoModel;
            }
        }
        Slot slot;
        const auto model = load_model_file(props_dir / file);
        render::ModelId id = 0;
        if (model.has_value() && renderer.add_model(*model, id)) {
            renderer.set_model_class(id, model_class);
            slot.model = id;
            slot.height = std::max(0.1f, model->bounds_max.y - model->bounds_min.y);
            used_models_.push_back(id);
        }
        loaded.push_back({file, slot});
        out = slot;
        return slot.model != kNoModel;
    };
    std::size_t missing = 0;
    std::size_t trees = 0;
    for (std::size_t s = 0; s < sim::kSpeciesCount; ++s) {
        const auto species = static_cast<sim::Species>(s);
        for (std::size_t z = 0; z < sim::kTreeSizes; ++z) {
            const auto size = static_cast<sim::TreeSize>(z);
            if (!sim::species_has_size(species, size)) {
                continue;
            }
            Slot& slot = slots_[tree_slot(species, size)];
            if (load(tree_model_file(species, size), render::ModelClass::Normal, slot)) {
                ++trees;
                continue;
            }
            ++missing;
            (void)load(fallback_tree_file(species), render::ModelClass::Normal, slot);
        }
    }
    if (missing > 0) {
        log::warn("map: {} tree model(s) missing; using stand-ins", missing);
    }
    bool any = trees > 0;
    for (std::size_t i = 0; i < std::size(kFeatureLooks); ++i) {
        Slot& slot = slots_[kTreeSlots + 1 + i];
        if (load(kFeatureLooks[i].file, kFeatureLooks[i].model_class, slot)) {
            any = true;
        } else {
            log::warn("map: model {} unavailable; that feature will not be drawn", kFeatureLooks[i].file);
        }
    }
    const auto house = load_model_file(props_dir / "house_small.glb");
    render::ModelId id = 0;
    house_ = house.has_value() && renderer.add_model(*house, id) ? id : kNoModel;
    const auto cloud = load_model_file(props_dir / "cloud.glb");
    cloud_ = cloud.has_value() && renderer.add_model(*cloud, id) ? id : kNoModel;
    if (cloud_ != kNoModel) {
        renderer.set_model_class(cloud_, render::ModelClass::Sky);
    }
    models_loaded_ = any;
    return any;
}

bool MapScene::show(render::SceneRenderer& renderer, const MapVisuals& visuals) {
    hide(renderer);
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

void MapScene::refresh_features(render::SceneRenderer& renderer, const sim::MapData& map) {
    apply_features(renderer, build_feature_instances(map));
}

void MapScene::apply_features(render::SceneRenderer& renderer,
                              const std::vector<std::vector<render::Instance>>& features) {
    if (models_loaded_) {
        // Slots that share a model (stand-ins) go into one list.
        for (const render::ModelId model : used_models_) {
            scratch_.clear();
            for (std::size_t i = 0; i < kVisualSlots && i < features.size(); ++i) {
                if (slots_[i].model != model) {
                    continue;
                }
                const bool tree = i < kTreeSlots;
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
