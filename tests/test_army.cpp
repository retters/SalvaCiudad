#include <doctest.h>

#include <map>
#include <memory>
#include <optional>
#include <ostream>
#include <tuple>

#include "sim/game.h"
#include "sim/worldgen.h"
#include "test_util.h"

using namespace sc::sim;

namespace {

// Everything available from the start (the barracks needs level 2).
std::shared_ptr<const Content> open_content() {
    static const std::shared_ptr<const Content> c = [] {
        auto copy = std::make_shared<Content>(sc::test::core_content());
        for (BuildingDef& b : copy->buildings) {
            b.tier = 0;
        }
        for (UnitDef& u : copy->units) {
            u.tier = 0;
        }
        return copy;
    }();
    return c;
}

const MapData& map_for(std::uint64_t seed, std::uint8_t players = 1, bool separate = false) {
    static std::map<std::tuple<std::uint64_t, std::uint8_t, bool>, MapData> cache;
    const auto key = std::make_tuple(seed, players, separate);
    auto it = cache.find(key);
    if (it == cache.end()) {
        MapSettings s;
        s.seed = seed;
        s.size = MapSize::Small;
        s.sea = Sea::None;  // Armies on land (islands have their own maps).
        s.players = players;
        s.separate = separate;
        std::optional<MapData> m = generate_map(s, sc::test::core_content());
        REQUIRE(m.has_value());
        it = cache.emplace(key, std::move(*m)).first;
    }
    return it->second;
}

// Phase 22: a medium map of islands, one per town.
const MapData& islands_for(std::uint64_t seed, std::uint8_t players) {
    static std::map<std::pair<std::uint64_t, std::uint8_t>, MapData> cache;
    const auto key = std::make_pair(seed, players);
    auto it = cache.find(key);
    if (it == cache.end()) {
        MapSettings s;
        s.seed = seed;
        s.size = MapSize::Medium;
        s.players = players;
        s.islands = 1;
        s.map_type = static_cast<std::uint8_t>(sc::test::core_content().flora.find_map_type("core:islands"));
        std::optional<MapData> m = generate_map(s, sc::test::core_content());
        REQUIRE(m.has_value());
        it = cache.emplace(key, std::move(*m)).first;
    }
    return it->second;
}

GameSetup setup(std::uint8_t players = 1) {
    GameSetup s;
    s.players = players;
    s.seed = 16;
    s.rules.climate.seasons = 0b0010;  // Summer.
    s.rules.diseases = Threat::None;
    s.rules.fires = Threat::None;
    s.rules.raiders = Threat::None;
    s.rules.wildlife = Threat::None;
    return s;
}

GameSetup versus(Victory victory, bool pvp = true) {
    GameSetup s = setup(2);
    s.rules.versus = true;
    s.rules.pvp = pvp;
    s.rules.victory = victory;
    return s;
}

void run(Game& g, std::uint32_t ticks) {
    for (std::uint32_t i = 0; i < ticks; ++i) {
        g.step();
    }
}

void grant(Game& g, const char* resource, std::int32_t amount, std::uint8_t player = 0) {
    Command c;
    c.type = CommandType::DevGrant;
    c.player = player;
    c.def = g.content().find_resource(resource);
    REQUIRE(c.def != kNoDef);
    c.value = amount;
    g.apply(c);
}

EntityId build(Game& g, const char* def, std::uint8_t player = 0) {
    grant(g, "core:log", 200, player);
    grant(g, "core:stone", 100, player);
    const DefIndex d = g.content().find_building(def);
    REQUIRE(d != kNoDef);
    const Building* tc = g.buildings().get(g.player(player).town_center);
    REQUIRE(tc != nullptr);
    const int ox = tc->x;
    const int oz = tc->z;
    for (int r = 12; r < 140; r += 2) {
        for (int a = 0; a < 8; ++a) {
            const int x = ox + (a % 3 - 1) * r;
            const int z = oz + (a / 3 - 1) * r;
            if (g.can_place(player, d, x, z, 0) != PlaceError::None) {
                continue;
            }
            Command c;
            c.type = CommandType::PlaceBuilding;
            c.player = player;
            c.def = d;
            c.position = {Fixed::from_int(x), Fixed::from_int(z)};
            g.apply(c);
            EntityId id;
            for (std::size_t i = 0; i < g.buildings().size(); ++i) {
                const Building& b = g.buildings().data()[i];
                if (b.def == d && b.x == x && b.z == z) {
                    id = g.buildings().entities()[i];
                }
            }
            REQUIRE(id.valid());
            for (int t = 0; t < 80 && g.buildings().get(id)->state != BuildingState::Complete; ++t) {
                run(g, 100);
            }
            REQUIRE(g.buildings().get(id)->state == BuildingState::Complete);
            return id;
        }
    }
    FAIL("no room for " << def);
    return {};
}

void train(Game& g, EntityId barracks, const char* unit, int n, std::uint8_t player = 0) {
    DefIndex u = kNoDef;
    for (std::size_t i = 0; i < g.content().units.size(); ++i) {
        u = g.content().units[i].id == unit ? static_cast<DefIndex>(i) : u;
    }
    REQUIRE(u != kNoDef);
    for (int k = 0; k < n; ++k) {
        Command c;
        c.type = CommandType::TrainUnit;
        c.player = player;
        c.entity = barracks;
        c.def = u;
        c.value = 1;
        g.apply(c);
    }
}

Command order(std::uint8_t player, ArmyOrderKind kind, std::uint8_t enemy = 0) {
    Command c;
    c.type = CommandType::ArmyOrder;
    c.player = player;
    c.value = static_cast<std::int32_t>(kind);
    c.count = enemy;
    return c;
}

}  // namespace

TEST_SUITE("army") {
    TEST_CASE("versus rules round-trip") {
        GameRules r;
        CHECK_FALSE(r.versus);
        r.versus = true;
        r.pvp = false;
        r.victory = Victory::Score;
        r.score_years = 7;
        BinaryWriter w;
        r.write(w);
        GameRules back;
        BinaryReader rd(w.bytes());
        REQUIRE(GameRules::read(rd, back));
        CHECK(back.versus);
        CHECK_FALSE(back.pvp);
        CHECK(back.victory == Victory::Score);
        CHECK(back.score_years == 7);
    }

    TEST_CASE("core has units, and a barracks turns villagers into soldiers") {
        REQUIRE(sc::test::core_content().units.size() >= 3);
        Game g(open_content(), map_for(101), setup());
        const EntityId barracks = build(g, "core:barracks");
        grant(g, "core:log", 30);
        const std::int32_t people = g.population(0);
        const std::int32_t deaths = g.player(0).deaths;
        train(g, barracks, "core:levy", 2);
        CHECK(g.buildings().get(barracks)->training.size() == 2);
        bool trained = false;
        for (int t = 0; t < 20 && g.soldiers(0) < 2; ++t) {
            run(g, 100);
            for (const Game::Event& e : g.take_events()) {
                trained = trained || e.kind == Game::Event::Kind::UnitTrained;
            }
        }
        CHECK(trained);
        CHECK(g.soldiers(0) == 2);
        CHECK(g.population(0) <= people - 2 + 1);  // A birth could come meanwhile.
        CHECK(g.player(0).deaths == deaths);
        CHECK(g.military_power(0) == 4);
        CHECK(g.score(0) > 0);
        // Cancelling: the last one leaves the line.
        train(g, barracks, "core:levy", 2);
        Command cancel;
        cancel.type = CommandType::TrainUnit;
        cancel.entity = barracks;
        cancel.value = 0;
        g.apply(cancel);
        CHECK(g.buildings().get(barracks)->training.size() == 1);
    }

    TEST_CASE("soldiers defend the town from raiders") {
        GameSetup s = setup();
        s.rules.raiders = Threat::Medium;
        Game g(open_content(), map_for(102), s);
        const EntityId barracks = build(g, "core:barracks");
        grant(g, "core:log", 60);
        train(g, barracks, "core:levy", 4);
        for (int t = 0; t < 30 && g.soldiers(0) < 4; ++t) {
            run(g, 100);
        }
        REQUIRE(g.soldiers(0) == 4);
        Command raid;
        raid.type = CommandType::DevRaid;
        g.apply(raid);
        REQUIRE(g.raiders_near(0) > 0);
        for (int t = 0; t < 60 && g.raiders_near(0) > 0; ++t) {
            run(g, 100);
        }
        CHECK(g.raiders_near(0) == 0);
    }

    TEST_CASE("in a cooperative game armies do not attack players") {
        Game g(open_content(), map_for(103, 2), setup(2));
        REQUIRE(g.player_count() == 2);
        CHECK_FALSE(g.enemies(0, 1));
        const auto rejected = g.rejected_commands();
        g.apply(order(0, ArmyOrderKind::Attack, 1));
        CHECK(g.rejected_commands() == rejected + 1);
    }

    TEST_CASE("versus: bringing down the rival town center wins") {
        Game g(open_content(), map_for(103, 2), versus(Victory::Elimination));
        REQUIRE(g.enemies(0, 1));
        const EntityId barracks = build(g, "core:barracks");
        grant(g, "core:log", 100);
        train(g, barracks, "core:levy", 6);
        for (int t = 0; t < 40 && g.soldiers(0) < 6; ++t) {
            run(g, 100);
        }
        REQUIRE(g.soldiers(0) == 6);
        g.apply(order(0, ArmyOrderKind::Attack, 1));
        CHECK(g.player(0).order == ArmyOrderKind::Attack);
        bool over = false;
        for (int t = 0; t < 120 && !g.game_over(); ++t) {
            run(g, 100);
            for (const Game::Event& e : g.take_events()) {
                over = over || (e.kind == Game::Event::Kind::GameOver && e.value == 1);
            }
        }
        CHECK(g.game_over());
        CHECK(over);
        CHECK(g.player(0).outcome == Outcome::Won);
        CHECK(g.player(1).outcome == Outcome::Lost);
        CHECK(g.buildings().get(g.player(1).town_center) == nullptr);
    }

    TEST_CASE("versus without war: the best score after the years wins") {
        GameSetup s = versus(Victory::Score, false);
        s.rules.score_years = 1;
        Game g(open_content(), map_for(103, 2), s);
        CHECK_FALSE(g.enemies(0, 1));
        grant(g, "core:log", 500, 1);  // Player 1 is richer: more buildings to come.
        (void)build(g, "core:storehouse", 1);
        run(g, g.year_ticks() + g.month_ticks());
        CHECK(g.game_over());
        CHECK((g.player(0).outcome == Outcome::Won) != (g.player(1).outcome == Outcome::Won));
    }

    TEST_CASE("with separate maps an army travels over the world map") {
        Game g(open_content(), map_for(104, 2, true), versus(Victory::Elimination));
        const EntityId barracks = build(g, "core:barracks");
        grant(g, "core:log", 30);
        train(g, barracks, "core:levy", 1);
        for (int t = 0; t < 20 && g.soldiers(0) < 1; ++t) {
            run(g, 100);
        }
        REQUIRE(g.soldiers(0) == 1);
        g.apply(order(0, ArmyOrderKind::Attack, 1));
        run(g, 20);
        const auto soldier = [&]() -> const Creature* {
            for (const Creature& a : g.creatures().data()) {
                if (a.kind == CreatureKind::Soldier) {
                    return &a;
                }
            }
            return nullptr;
        };
        REQUIRE(soldier() != nullptr);
        CHECK(soldier()->state == CreatureState::Travel);
        run(g, static_cast<std::uint32_t>(g.travel_ticks(0, 1)) + 20);
        REQUIRE(soldier() != nullptr);
        CHECK(soldier()->state != CreatureState::Travel);
        CHECK(g.map().region_at(soldier()->position.x.floor_int(), soldier()->position.z.floor_int()) == 1);
    }

    TEST_CASE("on islands an army crosses the sea to the rival's island") {
        Game g(open_content(), islands_for(106, 2), versus(Victory::Elimination));
        const Building* rival = g.buildings().get(g.player(1).town_center);
        REQUIRE(rival != nullptr);
        const FixedVec2 rival_door = g.door(*rival);
        REQUIRE_FALSE(g.nav().same_land(g.door(*g.buildings().get(g.player(0).town_center)), rival_door));
        const EntityId barracks = build(g, "core:barracks");
        grant(g, "core:log", 30);
        train(g, barracks, "core:levy", 1);
        for (int t = 0; t < 20 && g.soldiers(0) < 1; ++t) {
            run(g, 100);
        }
        REQUIRE(g.soldiers(0) == 1);
        g.apply(order(0, ArmyOrderKind::Attack, 1));
        run(g, 20);
        const auto soldier = [&]() -> const Creature* {
            for (const Creature& a : g.creatures().data()) {
                if (a.kind == CreatureKind::Soldier) {
                    return &a;
                }
            }
            return nullptr;
        };
        REQUIRE(soldier() != nullptr);
        CHECK(soldier()->state == CreatureState::Travel);
        run(g, static_cast<std::uint32_t>(g.travel_ticks(0, 1)) + 20);
        REQUIRE(soldier() != nullptr);
        CHECK(soldier()->state != CreatureState::Travel);
        CHECK(g.nav().same_land(soldier()->position, rival_door));
    }

    TEST_CASE("on islands raiders land on the coast") {
        GameSetup s = setup();
        s.rules.raiders = Threat::Medium;
        Game g(open_content(), islands_for(107, 1), s);
        grant(g, "core:log", 2000);  // Something worth taking.
        Command raid;
        raid.type = CommandType::DevRaid;
        g.apply(raid);
        const Building* tc = g.buildings().get(g.player(0).town_center);
        REQUIRE(tc != nullptr);
        int raiders = 0;
        for (const Creature& a : g.creatures().data()) {
            if (a.kind == CreatureKind::Raider) {
                ++raiders;
                CHECK(g.nav().same_land(a.position, g.door(*tc)));
            }
        }
        CHECK(raiders > 0);
    }

    TEST_CASE("a single-player town that dies out ends the game") {
        Game g(open_content(), map_for(105), setup());
        run(g, 40000);  // Nobody builds: the berries run out.
        CHECK(g.population(0) == 0);
        CHECK(g.game_over());
        CHECK(g.player(0).outcome == Outcome::Lost);
    }

    TEST_CASE("armies and training survive a save") {
        Game g(open_content(), map_for(103, 2), versus(Victory::Elimination));
        const EntityId barracks = build(g, "core:barracks");
        grant(g, "core:log", 60);
        train(g, barracks, "core:levy", 3);
        for (int t = 0; t < 20 && g.soldiers(0) < 1; ++t) {
            run(g, 100);
        }
        g.apply(order(0, ArmyOrderKind::Attack, 1));
        run(g, 300);
        BinaryWriter w;
        g.save(w);
        Game back(open_content(), map_for(101), setup());
        BinaryReader r(w.bytes());
        REQUIRE(back.load(r, open_content()));
        CHECK(back.hash() == g.hash());
        run(g, 800);
        run(back, 800);
        CHECK(back.hash() == g.hash());
    }
}
