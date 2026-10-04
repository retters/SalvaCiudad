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
        // Two small rocks (4 units each) and no other within 150 m.
        const Land l = land(21, {FeatureType::Stone}, FeatureType::Stone, 2, Fixed::from_ratio(1, 10));
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
