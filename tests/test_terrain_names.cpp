#include <doctest.h>

#include <algorithm>
#include <array>
#include <memory>
#include <optional>

#include "game/terrain_names.h"
#include "sim/game.h"
#include "sim/worldgen.h"
#include "test_util.h"

using namespace sc;

namespace {

std::shared_ptr<const sim::Content> shared_content() {
    // Not owned: the core content lives for the whole test run.
    return std::shared_ptr<const sim::Content>(std::shared_ptr<const sim::Content>{}, &sc::test::core_content());
}

sim::MapData generate(const sim::MapSettings& s) {
    std::optional<sim::MapData> m = sim::generate_map(s, sc::test::core_content());
    REQUIRE(m.has_value());
    return std::move(*m);
}

sim::MapSettings coast_settings(std::uint64_t seed) {
    sim::MapSettings s;
    s.seed = seed;
    s.size = sim::MapSize::Medium;
    s.players = 2;
    s.sea = sim::Sea::OneSide;
    s.landforms = sim::Amount::High;
    s.rivers = sim::Amount::High;
    return s;
}

bool has(const CellDescription& d, sim::LandformKind k) {
    return std::find(d.landforms.begin(), d.landforms.end(), k) != d.landforms.end();
}

// A point `t` of the way (0..1) along a landform's line.
std::array<double, 2> along(const sim::Landform& l, double t) {
    const double pos = t * static_cast<double>(l.points.size() - 1);
    const auto k = std::min(static_cast<std::size_t>(pos), l.points.size() - 2);
    const double f = pos - static_cast<double>(k);
    return {l.points[k][0] + (l.points[k + 1][0] - l.points[k][0]) * f,
            l.points[k][1] + (l.points[k + 1][1] - l.points[k][1]) * f};
}

CellDescription describe_at(TerrainNames& names, const sim::MapData& m, std::array<double, 2> p) {
    return names.describe(m, static_cast<std::int32_t>(p[0]), static_cast<std::int32_t>(p[1]));
}

}  // namespace

TEST_SUITE("terrain_names") {
    TEST_CASE("the names of what is under the cursor, on maps with a coast") {
        int lines = 0, lines_named = 0;
        int regions = 0, regions_named = 0;
        int river_points = 0, river_named = 0;
        int lobes = 0, lobes_right = 0;
        int sea_border = 0, border_water = 0;
        int lakes = 0, coasts = 0;
        for (std::uint64_t seed = 60; seed < 66; ++seed) {
            const sim::MapData m = generate(coast_settings(seed));
            REQUIRE(m.sea_levels.size() == 1);
            REQUIRE(m.sea_levels[0] != 0);
            TerrainNames names;
            CHECK_FALSE(names.describe(m, -1, 0).inside);
            CHECK_FALSE(names.describe(m, 0, m.size).inside);
            for (const sim::Landform& l : m.landforms) {
                switch (l.kind) {
                    case sim::LandformKind::Plateau: {
                        // A region: its middle says so.
                        const CellDescription d = describe_at(names, m, {double(l.points[0][0]), double(l.points[0][1])});
                        if (d.water == WaterKind::None) {
                            ++regions;
                            regions_named += d.region == l.kind ? 1 : 0;
                        }
                        break;
                    }
                    case sim::LandformKind::Valley:
                    case sim::LandformKind::Canyon:
                        // Along the middle of the line: a more specific
                        // structure (a ramp, a cliff) may take some of it.
                        for (int k = 4; k <= 36; ++k) {
                            const CellDescription d = describe_at(names, m, along(l, k / 40.0));
                            if (d.inside && d.water == WaterKind::None) {
                                ++lines;
                                lines_named += has(d, l.kind) ? 1 : 0;
                            }
                        }
                        break;
                    case sim::LandformKind::River:
                        for (std::size_t k = 1; k + 1 < l.points.size(); ++k) {
                            const CellDescription d = describe_at(names, m, {double(l.points[k][0]), double(l.points[k][1])});
                            if (d.inside && d.water != WaterKind::None) {
                                ++river_points;
                                river_named += d.water == WaterKind::River ? 1 : 0;
                            }
                        }
                        break;
                    case sim::LandformKind::Gulf:
                    case sim::LandformKind::Peninsula: {
                        // The middle of the region it took: sea in a gulf,
                        // land on a peninsula.
                        const CellDescription d = describe_at(names, m, {double(l.points[0][0]), double(l.points[0][1])});
                        if (d.inside) {
                            ++lobes;
                            const bool gulf = l.kind == sim::LandformKind::Gulf;
                            lobes_right += (gulf ? d.water == WaterKind::Sea : d.water == WaterKind::None) && has(d, l.kind) ? 1 : 0;
                        }
                        break;
                    }
                    default: break;
                }
            }
            // The sea reaches the border; its water is at the sea's level.
            for (std::int32_t i = 0; i < m.size; ++i) {
                for (const auto [x, z] : {std::pair{i, 0}, std::pair{i, m.size - 1}, std::pair{0, i}, std::pair{m.size - 1, i}}) {
                    if (m.water_at(x, z)) {
                        ++border_water;
                        sea_border += names.describe(m, x, z).water == WaterKind::Sea ? 1 : 0;
                    }
                }
            }
            // Lakes, and the coast beside the sea.
            for (std::int32_t z = 1; z < m.size - 1; z += 3) {
                for (std::int32_t x = 1; x < m.size - 1; x += 3) {
                    if (!m.water_at(x, z) && (m.water_at(x + 1, z) || m.water_at(x - 1, z))) {
                        const CellDescription d = names.describe(m, x, z);
                        const CellDescription wet = names.describe(m, m.water_at(x + 1, z) ? x + 1 : x - 1, z);
                        if (wet.water == WaterKind::Sea) {
                            coasts += d.coast ? 1 : 0;
                            CHECK(d.coast);
                        }
                        lakes += wet.water == WaterKind::Lake ? 1 : 0;
                    }
                }
            }
        }
        MESSAGE("regions " << regions_named << "/" << regions << ", lines " << lines_named << "/" << lines << ", rivers " << river_named << "/" << river_points << ", lobes "
                         << lobes_right << "/" << lobes << ", sea border " << sea_border << "/" << border_water);
        CHECK(regions > 0);
        CHECK(regions_named == regions);
        CHECK(lines > 100);
        CHECK(lines_named * 10 >= lines * 8);
        CHECK(river_points > 50);
        CHECK(river_named * 10 >= river_points * 9);
        CHECK(lobes >= 6);
        CHECK(lobes_right * 10 >= lobes * 8);
        CHECK(border_water > 0);
        CHECK(sea_border * 10 >= border_water * 9);
        CHECK(lakes > 0);
        CHECK(coasts > 0);
    }

    TEST_CASE("islands and separate maps have their names too") {
        sim::MapSettings s;
        s.seed = 404;
        s.size = sim::MapSize::Small;
        s.players = 2;
        s.sea = sc::sim::Sea::Archipelago;
        const sim::MapData islands = generate(s);
        TerrainNames names;
        int count = 0;
        for (const sim::Landform& l : islands.landforms) {
            if (l.kind == sim::LandformKind::Island) {
                ++count;
                const CellDescription d = names.describe(islands, l.points[0][0], l.points[0][1]);
                CHECK(d.water == WaterKind::None);
                CHECK(has(d, sim::LandformKind::Island));
            }
        }
        CHECK(count == 2 * std::min<std::int32_t>(s.islands, sim::worldgen::max_islands_per_town(s.size, 2)));
        // The open sea between them.
        CHECK(names.describe(islands, 2, 2).water == WaterKind::Sea);

        // Separate maps: each region keeps its own landforms and sea.
        sim::MapSettings sep;
        sep.seed = 405;
        sep.size = sim::MapSize::Small;
        sep.players = 2;
        sep.separate = true;
        sep.sea = sim::Sea::OneSide;
        const sim::MapData world = generate(sep);
        const std::int32_t t = world.region_size();
        REQUIRE(world.sea_levels.size() == 4);
        std::array<int, 4> per_region{};
        for (const sim::Landform& l : world.landforms) {
            if (l.kind == sim::LandformKind::River) {
                ++per_region[static_cast<std::size_t>(world.region_at(l.points[0][0], l.points[0][1]))];
            }
        }
        CHECK(per_region[0] > 0);
        CHECK(per_region[1] > 0);
        CHECK(per_region[2] == 0);  // Nobody's square: only sea.
        CHECK(world.sea_levels[1] != 0);
        TerrainNames world_names;
        CHECK(world_names.describe(world, t / 2, t + t / 2).water == WaterKind::Sea);
    }

    TEST_CASE("the landforms are saved with the game") {
        const sim::MapData map = generate(coast_settings(61));
        REQUIRE_FALSE(map.landforms.empty());
        sim::Game g(shared_content(), map, 1, 21);
        sim::BinaryWriter w;
        g.save(w);
        sim::Game back(shared_content(), sim::MapData{}, 0, 0);
        sim::BinaryReader r(w.bytes());
        REQUIRE(back.load(r, shared_content()));
        CHECK(r.at_end());
        CHECK(back.map().landforms == map.landforms);
        CHECK(back.map().sea_levels == map.sea_levels);
        // Names describe the terrain; they are not part of its checksum.
        sim::MapData unnamed = map;
        unnamed.landforms.clear();
        unnamed.sea_levels.clear();
        CHECK(unnamed.checksum() == map.checksum());
    }

    TEST_CASE("the description as text") {
        const sim::MapData map = generate(coast_settings(62));
        TerrainNames names;
        const CellDescription d = names.describe(map, map.size / 2, map.size / 2);
        const std::vector<std::string> lines = describe_lines(d, &sc::test::core_content());
        CHECK(lines.size() >= 5);
        CHECK(describe_lines(names.describe(map, -5, 3), nullptr).size() == 1);
    }
}
