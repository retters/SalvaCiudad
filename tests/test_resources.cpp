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

// Places `def` as near (x, z) as it fits and waits until it is built.
EntityId build(Game& g, const char* def, std::int32_t ox, std::int32_t oz) {
    const DefIndex d = content()->find_building(def);
    REQUIRE(d != kNoDef);
    grant(g, "core:log", 100);
    grant(g, "core:stone", 30);
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
        Game g(content(), l.map, setup());
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
        Game back(content(), l.map, setup());
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
        Game g(content(), l.map, setup());
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
        Game back(content(), l.map, setup());
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
        Game g(content(), l.map, setup());
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
            Game g(content(), *m, gs);
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

    TEST_CASE("a forager whose bushes are picked clean waits for them, without a word") {
        // Two bushes of one berry each; they grow back in a month.
        const Land l = land(21, {FeatureType::BerryBush, FeatureType::Herbs}, FeatureType::BerryBush, 2,
                            Fixed::from_ratio(1, 20));
        Game g(content(), l.map, setup());
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
        CHECK(left(g, FeatureType::BerryBush, l.x, l.z, 20) == 0);
        CHECK(std::string_view(sc::supply_key(def, *b)) == "hud.supply.waiting");
    }
}
