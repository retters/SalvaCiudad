#include <doctest.h>

#include <algorithm>
#include <cmath>
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

// The test map with no zones but the glade of a unicorn, `meters` from the
// start over dry ground (or, `far`, in the corner of the map farthest from it).
MapData glade_map(bool far = false, std::int32_t meters = 70) {
    MapData m = map_for(92);
    m.zones.clear();
    REQUIRE(!m.starts.empty());
    const std::int32_t sx = m.starts[0].x.floor_int(), sz = m.starts[0].z.floor_int();
    if (far) {
        m.zones.push_back({ZoneType::Unicorn, Fixed::from_int(sx < m.size / 2 ? m.size - 30 : 30),
                           Fixed::from_int(sz < m.size / 2 ? m.size - 30 : 30), Fixed::from_int(worldgen::kGladeRadius)});
        return m;
    }
    for (int a = 0; a < 16; ++a) {
        const double angle = a * 3.14159265358979 / 8.0;
        bool dry = true;
        for (int d = 0; d <= meters + 40 && dry; d += 2) {
            const auto x = static_cast<std::int32_t>(sx + std::cos(angle) * d), z = static_cast<std::int32_t>(sz + std::sin(angle) * d);
            dry = x > 8 && z > 8 && x < m.size - 8 && z < m.size - 8 && !m.water_at(x, z);
        }
        if (!dry) {
            continue;
        }
        m.zones.push_back({ZoneType::Unicorn, Fixed::from_int(static_cast<std::int32_t>(sx + std::cos(angle) * meters)),
                           Fixed::from_int(static_cast<std::int32_t>(sz + std::sin(angle) * meters)),
                           Fixed::from_int(worldgen::kGladeRadius)});
        return m;
    }
    FAIL("no dry way out of the start");
    return m;
}

// The same map without the glade.
MapData plain_map() {
    MapData m = glade_map();
    m.zones.clear();
    return m;
}

GameSetup setup(Threat diseases = Threat::None) {
    GameSetup s;
    s.seed = 15;
    s.rules.diseases = diseases;
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

std::pair<std::int32_t, std::int32_t> glade(const MapData& m) {
    for (const Zone& z : m.zones) {
        if (z.type == ZoneType::Unicorn) {
            return {z.x.floor_int(), z.z.floor_int()};
        }
    }
    FAIL("the map has no glade");
    return {0, 0};
}

bool unicorn(const Game& g) {
    for (std::size_t z = 0; z < g.map().zones.size(); ++z) {
        if (g.map().zones[z].type == ZoneType::Unicorn) {
            return g.zone_animals()[z] > 0;
        }
    }
    return false;
}

// A tree at (x, z).
void tree(Game& g, std::int32_t x, std::int32_t z) {
    Command c;
    c.type = CommandType::DevFeature;
    c.def = static_cast<std::uint16_t>(FeatureType::Tree);
    c.def2 = 0;
    c.count = 1;
    c.value = Fixed::one().raw();
    c.position = {Fixed::from_int(x), Fixed::from_int(z)};
    const std::size_t before = g.map().features.size();
    g.apply(c);
    REQUIRE(g.map().features.size() == before + 1);
}

// Trees of the map that stand: with something to fell.
int standing(const Game& g, std::int32_t x, std::int32_t z, std::int32_t radius) {
    int n = 0;
    for (std::size_t i = 0; i < g.map().features.size(); ++i) {
        const MapFeature& f = g.map().features[i];
        const std::int64_t dx = f.x.floor_int() - x, dz = f.z.floor_int() - z;
        n += f.type == FeatureType::Tree && g.nodes()[i].amount > 0 && dx * dx + dz * dz <= static_cast<std::int64_t>(radius) * radius ? 1 : 0;
    }
    return n;
}

// A town with food and a storehouse; where its center is.
std::pair<std::int32_t, std::int32_t> town(Game& g, const char* food = "core:bread") {
    grant(g, food, 6000);
    grant(g, "core:firewood", 2000);
    const Building tc = at(g, g.player(0).town_center);  // (A copy: building moves the others.)
    REQUIRE(put(g, "core:storehouse", tc.x - 26, tc.z).valid());
    return {tc.x + tc.width / 2, tc.z + tc.depth / 2};
}

int count(Game& g, Game::Event::Kind kind, std::uint8_t* other = nullptr) {
    int n = 0;
    for (const Game::Event& e : g.take_events()) {
        if (e.kind == kind) {
            ++n;
            if (other != nullptr) {
                *other = e.other;
            }
        }
    }
    return n;
}

std::uint64_t only(const Content& c, std::string_view id, bool without = false) {
    std::uint64_t mask = 0;
    for (std::size_t b = 0; b < c.flora.biomes.size(); ++b) {
        if ((c.flora.biomes[b].id == id) != without) {
            mask |= std::uint64_t{1} << b;
        }
    }
    return mask;
}

// The first villager with a home to fall ill in a town that eats mushrooms,
// with every home within 60 m of where the glade is (or would be): who, from
// which tick and for how many days.
struct Illness {
    std::uint32_t who = 0;
    std::uint32_t from = 0;
    std::uint32_t days = 0;
};
Illness first_illness(const MapData& map) {
    const auto g_owned = std::make_unique<Game>(core(), map, setup(Threat::Medium));
    Game& g = *g_owned;
    const auto [tx, tz] = town(g, "core:mushrooms");
    const auto [zx, zz] = glade(glade_map());
    for (int n = 0; n < 4; ++n) {
        const EntityId house = put(g, "core:house", (tx + zx * 2) / 3 + (n % 2) * 9, (tz + zz * 2) / 3 + (n / 2) * 9);
        REQUIRE(house.valid());
        const std::int64_t dx = at(g, house).x + at(g, house).width / 2 - zx, dz = at(g, house).z + at(g, house).depth / 2 - zz;
        REQUIRE(dx * dx + dz * dz <= village::kUnicornMeters * village::kUnicornMeters);
    }
    Illness out;
    EntityId ill;
    for (std::uint32_t t = 0; t < 2 * g.year_ticks(); ++t) {
        g.step();
        if (!ill.valid()) {
            for (std::size_t k = 0; k < g.villagers().size(); ++k) {
                const Villager& v = g.villagers().data()[k];
                if (v.disease != 0 && g.buildings().get(v.home) != nullptr) {
                    ill = g.villagers().entities()[k];
                    out.who = ill.index;
                    out.from = static_cast<std::uint32_t>(g.tick());
                    break;
                }
            }
        } else {
            const Villager* v = g.villagers().get(ill);
            REQUIRE(v != nullptr);  // (Nobody dies of a bad mushroom.)
            if (v->disease == 0) {
                out.days = (static_cast<std::uint32_t>(g.tick()) - out.from + g.day_ticks() / 2) / g.day_ticks();
                return out;
            }
        }
    }
    return out;
}

}  // namespace

TEST_SUITE("unicorn") {
    TEST_CASE("the base game: the enchanted wood has unicorns, and a glade is a zone that holds one") {
        const Content& c = test::core_content();
        for (const BiomeDef& b : c.flora.biomes) {
            CHECK(b.unicorn == (b.id == "core:enchanted"));
        }
        const auto g_owned = std::make_unique<Game>(core(), glade_map(), setup());
        Game& g = *g_owned;
        REQUIRE(g.map().zones.size() == 1);
        CHECK(g.zone_animals()[0] == 1);
        CHECK(g.zone_room(0) == 1);
        CHECK(unicorn(g));
        // It walks no map, and nobody hunts it.
        CHECK(g.creatures().size() == 0);
        const auto [tx, tz] = town(g);
        REQUIRE(put(g, "core:hunter", tx + 20, tz + 10).valid());
        run(g, 3000);
        CHECK(unicorn(g));
        CHECK(have(g, "core:meat") == 0);
    }

    TEST_CASE("a place within 60 m of the glade has 8 more of surroundings, and so has a house there") {
        const auto with_owned = std::make_unique<Game>(core(), glade_map(), setup());
        Game& with = *with_owned;
        const auto without_owned = std::make_unique<Game>(core(), plain_map(), setup());
        Game& without = *without_owned;
        const auto [gx, gz] = glade(with.map());
        const auto there = [](std::int32_t x, std::int32_t z) { return FixedVec2{Fixed::from_int(x), Fixed::from_int(z)}; };
        for (const std::int32_t d : {0, 30, 59, 60}) {
            CHECK(with.unicorn_near(gx + d, gz, village::kUnicornMeters));
            CHECK(with.desirability_at(there(gx + d, gz)) == without.desirability_at(there(gx + d, gz)) + village::kUnicornBeauty);
            CHECK(with.desirability_at(there(gx, gz - d)) == without.desirability_at(there(gx, gz - d)) + village::kUnicornBeauty);
        }
        for (const std::int32_t d : {61, 90, 200}) {
            CHECK_FALSE(with.unicorn_near(gx + d, gz, village::kUnicornMeters));
            CHECK(with.desirability_at(there(gx + d, gz)) == without.desirability_at(there(gx + d, gz)));
        }
        CHECK_FALSE(without.unicorn_near(gx, gz, village::kUnicornMeters));
        // The same house in the same place of both games.
        const auto [tx, tz] = town(with);
        (void)town(without);
        const EntityId near = put(with, "core:house", (tx + gx * 2) / 3, (tz + gz * 2) / 3);
        const EntityId same = put(without, "core:house", (tx + gx * 2) / 3, (tz + gz * 2) / 3);
        REQUIRE(near.valid());
        REQUIRE(same.valid());
        REQUIRE(at(with, near).x == at(without, same).x);
        REQUIRE(at(with, near).z == at(without, same).z);
        run(with, 300);
        run(without, 300);
        CHECK(at(with, near).desirability == at(without, same).desirability + village::kUnicornBeauty);
    }

    TEST_CASE("the sick whose home is by the glade get well in half the time") {
        // Two towns alike, one with the unicorn: the same villager falls ill of the same mushroom the same day.
        const Illness by = first_illness(glade_map());
        const Illness plain = first_illness(plain_map());
        MESSAGE("ill from tick " << by.from << ": " << by.days << " days by the unicorn, " << plain.days << " without it");
        REQUIRE(by.days > 0);
        REQUIRE(plain.days > 0);
        CHECK(by.from == plain.from);
        CHECK(by.who == plain.who);
        CHECK(plain.days >= 4);
        CHECK(by.days * 2 >= plain.days);
        CHECK(by.days * 2 <= plain.days + 1);
    }

    TEST_CASE("felling a tree by the glade drives the unicorn away for good: it is not back in ten years") {
        const auto g_owned = std::make_unique<Game>(core(), glade_map(), setup());
        Game& g = *g_owned;
        const auto [tx, tz] = town(g);
        const auto [gx, gz] = glade(g.map());
        // Trees in the glade, whatever the map had there; and a woodcutter next to it.
        for (int n = 0; n < 6; ++n) {
            tree(g, gx - 6 + n * 3, gz + (n % 2) * 4 - 2);
        }
        const DefIndex cutter = g.content().find_building("core:woodcutter");
        REQUIRE(cutter != kNoDef);
        const std::int32_t reach = g.content().buildings[cutter].work_radius;
        CHECK(g.fells_by_unicorn(cutter, gx - 10, gz - 10));
        CHECK(g.fells_by_unicorn(cutter, gx + reach + 30, gz));
        CHECK_FALSE(g.fells_by_unicorn(cutter, gx + reach + 50, gz));
        CHECK_FALSE(g.fells_by_unicorn(g.content().find_building("core:storehouse"), gx - 10, gz - 10));
        const EntityId house = put(g, "core:house", (tx + gx * 2) / 3, (tz + gz * 2) / 3);
        REQUIRE(house.valid());
        const EntityId lumber = put(g, "core:woodcutter", gx - 14, gz - 12);
        REQUIRE(lumber.valid());
        run(g, 200);
        REQUIRE(unicorn(g));
        const std::int32_t pleasant = at(g, house).desirability;
        (void)g.take_events();
        int left = 0;
        std::uint8_t felled_by = 99;
        const int trees = standing(g, gx, gz, worldgen::kGladeRadius);
        REQUIRE(trees >= 6);
        std::uint32_t t = 0;
        for (; t < 6000 && unicorn(g); ++t) {
            // Until then, not a tree of the glade is down.
            CHECK(standing(g, gx, gz, worldgen::kGladeRadius) == trees);
            g.step();
            left += count(g, Game::Event::Kind::UnicornLeft, &felled_by);
        }
        REQUIRE_FALSE(unicorn(g));
        MESSAGE("the first tree of the glade fell at tick " << t);
        CHECK(standing(g, gx, gz, worldgen::kGladeRadius) == trees - 1);
        CHECK(left == 1);
        CHECK(felled_by == 0);
        CHECK(g.zone_room(0) == 1);  // (There is room for one: none comes.)
        CHECK_FALSE(g.unicorn_near(gx, gz, village::kUnicornMeters));
        CHECK_FALSE(g.fells_by_unicorn(cutter, gx - 10, gz - 10));
        // The house loses what the unicorn gave it (a little more or less, for the trees around it).
        run(g, 300);
        CHECK(at(g, house).desirability <= pleasant - village::kUnicornBeauty + 2);
        // Ten years: it does not come back, and there is no second notice.
        for (std::uint32_t k = 0; k < 10 * g.year_ticks(); ++k) {
            if (k % g.calendar_month_ticks() == 0) {
                grant(g, "core:bread", std::max(0, 3000 - have(g, "core:bread")));
            }
            g.step();
            left += count(g, Game::Event::Kind::UnicornLeft);
            if (k % 500 == 0) {
                REQUIRE_FALSE(unicorn(g));
            }
        }
        CHECK_FALSE(unicorn(g));
        CHECK(left == 1);
    }

    TEST_CASE("felling trees away from the glade does not frighten the unicorn") {
        const auto g_owned = std::make_unique<Game>(core(), glade_map(), setup());
        Game& g = *g_owned;
        const auto [tx, tz] = town(g);
        const auto [gx, gz] = glade(g.map());
        // A woodcutter on the other side of the town, with trees by it: nothing it can reach is by the glade.
        const EntityId lumber = put(g, "core:woodcutter", tx - (gx - tx), tz - (gz - tz));
        REQUIRE(lumber.valid());
        const Building hut = at(g, lumber);
        const std::int32_t reach = g.content().buildings[hut.def].work_radius;
        const std::int64_t dx = hut.x - gx, dz = hut.z - gz;
        REQUIRE(dx * dx + dz * dz > static_cast<std::int64_t>(reach + worldgen::kGladeRadius + 8) * (reach + worldgen::kGladeRadius + 8));
        CHECK_FALSE(g.fells_by_unicorn(hut.def, hut.x, hut.z));
        for (int n = 0; n < 8; ++n) {
            tree(g, hut.x - 8 + n * 3, hut.z + 8 + (n % 2) * 3);
        }
        const int before = standing(g, hut.x, hut.z, reach);
        (void)g.take_events();
        int left = 0;
        for (std::uint32_t t = 0; t < 8000 && standing(g, hut.x, hut.z, reach) > before - 4; ++t) {
            g.step();
            left += count(g, Game::Event::Kind::UnicornLeft);
        }
        REQUIRE(standing(g, hut.x, hut.z, reach) <= before - 4);
        CHECK(unicorn(g));
        CHECK(left == 0);
    }

    TEST_CASE("a town hears of the unicorn the first time one of its people comes near, and only then") {
        // A house by the glade: its people go there.
        const auto g_owned = std::make_unique<Game>(core(), glade_map(false, 110), setup());
        Game& g = *g_owned;
        const auto [tx, tz] = town(g);
        const auto [gx, gz] = glade(g.map());
        (void)g.take_events();
        int seen = 0;
        run(g, 3 * g.calendar_day_ticks());
        seen += count(g, Game::Event::Kind::UnicornSeen);
        CHECK(seen == 0);  // (110 m from the town: nobody has been there.)
        REQUIRE(put(g, "core:house", (tx + gx * 3) / 4, (tz + gz * 3) / 4).valid());
        for (std::uint32_t t = 0; t < g.year_ticks(); ++t) {
            g.step();
            for (const Game::Event& e : g.take_events()) {
                if (e.kind == Game::Event::Kind::UnicornSeen) {
                    ++seen;
                    CHECK(e.owner == 0);
                    CHECK(e.at.x.floor_int() == gx);
                    CHECK(e.at.z.floor_int() == gz);
                }
            }
        }
        CHECK(seen == 1);
        CHECK(g.player(0).unicorns_seen == 1);
        // Far from everybody: nobody sees it.
        const auto far_owned = std::make_unique<Game>(core(), glade_map(true), setup());
        Game& far = *far_owned;
        (void)town(far);
        int none = 0;
        for (std::uint32_t k = 0; k < far.year_ticks() / 2; ++k) {
            far.step();
            none += count(far, Game::Event::Kind::UnicornSeen);
        }
        CHECK(none == 0);
        CHECK(far.player(0).unicorns_seen == 0);
        CHECK(unicorn(far));
    }

    TEST_CASE("the generator puts a glade in each stretch of enchanted wood, and none on a map without it") {
        const Content& c = test::core_content();
        int glades = 0;
        for (const std::uint64_t seed : {5ull, 44ull, 92ull}) {
            MapSettings s;
            s.seed = seed;
            s.size = MapSize::Small;
            s.sea = Sea::None;
            s.biomes = only(c, "core:enchanted");
            const std::optional<MapData> m = generate_map(s, c);
            REQUIRE(m.has_value());
            int here = 0;
            bool after = false;
            for (const Zone& z : m->zones) {
                if (z.type != ZoneType::Unicorn) {
                    CHECK_FALSE(after);  // They are the last ones.
                    continue;
                }
                after = true;
                ++here;
                const std::int32_t x = z.x.floor_int(), zz = z.z.floor_int();
                REQUIRE(m->biome_at(x, zz) < c.flora.biomes.size());
                CHECK(c.flora.biomes[m->biome_at(x, zz)].unicorn);
                CHECK_FALSE(m->water_at(x, zz));
                CHECK(z.radius == Fixed::from_int(worldgen::kGladeRadius));
                for (const StartPosition& start : m->starts) {
                    const std::int64_t dx = start.x.floor_int() - x, dz = start.z.floor_int() - zz;
                    CHECK(dx * dx + dz * dz >= static_cast<std::int64_t>(worldgen::kGladeFromStart) * worldgen::kGladeFromStart);
                }
            }
            MESSAGE("seed " << seed << ", all enchanted wood: " << here << " glades");
            CHECK(here >= 1);
            glades += here;
            // The same map made again is the same.
            const std::optional<MapData> again = generate_map(s, c);
            REQUIRE(again.has_value());
            CHECK(again->zones == m->zones);
            // And without that biome: none.
            s.biomes = only(c, "core:enchanted", true);
            const std::optional<MapData> plain = generate_map(s, c);
            REQUIRE(plain.has_value());
            for (const Zone& z : plain->zones) {
                CHECK(z.type != ZoneType::Unicorn);
            }
        }
        CHECK(glades >= 3);
    }

    TEST_CASE("saving and loading keeps who has seen the unicorn, and one that is gone") {
        const auto g_owned = std::make_unique<Game>(core(), glade_map(), setup());
        Game& g = *g_owned;
        const auto [tx, tz] = town(g);
        const auto [gx, gz] = glade(g.map());
        REQUIRE(put(g, "core:house", (tx + gx * 3) / 4, (tz + gz * 3) / 4).valid());
        for (std::uint32_t t = 0; t < g.year_ticks() && g.player(0).unicorns_seen == 0; ++t) {
            g.step();
        }
        REQUIRE(g.player(0).unicorns_seen == 1);
        {
            BinaryWriter w;
            g.save(w);
            const auto loaded_owned = std::make_unique<Game>(core(), glade_map(), setup());
            Game& loaded = *loaded_owned;
            BinaryReader r(w.bytes());
            REQUIRE(loaded.load(r, core()));
            CHECK(loaded.hash() == g.hash());
            CHECK(loaded.player(0).unicorns_seen == 1);
            CHECK(unicorn(loaded));
        }
        for (int n = 0; n < 6; ++n) {
            tree(g, gx - 6 + n * 3, gz + (n % 2) * 4 - 2);
        }
        REQUIRE(put(g, "core:woodcutter", gx - 14, gz - 12).valid());
        for (std::uint32_t t = 0; t < 6000 && unicorn(g); ++t) {
            g.step();
        }
        REQUIRE_FALSE(unicorn(g));
        BinaryWriter w;
        g.save(w);
        const auto loaded_owned = std::make_unique<Game>(core(), glade_map(), setup());
        Game& loaded = *loaded_owned;
        BinaryReader r(w.bytes());
        REQUIRE(loaded.load(r, core()));
        CHECK(loaded.hash() == g.hash());
        CHECK_FALSE(unicorn(loaded));
        run(g, 2 * g.calendar_month_ticks());
        run(loaded, 2 * loaded.calendar_month_ticks());
        CHECK(loaded.hash() == g.hash());
        CHECK_FALSE(unicorn(loaded));
    }

    // Not a test: a saved game with a house by the glade of a unicorn.
    //   salvasprosperia_tests -ts=unicorn -tc="manual*" --no-skip
    // It writes <temp>/SalvasProsperia/manual_unicorn.scsave: copy it to the saves
    // folder and load it.
    TEST_CASE("manual: a saved game with a house by the glade of a unicorn" * doctest::skip()) {
        std::error_code ec;
        const std::filesystem::path folder = std::filesystem::temp_directory_path(ec) / "SalvasProsperia";
        std::filesystem::create_directories(folder, ec);
        GameSetup rules = setup();
        rules.rules.fog = FogMode::None;
        const auto g_owned = std::make_unique<Game>(core(), glade_map(), rules);
        Game& g = *g_owned;
        const auto [tx, tz] = town(g);
        const auto [gx, gz] = glade(g.map());
        grant(g, "core:log", 200);
        const EntityId house = put(g, "core:house", (tx + gx * 2) / 3, (tz + gz * 2) / 3);
        REQUIRE(house.valid());
        run(g, 300);
        save::SaveData data;
        data.header.name = "unicorn";
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
        REQUIRE(save::write_file(folder / "manual_unicorn.scsave", data));
        MESSAGE("the glade at (" << gx << ", " << gz << "), the house at (" << at(g, house).x << ", " << at(g, house).z << ")");
    }
}
