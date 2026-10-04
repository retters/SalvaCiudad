// Trees: the four size classes (fixed in code) and the species, biomes and
// map types, which are data from the mods (docs/ARBOLES.md). Integers only:
// the generator uses them.
#pragma once

#include <cstdint>
#include <span>
#include <string>
#include <string_view>
#include <vector>

namespace sc::sim {

enum class TreeSize : std::uint8_t { Small, Medium, Large, Huge, Count };

inline constexpr std::size_t kTreeSizes = static_cast<std::size_t>(TreeSize::Count);

struct SizeInfo {
    const char* id;
    std::int32_t min_cm;     // Height range.
    std::int32_t max_cm;
    std::int32_t model_cm;   // Height of the models of this size.
    std::int32_t spacing_m;  // Minimum distance between trunks of this size.
};

[[nodiscard]] const SizeInfo& size_info(TreeSize size);

struct Weighted {
    std::uint8_t id;  // Index into the species or biome list.
    std::uint16_t weight;
};

// How a tree looks through the year (phase 51): in leaf or in flower, in
// its autumn colors, and bare. Only the look; the simulation ignores it.
enum class TreeState : std::uint8_t { Bloom, Autumn, Bare, Count };
inline constexpr std::size_t kTreeStates = static_cast<std::size_t>(TreeState::Count);

struct SpeciesDef {
    std::string id;       // "core:oak"
    std::string name_key;
    std::string mod;      // Mod folder with the models.
    // The model files of each state (phase 51), each a list of variants; a
    // state without files looks like Bloom (an evergreen declares only that
    // one). One model serves all sizes, scaled to each tree.
    std::vector<std::string> state_models[kTreeStates];
    // Phase 52: the far version of each of those files ("" if it has none):
    // a few hundred triangles, drawn where the tree is small on screen.
    std::vector<std::string> state_far[kTreeStates];
    std::uint8_t sizes = 0;  // Bit per TreeSize the species can have.
    std::int32_t logs[kTreeSizes] = {2, 5, 10, 20};  // Wood per tree of each size.
    bool landmark = false;   // Phase 34: its silhouette shows through the fog of war.
    // Phase 84: the fruit a tree of each size bears a year (all 0: not a
    // fruit tree). It hangs from the start of summer to the end of autumn.
    std::int32_t fruit[kTreeSizes] = {0, 0, 0, 0};
    [[nodiscard]] bool fruit_tree() const {
        for (const std::int32_t n : fruit) {
            if (n > 0) {
                return true;
            }
        }
        return false;
    }
    // Phase 55: a giant, placed a few per map as a landmark, each in a
    // clearing of this biome (-1: not a giant) and, if `giant_water_m` is
    // not 0, within that many meters of the water its biome asks for.
    std::int16_t giant_biome = -1;
    std::uint16_t giant_water_m = 0;
};

// Where a biome needs water nearby (phase 54).
enum class BiomeWater : std::uint8_t { Any, Fresh, Sea, Count };

// The kinds of region a biome may grow on, as bits of BiomeDef::regions.
enum class BiomeRegion : std::uint8_t { Plain, Hills, Mountains, Plateau, Basin, Count };

struct BiomeDef {
    std::string id;
    std::string name_key;
    std::vector<Weighted> species;
    std::uint16_t size_weights[kTreeSizes] = {25, 25, 25, 25};
    std::uint16_t density = 100;  // Percent of the usual forest density.
    std::uint8_t grass = 180;     // Decorative grass, 0..255.
    // Phase 54: where it likes to be. A place takes the biome that fits it
    // best. Temperature and humidity go from 0 to 100; the altitude is the
    // share of the map's land that lies lower, 0 to 100.
    std::uint8_t temperature[2] = {0, 100};
    std::uint8_t humidity[2] = {0, 100};
    std::uint8_t altitude[2] = {0, 100};
    BiomeWater water = BiomeWater::Any;  // Fresh or sea water must be within...
    std::uint16_t water_m = 0;           // ...this many meters.
    std::uint8_t regions = 0;            // Bit per BiomeRegion; 0: any.
    std::uint16_t weight = 100;          // How readily it wins where several fit.
};

// Limits so an index fits in the map's bytes.
inline constexpr std::size_t kMaxSpecies = 250;
inline constexpr std::size_t kMaxBiomes = 250;

struct Flora {
    std::vector<SpeciesDef> species;
    std::vector<BiomeDef> biomes;

    [[nodiscard]] bool species_has_size(std::size_t species, TreeSize size) const;
    // The allowed size closest to `wanted` (smaller wins a tie).
    [[nodiscard]] TreeSize fit_size(std::size_t species, TreeSize wanted) const;
    [[nodiscard]] int find_species(std::string_view id) const;  // -1 if missing.
    [[nodiscard]] int find_biome(std::string_view id) const;
};

// Picks from weights with a value in 0..65535 (a slice of a hash). Returns
// the id, or the first entry if all weights are 0.
[[nodiscard]] std::uint8_t pick_weighted(std::span<const Weighted> items, std::uint32_t roll16);

}  // namespace sc::sim
