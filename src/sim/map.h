// The game map: terrain heights, water, soil and the natural features on
// it, generated from a seed (section 7.6). Part of the simulation state, so
// it is integer-only and identical on every machine.
#pragma once

#include <cstdint>
#include <vector>

#include "sim/fixed.h"
#include "sim/flora.h"
#include "sim/serialize.h"

namespace sc::sim {

enum class MapSize : std::uint8_t { Small, Medium, Large, Huge, Giant, Colossal, Count };
enum class Amount : std::uint8_t { Low, Normal, High, Count };
enum class Relief : std::uint8_t { Low, Gentle, Mountainous, Count };

// Most natural features a map may have (saves refuse more): a colossal
// map with thick forests has several million.
inline constexpr std::uint32_t kMaxMapFeatures = 32'000'000;
// The biggest world: separate maps shrink to fit in it (Fixed positions
// reach 32767 m).
inline constexpr MapSize kMaxWorldSize = MapSize::Colossal;

// Side of the map in cells (1 cell = 1 m).
[[nodiscard]] constexpr std::int32_t map_cells(MapSize size) {
    switch (size) {
        case MapSize::Small: return 512;
        case MapSize::Medium: return 1024;
        case MapSize::Large: return 2048;
        case MapSize::Huge: return 4096;
        case MapSize::Giant: return 8192;
        case MapSize::Colossal: return 16384;
        case MapSize::Count: break;
    }
    return 512;
}

struct MapSettings {
    std::uint64_t seed = 1;
    MapSize size = MapSize::Medium;
    Amount water = Amount::Normal;      // Rivers and lakes.
    Amount forests = Amount::Normal;
    Amount resources = Amount::Normal;
    Relief relief = Relief::Low;
    std::uint8_t players = 1;           // Start positions to place (1..12).
    std::uint8_t map_type = 0;          // Index into the content's map types.
    std::uint8_t biome = 0;             // The only biome, for a map type without biomes.
    // Separate maps (section 7.7): each player gets a map of `size` from
    // seed + player number, laid side by side in one world with no way
    // across. Only with more than one player.
    bool separate = false;

    void write(BinaryWriter& w) const;
    [[nodiscard]] static bool read(BinaryReader& r, MapSettings& out);
    bool operator==(const MapSettings&) const = default;
};

// Regions per side of the world: 1 for a shared map, else enough for
// every player (2 x 2 up to four, 3 x 3 up to nine, 4 x 4 up to twelve).
[[nodiscard]] std::int32_t world_grid(const MapSettings& s);
// Each player's map size with separate maps: the chosen one, smaller if
// the whole world would pass the biggest map size.
[[nodiscard]] MapSize region_map_size(const MapSettings& s);
// Cells per side of the whole world.
[[nodiscard]] std::int32_t world_cells(const MapSettings& s);

enum class Terrain : std::uint8_t { Grass, Meadow, ForestFloor, Sand, Rock, Clay, Water, Count };

enum class FeatureType : std::uint8_t { Tree, Stone, IronOre, BerryBush, Herbs, Count };

// A natural object on the map. Positions are in meters from the map's
// corner (0, 0); rotation is a binary angle. For trees, `scale` is the
// height over the size's model height (see flora.h).
struct MapFeature {
    FeatureType type = FeatureType::Tree;
    std::uint8_t species = 0;  // Species, for trees.
    std::uint8_t size = 0;     // TreeSize, for trees.
    std::uint16_t rotation = 0;
    Fixed x;
    Fixed z;
    Fixed scale = Fixed::one();

    bool operator==(const MapFeature&) const = default;
};

enum class ZoneType : std::uint8_t { Deer, Boar, Wolves, Bears, Count };

// Where animals of a kind live.
struct Zone {
    ZoneType type = ZoneType::Deer;
    Fixed x;
    Fixed z;
    Fixed radius;

    bool operator==(const Zone&) const = default;
};

struct StartPosition {
    Fixed x;
    Fixed z;

    bool operator==(const StartPosition&) const = default;
};

struct MapData {
    MapSettings settings;
    std::uint16_t generator_version = 0;  // worldgen::kGeneratorVersion when made.
    std::int32_t size = 0;  // Cells per side.

    std::vector<std::uint16_t> heights;    // (size + 1)^2 vertices, centimeters.
    std::vector<std::uint16_t> water;      // size^2 cells: water surface in cm, 0 = dry.
    std::vector<std::uint8_t> terrain;     // size^2 cells, Terrain.
    std::vector<std::uint8_t> fertility;   // size^2 cells, 0..255.
    std::vector<std::uint8_t> biome;       // size^2 cells, index into the content's biomes.
    std::vector<MapFeature> features;
    std::vector<Zone> zones;
    std::vector<StartPosition> starts;

    [[nodiscard]] std::int32_t vertices_per_side() const { return size + 1; }
    // Separate maps: cells per side of a region (0 for a shared map) and
    // the region a cell is in (always 0 for a shared map). Player p's town
    // is in region p.
    [[nodiscard]] std::int32_t region_size() const;
    [[nodiscard]] std::int32_t region_at(std::int32_t cx, std::int32_t cz) const;
    [[nodiscard]] std::uint16_t height_cm(std::int32_t vx, std::int32_t vz) const;
    // Ground height in meters at a point, interpolated between vertices.
    [[nodiscard]] Fixed height_at(Fixed x, Fixed z) const;
    [[nodiscard]] Terrain terrain_at(std::int32_t cx, std::int32_t cz) const;
    [[nodiscard]] bool water_at(std::int32_t cx, std::int32_t cz) const;
    [[nodiscard]] std::uint8_t biome_at(std::int32_t cx, std::int32_t cz) const;
    // A tree's height in centimeters (0 for other features).
    [[nodiscard]] static std::int32_t tree_height_cm(const MapFeature& f);

    // Hash of everything generated: two machines with the same settings
    // must get the same value.
    [[nodiscard]] std::uint64_t checksum() const;
};

}  // namespace sc::sim
