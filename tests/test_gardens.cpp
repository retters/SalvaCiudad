#include <doctest.h>

#include <algorithm>
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

// The base game, with gardens and hives that give clay: something nobody
// eats, to count it; and hives that hold a lot, so that nothing is carried off.
std::shared_ptr<const Content> counting() {
    auto c = std::make_shared<Content>(test::core_content());
    const DefIndex clay = c->find_resource("core:clay");
    for (BuildingDef& b : c->buildings) {
        if (!b.garden_gives.empty()) {
            b.garden_gives = {{clay, 1}};
        }
        if (b.hive_gives != kNoDef) {
            b.hive_gives = clay;
            b.storage = 1000;
        }
    }
    return c;
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

void build_all(Game& g) {
    Command done;
    done.type = CommandType::DevBuild;
    g.apply(done);
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
    build_all(g);
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

// The flowers around a building of `def` standing at (x, z), as a house counts them.
std::int32_t around(const Game& g, const BuildingDef& d, std::int32_t x, std::int32_t z, std::int32_t m = village::kFlowerMeters) {
    return g.flowers(x - m, z - m, x + d.width - 1 + m, z + d.depth - 1 + m);
}

// A building of `def` where the flowers around it are thickest (or, with
// `bare`, where there are none), within 120 m of the town; built at once.
EntityId put_by_flowers(Game& g, const char* def, bool bare, std::int32_t apart_from_x = -1000, std::int32_t apart_from_z = -1000) {
    const DefIndex d = g.content().find_building(def);
    REQUIRE(d != kNoDef);
    const BuildingDef& bd = g.content().buildings[d];
    const auto [tx, tz] = town(g);
    std::int32_t best = -1;
    std::int32_t bx = 0, bz = 0;
    for (std::int32_t dz = -120; dz <= 120; dz += 4) {
        for (std::int32_t dx = -120; dx <= 120; dx += 4) {
            const std::int32_t x = tx + dx, z = tz + dz;
            if (std::max(std::abs(dx), std::abs(dz)) < 24 || std::max(std::abs(x - apart_from_x), std::abs(z - apart_from_z)) < 50 ||
                g.can_place(0, d, x, z, 0) != PlaceError::None) {
                continue;
            }
            // Room around it too: for a fence, a field.
            bool open = true;
            for (std::int32_t oz = -10; oz <= 10 && open; oz += 5) {
                for (std::int32_t ox = -10; ox <= 10 && open; ox += 5) {
                    open = g.nav().walkable((x + ox) / NavGrid::kCellMeters, (z + oz) / NavGrid::kCellMeters);
                }
            }
            if (!open) {
                continue;
            }
            const std::int32_t flowers = around(g, bd, x, z, 9);
            if (bare ? flowers == 0 && best < 0 : flowers > best) {
                best = flowers;
                bx = x;
                bz = z;
            }
        }
    }
    REQUIRE(best >= 0);
    return place_at(g, d, bx, bz);
}

void trace(Game& g, const char* def, std::int32_t x0, std::int32_t z0, std::int32_t x1, std::int32_t z1) {
    Command c;
    c.type = CommandType::Trace;
    c.def = g.content().find_building(def);
    REQUIRE(c.def != kNoDef);
    c.position = {Fixed::from_int(x0), Fixed::from_int(z0)};
    c.value = x1;
    c.value2 = z1;
    g.apply(c);
    build_all(g);
}

std::int32_t count(const Game& g, const char* def) {
    const DefIndex d = g.content().find_building(def);
    std::int32_t n = 0;
    for (const Building& b : g.buildings().data()) {
        n += b.def == d && b.state == BuildingState::Complete ? 1 : 0;
    }
    return n;
}

const Building& at(const Game& g, EntityId id) {
    const Building* b = g.buildings().get(id);
    REQUIRE(b != nullptr);
    return *b;
}

FixedVec2 middle(const Building& b) {
    return {Fixed::from_int(b.x) + Fixed::from_ratio(b.width, 2), Fixed::from_int(b.z) + Fixed::from_ratio(b.depth, 2)};
}

// `n` modules of a line along the south wall of `b`, a meter from it, from its west corner on.
void fence_south(Game& g, const Building& b, const char* def, std::int32_t from, std::int32_t n) {
    const std::int32_t z = b.z + b.depth + 1;
    trace(g, def, b.x - 2 + 2 * from, z, b.x - 2 + 2 * (from + n - 1), z);
}

// `n` modules of a line around `b`, a meter from its walls: along its south wall, then its north one.
void fence_around(Game& g, const Building& b, const char* def, std::int32_t from, std::int32_t n) {
    std::vector<std::pair<std::int32_t, std::int32_t>> spots;
    for (const std::int32_t z : {b.z + b.depth + 1, b.z - 3}) {
        for (std::int32_t x = b.x - 2; x <= b.x + b.width; x += 2) {
            spots.emplace_back(x, z);
        }
    }
    REQUIRE(static_cast<std::size_t>(from + n) <= spots.size());
    for (std::int32_t i = from; i < from + n; ++i) {
        trace(g, def, spots[static_cast<std::size_t>(i)].first, spots[static_cast<std::size_t>(i)].second,
              spots[static_cast<std::size_t>(i)].first, spots[static_cast<std::size_t>(i)].second);
    }
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

// Fields of a farm over the ground around `b`: as many of the four sides as take one. How many.
int plough_around(Game& g, EntityId farm, const Building& b, std::int32_t w = 8) {
    int placed = 0;
    const std::pair<std::int32_t, std::int32_t> spots[] = {{b.x - 1, b.z - w - 1},
                                                           {b.x - 1, b.z + b.depth + 1},
                                                           {b.x - w - 1, b.z - 1},
                                                           {b.x + b.width + 1, b.z - 1}};
    for (const auto& [x, z] : spots) {
        if (g.can_place_field(0, farm, x, z, w, w) != PlaceError::None) {
            continue;
        }
        Command c;
        c.type = CommandType::PlaceField;
        c.entity = farm;
        c.position = {Fixed::from_int(x), Fixed::from_int(z)};
        c.value = w | (w << 8);
        g.apply(c);
        ++placed;
    }
    return placed;
}

}  // namespace

TEST_SUITE("gardens") {
    TEST_CASE("the base game's gardens and hives") {
        const Content& c = test::core_content();
        const BuildingDef& picket = c.buildings[c.find_building("core:picket_fence")];
        CHECK(picket.garden_modules == 6);
        CHECK(picket.garden_house);
        CHECK_FALSE(picket.garden_formal);
        CHECK(picket.garden_desirability == 2);
        REQUIRE(picket.garden_gives.size() == 1);
        CHECK(picket.garden_gives[0].resource == c.find_resource("core:vegetables"));
        CHECK(picket.garden_gives[0].amount == 1);
        const BuildingDef& hedge = c.buildings[c.find_building("core:boxhedge")];
        CHECK(hedge.garden_modules == 6);
        CHECK(hedge.garden_formal);
        CHECK_FALSE(hedge.garden_house);
        CHECK(c.buildings[c.find_building("core:hedge")].garden_modules == 0);
        for (const char* id : {"core:decor_beehives", "core:decor_beehive"}) {
            const BuildingDef& hive = c.buildings[c.find_building(id)];
            CHECK(hive.hive_gives == c.find_resource("core:honey"));
            CHECK(hive.hive_radius == 30);
            CHECK(hive.storage > 0);
            CHECK(hive.workers == 0);
        }
    }

    TEST_CASE("a house with five modules of picket fence has no garden; with six it has, and its place is nicer by two") {
        Game g(core(), map_for(92), setup());
        provide(g);
        const EntityId house = put_by_flowers(g, "core:house", true);
        REQUIRE(house.valid());
        days(g, 1);
        const std::int32_t before = at(g, house).desirability;
        fence_south(g, at(g, house), "core:picket_fence", 0, 5);
        REQUIRE(count(g, "core:picket_fence") == 5);
        CHECK(at(g, house).garden == 0);
        days(g, 1);
        CHECK(at(g, house).desirability == before);
        fence_south(g, at(g, house), "core:picket_fence", 5, 1);
        REQUIRE(count(g, "core:picket_fence") == 6);
        CHECK(at(g, house).garden == garden::kHouse);  // At once.
        days(g, 1);
        CHECK(at(g, house).desirability == before + 2);
        CHECK(at(g, house).desirability == g.desirability_at(middle(at(g, house)), &at(g, house)));
        // More fence adds nothing; a low hedge is not a house's garden.
        fence_south(g, at(g, house), "core:picket_fence", 6, 2);
        days(g, 1);
        CHECK(at(g, house).desirability == before + 2);
        const EntityId other = put_by_flowers(g, "core:house", true, at(g, house).x, at(g, house).z);
        REQUIRE(other.valid());
        fence_south(g, at(g, other), "core:boxhedge", 0, 6);
        CHECK(at(g, other).garden == 0);
        // Six modules, but three of them too far.
        const EntityId third = put(g, "core:house", at(g, other).x + 30, at(g, other).z + 30);
        REQUIRE(third.valid());
        const Building t = at(g, third);
        fence_south(g, t, "core:picket_fence", 0, 3);
        trace(g, "core:picket_fence", t.x, t.z + t.depth + 5, t.x + 4, t.z + t.depth + 5);
        CHECK(at(g, third).garden == 0);
    }

    TEST_CASE("a house garden sends what it gives to the storage every quarter of the year, unless it froze") {
        // (Clay for the vegetables: nobody eats it, so it can be counted.)
        // (No food granted, and a storehouse: there must be room for what comes, or it is lost.)
        Game g(counting(), map_for(92), setup());
        const auto [tx, tz] = town(g);
        REQUIRE(put(g, "core:storehouse", tx - 24, tz).valid());
        const EntityId house = put(g, "core:house", tx + 22, tz - 20);
        const EntityId plain = put(g, "core:house", tx + 22, tz + 20);
        REQUIRE(house.valid());
        REQUIRE(plain.valid());
        fence_south(g, at(g, house), "core:picket_fence", 0, 6);
        REQUIRE(at(g, house).garden == garden::kHouse);
        const std::int32_t had = have(g, "core:clay");
        const std::uint32_t quarter = g.year_ticks() / 4;
        // A year: a unit from the one garden each time three months have gone by.
        int quarters = 0;
        std::uint32_t was = (g.calendar().month - 1) / 3;
        for (std::uint32_t t = 0; t < g.year_ticks(); ++t) {
            g.step();
            const std::uint32_t now = (g.calendar().month - 1) / 3;
            if (now != was) {
                was = now;
                ++quarters;
                CHECK(have(g, "core:clay") == had + quarters);  // That very day.
            }
        }
        CHECK(quarters == 4);
        CHECK(have(g, "core:clay") == had + 4);
        // In a land where it is always winter, nothing.
        Game cold(counting(), map_for(92), setup(0b1000));
        REQUIRE(put(cold, "core:storehouse", tx - 24, tz).valid());
        const EntityId icy = put(cold, "core:house", tx + 22, tz - 20);
        REQUIRE(icy.valid());
        fence_south(cold, at(cold, icy), "core:picket_fence", 0, 6);
        REQUIRE(at(cold, icy).garden == garden::kHouse);
        const std::int32_t cold_had = have(cold, "core:clay");
        bool froze = false;
        for (std::uint32_t t = 0; t < quarter + 2 * cold.day_ticks(); ++t) {
            cold.step();
            froze = froze || cold.frozen();
        }
        REQUIRE(froze);
        CHECK(have(cold, "core:clay") == cold_had);
    }

    TEST_CASE("six modules of low hedge by a statue double what it adds to a house's place") {
        Game g(core(), map_for(92), setup());
        provide(g);
        const EntityId house = put_by_flowers(g, "core:house", true);
        REQUIRE(house.valid());
        const Building h = at(g, house);
        // An obelisk some fifteen meters from the house.
        const EntityId statue = put(g, "core:decor_obelisk", h.x + 2, h.z + 18);
        REQUIRE(statue.valid());
        const std::int32_t worth = g.content().buildings[at(g, statue).def].desirability;
        REQUIRE(worth > 0);
        days(g, 1);
        const std::int32_t alone = at(g, house).desirability;
        const std::int32_t without = g.desirability_at(middle(h)) - g.desirability_at(middle(h), &at(g, statue));
        REQUIRE(without > 0);  // What the statue adds there.
        fence_around(g, at(g, statue), "core:boxhedge", 0, 5);
        REQUIRE(count(g, "core:boxhedge") == 5);
        CHECK(at(g, statue).garden == 0);
        fence_around(g, at(g, statue), "core:boxhedge", 5, 1);
        REQUIRE(count(g, "core:boxhedge") == 6);
        CHECK(at(g, statue).garden == garden::kFormal);
        // The hedge's own reach (6 m) does not get to the house.
        const std::int32_t with = g.desirability_at(middle(h)) - g.desirability_at(middle(h), &at(g, statue));
        CHECK(with >= 2 * without);
        CHECK(with <= 2 * without + 1);  // (Whole numbers: twice the statue's worth, then the distance.)
        days(g, 1);
        CHECK(at(g, house).desirability == alone + with - without);
        // A picket fence makes no formal garden, and an annex or a hedge is not a statue.
        const EntityId second = put(g, "core:decor_obelisk", h.x + 40, h.z + 40);
        REQUIRE(second.valid());
        fence_around(g, at(g, second), "core:picket_fence", 0, 6);
        REQUIRE(count(g, "core:picket_fence") == 6);
        CHECK(at(g, second).garden == 0);
    }

    TEST_CASE("a house by a meadow in flower is a nicer place from spring to autumn, and not in winter") {
        GameSetup rules = setup(0b1111);
        rules.rules.climate.minutes = {2, 2, 2, 2};
        Game g(core(), map_for(92), rules);
        provide(g);
        grant(g, "core:firewood", 2000);
        const EntityId house = put_by_flowers(g, "core:house", false);
        const EntityId bare = put_by_flowers(g, "core:house", true);
        REQUIRE(house.valid());
        REQUIRE(bare.valid());
        REQUIRE(g.calendar().season == Season::Spring);
        const std::int32_t flowers = g.flower_beauty(at(g, house));
        MESSAGE("flowers around the house: " << around(g, g.content().buildings[at(g, house).def], at(g, house).x, at(g, house).z)
                                             << ", worth " << flowers);
        REQUIRE(flowers >= 2);
        CHECK(flowers <= village::kMaxFlowerBeauty);
        CHECK(g.flower_beauty(at(g, bare)) == 0);
        days(g, 1);
        // (Without the cat that may come with the months, phase 106.)
        const auto place = [&](EntityId id) { return at(g, id).desirability - (at(g, id).cat != 0 ? village::kCatBeauty : 0); };
        const std::int32_t in_spring = place(house);
        const std::int32_t bare_in_spring = place(bare);
        CHECK(at(g, house).desirability == g.desirability_at(middle(at(g, house)), &at(g, house)));
        while (g.calendar().season != Season::Autumn) {
            g.step();
        }
        days(g, 1);
        CHECK(g.flower_beauty(at(g, house)) == flowers);
        CHECK(place(house) == in_spring);
        while (g.calendar().season != Season::Winter) {
            g.step();
        }
        days(g, 1);
        CHECK(g.flower_beauty(at(g, house)) == 0);
        CHECK(place(house) == in_spring - flowers);
        CHECK(place(bare) == bare_in_spring);
        while (g.calendar().season != Season::Spring) {
            g.step();
        }
        days(g, 1);
        CHECK(place(house) == in_spring);
    }

    TEST_CASE("ploughing the meadow takes its flowers from the house beside it") {
        Game g(core(), map_for(92), setup());
        provide(g);
        const EntityId house = put_by_flowers(g, "core:house", false);
        REQUIRE(house.valid());
        const Building h = at(g, house);
        const std::int32_t flowers = g.flower_beauty(h);
        const std::int32_t thick = around(g, g.content().buildings[h.def], h.x, h.z);
        REQUIRE(flowers >= 2);
        days(g, 1);
        const std::int32_t before = at(g, house).desirability;
        const EntityId farm = put(g, "core:farm", h.x + 22, h.z);
        REQUIRE(farm.valid());
        days(g, 1);
        const std::int32_t with_farm = at(g, house).desirability;  // (A farm has its own say on the place.)
        const std::int32_t flowers_with_farm = g.flower_beauty(at(g, house));
        const int fields = plough_around(g, farm, h);
        REQUIRE(fields >= 2);
        const std::int32_t left = around(g, g.content().buildings[h.def], h.x, h.z);
        MESSAGE("flowers: " << thick << " before, " << left << " with " << fields << " fields around; the house had " << before
                            << " and with the farm " << with_farm);
        CHECK(left < thick / 2);
        const std::int32_t after = g.flower_beauty(at(g, house));
        CHECK(after < flowers_with_farm);
        days(g, 1);
        CHECK(at(g, house).desirability == with_farm - (flowers_with_farm - after));
        // A road over them does the same.
        CHECK(g.flowers(h.x - 6, h.z - 6, h.x - 1, h.z + h.depth + 5) >= 0);
    }

    TEST_CASE("a hive in a meadow makes more than one with fields around it, and none in winter") {
        // (Hives that give clay: see counting().)
        const auto play = [](bool ploughed, std::int32_t& found) {
            Game g(counting(), map_for(92), setup());
            provide(g);
            const EntityId hive = put_by_flowers(g, "core:decor_beehives", false);
            REQUIRE(hive.valid());
            const Building b = at(g, hive);
            if (ploughed) {
                const EntityId farm = put(g, "core:farm", b.x + 26, b.z);
                REQUIRE(farm.valid());
                REQUIRE(plough_around(g, farm, b, 16) >= 2);
            }
            found = g.nectar(at(g, hive));
            const std::int32_t had = have(g, "core:clay");
            run(g, g.year_ticks() / 2);
            return have(g, "core:clay") - had;
        };
        std::int32_t meadow_nectar = 0, field_nectar = 0;
        const std::int32_t meadow = play(false, meadow_nectar);
        const std::int32_t fields = play(true, field_nectar);
        MESSAGE("in half a year: " << meadow << " in the meadow (" << meadow_nectar << " a day), " << fields << " among fields ("
                                   << field_nectar << " a day)");
        CHECK(meadow_nectar > 0);
        CHECK(field_nectar < meadow_nectar);
        CHECK(meadow > 0);
        CHECK(fields < meadow);
        // What it makes is what it finds: a unit for every kNectarPerUnit.
        const std::int32_t calendar_days = 60;
        CHECK(meadow >= meadow_nectar * (calendar_days - 2) / village::kNectarPerUnit);
        CHECK(meadow <= meadow_nectar * calendar_days / village::kNectarPerUnit + 1);
        // Winter.
        Game cold(counting(), map_for(92), setup(0b1000));
        const EntityId hive = put_by_flowers(cold, "core:decor_beehives", false);
        REQUIRE(hive.valid());
        CHECK(cold.nectar(at(cold, hive)) == 0);
        const std::int32_t had = have(cold, "core:clay");
        run(cold, cold.year_ticks() / 4);
        CHECK(have(cold, "core:clay") == had);
    }

    TEST_CASE("laborers carry a hive's honey to the storage") {
        // The base game's hive, with honey for the taking sooner.
        auto c = std::make_shared<Content>(test::core_content());
        for (BuildingDef& b : c->buildings) {
            if (b.hive_gives != kNoDef) {
                b.storage = 4;
            }
        }
        Game g(c, map_for(92), setup());
        const EntityId hive = put_by_flowers(g, "core:decor_beehives", false);
        REQUIRE(hive.valid());
        REQUIRE(g.nectar(at(g, hive)) > 0);
        const DefIndex honey = g.content().find_resource("core:honey");
        const std::int32_t had = g.stored(0)[honey];
        bool carried = false;
        for (std::uint32_t t = 0; t < 2 * g.year_ticks() && !carried; ++t) {
            g.step();
            for (const Villager& v : g.villagers().data()) {
                carried = carried || (v.carrying.resource == honey && v.carrying.amount > 0 && v.task == Task::GoDeliver);
            }
        }
        CHECK(carried);
        run(g, 1500);
        const Building* tc = g.buildings().get(g.player(0).town_center);
        std::int32_t in_store = 0;
        for (const Stock& s : tc->stock) {
            in_store += s.resource == honey ? s.amount : 0;
        }
        MESSAGE("honey: " << had << " to begin with, " << in_store << " in the town center, " << have(g, "core:honey") << " in all");
        CHECK(have(g, "core:honey") > 0);
    }

    TEST_CASE("saving and loading keeps gardens, formal gardens and what a hive has gathered") {
        Game g(core(), map_for(92), setup());
        provide(g);
        const EntityId house = put_by_flowers(g, "core:house", false);
        REQUIRE(house.valid());
        fence_south(g, at(g, house), "core:picket_fence", 0, 6);
        const EntityId statue = put(g, "core:decor_obelisk", at(g, house).x + 2, at(g, house).z + 24);
        REQUIRE(statue.valid());
        fence_around(g, at(g, statue), "core:boxhedge", 0, 6);
        const EntityId hive = put(g, "core:decor_beehives", at(g, house).x + 12, at(g, house).z - 12);
        REQUIRE(hive.valid());
        days(g, 7);
        REQUIRE(at(g, house).garden == garden::kHouse);
        REQUIRE(at(g, statue).garden == garden::kFormal);
        BinaryWriter w;
        g.save(w);
        Game loaded(core(), map_for(92), setup());
        BinaryReader r(w.bytes());
        REQUIRE(loaded.load(r, core()));
        CHECK(loaded.hash() == g.hash());
        CHECK(at(loaded, house).garden == garden::kHouse);
        CHECK(at(loaded, statue).garden == garden::kFormal);
        CHECK(at(loaded, hive).work_done == at(g, hive).work_done);
        CHECK(loaded.flower_beauty(at(loaded, house)) == g.flower_beauty(at(g, house)));
        run(g, g.year_ticks() / 4 + 200);
        run(loaded, loaded.year_ticks() / 4 + 200);
        CHECK(loaded.hash() == g.hash());
        CHECK(have(loaded, "core:honey") == have(g, "core:honey"));
    }

    // Not a test: a saved game with a house in its garden, a statue in its
    // formal garden and two hives. Run it by name:
    //   salvasprosperia_tests -ts=gardens -tc="manual*" --no-skip
    // It writes <temp>/SalvasProsperia/manual_gardens.scsave: copy it to the saves
    // folder and load it.
    TEST_CASE("manual: a saved game with gardens and hives" * doctest::skip()) {
        std::error_code ec;
        const std::filesystem::path folder = std::filesystem::temp_directory_path(ec) / "SalvasProsperia";
        std::filesystem::create_directories(folder, ec);
        GameSetup rules = setup(0b1111);
        rules.rules.fog = FogMode::None;
        Game g(core(), map_for(92), rules);
        provide(g);
        const auto [tx, tz] = town(g);
        const EntityId house = put(g, "core:house", tx + 20, tz - 14);
        REQUIRE(house.valid());
        const Building h = at(g, house);
        trace(g, "core:picket_fence", h.x - 2, h.z + h.depth + 1, h.x + h.width, h.z + h.depth + 1);
        trace(g, "core:picket_fence", h.x - 2, h.z - 2, h.x - 2, h.z + h.depth + 1);
        const EntityId statue = put(g, "core:decor_obelisk", tx + 36, tz - 12);
        REQUIRE(statue.valid());
        const Building s = at(g, statue);
        trace(g, "core:boxhedge", s.x - 3, s.z - 3, s.x + s.width + 1, s.z - 3);
        trace(g, "core:boxhedge", s.x - 3, s.z + s.depth + 1, s.x + s.width + 1, s.z + s.depth + 1);
        REQUIRE(put(g, "core:decor_beehives", tx + 20, tz + 12).valid());
        REQUIRE(put_by_flowers(g, "core:decor_beehive", false).valid());
        days(g, 8);
        save::SaveData data;
        data.header.name = "gardens";
        data.header.game_version = SC_VERSION_STRING;
        data.header.saved_at = "2026-10-05T00:00:00";
        data.header.rules_version = kGameRulesVersion;
        data.header.content_hash = g.content().hash;
        data.header.seed = g.map().settings.seed;
        data.header.tick = g.tick();
        data.header.population = static_cast<std::uint32_t>(g.population(0));
        BinaryWriter w;
        g.save(w);
        data.put("GAME", std::move(w.bytes()));
        REQUIRE(save::write_file(folder / "manual_gardens.scsave", data));
        MESSAGE("town center at (" << tx << ", " << tz << "); house garden " << int(at(g, house).garden) << ", statue "
                                   << int(at(g, statue).garden));
    }
}
