#include <doctest.h>

#include <chrono>
#include <memory>
#include <optional>
#include <ostream>

#include "sim/game.h"
#include "sim/worldgen.h"
#include "test_util.h"

using namespace sc::sim;

namespace {

std::shared_ptr<const Content> content() {
    // Aliases the static core content; nothing to free.
    return std::shared_ptr<const Content>(std::shared_ptr<const Content>{}, &sc::test::core_content());
}

MapData small_map(std::uint64_t seed, std::uint8_t players = 1) {
    MapSettings s;
    s.seed = seed;
    s.size = MapSize::Small;
    s.players = players;
    std::optional<MapData> m = generate_map(s, *content());
    REQUIRE(m.has_value());
    return std::move(*m);
}

DefIndex building(std::string_view id) {
    const DefIndex d = content()->find_building(std::string("core:") + std::string(id));
    REQUIRE(d != kNoDef);
    return d;
}

DefIndex resource(std::string_view id) {
    const DefIndex d = content()->find_resource(std::string("core:") + std::string(id));
    REQUIRE(d != kNoDef);
    return d;
}

const Building& town_center(const Game& g, std::uint8_t player = 0) {
    const Building* b = g.buildings().get(g.player(player).town_center);
    REQUIRE(b != nullptr);
    return *b;
}

// A free spot for `def` near the player's town center, spiraling out.
std::optional<std::pair<std::int32_t, std::int32_t>> spot_near(const Game& g, DefIndex def, std::int32_t skip = 0) {
    const Building& tc = town_center(g);
    for (std::int32_t r = 10; r < 120; r += 2) {
        for (std::int32_t dz = -r; dz <= r; dz += 2) {
            for (std::int32_t dx = -r; dx <= r; dx += 2) {
                if (std::max(std::abs(dx), std::abs(dz)) != r) {
                    continue;
                }
                const std::int32_t x = tc.x + dx;
                const std::int32_t z = tc.z + dz;
                if (g.can_place(0, def, x, z, 0) == PlaceError::None) {
                    if (skip-- == 0) {
                        return std::pair{x, z};
                    }
                }
            }
        }
    }
    return std::nullopt;
}

bool place(Game& g, DefIndex def, std::int32_t skip = 0) {
    const auto at = spot_near(g, def, skip);
    if (!at) {
        return false;
    }
    Command c;
    c.type = CommandType::PlaceBuilding;
    c.player = 0;
    c.def = def;
    c.position = {Fixed::from_int(at->first), Fixed::from_int(at->second)};
    const std::size_t before = g.buildings().size();
    g.apply(c);
    return g.buildings().size() == before + 1;
}

void run(Game& g, std::uint32_t ticks) {
    for (std::uint32_t i = 0; i < ticks; ++i) {
        g.step();
    }
}

std::int32_t complete_count(const Game& g, DefIndex def) {
    std::int32_t n = 0;
    for (const Building& b : g.buildings().data()) {
        n += b.def == def && b.state == BuildingState::Complete ? 1 : 0;
    }
    return n;
}

// A sensible opening: food, wood, homes and storage.
void opening(Game& g) {
    CHECK(place(g, building("forager")));
    CHECK(place(g, building("woodcutter")));
    CHECK(place(g, building("house")));
    CHECK(place(g, building("house")));
}

}  // namespace

TEST_SUITE("village") {
    TEST_CASE("a new game has a town center, villagers and goods") {
        Game g(content(), small_map(11), 1, 5);
        CHECK(g.player_count() == 1);
        const Building& tc = town_center(g);
        CHECK(tc.state == BuildingState::Complete);
        CHECK(g.population(0) == village::kStartVillagers);
        CHECK(g.population(0, true) == 10);
        const auto stored = g.stored(0);
        CHECK(stored[resource("log")] == 60);
        CHECK(stored[resource("berries")] == 150);
    }

    TEST_CASE("placement rules") {
        Game g(content(), small_map(12), 1, 5);
        const Building& tc = town_center(g);
        CHECK(g.can_place(0, building("house"), tc.x, tc.z, 0) == PlaceError::Blocked);
        CHECK(g.can_place(0, building("house"), -3, 10, 0) == PlaceError::OutsideMap);
        CHECK(g.can_place(0, building("town_center"), tc.x + 30, tc.z, 0) == PlaceError::Unique);
        CHECK(g.can_place(0, kNoDef, 50, 50, 0) == PlaceError::UnknownBuilding);
        // A bad command is rejected and counted, the same on every machine.
        Command c;
        c.type = CommandType::PlaceBuilding;
        c.player = 0;
        c.def = building("house");
        c.position = {Fixed::from_int(tc.x), Fixed::from_int(tc.z)};
        g.apply(c);
        CHECK(g.rejected_commands() == 1);
        c.player = 5;  // No such player.
        g.apply(c);
        CHECK(g.rejected_commands() == 2);
        // The town center cannot be removed.
        Command rm;
        rm.type = CommandType::RemoveBuilding;
        rm.player = 0;
        rm.entity = g.player(0).town_center;
        g.apply(rm);
        CHECK(g.rejected_commands() == 3);
    }

    TEST_CASE("rotated footprints swap width and depth") {
        const BuildingDef& d = content()->buildings[building("house")];
        std::int32_t w = 0, dp = 0;
        Game::footprint(d, 1, w, dp);
        CHECK(w == d.depth);
        CHECK(dp == d.width);
    }

    TEST_CASE("laborers build a house and families move in") {
        Game g(content(), small_map(13), 1, 7);
        REQUIRE(place(g, building("house")));
        const std::int32_t logs = g.stored(0)[resource("log")];
        run(g, 3000);
        CHECK(complete_count(g, building("house")) == 1);
        CHECK(g.stored(0)[resource("log")] <= logs - 12);
        std::int32_t housed = 0;
        for (const Villager& v : g.villagers().data()) {
            housed += g.buildings().get(v.home) != nullptr ? 1 : 0;
        }
        CHECK(housed >= 4);
    }

    TEST_CASE("gatherers bring wood and food to storage") {
        Game g(content(), small_map(14), 1, 7);
        REQUIRE(place(g, building("woodcutter")));
        REQUIRE(place(g, building("forager")));
        const auto before = g.stored(0);
        run(g, 6000);
        CHECK(complete_count(g, building("woodcutter")) == 1);
        CHECK(complete_count(g, building("forager")) == 1);
        const auto after = g.stored(0);
        // Wood: spent 16 on the two buildings, then gathered well past that.
        CHECK(after[resource("log")] > before[resource("log")] - 16);
        MESSAGE("logs " << before[resource("log")] << " -> " << after[resource("log")] << ", berries "
                        << before[resource("berries")] << " -> " << after[resource("berries")]);
    }

    TEST_CASE("without food the village starves") {
        auto hungry = std::make_shared<Content>(sc::test::core_content());
        for (ResourceDef& r : hungry->resources) {
            if (r.category == ResourceCategory::Food) {
                r.category = ResourceCategory::Material;  // Nothing is edible.
            }
        }
        Game g(hungry, small_map(15), 1, 3);
        run(g, 2500);
        CHECK(g.population(0) == village::kStartVillagers);
        run(g, 9000);  // Children eat half as much and last longer.
        CHECK(g.population(0) == 0);
        CHECK(g.player(0).deaths == village::kStartVillagers);
    }

    TEST_CASE("the same commands give the same game") {
        const MapData map = small_map(16);
        Game a(content(), map, 1, 99);
        Game b(content(), map, 1, 99);
        opening(a);
        opening(b);
        CHECK(a.hash() == b.hash());
        for (int i = 0; i < 20; ++i) {
            run(a, 250);
            run(b, 250);
            REQUIRE(a.hash() == b.hash());
        }
        Game c(content(), map, 1, 100);  // Another seed: another story.
        opening(c);
        run(c, 5000);
        CHECK(c.hash() != a.hash());
    }

    TEST_CASE("save and load keep everything") {
        Game g(content(), small_map(17), 1, 21);
        opening(g);
        run(g, 4321);
        BinaryWriter w;
        g.save(w);
        Game back(content(), small_map(1), 1, 1);
        BinaryReader r(w.bytes());
        REQUIRE(back.load(r, content()));
        CHECK(r.at_end());
        CHECK(back.hash() == g.hash());
        CHECK(back.tick() == g.tick());
        // And it goes on the same way.
        run(g, 1500);
        run(back, 1500);
        CHECK(back.hash() == g.hash());
    }

    TEST_CASE("broken saves are rejected and leave the game untouched") {
        Game g(content(), small_map(18), 1, 21);
        run(g, 200);
        BinaryWriter w;
        g.save(w);
        const std::uint64_t hash = g.hash();
        // Truncated at many points.
        for (std::size_t cut = 0; cut < w.bytes().size(); cut += w.bytes().size() / 37 + 1) {
            BinaryReader r(std::span(w.bytes().data(), cut));
            CHECK_FALSE(g.load(r, content()));
            REQUIRE(g.hash() == hash);
        }
        // Another content (another set of mods).
        auto other = std::make_shared<Content>(sc::test::core_content());
        other->hash ^= 1;
        BinaryReader r(w.bytes());
        CHECK_FALSE(g.load(r, other));
        CHECK(g.hash() == hash);
    }

    TEST_CASE("an hour of play: a tended village grows") {
        const auto start = std::chrono::steady_clock::now();
        Game g(content(), small_map(19), 1, 77);
        opening(g);
        int houses = 2;
        int foragers = 1;
        // An hour at normal speed; the player builds as the town grows.
        for (int minute = 0; minute < 60; ++minute) {
            run(g, 600);
            const auto stored = g.stored(0);
            if (stored[resource("log")] >= 20 && houses < 8 && g.population(0) + 4 > houses * 5 - 5) {
                if (place(g, building("house"))) {
                    ++houses;
                }
            }
            std::int32_t food = 0;
            for (std::size_t r = 0; r < stored.size(); ++r) {
                food += content()->resources[r].category == ResourceCategory::Food ? stored[r] : 0;
            }
            if (food < g.population(0) * 6 && foragers < 5 && place(g, building("forager"))) {
                ++foragers;
            }
            if (minute == 10) {
                CHECK(place(g, building("storehouse")));
            }
            if (minute == 20) {
                CHECK(place(g, building("woodcutter")));
                CHECK(place(g, building("stonecutter")));
            }
        }
        const Game& end = g;
        const auto stored = end.stored(0);
        MESSAGE("after an hour: population " << end.population(0) << ", births " << end.player(0).births
                                             << ", arrivals " << end.player(0).arrivals << ", deaths "
                                             << end.player(0).deaths << ", houses " << complete_count(end, building("house"))
                                             << ", logs " << stored[resource("log")] << ", berries "
                                             << stored[resource("berries")] << ", "
                                             << std::chrono::duration_cast<std::chrono::milliseconds>(
                                                    std::chrono::steady_clock::now() - start)
                                                    .count()
                                             << " ms");
        CHECK(end.population(0) > village::kStartVillagers);
        CHECK(complete_count(end, building("house")) >= 4);
    }

    TEST_CASE("an untended village fades away") {
        // No buildings: berries run out and nobody gathers more.
        Game g(content(), small_map(20), 1, 5);
        run(g, 36000);
        MESSAGE("untended: population " << g.population(0) << ", deaths " << g.player(0).deaths);
        CHECK(g.population(0) < village::kStartVillagers);
    }
}
