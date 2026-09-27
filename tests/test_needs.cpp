#include <doctest.h>

#include <memory>
#include <optional>
#include <ostream>

#include "sim/game.h"
#include "sim/worldgen.h"
#include "test_util.h"

using namespace sc::sim;

namespace {

// The core content with every building available from the start, for
// testing chains without growing a town first.
std::shared_ptr<const Content> open_content() {
    static const std::shared_ptr<const Content> c = [] {
        auto copy = std::make_shared<Content>(sc::test::core_content());
        for (BuildingDef& b : copy->buildings) {
            b.tier = 0;
        }
        return copy;
    }();
    return c;
}

std::shared_ptr<const Content> core() {
    return std::shared_ptr<const Content>(std::shared_ptr<const Content>{}, &sc::test::core_content());
}

const MapData& map_for(std::uint64_t seed) {
    static std::map<std::uint64_t, MapData> cache;
    auto it = cache.find(seed);
    if (it == cache.end()) {
        MapSettings s;
        s.seed = seed;
        s.size = MapSize::Small;
        std::optional<MapData> m = generate_map(s, sc::test::core_content());
        REQUIRE(m.has_value());
        it = cache.emplace(seed, std::move(*m)).first;
    }
    return it->second;
}

GameSetup setup() {
    GameSetup s;
    s.seed = 11;
    s.rules.climate.seasons = 0b0010;  // Summer: no cold to worry about.
    return s;
}

void run(Game& g, std::uint32_t ticks) {
    for (std::uint32_t i = 0; i < ticks; ++i) {
        g.step();
    }
}

void grant(Game& g, const char* resource, std::int32_t amount) {
    Command c;
    c.type = CommandType::DevGrant;
    c.def = g.content().find_resource(resource);
    REQUIRE(c.def != kNoDef);
    c.value = amount;
    g.apply(c);
}

EntityId place(Game& g, const char* def, int x0 = -1, int z0 = -1) {
    const DefIndex d = g.content().find_building(def);
    REQUIRE(d != kNoDef);
    const Building* tc = g.buildings().get(g.player(0).town_center);
    const int ox = x0 >= 0 ? x0 : tc->x;
    const int oz = z0 >= 0 ? z0 : tc->z;
    for (int r = x0 >= 0 ? 0 : 12; r < 140; r += 2) {
        for (int a = 0; a < 8; ++a) {
            const int x = ox + (a % 3 - 1) * r;
            const int z = oz + (a / 3 - 1) * r;
            if (g.can_place(0, d, x, z, 0) != PlaceError::None) {
                continue;
            }
            Command c;
            c.type = CommandType::PlaceBuilding;
            c.def = d;
            c.position = {Fixed::from_int(x), Fixed::from_int(z)};
            g.apply(c);
            for (std::size_t i = 0; i < g.buildings().size(); ++i) {
                const Building& b = g.buildings().data()[i];
                if (b.def == d && b.x == x && b.z == z) {
                    return g.buildings().entities()[i];
                }
            }
        }
    }
    FAIL("no room for " << def);
    return {};
}

EntityId build(Game& g, const char* def, int x0 = -1, int z0 = -1) {
    grant(g, "core:log", 200);
    grant(g, "core:stone", 100);
    grant(g, "core:bricks", 50);
    const EntityId id = place(g, def, x0, z0);
    for (int t = 0; t < 80 && g.buildings().get(id)->state != BuildingState::Complete; ++t) {
        run(g, 100);
    }
    REQUIRE(g.buildings().get(id)->state == BuildingState::Complete);
    return id;
}

std::int32_t total(const Game& g, const char* resource) {
    const DefIndex r = g.content().find_resource(resource);
    std::int32_t n = g.stored(0)[r];
    for (const Villager& v : g.villagers().data()) {
        n += v.carrying.resource == r ? v.carrying.amount : 0;
    }
    return n;
}

bool has(const Building& b, Need n) {
    return ((b.needs >> static_cast<unsigned>(n)) & 1u) != 0;
}

}  // namespace

TEST_SUITE("needs") {
    TEST_CASE("wheat becomes flour and flour becomes bread") {
        Game g(open_content(), map_for(61), setup());
        (void)build(g, "core:mill");
        (void)build(g, "core:bakery");
        grant(g, "core:wheat", 60);
        grant(g, "core:firewood", 30);
        const std::int32_t bread = total(g, "core:bread");
        run(g, 4000);
        MESSAGE("bread " << bread << " -> " << total(g, "core:bread") << ", wheat left " << total(g, "core:wheat"));
        CHECK(total(g, "core:bread") > bread + 8);
        CHECK(total(g, "core:wheat") < 60);
    }

    TEST_CASE("a workshop with two recipes makes what it has the inputs for") {
        Game g(open_content(), map_for(62), setup());
        (void)build(g, "core:tailor");
        grant(g, "core:leather", 10);  // No linen: clothes from leather.
        const auto made = [&] {
            std::int32_t n = total(g, "core:clothes");
            for (const Villager& v : g.villagers().data()) {
                n += v.clothes > 0 ? 1 : 0;  // Clothes being worn.
            }
            return n;
        };
        const std::int32_t clothes = made();
        run(g, 3000);
        CHECK(made() > clothes);
        CHECK(total(g, "core:leather") < 10);
    }

    TEST_CASE("a production limit stops a workshop") {
        Game g(open_content(), map_for(63), setup());
        const EntityId pit = build(g, "core:clay_pit");
        Command c;
        c.type = CommandType::SetLimit;
        c.entity = pit;
        c.value = 6;
        g.apply(c);
        run(g, 5000);
        CHECK(total(g, "core:clay") >= 6);
        CHECK(total(g, "core:clay") <= 10);  // The limit plus a batch or two on the way.
    }

    TEST_CASE("buildings above the town center's level are locked") {
        Game g(core(), map_for(64), setup());
        CHECK(g.tier(0) == 1);
        const Building* tc = g.buildings().get(g.player(0).town_center);
        CHECK(g.can_place(0, g.content().find_building("core:mill"), tc->x + 30, tc->z, 0) == PlaceError::Locked);
        // Upgrading needs people.
        Command up;
        up.type = CommandType::UpgradeBuilding;
        up.entity = g.player(0).town_center;
        g.apply(up);
        CHECK(g.rejected_commands() == 1);
        CHECK_FALSE(g.buildings().get(g.player(0).town_center)->upgrading);
    }

    TEST_CASE("the town center goes up a level") {
        auto content = std::make_shared<Content>(sc::test::core_content());
        for (BuildingDef& b : content->buildings) {
            if (b.kind == BuildingKind::TownCenter && !b.levels.empty()) {
                b.levels[0].population = 1;
            }
        }
        Game g(content, map_for(65), setup());
        grant(g, "core:log", 100);
        grant(g, "core:stone", 60);
        Command up;
        up.type = CommandType::UpgradeBuilding;
        up.entity = g.player(0).town_center;
        g.apply(up);
        CHECK(g.buildings().get(g.player(0).town_center)->upgrading);
        run(g, 6000);
        CHECK(g.tier(0) == 2);
        const Building* tc = g.buildings().get(g.player(0).town_center);
        CHECK(g.can_place(0, g.content().find_building("core:mill"), tc->x + 30, tc->z, 0) != PlaceError::Locked);
    }

    TEST_CASE("a well waters the homes near it, and they are happier") {
        Game g(open_content(), map_for(66), setup());
        const EntityId house = build(g, "core:house");
        run(g, 300);
        CHECK_FALSE(has(*g.buildings().get(house), Need::Water));
        CHECK(has(*g.buildings().get(house), Need::Heating));  // Summer.
        const std::int32_t before = g.buildings().get(house)->happiness;
        const Building& h = *g.buildings().get(house);
        (void)build(g, "core:well", h.x + 8, h.z);
        run(g, 300);
        const Building& a = *g.buildings().get(house);
        CHECK(has(a, Need::Water));
        CHECK(a.happiness >= 0);
        CHECK(a.happiness <= 100);
        CHECK(a.happiness > before);
    }

    TEST_CASE("a tavern entertains only while it has beer") {
        Game g(open_content(), map_for(67), setup());
        const EntityId house = build(g, "core:house");
        const Building& h = *g.buildings().get(house);
        (void)build(g, "core:tavern", h.x + 12, h.z);
        run(g, 300);
        CHECK_FALSE(has(*g.buildings().get(house), Need::Entertainment));
        grant(g, "core:beer", 40);
        run(g, 1500);
        const Building* tavern = nullptr;
        for (const Building& b : g.buildings().data()) {
            tavern = g.content().buildings[b.def].id == "core:tavern" ? &b : tavern;
        }
        REQUIRE(tavern != nullptr);
        MESSAGE("tavern workers " << tavern->workers.size() << " stock " << tavern->stock.size() << " task "
                                  << static_cast<int>(g.villagers().get(tavern->workers.front())->task) << " beer "
                                  << total(g, "core:beer"));
        CHECK(has(*g.buildings().get(house), Need::Entertainment));
    }

    TEST_CASE("a house with its needs met is upgraded and holds more people") {
        Game g(open_content(), map_for(68), setup());
        const EntityId house = build(g, "core:house");
        const Building& h = *g.buildings().get(house);
        (void)build(g, "core:well", h.x + 8, h.z);
        // Three kinds of food, clothes, and the materials.
        grant(g, "core:berries", 100);
        grant(g, "core:vegetables", 100);
        grant(g, "core:fish", 100);
        grant(g, "core:clothes", 30);
        grant(g, "core:log", 50);
        grant(g, "core:stone", 50);
        const std::int32_t room = g.capacity(*g.buildings().get(house));
        run(g, g.month_ticks() * 2 + 2000);
        const Building& after = *g.buildings().get(house);
        MESSAGE("needs " << after.needs << ", level " << static_cast<int>(after.level) << ", happiness " << after.happiness);

        CHECK(after.level == 1);
        CHECK(g.capacity(after) > room);
    }

    TEST_CASE("a market stocks food and villagers eat there") {
        Game g(open_content(), map_for(69), setup());
        const EntityId market = build(g, "core:market");
        grant(g, "core:vegetables", 60);
        run(g, 2000);
        const Building& m = *g.buildings().get(market);
        std::int32_t stock = 0;
        for (const Stock& s : m.stock) {
            stock += s.amount;
        }
        CHECK(stock > 0);
    }
}
