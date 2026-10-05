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

// A quiet game in one season of the year (a Season bit).
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

void grant(Game& g, const char* resource, std::int32_t amount) {
    Command c;
    c.type = CommandType::DevGrant;
    c.def = g.content().find_resource(resource);
    REQUIRE(c.def != kNoDef);
    c.value = amount;
    g.apply(c);
}

// Enough of everything that nobody starves or waits for logs.
void provide(Game& g) {
    grant(g, "core:log", 2000);
    for (const char* food : {"core:bread", "core:meat", "core:vegetables", "core:fruit"}) {
        grant(g, food, 3000);
    }
}

DefIndex building(const Game& g, const char* id) {
    const DefIndex d = g.content().find_building(id);
    REQUIRE(d != kNoDef);
    return d;
}

// The corner of a square of `side` x `side` cells near the town center where a
// fence fits on every module.
std::pair<std::int32_t, std::int32_t> open_ground(const Game& g, std::int32_t side) {
    const DefIndex fence = building(g, "core:picket_fence");
    const Building* tc = g.buildings().get(g.player(0).town_center);
    REQUIRE(tc != nullptr);
    for (std::int32_t r = 12; r < 200; r += 4) {
        for (const auto& [dx, dz] : {std::pair{r, 0}, std::pair{-r, 0}, std::pair{0, r}, std::pair{0, -r}, std::pair{r, r},
                                     std::pair{-r, -r}, std::pair{r, -r}, std::pair{-r, r}}) {
            const std::int32_t x0 = ((tc->x + dx) / 2) * 2, z0 = ((tc->z + dz) / 2) * 2;
            bool free = true;
            for (std::int32_t z = z0; z < z0 + side && free; z += 2) {
                for (std::int32_t x = x0; x < x0 + side && free; x += 2) {
                    free = g.can_place(0, fence, x, z, 0) == PlaceError::None;
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

void trace(Game& g, const char* def, std::int32_t x0, std::int32_t z0, std::int32_t x1, std::int32_t z1) {
    Command c;
    c.type = CommandType::Trace;
    c.def = building(g, def);
    c.position = {Fixed::from_int(x0), Fixed::from_int(z0)};
    c.value = x1;
    c.value2 = z1;
    g.apply(c);
}

// A closed square of `def`: its corner modules at (x0, z0) and (x0 + side, z0 + side).
void ring(Game& g, const char* def, std::int32_t x0, std::int32_t z0, std::int32_t side) {
    trace(g, def, x0, z0, x0 + side, z0);
    trace(g, def, x0 + side, z0, x0 + side, z0 + side);
    trace(g, def, x0 + side, z0 + side, x0, z0 + side);
    trace(g, def, x0, z0 + side, x0, z0);
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
    FAIL("could not place " << def);
    return {};
}

std::int32_t count(const Game& g, const char* def, bool complete_only = false) {
    const DefIndex d = building(g, def);
    std::int32_t n = 0;
    for (const Building& b : g.buildings().data()) {
        n += b.def == d && (!complete_only || b.state == BuildingState::Complete) ? 1 : 0;
    }
    return n;
}

// Until `n` of `def` are built.
void build(Game& g, const char* def, std::int32_t n) {
    for (int i = 0; i < 600 && count(g, def, true) < n; ++i) {
        run(g, 50);
    }
    REQUIRE(count(g, def, true) == n);
}

std::int32_t amount(const Building& b, DefIndex resource) {
    std::int32_t n = 0;
    for (const Stock& s : b.stock) {
        n += s.resource == resource ? s.amount : 0;
    }
    return n;
}

// The modules of `def` that gave their fruit in `year`.
std::int32_t picked(const Game& g, const char* def, std::uint32_t year) {
    const DefIndex d = building(g, def);
    std::int32_t n = 0;
    for (const Building& b : g.buildings().data()) {
        n += b.def == d && b.produced_year == year ? 1 : 0;
    }
    return n;
}

// A town with a forager at work and eight modules of hedge next to it.
struct Hedged {
    EntityId forager;
    std::int32_t x0 = 0, z0 = 0;
};
Hedged hedged(Game& g) {
    provide(g);
    Hedged h;
    const auto [x0, z0] = open_ground(g, 20);
    h.x0 = x0;
    h.z0 = z0;
    h.forager = place(g, "core:forager", x0 + 4, z0 + 6);
    build(g, "core:forager", 1);
    for (int i = 0; i < 100 && g.buildings().get(h.forager)->workers.empty(); ++i) {
        run(g, 50);
    }
    REQUIRE_FALSE(g.buildings().get(h.forager)->workers.empty());
    return h;
}

}  // namespace

TEST_SUITE("fences") {
    TEST_CASE("the base game's hedge, low hedge and picket fence: what Salvador asked for") {
        const Content& c = test::core_content();
        const DefIndex log = c.find_resource("core:log");
        const auto def = [&](const char* id) -> const BuildingDef& {
            const DefIndex d = c.find_building(id);
            REQUIRE(d != kNoDef);
            return c.buildings[d];
        };
        const auto has = [](const BuildingDef& d, LinePiece p) { return !d.line_pieces[static_cast<std::size_t>(p)].empty(); };
        const BuildingDef& hedge = def("core:hedge");
        const BuildingDef& low = def("core:boxhedge");
        const BuildingDef& fence = def("core:picket_fence");
        for (const BuildingDef* d : {&hedge, &low, &fence}) {
            CAPTURE(d->id);
            CHECK(d->width == kTraceModule);
            CHECK(d->depth == kTraceModule);
            CHECK(d->hp == 60);           // Not a defense: a raider's blow breaks it.
            CHECK_FALSE(d->fireproof);
            CHECK_FALSE(d->gate);
            CHECK(follows_ground(*d));
            CHECK(d->category == kGardenCategory);
            for (const LinePiece p : {LinePiece::End, LinePiece::Straight, LinePiece::Corner, LinePiece::Tee, LinePiece::Cross,
                                      LinePiece::Step}) {
                CHECK(has(*d, p));
            }
        }
        // The hedge: a log and 20 of work a module, diagonals, berries in autumn.
        CHECK(hedge.line == "hedge");
        CHECK(hedge.line_diagonal);
        CHECK(has(hedge, LinePiece::Diagonal));
        REQUIRE(hedge.cost.size() == 1);
        CHECK(hedge.cost[0].resource == log);
        CHECK(hedge.cost[0].amount == 1);
        CHECK(hedge.build_work == 20);
        CHECK(hedge.desirability > 0);
        CHECK(hedge.desirability_radius == 8);
        REQUIRE(hedge.yields.size() == 1);
        CHECK(hedge.yields[0].resource == c.find_resource("core:berries"));
        CHECK(hedge.yields[0].amount == 1);
        CHECK(hedge.yield_per == 4);
        CHECK(hedge.seasons == (1u << static_cast<unsigned>(Season::Autumn)));
        // The low hedge: no materials and 8 of work, +1 at 6 m, no diagonals.
        CHECK(low.line == "boxhedge");
        CHECK_FALSE(low.line_diagonal);
        CHECK(low.cost.empty());
        CHECK(low.build_work == 8);
        CHECK(low.desirability == 1);
        CHECK(low.desirability_radius == 6);
        CHECK(low.yields.empty());
        // The picket fence: a log and 10 of work, no diagonals.
        CHECK(fence.line == "picket");
        CHECK_FALSE(fence.line_diagonal);
        REQUIRE(fence.cost.size() == 1);
        CHECK(fence.cost[0].resource == log);
        CHECK(fence.cost[0].amount == 1);
        CHECK(fence.build_work == 10);
        CHECK(fence.desirability == 0);
        // Each has its way through.
        for (const auto& [id, line] : {std::pair{"core:hedge_arch", "hedge"}, std::pair{"core:boxhedge_gate", "boxhedge"},
                                       std::pair{"core:picket_gate", "picket"}}) {
            const BuildingDef& gate = def(id);
            CAPTURE(id);
            CHECK(gate.gate);
            CHECK(gate.line == line);
            CHECK(gate.width == kTraceModule);
            CHECK(gate.depth == kTraceModule);
            CHECK(gate.hp == 60);
        }
    }

    TEST_CASE("a closed pen of picket fence lets no villager out, until it has a gate") {
        Game g(core(), map_for(92), setup());
        const auto [x0, z0] = open_ground(g, 16);
        ring(g, "core:picket_fence", x0, z0, 12);
        REQUIRE(count(g, "core:picket_fence") == 24);
        const FixedVec2 inside{Fixed::from_int(x0 + 7), Fixed::from_int(z0 + 7)};
        const FixedVec2 outside{Fixed::from_int(x0 - 6), Fixed::from_int(z0 - 6)};
        const Building* tc = g.buildings().get(g.player(0).town_center);
        REQUIRE(g.nav().connected(outside, g.door(*tc)));
        CHECK_FALSE(g.nav().connected(inside, outside));
        for (const Building& b : g.buildings().data()) {
            if (b.def == building(g, "core:picket_fence")) {
                CHECK_FALSE(g.nav().walkable(b.x / 2, b.z / 2));
                CHECK(g.nav().barrier(b.x / 2, b.z / 2));
            }
        }
        // A gate over one of its modules: it takes its place.
        const DefIndex gate = building(g, "core:picket_gate");
        REQUIRE(g.can_place(0, gate, x0 + 6, z0, 0) == PlaceError::None);
        place(g, "core:picket_gate", x0 + 6, z0);
        CHECK(count(g, "core:picket_fence") == 23);
        CHECK(g.nav().connected(inside, outside));
        // People walk through the gate; the animals do not.
        CHECK(g.nav().walkable((x0 + 6) / 2, z0 / 2));
        CHECK(g.nav().barrier((x0 + 6) / 2, z0 / 2));
        // The gate of another fence does not go over this one.
        CHECK(g.can_place(0, building(g, "core:boxhedge_gate"), x0 + 2, z0, 0) != PlaceError::None);
        // Without the fence, the ground is no barrier.
        CHECK_FALSE(g.nav().barrier((x0 + 6) / 2, (z0 + 6) / 2));
    }

    TEST_CASE("no wild animal crosses a fence: the one inside stays in, the others stay out") {
        GameSetup s = setup();
        s.rules.wildlife = Threat::Medium;
        Game g(core(), map_for(91), s);
        // A pen of 16 x 16 m around one of them, where it fits whole.
        constexpr std::int32_t kSide = 14;
        EntityId penned;
        std::int32_t x0 = 0, z0 = 0;
        for (std::size_t i = 0; i < g.creatures().size() && !penned.valid(); ++i) {
            const Creature& a = g.creatures().data()[i];
            if (a.kind != CreatureKind::Wolf && a.kind != CreatureKind::Bear && a.kind != CreatureKind::Boar) {
                continue;
            }
            x0 = (a.position.x.floor_int() / 2) * 2 - 6;
            z0 = (a.position.z.floor_int() / 2) * 2 - 6;
            bool fits = x0 > 4 && z0 > 4;
            for (std::int32_t k = 0; k <= kSide && fits; k += 2) {
                for (const auto& [x, z] : {std::pair{x0 + k, z0}, std::pair{x0 + k, z0 + kSide}, std::pair{x0, z0 + k},
                                           std::pair{x0 + kSide, z0 + k}}) {
                    fits = fits && g.can_place(0, building(g, "core:picket_fence"), x, z, 0) == PlaceError::None;
                }
            }
            // Nobody else inside to begin with.
            for (std::size_t k = 0; k < g.creatures().size() && fits; ++k) {
                const FixedVec2 p = g.creatures().data()[k].position;
                fits = k == i || p.x.floor_int() < x0 || p.x.floor_int() >= x0 + kSide + 2 || p.z.floor_int() < z0 ||
                       p.z.floor_int() >= z0 + kSide + 2;
            }
            if (fits) {
                penned = g.creatures().entities()[i];
            }
        }
        REQUIRE(penned.valid());
        ring(g, "core:picket_fence", x0, z0, kSide);
        REQUIRE(count(g, "core:picket_fence") == 4 * kSide / 2);
        // The ground the fence closes in (its own cells are not it).
        const auto within = [&](FixedVec2 p) {
            return p.x.floor_int() >= x0 + 2 && p.x.floor_int() < x0 + kSide && p.z.floor_int() >= z0 + 2 &&
                   p.z.floor_int() < z0 + kSide;
        };
        REQUIRE(within(g.creatures().get(penned)->position));
        bool wanted_out = false;
        bool escaped = false;
        bool intruder = false;
        for (int t = 0; t < 6000; ++t) {
            g.step();
            for (std::size_t i = 0; i < g.creatures().size(); ++i) {
                const Creature& a = g.creatures().data()[i];
                if (g.creatures().entities()[i] == penned) {
                    wanted_out = wanted_out || !within(a.goal);
                    escaped = escaped || !within(a.position);
                } else {
                    intruder = intruder || within(a.position);
                }
            }
        }
        REQUIRE(g.creatures().get(penned) != nullptr);
        CHECK(wanted_out);  // It did try.
        CHECK_FALSE(escaped);
        CHECK_FALSE(intruder);
    }

    TEST_CASE("a raider breaks a fence with one blow") {
        GameSetup s = setup();
        s.rules.raiders = Threat::Medium;
        Game g(core(), map_for(93), s);
        // The town center inside a ring of fence, so they must break in.
        const Building* tc = g.buildings().get(g.player(0).town_center);
        REQUIRE(tc != nullptr);
        const std::int32_t x0 = ((tc->x - 6) / 2) * 2, z0 = ((tc->z - 6) / 2) * 2;
        constexpr std::int32_t kSide = 20;
        ring(g, "core:picket_fence", x0, z0, kSide);
        const std::int32_t modules = count(g, "core:picket_fence");
        REQUIRE(modules == 4 * kSide / 2);
        Command c;
        c.type = CommandType::DevRaid;
        g.apply(c);
        const DefIndex fence = building(g, "core:picket_fence");
        bool dented = false;
        for (int t = 0; t < 8000 && count(g, "core:picket_fence") == modules; ++t) {
            g.step();
            for (const Building& b : g.buildings().data()) {
                dented = dented || (b.def == fence && b.damage > 0);
            }
        }
        CHECK(count(g, "core:picket_fence") < modules);  // Broken through...
        CHECK_FALSE(dented);                             // ...and never left standing after a blow.
    }

    TEST_CASE("eight modules of hedge give the forager two of berries in autumn") {
        Game g(core(), map_for(92), setup(0b0100));
        const Hedged h = hedged(g);
        const DefIndex berries = g.content().find_resource("core:berries");
        REQUIRE(berries != kNoDef);
        trace(g, "core:hedge", h.x0, h.z0, h.x0 + 14, h.z0);
        REQUIRE(count(g, "core:hedge") == 8);
        // Tick by tick: whenever some modules give their fruit, the forager's
        // berries go up by one for every four of them.
        std::int32_t given = 0;
        const std::uint32_t year = g.calendar().year;
        for (int t = 0; t < 40000 && picked(g, "core:hedge", year) < 8; ++t) {
            const std::int32_t before = picked(g, "core:hedge", year);
            const std::int32_t had = amount(*g.buildings().get(h.forager), berries);
            g.step();
            REQUIRE(g.calendar().year == year);
            const std::int32_t now = picked(g, "core:hedge", year) - before;
            if (now > 0) {
                CHECK(now % 4 == 0);
                CHECK(amount(*g.buildings().get(h.forager), berries) - had == now / 4);
                given += now / 4;
            }
        }
        CHECK(picked(g, "core:hedge", year) == 8);
        CHECK(given == 2);
        // Once a year: nothing more the days after.
        const std::int32_t all = picked(g, "core:hedge", year);
        run(g, g.calendar_day_ticks() * 3);
        CHECK(picked(g, "core:hedge", g.calendar().year) == (g.calendar().year == year ? all : 0));
    }

    TEST_CASE("three modules of hedge are not enough for a berry, and a hedge gives nothing in spring") {
        {
            Game g(core(), map_for(92), setup(0b0100));
            const Hedged h = hedged(g);
            trace(g, "core:hedge", h.x0, h.z0, h.x0 + 4, h.z0);
            build(g, "core:hedge", 3);
            run(g, g.calendar_day_ticks() * 3);
            CHECK(picked(g, "core:hedge", g.calendar().year) == 0);
        }
        {
            Game g(core(), map_for(92), setup(0b0001));
            const Hedged h = hedged(g);
            trace(g, "core:hedge", h.x0, h.z0, h.x0 + 14, h.z0);
            build(g, "core:hedge", 8);
            run(g, g.calendar_day_ticks() * 3);
            REQUIRE(g.calendar().season == Season::Spring);
            CHECK(picked(g, "core:hedge", g.calendar().year) == 0);
        }
    }

    TEST_CASE("a hedge nobody gathers by gives nothing") {
        Game g(core(), map_for(92), setup(0b0100));
        provide(g);
        const auto [x0, z0] = open_ground(g, 20);
        trace(g, "core:hedge", x0, z0, x0 + 14, z0);
        build(g, "core:hedge", 8);
        run(g, g.calendar_day_ticks() * 3);
        CHECK(picked(g, "core:hedge", g.calendar().year) == 0);
    }

    TEST_CASE("a low hedge makes the place nicer 5 m away, not 10 m away, and twenty count as one") {
        Game g(core(), map_for(92), setup());
        provide(g);
        const auto [x0, z0] = open_ground(g, 24);
        // The middle of the module at (x0, z0) is (x0 + 1, z0 + 1).
        const FixedVec2 near{Fixed::from_int(x0 + 1), Fixed::from_int(z0 + 6)};   // 5 m south of it.
        const FixedVec2 far{Fixed::from_int(x0 + 1), Fixed::from_int(z0 + 11)};   // 10 m.
        const std::int32_t near_before = g.desirability_at(near);
        const std::int32_t far_before = g.desirability_at(far);
        trace(g, "core:boxhedge", x0, z0, x0, z0);
        // A site is not a hedge yet.
        CHECK(g.desirability_at(near) == near_before);
        build(g, "core:boxhedge", 1);
        CHECK(g.desirability_at(near) == near_before + 1);
        CHECK(g.desirability_at(far) == far_before);
        // More of it: still one hedge.
        trace(g, "core:boxhedge", x0 + 2, z0, x0 + 8, z0);
        build(g, "core:boxhedge", 5);
        CHECK(g.desirability_at(near) == near_before + 1);
        CHECK(g.desirability_at(far) == far_before);
        // The tall hedge reaches 8 m, and adds to the low one.
        const std::int32_t tall = g.content().buildings[building(g, "core:hedge")].desirability;
        trace(g, "core:hedge", x0, z0 + 12, x0, z0 + 12);   // Its middle 7 m from `near`, 2 m from `far`.
        build(g, "core:hedge", 1);
        CHECK(g.desirability_at(near) == near_before + 1 + tall);
        CHECK(g.desirability_at(far) == far_before + tall);
    }

    TEST_CASE("a hedge burns") {
        Game g(core(), map_for(92), setup());
        provide(g);
        const auto [x0, z0] = open_ground(g, 16);
        trace(g, "core:hedge", x0, z0, x0 + 4, z0);
        build(g, "core:hedge", 3);
        EntityId module;
        for (std::size_t i = 0; i < g.buildings().size(); ++i) {
            if (g.buildings().data()[i].x == x0 + 2 && g.buildings().data()[i].z == z0) {
                module = g.buildings().entities()[i];
            }
        }
        REQUIRE(module.valid());
        Command fire;
        fire.type = CommandType::DevIgnite;
        fire.entity = module;
        g.apply(fire);
        REQUIRE(g.buildings().get(module) != nullptr);
        CHECK(g.buildings().get(module)->fire > 0);
    }

    TEST_CASE("saving and loading keeps hedges, fences, gates and what was picked") {
        Game g(core(), map_for(92), setup(0b0100));
        const Hedged h = hedged(g);
        trace(g, "core:hedge", h.x0, h.z0, h.x0 + 14, h.z0);
        ring(g, "core:picket_fence", h.x0, h.z0 + 12, 6);
        place(g, "core:picket_gate", h.x0 + 2, h.z0 + 12);
        build(g, "core:hedge", 8);
        for (int i = 0; i < 400 && picked(g, "core:hedge", g.calendar().year) == 0; ++i) {
            run(g, 50);
        }
        REQUIRE(picked(g, "core:hedge", g.calendar().year) > 0);
        BinaryWriter w;
        g.save(w);
        Game loaded(core(), map_for(92), setup(0b0100));
        BinaryReader r(w.bytes());
        REQUIRE(loaded.load(r, core()));
        CHECK(loaded.hash() == g.hash());
        CHECK(picked(loaded, "core:hedge", g.calendar().year) == picked(g, "core:hedge", g.calendar().year));
        CHECK(count(loaded, "core:picket_gate") == 1);
        // The barrier is back on the loaded game's ground too.
        CHECK(loaded.nav().barrier(h.x0 / 2, (h.z0 + 12) / 2));
        CHECK(loaded.nav().barrier((h.x0 + 2) / 2, (h.z0 + 12) / 2));
        CHECK_FALSE(loaded.nav().barrier((h.x0 + 2) / 2, (h.z0 + 14) / 2));
        run(g, 600);
        run(loaded, 600);
        CHECK(loaded.hash() == g.hash());
    }

    TEST_CASE("a town center shut in on three sides is reached by the side left open") {
        // A palisade around the north, west and east of the town center, two
        // meters from it, and closed against it at both ends: the ground
        // between them is a pocket nobody outside can walk into. The south
        // side is open. A villager goes to the nearest side of a building,
        // and for the one who works north of it that side is in the pocket.
        Game g(core(), map_for(92), setup());
        provide(g);
        const Building tc = *g.buildings().get(g.player(0).town_center);
        // In cells of the walking grid (2 m): those the town center stands on.
        const std::int32_t k = NavGrid::kCell;
        const std::int32_t x0 = tc.x / k * k, z0 = tc.z / k * k;
        const std::int32_t x1 = (tc.x + tc.width - 1) / k * k, z1 = (tc.z + tc.depth - 1) / k * k;
        const std::int32_t mid = (x0 + x1) / 2 + 1;
        const FixedVec2 far_north{Fixed::from_int(mid), Fixed::from_int(z0 - 16)};
        // A splitter of firewood to the north: its worker comes to the town
        // center for logs, and to eat.
        const EntityId splitter = place(g, "core:firewood_splitter", x0, z0 - 30);
        REQUIRE(splitter.valid());
        Command done;
        done.type = CommandType::DevBuild;
        g.apply(done);
        EntityId worker;
        for (int t = 0; t < 4000 && !worker.valid(); ++t) {
            g.step();
            const Building* b = g.buildings().get(splitter);
            REQUIRE(b != nullptr);
            if (!b->workers.empty()) {
                const Villager* v = g.villagers().get(b->workers[0]);
                if (v != nullptr && v->task == Task::Produce) {
                    worker = b->workers[0];
                }
            }
        }
        REQUIRE(worker.valid());
        trace(g, "core:palisade", x0 - 2 * k, z0 - 2 * k, x1 + 2 * k, z0 - 2 * k);
        trace(g, "core:palisade", x0 - 2 * k, z0 - 2 * k, x0 - 2 * k, z1);
        trace(g, "core:palisade", x1 + 2 * k, z0 - 2 * k, x1 + 2 * k, z1);
        trace(g, "core:palisade", x0 - k, z1, x0 - k, z1);
        trace(g, "core:palisade", x1 + k, z1, x1 + k, z1);
        g.apply(done);
        const FixedVec2 pocket{Fixed::from_int(mid), Fixed::from_int(z0 - 1)};
        const FixedVec2 south{Fixed::from_int(mid), Fixed::from_int(z1 + k + 1)};
        REQUIRE(g.nav().walkable(g.nav().cell_of(pocket.x), g.nav().cell_of(pocket.z)));
        REQUIRE(g.nav().walkable(g.nav().cell_of(south.x), g.nav().cell_of(south.z)));
        REQUIRE_FALSE(g.nav().connected(far_north, pocket));
        REQUIRE(g.nav().connected(far_north, south));
        // The worker is outside, and its nearest side of the town center is the one shut in.
        const FixedVec2 from = g.villagers().get(worker)->position;
        REQUIRE(g.nav().connected(from, far_north));
        REQUIRE_FALSE(g.nav().connected(from, g.approach(tc, from)));
        // Four meals' time: it eats, and goes on with its work.
        const DefIndex firewood = g.content().find_resource("core:firewood");
        REQUIRE(firewood != kNoDef);
        const std::int32_t before = g.stored(0)[firewood];
        std::int32_t lowest = village::kFoodMax;
        for (int t = 0; t < 14000; ++t) {
            g.step();
            const Villager* v = g.villagers().get(worker);
            REQUIRE(v != nullptr);
            lowest = std::min(lowest, v->food);
        }
        CHECK(lowest > 0);
        CHECK(g.player(0).deaths == 0);
        CHECK(g.stored(0)[firewood] > before);
    }
}
