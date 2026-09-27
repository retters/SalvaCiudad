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

// Model per feature type, in FeatureType order.
constexpr FeatureLook kFeatureLooks[] = {
    {"tree_pine.glb", render::ModelClass::Normal},
    {"tree_oak.glb", render::ModelClass::Normal},
    {"rock.glb", render::ModelClass::Normal},
    {"ore_rock.glb", render::ModelClass::Normal},
    {"berry_bush.glb", render::ModelClass::SmallVegetation},
    {"herb.glb", render::ModelClass::SmallVegetation},
};
static_assert(std::size(kFeatureLooks) == static_cast<std::size_t>(sim::FeatureType::Count));

}  // namespace

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
        case sim::Terrain::Grass: r = 112; g = 146; b = 66; grows = true; break;
        case sim::Terrain::Meadow: r = 140; g = 166; b = 74; grows = true; break;
        case sim::Terrain::ForestFloor: r = 86; g = 106; b = 54; grows = true; break;
        case sim::Terrain::Sand: r = 214; g = 198; b = 148; break;
        case sim::Terrain::Rock: r = 140; g = 136; b = 128; break;
        case sim::Terrain::Clay: r = 170; g = 120; b = 86; break;
        // The same tone as the water surface, so rivers still read as water
        // where distant, coarser ground hides the surface.
        case sim::Terrain::Water: r = 52; g = 104; b = 110; break;
        case sim::Terrain::Count: break;
    }
    if (grows) {
        // Poor soil looks drier and yellower.
        const float dry = (1.0f - static_cast<float>(fertility) / 255.0f) * 0.55f;
        r += (170.0f - r) * dry;
        g += (164.0f - g) * dry;
        b += (90.0f - b) * dry;
    }
    // A little variation per cell so large areas are not flat.
    const float jitter = 0.96f + static_cast<float>(cell_hash & 0xFFu) / 255.0f * 0.08f;
    const auto channel = [&](float v) { return static_cast<std::uint8_t>(std::clamp(v * jitter, 0.0f, 255.0f)); };
    return {channel(r), channel(g), channel(b)};
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

MapVisuals build_map_visuals(const sim::MapData& map) {
    MapVisuals v;
    render::TerrainData& t = v.terrain;
    const std::int32_t n = map.size;
    t.cells = n;
    t.heights = map.heights;
    t.water = map.water;

    // Ground colors, averaged down when the map is bigger than the texture.
    t.color_size = std::min(n, kMaxGroundColorSize);
    const std::int32_t shrink = n / t.color_size;
    const auto texels = static_cast<std::size_t>(t.color_size);
    t.colors.resize(texels * texels * 4);
    for (std::int32_t ty = 0; ty < t.color_size; ++ty) {
        for (std::int32_t tx = 0; tx < t.color_size; ++tx) {
            std::uint32_t sum[3] = {0, 0, 0};
            for (std::int32_t dz = 0; dz < shrink; ++dz) {
                for (std::int32_t dx = 0; dx < shrink; ++dx) {
                    const std::int32_t cx = tx * shrink + dx;
                    const std::int32_t cz = ty * shrink + dz;
                    const std::size_t cell = static_cast<std::size_t>(cz) * static_cast<std::size_t>(n) +
                                             static_cast<std::size_t>(cx);
                    const Rgb8 c = ground_color(static_cast<sim::Terrain>(map.terrain[cell]), map.fertility[cell],
                                                hash2(static_cast<std::uint32_t>(cx), static_cast<std::uint32_t>(cz)));
                    sum[0] += c.r;
                    sum[1] += c.g;
                    sum[2] += c.b;
                }
            }
            const auto count = static_cast<std::uint32_t>(shrink * shrink);
            std::uint8_t* px = &t.colors[(static_cast<std::size_t>(ty) * texels + static_cast<std::size_t>(tx)) * 4];
            px[0] = static_cast<std::uint8_t>(sum[0] / count);
            px[1] = static_cast<std::uint8_t>(sum[1] / count);
            px[2] = static_cast<std::uint8_t>(sum[2] / count);
            px[3] = 255;
        }
    }

    // One instance per natural feature, standing on the ground.
    for (const sim::MapFeature& f : map.features) {
        const float x = to_float(f.x);
        const float z = to_float(f.z);
        render::Instance inst;
        inst.position = {x, to_float(map.height_at(f.x, f.z)), z};
        inst.yaw = static_cast<float>(f.rotation) / 65536.0f * 2.0f * std::numbers::pi_v<float>;
        inst.scale = to_float(f.scale);
        // Slightly different shades so forests do not look copied.
        const std::uint32_t h = hash2(static_cast<std::uint32_t>(f.x.raw()), static_cast<std::uint32_t>(f.z.raw()));
        const float shade = 0.9f + static_cast<float>(h & 0xFFu) / 255.0f * 0.2f;
        inst.tint = {shade, shade, shade};
        v.features[static_cast<std::size_t>(f.type)].push_back(inst);
    }
    return v;
}

bool MapScene::load_models(render::SceneRenderer& renderer, const std::filesystem::path& props_dir) {
    bool any = false;
    for (std::size_t i = 0; i < std::size(kFeatureLooks); ++i) {
        models_[i] = kNoModel;
        const auto model = load_model_file(props_dir / kFeatureLooks[i].file);
        render::ModelId id = 0;
        if (model.has_value() && renderer.add_model(*model, id)) {
            renderer.set_model_class(id, kFeatureLooks[i].model_class);
            models_[i] = id;
            any = true;
        } else {
            log::warn("map: model {} unavailable; that feature will not be drawn", kFeatureLooks[i].file);
        }
    }
    const auto house = load_model_file(props_dir / "house_small.glb");
    render::ModelId id = 0;
    house_ = house.has_value() && renderer.add_model(*house, id) ? id : kNoModel;
    models_loaded_ = any;
    return any;
}

bool MapScene::show(render::SceneRenderer& renderer, const MapVisuals& visuals) {
    hide(renderer);
    if (!renderer.set_terrain(visuals.terrain)) {
        return false;
    }
    for (std::size_t i = 0; i < models_.size(); ++i) {
        if (models_loaded_ && models_[i] != kNoModel) {
            renderer.set_instances(models_[i], visuals.features[i]);
        }
    }
    shown_ = true;
    return true;
}

void MapScene::show_sample_village(render::SceneRenderer& renderer, const sim::MapData& map, math::Vec3 center) {
    if (house_ == kNoModel) {
        return;
    }
    constexpr int kHouses = 6;
    constexpr float kRing = 18.0f;    // Meters from the center.
    constexpr float kHalfSize = 3.0f;  // About half the house's footprint.
    std::vector<render::Instance> houses;
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

void MapScene::hide(render::SceneRenderer& renderer) {
    if (house_ != kNoModel) {
        renderer.set_instances(house_, {});
    }
    if (models_loaded_) {
        for (const render::ModelId id : models_) {
            if (id != kNoModel) {
                renderer.set_instances(id, {});
            }
        }
    }
    renderer.clear_terrain();
    shown_ = false;
}

}  // namespace sc
