// Timing of the simulation with many villagers (phase 20). The small case
// runs with the other tests; the big one (12 towns of 1000 on a huge map)
// only on demand: salvaciudad_tests -ts=sim_perf --no-skip.
#include <doctest.h>

#include <algorithm>
#include <chrono>
#include <memory>
#include <optional>
#include <ostream>
#include <vector>

#include "game/fog_view.h"
#include "net/protocol.h"
#include "sim/game.h"
#include "sim/worldgen.h"
#include "test_util.h"

using namespace sc::sim;

namespace {

std::shared_ptr<const Content> core() {
    return std::shared_ptr<const Content>(std::shared_ptr<const Content>{}, &sc::test::core_content());
}

void command(Game& g, CommandType type, std::uint8_t player, std::int32_t value, DefIndex def = 0) {
    Command c;
    c.type = type;
    c.player = player;
    c.value = value;
    c.def = def;
    g.apply(c);
}

// A town ready to hold its people: houses, storage, food and work.
void grow(Game& g, std::uint8_t p, std::int32_t people) {
    const Content& c = g.content();
    for (const char* r : {"core:log", "core:stone"}) {
        command(g, CommandType::DevGrant, p, 10000, c.find_resource(r));
    }
    command(g, CommandType::DevGrant, p, 10000, c.find_resource("core:berries"));
    command(g, CommandType::DevGrant, p, 5000, c.find_resource("core:firewood"));
    const Building* tc = g.buildings().get(g.player(p).town_center);
    REQUIRE(tc != nullptr);
    const int tx = tc->x;
    const int tz = tc->z;
    // Houses for everyone, then some workplaces, in rings.
    std::vector<const char*> wanted;
    for (int h = 0; h < people / 5; ++h) {
        wanted.push_back("core:house");
    }
    for (int k = 0; k < std::max(1, people / 100); ++k) {
        for (const char* w : {"core:woodcutter", "core:forager", "core:stonecutter", "core:storehouse",
                              "core:firewood_splitter", "core:well"}) {
            wanted.push_back(w);
        }
    }
    std::size_t next = 0;
    for (int r = 10; r < 300 && next < wanted.size(); r += 7) {
        for (int a = -r; a <= r && next < wanted.size(); a += 7) {
            for (const auto& [x, z] : {std::pair{tx + a, tz - r}, std::pair{tx + a, tz + r}, std::pair{tx - r, tz + a},
                                       std::pair{tx + r, tz + a}}) {
                if (next >= wanted.size()) {
                    break;
                }
                const DefIndex d = c.find_building(wanted[next]);
                if (g.can_place(p, d, x, z, 0) != PlaceError::None) {
                    continue;
                }
                Command place;
                place.type = CommandType::PlaceBuilding;
                place.player = p;
                place.def = d;
                place.position = {Fixed::from_int(x), Fixed::from_int(z)};
                g.apply(place);
                ++next;
            }
        }
    }
    for (std::int32_t n = 0; n < people; n += 500) {
        command(g, CommandType::DevSpawn, p, std::min(500, people - n));
    }
}

struct Timing {
    double mean_ms = 0.0;
    double worst_ms = 0.0;
    double p95_ms = 0.0;
};

Timing measure(Game& g, int ticks) {
    std::vector<double> ms;
    ms.reserve(static_cast<std::size_t>(ticks));
    for (int t = 0; t < ticks; ++t) {
        const auto t0 = std::chrono::steady_clock::now();
        g.step();
        ms.push_back(std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - t0).count());
    }
    Timing out;
    for (const double m : ms) {
        out.mean_ms += m;
        out.worst_ms = std::max(out.worst_ms, m);
    }
    out.mean_ms /= static_cast<double>(ms.size());
    std::sort(ms.begin(), ms.end());
    out.p95_ms = ms[ms.size() * 95 / 100];
    return out;
}

GameSetup rules(std::uint8_t players) {
    GameSetup s;
    s.players = players;
    s.seed = 20;
    s.rules.climate.seasons = 0b0010;
    s.rules.raiders = Threat::None;
    return s;
}

}  // namespace

TEST_SUITE("sim_perf") {
    TEST_CASE("two towns of 300 keep up at triple speed (release)") {
#ifdef NDEBUG
        MapSettings ms;
        ms.seed = 20;
        ms.size = MapSize::Medium;
        ms.players = 2;
        std::optional<MapData> map = generate_map(ms, sc::test::core_content());
        REQUIRE(map.has_value());
        Game g(core(), *map, rules(2));
        for (std::uint8_t p = 0; p < 2; ++p) {
            grow(g, p, 300);
        }
        (void)measure(g, 600);  // Settling: everyone goes to work.
        const Timing t = measure(g, 1200);
        MESSAGE("2 x 300: " << g.villagers().size() << " villagers, " << g.buildings().size() << " buildings; tick "
                            << t.mean_ms << " ms mean, " << t.p95_ms << " ms p95, " << t.worst_ms << " ms worst");
        // Triple speed is 30 ticks a second: 33 ms each at most, on average.
        CHECK(t.mean_ms < 33.0);
#else
        MESSAGE("skipped: timing is only meaningful in release builds");
#endif
    }

    TEST_CASE("twelve towns of 1000 on a huge map" * doctest::skip()) {
        MapSettings ms;
        ms.seed = 2026;
        ms.size = MapSize::Huge;
        ms.players = 12;
        const auto g0 = std::chrono::steady_clock::now();
        std::optional<MapData> map = generate_map(ms, sc::test::core_content());
        REQUIRE(map.has_value());
        MESSAGE("map: " << std::chrono::duration<double>(std::chrono::steady_clock::now() - g0).count() << " s");
        Game g(core(), *map, rules(12));
        for (std::uint8_t p = 0; p < 12; ++p) {
            grow(g, p, 1000);
        }
        MESSAGE("12 x 1000: " << g.villagers().size() << " villagers, " << g.buildings().size() << " buildings");
        const Timing settle = measure(g, 600);
        MESSAGE("settling: " << settle.mean_ms << " ms mean, " << settle.p95_ms << " ms p95, " << settle.worst_ms
                             << " ms worst");
        const Timing t = measure(g, 2000);
        MESSAGE("running: " << t.mean_ms << " ms mean, " << t.p95_ms << " ms p95, " << t.worst_ms << " ms worst, "
                            << g.villagers().size() << " villagers");
        const auto h0 = std::chrono::steady_clock::now();
        (void)g.hash();
        MESSAGE("hash: " << std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - h0).count()
                         << " ms");
        BinaryWriter w;
        const auto s0 = std::chrono::steady_clock::now();
        g.save(w);
        MESSAGE("save: " << std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - s0).count()
                         << " ms, " << w.bytes().size() / 1024 << " KiB");
        const auto z0 = std::chrono::steady_clock::now();
        const sc::net::Snapshot snap = sc::net::pack_snapshot(g.tick(), w.bytes());
        MESSAGE("network snapshot: " << std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - z0).count()
                                     << " ms, " << snap.packed.size() / 1024 << " KiB packed");
    }

    // Phases 32 to 34: what the fog of war costs the simulation, with a
    // vision group per town (versus) as the worst case.
    TEST_CASE("twelve towns of 1000 with and without fog of war" * doctest::skip()) {
        MapSettings ms;
        ms.seed = 2026;
        ms.size = MapSize::Huge;
        ms.players = 12;
        std::optional<MapData> map = generate_map(ms, sc::test::core_content());
        REQUIRE(map.has_value());
        for (const FogMode fog : {FogMode::Static, FogMode::None, FogMode::Dynamic}) {
            GameSetup setup = rules(12);
            setup.rules.fog = fog;
            setup.rules.versus = true;
            Game g(core(), *map, setup);
            for (std::uint8_t p = 0; p < 12; ++p) {
                grow(g, p, 1000);
            }
            (void)measure(g, 600);
            const Timing t = measure(g, 2000);
            const auto h0 = std::chrono::steady_clock::now();
            (void)g.hash();
            const double hash_ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - h0).count();
            BinaryWriter w;
            g.save(w);
            // The update itself, once a second (ten ticks).
            const auto v0 = std::chrono::steady_clock::now();
            for (int k = 0; k < 20; ++k) {
                g.update_vision();
            }
            const double vision_ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - v0).count() / 20.0;
            // What the view works out each tick for one town.
            double view_ms = 0.0;
            if (fog != FogMode::None) {
                sc::FogView view;
                view.begin(g, g.vision_group(0));
                for (int k = 0; k < 50; ++k) {
                    g.step();
                    const auto f0 = std::chrono::steady_clock::now();
                    view.update(g);
                    (void)view.take_dirty();
                    view_ms += std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - f0).count();
                }
                view_ms /= 50.0;
            }
            MESSAGE("fog " << static_cast<int>(fog) << ": " << g.villagers().size() << " villagers; tick " << t.mean_ms
                           << " ms mean, " << t.p95_ms << " ms p95, " << t.worst_ms << " ms worst; vision update "
                           << vision_ms << " ms (" << vision_ms / 10.0 << " ms a tick); view " << view_ms << " ms a tick; hash " << hash_ms
                           << " ms; save " << w.bytes().size() / 1024 << " KiB");
        }
    }
}

#ifdef _WIN32
#include <windows.h>
#include <psapi.h>
#pragma comment(lib, "psapi.lib")
#endif

namespace {

// Peak memory of this process so far, MiB (0 where not measured).
std::size_t peak_mib() {
#ifdef _WIN32
    PROCESS_MEMORY_COUNTERS pmc{};
    if (GetProcessMemoryInfo(GetCurrentProcess(), &pmc, sizeof(pmc)) != 0) {
        return pmc.PeakWorkingSetSize / (1u << 20);
    }
#endif
    return 0;
}

}  // namespace

TEST_SUITE("sim_perf") {
    // Phase 21: generation time, memory, save and snapshot of the two
    // biggest sizes (several minutes; docs/RENDIMIENTO.md).
    TEST_CASE("giant and colossal maps" * doctest::skip()) {
        for (const MapSize size : {MapSize::Giant, MapSize::Colossal}) {
            MapSettings ms;
            ms.seed = 2026;
            ms.size = size;
            ms.players = 12;
            const auto g0 = std::chrono::steady_clock::now();
            std::optional<MapData> map = generate_map(ms, sc::test::core_content());
            REQUIRE(map.has_value());
            CHECK(map->features.size() <= kMaxMapFeatures);
            MESSAGE(map_cells(size) << " m: generated in "
                                    << std::chrono::duration<double>(std::chrono::steady_clock::now() - g0).count()
                                    << " s, " << map->features.size() << " features, peak " << peak_mib() << " MiB");
            Game g(core(), *map, rules(12));
            map.reset();
            const Timing t = measure(g, 200);
            MESSAGE("tick " << t.mean_ms << " ms mean, " << t.worst_ms << " ms worst");
            const auto h0 = std::chrono::steady_clock::now();
            (void)g.hash();
            MESSAGE("hash: " << std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - h0).count()
                             << " ms");
            BinaryWriter w;
            const auto s0 = std::chrono::steady_clock::now();
            g.save(w);
            MESSAGE("save: " << std::chrono::duration<double>(std::chrono::steady_clock::now() - s0).count() << " s, "
                             << w.bytes().size() / (1u << 20) << " MiB");
            CHECK(w.bytes().size() <= sc::net::kMaxSnapshotBytes);
            const auto z0 = std::chrono::steady_clock::now();
            const sc::net::Snapshot snap = sc::net::pack_snapshot(g.tick(), w.bytes());
            MESSAGE("network snapshot: " << std::chrono::duration<double>(std::chrono::steady_clock::now() - z0).count()
                                         << " s, " << snap.packed.size() / (1u << 20) << " MiB packed");
            BinaryReader r(w.bytes());
            const auto l0 = std::chrono::steady_clock::now();
            CHECK(g.load(r, core()));
            MESSAGE("load: " << std::chrono::duration<double>(std::chrono::steady_clock::now() - l0).count() << " s, peak "
                             << peak_mib() << " MiB");
        }
    }
}

TEST_SUITE("sim_perf") {
    // Phase 86: what the growing of the trees costs a tick, on a map with no
    // towns (only the world's own work). Several minutes on the largest.
    TEST_CASE("the trees' growth on the largest maps" * doctest::skip()) {
        for (const MapSize size : {MapSize::Huge, MapSize::Colossal}) {
            MapSettings ms;
            ms.seed = 12345;
            ms.size = size;
            std::optional<MapData> map = generate_map(ms, sc::test::core_content());
            REQUIRE(map.has_value());
            std::size_t trees = 0;
            for (const MapFeature& f : map->features) {
                trees += f.type == FeatureType::Tree ? 1u : 0u;
            }
            GameSetup setup = rules(1);
            setup.players = 0;
            Game g(core(), *map, setup);
            map.reset();
            const std::uint32_t year = 12 * g.calendar_month_ticks();
            const Timing first = measure(g, year);      // Nothing grows in the first year.
            (void)g.take_changed_nodes();
            const Timing second = measure(g, year);     // Most trees grow in the second.
            MESSAGE(map_cells(size) << " m, " << trees << " trees, " << g.calendar_day_ticks() << " ticks a day: tick "
                                    << first.mean_ms << " ms mean and " << first.worst_ms << " ms worst while nothing grows; "
                                    << second.mean_ms << " ms mean and " << second.worst_ms << " ms worst while "
                                    << g.take_changed_nodes().size() << " trees grow");
        }
    }
}
