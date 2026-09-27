// Tree species, size classes, biomes and map types (phase 6b, see
// docs/ARBOLES.md). Tables in code for now, shaped like the data files they
// become in phase 7. Integers only: the generator uses them.
#pragma once

#include <cstdint>
#include <span>

namespace sc::sim {

enum class TreeSize : std::uint8_t { Small, Medium, Large, Huge, Count };

enum class Species : std::uint8_t {
    Oak,
    Pine,
    Toog,
    Eucalyptus,
    Sequoia,
    MountainAsh,
    Cherry,
    Jacaranda,
    TulipTree,
    SilkFloss,
    Magnolia,
    Flamboyant,
    Bottlebrush,
    StonePine,
    Elm,
    Lemon,
    Apple,
    Orange,
    Pear,
    Peach,
    Avocado,
    Count
};

enum class Biome : std::uint8_t { Temperate, Pinewood, Giants, Australian, Flowering, Orchard, Count };

enum class MapType : std::uint8_t { Classic, Young, Giants, Northern, Varied, Single, Count };

inline constexpr std::size_t kTreeSizes = static_cast<std::size_t>(TreeSize::Count);
inline constexpr std::size_t kSpeciesCount = static_cast<std::size_t>(Species::Count);
inline constexpr std::size_t kBiomeCount = static_cast<std::size_t>(Biome::Count);
inline constexpr std::size_t kMapTypeCount = static_cast<std::size_t>(MapType::Count);

struct SizeInfo {
    const char* id;
    std::int32_t min_cm;        // Height range.
    std::int32_t max_cm;
    std::int32_t model_cm;      // Height of the models of this size.
    std::int32_t spacing_m;     // Minimum distance between trunks of this size.
};

struct SpeciesInfo {
    const char* id;
    std::uint8_t sizes;  // Bit per TreeSize the species can have.
};

struct Weighted {
    std::uint8_t id;
    std::uint16_t weight;
};

struct BiomeInfo {
    const char* id;
    std::span<const Weighted> species;
    std::uint16_t size_weights[kTreeSizes];
    std::uint16_t density;  // Percent of the usual forest density.
    std::uint8_t grass;     // Decorative grass, 0..255.
};

struct MapTypeInfo {
    const char* id;
    std::span<const Weighted> biomes;    // Empty for Single: the chosen biome.
    std::uint16_t size_bias[kTreeSizes];  // Percent applied to the biome's size weights.
    std::int32_t patch_m;                // Typical biome region size.
};

[[nodiscard]] const SizeInfo& size_info(TreeSize size);
[[nodiscard]] const SpeciesInfo& species_info(Species species);
[[nodiscard]] const BiomeInfo& biome_info(Biome biome);
[[nodiscard]] const MapTypeInfo& map_type_info(MapType type);

[[nodiscard]] bool species_has_size(Species species, TreeSize size);
// The allowed size closest to `wanted` (smaller wins a tie).
[[nodiscard]] TreeSize fit_size(Species species, TreeSize wanted);

// Picks from weights with a value in 0..65535 (a slice of a hash). Returns
// the id, or the first entry if all weights are 0.
[[nodiscard]] std::uint8_t pick_weighted(std::span<const Weighted> items, std::uint32_t roll16);

}  // namespace sc::sim
