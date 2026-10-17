#include <doctest.h>

#include <algorithm>
#include <filesystem>
#include <map>
#include <memory>
#include <optional>
#include <tuple>
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
GameSetup setup(std::uint8_t seasons = 0b1111) {
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

// Enough to eat and to keep warm for a good while.
void provide(Game& g) {
    for (const char* food : {"core:bread", "core:meat", "core:vegetables"}) {
        grant(g, food, 3000);
    }
    grant(g, "core:firewood", 2000);
    grant(g, "core:clothes", 100);
}

DefIndex building(const Game& g, const char* id) {
    const DefIndex d = g.content().find_building(id);
    REQUIRE(d != kNoDef);
    return d;
}

// A building of `def` near (x, z), where it fits; built at once.
EntityId put(Game& g, const char* def, std::int32_t x, std::int32_t z) {
    const DefIndex d = building(g, def);
    for (std::int32_t r = 0; r <= 16; ++r) {
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

std::pair<std::int32_t, std::int32_t> town(const Game& g) {
    const Building* tc = g.buildings().get(g.player(0).town_center);
    REQUIRE(tc != nullptr);
    return {tc->x, tc->z};
}

// What the town has of a resource: in its buildings and in its people's hands.
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

void level_up(Game& g) {
    Command c;
    c.type = CommandType::DevLevel;
    g.apply(c);
    REQUIRE(g.tier(0) >= 2);
}

// A field of 8 x 8 by the farm, sown with `crop` every year.
void field_of(Game& g, EntityId farm, const char* crop) {
    const Building at = *g.buildings().get(farm);
    const std::size_t index = at.fields.size();
    bool placed = false;
    for (int r = 8; r < 40 && !placed; r += 2) {
        for (int a = 0; a < 8 && !placed; ++a) {
            const int x = at.x + (a % 3 - 1) * r;
            const int z = at.z + (a / 3 - 1) * r;
            if (g.can_place_field(0, farm, x, z, 8, 8) != PlaceError::None) {
                continue;
            }
            Command c;
            c.type = CommandType::PlaceField;
            c.entity = farm;
            c.position = {Fixed::from_int(x), Fixed::from_int(z)};
            c.value = 8 | (8 << 8);
            g.apply(c);
            placed = true;
        }
    }
    REQUIRE(placed);
    REQUIRE(g.buildings().get(farm)->fields.size() == index + 1);
    for (int year = 0; year < static_cast<int>(kPlanYears); ++year) {
        Command c;
        c.type = CommandType::SetCrop;
        c.entity = farm;
        c.def = g.content().find_crop(crop);
        REQUIRE(c.def != kNoDef);
        c.value = static_cast<std::int32_t>(index) | (year << 8);
        g.apply(c);
    }
}

}  // namespace

TEST_SUITE("wine") {
    TEST_CASE("the base game's roots, vineyard, wine press and wine") {
        const Content& c = test::core_content();
        // Roots: a crop that stands the frost and takes longer than any other.
        const DefIndex roots = c.find_crop("core:roots");
        REQUIRE(roots != kNoDef);
        CHECK(c.crops[roots].hardy);
        CHECK(c.crops[roots].resource == c.find_resource("core:roots"));
        CHECK(c.crops[roots].models.size() == kCropStages);
        for (std::size_t i = 0; i < c.crops.size(); ++i) {
            if (i != roots) {
                CHECK(c.crops[i].grow_days < c.crops[roots].grow_days);
                CHECK_FALSE(c.crops[i].hardy);
            }
        }
        // The vineyard: 8 x 8, two workers, fruit each autumn from its third year.
        const BuildingDef& vineyard = c.buildings[c.find_building("core:vineyard")];
        CHECK(vineyard.width == 8);
        CHECK(vineyard.depth == 8);
        CHECK(vineyard.workers == 2);
        CHECK(vineyard.work == WorkKind::Produce);
        CHECK(vineyard.mature_years == 2);
        CHECK(vineyard.seasons == (1u << static_cast<unsigned>(Season::Autumn)));
        CHECK(vineyard.yearly_limit > 0);
        CHECK_FALSE(vineyard.model_winter.empty());
        REQUIRE(vineyard.recipes.size() == 1);
        const RecipeDef& grapes = c.recipes[vineyard.recipes[0]];
        CHECK(grapes.inputs.empty());
        REQUIRE(grapes.outputs.size() == 1);
        CHECK(grapes.outputs[0].resource == c.find_resource("core:fruit"));
        // The wine press: a workshop of one, two of fruit for one of wine.
        const BuildingDef& press = c.buildings[c.find_building("core:decor_wine_press")];
        CHECK(press.kind == BuildingKind::Workplace);
        CHECK(press.workers == 1);
        CHECK(press.desirability == 0);
        REQUIRE(press.recipes.size() == 1);
        const RecipeDef& pressing = c.recipes[press.recipes[0]];
        REQUIRE(pressing.inputs.size() == 1);
        REQUIRE(pressing.outputs.size() == 1);
        CHECK(pressing.inputs[0].resource == c.find_resource("core:fruit"));
        CHECK(pressing.inputs[0].amount == 2);
        CHECK(pressing.outputs[0].resource == c.find_resource("core:wine"));
        CHECK(pressing.outputs[0].amount == 1);
        // Wine: a good worth twice the beer, to the merchant too.
        const ResourceDef& wine = c.resources[c.find_resource("core:wine")];
        const ResourceDef& beer = c.resources[c.find_resource("core:beer")];
        CHECK(wine.category == ResourceCategory::Good);
        CHECK(wine.value == 2 * beer.value);
        CHECK_FALSE(wine.pile.empty());
        // The tavern takes either.
        const BuildingDef& tavern = c.buildings[c.find_building("core:tavern")];
        CHECK(tavern.service_any);
        REQUIRE(tavern.service_uses.size() == 2);
        CHECK(tavern.service_uses[0].resource == c.find_resource("core:beer"));
        CHECK(tavern.service_uses[1].resource == c.find_resource("core:wine"));
    }

    TEST_CASE("roots live through a frost that kills the wheat") {
        // Crops too slow to ripen before the winter, so the frost finds them growing.
        auto slow = std::make_shared<Content>(test::core_content());
        for (CropDef& c : slow->crops) {
            c.grow_days = 500;
        }
        Game g(slow, map_for(92), setup(0b1010));  // Summer and winter.
        provide(g);
        const auto [tx, tz] = town(g);
        const EntityId farm = put(g, "core:farm", tx + 24, tz);
        REQUIRE(farm.valid());
        field_of(g, farm, "core:wheat");
        field_of(g, farm, "core:roots");
        bool wheat_grew = false, roots_grew = false, frost = false;
        bool wheat_in_frost = false, roots_in_frost = false;
        for (std::uint32_t t = 0; t < g.year_ticks() * 9 / 10; t += 50) {
            run(g, 50);
            const Field& wheat = g.buildings().get(farm)->fields[0];
            const Field& roots = g.buildings().get(farm)->fields[1];
            wheat_grew = wheat_grew || wheat.state == FieldState::Growing;
            roots_grew = roots_grew || roots.state == FieldState::Growing;
            if (g.calendar().season == Season::Winter && g.frozen()) {
                frost = true;
                wheat_in_frost = wheat_in_frost || wheat.state == FieldState::Growing;
                roots_in_frost = roots_in_frost || roots.state == FieldState::Growing;
            }
        }
        REQUIRE(wheat_grew);
        REQUIRE(roots_grew);
        REQUIRE(frost);
        CHECK_FALSE(wheat_in_frost);
        CHECK(roots_in_frost);
    }

    TEST_CASE("a vineyard bears nothing its first two years, and in the third, only in autumn") {
        Game g(core(), map_for(92), setup());
        const auto [tx, tz] = town(g);
        const EntityId vineyard = put(g, "core:vineyard", tx + 24, tz);
        REQUIRE(vineyard.valid());
        const std::int32_t start = have(g, "core:fruit");
        std::map<Season, std::int32_t> by_season;
        std::int32_t first_two = 0;
        std::int32_t last = start;
        // Three years, fed from outside month by month.
        for (int month = 0; month < 36; ++month) {
            grant(g, "core:roots", 60);
            grant(g, "core:firewood", 30);
            for (std::uint32_t t = 0; t < g.calendar_month_ticks(); ++t) {
                g.step();
                // (Fruit is eaten too: what counts is each time there is more of it.)
                const std::int32_t now = have(g, "core:fruit");
                if (now > last) {
                    if (g.calendar().year <= 2) {
                        first_two += now - last;
                    } else {
                        by_season[g.calendar().season] += now - last;
                    }
                }
                last = now;
            }
        }
        REQUIRE(g.calendar().year == 4);
        MESSAGE("fruit in the third year: " << by_season[Season::Autumn] << " in autumn, "
                                            << by_season[Season::Spring] + by_season[Season::Summer] + by_season[Season::Winter]
                                            << " in the rest; in the first two years " << first_two);
        CHECK(first_two == 0);
        CHECK(by_season[Season::Autumn] > 20);
        CHECK(by_season[Season::Spring] == 0);
        CHECK(by_season[Season::Summer] == 0);
        CHECK(by_season[Season::Winter] == 0);
        CHECK(by_season[Season::Autumn] <= g.content().buildings[building(g, "core:vineyard")].yearly_limit);
    }

    TEST_CASE("the wine press turns fruit into wine, two for one") {
        Game g(core(), map_for(92), setup(0b0010));
        provide(g);
        const auto [tx, tz] = town(g);
        grant(g, "core:fruit", 40);
        const std::int32_t fruit = have(g, "core:fruit");
        REQUIRE(put(g, "core:decor_wine_press", tx + 16, tz).valid());
        std::int32_t wine = 0;
        for (int t = 0; t < 6000 && wine < 5; ++t) {
            g.step();
            wine = have(g, "core:wine");
        }
        CHECK(wine >= 5);
        // Two of fruit went into each (some more may have been eaten: fruit is food).
        CHECK(have(g, "core:fruit") <= fruit - 2 * wine);
    }

    TEST_CASE("a tavern with wine and no beer gives entertainment; with neither, none") {
        const auto entertained = [](const char* drink) {
            Game g(core(), map_for(92), setup(0b0010));
            provide(g);
            level_up(g);
            const auto [tx, tz] = town(g);
            REQUIRE(put(g, "core:house", tx + 14, tz).valid());
            const EntityId tavern = put(g, "core:tavern", tx + 14, tz + 12);
            REQUIRE(tavern.valid());
            if (drink != nullptr) {
                grant(g, drink, 200);
            }
            bool had = false;
            for (int t = 0; t < 6000 && !had; ++t) {
                g.step();
                for (const Building& b : g.buildings().data()) {
                    had = had || (g.content().buildings[b.def].kind == BuildingKind::House &&
                                  (b.needs & (1u << static_cast<unsigned>(Need::Entertainment))) != 0);
                }
            }
            // And nothing of the other drink appeared from nowhere.
            const std::int32_t beer = have(g, "core:beer"), wine = have(g, "core:wine");
            return std::tuple{had, beer, wine};
        };
        const auto [with_wine, beer1, wine1] = entertained("core:wine");
        CHECK(with_wine);
        CHECK(beer1 == 0);
        CHECK(wine1 < 200);  // It was drunk.
        const auto [with_beer, beer2, wine2] = entertained("core:beer");
        CHECK(with_beer);
        CHECK(beer2 < 200);
        CHECK(wine2 == 0);
        const auto [with_nothing, beer3, wine3] = entertained(nullptr);
        CHECK_FALSE(with_nothing);
        CHECK(beer3 + wine3 == 0);
    }

    TEST_CASE("saving and loading keeps a vineyard, a wine press at work and a tavern with wine") {
        Game g(core(), map_for(92), setup());
        provide(g);
        level_up(g);
        const auto [tx, tz] = town(g);
        REQUIRE(put(g, "core:vineyard", tx + 24, tz).valid());
        REQUIRE(put(g, "core:decor_wine_press", tx + 16, tz + 14).valid());
        REQUIRE(put(g, "core:tavern", tx - 14, tz).valid());
        grant(g, "core:fruit", 60);
        grant(g, "core:wine", 20);
        run(g, 1500);
        BinaryWriter w;
        g.save(w);
        Game loaded(core(), map_for(92), setup());
        BinaryReader r(w.bytes());
        REQUIRE(loaded.load(r, core()));
        CHECK(loaded.hash() == g.hash());
        run(g, 1500);
        run(loaded, 1500);
        CHECK(loaded.hash() == g.hash());
        CHECK(have(loaded, "core:wine") == have(g, "core:wine"));
    }

    // Not a test: two saved games with a vineyard, a wine press, a tavern and
    // a farm with a field of roots, in autumn and in winter. Run it by name:
    //   salvasprosperia_tests -ts=wine -tc="manual*" --no-skip
    // It writes <temp>/SalvasProsperia/manual_wine_autumn.scsave and
    // manual_wine_winter.scsave: copy them to the saves folder and load them.
    TEST_CASE("manual: saved games with a vineyard in autumn and in winter" * doctest::skip()) {
        std::error_code ec;
        const std::filesystem::path folder = std::filesystem::temp_directory_path(ec) / "SalvasProsperia";
        std::filesystem::create_directories(folder, ec);
        GameSetup rules = setup();
        rules.rules.climate.minutes = {5, 5, 5, 5};
        rules.rules.fog = FogMode::None;
        Game g(core(), map_for(92), rules);
        provide(g);
        level_up(g);
        const auto [tx, tz] = town(g);
        REQUIRE(put(g, "core:vineyard", tx + 22, tz - 4).valid());
        REQUIRE(put(g, "core:decor_wine_press", tx + 16, tz + 10).valid());
        REQUIRE(put(g, "core:tavern", tx - 16, tz).valid());
        const EntityId farm = put(g, "core:farm", tx, tz + 22);
        REQUIRE(farm.valid());
        field_of(g, farm, "core:roots");
        grant(g, "core:fruit", 80);
        grant(g, "core:wine", 40);
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
        for (int t = 0; t < 40000 && g.calendar().season != Season::Autumn; ++t) {
            g.step();
        }
        run(g, 600);
        REQUIRE(g.calendar().season == Season::Autumn);
        write("wine_autumn");
        for (int t = 0; t < 40000 && g.calendar().season != Season::Winter; ++t) {
            g.step();
        }
        run(g, 300);
        REQUIRE(g.calendar().season == Season::Winter);
        write("wine_winter");
        MESSAGE("town center at (" << tx << ", " << tz << ")");
    }
}
