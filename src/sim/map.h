// The game map: terrain heights, water, soil and the natural features on
// it, generated from a seed (section 7.6). Part of the simulation state, so
// it is integer-only and identical on every machine.
#pragma once

#include <array>
#include <cstdint>
#include <vector>

#include "sim/fixed.h"
#include "sim/flora.h"
#include "sim/serialize.h"

namespace sc::sim {

enum class MapSize : std::uint8_t { Small, Medium, Large, Huge, Giant, Colossal, Count };
// Phase 56: how much of something a map has is a percent, 0 to
// kMaxPercent, where 100 is the usual. These name the values the three
// levels of before had.
inline constexpr std::uint8_t kMaxPercent = 200;
struct Amount {
    static constexpr std::uint8_t Low = 50, Normal = 100, High = 200;
};
struct Relief {
    static constexpr std::uint8_t Low = 50, Gentle = 100, Mountainous = 175;
};
// The sea: none; along one side; along two (a corner or opposite sides);
// around one island per town; or around several islands per town.
enum class Sea : std::uint8_t { None, OneSide, TwoSides, Islands, Archipelago, Count };

// Most natural features a map may have (saves refuse more): a colossal
// map with thick forests has several million.
inline constexpr std::uint32_t kMaxMapFeatures = 32'000'000;
// Islands per town on a map type with islands (phase 22).
inline constexpr std::uint8_t kMaxIslandsPerTown = 8;
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

// The climate settings go from 0 to this, in percent.
inline constexpr std::uint8_t kMaxClimatePercent = kMaxPercent;
// Half the temperature range from the north to the south, at most.
inline constexpr std::uint8_t kMaxClimateRange = 30;

struct MapSettings {
    std::uint64_t seed = 1;
    MapSize size = MapSize::Medium;
    // Percents (0..kMaxPercent, 100 the usual).
    std::uint8_t rivers = 100;
    std::uint8_t lakes = 100;
    std::uint8_t forests = 100;
    std::uint8_t resources = 100;
    // Flat to mountainous. The new game form starts at Relief::Gentle (its
    // 100 %); a map made without choosing is flat, as it always was.
    std::uint8_t relief = Relief::Low;
    std::uint8_t players = 1;           // Start positions to place (1..12).
    // The biomes the map may have: bit i is biome i of the content (the
    // first 64). 0: all of them.
    std::uint64_t biomes = 0;
    // The climate, in percent: 100 is a map with cold in the north and warm
    // in the south; less is colder (or drier), more is warmer (or wetter).
    std::uint8_t temperature = 100;
    std::uint8_t humidity = 100;
    // Half the range of temperature from north to south (0..kMaxClimateRange):
    // the most gives a map from cold to warm, with every biome; a narrow one,
    // a map of one climate.
    std::uint8_t climate_range = kMaxClimateRange;
    // Phase 55: how many giant trees, in percent of the usual for the size
    // (0: none; up to kMaxClimatePercent).
    std::uint8_t giants = 100;
    // Separate maps (section 7.7): each player gets a map of `size` from
    // seed + player number, laid side by side in one world with no way
    // across. Only with more than one player.
    bool separate = false;
    // Islands per town, for an archipelago (1..kMaxIslandsPerTown):
    // 2 towns with 3 islands each make 6 islands.
    std::uint8_t islands = 2;
    Sea sea = Sea::None;
    // Phase 27: how many regions are not plains, and how many valleys and
    // canyons there are (phase 39). A percent.
    std::uint8_t landforms = 100;

    // An island map: the sea surrounds islands instead of one piece of land.
    [[nodiscard]] bool island_map() const { return sea == Sea::Islands || sea == Sea::Archipelago; }
    // Islands per town on it: one, or `islands` on an archipelago.
    [[nodiscard]] std::uint8_t islands_per_town() const { return sea == Sea::Archipelago ? islands : std::uint8_t{1}; }

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

// (Phase 98: a tree with a hive, a nest, an old stump or hollow log, a ring of mushrooms.)
// (Phase 101: deposits of clay, of coal and of gold. Phase 102: loose stones.)
enum class FeatureType : std::uint8_t {
    Tree, Stone, IronOre, BerryBush, Herbs, StoneDeposit, BeeTree, Nest, Stump, MushroomRing,
    ClayDeposit, CoalDeposit, GoldDeposit, LooseStones,
    // Phase 110: what a fisher's hut fishes better by: a shoal in the water (it is fished out and comes
    // back with the season), a bank of reeds on a fresh shore; and ducks, for eggs and meat.
    FishShoal, ReedBank, Ducks, Count
};

// A deposit (phases 83 and 101): finite, in three sizes, standing on ground
// that cannot be walked or built on, worked by several at once.
[[nodiscard]] constexpr bool is_deposit(FeatureType t) {
    return t == FeatureType::StoneDeposit || t == FeatureType::ClayDeposit || t == FeatureType::CoalDeposit ||
           t == FeatureType::GoldDeposit;
}

// Phase 83: a stone deposit is an outcrop in three sizes (0..2). A size
// holds the feature's amount, 5/2 of it or 25/4 of it (800, 2000 and 5000
// in the base game), stands on a square of 4, 6 or 8 m that cannot be
// walked or built on, and is as large as what is left in it.
inline constexpr std::uint8_t kDepositSizes = 3;
[[nodiscard]] constexpr std::int32_t deposit_amount(std::int32_t base, std::uint8_t size) {
    return size == 0 ? base : size == 1 ? base * 5 / 2 : base * 25 / 4;
}
[[nodiscard]] constexpr std::uint8_t deposit_size(std::int32_t base, std::int32_t amount) {
    return amount > deposit_amount(base, 1) ? std::uint8_t{2} : amount > base ? std::uint8_t{1} : std::uint8_t{0};
}
[[nodiscard]] constexpr std::int32_t deposit_half_side(std::uint8_t size) {
    return 2 + (size < kDepositSizes ? size : kDepositSizes - 1);
}

// A natural object on the map. Positions are in meters from the map's
// corner (0, 0); rotation is a binary angle. For trees, `scale` is the
// height over the size's model height (see flora.h).
struct MapFeature {
    FeatureType type = FeatureType::Tree;
    std::uint8_t species = 0;  // Species, for trees.
    std::uint8_t size = 0;     // TreeSize, for trees; 0..2 for a stone deposit, by what is left.
    std::uint16_t rotation = 0;
    Fixed x;
    Fixed z;
    Fixed scale = Fixed::one();

    bool operator==(const MapFeature&) const = default;
};

// (Phase 109: rabbits, small game that eats the vegetables; and the lynx, which is not hunted and hunts them.
// Neither is a creature that walks the map: a zone and how many live in it.)
// (Phase 111: mammoths, in the cold biomes and only in winter; the same.)
// (Phase 112: the glade of a unicorn, one in each stretch of enchanted wood: its radius is how near a
// tree may be felled without frightening it away; it holds 1 while the unicorn grazes there, and 0 for ever after.)
enum class ZoneType : std::uint8_t { Deer, Boar, Wolves, Bears, Rabbits, Lynx, Mammoths, Unicorn, Count };

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

// The named features a generation placed (phases 37 to 41): each along a
// line of points (x, z in meters from the map's corner), `width` meters
// across; a single point for the round ones (regions, islets, islands).
// Only for showing names: no rule of the game reads them. New kinds go at
// the end (saves hold the numbers).
enum class LandformKind : std::uint8_t {
    // Structures of the coast and the sea (phase 41), rivers.
    Gulf, Peninsula, Islet, Island, River,
    // Regions (phase 39); a plateau is a region too.
    Plain, Hills, Mountains, Plateau, Basin, Sea,
    // Structures on land (phase 40).
    Crest, Pass, Cliff, Ramp, Valley, Canyon,
    Count
};
struct Landform {
    LandformKind kind = LandformKind::Plain;
    std::vector<std::array<std::int32_t, 2>> points;
    std::int32_t width = 0;

    bool operator==(const Landform&) const = default;
};
// Most landforms and points a map may have (saves refuse more).
inline constexpr std::uint32_t kMaxLandforms = 100'000;
inline constexpr std::uint32_t kMaxLandformPoints = 4096;
// The generator tells, per square of this many meters, which region and
// which structure is there (phase 39).
inline constexpr std::int32_t kOwnerBlock = 8;

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
    // Phase 37, for the names under the cursor: the landforms, and the
    // sea's water surface per region in centimeters (0 = no sea there).
    // Not in checksum(): they describe the terrain, they are not part of it.
    std::vector<Landform> landforms;
    std::vector<std::uint16_t> sea_levels;
    // Phase 39: per kOwnerBlock square, row by row, the landform (index + 1,
    // 0 = none) of its region and of its structure.
    std::vector<std::uint16_t> region_owner;
    std::vector<std::uint16_t> structure_owner;
    // Phase 54, for the names under the cursor: per square of the same
    // grid, the temperature (low byte) and the humidity (high byte) that
    // chose its biome, 0 to 100. Empty on a map of one biome.
    std::vector<std::uint16_t> climate;
    [[nodiscard]] std::int32_t owner_side() const { return (size + kOwnerBlock - 1) / kOwnerBlock; }
    // The landform index + 1 at a cell in one of those grids (0 = none).
    [[nodiscard]] std::uint16_t owner_at(const std::vector<std::uint16_t>& grid, std::int32_t cx, std::int32_t cz) const;

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
