#include <doctest.h>

#include <memory>
#include <optional>

#include "sim/climate.h"
#include "sim/game.h"
#include "sim/worldgen.h"
#include "test_util.h"

using namespace sc::sim;

namespace {

std::shared_ptr<const Content> content() {
    return std::shared_ptr<const Content>(std::shared_ptr<const Content>{}, &sc::test::core_content());
}

MapData small_map(std::uint64_t seed) {
    MapSettings s;
    s.seed = seed;
    s.size = MapSize::Small;
    std::optional<MapData> m = generate_map(s, *content());
    REQUIRE(m.has_value());
    return std::move(*m);
}

GameSetup setup(ClimateSettings climate, StartGoods start = StartGoods::Normal) {
    GameSetup s;
    s.seed = 42;
    s.rules.climate = climate;
    s.rules.start = start;
    // Only what this suite tests: no fires, raiders or wild animals.
    s.rules.fires = Threat::None;
    s.rules.raiders = Threat::None;
    s.rules.wildlife = Threat::None;
    return s;
}

void run(Game& g, std::uint32_t ticks) {
    for (std::uint32_t i = 0; i < ticks; ++i) {
        g.step();
    }
}

// A house next to the town center, if there is room.
void build_house(Game& g) {
    const DefIndex house = content()->find_building("core:house");
    const Building* tc = g.buildings().get(g.player(0).town_center);
    REQUIRE(tc != nullptr);
    for (int r = 12; r < 80; r += 2) {
        for (int a = 0; a < 8; ++a) {
            const int x = tc->x + (a % 3 - 1) * r;
            const int z = tc->z + (a / 3 - 1) * r;
            if (g.can_place(0, house, x, z, 0) == PlaceError::None) {
                Command c;
                c.type = CommandType::PlaceBuilding;
                c.def = house;
                c.position = {Fixed::from_int(x), Fixed::from_int(z)};
                g.apply(c);
                return;
            }
        }
    }
    FAIL("no room for a house");
}

}  // namespace

TEST_SUITE("climate") {
    TEST_CASE("the calendar splits the year among the chosen seasons") {
        ClimateSettings four;
        const std::uint32_t year = year_ticks(YearLength::Normal);
        CHECK(year == 12000);
        CHECK(year_ticks(YearLength::Short) < year);
        CHECK(year_ticks(YearLength::Long) > year);
        CHECK(calendar(four, 0).season == Season::Spring);
        CHECK(calendar(four, year / 4).season == Season::Summer);
        CHECK(calendar(four, year / 2).season == Season::Autumn);
        CHECK(calendar(four, year * 3 / 4).season == Season::Winter);
        CHECK(calendar(four, year).season == Season::Spring);
        CHECK(calendar(four, year).year == 2);
        const Calendar c = calendar(four, year + 2 * (year / 12) + 3 * (year / 120));
        CHECK(c.month == 3);
        CHECK(c.day == 4);

        ClimateSettings summer;
        summer.seasons = 1u << static_cast<unsigned>(Season::Summer);
        for (std::uint64_t t = 0; t < 3 * year; t += 997) {
            CHECK(calendar(summer, t).season == Season::Summer);
        }
        ClimateSettings no_winter;
        no_winter.seasons = 0b0111;
        CHECK(calendar(no_winter, year * 9 / 10).season == Season::Autumn);
    }

    TEST_CASE("temperatures follow the seasons and the winter's harshness") {
        ClimateSettings mild;
        mild.winter = Harshness::Mild;
        ClimateSettings harsh;
        harsh.winter = Harshness::Harsh;
        const std::uint32_t year = year_ticks(YearLength::Normal);
        int mild_min = 100, harsh_min = 100, summer_max = -100;
        for (std::uint64_t t = 0; t < year; t += 100) {
            mild_min = std::min(mild_min, temperature(mild, 1, t));
            harsh_min = std::min(harsh_min, temperature(harsh, 1, t));
            if (calendar(mild, t).season == Season::Summer) {
                summer_max = std::max(summer_max, temperature(mild, 1, t));
            }
        }
        CHECK(mild_min >= -1);
        CHECK(harsh_min <= -14);
        CHECK(summer_max >= 21);
        // The same everywhere.
        CHECK(temperature(harsh, 99, 5555) == temperature(harsh, 99, 5555));
        ClimateSettings summer;
        summer.seasons = 1u << static_cast<unsigned>(Season::Summer);
        for (std::uint64_t t = 0; t < year; t += 100) {
            CHECK(temperature(summer, 3, t) >= 21);
        }
    }

    TEST_CASE("rules round-trip and bad ones are refused") {
        GameRules r;
        r.climate.seasons = 0b1010;
        r.climate.year = YearLength::Long;
        r.climate.winter = Harshness::Harsh;
        r.start = StartGoods::Plenty;
        r.max_population = 300;
        BinaryWriter w;
        r.write(w);
        BinaryReader rd(w.bytes());
        GameRules back;
        REQUIRE(GameRules::read(rd, back));
        CHECK(back == r);
        for (const auto& bad : {GameRules{{0, YearLength::Normal, Harshness::Normal}, StartGoods::Normal, 100},
                                GameRules{{0b1111, YearLength::Normal, Harshness::Normal}, StartGoods::Normal, 10}}) {
            BinaryWriter wb;
            bad.write(wb);
            BinaryReader rb(wb.bytes());
            GameRules out;
            CHECK_FALSE(GameRules::read(rb, out));
        }
    }

    TEST_CASE("snow falls in winter and melts in spring") {
        ClimateSettings c;
        c.winter = Harshness::Harsh;
        Game g(content(), small_map(41), setup(c));
        const std::uint32_t year = g.year_ticks();
        int winter_snow = 0;
        bool froze = false;
        for (std::uint32_t t = 0; t < year; t += 100) {
            run(g, 100);
            if (g.calendar().season == Season::Winter) {
                winter_snow = std::max(winter_snow, g.snow());
                froze = froze || g.frozen();
            }
        }
        CHECK(winter_snow > 40);
        CHECK(froze);
        run(g, year / 3);  // Late spring.
        CHECK(g.snow() == 0);
    }

    TEST_CASE("an eternal summer needs no firewood") {
        ClimateSettings c;
        c.seasons = 1u << static_cast<unsigned>(Season::Summer);
        Game g(content(), small_map(42), setup(c));
        build_house(g);
        run(g, g.year_ticks());
        CHECK(g.snow() == 0);
        for (const Villager& v : g.villagers().data()) {
            CHECK(v.warmth == village::kWarmthMax);
        }
    }

    TEST_CASE("the cold hurts without firewood, and firewood keeps homes warm") {
        ClimateSettings c;
        c.seasons = 1u << static_cast<unsigned>(Season::Winter);
        c.winter = Harshness::Harsh;
        // Without firewood at all.
        auto no_wood = std::make_shared<Content>(sc::test::core_content());
        for (ResourceDef& r : no_wood->resources) {
            if (r.id == "core:firewood" || r.id == "core:clothes") {
                r.id += "_gone";
            }
        }
        GameSetup cold = setup(c);
        Game freezing(no_wood, small_map(43), cold);
        build_house(freezing);
        run(freezing, 3000);
        int cold_people = 0;
        for (const Villager& v : freezing.villagers().data()) {
            cold_people += v.warmth < village::kWarmthMax / 2 ? 1 : 0;
        }
        CHECK(cold_people > 0);
        run(freezing, 6000);
        CHECK(freezing.player(0).deaths > 0);

        // With firewood brought home: everybody housed stays warm.
        Game warm(content(), small_map(43), cold);
        build_house(warm);
        build_house(warm);
        build_house(warm);
        const DefIndex firewood = content()->find_resource("core:firewood");
        for (int month = 0; month < 9; ++month) {
            Command grant;
            grant.type = CommandType::DevGrant;
            grant.def = firewood;
            grant.value = 60;
            warm.apply(grant);
            run(warm, 1000);
        }
        int housed_and_cold = 0;
        for (const Villager& v : warm.villagers().data()) {
            const Building* home = warm.buildings().get(v.home);
            housed_and_cold += home != nullptr && v.warmth == 0 ? 1 : 0;
        }
        CHECK(housed_and_cold == 0);
        CHECK(warm.player(0).deaths == 0);
    }

    TEST_CASE("frozen bushes are not picked") {
        ClimateSettings c;
        c.seasons = 1u << static_cast<unsigned>(Season::Winter);
        c.winter = Harshness::Harsh;
        Game g(content(), small_map(44), setup(c));
        run(g, 200);
        REQUIRE(g.frozen());
        std::int32_t before = 0;
        for (std::size_t i = 0; i < g.nodes().size(); ++i) {
            before += g.map().features[i].type == FeatureType::BerryBush ? g.nodes()[i].amount : 0;
        }
        const DefIndex forager = content()->find_building("core:forager");
        const Building* tc = g.buildings().get(g.player(0).town_center);
        for (int r = 14; r < 80; r += 2) {
            if (g.can_place(0, forager, tc->x + r, tc->z, 0) == PlaceError::None) {
                Command cmd;
                cmd.type = CommandType::PlaceBuilding;
                cmd.def = forager;
                cmd.position = {Fixed::from_int(tc->x + r), Fixed::from_int(tc->z)};
                g.apply(cmd);
                break;
            }
        }
        run(g, 3000);
        std::int32_t after = 0;
        for (std::size_t i = 0; i < g.nodes().size(); ++i) {
            after += g.map().features[i].type == FeatureType::BerryBush ? g.nodes()[i].amount : 0;
        }
        CHECK(after == before);
    }
}
