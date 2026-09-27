#include <doctest.h>

#include <algorithm>
#include <chrono>
#include <cmath>
#include <ostream>
#include <tuple>
#include <vector>

#include "sim/map.h"
#include "sim/worldgen.h"
#include "test_util.h"

using namespace sc::sim;

namespace {

MapSettings settings(std::uint64_t seed, MapSize size, std::uint8_t players = 1) {
    MapSettings s;
    s.seed = seed;
    s.size = size;
    s.players = players;
    return s;
}

const Content& content() {
    return sc::test::core_content();
}

std::optional<MapData> gen(const MapSettings& s, const GenProgress& progress = {}) {
    return generate_map(s, content(), progress);
}

std::uint8_t species(std::string_view id) {
    const int i = content().flora.find_species(std::string("core:") + std::string(id));
    REQUIRE(i >= 0);
    return static_cast<std::uint8_t>(i);
}

std::uint8_t biome(std::string_view id) {
    const int i = content().flora.find_biome(std::string("core:") + std::string(id));
    REQUIRE(i >= 0);
    return static_cast<std::uint8_t>(i);
}

std::uint8_t map_type(std::string_view id) {
    const int i = content().flora.find_map_type(std::string("core:") + std::string(id));
    REQUIRE(i >= 0);
    return static_cast<std::uint8_t>(i);
}

double meters(Fixed f) {
    return static_cast<double>(f.raw()) / 65536.0;
}

double distance(Fixed ax, Fixed az, Fixed bx, Fixed bz) {
    return std::hypot(meters(ax) - meters(bx), meters(az) - meters(bz));
}

// Sizes of the connected water areas, and whether each touches the border.
struct WaterArea {
    std::size_t cells = 0;
    bool border = false;
};

std::vector<WaterArea> water_areas(const MapData& m) {
    std::vector<WaterArea> areas;
    std::vector<std::uint8_t> seen(m.water.size(), 0);
    std::vector<std::size_t> queue;
    const std::int32_t n = m.size;
    for (std::size_t start = 0; start < m.water.size(); ++start) {
        if (m.water[start] == 0 || seen[start] != 0) {
            continue;
        }
        WaterArea area;
        queue.assign(1, start);
        seen[start] = 1;
        for (std::size_t q = 0; q < queue.size(); ++q) {
            const std::size_t c = queue[q];
            ++area.cells;
            const auto x = static_cast<std::int32_t>(c % static_cast<std::size_t>(n));
            const auto z = static_cast<std::int32_t>(c / static_cast<std::size_t>(n));
            if (x == 0 || z == 0 || x == n - 1 || z == n - 1) {
                area.border = true;
            }
            const std::int32_t nx[4] = {x - 1, x + 1, x, x};
            const std::int32_t nz[4] = {z, z, z - 1, z + 1};
            for (int k = 0; k < 4; ++k) {
                if (nx[k] < 0 || nz[k] < 0 || nx[k] >= n || nz[k] >= n) {
                    continue;
                }
                const std::size_t nc = static_cast<std::size_t>(nz[k]) * static_cast<std::size_t>(n) + static_cast<std::size_t>(nx[k]);
                if (m.water[nc] != 0 && seen[nc] == 0) {
                    seen[nc] = 1;
                    queue.push_back(nc);
                }
            }
        }
        areas.push_back(area);
    }
    return areas;
}

// Islands: land areas left when the sea (water that reaches the border) is
// taken away, as the island each cell belongs to (-1 for the sea).
std::vector<std::int32_t> island_ids(const MapData& m, std::int32_t& count) {
    const std::int32_t n = m.size;
    const auto cells = static_cast<std::size_t>(n) * static_cast<std::size_t>(n);
    std::vector<std::uint8_t> sea(cells, 0);
    std::vector<std::size_t> queue;
    const auto idx = [n](std::int32_t x, std::int32_t z) {
        return static_cast<std::size_t>(z) * static_cast<std::size_t>(n) + static_cast<std::size_t>(x);
    };
    for (std::int32_t i = 0; i < n; ++i) {
        for (const std::size_t c : {idx(i, 0), idx(i, n - 1), idx(0, i), idx(n - 1, i)}) {
            if (m.water[c] != 0 && sea[c] == 0) {
                sea[c] = 1;
                queue.push_back(c);
            }
        }
    }
    const auto spread = [&](auto&& accept, auto&& mark) {
        for (std::size_t q = 0; q < queue.size(); ++q) {
            const auto x = static_cast<std::int32_t>(queue[q] % static_cast<std::size_t>(n));
            const auto z = static_cast<std::int32_t>(queue[q] / static_cast<std::size_t>(n));
            const std::int32_t nx[4] = {x - 1, x + 1, x, x};
            const std::int32_t nz[4] = {z, z, z - 1, z + 1};
            for (int k = 0; k < 4; ++k) {
                if (nx[k] >= 0 && nz[k] >= 0 && nx[k] < n && nz[k] < n && accept(idx(nx[k], nz[k]))) {
                    mark(idx(nx[k], nz[k]));
                    queue.push_back(idx(nx[k], nz[k]));
                }
            }
        }
    };
    spread([&](std::size_t c) { return m.water[c] != 0 && sea[c] == 0; }, [&](std::size_t c) { sea[c] = 1; });
    std::vector<std::int32_t> id(cells, -1);
    count = 0;
    for (std::size_t start = 0; start < cells; ++start) {
        if (sea[start] != 0 || id[start] >= 0) {
            continue;
        }
        id[start] = count;
        queue.assign(1, start);
        spread([&](std::size_t c) { return sea[c] == 0 && id[c] < 0; }, [&](std::size_t c) { id[c] = count; });
        ++count;
    }
    return id;
}

// The golden checksum of a small map. If the generator changes on purpose,
// update it (and the simulation rules version).
constexpr std::uint64_t kGoldenSmallMap = 0xf8a930e6954b4446ull;

}  // namespace

TEST_SUITE("worldgen") {
    TEST_CASE("the same settings give the same map") {
        const auto a = gen(settings(12345, MapSize::Small));
        const auto b = gen(settings(12345, MapSize::Small));
        REQUIRE(a.has_value());
        REQUIRE(b.has_value());
        CHECK(a->checksum() == b->checksum());
        CHECK(a->heights == b->heights);
        CHECK(a->features == b->features);
        const auto c = gen(settings(12346, MapSize::Small));
        REQUIRE(c.has_value());
        CHECK(c->checksum() != a->checksum());
    }

    TEST_CASE("the small map checksum is the same on every build") {
        const auto m = gen(settings(12345, MapSize::Small));
        REQUIRE(m.has_value());
        MESSAGE("small map checksum: " << m->checksum());
        CHECK(m->checksum() == kGoldenSmallMap);
    }

    TEST_CASE("layout and contents of a medium map") {
        const auto m = gen(settings(777, MapSize::Medium, 4));
        REQUIRE(m.has_value());
        CHECK(m->size == 1024);
        CHECK(m->heights.size() == 1025u * 1025u);
        CHECK(m->water.size() == 1024u * 1024u);
        std::size_t water = 0;
        std::size_t forest = 0;
        std::size_t disagree = 0;
        for (std::size_t i = 0; i < m->terrain.size(); ++i) {
            const bool wet = m->water[i] != 0;
            water += wet;
            forest += m->terrain[i] == static_cast<std::uint8_t>(Terrain::ForestFloor);
            // Water and the Water terrain type always agree.
            disagree += wet != (m->terrain[i] == static_cast<std::uint8_t>(Terrain::Water));
        }
        CHECK(disagree == 0);
        CHECK(water > 1000);
        CHECK(forest > m->terrain.size() / 10);
        std::size_t trees = 0;
        std::size_t stones = 0;
        for (const MapFeature& f : m->features) {
            CHECK(f.x >= Fixed{});
            CHECK(f.z >= Fixed{});
            CHECK(f.x < Fixed::from_int(m->size));
            CHECK(f.z < Fixed::from_int(m->size));
            CHECK_FALSE(m->water_at(f.x.floor_int(), f.z.floor_int()));
            trees += f.type == FeatureType::Tree;
            stones += f.type == FeatureType::Stone;
        }
        CHECK(trees > 10000);
        CHECK(stones > 20);
        CHECK_FALSE(m->zones.empty());
    }

    TEST_CASE("rivers end in a lake or at the border") {
        for (const std::uint64_t seed : {1ull, 2ull, 3ull, 4ull}) {
            MapSettings s = settings(seed, MapSize::Medium);
            s.water = Amount::High;
            const auto m = gen(s);
            REQUIRE(m.has_value());
            for (const WaterArea& a : water_areas(*m)) {
                // A water area inside the map is a lake (large) or part of
                // a river that reached one; never a dead-end stream.
                const bool ends_well = a.border || a.cells >= 150;
                CHECK_MESSAGE(ends_well, "seed " << seed << ": water area of " << a.cells << " cells");
            }
        }
    }

    TEST_CASE("water is above the ground it covers") {
        for (const Relief relief : {Relief::Low, Relief::Mountainous}) {
            MapSettings s = settings(61, MapSize::Medium);
            s.water = Amount::High;
            s.relief = relief;
            const auto m = gen(s);
            REQUIRE(m.has_value());
            std::size_t cells = 0;
            std::size_t dry = 0;
            for (std::int32_t z = 0; z < m->size; ++z) {
                for (std::int32_t x = 0; x < m->size; ++x) {
                    const std::uint16_t w = m->water[static_cast<std::size_t>(z) * static_cast<std::size_t>(m->size) +
                                                     static_cast<std::size_t>(x)];
                    if (w == 0) {
                        continue;
                    }
                    ++cells;
                    const std::uint16_t lowest = std::min({m->height_cm(x, z), m->height_cm(x + 1, z),
                                                           m->height_cm(x, z + 1), m->height_cm(x + 1, z + 1)});
                    dry += w <= lowest;
                }
            }
            CHECK(cells > 1000);
            // Every water cell holds some water over its lowest corner.
            CHECK(dry == 0);
        }
    }

    TEST_CASE("mountainous relief is higher") {
        MapSettings low = settings(62, MapSize::Medium);
        MapSettings high = low;
        high.relief = Relief::Mountainous;
        const auto a = gen(low);
        const auto b = gen(high);
        REQUIRE(a.has_value());
        REQUIRE(b.has_value());
        const auto range = [](const MapData& m) {
            const auto [lo, hi] = std::minmax_element(m.heights.begin(), m.heights.end());
            return static_cast<int>(*hi) - static_cast<int>(*lo);
        };
        CHECK(range(*b) > range(*a) + 3000);  // At least 30 m more, in cm.
        CHECK(b->starts.size() == 1);
    }

    TEST_CASE("start positions are valid, apart and fair") {
        for (const std::uint8_t players : {std::uint8_t{1}, std::uint8_t{4}, std::uint8_t{8}}) {
            const auto m = gen(settings(4242, MapSize::Medium, players));
            REQUIRE(m.has_value());
            REQUIRE(m->starts.size() == players);
            for (std::size_t i = 0; i < m->starts.size(); ++i) {
                const StartPosition& s = m->starts[i];
                const Terrain t = m->terrain_at(s.x.floor_int(), s.z.floor_int());
                CHECK(t != Terrain::Water);
                CHECK(t != Terrain::Rock);
                int stones = 0;
                int berries = 0;
                int trees = 0;
                for (const MapFeature& f : m->features) {
                    const double d = distance(f.x, f.z, s.x, s.z);
                    CHECK(d > worldgen::kStartClearRadius);
                    if (d <= worldgen::kStartResourceRadius) {
                        stones += f.type == FeatureType::Stone;
                        berries += f.type == FeatureType::BerryBush;
                        trees += f.type == FeatureType::Tree;
                    }
                }
                CHECK(stones >= worldgen::kStartMinStones);
                CHECK(berries >= worldgen::kStartMinBerries);
                CHECK(trees >= worldgen::kStartMinTrees);
                // Water within reach.
                bool water = false;
                const std::int32_t r = worldgen::kStartMaxWaterDistance;
                for (std::int32_t dz = -r; dz <= r && !water; dz += 2) {
                    for (std::int32_t dx = -r; dx <= r && !water; dx += 2) {
                        water = m->water_at(s.x.floor_int() + dx, s.z.floor_int() + dz);
                    }
                }
                CHECK(water);
                for (std::size_t j = i + 1; j < m->starts.size(); ++j) {
                    CHECK(distance(s.x, s.z, m->starts[j].x, m->starts[j].z) >= 100.0);
                }
            }
        }
    }

    TEST_CASE("settings round-trip and bad ones are rejected") {
        MapSettings s = settings(99, MapSize::Large, 6);
        s.water = Amount::High;
        s.relief = Relief::Gentle;
        s.map_type = map_type("single");
        s.biome = biome("giants");
        BinaryWriter w;
        s.write(w);
        BinaryReader r(w.bytes());
        MapSettings back;
        REQUIRE(MapSettings::read(r, back));
        CHECK(back == s);
        std::vector<std::uint8_t> bad = w.bytes();
        bad[8] = 9;  // Size out of range.
        BinaryReader br(bad);
        CHECK_FALSE(MapSettings::read(br, back));
        bad = w.bytes();
        bad[13] = 13;  // Too many players.
        BinaryReader bp(bad);
        CHECK_FALSE(MapSettings::read(bp, back));
        bad = w.bytes();
        bad[14] = 255;  // Map type out of range.
        BinaryReader bt(bad);
        CHECK_FALSE(MapSettings::read(bt, back));
        for (const std::uint8_t islands : {std::uint8_t{0}, std::uint8_t{kMaxIslandsPerTown + 1}}) {
            bad = w.bytes();
            bad[17] = islands;
            BinaryReader bi(bad);
            CHECK_FALSE(MapSettings::read(bi, back));
        }
    }

    TEST_CASE("map sizes and separate worlds fit in the biggest size") {
        CHECK(map_cells(MapSize::Giant) == 8192);
        CHECK(map_cells(MapSize::Colossal) == 16384);
        MapSettings s = settings(1, MapSize::Colossal, 4);
        CHECK(world_cells(s) == 16384);
        s.separate = true;
        CHECK(region_map_size(s) == MapSize::Giant);
        CHECK(world_cells(s) == 16384);
        s.players = 12;
        CHECK(region_map_size(s) == MapSize::Huge);
        s.size = MapSize::Huge;
        s.players = 2;
        CHECK(region_map_size(s) == MapSize::Huge);
        for (std::uint8_t size = 0; size < static_cast<std::uint8_t>(MapSize::Count); ++size) {
            for (std::uint8_t players = 1; players <= 12; ++players) {
                s.size = static_cast<MapSize>(size);
                s.players = players;
                CHECK(world_cells(s) <= map_cells(kMaxWorldSize));
            }
        }
    }

    TEST_CASE("island layouts: archipelagos, apart and inside the map") {
        for (const auto& [cells, towns, per_town] : {std::tuple{1024, 1, 1}, std::tuple{1024, 2, 3}, std::tuple{2048, 4, 4},
                                                     std::tuple{4096, 12, 8}, std::tuple{512, 1, 1}}) {
            const std::vector<worldgen::Island> a = worldgen::island_layout(7, cells, towns, per_town);
            CHECK(a == worldgen::island_layout(7, cells, towns, per_town));
            REQUIRE(a.size() == static_cast<std::size_t>(towns * per_town));
            for (std::size_t i = 0; i < a.size(); ++i) {
                const bool main = static_cast<std::int32_t>(i) < towns;
                CHECK(a[i].x - a[i].radius >= 16);
                CHECK(a[i].z - a[i].radius >= 16);
                CHECK(a[i].x + a[i].radius <= cells - 16);
                CHECK(a[i].z + a[i].radius <= cells - 16);
                CHECK(a[i].town == (main ? i : a[i].town));
                // The discs never overlap; channels keep the shapes apart.
                for (std::size_t j = 0; j < i; ++j) {
                    const double d = std::hypot(a[i].x - a[j].x, a[i].z - a[j].z);
                    CHECK(d >= a[i].radius + a[j].radius);
                }
                if (!main) {
                    // Smaller than its main island, and nearer to it than to any other.
                    const worldgen::Island& home = a[a[i].town];
                    CHECK(a[i].radius < home.radius);
                    const double own = std::hypot(a[i].x - home.x, a[i].z - home.z);
                    for (std::int32_t t = 0; t < towns; ++t) {
                        if (t != a[i].town) {
                            CHECK(own < std::hypot(a[i].x - a[static_cast<std::size_t>(t)].x, a[i].z - a[static_cast<std::size_t>(t)].z));
                        }
                    }
                }
            }
        }
    }

    TEST_CASE("islands per town fit the map size") {
        for (std::uint8_t size = 0; size < static_cast<std::uint8_t>(MapSize::Count); ++size) {
            std::int32_t last = kMaxIslandsPerTown;
            for (std::int32_t towns = 1; towns <= 12; ++towns) {
                const std::int32_t k = worldgen::max_islands_per_town(static_cast<MapSize>(size), towns);
                CHECK(k >= 1);
                CHECK(k <= kMaxIslandsPerTown);
                CHECK(k <= last);  // More towns, fewer islands each.
                last = k;
            }
        }
        CHECK(worldgen::max_islands_per_town(MapSize::Huge, 12) == kMaxIslandsPerTown);
        CHECK(worldgen::max_islands_per_town(MapSize::Small, 12) == 1);
    }

    TEST_CASE("an island map has towns times islands per town islands, one town on each home island") {
        for (const auto& [size, towns, per_town] : {std::tuple{MapSize::Medium, 2, 3}, std::tuple{MapSize::Small, 1, 1},
                                                    std::tuple{MapSize::Large, 4, 2}}) {
            MapSettings s = settings(404, size, static_cast<std::uint8_t>(towns));
            s.map_type = map_type("islands");
            s.islands = static_cast<std::uint8_t>(per_town);
            REQUIRE(per_town <= worldgen::max_islands_per_town(size, towns));
            const auto m = gen(s);
            REQUIRE(m.has_value());
            CHECK(m->checksum() == gen(s)->checksum());
            std::int32_t count = 0;
            const std::vector<std::int32_t> id = island_ids(*m, count);
            CHECK(count == towns * per_town);
            REQUIRE(m->starts.size() == static_cast<std::size_t>(towns));
            std::vector<std::int32_t> homes;
            for (const StartPosition& st : m->starts) {
                const std::int32_t cx = st.x.floor_int();
                const std::int32_t cz = st.z.floor_int();
                CHECK_FALSE(m->water_at(cx, cz));
                const std::int32_t home = id[static_cast<std::size_t>(cz) * static_cast<std::size_t>(m->size) +
                                             static_cast<std::size_t>(cx)];
                CHECK(home >= 0);
                CHECK(std::find(homes.begin(), homes.end(), home) == homes.end());
                homes.push_back(home);
            }
            // The sea surrounds the map.
            CHECK(m->water_at(0, 0));
            CHECK(m->water_at(m->size - 1, m->size / 2));
        }
    }

    TEST_CASE("islands are irregular, the main ones bigger") {
        for (const std::uint64_t seed : {21u, 22u, 23u}) {
            MapSettings s = settings(seed, MapSize::Medium, 2);
            s.map_type = map_type("islands");
            s.islands = 3;
            const auto m = gen(s);
            REQUIRE(m.has_value());
            std::int32_t count = 0;
            const std::vector<std::int32_t> id = island_ids(*m, count);
            REQUIRE(count == 6);
            // Area and shoreline (cell edges between land and sea) of each.
            std::vector<double> area(static_cast<std::size_t>(count), 0.0);
            std::vector<double> shore(static_cast<std::size_t>(count), 0.0);
            const std::int32_t n = m->size;
            for (std::int32_t z = 0; z < n; ++z) {
                for (std::int32_t x = 0; x < n; ++x) {
                    const std::int32_t k = id[static_cast<std::size_t>(z * n + x)];
                    if (k < 0) {
                        continue;
                    }
                    area[static_cast<std::size_t>(k)] += 1.0;
                    for (const auto& [nx, nz] : {std::pair{x + 1, z}, std::pair{x - 1, z}, std::pair{x, z + 1}, std::pair{x, z - 1}}) {
                        if (nx < 0 || nz < 0 || nx >= n || nz >= n || id[static_cast<std::size_t>(nz * n + nx)] != k) {
                            shore[static_cast<std::size_t>(k)] += 1.0;
                        }
                    }
                }
            }
            // A disc drawn in cells scores about 0.6 (its staircase shore is
            // 4/pi longer); bays and peninsulas bring it well down.
            double mean = 0.0;
            for (std::int32_t k = 0; k < count; ++k) {
                const double compact = 4.0 * 3.14159265 * area[static_cast<std::size_t>(k)] /
                                       (shore[static_cast<std::size_t>(k)] * shore[static_cast<std::size_t>(k)]);
                CHECK(compact < 0.55);
                mean += compact / count;
            }
            MESSAGE("seed " << seed << ": mean compactness " << mean);
            CHECK(mean < 0.4);
            // Each town starts on the biggest island of its archipelago.
            for (const StartPosition& st : m->starts) {
                const std::int32_t home = id[static_cast<std::size_t>(st.z.floor_int() * n + st.x.floor_int())];
                REQUIRE(home >= 0);
                const double biggest = *std::max_element(area.begin(), area.end());
                CHECK(area[static_cast<std::size_t>(home)] >= biggest * 0.35);
            }
        }
    }

    TEST_CASE("generation can be cancelled") {
        int calls = 0;
        const auto m = gen(settings(5, MapSize::Small), [&](GenStage stage, int) {
            ++calls;
            return stage != GenStage::Rivers;
        });
        CHECK_FALSE(m.has_value());
        CHECK(calls > 0);
    }

    TEST_CASE("heights interpolate between vertices") {
        const auto m = gen(settings(8, MapSize::Small));
        REQUIRE(m.has_value());
        const Fixed at_vertex = m->height_at(Fixed::from_int(100), Fixed::from_int(200));
        CHECK(at_vertex == Fixed::from_ratio(m->height_cm(100, 200), 100));
        const Fixed mid = m->height_at(Fixed::from_ratio(201, 2), Fixed::from_int(200));
        const Fixed lo = std::min(m->height_at(Fixed::from_int(100), Fixed::from_int(200)),
                                  m->height_at(Fixed::from_int(101), Fixed::from_int(200)));
        const Fixed hi = std::max(m->height_at(Fixed::from_int(100), Fixed::from_int(200)),
                                  m->height_at(Fixed::from_int(101), Fixed::from_int(200)));
        CHECK(mid >= lo);
        CHECK(mid <= hi);
    }
}

TEST_SUITE("flora") {
    TEST_CASE("species sizes and fitting") {
        const Flora& f = content().flora;
        CHECK(f.species.size() == 21);
        CHECK(f.biomes.size() == 6);
        CHECK(f.map_types.size() == 7);
        CHECK(f.species_has_size(species("sequoia"), TreeSize::Huge));
        CHECK_FALSE(f.species_has_size(species("lemon"), TreeSize::Medium));
        CHECK(f.fit_size(species("lemon"), TreeSize::Huge) == TreeSize::Small);
        CHECK(f.fit_size(species("mountain_ash"), TreeSize::Small) == TreeSize::Large);
        CHECK(f.fit_size(species("toog"), TreeSize::Small) == TreeSize::Medium);
        for (const SpeciesDef& sp : f.species) {
            CHECK(sp.sizes != 0);
        }
        // Every biome's species exist, and every map type's biomes too.
        for (const BiomeDef& b : f.biomes) {
            for (const Weighted& w : b.species) {
                CHECK(w.id < f.species.size());
            }
        }
        for (const MapTypeDef& t : f.map_types) {
            for (const Weighted& w : t.biomes) {
                CHECK(w.id < f.biomes.size());
            }
        }
        const Weighted items[] = {{3, 1}, {7, 3}};
        CHECK(pick_weighted(items, 0) == 3);
        CHECK(pick_weighted(items, 0x3FFF) == 3);
        CHECK(pick_weighted(items, 0x4000) == 7);
        CHECK(pick_weighted(items, 0xFFFF) == 7);
    }

    TEST_CASE("trees have allowed sizes, heights in range and room") {
        const auto m = gen(settings(21, MapSize::Medium, 2));
        REQUIRE(m.has_value());
        CHECK(m->generator_version == worldgen::kGeneratorVersion);
        CHECK(m->biome.size() == m->terrain.size());
        std::vector<const MapFeature*> trees;
        std::size_t per_size[kTreeSizes] = {};
        for (const MapFeature& f : m->features) {
            if (f.type != FeatureType::Tree) {
                continue;
            }
            REQUIRE(f.species < content().flora.species.size());
            REQUIRE(f.size < kTreeSizes);
            const auto size = static_cast<TreeSize>(f.size);
            CHECK(content().flora.species_has_size(f.species, size));
            const std::int32_t h = MapData::tree_height_cm(f);
            CHECK(h >= size_info(size).min_cm - 1);
            CHECK(h <= size_info(size).max_cm + 1);
            ++per_size[f.size];
            trees.push_back(&f);
        }
        for (const std::size_t n : per_size) {
            CHECK(n > 0);
        }
        // Neighbors keep apart by their sizes (half spacings, less a cell).
        std::size_t close = 0;
        for (std::size_t i = 0; i < trees.size(); i += 7) {
            for (std::size_t j = 0; j < trees.size(); ++j) {
                if (i == j) {
                    continue;
                }
                const double d = distance(trees[i]->x, trees[i]->z, trees[j]->x, trees[j]->z);
                const double need = (size_info(static_cast<TreeSize>(trees[i]->size)).spacing_m / 2 +
                                     size_info(static_cast<TreeSize>(trees[j]->size)).spacing_m / 2) - 2.0;
                close += d < need;
            }
        }
        CHECK(close == 0);
    }

    TEST_CASE("map types change the forests") {
        MapSettings young = settings(33, MapSize::Small);
        young.map_type = map_type("young");
        MapSettings giants = young;
        giants.map_type = map_type("giants");
        MapSettings single = young;
        single.map_type = map_type("single");
        single.biome = biome("orchard");
        const auto a = gen(young);
        const auto b = gen(giants);
        const auto c = gen(single);
        REQUIRE(a.has_value());
        REQUIRE(b.has_value());
        REQUIRE(c.has_value());
        CHECK(a->checksum() != b->checksum());
        std::size_t young_big = 0;
        std::size_t giant_big = 0;
        for (const MapFeature& f : a->features) {
            young_big += f.type == FeatureType::Tree && f.size >= static_cast<std::uint8_t>(TreeSize::Large);
        }
        for (const MapFeature& f : b->features) {
            giant_big += f.type == FeatureType::Tree && f.size >= static_cast<std::uint8_t>(TreeSize::Large);
        }
        CHECK(giant_big > 100);
        // Young forests only grow big trees of species that cannot be small.
        CHECK(young_big * 20 < giant_big);
        std::size_t other_biome = 0;
        for (const std::uint8_t cell : c->biome) {
            other_biome += cell != biome("orchard");
        }
        CHECK(other_biome == 0);
        for (const MapFeature& f : c->features) {
            if (f.type == FeatureType::Tree) {
                const std::uint8_t sp = f.species;
                const bool orchard_species = sp == species("apple") || sp == species("pear") || sp == species("peach") ||
                                             sp == species("orange") || sp == species("lemon") ||
                                             sp == species("avocado") || sp == species("cherry");
                CHECK(orchard_species);
            }
        }
    }
}

TEST_SUITE("worldgen_perf") {
    TEST_CASE("a huge map generates in under 30 seconds (release)") {
#ifdef NDEBUG
        const auto t0 = std::chrono::steady_clock::now();
        const auto m = gen(settings(2026, MapSize::Huge, 8));
        const double seconds = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
        REQUIRE(m.has_value());
        MESSAGE("huge map: " << seconds << " s, " << m->features.size() << " features");
        CHECK(seconds < 30.0);
        CHECK(m->starts.size() == 8);
#else
        MESSAGE("skipped: timing is only meaningful in release builds");
#endif
    }
}
