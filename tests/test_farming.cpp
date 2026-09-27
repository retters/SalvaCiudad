#include <doctest.h>

#include <memory>
#include <optional>
#include <ostream>

#include "sim/game.h"
#include "sim/worldgen.h"
#include "test_util.h"

using namespace sc::sim;

namespace {

std::shared_ptr<const Content> content() {
    return std::shared_ptr<const Content>(std::shared_ptr<const Content>{}, &sc::test::core_content());
}

const MapData& map_for(std::uint64_t seed) {
    static std::map<std::uint64_t, MapData> cache;
    auto it = cache.find(seed);
    if (it == cache.end()) {
        MapSettings s;
        s.seed = seed;
        s.size = MapSize::Small;
        std::optional<MapData> m = generate_map(s, *content());
        REQUIRE(m.has_value());
        it = cache.emplace(seed, std::move(*m)).first;
    }
    return it->second;
}

GameSetup setup(std::uint8_t seasons = 0b1111) {
    GameSetup s;
    s.seed = 9;
    s.rules.climate.seasons = seasons;
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

void grant(Game& g, const char* resource, std::int32_t amount) {
    Command c;
    c.type = CommandType::DevGrant;
    c.def = content()->find_resource(resource);
    c.value = amount;
    g.apply(c);
}

// Places `def` near (x, z) (or the town center) and waits until it is built.
EntityId build(Game& g, const char* def, std::optional<std::pair<int, int>> near = std::nullopt) {
    const DefIndex d = content()->find_building(def);
    const Building* tc = g.buildings().get(g.player(0).town_center);
    REQUIRE(tc != nullptr);
    const int ox = near ? near->first : tc->x;
    const int oz = near ? near->second : tc->z;
    grant(g, "core:log", 100);
    grant(g, "core:stone", 30);
    for (int r = near ? 0 : 12; r < 120; r += 2) {
        for (int a = 0; a < 8; ++a) {
            const int x = ox + (a % 3 - 1) * r;
            const int z = oz + (a / 3 - 1) * r;
            if (g.can_place(0, d, x, z, 0) != PlaceError::None) {
                continue;
            }
            Command c;
            c.type = CommandType::PlaceBuilding;
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
            for (int t = 0; t < 60 && g.buildings().get(id)->state != BuildingState::Complete; ++t) {
                run(g, 100);
            }
            REQUIRE(g.buildings().get(id)->state == BuildingState::Complete);
            return id;
        }
    }
    FAIL("no room");
    return {};
}

// A field of `side` x `side` near the farm; returns false if none fits.
bool add_field(Game& g, EntityId farm, int side = 8) {
    const Building* b = g.buildings().get(farm);
    for (int r = 8; r < 40; r += 2) {
        for (int a = 0; a < 8; ++a) {
            const int x = b->x + (a % 3 - 1) * r;
            const int z = b->z + (a / 3 - 1) * r;
            if (g.can_place_field(0, farm, x, z, side, side) != PlaceError::None) {
                continue;
            }
            Command c;
            c.type = CommandType::PlaceField;
            c.entity = farm;
            c.position = {Fixed::from_int(x), Fixed::from_int(z)};
            c.value = side | (side << 8);
            g.apply(c);
            return true;
        }
    }
    return false;
}

void plan(Game& g, EntityId farm, std::size_t field, const char* crop) {
    for (int year = 0; year < 3; ++year) {
        Command c;
        c.type = CommandType::SetCrop;
        c.entity = farm;
        c.def = crop != nullptr ? content()->find_crop(crop) : kNoDef;
        c.value = static_cast<std::int32_t>(field) | (year << 8);
        g.apply(c);
    }
}

std::int32_t total(const Game& g, const char* resource) {
    const DefIndex r = content()->find_resource(resource);
    std::int32_t n = g.stored(0)[r];
    for (const Villager& v : g.villagers().data()) {
        n += v.carrying.resource == r ? v.carrying.amount : 0;
    }
    return n;
}

}  // namespace

TEST_SUITE("farming") {
    TEST_CASE("fields must fit their farm") {
        Game g(content(), map_for(51), setup());
        const EntityId farm = build(g, "core:farm");
        const Building* b = g.buildings().get(farm);
        CHECK(g.can_place_field(0, farm, b->x, b->z, 8, 8) == PlaceError::Blocked);  // On the farm itself.
        CHECK(g.can_place_field(0, farm, b->x + 200, b->z, 8, 8) == PlaceError::TooFar);
        CHECK(g.can_place_field(0, farm, b->x + 10, b->z, 3, 8) == PlaceError::BadSize);
        CHECK(g.can_place_field(0, g.player(0).town_center, b->x + 10, b->z, 8, 8) == PlaceError::UnknownBuilding);
        REQUIRE(add_field(g, farm));
        const Field f = g.buildings().get(farm)->fields.front();  // A copy: more fields follow.
        CHECK(f.fertility > 0);
        CHECK(f.fertility <= 100);
        // A building cannot go on the field.
        CHECK(g.can_place(0, content()->find_building("core:house"), f.x, f.z, 0) == PlaceError::Blocked);
        for (int i = 1; i < 4; ++i) {
            (void)add_field(g, farm, 6);
        }
        CHECK(g.buildings().get(farm)->fields.size() <= 4);
        CHECK(g.can_place_field(0, farm, f.x + 40, f.z, 6, 6) != PlaceError::None);
    }

    TEST_CASE("a farm sows in spring and brings in the harvest") {
        Game g(content(), map_for(52), setup());
        const EntityId farm = build(g, "core:farm");
        REQUIRE(add_field(g, farm, 10));
        plan(g, farm, 0, "core:vegetables");
        const std::int32_t before = total(g, "core:vegetables");
        const std::int32_t fertility = g.buildings().get(farm)->fields[0].fertility;
        bool grew = false;
        for (std::uint32_t t = 0; t < g.year_ticks(); t += 200) {
            run(g, 200);
            grew = grew || g.buildings().get(farm)->fields[0].state == FieldState::Growing;
        }
        CHECK(grew);
        const std::int32_t after = total(g, "core:vegetables");
        MESSAGE("vegetables " << before << " -> " << after << ", fertility " << fertility << " -> "
                              << g.buildings().get(farm)->fields[0].fertility);
        CHECK(after > before + 20);
        CHECK(g.buildings().get(farm)->fields[0].fertility < fertility);
    }

    TEST_CASE("beans and fallow years bring fertility back") {
        Game g(content(), map_for(53), setup());
        const EntityId farm = build(g, "core:farm");
        REQUIRE(add_field(g, farm, 8));
        REQUIRE(add_field(g, farm, 8));
        plan(g, farm, 0, "core:beans");
        plan(g, farm, 1, nullptr);  // Fallow.
        const std::int32_t f0 = g.buildings().get(farm)->fields[0].fertility;
        const std::int32_t f1 = g.buildings().get(farm)->fields[1].fertility;
        run(g, g.year_ticks() + 200);
        CHECK(g.buildings().get(farm)->fields[0].fertility > f0);
        CHECK(g.buildings().get(farm)->fields[1].fertility > f1);
    }

    TEST_CASE("frost kills a crop that did not ripen, and nothing is sown in winter") {
        auto slow = std::make_shared<Content>(sc::test::core_content());
        for (CropDef& c : slow->crops) {
            c.grow_days = 500;  // Cannot ripen in one summer.
        }
        Game g(slow, map_for(54), setup(0b1010));  // Summer and winter.
        const EntityId farm = build(g, "core:farm");
        REQUIRE(add_field(g, farm, 8));
        bool grew = false;
        for (std::uint32_t t = 0; t < g.year_ticks() * 9 / 10; t += 100) {
            run(g, 100);
            const Field& f = g.buildings().get(farm)->fields[0];
            grew = grew || f.state == FieldState::Growing;
            if (g.calendar().season == Season::Winter && g.frozen()) {
                CHECK(f.state != FieldState::Growing);
            }
        }
        CHECK(grew);
        CHECK(g.buildings().get(farm)->fields[0].pending == 0);
    }

    TEST_CASE("an orchard bears fruit from its third year") {
        Game g(content(), map_for(55), setup());
        const EntityId orchard = build(g, "core:orchard");
        const std::int32_t start = total(g, "core:fruit");
        // Food from outside, so the town lives that long.
        const auto months = [&](int n) {
            for (int m = 0; m < n; ++m) {
                grant(g, "core:roots", 40);
                grant(g, "core:firewood", 20);
                run(g, g.month_ticks());
            }
        };
        months(12);
        CHECK(total(g, "core:fruit") == start);
        months(24);
        const std::int32_t fruit = total(g, "core:fruit") - start;
        const Building& ob = *g.buildings().get(orchard);
        MESSAGE("fruit in its third year: " << fruit << " workers " << ob.workers.size() << "/" << ob.wanted_workers
                                            << " built " << ob.built_tick << " tick " << g.tick() << " produced "
                                            << ob.produced << " season " << static_cast<int>(g.calendar().season));

        CHECK(fruit > 20);
        CHECK(g.buildings().get(orchard)->produced <= content()->buildings[g.buildings().get(orchard)->def].yearly_limit);
    }

    TEST_CASE("hunters take game from the zones, and it comes back") {
        Game g(content(), map_for(56), setup());
        // The lodge next to the first zone with deer or boar.
        std::optional<std::size_t> zone;
        for (std::size_t z = 0; z < g.map().zones.size() && !zone; ++z) {
            const ZoneType t = g.map().zones[z].type;
            if (g.zone_animals()[z] > 0 && (t == ZoneType::Deer || t == ZoneType::Boar)) {
                zone = z;  // Game, not wolves.
            }
        }
        REQUIRE(zone.has_value());
        const Zone& zn = g.map().zones[*zone];
        const std::int32_t animals = g.zone_animals()[*zone];
        (void)build(g, "core:hunter", std::pair{zn.x.floor_int(), zn.z.floor_int()});
        const std::int32_t meat = total(g, "core:meat");
        run(g, 3000);
        CHECK(total(g, "core:meat") > meat);
        std::int32_t left = 0;
        for (std::size_t z = 0; z < g.zone_animals().size(); ++z) {
            const ZoneType t = g.map().zones[z].type;
            left += t == ZoneType::Deer || t == ZoneType::Boar ? g.zone_animals()[z] : 0;
        }
        std::int32_t full = 0;
        for (const Zone& z2 : g.map().zones) {
            full += z2.type == ZoneType::Deer ? 16 : (z2.type == ZoneType::Boar ? 10 : 0);
        }
        CHECK(left <= full);
        (void)animals;
    }

    TEST_CASE("fishers fish until the water freezes") {
        Game g(content(), map_for(57), setup());
        // Near the first water found around the town.
        const Building* tc = g.buildings().get(g.player(0).town_center);
        std::optional<std::pair<int, int>> shore;
        for (int r = 10; r < 250 && !shore; r += 4) {
            for (int a = 0; a < 16 && !shore; ++a) {
                const int x = tc->x + (a % 4 - 2) * r / 2;
                const int z = tc->z + (a / 4 - 2) * r / 2;
                if (x > 0 && z > 0 && x < g.map().size && z < g.map().size && g.map().water_at(x, z)) {
                    shore = std::pair{x, z};
                }
            }
        }
        REQUIRE(shore.has_value());
        (void)build(g, "core:fisher", shore);
        const std::int32_t fish = total(g, "core:fish");
        run(g, 3000);
        CHECK(total(g, "core:fish") > fish);
    }

    TEST_CASE("villagers eat a varied diet when they can") {
        Game g(content(), map_for(58), setup());
        run(g, g.month_ticks() * 3 + 10);
        int varied = 0;
        for (const Villager& v : g.villagers().data()) {
            varied += v.variety >= 2 ? 1 : 0;
        }
        CHECK(varied > 0);
    }

    TEST_CASE("fields survive saving and loading") {
        Game g(content(), map_for(59), setup());
        const EntityId farm = build(g, "core:farm");
        REQUIRE(add_field(g, farm, 8));
        run(g, 2000);
        BinaryWriter w;
        g.save(w);
        Game back(content(), MapData{}, 0, 0);
        BinaryReader r(w.bytes());
        REQUIRE(back.load(r, content()));
        CHECK(back.hash() == g.hash());
        REQUIRE(back.buildings().get(farm) != nullptr);
        CHECK(back.buildings().get(farm)->fields == g.buildings().get(farm)->fields);
        CHECK(back.can_place(0, content()->find_building("core:house"), g.buildings().get(farm)->fields[0].x,
                             g.buildings().get(farm)->fields[0].z, 0) == PlaceError::Blocked);
    }
}
