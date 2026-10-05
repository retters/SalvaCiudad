#include <doctest.h>

#include <algorithm>
#include <filesystem>
#include <map>
#include <memory>
#include <optional>
#include <utility>
#include <vector>

#include "game/map_scene.h"
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

// A quiet game with these seasons (Season bits; 0b1111: the usual year).
GameSetup setup(std::uint8_t seasons) {
    GameSetup s;
    s.seed = 15;
    s.rules.climate.seasons = seasons;
    s.rules.diseases = Threat::None;
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

void grant(Game& g, const char* resource, std::int32_t amount) {
    Command c;
    c.type = CommandType::DevGrant;
    c.def = g.content().find_resource(resource);
    REQUIRE(c.def != kNoDef);
    c.value = amount;
    g.apply(c);
}

DefIndex building(const Game& g, const char* id) {
    const DefIndex d = g.content().find_building(id);
    REQUIRE(d != kNoDef);
    return d;
}

// A building of `def` near (x, z), where it fits; built at once.
EntityId put(Game& g, const char* def, std::int32_t x, std::int32_t z) {
    const DefIndex d = building(g, def);
    for (std::int32_t r = 0; r <= 12; ++r) {
        for (std::int32_t dz = -r; dz <= r; ++dz) {
            for (std::int32_t dx = -r; dx <= r; ++dx) {
                if (std::max(std::abs(dx), std::abs(dz)) != r || g.can_place(0, d, x + dx, z + dz, 0) != PlaceError::None) {
                    continue;
                }
                Command c;
                c.type = CommandType::PlaceBuilding;
                c.def = d;
                c.position = {Fixed::from_int(x + dx), Fixed::from_int(z + dz)};
                g.apply(c);
                Command done;
                done.type = CommandType::DevBuild;
                g.apply(done);
                for (std::size_t i = 0; i < g.buildings().size(); ++i) {
                    const Building& b = g.buildings().data()[i];
                    if (b.def == d && b.x == x + dx && b.z == z + dz) {
                        return g.buildings().entities()[i];
                    }
                }
            }
        }
    }
    return {};
}

std::uint32_t plant(Game& g, FeatureType type, std::int32_t x, std::int32_t z) {
    Command c;
    c.type = CommandType::DevFeature;
    c.def = static_cast<std::uint16_t>(type);
    c.value = Fixed::one().raw();
    c.position = {Fixed::from_int(x), Fixed::from_int(z)};
    const std::size_t before = g.map().features.size();
    g.apply(c);
    REQUIRE(g.map().features.size() == before + 1);
    return static_cast<std::uint32_t>(before);
}

// A town with a forager at work and a berry bush a few steps from it.
struct Camp {
    EntityId forager;
    std::uint32_t bush = 0;
};
Camp camp(Game& g) {
    for (const char* food : {"core:bread", "core:meat", "core:vegetables", "core:fruit"}) {
        grant(g, food, 3000);
    }
    const Building* tc = g.buildings().get(g.player(0).town_center);
    REQUIRE(tc != nullptr);
    const std::int32_t tx = tc->x, tz = tc->z;
    Camp c;
    c.forager = put(g, "core:forager", tx + 16, tz);
    REQUIRE(c.forager.valid());
    const Building at = *g.buildings().get(c.forager);
    c.bush = plant(g, FeatureType::BerryBush, at.x + 10, at.z + 2);
    // Its biome's bushes are of berries (not brambles): the tests count on it.
    REQUIRE(g.bush_kind(g.map().features[c.bush]) != BushKind::Thorn);
    for (int t = 0; t < 400 && g.buildings().get(c.forager)->workers.empty(); ++t) {
        run(g, 10);
    }
    REQUIRE_FALSE(g.buildings().get(c.forager)->workers.empty());
    return c;
}

Calendar in(Season season, std::uint32_t year = 1) {
    Calendar c;
    c.year = year;
    c.season = season;
    return c;
}

}  // namespace

TEST_SUITE("berries") {
    TEST_CASE("the base game's berry bush gives once a year, in summer and autumn, and has its three looks") {
        const Content& c = test::core_content();
        const FeatureDef* bush = c.feature(FeatureType::BerryBush);
        REQUIRE(bush != nullptr);
        const auto bit = [](Season s) { return static_cast<std::uint8_t>(1u << static_cast<unsigned>(s)); };
        CHECK(bush->seasons == (bit(Season::Summer) | bit(Season::Autumn)));
        CHECK(bush->regrow_days == 0);
        CHECK_FALSE(bush->after_rain);
        CHECK(bush->resource == c.find_resource("core:berries"));
        // Its files: berries, blueberries, brambles; and without fruit, and in flower.
        CHECK(bush->models.size() == static_cast<std::size_t>(BushKind::Count));
        CHECK_FALSE(bush->model_green.empty());
        CHECK_FALSE(bush->model_flower.empty());
        // Blueberries where it is cold, brambles where it is dry.
        std::map<std::string, BushKind> kinds;
        for (const BiomeDef& b : c.flora.biomes) {
            kinds[b.id] = static_cast<BushKind>(b.bush);
        }
        CHECK(kinds["core:temperate"] == BushKind::Berries);
        CHECK(kinds["core:boreal"] == BushKind::Blueberries);
        CHECK(kinds["core:mountain"] == BushKind::Blueberries);
        CHECK(kinds["core:mediterranean"] == BushKind::Thorn);
        CHECK(kinds["core:savanna"] == BushKind::Thorn);
        // Herbs are as they were: they grow back, in any season.
        CHECK(c.feature(FeatureType::Herbs)->seasons == 0);
        CHECK(c.feature(FeatureType::Herbs)->regrow_days > 0);
    }

    TEST_CASE("a bush has no berries in spring, has them in summer, and loses them when winter comes") {
        Game g(core(), map_for(92), setup(0b1111));
        const Camp c = camp(g);
        const FeatureDef& bush = *g.content().feature(FeatureType::BerryBush);
        // By the calendar, whatever today is.
        CHECK(g.fruit_on(c.bush, in(Season::Spring)) == 0);
        CHECK(g.fruit_on(c.bush, in(Season::Summer)) == bush.amount);
        CHECK(g.fruit_on(c.bush, in(Season::Autumn)) == bush.amount);
        CHECK(g.fruit_on(c.bush, in(Season::Winter)) == 0);
        // And through a year of the game.
        std::map<Season, std::int32_t> least, most;
        std::int32_t picked_in_summer = 0;
        const std::uint32_t year = g.calendar().year;
        while (g.calendar().year == year) {
            const Season s = g.calendar().season;
            const std::int32_t has = g.fruit_on(c.bush);
            least[s] = least.contains(s) ? std::min(least[s], has) : has;
            most[s] = most.contains(s) ? std::max(most[s], has) : has;
            if (s == Season::Summer) {
                picked_in_summer = std::max(picked_in_summer, g.nodes()[c.bush].fruit_picked);
            }
            g.step();
        }
        CHECK(most[Season::Spring] == 0);
        CHECK(most[Season::Summer] == bush.amount);
        CHECK(picked_in_summer > 0);              // The forager went for them.
        CHECK(least[Season::Autumn] < bush.amount);  // What was picked in summer is not there again in autumn.
        CHECK(most[Season::Winter] == 0);
        CHECK(g.nodes()[c.bush].amount == 1);     // The bush itself is still there.
        // The next year, all of it again.
        CHECK(g.fruit_on(c.bush, in(Season::Summer, year + 1)) == bush.amount);
    }

    TEST_CASE("out of season the forager is waiting, not out of bushes") {
        Game g(core(), map_for(92), setup(0b1000));  // Winter.
        const Camp c = camp(g);
        (void)g.take_events();
        bool exhausted = false;
        for (int t = 0; t < 3000; ++t) {
            g.step();
            for (const Game::Event& e : g.take_events()) {
                exhausted = exhausted || (e.kind == Game::Event::Kind::Exhausted && e.entity == c.forager);
            }
        }
        CHECK(g.buildings().get(c.forager)->supply == Supply::Waiting);
        CHECK_FALSE(exhausted);
        CHECK(g.nodes()[c.bush].fruit_picked == 0);
    }

    TEST_CASE("brambles bear nothing and blueberries bear the same as berries") {
        // A dry, warm map has brambles; a cold one, blueberries.
        const auto bushes = [](std::uint8_t temperature, std::uint8_t humidity) {
            MapSettings s;
            s.seed = 31;
            s.size = MapSize::Small;
            s.sea = Sea::None;
            s.temperature = temperature;
            s.humidity = humidity;
            std::optional<MapData> m = generate_map(s, test::core_content());
            REQUIRE(m.has_value());
            Game g(core(), *m, setup(0b0010));  // Summer.
            const FeatureDef& bush = *g.content().feature(FeatureType::BerryBush);
            std::map<BushKind, int> count;
            for (std::size_t i = 0; i < g.map().features.size(); ++i) {
                const MapFeature& f = g.map().features[i];
                if (f.type != FeatureType::BerryBush) {
                    continue;
                }
                const BushKind kind = g.bush_kind(f);
                ++count[kind];
                CHECK(g.barren(f) == (kind == BushKind::Thorn));
                CHECK(g.fruit_on(static_cast<std::uint32_t>(i)) == (kind == BushKind::Thorn ? 0 : bush.amount));
                // On screen it is the bush of its biome.
                CHECK(visual_slot(g.content(), f, &g.map()) ==
                      feature_slot(g.content(), FeatureType::BerryBush, static_cast<std::size_t>(kind)));
            }
            return count;
        };
        auto dry = bushes(175, 25);
        auto cold = bushes(25, 100);
        MESSAGE("dry map: " << dry[BushKind::Thorn] << " brambles, " << dry[BushKind::Berries] << " of berries; cold map: "
                            << cold[BushKind::Blueberries] << " of blueberries, " << cold[BushKind::Berries] << " of berries");
        CHECK(dry[BushKind::Thorn] > 0);
        CHECK(cold[BushKind::Blueberries] > 0);
    }

    TEST_CASE("only a berry bush can be a bramble") {
        Game g(core(), map_for(92), setup(0b0010));
        const Camp c = camp(g);
        CHECK_FALSE(g.barren(g.map().features[c.bush]));
        MapFeature bramble = g.map().features[c.bush];
        bramble.type = FeatureType::Herbs;
        CHECK_FALSE(g.barren(bramble));  // Only a berry bush can be a bramble.
    }

    TEST_CASE("on screen a bush is in flower in spring, has its fruit in summer and autumn, and is green in winter") {
        const Content& c = test::core_content();
        MapFeature bush;
        bush.type = FeatureType::BerryBush;
        CHECK(feature_look(c, bush, TreeCalendar{Season::Spring, kTurnSteps}) == kFlowerLook);
        CHECK(feature_look(c, bush, TreeCalendar{Season::Summer, kTurnSteps}) == 0);
        CHECK(feature_look(c, bush, TreeCalendar{Season::Autumn, kTurnSteps}) == 0);
        CHECK(feature_look(c, bush, TreeCalendar{Season::Winter, kTurnSteps}) == kGreenLook);
        // What has no such models stays as it is all year: a nest, herbs, a rock.
        for (const FeatureType other : {FeatureType::Nest, FeatureType::Herbs, FeatureType::Stone, FeatureType::BeeTree}) {
            MapFeature f;
            f.type = other;
            for (const Season s : {Season::Spring, Season::Summer, Season::Autumn, Season::Winter}) {
                CHECK(feature_look(c, f, TreeCalendar{s, kTurnSteps}) == 0);
            }
        }
        // Without a map to tell its biome, the bush of berries.
        CHECK(visual_slot(c, bush) == feature_slot(c, FeatureType::BerryBush, 0));
    }

    TEST_CASE("a town starts with a quarter more food than before") {
        Game g(core(), map_for(92), setup(0b0010));
        const Building* tc = g.buildings().get(g.player(0).town_center);
        REQUIRE(tc != nullptr);
        const auto has = [&](const char* id) {
            std::int32_t n = 0;
            for (const Stock& s : tc->stock) {
                n += s.resource == g.content().find_resource(id) ? s.amount : 0;
            }
            return n;
        };
        CHECK(has("core:berries") == 188);
        CHECK(has("core:roots") == 50);
        CHECK(has("core:log") == 60);
    }

    // Not a test: two saved games with a forager and rows of berry bushes, in
    // spring (in flower) and in summer (with their fruit, the nearest ones
    // already picked). Run it by name:
    //   salvaciudad_tests -ts=berries -tc="manual*" --no-skip
    // It writes <temp>/SalvaCiudad/manual_berries_spring.scsave and
    // manual_berries_summer.scsave: copy them to the saves folder and load them.
    TEST_CASE("manual: saved games with berry bushes in spring and in summer" * doctest::skip()) {
        std::error_code ec;
        const std::filesystem::path folder = std::filesystem::temp_directory_path(ec) / "SalvaCiudad";
        std::filesystem::create_directories(folder, ec);
        GameSetup rules = setup(0b1111);
        rules.rules.climate.minutes = {10, 10, 10, 10};
        rules.rules.fog = FogMode::None;
        Game g(core(), map_for(92), rules);
        const Camp c = camp(g);
        const Building at = *g.buildings().get(c.forager);
        for (int k = 0; k < 8; ++k) {
            (void)plant(g, FeatureType::BerryBush, at.x - 6 + 3 * k, at.z + 12);
            (void)plant(g, FeatureType::BerryBush, at.x - 6 + 3 * k, at.z + 16);
        }
        const auto write = [&](const char* name) {
            save::SaveData data;
            data.header.name = name;
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
            REQUIRE(save::write_file(folder / (std::string("manual_") + name + ".scsave"), data));
        };
        run(g, 600);
        REQUIRE(g.calendar().season == Season::Spring);
        write("berries_spring");
        // Into the summer, until the forager has picked some bushes clean.
        for (int t = 0; t < 40000 && !(g.calendar().season == Season::Summer && g.fruit_on(c.bush) == 0); ++t) {
            g.step();
        }
        REQUIRE(g.calendar().season == Season::Summer);
        write("berries_summer");
        MESSAGE("forager at (" << at.x << ", " << at.z << ")");
    }
}
