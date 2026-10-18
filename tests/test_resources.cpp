// What the land gives and how a town hears it is running out (phases 81
// to 87): workplaces that say when nothing is left within their reach.
#include <doctest.h>

#include <algorithm>
#include <cstdlib>
#include <memory>
#include <optional>

#include "game/game_hud.h"
#include "sim/game.h"
#include "sim/worldgen.h"
#include "test_util.h"

using namespace sc::sim;

namespace {

std::shared_ptr<const Content> content() {
    return std::shared_ptr<const Content>(std::shared_ptr<const Content>{}, &sc::test::core_content());
}

// A small map without anything of `types` within 150 m of the start, and
// `count` small ones of `put` in a row 24 m east or west of it.
struct Land {
    MapData map;
    std::int32_t x = 0;  // Where the row is.
    std::int32_t z = 0;
};

Land land(std::uint64_t seed, std::initializer_list<FeatureType> types, FeatureType put, int count, Fixed scale) {
    MapSettings s;
    s.seed = seed;
    s.size = MapSize::Small;
    s.sea = Sea::None;
    s.players = 1;
    std::optional<MapData> m = generate_map(s, *content());
    REQUIRE(m.has_value());
    Land l;
    l.map = std::move(*m);
    REQUIRE(!l.map.starts.empty());
    const std::int32_t sx = l.map.starts[0].x.floor_int();
    const std::int32_t sz = l.map.starts[0].z.floor_int();
    std::erase_if(l.map.features, [&](const MapFeature& f) {
        const std::int64_t dx = f.x.floor_int() - sx;
        const std::int64_t dz = f.z.floor_int() - sz;
        return std::find(types.begin(), types.end(), f.type) != types.end() && dx * dx + dz * dz < 150 * 150;
    });
    l.x = sx + (sx + 60 < l.map.size ? 24 : -24);
    l.z = sz;
    for (int i = 0; i < count; ++i) {
        MapFeature f;
        f.type = put;
        f.x = Fixed::from_int(l.x);
        f.z = Fixed::from_int(l.z - 4 + i * 4);
        f.scale = scale;
        l.map.features.push_back(f);
    }
    return l;
}

GameSetup setup() {
    GameSetup s;
    s.players = 1;
    s.seed = 7;
    s.rules.climate.seasons = 0b0010;  // Summer all year: nothing freezes.
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

// Places `def` as near (x, z) as it fits and waits until it is built (with
// materials to spare, unless `granted` is false: the town's own then).
EntityId build(Game& g, const char* def, std::int32_t ox, std::int32_t oz, bool granted = true) {
    const DefIndex d = content()->find_building(def);
    REQUIRE(d != kNoDef);
    if (granted) {
        grant(g, "core:log", 100);
        grant(g, "core:stone", 30);
    }
    for (int r = 6; r < 40; r += 2) {
        for (int a = 0; a < 9; ++a) {
            const int x = ox + (a % 3 - 1) * r;
            const int z = oz + (a / 3 - 1) * r;
            if (a == 4 || g.can_place(0, d, x, z, 0) != PlaceError::None) {
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
            for (int t = 0; t < 80 && g.buildings().get(id)->state != BuildingState::Complete; ++t) {
                run(g, 100);
            }
            REQUIRE(g.buildings().get(id)->state == BuildingState::Complete);
            return id;
        }
    }
    FAIL("no room");
    return {};
}

// A land without bushes, herbs or trees near the start, and three trees in
// a row there: a medium apple tree, a small one and a medium oak. Returns
// the index of the first.
std::uint32_t orchard_land(Land& l) {
    l = land(21, {FeatureType::BerryBush, FeatureType::Herbs, FeatureType::Tree}, FeatureType::Tree, 3, Fixed::one());
    const auto apple = content()->flora.find_species("core:apple");
    const auto oak = content()->flora.find_species("core:oak");
    REQUIRE(apple >= 0);
    REQUIRE(oak >= 0);
    const std::size_t first = l.map.features.size() - 3;
    l.map.features[first].species = static_cast<std::uint8_t>(apple);
    l.map.features[first].size = static_cast<std::uint8_t>(TreeSize::Medium);
    l.map.features[first + 1].species = static_cast<std::uint8_t>(apple);
    l.map.features[first + 1].size = static_cast<std::uint8_t>(TreeSize::Small);
    l.map.features[first + 2].species = static_cast<std::uint8_t>(oak);
    l.map.features[first + 2].size = static_cast<std::uint8_t>(TreeSize::Medium);
    return static_cast<std::uint32_t>(first);
}

// A land without trees near the start, and three medium apple trees in a
// row there. Returns the index of the first.
std::uint32_t apple_land(Land& l) {
    l = land(21, {FeatureType::BerryBush, FeatureType::Herbs, FeatureType::Tree}, FeatureType::Tree, 3, Fixed::one());
    const int apple = content()->flora.find_species("core:apple");
    REQUIRE(apple >= 0);
    const std::size_t first = l.map.features.size() - 3;
    for (std::size_t i = first; i < l.map.features.size(); ++i) {
        l.map.features[i].species = static_cast<std::uint8_t>(apple);
        l.map.features[i].size = static_cast<std::uint8_t>(TreeSize::Medium);
    }
    return static_cast<std::uint32_t>(first);
}

// A land without trees near the start and a grove of `count` oaks of one
// size there, 5 m apart, in rows of ten. Returns the index of the first.
std::uint32_t oak_land(Land& l, int count, TreeSize size) {
    l = land(21, {FeatureType::BerryBush, FeatureType::Herbs, FeatureType::Tree}, FeatureType::Tree, 0, Fixed::one());
    const int oak = content()->flora.find_species("core:oak");
    REQUIRE(oak >= 0);
    const std::int32_t dir = l.x > l.map.starts[0].x.floor_int() ? 1 : -1;
    const auto first = static_cast<std::uint32_t>(l.map.features.size());
    for (int i = 0; i < count; ++i) {
        MapFeature f;
        f.type = FeatureType::Tree;
        f.species = static_cast<std::uint8_t>(oak);
        f.size = static_cast<std::uint8_t>(size);
        f.x = Fixed::from_int(l.x + dir * (i / 10) * 5);
        f.z = Fixed::from_int(l.z - 22 + (i % 10) * 5);
        l.map.features.push_back(f);
    }
    return first;
}

int sprouts(const Game& g, std::uint32_t first, int count) {
    int n = 0;
    for (std::uint32_t i = first; i < first + static_cast<std::uint32_t>(count); ++i) {
        n += g.sprout(i) ? 1 : 0;
    }
    return n;
}

Command set_option(EntityId workplace, std::uint8_t number, bool on) {
    Command c;
    c.type = CommandType::SetOption;
    c.entity = workplace;
    c.count = number;
    c.value = on ? 1 : 0;
    return c;
}

// Everything of `resource` the town has: stored, at its workplaces and in hand.
std::int32_t held(const Game& g, const char* resource) {
    const DefIndex r = content()->find_resource(resource);
    std::int32_t total = 0;
    for (const Building& b : g.buildings().data()) {
        for (const Stock& s : b.stock) {
            total += s.resource == r ? s.amount : 0;
        }
    }
    for (const Villager& v : g.villagers().data()) {
        total += v.carrying.resource == r ? v.carrying.amount : 0;
    }
    return total;
}

// Steps until the calendar says `season` (at most two years).
void run_to(Game& g, Season season) {
    for (std::uint32_t t = 0; t < 24 * g.calendar_month_ticks() && g.calendar().season != season; t += 20) {
        run(g, 20);
    }
    REQUIRE(g.calendar().season == season);
}

int exhausted_events(Game& g, EntityId of) {
    int n = 0;
    for (const Game::Event& e : g.take_events()) {
        n += e.kind == Game::Event::Kind::Exhausted && e.entity == of ? 1 : 0;
    }
    return n;
}

std::int32_t left(const Game& g, FeatureType type, std::int32_t x, std::int32_t z, std::int32_t radius) {
    std::int32_t total = 0;
    for (std::size_t i = 0; i < g.nodes().size(); ++i) {
        const MapFeature& f = g.map().features[i];
        const std::int64_t dx = f.x.floor_int() - x;
        const std::int64_t dz = f.z.floor_int() - z;
        if (f.type == type && dx * dx + dz * dz < static_cast<std::int64_t>(radius) * radius) {
            total += g.nodes()[i].amount;
        }
    }
    return total;
}

}  // namespace

TEST_SUITE("resources") {
    TEST_CASE("a stonecutter that runs out of rock says so once, and stays that way") {
        // Two small rocks (4 units each) and no other rock or deposit within 150 m.
        const Land l = land(21, {FeatureType::Stone, FeatureType::StoneDeposit}, FeatureType::Stone, 2,
                            Fixed::from_ratio(1, 10));
        const auto g_owned = std::make_unique<Game>(content(), l.map, setup());
        Game& g = *g_owned;
        const EntityId cutter = build(g, "core:stonecutter", l.x, l.z);
        const sc::sim::BuildingDef& def = content()->buildings[g.buildings().get(cutter)->def];
        (void)g.take_events();
        REQUIRE(left(g, FeatureType::Stone, l.x, l.z, 20) > 0);  // (Its workers may have started already.)
        CHECK(sc::supply_key(def, *g.buildings().get(cutter)) == nullptr);
        int told = 0;
        for (int t = 0; t < 120 && g.buildings().get(cutter)->supply != Supply::Exhausted; ++t) {
            run(g, 100);
            told += exhausted_events(g, cutter);
        }
        const Building* b = g.buildings().get(cutter);
        REQUIRE(b->supply == Supply::Exhausted);
        CHECK(left(g, FeatureType::Stone, l.x, l.z, 20) == 0);
        CHECK(std::string_view(sc::supply_key(def, *b)) == "hud.supply.exhausted");
        // Its workers keep looking and finding nothing: told only once.
        for (int t = 0; t < 30; ++t) {
            run(g, 100);
            told += exhausted_events(g, cutter);
        }
        CHECK(told == 1);
        CHECK(g.buildings().get(cutter)->supply == Supply::Exhausted);
        // The rock beyond its reach does not count.
        CHECK(left(g, FeatureType::Stone, l.x, l.z, 4000) > 0);

        // Saved and loaded, it is the same game.
        BinaryWriter w;
        g.save(w);
        const auto back_owned = std::make_unique<Game>(content(), l.map, setup());
        Game& back = *back_owned;
        BinaryReader r(w.bytes());
        REQUIRE(back.load(r, content()));
        CHECK(back.hash() == g.hash());
        CHECK(back.buildings().get(cutter)->supply == Supply::Exhausted);
        run(g, 300);
        run(back, 300);
        CHECK(back.hash() == g.hash());
        CHECK(exhausted_events(back, cutter) == 0);

        // Stopped, the window says nothing of it.
        Command stop;
        stop.type = CommandType::SetProduction;
        stop.entity = cutter;
        stop.value = 0;
        g.apply(stop);
        CHECK(sc::supply_key(def, *g.buildings().get(cutter)) == nullptr);
    }

    TEST_CASE("a stone deposit is quarried by two at once, wears down a size at a time and is gone") {
        // No loose rock near: only a medium deposit (2000), cut down to 812 to see it end.
        Land l = land(21, {FeatureType::Stone, FeatureType::StoneDeposit}, FeatureType::StoneDeposit, 1, Fixed::one());
        l.map.features.back().size = 1;
        const std::int32_t dx = l.map.features.back().x.floor_int();
        const std::int32_t dz = l.map.features.back().z.floor_int();
        const auto g_owned = std::make_unique<Game>(content(), l.map, setup());
        Game& g = *g_owned;
        const std::uint32_t node = static_cast<std::uint32_t>(g.nodes().size() - 1);
        REQUIRE(g.nodes()[node].amount == 2000);
        // Its ground is taken: nothing is built on it, and nobody walks through.
        const DefIndex house = content()->find_building("core:house");
        CHECK(g.can_place(0, house, dx - 1, dz - 1, 0) == PlaceError::Blocked);
        CHECK_FALSE(g.nav().walkable(g.nav().cell_of(Fixed::from_int(dx)), g.nav().cell_of(Fixed::from_int(dz))));
        const EntityId cutter = build(g, "core:stonecutter", dx, dz + 12);
        (void)g.take_events();
        // Both workers at the deposit at the same time.
        bool together = false;
        for (int t = 0; t < 3000 && !together; ++t) {
            g.step();
            int at = 0;
            for (const Villager& v : g.villagers().data()) {
                at += v.job == cutter && v.task == Task::Gather && v.node == node + 1 ? 1 : 0;
            }
            together = at >= 2;
        }
        CHECK(together);
        CHECK(g.map().features[node].size == 1);
        // Saved half spent and loaded, it is the same game.
        BinaryWriter w;
        g.save(w);
        const auto back_owned = std::make_unique<Game>(content(), l.map, setup());
        Game& back = *back_owned;
        BinaryReader r(w.bytes());
        REQUIRE(back.load(r, content()));
        CHECK(back.hash() == g.hash());
        CHECK(back.nodes()[node].amount == g.nodes()[node].amount);
        CHECK_FALSE(back.nav().walkable(back.nav().cell_of(Fixed::from_int(dx)), back.nav().cell_of(Fixed::from_int(dz))));
        run(g, 200);
        run(back, 200);
        CHECK(back.hash() == g.hash());
    }

    TEST_CASE("a small stone deposit is worked to its last unit and frees its ground; the stonecutter then says so") {
        Land l = land(21, {FeatureType::Stone, FeatureType::StoneDeposit}, FeatureType::StoneDeposit, 1, Fixed::one());
        const std::int32_t dx = l.map.features.back().x.floor_int();
        const std::int32_t dz = l.map.features.back().z.floor_int();
        const auto g_owned = std::make_unique<Game>(content(), l.map, setup());
        Game& g = *g_owned;
        const std::uint32_t node = static_cast<std::uint32_t>(g.nodes().size() - 1);
        REQUIRE(g.nodes()[node].amount == 800);
        CHECK(deposit_amount(800, 2) == 5000);
        CHECK(deposit_size(800, 5000) == 2);
        CHECK(deposit_size(800, 2001) == 2);
        CHECK(deposit_size(800, 2000) == 1);
        CHECK(deposit_size(800, 801) == 1);
        CHECK(deposit_size(800, 800) == 0);
        const EntityId cutter = build(g, "core:stonecutter", dx, dz + 12);
        (void)g.take_events();
        const DefIndex stone = content()->find_resource("core:stone");
        const auto all_stone = [&] {
            std::int32_t total = g.stored(0)[stone];
            for (const Building& b : g.buildings().data()) {
                for (const Stock& s : b.stock) {
                    total += b.state == BuildingState::Complete && content()->buildings[b.def].storage == 0 &&
                                     s.resource == stone
                                 ? s.amount
                                 : 0;
                }
            }
            for (const Villager& v : g.villagers().data()) {
                total += v.carrying.resource == stone ? v.carrying.amount : 0;
            }
            return total;
        };
        const std::int32_t before = all_stone();
        int told = 0;
        for (int t = 0; t < 4000 && g.buildings().get(cutter)->supply != Supply::Exhausted; ++t) {
            grant(g, "core:roots", 1);
            run(g, 100);
            told += exhausted_events(g, cutter);
        }
        CHECK(g.nodes()[node].amount == 0);
        CHECK(g.buildings().get(cutter)->supply == Supply::Exhausted);
        CHECK(told == 1);
        // (What does not fit in the storages is left on the ground: not all 800 are kept.)
        CHECK(all_stone() > before);
        CHECK(g.nav().walkable(g.nav().cell_of(Fixed::from_int(dx)), g.nav().cell_of(Fixed::from_int(dz))));
        CHECK(g.can_place(0, content()->find_building("core:house"), dx - 1, dz - 1, 0) != PlaceError::Blocked);
    }

    TEST_CASE("every start has a stone deposit, medium or large, within a walk") {
        for (const std::uint64_t seed : {4242ull, 12345ull, 777ull}) {
            MapSettings s;
            s.seed = seed;
            s.size = MapSize::Medium;
            s.sea = Sea::None;
            s.players = 4;
            const std::optional<MapData> m = generate_map(s, *content());
            REQUIRE(m.has_value());
            int deposits = 0;
            int sizes[kDepositSizes] = {};
            for (const MapFeature& f : m->features) {
                if (f.type == FeatureType::StoneDeposit) {
                    ++deposits;
                    REQUIRE(f.size < kDepositSizes);
                    ++sizes[f.size];
                }
            }
            MESSAGE("seed " << seed << ": " << deposits << " deposits (" << sizes[0] << " small, " << sizes[1] << " medium, "
                            << sizes[2] << " large)");
            CHECK(deposits >= 4);
            CHECK(deposits <= 40);
            GameSetup gs = setup();
            gs.players = 4;
            const auto g_owned = std::make_unique<Game>(content(), *m, gs);
            Game& g = *g_owned;
            for (std::size_t p = 0; p < m->starts.size(); ++p) {
                const StartPosition& st = m->starts[p];
                bool near = false;
                for (const MapFeature& f : m->features) {
                    const std::int64_t ddx = f.x.floor_int() - st.x.floor_int();
                    const std::int64_t ddz = f.z.floor_int() - st.z.floor_int();
                    if (f.type != FeatureType::StoneDeposit || f.size < 1 || ddx * ddx + ddz * ddz > 200 * 200) {
                        continue;
                    }
                    // Walkable from the town to beside the deposit.
                    const std::int32_t half = deposit_half_side(f.size) + 2;
                    for (const auto& [ox, oz] : {std::pair{half, 0}, std::pair{-half, 0}, std::pair{0, half}, std::pair{0, -half}}) {
                        near = near || g.nav().connected({st.x, st.z + Fixed::from_int(12)},
                                                         {f.x + Fixed::from_int(ox), f.z + Fixed::from_int(oz)});
                    }
                }
                CAPTURE(seed);
                CAPTURE(p);
                CHECK(near);
            }
            // Nothing else stands on a deposit's ground.
            for (const MapFeature& d : m->features) {
                if (d.type != FeatureType::StoneDeposit) {
                    continue;
                }
                for (const MapFeature& f : m->features) {
                    const std::int32_t reach = deposit_half_side(d.size);
                    const bool on = &f != &d && std::abs(f.x.floor_int() - d.x.floor_int()) <= reach &&
                                    std::abs(f.z.floor_int() - d.z.floor_int()) <= reach;
                    CHECK_FALSE(on);
                }
            }
        }
    }

    TEST_CASE("a fruit tree bears once a year: in summer, until autumn ends, and only when it is grown") {
        Land l;
        const std::uint32_t apple = orchard_land(l);
        GameSetup s = setup();
        s.rules.climate.seasons = 0b1111;
        const auto g_owned = std::make_unique<Game>(content(), l.map, s);
        Game& g = *g_owned;
        REQUIRE(g.calendar().season == Season::Spring);
        CHECK(g.fruit_on(apple) == 0);
        run_to(g, Season::Summer);
        CHECK(g.fruit_on(apple) == 6);
        CHECK(g.fruit_on(apple + 1) == 0);  // A small one never has any.
        CHECK(g.fruit_on(apple + 2) == 0);  // Nor an oak.
        run_to(g, Season::Autumn);
        CHECK(g.fruit_on(apple) == 6);
        run_to(g, Season::Winter);
        CHECK(g.fruit_on(apple) == 0);  // What nobody picked is lost.
        const std::uint32_t year = g.calendar().year;
        run_to(g, Season::Summer);
        CHECK(g.calendar().year == year + 1);
        CHECK(g.fruit_on(apple) == 6);

        // A species a mod marks as a fruit tree is one.
        auto modded = std::make_shared<Content>(sc::test::core_content());
        const auto oak = modded->flora.find_species("core:oak");
        REQUIRE(oak >= 0);
        modded->flora.species[static_cast<std::size_t>(oak)].fruit[static_cast<std::size_t>(TreeSize::Medium)] = 9;
        GameSetup summer = setup();
        const auto m_owned = std::make_unique<Game>(modded, l.map, summer);
        Game& m = *m_owned;
        CHECK(m.fruit_on(apple + 2) == 9);
    }

    TEST_CASE("a forager picks the fruit of the fruit trees as food, and the tree stays") {
        Land l;
        const std::uint32_t apple = orchard_land(l);
        const auto g_owned = std::make_unique<Game>(content(), l.map, setup());  // Summer all year.
        Game& g = *g_owned;
        const std::int32_t logs = g.nodes()[apple].amount;
        REQUIRE(g.fruit_on(apple) == 6);
        const DefIndex fruit = content()->find_resource("core:fruit");
        REQUIRE(fruit != kNoDef);
        const std::int32_t before = g.stored(0)[fruit];
        const EntityId forager = build(g, "core:forager", l.x, l.z + 14);
        (void)g.take_events();
        int told = 0;
        std::int32_t most = before;
        for (int t = 0; t < 200 && g.fruit_on(apple) > 0; ++t) {
            run(g, 20);
            told += exhausted_events(g, forager);
            most = std::max(most, g.stored(0)[fruit]);
        }
        CHECK(g.fruit_on(apple) == 0);
        for (int t = 0; t < 60; ++t) {
            run(g, 20);
            told += exhausted_events(g, forager);
            most = std::max(most, g.stored(0)[fruit]);
        }
        CHECK(most > before);                       // Brought in as fruit.
        CHECK(g.nodes()[apple].amount == logs);     // The tree was not felled.
        CHECK(g.nodes()[apple + 2].amount > 0);     // Nor the oak beside it.
        CHECK(g.nodes()[apple].fruit_picked == 6);
        // With nothing more to pick this year it waits, without a word.
        CHECK(g.buildings().get(forager)->supply == Supply::Waiting);
        CHECK(told == 0);

        BinaryWriter w;
        g.save(w);
        const auto back_owned = std::make_unique<Game>(content(), l.map, setup());
        Game& back = *back_owned;
        BinaryReader r(w.bytes());
        REQUIRE(back.load(r, content()));
        CHECK(back.hash() == g.hash());
        CHECK(back.fruit_on(apple) == 0);

        // Next year it bears again, and is picked again.
        const std::uint32_t year = g.calendar().year;
        for (std::uint32_t t = 0; t < 13 * g.calendar_month_ticks() && g.nodes()[apple].fruit_year <= year; t += 100) {
            grant(g, "core:roots", 2);
            run(g, 100);
        }
        CHECK(g.calendar().year > year);
        CHECK(g.nodes()[apple].fruit_year == g.calendar().year);
        CHECK(g.nodes()[apple].amount == logs);
    }

    TEST_CASE("a woodcutter spares the fruit trees until told otherwise; felled, they give wood and their fruit") {
        Land l;
        const std::uint32_t apple = apple_land(l);
        const auto g_owned = std::make_unique<Game>(content(), l.map, setup());  // Summer all year: the trees have fruit.
        Game& g = *g_owned;
        const EntityId cutter = build(g, "core:woodcutter", l.x, l.z + 14);
        (void)g.take_events();
        REQUIRE(g.buildings().get(cutter)->options == 0);
        const std::int32_t logs = g.nodes()[apple].amount;
        int told = 0;
        int about_fruit = 0;
        for (int t = 0; t < 40; ++t) {
            run(g, 50);
            for (const Game::Event& e : g.take_events()) {
                told += e.kind == Game::Event::Kind::Exhausted && e.entity == cutter ? 1 : 0;
                about_fruit += e.kind == Game::Event::Kind::Exhausted && e.entity == cutter && e.value == 1 ? 1 : 0;
            }
        }
        // Surrounded by apple trees only: none is felled, and it says why, once.
        for (std::uint32_t i = apple; i < apple + 3; ++i) {
            CHECK(g.nodes()[i].amount == logs);
        }
        const Building* b = g.buildings().get(cutter);
        CHECK(b->supply == Supply::OnlyFruit);
        CHECK(told == 1);
        CHECK(about_fruit == 1);
        CHECK(std::string_view(sc::supply_key(content()->buildings[b->def], *b)) == "hud.supply.onlyFruit");

        // The switch is an order: as bytes, like in a network game, to two games.
        BinaryWriter saved;
        g.save(saved);
        const auto other_owned = std::make_unique<Game>(content(), l.map, setup());
        Game& other = *other_owned;
        BinaryReader in(saved.bytes());
        REQUIRE(other.load(in, content()));
        const Command sent = set_option(cutter, 0, true);
        BinaryWriter wire;
        sent.write(wire);
        BinaryReader wire_in(wire.bytes());
        Command received;
        REQUIRE(Command::read(wire_in, received));
        CHECK(received == sent);
        const std::int32_t fruit = held(g, "core:fruit");
        const std::int32_t wood = held(g, "core:log");
        g.apply(sent);
        other.apply(received);
        CHECK((g.buildings().get(cutter)->options & option::kFellFruit) != 0);
        // Saved and loaded with the switch on.
        BinaryWriter w;
        g.save(w);
        const auto back_owned = std::make_unique<Game>(content(), l.map, setup());
        Game& back = *back_owned;
        BinaryReader r(w.bytes());
        REQUIRE(back.load(r, content()));
        CHECK(back.hash() == g.hash());
        CHECK((back.buildings().get(cutter)->options & option::kFellFruit) != 0);
        for (int t = 0; t < 60; ++t) {
            run(g, 50);
            run(other, 50);
            REQUIRE(g.hash() == other.hash());
        }
        // The three apple trees came down: their wood, and 6 pieces of fruit each.
        for (std::uint32_t i = apple; i < apple + 3; ++i) {
            CHECK(g.nodes()[i].amount == 0);
        }
        CHECK(held(g, "core:log") > wood);
        // (The villagers eat fruit too: at least most of the 18 is still there.)
        CHECK(held(g, "core:fruit") - fruit > 9);
        CHECK(held(g, "core:fruit") - fruit <= 18);
        // An option the workplace does not have, or of another's building, is refused.
        const std::uint64_t refused = g.rejected_commands();
        g.apply(set_option(cutter, 5, true));
        g.apply(set_option(g.player(0).town_center, 0, true));
        CHECK(g.rejected_commands() == refused + 2);
    }

    TEST_CASE("a fruit tree felled in winter gives only wood") {
        Land l;
        const std::uint32_t apple = apple_land(l);
        GameSetup s = setup();
        s.rules.climate.seasons = 0b1000;  // Winter all year.
        const auto g_owned = std::make_unique<Game>(content(), l.map, s);
        Game& g = *g_owned;
        REQUIRE(g.calendar().season == Season::Winter);
        const EntityId cutter = build(g, "core:woodcutter", l.x, l.z + 14);
        const std::int32_t fruit = held(g, "core:fruit");
        g.apply(set_option(cutter, 0, true));
        for (int t = 0; t < 60 && g.nodes()[apple].amount + g.nodes()[apple + 1].amount + g.nodes()[apple + 2].amount > 0; ++t) {
            grant(g, "core:firewood", 5);
            run(g, 50);
        }
        CHECK(g.nodes()[apple].amount == 0);
        CHECK(held(g, "core:fruit") <= fruit);
    }

    TEST_CASE("a site over trees is cleared by laborers who fell them, and their wood and fruit come to the town") {
        Land l;
        const std::uint32_t apple = apple_land(l);
        const auto g_owned = std::make_unique<Game>(content(), l.map, setup());  // Summer all year: the trees have fruit.
        Game& g = *g_owned;
        // A woodcutter beside them that spares fruit trees and replants: neither counts on a site.
        // (Built with the town's own wood, and with a storehouse: a new town's
        // center is full, and wood with nowhere to go is left on the ground.)
        (void)build(g, "core:storehouse", l.x, l.z - 20, false);
        const EntityId cutter = build(g, "core:woodcutter", l.x, l.z + 16, false);
        g.apply(set_option(cutter, 1, true));
        const std::int32_t logs = g.nodes()[apple + 1].amount;
        // All the town's wood, wherever it is: stored, on its sites and in hand.
        const auto wood = [&] {
            const DefIndex log = content()->find_resource("core:log");
            std::int32_t total = held(g, "core:log");
            for (const Building& b : g.buildings().data()) {
                for (const Stock& st : b.delivered) {
                    total += st.resource == log ? st.amount : 0;
                }
            }
            return total;
        };
        // A house right on the middle tree.
        const MapFeature& f = g.map().features[apple + 1];
        Command c;
        c.type = CommandType::PlaceBuilding;
        c.def = content()->find_building("core:house");
        c.position = {Fixed::from_int(f.x.floor_int() - 1), Fixed::from_int(f.z.floor_int() - 1)};
        const std::size_t before = g.buildings().size();
        g.apply(c);
        REQUIRE(g.buildings().size() == before + 1);
        const EntityId house = g.buildings().entities()[g.buildings().size() - 1];
        // The trees are still there, and the site says how many.
        const std::int32_t on_site = g.trees_on_site(*g.buildings().get(house));
        REQUIRE(on_site >= 1);
        CHECK(g.nodes()[apple + 1].amount == logs);
        std::vector<std::uint32_t> there;
        for (std::uint32_t i = apple; i < apple + 3; ++i) {
            const MapFeature& t = g.map().features[i];
            const Building& b = *g.buildings().get(house);
            if (t.x.floor_int() >= b.x - 1 && t.x.floor_int() < b.x + b.width + 1 && t.z.floor_int() >= b.z - 1 &&
                t.z.floor_int() < b.z + b.depth + 1) {
                there.push_back(i);
            }
        }
        CHECK(static_cast<std::int32_t>(there.size()) == on_site);
        const std::int32_t wood_before = wood();
        // Saved before it is cleared and loaded: the same game.
        BinaryWriter w;
        g.save(w);
        const auto back_owned = std::make_unique<Game>(content(), l.map, setup());
        Game& back = *back_owned;
        BinaryReader r(w.bytes());
        REQUIRE(back.load(r, content()));
        CHECK(back.hash() == g.hash());
        CHECK(back.trees_on_site(*back.buildings().get(house)) == on_site);
        // Nothing is built while a tree stands.
        bool built_early = false;
        for (int t = 0; t < 400 && g.trees_on_site(*g.buildings().get(house)) > 0; ++t) {
            run(g, 10);
            const Building* b = g.buildings().get(house);
            built_early = built_early || (g.trees_on_site(*b) > 0 && b->work_done > 0);
        }
        CHECK_FALSE(built_early);
        REQUIRE(g.trees_on_site(*g.buildings().get(house)) == 0);
        for (const std::uint32_t i : there) {
            CHECK(g.nodes()[i].amount == 0);
            CHECK_FALSE(g.sprout(i));                 // Nobody replants a site.
            CHECK(g.nodes()[i].fruit_picked == 6);    // Its fruit was taken, for the town.
        }
        // The trees outside the site are the woodcutter's business: it spares them.
        for (std::uint32_t i = apple; i < apple + 3; ++i) {
            if (std::find(there.begin(), there.end(), i) == there.end()) {
                CHECK(g.nodes()[i].amount == logs);
            }
        }
        // Their wood is the town's, all of it (still in the fellers' hands, or stored).
        CHECK(wood() == wood_before + on_site * logs);
        // And then the house is built.
        for (int t = 0; t < 80 && g.buildings().get(house)->state != BuildingState::Complete; ++t) {
            run(g, 100);
        }
        CHECK(g.buildings().get(house)->state == BuildingState::Complete);
    }

    TEST_CASE("a site cancelled before it is cleared keeps its trees") {
        Land l;
        const std::uint32_t apple = apple_land(l);
        const auto g_owned = std::make_unique<Game>(content(), l.map, setup());
        Game& g = *g_owned;
        const std::int32_t logs = g.nodes()[apple + 1].amount;
        const MapFeature& f = g.map().features[apple + 1];
        Command c;
        c.type = CommandType::PlaceBuilding;
        c.def = content()->find_building("core:house");
        c.position = {Fixed::from_int(f.x.floor_int() - 1), Fixed::from_int(f.z.floor_int() - 1)};
        const std::size_t before = g.buildings().size();
        g.apply(c);
        REQUIRE(g.buildings().size() == before + 1);
        Command cancel;
        cancel.type = CommandType::RemoveBuilding;
        cancel.entity = g.buildings().entities()[g.buildings().size() - 1];
        g.apply(cancel);
        CHECK(g.buildings().size() == before);
        for (std::uint32_t i = apple; i < apple + 3; ++i) {
            CHECK(g.nodes()[i].amount == logs);
        }
    }

    TEST_CASE("a field over trees is sown only after the farm's workers fell them") {
        Land l;
        const std::uint32_t oaks = oak_land(l, 2, TreeSize::Medium);
        const auto g_owned = std::make_unique<Game>(content(), l.map, setup());
        Game& g = *g_owned;
        const EntityId farm = build(g, "core:farm", l.x, l.z + 24);
        // A field around the two oaks.
        const MapFeature& f = g.map().features[oaks];
        const std::int32_t fx = f.x.floor_int() - 2;
        const std::int32_t fz = f.z.floor_int() - 2;
        REQUIRE(g.can_place_field(0, farm, fx, fz, 10, 10) == PlaceError::None);
        Command c;
        c.type = CommandType::PlaceField;
        c.entity = farm;
        c.position = {Fixed::from_int(fx), Fixed::from_int(fz)};
        c.value = 10 | (10 << 8);
        g.apply(c);
        REQUIRE(g.buildings().get(farm)->fields.size() == 1);
        const std::int32_t logs = g.nodes()[oaks].amount;
        CHECK(logs > 0);                             // Still standing.
        CHECK(g.tree_on(fx, fz, 10, 10, 0) != 0);
        bool sown_early = false;
        for (int t = 0; t < 600 && g.tree_on(fx, fz, 10, 10, 0) != 0; ++t) {
            run(g, 10);
            const Field& field = g.buildings().get(farm)->fields[0];
            sown_early = sown_early || (g.tree_on(fx, fz, 10, 10, 0) != 0 && (field.state != FieldState::Waiting || field.work > 0));
        }
        CHECK_FALSE(sown_early);
        CHECK(g.tree_on(fx, fz, 10, 10, 0) == 0);
        CHECK(g.nodes()[oaks].amount == 0);
        CHECK(g.nodes()[oaks + 1].amount == 0);
        // Then it is sown.
        bool sown = false;
        for (int t = 0; t < 400 && !sown; ++t) {
            run(g, 10);
            const Field& field = g.buildings().get(farm)->fields[0];
            sown = field.state != FieldState::Waiting || field.work > 0;
        }
        CHECK(sown);
    }

}

// Years of game: in a suite of their own, to fit the time of a debug run.
TEST_SUITE("resources_years") {
    TEST_CASE("trees grow a size a year, up to what their species reaches, each on its own day") {
        // A small oak (small, medium and large), a small apple tree (small and
        // medium) and a medium oak, far from any woodcutter.
        Land l;
        const std::uint32_t apple = orchard_land(l);
        const int oak = content()->flora.find_species("core:oak");
        l.map.features[apple].species = static_cast<std::uint8_t>(oak);
        l.map.features[apple].size = static_cast<std::uint8_t>(TreeSize::Small);
        const SpeciesDef& sp = content()->flora.species[static_cast<std::size_t>(oak)];
        GameSetup s = setup();
        s.rules.climate.seasons = 0b1111;
        const auto g_owned = std::make_unique<Game>(content(), l.map, s);
        Game& g = *g_owned;
        const std::uint32_t year = 12 * g.calendar_month_ticks();
        const auto size = [&](std::uint32_t i) { return static_cast<TreeSize>(g.map().features[i].size); };
        REQUIRE(size(apple) == TreeSize::Small);
        CHECK(g.nodes()[apple].amount == sp.logs[0]);
        CHECK(g.nodes()[apple + 1].grow_day != kNeverGrows);
        // Within its first year nothing changes.
        run(g, year - 10);
        CHECK(size(apple) == TreeSize::Small);
        CHECK(size(apple + 1) == TreeSize::Small);
        (void)g.take_changed_nodes();
        // By the end of the second, each has had its birthday: one size up.
        run(g, year);
        CHECK(size(apple) == TreeSize::Medium);
        CHECK(g.nodes()[apple].amount == sp.logs[1]);
        CHECK(size(apple + 1) == TreeSize::Medium);  // The apple tree: as large as it gets.
        CHECK(g.nodes()[apple + 1].grow_day == kNeverGrows);
        CHECK(g.fruit_on(apple + 1, Calendar{3, 6, 1, Season::Summer, 0}) == 6);  // Grown, it bears fruit.
        CHECK(size(apple + 2) == TreeSize::Large);
        const std::vector<std::uint32_t> changed = g.take_changed_nodes();
        CHECK(std::find(changed.begin(), changed.end(), apple) != changed.end());
        // Saved in the middle of its growing and loaded, it is the same game.
        BinaryWriter w;
        g.save(w);
        const auto back_owned = std::make_unique<Game>(content(), l.map, s);
        Game& back = *back_owned;
        BinaryReader r(w.bytes());
        REQUIRE(back.load(r, content()));
        CHECK(back.hash() == g.hash());
        CHECK(back.map().features[apple].size == g.map().features[apple].size);
        // A year more: the oak is large; the others stay (no core species but the giants is huge).
        run(g, year);
        run(back, year);
        CHECK(back.hash() == g.hash());
        CHECK(size(apple) == TreeSize::Large);
        CHECK(g.nodes()[apple].amount == sp.logs[2]);
        CHECK(size(apple + 1) == TreeSize::Medium);
        run(g, 2 * year);
        CHECK(size(apple) == TreeSize::Large);
        CHECK(g.nodes()[apple].grow_day == kNeverGrows);
    }

    TEST_CASE("the forest does not grow in one day, a giant does not grow, and a huge size takes two years more") {
        MapSettings ms;
        ms.seed = 4242;
        ms.size = MapSize::Small;
        ms.sea = Sea::None;
        std::optional<MapData> m = generate_map(ms, *content());
        REQUIRE(m.has_value());
        // A species that reaches huge, for this test.
        auto modded = std::make_shared<Content>(sc::test::core_content());
        const int oak = modded->flora.find_species("core:oak");
        REQUIRE(oak >= 0);
        modded->flora.species[static_cast<std::size_t>(oak)].sizes = 0b1111;
        GameSetup s = setup();
        s.players = 0;  // Nobody fells anything.
        s.rules.climate.seasons = 0b1111;
        const auto g_owned = std::make_unique<Game>(modded, *m, s);
        Game& g = *g_owned;
        const std::uint32_t year = 12 * g.calendar_month_ticks();
        int growing = 0;
        std::vector<std::uint32_t> oaks;
        for (std::uint32_t i = 0; i < g.nodes().size(); ++i) {
            const MapFeature& f = g.map().features[i];
            if (f.type != FeatureType::Tree) {
                continue;
            }
            growing += g.nodes()[i].grow_day != kNeverGrows ? 1 : 0;
            if (modded->flora.species[f.species].giant_biome >= 0) {
                CHECK(g.nodes()[i].grow_day == kNeverGrows);
            }
            if (f.species == oak && f.size == static_cast<std::uint8_t>(TreeSize::Large)) {
                oaks.push_back(i);
            }
        }
        REQUIRE(growing > 200);
        REQUIRE(!oaks.empty());
        // The second year, day by day: how many grew on each.
        run(g, year);
        (void)g.take_changed_nodes();
        std::size_t most = 0;
        std::size_t total = 0;
        int days_with_growth = 0;
        for (int day = 0; day < 120; ++day) {
            run(g, g.calendar_day_ticks());
            const std::size_t n = g.take_changed_nodes().size();
            most = std::max(most, n);
            total += n;
            days_with_growth += n > 0 ? 1 : 0;
        }
        MESSAGE(growing << " trees to grow; " << total << " grew in the second year, at most " << most << " in a day, on "
                        << days_with_growth << " days");
        CHECK(total >= static_cast<std::size_t>(growing) * 8 / 10);
        CHECK(most * 10 < total);  // No day has a tenth of the year's growth.
        CHECK(days_with_growth > 100);
        // The large oaks took two years: none is huge after one, all after two.
        for (const std::uint32_t i : oaks) {
            CHECK(g.map().features[i].size == static_cast<std::uint8_t>(TreeSize::Large));
        }
        run(g, year + g.calendar_day_ticks() * 2);
        for (const std::uint32_t i : oaks) {
            CHECK(g.map().features[i].size == static_cast<std::uint8_t>(TreeSize::Huge));
        }
    }

    TEST_CASE("a woodcutter told to replant leaves a sprout of the species where each tree stood; one not told leaves nothing") {
        Land l;
        const std::uint32_t oaks = oak_land(l, 4, TreeSize::Medium);
        const std::uint8_t species = l.map.features[oaks].species;
        for (const bool replant : {false, true}) {
            const auto g_owned = std::make_unique<Game>(content(), l.map, setup());
            Game& g = *g_owned;
            const EntityId cutter = build(g, "core:woodcutter", l.x, l.z + 16);
            if (replant) {
                g.apply(set_option(cutter, 1, true));
                CHECK((g.buildings().get(cutter)->options & option::kReplant) != 0);
            }
            const auto standing = [&] {
                int n = 0;
                for (std::uint32_t i = oaks; i < oaks + 4; ++i) {
                    n += g.nodes()[i].amount > 0 ? 1 : 0;
                }
                return n;
            };
            for (int t = 0; t < 80 && standing() > 0; ++t) {
                run(g, 50);
            }
            REQUIRE(standing() == 0);
            CHECK(sprouts(g, oaks, 4) == (replant ? 4 : 0));
            if (!replant) {
                continue;
            }
            // Each sprout is of the species, of its smallest size, where the tree was.
            for (std::uint32_t i = oaks; i < oaks + 4; ++i) {
                CHECK(g.map().features[i].species == species);
                CHECK(g.map().features[i].size == static_cast<std::uint8_t>(TreeSize::Small));
                CHECK(g.map().features[i].x == l.map.features[i].x);
                CHECK(g.nodes()[i].amount == 0);
            }
            // With only sprouts to look at, it waits for them, without a word.
            (void)g.take_events();
            run(g, 300);
            CHECK(g.buildings().get(cutter)->supply == Supply::Growing);
            CHECK(exhausted_events(g, cutter) == 0);
            const Building* b = g.buildings().get(cutter);
            CHECK(std::string_view(sc::supply_key(content()->buildings[b->def], *b)) == "hud.supply.growing");
            // Saved with sprouts and loaded: the same game; a year on, they are small trees.
            BinaryWriter w;
            g.save(w);
            const auto back_owned = std::make_unique<Game>(content(), l.map, setup());
            Game& back = *back_owned;
            BinaryReader r(w.bytes());
            REQUIRE(back.load(r, content()));
            CHECK(back.hash() == g.hash());
            CHECK(sprouts(back, oaks, 4) == 4);
            // A site cleared over a sprout leaves no sprout.
            Command c;
            c.type = CommandType::PlaceBuilding;
            c.def = content()->find_building("core:house");
            const MapFeature& f = g.map().features[oaks + 1];
            c.position = {Fixed::from_int(f.x.floor_int() - 1), Fixed::from_int(f.z.floor_int() - 1)};
            const std::size_t before = g.buildings().size();
            back.apply(c);
            REQUIRE(back.buildings().size() == before + 1);
            CHECK_FALSE(back.sprout(oaks + 1));
            CHECK(back.nodes()[oaks + 1].amount == 0);
            // (Stopped, so that it does not fell them again as they come of age.)
            Command stop;
            stop.type = CommandType::SetProduction;
            stop.entity = cutter;
            stop.value = 0;
            g.apply(stop);
            for (std::uint32_t t = 0; t < 13 * g.calendar_month_ticks(); t += 100) {
                grant(g, "core:roots", 2);
                run(g, 100);
            }
            CHECK(sprouts(g, oaks, 4) == 0);
            const SpeciesDef& sp = content()->flora.species[species];
            for (std::uint32_t i = oaks; i < oaks + 4; ++i) {
                CHECK(g.nodes()[i].amount == sp.logs[0]);
                CHECK(g.nodes()[i].grow_day != kNeverGrows);
            }
        }
    }

    TEST_CASE("a woodcutter told to fell only the grown trees waits for the young ones, and fells the first to come of age") {
        Land l;
        const std::uint32_t oaks = oak_land(l, 6, TreeSize::Medium);
        GameSetup s = setup();
        const auto g_owned = std::make_unique<Game>(content(), l.map, s);
        Game& g = *g_owned;
        CHECK_FALSE(g.mature(g.map().features[oaks]));
        const EntityId cutter = build(g, "core:woodcutter", l.x, l.z + 16);
        g.apply(set_option(cutter, 2, true));
        // (Its workers may have started on a tree before the order; they finish that load.)
        run(g, 500);
        (void)g.take_events();
        std::int32_t wood[6];
        for (std::uint32_t i = 0; i < 6; ++i) {
            wood[i] = g.nodes()[oaks + i].amount;
            CHECK(wood[i] > 0);
        }
        int told = 0;
        for (int t = 0; t < 30; ++t) {
            run(g, 50);
            told += exhausted_events(g, cutter);
        }
        for (std::uint32_t i = 0; i < 6; ++i) {
            CHECK(g.nodes()[oaks + i].amount == wood[i]);  // None touched.
        }
        CHECK(g.buildings().get(cutter)->supply == Supply::Growing);
        CHECK(told == 0);
        // In their second year they are large one by one, and are felled as they are.
        bool felled_young = false;
        int felled = 0;
        for (std::uint32_t t = 0; t < 26 * g.calendar_month_ticks() && felled < 6; t += 20) {
            if (t % 200 == 0) {
                grant(g, "core:roots", 1);
            }
            std::int32_t before[6];
            std::uint8_t size[6];
            for (std::uint32_t i = 0; i < 6; ++i) {
                before[i] = g.nodes()[oaks + i].amount;
                size[i] = g.map().features[oaks + i].size;
            }
            run(g, 20);
            felled = 0;
            for (std::uint32_t i = 0; i < 6; ++i) {
                const std::int32_t now = g.nodes()[oaks + i].amount;
                // Wood taken from a tree that was not large.
                felled_young = felled_young || (now < before[i] && size[i] < static_cast<std::uint8_t>(TreeSize::Large));
                felled += now == 0 ? 1 : 0;
            }
        }
        CHECK_FALSE(felled_young);
        CHECK(felled == 6);
        CHECK(g.mature(MapFeature{FeatureType::Tree, l.map.features[oaks].species, static_cast<std::uint8_t>(TreeSize::Large)}));
        // An apple tree is grown at medium: its species gets no larger.
        const int apple = content()->flora.find_species("core:apple");
        CHECK(g.mature(MapFeature{FeatureType::Tree, static_cast<std::uint8_t>(apple), static_cast<std::uint8_t>(TreeSize::Medium)}));
        CHECK_FALSE(g.mature(MapFeature{FeatureType::Tree, static_cast<std::uint8_t>(apple), static_cast<std::uint8_t>(TreeSize::Small)}));
    }

    TEST_CASE("replanting and felling only the grown, a woodcutter with sixty large trees still brings wood ten years on") {
        Land l;
        const std::uint32_t oaks = oak_land(l, 60, TreeSize::Large);
        const auto g_owned = std::make_unique<Game>(content(), l.map, setup());
        Game& g = *g_owned;
        const EntityId cutter = build(g, "core:woodcutter", l.x, l.z + 30);
        g.apply(set_option(cutter, 1, true));
        g.apply(set_option(cutter, 2, true));
        const std::uint32_t year = 12 * g.calendar_month_ticks();
        int felled_by_year[10] = {};
        std::int32_t taken_by_year[10] = {};
        for (int y = 0; y < 10; ++y) {
            for (std::uint32_t t = 0; t < year; t += 100) {
                grant(g, "core:roots", 3);
                grant(g, "core:firewood", 1);
                // The town's stores do not fill up: the wood is taken away.
                std::int32_t before[60];
                for (std::uint32_t i = 0; i < 60; ++i) {
                    before[i] = g.nodes()[oaks + i].amount;
                }
                run(g, 100);
                for (std::uint32_t i = 0; i < 60; ++i) {
                    const std::int32_t now = g.nodes()[oaks + i].amount;
                    felled_by_year[y] += before[i] > 0 && now == 0 ? 1 : 0;
                    taken_by_year[y] += now < before[i] ? before[i] - now : 0;
                }
            }
        }
        std::string line;
        for (int y = 0; y < 10; ++y) {
            line += std::to_string(felled_by_year[y]) + " ";
        }
        MESSAGE("trees felled each year: " << line << "; people " << g.population(0) << ", sprouts now "
                                            << sprouts(g, oaks, 60));
        CHECK(felled_by_year[0] > 0);
        // The grove comes back: wood in the last three years too.
        CHECK(taken_by_year[7] + taken_by_year[8] + taken_by_year[9] > 0);
        CHECK(felled_by_year[7] + felled_by_year[8] + felled_by_year[9] > 0);
        // Nothing is lost: every tree is standing, growing or a sprout.
        int there = 0;
        for (std::uint32_t i = oaks; i < oaks + 60; ++i) {
            there += g.nodes()[i].amount > 0 || g.sprout(i) ? 1 : 0;
        }
        CHECK(there == 60);
    }

}

TEST_SUITE("resources") {
    TEST_CASE("a forager whose bushes are picked clean waits for them, without a word") {
        // Two bushes; once their berries are picked there are no more until next year (phase 99).
        const Land l = land(21, {FeatureType::BerryBush, FeatureType::Herbs}, FeatureType::BerryBush, 2,
                            Fixed::from_ratio(1, 20));
        const auto g_owned = std::make_unique<Game>(content(), l.map, setup());
        Game& g = *g_owned;
        const EntityId forager = build(g, "core:forager", l.x, l.z);
        const sc::sim::BuildingDef& def = content()->buildings[g.buildings().get(forager)->def];
        (void)g.take_events();
        int told = 0;
        for (int t = 0; t < 120 && g.buildings().get(forager)->supply != Supply::Waiting; ++t) {
            run(g, 100);
            told += exhausted_events(g, forager);
        }
        const Building* b = g.buildings().get(forager);
        REQUIRE(b->supply == Supply::Waiting);
        CHECK(told == 0);
        // The bushes are still there, without a berry on them.
        CHECK(left(g, FeatureType::BerryBush, l.x, l.z, 20) == 2);
        for (std::size_t i = 0; i < g.nodes().size(); ++i) {
            const MapFeature& f = g.map().features[i];
            const std::int64_t dx = f.x.floor_int() - l.x, dz = f.z.floor_int() - l.z;
            if (f.type == FeatureType::BerryBush && dx * dx + dz * dz < 20 * 20) {
                CHECK(g.fruit_on(static_cast<std::uint32_t>(i)) == 0);
            }
        }
        CHECK(std::string_view(sc::supply_key(def, *b)) == "hud.supply.waiting");
    }
}
