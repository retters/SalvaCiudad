#include <doctest.h>

#include <algorithm>
#include <map>
#include <memory>
#include <optional>
#include <utility>
#include <vector>

#include "sim/game.h"
#include "sim/worldgen.h"
#include "test_util.h"

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

GameSetup setup() {
    GameSetup s;
    s.seed = 15;
    s.rules.climate.seasons = 0b0010;  // Summer.
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

// Food and logs, so nobody starves or waits; no stone: the tests count it.
void provide(Game& g) {
    grant(g, "core:log", 2000);
    for (const char* food : {"core:bread", "core:meat", "core:vegetables", "core:fruit"}) {
        grant(g, food, 3000);
    }
}

// Cobbled streets need a town center of the second level.
void level_up(Game& g) {
    Command c;
    c.type = CommandType::DevLevel;
    g.apply(c);
    REQUIRE(g.tier(0) >= 2);
}

DefIndex building(const Game& g, const char* id) {
    const DefIndex d = g.content().find_building(id);
    REQUIRE(d != kNoDef);
    return d;
}

// The corner of a square of `side` x `side` cells near the town center where a
// stretch of road fits on every module.
std::pair<std::int32_t, std::int32_t> open_ground(const Game& g, std::int32_t side) {
    const DefIndex road = building(g, "core:dirt_road");
    const Building* tc = g.buildings().get(g.player(0).town_center);
    REQUIRE(tc != nullptr);
    for (std::int32_t r = 12; r < 200; r += 4) {
        for (const auto& [dx, dz] : {std::pair{r, 0}, std::pair{-r, 0}, std::pair{0, r}, std::pair{0, -r}, std::pair{r, r},
                                     std::pair{-r, -r}, std::pair{r, -r}, std::pair{-r, r}}) {
            const std::int32_t x0 = ((tc->x + dx) / 2) * 2, z0 = ((tc->z + dz) / 2) * 2;
            bool free = true;
            for (std::int32_t z = z0; z < z0 + side && free; z += 2) {
                for (std::int32_t x = x0; x < x0 + side && free; x += 2) {
                    free = g.can_place(0, road, x, z, 0) == PlaceError::None;
                }
            }
            if (free) {
                return {x0, z0};
            }
        }
    }
    FAIL("no open ground near the town");
    return {0, 0};
}

Command trace(const Game& g, const char* def, std::int32_t x0, std::int32_t z0, std::int32_t x1, std::int32_t z1) {
    Command c;
    c.type = CommandType::Trace;
    c.def = building(g, def);
    c.position = {Fixed::from_int(x0), Fixed::from_int(z0)};
    c.value = x1;
    c.value2 = z1;
    return c;
}

// The buildings of a definition (a road's are its stretches still being built).
std::int32_t sites(const Game& g, const char* def) {
    const DefIndex d = building(g, def);
    std::int32_t n = 0;
    for (const Building& b : g.buildings().data()) {
        n += b.def == d ? 1 : 0;
    }
    return n;
}

// The cells with a road of a kind.
std::int32_t paved(const Game& g, const char* def) {
    const std::uint8_t kind = g.road_kind(building(g, def));
    REQUIRE(kind != 0);
    std::int32_t n = 0;
    for (const auto& [cell, k] : g.roads()) {
        n += k == kind ? 1 : 0;
    }
    return n;
}

// Until there are `n` cells of road of a kind, or the time runs out.
void wait_paved(Game& g, const char* def, std::int32_t n, int ticks = 30000) {
    for (int t = 0; t < ticks && paved(g, def) < n; t += 50) {
        run(g, 50);
    }
}

std::int32_t have(const Game& g, const char* resource) {
    const DefIndex r = g.content().find_resource(resource);
    std::int32_t n = 0;
    for (const Building& b : g.buildings().data()) {
        for (const Stock& s : b.stock) {
            n += s.resource == r ? s.amount : 0;
        }
        for (const Stock& s : b.delivered) {
            n += s.resource == r ? s.amount : 0;
        }
    }
    for (const Villager& v : g.villagers().data()) {
        n += v.carrying.resource == r ? v.carrying.amount : 0;
    }
    return n;
}

EntityId place(Game& g, const char* def, std::int32_t x, std::int32_t z) {
    Command c;
    c.type = CommandType::PlaceBuilding;
    c.def = building(g, def);
    c.position = {Fixed::from_int(x), Fixed::from_int(z)};
    g.apply(c);
    for (std::size_t i = 0; i < g.buildings().size(); ++i) {
        const Building& b = g.buildings().data()[i];
        if (b.def == c.def && b.x == x && b.z == z) {
            return g.buildings().entities()[i];
        }
    }
    return {};
}

void build(Game& g, EntityId id) {
    REQUIRE(id.valid());
    for (int t = 0; t < 400 && g.buildings().get(id) != nullptr && g.buildings().get(id)->state != BuildingState::Complete; ++t) {
        run(g, 50);
    }
    REQUIRE(g.buildings().get(id) != nullptr);
    REQUIRE(g.buildings().get(id)->state == BuildingState::Complete);
}

// An explorer walks from one point to another: how long it takes, and how
// much of that on a road.
struct Walk {
    int ticks = 0;
    int on_road = 0;
};
Walk walk(Game& g, EntityId who, FixedVec2 from, FixedVec2 to) {
    const auto send = [&](FixedVec2 where) {
        Command c;
        c.type = CommandType::MoveVillager;
        c.entity = who;
        c.position = where;
        g.apply(c);
    };
    const auto at = [&](FixedVec2 where) -> bool {
        const Villager* v = g.villagers().get(who);
        if (v == nullptr) {
            return false;
        }
        const FixedVec2 d = v->position - where;
        return abs(d.x) <= Fixed::from_ratio(1, 4) && abs(d.z) <= Fixed::from_ratio(1, 4);
    };
    send(from);
    for (int t = 0; t < 6000 && !at(from); ++t) {
        g.step();
    }
    REQUIRE(at(from));
    Walk w;
    send(to);
    while (w.ticks < 3000 && !at(to)) {
        g.step();
        ++w.ticks;
        const Villager* v = g.villagers().get(who);
        REQUIRE(v != nullptr);
        w.on_road += g.road_at(v->position.x.floor_int(), v->position.z.floor_int()) != 0 ? 1 : 0;
    }
    REQUIRE(at(to));
    return w;
}

// A game with an explorer and, 40 m apart, two points; `road` (if any) is
// laid along the row next to the straight line between them, a short way round.
Walk crossing(const char* road) {
    Game g(core(), map_for(92), setup());
    provide(g);
    grant(g, "core:stone", 200);
    level_up(g);
    const auto [x0, z0] = open_ground(g, 48);
    const DefIndex hut = building(g, "core:explorer");
    EntityId post;
    for (std::int32_t dz = 20; dz < 44 && !post.valid(); dz += 2) {
        if (g.can_place(0, hut, x0 + 20, z0 + dz, 0) == PlaceError::None) {
            post = place(g, "core:explorer", x0 + 20, z0 + dz);
        }
    }
    build(g, post);
    for (int t = 0; t < 200 && g.buildings().get(post)->workers.empty(); ++t) {
        run(g, 50);
    }
    REQUIRE(g.buildings().get(post)->workers.size() == 1);
    const EntityId who = g.buildings().get(post)->workers[0];
    if (road != nullptr) {
        g.apply(trace(g, road, x0 + 4, z0 + 12, x0 + 40, z0 + 12));
        wait_paved(g, road, 19);
        REQUIRE(paved(g, road) == 19);
    }
    return walk(g, who, {Fixed::from_int(x0 + 3), Fixed::from_int(z0 + 11)}, {Fixed::from_int(x0 + 43), Fixed::from_int(z0 + 11)});
}

}  // namespace

TEST_SUITE("roads") {
    TEST_CASE("the base game's roads: a dirt road, a cobbled street, and what takes them away") {
        const Content& c = test::core_content();
        const auto def = [&](const char* id) -> const BuildingDef& {
            const DefIndex d = c.find_building(id);
            REQUIRE(d != kNoDef);
            return c.buildings[d];
        };
        const BuildingDef& dirt = def("core:dirt_road");
        const BuildingDef& street = def("core:cobbled_street");
        const BuildingDef& eraser = def("core:road_eraser");
        for (const BuildingDef* d : {&dirt, &street, &eraser}) {
            CAPTURE(d->id);
            CHECK(d->line == "road");
            CHECK_FALSE(d->line_diagonal);
            CHECK(d->width == kRoadModule);
            CHECK(d->depth == kRoadModule);
            for (const LinePiece p : {LinePiece::Pillar, LinePiece::End, LinePiece::Straight, LinePiece::Corner, LinePiece::Tee,
                                      LinePiece::Cross}) {
                CHECK_FALSE(d->line_pieces[static_cast<std::size_t>(p)].empty());
            }
        }
        // Salvador's numbers.
        CHECK(dirt.cost.empty());
        CHECK(dirt.build_work == 5);
        CHECK(dirt.road == 115);
        CHECK(dirt.tier == 0);
        CHECK(dirt.road_desirability == 0);
        REQUIRE(street.cost.size() == 1);
        CHECK(street.cost[0].resource == c.find_resource("core:stone"));
        CHECK(street.cost[0].amount == 1);
        CHECK(street.build_work == 15);
        CHECK(street.road == 130);
        CHECK(street.tier == 2);
        CHECK(street.road_desirability == 4);
        CHECK(follows_ground(dirt));
        CHECK(eraser.road_eraser);
        CHECK(eraser.road == 0);
        CHECK(eraser.cost.empty());
    }

    TEST_CASE("a traced road is built stretch by stretch, and then it is ground and no building") {
        Game g(core(), map_for(92), setup());
        provide(g);
        const auto [x0, z0] = open_ground(g, 24);
        const std::size_t buildings = g.buildings().size();
        g.apply(trace(g, "core:dirt_road", x0, z0, x0 + 18, z0));
        CHECK(sites(g, "core:dirt_road") == 10);
        CHECK(g.roads().empty());
        // A stretch being built is walked over: no wall, nothing for a raider to break, no barrier.
        for (std::int32_t x = x0; x <= x0 + 18; x += 2) {
            CHECK(g.nav().walkable(x / 2, z0 / 2));
            CHECK_FALSE(g.nav().obstacle(x / 2, z0 / 2));
            CHECK_FALSE(g.nav().barrier(x / 2, z0 / 2));
        }
        const std::uint32_t version = g.roads_version();
        wait_paved(g, "core:dirt_road", 10);
        CHECK(paved(g, "core:dirt_road") == 10);
        CHECK(sites(g, "core:dirt_road") == 0);
        CHECK(g.buildings().size() == buildings);
        CHECK(g.roads_version() != version);
        const std::uint8_t kind = g.road_kind(building(g, "core:dirt_road"));
        for (std::int32_t x = x0; x <= x0 + 19; ++x) {
            CHECK(g.road_at(x, z0) == kind);
            CHECK(g.road_at(x, z0 + 1) == kind);
        }
        CHECK(g.road_at(x0 - 1, z0) == 0);
        CHECK(g.road_at(x0, z0 + 2) == 0);
        CHECK(g.road_def(kind) == building(g, "core:dirt_road"));
        CHECK(g.nav().road_percent(x0 / 2, z0 / 2) == 115);
        CHECK(g.nav().road_percent(x0 / 2, z0 / 2 + 1) == 100);
        // The same road again: there is nothing to lay.
        const std::uint32_t rejected = g.rejected_commands();
        g.apply(trace(g, "core:dirt_road", x0, z0, x0 + 18, z0));
        CHECK(g.rejected_commands() == rejected + 1);
        // A road goes on the cells of the walking grid, not across two of them.
        CHECK(g.can_place(0, building(g, "core:dirt_road"), x0 + 1, z0 + 4, 0) == PlaceError::Blocked);
    }

    TEST_CASE("a tree in the way of a road is felled first") {
        Game g(core(), map_for(92), setup());
        provide(g);
        const auto [x0, z0] = open_ground(g, 16);
        Command plant;
        plant.type = CommandType::DevFeature;
        plant.def = static_cast<std::uint16_t>(FeatureType::Tree);
        plant.def2 = 0;
        plant.count = 1;
        plant.value = Fixed::one().raw();
        plant.position = {Fixed::from_int(x0 + 5), Fixed::from_int(z0 + 1)};  // The middle of the third stretch.
        const std::size_t before = g.map().features.size();
        g.apply(plant);
        REQUIRE(g.map().features.size() == before + 1);
        REQUIRE(g.nodes().back().amount > 0);
        g.apply(trace(g, "core:dirt_road", x0, z0, x0 + 8, z0));
        REQUIRE(sites(g, "core:dirt_road") == 5);
        CHECK(g.nodes().back().amount > 0);  // Still standing: somebody has to come and fell it.
        wait_paved(g, "core:dirt_road", 5);
        CHECK(paved(g, "core:dirt_road") == 5);
        CHECK(g.nodes().back().amount == 0);
    }

    TEST_CASE("a cobbled street needs the second level and a stone a stretch: without stone it is not finished") {
        // (A map with no loose stones: laborers would pick them up for the street, phase 102.)
        MapData bare = map_for(92);
        std::erase_if(bare.features, [](const MapFeature& f) { return f.type == FeatureType::LooseStones; });
        Game g(core(), std::move(bare), setup());
        provide(g);
        const auto [x0, z0] = open_ground(g, 44);
        CHECK(g.can_place(0, building(g, "core:cobbled_street"), x0, z0, 0) == PlaceError::Locked);
        level_up(g);
        const std::int32_t stone = have(g, "core:stone");
        const std::int32_t wanted = stone + 3;  // Three more than there is stone for.
        REQUIRE(wanted <= 40);
        for (std::int32_t i = 0; i < wanted; i += 20) {
            const std::int32_t n = std::min(20, wanted - i);
            g.apply(trace(g, "core:cobbled_street", x0, z0 + i / 10, x0 + (n - 1) * 2, z0 + i / 10));
        }
        REQUIRE(sites(g, "core:cobbled_street") == wanted);
        wait_paved(g, "core:cobbled_street", stone);
        run(g, 3000);
        CHECK(paved(g, "core:cobbled_street") == stone);
        CHECK(sites(g, "core:cobbled_street") == 3);
        CHECK(have(g, "core:stone") == 0);
        // With the stone, they are.
        grant(g, "core:stone", 3);
        wait_paved(g, "core:cobbled_street", wanted);
        CHECK(paved(g, "core:cobbled_street") == wanted);
        CHECK(sites(g, "core:cobbled_street") == 0);
        CHECK(have(g, "core:stone") == 0);
    }

    TEST_CASE("a dirt road is made a street for the stone alone; nothing goes over as good a road") {
        Game g(core(), map_for(92), setup());
        provide(g);
        level_up(g);
        const auto [x0, z0] = open_ground(g, 24);
        g.apply(trace(g, "core:dirt_road", x0, z0, x0 + 6, z0));
        wait_paved(g, "core:dirt_road", 4);
        REQUIRE(paved(g, "core:dirt_road") == 4);
        grant(g, "core:stone", 10);
        const std::int32_t stone = have(g, "core:stone");
        const std::int32_t logs = have(g, "core:log");
        g.apply(trace(g, "core:cobbled_street", x0, z0, x0 + 6, z0));
        CHECK(sites(g, "core:cobbled_street") == 4);
        // Until each stretch is done, the dirt road is still there to walk on.
        CHECK(paved(g, "core:dirt_road") == 4);
        wait_paved(g, "core:cobbled_street", 4);
        CHECK(paved(g, "core:cobbled_street") == 4);
        CHECK(paved(g, "core:dirt_road") == 0);
        CHECK(g.roads().size() == 4);
        CHECK(have(g, "core:stone") == stone - 4);
        CHECK(have(g, "core:log") == logs);
        CHECK(g.nav().road_percent(x0 / 2, z0 / 2) == 130);
        // Neither a dirt road nor another street goes over a street.
        const std::uint32_t rejected = g.rejected_commands();
        g.apply(trace(g, "core:dirt_road", x0, z0, x0 + 6, z0));
        g.apply(trace(g, "core:cobbled_street", x0, z0, x0 + 6, z0));
        CHECK(g.rejected_commands() == rejected + 2);
        CHECK(g.can_place(0, building(g, "core:dirt_road"), x0, z0, 0) == PlaceError::Blocked);
    }

    TEST_CASE("with a road a short way round, one takes the road and gets there sooner; a street is faster still") {
        const Walk across = crossing(nullptr);
        const Walk dirt = crossing("core:dirt_road");
        const Walk street = crossing("core:cobbled_street");
        MESSAGE("ticks: across " << across.ticks << ", dirt road " << dirt.ticks << " (" << dirt.on_road << " on it), street "
                                 << street.ticks << " (" << street.on_road << " on it)");
        CHECK(across.on_road == 0);
        CHECK(dirt.on_road * 4 > dirt.ticks * 3);      // Most of the way on the road.
        CHECK(street.on_road * 4 > street.ticks * 3);
        CHECK(dirt.ticks < across.ticks);
        CHECK(street.ticks < dirt.ticks);
    }

    TEST_CASE("a house whose door opens onto a street is a nicer place; onto a dirt road, the same as before") {
        Game g(core(), map_for(92), setup());
        provide(g);
        grant(g, "core:stone", 100);
        level_up(g);
        const auto [x0, z0] = open_ground(g, 24);
        const EntityId id = place(g, "core:house", x0 + 4, z0 + 8);
        build(g, id);
        const Building house = *g.buildings().get(id);
        const FixedVec2 here{Fixed::from_int(house.x) + Fixed::from_ratio(house.width, 2),
                             Fixed::from_int(house.z) + Fixed::from_ratio(house.depth, 2)};
        // The cell of the road in front of the door (the door is a meter out of the wall).
        const FixedVec2 door = g.door(house);
        std::int32_t rx = (door.x.floor_int() / 2) * 2, rz = (door.z.floor_int() / 2) * 2;
        if (g.can_place(0, building(g, "core:dirt_road"), rx, rz, 0) != PlaceError::None) {
            rz -= 2;  // A house on odd cells: the stretch against its wall begins a meter farther.
        }
        REQUIRE(g.can_place(0, building(g, "core:dirt_road"), rx, rz, 0) == PlaceError::None);
        const std::int32_t before = g.desirability_at(here, &house);
        g.apply(trace(g, "core:dirt_road", rx - 4, rz, rx + 4, rz));
        wait_paved(g, "core:dirt_road", 5);
        REQUIRE(paved(g, "core:dirt_road") == 5);
        CHECK(g.desirability_at(here, g.buildings().get(id)) == before);
        g.apply(trace(g, "core:cobbled_street", rx - 4, rz, rx + 4, rz));
        wait_paved(g, "core:cobbled_street", 5);
        REQUIRE(paved(g, "core:cobbled_street") == 5);
        CHECK(g.desirability_at(here, g.buildings().get(id)) == before + 4);
        // A street that only passes by its side or its back does not count.
        Command erase = trace(g, "core:road_eraser", rx, rz, rx, rz);
        g.apply(erase);
        CHECK(g.desirability_at(here, g.buildings().get(id)) == before);
    }

    TEST_CASE("the eraser takes roads and unfinished stretches away, and a building or a field laid over a road too") {
        Game g(core(), map_for(92), setup());
        provide(g);
        const auto [x0, z0] = open_ground(g, 30);
        g.apply(trace(g, "core:dirt_road", x0, z0, x0 + 18, z0));
        wait_paved(g, "core:dirt_road", 10);
        REQUIRE(paved(g, "core:dirt_road") == 10);
        const DefIndex eraser = building(g, "core:road_eraser");
        CHECK(g.can_place(0, eraser, x0, z0, 0) == PlaceError::None);
        CHECK(g.can_place(0, eraser, x0, z0 + 4, 0) == PlaceError::Blocked);
        // Three cells of it, by tracing; nothing is built.
        const std::size_t buildings = g.buildings().size();
        g.apply(trace(g, "core:road_eraser", x0, z0, x0 + 4, z0));
        CHECK(paved(g, "core:dirt_road") == 7);
        CHECK(g.buildings().size() == buildings);
        CHECK(g.road_at(x0 + 4, z0) == 0);
        CHECK(g.nav().road_percent((x0 + 4) / 2, z0 / 2) == 100);
        CHECK(g.road_at(x0 + 6, z0) != 0);
        // Where there is nothing to take away, the order is refused.
        const std::uint32_t rejected = g.rejected_commands();
        g.apply(trace(g, "core:road_eraser", x0, z0 + 6, x0 + 8, z0 + 6));
        CHECK(g.rejected_commands() == rejected + 1);
        // A stretch still being built goes too.
        g.apply(trace(g, "core:dirt_road", x0, z0 + 10, x0 + 6, z0 + 10));
        REQUIRE(sites(g, "core:dirt_road") == 4);
        g.apply(trace(g, "core:road_eraser", x0, z0 + 10, x0 + 6, z0 + 10));
        CHECK(sites(g, "core:dirt_road") == 0);
        CHECK(g.buildings().size() == buildings);
        // A building over a road: the road under it is gone.
        REQUIRE(g.can_place(0, building(g, "core:palisade"), x0 + 8, z0, 0) == PlaceError::None);
        REQUIRE(place(g, "core:palisade", x0 + 8, z0).valid());
        CHECK(g.road_at(x0 + 8, z0) == 0);
        CHECK(paved(g, "core:dirt_road") == 6);
        // And so is the road under a house that only covers part of its cells.
        REQUIRE(g.can_place(0, building(g, "core:house"), x0 + 13, z0 - 3, 0) == PlaceError::None);
        REQUIRE(place(g, "core:house", x0 + 13, z0 - 3).valid());
        CHECK(g.road_at(x0 + 12, z0) == 0);
        CHECK(g.road_at(x0 + 18, z0) == 0);
        CHECK(g.road_at(x0 + 10, z0) != 0);
    }

    TEST_CASE("saving and loading keeps the roads and the stretches being built") {
        Game g(core(), map_for(92), setup());
        provide(g);
        grant(g, "core:stone", 6);
        level_up(g);
        const auto [x0, z0] = open_ground(g, 24);
        g.apply(trace(g, "core:dirt_road", x0, z0, x0 + 18, z0));
        wait_paved(g, "core:dirt_road", 10);
        g.apply(trace(g, "core:cobbled_street", x0, z0, x0 + 6, z0));
        wait_paved(g, "core:cobbled_street", 2);
        g.apply(trace(g, "core:dirt_road", x0, z0 + 4, x0 + 18, z0 + 4));
        run(g, 40);
        REQUIRE(!g.roads().empty());
        BinaryWriter w;
        g.save(w);
        Game loaded(core(), map_for(92), setup());
        BinaryReader r(w.bytes());
        REQUIRE(loaded.load(r, core()));
        CHECK(loaded.hash() == g.hash());
        CHECK(loaded.roads() == g.roads());
        CHECK(loaded.nav().road_percent(x0 / 2, z0 / 2) == g.nav().road_percent(x0 / 2, z0 / 2));
        CHECK(sites(loaded, "core:dirt_road") == sites(g, "core:dirt_road"));
        run(g, 1500);
        run(loaded, 1500);
        CHECK(loaded.hash() == g.hash());
        CHECK(loaded.roads() == g.roads());
        // A save with a road where the map has no cell, or of a kind there is not, is refused.
        Game one(core(), map_for(92), setup());
        provide(one);
        const auto [ox, oz] = open_ground(one, 8);
        one.apply(trace(one, "core:dirt_road", ox, oz, ox, oz));
        wait_paved(one, "core:dirt_road", 1);
        REQUIRE(one.roads().size() == 1);
        BinaryWriter good;
        one.save(good);
        const std::uint8_t kind = one.roads().begin()->second;
        const std::uint32_t cell = one.roads().begin()->first;
        // Its record: the count (1), the cell and the kind.
        std::vector<std::uint8_t> bytes = good.bytes();
        const std::uint8_t record[9] = {1, 0, 0, 0, static_cast<std::uint8_t>(cell), static_cast<std::uint8_t>(cell >> 8),
                                        static_cast<std::uint8_t>(cell >> 16), static_cast<std::uint8_t>(cell >> 24), kind};
        const auto found = std::search(bytes.begin(), bytes.end(), std::begin(record), std::end(record));
        REQUIRE(found != bytes.end());
        const auto at = static_cast<std::size_t>(found - bytes.begin());
        for (const auto& [offset, value] : {std::pair<std::size_t, std::uint8_t>{8, 9}, std::pair<std::size_t, std::uint8_t>{8, 0},
                                            std::pair<std::size_t, std::uint8_t>{7, 0xFF}}) {
            std::vector<std::uint8_t> bad = bytes;
            bad[at + offset] = value;
            Game refused(core(), map_for(92), setup());
            BinaryReader br(bad);
            CHECK_FALSE(refused.load(br, core()));
        }
    }

    TEST_CASE("two games given the same road orders agree, tick by tick") {
        Game a(core(), map_for(92), setup());
        Game b(core(), map_for(92), setup());
        for (Game* g : {&a, &b}) {
            provide(*g);
            grant(*g, "core:stone", 20);
            level_up(*g);
        }
        const auto [x0, z0] = open_ground(a, 24);
        const std::vector<Command> orders = {trace(a, "core:dirt_road", x0, z0, x0 + 18, z0),
                                             trace(a, "core:cobbled_street", x0, z0 + 4, x0 + 10, z0 + 4),
                                             trace(a, "core:cobbled_street", x0 + 4, z0, x0 + 10, z0),
                                             trace(a, "core:road_eraser", x0 + 14, z0, x0 + 18, z0)};
        for (const Command& c : orders) {
            // Each order travels as bytes.
            BinaryWriter w;
            c.write(w);
            BinaryReader r(w.bytes());
            Command back;
            REQUIRE(Command::read(r, back));
            a.apply(c);
            b.apply(back);
            for (int t = 0; t < 400; ++t) {
                a.step();
                b.step();
            }
            CHECK(a.hash() == b.hash());
        }
        CHECK(a.roads() == b.roads());
        CHECK(!a.roads().empty());
    }

    TEST_CASE("without roads a search finds the same way as ever, and with them it never guesses too high") {
        Game g(core(), map_for(92), setup());
        provide(g);
        const auto [x0, z0] = open_ground(g, 48);
        const FixedVec2 from{Fixed::from_int(x0 + 3), Fixed::from_int(z0 + 11)};
        const FixedVec2 to{Fixed::from_int(x0 + 43), Fixed::from_int(z0 + 11)};
        NavGrid nav = g.nav();
        std::vector<FixedVec2> direct;
        REQUIRE(nav.find_path(from, to, direct));
        // A road along the next row: the way goes over it.
        nav.set_road_kinds({115, 130});
        for (std::int32_t x = x0 + 4; x <= x0 + 40; x += 2) {
            nav.set_road(x / 2, (z0 + 12) / 2, 2);
        }
        std::vector<FixedVec2> by_road;
        REQUIRE(nav.find_path(from, to, by_road));
        bool on_road = false;
        for (const FixedVec2& p : by_road) {
            on_road = on_road || nav.road(p.x.floor_int() / 2, p.z.floor_int() / 2) != 0;
        }
        CHECK(on_road);
        // Taken away again: the same way as at first.
        for (std::int32_t x = x0 + 4; x <= x0 + 40; x += 2) {
            nav.set_road(x / 2, (z0 + 12) / 2, 0);
        }
        std::vector<FixedVec2> again;
        REQUIRE(nav.find_path(from, to, again));
        CHECK(again == direct);
    }
}
