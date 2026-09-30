#include <doctest.h>

#include <algorithm>
#include <cmath>
#include <map>
#include <memory>
#include <optional>

#include "game/terrain_names.h"
#include "sim/game.h"
#include "sim/worldgen.h"
#include "sim/worldgen_hier.h"
#include "test_util.h"

using namespace sc;
using sim::LandformKind;

namespace {

sim::MapSettings hier_settings(std::uint64_t seed, sim::MapSize size) {
    sim::MapSettings s;
    s.seed = seed;
    s.size = size;
    s.players = 2;
    s.sea = sim::Sea::None;
    s.generator = sim::MapGenerator::Hierarchical;
    return s;
}

sim::MapData generate(const sim::MapSettings& s) {
    std::optional<sim::MapData> m = sim::generate_map(s, sc::test::core_content());
    REQUIRE(m.has_value());
    return std::move(*m);
}

bool is_region(LandformKind k) {
    return k == LandformKind::Plain || k == LandformKind::Hills || k == LandformKind::Mountains ||
           k == LandformKind::Plateau || k == LandformKind::Basin;
}

// How many squares of the map each region kind covers.
std::map<LandformKind, std::int64_t> region_squares(const sim::MapData& m) {
    std::map<LandformKind, std::int64_t> out;
    for (const std::uint16_t owner : m.region_owner) {
        ++out[m.landforms[owner - 1u].kind];
    }
    return out;
}

std::shared_ptr<const sim::Content> shared_content() {
    return std::shared_ptr<const sim::Content>(std::shared_ptr<const sim::Content>{}, &sc::test::core_content());
}

}  // namespace

TEST_SUITE("worldgen_hier") {
    TEST_CASE("the generator is a setting of the map, kept in saves") {
        sim::MapSettings s = hier_settings(5, sim::MapSize::Small);
        sim::BinaryWriter w;
        s.write(w);
        sim::MapSettings back;
        sim::BinaryReader r(w.bytes());
        REQUIRE(sim::MapSettings::read(r, back));
        CHECK(back == s);
        // An unknown generator is refused.
        std::vector<std::uint8_t> bytes = w.bytes();
        bytes.back() = static_cast<std::uint8_t>(sim::MapGenerator::Count);
        sim::BinaryReader bad(bytes);
        CHECK_FALSE(sim::MapSettings::read(bad, back));
        // A classic map is named as before there was a choice.
        sim::MapSettings classic = s;
        classic.generator = sim::MapGenerator::Classic;
        sim::BinaryWriter identity;
        classic.write_identity(identity);
        sim::BinaryWriter full;
        classic.write(full);
        CHECK(identity.bytes().size() + 1 == full.bytes().size());
    }

    TEST_CASE("every square of a hierarchical map is in one region, the same each time") {
        const sim::MapData m = generate(hier_settings(11, sim::MapSize::Medium));
        CHECK(m.generator_version == sim::hier::kVersion);
        const auto side = static_cast<std::size_t>(m.owner_side());
        REQUIRE(m.region_owner.size() == side * side);
        REQUIRE(m.structure_owner.size() == side * side);
        for (const std::uint16_t owner : m.region_owner) {
            REQUIRE(owner >= 1);
            REQUIRE(owner <= m.landforms.size());
            CHECK(is_region(m.landforms[owner - 1u].kind));
        }
        // Several kinds of region, most of it plain.
        const auto squares = region_squares(m);
        CHECK(squares.size() >= 3);
        CHECK(squares.at(LandformKind::Plain) * 3 >= static_cast<std::int64_t>(m.region_owner.size()));
        // The same settings, the same map.
        const sim::MapData again = generate(hier_settings(11, sim::MapSize::Medium));
        CHECK(again.checksum() == m.checksum());
        CHECK(again.region_owner == m.region_owner);
        // Another generator, another map.
        sim::MapSettings classic = hier_settings(11, sim::MapSize::Medium);
        classic.generator = sim::MapGenerator::Classic;
        CHECK(generate(classic).checksum() != m.checksum());
    }

    TEST_CASE("the options change how many regions are not plains") {
        std::int64_t few = 0;
        std::int64_t many = 0;
        std::int64_t mountains_low = 0;
        std::int64_t mountains_high = 0;
        for (std::uint64_t seed = 20; seed < 24; ++seed) {
            sim::MapSettings s = hier_settings(seed, sim::MapSize::Medium);
            s.landforms = sim::Amount::Low;
            s.relief = sim::Relief::Low;
            auto low = region_squares(generate(s));
            for (const auto& [k, n] : low) {
                few += k == LandformKind::Plain ? 0 : n;
            }
            mountains_low += low[LandformKind::Mountains];
            s.landforms = sim::Amount::High;
            s.relief = sim::Relief::Mountainous;
            auto high = region_squares(generate(s));
            for (const auto& [k, n] : high) {
                many += k == LandformKind::Plain ? 0 : n;
            }
            mountains_high += high[LandformKind::Mountains];
        }
        CHECK(many > few);
        CHECK(mountains_high > mountains_low);
    }

    TEST_CASE("plateaus stand above the land around them on a cliff") {
        int measured = 0;
        int good = 0;
        for (std::uint64_t seed = 30; seed < 36; ++seed) {
            const sim::MapData m = generate(hier_settings(seed, sim::MapSize::Medium));
            for (std::size_t i = 0; i < m.landforms.size(); ++i) {
                const sim::Landform& l = m.landforms[i];
                if (l.kind != LandformKind::Plateau) {
                    continue;
                }
                // Its squares against the squares of other regions next to it.
                const std::int32_t side = m.owner_side();
                std::int64_t top = 0, top_n = 0, low = 0, low_n = 0;
                for (std::int32_t bz = 1; bz + 1 < side; ++bz) {
                    for (std::int32_t bx = 1; bx + 1 < side; ++bx) {
                        const auto at = [&](std::int32_t x, std::int32_t z) { return m.region_owner[static_cast<std::size_t>(z * side + x)]; };
                        const std::int32_t h = m.height_cm(bx * sim::kOwnerBlock + 4, bz * sim::kOwnerBlock + 4);
                        const bool mine = at(bx, bz) == i + 1;
                        // Squares well inside, and squares just outside.
                        bool inside = mine;
                        bool beside = false;
                        for (int dz = -3; dz <= 3; ++dz) {
                            for (int dx = -3; dx <= 3; ++dx) {
                                const std::int32_t x = std::clamp(bx + dx, 0, side - 1);
                                const std::int32_t z = std::clamp(bz + dz, 0, side - 1);
                                inside = inside && at(x, z) == i + 1;
                                beside = beside || (!mine && at(x, z) == i + 1);
                            }
                        }
                        if (inside) {
                            top += h;
                            ++top_n;
                        } else if (beside && m.landforms[at(bx, bz) - 1u].kind != LandformKind::Mountains) {
                            low += h;
                            ++low_n;
                        }
                    }
                }
                if (top_n >= 10 && low_n >= 10) {
                    ++measured;
                    good += top / top_n >= low / low_n + 1500 ? 1 : 0;
                }
            }
        }
        MESSAGE(good << " of " << measured << " plateaus stand above their surroundings");
        CHECK(measured > 0);
        CHECK(good * 10 >= measured * 8);
    }

    TEST_CASE("the names under the cursor are the map's own") {
        const sim::MapData m = generate(hier_settings(12, sim::MapSize::Small));
        TerrainNames names;
        for (std::int32_t z = 3; z < m.size; z += 37) {
            for (std::int32_t x = 5; x < m.size; x += 41) {
                const CellDescription d = names.describe(m, x, z);
                REQUIRE(d.region.has_value());
                CHECK(*d.region == m.landforms[m.owner_at(m.region_owner, x, z) - 1u].kind);
            }
        }
    }

    TEST_CASE("a hierarchical game saves and loads its regions") {
        const sim::MapData map = generate(hier_settings(13, sim::MapSize::Small));
        sim::Game g(shared_content(), map, 1, 21);
        sim::BinaryWriter w;
        g.save(w);
        sim::Game back(shared_content(), sim::MapData{}, 0, 0);
        sim::BinaryReader r(w.bytes());
        REQUIRE(back.load(r, shared_content()));
        CHECK(back.map().settings.generator == sim::MapGenerator::Hierarchical);
        CHECK(back.map().region_owner == map.region_owner);
        CHECK(back.map().structure_owner == map.structure_owner);
        CHECK(back.map().checksum() == map.checksum());
    }

    TEST_CASE("separate hierarchical maps keep each region's owners") {
        sim::MapSettings s = hier_settings(14, sim::MapSize::Small);
        s.separate = true;
        const sim::MapData world = generate(s);
        REQUIRE(world.region_owner.size() == static_cast<std::size_t>(world.owner_side()) * world.owner_side());
        const std::int32_t t = world.region_size();
        // Both players' squares name a region inside their own map.
        for (const std::int32_t player : {0, 1}) {
            const std::int32_t cx = (player % 2) * t + t / 2;
            const std::int32_t cz = t / 2;
            const std::uint16_t owner = world.owner_at(world.region_owner, cx, cz);
            REQUIRE(owner >= 1);
            const auto& p = world.landforms[owner - 1u].points[0];
            CHECK(p[0] >= player * t);
            CHECK(p[0] <= player * t + t);
        }
    }
}

namespace {

// The ground (cm) at a point along a structure's line: `t` of the way
// (0..1) and `side` meters to its left; -1 off the map.
std::int32_t ground_beside(const sim::MapData& m, const sim::Landform& l, double t, double side) {
    const double pos = t * static_cast<double>(l.points.size() - 1);
    const auto k = std::min(static_cast<std::size_t>(pos), l.points.size() - 2);
    const double f = pos - static_cast<double>(k);
    const double ax = l.points[k][0], az = l.points[k][1];
    const double bx = l.points[k + 1][0], bz = l.points[k + 1][1];
    const double len = std::max(1.0, std::hypot(bx - ax, bz - az));
    const double x = ax + (bx - ax) * f - (bz - az) / len * side;
    const double z = az + (bz - az) * f + (bx - ax) / len * side;
    if (x < 1 || z < 1 || x >= m.size - 1 || z >= m.size - 1) {
        return -1;
    }
    return m.height_cm(static_cast<std::int32_t>(x), static_cast<std::int32_t>(z));
}

}  // namespace

// The slowest ones, each in a suite of its own so debug builds fit the
// time limit (as in D-3110).
TEST_SUITE("worldgen_hier_structures") {
    TEST_CASE("structures: canyons below both sides, crests above their flanks, a ramp up each plateau") {
        int canyon_samples = 0, canyon_good = 0;
        int crest_samples = 0, crest_good = 0;
        int plateaus = 0, ramps = 0;
        for (std::uint64_t seed = 40; seed < 46; ++seed) {
            sim::MapSettings s = hier_settings(seed, sim::MapSize::Large);
            s.landforms = sim::Amount::High;
            s.relief = seed % 2 == 0 ? sim::Relief::Mountainous : sim::Relief::Gentle;
            const sim::MapData m = generate(s);
            for (const sim::Landform& l : m.landforms) {
                if (l.kind == LandformKind::Plateau) {
                    ++plateaus;
                } else if (l.kind == LandformKind::Ramp) {
                    ++ramps;
                } else if (l.kind == LandformKind::Canyon || l.kind == LandformKind::Crest) {
                    const bool canyon = l.kind == LandformKind::Canyon;
                    const double half = l.width / 2.0;
                    for (int k = 2; k < 18; ++k) {
                        const double t = k / 20.0;
                        const double off = canyon ? half * 1.8 : half * 1.6;
                        const std::int32_t mid = ground_beside(m, l, t, 0.0);
                        const std::int32_t left = ground_beside(m, l, t, off);
                        const std::int32_t right = ground_beside(m, l, t, -off);
                        if (mid < 0 || left < 0 || right < 0) {
                            continue;
                        }
                        if (canyon) {
                            // Inside its plateau only (past the rim it runs into the plain).
                            const auto owner = m.owner_at(m.region_owner, static_cast<std::int32_t>(l.points[0][0]),
                                                          static_cast<std::int32_t>(l.points[0][1]));
                            const std::int32_t cx = static_cast<std::int32_t>(l.points[0][0] + (l.points.back()[0] - l.points[0][0]) * t);
                            const std::int32_t cz = static_cast<std::int32_t>(l.points[0][1] + (l.points.back()[1] - l.points[0][1]) * t);
                            // Well inside it: both sides and the middle on the plateau's own squares.
                            const auto on = [&](double side) {
                                const double ax = l.points[0][0], az = l.points[0][1];
                                const double bx = l.points.back()[0], bz = l.points.back()[1];
                                const double len = std::max(1.0, std::hypot(bx - ax, bz - az));
                                const auto x = static_cast<std::int32_t>(cx - (bz - az) / len * side);
                                const auto z = static_cast<std::int32_t>(cz + (bx - ax) / len * side);
                                return m.owner_at(m.region_owner, x, z) == owner;
                            };
                            if (!on(0.0) || !on(off * 1.5) || !on(-off * 1.5)) {
                                continue;
                            }
                            ++canyon_samples;
                            canyon_good += mid + 500 <= std::min(left, right) ? 1 : 0;
                        } else if (k >= 5 && k <= 15) {
                            ++crest_samples;
                            crest_good += mid >= std::max(left, right) + 500 ? 1 : 0;
                        }
                    }
                }
            }
            // Each square has one structure at most, and it names a structure.
            for (const std::uint16_t owner : m.structure_owner) {
                if (owner != 0) {
                    REQUIRE(owner <= m.landforms.size());
                    CHECK_FALSE(is_region(m.landforms[owner - 1u].kind));
                }
            }
        }
        MESSAGE("canyons " << canyon_good << "/" << canyon_samples << ", crests " << crest_good << "/" << crest_samples
                           << ", ramps " << ramps << " for " << plateaus << " plateaus");
        CHECK(canyon_samples > 20);
        CHECK(canyon_good * 10 >= canyon_samples * 8);
        CHECK(crest_samples > 20);
        CHECK(crest_good * 10 >= crest_samples * 7);
        CHECK(ramps * 10 >= plateaus * 8);
    }

}

TEST_SUITE("worldgen_hier_compare") {
    TEST_CASE("less canyon than the classic generator with the same options") {
        // Meters of canyon: the classic ones cross the whole map.
        const auto meters = [](const sim::MapData& m, int& count) {
            double total = 0.0;
            for (const sim::Landform& l : m.landforms) {
                if (l.kind != LandformKind::Canyon) {
                    continue;
                }
                ++count;
                for (std::size_t k = 1; k < l.points.size(); ++k) {
                    total += std::hypot(l.points[k][0] - l.points[k - 1][0], l.points[k][1] - l.points[k - 1][1]);
                }
            }
            return total;
        };
        int hier_count = 0;
        int classic_count = 0;
        double hier = 0.0;
        double classic = 0.0;
        for (std::uint64_t seed = 50; seed < 54; ++seed) {
            sim::MapSettings s = hier_settings(seed, sim::MapSize::Large);
            s.landforms = sim::Amount::High;
            hier += meters(generate(s), hier_count);
            s.generator = sim::MapGenerator::Classic;
            classic += meters(generate(s), classic_count);
        }
        MESSAGE("canyons: " << hier_count << " hierarchical (" << hier << " m), " << classic_count << " classic (" << classic << " m)");
        CHECK(hier_count > 0);
        CHECK(hier_count <= classic_count);
        CHECK(hier * 2 < classic);
    }
}


TEST_SUITE("worldgen_hier_water") {
    TEST_CASE("a coast: sea along a side, never next to a plateau, towns on land") {
        for (std::uint64_t seed = 60; seed < 64; ++seed) {
            sim::MapSettings s = hier_settings(seed, sim::MapSize::Medium);
            s.sea = sim::Sea::Always;
            const sim::MapData m = generate(s);
            REQUIRE(m.sea_levels.size() == 1);
            CHECK(m.sea_levels[0] != 0);
            // The sea reaches the border along at least half a side.
            std::int32_t wet = 0;
            for (std::int32_t i = 0; i < m.size; ++i) {
                wet += (m.water_at(i, 0) ? 1 : 0) + (m.water_at(i, m.size - 1) ? 1 : 0) + (m.water_at(0, i) ? 1 : 0) +
                       (m.water_at(m.size - 1, i) ? 1 : 0);
            }
            CHECK(wet >= m.size / 2);
            // Most of the map is still land.
            std::size_t land = 0;
            for (const std::uint16_t w : m.water) {
                land += w == 0 ? 1 : 0;
            }
            CHECK(land * 2 >= m.water.size());
            // No plateau square touches a sea square.
            const std::int32_t side = m.owner_side();
            const auto kind = [&](std::int32_t x, std::int32_t z) { return m.landforms[m.region_owner[static_cast<std::size_t>(z * side + x)] - 1u].kind; };
            for (std::int32_t z = 0; z + 1 < side; ++z) {
                for (std::int32_t x = 0; x + 1 < side; ++x) {
                    for (const auto [a, b] : {std::pair{kind(x, z), kind(x + 1, z)}, std::pair{kind(x, z), kind(x, z + 1)}}) {
                        CHECK_FALSE(((a == LandformKind::Plateau && b == LandformKind::Sea) || (a == LandformKind::Sea && b == LandformKind::Plateau)));
                    }
                }
            }
            for (const sim::StartPosition& st : m.starts) {
                CHECK_FALSE(m.water_at(st.x.floor_int(), st.z.floor_int()));
            }
        }
    }

    TEST_CASE("islands: as many as asked, each town on its own") {
        sim::MapSettings s = hier_settings(70, sim::MapSize::Medium);
        s.players = 3;
        s.islands = 2;
        for (std::size_t t = 0; t < sc::test::core_content().flora.map_types.size(); ++t) {
            if (sc::test::core_content().flora.map_types[t].islands) {
                s.map_type = static_cast<std::uint8_t>(t);
            }
        }
        const sim::MapData m = generate(s);
        const std::int32_t wanted = 3 * std::min<std::int32_t>(2, sim::worldgen::max_islands_per_town(s.size, 3));
        std::vector<const sim::Landform*> islands;
        for (const sim::Landform& l : m.landforms) {
            if (l.kind == LandformKind::Island) {
                islands.push_back(&l);
            }
        }
        CHECK(static_cast<std::int32_t>(islands.size()) == wanted);
        // The middle of each island is land; the map's corners are sea.
        for (const sim::Landform* l : islands) {
            CHECK_FALSE(m.water_at(l->points[0][0], l->points[0][1]));
        }
        CHECK(m.water_at(2, 2));
        REQUIRE(m.starts.size() == 3);
        for (std::size_t p = 0; p < 3; ++p) {
            const std::int32_t x = m.starts[p].x.floor_int();
            const std::int32_t z = m.starts[p].z.floor_int();
            CHECK_FALSE(m.water_at(x, z));
            // On the island it was given (main islands come first).
            const double d = std::hypot(x - islands[p]->points[0][0], z - islands[p]->points[0][1]);
            CHECK(d <= islands[p]->width);
        }
    }

    TEST_CASE("most canyons carry a river, and river mouths are estuaries") {
        int canyons = 0;
        int wet = 0;
        int estuaries = 0;
        for (std::uint64_t seed = 80; seed < 84; ++seed) {
            sim::MapSettings s = hier_settings(seed, sim::MapSize::Large);
            s.landforms = sim::Amount::High;
            s.sea = sim::Sea::Always;
            const sim::MapData m = generate(s);
            for (const sim::Landform& l : m.landforms) {
                if (l.kind != LandformKind::Canyon) {
                    continue;
                }
                ++canyons;
                int water = 0;
                for (int k = 0; k <= 40; ++k) {
                    const double t = k / 40.0;
                    const auto x = static_cast<std::int32_t>(l.points[0][0] + (l.points.back()[0] - l.points[0][0]) * t);
                    const auto z = static_cast<std::int32_t>(l.points[0][1] + (l.points.back()[1] - l.points[0][1]) * t);
                    for (int dz = -12; dz <= 12; dz += 4) {
                        for (int dx = -12; dx <= 12; dx += 4) {
                            water += m.water_at(x + dx, z + dz) ? 1 : 0;
                        }
                    }
                }
                wet += water >= 20 ? 1 : 0;
            }
            // Water at the sea's level on a river's course is an estuary.
            TerrainNames names;
            for (const sim::Landform& l : m.landforms) {
                if (l.kind != LandformKind::River) {
                    continue;
                }
                const auto& end = l.points.back();
                const CellDescription d = names.describe(m, std::min(end[0], m.size - 1), std::min(end[1], m.size - 1));
                estuaries += d.water == WaterKind::Estuary ? 1 : 0;
                CHECK(d.water != WaterKind::Sea);
            }
        }
        MESSAGE(wet << " of " << canyons << " canyons with water; " << estuaries << " estuaries");
        CHECK(canyons > 0);
        CHECK(wet * 2 >= canyons);
    }
}

TEST_SUITE("worldgen_hier_life") {
    TEST_CASE("towns start fair, on plains or hills, with water, room and resources") {
        for (const std::uint8_t players : {std::uint8_t{1}, std::uint8_t{4}, std::uint8_t{8}}) {
            sim::MapSettings s = hier_settings(4242, sim::MapSize::Medium);
            s.players = players;
            const sim::MapData m = generate(s);
            REQUIRE(m.starts.size() == players);
            int on_good_ground = 0;
            for (std::size_t i = 0; i < m.starts.size(); ++i) {
                const sim::StartPosition& st = m.starts[i];
                const std::int32_t x = st.x.floor_int();
                const std::int32_t z = st.z.floor_int();
                const sim::Terrain t = m.terrain_at(x, z);
                CHECK(t != sim::Terrain::Water);
                CHECK(t != sim::Terrain::Rock);
                const LandformKind region = m.landforms[m.owner_at(m.region_owner, x, z) - 1u].kind;
                on_good_ground += region == LandformKind::Plain || region == LandformKind::Hills ? 1 : 0;
                int stones = 0, berries = 0, trees = 0;
                for (const sim::MapFeature& f : m.features) {
                    const double dx = (f.x - st.x).raw() / 65536.0;
                    const double dz = (f.z - st.z).raw() / 65536.0;
                    const double d = std::hypot(dx, dz);
                    CHECK(d > sim::worldgen::kStartClearRadius);
                    if (d <= sim::worldgen::kStartResourceRadius) {
                        stones += f.type == sim::FeatureType::Stone;
                        berries += f.type == sim::FeatureType::BerryBush;
                        trees += f.type == sim::FeatureType::Tree;
                    }
                }
                CHECK(stones >= sim::worldgen::kStartMinStones);
                CHECK(berries >= sim::worldgen::kStartMinBerries);
                CHECK(trees >= sim::worldgen::kStartMinTrees);
                bool water = false;
                const std::int32_t r = sim::worldgen::kStartMaxWaterDistance;
                for (std::int32_t dz = -r; dz <= r && !water; dz += 2) {
                    for (std::int32_t dx = -r; dx <= r && !water; dx += 2) {
                        water = m.water_at(x + dx, z + dz);
                    }
                }
                CHECK(water);
            }
            CHECK(on_good_ground == players);
        }
    }

    TEST_CASE("biomes follow the regions, with pinewoods on the mountains") {
        sim::MapSettings s = hier_settings(91, sim::MapSize::Large);
        s.relief = sim::Relief::Mountainous;
        std::int32_t pine = -1;
        for (std::size_t t = 0; t < sc::test::core_content().flora.map_types.size(); ++t) {
            if (sc::test::core_content().flora.map_types[t].id == "core:varied") {
                s.map_type = static_cast<std::uint8_t>(t);
            }
        }
        pine = sc::test::core_content().flora.find_biome("core:pinewood");
        REQUIRE(pine >= 0);
        const sim::MapData m = generate(s);
        // Per region, how many squares have its most common biome.
        std::map<std::uint16_t, std::map<std::uint8_t, int>> per_region;
        const std::int32_t side = m.owner_side();
        for (std::int32_t bz = 0; bz < side; ++bz) {
            for (std::int32_t bx = 0; bx < side; ++bx) {
                const std::int32_t x = bx * sim::kOwnerBlock + 4, z = bz * sim::kOwnerBlock + 4;
                ++per_region[m.owner_at(m.region_owner, x, z)][m.biome_at(x, z)];
            }
        }
        int regions = 0, uniform = 0, mountain = 0, pine_mountain = 0;
        for (const auto& [owner, biomes] : per_region) {
            int total = 0, most = 0;
            for (const auto& [b, count] : biomes) {
                total += count;
                most = std::max(most, count);
            }
            if (total < 40) {
                continue;
            }
            ++regions;
            uniform += most * 10 >= total * 8 ? 1 : 0;
            if (m.landforms[owner - 1u].kind == LandformKind::Mountains) {
                ++mountain;
                pine_mountain += biomes.count(static_cast<std::uint8_t>(pine)) != 0 && biomes.at(static_cast<std::uint8_t>(pine)) == most ? 1 : 0;
            }
        }
        MESSAGE(uniform << " of " << regions << " regions of one biome; " << pine_mountain << " of " << mountain << " mountains of pines");
        CHECK(uniform * 10 >= regions * 8);
        CHECK(mountain > 0);
        CHECK(pine_mountain == mountain);
    }

    TEST_CASE("every map type and a crowd of towns") {
        const auto& types = sc::test::core_content().flora.map_types;
        for (std::size_t t = 0; t < types.size(); ++t) {
            CAPTURE(types[t].id);
            sim::MapSettings s = hier_settings(95 + t, sim::MapSize::Small);
            s.map_type = static_cast<std::uint8_t>(t);
            const sim::MapData m = generate(s);
            CHECK(m.starts.size() == 2);
            CHECK_FALSE(m.features.empty());
        }
        sim::MapSettings crowd = hier_settings(99, sim::MapSize::Large);
        crowd.players = 12;
        const sim::MapData m = generate(crowd);
        REQUIRE(m.starts.size() == 12);
        for (const sim::StartPosition& st : m.starts) {
            CHECK_FALSE(m.water_at(st.x.floor_int(), st.z.floor_int()));
        }
    }
}

