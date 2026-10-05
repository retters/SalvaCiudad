#include "sim/content.h"

#include <algorithm>

namespace sc::sim {

namespace {

template <typename T>
DefIndex find_def(const std::vector<T>& list, std::string_view id) {
    for (std::size_t i = 0; i < list.size(); ++i) {
        if (list[i].id == id) {
            return static_cast<DefIndex>(i);
        }
    }
    return kNoDef;
}

}  // namespace

DefIndex Content::find_resource(std::string_view id) const {
    return find_def(resources, id);
}

DefIndex Content::find_building(std::string_view id) const {
    return find_def(buildings, id);
}

DefIndex Content::find_recipe(std::string_view id) const {
    return find_def(recipes, id);
}

DefIndex Content::find_crop(std::string_view id) const {
    return find_def(crops, id);
}

std::string race_body_file(std::string_view body) {
    return "models/characters/" + std::string(body) + ".glb";
}

std::int32_t wildflowers(const MapData& map, const Content& content, std::int32_t cx, std::int32_t cz) {
    if (cx < 0 || cz < 0 || cx >= map.size || cz >= map.size || map.water_at(cx, cz)) {
        return 0;
    }
    const Terrain terrain = map.terrain_at(cx, cz);
    const std::int32_t ground = terrain == Terrain::Meadow ? 100 : terrain == Terrain::Grass ? 45 : 0;
    if (ground == 0) {
        return 0;
    }
    const std::uint8_t b = map.biome_at(cx, cz);
    const std::int32_t biome = b < content.flora.biomes.size() ? content.flora.biomes[b].flowers : 100;
    // Patches: squares of 8 m, four in ten with flowers, some thicker than others.
    std::uint32_t h = static_cast<std::uint32_t>(cx >> 3) * 0x9E3779B1u ^ static_cast<std::uint32_t>(cz >> 3) * 0x85EBCA77u;
    h ^= h >> 15;
    h *= 0x2C1B3C6Du;
    h ^= h >> 12;
    h *= 0x297A2D39u;
    h ^= h >> 15;
    const auto patch = static_cast<std::int32_t>(h % 100u);
    if (patch < 60) {
        return 0;
    }
    return std::min(100, ground * biome / 100 * (patch - 40) / 60);
}

std::string pile_file(std::string_view pile, int level) {
    return std::string(pile) + "_" + std::to_string(level) + ".glb";
}

const FeatureDef* Content::feature(FeatureKind kind) const {
    for (const FeatureDef& f : features) {
        if (f.kind == kind) {
            return &f;
        }
    }
    return nullptr;
}

}  // namespace sc::sim
