#include <doctest.h>

#include <memory>
#include <optional>

#include "game/day_light.h"
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

    TEST_CASE("the village's day does not stretch with the year; harvests do") {
        const auto game = [](std::uint8_t season_minutes) {
            ClimateSettings c;
            c.seasons = 0b0111;
            c.minutes = {season_minutes, season_minutes, season_minutes, 0};
            return Game(content(), small_map(31), setup(c));
        };
        const Game usual = game(5);
        const Game longer = game(15);
        CHECK(usual.year_ticks() == 9000);
        CHECK(longer.year_ticks() == 27000);
        CHECK(usual.day_ticks() == longer.day_ticks());
        CHECK(usual.month_ticks() == longer.month_ticks());
        CHECK(longer.calendar_day_ticks() == 3 * usual.calendar_day_ticks());
        // What a harvest and a yearly limit are worth follows the year.
        CHECK(usual.per_year(120) == 90);
        CHECK(longer.per_year(120) == 270);
        CHECK(longer.per_year(1) == 2);
        CHECK(Game(content(), small_map(31), setup(ClimateSettings{})).per_year(120) == 120);
        CHECK(usual.per_year(0) == 0);
    }

    TEST_CASE("seasons with minutes of their own make the year") {
        // A long summer, a short winter and no autumn: 12 + 30 + 2 minutes.
        ClimateSettings c;
        c.seasons = 0b1011;
        c.minutes = {12, 30, 0, 2};
        REQUIRE(c.own_lengths());
        const std::uint32_t year = year_ticks(c);
        CHECK(year == 44u * kTicksPerMinute);
        CHECK(year % 120 == 0);  // A whole number of ticks per day.
        std::array<SeasonSpan, 4> spans{};
        REQUIRE(season_spans(c, spans) == 3);
        CHECK(spans[0].season == Season::Spring);
        CHECK(spans[1].ticks == 30u * kTicksPerMinute);
        CHECK(spans[2].season == Season::Winter);
        CHECK(calendar(c, 0).season == Season::Spring);
        CHECK(calendar(c, 12u * kTicksPerMinute - 1).season == Season::Spring);
        CHECK(calendar(c, 12u * kTicksPerMinute).season == Season::Summer);
        CHECK(calendar(c, 12u * kTicksPerMinute).season_progress == 0);
        CHECK(calendar(c, 27u * kTicksPerMinute).season_progress == 500);
        CHECK(calendar(c, 42u * kTicksPerMinute).season == Season::Winter);
        CHECK(calendar(c, year - 1).season == Season::Winter);
        CHECK(calendar(c, year - 1).season_progress == 999);
        CHECK(calendar(c, year).season == Season::Spring);
        CHECK(calendar(c, year).year == 2);
        // Still twelve months of ten days, each longer.
        const Calendar mid = calendar(c, year / 2);
        CHECK(mid.month == 7);
        CHECK(mid.day == 1);
        // The weather follows: warm through the long summer, freezing in
        // the two minutes of winter (after it eases in).
        for (std::uint64_t t = 20u * kTicksPerMinute; t < 42u * kTicksPerMinute; t += 300) {
            CHECK(temperature(c, 5, t) >= 18);
        }
        CHECK(temperature(c, 5, year - 100) <= 0);
        // Years of 60, 75 and 90 minutes, shared out as one likes.
        for (const auto& minutes : {std::array<std::uint8_t, 4>{15, 15, 15, 15}, std::array<std::uint8_t, 4>{20, 30, 20, 5},
                                    std::array<std::uint8_t, 4>{30, 30, 15, 15}}) {
            ClimateSettings longer;
            longer.minutes = minutes;
            const std::uint32_t sum = minutes[0] + minutes[1] + minutes[2] + minutes[3];
            CHECK(year_ticks(longer) == sum * kTicksPerMinute);
        }
        // Four seasons of five minutes are the usual year.
        ClimateSettings usual;
        usual.minutes = {5, 5, 5, 5};
        CHECK(year_ticks(usual) == year_ticks(YearLength::Normal));
        for (std::uint64_t t = 0; t < 12000; t += 37) {
            CHECK(calendar(usual, t).season == calendar(ClimateSettings{}, t).season);
            CHECK(calendar(usual, t).season_progress == calendar(ClimateSettings{}, t).season_progress);
            CHECK(temperature(usual, 9, t) == temperature(ClimateSettings{}, 9, t));
        }
    }

    TEST_CASE("day and night take turns by their own minutes, whatever the year") {
        // A year of 10 minutes, a day of 5 and a night of 10: the first half
        // of year 1 is day, then it is night until the middle of year 2.
        ClimateSettings c;
        c.seasons = 0b0011;
        c.minutes = {5, 5, 0, 0};
        REQUIRE(year_ticks(c) == 10 * kTicksPerMinute);
        const DayNightSettings d{5, 10};
        const auto at = [&](std::uint32_t year, std::uint32_t thousandths) {
            return std::uint64_t{year - 1} * year_ticks(c) + std::uint64_t{year_ticks(c)} * thousandths / 1000;
        };
        CHECK_FALSE(day_time(d, at(1, 0)).night);
        CHECK_FALSE(day_time(d, at(1, 499)).night);
        CHECK(day_time(d, at(1, 500)).night);
        CHECK(day_time(d, at(1, 999)).night);
        CHECK(day_time(d, at(2, 0)).night);
        CHECK(day_time(d, at(2, 499)).night);
        CHECK_FALSE(day_time(d, at(2, 500)).night);
        CHECK_FALSE(day_time(d, at(2, 999)).night);
        CHECK(day_time(d, at(3, 0)).night);
        // Progress and what is left.
        CHECK(day_time(d, 0).progress == 0);
        CHECK(day_time(d, 0).ticks_left == 5 * kTicksPerMinute);
        CHECK(day_time(d, 5 * kTicksPerMinute - 1).ticks_left == 1);
        CHECK(day_time(d, 10 * kTicksPerMinute).progress == 500);
        CHECK(day_time(d, 10 * kTicksPerMinute).ticks_left == 5 * kTicksPerMinute);
        // No cycle: always day.
        for (const std::uint64_t tick : {std::uint64_t{0}, std::uint64_t{4000}, std::uint64_t{123456}}) {
            CHECK_FALSE(day_time(DayNightSettings{}, tick).night);
        }
        // A game tells it, and keeps it through a save.
        GameSetup s = setup(c);
        s.rules.day_night = d;
        Game game(content(), small_map(31), s);
        CHECK_FALSE(game.day_time().night);
        run(game, 5 * kTicksPerMinute);
        CHECK(game.day_time().night);
    }

    TEST_CASE("day and night in the rules: both or neither, up to 30 minutes") {
        const auto round_trip = [](DayNightSettings d) {
            GameRules rules;
            rules.day_night = d;
            BinaryWriter w;
            rules.write(w);
            GameRules back;
            BinaryReader r(w.bytes());
            return GameRules::read(r, back) && back == rules;
        };
        CHECK(round_trip({}));
        CHECK(round_trip({5, 10}));
        CHECK(round_trip({30, 1}));
        CHECK_FALSE(round_trip({5, 0}));
        CHECK_FALSE(round_trip({0, 5}));
        CHECK_FALSE(round_trip({31, 5}));
    }

    TEST_CASE("the light of day and night") {
        const sc::render::Lighting day;
        // Noon is the season's own light; the sun is high.
        const sc::render::Lighting noon = sc::day_lighting(day, false, 0.5f);
        CHECK(noon.sun_color.x == doctest::Approx(day.sun_color.x));
        CHECK(noon.sky_ambient.z == doctest::Approx(day.sky_ambient.z));
        CHECK(noon.sun_direction.y > 0.9f);
        CHECK(noon.stars == doctest::Approx(0.0f));
        // Midnight is dark, with stars and a faint moon.
        const sc::render::Lighting midnight = sc::day_lighting(day, true, 0.5f);
        CHECK(midnight.sky_ambient.z < day.sky_ambient.z * 0.2f);
        CHECK(midnight.sun_color.z < 0.5f);
        CHECK(midnight.stars == doctest::Approx(1.0f));
        // Dusk and dawn meet the night with no jump, and the sun never
        // drops under the horizon (the shadows stay sane).
        const sc::render::Lighting dusk = sc::day_lighting(day, false, 1.0f);
        const sc::render::Lighting nightfall = sc::day_lighting(day, true, 0.0f);
        CHECK(dusk.sun_color.x == doctest::Approx(0.0f));
        CHECK(nightfall.sun_color.x == doctest::Approx(0.0f));
        CHECK(dusk.sky_ambient.x == doctest::Approx(nightfall.sky_ambient.x));
        CHECK(dusk.horizon_color.x == doctest::Approx(nightfall.horizon_color.x));
        CHECK(dusk.stars == doctest::Approx(nightfall.stars));
        CHECK(dusk.sun_direction.y > 0.1f);
        // The sun rises in the east and sets in the west.
        CHECK(sc::day_lighting(day, false, 0.1f).sun_direction.x > 0.5f);
        CHECK(sc::day_lighting(day, false, 0.9f).sun_direction.x < -0.5f);
        // Progress within the part, with the tick's fraction.
        CHECK(sc::day_progress({5, 10}, 0) == doctest::Approx(0.0f));
        CHECK(sc::day_progress({5, 10}, 1500) == doctest::Approx(0.5f));
        CHECK(sc::day_progress({5, 10}, 3000 + 3000) == doctest::Approx(0.5f));
        CHECK(sc::day_progress({}, 777) == doctest::Approx(0.5f));
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
        r.climate.minutes = {0, 7, 0, 30};
        r.climate.winter = Harshness::Harsh;
        r.start = StartGoods::Plenty;
        r.max_population = 300;
        BinaryWriter w;
        r.write(w);
        BinaryReader rd(w.bytes());
        GameRules back;
        REQUIRE(GameRules::read(rd, back));
        CHECK(back == r);
        // Minutes for a season the year does not have, none for one it has,
        // or too many: refused.
        for (const auto& minutes : {std::array<std::uint8_t, 4>{5, 7, 0, 30}, std::array<std::uint8_t, 4>{0, 0, 0, 30},
                                    std::array<std::uint8_t, 4>{0, 7, 0, 31}}) {
            GameRules bad = r;
            bad.climate.minutes = minutes;
            BinaryWriter bw;
            bad.write(bw);
            BinaryReader br(bw.bytes());
            GameRules out;
            CHECK_FALSE(GameRules::read(br, out));
        }
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
