#include <doctest.h>

#include <algorithm>
#include <bit>
#include <filesystem>
#include <map>
#include <memory>
#include <optional>
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

GameSetup setup(std::uint8_t seasons = 0b0010) {
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

// Until just after the homes were looked at again (once a day).
void days(Game& g, int n) {
    for (int i = 0; i < n; ++i) {
        do {
            g.step();
        } while (g.tick() % g.day_ticks() != 0);
    }
    run(g, 2);
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
    for (const char* food : {"core:bread", "core:meat", "core:vegetables", "core:fruit"}) {
        grant(g, food, 3000);
    }
}

std::pair<std::int32_t, std::int32_t> town(const Game& g) {
    const Building* tc = g.buildings().get(g.player(0).town_center);
    REQUIRE(tc != nullptr);
    return {tc->x, tc->z};
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
    for (std::int32_t r = 0; r <= 16; ++r) {
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

// An annex of `def` with `gap` meters between its walls and the house's, on whichever side it fits.
EntityId beside(Game& g, EntityId house, const char* def, std::int32_t gap) {
    const DefIndex d = g.content().find_building(def);
    REQUIRE(d != kNoDef);
    const Building h = *g.buildings().get(house);
    const BuildingDef& ad = g.content().buildings[d];
    const std::pair<std::int32_t, std::int32_t> spots[] = {{h.x + h.width + gap, h.z},
                                                           {h.x - gap - ad.width, h.z},
                                                           {h.x, h.z + h.depth + gap},
                                                           {h.x, h.z - gap - ad.depth}};
    for (const auto& [x, z] : spots) {
        if (const EntityId id = place_at(g, d, x, z); id.valid()) {
            return id;
        }
    }
    return {};
}

const Building& at(const Game& g, EntityId id) {
    const Building* b = g.buildings().get(id);
    REQUIRE(b != nullptr);
    return *b;
}

bool has(const Game& g, EntityId house, const char* annex) {
    const BuildingDef& d = g.content().buildings[g.content().find_building(annex)];
    REQUIRE(d.annex_bit >= 0);
    return ((at(g, house).annexes >> d.annex_bit) & 1u) != 0;
}

FixedVec2 middle(const Building& b) {
    return {Fixed::from_int(b.x) + Fixed::from_ratio(b.width, 2), Fixed::from_int(b.z) + Fixed::from_ratio(b.depth, 2)};
}

// What a house's happiness has over its base, its needs met and its neighborhood: what its annexes give.
std::int32_t extra(const Building& b) {
    return b.happiness - (28 + 8 * std::popcount(static_cast<unsigned>(b.needs)) + std::clamp(b.desirability / 2, -10, 10));
}

bool with_children(const Game& g, const Building& b) {
    for (const EntityId r : b.residents) {
        const Villager* v = g.villagers().get(r);
        if (v != nullptr && !g.adult(*v)) {
            return true;
        }
    }
    return false;
}

std::int32_t firewood(const Game& g, const Building& b) {
    const DefIndex fw = g.content().find_resource("core:firewood");
    std::int32_t n = 0;
    for (const Stock& s : b.stock) {
        n += s.resource == fw ? s.amount : 0;
    }
    return n;
}

void ignite(Game& g, EntityId id, bool accident) {
    Command c;
    c.type = CommandType::DevIgnite;
    c.entity = id;
    c.count = accident ? 1 : 0;
    g.apply(c);
}

}  // namespace

TEST_SUITE("annexes") {
    TEST_CASE("the base game's annexes, and the decorations they take the place of") {
        const Content& c = test::core_content();
        std::uint16_t bits = 0;
        for (const char* id : {"core:annex_clothesline", "core:annex_home_shrine", "core:annex_playground", "core:annex_rain_barrel",
                               "core:annex_woodshed"}) {
            const DefIndex d = c.find_building(id);
            REQUIRE(d != kNoDef);
            const BuildingDef& def = c.buildings[d];
            CAPTURE(id);
            CHECK(def.annex);
            CHECK(def.kind == BuildingKind::Decoration);
            CHECK(def.workers == 0);
            REQUIRE(def.annex_bit >= 0);
            CHECK(((bits >> def.annex_bit) & 1u) == 0);  // Each its own.
            bits = static_cast<std::uint16_t>(bits | (1u << def.annex_bit));
        }
        const auto def = [&](const char* id) -> const BuildingDef& { return c.buildings[c.find_building(id)]; };
        CHECK(def("core:annex_clothesline").annex_desirability == 6);
        CHECK(def("core:annex_clothesline").annex_radius == 3);
        CHECK(def("core:annex_clothesline").width == 4);
        CHECK(def("core:annex_clothesline").depth == 2);
        CHECK(def("core:annex_home_shrine").annex_need == static_cast<std::uint8_t>(Need::Religion));
        CHECK(def("core:annex_playground").annex_happiness == 5);
        CHECK(def("core:annex_playground").annex_children);
        CHECK(def("core:annex_playground").annex_radius == 15);
        CHECK(def("core:annex_rain_barrel").annex_rain);
        CHECK(def("core:annex_woodshed").annex_firewood == 80);
        for (const BuildingDef& b : c.buildings) {
            CHECK((b.annex_bit >= 0) == b.annex);
        }
        for (const char* gone : {"core:decor_clothesline", "core:decor_firewood_rack", "core:decor_tool_corner"}) {
            CHECK(c.find_building(gone) == kNoDef);
        }
    }

    TEST_CASE("a clothesline: the house beside it is a nicer place, one 10 m away is not, and two count as one") {
        Game g(core(), map_for(92), setup());
        provide(g);
        const auto [tx, tz] = town(g);
        const EntityId near = put(g, "core:house", tx + 22, tz - 20);
        const EntityId far = put(g, "core:house", tx + 22, tz + 20);
        REQUIRE(near.valid());
        REQUIRE(far.valid());
        days(g, 1);
        const std::int32_t before = at(g, near).desirability;
        REQUIRE(beside(g, near, "core:annex_clothesline", 2).valid());
        REQUIRE(beside(g, far, "core:annex_clothesline", 10).valid());
        // The house knows at once; its environment, the next day.
        CHECK(has(g, near, "core:annex_clothesline"));
        CHECK_FALSE(has(g, far, "core:annex_clothesline"));
        days(g, 1);
        CHECK(at(g, near).desirability == g.desirability_at(middle(at(g, near)), &at(g, near)) + 6);
        CHECK(at(g, near).desirability == before + 6);
        CHECK(at(g, far).desirability == g.desirability_at(middle(at(g, far)), &at(g, far)));
        CHECK(at(g, far).annexes == 0);
        // Another one by the same house adds nothing.
        REQUIRE(beside(g, near, "core:annex_clothesline", 1).valid());
        days(g, 1);
        CHECK(at(g, near).desirability == before + 6);
        // Three meters is the most.
        const EntityId third = put(g, "core:house", tx - 30, tz + 20);
        REQUIRE(third.valid());
        REQUIRE(beside(g, third, "core:annex_clothesline", 4).valid());
        CHECK_FALSE(has(g, third, "core:annex_clothesline"));
        REQUIRE(beside(g, third, "core:annex_clothesline", 3).valid());
        CHECK(has(g, third, "core:annex_clothesline"));
    }

    TEST_CASE("a home shrine: its house is as happy as with a chapel, and does not level up by it") {
        // Houses whose second level asks only for faith (and, for the other game, for nothing).
        const auto houses = [](bool faith) {
            auto c = std::make_shared<Content>(test::core_content());
            BuildingDef& house = c->buildings[c->find_building("core:house")];
            REQUIRE(!house.levels.empty());
            house.levels[0].needs = faith ? static_cast<std::uint16_t>(1u << static_cast<unsigned>(Need::Religion)) : std::uint16_t{0};
            house.levels[0].tier = 0;
            return c;
        };
        Game g(houses(true), map_for(92), setup());
        provide(g);
        const auto [tx, tz] = town(g);
        const EntityId with = put(g, "core:house", tx + 22, tz - 20);
        const EntityId without = put(g, "core:house", tx + 22, tz + 20);
        REQUIRE(with.valid());
        REQUIRE(without.valid());
        REQUIRE(beside(g, with, "core:annex_home_shrine", 1).valid());
        days(g, 3);
        const unsigned faith = 1u << static_cast<unsigned>(Need::Religion);
        CHECK(has(g, with, "core:annex_home_shrine"));
        CHECK((at(g, with).needs & faith) == 0);  // No chapel: the need itself is not met.
        CHECK(extra(at(g, with)) == 8);           // But the house is as happy as if it were.
        CHECK(extra(at(g, without)) == 0);
        CHECK_FALSE(at(g, with).upgrading);
        CHECK(at(g, with).level == 0);
        // (The same house levels up when its next level asks for nothing.)
        Game free(houses(false), map_for(92), setup());
        provide(free);
        const EntityId other = put(free, "core:house", tx + 22, tz - 20);
        REQUIRE(other.valid());
        days(free, 3);
        CHECK((at(free, other).upgrading || at(free, other).level > 0));
    }

    TEST_CASE("a playground: five more for the houses with children within 15 m, once, and nothing for the others") {
        Game g(core(), map_for(92), setup());
        provide(g);
        const auto [tx, tz] = town(g);
        std::vector<EntityId> near;
        for (const auto& [dx, dz] : {std::pair{20, -12}, std::pair{20, 2}, std::pair{34, -12}, std::pair{34, 2}}) {
            near.push_back(put(g, "core:house", tx + dx, tz + dz));
            REQUIRE(near.back().valid());
        }
        const EntityId far = put(g, "core:house", tx - 40, tz + 30);
        REQUIRE(far.valid());
        // Everybody finds a home.
        days(g, 6);
        const EntityId play = put(g, "core:annex_playground", tx + 28, tz - 4);
        REQUIRE(play.valid());
        days(g, 1);
        const auto look = [&](int playgrounds) {
            int with = 0;
            int without = 0;
            for (const EntityId id : near) {
                const Building& b = at(g, id);
                CAPTURE(playgrounds);
                REQUIRE(has(g, id, "core:annex_playground"));
                REQUIRE(b.happiness < 100);
                const bool children = with_children(g, b);
                CHECK(extra(b) == (children ? 5 : 0));
                with += children ? 1 : 0;
                without += children ? 0 : 1;
            }
            // Both kinds of house are there, or this looks at nothing.
            CHECK(with > 0);
            CHECK(without > 0);
            CHECK_FALSE(has(g, far, "core:annex_playground"));
            CHECK(extra(at(g, far)) == 0);
        };
        look(1);
        REQUIRE(put(g, "core:annex_playground", tx + 28, tz + 12).valid());
        days(g, 1);
        look(2);
    }

    TEST_CASE("a rain barrel: full, a fire that starts in its house goes out; after ten dry days it does not") {
        GameSetup rules = setup();
        rules.rules.rain = 25;  // Little rain: dry spells of ten days come soon.
        Game g(core(), map_for(92), rules);
        provide(g);
        const auto [tx, tz] = town(g);
        const EntityId house = put(g, "core:house", tx + 22, tz - 20);
        const EntityId bare = put(g, "core:house", tx - 50, tz + 40);
        REQUIRE(house.valid());
        REQUIRE(bare.valid());
        REQUIRE(beside(g, house, "core:annex_rain_barrel", 1).valid());
        REQUIRE(has(g, house, "core:annex_rain_barrel"));
        // Until it rains.
        for (int t = 0; t < 60000 && g.days_without_rain() != 0; ++t) {
            g.step();
        }
        REQUIRE(g.days_without_rain() == 0);
        CHECK(g.barrels_full());
        CHECK(g.has_full_barrel(at(g, house)));
        CHECK_FALSE(g.has_full_barrel(at(g, bare)));
        ignite(g, house, true);
        CHECK(at(g, house).fire == 0);
        ignite(g, bare, true);
        CHECK(at(g, bare).fire > 0);  // The same fire in a house without one.
        // Ten days without rain: empty.
        for (int t = 0; t < 200000 && g.days_without_rain() < village::kBarrelDryDays; ++t) {
            g.step();
        }
        REQUIRE(g.days_without_rain() >= village::kBarrelDryDays);
        REQUIRE(g.buildings().get(house) != nullptr);
        CHECK_FALSE(g.barrels_full());
        CHECK_FALSE(g.has_full_barrel(at(g, house)));
        ignite(g, house, true);
        CHECK(at(g, house).fire > 0);
    }

    TEST_CASE("where it never rains a barrel is empty, and a torch burns a house whatever its barrel") {
        GameSetup dry = setup();
        dry.rules.rain = 0;
        Game g(core(), map_for(92), dry);
        const auto [tx, tz] = town(g);
        const EntityId house = put(g, "core:house", tx + 22, tz - 20);
        REQUIRE(house.valid());
        REQUIRE(beside(g, house, "core:annex_rain_barrel", 1).valid());
        run(g, 300);
        CHECK_FALSE(g.barrels_full());
        ignite(g, house, true);
        CHECK(at(g, house).fire > 0);
        // A fire set on purpose, with the barrel full.
        GameSetup wet = setup();
        wet.rules.rain = 200;
        Game w(core(), map_for(92), wet);
        const EntityId other = put(w, "core:house", tx + 22, tz - 20);
        REQUIRE(other.valid());
        REQUIRE(beside(w, other, "core:annex_rain_barrel", 1).valid());
        for (int t = 0; t < 60000 && w.days_without_rain() != 0; ++t) {
            w.step();
        }
        REQUIRE(w.has_full_barrel(at(w, other)));
        ignite(w, other, false);
        CHECK(at(w, other).fire > 0);
    }

    TEST_CASE("a woodshed: its house keeps 80 of firewood, filled in autumn, and is warm all winter with the store empty") {
        GameSetup rules = setup(0b1100);  // Autumn, then winter.
        rules.rules.climate.minutes = {0, 0, 5, 4};
        Game g(core(), map_for(92), rules);
        provide(g);
        const auto [tx, tz] = town(g);
        const EntityId house = put(g, "core:house", tx + 22, tz - 20);
        const EntityId plain = put(g, "core:house", tx + 22, tz + 20);
        REQUIRE(house.valid());
        REQUIRE(plain.valid());
        REQUIRE(beside(g, house, "core:annex_woodshed", 1).valid());
        CHECK(g.firewood_room(at(g, house)) == 80);
        CHECK(g.firewood_room(at(g, plain)) == village::kHouseFirewood);
        const DefIndex fw = g.content().find_resource("core:firewood");
        grant(g, "core:firewood", 30);
        const std::int32_t all = g.stored(0)[fw];
        REQUIRE(all <= 80);
        REQUIRE(g.calendar().season == Season::Autumn);
        std::int32_t most = 0;
        std::int32_t most_plain = 0;
        while (g.calendar().season == Season::Autumn) {
            g.step();
            most = std::max(most, firewood(g, at(g, house)));
            most_plain = std::max(most_plain, firewood(g, at(g, plain)));
        }
        MESSAGE("firewood: " << all << " in all; the house with a woodshed had up to " << most << ", the other up to " << most_plain);
        CHECK(most > village::kHouseFirewood);
        CHECK(most <= 80);
        CHECK(most_plain <= village::kHouseFirewood);
        // The town's stores are empty: it is all at home.
        std::int32_t stored = 0;
        for (const Building& b : g.buildings().data()) {
            stored += g.content().buildings[b.def].kind != BuildingKind::House ? firewood(g, b) : 0;
        }
        CHECK(stored == 0);
        REQUIRE(!at(g, house).residents.empty());
        const std::int32_t at_winter = firewood(g, at(g, house));
        bool warm = true;
        std::uint64_t winter_days = 0;
        const std::uint64_t first = g.tick() / g.day_ticks();
        while (g.calendar().season == Season::Winter && g.calendar().year == 1) {
            g.step();
            warm = warm && at(g, house).heated;
            winter_days = g.tick() / g.day_ticks() - first;
        }
        MESSAGE("winter: " << winter_days << " days; the woodshed's house began it with " << at_winter << " and ended it with "
                           << firewood(g, at(g, house)));
        CHECK(winter_days >= 20);
        CHECK(warm);
        CHECK(firewood(g, at(g, house)) < at_winter);  // It did burn.
    }

    TEST_CASE("saving and loading keeps the annexes of a house and what they give") {
        GameSetup rules = setup(0b1100);
        Game g(core(), map_for(92), rules);
        provide(g);
        grant(g, "core:firewood", 200);
        const auto [tx, tz] = town(g);
        const EntityId house = put(g, "core:house", tx + 22, tz - 20);
        REQUIRE(house.valid());
        REQUIRE(beside(g, house, "core:annex_clothesline", 1).valid());
        REQUIRE(beside(g, house, "core:annex_home_shrine", 1).valid());
        REQUIRE(beside(g, house, "core:annex_rain_barrel", 2).valid());
        REQUIRE(beside(g, house, "core:annex_woodshed", 1).valid());
        REQUIRE(put(g, "core:annex_playground", tx + 22, tz - 34).valid());
        days(g, 4);
        REQUIRE(std::popcount(static_cast<unsigned>(at(g, house).annexes)) == 5);
        BinaryWriter w;
        g.save(w);
        Game loaded(core(), map_for(92), rules);
        BinaryReader r(w.bytes());
        REQUIRE(loaded.load(r, core()));
        CHECK(loaded.hash() == g.hash());
        CHECK(at(loaded, house).annexes == at(g, house).annexes);
        CHECK(loaded.firewood_room(at(loaded, house)) == 80);
        days(g, 3);
        days(loaded, 3);
        CHECK(loaded.hash() == g.hash());
        CHECK(at(loaded, house).happiness == at(g, house).happiness);
        CHECK(firewood(loaded, at(loaded, house)) == firewood(g, at(g, house)));
    }

    // Not a test: a saved game with a row of houses and every annex. Run it
    // by name:
    //   salvaciudad_tests -ts=annexes -tc="manual*" --no-skip
    // It writes <temp>/SalvaCiudad/manual_annexes.scsave: copy it to the saves
    // folder and load it.
    TEST_CASE("manual: a saved game with houses and their annexes" * doctest::skip()) {
        std::error_code ec;
        const std::filesystem::path folder = std::filesystem::temp_directory_path(ec) / "SalvaCiudad";
        std::filesystem::create_directories(folder, ec);
        GameSetup rules = setup(0b1111);
        rules.rules.fog = FogMode::None;
        Game g(core(), map_for(92), rules);
        provide(g);
        grant(g, "core:firewood", 200);
        const auto [tx, tz] = town(g);
        const char* annexes[] = {"core:annex_clothesline", "core:annex_home_shrine", "core:annex_rain_barrel", "core:annex_woodshed"};
        for (int i = 0; i < 4; ++i) {
            const EntityId house = put(g, "core:house", tx + 18 + 12 * i, tz - 16);
            REQUIRE(house.valid());
            REQUIRE(beside(g, house, annexes[i], 1).valid());
        }
        REQUIRE(put(g, "core:annex_playground", tx + 30, tz - 4).valid());
        days(g, 6);
        save::SaveData data;
        data.header.name = "annexes";
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
        REQUIRE(save::write_file(folder / "manual_annexes.scsave", data));
        MESSAGE("town center at (" << tx << ", " << tz << ")");
    }
}
