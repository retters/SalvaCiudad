// Procedural map generation from a seed (section 7.6). Deterministic: the
// same settings give the same map, bit for bit, on every machine. The
// ground is shaped by the hierarchical generator (worldgen_hier.h); the
// water, soil and life stages are here (phase 49: the only generator).
#pragma once

#include <array>
#include <cstdint>
#include <functional>
#include <optional>
#include <vector>

#include "sim/content.h"
#include "sim/map.h"

namespace sc::sim {

enum class GenStage : std::uint8_t { Relief, Lakes, Rivers, Soil, Biomes, Forests, Resources, Starts, Count };

// Called now and then with the stage and its progress (0..100). Returning
// false cancels the generation.
using GenProgress = std::function<bool(GenStage stage, int percent)>;

// Rules from the mods that change a generated map (section 7.13). Called
// once, on the generation thread, after everything else; the rules must be
// deterministic. Returning false cancels the generation.
class MapHooks {
public:
    virtual ~MapHooks() = default;
    virtual bool map_generated(MapData& map) = 0;
};

// Empty if cancelled. `content` gives the species, biomes and map types;
// map type and biome indices out of range fall back to the first ones.
// The map lists the landforms it got (MapData::landforms).
[[nodiscard]] std::optional<MapData> generate_map(const MapSettings& settings, const Content& content,
                                                  const GenProgress& progress = {}, MapHooks* hooks = nullptr);

// Tuning shared with the tests.
namespace worldgen {
// Changes whenever the same settings would give a different map. Saved with
// the map (decision D-620). It goes on from the hierarchical generator's
// own number, which it was until phase 49 (D-4902).
inline constexpr std::uint16_t kGeneratorVersion = 10;
inline constexpr std::int32_t kStartClearRadius = 25;       // Meters kept free for the town center.
inline constexpr std::int32_t kStartResourceRadius = 180;   // Where each start is guaranteed resources.
inline constexpr std::int32_t kStartMinStones = 4;
// Phase 83: each start has a stone deposit, medium or large, this near (in
// a straight line; the walk is somewhat longer).
inline constexpr std::int32_t kStartDepositRadius = 200;
// Phase 101: clay and coal within these many meters of every start.
inline constexpr std::int32_t kStartClayRadius = 250;
inline constexpr std::int32_t kStartCoalRadius = 400;
// Phase 102: loose stones, in tenths of a group per km² (a group is one to
// three), and how many every start has within how many meters.
inline constexpr std::int32_t kLooseStonesPerKm2 = 2000;
inline constexpr std::int32_t kStartMinLooseStones = 6;
inline constexpr std::int32_t kStartLooseRadius = 80;
inline constexpr std::int32_t kStartMinBerries = 4;
// Phase 98: trees with a hive, nests, and stumps or rings of mushrooms.
inline constexpr std::int32_t kStartMinBeeTrees = 2;
inline constexpr std::int32_t kStartMinNests = 2;
inline constexpr std::int32_t kStartMinMushrooms = 3;
inline constexpr std::int32_t kStartMinTrees = 60;
inline constexpr std::int32_t kStartMaxWaterDistance = 150;  // A start always has water this close.

// Phases 22 and 25: the map types with islands.
struct Island {
    std::int32_t x = 0;       // Center, meters.
    std::int32_t z = 0;
    std::int32_t radius = 0;  // Before its shape is bent: land reaches up to 1.7 times this.
    std::uint8_t town = 0;    // Whose archipelago.
    bool operator==(const Island&) const = default;
};
// Where the islands of a map of `cells` per side go (phase 25): one main
// island per town first, far from each other, then each town's smaller
// ones around its main island; all apart, with sea between them and
// around the map.
[[nodiscard]] std::vector<Island> island_layout(std::uint64_t seed, std::int32_t cells, std::int32_t towns,
                                                std::int32_t per_town);
// How many islands per town fit in a map size so that towns still get
// room (at least 1).
[[nodiscard]] std::int32_t max_islands_per_town(MapSize size, std::int32_t towns);
}  // namespace worldgen

}  // namespace sc::sim
