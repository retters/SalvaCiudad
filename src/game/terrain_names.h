// What is under the cursor, by name (phase 37): the ground, the water
// (river, lake or sea) and the landforms the generator placed there. Only
// for the statistics window (F3) and the developer tools; the simulation
// never reads it.
#pragma once

#include <cstdint>
#include <string>
#include <vector>

#include "sim/content.h"
#include "sim/map.h"

namespace sc {

enum class WaterKind : std::uint8_t { None, River, Lake, Sea };

struct CellDescription {
    bool inside = false;  // False: outside the map; nothing else is set.
    std::int32_t cx = 0;
    std::int32_t cz = 0;
    std::int32_t height_cm = 0;
    std::int32_t slope_pct = 0;  // Height difference across the cell, per 100.
    sim::Terrain terrain = sim::Terrain::Grass;
    std::uint8_t biome = 0;
    std::int32_t fertility_pct = 0;
    WaterKind water = WaterKind::None;
    std::int32_t water_depth_cm = 0;
    bool coast = false;  // Dry land with the sea close by.
    // Sorted, each kind once. Never Coast or River (see `coast` and `water`).
    std::vector<sim::LandformKind> landforms;
};

class TerrainNames {
public:
    // Describes a cell of `map`, indexing its landforms the first time (or
    // when it is another map). Cheap enough to call on every mouse move.
    [[nodiscard]] CellDescription describe(const sim::MapData& map, std::int32_t cx, std::int32_t cz);
    // Forgets the index (the map it was built for is gone).
    void reset() { landforms_ = nullptr; buckets_.clear(); }

    // Meters per side of the index's squares.
    static constexpr std::int32_t kBucket = 128;

private:
    void build(const sim::MapData& map);

    const sim::Landform* landforms_ = nullptr;  // The map's list it was built for.
    std::size_t count_ = 0;
    std::int32_t side_ = 0;  // Squares per side.
    std::vector<std::vector<std::uint32_t>> buckets_;  // Landforms reaching each square.
};

// Text keys for the names.
[[nodiscard]] const char* landform_key(sim::LandformKind kind);
[[nodiscard]] const char* water_key(WaterKind kind);
[[nodiscard]] const char* terrain_key(sim::Terrain terrain);

// The description as lines of text in the active language. `content` gives
// the biome names (may be null).
[[nodiscard]] std::vector<std::string> describe_lines(const CellDescription& d, const sim::Content* content);

}  // namespace sc
