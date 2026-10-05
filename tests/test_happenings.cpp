#include <doctest.h>

#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <filesystem>
#include <map>
#include <memory>
#include <optional>
#include <string>
#include <utility>
#include <vector>

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

// A small map with the sea on one side whose start is neither by the sea
// nor far from it: between 200 and 420 m. (The first seed that gives one.)
const MapData& coast_map() {
    static std::optional<MapData> map;
    for (std::uint64_t seed = 1; seed < 40 && !map; ++seed) {
        MapSettings s;
        s.seed = seed;
        s.size = MapSize::Small;
        s.sea = Sea::OneSide;
        std::optional<MapData> m = generate_map(s, test::core_content());
        REQUIRE(m.has_value());
        Game probe(std::shared_ptr<const Content>(std::shared_ptr<const Content>{}, &test::core_content()), *m, GameSetup{});
        const std::int32_t sx = m->starts[0].x.floor_int(), sz = m->starts[0].z.floor_int();
        std::int64_t nearest = INT64_MAX;
        for (std::int32_t z = 0; z < m->size; z += 4) {
            for (std::int32_t x = 0; x < m->size; x += 4) {
                if (probe.sea_at(x, z)) {
                    nearest = std::min<std::int64_t>(nearest, static_cast<std::int64_t>(x - sx) * (x - sx) + static_cast<std::int64_t>(z - sz) * (z - sz));
                }
            }
        }
        if (nearest >= 200 * 200 && nearest <= 420 * 420) {
            MESSAGE("coast map: seed " << seed << ", the sea " << std::sqrt(static_cast<double>(nearest)) << " m from the start");
            map = std::move(*m);
        }
    }
    REQUIRE(map.has_value());
    return *map;
}

// A small map without sea.
const MapData& inland_map() {
    static std::optional<MapData> map;
    if (!map) {
        MapSettings s;
        s.seed = 92;
        s.size = MapSize::Small;
        s.sea = Sea::None;
        map = generate_map(s, test::core_content());
        REQUIRE(map.has_value());
    }
    return *map;
}

std::uint8_t race(const char* id) {
    const Content& c = test::core_content();
    for (std::size_t i = 0; i < c.races.size(); ++i) {
        if (c.races[i].id == id) {
            return static_cast<std::uint8_t>(i);
        }
    }
    FAIL("no race " << id);
    return 0;
}

// A town of humans, and nobody else comes.
GameSetup setup(std::uint64_t seed = 15) {
    GameSetup s;
    s.seed = seed;
    s.rules.diseases = Threat::None;
    s.rules.fires = Threat::None;
    s.rules.raiders = Threat::None;
    s.rules.wildlife = Threat::None;
    s.rules.races.fill(race("core:human"));
    s.rules.other_races = 0;
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

EntityId place_at(Game& g, DefIndex d, std::int32_t x, std::int32_t z) {
    if (g.can_place(0, d, x, z, 0) != PlaceError::None) {
        return {};
    }
    Command c;
    c.type = CommandType::PlaceBuilding;
    c.def = d;
    c.position = {Fixed::from_int(x), Fixed::from_int(z)};
    g.apply(c);
    Command done;
    done.type = CommandType::DevBuild;
    g.apply(done);
    for (std::size_t i = 0; i < g.buildings().size(); ++i) {
        const Building& b = g.buildings().data()[i];
        if (b.def == d && b.x == x && b.z == z) {
            return g.buildings().entities()[i];
        }
    }
    return {};
}

// A building of `def` near (x, z), where it fits; built at once.
EntityId put(Game& g, const char* def, std::int32_t x, std::int32_t z) {
    const DefIndex d = g.content().find_building(def);
    REQUIRE(d != kNoDef);
    for (std::int32_t r = 0; r <= 24; ++r) {
        for (std::int32_t dz = -r; dz <= r; ++dz) {
            for (std::int32_t dx = -r; dx <= r; ++dx) {
                if (std::max(std::abs(dx), std::abs(dz)) != r) {
                    continue;
                }
                if (const EntityId id = place_at(g, d, x + dx, z + dz); id.valid()) {
                    return id;
                }
            }
        }
    }
    return {};
}

const Building& at(const Game& g, EntityId id) {
    const Building* b = g.buildings().get(id);
    REQUIRE(b != nullptr);
    return *b;
}

// Everything of `resource` the town has: in its buildings and in hand.
std::int32_t have(const Game& g, const char* resource) {
    const DefIndex r = g.content().find_resource(resource);
    std::int32_t n = 0;
    for (const Building& b : g.buildings().data()) {
        for (const Stock& s : b.stock) {
            n += s.resource == r ? s.amount : 0;
        }
    }
    for (const Villager& v : g.villagers().data()) {
        n += v.carrying.resource == r ? v.carrying.amount : 0;
    }
    return n;
}

// A town that lacks nothing, with a storehouse; where its center is.
std::pair<std::int32_t, std::int32_t> town(Game& g) {
    grant(g, "core:bread", 6000);
    grant(g, "core:firewood", 3000);
    const Building tc = at(g, g.player(0).town_center);  // (A copy: building moves the others.)
    REQUIRE(put(g, "core:storehouse", tc.x - 26, tc.z).valid());
    return {tc.x + tc.width / 2, tc.z + tc.depth / 2};
}

// Food and firewood for another month.
void supply(Game& g) {
    grant(g, "core:bread", std::max(0, 6000 - have(g, "core:bread")));
    grant(g, "core:firewood", std::max(0, 3000 - have(g, "core:firewood")));
}

// A house on the shore: the land nearest to the town among what has the sea within 60 m.
EntityId house_by_the_sea(Game& g) {
    const Building tc = at(g, g.player(0).town_center);
    std::int64_t best = INT64_MAX;
    std::pair<std::int32_t, std::int32_t> where{0, 0};
    for (std::int32_t z = 12; z < g.map().size - 12; z += 4) {
        for (std::int32_t x = 12; x < g.map().size - 12; x += 4) {
            const std::int64_t d = static_cast<std::int64_t>(x - tc.x) * (x - tc.x) + static_cast<std::int64_t>(z - tc.z) * (z - tc.z);
            if (d >= best || g.map().water_at(x, z)) {
                continue;
            }
            const bool sea = g.sea_at(x - 60, z) || g.sea_at(x + 60, z) || g.sea_at(x, z - 60) || g.sea_at(x, z + 60);
            if (sea) {
                best = d;
                where = {x, z};
            }
        }
    }
    REQUIRE(best != INT64_MAX);
    const EntityId house = put(g, "core:house", where.first, where.second);
    REQUIRE(house.valid());
    return house;
}

// `count` grown people of a people arrive.
void arrive(Game& g, const char* people, std::int32_t count) {
    Command c;
    c.type = CommandType::DevSpawn;
    c.value = count;
    c.def2 = static_cast<std::uint16_t>(race(people) + 1);
    const std::size_t before = g.villagers().size();
    g.apply(c);
    REQUIRE(g.villagers().size() == before + static_cast<std::size_t>(count));
}

std::uint32_t today(const Game& g) {
    return static_cast<std::uint32_t>(g.calendar_day());
}

}  // namespace

TEST_SUITE("happenings") {
    TEST_CASE("the base game: the foxfolk have the custom of the lanterns") {
        const Content& c = test::core_content();
        for (const RaceDef& r : c.races) {
            CHECK(r.lanterns == (r.id == "core:foxfolk"));
        }
        CHECK(village::kMoodPoints == 3);
        CHECK(village::kMoodDays == 10);
        CHECK(village::kWhaleMeters == 150);
        CHECK(village::kLanternFolk == 2);
    }

    TEST_CASE("with the same seed the happenings fall on the same days: the whales in autumn, the lanterns a day of each town") {
        const Game a(core(), inland_map(), setup(15));
        const Game b(core(), inland_map(), setup(15));
        const Game other(core(), inland_map(), setup(16));
        int differ = 0, towns_differ = 0, years_differ = 0;
        for (std::uint32_t year = 0; year < 12; ++year) {
            const std::uint32_t whales = a.happening_day(HappeningKind::Whales, year, 0);
            const std::uint32_t lanterns = a.happening_day(HappeningKind::Lanterns, year, 0);
            CHECK(whales == b.happening_day(HappeningKind::Whales, year, 0));
            CHECK(lanterns == b.happening_day(HappeningKind::Lanterns, year, 0));
            REQUIRE(whales < kDaysPerYear);
            REQUIRE(lanterns < kDaysPerYear);
            // The whales: a day of the autumn, the same for every town.
            const std::uint64_t noon = (static_cast<std::uint64_t>(year) * kDaysPerYear + whales) * a.calendar_day_ticks() + a.calendar_day_ticks() / 2;
            CHECK(sim::calendar(a.rules().climate, noon).season == Season::Autumn);
            CHECK(whales == a.happening_day(HappeningKind::Whales, year, 3));
            towns_differ += lanterns != a.happening_day(HappeningKind::Lanterns, year, 3) ? 1 : 0;
            differ += whales != other.happening_day(HappeningKind::Whales, year, 0) ? 1 : 0;
            differ += lanterns != other.happening_day(HappeningKind::Lanterns, year, 0) ? 1 : 0;
            years_differ += year > 0 && whales != a.happening_day(HappeningKind::Whales, year - 1, 0) ? 1 : 0;
        }
        CHECK(differ >= 12);
        CHECK(towns_differ >= 8);
        CHECK(years_differ >= 6);
        // In a game with no autumn they pass a day of the year, whichever.
        GameSetup mild = setup(15);
        mild.rules.climate.seasons = 0b0011;
        const Game spring(core(), inland_map(), mild);
        CHECK(spring.happening_day(HappeningKind::Whales, 4, 0) < kDaysPerYear);
    }

    TEST_CASE("the whales pass for a town with a building by the sea, and not for one inland") {
        Game coast(core(), coast_map(), setup());
        Game inland(core(), coast_map(), setup());
        Game dry(core(), inland_map(), setup());
        (void)town(coast);
        (void)town(inland);
        (void)town(dry);
        (void)house_by_the_sea(coast);
        (void)coast.take_events();
        const std::uint32_t day = coast.happening_day(HappeningKind::Whales, 0, 0);
        int seen = 0, others = 0;
        std::uint32_t from = 0;
        for (std::uint32_t t = 0; t < coast.year_ticks(); ++t) {
            if (t % coast.calendar_month_ticks() == 0) {
                supply(coast);
                supply(inland);
                supply(dry);
            }
            coast.step();
            inland.step();
            dry.step();
            for (const Game::Event& e : coast.take_events()) {
                if (e.kind == Game::Event::Kind::Whales) {
                    ++seen;
                    from = today(coast);
                    CHECK(e.owner == 0);
                    CHECK(today(coast) == day);
                    CHECK(coast.calendar().season == Season::Autumn);
                    // In the sea, within reach of the house.
                    CHECK(coast.sea_at(e.at.x.floor_int(), e.at.z.floor_int()));
                    REQUIRE(coast.happenings().size() == 1);
                    CHECK(coast.happenings()[0].kind == HappeningKind::Whales);
                    CHECK(coast.happenings()[0].town == 0);
                    CHECK(coast.happenings()[0].at == e.at);
                    CHECK(coast.happenings()[0].until_day == day + village::kWhaleDays);
                    CHECK(coast.town_mood(0) == village::kMoodPoints);
                }
            }
            for (Game* g : {&inland, &dry}) {
                for (const Game::Event& e : g->take_events()) {
                    others += e.kind == Game::Event::Kind::Whales ? 1 : 0;
                }
                CHECK(g->town_mood(0) == 0);
                CHECK(g->happenings().empty());
            }
            // What is seen of them lasts its days and no more.
            if (seen == 1) {
                CHECK(coast.happenings().size() == (today(coast) < from + village::kWhaleDays ? 1u : 0u));
            }
        }
        CHECK(seen == 1);
        CHECK(others == 0);
    }

    TEST_CASE("the mood of the town raises the happiness of its houses and is gone in ten days") {
        Game g(core(), coast_map(), setup());
        const auto [tx, tz] = town(g);
        (void)house_by_the_sea(g);
        const EntityId home = put(g, "core:house", tx + 20, tz - 18);
        REQUIRE(home.valid());
        const std::uint32_t day = g.happening_day(HappeningKind::Whales, 0, 0);
        std::int32_t before = -1, base_before = -1;
        bool began = false;
        for (std::uint32_t t = 0; t < g.year_ticks() && today(g) <= day + village::kMoodDays + 1; ++t) {
            if (t % g.calendar_month_ticks() == 0) {
                supply(g);
            }
            g.step();
            const std::uint32_t now = today(g);
            if (now < day) {
                CHECK(g.town_mood(0) == 0);
                before = at(g, home).happiness;
                base_before = before;
                continue;
            }
            began = true;
            // 3 for eight days, then 2 and 1, then nothing.
            const std::int32_t left = static_cast<std::int32_t>(day + village::kMoodDays) - static_cast<std::int32_t>(now);
            CHECK(g.town_mood(0) == std::clamp(left, 0, village::kMoodPoints));
            // The house: what it had, and the mood (seen from the second day of each: houses are looked at now and then).
            if (g.tick() % g.calendar_day_ticks() > g.calendar_day_ticks() / 2) {
                CHECK(at(g, home).happiness - g.town_mood(0) == base_before);
            }
        }
        REQUIRE(began);
        REQUIRE(before >= 0);
        CHECK(g.town_mood(0) == 0);
        CHECK(at(g, home).happiness == before);
    }

    TEST_CASE("the merchant on his way comes in half the time when the whales pass") {
        Game g(core(), coast_map(), setup());
        const auto [tx, tz] = town(g);
        (void)house_by_the_sea(g);
        grant(g, "core:log", 400);
        grant(g, "core:stone", 400);
        Command up;
        up.type = CommandType::DevLevel;
        g.apply(up);
        g.apply(up);
        REQUIRE(put(g, "core:trading_post", tx + 24, tz + 16).valid());
        const std::uint32_t day = g.happening_day(HappeningKind::Whales, 0, 0);
        bool passed = false;
        for (std::uint32_t t = 0; t < g.year_ticks() && !passed; ++t) {
            if (t % g.calendar_month_ticks() == 0) {
                supply(g);
            }
            const std::uint64_t planned = g.player(0).merchant_arrives;
            const std::uint64_t tick = g.tick();
            g.step();
            for (const Game::Event& e : g.take_events()) {
                if (e.kind == Game::Event::Kind::Whales) {
                    passed = true;
                    REQUIRE(today(g) == day);
                    REQUIRE(planned > tick + 4);  // One was on his way.
                    const std::uint64_t now = g.player(0).merchant_arrives;
                    MESSAGE("the merchant was " << planned - tick << " ticks away; now, " << now - tick);
                    CHECK(now < planned);
                    CHECK(now >= tick + (planned - tick) / 2 - 2);
                    CHECK(now <= tick + (planned - tick) / 2 + 2);
                }
            }
        }
        CHECK(passed);
    }

    TEST_CASE("a town with one of the foxfolk has no lanterns; with two, once a year") {
        Game one(core(), inland_map(), setup());
        Game two(core(), inland_map(), setup());
        Game none(core(), inland_map(), setup());
        (void)town(one);
        (void)town(two);
        (void)town(none);
        arrive(one, "core:foxfolk", 1);
        arrive(two, "core:foxfolk", 2);
        arrive(none, "core:human", 2);
        (void)two.take_events();
        int lit = 0, others = 0;
        std::uint32_t last = 0;
        for (std::uint32_t t = 0; t < 3 * two.year_ticks(); ++t) {
            if (t % two.calendar_month_ticks() == 0) {
                supply(one);
                supply(two);
                supply(none);
            }
            one.step();
            two.step();
            none.step();
            for (const Game::Event& e : two.take_events()) {
                if (e.kind == Game::Event::Kind::Lanterns) {
                    const std::uint32_t year = today(two) / kDaysPerYear;
                    CHECK(today(two) % kDaysPerYear == two.happening_day(HappeningKind::Lanterns, year, 0));
                    CHECK((lit == 0 || year == last + 1));
                    last = year;
                    ++lit;
                    CHECK(e.owner == 0);
                    const Building tc = at(two, two.player(0).town_center);
                    CHECK(std::abs(e.at.x.floor_int() - (tc.x + tc.width / 2)) <= tc.width);
                    CHECK(std::abs(e.at.z.floor_int() - (tc.z + tc.depth / 2)) <= tc.depth);
                    CHECK(two.town_mood(0) == village::kMoodPoints);
                    REQUIRE(two.happenings().size() == 1);
                    CHECK(two.happenings()[0].kind == HappeningKind::Lanterns);
                    CHECK(two.happenings()[0].until_day == today(two) + village::kLanternDays);
                }
            }
            for (Game* g : {&one, &none}) {
                for (const Game::Event& e : g->take_events()) {
                    others += e.kind == Game::Event::Kind::Lanterns ? 1 : 0;
                }
            }
        }
        CHECK(lit == 3);
        CHECK(others == 0);
        CHECK(one.town_mood(0) == 0);
        // The second of them comes late in the year, after the day of the lanterns: they go up the day it comes.
        const std::uint32_t year = today(one) / kDaysPerYear;
        while (today(one) % kDaysPerYear <= one.happening_day(HappeningKind::Lanterns, year, 0) + 2 && today(one) / kDaysPerYear == year) {
            one.step();
        }
        if (today(one) / kDaysPerYear == year) {
            (void)one.take_events();
            arrive(one, "core:foxfolk", 1);
            int late = 0;
            const std::uint32_t came = today(one);
            for (std::uint32_t t = 0; t < 3 * one.calendar_day_ticks(); ++t) {
                one.step();
                for (const Game::Event& e : one.take_events()) {
                    late += e.kind == Game::Event::Kind::Lanterns ? 1 : 0;
                }
            }
            CHECK(late == 1);
            CHECK(one.player(0).mood_until[static_cast<std::size_t>(HappeningKind::Lanterns)] == came + 1 + village::kMoodDays);
            return;
        }
        std::int32_t foxes = 0;
        for (const Villager& v : one.villagers().data()) {
            foxes += v.race == race("core:foxfolk") ? 1 : 0;
        }
        CHECK(foxes == 1);  // (It is still there: one is not enough.)
    }

    TEST_CASE("in a game with nights the lanterns go up the first night from their day on") {
        GameSetup rules = setup();
        rules.rules.day_night.day = 3;
        rules.rules.day_night.night = 2;
        rules.rules.races.fill(race("core:foxfolk"));
        Game g(core(), inland_map(), rules);
        (void)town(g);
        (void)g.take_events();
        int lit = 0;
        for (std::uint32_t t = 0; t < 2 * g.year_ticks(); ++t) {
            if (t % g.calendar_month_ticks() == 0) {
                supply(g);
            }
            g.step();
            for (const Game::Event& e : g.take_events()) {
                if (e.kind == Game::Event::Kind::Lanterns) {
                    const std::uint32_t year = today(g) / kDaysPerYear;
                    CHECK(year == static_cast<std::uint32_t>(lit));
                    CHECK(today(g) % kDaysPerYear >= g.happening_day(HappeningKind::Lanterns, year, 0));
                    CHECK(g.night());
                    ++lit;
                }
            }
        }
        CHECK(lit == 2);
    }

    TEST_CASE("saving and loading keeps a happening under way and the mood it left") {
        Game g(core(), coast_map(), setup());
        (void)town(g);
        (void)house_by_the_sea(g);
        arrive(g, "core:foxfolk", 2);
        for (std::uint32_t t = 0; t < g.year_ticks() && g.happenings().empty(); ++t) {
            if (t % g.calendar_month_ticks() == 0) {
                supply(g);
            }
            g.step();
        }
        REQUIRE(g.happenings().size() == 1);
        REQUIRE(g.town_mood(0) == village::kMoodPoints);
        BinaryWriter w;
        g.save(w);
        Game loaded(core(), coast_map(), setup());
        BinaryReader r(w.bytes());
        REQUIRE(loaded.load(r, core()));
        CHECK(loaded.hash() == g.hash());
        CHECK(loaded.happenings() == g.happenings());
        CHECK(loaded.town_mood(0) == village::kMoodPoints);
        CHECK(loaded.player(0).mood_until == g.player(0).mood_until);
        // It ends the same day in both, and the mood too.
        run(g, 12 * g.calendar_day_ticks());
        run(loaded, 12 * loaded.calendar_day_ticks());
        CHECK(loaded.hash() == g.hash());
        CHECK(loaded.happenings().empty());
        CHECK(loaded.town_mood(0) == 0);
        // A save cut short, or with a happening of a kind that does not exist, is refused.
        Game again(core(), coast_map(), setup());
        std::vector<std::uint8_t> bytes = w.bytes();
        bytes.resize(bytes.size() / 2);
        BinaryReader cut(bytes);
        CHECK_FALSE(again.load(cut, core()));
    }

    // Not a test: two saved games, one the day the whales pass by a town with a house on the shore, the
    // other the night of the lanterns of a town of foxfolk.
    //   salvaciudad_tests -ts=happenings -tc="manual*" --no-skip
    // It writes <temp>/SalvaCiudad/manual_whales.scsave and manual_lanterns.scsave: copy them to the saves
    // folder and load them.
    TEST_CASE("manual: saved games with the whales passing and with the lanterns of a town" * doctest::skip()) {
        std::error_code ec;
        const std::filesystem::path folder = std::filesystem::temp_directory_path(ec) / "SalvaCiudad";
        std::filesystem::create_directories(folder, ec);
        const auto write = [&](Game& g, const char* name) {
            save::SaveData data;
            data.header.name = name;
            data.header.game_version = SC_VERSION_STRING;
            data.header.saved_at = "2026-10-05T00:00:00";
            data.header.rules_version = kGameRulesVersion;
            data.header.content_hash = g.content().hash;
            data.header.seed = g.map().settings.seed;
            data.header.tick = g.tick();
            data.header.population = static_cast<std::uint32_t>(g.population(0));
            BinaryWriter bw;
            g.save(bw);
            data.put("GAME", std::move(bw.bytes()));
            REQUIRE(save::write_file(folder / (std::string("manual_") + name + ".scsave"), data));
        };
        GameSetup rules = setup();
        rules.rules.fog = FogMode::None;
        Game sea(core(), coast_map(), rules);
        (void)town(sea);
        const EntityId house = house_by_the_sea(sea);
        for (std::uint32_t t = 0; t < sea.year_ticks() && sea.happenings().empty(); ++t) {
            if (t % sea.calendar_month_ticks() == 0) {
                supply(sea);
            }
            sea.step();
        }
        REQUIRE(sea.happenings().size() == 1);
        write(sea, "whales");
        MESSAGE("the whales at (" << sea.happenings()[0].at.x.floor_int() << ", " << sea.happenings()[0].at.z.floor_int() << "), the house at ("
                                  << at(sea, house).x << ", " << at(sea, house).z << "), map of " << sea.map().size);
        GameSetup foxes = setup();
        foxes.rules.fog = FogMode::None;
        foxes.rules.day_night.day = 3;
        foxes.rules.day_night.night = 3;
        foxes.rules.races.fill(race("core:foxfolk"));
        Game fest(core(), inland_map(), foxes);
        (void)town(fest);
        for (std::uint32_t t = 0; t < fest.year_ticks() && fest.happenings().empty(); ++t) {
            if (t % fest.calendar_month_ticks() == 0) {
                supply(fest);
            }
            fest.step();
        }
        REQUIRE(fest.happenings().size() == 1);
        REQUIRE(fest.night());
        write(fest, "lanterns");
        MESSAGE("the lanterns at (" << fest.happenings()[0].at.x.floor_int() << ", " << fest.happenings()[0].at.z.floor_int() << "), night: "
                                    << fest.night());
    }
}
