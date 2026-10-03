#include <doctest.h>

#include <cmath>
#include <map>
#include <memory>
#include <optional>
#include <ostream>

#include "game/animal_motion.h"
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

GameSetup setup(Threat raiders = Threat::None, Threat wildlife = Threat::Medium) {
    GameSetup s;
    s.seed = 15;
    s.rules.climate.seasons = 0b0010;  // Summer.
    s.rules.diseases = Threat::None;
    s.rules.fires = Threat::None;
    s.rules.raiders = raiders;
    s.rules.wildlife = wildlife;
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

EntityId place(Game& g, const char* def, int x0, int z0) {
    const DefIndex d = g.content().find_building(def);
    REQUIRE(d != kNoDef);
    for (int r = 0; r < 60; r += 2) {
        for (int a = 0; a < 8; ++a) {
            const int x = x0 + (a % 3 - 1) * r;
            const int z = z0 + (a / 3 - 1) * r;
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

EntityId build(Game& g, const char* def, int x0, int z0) {
    grant(g, "core:log", 200);
    grant(g, "core:stone", 100);
    const EntityId id = place(g, def, x0, z0);
    for (int t = 0; t < 80 && g.buildings().get(id)->state != BuildingState::Complete; ++t) {
        run(g, 100);
    }
    REQUIRE(g.buildings().get(id)->state == BuildingState::Complete);
    return id;
}

std::int32_t count(const Game& g, CreatureKind kind) {
    std::int32_t n = 0;
    for (const Creature& a : g.creatures().data()) {
        n += a.kind == kind ? 1 : 0;
    }
    return n;
}

void raid_now(Game& g) {
    Command c;
    c.type = CommandType::DevRaid;
    g.apply(c);
}

}  // namespace

TEST_SUITE("wildlife") {
    TEST_CASE("threat levels for raiders and wildlife round-trip") {
        GameRules r;
        CHECK(r.raiders == Threat::Medium);
        CHECK(r.wildlife == Threat::Medium);
        r.raiders = Threat::High;
        r.wildlife = Threat::None;
        BinaryWriter w;
        r.write(w);
        GameRules back;
        BinaryReader rd(w.bytes());
        REQUIRE(GameRules::read(rd, back));
        CHECK(back.raiders == Threat::High);
        CHECK(back.wildlife == Threat::None);
    }

    TEST_CASE("animals live in their zones, and no dens by the town") {
        Game g(core(), map_for(91), setup());
        std::int32_t expected = 0;
        for (const std::int32_t n : g.zone_animals()) {
            expected += n;
        }
        CHECK(static_cast<std::int32_t>(g.creatures().size()) == expected);
        CHECK(count(g, CreatureKind::Deer) > 0);
        for (std::size_t z = 0; z < g.map().zones.size(); ++z) {
            if (!g.zone_open(z)) {
                CHECK(g.zone_animals()[z] == 0);
            }
        }
        run(g, 3000);
        // Still around their zones.
        for (const Creature& a : g.creatures().data()) {
            const Zone& zone = g.map().zones[a.zone];
            const std::int64_t dx = (a.position.x - zone.x).floor_int();
            const std::int64_t dz = (a.position.z - zone.z).floor_int();
            const std::int64_t reach = zone.radius.floor_int() + 60;
            CHECK(dx * dx + dz * dz <= reach * reach);
        }
    }

    TEST_CASE("without dangerous wildlife there are no wolves or bears") {
        Game g(core(), map_for(91), setup(Threat::None, Threat::None));
        CHECK(count(g, CreatureKind::Wolf) == 0);
        CHECK(count(g, CreatureKind::Bear) == 0);
        CHECK(count(g, CreatureKind::Deer) > 0);
    }

    TEST_CASE("gates let villagers through and stop raiders") {
        Game g(core(), map_for(92), setup());
        const Building* tc = g.buildings().get(g.player(0).town_center);
        const int tx = tc->x;  // Building more moves the buildings in memory.
        const int tz = tc->z;
        const EntityId gate = build(g, "core:gate", tx + 20, tz);
        const EntityId wall = build(g, "core:palisade", tx - 20, tz);
        const Building* gb = g.buildings().get(gate);
        const Building* wb = g.buildings().get(wall);
        const std::int32_t gx = (gb->x + 1) / 2;
        const std::int32_t gz = (gb->z + 1) / 2;
        CHECK(g.nav().walkable(gx, gz));
        CHECK(g.nav().obstacle(gx, gz));
        CHECK_FALSE(g.nav().walkable((wb->x + 1) / 2, (wb->z + 1) / 2));
        CHECK(g.nav().obstacle((wb->x + 1) / 2, (wb->z + 1) / 2));
    }

    TEST_CASE("raiders come, rob and go; the bell sends the militia") {
        Game g(core(), map_for(93), setup(Threat::Medium));
        const auto rejected = g.rejected_commands();
        raid_now(g);
        CHECK(g.rejected_commands() == rejected);
        bool started = false;
        for (const Game::Event& e : g.take_events()) {
            started = started || e.kind == Game::Event::Kind::RaidStarted;
        }
        REQUIRE(started);
        const std::int32_t raiders = count(g, CreatureKind::Raider);
        CHECK(raiders >= 2);
        CHECK(g.raiders_near(0) == raiders);
        CHECK(g.player(0).raids == 1);
        // The bell.
        Command bell;
        bell.type = CommandType::RingBell;
        bell.value = 1;
        g.apply(bell);
        CHECK(g.player(0).alarm);
        bool fighting = false;
        std::int32_t least = raiders;
        for (int t = 0; t < 60 && count(g, CreatureKind::Raider) > 0; ++t) {
            run(g, 100);
            for (const Villager& v : g.villagers().data()) {
                fighting = fighting || v.task == Task::Fight || v.task == Task::GoFight;
            }
            least = std::min(least, count(g, CreatureKind::Raider));
        }
        MESSAGE("raiders " << raiders << ", left at the end " << count(g, CreatureKind::Raider) << ", people "
                           << g.population(0) << ", deaths " << g.player(0).deaths);
        CHECK(fighting);
        CHECK(count(g, CreatureKind::Raider) == 0);  // Beaten or gone home.
        bell.value = 0;
        g.apply(bell);
        CHECK_FALSE(g.player(0).alarm);
    }

    TEST_CASE("a watchtower shoots raiders") {
        Game g(core(), map_for(94), setup(Threat::Medium));
        const Building* tc = g.buildings().get(g.player(0).town_center);
        (void)build(g, "core:watchtower", tc->x + 8, tc->z + 8);
        raid_now(g);
        std::int32_t hurt = 0;
        for (int t = 0; t < 60 && hurt == 0; ++t) {
            run(g, 50);
            for (const Creature& a : g.creatures().data()) {
                hurt += a.kind == CreatureKind::Raider && a.health < 400 ? 1 : 0;
            }
        }
        CHECK(hurt > 0);
    }

    TEST_CASE("raids come on their own after the year of grace") {
        Game g(core(), map_for(95), setup(Threat::Brutal));
        bool raided = false;
        for (int t = 0; t < 200 && !raided; ++t) {
            run(g, 100);
            for (const Game::Event& e : g.take_events()) {
                raided = raided || e.kind == Game::Event::Kind::RaidStarted;
            }
        }
        CHECK(raided);
        CHECK(g.tick() >= g.year_ticks());
    }

    TEST_CASE("the dev raid needs the developer tools") {
        Game g(core(), map_for(93), setup());
        g.set_dev_commands(false);
        const auto rejected = g.rejected_commands();
        raid_now(g);
        CHECK(g.rejected_commands() == rejected + 1);
        CHECK(count(g, CreatureKind::Raider) == 0);
    }

    TEST_CASE("animals and raiders survive a save") {
        Game g(core(), map_for(93), setup(Threat::Medium));
        raid_now(g);
        run(g, 400);
        REQUIRE(count(g, CreatureKind::Raider) > 0);
        BinaryWriter w;
        g.save(w);
        Game back(core(), map_for(91), setup());
        BinaryReader r(w.bytes());
        REQUIRE(back.load(r, core()));
        CHECK(back.hash() == g.hash());
        CHECK(back.creatures().size() == g.creatures().size());
        run(g, 800);
        run(back, 800);
        CHECK(back.hash() == g.hash());
    }

    TEST_CASE("an animal's clip follows its speed and its feet do not slide") {
        namespace am = sc::animal_motion;
        am::Clips c;
        c.idle = 0, c.walk = 1, c.run = 2, c.eat = 3;
        c.walk_speed = 1.2f, c.run_speed = 6.0f;
        c.idle_length = 3.0f, c.walk_length = 0.6f, c.run_length = 0.33f, c.eat_length = 3.0f;
        // At any speed the clip advances by distance / clip speed: the feet
        // move back exactly as fast as the animal moves forward.
        for (const float v : {0.3f, 0.83f, 1.0f, 1.8f, 1.81f, 2.6f, 3.2f, 6.0f, 9.0f}) {
            am::State s;
            am::advance(c, s, v, 0.0f, 0.0f, 7);
            const float clip_speed = s.clip == c.run ? c.run_speed : c.walk_speed;
            const float length = s.clip == c.run ? c.run_length : c.walk_length;
            CHECK(s.clip == (v > c.walk_speed * am::kRunAbove ? c.run : c.walk));
            const float dt = 0.01f;
            const float before = s.time;
            am::advance(c, s, v, dt, dt, 7);
            CHECK(std::fmod(s.time - before + length, length) * clip_speed == doctest::Approx(v * dt).epsilon(0.001));
        }
        // Paused: frozen.
        am::State s;
        am::advance(c, s, 1.0f, 0.2f, 0.0f, 7);
        const float t = s.time;
        am::advance(c, s, 1.0f, 0.0f, 0.0f, 7);
        CHECK(s.time == t);
        // Walk to run keeps the point of the stride.
        am::advance(c, s, 4.0f, 0.0f, 0.0f, 7);
        CHECK(s.clip == c.run);
        CHECK(s.time / c.run_length == doctest::Approx(t / c.walk_length));
    }

    TEST_CASE("a standing animal idles and grazes, taking turns at the end of each loop") {
        namespace am = sc::animal_motion;
        am::Clips c;
        c.idle = 0, c.walk = 1, c.run = 2, c.eat = 3;
        c.idle_length = 3.0f, c.eat_length = 2.0f;
        int idle = 0, eat = 0;
        for (std::uint32_t seed = 0; seed < 50; ++seed) {
            am::State s;
            am::advance(c, s, 2.0f, 0.1f, 0.1f, seed);  // Was walking.
            std::uint32_t last = s.clip;
            for (int f = 0; f < 600; ++f) {
                am::advance(c, s, 0.0f, 0.05f, 0.05f, seed);
                REQUIRE((s.clip == c.idle || s.clip == c.eat));
                CHECK(s.time >= 0.0f);
                CHECK(s.time < (s.clip == c.idle ? c.idle_length : c.eat_length));
                if (s.clip != last || f == 0) {
                    (s.clip == c.idle ? idle : eat) += 1;
                }
                last = s.clip;
            }
            // The same animal does the same.
            am::State a, b;
            for (int f = 0; f < 300; ++f) {
                am::advance(c, a, 0.0f, 0.05f, 0.05f, seed);
                am::advance(c, b, 0.0f, 0.05f, 0.05f, seed);
            }
            CHECK(a.clip == b.clip);
            CHECK(a.time == b.time);
        }
        CHECK(idle > 0);
        CHECK(eat > idle);
    }
}
