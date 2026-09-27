// Procedural map generation from a seed (section 7.6). Deterministic: the
// same settings give the same map, bit for bit, on every machine.
#pragma once

#include <cstdint>
#include <functional>
#include <optional>

#include "sim/map.h"

namespace sc::sim {

enum class GenStage : std::uint8_t { Relief, Lakes, Rivers, Soil, Biomes, Forests, Resources, Starts, Count };

// Called now and then with the stage and its progress (0..100). Returning
// false cancels the generation.
using GenProgress = std::function<bool(GenStage stage, int percent)>;

// Empty if cancelled.
[[nodiscard]] std::optional<MapData> generate_map(const MapSettings& settings, const GenProgress& progress = {});

// Tuning shared with the tests.
namespace worldgen {
// Changes whenever the same settings would give a different map. Saved with
// the map (decision D-620).
inline constexpr std::uint16_t kGeneratorVersion = 3;
inline constexpr std::int32_t kStartClearRadius = 25;       // Meters kept free for the town center.
inline constexpr std::int32_t kStartResourceRadius = 180;   // Where each start is guaranteed resources.
inline constexpr std::int32_t kStartMinStones = 2;
inline constexpr std::int32_t kStartMinBerries = 2;
inline constexpr std::int32_t kStartMinTrees = 60;
inline constexpr std::int32_t kStartMaxWaterDistance = 150;  // A start always has water this close.
}  // namespace worldgen

}  // namespace sc::sim
