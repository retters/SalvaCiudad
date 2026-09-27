#include "sim/flora.h"

namespace sc::sim {

namespace {

constexpr std::uint8_t S = 1u << 0;  // Small.
constexpr std::uint8_t M = 1u << 1;  // Medium.
constexpr std::uint8_t L = 1u << 2;  // Large.
constexpr std::uint8_t H = 1u << 3;  // Huge.

constexpr SizeInfo kSizes[kTreeSizes] = {
    {"small", 100, 700, 450, 3},
    {"medium", 700, 1200, 950, 5},
    {"large", 1200, 2400, 1800, 8},
    {"huge", 2400, 4300, 3300, 12},
};

// In Species order.
constexpr SpeciesInfo kSpecies[kSpeciesCount] = {
    {"oak", S | M | L},
    {"pine", S | M | L | H},
    {"toog", M | L | H},
    {"eucalyptus", S | M | L | H},
    {"sequoia", S | M | L | H},
    {"mountain_ash", L | H},
    {"cherry", S | M},
    {"jacaranda", S | M | L},
    {"tulip_tree", S | M | L},
    {"silk_floss", S | M | L},
    {"magnolia", S | M | L},
    {"flamboyant", S | M},
    {"bottlebrush", S},
    {"stone_pine", S | M | L},
    {"elm", S | M | L},
    {"lemon", S},
    {"apple", S | M},
    {"orange", S},
    {"pear", S | M},
    {"peach", S},
    {"avocado", S | M},
};

constexpr std::uint8_t sp(Species s) {
    return static_cast<std::uint8_t>(s);
}
constexpr std::uint8_t bi(Biome b) {
    return static_cast<std::uint8_t>(b);
}

constexpr Weighted kTemperate[] = {{sp(Species::Oak), 35},   {sp(Species::Pine), 25},  {sp(Species::Elm), 20},
                                   {sp(Species::Magnolia), 5}, {sp(Species::Apple), 5}, {sp(Species::Pear), 5},
                                   {sp(Species::Cherry), 5}};
constexpr Weighted kPinewood[] = {{sp(Species::Pine), 75}, {sp(Species::StonePine), 20}, {sp(Species::Oak), 5}};
constexpr Weighted kGiants[] = {{sp(Species::Sequoia), 40}, {sp(Species::MountainAsh), 25}, {sp(Species::Toog), 20},
                                {sp(Species::Eucalyptus), 15}};
constexpr Weighted kAustralian[] = {
    {sp(Species::Eucalyptus), 45}, {sp(Species::Bottlebrush), 30}, {sp(Species::MountainAsh), 25}};
constexpr Weighted kFlowering[] = {{sp(Species::Jacaranda), 25}, {sp(Species::Flamboyant), 20},
                                   {sp(Species::TulipTree), 20}, {sp(Species::SilkFloss), 15},
                                   {sp(Species::Magnolia), 10},  {sp(Species::Cherry), 10}};
constexpr Weighted kOrchard[] = {{sp(Species::Apple), 20}, {sp(Species::Pear), 15},  {sp(Species::Peach), 15},
                                 {sp(Species::Orange), 15}, {sp(Species::Lemon), 15}, {sp(Species::Avocado), 10},
                                 {sp(Species::Cherry), 10}};

// In Biome order.
constexpr BiomeInfo kBiomes[kBiomeCount] = {
    {"temperate", kTemperate, {30, 35, 30, 5}, 100, 200},
    {"pinewood", kPinewood, {25, 35, 30, 10}, 115, 120},
    {"giants", kGiants, {15, 20, 30, 35}, 70, 170},
    {"australian", kAustralian, {25, 30, 30, 15}, 75, 110},
    {"flowering", kFlowering, {35, 40, 25, 0}, 90, 210},
    {"orchard", kOrchard, {60, 40, 0, 0}, 55, 230},
};

constexpr Weighted kClassicBiomes[] = {{bi(Biome::Temperate), 35},  {bi(Biome::Pinewood), 20},
                                       {bi(Biome::Flowering), 15},  {bi(Biome::Orchard), 10},
                                       {bi(Biome::Australian), 10}, {bi(Biome::Giants), 10}};
constexpr Weighted kGiantBiomes[] = {{bi(Biome::Giants), 50}, {bi(Biome::Temperate), 25}, {bi(Biome::Pinewood), 25}};
constexpr Weighted kNorthernBiomes[] = {{bi(Biome::Pinewood), 75}, {bi(Biome::Temperate), 25}};
constexpr Weighted kVariedBiomes[] = {{bi(Biome::Temperate), 1},  {bi(Biome::Pinewood), 1}, {bi(Biome::Giants), 1},
                                      {bi(Biome::Australian), 1}, {bi(Biome::Flowering), 1}, {bi(Biome::Orchard), 1}};

// In MapType order.
constexpr MapTypeInfo kMapTypes[kMapTypeCount] = {
    {"classic", kClassicBiomes, {100, 100, 100, 100}, 350},
    {"young", kClassicBiomes, {200, 100, 0, 0}, 350},
    {"giants", kGiantBiomes, {60, 80, 150, 200}, 450},
    {"northern", kNorthernBiomes, {100, 100, 100, 100}, 400},
    {"varied", kVariedBiomes, {100, 100, 100, 100}, 180},
    {"single", {}, {100, 100, 100, 100}, 0},
};

}  // namespace

const SizeInfo& size_info(TreeSize size) {
    const auto i = static_cast<std::size_t>(size);
    return kSizes[i < kTreeSizes ? i : 0];
}

const SpeciesInfo& species_info(Species species) {
    const auto i = static_cast<std::size_t>(species);
    return kSpecies[i < kSpeciesCount ? i : 0];
}

const BiomeInfo& biome_info(Biome biome) {
    const auto i = static_cast<std::size_t>(biome);
    return kBiomes[i < kBiomeCount ? i : 0];
}

const MapTypeInfo& map_type_info(MapType type) {
    const auto i = static_cast<std::size_t>(type);
    return kMapTypes[i < kMapTypeCount ? i : 0];
}

bool species_has_size(Species species, TreeSize size) {
    return (species_info(species).sizes >> static_cast<unsigned>(size) & 1u) != 0;
}

TreeSize fit_size(Species species, TreeSize wanted) {
    const int w = static_cast<int>(wanted);
    for (int d = 0; d < static_cast<int>(kTreeSizes); ++d) {
        for (const int candidate : {w - d, w + d}) {
            if (candidate >= 0 && candidate < static_cast<int>(kTreeSizes) &&
                species_has_size(species, static_cast<TreeSize>(candidate))) {
                return static_cast<TreeSize>(candidate);
            }
        }
    }
    return TreeSize::Small;
}

std::uint8_t pick_weighted(std::span<const Weighted> items, std::uint32_t roll16) {
    std::uint32_t total = 0;
    for (const Weighted& w : items) {
        total += w.weight;
    }
    if (items.empty()) {
        return 0;
    }
    if (total == 0) {
        return items.front().id;
    }
    std::uint32_t target = (roll16 & 0xFFFFu) * total >> 16;
    for (const Weighted& w : items) {
        if (target < w.weight) {
            return w.id;
        }
        target -= w.weight;
    }
    return items.back().id;
}

}  // namespace sc::sim
