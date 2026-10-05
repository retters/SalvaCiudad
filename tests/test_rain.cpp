#include <doctest.h>

#include <algorithm>
#include <filesystem>
#include <map>
#include <memory>
#include <optional>
#include <utility>
#include <vector>

#include "game/day_light.h"
#include "game/save_file.h"
#include "sim/game.h"
#include "sim/worldgen.h"
#include "test_util.h"
#include "version.h"

using namespace sc;
using namespace sc::sim;

namespace {

std::shared_ptr<const Content> core() {
    return std::shared_ptr<const Content>(std::shared_ptr<const Content>{}, &test::core_content());
}

const MapData& map_for(std::uint64_t seed) {
    static std::map<std::uint64_t, MapData> cache;
    auto it = cache.find(seed);
    if (it == cache.end()) {
        MapSettings s;
        s.seed = seed;
        s.size = MapSize::Small;
        s.sea = Sea::None;
        std::optional<MapData> m = generate_map(s, test::core_content());
        REQUIRE(m.has_value());
        it = cache.emplace(seed, std::move(*m)).first;
    }
    return it->second;
}

// A quiet game in one season (a Season bit; 0b1111: the usual year), with so much rain.
GameSetup setup(std::uint8_t rain, std::uint8_t seasons = 0b0010) {
    GameSetup s;
    s.seed = 15;
    s.rules.climate.seasons = seasons;
    s.rules.diseases = Threat::None;
    s.rules.fires = Threat::None;
    s.rules.raiders = Threat::None;
    s.rules.wildlife = Threat::None;
    s.rules.rain = rain;
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

void provide(Game& g) {
    grant(g, "core:log", 2000);
    grant(g, "core:stone", 500);
    for (const char* food : {"core:bread", "core:meat", "core:vegetables", "core:fruit"}) {
        grant(g, food, 3000);
    }
}

DefIndex building(const Game& g, const char* id) {
    const DefIndex d = g.content().find_building(id);
    REQUIRE(d != kNoDef);
    return d;
}

void finish_all(Game& g) {
    Command c;
    c.type = CommandType::DevBuild;
    g.apply(c);
}

EntityId place(Game& g, const char* def, std::int32_t x, std::int32_t z) {
    Command c;
    c.type = CommandType::PlaceBuilding;
    c.def = building(g, def);
    c.position = {Fixed::from_int(x), Fixed::from_int(z)};
    g.apply(c);
    for (std::size_t i = 0; i < g.buildings().size(); ++i) {
        const Building& b = g.buildings().data()[i];
        if (b.def == c.def && b.x == x && b.z == z) {
            return g.buildings().entities()[i];
        }
    }
    return {};
}

// The corner of a square of `side` x `side` cells near the town center where a
// stretch of road fits on every module.
std::pair<std::int32_t, std::int32_t> open_ground(const Game& g, std::int32_t side) {
    const DefIndex road = building(g, "core:dirt_road");
    const Building* tc = g.buildings().get(g.player(0).town_center);
    REQUIRE(tc != nullptr);
    for (std::int32_t r = 12; r < 200; r += 4) {
        for (const auto& [dx, dz] : {std::pair{r, 0}, std::pair{-r, 0}, std::pair{0, r}, std::pair{0, -r}, std::pair{r, r},
                                     std::pair{-r, -r}, std::pair{r, -r}, std::pair{-r, r}}) {
            const std::int32_t x0 = ((tc->x + dx) / 2) * 2, z0 = ((tc->z + dz) / 2) * 2;
            bool free = true;
            for (std::int32_t z = z0; z < z0 + side && free; z += 2) {
                for (std::int32_t x = x0; x < x0 + side && free; x += 2) {
                    free = g.can_place(0, road, x, z, 0) == PlaceError::None;
                }
            }
            if (free) {
                return {x0, z0};
            }
        }
    }
    FAIL("no open ground near the town");
    return {0, 0};
}

// The share of the days of some years that are wet, among those that do not freeze, percent.
int wet_share(const GameRules& rules, std::uint8_t humidity, std::uint64_t seed, int years) {
    const std::uint64_t day_ticks = year_ticks(rules.climate) / kDaysPerYear;
    const std::uint64_t days = static_cast<std::uint64_t>(years) * kDaysPerYear;
    int mild = 0, wet = 0;
    for (std::uint64_t day = 0; day < days; ++day) {
        if (temperature(rules.climate, seed, day * day_ticks) < 0) {
            continue;
        }
        ++mild;
        wet += wet_day(rules.climate, rules.rain, humidity, seed, day) ? 1 : 0;
    }
    REQUIRE(mild > 0);
    return wet * 100 / mild;
}

// A 24 m stretch with `road` (if any) along the row beside it. When a day of
// rain begins (or a dry day after a dry one, with another to come), an
// explorer goes to one end and walks to the other: how many ticks the walk
// takes. The days are long here (600 ticks), so the weather lasts through
// it, and it is summer.
int crossing(const char* road, bool in_the_rain) {
    GameSetup rules = setup(200, 0b1111);
    rules.rules.climate.minutes = {30, 30, 30, 30};
    Game g(core(), map_for(92), rules);
    provide(g);
    Command level;
    level.type = CommandType::DevLevel;
    g.apply(level);
    const auto [x0, z0] = open_ground(g, 48);
    // (The hut well away from the stretch: an order to a point by its door means "come home".)
    EntityId post;
    for (std::int32_t dz = 36; dz < 44 && !post.valid(); dz += 2) {
        if (g.can_place(0, building(g, "core:explorer"), x0 + 20, z0 + dz, 0) == PlaceError::None) {
            post = place(g, "core:explorer", x0 + 20, z0 + dz);
        }
    }
    REQUIRE(post.valid());
    if (road != nullptr) {
        Command c;
        c.type = CommandType::Trace;
        c.def = building(g, road);
        c.position = {Fixed::from_int(x0 + 4), Fixed::from_int(z0 + 12)};
        c.value = x0 + 24;
        c.value2 = z0 + 12;
        g.apply(c);
    }
    finish_all(g);
    REQUIRE(g.roads().size() == (road != nullptr ? 11u : 0u));
    for (int t = 0; t < 400 && g.buildings().get(post)->workers.empty(); ++t) {
        run(g, 10);
    }
    REQUIRE(g.buildings().get(post)->workers.size() == 1);
    const EntityId who = g.buildings().get(post)->workers[0];
    REQUIRE(g.calendar_day_ticks() == 600);
    // On to the summer: in the cold of the first spring (1 degree) the
    // explorer does not get to its start in time.
    for (int t = 0; t < 40000 && g.calendar().season != Season::Summer; ++t) {
        g.step();
    }
    REQUIRE(g.calendar().season == Season::Summer);
    run(g, 6000);
    REQUIRE(g.temperature() >= 10);
    const auto day_begins = [&] { return g.tick() % g.calendar_day_ticks() == 0; };
    if (in_the_rain) {
        // A day of rain begins: mud today and tomorrow.
        for (int t = 0; t < 200000 && !(g.raining() && day_begins()); ++t) {
            g.step();
        }
        REQUIRE(g.raining());
    } else {
        // A dry day begins after another dry day, and tomorrow is dry too: no mud for two days.
        for (int t = 0; t < 200000 && !(!g.muddy() && !g.rained(g.calendar_day() + 1) && day_begins()); ++t) {
            g.step();
        }
        REQUIRE_FALSE(g.rained(g.calendar_day() + 1));
    }
    REQUIRE(g.muddy() == in_the_rain);
    const FixedVec2 from{Fixed::from_int(x0 + 3), Fixed::from_int(z0 + 11)};
    const FixedVec2 to{Fixed::from_int(x0 + 27), Fixed::from_int(z0 + 11)};
    const auto send = [&](FixedVec2 where) {
        Command c;
        c.type = CommandType::MoveVillager;
        c.entity = who;
        c.position = where;
        g.apply(c);
    };
    const auto at = [&](FixedVec2 where) {
        const Villager* v = g.villagers().get(who);
        if (v == nullptr) {
            return false;
        }
        const FixedVec2 d = v->position - where;
        return abs(d.x) <= Fixed::from_ratio(1, 4) && abs(d.z) <= Fixed::from_ratio(1, 4);
    };
    send(from);
    for (int t = 0; t < 900 && !at(from); ++t) {
        g.step();
    }
    REQUIRE(at(from));
    send(to);
    int ticks = 0;
    while (ticks < 250 && !at(to)) {
        g.step();
        ++ticks;
    }
    REQUIRE(at(to));
    REQUIRE(g.muddy() == in_the_rain);  // The weather lasted.
    return ticks;
}

}  // namespace

TEST_SUITE("rain") {
    TEST_CASE("the same seed has the same days of rain, another seed has others, and with no rain there is none") {
        GameRules rules;
        rules.rain = 100;
        std::vector<bool> a, b, other;
        for (std::uint64_t day = 0; day < 240; ++day) {
            a.push_back(wet_day(rules.climate, rules.rain, 100, 77, day));
            b.push_back(wet_day(rules.climate, rules.rain, 100, 77, day));
            other.push_back(wet_day(rules.climate, rules.rain, 100, 78, day));
            CHECK_FALSE(wet_day(rules.climate, 0, 100, 77, day));
            CHECK_FALSE(wet_day(rules.climate, 0, 200, 77, day));
        }
        CHECK(a == b);
        CHECK(a != other);
        CHECK(std::count(a.begin(), a.end(), true) > 0);
        // A game says the same as the function it is made of.
        Game g(core(), map_for(92), setup(100, 0b1111));
        for (std::uint64_t day = 0; day < 240; ++day) {
            CHECK(g.wet(day) == wet_day(g.rules().climate, 100, g.map().settings.humidity, g.seed(), day));
        }
    }

    TEST_CASE("in a usual year it rains between 15 and 35 days of a hundred that do not freeze") {
        GameRules rules;
        rules.rain = 100;
        for (const std::uint64_t seed : {1ull, 7ull, 2026ull, 99991ull}) {
            const int share = wet_share(rules, 100, seed, 5);
            CAPTURE(seed);
            CHECK(share >= 15);
            CHECK(share <= 35);
        }
        // More rain in the rules, or a wetter map, is more days; a dry map, fewer.
        GameRules heavy = rules;
        heavy.rain = 200;
        CHECK(wet_share(heavy, 100, 7, 5) > wet_share(rules, 100, 7, 5) + 10);
        CHECK(wet_share(rules, 200, 7, 5) > wet_share(rules, 100, 7, 5) + 10);
        CHECK(wet_share(rules, 25, 7, 5) < wet_share(rules, 100, 7, 5) - 8);
        CHECK(wet_share(rules, 0, 7, 5) == 0);
        // Spring and autumn are the wet seasons; however much it rains, not every day.
        CHECK(rain_chance(Season::Spring, 100, 100) > rain_chance(Season::Summer, 100, 100));
        CHECK(rain_chance(Season::Autumn, 100, 100) > rain_chance(Season::Summer, 100, 100));
        CHECK(rain_chance(Season::Autumn, 200, 200) == 90);
        CHECK(rain_chance(Season::Autumn, 0, 200) == 0);
    }

    TEST_CASE("the rules carry the rain, and too much of it is refused") {
        GameRules rules;
        CHECK(rules.rain == 0);  // What the games of earlier phases have: it never rains.
        rules.rain = 125;
        BinaryWriter w;
        rules.write(w);
        BinaryReader r(w.bytes());
        GameRules back;
        REQUIRE(GameRules::read(r, back));
        CHECK(back == rules);
        CHECK(back.rain == 125);
        rules.rain = kMaxRain + 1;
        BinaryWriter bad;
        rules.write(bad);
        BinaryReader rb(bad.bytes());
        CHECK_FALSE(GameRules::read(rb, back));
    }

    TEST_CASE("a game tells whether it rains, since when it does not, and when the dirt roads are mud") {
        Game g(core(), map_for(92), setup(100, 0b1111));
        provide(g);
        const std::uint32_t day = g.calendar_day_ticks();
        int rainy = 0, snowy = 0, muddy = 0;
        for (int d = 0; d < 240; ++d) {
            const std::uint64_t today = g.calendar_day();
            CHECK(g.raining() == g.rained(today));
            CHECK(g.muddy() == (g.rained(today) || (today > 0 && g.rained(today - 1))));
            CHECK((g.days_without_rain() == 0) == g.raining());
            if (!g.raining() && today > 0) {
                CHECK(g.days_without_rain() == std::min<std::int32_t>(kMaxDryDays, g.rained(today - 1) ? 1 : g.days_without_rain()));
            }
            // What falls when it freezes is snow, and makes no mud.
            if (g.snowing()) {
                CHECK(g.wet(today));
                CHECK_FALSE(g.raining());
                CHECK(temperature(g.rules().climate, g.seed(), today * day) < 0);
            }
            rainy += g.raining() ? 1 : 0;
            snowy += g.snowing() ? 1 : 0;
            muddy += g.muddy() ? 1 : 0;
            run(g, day);
        }
        MESSAGE("of 240 days: " << rainy << " of rain, " << snowy << " of snow, " << muddy << " of mud");
        CHECK(rainy > 20);
        CHECK(snowy > 0);
        CHECK(muddy > rainy);
        // Without rain in the rules, never.
        Game dry(core(), map_for(92), setup(0, 0b1111));
        for (int d = 0; d < 240; ++d) {
            CHECK_FALSE(dry.raining());
            CHECK_FALSE(dry.snowing());
            CHECK_FALSE(dry.muddy());
            CHECK(dry.days_without_rain() == std::min<std::int32_t>(kMaxDryDays, d + 1));
            run(dry, day);
        }
    }

    TEST_CASE("under the rain a dirt road is no faster than the open ground, a cobbled street still is") {
        const int across = crossing(nullptr, true);
        const int mud = crossing("core:dirt_road", true);
        const int street = crossing("core:cobbled_street", true);
        const int dry_road = crossing("core:dirt_road", false);
        MESSAGE("ticks in the rain: across " << across << ", dirt road " << mud << ", street " << street << "; dirt road once dry "
                                             << dry_road);
        CHECK(mud == across);
        CHECK(street < across);
        CHECK(dry_road < across);
        CHECK(street < dry_road);
    }

    TEST_CASE("a fire burns a building more slowly under the rain") {
        // The same town twice: where it rains and where it never does.
        const auto burned_after = [](std::uint8_t rain, std::uint64_t at_tick, int ticks) {
            Game g(core(), map_for(92), setup(rain));
            provide(g);
            const auto [x0, z0] = open_ground(g, 16);
            const EntityId house = place(g, "core:house", x0 + 2, z0 + 2);
            REQUIRE(house.valid());
            finish_all(g);
            while (g.tick() < at_tick) {
                g.step();
            }
            Command fire;
            fire.type = CommandType::DevIgnite;
            fire.entity = house;
            g.apply(fire);
            REQUIRE(g.buildings().get(house)->fire > 0);
            for (int t = 0; t < ticks; ++t) {
                g.step();
                REQUIRE(g.buildings().get(house) != nullptr);
            }
            return std::pair{g.buildings().get(house)->burned, g.buildings().get(house)->fire};
        };
        // When a day of rain begins, in the game where it rains.
        Game probe(core(), map_for(92), setup(200));
        while (!(probe.raining() && probe.tick() % probe.calendar_day_ticks() == 0)) {
            probe.step();
            REQUIRE(probe.tick() < 100000);
        }
        const std::uint64_t start = probe.tick();
        const int ticks = static_cast<int>(probe.calendar_day_ticks()) - 10;
        const auto wet = burned_after(200, start, ticks);
        const auto dry = burned_after(0, start, ticks);
        MESSAGE("after " << ticks << " ticks: burned " << wet.first << " in the rain (fire " << wet.second << "), " << dry.first
                         << " without it (fire " << dry.second << ")");
        CHECK(wet.first > 0);
        CHECK(wet.first * 2 <= dry.first);
        CHECK(wet.second < dry.second);
    }

    TEST_CASE("saving and loading keeps the weather: it follows from the day") {
        Game g(core(), map_for(92), setup(200));
        provide(g);
        const auto [x0, z0] = open_ground(g, 24);
        Command c;
        c.type = CommandType::Trace;
        c.def = building(g, "core:dirt_road");
        c.position = {Fixed::from_int(x0), Fixed::from_int(z0)};
        c.value = x0 + 18;
        c.value2 = z0;
        g.apply(c);
        finish_all(g);
        REQUIRE(g.roads().size() == 10);
        CHECK(g.nav().road_percent(x0 / 2, z0 / 2) == (g.muddy() ? 100 : 115));
        for (int t = 0; t < 60000 && !g.muddy(); ++t) {
            g.step();
        }
        REQUIRE(g.muddy());
        run(g, 37);
        CHECK(g.nav().road_percent(x0 / 2, z0 / 2) == 100);
        BinaryWriter w;
        g.save(w);
        Game loaded(core(), map_for(92), setup(0));
        BinaryReader r(w.bytes());
        REQUIRE(loaded.load(r, core()));
        CHECK(loaded.hash() == g.hash());
        CHECK(loaded.rules().rain == 200);
        CHECK(loaded.muddy());
        CHECK(loaded.raining() == g.raining());
        CHECK(loaded.nav().road_percent(x0 / 2, z0 / 2) == 100);
        // And when the mud dries, on both.
        for (int t = 0; t < 60000 && g.muddy(); ++t) {
            g.step();
            loaded.step();
        }
        REQUIRE_FALSE(g.muddy());
        CHECK_FALSE(loaded.muddy());
        CHECK(g.nav().road_percent(x0 / 2, z0 / 2) == 115);
        CHECK(loaded.nav().road_percent(x0 / 2, z0 / 2) == 115);
        CHECK(loaded.hash() == g.hash());
    }

    TEST_CASE("the light of a rainy day: gray, dimmer, and the same light when it is clear") {
        const render::Lighting clear;
        const render::Lighting same = rain_lighting(clear, 0.0f);
        CHECK(same.sun_color.x == clear.sun_color.x);
        CHECK(same.zenith_color.z == clear.zenith_color.z);
        const render::Lighting wet = rain_lighting(clear, 1.0f);
        // The blue of the sky goes; the sun is weak and has no disc.
        CHECK(wet.zenith_color.z - wet.zenith_color.x < (clear.zenith_color.z - clear.zenith_color.x) * 0.3f);
        CHECK(wet.sun_color.x < clear.sun_color.x * 0.5f);
        CHECK(wet.disc == 0.0f);
        const render::Lighting half = rain_lighting(clear, 0.5f);
        CHECK(half.sun_color.x < clear.sun_color.x);
        CHECK(half.sun_color.x > wet.sun_color.x);
        // By night it does not get lighter.
        render::Lighting night = clear;
        night.zenith_color = {0.01f, 0.015f, 0.04f};
        night.stars = 1.0f;
        const render::Lighting wet_night = rain_lighting(night, 1.0f);
        CHECK(wet_night.zenith_color.y <= 0.03f);
        CHECK(wet_night.stars == 0.0f);
    }

    // Not a test: a saved game on a day of rain, with a dirt road and a
    // cobbled street, to look at it and hear it. Run it by name:
    //   salvaciudad_tests -ts=rain -tc="manual*" --no-skip
    // It writes <temp>/SalvaCiudad/manual_rain.scsave: copy it to the saves folder and load it.
    TEST_CASE("manual: a saved game on a day of rain" * doctest::skip()) {
        std::error_code ec;
        const std::filesystem::path folder = std::filesystem::temp_directory_path(ec) / "SalvaCiudad";
        std::filesystem::create_directories(folder, ec);
        const std::filesystem::path file = folder / "manual_rain.scsave";
        GameSetup rules = setup(200, 0b1111);
        rules.rules.climate.minutes = {30, 30, 30, 30};  // Long days: the rain lasts a minute at x1.
        rules.rules.fog = FogMode::None;
        Game g(core(), map_for(92), rules);
        provide(g);
        Command level;
        level.type = CommandType::DevLevel;
        g.apply(level);
        const auto [x0, z0] = open_ground(g, 48);
        const auto lay = [&](const char* def, int ax, int az, int bx, int bz) {
            Command c;
            c.type = CommandType::Trace;
            c.def = building(g, def);
            c.position = {Fixed::from_int(x0 + ax), Fixed::from_int(z0 + az)};
            c.value = x0 + bx;
            c.value2 = z0 + bz;
            g.apply(c);
        };
        lay("core:dirt_road", 0, 10, 40, 10);
        lay("core:cobbled_street", 0, 16, 40, 16);
        lay("core:dirt_road", 20, 12, 20, 14);
        finish_all(g);
        for (int t = 0; t < 200000 && !(g.raining() && g.tick() % g.calendar_day_ticks() == 5); ++t) {
            g.step();
        }
        REQUIRE(g.raining());
        save::SaveData data;
        data.header.name = "rain";
        data.header.game_version = SC_VERSION_STRING;
        data.header.saved_at = "2026-10-04T00:00:00";
        data.header.rules_version = kGameRulesVersion;
        data.header.content_hash = g.content().hash;
        data.header.seed = g.map().settings.seed;
        data.header.tick = g.tick();
        data.header.population = static_cast<std::uint32_t>(g.population(0));
        BinaryWriter w;
        g.save(w);
        data.put("GAME", std::move(w.bytes()));
        REQUIRE(save::write_file(file, data));
        const Building* tc = g.buildings().get(g.player(0).town_center);
        MESSAGE("roads from cell (" << x0 << ", " << z0 << "); town center at (" << tc->x << ", " << tc->z << "); temperature "
                                    << g.temperature());
    }
}
