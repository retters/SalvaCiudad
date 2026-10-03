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
    // One of the two: a model file prefix inside the mod, completed with the
    // size ("models/props/tree_oak" + "_large.glb"), or the files of each
    // state (phase 51), each a list of variants; a state without files
    // looks like Bloom (an evergreen declares only that one). A species
    // with states has one model for all sizes, scaled to each tree.
    std::string model;
    std::vector<std::string> state_models[kTreeStates];
    // Phase 52: the far version of each of those files ("" if it has none):
    // a few hundred triangles, drawn where the tree is small on screen.
    std::vector<std::string> state_far[kTreeStates];
    [[nodiscard]] bool by_state() const { return !state_models[0].empty(); }
    std::uint8_t sizes = 0;  // Bit per TreeSize the species can have.
    std::int32_t logs[kTreeSizes] = {2, 5, 10, 20};  // Wood per tree of each size.
    bool evergreen = false;  // Keeps its leaves in autumn and winter (the look only).
    bool landmark = false;   // Phase 34: its silhouette shows through the fog of war.
};

struct BiomeDef {
    std::string id;
    std::string name_key;
    std::vector<Weighted> species;
    std::uint16_t size_weights[kTreeSizes] = {25, 25, 25, 25};
    std::uint16_t density = 100;  // Percent of the usual forest density.
    std::uint8_t grass = 180;     // Decorative grass, 0..255.
};

struct MapTypeDef {
    std::string id;
    std::string name_key;
    std::vector<Weighted> biomes;  // Empty: a single biome chosen by the player.
    std::uint16_t size_bias[kTreeSizes] = {100, 100, 100, 100};
    std::int32_t patch_m = 350;
    // Phase 22: the sea surrounds islands, a few per town.
    bool islands = false;
};

// Limits so an index fits in the map's bytes.
inline constexpr std::size_t kMaxSpecies = 250;
inline constexpr std::size_t kMaxBiomes = 250;
inline constexpr std::size_t kMaxMapTypes = 250;

struct Flora {
    std::vector<SpeciesDef> species;
    std::vector<BiomeDef> biomes;
    std::vector<MapTypeDef> map_types;

    [[nodiscard]] bool species_has_size(std::size_t species, TreeSize size) const;
    // The allowed size closest to `wanted` (smaller wins a tie).
    [[nodiscard]] TreeSize fit_size(std::size_t species, TreeSize wanted) const;
    [[nodiscard]] int find_species(std::string_view id) const;  // -1 if missing.
    [[nodiscard]] int find_biome(std::string_view id) const;
    [[nodiscard]] int find_map_type(std::string_view id) const;
};

// Picks from weights with a value in 0..65535 (a slice of a hash). Returns
// the id, or the first entry if all weights are 0.
[[nodiscard]] std::uint8_t pick_weighted(std::span<const Weighted> items, std::uint32_t roll16);

}  // namespace sc::sim
