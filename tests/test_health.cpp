#include <doctest.h>

#include <map>
#include <memory>
#include <optional>
#include <ostream>

#include "sim/game.h"
#include "sim/worldgen.h"
#include "test_util.h"

using namespace sc::sim;

namespace {

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

GameSetup setup(Threat diseases = Threat::None, Threat fires = Threat::None) {
    GameSetup s;
    s.seed = 13;
    s.rules.climate.seasons = 0b0010;  // Summer.
    s.rules.diseases = diseases;
    s.rules.fires = fires;
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

// Places `def` near (x0, z0), or near the town center.
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
    const EntityId id = place(g, def, x0, z0);
    for (int t = 0; t < 80 && g.buildings().get(id)->state != BuildingState::Complete; ++t) {
        run(g, 100);
    }
    REQUIRE(g.buildings().get(id)->state == BuildingState::Complete);
    return id;
}

void ignite(Game& g, EntityId id) {
    Command c;
    c.type = CommandType::DevIgnite;
    c.entity = id;
    g.apply(c);
}

}  // namespace

TEST_SUITE("health") {
    TEST_CASE("threat levels round-trip in the rules") {
        GameRules r;
        CHECK(r.diseases == Threat::Medium);
        CHECK(r.fires == Threat::Medium);
        r.diseases = Threat::Brutal;
        r.fires = Threat::None;
        BinaryWriter w;
        r.write(w);
        GameRules back;
        BinaryReader rd(w.bytes());
        REQUIRE(GameRules::read(rd, back));
        CHECK(back.diseases == Threat::Brutal);
        CHECK(back.fires == Threat::None);
        CHECK(threat_percent(Threat::None) == 0);
        CHECK(threat_percent(Threat::Brutal) == 400);
        // An unknown level is refused.
        std::vector<std::uint8_t> bytes = w.bytes();
        bytes[bytes.size() - 2] = 9;
        BinaryReader bad(bytes);
        CHECK_FALSE(GameRules::read(bad, back));
    }

    TEST_CASE("a building with no well nearby burns down") {
        Game g(core(), map_for(71), setup());
        const EntityId shed = build(g, "core:woodcutter");
        ignite(g, shed);
        CHECK(g.buildings().get(shed)->fire > 0);
        CHECK(g.fires() == 1);
        bool started = false;
        for (const Game::Event& e : g.take_events()) {
            started = started || (e.kind == Game::Event::Kind::FireStarted && e.entity == shed);
        }
        CHECK(started);
        run(g, 3000);
        CHECK(g.buildings().get(shed) == nullptr);
        CHECK(g.player(0).burned_down >= 1);
        CHECK(g.fires() == 0);
    }

    TEST_CASE("villagers put a fire out when a well is close") {
        Game g(core(), map_for(72), setup());
        const EntityId shed = build(g, "core:woodcutter");
        const Building* b = g.buildings().get(shed);
        (void)build(g, "core:well", b->x, b->z);
        ignite(g, shed);
        REQUIRE(g.fires() == 1);
        bool fighting = false;
        for (int t = 0; t < 30 && g.fires() > 0; ++t) {
            run(g, 50);
            for (const Villager& v : g.villagers().data()) {
                fighting = fighting || v.task == Task::FightFire;
            }
        }
        CHECK(fighting);
        CHECK(g.fires() == 0);
        REQUIRE(g.buildings().get(shed) != nullptr);
        CHECK(g.buildings().get(shed)->fire == 0);
        CHECK(g.buildings().get(shed)->burned > 0);  // Scorched but standing.
    }

    TEST_CASE("wells and stone buildings do not burn") {
        Game g(core(), map_for(73), setup());
        const EntityId well = build(g, "core:well");
        ignite(g, well);
        CHECK(g.buildings().get(well)->fire == 0);
        CHECK(g.fires() == 0);
    }

    TEST_CASE("the dev fire needs the developer tools") {
        Game g(core(), map_for(74), setup());
        const EntityId shed = build(g, "core:woodcutter");
        g.set_dev_commands(false);
        const auto before = g.rejected_commands();
        ignite(g, shed);
        CHECK(g.rejected_commands() == before + 1);
        CHECK(g.fires() == 0);
    }

    TEST_CASE("fires spread to buildings close by") {
        Game g(core(), map_for(75), setup());
        const EntityId a = build(g, "core:woodcutter");
        const Building* b = g.buildings().get(a);
        const EntityId near = build(g, "core:house", b->x + b->width + 2, b->z);
        ignite(g, a);
        bool spread = false;
        for (int t = 0; t < 40 && !spread; ++t) {
            run(g, 50);
            const Building* h = g.buildings().get(near);
            spread = h == nullptr || h->fire > 0 || h->burned > 0;
        }
        CHECK(spread);
    }

    TEST_CASE("no fires and no sickness when the threats are off") {
        Game g(core(), map_for(76), setup());
        run(g, 12000);
        CHECK(g.player(0).burned_down == 0);
        CHECK(g.fires() == 0);
        for (const Villager& v : g.villagers().data()) {
            CHECK(v.disease == 0);
        }
    }

    TEST_CASE("cold without clothes or heat brings flu, which passes") {
        GameSetup s = setup(Threat::Brutal);
        s.rules.climate.seasons = 0b1000;  // Always winter.
        s.rules.climate.winter = Harshness::Harsh;
        Game g(core(), map_for(77), s);
        std::int32_t most = 0;
        bool outbreak = false;
        bool recovered = false;
        for (int t = 0; t < 40; ++t) {
            run(g, 100);
            most = std::max(most, g.sick(0));
            for (const Game::Event& e : g.take_events()) {
                outbreak = outbreak || e.kind == Game::Event::Kind::Outbreak;
            }
            for (const Villager& v : g.villagers().data()) {
                recovered = recovered || v.immune_days > 0;
            }
        }
        MESSAGE("most sick at once " << most << ", people " << g.villagers().size());
        CHECK(most > 0);
        CHECK(outbreak);
        CHECK(recovered);
    }

    TEST_CASE("a healer's hut covers the homes around it") {
        Game g(core(), map_for(79), setup());
        const EntityId house = build(g, "core:house");
        const Building* h = g.buildings().get(house);
        (void)build(g, "core:healer", h->x, h->z);
        grant(g, "core:herbs", 20);
        run(g, 1500);
        const Building* after = g.buildings().get(house);
        REQUIRE(after != nullptr);
        CHECK(((after->needs >> static_cast<unsigned>(Need::Healer)) & 1u) != 0);
    }

    TEST_CASE("fire and sickness survive a save") {
        GameSetup s = setup(Threat::Brutal, Threat::Medium);
        s.rules.climate.seasons = 0b1000;
        Game g(core(), map_for(78), s);
        const EntityId shed = build(g, "core:woodcutter");
        ignite(g, shed);
        run(g, 600);
        BinaryWriter w;
        g.save(w);
        Game back(core(), map_for(78), setup());
        BinaryReader r(w.bytes());
        REQUIRE(back.load(r, core()));
        CHECK(back.hash() == g.hash());
        CHECK(back.fires() == g.fires());
        CHECK(back.sick(0) == g.sick(0));
        run(g, 1000);
        run(back, 1000);
        CHECK(back.hash() == g.hash());
    }
}
